from __future__ import annotations

import base64
from typing import Any

from agenda import runtime_config
from agenda.caldav_models import CalDavReadError, CalDavRequest, CalDavResponse, CalDavTransportUnavailable
from agenda.caldav_read_client import CalDavReadClient


DEFAULT_CALDAV_BASE_URL = 'https://cloud.frida-system.fr/'
DEFAULT_TIMEOUT_S = 12


class CalDavHttpTransport:
    def __init__(
        self,
        *,
        account: str,
        app_password: str,
        requests_module: Any,
        timeout_s: int = DEFAULT_TIMEOUT_S,
    ) -> None:
        self._account = str(account or runtime_config.CALDAV_ACCOUNT_V1)
        self._app_password = str(app_password or '')
        self._requests = requests_module
        self._timeout_s = int(timeout_s or DEFAULT_TIMEOUT_S)

    def __call__(self, request: CalDavRequest) -> CalDavResponse:
        if request.method not in {'PROPFIND', 'REPORT', 'GET'}:
            raise CalDavTransportUnavailable('CalDAV transport only supports read-only methods')
        request_func = getattr(self._requests, 'request', None)
        if not callable(request_func):
            raise CalDavTransportUnavailable('requests module does not expose request()')
        headers = dict(request.headers or {})
        headers['Authorization'] = _basic_auth_header(self._account, self._app_password)
        try:
            response = request_func(
                request.method,
                request.url,
                headers=headers,
                data=request.body.encode('utf-8') if request.body else b'',
                timeout=self._timeout_s,
            )
        except Exception as exc:
            reason_code = _requests_error_reason(self._requests, exc)
            if not reason_code:
                raise
            raise CalDavReadError(
                method=request.method,
                kind=request.kind,
                status_code=0,
                reason_code=reason_code,
            ) from None
        return CalDavResponse(
            status_code=int(getattr(response, 'status_code', 0) or 0),
            text=str(getattr(response, 'text', '') or ''),
            headers={},
        )


def build_live_caldav_read_client(
    *,
    account: str,
    app_password: str,
    requests_module: Any,
    config_module: Any = None,
) -> CalDavReadClient:
    base_url = _caldav_base_url(config_module)
    principal_path = f'/remote.php/dav/calendars/{str(account or runtime_config.CALDAV_ACCOUNT_V1).strip()}/'
    transport = CalDavHttpTransport(
        account=str(account or runtime_config.CALDAV_ACCOUNT_V1),
        app_password=str(app_password or ''),
        requests_module=requests_module,
    )
    return CalDavReadClient(
        transport=transport,
        base_url=base_url,
        principal_path=principal_path,
    )


def _caldav_base_url(config_module: Any) -> str:
    for attr in ('NEXTCLOUD_CALDAV_BASE_URL', 'NEXTCLOUD_BASE_URL', 'FRIDA_NEXTCLOUD_URL'):
        value = str(getattr(config_module, attr, '') or '').strip()
        if value:
            return value.rstrip('/') + '/'
    return DEFAULT_CALDAV_BASE_URL


def _basic_auth_header(account: str, app_password: str) -> str:
    raw = f'{account}:{app_password}'.encode('utf-8')
    return 'Basic ' + base64.b64encode(raw).decode('ascii')


def _requests_error_reason(requests_module: Any, exc: Exception) -> str:
    exceptions = getattr(requests_module, 'exceptions', None)
    timeout_type = getattr(exceptions, 'Timeout', None)
    request_error_type = getattr(exceptions, 'RequestException', None)
    if isinstance(timeout_type, type) and isinstance(exc, timeout_type):
        return 'caldav_timeout'
    if isinstance(request_error_type, type) and isinstance(exc, request_error_type):
        return 'caldav_request_error'
    return ''
