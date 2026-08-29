from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


PRIMARY_MODEL = "google/gemini-3.7-flash"
LEGACY_PRIMARY_MODEL = "google/gemini-3.1-flash-lite"
FALLBACK_MODEL = "openai/gpt-5.4-nano"
PRIMARY_REASONING_EFFORT = "medium"
PRIMARY_MAX_TOKENS = 500
LEGACY_MAX_TOKENS = 140
FALLBACK_MAX_TOKENS = 140
REQUEST_TIMEOUT_S = 15
PRIMARY_REQUEST_POLICY_VERSION = "validation_request_gemini_3_7_flash_medium_v1"
LEGACY_REQUEST_POLICY_VERSION = "validation_request_gemini_3_1_flash_lite_v1"
FALLBACK_REQUEST_POLICY_VERSION = "validation_request_gpt_5_4_nano_fallback_v1"
STANDARD_PROVIDER_ROUTING = {"allow_fallbacks": False, "require_parameters": True}


@dataclass(frozen=True, repr=False)
class ProviderResponse:
    text: str = field(repr=False)
    provider_metadata: dict[str, Any]


@dataclass(frozen=True, repr=False)
class PreparedValidationRequest:
    payload: dict[str, Any] = field(repr=False)
    timeout_s: int
    observability: dict[str, Any]


def _request_observability(
    *,
    policy_version: str,
    decision_source: str,
    model: str,
    reasoning_effort: str,
    reasoning_sent: bool,
    reasoning_excluded: bool,
    max_tokens: int,
    temperature_sent: bool,
    top_p_sent: bool,
) -> dict[str, Any]:
    payload = {
        "validation_request_policy_version": policy_version,
        "validation_transport": "standard",
        "validation_requested_model": model,
        "validation_attempt_decision_source": decision_source,
        "validation_reasoning_effort_requested": reasoning_effort,
        "validation_reasoning_effort_effective": reasoning_effort,
        "validation_reasoning_sent": reasoning_sent,
        "validation_reasoning_excluded": reasoning_excluded,
        "validation_max_tokens_effective": max_tokens,
        "validation_temperature_sent": temperature_sent,
        "validation_top_p_sent": top_p_sent,
        "validation_provider_fallbacks_allowed": False,
        "validation_provider_require_parameters": True,
    }
    validate_request_observability(payload)
    return payload


def validate_request_observability(value: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(value)
    version = str(payload.get("validation_request_policy_version") or "")
    expected = {
        PRIMARY_REQUEST_POLICY_VERSION: (
            "primary", PRIMARY_MODEL, PRIMARY_REASONING_EFFORT,
            PRIMARY_MAX_TOKENS, True, True, False, False,
        ),
        LEGACY_REQUEST_POLICY_VERSION: (
            "primary", LEGACY_PRIMARY_MODEL, "none",
            LEGACY_MAX_TOKENS, False, False, True, True,
        ),
        FALLBACK_REQUEST_POLICY_VERSION: (
            "fallback", FALLBACK_MODEL, "none",
            FALLBACK_MAX_TOKENS, False, False, True, True,
        ),
    }.get(version)
    if expected is None:
        raise ValueError("unknown_validation_request_policy_version")
    source, model, effort, max_tokens, reasoning_sent, excluded, temperature_sent, top_p_sent = expected
    if payload.get("validation_attempt_decision_source") != source or payload.get("validation_requested_model") != model:
        raise ValueError("incoherent_validation_request_source_or_model")
    if payload.get("validation_reasoning_effort_requested") != effort or payload.get("validation_reasoning_effort_effective") != effort:
        raise ValueError("incoherent_validation_reasoning_effort")
    if payload.get("validation_transport") != "standard":
        raise ValueError("invalid_validation_transport")
    coherence = (
        ("validation_reasoning_sent", reasoning_sent),
        ("validation_reasoning_excluded", excluded),
        ("validation_max_tokens_effective", max_tokens),
        ("validation_temperature_sent", temperature_sent),
        ("validation_top_p_sent", top_p_sent),
        ("validation_provider_fallbacks_allowed", False),
        ("validation_provider_require_parameters", True),
    )
    for key, expected_value in coherence:
        if payload.get(key) != expected_value or type(payload.get(key)) is not type(expected_value):
            raise ValueError(f"incoherent_{key}")
    return payload


def prepare_validation_request(
    *,
    model: str,
    decision_source: str,
    messages: Sequence[Mapping[str, str]],
    timeout_s: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
    reasoning_effort: str,
    llm_module: Any,
) -> PreparedValidationRequest:
    if int(timeout_s) != REQUEST_TIMEOUT_S:
        raise ValueError("invalid_validation_request_timeout")
    if float(temperature) != 0.0 or float(top_p) != 1.0:
        raise ValueError("invalid_validation_fallback_sampling_policy")
    payload: dict[str, Any] = {
        "model": model,
        "messages": list(messages),
        "provider": dict(STANDARD_PROVIDER_ROUTING),
    }
    if decision_source == "primary" and model == PRIMARY_MODEL:
        if reasoning_effort != PRIMARY_REASONING_EFFORT or int(max_tokens) != PRIMARY_MAX_TOKENS:
            raise ValueError("invalid_validation_primary_request_policy")
        payload.update(reasoning={"effort": PRIMARY_REASONING_EFFORT, "exclude": True}, max_tokens=PRIMARY_MAX_TOKENS)
        observability = _request_observability(
            policy_version=PRIMARY_REQUEST_POLICY_VERSION, decision_source=decision_source,
            model=model, reasoning_effort=PRIMARY_REASONING_EFFORT, reasoning_sent=True,
            reasoning_excluded=True, max_tokens=PRIMARY_MAX_TOKENS,
            temperature_sent=False, top_p_sent=False,
        )
    elif decision_source == "primary" and model == LEGACY_PRIMARY_MODEL:
        payload.update(temperature=float(temperature), top_p=float(top_p), max_tokens=LEGACY_MAX_TOKENS)
        observability = _request_observability(
            policy_version=LEGACY_REQUEST_POLICY_VERSION, decision_source=decision_source,
            model=model, reasoning_effort="none", reasoning_sent=False,
            reasoning_excluded=False, max_tokens=LEGACY_MAX_TOKENS,
            temperature_sent=True, top_p_sent=True,
        )
    elif decision_source == "fallback" and model == FALLBACK_MODEL:
        payload.update(temperature=float(temperature), top_p=float(top_p), max_tokens=FALLBACK_MAX_TOKENS)
        observability = _request_observability(
            policy_version=FALLBACK_REQUEST_POLICY_VERSION, decision_source=decision_source,
            model=model, reasoning_effort="none", reasoning_sent=False,
            reasoning_excluded=False, max_tokens=FALLBACK_MAX_TOKENS,
            temperature_sent=True, top_p_sent=True,
        )
    else:
        raise ValueError("unsupported_validation_request_policy")
    return PreparedValidationRequest(
        payload=llm_module.with_provider_attribution(payload, caller="validation_agent"),
        timeout_s=int(timeout_s),
        observability=observability,
    )


def request_provider_response(
    *,
    prepared_request: PreparedValidationRequest,
    requests_module: Any,
    llm_module: Any,
    logger: Any,
) -> ProviderResponse:
    response = requests_module.post(
        llm_module.or_chat_completions_url(),
        json=prepared_request.payload,
        headers=llm_module.or_headers(caller="validation_agent"),
        timeout=prepared_request.timeout_s,
    )
    response.raise_for_status()
    response_payload = llm_module.read_openrouter_response_payload(response)
    provider_metadata = llm_module.extract_openrouter_provider_metadata(
        response_payload,
        requested_model=str(prepared_request.payload["model"]),
    )
    llm_module.log_provider_metadata(
        logger, "validation_agent_provider_response", provider_metadata,
    )
    return ProviderResponse(
        text=llm_module.extract_openrouter_text(response_payload),
        provider_metadata=provider_metadata,
    )
