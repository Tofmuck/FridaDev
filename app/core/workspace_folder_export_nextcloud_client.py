from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from . import workspace_folder_exports
from . import workspace_folder_nextcloud_client as folder_client


EXPORTS_SUBFOLDER = "Exports"


@dataclass(frozen=True)
class NextcloudExportResponse:
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
class NextcloudExportReadResponse:
    ok: bool
    reason_code: str
    http_status: int = 0
    content: bytes = b""

    @property
    def status_class(self) -> str:
        if self.http_status <= 0:
            return "none"
        return f"{self.http_status // 100}xx"


class NextcloudExportClientError(RuntimeError):
    def __init__(self, reason_code: str, *, http_status: int = 0):
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.http_status = int(http_status or 0)

    @property
    def status_class(self) -> str:
        if self.http_status <= 0:
            return "none"
        return f"{self.http_status // 100}xx"


class NextcloudExportClient:
    """Bounded WebDAV client for Exports V1 placement."""

    def __init__(self, config: folder_client.NextcloudFolderClientConfig):
        self.config = config

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "NextcloudExportClient":
        try:
            config = folder_client.config_from_env(environ)
        except folder_client.NextcloudFolderClientError as exc:
            raise NextcloudExportClientError(
                _export_reason_for_folder_reason(exc.reason_code),
                http_status=exc.http_status,
            ) from None
        return cls(config)

    def exports_status(self, folder_name: str) -> NextcloudExportResponse:
        status, is_collection = self._request_collection_status(
            self._url(folder_name, EXPORTS_SUBFOLDER)
        )
        if status == 207 and is_collection:
            return NextcloudExportResponse(True, workspace_folder_exports.REASON_STORE_OK, status)
        if status == 207:
            raise NextcloudExportClientError(
                workspace_folder_exports.REASON_EXPORTS_TARGET_NOT_COLLECTION,
                http_status=status,
            )
        raise NextcloudExportClientError(_exports_target_reason(status), http_status=status)

    def put_export(
        self,
        folder_name: str,
        export_name: str,
        content: bytes,
        *,
        media_type: str = "",
    ) -> NextcloudExportResponse:
        status, etag = self._request_status(
            "PUT",
            self._url(folder_name, EXPORTS_SUBFOLDER, export_name),
            data=bytes(content or b""),
            headers={
                "If-None-Match": "*",
                "Content-Type": _safe_media_type(media_type),
            },
        )
        if status == 201:
            return NextcloudExportResponse(
                True,
                workspace_folder_exports.REASON_STORE_OK,
                status,
                etag_value=_safe_etag(etag),
            )
        if status in {200, 204}:
            raise NextcloudExportClientError(
                workspace_folder_exports.REASON_NAME_CONFLICT,
                http_status=status,
            )
        raise NextcloudExportClientError(_export_write_reason(status), http_status=status)

    def export_status(self, folder_name: str, export_name: str) -> NextcloudExportResponse:
        status, _etag = self._request_status(
            "PROPFIND",
            self._url(folder_name, EXPORTS_SUBFOLDER, export_name),
            headers={"Depth": "0"},
        )
        if status == 207:
            return NextcloudExportResponse(True, workspace_folder_exports.REASON_STORE_OK, status)
        raise NextcloudExportClientError(_export_write_reason(status), http_status=status)

    def read_export(
        self,
        folder_name: str,
        export_name: str,
        *,
        max_bytes: int,
    ) -> NextcloudExportReadResponse:
        status, content = self._request_content(
            "GET",
            self._url(folder_name, EXPORTS_SUBFOLDER, export_name),
            max_bytes=max_bytes,
        )
        if status == 200:
            return NextcloudExportReadResponse(
                True,
                workspace_folder_exports.REASON_DOWNLOAD_OK,
                status,
                content=content,
            )
        raise NextcloudExportClientError(_export_read_reason(status), http_status=status)

    def delete_export(
        self,
        folder_name: str,
        export_name: str,
        *,
        missing_ok: bool = True,
    ) -> NextcloudExportResponse:
        status, _etag = self._request_status(
            "DELETE",
            self._url(folder_name, EXPORTS_SUBFOLDER, export_name),
        )
        if status in {200, 202, 204} or (missing_ok and status == 404):
            return NextcloudExportResponse(
                True,
                workspace_folder_exports.REASON_REMOTE_COMPENSATION_OK,
                status,
            )
        raise NextcloudExportClientError(
            workspace_folder_exports.REASON_REMOTE_COMPENSATION_FAILED,
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
            raise NextcloudExportClientError(
                workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE
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
            raise NextcloudExportClientError(
                workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE
            ) from None

    def _request_content(
        self,
        method: str,
        url: str,
        *,
        max_bytes: int,
    ) -> tuple[int, bytes]:
        request = Request(url, method=method)
        request.add_header("Authorization", self._authorization_header())
        limit = max(0, int(max_bytes or 0))
        try:
            with urlopen(request, timeout=12) as response:
                status = int(response.status)
                if status != 200:
                    return status, b""
                content_length = str(response.headers.get("Content-Length") or "").strip()
                if content_length:
                    try:
                        if int(content_length) > limit:
                            raise NextcloudExportClientError(
                                workspace_folder_exports.REASON_TOO_LARGE,
                                http_status=status,
                            )
                    except ValueError:
                        pass
                chunks: list[bytes] = []
                total = 0
                while True:
                    chunk = response.read(min(64 * 1024, max(1, limit + 1 - total)))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                    if total > limit:
                        raise NextcloudExportClientError(
                            workspace_folder_exports.REASON_TOO_LARGE,
                            http_status=status,
                        )
                return status, b"".join(chunks)
        except HTTPError as exc:
            return int(exc.code or 0), b""
        except NextcloudExportClientError:
            raise
        except (OSError, URLError):
            raise NextcloudExportClientError(
                workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE
            ) from None

    def _authorization_header(self) -> str:
        raw = f"{self.config.username}:{self.config.app_password}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")


def secret_status_from_env(environ: dict[str, str] | None = None) -> dict[str, Any]:
    return folder_client.secret_status_from_env(environ)


def _export_reason_for_folder_reason(reason_code: str) -> str:
    if reason_code == folder_client.REASON_TARGET_MISSING:
        return workspace_folder_exports.REASON_EXPORTS_TARGET_MISSING
    if reason_code == folder_client.REASON_CONFLICT:
        return workspace_folder_exports.REASON_EXPORTS_TARGET_NOT_COLLECTION
    if reason_code in {folder_client.REASON_UNAVAILABLE, folder_client.REASON_AUTH_FAILED}:
        return workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE
    return workspace_folder_exports.REASON_NEXTCLOUD_ERROR_REDACTED


def _exports_target_reason(status: int) -> str:
    if status == 404:
        return workspace_folder_exports.REASON_EXPORTS_TARGET_MISSING
    if status in {401, 403} or status <= 0 or status >= 500:
        return workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE
    if status in {405, 409, 412, 423}:
        return workspace_folder_exports.REASON_EXPORTS_TARGET_NOT_COLLECTION
    return workspace_folder_exports.REASON_NEXTCLOUD_ERROR_REDACTED


def _export_write_reason(status: int) -> str:
    if status == 404:
        return workspace_folder_exports.REASON_EXPORTS_TARGET_MISSING
    if status in {401, 403} or status <= 0 or status >= 500:
        return workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE
    if status in {405, 409, 412, 423}:
        return workspace_folder_exports.REASON_NAME_CONFLICT
    return workspace_folder_exports.REASON_NEXTCLOUD_ERROR_REDACTED


def _export_read_reason(status: int) -> str:
    if status == 404:
        return workspace_folder_exports.REASON_EXPORT_NOT_FOUND
    if status in {401, 403} or status <= 0 or status >= 500:
        return workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE
    if status in {405, 409, 412, 423}:
        return workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE
    return workspace_folder_exports.REASON_NEXTCLOUD_ERROR_REDACTED


def _safe_media_type(value: Any) -> str:
    text = " ".join(str(value or "").strip().split()).lower()
    if "/" in text and all(ch.isalnum() or ch in "!#$&^_.+-/;= " for ch in text):
        return text[:120]
    return "application/octet-stream"


def _safe_etag(value: Any) -> str:
    text = str(value or "").strip()
    return text[:512] if text else ""
