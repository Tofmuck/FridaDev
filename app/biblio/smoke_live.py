"""Content-free live smoke runner for Biblio library turns."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from .catalogue_client import CatalogueClient
from .chat_runtime import BiblioChatResult, run_biblio_chat_turn


@dataclass(frozen=True)
class BiblioSmokeCase:
    case_id: str
    message: str = field(repr=False, compare=False)


DEFAULT_SMOKE_CASES: tuple[BiblioSmokeCase, ...] = (
    BiblioSmokeCase("S1", "Tu peux chercher et voir les premiers ouvrages ?"),
    BiblioSmokeCase("S2", "Extrait du Theetete de Platon 126b a 128a"),
    BiblioSmokeCase("S3", "Trouve dans le Theetete le passage ou Socrate parle de la maieutique"),
    BiblioSmokeCase("S4", "Cherche maieutique dans la bibliotheque"),
    BiblioSmokeCase("S5", "Peux tu me trouver dans le Theetete le passage ou Socrate parle de la maieutique"),
)

DEFAULT_RAW_MARKERS: tuple[str, ...] = (
    "Theetete",
    "Platon",
    "Socrate",
    "maieutique",
    "126b",
    "128a",
)

SmokeTurnRunner = Callable[..., BiblioChatResult]

EXIT_OK = 0
EXIT_CONTENT_FREE_VIOLATION = 2

_OUTPUT_KEYS = {
    "candidate_count",
    "case_id",
    "client_count",
    "context_call_count",
    "doc_id_shorts",
    "endpoint_count",
    "endpoint_kinds",
    "hashes",
    "lane_chars",
    "lane_injected",
    "lengths",
    "passage_count",
    "payload_objects_retained",
    "query_kind",
    "reason_code",
    "selected_count",
    "status",
}


def run_smokes(
    *,
    cases: Sequence[BiblioSmokeCase] = DEFAULT_SMOKE_CASES,
    turn_runner: SmokeTurnRunner = run_biblio_chat_turn,
    client_factory: Any = CatalogueClient,
    config_module: Any = None,
    raw_markers: Sequence[str] = DEFAULT_RAW_MARKERS,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for case in cases:
        result = turn_runner(
            {"biblio_enabled": True},
            user_msg=case.message,
            client_factory=client_factory,
            config_module=config_module,
        )
        records.append(_record_for_result(case.case_id, result, raw_markers=raw_markers))
    return records


def _record_for_result(
    case_id: str,
    result: BiblioChatResult,
    *,
    raw_markers: Sequence[str],
) -> dict[str, Any]:
    event = dict(result.observability_payload or {})
    context = result.context_result.to_observability() if result.context_result is not None else {}
    lane = _lane_observability(result.prompt_lane)
    client = event.get("client") if isinstance(event.get("client"), Mapping) else {}
    counts = event.get("counts") if isinstance(event.get("counts"), Mapping) else {}
    endpoint_kinds = _endpoint_kinds(client, context)
    passage_count = _to_int(lane.get("passage_count")) or _to_int(counts.get("passage_count"))
    lane_chars = _to_int(lane.get("chars")) or _to_int(counts.get("lane_chars"))
    prompt_content = (result.prompt_message or {}).get("content") if result.prompt_message else ""
    source_projection = {
        "event": event,
        "context": context,
        "lane": lane,
    }
    base_record = {
        "case_id": case_id,
        "status": _safe_text(event.get("status")),
        "reason_code": _safe_text(event.get("reason_code")),
        "query_kind": _safe_text(result.query_kind or event.get("query_kind")),
        "client_count": _to_int(client.get("event_count")),
        "endpoint_count": _to_int(context.get("endpoint_count")) or _to_int(client.get("event_count")),
        "endpoint_kinds": endpoint_kinds,
        "candidate_count": _to_int(context.get("candidate_count")),
        "context_call_count": _to_int(context.get("context_call_count")),
        "selected_count": _to_int(context.get("selected_count")),
        "passage_count": passage_count,
        "lane_injected": result.prompt_message is not None,
        "lane_chars": lane_chars,
        "doc_id_shorts": _doc_id_shorts(lane, context),
        "hashes": _hashes(lane, context),
        "lengths": {
            "lane_chars": lane_chars,
            "prompt_chars": len(prompt_content) if isinstance(prompt_content, str) else 0,
            "passage_chars": _to_int(context.get("passage_chars")) or _to_int(counts.get("passage_chars")),
        },
        "payload_objects_retained": _payload_objects_retained(result),
    }
    return _finalize_record(
        base_record,
        raw_markers=raw_markers,
        source_projection=source_projection,
    )


def _lane_observability(value: Any) -> dict[str, Any]:
    to_observability = getattr(value, "to_observability", None)
    if callable(to_observability):
        observed = to_observability()
        if isinstance(observed, Mapping):
            return dict(observed)
    return {}


def _endpoint_kinds(client: Mapping[str, Any], context: Mapping[str, Any]) -> list[str]:
    kinds: set[str] = set()
    for item in client.get("items") or []:
        if isinstance(item, Mapping) and item.get("endpoint_kind"):
            kinds.add(_safe_text(item.get("endpoint_kind")))
    for item in context.get("endpoint_kinds") or []:
        if item:
            kinds.add(_safe_text(item))
    return sorted(kind for kind in kinds if kind)


def _doc_id_shorts(lane: Mapping[str, Any], context: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for source in (
        lane.get("doc_id_shorts"),
        context.get("doc_id_short"),
        (context.get("candidate_search") or {}).get("doc_id_shorts")
        if isinstance(context.get("candidate_search"), Mapping)
        else (),
    ):
        if isinstance(source, str):
            values.append(source)
        elif isinstance(source, Sequence) and not isinstance(source, (bytes, bytearray, str)):
            values.extend(_safe_text(item) for item in source if item)
    return list(dict.fromkeys(item for item in values if item))


def _hashes(lane: Mapping[str, Any], context: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for source in (lane.get("hashes"), context.get("passage_hash")):
        if isinstance(source, str):
            values.append(source)
        elif isinstance(source, Sequence) and not isinstance(source, (bytes, bytearray, str)):
            values.extend(_safe_text(item) for item in source if item)
    return list(dict.fromkeys(item for item in values if item))


def _payload_objects_retained(result: BiblioChatResult) -> int:
    total = 0
    context = result.context_result
    if context is None:
        return total
    candidate_result = context.candidate_result
    if candidate_result is not None:
        total += sum(1 for item in candidate_result.endpoint_observations if hasattr(item, "payload"))
    total += sum(1 for item in context.context_observations if hasattr(item, "payload"))
    return total


def _finalize_record(
    record: Mapping[str, Any],
    *,
    raw_markers: Sequence[str],
    source_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    sanitized = {key: record[key] for key in sorted(_OUTPUT_KEYS) if key in record}
    source_leaks = _contains_raw_marker(source_projection or {}, raw_markers)
    record_leaks = _contains_raw_marker(record, raw_markers) or _contains_raw_marker(sanitized, raw_markers)
    sanitized["raw_marker_leaks"] = bool(source_leaks or record_leaks)
    return sanitized


def smoke_record_violations(record: Mapping[str, Any]) -> tuple[str, ...]:
    violations: list[str] = []
    if bool(record.get("raw_marker_leaks")):
        violations.append("raw_marker_leaks")
    if _to_int(record.get("payload_objects_retained")) > 0:
        violations.append("payload_objects_retained")
    return tuple(violations)


def smoke_exit_code(records: Sequence[Mapping[str, Any]], *, strict: bool = True) -> int:
    if not strict:
        return EXIT_OK
    for record in records:
        if smoke_record_violations(record):
            return EXIT_CONTENT_FREE_VIOLATION
    return EXIT_OK


def _contains_raw_marker(value: Any, raw_markers: Sequence[str]) -> bool:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return any(marker in encoded for marker in raw_markers if marker)


def _to_int(value: Any) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return 0


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run content-free Biblio live smokes.")
    parser.add_argument("--jsonl", action="store_true", help="Print one JSON object per line.")
    parser.add_argument(
        "--no-strict",
        action="store_true",
        help="Print records even if content-free guardrails fail and exit 0.",
    )
    args = parser.parse_args(argv)
    records = run_smokes()
    if args.jsonl:
        for record in records:
            print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True))
    return smoke_exit_code(records, strict=not args.no_strict)


if __name__ == "__main__":
    raise SystemExit(main())
