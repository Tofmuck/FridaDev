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
    }
    base.update(overrides)
    return main_payload_manifest.build_main_payload_manifest(**base)


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
                "summary": {"id": "summary-opaque", "content": raw_summary},
            },
            memory_traces=({"content": raw_memory},),
            context_hints=("SENSITIVE_HINT_MARKER_B",),
            recent_context_payload={"messages": [{"role": "user"}, {"role": "assistant"}, {"role": "user"}]},
            recent_window_payload={"turn_count": 2, "max_recent_turns": 5, "has_in_progress_turn": True},
            biblio_recent_dialogue=({"role": "user"}, {"role": "assistant"}),
            agenda_recent_dialogue=({"role": "user"},),
        )

        self.assertEqual(manifest["windows"]["conversation"]["message_count"], 5)
        self.assertEqual(manifest["windows"]["prompt_final"]["message_count"], 6)
        self.assertEqual(manifest["windows"]["recent_context"]["message_count"], 3)
        self.assertEqual(manifest["windows"]["recent_window"]["turn_count"], 2)
        self.assertEqual(manifest["windows"]["biblio_recent_dialogue"]["message_count"], 2)
        self.assertEqual(manifest["lane_statuses"]["summary"]["status"], "ok")
        self.assertEqual(manifest["lane_statuses"]["memory"]["status"], "ok")
        self.assertEqual(manifest["lane_statuses"]["context_hints"]["status"], "ok")

        encoded = _encoded(manifest)
        self.assertNotIn(raw_summary, encoded)
        self.assertNotIn(raw_memory, encoded)
        self.assertNotIn("SENSITIVE_HINT_MARKER_B", encoded)

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
        manifest = _build_manifest(
            prompt_messages=[
                {"role": "system", "content": "system"},
                {"role": "system", "content": "[NOTES DE DOSSIER PREPAREES]"},
                {"role": "user", "content": "[DOCUMENTS ACTIFS INJECTES]"},
                {"role": "system", "content": "[PASSAGES DE BIBLIOTHEQUE CONSULTES]"},
                {"role": "user", "content": "[ADOBE DOCS PASSAGES]"},
                {"role": "user", "content": "current question"},
            ],
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
