from __future__ import annotations

import json
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

from tools import web_search_confidence


class WebSearchConfidenceTests(unittest.TestCase):
    def test_explicit_url_page_read_is_high_and_non_actionable(self) -> None:
        fields = web_search_confidence.evaluate_web_confidence(
            {
                "enabled": True,
                "status": "ok",
                "explicit_url_detected": True,
                "collection_path": "explicit_url_direct",
                "read_state": "page_read",
                "results_count": 1,
                "source_material_summary": [
                    {
                        "rank": 1,
                        "url": "https://example.com/article",
                        "used_in_prompt": True,
                        "used_content_kind": "crawl_markdown",
                        "crawl_status": "success",
                        "content_chars": 1200,
                    }
                ],
                "crawl4ai_extraction_summary": [
                    {
                        "rank": 1,
                        "url": "https://example.com/article",
                        "crawl_status": "success",
                        "used_content_kind": "crawl_markdown",
                    }
                ],
                "used_content_kinds": ["crawl_markdown"],
                "injected_chars": 1200,
                "context_chars": 1400,
            }
        )

        self.assertEqual(fields["web_confidence_level"], "high")
        self.assertGreaterEqual(fields["web_confidence_score"], 0.78)
        self.assertIn("explicit_url_page_read", fields["web_confidence_reason_codes"])
        self.assertEqual(fields["openrouter_fallback_state"], "future_only")
        self.assertFalse(fields["openrouter_fallback_used"])

    def test_search_with_diverse_crawled_material_is_high(self) -> None:
        fields = web_search_confidence.evaluate_web_confidence(
            {
                "enabled": True,
                "status": "ok",
                "explicit_url_detected": False,
                "results_count": 2,
                "query_count": 3,
                "deduped_result_count": 2,
                "source_material_summary": [
                    {
                        "rank": 1,
                        "url": "https://docs.example/api",
                        "used_in_prompt": True,
                        "used_content_kind": "crawl_markdown",
                        "crawl_status": "success",
                        "content_chars": 900,
                    },
                    {
                        "rank": 2,
                        "url": "https://learn.example/reference",
                        "used_in_prompt": True,
                        "used_content_kind": "crawl_markdown",
                        "crawl_status": "success",
                        "content_chars": 900,
                    },
                ],
                "crawl4ai_extraction_summary": [
                    {"url": "https://docs.example/api", "crawl_status": "success"},
                    {"url": "https://learn.example/reference", "crawl_status": "success"},
                ],
                "used_content_kinds": ["crawl_markdown"],
                "injected_chars": 1800,
                "context_chars": 2200,
                "rerank_applied": True,
                "rerank_reason_counts": {"technical_docs_like_soft_bonus": 1},
            }
        )

        self.assertEqual(fields["web_confidence_level"], "high")
        self.assertIn("multi_domain_material", fields["web_confidence_reason_codes"])
        self.assertEqual(fields["web_confidence_inputs_summary"]["domain_count"], 2)
        self.assertEqual(fields["web_confidence_inputs_summary"]["used_domain_count"], 2)
        self.assertIn("rerank_signal_present", fields["web_confidence_reason_codes"])
        self.assertFalse(fields["openrouter_fallback_used"])

    def test_crawl_failure_used_as_prompt_material_caps_confidence(self) -> None:
        fields = web_search_confidence.evaluate_web_confidence(
            {
                "enabled": True,
                "status": "ok",
                "explicit_url_detected": False,
                "results_count": 2,
                "query_count": 3,
                "deduped_result_count": 2,
                "source_material_summary": [
                    {
                        "rank": 1,
                        "url": "https://institution.example/policy",
                        "used_in_prompt": True,
                        "used_content_kind": "crawl_markdown",
                        "crawl_status": "success",
                        "content_chars": 1200,
                    },
                    {
                        "rank": 2,
                        "url": "https://document.example/official.pdf",
                        "used_in_prompt": True,
                        "used_content_kind": "search_snippet",
                        "crawl_status": "error",
                        "content_chars": 180,
                    },
                ],
                "crawl4ai_extraction_summary": [
                    {"url": "https://institution.example/policy", "crawl_status": "success"},
                    {"url": "https://document.example/official.pdf", "crawl_status": "error"},
                ],
                "used_content_kinds": ["crawl_markdown", "search_snippet"],
                "injected_chars": 1380,
                "context_chars": 1600,
                "rerank_applied": True,
            }
        )

        self.assertEqual(fields["web_confidence_level"], "medium")
        self.assertLess(fields["web_confidence_score"], 0.78)
        self.assertEqual(fields["web_confidence_inputs_summary"]["crawl_failed_used_source_count"], 1)
        self.assertIn("crawl_empty_or_error_present", fields["web_confidence_reason_codes"])
        self.assertIn("crawl_failed_prompt_material_used", fields["web_confidence_reason_codes"])
        self.assertIn("crawl_partial_failure_limits_confidence", fields["web_confidence_reason_codes"])
        self.assertFalse(fields["openrouter_fallback_used"])

    def test_unused_crawl_failure_does_not_cap_high_confidence(self) -> None:
        fields = web_search_confidence.evaluate_web_confidence(
            {
                "enabled": True,
                "status": "ok",
                "explicit_url_detected": False,
                "results_count": 3,
                "query_count": 3,
                "deduped_result_count": 3,
                "source_material_summary": [
                    {
                        "rank": 1,
                        "url": "https://institution.example/policy",
                        "used_in_prompt": True,
                        "used_content_kind": "crawl_markdown",
                        "crawl_status": "success",
                        "content_chars": 1100,
                    },
                    {
                        "rank": 2,
                        "url": "https://analysis.example/report",
                        "used_in_prompt": True,
                        "used_content_kind": "crawl_markdown",
                        "crawl_status": "success",
                        "content_chars": 900,
                    },
                    {
                        "rank": 3,
                        "url": "https://failed.example/pdf",
                        "used_in_prompt": False,
                        "used_content_kind": "none",
                        "crawl_status": "error",
                        "content_chars": 0,
                    },
                ],
                "crawl4ai_extraction_summary": [
                    {"url": "https://institution.example/policy", "crawl_status": "success"},
                    {"url": "https://analysis.example/report", "crawl_status": "success"},
                    {"url": "https://failed.example/pdf", "crawl_status": "error"},
                ],
                "used_content_kinds": ["crawl_markdown"],
                "injected_chars": 2000,
                "context_chars": 2300,
                "rerank_applied": True,
            }
        )

        self.assertEqual(fields["web_confidence_level"], "high")
        self.assertEqual(fields["web_confidence_inputs_summary"]["crawl_failed_used_source_count"], 0)
        self.assertIn("crawl_empty_or_error_present", fields["web_confidence_reason_codes"])
        self.assertNotIn("crawl_failed_prompt_material_used", fields["web_confidence_reason_codes"])

    def test_unused_result_domain_does_not_create_multi_domain_confidence(self) -> None:
        base_payload = {
            "enabled": True,
            "status": "ok",
            "explicit_url_detected": False,
            "results_count": 2,
            "query_count": 1,
            "deduped_result_count": 2,
            "source_material_summary": [
                {
                    "rank": 1,
                    "url": "https://docs.example/api",
                    "used_in_prompt": True,
                    "used_content_kind": "crawl_markdown",
                    "crawl_status": "success",
                    "content_chars": 900,
                },
                {
                    "rank": 2,
                    "url": "https://unused.example/article",
                    "used_in_prompt": False,
                    "used_content_kind": "none",
                    "crawl_status": "not_attempted",
                    "content_chars": 0,
                },
            ],
            "crawl4ai_extraction_summary": [
                {"url": "https://docs.example/api", "crawl_status": "success"}
            ],
            "used_content_kinds": ["crawl_markdown"],
            "injected_chars": 900,
            "context_chars": 1200,
        }
        one_used_domain = web_search_confidence.evaluate_web_confidence(base_payload)
        two_used_domains_payload = dict(base_payload)
        two_used_domains_payload["source_material_summary"] = [
            dict(base_payload["source_material_summary"][0]),
            {
                "rank": 2,
                "url": "https://unused.example/article",
                "used_in_prompt": True,
                "used_content_kind": "crawl_markdown",
                "crawl_status": "success",
                "content_chars": 700,
            },
        ]
        two_used_domains_payload["crawl4ai_extraction_summary"] = [
            {"url": "https://docs.example/api", "crawl_status": "success"},
            {"url": "https://unused.example/article", "crawl_status": "success"},
        ]
        two_used_domains_payload["injected_chars"] = 1600
        two_used_domains_payload["context_chars"] = 1900
        two_used_domains = web_search_confidence.evaluate_web_confidence(two_used_domains_payload)

        self.assertEqual(one_used_domain["web_confidence_inputs_summary"]["domain_count"], 2)
        self.assertEqual(one_used_domain["web_confidence_inputs_summary"]["used_domain_count"], 1)
        self.assertNotIn("multi_domain_material", one_used_domain["web_confidence_reason_codes"])
        self.assertIn("single_domain_material", one_used_domain["web_confidence_reason_codes"])
        self.assertEqual(two_used_domains["web_confidence_inputs_summary"]["used_domain_count"], 2)
        self.assertIn("multi_domain_material", two_used_domains["web_confidence_reason_codes"])
        self.assertLess(
            one_used_domain["web_confidence_score"],
            two_used_domains["web_confidence_score"],
        )

    def test_no_data_is_low_and_human_review_candidate_only(self) -> None:
        fields = web_search_confidence.evaluate_web_confidence(
            {
                "enabled": True,
                "status": "skipped",
                "reason_code": "no_data",
                "results_count": 0,
                "source_material_summary": [],
                "used_content_kinds": [],
                "injected_chars": 0,
                "context_chars": 0,
            }
        )

        self.assertEqual(fields["web_confidence_level"], "low")
        self.assertIn("no_data", fields["web_confidence_reason_codes"])
        self.assertEqual(fields["openrouter_fallback_state"], "human_review_candidate")
        self.assertFalse(fields["openrouter_fallback_used"])
        self.assertIn("external_fallback_disabled_lot7", fields["openrouter_fallback_reason_codes"])

    def test_explicit_url_no_data_keeps_read_state_reason_visible(self) -> None:
        fields = web_search_confidence.evaluate_web_confidence(
            {
                "enabled": True,
                "status": "skipped",
                "reason_code": "no_data",
                "explicit_url_detected": True,
                "read_state": "page_not_read_crawl_empty",
                "results_count": 0,
                "source_material_summary": [
                    {
                        "rank": 1,
                        "url": "https://example.com/article",
                        "used_in_prompt": False,
                        "used_content_kind": "none",
                        "crawl_status": "empty",
                        "content_chars": 0,
                    }
                ],
                "used_content_kinds": [],
                "injected_chars": 0,
                "context_chars": 0,
            }
        )

        self.assertEqual(fields["web_confidence_level"], "low")
        self.assertIn("explicit_url_not_read", fields["web_confidence_reason_codes"])
        self.assertIn("no_data", fields["web_confidence_reason_codes"])
        self.assertEqual(fields["web_confidence_inputs_summary"]["read_state"], "page_not_read_crawl_empty")
        self.assertFalse(fields["openrouter_fallback_used"])

    def test_snippet_only_material_stays_low(self) -> None:
        fields = web_search_confidence.evaluate_web_confidence(
            {
                "enabled": True,
                "status": "ok",
                "results_count": 1,
                "source_material_summary": [
                    {
                        "rank": 1,
                        "url": "https://result.example/article",
                        "used_in_prompt": True,
                        "used_content_kind": "search_snippet",
                        "crawl_status": "not_attempted",
                        "content_chars": 90,
                    }
                ],
                "crawl4ai_extraction_summary": [],
                "used_content_kinds": ["search_snippet"],
                "injected_chars": 90,
                "context_chars": 160,
            }
        )

        self.assertEqual(fields["web_confidence_level"], "low")
        self.assertLess(fields["web_confidence_score"], 0.5)
        self.assertIn("snippet_only_material", fields["web_confidence_reason_codes"])
        self.assertFalse(fields["openrouter_fallback_used"])

    def test_pdf_text_material_counts_as_readable_web_material(self) -> None:
        fields = web_search_confidence.evaluate_web_confidence(
            {
                "enabled": True,
                "status": "ok",
                "explicit_url_detected": False,
                "results_count": 1,
                "query_count": 1,
                "deduped_result_count": 1,
                "source_material_summary": [
                    {
                        "rank": 1,
                        "url": "https://example.com/report.pdf",
                        "used_in_prompt": True,
                        "used_content_kind": "web_pdf_text",
                        "crawl_status": "success",
                        "content_chars": 1200,
                    }
                ],
                "crawl4ai_extraction_summary": [
                    {
                        "rank": 1,
                        "url": "https://example.com/report.pdf",
                        "crawl_status": "success",
                        "used_content_kind": "web_pdf_text",
                    }
                ],
                "used_content_kinds": ["web_pdf_text"],
                "injected_chars": 1200,
                "context_chars": 1500,
            }
        )

        self.assertEqual(fields["web_confidence_level"], "high")
        self.assertIn("readable_web_material_used", fields["web_confidence_reason_codes"])
        self.assertIn("web_pdf_text_used", fields["web_confidence_reason_codes"])
        self.assertNotIn("snippet_only_material", fields["web_confidence_reason_codes"])

    def test_confidence_output_does_not_echo_raw_query_or_content(self) -> None:
        raw_query = "documentation privée avec détail sensible"
        raw_content = "PASSAGE DOCUMENTAIRE BRUT A NE PAS LOGGUER"
        fields = web_search_confidence.evaluate_web_confidence(
            {
                "enabled": True,
                "status": "ok",
                "query": raw_query,
                "context_block": raw_content,
                "results_count": 1,
                "source_material_summary": [
                    {
                        "rank": 1,
                        "url": "https://docs.example/api",
                        "used_in_prompt": True,
                        "used_content_kind": "crawl_markdown",
                        "crawl_status": "success",
                        "content_chars": len(raw_content),
                    }
                ],
                "crawl4ai_extraction_summary": [
                    {"url": "https://docs.example/api", "crawl_status": "success"}
                ],
                "used_content_kinds": ["crawl_markdown"],
                "injected_chars": len(raw_content),
                "context_chars": len(raw_content),
            }
        )

        serialized = json.dumps(fields, ensure_ascii=False, sort_keys=True)
        self.assertNotIn(raw_query, serialized)
        self.assertNotIn(raw_content, serialized)
        self.assertFalse(fields["openrouter_fallback_used"])


if __name__ == "__main__":
    unittest.main()
