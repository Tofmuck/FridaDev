from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from benchmark.suites.stimmung import final_wording_execution_v2
from benchmark.suites.stimmung import final_wording_protocol_v2
from benchmark.suites.stimmung import final_wording_rating_v2


REPO_ROOT = Path(__file__).resolve().parents[4]


class _InjectedCrash(BaseException):
    pass


class _SyntheticClient:
    def __init__(self, *, failure: BaseException | None = None, cost_usd: float = 0.000225):
        self.calls: list[dict[str, object]] = []
        self.failure = failure
        self.cost_usd = cost_usd

    def chat_completion(
        self,
        payload: dict[str, object],
        *,
        caller: str,
        timeout_s: int,
    ) -> dict[str, object]:
        self.calls.append(copy.deepcopy(payload))
        if self.failure is not None and len(self.calls) == 3:
            raise self.failure
        sequence = len(self.calls)
        return {
            "ok": True,
            "status_code": 200,
            "raw_text": f"SYNTHETIC_TEST_RESPONSE_{sequence}",
            "finish_reason": "stop",
            "native_finish_reason": "stop",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 10,
                "total_tokens": 110,
            },
            "cost_estimate_usd": self.cost_usd,
            "model": "openai/gpt-5.1",
            "provider": "OpenAI",
        }


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_0600(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")
    os.chmod(path, 0o600)


def _synthetic_ratings(
    packet: dict[str, object],
    *,
    rating_source: str = "synthetic_test",
    rater_id: str = "offline_workflow_test",
) -> dict[str, object]:
    ratings: list[dict[str, object]] = []
    for item in packet["items"]:
        if item["comparison_kind"] == "causal_transition":
            ratings.append(
                {
                    "blind_id": item["blind_id"],
                    "delicacy_effect": "better_a",
                    "formulation_fit": "better_a",
                    "psychologization": "none",
                    "certainty_change": "none",
                    "truth_or_evidence_change": "none",
                    "masked_target": "none",
                }
            )
        else:
            ratings.append(
                {
                    "blind_id": item["blind_id"],
                    "formulation_fit": "adequate",
                    "artificial_caution": "absent",
                    "psychologization": "absent",
                    "certainty_change": "absent",
                    "truth_or_evidence_change": "absent",
                    "masked_target": "absent",
                }
            )
    return {
        "schema_version": final_wording_rating_v2.RATINGS_SCHEMA_VERSION,
        "packet_sha256": packet["packet_sha256"],
        "rating_source": rating_source,
        "rater_id": rater_id,
        "ratings_created_outside_runner": True,
        "ratings": ratings,
    }


class Lot4C4WorkflowV21Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = final_wording_protocol_v2.build_protocol(
            REPO_ROOT,
            freeze_commit="f" * 40,
        )

    def _run(
        self,
        parent: Path,
        client: _SyntheticClient,
        **kwargs: object,
    ) -> dict[str, object]:
        return final_wording_execution_v2.run_campaign(
            repo_root=REPO_ROOT,
            protocol=self.protocol,
            client=client,
            output_dir=parent / "campaign-private",
            review_export_dir=parent / "review-export",
            execution_authorized=True,
            evidence_source="synthetic_test",
            **kwargs,
        )

    def test_completed_attempts_are_checkpointed_and_never_recalled_after_resume(self) -> None:
        def crash(stage: str, sequence: int) -> None:
            if stage == "after_completed_checkpoint" and sequence == 3:
                raise _InjectedCrash("synthetic hard stop")

        with tempfile.TemporaryDirectory(dir="/tmp") as raw_parent:
            parent = Path(raw_parent)
            first = _SyntheticClient()
            with self.assertRaises(_InjectedCrash):
                self._run(parent, first, fault_injector=crash)

            ledger = _read_json(parent / "campaign-private/call_ledger.json")
            self.assertEqual([item["attempt_state"] for item in ledger["records"][:3]], [
                "completed",
                "completed",
                "completed",
            ])
            self.assertTrue((parent / "campaign-private/private_outputs.json").is_file())

            duplicate = _SyntheticClient()
            with self.assertRaisesRegex(ValueError, "temporary_output_directory_already_exists"):
                self._run(parent, duplicate)
            self.assertEqual(duplicate.calls, [])

            resumed = _SyntheticClient()
            result = self._run(parent, resumed, resume=True)
            self.assertEqual(result["status"], "human_rating_required")
            self.assertEqual(len(first.calls), 3)
            self.assertEqual(len(resumed.calls), 21)
            self.assertNotEqual(first.calls[0]["messages"], resumed.calls[0]["messages"])

    def test_attempt_started_becomes_costed_unknown_and_is_never_recalled(self) -> None:
        def crash(stage: str, sequence: int) -> None:
            if stage == "after_attempt_started_checkpoint" and sequence == 3:
                raise _InjectedCrash("ambiguous call boundary")

        with tempfile.TemporaryDirectory(dir="/tmp") as raw_parent:
            parent = Path(raw_parent)
            first = _SyntheticClient()
            with self.assertRaises(_InjectedCrash):
                self._run(parent, first, fault_injector=crash)
            self.assertEqual(len(first.calls), 2)

            resumed = _SyntheticClient()
            result = self._run(parent, resumed, resume=True)
            ledger = _read_json(parent / "campaign-private/call_ledger.json")
            third = ledger["records"][2]
            self.assertEqual(result["status"], "campaign_incomplete")
            self.assertEqual(result["reason_code"], "provider_attempt_outcome_unknown")
            self.assertEqual(third["attempt_state"], "attempt_outcome_unknown")
            self.assertEqual(
                third["accounted_cost_usd"],
                third["calculated_ceiling_cost_usd"],
            )
            self.assertEqual(ledger["attempted_call_count"], 3)
            self.assertEqual(resumed.calls, [])
            self.assertFalse((parent / "review-export").exists())

    def test_crash_before_attempt_mark_leaves_the_sequence_safe_to_run_once(self) -> None:
        def crash(stage: str, sequence: int) -> None:
            if stage == "before_attempt_started_checkpoint" and sequence == 3:
                raise _InjectedCrash("before durable mark")

        with tempfile.TemporaryDirectory(dir="/tmp") as raw_parent:
            parent = Path(raw_parent)
            first = _SyntheticClient()
            with self.assertRaises(_InjectedCrash):
                self._run(parent, first, fault_injector=crash)
            ledger = _read_json(parent / "campaign-private/call_ledger.json")
            self.assertEqual(ledger["records"][2]["attempt_state"], "planned")

            resumed = _SyntheticClient()
            result = self._run(parent, resumed, resume=True)
            self.assertEqual(result["status"], "human_rating_required")
            self.assertEqual(len(first.calls), 2)
            self.assertEqual(len(resumed.calls), 22)

    def test_returned_response_without_completed_checkpoint_is_unknown(self) -> None:
        def crash(stage: str, sequence: int) -> None:
            if stage == "after_private_output_checkpoint" and sequence == 3:
                raise _InjectedCrash("response returned but ledger not completed")

        with tempfile.TemporaryDirectory(dir="/tmp") as raw_parent:
            parent = Path(raw_parent)
            first = _SyntheticClient()
            with self.assertRaises(_InjectedCrash):
                self._run(parent, first, fault_injector=crash)
            self.assertEqual(len(first.calls), 3)
            ledger = _read_json(parent / "campaign-private/call_ledger.json")
            self.assertEqual(ledger["records"][2]["attempt_state"], "attempt_outcome_unknown")
            private = _read_json(parent / "campaign-private/private_outputs.json")
            self.assertNotIn("3", private["outputs"])

            resumed = _SyntheticClient()
            result = self._run(parent, resumed, resume=True)
            self.assertEqual(result["status"], "campaign_incomplete")
            self.assertEqual(resumed.calls, [])

    def test_python_exception_and_keyboard_interrupt_preserve_partial_evidence(self) -> None:
        for failure in (RuntimeError("controlled"), KeyboardInterrupt()):
            with self.subTest(failure=type(failure).__name__):
                with tempfile.TemporaryDirectory(dir="/tmp") as raw_parent:
                    parent = Path(raw_parent)
                    with self.assertRaises(type(failure)):
                        self._run(parent, _SyntheticClient(failure=failure))
                    ledger_path = parent / "campaign-private/call_ledger.json"
                    self.assertTrue(ledger_path.is_file())
                    ledger = _read_json(ledger_path)
                    self.assertEqual(
                        ledger["records"][2]["attempt_state"],
                        "attempt_outcome_unknown",
                    )
                    self.assertFalse((parent / "review-export").exists())

    def test_checkpoint_is_fsynced_before_call_and_atomic_replace_keeps_old_state(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as raw_parent:
            parent = Path(raw_parent)
            campaign_dir = parent / "campaign-private"
            observed_fsyncs: list[int] = []
            real_fsync = os.fsync

            class _InspectingClient(_SyntheticClient):
                def chat_completion(self, payload, *, caller, timeout_s):
                    ledger = _read_json(campaign_dir / "call_ledger.json")
                    self_test.assertEqual(ledger["records"][0]["attempt_state"], "attempt_started")
                    self_test.assertGreater(len(observed_fsyncs), 0)
                    raise RuntimeError("stop after durable inspection")

            self_test = self

            def recording_fsync(descriptor: int) -> None:
                observed_fsyncs.append(descriptor)
                real_fsync(descriptor)

            def reset_fsync_observation(stage: str, sequence: int) -> None:
                if stage == "before_attempt_started_checkpoint" and sequence == 1:
                    observed_fsyncs.clear()

            with mock.patch.object(
                final_wording_execution_v2.os,
                "fsync",
                side_effect=recording_fsync,
            ):
                with self.assertRaisesRegex(RuntimeError, "durable inspection"):
                    self._run(
                        parent,
                        _InspectingClient(),
                        fault_injector=reset_fsync_observation,
                    )

            checkpoint = campaign_dir / "atomic-test.json"
            final_wording_execution_v2._atomic_write_private_json(checkpoint, {"state": "old"})
            with mock.patch.object(
                final_wording_execution_v2.os,
                "replace",
                side_effect=OSError("replace interrupted"),
            ):
                with self.assertRaisesRegex(OSError, "replace interrupted"):
                    final_wording_execution_v2._atomic_write_private_json(
                        checkpoint,
                        {"state": "new"},
                    )
            self.assertEqual(_read_json(checkpoint), {"state": "old"})
            self.assertEqual(list(campaign_dir.glob(".atomic-test.json.*.tmp")), [])

    def test_resume_rejects_changed_freeze_forgotten_cost_and_attempt_37(self) -> None:
        expected_private, expected_review = final_wording_execution_v2.expected_live_campaign_paths(
            self.protocol
        )
        final_wording_execution_v2._validate_live_campaign_paths(
            self.protocol,
            expected_private,
            expected_review,
        )
        with self.assertRaisesRegex(
            ValueError,
            "live_campaign_paths_must_match_frozen_campaign_identity",
        ):
            final_wording_execution_v2._validate_live_campaign_paths(
                self.protocol,
                Path("/tmp/alternate-private"),
                Path("/tmp/alternate-review"),
            )

        def crash(stage: str, sequence: int) -> None:
            if stage == "after_completed_checkpoint" and sequence == 2:
                raise _InjectedCrash("retain two paid attempts")

        mutations = {
            "changed_freeze": lambda value: value.__setitem__("protocol_sha256", "0" * 64),
            "forgotten_cost": lambda value: value.__setitem__("accounted_cost_usd", 0.0),
            "attempt_37": lambda value: value.__setitem__("attempted_call_count", 37),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory(dir="/tmp") as raw_parent:
                    parent = Path(raw_parent)
                    with self.assertRaises(_InjectedCrash):
                        self._run(parent, _SyntheticClient(), fault_injector=crash)
                    ledger_path = parent / "campaign-private/call_ledger.json"
                    ledger = _read_json(ledger_path)
                    mutate(ledger)
                    final_wording_execution_v2._atomic_write_private_json(ledger_path, ledger)
                    resumed = _SyntheticClient()
                    with self.assertRaises(ValueError):
                        self._run(parent, resumed, resume=True)
                    self.assertEqual(resumed.calls, [])

    def test_resume_keeps_prior_cost_when_enforcing_the_absolute_cap(self) -> None:
        def crash(stage: str, sequence: int) -> None:
            if stage == "after_completed_checkpoint" and sequence == 3:
                raise _InjectedCrash("resume after three expensive completions")

        with tempfile.TemporaryDirectory(dir="/tmp") as raw_parent:
            parent = Path(raw_parent)
            first = _SyntheticClient(cost_usd=0.75)
            with self.assertRaises(_InjectedCrash):
                self._run(parent, first, fault_injector=crash)
            resumed = _SyntheticClient(cost_usd=0.75)
            result = self._run(parent, resumed, resume=True)
            ledger = _read_json(parent / "campaign-private/call_ledger.json")

            self.assertEqual(result["status"], "campaign_incomplete")
            self.assertEqual(result["reason_code"], "cost_cap_would_be_exceeded")
            self.assertEqual(len(first.calls), 3)
            self.assertEqual(len(resumed.calls), 1)
            self.assertEqual(ledger["attempted_call_count"], 4)
            self.assertEqual(ledger["accounted_cost_usd"], 3.0)

    def test_codex_assistance_requires_tof_ratification_before_unblinding(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as raw_parent:
            parent = Path(raw_parent)
            self._run(parent, _SyntheticClient())
            campaign_dir = parent / "campaign-private"
            packet_path = parent / "review-export/rating_packet.json"
            packet = _read_json(packet_path)
            ratings = _synthetic_ratings(
                packet,
                rating_source="codex_assisted_review_for_tof",
                rater_id="codex_for_tof",
            )
            ratings_path = parent / "review-export/ratings.json"
            _write_0600(ratings_path, ratings)
            mapping_path = campaign_dir / "blind_mapping.json"
            original_mapping = mapping_path.read_text(encoding="utf-8")
            mapping_path.write_text('{"must_not_be_read_before_ratification":true}')
            os.chmod(mapping_path, 0o600)

            pending = final_wording_rating_v2.finalize_campaign(
                campaign_dir=campaign_dir,
                rating_packet_path=packet_path,
                ratings_path=ratings_path,
                durable_output=parent / "durable.json",
            )
            self.assertEqual(pending["status"], "human_ratification_required")
            self.assertIsNone(pending["decision"])
            self.assertTrue(mapping_path.is_file())
            self.assertFalse((parent / "durable.json").exists())
            mapping_path.write_text(original_mapping, encoding="utf-8")
            os.chmod(mapping_path, 0o600)

            legacy = copy.deepcopy(ratings)
            legacy["rating_source"] = "delegated_human_review"
            with self.assertRaisesRegex(ValueError, "rating_source_invalid"):
                final_wording_rating_v2.validate_ratings(
                    legacy,
                    packet=packet,
                    evidence_source="synthetic_test",
                )
            false_human = copy.deepcopy(ratings)
            false_human["rating_source"] = "tof_human_review"
            with self.assertRaisesRegex(ValueError, "rating_source_invalid"):
                final_wording_rating_v2.validate_ratings(
                    false_human,
                    packet=packet,
                    evidence_source="synthetic_test",
                )
            tof_ratings = copy.deepcopy(false_human)
            tof_ratings["rater_id"] = "tof"
            self.assertEqual(
                len(
                    final_wording_rating_v2.validate_ratings(
                        tof_ratings,
                        packet=packet,
                        evidence_source="synthetic_test",
                    )
                ),
                12,
            )

            ratings_sha = hashlib.sha256(ratings_path.read_bytes()).hexdigest()
            ratification = {
                "schema_version": final_wording_rating_v2.RATIFICATION_SCHEMA_VERSION,
                "packet_sha256": packet["packet_sha256"],
                "ratings_sha256": ratings_sha,
                "ratification_source": "tof_human_ratification",
                "ratifier_id": "tof",
                "decision": "accept",
                "ratification_created_outside_provider_runner": True,
            }
            ratification_path = parent / "tof-ratification.json"
            refused = copy.deepcopy(ratification)
            refused["decision"] = "refuse"
            _write_0600(ratification_path, refused)
            refused_result = final_wording_rating_v2.finalize_campaign(
                campaign_dir=campaign_dir,
                rating_packet_path=packet_path,
                ratings_path=ratings_path,
                ratification_path=ratification_path,
                durable_output=parent / "durable.json",
            )
            self.assertEqual(refused_result["status"], "human_ratification_required")
            self.assertEqual(refused_result["reason_code"], "tof_ratification_refused")
            self.assertTrue((campaign_dir / "blind_mapping.json").is_file())

            wrong = copy.deepcopy(ratification)
            wrong["ratings_sha256"] = "0" * 64
            _write_0600(ratification_path, wrong)
            with self.assertRaisesRegex(ValueError, "ratification_ratings_fingerprint_invalid"):
                final_wording_rating_v2.finalize_campaign(
                    campaign_dir=campaign_dir,
                    rating_packet_path=packet_path,
                    ratings_path=ratings_path,
                    ratification_path=ratification_path,
                    durable_output=parent / "durable.json",
                )
            self.assertTrue((campaign_dir / "blind_mapping.json").is_file())

            _write_0600(ratification_path, ratification)
            artifact = final_wording_rating_v2.finalize_campaign(
                campaign_dir=campaign_dir,
                rating_packet_path=packet_path,
                ratings_path=ratings_path,
                ratification_path=ratification_path,
                durable_output=parent / "durable.json",
            )
            self.assertEqual(artifact["decision"], "provider_campaign_required")
            self.assertEqual(artifact["rating_source"], "codex_assisted_review_for_tof")
            self.assertEqual(artifact["ratification_source"], "tof_human_ratification")

    def test_review_export_contains_only_blind_packet_and_no_mapping_metadata(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as raw_parent:
            parent = Path(raw_parent)
            result = self._run(parent, _SyntheticClient())
            review_dir = parent / "review-export"
            private_dir = parent / "campaign-private"
            self.assertEqual(result["status"], "human_rating_required")
            self.assertEqual([path.name for path in review_dir.iterdir()], ["rating_packet.json"])
            self.assertFalse((private_dir / "rating_packet.json").exists())
            self.assertTrue((private_dir / "blind_mapping.json").is_file())
            packet_text = (review_dir / "rating_packet.json").read_text(encoding="utf-8")
            for forbidden in ('"variant"', '"control"', '"treatment"', '"directive"'):
                self.assertNotIn(forbidden, packet_text)
            with self.assertRaisesRegex(
                ValueError,
                "review_export_must_be_separate_from_private_campaign",
            ):
                final_wording_execution_v2._validate_review_export_dir(
                    REPO_ROOT,
                    private_dir,
                    private_dir / "review",
                )


if __name__ == "__main__":
    unittest.main()
