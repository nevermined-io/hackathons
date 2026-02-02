# Track 1: Data Marketplace

Build autonomous agents that can discover, buy, sell, and trade data in a decentralized marketplace.

## Overview

**Theme**: Autonomous Data Commerce

**Challenge**: Create AI agents that can autonomously participate in a data marketplace - finding data they need, negotiating prices, making purchases, and selling their own data or services.

## Use Cases

1. **Data Buyer Agent** - Autonomously discovers and purchases data from various providers
2. **Data Seller Agent** - Registers and sells data/services with dynamic pricing
3. **Smart Switcher** - Compares providers and switches based on price/quality
4. **Data Aggregator** - Combines data from multiple sources with payment routing

## Starter Kits

### Kit A: Buyer Agent

An agent that discovers and purchases data autonomously.

**Features:**
- Budget management (max spend per request/day)
- Provider discovery and comparison
- Automatic payment execution via x402
- Purchase history tracking

**Key Code:**

```typescript
import { Payments } from "@nevermined-io/payments";
import { paymentMiddleware } from "@nevermined-io/payments/express";

const payments = Payments.getInstance({
  nvmApiKey: process.env.NVM_API_KEY,
  environment: "sandbox",
});

// Budget tracking
let dailySpend = 0;
const MAX_DAILY_SPEND = 100; // credits

async function purchaseData(providerUrl: string, query: string) {
  // Check budget
  if (dailySpend >= MAX_DAILY_SPEND) {
    throw new Error("Daily budget exceeded");
  }

  // Get x402 token for the provider's plan
  const { accessToken } = await payments.x402.getX402AccessToken(PROVIDER_PLAN_ID);

  // Make purchase request
  const response = await fetch(`${providerUrl}/data`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "payment-signature": accessToken,
    },
    body: JSON.stringify({ query }),
  });

  // Track spending
  const settlement = JSON.parse(
    Buffer.from(response.headers.get("payment-response"), "base64").toString()
  );
  dailySpend += settlement.creditsBurned || 1;

  return response.json();
}
```

### Kit B: Selling Agent

An agent that sells data or services with payment protection.

**Features:**
- Endpoint protection with x402 middleware
- Dynamic pricing based on request complexity
- Usage analytics and revenue tracking
- Rate limiting per subscriber

**Key Code:**

```typescript
// Dynamic pricing based on request
app.use(paymentMiddleware(payments, {
  "POST /data": {
    planId: NVM_PLAN_ID,
    credits: (req) => {
      const { complexity } = req.body;
      // Price based on complexity
      if (complexity === "high") return 10;
      if (complexity === "medium") return 5;
      return 1;
    },
  },
}));
```

### Kit C: Switching Agent

An agent that switches between data providers based on price and quality.

**Features:**
- Multi-provider management
- Price comparison before purchase
- Quality scoring and provider ranking
- Automatic failover

**Key Code:**

```typescript
interface Provider {
  url: string;
  planId: string;
  pricePerCredit: number;
  qualityScore: number;
}

const providers: Provider[] = [
  { url: "https://provider-a.com", planId: "plan-a", pricePerCredit: 0.01, qualityScore: 0.9 },
  { url: "https://provider-b.com", planId: "plan-b", pricePerCredit: 0.005, qualityScore: 0.7 },
];

async function selectBestProvider(query: string): Promise<Provider> {
  // Score providers by value (quality / price)
  const scored = providers.map(p => ({
    ...p,
    value: p.qualityScore / p.pricePerCredit,
  }));

  // Sort by value
  scored.sort((a, b) => b.value - a.value);

  return scored[0];
}
```

## Technical Requirements

### Protocol: x402

All Track 1 kits use the x402 HTTP payment protocol:

| Header | Direction | Description |
|--------|-----------|-------------|
| `payment-signature` | Client -> Server | x402 access token |
| `payment-required` | Server -> Client (402) | Payment requirements |
| `payment-response` | Server -> Client (200) | Settlement receipt |

### Data Flow

```
┌──────────┐     ┌──────────────┐     ┌──────────┐
│  Buyer   │────>│  Nevermined  │<────│  Seller  │
│  Agent   │     │   Network    │     │  Agent   │
└──────────┘     └──────────────┘     └──────────┘
     │                  │                   │
     │  1. Discover     │                   │
     │  providers       │                   │
     │─────────────────>│                   │
     │                  │                   │
     │  2. Get payment  │                   │
     │  requirements    │                   │
     │─────────────────>│<──────────────────│
     │                  │                   │
     │  3. Purchase     │                   │
     │  data            │                   │
     │─────────────────>│───────────────────>│
     │                  │                   │
     │  4. Receive      │                   │
     │  data + receipt  │                   │
     │<─────────────────│<──────────────────│
```

## Judging Criteria

1. **Autonomy** (30%) - How autonomously does the agent operate?
2. **Economic Logic** (25%) - Smart budget/pricing decisions
3. **Integration** (20%) - Clean use of Nevermined APIs
4. **Innovation** (15%) - Creative marketplace features
5. **Code Quality** (10%) - Clean, documented code

## Ideas to Explore

- **Real-time pricing** - Adjust prices based on demand
- **Reputation system** - Track provider reliability
- **Data quality verification** - Verify data before full payment
- **Multi-currency support** - Accept different payment methods
- **Subscription models** - Recurring data feeds
- **Data derivatives** - Create and sell processed data

## Resources

- [Kit A: Buyer Agent](../../starter-kits/kit-a-buyer-agent/)
- [Kit B: Selling Agent](../../starter-kits/kit-b-selling-agent/)
- [Kit C: Switching Agent](../../starter-kits/kit-c-switching-agent/)
- [x402 Protocol Spec](https://github.com/coinbase/x402)
- [Nevermined Documentation](https://nevermined.ai/docs)
