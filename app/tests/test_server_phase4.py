from __future__ import annotations

import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import chat_llm_flow
from core import chat_service


def _event_payloads(events: list[tuple[str, dict[str, object]]], event_name: str) -> list[dict[str, object]]:
    return [payload for event, payload in events if event == event_name]


class ServerPhase4BehaviorTests(unittest.TestCase):
    def test_run_llm_exchange_uses_payload_model_for_outbound_call_and_logs(self) -> None:
        events: list[tuple[str, dict[str, object]]] = []
        observed: dict[str, object] = {
            'request_json': None,
            'estimate_calls': [],
        }
        conversation = {
            'id': 'conv-phase4-llm',
            'created_at': '2026-04-21T00:00:00Z',
            'messages': [{'role': 'user', 'content': 'Bonjour'}],
        }

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {
                    'id': 'gen-phase4',
                    'choices': [{'message': {'content': 'Reponse'}}],
                    'usage': {'prompt_tokens': 11, 'completion_tokens': 3, 'total_tokens': 14},
                }

        def fake_post(_url, *, json, headers, timeout):
            observed['request_json'] = dict(json)
            observed['request_headers'] = dict(headers)
            observed['request_timeout'] = timeout
            return FakeResponse()

        def fake_estimate_tokens(_messages, model):
            observed['estimate_calls'].append(str(model))
            return 5

        runtime_settings_module = SimpleNamespace(
            get_runtime_secret_value=lambda *_args, **_kwargs: SimpleNamespace(value='sk-phase4'),
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
            save_conversation=lambda _conversation, **_kwargs: None,
        )
        llm_module = SimpleNamespace(
            or_headers=lambda **_kwargs: {'Authorization': 'Bearer test'},
            build_payload=lambda _messages, _temperature, _top_p, _max_tokens, *, stream=False: {
                'model': 'openrouter/request-model',
                'messages': list(_messages),
                'stream': stream,
            },
            resolve_provider_title=lambda _caller='llm': 'FridaDev/llm',
            read_openrouter_response_payload=lambda response: response.json(),
            extract_openrouter_provider_metadata=lambda payload, *, requested_model=None: {
                'provider_generation_id': payload.get('id'),
                'provider_model': requested_model,
            },
            build_provider_observability_fields=lambda *, caller, provider_metadata: {
                'provider_caller': caller,
                'provider_title': f'FridaDev/{caller}',
                **dict(provider_metadata),
            },
            log_provider_metadata=lambda *_args, **_kwargs: None,
            extract_openrouter_text=lambda payload: payload['choices'][0]['message']['content'],
        )
        requests_module = SimpleNamespace(
            post=fake_post,
            exceptions=SimpleNamespace(RequestException=RuntimeError),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))
        config_module = SimpleNamespace(OR_BASE='https://openrouter.example', TIMEOUT_S=30)
        logger = SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None)

        result = chat_llm_flow.run_llm_exchange(
            conversation=conversation,
            prompt_messages=[{'role': 'user', 'content': 'Bonjour'}],
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
            token_utils_module=SimpleNamespace(estimate_tokens=fake_estimate_tokens),
            admin_logs_module=admin_logs_module,
            config_module=config_module,
            logger=logger,
            arbiter_module=SimpleNamespace(),
            now_iso_func=lambda: '2026-04-21T00:01:00Z',
            record_identity_entries_for_mode=lambda *_args, **_kwargs: None,
            mode_enforces_identity=lambda _mode: False,
            conversation_headers_func=lambda _conversation, updated_at: {'X-Conversation-Updated-At': updated_at},
        )

        self.assertEqual(result['kind'], 'json')
        self.assertEqual(result['status'], 200)
        self.assertEqual(observed['request_json']['model'], 'openrouter/request-model')
        self.assertEqual(_event_payloads(events, 'llm_payload')[0]['model'], 'openrouter/request-model')
        self.assertEqual(_event_payloads(events, 'llm_call')[0]['model'], 'openrouter/request-model')
        self.assertEqual(observed['estimate_calls'], ['openrouter/runtime-main-model'])

    def test_chat_response_uses_runtime_main_model_for_user_tokens_and_summary(self) -> None:
        observed: dict[str, object] = {
            'estimate_models': [],
            'summary_models': [],
            'llm_runtime_model': None,
        }
        conversation = {
            'id': 'conv-phase4-chat',
            'created_at': '2026-04-21T00:00:00Z',
            'messages': [],
        }

        def fake_estimate_tokens(_messages, model):
            observed['estimate_models'].append(str(model))
            return 7

        def fake_maybe_summarize(_conversation, model):
            observed['summary_models'].append(str(model))
            return False

        def fake_run_llm_exchange(**kwargs):
            observed['llm_runtime_model'] = kwargs['runtime_main_model']
            return {
                'kind': 'json',
                'payload': {'ok': True},
                'status': 200,
                'headers': {},
            }

        conv_store_module = SimpleNamespace(
            append_message=lambda conv, role, content, meta=None, timestamp=None: conv['messages'].append(
                {'role': role, 'content': content, 'timestamp': timestamp, **({'meta': meta} if meta is not None else {})}
            ),
            save_conversation=lambda *_args, **_kwargs: None,
            build_prompt_messages=lambda conv, *_args, **_kwargs: [
                {'role': str(message.get('role') or ''), 'content': str(message.get('content') or '')}
                for message in conv.get('messages', [])
            ],
        )
        runtime_settings_module = SimpleNamespace(
            get_main_model_settings=lambda: SimpleNamespace(
                payload={
                    'model': {'value': 'openrouter/runtime-main-model'},
                    'temperature': {'value': 0.4},
                    'top_p': {'value': 0.9},
                    'response_max_tokens': {'value': 512},
                }
            )
        )

        session = {
            'user_msg': 'Bonjour',
            'conversation': conversation,
            'stream_req': False,
            'web_search_on': False,
            'input_mode': 'keyboard',
        }

        with ExitStack() as stack:
            stack.enter_context(patch.object(chat_service.chat_session_flow, 'resolve_chat_session', return_value=(session, None)))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, 'resolve_backend_prompts', return_value=('SYSTEM', 'HERMENEUTIC')))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, 'build_augmented_system', return_value=('AUGMENTED SYSTEM', [])))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, 'apply_augmented_system', side_effect=lambda *_args, **_kwargs: None))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, 'build_hermeneutic_judgment_block', return_value=''))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, 'inject_hermeneutic_judgment_block', side_effect=lambda text, _block: text))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, 'build_voice_transcription_guard_block', return_value=''))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, 'inject_voice_transcription_guard_block', side_effect=lambda text, _block: text))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, 'build_direct_identity_revelation_guard_block', return_value=''))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, 'inject_direct_identity_revelation_guard_block', side_effect=lambda text, _block: text))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, 'build_web_reading_guard_block', return_value=''))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, 'inject_web_reading_guard_block', side_effect=lambda text, _block: text))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, 'build_plain_text_guard_block', return_value=''))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, 'inject_plain_text_guard_block', side_effect=lambda text, _block: text))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, 'inject_web_context', side_effect=lambda *_args, **_kwargs: None))
            stack.enter_context(patch.object(chat_service.chat_memory_flow, 'prepare_memory_context', return_value=('shadow', [], [])))
            stack.enter_context(patch.object(chat_service, '_resolve_summary_input', return_value={}))
            stack.enter_context(patch.object(chat_service, '_resolve_identity_input', return_value={}))
            stack.enter_context(patch.object(chat_service, '_resolve_recent_context_input', return_value={}))
            stack.enter_context(patch.object(chat_service, '_resolve_recent_window_input', return_value={}))
            stack.enter_context(patch.object(chat_service, '_resolve_user_turn_runtime_inputs', return_value=({}, {})))
            stack.enter_context(patch.object(chat_service, '_run_stimmung_agent_stage', return_value=None))
            stack.enter_context(patch.object(chat_service, '_store_latest_user_affective_turn_signal', side_effect=lambda *_args, **_kwargs: None))
            stack.enter_context(patch.object(chat_service, '_resolve_web_runtime_payload', return_value={'activation_mode': 'not_requested'}))
            stack.enter_context(patch.object(chat_service, '_run_hermeneutic_node_insertion_point', return_value={}))
            stack.enter_context(patch.object(chat_service, '_now_iso', return_value='2026-04-21T00:02:00Z'))
            stack.enter_context(patch.object(chat_service.chat_llm_flow, 'run_llm_exchange', side_effect=fake_run_llm_exchange))
            stack.enter_context(patch.object(chat_service.chat_turn_logger, 'set_state', side_effect=lambda *_args, **_kwargs: None))
            stack.enter_context(patch.object(chat_service.canonical_stimmung_input, 'build_stimmung_input', return_value={}))
            stack.enter_context(patch.object(chat_service.canonical_web_input, 'build_web_input_from_runtime_payload', side_effect=lambda payload: dict(payload)))
            stack.enter_context(patch.object(chat_service.assistant_output_contract, 'resolve_assistant_output_policy', return_value=None))

            result = chat_service.chat_response(
                {'message': 'Bonjour'},
                prompt_loader_module=SimpleNamespace(),
                conv_store_module=conv_store_module,
                memory_store_module=SimpleNamespace(),
                runtime_settings_module=runtime_settings_module,
                summarizer_module=SimpleNamespace(maybe_summarize=fake_maybe_summarize),
                identity_module=SimpleNamespace(),
                admin_logs_module=SimpleNamespace(log_event=lambda *_args, **_kwargs: None),
                llm_module=SimpleNamespace(),
                requests_module=SimpleNamespace(),
                token_utils_module=SimpleNamespace(estimate_tokens=fake_estimate_tokens),
                arbiter_module=SimpleNamespace(),
                web_search_module=SimpleNamespace(),
                config_module=SimpleNamespace(FRIDA_TIMEZONE='UTC'),
                logger=SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None),
            )

        self.assertEqual(result['kind'], 'json')
        self.assertEqual(result['status'], 200)
        self.assertEqual(observed['estimate_models'], ['openrouter/runtime-main-model'])
        self.assertEqual(observed['summary_models'], ['openrouter/runtime-main-model'])
        self.assertEqual(observed['llm_runtime_model'], 'openrouter/runtime-main-model')


if __name__ == '__main__':
    unittest.main()
