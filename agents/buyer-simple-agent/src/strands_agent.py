"""
Strands agent definition with buyer tools for x402 data purchasing.

This is the heart of the buyer kit. Both agent.py (interactive CLI) and
agent_agentcore.py (AWS) import from here. The tools are plain @tool —
NOT @requires_payment — because the buyer generates tokens, not receives them.

Usage:
    from src.strands_agent import payments, create_agent, NVM_PLAN_ID
"""

import os

from dotenv import load_dotenv
from strands import Agent, tool

from payments_py import Payments, PaymentOptions

from .budget import Budget
from .tools.discover import discover_pricing_impl
from .tools.balance import check_balance_impl
from .tools.purchase import purchase_data_impl
from .tools.discover_a2a import discover_agent_impl
from .tools.purchase_a2a import purchase_a2a_impl

load_dotenv()

NVM_API_KEY = os.environ["NVM_API_KEY"]
NVM_ENVIRONMENT = os.getenv("NVM_ENVIRONMENT", "sandbox")
NVM_PLAN_ID = os.environ["NVM_PLAN_ID"]
NVM_AGENT_ID = os.getenv("NVM_AGENT_ID")
SELLER_URL = os.getenv("SELLER_URL", "http://localhost:3000")
SELLER_A2A_URL = os.getenv("SELLER_A2A_URL", "http://localhost:9000")

MAX_DAILY_SPEND = int(os.getenv("MAX_DAILY_SPEND", "0"))
MAX_PER_REQUEST = int(os.getenv("MAX_PER_REQUEST", "0"))

payments = Payments.get_instance(
    PaymentOptions(nvm_api_key=NVM_API_KEY, environment=NVM_ENVIRONMENT)
)

budget = Budget(max_daily=MAX_DAILY_SPEND, max_per_request=MAX_PER_REQUEST)


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
def discover_agent(agent_url: str = "") -> dict:
    """Discover a seller via A2A protocol by fetching its agent card.

    Retrieves /.well-known/agent.json from the seller and parses
    the payment extension to find plan ID, agent ID, and pricing.

    Args:
        agent_url: Base URL of the A2A agent (defaults to SELLER_A2A_URL env var).
    """
    url = agent_url or SELLER_A2A_URL
    return discover_agent_impl(url)


@tool
def purchase_a2a(query: str, agent_url: str = "") -> dict:
    """Purchase data from a seller using the A2A protocol.

    Sends an A2A message with automatic x402 payment via PaymentsClient.
    The agent card's payment extension provides the plan ID and agent ID.

    Args:
        query: The data query to send to the seller.
        agent_url: Base URL of the A2A agent (defaults to SELLER_A2A_URL env var).
    """
    url = agent_url or SELLER_A2A_URL

    # First discover the agent to get payment info
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

    if not plan_id:
        return {
            "status": "error",
            "content": [{"text": "No plan ID found in agent card or environment."}],
            "credits_used": 0,
        }

    # Budget pre-check
    min_credits = payment.get("credits", 1)
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
    if result.get("status") == "success" and credits_used > 0:
        budget.record_purchase(credits_used, url, query)

    return result


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a data buying agent. You help users discover and purchase data from \
sellers using the Nevermined payment protocols.

You support two modes:

**HTTP mode (x402):**
1. **discover_pricing** — Call this first to see what the seller offers via HTTP.
2. **check_balance** — Check your credit balance and budget before purchasing.
3. **purchase_data** — Buy data by sending an x402-protected HTTP request.

**A2A mode (Agent-to-Agent protocol):**
1. **discover_agent** — Fetch the seller's agent card (/.well-known/agent.json) \
to see skills and payment requirements.
2. **check_balance** — Check your credit balance and budget.
3. **purchase_a2a** — Send an A2A message with automatic payment.

Important guidelines:
- Always discover the seller first so you can inform the user about costs.
- Always check the balance before making a purchase.
- Tell the user the expected cost BEFORE purchasing and confirm they want to proceed.
- After a purchase, report what was received and the credits spent.
- If budget limits are exceeded, explain the situation and suggest alternatives.
- Use A2A tools (discover_agent, purchase_a2a) when the seller runs in A2A mode.
- Use HTTP tools (discover_pricing, purchase_data) when the seller runs in HTTP mode.
- You can purchase from different sellers by providing their URL."""

TOOLS = [discover_pricing, check_balance, purchase_data, discover_agent, purchase_a2a]


def create_agent(model) -> Agent:
    """Create a Strands agent with the given model.

    Args:
        model: A Strands-compatible model (OpenAIModel, BedrockModel, etc.)

    Returns:
        Configured Strands Agent with buyer tools.
    """
    return Agent(
        model=model,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )
