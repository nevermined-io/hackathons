# Track 3: Content Marketplace

Build agents that can publish, discover, and consume paid content.

## Overview

**Theme**: Content Monetization

**Challenge**: Create AI agents that can publish content with tiered pricing, discover relevant paid content, and consume content while managing payment flows.

## Use Cases

1. **Content Publisher Agent** - Publishes content with dynamic pricing tiers
2. **Content Consumer Agent** - Discovers and purchases relevant content
3. **Content Curator Agent** - Aggregates and recommends paid content
4. **Subscription Manager** - Manages subscriptions across publishers

## Starter Kits

### Kit D: Publisher Agent

An agent that publishes content with tiered pricing using MCP.

**Features:**
- Multi-tier pricing (free preview, paid full)
- Content registration with metadata
- Access control per tier
- Revenue tracking

**Key Code:**

```typescript
import { Payments } from "@nevermined-io/payments";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

const payments = Payments.getInstance({
  nvmApiKey: process.env.NVM_API_KEY,
  environment: "sandbox",
});

// Register content tiers
const contentTiers = {
  free: {
    planId: "plan-free-preview",
    credits: 0,
    access: ["preview", "metadata"],
  },
  basic: {
    planId: "plan-basic",
    credits: 1,
    access: ["preview", "metadata", "summary"],
  },
  premium: {
    planId: "plan-premium",
    credits: 5,
    access: ["preview", "metadata", "summary", "full", "raw"],
  },
};

// MCP tool for content access
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === "get_content") {
    const { contentId, tier = "free" } = args;
    const tierConfig = contentTiers[tier];

    if (tier !== "free") {
      // Verify payment
      const verification = await payments.facilitator.verifyPermissions({
        planId: tierConfig.planId,
        accessToken: args.paymentToken,
      });

      if (!verification.success) {
        return {
          content: [{ type: "text", text: "Payment required for this tier" }],
          isError: true,
        };
      }
    }

    const content = await getContent(contentId, tierConfig.access);

    // Settle if paid tier
    if (tier !== "free") {
      await payments.facilitator.settlePermissions({
        planId: tierConfig.planId,
        accessToken: args.paymentToken,
        credits: tierConfig.credits,
      });
    }

    return {
      content: [{ type: "text", text: JSON.stringify(content) }],
    };
  }
});
```

### Kit E: Consuming Agent

An agent that discovers and consumes paid content.

**Features:**
- Content discovery and search
- Automatic payment for content
- Content caching
- Reading history

**Key Code:**

```typescript
interface ContentItem {
  id: string;
  title: string;
  description: string;
  publisher: string;
  planId: string;
  price: number;
  tier: string;
}

class ContentConsumer {
  private payments: Payments;
  private readingHistory: ContentItem[] = [];
  private budget: number = 100;

  async searchContent(query: string): Promise<ContentItem[]> {
    // Search across content providers
    const results = await this.searchProviders(query);
    return results.filter(item => item.price <= this.budget);
  }

  async purchaseContent(item: ContentItem): Promise<any> {
    if (item.price > this.budget) {
      throw new Error("Insufficient budget");
    }

    // Get payment token
    const { accessToken } = await this.payments.x402.getX402AccessToken(item.planId);

    // Request content with payment
    const response = await fetch(`${item.publisher}/content/${item.id}`, {
      method: "GET",
      headers: {
        "payment-signature": accessToken,
      },
    });

    // Update budget
    const settlement = JSON.parse(
      Buffer.from(response.headers.get("payment-response"), "base64").toString()
    );
    this.budget -= settlement.creditsBurned || item.price;

    // Track history
    this.readingHistory.push(item);

    return response.json();
  }

  async recommendContent(): Promise<ContentItem[]> {
    // Recommend based on reading history
    const topics = this.extractTopics(this.readingHistory);
    return this.searchContent(topics.join(" "));
  }
}
```

## Technical Requirements

### Protocols

**Publisher Agent (Kit D)**: Uses MCP for tool definitions with x402 for payments

```
mcp://publisher-agent/tools/get_content
mcp://publisher-agent/tools/list_content
mcp://publisher-agent/resources/content/{id}
```

**Consumer Agent (Kit E)**: Uses x402 HTTP protocol

### Content Flow

```
┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│   Consumer   │          │  Nevermined  │          │  Publisher   │
│    Agent     │          │   Network    │          │    Agent     │
│   (Kit E)    │          │              │          │   (Kit D)    │
└──────┬───────┘          └──────┬───────┘          └──────┬───────┘
       │                         │                         │
       │  1. Search content      │                         │
       │────────────────────────>│                         │
       │                         │                         │
       │  2. Get pricing info    │                         │
       │────────────────────────>│<────────────────────────│
       │                         │                         │
       │  3. Get payment token   │                         │
       │────────────────────────>│                         │
       │                         │                         │
       │  4. Request content     │                         │
       │    + payment token      │                         │
       │─────────────────────────────────────────────────>│
       │                         │                         │
       │                         │  5. Verify & settle     │
       │                         │<────────────────────────│
       │                         │                         │
       │  6. Content + receipt   │                         │
       │<─────────────────────────────────────────────────│
```

## Judging Criteria

1. **Content Model** (25%) - How well is content structured and priced?
2. **Discovery** (20%) - How effectively can content be found?
3. **Monetization** (20%) - Creative pricing and payment models
4. **User Experience** (20%) - Smooth content consumption flow
5. **Code Quality** (15%) - Clean, documented code

## Ideas to Explore

- **Dynamic pricing** - Adjust prices based on demand
- **Bundling** - Offer content bundles at discounts
- **Subscription tiers** - Monthly access plans
- **Content previews** - Free previews to drive purchases
- **Recommendation engine** - AI-powered content suggestions
- **Revenue sharing** - Split revenue with content creators
- **Content licensing** - Different licenses for different uses
- **Time-based access** - Content that expires after viewing

## Resources

- [Kit D: Publisher Agent](../../starter-kits/kit-d-publisher-agent/)
- [Kit E: Consuming Agent](../../starter-kits/kit-e-consuming-agent/)
- [MCP Integration Guide](https://nevermined.ai/docs/development-guide/build-using-nvm-mcp)
- [Nevermined Documentation](https://nevermined.ai/docs)
