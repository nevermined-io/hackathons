# Kit A: Buyer Agent

An autonomous agent that discovers and purchases data from marketplace providers.

**Track:** 1 - Data Marketplace
**Protocol:** x402
**Languages:** TypeScript, Python

## Features

- Budget management (daily/per-request limits)
- Provider discovery and comparison
- Automatic payment execution via x402
- Purchase history tracking
- Cost optimization

## Quick Start

### TypeScript

```bash
cd typescript
yarn install
cp .env.example .env
# Edit .env with your credentials
yarn agent   # Start the buyer agent
yarn demo    # Run the demo
```

### Python

```bash
cd python
poetry install
cp .env.example .env
# Edit .env with your credentials
poetry run agent   # Start the buyer agent
poetry run demo    # Run the demo
```

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Buyer     │────>│  Nevermined  │────>│   Seller    │
│   Agent     │     │   Network    │     │   Agent     │
└─────────────┘     └──────────────┘     └─────────────┘
      │                    │                    │
      │  1. Discover       │                    │
      │     providers      │                    │
      │───────────────────>│                    │
      │                    │                    │
      │  2. Get pricing    │                    │
      │───────────────────>│<───────────────────│
      │                    │                    │
      │  3. Purchase data  │                    │
      │───────────────────>│───────────────────>│
      │                    │                    │
      │  4. Receive data   │                    │
      │<───────────────────│<───────────────────│
```

## Configuration

### Environment Variables

```bash
# Required
NVM_API_KEY=nvm:your-api-key
NVM_ENVIRONMENT=sandbox
OPENAI_API_KEY=sk-your-key

# Budget settings
MAX_DAILY_SPEND=100           # Max credits per day
MAX_PER_REQUEST=10            # Max credits per request
DEFAULT_PROVIDER_PLAN_ID=plan-xxx  # Default provider to use

# Optional
PORT=3000
```

## API

### POST /purchase

Purchase data from a provider.

**Request:**
```json
{
  "providerUrl": "https://provider.example.com",
  "planId": "plan-xxx",
  "query": "market data for AAPL"
}
```

**Response:**
```json
{
  "success": true,
  "data": { ... },
  "cost": {
    "creditsUsed": 5,
    "remainingBudget": 95
  }
}
```

### GET /budget

Get current budget status.

**Response:**
```json
{
  "dailyBudget": 100,
  "dailySpend": 15,
  "remaining": 85,
  "resetAt": "2024-03-06T00:00:00Z"
}
```

### GET /history

Get purchase history.

**Response:**
```json
{
  "purchases": [
    {
      "id": "purchase-123",
      "provider": "https://provider.example.com",
      "query": "market data",
      "creditsUsed": 5,
      "timestamp": "2024-03-05T10:30:00Z"
    }
  ]
}
```

## Customization Ideas

1. **Multi-provider comparison** - Query multiple providers, compare results
2. **Quality scoring** - Track provider quality over time
3. **Dynamic budgeting** - Adjust budget based on data value
4. **Caching** - Cache results to avoid duplicate purchases
5. **Batch purchasing** - Buy multiple data points efficiently

## Next Steps

- Modify the purchase logic for your use case
- Add provider discovery mechanisms
- Implement quality assessment
- Connect with Kit B (Selling Agent) for testing

## Working Implementation

See [`../../agents/buyer-simple-agent/`](../../agents/buyer-simple-agent/) for a complete working implementation with Strands SDK, x402 payment flow, and budget management.

## Related

- [Kit B: Selling Agent](../kit-b-selling-agent/) - Build the seller side
- [Kit C: Switching Agent](../kit-c-switching-agent/) - Multi-provider switching
- [Track 1 Overview](../../docs/tracks/track-1-data-marketplace.md)
