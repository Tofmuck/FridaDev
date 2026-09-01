from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from benchmark.core import openrouter
from benchmark.suites.stimmung import final_wording_rating_v2 as rating_v2
from benchmark.suites.stimmung import final_wording_protocol_v2 as protocol_v24
from benchmark.suites.stimmung import final_wording_gpt52_v25 as campaign_v25
from benchmark.suites.stimmung import final_wording_gpt52_v25_finalize as finalize_v25


REPO_ROOT = Path(__file__).resolve().parents[4]
FREEZE_COMMIT = "f" * 40
RESULTS_ROOT = REPO_ROOT / "benchmark/results/stimmung"


def _write_0600(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")
    os.chmod(path, 0o600)


def _codex_ratings(packet: dict[str, object]) -> dict[str, object]:
    items = packet["items"]
    assert isinstance(items, list)
    return {
        "schema_version": rating_v2.RATINGS_SCHEMA_VERSION,
        "packet_sha256": packet["packet_sha256"],
        "rating_source": "codex_assisted_review_for_tof",
        "rater_id": "codex_for_tof",
        "ratings_created_outside_runner": True,
        "ratings": [
            {
                "blind_id": item["blind_id"],
                "delicacy_effect": "equivalent",
                "formulation_fit": "equivalent",
                "psychologization": "none",
                "certainty_change": "none",
                "truth_or_evidence_change": "none",
                "masked_target": "none",
            }
            for item in items
        ],
    }


class _SyntheticGPT52Client:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def chat_completion(
        self,
        payload: dict[str, object],
        *,
        caller: str,
        timeout_s: int,
    ) -> dict[str, object]:
        self.calls.append(copy.deepcopy(payload))
        return {
            "ok": True,
            "status_code": 200,
            "raw_text": "SYNTHETIC_TEST_RESPONSE",
            "finish_reason": "stop",
            "native_finish_reason": "stop",
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            "cost_estimate_usd": 0.00001575,
            "model": "openai/gpt-5.2",
            "provider": "OpenAI",
        }


def _model_metadata(*, supported_efforts: list[str] | None = None) -> dict[str, object]:
    return {
        "id": "openai/gpt-5.2",
        "context_length": 400_000,
        "top_provider": {"max_completion_tokens": 128_000},
        "pricing": {"prompt": "0.00000175", "completion": "0.000014"},
        "reasoning": {
            "supported_efforts": supported_efforts
            if supported_efforts is not None
            else ["high", "medium", "low"],
            "default_effort": "medium",
        },
    }


class Lot4C4GPT52V25Tests(unittest.TestCase):
    def test_gpt52_is_the_only_provider_visible_variable(self) -> None:
        base = protocol_v24._build_request_schedule(REPO_ROOT)
        campaign = campaign_v25.build_protocol(REPO_ROOT, freeze_commit=FREEZE_COMMIT)
        adapted = campaign_v25.build_request_schedule(REPO_ROOT, campaign)
        self.assertEqual(len(adapted), 24)
        self.assertEqual(campaign["model"], "openai/gpt-5.2")
        self.assertEqual(campaign["reasoning"], {"effort": "high", "exclude": True})
        self.assertEqual(campaign["absolute_cost_cap_usd"], 4.0)
        self.assertLessEqual(campaign["budget_with_safety_margin_usd"], 4.0)
        self.assertEqual(
            campaign["candidate_policy"]["sha256"],
            protocol_v24.BOUNDED_ENUNCIATION_POLICY_SHA256,
        )
        for old, new in zip(base, adapted, strict=True):
            self.assertEqual(old["messages_sha256"], new["messages_sha256"])
            self.assertEqual(old["payload"]["messages"], new["payload"]["messages"])
            old_payload = copy.deepcopy(old["payload"])
            new_payload = copy.deepcopy(new["payload"])
            old_payload["model"] = new_payload["model"]
            self.assertEqual(old_payload, new_payload)
            self.assertNotIn("temperature", new_payload)
            self.assertNotIn("top_p", new_payload)
            self.assertNotIn("stop", new_payload)

    def test_metadata_preflight_requires_high_and_recalculates_frozen_budget(self) -> None:
        campaign = campaign_v25.build_protocol(REPO_ROOT, freeze_commit=FREEZE_COMMIT)
        summary = campaign_v25.validate_model_metadata(
            capability_summary={
                "status": "compatible",
                "reason_code": "compatible_endpoint_available",
                "model": "openai/gpt-5.2",
                "metadata_http_status": 200,
                "endpoint_count": 2,
                "compatible_endpoint_count": 1,
                "required_capabilities": ["output_token_limit", "reasoning"],
            },
            model_metadata=_model_metadata(),
            protocol=campaign,
        )
        self.assertEqual(summary["status"], "compatible")
        self.assertTrue(summary["reasoning_effort_high_supported"])
        self.assertEqual(summary["context_length"], 400_000)
        self.assertEqual(summary["max_completion_tokens"], 128_000)
        self.assertEqual(summary["prompt_price_usd_per_token"], 0.00000175)
        self.assertEqual(summary["completion_price_usd_per_token"], 0.000014)
        self.assertLessEqual(summary["budget_with_safety_margin_usd"], 4.0)

    def test_metadata_preflight_rejects_missing_high_or_changed_price(self) -> None:
        campaign = campaign_v25.build_protocol(REPO_ROOT, freeze_commit=FREEZE_COMMIT)
        base = {
            "status": "compatible",
            "reason_code": "compatible_endpoint_available",
            "model": "openai/gpt-5.2",
            "metadata_http_status": 200,
            "endpoint_count": 1,
            "compatible_endpoint_count": 1,
            "required_capabilities": ["output_token_limit", "reasoning"],
        }
        missing_high = _model_metadata(supported_efforts=["medium", "low"])
        self.assertEqual(
            campaign_v25.validate_model_metadata(
                capability_summary=base,
                model_metadata=missing_high,
                protocol=campaign,
            )["status"],
            "no_compatible_endpoint",
        )
        changed_price = _model_metadata()
        changed_price["pricing"]["completion"] = "0.000015"  # type: ignore[index]
        self.assertEqual(
            campaign_v25.validate_model_metadata(
                capability_summary=base,
                model_metadata=changed_price,
                protocol=campaign,
            )["status"],
            "metadata_contract_mismatch",
        )

    def test_live_preflight_reads_exact_slug_then_fresh_model_metadata(self) -> None:
        campaign = campaign_v25.build_protocol(REPO_ROOT, freeze_commit=FREEZE_COMMIT)

        class Response:
            status_code = 200

            def __init__(self, payload: dict[str, object]) -> None:
                self._payload = payload

            def json(self) -> dict[str, object]:
                return self._payload

        endpoint_response = Response(
            {
                "data": {
                    "id": "openai/gpt-5.2",
                    "endpoints": [
                        {"supported_parameters": ["reasoning", "max_tokens"]}
                    ],
                }
            }
        )
        model_response = Response({"data": [_model_metadata()]})
        client = campaign_v25.GPT52OpenRouterClient(
            openrouter.OpenRouterConfig(
                base_url="https://openrouter.invalid/api/v1",
                api_key="synthetic-secret",
            ),
            protocol=campaign,
        )
        with mock.patch.object(
            openrouter.requests,
            "get",
            side_effect=[endpoint_response, model_response],
        ) as get:
            summary = client.preflight_model_capabilities(
                "openai/gpt-5.2",
                campaign_v25.REQUIRED_ENDPOINT_CAPABILITIES,
            )
        self.assertEqual(summary["status"], "compatible")
        self.assertEqual(get.call_count, 2)
        self.assertEqual(
            get.call_args_list[0].args[0],
            "https://openrouter.invalid/api/v1/models/openai/gpt-5.2/endpoints",
        )
        self.assertEqual(
            get.call_args_list[1].args[0],
            "https://openrouter.invalid/api/v1/models",
        )
        self.assertNotIn("synthetic-secret", repr(summary))

    def test_gpt51_response_cannot_be_presented_as_gpt52(self) -> None:
        outcome = campaign_v25.classify_provider_result(
            {
                "ok": True,
                "status_code": 200,
                "raw_text": "SYNTHETIC_TEST_RESPONSE",
                "finish_reason": "stop",
                "native_finish_reason": "stop",
                "usage": {},
                "cost_estimate_usd": 0.0,
                "model": "openai/gpt-5.1",
                "provider": "OpenAI",
            }
        )
        self.assertEqual(outcome["status"], "provider_routing_error")
        self.assertEqual(outcome["requested_model"], "openai/gpt-5.2")
        self.assertEqual(outcome["observed_model"], "unknown")

    def test_synthetic_campaign_reuses_runner_and_stops_for_human_rating(self) -> None:
        campaign = campaign_v25.build_protocol(REPO_ROOT, freeze_commit=FREEZE_COMMIT)
        client = _SyntheticGPT52Client()
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            result = campaign_v25.run_campaign(
                repo_root=REPO_ROOT,
                protocol=campaign,
                client=client,
                output_dir=root / "private",
                review_export_dir=root / "review",
                execution_authorized=True,
                evidence_source="synthetic_test",
            )
            self.assertEqual(result["status"], "human_rating_required")
            self.assertEqual(result["attempted_call_count"], 24)
            self.assertEqual(len(client.calls), 24)
            self.assertTrue((root / "review" / "rating_packet.json").is_file())
            self.assertTrue((root / "private" / "blind_mapping.json").is_file())
            self.assertFalse((root / "review" / "blind_mapping.json").exists())
            for payload in client.calls:
                self.assertEqual(payload["model"], "openai/gpt-5.2")
                self.assertEqual(payload["reasoning"], {"effort": "high", "exclude": True})
                self.assertEqual(
                    payload["provider"],
                    {"allow_fallbacks": False, "require_parameters": True},
                )

    def test_v25_finalizer_requires_ratification_then_preserves_gpt52_evidence(self) -> None:
        campaign = campaign_v25.build_protocol(REPO_ROOT, freeze_commit=FREEZE_COMMIT)
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            private_dir = root / "private"
            review_dir = root / "review"
            result = campaign_v25.run_campaign(
                repo_root=REPO_ROOT,
                protocol=campaign,
                client=_SyntheticGPT52Client(),
                output_dir=private_dir,
                review_export_dir=review_dir,
                execution_authorized=True,
                evidence_source="synthetic_test",
            )
            self.assertEqual(result["status"], "human_rating_required")
            packet_path = review_dir / "rating_packet.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            ratings_path = review_dir / "ratings.json"
            _write_0600(ratings_path, _codex_ratings(packet))
            ledger_path = private_dir / "call_ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            durable_path = root / "durable.json"

            with mock.patch.object(
                campaign_v25,
                "expected_live_campaign_paths",
                return_value=(private_dir, review_dir),
            ):
                with self.assertRaisesRegex(ValueError, "call_ledger_provenance_invalid"):
                    rating_v2.finalize_campaign(
                        campaign_dir=private_dir,
                        rating_packet_path=packet_path,
                        ratings_path=ratings_path,
                        durable_output=durable_path,
                    )
                pending = finalize_v25.finalize_campaign(
                    repo_root=REPO_ROOT,
                    freeze_commit=FREEZE_COMMIT,
                    campaign_dir=private_dir,
                    rating_packet_path=packet_path,
                    ratings_path=ratings_path,
                    durable_output=durable_path,
                )
                self.assertEqual(pending["status"], "human_ratification_required")
                self.assertTrue(private_dir.is_dir())
                self.assertTrue(review_dir.is_dir())
                self.assertFalse(durable_path.exists())

                ratings_sha = hashlib.sha256(ratings_path.read_bytes()).hexdigest()
                ratification_path = root / "ratification.json"
                _write_0600(
                    ratification_path,
                    {
                        "schema_version": rating_v2.RATIFICATION_SCHEMA_VERSION,
                        "packet_sha256": packet["packet_sha256"],
                        "ratings_sha256": ratings_sha,
                        "ratification_source": "tof_human_ratification",
                        "ratifier_id": "tof",
                        "decision": "accept",
                        "ratification_created_outside_provider_runner": True,
                    },
                )
                artifact = finalize_v25.finalize_campaign(
                    repo_root=REPO_ROOT,
                    freeze_commit=FREEZE_COMMIT,
                    campaign_dir=private_dir,
                    rating_packet_path=packet_path,
                    ratings_path=ratings_path,
                    ratification_path=ratification_path,
                    durable_output=durable_path,
                )

            self.assertEqual(artifact["decision"], "provider_campaign_required")
            self.assertEqual(artifact["route_counts"]["models"], {"openai/gpt-5.2": 24})
            self.assertEqual(artifact["observed_cost_usd"], ledger["observed_cost_usd"])
            self.assertEqual(artifact["ratification_source"], "tof_human_ratification")
            self.assertFalse(private_dir.exists())
            self.assertFalse(review_dir.exists())
            self.assertTrue(durable_path.is_file())

    def test_v25_finalize_cli_is_offline(self) -> None:
        artifact = {
            "decision": "fail",
            "call_count": 24,
            "rating_count": 12,
        }
        with mock.patch.object(
            finalize_v25,
            "finalize_campaign",
            return_value=artifact,
        ) as finalize, mock.patch.object(
            campaign_v25.OpenRouterClient,
            "from_env",
        ) as from_env:
            status = finalize_v25.main(
                [
                    "--repo-root", str(REPO_ROOT),
                    "--freeze-commit", FREEZE_COMMIT,
                    "--campaign-dir", "/tmp/private",
                    "--rating-packet", "/tmp/review/rating_packet.json",
                    "--ratings", "/tmp/review/ratings.json",
                    "--tof-ratification", "/tmp/ratification.json",
                    "--durable-output", "/tmp/durable.json",
                ]
            )
        self.assertEqual(status, 0)
        finalize.assert_called_once()
        from_env.assert_not_called()

    def test_ratified_gpt51_and_gpt52_artifacts_reject_the_same_candidate(self) -> None:
        expected = {
            "2026-09-01-lot4c4-final-wording-v2-4-gpt-5-1.json": {
                "model": "openai/gpt-5.1",
                "cost": 0.389553,
                "delicacy": 4,
                "formulation": 6,
                "critical": 3,
            },
            "2026-09-01-lot4c4-final-wording-v2-5-gpt-5-2.json": {
                "model": "openai/gpt-5.2",
                "cost": 0.2541882,
                "delicacy": 4,
                "formulation": 5,
                "critical": 5,
            },
        }
        for filename, evidence in expected.items():
            with self.subTest(filename=filename):
                artifact = json.loads(
                    (RESULTS_ROOT / filename).read_text(encoding="utf-8")
                )
                self.assertTrue(rating_v2.validate_durable_artifact(artifact))
                self.assertEqual(artifact["decision"], "fail")
                self.assertEqual(
                    artifact["reason_codes"],
                    [
                        "critical_zero_tolerance_breached",
                        "delicacy_improvement_threshold_missed",
                        "formulation_improvement_threshold_missed",
                    ],
                )
                self.assertEqual(
                    artifact["route_counts"]["models"],
                    {evidence["model"]: 24},
                )
                self.assertEqual(artifact["observed_cost_usd"], evidence["cost"])
                metrics = artifact["metrics"]
                self.assertEqual(
                    metrics["transition_delicacy_improved_count"],
                    evidence["delicacy"],
                )
                self.assertEqual(
                    metrics["transition_formulation_improved_count"],
                    evidence["formulation"],
                )
                self.assertEqual(
                    metrics["critical_failure_count"], evidence["critical"]
                )
                recalculated, reasons, observed = rating_v2._decision(
                    evidence_source="main_model_provider",
                    ledger={"outputs_complete": True},
                    metrics=metrics,
                )
                self.assertEqual(recalculated, artifact["decision"])
                self.assertEqual(reasons, artifact["reason_codes"])
                self.assertTrue(observed)

    def test_dry_run_is_offline_and_frozen(self) -> None:
        summary = campaign_v25.dry_run(REPO_ROOT, freeze_commit=FREEZE_COMMIT)
        self.assertEqual(summary["status"], "ready_offline")
        self.assertEqual(summary["decision"], "provider_campaign_required")
        self.assertEqual(summary["model"], "openai/gpt-5.2")
        self.assertEqual(summary["expected_call_count"], 24)
        self.assertEqual(summary["absolute_cost_cap_usd"], 4.0)


if __name__ == "__main__":
    unittest.main()
