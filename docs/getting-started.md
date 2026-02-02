# Getting Started

This guide will help you set up your development environment and run your first payment-enabled AI agent.

## Prerequisites

- **Node.js 18+** (for TypeScript starter kits)
- **Python 3.10+** (for Python starter kits)
- **Git** for cloning repositories

## Step 1: Get Your Nevermined API Key

1. Go to [https://nevermined.app/](https://nevermined.app/)
2. Log in using Web3Auth (Google, email, or crypto wallet)
3. Navigate to **Settings** > **API Keys**
4. Click **Generate new key**
5. Copy the key (starts with `nvm:`)

## Step 2: Create a Payment Plan

A payment plan controls how users pay to access your agent.

1. In the Nevermined App, click **"Create Agent"** or **"My Pricing Plans"**
2. Fill in your agent metadata (name, description)
3. **Register API Endpoints**: Add the endpoints you want to protect
   - For HTTP agents: `POST /ask`, `GET /data`, etc.
   - For MCP: Use logical URLs like `mcp://my-agent/tools/my-tool`
4. Create a payment plan:
   - **Credit-based**: Pay per request (recommended for hackathon)
   - **Time-based**: Pay for access period
   - **Trial**: Free trial for testing
5. Copy your **Plan ID** from the plan details

## Step 3: Set Up Your Environment

```bash
# Clone the hackathons repository
git clone https://github.com/nevermined-io/hackathons.git
cd hackathons

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
```

Your `.env` file should contain:

```bash
NVM_API_KEY=nvm:your-api-key-here
NVM_ENVIRONMENT=sandbox
NVM_PLAN_ID=your-plan-id-here
OPENAI_API_KEY=sk-your-openai-key
PORT=3000
```

## Step 4: Choose a Starter Kit

### For Track 1 (Data Marketplace)

Start with **Kit A (Buyer Agent)** or **Kit B (Selling Agent)**:

```bash
cd starter-kits/kit-a-buyer-agent

# TypeScript
yarn install
yarn agent

# OR Python
poetry install
poetry run agent
```

### For Track 2 (Internal A2A Economy)

Start with **Kit G (Requesting Agent)** or **Kit H (Servicing Agent)**:

```bash
cd starter-kits/kit-g-requesting-agent
yarn install
yarn agent
```

### For Track 3 (Content Marketplace)

Start with **Kit D (Publisher Agent)** or **Kit E (Consuming Agent)**:

```bash
cd starter-kits/kit-d-publisher-agent
yarn install
yarn agent
```

## Step 5: Test Your Agent

In a new terminal, run the client:

```bash
# TypeScript
yarn client

# Python
poetry run client
```

You should see:

1. **402 Payment Required** - First request without token
2. **Token generation** - Client gets x402 access token
3. **200 OK** - Second request with token succeeds

## Understanding the x402 Flow

```
┌─────────┐                              ┌─────────┐
│  Client │                              │  Agent  │
└────┬────┘                              └────┬────┘
     │                                        │
     │  1. POST /ask (no token)               │
     │───────────────────────────────────────>│
     │                                        │
     │  2. 402 Payment Required               │
     │     Header: payment-required           │
     │<───────────────────────────────────────│
     │                                        │
     │  3. Generate x402 token via SDK        │
     │                                        │
     │  4. POST /ask                          │
     │     Header: payment-signature          │
     │───────────────────────────────────────>│
     │                                        │
     │  5. 200 OK + response                  │
     │     Header: payment-response           │
     │<───────────────────────────────────────│
```

## Next Steps

1. **Customize your agent** - Modify the business logic
2. **Add more endpoints** - Protect additional routes
3. **Deploy to AWS** - See [AWS Integration](./aws-integration.md)
4. **Explore other kits** - Combine kits for complex scenarios

## Troubleshooting

### "NVM_API_KEY is required"

Make sure your `.env` file exists and contains valid credentials.

### "402 Payment Required" keeps failing

1. Verify your `NVM_PLAN_ID` is correct
2. Check that you have credits in your plan
3. Ensure the endpoint URL matches your plan configuration

### "Invalid token"

1. Tokens expire - generate a new one
2. Check that you're using the correct plan ID

## Resources

- [Nevermined Documentation](https://nevermined.ai/docs)
- [x402 Protocol Spec](https://github.com/coinbase/x402)
- [Support Discord](https://discord.com/invite/GZju2qScKq)
