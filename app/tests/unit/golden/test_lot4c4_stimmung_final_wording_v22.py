"""Authenticate v2.2/v2.3 history without bypassing the F24 runner guard."""

from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from benchmark.core import openrouter
from benchmark.suites.stimmung import final_wording_execution_v2
from benchmark.suites.stimmung import final_wording_finalization_v2


REPO_ROOT = Path(__file__).resolve().parents[4]
HISTORICAL_V21_FREEZE_SHA256 = (
    "a3afa9e8537311a107694dfc1e780741cb37676a3afbd789e3917d3e48cbab10"
)
HISTORICAL_V22_FREEZE_SHA256 = (
    "428fd763c65f2692069b569ee740631642abd06214cd92e3f23bbd31915a99a2"
)
HISTORICAL_SCHEDULE_SHA256 = (
    "73130ead0e87c596347eb5cb09f3a8fa46be541a229d79199a876e7d8e272c7b"
)
HISTORICAL_V23_FREEZE_SHA256 = (
    "77bf7bf67c8bcb1b61ae18a8ec3f86a3f0cffa4b2eb1dc82334e2a4b0f7ccb70"
)
V24_FREEZE_COMMIT = "7fcf26d8d3991b6d64f586b89025b9404316e30e"
V24_MANIFEST_SHA256 = "736cb6d83ab8c0626de8f7cc4cf3ba4a9c7ab494d69353a2d0383f361ca25f91"


class _MetadataResponse:
    status_code = 200
    content = b"{}"

    @staticmethod
    def json() -> dict[str, object]:
        return {
            "data": {
                "id": "openai/gpt-5.1",
                "name": "GPT-5.1",
                "created": 0,
                "description": "synthetic metadata",
                "architecture": {
                    "input_modalities": ["text"],
                    "output_modalities": ["text"],
                    "tokenizer": "GPT",
                    "instruct_type": None,
                    "modality": "text->text",
                },
                "endpoints": [
                    {
                        "name": "synthetic endpoint",
                        "model_id": "openai/gpt-5.1",
                        "model_name": "GPT-5.1",
                        "context_length": 400000,
                        "pricing": {"prompt": "0.00000125", "completion": "0.00001"},
                        "provider_name": "OpenAI",
                        "tag": "default",
                        "quantization": None,
                        "max_completion_tokens": 32768,
                        "max_prompt_tokens": 400000,
                        "supported_parameters": [
                            "reasoning",
                            "max_tokens",
                        ],
                        "status": 0,
                        "uptime_last_30m": 100.0,
                        "supports_implicit_caching": False,
                        "latency_last_30m": {},
                        "throughput_last_30m": {},
                    }
                ],
            }
        }


class _UnreachableClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def chat_completion(
        self,
        payload: dict[str, object],
        **_: object,
    ) -> dict[str, object]:
        self.calls.append(payload)
        raise AssertionError("historical runner reached the provider boundary")


def _authenticated_manifest(filename: str, expected_sha256: str) -> dict[str, object]:
    path = REPO_ROOT / "benchmark/suites/stimmung/fixtures" / filename
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise AssertionError(f"historical manifest changed: {filename}")
    return json.loads(raw.decode("utf-8"))


class Lot4C4WorkflowV23Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.v21_manifest = _authenticated_manifest(
            "stimmung_final_wording_freeze_v2_1.json",
            HISTORICAL_V21_FREEZE_SHA256,
        )
        cls.v22_manifest = _authenticated_manifest(
            "stimmung_final_wording_freeze_v2_2.json",
            HISTORICAL_V22_FREEZE_SHA256,
        )
        cls.v23_manifest = _authenticated_manifest(
            "stimmung_final_wording_freeze_v2_3.json",
            HISTORICAL_V23_FREEZE_SHA256,
        )
        cls.v24_manifest = _authenticated_manifest(
            "stimmung_final_wording_freeze_v2_4.json",
            V24_MANIFEST_SHA256,
        )
        cls.v24_protocol, _ = final_wording_finalization_v2.load_historical_protocol(
            REPO_ROOT,
            freeze_commit=V24_FREEZE_COMMIT,
        )

    def test_v22_v23_archives_record_the_exact_runtime_policy_transition(self) -> None:
        self.assertEqual(
            self.v22_manifest["protocol_version"],
            "lot4c4_final_wording_provider_campaign_v2_2",
        )
        self.assertEqual(
            self.v23_manifest["protocol_version"],
            "lot4c4_final_wording_provider_campaign_v2_3",
        )
        v22_policy = self.v22_manifest["runtime_policy"]
        v23_policy = self.v23_manifest["runtime_policy"]
        self.assertNotIn("temperature", v22_policy)
        self.assertNotIn("top_p", v22_policy)
        self.assertNotIn("temperature", v23_policy)
        self.assertNotIn("top_p", v23_policy)
        self.assertEqual(
            v22_policy["required_endpoint_capabilities"],
            {
                "reasoning": ["reasoning"],
                "output_token_limit": ["max_tokens"],
                "stop_sequences": ["stop"],
                "structured_outputs": ["response_format", "structured_outputs"],
            },
        )
        self.assertEqual(
            v23_policy["required_endpoint_capabilities"],
            {"reasoning": ["reasoning"], "output_token_limit": ["max_tokens"]},
        )
        self.assertEqual(self.v22_manifest["schedule"], self.v23_manifest["schedule"])

    def test_model_endpoint_preflight_is_exact_and_content_free(self) -> None:
        client = openrouter.OpenRouterClient(
            openrouter.OpenRouterConfig(
                base_url="https://openrouter.invalid/api/v1",
                api_key="synthetic-secret",
            ),
            pricing_by_model={},
        )
        with mock.patch.object(openrouter.requests, "get", return_value=_MetadataResponse()) as get:
            summary = client.preflight_model_capabilities(
                "openai/gpt-5.1",
                {
                    "reasoning": ("reasoning",),
                    "output_token_limit": ("max_tokens",),
                },
            )

        self.assertEqual(summary["status"], "compatible")
        self.assertEqual(summary["compatible_endpoint_count"], 1)
        self.assertEqual(
            get.call_args.args[0],
            "https://openrouter.invalid/api/v1/models/openai/gpt-5.1/endpoints",
        )
        self.assertEqual(
            set(summary),
            {
                "status",
                "reason_code",
                "model",
                "metadata_http_status",
                "endpoint_count",
                "compatible_endpoint_count",
                "required_capabilities",
            },
        )
        self.assertNotIn("synthetic endpoint", json.dumps(summary))

    def test_v22_preflight_refusal_and_v23_supersession_remain_historical(self) -> None:
        superseded = self.v23_manifest["supersedes"]
        self.assertEqual(superseded["protocol_version"], self.v22_manifest["protocol_version"])
        self.assertFalse(superseded["campaign_started"])
        self.assertEqual(superseded["provider_calls_observed"], 0)
        self.assertEqual(superseded["provider_inference_count"], 0)
        self.assertEqual(superseded["observed_cost_usd"], 0.0)
        self.assertIn(
            "preflight_capabilities_not_aligned_with_actual_payload",
            superseded["reason_codes"],
        )

    def test_http_4xx_taxonomy_is_not_transport(self) -> None:
        expected = {
            401: "provider_auth_error",
            403: "provider_auth_error",
            404: "provider_routing_error",
            422: "provider_request_error",
        }
        for status_code, status in expected.items():
            with self.subTest(status_code=status_code):
                outcome = final_wording_execution_v2._classify_provider_result(
                    {
                        "ok": False,
                        "status_code": status_code,
                        "error": "synthetic",
                        "raw_text": None,
                        "finish_reason": None,
                        "native_finish_reason": None,
                        "usage": {},
                        "cost_estimate_usd": None,
                        "model": "",
                        "provider": "",
                    }
                )
                self.assertEqual(outcome["status"], status)

    def test_current_public_runner_refuses_historical_protocol_before_any_effect(self) -> None:
        client = _UnreachableClient()
        progress: list[tuple[object, ...]] = []
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            private = root / "private"
            review = root / "review"
            with self.assertRaisesRegex(ValueError, "freeze_manifest_mismatch"):
                final_wording_execution_v2.run_campaign(
                    repo_root=REPO_ROOT,
                    protocol=self.v24_protocol,
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

    def test_v21_v22_and_v23_history_is_pinned_and_cannot_be_reused(self) -> None:
        self.assertEqual(self.v22_manifest["schedule"]["sha256"], HISTORICAL_SCHEDULE_SHA256)
        self.assertEqual(self.v23_manifest["schedule"]["sha256"], HISTORICAL_SCHEDULE_SHA256)
        self.assertEqual(
            self.v24_manifest["supersedes"]["protocol_version"],
            "lot4c4_final_wording_provider_campaign_v2_3",
        )
        self.assertEqual(
            self.v23_manifest["supersedes"],
            {
                "campaign_reusable": False,
                "campaign_started": False,
                "compatible_endpoint_count": 0,
                "endpoint_count": 5,
                "metadata_get_count": 1,
                "metadata_http_status": 200,
                "protocol_version": "lot4c4_final_wording_provider_campaign_v2_2",
                "provider_calls_observed": 0,
                "provider_inference_count": 0,
                "observed_cost_usd": 0.0,
                "provider_results_attached": False,
                "reason_codes": [
                    "stop_parameter_not_supported_by_gpt_5_1_endpoints",
                    "structured_outputs_capability_not_sent_by_payload",
                    "preflight_capabilities_not_aligned_with_actual_payload",
                ],
            },
        )
        output = io.StringIO()
        with mock.patch.object(
            final_wording_execution_v2.OpenRouterClient,
            "from_env",
            side_effect=AssertionError("credentials must stay unreachable"),
        ), redirect_stdout(output), tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            private = root / "private"
            review = root / "review"
            with self.assertRaisesRegex(ValueError, "freeze_manifest_mismatch"):
                final_wording_execution_v2.main(
                    [
                        "--repo-root", str(REPO_ROOT),
                        "--freeze-commit", V24_FREEZE_COMMIT,
                        "--dry-run",
                    ]
                )
            with self.assertRaisesRegex(ValueError, "freeze_manifest_mismatch"):
                final_wording_execution_v2.main(
                    [
                        "--repo-root", str(REPO_ROOT),
                        "--freeze-commit", V24_FREEZE_COMMIT,
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
