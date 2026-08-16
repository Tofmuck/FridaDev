from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tools import web_search, web_search_profile, web_search_runtime_events


class WebSearchRuntimeEventsTests(unittest.TestCase):
    def test_payload_augmentation_derives_stable_summaries_and_counters(self) -> None:
        payload = {
            "enabled": True,
            "status": "ok",
            "reason_code": None,
            "collection_path": "search_only",
            "search_profile": web_search_profile.PROFILE_GENERAL,
            "results_count": 2,
            "context_block": "SYNTHETIC_CONTEXT",
            "sources": [
                {
                    "rank": 1,
                    "url": "https://one.invalid/a",
                    "source_origin": "search_result",
                    "used_in_prompt": True,
                    "used_content_kind": "crawl_markdown",
                    "content_used": "SYNTHETIC_ONE",
                    "crawl_status": "success",
                    "crawl_filter": "fit",
                    "crawl_policy_kind": "historical_fit",
                    "crawl_cache_mode": "1",
                    "web_pdf_read_attempted": False,
                },
                {
                    "rank": 2,
                    "url": "https://two.invalid/b.pdf",
                    "source_origin": "search_result",
                    "used_in_prompt": True,
                    "used_content_kind": "web_pdf_text",
                    "content_used": "SYNTHETIC_TWO",
                    "crawl_status": "success",
                    "crawl_filter": "raw",
                    "crawl_policy_kind": "pdf_direct",
                    "crawl_cache_mode": "0",
                    "web_pdf_read_attempted": True,
                    "web_pdf_read_status": "success",
                    "web_pdf_read_reason_code": "web_pdf_read_success",
                    "web_pdf_read_pages": 3,
                    "web_pdf_read_bytes": 123,
                    "web_pdf_read_chars": 13,
                    "web_pdf_read_elapsed_ms": 7,
                },
            ],
        }

        result = web_search_runtime_events.augment_payload_observability(payload)

        self.assertIs(result, payload)
        self.assertEqual(result["used_content_kinds"], ["crawl_markdown", "web_pdf_text"])
        self.assertEqual(result["injected_chars"], 26)
        self.assertEqual(result["context_chars"], len("SYNTHETIC_CONTEXT"))
        self.assertEqual(result["web_pdf_read_attempted_count"], 1)
        self.assertEqual(result["web_pdf_read_status_counts"], {"success": 1})
        self.assertEqual(result["web_pdf_read_reason_codes"], ["web_pdf_read_success"])
        self.assertEqual(result["crawl4ai_filter_counts"], {"fit": 1, "raw": 1})
        self.assertEqual(result["crawl4ai_cache_modes"], {"0": 1, "1": 1})

    def test_event_projection_redacts_query_url_content_and_hashes(self) -> None:
        raw_query = "LOT9C4_RAW_QUERY"
        raw_url_marker = "LOT9C4_RAW_URL"
        raw_content = "LOT9C4_RAW_CONTENT"
        emitted: list[dict[str, object]] = []

        with mock.patch.object(
            web_search_runtime_events.chat_turn_logger,
            "emit",
            side_effect=lambda stage, **kwargs: emitted.append({"stage": stage, **kwargs}),
        ):
            web_search_runtime_events.emit_web_search_runtime_event(
                enabled=True,
                status="ok",
                reason_code=None,
                query_preview=raw_query,
                results_count=1,
                context_block=raw_content,
                explicit_url_detected=True,
                explicit_url=f"https://example.invalid/{raw_url_marker}?q=private",
                sources=[
                    {
                        "rank": 1,
                        "url": f"https://example.invalid/{raw_url_marker}?q=private",
                        "used_in_prompt": True,
                        "used_content_kind": "crawl_markdown",
                        "content_used": raw_content,
                        "crawl_status": "success",
                        "crawl_query_sha256_12": "abcdef123456",
                        "web_pdf_read_attempted": True,
                        "web_pdf_read_status": "success",
                    }
                ],
            )

        self.assertEqual(len(emitted), 1)
        event_payload = emitted[0]["payload"]
        encoded = json.dumps(event_payload, ensure_ascii=False, sort_keys=True)
        for forbidden in (raw_query, raw_url_marker, raw_content, "https://", "abcdef123456"):
            self.assertNotIn(forbidden, encoded)
        self.assertEqual(event_payload["query_preview"], "")
        self.assertTrue(event_payload["query_present"])
        self.assertFalse(event_payload["explicit_url_included"])
        self.assertFalse(event_payload["crawl4ai_query_hashes_included"])
        self.assertFalse(event_payload["web_pdf_read_summary"][0]["url_fingerprint_included"])

    def test_event_projection_preserves_supplied_confidence_and_evidence(self) -> None:
        forbidden = mock.Mock(side_effect=AssertionError("semantic evaluator must not rerun"))
        emitted: list[dict[str, object]] = []
        with mock.patch.object(
            web_search_runtime_events.web_search_confidence,
            "evaluate_web_confidence",
            forbidden,
        ), mock.patch.object(
            web_search_runtime_events.web_search_evidence,
            "evaluate_web_evidence",
            forbidden,
        ), mock.patch.object(
            web_search_runtime_events.chat_turn_logger,
            "emit",
            side_effect=lambda stage, **kwargs: emitted.append({"stage": stage, **kwargs}),
        ):
            web_search_runtime_events.emit_web_search_runtime_event(
                enabled=True,
                status="ok",
                reason_code=None,
                query_preview="SYNTHETIC_QUERY",
                results_count=0,
                context_block="",
                web_confidence_policy_kind="confidence_v1",
                web_confidence_level="medium",
                web_confidence_score=0.5,
                web_confidence_reason_codes=["synthetic_confidence"],
                web_confidence_inputs_summary={"used_source_count": 0},
                web_evidence_policy_kind="evidence_v1",
                web_evidence_status="partial",
                web_evidence_reason_codes=["synthetic_evidence"],
                web_evidence_guidance_codes=["state_evidence_limits_naturally"],
                web_evidence_inputs_summary={"results_count": 0},
                web_evidence_can_answer=True,
                web_evidence_requires_caveat=True,
                web_evidence_can_suggest_reformulation=True,
                web_evidence_url_request_policy="only_if_relevant_not_default",
            )

        event_payload = emitted[0]["payload"]
        self.assertEqual(event_payload["web_confidence_policy_kind"], "confidence_v1")
        self.assertEqual(event_payload["web_confidence_score"], 0.5)
        self.assertEqual(event_payload["web_evidence_policy_kind"], "evidence_v1")
        self.assertEqual(event_payload["web_evidence_status"], "partial")
        self.assertTrue(event_payload["web_evidence_requires_caveat"])

    def test_skipped_event_emits_one_branch_skip_without_error(self) -> None:
        branch_skips: list[dict[str, object]] = []
        errors: list[dict[str, object]] = []
        with mock.patch.object(
            web_search_runtime_events.chat_turn_logger,
            "emit",
            return_value=None,
        ), mock.patch.object(
            web_search_runtime_events.chat_turn_logger,
            "emit_branch_skipped",
            side_effect=lambda **kwargs: branch_skips.append(kwargs),
        ), mock.patch.object(
            web_search_runtime_events.chat_turn_logger,
            "emit_error",
            side_effect=lambda **kwargs: errors.append(kwargs),
        ):
            web_search_runtime_events.emit_web_search_runtime_event(
                enabled=True,
                status="skipped",
                reason_code="no_data",
                query_preview="SYNTHETIC_QUERY",
                results_count=0,
                context_block="",
            )

        self.assertEqual(branch_skips, [{"reason_code": "no_data", "reason_short": "web_search_no_results"}])
        self.assertEqual(errors, [])

    def test_error_event_emits_one_error_without_branch_skip(self) -> None:
        branch_skips: list[dict[str, object]] = []
        errors: list[dict[str, object]] = []
        with mock.patch.object(
            web_search_runtime_events.chat_turn_logger,
            "emit",
            return_value=None,
        ), mock.patch.object(
            web_search_runtime_events.chat_turn_logger,
            "emit_branch_skipped",
            side_effect=lambda **kwargs: branch_skips.append(kwargs),
        ), mock.patch.object(
            web_search_runtime_events.chat_turn_logger,
            "emit_error",
            side_effect=lambda **kwargs: errors.append(kwargs),
        ):
            web_search_runtime_events.emit_web_search_runtime_event(
                enabled=True,
                status="error",
                reason_code="web_search_upstream_error",
                query_preview="SYNTHETIC_QUERY",
                results_count=0,
                context_block="",
                error_class="TimeoutError",
                message_short="web_search_upstream_error",
            )

        self.assertEqual(branch_skips, [])
        self.assertEqual(
            errors,
            [
                {
                    "error_code": "web_search_upstream_error",
                    "error_class": "TimeoutError",
                    "message_short": "web_search_upstream_error",
                }
            ],
        )

    def test_web_search_facade_reaches_extracted_event_writer(self) -> None:
        writer = mock.Mock()
        with mock.patch.object(
            web_search_runtime_events,
            "emit_web_search_runtime_event",
            writer,
        ):
            web_search._emit_web_search_runtime_event(
                enabled=True,
                status="ok",
                reason_code=None,
                query_preview="SYNTHETIC_QUERY",
                results_count=0,
                context_block="",
            )

        writer.assert_called_once_with(
            enabled=True,
            status="ok",
            reason_code=None,
            query_preview="SYNTHETIC_QUERY",
            results_count=0,
            context_block="",
        )


if __name__ == "__main__":
    unittest.main()
