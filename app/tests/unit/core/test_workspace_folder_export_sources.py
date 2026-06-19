from __future__ import annotations

import unittest

from core import workspace_folder_export_conversation_store
from core import workspace_folder_export_sources


CONVERSATION_ID = "22222222-3333-4444-8555-666666666666"


class _FakeConversationStore:
    def __init__(self, *, summary=None, conversation=None, normalized=CONVERSATION_ID):
        self.summary = summary
        self.conversation = conversation
        self.normalized = normalized
        self.calls = []

    def normalize_conversation_id(self, value):
        self.calls.append(("normalize", value))
        return self.normalized

    def get_conversation_summary(self, conversation_id, *, include_deleted=False):
        self.calls.append(("summary", conversation_id, include_deleted))
        if self.summary == "raise":
            raise RuntimeError("raw store failure")
        return self.summary

    def read_conversation(self, conversation_id, system_prompt):
        self.calls.append(("read", conversation_id, system_prompt))
        if self.conversation == "raise":
            raise RuntimeError("raw read failure")
        return self.conversation


class WorkspaceFolderExportSourcesTests(unittest.TestCase):
    def test_conversation_source_excludes_system_and_tool_messages(self) -> None:
        source = workspace_folder_export_sources.acquire_export_source(
            {
                "source_kind": "conversation",
                "explicit_source": True,
                "conversation_id": "11111111-2222-4333-8444-555555555555",
                "messages": [
                    {"id": "sys", "role": "system", "content": "do not export"},
                    {"id": "u1", "role": "user", "content": "Bonjour Frida"},
                    {"id": "tool", "role": "tool", "content": "payload technique"},
                    {"id": "a1", "role": "assistant", "content": "Bonjour."},
                ],
            }
        )

        self.assertTrue(source.ok)
        self.assertIn("Bonjour Frida", source.content)
        self.assertIn("Bonjour.", source.content)
        self.assertNotIn("do not export", source.content)
        self.assertNotIn("payload technique", source.content)
        self.assertEqual(source.counters["message_count"], 2)
        self.assertTrue(source.source_ref.startswith("conversation:11111111:"))

    def test_conversation_source_reads_store_when_messages_are_absent(self) -> None:
        fake_store = _FakeConversationStore(
            summary={
                "id": CONVERSATION_ID,
                "title": "Conversation source",
                "message_count": 2,
                "deleted_at": None,
            },
            conversation={
                "id": CONVERSATION_ID,
                "messages": [
                    {"role": "system", "content": "system prompt interdit"},
                    {"role": "user", "content": "Question relue"},
                    {"role": "tool", "content": "payload outil interdit"},
                    {"role": "assistant", "content": "Reponse relue", "meta": {"private_meta": "non"}},
                ],
            },
        )

        source = workspace_folder_export_sources.acquire_export_source(
            {
                "source_kind": "conversation",
                "explicit_source": True,
                "conversation_id": CONVERSATION_ID,
            },
            conversation_reader=lambda payload: workspace_folder_export_conversation_store.read_conversation_source(
                payload,
                conv_store_module=fake_store,
            ),
        )

        self.assertTrue(source.ok)
        self.assertIn(("summary", CONVERSATION_ID, True), fake_store.calls)
        self.assertIn(("read", CONVERSATION_ID, ""), fake_store.calls)
        self.assertIn("Question relue", source.content)
        self.assertIn("Reponse relue", source.content)
        self.assertNotIn("system prompt interdit", source.content)
        self.assertNotIn("payload outil interdit", source.content)
        self.assertNotIn("private_meta", source.content)
        self.assertTrue(source.source_ref.startswith("conversation:22222222:"))

    def test_conversation_source_with_reader_ignores_payload_messages(self) -> None:
        def reader(payload):
            return {
                "ok": True,
                "conversation_id": payload["conversation_id"],
                "title": "Conversation relue",
                "messages": [
                    {"id": "u-store", "role": "user", "content": "Question store"},
                    {"id": "a-store", "role": "assistant", "content": "Reponse store"},
                ],
            }

        source = workspace_folder_export_sources.acquire_export_source(
            {
                "source_kind": "conversation",
                "explicit_source": True,
                "conversation_id": CONVERSATION_ID,
                "messages": [
                    {"id": "u-injected", "role": "user", "content": "Message payload"},
                ],
            },
            conversation_reader=reader,
        )

        self.assertTrue(source.ok)
        self.assertIn("Question store", source.content)
        self.assertIn("Reponse store", source.content)
        self.assertNotIn("Message payload", source.content)

    def test_conversation_store_reader_refuses_deleted_incomplete_or_failed_reads(self) -> None:
        deleted = workspace_folder_export_conversation_store.read_conversation_source(
            {"conversation_id": CONVERSATION_ID},
            conv_store_module=_FakeConversationStore(
                summary={"id": CONVERSATION_ID, "message_count": 1, "deleted_at": "2026-06-18T10:00:00Z"},
                conversation={"messages": [{"role": "user", "content": "ignore"}]},
            ),
        )
        incomplete = workspace_folder_export_conversation_store.read_conversation_source(
            {"conversation_id": CONVERSATION_ID},
            conv_store_module=_FakeConversationStore(
                summary={"id": CONVERSATION_ID, "message_count": 2, "deleted_at": None},
                conversation={"messages": [{"role": "user", "content": "only one"}]},
            ),
        )
        failed = workspace_folder_export_conversation_store.read_conversation_source(
            {"conversation_id": CONVERSATION_ID},
            conv_store_module=_FakeConversationStore(summary="raise"),
        )
        invalid = workspace_folder_export_conversation_store.read_conversation_source(
            {"conversation_id": "not-a-uuid"},
            conv_store_module=_FakeConversationStore(normalized=None),
        )

        self.assertEqual(deleted["reason_code"], "folder_export_source_unavailable")
        self.assertEqual(incomplete["reason_code"], "folder_export_source_read_unavailable")
        self.assertEqual(failed["reason_code"], "folder_export_source_read_unavailable")
        self.assertEqual(invalid["reason_code"], "folder_export_source_unavailable")
        self.assertNotIn("ignore", str(deleted))
        self.assertNotIn("only one", str(incomplete))

    def test_explicit_flag_must_be_strict_boolean_true(self) -> None:
        for value in ("false", "0", "no", "yes", "arbitrary", ["true"], {"ok": True}, 1):
            with self.subTest(value=value):
                source = workspace_folder_export_sources.acquire_export_source(
                    {
                        "source_kind": "conversation",
                        "explicit_source": value,
                        "messages": [{"id": "u1", "role": "user", "content": "Bonjour"}],
                    }
                )

                self.assertFalse(source.ok)
                self.assertEqual(source.reason_code, "folder_export_source_ambiguous")

    def test_explicit_boolean_true_is_accepted(self) -> None:
        source = workspace_folder_export_sources.acquire_export_source(
            {
                "source_kind": "conversation",
                "explicit_source": True,
                "messages": [{"id": "u1", "role": "user", "content": "Bonjour"}],
            }
        )

        self.assertTrue(source.ok)
        self.assertIn("Bonjour", source.content)

    def test_message_selection_requires_explicit_ids_and_preserves_conversation_order(self) -> None:
        source = workspace_folder_export_sources.acquire_export_source(
            {
                "source_kind": "message_selection",
                "explicit": True,
                "selected_message_ids": ["a1", "u2"],
                "messages": [
                    {"id": "u1", "role": "user", "content": "ignore"},
                    {"id": "a1", "role": "assistant", "content": "first selected"},
                    {"id": "u2", "role": "user", "content": "second selected"},
                ],
            }
        )

        self.assertTrue(source.ok)
        self.assertLess(source.content.index("first selected"), source.content.index("second selected"))
        self.assertNotIn("ignore", source.content)
        self.assertTrue(source.source_ref.startswith("message-selection:redacted:"))

    def test_frida_response_must_be_explicitly_designated(self) -> None:
        implicit = workspace_folder_export_sources.acquire_export_source(
            {
                "source_kind": "frida_response",
                "explicit": True,
                "messages": [{"id": "a1", "role": "assistant", "content": "last answer"}],
            }
        )
        explicit = workspace_folder_export_sources.acquire_export_source(
            {
                "source_kind": "frida_response",
                "explicit": True,
                "response_message_id": "a1",
                "messages": [{"id": "a1", "role": "assistant", "content": "chosen answer"}],
            }
        )

        self.assertFalse(implicit.ok)
        self.assertEqual(implicit.reason_code, "folder_export_source_missing")
        self.assertTrue(explicit.ok)
        self.assertEqual(explicit.content, "chosen answer")

    def test_note_source_uses_injected_reader_only(self) -> None:
        calls = []

        def reader(payload):
            calls.append(payload["note_id"])
            return {
                "ok": True,
                "title": "Note utile",
                "note_conversation": {"markdown_content": "Contenu note complet"},
            }

        missing_reader = workspace_folder_export_sources.acquire_export_source(
            {"source_kind": "note", "explicit": True, "note_id": "note-1"}
        )
        source = workspace_folder_export_sources.acquire_export_source(
            {"source_kind": "note", "explicit": True, "note_id": "note-1"},
            note_reader=reader,
        )

        self.assertFalse(missing_reader.ok)
        self.assertEqual(missing_reader.reason_code, "folder_export_source_read_unavailable")
        self.assertTrue(source.ok)
        self.assertEqual(calls, ["note-1"])
        self.assertEqual(source.content, "Contenu note complet")
        self.assertTrue(source.source_ref.startswith("workspace-note:redacted:"))

    def test_document_source_without_reader_is_not_prepared(self) -> None:
        source = workspace_folder_export_sources.acquire_export_source(
            {"source_kind": "document", "explicit": True, "document_id": "doc-1"}
        )

        self.assertFalse(source.ok)
        self.assertEqual(source.reason_code, "folder_export_source_not_prepared")

    def test_existing_export_source_without_reader_is_refused(self) -> None:
        source = workspace_folder_export_sources.acquire_export_source(
            {"source_kind": "export", "explicit": True, "export_id": "export-1"}
        )

        self.assertFalse(source.ok)
        self.assertEqual(source.reason_code, "folder_export_source_read_unavailable")

    def test_source_too_large_is_refused_without_truncation(self) -> None:
        source = workspace_folder_export_sources.acquire_export_source(
            {
                "source_kind": "conversation",
                "explicit": True,
                "messages": [
                    {
                        "id": "u1",
                        "role": "user",
                        "content": "a" * (workspace_folder_export_sources.SOURCE_TEXT_MAX_CHARS + 1),
                    }
                ],
            }
        )

        self.assertFalse(source.ok)
        self.assertEqual(source.reason_code, "folder_export_source_read_too_large")
        self.assertEqual(source.content, "")
        self.assertGreater(source.counters["char_count"], workspace_folder_export_sources.SOURCE_TEXT_MAX_CHARS)

    def test_content_free_projection_never_contains_source_content(self) -> None:
        source = workspace_folder_export_sources.acquire_export_source(
            {
                "source_kind": "conversation",
                "explicit": True,
                "messages": [{"id": "u1", "role": "user", "content": "contenu sensible"}],
            }
        )

        projection = source.content_free_projection()
        self.assertNotIn("content", projection)
        self.assertNotIn("contenu sensible", str(projection))


if __name__ == "__main__":
    unittest.main()
