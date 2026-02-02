# Track 2: Internal A2A Economy

Build agent-to-agent transaction systems for internal organizational workflows.

## Overview

**Theme**: Enterprise Agent Economy

**Challenge**: Create AI agents that can transact with each other within an organization - requesting services, providing services, tracking costs, and optimizing spending across agent teams.

## Use Cases

1. **Quality Assessment Agent** - Evaluates outputs from other agents
2. **Service Requesting Agent** - Requests work from specialized agents
3. **Service Provider Agent** - Provides specialized services to other agents
4. **ROI Governor** - Monitors spending and optimizes agent budgets

## Starter Kits

### Kit F: Quality Assessment Agent

An agent that evaluates the quality of outputs from other agents.

**Features:**
- Quality scoring algorithms
- A2A transaction for assessment requests
- Feedback loop to providers
- Quality history tracking

**Key Code:**

```typescript
interface AssessmentRequest {
  requestId: string;
  data: any;
  expectedFormat: string;
  qualityThreshold: number;
}

interface AssessmentResult {
  requestId: string;
  score: number;
  passed: boolean;
  feedback: string[];
}

async function assessQuality(request: AssessmentRequest): Promise<AssessmentResult> {
  const { data, expectedFormat, qualityThreshold } = request;

  // Run quality checks
  const checks = [
    checkCompleteness(data),
    checkFormat(data, expectedFormat),
    checkAccuracy(data),
    checkConsistency(data),
  ];

  const results = await Promise.all(checks);
  const score = results.reduce((sum, r) => sum + r.score, 0) / results.length;

  return {
    requestId: request.requestId,
    score,
    passed: score >= qualityThreshold,
    feedback: results.flatMap(r => r.issues),
  };
}
```

### Kit G: Requesting Agent

An agent that requests services from other agents in the organization.

**Features:**
- Service discovery
- Request routing
- Response aggregation
- Budget allocation per request

**Key Code:**

```typescript
interface ServiceRequest {
  serviceType: string;
  payload: any;
  maxBudget: number;
  deadline?: Date;
}

const serviceProviders: Map<string, AgentEndpoint> = new Map([
  ["data-analysis", { url: "http://analysis-agent:3000", planId: "plan-analysis" }],
  ["summarization", { url: "http://summarize-agent:3000", planId: "plan-summarize" }],
  ["translation", { url: "http://translate-agent:3000", planId: "plan-translate" }],
]);

async function requestService(request: ServiceRequest) {
  const provider = serviceProviders.get(request.serviceType);
  if (!provider) {
    throw new Error(`No provider for service: ${request.serviceType}`);
  }

  // Get payment token
  const { accessToken } = await payments.x402.getX402AccessToken(provider.planId);

  // Make request
  const response = await fetch(`${provider.url}/execute`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "payment-signature": accessToken,
    },
    body: JSON.stringify(request.payload),
  });

  return response.json();
}
```

### Kit H: Servicing Agent

An agent that provides specialized services to other agents.

**Features:**
- Service registration
- Request handling
- Payment verification
- Service level tracking

**Key Code:**

```typescript
// Register services with different pricing
app.use(paymentMiddleware(payments, {
  "POST /analyze": { planId: PLAN_ID, credits: 5 },
  "POST /summarize": { planId: PLAN_ID, credits: 2 },
  "POST /translate": { planId: PLAN_ID, credits: 3 },
}));

// Service implementation
app.post("/analyze", async (req, res) => {
  const { data, analysisType } = req.body;

  const result = await performAnalysis(data, analysisType);

  res.json({
    result,
    serviceMetadata: {
      processingTime: Date.now() - req.startTime,
      analysisType,
    },
  });
});
```

### Kit I: ROI Governor Agent

An agent that monitors and optimizes spending across all agents.

**Features:**
- Spending dashboard
- Budget allocation
- Cost anomaly detection
- ROI optimization recommendations

**Key Code:**

```typescript
interface AgentSpending {
  agentId: string;
  planId: string;
  creditsUsed: number;
  totalCost: number;
  requestCount: number;
}

interface BudgetAllocation {
  agentId: string;
  dailyBudget: number;
  weeklyBudget: number;
  currentSpend: number;
}

class ROIGovernor {
  private budgets: Map<string, BudgetAllocation> = new Map();
  private spending: AgentSpending[] = [];

  async checkBudget(agentId: string, requestedCredits: number): Promise<boolean> {
    const budget = this.budgets.get(agentId);
    if (!budget) return false;

    return (budget.currentSpend + requestedCredits) <= budget.dailyBudget;
  }

  async recordSpending(spending: AgentSpending): void {
    this.spending.push(spending);

    const budget = this.budgets.get(spending.agentId);
    if (budget) {
      budget.currentSpend += spending.totalCost;
    }
  }

  async getRecommendations(): Promise<Recommendation[]> {
    // Analyze spending patterns
    const recommendations: Recommendation[] = [];

    // Find high-cost, low-value agents
    for (const agent of this.spending) {
      const roi = calculateROI(agent);
      if (roi < THRESHOLD) {
        recommendations.push({
          agentId: agent.agentId,
          action: "reduce_budget",
          reason: `Low ROI: ${roi.toFixed(2)}`,
        });
      }
    }

    return recommendations;
  }
}
```

## Technical Requirements

### Protocol: A2A

Agent-to-Agent transactions use the A2A protocol for direct agent communication with integrated payments.

### Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Organization                             │
│                                                            │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│   │  Requesting │───>│  Servicing  │<───│  Quality    │   │
│   │    Agent    │    │    Agent    │    │  Assessment │   │
│   │    (Kit G)  │    │   (Kit H)   │    │   (Kit F)   │   │
│   └─────────────┘    └─────────────┘    └─────────────┘   │
│          │                 │                  │            │
│          └─────────────────┼──────────────────┘            │
│                           │                               │
│                    ┌──────┴──────┐                        │
│                    │ ROI Governor│                        │
│                    │   (Kit I)   │                        │
│                    └─────────────┘                        │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Judging Criteria

1. **Integration** (25%) - How well do agents work together?
2. **Economic Efficiency** (25%) - Smart budget and cost management
3. **Autonomy** (20%) - Minimal human intervention needed
4. **Observability** (15%) - Visibility into agent transactions
5. **Code Quality** (15%) - Clean, maintainable code

## Ideas to Explore

- **Agent marketplace** - Internal service catalog
- **SLA enforcement** - Guarantee service levels with payments
- **Cost prediction** - Estimate costs before execution
- **Cross-department billing** - Track costs by team
- **Efficiency competitions** - Reward cost-effective agents
- **Fallback strategies** - Handle provider failures gracefully

## Resources

- [Kit F: Quality Assessment](../../starter-kits/kit-f-quality-assessment/)
- [Kit G: Requesting Agent](../../starter-kits/kit-g-requesting-agent/)
- [Kit H: Servicing Agent](../../starter-kits/kit-h-servicing-agent/)
- [Kit I: ROI Governor](../../starter-kits/kit-i-roi-governor/)
- [A2A Protocol Examples](https://github.com/nevermined-io/hackathons/tree/main/examples/a2a)
