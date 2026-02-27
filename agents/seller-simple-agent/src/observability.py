"""
Nevermined observability helpers.

Routes OpenAI calls through Nevermined's observability proxy so that
token usage, cost, and request events appear in the Nevermined dashboard.

The key integration point is ``payments.observability.with_openai()``, which
returns an ``OpenAIConfiguration`` containing a proxy base_url and Helicone
headers that instrument every LLM call.

Usage:
    from src.observability import create_observability_client, create_observability_model

    # For direct OpenAI calls (tools)
    client = create_observability_client(payments, agent_request, api_key)

    # For Strands OpenAIModel
    model = create_observability_model(payments, agent_request, api_key, model_id)
"""

import os
from uuid import uuid4

from openai import OpenAI
from strands.models.openai import OpenAIModel

from payments_py import Payments
from payments_py.common.types import StartAgentRequest

from .log import get_logger, log

_logger = get_logger("seller.observability")


def _resolve_agent_request(agent_request) -> StartAgentRequest | None:
    """Convert agent_request to StartAgentRequest if needed."""
    if agent_request is None:
        return None
    if isinstance(agent_request, StartAgentRequest):
        return agent_request
    if isinstance(agent_request, dict):
        try:
            return StartAgentRequest.model_validate(agent_request)
        except Exception:
            return None
    return agent_request


def create_observability_client(
    payments: Payments,
    agent_request,
    api_key: str | None = None,
) -> OpenAI | None:
    """Create an OpenAI client routed through Nevermined observability.

    Returns None if agent_request is unavailable or observability setup fails.
    """
    start_request = _resolve_agent_request(agent_request)
    if not start_request:
        return None

    api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    try:
        config = payments.observability.with_openai(
            api_key=api_key,
            start_agent_request=start_request,
            custom_properties={"sessionid": str(uuid4())},
        )
        log(_logger, "OBSERVABILITY", "ENABLED",
            f"request_id={getattr(start_request, 'agent_request_id', 'unknown')}")
        return OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            default_headers=config.default_headers,
        )
    except Exception as exc:
        log(_logger, "OBSERVABILITY", "FAILED", str(exc))
        return None


def create_observability_model(
    payments: Payments,
    agent_request,
    api_key: str | None = None,
    model_id: str | None = None,
) -> OpenAIModel | None:
    """Create a Strands OpenAIModel routed through Nevermined observability.

    Returns None if agent_request is unavailable or observability setup fails.
    """
    start_request = _resolve_agent_request(agent_request)
    if not start_request:
        return None

    api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    model_id = model_id or os.environ.get("MODEL_ID", "gpt-4o-mini")

    try:
        config = payments.observability.with_openai(
            api_key=api_key,
            start_agent_request=start_request,
            custom_properties={"sessionid": str(uuid4())},
        )
        return OpenAIModel(
            client_args={
                "api_key": config.api_key,
                "base_url": config.base_url,
                "default_headers": config.default_headers,
            },
            model_id=model_id,
        )
    except Exception as exc:
        log(_logger, "OBSERVABILITY", "FAILED", f"model setup: {exc}")
        return None
