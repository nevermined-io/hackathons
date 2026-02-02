# Kit E: Consuming Agent

An agent that discovers and consumes paid content from publishers.

**Track:** 3 - Content Marketplace
**Protocol:** x402
**Languages:** TypeScript

## Features

- Content discovery and search
- Automatic payment for content
- Content caching
- Reading history
- Recommendation engine

## Quick Start

```bash
yarn install
cp .env.example .env
# Edit .env with your credentials
yarn agent   # Start the consuming agent
yarn demo    # Run the demo
```

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Consuming  │────>│  Nevermined  │────>│  Publisher  │
│    Agent    │     │   Network    │     │    Agent    │
└─────────────┘     └──────────────┘     └─────────────┘
      │                    │                    │
      │  1. Search content │                    │
      │───────────────────>│───────────────────>│
      │                    │                    │
      │  2. Get pricing    │                    │
      │───────────────────>│<───────────────────│
      │                    │                    │
      │  3. Purchase       │                    │
      │───────────────────>│───────────────────>│
      │                    │                    │
      │  4. Receive +      │                    │
      │     cache          │                    │
      │<───────────────────│<───────────────────│
```

## Configuration

### Environment Variables

```bash
# Required
NVM_API_KEY=nvm:your-api-key
NVM_ENVIRONMENT=sandbox
OPENAI_API_KEY=sk-your-key

# Budget
DAILY_BUDGET=100
MAX_PER_CONTENT=10

# Optional
PORT=3000
CACHE_DURATION=3600  # seconds
```

## API

### POST /search

Search for content across publishers.

**Request:**
```json
{
  "query": "market analysis",
  "category": "research",
  "maxPrice": 5
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "article-123",
      "title": "Market Analysis Q1 2024",
      "publisher": "https://publisher-a.com",
      "planId": "plan-basic",
      "price": 1,
      "tier": "basic"
    }
  ]
}
```

### POST /purchase

Purchase and retrieve content.

**Request:**
```json
{
  "contentId": "article-123",
  "publisher": "https://publisher-a.com",
  "planId": "plan-basic",
  "tier": "basic"
}
```

**Response:**
```json
{
  "content": {
    "id": "article-123",
    "title": "Market Analysis Q1 2024",
    "summary": "...",
    "fullContent": "...",
    "tier": "basic"
  },
  "cost": {
    "creditsUsed": 1,
    "remainingBudget": 99
  }
}
```

### GET /history

Get reading history.

**Response:**
```json
{
  "history": [
    {
      "contentId": "article-123",
      "title": "Market Analysis Q1 2024",
      "purchasedAt": "2024-03-05T10:30:00Z",
      "cost": 1,
      "tier": "basic"
    }
  ]
}
```

### GET /recommendations

Get content recommendations based on history.

**Response:**
```json
{
  "recommendations": [
    {
      "id": "article-456",
      "title": "Q2 2024 Forecast",
      "reason": "Similar to 'Market Analysis Q1 2024'",
      "price": 1
    }
  ]
}
```

### GET /budget

Get current budget status.

**Response:**
```json
{
  "dailyBudget": 100,
  "spent": 15,
  "remaining": 85,
  "contentPurchased": 8
}
```

## Content Cache

The agent caches purchased content to avoid re-purchasing:

```typescript
interface CacheEntry {
  contentId: string;
  content: Content;
  purchasedAt: Date;
  expiresAt: Date;
  tier: string;
}

class ContentCache {
  private cache: Map<string, CacheEntry> = new Map();

  get(contentId: string): Content | null {
    const entry = this.cache.get(contentId);
    if (!entry || entry.expiresAt < new Date()) {
      return null;
    }
    return entry.content;
  }

  set(contentId: string, content: Content, tier: string): void {
    this.cache.set(contentId, {
      contentId,
      content,
      purchasedAt: new Date(),
      expiresAt: new Date(Date.now() + CACHE_DURATION * 1000),
      tier,
    });
  }
}
```

## Recommendation Engine

```typescript
class RecommendationEngine {
  private history: ReadingHistory[];

  async getRecommendations(): Promise<ContentRecommendation[]> {
    // Extract topics from reading history
    const topics = await this.extractTopics();

    // Search for similar content
    const results = await this.searchByTopics(topics);

    // Filter out already purchased
    const newContent = results.filter(c => !this.hasPurchased(c.id));

    // Rank by relevance
    return this.rankByRelevance(newContent, topics);
  }

  private async extractTopics(): Promise<string[]> {
    const titles = this.history.map(h => h.title);
    // Use LLM to extract key topics
    const topics = await extractKeyTopics(titles);
    return topics;
  }
}
```

## Customization Ideas

1. **Smart purchasing** - AI decides which tier is needed
2. **Content alerts** - Notify when relevant content is published
3. **Batch downloading** - Download multiple pieces efficiently
4. **Offline mode** - Cache content for offline access
5. **Content comparison** - Compare content from different publishers

## Next Steps

- Customize search criteria for your domain
- Add content processing/analysis
- Implement recommendation algorithm
- Set up alerts for new content
- Test with Kit D (Publisher Agent)

## Related

- [Kit D: Publisher Agent](../kit-d-publisher-agent/) - Build the publisher side
- [Track 3 Overview](../../docs/tracks/track-3-content-marketplace.md)
