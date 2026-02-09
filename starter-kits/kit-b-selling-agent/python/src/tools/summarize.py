"""Content summarization tool - uses OpenAI for LLM-powered analysis."""

import os

from openai import OpenAI


def summarize_content_impl(content: str, focus: str = "key_findings") -> dict:
    """Summarize content using an LLM.

    Args:
        content: The text content to summarize.
        focus: Focus area - 'key_findings', 'action_items', 'trends', or 'risks'.

    Returns:
        dict with status, content (for Strands), summary, and key_points.
    """
    focus_prompts = {
        "key_findings": "Extract the most important findings and insights.",
        "action_items": "Identify actionable recommendations and next steps.",
        "trends": "Identify emerging trends and patterns.",
        "risks": "Identify potential risks and concerns.",
    }

    focus_instruction = focus_prompts.get(focus, focus_prompts["key_findings"])

    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        model_id = os.environ.get("MODEL_ID", "gpt-4o-mini")

        completion = client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a data analyst. Summarize the provided content. "
                        f"{focus_instruction}\n\n"
                        "Return your response in this exact format:\n"
                        "SUMMARY: <2-3 sentence summary>\n"
                        "KEY POINTS:\n"
                        "- <point 1>\n"
                        "- <point 2>\n"
                        "- <point 3>"
                    ),
                },
                {"role": "user", "content": content[:4000]},  # Truncate long content
            ],
            max_tokens=500,
        )

        response_text = completion.choices[0].message.content or "No summary generated"

        # Parse the structured response
        summary = response_text
        key_points = []
        if "KEY POINTS:" in response_text:
            parts = response_text.split("KEY POINTS:")
            summary = parts[0].replace("SUMMARY:", "").strip()
            points_text = parts[1].strip()
            key_points = [
                p.strip().lstrip("- ")
                for p in points_text.split("\n")
                if p.strip().startswith("-")
            ]

        return {
            "status": "success",
            "content": [{"text": response_text}],
            "summary": summary,
            "key_points": key_points,
        }

    except Exception as e:
        return {
            "status": "error",
            "content": [{"text": f"Summarization failed: {str(e)}"}],
            "summary": "",
            "key_points": [],
        }
