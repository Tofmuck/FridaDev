from __future__ import annotations

import unittest

from core import workspace_folder_export_generation
from core import workspace_folder_exports


FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
EXPORT_ID = "11111111-2222-4333-8444-555555555555"


def _conversation_request(**overrides):
    payload = {
        "workspace_folder_id": FOLDER_ID,
        "export_id": EXPORT_ID,
        "export_format": "md",
        "title": "Synthese",
        "source_kind": "conversation",
        "explicit_source": True,
        "conversation_id": "22222222-3333-4444-8555-666666666666",
        "messages": [
            {"id": "u1", "role": "user", "content": "Question utile"},
            {"id": "a1", "role": "assistant", "content": "Reponse utile"},
        ],
    }
    payload.update(overrides)
    return payload


class WorkspaceFolderExportGenerationTests(unittest.TestCase):
    def test_generates_markdown_conversation_complete_metadata_only(self) -> None:
        result = workspace_folder_export_generation.generate_workspace_folder_export(
            _conversation_request()
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["export_format"], "md")
        self.assertIn("# Synthese", result["export_content"])
        self.assertIn("Question utile", result["export_content"])
        technical = result["export_v1_technical"]
        self.assertEqual(technical["nextcloud_sync_state"], workspace_folder_exports.EXPORT_NEXTCLOUD_SYNC_ERROR)
        self.assertEqual(technical["reason_code"], "folder_export_create_ok")
        self.assertTrue(technical["source_ref"].startswith("conversation:22222222:"))
        technical_text = str(technical)
        self.assertNotIn("Question utile", technical_text)
        self.assertNotIn("Reponse utile", technical_text)
        metadata_text = str(result["export_v1_metadata"])
        self.assertNotIn("export_content", metadata_text)
        self.assertNotIn("Question utile", metadata_text)

    def test_generates_txt_conversation_without_markdown_heading_marker(self) -> None:
        result = workspace_folder_export_generation.generate_workspace_folder_export(
            _conversation_request(export_format="txt")
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["export_format"], "txt")
        self.assertIn("Synthese", result["export_content"])
        self.assertNotIn("# Synthese", result["export_content"])
        self.assertIn("Question utile", result["export_content"])

    def test_message_selection_and_frida_response_sources_are_explicit(self) -> None:
        selection = workspace_folder_export_generation.generate_workspace_folder_export(
            _conversation_request(
                source_kind="message_selection",
                selected_message_ids=["a1"],
                messages=[
                    {"id": "u1", "role": "user", "content": "Not selected"},
                    {"id": "a1", "role": "assistant", "content": "Selected answer"},
                ],
            )
        )
        response = workspace_folder_export_generation.generate_workspace_folder_export(
            _conversation_request(
                source_kind="frida_response",
                response_message_id="a1",
                messages=[
                    {"id": "u1", "role": "user", "content": "User message"},
                    {"id": "a1", "role": "assistant", "content": "Chosen response"},
                ],
            )
        )
        implicit = workspace_folder_export_generation.generate_workspace_folder_export(
            _conversation_request(
                source_kind="frida_response",
                response_message_id="",
                messages=[{"id": "a1", "role": "assistant", "content": "Should not be guessed"}],
            )
        )

        self.assertTrue(selection["ok"])
        self.assertIn("Selected answer", selection["export_content"])
        self.assertNotIn("Not selected", selection["export_content"])
        self.assertTrue(response["ok"])
        self.assertEqual(implicit["reason_code"], "folder_export_source_missing")
        self.assertEqual(implicit["export_content"], "")

    def test_note_and_document_sources_use_injected_capabilities(self) -> None:
        note_result = workspace_folder_export_generation.generate_workspace_folder_export(
            _conversation_request(source_kind="note", note_id="note-private-ref"),
            note_reader=lambda payload: {
                "ok": True,
                "title": "Note source",
                "note_conversation": {"markdown_content": "Texte note complet"},
            },
        )
        document_result = workspace_folder_export_generation.generate_workspace_folder_export(
            _conversation_request(source_kind="document", document_id="doc-private-ref"),
            document_reader=lambda payload: {
                "ok": True,
                "title": "Document source",
                "document_conversation": {"text_content": "Texte document complet"},
            },
        )

        self.assertTrue(note_result["ok"])
        self.assertIn("Texte note complet", note_result["export_content"])
        self.assertNotIn("note-private-ref", str(note_result["export_v1_technical"]))
        self.assertTrue(document_result["ok"])
        self.assertIn("Texte document complet", document_result["export_content"])
        self.assertNotIn("doc-private-ref", str(document_result["export_v1_technical"]))

    def test_document_and_export_without_reader_are_refused_cleanly(self) -> None:
        document_result = workspace_folder_export_generation.generate_workspace_folder_export(
            _conversation_request(source_kind="document", document_id="doc-private-ref")
        )
        export_result = workspace_folder_export_generation.generate_workspace_folder_export(
            _conversation_request(source_kind="export", export_id="export-private-ref")
        )

        self.assertFalse(document_result["ok"])
        self.assertEqual(document_result["reason_code"], "folder_export_source_not_prepared")
        self.assertEqual(document_result["export_content"], "")
        self.assertFalse(export_result["ok"])
        self.assertEqual(export_result["reason_code"], "folder_export_source_read_unavailable")

    def test_too_large_source_and_unsupported_format_are_refused_without_content(self) -> None:
        too_large = workspace_folder_export_generation.generate_workspace_folder_export(
            _conversation_request(
                messages=[
                    {
                        "id": "u1",
                        "role": "user",
                        "content": "a" * 120_001,
                    }
                ]
            )
        )
        unsupported = workspace_folder_export_generation.generate_workspace_folder_export(
            _conversation_request(export_format="pdf")
        )

        self.assertFalse(too_large["ok"])
        self.assertEqual(too_large["reason_code"], "folder_export_source_read_too_large")
        self.assertEqual(too_large["export_content"], "")
        self.assertFalse(unsupported["ok"])
        self.assertEqual(unsupported["reason_code"], "folder_export_format_unsupported")
        self.assertEqual(unsupported["export_content"], "")

    def test_private_source_ref_is_structured_not_copied_raw(self) -> None:
        result = workspace_folder_export_generation.generate_workspace_folder_export(
            _conversation_request(conversation_id="FlorenceBoitezPrivateConversation")
        )

        self.assertTrue(result["ok"])
        source_ref = result["export_v1_technical"]["source_ref"]
        self.assertTrue(source_ref.startswith("conversation:redacted:"))
        self.assertNotIn("FlorenceBoitezPrivateConversation", str(result["export_v1_technical"]))

    def test_generated_content_is_not_truncated_when_within_limit(self) -> None:
        exact = "x" * 1024
        result = workspace_folder_export_generation.generate_workspace_folder_export(
            _conversation_request(messages=[{"id": "u1", "role": "user", "content": exact}])
        )

        self.assertTrue(result["ok"])
        self.assertIn(exact, result["export_content"])


if __name__ == "__main__":
    unittest.main()
