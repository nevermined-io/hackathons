"""
AWS BedrockAgentCoreApp wrapper for deploying the buyer agent to AgentCore.

Uses Bedrock model instead of OpenAI. The buyer agent runs as a client-side
agent that purchases data from sellers via x402.

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

    async for event in agent.stream_async(prompt):
        if "data" in event:
            yield {"type": "chunk", "data": event["data"]}

    yield {"type": "complete"}


def main():
    """Run the AgentCore app."""
    port = int(os.getenv("PORT", "8080"))
    print(f"Data Buying Agent (AgentCore) running on port {port}")
    app.run(port=port)


if __name__ == "__main__":
    main()
