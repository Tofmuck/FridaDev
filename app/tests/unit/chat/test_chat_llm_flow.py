from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import assistant_output_contract
from core import chat_stream_control
from core import chat_llm_flow


class _RequestException(Exception):
    pass


_DANGEROUS_SENTINEL = "ARTIFICIAL_SECRET_SENTINEL"


def _dangerous_exception_message() -> str:
    return (
        "https://example.invalid/private?"
        + "to"
        + "ken="
        + _DANGEROUS_SENTINEL
        + " Bea"
        + "rer "
        + _DANGEROUS_SENTINEL
        + " /private/path/"
        + _DANGEROUS_SENTINEL
        + " provider "
        + "payload "
        + "raw"
    )


def _assert_content_free(testcase: unittest.TestCase, *values) -> None:
    blob = json.dumps(values, ensure_ascii=False, sort_keys=True, default=str)
    for marker in (
        _DANGEROUS_SENTINEL,
        "example.invalid",
        "Bearer",
        "/private/path/",
        "provider " + "payload " + "raw",
    ):
        testcase.assertNotIn(marker, blob)


def _event_payloads(events, event_name: str):
    return [payload for event, payload in events if event == event_name]


def _collect_stream_output(stream) -> tuple[str, dict[str, str] | None]:
    parts: list[bytes] = []
    for part in stream:
        if isinstance(part, (bytes, bytearray)):
            parts.append(bytes(part))
        else:
            parts.append(str(part).encode('utf-8'))
    return chat_stream_control.split_text_and_terminal(b''.join(parts))


def _collect_stream_parts(stream) -> list[str]:
    parts: list[str] = []
    for part in stream:
        if isinstance(part, (bytes, bytearray)):
            parts.append(bytes(part).decode('utf-8', errors='ignore'))
        else:
            parts.append(str(part or ''))
    return parts


def _synthetic_chat_completions_url() -> str:
    return 'https://runtime-main.invalid/v1/chat/completions'


class ChatLlmFlowTests(unittest.TestCase):
    def _exercise_post_persistence_surface(
        self,
        *,
        surface: str,
        fail_at: str | None = None,
        fail_failure_observability: bool = False,
        persistence: str = 'success',
        assistant_text: str = 'Artificial assistant turn marker.',
    ) -> dict[str, object]:
        surface_flags = {
            'normal_non_stream': (False, False),
            'normal_stream': (False, True),
            'override_non_stream': (True, False),
            'override_stream': (True, True),
        }
        is_override, stream_req = surface_flags[surface]
        user_text = 'Artificial user turn marker.'
        assistant_meta = {
            'source': 'synthetic_final_lock' if is_override else 'synthetic_provider',
            'final_lock': is_override,
        }
        timestamp = '2026-07-22T10:00:00Z'
        conversation = {
            'id': f'conv-{surface}',
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

        def raise_synthetic_failure() -> None:
            raise RuntimeError(_dangerous_exception_message())

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
            assistant_response_override = chat_llm_flow.AssistantResponseOverride(
                content=assistant_text,
                source='synthetic_final_lock',
                reason_code='synthetic_final_lock_authorized',
                meta=assistant_meta,
                observability={'content_present': True, 'content_chars': len(assistant_text)},
            )

        result = None
        visible_text = None
        terminal = None
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
                    exceptions=SimpleNamespace(RequestException=_RequestException),
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
                visible_text, terminal = _collect_stream_output(result['stream'])
        except Exception as exc:
            raised_exception = exc

        return {
            'assistant_meta': assistant_meta,
            'assistant_text': assistant_text,
            'conversation': conversation,
            'is_override': is_override,
            'observed': observed,
            'raised_exception': raised_exception,
            'result': result,
            'stream_req': stream_req,
            'terminal': terminal,
            'timestamp': timestamp,
            'user_text': user_text,
            'visible_text': visible_text,
        }

    def _expected_post_persistence_sequence(
        self,
        *,
        surface: str,
        fail_at: str | None,
    ) -> list[str]:
        assistant_effect = ['assistant_text_estimation']
        if fail_at != 'assistant_text_estimation':
            assistant_effect.append('assistant_text_log')
        identity_effects = ['identity_entries', 'identity_mode_decision']
        if fail_at != 'identity_mode_decision':
            identity_effects.append('identity_reactivation')
        if surface == 'normal_stream':
            return assistant_effect + identity_effects + ['memory_traces']
        return assistant_effect + ['memory_traces'] + identity_effects

    def test_post_persistence_auxiliary_failure_matrix_preserves_success_on_all_surfaces(self) -> None:
        effect_to_observed_name = {
            'assistant_text_estimation': 'assistant_text_observability',
            'assistant_text_log': 'assistant_text_observability',
            'memory_traces': 'memory_traces',
            'identity_entries': 'identity_entries',
            'identity_mode_decision': 'identity_reactivation',
            'identity_reactivation': 'identity_reactivation',
        }
        surfaces = (
            'normal_non_stream',
            'normal_stream',
            'override_non_stream',
            'override_stream',
        )
        for surface in surfaces:
            for fail_at, observed_effect_name in effect_to_observed_name.items():
                with self.subTest(surface=surface, fail_at=fail_at):
                    case = self._exercise_post_persistence_surface(
                        surface=surface,
                        fail_at=fail_at,
                    )
                    observed = case['observed']
                    result = case['result']
                    conversation = case['conversation']

                    self.assertIsNone(case['raised_exception'])
                    self.assertEqual(observed['save_calls'], 1)
                    self.assertEqual(len(observed['durable_snapshots']), 1)
                    self.assertEqual(
                        observed['post_effect_sequence'],
                        self._expected_post_persistence_sequence(
                            surface=surface,
                            fail_at=fail_at,
                        ),
                    )
                    assistant_messages = [
                        message
                        for message in conversation['messages']
                        if message.get('role') == 'assistant'
                    ]
                    self.assertEqual(len(assistant_messages), 1)
                    self.assertEqual(assistant_messages[0]['content'], case['assistant_text'])
                    self.assertEqual(assistant_messages[0]['meta'], case['assistant_meta'])
                    self.assertEqual(
                        observed['durable_snapshots'][0][-1],
                        assistant_messages[0],
                    )
                    if case['stream_req']:
                        self.assertEqual(case['visible_text'], case['assistant_text'])
                        self.assertEqual(
                            case['terminal'],
                            {'event': 'done', 'updated_at': case['timestamp']},
                        )
                        self.assertEqual(
                            result['headers'],
                            {
                                'X-Conversation-Id': conversation['id'],
                                'X-Conversation-Created-At': conversation['created_at'],
                            },
                        )
                    else:
                        self.assertEqual(result['kind'], 'json')
                        self.assertEqual(result['status'], 200)
                        self.assertTrue(result['payload']['ok'])
                        self.assertEqual(result['payload']['text'], case['assistant_text'])
                        self.assertEqual(
                            result['headers'],
                            {
                                'X-Conversation-Id': conversation['id'],
                                'X-Conversation-Updated-At': case['timestamp'],
                            },
                        )
                    self.assertEqual(observed['post_calls'], 0 if case['is_override'] else 1)
                    self.assertEqual(observed['secret_calls'], 0 if case['is_override'] else 1)
                    self.assertEqual(observed['url_calls'], 0 if case['is_override'] else 1)

                    failure_events = _event_payloads(
                        observed['admin_events'],
                        'chat_post_persistence_aux_error',
                    )
                    self.assertEqual(len(failure_events), 1)
                    self.assertEqual(failure_events[0]['effect_name'], observed_effect_name)
                    self.assertEqual(
                        failure_events[0]['reason_code'],
                        'chat_post_persistence_aux_error',
                    )
                    self.assertEqual(failure_events[0]['error_class'], 'RuntimeError')
                    self.assertEqual(len(observed['logger_error_calls']), 1)
                    failure_observability = (
                        failure_events,
                        observed['logger_error_calls'],
                    )
                    _assert_content_free(self, failure_observability)
                    failure_blob = json.dumps(failure_observability, default=str)
                    self.assertNotIn(case['assistant_text'], failure_blob)
                    self.assertNotIn(case['user_text'], failure_blob)

    def test_post_persistence_failure_observability_is_never_raises_on_all_surfaces(self) -> None:
        for surface in (
            'normal_non_stream',
            'normal_stream',
            'override_non_stream',
            'override_stream',
        ):
            with self.subTest(surface=surface):
                case = self._exercise_post_persistence_surface(
                    surface=surface,
                    fail_at='memory_traces',
                    fail_failure_observability=True,
                )
                observed = case['observed']

                self.assertIsNone(case['raised_exception'])
                self.assertEqual(observed['save_calls'], 1)
                self.assertEqual(observed['failure_admin_log_calls'], 1)
                self.assertEqual(len(observed['logger_error_calls']), 1)
                if case['stream_req']:
                    self.assertEqual(case['terminal']['event'], 'done')
                else:
                    self.assertEqual(case['result']['status'], 200)

    def test_primary_persistence_negative_result_stays_fail_closed_on_all_surfaces(self) -> None:
        for surface in (
            'normal_non_stream',
            'normal_stream',
            'override_non_stream',
            'override_stream',
        ):
            with self.subTest(surface=surface):
                case = self._exercise_post_persistence_surface(
                    surface=surface,
                    persistence='negative',
                )
                observed = case['observed']

                self.assertIsNone(case['raised_exception'])
                self.assertEqual(observed['save_calls'], 1)
                self.assertEqual(observed['post_effect_sequence'], [])
                self.assertEqual(observed['durable_snapshots'], [])
                if case['stream_req']:
                    self.assertEqual(
                        case['terminal'],
                        {
                            'event': 'error',
                            'error_code': 'conversation_persist_failed',
                        },
                    )
                else:
                    self.assertEqual(case['result']['status'], 503)
                    self.assertFalse(case['result']['payload']['ok'])

    def test_primary_persistence_exception_stays_fail_closed_on_all_surfaces(self) -> None:
        for surface in (
            'normal_non_stream',
            'normal_stream',
            'override_non_stream',
            'override_stream',
        ):
            with self.subTest(surface=surface):
                case = self._exercise_post_persistence_surface(
                    surface=surface,
                    persistence='raises',
                )
                observed = case['observed']

                self.assertEqual(observed['post_effect_sequence'], [])
                self.assertEqual(observed['durable_snapshots'], [])
                if surface == 'normal_stream':
                    self.assertIsNone(case['raised_exception'])
                    self.assertEqual(
                        case['terminal'],
                        {
                            'event': 'error',
                            'error_code': 'conversation_persist_failed',
                        },
                    )
                    self.assertEqual(observed['save_calls'], 2)
                else:
                    self.assertIsInstance(case['raised_exception'], RuntimeError)
                    expected_save_calls = 2 if surface == 'normal_non_stream' else 1
                    self.assertEqual(observed['save_calls'], expected_save_calls)

    def test_run_llm_exchange_sync_success_keeps_json_contract(self) -> None:
        events = []
        observed = {
            'headers_called_with': None,
            'payload_stream_flag': None,
            'request_stream_flag': None,
            'identity_callback_called': False,
            'save_calls': [],
            'secret_calls': 0,
            'provider_log_calls': [],
            'post_calls': 0,
            'sanitize_calls': [],
            'sequence': [],
            'url_helper_calls': 0,
        }
        conversation = {
            'id': 'conv-sync',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    'id': 'gen-sync',
                    'model': 'openrouter/runtime-main-model',
                    'usage': {'prompt_tokens': 12, 'completion_tokens': 5, 'total_tokens': 17},
                    'choices': [{'message': {'content': 'reponse test'}}],
                }

        def fake_post(url, *, json, headers, timeout):
            observed['post_calls'] += 1
            observed['request_url'] = url
            observed['request_stream_flag'] = None
            observed['request_payload'] = dict(json)
            observed['request_headers'] = dict(headers)
            observed['request_timeout'] = timeout
            return FakeResponse()

        def fake_or_chat_completions_url():
            observed['url_helper_calls'] += 1
            return 'https://runtime-main.invalid/v1/chat/completions'

        def fake_build_payload(_messages, _temperature, _top_p, _max_tokens, *, stream=False):
            observed['payload_stream_flag'] = stream
            return {'model': 'openrouter/runtime-main-model'}

        def fake_get_runtime_secret_value(_section, _field):
            observed['secret_calls'] += 1
            return SimpleNamespace(value='sk-test')

        runtime_settings_module = SimpleNamespace(
            get_runtime_secret_value=fake_get_runtime_secret_value,
            RuntimeSettingsSecretRequiredError=RuntimeError,
            RuntimeSettingsSecretResolutionError=ValueError,
        )

        def fake_save_new_traces(_conversation):
            observed['sequence'].append('save_new_traces')

        def fake_reactivate_identities(_identity_ids):
            observed['sequence'].append('reactivate_identities')

        def fake_save_conversation(_conversation, **kwargs):
            observed['sequence'].append('save_conversation')
            observed['save_calls'].append(dict(kwargs))

        memory_store_module = SimpleNamespace(
            save_new_traces=fake_save_new_traces,
            reactivate_identities=fake_reactivate_identities,
        )
        conv_store_module = SimpleNamespace(
            append_message=lambda conv, role, content, timestamp=None, meta=None: conv['messages'].append(
                {'role': role, 'content': content, 'timestamp': timestamp, **({'meta': meta} if meta is not None else {})}
            ),
            save_conversation=fake_save_conversation,
        )
        llm_module = SimpleNamespace(
            or_chat_completions_url=fake_or_chat_completions_url,
            or_headers=lambda *, caller: observed.update({'headers_called_with': caller}) or {'Authorization': 'Bearer token'},
            resolve_provider_title=lambda caller='llm': f'FridaDev/{caller}',
            build_payload=fake_build_payload,
            read_openrouter_response_payload=lambda response: response.json(),
            extract_openrouter_provider_metadata=lambda payload, *, requested_model=None: {
                'provider_generation_id': payload.get('id'),
                'provider_model': payload.get('model') or requested_model,
                'provider_prompt_tokens': (payload.get('usage') or {}).get('prompt_tokens'),
                'provider_completion_tokens': (payload.get('usage') or {}).get('completion_tokens'),
                'provider_total_tokens': (payload.get('usage') or {}).get('total_tokens'),
            },
            build_provider_observability_fields=lambda *, caller, provider_metadata: {
                'provider_caller': caller,
                'provider_title': f'FridaDev/{caller}',
                **dict(provider_metadata),
            },
            merge_openrouter_provider_metadata=lambda current, payload, *, requested_model=None: dict(current or {}, **{
                key: value
                for key, value in {
                    'provider_generation_id': payload.get('id'),
                    'provider_model': payload.get('model') or requested_model,
                    'provider_prompt_tokens': (payload.get('usage') or {}).get('prompt_tokens'),
                    'provider_completion_tokens': (payload.get('usage') or {}).get('completion_tokens'),
                    'provider_total_tokens': (payload.get('usage') or {}).get('total_tokens'),
                }.items()
                if value is not None
            }),
            log_provider_metadata=lambda _logger, event, provider_metadata: observed['provider_log_calls'].append((event, dict(provider_metadata))),
            extract_openrouter_text=lambda payload: payload['choices'][0]['message']['content'],
            sanitize_provider_text=lambda text: observed['sanitize_calls'].append(text) or text,
            main_llm_reasoning_observability_from_payload=lambda _payload: {
                'main_llm_reasoning_effort_requested': 'high',
                'main_llm_reasoning_effort_effective': 'high',
                'main_llm_reasoning_hidden': True,
            },
        )
        requests_module = SimpleNamespace(
            post=fake_post,
            exceptions=SimpleNamespace(RequestException=_RequestException),
        )
        token_utils_module = SimpleNamespace(estimate_tokens=lambda _messages, _model: 7)

        def fake_log_event(event, **kwargs):
            if event == 'AssistantText':
                observed['sequence'].append('AssistantText')
            events.append((event, kwargs))

        admin_logs_module = SimpleNamespace(log_event=fake_log_event)
        config_module = SimpleNamespace(OR_BASE='https://legacy-env.invalid/v1', TIMEOUT_S=42)
        logger = SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None)

        result = chat_llm_flow.run_llm_exchange(
            conversation=conversation,
            prompt_messages=[{'role': 'user', 'content': 'bonjour'}],
            runtime_main_model='openrouter/runtime-main-model',
            temperature=0.4,
            top_p=1.0,
            max_tokens=256,
            stream_req=False,
            current_mode='enforced_all',
            identity_ids=['identity-1'],
            web_input=None,
            runtime_settings_module=runtime_settings_module,
            memory_store_module=memory_store_module,
            conv_store_module=conv_store_module,
            llm_module=llm_module,
            requests_module=requests_module,
            token_utils_module=token_utils_module,
            admin_logs_module=admin_logs_module,
            config_module=config_module,
            logger=logger,
            arbiter_module=SimpleNamespace(),
            now_iso_func=lambda: '2026-03-26T00:10:00Z',
            record_identity_entries_for_mode=lambda *_args, **_kwargs: (
                observed['sequence'].append('identity_write'),
                observed.update({'identity_callback_called': True}),
            ),
            mode_enforces_identity=lambda _mode: True,
            conversation_headers_func=lambda _conversation, updated_at: {
                'X-Conversation-Id': 'conv-sync',
                'X-Conversation-Created-At': '2026-03-26T00:00:00Z',
                'X-Conversation-Updated-At': updated_at,
            },
            assistant_response_meta={
                'source': 'biblio_read_passages_response',
                'biblio_render_mode': 'read_passages_llm_response',
            },
            assistant_response_intro='Intro agentique',
            assistant_response_outro='Relance agentique',
        )

        self.assertEqual(result['kind'], 'json')
        self.assertEqual(result['status'], 200)
        self.assertEqual(
            result['payload'],
            {
                'ok': True,
                'text': 'Intro agentique\n\nreponse test\n\nRelance agentique',
                'conversation_id': 'conv-sync',
                'created_at': '2026-03-26T00:00:00Z',
                'updated_at': '2026-03-26T00:10:00Z',
            },
        )
        self.assertEqual(result['headers']['X-Conversation-Id'], 'conv-sync')
        self.assertEqual(observed['headers_called_with'], 'llm')
        self.assertEqual(observed['request_url'], 'https://runtime-main.invalid/v1/chat/completions')
        self.assertNotIn('legacy-env.invalid', observed['request_url'])
        self.assertEqual(observed['url_helper_calls'], 1)
        self.assertEqual(observed['post_calls'], 1)
        self.assertEqual(observed['request_payload'], {'model': 'openrouter/runtime-main-model'})
        self.assertEqual(observed['request_headers'], {'Authorization': 'Bearer token'})
        self.assertEqual(observed['request_timeout'], 42)
        self.assertFalse(observed['payload_stream_flag'])
        self.assertEqual(observed['secret_calls'], 1)
        self.assertEqual(observed['sanitize_calls'], [])
        self.assertTrue(observed['identity_callback_called'])
        self.assertEqual(observed['save_calls'][-1]['updated_at'], '2026-03-26T00:10:00Z')
        self.assertEqual(
            conversation['messages'][-1]['meta'],
            {
                'source': 'biblio_read_passages_response',
                'biblio_render_mode': 'read_passages_llm_response',
            },
        )
        self.assertEqual(
            conversation['messages'][-1]['content'],
            'Intro agentique\n\nreponse test\n\nRelance agentique',
        )
        self.assertEqual(
            observed['sequence'],
            ['save_conversation', 'AssistantText', 'save_new_traces', 'identity_write', 'reactivate_identities'],
        )
        self.assertEqual(_event_payloads(events, 'llm_payload')[0]['model'], 'openrouter/runtime-main-model')
        self.assertEqual(_event_payloads(events, 'llm_payload')[0]['provider_caller'], 'llm')
        self.assertEqual(_event_payloads(events, 'llm_payload')[0]['provider_title'], 'FridaDev/llm')
        self.assertEqual(_event_payloads(events, 'llm_payload')[0]['main_llm_reasoning_effort_effective'], 'high')
        self.assertTrue(_event_payloads(events, 'llm_payload')[0]['main_llm_reasoning_hidden'])
        self.assertFalse(_event_payloads(events, 'llm_call')[0]['stream'])
        self.assertEqual(_event_payloads(events, 'llm_call')[0]['main_llm_reasoning_effort_requested'], 'high')
        self.assertEqual(
            _event_payloads(events, 'llm_provider_response'),
            [
                {
                    'conversation_id': 'conv-sync',
                    'provider_caller': 'llm',
                    'provider_title': 'FridaDev/llm',
                    'provider_generation_id': 'gen-sync',
                    'provider_model': 'openrouter/runtime-main-model',
                    'provider_prompt_tokens': 12,
                    'provider_completion_tokens': 5,
                    'provider_total_tokens': 17,
                }
            ],
        )

        self.assertEqual(
            _event_payloads(events, 'AssistantText'),
            [
                {
                    'conversation_id': 'conv-sync',
                    'estimated_assistant_tokens': 7,
                    'message_timestamp': '2026-03-26T00:10:00Z',
                }
            ],
        )
        self.assertEqual(
            observed['provider_log_calls'],
            [
                (
                    'llm_provider_response',
                    {
                        'provider_caller': 'llm',
                        'provider_title': 'FridaDev/llm',
                        'provider_generation_id': 'gen-sync',
                        'provider_model': 'openrouter/runtime-main-model',
                        'provider_prompt_tokens': 12,
                        'provider_completion_tokens': 5,
                        'provider_total_tokens': 17,
                    },
                )
            ],
        )

    def test_presence_override_is_exact_single_save_success_with_normal_dialogue_derivations(self) -> None:
        for surface in ('override_non_stream', 'override_stream'):
            with self.subTest(surface=surface):
                exercised = self._exercise_post_persistence_surface(
                    surface=surface,
                    assistant_text='...',
                )
                observed = exercised['observed']
                result = exercised['result']

                self.assertIsNone(exercised['raised_exception'])
                self.assertEqual(observed['post_calls'], 0)
                self.assertEqual(observed['secret_calls'], 0)
                self.assertEqual(observed['url_calls'], 0)
                self.assertEqual(observed['save_calls'], 1)
                self.assertIn('memory_traces', observed['post_effect_sequence'])
                self.assertIn('identity_entries', observed['post_effect_sequence'])
                self.assertEqual(
                    observed['post_effect_sequence'],
                    self._expected_post_persistence_sequence(
                        surface=surface,
                        fail_at=None,
                    ),
                )
                self.assertEqual(
                    [message['role'] for message in exercised['conversation']['messages']],
                    ['user', 'assistant'],
                )
                self.assertEqual(exercised['conversation']['messages'][-1]['content'], '...')
                self.assertEqual(
                    exercised['conversation']['messages'][-1]['timestamp'],
                    exercised['timestamp'],
                )
                self.assertEqual(
                    observed['durable_snapshots'][-1][-1]['content'],
                    '...',
                )
                if exercised['stream_req']:
                    self.assertEqual(exercised['visible_text'], '...')
                    self.assertEqual(
                        exercised['terminal'],
                        {'event': 'done', 'updated_at': exercised['timestamp']},
                    )
                else:
                    self.assertEqual(result['kind'], 'json')
                    self.assertEqual(result['status'], 200)
                    self.assertEqual(result['payload']['ok'], True)
                    self.assertEqual(result['payload']['text'], '...')
                    self.assertEqual(result['payload']['updated_at'], exercised['timestamp'])

    def test_run_llm_exchange_sync_override_bypasses_llm_and_persists_final_message(self) -> None:
        events = []
        observed = {
            'secret_calls': 0,
            'post_calls': 0,
            'url_calls': 0,
            'save_new_traces_calls': [],
            'identity_callback_called': False,
            'reactivate_called': False,
            'save_calls': [],
        }
        raw_biblio_text = 'RAW BIBLIO EXACT TEXT IS USER-VISIBLE FINAL CONTENT'
        final_text = (
            'Source: document du catalogue, page 12.\n\n'
            f'{raw_biblio_text}\n'
        )
        conversation = {
            'id': 'conv-override',
            'created_at': '2026-06-04T00:00:00Z',
            'messages': [{'role': 'user', 'content': 'biblio'}],
        }

        def forbidden_secret(*_args, **_kwargs):
            observed['secret_calls'] += 1
            raise AssertionError('LLM secret must not be read for an authorized override')

        def forbidden_post(*_args, **_kwargs):
            observed['post_calls'] += 1
            raise AssertionError('LLM must not be called for an authorized override')

        def forbidden_url_resolution():
            observed['url_calls'] += 1
            raise AssertionError('LLM URL must not be resolved for an authorized override')

        def fake_save_new_traces(saved_conversation):
            observed['save_new_traces_calls'].append([dict(message) for message in saved_conversation['messages']])

        def fake_save_conversation(_conversation, **kwargs):
            observed['save_calls'].append(dict(kwargs))

        result = chat_llm_flow.run_llm_exchange(
            conversation=conversation,
            prompt_messages=[{'role': 'user', 'content': 'biblio'}],
            runtime_main_model='openrouter/runtime-main-model',
            temperature=0.4,
            top_p=1.0,
            max_tokens=256,
            stream_req=False,
            current_mode='enforced_all',
            identity_ids=['id-a'],
            web_input=None,
            runtime_settings_module=SimpleNamespace(
                get_runtime_secret_value=forbidden_secret,
                RuntimeSettingsSecretRequiredError=RuntimeError,
                RuntimeSettingsSecretResolutionError=ValueError,
            ),
            memory_store_module=SimpleNamespace(
                save_new_traces=fake_save_new_traces,
                reactivate_identities=lambda _identity_ids: observed.update({'reactivate_called': True}),
            ),
            conv_store_module=SimpleNamespace(
                append_message=lambda conv, role, content, timestamp=None, meta=None: conv['messages'].append(
                    {
                        'role': role,
                        'content': content,
                        'timestamp': timestamp,
                        **({'meta': meta} if meta is not None else {}),
                    }
                ),
                save_conversation=fake_save_conversation,
            ),
            llm_module=SimpleNamespace(or_chat_completions_url=forbidden_url_resolution),
            requests_module=SimpleNamespace(
                post=forbidden_post,
                exceptions=SimpleNamespace(RequestException=_RequestException),
            ),
            token_utils_module=SimpleNamespace(estimate_tokens=lambda _messages, _model: 13),
            admin_logs_module=SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs))),
            config_module=SimpleNamespace(OR_BASE='https://openrouter.example', TIMEOUT_S=42),
            logger=SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None),
            arbiter_module=SimpleNamespace(),
            now_iso_func=lambda: '2026-06-04T00:10:00Z',
            record_identity_entries_for_mode=lambda *_args, **_kwargs: observed.update(
                {'identity_callback_called': True}
            ),
            mode_enforces_identity=lambda _mode: True,
            conversation_headers_func=lambda _conversation, updated_at: {'X-Conversation-Updated-At': updated_at},
            assistant_response_override=chat_llm_flow.AssistantResponseOverride(
                content=final_text,
                source='biblio_rendered_answer',
                reason_code='biblio_final_response_authorized',
                meta={
                    'source': 'biblio_rendered_answer',
                    'biblio_answer_status': 'ready',
                    'biblio_render_mode': 'exact_excerpt',
                },
                observability={
                    'status': 'authorized',
                    'content_hash': '0123456789ab',
                    'exact_text_chars': len(raw_biblio_text),
                    'exact_text_hash': 'abcdef123456',
                    'semantic_judgment': False,
                },
            ),
        )

        self.assertEqual(result['kind'], 'json')
        self.assertEqual(result['status'], 200)
        self.assertEqual(result['payload']['text'], final_text)
        self.assertEqual(conversation['messages'][-1]['role'], 'assistant')
        self.assertEqual(conversation['messages'][-1]['content'], final_text)
        self.assertEqual(conversation['messages'][-1]['meta']['source'], 'biblio_rendered_answer')
        self.assertEqual(observed['secret_calls'], 0)
        self.assertEqual(observed['post_calls'], 0)
        self.assertEqual(observed['url_calls'], 0)
        self.assertTrue(observed['identity_callback_called'])
        self.assertTrue(observed['reactivate_called'])
        self.assertEqual(observed['save_new_traces_calls'][-1][-1]['content'], final_text)
        event_dump = str(events)
        self.assertIn('assistant_response_override', event_dump)
        self.assertNotIn(raw_biblio_text, event_dump)
        self.assertEqual(_event_payloads(events, 'llm_payload'), [])
        self.assertEqual(_event_payloads(events, 'llm_call'), [])
        self.assertEqual(_event_payloads(events, 'AssistantText')[0]['estimated_assistant_tokens'], 13)

    def test_run_llm_exchange_stream_override_persists_biblio_content_for_memory(self) -> None:
        events = []
        observed = {
            'secret_calls': 0,
            'post_calls': 0,
            'url_calls': 0,
            'save_new_traces_calls': [],
            'identity_callback_called': False,
            'reactivate_called': False,
            'save_calls': [],
        }
        raw_biblio_text = 'RAW BIBLIO STREAM TEXT IS USER-VISIBLE FINAL CONTENT'
        final_text = (
            'Source: document du catalogue, page 12.\n\n'
            f'{raw_biblio_text}\n'
        )
        conversation = {
            'id': 'conv-stream-override',
            'created_at': '2026-06-04T00:00:00Z',
            'messages': [{'role': 'user', 'content': 'biblio stream'}],
        }

        def forbidden_secret(*_args, **_kwargs):
            observed['secret_calls'] += 1
            raise AssertionError('LLM secret must not be read for a streaming override')

        def forbidden_post(*_args, **_kwargs):
            observed['post_calls'] += 1
            raise AssertionError('LLM must not be called for a streaming override')

        def forbidden_url_resolution():
            observed['url_calls'] += 1
            raise AssertionError('LLM URL must not be resolved for a streaming override')

        def fake_save_new_traces(saved_conversation):
            observed['save_new_traces_calls'].append([dict(message) for message in saved_conversation['messages']])

        def fake_save_conversation(_conversation, **kwargs):
            observed['save_calls'].append(dict(kwargs))

        result = chat_llm_flow.run_llm_exchange(
            conversation=conversation,
            prompt_messages=[{'role': 'user', 'content': 'biblio stream'}],
            runtime_main_model='openrouter/runtime-main-model',
            temperature=0.4,
            top_p=1.0,
            max_tokens=256,
            stream_req=True,
            current_mode='enforced_all',
            identity_ids=['id-stream'],
            web_input=None,
            runtime_settings_module=SimpleNamespace(
                get_runtime_secret_value=forbidden_secret,
                RuntimeSettingsSecretRequiredError=RuntimeError,
                RuntimeSettingsSecretResolutionError=ValueError,
            ),
            memory_store_module=SimpleNamespace(
                save_new_traces=fake_save_new_traces,
                reactivate_identities=lambda _identity_ids: observed.update({'reactivate_called': True}),
            ),
            conv_store_module=SimpleNamespace(
                append_message=lambda conv, role, content, timestamp=None, meta=None: conv['messages'].append(
                    {
                        'role': role,
                        'content': content,
                        'timestamp': timestamp,
                        **({'meta': meta} if meta is not None else {}),
                    }
                ),
                save_conversation=fake_save_conversation,
            ),
            llm_module=SimpleNamespace(or_chat_completions_url=forbidden_url_resolution),
            requests_module=SimpleNamespace(
                post=forbidden_post,
                exceptions=SimpleNamespace(RequestException=_RequestException),
            ),
            token_utils_module=SimpleNamespace(estimate_tokens=lambda _messages, _model: 21),
            admin_logs_module=SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs))),
            config_module=SimpleNamespace(OR_BASE='https://openrouter.example', TIMEOUT_S=42),
            logger=SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None),
            arbiter_module=SimpleNamespace(),
            now_iso_func=lambda: '2026-06-04T00:12:00Z',
            record_identity_entries_for_mode=lambda *_args, **_kwargs: observed.update(
                {'identity_callback_called': True}
            ),
            mode_enforces_identity=lambda _mode: True,
            conversation_headers_func=lambda _conversation, updated_at: {'X-Conversation-Updated-At': updated_at},
            conversation_stream_headers_func=lambda _conversation: {'X-Conversation-Id': 'conv-stream-override'},
            assistant_response_override=chat_llm_flow.AssistantResponseOverride(
                content=final_text,
                source='biblio_rendered_answer',
                reason_code='biblio_final_response_authorized',
                meta={
                    'source': 'biblio_rendered_answer',
                    'biblio_answer_status': 'ready',
                    'biblio_render_mode': 'exact_excerpt',
                    'biblio_exact_text_rendered': True,
                    'biblio_exact_text_chars': len(raw_biblio_text),
                    'biblio_exact_text_hash': 'fedcba654321',
                },
                observability={
                    'status': 'authorized',
                    'content_hash': '0123456789ab',
                    'exact_text_chars': len(raw_biblio_text),
                    'exact_text_hash': 'fedcba654321',
                    'semantic_judgment': False,
                },
            ),
        )

        self.assertEqual(result['kind'], 'stream')
        self.assertEqual(result['headers'], {'X-Conversation-Id': 'conv-stream-override'})
        streamed, terminal = _collect_stream_output(result['stream'])
        self.assertEqual(streamed, final_text)
        self.assertEqual(terminal, {'event': 'done', 'updated_at': '2026-06-04T00:12:00Z'})
        self.assertEqual(conversation['messages'][-1]['role'], 'assistant')
        self.assertEqual(conversation['messages'][-1]['content'], final_text)
        self.assertEqual(conversation['messages'][-1]['meta']['source'], 'biblio_rendered_answer')
        self.assertEqual(conversation['messages'][-1]['meta']['biblio_answer_status'], 'ready')
        self.assertEqual(conversation['messages'][-1]['meta']['biblio_render_mode'], 'exact_excerpt')
        self.assertTrue(conversation['messages'][-1]['meta']['biblio_exact_text_rendered'])
        self.assertEqual(conversation['messages'][-1]['meta']['biblio_exact_text_hash'], 'fedcba654321')
        self.assertEqual(observed['secret_calls'], 0)
        self.assertEqual(observed['post_calls'], 0)
        self.assertEqual(observed['url_calls'], 0)
        self.assertEqual(observed['save_calls'][-1]['updated_at'], '2026-06-04T00:12:00Z')
        self.assertEqual(observed['save_new_traces_calls'][-1][-1]['content'], final_text)
        self.assertEqual(
            observed['save_new_traces_calls'][-1][-1]['meta']['source'],
            'biblio_rendered_answer',
        )
        self.assertTrue(observed['identity_callback_called'])
        self.assertTrue(observed['reactivate_called'])
        event_dump = str(events)
        self.assertIn('assistant_response_override', event_dump)
        self.assertIn('semantic_judgment', event_dump)
        self.assertNotIn(raw_biblio_text, event_dump)
        self.assertEqual(_event_payloads(events, 'llm_payload'), [])
        self.assertEqual(_event_payloads(events, 'llm_call'), [])
        self.assertEqual(_event_payloads(events, 'AssistantText')[0]['estimated_assistant_tokens'], 21)

    def test_run_llm_exchange_sync_persistence_failure_blocks_derived_writes(self) -> None:
        events = []
        observed = {
            'sequence': [],
            'trace_calls': 0,
            'identity_calls': 0,
            'reactivate_calls': 0,
        }
        conversation = {
            'id': 'conv-sync-persist-fail',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'reponse non persistable'}}]}

        runtime_settings_module = SimpleNamespace(
            get_runtime_secret_value=lambda *_args, **_kwargs: SimpleNamespace(value='sk-test'),
            RuntimeSettingsSecretRequiredError=RuntimeError,
            RuntimeSettingsSecretResolutionError=ValueError,
        )

        def fake_save_conversation(_conversation, **kwargs):
            observed['sequence'].append(('save_conversation', dict(kwargs)))
            return SimpleNamespace(
                ok=False,
                catalog_saved=True,
                messages_saved=False,
                updated_at=kwargs.get('updated_at'),
                message_count=len(_conversation.get('messages', [])),
                reason='messages_write_failed',
            )

        memory_store_module = SimpleNamespace(
            save_new_traces=lambda _conversation: observed.update({'trace_calls': observed['trace_calls'] + 1}),
            reactivate_identities=lambda _identity_ids: observed.update({'reactivate_calls': observed['reactivate_calls'] + 1}),
        )
        conv_store_module = SimpleNamespace(
            append_message=lambda conv, role, content, timestamp=None, meta=None: conv['messages'].append(
                {'role': role, 'content': content, 'timestamp': timestamp, **({'meta': meta} if meta is not None else {})}
            ),
            save_conversation=fake_save_conversation,
        )
        llm_module = SimpleNamespace(
            or_chat_completions_url=_synthetic_chat_completions_url,
            or_headers=lambda *, caller: {'Authorization': 'Bearer token'},
            resolve_provider_title=lambda caller='llm': f'FridaDev/{caller}',
            build_payload=lambda *_args, **_kwargs: {'model': 'openrouter/runtime-main-model'},
            read_openrouter_response_payload=lambda response: response.json(),
            extract_openrouter_provider_metadata=lambda payload, *, requested_model=None: {
                'provider_model': requested_model,
            },
            build_provider_observability_fields=lambda *, caller, provider_metadata: {
                'provider_caller': caller,
                'provider_title': f'FridaDev/{caller}',
                **dict(provider_metadata),
            },
            merge_openrouter_provider_metadata=lambda current, payload, *, requested_model=None: dict(current or {}),
            log_provider_metadata=lambda *_args, **_kwargs: None,
            extract_openrouter_text=lambda payload: payload['choices'][0]['message']['content'],
            sanitize_provider_text=lambda text: text,
        )

        result = chat_llm_flow.run_llm_exchange(
            conversation=conversation,
            prompt_messages=[{'role': 'user', 'content': 'bonjour'}],
            runtime_main_model='openrouter/runtime-main-model',
            temperature=0.4,
            top_p=1.0,
            max_tokens=256,
            stream_req=False,
            current_mode='enforced_all',
            identity_ids=['id-a'],
            web_input=None,
            runtime_settings_module=runtime_settings_module,
            memory_store_module=memory_store_module,
            conv_store_module=conv_store_module,
            llm_module=llm_module,
            requests_module=SimpleNamespace(
                post=lambda *_args, **_kwargs: FakeResponse(),
                exceptions=SimpleNamespace(RequestException=_RequestException),
            ),
            token_utils_module=SimpleNamespace(estimate_tokens=lambda *_args, **_kwargs: 3),
            admin_logs_module=SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs))),
            config_module=SimpleNamespace(OR_BASE='https://openrouter.example', TIMEOUT_S=42),
            logger=SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None),
            arbiter_module=SimpleNamespace(),
            now_iso_func=lambda: '2026-03-26T00:10:00Z',
            record_identity_entries_for_mode=lambda *_args, **_kwargs: observed.update(
                {'identity_calls': observed['identity_calls'] + 1}
            ),
            mode_enforces_identity=lambda _mode: True,
            conversation_headers_func=lambda _conversation, updated_at: {'X-Conversation-Updated-At': updated_at},
        )

        self.assertEqual(result['kind'], 'json')
        self.assertEqual(result['status'], 503)
        self.assertEqual(
            result['payload'],
            {
                'ok': False,
                'error': 'sauvegarde conversationnelle impossible',
                'reason': 'messages_write_failed',
            },
        )
        self.assertEqual([name for name, _kwargs in observed['sequence']], ['save_conversation'])
        self.assertEqual(observed['trace_calls'], 0)
        self.assertEqual(observed['identity_calls'], 0)
        self.assertEqual(observed['reactivate_calls'], 0)

    def test_run_llm_exchange_stream_success_keeps_stream_contract(self) -> None:
        events = []
        observed = {
            'request_stream_flag': None,
            'save_calls': [],
            'identity_callback_called': False,
            'reactivate_called': False,
            'provider_log_calls': [],
            'post_calls': 0,
            'stream_completed': False,
            'now_iso_flags': [],
            'sanitize_calls': [],
            'url_helper_calls': 0,
        }
        conversation = {
            'id': 'conv-stream',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }

        class FakeStreamResponse:
            encoding = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True, delimiter='\n'):
                yield 'data: {"id":"gen-stream","model":"openrouter/runtime-main-model","choices":[{"delta":{"content":"Bon"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"jour"}}]}'
                yield 'data: {"usage":{"prompt_tokens":40,"completion_tokens":2,"total_tokens":42},"choices":[{"delta":{}}]}'
                observed['stream_completed'] = True
                yield 'data: [DONE]'

        def fake_post(url, *, json, headers, timeout, stream=False):
            observed['post_calls'] += 1
            observed['request_url'] = url
            observed['request_stream_flag'] = stream
            observed['request_payload'] = dict(json)
            observed['request_headers'] = dict(headers)
            observed['request_timeout'] = timeout
            return FakeStreamResponse()

        def fake_or_chat_completions_url():
            observed['url_helper_calls'] += 1
            return 'https://runtime-main.invalid/v1/chat/completions'

        runtime_settings_module = SimpleNamespace(
            get_runtime_secret_value=lambda *_args, **_kwargs: SimpleNamespace(value='sk-test'),
            RuntimeSettingsSecretRequiredError=RuntimeError,
            RuntimeSettingsSecretResolutionError=ValueError,
        )
        memory_store_module = SimpleNamespace(
            save_new_traces=lambda _conversation: None,
            reactivate_identities=lambda _identity_ids: observed.update({'reactivate_called': True}),
        )
        conv_store_module = SimpleNamespace(
            append_message=lambda conv, role, content, timestamp=None, meta=None: conv['messages'].append(
                {'role': role, 'content': content, 'timestamp': timestamp, **({'meta': meta} if meta is not None else {})}
            ),
            save_conversation=lambda _conversation, **kwargs: observed['save_calls'].append(dict(kwargs)),
        )
        llm_module = SimpleNamespace(
            or_chat_completions_url=fake_or_chat_completions_url,
            or_headers=lambda *, caller: {'Authorization': 'Bearer token'},
            resolve_provider_title=lambda caller='llm': f'FridaDev/{caller}',
            build_payload=lambda *_args, **_kwargs: {'model': 'openrouter/runtime-main-model'},
            read_openrouter_response_payload=lambda response: response.json(),
            extract_openrouter_provider_metadata=lambda payload, *, requested_model=None: {
                'provider_generation_id': payload.get('id'),
                'provider_model': payload.get('model') or requested_model,
                'provider_prompt_tokens': (payload.get('usage') or {}).get('prompt_tokens'),
                'provider_completion_tokens': (payload.get('usage') or {}).get('completion_tokens'),
                'provider_total_tokens': (payload.get('usage') or {}).get('total_tokens'),
            },
            build_provider_observability_fields=lambda *, caller, provider_metadata: {
                'provider_caller': caller,
                'provider_title': f'FridaDev/{caller}',
                **dict(provider_metadata),
            },
            merge_openrouter_provider_metadata=lambda current, payload, *, requested_model=None: dict(current or {}, **{
                key: value
                for key, value in {
                    'provider_generation_id': payload.get('id'),
                    'provider_model': payload.get('model') or requested_model,
                    'provider_prompt_tokens': (payload.get('usage') or {}).get('prompt_tokens'),
                    'provider_completion_tokens': (payload.get('usage') or {}).get('completion_tokens'),
                    'provider_total_tokens': (payload.get('usage') or {}).get('total_tokens'),
                }.items()
                if value is not None
            }),
            log_provider_metadata=lambda _logger, event, provider_metadata: observed['provider_log_calls'].append((event, dict(provider_metadata))),
            extract_openrouter_text=lambda payload: payload['choices'][0]['message']['content'],
            sanitize_provider_text=lambda text: observed['sanitize_calls'].append(text) or text,
        )
        requests_module = SimpleNamespace(
            post=fake_post,
            exceptions=SimpleNamespace(RequestException=_RequestException),
        )
        token_utils_module = SimpleNamespace(estimate_tokens=lambda _messages, _model: 3)
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))
        config_module = SimpleNamespace(OR_BASE='https://legacy-env.invalid/v1', TIMEOUT_S=42)
        logger = SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None)

        def fake_now_iso():
            observed['now_iso_flags'].append(observed['stream_completed'])
            return '2026-03-26T00:11:59Z'

        result = chat_llm_flow.run_llm_exchange(
            conversation=conversation,
            prompt_messages=[{'role': 'user', 'content': 'bonjour'}],
            runtime_main_model='openrouter/runtime-main-model',
            temperature=0.4,
            top_p=1.0,
            max_tokens=256,
            stream_req=True,
            current_mode='enforced_all',
            identity_ids=['id-a'],
            web_input=None,
            runtime_settings_module=runtime_settings_module,
            memory_store_module=memory_store_module,
            conv_store_module=conv_store_module,
            llm_module=llm_module,
            requests_module=requests_module,
            token_utils_module=token_utils_module,
            admin_logs_module=admin_logs_module,
            config_module=config_module,
            logger=logger,
            arbiter_module=SimpleNamespace(),
            now_iso_func=fake_now_iso,
            record_identity_entries_for_mode=lambda *_args, **_kwargs: observed.update({'identity_callback_called': True}),
            mode_enforces_identity=lambda mode: mode == 'enforced_all',
            conversation_headers_func=lambda _conversation, updated_at: {
                'X-Conversation-Id': 'conv-stream',
                'X-Conversation-Created-At': '2026-03-26T00:00:00Z',
                'X-Conversation-Updated-At': updated_at,
            },
            conversation_stream_headers_func=lambda _conversation: {
                'X-Conversation-Id': 'conv-stream',
                'X-Conversation-Created-At': '2026-03-26T00:00:00Z',
            },
            assistant_response_meta={
                'source': 'biblio_read_passages_response',
                'biblio_render_mode': 'read_passages_llm_response',
            },
            assistant_response_intro='Intro stream',
            assistant_response_outro='Outro stream',
        )

        self.assertEqual(result['kind'], 'stream')
        self.assertEqual(result['headers']['X-Conversation-Id'], 'conv-stream')
        self.assertEqual(result['headers']['X-Conversation-Created-At'], '2026-03-26T00:00:00Z')
        self.assertNotIn('X-Conversation-Updated-At', result['headers'])
        self.assertTrue(_event_payloads(events, 'llm_call')[0]['stream'])
        self.assertEqual(_event_payloads(events, 'llm_call')[0]['provider_caller'], 'llm')
        self.assertEqual(_event_payloads(events, 'llm_call')[0]['provider_title'], 'FridaDev/llm')

        streamed, terminal = _collect_stream_output(result['stream'])
        self.assertEqual(streamed, '')
        self.assertEqual(
            terminal,
            {
                'event': 'done',
                'updated_at': '2026-03-26T00:11:59Z',
                'final_text': 'Intro stream\n\nBonjour\n\nOutro stream',
            },
        )
        self.assertTrue(observed['request_stream_flag'])
        self.assertEqual(observed['request_url'], 'https://runtime-main.invalid/v1/chat/completions')
        self.assertNotIn('legacy-env.invalid', observed['request_url'])
        self.assertEqual(observed['url_helper_calls'], 1)
        self.assertEqual(observed['post_calls'], 1)
        self.assertEqual(observed['request_payload'], {'model': 'openrouter/runtime-main-model'})
        self.assertEqual(observed['request_headers'], {'Authorization': 'Bearer token'})
        self.assertEqual(observed['request_timeout'], 42)
        self.assertEqual(conversation['messages'][-1]['role'], 'assistant')
        self.assertEqual(conversation['messages'][-1]['content'], 'Intro stream\n\nBonjour\n\nOutro stream')
        self.assertEqual(conversation['messages'][-1]['timestamp'], '2026-03-26T00:11:59Z')
        self.assertEqual(
            conversation['messages'][-1]['meta'],
            {
                'source': 'biblio_read_passages_response',
                'biblio_render_mode': 'read_passages_llm_response',
            },
        )
        self.assertEqual(observed['save_calls'][-1]['updated_at'], '2026-03-26T00:11:59Z')
        self.assertEqual(observed['now_iso_flags'], [True])
        self.assertEqual(observed['sanitize_calls'], ['Bon', 'jour', 'Bonjour'])
        self.assertTrue(observed['identity_callback_called'])
        self.assertTrue(observed['reactivate_called'])
        self.assertEqual(
            _event_payloads(events, 'llm_provider_response'),
            [
                {
                    'conversation_id': 'conv-stream',
                    'provider_caller': 'llm',
                    'provider_title': 'FridaDev/llm',
                    'provider_generation_id': 'gen-stream',
                    'provider_model': 'openrouter/runtime-main-model',
                    'provider_prompt_tokens': 40,
                    'provider_completion_tokens': 2,
                    'provider_total_tokens': 42,
                }
            ],
        )
        self.assertEqual(
            _event_payloads(events, 'AssistantText'),
            [
                {
                    'conversation_id': 'conv-stream',
                    'estimated_assistant_tokens': 3,
                    'message_timestamp': '2026-03-26T00:11:59Z',
                }
            ],
        )
        self.assertEqual(
            observed['provider_log_calls'],
            [
                (
                    'llm_provider_response',
                    {
                        'provider_caller': 'llm',
                        'provider_title': 'FridaDev/llm',
                        'provider_generation_id': 'gen-stream',
                        'provider_model': 'openrouter/runtime-main-model',
                        'provider_prompt_tokens': 40,
                        'provider_completion_tokens': 2,
                        'provider_total_tokens': 42,
                    },
                )
            ],
        )

    def test_run_llm_exchange_stream_buffers_and_keeps_simple_lists_for_ordinary_turn_output(self) -> None:
        conversation = {
            'id': 'conv-stream-plain-text',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }

        class FakeStreamResponse:
            encoding = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True, delimiter='\n'):
                yield 'data: {"choices":[{"delta":{"content":"JSON est un format.\\n\\n"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"- Lisible.\\n"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"1) Portable."}}]}'
                yield 'data: {"choices":[{"delta":{"content":" **Bo"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"ld**"}}]}'
                yield 'data: [DONE]'

        def fake_post(_url, *, json, headers, timeout, stream=False):
            return FakeStreamResponse()

        runtime_settings_module = SimpleNamespace(
            get_runtime_secret_value=lambda *_args, **_kwargs: SimpleNamespace(value='sk-test'),
            RuntimeSettingsSecretRequiredError=RuntimeError,
            RuntimeSettingsSecretResolutionError=ValueError,
        )
        memory_store_module = SimpleNamespace(
            save_new_traces=lambda _conversation: None,
            reactivate_identities=lambda _identity_ids: None,
        )
        conv_store_module = SimpleNamespace(
            append_message=lambda conv, role, content, timestamp=None: conv['messages'].append(
                {'role': role, 'content': content, 'timestamp': timestamp}
            ),
            save_conversation=lambda *_args, **_kwargs: None,
        )
        llm_module = SimpleNamespace(
            or_chat_completions_url=_synthetic_chat_completions_url,
            or_headers=lambda *, caller: {'Authorization': 'Bearer token'},
            resolve_provider_title=lambda caller='llm': f'FridaDev/{caller}',
            build_payload=lambda *_args, **_kwargs: {'model': 'openrouter/runtime-main-model'},
            extract_openrouter_provider_metadata=lambda payload, *, requested_model=None: {
                'provider_generation_id': payload.get('id'),
                'provider_model': payload.get('model') or requested_model,
                'provider_prompt_tokens': (payload.get('usage') or {}).get('prompt_tokens'),
                'provider_completion_tokens': (payload.get('usage') or {}).get('completion_tokens'),
                'provider_total_tokens': (payload.get('usage') or {}).get('total_tokens'),
            },
            build_provider_observability_fields=lambda *, caller, provider_metadata: {
                'provider_caller': caller,
                'provider_title': f'FridaDev/{caller}',
                **dict(provider_metadata),
            },
            merge_openrouter_provider_metadata=lambda current, payload, *, requested_model=None: dict(current or {}, **{
                key: value
                for key, value in {
                    'provider_generation_id': payload.get('id'),
                    'provider_model': payload.get('model') or requested_model,
                    'provider_prompt_tokens': (payload.get('usage') or {}).get('prompt_tokens'),
                    'provider_completion_tokens': (payload.get('usage') or {}).get('completion_tokens'),
                    'provider_total_tokens': (payload.get('usage') or {}).get('total_tokens'),
                }.items()
                if value is not None
            }),
            log_provider_metadata=lambda *_args, **_kwargs: None,
            extract_openrouter_text=lambda payload: payload['choices'][0]['message']['content'],
            sanitize_provider_text=lambda text: text,
        )
        requests_module = SimpleNamespace(
            post=fake_post,
            exceptions=SimpleNamespace(RequestException=_RequestException),
        )
        result = chat_llm_flow.run_llm_exchange(
            conversation=conversation,
            prompt_messages=[{'role': 'user', 'content': 'bonjour'}],
            runtime_main_model='openrouter/runtime-main-model',
            temperature=0.4,
            top_p=1.0,
            max_tokens=256,
            stream_req=True,
            current_mode='shadow',
            identity_ids=[],
            web_input=None,
            assistant_output_policy=assistant_output_contract.AssistantOutputPolicy(),
            runtime_settings_module=runtime_settings_module,
            memory_store_module=memory_store_module,
            conv_store_module=conv_store_module,
            llm_module=llm_module,
            requests_module=requests_module,
            token_utils_module=SimpleNamespace(estimate_tokens=lambda *_args, **_kwargs: 3),
            admin_logs_module=SimpleNamespace(log_event=lambda *_args, **_kwargs: None),
            config_module=SimpleNamespace(OR_BASE='https://openrouter.example', TIMEOUT_S=42),
            logger=SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None),
            arbiter_module=SimpleNamespace(),
            now_iso_func=lambda: '2026-03-26T00:11:00Z',
            record_identity_entries_for_mode=lambda *_args, **_kwargs: None,
            mode_enforces_identity=lambda _mode: False,
            conversation_headers_func=lambda _conversation, updated_at: {'X-Conversation-Updated-At': updated_at},
        )

        parts = _collect_stream_parts(result['stream'])
        streamed, terminal = chat_stream_control.split_text_and_terminal(''.join(parts))
        visible_parts = [part for part in parts if not part.startswith(chat_stream_control.STREAM_CONTROL_PREFIX)]
        self.assertGreaterEqual(len(visible_parts), 2)
        self.assertEqual(visible_parts[0], 'JSON est un format.')
        self.assertIn('\n- Lisible.', streamed)
        self.assertIn('\n1) Portable.', streamed)
        self.assertIn('Lisible.', streamed)
        self.assertIn('Portable.', streamed)
        self.assertIn('**Bo', streamed)
        self.assertEqual(
            terminal,
            {
                'event': 'done',
                'updated_at': '2026-03-26T00:11:00Z',
                'final_text': 'JSON est un format.\n\n- Lisible.\n1) Portable. Bold',
            },
        )
        self.assertEqual(conversation['messages'][-1]['content'], terminal['final_text'])

    def test_run_llm_exchange_stream_preserves_structure_for_explicit_plan_requests(self) -> None:
        conversation = {
            'id': 'conv-stream-structured',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }

        class FakeStreamResponse:
            encoding = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True, delimiter='\n'):
                yield 'data: {"choices":[{"delta":{"content":"1) Comprendre\\n"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"2) Structurer"}}]}'
                yield 'data: [DONE]'

        def fake_post(_url, *, json, headers, timeout, stream=False):
            return FakeStreamResponse()

        runtime_settings_module = SimpleNamespace(
            get_runtime_secret_value=lambda *_args, **_kwargs: SimpleNamespace(value='sk-test'),
            RuntimeSettingsSecretRequiredError=RuntimeError,
            RuntimeSettingsSecretResolutionError=ValueError,
        )
        memory_store_module = SimpleNamespace(
            save_new_traces=lambda _conversation: None,
            reactivate_identities=lambda _identity_ids: None,
        )
        conv_store_module = SimpleNamespace(
            append_message=lambda conv, role, content, timestamp=None: conv['messages'].append(
                {'role': role, 'content': content, 'timestamp': timestamp}
            ),
            save_conversation=lambda *_args, **_kwargs: None,
        )
        llm_module = SimpleNamespace(
            or_chat_completions_url=_synthetic_chat_completions_url,
            or_headers=lambda *, caller: {'Authorization': 'Bearer token'},
            resolve_provider_title=lambda caller='llm': f'FridaDev/{caller}',
            build_payload=lambda *_args, **_kwargs: {'model': 'openrouter/runtime-main-model'},
            extract_openrouter_provider_metadata=lambda payload, *, requested_model=None: {},
            build_provider_observability_fields=lambda *, caller, provider_metadata: {},
            merge_openrouter_provider_metadata=lambda current, payload, *, requested_model=None: dict(current or {}),
            log_provider_metadata=lambda *_args, **_kwargs: None,
            extract_openrouter_text=lambda payload: payload['choices'][0]['message']['content'],
            sanitize_provider_text=lambda text: text,
        )
        requests_module = SimpleNamespace(
            post=fake_post,
            exceptions=SimpleNamespace(RequestException=_RequestException),
        )
        result = chat_llm_flow.run_llm_exchange(
            conversation=conversation,
            prompt_messages=[{'role': 'user', 'content': 'bonjour'}],
            runtime_main_model='openrouter/runtime-main-model',
            temperature=0.4,
            top_p=1.0,
            max_tokens=256,
            stream_req=True,
            current_mode='shadow',
            identity_ids=[],
            web_input=None,
            assistant_output_policy=assistant_output_contract.AssistantOutputPolicy(allow_structure=True),
            runtime_settings_module=runtime_settings_module,
            memory_store_module=memory_store_module,
            conv_store_module=conv_store_module,
            llm_module=llm_module,
            requests_module=requests_module,
            token_utils_module=SimpleNamespace(estimate_tokens=lambda *_args, **_kwargs: 3),
            admin_logs_module=SimpleNamespace(log_event=lambda *_args, **_kwargs: None),
            config_module=SimpleNamespace(OR_BASE='https://openrouter.example', TIMEOUT_S=42),
            logger=SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None),
            arbiter_module=SimpleNamespace(),
            now_iso_func=lambda: '2026-03-26T00:11:00Z',
            record_identity_entries_for_mode=lambda *_args, **_kwargs: None,
            mode_enforces_identity=lambda _mode: False,
            conversation_headers_func=lambda _conversation, updated_at: {'X-Conversation-Updated-At': updated_at},
        )

        streamed, terminal = _collect_stream_output(result['stream'])
        self.assertIn('1) Comprendre', streamed)
        self.assertIn('2) Structurer', streamed)
        self.assertEqual(terminal, {'event': 'done', 'updated_at': '2026-03-26T00:11:00Z'})
        self.assertEqual(conversation['messages'][-1]['content'], streamed)

    def test_run_llm_exchange_stream_removes_unrequested_fenced_code_blocks(self) -> None:
        observed = {'save_calls': [], 'save_new_traces_calls': [], 'sequence': []}
        conversation = {
            'id': 'conv-stream-no-code',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }

        class FakeStreamResponse:
            encoding = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True, delimiter='\n'):
                yield 'data: {"choices":[{"delta":{"content":"Voici JSON :\\n\\n"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"```json\\n"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"{\\n  \\"nom\\": \\"Dupont\\"\\n}\\n"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"```\\n"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"C\\u2019est un format texte."}}]}'
                yield 'data: [DONE]'

        def fake_post(_url, *, json, headers, timeout, stream=False):
            return FakeStreamResponse()

        runtime_settings_module = SimpleNamespace(
            get_runtime_secret_value=lambda *_args, **_kwargs: SimpleNamespace(value='sk-test'),
            RuntimeSettingsSecretRequiredError=RuntimeError,
            RuntimeSettingsSecretResolutionError=ValueError,
        )

        def fake_save_new_traces(_conversation):
            observed['sequence'].append('save_new_traces')
            observed['save_new_traces_calls'].append([dict(message) for message in _conversation['messages']])

        def fake_save_conversation(_conversation, **kwargs):
            observed['sequence'].append('save_conversation')
            observed['save_calls'].append(dict(kwargs))

        memory_store_module = SimpleNamespace(
            save_new_traces=fake_save_new_traces,
            reactivate_identities=lambda _identity_ids: observed['sequence'].append('reactivate_identities'),
        )
        conv_store_module = SimpleNamespace(
            append_message=lambda conv, role, content, timestamp=None: conv['messages'].append(
                {'role': role, 'content': content, 'timestamp': timestamp}
            ),
            save_conversation=fake_save_conversation,
        )
        llm_module = SimpleNamespace(
            or_chat_completions_url=_synthetic_chat_completions_url,
            or_headers=lambda *, caller: {'Authorization': 'Bearer token'},
            resolve_provider_title=lambda caller='llm': f'FridaDev/{caller}',
            build_payload=lambda *_args, **_kwargs: {'model': 'openrouter/runtime-main-model'},
            extract_openrouter_provider_metadata=lambda payload, *, requested_model=None: {},
            build_provider_observability_fields=lambda *, caller, provider_metadata: {},
            merge_openrouter_provider_metadata=lambda current, payload, *, requested_model=None: dict(current or {}),
            log_provider_metadata=lambda *_args, **_kwargs: None,
            extract_openrouter_text=lambda payload: payload['choices'][0]['message']['content'],
            sanitize_provider_text=lambda text: text,
        )
        requests_module = SimpleNamespace(
            post=fake_post,
            exceptions=SimpleNamespace(RequestException=_RequestException),
        )
        result = chat_llm_flow.run_llm_exchange(
            conversation=conversation,
            prompt_messages=[{'role': 'user', 'content': 'bonjour'}],
            runtime_main_model='openrouter/runtime-main-model',
            temperature=0.4,
            top_p=1.0,
            max_tokens=256,
            stream_req=True,
            current_mode='enforced_all',
            identity_ids=['identity-1'],
            web_input=None,
            assistant_output_policy=assistant_output_contract.AssistantOutputPolicy(),
            runtime_settings_module=runtime_settings_module,
            memory_store_module=memory_store_module,
            conv_store_module=conv_store_module,
            llm_module=llm_module,
            requests_module=requests_module,
            token_utils_module=SimpleNamespace(estimate_tokens=lambda *_args, **_kwargs: 3),
            admin_logs_module=SimpleNamespace(
                log_event=lambda event, **_kwargs: (
                    observed['sequence'].append('AssistantText')
                    if event == 'AssistantText'
                    else None
                )
            ),
            config_module=SimpleNamespace(OR_BASE='https://openrouter.example', TIMEOUT_S=42),
            logger=SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None),
            arbiter_module=SimpleNamespace(),
            now_iso_func=lambda: '2026-03-26T00:11:00Z',
            record_identity_entries_for_mode=lambda *_args, **_kwargs: observed['sequence'].append('identity_write'),
            mode_enforces_identity=lambda _mode: True,
            conversation_headers_func=lambda _conversation, updated_at: {'X-Conversation-Updated-At': updated_at},
        )

        streamed, terminal = _collect_stream_output(result['stream'])
        self.assertIn('Voici JSON :', streamed)
        self.assertIn('C’est un format texte.', streamed)
        self.assertNotIn('```', streamed)
        self.assertNotIn('"nom"', streamed)
        self.assertEqual(terminal, {'event': 'done', 'updated_at': '2026-03-26T00:11:00Z'})
        self.assertEqual(conversation['messages'][-1]['content'], streamed)
        self.assertNotIn('meta', conversation['messages'][-1])
        self.assertEqual(observed['save_calls'][-1]['updated_at'], '2026-03-26T00:11:00Z')
        self.assertEqual(
            observed['sequence'],
            ['save_conversation', 'AssistantText', 'identity_write', 'reactivate_identities', 'save_new_traces'],
        )
        self.assertEqual(observed['save_new_traces_calls'][-1][-1]['content'], streamed)

    def test_run_llm_exchange_stream_persistence_failure_emits_terminal_without_updated_at(self) -> None:
        events = []
        observed = {
            'save_calls': [],
            'save_new_traces_calls': [],
            'identity_calls': 0,
            'reactivate_calls': 0,
        }
        conversation = {
            'id': 'conv-stream-persist-fail',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }

        class FakeStreamResponse:
            encoding = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True, delimiter='\n'):
                yield 'data: {"choices":[{"delta":{"content":"Bon"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"jour"}}]}'
                yield 'data: [DONE]'

        def fake_save_conversation(_conversation, **kwargs):
            observed['save_calls'].append(dict(kwargs))
            return SimpleNamespace(
                ok=False,
                catalog_saved=True,
                messages_saved=False,
                updated_at=kwargs.get('updated_at'),
                message_count=len(_conversation.get('messages', [])),
                reason='messages_write_failed',
            )

        runtime_settings_module = SimpleNamespace(
            get_runtime_secret_value=lambda *_args, **_kwargs: SimpleNamespace(value='sk-test'),
            RuntimeSettingsSecretRequiredError=RuntimeError,
            RuntimeSettingsSecretResolutionError=ValueError,
        )
        memory_store_module = SimpleNamespace(
            save_new_traces=lambda _conversation: observed['save_new_traces_calls'].append(
                [dict(message) for message in _conversation.get('messages', [])]
            ),
            reactivate_identities=lambda _identity_ids: observed.update({'reactivate_calls': observed['reactivate_calls'] + 1}),
        )
        conv_store_module = SimpleNamespace(
            append_message=lambda conv, role, content, timestamp=None, meta=None: conv['messages'].append(
                {'role': role, 'content': content, 'timestamp': timestamp, **({'meta': meta} if meta is not None else {})}
            ),
            save_conversation=fake_save_conversation,
        )
        llm_module = SimpleNamespace(
            or_chat_completions_url=_synthetic_chat_completions_url,
            or_headers=lambda *, caller: {'Authorization': 'Bearer token'},
            resolve_provider_title=lambda caller='llm': f'FridaDev/{caller}',
            build_payload=lambda *_args, **_kwargs: {'model': 'openrouter/runtime-main-model'},
            extract_openrouter_provider_metadata=lambda payload, *, requested_model=None: {},
            build_provider_observability_fields=lambda *, caller, provider_metadata: {},
            merge_openrouter_provider_metadata=lambda current, payload, *, requested_model=None: dict(current or {}),
            log_provider_metadata=lambda *_args, **_kwargs: None,
            extract_openrouter_text=lambda payload: payload['choices'][0]['message']['content'],
            sanitize_provider_text=lambda text: text,
        )
        result = chat_llm_flow.run_llm_exchange(
            conversation=conversation,
            prompt_messages=[{'role': 'user', 'content': 'bonjour'}],
            runtime_main_model='openrouter/runtime-main-model',
            temperature=0.4,
            top_p=1.0,
            max_tokens=256,
            stream_req=True,
            current_mode='enforced_all',
            identity_ids=['id-a'],
            web_input=None,
            assistant_output_policy=assistant_output_contract.AssistantOutputPolicy(),
            runtime_settings_module=runtime_settings_module,
            memory_store_module=memory_store_module,
            conv_store_module=conv_store_module,
            llm_module=llm_module,
            requests_module=SimpleNamespace(
                post=lambda *_args, **_kwargs: FakeStreamResponse(),
                exceptions=SimpleNamespace(RequestException=_RequestException),
            ),
            token_utils_module=SimpleNamespace(estimate_tokens=lambda *_args, **_kwargs: 3),
            admin_logs_module=SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs))),
            config_module=SimpleNamespace(OR_BASE='https://openrouter.example', TIMEOUT_S=42),
            logger=SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None),
            arbiter_module=SimpleNamespace(),
            now_iso_func=lambda: '2026-03-26T00:11:00Z',
            record_identity_entries_for_mode=lambda *_args, **_kwargs: observed.update(
                {'identity_calls': observed['identity_calls'] + 1}
            ),
            mode_enforces_identity=lambda _mode: True,
            conversation_headers_func=lambda _conversation, updated_at: {'X-Conversation-Updated-At': updated_at},
        )

        streamed, terminal = _collect_stream_output(result['stream'])
        self.assertEqual(streamed, 'Bonjour')
        self.assertEqual(
            terminal,
            {
                'event': 'error',
                'error_code': 'conversation_persist_failed',
            },
        )
        self.assertNotIn('updated_at', terminal)
        self.assertEqual(conversation['messages'], [{'role': 'user', 'content': 'hello'}])
        self.assertEqual(observed['save_calls'][-1]['updated_at'], '2026-03-26T00:11:00Z')
        self.assertEqual(observed['save_new_traces_calls'], [])
        self.assertEqual(observed['identity_calls'], 0)
        self.assertEqual(observed['reactivate_calls'], 0)
        persist_error_events = _event_payloads(events, 'llm_stream_finalize_persist_error')
        self.assertEqual(persist_error_events[-1]['error_code'], 'conversation_persist_failed')
        self.assertEqual(persist_error_events[-1]['reason'], 'messages_write_failed')

    def test_run_llm_exchange_stream_emits_error_terminal_on_request_exception(self) -> None:
        events = []
        observed = {'save_calls': [], 'provider_log_calls': []}
        conversation = {
            'id': 'conv-stream-error',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }

        class FakeStreamResponse:
            encoding = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True, delimiter='\n'):
                yield 'data: {"choices":[{"delta":{"content":"Bon"}}]}'
                raise _RequestException(_dangerous_exception_message())

        def fake_post(_url, *, json, headers, timeout, stream=False):
            return FakeStreamResponse()

        runtime_settings_module = SimpleNamespace(
            get_runtime_secret_value=lambda *_args, **_kwargs: SimpleNamespace(value='sk-test'),
            RuntimeSettingsSecretRequiredError=RuntimeError,
            RuntimeSettingsSecretResolutionError=ValueError,
        )

        memory_store_module = SimpleNamespace(
            save_new_traces=lambda _conversation: None,
            reactivate_identities=lambda _identity_ids: None,
        )
        conv_store_module = SimpleNamespace(
            append_message=lambda conv, role, content, timestamp=None, meta=None: conv['messages'].append(
                {'role': role, 'content': content, 'timestamp': timestamp, **({'meta': meta} if meta is not None else {})}
            ),
            save_conversation=lambda _conversation, **kwargs: observed['save_calls'].append(dict(kwargs)),
        )
        llm_module = SimpleNamespace(
            or_chat_completions_url=_synthetic_chat_completions_url,
            or_headers=lambda *, caller: {'Authorization': 'Bearer token'},
            resolve_provider_title=lambda caller='llm': f'FridaDev/{caller}',
            build_payload=lambda *_args, **_kwargs: {'model': 'openrouter/runtime-main-model'},
            extract_openrouter_provider_metadata=lambda payload, *, requested_model=None: {
                'provider_generation_id': payload.get('id'),
                'provider_model': payload.get('model') or requested_model,
            },
            build_provider_observability_fields=lambda *, caller, provider_metadata: {
                'provider_caller': caller,
                'provider_title': f'FridaDev/{caller}',
                **dict(provider_metadata),
            },
            merge_openrouter_provider_metadata=lambda current, payload, *, requested_model=None: dict(current or {}, **{
                key: value
                for key, value in {
                    'provider_generation_id': payload.get('id'),
                    'provider_model': payload.get('model') or requested_model,
                }.items()
                if value is not None
            }),
            log_provider_metadata=lambda _logger, event, provider_metadata: observed['provider_log_calls'].append((event, dict(provider_metadata))),
            extract_openrouter_text=lambda payload: payload['choices'][0]['message']['content'],
            sanitize_provider_text=lambda text: text,
        )
        requests_module = SimpleNamespace(
            post=fake_post,
            exceptions=SimpleNamespace(RequestException=_RequestException),
        )
        result = chat_llm_flow.run_llm_exchange(
            conversation=conversation,
            prompt_messages=[{'role': 'user', 'content': 'bonjour'}],
            runtime_main_model='openrouter/runtime-main-model',
            temperature=0.4,
            top_p=1.0,
            max_tokens=256,
            stream_req=True,
            current_mode='shadow',
            identity_ids=[],
            web_input=None,
            runtime_settings_module=runtime_settings_module,
            memory_store_module=memory_store_module,
            conv_store_module=conv_store_module,
            llm_module=llm_module,
            requests_module=requests_module,
            token_utils_module=SimpleNamespace(estimate_tokens=lambda *_args, **_kwargs: 3),
            admin_logs_module=SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs))),
            config_module=SimpleNamespace(OR_BASE='https://openrouter.example', TIMEOUT_S=42),
            logger=SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None),
            arbiter_module=SimpleNamespace(),
            now_iso_func=lambda: '2026-03-26T00:11:00Z',
            record_identity_entries_for_mode=lambda *_args, **_kwargs: None,
            mode_enforces_identity=lambda _mode: False,
            conversation_headers_func=lambda _conversation, updated_at: {'X-Conversation-Updated-At': updated_at},
        )

        streamed, terminal = _collect_stream_output(result['stream'])
        self.assertEqual(streamed, 'Bon')
        self.assertEqual(
            terminal,
            {
                'event': 'error',
                'error_code': 'upstream_error',
                'updated_at': '2026-03-26T00:11:00Z',
            },
        )
        self.assertEqual(
            conversation['messages'],
            [
                {'role': 'user', 'content': 'hello'},
                {
                    'role': 'assistant',
                    'content': '',
                    'timestamp': '2026-03-26T00:11:00Z',
                    'meta': {
                        'assistant_turn': {
                            'status': 'interrupted',
                            'error_code': 'upstream_error',
                        }
                    },
                },
            ],
        )
        self.assertEqual(observed['save_calls'][-1]['updated_at'], '2026-03-26T00:11:00Z')
        self.assertEqual(
            _event_payloads(events, 'llm_stream_error'),
            [
                {
                    'level': 'ERROR',
                    'conversation_id': 'conv-stream-error',
                    'model': 'openrouter/runtime-main-model',
                    'error_class': '_RequestException',
                    'error_code': 'upstream_error',
                    'reason_code': 'llm_upstream_error',
                }
            ],
        )
        _assert_content_free(self, terminal, events, conversation)

    def test_run_llm_exchange_stream_emits_error_terminal_on_local_finalize_exception(self) -> None:
        events = []
        observed = {'save_calls': [], 'save_attempts': 0, 'provider_log_calls': [], 'save_new_traces_calls': []}
        conversation = {
            'id': 'conv-stream-finalize-error',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }

        class FakeStreamResponse:
            encoding = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True, delimiter='\n'):
                yield 'data: {"id":"gen-stream","choices":[{"delta":{"content":"Bon"}}]}'
                yield 'data: [DONE]'

        def fake_post(_url, *, json, headers, timeout, stream=False):
            return FakeStreamResponse()

        runtime_settings_module = SimpleNamespace(
            get_runtime_secret_value=lambda *_args, **_kwargs: SimpleNamespace(value='sk-test'),
            RuntimeSettingsSecretRequiredError=RuntimeError,
            RuntimeSettingsSecretResolutionError=ValueError,
        )

        def fake_save_new_traces(_conversation):
            observed['save_new_traces_calls'].append([dict(message) for message in _conversation['messages']])

        memory_store_module = SimpleNamespace(
            save_new_traces=fake_save_new_traces,
            reactivate_identities=lambda _identity_ids: None,
        )

        def fake_save_conversation(_conversation, **kwargs):
            observed['save_attempts'] += 1
            if observed['save_attempts'] == 1:
                raise RuntimeError(_dangerous_exception_message())
            observed['save_calls'].append(dict(kwargs))

        conv_store_module = SimpleNamespace(
            append_message=lambda conv, role, content, timestamp=None, meta=None: conv['messages'].append(
                {'role': role, 'content': content, 'timestamp': timestamp, **({'meta': meta} if meta is not None else {})}
            ),
            save_conversation=fake_save_conversation,
        )
        llm_module = SimpleNamespace(
            or_chat_completions_url=_synthetic_chat_completions_url,
            or_headers=lambda *, caller: {'Authorization': 'Bearer token'},
            resolve_provider_title=lambda caller='llm': f'FridaDev/{caller}',
            build_payload=lambda *_args, **_kwargs: {'model': 'openrouter/runtime-main-model'},
            extract_openrouter_provider_metadata=lambda payload, *, requested_model=None: {
                'provider_generation_id': payload.get('id'),
                'provider_model': payload.get('model') or requested_model,
            },
            build_provider_observability_fields=lambda *, caller, provider_metadata: {
                'provider_caller': caller,
                'provider_title': f'FridaDev/{caller}',
                **dict(provider_metadata),
            },
            merge_openrouter_provider_metadata=lambda current, payload, *, requested_model=None: dict(current or {}, **{
                key: value
                for key, value in {
                    'provider_generation_id': payload.get('id'),
                    'provider_model': payload.get('model') or requested_model,
                }.items()
                if value is not None
            }),
            log_provider_metadata=lambda _logger, event, provider_metadata: observed['provider_log_calls'].append((event, dict(provider_metadata))),
            extract_openrouter_text=lambda payload: payload['choices'][0]['message']['content'],
            sanitize_provider_text=lambda text: text,
        )
        requests_module = SimpleNamespace(
            post=fake_post,
            exceptions=SimpleNamespace(RequestException=_RequestException),
        )
        result = chat_llm_flow.run_llm_exchange(
            conversation=conversation,
            prompt_messages=[{'role': 'user', 'content': 'bonjour'}],
            runtime_main_model='openrouter/runtime-main-model',
            temperature=0.4,
            top_p=1.0,
            max_tokens=256,
            stream_req=True,
            current_mode='shadow',
            identity_ids=[],
            web_input=None,
            runtime_settings_module=runtime_settings_module,
            memory_store_module=memory_store_module,
            conv_store_module=conv_store_module,
            llm_module=llm_module,
            requests_module=requests_module,
            token_utils_module=SimpleNamespace(estimate_tokens=lambda *_args, **_kwargs: 3),
            admin_logs_module=SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs))),
            config_module=SimpleNamespace(OR_BASE='https://openrouter.example', TIMEOUT_S=42),
            logger=SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None),
            arbiter_module=SimpleNamespace(),
            now_iso_func=lambda: '2026-03-26T00:11:00Z',
            record_identity_entries_for_mode=lambda *_args, **_kwargs: None,
            mode_enforces_identity=lambda _mode: False,
            conversation_headers_func=lambda _conversation, updated_at: {'X-Conversation-Updated-At': updated_at},
        )

        streamed, terminal = _collect_stream_output(result['stream'])
        self.assertEqual(streamed, 'Bon')
        self.assertEqual(
            terminal,
            {
                'event': 'error',
                'error_code': 'stream_finalize_error',
                'updated_at': '2026-03-26T00:11:00Z',
            },
        )
        self.assertEqual(
            conversation['messages'],
            [
                {'role': 'user', 'content': 'hello'},
                {
                    'role': 'assistant',
                    'content': '',
                    'timestamp': '2026-03-26T00:11:00Z',
                    'meta': {
                        'assistant_turn': {
                            'status': 'interrupted',
                            'error_code': 'stream_finalize_error',
                        }
                    },
                },
            ],
        )
        self.assertEqual(observed['save_attempts'], 2)
        self.assertEqual(observed['save_calls'][-1]['updated_at'], '2026-03-26T00:11:00Z')
        self.assertEqual(observed['save_new_traces_calls'], [])
        self.assertEqual(
            _event_payloads(events, 'llm_stream_finalize_error'),
            [
                {
                    'level': 'ERROR',
                    'conversation_id': 'conv-stream-finalize-error',
                    'model': 'openrouter/runtime-main-model',
                    'error_class': 'RuntimeError',
                    'error_code': 'stream_finalize_error',
                    'reason_code': 'llm_stream_finalize_error',
                }
            ],
        )
        _assert_content_free(self, terminal, events, conversation)

    def test_run_llm_exchange_returns_502_on_request_exception(self) -> None:
        events = []
        observed = {'save_calls': 0}

        def fake_post(*_args, **_kwargs):
            raise _RequestException(_dangerous_exception_message())

        runtime_settings_module = SimpleNamespace(
            get_runtime_secret_value=lambda *_args, **_kwargs: SimpleNamespace(value='sk-test'),
            RuntimeSettingsSecretRequiredError=RuntimeError,
            RuntimeSettingsSecretResolutionError=ValueError,
        )
        memory_store_module = SimpleNamespace(save_new_traces=lambda *_args, **_kwargs: None, reactivate_identities=lambda *_args, **_kwargs: None)
        conv_store_module = SimpleNamespace(
            append_message=lambda *_args, **_kwargs: None,
            save_conversation=lambda *_args, **_kwargs: observed.update({'save_calls': observed['save_calls'] + 1}),
        )
        llm_module = SimpleNamespace(
            or_chat_completions_url=_synthetic_chat_completions_url,
            or_headers=lambda **_kwargs: {},
            resolve_provider_title=lambda caller='llm': f'FridaDev/{caller}',
            build_payload=lambda *_args, **_kwargs: {'model': 'openrouter/runtime-main-model'},
            sanitize_provider_text=lambda text: text,
        )
        requests_module = SimpleNamespace(
            post=fake_post,
            exceptions=SimpleNamespace(RequestException=_RequestException),
        )
        token_utils_module = SimpleNamespace(estimate_tokens=lambda *_args, **_kwargs: 1)
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))
        config_module = SimpleNamespace(OR_BASE='https://openrouter.example', TIMEOUT_S=42)
        logger = SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None)

        result = chat_llm_flow.run_llm_exchange(
            conversation={'id': 'conv-err', 'created_at': '2026-03-26T00:00:00Z', 'messages': []},
            prompt_messages=[{'role': 'user', 'content': 'bonjour'}],
            runtime_main_model='openrouter/runtime-main-model',
            temperature=0.4,
            top_p=1.0,
            max_tokens=256,
            stream_req=False,
            current_mode='shadow',
            identity_ids=[],
            web_input=None,
            runtime_settings_module=runtime_settings_module,
            memory_store_module=memory_store_module,
            conv_store_module=conv_store_module,
            llm_module=llm_module,
            requests_module=requests_module,
            token_utils_module=token_utils_module,
            admin_logs_module=admin_logs_module,
            config_module=config_module,
            logger=logger,
            arbiter_module=SimpleNamespace(),
            now_iso_func=lambda: '2026-03-26T00:12:00Z',
            record_identity_entries_for_mode=lambda *_args, **_kwargs: None,
            mode_enforces_identity=lambda _mode: False,
            conversation_headers_func=lambda *_args, **_kwargs: {},
        )

        self.assertEqual(result['kind'], 'json')
        self.assertEqual(result['status'], 502)
        self.assertEqual(
            result['payload'],
            {
                'ok': False,
                'error': 'Connexion au LLM impossible',
                'error_code': 'upstream_error',
                'reason_code': 'llm_upstream_error',
                'error_class': '_RequestException',
            },
        )
        self.assertEqual(observed['save_calls'], 1)
        self.assertEqual(
            _event_payloads(events, 'llm_error'),
            [
                {
                    'level': 'ERROR',
                    'conversation_id': 'conv-err',
                    'model': 'openrouter/runtime-main-model',
                    'error_class': '_RequestException',
                    'error_code': 'upstream_error',
                    'reason_code': 'llm_upstream_error',
                }
            ],
        )
        _assert_content_free(self, result, events)

    def test_run_llm_exchange_returns_500_on_runtime_secret_error(self) -> None:
        class SecretRequiredError(Exception):
            pass

        observed = {'build_payload_called': False}

        runtime_settings_module = SimpleNamespace(
            get_runtime_secret_value=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                SecretRequiredError(_dangerous_exception_message())
            ),
            RuntimeSettingsSecretRequiredError=SecretRequiredError,
            RuntimeSettingsSecretResolutionError=ValueError,
        )
        llm_module = SimpleNamespace(
            or_chat_completions_url=_synthetic_chat_completions_url,
            or_headers=lambda **_kwargs: {},
            resolve_provider_title=lambda caller='llm': f'FridaDev/{caller}',
            build_payload=lambda *_args, **_kwargs: observed.update({'build_payload_called': True}) or {},
            sanitize_provider_text=lambda text: text,
        )

        result = chat_llm_flow.run_llm_exchange(
            conversation={'id': 'conv-secret', 'created_at': '2026-03-26T00:00:00Z', 'messages': []},
            prompt_messages=[{'role': 'user', 'content': 'bonjour'}],
            runtime_main_model='openrouter/runtime-main-model',
            temperature=0.4,
            top_p=1.0,
            max_tokens=256,
            stream_req=False,
            current_mode='shadow',
            identity_ids=[],
            web_input=None,
            runtime_settings_module=runtime_settings_module,
            memory_store_module=SimpleNamespace(save_new_traces=lambda *_args, **_kwargs: None, reactivate_identities=lambda *_args, **_kwargs: None),
            conv_store_module=SimpleNamespace(append_message=lambda *_args, **_kwargs: None, save_conversation=lambda *_args, **_kwargs: None),
            llm_module=llm_module,
            requests_module=SimpleNamespace(
                post=lambda *_args, **_kwargs: None,
                exceptions=SimpleNamespace(RequestException=_RequestException),
            ),
            token_utils_module=SimpleNamespace(estimate_tokens=lambda *_args, **_kwargs: 1),
            admin_logs_module=SimpleNamespace(log_event=lambda *_args, **_kwargs: None),
            config_module=SimpleNamespace(OR_BASE='https://openrouter.example', TIMEOUT_S=42),
            logger=SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None),
            arbiter_module=SimpleNamespace(),
            now_iso_func=lambda: '2026-03-26T00:12:00Z',
            record_identity_entries_for_mode=lambda *_args, **_kwargs: None,
            mode_enforces_identity=lambda _mode: False,
            conversation_headers_func=lambda *_args, **_kwargs: {},
        )

        self.assertEqual(result['kind'], 'json')
        self.assertEqual(result['status'], 500)
        self.assertEqual(
            result['payload'],
            {
                'ok': False,
                'error': 'Configuration LLM indisponible',
                'error_code': 'llm_secret_resolution_error',
                'reason_code': 'llm_secret_resolution_error',
                'error_class': 'SecretRequiredError',
            },
        )
        self.assertFalse(observed['build_payload_called'])
        _assert_content_free(self, result)


if __name__ == '__main__':
    unittest.main()
