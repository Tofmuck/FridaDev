from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from . import workspace_folder_nextcloud_client as folder_client
from . import workspace_folder_notes


NOTES_SUBFOLDER = "Notes"
REASON_ETAG_MISSING = workspace_folder_notes.REASON_ETAG_MISSING
REASON_REMOTE_READ_FAILED = workspace_folder_notes.REASON_REMOTE_READ_FAILED
REASON_REMOTE_WRITE_FAILED = workspace_folder_notes.REASON_REMOTE_WRITE_FAILED


@dataclass(frozen=True)
class NextcloudNoteResponse:
    ok: bool
    reason_code: str
    http_status: int = 0
    etag_value: str = ""

    @property
    def status_class(self) -> str:
        if self.http_status <= 0:
            return "none"
        return f"{self.http_status // 100}xx"


@dataclass(frozen=True)
class NextcloudNoteContentResponse(NextcloudNoteResponse):
    markdown: str = ""


class NextcloudNoteClientError(RuntimeError):
    def __init__(self, reason_code: str, *, http_status: int = 0):
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.http_status = int(http_status or 0)

    @property
    def status_class(self) -> str:
        if self.http_status <= 0:
            return "none"
        return f"{self.http_status // 100}xx"


class NextcloudNoteClient:
    """Bounded WebDAV client for Notes V1 creation."""

    def __init__(self, config: folder_client.NextcloudFolderClientConfig):
        self.config = config

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "NextcloudNoteClient":
        try:
            config = folder_client.config_from_env(environ)
        except folder_client.NextcloudFolderClientError as exc:
            raise NextcloudNoteClientError(
                _note_reason_for_folder_reason(exc.reason_code),
                http_status=exc.http_status,
            ) from None
        return cls(config)

    def notes_status(self, folder_name: str) -> NextcloudNoteResponse:
        status, is_collection = self._request_collection_status(
            self._url(folder_name, NOTES_SUBFOLDER)
        )
        if status == 207 and is_collection:
            return NextcloudNoteResponse(True, workspace_folder_notes.REASON_CREATE_OK, status)
        if status == 207:
            raise NextcloudNoteClientError(
                workspace_folder_notes.REASON_NOTES_TARGET_NOT_COLLECTION,
                http_status=status,
            )
        raise NextcloudNoteClientError(_notes_target_reason(status), http_status=status)

    def put_note(
        self,
        folder_name: str,
        note_name: str,
        markdown: bytes,
    ) -> NextcloudNoteResponse:
        status, etag = self._request_status(
            "PUT",
            self._url(folder_name, NOTES_SUBFOLDER, note_name),
            data=bytes(markdown or b""),
            headers={
                "If-None-Match": "*",
                "Content-Type": "text/markdown; charset=utf-8",
            },
        )
        if status == 201:
            return NextcloudNoteResponse(
                True,
                workspace_folder_notes.REASON_CREATE_OK,
                status,
                etag_value=_safe_etag(etag),
            )
        if status in {200, 204}:
            raise NextcloudNoteClientError(
                workspace_folder_notes.REASON_NAME_CONFLICT,
                http_status=status,
            )
        raise NextcloudNoteClientError(_note_write_reason(status), http_status=status)

    def note_status(self, folder_name: str, note_name: str) -> NextcloudNoteResponse:
        status, _etag = self._request_status(
            "PROPFIND",
            self._url(folder_name, NOTES_SUBFOLDER, note_name),
            headers={"Depth": "0"},
        )
        if status == 207:
            return NextcloudNoteResponse(True, workspace_folder_notes.REASON_CREATE_OK, status)
        raise NextcloudNoteClientError(_note_write_reason(status), http_status=status)

    def get_note_content(
        self,
        folder_name: str,
        note_name: str,
        *,
        max_bytes: int,
    ) -> NextcloudNoteContentResponse:
        status, etag, body = self._request_body(
            "GET",
            self._url(folder_name, NOTES_SUBFOLDER, note_name),
            max_bytes=max_bytes,
        )
        if status == 200:
            try:
                markdown = body.decode("utf-8")
            except UnicodeDecodeError:
                raise NextcloudNoteClientError(REASON_REMOTE_READ_FAILED, http_status=status) from None
            return NextcloudNoteContentResponse(
                True,
                workspace_folder_notes.REASON_LOOKUP_OK,
                status,
                etag_value=_safe_etag(etag),
                markdown=markdown,
            )
        raise NextcloudNoteClientError(_note_read_reason(status), http_status=status)

    def put_note_if_match(
        self,
        folder_name: str,
        note_name: str,
        markdown: bytes,
        *,
        etag_value: str,
    ) -> NextcloudNoteResponse:
        etag = _safe_etag(etag_value)
        if not etag:
            raise NextcloudNoteClientError(REASON_ETAG_MISSING)
        status, response_etag = self._request_status(
            "PUT",
            self._url(folder_name, NOTES_SUBFOLDER, note_name),
            data=bytes(markdown or b""),
            headers={
                "If-Match": etag,
                "Content-Type": "text/markdown; charset=utf-8",
            },
        )
        if status in {200, 204}:
            return NextcloudNoteResponse(
                True,
                workspace_folder_notes.REASON_APPEND_OK,
                status,
                etag_value=_safe_etag(response_etag),
            )
        if status == 412:
            raise NextcloudNoteClientError(
                workspace_folder_notes.REASON_VERSION_CONFLICT,
                http_status=status,
            )
        raise NextcloudNoteClientError(_note_append_write_reason(status), http_status=status)

    def delete_note(
        self,
        folder_name: str,
        note_name: str,
        *,
        missing_ok: bool = True,
    ) -> NextcloudNoteResponse:
        status, _etag = self._request_status(
            "DELETE",
            self._url(folder_name, NOTES_SUBFOLDER, note_name),
        )
        if status in {200, 202, 204} or (missing_ok and status == 404):
            return NextcloudNoteResponse(
                True,
                workspace_folder_notes.REASON_REMOTE_COMPENSATION_OK,
                status,
            )
        raise NextcloudNoteClientError(
            workspace_folder_notes.REASON_REMOTE_COMPENSATION_FAILED,
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
            raise NextcloudNoteClientError(
                workspace_folder_notes.REASON_NOTES_TARGET_UNAVAILABLE
            ) from None
        return 207, folder_client._propfind_body_is_collection(body)

    def _request_status(
        self,
        method: str,
        url: str,
        *,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, str]:
        request = Request(url, data=data, method=method)
        request.add_header("Authorization", self._authorization_header())
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        try:
            with urlopen(request, timeout=12) as response:
                return int(response.status), str(response.headers.get("ETag") or "")
        except HTTPError as exc:
            return int(exc.code or 0), ""
        except (OSError, URLError):
            raise NextcloudNoteClientError(
                workspace_folder_notes.REASON_NOTES_TARGET_UNAVAILABLE
            ) from None

    def _request_body(
        self,
        method: str,
        url: str,
        *,
        max_bytes: int,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, str, bytes]:
        request = Request(url, method=method)
        request.add_header("Authorization", self._authorization_header())
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        try:
            with urlopen(request, timeout=12) as response:
                limit = max(0, int(max_bytes or 0))
                body = response.read(limit + 1 if limit else -1)
                return int(response.status), str(response.headers.get("ETag") or ""), body
        except HTTPError as exc:
            return int(exc.code or 0), "", b""
        except (OSError, URLError):
            raise NextcloudNoteClientError(REASON_REMOTE_READ_FAILED) from None

    def _authorization_header(self) -> str:
        raw = f"{self.config.username}:{self.config.app_password}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")


def secret_status_from_env(environ: dict[str, str] | None = None) -> dict[str, Any]:
    return folder_client.secret_status_from_env(environ)


def _note_reason_for_folder_reason(reason_code: str) -> str:
    if reason_code == folder_client.REASON_TARGET_MISSING:
        return workspace_folder_notes.REASON_NOTES_TARGET_MISSING
    if reason_code == folder_client.REASON_CONFLICT:
        return workspace_folder_notes.REASON_NOTES_TARGET_NOT_COLLECTION
    if reason_code in {folder_client.REASON_UNAVAILABLE, folder_client.REASON_AUTH_FAILED}:
        return workspace_folder_notes.REASON_NOTES_TARGET_UNAVAILABLE
    return workspace_folder_notes.REASON_NEXTCLOUD_ERROR_REDACTED


def _notes_target_reason(status: int) -> str:
    if status == 404:
        return workspace_folder_notes.REASON_NOTES_TARGET_MISSING
    if status in {401, 403} or status <= 0 or status >= 500:
        return workspace_folder_notes.REASON_NOTES_TARGET_UNAVAILABLE
    if status in {405, 409, 412, 423}:
        return workspace_folder_notes.REASON_NOTES_TARGET_NOT_COLLECTION
    return workspace_folder_notes.REASON_NEXTCLOUD_ERROR_REDACTED


def _note_write_reason(status: int) -> str:
    if status == 404:
        return workspace_folder_notes.REASON_NOTES_TARGET_MISSING
    if status in {401, 403} or status <= 0 or status >= 500:
        return workspace_folder_notes.REASON_NOTES_TARGET_UNAVAILABLE
    if status in {405, 409, 412, 423}:
        return workspace_folder_notes.REASON_NAME_CONFLICT
    return workspace_folder_notes.REASON_NEXTCLOUD_ERROR_REDACTED


def _note_read_reason(status: int) -> str:
    if status == 404:
        return workspace_folder_notes.REASON_NOT_FOUND
    if status in {401, 403} or status <= 0 or status >= 500:
        return REASON_REMOTE_READ_FAILED
    return REASON_REMOTE_READ_FAILED


def _note_append_write_reason(status: int) -> str:
    if status == 404:
        return workspace_folder_notes.REASON_NOT_FOUND
    if status in {409, 423}:
        return workspace_folder_notes.REASON_VERSION_CONFLICT
    if status in {401, 403} or status <= 0 or status >= 500:
        return REASON_REMOTE_WRITE_FAILED
    return REASON_REMOTE_WRITE_FAILED


def _safe_etag(value: Any) -> str:
    text = str(value or "").strip()
    return text[:512] if text else ""
