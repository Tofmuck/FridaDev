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
from biblio import librarian_dialogue_navigation as dialogue_navigation
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

    def test_discursive_before_does_not_block_catalogue_list(self) -> None:
        for message in (
            "Avant tout, quels ouvrages as-tu ?",
            "Avant de chercher, liste le catalogue",
        ):
            with self.subTest(message=message):
                result = dialogue.plan_biblio_dialogue(message)

                self.assertEqual(result.status, dialogue.STATUS_PLANNED)
                self.assertEqual(result.reason_code, dialogue.REASON_CATALOG_LIST)
                self.assertEqual(result.intent.intent, dialogue.INTENT_LIST_CATALOG)
                self.assertEqual(_tool_names(result), [tools.TOOL_CATALOG_LIST])

    def test_thematic_before_does_not_become_navigation(self) -> None:
        result = dialogue.plan_biblio_dialogue("Avant Socrate, cherche maieutique")

        self.assertNotEqual(result.status, dialogue.STATUS_UNSUPPORTED_MISSING_TOOL)
        self.assertNotEqual(result.intent.intent, dialogue.INTENT_NAVIGATE)
        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_THEME_SEARCH)
        self.assertEqual(_tool_names(result), [tools.TOOL_CATALOG_SEARCH])

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

    def test_definite_passage_reference_with_last_result_plans_bounded_context(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "paragraph_id": 101})

        for message in ("Explique le passage", "reprends le passage", "resume le passage", "relis le passage"):
            with self.subTest(message=message):
                result = dialogue.plan_biblio_dialogue(message, state=state)

                self.assertEqual(result.status, dialogue.STATUS_PLANNED)
                self.assertEqual(result.reason_code, dialogue.REASON_LAST_PASSAGE_CONTEXT)
                self.assertEqual(_tool_names(result), [tools.TOOL_PASSAGE_CONTEXT])
                self.assertEqual(result.plan.tool_calls[0].params["paragraph_id"], 101)

    def test_this_passage_without_state_clarifies(self) -> None:
        result = dialogue.plan_biblio_dialogue("Explique ce passage")

        self.assertEqual(result.status, dialogue.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(result.reason_code, dialogue.REASON_LAST_PASSAGE_MISSING)
        self.assertEqual(_tool_names(result), [])

    def test_definite_passage_reference_without_state_clarifies(self) -> None:
        result = dialogue.plan_biblio_dialogue("Explique le passage")

        self.assertEqual(result.status, dialogue.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(result.reason_code, dialogue.REASON_LAST_PASSAGE_MISSING)
        self.assertEqual(_tool_names(result), [])

    def test_navigation_request_missing_tool_does_not_plan_forbidden_tool(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "page_no": 12, "para_no": 3})

        result = dialogue.plan_biblio_dialogue("Et le passage suivant ?", state=state)

        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_PAGE_READ)
        self.assertEqual(result.tool_required, "navigation_page_next")
        self.assertEqual(_tool_names(result), [tools.TOOL_PAGE_READ])
        self.assertEqual(result.plan.tool_calls[0].params["page_no"], 13)

    def test_passage_before_request_stays_navigation_missing_tool(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "page_no": 12, "para_no": 3})

        result = dialogue.plan_biblio_dialogue("Je veux le passage avant celui-ci", state=state)

        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_PAGE_READ)
        self.assertEqual(result.tool_required, "navigation_page_previous")
        self.assertEqual(_tool_names(result), [tools.TOOL_PAGE_READ])
        self.assertEqual(result.plan.tool_calls[0].params["page_no"], 11)

    def test_plus_haut_with_state_plans_previous_context_when_anchor_is_precise(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "page_no": 12, "para_no": 3})

        result = dialogue.plan_biblio_dialogue("plus haut", state=state)

        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_CONTEXT_PREVIOUS)
        self.assertEqual(_tool_names(result), [tools.TOOL_PASSAGE_CONTEXT])
        self.assertEqual(result.plan.tool_calls[0].params["page_no"], 12)
        self.assertEqual(result.plan.tool_calls[0].params["para_no"], 2)

    def test_plus_haut_at_page_start_falls_back_to_previous_page(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "page_no": 12, "para_no": 1})

        result = dialogue.plan_biblio_dialogue("plus haut", state=state)

        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_PAGE_READ)
        self.assertEqual(_tool_names(result), [tools.TOOL_PAGE_READ])
        self.assertEqual(result.plan.tool_calls[0].params["page_no"], 11)

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

        for message in (
            "Montre la table des matieres du Theetete",
            "Du Theetete, donne moi la table des matieres",
            "Theetete table des matieres",
            "Theetete sommaire",
            "Sommaire du Theetete",
            "Table des matieres Theetete",
            "Montre moi le sommaire Theetete",
            "Sommaire Theetete",
            "Table des matieres Platon",
            "Table des matieres complete Theetete",
            "Sommaire complet Theetete",
            "Sommaire general Platon",
            "Table des matieres detaillee Platon",
            "Table des matieres complete du Theetete",
            "Sommaire complet du Theetete",
        ):
            with self.subTest(message=message):
                result = dialogue.plan_biblio_dialogue(message, state=state)

                self.assertEqual(result.status, dialogue.STATUS_NEEDS_CLARIFICATION)
                self.assertEqual(result.reason_code, dialogue.REASON_TOC_EXPLICIT_REFERENCE_UNRESOLVED)
                self.assertEqual(_tool_names(result), [])
                self.assertFalse(result.current_document_used)

    def test_table_of_contents_deictic_book_request_uses_current_document(self) -> None:
        state = _state_with_document()

        for message in (
            "Sommaire de ce livre",
            "Table des matieres de cet ouvrage",
        ):
            with self.subTest(message=message):
                result = dialogue.plan_biblio_dialogue(message, state=state)

                self.assertEqual(result.status, dialogue.STATUS_PLANNED)
                self.assertEqual(result.reason_code, dialogue.REASON_TABLE_OF_CONTENTS)
                self.assertEqual(_tool_names(result), [tools.TOOL_DOCUMENT_TOC])
                self.assertEqual(result.plan.tool_calls[0].params["document_id"], "doc-1")

    def test_table_of_contents_suffix_qualifiers_use_current_document(self) -> None:
        state = _state_with_document()

        for message in (
            "Table des matieres",
            "Sommaire",
            "Table des matieres complete",
            "Montre la table des matieres complete",
            "Table des matieres detaillee",
            "Sommaire complet",
            "Sommaire general",
        ):
            with self.subTest(message=message):
                result = dialogue.plan_biblio_dialogue(message, state=state)

                self.assertEqual(result.status, dialogue.STATUS_PLANNED)
                self.assertEqual(result.reason_code, dialogue.REASON_TABLE_OF_CONTENTS)
                self.assertEqual(_tool_names(result), [tools.TOOL_DOCUMENT_TOC])
                self.assertEqual(result.plan.tool_calls[0].params["document_id"], "doc-1")

    def test_table_of_contents_politeness_suffixes_use_current_document(self) -> None:
        state = _state_with_document()

        for message in (
            "Table des matieres complete stp",
            "Table des matieres complete s il te plait",
            "Sommaire general merci",
            "Sommaire complet maintenant",
        ):
            with self.subTest(message=message):
                result = dialogue.plan_biblio_dialogue(message, state=state)

                self.assertEqual(result.status, dialogue.STATUS_PLANNED)
                self.assertEqual(result.reason_code, dialogue.REASON_TABLE_OF_CONTENTS)
                self.assertEqual(_tool_names(result), [tools.TOOL_DOCUMENT_TOC])
                self.assertEqual(result.plan.tool_calls[0].params["document_id"], "doc-1")

    def test_table_of_contents_politeness_suffixes_without_state_clarify(self) -> None:
        result = dialogue.plan_biblio_dialogue("Table des matieres complete stp")

        self.assertEqual(result.status, dialogue.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(result.reason_code, dialogue.REASON_CURRENT_DOCUMENT_MISSING)
        self.assertEqual(_tool_names(result), [])

    def test_table_of_contents_suffix_qualifiers_without_state_clarify(self) -> None:
        for message in (
            "Table des matieres",
            "Table des matieres complete",
            "Sommaire complet",
            "Sommaire general",
        ):
            with self.subTest(message=message):
                result = dialogue.plan_biblio_dialogue(message)

                self.assertEqual(result.status, dialogue.STATUS_NEEDS_CLARIFICATION)
                self.assertEqual(result.reason_code, dialogue.REASON_CURRENT_DOCUMENT_MISSING)
                self.assertEqual(_tool_names(result), [])

    def test_navigation_with_valid_page_anchor_plans_bounded_page_reads(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "page_no": 12, "para_no": 3})

        for message, scope_mode, expected_pages in (
            ("Montre-moi la page precedente.", "page_previous", [11]),
            ("Montre-moi la page suivante.", "page_next", [13]),
            ("Page 28 a page 32.", "page_explicit", [28, 29, 30, 31, 32]),
        ):
            with self.subTest(message=message):
                result = dialogue.plan_biblio_dialogue(message, state=state)

                self.assertEqual(result.status, dialogue.STATUS_PLANNED)
                self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_PAGE_READ)
                self.assertEqual(result.intent.intent, dialogue.INTENT_NAVIGATE)
                self.assertEqual(result.intent.scope_mode, scope_mode)
                self.assertEqual(result.tool_required, f"navigation_{scope_mode}")
                self.assertEqual(_tool_names(result), [tools.TOOL_PAGE_READ] * len(expected_pages))
                self.assertEqual([call.params["page_no"] for call in result.plan.tool_calls], expected_pages)
                self.assertTrue(result.current_document_used)

    def test_navigation_continue_after_same_page_range_uses_interval_end_anchor(self) -> None:
        state = _state_with_document(
            last_result={
                "document_id": "doc-1",
                "page_no": 12,
                "para_no": 3,
                "interval_hint": {
                    "kind": "range",
                    "mode": "same_page_range",
                    "start_page_no": 12,
                    "end_page_no": 12,
                    "end_para_no": 6,
                    "page_span": 1,
                },
            }
        )

        result = dialogue.plan_biblio_dialogue("Continue apres ce passage.", state=state)

        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_CONTINUE_FROM_RANGE_END)
        self.assertEqual(result.intent.query_kind, "passage_context")
        self.assertEqual(_tool_names(result), [tools.TOOL_PASSAGE_CONTEXT])
        self.assertEqual(
            result.plan.tool_calls[0].params,
            {"document_id": "doc-1", "page_no": 12, "para_no": 6, "window_chars": 1400},
        )

    def test_navigation_continue_after_multi_page_range_uses_interval_end_anchor(self) -> None:
        state = _state_with_document(
            last_result={
                "document_id": "doc-1",
                "page_no": 12,
                "para_no": 3,
                "interval_hint": {
                    "kind": "range",
                    "mode": "multi_page_range",
                    "start_page_no": 12,
                    "end_page_no": 14,
                    "end_para_no": 2,
                    "page_span": 3,
                },
            }
        )

        result = dialogue.plan_biblio_dialogue("Continue apres ce passage.", state=state)

        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_CONTINUE_FROM_RANGE_END)
        self.assertEqual(result.intent.query_kind, "passage_context")
        self.assertEqual(_tool_names(result), [tools.TOOL_PASSAGE_CONTEXT])
        self.assertEqual(
            result.plan.tool_calls[0].params,
            {"document_id": "doc-1", "page_no": 14, "para_no": 2, "window_chars": 1400},
        )

    def test_navigation_continue_after_canonical_range_segment_uses_next_anchor(self) -> None:
        state = _state_with_document(
            last_result={
                "document_id": "doc-1",
                "page_no": 12,
                "para_no": 3,
                "interval_hint": {
                    "kind": "range",
                    "mode": "multi_page_range_segment",
                    "state": "segment",
                    "start_page_no": 12,
                    "end_page_no": 14,
                    "end_para_no": 2,
                    "requested_end_page_no": 15,
                    "requested_end_para_no": 4,
                    "next_page_no": 14,
                    "next_para_no": 3,
                    "page_span": 3,
                },
            }
        )

        result = dialogue.plan_biblio_dialogue("Continue apres ce passage.", state=state)

        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_CONTINUE_FROM_RANGE_END)
        self.assertEqual(result.intent.query_kind, "passage_context")
        self.assertEqual(_tool_names(result), [tools.TOOL_PASSAGE_CONTEXT])
        self.assertEqual(
            result.plan.tool_calls[0].params,
            {"document_id": "doc-1", "page_no": 14, "para_no": 3, "window_chars": 1400},
        )

    def test_navigation_page_next_after_range_stays_page_granular(self) -> None:
        state = _state_with_document(
            last_result={
                "document_id": "doc-1",
                "page_no": 12,
                "para_no": 3,
                "interval_hint": {
                    "kind": "range",
                    "mode": "multi_page_range",
                    "start_page_no": 12,
                    "end_page_no": 14,
                    "end_para_no": 2,
                    "page_span": 3,
                },
            }
        )

        result = dialogue.plan_biblio_dialogue("Montre-moi la page suivante.", state=state)

        self.assertEqual(result.status, dialogue.STATUS_PLANNED)
        self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_PAGE_READ)
        self.assertEqual(result.intent.query_kind, "page_read")
        self.assertEqual(_tool_names(result), [tools.TOOL_PAGE_READ])
        self.assertEqual(result.plan.tool_calls[0].params, {"document_id": "doc-1", "page_no": 15})

    def test_navigation_with_valid_state_reports_missing_tools_for_still_unsupported_moves(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "page_no": 12, "para_no": 3})

        for message, scope_mode in (
            ("Plus bas.", "down"),
            ("Cherche un autre passage proche.", "nearby_passage"),
            ("Un autre passage proche.", "nearby_passage"),
            ("Montre un passage voisin.", "nearby_passage"),
            ("Autre extrait voisin.", "nearby_passage"),
        ):
            with self.subTest(message=message):
                result = dialogue.plan_biblio_dialogue(message, state=state)

                self.assertEqual(result.status, dialogue.STATUS_UNSUPPORTED_MISSING_TOOL)
                self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_TOOL_MISSING)
                self.assertEqual(result.intent.intent, dialogue.INTENT_NAVIGATE)
                self.assertEqual(result.intent.scope_mode, scope_mode)
                self.assertEqual(result.tool_required, f"navigation_{scope_mode}")
                self.assertEqual(_tool_names(result), [])

    def test_navigation_explicit_unresolved_reference_does_not_use_current_document(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "paragraph_id": 101})

        for message in (
            "Autour de ce passage dans le Theetete",
            "Autour de ce passage dans Platon",
            "Autour de ce passage chez Platon",
            "Autour de ce passage dans l'Apologie",
            "Autour de ce passage dans l Apologie",
            "Autour de ce passage de l Apologie",
            "Autour de ce passage d'Apologie",
            "Autour de ce passage dans Apologie",
            "Continue dans le Theetete",
            "Continue chez Platon",
            "Page precedente dans Platon",
            "Page precedente chez Platon",
        ):
            with self.subTest(message=message):
                result = dialogue.plan_biblio_dialogue(message, state=state)

                self.assertEqual(result.status, dialogue.STATUS_NEEDS_CLARIFICATION)
                self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_EXPLICIT_REFERENCE_UNRESOLVED)
                self.assertEqual(result.intent.intent, dialogue.INTENT_NAVIGATE)
                self.assertFalse(result.current_document_used)
                self.assertEqual(_tool_names(result), [])

    def test_navigation_explicit_reference_target_extracts_real_named_documents(self) -> None:
        cases = {
            "Dans Platon, page 28 a 32": "Platon",
            "Dans Aristote page suivante": "Aristote",
            "Page precedente chez Friedrich Nietzsche": "Friedrich Nietzsche",
            "Dans le Theetete, page 28 a 32": "Theetete",
            "Continue dans ce livre": "",
        }

        for message, expected in cases.items():
            with self.subTest(message=message):
                self.assertEqual(dialogue_navigation.explicit_reference_target(message), expected)

    def test_nearby_search_with_theme_or_work_stays_thematic_search(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "paragraph_id": 101})

        for message in (
            "Cherche un passage proche de la maieutique",
            "Trouve un passage proche de Socrate",
            "Cherche le passage proche dans le Theetete",
        ):
            with self.subTest(message=message):
                result = dialogue.plan_biblio_dialogue(message, state=state)

                self.assertEqual(result.status, dialogue.STATUS_PLANNED)
                self.assertEqual(result.reason_code, dialogue.REASON_THEME_SEARCH)
                self.assertEqual(result.intent.intent, dialogue.INTENT_SEARCH_PASSAGE)
                self.assertEqual(_tool_names(result), [tools.TOOL_CATALOG_SEARCH])
                self.assertFalse(result.current_document_used)

    def test_around_this_passage_with_valid_state_plans_bounded_context(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "paragraph_id": 101})

        for message in (
            "Autour de ce passage.",
            "Autour de ce passage dans ce livre.",
            "Autour de ce passage dans cet ouvrage.",
            "Autour de ce passage de cet ouvrage.",
            "Autour de ce passage du document.",
        ):
            with self.subTest(message=message):
                result = dialogue.plan_biblio_dialogue(message, state=state)

                self.assertEqual(result.status, dialogue.STATUS_PLANNED)
                self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_CONTEXT_AROUND)
                self.assertEqual(result.intent.intent, dialogue.INTENT_NAVIGATE)
                self.assertEqual(result.intent.scope_mode, "around_passage")
                self.assertEqual(result.tool_required, "navigation_around_passage")
                self.assertEqual(_tool_names(result), [tools.TOOL_PASSAGE_CONTEXT])
                self.assertEqual(result.plan.tool_calls[0].params["paragraph_id"], 101)
                self.assertEqual(result.plan.tool_calls[0].params["window_chars"], 1400)

    def test_origin_question_about_this_passage_plans_bounded_context(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "paragraph_id": 101})

        for message in (
            "D'ou vient ce passage ?",
            "Quelle est la source de ce passage ?",
            "Ce passage provient d'ou ?",
        ):
            with self.subTest(message=message):
                result = dialogue.plan_biblio_dialogue(message, state=state)

                self.assertEqual(result.status, dialogue.STATUS_PLANNED)
                self.assertEqual(result.reason_code, dialogue.REASON_LAST_PASSAGE_ORIGIN)
                self.assertEqual(result.intent.intent, dialogue.INTENT_ORIGIN_CHECK)
                self.assertEqual(_tool_names(result), [tools.TOOL_PASSAGE_CONTEXT])
                self.assertEqual(result.plan.tool_calls[0].params["paragraph_id"], 101)
                self.assertTrue(result.current_document_used)

    def test_deictic_navigation_with_missing_tool_stays_missing_tool(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "paragraph_id": 101})

        for message in ("Continue dans ce livre", "Continue dans cet ouvrage"):
            with self.subTest(message=message):
                result = dialogue.plan_biblio_dialogue(message, state=state)

                self.assertEqual(result.status, dialogue.STATUS_NEEDS_CLARIFICATION)
                self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_PAGE_ANCHOR_MISSING)
                self.assertEqual(result.intent.intent, dialogue.INTENT_NAVIGATE)
                self.assertEqual(result.intent.scope_mode, "continue")
                self.assertEqual(result.tool_required, "navigation_continue")
                self.assertEqual(_tool_names(result), [])

    def test_navigation_without_page_anchor_clarifies(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "paragraph_id": 101})

        for message in ("Continue apres ce passage.", "Montre-moi la page precedente."):
            with self.subTest(message=message):
                result = dialogue.plan_biblio_dialogue(message, state=state)

                self.assertEqual(result.status, dialogue.STATUS_NEEDS_CLARIFICATION)
                self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_PAGE_ANCHOR_MISSING)
                self.assertEqual(_tool_names(result), [])

    def test_navigation_without_state_clarifies(self) -> None:
        for message in ("Continue.", "Plus haut.", "Montre-moi la page precedente."):
            with self.subTest(message=message):
                result = dialogue.plan_biblio_dialogue(message)

                self.assertEqual(result.status, dialogue.STATUS_NEEDS_CLARIFICATION)
                self.assertEqual(result.reason_code, dialogue.REASON_CURRENT_DOCUMENT_MISSING)
                self.assertEqual(result.intent.intent, dialogue.INTENT_NAVIGATE)
                self.assertEqual(_tool_names(result), [])

    def test_explicit_page_range_too_wide_clarifies(self) -> None:
        state = _state_with_document(last_result={"document_id": "doc-1", "page_no": 12, "para_no": 3})

        result = dialogue.plan_biblio_dialogue("Page 28 a page 40", state=state)

        self.assertEqual(result.status, dialogue.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(result.reason_code, dialogue.REASON_NAVIGATION_PAGE_RANGE_TOO_WIDE)
        self.assertEqual(_tool_names(result), [])

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
        source = (inspect.getsource(dialogue) + inspect.getsource(dialogue_navigation)).lower()

        self.assertNotIn("openrouter", source)
        self.assertNotIn("chat_runtime", source)
        self.assertNotIn("model_call", source)
        self.assertNotIn("llm", source)

    def test_dialogue_navigation_has_no_forbidden_catalogue_routes(self) -> None:
        source = (inspect.getsource(dialogue) + inspect.getsource(dialogue_navigation)).lower()

        for forbidden in ("latest/page", "latest/context", "export/chunk"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


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
