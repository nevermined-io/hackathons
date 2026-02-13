"""
A2A registration server for the buyer agent.

Listens for seller registration messages via A2A JSON-RPC. When a seller
sends a message containing its agent URL, the server fetches the agent card
and stores it in the shared SellerRegistry.

Also exposes a GET /sellers debug endpoint for inspecting the registry.

Usage:
    from .registration_server import start_registration_server
    start_registration_server(registry, port=8000)
"""

import asyncio
import datetime
import threading
from uuid import uuid4

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from a2a.server.agent_execution import AgentExecutor
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCard,
    AgentCapabilities,
    Message,
    Role,
    Task,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

from .registry import SellerRegistry


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class RegistrationExecutor(AgentExecutor):
    """Handles seller registration via A2A messages.

    Expects the message text to be a seller agent URL. Fetches the agent card,
    registers the seller, and responds with a confirmation.
    """

    def __init__(self, registry: SellerRegistry):
        self._registry = registry

    async def execute(self, context, event_queue: EventQueue) -> None:
        task_id = context.task_id or str(uuid4())
        context_id = context.context_id or str(uuid4())

        # Publish initial Task
        if not getattr(context, "current_task", None):
            await event_queue.enqueue_event(
                Task(
                    id=task_id,
                    context_id=context_id,
                    status=TaskStatus(
                        state=TaskState.submitted, timestamp=_now_iso()
                    ),
                    history=[],
                )
            )

        # Extract agent URL from the message text
        agent_url = self._extract_text(context).strip()
        if not agent_url:
            await self._respond(
                event_queue, task_id, context_id,
                TaskState.failed, "No agent URL provided.",
            )
            return

        # Fetch the seller's agent card
        card_url = f"{agent_url.rstrip('/')}/.well-known/agent.json"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(card_url)
            if resp.status_code != 200:
                await self._respond(
                    event_queue, task_id, context_id,
                    TaskState.failed,
                    f"Failed to fetch agent card: HTTP {resp.status_code}",
                )
                return
            agent_card = resp.json()
        except Exception as exc:
            await self._respond(
                event_queue, task_id, context_id,
                TaskState.failed, f"Error fetching agent card: {exc}",
            )
            return

        # Register the seller
        info = self._registry.register(agent_url, agent_card)
        skill_names = [s.get("name", s.get("id", "?")) for s in info.skills]
        text = (
            f"Registered seller '{info.name}' at {info.url} "
            f"with skills: {', '.join(skill_names)}"
        )

        await self._respond(
            event_queue, task_id, context_id, TaskState.completed, text,
        )

    async def cancel(self, context, event_queue: EventQueue) -> None:
        task_id = getattr(context, "task_id", None) or str(uuid4())
        context_id = getattr(context, "context_id", None) or str(uuid4())
        await self._respond(
            event_queue, task_id, context_id,
            TaskState.canceled, "Cancelled.",
        )

    @staticmethod
    def _extract_text(context) -> str:
        message = getattr(context, "message", None)
        if not message:
            return ""
        parts = getattr(message, "parts", [])
        fragments = []
        for part in parts:
            if hasattr(part, "root"):
                part = part.root
            if hasattr(part, "text"):
                fragments.append(part.text)
            elif isinstance(part, dict) and part.get("kind") == "text":
                fragments.append(part.get("text", ""))
        return "".join(fragments)

    @staticmethod
    async def _respond(
        event_queue: EventQueue,
        task_id: str,
        context_id: str,
        state: TaskState,
        text: str,
    ) -> None:
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                status=TaskStatus(
                    state=state,
                    message=Message(
                        message_id=str(uuid4()),
                        role=Role.agent,
                        parts=[{"kind": "text", "text": text}],
                        task_id=task_id,
                        context_id=context_id,
                    ),
                    timestamp=_now_iso(),
                ),
                final=True,
            )
        )


def _build_buyer_agent_card(port: int) -> AgentCard:
    """Build the buyer's agent card (no skills, no payment)."""
    return AgentCard(
        name="Data Buying Agent",
        description="Buyer agent registration server. Sellers can register here.",
        url=f"http://localhost:{port}",
        version="0.1.0",
        skills=[],
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=True, pushNotifications=False),
    )


def start_registration_server(registry: SellerRegistry, port: int = 8000) -> None:
    """Start the A2A registration server in a daemon thread.

    Args:
        registry: Shared SellerRegistry instance.
        port: Port for the registration server.
    """
    def _run():
        app = FastAPI()

        # Debug endpoint to inspect the registry
        @app.get("/sellers")
        async def list_sellers():
            return JSONResponse(content=registry.list_all())

        # A2A JSON-RPC routes
        executor = RegistrationExecutor(registry)
        agent_card = _build_buyer_agent_card(port)
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

        uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
