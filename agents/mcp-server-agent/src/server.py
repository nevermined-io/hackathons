"""MCP server with Nevermined payment-protected tools.

Exposes three data tools with tiered credit pricing via the MCP protocol.
OAuth 2.1 and credit redemption are handled automatically by PaymentsMCP.

Credit pricing:
  - search_data:    1 credit (fixed, simple web lookup)
  - summarize_data: 2-10 credits (dynamic, based on output length)
  - research_data:  5-20 credits (dynamic, based on depth + output length)
"""

import asyncio
import os
import signal
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from openai import OpenAI
from payments_py import Payments, PaymentOptions
from payments_py.common.types import StartAgentRequest
from payments_py.mcp import PaymentsMCP

from .tools.market_research import research_market_impl
from .tools.summarize import summarize_content_impl
from .tools.web_search import search_web

load_dotenv()

NVM_API_KEY = os.environ.get("NVM_API_KEY", "")
NVM_ENVIRONMENT = os.environ.get("NVM_ENVIRONMENT", "staging")
NVM_AGENT_ID = os.environ.get("NVM_AGENT_ID", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
PORT = int(os.environ.get("PORT", "3000"))

payments = Payments.get_instance(
    PaymentOptions(nvm_api_key=NVM_API_KEY, environment=NVM_ENVIRONMENT)
)

mcp = PaymentsMCP(
    payments,
    name="data-mcp-server",
    agent_id=NVM_AGENT_ID,
    version="1.0.0",
    description="Data tools MCP server with Nevermined payments",
)


# --- Observability ---
#
# Build a per-request OpenAI client that routes LLM calls through Nevermined's
# observability proxy (Helicone). Uses the real agent_request from the paywall
# context so every inference is tagged with the actual subscriber, plan, and
# request metadata.


def _get_openai_client(paywall_context: Optional[Dict[str, Any]] = None) -> OpenAI:
    """Return an OpenAI client, with Helicone observability if agent_request is available."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")

    agent_req_data = (paywall_context or {}).get("agent_request")
    if agent_req_data is not None:
        try:
            start_req = StartAgentRequest(**agent_req_data)
            oai_config = payments.observability.with_openai(
                api_key=OPENAI_API_KEY,
                start_agent_request=start_req,
                custom_properties={"server": "mcp-server-agent", "environment": NVM_ENVIRONMENT},
            )
            print(f"[Observability] Proxying through {oai_config.base_url} "
                  f"(subscriber={start_req.balance.holder_address[:10]}..., "
                  f"request={start_req.agent_request_id})")
            return OpenAI(
                api_key=oai_config.api_key,
                base_url=oai_config.base_url,
                default_headers=oai_config.default_headers,
            )
        except Exception as e:
            print(f"[Observability] Setup failed ({e}), using direct OpenAI")

    print("[Observability] No agent_request in context, using direct OpenAI")
    return OpenAI(api_key=OPENAI_API_KEY)


# --- Dynamic credit functions ---
#
# The PaymentsMCP paywall calls these AFTER the tool executes, passing a context
# dict with {"args": {...}, "result": {...}, "request": {...}}.
# The result is already in MCP format: {"content": [{"type": "text", "text": "..."}]}


def _summarize_credits(ctx: Dict[str, Any]) -> int:
    """2-10 credits based on output length.

    Short summaries (< 500 chars) cost 2 credits.
    Each additional 500 chars adds 1 credit, up to 10.
    """
    result = ctx.get("result") or {}
    content = result.get("content", [])
    text = content[0].get("text", "") if content else ""
    return min(10, max(2, 2 + len(text) // 500))


def _research_credits(ctx: Dict[str, Any]) -> int:
    """5-20 credits based on depth arg + output length.

    Base: 5 credits (standard) or 10 credits (deep).
    Each 500 chars of output adds 1 credit, up to +10.
    """
    args = ctx.get("args") or {}
    depth = args.get("depth", "standard")
    base = 10 if depth == "deep" else 5

    result = ctx.get("result") or {}
    content = result.get("content", [])
    text = content[0].get("text", "") if content else ""
    length_credits = len(text) // 500

    return min(20, base + length_credits)


# --- Tools ---


@mcp.tool(credits=1)
def search_data(query: str) -> str:
    """Search the web for data using DuckDuckGo.

    :param query: Search query string
    """
    result = search_web(query)
    return result["content"][0]["text"]


@mcp.tool(credits=_summarize_credits)
def summarize_data(content: str, focus: str = "key_findings", paywall_context=None) -> str:
    """Summarize content using AI (2-10 credits based on output length).

    :param content: The text content to summarize
    :param focus: Focus area - key_findings, action_items, trends, or risks
    """
    client = _get_openai_client(paywall_context)
    result = summarize_content_impl(content, focus, openai_client=client)
    return result["content"][0]["text"]


@mcp.tool(credits=_research_credits)
def research_data(query: str, depth: str = "standard", paywall_context=None) -> str:
    """Conduct market research combining search, analysis, and AI synthesis (5-20 credits based on depth and output).

    :param query: The research topic or question
    :param depth: Research depth - standard (5+ credits) or deep (10+ credits)
    """
    client = _get_openai_client(paywall_context)
    result = research_market_impl(query, depth, openai_client=client)
    return result["content"][0]["text"]


# --- Entry point ---


async def _run():
    result = await mcp.start(port=PORT)
    info = result["info"]
    stop = result["stop"]

    print(f"\nMCP Server running at: {info['baseUrl']}")
    print(f"  MCP endpoint:  {info['baseUrl']}/mcp")
    print(f"  Health check:  {info['baseUrl']}/health")
    print(f"  Tools: {', '.join(info.get('tools', []))}")
    print()

    loop = asyncio.get_running_loop()
    shutdown = loop.create_future()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: shutdown.set_result(True))

    await shutdown
    await stop()
    print("Server stopped.")


def main():
    asyncio.run(_run())


if __name__ == "__main__":
    main()
