"""Purchase data from a seller - x402 token generation and HTTP request."""

import base64
import json

import httpx

from payments_py import Payments


def purchase_data_impl(
    payments: Payments,
    plan_id: str,
    seller_url: str,
    query: str,
    agent_id: str | None = None,
) -> dict:
    """Purchase data from a seller using the x402 protocol.

    Flow:
    1. Generate x402 access token via payments.x402.get_x402_access_token()
    2. POST {seller_url}/data with payment-signature header
    3. Handle 402 (insufficient credits) or 200 (success)

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
        # Step 1: Generate x402 access token
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

        # Step 2: POST /data with payment-signature header
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{seller_url}/data",
                headers={
                    "Content-Type": "application/json",
                    "payment-signature": access_token,
                },
                json={"query": query},
            )

        # Step 3: Handle response
        if response.status_code == 402:
            payment_required_header = response.headers.get("payment-required", "")
            details = ""
            if payment_required_header:
                try:
                    decoded = json.loads(
                        base64.b64decode(payment_required_header).decode("utf-8")
                    )
                    details = f"\nPayment details: {json.dumps(decoded, indent=2)}"
                except Exception:
                    pass

            return {
                "status": "payment_required",
                "content": [{"text": (
                    f"Payment required (HTTP 402). "
                    f"Insufficient credits or invalid token.{details}"
                )}],
                "credits_used": 0,
            }

        if response.status_code != 200:
            return {
                "status": "error",
                "content": [{"text": (
                    f"Seller returned HTTP {response.status_code}: {response.text[:500]}"
                )}],
                "credits_used": 0,
            }

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
        return {
            "status": "error",
            "content": [{"text": f"Cannot connect to seller at {seller_url}. Is it running?"}],
            "credits_used": 0,
        }
    except Exception as e:
        return {
            "status": "error",
            "content": [{"text": f"Purchase failed: {e}"}],
            "credits_used": 0,
        }
