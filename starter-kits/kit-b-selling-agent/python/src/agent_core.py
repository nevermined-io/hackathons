"""
Strands agent definition with Nevermined x402 payment-protected tools.

This is the heart of the kit. Both agent.py (FastAPI) and agent_agentcore.py
(AWS) import from here. The tools use plain functions from tools/ modules,
wrapped with @tool + @requires_payment decorators.

Usage:
    from src.agent_core import payments, create_agent, NVM_PLAN_ID
"""

import os

from dotenv import load_dotenv
from strands import Agent, tool

from payments_py import PaymentOptions, Payments
from payments_py.x402.strands import requires_payment

from .tools.web_search import search_web
from .tools.summarize import summarize_content_impl
from .tools.market_research import research_market_impl

load_dotenv()

# Nevermined configuration
NVM_API_KEY = os.environ["NVM_API_KEY"]
NVM_ENVIRONMENT = os.getenv("NVM_ENVIRONMENT", "sandbox")
NVM_PLAN_ID = os.environ["NVM_PLAN_ID"]
NVM_AGENT_ID = os.getenv("NVM_AGENT_ID")

# Initialize Nevermined Payments SDK
payments = Payments.get_instance(
    PaymentOptions(nvm_api_key=NVM_API_KEY, environment=NVM_ENVIRONMENT)
)


# ---------------------------------------------------------------------------
# Payment-protected Strands tools
# ---------------------------------------------------------------------------

@tool(context=True)
@requires_payment(
    payments=payments,
    plan_id=NVM_PLAN_ID,
    credits=1,
    agent_id=NVM_AGENT_ID,
)
def search_data(query: str, max_results: int = 5, tool_context=None) -> dict:
    """Search the web for data. Costs 1 credit per request.

    Args:
        query: The search query to run.
        max_results: Maximum number of results to return.
    """
    return search_web(query, max_results)


@tool(context=True)
@requires_payment(
    payments=payments,
    plan_id=NVM_PLAN_ID,
    credits=5,
    agent_id=NVM_AGENT_ID,
)
def summarize_data(content: str, focus: str = "key_findings", tool_context=None) -> dict:
    """Summarize content with LLM-powered analysis. Costs 5 credits per request.

    Args:
        content: The text content to summarize.
        focus: Focus area - 'key_findings', 'action_items', 'trends', or 'risks'.
    """
    return summarize_content_impl(content, focus)


@tool(context=True)
@requires_payment(
    payments=payments,
    plan_id=NVM_PLAN_ID,
    credits=10,
    agent_id=NVM_AGENT_ID,
)
def research_data(query: str, depth: str = "standard", tool_context=None) -> dict:
    """Conduct full market research with a multi-source report. Costs 10 credits per request.

    Args:
        query: The research topic or question.
        depth: Research depth - 'standard' or 'deep'.
    """
    return research_market_impl(query, depth)


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a data selling agent. You provide data services at three pricing tiers:

1. **search_data** (1 credit) - Basic web search. Use this for quick lookups.
2. **summarize_data** (5 credits) - LLM-powered content summarization. Use this \
when the user wants analysis of specific content.
3. **research_data** (10 credits) - Full market research report. Use this for \
comprehensive research questions.

Choose the appropriate tool based on the user's request complexity. If the user \
asks for a simple search, use search_data. If they want analysis or summary, use \
summarize_data. For in-depth research, use research_data.

Always be helpful and explain what data you found."""

TOOLS = [search_data, summarize_data, research_data]


def create_agent(model) -> Agent:
    """Create a Strands agent with the given model.

    Args:
        model: A Strands-compatible model (OpenAIModel, BedrockModel, etc.)

    Returns:
        Configured Strands Agent with payment-protected tools.
    """
    return Agent(
        model=model,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )
