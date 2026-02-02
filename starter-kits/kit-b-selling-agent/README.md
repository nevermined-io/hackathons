# Kit B: Selling Agent

An agent that sells data or services with x402 payment protection.

**Track:** 1 - Data Marketplace
**Protocol:** x402
**Languages:** TypeScript, Python

## Features

- Endpoint protection with x402 middleware
- Dynamic pricing based on request complexity
- Usage analytics and revenue tracking
- Rate limiting per subscriber
- Automatic settlement

## Quick Start

### TypeScript

```bash
cd typescript
yarn install
cp .env.example .env
# Edit .env with your credentials
yarn agent   # Start the selling agent
yarn client  # Test with client
```

### Python

```bash
cd python
poetry install
cp .env.example .env
# Edit .env with your credentials
poetry run agent   # Start the selling agent
poetry run client  # Test with client
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

## Configuration

### Environment Variables

```bash
# Required
NVM_API_KEY=nvm:your-api-key
NVM_ENVIRONMENT=sandbox
NVM_PLAN_ID=your-plan-id
OPENAI_API_KEY=sk-your-key

# Optional
PORT=3000
```

### Creating a Payment Plan

1. Go to [https://nevermined.app/](https://nevermined.app/)
2. Navigate to "My Pricing Plans"
3. Create a new plan with:
   - Plan type: Credit-based
   - Endpoints: `POST /data`, `GET /data/:id`
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
  "query": "market data for AAPL",
  "complexity": "medium"
}
```

**Response (200):**
```json
{
  "data": {
    "symbol": "AAPL",
    "price": 178.50,
    "volume": 52000000
  },
  "metadata": {
    "timestamp": "2024-03-05T10:30:00Z",
    "source": "market-feed"
  }
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
    "simple": { "credits": 1, "description": "Basic query" },
    "medium": { "credits": 5, "description": "Standard analysis" },
    "complex": { "credits": 10, "description": "Deep analysis" }
  }
}
```

### GET /stats

Get usage statistics (for seller).

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

The kit supports dynamic pricing based on request parameters:

```typescript
app.use(paymentMiddleware(payments, {
  "POST /data": {
    planId: NVM_PLAN_ID,
    credits: (req) => {
      const { complexity } = req.body;
      switch (complexity) {
        case "complex": return 10;
        case "medium": return 5;
        default: return 1;
      }
    },
  },
}));
```

## Customization Ideas

1. **Tiered access** - Different data quality at different prices
2. **Subscription discounts** - Lower per-credit cost for frequent users
3. **Data freshness pricing** - Real-time data costs more
4. **Volume discounts** - Reduce price for bulk queries
5. **Geographic pricing** - Different rates by region

## Next Steps

- Modify the data source for your domain
- Implement custom pricing logic
- Add data quality guarantees
- Set up revenue analytics
- Test with Kit A (Buyer Agent)

## Related

- [Kit A: Buyer Agent](../kit-a-buyer-agent/) - Build the buyer side
- [Kit C: Switching Agent](../kit-c-switching-agent/) - Multi-provider switching
- [Track 1 Overview](../../docs/tracks/track-1-data-marketplace.md)
