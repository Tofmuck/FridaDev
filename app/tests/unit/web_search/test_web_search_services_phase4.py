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


class WebSearchPhase4ServicesTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def _db_services_view(self):
        return runtime_settings.RuntimeSectionView(
            section='services',
            payload=runtime_settings.normalize_stored_payload(
                'services',
                {
                    'searxng_url': {'value': 'https://search.override.example', 'origin': 'db'},
                    'searxng_results': {'value': 2, 'origin': 'db'},
                    'crawl4ai_url': {'value': 'https://crawl.override.example', 'origin': 'db'},
                    'crawl4ai_token': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                    'crawl4ai_top_n': {'value': 1, 'origin': 'db'},
                    'crawl4ai_max_chars': {'value': 10, 'origin': 'db'},
                    'crawl4ai_explicit_url_max_chars': {'value': 25, 'origin': 'db'},
                },
            ),
            source='db',
            source_reason='db_row',
        )

    def test_search_uses_runtime_services_settings(self) -> None:
        observed = {'url': None}
        original_get_settings = web_search.runtime_settings.get_services_settings
        original_get = web_search.requests.get

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {
                    'results': [
                        {'title': 'A', 'url': 'https://a.example', 'content': 'a'},
                        {'title': 'B', 'url': 'https://b.example', 'content': 'b'},
                        {'title': 'C', 'url': 'https://c.example', 'content': 'c'},
                    ]
                }

        def fake_get(url, params, timeout):
            observed['url'] = url
            return FakeResponse()

        web_search.runtime_settings.get_services_settings = self._db_services_view
        web_search.requests.get = fake_get
        try:
            results = web_search.search('frida')
        finally:
            web_search.runtime_settings.get_services_settings = original_get_settings
            web_search.requests.get = original_get

        self.assertEqual(observed['url'], 'https://search.override.example/search')
        self.assertEqual(len(results), 2)

    def test_crawl_uses_runtime_services_settings_and_env_token_fallback(self) -> None:
        observed = {'url': None, 'auth': None, 'json': None}
        original_get_settings = web_search.runtime_settings.get_services_settings
        original_get_secret = web_search.runtime_settings.get_runtime_secret_value
        original_post = web_search.requests.post

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {'success': True, 'markdown': 'contenu crawl'}

        def fake_post(url, json, headers, timeout):
            observed['url'] = url
            observed['auth'] = headers['Authorization']
            observed['json'] = dict(json)
            return FakeResponse()

        def fake_get_runtime_secret_value(section: str, field: str):
            self.assertEqual((section, field), ('services', 'crawl4ai_token'))
            return runtime_settings.RuntimeSecretValue(
                section='services',
                field='crawl4ai_token',
                value='crawl-db-token',
                source='db_encrypted',
                source_reason='db_row',
            )

        web_search.runtime_settings.get_services_settings = self._db_services_view
        web_search.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        web_search.requests.post = fake_post
        try:
            content = web_search.crawl('https://source.example')
        finally:
            web_search.runtime_settings.get_services_settings = original_get_settings
            web_search.runtime_settings.get_runtime_secret_value = original_get_secret
            web_search.requests.post = original_post

        self.assertEqual(content, 'contenu crawl')
        self.assertEqual(observed['url'], 'https://crawl.override.example/md')
        self.assertEqual(observed['auth'], 'Bearer crawl-db-token')
        self.assertEqual(
            observed['json'],
            {'url': 'https://source.example', 'f': 'fit', 'c': '0'},
        )
        self.assertNotIn('only_text', observed['json'])
        self.assertNotIn('cache', observed['json'])

    def test_format_context_uses_runtime_crawl_limits(self) -> None:
        original_get_settings = web_search.runtime_settings.get_services_settings
        original_crawl_with_status = web_search.crawl_with_status
        calls = {'count': 0}

        def fake_crawl_with_status(url):
            calls['count'] += 1
            return {
                'status': 'success',
                'markdown': 'abcdefghijklmnopqrstuvwxyz',
                'error_class': None,
            }

        web_search.runtime_settings.get_services_settings = self._db_services_view
        web_search.crawl_with_status = fake_crawl_with_status
        try:
            text = web_search._format_context(
                'frida',
                [
                    {'title': 'A', 'url': 'https://a.example', 'content': 'resume A'},
                    {'title': 'B', 'url': 'https://b.example', 'content': 'resume B'},
                ],
            )
        finally:
            web_search.runtime_settings.get_services_settings = original_get_settings
            web_search.crawl_with_status = original_crawl_with_status

        self.assertEqual(calls['count'], 1)
        self.assertIn('abcdefghij\n[...contenu tronqué]', text)

    def test_crawl_with_status_reports_empty_when_markdown_is_blank(self) -> None:
        original_get_settings = web_search.runtime_settings.get_services_settings
        original_get_secret = web_search.runtime_settings.get_runtime_secret_value
        original_post = web_search.requests.post

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {'success': True, 'markdown': '   '}

        def fake_post(_url, json=None, headers=None, timeout=None):
            return FakeResponse()

        def fake_get_runtime_secret_value(section: str, field: str):
            self.assertEqual((section, field), ('services', 'crawl4ai_token'))
            return runtime_settings.RuntimeSecretValue(
                section='services',
                field='crawl4ai_token',
                value='crawl-db-token',
                source='db_encrypted',
                source_reason='db_row',
            )

        web_search.runtime_settings.get_services_settings = self._db_services_view
        web_search.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        web_search.requests.post = fake_post
        try:
            result = web_search.crawl_with_status('https://source.example')
        finally:
            web_search.runtime_settings.get_services_settings = original_get_settings
            web_search.runtime_settings.get_runtime_secret_value = original_get_secret
            web_search.requests.post = original_post

        self.assertEqual(result['status'], 'empty')
        self.assertEqual(result['markdown'], '')
        self.assertIsNone(result['error_class'])
        self.assertEqual(result['filter'], 'fit')

    def test_runtime_crawl4ai_token_uses_env_fallback_when_runtime_layer_returns_it(self) -> None:
        original_get_secret = web_search.runtime_settings.get_runtime_secret_value

        def fake_get_runtime_secret_value(section: str, field: str):
            self.assertEqual((section, field), ('services', 'crawl4ai_token'))
            return runtime_settings.RuntimeSecretValue(
                section='services',
                field='crawl4ai_token',
                value='crawl-env-fallback-token',
                source='env_fallback',
                source_reason='empty_table',
            )

        web_search.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        try:
            token = web_search._runtime_crawl4ai_token()
        finally:
            web_search.runtime_settings.get_runtime_secret_value = original_get_secret

        self.assertEqual(token, 'crawl-env-fallback-token')

    def test_runtime_crawl4ai_token_raises_explicit_error_when_db_secret_is_not_decryptable(self) -> None:
        original_get_secret = web_search.runtime_settings.get_runtime_secret_value

        def fake_get_runtime_secret_value(section: str, field: str):
            raise runtime_settings.RuntimeSettingsSecretResolutionError(
                'failed to decrypt runtime secret services.crawl4ai_token: bad ciphertext'
            )

        web_search.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        try:
            with self.assertRaisesRegex(
                runtime_settings.RuntimeSettingsSecretResolutionError,
                'failed to decrypt runtime secret services.crawl4ai_token: bad ciphertext',
            ):
                web_search._runtime_crawl4ai_token()
        finally:
            web_search.runtime_settings.get_runtime_secret_value = original_get_secret


if __name__ == '__main__':
    unittest.main()
