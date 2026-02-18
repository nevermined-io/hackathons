# Kit G: Requesting Agent

An agent that requests services from other agents in the organization.

**Track:** 2 - Internal A2A Economy
**Protocol:** A2A/x402
**Languages:** TypeScript

## Features

- Service discovery
- Request routing
- Response aggregation
- Budget allocation per request
- Retry and failover logic

## Quick Start

```bash
yarn install
cp .env.example .env
# Edit .env with your credentials
yarn agent   # Start the requesting agent
yarn demo    # Run the demo
```

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Requesting │────>│   Service    │────>│  Servicing  │
│    Agent    │     │  Discovery   │     │    Agent    │
└─────────────┘     └──────────────┘     └─────────────┘
      │                    │                    │
      │  1. Discover       │                    │
      │     services       │                    │
      │───────────────────>│                    │
      │                    │                    │
      │  2. Select best    │                    │
      │     provider       │                    │
      │<───────────────────│                    │
      │                    │                    │
      │  3. Request        │                    │
      │    + payment       │                    │
      │───────────────────────────────────────>│
      │                    │                    │
      │  4. Response       │                    │
      │    + receipt       │                    │
      │<───────────────────────────────────────│
```

## Configuration

### Environment Variables

```bash
# Required
NVM_API_KEY=sandbox:your-api-key
NVM_ENVIRONMENT=sandbox
OPENAI_API_KEY=sk-your-key

# Service registry
SERVICE_REGISTRY_URL=http://registry:3000

# Budget
DAILY_BUDGET=1000
MAX_PER_REQUEST=50

# Optional
PORT=3000
MAX_RETRIES=3
TIMEOUT_MS=30000
```

### Service Registry Configuration

```typescript
interface ServiceProvider {
  serviceType: string;
  providerId: string;
  endpoint: string;
  planId: string;
  pricing: {
    creditsPerRequest: number;
  };
  metadata: {
    version: string;
    capabilities: string[];
  };
}
```

## API

### POST /request

Request a service from a provider.

**Request:**
```json
{
  "serviceType": "data-analysis",
  "payload": {
    "data": [...],
    "analysisType": "trend"
  },
  "options": {
    "maxBudget": 10,
    "preferredProvider": "agent-xyz",
    "timeout": 30000
  }
}
```

**Response:**
```json
{
  "requestId": "req-123",
  "result": {
    "analysis": {...},
    "confidence": 0.92
  },
  "provider": {
    "id": "agent-xyz",
    "serviceType": "data-analysis"
  },
  "cost": {
    "creditsUsed": 5,
    "remainingBudget": 995
  },
  "latency": 2340
}
```

### GET /services

List available services.

**Response:**
```json
{
  "services": [
    {
      "type": "data-analysis",
      "providers": [
        {
          "id": "agent-a",
          "endpoint": "http://agent-a:3000",
          "price": 5,
          "rating": 4.8
        }
      ]
    },
    {
      "type": "summarization",
      "providers": [...]
    }
  ]
}
```

### POST /aggregate

Request same service from multiple providers and aggregate.

**Request:**
```json
{
  "serviceType": "data-analysis",
  "payload": {...},
  "aggregation": {
    "strategy": "vote",
    "minProviders": 3
  }
}
```

**Response:**
```json
{
  "aggregatedResult": {...},
  "providerResults": [
    { "provider": "agent-a", "result": {...} },
    { "provider": "agent-b", "result": {...} },
    { "provider": "agent-c", "result": {...} }
  ],
  "agreement": 0.85,
  "totalCost": 15
}
```

### GET /budget

Get current budget status.

**Response:**
```json
{
  "dailyBudget": 1000,
  "spent": 150,
  "remaining": 850,
  "requestCount": 45,
  "byService": {
    "data-analysis": 80,
    "summarization": 50,
    "translation": 20
  }
}
```

## Service Discovery

```typescript
class ServiceDiscovery {
  private registry: Map<string, ServiceProvider[]> = new Map();

  async discover(serviceType: string): Promise<ServiceProvider[]> {
    // Check cache
    if (this.registry.has(serviceType)) {
      return this.registry.get(serviceType);
    }

    // Query registry
    const providers = await this.queryRegistry(serviceType);
    this.registry.set(serviceType, providers);

    return providers;
  }

  async selectBest(serviceType: string, options: SelectionOptions): Promise<ServiceProvider> {
    const providers = await this.discover(serviceType);

    // Filter by budget
    const affordable = providers.filter(p => p.pricing.creditsPerRequest <= options.maxBudget);

    // Sort by preference
    if (options.preferredProvider) {
      const preferred = affordable.find(p => p.providerId === options.preferredProvider);
      if (preferred) return preferred;
    }

    // Sort by rating/price ratio
    return affordable.sort((a, b) => {
      const valueA = a.rating / a.pricing.creditsPerRequest;
      const valueB = b.rating / b.pricing.creditsPerRequest;
      return valueB - valueA;
    })[0];
  }
}
```

## Request Routing

```typescript
async function routeRequest(request: ServiceRequest): Promise<ServiceResponse> {
  const provider = await serviceDiscovery.selectBest(
    request.serviceType,
    request.options
  );

  // Get payment token
  const { accessToken } = await payments.x402.getX402AccessToken(provider.planId);

  // Make request with retry
  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    try {
      const response = await fetch(`${provider.endpoint}/execute`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "payment-signature": accessToken,
        },
        body: JSON.stringify(request.payload),
        signal: AbortSignal.timeout(request.options.timeout),
      });

      if (response.ok) {
        return {
          result: await response.json(),
          provider,
          cost: extractCost(response.headers),
        };
      }
    } catch (error) {
      if (attempt === MAX_RETRIES - 1) throw error;
      await delay(1000 * (attempt + 1)); // Exponential backoff
    }
  }
}
```

## Customization Ideas

1. **Smart routing** - ML-based provider selection
2. **Request batching** - Batch multiple requests to same provider
3. **Circuit breaker** - Protect against failing providers
4. **Request caching** - Cache responses for similar requests
5. **Cost prediction** - Estimate cost before execution

## Next Steps

- Register your service providers
- Customize routing logic
- Add domain-specific aggregation
- Set up monitoring
- Test with Kit H (Servicing Agent)

## Related

- [Kit F: Quality Assessment](../kit-f-quality-assessment/) - Assess quality
- [Kit H: Servicing Agent](../kit-h-servicing-agent/) - Provide services
- [Kit I: ROI Governor](../kit-i-roi-governor/) - Monitor spending
- [Track 2 Overview](../../docs/tracks/track-2-internal-a2a.md)
