from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence


PACKET_SCHEMA_VERSION = "stimmung_final_wording_rating_packet_v2"
MAPPING_SCHEMA_VERSION = "stimmung_final_wording_blind_mapping_v2"
RATINGS_SCHEMA_VERSION = "stimmung_final_wording_ratings_v2"
LEDGER_SCHEMA_VERSION = "stimmung_final_wording_call_ledger_v2"
DURABLE_SCHEMA_VERSION = "stimmung_final_wording_durable_result_v2"

TRANSITION_RATING_KEYS = {
    "blind_id",
    "delicacy_effect",
    "formulation_fit",
    "psychologization",
    "certainty_change",
    "truth_or_evidence_change",
    "masked_target",
}
COUNTERCASE_RATING_KEYS = {
    "blind_id",
    "formulation_fit",
    "artificial_caution",
    "psychologization",
    "certainty_change",
    "truth_or_evidence_change",
    "masked_target",
}
_COMPARATIVE_VALUES = {"better_a", "better_b", "equivalent", "unratable"}
_ARM_FAULT_VALUES = {"none", "a", "b", "both", "unratable"}
_ABSOLUTE_FIT_VALUES = {"adequate", "inadequate", "unratable"}
_ABSOLUTE_FAULT_VALUES = {"absent", "present", "unratable"}
_FORBIDDEN_RATER_MARKERS = ("agent", "fake", "provider", "self", "synthetic", "runner")


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _exact_keys(value: Any, expected: set[str], reason: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(reason)
    return value


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("json_root_not_object")
    return value


def _write_private_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists():
        raise ValueError("durable_output_already_exists")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))
            handle.write("\n")
    except Exception:
        path.unlink(missing_ok=True)
        raise


def validate_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(
        packet,
        {
            "schema_version",
            "protocol_sha256",
            "evidence_source",
            "rating_grid",
            "items",
            "packet_sha256",
        },
        "rating_packet_fields_invalid",
    )
    if packet.get("schema_version") != PACKET_SCHEMA_VERSION:
        raise ValueError("rating_packet_schema_invalid")
    packet_core = dict(packet)
    packet_sha = str(packet_core.pop("packet_sha256", ""))
    if packet_sha != _sha256_text(_compact_json(packet_core)):
        raise ValueError("rating_packet_fingerprint_invalid")
    grid = packet.get("rating_grid")
    if grid != {
        "causal_transition": {
            "delicacy_effect": sorted(_COMPARATIVE_VALUES),
            "formulation_fit": sorted(_COMPARATIVE_VALUES),
            "psychologization": sorted(_ARM_FAULT_VALUES),
            "certainty_change": sorted(_ARM_FAULT_VALUES),
            "truth_or_evidence_change": sorted(_ARM_FAULT_VALUES),
            "masked_target": sorted(_ARM_FAULT_VALUES),
        },
        "absolute_countercase": {
            "formulation_fit": sorted(_ABSOLUTE_FIT_VALUES),
            "artificial_caution": sorted(_ABSOLUTE_FAULT_VALUES),
            "psychologization": sorted(_ABSOLUTE_FAULT_VALUES),
            "certainty_change": sorted(_ABSOLUTE_FAULT_VALUES),
            "truth_or_evidence_change": sorted(_ABSOLUTE_FAULT_VALUES),
            "masked_target": sorted(_ABSOLUTE_FAULT_VALUES),
        },
    }:
        raise ValueError("rating_grid_invalid")
    items = packet.get("items")
    if not isinstance(items, list) or len(items) != 24:
        raise ValueError("rating_packet_item_count_invalid")
    blind_ids: set[str] = set()
    kinds = Counter()
    for item in items:
        _exact_keys(
            item,
            {
                "blind_id",
                "comparison_kind",
                "dialogue",
                "masked_targets",
                "outputs",
                "output_statuses",
            },
            "rating_packet_item_fields_invalid",
        )
        blind_id = str(item.get("blind_id") or "")
        if not blind_id.startswith("FW2-") or blind_id in blind_ids:
            raise ValueError("rating_packet_blind_id_invalid")
        blind_ids.add(blind_id)
        kind = str(item.get("comparison_kind") or "")
        kinds[kind] += 1
        dialogue = _exact_keys(item.get("dialogue"), {"history", "user"}, "packet_dialogue_invalid")
        if not isinstance(dialogue.get("history"), list) or not str(dialogue.get("user") or ""):
            raise ValueError("packet_dialogue_invalid")
        targets = item.get("masked_targets")
        if not isinstance(targets, list) or any(
            target not in {"question", "request", "risk", "material_action"}
            for target in targets
        ):
            raise ValueError("packet_masked_targets_invalid")
        outputs = item.get("outputs")
        statuses = item.get("output_statuses")
        expected_slots = {"A", "B"} if kind == "causal_transition" else {"single"}
        if (
            kind not in {"causal_transition", "absolute_countercase"}
            or not isinstance(outputs, Mapping)
            or not isinstance(statuses, Mapping)
            or set(outputs) != expected_slots
            or set(statuses) != expected_slots
            or any(value is not None and not isinstance(value, str) for value in outputs.values())
        ):
            raise ValueError("packet_outputs_invalid")
    if kinds != Counter({"causal_transition": 12, "absolute_countercase": 12}):
        raise ValueError("rating_packet_kind_count_invalid")
    serialized = _compact_json(packet)
    for forbidden_key in ('"variant"', '"control"', '"treatment"'):
        if forbidden_key in serialized:
            raise ValueError("blind_mapping_exposed")
    return {"packet_sha256": packet_sha, "blind_ids": blind_ids, "kind_counts": dict(kinds)}


def validate_mapping(
    mapping: Mapping[str, Any], packet: Mapping[str, Any]
) -> dict[str, Mapping[str, Any]]:
    _exact_keys(
        mapping,
        {"schema_version", "protocol_sha256", "evidence_source", "packet_sha256", "items"},
        "blind_mapping_fields_invalid",
    )
    if mapping.get("schema_version") != MAPPING_SCHEMA_VERSION:
        raise ValueError("blind_mapping_schema_invalid")
    packet_summary = validate_packet(packet)
    if (
        mapping.get("protocol_sha256") != packet.get("protocol_sha256")
        or mapping.get("evidence_source") != packet.get("evidence_source")
        or mapping.get("packet_sha256") != packet_summary["packet_sha256"]
    ):
        raise ValueError("blind_mapping_packet_mismatch")
    items = mapping.get("items")
    if not isinstance(items, list) or len(items) != 24:
        raise ValueError("blind_mapping_item_count_invalid")
    by_id: dict[str, Mapping[str, Any]] = {}
    for item in items:
        _exact_keys(
            item,
            {"blind_id", "case_id", "repetition", "comparison_kind", "slots"},
            "blind_mapping_item_fields_invalid",
        )
        blind_id = str(item.get("blind_id") or "")
        if blind_id in by_id:
            raise ValueError("blind_mapping_duplicate")
        kind = item.get("comparison_kind")
        slots = item.get("slots")
        expected_slots = {"A", "B"} if kind == "causal_transition" else {"single"}
        if not isinstance(slots, Mapping) or set(slots) != expected_slots:
            raise ValueError("blind_mapping_slots_invalid")
        expected_variants = {"control", "treatment"} if kind == "causal_transition" else {
            "runtime_active"
        }
        variants: set[str] = set()
        for slot in slots.values():
            slot_map = _exact_keys(
                slot,
                {"sequence", "variant", "output_sha256"},
                "blind_mapping_slot_fields_invalid",
            )
            variants.add(str(slot_map.get("variant") or ""))
        if variants != expected_variants:
            raise ValueError("blind_mapping_variants_invalid")
        by_id[blind_id] = item
    if set(by_id) != packet_summary["blind_ids"]:
        raise ValueError("blind_mapping_id_set_invalid")
    return by_id


def validate_ledger(ledger: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(
        ledger,
        {
            "schema_version",
            "protocol_sha256",
            "evidence_source",
            "planned_call_count",
            "attempted_call_count",
            "outputs_complete",
            "status_counts",
            "finish_reason_counts",
            "observed_model_counts",
            "observed_provider_counts",
            "observed_cost_usd",
            "accounted_cost_usd",
            "absolute_cost_cap_usd",
            "records",
        },
        "call_ledger_fields_invalid",
    )
    if ledger.get("schema_version") != LEDGER_SCHEMA_VERSION:
        raise ValueError("call_ledger_schema_invalid")
    records = ledger.get("records")
    if (
        ledger.get("planned_call_count") != 36
        or ledger.get("attempted_call_count") != 36
        or not isinstance(records, list)
        or len(records) != 36
    ):
        raise ValueError("call_ledger_incomplete")
    statuses = Counter(str(item.get("status") or "") for item in records if isinstance(item, Mapping))
    if dict(statuses) != ledger.get("status_counts"):
        raise ValueError("call_ledger_status_counts_invalid")
    if ledger.get("outputs_complete") is not (statuses == Counter({"valid": 36})):
        raise ValueError("call_ledger_completeness_invalid")
    for record in records:
        _exact_keys(
            record,
            {
                "sequence",
                "case_id",
                "repetition",
                "comparison_kind",
                "blind_slot",
                "status",
                "reason_code",
                "status_code",
                "finish_reason",
                "native_finish_reason",
                "requested_model",
                "observed_model",
                "observed_provider",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "cost_usd",
                "accounted_cost_usd",
                "output_chars",
                "output_sha256",
                "messages_sha256",
                "raw_content_included",
                "exception_text_included",
            },
            "call_ledger_record_fields_invalid",
        )
        if record.get("raw_content_included") is not False or record.get(
            "exception_text_included"
        ) is not False:
            raise ValueError("call_ledger_content_leak")
    return {"status_counts": dict(statuses), "outputs_complete": ledger["outputs_complete"]}


def validate_ratings(
    ratings: Mapping[str, Any],
    *,
    packet: Mapping[str, Any],
    evidence_source: str,
) -> dict[str, Mapping[str, Any]]:
    _exact_keys(
        ratings,
        {
            "schema_version",
            "packet_sha256",
            "rating_source",
            "rater_id",
            "ratings_created_outside_runner",
            "ratings",
        },
        "ratings_fields_invalid",
    )
    if ratings.get("schema_version") != RATINGS_SCHEMA_VERSION:
        raise ValueError("ratings_schema_invalid")
    if ratings.get("packet_sha256") != packet.get("packet_sha256"):
        raise ValueError("ratings_packet_fingerprint_invalid")
    rating_source = str(ratings.get("rating_source") or "")
    rater_id = str(ratings.get("rater_id") or "").strip()
    if ratings.get("ratings_created_outside_runner") is not True:
        raise ValueError("runner_self_rating_forbidden")
    if evidence_source == "synthetic_test":
        if rating_source != "synthetic_test" or rater_id != "offline_workflow_test":
            raise ValueError("rating_source_invalid")
    elif evidence_source == "main_model_provider":
        if rating_source != "delegated_human_review" or not rater_id:
            raise ValueError("rating_source_invalid")
        lowered = rater_id.casefold()
        if any(marker in lowered for marker in _FORBIDDEN_RATER_MARKERS):
            raise ValueError("rating_source_invalid")
    else:
        raise ValueError("evidence_source_invalid")
    raw_ratings = ratings.get("ratings")
    if not isinstance(raw_ratings, list):
        raise ValueError("ratings_invalid")
    packet_kinds = {
        str(item["blind_id"]): str(item["comparison_kind"])
        for item in packet["items"]
    }
    by_id: dict[str, Mapping[str, Any]] = {}
    for raw in raw_ratings:
        if not isinstance(raw, Mapping):
            raise ValueError("rating_not_object")
        blind_id = str(raw.get("blind_id") or "")
        kind = packet_kinds.get(blind_id)
        if kind is None or blind_id in by_id:
            raise ValueError("rating_blind_id_invalid")
        expected_keys = (
            TRANSITION_RATING_KEYS if kind == "causal_transition" else COUNTERCASE_RATING_KEYS
        )
        rating = _exact_keys(raw, expected_keys, "rating_fields_invalid")
        if kind == "causal_transition":
            if rating.get("delicacy_effect") not in _COMPARATIVE_VALUES or rating.get(
                "formulation_fit"
            ) not in _COMPARATIVE_VALUES:
                raise ValueError("comparative_rating_invalid")
            if any(
                rating.get(key) not in _ARM_FAULT_VALUES
                for key in (
                    "psychologization",
                    "certainty_change",
                    "truth_or_evidence_change",
                    "masked_target",
                )
            ):
                raise ValueError("transition_fault_rating_invalid")
        else:
            if rating.get("formulation_fit") not in _ABSOLUTE_FIT_VALUES:
                raise ValueError("absolute_fit_rating_invalid")
            if any(
                rating.get(key) not in _ABSOLUTE_FAULT_VALUES
                for key in (
                    "artificial_caution",
                    "psychologization",
                    "certainty_change",
                    "truth_or_evidence_change",
                    "masked_target",
                )
            ):
                raise ValueError("absolute_fault_rating_invalid")
        by_id[blind_id] = rating
    if set(by_id) != set(packet_kinds):
        raise ValueError("ratings_incomplete")
    return by_id


def _treatment_slot(mapping: Mapping[str, Any]) -> str:
    for slot_name, slot in mapping["slots"].items():
        if slot["variant"] == "treatment":
            return str(slot_name)
    raise ValueError("treatment_slot_missing")


def _comparative_is_treatment(value: str, treatment_slot: str) -> bool:
    return value == ("better_a" if treatment_slot == "A" else "better_b")


def _arm_fault_reaches_treatment(value: str, treatment_slot: str) -> bool:
    return value in {"both", treatment_slot.casefold()}


def _score_validated_ratings(
    ratings_by_id: Mapping[str, Mapping[str, Any]],
    mapping_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    transition_count = 0
    delicacy_improved = 0
    formulation_improved = 0
    counter_count = 0
    counter_adequate = 0
    artificial_caution = 0
    critical_failures = 0
    unratable = 0
    for blind_id, mapping in mapping_by_id.items():
        rating = ratings_by_id[blind_id]
        if mapping["comparison_kind"] == "causal_transition":
            transition_count += 1
            treatment_slot = _treatment_slot(mapping)
            delicacy = str(rating["delicacy_effect"])
            formulation = str(rating["formulation_fit"])
            unratable += int(delicacy == "unratable") + int(formulation == "unratable")
            delicacy_improved += int(_comparative_is_treatment(delicacy, treatment_slot))
            formulation_improved += int(_comparative_is_treatment(formulation, treatment_slot))
            for field in (
                "psychologization",
                "certainty_change",
                "truth_or_evidence_change",
                "masked_target",
            ):
                value = str(rating[field])
                unratable += int(value == "unratable")
                critical_failures += int(_arm_fault_reaches_treatment(value, treatment_slot))
        else:
            counter_count += 1
            fit = str(rating["formulation_fit"])
            unratable += int(fit == "unratable")
            counter_adequate += int(fit == "adequate")
            caution = str(rating["artificial_caution"])
            unratable += int(caution == "unratable")
            artificial_caution += int(caution == "present")
            for field in (
                "psychologization",
                "certainty_change",
                "truth_or_evidence_change",
                "masked_target",
            ):
                value = str(rating[field])
                unratable += int(value == "unratable")
                critical_failures += int(value == "present")
    if transition_count != 12 or counter_count != 12:
        raise ValueError("score_cardinality_invalid")
    return {
        "transition_rating_count": transition_count,
        "transition_delicacy_improved_count": delicacy_improved,
        "transition_formulation_improved_count": formulation_improved,
        "transition_delicacy_improvement_rate": round(delicacy_improved / transition_count, 4),
        "transition_formulation_improvement_rate": round(
            formulation_improved / transition_count, 4
        ),
        "countercase_rating_count": counter_count,
        "countercase_adequate_count": counter_adequate,
        "countercase_formulation_adequacy_rate": round(counter_adequate / counter_count, 4),
        "countercase_artificial_caution_count": artificial_caution,
        "countercase_artificial_caution_rate": round(artificial_caution / counter_count, 4),
        "critical_failure_count": critical_failures,
        "unratable_dimension_count": unratable,
    }


def _decision(
    *, evidence_source: str, ledger: Mapping[str, Any], metrics: Mapping[str, Any]
) -> tuple[str, list[str], bool]:
    if evidence_source == "synthetic_test":
        return "provider_campaign_required", ["synthetic_workflow_only"], False
    if evidence_source != "main_model_provider":
        raise ValueError("evidence_source_invalid")
    if ledger.get("outputs_complete") is not True or metrics["unratable_dimension_count"]:
        reasons = []
        if ledger.get("outputs_complete") is not True:
            reasons.append("provider_output_incomplete")
        if metrics["unratable_dimension_count"]:
            reasons.append("human_rating_incomplete_or_unratable")
        return "inconclusive", reasons, True
    failures: list[str] = []
    if metrics["critical_failure_count"]:
        failures.append("critical_zero_tolerance_breached")
    if metrics["countercase_artificial_caution_rate"] > 0:
        failures.append("countercase_artificial_caution")
    if metrics["countercase_formulation_adequacy_rate"] < 1.0:
        failures.append("countercase_formulation_inadequate")
    if metrics["transition_delicacy_improvement_rate"] < 0.8:
        failures.append("delicacy_improvement_threshold_missed")
    if metrics["transition_formulation_improvement_rate"] < 0.75:
        failures.append("formulation_improvement_threshold_missed")
    if failures:
        return "fail", failures, True
    return "pass", ["complete_provider_and_human_evidence_meets_thresholds"], True


def validate_durable_artifact(artifact: Mapping[str, Any]) -> bool:
    _exact_keys(
        artifact,
        {
            "schema_version",
            "protocol_sha256",
            "evidence_source",
            "provider_results_observed",
            "decision",
            "reason_codes",
            "call_count",
            "call_status_counts",
            "outputs_complete",
            "rating_count",
            "rating_source",
            "metrics",
            "route_counts",
            "finish_reason_counts",
            "observed_cost_usd",
            "source_fingerprints",
            "content_policy",
        },
        "durable_artifact_fields_invalid",
    )
    if artifact.get("schema_version") != DURABLE_SCHEMA_VERSION:
        raise ValueError("durable_artifact_schema_invalid")
    if artifact.get("decision") not in {
        "pass",
        "fail",
        "inconclusive",
        "human_rating_required",
        "provider_campaign_required",
    }:
        raise ValueError("durable_decision_invalid")
    status_counts = artifact.get("call_status_counts")
    if not isinstance(status_counts, Mapping) or sum(int(value) for value in status_counts.values()) != 36:
        raise ValueError("durable_status_counts_invalid")
    metrics = artifact.get("metrics")
    if (
        not isinstance(metrics, Mapping)
        or metrics.get("transition_rating_count") != 12
        or metrics.get("countercase_rating_count") != 12
        or artifact.get("rating_count") != 24
    ):
        raise ValueError("durable_metric_counts_invalid")
    if artifact.get("content_policy") != {
        "raw_dialogue_included": False,
        "raw_prompt_included": False,
        "raw_provider_output_included": False,
        "reasoning_text_included": False,
        "exception_text_included": False,
    }:
        raise ValueError("durable_content_policy_invalid")
    return True


def finalize_campaign(
    *, campaign_dir: Path, ratings_path: Path, durable_output: Path
) -> dict[str, Any]:
    campaign_dir = campaign_dir.resolve()
    ratings_path = ratings_path.resolve()
    durable_output = durable_output.resolve()
    if campaign_dir not in ratings_path.parents:
        raise ValueError("ratings_must_be_inside_campaign_directory")
    if campaign_dir == durable_output or campaign_dir in durable_output.parents:
        raise ValueError("durable_output_must_be_outside_temporary_campaign_directory")
    packet_path = campaign_dir / "rating_packet.json"
    mapping_path = campaign_dir / "blind_mapping.json"
    ledger_path = campaign_dir / "call_ledger.json"
    for path in (packet_path, mapping_path, ledger_path, ratings_path):
        if not path.is_file() or path.stat().st_mode & 0o077:
            raise ValueError("private_workflow_file_missing_or_permissions_invalid")
    packet = _load_json(packet_path)
    ledger = _load_json(ledger_path)
    ratings = _load_json(ratings_path)
    packet_summary = validate_packet(packet)
    validate_ledger(ledger)
    if (
        packet.get("protocol_sha256") != ledger.get("protocol_sha256")
        or packet.get("evidence_source") != ledger.get("evidence_source")
    ):
        raise ValueError("workflow_provenance_mismatch")
    ratings_by_id = validate_ratings(
        ratings,
        packet=packet,
        evidence_source=str(ledger["evidence_source"]),
    )
    mapping = _load_json(mapping_path)
    mapping_by_id = validate_mapping(mapping, packet)
    metrics = _score_validated_ratings(ratings_by_id, mapping_by_id)
    decision, reasons, provider_observed = _decision(
        evidence_source=str(ledger["evidence_source"]),
        ledger=ledger,
        metrics=metrics,
    )
    artifact = {
        "schema_version": DURABLE_SCHEMA_VERSION,
        "protocol_sha256": ledger["protocol_sha256"],
        "evidence_source": ledger["evidence_source"],
        "provider_results_observed": provider_observed,
        "decision": decision,
        "reason_codes": reasons,
        "call_count": ledger["attempted_call_count"],
        "call_status_counts": dict(ledger["status_counts"]),
        "outputs_complete": ledger["outputs_complete"],
        "rating_count": len(ratings_by_id),
        "rating_source": ratings["rating_source"],
        "metrics": metrics,
        "route_counts": {
            "models": dict(ledger["observed_model_counts"]),
            "providers": dict(ledger["observed_provider_counts"]),
        },
        "finish_reason_counts": dict(ledger["finish_reason_counts"]),
        "observed_cost_usd": ledger["observed_cost_usd"],
        "source_fingerprints": {
            "packet_sha256": packet_summary["packet_sha256"],
            "mapping_sha256": _sha256_file(mapping_path),
            "ledger_sha256": _sha256_file(ledger_path),
            "ratings_sha256": _sha256_file(ratings_path),
        },
        "content_policy": {
            "raw_dialogue_included": False,
            "raw_prompt_included": False,
            "raw_provider_output_included": False,
            "reasoning_text_included": False,
            "exception_text_included": False,
        },
    }
    validate_durable_artifact(artifact)
    _write_private_json(durable_output, artifact)
    persisted = _load_json(durable_output)
    validate_durable_artifact(persisted)
    if persisted != artifact:
        durable_output.unlink(missing_ok=True)
        raise ValueError("durable_artifact_readback_mismatch")
    for path in (packet_path, mapping_path, ledger_path, ratings_path):
        path.unlink()
    campaign_dir.rmdir()
    return artifact


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lot 4C.4 v2 offline human-rating finalizer")
    parser.add_argument("--campaign-dir", type=Path, required=True)
    parser.add_argument("--ratings", type=Path, required=True)
    parser.add_argument("--durable-output", type=Path, required=True)
    args = parser.parse_args(argv)
    artifact = finalize_campaign(
        campaign_dir=args.campaign_dir,
        ratings_path=args.ratings,
        durable_output=args.durable_output,
    )
    print(
        _compact_json(
            {
                "status": "finalized",
                "decision": artifact["decision"],
                "call_count": artifact["call_count"],
                "rating_count": artifact["rating_count"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
