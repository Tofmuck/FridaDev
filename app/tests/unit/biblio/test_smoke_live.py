from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import chat_runtime
from biblio import observability
from biblio import passage_extractor as extractor
from biblio import prompt_lane
from biblio import smoke_live


RAW_PASSAGE = "RAW_SMOKE_PASSAGE_MUST_NOT_APPEAR_IN_RECORD"


class BiblioSmokeLiveTests(unittest.TestCase):
    def test_smoke_record_is_content_free_even_when_lane_contains_passage(self) -> None:
        records = smoke_live.run_smokes(
            cases=(smoke_live.BiblioSmokeCase("S1", "RAW USER QUERY MUST NOT APPEAR"),),
            turn_runner=_fake_turn_runner,
            raw_markers=(RAW_PASSAGE, "RAW USER QUERY MUST NOT APPEAR"),
        )

        self.assertEqual(len(records), 1)
        record = records[0]
        encoded = json.dumps(record, ensure_ascii=False, sort_keys=True)
        self.assertEqual(record["case_id"], "S1")
        self.assertEqual(record["status"], "extracted")
        self.assertEqual(record["query_kind"], "search_catalog")
        self.assertTrue(record["lane_injected"])
        self.assertEqual(record["passage_count"], 1)
        self.assertGreater(record["lane_chars"], 0)
        self.assertEqual(record["payload_objects_retained"], 0)
        self.assertFalse(record["raw_marker_leaks"])
        self.assertNotIn(RAW_PASSAGE, encoded)
        self.assertNotIn("RAW USER QUERY MUST NOT APPEAR", encoded)

    def test_default_case_ids_do_not_expose_queries(self) -> None:
        encoded = json.dumps(
            [{"case_id": case.case_id} for case in smoke_live.DEFAULT_SMOKE_CASES],
            ensure_ascii=False,
            sort_keys=True,
        )

        self.assertNotIn("Theetete", encoded)
        self.assertNotIn("maieutique", encoded)
        self.assertNotIn("Platon", encoded)


def _fake_turn_runner(data, *, user_msg, client_factory=None, config_module=None):
    passage = _passage(RAW_PASSAGE)
    lane = prompt_lane.build_biblio_prompt_lane([passage])
    payload = observability.build_biblio_event_payload(
        enabled=bool(data.get("biblio_enabled")),
        used=True,
        query_kind="search_catalog",
        passage_result=passage,
        prompt_lane=lane,
        status="extracted",
        reason_code="biblio_context_passage_extracted",
    )
    return chat_runtime.BiblioChatResult(
        enabled=True,
        used=True,
        reason_code="biblio_context_passage_extracted",
        query_kind="search_catalog",
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
