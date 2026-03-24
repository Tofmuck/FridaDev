from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


class ServerPhase4MainModelTests(unittest.TestCase):
    def test_server_uses_payload_model_for_llm_call_flow(self) -> None:
        source = (APP_DIR / 'server.py').read_text()
        self.assertIn('call_model = str(payload["model"])', source)
        self.assertIn('model=call_model', source)
        self.assertNotIn('model   = config.OR_MODEL', source)
        self.assertNotIn('model = config.OR_MODEL', source)

    def test_server_keeps_token_count_uses_separate_for_now(self) -> None:
        source = (APP_DIR / 'server.py').read_text()
        self.assertIn('token_utils.count_tokens([{"content": user_msg}], config.OR_MODEL)', source)
        self.assertIn('summarizer.maybe_summarize(conversation, config.OR_MODEL)', source)
        self.assertIn('config.OR_MODEL,', source)


if __name__ == '__main__':
    unittest.main()
