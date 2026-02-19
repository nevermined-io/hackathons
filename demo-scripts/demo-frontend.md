# Demo: A2A Buyer-Seller Marketplace (Frontend)

Web UI demo walking through the full A2A marketplace flow using the React frontend. Shows the sidebar seller panel, chat interface, and activity log updating in real time as sellers register and purchases are made.

## Prerequisites

### Buyer Setup (`agents/buyer-simple-agent/`)

Create `.env`:

```bash
NVM_API_KEY=nvm:your-api-key
NVM_ENVIRONMENT=sandbox
NVM_PLAN_ID=your-plan-id
OPENAI_API_KEY=sk-your-key
```

Install backend + frontend:

```bash
cd agents/buyer-simple-agent
poetry install

cd agents/buyer-simple-agent/frontend
npm install
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

> **Note:** Use `poetry run python -m src.<module>` to run entry points because both projects use `package-mode = false`.

---

## For Humans: Step-by-Step

Open **4 terminal windows**. The frontend runs as a separate dev server that proxies API calls to the buyer backend.

### Step 1 — Start the Buyer Web Server

**Terminal 1 (Buyer Backend)**

```bash
cd agents/buyer-simple-agent
poetry run python -m src.web
```

**Expected output:**

```
HH:MM:SS | WEB         | STARTUP     | port=8000 mode=a2a
Buyer Agent Web Server running on http://localhost:8000
A2A registration endpoint active
Frontend not built — use http://localhost:5173 for dev
```

**What's happening:** The FastAPI web server starts with:
- `POST /api/chat` — SSE streaming chat
- `GET /api/sellers` — List registered sellers
- `GET /api/balance` — Credit balance and budget
- `GET /api/logs/stream` — SSE activity log
- A2A registration routes (sellers register here via `--buyer-url`)

---

### Step 2 — Start the Frontend Dev Server

**Terminal 2 (Frontend)**

```bash
cd agents/buyer-simple-agent/frontend
npm run dev
```

**Expected output:**

```
  VITE v6.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
```

Open **http://localhost:5173** in your browser.

**Expected UI state:**

| Panel | Content |
|-------|---------|
| Sidebar (left) | "Marketplace Sellers" heading, "No sellers registered" message |
| Chat (center) | Empty chat area with input field at bottom |
| Activity Log (right) | `STARTUP` entry showing server started |

---

### Step 3 — Ask: "What sellers are available?"

Type in the chat input and press Enter:

```
What sellers are available?
```

**Expected UI state:**

| Panel | Content |
|-------|---------|
| Chat | Agent responds: "No sellers registered yet..." |
| Activity Log | `LIST_SELLERS` entry with `count=0` |
| Sidebar | Still empty — "No sellers registered" |

**What's happening:** The chat message is sent via `POST /api/chat` as SSE. The agent calls `list_sellers` and streams the response token by token.

---

### Step 4 — Start Seller A (search only, port 9001)

**Terminal 3 (Seller A)**

```bash
cd agents/seller-simple-agent
poetry run python -m src.agent_a2a --tools search --port 9001 --buyer-url http://localhost:8000
```

**Expected terminal output:**

```
15:06:26 | SERVER      | STARTUP     | Data Selling Agent — A2A Mode on port 9001
15:06:26 | SERVER      | STARTUP     | tools=[search] pricing=Credits vary by tool: search_data=1
15:06:26 | SERVER      | STARTUP     | will register with buyer at http://localhost:8000
...
15:06:28 | REGISTER    | SUCCESS     | registered with http://localhost:8000
```

**Expected UI state (updates automatically):**

| Panel | Content |
|-------|---------|
| Sidebar | Shows **1 seller**: "Data Selling Agent" with "Web Search" skill, 1 credit |
| Activity Log | New `REGISTERED` entry: "Data Selling Agent" at localhost:9001 |

> **Tip:** The sidebar polls `/api/sellers` periodically — the new seller should appear within a few seconds.

---

### Step 5 — Ask: "What sellers are available?"

Type in the chat input:

```
What sellers are available?
```

**Expected UI state:**

| Panel | Content |
|-------|---------|
| Chat | Agent lists 1 seller with skills and pricing |
| Sidebar | "Data Selling Agent" — Web Search, 1 credit |
| Activity Log | `LIST_SELLERS` with `count=1` |

---

### Step 6 — Ask: "Tell me more about the Data Selling Agent"

Type in the chat input:

```
Tell me more about the Data Selling Agent
```

**Expected UI state:**

| Panel | Content |
|-------|---------|
| Chat | Detailed agent info: name, description, skills, payment details |
| Activity Log | `DISCOVER` entries showing agent card fetch |

**What's happening:** The agent calls `discover_agent` to fetch the full agent card from the seller's `/.well-known/agent.json` endpoint.

---

### Step 7 — Ask: "Search for what is bitcoin"

Type in the chat input:

```
Search for what is bitcoin
```

**Expected UI state:**

| Panel | Content |
|-------|---------|
| Chat | Shows a "tool_use" indicator while processing, then search results about Bitcoin with a note about credits spent |
| Activity Log | `PURCHASE` entry, then `COMPLETED` with credits_used=1 |
| Sidebar | Credit count may update on next balance check |

In **Terminal 3 (Seller A):**

```
15:07:12 | PAYMENT     | VERIFY      | method=message/stream token=eyJ4NDAy...
15:07:12 | PAYMENT     | VERIFIED    | method=message/stream status=ok
15:07:12 | EXECUTOR    | RECEIVED    | query="what is bitcoin" task=31cd2194
15:07:18 | EXECUTOR    | COMPLETED   | credits_used=1 response=467 chars
```

---

### Step 8 — Ask: "Check my balance"

Type in the chat input:

```
Check my balance
```

**Expected UI state:**

| Panel | Content |
|-------|---------|
| Chat | Shows balance (e.g., "53 credits"), plan ID, subscriber status, and daily budget stats |
| Activity Log | `BALANCE` entry |

**What's happening:** Balance is queried from the Nevermined API (ERC-1155 on Base Sepolia for sandbox). The credit decrease reflects the purchase in Step 7.

---

### Step 9 — Start Seller B (summarize tool, port 9002)

**Terminal 4 (Seller B)**

```bash
cd agents/seller-simple-agent
poetry run python -m src.agent_a2a --tools summarize --port 9002 --buyer-url http://localhost:8000
```

**Expected terminal output:**

```
15:12:37 | SERVER      | STARTUP     | Data Selling Agent — A2A Mode on port 9002
15:12:37 | SERVER      | STARTUP     | tools=[summarize] pricing=Credits vary by tool: summarize_data=5
...
15:12:39 | REGISTER    | SUCCESS     | registered with http://localhost:8000
```

**Expected UI state (updates automatically):**

| Panel | Content |
|-------|---------|
| Sidebar | Now shows **2 sellers**: Web Search (port 9001, 1 credit) and Content Summarization (port 9002, 5 credits) |
| Activity Log | New `REGISTERED` entry for the second seller |

---

### Step 10 — Ask: "What sellers are available now?"

Type in the chat input:

```
What sellers are available now?
```

**Expected UI state:**

| Panel | Content |
|-------|---------|
| Chat | Lists both sellers with their respective skills and pricing |
| Sidebar | 2 sellers displayed |
| Activity Log | `LIST_SELLERS` with `count=2` |

---

### Step 11 — Ask: "Use the seller on port 9002 to summarize the latest AI trends"

Type in the chat input:

```
Use the seller on port 9002 to summarize the latest AI trends
```

**Expected UI state:**

| Panel | Content |
|-------|---------|
| Chat | Summary of AI trends, note about 5 credits spent |
| Activity Log | `PURCHASE` targeting port 9002, `COMPLETED` with credits_used=5 |

**What's happening:** The buyer targets Seller B specifically by URL. The `summarize_data` tool costs 5 credits (higher than search because it processes more data).

---

## For LLMs: API-Level Testing

The frontend requires a browser, but all functionality is accessible via the HTTP API. Use these endpoints for automated testing.

### Endpoints

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| `GET` | `/api/sellers` | List registered sellers | JSON array |
| `GET` | `/api/balance` | Credit balance and budget | JSON object |
| `POST` | `/api/chat` | Chat with the agent (SSE stream) | `text/event-stream` |
| `GET` | `/api/logs/stream` | Activity log stream (SSE) | `text/event-stream` |

### Setup

```bash
# Start buyer web server
cd agents/buyer-simple-agent
poetry run python -m src.web &
BUYER_PID=$!
sleep 5

# Start Seller A
cd agents/seller-simple-agent
poetry run python -m src.agent_a2a --tools search --port 9001 --buyer-url http://localhost:8000 &
SELLER_A_PID=$!
sleep 5

# Start Seller B
poetry run python -m src.agent_a2a --tools summarize --port 9002 --buyer-url http://localhost:8000 &
SELLER_B_PID=$!
sleep 5
```

### Verify Sellers Registered

```bash
curl -s http://localhost:8000/api/sellers | python3 -m json.tool
```

**Expected:** JSON array with 2 entries:

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

### Check Balance

```bash
curl -s http://localhost:8000/api/balance | python3 -m json.tool
```

**Expected:** JSON with nested `balance` and `budget` objects:

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

### Send Chat Message

```bash
curl -s -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What sellers are available?"}' \
  --max-time 60
```

**Response format (SSE):**

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

### Purchase via Chat

```bash
curl -s -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Search for what is bitcoin"}' \
  --max-time 90
```

**Expected SSE events:**

1. `event: tool_use` with `{"name": "purchase_a2a"}` (may also show `discover_agent`, `check_balance`)
2. Multiple `event: token` chunks with search results
3. `event: done` with complete response including credit usage

### Cleanup

```bash
kill $BUYER_PID $SELLER_A_PID $SELLER_B_PID 2>/dev/null
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Frontend shows blank page | Ensure `npm run dev` is running in `frontend/` dir |
| CORS errors in browser console | Ensure buyer backend is on port 8000 (CORS allows localhost:5173 and 127.0.0.1:5173) |
| Sidebar doesn't update | Refresh the page; check that seller registration logged `SUCCESS` |
| Chat returns error | Check Terminal 1 for Python errors; verify `OPENAI_API_KEY` is set |
| `poetry run web` fails | Use `poetry run python -m src.web` instead (`package-mode = false`) |
| `poetry run agent-a2a` fails | Use `poetry run python -m src.agent_a2a` instead (`package-mode = false`) |
| Activity log empty | Ensure you opened `http://localhost:5173` (not 8000) for dev mode |
| Credits not decreasing | Check `NVM_ENVIRONMENT=sandbox` and that your plan has credits |
| `No file/folder found for package` | Run `poetry install` in the agent directory |
