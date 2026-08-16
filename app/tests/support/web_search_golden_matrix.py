from __future__ import annotations

import copy
import json
from types import SimpleNamespace
from typing import Any
from unittest import mock

from tools import web_search


RAW_USER_SENTINEL = "LOT9C_RAW_USER_SENTINEL"
RAW_QUERY_SENTINEL = "LOT9C_RAW_QUERY_SENTINEL"
RAW_CONTENT_SENTINEL = "LOT9C_RAW_CONTENT_SENTINEL"
RAW_URL_SENTINEL = "LOT9C_RAW_URL_SENTINEL"
RAW_EXCEPTION_SENTINEL = "LOT9C_RAW_EXCEPTION_SENTINEL"
RAW_SECRET_SENTINEL = "LOT9C_RAW_SECRET_SENTINEL"

EXPLICIT_HTML_URL = f"https://golden.invalid/{RAW_URL_SENTINEL}?q=private"
EXPLICIT_PDF_URL = f"https://golden.invalid/{RAW_URL_SENTINEL}.pdf?q=private"

CASE_IDS = (
    "explicit_url_success",
    "explicit_url_crawl_timeout",
    "explicit_url_crawl_error",
    "explicit_url_pdf",
    "searxng_no_results",
    "searxng_upstream_error",
    "discovery_no_results",
    "discovery_upstream_error",
)

GOLDEN_FIELDS = (
    "case_id",
    "status",
    "reason_code",
    "error_class",
    "collection_path",
    "explicit_url_detected",
    "read_state",
    "primary_read_status",
    "results_count",
    "source_count",
    "context_injected",
    "used_content_kinds",
    "web_pdf_read_attempted_count",
    "web_evidence_status",
    "web_confidence_level",
    "discovery_provider_effective",
    "discovery_error_kind",
    "event_status",
    "event_reason_code",
    "event_context_injected",
    "event_query_included",
    "event_explicit_url_included",
    "branch_skipped_count",
    "error_event_count",
)


class _JsonResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return copy.deepcopy(self._payload)


def _runtime_value(field: str) -> Any:
    return {
        "searxng_url": "https://searxng.invalid",
        "searxng_results": 5,
        "crawl4ai_url": "https://crawl4ai.invalid",
        "crawl4ai_top_n": 1,
        "crawl4ai_max_chars": 400,
        "crawl4ai_explicit_url_max_chars": 400,
    }.get(field)


def _pdf_result(case_id: str, url: str) -> Any:
    if case_id == "explicit_url_pdf":
        return web_search.web_pdf_reader.WebPdfReadResult(
            url=url,
            status="success",
            reason_code="web_pdf_read_success",
            attempted=True,
            detected=True,
            media_type="application/pdf",
            text=RAW_CONTENT_SENTINEL,
            bytes_read=321,
            pages=1,
            chars=len(RAW_CONTENT_SENTINEL),
            elapsed_ms=7,
        )
    return web_search.web_pdf_reader.WebPdfReadResult(
        url=url,
        status="skipped",
        reason_code="web_pdf_not_detected",
        attempted=False,
        detected=False,
    )


def _user_message(case_id: str) -> str:
    if case_id == "explicit_url_pdf":
        return f"{RAW_USER_SENTINEL} {EXPLICIT_PDF_URL}"
    if case_id.startswith("explicit_url_"):
        return f"{RAW_USER_SENTINEL} {EXPLICIT_HTML_URL}"
    return RAW_USER_SENTINEL


def exercise_web_case(case_id: str) -> dict[str, Any]:
    if case_id not in CASE_IDS:
        raise ValueError(f"unknown web golden case: {case_id}")
    emitted: list[dict[str, Any]] = []

    def capture_emit(stage: str, **kwargs: Any) -> None:
        emitted.append({"kind": "event", "stage": stage, **copy.deepcopy(kwargs)})

    def fake_get(*_args: Any, **_kwargs: Any) -> _JsonResponse:
        if case_id == "searxng_upstream_error":
            raise TimeoutError(RAW_EXCEPTION_SENTINEL)
        return _JsonResponse({"results": []})

    def fake_post(*_args: Any, **_kwargs: Any) -> _JsonResponse:
        return _JsonResponse({"choices": [{"message": {"annotations": []}}]})

    def fake_crawl_post(*_args: Any, **kwargs: Any) -> _JsonResponse:
        if case_id == "explicit_url_crawl_timeout":
            raise TimeoutError(RAW_EXCEPTION_SENTINEL)
        if case_id == "explicit_url_crawl_error":
            raise RuntimeError(RAW_EXCEPTION_SENTINEL)
        if case_id == "explicit_url_success":
            request_payload = dict(kwargs.get("json") or {})
            return _JsonResponse(
                {
                    "success": True,
                    "markdown": RAW_CONTENT_SENTINEL,
                    "filter": str(request_payload.get("f") or "fit"),
                }
            )
        raise AssertionError(f"unexpected Crawl4AI transport call for {case_id}")

    if case_id == "discovery_upstream_error":
        headers = lambda **_kwargs: (_ for _ in ()).throw(  # noqa: E731
            RuntimeError(RAW_EXCEPTION_SENTINEL)
        )
    else:
        headers = lambda **_kwargs: {"X-Frida-Caller": "web_discovery"}  # noqa: E731
    llm_module = SimpleNamespace(
        or_chat_completions_url=lambda: "https://provider.invalid/chat/completions",
        or_headers_custom=headers,
        read_openrouter_response_payload=lambda response: response.json(),
    )
    discovery_provider = "openrouter_exa" if case_id.startswith("discovery_") else "local"

    with mock.patch.object(web_search, "_runtime_services_value", side_effect=_runtime_value), mock.patch.object(
        web_search, "_runtime_crawl4ai_token", return_value=RAW_SECRET_SENTINEL
    ), mock.patch.object(
        web_search, "reformulate", return_value=RAW_QUERY_SENTINEL
    ), mock.patch.object(
        web_search.web_pdf_reader,
        "read_pdf_url",
        side_effect=lambda url, **_kwargs: _pdf_result(case_id, url),
    ), mock.patch.object(
        web_search.requests, "get", side_effect=fake_get
    ), mock.patch.object(
        web_search.requests, "post", side_effect=fake_crawl_post
    ), mock.patch.object(
        web_search.web_public_url_policy.socket,
        "getaddrinfo",
        return_value=[(None, None, None, "", ("93.184.216.34", 0))],
    ), mock.patch.object(
        web_search.chat_turn_logger, "emit", side_effect=capture_emit
    ), mock.patch.object(
        web_search.chat_turn_logger,
        "emit_branch_skipped",
        side_effect=lambda **kwargs: emitted.append(
            {"kind": "branch_skipped", **copy.deepcopy(kwargs)}
        ),
    ), mock.patch.object(
        web_search.chat_turn_logger,
        "emit_error",
        side_effect=lambda **kwargs: emitted.append(
            {"kind": "error", **copy.deepcopy(kwargs)}
        ),
    ):
        payload = web_search.build_context_payload(
            _user_message(case_id),
            requests_module=SimpleNamespace(post=fake_post),
            llm_module=llm_module,
            now_iso="2026-08-16T12:00:00Z",
            enable_specialized_queries=False,
            enable_profiled_searxng_params=False,
            enable_reranking=False,
            enable_profiled_crawl4ai_policy=False,
            discovery_provider=discovery_provider,
        )
    return {"case_id": case_id, "payload": payload, "events": emitted}


def exercise_web_matrix() -> tuple[dict[str, Any], ...]:
    return tuple(exercise_web_case(case_id) for case_id in CASE_IDS)


def project_web_case(case: dict[str, Any]) -> tuple[Any, ...]:
    payload = dict(case["payload"])
    events = list(case["events"])
    web_event = next(
        event
        for event in events
        if event.get("kind") == "event" and event.get("stage") == "web_search"
    )
    event_payload = dict(web_event.get("payload") or {})
    projected = {
        "case_id": str(case["case_id"]),
        "status": str(payload.get("status") or ""),
        "reason_code": str(payload.get("reason_code") or ""),
        "error_class": str(payload.get("error_class") or ""),
        "collection_path": str(payload.get("collection_path") or ""),
        "explicit_url_detected": bool(payload.get("explicit_url_detected")),
        "read_state": str(payload.get("read_state") or ""),
        "primary_read_status": str(payload.get("primary_read_status") or ""),
        "results_count": int(payload.get("results_count") or 0),
        "source_count": len(list(payload.get("sources") or [])),
        "context_injected": bool(payload.get("context_block")),
        "used_content_kinds": tuple(payload.get("used_content_kinds") or ()),
        "web_pdf_read_attempted_count": int(payload.get("web_pdf_read_attempted_count") or 0),
        "web_evidence_status": str(payload.get("web_evidence_status") or ""),
        "web_confidence_level": str(payload.get("web_confidence_level") or ""),
        "discovery_provider_effective": str(payload.get("web_discovery_provider_effective") or ""),
        "discovery_error_kind": str(payload.get("web_discovery_external_error_kind") or ""),
        "event_status": str(web_event.get("status") or ""),
        "event_reason_code": str(web_event.get("reason_code") or ""),
        "event_context_injected": bool(event_payload.get("context_injected")),
        "event_query_included": bool(event_payload.get("query_preview")),
        "event_explicit_url_included": bool(event_payload.get("explicit_url_included")),
        "branch_skipped_count": sum(event.get("kind") == "branch_skipped" for event in events),
        "error_event_count": sum(event.get("kind") == "error" for event in events),
    }
    return tuple(projected[field] for field in GOLDEN_FIELDS)


# Fields follow GOLDEN_FIELDS. Only compact product-observable semantics are frozen.
EXPECTED_WEB_GOLDEN_MATRIX = (
    ("explicit_url_success", "ok", "", "", "explicit_url_direct", True, "page_read", "success", 1, 1, True, ("crawl_markdown",), 0, "sufficient", "high", "local", "", "ok", "", True, False, False, 0, 0),
    ("explicit_url_crawl_timeout", "skipped", "no_data", "", "explicit_url_fallback_search", True, "page_not_read_error", "error", 0, 1, False, (), 0, "insufficient", "low", "local", "", "skipped", "no_data", False, False, False, 1, 0),
    ("explicit_url_crawl_error", "skipped", "no_data", "", "explicit_url_fallback_search", True, "page_not_read_error", "error", 0, 1, False, (), 0, "insufficient", "low", "local", "", "skipped", "no_data", False, False, False, 1, 0),
    ("explicit_url_pdf", "ok", "", "", "explicit_url_direct", True, "page_read", "success", 1, 1, True, ("web_pdf_text",), 1, "sufficient", "high", "local", "", "ok", "", True, False, False, 0, 0),
    ("searxng_no_results", "skipped", "no_data", "", "search_only", False, "", "not_attempted", 0, 0, False, (), 0, "insufficient", "low", "local", "", "skipped", "no_data", False, False, False, 1, 0),
    ("searxng_upstream_error", "error", "web_search_upstream_error", "TimeoutError", "search_only", False, "", "not_attempted", 0, 0, False, (), 0, "insufficient", "low", "local", "", "error", "web_search_upstream_error", False, False, False, 0, 1),
    ("discovery_no_results", "skipped", "no_data", "", "search_only", False, "", "not_attempted", 0, 0, False, (), 0, "insufficient", "low", "openrouter_exa", "", "skipped", "no_data", False, False, False, 1, 0),
    ("discovery_upstream_error", "error", "web_discovery_upstream_error", "WebDiscoveryUpstreamError", "search_only", False, "", "not_attempted", 0, 0, False, (), 0, "insufficient", "low", "openrouter_exa", "openrouter_config_error", "error", "web_discovery_upstream_error", False, False, False, 0, 1),
)


def assert_web_golden_matrix(actual: tuple[tuple[Any, ...], ...]) -> None:
    if actual != EXPECTED_WEB_GOLDEN_MATRIX:
        raise AssertionError("web golden matrix changed")


def assert_content_free_projection(value: Any) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    forbidden = (
        RAW_USER_SENTINEL,
        RAW_QUERY_SENTINEL,
        RAW_CONTENT_SENTINEL,
        RAW_URL_SENTINEL,
        RAW_EXCEPTION_SENTINEL,
        RAW_SECRET_SENTINEL,
        "https://",
    )
    if any(item in encoded for item in forbidden):
        raise AssertionError("raw web material reached content-free projection")
