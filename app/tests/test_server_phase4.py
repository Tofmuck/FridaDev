from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


class ServerPhase4MainModelTests(unittest.TestCase):
    def test_server_uses_payload_model_for_llm_call_flow(self) -> None:
        source_server = (APP_DIR / 'server.py').read_text()
        source_chat = (APP_DIR / 'core' / 'chat_service.py').read_text()
        source_llm_flow = (APP_DIR / 'core' / 'chat_llm_flow.py').read_text()
        self.assertIn('chat_service.chat_response(', source_server)
        self.assertIn("call_model = str(payload['model'])", source_llm_flow)
        self.assertIn('model=call_model', source_llm_flow)
        self.assertNotIn('model   = config.OR_MODEL', source_chat)
        self.assertNotIn('model = config.OR_MODEL', source_chat)
        self.assertNotIn('model   = config.OR_MODEL', source_llm_flow)
        self.assertNotIn('model = config.OR_MODEL', source_llm_flow)

    def test_server_uses_runtime_main_model_for_token_count_flow(self) -> None:
        source_chat = (APP_DIR / 'core' / 'chat_service.py').read_text()
        source_llm_flow = (APP_DIR / 'core' / 'chat_llm_flow.py').read_text()
        self.assertIn('runtime_main_view = runtime_settings_module.get_main_model_settings()', source_chat)
        self.assertIn("runtime_main_model = str(runtime_main_payload['model']['value'])", source_chat)
        self.assertIn("token_utils_module.estimate_tokens([{'content': user_msg}], runtime_main_model)", source_chat)
        self.assertIn('summarizer_module.maybe_summarize(conversation, runtime_main_model)', source_chat)
        self.assertIn("token_utils_module.estimate_tokens([{'content': text}], runtime_main_model)", source_llm_flow)
        self.assertIn("token_utils_module.estimate_tokens(", source_llm_flow)
        self.assertNotIn('config.OR_MODEL', source_chat)
        self.assertNotIn('config.OR_MODEL', source_llm_flow)


if __name__ == '__main__':
    unittest.main()
