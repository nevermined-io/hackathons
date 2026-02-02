# Shared Utilities

Common utilities and helpers used across starter kits.

## Contents

- **payments/** - Nevermined payment utilities
- **types/** - Common TypeScript types
- **config/** - Configuration helpers
- **testing/** - Test utilities

## Installation

These utilities are automatically available in each starter kit. To use them directly:

```typescript
// TypeScript
import { createPaymentsClient, BudgetManager } from '../shared';
```

```python
# Python
from shared import create_payments_client, BudgetManager
```

## Utilities

### Payments Client

Factory for creating configured Payments instances:

```typescript
import { createPaymentsClient } from './shared/payments';

const payments = createPaymentsClient({
  apiKey: process.env.NVM_API_KEY,
  environment: process.env.NVM_ENVIRONMENT,
});
```

### Budget Manager

Track and enforce spending limits:

```typescript
import { BudgetManager } from './shared/budget';

const budget = new BudgetManager({
  dailyLimit: 100,
  perRequestLimit: 10,
});

if (await budget.canSpend(5)) {
  await budget.recordSpending(5);
}
```

### Request Tracker

Track requests and responses:

```typescript
import { RequestTracker } from './shared/tracking';

const tracker = new RequestTracker();

tracker.recordRequest({
  requestId: 'req-123',
  endpoint: '/data',
  credits: 5,
});
```

### Configuration

Load and validate environment configuration:

```typescript
import { loadConfig, validateConfig } from './shared/config';

const config = loadConfig();
validateConfig(config, ['NVM_API_KEY', 'NVM_PLAN_ID']);
```

## Development

To add new shared utilities:

1. Create the utility in the appropriate directory
2. Export from `index.ts`
3. Update this README
4. Test across multiple kits
