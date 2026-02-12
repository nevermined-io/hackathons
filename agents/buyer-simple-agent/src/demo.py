"""
Strands-native buyer demo — LLM orchestrates the full purchase flow.

Pre-scripted prompts that exercise all buyer tools:
1. Discover what data is available
2. Check credit balance
3. Purchase data
4. Review spending

Usage:
    # First start the seller: cd ../seller-simple-agent && poetry run agent
    # Then run:
    poetry run demo
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

from strands.models.openai import OpenAIModel

from .strands_agent import create_agent, NVM_PLAN_ID, SELLER_URL

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    print("OPENAI_API_KEY is required. Set it in .env file.")
    sys.exit(1)

model = OpenAIModel(
    client_args={"api_key": OPENAI_API_KEY},
    model_id=os.getenv("MODEL_ID", "gpt-4o-mini"),
)
agent = create_agent(model)


DEMO_PROMPTS = [
    "What data is available from the seller? Show me the pricing tiers.",
    "How many credits do I have? Check my balance and budget.",
    "Search for the latest AI agent trends.",
    "What's my spending so far today?",
]


def main():
    """Run the LLM-orchestrated buyer demo."""
    print("=" * 60)
    print("Data Buying Agent — Strands Demo")
    print("=" * 60)
    print(f"Seller: {SELLER_URL}")
    print(f"Plan ID: {NVM_PLAN_ID}")

    for i, prompt in enumerate(DEMO_PROMPTS, 1):
        print(f"\n{'=' * 60}")
        print(f"PROMPT {i}: {prompt}")
        print("=" * 60)

        try:
            result = agent(prompt)
            print(f"\nAgent: {result}")
        except Exception as e:
            print(f"\nError: {e}")

    print(f"\n{'=' * 60}")
    print("DEMO COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
