from __future__ import annotations

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

from core.hermeneutic_node.validation import validation_agent


def _primary_verdict(
    *,
    judgment_posture: str = "answer",
    source_conflicts: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "epistemic_regime": "incertain",
        "proof_regime": "source_explicite_requise",
        "uncertainty_posture": "prudente",
        "judgment_posture": judgment_posture,
        "discursive_regime": "simple" if judgment_posture == "answer" else "meta",
        "resituation_level": "none",
        "time_reference_mode": "atemporal",
        "source_priority": [
            ["tour_utilisateur"],
            ["temps"],
            ["memoire", "contexte_recent", "identity"],
        ],
        "source_conflicts": list(source_conflicts or []),
        "pipeline_directives_provisional": [f"posture_{judgment_posture}"],
        "audit": {
            "fail_open": False,
            "state_used": False,
            "degraded_fields": [],
        },
    }


def _dialogue_context() -> dict[str, object]:
    return {
        "schema_version": "v1",
        "messages": [
            {
                "role": "user",
                "content": "Je veux une reponse mais le contexte recent reste fragile.",
                "timestamp": "2026-04-02T10:00:00Z",
            },
            {
                "role": "assistant",
                "content": "Je t'entends, je relis le fil recent.",
                "timestamp": "2026-04-02T10:01:00Z",
            },
        ],
    }


def _canonical_inputs() -> dict[str, object]:
    return {
        "user_turn_input": {"schema_version": "v1", "geste_dialogique_dominant": "interrogation"},
        "recent_context_input": {"schema_version": "v1", "messages": []},
    }


class _FakeRequests:
    class exceptions:
        class RequestException(Exception):
            pass

        class Timeout(RequestException):
            pass

    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.calls: list[dict[str, object]] = []

    def post(self, url, json, headers, timeout):
        self.calls.append(
            {
                "url": url,
                "json": dict(json),
                "headers": dict(headers),
                "timeout": timeout,
            }
        )
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _FakeResponse:
    def __init__(self, content: str, *, error: Exception | None = None) -> None:
        self._content = content
        self._error = error

    def raise_for_status(self) -> None:
        if self._error is not None:
            raise self._error

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


class ValidationAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_read_prompt = validation_agent.prompt_loader.read_prompt_text
        self.original_or_headers = validation_agent.llm_client.or_headers
        self.original_or_chat_completions_url = validation_agent.llm_client.or_chat_completions_url
        self.original_runtime_settings_getter = validation_agent.runtime_settings.get_validation_agent_model_settings
        validation_agent.prompt_loader.read_prompt_text = lambda _path: "SYSTEM PROMPT"
        validation_agent.llm_client.or_headers = lambda caller="llm": {
            "Authorization": f"caller={caller}"
        }
        validation_agent.llm_client.or_chat_completions_url = lambda: "https://openrouter.example/chat/completions"
        validation_agent.runtime_settings.get_validation_agent_model_settings = lambda: types.SimpleNamespace(
            payload={
                "primary_model": {"value": validation_agent.PRIMARY_MODEL},
                "fallback_model": {"value": validation_agent.FALLBACK_MODEL},
                "timeout_s": {"value": 10},
                "temperature": {"value": 0.0},
                "top_p": {"value": 1.0},
                "max_tokens": {"value": 80},
            }
        )

    def tearDown(self) -> None:
        validation_agent.prompt_loader.read_prompt_text = self.original_read_prompt
        validation_agent.llm_client.or_headers = self.original_or_headers
        validation_agent.llm_client.or_chat_completions_url = self.original_or_chat_completions_url
        validation_agent.runtime_settings.get_validation_agent_model_settings = self.original_runtime_settings_getter

    def test_build_validated_output_rejects_invalid_primary_verdict(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_primary_verdict"):
            validation_agent.build_validated_output(
                primary_verdict={"judgment_posture": "answer"},
                justifications={},
                validation_dialogue_context=_dialogue_context(),
                canonical_inputs={},
            )

    def test_build_validated_output_rejects_invalid_validation_dialogue_context(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_validation_dialogue_context"):
            validation_agent.build_validated_output(
                primary_verdict=_primary_verdict(),
                justifications={},
                validation_dialogue_context={},
                canonical_inputs={},
            )

    def test_build_validated_output_rejects_validation_dialogue_context_with_schema_only(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_validation_dialogue_context"):
            validation_agent.build_validated_output(
                primary_verdict=_primary_verdict(),
                justifications={},
                validation_dialogue_context={"schema_version": "v1"},
                canonical_inputs={},
            )

    def test_build_validated_output_rejects_arbitrary_validation_dialogue_context_mapping(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_validation_dialogue_context"):
            validation_agent.build_validated_output(
                primary_verdict=_primary_verdict(),
                justifications={},
                validation_dialogue_context={"foo": "bar"},
                canonical_inputs={},
            )

    def test_build_validated_output_rejects_non_mapping_justifications(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_justifications"):
            validation_agent.build_validated_output(
                primary_verdict=_primary_verdict(),
                justifications=[],
                validation_dialogue_context=_dialogue_context(),
                canonical_inputs={},
            )

    def test_build_validated_output_rejects_non_mapping_canonical_inputs(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_canonical_inputs"):
            validation_agent.build_validated_output(
                primary_verdict=_primary_verdict(),
                justifications={},
                validation_dialogue_context=_dialogue_context(),
                canonical_inputs=[],
            )

    def test_build_validated_output_returns_nominal_confirm_result(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse('{"schema_version":"v1","validation_decision":"confirm"}'),
            ]
        )

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(),
            requests_module=requests_module,
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.decision_source, "primary")
        self.assertEqual(result.model, validation_agent.PRIMARY_MODEL)
        self.assertIsNone(result.reason_code)
        self.assertEqual(
            result.validated_output,
            {
                "schema_version": "v1",
                "validation_decision": "confirm",
                "final_judgment_posture": "answer",
                "pipeline_directives_final": ["posture_answer"],
            },
        )
        self.assertEqual(
            requests_module.calls[0]["json"]["model"],
            validation_agent.PRIMARY_MODEL,
        )
        self.assertEqual(
            requests_module.calls[0]["headers"],
            {"Authorization": "caller=validation_agent"},
        )
        self.assertNotIn("primary_verdict", result.validated_output)
        self.assertNotIn("validation_dialogue_context", result.validated_output)
        self.assertNotIn("justifications", result.validated_output)

    def test_build_validated_output_uses_runtime_settings_models_and_sampling(self) -> None:
        validation_agent.runtime_settings.get_validation_agent_model_settings = lambda: types.SimpleNamespace(
            payload={
                "primary_model": {"value": "openai/custom-validation-primary"},
                "fallback_model": {"value": "openai/custom-validation-fallback"},
                "timeout_s": {"value": 14},
                "temperature": {"value": 0.2},
                "top_p": {"value": 0.88},
                "max_tokens": {"value": 64},
            }
        )
        requests_module = _FakeRequests(
            [
                _FakeResponse('{"schema_version":"v1","validation_decision":"confirm"}'),
            ]
        )

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(),
            requests_module=requests_module,
        )

        self.assertEqual(result.model, "openai/custom-validation-primary")
        self.assertEqual(requests_module.calls[0]["json"]["model"], "openai/custom-validation-primary")
        self.assertEqual(requests_module.calls[0]["json"]["temperature"], 0.2)
        self.assertEqual(requests_module.calls[0]["json"]["top_p"], 0.88)
        self.assertEqual(requests_module.calls[0]["json"]["max_tokens"], 64)
        self.assertEqual(requests_module.calls[0]["timeout"], 14)
        self.assertEqual(
            requests_module.calls[0]["headers"],
            {"Authorization": "caller=validation_agent"},
        )

    def test_build_validated_output_accepts_minimal_recent_context_like_dialogue_context(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse('{"schema_version":"v1","validation_decision":"confirm"}'),
            ]
        )

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(),
            justifications={},
            validation_dialogue_context={
                "schema_version": "v1",
                "messages": [{"role": "user", "content": "Bonjour"}],
            },
            canonical_inputs={},
            requests_module=requests_module,
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.validated_output["validation_decision"], "confirm")
        self.assertEqual(result.validated_output["final_judgment_posture"], "answer")

    def test_build_validated_output_keeps_answer_after_challenge(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse('{"schema_version":"v1","validation_decision":"challenge"}'),
            ]
        )

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(judgment_posture="answer"),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(),
            requests_module=requests_module,
        )

        self.assertEqual(result.validated_output["validation_decision"], "challenge")
        self.assertEqual(result.validated_output["final_judgment_posture"], "answer")
        self.assertEqual(result.validated_output["pipeline_directives_final"], ["posture_answer"])

    def test_build_validated_output_maps_clarify_and_suspend_locally(self) -> None:
        clarify_requests = _FakeRequests(
            [
                _FakeResponse('{"schema_version":"v1","validation_decision":"clarify"}'),
            ]
        )
        clarify_result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(judgment_posture="answer"),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(),
            requests_module=clarify_requests,
        )
        self.assertEqual(clarify_result.validated_output["final_judgment_posture"], "clarify")
        self.assertEqual(clarify_result.validated_output["pipeline_directives_final"], ["posture_clarify"])

        suspend_requests = _FakeRequests(
            [
                _FakeResponse('{"schema_version":"v1","validation_decision":"suspend"}'),
            ]
        )
        suspend_result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(judgment_posture="answer"),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(),
            requests_module=suspend_requests,
        )
        self.assertEqual(suspend_result.validated_output["final_judgment_posture"], "suspend")
        self.assertEqual(suspend_result.validated_output["pipeline_directives_final"], ["posture_suspend"])

    def test_build_validated_output_uses_fallback_model_after_primary_invalid_json(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse("not json"),
                _FakeResponse('{"schema_version":"v1","validation_decision":"confirm"}'),
            ]
        )

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(),
            requests_module=requests_module,
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.decision_source, "fallback")
        self.assertEqual(result.model, validation_agent.FALLBACK_MODEL)
        self.assertEqual(
            [call["json"]["model"] for call in requests_module.calls],
            [validation_agent.PRIMARY_MODEL, validation_agent.FALLBACK_MODEL],
        )
        self.assertEqual(result.validated_output["validation_decision"], "confirm")

    def test_build_validated_output_returns_fail_open_after_double_failure(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeRequests.exceptions.Timeout("primary timeout"),
                _FakeResponse("not json"),
            ]
        )

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(),
            requests_module=requests_module,
        )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.decision_source, "fail_open")
        self.assertEqual(result.model, validation_agent.FALLBACK_MODEL)
        self.assertEqual(result.reason_code, "invalid_json")
        self.assertEqual(
            result.validated_output,
            {
                "schema_version": "v1",
                "validation_decision": "suspend",
                "final_judgment_posture": "suspend",
                "pipeline_directives_final": ["posture_suspend", "fallback_validation"],
            },
        )

    def test_build_validated_output_centers_prompt_on_validation_dialogue_context(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse('{"schema_version":"v1","validation_decision":"confirm"}'),
            ]
        )

        validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(),
            justifications={"summary": "support sibling artefact"},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(),
            requests_module=requests_module,
        )

        user_message = requests_module.calls[0]["json"]["messages"][1]["content"]
        self.assertIn(
            "validation_dialogue_context (matiere hermeneutique principale de la relecture):",
            user_message,
        )
        self.assertIn("Je veux une reponse mais le contexte recent reste fragile.", user_message)
        self.assertIn("primary_verdict (support structure amont, non terminal):", user_message)
        self.assertLess(
            user_message.index("validation_dialogue_context"),
            user_message.index("primary_verdict"),
        )
        self.assertIn(
            '{"schema_version":"v1","validation_decision":"confirm|challenge|clarify|suspend"}',
            user_message,
        )

    def test_build_messages_bounds_large_validation_inputs(self) -> None:
        large_context = {
            "schema_version": "v1",
            "messages": [
                {
                    "role": "user",
                    "content": "x" * 20000,
                    "timestamp": "2026-04-02T10:00:00Z",
                }
            ],
        }
        large_justifications = {"analysis": "y" * 8000}
        large_canonical_inputs = {"recent_context_input": {"messages": ["z" * 8000]}}

        messages = validation_agent._build_messages(
            system_prompt="SYSTEM PROMPT",
            primary_verdict=_primary_verdict(),
            justifications=large_justifications,
            validation_dialogue_context=large_context,
            canonical_inputs=large_canonical_inputs,
        )

        user_message = messages[1]["content"]
        self.assertLess(len(user_message), 7800)
        self.assertIn("validation_dialogue_context (matiere hermeneutique principale de la relecture):", user_message)
        self.assertIn('"message_count":1', user_message)
        self.assertIn('"truncated":true', user_message)
        self.assertIn("primary_verdict (support structure amont, non terminal):", user_message)
        self.assertIn("justifications (artefact frere, hors primary_verdict):", user_message)
        self.assertIn("canonical_inputs (supports de relecture contextuelle):", user_message)
        self.assertLess(user_message.index("validation_dialogue_context"), user_message.index("primary_verdict"))


if __name__ == "__main__":
    unittest.main()
