from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from . import workspace_folder_generated_images
from . import workspace_folder_nextcloud_client as folder_client


IMAGES_SUBFOLDER = "Images"


@dataclass(frozen=True)
class NextcloudGeneratedImageResponse:
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
class NextcloudGeneratedImageReadResponse:
    ok: bool
    reason_code: str
    http_status: int = 0
    content: bytes = b""
    media_type: str = ""

    @property
    def status_class(self) -> str:
        if self.http_status <= 0:
            return "none"
        return f"{self.http_status // 100}xx"


class NextcloudGeneratedImageClientError(RuntimeError):
    def __init__(self, reason_code: str, *, http_status: int = 0):
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.http_status = int(http_status or 0)

    @property
    def status_class(self) -> str:
        if self.http_status <= 0:
            return "none"
        return f"{self.http_status // 100}xx"


class NextcloudGeneratedImageClient:
    """Bounded WebDAV client for Generated Images V1 exact targets."""

    def __init__(self, config: folder_client.NextcloudFolderClientConfig):
        self.config = config

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "NextcloudGeneratedImageClient":
        try:
            config = folder_client.config_from_env(environ)
        except folder_client.NextcloudFolderClientError as exc:
            raise NextcloudGeneratedImageClientError(
                _image_reason_for_folder_reason(exc.reason_code),
                http_status=exc.http_status,
            ) from None
        return cls(config)

    def images_status(self, folder_name: str) -> NextcloudGeneratedImageResponse:
        status, is_collection = self._request_collection_status(
            self._url(folder_name, IMAGES_SUBFOLDER)
        )
        if status == 207 and is_collection:
            return NextcloudGeneratedImageResponse(
                True,
                workspace_folder_generated_images.REASON_STORE_OK,
                status,
            )
        if status == 207:
            raise NextcloudGeneratedImageClientError(
                workspace_folder_generated_images.REASON_IMAGES_TARGET_NOT_COLLECTION,
                http_status=status,
            )
        raise NextcloudGeneratedImageClientError(_images_target_reason(status), http_status=status)

    def put_image(
        self,
        folder_name: str,
        image_name: str,
        content: bytes,
        *,
        media_type: str = "",
    ) -> NextcloudGeneratedImageResponse:
        status, etag = self._request_status(
            "PUT",
            self._url(folder_name, IMAGES_SUBFOLDER, image_name),
            data=bytes(content or b""),
            headers={
                "If-None-Match": "*",
                "Content-Type": _safe_media_type(media_type),
            },
        )
        if status == 201:
            return NextcloudGeneratedImageResponse(
                True,
                workspace_folder_generated_images.REASON_STORE_OK,
                status,
                etag_value=_safe_etag(etag),
            )
        if status in {200, 204}:
            raise NextcloudGeneratedImageClientError(
                workspace_folder_generated_images.REASON_NAME_CONFLICT,
                http_status=status,
            )
        raise NextcloudGeneratedImageClientError(_image_write_reason(status), http_status=status)

    def delete_image(
        self,
        folder_name: str,
        image_name: str,
        *,
        missing_ok: bool = True,
    ) -> NextcloudGeneratedImageResponse:
        status, _etag = self._request_status(
            "DELETE",
            self._url(folder_name, IMAGES_SUBFOLDER, image_name),
        )
        if status in {200, 202, 204} or (missing_ok and status == 404):
            return NextcloudGeneratedImageResponse(
                True,
                workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_OK,
                status,
            )
        raise NextcloudGeneratedImageClientError(
            workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_FAILED,
            http_status=status,
        )

    def delete_created_image_if_match(
        self,
        folder_name: str,
        image_name: str,
        *,
        etag_value: str,
    ) -> NextcloudGeneratedImageResponse:
        etag = _safe_etag(etag_value)
        if not etag or etag != str(etag_value or "").strip():
            raise NextcloudGeneratedImageClientError(
                workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_OWNERSHIP_UNVERIFIED
            )
        try:
            status, _response_etag = self._request_status(
                "DELETE",
                self._url(folder_name, IMAGES_SUBFOLDER, image_name),
                headers={"If-Match": etag},
            )
        except NextcloudGeneratedImageClientError as exc:
            raise NextcloudGeneratedImageClientError(
                workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_FAILED,
                http_status=exc.http_status,
            ) from None
        if status in {200, 202, 204}:
            return NextcloudGeneratedImageResponse(
                True,
                workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_OK,
                status,
            )
        if status == 404:
            return NextcloudGeneratedImageResponse(
                True,
                workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_MISSING,
                status,
            )
        if status == 412:
            raise NextcloudGeneratedImageClientError(
                workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_PRECONDITION_FAILED,
                http_status=status,
            )
        raise NextcloudGeneratedImageClientError(
            workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_FAILED,
            http_status=status,
        )

    def read_image(
        self,
        folder_name: str,
        image_name: str,
        *,
        max_bytes: int,
    ) -> NextcloudGeneratedImageReadResponse:
        status, content, media_type = self._request_content(
            "GET",
            self._url(folder_name, IMAGES_SUBFOLDER, image_name),
            max_bytes=int(max_bytes or 0),
        )
        if status == 200:
            return NextcloudGeneratedImageReadResponse(
                True,
                workspace_folder_generated_images.REASON_DOWNLOAD_OK,
                status,
                content=content,
                media_type=_safe_media_type(media_type),
            )
        raise NextcloudGeneratedImageClientError(_image_read_reason(status), http_status=status)

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
            raise NextcloudGeneratedImageClientError(
                workspace_folder_generated_images.REASON_IMAGES_TARGET_UNAVAILABLE
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
            raise NextcloudGeneratedImageClientError(
                workspace_folder_generated_images.REASON_IMAGES_TARGET_UNAVAILABLE
            ) from None

    def _request_content(
        self,
        method: str,
        url: str,
        *,
        max_bytes: int,
    ) -> tuple[int, bytes, str]:
        request = Request(url, method=method)
        request.add_header("Authorization", self._authorization_header())
        try:
            with urlopen(request, timeout=12) as response:
                status = int(response.status)
                content_length = response.headers.get("Content-Length")
                if content_length:
                    try:
                        if int(content_length) > max_bytes:
                            raise NextcloudGeneratedImageClientError(
                                workspace_folder_generated_images.REASON_TOO_LARGE,
                                http_status=status,
                            )
                    except ValueError:
                        pass
                chunks: list[bytes] = []
                total = 0
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise NextcloudGeneratedImageClientError(
                            workspace_folder_generated_images.REASON_TOO_LARGE,
                            http_status=status,
                        )
                    chunks.append(chunk)
                media_type = str(response.headers.get("Content-Type") or "")
                return status, b"".join(chunks), media_type
        except HTTPError as exc:
            return int(exc.code or 0), b"", ""
        except NextcloudGeneratedImageClientError:
            raise
        except (OSError, URLError):
            raise NextcloudGeneratedImageClientError(
                workspace_folder_generated_images.REASON_IMAGES_TARGET_UNAVAILABLE
            ) from None

    def _authorization_header(self) -> str:
        raw = f"{self.config.username}:{self.config.app_password}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")


def secret_status_from_env(environ: dict[str, str] | None = None) -> dict[str, Any]:
    return folder_client.secret_status_from_env(environ)


def _image_reason_for_folder_reason(reason_code: str) -> str:
    if reason_code == folder_client.REASON_TARGET_MISSING:
        return workspace_folder_generated_images.REASON_IMAGES_TARGET_MISSING
    if reason_code == folder_client.REASON_CONFLICT:
        return workspace_folder_generated_images.REASON_IMAGES_TARGET_NOT_COLLECTION
    if reason_code in {folder_client.REASON_UNAVAILABLE, folder_client.REASON_AUTH_FAILED}:
        return workspace_folder_generated_images.REASON_IMAGES_TARGET_UNAVAILABLE
    return workspace_folder_generated_images.REASON_NEXTCLOUD_ERROR_REDACTED


def _images_target_reason(status: int) -> str:
    if status == 404:
        return workspace_folder_generated_images.REASON_IMAGES_TARGET_MISSING
    if status in {401, 403} or status <= 0 or status >= 500:
        return workspace_folder_generated_images.REASON_IMAGES_TARGET_UNAVAILABLE
    if status in {405, 409, 412, 423}:
        return workspace_folder_generated_images.REASON_IMAGES_TARGET_NOT_COLLECTION
    return workspace_folder_generated_images.REASON_NEXTCLOUD_ERROR_REDACTED


def _image_write_reason(status: int) -> str:
    if status == 404:
        return workspace_folder_generated_images.REASON_IMAGES_TARGET_MISSING
    if status in {401, 403} or status <= 0 or status >= 500:
        return workspace_folder_generated_images.REASON_IMAGES_TARGET_UNAVAILABLE
    if status in {405, 409, 412, 423}:
        return workspace_folder_generated_images.REASON_NAME_CONFLICT
    return workspace_folder_generated_images.REASON_NEXTCLOUD_ERROR_REDACTED


def _image_read_reason(status: int) -> str:
    if status == 404:
        return workspace_folder_generated_images.REASON_NOT_FOUND
    if status in {401, 403} or status <= 0 or status >= 500:
        return workspace_folder_generated_images.REASON_IMAGES_TARGET_UNAVAILABLE
    if status in {405, 409, 412, 423}:
        return workspace_folder_generated_images.REASON_IMAGES_TARGET_UNAVAILABLE
    return workspace_folder_generated_images.REASON_NEXTCLOUD_ERROR_REDACTED


def _safe_media_type(value: Any) -> str:
    text = " ".join(str(value or "").strip().split()).lower()
    if "/" in text and all(ch.isalnum() or ch in "!#$&^_.+-/;= " for ch in text):
        return text[:120]
    return "application/octet-stream"


def _safe_etag(value: Any) -> str:
    text = str(value or "").strip()
    return text if text and len(text) <= 512 else ""
