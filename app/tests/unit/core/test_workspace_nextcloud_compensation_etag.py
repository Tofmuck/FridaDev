from __future__ import annotations

import unittest

from core import workspace_document_nextcloud_client as document_client
from core import workspace_folder_export_nextcloud_client as export_client
from core import workspace_folder_exports
from core import workspace_folder_generated_image_nextcloud_client as image_client
from core import workspace_folder_generated_images
from core import workspace_folder_note_nextcloud_client as note_client
from core import workspace_folder_notes


class _SyntheticTransportClient:
    client_error_type: type[RuntimeError]

    def __init__(
        self,
        status: int,
        *,
        response_etag: str = "",
        transport_error: bool = False,
    ) -> None:
        self.status = status
        self.response_etag = response_etag
        self.transport_error = transport_error
        self.transport_calls: list[tuple[str, dict[str, str]]] = []

    def _url(self, *segments: str) -> str:
        return "synthetic://redacted"

    def _request_status(
        self,
        method: str,
        url: str,
        *,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, str]:
        self.transport_calls.append((method, dict(headers or {})))
        if self.transport_error:
            raise self.client_error_type("synthetic_transport_error", http_status=503)
        return self.status, self.response_etag


class _DocumentClient(_SyntheticTransportClient, document_client.NextcloudDocumentClient):
    client_error_type = document_client.NextcloudDocumentClientError


class _NoteClient(_SyntheticTransportClient, note_client.NextcloudNoteClient):
    client_error_type = note_client.NextcloudNoteClientError


class _ExportClient(_SyntheticTransportClient, export_client.NextcloudExportClient):
    client_error_type = export_client.NextcloudExportClientError


class _ImageClient(_SyntheticTransportClient, image_client.NextcloudGeneratedImageClient):
    client_error_type = image_client.NextcloudGeneratedImageClientError


CLIENT_CASES = (
    {
        "family": "documents",
        "client_type": _DocumentClient,
        "client_error_type": document_client.NextcloudDocumentClientError,
        "put_method": "put_document",
        "delete_method": "delete_created_document_if_match",
        "generic_delete_method": "delete_document",
        "target_name": "synthetic.txt",
        "ownership_reason": document_client.REASON_REMOTE_COMPENSATION_OWNERSHIP_UNVERIFIED,
        "missing_reason": document_client.REASON_REMOTE_COMPENSATION_MISSING,
        "precondition_reason": document_client.REASON_REMOTE_COMPENSATION_PRECONDITION_FAILED,
        "failed_reason": document_client.REASON_REMOTE_COMPENSATION_FAILED,
    },
    {
        "family": "notes",
        "client_type": _NoteClient,
        "client_error_type": note_client.NextcloudNoteClientError,
        "put_method": "put_note",
        "delete_method": "delete_created_note_if_match",
        "generic_delete_method": "delete_note",
        "target_name": "synthetic.md",
        "ownership_reason": workspace_folder_notes.REASON_REMOTE_COMPENSATION_OWNERSHIP_UNVERIFIED,
        "missing_reason": workspace_folder_notes.REASON_REMOTE_COMPENSATION_MISSING,
        "precondition_reason": workspace_folder_notes.REASON_REMOTE_COMPENSATION_PRECONDITION_FAILED,
        "failed_reason": workspace_folder_notes.REASON_REMOTE_COMPENSATION_FAILED,
    },
    {
        "family": "exports",
        "client_type": _ExportClient,
        "client_error_type": export_client.NextcloudExportClientError,
        "put_method": "put_export",
        "delete_method": "delete_created_export_if_match",
        "generic_delete_method": "delete_export",
        "target_name": "synthetic.txt",
        "ownership_reason": workspace_folder_exports.REASON_REMOTE_COMPENSATION_OWNERSHIP_UNVERIFIED,
        "missing_reason": workspace_folder_exports.REASON_REMOTE_COMPENSATION_MISSING,
        "precondition_reason": workspace_folder_exports.REASON_REMOTE_COMPENSATION_PRECONDITION_FAILED,
        "failed_reason": workspace_folder_exports.REASON_REMOTE_COMPENSATION_FAILED,
    },
    {
        "family": "images",
        "client_type": _ImageClient,
        "client_error_type": image_client.NextcloudGeneratedImageClientError,
        "put_method": "put_image",
        "delete_method": "delete_created_image_if_match",
        "generic_delete_method": "delete_image",
        "target_name": "synthetic.png",
        "ownership_reason": workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_OWNERSHIP_UNVERIFIED,
        "missing_reason": workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_MISSING,
        "precondition_reason": workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_PRECONDITION_FAILED,
        "failed_reason": workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_FAILED,
    },
)


INVALID_OWNERSHIP_ETAGS = (
    "*",
    'W/"weak"',
    '"a", "b"',
    "unquoted",
    "",
    "   ",
    '"unterminated',
    '"contains\x1fcontrol"',
    '"contains\x7fdelete"',
    '"unicode-\u0100"',
    ' "surrounded-by-whitespace"',
    '"' + ("x" * 511) + '"',
)


class WorkspaceNextcloudCompensationEtagTests(unittest.TestCase):
    def test_strong_etag_from_current_put_is_preserved_and_sent_exactly(self) -> None:
        etag = '"created-version"'
        for case in CLIENT_CASES:
            with self.subTest(family=case["family"]):
                client = case["client_type"](201, response_etag=etag)
                created = getattr(client, case["put_method"])(
                    "SyntheticFolder",
                    case["target_name"],
                    b"synthetic",
                )
                self.assertEqual(created.etag_value, etag)

                client.status = 204
                client.transport_calls.clear()
                deleted = getattr(client, case["delete_method"])(
                    "SyntheticFolder",
                    case["target_name"],
                    etag_value=created.etag_value,
                )

                self.assertTrue(deleted.ok)
                self.assertEqual(
                    client.transport_calls,
                    [("DELETE", {"If-Match": etag})],
                )

    def test_valid_strong_etag_at_existing_bound_is_accepted(self) -> None:
        etag = '"' + ("x" * 510) + '"'
        for case in CLIENT_CASES:
            with self.subTest(family=case["family"]):
                client = case["client_type"](204)

                getattr(client, case["delete_method"])(
                    "SyntheticFolder",
                    case["target_name"],
                    etag_value=etag,
                )

                self.assertEqual(
                    client.transport_calls,
                    [("DELETE", {"If-Match": etag})],
                )

    def test_non_owning_etags_are_rejected_before_transport(self) -> None:
        for case in CLIENT_CASES:
            for etag in INVALID_OWNERSHIP_ETAGS:
                with self.subTest(family=case["family"], etag=repr(etag)):
                    client = case["client_type"](204)

                    with self.assertRaises(case["client_error_type"]) as refused:
                        getattr(client, case["delete_method"])(
                            "SyntheticFolder",
                            case["target_name"],
                            etag_value=etag,
                        )

                    self.assertEqual(refused.exception.reason_code, case["ownership_reason"])
                    self.assertEqual(client.transport_calls, [])

    def test_put_does_not_expose_non_owning_etags_for_compensation(self) -> None:
        for case in CLIENT_CASES:
            for etag in INVALID_OWNERSHIP_ETAGS:
                with self.subTest(family=case["family"], etag=repr(etag)):
                    client = case["client_type"](201, response_etag=etag)

                    created = getattr(client, case["put_method"])(
                        "SyntheticFolder",
                        case["target_name"],
                        b"synthetic",
                    )

                    self.assertEqual(created.etag_value, "")

    def test_conditional_delete_keeps_404_412_and_transport_classifications(self) -> None:
        etag = '"created-version"'
        for case in CLIENT_CASES:
            with self.subTest(family=case["family"], outcome="404"):
                missing_client = case["client_type"](404)
                missing = getattr(missing_client, case["delete_method"])(
                    "SyntheticFolder",
                    case["target_name"],
                    etag_value=etag,
                )
                self.assertEqual(missing.reason_code, case["missing_reason"])

            with self.subTest(family=case["family"], outcome="412"):
                refused_client = case["client_type"](412)
                with self.assertRaises(case["client_error_type"]) as refused:
                    getattr(refused_client, case["delete_method"])(
                        "SyntheticFolder",
                        case["target_name"],
                        etag_value=etag,
                    )
                self.assertEqual(refused.exception.reason_code, case["precondition_reason"])

            with self.subTest(family=case["family"], outcome="transport_error"):
                failed_client = case["client_type"](0, transport_error=True)
                with self.assertRaises(case["client_error_type"]) as failed:
                    getattr(failed_client, case["delete_method"])(
                        "SyntheticFolder",
                        case["target_name"],
                        etag_value=etag,
                    )
                self.assertEqual(failed.exception.reason_code, case["failed_reason"])

    def test_generic_delete_path_remains_unconditional(self) -> None:
        for case in CLIENT_CASES:
            with self.subTest(family=case["family"]):
                client = case["client_type"](204)

                deleted = getattr(client, case["generic_delete_method"])(
                    "SyntheticFolder",
                    case["target_name"],
                )

                self.assertTrue(deleted.ok)
                self.assertEqual(client.transport_calls, [("DELETE", {})])


if __name__ == "__main__":
    unittest.main()
