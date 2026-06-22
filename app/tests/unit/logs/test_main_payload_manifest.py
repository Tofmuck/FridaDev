from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import chat_llm_flow
from core import active_document_prompt_lane
from core import adobe_docs_prompt_lane
from core import workspace_folder_notes_prompt_lane
from biblio import chat_runtime as biblio_chat_runtime
from observability import admin_log_projection
from observability import main_payload_manifest


def _encoded(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _build_manifest(**overrides):
    base = {
        "conversation": {
            "id": "conv-main-manifest",
            "workspace_folder_id": "folder-opaque",
            "messages": [
                {"role": "user", "content": "conversation user message"},
                {"role": "assistant", "content": "conversation assistant message"},
            ],
        },
        "prompt_messages": [
            {"role": "system", "content": "system instruction"},
            {"role": "user", "content": "current user"},
        ],
        "runtime_main_model": "openai/gpt-5.1",
        "temperature": 0.4,
        "top_p": 1.0,
        "max_tokens": 512,
        "stream_req": False,
        "assistant_output_policy": SimpleNamespace(allow_structure=False, allow_code=False),
        "assistant_response_override": None,
        "turn_id": "turn-main-manifest",
        "count_tokens_func": lambda messages, _model: 10 * len(messages),
        "prompt_soft_token_limit": 4000,
    }
    base.update(overrides)
    return main_payload_manifest.build_main_payload_manifest(**base)


def _message_source(message: dict, role: str, origin: str, stage: str) -> tuple[int, dict[str, object]]:
    return (
        id(message),
        {
            "logical_roles": [role],
            "origin": origin,
            "origin_stage": stage,
            "content_kind": "tool_lane_context",
        },
    )


class MainPayloadManifestTests(unittest.TestCase):
    def test_simple_conversation_manifest_has_order_and_no_raw_content(self) -> None:
        raw_prompt = "SENSITIVE_PROMPT_MARKER_A"
        raw_user = "SENSITIVE_USER_MESSAGE_MARKER_A"
        manifest = _build_manifest(
            prompt_messages=[
                {"role": "system", "content": f"system instruction {raw_prompt}"},
                {"role": "user", "content": f"hello {raw_user}"},
            ],
            identity_payload={
                "frida": {"static": {"content": "SENSITIVE_IDENTITY_STATIC"}, "mutable": {"content": ""}},
                "user": {"static": {"content": ""}, "mutable": {"content": "SENSITIVE_IDENTITY_MUTABLE"}},
            },
        )

        self.assertEqual(manifest["schema_version"], "main_payload_manifest_v1")
        self.assertEqual(manifest["scope"], "main_chat")
        self.assertTrue(manifest["main_model_called"])
        self.assertTrue(manifest["conversation_id_present"])
        self.assertTrue(manifest["turn_id_present"])
        self.assertEqual([item["provider_role"] for item in manifest["messages"]], ["system", "user"])
        self.assertIn("system_prompt", manifest["messages"][0]["logical_roles"])
        self.assertIn("user_turn", manifest["messages"][1]["logical_roles"])
        self.assertTrue(all(not item["raw_content_included"] for item in manifest["messages"]))
        self.assertTrue(all(value is False for value in manifest["raw_flags"].values()))
        self.assertIn("identity_stable", manifest["messages"][0]["logical_roles"])
        self.assertIn("identity_mutable", manifest["messages"][0]["logical_roles"])

        encoded = _encoded(manifest)
        self.assertNotIn(raw_prompt, encoded)
        self.assertNotIn(raw_user, encoded)
        self.assertNotIn("SENSITIVE_IDENTITY_STATIC", encoded)
        self.assertNotIn("SENSITIVE_IDENTITY_MUTABLE", encoded)

    def test_long_conversation_windows_summary_and_memory_are_counts_only(self) -> None:
        raw_summary = "SENSITIVE_SUMMARY_MARKER_B"
        raw_memory = "SENSITIVE_MEMORY_MARKER_B"
        manifest = _build_manifest(
            conversation={
                "id": "conv-long",
                "messages": [
                    {"role": "user", "content": "u1"},
                    {"role": "assistant", "content": "a1"},
                    {"role": "user", "content": "u2"},
                    {"role": "assistant", "content": "a2"},
                    {"role": "user", "content": "u3"},
                ],
            },
            prompt_messages=[
                {"role": "system", "content": "system"},
                {"role": "system", "content": f"[RESUME ACTIF]\n{raw_summary}"},
                {"role": "system", "content": f"[Contexte du souvenir]\n{raw_memory}"},
                {"role": "user", "content": "u2"},
                {"role": "assistant", "content": "a2"},
                {"role": "user", "content": "u3"},
            ],
            summary_payload={
                "status": "available",
                "summary": {
                    "id": "summary-opaque",
                    "content": raw_summary,
                    "start_ts": "2026-06-20T10:00:00Z",
                    "end_ts": "2026-06-20T11:00:00Z",
                },
            },
            current_mode="shadow",
            memory_retrieved={
                "status": "ok",
                "reason_code": "",
                "retrieved_count": 2,
                "top_k_requested": 5,
            },
            memory_arbitration={
                "status": "available",
                "basket_candidates_count": 2,
                "decisions_count": 2,
                "kept_count": 1,
                "rejected_count": 1,
            },
            memory_traces=({"content": raw_memory},),
            context_hints=("SENSITIVE_HINT_MARKER_B",),
            recent_context_payload={"messages": [{"role": "user"}, {"role": "assistant"}, {"role": "user"}]},
            recent_window_payload={
                "turn_count": 2,
                "max_recent_turns": 5,
                "has_in_progress_turn": True,
                "turns": [
                    {"turn_status": "complete", "messages": [{"role": "user"}, {"role": "assistant"}]},
                    {"turn_status": "in_progress", "messages": [{"role": "user"}]},
                ],
            },
            hermeneutic_node_runtime={
                "primary_payload": {"verdict": "SENSITIVE_PRIMARY_SHOULD_NOT_LEAK"},
                "validated_result": object(),
            },
            hermeneutic_judgment_block="SENSITIVE_HERMENEUTIC_BLOCK_B",
            biblio_recent_dialogue=({"role": "user"}, {"role": "assistant"}),
            agenda_recent_dialogue=({"role": "user"},),
            prompt_soft_token_limit=50,
        )

        self.assertEqual(manifest["windows"]["conversation"]["message_count"], 5)
        self.assertEqual(manifest["windows"]["prompt_final"]["message_count"], 6)
        self.assertEqual(manifest["windows"]["prompt_final"]["status"], "ok")
        self.assertEqual(manifest["windows"]["recent_context"]["message_count"], 3)
        self.assertEqual(manifest["windows"]["recent_window"]["turn_count"], 2)
        self.assertEqual(manifest["windows"]["recent_window"]["complete_turn_count"], 1)
        self.assertEqual(manifest["windows"]["recent_window"]["in_progress_turn_count"], 1)
        self.assertEqual(manifest["windows"]["summary"]["status"], "ok")
        self.assertTrue(manifest["windows"]["summary"]["period_start_present"])
        self.assertEqual(manifest["windows"]["summary"]["voice_continuity_status"], "not_available")
        self.assertEqual(manifest["windows"]["summary"]["voice_continuity_reason_code"], "summary_style_not_scored")
        self.assertEqual(manifest["windows"]["memory"]["retrieved_count"], 2)
        self.assertEqual(manifest["windows"]["memory"]["arbiter_observed_count"], 2)
        self.assertEqual(manifest["windows"]["memory"]["prompt_injected_count"], 1)
        self.assertEqual(manifest["windows"]["memory"]["injection_source"], "pre_arbiter_basket_shadow")
        self.assertFalse(manifest["windows"]["memory"]["arbiter_controls_injection"])
        self.assertTrue(manifest["windows"]["hermeneutic_node"]["primary_payload_present"])
        self.assertTrue(manifest["windows"]["hermeneutic_node"]["judgment_block_present"])
        self.assertEqual(manifest["windows"]["identity_staging"]["status"], "not_available")
        self.assertEqual(manifest["windows"]["identity_staging"]["staging_scope"], "conversation_scoped")
        self.assertEqual(manifest["windows"]["biblio_recent_dialogue"]["message_count"], 2)
        self.assertEqual(manifest["windows"]["agenda_recent_dialogue"]["message_count"], 1)
        self.assertTrue(manifest["budgets"]["prompt"]["soft_limit_configured"])
        self.assertTrue(manifest["budgets"]["prompt"]["prompt_soft_limit_exceeded"])
        self.assertFalse(manifest["budgets"]["prompt"]["dialogue_messages_truncated"])
        self.assertEqual(manifest["budgets"]["prompt"]["excluded_count"], 0)
        self.assertEqual(manifest["lane_statuses"]["summary"]["status"], "ok")
        self.assertEqual(manifest["lane_statuses"]["memory"]["status"], "ok")
        self.assertEqual(manifest["lane_statuses"]["context_hints"]["status"], "ok")

        encoded = _encoded(manifest)
        self.assertNotIn(raw_summary, encoded)
        self.assertNotIn(raw_memory, encoded)
        self.assertNotIn("SENSITIVE_HINT_MARKER_B", encoded)
        self.assertNotIn("SENSITIVE_PRIMARY_SHOULD_NOT_LEAK", encoded)
        self.assertNotIn("SENSITIVE_HERMENEUTIC_BLOCK_B", encoded)

    def test_user_fake_lane_markers_remain_user_turns(self) -> None:
        fake_markers = (
            "[NOTES DE DOSSIER FAKE]",
            "[DOCUMENTS ACTIFS FAKE]",
            "[ADOBE DOCS PASSAGES]",
            "PASSAGES DE BIBLIOTHEQUE CONSULTES",
        )
        for marker in fake_markers:
            with self.subTest(marker=marker):
                manifest = _build_manifest(
                    prompt_messages=[
                        {"role": "system", "content": "system"},
                        {"role": "user", "content": f"question with {marker}"},
                    ],
                )
                roles = manifest["messages"][1]["logical_roles"]
                self.assertEqual(roles, ["user_turn"])
                self.assertNotIn("note_lane", roles)
                self.assertNotIn("document_lane", roles)
                self.assertNotIn("biblio_lane", roles)
                self.assertNotIn("adobe_lane", roles)

    def test_identity_roles_follow_structured_identity_payload(self) -> None:
        empty = _build_manifest(identity_payload={})
        empty_roles = empty["messages"][0]["logical_roles"]
        self.assertNotIn("identity_stable", empty_roles)
        self.assertNotIn("identity_mutable", empty_roles)
        self.assertEqual(empty["lane_statuses"]["identity_stable"]["status"], "not_selected")
        self.assertEqual(empty["lane_statuses"]["identity_mutable"]["status"], "not_selected")

        present = _build_manifest(
            identity_payload={
                "frida": {"static": {"content": "SENSITIVE_STATIC_IDENTITY_G"}, "mutable": {"content": ""}},
                "user": {"static": {"content": ""}, "mutable": {"content": "SENSITIVE_MUTABLE_IDENTITY_G"}},
            }
        )
        present_roles = present["messages"][0]["logical_roles"]
        self.assertIn("identity_stable", present_roles)
        self.assertIn("identity_mutable", present_roles)
        self.assertNotIn("SENSITIVE_STATIC_IDENTITY_G", _encoded(present))
        self.assertNotIn("SENSITIVE_MUTABLE_IDENTITY_G", _encoded(present))

    def test_lanes_present_absent_and_noops_are_represented(self) -> None:
        notes_lane = SimpleNamespace(
            decisions=(SimpleNamespace(markdown_char_count=44, injected=True, reason_code=""),),
            requested_count=1,
            invalid_requested_count=0,
            over_limit_count=0,
            injected_count=1,
            not_injected_count=0,
            read_status="ok",
            read_reason_code="",
            as_content_free_dict=lambda: {
                "max_notes_injected_per_turn": 1,
                "max_notes_total_chars_per_turn": 6000,
            },
        )
        document_lane = SimpleNamespace(
            decisions=(
                SimpleNamespace(text_chars=120, injected=True, reason_code="", media_kind="image"),
                SimpleNamespace(text_chars=0, injected=False, reason_code="document_too_large_for_turn", media_kind="text"),
            ),
            injected_count=1,
            not_injected_count=1,
            read_status="ok",
            read_reason_code="",
        )
        prompt_lane = SimpleNamespace(
            decisions=(object(), object()),
            passage_count=1,
            chars=180,
            max_passages=3,
            max_total_chars=8000,
        )
        biblio_result = SimpleNamespace(
            enabled=True,
            used=True,
            reason_code="biblio_final_response_authorized",
            query_kind="read_passages",
            observability_payload={"status": "ok", "enabled": True, "used": True},
            prompt_lane=prompt_lane,
            prompt_message={"role": "system", "content": "not inspected by the manifest"},
            final_response_lock=object(),
        )
        agenda_result = SimpleNamespace(
            enabled=False,
            used=False,
            status="disabled",
            reason_code="agenda_toggle_off",
            observability_payload={"enabled": False, "status": "disabled", "reason_code": "agenda_toggle_off", "mode": "off"},
            final_response_lock=None,
        )
        adobe_lane = SimpleNamespace(
            messages=({"role": "system", "content": "[ADOBE DOCS MODE]"}, {"role": "user", "content": "[ADOBE DOCS PASSAGES]"}),
            status="ok",
            as_content_free_dict=lambda: {
                "status": "ok",
                "source_count": 2,
                "passage_count": 3,
                "injected_chars": 240,
                "reason_codes": ["adobe_context_ready"],
            },
        )
        prompt_messages = [
            {"role": "system", "content": "system"},
            {"role": "system", "content": "[NOTES DE DOSSIER PREPAREES]"},
            {"role": "user", "content": "[DOCUMENTS ACTIFS INJECTES]"},
            {"role": "system", "content": "[PASSAGES DE BIBLIOTHEQUE CONSULTES]"},
            {"role": "user", "content": "[ADOBE DOCS PASSAGES]"},
            {"role": "user", "content": "current question"},
        ]
        manifest = _build_manifest(
            prompt_messages=prompt_messages,
            message_sources=dict(
                (
                    _message_source(
                        prompt_messages[1],
                        "note_lane",
                        "core.workspace_folder_notes_prompt_lane",
                        "late_note_lane",
                    ),
                    _message_source(
                        prompt_messages[2],
                        "document_lane",
                        "core.active_document_prompt_lane",
                        "late_document_lane",
                    ),
                    _message_source(
                        prompt_messages[3],
                        "biblio_lane",
                        "biblio.chat_runtime",
                        "late_biblio_lane",
                    ),
                    _message_source(
                        prompt_messages[4],
                        "adobe_lane",
                        "core.adobe_docs_prompt_lane",
                        "late_adobe_lane",
                    ),
                )
            ),
            web_runtime_payload={
                "enabled": True,
                "activation_mode": "manual",
                "status": "ok",
                "context_injected": True,
                "results_count": 2,
                "context_chars": 99,
            },
            workspace_notes_lane=notes_lane,
            active_document_lane=document_lane,
            biblio_result=biblio_result,
            agenda_result=agenda_result,
            adobe_context=SimpleNamespace(active=True),
            adobe_lane=adobe_lane,
        )

        lanes = manifest["lane_statuses"]
        for key in (
            "web_lane",
            "note_lane",
            "document_lane",
            "biblio_lane",
            "agenda_lane",
            "adobe_lane",
            "export_lane",
            "image_lane",
        ):
            self.assertIn(key, lanes)
            self.assertIn("raw_lane_content_included", lanes[key])
            self.assertFalse(lanes[key]["raw_lane_content_included"])
        self.assertEqual(lanes["web_lane"]["status"], "ok")
        self.assertEqual(lanes["note_lane"]["injected_count"], 1)
        self.assertEqual(lanes["document_lane"]["excluded_count"], 1)
        self.assertEqual(lanes["biblio_lane"]["final_response_lock_present"], True)
        self.assertEqual(lanes["agenda_lane"]["status"], "disabled")
        self.assertEqual(lanes["adobe_lane"]["passage_count"], 3)
        self.assertEqual(lanes["export_lane"]["status"], "not_applicable")
        self.assertEqual(lanes["image_lane"]["status"], "not_applicable")
        self.assertEqual(manifest["messages"][1]["logical_roles"], ["note_lane"])
        self.assertEqual(manifest["messages"][2]["logical_roles"], ["document_lane"])
        self.assertEqual(manifest["messages"][3]["logical_roles"], ["biblio_lane"])
        self.assertEqual(manifest["messages"][4]["logical_roles"], ["adobe_lane"])
        self.assertIn("web_lane", manifest["messages"][-1]["logical_roles"])

    def test_real_lane_injections_are_classified_from_structured_sources(self) -> None:
        prompt_messages = [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "current question"},
        ]
        message_sources: dict[int, dict[str, object]] = {}

        note_read = {
            "ok": True,
            "note": {
                "note_v1_user": {"note_ref": "note_ref_test", "title": "Synthetic note"},
                "note_v1_technical": {"folder_ref": "folder_ref_test", "title_hash": "titlehash123"},
            },
            "note_conversation": {
                "note_ref": "note_ref_test",
                "folder_ref": "folder_ref_test",
                "markdown_char_count": 24,
                "markdown_content": "synthetic note body only",
            },
        }
        before = main_payload_manifest.capture_message_refs(prompt_messages)
        notes_lane = workspace_folder_notes_prompt_lane.inject_workspace_folder_notes_prompt_lane(
            prompt_messages,
            [note_read],
            requested_count=1,
        )
        message_sources.update(
            main_payload_manifest.message_sources_for_new_messages(
                prompt_messages,
                before,
                logical_roles=("note_lane",),
                origin="core.workspace_folder_notes_prompt_lane",
                origin_stage="late_note_lane",
                content_kind="tool_lane_context",
            )
        )

        before = main_payload_manifest.capture_message_refs(prompt_messages)
        document_lane = active_document_prompt_lane.inject_active_document_prompt_lane(
            prompt_messages,
            [
                {
                    "document_id": "doc-test",
                    "filename": "synthetic.txt",
                    "media_kind": "text",
                    "text_chars": 28,
                    "text_content": "synthetic document body only",
                    "injectable": True,
                }
            ],
            model="openai/gpt-5.1",
            count_tokens_func=lambda _messages, _model: 20,
            max_tokens=8000,
        )
        message_sources.update(
            main_payload_manifest.message_sources_for_new_messages(
                prompt_messages,
                before,
                logical_roles=("document_lane",),
                origin="core.active_document_prompt_lane",
                origin_stage="late_document_lane",
                content_kind="tool_lane_context",
            )
        )

        prompt_lane = SimpleNamespace(decisions=(object(),), passage_count=1, chars=32, max_passages=3, max_total_chars=8000)
        biblio_result = SimpleNamespace(
            enabled=True,
            used=True,
            reason_code="",
            query_kind="read_passages",
            observability_payload={"status": "ok", "enabled": True, "used": True},
            prompt_lane=prompt_lane,
            prompt_message={"role": "system", "content": "PASSAGES DE BIBLIOTHEQUE SYNTHETIQUES"},
            final_response_lock=None,
        )
        before = main_payload_manifest.capture_message_refs(prompt_messages)
        biblio_chat_runtime.inject_biblio_prompt_lane(prompt_messages, biblio_result)
        message_sources.update(
            main_payload_manifest.message_sources_for_new_messages(
                prompt_messages,
                before,
                logical_roles=("biblio_lane",),
                origin="biblio.chat_runtime",
                origin_stage="late_biblio_lane",
                content_kind="tool_lane_context",
            )
        )

        adobe_context = SimpleNamespace(
            active=True,
            product="photoshop",
            status="ok",
            evidence="synthetic",
            sources=(),
            passages=(
                SimpleNamespace(
                    source_type="helpx",
                    canonical_url="",
                    heading="Crop",
                    section_path=("Crop",),
                    text="synthetic adobe body only",
                ),
            ),
            injected_chars=25,
            reason_codes=("adobe_context_ready",),
        )
        before = main_payload_manifest.capture_message_refs(prompt_messages)
        adobe_lane = adobe_docs_prompt_lane.inject_adobe_prompt_lane(prompt_messages, adobe_context)
        message_sources.update(
            main_payload_manifest.message_sources_for_new_messages(
                prompt_messages,
                before,
                logical_roles=("adobe_lane",),
                origin="core.adobe_docs_prompt_lane",
                origin_stage="late_adobe_lane",
                content_kind="tool_lane_context",
            )
        )

        manifest = _build_manifest(
            prompt_messages=prompt_messages,
            message_sources=message_sources,
            workspace_notes_lane=notes_lane,
            active_document_lane=document_lane,
            biblio_result=biblio_result,
            adobe_context=adobe_context,
            adobe_lane=adobe_lane,
        )

        roles_by_stage: dict[str, set[str]] = {}
        for message in manifest["messages"]:
            roles_by_stage.setdefault(message["origin_stage"], set()).update(message["logical_roles"])

        self.assertIn("note_lane", roles_by_stage["late_note_lane"])
        self.assertIn("document_lane", roles_by_stage["late_document_lane"])
        self.assertIn("biblio_lane", roles_by_stage["late_biblio_lane"])
        self.assertIn("adobe_lane", roles_by_stage["late_adobe_lane"])
        encoded = _encoded(manifest)
        self.assertNotIn("synthetic note body only", encoded)
        self.assertNotIn("synthetic document body only", encoded)
        self.assertNotIn("synthetic adobe body only", encoded)

    def test_new_conversation_without_memory_keeps_noop_surfaces_visible(self) -> None:
        manifest = _build_manifest(
            conversation={"messages": []},
            turn_id="turn-pending-new",
            prompt_messages=[
                {"role": "system", "content": "system"},
                {"role": "user", "content": "new conversation question"},
            ],
            memory_traces=(),
            context_hints=(),
            web_runtime_payload={"enabled": False, "activation_mode": "off"},
        )

        self.assertFalse(manifest["conversation_id_present"])
        self.assertTrue(manifest["turn_id_present"])
        self.assertEqual(manifest["conversation_state"]["conversation_state_kind"], "pending_or_new_without_id")
        self.assertEqual(manifest["conversation_state"]["conversation_message_count"], 0)
        self.assertEqual(manifest["lane_statuses"]["memory"]["status"], "not_selected")
        self.assertEqual(manifest["lane_statuses"]["context_hints"]["status"], "not_selected")
        self.assertEqual(manifest["lane_statuses"]["web_lane"]["status"], "disabled")
        self.assertEqual(manifest["lane_statuses"]["note_lane"]["status"], "not_selected")
        self.assertEqual(manifest["lane_statuses"]["document_lane"]["status"], "not_selected")
        self.assertEqual(manifest["lane_statuses"]["export_lane"]["status"], "not_applicable")
        self.assertEqual(manifest["lane_statuses"]["image_lane"]["status"], "not_applicable")
        self.assertEqual(manifest["lane_conflicts"]["status"], "not_selected")
        self.assertEqual(manifest["lane_conflicts"]["reason_code"], "no_final_response_lock")
        self.assertFalse(manifest["lane_conflicts"]["implicit_injection_detected"])

    def test_final_response_lock_bypasses_main_model_without_content(self) -> None:
        raw_final = "SENSITIVE_FINAL_LOCK_MARKER_D"
        override = chat_llm_flow.AssistantResponseOverride(
            content=raw_final,
            source="agenda_final_response_lock",
            reason_code="agenda_final_response_authorized",
            observability={
                "status": "authorized",
                "content_hash": "abcdef123456",
                "content_present": True,
                "content_chars": len(raw_final),
            },
        )
        manifest = _build_manifest(assistant_response_override=override)

        self.assertFalse(manifest["main_model_called"])
        self.assertTrue(manifest["final_response_lock"]["present"])
        self.assertTrue(manifest["final_response_lock"]["main_model_bypassed"])
        self.assertEqual(manifest["final_response_lock"]["source"], "agenda_final_response_lock")
        self.assertEqual(manifest["final_response_lock"]["reason_code"], "agenda_final_response_authorized")
        self.assertEqual(manifest["final_response_lock"]["priority_policy"], "agenda_over_biblio")
        self.assertFalse(manifest["final_response_lock"]["raw_content_included"])
        self.assertNotIn(raw_final, _encoded(manifest))
        self.assertNotIn("abcdef123456", _encoded(manifest))

    def test_agenda_final_lock_is_selected_content_free(self) -> None:
        raw_final = "SENSITIVE_AGENDA_FINAL_LOCK"
        lock = SimpleNamespace(source="agenda_readonly_response")
        agenda_result = SimpleNamespace(
            enabled=True,
            used=True,
            status="ok",
            reason_code="agenda_readonly_final_response",
            observability_payload={
                "enabled": True,
                "status": "ok",
                "reason_code": "agenda_readonly_final_response",
                "mode": "readonly",
                "tool_count": 1,
                "model_called": False,
            },
            final_response_lock=lock,
        )
        override = chat_llm_flow.AssistantResponseOverride(
            content=raw_final,
            source="agenda_readonly_response",
            reason_code="agenda_readonly_final_response",
            observability={
                "content_present": True,
                "content_chars": len(raw_final),
                "content_hash": "agenda_hash_must_not_leak",
            },
        )

        manifest = _build_manifest(
            assistant_response_override=override,
            agenda_result=agenda_result,
        )

        self.assertFalse(manifest["main_model_called"])
        self.assertEqual(manifest["final_response_lock"]["source"], "agenda_readonly_response")
        self.assertTrue(manifest["lane_statuses"]["agenda_lane"]["final_response_lock_present"])
        self.assertTrue(manifest["lane_statuses"]["agenda_lane"]["final_response_lock_selected"])
        self.assertFalse(manifest["lane_statuses"]["agenda_lane"]["final_response_lock_suppressed"])
        self.assertEqual(manifest["lane_conflicts"]["candidate_count"], 1)
        self.assertEqual(manifest["lane_conflicts"]["candidate_sources"], ["agenda_readonly_response"])
        self.assertTrue(manifest["lane_conflicts"]["agenda_selected"])
        self.assertFalse(manifest["lane_conflicts"]["biblio_selected"])
        self.assertFalse(manifest["lane_conflicts"]["conflict_present"])
        self.assertTrue(manifest["windows"]["agenda_recent_dialogue"]["final_response_lock_present"])
        encoded = _encoded(manifest)
        self.assertNotIn(raw_final, encoded)
        self.assertNotIn("agenda_hash_must_not_leak", encoded)

    def test_biblio_final_lock_is_selected_content_free(self) -> None:
        raw_final = "SENSITIVE_BIBLIO_FINAL_LOCK"
        lock = SimpleNamespace(source="biblio_rendered_answer")
        biblio_result = SimpleNamespace(
            enabled=True,
            used=True,
            reason_code="biblio_final_response_authorized",
            query_kind="read_passages",
            observability_payload={"status": "ok", "enabled": True, "used": True},
            prompt_lane=SimpleNamespace(decisions=(), passage_count=0, chars=0, max_passages=3, max_total_chars=8000),
            prompt_message=None,
            final_response_lock=lock,
        )
        override = chat_llm_flow.AssistantResponseOverride(
            content=raw_final,
            source="biblio_rendered_answer",
            reason_code="biblio_final_response_authorized",
            observability={
                "content_present": True,
                "content_chars": len(raw_final),
                "content_sha256_12": "biblio_hash_must_not_leak",
            },
        )

        manifest = _build_manifest(
            assistant_response_override=override,
            biblio_result=biblio_result,
        )

        self.assertFalse(manifest["main_model_called"])
        self.assertEqual(manifest["final_response_lock"]["source"], "biblio_rendered_answer")
        self.assertTrue(manifest["lane_statuses"]["biblio_lane"]["final_response_lock_present"])
        self.assertTrue(manifest["lane_statuses"]["biblio_lane"]["final_response_lock_selected"])
        self.assertFalse(manifest["lane_statuses"]["biblio_lane"]["final_response_lock_suppressed"])
        self.assertEqual(manifest["lane_conflicts"]["candidate_count"], 1)
        self.assertEqual(manifest["lane_conflicts"]["candidate_sources"], ["biblio_rendered_answer"])
        self.assertFalse(manifest["lane_conflicts"]["agenda_selected"])
        self.assertTrue(manifest["lane_conflicts"]["biblio_selected"])
        self.assertFalse(manifest["lane_conflicts"]["conflict_present"])
        self.assertTrue(manifest["windows"]["biblio_recent_dialogue"]["final_response_lock_present"])
        encoded = _encoded(manifest)
        self.assertNotIn(raw_final, encoded)
        self.assertNotIn("biblio_hash_must_not_leak", encoded)

    def test_agenda_biblio_lock_conflict_records_agenda_priority(self) -> None:
        raw_agenda = "SENSITIVE_AGENDA_CONFLICT_LOCK"
        raw_biblio = "SENSITIVE_BIBLIO_CONFLICT_LOCK"
        prompt_messages = [
            {"role": "system", "content": "system"},
            {"role": "system", "content": "synthetic biblio lane block"},
            {"role": "user", "content": "question"},
        ]
        biblio_lock = SimpleNamespace(source="biblio_rendered_answer", content=raw_biblio)
        biblio_result = SimpleNamespace(
            enabled=True,
            used=True,
            reason_code="biblio_final_response_authorized",
            query_kind="read_passages",
            observability_payload={"status": "ok", "enabled": True, "used": True},
            prompt_lane=SimpleNamespace(decisions=(object(),), passage_count=1, chars=42, max_passages=3, max_total_chars=8000),
            prompt_message=prompt_messages[1],
            final_response_lock=biblio_lock,
        )
        agenda_lock = SimpleNamespace(source="agenda_readonly_response", content=raw_agenda)
        agenda_result = SimpleNamespace(
            enabled=True,
            used=True,
            status="ok",
            reason_code="agenda_readonly_final_response",
            observability_payload={
                "enabled": True,
                "status": "ok",
                "reason_code": "agenda_readonly_final_response",
                "mode": "readonly",
                "tool_count": 1,
                "model_called": False,
            },
            final_response_lock=agenda_lock,
        )
        override = chat_llm_flow.AssistantResponseOverride(
            content=raw_agenda,
            source="agenda_readonly_response",
            reason_code="agenda_readonly_final_response",
            observability={
                "content_present": True,
                "content_chars": len(raw_agenda),
            },
        )

        manifest = _build_manifest(
            prompt_messages=prompt_messages,
            message_sources=dict(
                (
                    _message_source(
                        prompt_messages[1],
                        "biblio_lane",
                        "biblio.chat_runtime",
                        "late_biblio_lane",
                    ),
                )
            ),
            assistant_response_override=override,
            biblio_result=biblio_result,
            agenda_result=agenda_result,
            biblio_recent_dialogue=({"role": "user"},),
            agenda_recent_dialogue=({"role": "user"},),
        )

        self.assertFalse(manifest["main_model_called"])
        self.assertEqual(manifest["final_response_lock"]["source"], "agenda_readonly_response")
        self.assertTrue(manifest["lane_conflicts"]["conflict_present"])
        self.assertEqual(manifest["lane_conflicts"]["priority_policy"], "agenda_over_biblio")
        self.assertEqual(manifest["lane_conflicts"]["status"], "ok")
        self.assertEqual(manifest["lane_conflicts"]["reason_code"], "agenda_over_biblio_applied")
        self.assertEqual(manifest["lane_conflicts"]["candidate_count"], 2)
        self.assertEqual(
            manifest["lane_conflicts"]["candidate_sources"],
            ["agenda_readonly_response", "biblio_rendered_answer"],
        )
        self.assertTrue(manifest["lane_conflicts"]["agenda_selected"])
        self.assertFalse(manifest["lane_conflicts"]["biblio_selected"])
        self.assertEqual(manifest["lane_conflicts"]["suppressed_source"], "biblio_rendered_answer")
        self.assertEqual(manifest["lane_conflicts"]["suppressed_count"], 1)
        self.assertEqual(manifest["lane_conflicts"]["message_lane_block_count"], 1)
        self.assertEqual(manifest["lane_conflicts"]["message_lane_status_mismatch_count"], 0)
        self.assertFalse(manifest["lane_conflicts"]["implicit_injection_detected"])
        self.assertTrue(manifest["lane_statuses"]["agenda_lane"]["final_response_lock_selected"])
        self.assertFalse(manifest["lane_statuses"]["agenda_lane"]["final_response_lock_suppressed"])
        self.assertFalse(manifest["lane_statuses"]["biblio_lane"]["final_response_lock_selected"])
        self.assertTrue(manifest["lane_statuses"]["biblio_lane"]["final_response_lock_suppressed"])
        self.assertEqual(manifest["messages"][1]["logical_roles"], ["biblio_lane"])
        self.assertTrue(manifest["windows"]["agenda_recent_dialogue"]["final_response_lock_present"])
        self.assertTrue(manifest["windows"]["biblio_recent_dialogue"]["final_response_lock_present"])
        encoded = _encoded(manifest)
        self.assertNotIn(raw_agenda, encoded)
        self.assertNotIn(raw_biblio, encoded)

    def test_unexpected_biblio_priority_over_agenda_is_failed_content_free(self) -> None:
        raw_agenda = "SENSITIVE_AGENDA_UNEXPECTED_LOCK"
        raw_biblio = "SENSITIVE_BIBLIO_UNEXPECTED_LOCK"
        biblio_lock = SimpleNamespace(source="biblio_rendered_answer", content=raw_biblio)
        biblio_result = SimpleNamespace(
            enabled=True,
            used=True,
            reason_code="biblio_final_response_authorized",
            query_kind="read_passages",
            observability_payload={"status": "ok", "enabled": True, "used": True},
            prompt_lane=SimpleNamespace(decisions=(), passage_count=0, chars=0, max_passages=3, max_total_chars=8000),
            prompt_message=None,
            final_response_lock=biblio_lock,
        )
        agenda_lock = SimpleNamespace(source="agenda_readonly_response", content=raw_agenda)
        agenda_result = SimpleNamespace(
            enabled=True,
            used=True,
            status="ok",
            reason_code="agenda_readonly_final_response",
            observability_payload={
                "enabled": True,
                "status": "ok",
                "reason_code": "agenda_readonly_final_response",
                "mode": "readonly",
                "tool_count": 1,
                "model_called": False,
            },
            final_response_lock=agenda_lock,
        )
        override = chat_llm_flow.AssistantResponseOverride(
            content=raw_biblio,
            source="biblio_rendered_answer",
            reason_code="biblio_final_response_authorized",
            observability={
                "content_present": True,
                "content_chars": len(raw_biblio),
            },
        )

        manifest = _build_manifest(
            assistant_response_override=override,
            biblio_result=biblio_result,
            agenda_result=agenda_result,
            biblio_recent_dialogue=({"role": "user"},),
            agenda_recent_dialogue=({"role": "user"},),
        )

        self.assertFalse(manifest["main_model_called"])
        self.assertEqual(manifest["final_response_lock"]["source"], "biblio_rendered_answer")
        self.assertTrue(manifest["lane_conflicts"]["conflict_present"])
        self.assertEqual(manifest["lane_conflicts"]["priority_policy"], "agenda_over_biblio")
        self.assertEqual(manifest["lane_conflicts"]["reason_code"], "final_lock_priority_unexpected")
        self.assertEqual(manifest["lane_conflicts"]["status"], "failed")
        self.assertFalse(manifest["lane_conflicts"]["agenda_selected"])
        self.assertTrue(manifest["lane_conflicts"]["biblio_selected"])
        self.assertEqual(manifest["lane_conflicts"]["selected_source"], "biblio_rendered_answer")
        self.assertEqual(manifest["lane_conflicts"]["suppressed_source"], "agenda_readonly_response")
        self.assertEqual(manifest["lane_conflicts"]["suppressed_count"], 1)
        self.assertTrue(manifest["lane_statuses"]["agenda_lane"]["final_response_lock_suppressed"])
        self.assertTrue(manifest["lane_statuses"]["biblio_lane"]["final_response_lock_selected"])
        encoded = _encoded(manifest)
        self.assertNotIn(raw_agenda, encoded)
        self.assertNotIn(raw_biblio, encoded)

    def test_hash_policy_rejects_stable_short_hash_leakage(self) -> None:
        sensitive_text = "short sensitive text for dictionary attack"
        naive_hash_12 = hashlib.sha256(sensitive_text.encode("utf-8")).hexdigest()[:12]
        manifest = _build_manifest(
            prompt_messages=[
                {"role": "system", "content": f"system {sensitive_text}"},
                {"role": "user", "content": f"user {sensitive_text}"},
            ],
        )

        encoded = _encoded(manifest)
        self.assertEqual(manifest["hash_policy"]["stable_text_hashes_included"], False)
        self.assertEqual(manifest["hash_policy"]["short_stable_text_hashes_included"], False)
        self.assertNotIn("hash_12", encoded)
        self.assertNotIn(naive_hash_12, encoded)
        self.assertNotIn(sensitive_text, encoded)

    def test_admin_projection_preserves_manifest_shape_content_free(self) -> None:
        raw_prompt = "SENSITIVE_PROMPT_MARKER_F"
        raw_user = "SENSITIVE_USER_MARKER_F"
        credential_marker = "SENSITIVE_CREDENTIAL_MARKER_F"
        dav_marker = "https" + "://dav.example.invalid/private/path"
        data_marker = "data:" + "image/png;" + "base" + "64," + "AAAA"
        manifest = _build_manifest(
            prompt_messages=[
                {"role": "system", "content": f"system {raw_prompt} {credential_marker}"},
                {"role": "user", "content": f"{raw_user} {dav_marker} {data_marker}"},
            ],
            web_runtime_payload={
                "enabled": True,
                "activation_mode": "manual",
                "status": "ok",
                "context_injected": True,
                "results_count": 1,
                "context_chars": 25,
            },
        )

        projected, redaction = admin_log_projection.project_payload(manifest)
        encoded = _encoded(projected)

        self.assertEqual(projected["schema_version"], "main_payload_manifest_v1")
        self.assertIn("messages", projected)
        self.assertEqual(projected["messages"][0]["provider_role"], "system")
        self.assertEqual(projected["messages"][1]["provider_role"], "user")
        self.assertIn("raw_flags", projected)
        self.assertFalse(projected["raw_flags"]["raw_prompt_included"])
        self.assertFalse(redaction["raw_event_payloads_included"])
        for marker in (raw_prompt, raw_user, credential_marker, dav_marker, data_marker):
            self.assertNotIn(marker, encoded)


if __name__ == "__main__":
    unittest.main()
