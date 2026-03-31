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
    now_human = now_local.strftime("%A %d %B %Y à %H:%M")
    return (
        "[RÉFÉRENCE TEMPORELLE]\n"
        f"NOW: {time_input_payload['now_local_iso']}\n"
        f"TIMEZONE: {time_input_payload['timezone']}\n\n"
        f"Nous sommes le {now_human}. C'est ton 'maintenant'.\n"
        "Les messages ci-dessous sont horodatés relativement à ce maintenant (ex : 'il y a 2 jours').\n"
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

        if delta_seconds < 60:
            return {
                "delta_seconds": delta_seconds,
                "delta_class": "just_now",
                "delta_human": "à l'instant",
            }
        if delta_seconds < 3600:
            minutes = delta_seconds // 60
            return {
                "delta_seconds": delta_seconds,
                "delta_class": "minutes",
                "delta_human": f"il y a {minutes} minute{'s' if minutes > 1 else ''}",
            }

        timezone_ref = _resolve_timezone(timezone_name)
        local_msg = dt_msg.astimezone(timezone_ref)
        local_now = dt_now.astimezone(timezone_ref)
        local_hour = _format_local_hour(local_msg)

        if local_msg.date() == local_now.date():
            return {
                "delta_seconds": delta_seconds,
                "delta_class": "same_day",
                "delta_human": f"aujourd'hui à {local_hour}",
            }
        if local_msg.date() == (local_now - timedelta(days=1)).date():
            return {
                "delta_seconds": delta_seconds,
                "delta_class": "yesterday",
                "delta_human": f"hier à {local_hour}",
            }
        if delta_seconds < 86400 * 7:
            days = delta_seconds // 86400
            return {
                "delta_seconds": delta_seconds,
                "delta_class": "days",
                "delta_human": f"il y a {days} jour{'s' if days > 1 else ''}",
            }
        if delta_seconds < 86400 * 30:
            weeks = delta_seconds // (86400 * 7)
            return {
                "delta_seconds": delta_seconds,
                "delta_class": "weeks",
                "delta_human": f"il y a {weeks} semaine{'s' if weeks > 1 else ''}",
            }
        if delta_seconds < 86400 * 365:
            months = delta_seconds // (86400 * 30)
            return {
                "delta_seconds": delta_seconds,
                "delta_class": "months",
                "delta_human": f"il y a {months} mois",
            }
        years = delta_seconds // (86400 * 365)
        return {
            "delta_seconds": delta_seconds,
            "delta_class": "years",
            "delta_human": f"il y a {years} an{'s' if years > 1 else ''}",
        }
    except Exception:
        return {
            "delta_seconds": None,
            "delta_class": "unknown",
            "delta_human": "",
        }


def render_delta_label(ts_msg: str, ts_now: str, *, timezone_name: str) -> str:
    return str(
        build_delta_info(
            ts_msg,
            ts_now,
            timezone_name=timezone_name,
        )["delta_human"]
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
