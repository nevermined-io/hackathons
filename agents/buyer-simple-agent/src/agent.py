"""
Interactive CLI for the data buying agent.

Read-eval-print loop: user types queries, the Strands agent orchestrates
buyer tools (discover, check balance, purchase) autonomously.

In A2A mode, also starts a registration server so sellers can announce
themselves automatically.

Usage:
    poetry run agent
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

from strands.models.openai import OpenAIModel

from .strands_agent import create_agent, NVM_PLAN_ID, SELLER_URL, A2A_MODE, seller_registry
from .registration_server import start_registration_server

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
BUYER_PORT = int(os.getenv("BUYER_PORT", "8000"))

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
    # Start registration server in A2A mode
    if A2A_MODE:
        start_registration_server(seller_registry, port=BUYER_PORT)

    print("=" * 60)
    print("Data Buying Agent — Interactive CLI")
    print("=" * 60)
    print(f"Seller: {SELLER_URL}")
    print(f"Plan ID: {NVM_PLAN_ID}")
    if A2A_MODE:
        print(f"Registration: http://localhost:{BUYER_PORT} (A2A mode)")
        print(f"Debug:        http://localhost:{BUYER_PORT}/sellers")
    print("\nType your queries (or 'quit' to exit):")
    print("Examples:")
    print('  "What sellers are available?"')
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
