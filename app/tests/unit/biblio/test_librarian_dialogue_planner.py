from __future__ import annotations

import inspect
import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio.conversation_state import BiblioConversationState
from biblio import librarian_dialogue_planner as dialogue
from biblio import librarian_tools as tools


RAW_USER = "RAW USER MESSAGE MUST NOT LEAK FROM DIALOGUE PLANNER"
RAW_TITLE = "RAW TITLE MUST NOT LEAK FROM DIALOGUE PLANNER"
RAW_PASSAGE = "RAW PASSAGE MUST NOT LEAK FROM DIALOGUE PLANNER"


class BiblioLibrarianDialoguePlannerTests(unittest.TestCase):
    def test_catalogue_request_plans_catalog_list(self) -> None:
        result = dialogue.plan_biblio_dialogue("Tu peux me dire quels ouvrages tu as dans la bibliotheque ?")

        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_CATALOG_LIST)
        self.assertEqual(result.intent.intent, dialogue.INTENT_LIST_CATALOG)
        self.assertEqual(_tool_names(result), [tools.TOOL_CATALOG_LIST])
        self.assertEqual(result.plan.tool_calls[0].params["limit"], 100)

    def test_thematic_work_request_plans_search_without_inventing_context(self) -> None:
        result = dialogue.plan_biblio_dialogue(
            "Trouve dans le Theetete le passage ou Socrate parle de la maieutique"
        )

        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_THEME_SEARCH)
        self.assertEqual(result.intent.intent, dialogue.INTENT_SEARCH_PASSAGE)
        self.assertEqual(_tool_names(result), [tools.TOOL_CATALOG_SEARCH])
        self.assertNotIn(tools.TOOL_PASSAGE_CONTEXT, _tool_names(result))

    def test_current_document_search_uses_current_document_anchor(self) -> None:
        state = _state_with_document()

        result = dialogue.plan_biblio_dialogue("Dans ce livre, cherche la maieutique", state=state)

        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_CURRENT_DOCUMENT_ANCHOR_GLOBAL_SEARCH)
        self.assertTrue(result.current_document_used)
        self.assertEqual(result.intent.scope_mode, "current_document_anchor_global_search")
        self.assertNotEqual(result.intent.scope_mode, "current_document_strict")
        self.assertEqual(_tool_names(result), [tools.TOOL_DOCUMENT_OPEN_SUMMARY, tools.TOOL_CATALOG_SEARCH])
        self.assertEqual(result.plan.tool_calls[0].params["document_id"], "doc-1")
        self.assertEqual(result.to_observability()["intent"]["scope_mode"], "current_document_anchor_global_search")

    def test_current_document_search_without_state_clarifies(self) -> None:
        result = dialogue.plan_biblio_dialogue("Dans ce livre, cherche la maieutique")

        self.assertEqual(result.status, dialogue.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(result.reason_code, dialogue.REASON_CURRENT_DOCUMENT_MISSING)
        self.assertEqual(result.plan.intent, "clarify")
        self.assertEqual(result.plan.answer_mode, "clarify")
        self.assertEqual(_tool_names(result), [])

    def test_explain_this_passage_with_last_result_plans_bounded_context(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "page_no": 12, "para_no": 3})

        result = dialogue.plan_biblio_dialogue("Explique ce passage", state=state)

        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_LAST_PASSAGE_CONTEXT)
        self.assertEqual(result.intent.intent, dialogue.INTENT_EXPLAIN_PASSAGE)
        self.assertEqual(_tool_names(result), [tools.TOOL_PASSAGE_CONTEXT])
        self.assertEqual(result.plan.tool_calls[0].params["page_no"], 12)
        self.assertEqual(result.plan.tool_calls[0].params["para_no"], 3)

    def test_resume_this_passage_with_last_result_plans_bounded_context(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "paragraph_id": 101})

        result = dialogue.plan_biblio_dialogue("reprends ce passage", state=state)

        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_LAST_PASSAGE_CONTEXT)
        self.assertEqual(_tool_names(result), [tools.TOOL_PASSAGE_CONTEXT])
        self.assertEqual(result.plan.tool_calls[0].params["paragraph_id"], 101)

    def test_this_passage_without_state_clarifies(self) -> None:
        result = dialogue.plan_biblio_dialogue("Explique ce passage")

        self.assertEqual(result.status, dialogue.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(result.reason_code, dialogue.REASON_LAST_PASSAGE_MISSING)
        self.assertEqual(_tool_names(result), [])

    def test_navigation_request_missing_tool_does_not_plan_forbidden_tool(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "page_no": 12, "para_no": 3})

        result = dialogue.plan_biblio_dialogue("Et le passage suivant ?", state=state)

        self.assertEqual(result.status, dialogue.STATUS_UNSUPPORTED_MISSING_TOOL)
        self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_TOOL_MISSING)
        self.assertEqual(result.tool_required, "navigation")
        self.assertEqual(_tool_names(result), [])

    def test_plus_haut_with_state_reports_missing_navigation_tool(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "page_no": 12, "para_no": 3})

        result = dialogue.plan_biblio_dialogue("plus haut", state=state)

        self.assertEqual(result.status, dialogue.STATUS_UNSUPPORTED_MISSING_TOOL)
        self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_TOOL_MISSING)
        self.assertEqual(_tool_names(result), [])

    def test_plus_haut_without_state_clarifies(self) -> None:
        result = dialogue.plan_biblio_dialogue("plus haut")

        self.assertEqual(result.status, dialogue.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(result.reason_code, dialogue.REASON_CURRENT_DOCUMENT_MISSING)
        self.assertEqual(_tool_names(result), [])

    def test_compare_without_candidates_clarifies(self) -> None:
        result = dialogue.plan_biblio_dialogue("Compare les deux passages")

        self.assertEqual(result.status, dialogue.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(result.reason_code, dialogue.REASON_CANDIDATES_MISSING)
        self.assertEqual(_tool_names(result), [])

    def test_compare_with_candidates_plans_bounded_context(self) -> None:
        state = _state_with_candidates()

        result = dialogue.plan_biblio_dialogue("Compare les deux passages", state=state)

        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_COMPARE_CANDIDATES)
        self.assertEqual(_tool_names(result), [tools.TOOL_PASSAGE_CONTEXT, tools.TOOL_PASSAGE_CONTEXT])
        self.assertEqual(result.plan.tool_calls[0].params["paragraph_id"], 101)
        self.assertEqual(result.plan.tool_calls[1].params["page_no"], 13)
        self.assertEqual(result.plan.tool_calls[1].params["para_no"], 4)

    def test_table_of_contents_deictic_request_uses_current_document(self) -> None:
        state = _state_with_document()

        result = dialogue.plan_biblio_dialogue("Ouvre la table des matieres de celui-la", state=state)

        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_TABLE_OF_CONTENTS)
        self.assertEqual(_tool_names(result), [tools.TOOL_DOCUMENT_TOC])
        self.assertEqual(result.plan.tool_calls[0].params["document_id"], "doc-1")

    def test_table_of_contents_explicit_title_does_not_silently_use_current_document(self) -> None:
        state = _state_with_document()

        result = dialogue.plan_biblio_dialogue("Montre la table des matieres du Theetete", state=state)

        self.assertEqual(result.status, dialogue.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(result.reason_code, dialogue.REASON_TOC_EXPLICIT_REFERENCE_UNRESOLVED)
        self.assertEqual(_tool_names(result), [])
        self.assertFalse(result.current_document_used)

    def test_dictated_theme_query_plans_search(self) -> None:
        result = dialogue.plan_biblio_dialogue("cherche le moment ou Socrate parle de sage femme")

        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_THEME_SEARCH)
        self.assertEqual(_tool_names(result), [tools.TOOL_CATALOG_SEARCH])
        self.assertGreater(result.query_variant_count, 0)

    def test_observability_and_repr_are_content_free(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "passage_hash": "a" * 12})

        result = dialogue.plan_biblio_dialogue(
            f"Dans ce livre, cherche {RAW_USER} {RAW_TITLE} {RAW_PASSAGE}",
            state=state,
        )
        encoded = _json(result.to_observability())
        repr_encoded = repr(result)

        for raw in (RAW_USER, RAW_TITLE, RAW_PASSAGE):
            with self.subTest(raw=raw):
                self.assertNotIn(raw, encoded)
                self.assertNotIn(raw, repr_encoded)

    def test_dialogue_planner_has_no_external_agent_wiring_imports(self) -> None:
        source = inspect.getsource(dialogue).lower()

        self.assertNotIn("openrouter", source)
        self.assertNotIn("chat_runtime", source)
        self.assertNotIn("model_call", source)
        self.assertNotIn("llm", source)


def _state_with_document(*, last_result: dict[str, object] | None = None) -> BiblioConversationState:
    return BiblioConversationState(
        current_document={"document_id": "doc-1", "doc_id_short": "doc00001"},
        last_result=last_result or {},
    )


def _state_with_candidates() -> BiblioConversationState:
    return BiblioConversationState(
        current_document={"document_id": "doc-1", "doc_id_short": "doc00001"},
        last_candidates=(
            {"document_id": "doc-1", "doc_id_short": "doc00001", "paragraph_id": 101},
            {"document_id": "doc-1", "doc_id_short": "doc00001", "page_no": 13, "para_no": 4},
        ),
        last_ambiguity={"status": "ambiguous", "candidate_count": 2},
    )


def _tool_names(result: dialogue.BiblioDialoguePlanningResult) -> list[str]:
    return [call.tool_name for call in result.plan.tool_calls]


def _json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
