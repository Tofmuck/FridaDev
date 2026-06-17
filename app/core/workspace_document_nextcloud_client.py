from __future__ import annotations

import base64
import mimetypes
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from . import workspace_folder_nextcloud_client as folder_client


DOCUMENTS_SUBFOLDER = "Documents"

REASON_FOLDER_NOT_LINKED = "folder_document_folder_not_linked"
REASON_DOCUMENTS_TARGET_MISSING = "folder_document_documents_target_missing"
REASON_DOCUMENTS_TARGET_CONFLICT = "folder_document_documents_target_conflict"
REASON_DOCUMENTS_TARGET_UNAVAILABLE = "folder_document_documents_target_unavailable"
REASON_DOCUMENTS_TARGET_NOT_COLLECTION = "folder_document_documents_target_not_collection"
REASON_NAME_INVALID = "folder_document_name_invalid"
REASON_NAME_CONFLICT = "folder_document_name_conflict"
REASON_UPLOAD_OK = "folder_document_upload_ok"
REASON_RUNTIME_UNAVAILABLE = "folder_document_runtime_unavailable"
REASON_NEXTCLOUD_ERROR_REDACTED = "folder_document_nextcloud_error_redacted"
REASON_LOCAL_PERSISTENCE_FAILED = "folder_document_local_persistence_failed"
REASON_LINK_PERSISTENCE_FAILED = "folder_document_link_persistence_failed"
REASON_LINK_LOOKUP_FAILED = "folder_document_link_lookup_failed"
REASON_LINK_MISSING = "folder_document_link_missing"
REASON_LINK_MARK_FAILED = "folder_document_link_mark_failed"
REASON_DELETE_OK = "folder_document_delete_ok"
REASON_REMOTE_DELETE_FAILED = "folder_document_remote_delete_failed"
REASON_LOCAL_DELETE_FAILED = "folder_document_local_delete_failed"
REASON_REMOTE_COMPENSATION_OK = "folder_document_remote_compensation_ok"
REASON_REMOTE_COMPENSATION_FAILED = "folder_document_remote_compensation_failed"
REASON_EXISTING_COPY_REQUIRED = "folder_document_existing_copy_required"
REASON_EXISTING_COPY_OK = "folder_document_existing_copy_ok"
REASON_EXISTING_COPY_CONFLICT = "folder_document_existing_copy_conflict"
REASON_EXISTING_SOURCE_PRESERVED = "folder_document_existing_source_preserved"
REASON_EXISTING_SOURCE_MISSING = "folder_document_existing_source_missing"


@dataclass(frozen=True)
class NextcloudDocumentResponse:
    ok: bool
    reason_code: str
    http_status: int = 0

    @property
    def status_class(self) -> str:
        if self.http_status <= 0:
            return "none"
        return f"{self.http_status // 100}xx"


class NextcloudDocumentClientError(RuntimeError):
    def __init__(self, reason_code: str, *, http_status: int = 0):
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.http_status = int(http_status or 0)

    @property
    def status_class(self) -> str:
        if self.http_status <= 0:
            return "none"
        return f"{self.http_status // 100}xx"


class NextcloudDocumentClient:
    """Bounded WebDAV client for Documents V1 file placement."""

    def __init__(self, config: folder_client.NextcloudFolderClientConfig):
        self.config = config

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "NextcloudDocumentClient":
        try:
            config = folder_client.config_from_env(environ)
        except folder_client.NextcloudFolderClientError as exc:
            raise NextcloudDocumentClientError(
                _document_reason_for_folder_reason(exc.reason_code),
                http_status=exc.http_status,
            ) from None
        return cls(config)

    def documents_status(self, folder_name: str) -> NextcloudDocumentResponse:
        status, is_collection = self._request_collection_status(
            self._url(folder_name, DOCUMENTS_SUBFOLDER)
        )
        if status == 207 and is_collection:
            return NextcloudDocumentResponse(True, REASON_UPLOAD_OK, status)
        if status == 207:
            raise NextcloudDocumentClientError(
                REASON_DOCUMENTS_TARGET_NOT_COLLECTION,
                http_status=status,
            )
        raise NextcloudDocumentClientError(_documents_target_reason(status), http_status=status)

    def put_document(
        self,
        folder_name: str,
        document_name: str,
        content: bytes,
        *,
        media_type: str = "",
    ) -> NextcloudDocumentResponse:
        status = self._request_status(
            "PUT",
            self._url(folder_name, DOCUMENTS_SUBFOLDER, document_name),
            data=bytes(content or b""),
            headers={
                "If-None-Match": "*",
                "Content-Type": _safe_media_type(media_type),
            },
        )
        if status == 201:
            return NextcloudDocumentResponse(True, REASON_UPLOAD_OK, status)
        if status in {200, 204}:
            raise NextcloudDocumentClientError(REASON_NAME_CONFLICT, http_status=status)
        raise NextcloudDocumentClientError(_document_write_reason(status), http_status=status)

    def document_status(self, folder_name: str, document_name: str) -> NextcloudDocumentResponse:
        status = self._request_status(
            "PROPFIND",
            self._url(folder_name, DOCUMENTS_SUBFOLDER, document_name),
            headers={"Depth": "0"},
        )
        if status == 207:
            return NextcloudDocumentResponse(True, REASON_UPLOAD_OK, status)
        raise NextcloudDocumentClientError(_document_write_reason(status), http_status=status)

    def delete_document(
        self,
        folder_name: str,
        document_name: str,
        *,
        missing_ok: bool = True,
    ) -> NextcloudDocumentResponse:
        status = self._request_status(
            "DELETE",
            self._url(folder_name, DOCUMENTS_SUBFOLDER, document_name),
        )
        if status in {200, 202, 204} or (missing_ok and status == 404):
            return NextcloudDocumentResponse(True, REASON_DELETE_OK, status)
        raise NextcloudDocumentClientError(
            REASON_REMOTE_DELETE_FAILED,
            http_status=status,
        )

    def _url(self, *segments: str) -> str:
        parts = [self.config.root_name, *[segment for segment in segments if segment]]
        encoded = "/".join(quote(part.strip("/"), safe="") for part in parts)
        user = quote(self.config.username, safe="")
        return f"{self.config.base_url}/remote.php/dav/files/{user}/{encoded}"

    def _request_collection_status(self, url: str) -> tuple[int, bool]:
        request = Request(url, method="PROPFIND")
        request.add_header("Authorization", self._authorization_header())
        request.add_header("Depth", "0")
        try:
            with urlopen(request, timeout=12) as response:
                status = int(response.status)
                if status != 207:
                    return status, False
                body = response.read()
        except HTTPError as exc:
            return int(exc.code or 0), False
        except (OSError, URLError):
            raise NextcloudDocumentClientError(REASON_DOCUMENTS_TARGET_UNAVAILABLE) from None
        return 207, folder_client._propfind_body_is_collection(body)

    def _request_status(
        self,
        method: str,
        url: str,
        *,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> int:
        request = Request(url, data=data, method=method)
        request.add_header("Authorization", self._authorization_header())
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        try:
            with urlopen(request, timeout=12) as response:
                return int(response.status)
        except HTTPError as exc:
            return int(exc.code or 0)
        except (OSError, URLError):
            raise NextcloudDocumentClientError(REASON_DOCUMENTS_TARGET_UNAVAILABLE) from None

    def _authorization_header(self) -> str:
        raw = f"{self.config.username}:{self.config.app_password}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")


def _document_reason_for_folder_reason(reason_code: str) -> str:
    if reason_code == folder_client.REASON_TARGET_MISSING:
        return REASON_DOCUMENTS_TARGET_MISSING
    if reason_code == folder_client.REASON_CONFLICT:
        return REASON_DOCUMENTS_TARGET_CONFLICT
    if reason_code in {folder_client.REASON_UNAVAILABLE, folder_client.REASON_AUTH_FAILED}:
        return REASON_DOCUMENTS_TARGET_UNAVAILABLE
    return REASON_NEXTCLOUD_ERROR_REDACTED


def _documents_target_reason(status: int) -> str:
    if status == 404:
        return REASON_DOCUMENTS_TARGET_MISSING
    if status in {401, 403} or status <= 0 or status >= 500:
        return REASON_DOCUMENTS_TARGET_UNAVAILABLE
    if status in {405, 409, 412, 423}:
        return REASON_DOCUMENTS_TARGET_CONFLICT
    return REASON_NEXTCLOUD_ERROR_REDACTED


def _document_write_reason(status: int) -> str:
    if status == 404:
        return REASON_DOCUMENTS_TARGET_MISSING
    if status in {401, 403} or status <= 0 or status >= 500:
        return REASON_DOCUMENTS_TARGET_UNAVAILABLE
    if status in {405, 409, 412, 423}:
        return REASON_NAME_CONFLICT
    return REASON_NEXTCLOUD_ERROR_REDACTED


def _safe_media_type(value: Any) -> str:
    text = " ".join(str(value or "").strip().split()).lower()
    if "/" in text and all(ch.isalnum() or ch in "!#$&^_.+-/" for ch in text):
        return text[:120]
    guessed = mimetypes.types_map.get(text)
    return guessed or "application/octet-stream"
