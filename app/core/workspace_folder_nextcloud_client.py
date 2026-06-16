from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://platform-nextcloud"
DEFAULT_USERNAME = "frida"
DEFAULT_ROOT_NAME = "Frida"
DEFAULT_APP_PASSWORD_FILE = "/run/secrets/nextcloud_frida_app_password"

REASON_CREATE_OK = "workspace_folder_nextcloud_create_ok"
REASON_RENAME_OK = "workspace_folder_nextcloud_rename_ok"
REASON_CONFLICT = "workspace_folder_nextcloud_conflict"
REASON_UNAVAILABLE = "workspace_folder_nextcloud_unavailable"
REASON_AUTH_FAILED = "workspace_folder_nextcloud_auth_failed"
REASON_TARGET_MISSING = "workspace_folder_nextcloud_target_missing"
REASON_ROLLBACK_OK = "workspace_folder_nextcloud_rollback_ok"
REASON_ROLLBACK_FAILED = "workspace_folder_nextcloud_rollback_failed"
REASON_LOCAL_PERSISTENCE_FAILED = "workspace_folder_local_persistence_failed"
REASON_ERROR_REDACTED = "workspace_folder_nextcloud_error_redacted"


@dataclass(frozen=True)
class NextcloudFolderClientConfig:
    base_url: str
    username: str
    app_password: str
    root_name: str = DEFAULT_ROOT_NAME


@dataclass(frozen=True)
class NextcloudFolderResponse:
    ok: bool
    reason_code: str
    http_status: int = 0

    @property
    def status_class(self) -> str:
        if self.http_status <= 0:
            return "none"
        return f"{self.http_status // 100}xx"


class NextcloudFolderClientError(RuntimeError):
    def __init__(self, reason_code: str, *, http_status: int = 0):
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.http_status = int(http_status or 0)

    @property
    def status_class(self) -> str:
        if self.http_status <= 0:
            return "none"
        return f"{self.http_status // 100}xx"


def secret_status_from_env(environ: dict[str, str] | None = None) -> dict[str, Any]:
    env = environ if environ is not None else os.environ
    secret_file = env.get("FRIDA_NEXTCLOUD_APP_PASSWORD_FILE") or DEFAULT_APP_PASSWORD_FILE
    return {
        "secret_available": Path(secret_file).is_file(),
        "source_type": "file",
        "source_ref": "file:/run/secrets/[redacted]" if secret_file.startswith("/run/secrets/") else "file:[redacted]",
        "value_displayed": False,
    }


def config_from_env(environ: dict[str, str] | None = None) -> NextcloudFolderClientConfig:
    env = environ if environ is not None else os.environ
    secret_file = env.get("FRIDA_NEXTCLOUD_APP_PASSWORD_FILE") or DEFAULT_APP_PASSWORD_FILE
    try:
        app_password = Path(secret_file).read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise NextcloudFolderClientError(REASON_UNAVAILABLE) from None
    if not app_password:
        raise NextcloudFolderClientError(REASON_UNAVAILABLE)
    return NextcloudFolderClientConfig(
        base_url=(env.get("FRIDA_NEXTCLOUD_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
        username=env.get("FRIDA_NEXTCLOUD_USERNAME") or DEFAULT_USERNAME,
        app_password=app_password,
        root_name=env.get("FRIDA_NEXTCLOUD_ROOT_NAME") or DEFAULT_ROOT_NAME,
    )


class NextcloudFolderClient:
    def __init__(self, config: NextcloudFolderClientConfig):
        self.config = config

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "NextcloudFolderClient":
        return cls(config_from_env(environ))

    def root_status(self) -> NextcloudFolderResponse:
        status = self._request_status("PROPFIND", self._folder_url(), headers={"Depth": "0"})
        if status == 207:
            return NextcloudFolderResponse(True, REASON_CREATE_OK, status)
        raise NextcloudFolderClientError(_reason_for_status(status), http_status=status)

    def folder_status(self, folder_name: str) -> NextcloudFolderResponse:
        status = self._request_status("PROPFIND", self._folder_url(folder_name), headers={"Depth": "0"})
        if status == 207:
            return NextcloudFolderResponse(True, REASON_CREATE_OK, status)
        raise NextcloudFolderClientError(_reason_for_status(status), http_status=status)

    def create_folder(self, folder_name: str) -> NextcloudFolderResponse:
        status = self._request_status("MKCOL", self._folder_url(folder_name))
        if status in {200, 201, 204}:
            return NextcloudFolderResponse(True, REASON_CREATE_OK, status)
        raise NextcloudFolderClientError(_reason_for_status(status), http_status=status)

    def move_folder(self, old_name: str, new_name: str) -> NextcloudFolderResponse:
        status = self._request_status(
            "MOVE",
            self._folder_url(old_name),
            headers={
                "Destination": self._folder_url(new_name),
                "Overwrite": "F",
            },
        )
        if status in {200, 201, 204}:
            return NextcloudFolderResponse(True, REASON_RENAME_OK, status)
        raise NextcloudFolderClientError(_reason_for_status(status), http_status=status)

    def delete_folder(self, folder_name: str, *, missing_ok: bool = True) -> NextcloudFolderResponse:
        status = self._request_status("DELETE", self._folder_url(folder_name))
        if status in {200, 202, 204} or (missing_ok and status == 404):
            return NextcloudFolderResponse(True, REASON_ROLLBACK_OK, status)
        raise NextcloudFolderClientError(REASON_ROLLBACK_FAILED, http_status=status)

    def _folder_url(self, *segments: str) -> str:
        parts = [self.config.root_name, *[segment for segment in segments if segment]]
        encoded = "/".join(quote(part.strip("/"), safe="") for part in parts)
        user = quote(self.config.username, safe="")
        return f"{self.config.base_url}/remote.php/dav/files/{user}/{encoded}"

    def _request_status(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> int:
        request = Request(url, method=method)
        request.add_header("Authorization", self._authorization_header())
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        try:
            with urlopen(request, timeout=12) as response:
                return int(response.status)
        except HTTPError as exc:
            return int(exc.code or 0)
        except (OSError, URLError):
            raise NextcloudFolderClientError(REASON_UNAVAILABLE) from None

    def _authorization_header(self) -> str:
        raw = f"{self.config.username}:{self.config.app_password}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")


def _reason_for_status(status: int) -> str:
    if status in {401, 403}:
        return REASON_AUTH_FAILED
    if status == 404:
        return REASON_TARGET_MISSING
    if status in {405, 409, 412, 423}:
        return REASON_CONFLICT
    if status <= 0 or status >= 500:
        return REASON_UNAVAILABLE
    return REASON_ERROR_REDACTED
