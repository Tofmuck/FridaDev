from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo


SCHEMA_VERSION = "v1"

_WEEKDAY_NAMES = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
_WEEKDAY_NAMES_FR = (
    "lundi",
    "mardi",
    "mercredi",
    "jeudi",
    "vendredi",
    "samedi",
    "dimanche",
)
_MONTH_NAMES_FR = (
    "janvier",
    "fevrier",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "aout",
    "septembre",
    "octobre",
    "novembre",
    "decembre",
)


def _parse_iso_datetime(raw: str) -> datetime:
    dt_value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    return dt_value


def _resolve_timezone(timezone_name: str) -> ZoneInfo | timezone:
    try:
        return ZoneInfo(str(timezone_name))
    except Exception:
        return timezone.utc


def _derive_day_part(local_dt: datetime) -> tuple[str, str]:
    hour = local_dt.hour
    if 5 <= hour < 12:
        return "morning", "matin"
    if 12 <= hour < 18:
        return "afternoon", "apres-midi"
    if 18 <= hour < 22:
        return "evening", "soir"
    return "night", "nuit"


def _format_local_hour(local_dt: datetime) -> str:
    return f"{local_dt.hour}h" + (f"{local_dt.minute:02d}" if local_dt.minute else "")


def _format_local_date_fr(local_dt: datetime) -> str:
    weekday = _WEEKDAY_NAMES_FR[local_dt.weekday()]
    month = _MONTH_NAMES_FR[local_dt.month - 1]
    return f"{weekday} {local_dt.day} {month} {local_dt.year}"


def local_date_iso(ts_iso: str, *, timezone_name: str) -> str:
    try:
        dt_value = _parse_iso_datetime(ts_iso)
    except Exception:
        return ""
    timezone_ref = _resolve_timezone(timezone_name)
    return dt_value.astimezone(timezone_ref).strftime("%Y-%m-%d")


def local_date_label_fr(
    ts_iso: str,
    *,
    timezone_name: str,
    include_timezone: bool = False,
) -> str:
    try:
        dt_value = _parse_iso_datetime(ts_iso)
    except Exception:
        return ""
    timezone_ref = _resolve_timezone(timezone_name)
    rendered = _format_local_date_fr(dt_value.astimezone(timezone_ref))
    if include_timezone:
        return f"{rendered} {timezone_name}"
    return rendered


def _format_local_datetime_fr(local_dt: datetime, *, timezone_name: str | None = None) -> str:
    rendered = f"{_format_local_date_fr(local_dt)} à {_format_local_hour(local_dt)}"
    if timezone_name:
        return f"{rendered} {timezone_name}"
    return rendered


def _delta_payload(
    *,
    delta_seconds: int | None,
    delta_class: str,
    delta_human: str,
    local_msg: datetime | None = None,
    timezone_name: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "delta_seconds": delta_seconds,
        "delta_class": delta_class,
        "delta_human": delta_human,
        "delta_label": delta_human,
    }
    if local_msg is None or not timezone_name:
        return payload

    absolute_human = _format_local_datetime_fr(local_msg, timezone_name=timezone_name)
    payload["delta_absolute_human"] = absolute_human
    payload["delta_relative_human"] = delta_human
    payload["delta_label"] = f"{absolute_human} — {delta_human}" if delta_human else absolute_human
    return payload


def build_time_input(*, now_utc_iso: str, timezone_name: str) -> dict[str, str]:
    now_utc = _parse_iso_datetime(now_utc_iso).astimezone(timezone.utc)
    timezone_ref = _resolve_timezone(timezone_name)
    now_local = now_utc.astimezone(timezone_ref)
    day_part_class, day_part_human = _derive_day_part(now_local)
    return {
        "schema_version": SCHEMA_VERSION,
        "now_utc_iso": now_utc.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "timezone": str(timezone_name),
        "now_local_iso": now_local.isoformat(timespec="seconds"),
        "local_date": now_local.strftime("%Y-%m-%d"),
        "local_time": now_local.strftime("%H:%M"),
        "local_weekday": _WEEKDAY_NAMES[now_local.weekday()],
        "day_part_class": day_part_class,
        "day_part_human": day_part_human,
    }


def build_time_reference_block(time_input_payload: Mapping[str, Any]) -> str:
    now_local = _parse_iso_datetime(str(time_input_payload["now_local_iso"]))
    now_human = _format_local_datetime_fr(now_local)
    return (
        "[RÉFÉRENCE TEMPORELLE]\n"
        f"NOW: {time_input_payload['now_local_iso']}\n"
        f"TIMEZONE: {time_input_payload['timezone']}\n\n"
        f"Nous sommes le {now_human}. C'est ton 'maintenant'.\n"
        "Les labels Delta-T des messages ci-dessous portent une date locale absolue, "
        "l'heure locale, la timezone et un relatif lisible par rapport à ce maintenant.\n"
        "Les marqueurs [— silence de X —] indiquent une interruption de la conversation. "
        "Tu n'as pas à les mentionner, mais tu peux en tenir compte dans ton ton si c'est pertinent.\n"
        "Ne mentionne jamais spontanément la date ou l'heure dans tes réponses, "
        "sauf si on te le demande explicitement.\n"
        "Le NOW de reference du tour est deja fourni ci-dessus: n'affirme jamais que tu n'y as pas acces.\n"
        "N'utilise les formulations de journee (ce matin, cet apres-midi, ce soir, cette nuit) "
        "que si l'ancrage dans NOW et les timestamps est robuste; sinon reste neutre.\n"
        "Si on te demande quand on a parle la derniere fois, privilegie le relatif puis ajoute "
        "un absolu court seulement si utile."
    )


def build_delta_info(
    ts_msg: str,
    ts_now: str,
    *,
    timezone_name: str,
) -> dict[str, Any]:
    try:
        dt_msg = _parse_iso_datetime(ts_msg)
        dt_now = _parse_iso_datetime(ts_now)
        delta_seconds = int((dt_now - dt_msg).total_seconds())
        timezone_ref = _resolve_timezone(timezone_name)
        local_msg = dt_msg.astimezone(timezone_ref)
        local_now = dt_now.astimezone(timezone_ref)
        local_day_delta = (local_now.date() - local_msg.date()).days
        elapsed_local_days = local_day_delta if local_day_delta > 0 else max(delta_seconds // 86400, 0)

        if delta_seconds < 60:
            return _delta_payload(
                delta_seconds=delta_seconds,
                delta_class="just_now",
                delta_human="à l'instant",
                local_msg=local_msg,
                timezone_name=timezone_name,
            )
        if delta_seconds < 3600:
            minutes = delta_seconds // 60
            return _delta_payload(
                delta_seconds=delta_seconds,
                delta_class="minutes",
                delta_human=f"il y a {minutes} minute{'s' if minutes > 1 else ''}",
                local_msg=local_msg,
                timezone_name=timezone_name,
            )

        if local_msg.date() == local_now.date():
            return _delta_payload(
                delta_seconds=delta_seconds,
                delta_class="same_day",
                delta_human="aujourd'hui",
                local_msg=local_msg,
                timezone_name=timezone_name,
            )
        if local_msg.date() == (local_now - timedelta(days=1)).date():
            return _delta_payload(
                delta_seconds=delta_seconds,
                delta_class="yesterday",
                delta_human="hier",
                local_msg=local_msg,
                timezone_name=timezone_name,
            )
        if 2 <= local_day_delta < 7:
            return _delta_payload(
                delta_seconds=delta_seconds,
                delta_class="days",
                delta_human=f"il y a {local_day_delta} jours",
                local_msg=local_msg,
                timezone_name=timezone_name,
            )
        if delta_seconds < 86400 * 30:
            weeks = max(1, elapsed_local_days // 7)
            return _delta_payload(
                delta_seconds=delta_seconds,
                delta_class="weeks",
                delta_human=f"il y a {weeks} semaine{'s' if weeks > 1 else ''}",
                local_msg=local_msg,
                timezone_name=timezone_name,
            )
        if delta_seconds < 86400 * 365:
            months = max(1, elapsed_local_days // 30)
            return _delta_payload(
                delta_seconds=delta_seconds,
                delta_class="months",
                delta_human=f"il y a {months} mois",
                local_msg=local_msg,
                timezone_name=timezone_name,
            )
        years = max(1, elapsed_local_days // 365)
        return _delta_payload(
            delta_seconds=delta_seconds,
            delta_class="years",
            delta_human=f"il y a {years} an{'s' if years > 1 else ''}",
            local_msg=local_msg,
            timezone_name=timezone_name,
        )
    except Exception:
        return _delta_payload(
            delta_seconds=None,
            delta_class="unknown",
            delta_human="",
        )


def render_delta_label(ts_msg: str, ts_now: str, *, timezone_name: str) -> str:
    return str(
        build_delta_info(
            ts_msg,
            ts_now,
            timezone_name=timezone_name,
        ).get("delta_label")
        or ""
    )


def build_silence_info(ts_before: str, ts_after: str) -> dict[str, Any]:
    try:
        dt_before = _parse_iso_datetime(ts_before)
        dt_after = _parse_iso_datetime(ts_after)
        silence_seconds = int((dt_after - dt_before).total_seconds())
        if silence_seconds < 60:
            return {
                "silence_seconds": silence_seconds,
                "silence_class": "seconds",
                "silence_human": "[— silence de quelques secondes —]",
            }
        if silence_seconds < 3600:
            minutes = silence_seconds // 60
            return {
                "silence_seconds": silence_seconds,
                "silence_class": "minutes",
                "silence_human": f"[— silence de {minutes} minute{'s' if minutes > 1 else ''} —]",
            }
        if silence_seconds < 86400:
            hours = silence_seconds // 3600
            return {
                "silence_seconds": silence_seconds,
                "silence_class": "hours",
                "silence_human": f"[— silence de {hours} heure{'s' if hours > 1 else ''} —]",
            }
        if silence_seconds < 86400 * 2:
            return {
                "silence_seconds": silence_seconds,
                "silence_class": "one_day",
                "silence_human": "[— silence d'un jour —]",
            }
        if silence_seconds < 86400 * 7:
            days = silence_seconds // 86400
            return {
                "silence_seconds": silence_seconds,
                "silence_class": "days",
                "silence_human": f"[— silence de {days} jours —]",
            }
        if silence_seconds < 86400 * 30:
            weeks = silence_seconds // (86400 * 7)
            return {
                "silence_seconds": silence_seconds,
                "silence_class": "weeks",
                "silence_human": f"[— silence de {weeks} semaine{'s' if weeks > 1 else ''} —]",
            }
        months = silence_seconds // (86400 * 30)
        return {
            "silence_seconds": silence_seconds,
            "silence_class": "months",
            "silence_human": f"[— silence de {months} mois —]",
        }
    except Exception:
        return {
            "silence_seconds": None,
            "silence_class": "unknown",
            "silence_human": "",
        }


def render_silence_label(ts_before: str, ts_after: str) -> str:
    return str(build_silence_info(ts_before, ts_after)["silence_human"])
