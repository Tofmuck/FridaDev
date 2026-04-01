from __future__ import annotations

import sys
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
        return {'choices': [{'message': {'content': self._content}}]}


class StimmungAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_read_prompt = stimmung_agent.prompt_loader.read_prompt_text
        self.original_or_headers = stimmung_agent.llm_client.or_headers
        stimmung_agent.prompt_loader.read_prompt_text = lambda _path: 'SYSTEM PROMPT'
        stimmung_agent.llm_client.or_headers = lambda caller='llm': {'Authorization': f'caller={caller}'}

    def tearDown(self) -> None:
        stimmung_agent.prompt_loader.read_prompt_text = self.original_read_prompt
        stimmung_agent.llm_client.or_headers = self.original_or_headers

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
        self.assertEqual(requests_module.calls[0]['headers'], {'Authorization': 'caller=llm'})

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
            result.signal,
            {
                'schema_version': 'v1',
                'present': False,
                'tones': [],
                'dominant_tone': None,
                'confidence': 0.0,
                'reason_code': 'validation_error',
            },
        )


if __name__ == '__main__':
    unittest.main()
