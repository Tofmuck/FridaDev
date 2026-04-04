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

    def test_build_context_keeps_legacy_contract_when_context_is_truncated(self) -> None:
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_format_context = web_search._format_context

        web_search.reformulate = lambda _user_msg: 'query tronquee'
        web_search.search = lambda _query: [
            {'title': 'A', 'url': 'https://a.example', 'content': 'a'},
        ]
        web_search._format_context = lambda query, _results: f'CTX::{query}::[...contenu tronqué]'
        try:
            context, query, result_count = web_search.build_context('question initiale')
        finally:
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._format_context = original_format_context

        self.assertEqual(context, 'CTX::query tronquee::[...contenu tronqué]')
        self.assertEqual(query, 'query tronquee')
        self.assertEqual(result_count, 1)

    def test_build_context_payload_reads_explicit_url_before_generic_search_when_crawl_succeeds(self) -> None:
        url = 'https://example.com/article'
        observed_calls: list[tuple[str, str]] = []
        original_runtime_services_value = web_search._runtime_services_value
        original_crawl_with_status = web_search.crawl_with_status
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_emit = web_search._emit_web_search_runtime_event

        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 2,
            'crawl4ai_max_chars': 40,
        }[field]

        def fake_crawl_with_status(input_url: str):
            observed_calls.append(('crawl', input_url))
            return {
                'status': 'success',
                'markdown': 'contenu primaire ' * 10,
                'error_class': None,
            }

        def fail_reformulate(_user_msg: str) -> str:
            raise AssertionError('generic search should not run when explicit URL crawl succeeds')

        def fail_search(_query: str):
            raise AssertionError('search() should not run when explicit URL crawl succeeds')

        web_search.crawl_with_status = fake_crawl_with_status
        web_search.reformulate = fail_reformulate
        web_search.search = fail_search
        web_search._emit_web_search_runtime_event = lambda **_kwargs: None
        try:
            payload = web_search.build_context_payload(f'Tu peux lire ceci : {url}')
        finally:
            web_search._runtime_services_value = original_runtime_services_value
            web_search.crawl_with_status = original_crawl_with_status
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._emit_web_search_runtime_event = original_emit

        self.assertEqual(observed_calls, [('crawl', url)])
        self.assertTrue(payload['explicit_url_detected'])
        self.assertEqual(payload['explicit_url'], url)
        self.assertEqual(payload['primary_source_kind'], 'explicit_url')
        self.assertTrue(payload['primary_read_attempted'])
        self.assertEqual(payload['primary_read_status'], 'success')
        self.assertFalse(payload['fallback_used'])
        self.assertEqual(payload['collection_path'], 'explicit_url_direct')
        self.assertEqual(payload['query'], '')
        self.assertEqual(payload['results_count'], 1)
        self.assertEqual(payload['sources'][0]['source_origin'], 'explicit_url')
        self.assertTrue(payload['sources'][0]['is_primary_source'])
        self.assertEqual(payload['sources'][0]['crawl_status'], 'success')
        self.assertEqual(payload['sources'][0]['used_content_kind'], 'crawl_markdown')
        self.assertIn('URL explicite fournie par l\'utilisateur', payload['context_block'])

    def test_build_context_payload_tries_explicit_url_before_search_fallback(self) -> None:
        url = 'https://example.com/article'
        observed_calls: list[tuple[str, str]] = []
        original_runtime_services_value = web_search._runtime_services_value
        original_crawl_with_status = web_search.crawl_with_status
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_emit = web_search._emit_web_search_runtime_event

        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 0,
            'crawl4ai_max_chars': 80,
        }[field]

        def fake_crawl_with_status(input_url: str):
            observed_calls.append(('crawl', input_url))
            return {
                'status': 'empty',
                'markdown': '',
                'error_class': None,
            }

        def fake_reformulate(user_msg: str) -> str:
            observed_calls.append(('reformulate', user_msg))
            return 'requete fallback'

        def fake_search(query: str):
            observed_calls.append(('search', query))
            return [
                {
                    'title': 'Source fallback',
                    'url': 'https://fallback.example/article',
                    'content': 'resume fallback',
                }
            ]

        web_search.crawl_with_status = fake_crawl_with_status
        web_search.reformulate = fake_reformulate
        web_search.search = fake_search
        web_search._emit_web_search_runtime_event = lambda **_kwargs: None
        try:
            payload = web_search.build_context_payload(f'Tu peux lire ceci : {url}')
        finally:
            web_search._runtime_services_value = original_runtime_services_value
            web_search.crawl_with_status = original_crawl_with_status
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._emit_web_search_runtime_event = original_emit

        self.assertEqual([step[0] for step in observed_calls], ['crawl', 'reformulate', 'search'])
        self.assertTrue(payload['explicit_url_detected'])
        self.assertEqual(payload['explicit_url'], url)
        self.assertEqual(payload['primary_source_kind'], 'explicit_url')
        self.assertTrue(payload['primary_read_attempted'])
        self.assertEqual(payload['primary_read_status'], 'empty')
        self.assertTrue(payload['fallback_used'])
        self.assertEqual(payload['collection_path'], 'explicit_url_fallback_search')
        self.assertEqual(payload['query'], 'requete fallback')
        self.assertEqual(payload['results_count'], 1)
        self.assertEqual(payload['sources'][0]['source_origin'], 'search_result')
        self.assertFalse(payload['sources'][0]['is_primary_source'])
        self.assertEqual(payload['sources'][0]['crawl_status'], 'not_attempted')
        self.assertEqual(payload['sources'][0]['used_content_kind'], 'search_snippet')
        self.assertIn("Lecture directe tentee d'abord : empty.", payload['context_block'])


if __name__ == '__main__':
    unittest.main()
