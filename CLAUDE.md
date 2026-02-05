# CLAUDE.md - Autonomous Business Hackathon

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Repository containing starter kits and resources for the **Autonomous Business Hackathon** (March 5-6, SF) hosted by AWS. The hackathon focuses on building AI agents with Nevermined payment integration.

## MCP Server Integration

Connect to Nevermined docs for AI-assisted development ("vibe coding"):

### Claude Desktop

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "nevermined": {
      "url": "https://docs.nevermined.app/mcp"
    }
  }
}
```

### Claude Code

```json
{
  "mcpServers": {
    "nevermined": {
      "url": "https://docs.nevermined.app/mcp"
    }
  }
}
```

### LLM Context Resources

- **MCP Server**: https://docs.nevermined.app/mcp
- **Context File**: https://docs.nevermined.app/assets/nevermined_mcp_for_llms.txt

---

## Hackathon Tracks

| Track | Theme | Focus |
|-------|-------|-------|
| **Track 1** | Data Marketplace | Autonomous data buying/selling agents (Kits A, B, C) |
| **Track 2** | Internal A2A Economy | Agent-to-agent transactions within organizations (Kits F, G, H, I) |
| **Track 3** | Content Marketplace | Content publishing and consumption agents (Kits D, E) |
| **Track 4** | Open Track | Any creative use case |

---

## Starter Kit Matrix

| Kit | Name | Track | Protocol | Language |
|-----|------|-------|----------|----------|
| A | Buyer Agent | 1 | x402 | TypeScript, Python |
| B | Selling Agent | 1 | x402 | TypeScript, Python |
| C | Switching Agent | 1 | x402 | TypeScript |
| D | Publisher Agent | 3 | MCP/x402 | TypeScript |
| E | Consuming Agent | 3 | x402 | TypeScript |
| F | Quality Assessment | 2 | A2A | TypeScript |
| G | Requesting Agent | 2 | A2A | TypeScript |
| H | Servicing Agent | 2 | A2A | TypeScript |
| I | ROI Governor | 2 | A2A | TypeScript |

---

## Environment Setup

### Required Environment Variables

```bash
# .env file
# Nevermined credentials (required)
NVM_API_KEY=nvm:your-api-key
NVM_ENVIRONMENT=sandbox          # or 'live', 'staging_sandbox'
NVM_PLAN_ID=your-plan-id
NVM_AGENT_ID=your-agent-id       # optional

# LLM Provider (for AI agents)
OPENAI_API_KEY=sk-your-key

# AWS (for AgentCore deployment)
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

### Get Your Nevermined API Key

1. Go to [https://nevermined.app/](https://nevermined.app/)
2. Log in (Web3Auth with Google, email, or crypto wallet)
3. Navigate to Settings > API Keys
4. Generate a new key and copy it

### Create a Payment Plan

1. In the Nevermined App, go to "My agents" or "My pricing plans"
2. Register your agent with metadata
3. Create a payment plan (credit-based, time-based, or trial)
4. Copy the `planId` for your environment variables

---

## Protocol Quick Reference

### x402 (HTTP Payment Protocol)

The x402 protocol uses HTTP headers for payment negotiation:

| Header | Direction | Description |
|--------|-----------|-------------|
| `payment-signature` | Client -> Server | x402 access token |
| `payment-required` | Server -> Client (402) | Payment requirements (base64 JSON) |
| `payment-response` | Server -> Client (200) | Settlement receipt (base64 JSON) |

**TypeScript Example:**

```typescript
import { Payments } from "@nevermined-io/payments";
import { paymentMiddleware } from "@nevermined-io/payments/express";

const payments = Payments.getInstance({
  nvmApiKey: process.env.NVM_API_KEY,
  environment: "sandbox",
});

app.use(paymentMiddleware(payments, {
  "POST /ask": { planId: PLAN_ID, credits: 1 },
}));
```

**Python Example:**

```python
from payments_py import Payments, PaymentOptions
from payments_py.x402.fastapi import PaymentMiddleware

payments = Payments.get_instance(
    PaymentOptions(nvm_api_key=NVM_API_KEY, environment="sandbox")
)

app.add_middleware(
    PaymentMiddleware,
    payments=payments,
    routes={"POST /ask": {"plan_id": PLAN_ID, "credits": 1}},
)
```

### A2A (Agent-to-Agent Protocol)

For autonomous agent-to-agent transactions. See `tutorials/a2a-examples/` for patterns.

### MCP (Model Context Protocol)

For tool/plugin monetization. Logical URLs follow: `mcp://<serverName>/<typeName>/<methodName>`

Example: `mcp://weather-mcp/tools/weather.today`

---

## AWS Integration

### Strands SDK + Nevermined

Integrate Nevermined payments into Strands agents using the `@requires_payment` decorator:

```python
from strands import Agent, tool
from payments_py import Payments, PaymentOptions
from payments_py.x402.strands import requires_payment

payments = Payments.get_instance(
    PaymentOptions(nvm_api_key=NVM_API_KEY, environment="sandbox")
)

@tool(context=True)
@requires_payment(payments=payments, plan_id=PLAN_ID, credits=1)
def my_tool(query: str, tool_context=None) -> dict:
    """My payment-protected tool."""
    return {"status": "success", "content": [{"text": f"Result: {query}"}]}

agent = Agent(tools=[my_tool])
state = {"payment_token": "x402-access-token"}
result = agent("Do something", invocation_state=state)
```

See `agents/strands-simple-agent/` for a complete working example.

### AgentCore Deployment

Deploy payment-enabled agents to AWS AgentCore:

```python
from bedrock_agentcore import BedrockAgentCoreApp
from payments_py import Payments

app = BedrockAgentCoreApp()
payments = Payments.get_instance(...)

@app.entrypoint
def invoke(payload):
    # Verify payment and execute
    result = process_request(payload)
    return {"result": result}
```

Reference: https://github.com/awslabs/amazon-bedrock-agentcore-samples

---

## Common Commands

### TypeScript Kits

```bash
# Install dependencies
yarn install

# Run the agent (server)
yarn agent

# Run the client
yarn client

# Build
yarn build
```

### Python Kits

```bash
# Install dependencies
poetry install

# Run the agent (server)
poetry run agent

# Run the client
poetry run client
```

---

## Repository Structure

```
hackathons/
├── CLAUDE.md                    # This file
├── README.md                    # Overview and getting started
├── .gitignore
├── .env.example
├── docs/
│   ├── getting-started.md
│   ├── aws-integration.md
│   └── tracks/
│       ├── track-1-data-marketplace.md
│       ├── track-2-internal-a2a.md
│       ├── track-3-content-marketplace.md
│       └── track-4-open.md
├── starter-kits/
│   ├── shared/                  # Common utilities
│   ├── kit-a-buyer-agent/
│   ├── kit-b-selling-agent/
│   ├── kit-c-switching-agent/
│   ├── kit-d-publisher-agent/
│   ├── kit-e-consuming-agent/
│   ├── kit-f-quality-assessment/
│   ├── kit-g-requesting-agent/
│   ├── kit-h-servicing-agent/
│   └── kit-i-roi-governor/
├── agents/                      # Independent agent projects
│   └── strands-simple-agent/    # Strands + Nevermined x402 demo
├── aws-integration/
│   ├── strands-nevermined/      # Strands SDK + Nevermined
│   └── agentcore-deployment/    # AgentCore deploy scripts
└── examples/                    # Complete working demos
```

### Agents Directory

Each subfolder under `agents/` is an independent agent project with its own `pyproject.toml` (poetry).

- `strands-simple-agent/` - Strands agent with x402 payment-protected tools
  - Install: `poetry install`
  - Run agent: `poetry run python agent.py`
  - Run demo: `poetry run python demo.py`

---

## Related Resources

- [Nevermined Documentation](https://nevermined.ai/docs)
- [Nevermined App](https://nevermined.app)
- [Payments TypeScript SDK](https://github.com/nevermined-io/payments)
- [Payments Python SDK](https://github.com/nevermined-io/payments-py)
- [x402 Protocol Spec](https://github.com/coinbase/x402)
- [AWS AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)

---

## Support

- **Discord**: [Join Nevermined Community](https://discord.com/invite/GZju2qScKq)
- **Hackathon Slack**: Check event communications
