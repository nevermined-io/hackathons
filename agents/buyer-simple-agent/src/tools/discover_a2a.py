"""Discover a seller via A2A agent card — fetch /.well-known/agent.json."""

import httpx

from ..log import get_logger, log


_logger = get_logger("buyer.discovery")


def discover_agent_impl(agent_url: str) -> dict:
    """Fetch an A2A agent card and parse payment extension.

    Args:
        agent_url: Base URL of the A2A agent (e.g. http://localhost:9000).

    Returns:
        dict with status, content (for Strands), and parsed agent card info.
    """
    url = agent_url.rstrip("/")
    card_url = f"{url}/.well-known/agent.json"
    log(_logger, "DISCOVERY", "FETCHING", f"url={card_url}")

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(card_url)

        if response.status_code != 200:
            log(_logger, "DISCOVERY", "ERROR",
                f"HTTP {response.status_code} from {card_url}")
            return {
                "status": "error",
                "content": [{"text": (
                    f"Failed to fetch agent card from {card_url}: "
                    f"HTTP {response.status_code}"
                )}],
            }

        card = response.json()

        # Extract basic info
        name = card.get("name", "Unknown Agent")
        description = card.get("description", "No description")
        version = card.get("version", "unknown")
        skills = card.get("skills", [])

        # Extract payment extension
        payment_ext = None
        extensions = card.get("capabilities", {}).get("extensions", [])
        for ext in extensions:
            if ext.get("uri") == "urn:nevermined:payment":
                payment_ext = ext.get("params", {})
                break

        payment_type = payment_ext.get("paymentType", "unknown") if payment_ext else "free"

        # Build readable output
        lines = [
            f"Agent: {name}",
            f"Description: {description}",
            f"Version: {version}",
            f"URL: {url}",
            "",
            "Skills:",
        ]
        for skill in skills:
            skill_name = skill.get("name", skill.get("id", "unknown"))
            skill_desc = skill.get("description", "")
            lines.append(f"  - {skill_name}: {skill_desc}")

        if payment_ext:
            lines.extend([
                "",
                "Payment:",
                f"  Plan ID: {payment_ext.get('planId', '')}",
                f"  Agent ID: {payment_ext.get('agentId', '')}",
                f"  Min credits: {payment_ext.get('credits', 0)}",
                f"  Payment type: {payment_type}",
                f"  Cost info: {payment_ext.get('costDescription', '')}",
            ])
        else:
            lines.extend(["", "Payment: No payment extension found (free agent)"])

        result = {
            "status": "success",
            "content": [{"text": "\n".join(lines)}],
            "name": name,
            "description": description,
            "skills": skills,
        }

        if payment_ext:
            result["payment"] = payment_ext

        log(_logger, "DISCOVERY", "FOUND",
            f"name={name} skills={len(skills)} payment={payment_type}")
        return result

    except httpx.ConnectError:
        log(_logger, "DISCOVERY", "ERROR",
            f"cannot connect to {card_url}")
        return {
            "status": "error",
            "content": [{"text": f"Cannot connect to agent at {card_url}. Is it running?"}],
        }
    except Exception as e:
        log(_logger, "DISCOVERY", "ERROR", f"failed: {e}")
        return {
            "status": "error",
            "content": [{"text": f"Failed to discover agent: {e}"}],
        }
