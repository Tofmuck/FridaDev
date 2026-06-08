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


class ReadToolValidationError(ValueError):
    pass
