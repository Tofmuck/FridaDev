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

from core import chat_turn_runtime_inputs


class ChatTurnRuntimeInputsWebTimeTests(unittest.TestCase):
    def test_web_runtime_payload_forwards_turn_now_iso(self) -> None:
        observed = {}

        def fake_build_context_payload(_user_msg, **kwargs):
            observed.update(kwargs)
            return {
                'enabled': True,
                'status': 'ok',
                'reason_code': None,
                'original_user_message': 'cherche',
                'query': 'requete',
                'results_count': 1,
                'runtime': {},
                'sources': [],
                'context_block': 'WEB',
            }

        payload = chat_turn_runtime_inputs.resolve_web_runtime_payload(
            user_msg='cherche',
            web_search_on=True,
            web_search_module=SimpleNamespace(build_context_payload=fake_build_context_payload),
            requests_module=SimpleNamespace(),
            llm_module=SimpleNamespace(),
            now_iso='2026-05-17T22:05:00Z',
        )

        self.assertEqual(observed['now_iso'], '2026-05-17T22:05:00Z')
        self.assertEqual(payload['activation_mode'], 'manual')


if __name__ == '__main__':
    unittest.main()
