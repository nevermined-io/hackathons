# Deploy to AWS Bedrock AgentCore

This guide walks you through deploying Nevermined payment-enabled agents to AWS Bedrock AgentCore. It covers the seller (A2A server with payment verification) and buyer (web client with SigV4-signed requests) agents from this repo.

**Working examples:** `agents/seller-simple-agent/` and `agents/buyer-simple-agent/`

---

## Quick Deploy

Deploy both agents with a single command:

```bash
# Set your credentials
export SELLER_NVM_API_KEY=sandbox:...   # Seller's key (builder/publisher)
export BUYER_NVM_API_KEY=sandbox:...    # Buyer's key (subscriber)
export NVM_PLAN_ID=...                  # Seller's payment plan ID
export NVM_AGENT_ID=...                 # Seller's agent ID
export OPENAI_API_KEY=sk-...

# Optional (defaults shown)
export AWS_REGION=us-west-2
export NVM_ENVIRONMENT=sandbox

# Deploy seller + buyer to AgentCore
./scripts/deploy-agentcore.sh
```

The script will:
1. Check prerequisites (AWS CLI, AgentCore toolkit, Docker)
2. Create `.bedrock_agentcore.yaml` from the example templates (filling in your AWS account and region)
3. Deploy the seller agent and capture its ARN
4. Deploy the buyer agent with the seller ARN injected
5. Print both ARNs and next steps

To redeploy only the buyer (e.g., after updating code):

```bash
export SKIP_SELLER=1
export SELLER_AGENT_ARN=arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:runtime/seller_agent-XXX
./scripts/deploy-agentcore.sh
```

Test the deployment:

```bash
./scripts/test-agentcore.sh
```

For the full manual walkthrough, continue reading below.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [How AgentCore Changes the Payment Flow](#how-agentcore-changes-the-payment-flow)
3. [Deploy the Seller Agent](#deploy-the-seller-agent)
4. [Deploy the Buyer Agent](#deploy-the-buyer-agent)
5. [Test the Deployment](#test-the-deployment)
6. [Environment Variables Reference](#environment-variables-reference)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### AWS

- **AWS account** with Bedrock AgentCore access (request via the AWS console)
- **AWS CLI v2** installed and configured (`aws configure`)
- **Bedrock AgentCore Toolkit** installed:
  ```bash
  pip install bedrock-agentcore
  ```
- **Docker** installed and running
- **IAM permissions**: Your AWS user/role needs permissions for Bedrock AgentCore, ECR, CodeBuild, and Secrets Manager

### Nevermined

- **API Key** — get one at [nevermined.app](https://nevermined.app) > API Keys
- **Payment Plan** — create one at [nevermined.app](https://nevermined.app) > My Pricing Plans
- **Plan ID** and **Agent ID** from your plan

### Verify your setup

```bash
# AWS
aws sts get-caller-identity          # Should show your account
aws bedrock-agentcore help 2>&1 | head -5  # Should not error

# Bedrock AgentCore Toolkit
agentcore --version

# Docker
docker info > /dev/null && echo "Docker OK"
```

---

## How AgentCore Changes the Payment Flow

When you run agents locally, x402 payment tokens travel in the `payment-signature` HTTP header. AgentCore's proxy changes two things:

### Problem 1: Header Stripping

AgentCore's proxy **strips all custom HTTP headers** except those prefixed with `X-Amzn-Bedrock-AgentCore-Runtime-Custom-`. This means `payment-signature` never reaches your seller agent.

**Solution (seller side):** Add a header remapping middleware that copies `X-Amzn-Bedrock-AgentCore-Runtime-Custom-Payment-Signature` → `payment-signature` before the payment middleware sees it. Also configure a **request header allowlist** in the AgentCore config so the proxy lets the custom header through.

### Problem 2: SigV4 Authentication

AgentCore requires all incoming requests to be **SigV4-signed** using AWS credentials. A buyer agent can't just POST to the seller's AgentCore URL — the request must be signed.

**Solution (buyer side):** Use an httpx auth class that applies SigV4 signing to every outgoing request. Inside AgentCore containers, AWS credentials are available via the ECS task role (no hardcoded keys needed).

### Problem 3: Agent Card Discovery

The A2A protocol's agent card endpoint (`GET /.well-known/agent.json`) doesn't work through AgentCore's proxy because AgentCore routes everything to `POST /invocations`.

**Solution (buyer side):** Pre-register the seller from the `SELLER_AGENT_ARN` environment variable instead of fetching the agent card at runtime.

### The Full Picture

```
Local flow:
  Buyer --[payment-signature: token]--> Seller
  Simple. Headers pass through. Done.

AgentCore flow:
  Buyer
    1. Build AgentCore URL from seller ARN
    2. Send token in BOTH headers:
       - payment-signature (standard, will be stripped)
       - X-Amzn-Bedrock-AgentCore-Runtime-Custom-Payment-Signature (survives proxy)
    3. SigV4-sign the request
    --> AgentCore Proxy (strips payment-signature, keeps custom header)
    --> Seller Middleware (copies custom header -> payment-signature)
    --> Payment Middleware (verifies payment-signature as normal)
```

---

## Deploy the Seller Agent

The seller is an A2A server with payment-protected tools. Its AgentCore entry point is `src/agent_a2a_agentcore.py`.

### Step 1: Initialize AgentCore project

```bash
cd agents/seller-simple-agent

# Initialize with the AgentCore toolkit (interactive)
agentcore init
```

This creates `.bedrock_agentcore.yaml` and `.bedrock_agentcore/` directory. When prompted:

| Prompt | Value |
|--------|-------|
| Agent name | `seller_agent` (or your choice) |
| Language | `python` |
| Deployment type | `container` |
| Entry point | `src/agent_a2a_agentcore.py` |
| Platform | `linux/arm64` (or `linux/amd64`) |

### Step 2: Configure the header allowlist

This is **critical**. Without it, the payment header is stripped by the proxy.

Edit `.bedrock_agentcore.yaml` and add:

```yaml
    request_header_configuration:
      requestHeaderAllowlist:
      - X-Amzn-Bedrock-AgentCore-Runtime-Custom-Payment-Signature
```

This goes under your agent's configuration block (same level as `aws`, `bedrock_agentcore`, etc.).

### Step 3: Set environment variables

Your agent needs `NVM_API_KEY`, `NVM_ENVIRONMENT`, `NVM_PLAN_ID`, `NVM_AGENT_ID`, and `OPENAI_API_KEY`. There are two approaches:

**Option A: AWS Secrets Manager (recommended for production)**

```bash
aws secretsmanager create-secret \
    --name hackathon/seller-agent \
    --region us-west-2 \
    --secret-string '{
        "NVM_API_KEY": "sandbox:your-api-key",
        "NVM_ENVIRONMENT": "sandbox",
        "NVM_PLAN_ID": "your-plan-id",
        "NVM_AGENT_ID": "your-agent-id",
        "OPENAI_API_KEY": "sk-your-key"
    }'
```

Then configure the agent runtime to pull from Secrets Manager (via the AgentCore console or API).

**Option B: `.env` file in container (quick for hackathon)**

Create a `.env` file with your credentials and ensure the Dockerfile copies it:

```dockerfile
# Add to Dockerfile before the CMD line:
COPY .env .env
```

> **Warning:** Don't commit `.env` files with real credentials. Add `.env` to `.gitignore`.

### Step 4: Build and deploy

```bash
# Build and deploy via the AgentCore toolkit
agentcore deploy
```

This will:
1. Build the Docker image
2. Push it to ECR
3. Create/update the agent runtime in AgentCore
4. Return the agent ARN

Save the **agent ARN** — the buyer needs it:

```
arn:aws:bedrock-agentcore:us-west-2:YOUR_ACCOUNT:runtime/seller_agent-XXXXXXXXXX
```

### Step 5: Verify the seller is running

```bash
# Check agent status
agentcore status seller_agent

# Test the health check (via direct invocation)
aws bedrock-agentcore invoke-agent-runtime \
    --agent-runtime-arn "arn:aws:bedrock-agentcore:us-west-2:YOUR_ACCOUNT:runtime/seller_agent-XXXXXXXXXX" \
    --qualifier DEFAULT \
    --payload '{"method": "ping"}' \
    --region us-west-2 \
    output.json && cat output.json
```

### What the seller's AgentCore code does

The key file is `src/agent_a2a_agentcore.py`. It:

1. **Reads `PORT` and `AGENT_URL`** from env vars set by AgentCore runtime
2. **Creates the A2A server** with payment verification hooks
3. **Adds `AgentCoreHeaderMiddleware`** that:
   - Remaps `/invocations` → `/` (AgentCore routes all traffic to `/invocations`)
   - Copies `X-Amzn-Bedrock-AgentCore-Runtime-Custom-Payment-Signature` → `payment-signature`
4. The middleware is added **after** `PaymentsA2AServer.start()` because Starlette executes middleware in reverse order — so the header remapping runs first

---

## Deploy the Buyer Agent

The buyer is a web server that discovers sellers and makes purchases. Its AgentCore entry point is `src/web_agentcore.py`.

### Step 1: Initialize AgentCore project

```bash
cd agents/buyer-simple-agent

agentcore init
```

When prompted:

| Prompt | Value |
|--------|-------|
| Agent name | `buyer_agent` (or your choice) |
| Language | `python` |
| Deployment type | `container` |
| Entry point | `src/web_agentcore.py` |
| Platform | `linux/arm64` (or `linux/amd64`) |

### Step 2: Set environment variables

The buyer needs the same Nevermined variables **plus** the seller's ARN:

```bash
aws secretsmanager create-secret \
    --name hackathon/buyer-agent \
    --region us-west-2 \
    --secret-string '{
        "NVM_API_KEY": "sandbox:your-api-key",
        "NVM_ENVIRONMENT": "sandbox",
        "NVM_PLAN_ID": "your-plan-id",
        "NVM_AGENT_ID": "your-agent-id",
        "OPENAI_API_KEY": "sk-your-key",
        "SELLER_AGENT_ARN": "arn:aws:bedrock-agentcore:us-west-2:ACCOUNT:runtime/seller_agent-XXXXXXXXXX"
    }'
```

The buyer does **not** need a header allowlist (it's a client, not a server receiving custom headers).

### Step 3: Build and deploy

```bash
agentcore deploy
```

### Step 4: Verify the buyer is running

```bash
agentcore status buyer_agent
```

### What the buyer's AgentCore code does

Two key files:

**`src/web_agentcore.py`:**
1. Injects `AgentCorePaymentsClient` as the payment client class (SigV4 + dual headers)
2. Reads `SELLER_AGENT_ARN` and computes the AgentCore invocation URL
3. Pre-registers the seller with a synthetic agent card (since `GET /.well-known/agent.json` doesn't work through the proxy)
4. Adds `AgentCorePathMiddleware` that rewrites `/invocations` → `/api/chat`

**`src/agentcore_payments_client.py`:**
1. **`build_agentcore_url(arn, region)`** — converts an agent ARN to `https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT`
2. **`SigV4HttpxAuth`** — httpx auth class that signs every request using the container's IAM role credentials. Only signs `host`, `content-type`, and `x-amzn-*` headers to avoid signature mismatches
3. **`AgentCorePaymentsClient`** — extends `PaymentsClient` with:
   - Dual headers: sends token in both `payment-signature` and `x-amzn-bedrock-agentcore-runtime-custom-payment-signature`
   - SigV4 signing on the httpx client (auto-detected when URL contains `bedrock-agentcore`)
   - URL fix: strips trailing `/` that the base class adds (would break the `?qualifier=DEFAULT` query string)

---

## Test the Deployment

### End-to-end test

Once both agents are deployed, test the payment flow:

```bash
# 1. Invoke the buyer agent
aws bedrock-agentcore invoke-agent-runtime \
    --agent-runtime-arn "arn:aws:bedrock-agentcore:us-west-2:YOUR_ACCOUNT:runtime/buyer_agent-XXXXXXXXXX" \
    --qualifier DEFAULT \
    --payload '{"prompt": "Search for AI market trends"}' \
    --region us-west-2 \
    output.json

cat output.json
```

### What success looks like

In the **seller logs**, you should see:

```
[MIDDLEWARE] [REMAP] copied AgentCore custom header -> payment-signature
[PAYMENT] [VERIFY] method=message/send token=eyJhbGci...
[PAYMENT] [VERIFIED] method=message/send status=ok
```

In the **buyer logs**, you should see:

```
[SIGV4] [SIGNED] method=POST url=https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/...
[CLIENT] [SIGV4] SigV4 auth enabled for httpx client
```

### View logs

```bash
# Via AgentCore toolkit
agentcore logs seller_agent --follow
agentcore logs buyer_agent --follow
```

---

## Environment Variables Reference

### Seller Agent

| Variable | Required | Description |
|----------|----------|-------------|
| `NVM_API_KEY` | Yes | Nevermined builder/seller API key |
| `NVM_ENVIRONMENT` | Yes | `sandbox`, `staging_sandbox`, or `live` |
| `NVM_PLAN_ID` | Yes | Your payment plan ID |
| `NVM_AGENT_ID` | Yes | Your agent ID (required for A2A mode) |
| `OPENAI_API_KEY` | Yes | OpenAI API key for LLM inference |
| `MODEL_ID` | No | OpenAI model (default: `gpt-4o-mini`) |
| `PORT` | No | Set by AgentCore runtime (default: `8080`) |
| `AGENT_URL` | No | Set by AgentCore runtime (public URL) |

### Buyer Agent

| Variable | Required | Description |
|----------|----------|-------------|
| `NVM_API_KEY` | Yes | Nevermined subscriber API key |
| `NVM_ENVIRONMENT` | Yes | `sandbox`, `staging_sandbox`, or `live` |
| `NVM_PLAN_ID` | Yes | The seller's plan ID you subscribed to |
| `NVM_AGENT_ID` | No | Seller's agent ID (for token scoping) |
| `OPENAI_API_KEY` | Yes | OpenAI API key for LLM inference |
| `SELLER_AGENT_ARN` | Yes* | Seller's AgentCore runtime ARN (*AgentCore only) |
| `AWS_REGION` | No | AWS region (default: `us-west-2`) |
| `PORT` | No | Set by AgentCore runtime (default: `8080`) |
| `AGENT_URL` | No | Set by AgentCore runtime (public URL) |

---

## Troubleshooting

### `payment-signature` header not found (402 Payment Required)

**Cause:** The header allowlist is not configured, so AgentCore strips the payment header.

**Fix:** Add to the seller's `.bedrock_agentcore.yaml`:

```yaml
    request_header_configuration:
      requestHeaderAllowlist:
      - X-Amzn-Bedrock-AgentCore-Runtime-Custom-Payment-Signature
```

Then redeploy: `agentcore deploy`

### SigV4 signature mismatch (403 Forbidden)

**Cause:** The SigV4 signature includes headers that get modified by httpx after signing.

**Fix:** The `SigV4HttpxAuth` class only signs `host`, `content-type`, and `x-amzn-*` headers. If you've added custom headers, make sure they're included in the signing set. Check `agentcore_payments_client.py:86-92`.

### Seller not found / connection timeout

**Cause:** The buyer can't reach the seller's AgentCore endpoint.

**Fix:**
1. Verify the seller ARN is correct: `agentcore status seller_agent`
2. Check that `SELLER_AGENT_ARN` is set in the buyer's environment
3. Verify both agents are in the same AWS region
4. Check that the buyer's IAM role has `bedrock-agentcore:InvokeAgentRuntime` permission

### Path not found / 404 errors

**Cause:** AgentCore routes all traffic to `POST /invocations`, but your agent expects different paths.

**Fix:** Both agents include path rewrite middleware:
- Seller: `/invocations` → `/` (A2A JSON-RPC handler)
- Buyer: `/invocations` → `/api/chat` (chat handler)

If you're building a new agent, add similar middleware. See `agent_a2a_agentcore.py:79-85` and `web_agentcore.py:122-127`.

### Agent card discovery fails

**Cause:** `GET /.well-known/agent.json` doesn't work through AgentCore's proxy.

**Fix:** Use pre-registration instead. Set `SELLER_AGENT_ARN` and the buyer will build a synthetic agent card. See `web_agentcore.py:62-104`.

### URL mangling (`?qualifier=DEFAULT/`)

**Cause:** The base `PaymentsClient` appends `/` to URLs, which breaks the AgentCore query string.

**Fix:** `AgentCorePaymentsClient` strips trailing `/` from AgentCore URLs automatically. If you're extending the client, call `self._agent_base_url.rstrip("/")` after `super().__init__()`.

### Container fails to start

Common issues:
1. **Missing dependencies**: Make sure your Dockerfile installs all extras (`poetry install` not `poetry install -E agentcore` — the Dockerfile handles this)
2. **Wrong entry point**: Check that the `CMD` in your Dockerfile matches the entry point in `.bedrock_agentcore.yaml`
3. **Port mismatch**: Use `PORT` env var (set by AgentCore), not a hardcoded port

### AWS credentials not found inside container

**Cause:** The container can't find IAM credentials for SigV4 signing.

**Fix:** Inside AgentCore containers, credentials come from the ECS task role automatically. The `SigV4HttpxAuth` class uses `boto3.Session().get_credentials()` which reads the container credential provider. Make sure your agent's execution role has the necessary permissions.

---

## Adapting Your Own Agent

To deploy your own agent to AgentCore with Nevermined payments:

### If your agent is a seller (receives payments)

1. Add `AgentCoreHeaderMiddleware` to remap the payment header (copy from `agent_a2a_agentcore.py:67-99`)
2. Add path rewrite middleware for `/invocations` → your handler path
3. Configure the header allowlist in `.bedrock_agentcore.yaml`
4. Use `PORT` and `AGENT_URL` env vars from AgentCore

### If your agent is a buyer (makes payments)

1. Use `AgentCorePaymentsClient` instead of `PaymentsClient` (copy from `agentcore_payments_client.py`)
2. Pre-register sellers from ARN env vars (agent card discovery won't work)
3. Set `SELLER_AGENT_ARN` in your environment

### Key files to copy/adapt

| File | Role | What it does |
|------|------|-------------|
| `seller-simple-agent/src/agent_a2a_agentcore.py` | Seller | Header remapping + path rewrite middleware |
| `buyer-simple-agent/src/agentcore_payments_client.py` | Buyer | SigV4 signing + dual headers + URL handling |
| `buyer-simple-agent/src/web_agentcore.py` | Buyer | Seller pre-registration + path rewrite |
