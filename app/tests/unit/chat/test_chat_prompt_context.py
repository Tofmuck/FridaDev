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

from core import chat_prompt_context


class ChatPromptContextTests(unittest.TestCase):
    def test_resolve_backend_prompts_uses_prompt_loader_authority(self) -> None:
        loader = SimpleNamespace(
            get_main_system_prompt=lambda: 'BACKEND SYSTEM PROMPT',
            get_main_hermeneutical_prompt=lambda: 'BACKEND HERMENEUTICAL PROMPT',
        )

        system_prompt, hermeneutical_prompt = chat_prompt_context.resolve_backend_prompts(loader)

        self.assertEqual(system_prompt, 'BACKEND SYSTEM PROMPT')
        self.assertEqual(hermeneutical_prompt, 'BACKEND HERMENEUTICAL PROMPT')

    def test_build_augmented_system_keeps_expected_order(self) -> None:
        identity_module = SimpleNamespace(
            build_identity_block=lambda: ('[IDENTITY BLOCK]', ['id-a', 'id-b']),
        )
        config_module = SimpleNamespace(FRIDA_TIMEZONE='Europe/Paris')

        augmented_system, identity_ids = chat_prompt_context.build_augmented_system(
            system_prompt='BACKEND SYSTEM PROMPT',
            hermeneutical_prompt='BACKEND HERMENEUTICAL PROMPT',
            config_module=config_module,
            identity_module=identity_module,
        )

        self.assertEqual(identity_ids, ['id-a', 'id-b'])
        self.assertIn('BACKEND SYSTEM PROMPT', augmented_system)
        self.assertIn('BACKEND HERMENEUTICAL PROMPT', augmented_system)
        self.assertIn('[RÉFÉRENCE TEMPORELLE]', augmented_system)
        self.assertIn('[IDENTITY BLOCK]', augmented_system)
        self.assertLess(
            augmented_system.index('BACKEND SYSTEM PROMPT'),
            augmented_system.index('BACKEND HERMENEUTICAL PROMPT'),
        )
        self.assertLess(
            augmented_system.index('BACKEND HERMENEUTICAL PROMPT'),
            augmented_system.index('[RÉFÉRENCE TEMPORELLE]'),
        )
        self.assertLess(
            augmented_system.index('[RÉFÉRENCE TEMPORELLE]'),
            augmented_system.index('[IDENTITY BLOCK]'),
        )

    def test_apply_augmented_system_overwrites_first_system_message_only(self) -> None:
        conversation = {
            'messages': [
                {'role': 'system', 'content': 'old system'},
                {'role': 'user', 'content': 'hello'},
            ]
        }

        chat_prompt_context.apply_augmented_system(conversation, 'new augmented system')

        self.assertEqual(conversation['messages'][0]['content'], 'new augmented system')
        self.assertEqual(conversation['messages'][1]['content'], 'hello')

    def test_inject_web_context_targets_last_user_message_and_logs_event(self) -> None:
        prompt_messages = [
            {'role': 'user', 'content': 'first user'},
            {'role': 'assistant', 'content': 'assistant'},
            {'role': 'user', 'content': 'last user'},
        ]
        observed_logs = []

        web_search_module = SimpleNamespace(
            build_context=lambda _user_msg: ('WEB CONTEXT', 'query test', 3),
        )
        admin_logs_module = SimpleNamespace(
            log_event=lambda event, **kwargs: observed_logs.append((event, kwargs)),
        )

        chat_prompt_context.inject_web_context(
            prompt_messages,
            user_msg='Bonjour',
            conversation_id='conv-ctx',
            web_search_module=web_search_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(prompt_messages[0]['content'], 'first user')
        self.assertEqual(prompt_messages[2]['content'], 'WEB CONTEXT\n\nQuestion : last user')
        self.assertEqual(len(observed_logs), 1)
        event, payload = observed_logs[0]
        self.assertEqual(event, 'web_search')
        self.assertEqual(payload['conversation_id'], 'conv-ctx')
        self.assertEqual(payload['query'], 'query test')
        self.assertEqual(payload['original'], 'Bonjour')
        self.assertEqual(payload['results'], 3)
        self.assertNotIn('ticketmaster', payload)

    def test_inject_web_context_skips_when_no_context(self) -> None:
        prompt_messages = [{'role': 'user', 'content': 'last user'}]
        observed_logs = []

        web_search_module = SimpleNamespace(
            build_context=lambda _user_msg: ('', 'query ignored', 0),
        )
        admin_logs_module = SimpleNamespace(
            log_event=lambda event, **kwargs: observed_logs.append((event, kwargs)),
        )

        chat_prompt_context.inject_web_context(
            prompt_messages,
            user_msg='Bonjour',
            conversation_id='conv-ctx',
            web_search_module=web_search_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(prompt_messages[0]['content'], 'last user')
        self.assertEqual(observed_logs, [])


if __name__ == '__main__':
    unittest.main()
