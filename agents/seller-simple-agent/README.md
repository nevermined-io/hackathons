# Seller Simple Agent

A data-selling agent with x402 payment-protected tools powered by Strands SDK and Nevermined.

## Overview

This agent demonstrates how to sell data and services with tiered pricing using the `@requires_payment` decorator from `payments-py`. It includes three tools at different price points, two deployment modes, and built-in usage analytics.

## Architecture

```
                    ┌──────────────────────────────────┐
                    │       Strands Agent Core          │
                    │                                   │
                    │  ┌────────────┐  ┌─────────────┐ │
                    │  │search_data │  │summarize_data│ │
                    │  │  (1 credit)│  │  (5 credits) │ │
                    │  └────────────┘  └─────────────┘ │
                    │         ┌──────────────┐         │
                    │         │research_data │         │
                    │         │ (10 credits) │         │
                    │         └──────────────┘         │
                    └──────────┬───────────┬───────────┘
                               │           │
                    ┌──────────▼──┐  ┌─────▼──────────┐
                    │  FastAPI    │  │  AgentCore      │
                    │  + OpenAI   │  │  + Bedrock      │
                    │  (local)    │  │  (AWS)          │
                    └─────────────┘  └────────────────┘
```

## Quick Start

```bash
poetry install
cp .env.example .env
# Edit .env with your credentials

# Option 1: Run as FastAPI server (x402 protected HTTP endpoints)
poetry run agent

# Option 2: Run Strands agent directly (for testing tools)
poetry run demo

# Option 3: Test with client
poetry run client
```

## How It Works

```
┌─────────┐                              ┌─────────┐
│  Client │                              │  Seller │
│ (Buyer) │                              │  Agent  │
└────┬────┘                              └────┬────┘
     │                                        │
     │  1. POST /data (no token)              │
     │───────────────────────────────────────>│
     │                                        │
     │  2. 402 Payment Required               │
     │     Header: payment-required           │
     │<───────────────────────────────────────│
     │                                        │
     │  3. Get x402 token from Nevermined     │
     │                                        │
     │  4. POST /data                         │
     │     Header: payment-signature          │
     │───────────────────────────────────────>│
     │                                        │
     │     - Verify permissions               │
     │     - Process request                  │
     │     - Settle credits                   │
     │                                        │
     │  5. 200 OK + data                      │
     │     Header: payment-response           │
     │<───────────────────────────────────────│
```

## Tool Pricing

| Tool | Credits | Description |
|------|---------|-------------|
| `search_data` | 1 | Quick data lookup — search for specific data points |
| `summarize_data` | 5 | Summarize and analyze a dataset or topic |
| `research_data` | 10 | Deep research — multi-source analysis with citations |

## Deployment Modes

### Local (FastAPI + OpenAI)

Run the agent as a FastAPI server. Payment protection is handled by `@requires_payment` on each Strands tool — the server is a thin HTTP wrapper. Uses OpenAI for LLM inference.

```bash
poetry run agent   # Starts FastAPI on http://localhost:3000
```

### AWS (AgentCore + Bedrock)

Deploy the same agent core to AWS AgentCore. Uses Amazon Bedrock for LLM inference.

```bash
poetry run agent-agentcore
```

Requires AWS credentials and Bedrock model access configured in `.env`.

## Configuration

### Environment Variables

```bash
# Required
NVM_API_KEY=sandbox:your-api-key
NVM_ENVIRONMENT=sandbox
NVM_PLAN_ID=your-plan-id
OPENAI_API_KEY=sk-your-key

# Optional
NVM_AGENT_ID=your-agent-id
MODEL_ID=gpt-4o-mini
PORT=3000
```

### Creating a Payment Plan

1. Go to [https://nevermined.app/](https://nevermined.app/)
2. Navigate to "My Pricing Plans"
3. Create a new plan with:
   - Plan type: Credit-based
   - Endpoints: `POST /data`
   - Price per credit: Set your rate
4. Copy the Plan ID to your `.env`

## API

### POST /data

Query data (payment protected).

**Request Headers:**
```
Content-Type: application/json
payment-signature: <x402-access-token>
```

**Request Body:**
```json
{
  "query": "market data for AAPL"
}
```

**Response (200):**
```json
{
  "response": "Found 5 results for 'market data for AAPL'...",
  "credits_used": 1
}
```

**Response (402 - No Token):**
```json
{
  "error": "Payment Required",
  "message": "Send x402 token in payment-signature header"
}
```

### GET /pricing

Get pricing information.

**Response:**
```json
{
  "planId": "plan-xxx",
  "tiers": {
    "simple": { "credits": 1, "description": "Basic web search", "tool": "search_data" },
    "medium": { "credits": 5, "description": "Content summarization", "tool": "summarize_data" },
    "complex": { "credits": 10, "description": "Full market research", "tool": "research_data" }
  }
}
```

### GET /stats

Get usage statistics.

**Response:**
```json
{
  "totalRequests": 1500,
  "totalCreditsEarned": 7500,
  "uniqueSubscribers": 45,
  "averageCreditsPerRequest": 5
}
```

## Dynamic Pricing

```python
@tool(context=True)
@requires_payment(payments=payments, plan_id=PLAN_ID, credits=1)
def search_data(query: str, tool_context=None) -> dict:
    """Quick data lookup (1 credit)."""
    return {"status": "success", "content": [{"text": f"Results for: {query}"}]}

@tool(context=True)
@requires_payment(payments=payments, plan_id=PLAN_ID, credits=10)
def research_data(query: str, tool_context=None) -> dict:
    """Deep research with citations (10 credits)."""
    return {"status": "success", "content": [{"text": f"Research report: {query}"}]}
```

## A2A Mode

Run the seller as an A2A-compliant agent with standard agent card discovery and payment-protected JSON-RPC messaging.

### Start in A2A Mode

```bash
poetry run agent-a2a   # Starts A2A server on http://localhost:9000
```

### Agent Card

The agent card is served at `/.well-known/agent.json` and includes a `urn:nevermined:payment` extension with plan ID, agent ID, and pricing info.

```bash
curl -s http://localhost:9000/.well-known/agent.json | python3 -m json.tool
```

### How A2A Differs from HTTP Mode

| Aspect | HTTP Mode (`poetry run agent`) | A2A Mode (`poetry run agent-a2a`) |
|--------|-------------------------------|----------------------------------|
| Discovery | `GET /pricing` (custom) | `/.well-known/agent.json` (standard) |
| Communication | REST `POST /data` | A2A JSON-RPC messages |
| Payment handling | `@requires_payment` per tool | `PaymentsRequestHandler` per request |
| Token transport | `payment-signature` header | `payment-signature` header |
| Port | 3000 | 9000 |
| Interoperability | Custom protocol | Any A2A-compatible agent |

### Configuration

Add to your `.env`:

```bash
A2A_PORT=9000  # Default: 9000
```

## Customization Ideas

1. **Swap data sources** — Integrate Exa, Tavily, Apify, or your own APIs
2. **Add domain-specific tools** — Financial data, weather, legal documents, etc.
3. **Dynamic pricing** — Adjust credits based on data freshness, volume, or complexity
4. **Tiered access** — Different data quality at different price points
5. **Subscription discounts** — Lower per-credit cost for frequent users
6. **Data freshness pricing** — Real-time data costs more than historical
7. **Volume discounts** — Reduce price for bulk queries
