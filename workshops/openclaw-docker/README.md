# OpenClaw + Nevermined x402 Demo (Docker)

Two OpenClaw instances in Docker containers communicating via x402 payments — one seller (paid endpoint) and one buyer (using `nevermined_queryAgent`).

## Architecture

```
┌─────────────────────────┐     x402 HTTP      ┌─────────────────────────┐
│  Container: buyer       │ ──────────────────> │  Container: seller      │
│                         │                     │                         │
│  OpenClaw gateway       │                     │  OpenClaw gateway       │
│  + Nevermined plugin    │                     │  + Nevermined plugin    │
│    (subscriber config)  │                     │    (builder config)     │
│                         │                     │    enablePaidEndpoint   │
│  Web UI :18790          │                     │  Web UI :18789          │
└─────────────────────────┘                     └─────────────────────────┘
```

## Quick Start

```bash
docker-compose up --build
```

- Seller UI: http://localhost:18789
- Buyer UI: http://localhost:18790

## Demo Flow

### 1. Seller Setup (http://localhost:18789)

Login with your seller API key:
```
/nvm_login <seller-api-key>
```

Register an agent and plan:
```
Register an agent called "Weather Oracle" at URL http://seller:18789/nevermined/agent
with a plan named "Weather" priced at 1000000 to address 0x...
with token 0x036CbD53842c5426634e7929541eC2318f3dCF7e granting 100 credits
```

Note the returned `planId` and `agentId`.

### 2. Buyer Setup (http://localhost:18790)

Login with your buyer API key:
```
/nvm_login <buyer-api-key>
```

Subscribe to the seller's plan:
```
Order plan <planId>
```

Check balance:
```
Check my balance for plan <planId>
```

### 3. Payment Flow

Send a paid query from the buyer:
```
Query the agent at http://seller:18789/nevermined/agent about the weather in Barcelona,
using plan <planId> and agent <agentId>
```

Verify the response returned and credits decreased.

## Teardown

```bash
docker-compose down
```

## Notes

- Both containers share a Docker network (`nvm-demo`) so the buyer can reach the seller at `http://seller:18789`
- The `.env` file is a reference for API keys — paste them into the web UIs during the live demo
- `enablePaidEndpoint` is set for both containers (harmless on buyer side)
- All Nevermined setup (login, plan registration, ordering) happens live during the demo
