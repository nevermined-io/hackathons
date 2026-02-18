# AgentCore Deployment

Deploy payment-enabled agents to AWS AgentCore.

## Overview

AWS AgentCore provides managed infrastructure for deploying AI agents. This guide shows how to deploy Nevermined payment-enabled agents.

## Prerequisites

- AWS account with AgentCore access
- AWS CLI configured
- Docker installed
- Nevermined API key and plan

## Project Structure

```
my-agent/
├── agent.py              # Agent with Nevermined integration
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container definition
├── agentcore.yaml       # AgentCore configuration
└── .env.example         # Environment template
```

## Agent Implementation

### agent.py

```python
"""Payment-enabled agent for AgentCore deployment."""
import os
import logging
from bedrock_agentcore import BedrockAgentCoreApp
from payments_py import Payments, PaymentOptions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()

# Initialize Nevermined
payments = Payments.get_instance(
    PaymentOptions(
        nvm_api_key=os.environ.get("NVM_API_KEY"),
        environment=os.environ.get("NVM_ENVIRONMENT", "sandbox")
    )
)

PLAN_ID = os.environ.get("NVM_PLAN_ID")


@app.entrypoint
def invoke(payload: dict) -> dict:
    """Main entry point for the agent.

    Args:
        payload: Request payload containing:
            - prompt: The user's request
            - payment_token: x402 access token (optional)

    Returns:
        Response with result or error
    """
    prompt = payload.get("prompt", "")
    payment_token = payload.get("payment_token")

    logger.info(f"Processing request: {prompt[:50]}...")

    # Check if this is a paid request
    if payment_token:
        # Verify payment
        verification = payments.facilitator.verify_permissions(
            plan_id=PLAN_ID,
            access_token=payment_token
        )

        if not verification.get("success"):
            logger.warning("Payment verification failed")
            return {
                "success": False,
                "error": "Payment verification failed",
                "payment_required": True,
                "plan_id": PLAN_ID
            }

        logger.info(f"Payment verified: {verification.get('agent_request_id')}")
    else:
        # Return payment requirements for paid endpoints
        return {
            "success": False,
            "error": "Payment token required",
            "payment_required": True,
            "plan_id": PLAN_ID
        }

    # Execute agent logic
    try:
        result = process_request(prompt)

        # Settle payment
        settlement = payments.facilitator.settle_permissions(
            plan_id=PLAN_ID,
            access_token=payment_token,
            credits=1
        )

        logger.info(f"Payment settled: {settlement.get('credits_burned')} credits")

        return {
            "success": True,
            "result": result,
            "credits_used": settlement.get("credits_burned", 1)
        }

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def process_request(prompt: str) -> str:
    """Your agent's business logic here.

    Replace this with your actual implementation:
    - LLM calls
    - Data processing
    - External API calls
    - etc.
    """
    # Example: Echo back the prompt
    return f"Processed: {prompt}"


if __name__ == "__main__":
    app.run()
```

### requirements.txt

```
bedrock-agentcore>=0.1.0
payments-py>=0.1.0
python-dotenv>=1.0.0
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the agent
CMD ["python", "agent.py"]
```

### agentcore.yaml

```yaml
name: payment-enabled-agent
version: 1.0.0
runtime: python3.11

# Entry point
entrypoint: agent:invoke

# Environment variables (from secrets/config)
environment:
  NVM_API_KEY: ${NVM_API_KEY}
  NVM_PLAN_ID: ${NVM_PLAN_ID}
  NVM_ENVIRONMENT: ${NVM_ENVIRONMENT:-sandbox}

# Resource configuration
resources:
  memory: 512MB
  timeout: 30s

# Health check
healthcheck:
  path: /health
  interval: 30s

# Scaling (optional)
scaling:
  minInstances: 1
  maxInstances: 10
  targetConcurrency: 10
```

## Deployment

### 1. Set Up Secrets

Store Nevermined credentials in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
    --name hackathon/nevermined \
    --secret-string '{
        "NVM_API_KEY": "sandbox:your-api-key",
        "NVM_PLAN_ID": "your-plan-id",
        "NVM_ENVIRONMENT": "sandbox"
    }'
```

### 2. Build and Push Container

```bash
# Build
docker build -t payment-agent:latest .

# Tag for ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-west-2.amazonaws.com

docker tag payment-agent:latest YOUR_ACCOUNT.dkr.ecr.us-west-2.amazonaws.com/payment-agent:latest

# Push
docker push YOUR_ACCOUNT.dkr.ecr.us-west-2.amazonaws.com/payment-agent:latest
```

### 3. Deploy to AgentCore

```bash
# Install CLI
pip install bedrock-agentcore-cli

# Deploy
agentcore deploy \
    --config agentcore.yaml \
    --secrets hackathon/nevermined \
    --region us-west-2
```

### 4. Test Deployment

```bash
# Invoke without payment (should fail)
agentcore invoke payment-enabled-agent \
    --payload '{"prompt": "Hello"}'

# Expected: {"success": false, "error": "Payment token required", ...}

# Invoke with payment
agentcore invoke payment-enabled-agent \
    --payload '{"prompt": "Hello", "payment_token": "nvm:your-token"}'

# Expected: {"success": true, "result": "Processed: Hello", ...}
```

## Monitoring

### CloudWatch Logs

```bash
# View logs
aws logs tail /aws/agentcore/payment-enabled-agent --follow
```

### Custom Metrics

```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def record_payment_metric(credits_used: int):
    cloudwatch.put_metric_data(
        Namespace='Hackathon/Payments',
        MetricData=[
            {
                'MetricName': 'CreditsUsed',
                'Value': credits_used,
                'Unit': 'Count'
            }
        ]
    )
```

## Troubleshooting

### Payment Verification Fails

1. Check `NVM_API_KEY` is set correctly
2. Verify `NVM_PLAN_ID` matches a valid plan
3. Check the token hasn't expired
4. Verify network connectivity to Nevermined

### Deployment Fails

1. Check Docker image builds locally
2. Verify ECR permissions
3. Check agentcore.yaml syntax
4. Review CloudWatch logs for errors

## Related Resources

- [AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
- [Nevermined Documentation](https://nevermined.ai/docs)
