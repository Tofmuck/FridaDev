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

from tools import web_public_url_policy, web_search


class WebSearchLogRedactionTests(unittest.TestCase):
    def test_reformulate_error_log_redacts_user_exception_and_provider_payload(self) -> None:
        user_msg = (
            'RAW_USER_MESSAGE_REFORMULATE_SENTINEL '
            'https://user.example/private?token=RAW_USER_TOKEN_SENTINEL'
        )
        provider_url = 'https://provider.example/chat/completions?token=RAW_PROVIDER_URL_TOKEN'
        header_token = 'RAW_HEADER_TOKEN_SENTINEL'
        provider_payload = 'RAW_PROVIDER_PAYLOAD_SENTINEL'
        exception_text = 'RAW_REFORMULATE_EXCEPTION_SENTINEL'
        system_prompt = 'RAW_SYSTEM_PROMPT_SENTINEL {today}'
        original_prompt_getter = web_search.prompt_loader.get_web_reformulation_prompt
        original_settings_getter = web_search.web_reformulation_settings.get_runtime_settings

        class FakeSettings:
            model = 'openai/gpt-5.4-mini'
            max_tokens = 40
            temperature = 0.2
            timeout_s = 10

        class FakeLlmModule:
            @staticmethod
            def or_chat_completions_url() -> str:
                return provider_url

            @staticmethod
            def or_headers(*, caller: str = 'llm') -> dict[str, str]:
                return {
                    'Authorization': f'Bearer {header_token}',
                    'X-Frida-Caller': caller,
                }

            @staticmethod
            def with_provider_attribution(payload: dict[str, Any], *, caller: str) -> dict[str, Any]:
                enriched = dict(payload)
                enriched['raw_provider_payload_sentinel'] = provider_payload
                enriched['provider_caller'] = caller
                return enriched

            @staticmethod
            def resolve_provider_title(_caller: str) -> str:
                return 'FridaDev/WebReformulation'

            @staticmethod
            def read_openrouter_response_payload(_response: Any) -> dict[str, Any]:
                return {}

            @staticmethod
            def extract_openrouter_text(_payload: dict[str, Any]) -> str:
                return ''

        class FakeRequestsModule:
            @staticmethod
            def post(url: str, json: dict[str, Any], headers: dict[str, str], timeout: int) -> Any:
                raise RuntimeError(
                    f'{exception_text} url={url} headers={headers} payload={json} timeout={timeout}'
                )

        web_search.prompt_loader.get_web_reformulation_prompt = lambda: system_prompt
        web_search.web_reformulation_settings.get_runtime_settings = lambda: FakeSettings()
        try:
            with self.assertLogs('frida.web_search', level='WARNING') as captured:
                result = web_search.reformulate(
                    user_msg,
                    requests_module=FakeRequestsModule(),
                    llm_module=FakeLlmModule(),
                    now_iso='2026-06-21T00:00:00Z',
                )
        finally:
            web_search.prompt_loader.get_web_reformulation_prompt = original_prompt_getter
            web_search.web_reformulation_settings.get_runtime_settings = original_settings_getter

        self.assertEqual(result, user_msg)
        logs = '\n'.join(captured.output)
        self.assertIn('reformulate_error reason=web_reformulation_exception', logs)
        self.assertIn('err_class=RuntimeError', logs)
        self.assertNotIn('RAW_USER_MESSAGE_REFORMULATE_SENTINEL', logs)
        self.assertNotIn('RAW_USER_TOKEN_SENTINEL', logs)
        self.assertNotIn('user.example', logs)
        self.assertNotIn(exception_text, logs)
        self.assertNotIn(provider_url, logs)
        self.assertNotIn('provider.example', logs)
        self.assertNotIn('RAW_PROVIDER_URL_TOKEN', logs)
        self.assertNotIn(header_token, logs)
        self.assertNotIn(provider_payload, logs)
        self.assertNotIn(system_prompt, logs)
        self.assertNotIn('RAW_SYSTEM_PROMPT_SENTINEL', logs)

    def test_crawl_error_log_redacts_url_and_exception_text(self) -> None:
        sentinel_url = 'https://sensitive.example/private/path?token=raw-token#frag'
        original_post = web_search.requests.post
        original_runtime_services_value = web_search._runtime_services_value
        original_runtime_crawl4ai_token = web_search._runtime_crawl4ai_token
        original_getaddrinfo = web_public_url_policy.socket.getaddrinfo

        def fake_post(*_args: Any, **_kwargs: Any):
            raise RuntimeError('RAW_CRAWL_EXCEPTION_SENTINEL')

        web_search.requests.post = fake_post
        web_public_url_policy.socket.getaddrinfo = lambda *_args, **_kwargs: [
            (None, None, None, '', ('93.184.216.34', 0))
        ]
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
            web_public_url_policy.socket.getaddrinfo = original_getaddrinfo

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
