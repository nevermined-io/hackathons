# Kit D: Publisher Agent

An agent that publishes content with tiered pricing using MCP and x402.

**Track:** 3 - Content Marketplace
**Protocol:** MCP/x402
**Languages:** TypeScript

## Features

- Multi-tier pricing (free, basic, premium)
- Content registration with metadata
- MCP tool definitions for content access
- Access control per pricing tier
- Revenue tracking

## Quick Start

```bash
yarn install
cp .env.example .env
# Edit .env with your credentials
yarn agent   # Start the publisher agent
yarn client  # Test content access
```

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Consumer   │────>│  Nevermined  │────>│  Publisher  │
│   (Client)  │     │   Network    │     │    Agent    │
└─────────────┘     └──────────────┘     └─────────────┘
      │                    │                    │
      │  1. List content   │                    │
      │───────────────────>│───────────────────>│
      │                    │                    │
      │  2. Get pricing    │                    │
      │───────────────────>│<───────────────────│
      │                    │                    │
      │  3. Request tier   │                    │
      │   + payment token  │                    │
      │───────────────────>│───────────────────>│
      │                    │                    │
      │  4. Content +      │                    │
      │     receipt        │                    │
      │<───────────────────│<───────────────────│
```

## Configuration

### Environment Variables

```bash
# Required
NVM_API_KEY=nvm:your-api-key
NVM_ENVIRONMENT=sandbox

# Plan IDs for each tier
NVM_PLAN_FREE=plan-free-xxx
NVM_PLAN_BASIC=plan-basic-xxx
NVM_PLAN_PREMIUM=plan-premium-xxx

# Optional
PORT=3000
CONTENT_STORAGE_PATH=./content
```

## Pricing Tiers

| Tier | Credits | Access |
|------|---------|--------|
| Free | 0 | Preview, metadata only |
| Basic | 1 | Preview, metadata, summary |
| Premium | 5 | Full content, raw data, API access |

## MCP Tools

### list_content

List available content.

```json
{
  "name": "list_content",
  "arguments": {
    "category": "research",
    "limit": 10
  }
}
```

### get_content

Get content by ID and tier.

```json
{
  "name": "get_content",
  "arguments": {
    "contentId": "article-123",
    "tier": "premium",
    "paymentToken": "nvm:token..."
  }
}
```

### get_pricing

Get pricing for specific content.

```json
{
  "name": "get_pricing",
  "arguments": {
    "contentId": "article-123"
  }
}
```

## API

### GET /content

List all published content.

**Response:**
```json
{
  "content": [
    {
      "id": "article-123",
      "title": "Market Analysis Q1 2024",
      "description": "Comprehensive market analysis...",
      "category": "research",
      "tiers": ["free", "basic", "premium"]
    }
  ]
}
```

### GET /content/:id

Get content (tier based on payment).

**Request Headers:**
```
payment-signature: <x402-access-token>
```

**Response (Premium tier):**
```json
{
  "id": "article-123",
  "title": "Market Analysis Q1 2024",
  "preview": "...",
  "summary": "...",
  "fullContent": "...",
  "rawData": { ... },
  "tier": "premium"
}
```

### POST /content

Publish new content.

**Request:**
```json
{
  "title": "New Research",
  "description": "Description...",
  "content": {
    "preview": "...",
    "summary": "...",
    "full": "...",
    "raw": { ... }
  },
  "category": "research"
}
```

## Content Structure

```typescript
interface Content {
  id: string;
  title: string;
  description: string;
  category: string;
  createdAt: Date;
  tiers: {
    free: {
      preview: string;
      metadata: ContentMetadata;
    };
    basic: {
      preview: string;
      metadata: ContentMetadata;
      summary: string;
    };
    premium: {
      preview: string;
      metadata: ContentMetadata;
      summary: string;
      fullContent: string;
      rawData: any;
    };
  };
}
```

## Customization Ideas

1. **Dynamic pricing** - Adjust prices based on content popularity
2. **Time-limited access** - Content that expires after viewing
3. **Bundling** - Offer content bundles at discounts
4. **Subscriptions** - Monthly access to all content
5. **Early access** - Premium users get content first

## MCP Server Setup

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { Payments } from "@nevermined-io/payments";

const server = new McpServer({
  name: "publisher-agent",
  version: "1.0.0",
});

// Register tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "get_content",
        description: "Get content by ID (payment required for non-free tiers)",
        inputSchema: {
          type: "object",
          properties: {
            contentId: { type: "string" },
            tier: { type: "string", enum: ["free", "basic", "premium"] },
            paymentToken: { type: "string" },
          },
          required: ["contentId"],
        },
      },
    ],
  };
});
```

## Next Steps

- Add your content types
- Customize pricing tiers
- Implement content storage
- Set up analytics
- Test with Kit E (Consuming Agent)

## Related

- [Kit E: Consuming Agent](../kit-e-consuming-agent/) - Build the consumer side
- [Track 3 Overview](../../docs/tracks/track-3-content-marketplace.md)
- [MCP Integration Guide](../../docs/aws-integration.md)
