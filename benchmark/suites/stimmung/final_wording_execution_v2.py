from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Mapping, Sequence

from benchmark.core.openrouter import OpenRouterClient
from benchmark.suites.stimmung import final_wording_protocol_v2 as protocol_v2
from benchmark.suites.stimmung import final_wording_rating_v2 as rating_v2


_ALLOWED_OBSERVED_MODELS = {
    "openai/gpt-5.1",
    "openai/gpt-5.1-20251113",
    "openai/gpt-5.1-2025-11-13",
}
_VALID_STATUSES = {
    "valid",
    "transport_error",
    "timeout",
    "refusal",
    "length",
    "provider_auth_error",
    "provider_routing_error",
    "provider_request_error",
    "provider_server_error",
    "provider_schema_error",
}
_CAMPAIGN_TERMINAL_REASONS = {
    "provider_attempt_outcome_unknown",
    "provider_outputs_incomplete",
    "call_cap_would_be_exceeded",
    "cost_cap_would_be_exceeded",
    "absolute_cost_cap_exceeded",
    "canary_provider_auth_error",
    "canary_provider_routing_error",
    "canary_provider_request_error",
    "provider_auth_error",
    "provider_routing_error",
    "provider_request_error",
}
PRIVATE_OUTPUTS_SCHEMA_VERSION = "stimmung_final_wording_private_outputs_v2_4"
_NONRECOVERABLE_PROVIDER_STATUSES = {
    "provider_auth_error",
    "provider_routing_error",
    "provider_request_error",
}


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _int_metric(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if 0 <= result <= 10_000_000 else None


def _float_metric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return round(result, 8) if 0 <= result <= 1_000_000 else None


def _closed_finish_reason(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in {"stop", "length", "content_filter", "error"} else "unknown"


def _closed_provider(value: Any) -> str:
    text = str(value or "").strip().casefold()
    return "openai" if "openai" in text else "unknown"


def _classify_provider_result(response: Mapping[str, Any]) -> dict[str, Any]:
    raw_text = str(response.get("raw_text") or "").strip()
    observed_model_raw = str(response.get("model") or "").strip()
    observed_model = (
        observed_model_raw if observed_model_raw in _ALLOWED_OBSERVED_MODELS else "unknown"
    )
    observed_provider = _closed_provider(response.get("provider"))
    finish_reason = _closed_finish_reason(response.get("finish_reason"))
    native_finish_reason = _closed_finish_reason(response.get("native_finish_reason"))
    usage = response.get("usage") if isinstance(response.get("usage"), Mapping) else {}
    base = {
        "status_code": _int_metric(response.get("status_code")),
        "finish_reason": finish_reason,
        "native_finish_reason": native_finish_reason,
        "requested_model": protocol_v2.ACTIVE_MAIN_MODEL,
        "observed_model": observed_model,
        "observed_provider": observed_provider,
        "prompt_tokens": _int_metric(usage.get("prompt_tokens")),
        "completion_tokens": _int_metric(usage.get("completion_tokens")),
        "total_tokens": _int_metric(usage.get("total_tokens")),
        "cost_usd": _float_metric(response.get("cost_estimate_usd")),
        "raw_text": raw_text or None,
    }
    if not response.get("ok"):
        status_code = base["status_code"]
        error_kind = str(response.get("error") or "").casefold()
        if status_code in {401, 403}:
            return {
                **base,
                "status": "provider_auth_error",
                "reason_code": "provider_auth_error",
            }
        if status_code == 404:
            return {
                **base,
                "status": "provider_routing_error",
                "reason_code": "provider_routing_error",
            }
        if status_code is not None and 400 <= status_code < 500:
            return {
                **base,
                "status": "provider_request_error",
                "reason_code": "provider_request_error",
            }
        if status_code is not None and 500 <= status_code < 600:
            return {
                **base,
                "status": "provider_server_error",
                "reason_code": "provider_server_error",
            }
        if "invalid_transport_result" in error_kind:
            return {
                **base,
                "status": "provider_schema_error",
                "reason_code": "provider_schema_error",
            }
        timeout = "timeout" in error_kind or "timed out" in error_kind
        return {
            **base,
            "status": "timeout" if timeout else "transport_error",
            "reason_code": "timeout" if timeout else "transport_error",
        }
    if not raw_text:
        return {**base, "status": "refusal", "reason_code": "empty_provider_output"}
    if finish_reason == "length" or native_finish_reason == "length":
        return {**base, "status": "length", "reason_code": "provider_length_termination"}
    if finish_reason != "stop":
        return {
            **base,
            "status": "provider_schema_error",
            "reason_code": "unexpected_finish_reason",
        }
    if observed_model == "unknown" or observed_provider != "openai":
        return {**base, "status": "provider_routing_error", "reason_code": "route_mismatch"}
    return {**base, "status": "valid", "reason_code": "valid_complete_output"}


def _validate_tmp_path(repo_root: Path, path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError("temporary_output_directory_must_be_absolute")
    resolved = path.resolve()
    tmp_root = Path("/tmp").resolve()
    repo = repo_root.resolve()
    if resolved == repo or repo in resolved.parents:
        raise ValueError("raw_packet_inside_repo_forbidden")
    if resolved == tmp_root or tmp_root not in resolved.parents:
        raise ValueError("temporary_output_directory_must_be_under_tmp")
    if not resolved.parent.is_dir():
        raise ValueError("temporary_output_parent_missing")
    return resolved


def _validate_output_dir(repo_root: Path, output_dir: Path, *, resume: bool = False) -> Path:
    resolved = _validate_tmp_path(repo_root, output_dir)
    if resume:
        if not resolved.is_dir() or resolved.stat().st_mode & 0o077:
            raise ValueError("resume_campaign_directory_missing_or_permissions_invalid")
    elif resolved.exists():
        raise ValueError("temporary_output_directory_already_exists")
    return resolved


def _validate_review_export_dir(
    repo_root: Path,
    campaign_dir: Path,
    review_export_dir: Path,
    *,
    resume: bool = False,
) -> Path:
    resolved = _validate_tmp_path(repo_root, review_export_dir)
    campaign = campaign_dir.resolve()
    if resolved == campaign or campaign in resolved.parents or resolved in campaign.parents:
        raise ValueError("review_export_must_be_separate_from_private_campaign")
    if resolved.exists():
        if not resume or not resolved.is_dir() or resolved.stat().st_mode & 0o077:
            raise ValueError("review_export_directory_already_exists")
        unexpected = {path.name for path in resolved.iterdir()} - {"rating_packet.json"}
        if unexpected:
            raise ValueError("review_export_contains_unexpected_files")
    return resolved


def expected_live_campaign_paths(protocol: Mapping[str, Any]) -> tuple[Path, Path]:
    freeze_commit = str(protocol.get("freeze_commit") or "")
    if len(freeze_commit) != 40:
        raise ValueError("freeze_commit_invalid")
    stem = f"lot4c4-final-wording-v2.4-{freeze_commit[:12]}"
    return Path(f"/tmp/{stem}-private"), Path(f"/tmp/{stem}-review")


def _validate_live_campaign_paths(
    protocol: Mapping[str, Any], output_dir: Path, review_export_dir: Path
) -> None:
    expected_private, expected_review = expected_live_campaign_paths(protocol)
    if output_dir.resolve() != expected_private or review_export_dir.resolve() != expected_review:
        raise ValueError("live_campaign_paths_must_match_frozen_campaign_identity")


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write_private_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, exist_ok=True)
    if path.parent.stat().st_mode & 0o077:
        raise ValueError("private_directory_permissions_invalid")
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        os.chmod(path, 0o600)
        _fsync_directory(path.parent)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def _planned_ledger_record(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "sequence": int(plan["sequence"]),
        "case_id": str(plan["case_id"]),
        "repetition": int(plan["repetition"]),
        "comparison_kind": str(plan["comparison_kind"]),
        "blind_slot": str(plan["blind_slot"]),
        "messages_sha256": str(plan["messages_sha256"]),
        "calculated_ceiling_cost_usd": float(plan["calculated_ceiling_cost_usd"]),
        "attempt_state": "planned",
        "status": None,
        "reason_code": "not_attempted",
        "status_code": None,
        "finish_reason": "unknown",
        "native_finish_reason": "unknown",
        "requested_model": protocol_v2.ACTIVE_MAIN_MODEL,
        "observed_model": "unknown",
        "observed_provider": "unknown",
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "cost_usd": None,
        "accounted_cost_usd": 0.0,
        "output_chars": 0,
        "output_sha256": "",
        "raw_content_included": False,
        "exception_text_included": False,
    }


def _call_ledger_record(
    plan: Mapping[str, Any], outcome: Mapping[str, Any], *, accounted_cost: float
) -> dict[str, Any]:
    raw_text = str(outcome.get("raw_text") or "")
    return {
        "sequence": int(plan["sequence"]),
        "case_id": str(plan["case_id"]),
        "repetition": int(plan["repetition"]),
        "comparison_kind": str(plan["comparison_kind"]),
        "blind_slot": str(plan["blind_slot"]),
        "messages_sha256": str(plan["messages_sha256"]),
        "calculated_ceiling_cost_usd": float(plan["calculated_ceiling_cost_usd"]),
        "attempt_state": "completed",
        "status": str(outcome["status"]),
        "reason_code": str(outcome["reason_code"]),
        "status_code": outcome["status_code"],
        "finish_reason": str(outcome["finish_reason"]),
        "native_finish_reason": str(outcome["native_finish_reason"]),
        "requested_model": str(outcome["requested_model"]),
        "observed_model": str(outcome["observed_model"]),
        "observed_provider": str(outcome["observed_provider"]),
        "prompt_tokens": outcome["prompt_tokens"],
        "completion_tokens": outcome["completion_tokens"],
        "total_tokens": outcome["total_tokens"],
        "cost_usd": outcome["cost_usd"],
        "accounted_cost_usd": accounted_cost,
        "output_chars": len(raw_text),
        "output_sha256": _sha256_text(raw_text) if raw_text else "",
        "raw_content_included": False,
        "exception_text_included": False,
    }


def _attempt_started_record(record: Mapping[str, Any]) -> dict[str, Any]:
    started = copy.deepcopy(dict(record))
    if started.get("attempt_state") != "planned":
        raise ValueError("sequence_not_planned")
    started.update(
        {
            "attempt_state": "attempt_started",
            "reason_code": "attempt_started",
            "accounted_cost_usd": float(started["calculated_ceiling_cost_usd"]),
        }
    )
    return started


def _unknown_outcome_record(record: Mapping[str, Any]) -> dict[str, Any]:
    unknown = copy.deepcopy(dict(record))
    if unknown.get("attempt_state") != "attempt_started":
        raise ValueError("unknown_outcome_requires_started_attempt")
    unknown.update(
        {
            "attempt_state": "attempt_outcome_unknown",
            "status": "unknown",
            "reason_code": "provider_attempt_outcome_unknown",
            "accounted_cost_usd": float(unknown["calculated_ceiling_cost_usd"]),
        }
    )
    return unknown


def _runtime_parameters_sha(protocol: Mapping[str, Any]) -> str:
    return _sha256_text(
        _compact_json(
            {
                key: protocol[key]
                for key in (
                    "model",
                    "max_tokens",
                    "reasoning",
                    "required_endpoint_capabilities",
                    "timeout_s",
                    "transport_policy",
                )
            }
        )
    )


def _refresh_ledger(ledger: dict[str, Any]) -> None:
    records = ledger["records"]
    state_counts = Counter(str(record["attempt_state"]) for record in records)
    completed = [record for record in records if record["attempt_state"] == "completed"]
    attempted = len(records) - state_counts.get("planned", 0)
    ledger["attempted_call_count"] = attempted
    ledger["completed_call_count"] = state_counts.get("completed", 0)
    ledger["unknown_outcome_count"] = state_counts.get("attempt_outcome_unknown", 0)
    ledger["attempt_state_counts"] = dict(state_counts)
    ledger["status_counts"] = _counter([str(record["status"]) for record in completed])
    ledger["finish_reason_counts"] = _counter(
        [str(record["finish_reason"]) for record in completed]
    )
    ledger["observed_model_counts"] = _counter(
        [str(record["observed_model"]) for record in completed]
    )
    ledger["observed_provider_counts"] = _counter(
        [str(record["observed_provider"]) for record in completed]
    )
    ledger["observed_cost_usd"] = round(
        sum(float(record["cost_usd"] or 0.0) for record in completed),
        8,
    )
    ledger["accounted_cost_usd"] = round(
        sum(float(record["accounted_cost_usd"]) for record in records),
        8,
    )
    ledger["outputs_complete"] = (
        state_counts == Counter({"completed": protocol_v2.EXPECTED_CALLS})
        and ledger["status_counts"] == {"valid": protocol_v2.EXPECTED_CALLS}
    )


def _new_ledger(
    protocol: Mapping[str, Any],
    schedule: Sequence[Mapping[str, Any]],
    *,
    evidence_source: str,
) -> dict[str, Any]:
    ledger = {
        "schema_version": rating_v2.LEDGER_SCHEMA_VERSION,
        "protocol_sha256": protocol_v2.protocol_sha256(protocol),
        "freeze_commit": str(protocol["freeze_commit"]),
        "corpus_sha256": str(protocol["input_fingerprints"]["corpus_v2_sha256"]),
        "schedule_sha256": str(protocol["schedule_sha256"]),
        "model": str(protocol["model"]),
        "runtime_parameters_sha256": _runtime_parameters_sha(protocol),
        "evidence_source": evidence_source,
        "campaign_status": "running",
        "terminal_reason_code": None,
        "planned_call_count": len(schedule),
        "attempted_call_count": 0,
        "completed_call_count": 0,
        "unknown_outcome_count": 0,
        "outputs_complete": False,
        "attempt_state_counts": {},
        "status_counts": {},
        "finish_reason_counts": {},
        "observed_model_counts": {},
        "observed_provider_counts": {},
        "observed_cost_usd": 0.0,
        "accounted_cost_usd": 0.0,
        "absolute_call_cap": int(protocol["absolute_call_cap"]),
        "absolute_cost_cap_usd": float(protocol["absolute_cost_cap_usd"]),
        "records": [_planned_ledger_record(plan) for plan in schedule],
    }
    _refresh_ledger(ledger)
    return ledger


def _new_private_outputs(protocol_sha: str, evidence_source: str) -> dict[str, Any]:
    return {
        "schema_version": PRIVATE_OUTPUTS_SCHEMA_VERSION,
        "protocol_sha256": protocol_sha,
        "evidence_source": evidence_source,
        "outputs": {},
    }


def _rating_grid() -> dict[str, dict[str, list[str]]]:
    return {
        "causal_transition": {
            "delicacy_effect": sorted(rating_v2._COMPARATIVE_VALUES),
            "formulation_fit": sorted(rating_v2._COMPARATIVE_VALUES),
            "psychologization": sorted(rating_v2._ARM_FAULT_VALUES),
            "certainty_change": sorted(rating_v2._ARM_FAULT_VALUES),
            "truth_or_evidence_change": sorted(rating_v2._ARM_FAULT_VALUES),
            "masked_target": sorted(rating_v2._ARM_FAULT_VALUES),
        },
    }


def _blind_id(protocol_sha: str, case_id: str, repetition: int) -> str:
    material = f"{protocol_sha}:{case_id}:{repetition}:lot4c4-v2.4"
    return f"FW24-{_sha256_text(material)[:16]}"


def _build_rating_material(
    *,
    corpus: Mapping[str, Any],
    protocol_sha: str,
    evidence_source: str,
    executions: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    grouped: dict[tuple[str, int], list[tuple[Mapping[str, Any], Mapping[str, Any]]]] = {}
    for plan, outcome in executions:
        grouped.setdefault((str(plan["case_id"]), int(plan["repetition"])), []).append(
            (plan, outcome)
        )
    packet_items: list[dict[str, Any]] = []
    mapping_items: list[dict[str, Any]] = []
    for case in [
        item
        for item in corpus["cases"]
        if item["provider_eligible"] and item["enunciation_state"] == "transition_delicate"
    ]:
        for repetition in (1, 2):
            key = (str(case["id"]), repetition)
            arms = grouped.get(key, [])
            if len(arms) != 2:
                raise ValueError("rating_material_call_group_incomplete")
            kind = "causal_transition"
            blind_id = _blind_id(protocol_sha, str(case["id"]), repetition)
            outputs: dict[str, str | None] = {}
            statuses: dict[str, str] = {}
            slots: dict[str, dict[str, Any]] = {}
            for plan, outcome in arms:
                slot = str(plan["blind_slot"])
                raw_text = str(outcome.get("raw_text") or "")
                outputs[slot] = raw_text or None
                statuses[slot] = str(outcome["status"])
                slots[slot] = {
                    "sequence": int(plan["sequence"]),
                    "variant": str(plan["variant"]),
                    "output_sha256": _sha256_text(raw_text) if raw_text else "",
                }
            packet_items.append(
                {
                    "blind_id": blind_id,
                    "comparison_kind": kind,
                    "dialogue": copy.deepcopy(case["dialogue"]),
                    "masked_targets": copy.deepcopy(
                        case["expectations"]["final_text"]["masked_targets"]
                    ),
                    "outputs": outputs,
                    "output_statuses": statuses,
                }
            )
            mapping_items.append(
                {
                    "blind_id": blind_id,
                    "case_id": case["id"],
                    "repetition": repetition,
                    "comparison_kind": kind,
                    "slots": slots,
                }
            )
    packet_core = {
        "schema_version": rating_v2.PACKET_SCHEMA_VERSION,
        "protocol_sha256": protocol_sha,
        "evidence_source": evidence_source,
        "rating_grid": _rating_grid(),
        "items": packet_items,
    }
    packet = {**packet_core, "packet_sha256": _sha256_text(_compact_json(packet_core))}
    mapping = {
        "schema_version": rating_v2.MAPPING_SCHEMA_VERSION,
        "protocol_sha256": protocol_sha,
        "evidence_source": evidence_source,
        "packet_sha256": packet["packet_sha256"],
        "items": mapping_items,
    }
    rating_v2.validate_packet(packet)
    rating_v2.validate_mapping(mapping, packet)
    return packet, mapping


def _counter(values: Sequence[str]) -> dict[str, int]:
    return dict(Counter(values))


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("json_root_not_object")
    return value


def _invoke_fault(fault_injector: Any | None, stage: str, sequence: int) -> None:
    if callable(fault_injector):
        fault_injector(stage, sequence)


def _validate_resume_material(
    *,
    protocol: Mapping[str, Any],
    schedule: Sequence[Mapping[str, Any]],
    evidence_source: str,
    ledger: Mapping[str, Any],
    private_outputs: Mapping[str, Any],
) -> None:
    rating_v2.validate_ledger(ledger)
    expected_protocol_sha = protocol_v2.protocol_sha256(protocol)
    expected = {
        "protocol_sha256": expected_protocol_sha,
        "freeze_commit": str(protocol["freeze_commit"]),
        "corpus_sha256": str(protocol["input_fingerprints"]["corpus_v2_sha256"]),
        "schedule_sha256": str(protocol["schedule_sha256"]),
        "model": str(protocol["model"]),
        "runtime_parameters_sha256": _runtime_parameters_sha(protocol),
        "evidence_source": evidence_source,
        "planned_call_count": len(schedule),
        "absolute_call_cap": int(protocol["absolute_call_cap"]),
        "absolute_cost_cap_usd": float(protocol["absolute_cost_cap_usd"]),
    }
    if any(ledger.get(key) != value for key, value in expected.items()):
        raise ValueError("resume_protocol_or_freeze_mismatch")
    if set(private_outputs) != {
        "schema_version",
        "protocol_sha256",
        "evidence_source",
        "outputs",
    }:
        raise ValueError("private_outputs_fields_invalid")
    if (
        private_outputs.get("schema_version") != PRIVATE_OUTPUTS_SCHEMA_VERSION
        or private_outputs.get("protocol_sha256") != expected_protocol_sha
        or private_outputs.get("evidence_source") != evidence_source
        or not isinstance(private_outputs.get("outputs"), Mapping)
    ):
        raise ValueError("private_outputs_provenance_invalid")
    plans_by_sequence = {int(plan["sequence"]): plan for plan in schedule}
    outputs = private_outputs["outputs"]
    for record in ledger["records"]:
        sequence = int(record["sequence"])
        plan = plans_by_sequence.get(sequence)
        if plan is None or record["messages_sha256"] != plan["messages_sha256"]:
            raise ValueError("resume_schedule_record_mismatch")
        private = outputs.get(str(sequence))
        if record["attempt_state"] == "completed":
            if not isinstance(private, Mapping):
                raise ValueError("completed_attempt_private_output_missing")
            raw_text = str(private.get("raw_text") or "")
            if record["output_sha256"] != (_sha256_text(raw_text) if raw_text else ""):
                raise ValueError("private_output_fingerprint_mismatch")
            expected_record = _call_ledger_record(
                plan,
                private,
                accounted_cost=float(record["accounted_cost_usd"]),
            )
            if dict(record) != expected_record:
                raise ValueError("private_output_ledger_mismatch")
        elif private is not None and record["attempt_state"] != "attempt_started":
            raise ValueError("private_output_without_completed_attempt")


def _mark_started_as_unknown(ledger: dict[str, Any]) -> bool:
    changed = False
    for index, record in enumerate(ledger["records"]):
        if record["attempt_state"] == "attempt_started":
            ledger["records"][index] = _unknown_outcome_record(record)
            changed = True
    if changed:
        ledger["campaign_status"] = "campaign_incomplete"
        ledger["terminal_reason_code"] = "provider_attempt_outcome_unknown"
        _refresh_ledger(ledger)
    return changed


def _incomplete_result(
    ledger: dict[str, Any],
    ledger_path: Path,
    *,
    reason_code: str,
) -> dict[str, Any]:
    if reason_code not in _CAMPAIGN_TERMINAL_REASONS:
        raise ValueError("campaign_terminal_reason_invalid")
    ledger["campaign_status"] = "campaign_incomplete"
    ledger["terminal_reason_code"] = reason_code
    _refresh_ledger(ledger)
    _atomic_write_private_json(ledger_path, ledger)
    rating_v2.validate_ledger(ledger)
    return {
        "status": "campaign_incomplete",
        "decision": None,
        "reason_code": reason_code,
        "evidence_source": ledger["evidence_source"],
        "attempted_call_count": ledger["attempted_call_count"],
        "completed_call_count": ledger["completed_call_count"],
        "unknown_outcome_count": ledger["unknown_outcome_count"],
        "accounted_cost_usd": ledger["accounted_cost_usd"],
        "outputs_complete": False,
    }


def run_campaign(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    client: Any,
    output_dir: Path,
    review_export_dir: Path,
    execution_authorized: bool,
    evidence_source: str,
    progress: Any | None = None,
    capability_progress: Any | None = None,
    resume: bool = False,
    fault_injector: Any | None = None,
) -> dict[str, Any]:
    if execution_authorized is not True:
        raise ValueError("explicit_execution_authorization_required")
    if evidence_source not in {"synthetic_test", "main_model_provider"}:
        raise ValueError("evidence_source_invalid")
    if evidence_source == "main_model_provider" and not isinstance(client, OpenRouterClient):
        raise ValueError("provider_provenance_requires_openrouter_client")
    if evidence_source == "synthetic_test" and isinstance(client, OpenRouterClient):
        raise ValueError("synthetic_provenance_client_mismatch")
    protocol_v2.validate_protocol(protocol, repo_root)
    if evidence_source == "main_model_provider":
        _validate_live_campaign_paths(protocol, output_dir, review_export_dir)
    schedule = protocol_v2.build_request_schedule(repo_root, protocol)
    if len(schedule) != protocol_v2.EXPECTED_CALLS or len(schedule) > int(
        protocol["absolute_call_cap"]
    ):
        raise ValueError("absolute_call_cap_invalid")
    capability_preflight: dict[str, Any] | None = None
    if evidence_source == "main_model_provider":
        capability_preflight = client.preflight_model_capabilities(
            protocol_v2.ACTIVE_MAIN_MODEL,
            protocol_v2.REQUIRED_ENDPOINT_CAPABILITIES,
        )
        if callable(capability_progress):
            capability_progress(capability_preflight)
        if capability_preflight.get("status") != "compatible":
            return {
                "status": "campaign_incomplete",
                "decision": None,
                "reason_code": "no_compatible_provider_endpoint",
                "evidence_source": evidence_source,
                "attempted_call_count": 0,
                "completed_call_count": 0,
                "unknown_outcome_count": 0,
                "accounted_cost_usd": 0.0,
                "outputs_complete": False,
                "capability_preflight": capability_preflight,
            }
    resolved_output = _validate_output_dir(repo_root, output_dir, resume=resume)
    resolved_review = _validate_review_export_dir(
        repo_root,
        resolved_output,
        review_export_dir,
        resume=resume,
    )
    ledger_path = resolved_output / "call_ledger.json"
    private_outputs_path = resolved_output / "private_outputs.json"
    protocol_sha = protocol_v2.protocol_sha256(protocol)
    if resume:
        for path in (ledger_path, private_outputs_path):
            if not path.is_file() or path.stat().st_mode & 0o077:
                raise ValueError("resume_checkpoint_missing_or_permissions_invalid")
        ledger = _load_json(ledger_path)
        private_outputs = _load_json(private_outputs_path)
        _validate_resume_material(
            protocol=protocol,
            schedule=schedule,
            evidence_source=evidence_source,
            ledger=ledger,
            private_outputs=private_outputs,
        )
        started_sequences = [
            str(record["sequence"])
            for record in ledger["records"]
            if record["attempt_state"] == "attempt_started"
        ]
        if _mark_started_as_unknown(ledger):
            for sequence in started_sequences:
                private_outputs["outputs"].pop(sequence, None)
            _atomic_write_private_json(private_outputs_path, private_outputs)
            _atomic_write_private_json(ledger_path, ledger)
        if ledger["unknown_outcome_count"]:
            return _incomplete_result(
                ledger,
                ledger_path,
                reason_code="provider_attempt_outcome_unknown",
            )
        if ledger["campaign_status"] == "campaign_incomplete":
            return _incomplete_result(
                ledger,
                ledger_path,
                reason_code=str(ledger["terminal_reason_code"]),
            )
    else:
        resolved_output.mkdir(mode=0o700)
        _fsync_directory(resolved_output.parent)
        if resolved_output.stat().st_mode & 0o077:
            raise ValueError("temporary_output_directory_permissions_invalid")
        ledger = _new_ledger(protocol, schedule, evidence_source=evidence_source)
        private_outputs = _new_private_outputs(protocol_sha, evidence_source)
        _atomic_write_private_json(private_outputs_path, private_outputs)
        _atomic_write_private_json(ledger_path, ledger)

    for plan in schedule:
        sequence = int(plan["sequence"])
        record = ledger["records"][sequence - 1]
        if record["attempt_state"] == "completed":
            continue
        if record["attempt_state"] != "planned":
            raise ValueError("resume_attempt_state_incoherent")
        if int(ledger["attempted_call_count"]) >= int(protocol["absolute_call_cap"]):
            return _incomplete_result(
                ledger,
                ledger_path,
                reason_code="call_cap_would_be_exceeded",
            )
        planned_ceiling = float(plan["calculated_ceiling_cost_usd"])
        if (
            float(ledger["accounted_cost_usd"]) + planned_ceiling
            > float(protocol["absolute_cost_cap_usd"])
        ):
            return _incomplete_result(
                ledger,
                ledger_path,
                reason_code="cost_cap_would_be_exceeded",
            )
        _invoke_fault(fault_injector, "before_attempt_started_checkpoint", sequence)
        ledger["records"][sequence - 1] = _attempt_started_record(record)
        _refresh_ledger(ledger)
        _atomic_write_private_json(ledger_path, ledger)
        _invoke_fault(fault_injector, "after_attempt_started_checkpoint", sequence)
        try:
            response = client.chat_completion(
                copy.deepcopy(dict(plan["payload"])),
                caller="llm",
                timeout_s=protocol_v2.ACTIVE_TIMEOUT_S,
            )
            _invoke_fault(fault_injector, "after_provider_return", sequence)
            if not isinstance(response, Mapping):
                response = {
                    "ok": False,
                    "status_code": None,
                    "error": "invalid_transport_result",
                    "raw_text": None,
                    "finish_reason": None,
                    "native_finish_reason": None,
                    "usage": {},
                    "cost_estimate_usd": None,
                    "model": "",
                    "provider": "",
                }
            outcome = _classify_provider_result(response)
            if outcome["status"] not in _VALID_STATUSES:
                raise ValueError("provider_status_invalid")
            private_outputs["outputs"][str(sequence)] = copy.deepcopy(outcome)
            _atomic_write_private_json(private_outputs_path, private_outputs)
            _invoke_fault(fault_injector, "after_private_output_checkpoint", sequence)
            observed_cost = outcome.get("cost_usd")
            accounted_increment = (
                float(observed_cost) if observed_cost is not None else planned_ceiling
            )
            ledger["records"][sequence - 1] = _call_ledger_record(
                plan,
                outcome,
                accounted_cost=accounted_increment,
            )
            _refresh_ledger(ledger)
            if float(ledger["accounted_cost_usd"]) > float(protocol["absolute_cost_cap_usd"]):
                ledger["campaign_status"] = "campaign_incomplete"
                ledger["terminal_reason_code"] = "absolute_cost_cap_exceeded"
            _atomic_write_private_json(ledger_path, ledger)
            _invoke_fault(fault_injector, "after_completed_checkpoint", sequence)
        except BaseException:
            current = ledger["records"][sequence - 1]
            if current["attempt_state"] == "attempt_started":
                private_outputs["outputs"].pop(str(sequence), None)
                _atomic_write_private_json(private_outputs_path, private_outputs)
                ledger["records"][sequence - 1] = _unknown_outcome_record(current)
                ledger["campaign_status"] = "campaign_incomplete"
                ledger["terminal_reason_code"] = "provider_attempt_outcome_unknown"
                _refresh_ledger(ledger)
                _atomic_write_private_json(ledger_path, ledger)
            raise
        if ledger["campaign_status"] == "campaign_incomplete":
            return _incomplete_result(
                ledger,
                ledger_path,
                reason_code=str(ledger["terminal_reason_code"]),
            )
        completed_status = str(ledger["records"][sequence - 1]["status"])
        if completed_status in _NONRECOVERABLE_PROVIDER_STATUSES:
            reason_code = (
                f"canary_{completed_status}" if sequence == 1 else completed_status
            )
            return _incomplete_result(
                ledger,
                ledger_path,
                reason_code=reason_code,
            )
        if callable(progress):
            progress(sequence, len(schedule), ledger["records"][sequence - 1])

    _refresh_ledger(ledger)
    if (
        ledger["attempted_call_count"] != protocol_v2.EXPECTED_CALLS
        or ledger["completed_call_count"] != protocol_v2.EXPECTED_CALLS
    ):
        raise ValueError("campaign_attempt_count_incomplete")
    if not ledger["outputs_complete"]:
        return _incomplete_result(
            ledger,
            ledger_path,
            reason_code="provider_outputs_incomplete",
        )
    executions: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    for plan in schedule:
        outcome = private_outputs["outputs"].get(str(plan["sequence"]))
        if not isinstance(outcome, Mapping):
            raise ValueError("complete_campaign_private_output_missing")
        executions.append((plan, outcome))
    corpus = protocol_v2.load_corpus(repo_root)
    packet, mapping = _build_rating_material(
        corpus=corpus,
        protocol_sha=protocol_sha,
        evidence_source=evidence_source,
        executions=executions,
    )
    ledger["campaign_status"] = "human_rating_required"
    ledger["terminal_reason_code"] = None
    _atomic_write_private_json(ledger_path, ledger)
    rating_v2.validate_ledger(ledger, require_complete=True)
    _atomic_write_private_json(resolved_output / "blind_mapping.json", mapping)
    if not resolved_review.exists():
        resolved_review.mkdir(mode=0o700)
        _fsync_directory(resolved_review.parent)
    packet_path = resolved_review / "rating_packet.json"
    if packet_path.exists() and _load_json(packet_path) != packet:
        raise ValueError("review_packet_resume_mismatch")
    _atomic_write_private_json(packet_path, packet)
    return {
        "status": "human_rating_required",
        "decision": None,
        "evidence_source": evidence_source,
        "attempted_call_count": ledger["attempted_call_count"],
        "outputs_complete": True,
        "packet_sha256": packet["packet_sha256"],
        "private_campaign_directory": str(resolved_output),
        "review_export_directory": str(resolved_review),
    }


def _git_output(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def verify_live_preflight(repo_root: Path, *, freeze_commit: str) -> None:
    if _git_output(repo_root, "rev-parse", "HEAD") != freeze_commit:
        raise ValueError("live_freeze_commit_not_current_head")
    if _git_output(repo_root, "rev-parse", "@{upstream}") != freeze_commit:
        raise ValueError("live_freeze_commit_not_pushed_upstream")
    if _git_output(repo_root, "status", "--porcelain"):
        raise ValueError("live_worktree_not_clean")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lot 4C.4 v2.4 bounded-candidate campaign")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--review-export-dir", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    if args.dry_run and args.execute_live:
        raise SystemExit("--dry-run and --execute-live are mutually exclusive")
    if not args.dry_run and not args.execute_live:
        raise SystemExit("offline by default: use --dry-run or an explicit future --execute-live GO")
    if args.resume and not args.execute_live:
        raise SystemExit("--resume requires an explicit future --execute-live GO")
    if args.execute_live and (args.output_dir is None or args.review_export_dir is None):
        raise SystemExit(
            "--output-dir and a separate --review-export-dir under /tmp are required"
        )
    protocol = protocol_v2.build_protocol(
        args.repo_root,
        freeze_commit=args.freeze_commit,
    )
    summary = protocol_v2.validate_protocol(protocol, args.repo_root)
    if args.dry_run:
        print(
            _compact_json(
                {
                    **summary,
                    "status": "ready_offline",
                    "decision": "provider_campaign_required",
                    "protocol_sha256": protocol_v2.protocol_sha256(protocol),
                }
            )
        )
        return 0
    verify_live_preflight(args.repo_root, freeze_commit=args.freeze_commit)
    resolved_output = _validate_output_dir(
        args.repo_root,
        args.output_dir,
        resume=args.resume,
    )
    _validate_review_export_dir(
        args.repo_root,
        resolved_output,
        args.review_export_dir,
        resume=args.resume,
    )
    _validate_live_campaign_paths(protocol, args.output_dir, args.review_export_dir)
    client = OpenRouterClient.from_env(
        title="FridaDev/Lot4C4-Bounded-Enunciation-v2.4",
        fetch_pricing=False,
    )

    def capability_progress(summary: Mapping[str, Any]) -> None:
        print(
            _compact_json({"status": "capability_preflight", **dict(summary)}),
            flush=True,
        )

    def progress(current: int, total: int, _record: Mapping[str, Any]) -> None:
        if current == 1 or current % 6 == 0 or current == total:
            print(
                _compact_json({"status": "running", "completed": current, "total": total}),
                flush=True,
            )

    result = run_campaign(
        repo_root=args.repo_root,
        protocol=protocol,
        client=client,
        output_dir=args.output_dir,
        review_export_dir=args.review_export_dir,
        execution_authorized=True,
        evidence_source="main_model_provider",
        progress=progress,
        capability_progress=capability_progress,
        resume=args.resume,
    )
    print(_compact_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
