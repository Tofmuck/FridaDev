from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import config
from tools import web_search
from tools import web_search_clients
from tools import web_search_discovery
from tools import web_search_profile


class _JsonResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class WebSearchClientsTests(unittest.TestCase):
    def test_local_client_keeps_explicit_timeout_and_normalizes_success(self) -> None:
        observed: dict[str, object] = {}

        def fake_get(url: str, *, params: dict[str, str], timeout: int) -> _JsonResponse:
            observed.update(url=url, params=dict(params), timeout=timeout)
            return _JsonResponse(
                {
                    'results': [
                        {
                            'title': 'SYNTHETIC_TITLE',
                            'url': 'https://source.invalid/item',
                            'content': 'SYNTHETIC_SNIPPET',
                            'ignored': 'SYNTHETIC_IGNORED',
                        }
                    ]
                }
            )

        result = web_search_clients.search_local_with_status(
            'SYNTHETIC_QUERY',
            searxng_url='https://searxng.invalid/',
            max_results=1,
            searxng_params={'engines': 'bing', 'time_range': ''},
            requests_module=SimpleNamespace(get=fake_get),
        )

        self.assertEqual(observed['url'], 'https://searxng.invalid/search')
        self.assertEqual(observed['timeout'], web_search_clients.SEARXNG_TIMEOUT_S)
        self.assertEqual(observed['params']['q'], 'SYNTHETIC_QUERY')
        self.assertEqual(observed['params']['engines'], 'bing')
        self.assertNotIn('time_range', observed['params'])
        self.assertEqual(
            result,
            {
                'status': 'ok',
                'reason_code': None,
                'error_class': '',
                'results': [
                    {
                        'title': 'SYNTHETIC_TITLE',
                        'url': 'https://source.invalid/item',
                        'content': 'SYNTHETIC_SNIPPET',
                    }
                ],
            },
        )

    def test_local_client_preserves_error_status_and_class(self) -> None:
        def fail_get(*_args: object, **_kwargs: object) -> None:
            raise TimeoutError('SYNTHETIC_RAW_EXCEPTION')

        result = web_search_clients.search_local_with_status(
            'SYNTHETIC_QUERY',
            searxng_url='https://searxng.invalid',
            max_results=5,
            requests_module=SimpleNamespace(get=fail_get),
        )

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['reason_code'], web_search_clients.WEB_SEARCH_UPSTREAM_ERROR_REASON)
        self.assertEqual(result['error_class'], 'TimeoutError')
        self.assertEqual(result['results'], [])
        self.assertNotIn('SYNTHETIC_RAW_EXCEPTION', repr(result))

    def test_discovery_adapter_distinguishes_local_no_data_from_upstream_error(self) -> None:
        responses = iter(
            (
                {'status': 'ok', 'reason_code': None, 'error_class': '', 'results': []},
                {
                    'status': 'error',
                    'reason_code': web_search_clients.WEB_SEARCH_UPSTREAM_ERROR_REASON,
                    'error_class': 'TimeoutError',
                    'results': [],
                },
            )
        )

        def local_search_response(_query: str, _params: dict[str, str] | None) -> dict[str, object]:
            return next(responses)

        no_data = web_search_clients.discover_with_status(
            'SYNTHETIC_QUERY',
            search_profile=web_search_profile.PROFILE_GENERAL_DIVERS,
            searxng_params=None,
            max_results=5,
            requested_provider='local',
            local_search_response=local_search_response,
        )
        upstream_error = web_search_clients.discover_with_status(
            'SYNTHETIC_QUERY',
            search_profile=web_search_profile.PROFILE_GENERAL_DIVERS,
            searxng_params=None,
            max_results=5,
            requested_provider='local',
            local_search_response=local_search_response,
        )

        self.assertEqual(no_data.error_class, '')
        self.assertEqual(no_data.response.results, [])
        self.assertEqual(no_data.response.observability['web_discovery_reason_codes'], ['local_searxng_discovery_used'])
        self.assertEqual(upstream_error.error_class, 'TimeoutError')
        self.assertEqual(
            upstream_error.response.observability['web_discovery_reason_codes'],
            [
                'local_searxng_discovery_used',
                web_search_clients.SEARXNG_REQUEST_FAILED_REASON,
                web_search_clients.WEB_SEARCH_UPSTREAM_ERROR_REASON,
            ],
        )

    def test_discovery_adapter_preserves_external_timeout_and_error_mapping(self) -> None:
        observed: dict[str, object] = {}

        def fail_post(_url: str, *, json: dict[str, object], headers: dict[str, str], timeout: int) -> None:
            observed.update(json=json, headers=headers, timeout=timeout)
            raise TimeoutError('SYNTHETIC_RAW_EXCEPTION')

        llm_module = SimpleNamespace(
            or_chat_completions_url=lambda: 'https://provider.invalid/chat/completions',
            or_headers_custom=lambda **_kwargs: {'X-Frida-Caller': 'web_discovery'},
        )
        result = web_search_clients.discover_with_status(
            'SYNTHETIC_QUERY',
            search_profile=web_search_profile.PROFILE_GENERAL_DIVERS,
            searxng_params=None,
            max_results=5,
            requested_provider='openrouter_exa',
            local_search_response=lambda *_args: self.fail('local client must not run'),
            requests_module=SimpleNamespace(post=fail_post),
            llm_module=llm_module,
        )

        self.assertEqual(observed['timeout'], config.WEB_SEARCH_DISCOVERY_TIMEOUT_S)
        self.assertEqual(result.error_class, '')
        self.assertEqual(result.response.results, [])
        self.assertEqual(
            result.response.observability['web_discovery_external_error_kind'],
            'openrouter_timeout',
        )
        self.assertNotIn('SYNTHETIC_RAW_EXCEPTION', repr(result))

    def test_web_search_facade_delegates_to_extracted_clients(self) -> None:
        local_response = {
            'status': 'ok',
            'reason_code': None,
            'error_class': '',
            'results': [],
        }
        discovery_result = web_search_clients.DiscoveryClientResult(
            response=web_search_discovery.DiscoveryResponse(
                results=[],
                observability=web_search_discovery.empty_observability_fields(
                    requested_provider='local',
                    effective_provider_value='local',
                ),
            ),
            error_class='',
        )

        with mock.patch.object(
            web_search.web_search_clients,
            'search_local_with_status',
            return_value=local_response,
        ) as local_client, mock.patch.object(
            web_search,
            '_runtime_services_value',
            return_value='https://searxng.invalid',
        ):
            self.assertIs(
                web_search.search_with_status('SYNTHETIC_QUERY', max_results=3),
                local_response,
            )
        self.assertEqual(local_client.call_args.kwargs['timeout_s'], web_search_clients.SEARXNG_TIMEOUT_S)

        with mock.patch.object(
            web_search.web_search_clients,
            'discover_with_status',
            return_value=discovery_result,
        ) as discovery_client:
            actual = web_search._call_discovery_with_profile_params(
                'SYNTHETIC_QUERY',
                search_profile=web_search_profile.PROFILE_GENERAL_DIVERS,
                searxng_params=None,
                max_results=3,
                discovery_provider='local',
            )
        self.assertIs(actual, discovery_result)
        discovery_client.assert_called_once()


if __name__ == '__main__':
    unittest.main()
