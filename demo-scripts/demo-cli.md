# Demo: A2A Buyer-Seller Marketplace (CLI)

Interactive CLI demo walking through the full A2A marketplace flow — starting with no sellers, adding them incrementally, discovering capabilities, and making purchases.

## Prerequisites

### Buyer Setup (`agents/buyer-simple-agent/`)

Create `.env`:

```bash
NVM_API_KEY=nvm:your-api-key
NVM_ENVIRONMENT=sandbox
NVM_PLAN_ID=your-plan-id
OPENAI_API_KEY=sk-your-key
```

Install:

```bash
cd agents/buyer-simple-agent
poetry install
```

### Seller Setup (`agents/seller-simple-agent/`)

Create `.env`:

```bash
NVM_API_KEY=nvm:your-api-key
NVM_ENVIRONMENT=sandbox
NVM_PLAN_ID=your-plan-id
NVM_AGENT_ID=your-agent-id       # required for seller (find in Nevermined App)
OPENAI_API_KEY=sk-your-key
```

Install:

```bash
cd agents/seller-simple-agent
poetry install
```

> **Note:** Use `poetry run python -m src.<module>` to run entry points (not `poetry run agent` or `poetry run agent-a2a`) because both projects use `package-mode = false`.

---

## For Humans: Step-by-Step

Open **3 terminal windows** side by side. Each step below tells you which terminal to use.

### Step 1 — Start the Buyer Agent (no sellers running)

**Terminal 1 (Buyer)**

```bash
cd agents/buyer-simple-agent
poetry run python -m src.agent
```

**Expected output:**

```
============================================================
Data Buying Agent — Interactive CLI
============================================================
Mode: a2a
Plan ID: <your-plan-id>
Registration: http://localhost:8000 (sellers register here)
Debug:        http://localhost:8000/sellers

Type your queries (or 'quit' to exit):
Examples:
  "What sellers are available?"
  "How many credits do I have?"
  "Search for the latest AI agent trends"

You:
```

**What's happening:** The buyer agent starts in A2A mode by default with tools (list_sellers, discover_agent, check_balance, purchase_a2a) and a registration server on port 8000. No sellers are running yet.

> **Tip:** Use `--mode http` for direct x402 HTTP mode (no registration server, uses `SELLER_URL` env var instead).

---

### Step 2 — Ask: "What sellers are available?"

**Terminal 1 (Buyer)** — type at the `You:` prompt:

```
What sellers are available?
```

**Expected output (key phrases):**

```
No sellers registered yet.
Sellers will appear here when they start with --buyer-url,
or you can discover one manually with discover_agent.
```

**What's happening:** The agent calls `list_sellers` which checks the local registry. It's empty because no sellers have started.

---

### Step 3 — Start Seller A (search only, port 9001)

**Terminal 2 (Seller A)**

```bash
cd agents/seller-simple-agent
poetry run python -m src.agent_a2a --tools search --port 9001 --buyer-url http://localhost:8000
```

**Expected output:**

```
15:06:26 | SERVER      | STARTUP     | Data Selling Agent — A2A Mode on port 9001
15:06:26 | SERVER      | STARTUP     | tools=[search] pricing=Credits vary by tool: search_data=1
15:06:26 | SERVER      | STARTUP     | will register with buyer at http://localhost:8000
...
15:06:28 | REGISTER    | SENDING     | buyer=http://localhost:8000 self=http://localhost:9001
15:06:28 | REGISTER    | SUCCESS     | registered with http://localhost:8000
```

**What's happening:** Seller A starts with only the `search` tool exposed (1 credit per use). It automatically registers with the buyer via the `--buyer-url` flag.

In **Terminal 1** you should see a registration log:

```
HH:MM:SS | REGISTRY    | REGISTERED  | name=Data Selling Agent skills=['Web Search'] url=http://localhost:9001
```

---

### Step 4 — Ask: "What sellers are available?"

**Terminal 1 (Buyer):**

```
What sellers are available?
```

**Expected output:**

```
Registered sellers (1):

  Data Selling Agent (http://localhost:9001)
    Skills: Web Search
    Min credits: 1
    Pricing: Credits vary by tool: search_data=1
```

**What's happening:** The agent calls `list_sellers` again. Now it finds the seller that just registered, showing its name, URL, available skills, and pricing.

---

### Step 5 — Ask: "Tell me more about the Data Selling Agent"

**Terminal 1 (Buyer):**

```
Tell me more about the Data Selling Agent
```

**Expected output (key phrases):**

```
Name: Data Selling Agent
Skills: Web Search
Payment: planId=..., agentId=..., credits=1
```

**What's happening:** The agent calls `discover_agent` to fetch the full agent card from `http://localhost:9001/.well-known/agent.json`, displaying skills, description, and payment extension details.

---

### Step 6 — Ask: "Search for what is bitcoin"

**Terminal 1 (Buyer):**

```
Search for what is bitcoin
```

**Expected output (key phrases):**

```
# The agent may first discover the seller and check balance
# Then it calls purchase_a2a with the query
# You should see search results about Bitcoin
# And a note like: "1 credit" or "balance is now 53 credits"
```

In **Terminal 2 (Seller A)** you'll see:

```
15:07:12 | PAYMENT     | VERIFY      | method=message/stream token=eyJ4NDAy...
15:07:12 | PAYMENT     | VERIFIED    | method=message/stream status=ok
15:07:12 | EXECUTOR    | RECEIVED    | query="what is bitcoin" task=31cd2194
15:07:18 | EXECUTOR    | COMPLETED   | credits_used=1 response=467 chars
```

**What's happening:** The buyer generates an x402 payment token, sends an A2A message to Seller A, the seller validates payment, runs the `search_data` tool, returns results, and settles 1 credit on-chain.

---

### Step 7 — Ask: "Check my balance"

**Terminal 1 (Buyer):**

```
Check my balance
```

**Expected output:**

```
Plan ID: <your-plan-id>
Balance: 53 credits
Subscriber: Yes

Local budget:
  Daily limit: 100
  Daily spent: 1
  Daily remaining: 99
  Total spent (session): 1
```

**What's happening:** The agent calls `check_balance` which queries the Nevermined API for the on-chain credit balance (ERC-1155 on Base Sepolia in sandbox mode) and also reports local budget tracking.

---

### Step 8 — Start Seller B (summarize tool, port 9002)

**Terminal 3 (Seller B)**

```bash
cd agents/seller-simple-agent
poetry run python -m src.agent_a2a --tools summarize --port 9002 --buyer-url http://localhost:8000
```

**Expected output:**

```
15:12:37 | SERVER      | STARTUP     | Data Selling Agent — A2A Mode on port 9002
15:12:37 | SERVER      | STARTUP     | tools=[summarize] pricing=Credits vary by tool: summarize_data=5
15:12:37 | SERVER      | STARTUP     | will register with buyer at http://localhost:8000
...
15:12:39 | REGISTER    | SUCCESS     | registered with http://localhost:8000
```

In **Terminal 1** you should see:

```
HH:MM:SS | REGISTRY    | REGISTERED  | name=Data Selling Agent skills=['Content Summarization'] url=http://localhost:9002
```

**What's happening:** A second seller starts with only the `summarize` tool (5 credits per use, higher because it processes more data). It also auto-registers with the buyer.

---

### Step 9 — Ask: "What sellers are available now?"

**Terminal 1 (Buyer):**

```
What sellers are available now?
```

**Expected output:**

```
Registered sellers (2):

  Data Selling Agent (http://localhost:9001)
    Skills: Web Search
    Min credits: 1
    Pricing: Credits vary by tool: search_data=1

  Data Selling Agent (http://localhost:9002)
    Skills: Content Summarization
    Min credits: 5
    Pricing: Credits vary by tool: summarize_data=5
```

**What's happening:** Both sellers now appear in the registry. The agent can distinguish them by URL and skill set.

---

### Step 10 — Ask: "Use the seller on port 9002 to summarize the latest AI trends"

**Terminal 1 (Buyer):**

```
Use the seller on port 9002 to summarize the latest AI trends
```

**Expected output (key phrases):**

```
# Agent calls purchase_a2a with agent_url=http://localhost:9002
# Returns a summary of AI trends
# 5 credits spent
```

**What's happening:** The buyer specifically targets Seller B (port 9002) for a summarization task. The payment flow is the same as Step 6 but with a different seller and higher credit cost.

---

## For LLMs: Automated Testing

The buyer CLI uses an interactive REPL (`You:` prompt). Below are the exact commands and expected patterns for automated verification.

### Setup Commands

```bash
# Start buyer web server (easier to test via HTTP than REPL)
cd agents/buyer-simple-agent
poetry run python -m src.web &
BUYER_PID=$!
sleep 5

# Start Seller A (background)
cd agents/seller-simple-agent
poetry run python -m src.agent_a2a --tools search --port 9001 --buyer-url http://localhost:8000 &
SELLER_A_PID=$!
sleep 5

# Start Seller B (background)
poetry run python -m src.agent_a2a --tools summarize --port 9002 --buyer-url http://localhost:8000 &
SELLER_B_PID=$!
sleep 5
```

### Verification via HTTP API

The web server (`poetry run python -m src.web`) exposes the same agent with JSON APIs:

**List sellers:**

```bash
curl -s http://localhost:8000/api/sellers | python3 -m json.tool
```

Expected: JSON array with 2 entries, each containing `url`, `name`, `description`, `skills`, `credits`, `cost_description`.

```json
[
  {
    "url": "http://localhost:9001",
    "name": "Data Selling Agent",
    "description": "AI-powered data agent that provides web search, content summarization, and market research services with tiered pricing.",
    "skills": ["Web Search"],
    "credits": 1,
    "cost_description": "Credits vary by tool: search_data=1"
  },
  {
    "url": "http://localhost:9002",
    "name": "Data Selling Agent",
    "description": "AI-powered data agent that provides web search, content summarization, and market research services with tiered pricing.",
    "skills": ["Content Summarization"],
    "credits": 5,
    "cost_description": "Credits vary by tool: summarize_data=5"
  }
]
```

**Check balance:**

```bash
curl -s http://localhost:8000/api/balance | python3 -m json.tool
```

Expected: JSON with nested `balance` and `budget` objects.

```json
{
  "balance": {
    "status": "success",
    "content": [{"text": "Plan ID: ...\nBalance: 54 credits\nSubscriber: Yes"}],
    "balance": 54,
    "isSubscriber": true
  },
  "budget": {
    "daily_limit": 100,
    "daily_spent": 0,
    "daily_remaining": 100,
    "per_request_limit": 10,
    "total_spent": 0,
    "total_purchases": 0,
    "recent_purchases": []
  }
}
```

**Send a chat message (SSE):**

```bash
curl -s -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What sellers are available?"}' \
  --max-time 60
```

Response format is SSE (`text/event-stream`):

```
event: tool_use
data: {"name": "list_sellers"}

event: token
data: {"text": "There "}

event: token
data: {"text": "are "}

...

event: done
data: {"text": "There are 2 registered sellers..."}
```

Parse `event: done` to get the complete response text.

### Cleanup

```bash
kill $BUYER_PID $SELLER_A_PID $SELLER_B_PID 2>/dev/null
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `NVM_API_KEY is required` | Create `.env` with your Nevermined API key |
| `NVM_AGENT_ID is required` | Seller needs `NVM_AGENT_ID` in `.env` (find in Nevermined App agent settings) |
| `OPENAI_API_KEY is required` | Add your OpenAI key to `.env` |
| Seller registration fails | Ensure buyer is running on port 8000 before starting sellers |
| `poetry run agent` or `poetry run agent-a2a` fails | Use `poetry run python -m src.agent` or `poetry run python -m src.agent_a2a` instead (`package-mode = false`) |
| CLI doesn't show A2A tools | A2A mode is the default; use `--mode http` only if you want direct x402 |
| Credits not decreasing | Check `NVM_ENVIRONMENT=sandbox` and that plan has credits |
| `No file/folder found for package` | Run `poetry install` in the agent directory |
