"""
Plain Strands tools WITHOUT @requires_payment — for A2A mode.

In A2A mode, payment validation and credit settlement happen at the A2A
message level via PaymentsRequestHandler. Individual tools don't need
the @requires_payment decorator.

The tool functions delegate to the same implementations in tools/.

Usage:
    from src.strands_agent_plain import create_plain_agent, CREDIT_MAP
"""

from strands import Agent, tool

from .tools.market_research import research_market_impl
from .tools.summarize import summarize_content_impl
from .tools.web_search import search_web


# ---------------------------------------------------------------------------
# Plain Strands tools (no payment decorator)
# ---------------------------------------------------------------------------

@tool
def search_data(query: str, max_results: int = 5) -> dict:
    """Search the web for data. Costs 1 credit per request.

    Args:
        query: The search query to run.
        max_results: Maximum number of results to return.
    """
    return search_web(query, max_results)


@tool
def summarize_data(content: str, focus: str = "key_findings") -> dict:
    """Summarize content with LLM-powered analysis. Costs 5 credits per request.

    Args:
        content: The text content to summarize.
        focus: Focus area - 'key_findings', 'action_items', 'trends', or 'risks'.
    """
    return summarize_content_impl(content, focus)


@tool
def research_data(query: str, depth: str = "standard") -> dict:
    """Conduct full market research with a multi-source report. Costs 10 credits per request.

    Args:
        query: The research topic or question.
        depth: Research depth - 'standard' or 'deep'.
    """
    return research_market_impl(query, depth)


# Credit cost per tool — used by the executor to report creditsUsed
CREDIT_MAP = {
    "search_data": 1,
    "summarize_data": 5,
    "research_data": 10,
}

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


def create_plain_agent(model) -> Agent:
    """Create a Strands agent with plain (non-payment) tools.

    Args:
        model: A Strands-compatible model (OpenAIModel, BedrockModel, etc.)

    Returns:
        Configured Strands Agent with plain tools for A2A mode.
    """
    return Agent(
        model=model,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )
