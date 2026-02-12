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

load_dotenv()

NVM_API_KEY = os.environ["NVM_API_KEY"]
NVM_ENVIRONMENT = os.getenv("NVM_ENVIRONMENT", "sandbox")
NVM_PLAN_ID = os.environ["NVM_PLAN_ID"]
NVM_AGENT_ID = os.getenv("NVM_AGENT_ID")
SELLER_URL = os.getenv("SELLER_URL", "http://localhost:3000")

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
# Agent factory
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a data buying agent. You help users discover and purchase data from \
sellers using the Nevermined x402 payment protocol.

Your workflow:
1. **discover_pricing** — Call this first to see what the seller offers and \
the cost of each tier.
2. **check_balance** — Check your credit balance and budget before purchasing.
3. **purchase_data** — Buy data by sending a query to the seller.

Important guidelines:
- Always discover pricing first so you can inform the user about costs.
- Always check the balance before making a purchase.
- Tell the user the expected cost BEFORE purchasing and confirm they want to proceed.
- After a purchase, report what was received and the credits spent.
- If budget limits are exceeded, explain the situation and suggest alternatives.
- You can purchase from different sellers by providing their URL."""

TOOLS = [discover_pricing, check_balance, purchase_data]


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
