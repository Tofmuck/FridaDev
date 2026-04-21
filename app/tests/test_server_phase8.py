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

from core import chat_service


class ServerPhase8BehaviorTests(unittest.TestCase):
    def test_chat_response_prefers_runtime_sampling_settings_over_request_values(self) -> None:
        observed: dict[str, object] = {
            'temperature': None,
            'top_p': None,
            'max_tokens': None,
        }
        conversation = {
            'id': 'conv-phase8',
            'created_at': '2026-04-21T00:00:00Z',
            'messages': [],
        }

        def fake_run_llm_exchange(**kwargs):
            observed['temperature'] = kwargs['temperature']
            observed['top_p'] = kwargs['top_p']
            observed['max_tokens'] = kwargs['max_tokens']
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
                    'temperature': {'value': 0.35},
                    'top_p': {'value': 0.82},
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
            stack.enter_context(patch.object(chat_service, '_now_iso', return_value='2026-04-21T00:03:00Z'))
            stack.enter_context(patch.object(chat_service.chat_llm_flow, 'run_llm_exchange', side_effect=fake_run_llm_exchange))
            stack.enter_context(patch.object(chat_service.chat_turn_logger, 'set_state', side_effect=lambda *_args, **_kwargs: None))
            stack.enter_context(patch.object(chat_service.canonical_stimmung_input, 'build_stimmung_input', return_value={}))
            stack.enter_context(patch.object(chat_service.canonical_web_input, 'build_web_input_from_runtime_payload', side_effect=lambda payload: dict(payload)))
            stack.enter_context(patch.object(chat_service.assistant_output_contract, 'resolve_assistant_output_policy', return_value=None))

            result = chat_service.chat_response(
                {
                    'message': 'Bonjour',
                    'temperature': 9.9,
                    'top_p': 0.01,
                    'max_tokens': 123,
                },
                prompt_loader_module=SimpleNamespace(),
                conv_store_module=conv_store_module,
                memory_store_module=SimpleNamespace(),
                runtime_settings_module=runtime_settings_module,
                summarizer_module=SimpleNamespace(maybe_summarize=lambda *_args, **_kwargs: False),
                identity_module=SimpleNamespace(),
                admin_logs_module=SimpleNamespace(log_event=lambda *_args, **_kwargs: None),
                llm_module=SimpleNamespace(),
                requests_module=SimpleNamespace(),
                token_utils_module=SimpleNamespace(estimate_tokens=lambda *_args, **_kwargs: 1),
                arbiter_module=SimpleNamespace(),
                web_search_module=SimpleNamespace(),
                config_module=SimpleNamespace(FRIDA_TIMEZONE='UTC'),
                logger=SimpleNamespace(info=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None),
            )

        self.assertEqual(result['kind'], 'json')
        self.assertEqual(result['status'], 200)
        self.assertEqual(observed['temperature'], 0.35)
        self.assertEqual(observed['top_p'], 0.82)
        self.assertEqual(observed['max_tokens'], 123)


if __name__ == '__main__':
    unittest.main()
