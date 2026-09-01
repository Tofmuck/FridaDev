from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from benchmark.core import openrouter
from benchmark.suites.stimmung import final_wording_protocol_v2 as protocol_v24
from benchmark.suites.stimmung import final_wording_gpt52_v25 as campaign_v25


REPO_ROOT = Path(__file__).resolve().parents[4]
FREEZE_COMMIT = "f" * 40


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

    def test_dry_run_is_offline_and_frozen(self) -> None:
        summary = campaign_v25.dry_run(REPO_ROOT, freeze_commit=FREEZE_COMMIT)
        self.assertEqual(summary["status"], "ready_offline")
        self.assertEqual(summary["decision"], "provider_campaign_required")
        self.assertEqual(summary["model"], "openai/gpt-5.2")
        self.assertEqual(summary["expected_call_count"], 24)
        self.assertEqual(summary["absolute_cost_cap_usd"], 4.0)


if __name__ == "__main__":
    unittest.main()
