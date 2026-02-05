# Strands Simple Agent with Nevermined Payments

A demo Strands AI agent with tools protected by Nevermined x402 payment verification.

## Overview

This example shows how to use the `@requires_payment` decorator from `payments-py` to protect Strands agent tools with x402 payment verification and settlement. Each tool invocation:

1. Extracts the x402 payment token from the agent's invocation state
2. Verifies the subscriber has sufficient credits via Nevermined
3. Executes the tool
4. Settles (burns) credits after successful execution

When no payment token is provided, the tool returns an x402-compliant error containing the full `PaymentRequired` object, allowing clients to discover accepted plans and acquire the correct token.

## Setup

```bash
# Install dependencies
poetry install

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your Nevermined API key, plan ID, etc.
```

## Usage

### 1. Run the x402 discovery flow (demo.py)

The demo demonstrates the full x402 payment negotiation:

```bash
poetry run python demo.py
```

This will:
1. Call the agent **without** a payment token
2. Receive a `PaymentRequired` error with accepted plans
3. Choose a plan from the `accepts` array
4. Generate an x402 access token for that plan
5. Call the agent **with** the payment token

### 2. Run the agent directly (agent.py)

```bash
poetry run python agent.py
```

### Programmatic usage

```python
from strands import Agent, tool
from payments_py import Payments, PaymentOptions
from payments_py.x402.strands import requires_payment, extract_payment_required

payments = Payments.get_instance(
    PaymentOptions(nvm_api_key="nvm:...", environment="sandbox")
)

@tool
@requires_payment(payments=payments, plan_id="your-plan-id", credits=1)
def my_tool(query: str, tool_context=None) -> dict:
    """My payment-protected tool."""
    return {"status": "success", "content": [{"text": f"Result: {query}"}]}

agent = Agent(tools=[my_tool])

# First call without token — triggers PaymentRequired error
result = agent("Do something")

# Extract PaymentRequired from agent conversation history
payment_required = extract_payment_required(agent.messages)
# payment_required["accepts"][0]["planId"] contains the plan to subscribe to

# Then call with a valid token
result = agent("Do something", payment_token="x402-access-token")
```

## Tools

| Tool               | Credits | Description               |
|--------------------|---------|---------------------------|
| `analyze_data`     | 1       | Quick data analysis       |
| `premium_report`   | 5       | Detailed analysis report  |

## How it works

The `@requires_payment` decorator wraps Strands `@tool` functions:

- **Token source**: `tool_context.invocation_state["payment_token"]` (set via `agent("prompt", payment_token="...")`)
- **Verification**: Calls `payments.facilitator.verify_permissions()` before tool execution
- **Settlement**: Calls `payments.facilitator.settle_permissions()` after successful execution
- **Payment discovery**: Returns x402-compliant error with `PaymentRequired` when token is missing or invalid

### x402 error format

When payment is missing or verification fails, the tool returns:

```python
{
    "status": "error",
    "content": [
        {"text": "Payment required: missing payment_token ..."},
        {"json": {
            "x402Version": 2,
            "resource": {"url": "analyze_data"},
            "accepts": [
                {"scheme": "nvm:erc4337", "network": "eip155:84532", "planId": "..."}
            ],
            "extensions": {}
        }}
    ]
}
```

This follows the [x402 MCP transport spec](https://github.com/coinbase/x402/blob/main/specs/transports-v2/mcp.md) pattern: error result with both a human-readable text block and a structured JSON block containing the `PaymentRequired` object.
