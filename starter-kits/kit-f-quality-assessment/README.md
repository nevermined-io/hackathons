# Kit F: Quality Assessment Agent

An agent that evaluates the quality of outputs from other agents.

**Track:** 2 - Internal A2A Economy
**Protocol:** A2A/x402
**Languages:** TypeScript

## Features

- Quality scoring algorithms
- A2A transaction for assessment requests
- Feedback loop to providers
- Quality history and trending
- Configurable quality thresholds

## Quick Start

```bash
yarn install
cp .env.example .env
# Edit .env with your credentials
yarn agent   # Start the quality agent
yarn demo    # Run the demo
```

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Requester  │────>│   Quality    │────>│   Service   │
│    Agent    │     │  Assessment  │     │   Provider  │
└─────────────┘     └──────────────┘     └─────────────┘
      │                    │                    │
      │  1. Submit output  │                    │
      │    for assessment  │                    │
      │───────────────────>│                    │
      │                    │                    │
      │  2. Run quality    │                    │
      │     checks         │                    │
      │                    │                    │
      │  3. Return score   │                    │
      │    + feedback      │                    │
      │<───────────────────│                    │
      │                    │                    │
      │                    │  4. Send feedback  │
      │                    │───────────────────>│
```

## Configuration

### Environment Variables

```bash
# Required
NVM_API_KEY=nvm:your-api-key
NVM_ENVIRONMENT=sandbox
NVM_PLAN_ID=plan-quality-xxx
OPENAI_API_KEY=sk-your-key

# Quality thresholds
MIN_QUALITY_SCORE=0.7
COMPLETENESS_WEIGHT=0.3
ACCURACY_WEIGHT=0.4
FORMAT_WEIGHT=0.2
CONSISTENCY_WEIGHT=0.1

# Optional
PORT=3000
```

## API

### POST /assess

Submit output for quality assessment (payment protected).

**Request Headers:**
```
payment-signature: <x402-access-token>
```

**Request:**
```json
{
  "requestId": "req-123",
  "serviceType": "data-analysis",
  "output": {
    "data": { ... },
    "format": "json"
  },
  "expectedSchema": { ... },
  "context": {
    "originalRequest": "...",
    "provider": "agent-xyz"
  }
}
```

**Response:**
```json
{
  "assessmentId": "assess-456",
  "score": 0.85,
  "passed": true,
  "breakdown": {
    "completeness": 0.9,
    "accuracy": 0.8,
    "format": 0.95,
    "consistency": 0.75
  },
  "feedback": [
    "Missing field 'timestamp' in response",
    "Numeric precision could be improved"
  ],
  "recommendations": [
    "Add timestamp to all responses",
    "Use consistent decimal places"
  ]
}
```

### GET /history/:providerId

Get quality history for a provider.

**Response:**
```json
{
  "providerId": "agent-xyz",
  "assessments": [
    {
      "assessmentId": "assess-456",
      "score": 0.85,
      "timestamp": "2024-03-05T10:30:00Z"
    }
  ],
  "averageScore": 0.82,
  "trend": "improving",
  "totalAssessments": 150
}
```

### GET /stats

Get overall quality statistics.

**Response:**
```json
{
  "totalAssessments": 5000,
  "averageScore": 0.81,
  "passRate": 0.92,
  "topProviders": [
    { "id": "agent-a", "avgScore": 0.95 },
    { "id": "agent-b", "avgScore": 0.88 }
  ],
  "commonIssues": [
    { "issue": "Missing fields", "frequency": 0.15 },
    { "issue": "Format errors", "frequency": 0.08 }
  ]
}
```

## Quality Checks

### Completeness Check

Verifies all required fields are present:

```typescript
async function checkCompleteness(output: any, schema: Schema): Promise<CheckResult> {
  const requiredFields = getRequiredFields(schema);
  const missingFields = requiredFields.filter(f => !hasField(output, f));

  return {
    score: 1 - (missingFields.length / requiredFields.length),
    issues: missingFields.map(f => `Missing required field: ${f}`),
  };
}
```

### Accuracy Check

Uses LLM to verify accuracy:

```typescript
async function checkAccuracy(output: any, context: Context): Promise<CheckResult> {
  const prompt = `
    Evaluate the accuracy of this output given the original request.
    Original request: ${context.originalRequest}
    Output: ${JSON.stringify(output)}

    Rate accuracy from 0-1 and list any inaccuracies.
  `;

  const result = await llm.evaluate(prompt);
  return {
    score: result.score,
    issues: result.inaccuracies,
  };
}
```

### Format Check

Validates output format:

```typescript
async function checkFormat(output: any, expectedFormat: string): Promise<CheckResult> {
  const issues: string[] = [];

  // Check structure
  if (expectedFormat === "json" && typeof output !== "object") {
    issues.push("Expected JSON object");
  }

  // Check encoding
  if (!isValidEncoding(output)) {
    issues.push("Invalid character encoding");
  }

  return {
    score: issues.length === 0 ? 1 : 0.5,
    issues,
  };
}
```

### Consistency Check

Compares with historical outputs:

```typescript
async function checkConsistency(output: any, history: HistoricalOutput[]): Promise<CheckResult> {
  if (history.length === 0) {
    return { score: 1, issues: [] };
  }

  const inconsistencies: string[] = [];

  // Check field consistency
  for (const field of getCommonFields(output, history)) {
    if (!isConsistent(output[field], history.map(h => h[field]))) {
      inconsistencies.push(`Inconsistent value for field: ${field}`);
    }
  }

  return {
    score: 1 - (inconsistencies.length * 0.1),
    issues: inconsistencies,
  };
}
```

## Customization Ideas

1. **Domain-specific checks** - Add checks for your data type
2. **ML-based scoring** - Train a model on quality data
3. **Automated feedback** - Send improvement suggestions to providers
4. **Quality SLAs** - Enforce minimum quality levels
5. **Quality badges** - Award badges to high-quality providers

## Next Steps

- Customize quality checks for your domain
- Add domain-specific validation rules
- Implement feedback automation
- Set up quality dashboards
- Test with Kit H (Servicing Agent)

## Related

- [Kit G: Requesting Agent](../kit-g-requesting-agent/) - Request services
- [Kit H: Servicing Agent](../kit-h-servicing-agent/) - Provide services
- [Kit I: ROI Governor](../kit-i-roi-governor/) - Monitor spending
- [Track 2 Overview](../../docs/tracks/track-2-internal-a2a.md)
