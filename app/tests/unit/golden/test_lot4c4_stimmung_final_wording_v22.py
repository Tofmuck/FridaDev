from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from benchmark.core import openrouter
from benchmark.suites.stimmung import final_wording_execution_v2
from benchmark.suites.stimmung import final_wording_protocol_v2


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


class _SyntheticProviderClient(openrouter.OpenRouterClient):
    def __init__(self, *, preflight_status: str, response_status: int) -> None:
        super().__init__(
            openrouter.OpenRouterConfig(
                base_url="https://openrouter.invalid/api/v1",
                api_key="synthetic-secret",
            ),
            pricing_by_model={},
        )
        self.preflight_status = preflight_status
        self.response_status = response_status
        self.events: list[str] = []
        self.calls: list[dict[str, object]] = []

    def preflight_model_capabilities(
        self,
        model: str,
        required_capabilities: dict[str, tuple[str, ...]],
    ) -> dict[str, object]:
        self.events.append("preflight")
        compatible = self.preflight_status == "compatible"
        return {
            "status": self.preflight_status,
            "reason_code": (
                "compatible_endpoint_available"
                if compatible
                else "no_compatible_provider_endpoint"
            ),
            "model": model,
            "metadata_http_status": 200,
            "endpoint_count": 1,
            "compatible_endpoint_count": int(compatible),
            "required_capabilities": sorted(required_capabilities),
        }

    def chat_completion(
        self,
        payload: dict[str, object],
        *,
        caller: str,
        timeout_s: int,
    ) -> dict[str, object]:
        self.events.append("post")
        self.calls.append(copy.deepcopy(payload))
        if self.response_status != 200:
            return {
                "ok": False,
                "status_code": self.response_status,
                "elapsed_ms": 1.0,
                "error": "synthetic provider error",
                "raw_text": None,
                "finish_reason": None,
                "native_finish_reason": None,
                "usage": {},
                "cost_estimate_usd": None,
                "model": "",
                "provider": "",
            }
        return {
            "ok": True,
            "status_code": 200,
            "elapsed_ms": 1.0,
            "error": None,
            "raw_text": "SYNTHETIC_TEST_RESPONSE",
            "finish_reason": "stop",
            "native_finish_reason": "stop",
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            "cost_estimate_usd": 0.00001125,
            "model": "openai/gpt-5.1",
            "provider": "OpenAI",
        }


class Lot4C4WorkflowV23Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = final_wording_protocol_v2.build_protocol(
            REPO_ROOT,
            freeze_commit="f" * 40,
        )

    def test_payload_removes_sampling_without_changing_messages_or_schedule(self) -> None:
        schedule = final_wording_protocol_v2.build_request_schedule(
            REPO_ROOT,
            self.protocol,
        )
        self.assertEqual(len(schedule), 24)
        self.assertEqual(
            self.protocol["protocol_version"],
            "lot4c4_final_wording_bounded_candidate_v2_4",
        )
        self.assertNotIn("temperature", self.protocol)
        self.assertNotIn("top_p", self.protocol)
        for item in schedule:
            payload = item["payload"]
            self.assertNotIn("temperature", payload)
            self.assertNotIn("top_p", payload)
            self.assertNotIn("stop", payload)
            self.assertEqual(payload["model"], "openai/gpt-5.1")
            self.assertEqual(payload["max_tokens"], 8192)
            self.assertEqual(payload["reasoning"], {"effort": "high", "exclude": True})
            self.assertEqual(
                payload["provider"],
                {"allow_fallbacks": False, "require_parameters": True},
            )

        mutated = copy.deepcopy(schedule)
        mutated[0]["payload"]["temperature"] = 0.7
        with self.assertRaisesRegex(ValueError, "schedule_runtime_policy_invalid"):
            final_wording_protocol_v2.validate_schedule(
                final_wording_protocol_v2.load_corpus(REPO_ROOT),
                mutated,
            )
        mutated = copy.deepcopy(schedule)
        mutated[0]["payload"]["stop"] = ["<|endoftext|>"]
        with self.assertRaisesRegex(ValueError, "schedule_runtime_policy_invalid"):
            final_wording_protocol_v2.validate_schedule(
                final_wording_protocol_v2.load_corpus(REPO_ROOT),
                mutated,
            )

        self.assertEqual(
            self.protocol["required_endpoint_capabilities"],
            {
                "reasoning": ["reasoning"],
                "output_token_limit": ["max_tokens"],
            },
        )
        mutated_protocol = copy.deepcopy(self.protocol)
        mutated_protocol["required_endpoint_capabilities"]["structured_outputs"] = [
            "response_format"
        ]
        with self.assertRaises(ValueError):
            final_wording_protocol_v2.validate_protocol(mutated_protocol, REPO_ROOT)

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

    def test_preflight_rejects_missing_or_false_compatible_endpoints_before_post(self) -> None:
        for status in ("no_compatible_endpoint", "model_metadata_mismatch"):
            with self.subTest(status=status), tempfile.TemporaryDirectory(dir="/tmp") as raw:
                root = Path(raw)
                client = _SyntheticProviderClient(
                    preflight_status=status,
                    response_status=200,
                )
                with mock.patch.object(
                    final_wording_execution_v2,
                    "_validate_live_campaign_paths",
                    return_value=None,
                ):
                    result = final_wording_execution_v2.run_campaign(
                        repo_root=REPO_ROOT,
                        protocol=self.protocol,
                        client=client,
                        output_dir=root / "private",
                        review_export_dir=root / "review",
                        execution_authorized=True,
                        evidence_source="main_model_provider",
                    )
                self.assertEqual(result["status"], "campaign_incomplete")
                self.assertEqual(result["reason_code"], "no_compatible_provider_endpoint")
                self.assertEqual(result["attempted_call_count"], 0)
                self.assertEqual(client.events, ["preflight"])
                self.assertFalse((root / "private").exists())

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

    def test_first_sequence_is_the_only_canary_and_404_stops_without_retry(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            client = _SyntheticProviderClient(
                preflight_status="compatible",
                response_status=404,
            )
            with mock.patch.object(
                final_wording_execution_v2,
                "_validate_live_campaign_paths",
                return_value=None,
            ):
                result = final_wording_execution_v2.run_campaign(
                    repo_root=REPO_ROOT,
                    protocol=self.protocol,
                    client=client,
                    output_dir=root / "private",
                    review_export_dir=root / "review",
                    execution_authorized=True,
                    evidence_source="main_model_provider",
                )
            ledger = json.loads(
                (root / "private/call_ledger.json").read_text(encoding="utf-8")
            )
            self.assertEqual(client.events, ["preflight", "post"])
            self.assertEqual(len(client.calls), 1)
            self.assertEqual(result["status"], "campaign_incomplete")
            self.assertEqual(result["reason_code"], "canary_provider_routing_error")
            self.assertEqual(ledger["attempted_call_count"], 1)
            self.assertEqual(ledger["status_counts"], {"provider_routing_error": 1})
            self.assertFalse((root / "review").exists())

        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            client = _SyntheticProviderClient(
                preflight_status="compatible",
                response_status=200,
            )
            with mock.patch.object(
                final_wording_execution_v2,
                "_validate_live_campaign_paths",
                return_value=None,
            ):
                result = final_wording_execution_v2.run_campaign(
                    repo_root=REPO_ROOT,
                    protocol=self.protocol,
                    client=client,
                    output_dir=root / "private",
                    review_export_dir=root / "review",
                    execution_authorized=True,
                    evidence_source="main_model_provider",
                )
            self.assertEqual(result["status"], "human_rating_required")
            self.assertEqual(client.events[0], "preflight")
            self.assertEqual(client.events[1:], ["post"] * 24)
            self.assertEqual(len(client.calls), 24)

    def test_v21_v22_and_v23_history_is_pinned_and_cannot_be_reused(self) -> None:
        historical_path = (
            REPO_ROOT
            / "benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2_1.json"
        )
        self.assertEqual(
            final_wording_protocol_v2._sha256_file(historical_path),
            HISTORICAL_V21_FREEZE_SHA256,
        )
        historical_v22_path = (
            REPO_ROOT
            / "benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2_2.json"
        )
        self.assertEqual(
            final_wording_protocol_v2._sha256_file(historical_v22_path),
            HISTORICAL_V22_FREEZE_SHA256,
        )
        self.assertEqual(
            self.protocol["supersedes_protocol_version"],
            "lot4c4_final_wording_provider_campaign_v2_3",
        )
        self.assertEqual(
            self.protocol["v2_2_preflight_history"],
            {
                "metadata_get_count": 1,
                "metadata_http_status": 200,
                "endpoint_count": 5,
                "compatible_endpoint_count": 0,
                "provider_post_count": 0,
                "provider_inference_count": 0,
                "observed_cost_usd": 0.0,
                "campaign_started": False,
                "reusable": False,
            },
        )
        self.assertEqual(
            self.protocol["v2_1_campaign_history"],
            {
                "attempted_call_count": 36,
                "http_404_count": 36,
                "provider_inference_count": 0,
                "observed_cost_usd": 0.0,
                "ledger_conservative_cost_usd": 3.2567175,
                "ledger_conservative_cost_billed": False,
                "reusable": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
