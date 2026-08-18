from __future__ import annotations

import json
from typing import Any

from agenda import agent_contract, agent_runtime, product_methods
from agenda.caldav_models import CalendarEvent, CalendarSummary


RAW_SENTINELS = (
    "SYNTHETIC-USER-CONTENT",
    "SYNTHETIC-AGENDA-TITLE",
    "SYNTHETIC-AGENDA-LOCATION",
    "SYNTHETIC-AGENDA-DESCRIPTION",
    "fixture-secret-value",
    "/remote.php/dav/",
    "BEGIN:VCALENDAR",
    "BEGIN:VEVENT",
)


class FakeAgendaModelClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls = 0

    def complete(self, request, *, settings):
        self.calls += 1
        self.last_request = request
        self.last_settings = settings
        return agent_runtime.AgendaAgentModelResponse(
            status="ok",
            reason_code="fake_ok",
            content=json.dumps(self.payload),
            attempt_count=1,
        )


class ErrorAgendaModelClient:
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        self.calls = 0

    def complete(self, request, *, settings):
        del request, settings
        self.calls += 1
        return agent_runtime.AgendaAgentModelResponse(
            status="error",
            reason_code=self.reason_code,
            content="",
            attempt_count=1,
        )


class ExplodingAgendaModelClient:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, request, *, settings):
        del request, settings
        self.calls += 1
        raise AssertionError("agenda model must not be called")


class FakeAgendaReadClient:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.calendar = CalendarSummary(
            local_id="primary",
            display_name="SYNTHETIC-AGENDA-CALENDAR",
            permissions=("read",),
            color="#1166aa",
            enabled=True,
            readonly=True,
            family_calendar=False,
            family_calendar_classification="non_family",
            caldav_path="/remote.php/dav/calendars/fixture-user/primary/",
        )
        self.event = CalendarEvent(
            event_id="event-1",
            calendar_id="primary",
            uid="synthetic-event@example.invalid",
            summary="SYNTHETIC-AGENDA-TITLE",
            location="SYNTHETIC-AGENDA-LOCATION",
            description="SYNTHETIC-AGENDA-DESCRIPTION",
            start_iso="2026-06-08T07:00:00Z",
            end_iso="2026-06-08T08:00:00Z",
            timezone="UTC",
            etag="synthetic-etag",
            caldav_path="/remote.php/dav/calendars/fixture-user/primary/event-1.ics",
        )

    def list_calendars(self):
        self.calls.append("list_calendars")
        return (self.calendar,)

    def query_calendar_events(self, calendar, *, start_iso, end_iso, timezone_name="UTC"):
        del calendar, start_iso, end_iso, timezone_name
        self.calls.append("query_calendar_events")
        return (self.event,)

    def calendar_by_local_id(self, calendar_id):
        if str(calendar_id or "") == self.calendar.local_id:
            return self.calendar
        return None


class SecretCountingRuntimeSettings:
    def __init__(self, value: str = "fixture-secret-value") -> None:
        self.value = value
        self.secret_reads = 0

    def get_runtime_secret_value(self, section, field):
        self.secret_reads += 1
        return type(
            "RuntimeSecretValueFixture",
            (),
            {"section": section, "field": field, "value": self.value},
        )()


def read_today_payload() -> dict[str, Any]:
    return {
        "schema_version": agent_contract.SCHEMA_VERSION,
        "product_method": product_methods.METHOD_READ_TODAY,
        "intent": "SYNTHETIC-USER-CONTENT",
        "calendar_scope": {
            "calendar_ids": ["primary"],
            "family_calendar": False,
            "ambiguity": "none",
        },
        "time_scope": {
            "kind": "day",
            "start": "2026-06-08T00:00:00Z",
            "end": "2026-06-09T00:00:00Z",
            "timezone": "UTC",
            "ambiguity": "none",
        },
        "tool_calls": [
            {
                "tool_name": product_methods.TOOL_EVENT_QUERY_RANGE,
                "method": "GET",
                "params": {
                    "calendar_id": "primary",
                    "start": "2026-06-08T00:00:00Z",
                    "end": "2026-06-09T00:00:00Z",
                    "timezone": "UTC",
                },
                "call_id": "call-1",
            }
        ],
        "draft": _empty_draft(),
        "mutation": {
            "requested": False,
            "kind": "none",
            "confirmation_required": False,
            "confirmation_level": "none",
            "pending_action_id": "",
        },
        "answer_mode": "agenda_summary",
        "risk_flags": [],
        "fallback_reason": "",
        "surface_intro": "",
        "surface_error": "SYNTHETIC-AGENDA-ERROR",
        "surface_outro": "",
    }


def propose_create_payload() -> dict[str, Any]:
    payload = read_today_payload()
    payload.update(
        {
            "product_method": product_methods.METHOD_PROPOSE_CREATE_EVENT,
            "tool_calls": [],
            "draft": {
                **_empty_draft(),
                "title": "SYNTHETIC-AGENDA-TITLE",
                "location": "SYNTHETIC-AGENDA-LOCATION",
                "description": "SYNTHETIC-AGENDA-DESCRIPTION",
                "calendar_id": "primary",
                "start": "2026-06-09T08:00:00Z",
                "end": "2026-06-09T09:00:00Z",
                "timezone": "UTC",
                "all_day": False,
            },
            "mutation": {
                "requested": False,
                "kind": "create",
                "confirmation_required": True,
                "confirmation_level": "simple",
                "pending_action_id": "",
            },
            "answer_mode": "proposal",
        }
    )
    return payload


def assert_content_free(value: Any) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    leaked = [sentinel for sentinel in RAW_SENTINELS if sentinel in encoded]
    if leaked:
        raise AssertionError(f"raw Agenda sentinel leaked: {leaked}")


def _empty_draft() -> dict[str, Any]:
    return {
        "title": None,
        "location": None,
        "description": None,
        "calendar_id": None,
        "start": None,
        "end": None,
        "timezone": None,
        "all_day": None,
        "target_event_id": None,
        "change_summary": None,
    }
