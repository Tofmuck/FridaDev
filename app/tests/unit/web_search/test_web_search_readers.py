from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tools import web_search, web_search_readers


class _JsonResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class WebSearchReadersTests(unittest.TestCase):
    def test_crawl_client_preserves_md_contract_timeout_and_status(self) -> None:
        observed: dict[str, object] = {}

        def fake_post(
            url: str,
            *,
            json: dict[str, str],
            headers: dict[str, str],
            timeout: int,
        ) -> _JsonResponse:
            observed.update(url=url, json=dict(json), headers=dict(headers), timeout=timeout)
            return _JsonResponse(
                {
                    "success": True,
                    "markdown": "SYNTHETIC_MARKDOWN",
                    "filter": "bm25",
                }
            )

        result = web_search_readers.crawl_markdown_with_status(
            "https://93.184.216.34/article",
            filter_type="bm25",
            query="SYNTHETIC_QUERY",
            cache_mode="1",
            runtime_service_value=lambda field: {"crawl4ai_url": "https://crawl.invalid/"}[field],
            runtime_token=lambda: "SYNTHETIC_TOKEN",
            requests_module=SimpleNamespace(post=fake_post),
            blocked_url_reason=lambda _url: "",
        )

        self.assertEqual(observed["url"], "https://crawl.invalid/md")
        self.assertEqual(
            observed["json"],
            {
                "url": "https://93.184.216.34/article",
                "f": "bm25",
                "c": "1",
                "q": "SYNTHETIC_QUERY",
            },
        )
        self.assertEqual(observed["headers"]["Authorization"], "Bearer SYNTHETIC_TOKEN")
        self.assertEqual(observed["timeout"], 20)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["markdown"], "SYNTHETIC_MARKDOWN")
        self.assertEqual(result["filter"], "bm25")
        self.assertEqual(result["cache_mode"], "1")
        self.assertEqual(result["query_chars"], len("SYNTHETIC_QUERY"))

    def test_crawl_client_rejects_url_before_settings_secret_payload_or_transport(self) -> None:
        def forbidden(*_args: object, **_kwargs: object) -> object:
            raise AssertionError("dependency must not be resolved for a blocked URL")

        result = web_search_readers.crawl_markdown_with_status(
            "http://127.0.0.1/private?token=SYNTHETIC_QUERY_SECRET",
            runtime_service_value=forbidden,
            runtime_token=forbidden,
            requests_module=SimpleNamespace(post=forbidden),
            payload_builder=forbidden,
            blocked_url_reason=lambda _url: "web_url_blocked_internal",
        )

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["reason_code"], "web_url_blocked_internal")
        self.assertEqual(result["error_class"], "crawl_url_blocked")
        self.assertEqual(result["markdown"], "")

    def test_explicit_url_reader_uses_raw_only_after_empty_fit(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_crawl(_url: str, **kwargs: object) -> dict[str, object]:
            calls.append(dict(kwargs))
            if kwargs["filter_type"] == "fit":
                return {"status": "empty", "markdown": "", "filter": "fit"}
            return {"status": "success", "markdown": "SYNTHETIC_RAW", "filter": "raw"}

        result = web_search_readers.read_explicit_url_with_status(
            "https://93.184.216.34/article",
            crawl_func=fake_crawl,
        )

        self.assertEqual([call["filter_type"] for call in calls], ["fit", "raw"])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["markdown"], "SYNTHETIC_RAW")
        self.assertTrue(result["raw_fallback_used"])
        self.assertEqual(result["crawl_primary_status"], "empty")
        self.assertEqual(result["crawl_fallback_status"], "success")
        self.assertEqual(result["crawl_fallback_reason"], "fit_empty_raw_fallback")

    def test_pdf_adapter_preserves_direct_reader_result(self) -> None:
        observed: dict[str, object] = {}
        crawl_like = {
            "status": "success",
            "markdown": "SYNTHETIC_PDF_TEXT",
            "web_pdf_read_attempted": True,
        }
        result_object = SimpleNamespace(
            detected=True,
            to_crawl_like_result=lambda: dict(crawl_like),
        )

        def fake_read_pdf_url(url: str, **kwargs: object) -> object:
            observed.update(url=url, kwargs=dict(kwargs))
            return result_object

        result = web_search_readers.read_pdf_as_crawl_result(
            "https://93.184.216.34/document.pdf",
            max_chars=321,
            probe_content_type=True,
            pdf_reader_module=SimpleNamespace(
                DEFAULT_MAX_CHARS=999,
                read_pdf_url=fake_read_pdf_url,
            ),
        )

        self.assertEqual(observed["url"], "https://93.184.216.34/document.pdf")
        self.assertEqual(observed["kwargs"], {"max_chars": 321, "probe_content_type": True})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["markdown"], "SYNTHETIC_PDF_TEXT")
        self.assertEqual(result["crawl_max_chars"], 321)

    def test_crawl_error_log_keeps_url_query_exception_and_secret_redacted(self) -> None:
        def fail_post(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("SYNTHETIC_RAW_EXCEPTION")

        with self.assertLogs("frida.web_search", level="WARNING") as captured:
            result = web_search_readers.crawl_markdown_with_status(
                "https://sensitive.invalid/private?token=SYNTHETIC_QUERY_SECRET#frag",
                filter_type="fit",
                query="SYNTHETIC_RAW_QUERY",
                runtime_service_value=lambda _field: "https://crawl.invalid",
                runtime_token=lambda: "SYNTHETIC_RAW_TOKEN",
                requests_module=SimpleNamespace(post=fail_post),
                blocked_url_reason=lambda _url: "",
            )

        logs = "\n".join(captured.output)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_class"], "RuntimeError")
        self.assertIn("url_query_present=True", logs)
        self.assertIn("url_fragment_present=True", logs)
        self.assertIn("err_class=RuntimeError", logs)
        for forbidden in (
            "sensitive.invalid",
            "/private",
            "SYNTHETIC_QUERY_SECRET",
            "SYNTHETIC_RAW_QUERY",
            "SYNTHETIC_RAW_TOKEN",
            "SYNTHETIC_RAW_EXCEPTION",
        ):
            self.assertNotIn(forbidden, logs)

    def test_web_search_facade_uses_extracted_reader_boundary(self) -> None:
        sentinel = {"status": "success", "markdown": "SYNTHETIC_BOUNDARY"}
        with mock.patch.object(
            web_search.web_search_readers,
            "crawl_markdown_with_status",
            return_value=sentinel,
        ):
            result = web_search._crawl_markdown_with_status(
                "https://93.184.216.34/article"
            )

        self.assertIs(result, sentinel)


if __name__ == "__main__":
    unittest.main()
