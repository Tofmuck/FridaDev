from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tools import web_search


class WebSearchLogRedactionTests(unittest.TestCase):
    def test_crawl_error_log_redacts_url_and_exception_text(self) -> None:
        sentinel_url = 'https://sensitive.example/private/path?token=raw-token#frag'
        original_post = web_search.requests.post
        original_runtime_services_value = web_search._runtime_services_value
        original_runtime_crawl4ai_token = web_search._runtime_crawl4ai_token

        def fake_post(*_args: Any, **_kwargs: Any):
            raise RuntimeError('RAW_CRAWL_EXCEPTION_SENTINEL')

        web_search.requests.post = fake_post
        web_search._runtime_services_value = lambda field: {
            'crawl4ai_url': 'http://crawl4ai.local',
        }[field]
        web_search._runtime_crawl4ai_token = lambda: 'RAW_CRAWL_TOKEN_SENTINEL'
        try:
            with self.assertLogs('frida.web_search', level='WARNING') as captured:
                result = web_search._crawl_markdown_with_status(
                    sentinel_url,
                    filter_type='fit',
                    query='RAW CRAWL QUERY SENTINEL',
                )
        finally:
            web_search.requests.post = original_post
            web_search._runtime_services_value = original_runtime_services_value
            web_search._runtime_crawl4ai_token = original_runtime_crawl4ai_token

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_class'], 'RuntimeError')
        logs = '\n'.join(captured.output)
        self.assertIn('crawl_error reason=crawl_exception', logs)
        self.assertIn('filter=fit', logs)
        self.assertIn('url_scheme=https', logs)
        self.assertIn('url_query_present=True', logs)
        self.assertIn('url_fragment_present=True', logs)
        self.assertIn('err_class=RuntimeError', logs)
        self.assertNotIn(sentinel_url, logs)
        self.assertNotIn('sensitive.example', logs)
        self.assertNotIn('/private/path', logs)
        self.assertNotIn('raw-token', logs)
        self.assertNotIn('RAW_CRAWL_EXCEPTION_SENTINEL', logs)
        self.assertNotIn('RAW_CRAWL_TOKEN_SENTINEL', logs)
        self.assertNotIn('RAW CRAWL QUERY SENTINEL', logs)


if __name__ == '__main__':
    unittest.main()
