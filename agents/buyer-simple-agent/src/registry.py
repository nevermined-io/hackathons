"""Thread-safe in-memory seller registry.

Stores seller agent cards and payment info discovered via A2A registration
or manual discovery. Used by the buyer agent to track available sellers.
"""

import threading
from dataclasses import dataclass, field


@dataclass
class SellerInfo:
    """Parsed seller information from an agent card."""

    url: str
    name: str
    description: str
    skills: list[dict]
    plan_id: str = ""
    agent_id: str = ""
    credits: int = 1
    cost_description: str = ""


class SellerRegistry:
    """Thread-safe in-memory registry of seller agents."""

    def __init__(self):
        self._sellers: dict[str, SellerInfo] = {}
        self._lock = threading.Lock()

    def register(self, agent_url: str, agent_card: dict) -> SellerInfo:
        """Parse an agent card and store seller info.

        Args:
            agent_url: The seller's base URL.
            agent_card: The full agent card dict (from /.well-known/agent.json).

        Returns:
            The stored SellerInfo.
        """
        url = agent_url.rstrip("/")

        name = agent_card.get("name", "Unknown Agent")
        description = agent_card.get("description", "")
        skills = agent_card.get("skills", [])

        # Extract payment extension
        plan_id = ""
        agent_id = ""
        credits = 1
        cost_description = ""

        extensions = agent_card.get("capabilities", {}).get("extensions", [])
        for ext in extensions:
            if ext.get("uri") == "urn:nevermined:payment":
                params = ext.get("params", {})
                plan_id = params.get("planId", "")
                agent_id = params.get("agentId", "")
                credits = params.get("credits", 1)
                cost_description = params.get("costDescription", "")
                break

        info = SellerInfo(
            url=url,
            name=name,
            description=description,
            skills=skills,
            plan_id=plan_id,
            agent_id=agent_id,
            credits=credits,
            cost_description=cost_description,
        )

        with self._lock:
            self._sellers[url] = info

        return info

    def get_payment_info(self, agent_url: str) -> dict | None:
        """Get cached payment info for a seller (skips re-discovery).

        Args:
            agent_url: The seller's base URL.

        Returns:
            Dict with planId, agentId, credits, or None if not registered.
        """
        url = agent_url.rstrip("/")
        with self._lock:
            info = self._sellers.get(url)
        if not info:
            return None
        return {
            "planId": info.plan_id,
            "agentId": info.agent_id,
            "credits": info.credits,
        }

    def list_all(self) -> list[dict]:
        """Return a summary list of all registered sellers."""
        with self._lock:
            sellers = list(self._sellers.values())
        result = []
        for s in sellers:
            skill_names = [
                sk.get("name", sk.get("id", "unknown")) for sk in s.skills
            ]
            result.append({
                "url": s.url,
                "name": s.name,
                "description": s.description,
                "skills": skill_names,
                "credits": s.credits,
                "cost_description": s.cost_description,
            })
        return result

    def get_first_url(self) -> str | None:
        """Return the URL of the first registered seller, or None."""
        with self._lock:
            if not self._sellers:
                return None
            return next(iter(self._sellers.values())).url

    def __len__(self) -> int:
        with self._lock:
            return len(self._sellers)
