"""
Strands agent definition with buyer tools for x402 data purchasing.

This is the heart of the buyer kit. Both agent.py (interactive CLI) and
agent_agentcore.py (AWS) import from here. The tools are plain @tool —
NOT @requires_payment — because the buyer generates tokens, not receives them.

Usage:
    from src.strands_agent import payments, create_agent, NVM_PLAN_ID, seller_registry
"""

import os

from dotenv import load_dotenv
from strands import Agent, tool

from payments_py import Payments, PaymentOptions

from .budget import Budget
from .log import get_logger, log
from .registry import SellerRegistry
from .tools.balance import check_balance_impl
from .tools.discover import discover_pricing_impl
from .tools.discover_a2a import discover_agent_impl
from .tools.purchase import purchase_data_impl
from .tools.purchase_a2a import purchase_a2a_impl

load_dotenv()

NVM_API_KEY = os.environ["NVM_API_KEY"]
NVM_ENVIRONMENT = os.getenv("NVM_ENVIRONMENT", "sandbox")
NVM_PLAN_ID = os.environ["NVM_PLAN_ID"]
NVM_AGENT_ID = os.getenv("NVM_AGENT_ID")
SELLER_URL = os.getenv("SELLER_URL", "http://localhost:3000")
SELLER_A2A_URL = os.getenv("SELLER_A2A_URL", "")

MAX_DAILY_SPEND = int(os.getenv("MAX_DAILY_SPEND", "0"))
MAX_PER_REQUEST = int(os.getenv("MAX_PER_REQUEST", "0"))

payments = Payments.get_instance(
    PaymentOptions(nvm_api_key=NVM_API_KEY, environment=NVM_ENVIRONMENT)
)

budget = Budget(max_daily=MAX_DAILY_SPEND, max_per_request=MAX_PER_REQUEST)

_logger = get_logger("buyer.tools")

# Shared seller registry — used by tools and registration server
seller_registry = SellerRegistry()


# ---------------------------------------------------------------------------
# Buyer tools (plain @tool — no @requires_payment)
# ---------------------------------------------------------------------------

@tool
def discover_pricing(seller_url: str = "") -> dict:
    """Discover a seller's available data services and pricing tiers.

    Call this first to understand what data is available and how much it costs.

    Args:
        seller_url: Base URL of the seller (defaults to SELLER_URL env var).
    """
    url = seller_url or SELLER_URL
    return discover_pricing_impl(url)


@tool
def check_balance() -> dict:
    """Check your Nevermined credit balance and daily budget status.

    Returns your remaining credits on the seller's plan and your
    local spending budget status.
    """
    log(_logger, "TOOLS", "BALANCE", f"plan={NVM_PLAN_ID[:12]}")
    result = check_balance_impl(payments, NVM_PLAN_ID)
    budget_status = budget.get_status()
    result["budget"] = budget_status

    budget_lines = [
        "",
        "Local budget:",
        f"  Daily limit: {budget_status['daily_limit']}",
        f"  Daily spent: {budget_status['daily_spent']}",
        f"  Daily remaining: {budget_status['daily_remaining']}",
        f"  Total spent (session): {budget_status['total_spent']}",
    ]
    if result.get("content"):
        result["content"][0]["text"] += "\n".join(budget_lines)

    return result


@tool
def purchase_data(query: str, seller_url: str = "") -> dict:
    """Purchase data from a seller using x402 payment.

    Generates an x402 access token and sends the query to the seller.
    Budget limits are checked before purchasing.

    Args:
        query: The data query to send to the seller.
        seller_url: Base URL of the seller (defaults to SELLER_URL env var).
    """
    url = seller_url or SELLER_URL

    # Pre-check with minimum 1 credit (actual cost is determined by the seller)
    allowed, reason = budget.can_spend(1)
    if not allowed:
        return {
            "status": "budget_exceeded",
            "content": [{"text": f"Budget check failed: {reason}"}],
            "credits_used": 0,
        }

    result = purchase_data_impl(
        payments=payments,
        plan_id=NVM_PLAN_ID,
        seller_url=url,
        query=query,
        agent_id=NVM_AGENT_ID,
    )

    credits_used = result.get("credits_used", 0)
    if result.get("status") == "success" and credits_used > 0:
        budget.record_purchase(credits_used, url, query)

    return result


# ---------------------------------------------------------------------------
# A2A buyer tools
# ---------------------------------------------------------------------------

@tool
def list_sellers() -> dict:
    """List all registered sellers, their skills, and pricing.

    Sellers register automatically via A2A when they start with --buyer-url.
    You can also register sellers manually with discover_agent.
    """
    sellers = seller_registry.list_all()
    log(_logger, "TOOLS", "LIST_SELLERS", f"count={len(sellers)}")
    if not sellers:
        return {
            "status": "success",
            "content": [{"text": "No sellers registered yet. "
                         "Sellers will appear here when they start with --buyer-url, "
                         "or you can discover one manually with discover_agent."}],
            "sellers": [],
        }

    lines = [f"Registered sellers ({len(sellers)}):"]
    for s in sellers:
        skills_str = ", ".join(s["skills"]) if s["skills"] else "none"
        lines.append(f"\n  {s['name']} ({s['url']})")
        lines.append(f"    Skills: {skills_str}")
        lines.append(f"    Min credits: {s['credits']}")
        if s["cost_description"]:
            lines.append(f"    Pricing: {s['cost_description']}")

    return {
        "status": "success",
        "content": [{"text": "\n".join(lines)}],
        "sellers": sellers,
    }


@tool
def discover_agent(agent_url: str = "") -> dict:
    """Discover a seller via A2A protocol by fetching its agent card.

    Retrieves /.well-known/agent.json from the seller and parses
    the payment extension to find plan ID, agent ID, and pricing.
    Also registers the seller in the local registry.

    Args:
        agent_url: Base URL of the A2A agent (defaults to SELLER_A2A_URL env var).
    """
    url = agent_url or SELLER_A2A_URL
    log(_logger, "TOOLS", "DISCOVER", f"url={url}")
    result = discover_agent_impl(url)

    if result.get("status") == "success":
        log(_logger, "TOOLS", "DISCOVER",
            f'found name={result.get("name", "?")} skills={len(result.get("skills", []))}')

        # Also register in the seller registry (best-effort)
        import httpx
        try:
            card_url = f"{url.rstrip('/')}/.well-known/agent.json"
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(card_url)
            if resp.status_code == 200:
                seller_registry.register(url, resp.json())
        except Exception:
            pass

    return result


@tool
def purchase_a2a(query: str, agent_url: str = "") -> dict:
    """Purchase data from a seller using the A2A protocol.

    Sends an A2A message with automatic x402 payment via PaymentsClient.
    The agent card's payment extension provides the plan ID and agent ID.

    If no agent_url is provided, uses the first registered seller from the
    registry, or falls back to SELLER_A2A_URL.

    Args:
        query: The data query to send to the seller.
        agent_url: Base URL of the A2A agent (optional if sellers are registered).
    """
    url = agent_url or SELLER_A2A_URL

    # If no URL specified, try the registry
    if not url:
        url = seller_registry.get_first_url()
    if not url:
        return {
            "status": "error",
            "content": [{"text": "No seller URL provided and no sellers registered. "
                         "Use list_sellers to check, or provide an agent_url."}],
            "credits_used": 0,
        }

    log(_logger, "TOOLS", "PURCHASE", f'url={url} query="{query[:60]}"')

    # Check registry for cached payment info (skip discovery round-trip)
    cached = seller_registry.get_payment_info(url)
    if cached:
        log(_logger, "TOOLS", "PURCHASE",
            f'using cached payment info plan={cached["planId"][:12]}')
        plan_id = cached["planId"] or NVM_PLAN_ID
        agent_id = cached["agentId"] or NVM_AGENT_ID or ""
        min_credits = cached["credits"]
    else:
        # Fall back to full discovery
        discovery = discover_agent_impl(url)
        if discovery.get("status") != "success":
            return {
                "status": "error",
                "content": [{"text": f"Cannot discover agent at {url}. Is it running?"}],
                "credits_used": 0,
            }
        payment = discovery.get("payment", {})
        plan_id = payment.get("planId", NVM_PLAN_ID)
        agent_id = payment.get("agentId", NVM_AGENT_ID or "")
        min_credits = payment.get("credits", 1)

    if not plan_id:
        return {
            "status": "error",
            "content": [{"text": "No plan ID found in agent card or environment."}],
            "credits_used": 0,
        }

    # Budget pre-check
    allowed, reason = budget.can_spend(min_credits)
    if not allowed:
        return {
            "status": "budget_exceeded",
            "content": [{"text": f"Budget check failed: {reason}"}],
            "credits_used": 0,
        }

    result = purchase_a2a_impl(
        payments=payments,
        plan_id=plan_id,
        agent_url=url,
        agent_id=agent_id,
        query=query,
    )

    credits_used = result.get("credits_used", 0)
    log(_logger, "TOOLS", "PURCHASE",
        f'status={result.get("status")} credits={credits_used}')
    if result.get("status") == "success" and credits_used > 0:
        budget.record_purchase(credits_used, url, query)

    return result


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

_GUIDELINES = """\

Important guidelines:
- Always discover the seller first so you can inform the user about costs.
- Always check the balance before making a purchase.
- Tell the user the expected cost BEFORE purchasing and confirm they want to proceed.
- After a purchase, report what was received and the credits spent.
- If budget limits are exceeded, explain the situation and suggest alternatives.
- You can purchase from different sellers by providing their URL."""

_A2A_PROMPT = """\
You are a data buying agent. You help users discover and purchase data from \
sellers using the A2A (Agent-to-Agent) protocol with Nevermined payments.

Sellers register with you automatically when they start. Use list_sellers \
to see available sellers, their skills, and pricing.

Your workflow:
1. **list_sellers** — See all registered sellers and their capabilities.
2. **discover_agent** — Manually discover a seller by URL (also registers it).
3. **check_balance** — Check your credit balance and budget.
4. **purchase_a2a** — Send an A2A message with automatic payment.
""" + _GUIDELINES

_HTTP_PROMPT = """\
You are a data buying agent. You help users discover and purchase data from \
sellers using the x402 HTTP payment protocol.

Your workflow:
1. **discover_pricing** — Call this first to see what the seller offers.
2. **check_balance** — Check your credit balance and budget before purchasing.
3. **purchase_data** — Buy data by sending an x402-protected HTTP request.
""" + _GUIDELINES

_A2A_TOOLS = [list_sellers, discover_agent, check_balance, purchase_a2a]
_HTTP_TOOLS = [discover_pricing, check_balance, purchase_data]


def create_agent(model, mode: str = "a2a") -> Agent:
    """Create a Strands agent with the given model.

    Args:
        model: A Strands-compatible model (OpenAIModel, BedrockModel, etc.)
        mode: Agent mode — "a2a" for A2A marketplace tools (default),
              "http" for direct x402 HTTP tools.

    Returns:
        Configured Strands Agent with buyer tools.
    """
    if mode == "a2a":
        tools = _A2A_TOOLS
        prompt = _A2A_PROMPT
    elif mode == "http":
        tools = _HTTP_TOOLS
        prompt = _HTTP_PROMPT
    else:
        raise ValueError(f"Invalid mode {mode!r}, must be 'a2a' or 'http'")
    return Agent(
        model=model,
        tools=tools,
        system_prompt=prompt,
    )
