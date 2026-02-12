"""
Scripted A2A buyer demo — step-by-step A2A payment flow without LLM.

Demonstrates the complete buyer-side A2A flow:
1. Fetch agent card from /.well-known/agent.json
2. Parse payment extension (planId, credits, agentId)
3. Check credit balance
4. Send A2A message via PaymentsClient with auto-payment
5. Display response and settlement info

Usage:
    # First start the seller in A2A mode:
    #   cd ../seller-simple-agent && poetry run agent-a2a
    # Then run this client:
    poetry run client-a2a
"""

import asyncio
import json
import os
import sys
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()

from a2a.types import Message, MessageSendParams, Role

from payments_py import Payments, PaymentOptions

from .tools.discover_a2a import discover_agent_impl
from .tools.balance import check_balance_impl

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


async def send_a2a_message(plan_id: str, agent_id: str, query: str) -> dict:
    """Send an A2A message and return the result."""
    client = payments.a2a.get_client(
        agent_base_url=SELLER_A2A_URL,
        agent_id=agent_id,
        plan_id=plan_id,
    )

    message = Message(
        message_id=str(uuid4()),
        role=Role.user,
        parts=[{"kind": "text", "text": query}],
    )

    params = MessageSendParams(message=message)
    print(f"\nSending A2A message: {query}")

    result = await client.send_message(params)

    # Extract response
    response_text = ""
    credits_used = 0

    if result and hasattr(result, "status") and result.status:
        status = result.status
        if hasattr(status, "message") and status.message:
            for part in getattr(status.message, "parts", []):
                if hasattr(part, "root"):
                    part = part.root
                if hasattr(part, "text"):
                    response_text += part.text
                elif isinstance(part, dict) and part.get("kind") == "text":
                    response_text += part.get("text", "")
        if hasattr(status, "metadata"):
            metadata = status.metadata or {}
            credits_used = metadata.get("creditsUsed", 0)

    return {
        "response": response_text or "No response text",
        "credits_used": credits_used,
    }


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
    try:
        result = asyncio.run(
            send_a2a_message(plan_id, agent_id, "AI agent market trends 2025")
        )
        print(f"\nCredits used: {result['credits_used']}")
        print(f"Response: {result['response'][:500]}...")
    except Exception as e:
        print(f"\nA2A message failed: {e}")

    # Step 5: Summary
    print_step(5, "Summary")
    print(
        """
A2A Buyer Flow Summary:
1. GET  /.well-known/agent.json  -> Discovered agent card + payment info
2. Parsed payment extension      -> Plan ID, Agent ID, credits
3. Checked NVM balance           -> Credit balance and subscriber status
4. A2A message (with auto-pay)   -> Sent query, got response
"""
    )

    print("=" * 60)
    print("FLOW COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
