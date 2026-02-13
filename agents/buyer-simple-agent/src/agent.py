"""
Interactive CLI for the data buying agent.

Read-eval-print loop: user types queries, the Strands agent orchestrates
buyer tools (discover, check balance, purchase) autonomously.

In A2A mode (the default), also starts a registration server so sellers
can announce themselves automatically.

Usage:
    poetry run python -m src.agent
    poetry run python -m src.agent --mode http
"""

import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from strands.models.openai import OpenAIModel

from .strands_agent import create_agent, NVM_PLAN_ID, SELLER_URL, seller_registry
from .registration_server import start_registration_server

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
BUYER_PORT = int(os.getenv("BUYER_PORT", "8000"))

if not OPENAI_API_KEY:
    print("OPENAI_API_KEY is required. Set it in .env file.")
    sys.exit(1)


def _parse_args():
    parser = argparse.ArgumentParser(description="Data Buying Agent — Interactive CLI")
    parser.add_argument(
        "--mode",
        choices=["a2a", "http"],
        default="a2a",
        help="Agent mode: 'a2a' for A2A marketplace (default), 'http' for direct x402",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=BUYER_PORT,
        help=f"Port for the A2A registration server (default: {BUYER_PORT})",
    )
    return parser.parse_args()


def main():
    """Run the interactive buyer agent CLI."""
    args = _parse_args()
    mode = args.mode
    port = args.port

    model = OpenAIModel(
        client_args={"api_key": OPENAI_API_KEY},
        model_id=os.getenv("MODEL_ID", "gpt-4o-mini"),
    )
    agent = create_agent(model, mode=mode)

    # Start registration server in A2A mode
    if mode == "a2a":
        start_registration_server(seller_registry, port=port)

    print("=" * 60)
    print("Data Buying Agent — Interactive CLI")
    print("=" * 60)
    print(f"Mode: {mode}")
    print(f"Plan ID: {NVM_PLAN_ID}")
    if mode == "a2a":
        print(f"Registration: http://localhost:{port} (sellers register here)")
        print(f"Debug:        http://localhost:{port}/sellers")
    else:
        print(f"Seller: {SELLER_URL}")
    print("\nType your queries (or 'quit' to exit):")
    print("Examples:")
    if mode == "a2a":
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
