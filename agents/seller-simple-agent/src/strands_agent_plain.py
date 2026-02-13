"""
Plain Strands tools WITHOUT @requires_payment — for A2A mode.

In A2A mode, payment validation and credit settlement happen at the A2A
message level via PaymentsRequestHandler. Individual tools don't need
the @requires_payment decorator.

The tool functions delegate to the same implementations in tools/.

Usage:
    from src.strands_agent_plain import create_plain_agent, CREDIT_MAP, resolve_tools
"""

from a2a.types import AgentSkill
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


# ---------------------------------------------------------------------------
# ALL_TOOLS registry — maps short names to (tool_fn, credits, AgentSkill)
# ---------------------------------------------------------------------------

ALL_TOOLS = {
    "search": {
        "tool": search_data,
        "credits": 1,
        "skill": AgentSkill(
            id="search_data",
            name="Web Search",
            description="Search the web for data. Costs 1 credit per request.",
            tags=["search", "data", "web"],
        ),
    },
    "summarize": {
        "tool": summarize_data,
        "credits": 5,
        "skill": AgentSkill(
            id="summarize_data",
            name="Content Summarization",
            description="Summarize content with LLM-powered analysis. Costs 5 credits.",
            tags=["summarize", "analysis", "llm"],
        ),
    },
    "research": {
        "tool": research_data,
        "credits": 10,
        "skill": AgentSkill(
            id="research_data",
            name="Market Research",
            description="Full market research with multi-source report. Costs 10 credits.",
            tags=["research", "market", "report"],
        ),
    },
}


def resolve_tools(tool_names: list[str] | None = None):
    """Resolve tool short names to (tools, credit_map, skills).

    Args:
        tool_names: List of short names (e.g. ["search", "summarize"]).
                    None or empty means all tools.

    Returns:
        Tuple of (tools_list, credit_map_dict, skills_list).
    """
    names = tool_names if tool_names else list(ALL_TOOLS.keys())
    tools = []
    credit_map = {}
    skills = []
    for name in names:
        entry = ALL_TOOLS[name]
        fn = entry["tool"]
        tools.append(fn)
        credit_map[fn.__name__] = entry["credits"]
        skills.append(entry["skill"])
    return tools, credit_map, skills


# Module-level defaults (backward compatibility)
CREDIT_MAP = {fn.__name__: e["credits"] for fn, e in
               ((ALL_TOOLS[n]["tool"], ALL_TOOLS[n]) for n in ALL_TOOLS)}
TOOLS = [ALL_TOOLS[n]["tool"] for n in ALL_TOOLS]

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


def _build_system_prompt(tools_list):
    """Build a system prompt that only mentions the available tools."""
    tool_names = {t.__name__ for t in tools_list}
    lines = ["You are a data selling agent. You provide data services:\n"]
    if "search_data" in tool_names:
        lines.append("- **search_data** (1 credit) - Basic web search for quick lookups.")
    if "summarize_data" in tool_names:
        lines.append("- **summarize_data** (5 credits) - LLM-powered content summarization.")
    if "research_data" in tool_names:
        lines.append("- **research_data** (10 credits) - Full market research report.")
    lines.append(
        "\nChoose the appropriate tool based on the user's request complexity. "
        "Always be helpful and explain what data you found."
    )
    return "\n".join(lines)


def create_plain_agent(model, tool_names: list[str] | None = None) -> Agent:
    """Create a Strands agent with plain (non-payment) tools.

    Args:
        model: A Strands-compatible model (OpenAIModel, BedrockModel, etc.)
        tool_names: Optional list of tool short names to include.
                    None means all tools.

    Returns:
        Configured Strands Agent with plain tools for A2A mode.
    """
    if tool_names:
        tools, _, _ = resolve_tools(tool_names)
        prompt = _build_system_prompt(tools)
    else:
        tools = TOOLS
        prompt = SYSTEM_PROMPT
    return Agent(
        model=model,
        tools=tools,
        system_prompt=prompt,
    )
