"""
Scripted x402 buyer demo — step-by-step payment flow without LLM.

Demonstrates the complete buyer-side x402 flow:
1. Discover seller pricing tiers
2. Check credit balance
3. Purchase data (search query — low cost)
4. Purchase data (research query — high cost)
5. Review budget

Usage:
    # First start the seller: cd ../seller-simple-agent && poetry run agent
    # Then run this client:
    poetry run client
"""

import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from payments_py import Payments, PaymentOptions

from .tools.discover import discover_pricing_impl
from .tools.balance import check_balance_impl
from .tools.purchase import purchase_data_impl
from .budget import Budget

SELLER_URL = os.getenv("SELLER_URL", "http://localhost:3000")
NVM_API_KEY = os.getenv("NVM_API_KEY", "")
NVM_ENVIRONMENT = os.getenv("NVM_ENVIRONMENT", "sandbox")
NVM_PLAN_ID = os.getenv("NVM_PLAN_ID", "")
NVM_AGENT_ID = os.getenv("NVM_AGENT_ID")

if not NVM_API_KEY or not NVM_PLAN_ID:
    print("NVM_API_KEY and NVM_PLAN_ID are required.")
    sys.exit(1)

payments = Payments.get_instance(
    PaymentOptions(nvm_api_key=NVM_API_KEY, environment=NVM_ENVIRONMENT)
)

budget = Budget(max_daily=100, max_per_request=10)


def pretty_json(obj: dict) -> str:
    """Format JSON for console output."""
    return json.dumps(obj, indent=2)


def print_step(number: int, title: str):
    """Print a formatted step header."""
    print(f"\n{'=' * 60}")
    print(f"STEP {number}: {title}")
    print("=" * 60)


def print_result(result: dict):
    """Print status and content from a tool result."""
    print(f"\nStatus: {result['status']}")
    if result.get("content"):
        print(result["content"][0]["text"])


def purchase_and_record(query: str):
    """Execute a purchase and record it in the budget tracker."""
    print(f"\nQuery: {query}")

    result = purchase_data_impl(
        payments=payments,
        plan_id=NVM_PLAN_ID,
        seller_url=SELLER_URL,
        query=query,
        agent_id=NVM_AGENT_ID,
    )
    print(f"Status: {result['status']}")
    print(f"Credits used: {result.get('credits_used', 0)}")
    if result.get("content"):
        print(f"Response: {result['content'][0]['text'][:500]}...")

    if result.get("status") == "success":
        budget.record_purchase(result["credits_used"], SELLER_URL, query)

    return result


def main():
    """Run the step-by-step buyer demo."""
    print("=" * 60)
    print("x402 Buyer Flow — Data Buying Agent")
    print("=" * 60)
    print(f"\nSeller: {SELLER_URL}")
    print(f"Plan ID: {NVM_PLAN_ID}")

    print_step(1, "Discover seller pricing tiers")
    print_result(discover_pricing_impl(SELLER_URL))

    print_step(2, "Check credit balance")
    print_result(check_balance_impl(payments, NVM_PLAN_ID))

    print_step(3, "Purchase data — simple search (1 credit)")
    purchase_and_record("AI agent market trends 2025")

    print_step(4, "Purchase data — research report (10 credits)")
    query2 = "Conduct deep research on autonomous agent economies and pricing models"
    allowed, reason = budget.can_spend(10)
    print(f"\nBudget check: {'OK' if allowed else reason}")
    if allowed:
        purchase_and_record(query2)

    print_step(5, "Review budget")
    print(f"\n{pretty_json(budget.get_status())}")

    print(f"\n{'=' * 60}")
    print("FLOW COMPLETE!")
    print("=" * 60)
    print(
        """
x402 Buyer Flow Summary:
1. GET  /pricing              -> Discovered pricing tiers
2. Checked NVM balance        -> Credit balance and subscriber status
3. POST /data (search query)  -> Purchased data (1 credit)
4. POST /data (research query)-> Purchased data (10 credits)
5. Reviewed budget            -> Daily spend tracking
"""
    )


if __name__ == "__main__":
    main()
