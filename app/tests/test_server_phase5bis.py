from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


class ServerPhase5BisSecretRuntimeTests(unittest.TestCase):
    def test_server_triggers_runtime_secret_env_backfill_at_startup(self) -> None:
        source = (APP_DIR / 'server.py').read_text()
        self.assertIn('runtime_settings.init_runtime_settings_db()', source)
        self.assertIn('runtime_settings.bootstrap_runtime_settings_from_env()', source)
        self.assertIn('runtime_settings.backfill_runtime_secrets_from_env()', source)

    def test_server_uses_runtime_main_model_secret_for_llm_call_flow(self) -> None:
        source_server = (APP_DIR / 'server.py').read_text()
        source_chat = (APP_DIR / 'core' / 'chat_service.py').read_text()
        source_llm_flow = (APP_DIR / 'core' / 'chat_llm_flow.py').read_text()
        self.assertIn('chat_service.chat_response(', source_server)
        self.assertIn("runtime_settings_module.get_runtime_secret_value('main_model', 'api_key')", source_llm_flow)
        self.assertNotIn('if not config.OR_KEY', source_chat)
        self.assertNotIn('OPENROUTER_API_KEY manquant', source_chat)
        self.assertNotIn('if not config.OR_KEY', source_llm_flow)
        self.assertNotIn('OPENROUTER_API_KEY manquant', source_llm_flow)


if __name__ == '__main__':
    unittest.main()
