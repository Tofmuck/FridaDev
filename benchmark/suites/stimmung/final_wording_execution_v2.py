from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

from benchmark.core.openrouter import OpenRouterClient
from benchmark.suites.stimmung import final_wording_protocol_v2 as protocol_v2
from benchmark.suites.stimmung import final_wording_rating_v2 as rating_v2


_ALLOWED_OBSERVED_MODELS = {
    "openai/gpt-5.1",
    "openai/gpt-5.1-20251113",
    "openai/gpt-5.1-2025-11-13",
}
_VALID_STATUSES = {"valid", "transport_error", "timeout", "refusal", "length"}


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
        error_kind = str(response.get("error") or "").casefold()
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
            "status": "transport_error",
            "reason_code": "unexpected_finish_reason",
        }
    if observed_model == "unknown" or observed_provider != "openai":
        return {**base, "status": "transport_error", "reason_code": "route_mismatch"}
    return {**base, "status": "valid", "reason_code": "valid_complete_output"}


def _validate_output_dir(repo_root: Path, output_dir: Path) -> Path:
    if not output_dir.is_absolute():
        raise ValueError("temporary_output_directory_must_be_absolute")
    resolved = output_dir.resolve()
    tmp_root = Path("/tmp").resolve()
    repo = repo_root.resolve()
    if resolved == repo or repo in resolved.parents:
        raise ValueError("raw_packet_inside_repo_forbidden")
    if resolved == tmp_root or tmp_root not in resolved.parents:
        raise ValueError("temporary_output_directory_must_be_under_tmp")
    if resolved.exists():
        raise ValueError("temporary_output_directory_already_exists")
    if not resolved.parent.is_dir():
        raise ValueError("temporary_output_parent_missing")
    return resolved


def _write_private_json(path: Path, value: Mapping[str, Any]) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))
            handle.write("\n")
    except Exception:
        path.unlink(missing_ok=True)
        raise


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
        "messages_sha256": str(plan["messages_sha256"]),
        "raw_content_included": False,
        "exception_text_included": False,
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
        "absolute_countercase": {
            "formulation_fit": sorted(rating_v2._ABSOLUTE_FIT_VALUES),
            "artificial_caution": sorted(rating_v2._ABSOLUTE_FAULT_VALUES),
            "psychologization": sorted(rating_v2._ABSOLUTE_FAULT_VALUES),
            "certainty_change": sorted(rating_v2._ABSOLUTE_FAULT_VALUES),
            "truth_or_evidence_change": sorted(rating_v2._ABSOLUTE_FAULT_VALUES),
            "masked_target": sorted(rating_v2._ABSOLUTE_FAULT_VALUES),
        },
    }


def _blind_id(protocol_sha: str, case_id: str, repetition: int) -> str:
    material = f"{protocol_sha}:{case_id}:{repetition}:lot4c4-v2"
    return f"FW2-{_sha256_text(material)[:16]}"


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
    for case in [item for item in corpus["cases"] if item["provider_eligible"]]:
        for repetition in (1, 2):
            key = (str(case["id"]), repetition)
            arms = grouped.get(key, [])
            expected_arm_count = 2 if case["enunciation_state"] == "transition_delicate" else 1
            if len(arms) != expected_arm_count:
                raise ValueError("rating_material_call_group_incomplete")
            kind = (
                "causal_transition"
                if case["enunciation_state"] == "transition_delicate"
                else "absolute_countercase"
            )
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


def run_campaign(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    client: Any,
    output_dir: Path,
    execution_authorized: bool,
    evidence_source: str,
    progress: Any | None = None,
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
    schedule = protocol_v2.build_request_schedule(repo_root, protocol)
    if len(schedule) != 36 or len(schedule) > int(protocol["absolute_call_cap"]):
        raise ValueError("absolute_call_cap_invalid")
    resolved_output = _validate_output_dir(repo_root, output_dir)
    resolved_output.mkdir(mode=0o700)
    if resolved_output.stat().st_mode & 0o077:
        raise ValueError("temporary_output_directory_permissions_invalid")

    executions: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    ledger_records: list[dict[str, Any]] = []
    cumulative_accounted = 0.0
    cumulative_observed = 0.0
    try:
        for plan in schedule:
            if len(executions) >= int(protocol["absolute_call_cap"]):
                raise ValueError("call_cap_would_be_exceeded")
            planned_ceiling = float(plan["calculated_ceiling_cost_usd"])
            if cumulative_accounted + planned_ceiling > float(protocol["absolute_cost_cap_usd"]):
                raise ValueError("cost_cap_would_be_exceeded")
            try:
                response = client.chat_completion(
                    copy.deepcopy(dict(plan["payload"])),
                    caller="llm",
                    timeout_s=protocol_v2.ACTIVE_TIMEOUT_S,
                )
            except Exception as exc:
                response = {
                    "ok": False,
                    "status_code": None,
                    "error": type(exc).__name__,
                    "raw_text": None,
                    "finish_reason": None,
                    "native_finish_reason": None,
                    "usage": {},
                    "cost_estimate_usd": None,
                    "model": "",
                    "provider": "",
                }
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
            observed_cost = outcome.get("cost_usd")
            accounted_increment = (
                float(observed_cost) if observed_cost is not None else planned_ceiling
            )
            cumulative_accounted = round(cumulative_accounted + accounted_increment, 8)
            if observed_cost is not None:
                cumulative_observed = round(cumulative_observed + float(observed_cost), 8)
            if cumulative_accounted > float(protocol["absolute_cost_cap_usd"]):
                raise ValueError("absolute_cost_cap_exceeded")
            executions.append((plan, outcome))
            ledger_records.append(
                _call_ledger_record(plan, outcome, accounted_cost=accounted_increment)
            )
            if callable(progress):
                progress(int(plan["sequence"]), len(schedule), ledger_records[-1])
        if len(executions) != 36:
            raise ValueError("campaign_attempt_count_incomplete")
        protocol_sha = protocol_v2.protocol_sha256(protocol)
        corpus = protocol_v2.load_corpus(repo_root)
        packet, mapping = _build_rating_material(
            corpus=corpus,
            protocol_sha=protocol_sha,
            evidence_source=evidence_source,
            executions=executions,
        )
        status_counts = _counter([str(record["status"]) for record in ledger_records])
        ledger = {
            "schema_version": rating_v2.LEDGER_SCHEMA_VERSION,
            "protocol_sha256": protocol_sha,
            "evidence_source": evidence_source,
            "planned_call_count": len(schedule),
            "attempted_call_count": len(executions),
            "outputs_complete": status_counts == {"valid": 36},
            "status_counts": status_counts,
            "finish_reason_counts": _counter(
                [str(record["finish_reason"]) for record in ledger_records]
            ),
            "observed_model_counts": _counter(
                [str(record["observed_model"]) for record in ledger_records]
            ),
            "observed_provider_counts": _counter(
                [str(record["observed_provider"]) for record in ledger_records]
            ),
            "observed_cost_usd": cumulative_observed,
            "accounted_cost_usd": cumulative_accounted,
            "absolute_cost_cap_usd": protocol["absolute_cost_cap_usd"],
            "records": ledger_records,
        }
        rating_v2.validate_ledger(ledger)
        _write_private_json(resolved_output / "rating_packet.json", packet)
        _write_private_json(resolved_output / "blind_mapping.json", mapping)
        _write_private_json(resolved_output / "call_ledger.json", ledger)
    except Exception:
        for path in resolved_output.iterdir():
            path.unlink(missing_ok=True)
        resolved_output.rmdir()
        raise
    return {
        "status": "human_rating_required",
        "decision": None,
        "evidence_source": evidence_source,
        "attempted_call_count": len(executions),
        "outputs_complete": ledger["outputs_complete"],
        "packet_sha256": packet["packet_sha256"],
        "temporary_directory": str(resolved_output),
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
    parser = argparse.ArgumentParser(description="Lot 4C.4 v2 bounded main-model campaign")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    if args.dry_run and args.execute_live:
        raise SystemExit("--dry-run and --execute-live are mutually exclusive")
    if not args.dry_run and not args.execute_live:
        raise SystemExit("offline by default: use --dry-run or an explicit future --execute-live GO")
    if args.execute_live and args.output_dir is None:
        raise SystemExit("--output-dir under /tmp is required for live execution")
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
    _validate_output_dir(args.repo_root, args.output_dir)
    client = OpenRouterClient.from_env(title="FridaDev/Lot4C4-Final-Wording-v2")

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
        execution_authorized=True,
        evidence_source="main_model_provider",
        progress=progress,
    )
    print(_compact_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
