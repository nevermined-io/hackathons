"""
Full x402 payment discovery and token acquisition demo.

Demonstrates the complete x402 flow:
1. Call the agent WITHOUT a payment token
2. Extract PaymentRequired from agent.messages using extract_payment_required()
3. Choose a plan from the accepts array
4. Generate an x402 access token for that plan
5. Call the agent again WITH the payment token

Usage:
    poetry run python demo.py
"""

from agent import agent, payments
from payments_py.x402.strands import extract_payment_required


def main():
    """Demonstrate the x402 payment discovery flow."""
    prompt = "Analyze the latest sales trends for Q4"

    # Step 1: Call the agent WITHOUT a payment token
    print("Step 1: Calling agent without payment token...")
    print(f"  Prompt: {prompt}\n")

    result = agent(prompt)  # No payment_token — will trigger 402

    # The agent's tool returns an error with PaymentRequired in the
    # content blocks. The LLM sees this and relays it in natural language.
    print(f"  Agent response: {result}")
    print()

    # Step 2: Extract PaymentRequired from agent.messages
    print("Step 2: Extracting PaymentRequired from agent.messages...")
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

    print(f"Step 3: Acquiring x402 access token for plan {plan_id}...")

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
    print("Step 4: Calling agent with payment token...")
    print(f"  Prompt: {prompt}\n")

    result = agent(prompt, payment_token=access_token)
    print(f"  Agent response: {result}")


if __name__ == "__main__":
    main()
