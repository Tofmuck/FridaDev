from __future__ import annotations

import copy
from contextlib import nullcontext
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from benchmark.suites.stimmung import final_wording_execution_v2 as execution_v2
from benchmark.suites.stimmung import final_wording_finalization_v2 as finalization_v2
from benchmark.suites.stimmung import final_wording_gpt52_v25 as campaign_v25
from benchmark.suites.stimmung import final_wording_gpt52_v25_finalize as finalize_v25
from benchmark.suites.stimmung import final_wording_protocol_v2 as protocol_v2
from benchmark.suites.stimmung import final_wording_rating_v2 as rating_v2


REPO_ROOT = Path(__file__).resolve().parents[4]
FREEZE_COMMIT = "f" * 40


def _rating_material() -> tuple[dict[str, object], dict[str, object]]:
    schedule = protocol_v2._build_request_schedule(REPO_ROOT)
    executions = [
        (
            plan,
            {
                "status": "valid",
                "raw_text": f"SYNTHETIC_OUTPUT_{plan['sequence']}",
            },
        )
        for plan in schedule
    ]
    return execution_v2._build_rating_material(
        corpus=protocol_v2.load_corpus(REPO_ROOT),
        protocol_sha="a" * 64,
        evidence_source="synthetic_test",
        executions=executions,
    )


def _better_a_ratings(packet: dict[str, object]) -> dict[str, dict[str, object]]:
    items = packet["items"]
    assert isinstance(items, list)
    return {
        str(item["blind_id"]): {
            "blind_id": item["blind_id"],
            "delicacy_effect": "better_a",
            "formulation_fit": "better_a",
            "psychologization": "none",
            "certainty_change": "none",
            "truth_or_evidence_change": "none",
            "masked_target": "none",
        }
        for item in items
    }


def _write_0600(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")
    os.chmod(path, 0o600)


def _ratings_document(
    packet: dict[str, object],
    *,
    rating_source: str = "synthetic_test",
) -> dict[str, object]:
    ratings_by_id = _better_a_ratings(packet)
    rater_id = {
        "synthetic_test": "offline_workflow_test",
        "codex_assisted_review_for_tof": "codex_for_tof",
    }[rating_source]
    return {
        "schema_version": rating_v2.RATINGS_SCHEMA_VERSION,
        "packet_sha256": packet["packet_sha256"],
        "rating_source": rating_source,
        "rater_id": rater_id,
        "ratings_created_outside_runner": True,
        "ratings": list(ratings_by_id.values()),
    }


@lru_cache(maxsize=2)
def _cached_historical_protocol_and_schedule(
    *,
    v25: bool,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    context = campaign_v25._campaign_profile() if v25 else None
    if context is not None:
        context.__enter__()
    try:
        protocol = protocol_v2._build_unfrozen_protocol(
            REPO_ROOT,
            freeze_commit=FREEZE_COMMIT,
        )
        manifest = json.loads(
            protocol_v2.freeze_manifest_path(REPO_ROOT).read_text(encoding="utf-8")
        )
        protocol["input_fingerprints"] = copy.deepcopy(manifest["frozen_inputs"])
        schedule = protocol_v2._build_request_schedule(REPO_ROOT)
        return protocol, schedule
    finally:
        if context is not None:
            context.__exit__(None, None, None)


def _historical_protocol_and_schedule(
    *,
    v25: bool,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    protocol, schedule = _cached_historical_protocol_and_schedule(v25=v25)
    return copy.deepcopy(protocol), copy.deepcopy(schedule)


def _complete_outcome(sequence: int, *, v25: bool) -> dict[str, object]:
    model = campaign_v25.TARGET_MODEL if v25 else protocol_v2.ACTIVE_MAIN_MODEL
    raw_text = f"SYNTHETIC_OUTPUT_{sequence}"
    return {
        "status": "valid",
        "reason_code": "valid_complete_output",
        "status_code": 200,
        "finish_reason": "stop",
        "native_finish_reason": "stop",
        "requested_model": model,
        "observed_model": model,
        "observed_provider": "openai",
        "prompt_tokens": 100,
        "completion_tokens": 10,
        "total_tokens": 110,
        "cost_usd": 0.0001,
        "raw_text": raw_text,
    }


def _create_complete_workflow(
    root: Path,
    *,
    v25: bool = False,
    rating_source: str = "synthetic_test",
) -> dict[str, object]:
    private_dir = root / "private"
    review_dir = root / "review"
    private_dir.mkdir(mode=0o700)
    review_dir.mkdir(mode=0o700)
    protocol, schedule = _historical_protocol_and_schedule(v25=v25)
    protocol_sha = protocol_v2.protocol_sha256(protocol)
    outcomes = {
        int(plan["sequence"]): _complete_outcome(int(plan["sequence"]), v25=v25)
        for plan in schedule
    }

    context = campaign_v25._campaign_profile() if v25 else None
    if context is not None:
        context.__enter__()
    try:
        ledger = execution_v2._new_ledger(
            protocol,
            schedule,
            evidence_source="synthetic_test",
        )
        for plan in schedule:
            sequence = int(plan["sequence"])
            ledger["records"][sequence - 1] = execution_v2._call_ledger_record(
                plan,
                outcomes[sequence],
                accounted_cost=0.0001,
            )
        execution_v2._refresh_ledger(ledger)
        ledger["campaign_status"] = "human_rating_required"
        ledger["terminal_reason_code"] = None
        packet, mapping = execution_v2._build_rating_material(
            corpus=protocol_v2.load_corpus(REPO_ROOT),
            protocol_sha=protocol_sha,
            evidence_source="synthetic_test",
            executions=[(plan, outcomes[int(plan["sequence"])]) for plan in schedule],
        )
        private_outputs = execution_v2._new_private_outputs(
            protocol_sha,
            "synthetic_test",
        )
        private_outputs["outputs"] = {
            str(sequence): outcome for sequence, outcome in outcomes.items()
        }
    finally:
        if context is not None:
            context.__exit__(None, None, None)

    packet_path = review_dir / "rating_packet.json"
    ratings_path = review_dir / "ratings.json"
    mapping_path = private_dir / "blind_mapping.json"
    ledger_path = private_dir / "call_ledger.json"
    outputs_path = private_dir / "private_outputs.json"
    _write_0600(packet_path, packet)
    _write_0600(ratings_path, _ratings_document(packet, rating_source=rating_source))
    _write_0600(mapping_path, mapping)
    _write_0600(ledger_path, ledger)
    _write_0600(outputs_path, private_outputs)
    return {
        "protocol": protocol,
        "schedule": schedule,
        "packet": packet,
        "private_dir": private_dir,
        "review_dir": review_dir,
        "packet_path": packet_path,
        "ratings_path": ratings_path,
        "mapping_path": mapping_path,
        "ledger_path": ledger_path,
        "outputs_path": outputs_path,
        "durable_path": root / "durable.json",
    }


def _protected_snapshot(workflow: dict[str, object]) -> dict[Path, bytes]:
    paths = [
        workflow["packet_path"],
        workflow["ratings_path"],
        workflow["mapping_path"],
        workflow["ledger_path"],
        workflow["outputs_path"],
    ]
    return {path: path.read_bytes() for path in paths if isinstance(path, Path)}


def _assert_rejected_without_mutation(
    test: unittest.TestCase,
    workflow: dict[str, object],
    *,
    reason: str,
) -> None:
    before = _protected_snapshot(workflow)
    with test.assertRaisesRegex(ValueError, reason), mock.patch.object(
        rating_v2,
        "_score_validated_ratings",
        side_effect=AssertionError("scorer_must_stay_unreachable"),
    ):
        finalization_v2.finalize_campaign(
            repo_root=REPO_ROOT,
            freeze_commit=FREEZE_COMMIT,
            campaign_dir=workflow["private_dir"],
            rating_packet_path=workflow["packet_path"],
            ratings_path=workflow["ratings_path"],
            durable_output=workflow["durable_path"],
        )
    test.assertFalse(workflow["durable_path"].exists())
    test.assertEqual(_protected_snapshot(workflow), before)
    test.assertTrue(workflow["private_dir"].is_dir())
    test.assertTrue(workflow["review_dir"].is_dir())


class L76HistoricalAttributionReproductionTests(unittest.TestCase):
    def test_old_mapping_validation_accepts_variant_swap_and_changes_attribution(self) -> None:
        packet, mapping = _rating_material()
        original = rating_v2.validate_mapping(mapping, packet)
        ratings = _better_a_ratings(packet)
        original_metrics = rating_v2._score_validated_ratings(ratings, original)

        swapped_mapping = copy.deepcopy(mapping)
        first = swapped_mapping["items"][0]
        first["slots"]["A"]["variant"], first["slots"]["B"]["variant"] = (
            first["slots"]["B"]["variant"],
            first["slots"]["A"]["variant"],
        )
        swapped = rating_v2.validate_mapping(swapped_mapping, packet)
        swapped_metrics = rating_v2._score_validated_ratings(ratings, swapped)

        self.assertEqual(
            [slot["output_sha256"] for slot in mapping["items"][0]["slots"].values()],
            [
                slot["output_sha256"]
                for slot in swapped_mapping["items"][0]["slots"].values()
            ],
        )
        self.assertNotEqual(
            original_metrics["transition_delicacy_improved_count"],
            swapped_metrics["transition_delicacy_improved_count"],
        )
        self.assertNotEqual(
            original_metrics["transition_formulation_improved_count"],
            swapped_metrics["transition_formulation_improved_count"],
        )


class L76HistoricalAttributionGuardTests(unittest.TestCase):
    def test_legacy_public_finalizer_cannot_bypass_attribution_guard(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            workflow = _create_complete_workflow(Path(raw))
            mapping = json.loads(workflow["mapping_path"].read_text(encoding="utf-8"))
            first = mapping["items"][0]
            first["slots"]["A"]["variant"], first["slots"]["B"]["variant"] = (
                first["slots"]["B"]["variant"],
                first["slots"]["A"]["variant"],
            )
            _write_0600(workflow["mapping_path"], mapping)
            before = _protected_snapshot(workflow)

            with self.assertRaisesRegex(
                ValueError,
                "historical_attribution_guard_required",
            ):
                rating_v2.finalize_campaign(
                    campaign_dir=workflow["private_dir"],
                    rating_packet_path=workflow["packet_path"],
                    ratings_path=workflow["ratings_path"],
                    durable_output=workflow["durable_path"],
                )
            self.assertEqual(_protected_snapshot(workflow), before)
            self.assertFalse(workflow["durable_path"].exists())

    def test_internal_scorer_and_purge_require_the_guard_capability(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            workflow = _create_complete_workflow(Path(raw))
            before = _protected_snapshot(workflow)

            with self.assertRaisesRegex(
                ValueError,
                "historical_attribution_guard_required",
            ):
                rating_v2._finalize_after_attribution_guard(
                    campaign_dir=workflow["private_dir"],
                    rating_packet_path=workflow["packet_path"],
                    ratings_path=workflow["ratings_path"],
                    durable_output=workflow["durable_path"],
                )
            self.assertEqual(_protected_snapshot(workflow), before)
            self.assertFalse(workflow["durable_path"].exists())

    def test_variant_swap_is_rejected_before_scorer_or_purge(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            workflow = _create_complete_workflow(Path(raw))
            mapping = json.loads(workflow["mapping_path"].read_text(encoding="utf-8"))
            first = mapping["items"][0]
            first["slots"]["A"]["variant"], first["slots"]["B"]["variant"] = (
                first["slots"]["B"]["variant"],
                first["slots"]["A"]["variant"],
            )
            _write_0600(workflow["mapping_path"], mapping)

            _assert_rejected_without_mutation(
                self,
                workflow,
                reason="attribution_mapping_calendar_mismatch",
            )

    def test_mapping_change_after_guard_is_rejected_before_scorer_or_purge(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            workflow = _create_complete_workflow(Path(raw))
            finalize_after_guard = rating_v2._finalize_after_attribution_guard
            expected_paths = set(_protected_snapshot(workflow))

            def mutate_then_finalize(**kwargs: object) -> dict[str, object]:
                mapping = json.loads(
                    workflow["mapping_path"].read_text(encoding="utf-8")
                )
                first = mapping["items"][0]
                first["slots"]["A"]["variant"], first["slots"]["B"]["variant"] = (
                    first["slots"]["B"]["variant"],
                    first["slots"]["A"]["variant"],
                )
                _write_0600(workflow["mapping_path"], mapping)
                return finalize_after_guard(**kwargs)

            with mock.patch.object(
                rating_v2,
                "_finalize_after_attribution_guard",
                side_effect=mutate_then_finalize,
            ), mock.patch.object(
                rating_v2,
                "_score_validated_ratings",
                side_effect=AssertionError("scorer_must_stay_unreachable"),
            ), self.assertRaisesRegex(
                ValueError,
                "historical_attribution_sources_changed",
            ):
                finalization_v2.finalize_campaign(
                    repo_root=REPO_ROOT,
                    freeze_commit=FREEZE_COMMIT,
                    campaign_dir=workflow["private_dir"],
                    rating_packet_path=workflow["packet_path"],
                    ratings_path=workflow["ratings_path"],
                    durable_output=workflow["durable_path"],
            )

            self.assertFalse(workflow["durable_path"].exists())
            self.assertEqual(set(_protected_snapshot(workflow)), expected_paths)

    def test_durable_output_inside_source_or_staging_directory_is_rejected(self) -> None:
        for location in ("review", "private_staged", "review_staged"):
            with self.subTest(location=location), tempfile.TemporaryDirectory(
                dir="/tmp"
            ) as raw:
                workflow = _create_complete_workflow(Path(raw))
                destinations = {
                    "review": workflow["review_dir"] / "durable.json",
                    "private_staged": workflow["private_dir"].with_name(
                        ".private.finalization-purge"
                    )
                    / "call_ledger.json",
                    "review_staged": workflow["review_dir"].with_name(
                        ".review.finalization-purge"
                    )
                    / "rating_packet.json",
                }
                before = _protected_snapshot(workflow)

                with self.assertRaisesRegex(
                    ValueError,
                    "durable_output_must_be_outside_temporary_campaign_directory",
                ):
                    finalization_v2.finalize_campaign(
                        repo_root=REPO_ROOT,
                        freeze_commit=FREEZE_COMMIT,
                        campaign_dir=workflow["private_dir"],
                        rating_packet_path=workflow["packet_path"],
                        ratings_path=workflow["ratings_path"],
                        durable_output=destinations[location],
                    )

                self.assertEqual(_protected_snapshot(workflow), before)

    def test_precommit_staging_and_write_failures_restore_all_sources(self) -> None:
        for failure in (
            "preexisting_durable",
            "second_directory_rename",
            "durable_write",
        ):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory(
                dir="/tmp"
            ) as raw:
                workflow = _create_complete_workflow(Path(raw))
                before = _protected_snapshot(workflow)
                if failure == "preexisting_durable":
                    workflow["durable_path"].write_bytes(b"PREEXISTING")
                    os.chmod(workflow["durable_path"], 0o600)
                    patcher = nullcontext()
                    reason = "durable_output_already_exists"
                elif failure == "second_directory_rename":
                    original_replace = Path.replace

                    def fail_review_rename(source: Path, target: Path) -> Path:
                        if source == workflow["review_dir"]:
                            raise OSError("synthetic rename failure")
                        return original_replace(source, target)

                    patcher = mock.patch.object(
                        Path,
                        "replace",
                        autospec=True,
                        side_effect=fail_review_rename,
                    )
                    reason = "finalization_staging_failed"
                else:
                    patcher = mock.patch.object(
                        rating_v2,
                        "_atomic_write_private_json",
                        side_effect=OSError("synthetic durable write failure"),
                    )
                    reason = "finalization_commit_failed"

                with patcher, self.assertRaisesRegex(
                    ValueError,
                    reason,
                ):
                    finalization_v2.finalize_campaign(
                        repo_root=REPO_ROOT,
                        freeze_commit=FREEZE_COMMIT,
                        campaign_dir=workflow["private_dir"],
                        rating_packet_path=workflow["packet_path"],
                        ratings_path=workflow["ratings_path"],
                        durable_output=workflow["durable_path"],
                    )

                self.assertEqual(_protected_snapshot(workflow), before)
                if failure == "preexisting_durable":
                    self.assertEqual(workflow["durable_path"].read_bytes(), b"PREEXISTING")
                else:
                    self.assertFalse(workflow["durable_path"].exists())
                self.assertTrue(workflow["private_dir"].is_dir())
                self.assertTrue(workflow["review_dir"].is_dir())

    def test_postcommit_cleanup_failure_keeps_a_valid_durable_result(self) -> None:
        for operation in ("unlink", "rmdir"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory(
                dir="/tmp"
            ) as raw:
                workflow = _create_complete_workflow(Path(raw))
                target = getattr(Path, operation)
                injected = False

                def fail_once(path: Path, *args: object, **kwargs: object) -> object:
                    nonlocal injected
                    if "finalization-purge" in str(path) and not injected:
                        injected = True
                        raise OSError(f"synthetic {operation} failure")
                    return target(path, *args, **kwargs)

                with mock.patch.object(
                    Path,
                    operation,
                    autospec=True,
                    side_effect=fail_once,
                ):
                    artifact = finalization_v2.finalize_campaign(
                        repo_root=REPO_ROOT,
                        freeze_commit=FREEZE_COMMIT,
                        campaign_dir=workflow["private_dir"],
                        rating_packet_path=workflow["packet_path"],
                        ratings_path=workflow["ratings_path"],
                        durable_output=workflow["durable_path"],
                    )

                self.assertTrue(injected)
                self.assertTrue(workflow["durable_path"].is_file())
                self.assertTrue(rating_v2.validate_durable_artifact(artifact))
                self.assertFalse(workflow["private_dir"].exists())
                self.assertFalse(workflow["review_dir"].exists())

    def test_sequence_case_repetition_and_slot_mismatches_are_rejected(self) -> None:
        def swap_sequences(workflow: dict[str, object]) -> None:
            mapping = json.loads(workflow["mapping_path"].read_text(encoding="utf-8"))
            slots = mapping["items"][0]["slots"]
            slots["A"]["sequence"], slots["B"]["sequence"] = (
                slots["B"]["sequence"],
                slots["A"]["sequence"],
            )
            _write_0600(workflow["mapping_path"], mapping)

        def change_case(workflow: dict[str, object]) -> None:
            mapping = json.loads(workflow["mapping_path"].read_text(encoding="utf-8"))
            mapping["items"][0]["case_id"] = "L4C4-FW2-foreign"
            _write_0600(workflow["mapping_path"], mapping)

        def change_repetition(workflow: dict[str, object]) -> None:
            mapping = json.loads(workflow["mapping_path"].read_text(encoding="utf-8"))
            mapping["items"][0]["repetition"] = 3
            _write_0600(workflow["mapping_path"], mapping)

        def change_repetition_type(workflow: dict[str, object]) -> None:
            mapping = json.loads(workflow["mapping_path"].read_text(encoding="utf-8"))
            mapping["items"][0]["repetition"] = True
            _write_0600(workflow["mapping_path"], mapping)

        def change_slot(workflow: dict[str, object]) -> None:
            ledger = json.loads(workflow["ledger_path"].read_text(encoding="utf-8"))
            ledger["records"][0]["blind_slot"] = "B"
            _write_0600(workflow["ledger_path"], ledger)

        def change_comparison_kind(workflow: dict[str, object]) -> None:
            mapping = json.loads(workflow["mapping_path"].read_text(encoding="utf-8"))
            mapping["items"][0]["comparison_kind"] = "foreign_comparison"
            _write_0600(workflow["mapping_path"], mapping)

        def change_messages_fingerprint(workflow: dict[str, object]) -> None:
            ledger = json.loads(workflow["ledger_path"].read_text(encoding="utf-8"))
            ledger["records"][0]["messages_sha256"] = "0" * 64
            _write_0600(workflow["ledger_path"], ledger)

        for name, mutate, reason in (
            ("sequence", swap_sequences, "attribution_mapping_calendar_mismatch"),
            ("case", change_case, "attribution_mapping_calendar_mismatch"),
            ("repetition", change_repetition, "attribution_mapping_calendar_mismatch"),
            (
                "repetition_type",
                change_repetition_type,
                "attribution_mapping_calendar_mismatch",
            ),
            ("slot", change_slot, "attribution_calendar_ledger_mismatch"),
            (
                "comparison_kind",
                change_comparison_kind,
                "attribution_mapping_calendar_mismatch",
            ),
            (
                "messages_sha256",
                change_messages_fingerprint,
                "attribution_calendar_ledger_mismatch",
            ),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory(dir="/tmp") as raw:
                workflow = _create_complete_workflow(Path(raw))
                mutate(workflow)
                _assert_rejected_without_mutation(self, workflow, reason=reason)

    def test_mapping_output_must_equal_ledger_output(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            workflow = _create_complete_workflow(Path(raw))
            ledger = json.loads(workflow["ledger_path"].read_text(encoding="utf-8"))
            ledger["records"][0]["output_sha256"] = hashlib.sha256(
                b"different synthetic output"
            ).hexdigest()
            _write_0600(workflow["ledger_path"], ledger)

            _assert_rejected_without_mutation(
                self,
                workflow,
                reason="attribution_mapping_ledger_output_mismatch",
            )

    def test_duplicate_missing_and_foreign_sequences_are_rejected(self) -> None:
        def duplicate(workflow: dict[str, object]) -> None:
            mapping = json.loads(workflow["mapping_path"].read_text(encoding="utf-8"))
            mapping["items"][0]["slots"]["B"]["sequence"] = mapping["items"][0][
                "slots"
            ]["A"]["sequence"]
            _write_0600(workflow["mapping_path"], mapping)

        def foreign(workflow: dict[str, object]) -> None:
            mapping = json.loads(workflow["mapping_path"].read_text(encoding="utf-8"))
            mapping["items"][0]["slots"]["A"]["sequence"] = 25
            _write_0600(workflow["mapping_path"], mapping)

        for name, mutate in (("duplicate_and_missing", duplicate), ("foreign", foreign)):
            with self.subTest(name=name), tempfile.TemporaryDirectory(dir="/tmp") as raw:
                workflow = _create_complete_workflow(Path(raw))
                mutate(workflow)
                _assert_rejected_without_mutation(
                    self,
                    workflow,
                    reason="attribution_sequence_bijection_invalid",
                )

    def test_calendar_fingerprint_and_workflow_provenance_are_rejected(self) -> None:
        original_builder = protocol_v2._build_request_schedule

        def changed_calendar(repo_root: Path) -> list[dict[str, object]]:
            schedule = original_builder(repo_root)
            schedule[0]["messages_sha256"] = "0" * 64
            return schedule

        with mock.patch.object(
            protocol_v2,
            "_build_request_schedule",
            side_effect=changed_calendar,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "historical_calendar_provenance_invalid",
            ):
                finalization_v2.load_historical_protocol(
                    REPO_ROOT,
                    freeze_commit=FREEZE_COMMIT,
                )

        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            workflow = _create_complete_workflow(Path(raw))
            ledger = json.loads(workflow["ledger_path"].read_text(encoding="utf-8"))
            ledger["schedule_sha256"] = "0" * 64
            _write_0600(workflow["ledger_path"], ledger)
            _assert_rejected_without_mutation(
                self,
                workflow,
                reason="historical_workflow_provenance_invalid",
            )

    def test_incomplete_ratings_and_missing_ratification_do_not_read_mapping(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            workflow = _create_complete_workflow(Path(raw))
            ratings = json.loads(workflow["ratings_path"].read_text(encoding="utf-8"))
            ratings["ratings"].pop()
            _write_0600(workflow["ratings_path"], ratings)
            workflow["mapping_path"].write_text("mapping must stay unread", encoding="utf-8")
            os.chmod(workflow["mapping_path"], 0o600)
            before = _protected_snapshot(workflow)

            with mock.patch.object(
                finalization_v2,
                "load_historical_protocol",
                side_effect=AssertionError("calendar_must_stay_unreachable"),
            ), self.assertRaisesRegex(ValueError, "ratings_incomplete"):
                finalization_v2.finalize_campaign(
                    repo_root=REPO_ROOT,
                    freeze_commit=FREEZE_COMMIT,
                    campaign_dir=workflow["private_dir"],
                    rating_packet_path=workflow["packet_path"],
                    ratings_path=workflow["ratings_path"],
                    durable_output=workflow["durable_path"],
                )
            self.assertEqual(_protected_snapshot(workflow), before)
            self.assertFalse(workflow["durable_path"].exists())

        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            workflow = _create_complete_workflow(
                Path(raw),
                rating_source="codex_assisted_review_for_tof",
            )
            workflow["mapping_path"].write_text("mapping must stay unread", encoding="utf-8")
            os.chmod(workflow["mapping_path"], 0o600)
            before = _protected_snapshot(workflow)

            with mock.patch.object(
                finalization_v2,
                "load_historical_protocol",
                side_effect=AssertionError("calendar_must_stay_unreachable"),
            ):
                pending = finalization_v2.finalize_campaign(
                    repo_root=REPO_ROOT,
                    freeze_commit=FREEZE_COMMIT,
                    campaign_dir=workflow["private_dir"],
                    rating_packet_path=workflow["packet_path"],
                    ratings_path=workflow["ratings_path"],
                    durable_output=workflow["durable_path"],
                )
            self.assertEqual(pending["status"], "human_ratification_required")
            self.assertEqual(_protected_snapshot(workflow), before)
            self.assertFalse(workflow["durable_path"].exists())

    def test_v24_nominal_finalization_scores_then_purges(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            workflow = _create_complete_workflow(Path(raw))
            artifact = rating_v2.finalize_campaign(
                repo_root=REPO_ROOT,
                freeze_commit=FREEZE_COMMIT,
                campaign_dir=workflow["private_dir"],
                rating_packet_path=workflow["packet_path"],
                ratings_path=workflow["ratings_path"],
                durable_output=workflow["durable_path"],
            )

            self.assertEqual(artifact["decision"], "provider_campaign_required")
            self.assertTrue(workflow["durable_path"].is_file())
            self.assertFalse(workflow["private_dir"].exists())
            self.assertFalse(workflow["review_dir"].exists())

    def test_v25_nominal_finalizer_reuses_the_shared_guard(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            workflow = _create_complete_workflow(
                root,
                v25=True,
                rating_source="codex_assisted_review_for_tof",
            )
            ratings_sha = hashlib.sha256(workflow["ratings_path"].read_bytes()).hexdigest()
            ratification_path = root / "ratification.json"
            _write_0600(
                ratification_path,
                {
                    "schema_version": rating_v2.RATIFICATION_SCHEMA_VERSION,
                    "packet_sha256": workflow["packet"]["packet_sha256"],
                    "ratings_sha256": ratings_sha,
                    "ratification_source": "tof_human_ratification",
                    "ratifier_id": "tof",
                    "decision": "accept",
                    "ratification_created_outside_provider_runner": True,
                },
            )
            with mock.patch.object(
                campaign_v25,
                "expected_live_campaign_paths",
                return_value=(workflow["private_dir"], workflow["review_dir"]),
            ), mock.patch.object(
                finalization_v2,
                "validate_attribution_bijection",
                wraps=finalization_v2.validate_attribution_bijection,
            ) as guard:
                artifact = finalize_v25.finalize_campaign(
                    repo_root=REPO_ROOT,
                    freeze_commit=FREEZE_COMMIT,
                    campaign_dir=workflow["private_dir"],
                    rating_packet_path=workflow["packet_path"],
                    ratings_path=workflow["ratings_path"],
                    ratification_path=ratification_path,
                    durable_output=workflow["durable_path"],
                )

            self.assertEqual(guard.call_count, 1)
            self.assertEqual(artifact["decision"], "provider_campaign_required")
            self.assertEqual(artifact["route_counts"]["models"], {"openai/gpt-5.2": 24})
            self.assertEqual(artifact["ratification_source"], "tof_human_ratification")
            self.assertTrue(workflow["durable_path"].is_file())
            self.assertFalse(workflow["private_dir"].exists())
            self.assertFalse(workflow["review_dir"].exists())

    def test_v25_rejects_the_same_variant_swap_without_purge(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            workflow = _create_complete_workflow(Path(raw), v25=True)
            mapping = json.loads(workflow["mapping_path"].read_text(encoding="utf-8"))
            first = mapping["items"][0]
            first["slots"]["A"]["variant"], first["slots"]["B"]["variant"] = (
                first["slots"]["B"]["variant"],
                first["slots"]["A"]["variant"],
            )
            _write_0600(workflow["mapping_path"], mapping)
            before = _protected_snapshot(workflow)

            with mock.patch.object(
                campaign_v25,
                "expected_live_campaign_paths",
                return_value=(workflow["private_dir"], workflow["review_dir"]),
            ), self.assertRaisesRegex(
                ValueError,
                "attribution_mapping_calendar_mismatch",
            ):
                finalize_v25.finalize_campaign(
                    repo_root=REPO_ROOT,
                    freeze_commit=FREEZE_COMMIT,
                    campaign_dir=workflow["private_dir"],
                    rating_packet_path=workflow["packet_path"],
                    ratings_path=workflow["ratings_path"],
                    durable_output=workflow["durable_path"],
                )

            self.assertEqual(_protected_snapshot(workflow), before)
            self.assertFalse(workflow["durable_path"].exists())


if __name__ == "__main__":
    unittest.main()
