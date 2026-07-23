from __future__ import annotations

from collections.abc import Callable
import copy
import hashlib
import json
from types import SimpleNamespace
from typing import Any

from admin import runtime_settings
from core import assistant_turn_state
from core import chat_llm_flow
from core import chat_stream_control


class SyntheticRequestException(Exception):
    pass


def assert_single_done_terminal(
    raw_text: str | bytes | bytearray,
) -> tuple[str, dict[str, str]]:
    if isinstance(raw_text, (bytes, bytearray)):
        text = bytes(raw_text).decode('utf-8', errors='ignore')
    else:
        text = str(raw_text)
    if text.count(chat_stream_control.STREAM_CONTROL_PREFIX) != 1:
        raise AssertionError('stream must contain one terminal control frame')
    visible_text, terminal = chat_stream_control.split_text_and_terminal(text)
    if terminal is None or terminal.get('event') != chat_stream_control.STREAM_TERMINAL_DONE:
        raise AssertionError('stream must end with one done terminal')
    return visible_text, terminal


def exercise_chat_llm_surface(
    *,
    surface: str,
    fail_at: str | None = None,
    fail_failure_observability: bool = False,
    persistence: str = 'success',
    regime: str = 'answer',
    assistant_text: str | None = None,
) -> dict[str, object]:
    """Exercise the real LLM/persistence boundary with bounded synthetic fakes."""

    surface_flags = {
        'normal_non_stream': (False, False),
        'normal_stream': (False, True),
        'override_non_stream': (True, False),
        'override_stream': (True, True),
    }
    is_override, stream_req = surface_flags[surface]
    if regime not in {'answer', 'presence'}:
        raise ValueError('unsupported synthetic dialogic regime')
    if regime == 'presence' and not is_override:
        raise ValueError('presence requires the existing override boundary')

    user_text = 'Artificial user turn marker.'
    if assistant_text is None:
        assistant_text = '...' if regime == 'presence' else 'Artificial assistant turn marker.'
    assistant_meta = (
        assistant_turn_state.build_dialogic_presence_assistant_turn_meta()
        if regime == 'presence'
        else {
            'source': 'synthetic_final_lock' if is_override else 'synthetic_provider',
            'final_lock': is_override,
        }
    )
    timestamp = '2026-07-22T10:00:00Z'
    conversation = {
        'id': f'conv-{surface}-{regime}',
        'created_at': '2026-07-22T09:00:00Z',
        'messages': [{'role': 'user', 'content': user_text}],
    }
    observed: dict[str, object] = {
        'admin_events': [],
        'durable_snapshots': [],
        'failure_admin_log_calls': 0,
        'logger_error_calls': [],
        'post_calls': 0,
        'post_effect_sequence': [],
        'save_calls': 0,
        'secret_calls': 0,
        'url_calls': 0,
    }

    def dangerous_exception_message() -> str:
        marker = 'ARTIFICIAL_SECRET_SENTINEL'
        return (
            'https://example.invalid/private?'
            + 'to'
            + 'ken='
            + marker
            + ' Bea'
            + 'rer '
            + marker
            + ' /private/path/'
            + marker
            + ' provider '
            + 'payload '
            + 'raw'
        )

    def raise_synthetic_failure() -> None:
        raise RuntimeError(dangerous_exception_message())

    def fail_if(point: str) -> None:
        if fail_at == point:
            raise_synthetic_failure()

    def append_message(conv, role, content, timestamp=None, meta=None):
        message = {'role': role, 'content': content, 'timestamp': timestamp}
        if meta is not None:
            message['meta'] = dict(meta)
        conv['messages'].append(message)

    def save_conversation(conv, **kwargs):
        observed['save_calls'] += 1
        if persistence == 'raises':
            raise_synthetic_failure()
        if persistence == 'negative':
            return SimpleNamespace(
                ok=False,
                updated_at=kwargs.get('updated_at'),
                reason='messages_write_failed',
            )
        observed['durable_snapshots'].append(
            [dict(message) for message in conv.get('messages', [])]
        )
        return SimpleNamespace(
            ok=True,
            updated_at=kwargs.get('updated_at'),
            reason='',
        )

    def estimate_tokens(_messages, _model):
        observed['post_effect_sequence'].append('assistant_text_estimation')
        fail_if('assistant_text_estimation')
        return 7

    def save_new_traces(_conversation):
        observed['post_effect_sequence'].append('memory_traces')
        fail_if('memory_traces')

    def record_identity_entries(*_args, **_kwargs):
        observed['post_effect_sequence'].append('identity_entries')
        fail_if('identity_entries')

    def mode_enforces_identity(_mode):
        observed['post_effect_sequence'].append('identity_mode_decision')
        fail_if('identity_mode_decision')
        return True

    def reactivate_identities(_identity_ids):
        observed['post_effect_sequence'].append('identity_reactivation')
        fail_if('identity_reactivation')

    def log_event(event, **kwargs):
        observed['admin_events'].append((event, dict(kwargs)))
        if event == 'AssistantText':
            observed['post_effect_sequence'].append('assistant_text_log')
            fail_if('assistant_text_log')
        if event == 'chat_post_persistence_aux_error':
            observed['failure_admin_log_calls'] += 1
            if fail_failure_observability:
                raise_synthetic_failure()

    def logger_error(*args, **kwargs):
        observed['logger_error_calls'].append((args, dict(kwargs)))
        if fail_failure_observability:
            raise_synthetic_failure()

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {'choices': [{'message': {'content': assistant_text}}]}

    class FakeStreamResponse:
        encoding = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        def iter_lines(self, decode_unicode=True, delimiter='\n'):
            yield 'data: ' + json.dumps(
                {'choices': [{'delta': {'content': assistant_text}}]},
                ensure_ascii=False,
            )
            yield 'data: [DONE]'

    def requests_post(*_args, **kwargs):
        observed['post_calls'] += 1
        if is_override:
            raise AssertionError('provider call forbidden for override')
        return FakeStreamResponse() if kwargs.get('stream') else FakeResponse()

    def get_runtime_secret_value(*_args, **_kwargs):
        observed['secret_calls'] += 1
        if is_override:
            raise AssertionError('secret lookup forbidden for override')
        return SimpleNamespace(value='synthetic-key')

    def or_chat_completions_url():
        observed['url_calls'] += 1
        if is_override:
            raise AssertionError('URL resolution forbidden for override')
        return 'https://runtime-main.invalid/v1/chat/completions'

    runtime_settings_module = SimpleNamespace(
        get_runtime_secret_value=get_runtime_secret_value,
        RuntimeSettingsSecretRequiredError=KeyError,
        RuntimeSettingsSecretResolutionError=LookupError,
    )
    memory_store_module = SimpleNamespace(
        save_new_traces=save_new_traces,
        reactivate_identities=reactivate_identities,
    )
    conv_store_module = SimpleNamespace(
        append_message=append_message,
        save_conversation=save_conversation,
    )
    llm_module = SimpleNamespace(
        or_chat_completions_url=or_chat_completions_url,
        or_headers=lambda *, caller: {},
        resolve_provider_title=lambda caller='llm': f'FridaDev/{caller}',
        build_payload=lambda *_args, **_kwargs: {'model': 'synthetic-main-model'},
        read_openrouter_response_payload=lambda response: response.json(),
        extract_openrouter_provider_metadata=lambda _payload, *, requested_model=None: {
            'provider_model': requested_model,
        },
        build_provider_observability_fields=lambda *, caller, provider_metadata: {
            'provider_caller': caller,
            **dict(provider_metadata),
        },
        merge_openrouter_provider_metadata=lambda current, _payload, *, requested_model=None: {
            **dict(current or {}),
            'provider_model': requested_model,
        },
        log_provider_metadata=lambda *_args, **_kwargs: None,
        extract_openrouter_text=lambda payload: payload['choices'][0]['message']['content'],
        sanitize_provider_text=lambda text: text,
    )
    assistant_response_override = None
    if is_override:
        source = 'hermeneutic_validation_presence' if regime == 'presence' else 'synthetic_final_lock'
        reason_code = 'dialogic_presence' if regime == 'presence' else 'synthetic_final_lock_authorized'
        assistant_response_override = chat_llm_flow.AssistantResponseOverride(
            content=assistant_text,
            source=source,
            reason_code=reason_code,
            meta=assistant_meta,
            observability={'content_present': True, 'content_chars': len(assistant_text)},
        )

    result = None
    visible_text = None
    terminal = None
    stream_parts: list[str] = []
    raised_exception = None
    try:
        result = chat_llm_flow.run_llm_exchange(
            conversation=conversation,
            prompt_messages=[{'role': 'user', 'content': user_text}],
            runtime_main_model='synthetic-main-model',
            temperature=0.4,
            top_p=1.0,
            max_tokens=256,
            stream_req=stream_req,
            current_mode='enforced_all',
            identity_ids=['synthetic-identity-id'],
            web_input=None,
            runtime_settings_module=runtime_settings_module,
            memory_store_module=memory_store_module,
            conv_store_module=conv_store_module,
            llm_module=llm_module,
            requests_module=SimpleNamespace(
                post=requests_post,
                exceptions=SimpleNamespace(RequestException=SyntheticRequestException),
            ),
            token_utils_module=SimpleNamespace(estimate_tokens=estimate_tokens),
            admin_logs_module=SimpleNamespace(log_event=log_event),
            config_module=SimpleNamespace(OR_BASE='https://synthetic.invalid', TIMEOUT_S=42),
            logger=SimpleNamespace(
                info=lambda *_args, **_kwargs: None,
                error=logger_error,
            ),
            arbiter_module=SimpleNamespace(),
            now_iso_func=lambda: timestamp,
            record_identity_entries_for_mode=record_identity_entries,
            mode_enforces_identity=mode_enforces_identity,
            conversation_headers_func=lambda _conversation, updated_at: {
                'X-Conversation-Id': conversation['id'],
                'X-Conversation-Updated-At': updated_at,
            },
            conversation_stream_headers_func=lambda _conversation: {
                'X-Conversation-Id': conversation['id'],
                'X-Conversation-Created-At': conversation['created_at'],
            },
            assistant_response_override=assistant_response_override,
            assistant_response_meta=assistant_meta,
        )
        if stream_req:
            for part in result['stream']:
                if isinstance(part, (bytes, bytearray)):
                    stream_parts.append(bytes(part).decode('utf-8', errors='ignore'))
                else:
                    stream_parts.append(str(part or ''))
            visible_text, terminal = chat_stream_control.split_text_and_terminal(
                ''.join(stream_parts).encode('utf-8')
            )
    except Exception as exc:
        raised_exception = exc

    return {
        'assistant_meta': assistant_meta,
        'assistant_text': assistant_text,
        'conversation': conversation,
        'is_override': is_override,
        'observed': observed,
        'raised_exception': raised_exception,
        'regime': regime,
        'result': result,
        'stream_parts': stream_parts,
        'stream_req': stream_req,
        'terminal': terminal,
        'timestamp': timestamp,
        'user_text': user_text,
        'visible_text': visible_text,
    }


def patch_server_chat_pipeline(
    server_module,
    *,
    conversation: dict[str, Any],
    requests_post,
    build_prompt_messages: Callable[..., list[dict[str, Any]]] | None = None,
    build_payload: Callable[..., dict[str, Any]] | None = None,
    save_conversation_result: Any | Callable[..., Any] = None,
    conversation_path: str = 'conv/conv-test-chat.json',
    runtime_api_key: str = 'sk-test-chat',
    runtime_model: str = 'openrouter/runtime-main-model',
    existing_conversation: bool = False,
    summarize_user_turn: bool = False,
    hermeneutic_mode: str | None = None,
    disable_chat_log_storage: bool = False,
):
    """Patch the shared baseline /api/chat seam and return observations plus restore."""

    originals = []
    observed = {
        'save_calls': [],
        'save_new_traces_calls': [],
        'node_state_reads': [],
        'node_state_writes': [],
    }
    node_state_store: dict[str, dict[str, Any]] = {}
    observed['node_state_store'] = node_state_store

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
                'model': {'value': runtime_model, 'origin': 'db'},
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
    patch_attr(
        server_module.runtime_settings,
        'get_agenda_agent_settings',
        lambda: runtime_settings.RuntimeSectionView(
            section='agenda_agent',
            payload={
                'mode': {'value': 'off', 'origin': 'db_seed'},
                'caldav_account': {'value': 'tof', 'origin': 'db_seed'},
                'caldav_app_password': {'is_secret': True, 'is_set': False, 'origin': 'missing'},
            },
            source='db',
            source_reason='test_default_off',
        ),
    )
    if existing_conversation:
        def unexpected_new_conversation(_system):
            raise AssertionError('existing synthetic conversation must be loaded')

        patch_attr(
            server_module.conv_store,
            'normalize_conversation_id',
            lambda _raw: conversation['id'],
        )
        patch_attr(
            server_module.conv_store,
            'load_conversation',
            lambda *_args, **_kwargs: conversation,
        )
        patch_attr(
            server_module.conv_store,
            'new_conversation',
            unexpected_new_conversation,
        )
    else:
        patch_attr(server_module.conv_store, 'normalize_conversation_id', lambda _raw: None)
        patch_attr(server_module.conv_store, 'load_conversation', lambda *_args, **_kwargs: None)
        patch_attr(server_module.conv_store, 'new_conversation', lambda _system: conversation)

    def fake_save_conversation(*_args, **kwargs):
        conversation_snapshot = None
        if _args and isinstance(_args[0], dict):
            conversation_snapshot = [
                dict(message)
                for message in _args[0].get('messages', [])
            ]
        observed['save_calls'].append(
            {
                'kwargs': dict(kwargs),
                'messages': conversation_snapshot,
            }
        )
        if callable(save_conversation_result):
            return save_conversation_result(*_args, **kwargs)
        return save_conversation_result

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
    patch_attr(
        server_module.summarizer,
        'maybe_summarize',
        lambda *args, **kwargs: summarize_user_turn,
    )
    if hermeneutic_mode is not None:
        patch_attr(server_module.config, 'HERMENEUTIC_MODE', hermeneutic_mode)
    if disable_chat_log_storage:
        patch_attr(
            server_module.chat_turn_logger.log_store,
            'insert_chat_log_event',
            lambda *_args, **_kwargs: {'inserted': True},
        )
        patch_attr(
            server_module,
            '_finish_chat_turn_and_refresh_dashboard',
            lambda *_args, **_kwargs: None,
        )
        patch_attr(
            server_module.chat_service,
            '_resolve_summary_input',
            lambda **_kwargs: {},
        )
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
    patch_attr(
        server_module.memory_store,
        'retrieve_for_arbiter_with_status',
        lambda *_args, **_kwargs: {
            'traces': [],
            'ok': True,
            'status': 'ok',
            'reason_code': 'no_data',
            'error_code': None,
            'error_class': None,
            'top_k_requested': None,
        },
    )
    patch_attr(server_module.memory_store, 'get_recent_context_hints', lambda **_kwargs: [])

    def _state_hash(payload: dict[str, Any] | None) -> str:
        if not payload:
            return ''
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()[:12]

    def fake_read_node_state(conversation_id: str):
        state = copy.deepcopy(node_state_store.get(str(conversation_id or '')))
        result = {
            'state': state,
            'present': bool(state),
            'valid': True,
            'reason_code': 'ok' if state else 'not_found',
            'schema_version': str(state.get('schema_version') or '') if state else '',
            'state_sha256_12': _state_hash(state),
        }
        observed['node_state_reads'].append(dict(result, state=None))
        return result

    def fake_write_node_state(conversation_id: str, state: dict[str, Any] | None):
        conv_id = str(conversation_id or '')
        if not state:
            result = {
                'attempted': True,
                'written': False,
                'changed': False,
                'reason_code': 'invalid_node_state',
                'schema_version': '',
                'state_sha256_12': '',
            }
            observed['node_state_writes'].append(dict(result, state=None))
            return result
        next_state = copy.deepcopy(dict(state or {}))
        old_state = copy.deepcopy(node_state_store.get(conv_id))
        node_state_store[conv_id] = next_state
        changed = old_state != next_state
        result = {
            'attempted': True,
            'written': True,
            'changed': changed,
            'reason_code': 'written' if changed else 'unchanged',
            'schema_version': str(next_state.get('schema_version') or ''),
            'state_sha256_12': _state_hash(next_state),
        }
        observed['node_state_writes'].append(dict(result, state=copy.deepcopy(next_state)))
        return result

    patch_attr(server_module.memory_store, 'read_hermeneutic_node_state', fake_read_node_state)
    patch_attr(server_module.memory_store, 'write_hermeneutic_node_state', fake_write_node_state)
    patch_attr(server_module.admin_logs, 'log_event', lambda *args, **kwargs: None)
    patch_attr(server_module.llm, 'or_headers', lambda **_kwargs: {})

    def fake_build_payload(_messages, _temperature, _top_p, max_tokens, stream=False):
        observed['payload_messages'] = [dict(message) for message in _messages]
        return {
            'model': runtime_model,
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


def exercise_chat_route_surface(server_module, *, stream_req: bool) -> dict[str, object]:
    """Exercise the real Flask/chat-service seam with a synthetic provider response."""

    conversation = {
        'id': f'conv-lot9-route-{"stream" if stream_req else "json"}',
        'created_at': '2026-07-23T09:00:00Z',
        'messages': [],
    }
    assistant_text = 'Artificial assistant route marker.'
    provider_calls = []

    class FakeResponse:
        encoding = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        def json(self):
            return {'choices': [{'message': {'content': assistant_text}}]}

        def iter_lines(self, decode_unicode=True, delimiter='\n'):
            yield 'data: ' + json.dumps(
                {'choices': [{'delta': {'content': assistant_text}}]},
                ensure_ascii=False,
            )
            yield 'data: [DONE]'

    def requests_post(*args, **kwargs):
        payload = kwargs.get('json') if isinstance(kwargs.get('json'), dict) else {}
        provider_calls.append(
            {
                'model': str(payload.get('model') or ''),
                'stream': bool(kwargs.get('stream')),
            }
        )
        return FakeResponse()

    observed, restore = patch_server_chat_pipeline(
        server_module,
        conversation=conversation,
        requests_post=requests_post,
        save_conversation_result=lambda _conversation, **kwargs: SimpleNamespace(
            ok=True,
            updated_at=kwargs.get('updated_at'),
            reason='',
        ),
        existing_conversation=True,
        summarize_user_turn=True,
        hermeneutic_mode='off',
        disable_chat_log_storage=True,
    )
    try:
        response = server_module.app.test_client().post(
            '/api/chat',
            json={
                'message': 'Artificial user route marker.',
                'stream': stream_req,
                'conversation_id': conversation['id'],
            },
        )
        response_bytes = response.get_data()
    finally:
        restore()

    visible_text = None
    terminal = None
    if stream_req:
        visible_text, terminal = assert_single_done_terminal(response_bytes)
    return {
        'assistant_text': assistant_text,
        'conversation': conversation,
        'observed': observed,
        'provider_calls': provider_calls,
        'response': response,
        'response_bytes': response_bytes,
        'stream_req': stream_req,
        'terminal': terminal,
        'visible_text': visible_text,
    }
