from __future__ import annotations

import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import chat_service
from core import workspace_folder_notes
from core import workspace_folder_notes_prompt_lane


FOLDER_ID = "11111111-2222-4333-8444-555555555555"
NOTE_ID = "33333333-3333-4333-8333-333333333333"


class _FakeWorkspaceFolders:
    def get_workspace_folder(self, folder_id, *, include_deleted=False):
        if folder_id != FOLDER_ID:
            return None
        return {
            "id": FOLDER_ID,
            "display_name": "Projet sensible",
            "nextcloud_target_name": "Projet-sensible",
            "nextcloud_sync_state": "linked",
            "deleted_at": None,
        }


class _FakeNotesRead:
    def __init__(self, markdown: str):
        self.markdown = markdown
        self.calls = []

    def prepare_workspace_folder_note_for_conversation(self, folder, *, note_id, notes_module):
        self.calls.append({"folder_id": folder.get("id"), "note_id": note_id})
        title = "Carnet sensible"
        target = workspace_folder_notes.sanitize_note_target_name(title)
        return {
            "ok": True,
            "reason_code": workspace_folder_notes.REASON_READ_OK,
            "status": 200,
            "note": {
                "note_v1_user": {
                    "note_id": NOTE_ID,
                    "note_ref": workspace_folder_notes.note_ref(NOTE_ID),
                    "title": title,
                },
                "note_v1_technical": {
                    "note_ref": workspace_folder_notes.note_ref(NOTE_ID),
                    "folder_ref": workspace_folder_notes.folder_ref(FOLDER_ID),
                    "title_hash": workspace_folder_notes.title_hash_for_target(target),
                    "etag_hash": "abcdef123456",
                    "etag_present": True,
                    "status": "available",
                    "reason_code": workspace_folder_notes.REASON_READ_OK,
                },
            },
            "note_conversation": {
                "read_state": "ready",
                "reason_code": workspace_folder_notes.REASON_READ_OK,
                "note_ref": workspace_folder_notes.note_ref(NOTE_ID),
                "folder_ref": workspace_folder_notes.folder_ref(FOLDER_ID),
                "markdown_char_count": len(self.markdown),
                "markdown_content": self.markdown,
                "injection_scope": "current_turn_only",
                "memory_rag_identity_summary": "not_used",
            },
            "note_nextcloud": {
                "read_state": "ready",
                "reason_code": workspace_folder_notes.REASON_READ_OK,
                "etag_hash": "abcdef123456",
                "etag_present": True,
            },
        }


class ChatWorkspaceFolderNotesPromptTests(unittest.TestCase):
    def test_workspace_notes_mode_without_selected_note_is_visible_to_backend_prompt(self) -> None:
        reader = _FakeNotesRead("unused markdown should not be read")
        result = workspace_folder_notes_prompt_lane.read_workspace_folder_notes_for_prompt(
            data={"workspace_notes_mode": True},
            conversation={"workspace_folder_id": FOLDER_ID},
            workspace_folders_module=_FakeWorkspaceFolders(),
            workspace_folder_notes_module=workspace_folder_notes,
            workspace_folder_notes_read_module=reader,
        )
        prompt_messages = [{"role": "user", "content": "Préparons une note"}]

        lane = workspace_folder_notes_prompt_lane.inject_workspace_folder_notes_prompt_lane(
            prompt_messages,
            result.note_reads,
            read_status=result.status,
            read_reason_code=result.reason_code,
            requested_count=result.requested_count,
        )

        self.assertEqual(reader.calls, [])
        self.assertEqual(result.status, workspace_folder_notes_prompt_lane.READ_STATUS_OK)
        self.assertEqual(
            result.reason_code,
            workspace_folder_notes_prompt_lane.REASON_MODE_ACTIVE_WITHOUT_SELECTION,
        )
        self.assertEqual(lane.injected_count, 0)
        self.assertEqual(lane.requested_count, 1)
        self.assertEqual(prompt_messages[0]["role"], "system")
        self.assertIn("note_mode_active", prompt_messages[0]["content"])
        self.assertNotIn("selectionnees explicitement", prompt_messages[0]["content"])
        self.assertNotIn("[MARKDOWN]", str(prompt_messages))
        self.assertNotIn("unused markdown", str(prompt_messages))
        self.assertNotIn("markdown_content", str(lane.as_content_free_dict()))

    def test_workspace_notes_mode_without_current_folder_does_not_claim_current_folder(self) -> None:
        reader = _FakeNotesRead("unused markdown should not be read")
        result = workspace_folder_notes_prompt_lane.read_workspace_folder_notes_for_prompt(
            data={"workspace_notes_mode": True},
            conversation={},
            workspace_folders_module=_FakeWorkspaceFolders(),
            workspace_folder_notes_module=workspace_folder_notes,
            workspace_folder_notes_read_module=reader,
        )
        prompt_messages = [{"role": "user", "content": "Préparons une note"}]

        lane = workspace_folder_notes_prompt_lane.inject_workspace_folder_notes_prompt_lane(
            prompt_messages,
            result.note_reads,
            read_status=result.status,
            read_reason_code=result.reason_code,
            requested_count=result.requested_count,
        )

        self.assertEqual(reader.calls, [])
        self.assertEqual(result.status, workspace_folder_notes_prompt_lane.READ_STATUS_ERROR)
        self.assertEqual(result.reason_code, workspace_folder_notes.REASON_FOLDER_NOT_LINKED)
        self.assertEqual(lane.injected_count, 0)
        self.assertEqual(prompt_messages[0]["role"], "system")
        self.assertIn(workspace_folder_notes.REASON_FOLDER_NOT_LINKED, prompt_messages[0]["content"])
        self.assertNotIn("dossier courant", prompt_messages[0]["content"])
        self.assertNotIn("selectionnees explicitement", prompt_messages[0]["content"])
        self.assertNotIn("[MARKDOWN]", str(prompt_messages))
        self.assertNotIn("unused markdown", str(prompt_messages))
        self.assertNotIn("markdown_content", str(lane.as_content_free_dict()))

    def test_chat_response_injects_explicit_note_and_continuity_capsule_in_prompt_turn(self) -> None:
        markdown = "# Note sensible\n\nContenu conversationnel utile"
        capsule_text = "ARTIFICIAL_CHAT_SERVICE_CAPSULE_SENTINEL"
        observed: dict[str, object] = {
            "prompt_messages": [],
            "states": [],
            "events": [],
        }
        conversation = {
            "id": "conv-notes-prompt",
            "created_at": "2026-06-18T12:00:00Z",
            "workspace_folder_id": FOLDER_ID,
            "messages": [],
        }

        def fake_run_llm_exchange(**kwargs):
            observed["prompt_messages"] = list(kwargs["prompt_messages"])
            return {
                "kind": "json",
                "payload": {"ok": True},
                "status": 200,
                "headers": {},
            }

        conv_store_module = SimpleNamespace(
            append_message=lambda conv, role, content, meta=None, timestamp=None: conv["messages"].append(
                {"role": role, "content": content, "timestamp": timestamp, **({"meta": meta} if meta is not None else {})}
            ),
            save_conversation=lambda *_args, **_kwargs: None,
            build_prompt_messages=lambda conv, *_args, **_kwargs: [
                {"role": str(message.get("role") or ""), "content": str(message.get("content") or "")}
                for message in conv.get("messages", [])
            ],
        )
        runtime_settings_module = SimpleNamespace(
            get_main_model_settings=lambda: SimpleNamespace(
                payload={
                    "model": {"value": "openrouter/runtime-main-model"},
                    "temperature": {"value": 0.35},
                    "top_p": {"value": 0.82},
                    "response_max_tokens": {"value": 512},
                }
            )
        )
        session = {
            "user_msg": "Lis cette note",
            "conversation": conversation,
            "stream_req": False,
            "web_search_on": False,
            "input_mode": "keyboard",
        }
        fake_notes_read = _FakeNotesRead(markdown)

        with ExitStack() as stack:
            stack.enter_context(patch.object(chat_service.chat_session_flow, "resolve_chat_session", return_value=(session, None)))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, "resolve_backend_prompts", return_value=("SYSTEM", "HERMENEUTIC")))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, "build_augmented_system", return_value=("AUGMENTED SYSTEM", [])))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, "apply_augmented_system", side_effect=lambda *_args, **_kwargs: None))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, "build_hermeneutic_judgment_block", return_value=""))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, "inject_hermeneutic_judgment_block", side_effect=lambda text, _block: text))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, "build_voice_transcription_guard_block", return_value=""))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, "inject_voice_transcription_guard_block", side_effect=lambda text, _block: text))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, "build_direct_identity_revelation_guard_block", return_value=""))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, "inject_direct_identity_revelation_guard_block", side_effect=lambda text, _block: text))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, "build_web_reading_guard_block", return_value=""))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, "inject_web_reading_guard_block", side_effect=lambda text, _block: text))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, "build_web_evidence_guard_block", return_value=""))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, "inject_web_evidence_guard_block", side_effect=lambda text, _block: text))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, "build_plain_text_guard_block", return_value=""))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, "inject_plain_text_guard_block", side_effect=lambda text, _block: text))
            stack.enter_context(patch.object(chat_service.chat_prompt_context, "inject_web_context", side_effect=lambda *_args, **_kwargs: None))
            stack.enter_context(patch.object(chat_service.chat_memory_flow, "prepare_memory_context", return_value=("shadow", [], [])))
            stack.enter_context(patch.object(chat_service, "_resolve_summary_input", return_value={}))
            stack.enter_context(patch.object(chat_service, "_resolve_identity_input", return_value={}))
            stack.enter_context(patch.object(chat_service, "_resolve_recent_context_input", return_value={}))
            stack.enter_context(patch.object(chat_service, "_resolve_recent_window_input", return_value={}))
            stack.enter_context(patch.object(chat_service, "_resolve_user_turn_runtime_inputs", return_value=({}, {})))
            stack.enter_context(patch.object(chat_service, "_run_stimmung_agent_stage", return_value=None))
            stack.enter_context(patch.object(chat_service, "_store_latest_user_affective_turn_signal", side_effect=lambda *_args, **_kwargs: None))
            stack.enter_context(patch.object(chat_service, "_resolve_web_runtime_payload", return_value={"activation_mode": "not_requested"}))
            stack.enter_context(patch.object(chat_service, "_run_hermeneutic_node_insertion_point", return_value={}))
            stack.enter_context(patch.object(chat_service, "_active_documents_for_prompt", return_value=chat_service.ActiveDocumentsPromptRead(status="empty")))
            stack.enter_context(patch.object(chat_service, "_workspace_files_for_prompt", return_value=chat_service.ActiveDocumentsPromptRead(status="empty")))
            stack.enter_context(patch.object(chat_service, "_record_active_document_prompt_decisions", side_effect=lambda *_args, **_kwargs: None))
            stack.enter_context(patch.object(chat_service.active_documents_observability, "emit_prompt_decision_event", side_effect=lambda *_args, **_kwargs: None))
            stack.enter_context(patch.object(chat_service.biblio_chat_runtime, "read_biblio_conversation_state", return_value={}))
            stack.enter_context(
                patch.object(
                    chat_service.biblio_chat_runtime,
                    "run_biblio_chat_turn",
                    return_value=SimpleNamespace(
                        observability_payload={},
                        enabled=False,
                        used=False,
                        query_kind="none",
                        final_response_lock=None,
                        answer_object=None,
                        rendered_answer=None,
                    ),
                )
            )
            stack.enter_context(patch.object(chat_service.biblio_chat_runtime, "attach_biblio_conversation_state", side_effect=lambda *_args, **_kwargs: None))
            stack.enter_context(patch.object(chat_service.biblio_chat_runtime, "inject_biblio_prompt_lane", side_effect=lambda *_args, **_kwargs: None))
            stack.enter_context(patch.object(chat_service.agenda_chat_runtime, "normalize_agenda_enabled", return_value=False))
            stack.enter_context(patch.object(chat_service, "_now_iso", return_value="2026-06-18T12:01:00Z"))
            stack.enter_context(patch.object(chat_service.chat_llm_flow, "run_llm_exchange", side_effect=fake_run_llm_exchange))
            stack.enter_context(patch.object(chat_service.chat_turn_logger, "current_turn_id", return_value="turn-notes"))
            stack.enter_context(patch.object(chat_service.chat_turn_logger, "set_state", side_effect=lambda name, payload: observed["states"].append((name, payload))))
            stack.enter_context(patch.object(chat_service.chat_turn_logger, "emit", side_effect=lambda name, **payload: observed["events"].append((name, payload))))
            stack.enter_context(patch.object(chat_service.canonical_stimmung_input, "build_stimmung_input", return_value={}))
            stack.enter_context(patch.object(chat_service.canonical_web_input, "build_web_input_from_runtime_payload", side_effect=lambda payload: dict(payload)))
            stack.enter_context(patch.object(chat_service.assistant_output_contract, "resolve_assistant_output_policy", return_value=None))

            result = chat_service.chat_response(
                {
                    "message": "Lis cette note",
                    "workspace_note_id": NOTE_ID,
                },
                prompt_loader_module=SimpleNamespace(),
                conv_store_module=conv_store_module,
                memory_store_module=SimpleNamespace(),
                runtime_settings_module=runtime_settings_module,
                summarizer_module=SimpleNamespace(maybe_summarize=lambda *_args, **_kwargs: False),
                identity_module=SimpleNamespace(),
                admin_logs_module=SimpleNamespace(log_event=lambda *_args, **_kwargs: None),
                llm_module=SimpleNamespace(),
                requests_module=SimpleNamespace(),
                token_utils_module=SimpleNamespace(estimate_tokens=lambda *_args, **_kwargs: 1),
                arbiter_module=SimpleNamespace(),
                web_search_module=SimpleNamespace(),
                config_module=SimpleNamespace(
                    FRIDA_TIMEZONE="UTC",
                    CONTINUITY_CAPSULE_ENABLED=True,
                    CONTINUITY_CAPSULE_TEXT=capsule_text,
                    CONTINUITY_CAPSULE_VERSION="continuity_capsule_v1",
                    CONTINUITY_CAPSULE_MAX_CHARS=200,
                ),
                logger=SimpleNamespace(info=lambda *_args, **_kwargs: None, warning=lambda *_args, **_kwargs: None, error=lambda *_args, **_kwargs: None),
                workspace_folders_module=_FakeWorkspaceFolders(),
                workspace_folder_notes_module=workspace_folder_notes,
                workspace_folder_notes_read_module=fake_notes_read,
            )

        self.assertEqual(result["kind"], "json")
        self.assertEqual(result["status"], 200)
        prompt_text = "\n".join(message["content"] for message in observed["prompt_messages"])
        self.assertIn(markdown, prompt_text)
        self.assertIn(capsule_text, prompt_text)
        self.assertEqual(fake_notes_read.calls, [{"folder_id": FOLDER_ID, "note_id": NOTE_ID}])
        self.assertNotIn(markdown, str(observed["states"]))
        self.assertNotIn(markdown, str(observed["events"]))
        self.assertNotIn(capsule_text, str(observed["states"]))
        self.assertNotIn(capsule_text, str(observed["events"]))
        self.assertNotIn("Carnet sensible", str(observed["states"]))
        self.assertNotIn("abcdef123456", str(observed["events"]))
        manifest_events = [
            payload["payload"]
            for name, payload in observed["events"]
            if name == "main_payload_manifest"
        ]
        self.assertEqual(len(manifest_events), 1)
        manifest = manifest_events[0]
        self.assertEqual(manifest["schema_version"], "main_payload_manifest_v1")
        self.assertTrue(manifest["main_model_called"])
        self.assertEqual(manifest["lane_statuses"]["note_lane"]["status"], "ok")
        self.assertEqual(manifest["lane_statuses"]["note_lane"]["injected_count"], 1)
        self.assertFalse(manifest["lane_statuses"]["note_lane"]["raw_lane_content_included"])
        self.assertEqual(manifest["continuity_capsule"]["status"], "ok")
        self.assertEqual(manifest["continuity_capsule"]["injected_count"], 1)
        self.assertFalse(manifest["continuity_capsule"]["raw_capsule_content_included"])
        capsule_messages = [
            message
            for message in manifest["messages"]
            if "continuity_capsule" in message["logical_roles"]
        ]
        self.assertEqual(len(capsule_messages), 1)
        self.assertEqual(capsule_messages[0]["origin"], "core.continuity_capsule")
        self.assertEqual(capsule_messages[0]["origin_stage"], "late_continuity_capsule")
        note_messages = [
            message
            for message in manifest["messages"]
            if "note_lane" in message["logical_roles"]
        ]
        self.assertGreaterEqual(len(note_messages), 1)
        self.assertTrue(
            all(message["origin"] == "core.workspace_folder_notes_prompt_lane" for message in note_messages)
        )
        self.assertTrue(all(message["origin_stage"] == "late_note_lane" for message in note_messages))
        self.assertNotIn(markdown, str(manifest))
        self.assertNotIn(capsule_text, str(manifest))
        self.assertEqual(conversation["messages"][0]["content"], "Lis cette note")
        self.assertNotIn(markdown, str(conversation["messages"]))
        self.assertNotIn(capsule_text, str(conversation["messages"]))


if __name__ == "__main__":
    unittest.main()
