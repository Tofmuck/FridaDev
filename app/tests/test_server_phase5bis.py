from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


def _chat_response_call_sites(
    owner_sources: list[tuple[str, str]],
) -> list[str]:
    sites = []
    for filename, source in owner_sources:
        tree = ast.parse(source, filename=filename)
        sites.extend(
            f'{filename}:{node.lineno}'
            for node in ast.walk(tree)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'chat_response'
            )
        )
    return sorted(sites)


class ServerPhase5BisSecretRuntimeTests(unittest.TestCase):
    def test_server_triggers_runtime_secret_env_backfill_at_startup(self) -> None:
        source = (APP_DIR / 'server.py').read_text()
        self.assertIn('runtime_settings.init_runtime_settings_db()', source)
        self.assertIn('runtime_settings.bootstrap_runtime_settings_from_env()', source)
        self.assertIn('runtime_settings.backfill_runtime_secrets_from_env()', source)

    def test_server_uses_runtime_main_model_secret_for_llm_call_flow(self) -> None:
        owner_paths = (
            APP_DIR / 'server.py',
            APP_DIR / 'chat_transport_routes.py',
        )
        owner_sources = [
            (path.name, path.read_text(encoding='utf-8'))
            for path in owner_paths
            if path.is_file()
        ]
        call_sites = _chat_response_call_sites(owner_sources)
        self.assertEqual(len(call_sites), 1, call_sites)

        comment_and_string_only = _chat_response_call_sites(
            [
                (
                    'server.py',
                    "# route.chat_response({})\n"
                    "marker = 'route.chat_response({})'\n",
                )
            ]
        )
        current_owner_only = _chat_response_call_sites(
            [('server.py', 'route.chat_response({})\n')]
        )
        future_owner_only = _chat_response_call_sites(
            [('chat_transport_routes.py', 'route.chat_response({})\n')]
        )
        attribute_without_call = _chat_response_call_sites(
            [('server.py', 'handler = route.chat_response\n')]
        )
        duplicate_same_line = _chat_response_call_sites(
            [('server.py', 'left.chat_response({}); right.chat_response({})\n')]
        )
        duplicate_owners = _chat_response_call_sites(
            [
                ('server.py', 'left.chat_response({})\n'),
                ('chat_transport_routes.py', 'right.chat_response({})\n'),
            ]
        )
        self.assertEqual(comment_and_string_only, [])
        self.assertEqual(len(current_owner_only), 1)
        self.assertEqual(len(future_owner_only), 1)
        self.assertEqual(attribute_without_call, [])
        self.assertEqual(len(duplicate_same_line), 2)
        self.assertEqual(len(duplicate_owners), 2)

        source_chat = (APP_DIR / 'core' / 'chat_service.py').read_text()
        source_llm_flow = (APP_DIR / 'core' / 'chat_llm_flow.py').read_text()
        self.assertIn("runtime_settings_module.get_runtime_secret_value('main_model', 'api_key')", source_llm_flow)
        self.assertNotIn('if not config.OR_KEY', source_chat)
        self.assertNotIn('OPENROUTER_API_KEY manquant', source_chat)
        self.assertNotIn('if not config.OR_KEY', source_llm_flow)
        self.assertNotIn('OPENROUTER_API_KEY manquant', source_llm_flow)


if __name__ == '__main__':
    unittest.main()
