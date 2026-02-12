"""Purchase data from a seller via A2A protocol — uses PaymentsClient."""

import asyncio
from uuid import uuid4

from a2a.types import (
    Message,
    MessageSendParams,
    Role,
)

from payments_py import Payments


def purchase_a2a_impl(
    payments: Payments,
    plan_id: str,
    agent_url: str,
    agent_id: str,
    query: str,
) -> dict:
    """Send an A2A message to a seller with automatic x402 payment.

    Uses PaymentsClient which auto-generates the x402 access token
    and injects it as a payment-signature header.

    Args:
        payments: Initialized Payments SDK instance.
        plan_id: The seller's plan ID (from agent card).
        agent_url: Base URL of the A2A agent.
        agent_id: Seller's agent ID (from agent card).
        query: The data query to send.

    Returns:
        dict with status, content (for Strands), response text, and credits_used.
    """
    return asyncio.get_event_loop().run_until_complete(
        _purchase_a2a_async(payments, plan_id, agent_url, agent_id, query)
    ) if _has_running_loop() else asyncio.run(
        _purchase_a2a_async(payments, plan_id, agent_url, agent_id, query)
    )


def _has_running_loop() -> bool:
    """Check if there's already a running event loop."""
    try:
        loop = asyncio.get_running_loop()
        return loop.is_running()
    except RuntimeError:
        return False


async def _purchase_a2a_async(
    payments: Payments,
    plan_id: str,
    agent_url: str,
    agent_id: str,
    query: str,
) -> dict:
    """Async implementation of A2A purchase."""
    try:
        client = payments.a2a.get_client(
            agent_base_url=agent_url,
            agent_id=agent_id,
            plan_id=plan_id,
        )

        message = Message(
            message_id=str(uuid4()),
            role=Role.user,
            parts=[{"kind": "text", "text": query}],
        )

        params = MessageSendParams(message=message)

        result = await client.send_message(params)

        # Extract response text from the result
        response_text = ""
        credits_used = 0

        if result is None:
            return {
                "status": "error",
                "content": [{"text": "No response from seller agent."}],
                "credits_used": 0,
            }

        # Result can be a Task or Message
        if hasattr(result, "status") and result.status:
            status = result.status
            if hasattr(status, "message") and status.message:
                for part in getattr(status.message, "parts", []):
                    if hasattr(part, "root"):
                        part = part.root
                    if hasattr(part, "text"):
                        response_text += part.text
                    elif isinstance(part, dict) and part.get("kind") == "text":
                        response_text += part.get("text", "")

        # Check for creditsUsed in metadata
        if hasattr(result, "status") and hasattr(result.status, "metadata"):
            metadata = result.status.metadata or {}
            credits_used = metadata.get("creditsUsed", 0)

        # Also check task-level metadata
        if hasattr(result, "metadata"):
            task_meta = result.metadata or {}
            if "creditsUsed" in task_meta:
                credits_used = task_meta["creditsUsed"]

        if not response_text:
            # Try artifacts
            for artifact in getattr(result, "artifacts", []):
                for part in getattr(artifact, "parts", []):
                    if hasattr(part, "root"):
                        part = part.root
                    if hasattr(part, "text"):
                        response_text += part.text

        if not response_text:
            response_text = "Agent completed the task but returned no text."

        return {
            "status": "success",
            "content": [{"text": response_text}],
            "response": response_text,
            "credits_used": credits_used,
        }

    except Exception as e:
        error_msg = str(e)
        if "402" in error_msg or "Payment" in error_msg:
            return {
                "status": "payment_required",
                "content": [{"text": f"Payment failed: {error_msg}"}],
                "credits_used": 0,
            }
        return {
            "status": "error",
            "content": [{"text": f"A2A purchase failed: {error_msg}"}],
            "credits_used": 0,
        }
