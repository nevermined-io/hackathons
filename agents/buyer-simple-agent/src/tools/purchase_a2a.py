"""Purchase data from a seller via A2A protocol — JSON-RPC with x402 auth."""

import json
from uuid import uuid4

import httpx

from payments_py import Payments


def purchase_a2a_impl(
    payments: Payments,
    plan_id: str,
    agent_url: str,
    agent_id: str,
    query: str,
) -> dict:
    """Send an A2A message to a seller with x402 payment.

    Generates an x402 access token, then sends an A2A JSON-RPC message
    with the token in the payment-signature header.

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
        # Step 1: Generate x402 access token (sync)
        token_result = payments.x402.get_x402_access_token(
            plan_id=plan_id,
            agent_id=agent_id,
        )
        access_token = token_result.get("accessToken")

        if not access_token:
            return {
                "status": "error",
                "content": [{"text": (
                    "Failed to generate x402 access token. "
                    "Are you subscribed to this plan?"
                )}],
                "credits_used": 0,
            }

        # Step 2: Build A2A JSON-RPC message
        message_id = str(uuid4())
        rpc_body = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": message_id,
                    "role": "user",
                    "parts": [{"kind": "text", "text": query}],
                }
            },
        }

        # Step 3: Send with payment-signature header
        url = agent_url.rstrip("/") + "/"
        with httpx.Client(timeout=90.0) as client:
            response = client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "payment-signature": access_token,
                },
                json=rpc_body,
            )

        if response.status_code == 402:
            return {
                "status": "payment_required",
                "content": [{"text": "Payment required (HTTP 402). Check credits or token."}],
                "credits_used": 0,
            }

        if response.status_code != 200:
            return {
                "status": "error",
                "content": [{"text": (
                    f"A2A server returned HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                )}],
                "credits_used": 0,
            }

        # Step 4: Parse JSON-RPC response
        rpc_response = response.json()

        if "error" in rpc_response:
            error = rpc_response["error"]
            return {
                "status": "error",
                "content": [{"text": f"A2A error: {error.get('message', error)}"}],
                "credits_used": 0,
            }

        result = rpc_response.get("result", {})
        return _extract_response(result)

    except httpx.ConnectError:
        return {
            "status": "error",
            "content": [{"text": f"Cannot connect to agent at {agent_url}. Is it running?"}],
            "credits_used": 0,
        }
    except Exception as e:
        return {
            "status": "error",
            "content": [{"text": f"A2A purchase failed: {e}"}],
            "credits_used": 0,
        }


def _extract_response(result: dict) -> dict:
    """Extract text and credits from an A2A Task/Message result."""
    response_text = ""
    credits_used = 0

    # Extract from status.message.parts
    status = result.get("status", {})
    message = status.get("message", {})
    for part in message.get("parts", []):
        if isinstance(part, dict) and part.get("kind") == "text":
            response_text += part.get("text", "")

    # Extract creditsUsed from metadata
    metadata = status.get("metadata") or result.get("metadata") or {}
    credits_used = metadata.get("creditsUsed", 0)

    # Try artifacts if no text in status
    if not response_text:
        for artifact in result.get("artifacts", []):
            for part in artifact.get("parts", []):
                if isinstance(part, dict) and part.get("kind") == "text":
                    response_text += part.get("text", "")

    if not response_text:
        response_text = "Agent completed the task but returned no text."

    return {
        "status": "success",
        "content": [{"text": response_text}],
        "response": response_text,
        "credits_used": credits_used,
    }
