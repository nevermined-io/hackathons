# Data Buying Agent

A Strands AI agent that **discovers sellers, purchases data via x402 payments, and tracks spending** with budget management.

This is the buyer counterpart to the [seller-simple-agent](../seller-simple-agent/). Together they demonstrate a complete autonomous data marketplace.

## Architecture

```
┌─────────────────────────────────────────────┐
│            Strands Agent Core               │
│                                             │
│  ┌──────────────────┐  ┌─────────────────┐  │
│  │ discover_pricing │  │ check_balance   │  │
│  │  (GET /pricing)  │  │ (NVM API +      │  │
│  │                  │  │  local budget)  │  │
│  └──────────────────┘  └─────────────────┘  │
│           ┌─────────────────┐               │
│           │ purchase_data   │               │
│           │ (x402 token +   │               │
│           │  POST /data)    │               │
│           └─────────────────┘               │
└──────────────┬──────────────┬───────────────┘
               │              │
    ┌──────────▼──┐   ┌──────▼──────────┐
    │  CLI Agent  │   │  AgentCore      │
    │  + OpenAI   │   │  + Bedrock      │
    │  (local)    │   │  (AWS)          │
    └─────────────┘   └─────────────────┘
```

## Quick Start

```bash
# Install dependencies
poetry install

# Copy environment file and fill in your credentials
cp .env.example .env

# Start the seller (in another terminal)
cd ../seller-simple-agent && poetry run agent

# Run the interactive agent
poetry run agent

# Or run the scripted demo (no LLM needed)
poetry run client

# Or run the LLM-orchestrated demo
poetry run demo
```

## How It Works

```
Buyer Agent                    Nevermined                    Seller Agent
     │                            │                              │
     │  1. GET /pricing           │                              │
     │───────────────────────────────────────────────────────────>│
     │  <- pricing tiers          │                              │
     │<───────────────────────────────────────────────────────────│
     │                            │                              │
     │  2. Check balance          │                              │
     │───────────────────────────>│                              │
     │  <- credits remaining      │                              │
     │<───────────────────────────│                              │
     │                            │                              │
     │  3. Get x402 access token  │                              │
     │───────────────────────────>│                              │
     │  <- access token           │                              │
     │<───────────────────────────│                              │
     │                            │                              │
     │  4. POST /data + token     │                              │
     │───────────────────────────────────────────────────────────>│
     │                            │  5. Verify & settle          │
     │                            │<─────────────────────────────│
     │                            │  <- settlement receipt       │
     │                            │─────────────────────────────>│
     │  <- data response          │                              │
     │<───────────────────────────────────────────────────────────│
```

## Tools

| Tool | Description | Credits |
|------|-------------|---------|
| `discover_pricing` | GET /pricing from seller — shows tiers and costs | Free |
| `check_balance` | Check NVM credit balance + local budget status | Free |
| `purchase_data` | Generate x402 token, POST /data, return results | Varies by tier |

**Key difference from seller:** Buyer tools are plain `@tool` — NOT `@requires_payment`. The buyer *generates* payment tokens; it doesn't receive them.

## Deployment Modes

### 1. Interactive CLI (local development)

```bash
poetry run agent
```

Uses OpenAI for the LLM. The agent runs a read-eval-print loop where you type queries and it orchestrates the buyer tools.

### 2. Scripted Demo (no LLM)

```bash
poetry run client
```

Step-by-step x402 buyer flow calling tools directly — no LLM needed. Good for testing the payment flow.

### 3. Strands Demo (LLM-orchestrated)

```bash
poetry run demo
```

Pre-scripted prompts that exercise all buyer tools with LLM orchestration.

### 4. AWS AgentCore

```bash
poetry install -E agentcore
poetry run agent-agentcore
```

Uses Bedrock for the LLM. Deploy to AWS AgentCore for production.

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NVM_API_KEY` | Yes | Nevermined **subscriber** API key |
| `NVM_ENVIRONMENT` | Yes | `sandbox`, `staging_sandbox`, or `live` |
| `NVM_PLAN_ID` | Yes | The seller's plan ID you subscribed to |
| `NVM_AGENT_ID` | No | Seller's agent ID (for token scoping) |
| `SELLER_URL` | No | Seller endpoint (default: `http://localhost:3000`) |
| `OPENAI_API_KEY` | Yes* | OpenAI API key (*not needed for `client`) |
| `MODEL_ID` | No | OpenAI model (default: `gpt-4o-mini`) |
| `MAX_DAILY_SPEND` | No | Daily credit limit (0 = unlimited) |
| `MAX_PER_REQUEST` | No | Per-request credit limit (0 = unlimited) |

### Subscribing to a Seller's Plan

Before buying data, you need to subscribe to the seller's plan:

1. Get the seller's **Plan ID** (from their `/pricing` endpoint or the Nevermined App)
2. Go to [nevermined.app](https://nevermined.app) and find the plan
3. Subscribe (purchase credits)
4. Set `NVM_PLAN_ID` in your `.env` to the seller's plan ID
5. Use your **subscriber** API key as `NVM_API_KEY`

## Seller vs Buyer Comparison

| Aspect | Seller | Buyer |
|--------|--------|-------|
| Entry point | FastAPI server (port 3000) | Interactive CLI |
| Tools | `@requires_payment` protected | Plain `@tool` |
| NVM_API_KEY | Builder/seller key | Subscriber key |
| NVM_PLAN_ID | "My plan I created" | "The seller's plan I subscribe to" |
| Payments SDK | Verify + settle tokens | Generate tokens + check balance |
| Tracking | Analytics (earnings) | Budget (spending limits) |
| SELLER_URL | N/A (is the server) | Required (where to buy from) |

## Customization Ideas

1. **Multi-provider comparison** — Query multiple sellers, compare results and prices
2. **Auto-subscribe** — Call `payments.plans.order_plan()` if not yet subscribed
3. **Quality scoring** — Track data quality per seller over time
4. **Caching** — Cache results to avoid duplicate purchases
5. **A2A protocol** — Use agent-to-agent protocol for richer seller discovery
6. **Persistent budget** — Store budget in file/database instead of in-memory

## Related

- [seller-simple-agent](../seller-simple-agent/) — The seller counterpart
- [Kit A: Buyer Agent](../../starter-kits/kit-a-buyer-agent/) — Starter kit docs
- [Kit B: Selling Agent](../../starter-kits/kit-b-selling-agent/) — Seller starter kit
- [Track 1: Data Marketplace](../../docs/tracks/track-1-data-marketplace.md) — Track overview
