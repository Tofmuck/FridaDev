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
        requests_module = _FakeRequests(
            [
                _FakeRequests.exceptions.Timeout('primary timeout'),
                _FakeResponse(
                    '{"schema_version":"v1","present":true,"tones":[{"tone":"hors_taxonomie","strength":5}],"dominant_tone":"hors_taxonomie","confidence":0.4}'
                ),
            ]
        )

        result = stimmung_agent.build_affective_turn_signal(
            user_msg='Je ne comprends rien',
            requests_module=requests_module,
        )

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


if __name__ == '__main__':
    unittest.main()
