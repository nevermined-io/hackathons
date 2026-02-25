"""Market research tool - multi-step research pipeline."""

import os
import re

import httpx
from openai import OpenAI

from .web_search import search_web


def _fetch_url_content(url: str, max_chars: int = 2000) -> str:
    """Fetch and extract text content from a URL."""
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": "MCPServerAgent/1.0"})
            text = response.text
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:max_chars]
    except Exception:
        return ""


def research_market_impl(query: str, depth: str = "standard") -> dict:
    """Conduct market research by combining search, content fetching, and summarization.

    Args:
        query: The research topic or question.
        depth: Research depth - 'standard' (search + summarize) or 'deep' (+ URL fetching).

    Returns:
        dict with status, content (for Strands), report, and sources.
    """
    sources = []

    try:
        # Step 1: Web search
        search_results = search_web(query, max_results=8)
        raw_results = search_results.get("results", [])

        if not raw_results:
            return {
                "status": "success",
                "content": [{"text": f"No data found for research query: '{query}'"}],
                "report": f"No data found for: {query}",
                "sources": [],
            }

        sources = [
            {"title": r.get("title", ""), "url": r["url"]}
            for r in raw_results
            if r.get("url")
        ]

        # Step 2: Gather content
        content_pieces = [r.get("snippet", "") for r in raw_results if r.get("snippet")]

        if depth == "deep":
            for r in raw_results[:3]:
                url = r.get("url", "")
                if url:
                    fetched = _fetch_url_content(url)
                    if fetched:
                        content_pieces.append(fetched)

        combined_content = "\n\n".join(content_pieces)

        # Step 3: Synthesize with LLM
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        model_id = os.environ.get("MODEL_ID", "gpt-4o-mini")

        completion = client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a market research analyst. Based on the provided data, "
                        "write a concise research report. Include:\n"
                        "1. Executive Summary (2-3 sentences)\n"
                        "2. Key Findings (3-5 bullet points)\n"
                        "3. Market Trends (if applicable)\n"
                        "4. Recommendations (2-3 actionable items)"
                    ),
                },
                {
                    "role": "user",
                    "content": f"Research query: {query}\n\nData:\n{combined_content[:6000]}",
                },
            ],
            max_tokens=1000,
        )

        report = completion.choices[0].message.content or "No report generated"

        return {
            "status": "success",
            "content": [{"text": report}],
            "report": report,
            "sources": sources,
        }

    except Exception as e:
        return {
            "status": "error",
            "content": [{"text": f"Research failed: {e}"}],
            "report": "",
            "sources": sources,
        }
