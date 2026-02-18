# Kit C: Switching Agent

An agent that switches between data providers based on price, quality, and availability.

**Track:** 1 - Data Marketplace
**Protocol:** x402
**Languages:** TypeScript

## Features

- Multi-provider management
- Real-time price comparison
- Quality scoring and ranking
- Automatic failover
- Cost optimization

## Quick Start

```bash
yarn install
cp .env.example .env
# Edit .env with your credentials
yarn agent   # Start the switching agent
yarn demo    # Run the demo
```

## How It Works

```
                    ┌─────────────────┐
                    │   Switching     │
                    │     Agent       │
                    │    (Kit C)      │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
       ┌──────────┐   ┌──────────┐   ┌──────────┐
       │ Provider │   │ Provider │   │ Provider │
       │    A     │   │    B     │   │    C     │
       │ ($0.01)  │   │ ($0.005) │   │ ($0.02)  │
       │ Q: 0.9   │   │ Q: 0.7   │   │ Q: 0.95  │
       └──────────┘   └──────────┘   └──────────┘
```

The agent selects providers based on:
- **Price** - Cost per credit
- **Quality** - Historical accuracy/reliability score
- **Availability** - Provider uptime
- **Value** - Quality/Price ratio

## Configuration

### Environment Variables

```bash
# Required
NVM_API_KEY=sandbox:your-api-key
NVM_ENVIRONMENT=sandbox
OPENAI_API_KEY=sk-your-key

# Provider configuration (JSON)
PROVIDERS='[
  {"name": "Provider A", "url": "https://a.example.com", "planId": "plan-a"},
  {"name": "Provider B", "url": "https://b.example.com", "planId": "plan-b"}
]'

# Optional
PORT=3000
MAX_FALLBACK_ATTEMPTS=3
```

### Provider Configuration

```typescript
interface Provider {
  name: string;
  url: string;
  planId: string;
  pricePerCredit?: number;   // Fetched or configured
  qualityScore?: number;     // 0-1, tracked over time
  availability?: number;     // 0-1, tracked over time
}
```

## API

### POST /query

Query data using the best available provider.

**Request:**
```json
{
  "query": "market data for AAPL",
  "strategy": "best_value"
}
```

**Strategy options:**
- `cheapest` - Lowest price
- `best_quality` - Highest quality score
- `best_value` - Best quality/price ratio
- `fastest` - Lowest latency

**Response:**
```json
{
  "data": { ... },
  "provider": {
    "name": "Provider A",
    "creditsUsed": 5,
    "qualityScore": 0.92,
    "latency": 230
  }
}
```

### GET /providers

Get all configured providers with stats.

**Response:**
```json
{
  "providers": [
    {
      "name": "Provider A",
      "url": "https://a.example.com",
      "planId": "plan-a",
      "pricePerCredit": 0.01,
      "qualityScore": 0.92,
      "availability": 0.99,
      "valueScore": 92
    },
    {
      "name": "Provider B",
      "url": "https://b.example.com",
      "planId": "plan-b",
      "pricePerCredit": 0.005,
      "qualityScore": 0.75,
      "availability": 0.95,
      "valueScore": 150
    }
  ]
}
```

### POST /providers

Add a new provider.

**Request:**
```json
{
  "name": "New Provider",
  "url": "https://new.example.com",
  "planId": "plan-new"
}
```

### DELETE /providers/:name

Remove a provider.

## Selection Algorithm

```typescript
function selectProvider(providers: Provider[], strategy: Strategy): Provider {
  switch (strategy) {
    case "cheapest":
      return providers.sort((a, b) => a.pricePerCredit - b.pricePerCredit)[0];

    case "best_quality":
      return providers.sort((a, b) => b.qualityScore - a.qualityScore)[0];

    case "best_value":
      // Value = Quality / Price
      const scored = providers.map(p => ({
        ...p,
        value: (p.qualityScore * p.availability) / p.pricePerCredit,
      }));
      return scored.sort((a, b) => b.value - a.value)[0];

    case "fastest":
      return providers.sort((a, b) => a.avgLatency - b.avgLatency)[0];
  }
}
```

## Failover Logic

When a provider fails:

1. Mark provider as temporarily unavailable
2. Select next best provider using the same strategy
3. Execute request with backup provider
4. Update availability scores
5. Retry original provider after cooldown

```typescript
async function queryWithFailover(query: string, strategy: Strategy) {
  const providers = getAvailableProviders();
  const sorted = rankProviders(providers, strategy);

  for (const provider of sorted) {
    try {
      return await queryProvider(provider, query);
    } catch (error) {
      markProviderFailed(provider);
      continue;
    }
  }

  throw new Error("All providers failed");
}
```

## Quality Tracking

Quality scores are updated based on:
- Response validity (parseable, expected format)
- Data accuracy (when verifiable)
- Response latency
- Error rates

```typescript
function updateQualityScore(provider: Provider, response: Response) {
  const newScore = calculateScore(response);
  // Exponential moving average
  provider.qualityScore = 0.9 * provider.qualityScore + 0.1 * newScore;
}
```

## Customization Ideas

1. **ML-based selection** - Train a model to predict best provider
2. **Time-based routing** - Different providers for different times
3. **Cost caps** - Automatic switching when budget runs low
4. **A/B testing** - Test new providers with a percentage of traffic
5. **Geographic routing** - Route based on provider location

## Next Steps

- Add your actual data providers
- Customize the selection algorithm
- Implement quality metrics for your domain
- Set up monitoring and alerts
- Test failover scenarios

## Related

- [Kit A: Buyer Agent](../kit-a-buyer-agent/) - Simple buyer
- [Kit B: Selling Agent](../kit-b-selling-agent/) - Build a provider
- [Track 1 Overview](../../docs/tracks/track-1-data-marketplace.md)
