from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


class ServerPhase5BisSecretRuntimeTests(unittest.TestCase):
    def test_server_uses_runtime_main_model_secret_for_llm_call_flow(self) -> None:
        source = (APP_DIR / 'server.py').read_text()
        self.assertIn("runtime_settings.get_runtime_secret_value('main_model', 'api_key')", source)
        self.assertNotIn('if not config.OR_KEY', source)
        self.assertNotIn('OPENROUTER_API_KEY manquant', source)


if __name__ == '__main__':
    unittest.main()
