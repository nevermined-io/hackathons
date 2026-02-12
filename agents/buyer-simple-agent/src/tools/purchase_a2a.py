"""Purchase data from a seller via A2A protocol using PaymentsClient."""

import asyncio
from uuid import uuid4

from a2a.types import MessageSendParams, Message, TextPart

from payments_py import Payments
from payments_py.a2a.payments_client import PaymentsClient


def purchase_a2a_impl(
    payments: Payments,
    plan_id: str,
    agent_url: str,
    agent_id: str,
    query: str,
) -> dict:
    """Send an A2A message to a seller with x402 payment.

    Uses PaymentsClient which automatically generates and injects x402
    access tokens into A2A requests.  Streams the response events and
    returns the final completed result.

    Args:
        payments: Initialized Payments SDK instance.
        plan_id: The seller's plan ID (from agent card).
        agent_url: Base URL of the A2A agent.
        agent_id: Seller's agent ID (from agent card).
        query: The data query to send.

    Returns:
        dict with status, content (for Strands), response text, and credits_used.
    """
    try:
        client = PaymentsClient(
            agent_base_url=agent_url,
            payments=payments,
            agent_id=agent_id,
            plan_id=plan_id,
        )

        params = MessageSendParams(
            message=Message(
                message_id=str(uuid4()),
                role="user",
                parts=[TextPart(text=query)],
            )
        )

        events = asyncio.run(_collect_stream(client, params))
        return _extract_from_events(events)

    except Exception as e:
        error_msg = str(e)
        if "Connect" in error_msg or "ConnectionRefused" in error_msg:
            return {
                "status": "error",
                "content": [{"text": f"Cannot connect to agent at {agent_url}. Is it running?"}],
                "credits_used": 0,
            }
        return {
            "status": "error",
            "content": [{"text": f"A2A purchase failed: {e}"}],
            "credits_used": 0,
        }


async def _collect_stream(client: PaymentsClient, params: MessageSendParams) -> list:
    """Collect all SSE events from a streaming send_message call."""
    events = []
    async for event in client.send_message_stream(params):
        events.append(event)
    return events


def _extract_text_from_parts(parts) -> str:
    """Extract text from a list of message parts."""
    text = ""
    for part in parts:
        if hasattr(part, "root"):
            part = part.root
        if hasattr(part, "text"):
            text += part.text
        elif isinstance(part, dict) and part.get("kind") == "text":
            text += part.get("text", "")
    return text


def _extract_from_events(events: list) -> dict:
    """Extract the final response from a list of A2A SSE events.

    Events are tuples of (Task, TaskStatusUpdateEvent | None).
    We look for the last completed event and extract text + creditsUsed.
    """
    response_text = ""
    credits_used = 0

    if not events:
        return {
            "status": "success",
            "content": [{"text": "Agent completed the task but returned no events."}],
            "response": "",
            "credits_used": 0,
        }

    # Walk events in reverse to find the final completed one
    for event in reversed(events):
        # Unwrap tuple: (Task, TaskStatusUpdateEvent | None)
        task = None
        status_update = None
        if isinstance(event, tuple):
            task = event[0] if len(event) > 0 else None
            status_update = event[1] if len(event) > 1 else None
        else:
            task = event

        # Check the Task object's status
        if task is not None and hasattr(task, "status") and task.status:
            state = task.status.state
            state_val = state.value if hasattr(state, "value") else str(state)

            if state_val == "completed":
                # Extract text from status.message
                if hasattr(task.status, "message") and task.status.message:
                    parts = getattr(task.status.message, "parts", [])
                    response_text = _extract_text_from_parts(parts)

                # Extract creditsUsed from TaskStatusUpdateEvent metadata
                if status_update is not None:
                    metadata = getattr(status_update, "metadata", None) or {}
                    if isinstance(metadata, dict):
                        credits_used = metadata.get("creditsUsed", 0)

                # Fallback: check task-level metadata
                if credits_used == 0:
                    metadata = getattr(task, "metadata", None) or {}
                    if isinstance(metadata, dict):
                        credits_used = metadata.get("creditsUsed", 0)

                break

            elif state_val == "failed":
                msg_text = ""
                if hasattr(task.status, "message") and task.status.message:
                    parts = getattr(task.status.message, "parts", [])
                    msg_text = _extract_text_from_parts(parts)
                return {
                    "status": "error",
                    "content": [{"text": msg_text or "Agent task failed."}],
                    "credits_used": 0,
                }

    if not response_text:
        response_text = "Agent completed the task but returned no text."

    return {
        "status": "success",
        "content": [{"text": response_text}],
        "response": response_text,
        "credits_used": credits_used,
    }
