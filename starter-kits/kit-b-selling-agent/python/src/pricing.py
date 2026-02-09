"""Pricing tiers for the data selling agent."""

PRICING_TIERS = {
    "simple": {
        "credits": 1,
        "description": "Basic web search - returns raw search results",
        "tool": "search_data",
    },
    "medium": {
        "credits": 5,
        "description": "Content summarization - LLM-powered analysis",
        "tool": "summarize_data",
    },
    "complex": {
        "credits": 10,
        "description": "Full market research - multi-source report",
        "tool": "research_data",
    },
}


def get_credits_for_complexity(complexity: str) -> int:
    """Return the credit cost for a given complexity tier."""
    tier = PRICING_TIERS.get(complexity, PRICING_TIERS["simple"])
    return tier["credits"]
