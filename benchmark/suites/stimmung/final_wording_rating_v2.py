from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence


PACKET_SCHEMA_VERSION = "stimmung_final_wording_rating_packet_v2_1"
MAPPING_SCHEMA_VERSION = "stimmung_final_wording_blind_mapping_v2_1"
RATINGS_SCHEMA_VERSION = "stimmung_final_wording_ratings_v2_1"
RATIFICATION_SCHEMA_VERSION = "stimmung_final_wording_tof_ratification_v2_1"
LEDGER_SCHEMA_VERSION = "stimmung_final_wording_call_ledger_v2_1"
DURABLE_SCHEMA_VERSION = "stimmung_final_wording_durable_result_v2_1"

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
_RATING_SOURCES = {
    "synthetic_test",
    "tof_human_review",
    "codex_assisted_review_for_tof",
}
_COMPLETED_REASON_CODES = {
    "valid_complete_output",
    "timeout",
    "transport_error",
    "empty_provider_output",
    "provider_length_termination",
    "unexpected_finish_reason",
    "route_mismatch",
}
_DURABLE_REASON_CODES = {
    "synthetic_workflow_only",
    "provider_output_incomplete",
    "human_rating_incomplete_or_unratable",
    "critical_zero_tolerance_breached",
    "countercase_artificial_caution",
    "countercase_formulation_inadequate",
    "delicacy_improvement_threshold_missed",
    "formulation_improvement_threshold_missed",
    "complete_provider_and_human_evidence_meets_thresholds",
}
_HEX = frozenset("0123456789abcdef")


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_hex_digest(value: Any, length: int) -> bool:
    text = str(value or "")
    return len(text) == length and all(char in _HEX for char in text)


def _exact_keys(value: Any, expected: set[str], reason: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(reason)
    return value


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("json_root_not_object")
    return value


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write_private_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists():
        raise ValueError("durable_output_already_exists")
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
            or any(status != "valid" for status in statuses.values())
        ):
            raise ValueError("packet_outputs_invalid")
    if kinds != Counter({"causal_transition": 12, "absolute_countercase": 12}):
        raise ValueError("rating_packet_kind_count_invalid")
    serialized = _compact_json(packet)
    for forbidden_key in (
        '"variant"',
        '"control"',
        '"treatment"',
        '"delicate_expression"',
        '"enunciation_directive"',
    ):
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
    packet_items = {str(item["blind_id"]): item for item in packet["items"]}
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
        packet_item = packet_items.get(blind_id)
        if packet_item is None:
            raise ValueError("blind_mapping_packet_item_missing")
        for slot_name, slot in slots.items():
            output = str(packet_item["outputs"].get(slot_name) or "")
            if slot.get("output_sha256") != (_sha256_text(output) if output else ""):
                raise ValueError("blind_mapping_output_fingerprint_invalid")
        if variants != expected_variants:
            raise ValueError("blind_mapping_variants_invalid")
        by_id[blind_id] = item
    if set(by_id) != packet_summary["blind_ids"]:
        raise ValueError("blind_mapping_id_set_invalid")
    return by_id


def validate_ledger(
    ledger: Mapping[str, Any], *, require_complete: bool = False
) -> dict[str, Any]:
    _exact_keys(
        ledger,
        {
            "schema_version",
            "protocol_sha256",
            "freeze_commit",
            "corpus_sha256",
            "schedule_sha256",
            "model",
            "runtime_parameters_sha256",
            "evidence_source",
            "campaign_status",
            "terminal_reason_code",
            "planned_call_count",
            "attempted_call_count",
            "completed_call_count",
            "unknown_outcome_count",
            "outputs_complete",
            "attempt_state_counts",
            "status_counts",
            "finish_reason_counts",
            "observed_model_counts",
            "observed_provider_counts",
            "observed_cost_usd",
            "accounted_cost_usd",
            "absolute_call_cap",
            "absolute_cost_cap_usd",
            "records",
        },
        "call_ledger_fields_invalid",
    )
    if ledger.get("schema_version") != LEDGER_SCHEMA_VERSION:
        raise ValueError("call_ledger_schema_invalid")
    if (
        not _is_hex_digest(ledger.get("protocol_sha256"), 64)
        or not _is_hex_digest(ledger.get("freeze_commit"), 40)
        or not _is_hex_digest(ledger.get("corpus_sha256"), 64)
        or not _is_hex_digest(ledger.get("schedule_sha256"), 64)
        or not _is_hex_digest(ledger.get("runtime_parameters_sha256"), 64)
        or ledger.get("model") != "openai/gpt-5.1"
        or ledger.get("evidence_source") not in {"synthetic_test", "main_model_provider"}
        or ledger.get("absolute_cost_cap_usd") != 4.0
    ):
        raise ValueError("call_ledger_provenance_invalid")
    records = ledger.get("records")
    if ledger.get("planned_call_count") != 36 or ledger.get("absolute_call_cap") != 36:
        raise ValueError("call_ledger_incomplete")
    if not isinstance(records, list) or len(records) != 36:
        raise ValueError("call_ledger_record_count_invalid")
    if ledger.get("campaign_status") not in {
        "running",
        "campaign_incomplete",
        "human_rating_required",
    }:
        raise ValueError("call_ledger_campaign_status_invalid")
    terminal_reason = ledger.get("terminal_reason_code")
    if terminal_reason not in {
        None,
        "provider_attempt_outcome_unknown",
        "provider_outputs_incomplete",
        "call_cap_would_be_exceeded",
        "cost_cap_would_be_exceeded",
        "absolute_cost_cap_exceeded",
    }:
        raise ValueError("call_ledger_terminal_reason_invalid")
    record_keys = {
        "sequence",
        "case_id",
        "repetition",
        "comparison_kind",
        "blind_slot",
        "messages_sha256",
        "calculated_ceiling_cost_usd",
        "attempt_state",
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
        "raw_content_included",
        "exception_text_included",
    }
    states = Counter()
    statuses = Counter()
    finish_reasons = Counter()
    models = Counter()
    providers = Counter()
    observed_cost = 0.0
    accounted_cost = 0.0
    valid_completed = 0
    allowed_statuses = {"valid", "transport_error", "timeout", "refusal", "length"}
    for expected_sequence, record in enumerate(records, start=1):
        _exact_keys(record, record_keys, "call_ledger_record_fields_invalid")
        if record.get("sequence") != expected_sequence:
            raise ValueError("call_ledger_sequence_invalid")
        state = str(record.get("attempt_state") or "")
        if state not in {"planned", "attempt_started", "completed", "attempt_outcome_unknown"}:
            raise ValueError("call_ledger_attempt_state_invalid")
        states[state] += 1
        if record.get("raw_content_included") is not False or record.get(
            "exception_text_included"
        ) is not False:
            raise ValueError("call_ledger_content_leak")
        ceiling = float(record.get("calculated_ceiling_cost_usd") or 0.0)
        accounted = float(record.get("accounted_cost_usd") or 0.0)
        if ceiling <= 0 or accounted < 0:
            raise ValueError("call_ledger_cost_invalid")
        accounted_cost += accounted
        if state == "planned":
            if record.get("reason_code") != "not_attempted" or accounted != 0:
                raise ValueError("planned_attempt_record_invalid")
        elif state == "attempt_started":
            if record.get("reason_code") != "attempt_started" or accounted != ceiling:
                raise ValueError("started_attempt_record_invalid")
        elif state == "attempt_outcome_unknown":
            if (
                record.get("status") != "unknown"
                or record.get("reason_code") != "provider_attempt_outcome_unknown"
                or accounted != ceiling
                or record.get("output_sha256")
            ):
                raise ValueError("unknown_attempt_record_invalid")
        else:
            status = str(record.get("status") or "")
            if status not in allowed_statuses:
                raise ValueError("completed_attempt_status_invalid")
            if record.get("reason_code") not in _COMPLETED_REASON_CODES:
                raise ValueError("completed_attempt_reason_code_invalid")
            statuses[status] += 1
            finish_reasons[str(record.get("finish_reason") or "unknown")] += 1
            models[str(record.get("observed_model") or "unknown")] += 1
            providers[str(record.get("observed_provider") or "unknown")] += 1
            observed_cost += float(record.get("cost_usd") or 0.0)
            valid_completed += int(status == "valid")
    attempted = 36 - states.get("planned", 0)
    completed = states.get("completed", 0)
    unknown = states.get("attempt_outcome_unknown", 0)
    if attempted > 36 or ledger.get("attempted_call_count") != attempted:
        raise ValueError("call_ledger_attempt_count_invalid")
    if ledger.get("completed_call_count") != completed:
        raise ValueError("call_ledger_completed_count_invalid")
    if ledger.get("unknown_outcome_count") != unknown:
        raise ValueError("call_ledger_unknown_count_invalid")
    if dict(states) != ledger.get("attempt_state_counts"):
        raise ValueError("call_ledger_attempt_state_counts_invalid")
    if dict(statuses) != ledger.get("status_counts"):
        raise ValueError("call_ledger_status_counts_invalid")
    if dict(finish_reasons) != ledger.get("finish_reason_counts"):
        raise ValueError("call_ledger_finish_reason_counts_invalid")
    if dict(models) != ledger.get("observed_model_counts"):
        raise ValueError("call_ledger_model_counts_invalid")
    if dict(providers) != ledger.get("observed_provider_counts"):
        raise ValueError("call_ledger_provider_counts_invalid")
    if round(observed_cost, 8) != ledger.get("observed_cost_usd"):
        raise ValueError("call_ledger_observed_cost_invalid")
    if round(accounted_cost, 8) != ledger.get("accounted_cost_usd"):
        raise ValueError("call_ledger_accounted_cost_invalid")
    if accounted_cost > float(ledger.get("absolute_cost_cap_usd") or 0.0):
        if ledger.get("terminal_reason_code") != "absolute_cost_cap_exceeded":
            raise ValueError("call_ledger_cost_cap_invalid")
    complete = completed == 36 and valid_completed == 36
    if ledger.get("outputs_complete") is not complete:
        raise ValueError("call_ledger_completeness_invalid")
    if require_complete and (
        not complete
        or ledger.get("campaign_status") != "human_rating_required"
        or terminal_reason is not None
    ):
        raise ValueError("call_ledger_not_ready_for_rating")
    return {
        "attempt_state_counts": dict(states),
        "status_counts": dict(statuses),
        "outputs_complete": complete,
    }


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
    if evidence_source not in {"synthetic_test", "main_model_provider"}:
        raise ValueError("evidence_source_invalid")
    if rating_source not in _RATING_SOURCES:
        raise ValueError("rating_source_invalid")
    expected_raters = {
        "synthetic_test": "offline_workflow_test",
        "tof_human_review": "tof",
        "codex_assisted_review_for_tof": "codex_for_tof",
    }
    if rater_id != expected_raters[rating_source]:
        raise ValueError("rating_source_invalid")
    if rating_source == "synthetic_test" and evidence_source != "synthetic_test":
        raise ValueError("rating_source_invalid")
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


def validate_ratification(
    ratification: Mapping[str, Any],
    *,
    packet_sha256: str,
    ratings_sha256: str,
) -> str:
    _exact_keys(
        ratification,
        {
            "schema_version",
            "packet_sha256",
            "ratings_sha256",
            "ratification_source",
            "ratifier_id",
            "decision",
            "ratification_created_outside_provider_runner",
        },
        "ratification_fields_invalid",
    )
    if ratification.get("schema_version") != RATIFICATION_SCHEMA_VERSION:
        raise ValueError("ratification_schema_invalid")
    if ratification.get("packet_sha256") != packet_sha256:
        raise ValueError("ratification_packet_fingerprint_invalid")
    if ratification.get("ratings_sha256") != ratings_sha256:
        raise ValueError("ratification_ratings_fingerprint_invalid")
    if (
        ratification.get("ratification_source") != "tof_human_ratification"
        or ratification.get("ratifier_id") != "tof"
        or ratification.get("ratification_created_outside_provider_runner") is not True
    ):
        raise ValueError("ratification_provenance_invalid")
    decision = str(ratification.get("decision") or "")
    if decision not in {"accept", "refuse"}:
        raise ValueError("ratification_decision_invalid")
    return decision


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
            "ratification_source",
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
    reason_codes = artifact.get("reason_codes")
    if (
        not isinstance(reason_codes, list)
        or not reason_codes
        or any(reason not in _DURABLE_REASON_CODES for reason in reason_codes)
    ):
        raise ValueError("durable_reason_codes_invalid")
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
    if artifact.get("rating_source") not in _RATING_SOURCES:
        raise ValueError("durable_rating_source_invalid")
    if artifact.get("evidence_source") == "synthetic_test":
        if (
            artifact.get("provider_results_observed") is not False
            or artifact.get("decision") != "provider_campaign_required"
        ):
            raise ValueError("synthetic_provider_verdict_forbidden")
    elif artifact.get("evidence_source") == "main_model_provider":
        if artifact.get("provider_results_observed") is not True or artifact.get(
            "decision"
        ) not in {"pass", "fail", "inconclusive"}:
            raise ValueError("provider_verdict_provenance_invalid")
    else:
        raise ValueError("durable_evidence_source_invalid")
    expected_ratification = (
        "tof_human_ratification"
        if artifact.get("rating_source") == "codex_assisted_review_for_tof"
        else None
    )
    if artifact.get("ratification_source") != expected_ratification:
        raise ValueError("durable_ratification_source_invalid")
    fingerprints = artifact.get("source_fingerprints")
    if not isinstance(fingerprints, Mapping) or set(fingerprints) != {
        "packet_sha256",
        "mapping_sha256",
        "ledger_sha256",
        "ratings_sha256",
        "ratification_sha256",
    }:
        raise ValueError("durable_source_fingerprints_invalid")
    for key in ("packet_sha256", "mapping_sha256", "ledger_sha256", "ratings_sha256"):
        if not _is_hex_digest(fingerprints.get(key), 64):
            raise ValueError("durable_source_fingerprints_invalid")
    if expected_ratification is None:
        if fingerprints.get("ratification_sha256") is not None:
            raise ValueError("durable_source_fingerprints_invalid")
    elif not _is_hex_digest(fingerprints.get("ratification_sha256"), 64):
        raise ValueError("durable_source_fingerprints_invalid")
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
    *,
    campaign_dir: Path,
    rating_packet_path: Path,
    ratings_path: Path,
    durable_output: Path,
    ratification_path: Path | None = None,
) -> dict[str, Any]:
    campaign_dir = campaign_dir.resolve()
    rating_packet_path = rating_packet_path.resolve()
    ratings_path = ratings_path.resolve()
    durable_output = durable_output.resolve()
    if campaign_dir == durable_output or campaign_dir in durable_output.parents:
        raise ValueError("durable_output_must_be_outside_temporary_campaign_directory")
    if campaign_dir in rating_packet_path.parents or campaign_dir in ratings_path.parents:
        raise ValueError("review_material_must_be_outside_private_campaign_directory")
    if rating_packet_path.parent != ratings_path.parent:
        raise ValueError("ratings_must_share_review_export_directory")
    review_dir = rating_packet_path.parent
    mapping_path = campaign_dir / "blind_mapping.json"
    ledger_path = campaign_dir / "call_ledger.json"
    private_outputs_path = campaign_dir / "private_outputs.json"
    for path in (
        rating_packet_path,
        mapping_path,
        ledger_path,
        private_outputs_path,
        ratings_path,
    ):
        if not path.is_file() or path.stat().st_mode & 0o077:
            raise ValueError("private_workflow_file_missing_or_permissions_invalid")
    if review_dir.stat().st_mode & 0o077 or campaign_dir.stat().st_mode & 0o077:
        raise ValueError("private_workflow_directory_permissions_invalid")
    if {path.name for path in review_dir.iterdir()} != {
        rating_packet_path.name,
        ratings_path.name,
    }:
        raise ValueError("review_export_contains_unexpected_files")
    packet = _load_json(rating_packet_path)
    ledger = _load_json(ledger_path)
    ratings = _load_json(ratings_path)
    packet_summary = validate_packet(packet)
    validate_ledger(ledger, require_complete=True)
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
    rating_source = str(ratings["rating_source"])
    ratings_sha = _sha256_file(ratings_path)
    ratification_source: str | None = None
    ratification_sha: str | None = None
    if rating_source == "codex_assisted_review_for_tof":
        if ratification_path is None:
            return {
                "status": "human_ratification_required",
                "decision": None,
                "reason_code": "codex_assisted_rating_requires_tof_ratification",
                "packet_sha256": packet_summary["packet_sha256"],
                "ratings_sha256": ratings_sha,
                "rating_source": rating_source,
            }
        resolved_ratification = ratification_path.resolve()
        if (
            not resolved_ratification.is_file()
            or resolved_ratification.stat().st_mode & 0o077
        ):
            raise ValueError("ratification_file_missing_or_permissions_invalid")
        ratification = _load_json(resolved_ratification)
        ratification_decision = validate_ratification(
            ratification,
            packet_sha256=packet_summary["packet_sha256"],
            ratings_sha256=ratings_sha,
        )
        if ratification_decision == "refuse":
            return {
                "status": "human_ratification_required",
                "decision": None,
                "reason_code": "tof_ratification_refused",
                "packet_sha256": packet_summary["packet_sha256"],
                "ratings_sha256": ratings_sha,
                "rating_source": rating_source,
            }
        ratification_source = "tof_human_ratification"
        ratification_sha = _sha256_file(resolved_ratification)
    elif ratification_path is not None:
        raise ValueError("ratification_only_allowed_for_codex_assisted_review")
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
        "rating_source": rating_source,
        "ratification_source": ratification_source,
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
            "ratings_sha256": ratings_sha,
            "ratification_sha256": ratification_sha,
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
    _atomic_write_private_json(durable_output, artifact)
    persisted = _load_json(durable_output)
    validate_durable_artifact(persisted)
    if persisted != artifact:
        durable_output.unlink(missing_ok=True)
        raise ValueError("durable_artifact_readback_mismatch")
    for path in (
        rating_packet_path,
        ratings_path,
        mapping_path,
        private_outputs_path,
        ledger_path,
    ):
        path.unlink()
    review_dir.rmdir()
    campaign_dir.rmdir()
    return artifact


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lot 4C.4 v2 offline human-rating finalizer")
    parser.add_argument("--campaign-dir", type=Path, required=True)
    parser.add_argument("--rating-packet", type=Path, required=True)
    parser.add_argument("--ratings", type=Path, required=True)
    parser.add_argument("--tof-ratification", type=Path)
    parser.add_argument("--durable-output", type=Path, required=True)
    args = parser.parse_args(argv)
    artifact = finalize_campaign(
        campaign_dir=args.campaign_dir,
        rating_packet_path=args.rating_packet,
        ratings_path=args.ratings,
        ratification_path=args.tof_ratification,
        durable_output=args.durable_output,
    )
    print(
        _compact_json(
            {
                "status": artifact.get("status", "finalized"),
                "decision": artifact.get("decision"),
                "call_count": artifact.get("call_count"),
                "rating_count": artifact.get("rating_count"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
