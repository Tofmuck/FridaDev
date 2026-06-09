from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin
from xml.etree import ElementTree

from agenda.caldav_models import (
    CalDavReadError,
    CalDavRequest,
    CalDavResponse,
    CalDavTransportUnavailable,
    CalendarEvent,
    CalendarSummary,
)
from agenda import family_calendar_policy
from agenda.ics_reader import parse_ics_events
from agenda.observability import sha256_12


Transport = Callable[[CalDavRequest], CalDavResponse]


def _local_name(tag: str) -> str:
    return str(tag or '').rsplit('}', 1)[-1]


def _text_for_child(element: ElementTree.Element, local_name: str) -> str:
    for child in element.iter():
        if _local_name(child.tag) == local_name and child.text:
            return str(child.text).strip()
    return ''


class CalDavReadClient:
    def __init__(
        self,
        *,
        transport: Transport | None,
        base_url: str = 'https://caldav.invalid/',
        principal_path: str = '/remote.php/dav/calendars/tof/',
    ) -> None:
        self._transport = transport
        self._base_url = str(base_url or 'https://caldav.invalid/')
        self._principal_path = str(principal_path or '/remote.php/dav/calendars/tof/')

    def list_calendars(self) -> tuple[CalendarSummary, ...]:
        response = self._send(
            CalDavRequest(
                method='PROPFIND',
                url=self._absolute_url(self._principal_path),
                headers={'Depth': '1', 'Content-Type': 'application/xml; charset=utf-8'},
                body=_calendar_list_body(),
                kind='calendar_list',
            ),
            expected_statuses=(207,),
        )
        return parse_calendar_propfind(response.text)

    def query_calendar_events(
        self,
        calendar: CalendarSummary,
        *,
        start_iso: str,
        end_iso: str,
        timezone_name: str = 'UTC',
    ) -> tuple[CalendarEvent, ...]:
        response = self._send(
            CalDavRequest(
                method='REPORT',
                url=self._absolute_url(calendar.caldav_path),
                headers={'Depth': '1', 'Content-Type': 'application/xml; charset=utf-8'},
                body=_calendar_query_body(start_iso=start_iso, end_iso=end_iso),
                kind='event_query_range',
            ),
            expected_statuses=(207,),
        )
        return parse_event_report(
            response.text,
            calendar=calendar,
            timezone_name=timezone_name,
            window_start_iso=start_iso,
            window_end_iso=end_iso,
        )

    def get_event(self, event: CalendarEvent) -> CalendarEvent:
        response = self._send(
            CalDavRequest(
                method='GET',
                url=self._absolute_url(event.caldav_path),
                headers={'Accept': 'text/calendar'},
                body='',
                kind='event_get',
            ),
            expected_statuses=(200,),
        )
        events = parse_ics_events(
            response.text,
            calendar_id=event.calendar_id,
            timezone_name=event.timezone,
            default_etag=event.etag,
            default_caldav_path=event.caldav_path,
            source_ics=response.text,
            window_start_iso=event.start_iso,
            window_end_iso=event.end_iso,
        )
        for candidate in events:
            if candidate.event_id == event.event_id:
                return candidate
        for candidate in events:
            if candidate.uid == event.uid:
                return candidate
        return event

    def _send(self, request: CalDavRequest, *, expected_statuses: tuple[int, ...]) -> CalDavResponse:
        if self._transport is None:
            raise CalDavTransportUnavailable('CalDAV read client requires an injected transport')
        response = self._transport(request)
        if int(response.status_code) not in expected_statuses:
            raise CalDavReadError(
                method=request.method,
                kind=request.kind,
                status_code=int(response.status_code),
                reason_code=_status_reason(int(response.status_code)),
            )
        return response

    def _absolute_url(self, path_or_url: str) -> str:
        value = str(path_or_url or '')
        if value.startswith(('http://', 'https://')):
            return value
        return urljoin(self._base_url.rstrip('/') + '/', value.lstrip('/'))


def parse_calendar_propfind(xml_text: str) -> tuple[CalendarSummary, ...]:
    root = ElementTree.fromstring(str(xml_text or ''))
    calendars: list[CalendarSummary] = []
    for response in (item for item in root.iter() if _local_name(item.tag) == 'response'):
        href = _text_for_child(response, 'href')
        display_name = _text_for_child(response, 'displayname')
        if not href or not display_name:
            continue
        privileges = tuple(sorted(set(_privileges(response))))
        color = _text_for_child(response, 'calendar-color')
        risk_flag = _text_for_child(response, 'x-frida-risk-flag').lower()
        readonly = 'write' not in privileges
        local_id = f'cal_{sha256_12(href)}'
        classification = _calendar_classification(risk_flag)
        calendars.append(
            CalendarSummary(
                local_id=local_id,
                display_name=display_name,
                permissions=privileges,
                color=color,
                enabled=True,
                readonly=readonly,
                family_calendar=classification == family_calendar_policy.CLASSIFICATION_FAMILY,
                family_calendar_classification=classification,
                caldav_path=href,
            )
        )
    return tuple(calendars)


def parse_event_report(
    response_text: str,
    *,
    calendar: CalendarSummary,
    timezone_name: str = 'UTC',
    window_start_iso: str = '',
    window_end_iso: str = '',
) -> tuple[CalendarEvent, ...]:
    text = str(response_text or '').strip()
    if text.startswith('BEGIN:VCALENDAR'):
        return parse_ics_events(
            text,
            calendar_id=calendar.local_id,
            timezone_name=timezone_name,
            source_ics=text,
            window_start_iso=window_start_iso,
            window_end_iso=window_end_iso,
        )
    root = ElementTree.fromstring(text)
    events: list[CalendarEvent] = []
    for response in (item for item in root.iter() if _local_name(item.tag) == 'response'):
        href = _text_for_child(response, 'href')
        etag = _text_for_child(response, 'getetag')
        calendar_data = _text_for_child(response, 'calendar-data')
        if not calendar_data:
            continue
        events.extend(
            parse_ics_events(
                calendar_data,
                calendar_id=calendar.local_id,
                timezone_name=timezone_name,
                default_etag=etag,
                default_caldav_path=href,
                source_ics=calendar_data,
                window_start_iso=window_start_iso,
                window_end_iso=window_end_iso,
            )
        )
    return tuple(sorted(events, key=lambda event: (event.start_iso, event.end_iso, event.event_id)))


def _privileges(response: ElementTree.Element) -> list[str]:
    values: list[str] = []
    in_privilege = False
    for element in response.iter():
        name = _local_name(element.tag)
        if name == 'privilege':
            in_privilege = True
            continue
        if in_privilege and name not in {'privilege', 'current-user-privilege-set'}:
            values.append(name)
            in_privilege = False
    return values or ['read']


def _calendar_list_body() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<d:propfind xmlns:d="DAV:" xmlns:cs="http://calendarserver.org/ns/">'
        '<d:prop><d:displayname/><d:current-user-privilege-set/>'
        '<cs:calendar-color/><x-frida-risk-flag/></d:prop></d:propfind>'
    )


def _calendar_classification(risk_flag: str) -> str:
    return family_calendar_policy.normalize_classification(risk_flag)


def _calendar_query_body(*, start_iso: str, end_iso: str) -> str:
    start = _caldav_timestamp(start_iso)
    end = _caldav_timestamp(end_iso)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
        '<d:prop><d:getetag/><c:calendar-data/></d:prop>'
        '<c:filter><c:comp-filter name="VCALENDAR"><c:comp-filter name="VEVENT">'
        f'<c:time-range start="{start}" end="{end}"/>'
        '</c:comp-filter></c:comp-filter></c:filter></c:calendar-query>'
    )


def _caldav_timestamp(iso_value: str) -> str:
    return str(iso_value or '').replace('-', '').replace(':', '').replace('+00:00', 'Z')


def _status_reason(status_code: int) -> str:
    if status_code == 401:
        return 'caldav_unauthorized'
    if status_code == 403:
        return 'caldav_forbidden'
    if status_code == 404:
        return 'caldav_not_found'
    if status_code >= 500:
        return 'caldav_server_error'
    return 'caldav_unexpected_status'
