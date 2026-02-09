"""
FastAPI server wrapping the Strands agent for local development.

Provides HTTP endpoints with x402 payment middleware. Uses OpenAI model.

Usage:
    poetry run agent
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from strands.models.openai import OpenAIModel

from payments_py.x402.fastapi import PaymentMiddleware, X402_HEADERS

from .agent_core import payments, create_agent, NVM_PLAN_ID
from .analytics import analytics
from .pricing import PRICING_TIERS, get_credits_for_complexity

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
    complexity: str = "simple"


# Add payment middleware - protects POST /data with dynamic credits
app.add_middleware(
    PaymentMiddleware,
    payments=payments,
    routes={
        "POST /data": {
            "plan_id": NVM_PLAN_ID,
            "credits": 1,  # Base cost; actual tool cost is handled by @requires_payment
        },
    },
)


@app.post("/data")
async def data(request: Request, body: DataRequest) -> JSONResponse:
    """Query data through the Strands agent (protected by payment middleware)."""
    try:
        # Get payment token from middleware (already verified)
        payment_token = request.headers.get(X402_HEADERS["PAYMENT_SIGNATURE"], "")

        # Run the agent with the payment token
        state = {"payment_token": payment_token} if payment_token else {}
        result = agent(body.query, invocation_state=state)

        # Record analytics
        credits = get_credits_for_complexity(body.complexity)
        analytics.record_request(body.complexity, credits)

        return JSONResponse(content={
            "response": str(result),
            "complexity": body.complexity,
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
    print(f"\nPayment protection enabled for POST /data")
    print(f"Plan ID: {NVM_PLAN_ID}")
    print(f"\nEndpoints:")
    print(f"  POST /data     - Query data (protected, requires x402 token)")
    print(f"  GET  /pricing  - View pricing tiers")
    print(f"  GET  /stats    - View usage analytics")
    print(f"  GET  /health   - Health check")
    print(
        f"\nSend x402 token in '{X402_HEADERS['PAYMENT_SIGNATURE']}' header."
    )

    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
