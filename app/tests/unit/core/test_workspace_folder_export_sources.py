from __future__ import annotations

import unittest

from core import workspace_folder_export_sources


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
