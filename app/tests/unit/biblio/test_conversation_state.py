from __future__ import annotations

import json
import sys
import types
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

try:
    from core import conversations_store
except ModuleNotFoundError as exc:
    if exc.name != "psycopg":
        raise
    psycopg_module = types.ModuleType("psycopg")
    psycopg_rows_module = types.ModuleType("psycopg.rows")
    psycopg_types_module = types.ModuleType("psycopg.types")
    psycopg_json_module = types.ModuleType("psycopg.types.json")
    psycopg_rows_module.dict_row = object()
    psycopg_json_module.Json = lambda value: value
    sys.modules.setdefault("psycopg", psycopg_module)
    sys.modules.setdefault("psycopg.rows", psycopg_rows_module)
    sys.modules.setdefault("psycopg.types", psycopg_types_module)
    sys.modules.setdefault("psycopg.types.json", psycopg_json_module)
    from core import conversations_store


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
        self.assertEqual(transition.to_observability()["persistence_status"], "pending_normal_conversation_save")
        self.assertEqual(transition.to_observability()["persistence_guarantee"], "after_normal_conversation_save")
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

    def test_update_after_range_extraction_persists_interval_hint_without_text(self) -> None:
        previous = conversation_state.BiblioConversationState.empty(conversation_id="conv-123")
        runtime = _RuntimeResult(passage_result=_range_passage(RAW_PASSAGE), status="extracted")

        state, _transition = conversation_state.update_state_from_runtime(
            previous,
            query_plan=_Plan(intent="extract_range", work_title=RAW_QUERY),
            library_result=runtime,
            conversation_id="conv-123",
            now_iso="2026-05-31T12:00:00Z",
        )
        observed = state.to_observability()

        self.assertEqual(state.last_intent, "extract_range")
        self.assertEqual(state.last_result["interval_hint"]["kind"], "range")
        self.assertEqual(state.last_result["interval_hint"]["mode"], "multi_page_range")
        self.assertEqual(state.last_result["interval_hint"]["end_page_no"], 14)
        self.assertEqual(state.last_result["interval_hint"]["end_para_no"], 2)
        self.assertEqual(observed["last_result_interval_kind"], "range")
        self.assertEqual(observed["last_result_interval_mode"], "multi_page_range")
        self.assertEqual(observed["last_result_interval_end_page_no"], 14)
        encoded = _json(state.to_dict())
        self.assertNotIn(RAW_PASSAGE, encoded)
        self.assertNotIn(RAW_QUERY, encoded)

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

    def test_next_page_with_anchor_has_distinct_followup_kind_without_page_tool(self) -> None:
        state, _transition = conversation_state.update_state_from_runtime(
            conversation_state.BiblioConversationState.empty(conversation_id="conv-123"),
            query_plan=_Plan(intent="search_catalog"),
            library_result=_RuntimeResult(passage_result=_passage(RAW_PASSAGE), status="extracted"),
            conversation_id="conv-123",
            now_iso="2026-05-31T12:00:00Z",
        )
        followup = conversation_followup.detect_followup_request("montre-moi la page suivante")
        clarification = conversation_followup.clarification_for_followup(state, followup)

        self.assertEqual(followup.kind, conversation_followup.FOLLOWUP_NEXT_PAGE)
        self.assertIsNotNone(clarification)
        self.assertEqual(clarification.followup_kind, conversation_followup.FOLLOWUP_NEXT_PAGE)
        self.assertEqual(clarification.reason_code, conversation_followup.REASON_PAGE_TOOL_UNAVAILABLE)
        self.assertIn("Outil requis indisponible", clarification.message["content"])

    def test_state_survives_normal_conversation_save_and_load_through_store_fakes(self) -> None:
        conversation_id = "11111111-1111-4111-8111-111111111111"
        state, _transition = conversation_state.update_state_from_runtime(
            conversation_state.BiblioConversationState.empty(conversation_id=conversation_id),
            query_plan=_Plan(intent="extract_passage", work_title=RAW_QUERY),
            library_result=_RuntimeResult(passage_result=_passage(RAW_PASSAGE), status="extracted"),
            conversation_id=conversation_id,
            now_iso="2026-05-31T12:00:00Z",
        )
        conversation = {
            "id": conversation_id,
            "created_at": "2026-05-31T12:00:00Z",
            "messages": [
                {"role": "system", "content": "system", "timestamp": "2026-05-31T12:00:00Z"},
                {"role": "user", "content": RAW_QUERY, "timestamp": "2026-05-31T12:00:01Z"},
            ],
        }
        self.assertTrue(conversation_state.attach_state_to_latest_user_message(conversation, state))

        stored_messages: list[dict[str, object]] = []
        logger = _Logger()
        result = conversations_store.save_conversation(
            conversation,
            updated_at="2026-05-31T12:00:02Z",
            preserve_deleted=False,
            now_iso_func=lambda: "2026-05-31T12:00:03Z",
            normalize_messages_for_storage_func=_normalize_messages_for_storage,
            logger=logger,
            admin_log_event_func=lambda *_args, **_kwargs: None,
            upsert_conversation_catalog_func=lambda *_args, **_kwargs: {"id": conversation_id},
            upsert_conversation_messages_func=lambda saved: _capture_messages(saved, stored_messages),
        )

        self.assertTrue(result.ok)
        self.assertTrue(stored_messages)
        loaded_messages = conversations_store.load_messages_from_db(
            conversation_id,
            normalize_conversation_id_func=lambda raw: str(raw) if raw else None,
            db_conn_func=lambda: _FakeMessagesConn(stored_messages),
            ts_to_iso_func=lambda raw: conversations_store.ts_to_iso(
                raw,
                now_iso_func=lambda: "2026-05-31T12:00:04Z",
            ),
            logger=logger,
        )
        loaded_state = conversation_state.read_state_from_conversation(
            {"id": conversation_id, "messages": loaded_messages}
        )

        self.assertTrue(loaded_state.present)
        self.assertEqual(loaded_state.current_document["document_id"], "doc-123456")
        self.assertEqual(loaded_state.page_no, 12)
        self.assertEqual(loaded_state.para_no, 3)
        self.assertEqual(loaded_state.paragraph_id, 99)
        encoded_loaded = _json(loaded_messages)
        self.assertNotIn(RAW_PASSAGE, encoded_loaded)
        self.assertNotIn(RAW_TITLE, encoded_loaded)
        self.assertNotIn(RAW_QUERY, _json(loaded_state.to_dict()))


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


def _range_passage(passage: str) -> extractor.BiblioPassageResult:
    result = _passage(passage)
    return extractor.BiblioPassageResult(
        status=result.status,
        reason_code=extractor.REASON_RANGE_EXTRACTED,
        resolution=result.resolution,
        passage=result.passage,
        doc_id_short=result.doc_id_short,
        passage_chars=result.passage_chars,
        passage_hash=result.passage_hash,
        char_offset=result.char_offset,
        window_chars=result.window_chars,
        max_passage_chars=result.max_passage_chars,
        excerpt_start=result.excerpt_start,
        excerpt_end=result.excerpt_end,
        text_length=result.text_length,
        page_no=12,
        para_no=3,
        paragraph_id=99,
        interval_hint=extractor.BiblioCanonicalIntervalHint(
            kind="range",
            mode="multi_page_range",
            start_page_no=12,
            start_para_no=3,
            start_paragraph_id=99,
            end_page_no=14,
            end_para_no=2,
            page_span=3,
            paragraph_span=5,
        ),
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


def _normalize_messages_for_storage(messages):
    return conversations_store.normalize_messages_for_storage(
        messages,
        ts_to_iso_func=lambda raw: conversations_store.ts_to_iso(
            raw,
            now_iso_func=lambda: "2026-05-31T12:00:05Z",
        ),
        coerce_bool_func=conversations_store.coerce_bool,
    )


def _capture_messages(saved: dict[str, object], out: list[dict[str, object]]) -> bool:
    out[:] = json.loads(json.dumps(saved.get("messages") or []))
    return True


class _Logger:
    def info(self, *_args, **_kwargs) -> None:
        return None

    def warning(self, *_args, **_kwargs) -> None:
        return None


class _FakeMessagesCursor:
    def __init__(self, messages: list[dict[str, object]]) -> None:
        self.messages = messages

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, *_args, **_kwargs) -> None:
        return None

    def fetchall(self) -> list[dict[str, object]]:
        return [
            {
                "role": item.get("role"),
                "content": item.get("content"),
                "timestamp": item.get("timestamp"),
                "summarized_by": item.get("summarized_by"),
                "embedded": item.get("embedded"),
                "meta": item.get("meta"),
            }
            for item in self.messages
        ]


class _FakeMessagesConn:
    def __init__(self, messages: list[dict[str, object]]) -> None:
        self.messages = messages

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def cursor(self, *_args, **_kwargs):
        return _FakeMessagesCursor(self.messages)


if __name__ == "__main__":
    unittest.main()
