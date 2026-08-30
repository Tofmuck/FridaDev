from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "benchmark").exists() and (parent / "app").exists():
            return parent
    raise RuntimeError("Unable to resolve repo root")


REPO_ROOT = _repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.suites.stimmung import dialogic_campaign


class _WitnessClient:
    def __init__(
        self,
        witness_by_dialogue: dict[str, list[dict]],
        schedule: list[dict],
    ) -> None:
        self.witness_by_dialogue = witness_by_dialogue
        self.schedule = schedule
        self.calls: list[dict] = []

    def chat_completion(self, payload: dict, *, caller: str, timeout_s: int) -> dict:
        metadata = self.schedule[len(self.calls)]
        self.calls.append(
            {
                "payload": copy.deepcopy(payload),
                "caller": caller,
                "timeout_s": timeout_s,
                "metadata": {
                    "dialogue_id": metadata["dialogue_id"],
                    "turn_id": metadata["turn_id"],
                },
            }
        )
        signal = self.witness_by_dialogue[metadata["dialogue_id"]][metadata["turn_id"] - 1]
        model = str(payload["model"])
        provider = "Google" if model.startswith("google/") else "OpenAI"
        return {
            "ok": True,
            "status_code": 200,
            "elapsed_ms": 12.5,
            "error": None,
            "raw_text": json.dumps(signal, ensure_ascii=False),
            "finish_reason": "stop",
            "native_finish_reason": "STOP",
            "usage": {
                "prompt_tokens": 640,
                "completion_tokens": 48,
                "total_tokens": 688,
            },
            "cost_estimate_usd": 0.0002,
            "cost_estimate_source": "provider_usage_cost",
            "generation_id": "generation-id-not-retained",
            "model": model,
            "provider": provider,
            "service_tier": "default",
        }


class Lot4S1StimmungProviderCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = dialogic_campaign.build_protocol(
            REPO_ROOT,
            freeze_commit="0" * 40,
        )
        witness_path = (
            REPO_ROOT
            / "benchmark/suites/stimmung/fixtures/stimmung_dialogic_reachability_witness_v1.json"
        )
        witness = json.loads(witness_path.read_text(encoding="utf-8"))
        cls.witness_by_dialogue = {
            item["dialogue_id"]: item["signals"] for item in witness["dialogues"]
        }
        cls.schedule = dialogic_campaign.build_request_schedule(REPO_ROOT, cls.protocol)

    def test_protocol_freezes_exact_schedule_models_parameters_and_cost_cap(self) -> None:
        summary = dialogic_campaign.validate_protocol(self.protocol, REPO_ROOT)

        self.assertEqual(summary["dialogue_count"], 16)
        self.assertEqual(summary["turn_count"], 69)
        self.assertEqual(summary["evaluated_step_count"], 32)
        self.assertEqual(summary["expected_call_count"], 276)
        self.assertEqual(self.protocol["absolute_call_cap"], 276)
        self.assertEqual(self.protocol["repetitions"], 2)
        self.assertEqual(
            self.protocol["models"],
            {
                "primary": "google/gemini-3.1-flash-lite",
                "fallback": "openai/gpt-5.4-nano",
            },
        )
        self.assertEqual(
            self.protocol["generation_params"],
            {"temperature": 0.1, "top_p": 1.0, "max_tokens": 220},
        )
        self.assertEqual(self.protocol["timeout_s"], 10)
        self.assertLessEqual(self.protocol["estimated_max_cost_usd"], 0.30)
        self.assertEqual(self.protocol["cost_cap_usd"], 0.30)

        model_mutant = copy.deepcopy(self.protocol)
        model_mutant["models"] = {
            "primary": self.protocol["models"]["fallback"],
            "fallback": self.protocol["models"]["primary"],
        }
        with self.assertRaisesRegex(ValueError, "protocol_freeze_mismatch"):
            dialogic_campaign.validate_protocol(model_mutant, REPO_ROOT)

    def test_request_schedule_uses_product_messages_and_keeps_all_turns(self) -> None:
        schedule = dialogic_campaign.build_request_schedule(REPO_ROOT, self.protocol)

        self.assertEqual(len(schedule), 276)
        self.assertEqual(
            len({(item["source"], item["repetition"], item["dialogue_id"], item["turn_id"]) for item in schedule}),
            276,
        )
        self.assertEqual(sum(1 for item in schedule if item["evaluated"]), 128)
        for source in ("primary", "fallback"):
            for repetition in (1, 2):
                selected = [
                    item for item in schedule
                    if item["source"] == source and item["repetition"] == repetition
                ]
                self.assertEqual(len(selected), 69)
        first_by_role = {
            (item["dialogue_id"], item["turn_id"], item["repetition"]): item
            for item in schedule if item["source"] == "primary"
        }
        fallback_by_role = {
            (item["dialogue_id"], item["turn_id"], item["repetition"]): item
            for item in schedule if item["source"] == "fallback"
        }
        self.assertEqual(set(first_by_role), set(fallback_by_role))
        for key, primary in first_by_role.items():
            self.assertEqual(primary["messages_sha256"], fallback_by_role[key]["messages_sha256"])
            self.assertEqual(primary["window_turn_count"], fallback_by_role[key]["window_turn_count"])
            self.assertEqual(primary["payload"]["provider"], {"allow_fallbacks": False})

    def test_fake_provider_run_traverses_normalizer_aggregation_and_scorer(self) -> None:
        client = _WitnessClient(self.witness_by_dialogue, self.schedule)
        records = dialogic_campaign.run_campaign(
            repo_root=REPO_ROOT,
            protocol=self.protocol,
            client=client,
        )
        validation = dialogic_campaign.validate_artifact(records, REPO_ROOT, self.protocol)

        self.assertEqual(len(client.calls), 276)
        self.assertEqual(validation["call_count"], 276)
        self.assertEqual(validation["dialogue_score_count"], 64)
        self.assertEqual(validation["final_decision"], "keep_current")
        self.assertTrue(all(call["caller"] == "stimmung_agent" for call in client.calls))
        self.assertTrue(all(call["timeout_s"] == 10 for call in client.calls))
        for call in client.calls:
            self.assertEqual(
                call["payload"]["provider"],
                {"allow_fallbacks": False},
            )
            self.assertNotIn(":batch", call["payload"]["model"])
            self.assertNotIn("_lot4s1_test_metadata", call["payload"])

    def test_artifact_reconstruction_rejects_mutated_aggregate_order_and_raw_fields(self) -> None:
        records = dialogic_campaign.run_campaign(
            repo_root=REPO_ROOT,
            protocol=self.protocol,
            client=_WitnessClient(self.witness_by_dialogue, self.schedule),
        )
        call_index = next(
            index for index, record in enumerate(records)
            if record["record_type"] == "call" and record["evaluated"]
        )

        aggregate_mutant = copy.deepcopy(records)
        aggregate_mutant[call_index]["aggregate"]["shift_state"] = "candidate_shift"
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_artifact(aggregate_mutant, REPO_ROOT, self.protocol)

        order_mutant = copy.deepcopy(records)
        order_mutant[0], order_mutant[1] = order_mutant[1], order_mutant[0]
        with self.assertRaisesRegex(ValueError, "call_order_invalid"):
            dialogic_campaign.validate_artifact(order_mutant, REPO_ROOT, self.protocol)

        raw_mutant = copy.deepcopy(records)
        raw_mutant[0]["raw_text"] = "synthetic raw output"
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_content_free_record(raw_mutant[0])

        free_reason_mutant = copy.deepcopy(
            next(record for record in records if record["record_type"] == "dialogue_score")
        )
        free_reason_mutant["classification"] = "fail"
        free_reason_mutant["error_class"] = "semantic"
        free_reason_mutant["reason_codes"] = ["synthetic conversational sentence"]
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_content_free_record(free_reason_mutant)

        zero_metric_mutant = copy.deepcopy(records[0])
        zero_metric_mutant["latency_ms"] = None
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_content_free_record(zero_metric_mutant)

    def test_decision_requires_complete_repetitions_and_reproducible_failure(self) -> None:
        records = dialogic_campaign.run_campaign(
            repo_root=REPO_ROOT,
            protocol=self.protocol,
            client=_WitnessClient(self.witness_by_dialogue, self.schedule),
        )
        scores = [record for record in records if record["record_type"] == "dialogue_score"]

        isolated = copy.deepcopy(scores)
        target = next(
            item for item in isolated
            if item["source"] == "primary" and item["repetition"] == 1
        )
        target["classification"] = "fail"
        target["error_class"] = "semantic"
        target["reason_codes"] = ["dominant_tone_outside_allowed"]
        self.assertEqual(
            dialogic_campaign.decide_from_dialogue_scores(isolated)["decision"],
            "inconclusive",
        )

        reproducible = copy.deepcopy(scores)
        dialogue_id = target["dialogue_id"]
        for item in reproducible:
            if item["source"] == "primary" and item["dialogue_id"] == dialogue_id:
                item["classification"] = "fail"
                item["error_class"] = "semantic"
                item["reason_codes"] = ["dominant_tone_outside_allowed"]
        decision = dialogic_campaign.decide_from_dialogue_scores(reproducible)
        self.assertEqual(decision["decision"], "strengthen")
        self.assertEqual(decision["next_micro_lot"], "4C.2")

        incomplete = scores[:-1]
        self.assertEqual(
            dialogic_campaign.decide_from_dialogue_scores(incomplete)["decision"],
            "inconclusive",
        )

    def test_invalid_json_and_fail_open_never_become_semantic_success(self) -> None:
        records = dialogic_campaign.run_campaign(
            repo_root=REPO_ROOT,
            protocol=self.protocol,
            client=_WitnessClient(self.witness_by_dialogue, self.schedule),
        )
        call = copy.deepcopy(next(record for record in records if record["record_type"] == "call"))
        call["status"] = "json_error"
        call["reason_code"] = "invalid_json"
        call["json_valid"] = False
        call["schema_valid"] = False
        call["signal"] = None
        call["fail_open"] = True
        self.assertEqual(dialogic_campaign.validate_content_free_record(call)["status"], "json_error")

        false_success = copy.deepcopy(call)
        false_success["status"] = "ok"
        false_success["reason_code"] = "ok"
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_content_free_record(false_success)

    def test_jsonl_round_trip_is_deterministic_and_content_free(self) -> None:
        records = dialogic_campaign.run_campaign(
            repo_root=REPO_ROOT,
            protocol=self.protocol,
            client=_WitnessClient(self.witness_by_dialogue, self.schedule),
        )
        encoded = dialogic_campaign.encode_jsonl(records)
        parsed = dialogic_campaign.parse_jsonl(encoded)
        self.assertEqual(parsed, records)
        self.assertEqual(dialogic_campaign.encode_jsonl(parsed), encoded)
        self.assertNotIn("generation-id-not-retained", encoded)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "artifact.jsonl"
            dialogic_campaign.write_jsonl(path, records)
            self.assertEqual(dialogic_campaign.load_jsonl(path), records)


if __name__ == "__main__":
    unittest.main()
