from __future__ import annotations

import unittest

from core import workspace_folder_documents
from core import workspace_files_store


FOLDER_ID = "11111111-2222-4333-8444-555555555555"
FILE_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
LINKED_FOLDER = {"id": FOLDER_ID, "nextcloud_sync_state": "linked"}


def _file_item(**overrides):
    payload = {
        "id": FILE_ID,
        "workspace_folder_id": FOLDER_ID,
        "display_name": "note.txt",
        "content_kind": "document",
        "media_kind": "text",
        "mime_type": "text/plain",
        "source_extension": ".txt",
        "byte_size": 12,
        "sha256_12": "abc123def456",
        "text_chars": 12,
        "text_sha256_12": "def456abc123",
        "status": "active",
        "reason_code": "",
    }
    payload.update(overrides)
    return payload


class DocumentsV1ReadModelTests(unittest.TestCase):
    def test_user_projection_exposes_display_name_but_technical_projection_redacts_it(self) -> None:
        item = workspace_files_store.serialize_workspace_file_row(
            {
                **_file_item(),
                "display_name": "  Projet Tulu document.txt ",
                "original_filename": "../Projet Tulu document.txt",
                "storage_key": f"{FOLDER_ID}/{FILE_ID}.txt",
            }
        )

        projected = workspace_folder_documents.apply_document_v1_projection(item, folder=LINKED_FOLDER)

        user = projected["document_v1_user"]
        technical = projected["document_v1_technical"]
        self.assertEqual(user["display_name"], "Projet Tulu document.txt")
        self.assertEqual(user["document_status"], "readable")
        self.assertEqual(user["reason_code"], "folder_document_text_ready")
        self.assertEqual(technical["document_status"], "readable")
        self.assertEqual(technical["reason_code"], "folder_document_text_ready")
        self.assertIn("name_hash", technical)
        encoded_technical = str(technical)
        self.assertNotIn("Projet Tulu", encoded_technical)
        self.assertNotIn("display_name", encoded_technical)
        self.assertNotIn("original_filename", encoded_technical)
        self.assertNotIn("storage_key", encoded_technical)
        self.assertNotIn("remote.php", encoded_technical)
        self.assertNotIn("Authorization", encoded_technical)
        self.assertNotIn("Cookie", encoded_technical)
        self.assertNotIn("document.txt", encoded_technical)

    def test_technical_projection_normalizes_dangerous_mime_type(self) -> None:
        projected = workspace_folder_documents.apply_document_v1_projection(
            _file_item(mime_type="/Frida/Projet/document.pdf"),
            folder=LINKED_FOLDER,
        )

        technical = projected["document_v1_technical"]
        self.assertEqual(technical["mime_type"], "unknown")
        self.assertNotIn("/Frida", str(technical))
        self.assertNotIn("document.pdf", str(technical))

    def test_technical_projection_normalizes_dav_url_in_mime_type_and_extension(self) -> None:
        projected = workspace_folder_documents.apply_document_v1_projection(
            _file_item(
                mime_type="https://example.invalid/remote.php/dav/files/frida/doc.pdf",
                source_extension="https://example.invalid/remote.php/dav/files/frida/doc.pdf",
            ),
            folder=LINKED_FOLDER,
        )

        technical = projected["document_v1_technical"]
        self.assertEqual(technical["mime_type"], "unknown")
        self.assertEqual(technical["source_extension"], "")
        encoded = str(technical)
        self.assertNotIn("remote.php", encoded)
        self.assertNotIn("https://", encoded)
        self.assertNotIn("doc.pdf", encoded)

    def test_technical_projection_normalizes_suspect_content_and_media_kind(self) -> None:
        projected = workspace_folder_documents.apply_document_v1_projection(
            _file_item(content_kind="/Frida/Projet", media_kind="/Frida/Media"),
            folder=LINKED_FOLDER,
        )

        technical = projected["document_v1_technical"]
        self.assertEqual(technical["content_kind"], "unknown")
        self.assertEqual(technical["media_kind"], "unknown")
        encoded = str(technical)
        self.assertNotIn("/Frida", encoded)

    def test_technical_projection_redacts_non_uuid_identifiers(self) -> None:
        projected = workspace_folder_documents.apply_document_v1_projection(
            _file_item(id="SecretDocumentName", workspace_folder_id="ProjetTulu"),
            folder=LINKED_FOLDER,
        )

        technical = projected["document_v1_technical"]
        self.assertEqual(technical["workspace_file_id"], "")
        self.assertEqual(technical["workspace_folder_id"], "")
        self.assertTrue(technical["document_ref"].startswith("workspace-file:redacted:"))
        self.assertFalse(technical["document_ref"].startswith("workspace-file:SecretDo"))
        encoded = str(technical)
        self.assertNotIn("SecretDocumentName", encoded)
        self.assertNotIn("ProjetTulu", encoded)

        valid = workspace_folder_documents.apply_document_v1_projection(
            _file_item(id=FILE_ID, workspace_folder_id=FOLDER_ID),
            folder=LINKED_FOLDER,
        )["document_v1_technical"]
        self.assertEqual(valid["workspace_file_id"], FILE_ID)
        self.assertEqual(valid["workspace_folder_id"], FOLDER_ID)
        self.assertTrue(valid["document_ref"].startswith("workspace-file:aaaaaaaa:"))

    def test_parse_error_maps_to_error_status_and_parse_reason(self) -> None:
        projected = workspace_folder_documents.apply_document_v1_projection(
            _file_item(status="parse_error", reason_code="workspace_file_unreadable", text_chars=0),
            folder=LINKED_FOLDER,
        )

        self.assertEqual(projected["document_v1_status"], "error")
        self.assertEqual(projected["document_v1_readiness"], "blocked")
        self.assertEqual(projected["document_v1_reason_code"], "folder_document_parse_error")
        self.assertEqual(projected["document_v1_technical"]["reason_code"], "folder_document_parse_error")

    def test_valid_text_pdf_visual_and_image_statuses_remain_stable(self) -> None:
        text = workspace_folder_documents.apply_document_v1_projection(
            _file_item(mime_type="text/plain", source_extension=".txt", text_chars=12),
            folder=LINKED_FOLDER,
        )
        pdf_text = workspace_folder_documents.apply_document_v1_projection(
            _file_item(mime_type="application/pdf", source_extension=".pdf", text_chars=12),
            folder=LINKED_FOLDER,
        )
        pdf_visual = workspace_folder_documents.apply_document_v1_projection(
            _file_item(mime_type="application/pdf", source_extension=".pdf", text_chars=0, status="ocr_required"),
            folder=LINKED_FOLDER,
        )
        image = workspace_folder_documents.apply_document_v1_projection(
            _file_item(content_kind="image", media_kind="image", mime_type="image/png", source_extension=".png"),
            folder=LINKED_FOLDER,
        )

        self.assertEqual(text["document_v1_status"], "readable")
        self.assertEqual(pdf_text["document_v1_status"], "pdf_text")
        self.assertEqual(pdf_visual["document_v1_status"], "pdf_visual_required")
        self.assertEqual(image["document_v1_status"], "visual_ready")
        self.assertEqual(image["document_v1_technical"]["mime_type"], "image/png")
        self.assertEqual(image["document_v1_technical"]["source_extension"], ".png")

    def test_projection_marks_non_linked_folder_unavailable_content_free(self) -> None:
        projected = workspace_folder_documents.apply_document_v1_projection(
            _file_item(display_name="note.txt"),
            folder={"id": FOLDER_ID, "nextcloud_sync_state": "sync_error"},
        )

        self.assertEqual(projected["document_v1_status"], "unavailable")
        self.assertEqual(projected["document_v1_readiness"], "blocked")
        self.assertEqual(projected["document_v1_reason_code"], "folder_document_folder_not_linked")
        self.assertEqual(projected["document_v1_technical"]["reason_code"], "folder_document_folder_not_linked")

    def test_projection_marks_linked_document_nextcloud_state_without_raw_target_name(self) -> None:
        projected = workspace_folder_documents.apply_document_v1_projection(
            _file_item(
                storage_key="hidden/path/note.txt",
                document_nextcloud_link={
                    "lookup_state": "ok",
                    "nextcloud_sync_state": "linked",
                    "nextcloud_document_ref": "workspace-file:aaaaaaaa:abc123def456",
                    "nextcloud_name_hash": "abc123def456",
                    "nextcloud_target_name": "Projet secret.txt",
                    "last_sync_reason_code": "folder_document_upload_ok",
                    "last_sync_operation": "upload",
                }
            ),
            folder=LINKED_FOLDER,
        )

        user = projected["document_v1_user"]
        technical = projected["document_v1_technical"]
        self.assertEqual(user["nextcloud_sync_state"], "linked")
        self.assertEqual(user["nextcloud_status_label"], "Range Nextcloud")
        self.assertEqual(technical["nextcloud_sync_state"], "linked")
        self.assertEqual(technical["nextcloud_document_ref"], "workspace-file:aaaaaaaa:abc123def456")
        self.assertEqual(technical["nextcloud_name_hash"], "abc123def456")
        self.assertEqual(technical["nextcloud_reason_code"], "folder_document_upload_ok")
        self.assertEqual(projected["display_name"], "note.txt")
        self.assertNotIn("storage_key", projected)
        self.assertNotIn("document_nextcloud_link", projected)
        encoded_technical = str(technical)
        self.assertNotIn("Projet secret.txt", encoded_technical)
        self.assertNotIn("nextcloud_target_name", encoded_technical)
        self.assertNotIn("note.txt", encoded_technical)

    def test_projection_marks_local_only_documents_honestly(self) -> None:
        projected = workspace_folder_documents.apply_document_v1_projection(_file_item(), folder=LINKED_FOLDER)

        self.assertEqual(projected["document_v1_user"]["nextcloud_sync_state"], "local_only")
        self.assertEqual(projected["document_v1_user"]["nextcloud_status_label"], "Local seulement")
        self.assertEqual(projected["document_v1_technical"]["nextcloud_sync_state"], "local_only")
        self.assertEqual(
            projected["document_v1_technical"]["nextcloud_reason_code"],
            "folder_document_local_only",
        )

    def test_projection_marks_link_lookup_failure_content_free(self) -> None:
        projected = workspace_folder_documents.apply_document_v1_projection(
            _file_item(
                document_nextcloud_link={
                    "lookup_state": "failed",
                    "reason_code": "folder_document_link_lookup_failed",
                    "nextcloud_target_name": "Projet secret.txt",
                }
            ),
            folder=LINKED_FOLDER,
        )

        self.assertEqual(projected["document_v1_user"]["nextcloud_sync_state"], "sync_error")
        self.assertEqual(projected["document_v1_user"]["nextcloud_reason_code"], "folder_document_link_lookup_failed")
        self.assertEqual(projected["document_v1_technical"]["nextcloud_sync_state"], "sync_error")
        self.assertEqual(
            projected["document_v1_technical"]["nextcloud_reason_code"],
            "folder_document_link_lookup_failed",
        )
        self.assertNotIn("Projet secret.txt", str(projected["document_v1_technical"]))

    def test_usage_projection_links_conversation_without_active_document_or_biblio(self) -> None:
        selection = {
            "conversation_id": "11111111-1111-4111-8111-111111111111",
            "workspace_file_id": "33333333-3333-4333-8333-333333333333",
            "workspace_folder_id": "22222222-2222-4222-8222-222222222222",
            "selected": True,
            "selection_status": "selected",
            "file": _file_item(
                id="33333333-3333-4333-8333-333333333333",
                workspace_folder_id="22222222-2222-4222-8222-222222222222",
            ),
        }

        projected = workspace_folder_documents.apply_selection_document_v1_projection(selection)

        self.assertEqual(projected["document_v1_usage"]["source"], "workspace_file_selection")
        self.assertEqual(projected["document_v1_usage"]["usage_status"], "selected")
        self.assertEqual(projected["document_v1_usage"]["reason_code"], "folder_document_selected")
        encoded = str(projected)
        self.assertNotIn("active_document", encoded)
        self.assertNotIn("library_document", encoded)
        self.assertNotIn("catalogue_document", encoded)
        self.assertNotIn("passage documentaire", encoded)

    def test_usage_projection_redacts_unknown_reason_code(self) -> None:
        projected = workspace_folder_documents.apply_selection_document_v1_projection(
            {
                "conversation_id": "11111111-1111-4111-8111-111111111111",
                "workspace_file_id": "33333333-3333-4333-8333-333333333333",
                "workspace_folder_id": "22222222-2222-4222-8222-222222222222",
                "selected": False,
                "selection_status": "stale",
                "reason_code": "/Frida/Projet-Tulu/document.txt",
            }
        )

        self.assertEqual(projected["document_v1_usage"]["reason_code"], "folder_document_content_redacted")
        self.assertNotIn("/Frida", str(projected["document_v1_usage"]))


if __name__ == "__main__":
    unittest.main()
