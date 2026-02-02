# Kit H: Servicing Agent

An agent that provides specialized services to other agents.

**Track:** 2 - Internal A2A Economy
**Protocol:** A2A/x402
**Languages:** TypeScript

## Features

- Service registration
- Request handling with payment verification
- Service level tracking
- Usage analytics
- Rate limiting

## Quick Start

```bash
yarn install
cp .env.example .env
# Edit .env with your credentials
yarn agent   # Start the servicing agent
yarn demo    # Run the demo
```

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Requesting │────>│  Nevermined  │────>│  Servicing  │
│    Agent    │     │   Network    │     │    Agent    │
└─────────────┘     └──────────────┘     └─────────────┘
      │                    │                    │
      │  1. Request        │                    │
      │    + payment token │                    │
      │───────────────────>│───────────────────>│
      │                    │                    │
      │                    │  2. Verify payment │
      │                    │<───────────────────│
      │                    │                    │
      │                    │  3. Execute        │
      │                    │     service        │
      │                    │                    │
      │                    │  4. Settle         │
      │                    │<───────────────────│
      │                    │                    │
      │  5. Response       │                    │
      │    + receipt       │                    │
      │<───────────────────│<───────────────────│
```

## Configuration

### Environment Variables

```bash
# Required
NVM_API_KEY=nvm:your-api-key
NVM_ENVIRONMENT=sandbox
NVM_PLAN_ID=plan-service-xxx
OPENAI_API_KEY=sk-your-key

# Service registration
SERVICE_TYPE=data-analysis
SERVICE_NAME=Advanced Data Analysis Agent
SERVICE_DESCRIPTION=Performs trend analysis, forecasting, and insights

# Optional
PORT=3000
MAX_CONCURRENT=10
RATE_LIMIT_PER_MINUTE=60
```

## API

### POST /execute

Execute a service request (payment protected).

**Request Headers:**
```
payment-signature: <x402-access-token>
```

**Request:**
```json
{
  "operation": "analyze",
  "data": [...],
  "options": {
    "analysisType": "trend",
    "period": "30d"
  }
}
```

**Response:**
```json
{
  "requestId": "req-123",
  "result": {
    "trend": "increasing",
    "slope": 0.15,
    "confidence": 0.92,
    "forecast": [...]
  },
  "metadata": {
    "processingTime": 1250,
    "creditsUsed": 5
  }
}
```

### GET /capabilities

List service capabilities.

**Response:**
```json
{
  "serviceType": "data-analysis",
  "operations": [
    {
      "name": "analyze",
      "description": "Perform data analysis",
      "inputSchema": {...},
      "credits": 5
    },
    {
      "name": "forecast",
      "description": "Generate forecasts",
      "inputSchema": {...},
      "credits": 10
    }
  ],
  "limits": {
    "maxDataPoints": 10000,
    "maxForecastPeriod": "365d"
  }
}
```

### GET /stats

Get service usage statistics.

**Response:**
```json
{
  "totalRequests": 5000,
  "successRate": 0.98,
  "averageLatency": 1200,
  "creditsEarned": 25000,
  "uniqueClients": 45,
  "byOperation": {
    "analyze": { "count": 3500, "avgLatency": 1100 },
    "forecast": { "count": 1500, "avgLatency": 1500 }
  }
}
```

### GET /health

Health check endpoint (unprotected).

**Response:**
```json
{
  "status": "healthy",
  "uptime": 86400,
  "load": 0.45,
  "queueLength": 3
}
```

## Service Implementation

### Payment Middleware

```typescript
import { paymentMiddleware } from "@nevermined-io/payments/express";

// Protect service endpoints
app.use(paymentMiddleware(payments, {
  "POST /execute": {
    planId: NVM_PLAN_ID,
    credits: (req) => {
      // Dynamic pricing based on operation
      const { operation } = req.body;
      switch (operation) {
        case "forecast": return 10;
        case "analyze": return 5;
        default: return 1;
      }
    },
  },
}));
```

### Service Logic

```typescript
class DataAnalysisService {
  async execute(request: ServiceRequest): Promise<ServiceResult> {
    const { operation, data, options } = request;

    switch (operation) {
      case "analyze":
        return this.analyze(data, options);
      case "forecast":
        return this.forecast(data, options);
      default:
        throw new Error(`Unknown operation: ${operation}`);
    }
  }

  private async analyze(data: any[], options: AnalysisOptions): Promise<AnalysisResult> {
    // Perform analysis
    const trend = calculateTrend(data);
    const insights = await generateInsights(data, options);

    return {
      trend: trend.direction,
      slope: trend.slope,
      confidence: trend.confidence,
      insights,
    };
  }

  private async forecast(data: any[], options: ForecastOptions): Promise<ForecastResult> {
    // Generate forecast
    const predictions = await generatePredictions(data, options.period);

    return {
      predictions,
      confidence: calculateConfidence(predictions),
    };
  }
}
```

### Service Registration

```typescript
async function registerService() {
  const registration = {
    serviceType: SERVICE_TYPE,
    name: SERVICE_NAME,
    description: SERVICE_DESCRIPTION,
    endpoint: `http://${HOST}:${PORT}`,
    planId: NVM_PLAN_ID,
    capabilities: [
      { operation: "analyze", credits: 5 },
      { operation: "forecast", credits: 10 },
    ],
  };

  await serviceRegistry.register(registration);
  console.log(`Service registered: ${SERVICE_NAME}`);
}
```

## Rate Limiting

```typescript
import rateLimit from "express-rate-limit";

const limiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: RATE_LIMIT_PER_MINUTE,
  message: { error: "Rate limit exceeded" },
});

app.use("/execute", limiter);
```

## Customization Ideas

1. **Multi-operation service** - Offer various related operations
2. **Tiered quality** - Different quality levels at different prices
3. **Priority queue** - Premium requests processed first
4. **Batch processing** - Handle multiple requests efficiently
5. **Custom SLAs** - Guarantee response times for extra credits

## Next Steps

- Implement your service logic
- Register with the service registry
- Set up monitoring and alerting
- Define SLAs and pricing
- Test with Kit G (Requesting Agent)

## Related

- [Kit F: Quality Assessment](../kit-f-quality-assessment/) - Get quality feedback
- [Kit G: Requesting Agent](../kit-g-requesting-agent/) - Request services
- [Kit I: ROI Governor](../kit-i-roi-governor/) - Monitor spending
- [Track 2 Overview](../../docs/tracks/track-2-internal-a2a.md)
