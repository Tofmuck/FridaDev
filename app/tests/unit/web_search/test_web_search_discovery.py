from __future__ import annotations

import sys
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


if __name__ == '__main__':
    unittest.main()
