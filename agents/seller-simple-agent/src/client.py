"""
HTTP x402 client - demonstrates the full payment flow against the FastAPI server.

Shows the complete x402 HTTP protocol:
1. GET /pricing - discover pricing tiers
2. POST /data without token -> 402 Payment Required
3. Decode payment requirements from header
4. Generate x402 access token
5. POST /data with token -> 200 OK
6. GET /stats - view usage analytics

Usage:
    # First start the server: poetry run agent
    # Then run this client:
    poetry run client
"""

import base64
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

import httpx

from payments_py import Payments, PaymentOptions

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:3000")
NVM_API_KEY = os.getenv("NVM_API_KEY", "")
NVM_ENVIRONMENT = os.getenv("NVM_ENVIRONMENT", "sandbox")
NVM_PLAN_ID = os.getenv("NVM_PLAN_ID", "")

if not NVM_API_KEY or not NVM_PLAN_ID:
    print("NVM_API_KEY and NVM_PLAN_ID are required.")
    sys.exit(1)

payments = Payments.get_instance(
    PaymentOptions(nvm_api_key=NVM_API_KEY, environment=NVM_ENVIRONMENT)
)


def decode_base64_json(base64_str: str) -> dict:
    """Decode base64-encoded JSON from headers."""
    json_str = base64.b64decode(base64_str).decode("utf-8")
    return json.loads(json_str)


def pretty_json(obj: dict) -> str:
    """Format JSON for console output."""
    return json.dumps(obj, indent=2)


def main():
    """Run the x402 HTTP payment flow demo."""
    print("=" * 60)
    print("x402 HTTP Payment Flow - Data Selling Agent")
    print("=" * 60)
    print(f"\nServer: {SERVER_URL}")
    print(f"Plan ID: {NVM_PLAN_ID}")

    with httpx.Client(timeout=60.0) as client:
        # Step 1: Discover pricing
        print("\n" + "=" * 60)
        print("STEP 1: Discover pricing tiers")
        print("=" * 60)

        pricing_resp = client.get(f"{SERVER_URL}/pricing")
        print(f"\nGET /pricing -> {pricing_resp.status_code}")
        print(pretty_json(pricing_resp.json()))

        # Step 2: Request without token -> 402
        print("\n" + "=" * 60)
        print("STEP 2: Request without payment token")
        print("=" * 60)

        response1 = client.post(
            f"{SERVER_URL}/data",
            headers={"Content-Type": "application/json"},
            json={"query": "AI agent market trends 2025"},
        )

        print(f"\nPOST /data -> {response1.status_code} {response1.reason_phrase}")

        if response1.status_code != 402:
            print(f"Expected 402 Payment Required, got: {response1.status_code}")
            sys.exit(1)

        # Step 3: Decode payment requirements
        print("\n" + "=" * 60)
        print("STEP 3: Decode payment requirements from header")
        print("=" * 60)

        payment_required_header = response1.headers.get("payment-required")

        if not payment_required_header:
            print("Missing 'payment-required' header in 402 response")
            sys.exit(1)

        payment_required = decode_base64_json(payment_required_header)
        print("\nDecoded Payment Requirements:")
        print(pretty_json(payment_required))

        # Step 4: Generate x402 access token
        print("\n" + "=" * 60)
        print("STEP 4: Generate x402 access token")
        print("=" * 60)

        print("\nCalling payments.x402.get_x402_access_token()...")
        token_result = payments.x402.get_x402_access_token(NVM_PLAN_ID)
        access_token = token_result["accessToken"]

        print(f"Token generated! Length: {len(access_token)} chars")
        print(f"Preview: {access_token[:50]}...")

        # Step 5: Request with token -> success
        print("\n" + "=" * 60)
        print("STEP 5: Request with payment token")
        print("=" * 60)

        print("\nSending POST /data with 'payment-signature' header...")

        response2 = client.post(
            f"{SERVER_URL}/data",
            headers={
                "Content-Type": "application/json",
                "payment-signature": access_token,
            },
            json={"query": "AI agent market trends 2025"},
        )

        print(f"\nPOST /data -> {response2.status_code} {response2.reason_phrase}")

        if response2.status_code != 200:
            print(f"Expected 200 OK, got: {response2.status_code}")
            print(f"Response: {response2.text}")
            sys.exit(1)

        print("\nResponse body:")
        print(pretty_json(response2.json()))

        # Step 6: Check analytics
        print("\n" + "=" * 60)
        print("STEP 6: Check usage analytics")
        print("=" * 60)

        stats_resp = client.get(f"{SERVER_URL}/stats")
        print(f"\nGET /stats -> {stats_resp.status_code}")
        print(pretty_json(stats_resp.json()))

        # Summary
        print("\n" + "=" * 60)
        print("FLOW COMPLETE!")
        print("=" * 60)
        print(
            """
x402 HTTP Payment Flow Summary:
1. GET  /pricing              -> Discovered 3 pricing tiers
2. POST /data (no token)      -> 402 Payment Required
3. Decoded payment-required   -> Plan ID, scheme, network
4. Generated access token     -> Using Nevermined SDK
5. POST /data (with token)    -> 200 OK + agent response
6. GET  /stats                -> Usage analytics
"""
        )


if __name__ == "__main__":
    main()
