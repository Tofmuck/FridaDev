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
from biblio import passage_extractor as extractor
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
        self.assertFalse(payload["module_state"]["chat_wired"])
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


class _FakeConfig:
    BIBLIO_CATALOGUE_BASE_URL = "https://human-user:human-secret@catalogue.example.test:9443/doc-api?token=hidden#frag"
    BIBLIO_CATALOGUE_TIMEOUT_S = 12


class _FakeTurnLogger:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def emit(self, stage: str, *, status: str, payload: dict[str, object]) -> bool:
        self.events.append({"stage": stage, "status": status, "payload": payload})
        return True


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


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
