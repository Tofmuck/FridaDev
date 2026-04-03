from __future__ import annotations

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

from core import chat_llm_flow


class _RequestException(Exception):
    pass


def _event_payloads(events, event_name: str):
    return [payload for event, payload in events if event == event_name]


class ChatLlmFlowTests(unittest.TestCase):
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

        def fake_post(_url, *, json, headers, timeout):
            observed['request_stream_flag'] = None
            observed['request_payload'] = dict(json)
            observed['request_headers'] = dict(headers)
            observed['request_timeout'] = timeout
            return FakeResponse()

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
        memory_store_module = SimpleNamespace(
            save_new_traces=lambda _conversation: None,
            reactivate_identities=lambda _identity_ids: None,
        )
        conv_store_module = SimpleNamespace(
            append_message=lambda conv, role, content, timestamp=None: conv['messages'].append(
                {'role': role, 'content': content, 'timestamp': timestamp}
            ),
            save_conversation=lambda _conversation, **kwargs: observed['save_calls'].append(dict(kwargs)),
        )
        llm_module = SimpleNamespace(
            or_headers=lambda *, caller: observed.update({'headers_called_with': caller}) or {'Authorization': 'Bearer token'},
            build_payload=fake_build_payload,
            read_openrouter_response_payload=lambda response: response.json(),
            extract_openrouter_provider_metadata=lambda payload, *, requested_model=None: {
                'provider_generation_id': payload.get('id'),
                'provider_model': payload.get('model') or requested_model,
                'provider_prompt_tokens': (payload.get('usage') or {}).get('prompt_tokens'),
                'provider_completion_tokens': (payload.get('usage') or {}).get('completion_tokens'),
                'provider_total_tokens': (payload.get('usage') or {}).get('total_tokens'),
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
            _sanitize_encoding=lambda text: text,
        )
        requests_module = SimpleNamespace(
            post=fake_post,
            exceptions=SimpleNamespace(RequestException=_RequestException),
        )
        token_utils_module = SimpleNamespace(count_tokens=lambda _messages, _model: 7)
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))
        config_module = SimpleNamespace(OR_BASE='https://openrouter.example', TIMEOUT_S=42)
        logger = SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None)

        result = chat_llm_flow.run_llm_exchange(
            conversation=conversation,
            prompt_messages=[{'role': 'user', 'content': 'bonjour'}],
            runtime_main_model='openrouter/runtime-main-model',
            temperature=0.4,
            top_p=1.0,
            max_tokens=256,
            stream_req=False,
            current_mode='shadow',
            identity_ids=[],
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
            record_identity_entries_for_mode=lambda *_args, **_kwargs: observed.update({'identity_callback_called': True}),
            mode_enforces_identity=lambda _mode: False,
            conversation_headers_func=lambda _conversation, updated_at: {
                'X-Conversation-Id': 'conv-sync',
                'X-Conversation-Created-At': '2026-03-26T00:00:00Z',
                'X-Conversation-Updated-At': updated_at,
            },
        )

        self.assertEqual(result['kind'], 'json')
        self.assertEqual(result['status'], 200)
        self.assertEqual(
            result['payload'],
            {
                'ok': True,
                'text': 'reponse test',
                'conversation_id': 'conv-sync',
                'created_at': '2026-03-26T00:00:00Z',
                'updated_at': '2026-03-26T00:10:00Z',
            },
        )
        self.assertEqual(result['headers']['X-Conversation-Id'], 'conv-sync')
        self.assertEqual(observed['headers_called_with'], 'llm')
        self.assertFalse(observed['payload_stream_flag'])
        self.assertEqual(observed['secret_calls'], 1)
        self.assertTrue(observed['identity_callback_called'])
        self.assertEqual(observed['save_calls'][-1]['updated_at'], '2026-03-26T00:10:00Z')
        self.assertEqual(_event_payloads(events, 'llm_payload')[0]['model'], 'openrouter/runtime-main-model')
        self.assertFalse(_event_payloads(events, 'llm_call')[0]['stream'])
        self.assertEqual(
            observed['provider_log_calls'],
            [
                (
                    'llm_provider_response',
                    {
                        'provider_generation_id': 'gen-sync',
                        'provider_model': 'openrouter/runtime-main-model',
                        'provider_prompt_tokens': 12,
                        'provider_completion_tokens': 5,
                        'provider_total_tokens': 17,
                    },
                )
            ],
        )

    def test_run_llm_exchange_stream_success_keeps_stream_contract(self) -> None:
        events = []
        observed = {
            'request_stream_flag': None,
            'save_calls': [],
            'identity_callback_called': False,
            'reactivate_called': False,
            'provider_log_calls': [],
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
                yield 'data: [DONE]'

        def fake_post(_url, *, json, headers, timeout, stream=False):
            observed['request_stream_flag'] = stream
            return FakeStreamResponse()

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
            append_message=lambda conv, role, content, timestamp=None: conv['messages'].append(
                {'role': role, 'content': content, 'timestamp': timestamp}
            ),
            save_conversation=lambda _conversation, **kwargs: observed['save_calls'].append(dict(kwargs)),
        )
        llm_module = SimpleNamespace(
            or_headers=lambda *, caller: {'Authorization': 'Bearer token'},
            build_payload=lambda *_args, **_kwargs: {'model': 'openrouter/runtime-main-model'},
            read_openrouter_response_payload=lambda response: response.json(),
            extract_openrouter_provider_metadata=lambda payload, *, requested_model=None: {
                'provider_generation_id': payload.get('id'),
                'provider_model': payload.get('model') or requested_model,
                'provider_prompt_tokens': (payload.get('usage') or {}).get('prompt_tokens'),
                'provider_completion_tokens': (payload.get('usage') or {}).get('completion_tokens'),
                'provider_total_tokens': (payload.get('usage') or {}).get('total_tokens'),
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
            _sanitize_encoding=lambda text: text,
        )
        requests_module = SimpleNamespace(
            post=fake_post,
            exceptions=SimpleNamespace(RequestException=_RequestException),
        )
        token_utils_module = SimpleNamespace(count_tokens=lambda _messages, _model: 3)
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))
        config_module = SimpleNamespace(OR_BASE='https://openrouter.example', TIMEOUT_S=42)
        logger = SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None)

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
            now_iso_func=lambda: '2026-03-26T00:11:00Z',
            record_identity_entries_for_mode=lambda *_args, **_kwargs: observed.update({'identity_callback_called': True}),
            mode_enforces_identity=lambda mode: mode == 'enforced_all',
            conversation_headers_func=lambda _conversation, updated_at: {
                'X-Conversation-Id': 'conv-stream',
                'X-Conversation-Created-At': '2026-03-26T00:00:00Z',
                'X-Conversation-Updated-At': updated_at,
            },
        )

        self.assertEqual(result['kind'], 'stream')
        self.assertEqual(result['headers']['X-Conversation-Id'], 'conv-stream')
        self.assertEqual(result['headers']['X-Conversation-Updated-At'], '2026-03-26T00:11:00Z')
        self.assertTrue(_event_payloads(events, 'llm_call')[0]['stream'])

        streamed = ''.join(part for part in result['stream'])
        self.assertEqual(streamed, 'Bonjour')
        self.assertTrue(observed['request_stream_flag'])
        self.assertEqual(conversation['messages'][-1]['role'], 'assistant')
        self.assertEqual(conversation['messages'][-1]['content'], 'Bonjour')
        self.assertEqual(observed['save_calls'][-1]['updated_at'], '2026-03-26T00:11:00Z')
        self.assertTrue(observed['identity_callback_called'])
        self.assertTrue(observed['reactivate_called'])
        self.assertEqual(
            observed['provider_log_calls'],
            [
                (
                    'llm_provider_response',
                    {
                        'provider_generation_id': 'gen-stream',
                        'provider_model': 'openrouter/runtime-main-model',
                        'provider_prompt_tokens': 40,
                        'provider_completion_tokens': 2,
                        'provider_total_tokens': 42,
                    },
                )
            ],
        )

    def test_run_llm_exchange_returns_502_on_request_exception(self) -> None:
        events = []
        observed = {'save_calls': 0}

        def fake_post(*_args, **_kwargs):
            raise _RequestException('boom')

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
            or_headers=lambda **_kwargs: {},
            build_payload=lambda *_args, **_kwargs: {'model': 'openrouter/runtime-main-model'},
            _sanitize_encoding=lambda text: text,
        )
        requests_module = SimpleNamespace(
            post=fake_post,
            exceptions=SimpleNamespace(RequestException=_RequestException),
        )
        token_utils_module = SimpleNamespace(count_tokens=lambda *_args, **_kwargs: 1)
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
        self.assertEqual(result['payload'], {'ok': False, 'error': 'Connexion au LLM: boom'})
        self.assertEqual(observed['save_calls'], 1)
        self.assertEqual(_event_payloads(events, 'llm_error')[0]['model'], 'openrouter/runtime-main-model')

    def test_run_llm_exchange_returns_500_on_runtime_secret_error(self) -> None:
        class SecretRequiredError(Exception):
            pass

        observed = {'build_payload_called': False}

        runtime_settings_module = SimpleNamespace(
            get_runtime_secret_value=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                SecretRequiredError('missing secret config: main_model.api_key')
            ),
            RuntimeSettingsSecretRequiredError=SecretRequiredError,
            RuntimeSettingsSecretResolutionError=ValueError,
        )
        llm_module = SimpleNamespace(
            or_headers=lambda **_kwargs: {},
            build_payload=lambda *_args, **_kwargs: observed.update({'build_payload_called': True}) or {},
            _sanitize_encoding=lambda text: text,
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
            runtime_settings_module=runtime_settings_module,
            memory_store_module=SimpleNamespace(save_new_traces=lambda *_args, **_kwargs: None, reactivate_identities=lambda *_args, **_kwargs: None),
            conv_store_module=SimpleNamespace(append_message=lambda *_args, **_kwargs: None, save_conversation=lambda *_args, **_kwargs: None),
            llm_module=llm_module,
            requests_module=SimpleNamespace(
                post=lambda *_args, **_kwargs: None,
                exceptions=SimpleNamespace(RequestException=_RequestException),
            ),
            token_utils_module=SimpleNamespace(count_tokens=lambda *_args, **_kwargs: 1),
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
        self.assertEqual(result['payload'], {'ok': False, 'error': 'missing secret config: main_model.api_key'})
        self.assertFalse(observed['build_payload_called'])


if __name__ == '__main__':
    unittest.main()
