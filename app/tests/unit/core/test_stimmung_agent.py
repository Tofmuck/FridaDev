from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import stimmung_agent
from observability import chat_turn_logger
from observability import log_store


class _FakeRequests:
    class exceptions:
        class RequestException(Exception):
            pass

        class Timeout(RequestException):
            pass

    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.calls: list[dict[str, object]] = []

    def post(self, url, json, headers, timeout):
        self.calls.append(
            {
                'url': url,
                'json': dict(json),
                'headers': dict(headers),
                'timeout': timeout,
            }
        )
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _FakeResponse:
    def __init__(self, content: str, *, error: Exception | None = None) -> None:
        self._content = content
        self._error = error

    def raise_for_status(self) -> None:
        if self._error is not None:
            raise self._error

    def json(self):
        return {
            'id': 'gen-stimmung',
            'model': 'openai/gpt-5.4-mini',
            'usage': {'prompt_tokens': 14, 'completion_tokens': 6, 'total_tokens': 20},
            'choices': [{'message': {'content': self._content}}],
        }


class StimmungAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_read_prompt = stimmung_agent.prompt_loader.read_prompt_text
        self.original_or_headers = stimmung_agent.llm_client.or_headers
        self.original_or_chat_completions_url = stimmung_agent.llm_client.or_chat_completions_url
        self.original_log_provider_metadata = stimmung_agent.llm_client.log_provider_metadata
        self.original_runtime_settings_getter = stimmung_agent.runtime_settings.get_stimmung_agent_model_settings
        self.provider_logs = []
        stimmung_agent.prompt_loader.read_prompt_text = lambda _path: 'SYSTEM PROMPT'
        stimmung_agent.llm_client.or_headers = lambda caller='llm': {'Authorization': f'caller={caller}'}
        stimmung_agent.llm_client.or_chat_completions_url = lambda: 'https://openrouter.example/chat/completions'
        stimmung_agent.llm_client.log_provider_metadata = lambda _logger, event_name, provider_metadata: self.provider_logs.append(
            (event_name, dict(provider_metadata))
        )
        stimmung_agent.runtime_settings.get_stimmung_agent_model_settings = lambda: types.SimpleNamespace(
            payload={
                'primary_model': {'value': stimmung_agent.PRIMARY_MODEL},
                'fallback_model': {'value': stimmung_agent.FALLBACK_MODEL},
                'timeout_s': {'value': 10},
                'temperature': {'value': 0.1},
                'top_p': {'value': 1.0},
                'max_tokens': {'value': 220},
            }
        )

    def tearDown(self) -> None:
        stimmung_agent.prompt_loader.read_prompt_text = self.original_read_prompt
        stimmung_agent.llm_client.or_headers = self.original_or_headers
        stimmung_agent.llm_client.or_chat_completions_url = self.original_or_chat_completions_url
        stimmung_agent.llm_client.log_provider_metadata = self.original_log_provider_metadata
        stimmung_agent.runtime_settings.get_stimmung_agent_model_settings = self.original_runtime_settings_getter

    def test_build_affective_turn_signal_returns_primary_validated_signal(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    '{"schema_version":"v1","present":true,"tones":[{"tone":"frustration","strength":7},{"tone":"confusion","strength":4}],"dominant_tone":"frustration","confidence":0.82}'
                )
            ]
        )

        result = stimmung_agent.build_affective_turn_signal(
            user_msg="C'est agaçant et je suis perdu",
            requests_module=requests_module,
        )

        self.assertEqual(result.status, 'ok')
        self.assertEqual(result.decision_source, 'primary')
        self.assertEqual(result.model, stimmung_agent.PRIMARY_MODEL)
        self.assertTrue(result.signal['present'])
        self.assertEqual(result.signal['dominant_tone'], 'frustration')
        self.assertEqual(result.signal['tones'][1], {'tone': 'confusion', 'strength': 4})
        self.assertEqual(requests_module.calls[0]['json']['model'], stimmung_agent.PRIMARY_MODEL)
        self.assertEqual(requests_module.calls[0]['headers'], {'Authorization': 'caller=stimmung_agent'})
        self.assertEqual(
            result.provider_metadata,
            {
                'provider_generation_id': 'gen-stimmung',
                'provider_model': 'openai/gpt-5.4-mini',
                'provider_prompt_tokens': 14,
                'provider_completion_tokens': 6,
                'provider_total_tokens': 20,
            },
        )
        self.assertEqual(
            self.provider_logs,
            [
                (
                    'stimmung_agent_provider_response',
                    {
                        'provider_generation_id': 'gen-stimmung',
                        'provider_model': 'openai/gpt-5.4-mini',
                        'provider_prompt_tokens': 14,
                        'provider_completion_tokens': 6,
                        'provider_total_tokens': 20,
                    },
                )
            ],
        )

    def test_build_affective_turn_signal_emits_stimmung_prompt_prepared_without_raw_payload(self) -> None:
        observed: list[dict[str, object]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, object], **_kwargs: object) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-stimmung-prepared',
            user_msg='message courant ultra sensible',
            web_search_enabled=False,
        )
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    '{"schema_version":"v1","present":true,"tones":[{"tone":"curiosite","strength":5}],"dominant_tone":"curiosite","confidence":0.74}'
                )
            ]
        )
        recent_window_input_payload = {
            'schema_version': 'v1',
            'turn_count': 2,
            'max_recent_turns': 5,
            'has_in_progress_turn': True,
            'turns': [
                {
                    'turn_status': 'complete',
                    'messages': [
                        {'role': 'user', 'content': 'ancien contenu prive'},
                        {'role': 'assistant', 'content': 'ancienne reponse privee'},
                    ],
                },
                {
                    'turn_status': 'in_progress',
                    'messages': [{'role': 'user', 'content': 'message courant ultra sensible'}],
                },
            ],
        }
        try:
            stimmung_agent.build_affective_turn_signal(
                user_msg='message courant ultra sensible',
                recent_window_input_payload=recent_window_input_payload,
                requests_module=requests_module,
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        event = next(item for item in observed if item['stage'] == 'stimmung_prompt_prepared')
        payload = event['payload_json']
        self.assertEqual(event['status'], 'ok')
        self.assertEqual(payload['model'], stimmung_agent.PRIMARY_MODEL)
        self.assertEqual(payload['prompt_kind'], 'stimmung_agent_secondary')
        self.assertEqual(payload['payload_kind'], 'secondary_stimmung_agent_provider')
        self.assertEqual(payload['provider_caller'], 'stimmung_agent')
        self.assertTrue(payload['secondary_provider_payload'])
        self.assertFalse(payload['main_llm_payload'])
        self.assertEqual(payload['attempt_decision_source'], 'primary')
        self.assertEqual(payload['messages_count'], 2)
        self.assertEqual(payload['message_role_counts'], {'system': 1, 'user': 1})
        self.assertTrue(payload['system_prompt_present'])
        self.assertGreater(payload['system_prompt_chars'], 0)
        self.assertTrue(payload['recent_window_present'])
        self.assertEqual(payload['recent_turn_count'], 2)
        self.assertEqual(payload['recent_turns_with_messages_count'], 2)
        self.assertTrue(payload['recent_has_in_progress_turn'])
        self.assertEqual(payload['recent_max_turns'], 5)
        self.assertTrue(payload['current_user_present'])
        self.assertGreater(payload['current_user_chars'], 0)
        self.assertGreater(payload['input_chars_total'], 0)
        self.assertEqual(
            payload['sampling'],
            {'temperature': 0.1, 'top_p': 1.0, 'max_tokens': 220, 'timeout_s': 10},
        )
        self.assertFalse(payload['fail_open'])
        self.assertEqual(payload['reason_code'], '')

        def collect_keys(value: object) -> set[str]:
            if isinstance(value, dict):
                keys: set[str] = set()
                for key, item in value.items():
                    keys.add(str(key))
                    keys.update(collect_keys(item))
                return keys
            if isinstance(value, list):
                keys = set()
                for item in value:
                    keys.update(collect_keys(item))
                return keys
            return set()

        forbidden_keys = {'prompt', 'messages', 'content', 'user_message', 'recent_window'}
        self.assertTrue(forbidden_keys.isdisjoint(collect_keys(payload)))
        serialized = repr(payload)
        self.assertNotIn('SYSTEM PROMPT', serialized)
        self.assertNotIn('ancien contenu prive', serialized)
        self.assertNotIn('ancienne reponse privee', serialized)
        self.assertNotIn('message courant ultra sensible', serialized)

    def test_build_affective_turn_signal_uses_runtime_settings_models_and_sampling(self) -> None:
        stimmung_agent.runtime_settings.get_stimmung_agent_model_settings = lambda: types.SimpleNamespace(
            payload={
                'primary_model': {'value': 'openai/custom-stimmung-primary'},
                'fallback_model': {'value': 'openai/custom-stimmung-fallback'},
                'timeout_s': {'value': 22},
                'temperature': {'value': 0.6},
                'top_p': {'value': 0.77},
                'max_tokens': {'value': 333},
            }
        )
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    '{"schema_version":"v1","present":true,"tones":[{"tone":"curiosite","strength":5}],"dominant_tone":"curiosite","confidence":0.74}'
                )
            ]
        )

        result = stimmung_agent.build_affective_turn_signal(
            user_msg='Je veux un test runtime-backed',
            requests_module=requests_module,
        )

        self.assertEqual(result.model, 'openai/custom-stimmung-primary')
        self.assertEqual(requests_module.calls[0]['json']['model'], 'openai/custom-stimmung-primary')
        self.assertEqual(requests_module.calls[0]['json']['temperature'], 0.6)
        self.assertEqual(requests_module.calls[0]['json']['top_p'], 0.77)
        self.assertEqual(requests_module.calls[0]['json']['max_tokens'], 333)
        self.assertEqual(requests_module.calls[0]['timeout'], 22)
        self.assertEqual(requests_module.calls[0]['headers'], {'Authorization': 'caller=stimmung_agent'})

    def test_build_affective_turn_signal_uses_recent_window_context_with_five_turn_cap(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    '{"schema_version":"v1","present":true,"tones":[{"tone":"neutralite","strength":3}],"dominant_tone":"neutralite","confidence":0.71}'
                )
            ]
        )
        recent_window_input_payload = {
            'schema_version': 'v1',
            'turns': [
                {
                    'turn_status': 'complete',
                    'messages': [
                        {'role': 'user', 'content': 'ancien 0'},
                        {'role': 'assistant', 'content': 'reponse 0'},
                    ],
                },
                {
                    'turn_status': 'complete',
                    'messages': [
                        {'role': 'user', 'content': 'ancien 1'},
                        {'role': 'assistant', 'content': 'reponse 1'},
                    ],
                },
                {
                    'turn_status': 'complete',
                    'messages': [
                        {'role': 'user', 'content': 'ancien 2'},
                        {'role': 'assistant', 'content': 'reponse 2'},
                    ],
                },
                {
                    'turn_status': 'complete',
                    'messages': [
                        {'role': 'user', 'content': 'ancien 3'},
                        {'role': 'assistant', 'content': 'reponse 3'},
                    ],
                },
                {
                    'turn_status': 'complete',
                    'messages': [
                        {'role': 'user', 'content': 'ancien 4'},
                        {'role': 'assistant', 'content': 'reponse 4'},
                    ],
                },
                {
                    'turn_status': 'complete',
                    'messages': [
                        {'role': 'user', 'content': 'ancien 5'},
                        {'role': 'assistant', 'content': 'reponse 5'},
                    ],
                },
                {
                    'turn_status': 'in_progress',
                    'messages': [{'role': 'user', 'content': 'Message courant'}],
                },
            ],
        }

        stimmung_agent.build_affective_turn_signal(
            user_msg='Message courant',
            recent_window_input_payload=recent_window_input_payload,
            requests_module=requests_module,
        )

        request_content = requests_module.calls[0]['json']['messages'][1]['content']
        self.assertIn('Fenetre conversationnelle locale (5 tours max)', request_content)
        self.assertNotIn('ancien 0', request_content)
        self.assertIn('ancien 1', request_content)
        self.assertIn('reponse 5', request_content)
        self.assertIn('Tour utilisateur courant (centre de l\'analyse, signal a produire pour ce tour)', request_content)
        self.assertIn('Message courant', request_content)

    def test_build_messages_keeps_current_turn_centered_without_claiming_stabilized_stimmung(self) -> None:
        messages = stimmung_agent._build_messages(
            system_prompt='SYSTEM PROMPT',
            user_msg='Je suis perdu ici',
            recent_window_input_payload={
                'schema_version': 'v1',
                'turns': [
                    {
                        'turn_status': 'complete',
                        'messages': [
                            {'role': 'user', 'content': 'Avant'},
                            {'role': 'assistant', 'content': 'Reponse avant'},
                        ],
                    }
                ],
            },
        )

        self.assertEqual(messages[0]['content'], 'SYSTEM PROMPT')
        self.assertIn('Fenetre conversationnelle locale (5 tours max)', messages[1]['content'])
        self.assertIn('Avant', messages[1]['content'])
        self.assertIn('Tour utilisateur courant (centre de l\'analyse, signal a produire pour ce tour)', messages[1]['content'])
        self.assertIn('Je suis perdu ici', messages[1]['content'])
        self.assertNotIn('stimmung stabilisee', messages[1]['content'])

    def test_stimmung_contract_ignores_temporal_gaps_and_keeps_timestamps_out(self) -> None:
        prompt = (APP_DIR / 'prompts' / 'stimmung_agent.txt').read_text(encoding='utf-8')
        messages = stimmung_agent._build_messages(
            system_prompt=prompt,
            user_msg='Je suis perdu depuis hier',
            recent_window_input_payload={
                'schema_version': 'v1',
                'turns': [
                    {
                        'turn_status': 'complete',
                        'messages': [
                            {
                                'role': 'user',
                                'content': 'Avant',
                                'timestamp': '2026-05-17T21:00:00Z',
                            },
                            {
                                'role': 'assistant',
                                'content': 'Reponse avant',
                                'timestamp': '2026-05-17T21:01:00Z',
                            },
                        ],
                    }
                ],
            },
        )

        self.assertIn('Tu ignores les timestamps, les delais et les gaps temporels', prompt)
        self.assertNotIn('2026-05-17T21:00:00Z', messages[1]['content'])
        self.assertNotIn('2026-05-17T21:01:00Z', messages[1]['content'])
        self.assertIn("Tour utilisateur courant (centre de l'analyse", messages[1]['content'])

    def test_validate_affective_turn_signal_rejects_tone_outside_taxonomy(self) -> None:
        with self.assertRaises(stimmung_agent._SignalValidationError):
            stimmung_agent._validate_affective_turn_signal(
                {
                    'schema_version': 'v1',
                    'present': True,
                    'tones': [{'tone': 'melancolie', 'strength': 4}],
                    'dominant_tone': 'melancolie',
                    'confidence': 0.6,
                }
            )

    def test_validate_affective_turn_signal_rejects_strength_outside_range(self) -> None:
        with self.assertRaises(stimmung_agent._SignalValidationError):
            stimmung_agent._validate_affective_turn_signal(
                {
                    'schema_version': 'v1',
                    'present': True,
                    'tones': [{'tone': 'confusion', 'strength': 11}],
                    'dominant_tone': 'confusion',
                    'confidence': 0.6,
                }
            )

    def test_validate_affective_turn_signal_rejects_incoherent_dominant_tone(self) -> None:
        with self.assertRaises(stimmung_agent._SignalValidationError):
            stimmung_agent._validate_affective_turn_signal(
                {
                    'schema_version': 'v1',
                    'present': True,
                    'tones': [{'tone': 'confusion', 'strength': 6}],
                    'dominant_tone': 'frustration',
                    'confidence': 0.6,
                }
            )

    def test_build_affective_turn_signal_uses_fallback_after_primary_invalid_json(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse('not json at all'),
                _FakeResponse(
                    '{"schema_version":"v1","present":true,"tones":[{"tone":"neutralite","strength":3}],"dominant_tone":"neutralite","confidence":0.71}'
                ),
            ]
        )

        result = stimmung_agent.build_affective_turn_signal(
            user_msg='Bonjour',
            requests_module=requests_module,
        )

        self.assertEqual(result.status, 'ok')
        self.assertEqual(result.decision_source, 'fallback')
        self.assertEqual(result.model, stimmung_agent.FALLBACK_MODEL)
        self.assertEqual(
            [call['json']['model'] for call in requests_module.calls],
            [stimmung_agent.PRIMARY_MODEL, stimmung_agent.FALLBACK_MODEL],
        )
        self.assertEqual(result.signal['dominant_tone'], 'neutralite')

    def test_build_affective_turn_signal_returns_fail_open_after_double_failure(self) -> None:
        observed: list[dict[str, object]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, object], **_kwargs: object) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-stimmung-fail-open',
            user_msg='Je ne comprends rien',
            web_search_enabled=False,
        )
        requests_module = _FakeRequests(
            [
                _FakeRequests.exceptions.Timeout('primary timeout'),
                _FakeResponse(
                    '{"schema_version":"v1","present":true,"tones":[{"tone":"hors_taxonomie","strength":5}],"dominant_tone":"hors_taxonomie","confidence":0.4}'
                ),
            ]
        )

        try:
            result = stimmung_agent.build_affective_turn_signal(
                user_msg='Je ne comprends rien',
                requests_module=requests_module,
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        self.assertEqual(result.status, 'error')
        self.assertEqual(result.decision_source, 'fail_open')
        self.assertEqual(result.model, stimmung_agent.FALLBACK_MODEL)
        self.assertEqual(result.reason_code, 'validation_error')
        self.assertEqual(
            stimmung_agent._validate_affective_turn_signal(result.signal),
            result.signal,
        )
        self.assertEqual(
            result.signal,
            {
                'schema_version': 'v1',
                'present': False,
                'tones': [],
                'dominant_tone': None,
                'confidence': 0.0,
            },
        )
        prepared_events = [item for item in observed if item['stage'] == 'stimmung_prompt_prepared']
        self.assertEqual(len(prepared_events), 2)
        self.assertEqual(
            [item['payload_json']['attempt_decision_source'] for item in prepared_events],
            ['primary', 'fallback'],
        )
        self.assertTrue(all(item['payload_json']['secondary_provider_payload'] for item in prepared_events))
        self.assertTrue(all(not item['payload_json']['main_llm_payload'] for item in prepared_events))
        self.assertNotIn('Je ne comprends rien', repr([item['payload_json'] for item in prepared_events]))


if __name__ == '__main__':
    unittest.main()
