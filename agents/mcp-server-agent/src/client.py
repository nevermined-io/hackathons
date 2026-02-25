"""Demo script showing how to connect to the MCP server as a client.

Demonstrates the full flow:
1. Order (subscribe to) the payment plan
2. Get an x402 access token from Nevermined
3. List available tools via MCP
4. Call a payment-protected tool
"""

import asyncio
import os

import httpx
from dotenv import load_dotenv
from payments_py import Payments, PaymentOptions

load_dotenv()

NVM_API_KEY = os.environ.get("NVM_SUBSCRIBER_API_KEY", "")
NVM_ENVIRONMENT = os.environ.get("NVM_ENVIRONMENT", "staging")
NVM_PLAN_ID = os.environ.get("NVM_PLAN_ID", "")
SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:3000")

MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}


async def mcp_call(client, id, method, params=None):
    """Send a JSON-RPC request to the MCP endpoint."""
    resp = await client.post(
        f"{SERVER_URL}/mcp",
        headers=MCP_HEADERS,
        json={
            "jsonrpc": "2.0",
            "id": id,
            "method": method,
            "params": params or {},
        },
    )
    return resp.status_code, resp.json()


async def run_demo():
    print("=== MCP Server Agent Demo ===\n")

    # Step 1: Health check
    print("1. Checking server health...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{SERVER_URL}/health")
        print(f"   Health: {resp.status_code} {resp.json()}\n")

    # Step 2: Subscribe to the plan (only needed once)
    print("2. Checking subscription...")
    payments = Payments.get_instance(
        PaymentOptions(nvm_api_key=NVM_API_KEY, environment=NVM_ENVIRONMENT)
    )
    balance = payments.plans.get_plan_balance(NVM_PLAN_ID)
    if not balance.is_subscriber:
        print("   Not subscribed yet — ordering plan...")
        order_result = payments.plans.order_plan(NVM_PLAN_ID)
        print(f"   Order result: {order_result}")
    else:
        print(f"   Already subscribed (balance: {balance.balance} credits)")

    # Step 3: Get x402 access token
    print("\n3. Getting x402 access token...")
    token_result = payments.x402.get_x402_access_token(NVM_PLAN_ID)
    access_token = token_result["accessToken"]
    print(f"   Token: {access_token[:60]}...\n")

    # Set auth header for all MCP calls
    MCP_HEADERS["Authorization"] = f"Bearer {access_token}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 4: Initialize MCP session
        print("4. Initializing MCP session...")
        status, data = await mcp_call(client, 1, "initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "demo-client", "version": "1.0.0"},
        })
        server_info = data.get("result", {}).get("serverInfo", {})
        print(f"   Server: {server_info.get('name')} v{server_info.get('version')}")

        # Step 5: List tools
        print("\n5. Listing available tools...")
        status, data = await mcp_call(client, 2, "tools/list")
        tools = data.get("result", {}).get("tools", [])
        for tool in tools:
            print(f"   - {tool['name']}: {tool.get('description', '')[:80]}")

        # Step 6: Call search_data tool (1 credit)
        print("\n6. Calling search_data tool (1 credit)...")
        status, data = await mcp_call(client, 3, "tools/call", {
            "name": "search_data",
            "arguments": {"query": "artificial intelligence trends 2025"},
        })
        result = data.get("result", {})
        content = result.get("content", [])
        meta = result.get("_meta", {})
        if content:
            text = content[0].get("text", "")
            print(f"   Result: {text[:300]}")
        if meta:
            print(f"   Credits redeemed: {meta.get('creditsRedeemed', 'N/A')}")
            print(f"   Success: {meta.get('success', 'N/A')}")

    print("\n=== Demo complete ===")


def main():
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
