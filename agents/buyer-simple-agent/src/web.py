"""
Web server for the buyer agent with chat UI support.

Provides a FastAPI server with:
- POST /api/chat — SSE streaming chat with the Strands agent
- GET /api/sellers — List registered sellers
- GET /api/balance — Check credit balance and budget
- GET /api/logs/stream — SSE log stream
- A2A registration routes (same as registration_server.py)
- Static file serving for the React frontend

Usage:
    poetry run web
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from starlette.responses import FileResponse

from strands.models.openai import OpenAIModel

from .log import enable_web_logging, get_logger, log
from .registration_server import RegistrationExecutor, _build_buyer_agent_card
from .strands_agent import (
    NVM_PLAN_ID,
    budget,
    create_agent,
    payments,
    seller_registry,
)
from .tools.balance import check_balance_impl

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
BUYER_PORT = int(os.getenv("BUYER_PORT", "8000"))

if not OPENAI_API_KEY:
    print("OPENAI_API_KEY is required. Set it in .env file.")
    sys.exit(1)

# Create agent with no console callback handler for web mode
model = OpenAIModel(
    client_args={"api_key": OPENAI_API_KEY},
    model_id=os.getenv("MODEL_ID", "gpt-4o-mini"),
)
agent = create_agent(model, mode="a2a")

# Serialize concurrent chat requests (Strands Agent is not thread-safe)
agent_lock = asyncio.Lock()

# Log broadcast: each SSE subscriber gets its own queue
log_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
_log_subscribers: set[asyncio.Queue] = set()
_log_history: list[dict] = []  # recent logs for new subscribers
_LOG_HISTORY_MAX = 200


async def _log_dispatcher():
    """Read from the single log_queue and fan out to all subscribers."""
    while True:
        entry = await log_queue.get()
        _log_history.append(entry)
        if len(_log_history) > _LOG_HISTORY_MAX:
            _log_history.pop(0)
        dead = []
        for q in _log_subscribers:
            try:
                q.put_nowait(entry)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            _log_subscribers.discard(q)


_logger = get_logger("buyer.web")

app = FastAPI(title="Buyer Agent Web")


@app.on_event("startup")
async def _start_log_dispatcher():
    asyncio.create_task(_log_dispatcher())


# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enable web log streaming
enable_web_logging(log_queue)


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


@app.post("/api/chat")
async def chat(request: Request):
    """Stream a chat response from the agent via SSE."""
    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    log(_logger, "WEB", "RECEIVED", f'chat message: "{message[:80]}"')

    async def event_generator():
        full_response = ""
        try:
            async with agent_lock:
                async for event in agent.stream_async(message):
                    if "data" in event:
                        chunk = event["data"]
                        full_response += chunk
                        yield {
                            "event": "token",
                            "data": json.dumps({"text": chunk}),
                        }
                    elif "current_tool_use" in event:
                        tool_info = event["current_tool_use"]
                        tool_name = tool_info.get("name", "unknown")
                        yield {
                            "event": "tool_use",
                            "data": json.dumps({"name": tool_name}),
                        }
            yield {
                "event": "done",
                "data": json.dumps({"text": full_response}),
            }
        except Exception as exc:
            log(_logger, "WEB", "ERROR", f"chat stream error: {exc}")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(exc)}),
            }

    return EventSourceResponse(event_generator())


@app.get("/api/sellers")
async def get_sellers():
    """Return all registered sellers."""
    return JSONResponse(content=seller_registry.list_all())


@app.get("/api/balance")
async def get_balance():
    """Check credit balance and budget status."""
    balance_result = check_balance_impl(payments, NVM_PLAN_ID)
    budget_status = budget.get_status()
    return JSONResponse(content={
        "balance": balance_result,
        "budget": budget_status,
    })


@app.get("/api/logs/stream")
async def log_stream(request: Request):
    """Stream log entries via SSE (broadcast to each subscriber)."""
    sub_queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    _log_subscribers.add(sub_queue)

    async def event_generator():
        try:
            # Replay history so new connections see past events
            for entry in _log_history:
                yield {"event": "log", "data": json.dumps(entry)}
            # Stream live events
            while True:
                if await request.is_disconnected():
                    break
                try:
                    entry = await asyncio.wait_for(sub_queue.get(), timeout=15.0)
                    yield {"event": "log", "data": json.dumps(entry)}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
        finally:
            _log_subscribers.discard(sub_queue)

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# A2A registration routes
# ---------------------------------------------------------------------------

# A2A registration routes (always mounted so sellers can register)
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

executor = RegistrationExecutor(seller_registry)
agent_card = _build_buyer_agent_card(BUYER_PORT)
task_store = InMemoryTaskStore()
handler = DefaultRequestHandler(
    agent_executor=executor,
    task_store=task_store,
)
a2a_app = A2AFastAPIApplication(
    agent_card=agent_card,
    http_handler=handler,
)
a2a_app.add_routes_to_app(app)

# ---------------------------------------------------------------------------
# Static file serving (production frontend)
# ---------------------------------------------------------------------------

FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"


if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        """Serve the SPA index.html for all non-API routes."""
        file_path = (FRONTEND_DIR / path).resolve()
        if file_path.is_relative_to(FRONTEND_DIR.resolve()) and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")


def main():
    """Run the buyer agent web server."""
    import uvicorn

    log(_logger, "WEB", "STARTUP", f"port={BUYER_PORT} mode=a2a")
    print(f"Buyer Agent Web Server running on http://localhost:{BUYER_PORT}")
    print(f"A2A registration endpoint active")
    if FRONTEND_DIR.exists():
        print(f"Serving frontend from {FRONTEND_DIR}")
    else:
        print(f"Frontend not built — use http://localhost:5173 for dev")

    uvicorn.run(app, host="0.0.0.0", port=BUYER_PORT, log_level="warning")


if __name__ == "__main__":
    main()
