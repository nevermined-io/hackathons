"""Purchase data from a seller via A2A protocol using PaymentsClient."""

import asyncio
from uuid import uuid4

from a2a.types import MessageSendParams, Message, TextPart

from payments_py import Payments
from payments_py.a2a.payments_client import PaymentsClient

from ..log import get_logger, log


def _error(message: str) -> dict:
    """Build a standard error response."""
    return {"status": "error", "content": [{"text": message}], "credits_used": 0}


def _success(text: str, credits_used: int = 0) -> dict:
    """Build a standard success response."""
    return {
        "status": "success",
        "content": [{"text": text}],
        "response": text,
        "credits_used": credits_used,
    }


_logger = get_logger("buyer.a2a_client")


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
    log(_logger, "A2A_CLIENT", "CONNECT",
        f"url={agent_url} plan={plan_id[:12]} agent={agent_id[:12]}")
    try:
        client = PaymentsClient(
            agent_base_url=agent_url,
            payments=payments,
            agent_id=agent_id,
            plan_id=plan_id,
        )

        log(_logger, "A2A_CLIENT", "TOKEN", "generating x402 access token")

        params = MessageSendParams(
            message=Message(
                message_id=str(uuid4()),
                role="user",
                parts=[TextPart(text=query)],
            )
        )

        log(_logger, "A2A_CLIENT", "SENDING", f'query="{query[:60]}"')
        events = asyncio.run(_collect_stream(client, params))
        result = _extract_from_events(events)

        log(_logger, "A2A_CLIENT", "COMPLETED",
            f'credits_used={result.get("credits_used", 0)} '
            f'response={len(result.get("response", result.get("content", [{}])[0].get("text", "")))} chars')
        return result

    except (ConnectionError, OSError):
        log(_logger, "A2A_CLIENT", "ERROR",
            f"cannot connect to agent at {agent_url}")
        return _error(f"Cannot connect to agent at {agent_url}. Is it running?")
    except Exception as e:
        log(_logger, "A2A_CLIENT", "ERROR", f"purchase failed: {e}")
        return _error(f"A2A purchase failed: {e}")


async def _collect_stream(client: PaymentsClient, params: MessageSendParams) -> list:
    """Collect all SSE events from a streaming send_message call."""
    events = []
    async for event in client.send_message_stream(params):
        events.append(event)
    return events


def _extract_text_from_parts(parts) -> str:
    """Extract text from a list of A2A message parts.

    Parts may be Pydantic models (with .root/.text) or plain dicts.
    """
    fragments = []
    for part in parts:
        if hasattr(part, "root"):
            part = part.root
        if hasattr(part, "text"):
            fragments.append(part.text)
        elif isinstance(part, dict) and part.get("kind") == "text":
            fragments.append(part.get("text", ""))
    return "".join(fragments)


def _get_metadata_value(obj, key: str, default=0):
    """Safely read a key from an object's metadata dict."""
    metadata = getattr(obj, "metadata", None) or {}
    if isinstance(metadata, dict):
        return metadata.get(key, default)
    return default


def _extract_from_events(events: list) -> dict:
    """Extract the final response from a list of A2A SSE events.

    Events are tuples of (Task, TaskStatusUpdateEvent | None).
    We look for the last completed event and extract text + creditsUsed.
    """
    if not events:
        return _success("Agent completed the task but returned no events.")

    for event in reversed(events):
        # Unwrap tuple: (Task, TaskStatusUpdateEvent | None)
        if isinstance(event, tuple):
            task, status_update = event[0], event[1] if len(event) > 1 else None
        else:
            task, status_update = event, None

        status = getattr(task, "status", None)
        if not status:
            continue

        state = status.state
        state_val = state.value if hasattr(state, "value") else str(state)

        if state_val == "completed" or state_val == "failed":
            log(_logger, "A2A_CLIENT", "EVENT", f"state={state_val}")

        if state_val == "completed":
            message = getattr(status, "message", None)
            parts = getattr(message, "parts", []) if message else []
            response_text = _extract_text_from_parts(parts)

            # Prefer creditsUsed from the status update event, fall back to task
            credits_used = 0
            if status_update is not None:
                credits_used = _get_metadata_value(status_update, "creditsUsed")
            if credits_used == 0:
                credits_used = _get_metadata_value(task, "creditsUsed")

            return _success(
                response_text or "Agent completed the task but returned no text.",
                credits_used,
            )

        if state_val == "failed":
            message = getattr(status, "message", None)
            parts = getattr(message, "parts", []) if message else []
            msg_text = _extract_text_from_parts(parts)
            return _error(msg_text or "Agent task failed.")

    return _success("Agent completed the task but returned no text.")
