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


def main():
    """Run the step-by-step buyer demo."""
    print("=" * 60)
    print("x402 Buyer Flow — Data Buying Agent")
    print("=" * 60)
    print(f"\nSeller: {SELLER_URL}")
    print(f"Plan ID: {NVM_PLAN_ID}")

    # Step 1: Discover pricing
    print("\n" + "=" * 60)
    print("STEP 1: Discover seller pricing tiers")
    print("=" * 60)

    pricing = discover_pricing_impl(SELLER_URL)
    print(f"\nStatus: {pricing['status']}")
    if pricing.get("content"):
        print(pricing["content"][0]["text"])

    # Step 2: Check balance
    print("\n" + "=" * 60)
    print("STEP 2: Check credit balance")
    print("=" * 60)

    balance = check_balance_impl(payments, NVM_PLAN_ID)
    print(f"\nStatus: {balance['status']}")
    if balance.get("content"):
        print(balance["content"][0]["text"])

    # Step 3: Purchase — simple search (1 credit)
    print("\n" + "=" * 60)
    print("STEP 3: Purchase data — simple search (1 credit)")
    print("=" * 60)

    query1 = "AI agent market trends 2025"
    print(f"\nQuery: {query1}")

    result1 = purchase_data_impl(
        payments=payments,
        plan_id=NVM_PLAN_ID,
        seller_url=SELLER_URL,
        query=query1,
        agent_id=NVM_AGENT_ID,
    )
    print(f"Status: {result1['status']}")
    print(f"Credits used: {result1.get('credits_used', 0)}")
    if result1.get("content"):
        response_text = result1["content"][0]["text"]
        print(f"Response: {response_text[:500]}...")

    if result1.get("status") == "success":
        budget.record_purchase(result1["credits_used"], SELLER_URL, query1)

    # Step 4: Purchase — research query (10 credits)
    print("\n" + "=" * 60)
    print("STEP 4: Purchase data — research report (10 credits)")
    print("=" * 60)

    query2 = "Conduct deep research on autonomous agent economies and pricing models"
    print(f"\nQuery: {query2}")

    allowed, reason = budget.can_spend(10)
    print(f"Budget check: {'OK' if allowed else reason}")

    if allowed:
        result2 = purchase_data_impl(
            payments=payments,
            plan_id=NVM_PLAN_ID,
            seller_url=SELLER_URL,
            query=query2,
            agent_id=NVM_AGENT_ID,
        )
        print(f"Status: {result2['status']}")
        print(f"Credits used: {result2.get('credits_used', 0)}")
        if result2.get("content"):
            response_text = result2["content"][0]["text"]
            print(f"Response: {response_text[:500]}...")

        if result2.get("status") == "success":
            budget.record_purchase(result2["credits_used"], SELLER_URL, query2)

    # Step 5: Review budget
    print("\n" + "=" * 60)
    print("STEP 5: Review budget")
    print("=" * 60)

    status = budget.get_status()
    print(f"\n{pretty_json(status)}")

    # Summary
    print("\n" + "=" * 60)
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
