from __future__ import annotations

import socket
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

from tools import web_public_url_policy, web_search, web_search_crawl_policy


def _resolved(*addresses: str):
    return [(None, None, None, "", (address, 0)) for address in addresses]


class WebPublicUrlPolicyTests(unittest.TestCase):
    def test_blocks_non_public_ip_families_and_internal_names(self) -> None:
        blocked_urls = [
            "http://127.0.0.1/page",
            "http://10.0.0.1/page",
            "http://169.254.169.254/page",
            "http://224.0.0.1/page",
            "http://240.0.0.1/page",
            "http://0.0.0.0/page",
            "http://[::1]/page",
            "http://[fe80::1]/page",
            "http://[fc00::1]/page",
            "http://[ff02::1]/page",
            "http://[2001:db8::1]/page",
            "http://localhost/page",
            "http://crawl4ai/page",
            "http://service.internal/page",
            "http://host.docker.internal/page",
            "http://127.0.0.1\\@public.example/page",
        ]

        for url in blocked_urls:
            with self.subTest(url=url):
                self.assertEqual(
                    web_public_url_policy.blocked_url_reason(url),
                    web_public_url_policy.REASON_URL_BLOCKED_INTERNAL,
                )

    def test_dns_requires_all_resolved_addresses_to_be_global(self) -> None:
        self.assertEqual(
            web_public_url_policy.blocked_url_reason(
                "https://public-looking.example/page",
                resolver=lambda *_args, **_kwargs: _resolved("93.184.216.34", "172.18.0.5"),
            ),
            web_public_url_policy.REASON_URL_BLOCKED_INTERNAL,
        )
        self.assertEqual(
            web_public_url_policy.blocked_url_reason(
                "https://public.example/page",
                resolver=lambda *_args, **_kwargs: _resolved("93.184.216.34", "2606:4700:4700::1111"),
            ),
            "",
        )

    def test_dns_failure_is_blocked_fail_closed(self) -> None:
        def fail_resolution(*_args, **_kwargs):
            raise socket.gaierror("synthetic_dns_failure")

        self.assertEqual(
            web_public_url_policy.blocked_url_reason(
                "https://unresolved.example/page",
                resolver=fail_resolution,
            ),
            web_public_url_policy.REASON_URL_BLOCKED_INTERNAL,
        )


class WebSearchSsrfGuardTests(unittest.TestCase):
    def _assert_crawl_rejected_without_payload(self, url: str) -> dict[str, object]:
        original_payload_builder = web_search._build_crawl4ai_md_payload
        original_post = web_search.requests.post
        original_runtime_value = web_search._runtime_services_value
        original_token = web_search._runtime_crawl4ai_token
        web_search._build_crawl4ai_md_payload = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Crawl4AI payload must not be built for a rejected URL")
        )
        web_search.requests.post = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Crawl4AI must not be called for a rejected URL")
        )
        web_search._runtime_services_value = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Crawl4AI settings must not be resolved for a rejected URL")
        )
        web_search._runtime_crawl4ai_token = lambda: (_ for _ in ()).throw(
            AssertionError("Crawl4AI token must not be resolved for a rejected URL")
        )
        try:
            return web_search._crawl_markdown_with_status(url)
        finally:
            web_search._build_crawl4ai_md_payload = original_payload_builder
            web_search.requests.post = original_post
            web_search._runtime_services_value = original_runtime_value
            web_search._runtime_crawl4ai_token = original_token

    def test_explicit_internal_url_is_rejected_before_crawl4ai_payload(self) -> None:
        result = self._assert_crawl_rejected_without_payload("http://127.0.0.1/private")

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_class"], "crawl_url_blocked")
        self.assertEqual(result["reason_code"], "web_url_blocked_internal")
        self.assertEqual(result["markdown"], "")

        explicit_result = web_search._crawl_explicit_url_primary_with_status(
            "http://127.0.0.1/private"
        )
        self.assertEqual(explicit_result["status"], "error")
        self.assertEqual(explicit_result["crawl_policy_reason"], "web_url_blocked_internal")
        self.assertFalse(explicit_result["raw_fallback_used"])

    def test_hostname_resolving_to_private_ip_is_rejected_before_crawl4ai(self) -> None:
        original_getaddrinfo = web_public_url_policy.socket.getaddrinfo
        web_public_url_policy.socket.getaddrinfo = lambda *_args, **_kwargs: _resolved("172.18.0.5")
        try:
            result = self._assert_crawl_rejected_without_payload("https://public-looking.example/page")
        finally:
            web_public_url_policy.socket.getaddrinfo = original_getaddrinfo

        self.assertEqual(result["reason_code"], "web_url_blocked_internal")

    def test_public_html_url_keeps_existing_crawl4ai_path_with_fake_transport(self) -> None:
        observed: dict[str, object] = {}
        original_getaddrinfo = web_public_url_policy.socket.getaddrinfo
        original_post = web_search.requests.post
        original_runtime_value = web_search._runtime_services_value
        original_token = web_search._runtime_crawl4ai_token

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {"success": True, "markdown": "synthetic public content", "filter": "fit"}

        def fake_post(url, json, headers, timeout):
            observed.update(
                url=url,
                json=dict(json),
                authorization=headers.get("Authorization"),
                timeout=timeout,
            )
            return FakeResponse()

        web_public_url_policy.socket.getaddrinfo = lambda *_args, **_kwargs: _resolved(
            "93.184.216.34"
        )
        web_search.requests.post = fake_post
        web_search._runtime_services_value = lambda field: {
            "crawl4ai_url": "https://crawl.example",
        }[field]
        web_search._runtime_crawl4ai_token = lambda: "synthetic-token"
        try:
            result = web_search._crawl_markdown_with_status("https://public.example/article.html")
        finally:
            web_public_url_policy.socket.getaddrinfo = original_getaddrinfo
            web_search.requests.post = original_post
            web_search._runtime_services_value = original_runtime_value
            web_search._runtime_crawl4ai_token = original_token

        self.assertEqual(result["status"], "success")
        self.assertEqual(observed["url"], "https://crawl.example/md")
        self.assertEqual(
            observed["json"],
            {"url": "https://public.example/article.html", "f": "fit", "c": "0"},
        )

    def test_searxng_result_url_uses_same_guard_before_crawl4ai(self) -> None:
        policy = web_search_crawl_policy.Crawl4AIExtractionPolicy(
            kind="historical_fit",
            reason_code="general_fit_default",
            primary_filter="fit",
        )

        original_post = web_search.requests.post
        web_search.requests.post = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("A rejected SearXNG result must not call Crawl4AI")
        )
        try:
            result = web_search._crawl_search_result_with_policy("http://10.0.0.8/page", policy)
        finally:
            web_search.requests.post = original_post

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["crawl_policy_reason"], "web_url_blocked_internal")

    def test_blocked_explicit_pdf_stays_on_pdf_path_without_crawl4ai_fallback(self) -> None:
        original_crawl = web_search._crawl_markdown_with_status
        web_search._crawl_markdown_with_status = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("A blocked explicit PDF must not fall through to Crawl4AI")
        )
        try:
            result = web_search._read_web_pdf_as_crawl_result(
                "http://127.0.0.1/private.pdf",
                max_chars=100,
                probe_content_type=True,
            )
        finally:
            web_search._crawl_markdown_with_status = original_crawl

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["crawl_policy_reason"], "web_pdf_url_blocked_internal")
        self.assertFalse(result["web_pdf_read_attempted"])


if __name__ == "__main__":
    unittest.main()
