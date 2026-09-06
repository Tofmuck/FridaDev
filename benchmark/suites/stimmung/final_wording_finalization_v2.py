from __future__ import annotations

from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from benchmark.suites.stimmung import final_wording_execution_v2 as execution_v2
from benchmark.suites.stimmung import final_wording_protocol_v2 as protocol_v2
from benchmark.suites.stimmung import final_wording_rating_v2 as rating_v2


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_object_snapshot(path: Path, reason: str) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError(reason) from None
    if not isinstance(value, dict):
        raise ValueError(reason)
    return value, hashlib.sha256(raw).hexdigest()


def _load_object(path: Path, reason: str) -> dict[str, Any]:
    return _load_object_snapshot(path, reason)[0]


def _same_identity(left: Any, right: Any) -> bool:
    return type(left) is type(right) and left == right


def load_historical_protocol(
    repo_root: Path,
    *,
    freeze_commit: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Rebuild the frozen calendar without reinterpreting later runtime hashes."""

    try:
        protocol = protocol_v2._build_unfrozen_protocol(
            repo_root,
            freeze_commit=freeze_commit,
        )
        manifest = _load_object(
            protocol_v2.freeze_manifest_path(repo_root),
            "historical_calendar_provenance_invalid",
        )
        frozen_inputs = manifest.get("frozen_inputs")
        if not isinstance(frozen_inputs, Mapping):
            raise ValueError("historical_calendar_provenance_invalid")
        protocol["input_fingerprints"] = copy.deepcopy(dict(frozen_inputs))
        if protocol_v2.expected_freeze_manifest(protocol, repo_root) != manifest:
            raise ValueError("historical_calendar_provenance_invalid")
        schedule = protocol_v2._build_request_schedule(repo_root)
        protocol_v2.validate_schedule(protocol_v2.load_corpus(repo_root), schedule)
    except ValueError as exc:
        if str(exc) in {
            "historical_calendar_provenance_invalid",
            "historical_calendar_fingerprint_invalid",
        }:
            raise
        raise ValueError("historical_calendar_provenance_invalid") from None

    schedule_sha = protocol_v2._sha256_text(
        _compact_json(protocol_v2._schedule_fingerprint(schedule))
    )
    manifest_schedule = manifest.get("schedule")
    if (
        schedule_sha != protocol.get("schedule_sha256")
        or not isinstance(manifest_schedule, Mapping)
        or schedule_sha != manifest_schedule.get("sha256")
        or len(schedule) != manifest_schedule.get("call_count")
    ):
        raise ValueError("historical_calendar_fingerprint_invalid")
    return protocol, schedule


def _validate_preblind_paths(
    *,
    campaign_dir: Path,
    rating_packet_path: Path,
    ratings_path: Path,
    durable_output: Path,
) -> tuple[Path, Path, Path, Path]:
    campaign = campaign_dir.resolve()
    packet = rating_packet_path.resolve()
    ratings = ratings_path.resolve()
    durable = durable_output.resolve()
    review = packet.parent
    campaign_staged = rating_v2._purge_staging_path(campaign)
    review_staged = rating_v2._purge_staging_path(review)
    if (
        campaign == durable
        or campaign in durable.parents
        or review == durable
        or review in durable.parents
        or campaign_staged == durable
        or campaign_staged in durable.parents
        or review_staged == durable
        or review_staged in durable.parents
    ):
        raise ValueError("durable_output_must_be_outside_temporary_campaign_directory")
    if durable.exists():
        raise ValueError("durable_output_already_exists")
    if campaign in packet.parents or campaign in ratings.parents:
        raise ValueError("review_material_must_be_outside_private_campaign_directory")
    if packet.parent != ratings.parent:
        raise ValueError("ratings_must_share_review_export_directory")
    ledger = campaign / "call_ledger.json"
    for path in (packet, ratings, ledger):
        if not path.is_file() or path.stat().st_mode & 0o077:
            raise ValueError("private_workflow_file_missing_or_permissions_invalid")
    if packet.parent.stat().st_mode & 0o077 or campaign.stat().st_mode & 0o077:
        raise ValueError("private_workflow_directory_permissions_invalid")
    if {path.name for path in packet.parent.iterdir()} != {packet.name, ratings.name}:
        raise ValueError("review_export_contains_unexpected_files")
    return campaign, packet, ratings, durable


def _validate_unblinded_paths(
    *,
    campaign: Path,
    mapping_path: Path,
    private_outputs_path: Path,
) -> None:
    ledger_path = campaign / "call_ledger.json"
    if {path.name for path in campaign.iterdir()} != {
        mapping_path.name,
        ledger_path.name,
        private_outputs_path.name,
    }:
        raise ValueError("private_campaign_contains_unexpected_files")
    for path in (mapping_path, private_outputs_path):
        if not path.is_file() or path.stat().st_mode & 0o077:
            raise ValueError("private_workflow_file_missing_or_permissions_invalid")


def _validate_workflow_provenance(
    *,
    protocol: Mapping[str, Any],
    packet: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> None:
    expected = {
        "protocol_sha256": protocol_v2.protocol_sha256(protocol),
        "freeze_commit": protocol["freeze_commit"],
        "corpus_sha256": protocol["input_fingerprints"]["corpus_v2_sha256"],
        "schedule_sha256": protocol["schedule_sha256"],
        "model": protocol["model"],
        "runtime_parameters_sha256": execution_v2._runtime_parameters_sha(protocol),
        "planned_call_count": protocol["expected_call_count"],
        "absolute_call_cap": protocol["absolute_call_cap"],
        "absolute_cost_cap_usd": protocol["absolute_cost_cap_usd"],
    }
    if any(ledger.get(key) != value for key, value in expected.items()):
        raise ValueError("historical_workflow_provenance_invalid")
    if (
        packet.get("protocol_sha256") != expected["protocol_sha256"]
        or packet.get("evidence_source") != ledger.get("evidence_source")
    ):
        raise ValueError("historical_workflow_provenance_invalid")


def validate_attribution_bijection(
    *,
    protocol: Mapping[str, Any],
    schedule: Sequence[Mapping[str, Any]],
    packet: Mapping[str, Any],
    mapping_by_id: Mapping[str, Mapping[str, Any]],
    ledger: Mapping[str, Any],
) -> None:
    expected_sequences = set(range(1, int(protocol["expected_call_count"]) + 1))
    records = ledger.get("records")
    if not isinstance(records, list):
        raise ValueError("attribution_sequence_bijection_invalid")
    raw_schedule_sequences = [item.get("sequence") for item in schedule]
    raw_ledger_sequences = [item.get("sequence") for item in records]
    raw_mapping_sequences = [
        slot.get("sequence")
        for item in mapping_by_id.values()
        for slot in item.get("slots", {}).values()
    ]
    if any(
        type(sequence) is not int
        for sequence in (
            *raw_schedule_sequences,
            *raw_ledger_sequences,
            *raw_mapping_sequences,
        )
    ):
        raise ValueError("attribution_sequence_bijection_invalid")
    schedule_sequences = [int(sequence) for sequence in raw_schedule_sequences]
    ledger_sequences = [int(sequence) for sequence in raw_ledger_sequences]
    mapping_sequences = [int(sequence) for sequence in raw_mapping_sequences]
    if (
        Counter(schedule_sequences) != Counter(expected_sequences)
        or Counter(ledger_sequences) != Counter(expected_sequences)
        or Counter(mapping_sequences) != Counter(expected_sequences)
    ):
        raise ValueError("attribution_sequence_bijection_invalid")

    schedule_by_sequence = {int(item["sequence"]): item for item in schedule}
    ledger_by_sequence = {int(item["sequence"]): item for item in records}
    packet_by_id = {str(item["blind_id"]): item for item in packet["items"]}
    expected_blind_ids: set[str] = set()
    protocol_sha = protocol_v2.protocol_sha256(protocol)
    linked_sequences: set[int] = set()
    for sequence in sorted(expected_sequences):
        calendar = schedule_by_sequence[sequence]
        record = ledger_by_sequence[sequence]
        for key, ledger_key in (
            ("case_id", "case_id"),
            ("repetition", "repetition"),
            ("comparison_kind", "comparison_kind"),
            ("blind_slot", "blind_slot"),
            ("messages_sha256", "messages_sha256"),
        ):
            if not _same_identity(calendar.get(key), record.get(ledger_key)):
                raise ValueError("attribution_calendar_ledger_mismatch")

        blind_id = execution_v2._blind_id(
            protocol_sha,
            str(calendar["case_id"]),
            int(calendar["repetition"]),
        )
        expected_blind_ids.add(blind_id)
        mapping = mapping_by_id.get(blind_id)
        packet_item = packet_by_id.get(blind_id)
        if mapping is None or packet_item is None:
            raise ValueError("attribution_mapping_calendar_mismatch")
        if (
            not _same_identity(mapping.get("case_id"), calendar.get("case_id"))
            or not _same_identity(mapping.get("repetition"), calendar.get("repetition"))
            or not _same_identity(
                mapping.get("comparison_kind"), calendar.get("comparison_kind")
            )
            or not _same_identity(
                packet_item.get("comparison_kind"), calendar.get("comparison_kind")
            )
        ):
            raise ValueError("attribution_mapping_calendar_mismatch")
        slot_name = str(calendar["blind_slot"])
        slot = mapping.get("slots", {}).get(slot_name)
        if (
            not isinstance(slot, Mapping)
            or not _same_identity(slot.get("sequence"), sequence)
            or not _same_identity(slot.get("variant"), calendar.get("variant"))
        ):
            raise ValueError("attribution_mapping_calendar_mismatch")
        if not _same_identity(slot.get("output_sha256"), record.get("output_sha256")):
            raise ValueError("attribution_mapping_ledger_output_mismatch")
        linked_sequences.add(sequence)

    if set(mapping_by_id) != expected_blind_ids or linked_sequences != expected_sequences:
        raise ValueError("attribution_sequence_bijection_invalid")


def _validate_ratings_and_ratification_before_unblinding(
    *,
    packet: Mapping[str, Any],
    ledger: Mapping[str, Any],
    ratings: Mapping[str, Any],
    ratings_sha: str,
    ratification_path: Path | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    packet_summary = rating_v2.validate_packet(packet)
    ratings_by_id = rating_v2.validate_ratings(
        ratings,
        packet=packet,
        evidence_source=str(ledger["evidence_source"]),
    )
    rating_source = str(ratings["rating_source"])
    ratification_sha: str | None = None
    ratification_source: str | None = None
    if rating_source == "codex_assisted_review_for_tof":
        if ratification_path is None:
            return (
                {
                    "status": "human_ratification_required",
                    "decision": None,
                    "reason_code": "codex_assisted_rating_requires_tof_ratification",
                    "packet_sha256": packet_summary["packet_sha256"],
                    "ratings_sha256": ratings_sha,
                    "rating_source": rating_source,
                },
                None,
            )
        ratification = ratification_path.resolve()
        if not ratification.is_file() or ratification.stat().st_mode & 0o077:
            raise ValueError("ratification_file_missing_or_permissions_invalid")
        value, ratification_sha = _load_object_snapshot(
            ratification,
            "ratification_fields_invalid",
        )
        decision = rating_v2.validate_ratification(
            value,
            packet_sha256=packet_summary["packet_sha256"],
            ratings_sha256=ratings_sha,
        )
        if decision == "refuse":
            return (
                {
                    "status": "human_ratification_required",
                    "decision": None,
                    "reason_code": "tof_ratification_refused",
                    "packet_sha256": packet_summary["packet_sha256"],
                    "ratings_sha256": ratings_sha,
                    "rating_source": rating_source,
                },
                None,
            )
        ratification_source = "tof_human_ratification"
    elif ratification_path is not None:
        raise ValueError("ratification_only_allowed_for_codex_assisted_review")
    return (
        None,
        {
            "packet_summary": packet_summary,
            "ratings_by_id": ratings_by_id,
            "rating_source": rating_source,
            "ratification_source": ratification_source,
            "ratification_sha256": ratification_sha,
        },
    )


def finalize_campaign(
    *,
    repo_root: Path,
    freeze_commit: str,
    campaign_dir: Path,
    rating_packet_path: Path,
    ratings_path: Path,
    durable_output: Path,
    ratification_path: Path | None = None,
) -> dict[str, Any]:
    campaign, packet_path, resolved_ratings, durable = _validate_preblind_paths(
        campaign_dir=campaign_dir,
        rating_packet_path=rating_packet_path,
        ratings_path=ratings_path,
        durable_output=durable_output,
    )
    ledger_path = campaign / "call_ledger.json"
    packet, packet_file_sha = _load_object_snapshot(
        packet_path,
        "rating_packet_fields_invalid",
    )
    ledger, ledger_file_sha = _load_object_snapshot(
        ledger_path,
        "call_ledger_fields_invalid",
    )
    ratings, ratings_file_sha = _load_object_snapshot(
        resolved_ratings,
        "ratings_invalid",
    )
    rating_v2.validate_packet(packet)
    rating_v2.validate_ledger(ledger, require_complete=True)
    if (
        packet.get("protocol_sha256") != ledger.get("protocol_sha256")
        or packet.get("evidence_source") != ledger.get("evidence_source")
    ):
        raise ValueError("workflow_provenance_mismatch")
    pending, rating_snapshot = _validate_ratings_and_ratification_before_unblinding(
        packet=packet,
        ledger=ledger,
        ratings=ratings,
        ratings_sha=ratings_file_sha,
        ratification_path=ratification_path,
    )
    if pending is not None:
        return pending
    if rating_snapshot is None:
        raise ValueError("historical_attribution_guard_required")

    protocol, schedule = load_historical_protocol(
        repo_root.resolve(),
        freeze_commit=freeze_commit,
    )
    _validate_workflow_provenance(protocol=protocol, packet=packet, ledger=ledger)
    mapping_path = campaign / "blind_mapping.json"
    private_outputs_path = campaign / "private_outputs.json"
    _validate_unblinded_paths(
        campaign=campaign,
        mapping_path=mapping_path,
        private_outputs_path=private_outputs_path,
    )
    mapping, mapping_file_sha = _load_object_snapshot(
        mapping_path,
        "blind_mapping_fields_invalid",
    )
    mapping_by_id = rating_v2.validate_mapping(mapping, packet)
    validate_attribution_bijection(
        protocol=protocol,
        schedule=schedule,
        packet=packet,
        mapping_by_id=mapping_by_id,
        ledger=ledger,
    )
    ratification_file_sha = rating_snapshot["ratification_sha256"]
    return rating_v2._finalize_after_attribution_guard(
        campaign_dir=campaign,
        rating_packet_path=packet_path,
        ratings_path=resolved_ratings,
        ratification_path=ratification_path,
        durable_output=durable,
        _attribution_guard=rating_v2._ATTRIBUTION_GUARD_CAPABILITY,
        _attribution_snapshot={
            "packet": packet,
            "ledger": ledger,
            "ratings_by_id": rating_snapshot["ratings_by_id"],
            "mapping_by_id": mapping_by_id,
            "packet_summary": rating_snapshot["packet_summary"],
            "rating_source": rating_snapshot["rating_source"],
            "ratification_source": rating_snapshot["ratification_source"],
            "artifact_source_fingerprints": {
                "packet_sha256": rating_snapshot["packet_summary"]["packet_sha256"],
                "mapping_sha256": mapping_file_sha,
                "ledger_sha256": ledger_file_sha,
                "ratings_sha256": ratings_file_sha,
                "ratification_sha256": ratification_file_sha,
            },
            "file_fingerprints": {
                "packet_sha256": packet_file_sha,
                "mapping_sha256": mapping_file_sha,
                "ledger_sha256": ledger_file_sha,
                "ratings_sha256": ratings_file_sha,
                "ratification_sha256": ratification_file_sha,
            },
        },
    )
