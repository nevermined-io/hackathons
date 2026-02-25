"""One-time setup script: registers an MCP agent and payment plan on Nevermined.

Only requires NVM_API_KEY in .env (or as environment variable).
Writes the resulting NVM_AGENT_ID and NVM_PLAN_ID back to .env so the
server can pick them up on next start.

Usage:
    poetry run setup
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv, set_key
from payments_py import Payments, PaymentOptions
from payments_py.common.types import (
    AgentAPIAttributes,
    AgentMetadata,
    Endpoint,
    PlanMetadata,
)
from payments_py.plans import get_dynamic_credits_config, get_free_price_config

# MCP server name — must match the name passed to PaymentsMCP in server.py
MCP_SERVER_NAME = "data-mcp-server"

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

load_dotenv(ENV_FILE)


def main():
    nvm_api_key = os.environ.get("NVM_API_KEY", "")
    nvm_environment = os.environ.get("NVM_ENVIRONMENT", "staging")

    if not nvm_api_key:
        print("Error: NVM_API_KEY is required. Set it in .env or as an environment variable.")
        sys.exit(1)

    # Check if already configured
    existing_agent = os.environ.get("NVM_AGENT_ID", "")
    existing_plan = os.environ.get("NVM_PLAN_ID", "")
    if existing_agent and existing_plan:
        print("Already configured:")
        print(f"  NVM_AGENT_ID = {existing_agent}")
        print(f"  NVM_PLAN_ID  = {existing_plan}")
        print()
        answer = input("Re-register? This creates NEW ids (y/N): ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return

    print(f"\nRegistering MCP agent on Nevermined ({nvm_environment})...\n")

    payments = Payments.get_instance(
        PaymentOptions(nvm_api_key=nvm_api_key, environment=nvm_environment)
    )

    # --- Agent metadata ---
    #
    # Endpoints use MCP logical URIs instead of HTTP URLs.
    # Format: mcp://<serverName>/<type>/<name>
    #
    # This decouples the registration from the physical server location.
    # The paywall resolves these URIs at runtime to match incoming tool calls,
    # so the same registration works for localhost, production, or any host.
    #
    agent_metadata = AgentMetadata(
        name="Data MCP Server",
        description=(
            "MCP server with payment-protected data tools: "
            "web search (1 credit), AI summarization (2-10 credits), "
            "and market research (5-20 credits)."
        ),
        tags=["mcp", "data", "search", "research", "ai"],
    )

    agent_api = AgentAPIAttributes(
        endpoints=[
            Endpoint(verb="POST", url=f"mcp://{MCP_SERVER_NAME}/tools/search_data"),
            Endpoint(verb="POST", url=f"mcp://{MCP_SERVER_NAME}/tools/summarize_data"),
            Endpoint(verb="POST", url=f"mcp://{MCP_SERVER_NAME}/tools/research_data"),
        ],
        agent_definition_url=f"mcp://{MCP_SERVER_NAME}/tools/*",
    )

    # --- Plan: free, 100 dynamic credits (1-20 per request) ---
    plan_metadata = PlanMetadata(
        name="Data MCP Server - Credits Plan",
        description="100 credits for data tools. Search=1cr, Summarize=2-10cr, Research=5-20cr.",
    )

    price_config = get_free_price_config()

    credits_config = get_dynamic_credits_config(
        credits_granted=100,
        min_credits_per_request=1,
        max_credits_per_request=20,
    )

    # --- Register ---
    print("Calling register_agent_and_plan()...")
    result = payments.agents.register_agent_and_plan(
        agent_metadata=agent_metadata,
        agent_api=agent_api,
        plan_metadata=plan_metadata,
        price_config=price_config,
        credits_config=credits_config,
        access_limit="credits",
    )

    agent_id = result.get("agentId", "")
    plan_id = result.get("planId", "")

    if not agent_id or not plan_id:
        print(f"Error: unexpected response: {result}")
        sys.exit(1)

    print("\nRegistered successfully!")
    print(f"  Agent ID: {agent_id}")
    print(f"  Plan ID:  {plan_id}")

    # --- Write to .env ---
    if not ENV_FILE.exists():
        ENV_FILE.write_text(f"NVM_API_KEY={nvm_api_key}\nNVM_ENVIRONMENT={nvm_environment}\n")

    set_key(str(ENV_FILE), "NVM_AGENT_ID", agent_id)
    set_key(str(ENV_FILE), "NVM_PLAN_ID", plan_id)

    print(f"\nSaved to {ENV_FILE}")
    print("\nYou can now start the server:")
    print("  poetry run agent")


if __name__ == "__main__":
    main()
