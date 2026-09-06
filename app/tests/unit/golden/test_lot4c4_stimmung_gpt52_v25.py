"""Separate frozen v2.5 evidence from deliberately refused runner reuse."""

from __future__ import annotations

import copy
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from benchmark.core import openrouter
from benchmark.suites.stimmung import final_wording_finalization_v2 as finalization_v2
from benchmark.suites.stimmung import final_wording_gpt52_v25 as campaign_v25
from benchmark.suites.stimmung import final_wording_gpt52_v25_finalize as finalize_v25
from benchmark.suites.stimmung import final_wording_protocol_v2 as protocol_v24
from benchmark.suites.stimmung import final_wording_rating_v2 as rating_v2


REPO_ROOT = Path(__file__).resolve().parents[4]
V24_FREEZE_COMMIT = "7fcf26d8d3991b6d64f586b89025b9404316e30e"
V25_FREEZE_COMMIT = "1371a2422ec835b2229bd5c7668bccadd7363fc2"
RESULTS_ROOT = REPO_ROOT / "benchmark/results/stimmung"
V25_MANIFEST_PATH = (
    REPO_ROOT
    / "benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2_5.json"
)
V25_MANIFEST_SHA256 = "3f1863a855a13a49528348968cce2a748758c208ec0f0b19456101f0557521ec"
V25_RESULT_PATH = (
    RESULTS_ROOT / "2026-09-01-lot4c4-final-wording-v2-5-gpt-5-2.json"
)
V25_RESULT_SHA256 = "4a6b0f6f1f38c6917a3dfd50ceeb992ca6a61a4ce1c20afcfaefcfdc3a6dc5da"


def _historical_v24() -> tuple[dict[str, object], list[dict[str, object]]]:
    return finalization_v2.load_historical_protocol(
        REPO_ROOT,
        freeze_commit=V24_FREEZE_COMMIT,
    )


def _historical_v25() -> tuple[dict[str, object], list[dict[str, object]]]:
    with campaign_v25._campaign_profile():
        return finalization_v2.load_historical_protocol(
            REPO_ROOT,
            freeze_commit=V25_FREEZE_COMMIT,
        )


class _UnreachableGPT52Client:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def chat_completion(self, payload: dict[str, object], **_: object) -> dict[str, object]:
        self.calls.append(payload)
        raise AssertionError("historical GPT-5.2 runner reached the provider boundary")


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
    def test_gpt52_is_the_only_provider_visible_variable_in_the_archive(self) -> None:
        base_protocol, base = _historical_v24()
        campaign, adapted = _historical_v25()
        self.assertEqual(len(adapted), 24)
        self.assertEqual(campaign["model"], "openai/gpt-5.2")
        self.assertEqual(campaign["reasoning"], {"effort": "high", "exclude": True})
        self.assertEqual(campaign["absolute_cost_cap_usd"], 4.0)
        self.assertLessEqual(campaign["budget_with_safety_margin_usd"], 4.0)
        self.assertEqual(
            campaign["candidate_policy"]["sha256"],
            protocol_v24.BOUNDED_ENUNCIATION_POLICY_SHA256,
        )
        self.assertEqual(base_protocol["model"], "openai/gpt-5.1")
        for old, new in zip(base, adapted, strict=True):
            self.assertEqual(old["messages_sha256"], new["messages_sha256"])
            self.assertEqual(old["payload"]["messages"], new["payload"]["messages"])
            old_payload = copy.deepcopy(old["payload"])
            new_payload = copy.deepcopy(new["payload"])
            old_payload["model"] = new_payload["model"]
            self.assertEqual(old_payload, new_payload)
            self.assertEqual(new_payload["reasoning"], {"effort": "high", "exclude": True})
            self.assertEqual(
                new_payload["provider"],
                {"allow_fallbacks": False, "require_parameters": True},
            )
            self.assertNotIn("temperature", new_payload)
            self.assertNotIn("top_p", new_payload)
            self.assertNotIn("stop", new_payload)

    def test_metadata_preflight_requires_high_and_recalculates_frozen_budget(self) -> None:
        campaign, _ = _historical_v25()
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
        self.assertLessEqual(summary["budget_with_safety_margin_usd"], 4.0)

    def test_metadata_preflight_rejects_missing_high_or_changed_price(self) -> None:
        campaign, _ = _historical_v25()
        base = {
            "status": "compatible",
            "reason_code": "compatible_endpoint_available",
            "model": "openai/gpt-5.2",
            "metadata_http_status": 200,
            "endpoint_count": 1,
            "compatible_endpoint_count": 1,
            "required_capabilities": ["output_token_limit", "reasoning"],
        }
        self.assertEqual(
            campaign_v25.validate_model_metadata(
                capability_summary=base,
                model_metadata=_model_metadata(supported_efforts=["medium", "low"]),
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

    def test_live_preflight_component_reads_exact_slug_and_model_metadata(self) -> None:
        campaign, _ = _historical_v25()

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
                    "endpoints": [{"supported_parameters": ["reasoning", "max_tokens"]}],
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

    def test_public_runner_refuses_drift_before_client_progress_or_files(self) -> None:
        campaign, _ = _historical_v25()
        client = _UnreachableGPT52Client()
        progress: list[tuple[object, ...]] = []
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            private = root / "private"
            review = root / "review"
            with self.assertRaisesRegex(ValueError, "freeze_manifest_mismatch"):
                campaign_v25.run_campaign(
                    repo_root=REPO_ROOT,
                    protocol=campaign,
                    client=client,
                    output_dir=private,
                    review_export_dir=review,
                    execution_authorized=True,
                    evidence_source="synthetic_test",
                    progress=lambda *args: progress.append(args),
                    capability_progress=lambda *args: progress.append(args),
                )
            self.assertEqual(client.calls, [])
            self.assertEqual(progress, [])
            self.assertFalse(private.exists())
            self.assertFalse(review.exists())

    def test_v25_finalizer_archive_inputs_match_retained_evidence(self) -> None:
        raw_manifest = V25_MANIFEST_PATH.read_bytes()
        raw_result = V25_RESULT_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(raw_manifest).hexdigest(), V25_MANIFEST_SHA256)
        self.assertEqual(hashlib.sha256(raw_result).hexdigest(), V25_RESULT_SHA256)
        protocol, schedule = _historical_v25()
        artifact = json.loads(raw_result.decode("utf-8"))
        self.assertTrue(rating_v2.validate_durable_artifact(artifact))
        self.assertEqual(protocol_v24.protocol_sha256(protocol), artifact["protocol_sha256"])
        self.assertEqual(len(schedule), 24)
        self.assertEqual(artifact["route_counts"]["models"], {"openai/gpt-5.2": 24})

    def test_v25_finalize_cli_is_offline_argument_wiring(self) -> None:
        artifact = {"decision": "fail", "call_count": 24, "rating_count": 12}
        output = io.StringIO()
        with mock.patch.object(
            finalize_v25,
            "finalize_campaign",
            return_value=artifact,
        ) as finalize, mock.patch.object(
            campaign_v25.OpenRouterClient,
            "from_env",
        ) as from_env, redirect_stdout(output):
            status = finalize_v25.main(
                [
                    "--repo-root", str(REPO_ROOT),
                    "--freeze-commit", V25_FREEZE_COMMIT,
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
        self.assertEqual(
            json.loads(output.getvalue()),
            {
                "status": "finalized",
                "decision": "fail",
                "call_count": 24,
                "rating_count": 12,
            },
        )

    def test_ratified_gpt51_and_gpt52_artifacts_reject_the_same_candidate(self) -> None:
        expected = {
            "2026-09-01-lot4c4-final-wording-v2-4-gpt-5-1.json": (
                "openai/gpt-5.1", 0.389553, 4, 6, 3
            ),
            "2026-09-01-lot4c4-final-wording-v2-5-gpt-5-2.json": (
                "openai/gpt-5.2", 0.2541882, 4, 5, 5
            ),
        }
        for filename, evidence in expected.items():
            with self.subTest(filename=filename):
                artifact = json.loads((RESULTS_ROOT / filename).read_text(encoding="utf-8"))
                model, cost, delicacy, formulation, critical = evidence
                self.assertTrue(rating_v2.validate_durable_artifact(artifact))
                self.assertEqual(artifact["decision"], "fail")
                self.assertEqual(artifact["route_counts"]["models"], {model: 24})
                self.assertEqual(artifact["observed_cost_usd"], cost)
                self.assertEqual(
                    artifact["metrics"]["transition_delicacy_improved_count"],
                    delicacy,
                )
                self.assertEqual(
                    artifact["metrics"]["transition_formulation_improved_count"],
                    formulation,
                )
                self.assertEqual(artifact["metrics"]["critical_failure_count"], critical)

    def test_cli_refuses_dry_run_and_execution_before_output_or_credentials(self) -> None:
        output = io.StringIO()
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            private = root / "private"
            review = root / "review"
            with mock.patch.object(
                campaign_v25.OpenRouterClient,
                "from_env",
                side_effect=AssertionError("credentials must stay unreachable"),
            ), redirect_stdout(output):
                with self.assertRaisesRegex(ValueError, "freeze_manifest_mismatch"):
                    campaign_v25.main(
                        [
                            "--repo-root", str(REPO_ROOT),
                            "--freeze-commit", V25_FREEZE_COMMIT,
                            "--dry-run",
                        ]
                    )
                with self.assertRaisesRegex(ValueError, "freeze_manifest_mismatch"):
                    campaign_v25.main(
                        [
                            "--repo-root", str(REPO_ROOT),
                            "--freeze-commit", V25_FREEZE_COMMIT,
                            "--execute-live",
                            "--output-dir", str(private),
                            "--review-export-dir", str(review),
                        ]
                    )
            self.assertFalse(private.exists())
            self.assertFalse(review.exists())
        self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
