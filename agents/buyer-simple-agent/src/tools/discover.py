"""Discover seller pricing - GET /pricing from a seller endpoint."""

import httpx


def discover_pricing_impl(seller_url: str) -> dict:
    """Fetch pricing tiers from a seller's /pricing endpoint.

    Args:
        seller_url: Base URL of the seller (e.g. http://localhost:3000).

    Returns:
        dict with status, content (for Strands), planId, and tiers.
    """
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(f"{seller_url}/pricing")

        if response.status_code != 200:
            return {
                "status": "error",
                "content": [{"text": f"Seller returned HTTP {response.status_code}"}],
            }

        data = response.json()
        plan_id = data.get("planId", "unknown")
        tiers = data.get("tiers", {})

        lines = [f"Seller: {seller_url}", f"Plan ID: {plan_id}", "", "Pricing tiers:"]
        for name, tier in tiers.items():
            credits = tier.get("credits", "?")
            desc = tier.get("description", "")
            tool_name = tier.get("tool", "")
            lines.append(f"  - {name}: {credits} credits — {desc} (tool: {tool_name})")

        return {
            "status": "success",
            "content": [{"text": "\n".join(lines)}],
            "planId": plan_id,
            "tiers": tiers,
        }

    except httpx.ConnectError:
        return {
            "status": "error",
            "content": [{"text": f"Cannot connect to seller at {seller_url}. Is it running?"}],
        }
    except Exception as e:
        return {
            "status": "error",
            "content": [{"text": f"Failed to discover pricing: {e}"}],
        }
