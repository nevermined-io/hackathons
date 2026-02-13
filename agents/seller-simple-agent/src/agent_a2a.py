"""
A2A server entry point for the data selling agent.

Runs the seller as an A2A-compliant agent with:
- Standard agent card at /.well-known/agent.json (with payment extension)
- JSON-RPC message endpoint with payment validation middleware
- Automatic credit settlement via PaymentsRequestHandler

Payment flow:
1. Client fetches /.well-known/agent.json -> discovers payment requirements
2. Client sends A2A message with payment-signature header
3. PaymentsRequestHandler validates the token
4. StrandsA2AExecutor runs the Strands agent (plain tools)
5. On completion, handler settles credits based on creditsUsed metadata

Usage:
    poetry run agent-a2a
    poetry run agent-a2a --tools search --port 9001
    poetry run agent-a2a --tools summarize --port 9002 --buyer-url http://localhost:8000
"""

import argparse
import asyncio
import datetime
import os
import sys
import threading
import time
from uuid import uuid4

import httpx
from dotenv import load_dotenv
from strands import Agent
from strands.models.openai import OpenAIModel

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.events.event_queue import EventQueue
from a2a.types import (
    AgentSkill,
    Message,
    Role,
    Task,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

from payments_py import Payments, PaymentOptions
from payments_py.a2a.agent_card import build_payment_agent_card
from payments_py.a2a.server import PaymentsA2AServer

from .strands_agent_plain import ALL_TOOLS, create_plain_agent, resolve_tools

load_dotenv()

NVM_API_KEY = os.environ["NVM_API_KEY"]
NVM_ENVIRONMENT = os.getenv("NVM_ENVIRONMENT", "sandbox")
NVM_PLAN_ID = os.environ["NVM_PLAN_ID"]
NVM_AGENT_ID = os.getenv("NVM_AGENT_ID", "")

if not NVM_AGENT_ID:
    print("ERROR: NVM_AGENT_ID is required for A2A mode.")
    print("Set it in your .env file. You can find it in the Nevermined App")
    print("under your agent's settings, or use the Plan ID as a fallback.")
    sys.exit(1)

payments = Payments.get_instance(
    PaymentOptions(nvm_api_key=NVM_API_KEY, environment=NVM_ENVIRONMENT)
)


# ---------------------------------------------------------------------------
# Custom executor that wraps the Strands agent for A2A
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return the current UTC timestamp in ISO format."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _make_status_event(
    task_id: str,
    context_id: str,
    state: TaskState,
    text: str,
    credits_used: int | None = None,
    final: bool = True,
) -> TaskStatusUpdateEvent:
    """Build a TaskStatusUpdateEvent with a text message."""
    metadata = {"creditsUsed": credits_used} if credits_used is not None else None
    return TaskStatusUpdateEvent(
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
        metadata=metadata,
        final=final,
    )


def _extract_text_from_parts(parts) -> str:
    """Extract text from a list of A2A message parts."""
    fragments = []
    for part in parts:
        if hasattr(part, "root"):
            part = part.root
        if hasattr(part, "text"):
            fragments.append(part.text)
        elif isinstance(part, dict) and part.get("kind") == "text":
            fragments.append(part.get("text", ""))
    return "".join(fragments)


class StrandsA2AExecutor(AgentExecutor):
    """Execute A2A requests by delegating to a Strands agent.

    Extracts the user's text from the A2A message, runs the Strands agent,
    and emits a final TaskStatusUpdateEvent with creditsUsed metadata
    (which triggers PaymentsRequestHandler to settle).
    """

    def __init__(self, agent: Agent, credit_map: dict[str, int] | None = None):
        self._agent = agent
        self._credit_map = credit_map or {}

    async def execute(self, context, event_queue: EventQueue) -> None:
        task_id = context.task_id or str(uuid4())
        context_id = context.context_id or str(uuid4())

        # Publish initial Task if this is a new request
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

        # Publish working status
        await event_queue.enqueue_event(
            _make_status_event(
                task_id, context_id, TaskState.working,
                "Processing request...", final=False,
            )
        )

        # Extract user text from A2A message
        user_text = self._extract_user_text(context) or "Hello"

        # Run the Strands agent
        # Snapshot message count so we only count credits from this request
        msg_offset = len(self._agent.messages)
        try:
            result = await asyncio.to_thread(self._agent, user_text)
            response_text = str(result)
        except Exception as exc:
            await event_queue.enqueue_event(
                _make_status_event(
                    task_id, context_id, TaskState.failed,
                    f"Error: {exc}", credits_used=0,
                )
            )
            return

        credits_used = self._calculate_credits(self._agent.messages[msg_offset:])

        await event_queue.enqueue_event(
            _make_status_event(
                task_id, context_id, TaskState.completed,
                response_text, credits_used=credits_used,
            )
        )

    async def cancel(self, context, event_queue: EventQueue) -> None:
        task_id = getattr(context, "task_id", None) or str(uuid4())
        context_id = getattr(context, "context_id", None) or str(uuid4())
        await event_queue.enqueue_event(
            _make_status_event(
                task_id, context_id, TaskState.canceled,
                "Task cancelled.", credits_used=0,
            )
        )

    @staticmethod
    def _extract_user_text(context) -> str:
        """Extract the user's text from an A2A message context."""
        message = getattr(context, "message", None)
        if not message:
            return ""
        parts = getattr(message, "parts", [])
        return _extract_text_from_parts(parts)

    def _calculate_credits(self, messages: list) -> int:
        """Scan agent messages for tool_use to determine total credits."""
        total = 0
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            for block in msg.get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    total += self._credit_map.get(block.get("name", ""), 1)
        return total or 1  # minimum 1 credit per request


# ---------------------------------------------------------------------------
# Self-registration with buyer
# ---------------------------------------------------------------------------

def _register_with_buyer(buyer_url: str, agent_url: str):
    """Send a registration A2A message to the buyer's registration server.

    Runs in a daemon thread with a short delay so uvicorn has time to start.
    Retries up to 3 times on connection errors.
    """
    time.sleep(2)  # wait for uvicorn to bind

    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "messageId": str(uuid4()),
                "role": "user",
                "parts": [{"kind": "text", "text": agent_url}],
            }
        },
    }

    for attempt in range(1, 4):
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(buyer_url, json=payload)
            if resp.status_code == 200:
                print(f"\nRegistered with buyer at {buyer_url}")
                return
            print(f"\nRegistration attempt {attempt}: HTTP {resp.status_code}")
        except Exception as exc:
            print(f"\nRegistration attempt {attempt} failed: {exc}")
        time.sleep(2)

    print("\nWARNING: Could not register with buyer after 3 attempts.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _parse_args():
    parser = argparse.ArgumentParser(description="Data Selling Agent — A2A Mode")
    parser.add_argument(
        "--tools",
        nargs="*",
        choices=list(ALL_TOOLS.keys()),
        default=None,
        help="Tools to expose (default: all). Options: search, summarize, research",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("A2A_PORT", "9000")),
        help="Port to listen on (default: A2A_PORT env or 9000)",
    )
    parser.add_argument(
        "--buyer-url",
        default=os.getenv("BUYER_URL", ""),
        help="Buyer registration URL for auto-registration (default: BUYER_URL env)",
    )
    return parser.parse_args()


def main():
    """Start the A2A server."""
    args = _parse_args()
    port = args.port
    tool_names = args.tools
    buyer_url = args.buyer_url

    # Resolve tools, credit map, and skills
    tools_list, credit_map, skills = resolve_tools(tool_names)

    # Build cost description from credit map
    cost_parts = [f"{name}={cost}" for name, cost in credit_map.items()]
    cost_description = "Credits vary by tool: " + ", ".join(cost_parts)

    # Build dynamic agent card
    base_agent_card = {
        "name": "Data Selling Agent",
        "description": (
            "AI-powered data agent that provides web search, content summarization, "
            "and market research services with tiered pricing."
        ),
        "url": f"http://localhost:{port}",
        "version": "0.1.0",
        "skills": [s.model_dump() for s in skills],
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
        },
    }

    agent_card = build_payment_agent_card(
        base_agent_card,
        {
            "paymentType": "dynamic",
            "credits": min(credit_map.values()),
            "planId": NVM_PLAN_ID,
            "agentId": NVM_AGENT_ID,
            "costDescription": cost_description,
        },
    )

    # Create strands agent and executor
    model = OpenAIModel(
        client_args={"api_key": os.environ.get("OPENAI_API_KEY", "")},
        model_id=os.getenv("MODEL_ID", "gpt-4o-mini"),
    )

    agent = create_plain_agent(model, tool_names)
    executor = StrandsA2AExecutor(agent, credit_map)

    tool_label = ", ".join(tool_names) if tool_names else "all"
    print("=" * 60)
    print("Data Selling Agent — A2A Mode")
    print("=" * 60)
    print(f"\nAgent card:  http://localhost:{port}/.well-known/agent.json")
    print(f"JSON-RPC:    http://localhost:{port}/")
    print(f"Plan ID:     {NVM_PLAN_ID}")
    print(f"Agent ID:    {NVM_AGENT_ID}")
    print(f"Environment: {NVM_ENVIRONMENT}")
    print(f"Tools:       {tool_label}")
    print(f"Pricing:     {cost_description}")

    # Self-register with buyer if buyer URL provided
    if buyer_url:
        agent_url = f"http://localhost:{port}"
        print(f"Registering: {buyer_url}")
        thread = threading.Thread(
            target=_register_with_buyer,
            args=(buyer_url, agent_url),
            daemon=True,
        )
        thread.start()

    result = PaymentsA2AServer.start(
        agent_card=agent_card,
        executor=executor,
        payments_service=payments,
        port=port,
    )

    asyncio.run(result.server.serve())


if __name__ == "__main__":
    main()
