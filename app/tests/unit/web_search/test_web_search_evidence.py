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

from tools import web_search_evidence


class WebSearchEvidenceTests(unittest.TestCase):
    def test_no_results_is_insufficient_but_not_external_fallback(self) -> None:
        fields = web_search_evidence.evaluate_web_evidence(
            {
                "enabled": True,
                "status": "skipped",
                "reason_code": "no_data",
                "results_count": 0,
                "source_material_summary": [],
                "used_content_kinds": [],
                "injected_chars": 0,
            }
        )

        self.assertEqual(fields["web_evidence_status"], "insufficient")
        self.assertIn("no_results", fields["web_evidence_reason_codes"])
        self.assertIn("can_answer_with_caveat", fields["web_evidence_guidance_codes"])
        self.assertTrue(fields["web_evidence_can_answer"])
        self.assertTrue(fields["web_evidence_requires_caveat"])
        self.assertFalse(fields["web_evidence_external_fallback_used"])

    def test_results_found_but_not_read_are_distinguished(self) -> None:
        fields = web_search_evidence.evaluate_web_evidence(
            {
                "enabled": True,
                "status": "ok",
                "results_count": 2,
                "source_material_summary": [
                    {
                        "rank": 1,
                        "url": "https://example.com/a",
                        "used_in_prompt": False,
                        "used_content_kind": "none",
                        "content_chars": 0,
                    },
                    {
                        "rank": 2,
                        "url": "https://example.org/b",
                        "used_in_prompt": False,
                        "used_content_kind": "none",
                        "content_chars": 0,
                    },
                ],
                "used_content_kinds": [],
                "injected_chars": 0,
            }
        )

        self.assertEqual(fields["web_evidence_status"], "insufficient")
        self.assertIn("results_found_but_not_read", fields["web_evidence_reason_codes"])

    def test_snippet_only_material_is_partial_and_not_a_direct_read(self) -> None:
        fields = web_search_evidence.evaluate_web_evidence(
            {
                "enabled": True,
                "status": "ok",
                "results_count": 1,
                "source_material_summary": [
                    {
                        "rank": 1,
                        "url": "https://example.com/a",
                        "used_in_prompt": True,
                        "used_content_kind": "search_snippet",
                        "content_chars": 90,
                    },
                ],
                "used_content_kinds": ["search_snippet"],
                "injected_chars": 90,
            }
        )

        self.assertEqual(fields["web_evidence_status"], "partial")
        self.assertIn("snippet_only_material", fields["web_evidence_reason_codes"])
        self.assertTrue(fields["web_evidence_requires_caveat"])

    def test_profile_expected_source_missing_is_partial_evidence(self) -> None:
        fields = web_search_evidence.evaluate_web_evidence(
            {
                "enabled": True,
                "status": "ok",
                "results_count": 1,
                "source_material_summary": [
                    {
                        "rank": 1,
                        "url": "https://blog.example/tutorial",
                        "used_in_prompt": True,
                        "used_content_kind": "crawl_markdown",
                        "content_chars": 900,
                    },
                ],
                "used_content_kinds": ["crawl_markdown"],
                "injected_chars": 900,
                "profile_insufficient_evidence": True,
                "profile_insufficient_evidence_reason_codes": [
                    "expected_authority_material_missing",
                ],
            }
        )

        self.assertEqual(fields["web_evidence_status"], "partial")
        self.assertIn("expected_source_material_missing", fields["web_evidence_reason_codes"])
        self.assertIn("state_evidence_limits_naturally", fields["web_evidence_guidance_codes"])

    def test_situated_secondary_without_official_material_is_visible(self) -> None:
        fields = web_search_evidence.evaluate_web_evidence(
            {
                "enabled": True,
                "status": "ok",
                "results_count": 1,
                "source_material_summary": [
                    {
                        "rank": 1,
                        "url": "https://syndicat.example/tract",
                        "used_in_prompt": True,
                        "used_content_kind": "crawl_markdown",
                        "content_chars": 900,
                    },
                ],
                "used_content_kinds": ["crawl_markdown"],
                "injected_chars": 900,
                "profile_insufficient_evidence": True,
                "profile_insufficient_evidence_reason_codes": [
                    "situated_secondary_without_official_material",
                ],
            }
        )

        self.assertEqual(fields["web_evidence_status"], "partial")
        self.assertIn("situated_secondary_without_official_material", fields["web_evidence_reason_codes"])

    def test_explicit_url_failed_read_preserves_read_state_and_forbids_direct_read_claim(self) -> None:
        fields = web_search_evidence.evaluate_web_evidence(
            {
                "enabled": True,
                "status": "skipped",
                "explicit_url_detected": True,
                "read_state": "page_not_read_crawl_empty",
                "results_count": 0,
            }
        )

        self.assertEqual(fields["web_evidence_status"], "insufficient")
        self.assertIn("explicit_url_crawl_empty", fields["web_evidence_reason_codes"])
        self.assertIn("do_not_claim_direct_read", fields["web_evidence_guidance_codes"])
        self.assertEqual(fields["web_evidence_inputs_summary"]["read_state"], "page_not_read_crawl_empty")

    def test_output_does_not_echo_raw_query_or_content(self) -> None:
        fields = web_search_evidence.evaluate_web_evidence(
            {
                "enabled": True,
                "status": "ok",
                "query": "requete sensible a ne pas logger",
                "context_block": "CONTENU BRUT A NE PAS LOGGUER",
                "results_count": 1,
                "source_material_summary": [
                    {
                        "rank": 1,
                        "url": "https://example.com/a",
                        "used_in_prompt": True,
                        "used_content_kind": "crawl_markdown",
                        "content_chars": 1200,
                    },
                ],
                "used_content_kinds": ["crawl_markdown"],
                "injected_chars": 1200,
            }
        )

        serialized = json.dumps(fields, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("requete sensible a ne pas logger", serialized)
        self.assertNotIn("CONTENU BRUT A NE PAS LOGGUER", serialized)


if __name__ == "__main__":
    unittest.main()
