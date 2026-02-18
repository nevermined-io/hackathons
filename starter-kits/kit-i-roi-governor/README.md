# Kit I: ROI Governor Agent

An agent that monitors and optimizes spending across all organizational agents.

**Track:** 2 - Internal A2A Economy
**Protocol:** A2A/x402
**Languages:** TypeScript

## Features

- Real-time spending dashboard
- Budget allocation and enforcement
- Cost anomaly detection
- ROI optimization recommendations
- Automated budget adjustments

## Quick Start

```bash
yarn install
cp .env.example .env
# Edit .env with your credentials
yarn agent   # Start the ROI governor
yarn demo    # Run the demo
```

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    ROI Governor                         │
│                      (Kit I)                            │
└─────────────────────────────────────────────────────────┘
         │              │              │
         │  Monitor     │  Allocate    │  Optimize
         ▼              ▼              ▼
   ┌───────────┐  ┌───────────┐  ┌───────────┐
   │ Requesting │  │ Servicing │  │  Quality  │
   │   Agent    │  │   Agent   │  │ Assessment│
   │  (Kit G)   │  │  (Kit H)  │  │  (Kit F)  │
   └───────────┘  └───────────┘  └───────────┘
```

The ROI Governor:
1. **Monitors** spending across all agents
2. **Allocates** budgets based on priorities
3. **Optimizes** spending for maximum ROI
4. **Alerts** on anomalies and budget overruns

## Configuration

### Environment Variables

```bash
# Required
NVM_API_KEY=sandbox:your-api-key
NVM_ENVIRONMENT=sandbox

# Budget settings
TOTAL_BUDGET=10000
BUDGET_PERIOD=daily
ALERT_THRESHOLD=0.8  # Alert at 80% spend

# Optimization
ENABLE_AUTO_OPTIMIZATION=true
OPTIMIZATION_INTERVAL=3600  # seconds

# Optional
PORT=3000
```

## API

### GET /dashboard

Get spending dashboard.

**Response:**
```json
{
  "period": "2024-03-05",
  "totalBudget": 10000,
  "totalSpent": 4500,
  "utilizationRate": 0.45,
  "byAgent": [
    {
      "agentId": "requesting-agent-1",
      "agentName": "Data Analysis Requester",
      "budget": 3000,
      "spent": 2000,
      "utilization": 0.67,
      "roi": 2.5
    },
    {
      "agentId": "requesting-agent-2",
      "agentName": "Report Generator",
      "budget": 2000,
      "spent": 1500,
      "utilization": 0.75,
      "roi": 1.8
    }
  ],
  "byService": [
    {
      "serviceType": "data-analysis",
      "spent": 2500,
      "requests": 500,
      "avgCostPerRequest": 5
    }
  ],
  "alerts": [
    {
      "type": "budget_warning",
      "agentId": "requesting-agent-2",
      "message": "Approaching budget limit (75%)"
    }
  ]
}
```

### POST /budget

Allocate budget to an agent.

**Request:**
```json
{
  "agentId": "requesting-agent-1",
  "budget": 3500,
  "period": "daily"
}
```

**Response:**
```json
{
  "agentId": "requesting-agent-1",
  "previousBudget": 3000,
  "newBudget": 3500,
  "effectiveFrom": "2024-03-05T12:00:00Z"
}
```

### GET /recommendations

Get optimization recommendations.

**Response:**
```json
{
  "recommendations": [
    {
      "type": "reduce_budget",
      "agentId": "requesting-agent-2",
      "currentBudget": 2000,
      "recommendedBudget": 1500,
      "reason": "Low ROI (1.2) compared to average (2.0)",
      "estimatedSavings": 500
    },
    {
      "type": "increase_budget",
      "agentId": "requesting-agent-1",
      "currentBudget": 3000,
      "recommendedBudget": 4000,
      "reason": "High ROI (3.5) with budget constraints",
      "estimatedBenefit": "20% more output"
    },
    {
      "type": "switch_provider",
      "agentId": "requesting-agent-3",
      "currentProvider": "expensive-service",
      "recommendedProvider": "cost-effective-service",
      "reason": "Same quality, 40% lower cost"
    }
  ],
  "totalPotentialSavings": 800,
  "implementationPlan": [...]
}
```

### POST /optimize

Apply optimization recommendations.

**Request:**
```json
{
  "recommendations": ["rec-1", "rec-2"],
  "dryRun": false
}
```

**Response:**
```json
{
  "applied": [
    {
      "id": "rec-1",
      "status": "success",
      "changes": {...}
    }
  ],
  "failed": [],
  "estimatedSavings": 500
}
```

### GET /alerts

Get active alerts.

**Response:**
```json
{
  "alerts": [
    {
      "id": "alert-123",
      "type": "budget_exceeded",
      "severity": "high",
      "agentId": "requesting-agent-2",
      "message": "Daily budget exceeded by 15%",
      "timestamp": "2024-03-05T14:30:00Z",
      "acknowledged": false
    },
    {
      "id": "alert-124",
      "type": "anomaly_detected",
      "severity": "medium",
      "agentId": "requesting-agent-1",
      "message": "Unusual spending pattern detected",
      "timestamp": "2024-03-05T15:00:00Z",
      "acknowledged": false
    }
  ]
}
```

## ROI Calculation

```typescript
interface AgentMetrics {
  agentId: string;
  creditsSpent: number;
  outputValue: number;  // Measured or estimated
  qualityScore: number;
}

function calculateROI(metrics: AgentMetrics): number {
  // ROI = (Output Value - Cost) / Cost
  const cost = metrics.creditsSpent;
  const value = metrics.outputValue * metrics.qualityScore;
  return (value - cost) / cost;
}

function rankAgentsByROI(agents: AgentMetrics[]): AgentMetrics[] {
  return agents.sort((a, b) => calculateROI(b) - calculateROI(a));
}
```

## Anomaly Detection

```typescript
class AnomalyDetector {
  private history: SpendingHistory[] = [];
  private threshold: number = 2; // Standard deviations

  detect(current: SpendingData): Anomaly[] {
    const anomalies: Anomaly[] = [];

    // Check spending rate
    const avgSpendRate = this.calculateAvgSpendRate();
    const currentRate = current.spent / current.duration;

    if (Math.abs(currentRate - avgSpendRate) > this.threshold * this.stdDev) {
      anomalies.push({
        type: "spending_rate",
        message: `Unusual spending rate: ${currentRate} vs avg ${avgSpendRate}`,
        severity: "medium",
      });
    }

    // Check request patterns
    // ... more anomaly checks

    return anomalies;
  }
}
```

## Budget Enforcement

```typescript
class BudgetEnforcer {
  private budgets: Map<string, BudgetAllocation> = new Map();

  async checkBudget(agentId: string, requestedCredits: number): Promise<boolean> {
    const budget = this.budgets.get(agentId);
    if (!budget) return false;

    const remaining = budget.allocated - budget.spent;
    return requestedCredits <= remaining;
  }

  async recordSpending(agentId: string, credits: number): Promise<void> {
    const budget = this.budgets.get(agentId);
    if (budget) {
      budget.spent += credits;

      // Check alerts
      if (budget.spent / budget.allocated > ALERT_THRESHOLD) {
        await this.sendAlert(agentId, "budget_warning");
      }
    }
  }
}
```

## Customization Ideas

1. **ML-based forecasting** - Predict future spending
2. **Automated rebalancing** - Dynamically shift budgets
3. **Cost attribution** - Track costs to business outcomes
4. **Reporting** - Generate spending reports
5. **Approval workflows** - Require approval for large expenses

## Next Steps

- Connect to your agent network
- Define ROI metrics for your domain
- Set up alerting integrations
- Create custom dashboards
- Implement optimization strategies

## Related

- [Kit F: Quality Assessment](../kit-f-quality-assessment/) - Quality data for ROI
- [Kit G: Requesting Agent](../kit-g-requesting-agent/) - Track spending
- [Kit H: Servicing Agent](../kit-h-servicing-agent/) - Track revenue
- [Track 2 Overview](../../docs/tracks/track-2-internal-a2a.md)
