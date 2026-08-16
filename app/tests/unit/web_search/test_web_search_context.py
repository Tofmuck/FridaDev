from __future__ import annotations

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

from core.web_read_state import (
    READ_STATE_PAGE_NOT_READ_CRAWL_EMPTY,
    READ_STATE_PAGE_NOT_READ_ERROR,
    READ_STATE_PAGE_NOT_READ_SNIPPET_FALLBACK,
    READ_STATE_PAGE_PARTIALLY_READ,
    READ_STATE_PAGE_READ,
)
from tools import web_search, web_search_context, web_search_profile


class WebSearchContextTests(unittest.TestCase):
    def test_search_material_preserves_source_order_and_terminal_context(self) -> None:
        results = [
            {
                "title": "SYNTHETIC_OFFICIAL",
                "url": "https://official.invalid/reference",
                "content": "SYNTHETIC_OFFICIAL_CONTENT",
            },
            {
                "title": "SYNTHETIC_SITUATED",
                "url": "https://situated.invalid/analysis",
                "content": "SYNTHETIC_SITUATED_CONTENT",
            },
        ]

        def build_source(rank: int, result: dict[str, object], **_kwargs: object) -> dict[str, object]:
            return {
                "rank": rank,
                "title": result["title"],
                "url": result["url"],
                "source_domain": str(result["url"]).split("/")[2],
                "used_in_prompt": True,
                "used_content_kind": "search_snippet",
                "content_used": result["content"],
                "truncated": False,
                "crawl_status": "not_attempted",
            }

        material = web_search_context.build_search_context_material(
            "SYNTHETIC_QUERY",
            results,
            runtime={"crawl4ai_top_n": 2, "crawl4ai_max_chars": 500},
            today="16 aout 2026",
            search_profile=web_search_profile.PROFILE_GENERAL,
            build_source_payload=build_source,
        )

        self.assertEqual(
            [source["title"] for source in material["sources"]],
            ["SYNTHETIC_OFFICIAL", "SYNTHETIC_SITUATED"],
        )
        context = material["context_block"]
        self.assertLess(context.index("SYNTHETIC_OFFICIAL"), context.index("SYNTHETIC_SITUATED"))
        self.assertIn(web_search_context.WEB_SEARCH_SOURCE_ATTRIBUTION_LINE, context)
        self.assertTrue(context.endswith("[FIN DES RÉSULTATS WEB]"))
        self.assertEqual(material["runtime"]["crawl4ai_effective_top_n"], 2)
        self.assertEqual(material["results_count"], 2)

    def test_explicit_url_material_preserves_pdf_kind_budget_and_prompt_shape(self) -> None:
        material = web_search_context.build_explicit_url_context_material(
            "https://93.184.216.34/document.pdf",
            "SYNTHETIC_PDF_TEXT",
            crawl_result={
                "status": "success",
                "filter": "fit",
                "web_pdf_read_attempted": True,
                "web_pdf_read_detected": True,
                "web_pdf_read_status": "success",
                "web_pdf_read_reason_code": "web_pdf_read_success",
                "web_pdf_read_pages": 2,
            },
            runtime={
                "crawl4ai_max_chars": 100,
                "crawl4ai_explicit_url_max_chars": 321,
            },
            today="16 aout 2026",
        )

        source = material["sources"][0]
        self.assertEqual(source["used_content_kind"], "web_pdf_text")
        self.assertEqual(source["crawl_max_chars"], 321)
        self.assertEqual(source["web_pdf_read_pages"], 2)
        self.assertEqual(source["content_used"], "SYNTHETIC_PDF_TEXT")
        self.assertIn("Lecture directe PDF prioritaire reussie", material["context_block"])
        self.assertTrue(material["context_block"].endswith("[FIN DES RÉSULTATS WEB]"))

    def test_read_state_matrix_distinguishes_direct_partial_snippet_empty_and_error(self) -> None:
        cases = (
            ("success", [{"is_primary_source": True, "truncated": False}], READ_STATE_PAGE_READ),
            ("success", [{"is_primary_source": True, "truncated": True}], READ_STATE_PAGE_PARTIALLY_READ),
            (
                "error",
                [{"used_in_prompt": True, "used_content_kind": "search_snippet"}],
                READ_STATE_PAGE_NOT_READ_SNIPPET_FALLBACK,
            ),
            ("empty", [], READ_STATE_PAGE_NOT_READ_CRAWL_EMPTY),
            ("error", [], READ_STATE_PAGE_NOT_READ_ERROR),
        )
        for primary_status, sources, expected in cases:
            with self.subTest(primary_status=primary_status, expected=expected):
                self.assertEqual(
                    web_search_context.derive_read_state(
                        explicit_url="https://93.184.216.34/page",
                        primary_read_status=primary_status,
                        sources=sources,
                    ),
                    expected,
                )
        self.assertIsNone(
            web_search_context.derive_read_state(
                explicit_url=None,
                primary_read_status="success",
                sources=[],
            )
        )

    def test_payload_status_matrix_keeps_local_and_discovery_errors_distinct(self) -> None:
        cases = (
            (True, {}, ("ok", None, "")),
            (False, {}, ("skipped", "no_data", "")),
            (
                False,
                {"local_search_error_count": 1, "local_search_error_class": "TimeoutError"},
                ("error", "web_search_upstream_error", "TimeoutError"),
            ),
            (
                False,
                {
                    "web_discovery_external_error_kind": "openrouter_config_error",
                    "web_discovery_reason_codes": ["openrouter_exa_discovery_failed"],
                },
                ("error", "web_discovery_upstream_error", "WebDiscoveryUpstreamError"),
            ),
        )
        for has_results, query_plan, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(
                    web_search_context.web_search_payload_status(
                        has_results=has_results,
                        query_plan=query_plan,
                        local_error_reason_code="web_search_upstream_error",
                        discovery_error_reason_code="web_discovery_upstream_error",
                    ),
                    expected,
                )

    def test_evidence_augmentation_preserves_source_first_and_failure_guidance(self) -> None:
        payload = {
            "enabled": True,
            "status": "ok",
            "reason_code": None,
            "collection_path": "search_only",
            "read_state": None,
            "results_count": 1,
            "search_profile": web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS,
            "source_first_policy_kind": "source_first_authority_map_v0",
            "source_first_active": True,
            "source_first_authority": "SYNTHETIC_AUTHORITY",
            "sources": [
                {
                    "url": "https://cgt.fr/synthetic",
                    "source_domain": "cgt.fr",
                    "used_in_prompt": True,
                    "used_content_kind": "search_snippet",
                    "content_used": "SYNTHETIC_MATERIAL",
                }
            ],
            "source_material_summary": [
                {
                    "url": "https://cgt.fr/synthetic",
                    "used_in_prompt": True,
                    "used_content_kind": "search_snippet",
                    "content_chars": 18,
                    "crawl_status": "empty",
                }
            ],
            "crawl4ai_extraction_summary": [{"crawl_status": "empty"}],
            "used_content_kinds": ["search_snippet"],
            "injected_chars": 18,
            "context_chars": 64,
        }

        result = web_search_context.augment_payload_evidence(payload)

        self.assertIs(result, payload)
        self.assertTrue(result["source_first_active"])
        self.assertEqual(result["source_first_authority"], "SYNTHETIC_AUTHORITY")
        self.assertEqual(result["web_evidence_status"], "partial")
        self.assertIn(
            "expected_source_material_missing",
            result["web_evidence_reason_codes"],
        )
        self.assertIn(
            "situated_secondary_without_official_material",
            result["web_evidence_reason_codes"],
        )
        self.assertIn(
            "state_evidence_limits_naturally",
            result["web_evidence_guidance_codes"],
        )

    def test_web_search_facades_use_extracted_context_boundary(self) -> None:
        sentinel = {
            "runtime": {},
            "results_count": 0,
            "sources": [],
            "context_block": "SYNTHETIC_BOUNDARY",
        }
        with mock.patch.object(
            web_search.web_search_context,
            "build_search_context_material",
            return_value=sentinel,
        ):
            result = web_search._build_search_context_material(
                "SYNTHETIC_QUERY",
                [],
                now_iso="2026-08-16T12:00:00Z",
            )

        self.assertIs(result, sentinel)


if __name__ == "__main__":
    unittest.main()
