"""Web search tool - searches the web using DuckDuckGo."""

import httpx


def search_web(query: str, max_results: int = 5) -> dict:
    """Search the web using DuckDuckGo Instant Answer API.

    No API key required. Hackathon teams can swap in Exa, Tavily, or Apify.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        dict with status, content (for Strands), and results list.
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1"},
            )
            data = response.json()

        results = []

        # DuckDuckGo returns results in RelatedTopics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append({
                    "title": topic.get("Text", "")[:100],
                    "url": topic.get("FirstURL", ""),
                    "snippet": topic.get("Text", ""),
                })

        # Also include the Abstract if available
        abstract = data.get("Abstract", "")
        if abstract:
            results.insert(0, {
                "title": data.get("Heading", "Overview"),
                "url": data.get("AbstractURL", ""),
                "snippet": abstract,
            })

        if results:
            summary = f"Found {len(results)} results for '{query}'"
            details = "\n".join(
                f"- {r['title']}: {r['snippet'][:200]}" for r in results
            )
            text = f"{summary}\n\n{details}"
        else:
            text = f"No results found for '{query}'. Try a different search term."

        return {
            "status": "success",
            "content": [{"text": text}],
            "results": results,
        }

    except Exception as e:
        return {
            "status": "error",
            "content": [{"text": f"Search failed: {e}"}],
            "results": [],
        }
