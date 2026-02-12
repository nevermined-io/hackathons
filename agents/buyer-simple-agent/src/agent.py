"""
Interactive CLI for the data buying agent.

Read-eval-print loop: user types queries, the Strands agent orchestrates
buyer tools (discover, check balance, purchase) autonomously.

Usage:
    poetry run agent
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


def main():
    """Run the interactive buyer agent CLI."""
    print("=" * 60)
    print("Data Buying Agent — Interactive CLI")
    print("=" * 60)
    print(f"Seller: {SELLER_URL}")
    print(f"Plan ID: {NVM_PLAN_ID}")
    print("\nType your queries (or 'quit' to exit):")
    print("Examples:")
    print('  "What data is available from the seller?"')
    print('  "How many credits do I have?"')
    print('  "Search for the latest AI agent trends"')
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        try:
            result = agent(user_input)
            print(f"\nAgent: {result}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
