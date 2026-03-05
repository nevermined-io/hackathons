# TOOLS.md - Nevermined Demo

## Nevermined

- **App URL**: https://nevermined.app (NOT app.nevermined.app)
- **API Keys**: Get from https://nevermined.app > API Keys > Global NVM API Keys
- **Environment**: sandbox (for testing). API keys start with `sandbox:`
- **Docs**: https://nevermined.ai/docs

### Authentication

Use `/nvm_login <api-key>` to authenticate. API keys look like `sandbox:eyJhbG...`

### Available Nevermined Tools

- `nevermined_checkBalance` — check credit balance for a plan
- `nevermined_getAccessToken` — get an x402 access token
- `nevermined_orderPlan` — purchase a payment plan
- `nevermined_queryAgent` — send a paid query to an agent
- `nevermined_registerAgent` — register an agent with a payment plan
- `nevermined_createPlan` — create a standalone payment plan
- `nevermined_listPlans` — list your payment plans
