"""Purchase data from a seller - x402 token generation and HTTP request."""

import base64
import json

import httpx

from payments_py import Payments


def _decode_payment_required(header: str) -> str:
    """Decode the base64-encoded payment-required header into readable details."""
    if not header:
        return ""
    try:
        decoded = json.loads(base64.b64decode(header).decode("utf-8"))
        return f"\nPayment details: {json.dumps(decoded, indent=2)}"
    except Exception:
        return ""


def _error(message: str) -> dict:
    """Build a standard error response."""
    return {"status": "error", "content": [{"text": message}], "credits_used": 0}


def purchase_data_impl(
    payments: Payments,
    plan_id: str,
    seller_url: str,
    query: str,
    agent_id: str | None = None,
) -> dict:
    """Purchase data from a seller using the x402 protocol.

    Generates an x402 access token, POSTs the query to {seller_url}/data
    with the payment-signature header, and handles the response.

    Args:
        payments: Initialized Payments SDK instance.
        plan_id: The seller's plan ID.
        seller_url: Base URL of the seller.
        query: The data query to send.
        agent_id: Optional seller agent ID for token scoping.

    Returns:
        dict with status, content (for Strands), response data, and credits_used.
    """
    try:
        token_result = payments.x402.get_x402_access_token(
            plan_id=plan_id,
            agent_id=agent_id,
        )
        access_token = token_result.get("accessToken")

        if not access_token:
            return _error(
                "Failed to generate x402 access token. "
                "Are you subscribed to this plan?"
            )

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{seller_url}/data",
                headers={
                    "Content-Type": "application/json",
                    "payment-signature": access_token,
                },
                json={"query": query},
            )

        if response.status_code == 402:
            details = _decode_payment_required(
                response.headers.get("payment-required", "")
            )
            return {
                "status": "payment_required",
                "content": [{"text": (
                    f"Payment required (HTTP 402). "
                    f"Insufficient credits or invalid token.{details}"
                )}],
                "credits_used": 0,
            }

        if response.status_code != 200:
            return _error(
                f"Seller returned HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        data = response.json()
        agent_response = data.get("response", "")
        credits_used = data.get("credits_used", 0)

        return {
            "status": "success",
            "content": [{"text": agent_response}],
            "response": agent_response,
            "credits_used": credits_used,
        }

    except httpx.ConnectError:
        return _error(f"Cannot connect to seller at {seller_url}. Is it running?")
    except Exception as e:
        return _error(f"Purchase failed: {e}")
