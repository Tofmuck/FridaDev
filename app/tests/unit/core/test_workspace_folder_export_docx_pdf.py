from __future__ import annotations

import unittest
import zipfile
from io import BytesIO

from core import workspace_folder_export_docx_pdf
from core import workspace_folder_exports
from core.workspace_folder_export_sources import ExportSource


def _source(**overrides):
    payload = {
        "ok": True,
        "reason_code": workspace_folder_exports.REASON_LOOKUP_OK,
        "source_kind": workspace_folder_exports.SOURCE_CONVERSATION,
        "source_ref": "conversation:11111111:abc123def456",
        "source_hash": "abc123def456",
        "title": "Conversation synthese",
        "content": "## Utilisateur\n\nQuestion utile\n\n## Frida\n\nReponse utile",
        "char_count": 58,
        "counters": {"message_count": 2},
    }
    payload.update(overrides)
    return ExportSource(**payload)


class WorkspaceFolderExportDocxPdfTests(unittest.TestCase):
    def test_docx_renderer_builds_minimal_ooxml_in_memory(self) -> None:
        result = workspace_folder_export_docx_pdf.render_binary_export(
            workspace_folder_exports.EXPORT_FORMAT_DOCX,
            _source(),
            title="Synthese",
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.mime_type, workspace_folder_export_docx_pdf.DOCX_MIME_TYPE)
        self.assertGreater(len(result.content_bytes), 0)
        with zipfile.ZipFile(BytesIO(result.content_bytes)) as archive:
            names = set(archive.namelist())
            self.assertIn("[Content_Types].xml", names)
            self.assertIn("_rels/.rels", names)
            self.assertIn("word/document.xml", names)
            document_xml = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("Question utile", document_xml)
        self.assertIn("Reponse utile", document_xml)

    def test_pdf_renderer_builds_complete_pdf_in_memory(self) -> None:
        result = workspace_folder_export_docx_pdf.render_binary_export(
            workspace_folder_exports.EXPORT_FORMAT_PDF,
            _source(),
            title="Synthese",
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.mime_type, workspace_folder_export_docx_pdf.PDF_MIME_TYPE)
        self.assertGreater(len(result.content_bytes), 0)
        self.assertTrue(result.content_bytes.startswith(b"%PDF-1.4"))
        self.assertTrue(result.content_bytes.rstrip().endswith(b"%%EOF"))
        self.assertEqual(result.page_count, 1)

    def test_missing_dependency_is_refused_content_free(self) -> None:
        result = workspace_folder_export_docx_pdf.render_binary_export(
            workspace_folder_exports.EXPORT_FORMAT_PDF,
            _source(),
            title="Synthese",
            dependency_checker=lambda fmt: False,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "folder_export_dependency_unavailable")
        self.assertEqual(result.content_bytes, b"")

    def test_pdf_too_many_pages_refuses_without_partial_binary(self) -> None:
        result = workspace_folder_export_docx_pdf.render_binary_export(
            workspace_folder_exports.EXPORT_FORMAT_PDF,
            _source(content="\n".join(f"Ligne {index}" for index in range(5000))),
            title="Synthese",
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "folder_export_too_large")
        self.assertEqual(result.content_bytes, b"")

    def test_pdf_refuses_unsupported_text_without_lossy_replacement(self) -> None:
        result = workspace_folder_export_docx_pdf.render_binary_export(
            workspace_folder_exports.EXPORT_FORMAT_PDF,
            _source(content="Texte avec emoji non supporte \U0001f642"),
            title="Synthese",
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "folder_export_generation_failed_redacted")
        self.assertEqual(result.content_bytes, b"")

    def test_runtime_dependency_status_is_explicit(self) -> None:
        status = workspace_folder_export_docx_pdf.runtime_dependency_status()

        self.assertTrue(status[workspace_folder_exports.EXPORT_FORMAT_DOCX])
        self.assertTrue(status[workspace_folder_exports.EXPORT_FORMAT_PDF])


if __name__ == "__main__":
    unittest.main()
