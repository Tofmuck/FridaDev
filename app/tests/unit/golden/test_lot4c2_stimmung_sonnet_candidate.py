from __future__ import annotations

import copy
import json
import sys
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
from core import stimmung_agent


class _SonnetWitnessClient:
    def __init__(
        self,
        witness_by_dialogue: dict[str, list[dict]],
        schedule: list[dict],
    ) -> None:
        self.witness_by_dialogue = witness_by_dialogue
        self.schedule = schedule
        self.calls: list[dict] = []

    def chat_completion(self, payload: dict, *, caller: str, timeout_s: int) -> dict:
        plan = self.schedule[len(self.calls)]
        self.calls.append(
            {
                "payload": copy.deepcopy(payload),
                "caller": caller,
                "timeout_s": timeout_s,
            }
        )
        signal = self.witness_by_dialogue[plan["dialogue_id"]][plan["turn_id"] - 1]
        return {
            "ok": True,
            "status_code": 200,
            "elapsed_ms": 250.0,
            "error": None,
            "raw_text": json.dumps(signal, ensure_ascii=False),
            "finish_reason": "stop",
            "native_finish_reason": "end_turn",
            "usage": {
                "prompt_tokens": 700,
                "completion_tokens": 180,
                "total_tokens": 880,
                "completion_tokens_details": {"reasoning_tokens": 80},
            },
            "cost_estimate_usd": 0.0032,
            "cost_estimate_source": "provider_usage_cost",
            "generation_id": "not-retained",
            "model": "anthropic/claude-sonnet-5-20260630",
            "provider": "Anthropic",
            "service_tier": "default",
        }


class Lot4C2StimmungSonnetCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = dialogic_campaign.build_sonnet_candidate_protocol(
            REPO_ROOT,
            freeze_commit="4" * 40,
        )
        cls.schedule = dialogic_campaign.build_sonnet_candidate_request_schedule(
            REPO_ROOT,
            cls.protocol,
        )
        witness_path = (
            REPO_ROOT
            / "benchmark/suites/stimmung/fixtures/stimmung_dialogic_reachability_witness_v1.json"
        )
        witness = json.loads(witness_path.read_text(encoding="utf-8"))
        cls.witness_by_dialogue = {
            item["dialogue_id"]: item["signals"] for item in witness["dialogues"]
        }

    def test_structural_maximum_and_strict_schema_derive_from_runtime_contract(self) -> None:
        maximum = dialogic_campaign.derive_stimmung_structural_maximum()
        response_format = dialogic_campaign.build_stimmung_response_format()
        schema = response_format["json_schema"]["schema"]

        self.assertEqual(maximum["tone_count"], len(stimmung_agent.ALLOWED_TONES))
        self.assertEqual(maximum["compact_chars"], 418)
        self.assertEqual(maximum["spaced_chars"], 462)
        self.assertEqual(maximum["indent2_chars"], 676)
        self.assertEqual(maximum["response_reserve_tokens"], 1024)
        self.assertEqual(maximum["reasoning_headroom_tokens"], 14976)
        self.assertEqual(response_format["type"], "json_schema")
        self.assertTrue(response_format["json_schema"]["strict"])
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["tones"]["maxItems"], 9)
        self.assertEqual(
            set(schema["properties"]["tones"]["items"]["properties"]["tone"]["enum"]),
            set(stimmung_agent.ALLOWED_TONES),
        )
        self.assertEqual(set(schema["required"]), set(stimmung_agent._ALLOWED_SIGNAL_KEYS))

    def test_protocol_freezes_sonnet_policy_cost_provenance_and_exact_schedule(self) -> None:
        summary = dialogic_campaign.validate_sonnet_candidate_protocol(
            self.protocol,
            REPO_ROOT,
        )

        self.assertEqual(summary["expected_call_count"], 138)
        self.assertEqual(self.protocol["absolute_call_cap"], 138)
        self.assertEqual(self.protocol["model"], "anthropic/claude-sonnet-5")
        self.assertEqual(
            self.protocol["canonical_slug"],
            "anthropic/claude-sonnet-5-20260630",
        )
        self.assertEqual(self.protocol["allowed_providers"], ["Anthropic"])
        self.assertEqual(self.protocol["reasoning"], {"effort": "medium", "exclude": True})
        self.assertEqual(self.protocol["max_tokens"], 16000)
        self.assertEqual(self.protocol["timeout_s"], 30)
        self.assertEqual(self.protocol["provider_policy"], {
            "order": ["Anthropic"],
            "allow_fallbacks": False,
            "require_parameters": True,
        })
        self.assertLess(self.protocol["estimated_max_cost_usd"], 25.0)
        self.assertEqual(self.protocol["cost_cap_usd"], 25.0)
        self.assertEqual(len(self.schedule), 138)
        self.assertEqual({item["source"] for item in self.schedule}, {"primary"})
        self.assertEqual(
            {item["payload"]["model"] for item in self.schedule},
            {"anthropic/claude-sonnet-5"},
        )
        self.assertTrue(all(item["payload"]["messages"] for item in self.schedule))

    def test_payload_is_strict_anthropic_only_without_sampling_tools_retry_or_fallback(self) -> None:
        payload = self.schedule[0]["payload"]
        self.assertEqual(
            set(payload),
            {"model", "messages", "max_tokens", "reasoning", "provider", "response_format"},
        )
        self.assertEqual(payload["reasoning"], {"effort": "medium", "exclude": True})
        self.assertEqual(payload["provider"], {
            "order": ["Anthropic"],
            "allow_fallbacks": False,
            "require_parameters": True,
        })
        self.assertNotIn("temperature", payload)
        self.assertNotIn("top_p", payload)
        self.assertNotIn("top_k", payload)
        self.assertNotIn("tools", payload)
        dialogic_campaign.validate_sonnet_candidate_payload(payload)

        mutations = {
            "latest_alias": ("model", "anthropic/claude-sonnet-5:latest"),
            "wrong_cap": ("max_tokens", 15999),
            "sampling": ("temperature", 0.1),
        }
        for label, (key, value) in mutations.items():
            with self.subTest(label=label):
                mutant = copy.deepcopy(payload)
                mutant[key] = value
                with self.assertRaises(ValueError):
                    dialogic_campaign.validate_sonnet_candidate_payload(mutant)

        effort = copy.deepcopy(payload)
        effort["reasoning"]["effort"] = "high"
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_sonnet_candidate_payload(effort)

        route = copy.deepcopy(payload)
        route["provider"]["order"] = ["amazon-bedrock"]
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_sonnet_candidate_payload(route)

        schema = copy.deepcopy(payload)
        schema["response_format"]["json_schema"]["strict"] = False
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_sonnet_candidate_payload(schema)

    def test_only_native_model_tuple_differs_from_historical_primary(self) -> None:
        historical_protocol = dialogic_campaign.build_protocol(
            REPO_ROOT,
            freeze_commit=dialogic_campaign.PHASE_A_FREEZE_COMMIT,
        )
        historical = [
            item
            for item in dialogic_campaign.build_request_schedule(
                REPO_ROOT,
                historical_protocol,
            )
            if item["source"] == "primary"
        ]

        self.assertEqual(len(historical), len(self.schedule))
        for control, candidate in zip(historical, self.schedule):
            self.assertEqual(
                {key: control[key] for key in ("sequence", "dialogue_id", "turn_id", "evaluated", "repetition")},
                {key: candidate[key] for key in ("sequence", "dialogue_id", "turn_id", "evaluated", "repetition")},
            )
            self.assertEqual(control["payload"]["messages"], candidate["payload"]["messages"])
            self.assertEqual(
                dialogic_campaign.validate_sonnet_model_policy_difference(
                    control["payload"],
                    candidate["payload"],
                ),
                list(dialogic_campaign.SONNET_ALLOWED_POLICY_DIFFERENCES),
            )

    def test_fake_run_traverses_product_normalizer_aggregator_and_strict_decision(self) -> None:
        client = _SonnetWitnessClient(self.witness_by_dialogue, self.schedule)
        records = dialogic_campaign.run_sonnet_candidate_campaign(
            repo_root=REPO_ROOT,
            protocol=self.protocol,
            client=client,
        )
        validation = dialogic_campaign.validate_sonnet_candidate_artifact(
            records,
            REPO_ROOT,
            self.protocol,
        )
        calls = [item for item in records if item["record_type"] == "call"]

        self.assertEqual(len(client.calls), 138)
        self.assertEqual(validation["call_count"], 138)
        self.assertEqual(validation["dialogue_score_count"], 32)
        self.assertEqual(validation["final_decision"], "eligible_primary")
        self.assertTrue(all(call["caller"] == "stimmung_agent" for call in client.calls))
        self.assertTrue(all(call["timeout_s"] == 30 for call in client.calls))
        self.assertEqual({item["finish_reason"] for item in calls}, {"stop"})
        self.assertEqual({item["native_finish_reason"] for item in calls}, {"stop"})
        self.assertEqual({item["observed_provider"] for item in calls}, {"anthropic"})

    def test_artifact_and_decision_reject_raw_route_length_missing_and_31_of_32(self) -> None:
        records = dialogic_campaign.run_sonnet_candidate_campaign(
            repo_root=REPO_ROOT,
            protocol=self.protocol,
            client=_SonnetWitnessClient(self.witness_by_dialogue, self.schedule),
        )
        calls = [copy.deepcopy(item) for item in records if item["record_type"] == "call"]
        scores = [
            copy.deepcopy(item)
            for item in records
            if item["record_type"] == "dialogue_score"
        ]

        raw = copy.deepcopy(records[0])
        raw["reasoning_text"] = "synthetic raw reasoning"
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_sonnet_candidate_record(raw)

        route = copy.deepcopy(records[0])
        route["observed_provider"] = "unknown"
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_sonnet_candidate_record(route)

        length = copy.deepcopy(records[0])
        length["finish_reason"] = "length"
        length["native_finish_reason"] = "length"
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_sonnet_candidate_record(length)

        native_unknown = copy.deepcopy(records[0])
        native_unknown["native_finish_reason"] = "unknown"
        dialogic_campaign.validate_sonnet_candidate_record(native_unknown)

        with self.assertRaises(ValueError):
            dialogic_campaign.validate_sonnet_candidate_artifact(
                records[1:],
                REPO_ROOT,
                self.protocol,
            )

        failed = copy.deepcopy(scores)
        failed[0]["classification"] = "fail"
        failed[0]["error_class"] = "semantic"
        failed[0]["reason_codes"] = ["signal_overcoded"]
        self.assertEqual(
            dialogic_campaign.decide_sonnet_candidate(
                calls,
                failed,
                historical_records=dialogic_campaign.load_historical_provider_artifact(REPO_ROOT),
            )["decision"],
            "not_eligible",
        )
        self.assertEqual(
            dialogic_campaign.decide_sonnet_candidate(
                calls,
                scores[:-1],
                historical_records=dialogic_campaign.load_historical_provider_artifact(REPO_ROOT),
            )["decision"],
            "inconclusive",
        )


if __name__ == "__main__":
    unittest.main()
