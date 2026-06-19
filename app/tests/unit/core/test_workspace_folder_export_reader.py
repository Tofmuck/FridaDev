from __future__ import annotations

import unittest

from core import workspace_folder_export_nextcloud_client
from core import workspace_folder_export_reader
from core import workspace_folder_exports


FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
OTHER_FOLDER_ID = "bbbbbbbb-bbbb-4ccc-8ddd-ffffffffffff"
EXPORT_ID = "11111111-2222-4333-8444-555555555555"


class _FakeExportsModule:
    def __init__(self, export=None, *, fail_get=False):
        self.export = export
        self.fail_get = fail_get
        self.get_calls = []

    def get_export(self, export_id, *, fail_closed=True):
        self.get_calls.append({"export_id": export_id, "fail_closed": fail_closed})
        if self.fail_get:
            raise RuntimeError("raw db failure with raw-etag-secret")
        if not self.export:
            return None
        if workspace_folder_exports.normalize_export_id(self.export.get("id")) == export_id:
            return self.export
        return None


class _FakeNextcloud:
    def __init__(self, *, content=b"source text", fail_reason=""):
        self.content = bytes(content)
        self.fail_reason = fail_reason
        self.read_calls = []

    def read_export(self, folder_name, export_name, *, max_bytes):
        self.read_calls.append(
            {
                "folder_name": folder_name,
                "export_name": export_name,
                "max_bytes": max_bytes,
            }
        )
        if self.fail_reason:
            raise workspace_folder_export_nextcloud_client.NextcloudExportClientError(
                self.fail_reason,
                http_status=200 if self.fail_reason == workspace_folder_exports.REASON_TOO_LARGE else 503,
            )
        return workspace_folder_export_nextcloud_client.NextcloudExportReadResponse(
            True,
            workspace_folder_exports.REASON_DOWNLOAD_OK,
            200,
            content=self.content,
        )


def _folder(**overrides):
    payload = {
        "id": FOLDER_ID,
        "display_name": "Projet lecteur",
        "nextcloud_target_name": "Projet-lecteur",
        "nextcloud_sync_state": "linked",
        "deleted_at": None,
    }
    payload.update(overrides)
    return payload


def _export(**overrides):
    payload = {
        "id": EXPORT_ID,
        "workspace_folder_id": FOLDER_ID,
        "title": "Source sensible",
        "target_name": "Source-sensible.md",
        "export_format": "md",
        "local_state": "available",
        "nextcloud_sync_state": "linked",
        "deleted_at": None,
        "etag_value": '"raw-etag-secret"',
    }
    payload.update(overrides)
    return payload


def _payload(**overrides):
    payload = {
        "workspace_folder_id": FOLDER_ID,
        "source_kind": "export",
        "source_export_id": EXPORT_ID,
        "explicit_source": True,
    }
    payload.update(overrides)
    return payload


class WorkspaceFolderExportReaderTests(unittest.TestCase):
    def test_md_source_reads_exact_persisted_target(self) -> None:
        exports = _FakeExportsModule(_export())
        nextcloud = _FakeNextcloud(content=b"# Source\n\ntexte source")

        result = workspace_folder_export_reader.read_export_source(
            _payload(),
            folder=_folder(),
            workspace_folder_exports_module=exports,
            nextcloud=nextcloud,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["reason_code"], "folder_export_reuse_ok")
        self.assertEqual(result["export_content"], "# Source\n\ntexte source")
        self.assertEqual(
            nextcloud.read_calls,
            [
                {
                    "folder_name": "Projet-lecteur",
                    "export_name": "Source-sensible.md",
                    "max_bytes": workspace_folder_export_reader.SOURCE_EXPORT_MAX_BYTES,
                }
            ],
        )
        self.assertEqual(exports.get_calls[0]["export_id"], EXPORT_ID)

    def test_txt_source_is_supported(self) -> None:
        result = workspace_folder_export_reader.read_export_source(
            _payload(),
            folder=_folder(),
            workspace_folder_exports_module=_FakeExportsModule(
                _export(target_name="Source-sensible.txt", export_format="txt")
            ),
            nextcloud=_FakeNextcloud(content=b"texte source"),
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["source_format"], "txt")

    def test_missing_or_invalid_source_id_is_refused_before_store(self) -> None:
        exports = _FakeExportsModule(_export())
        nextcloud = _FakeNextcloud()

        result = workspace_folder_export_reader.read_export_source(
            _payload(source_export_id="not-a-uuid"),
            folder=_folder(),
            workspace_folder_exports_module=exports,
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "folder_export_source_missing")
        self.assertEqual(exports.get_calls, [])
        self.assertEqual(nextcloud.read_calls, [])

    def test_source_absent_deleted_cross_folder_or_non_linked_is_refused(self) -> None:
        cases = (
            (None, "folder_export_not_found"),
            (_export(local_state="deleted", deleted_at="2026-06-19T12:00:00Z"), "folder_export_deleted"),
            (_export(workspace_folder_id=OTHER_FOLDER_ID), "folder_export_not_found"),
            (_export(local_state="sync_error"), "folder_export_not_linked"),
            (_export(nextcloud_sync_state="sync_error"), "folder_export_not_linked"),
        )
        for export, reason in cases:
            with self.subTest(reason=reason):
                nextcloud = _FakeNextcloud()
                result = workspace_folder_export_reader.read_export_source(
                    _payload(),
                    folder=_folder(),
                    workspace_folder_exports_module=_FakeExportsModule(export),
                    nextcloud=nextcloud,
                )

                self.assertFalse(result["ok"])
                self.assertEqual(result["reason_code"], reason)
                self.assertEqual(nextcloud.read_calls, [])
                self.assertNotIn("raw-etag-secret", str(result))

    def test_docx_pdf_and_unknown_formats_are_refused_before_nextcloud(self) -> None:
        cases = (
            _export(target_name="Source-sensible.docx", export_format="docx"),
            _export(target_name="Source-sensible.pdf", export_format="pdf"),
            _export(target_name="Source-sensible.bin", export_format="bin"),
        )
        for export in cases:
            with self.subTest(format=export["export_format"]):
                nextcloud = _FakeNextcloud()
                result = workspace_folder_export_reader.read_export_source(
                    _payload(),
                    folder=_folder(),
                    workspace_folder_exports_module=_FakeExportsModule(export),
                    nextcloud=nextcloud,
                )

                self.assertFalse(result["ok"])
                self.assertEqual(
                    result["reason_code"],
                    "folder_export_source_format_unsupported",
                )
                self.assertEqual(nextcloud.read_calls, [])

    def test_too_large_non_utf8_store_and_nextcloud_failures_are_fail_closed(self) -> None:
        cases = (
            (
                _FakeExportsModule(_export(), fail_get=True),
                _FakeNextcloud(),
                "folder_export_lookup_failed",
            ),
            (
                _FakeExportsModule(_export()),
                _FakeNextcloud(fail_reason=workspace_folder_exports.REASON_TOO_LARGE),
                "folder_export_source_read_too_large",
            ),
            (
                _FakeExportsModule(_export()),
                _FakeNextcloud(fail_reason=workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE),
                "folder_export_source_read_unavailable",
            ),
            (
                _FakeExportsModule(_export()),
                _FakeNextcloud(content=b"\xff\xfe"),
                "folder_export_source_read_unavailable",
            ),
            (
                _FakeExportsModule(_export()),
                _FakeNextcloud(content=("x" * (workspace_folder_export_reader.SOURCE_EXPORT_MAX_CHARS + 1)).encode("utf-8")),
                "folder_export_source_read_too_large",
            ),
        )
        for exports, nextcloud, reason in cases:
            with self.subTest(reason=reason):
                result = workspace_folder_export_reader.read_export_source(
                    _payload(),
                    folder=_folder(),
                    workspace_folder_exports_module=exports,
                    nextcloud=nextcloud,
                )

                self.assertFalse(result["ok"])
                self.assertEqual(result["reason_code"], reason)
                self.assertNotIn("source text", str(result))
                self.assertNotIn("raw-etag-secret", str(result))


if __name__ == "__main__":
    unittest.main()
