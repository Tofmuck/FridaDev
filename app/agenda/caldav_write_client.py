from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

from agenda.caldav_models import CalDavRequest, CalDavResponse
from agenda.observability import sha256_12


Transport = Callable[[CalDavRequest], CalDavResponse]


@dataclass(frozen=True)
class CalDavWriteResult:
    method: str
    status_code: int
    calendar_id: str = ''
    event_reference: str = ''
    etag_present: bool = False

    def to_observation(self) -> dict[str, Any]:
        return {
            'schema_version': 'frida_agenda_caldav_write_result_v1',
            'method': self.method,
            'http_status': self.status_code,
            'calendar_hash': sha256_12(self.calendar_id),
            'event_hash': sha256_12(self.event_reference),
            'etag_present': bool(self.etag_present),
            'content_free': True,
            'redacted': True,
        }


class CalDavWriteValidationError(ValueError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = str(reason_code or 'agenda_write_invalid_target')
        super().__init__(self.reason_code)


class CalDavWriteError(RuntimeError):
    def __init__(self, *, method: str, status_code: int, reason_code: str) -> None:
        self.method = str(method or '')
        self.status_code = int(status_code)
        self.reason_code = str(reason_code or 'caldav_write_unexpected_status')
        super().__init__(
            f'CalDAV write request failed: method={self.method} '
            f'status={self.status_code} reason={self.reason_code}'
        )


class CalDavWriteClient:
    def __init__(
        self,
        *,
        transport: Transport | None,
        base_url: str = 'https://caldav.invalid/',
        calendar_paths: Mapping[str, str] | None = None,
    ) -> None:
        self._transport = transport
        self._base_url = str(base_url or 'https://caldav.invalid/')
        self._calendar_paths = {
            str(key or ''): str(value or '')
            for key, value in dict(calendar_paths or {}).items()
            if str(key or '') and str(value or '')
        }

    def put_new_event(self, *, calendar_id: str, uid: str, ics_text: str) -> CalDavWriteResult:
        calendar_path = self._calendar_paths.get(str(calendar_id or ''))
        if not calendar_path:
            raise CalDavWriteValidationError('agenda_write_calendar_target_missing')
        path = calendar_path.rstrip('/') + '/' + _ics_file_name(uid)
        return self._put(
            path=path,
            ics_text=ics_text,
            calendar_id=calendar_id,
            event_reference=uid,
            headers={'If-None-Match': '*'},
        )

    def put_existing_event(
        self,
        *,
        caldav_path: str,
        ics_text: str,
        etag: str = '',
        calendar_id: str = '',
        event_reference: str = '',
    ) -> CalDavWriteResult:
        if not str(caldav_path or '').strip():
            raise CalDavWriteValidationError('agenda_write_target_missing')
        if not str(etag or '').strip():
            raise CalDavWriteValidationError('agenda_write_etag_missing')
        headers = {'If-Match': str(etag)}
        return self._put(
            path=caldav_path,
            ics_text=ics_text,
            calendar_id=calendar_id,
            event_reference=event_reference,
            headers=headers,
        )

    def delete_event(
        self,
        *,
        caldav_path: str,
        etag: str = '',
        calendar_id: str = '',
        event_reference: str = '',
    ) -> CalDavWriteResult:
        if not str(caldav_path or '').strip():
            raise CalDavWriteValidationError('agenda_write_target_missing')
        if not str(etag or '').strip():
            raise CalDavWriteValidationError('agenda_write_etag_missing')
        headers = {'If-Match': str(etag)}
        response = self._send(
            CalDavRequest(
                method='DELETE',
                url=self._absolute_url(caldav_path),
                headers=headers,
                body='',
                kind='delete_event',
            ),
            expected_statuses=(200, 202, 204),
        )
        return CalDavWriteResult(
            method='DELETE',
            status_code=response.status_code,
            calendar_id=calendar_id,
            event_reference=event_reference,
            etag_present=bool(etag),
        )

    def _put(
        self,
        *,
        path: str,
        ics_text: str,
        calendar_id: str,
        event_reference: str,
        headers: Mapping[str, str],
    ) -> CalDavWriteResult:
        response = self._send(
            CalDavRequest(
                method='PUT',
                url=self._absolute_url(path),
                headers={'Content-Type': 'text/calendar; charset=utf-8'} | dict(headers),
                body=str(ics_text or ''),
                kind='put_event',
            ),
            expected_statuses=(200, 201, 204),
        )
        return CalDavWriteResult(
            method='PUT',
            status_code=response.status_code,
            calendar_id=calendar_id,
            event_reference=event_reference,
            etag_present=bool(headers.get('If-Match')),
        )

    def _send(self, request: CalDavRequest, *, expected_statuses: tuple[int, ...]) -> CalDavResponse:
        if self._transport is None:
            raise CalDavWriteValidationError('agenda_write_client_unavailable')
        response = self._transport(request)
        status_code = int(response.status_code)
        if status_code not in expected_statuses:
            raise CalDavWriteError(
                method=request.method,
                status_code=status_code,
                reason_code=_status_reason(status_code),
            )
        return response

    def _absolute_url(self, path_or_url: str) -> str:
        value = str(path_or_url or '')
        if value.startswith(('http://', 'https://')):
            return value
        return urljoin(self._base_url.rstrip('/') + '/', value.lstrip('/'))


def _ics_file_name(uid: str) -> str:
    safe = ''.join(char for char in str(uid or '') if char.isalnum() or char in {'-', '_', '.'})
    if not safe:
        safe = 'agenda-event'
    return safe[:120] + '.ics'


def _status_reason(status_code: int) -> str:
    if status_code in {409, 412}:
        return 'agenda_write_conflict'
    if status_code == 401:
        return 'caldav_unauthorized'
    if status_code == 403:
        return 'caldav_forbidden'
    if status_code == 404:
        return 'caldav_not_found'
    if status_code >= 500:
        return 'caldav_server_error'
    return 'caldav_write_unexpected_status'
