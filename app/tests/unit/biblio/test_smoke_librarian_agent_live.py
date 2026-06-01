from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import chat_runtime
from biblio import observability
from biblio import passage_extractor as extractor
from biblio import prompt_lane
from biblio import smoke_librarian_agent_live as smoke


RAW_PASSAGE = "RAW_AGENT_SMOKE_PASSAGE_MUST_NOT_APPEAR"
RAW_QUERY = "RAW AGENT SMOKE QUERY MUST NOT APPEAR"


class BiblioLibrarianAgentSmokeLiveTests(unittest.TestCase):
    def test_matrix_contains_required_product_families_without_raw_case_ids(self) -> None:
        messages = "\n".join(case.message for case in smoke.DEFAULT_SMOKE_CASES)
        encoded_public_matrix = json.dumps(
            [{"case_id": case.case_id, "case_kind": case.case_kind} for case in smoke.DEFAULT_SMOKE_CASES],
            ensure_ascii=False,
            sort_keys=True,
        )

        self.assertIn("Kant", messages)
        self.assertTrue("maïeutique" in messages or "maieutique" in messages)
        self.assertIn("Quels ouvrages", messages)
        self.assertNotIn("Kant", encoded_public_matrix)
        self.assertNotIn("Theetete", encoded_public_matrix)
        self.assertNotIn("maieutique", encoded_public_matrix)

    def test_smoke_record_is_content_free_even_when_lane_contains_passage(self) -> None:
        records = smoke.run_smokes(
            cases=(smoke.BiblioLibrarianProductSmokeCase("P01", "range_extract", RAW_QUERY),),
            turn_runner=_fake_turn_runner,
            raw_markers=(RAW_PASSAGE, RAW_QUERY),
        )

        self.assertEqual(len(records), 1)
        record = records[0]
        encoded = json.dumps(record, ensure_ascii=False, sort_keys=True)
        self.assertEqual(record["case_id"], "P01")
        self.assertEqual(record["status"], "extracted")
        self.assertEqual(record["query_kind"], "extract_range")
        self.assertTrue(record["lane_injected"])
        self.assertEqual(record["passage_count"], 1)
        self.assertEqual(record["payload_objects_retained"], 0)
        self.assertFalse(record["raw_marker_leaks"])
        self.assertEqual(record["product_expectation_status"], "met")
        self.assertNotIn(RAW_PASSAGE, encoded)
        self.assertNotIn(RAW_QUERY, encoded)

    def test_final_record_marker_leak_is_detected_without_emitting_unknown_field(self) -> None:
        record = smoke._finalize_record(
            {
                "case_id": "P01",
                "status": "extracted",
                "payload_objects_retained": 0,
                "product_expectation_status": "met",
                "debug_raw": RAW_PASSAGE,
            },
            raw_markers=(RAW_PASSAGE,),
            source_projection={},
        )
        encoded = json.dumps(record, ensure_ascii=False, sort_keys=True)

        self.assertTrue(record["raw_marker_leaks"])
        self.assertNotIn("debug_raw", record)
        self.assertNotIn(RAW_PASSAGE, encoded)

    def test_strict_exit_fails_on_leaks_payload_and_product_failure(self) -> None:
        safe = {
            "case_id": "P01",
            "raw_marker_leaks": False,
            "payload_objects_retained": 0,
            "forbidden_endpoint_used": False,
            "agent_used_for_response": False,
            "agent_product_response_changed": False,
            "agent_tool_execution_status": "not_executed",
            "agent_tool_call_event_count": 0,
            "product_expectation_status": "met",
        }
        raw_leak = {**safe, "raw_marker_leaks": True}
        retained_payload = {**safe, "payload_objects_retained": 1}
        product_failed = {**safe, "product_expectation_status": "failed"}

        self.assertEqual(smoke.smoke_exit_code([safe]), smoke.EXIT_OK)
        self.assertEqual(smoke.smoke_exit_code([raw_leak]), smoke.EXIT_VALIDATION_FAILURE)
        self.assertEqual(smoke.smoke_exit_code([retained_payload]), smoke.EXIT_VALIDATION_FAILURE)
        self.assertEqual(smoke.smoke_exit_code([product_failed]), smoke.EXIT_VALIDATION_FAILURE)
        self.assertEqual(
            smoke.smoke_exit_code([product_failed], product_strict=False),
            smoke.EXIT_OK,
        )

    def test_strict_exit_fails_on_agent_side_effects(self) -> None:
        base = {
            "case_id": "P01",
            "raw_marker_leaks": False,
            "payload_objects_retained": 0,
            "forbidden_endpoint_used": False,
            "agent_used_for_response": False,
            "agent_product_response_changed": False,
            "agent_tool_execution_status": "not_executed",
            "agent_tool_call_event_count": 0,
            "product_expectation_status": "met",
        }

        self.assertEqual(
            smoke.smoke_exit_code([{**base, "agent_used_for_response": True}]),
            smoke.EXIT_VALIDATION_FAILURE,
        )
        self.assertEqual(
            smoke.smoke_exit_code([{**base, "agent_product_response_changed": True}]),
            smoke.EXIT_VALIDATION_FAILURE,
        )
        self.assertEqual(
            smoke.smoke_exit_code([{**base, "agent_tool_call_event_count": 1}]),
            smoke.EXIT_VALIDATION_FAILURE,
        )
        self.assertEqual(
            smoke.smoke_exit_code([{**base, "agent_tool_execution_status": "executed"}]),
            smoke.EXIT_VALIDATION_FAILURE,
        )

    def test_main_is_strict_by_default_and_no_strict_is_explicit(self) -> None:
        records = [
            {
                "case_id": "P01",
                "raw_marker_leaks": True,
                "payload_objects_retained": 0,
                "product_expectation_status": "met",
            }
        ]

        with mock.patch("biblio.smoke_librarian_agent_live.run_smokes", return_value=records):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(smoke.main(["--jsonl"]), smoke.EXIT_VALIDATION_FAILURE)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(smoke.main(["--jsonl", "--no-strict"]), smoke.EXIT_OK)


def _fake_turn_runner(
    data,
    *,
    user_msg,
    conversation_id="",
    conversation_state=None,
    recent_dialogue=(),
    client_factory=None,
    config_module=None,
):
    passage = _passage(RAW_PASSAGE)
    lane = prompt_lane.build_biblio_prompt_lane([passage])
    payload = observability.build_biblio_event_payload(
        enabled=bool(data.get("biblio_enabled")),
        used=True,
        query_kind="extract_range",
        passage_result=passage,
        prompt_lane=lane,
        status="extracted",
        reason_code="biblio_context_passage_extracted",
    )
    return chat_runtime.BiblioChatResult(
        enabled=True,
        used=True,
        reason_code="biblio_context_passage_extracted",
        query_kind="extract_range",
        passage_result=passage,
        prompt_lane=lane,
        observability_payload=payload,
    )


def _passage(passage: str) -> extractor.BiblioPassageResult:
    return extractor.BiblioPassageResult(
        status=extractor.STATUS_EXTRACTED,
        reason_code=extractor.REASON_PASSAGE_EXTRACTED,
        passage=passage,
        doc_id_short="doc-1234",
        passage_chars=len(passage),
        passage_hash="",
        char_offset=0,
        window_chars=700,
        max_passage_chars=4_000,
        excerpt_start=0,
        excerpt_end=len(passage),
        text_length=len(passage),
        page_no=12,
        para_no=3,
        paragraph_id=99,
    )


if __name__ == "__main__":
    unittest.main()
