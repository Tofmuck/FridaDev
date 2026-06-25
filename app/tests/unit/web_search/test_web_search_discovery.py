from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

if 'psycopg' not in sys.modules and importlib.util.find_spec('psycopg') is None:
    psycopg_module = types.ModuleType('psycopg')
    psycopg_rows_module = types.ModuleType('psycopg.rows')
    psycopg_rows_module.dict_row = object()
    psycopg_module.rows = psycopg_rows_module
    sys.modules['psycopg'] = psycopg_module
    sys.modules['psycopg.rows'] = psycopg_rows_module

from tools import web_search
from tools import web_search_discovery
from tools import web_search_profile


class WebSearchDiscoveryTests(unittest.TestCase):
    def test_local_provider_keeps_searxng_search_path(self) -> None:
        observed = {'query': '', 'params': None}

        def local_search(query: str, *, searxng_params=None):
            observed['query'] = query
            observed['params'] = dict(searxng_params or {})
            return [
                {
                    'title': 'Resultat local',
                    'url': 'https://local.example/doc',
                    'content': 'Snippet local',
                }
            ]

        response = web_search_discovery.discover_urls(
            'documentation exemple',
            search_profile=web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
            searxng_params={'engines': 'bing'},
            max_results=5,
            requested_provider='local',
            local_search=local_search,
        )

        self.assertEqual(observed['query'], 'documentation exemple')
        self.assertEqual(observed['params'], {'engines': 'bing'})
        self.assertEqual(response.results[0]['url'], 'https://local.example/doc')
        self.assertEqual(response.observability['web_discovery_provider_effective'], 'local')
        self.assertFalse(response.observability['web_discovery_external_used'])

    def test_openrouter_exa_provider_builds_server_tool_payload_and_normalizes_citations(self) -> None:
        observed = {'payload': None, 'headers': None}

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {
                    'choices': [
                        {
                            'message': {
                                'annotations': [
                                    {
                                        'type': 'url_citation',
                                        'url_citation': {
                                            'title': 'Stripe Checkout',
                                            'url': 'https://docs.stripe.com/payments/checkout',
                                            'content': 'Official Checkout docs.',
                                        },
                                    }
                                ],
                                'content': 'Citation.',
                            }
                        }
                    ]
                }

        def fake_post(url, json, headers, timeout):
            observed['payload'] = json
            observed['headers'] = headers
            observed['url'] = url
            observed['timeout'] = timeout
            return FakeResponse()

        fake_llm_module = SimpleNamespace(
            or_chat_completions_url=lambda: 'https://openrouter.example/chat/completions',
            or_headers_custom=lambda *, caller, referer, title: {
                'Content-Type': 'application/json',
                'X-Frida-Caller': caller,
                'X-OpenRouter-Title': title,
            },
            read_openrouter_response_payload=lambda response: response.json(),
        )

        response = web_search_discovery.discover_urls(
            'documentation officielle Stripe Checkout',
            search_profile=web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
            max_results=5,
            requested_provider='openrouter_exa',
            local_search=lambda *_args, **_kwargs: [],
            requests_module=SimpleNamespace(post=fake_post),
            llm_module=fake_llm_module,
        )

        self.assertEqual(response.results[0]['url'], 'https://docs.stripe.com/payments/checkout')
        self.assertEqual(response.results[0]['discovery_source_kind'], 'openrouter_url_citation')
        tool = observed['payload']['tools'][0]
        self.assertEqual(tool['type'], 'openrouter:web_search')
        self.assertEqual(tool['parameters']['engine'], 'exa')
        self.assertEqual(tool['parameters']['max_results'], 5)
        self.assertEqual(tool['parameters']['search_context_size'], 'low')
        self.assertEqual(observed['headers']['X-Frida-Caller'], 'web_discovery')
        self.assertTrue(response.observability['web_discovery_external_used'])
        self.assertEqual(response.observability['web_discovery_external_provider'], 'openrouter_exa')

    def test_openrouter_headers_fallback_uses_web_discovery_caller(self) -> None:
        observed: dict[str, str] = {}

        def fake_or_headers(*, caller='llm'):
            observed['caller'] = caller
            return {'X-Frida-Caller': caller}

        fake_llm_module = SimpleNamespace(
            or_headers=fake_or_headers,
        )

        headers = web_search_discovery._openrouter_headers(fake_llm_module)

        self.assertEqual(observed['caller'], 'web_discovery')
        self.assertEqual(headers['X-Frida-Caller'], 'web_discovery')

    def test_openrouter_exa_missing_config_returns_clean_observable_error(self) -> None:
        fake_llm_module = SimpleNamespace(
            or_chat_completions_url=lambda: 'https://openrouter.example/chat/completions',
            or_headers_custom=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError('missing key')),
            read_openrouter_response_payload=lambda response: response.json(),
        )

        response = web_search_discovery.discover_urls(
            'actualite ia europe',
            search_profile=web_search_profile.PROFILE_ACTUALITE,
            requested_provider='openrouter_exa',
            local_search=lambda *_args, **_kwargs: [],
            llm_module=fake_llm_module,
        )

        self.assertEqual(response.results, [])
        self.assertEqual(response.observability['web_discovery_provider_effective'], 'openrouter_exa')
        self.assertFalse(response.observability['web_discovery_external_used'])
        self.assertEqual(response.observability['web_discovery_external_error_kind'], 'openrouter_config_error')
        self.assertIn('openrouter_exa_discovery_failed', response.observability['web_discovery_reason_codes'])

    def test_build_context_payload_distinguishes_openrouter_discovery_error_from_no_citations(self) -> None:
        original_runtime_services_value = web_search._runtime_services_value
        original_reformulate = web_search.reformulate
        original_emit = web_search._emit_web_search_runtime_event

        observed_events: list[dict[str, object]] = []

        def fake_runtime_services_value(field: str):
            values = {
                'searxng_results': 5,
                'crawl4ai_top_n': 0,
                'crawl4ai_max_chars': 80,
            }
            if field in values:
                return values[field]
            return original_runtime_services_value(field)

        class NoCitationResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {'choices': [{'message': {'annotations': []}}]}

        def no_citation_post(*_args, **_kwargs):
            return NoCitationResponse()

        error_llm_module = SimpleNamespace(
            or_chat_completions_url=lambda: 'https://openrouter.example/chat/completions',
            or_headers_custom=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError('missing key')),
            read_openrouter_response_payload=lambda response: response.json(),
        )
        no_citation_llm_module = SimpleNamespace(
            or_chat_completions_url=lambda: 'https://openrouter.example/chat/completions',
            or_headers_custom=lambda **_kwargs: {'X-Frida-Caller': 'web_discovery'},
            read_openrouter_response_payload=lambda response: response.json(),
        )

        web_search._runtime_services_value = fake_runtime_services_value
        web_search.reformulate = lambda *_args, **_kwargs: 'synthetic discovery query'
        web_search._emit_web_search_runtime_event = lambda **kwargs: observed_events.append(kwargs)
        try:
            error_payload = web_search.build_context_payload(
                'synthetic user question',
                requests_module=SimpleNamespace(post=no_citation_post),
                llm_module=error_llm_module,
                discovery_provider='openrouter_exa',
                enable_specialized_queries=False,
                enable_reranking=False,
            )
            error_event = dict(observed_events[-1])

            observed_events.clear()
            no_citation_payload = web_search.build_context_payload(
                'synthetic user question',
                requests_module=SimpleNamespace(post=no_citation_post),
                llm_module=no_citation_llm_module,
                discovery_provider='openrouter_exa',
                enable_specialized_queries=False,
                enable_reranking=False,
            )
            no_citation_event = dict(observed_events[-1])
        finally:
            web_search._runtime_services_value = original_runtime_services_value
            web_search.reformulate = original_reformulate
            web_search._emit_web_search_runtime_event = original_emit

        self.assertEqual(error_payload['status'], 'error')
        self.assertEqual(error_payload['reason_code'], web_search.WEB_DISCOVERY_UPSTREAM_ERROR_REASON)
        self.assertEqual(error_payload['error_class'], 'WebDiscoveryUpstreamError')
        self.assertEqual(error_payload['web_discovery_external_error_kind'], 'openrouter_config_error')
        self.assertIn('openrouter_exa_discovery_failed', error_payload['web_discovery_reason_codes'])
        self.assertEqual(error_event['status'], 'error')
        self.assertEqual(error_event['reason_code'], web_search.WEB_DISCOVERY_UPSTREAM_ERROR_REASON)
        self.assertEqual(error_event['message_short'], web_search.WEB_DISCOVERY_UPSTREAM_ERROR_REASON)

        self.assertEqual(no_citation_payload['status'], 'skipped')
        self.assertEqual(no_citation_payload['reason_code'], 'no_data')
        self.assertEqual(no_citation_payload['web_discovery_external_error_kind'], '')
        self.assertIn('openrouter_exa_no_url_citations', no_citation_payload['web_discovery_reason_codes'])
        self.assertEqual(no_citation_event['status'], 'skipped')
        self.assertEqual(no_citation_event['reason_code'], 'no_data')

    def test_explicit_url_forces_local_provider_even_when_openrouter_is_requested(self) -> None:
        self.assertEqual(
            web_search_discovery.effective_provider(
                requested_provider='openrouter_exa',
                search_profile=web_search_profile.PROFILE_EXPLICIT_URL,
            ),
            'local',
        )
        fields = web_search_discovery.plan_observability_fields(
            requested_provider='openrouter_exa',
            search_profile=web_search_profile.PROFILE_EXPLICIT_URL,
        )
        self.assertEqual(fields['web_discovery_provider_effective'], 'local')
        self.assertIn('explicit_url_forces_local_discovery', fields['web_discovery_reason_codes'])

    def test_build_context_payload_openrouter_discovery_uses_injected_requests_module(self) -> None:
        observed: dict[str, object] = {'post_called': False}

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {
                    'choices': [
                        {
                            'message': {
                                'annotations': [
                                    {
                                        'type': 'url_citation',
                                        'url_citation': {
                                            'title': 'Stripe Checkout',
                                            'url': 'https://docs.stripe.com/payments/checkout',
                                            'content': 'Official Checkout docs.',
                                        },
                                    }
                                ],
                                'content': 'Citation.',
                            }
                        }
                    ]
                }

        def fake_post(url, json, headers, timeout):
            observed.update(
                {
                    'post_called': True,
                    'url': url,
                    'headers': dict(headers or {}),
                    'engine': json['tools'][0]['parameters']['engine'],
                    'timeout': timeout,
                }
            )
            return FakeResponse()

        fake_llm_module = SimpleNamespace(
            or_chat_completions_url=lambda: 'https://openrouter.example/chat/completions',
            or_headers_custom=lambda *, caller, referer, title: {
                'Content-Type': 'application/json',
                'X-Frida-Caller': caller,
                'X-OpenRouter-Title': title,
            },
            read_openrouter_response_payload=lambda response: response.json(),
        )

        original_runtime_services_value = web_search._runtime_services_value
        original_reformulate = web_search.reformulate
        original_build_search_context_material = web_search._build_search_context_material
        original_emit = web_search._emit_web_search_runtime_event

        def fake_runtime_services_value(field: str):
            return {
                'searxng_results': 5,
                'crawl4ai_top_n': 1,
                'crawl4ai_max_chars': 500,
                'crawl4ai_explicit_url_max_chars': 500,
            }[field]

        def fake_build_search_context_material(query, results, **_kwargs):
            source = {
                'rank': 1,
                'title': results[0]['title'],
                'url': results[0]['url'],
                'source_domain': 'docs.stripe.com',
                'search_snippet': results[0]['content'],
                'used_in_prompt': True,
                'used_content_kind': 'search_snippet',
                'content_used': results[0]['content'],
                'truncated': False,
                'source_origin': 'search_result',
                'is_primary_source': False,
                'crawl_status': 'not_attempted',
                'crawl_filter': '',
                'crawl_filter_requested': '',
                'crawl_policy_kind': '',
                'crawl_policy_reason': '',
                'crawl_cache_mode': '',
                'crawl_query_sha256_12': '',
                'crawl_query_chars': 0,
                'crawl_fallback_used': False,
                'crawl_fallback_reason': '',
                'crawl_primary_status': 'not_attempted',
                'crawl_fallback_status': '',
                'crawl_markdown_chars': 0,
                'crawl_max_chars': 0,
                'query_source_kind': 'primary',
                'query_source_index': 0,
                'query_source_sha256_12': '',
            }
            return {
                'runtime': {},
                'results_count': 1,
                'sources': [source],
                'context_block': 'context',
            }

        web_search._runtime_services_value = fake_runtime_services_value
        web_search.reformulate = lambda *_args, **_kwargs: 'documentation officielle Stripe Checkout'
        web_search._build_search_context_material = fake_build_search_context_material
        web_search._emit_web_search_runtime_event = lambda **_kwargs: None
        try:
            payload = web_search.build_context_payload(
                'cherche la documentation officielle Stripe Checkout',
                requests_module=SimpleNamespace(post=fake_post),
                llm_module=fake_llm_module,
                discovery_provider='openrouter_exa',
                enable_specialized_queries=False,
                enable_reranking=False,
            )
        finally:
            web_search._runtime_services_value = original_runtime_services_value
            web_search.reformulate = original_reformulate
            web_search._build_search_context_material = original_build_search_context_material
            web_search._emit_web_search_runtime_event = original_emit

        self.assertTrue(observed['post_called'])
        self.assertEqual(observed['engine'], 'exa')
        self.assertEqual(observed['headers']['X-Frida-Caller'], 'web_discovery')
        self.assertEqual(payload['web_discovery_provider_effective'], 'openrouter_exa')
        self.assertTrue(payload['web_discovery_external_used'])


if __name__ == '__main__':
    unittest.main()
