from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Iterator, Mapping


@dataclass(frozen=True, repr=False)
class PreparedProviderCall:
    headers: Mapping[str, str] = field(repr=False)
    payload: Mapping[str, Any] = field(repr=False)
    call_model: str
    provider_title: str
    reasoning_observability: Mapping[str, Any]
    url: str = field(repr=False)


@dataclass(repr=False)
class ProviderStreamState:
    response_open: bool = False
    provider_metadata: dict[str, object] = field(default_factory=dict, repr=False)


def require_main_model_secret(*, runtime_settings_module: Any) -> None:
    runtime_settings_module.get_runtime_secret_value('main_model', 'api_key')


def prepare_provider_call(
    *,
    conversation: Mapping[str, Any],
    prompt_messages: list[dict[str, Any]],
    temperature: float,
    top_p: float,
    max_tokens: int,
    stream_req: bool,
    llm_module: Any,
    admin_logs_module: Any,
) -> PreparedProviderCall:
    headers = llm_module.or_headers(caller='llm')
    payload = llm_module.build_payload(
        prompt_messages,
        temperature,
        top_p,
        max_tokens,
        stream=stream_req,
    )
    call_model = str(payload['model'])
    provider_title = llm_module.resolve_provider_title('llm')
    reasoning_observability_builder = getattr(
        llm_module,
        'main_llm_reasoning_observability_from_payload',
        None,
    )
    reasoning_observability = (
        reasoning_observability_builder(payload)
        if callable(reasoning_observability_builder)
        else {}
    )
    url = llm_module.or_chat_completions_url()
    admin_logs_module.log_event(
        'llm_payload',
        conversation_id=conversation['id'],
        model=call_model,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stream=stream_req,
        message_count=len(prompt_messages),
        provider_caller='llm',
        provider_title=provider_title,
        **reasoning_observability,
    )
    return PreparedProviderCall(
        headers=headers,
        payload=payload,
        call_model=call_model,
        provider_title=provider_title,
        reasoning_observability=reasoning_observability,
        url=url,
    )


def read_non_stream_provider_response(
    *,
    prepared_call: PreparedProviderCall,
    conversation: Mapping[str, Any],
    prompt_messages: list[dict[str, Any]],
    requests_module: Any,
    llm_module: Any,
    admin_logs_module: Any,
    config_module: Any,
    logger: Any,
) -> str:
    logger.info(
        'llm_call id=%s model=%s messages=%s',
        conversation['id'],
        prepared_call.call_model,
        len(prompt_messages),
    )
    admin_logs_module.log_event(
        'llm_call',
        conversation_id=conversation['id'],
        model=prepared_call.call_model,
        message_count=len(prompt_messages),
        stream=False,
        provider_caller='llm',
        provider_title=prepared_call.provider_title,
        **prepared_call.reasoning_observability,
    )
    response = requests_module.post(
        prepared_call.url,
        json=prepared_call.payload,
        headers=prepared_call.headers,
        timeout=config_module.TIMEOUT_S,
    )
    response.raise_for_status()
    obj = llm_module.read_openrouter_response_payload(response)
    provider_fields = llm_module.build_provider_observability_fields(
        caller='llm',
        provider_metadata=llm_module.extract_openrouter_provider_metadata(
            obj,
            requested_model=prepared_call.call_model,
        ),
    )
    llm_module.log_provider_metadata(logger, 'llm_provider_response', provider_fields)
    admin_logs_module.log_event(
        'llm_provider_response',
        conversation_id=conversation['id'],
        **provider_fields,
    )
    return llm_module.extract_openrouter_text(obj)


def iter_stream_provider_content(
    *,
    prepared_call: PreparedProviderCall,
    state: ProviderStreamState,
    requests_module: Any,
    llm_module: Any,
    config_module: Any,
) -> Iterator[str]:
    with requests_module.post(
        prepared_call.url,
        json=prepared_call.payload,
        headers=prepared_call.headers,
        timeout=config_module.TIMEOUT_S,
        stream=True,
    ) as response:
        response.raise_for_status()
        state.response_open = True
        state.provider_metadata = llm_module.extract_openrouter_provider_metadata(
            {},
            requested_model=prepared_call.call_model,
        )
        response.encoding = response.encoding or 'utf-8'
        for line in response.iter_lines(decode_unicode=True, delimiter='\n'):
            if not line or not line.startswith('data:'):
                continue
            data_str = line[5:].strip()
            if data_str == '[DONE]':
                break
            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            state.provider_metadata = llm_module.merge_openrouter_provider_metadata(
                state.provider_metadata,
                chunk,
                requested_model=prepared_call.call_model,
            )
            delta = chunk.get('choices', [{}])[0].get('delta', {})
            content = delta.get('content')
            if content:
                yield llm_module.sanitize_provider_text(content)


def emit_provider_response_observability(
    *,
    prepared_call: PreparedProviderCall,
    state: ProviderStreamState,
    conversation: Mapping[str, Any],
    llm_module: Any,
    admin_logs_module: Any,
    logger: Any,
) -> None:
    if not state.response_open:
        return
    provider_fields = llm_module.build_provider_observability_fields(
        caller='llm',
        provider_metadata=state.provider_metadata,
    )
    llm_module.log_provider_metadata(logger, 'llm_provider_response', provider_fields)
    admin_logs_module.log_event(
        'llm_provider_response',
        conversation_id=conversation['id'],
        **provider_fields,
    )
