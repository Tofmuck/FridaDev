from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import chat_runtime
from biblio import catalogue_client as catalogue
from biblio import conversation_followup
from biblio import conversation_state
from biblio import document_resolver
from biblio import library_runtime
from biblio import librarian_agent
from biblio import librarian_agent_bridge
from biblio import librarian_agent_contract as agent_contract
from biblio import librarian_agent_openrouter as agent_openrouter
from biblio import librarian_product_methods
from biblio import librarian_agent_runtime
from biblio import librarian_tools
from biblio import passage_extractor as extractor
from biblio import prompt_lane
from biblio import query_planner


RAW_PASSAGE = "SYNTHETIC_BIBLIO_CHAT_PASSAGE_MUST_ONLY_APPEAR_IN_PROMPT"


class BiblioChatRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._resolve_settings_before = librarian_agent_runtime._resolve_settings

        def deterministic_unit_settings(config_module=None):
            if config_module is not None:
                return self._resolve_settings_before(config_module)
            return agent_contract.BiblioLibrarianAgentSettings(mode=agent_contract.MODE_OFF)

        librarian_agent_runtime._resolve_settings = deterministic_unit_settings

    def tearDown(self) -> None:
        librarian_agent_runtime._resolve_settings = self._resolve_settings_before

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

    def test_toggle_off_with_existing_state_does_not_reattach_current_user_message(self) -> None:
        state, _transition = conversation_state.update_state_from_runtime(
            conversation_state.BiblioConversationState.empty(conversation_id="conv-biblio-state"),
            query_plan=query_planner.BiblioQueryPlan(
                should_consult=True,
                intent=query_planner.INTENT_SEARCH_CATALOG,
                reason_code=query_planner.REASON_SEARCH_CATALOG,
                query_kind=query_planner.INTENT_SEARCH_CATALOG,
            ),
            library_result=_RuntimeResult(passage_result=_passage(RAW_PASSAGE), status="extracted"),
            conversation_id="conv-biblio-state",
            now_iso="2026-05-31T12:00:00Z",
        )
        conversation = {
            "id": "conv-biblio-state",
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "ancienne demande", "meta": {"biblio_state": state.to_dict()}},
                {"role": "assistant", "content": "ancienne reponse"},
                {"role": "user", "content": "message courant"},
            ],
        }

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": False},
            user_msg="message courant",
            conversation_id="conv-biblio-state",
            conversation_state=chat_runtime.read_biblio_conversation_state(conversation),
            client_factory=_raising_client_factory,
        )
        attached = chat_runtime.attach_biblio_conversation_state(conversation, result)

        self.assertFalse(result.used)
        self.assertFalse(attached)
        self.assertNotIn("meta", conversation["messages"][-1])
        self.assertTrue(chat_runtime.read_biblio_conversation_state(conversation).present)

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

    def test_agent_mode_off_does_not_call_model(self) -> None:
        fake_model = _FakeAgentModel(_valid_agent_json())
        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Explique simplement ce concept.",
            client_factory=_raising_client_factory,
            config_module=SimpleNamespace(BIBLIO_LIBRARIAN_AGENT_MODE="off"),
            librarian_agent_factory=lambda: librarian_agent.BiblioLibrarianAgent(fake_model),
        )

        self.assertFalse(result.used)
        self.assertEqual(fake_model.calls, 0)
        self.assertEqual(result.observability_payload["librarian_agent"]["status"], "skipped")
        self.assertFalse(result.observability_payload["librarian_agent"]["model_called"])

    def test_biblio_toggle_off_does_not_call_agent_even_if_agent_shadow_configured(self) -> None:
        fake_model = _FakeAgentModel(_valid_agent_json())
        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": False},
            user_msg="passage 126b dans Platon",
            client_factory=_raising_client_factory,
            config_module=_agent_config("shadow"),
            librarian_agent_factory=lambda: librarian_agent.BiblioLibrarianAgent(fake_model),
        )

        self.assertFalse(result.enabled)
        self.assertFalse(result.used)
        self.assertEqual(fake_model.calls, 0)
        self.assertEqual(result.observability_payload["librarian_agent"], {})

    def test_agent_shadow_compares_without_changing_deterministic_response(self) -> None:
        fake_model = _FakeAgentModel(_valid_agent_json(tool_name=librarian_tools.TOOL_CATALOG_SEARCH, params={"query": "hidden"}))
        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Explique simplement ce concept.",
            recent_dialogue=({"role": "user", "content": "RAW DIALOGUE MUST NOT LEAK"},),
            client_factory=_raising_client_factory,
            config_module=_agent_config("shadow"),
            librarian_agent_factory=lambda: librarian_agent.BiblioLibrarianAgent(fake_model),
        )
        observed = result.observability_payload["librarian_agent"]
        encoded = json.dumps(result.observability_payload, ensure_ascii=False, sort_keys=True)

        self.assertFalse(result.used)
        self.assertIsNone(result.prompt_message)
        self.assertEqual(result.observability_payload["client"]["event_count"], 0)
        self.assertEqual(fake_model.calls, 1)
        self.assertEqual(observed["mode"], "shadow")
        self.assertEqual(observed["comparison_kind"], "deterministic_comparison")
        self.assertTrue(observed["model_called"])
        self.assertFalse(observed["used_for_response"])
        self.assertTrue(observed["deterministic_controller"])
        self.assertFalse(observed["product_response_changed"])
        self.assertEqual(observed["tool_execution_status"], "not_executed")
        self.assertEqual(observed["tool_call_event_count"], 0)
        self.assertEqual(observed["selection_event_count"], 0)
        self.assertEqual(observed["state_update_event_count"], 0)
        self.assertEqual(observed["final_event_count"], 0)
        self.assertFalse(observed["agent_loop_executed"])
        self.assertNotIn("request", observed)
        request_observation = observed["request_observation"]
        self.assertTrue(request_observation["user_message_present"])
        self.assertEqual(request_observation["user_message_chars"], len("Explique simplement ce concept."))
        self.assertEqual(
            request_observation["user_message_hash"],
            hashlib.sha256("Explique simplement ce concept.".encode("utf-8")).hexdigest()[:12],
        )
        self.assertEqual(request_observation["recent_dialogue_count"], 1)
        self.assertEqual(request_observation["bounded_recent_dialogue_count"], 1)
        self.assertEqual(
            request_observation["recent_dialogue_hashes"],
            [hashlib.sha256("RAW DIALOGUE MUST NOT LEAK".encode("utf-8")).hexdigest()[:12]],
        )
        self.assertEqual(request_observation["settings"]["primary_model"], "model/x")
        self.assertEqual(observed["agent"]["validation"]["tool_names"], [librarian_tools.TOOL_CATALOG_SEARCH])
        self.assertEqual(observed["agent"]["validation"]["plan"]["tool_names"], [librarian_tools.TOOL_CATALOG_SEARCH])
        self.assertEqual(observed["agent"]["validation"]["json_hash"], hashlib.sha256(fake_model.content.encode("utf-8")).hexdigest()[:12])
        self.assertEqual(observed["agent"]["validation"]["finish_reason"], "stop")
        self.assertNotIn("Explique simplement ce concept.", encoded)
        self.assertNotIn("RAW DIALOGUE MUST NOT LEAK", encoded)
        self.assertNotIn("hidden", encoded)

    def test_agent_candidate_keeps_candidate_observable_without_using_response(self) -> None:
        fake_model = _FakeAgentModel(_valid_agent_json(tool_name=librarian_tools.TOOL_CATALOG_LIST, params={"limit": 10}))
        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Explique simplement ce concept.",
            client_factory=_raising_client_factory,
            config_module=_agent_config("candidate"),
            librarian_agent_factory=lambda: librarian_agent.BiblioLibrarianAgent(fake_model),
        )
        observed = result.observability_payload["librarian_agent"]

        self.assertFalse(result.used)
        self.assertEqual(fake_model.calls, 1)
        self.assertEqual(observed["mode"], "candidate")
        self.assertTrue(observed["candidate_plan_present"])
        self.assertFalse(observed["used_for_response"])

    def test_agent_active_is_not_product_enabled(self) -> None:
        fake_model = _FakeAgentModel(_valid_agent_json())
        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Explique simplement ce concept.",
            client_factory=_raising_client_factory,
            config_module=_agent_config("active"),
            librarian_agent_factory=lambda: librarian_agent.BiblioLibrarianAgent(fake_model),
        )
        observed = result.observability_payload["librarian_agent"]

        self.assertFalse(result.used)
        self.assertEqual(fake_model.calls, 1)
        self.assertEqual(observed["agent"]["reason_code"], librarian_agent.REASON_ACTIVE_VALIDATED)
        self.assertTrue(observed["candidate_plan_present"])
        self.assertFalse(observed["used_for_response"])
        self.assertTrue(observed["fallback_deterministic"])

    def test_agent_first_executes_work_lookup_method_when_deterministic_has_no_signal(self) -> None:
        fake_model = _FakeAgentModel(
            _valid_agent_json(
                tool_name=librarian_tools.TOOL_CATALOG_SEARCH,
                params={"query": "RAW AGENT QUERY MUST NOT LEAK", "limit": 5},
                product_method=librarian_product_methods.PRODUCT_METHOD_WORK_LOOKUP,
                case_id="",
            )
        )
        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Trouve-moi le Théétète de Platon.",
            client_factory=lambda **_kwargs: _FakeClient(),
            config_module=_agent_config("active"),
            librarian_agent_factory=lambda: librarian_agent.BiblioLibrarianAgent(fake_model),
        )
        observed = result.observability_payload["librarian_agent"]
        encoded = json.dumps(result.observability_payload, ensure_ascii=False, sort_keys=True)

        self.assertTrue(result.used)
        self.assertIsNotNone(result.prompt_message)
        self.assertEqual(result.query_kind, chat_runtime.QUERY_KIND_AGENT_FIRST)
        self.assertEqual(result.observability_payload["client"]["event_count"], 2)
        self.assertEqual(result.observability_payload["client"]["items"][0]["endpoint_kind"], "search")
        self.assertEqual(result.observability_payload["client"]["items"][1]["endpoint_kind"], "metadata")
        self.assertEqual(result.observability_payload["status"], "agent_first_executed")
        self.assertEqual(result.observability_payload["reason_code"], "biblio_agent_first_plan_executed")
        self.assertTrue(observed["used_for_response"])
        self.assertFalse(observed["deterministic_controller"])
        self.assertTrue(observed["product_response_changed"])
        self.assertTrue(observed["agent_loop_executed"])
        self.assertEqual(observed["execution_scope"], "agent_first")
        self.assertEqual(observed["tool_execution_status"], "executed")
        self.assertEqual(observed["tool_call_event_count"], 2)
        self.assertEqual(
            observed["tool_loop"]["tool_names"],
            [librarian_tools.TOOL_CATALOG_SEARCH, librarian_tools.TOOL_DOCUMENT_OPEN_SUMMARY],
        )
        self.assertEqual(observed["tool_loop"]["endpoint_kinds"], ["search", "metadata"])
        self.assertNotIn("RAW AGENT QUERY MUST NOT LEAK", encoded)
        self.assertNotIn("RAW SEARCH TEXT MUST NOT BE OBSERVABLE", encoded)

    def test_agent_first_theme_search_completes_to_context_when_deterministic_requests_passage(self) -> None:
        fake_model = _FakeAgentModel(
            _valid_agent_json(
                tool_name=librarian_tools.TOOL_CATALOG_SEARCH,
                params={"query": "RAW AGENT QUERY MUST NOT LEAK", "limit": 5},
            )
        )
        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Cherche le passage sur la maieutique dans le Theetete",
            client_factory=lambda **_kwargs: _FakeClient(),
            config_module=_agent_config("active"),
            librarian_agent_factory=lambda: librarian_agent.BiblioLibrarianAgent(fake_model),
        )
        encoded = json.dumps(result.observability_payload, ensure_ascii=False, sort_keys=True)

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, chat_runtime.QUERY_KIND_AGENT_FIRST)
        self.assertEqual(result.observability_payload["client"]["event_count"], 2)
        self.assertEqual(
            [item["endpoint_kind"] for item in result.observability_payload["client"]["items"]],
            ["search", "context"],
        )
        self.assertEqual(result.observability_payload["lane"]["passage_count"], 1)
        self.assertNotIn("RAW AGENT QUERY MUST NOT LEAK", encoded)
        self.assertNotIn("RAW SEARCH TEXT MUST NOT BE OBSERVABLE", encoded)
        self.assertNotIn("RAW CONTEXT TEXT MUST NOT BE OBSERVABLE", encoded)

    def test_agent_first_executes_explicit_locator_range_when_agent_plan_is_valid(self) -> None:
        fake_model = _FakeAgentModel(
            _valid_agent_json(
                product_method=librarian_product_methods.PRODUCT_METHOD_PASSAGE_EXTRACT_CANONICAL_RANGE,
                tool_name=librarian_tools.TOOL_CATALOG_SEARCH,
                params={"query": "RAW AGENT QUERY MUST NOT LEAK", "limit": 5},
            )
        )
        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Bon, vas-y, tu me balances ici un extrait du Théétète de Platon. On va dire 126b à 128a.",
            client_factory=lambda **_kwargs: _FakeClient(),
            config_module=_agent_config("active"),
            librarian_agent_factory=lambda: librarian_agent.BiblioLibrarianAgent(fake_model),
        )
        agent_observed = result.observability_payload["librarian_agent"]

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, chat_runtime.QUERY_KIND_AGENT_FIRST)
        self.assertEqual(fake_model.calls, 1)
        self.assertTrue(agent_observed["candidate_plan_present"])
        self.assertTrue(agent_observed["used_for_response"])
        self.assertFalse(agent_observed["deterministic_controller"])
        self.assertTrue(agent_observed["agent_loop_executed"])
        self.assertGreaterEqual(agent_observed["tool_call_event_count"], 2)
        self.assertEqual(agent_observed["tool_execution_status"], "executed")
        self.assertIn("context", agent_observed["tool_loop"]["endpoint_kinds"])
        self.assertEqual(result.observability_payload["product_case_id"], "P10")
        self.assertEqual(
            result.observability_payload["product_method"],
            librarian_product_methods.PRODUCT_METHOD_PASSAGE_SET_CURRENT_REFERENCE,
        )
        self.assertEqual(result.observability_payload["product_truth"], librarian_product_methods.TRUTH_LEVEL_EXACT)

    def test_agent_first_uses_bounded_fallback_plan_when_active_model_returns_invalid_json(self) -> None:
        fake_model = _FakeAgentModel("not json")
        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Dans le Theetete, trouve le passage ou Socrate parle de la maieutique.",
            client_factory=lambda **_kwargs: _FakeClient(),
            config_module=_agent_config("active"),
            librarian_agent_factory=lambda: librarian_agent.BiblioLibrarianAgent(fake_model),
        )
        observed = result.observability_payload["librarian_agent"]
        encoded = json.dumps(result.observability_payload, ensure_ascii=False, sort_keys=True)

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, chat_runtime.QUERY_KIND_AGENT_FIRST)
        self.assertTrue(observed["candidate_plan_present"])
        self.assertEqual(observed["agent"]["reason_code"], agent_contract.REASON_JSON_FREE_TEXT)
        self.assertEqual(observed["execution_scope"], "agent_first")
        self.assertEqual(result.observability_payload["client"]["event_count"], 2)
        self.assertNotIn("RAW SEARCH TEXT MUST NOT BE OBSERVABLE", encoded)
        self.assertNotIn("RAW CONTEXT TEXT MUST NOT BE OBSERVABLE", encoded)

    def test_agent_first_query_fallback_plan_carries_product_method(self) -> None:
        query_plan = query_planner.plan_biblio_query("Dans le Theetete, trouve le passage ou Socrate parle de la maieutique.")

        fallback = librarian_agent_bridge.build_query_fallback_plan(query_plan)

        self.assertIsNotNone(fallback)
        assert fallback is not None
        self.assertEqual(fallback.case_id, "")
        self.assertEqual(fallback.product_method, librarian_product_methods.PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK)
        self.assertEqual([call.tool_name for call in fallback.tool_calls], [librarian_tools.TOOL_CATALOG_SEARCH])

    def test_agent_first_invalid_json_uses_dialogue_state_fallback_for_context_followup(self) -> None:
        fake_model = _FakeAgentModel("not json")
        state = conversation_state.BiblioConversationState(
            conversation_id="conv-agent-first-state",
            current_document={"document_id": "doc-1234", "doc_id_short": "doc-1234"},
            last_result={"document_id": "doc-1234", "paragraph_id": 99, "passage_hash": "a" * 12},
            last_passage_hash="a" * 12,
            last_intent="extract_passage",
        )

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Autour de ce passage.",
            conversation_id="conv-agent-first-state",
            conversation_state=state,
            client_factory=lambda **_kwargs: _FakeClient(),
            config_module=_agent_config("active"),
            librarian_agent_factory=lambda: librarian_agent.BiblioLibrarianAgent(fake_model),
        )
        observed = result.observability_payload["librarian_agent"]
        encoded = json.dumps(result.observability_payload, ensure_ascii=False, sort_keys=True)

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, chat_runtime.QUERY_KIND_AGENT_FIRST)
        self.assertTrue(observed["candidate_plan_present"])
        self.assertEqual(observed["execution_scope"], "agent_first")
        self.assertEqual(result.observability_payload["client"]["event_count"], 1)
        self.assertEqual(result.observability_payload["client"]["items"][0]["endpoint_kind"], "context")
        self.assertEqual(result.observability_payload["lane"]["passage_count"], 1)
        self.assertFalse(observed["deterministic_controller"])
        self.assertNotIn("RAW CONTEXT TEXT MUST NOT BE OBSERVABLE", encoded)

    def test_agent_first_dialogue_fallback_plan_carries_show_around_current_method(self) -> None:
        state = conversation_state.BiblioConversationState(
            conversation_id="conv-agent-first-state",
            current_document={"document_id": "doc-1234", "doc_id_short": "doc-1234"},
            last_result={"document_id": "doc-1234", "paragraph_id": 99, "passage_hash": "a" * 12},
            last_passage_hash="a" * 12,
            last_intent="extract_passage",
        )

        fallback = librarian_agent_bridge.build_dialogue_fallback_plan(
            user_msg="Autour de ce passage.",
            state=state,
            recent_dialogue=(),
        )

        self.assertIsNotNone(fallback)
        assert fallback is not None
        self.assertEqual(fallback.case_id, "")
        self.assertEqual(fallback.product_method, librarian_product_methods.PRODUCT_METHOD_PASSAGE_SHOW_AROUND_CURRENT)
        self.assertEqual([call.tool_name for call in fallback.tool_calls], [librarian_tools.TOOL_PASSAGE_CONTEXT])

    def test_agent_first_dialogue_fallback_plan_carries_origin_check_method(self) -> None:
        state = conversation_state.BiblioConversationState(
            conversation_id="conv-agent-first-origin",
            current_document={"document_id": "doc-1234", "doc_id_short": "doc-1234"},
            last_result={"document_id": "doc-1234", "paragraph_id": 99, "passage_hash": "a" * 12},
            last_passage_hash="a" * 12,
            last_intent="extract_passage",
        )

        fallback = librarian_agent_bridge.build_dialogue_fallback_plan(
            user_msg="D'ou vient ce passage ?",
            state=state,
            recent_dialogue=(),
        )

        self.assertIsNotNone(fallback)
        assert fallback is not None
        self.assertEqual(fallback.case_id, "")
        self.assertEqual(fallback.product_method, librarian_product_methods.PRODUCT_METHOD_PASSAGE_ORIGIN_CHECK)
        self.assertEqual([call.tool_name for call in fallback.tool_calls], [librarian_tools.TOOL_PASSAGE_CONTEXT])

    def test_agent_first_dialogue_fallback_plan_carries_compare_candidates_method(self) -> None:
        state = conversation_state.BiblioConversationState(
            conversation_id="conv-agent-first-compare",
            last_candidates=[
                {"document_id": "doc-1", "paragraph_id": 101, "passage_hash": "a" * 12},
                {"document_id": "doc-1", "page_no": 13, "para_no": 4, "passage_hash": "b" * 12},
            ],
        )

        fallback = librarian_agent_bridge.build_dialogue_fallback_plan(
            user_msg="Compare les deux passages",
            state=state,
            recent_dialogue=(),
        )

        self.assertIsNotNone(fallback)
        assert fallback is not None
        self.assertEqual(fallback.case_id, "")
        self.assertEqual(
            fallback.product_method,
            librarian_product_methods.PRODUCT_METHOD_PASSAGE_COMPARE_CANDIDATES,
        )
        self.assertEqual(
            [call.tool_name for call in fallback.tool_calls],
            [librarian_tools.TOOL_PASSAGE_CONTEXT, librarian_tools.TOOL_PASSAGE_CONTEXT],
        )

    def test_agent_first_invalid_json_uses_dialogue_state_fallback_for_origin_check(self) -> None:
        fake_model = _FakeAgentModel("not json")
        state = conversation_state.BiblioConversationState(
            conversation_id="conv-agent-first-origin",
            current_document={"document_id": "doc-1234", "doc_id_short": "doc-1234"},
            last_result={"document_id": "doc-1234", "paragraph_id": 99, "passage_hash": "a" * 12},
            last_passage_hash="a" * 12,
            last_intent="extract_passage",
        )

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="D'ou vient ce passage ?",
            conversation_id="conv-agent-first-origin",
            conversation_state=state,
            client_factory=lambda **_kwargs: _FakeClient(),
            config_module=_agent_config("active"),
            librarian_agent_factory=lambda: librarian_agent.BiblioLibrarianAgent(fake_model),
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, chat_runtime.QUERY_KIND_AGENT_FIRST)
        self.assertEqual(result.observability_payload["client"]["event_count"], 1)
        self.assertEqual(result.observability_payload["client"]["items"][0]["endpoint_kind"], "context")
        self.assertEqual(result.observability_payload["lane"]["passage_count"], 1)
        self.assertTrue(result.biblio_state.has_last_anchor if result.biblio_state else False)

    def test_agent_first_empty_candidate_plan_uses_dialogue_state_fallback(self) -> None:
        fake_model = _FakeAgentModel(_empty_agent_plan_json())
        state = conversation_state.BiblioConversationState(
            conversation_id="conv-agent-first-empty",
            current_document={"document_id": "doc-1234", "doc_id_short": "doc-1234"},
            last_result={"document_id": "doc-1234", "paragraph_id": 99, "passage_hash": "a" * 12},
            last_passage_hash="a" * 12,
            last_intent="extract_passage",
        )

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="D'ou vient ce passage ?",
            conversation_id="conv-agent-first-empty",
            conversation_state=state,
            client_factory=lambda **_kwargs: _FakeClient(),
            config_module=_agent_config("active"),
            librarian_agent_factory=lambda: librarian_agent.BiblioLibrarianAgent(fake_model),
        )
        observed = result.observability_payload["librarian_agent"]

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, chat_runtime.QUERY_KIND_AGENT_FIRST)
        self.assertTrue(observed["candidate_plan_present"])
        self.assertEqual(result.observability_payload["client"]["event_count"], 1)
        self.assertEqual(result.observability_payload["client"]["items"][0]["endpoint_kind"], "context")
        self.assertEqual(result.observability_payload["lane"]["passage_count"], 1)
        self.assertTrue(observed["used_for_response"])

    def test_agent_invalid_json_forbidden_tool_and_timeout_keep_deterministic_response(self) -> None:
        cases = [
            _FakeAgentModel("not json"),
            _FakeAgentModel(_valid_agent_json(tool_name="latest/page")),
            _FakeAgentModel(
                response=agent_openrouter.BiblioLibrarianAgentModelResponse(
                    status=agent_openrouter.STATUS_ERROR,
                    reason_code=agent_openrouter.REASON_TIMEOUT,
                    attempt_count=1,
                )
            ),
        ]
        for fake_model in cases:
            with self.subTest(response=fake_model.response.reason_code if fake_model.response else "content"):
                result = chat_runtime.run_biblio_chat_turn(
                    {"biblio_enabled": True},
                    user_msg="Explique simplement ce concept.",
                    client_factory=_raising_client_factory,
                    config_module=_agent_config("shadow"),
                    librarian_agent_factory=lambda fake=fake_model: librarian_agent.BiblioLibrarianAgent(fake),
                )
                observed = result.observability_payload["librarian_agent"]

                self.assertFalse(result.used)
                self.assertIsNone(result.prompt_message)
                self.assertFalse(observed["used_for_response"])
                self.assertTrue(observed["fallback_deterministic"])

    def test_agent_runtime_exception_keeps_deterministic_response(self) -> None:
        def raising_agent_factory():
            raise RuntimeError("RAW MODEL FAILURE MUST NOT LEAK")

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Explique simplement ce concept.",
            client_factory=_raising_client_factory,
            config_module=_agent_config("shadow"),
            librarian_agent_factory=raising_agent_factory,
        )
        encoded = json.dumps(result.observability_payload, ensure_ascii=False, sort_keys=True)

        self.assertFalse(result.used)
        self.assertIsNone(result.prompt_message)
        self.assertEqual(result.observability_payload["librarian_agent"]["status"], "fallback_deterministic")
        self.assertFalse(result.observability_payload["librarian_agent"]["used_for_response"])
        self.assertNotIn("RAW MODEL FAILURE MUST NOT LEAK", encoded)

    def test_non_used_turn_with_existing_state_does_not_reattach_current_user_message(self) -> None:
        state, _transition = conversation_state.update_state_from_runtime(
            conversation_state.BiblioConversationState.empty(conversation_id="conv-biblio-state"),
            query_plan=query_planner.BiblioQueryPlan(
                should_consult=True,
                intent=query_planner.INTENT_SEARCH_CATALOG,
                reason_code=query_planner.REASON_SEARCH_CATALOG,
                query_kind=query_planner.INTENT_SEARCH_CATALOG,
            ),
            library_result=_RuntimeResult(passage_result=_passage(RAW_PASSAGE), status="extracted"),
            conversation_id="conv-biblio-state",
            now_iso="2026-05-31T12:00:00Z",
        )
        conversation = {
            "id": "conv-biblio-state",
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "ancienne demande", "meta": {"biblio_state": state.to_dict()}},
                {"role": "assistant", "content": "ancienne reponse"},
                {"role": "user", "content": "Explique simplement ce concept."},
            ],
        }

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Explique simplement ce concept.",
            conversation_id="conv-biblio-state",
            conversation_state=chat_runtime.read_biblio_conversation_state(conversation),
            client_factory=_raising_client_factory,
        )
        attached = chat_runtime.attach_biblio_conversation_state(conversation, result)

        self.assertFalse(result.used)
        self.assertFalse(attached)
        self.assertNotIn("meta", conversation["messages"][-1])

    def test_followup_without_biblio_state_clarifies_without_catalogue_call(self) -> None:
        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="continue apres ce passage",
            conversation_id="conv-biblio-state",
            client_factory=_raising_client_factory,
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "page_read")
        self.assertEqual(result.reason_code, chat_runtime.librarian_dialogue_planner.REASON_CURRENT_DOCUMENT_MISSING)
        self.assertIsNotNone(result.prompt_message)
        self.assertIn("Navigation documentaire demandee", result.prompt_message["content"])
        self.assertEqual(result.observability_payload["status"], "needs_clarification")
        self.assertEqual(result.observability_payload["client"]["event_count"], 0)

    def test_extracted_passage_updates_and_attaches_content_free_state(self) -> None:
        observed: dict[str, object] = {}
        conversation = {
            "id": "conv-biblio-state",
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "RAW USER QUERY MUST NOT ENTER STATE"},
            ],
        }

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Cherche le passage 126b dans Platon dans le catalogue.",
            conversation_id="conv-biblio-state",
            now_iso="2026-05-31T12:00:00Z",
            client_factory=lambda **_kwargs: _FakeClient(),
            extractor_factory=lambda client: _FakeExtractor(observed),
        )
        attached = chat_runtime.attach_biblio_conversation_state(conversation, result)
        loaded = chat_runtime.read_biblio_conversation_state(conversation)

        self.assertTrue(attached)
        self.assertTrue(loaded.present)
        self.assertEqual(loaded.page_no, 12)
        self.assertEqual(loaded.para_no, 3)
        self.assertEqual(loaded.paragraph_id, 99)
        self.assertEqual(len(loaded.last_passage_hash), 12)
        encoded_state = json.dumps(loaded.to_dict(), ensure_ascii=False, sort_keys=True)
        self.assertNotIn(RAW_PASSAGE, encoded_state)
        self.assertNotIn("RAW USER QUERY MUST NOT ENTER STATE", encoded_state)
        self.assertNotIn("payload", encoded_state.lower())
        self.assertEqual(result.observability_payload["state"]["last_result_present"], True)

    def test_previous_page_with_state_reads_previous_page(self) -> None:
        state, _transition = conversation_state.update_state_from_runtime(
            conversation_state.BiblioConversationState.empty(conversation_id="conv-biblio-state"),
            query_plan=query_planner.BiblioQueryPlan(
                should_consult=True,
                intent=query_planner.INTENT_SEARCH_CATALOG,
                reason_code=query_planner.REASON_SEARCH_CATALOG,
                query_kind=query_planner.INTENT_SEARCH_CATALOG,
            ),
            library_result=_RuntimeResult(passage_result=_passage(RAW_PASSAGE), status="extracted"),
            conversation_id="conv-biblio-state",
            now_iso="2026-05-31T12:00:00Z",
        )

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="montre-moi la page precedente",
            conversation_id="conv-biblio-state",
            conversation_state=state,
            client_factory=lambda **_kwargs: _FakeClient(),
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "page_read")
        self.assertEqual(result.reason_code, chat_runtime.librarian_dialogue_planner.REASON_NAVIGATION_PAGE_READ)
        self.assertIn("Page consultee", result.prompt_message["content"])
        self.assertEqual(result.observability_payload["client"]["event_count"], 1)
        self.assertEqual(result.observability_payload["client"]["items"][0]["endpoint_kind"], "page")

    def test_next_page_with_state_reads_next_page(self) -> None:
        state, _transition = conversation_state.update_state_from_runtime(
            conversation_state.BiblioConversationState.empty(conversation_id="conv-biblio-state"),
            query_plan=query_planner.BiblioQueryPlan(
                should_consult=True,
                intent=query_planner.INTENT_SEARCH_CATALOG,
                reason_code=query_planner.REASON_SEARCH_CATALOG,
                query_kind=query_planner.INTENT_SEARCH_CATALOG,
            ),
            library_result=_RuntimeResult(passage_result=_passage(RAW_PASSAGE), status="extracted"),
            conversation_id="conv-biblio-state",
            now_iso="2026-05-31T12:00:00Z",
        )

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="montre-moi la page suivante",
            conversation_id="conv-biblio-state",
            conversation_state=state,
            client_factory=lambda **_kwargs: _FakeClient(),
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "page_read")
        self.assertEqual(result.reason_code, chat_runtime.librarian_dialogue_planner.REASON_NAVIGATION_PAGE_READ)
        self.assertIn("Page consultee", result.prompt_message["content"])
        self.assertEqual(result.observability_payload["client"]["event_count"], 1)
        self.assertEqual(result.observability_payload["client"]["items"][0]["endpoint_kind"], "page")

    def test_explicit_page_range_with_current_document_reads_bounded_pages(self) -> None:
        state = conversation_state.BiblioConversationState(
            conversation_id="conv-biblio-state",
            current_document={"document_id": "doc-1234", "doc_id_short": "doc-1234"},
            page_no=12,
        )

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="page 28 a page 32",
            conversation_id="conv-biblio-state",
            conversation_state=state,
            client_factory=lambda **_kwargs: _FakeClient(),
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "page_read")
        self.assertEqual(result.observability_payload["client"]["event_count"], 5)
        self.assertEqual(
            [item["endpoint_kind"] for item in result.observability_payload["client"]["items"]],
            ["page", "page", "page", "page", "page"],
        )
        self.assertIn("Page consultee", result.prompt_message["content"])

    def test_explicit_page_range_with_named_document_reads_bounded_pages(self) -> None:
        fake = _NamedDocumentPageClient({"Platon": "doc-1234"})

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Dans Platon, page 28 a page 32",
            client_factory=lambda **_kwargs: fake,
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "page_read")
        self.assertEqual(result.reason_code, chat_runtime.librarian_dialogue_planner.REASON_NAVIGATION_PAGE_READ)
        self.assertEqual(result.observability_payload["client"]["event_count"], 5)
        self.assertEqual(
            [item["endpoint_kind"] for item in result.observability_payload["client"]["items"]],
            ["page", "page", "page", "page", "page"],
        )
        self.assertIn("Page consultee", result.prompt_message["content"])

    def test_named_previous_page_uses_matching_document_anchor(self) -> None:
        fake = _NamedDocumentPageClient({"Platon": "doc-1234"})
        state = conversation_state.BiblioConversationState(
            conversation_id="conv-biblio-state",
            current_document={"document_id": "doc-1234", "doc_id_short": "doc-1234"},
            last_result={"document_id": "doc-1234", "page_no": 12, "para_no": 3},
            page_no=12,
            para_no=3,
        )

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Dans Platon, page precedente",
            conversation_id="conv-biblio-state",
            conversation_state=state,
            client_factory=lambda **_kwargs: fake,
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "page_read")
        self.assertEqual(result.reason_code, chat_runtime.librarian_dialogue_planner.REASON_NAVIGATION_PAGE_READ)
        self.assertEqual(result.observability_payload["client"]["event_count"], 1)
        self.assertEqual(result.observability_payload["client"]["items"][0]["endpoint_kind"], "page")
        self.assertIn("Page consultee", result.prompt_message["content"])

    def test_named_previous_page_does_not_reuse_other_document_anchor(self) -> None:
        fake = _NamedDocumentPageClient({"Platon": "doc-1234"})
        state = conversation_state.BiblioConversationState(
            conversation_id="conv-biblio-state",
            current_document={"document_id": "doc-other", "doc_id_short": "doc-other"},
            last_result={"document_id": "doc-other", "page_no": 12, "para_no": 3},
            page_no=12,
            para_no=3,
        )

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Dans Platon, page precedente",
            conversation_id="conv-biblio-state",
            conversation_state=state,
            client_factory=lambda **_kwargs: fake,
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "page_read")
        self.assertEqual(result.reason_code, chat_runtime.librarian_dialogue_planner.REASON_NAVIGATION_PAGE_ANCHOR_MISSING)
        self.assertEqual(result.observability_payload["status"], "needs_clarification")
        self.assertEqual(result.observability_payload["client"]["event_count"], 0)

    def test_named_internal_work_without_document_page_mapping_stays_clarification(self) -> None:
        fake = _NamedDocumentPageClient({"Platon": "doc-1234"})

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Dans le Theetete, page 28 a 32",
            client_factory=lambda **_kwargs: fake,
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "page_read")
        self.assertEqual(
            result.reason_code,
            chat_runtime.librarian_dialogue_planner.REASON_NAVIGATION_EXPLICIT_REFERENCE_UNRESOLVED,
        )
        self.assertEqual(result.observability_payload["status"], "needs_clarification")
        self.assertEqual(result.observability_payload["client"]["event_count"], 0)

    def test_around_this_passage_executes_bounded_context_navigation(self) -> None:
        state = conversation_state.BiblioConversationState(
            conversation_id="conv-biblio-state",
            current_document={"document_id": "doc-1234", "doc_id_short": "doc-1234"},
            last_result={"document_id": "doc-1234", "paragraph_id": 101, "page_no": 12, "para_no": 3},
            page_no=12,
            para_no=3,
            paragraph_id=101,
        )

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="autour de ce passage",
            conversation_id="conv-biblio-state",
            conversation_state=state,
            client_factory=lambda **_kwargs: _FakeClient(),
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "passage_context")
        self.assertEqual(result.reason_code, chat_runtime.librarian_dialogue_planner.REASON_NAVIGATION_CONTEXT_AROUND)
        self.assertEqual(result.observability_payload["client"]["event_count"], 1)
        self.assertEqual(result.observability_payload["client"]["items"][0]["endpoint_kind"], "context")
        self.assertIn("Contexte consulte", result.prompt_message["content"])

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

    def test_catalogue_list_request_fetches_complete_reasonable_catalogue(self) -> None:
        fake = _CatalogListClient(total=10)

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Et tu peux me dire ce que tu as comme ouvrages dans la bibliothèque ? Tu peux les lister ?",
            client_factory=lambda **_kwargs: fake,
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "list_catalog")
        self.assertEqual(fake.calls, [("catalog", None, 100, 0)])
        self.assertIsNotNone(result.prompt_message)
        self.assertIn("Catalogue disponible: 10 ouvrages. Liste complete affichee.", result.prompt_message["content"])
        self.assertIn("10.", result.prompt_message["content"])
        self.assertEqual(result.observability_payload["status"], "listed")
        self.assertEqual(result.observability_payload["lane"]["total_count"], 10)
        self.assertEqual(result.observability_payload["lane"]["displayed_count"], 10)
        self.assertFalse(result.observability_payload["lane"]["truncated"])

        encoded_observability = json.dumps(result.observability_payload, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("RAW CATALOG TITLE", encoded_observability)
        self.assertNotIn("RAW CATALOG AUTHOR", encoded_observability)

    def test_catalogue_list_request_is_explicitly_paginated_above_reasonable_limit(self) -> None:
        fake = _CatalogListClient(total=125)

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="C'est tout ?",
            client_factory=lambda **_kwargs: fake,
        )

        self.assertTrue(result.used)
        self.assertEqual(fake.calls, [("catalog", None, 100, 0)])
        self.assertIsNotNone(result.prompt_message)
        self.assertIn("Catalogue disponible: 125 ouvrages. Affichage des 100 premiers", result.prompt_message["content"])
        self.assertEqual(result.observability_payload["lane"]["total_count"], 125)
        self.assertEqual(result.observability_payload["lane"]["displayed_count"], 100)
        self.assertTrue(result.observability_payload["lane"]["truncated"])

    def test_table_of_contents_request_lists_chapters_when_lightweight_overview_is_available(self) -> None:
        fake = _TableOfContentsClient()

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Table des matières des éditions complètes de Platon dans la bibliothèque",
            client_factory=lambda **_kwargs: fake,
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "show_table_of_contents")
        self.assertEqual(fake.calls[0], ("catalog", "Platon", 8, 0))
        self.assertEqual(fake.calls[1], ("chapters", "doc-toc", 500, 0))
        self.assertEqual(result.observability_payload["status"], "toc_listed")
        self.assertEqual(result.observability_payload["client"]["event_count"], 2)
        self.assertIsNotNone(result.prompt_message)
        self.assertIn("Table des matieres disponible: 2 entrees. Liste complete affichee.", result.prompt_message["content"])
        self.assertIn("RAW CHAPTER TITLE ONE", result.prompt_message["content"])

        encoded_observability = json.dumps(result.observability_payload, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("RAW CHAPTER TITLE ONE", encoded_observability)
        self.assertNotIn("RAW DOCUMENT TITLE", encoded_observability)

    def test_table_of_contents_can_reuse_current_document_state_without_renaming_work(self) -> None:
        fake = _TableOfContentsClient()
        opened = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Ouvre Platon dans la bibliothèque",
            conversation_id="conv-biblio-state",
            client_factory=lambda **_kwargs: fake,
        )

        self.assertTrue(opened.biblio_state.current_document.get("document_id"))

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Donne-moi la table des matières",
            conversation_id="conv-biblio-state",
            conversation_state=opened.biblio_state,
            client_factory=lambda **_kwargs: fake,
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "show_table_of_contents")
        self.assertEqual(fake.calls, [("catalog", "Platon", 8, 0), ("chapters", "doc-toc", 500, 0)])
        self.assertEqual(result.observability_payload["status"], "toc_listed")
        self.assertIsNotNone(result.prompt_message)
        self.assertIn("Table des matieres disponible: 2 entrees.", result.prompt_message["content"])

    def test_table_of_contents_request_reports_platform_gap_for_large_document_without_document_route_call(self) -> None:
        fake = _LargeTableOfContentsClient()

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="T'arrives à trouver la table des matières des éditions complètes de Platon que tu as dans la bibliothèque ?",
            client_factory=lambda **_kwargs: fake,
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "show_table_of_contents")
        self.assertEqual(fake.calls, [("catalog", "Platon", 8, 0), ("chapters", "doc-large", 500, 0)])
        self.assertEqual(result.observability_payload["status"], "toc_listed")
        self.assertEqual(result.reason_code, "biblio_table_of_contents_listed")
        self.assertIsNotNone(result.prompt_message)
        self.assertIn("Table des matieres disponible: 10 entrees. Liste complete affichee.", result.prompt_message["content"])

        encoded_observability = json.dumps(result.observability_payload, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("RAW DOCUMENT TITLE", encoded_observability)
        self.assertNotIn("RAW CHAPTER TITLE ONE", encoded_observability)

    def test_internal_work_table_of_contents_request_focuses_matching_volume_entry(self) -> None:
        fake = _InternalWorkTableOfContentsClient()

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Sommaire du Théétète de Platon",
            client_factory=lambda **_kwargs: fake,
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "show_table_of_contents")
        self.assertEqual(fake.calls, [("catalog", "Platon", 8, 0), ("chapters", "doc-toc", 500, 0)])
        self.assertEqual(result.observability_payload["status"], "toc_listed")
        self.assertEqual(result.reason_code, "biblio_table_of_contents_listed")
        self.assertIsNotNone(result.prompt_message)
        self.assertIn(
            "Affichage des 1 entrees correspondant a l'oeuvre interne.",
            result.prompt_message["content"],
        )
        self.assertIn("RAW WORK CHAPTER TITLE THÉÉTÈTE", result.prompt_message["content"])
        self.assertNotIn("RAW INTRO CHAPTER TITLE", result.prompt_message["content"])

        encoded_observability = json.dumps(result.observability_payload, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("RAW WORK CHAPTER TITLE THÉÉTÈTE", encoded_observability)
        self.assertNotIn("RAW DOCUMENT TITLE", encoded_observability)

    def test_open_document_request_returns_catalogue_summary_without_raw_observability(self) -> None:
        fake = _TableOfContentsClient()

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Ouvre Platon dans la bibliothèque",
            client_factory=lambda **_kwargs: fake,
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "open_document")
        self.assertEqual(result.observability_payload["status"], "opened")
        self.assertIsNotNone(result.prompt_message)
        self.assertIn("Document Catalogue trouve:", result.prompt_message["content"])
        self.assertEqual(fake.calls, [("catalog", "Platon", 8, 0)])

        encoded_observability = json.dumps(result.observability_payload, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("RAW DOCUMENT TITLE", encoded_observability)

    def test_library_runtime_list_catalog_retains_only_endpoint_observations(self) -> None:
        plan = query_planner.plan_biblio_query("Tu peux chercher et voir les premiers ouvrages ?")

        result = library_runtime.run_biblio_library_plan(_FakeClient(), plan)

        self.assertEqual(result.status, library_runtime.STATUS_LISTED)
        self.assertTrue(result.endpoint_observations)
        self.assertFalse(hasattr(result, "client_responses"))
        self.assertFalse(any(hasattr(item, "payload") for item in result.endpoint_observations))

    def test_unaccented_thematic_search_uses_context_and_builds_passage_lane(self) -> None:
        fake = _AccentSensitiveSearchClient()

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Cherche maieutique dans la bibliotheque",
            client_factory=lambda **_kwargs: fake,
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "search_catalog")
        self.assertEqual(result.observability_payload["status"], "extracted")
        self.assertIsNotNone(result.context_result)
        self.assertIsNotNone(result.passage_result)
        self.assertIsNotNone(result.prompt_message)
        self.assertIn(prompt_lane.LANE_HEADER, result.prompt_message["content"])
        self.assertIn("Niveau de resolution: approximation contextuelle.", result.prompt_message["content"])
        self.assertIn("Approximation contextuelle 1", result.prompt_message["content"])
        self.assertNotIn("[CONSULTATION DE BIBLIOTHEQUE]", result.prompt_message["content"])
        self.assertIn(RAW_PASSAGE, result.prompt_message["content"])
        self.assertEqual(result.observability_payload["counts"]["passage_count"], 1)
        self.assertEqual(result.observability_payload["lane"]["product_truth"], "contextual_approximation")
        self.assertIn(("search", "maïeutique"), fake.calls)
        self.assertTrue(any(call[0] == "context" for call in fake.calls))

        encoded_observability = json.dumps(result.observability_payload, ensure_ascii=False, sort_keys=True)
        self.assertNotIn(RAW_PASSAGE, encoded_observability)
        self.assertNotIn("RAW SEARCH TEXT MUST NOT BE OBSERVABLE", encoded_observability)
        self.assertNotIn("RAW TITLE MUST STAY INTERNAL", encoded_observability)

    def test_library_runtime_search_catalog_retains_only_endpoint_observations(self) -> None:
        plan = query_planner.plan_biblio_query("Cherche maieutique dans la bibliotheque")
        fake = _AccentSensitiveSearchClient()

        result = library_runtime.run_biblio_library_plan(fake, plan)
        encoded = json.dumps(result.client_observability(), ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, "extracted")
        self.assertIsNotNone(result.context_result)
        self.assertIsNotNone(result.prompt_lane)
        self.assertTrue(result.endpoint_observations)
        self.assertFalse(hasattr(result, "client_responses"))
        self.assertFalse(any(hasattr(item, "payload") for item in result.endpoint_observations))
        self.assertFalse(any(hasattr(item, "payload") for item in result.context_result.context_observations))
        self.assertFalse(
            any(hasattr(item, "payload") for item in result.context_result.candidate_result.endpoint_observations)
        )
        self.assertNotIn("RAW TITLE MUST STAY INTERNAL", encoded)
        self.assertNotIn("RAW SEARCH TEXT MUST NOT BE OBSERVABLE", encoded)
        self.assertNotIn(RAW_PASSAGE, encoded)
        self.assertNotIn("payload", encoded)

    def test_thematic_search_repro_phrasings_build_passage_lane(self) -> None:
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
                self.assertEqual(result.observability_payload["status"], "extracted")
                self.assertNotEqual(result.reason_code, "locator_required_for_passage")
                self.assertIsNotNone(result.context_result)
                self.assertIsNotNone(result.passage_result)
                self.assertIsNotNone(result.prompt_message)
                self.assertIn(prompt_lane.LANE_HEADER, result.prompt_message["content"])
                self.assertNotIn("[CONSULTATION DE BIBLIOTHEQUE]", result.prompt_message["content"])
                self.assertIn(("search", "maïeutique"), fake.calls)
                self.assertTrue(any(call[0] == "context" for call in fake.calls))

    def test_ambiguous_thematic_search_builds_bounded_candidate_passage_lane(self) -> None:
        fake = _AmbiguousThematicSearchClient()

        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Cherche maïeutique dans la bibliothèque",
            client_factory=lambda **_kwargs: fake,
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "search_catalog")
        self.assertEqual(result.observability_payload["status"], "ambiguous")
        self.assertIsNotNone(result.context_result)
        self.assertIsNone(result.passage_result)
        self.assertIsNotNone(result.prompt_message)
        self.assertIn(prompt_lane.LANE_HEADER, result.prompt_message["content"])
        self.assertIn("Niveau de resolution: candidat plausible.", result.prompt_message["content"])
        self.assertIn("Passage candidat 1", result.prompt_message["content"])
        self.assertIn("Passage candidat 2", result.prompt_message["content"])
        self.assertEqual(result.observability_payload["counts"]["passage_count"], 2)
        self.assertEqual(result.observability_payload["lane"]["product_truth"], "plausible_candidate")
        self.assertEqual(result.context_result.to_observability()["selected_count"], 0)
        self.assertTrue(any(call[0] == "context" for call in fake.calls))

        encoded_observability = json.dumps(result.observability_payload, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("RAW AMBIGUOUS PASSAGE A", encoded_observability)
        self.assertNotIn("RAW AMBIGUOUS PASSAGE B", encoded_observability)
        self.assertNotIn("RAW TITLE MUST STAY INTERNAL", encoded_observability)
        self.assertNotIn("RAW SEARCH TEXT MUST NOT BE OBSERVABLE", encoded_observability)
        self.assertTrue(result.biblio_state.last_ambiguity)
        self.assertGreaterEqual(result.biblio_state.last_ambiguity["candidate_count"], 2)

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
        self.assertEqual(request.resolve_request.document_title, "Platon")
        self.assertEqual(request.resolve_request.work_title, "Théétète")
        self.assertEqual(request.resolve_request.locator, "126b")
        self.assertEqual(request.resolve_request.locator_end, "128a")
        self.assertEqual(request.resolve_request.locator_anchor_page, 131)
        self.assertNotEqual(result.reason_code, chat_runtime.REASON_NO_BIBLIOGRAPHIC_SIGNAL)

    def test_bare_work_and_corpus_request_returns_documentary_resolution_without_forcing_passage(self) -> None:
        result = chat_runtime.run_biblio_chat_turn(
            {"biblio_enabled": True},
            user_msg="Trouve-moi le Theetete de Platon.",
            client_factory=lambda **_kwargs: _FakeClient(),
        )

        self.assertTrue(result.used)
        self.assertEqual(result.query_kind, "resolve_work")
        self.assertEqual(result.observability_payload["status"], "resolved")
        self.assertIsNone(result.passage_result)
        self.assertIsNone(result.context_result)
        self.assertIsNotNone(result.prompt_message)
        self.assertIn("[CONSULTATION DE BIBLIOTHEQUE]", result.prompt_message["content"])
        self.assertIn("Cible documentaire: oeuvre interne dans document/corpus", result.prompt_message["content"])
        self.assertIn("Resolution documentaire effectuee.", result.prompt_message["content"])
        self.assertIn("Aucun passage exact n'a ete extrait", result.prompt_message["content"])
        self.assertTrue(result.biblio_state.current_document.get("document_id"))
        self.assertTrue(result.biblio_state.current_work)

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

    def chapters(self, doc_id: str, *, limit: int = 500, offset: int = 0) -> catalogue.CatalogueResponse:
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CHAPTERS,
            status_code=200,
            payload={
                "document_id": doc_id,
                "total": 2,
                "limit": limit,
                "offset": offset,
                "count": 2,
                "truncated": False,
                "chapters": [
                    {
                        "chapter_no": 1,
                        "title": "RAW CHAPTER TITLE MUST STAY INTERNAL",
                        "unit_no": 1,
                        "source": "toc",
                    },
                    {
                        "chapter_no": 2,
                        "title": "Théétète",
                        "unit_no": 2,
                        "source": "toc",
                    },
                ],
            },
            duration_ms=1,
            result_count=2,
            doc_id_short=catalogue.short_doc_id(doc_id),
        )

    def page(self, doc_id: str, page_no: int) -> catalogue.CatalogueResponse:
        text = f"RAW PAGE {page_no} TEXT MUST NOT BE OBSERVABLE"
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_PAGE,
            status_code=200,
            payload={
                "document_id": doc_id,
                "title": "Internal work carrier",
                "page_no": page_no,
                "raw_text": text,
                "paragraph_count": 4,
                "paragraphs": [
                    {"para_no": 1, "text": f"RAW PAGE {page_no} PARA 1"},
                    {"para_no": 2, "text": f"RAW PAGE {page_no} PARA 2"},
                    {"para_no": 3, "text": f"RAW PAGE {page_no} PARA 3"},
                    {"para_no": 4, "text": f"RAW PAGE {page_no} PARA 4"},
                ],
            },
            duration_ms=1,
            result_count=1,
            doc_id_short=catalogue.short_doc_id(doc_id),
            content_chars=len(text),
        )

    def context(
        self,
        doc_id: str,
        *,
        page_no: int | None = None,
        para_no: int | None = None,
        paragraph_id: int | None = None,
        char_offset: int = 0,
        window_chars: int = 700,
    ) -> catalogue.CatalogueResponse:
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CONTEXT,
            status_code=200,
            payload={"document_id": doc_id, "text": "RAW CONTEXT TEXT MUST NOT BE OBSERVABLE"},
            duration_ms=1,
            result_count=1,
            doc_id_short=catalogue.short_doc_id(doc_id),
            content_chars=len("RAW CONTEXT TEXT MUST NOT BE OBSERVABLE"),
        )

    def metadata(self, doc_id: str) -> catalogue.CatalogueResponse:
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_METADATA,
            status_code=200,
            payload={
                "document_id": doc_id,
                "title": "Internal work carrier",
                "human_canonical_title": "Internal work carrier",
                "human_authors": "Platon",
            },
            duration_ms=1,
            result_count=1,
            doc_id_short=catalogue.short_doc_id(doc_id),
        )


class _NamedDocumentPageClient(_FakeClient):
    def __init__(self, documents: dict[str, str]) -> None:
        self._documents = dict(documents)

    def catalog(self, *, q: str | None = None, limit: int = 100, offset: int = 0) -> catalogue.CatalogueResponse:
        doc_id = self._documents.get(str(q or ""))
        items = []
        if doc_id:
            items.append(
                {
                    "id": doc_id,
                    "title": str(q or ""),
                    "human_canonical_title": str(q or ""),
                    "human_authors": "",
                }
            )
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CATALOG,
            status_code=200,
            payload={"total": len(items), "items": items},
            duration_ms=1,
            result_count=len(items),
        )


class _CatalogListClient:
    def __init__(self, *, total: int) -> None:
        self.total = total
        self.calls: list[tuple[object, ...]] = []

    def catalog(self, *, q: str | None = None, limit: int = 100, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("catalog", q, limit, offset))
        count = min(limit, self.total)
        items = [
            {
                "id": f"doc-{index:04d}",
                "title": f"RAW CATALOG TITLE {index}",
                "human_canonical_title": f"RAW CATALOG TITLE {index}",
                "human_authors": f"RAW CATALOG AUTHOR {index}",
                "page_count": 10 + index,
                "paragraph_count": 100 + index,
                "chapter_count": index,
                "toc_source": "synthetic" if index else "none",
            }
            for index in range(1, count + 1)
        ]
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CATALOG,
            status_code=200,
            payload={"total": self.total, "count": len(items), "items": items},
            duration_ms=1,
            result_count=len(items),
        )


class _TableOfContentsClient:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def catalog(self, *, q: str | None = None, limit: int = 100, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("catalog", q, limit, offset))
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CATALOG,
            status_code=200,
            payload={
                "total": 1,
                "count": 1,
                "items": [
                    {
                        "id": "doc-toc",
                        "title": "RAW DOCUMENT TITLE",
                        "human_canonical_title": "RAW DOCUMENT TITLE",
                        "human_authors": "RAW DOCUMENT AUTHOR",
                        "page_count": 42,
                        "paragraph_count": 400,
                        "chapter_count": 2,
                        "toc_source": "synthetic",
                    }
                ],
            },
            duration_ms=1,
            result_count=1,
        )

    def chapters(self, doc_id: str, *, limit: int = 500, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("chapters", doc_id, limit, offset))
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CHAPTERS,
            status_code=200,
            payload={
                "document": {"id": doc_id, "toc_source": "synthetic"},
                "total": 2,
                "limit": limit,
                "offset": offset,
                "count": 2,
                "truncated": False,
                "chapters": [
                    {"chapter_no": 1, "title": "RAW CHAPTER TITLE ONE", "unit_no": 1, "source": "synthetic"},
                    {"chapter_no": 2, "title": "RAW CHAPTER TITLE TWO", "unit_no": 2, "source": "synthetic"},
                ],
            },
            duration_ms=1,
            result_count=1,
            doc_id_short=doc_id[:8],
        )


class _LargeTableOfContentsClient(_TableOfContentsClient):
    def catalog(self, *, q: str | None = None, limit: int = 100, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("catalog", q, limit, offset))
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CATALOG,
            status_code=200,
            payload={
                "total": 1,
                "count": 1,
                "items": [
                    {
                        "id": "doc-large",
                        "title": "RAW DOCUMENT TITLE",
                        "human_canonical_title": "RAW DOCUMENT TITLE",
                        "human_authors": "RAW DOCUMENT AUTHOR",
                        "page_count": 252,
                        "paragraph_count": 41_482,
                        "chapter_count": 10,
                        "toc_source": "synthetic",
                    }
                ],
            },
            duration_ms=1,
            result_count=1,
        )

    def chapters(self, doc_id: str, *, limit: int = 500, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("chapters", doc_id, limit, offset))
        chapters = [
            {"chapter_no": index, "title": f"RAW CHAPTER TITLE {index}", "unit_no": index, "source": "synthetic"}
            for index in range(1, 11)
        ]
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CHAPTERS,
            status_code=200,
            payload={
                "document": {"id": doc_id, "toc_source": "synthetic"},
                "total": len(chapters),
                "limit": limit,
                "offset": offset,
                "count": len(chapters),
                "truncated": False,
                "chapters": chapters,
            },
            duration_ms=1,
            result_count=len(chapters),
            doc_id_short=doc_id[:8],
        )


class _InternalWorkTableOfContentsClient(_TableOfContentsClient):
    def chapters(self, doc_id: str, *, limit: int = 500, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("chapters", doc_id, limit, offset))
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CHAPTERS,
            status_code=200,
            payload={
                "document": {"id": doc_id, "toc_source": "synthetic"},
                "total": 3,
                "limit": limit,
                "offset": offset,
                "count": 3,
                "truncated": False,
                "chapters": [
                    {
                        "chapter_no": 1,
                        "title": "RAW INTRO CHAPTER TITLE",
                        "unit_no": 1,
                        "source": "synthetic",
                        "document_role_signal": "introduction",
                        "document_role_signal_source": "chapter_title",
                        "document_role_signal_strength": "weak",
                    },
                    {"chapter_no": 2, "title": "RAW WORK CHAPTER TITLE THÉÉTÈTE", "unit_no": 2, "source": "synthetic"},
                    {"chapter_no": 3, "title": "RAW OTHER CHAPTER TITLE", "unit_no": 3, "source": "synthetic"},
                ],
            },
            duration_ms=1,
            result_count=3,
            doc_id_short=doc_id[:8],
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

    def context(
        self,
        doc_id: str,
        *,
        page_no: int | None = None,
        para_no: int | None = None,
        paragraph_id: int | None = None,
        char_offset: int = 0,
        window_chars: int = 700,
    ) -> catalogue.CatalogueResponse:
        self.calls.append(("context", doc_id, str(paragraph_id or ""), str(page_no or ""), str(para_no or "")))
        passage = RAW_PASSAGE
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CONTEXT,
            status_code=200,
            payload={
                "document_id": doc_id,
                "page_no": page_no,
                "para_no": para_no,
                "paragraph_id": paragraph_id,
                "excerpt": passage,
                "excerpt_start": 0,
                "excerpt_end": len(passage),
                "text_length": len(passage),
                "title": "RAW TITLE MUST STAY INTERNAL",
            },
            duration_ms=1,
            result_count=1,
            doc_id_short=doc_id[:8],
            content_chars=len(passage),
        )


class _AmbiguousThematicSearchClient(_AccentSensitiveSearchClient):
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
                    "rank": 0.3,
                    "text": "RAW SEARCH TEXT MUST NOT BE OBSERVABLE",
                },
                {
                    "document_id": "doc-5678",
                    "title": "RAW TITLE MUST STAY INTERNAL",
                    "page_no": 5,
                    "para_no": 27,
                    "rank": 0.3,
                    "text": "RAW SEARCH TEXT MUST NOT BE OBSERVABLE",
                },
            ]
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            status_code=200,
            payload={"count": len(rows), "results": rows[:limit]},
            duration_ms=1,
            result_count=len(rows[:limit]),
        )

    def context(
        self,
        doc_id: str,
        *,
        page_no: int | None = None,
        para_no: int | None = None,
        paragraph_id: int | None = None,
        char_offset: int = 0,
        window_chars: int = 700,
    ) -> catalogue.CatalogueResponse:
        self.calls.append(("context", doc_id, str(paragraph_id or ""), str(page_no or ""), str(para_no or "")))
        suffix = "A" if doc_id == "doc-1234" else "B"
        passage = f"RAW AMBIGUOUS PASSAGE {suffix} " + ("x" * 120)
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CONTEXT,
            status_code=200,
            payload={
                "document_id": doc_id,
                "page_no": page_no,
                "para_no": para_no,
                "paragraph_id": paragraph_id,
                "excerpt": passage,
                "excerpt_start": 0,
                "excerpt_end": len(passage),
                "text_length": len(passage),
                "title": "RAW TITLE MUST STAY INTERNAL",
            },
            duration_ms=1,
            result_count=1,
            doc_id_short=doc_id[:8],
            content_chars=len(passage),
        )


class _FakeExtractor:
    def __init__(self, observed: dict[str, object]) -> None:
        self.observed = observed

    def extract(self, request):
        self.observed["request"] = request
        return _passage(RAW_PASSAGE)


class _FakeAgentModel:
    def __init__(
        self,
        content: str = "",
        *,
        response: agent_openrouter.BiblioLibrarianAgentModelResponse | None = None,
    ) -> None:
        self.content = content
        self.response = response
        self.calls = 0
        self.requests: list[agent_contract.BiblioLibrarianAgentRequest] = []

    def complete(self, request, *, settings=None):
        self.calls += 1
        self.requests.append(request)
        if self.response is not None:
            return self.response
        return agent_openrouter.BiblioLibrarianAgentModelResponse(
            status=agent_openrouter.STATUS_OK,
            reason_code=agent_openrouter.REASON_OK,
            content=self.content,
            finish_reason="stop",
            attempt_count=1,
            response_chars=len(self.content),
        )


class _RuntimeResult:
    def __init__(self, *, passage_result=None, status: str) -> None:
        self.status = status
        self.reason_code = f"biblio_{status}"
        self.passage_result = passage_result
        self.context_result = None
        self.passage_results = (passage_result,) if passage_result is not None else ()
        self.consultation_message = None


def _raising_client_factory(**_kwargs):
    raise AssertionError("Catalogue client must not be built")


def _agent_config(mode: str) -> SimpleNamespace:
    return SimpleNamespace(
        BIBLIO_LIBRARIAN_AGENT_MODE=mode,
        BIBLIO_LIBRARIAN_AGENT_MODEL="model/x",
        BIBLIO_LIBRARIAN_AGENT_MAX_RECENT_TURNS=3,
    )


def _valid_agent_json(
    *,
    tool_name: str = librarian_tools.TOOL_CATALOG_LIST,
    params: dict[str, object] | None = None,
    case_id: str | None = None,
    product_method: str | None = None,
) -> str:
    effective_product_method = product_method or _product_method_for_tool(tool_name)
    effective_case_id = (
        case_id if case_id is not None else librarian_product_methods.default_case_id_for_method(effective_product_method)
    )
    return json.dumps(
        {
            "schema_version": agent_contract.SCHEMA_VERSION,
            "case_id": effective_case_id,
            "intent": "list_catalog",
            "product_method": effective_product_method,
            "tool_calls": [
                {
                    "tool_name": tool_name,
                    "method": "GET",
                    "params": dict(params or {"limit": 10}),
                }
            ],
            "answer_mode": "tool",
            "risk_flags": [],
            "fallback_reason": "",
        },
        ensure_ascii=False,
    )


def _empty_agent_plan_json() -> str:
    return json.dumps(
        {
            "schema_version": agent_contract.SCHEMA_VERSION,
            "case_id": "",
            "intent": "clarify",
            "product_method": librarian_product_methods.PRODUCT_METHOD_CLARIFY_BIBLIO_REQUEST,
            "tool_calls": [],
            "answer_mode": "clarify",
            "risk_flags": [],
            "fallback_reason": "model_requested_clarification",
        },
        ensure_ascii=False,
    )


def _product_method_for_tool(tool_name: str) -> str:
    mapping = {
        librarian_tools.TOOL_CATALOG_LIST: librarian_product_methods.PRODUCT_METHOD_CATALOG_LIST_BOUNDED,
        librarian_tools.TOOL_CATALOG_SEARCH: librarian_product_methods.PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK,
        librarian_tools.TOOL_DOCUMENT_OPEN_SUMMARY: librarian_product_methods.PRODUCT_METHOD_WORK_LOOKUP,
        librarian_tools.TOOL_DOCUMENT_TOC: librarian_product_methods.PRODUCT_METHOD_DOCUMENT_TOC_SHOW,
        librarian_tools.TOOL_PAGE_READ: librarian_product_methods.PRODUCT_METHOD_PASSAGE_CONTINUE_NEXT_SEGMENT,
        librarian_tools.TOOL_LOCATE: librarian_product_methods.PRODUCT_METHOD_PASSAGE_EXTRACT_CANONICAL_RANGE,
        librarian_tools.TOOL_PASSAGE_CONTEXT: librarian_product_methods.PRODUCT_METHOD_PASSAGE_SHOW_AROUND_CURRENT,
    }
    return mapping.get(tool_name, librarian_product_methods.PRODUCT_METHOD_CATALOG_LIST_BOUNDED)


def _passage(passage: str) -> extractor.BiblioPassageResult:
    document = document_resolver.DocumentCandidate(
        document_id="doc-1234",
        doc_id_short="doc-1234",
        title="Document de test",
    )
    locator = document_resolver.LocatorCandidate(
        document_id="doc-1234",
        doc_id_short="doc-1234",
        kind="stephanus",
        label="126b",
        page_no=12,
        para_no=3,
        paragraph_id=99,
    )
    resolution = document_resolver.BiblioResolutionResult(
        status=document_resolver.STATUS_RESOLVED,
        reason_code=document_resolver.REASON_DOCUMENT_AND_LOCATOR_RESOLVED,
        document=document,
        document_candidates=(document,),
        locator=locator,
        locator_candidates=(locator,),
        requested_locator_kind="stephanus",
        requested_locator="126b",
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


if __name__ == "__main__":
    unittest.main()
