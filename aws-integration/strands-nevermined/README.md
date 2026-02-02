# Strands SDK + Nevermined Integration

Integrate Nevermined payment capabilities into AWS Strands agents.

## Overview

[Strands](https://github.com/awslabs/strands-agents) is AWS's agent framework. This integration shows how to add Nevermined payment verification to your Strands agents.

## Prerequisites

```bash
pip install strands-agents payments-py
```

## Basic Integration

### Payment Tool

Add payment verification as a tool:

```python
import os
from strands import Agent
from strands.tools import tool
from payments_py import Payments, PaymentOptions

# Initialize Nevermined
payments = Payments.get_instance(
    PaymentOptions(
        nvm_api_key=os.environ.get("NVM_API_KEY"),
        environment=os.environ.get("NVM_ENVIRONMENT", "sandbox")
    )
)

PLAN_ID = os.environ.get("NVM_PLAN_ID")


@tool
def verify_payment(payment_token: str) -> dict:
    """Verify a payment token before executing paid operations.

    Args:
        payment_token: The x402 access token from the client

    Returns:
        Verification result with success status
    """
    result = payments.facilitator.verify_permissions(
        plan_id=PLAN_ID,
        access_token=payment_token
    )
    return {
        "success": result.get("success", False),
        "agent_request_id": result.get("agent_request_id"),
        "balance": result.get("balance"),
    }


@tool
def settle_payment(payment_token: str, credits: int = 1) -> dict:
    """Settle a payment after successful execution.

    Args:
        payment_token: The x402 access token
        credits: Number of credits to burn

    Returns:
        Settlement result
    """
    result = payments.facilitator.settle_permissions(
        plan_id=PLAN_ID,
        access_token=payment_token,
        credits=credits
    )
    return {
        "success": result.get("success", False),
        "credits_burned": result.get("credits_burned"),
    }


@tool
def premium_data_lookup(query: str, payment_token: str) -> str:
    """Look up premium data (requires payment).

    Args:
        query: The search query
        payment_token: x402 access token for payment

    Returns:
        Search results
    """
    # Verify payment first
    verification = payments.facilitator.verify_permissions(
        plan_id=PLAN_ID,
        access_token=payment_token
    )

    if not verification.get("success"):
        return "Payment verification failed. Please provide a valid payment token."

    # Execute the paid operation
    results = perform_lookup(query)

    # Settle the payment
    payments.facilitator.settle_permissions(
        plan_id=PLAN_ID,
        access_token=payment_token,
        credits=1
    )

    return f"Results for '{query}': {results}"


def perform_lookup(query: str) -> str:
    """Your actual lookup logic here."""
    return f"Data for {query}..."


# Create agent with payment tools
agent = Agent(
    tools=[verify_payment, settle_payment, premium_data_lookup],
    system_prompt="""You are a data assistant that provides premium data lookups.
    For premium operations, you must verify payment using the provided payment token.
    Always verify payment before executing paid operations and settle after completion."""
)
```

### Using the Agent

```python
# Client provides payment token
payment_token = "nvm:access_token_here"

result = agent(f"""
    I need premium data lookup for "market trends Q1 2024".
    My payment token is: {payment_token}
""")

print(result.message)
```

## Advanced Patterns

### Payment Middleware

Wrap all tools with payment verification:

```python
from functools import wraps

def requires_payment(credits: int = 1):
    """Decorator to require payment for a tool."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            payment_token = kwargs.get("payment_token")
            if not payment_token:
                return {"error": "Payment token required"}

            # Verify
            verification = payments.facilitator.verify_permissions(
                plan_id=PLAN_ID,
                access_token=payment_token
            )

            if not verification.get("success"):
                return {"error": "Payment verification failed"}

            # Execute
            result = func(*args, **kwargs)

            # Settle
            payments.facilitator.settle_permissions(
                plan_id=PLAN_ID,
                access_token=payment_token,
                credits=credits
            )

            return result
        return wrapper
    return decorator


@tool
@requires_payment(credits=5)
def expensive_analysis(data: str, payment_token: str) -> dict:
    """Perform expensive analysis (5 credits)."""
    return {"analysis": f"Analysis of {data}"}
```

### Multi-Tier Pricing

```python
PRICING_TIERS = {
    "basic": {"plan_id": "plan-basic", "credits": 1},
    "standard": {"plan_id": "plan-standard", "credits": 5},
    "premium": {"plan_id": "plan-premium", "credits": 10},
}


@tool
def tiered_service(query: str, tier: str, payment_token: str) -> dict:
    """Service with tiered pricing.

    Args:
        query: The query to process
        tier: Pricing tier (basic, standard, premium)
        payment_token: Payment token
    """
    tier_config = PRICING_TIERS.get(tier, PRICING_TIERS["basic"])

    # Verify with correct plan
    verification = payments.facilitator.verify_permissions(
        plan_id=tier_config["plan_id"],
        access_token=payment_token
    )

    if not verification.get("success"):
        return {"error": f"Payment verification failed for {tier} tier"}

    # Execute with tier-appropriate logic
    result = process_with_tier(query, tier)

    # Settle
    payments.facilitator.settle_permissions(
        plan_id=tier_config["plan_id"],
        access_token=payment_token,
        credits=tier_config["credits"]
    )

    return result
```

## Error Handling

```python
@tool
def safe_paid_operation(query: str, payment_token: str) -> dict:
    """Paid operation with proper error handling."""
    try:
        # Verify
        verification = payments.facilitator.verify_permissions(
            plan_id=PLAN_ID,
            access_token=payment_token
        )

        if not verification.get("success"):
            return {
                "success": False,
                "error": "Payment verification failed",
                "details": verification.get("error")
            }

        # Execute
        try:
            result = do_work(query)
        except Exception as e:
            # Don't charge for failed execution
            return {
                "success": False,
                "error": f"Execution failed: {e}",
                "charged": False
            }

        # Settle only on success
        settlement = payments.facilitator.settle_permissions(
            plan_id=PLAN_ID,
            access_token=payment_token,
            credits=1
        )

        return {
            "success": True,
            "result": result,
            "credits_charged": settlement.get("credits_burned", 1)
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Payment system error: {e}"
        }
```

## Related Resources

- [Strands SDK Documentation](https://github.com/awslabs/strands-agents)
- [AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
- [Nevermined Python SDK](https://github.com/nevermined-io/payments-py)
