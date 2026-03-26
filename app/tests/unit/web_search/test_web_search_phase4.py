from __future__ import annotations

import sys
import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from tools import web_search
import config


class WebSearchPhase4MainModelTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_reformulate_uses_runtime_main_model_from_db_when_present(self) -> None:
        observed = {'model': None}
        original_get_settings = web_search.runtime_settings.get_main_model_settings
        original_post = web_search.requests.post

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openai/gpt-5.4-mini', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'referer': {'value': 'https://frida-system.fr', 'origin': 'db'},
                        'app_name': {'value': 'FridaDev', 'origin': 'db'},
                        'title_llm': {'value': 'FridaDev/LLM', 'origin': 'db'},
                        'title_arbiter': {'value': 'FridaDev/Arbiter', 'origin': 'db'},
                        'title_resumer': {'value': 'FridaDev/Resumer', 'origin': 'db'},
                        'temperature': {'value': 0.4, 'origin': 'db'},
                        'top_p': {'value': 1.0, 'origin': 'db'},
                    },
                ),
                source='db',
                source_reason='db_row',
            )

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {"choices": [{"message": {"content": "requete test"}}]}

        def fake_post(url, json, headers, timeout):
            observed['model'] = json['model']
            return FakeResponse()

        web_search.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        web_search.requests.post = fake_post
        try:
            query = web_search.reformulate('actualites ia')
        finally:
            web_search.runtime_settings.get_main_model_settings = original_get_settings
            web_search.requests.post = original_post

        self.assertEqual(query, 'requete test')
        self.assertEqual(observed['model'], 'openai/gpt-5.4-mini')

    def test_reformulate_keeps_env_fallback_when_db_row_is_missing(self) -> None:
        observed = {'model': None}
        original_get_settings = web_search.runtime_settings.get_main_model_settings
        original_post = web_search.requests.post

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.build_env_seed_bundle('main_model').payload,
                source='env',
                source_reason='empty_table',
            )

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {"choices": [{"message": {"content": "requete fallback"}}]}

        def fake_post(url, json, headers, timeout):
            observed['model'] = json['model']
            return FakeResponse()

        web_search.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        web_search.requests.post = fake_post
        try:
            query = web_search.reformulate('actualites ia')
        finally:
            web_search.runtime_settings.get_main_model_settings = original_get_settings
            web_search.requests.post = original_post

        self.assertEqual(query, 'requete fallback')
        self.assertEqual(observed['model'], config.OR_MODEL)

    def test_build_context_keeps_context_query_and_result_count_contract(self) -> None:
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_format_context = web_search._format_context

        web_search.reformulate = lambda _user_msg: 'query reformulee'
        web_search.search = lambda _query: [
            {'title': 'A', 'url': 'https://a.example', 'content': 'a'},
            {'title': 'B', 'url': 'https://b.example', 'content': 'b'},
        ]
        web_search._format_context = lambda query, results: f'CTX::{query}::{len(results)}'
        try:
            context, query, result_count = web_search.build_context('question initiale')
        finally:
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._format_context = original_format_context

        self.assertEqual(context, 'CTX::query reformulee::2')
        self.assertEqual(query, 'query reformulee')
        self.assertEqual(result_count, 2)


if __name__ == '__main__':
    unittest.main()
