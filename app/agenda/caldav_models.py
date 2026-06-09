from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CalendarSummary:
    local_id: str
    display_name: str
    permissions: tuple[str, ...] = ()
    color: str = ''
    enabled: bool = True
    readonly: bool = True
    family_calendar: bool = False
    family_calendar_classification: str = 'unknown'
    caldav_path: str = ''


@dataclass(frozen=True)
class CalendarEvent:
    event_id: str
    calendar_id: str
    uid: str
    summary: str
    location: str
    description: str
    start_iso: str
    end_iso: str
    timezone: str = 'UTC'
    etag: str = ''
    caldav_path: str = ''
    all_day: bool = False
    source_ics: str = ''


@dataclass
class AgendaReadState:
    calendars: dict[str, CalendarSummary] = field(default_factory=dict)
    events: dict[str, CalendarEvent] = field(default_factory=dict)

    def add_calendars(self, calendars: tuple[CalendarSummary, ...]) -> None:
        for calendar in calendars:
            self.calendars[calendar.local_id] = calendar

    def add_events(self, events: tuple[CalendarEvent, ...]) -> None:
        for event in events:
            self.events[event.event_id] = event

    def events_for_calendar(self, calendar_id: str) -> tuple[CalendarEvent, ...]:
        return tuple(
            sorted(
                (event for event in self.events.values() if event.calendar_id == calendar_id),
                key=lambda event: (event.start_iso, event.end_iso, event.event_id),
            )
        )


@dataclass(frozen=True)
class ReadToolResult:
    status: str
    items: tuple[Any, ...]
    observation: dict[str, Any]


@dataclass(frozen=True)
class CalDavRequest:
    method: str
    url: str
    headers: dict[str, str]
    body: str
    kind: str


@dataclass(frozen=True)
class CalDavResponse:
    status_code: int
    text: str
    headers: dict[str, str] = field(default_factory=dict)


class CalDavTransportUnavailable(RuntimeError):
    pass


class CalDavReadError(RuntimeError):
    def __init__(self, *, method: str, kind: str, status_code: int, reason_code: str) -> None:
        self.method = str(method or '')
        self.kind = str(kind or '')
        self.status_code = int(status_code)
        self.reason_code = str(reason_code or 'unexpected_status')
        super().__init__(
            f'CalDAV read request failed: method={self.method} '
            f'kind={self.kind} status={self.status_code} reason={self.reason_code}'
        )

    def to_observation(self) -> dict[str, Any]:
        return {
            'schema_version': 'frida_agenda_caldav_read_error_v1',
            'status': 'error',
            'reason_code': self.reason_code,
            'method': self.method,
            'kind': self.kind,
            'http_status': self.status_code,
            'caldav_access': False,
            'nextcloud_access': False,
            'content_free': True,
            'redacted': True,
        }


class ReadToolValidationError(ValueError):
    pass
