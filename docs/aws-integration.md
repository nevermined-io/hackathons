# AWS Integration Guide

This guide covers integrating Nevermined payments with AWS services, specifically Strands SDK and AgentCore.

## Overview

AWS provides infrastructure for deploying and running AI agents at scale. Nevermined adds the payment layer, enabling your agents to monetize their services.

**Key integrations:**

- **Strands SDK**: Add payment tools to your Strands agents
- **AgentCore**: Deploy payment-enabled agents to production

## Prerequisites

- AWS account with appropriate permissions
- AWS CLI configured (`aws configure`)
- Nevermined API key and payment plan

## Strands SDK + Nevermined

### Installation

```bash
pip install strands-agents payments-py
```

### Basic Integration

```python
import os
from strands import Agent
from strands.tools import tool
from payments_py import Payments, PaymentOptions

# Initialize Nevermined
payments = Payments.get_instance(
    PaymentOptions(
        nvm_api_key=os.environ.get("NVM_API_KEY"),
        environment="sandbox"
    )
)

PLAN_ID = os.environ.get("NVM_PLAN_ID")


@tool
def paid_data_lookup(query: str) -> str:
    """Look up data (requires payment verification)."""
    # In production, verify payment before executing
    return f"Results for: {query}"


# Create agent with payment-aware tools
agent = Agent(
    tools=[paid_data_lookup],
    system_prompt="You are a data assistant that charges for premium lookups."
)

# Run the agent
result = agent("Find me the latest market data for AAPL")
print(result.message)
```

### Payment Verification in Tools

```python
from payments_py.x402.helpers import build_payment_required

@tool
def premium_analysis(data: str, payment_token: str = None) -> str:
    """Perform premium analysis (payment required)."""

    if not payment_token:
        # Return payment requirements
        requirements = build_payment_required(
            plan_id=PLAN_ID,
            description="Premium data analysis"
        )
        return f"Payment required: {requirements}"

    # Verify the payment token
    verification = payments.facilitator.verify_permissions(
        plan_id=PLAN_ID,
        access_token=payment_token
    )

    if not verification.get("success"):
        return "Payment verification failed"

    # Execute the paid operation
    result = perform_analysis(data)

    # Settle the payment
    payments.facilitator.settle_permissions(
        plan_id=PLAN_ID,
        access_token=payment_token,
        credits=1
    )

    return result
```

## AgentCore Deployment

AWS AgentCore provides managed infrastructure for deploying AI agents.

### Project Structure

```
my-agent/
├── agent.py          # Agent code with Nevermined
├── requirements.txt
├── Dockerfile
└── agentcore.yaml    # AgentCore configuration
```

### Agent Implementation

```python
# agent.py
from bedrock_agentcore import BedrockAgentCoreApp
from payments_py import Payments, PaymentOptions
import os

app = BedrockAgentCoreApp()

# Initialize Nevermined
payments = Payments.get_instance(
    PaymentOptions(
        nvm_api_key=os.environ.get("NVM_API_KEY"),
        environment="sandbox"
    )
)

PLAN_ID = os.environ.get("NVM_PLAN_ID")


@app.entrypoint
def invoke(payload):
    """Main entry point for the agent."""
    prompt = payload.get("prompt", "")
    payment_token = payload.get("payment_token")

    # Verify payment
    if payment_token:
        verification = payments.facilitator.verify_permissions(
            plan_id=PLAN_ID,
            access_token=payment_token
        )

        if not verification.get("success"):
            return {"error": "Payment verification failed"}
    else:
        return {"error": "Payment token required", "plan_id": PLAN_ID}

    # Execute agent logic
    result = process_request(prompt)

    # Settle payment
    payments.facilitator.settle_permissions(
        plan_id=PLAN_ID,
        access_token=payment_token,
        credits=1
    )

    return {"result": result}


def process_request(prompt: str) -> str:
    """Your agent's business logic here."""
    # Add your LLM calls, data processing, etc.
    return f"Processed: {prompt}"


if __name__ == "__main__":
    app.run()
```

### AgentCore Configuration

```yaml
# agentcore.yaml
name: my-payment-agent
version: 1.0.0
runtime: python3.10

environment:
  NVM_API_KEY: ${NVM_API_KEY}
  NVM_PLAN_ID: ${NVM_PLAN_ID}
  NVM_ENVIRONMENT: sandbox

resources:
  memory: 512MB
  timeout: 30s

entrypoint: agent:invoke
```

### Deployment

```bash
# Install AgentCore CLI
pip install bedrock-agentcore-cli

# Deploy the agent
agentcore deploy --config agentcore.yaml
```

## Reference Patterns

The following patterns from [amazon-bedrock-agentcore-samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples) are useful:

### From `03-integrations/strands-agents/`

- Basic Strands agent setup
- Tool definition patterns
- Multi-tool agents

### From `02-use-cases/`

- `enterprise-web-intelligence-agent/` - Web data gathering with cost tracking
- `cost-optimization-agent/` - Budget management patterns
- `market-trends-agent/` - Data marketplace integration

## Best Practices

### 1. Environment Variables

Never hardcode credentials. Use environment variables:

```python
NVM_API_KEY = os.environ.get("NVM_API_KEY")
if not NVM_API_KEY:
    raise ValueError("NVM_API_KEY environment variable required")
```

### 2. Error Handling

Always handle payment failures gracefully:

```python
try:
    verification = payments.facilitator.verify_permissions(...)
except Exception as e:
    logger.error(f"Payment verification failed: {e}")
    return {"error": "Payment service unavailable"}
```

### 3. Idempotency

Use unique request IDs for settlement:

```python
import uuid

request_id = str(uuid.uuid4())
settlement = payments.facilitator.settle_permissions(
    plan_id=PLAN_ID,
    access_token=token,
    credits=1,
    request_id=request_id  # Prevents double-charging
)
```

### 4. Logging

Track all payment operations:

```python
import logging

logger = logging.getLogger(__name__)

logger.info(f"Payment verified: {verification.get('agent_request_id')}")
logger.info(f"Credits used: {settlement.get('credits_burned')}")
```

## Resources

- [AWS AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Strands SDK Documentation](https://github.com/awslabs/strands-agents)
- [AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
- [Nevermined Documentation](https://nevermined.ai/docs)
