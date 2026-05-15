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

from observability import dashboard_content_gate


class DashboardContentGateLot8Tests(unittest.TestCase):
    def test_secondary_llm_call_is_not_classified_as_main_model_payload(self) -> None:
        payload = dashboard_content_gate.build_content_gate_payload(
            fact={'conversation_id': 'conv-1', 'turn_id': 'turn-1'},
            events=[
                {
                    'event_id': 'evt-secondary',
                    'conversation_id': 'conv-1',
                    'turn_id': 'turn-1',
                    'stage': 'llm_call',
                    'status': 'ok',
                    'payload': {
                        'provider_caller': 'validation_agent',
                        'messages': [{'role': 'system', 'content': 'SECONDARY PAYLOAD'}],
                    },
                }
            ],
        )

        by_key = {item['key']: item for item in payload['items']}

        self.assertEqual(by_key['main_model_payload']['status'], 'not_reconstructible')
        self.assertIsNone(by_key['main_model_payload'].get('content_text'))
        self.assertEqual(by_key['secondary_provider_payloads']['status'], 'exact_available')
        self.assertIn('SECONDARY PAYLOAD', by_key['secondary_provider_payloads']['content_text'])

    def test_main_llm_call_still_classifies_as_main_model_payload(self) -> None:
        payload = dashboard_content_gate.build_content_gate_payload(
            fact={'conversation_id': 'conv-1', 'turn_id': 'turn-1'},
            events=[
                {
                    'event_id': 'evt-main',
                    'conversation_id': 'conv-1',
                    'turn_id': 'turn-1',
                    'stage': 'llm_call',
                    'status': 'ok',
                    'payload': {
                        'provider_caller': 'llm',
                        'messages': [{'role': 'system', 'content': 'MAIN PAYLOAD'}],
                    },
                }
            ],
        )

        by_key = {item['key']: item for item in payload['items']}

        self.assertEqual(by_key['main_model_payload']['status'], 'exact_available')
        self.assertIn('MAIN PAYLOAD', by_key['main_model_payload']['content_text'])
        self.assertEqual(by_key['secondary_provider_payloads']['status'], 'not_reconstructible')


if __name__ == '__main__':
    unittest.main()
