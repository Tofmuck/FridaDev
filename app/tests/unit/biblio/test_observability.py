from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import catalogue_client as catalogue
from biblio import document_resolver as resolver
from biblio import observability
from biblio import passage_candidate_search as candidate_search
from biblio import passage_context_search as context_search
from biblio import passage_extractor as extractor
from biblio import passage_selection
from biblio import prompt_lane


RAW_SECRET = "SYNTHETIC_BIBLIO_RAW_CONTENT_MUST_NOT_LEAK"
RAW_HASH = "SYNTHETIC_BIBLIO_HASH_MUST_NOT_LEAK"


class BiblioObservabilityTests(unittest.TestCase):
    def test_admin_status_exposes_only_non_secret_config_and_boundaries(self) -> None:
        payload = observability.build_admin_observability(config_module=_FakeConfig)
        encoded = _json(payload)

        self.assertEqual(payload["kind"], "biblio_admin_observability")
        self.assertEqual(payload["admin_route"], "/api/admin/biblio/observability")
        self.assertEqual(payload["config"]["catalogue_base_url"], "https://catalogue.example.test:9443/doc-api")
        self.assertEqual(payload["config"]["timeout_s"], 12)
        self.assertTrue(payload["config"]["get_only"])
        self.assertEqual(payload["config"]["allowed_methods"], ["GET"])
        self.assertTrue(payload["module_state"]["chat_wired"])
        self.assertTrue(payload["module_state"]["frontend_wired"])
        self.assertTrue(payload["module_state"]["toggle_wired"])
        self.assertFalse(payload["module_state"]["db_write"])
        self.assertFalse(payload["boundaries"]["active_document"])
        self.assertFalse(payload["redaction"]["raw_content_included"])
        self.assertNotIn("human-user", encoded)
        self.assertNotIn("human-secret", encoded)
        self.assertNotIn("token=", encoded)
        self.assertNotIn("cookie", encoded.lower())

    def test_event_payload_uses_only_content_free_projections(self) -> None:
        resolution = _resolution_with_raw_internal_fields()
        passage = _passage(RAW_SECRET, resolution=resolution, passage_hash=RAW_HASH)
        lane = prompt_lane.build_biblio_prompt_lane([passage])
        response = catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CONTEXT,
            status_code=200,
            payload={"text": RAW_SECRET, "payload": RAW_SECRET},
            duration_ms=7,
            result_count=1,
            doc_id_short="doc-1234",
            content_chars=len(RAW_SECRET),
        )
        error = catalogue.CatalogueTimeout(
            endpoint_kind=catalogue.ENDPOINT_CONTEXT,
            duration_ms=8,
            doc_id="doc-123456",
            error_class="Timeout",
            detail=RAW_SECRET,
        )

        payload = observability.build_biblio_event_payload(
            enabled=True,
            used=True,
            query_kind="document_locator",
            client_response=response,
            client_error=error,
            resolution=resolution,
            passage_result=passage,
            prompt_lane=lane,
        )
        encoded = _json(payload)

        self.assertEqual(payload["kind"], "biblio_observability_event")
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["client"]["event_count"], 2)
        self.assertEqual(payload["resolver"]["status"], resolver.STATUS_RESOLVED)
        self.assertEqual(payload["extractor"]["status"], extractor.STATUS_EXTRACTED)
        self.assertEqual(payload["lane"]["passage_count"], 1)
        self.assertEqual(payload["counts"]["passage_count"], 1)
        self.assertFalse(payload["redaction"]["raw_passage_included"])
        self.assertNotIn(RAW_SECRET, encoded)
        self.assertNotIn(RAW_HASH, encoded)
        self.assertNotIn(prompt_lane.LANE_HEADER, encoded)
        self.assertNotIn(prompt_lane.LANE_FOOTER, encoded)

    def test_event_payload_accepts_endpoint_observations_without_payload(self) -> None:
        observation = catalogue.CatalogueEndpointObservation(
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            status_code=200,
            duration_ms=7,
            result_count=8,
            doc_id_short="doc-1234",
            content_chars=128,
        )

        payload = observability.build_biblio_event_payload(
            enabled=True,
            used=True,
            query_kind="search_catalog",
            client_response=[observation],
            status="searched",
            reason_code="biblio_catalog_searched",
        )
        encoded = _json(payload)

        self.assertEqual(payload["client"]["event_count"], 1)
        self.assertEqual(payload["client"]["items"][0]["endpoint_kind"], catalogue.ENDPOINT_SEARCH)
        self.assertNotIn("payload", payload["client"]["items"][0])
        self.assertNotIn(RAW_SECRET, encoded)

    def test_event_payload_exposes_librarian_agent_observation_without_raw_content(self) -> None:
        payload = observability.build_biblio_event_payload(
            enabled=True,
            used=False,
            query_kind="no_signal",
            librarian_agent=_FakeLibrarianAgentObservation(),
            status="not_selected",
            reason_code="biblio_no_bibliographic_signal",
        )
        agent = payload["librarian_agent"]
        encoded = _json(payload)

        self.assertEqual(agent["mode"], "shadow")
        self.assertEqual(agent["comparison_kind"], "deterministic_comparison")
        self.assertTrue(agent["request_observation"]["user_message_present"])
        self.assertEqual(agent["request_observation"]["user_message_hash"], "abcdef123456")
        self.assertEqual(agent["request_observation"]["recent_dialogue_hashes"], ["123456abcdef"])
        self.assertEqual(agent["request_observation"]["settings"]["primary_model"], "model/x")
        self.assertEqual(agent["agent"]["validation"]["tool_names"], ["catalog_search"])
        self.assertEqual(agent["agent"]["validation"]["json_hash"], "fedcba654321")
        self.assertEqual(agent["tool_execution_status"], "not_executed")
        self.assertFalse(agent["used_for_response"])
        self.assertFalse(agent["product_response_changed"])

        self.assertNotIn("request", agent)
        self.assertNotIn(RAW_SECRET, encoded)
        self.assertNotIn("RAW JSON MODEL MUST NOT LEAK", encoded)
        self.assertNotIn("RAW TOOL PARAMS MUST NOT LEAK", encoded)
        keys = _collect_keys(payload)
        self.assertNotIn("message", keys)
        self.assertNotIn("prompt", keys)
        self.assertNotIn("payload", keys)
        self.assertNotIn("params", keys)

    def test_event_payload_exposes_lot7_passage_search_projection_content_free(self) -> None:
        context_result = _ambiguous_context_search_result()
        lane = prompt_lane.build_biblio_prompt_lane(context_result.passage_results)

        payload = observability.build_biblio_event_payload(
            enabled=True,
            used=True,
            query_kind="search_catalog",
            passage_result=context_result,
            prompt_lane=lane,
        )
        encoded = _json(payload)
        passage_search = payload["passage_search"]

        self.assertEqual(payload["status"], "ambiguous")
        self.assertEqual(passage_search["candidate_count"], 2)
        self.assertEqual(passage_search["context_call_count"], 1)
        self.assertEqual(passage_search["selected_count"], 0)
        self.assertEqual(passage_search["passage_result_count"], 1)
        self.assertEqual(passage_search["passage_count"], 1)
        self.assertTrue(passage_search["ambiguous"])
        self.assertTrue(passage_search["lane_injected"])
        self.assertCountEqual(passage_search["endpoint_kinds"], [catalogue.ENDPOINT_SEARCH, catalogue.ENDPOINT_CONTEXT])
        self.assertEqual(passage_search["selection_reason_codes"], ["selection_gap_too_small"])
        self.assertEqual(payload["counts"]["candidate_count"], 2)
        self.assertEqual(payload["counts"]["context_call_count"], 1)
        self.assertEqual(payload["counts"]["ambiguous_count"], 1)
        self.assertFalse(passage_search["theme_query_signal"]["available"])
        self.assertFalse(passage_search["work_query_signal"]["available"])

        self.assertNotIn(RAW_SECRET, encoded)
        self.assertNotIn("RAW TITLE MUST NOT LEAK", encoded)
        self.assertNotIn("RAW QUERY MUST NOT LEAK", encoded)
        self.assertNotIn(prompt_lane.LANE_HEADER, encoded)
        self.assertNotIn("message", encoded)

    def test_malformed_passage_hash_without_text_is_never_observable(self) -> None:
        passage = _passage(
            "",
            status=extractor.STATUS_TOO_LONG,
            reason_code=extractor.REASON_PASSAGE_TOO_LONG,
            passage_hash=RAW_HASH,
        )

        payload = observability.build_biblio_event_payload(
            enabled=True,
            used=True,
            passage_result=passage,
        )

        self.assertEqual(payload["extractor"]["passage_hash"], "")
        self.assertNotIn(RAW_HASH, _json(payload))

    def test_emit_biblio_event_uses_biblio_stage_without_raw_content(self) -> None:
        passage = _passage(RAW_SECRET)
        lane = prompt_lane.build_biblio_prompt_lane([passage])
        payload = observability.build_biblio_event_payload(
            enabled=True,
            used=True,
            passage_result=passage,
            prompt_lane=lane,
        )
        fake_logger = _FakeTurnLogger()

        emitted = observability.emit_biblio_event(payload, chat_turn_logger_module=fake_logger)

        self.assertTrue(emitted)
        self.assertEqual(fake_logger.events[0]["stage"], "biblio")
        self.assertEqual(fake_logger.events[0]["status"], "ok")
        self.assertNotIn(RAW_SECRET, _json(fake_logger.events[0]))

    def test_emit_biblio_event_preserves_agentic_noop_and_failure_statuses(self) -> None:
        fake_logger = _FakeTurnLogger()
        disabled = observability.build_biblio_event_payload(
            enabled=False,
            used=False,
            query_kind="not_requested",
            status="disabled",
            reason_code="biblio_toggle_disabled",
        )
        no_signal = observability.build_biblio_event_payload(
            enabled=True,
            used=False,
            query_kind="no_signal",
            status="not_selected",
            reason_code="biblio_no_bibliographic_signal",
        )
        failure = observability.build_biblio_event_payload(
            enabled=True,
            used=True,
            query_kind="search_catalog",
            client_error={"status": "error", "reason_code": "biblio_runtime_error"},
            status="error",
            reason_code="biblio_runtime_error",
        )

        self.assertTrue(observability.emit_biblio_event(disabled, chat_turn_logger_module=fake_logger))
        self.assertTrue(observability.emit_biblio_event(no_signal, chat_turn_logger_module=fake_logger))
        self.assertTrue(observability.emit_biblio_event(failure, chat_turn_logger_module=fake_logger))

        self.assertEqual(
            [event["status"] for event in fake_logger.events],
            ["disabled", "not_selected", "error"],
        )
        encoded = _json(fake_logger.events)
        self.assertNotIn(RAW_SECRET, encoded)


class _FakeConfig:
    BIBLIO_CATALOGUE_BASE_URL = "https://human-user:human-secret@catalogue.example.test:9443/doc-api?token=hidden#frag"
    BIBLIO_CATALOGUE_TIMEOUT_S = 12


class _FakeTurnLogger:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def emit(self, stage: str, *, status: str, payload: dict[str, object]) -> bool:
        self.events.append({"stage": stage, "status": status, "payload": payload})
        return True


class _FakeLibrarianAgentObservation:
    def to_observability(self) -> dict[str, object]:
        return {
            "present": True,
            "comparison_kind": "deterministic_comparison",
            "status": "evaluated",
            "reason_code": "biblio_librarian_agent_compared",
            "mode": "shadow",
            "model_called": True,
            "candidate_plan_present": True,
            "used_for_response": False,
            "deterministic_controller": True,
            "product_response_changed": False,
            "fallback_deterministic": True,
            "tool_execution_status": "not_executed",
            "tool_call_event_count": 0,
            "selection_event_count": 0,
            "state_update_event_count": 0,
            "final_event_count": 0,
            "agent_loop_executed": False,
            "request_observation": {
                "user_message_present": True,
                "user_message_chars": 32,
                "user_message_hash": "abcdef123456",
                "recent_dialogue_count": 1,
                "bounded_recent_dialogue_count": 1,
                "recent_dialogue_hashes": ["123456abcdef"],
                "message": RAW_SECRET,
                "settings": {
                    "mode": "shadow",
                    "primary_model": "model/x",
                    "prompt": RAW_SECRET,
                },
            },
            "agent": {
                "validation": {
                    "status": "validated",
                    "reason_code": "biblio_librarian_agent_json_validated",
                    "tool_names": ["catalog_search"],
                    "json_hash": "fedcba654321",
                    "raw": "RAW JSON MODEL MUST NOT LEAK",
                    "plan": {
                        "intent": "list_catalog",
                        "tool_names": ["catalog_search"],
                        "params": "RAW TOOL PARAMS MUST NOT LEAK",
                    },
                },
                "model": {
                    "status": "ok",
                    "reason_code": "biblio_librarian_agent_model_ok",
                    "model_effective": "model/x",
                    "finish_reason": "stop",
                    "attempt_count": 1,
                    "duration_ms": 12,
                    "response_chars": 200,
                    "payload": RAW_SECRET,
                },
            },
        }


def _resolution_with_raw_internal_fields() -> resolver.BiblioResolutionResult:
    document = resolver.DocumentCandidate(
        document_id="doc-123456",
        doc_id_short="doc-1234",
        title=RAW_SECRET,
        canonical_title=RAW_SECRET,
        authors=RAW_SECRET,
        metadata_status="validated",
        match_reasons=("document_id",),
    )
    locator = resolver.LocatorCandidate(
        document_id="doc-123456",
        doc_id_short="doc-1234",
        kind="stephanus",
        label=RAW_SECRET,
        page_no=12,
        para_no=3,
        paragraph_id=99,
    )
    return resolver.BiblioResolutionResult(
        status=resolver.STATUS_RESOLVED,
        reason_code=resolver.REASON_DOCUMENT_AND_LOCATOR_RESOLVED,
        document=document,
        document_candidates=(document,),
        locator=locator,
        locator_candidates=(locator,),
        requested_locator_kind="stephanus",
        requested_locator=RAW_SECRET,
    )


def _passage(
    passage: str,
    *,
    status: str = extractor.STATUS_EXTRACTED,
    reason_code: str = extractor.REASON_PASSAGE_EXTRACTED,
    resolution: resolver.BiblioResolutionResult | None = None,
    passage_hash: str = "",
) -> extractor.BiblioPassageResult:
    return extractor.BiblioPassageResult(
        status=status,
        reason_code=reason_code,
        resolution=resolution,
        passage=passage,
        doc_id_short="doc-1234",
        passage_chars=len(passage),
        passage_hash=passage_hash,
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


def _ambiguous_context_search_result() -> context_search.BiblioPassageContextSearchResult:
    first = candidate_search.BiblioPassageCandidate(
        document_id="doc-123456",
        doc_id_short="doc-1234",
        page_no=12,
        para_no=3,
        paragraph_id=99,
        score=42.0,
        hit_count=2,
        query_variant_count=2,
        query_hashes=("a" * 12,),
        reason_codes=("theme_hit", "work_document_match"),
        catalogue_rank_score=0.3,
        first_result_index=1,
    )
    second = candidate_search.BiblioPassageCandidate(
        document_id="doc-567890",
        doc_id_short="doc-5678",
        page_no=13,
        para_no=4,
        paragraph_id=100,
        score=41.0,
        hit_count=1,
        query_variant_count=1,
        query_hashes=("b" * 12,),
        reason_codes=("theme_hit",),
        catalogue_rank_score=0.2,
        first_result_index=2,
    )
    candidate_result = candidate_search.BiblioPassageCandidateSearchResult(
        status=candidate_search.STATUS_CANDIDATES_FOUND,
        reason_code=candidate_search.REASON_CANDIDATES_FOUND,
        candidates=(first, second),
        query_hashes=("a" * 12, "b" * 12),
        endpoint_observations=(
            catalogue.CatalogueEndpointObservation(
                endpoint_kind=catalogue.ENDPOINT_SEARCH,
                status_code=200,
                duration_ms=8,
                result_count=2,
                doc_id_short="doc-1234",
                content_chars=128,
            ),
        ),
        total_candidate_count=2,
    )
    selection = passage_selection.BiblioPassageSelectionDecision(
        status=passage_selection.STATUS_AMBIGUOUS,
        reason_code=passage_selection.REASON_SELECTION_GAP_TOO_SMALL,
        scores=(
            passage_selection.BiblioPassageSelectionScore(
                index=0,
                doc_id_short="doc-1234",
                score=42.0,
                candidate_score=42.0,
                context_chars=len(RAW_SECRET),
                reason_codes=("selection_gap_too_small",),
            ),
            passage_selection.BiblioPassageSelectionScore(
                index=1,
                doc_id_short="doc-5678",
                score=41.0,
                candidate_score=41.0,
                context_chars=32,
                reason_codes=("selection_gap_too_small",),
            ),
        ),
        top_score=42.0,
        runner_up_score=41.0,
        score_gap=1.0,
        ambiguous=True,
    )
    passage = _passage(RAW_SECRET)
    return context_search.BiblioPassageContextSearchResult(
        status=context_search.STATUS_AMBIGUOUS,
        reason_code=context_search.REASON_CONTEXT_AMBIGUOUS,
        candidate_result=candidate_result,
        context_observations=(
            catalogue.CatalogueEndpointObservation(
                endpoint_kind=catalogue.ENDPOINT_CONTEXT,
                status_code=200,
                duration_ms=6,
                result_count=1,
                doc_id_short="doc-1234",
                content_chars=len(RAW_SECRET),
            ),
        ),
        decisions=(
            context_search.BiblioPassageContextDecision(
                status=context_search.STATUS_EXTRACTED,
                reason_code=context_search.REASON_CONTEXT_EXTRACTED,
                doc_id_short="doc-1234",
                page_no=12,
                para_no=3,
                paragraph_id=99,
                candidate_score=42.0,
                candidate_reason_codes=("theme_hit", "work_document_match"),
                context_chars=len(RAW_SECRET),
                context_hash="c" * 12,
                selected=False,
                selection_score=42.0,
                selection_reason_codes=("selection_gap_too_small",),
            ),
        ),
        passage_results=(passage,),
        selection=selection,
    )


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _collect_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = set(value.keys())
        for child in value.values():
            keys.update(_collect_keys(child))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for child in value:
            keys.update(_collect_keys(child))
        return keys
    return set()


if __name__ == "__main__":
    unittest.main()
