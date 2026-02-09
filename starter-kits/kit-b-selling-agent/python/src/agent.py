"""
FastAPI server wrapping the Strands agent for local development.

Thin HTTP wrapper around the Strands agent. Payment protection is handled
entirely by @requires_payment on the tools — no FastAPI middleware needed.

Usage:
    poetry run agent
"""

import base64
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from strands.models.openai import OpenAIModel

from payments_py.x402.strands import extract_payment_required

from .agent_core import create_agent, NVM_PLAN_ID
from .analytics import analytics
from .pricing import PRICING_TIERS

# Configuration
PORT = int(os.getenv("PORT", "3000"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

if not OPENAI_API_KEY:
    print("OPENAI_API_KEY is required. Set it in .env file.")
    sys.exit(1)

# Create Strands agent with OpenAI model
model = OpenAIModel(
    client_args={"api_key": OPENAI_API_KEY},
    model_id=os.getenv("MODEL_ID", "gpt-4o-mini"),
)
agent = create_agent(model)

# Create FastAPI app
app = FastAPI(
    title="Kit B - Data Selling Agent (Python)",
    description="Strands AI agent with x402 payment-protected data tools",
)


class DataRequest(BaseModel):
    query: str


@app.post("/data")
async def data(request: Request, body: DataRequest) -> JSONResponse:
    """Query data through the Strands agent.

    Payment is handled by @requires_payment on each tool. If no valid
    token is provided, the tool returns a PaymentRequired error which
    we translate into an HTTP 402 response with the standard headers.
    """
    try:
        # Pass payment token from HTTP header to the Strands agent
        payment_token = request.headers.get("payment-signature", "")
        state = {"payment_token": payment_token} if payment_token else {}

        result = agent(body.query, invocation_state=state)

        # Check if payment was required but not fulfilled
        payment_required = extract_payment_required(agent.messages)
        if payment_required and not state.get("payment_settlement"):
            encoded = base64.b64encode(
                json.dumps(payment_required).encode()
            ).decode()
            return JSONResponse(
                status_code=402,
                content={
                    "error": "Payment Required",
                    "message": str(result),
                },
                headers={"payment-required": encoded},
            )

        # Success — record analytics
        settlement = state.get("payment_settlement")
        credits = settlement.credits_redeemed if settlement else 0
        analytics.record_request("request", credits)

        return JSONResponse(content={
            "response": str(result),
            "credits_used": credits,
        })

    except Exception as error:
        print(f"Error in /data: {error}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.get("/pricing")
async def pricing() -> JSONResponse:
    """Get pricing information (unprotected)."""
    return JSONResponse(content={
        "planId": NVM_PLAN_ID,
        "tiers": PRICING_TIERS,
    })


@app.get("/stats")
async def stats() -> JSONResponse:
    """Get usage statistics (unprotected)."""
    return JSONResponse(content=analytics.get_stats())


@app.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint (unprotected)."""
    return JSONResponse(content={"status": "ok"})


def main():
    """Run the FastAPI server."""
    print(f"Data Selling Agent running on http://localhost:{PORT}")
    print(f"\nPayment protection via @requires_payment on Strands tools")
    print(f"Plan ID: {NVM_PLAN_ID}")
    print(f"\nEndpoints:")
    print(f"  POST /data     - Query data (send x402 token in 'payment-signature' header)")
    print(f"  GET  /pricing  - View pricing tiers")
    print(f"  GET  /stats    - View usage analytics")
    print(f"  GET  /health   - Health check")

    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
