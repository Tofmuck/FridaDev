from __future__ import annotations

import copy
import importlib.util
import sys
import types
import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

if importlib.util.find_spec("psycopg") is None:
    psycopg_module = types.ModuleType("psycopg")
    psycopg_rows_module = types.ModuleType("psycopg.rows")
    psycopg_rows_module.dict_row = object()
    psycopg_module.rows = psycopg_rows_module
    sys.modules.setdefault("psycopg", psycopg_module)
    sys.modules.setdefault("psycopg.rows", psycopg_rows_module)

from core.hermeneutic_node.validation import (
    hard_guards,
    validation_agent,
    validation_contract,
    validation_messages,
    validation_transport,
)


class _FakeResponse:
    def raise_for_status(self) -> None:
        return None


class _FakeRequests:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def post(self, url, *, json, headers, timeout):
        self.calls.append(
            {
                "url": url,
                "json": dict(json),
                "headers": dict(headers),
                "timeout": timeout,
            }
        )
        return _FakeResponse()


class _FakeLlm:
    def __init__(self) -> None:
        self.provider_logs: list[tuple[str, dict[str, object]]] = []

    def with_provider_attribution(self, payload, *, caller):
        attributed = dict(payload)
        attributed["metadata"] = {"frida_caller": caller}
        return attributed

    def or_chat_completions_url(self):
        return "https://provider.test/chat"

    def or_headers(self, *, caller):
        return {"Authorization": f"caller={caller}"}

    def read_openrouter_response_payload(self, _response):
        return {"choices": [{"message": {"content": "not-json"}}]}

    def extract_openrouter_provider_metadata(self, _payload, *, requested_model):
        return {"provider_model": requested_model, "provider_total_tokens": 3}

    def log_provider_metadata(self, _logger, event_name, provider_metadata):
        self.provider_logs.append((event_name, dict(provider_metadata)))

    def extract_openrouter_text(self, payload):
        return payload["choices"][0]["message"]["content"]


class ValidationAgentBoundaryTests(unittest.TestCase):
    def test_request_policy_builds_exact_primary_and_unchanged_fallback_payloads(self) -> None:
        llm_module = _FakeLlm()
        messages = [
            {"role": "system", "content": "SYSTEM SENTINEL"},
            {"role": "user", "content": "USER SENTINEL"},
        ]

        primary = validation_transport.prepare_validation_request(
            model="google/gemini-3.7-flash",
            decision_source="primary",
            messages=messages,
            timeout_s=15,
            temperature=0.0,
            top_p=1.0,
            max_tokens=500,
            reasoning_effort="medium",
            llm_module=llm_module,
        )
        fallback = validation_transport.prepare_validation_request(
            model=validation_agent.FALLBACK_MODEL,
            decision_source="fallback",
            messages=messages,
            timeout_s=15,
            temperature=0.0,
            top_p=1.0,
            max_tokens=500,
            reasoning_effort="medium",
            llm_module=llm_module,
        )
        legacy = validation_transport.prepare_validation_request(
            model=validation_transport.LEGACY_PRIMARY_MODEL,
            decision_source="primary",
            messages=messages,
            timeout_s=15,
            temperature=0.0,
            top_p=1.0,
            max_tokens=140,
            reasoning_effort="medium",
            llm_module=llm_module,
        )

        self.assertEqual(
            primary.payload["reasoning"],
            {"effort": "medium", "exclude": True},
        )
        self.assertEqual(primary.payload["max_tokens"], 500)
        self.assertEqual(
            primary.payload["provider"],
            {"allow_fallbacks": False, "require_parameters": True},
        )
        for forbidden in ("temperature", "top_p", "response_format", "service_tier"):
            self.assertNotIn(forbidden, primary.payload)
        self.assertEqual(primary.observability["validation_reasoning_effort_effective"], "medium")
        self.assertTrue(primary.observability["validation_reasoning_sent"])
        self.assertTrue(primary.observability["validation_reasoning_excluded"])
        self.assertFalse(primary.observability["validation_temperature_sent"])
        self.assertFalse(primary.observability["validation_top_p_sent"])
        self.assertTrue(primary.observability["validation_provider_routing_sent"])

        self.assertNotIn("reasoning", fallback.payload)
        self.assertEqual(fallback.payload["temperature"], 0.0)
        self.assertEqual(fallback.payload["top_p"], 1.0)
        self.assertEqual(fallback.payload["max_tokens"], 140)
        self.assertNotIn("provider", fallback.payload)
        self.assertFalse(fallback.observability["validation_reasoning_sent"])
        self.assertTrue(fallback.observability["validation_temperature_sent"])
        self.assertTrue(fallback.observability["validation_top_p_sent"])
        self.assertFalse(fallback.observability["validation_provider_routing_sent"])
        self.assertNotIn("validation_provider_fallbacks_allowed", fallback.observability)
        self.assertNotIn("validation_provider_require_parameters", fallback.observability)

        self.assertNotIn("provider", legacy.payload)
        self.assertFalse(legacy.observability["validation_provider_routing_sent"])
        self.assertNotIn("validation_provider_fallbacks_allowed", legacy.observability)
        self.assertNotIn("validation_provider_require_parameters", legacy.observability)

        for mutant in (
            dict(primary.observability, validation_reasoning_effort_effective="high"),
            dict(primary.observability, validation_temperature_sent=True),
            dict(fallback.observability, validation_reasoning_sent=True),
            dict(primary.observability, validation_provider_routing_sent=False),
            dict(fallback.observability, validation_provider_fallbacks_allowed=False),
        ):
            with self.assertRaises(ValueError):
                validation_transport.validate_request_observability(mutant)
        self.assertEqual(
            validation_transport.configured_primary_request_policy_version(
                primary_model=validation_transport.PRIMARY_MODEL,
                fallback_model=validation_transport.FALLBACK_MODEL,
                timeout_s=15,
                temperature=0.0,
                top_p=1.0,
                max_tokens=500,
                reasoning_effort="medium",
            ),
            validation_transport.PRIMARY_REQUEST_POLICY_VERSION,
        )
        self.assertEqual(
            validation_transport.configured_primary_request_policy_version(
                primary_model=validation_transport.PRIMARY_MODEL,
                fallback_model=validation_transport.FALLBACK_MODEL,
                timeout_s=15,
                temperature=0.1,
                top_p=1.0,
                max_tokens=500,
                reasoning_effort="medium",
            ),
            "unknown",
        )
        with self.assertRaisesRegex(ValueError, "invalid_validation_request_timeout"):
            validation_transport.prepare_validation_request(
                model=validation_transport.PRIMARY_MODEL,
                decision_source="primary",
                messages=messages,
                timeout_s=14,
                temperature=0.0,
                top_p=1.0,
                max_tokens=500,
                reasoning_effort="medium",
                llm_module=llm_module,
            )
        with self.assertRaisesRegex(ValueError, "invalid_validation_fallback_sampling_policy"):
            validation_transport.prepare_validation_request(
                model=validation_transport.FALLBACK_MODEL,
                decision_source="fallback",
                messages=messages,
                timeout_s=15,
                temperature=0.2,
                top_p=1.0,
                max_tokens=500,
                reasoning_effort="medium",
                llm_module=llm_module,
            )

    def test_pure_contract_accepts_valid_verdict_and_rejects_non_answer_presence(self) -> None:
        valid = {
            "schema_version": "v1",
            "final_judgment_posture": "answer",
            "final_output_regime": "presence",
            "arbiter_reason": "reception locale",
        }

        self.assertEqual(
            validation_contract.validate_model_verdict(valid),
            valid,
        )

        mutant = dict(valid)
        mutant["final_judgment_posture"] = "clarify"
        with self.assertRaises(validation_contract.ValidationPayloadError):
            validation_contract.validate_model_verdict(mutant)

    def test_normalized_agent_result_has_its_own_contract_boundary(self) -> None:
        normalized_output = validation_contract.build_validated_output_payload(
            primary_verdict={
                "upstream_advisory": {
                    "recommended_judgment_posture": "answer",
                    "proposed_output_regime": "simple",
                }
            },
            final_judgment_posture="answer",
            final_output_regime="simple",
            arbiter_reason="synthetic bounded reason",
            fail_open=False,
            applied_hard_guards=(),
        )
        result = validation_contract.ValidationAgentResult(
            validated_output=normalized_output,
            status="ok",
            model=validation_transport.PRIMARY_MODEL,
            decision_source="primary",
            provider_metadata={"provider_model": validation_transport.PRIMARY_MODEL},
        )

        self.assertIs(validation_contract.validate_agent_result(result), result)
        with self.assertRaises(validation_contract.ValidationPayloadError):
            validation_contract.validate_model_verdict(result.validated_output)
        caveated_result = validation_contract.ValidationAgentResult(
            validated_output=validation_contract.build_validated_output_payload(
                primary_verdict={},
                final_judgment_posture="answer",
                final_output_regime="simple",
                arbiter_reason="synthetic bounded caveat",
                fail_open=False,
                applied_hard_guards=("web_caveat_required",),
                hard_guard_effect=hard_guards.HARD_GUARD_EFFECT_CAVEAT_REQUIRED,
            ),
            status="ok",
            model=validation_transport.PRIMARY_MODEL,
            decision_source="primary",
        )
        self.assertIs(validation_contract.validate_agent_result(caveated_result), caveated_result)
        forbidden_answer = dict(caveated_result.validated_output)
        forbidden_answer["hard_guard_effect"] = (
            hard_guards.HARD_GUARD_EFFECT_ANSWER_FORBIDDEN
        )
        with self.assertRaises(validation_contract.ValidationPayloadError):
            validation_contract.validate_agent_result(
                validation_contract.ValidationAgentResult(
                    validated_output=forbidden_answer,
                    status="ok",
                    model=validation_transport.PRIMARY_MODEL,
                    decision_source="primary",
                )
            )
        raw_verdict = {
            "schema_version": "v1",
            "final_judgment_posture": "answer",
            "final_output_regime": "simple",
            "arbiter_reason": "synthetic bounded reason",
        }
        with self.assertRaises(validation_contract.ValidationPayloadError):
            validation_contract.validate_agent_result(
                validation_contract.ValidationAgentResult(
                    validated_output=raw_verdict,
                    status="ok",
                    model=validation_transport.PRIMARY_MODEL,
                    decision_source="primary",
                )
            )

    def test_message_builder_is_repeatable_bounded_and_does_not_mutate_inputs(self) -> None:
        primary_verdict = {"schema_version": "v1", "judgment_posture": "answer"}
        dialogue_context = {
            "schema_version": "v1",
            "messages": [{"role": "user", "content": "x" * 20000}],
        }
        canonical_inputs = {"support": {"content": "z" * 8000}}
        hard_guard_payload = {
            "allowed_postures": ["clarify", "suspend"],
            "applied_hard_guards": ["sentinel_guard"],
            "hard_guard_effect": "answer_forbidden",
        }
        originals = copy.deepcopy(
            (primary_verdict, dialogue_context, canonical_inputs, hard_guard_payload)
        )

        kwargs = {
            "system_prompt": "SYSTEM SENTINEL",
            "primary_verdict": primary_verdict,
            "justifications": {"support": "y" * 8000},
            "validation_dialogue_context": dialogue_context,
            "canonical_inputs": canonical_inputs,
            "hard_guard_payload": hard_guard_payload,
        }
        first = validation_messages.build_messages(**kwargs)
        second = validation_messages.build_messages(**kwargs)

        self.assertEqual(first, second)
        self.assertEqual(
            (primary_verdict, dialogue_context, canonical_inputs, hard_guard_payload),
            originals,
        )
        self.assertEqual(first[0], {"role": "system", "content": "SYSTEM SENTINEL"})
        self.assertLess(len(first[1]["content"]), 7800)
        self.assertLess(
            first[1]["content"].index("validation_dialogue_context"),
            first[1]["content"].index("primary_verdict"),
        )
        self.assertIn("sentinel_guard", first[1]["content"])

    def test_transport_posts_once_and_returns_raw_text_without_deciding_verdict(self) -> None:
        requests_module = _FakeRequests()
        llm_module = _FakeLlm()
        messages = [
            {"role": "system", "content": "SYSTEM SENTINEL"},
            {"role": "user", "content": "USER SENTINEL"},
        ]

        prepared = validation_transport.prepare_validation_request(
            model=validation_transport.PRIMARY_MODEL,
            decision_source="primary",
            messages=messages,
            timeout_s=15,
            temperature=0.0,
            top_p=1.0,
            max_tokens=500,
            reasoning_effort="medium",
            llm_module=llm_module,
        )
        result = validation_transport.request_provider_response(
            prepared_request=prepared,
            requests_module=requests_module,
            llm_module=llm_module,
            logger=object(),
        )

        self.assertEqual(result.text, "not-json")
        self.assertEqual(
            result.provider_metadata,
            {"provider_model": validation_transport.PRIMARY_MODEL, "provider_total_tokens": 3},
        )
        self.assertEqual(len(requests_module.calls), 1)
        self.assertEqual(requests_module.calls[0]["json"]["messages"], messages)
        self.assertEqual(requests_module.calls[0]["json"]["max_tokens"], 500)
        self.assertEqual(requests_module.calls[0]["timeout"], 15)
        self.assertEqual(
            llm_module.provider_logs,
            [
                (
                    "validation_agent_provider_response",
                    {"provider_model": validation_transport.PRIMARY_MODEL, "provider_total_tokens": 3},
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
