"""
Scripted A2A buyer demo — step-by-step A2A payment flow without LLM.

Demonstrates the complete buyer-side A2A flow:
1. Fetch agent card from /.well-known/agent.json
2. Parse payment extension (planId, credits, agentId)
3. Check credit balance
4. Send A2A message via PaymentsClient with automatic x402 payment
5. Display response and settlement info

Usage:
    # First start the seller in A2A mode:
    #   cd ../seller-simple-agent && poetry run agent-a2a
    # Then run this client:
    poetry run client-a2a
"""

import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from payments_py import Payments, PaymentOptions

from .tools.discover_a2a import discover_agent_impl
from .tools.balance import check_balance_impl
from .tools.purchase_a2a import purchase_a2a_impl

SELLER_A2A_URL = os.getenv("SELLER_A2A_URL", "http://localhost:9000")
NVM_API_KEY = os.getenv("NVM_API_KEY", "")
NVM_ENVIRONMENT = os.getenv("NVM_ENVIRONMENT", "sandbox")
NVM_PLAN_ID = os.getenv("NVM_PLAN_ID", "")

if not NVM_API_KEY:
    print("NVM_API_KEY is required.")
    sys.exit(1)

payments = Payments.get_instance(
    PaymentOptions(nvm_api_key=NVM_API_KEY, environment=NVM_ENVIRONMENT)
)


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


def main():
    """Run the step-by-step A2A buyer demo."""
    print("=" * 60)
    print("A2A Buyer Flow — Data Buying Agent")
    print("=" * 60)
    print(f"\nSeller A2A URL: {SELLER_A2A_URL}")

    # Step 1: Discover agent via agent card
    print_step(1, "Fetch agent card (/.well-known/agent.json)")
    discovery = discover_agent_impl(SELLER_A2A_URL)
    print_result(discovery)

    if discovery.get("status") != "success":
        print("\nCannot proceed without agent card. Is the seller running?")
        sys.exit(1)

    # Step 2: Parse payment extension
    print_step(2, "Parse payment extension")
    payment = discovery.get("payment", {})
    plan_id = payment.get("planId", NVM_PLAN_ID)
    agent_id = payment.get("agentId", "")
    min_credits = payment.get("credits", 0)
    cost_desc = payment.get("costDescription", "")

    print(f"\nPlan ID:     {plan_id}")
    print(f"Agent ID:    {agent_id}")
    print(f"Min credits: {min_credits}")
    print(f"Cost info:   {cost_desc}")

    if not plan_id:
        print("\nNo plan ID found. Set NVM_PLAN_ID in .env.")
        sys.exit(1)

    # Step 3: Check balance
    print_step(3, "Check credit balance")
    print_result(check_balance_impl(payments, plan_id))

    # Step 4: Send A2A message
    print_step(4, "Send A2A message — search query")
    result = purchase_a2a_impl(
        payments=payments,
        plan_id=plan_id,
        agent_url=SELLER_A2A_URL,
        agent_id=agent_id,
        query="AI agent market trends 2025",
    )
    print(f"\nStatus: {result['status']}")
    print(f"Credits used: {result.get('credits_used', 0)}")
    if result.get("content"):
        text = result["content"][0]["text"]
        print(f"Response: {text[:500]}{'...' if len(text) > 500 else ''}")

    # Step 5: Summary
    print_step(5, "Summary")
    print(
        """
A2A Buyer Flow Summary:
1. GET  /.well-known/agent.json  -> Discovered agent card + payment info
2. Parsed payment extension      -> Plan ID, Agent ID, credits
3. Checked NVM balance           -> Credit balance and subscriber status
4. A2A message (with x402 token) -> Sent query, got response
"""
    )

    print("=" * 60)
    print("FLOW COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
