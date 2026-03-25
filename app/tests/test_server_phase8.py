from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


class ServerPhase8Tests(unittest.TestCase):
    def test_api_chat_uses_runtime_sampling_settings(self) -> None:
        source = (APP_DIR / "server.py").read_text(encoding="utf-8")

        self.assertNotIn('data.get("temperature")', source)
        self.assertNotIn('data.get("top_p")', source)
        self.assertIn("runtime_main_payload['temperature']['value']", source)
        self.assertIn("runtime_main_payload['top_p']['value']", source)
        self.assertIn('data.get("max_tokens")', source)


if __name__ == "__main__":
    unittest.main()
