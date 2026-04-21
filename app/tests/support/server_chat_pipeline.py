from __future__ import annotations

from collections.abc import Callable
from typing import Any

from admin import runtime_settings


def patch_server_chat_pipeline(
    server_module,
    *,
    conversation: dict[str, Any],
    requests_post,
    build_prompt_messages: Callable[..., list[dict[str, Any]]] | None = None,
    build_payload: Callable[..., dict[str, Any]] | None = None,
    conversation_path: str = 'conv/conv-test-chat.json',
    runtime_api_key: str = 'sk-test-chat',
):
    """Patch the shared baseline /api/chat seam and return observations plus restore."""

    originals = []
    observed = {'save_calls': [], 'save_new_traces_calls': []}

    def patch_attr(obj, name, value):
        originals.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    patch_attr(server_module.prompt_loader, 'get_main_system_prompt', lambda: 'BACKEND SYSTEM PROMPT')
    patch_attr(
        server_module.prompt_loader,
        'get_main_hermeneutical_prompt',
        lambda: 'BACKEND HERMENEUTICAL PROMPT',
    )
    patch_attr(
        server_module.runtime_settings,
        'get_main_model_settings',
        lambda: runtime_settings.RuntimeSectionView(
            section='main_model',
            payload={
                'model': {'value': 'openrouter/runtime-main-model', 'origin': 'db'},
                'temperature': {'value': 0.4, 'origin': 'db'},
                'top_p': {'value': 1.0, 'origin': 'db'},
                'response_max_tokens': {'value': 2048, 'origin': 'db_seed'},
                'api_key': {'is_secret': True, 'is_set': True, 'origin': 'db'},
            },
            source='db',
            source_reason='db_row',
        ),
    )
    patch_attr(
        server_module.runtime_settings,
        'get_runtime_secret_value',
        lambda *args, **kwargs: runtime_settings.RuntimeSecretValue(
            section='main_model',
            field='api_key',
            value=runtime_api_key,
            source='db_encrypted',
            source_reason='db_row',
        ),
    )
    patch_attr(server_module.conv_store, 'normalize_conversation_id', lambda _raw: None)
    patch_attr(server_module.conv_store, 'load_conversation', lambda *_args, **_kwargs: None)
    patch_attr(server_module.conv_store, 'new_conversation', lambda _system: conversation)

    def fake_save_conversation(*_args, **kwargs):
        observed['save_calls'].append({'kwargs': dict(kwargs)})

    patch_attr(server_module.conv_store, 'save_conversation', fake_save_conversation)
    patch_attr(
        server_module.conv_store,
        'append_message',
        lambda conv, role, content, timestamp=None, meta=None, **_kwargs: conv['messages'].append(
            {'role': role, 'content': content, 'timestamp': timestamp, 'meta': meta}
        ),
    )
    patch_attr(server_module.conv_store, 'conversation_path', lambda _id: conversation_path)

    if build_prompt_messages is None:
        prompt_message_builder = lambda *_args, **_kwargs: [{'role': 'user', 'content': 'Bonjour'}]
    else:
        prompt_message_builder = build_prompt_messages

    patch_attr(server_module.conv_store, 'build_prompt_messages', prompt_message_builder)
    patch_attr(server_module.memory_store, 'decay_identities', lambda: None)
    patch_attr(server_module.summarizer, 'maybe_summarize', lambda *args, **kwargs: False)
    patch_attr(server_module.identity, 'build_identity_block', lambda: ('', []))
    patch_attr(
        server_module.identity,
        'build_identity_input',
        lambda: {
            'schema_version': 'v2',
            'frida': {
                'static': {'content': '', 'source': None},
                'mutable': {
                    'content': '',
                    'source_trace_id': None,
                    'updated_by': None,
                    'update_reason': None,
                    'updated_ts': None,
                },
            },
            'user': {
                'static': {'content': '', 'source': None},
                'mutable': {
                    'content': '',
                    'source_trace_id': None,
                    'updated_by': None,
                    'update_reason': None,
                    'updated_ts': None,
                },
            },
        },
    )
    patch_attr(server_module.memory_store, 'retrieve', lambda *_args, **_kwargs: [])
    patch_attr(server_module.memory_store, 'get_recent_context_hints', lambda **_kwargs: [])
    patch_attr(server_module.admin_logs, 'log_event', lambda *args, **kwargs: None)
    patch_attr(server_module.llm, 'or_headers', lambda **_kwargs: {})

    def fake_build_payload(_messages, _temperature, _top_p, max_tokens, stream=False):
        observed['payload_messages'] = [dict(message) for message in _messages]
        return {
            'model': 'openrouter/runtime-main-model',
            'messages': list(_messages),
            'max_tokens': max_tokens,
            'stream': stream,
        }

    if build_payload is None:
        payload_builder = fake_build_payload
    else:
        def payload_builder(_messages, _temperature, _top_p, max_tokens, stream=False):
            observed['payload_messages'] = [dict(message) for message in _messages]
            return build_payload(_messages, _temperature, _top_p, max_tokens, stream=stream)

    patch_attr(server_module.llm, 'build_payload', payload_builder)
    patch_attr(server_module.requests, 'post', requests_post)
    patch_attr(server_module.token_utils, 'count_tokens', lambda *_args, **_kwargs: 1)
    patch_attr(
        server_module.memory_store,
        'save_new_traces',
        lambda conv, *_args, **_kwargs: observed['save_new_traces_calls'].append(
            [dict(message) for message in conv.get('messages', [])]
        ),
    )
    patch_attr(server_module.chat_service, '_record_identity_entries_for_mode', lambda *_args, **_kwargs: None)
    patch_attr(server_module.memory_store, 'reactivate_identities', lambda *_args, **_kwargs: None)
    patch_attr(
        server_module.chat_service.stimmung_agent,
        'build_affective_turn_signal',
        lambda **_kwargs: server_module.chat_service.stimmung_agent.StimmungAgentResult(
            signal={
                'schema_version': 'v1',
                'present': True,
                'tones': [{'tone': 'neutralite', 'strength': 3}],
                'dominant_tone': 'neutralite',
                'confidence': 0.55,
            },
            status='ok',
            model='openai/gpt-5.4-mini',
            decision_source='primary',
            reason_code=None,
        ),
    )

    def restore():
        while originals:
            obj, name, value = originals.pop()
            setattr(obj, name, value)

    return observed, restore
