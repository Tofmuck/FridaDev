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

from admin import runtime_settings
from tools import web_search
import config


class WebSearchPhase4WebReformulationModelTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_reformulate_uses_runtime_web_reformulation_model_from_db_when_present(self) -> None:
        observed = {'model': None, 'temperature': None, 'max_tokens': None, 'timeout': None}
        original_get_settings = web_search.web_reformulation_settings.runtime_settings.get_web_reformulation_model_settings
        original_post = web_search.requests.post

        def fake_get_web_reformulation_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='web_reformulation_model',
                payload=runtime_settings.normalize_stored_payload(
                    'web_reformulation_model',
                    {
                        'model': {'value': 'openai/gpt-5.4-mini', 'origin': 'db'},
                        'temperature': {'value': 0.2, 'origin': 'db'},
                        'max_tokens': {'value': 40, 'origin': 'db'},
                        'timeout_s': {'value': 10, 'origin': 'db'},
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
            observed['temperature'] = json['temperature']
            observed['max_tokens'] = json['max_tokens']
            observed['timeout'] = timeout
            return FakeResponse()

        web_search.web_reformulation_settings.runtime_settings.get_web_reformulation_model_settings = fake_get_web_reformulation_model_settings
        web_search.requests.post = fake_post
        try:
            query = web_search.reformulate('actualites ia')
        finally:
            web_search.web_reformulation_settings.runtime_settings.get_web_reformulation_model_settings = original_get_settings
            web_search.requests.post = original_post

        self.assertEqual(query, 'requete test')
        self.assertEqual(observed['model'], 'openai/gpt-5.4-mini')
        self.assertEqual(observed['temperature'], 0.2)
        self.assertEqual(observed['max_tokens'], 40)
        self.assertEqual(observed['timeout'], 10)

    def test_reformulate_default_is_not_coupled_to_runtime_main_model(self) -> None:
        observed = {'model': None, 'timeout': None}
        original_get_web_settings = web_search.web_reformulation_settings.runtime_settings.get_web_reformulation_model_settings

        def fake_get_web_reformulation_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='web_reformulation_model',
                payload=runtime_settings.build_env_seed_bundle('web_reformulation_model').payload,
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
            observed['timeout'] = timeout
            return FakeResponse()

        fake_llm_module = SimpleNamespace(
            or_chat_completions_url=lambda: 'https://openrouter.example/chat/completions',
            or_headers=lambda *, caller='llm': {'X-Frida-Caller': caller},
            read_openrouter_response_payload=lambda response: response.json(),
            extract_openrouter_text=lambda payload: payload['choices'][0]['message']['content'],
        )

        web_search.web_reformulation_settings.runtime_settings.get_web_reformulation_model_settings = fake_get_web_reformulation_model_settings
        try:
            query = web_search.reformulate(
                'actualites ia',
                requests_module=SimpleNamespace(post=fake_post),
                llm_module=fake_llm_module,
            )
        finally:
            web_search.web_reformulation_settings.runtime_settings.get_web_reformulation_model_settings = original_get_web_settings

        self.assertEqual(query, 'requete fallback')
        self.assertEqual(observed['model'], config.WEB_REFORMULATION_MODEL)
        self.assertEqual(observed['timeout'], config.WEB_REFORMULATION_TIMEOUT_S)

    def test_reformulate_uses_dedicated_web_reformulation_caller(self) -> None:
        observed = {
            'url': None,
            'headers': None,
            'timeout': None,
            'caller': None,
        }

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {"choices": [{"message": {"content": "requete web"}}]}

        def fake_post(url, json, headers, timeout):
            observed['url'] = url
            observed['headers'] = dict(headers)
            observed['timeout'] = timeout
            observed['model'] = json['model']
            return FakeResponse()

        def fake_or_headers(*, caller='llm'):
            observed['caller'] = caller
            return {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer sk-runtime',
                'X-Frida-Caller': caller,
                'X-Title': 'FridaDev/WebReformulation',
                'X-OpenRouter-Title': 'FridaDev/WebReformulation',
            }

        fake_llm_module = SimpleNamespace(
            or_chat_completions_url=lambda: 'https://openrouter.example/chat/completions',
            or_headers=fake_or_headers,
            read_openrouter_response_payload=lambda response: response.json(),
            extract_openrouter_text=lambda payload: payload['choices'][0]['message']['content'],
        )

        query = web_search.reformulate(
            'actualites ia',
            requests_module=SimpleNamespace(post=fake_post),
            llm_module=fake_llm_module,
        )

        self.assertEqual(query, 'requete web')
        self.assertEqual(observed['url'], 'https://openrouter.example/chat/completions')
        self.assertEqual(observed['timeout'], 10)
        self.assertEqual(observed['caller'], 'web_reformulation')
        self.assertEqual(observed['headers']['X-Frida-Caller'], 'web_reformulation')
        self.assertEqual(observed['headers']['X-Title'], 'FridaDev/WebReformulation')

    def test_reformulate_uses_frida_local_date_around_midnight(self) -> None:
        observed = {'system_prompt': ''}

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {"choices": [{"message": {"content": "requete locale"}}]}

        def fake_post(_url, json, headers, timeout):
            _ = headers, timeout
            observed['system_prompt'] = json['messages'][0]['content']
            return FakeResponse()

        fake_llm_module = SimpleNamespace(
            or_chat_completions_url=lambda: 'https://openrouter.example/chat/completions',
            or_headers=lambda *, caller='llm': {'X-Frida-Caller': caller},
            read_openrouter_response_payload=lambda response: response.json(),
            extract_openrouter_text=lambda payload: payload['choices'][0]['message']['content'],
        )

        query = web_search.reformulate(
            'actualites du jour',
            requests_module=SimpleNamespace(post=fake_post),
            llm_module=fake_llm_module,
            now_iso='2026-05-17T22:05:00Z',
        )

        self.assertEqual(query, 'requete locale')
        self.assertIn('Nous sommes le lundi 18 mai 2026 Europe/Paris.', observed['system_prompt'])
        self.assertNotIn('17 May 2026', observed['system_prompt'])
        self.assertNotIn('17 mai 2026', observed['system_prompt'])

    def test_web_context_blocks_use_frida_local_date_around_midnight(self) -> None:
        original_runtime_services_value = web_search._runtime_services_value
        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 0,
            'crawl4ai_max_chars': 400,
            'crawl4ai_explicit_url_max_chars': 400,
        }[field]
        try:
            search_material = web_search._build_search_context_material(
                'requete',
                [{'title': 'A', 'url': 'https://a.example', 'content': 'snippet'}],
                now_iso='2026-05-17T22:05:00Z',
            )
            explicit_material = web_search._build_explicit_url_context_material(
                'https://a.example',
                'contenu lu',
                now_iso='2026-05-17T22:05:00Z',
            )
        finally:
            web_search._runtime_services_value = original_runtime_services_value

        expected_header = '[RECHERCHE WEB — lundi 18 mai 2026 Europe/Paris]'
        self.assertEqual(search_material['context_block'].splitlines()[0], expected_header)
        self.assertEqual(explicit_material['context_block'].splitlines()[0], expected_header)
        self.assertNotIn('17 May 2026', search_material['context_block'])
        self.assertNotIn('17 mai 2026', search_material['context_block'])
        self.assertNotIn('17 May 2026', explicit_material['context_block'])
        self.assertNotIn('17 mai 2026', explicit_material['context_block'])

    def test_search_error_log_does_not_expose_raw_query(self) -> None:
        original_get = web_search.requests.get
        raw_query = 'requete privee sensible'

        def fail_get(*_args, **_kwargs):
            raise RuntimeError('searxng down')

        web_search.requests.get = fail_get
        try:
            with self.assertLogs('frida.web_search', level='WARNING') as captured:
                results = web_search.search(raw_query)
        finally:
            web_search.requests.get = original_get

        self.assertEqual(results, [])
        joined = '\n'.join(captured.output)
        self.assertIn('search_error', joined)
        self.assertIn(f'query_chars={len(raw_query)}', joined)
        self.assertRegex(joined, r'query_sha256_12=[0-9a-f]{12}')
        self.assertIn('error_class=RuntimeError', joined)
        self.assertIn('reason_code=searxng_request_failed', joined)
        self.assertNotIn(raw_query, joined)
        self.assertNotIn('query=', joined)
        self.assertNotIn('err=', joined)

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
        original_crawl_markdown_with_status = web_search._crawl_markdown_with_status
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_emit = web_search._emit_web_search_runtime_event

        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 2,
            'crawl4ai_max_chars': 400,
        }[field]

        def fake_crawl_markdown_with_status(input_url: str, *, filter_type: str = 'fit', query: str | None = None):
            observed_calls.append((filter_type, input_url))
            return {
                'status': 'success',
                'markdown': 'contenu primaire court',
                'error_class': None,
                'filter': filter_type,
            }

        def fail_reformulate(_user_msg: str) -> str:
            raise AssertionError('generic search should not run when explicit URL crawl succeeds')

        def fail_search(_query: str):
            raise AssertionError('search() should not run when explicit URL crawl succeeds')

        web_search._crawl_markdown_with_status = fake_crawl_markdown_with_status
        web_search.reformulate = fail_reformulate
        web_search.search = fail_search
        web_search._emit_web_search_runtime_event = lambda **_kwargs: None
        try:
            payload = web_search.build_context_payload(f'Tu peux lire ceci : {url}')
        finally:
            web_search._runtime_services_value = original_runtime_services_value
            web_search._crawl_markdown_with_status = original_crawl_markdown_with_status
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._emit_web_search_runtime_event = original_emit

        self.assertEqual(observed_calls, [('fit', url)])
        self.assertTrue(payload['explicit_url_detected'])
        self.assertEqual(payload['explicit_url'], url)
        self.assertEqual(payload['primary_source_kind'], 'explicit_url')
        self.assertTrue(payload['primary_read_attempted'])
        self.assertEqual(payload['primary_read_status'], 'success')
        self.assertEqual(payload['primary_read_filter'], 'fit')
        self.assertFalse(payload['primary_read_raw_fallback_used'])
        self.assertEqual(payload['read_state'], 'page_read')
        self.assertFalse(payload['fallback_used'])
        self.assertEqual(payload['collection_path'], 'explicit_url_direct')
        self.assertEqual(payload['query'], '')
        self.assertEqual(payload['results_count'], 1)
        self.assertEqual(payload['sources'][0]['source_origin'], 'explicit_url')
        self.assertTrue(payload['sources'][0]['is_primary_source'])
        self.assertEqual(payload['sources'][0]['crawl_status'], 'success')
        self.assertEqual(payload['sources'][0]['used_content_kind'], 'crawl_markdown')
        self.assertEqual(payload['used_content_kinds'], ['crawl_markdown'])
        self.assertEqual(payload['injected_chars'], len(payload['sources'][0]['content_used']))
        self.assertEqual(payload['context_chars'], len(payload['context_block']))
        self.assertEqual(payload['source_material_summary'][0]['used_content_kind'], 'crawl_markdown')
        self.assertEqual(payload['source_material_summary'][0]['content_chars'], len(payload['sources'][0]['content_used']))
        self.assertIn('URL explicite fournie par l\'utilisateur', payload['context_block'])

    def test_build_context_payload_marks_explicit_url_as_partially_read_when_direct_content_is_truncated(self) -> None:
        url = 'https://example.com/article'
        original_runtime_services_value = web_search._runtime_services_value
        original_crawl_markdown_with_status = web_search._crawl_markdown_with_status
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_emit = web_search._emit_web_search_runtime_event

        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 2,
            'crawl4ai_max_chars': 20,
        }[field]
        web_search._crawl_markdown_with_status = lambda _url, *, filter_type='fit', query=None: {
            'status': 'success',
            'markdown': 'contenu primaire ' * 10,
            'error_class': None,
            'filter': filter_type,
        }
        web_search.reformulate = lambda _msg: (_ for _ in ()).throw(
            AssertionError('generic search should not run when explicit URL crawl succeeds')
        )
        web_search.search = lambda _query: (_ for _ in ()).throw(
            AssertionError('search should not run when explicit URL crawl succeeds')
        )
        web_search._emit_web_search_runtime_event = lambda **_kwargs: None
        try:
            payload = web_search.build_context_payload(f'Tu peux lire ceci : {url}')
        finally:
            web_search._runtime_services_value = original_runtime_services_value
            web_search._crawl_markdown_with_status = original_crawl_markdown_with_status
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._emit_web_search_runtime_event = original_emit

        self.assertEqual(payload['read_state'], 'page_partially_read')
        self.assertEqual(payload['primary_read_filter'], 'fit')
        self.assertFalse(payload['primary_read_raw_fallback_used'])
        self.assertTrue(payload['sources'][0]['truncated'])
        self.assertEqual(payload['sources'][0]['used_content_kind'], 'crawl_markdown')
        self.assertEqual(payload['used_content_kinds'], ['crawl_markdown'])
        self.assertTrue(payload['source_material_summary'][0]['truncated'])

    def test_build_context_payload_uses_explicit_url_budget_distinct_from_search_budget(self) -> None:
        url = 'https://example.com/article'
        original_runtime_services_value = web_search._runtime_services_value
        original_crawl_markdown_with_status = web_search._crawl_markdown_with_status
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_emit = web_search._emit_web_search_runtime_event

        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 2,
            'crawl4ai_max_chars': 5000,
            'crawl4ai_explicit_url_max_chars': 25000,
        }[field]
        web_search._crawl_markdown_with_status = lambda _url, *, filter_type='fit', query=None: {
            'status': 'success',
            'markdown': 'x' * 18000,
            'error_class': None,
            'filter': filter_type,
        }
        web_search.reformulate = lambda _msg: (_ for _ in ()).throw(
            AssertionError('generic search should not run when explicit URL crawl succeeds')
        )
        web_search.search = lambda _query: (_ for _ in ()).throw(
            AssertionError('search should not run when explicit URL crawl succeeds')
        )
        web_search._emit_web_search_runtime_event = lambda **_kwargs: None
        try:
            payload = web_search.build_context_payload(f'Tu peux lire ceci : {url}')
        finally:
            web_search._runtime_services_value = original_runtime_services_value
            web_search._crawl_markdown_with_status = original_crawl_markdown_with_status
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._emit_web_search_runtime_event = original_emit

        self.assertEqual(payload['collection_path'], 'explicit_url_direct')
        self.assertEqual(payload['read_state'], 'page_read')
        self.assertFalse(payload['sources'][0]['truncated'])
        self.assertEqual(len(payload['sources'][0]['content_used']), 18000)

    def test_build_context_payload_keeps_explicit_url_partially_read_when_content_exceeds_explicit_budget(self) -> None:
        url = 'https://example.com/article'
        original_runtime_services_value = web_search._runtime_services_value
        original_crawl_markdown_with_status = web_search._crawl_markdown_with_status
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_emit = web_search._emit_web_search_runtime_event

        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 2,
            'crawl4ai_max_chars': 5000,
            'crawl4ai_explicit_url_max_chars': 25000,
        }[field]
        web_search._crawl_markdown_with_status = lambda _url, *, filter_type='fit', query=None: {
            'status': 'success',
            'markdown': 'x' * 26000,
            'error_class': None,
            'filter': filter_type,
        }
        web_search.reformulate = lambda _msg: (_ for _ in ()).throw(
            AssertionError('generic search should not run when explicit URL crawl succeeds')
        )
        web_search.search = lambda _query: (_ for _ in ()).throw(
            AssertionError('search should not run when explicit URL crawl succeeds')
        )
        web_search._emit_web_search_runtime_event = lambda **_kwargs: None
        try:
            payload = web_search.build_context_payload(f'Tu peux lire ceci : {url}')
        finally:
            web_search._runtime_services_value = original_runtime_services_value
            web_search._crawl_markdown_with_status = original_crawl_markdown_with_status
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._emit_web_search_runtime_event = original_emit

        self.assertEqual(payload['collection_path'], 'explicit_url_direct')
        self.assertEqual(payload['read_state'], 'page_partially_read')
        self.assertTrue(payload['sources'][0]['truncated'])
        self.assertEqual(
            payload['sources'][0]['content_used'],
            ('x' * 25000) + "\n[...contenu tronqué]",
        )

    def test_build_context_payload_tries_fit_then_raw_before_search_fallback(self) -> None:
        url = 'https://example.com/article'
        observed_calls: list[tuple[str, str]] = []
        original_runtime_services_value = web_search._runtime_services_value
        original_crawl_markdown_with_status = web_search._crawl_markdown_with_status
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_emit = web_search._emit_web_search_runtime_event

        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 0,
            'crawl4ai_max_chars': 80,
        }[field]

        def fake_crawl_markdown_with_status(input_url: str, *, filter_type: str = 'fit', query: str | None = None):
            observed_calls.append((filter_type, input_url))
            return {
                'status': 'empty',
                'markdown': '',
                'error_class': None,
                'filter': filter_type,
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

        web_search._crawl_markdown_with_status = fake_crawl_markdown_with_status
        web_search.reformulate = fake_reformulate
        web_search.search = fake_search
        web_search._emit_web_search_runtime_event = lambda **_kwargs: None
        try:
            payload = web_search.build_context_payload(f'Tu peux lire ceci : {url}')
        finally:
            web_search._runtime_services_value = original_runtime_services_value
            web_search._crawl_markdown_with_status = original_crawl_markdown_with_status
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._emit_web_search_runtime_event = original_emit

        self.assertEqual(
            observed_calls,
            [
                ('fit', url),
                ('raw', url),
                ('reformulate', f'Tu peux lire ceci : {url}'),
                ('search', 'requete fallback'),
            ],
        )
        self.assertTrue(payload['explicit_url_detected'])
        self.assertEqual(payload['explicit_url'], url)
        self.assertEqual(payload['primary_source_kind'], 'explicit_url')
        self.assertTrue(payload['primary_read_attempted'])
        self.assertEqual(payload['primary_read_status'], 'empty')
        self.assertEqual(payload['primary_read_filter'], 'raw')
        self.assertTrue(payload['primary_read_raw_fallback_used'])
        self.assertEqual(payload['read_state'], 'page_not_read_snippet_fallback')
        self.assertTrue(payload['fallback_used'])
        self.assertEqual(payload['collection_path'], 'explicit_url_fallback_search')
        self.assertEqual(payload['query'], 'requete fallback')
        self.assertEqual(payload['results_count'], 2)
        self.assertEqual(payload['sources'][0]['url'], url)
        self.assertEqual(payload['sources'][0]['source_origin'], 'explicit_url')
        self.assertTrue(payload['sources'][0]['is_primary_source'])
        self.assertEqual(payload['sources'][0]['crawl_status'], 'empty')
        self.assertEqual(payload['sources'][0]['used_content_kind'], 'none')
        self.assertEqual(payload['sources'][1]['source_origin'], 'search_result')
        self.assertFalse(payload['sources'][1]['is_primary_source'])
        self.assertEqual(payload['sources'][1]['crawl_status'], 'not_attempted')
        self.assertEqual(payload['sources'][1]['used_content_kind'], 'search_snippet')
        self.assertEqual(payload['used_content_kinds'], ['search_snippet'])
        self.assertGreater(payload['injected_chars'], 0)
        self.assertEqual(payload['context_chars'], len(payload['context_block']))
        self.assertEqual(
            payload['source_material_summary'],
            [
                {
                    'rank': 1,
                    'url': url,
                    'source_origin': 'explicit_url',
                    'is_primary_source': True,
                    'used_in_prompt': False,
                    'used_content_kind': 'none',
                    'crawl_status': 'empty',
                    'content_chars': 0,
                    'truncated': False,
                },
                {
                    'rank': 2,
                    'url': 'https://fallback.example/article',
                    'source_origin': 'search_result',
                    'is_primary_source': False,
                    'used_in_prompt': True,
                    'used_content_kind': 'search_snippet',
                    'crawl_status': 'not_attempted',
                    'content_chars': len(payload['sources'][1]['content_used']),
                    'truncated': False,
                },
            ],
        )
        self.assertIn("Lecture directe tentee d'abord : empty.", payload['context_block'])

    def test_build_context_payload_reads_explicit_url_via_raw_when_fit_is_empty(self) -> None:
        url = 'https://example.com/article'
        observed_calls: list[tuple[str, str]] = []
        original_runtime_services_value = web_search._runtime_services_value
        original_crawl_markdown_with_status = web_search._crawl_markdown_with_status
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_emit = web_search._emit_web_search_runtime_event

        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 2,
            'crawl4ai_max_chars': 40,
        }[field]

        def fake_crawl_markdown_with_status(input_url: str, *, filter_type: str = 'fit', query: str | None = None):
            observed_calls.append((filter_type, input_url))
            if filter_type == 'fit':
                return {'status': 'empty', 'markdown': '', 'error_class': None, 'filter': 'fit'}
            return {
                'status': 'success',
                'markdown': 'contenu primaire raw ' * 5,
                'error_class': None,
                'filter': 'raw',
            }

        web_search._crawl_markdown_with_status = fake_crawl_markdown_with_status
        web_search.reformulate = lambda _msg: (_ for _ in ()).throw(
            AssertionError('generic search should not run when raw fallback succeeds')
        )
        web_search.search = lambda _query: (_ for _ in ()).throw(
            AssertionError('search should not run when raw fallback succeeds')
        )
        web_search._emit_web_search_runtime_event = lambda **_kwargs: None
        try:
            payload = web_search.build_context_payload(f'Tu peux lire ceci : {url}')
        finally:
            web_search._runtime_services_value = original_runtime_services_value
            web_search._crawl_markdown_with_status = original_crawl_markdown_with_status
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._emit_web_search_runtime_event = original_emit

        self.assertEqual(observed_calls, [('fit', url), ('raw', url)])
        self.assertEqual(payload['status'], 'ok')
        self.assertEqual(payload['primary_read_status'], 'success')
        self.assertEqual(payload['primary_read_filter'], 'raw')
        self.assertTrue(payload['primary_read_raw_fallback_used'])
        self.assertEqual(payload['collection_path'], 'explicit_url_direct')
        self.assertFalse(payload['fallback_used'])
        self.assertEqual(payload['read_state'], 'page_partially_read')
        self.assertEqual(payload['used_content_kinds'], ['crawl_markdown'])
        self.assertEqual(payload['sources'][0]['crawl_status'], 'success')
        self.assertEqual(payload['sources'][0]['used_content_kind'], 'crawl_markdown')

    def test_build_context_payload_promotes_matching_explicit_url_in_fallback_without_duplicate(self) -> None:
        url = 'https://example.com/article'
        original_runtime_services_value = web_search._runtime_services_value
        original_crawl_markdown_with_status = web_search._crawl_markdown_with_status
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_emit = web_search._emit_web_search_runtime_event

        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 0,
            'crawl4ai_max_chars': 80,
        }[field]
        web_search._crawl_markdown_with_status = lambda _url, *, filter_type='fit', query=None: {
            'status': 'empty',
            'markdown': '',
            'error_class': None,
            'filter': filter_type,
        }
        web_search.reformulate = lambda _user_msg: 'requete fallback'
        web_search.search = lambda _query: [
            {
                'title': 'Resultat hors sujet',
                'url': 'https://irrelevant.example/article',
                'content': 'resume hors sujet',
            },
            {
                'title': 'Titre Mediapart',
                'url': url,
                'content': 'resume primaire',
            },
        ]
        web_search._emit_web_search_runtime_event = lambda **_kwargs: None
        try:
            payload = web_search.build_context_payload(f'Tu peux lire ceci : {url}')
        finally:
            web_search._runtime_services_value = original_runtime_services_value
            web_search._crawl_markdown_with_status = original_crawl_markdown_with_status
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._emit_web_search_runtime_event = original_emit

        self.assertEqual(payload['results_count'], 2)
        self.assertEqual(payload['sources'][0]['url'], url)
        self.assertEqual(payload['sources'][0]['title'], 'Titre Mediapart')
        self.assertEqual(payload['sources'][0]['source_origin'], 'explicit_url')
        self.assertTrue(payload['sources'][0]['is_primary_source'])
        self.assertEqual(payload['sources'][0]['crawl_status'], 'empty')
        self.assertEqual(payload['primary_read_filter'], 'raw')
        self.assertTrue(payload['primary_read_raw_fallback_used'])
        self.assertEqual(payload['sources'][0]['used_content_kind'], 'search_snippet')
        self.assertEqual(payload['read_state'], 'page_not_read_snippet_fallback')
        self.assertEqual(payload['sources'][1]['url'], 'https://irrelevant.example/article')
        self.assertEqual(payload['sources'][1]['source_origin'], 'search_result')
        self.assertFalse(payload['sources'][1]['is_primary_source'])
        self.assertEqual(
            [source['url'] for source in payload['sources']].count(url),
            1,
        )

    def test_build_context_payload_keeps_explicit_url_trace_without_false_success_when_fallback_is_empty(self) -> None:
        url = 'https://example.com/article'
        original_runtime_services_value = web_search._runtime_services_value
        original_crawl_markdown_with_status = web_search._crawl_markdown_with_status
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_emit = web_search._emit_web_search_runtime_event

        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 0,
            'crawl4ai_max_chars': 80,
        }[field]
        web_search._crawl_markdown_with_status = lambda _url, *, filter_type='fit', query=None: {
            'status': 'empty',
            'markdown': '',
            'error_class': None,
            'filter': filter_type,
        }
        web_search.reformulate = lambda _msg: 'requete vide'
        web_search.search = lambda _query: []
        web_search._emit_web_search_runtime_event = lambda **_kwargs: None
        try:
            payload = web_search.build_context_payload(f'Lis: {url}')
        finally:
            web_search._runtime_services_value = original_runtime_services_value
            web_search._crawl_markdown_with_status = original_crawl_markdown_with_status
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._emit_web_search_runtime_event = original_emit

        self.assertEqual(payload['status'], 'skipped')
        self.assertEqual(payload['reason_code'], 'no_data')
        self.assertEqual(payload['results_count'], 0)
        self.assertEqual(payload['read_state'], 'page_not_read_crawl_empty')
        self.assertEqual(payload['primary_read_filter'], 'raw')
        self.assertTrue(payload['primary_read_raw_fallback_used'])
        self.assertTrue(payload['fallback_used'])
        self.assertEqual(payload['collection_path'], 'explicit_url_fallback_search')
        self.assertEqual(payload['context_block'], '')
        self.assertEqual(len(payload['sources']), 1)
        self.assertEqual(payload['sources'][0]['url'], url)
        self.assertEqual(payload['sources'][0]['source_origin'], 'explicit_url')
        self.assertTrue(payload['sources'][0]['is_primary_source'])
        self.assertEqual(payload['sources'][0]['crawl_status'], 'empty')
        self.assertEqual(payload['sources'][0]['used_content_kind'], 'none')
        self.assertEqual(payload['used_content_kinds'], [])
        self.assertEqual(payload['injected_chars'], 0)
        self.assertEqual(payload['context_chars'], len(payload['context_block']))
        self.assertEqual(
            payload['source_material_summary'],
            [
                {
                    'rank': 1,
                    'url': url,
                    'source_origin': 'explicit_url',
                    'is_primary_source': True,
                    'used_in_prompt': False,
                    'used_content_kind': 'none',
                    'crawl_status': 'empty',
                    'content_chars': 0,
                    'truncated': False,
                }
            ],
        )

    def test_build_context_payload_marks_explicit_url_as_not_read_error_when_crawl_errors_and_fallback_is_empty(self) -> None:
        url = 'https://example.com/article'
        original_runtime_services_value = web_search._runtime_services_value
        original_crawl_markdown_with_status = web_search._crawl_markdown_with_status
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_emit = web_search._emit_web_search_runtime_event

        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 0,
            'crawl4ai_max_chars': 80,
        }[field]
        web_search._crawl_markdown_with_status = lambda _url, *, filter_type='fit', query=None: {
            'status': 'error',
            'markdown': '',
            'error_class': 'TimeoutError',
            'filter': filter_type,
        }
        web_search.reformulate = lambda _msg: 'requete erreur'
        web_search.search = lambda _query: []
        web_search._emit_web_search_runtime_event = lambda **_kwargs: None
        try:
            payload = web_search.build_context_payload(f'Lis: {url}')
        finally:
            web_search._runtime_services_value = original_runtime_services_value
            web_search._crawl_markdown_with_status = original_crawl_markdown_with_status
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._emit_web_search_runtime_event = original_emit

        self.assertEqual(payload['status'], 'skipped')
        self.assertEqual(payload['reason_code'], 'no_data')
        self.assertEqual(payload['results_count'], 0)
        self.assertEqual(payload['read_state'], 'page_not_read_error')
        self.assertEqual(payload['primary_read_filter'], 'fit')
        self.assertFalse(payload['primary_read_raw_fallback_used'])
        self.assertEqual(payload['context_block'], '')
        self.assertEqual(payload['sources'][0]['url'], url)
        self.assertEqual(payload['sources'][0]['crawl_status'], 'error')
        self.assertEqual(payload['sources'][0]['used_content_kind'], 'none')
        self.assertEqual(payload['used_content_kinds'], [])
        self.assertEqual(payload['injected_chars'], 0)

    def test_build_context_payload_search_only_keeps_fit_crawl_without_raw_fallback(self) -> None:
        observed_calls: list[tuple[str, str]] = []
        original_runtime_services_value = web_search._runtime_services_value
        original_crawl_markdown_with_status = web_search._crawl_markdown_with_status
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_emit = web_search._emit_web_search_runtime_event

        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 1,
            'crawl4ai_max_chars': 80,
            'crawl4ai_explicit_url_max_chars': 25000,
        }[field]

        def fake_crawl_markdown_with_status(url: str, *, filter_type: str = 'fit', query: str | None = None):
            observed_calls.append((filter_type, url))
            return {
                'status': 'success',
                'markdown': 'contenu search only ' * 10,
                'error_class': None,
                'filter': filter_type,
            }

        web_search._crawl_markdown_with_status = fake_crawl_markdown_with_status
        web_search.reformulate = lambda _msg: 'requete search only'
        web_search.search = lambda _query: [
            {'title': 'Resultat', 'url': 'https://result.example/article', 'content': 'snippet'},
        ]
        web_search._emit_web_search_runtime_event = lambda **_kwargs: None
        try:
            payload = web_search.build_context_payload('Trouve-moi cet article')
        finally:
            web_search._runtime_services_value = original_runtime_services_value
            web_search._crawl_markdown_with_status = original_crawl_markdown_with_status
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._emit_web_search_runtime_event = original_emit

        self.assertEqual(observed_calls, [('fit', 'https://result.example/article')])
        self.assertFalse(payload['explicit_url_detected'])
        self.assertEqual(payload['collection_path'], 'search_only')
        self.assertIsNone(payload['primary_read_filter'])
        self.assertFalse(payload['primary_read_raw_fallback_used'])
        self.assertTrue(payload['sources'][0]['truncated'])
        self.assertEqual(payload['read_state'], None)
        self.assertEqual(payload['context_chars'], len(payload['context_block']))


if __name__ == '__main__':
    unittest.main()
