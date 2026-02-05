# Autonomous Business Hackathon

Starter kits and resources for the **Autonomous Business Hackathon** (March 5-6, San Francisco) hosted by AWS.

Build AI agents that can buy, sell, and transact autonomously using Nevermined payment infrastructure.

## Quick Start

1. **Choose a starter kit** from the [Starter Kits](#starter-kits) section
2. **Set up your environment** with Nevermined credentials
3. **Run the example** and start building!

## Prerequisites

- Node.js 18+ (for TypeScript kits)
- Python 3.10+ (for Python kits)
- [Nevermined App account](https://nevermined.app) for API keys and payment plans
- OpenAI API key (or other LLM provider)

## Environment Setup

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your credentials
# NVM_API_KEY - Get from https://nevermined.app Settings > API Keys
# NVM_PLAN_ID - Create a plan in the Nevermined App
# OPENAI_API_KEY - Your OpenAI API key
```

## Hackathon Tracks

| Track | Theme | Description | Starter Kits |
|-------|-------|-------------|--------------|
| **1** | Data Marketplace | Autonomous data buying/selling agents | A, B, C |
| **2** | Internal A2A Economy | Agent-to-agent transactions within organizations | F, G, H, I |
| **3** | Content Marketplace | Content publishing and consumption | D, E |
| **4** | Open Track | Any creative use case | Any |

## Starter Kits

### Track 1: Data Marketplace (Priority)

| Kit | Name | Description | Languages |
|-----|------|-------------|-----------|
| **A** | [Buyer Agent](./starter-kits/kit-a-buyer-agent/) | Discovers and purchases data autonomously | TS, Python |
| **B** | [Selling Agent](./starter-kits/kit-b-selling-agent/) | Registers and sells data/services | TS, Python |
| **C** | [Switching Agent](./starter-kits/kit-c-switching-agent/) | Switches between data providers based on price/quality | TS |

### Track 2: Internal A2A Economy

| Kit | Name | Description | Languages |
|-----|------|-------------|-----------|
| **F** | [Quality Assessment](./starter-kits/kit-f-quality-assessment/) | Evaluates data/service quality | TS |
| **G** | [Requesting Agent](./starter-kits/kit-g-requesting-agent/) | Requests services from other agents | TS |
| **H** | [Servicing Agent](./starter-kits/kit-h-servicing-agent/) | Provides services to other agents | TS |
| **I** | [ROI Governor](./starter-kits/kit-i-roi-governor/) | Monitors and optimizes agent spending | TS |

### Track 3: Content Marketplace

| Kit | Name | Description | Languages |
|-----|------|-------------|-----------|
| **D** | [Publisher Agent](./starter-kits/kit-d-publisher-agent/) | Publishes content with tiered pricing | TS |
| **E** | [Consuming Agent](./starter-kits/kit-e-consuming-agent/) | Discovers and consumes paid content | TS |

## Demo Agents

Complete working agents in the [`agents/`](./agents/) directory:

| Agent | Description | Stack |
|-------|-------------|-------|
| [strands-simple-agent](./agents/strands-simple-agent/) | Strands AI agent with x402 payment-protected tools and full payment discovery flow | Python, Strands SDK, Nevermined |

## Protocol Overview

### x402 (HTTP Payment Protocol)

Used by Kits A, B, C, D, E. Payment negotiation via HTTP headers:

```
Client sends: payment-signature header with access token
Server returns: 402 with payment-required header (if no token)
Server returns: 200 with payment-response header (after settlement)
```

### A2A (Agent-to-Agent)

Used by Kits F, G, H, I. Direct agent-to-agent transactions.

### MCP (Model Context Protocol)

Used by Kit D. Tool/plugin monetization with logical URLs.

## AWS Integration

This hackathon is hosted by AWS. See [aws-integration/](./aws-integration/) for:

- **Strands SDK + Nevermined**: Add payments to Strands agents
- **AgentCore Deployment**: Deploy agents to AWS AgentCore

## Resources

- [Getting Started Guide](./docs/getting-started.md)
- [AWS Integration Guide](./docs/aws-integration.md)
- [Track 1: Data Marketplace](./docs/tracks/track-1-data-marketplace.md)
- [Track 2: Internal A2A Economy](./docs/tracks/track-2-internal-a2a.md)
- [Track 3: Content Marketplace](./docs/tracks/track-3-content-marketplace.md)

## External Links

- [Nevermined Documentation](https://nevermined.ai/docs)
- [Nevermined App](https://nevermined.app)
- [x402 Protocol Spec](https://github.com/coinbase/x402)
- [AWS AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)

## Support

- **Nevermined Discord**: [Join Community](https://discord.com/invite/GZju2qScKq)
- **Hackathon Slack**: Check event communications

## License

MIT
