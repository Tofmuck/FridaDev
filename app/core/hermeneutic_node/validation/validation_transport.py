from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, repr=False)
class ProviderResponse:
    text: str = field(repr=False)
    provider_metadata: dict[str, Any]


def request_provider_response(
    *,
    model: str,
    messages: Sequence[Mapping[str, str]],
    timeout_s: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
    requests_module: Any,
    llm_module: Any,
    logger: Any,
) -> ProviderResponse:
    payload = llm_module.with_provider_attribution(
        {
            "model": model,
            "messages": list(messages),
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        },
        caller="validation_agent",
    )
    response = requests_module.post(
        llm_module.or_chat_completions_url(),
        json=payload,
        headers=llm_module.or_headers(caller="validation_agent"),
        timeout=timeout_s,
    )
    response.raise_for_status()
    response_payload = llm_module.read_openrouter_response_payload(response)
    provider_metadata = llm_module.extract_openrouter_provider_metadata(
        response_payload,
        requested_model=model,
    )
    llm_module.log_provider_metadata(
        logger,
        "validation_agent_provider_response",
        provider_metadata,
    )
    return ProviderResponse(
        text=llm_module.extract_openrouter_text(response_payload),
        provider_metadata=provider_metadata,
    )
