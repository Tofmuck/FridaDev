from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import chat_runtime
from biblio import catalogue_client as catalogue
from biblio import library_runtime
from biblio import passage_extractor as extractor
from biblio import prompt_lane
from biblio import query_planner


RAW_PASSAGE = "SYNTHETIC_BIBLIO_CHAT_PASSAGE_MUST_ONLY_APPEAR_IN_PROMPT"


class BiblioChatRuntimeTests(unittest.TestCase):
    def test_toggle_off_does_not_build_client_or_call_catalogue(self) -> None:
        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": False},
            user_msg="passage 126b dans Platon",
            client_factory=_raising_client_factory,
        )

        self.assertFalse(result.enabled)
        self.assertFalse(result.used)
        self.assertIsNone(result.prompt_message)
        self.assertEqual(result.observability_payload["enabled"], False)
        self.assertEqual(result.observability_payload["used"], False)
        self.assertEqual(result.observability_payload["status"], "not_applicable")
        self.assertIn(chat_runtime.REASON_TOGGLE_DISABLED, result.observability_payload["reason_code_counts"])

    def test_toggle_on_without_clear_bibliographic_signal_does_not_call_catalogue(self) -> None:
        for message in (
            "Explique simplement ce concept.",
            "Je cherche un livre sympa.",
            "Cherche dans mon livre.",
            "Comment faire dans Photoshop ?",
        ):
            with self.subTest(message=message):
                result = chat_runtime.run_biblio_chat_turn(
                    {"biblio_enabled": True},
                    user_msg=message,
                    client_factory=_raising_client_factory,
                )

                self.assertTrue(result.enabled)
                self.assertFalse(result.used)
                self.assertIsNone(result.prompt_message)
                self.assertEqual(result.observability_payload["status"], "not_used")
                self.assertEqual(result.observability_payload["client"]["event_count"], 0)

    def test_clear_document_locator_signal_extracts_and_builds_lane(self) -> None:
        observed: dict[str, object] = {}

        def client_factory(**kwargs):
            observed["client_config_module"] = kwargs.get("config_module")
            return _FakeClient()

        def extractor_factory(client):
            observed["extractor_client"] = client
            return _FakeExtractor(observed)

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Cherche le passage 126b dans Platon dans le catalogue.",
            config_module=_FakeConfig,
            client_factory=client_factory,
            extractor_factory=extractor_factory,
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "extract_passage")
        self.assertIsInstance(observed["extractor_client"], _FakeClient)
        self.assertIs(observed["client_config_module"], _FakeConfig)
        request = observed["request"]
        self.assertEqual(request.resolve_request.title, "Platon")
        self.assertEqual(request.resolve_request.locator, "126b")
        self.assertIsNotNone(result.prompt_message)
        self.assertIn(prompt_lane.LANE_HEADER, result.prompt_message["content"])
        self.assertIn(RAW_PASSAGE, result.prompt_message["content"])

        encoded_observability = json.dumps(result.observability_payload, ensure_ascii=False, sort_keys=True)
        self.assertNotIn(RAW_PASSAGE, encoded_observability)
        self.assertNotIn(prompt_lane.LANE_HEADER, encoded_observability)
        self.assertEqual(result.observability_payload["counts"]["passage_count"], 1)

    def test_catalogue_list_request_consults_catalogue_and_builds_consultation_lane(self) -> None:
        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Tu peux chercher et voir les premiers ouvrages ?",
            client_factory=lambda **_kwargs: _FakeClient(),
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "list_catalog")
        self.assertIsNotNone(result.prompt_message)
        self.assertIn("[CONSULTATION DE BIBLIOTHEQUE]", result.prompt_message["content"])
        self.assertEqual(result.observability_payload["status"], "listed")
        self.assertEqual(result.observability_payload["client"]["event_count"], 1)

    def test_library_runtime_list_catalog_retains_only_endpoint_observations(self) -> None:
        plan = query_planner.plan_biblio_query("Tu peux chercher et voir les premiers ouvrages ?")

        result = library_runtime.run_biblio_library_plan(_FakeClient(), plan)

        self.assertEqual(result.status, library_runtime.STATUS_LISTED)
        self.assertTrue(result.endpoint_observations)
        self.assertFalse(hasattr(result, "client_responses"))
        self.assertFalse(any(hasattr(item, "payload") for item in result.endpoint_observations))

    def test_unaccented_thematic_search_uses_accent_variant_without_extracting_yet(self) -> None:
        fake = _AccentSensitiveSearchClient()

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Cherche maieutique dans la bibliotheque",
            client_factory=lambda **_kwargs: fake,
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "search_catalog")
        self.assertEqual(result.observability_payload["status"], "searched")
        self.assertIsNotNone(result.prompt_message)
        self.assertIn("[CONSULTATION DE BIBLIOTHEQUE]", result.prompt_message["content"])
        self.assertIsNone(result.passage_result)
        self.assertNotIn(prompt_lane.LANE_HEADER, result.prompt_message["content"])
        self.assertIn(("search", "maïeutique"), fake.calls)
        self.assertNotIn(("context",), fake.calls)

    def test_library_runtime_search_catalog_retains_only_endpoint_observations(self) -> None:
        plan = query_planner.plan_biblio_query("Cherche maieutique dans la bibliotheque")
        fake = _AccentSensitiveSearchClient()

        result = library_runtime.run_biblio_library_plan(fake, plan)
        encoded = json.dumps(result.client_observability(), ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, library_runtime.STATUS_SEARCHED)
        self.assertTrue(result.endpoint_observations)
        self.assertFalse(hasattr(result, "client_responses"))
        self.assertFalse(any(hasattr(item, "payload") for item in result.endpoint_observations))
        self.assertNotIn("RAW TITLE MUST STAY INTERNAL", encoded)
        self.assertNotIn("RAW SEARCH TEXT MUST NOT BE OBSERVABLE", encoded)
        self.assertNotIn("payload", encoded)

    def test_thematic_search_repro_phrasings_do_not_fall_back_to_locator_required(self) -> None:
        messages = (
            "Peux-tu me trouver dans le Théétète le passage où Socrate parle de la maïeutique ?",
            "Peux-tu me trouver dans le Theetete le passage ou Socrate parle de la maieutique ?",
            "Tu peux me chercher dans le Théétète le passage où Socrate parle de la maïeutique ?",
            "Trouve le passage sur la maieutique dans le Theetete",
            "Cherche le passage sur la maïeutique dans le Théétète",
        )

        for message in messages:
            with self.subTest(message=message):
                fake = _AccentSensitiveSearchClient()
                result = chat_runtime.run_biblio_chat_turn(
                    {"biblio_enabled": True},
                    user_msg=message,
                    client_factory=lambda **_kwargs: fake,
                )

                self.assertTrue(result.used)
                self.assertEqual(result.query_kind, "search_catalog")
                self.assertEqual(result.observability_payload["status"], "searched")
                self.assertNotEqual(result.reason_code, "locator_required_for_passage")
                self.assertIsNone(result.passage_result)
                self.assertIsNotNone(result.prompt_message)
                self.assertIn("[CONSULTATION DE BIBLIOTHEQUE]", result.prompt_message["content"])
                self.assertNotIn(prompt_lane.LANE_HEADER, result.prompt_message["content"])
                self.assertIn(("search", "maïeutique"), fake.calls)
                self.assertNotIn(("context",), fake.calls)

    def test_theetete_range_request_reaches_extractor_with_work_anchor(self) -> None:
        observed: dict[str, object] = {}

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Bon, vas-y, tu me balances ici un extrait du Théétète de Platon. On va dire 126b à 128a.",
            client_factory=lambda **_kwargs: _FakeClient(),
            extractor_factory=lambda client: _FakeExtractor(observed),
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "extract_range")
        request = observed["request"]
        self.assertEqual(request.resolve_request.title, "Platon")
        self.assertEqual(request.resolve_request.locator, "126b")
        self.assertEqual(request.resolve_request.locator_end, "128a")
        self.assertEqual(request.resolve_request.locator_anchor_page, 131)
        self.assertNotEqual(result.reason_code, chat_runtime.REASON_NO_BIBLIOGRAPHIC_SIGNAL)

    def test_library_runtime_extract_range_retains_no_payloads_in_runtime_or_work_resolution(self) -> None:
        plan = query_planner.plan_biblio_query(
            "Bon, vas-y, tu me balances ici un extrait du Théétète de Platon. On va dire 126b à 128a."
        )
        observed: dict[str, object] = {}

        result = library_runtime.run_biblio_library_plan(
            _FakeClient(),
            plan,
            extractor_factory=lambda client: _FakeExtractor(observed),
        )

        self.assertEqual(result.status, library_runtime.STATUS_EXTRACTED_OR_LANE)
        self.assertIsNotNone(result.work_resolution)
        self.assertTrue(result.endpoint_observations)
        self.assertTrue(result.work_resolution.endpoint_observations)
        self.assertFalse(hasattr(result, "client_responses"))
        self.assertFalse(hasattr(result.work_resolution, "client_responses"))
        self.assertFalse(any(hasattr(item, "payload") for item in result.endpoint_observations))
        self.assertFalse(any(hasattr(item, "payload") for item in result.work_resolution.endpoint_observations))

    def test_common_french_locator_phrasings_resolve_title(self) -> None:
        cases = (
            "Cherche le passage 126b dans Platon dans le catalogue.",
            "Peux-tu me sortir le passage 126b de Platon ?",
            "Peux-tu me sortir le passage 126b de Platon dans la bibliotheque ?",
            "Dans la biblio, trouve 126b chez Platon.",
        )

        for message in cases:
            with self.subTest(message=message):
                decision = chat_runtime.resolve_biblio_chat_decision(
                    {"biblio_enabled": True},
                    message,
                )

                self.assertTrue(decision.should_attempt)
                self.assertEqual(decision.reason_code, "biblio_passage_requested")
                self.assertIsNotNone(decision.resolve_request)
                self.assertEqual(decision.resolve_request.title, "Platon")
                self.assertEqual(decision.resolve_request.locator, "126b")

    def test_oral_apostrophe_title_cleanup_preserves_de_la_title(self) -> None:
        cases = (
            ("Peux-tu me sortir le passage 126b de l Apologie ?", "Apologie"),
            ("Peux-tu me sortir le passage 126b de l'Apologie ?", "Apologie"),
            ("Peux-tu me sortir le passage 126b de la République ?", "République"),
        )

        for message, expected_title in cases:
            with self.subTest(message=message):
                decision = chat_runtime.resolve_biblio_chat_decision(
                    {"biblio_enabled": True},
                    message,
                )

                self.assertTrue(decision.should_attempt)
                self.assertIsNotNone(decision.resolve_request)
                self.assertEqual(decision.resolve_request.title, expected_title)
                self.assertEqual(decision.resolve_request.locator, "126b")

    def test_locator_range_arrow_does_not_remain_in_title(self) -> None:
        decision = chat_runtime.resolve_biblio_chat_decision(
            {"biblio_enabled": True},
            "Cherche dans Platon 126b -> 126e dans le catalogue.",
        )

        self.assertTrue(decision.should_attempt)
        self.assertIsNotNone(decision.resolve_request)
        self.assertEqual(decision.resolve_request.title, "Platon")
        self.assertEqual(decision.resolve_request.locator, "126b")
        self.assertEqual(decision.resolve_request.locator_end, "126e")

    def test_function_words_and_biblio_surface_words_are_never_titles(self) -> None:
        fragments = ("le", "la", "l", "bibliotheque", "catalogue", "biblio", "ouvrage", "livre")

        for fragment in fragments:
            with self.subTest(fragment=fragment):
                decision = chat_runtime.resolve_biblio_chat_decision(
                    {"biblio_enabled": True},
                    f"Trouve 126b chez {fragment}.",
                )

                self.assertFalse(decision.should_attempt)
                self.assertIsNone(decision.resolve_request)

    def test_toggle_off_still_blocks_natural_biblio_request_before_client_construction(self) -> None:
        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": False},
            user_msg="Peux-tu me sortir le passage 126b de Platon ?",
            client_factory=_raising_client_factory,
        )

        self.assertFalse(result.enabled)
        self.assertFalse(result.used)
        self.assertIsNone(result.prompt_message)

    def test_inject_prompt_lane_inserts_before_last_user_message(self) -> None:
        passage = _passage(RAW_PASSAGE)
        result = chat_runtime.BiblioChatResult(
            enabled=True,
            used=True,
            reason_code=chat_runtime.REASON_DOCUMENT_LOCATOR_SIGNAL_DETECTED,
            query_kind=chat_runtime.QUERY_KIND_DOCUMENT_LOCATOR,
            passage_result=passage,
            prompt_lane=prompt_lane.build_biblio_prompt_lane([passage]),
            observability_payload={},
        )
        messages = [
            {"role": "system", "content": "system"},
            {"role": "assistant", "content": "older"},
            {"role": "user", "content": "question"},
        ]

        injected = chat_runtime.inject_biblio_prompt_lane(messages, result)

        self.assertTrue(injected)
        self.assertEqual(messages[-1]["role"], "user")
        self.assertEqual(messages[-2]["role"], "system")
        self.assertIn(prompt_lane.LANE_HEADER, messages[-2]["content"])


class _FakeConfig:
    pass


class _FakeClient:
    def catalog(self, *, q: str | None = None, limit: int = 100, offset: int = 0) -> catalogue.CatalogueResponse:
        items = [
            {
                "id": "doc-1234",
                "title": q or "Catalogue item",
                "human_canonical_title": q or "Catalogue item",
                "human_authors": "Platon" if q == "Platon" else "",
            }
        ]
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CATALOG,
            status_code=200,
            payload={"total": len(items), "items": items},
            duration_ms=1,
            result_count=len(items),
        )

    def search(self, q: str, *, limit: int = 20) -> catalogue.CatalogueResponse:
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            status_code=200,
            payload={
                "count": 1,
                "results": [
                    {
                        "document_id": "doc-1234",
                        "title": "Internal work carrier",
                        "page_no": 131,
                        "para_no": 230,
                        "text": "RAW SEARCH TEXT MUST NOT BE OBSERVABLE",
                    }
                ],
            },
            duration_ms=1,
            result_count=1,
        )


class _AccentSensitiveSearchClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def catalog(self, *, q: str | None = None, limit: int = 100, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("catalog", str(q or "")))
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CATALOG,
            status_code=200,
            payload={"total": 0, "items": []},
            duration_ms=1,
            result_count=0,
        )

    def search(self, q: str, *, limit: int = 20) -> catalogue.CatalogueResponse:
        self.calls.append(("search", str(q or "")))
        rows = []
        if q == "maïeutique":
            rows = [
                {
                    "document_id": "doc-1234",
                    "title": "RAW TITLE MUST STAY INTERNAL",
                    "page_no": 4,
                    "para_no": 26,
                    "text": "RAW SEARCH TEXT MUST NOT BE OBSERVABLE",
                }
            ]
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            status_code=200,
            payload={"count": len(rows), "results": rows},
            duration_ms=1,
            result_count=len(rows),
        )


class _FakeExtractor:
    def __init__(self, observed: dict[str, object]) -> None:
        self.observed = observed

    def extract(self, request):
        self.observed["request"] = request
        return _passage(RAW_PASSAGE)


def _raising_client_factory(**_kwargs):
    raise AssertionError("Catalogue client must not be built")


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
