from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import conversation_followup
from biblio import conversation_state
from biblio import document_resolver as resolver
from biblio import passage_candidate_search as candidate_search
from biblio import passage_context_search as context_search
from biblio import passage_extractor as extractor
from biblio import passage_selection


RAW_PASSAGE = "SYNTHETIC_BIBLIO_STATE_PASSAGE_MUST_NOT_PERSIST"
RAW_TITLE = "SYNTHETIC_BIBLIO_STATE_TITLE_MUST_NOT_PERSIST"
RAW_QUERY = "SYNTHETIC_BIBLIO_STATE_QUERY_MUST_NOT_PERSIST"


class BiblioConversationStateTests(unittest.TestCase):
    def test_empty_state_has_schema_and_is_content_free(self) -> None:
        state = conversation_state.BiblioConversationState.empty(conversation_id="conv-123")

        self.assertEqual(state.schema_version, conversation_state.SCHEMA_VERSION)
        self.assertFalse(state.present)
        self.assertEqual(state.to_dict()["conversation_id"], "conv-123")
        encoded = _json(state.to_dict())
        self.assertNotIn(RAW_PASSAGE, encoded)
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn("payload", encoded.lower())

    def test_update_after_extraction_persists_only_anchors_and_hashes(self) -> None:
        previous = conversation_state.BiblioConversationState.empty(conversation_id="conv-123")
        runtime = _RuntimeResult(passage_result=_passage(RAW_PASSAGE), status="extracted")

        state, transition = conversation_state.update_state_from_runtime(
            previous,
            query_plan=_Plan(intent="extract_passage", work_title=RAW_QUERY),
            library_result=runtime,
            conversation_id="conv-123",
            now_iso="2026-05-31T12:00:00Z",
        )

        self.assertTrue(state.present)
        self.assertTrue(transition.changed)
        self.assertEqual(state.last_intent, "extract_passage")
        self.assertEqual(state.page_no, 12)
        self.assertEqual(state.para_no, 3)
        self.assertEqual(state.paragraph_id, 99)
        self.assertEqual(len(state.last_passage_hash), 12)
        self.assertEqual(state.current_document["document_id"], "doc-123456")
        encoded = _json(state.to_dict())
        self.assertNotIn(RAW_PASSAGE, encoded)
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_QUERY, encoded)
        self.assertNotIn("payload", encoded.lower())

    def test_state_round_trips_through_latest_user_message_meta(self) -> None:
        state, _transition = conversation_state.update_state_from_runtime(
            conversation_state.BiblioConversationState.empty(conversation_id="conv-123"),
            query_plan=_Plan(intent="search_catalog"),
            library_result=_RuntimeResult(context_result=_ambiguous_context_result(), status="ambiguous"),
            conversation_id="conv-123",
            now_iso="2026-05-31T12:00:00Z",
        )
        conversation = {
            "id": "conv-123",
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": RAW_QUERY},
            ],
        }

        attached = conversation_state.attach_state_to_latest_user_message(conversation, state)
        loaded = conversation_state.read_state_from_conversation(conversation)

        self.assertTrue(attached)
        self.assertTrue(loaded.present)
        self.assertEqual(loaded.last_ambiguity["candidate_count"], 2)
        encoded = _json(conversation)
        self.assertNotIn(RAW_PASSAGE, encoded)
        self.assertNotIn(RAW_TITLE, encoded)

    def test_clear_state_returns_empty_state(self) -> None:
        state = conversation_state.clear_state(conversation_id="conv-123")

        self.assertFalse(state.present)
        self.assertEqual(state.schema_version, conversation_state.SCHEMA_VERSION)

    def test_followup_without_state_requires_clarification(self) -> None:
        followup = conversation_followup.detect_followup_request("continue")
        clarification = conversation_followup.clarification_for_followup(
            conversation_state.BiblioConversationState.empty(conversation_id="conv-123"),
            followup,
        )

        self.assertTrue(followup.present)
        self.assertIsNotNone(clarification)
        self.assertEqual(clarification.reason_code, conversation_followup.REASON_STATE_MISSING)
        self.assertIn("clarifier", clarification.message["content"])

    def test_previous_page_with_anchor_still_clarifies_without_page_tool(self) -> None:
        state, _transition = conversation_state.update_state_from_runtime(
            conversation_state.BiblioConversationState.empty(conversation_id="conv-123"),
            query_plan=_Plan(intent="search_catalog"),
            library_result=_RuntimeResult(passage_result=_passage(RAW_PASSAGE), status="extracted"),
            conversation_id="conv-123",
            now_iso="2026-05-31T12:00:00Z",
        )
        followup = conversation_followup.detect_followup_request("montre-moi la page precedente")
        clarification = conversation_followup.clarification_for_followup(state, followup)

        self.assertIsNotNone(clarification)
        self.assertTrue(clarification.state_present)
        self.assertTrue(clarification.anchor_present)
        self.assertEqual(clarification.reason_code, conversation_followup.REASON_PAGE_TOOL_UNAVAILABLE)
        self.assertIn("latest/page", clarification.message["content"])


class _Plan:
    def __init__(
        self,
        *,
        intent: str,
        work_title: str = "",
        document_title: str = "",
        catalogue_query: str = "",
        author: str = "",
    ) -> None:
        self.intent = intent
        self.work_title = work_title
        self.document_title = document_title
        self.catalogue_query = catalogue_query
        self.author = author


class _RuntimeResult:
    def __init__(
        self,
        *,
        passage_result=None,
        context_result=None,
        status: str,
    ) -> None:
        self.status = status
        self.reason_code = f"biblio_{status}"
        self.passage_result = passage_result
        self.context_result = context_result
        self.passage_results = (passage_result,) if passage_result is not None else ()
        self.consultation_message = None


def _passage(passage: str) -> extractor.BiblioPassageResult:
    document = resolver.DocumentCandidate(
        document_id="doc-123456",
        doc_id_short="doc-1234",
        title=RAW_TITLE,
        canonical_title=RAW_TITLE,
        authors=RAW_TITLE,
        metadata_status="validated",
    )
    locator = resolver.LocatorCandidate(
        document_id="doc-123456",
        doc_id_short="doc-1234",
        kind="stephanus",
        label=RAW_TITLE,
        page_no=12,
        para_no=3,
        paragraph_id=99,
    )
    resolution = resolver.BiblioResolutionResult(
        status=resolver.STATUS_RESOLVED,
        reason_code=resolver.REASON_DOCUMENT_AND_LOCATOR_RESOLVED,
        document=document,
        document_candidates=(document,),
        locator=locator,
        locator_candidates=(locator,),
    )
    return extractor.BiblioPassageResult(
        status=extractor.STATUS_EXTRACTED,
        reason_code=extractor.REASON_PASSAGE_EXTRACTED,
        resolution=resolution,
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


def _ambiguous_context_result() -> context_search.BiblioPassageContextSearchResult:
    first = candidate_search.BiblioPassageCandidate(
        document_id="doc-123456",
        doc_id_short="doc-1234",
        page_no=12,
        para_no=3,
        paragraph_id=99,
        score=42.0,
    )
    second = candidate_search.BiblioPassageCandidate(
        document_id="doc-567890",
        doc_id_short="doc-5678",
        page_no=13,
        para_no=4,
        paragraph_id=100,
        score=41.0,
    )
    candidate_result = candidate_search.BiblioPassageCandidateSearchResult(
        status=candidate_search.STATUS_CANDIDATES_FOUND,
        reason_code=candidate_search.REASON_CANDIDATES_FOUND,
        candidates=(first, second),
        total_candidate_count=2,
    )
    selection = passage_selection.BiblioPassageSelectionDecision(
        status=passage_selection.STATUS_AMBIGUOUS,
        reason_code=passage_selection.REASON_SELECTION_GAP_TOO_SMALL,
        scores=(),
        top_score=42.0,
        runner_up_score=41.0,
        score_gap=1.0,
        ambiguous=True,
    )
    return context_search.BiblioPassageContextSearchResult(
        status=context_search.STATUS_AMBIGUOUS,
        reason_code=context_search.REASON_CONTEXT_AMBIGUOUS,
        candidate_result=candidate_result,
        passage_results=(_passage(RAW_PASSAGE),),
        selection=selection,
    )


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
