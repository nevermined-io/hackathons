"""
Full x402 payment discovery and token acquisition demo (Strands-native, no HTTP).

Demonstrates the complete x402 flow:
1. Call the agent WITHOUT a payment token
2. Extract PaymentRequired from agent.messages
3. Choose a plan from the accepts array
4. Generate an x402 access token for that plan
5. Call the agent again WITH the payment token

Usage:
    poetry run demo
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

from strands.models.openai import OpenAIModel
from payments_py.x402.strands import extract_payment_required

from .agent_core import payments, create_agent

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    print("OPENAI_API_KEY is required. Set it in .env file.")
    sys.exit(1)

# Create agent with OpenAI model
model = OpenAIModel(
    client_args={"api_key": OPENAI_API_KEY},
    model_id=os.getenv("MODEL_ID", "gpt-4o-mini"),
)
agent = create_agent(model)


def main():
    """Demonstrate the x402 payment discovery flow."""
    prompt = "Search for the latest trends in AI agents"

    # Step 1: Call the agent WITHOUT a payment token
    print("=" * 60)
    print("STEP 1: Calling agent without payment token")
    print("=" * 60)
    print(f"  Prompt: {prompt}\n")

    result = agent(prompt)  # No payment_token — will trigger 402

    print(f"  Agent response: {result}")
    print()

    # Step 2: Extract PaymentRequired from agent.messages
    print("=" * 60)
    print("STEP 2: Extracting PaymentRequired from agent.messages")
    print("=" * 60)

    payment_required = extract_payment_required(agent.messages)

    if payment_required is None:
        print("  No PaymentRequired found in agent messages.")
        print("  (The agent may not have called a payment-protected tool.)")
        return

    print(f"  x402Version: {payment_required['x402Version']}")
    print(f"  Accepted plans ({len(payment_required['accepts'])}):")
    for i, scheme in enumerate(payment_required["accepts"]):
        print(
            f"    [{i}] planId={scheme['planId']}, "
            f"scheme={scheme['scheme']}, "
            f"network={scheme['network']}"
        )
    print()

    # Step 3: Choose a plan and get an access token
    chosen_plan = payment_required["accepts"][0]
    plan_id = chosen_plan["planId"]
    agent_id = (chosen_plan.get("extra") or {}).get("agentId")

    print("=" * 60)
    print(f"STEP 3: Acquiring x402 access token for plan {plan_id}")
    print("=" * 60)

    token_response = payments.x402.get_x402_access_token(
        plan_id=plan_id,
        agent_id=agent_id,
    )

    access_token = token_response.get("accessToken")
    if not access_token:
        print("  Failed to get access token. Do you have a subscription?")
        return

    print(f"  Token obtained: {access_token[:30]}...")
    print()

    # Step 4: Call the agent WITH the payment token
    print("=" * 60)
    print("STEP 4: Calling agent with payment token")
    print("=" * 60)
    print(f"  Prompt: {prompt}\n")

    state = {"payment_token": access_token}
    result = agent(prompt, invocation_state=state)
    print(f"  Agent response: {result}")
    print()

    # Step 5: Check settlement result
    print("=" * 60)
    print("STEP 5: Payment settlement")
    print("=" * 60)

    settlement = state.get("payment_settlement")
    if settlement:
        print(f"  Success: {settlement.success}")
        print(f"  Credits redeemed: {settlement.credits_redeemed}")
        print(f"  Remaining balance: {settlement.remaining_balance}")
        print(f"  Network: {settlement.network}")
    else:
        print("  No settlement found (tool may have returned an error)")

    print()
    print("=" * 60)
    print("FLOW COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
