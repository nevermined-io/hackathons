"""
AWS BedrockAgentCoreApp wrapper for deploying the agent to AgentCore.

Uses Bedrock model instead of OpenAI. Follows the cost-optimization-agent pattern.

Usage:
    poetry run agent-agentcore

Requires:
    pip install bedrock-agentcore   (or: poetry install -E agentcore)
"""

import os

from dotenv import load_dotenv

load_dotenv()

from bedrock_agentcore import BedrockAgentCoreApp
from strands.models.bedrock import BedrockModel

from .strands_agent import create_agent

model = BedrockModel(
    model_id=os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0"),
    region_name=os.getenv("AWS_REGION", "us-west-2"),
)
agent = create_agent(model)

app = BedrockAgentCoreApp()


@app.entrypoint
async def process_request(payload):
    """Process incoming requests via AgentCore."""
    prompt = payload.get("prompt", "")
    payment_token = payload.get("payment_token")

    state = {"payment_token": payment_token} if payment_token else {}

    async for event in agent.stream_async(prompt, invocation_state=state):
        if "data" in event:
            yield {"type": "chunk", "data": event["data"]}

    yield {"type": "complete"}


def main():
    """Run the AgentCore app."""
    port = int(os.getenv("PORT", "8080"))
    print(f"Data Selling Agent (AgentCore) running on port {port}")
    app.run(port=port)


if __name__ == "__main__":
    main()
