"""
Strands AI agent with Nevermined x402 payment-protected tools.

This demo shows how to use the @requires_payment decorator to protect
Strands agent tools with x402 payment verification and settlement.

Usage:
    poetry run python agent.py
"""

import os

from dotenv import load_dotenv
from strands import Agent, tool

from payments_py import PaymentOptions, Payments
from payments_py.x402.strands import PaymentContext, requires_payment

load_dotenv()

NVM_API_KEY = os.environ["NVM_API_KEY"]
NVM_ENVIRONMENT = os.getenv("NVM_ENVIRONMENT", "sandbox")
NVM_PLAN_ID = os.environ["NVM_PLAN_ID"]
NVM_AGENT_ID = os.getenv("NVM_AGENT_ID")

payments = Payments.get_instance(
    PaymentOptions(nvm_api_key=NVM_API_KEY, environment=NVM_ENVIRONMENT)
)


@tool
@requires_payment(
    payments=payments,
    plan_id=NVM_PLAN_ID,
    credits=1,
    agent_id=NVM_AGENT_ID,
)
def analyze_data(query: str, tool_context=None) -> dict:
    """Analyze data based on a query. Costs 1 credit per request.

    Args:
        query: The data analysis query to process.
    """
    if tool_context:
        ctx = tool_context.invocation_state.get("payment_context")
        if ctx and isinstance(ctx, PaymentContext):
            print(f"  Payment verified. Request ID: {ctx.agent_request_id}")

    return {
        "status": "success",
        "content": [
            {
                "text": f"Analysis complete for query: '{query}'. "
                "Here are the key findings: [simulated results]"
            }
        ],
    }


@tool
@requires_payment(
    payments=payments,
    plan_id=NVM_PLAN_ID,
    credits=5,
    agent_id=NVM_AGENT_ID,
)
def premium_report(topic: str, depth: str = "standard", tool_context=None) -> dict:
    """Generate a premium analysis report. Costs 5 credits per request.

    Args:
        topic: The topic to generate a report about.
        depth: Analysis depth - 'standard' or 'deep'.
    """
    return {
        "status": "success",
        "content": [
            {
                "text": f"Premium {depth} report on '{topic}': "
                "[detailed simulated analysis with charts and recommendations]"
            }
        ],
    }


agent = Agent(
    tools=[analyze_data, premium_report],
    system_prompt=(
        "You are a data analysis agent. You have two tools available:\n"
        "- analyze_data: Quick analysis (1 credit)\n"
        "- premium_report: Detailed report (5 credits)\n"
        "Use the appropriate tool based on the user's request."
    ),
)


def main():
    """Run the agent with payment-protected tools (no token — triggers 402)."""
    print("Starting Strands agent with Nevermined payment protection...")
    print(f"Plan ID: {NVM_PLAN_ID}")
    print(f"Environment: {NVM_ENVIRONMENT}")
    print()

    # Call without payment token — the tool will return an x402
    # PaymentRequired error. Use demo.py for the full discovery flow.
    result = agent("Analyze the latest sales trends for Q4")
    print(f"\nAgent response: {result}")


if __name__ == "__main__":
    main()
