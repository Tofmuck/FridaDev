from __future__ import annotations

import json
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

from core.hermeneutic_node.inputs import recent_context_input as canonical_recent_context_input
from core.hermeneutic_node.validation import hard_guards, validation_agent


def _primary_verdict(
    *,
    judgment_posture: str = "answer",
    discursive_regime: str | None = None,
    epistemic_regime: str = "incertain",
    proof_regime: str = "source_explicite_requise",
    uncertainty_posture: str = "prudente",
    source_conflicts: list[dict[str, object]] | None = None,
    active_signal_families: list[str] | None = None,
) -> dict[str, object]:
    discursive_regime_value = discursive_regime or ("simple" if judgment_posture == "answer" else "meta")
    active_signal_families = list(active_signal_families or [])
    source_conflicts = list(source_conflicts or [])
    return {
        "schema_version": "v1",
        "epistemic_regime": epistemic_regime,
        "proof_regime": proof_regime,
        "uncertainty_posture": uncertainty_posture,
        "judgment_posture": judgment_posture,
        "discursive_regime": discursive_regime_value,
        "resituation_level": "none",
        "time_reference_mode": "atemporal",
        "source_priority": [
            ["tour_utilisateur"],
            ["temps"],
            ["memoire", "contexte_recent", "identity"],
        ],
        "source_conflicts": source_conflicts,
        "upstream_advisory": {
            "schema_version": "v1",
            "recommended_judgment_posture": judgment_posture,
            "proposed_output_regime": discursive_regime_value,
            "active_signal_families": active_signal_families,
            "active_signal_families_count": len(active_signal_families),
            "constraint_present": bool(source_conflicts),
        },
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


def _canonical_inputs(
    *,
    gesture: str = "interrogation",
    ambiguity_present: bool = False,
    underdetermination_present: bool = False,
    active_signal_families: list[str] | None = None,
    web_input: dict[str, object] | None = None,
) -> dict[str, object]:
    active_signal_families = list(active_signal_families or [])
    return {
        "user_turn_input": {"schema_version": "v1", "geste_dialogique_dominant": gesture},
        "user_turn_signals": {
            "present": bool(
                ambiguity_present
                or underdetermination_present
                or active_signal_families
            ),
            "ambiguity_present": ambiguity_present,
            "underdetermination_present": underdetermination_present,
            "active_signal_families": active_signal_families,
            "active_signal_families_count": len(active_signal_families),
        },
        "recent_context_input": {"schema_version": "v1", "messages": []},
        "web_input": dict(web_input or {}),
    }


def _web_input(
    *,
    status: str = "ok",
    results_count: int = 0,
    explicit_url_detected: bool = False,
    explicit_url: str | None = None,
    read_state: str | None = None,
    sources: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "status": status,
        "results_count": results_count,
        "explicit_url_detected": explicit_url_detected,
        "explicit_url": explicit_url,
        "read_state": read_state,
        "sources": list(sources or []),
    }


def _arbiter_json(
    *,
    final_judgment_posture: str,
    final_output_regime: str,
    arbiter_reason: str,
) -> str:
    return json.dumps(
        {
            "schema_version": "v1",
            "final_judgment_posture": final_judgment_posture,
            "final_output_regime": final_output_regime,
            "arbiter_reason": arbiter_reason,
        },
        ensure_ascii=True,
        separators=(",", ":"),
    )


def _expected_validated_output(
    *,
    validation_decision: str,
    final_judgment_posture: str,
    final_output_regime: str,
    arbiter_followed_upstream: bool,
    advisory_recommendations_followed: list[str],
    advisory_recommendations_overridden: list[str],
    arbiter_reason: str,
    fail_open: bool = False,
    applied_hard_guards: list[str] | None = None,
    hard_guard_effect: str | None = None,
) -> dict[str, object]:
    directives = [f"posture_{final_judgment_posture}", f"regime_{final_output_regime}"]
    if fail_open:
        directives.append("fallback_validation")
    payload = {
        "schema_version": "v1",
        "validation_decision": validation_decision,
        "final_judgment_posture": final_judgment_posture,
        "final_output_regime": final_output_regime,
        "pipeline_directives_final": directives,
        "arbiter_followed_upstream": arbiter_followed_upstream,
        "advisory_recommendations_followed": advisory_recommendations_followed,
        "advisory_recommendations_overridden": advisory_recommendations_overridden,
        "applied_hard_guards": list(applied_hard_guards or []),
        "arbiter_reason": arbiter_reason,
    }
    if hard_guard_effect:
        payload["hard_guard_effect"] = hard_guard_effect
    return payload


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
        return {
            "id": "gen-validation",
            "model": "openai/gpt-5.4-mini",
            "usage": {"prompt_tokens": 18, "completion_tokens": 4, "total_tokens": 22},
            "choices": [{"message": {"content": self._content}}],
        }


class ValidationAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_read_prompt = validation_agent.prompt_loader.read_prompt_text
        self.original_or_headers = validation_agent.llm_client.or_headers
        self.original_or_chat_completions_url = validation_agent.llm_client.or_chat_completions_url
        self.original_log_provider_metadata = validation_agent.llm_client.log_provider_metadata
        self.original_runtime_settings_getter = validation_agent.runtime_settings.get_validation_agent_model_settings
        self.provider_logs = []
        validation_agent.prompt_loader.read_prompt_text = lambda _path: "SYSTEM PROMPT"
        validation_agent.llm_client.or_headers = lambda caller="llm": {
            "Authorization": f"caller={caller}"
        }
        validation_agent.llm_client.or_chat_completions_url = lambda: "https://openrouter.example/chat/completions"
        validation_agent.llm_client.log_provider_metadata = lambda _logger, event_name, provider_metadata: self.provider_logs.append(
            (event_name, dict(provider_metadata))
        )
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
        validation_agent.llm_client.log_provider_metadata = self.original_log_provider_metadata
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

    def test_build_validated_output_returns_nominal_follow_result(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="answer",
                        final_output_regime="simple",
                        arbiter_reason="lecture locale suffisante",
                    )
                ),
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
            result.provider_metadata,
            {
                "provider_generation_id": "gen-validation",
                "provider_model": "openai/gpt-5.4-mini",
                "provider_prompt_tokens": 18,
                "provider_completion_tokens": 4,
                "provider_total_tokens": 22,
            },
        )
        self.assertEqual(
            result.validated_output,
            _expected_validated_output(
                validation_decision="confirm",
                final_judgment_posture="answer",
                final_output_regime="simple",
                arbiter_followed_upstream=True,
                advisory_recommendations_followed=[
                    "upstream_recommendation_posture",
                    "upstream_output_regime_proposed",
                ],
                advisory_recommendations_overridden=[],
                arbiter_reason="lecture locale suffisante",
            ),
        )
        self.assertEqual(
            requests_module.calls[0]["json"]["model"],
            validation_agent.PRIMARY_MODEL,
        )
        self.assertEqual(
            requests_module.calls[0]["headers"],
            {"Authorization": "caller=validation_agent"},
        )
        self.assertEqual(
            self.provider_logs,
            [
                (
                    "validation_agent_provider_response",
                    {
                        "provider_generation_id": "gen-validation",
                        "provider_model": "openai/gpt-5.4-mini",
                        "provider_prompt_tokens": 18,
                        "provider_completion_tokens": 4,
                        "provider_total_tokens": 22,
                    },
                )
            ],
        )

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
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="answer",
                        final_output_regime="simple",
                        arbiter_reason="lecture locale suffisante",
                    )
                ),
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

    def test_build_validated_output_clamps_runtime_settings_max_tokens_to_contractual_cap(self) -> None:
        validation_agent.runtime_settings.get_validation_agent_model_settings = lambda: types.SimpleNamespace(
            payload={
                "primary_model": {"value": "openai/custom-validation-primary"},
                "fallback_model": {"value": "openai/custom-validation-fallback"},
                "timeout_s": {"value": 14},
                "temperature": {"value": 0.2},
                "top_p": {"value": 0.88},
                "max_tokens": {"value": 2000},
            }
        )
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="answer",
                        final_output_regime="simple",
                        arbiter_reason="lecture locale suffisante",
                    )
                ),
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
        self.assertEqual(
            requests_module.calls[0]["json"]["max_tokens"],
            validation_agent.MAX_RESPONSE_TOKENS,
        )

    def test_build_validated_output_accepts_minimal_recent_context_like_dialogue_context(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="answer",
                        final_output_regime="simple",
                        arbiter_reason="tour direct peu ambigu",
                    )
                ),
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

    def test_build_validated_output_allows_arbiter_to_override_primary_clarify(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="answer",
                        final_output_regime="simple",
                        arbiter_reason="lecture dialogique locale suffisante",
                    )
                ),
            ]
        )

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(judgment_posture="clarify", discursive_regime="meta"),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(),
            requests_module=requests_module,
        )

        self.assertEqual(
            result.validated_output,
            _expected_validated_output(
                validation_decision="challenge",
                final_judgment_posture="answer",
                final_output_regime="simple",
                arbiter_followed_upstream=False,
                advisory_recommendations_followed=[],
                advisory_recommendations_overridden=[
                    "upstream_recommendation_posture",
                    "upstream_output_regime_proposed",
                ],
                arbiter_reason="lecture dialogique locale suffisante",
            ),
        )

    def test_build_validated_output_keeps_clarify_and_suspend_as_final_verdicts(self) -> None:
        clarify_requests = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="clarify",
                        final_output_regime="meta",
                        arbiter_reason="referent insuffisamment determine",
                    )
                ),
            ]
        )
        clarify_result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(judgment_posture="answer"),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(
                gesture="orientation",
                underdetermination_present=True,
                active_signal_families=["visee"],
            ),
            requests_module=clarify_requests,
        )
        self.assertEqual(
            clarify_result.validated_output,
            _expected_validated_output(
                validation_decision="clarify",
                final_judgment_posture="clarify",
                final_output_regime="meta",
                arbiter_followed_upstream=False,
                advisory_recommendations_followed=[],
                advisory_recommendations_overridden=[
                    "upstream_recommendation_posture",
                    "upstream_output_regime_proposed",
                ],
                arbiter_reason="referent insuffisamment determine",
            ),
        )

        suspend_requests = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="suspend",
                        final_output_regime="simple",
                        arbiter_reason="base admissible absente",
                    )
                ),
            ]
        )
        suspend_result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(judgment_posture="answer"),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(),
            requests_module=suspend_requests,
        )
        self.assertEqual(suspend_result.validated_output["validation_decision"], "suspend")
        self.assertEqual(suspend_result.validated_output["final_judgment_posture"], "suspend")
        self.assertEqual(suspend_result.validated_output["final_output_regime"], "simple")

    def test_build_validated_output_hard_guard_blocks_answer_for_explicit_url_not_read_without_forcing_meta(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="clarify",
                        final_output_regime="simple",
                        arbiter_reason="je peux cadrer sans pretendre avoir lu la page",
                    )
                ),
            ]
        )

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(
                web_input=_web_input(
                    status="ok",
                    results_count=1,
                    explicit_url_detected=True,
                    explicit_url="https://example.com/article",
                    read_state="page_not_read_snippet_fallback",
                    sources=[
                        {
                            "used_in_prompt": True,
                            "used_content_kind": "search_snippet",
                            "content_used": "resume court",
                        }
                    ],
                )
            ),
            requests_module=requests_module,
        )

        self.assertEqual(
            result.validated_output,
            _expected_validated_output(
                validation_decision="clarify",
                final_judgment_posture="clarify",
                final_output_regime="simple",
                arbiter_followed_upstream=False,
                advisory_recommendations_followed=["upstream_output_regime_proposed"],
                advisory_recommendations_overridden=["upstream_recommendation_posture"],
                arbiter_reason="je peux cadrer sans pretendre avoir lu la page",
                applied_hard_guards=[hard_guards.HARD_GUARD_EXPLICIT_URL_NOT_READ],
                hard_guard_effect=hard_guards.HARD_GUARD_EFFECT_ANSWER_FORBIDDEN,
            ),
        )

    def test_build_validated_output_hard_guard_blocks_answer_for_missing_external_verification_with_suspend_choice(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="suspend",
                        final_output_regime="simple",
                        arbiter_reason="verification actuelle indisponible",
                    )
                ),
            ]
        )

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(
                epistemic_regime="a_verifier",
                proof_regime="verification_externe_requise",
                uncertainty_posture="explicite",
            ),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(
                web_input=_web_input(status="skipped", results_count=0, sources=[]),
            ),
            requests_module=requests_module,
        )

        self.assertEqual(
            result.validated_output,
            _expected_validated_output(
                validation_decision="suspend",
                final_judgment_posture="suspend",
                final_output_regime="simple",
                arbiter_followed_upstream=False,
                advisory_recommendations_followed=["upstream_output_regime_proposed"],
                advisory_recommendations_overridden=["upstream_recommendation_posture"],
                arbiter_reason="verification actuelle indisponible",
                applied_hard_guards=[hard_guards.HARD_GUARD_EXTERNAL_VERIFICATION_MISSING],
                hard_guard_effect=hard_guards.HARD_GUARD_EFFECT_ANSWER_FORBIDDEN,
            ),
        )

    def test_build_validated_output_retries_when_primary_answer_violates_hard_guard(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="answer",
                        final_output_regime="simple",
                        arbiter_reason="je reponds quand meme",
                    )
                ),
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="clarify",
                        final_output_regime="simple",
                        arbiter_reason="je peux cadrer sans pretendre verifier",
                    )
                ),
            ]
        )

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(
                epistemic_regime="a_verifier",
                proof_regime="verification_externe_requise",
                uncertainty_posture="explicite",
            ),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(
                web_input=_web_input(status="skipped", results_count=0, sources=[]),
            ),
            requests_module=requests_module,
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.decision_source, "fallback")
        self.assertEqual(result.model, validation_agent.FALLBACK_MODEL)
        self.assertEqual(
            result.validated_output["applied_hard_guards"],
            [hard_guards.HARD_GUARD_EXTERNAL_VERIFICATION_MISSING],
        )
        self.assertIn(
            "hard_guards (contraintes deterministes non cassables):",
            requests_module.calls[0]["json"]["messages"][1]["content"],
        )
        self.assertIn(
            '"allowed_postures":["clarify","suspend"]',
            requests_module.calls[0]["json"]["messages"][1]["content"],
        )
        self.assertIn(
            hard_guards.HARD_GUARD_EXTERNAL_VERIFICATION_MISSING,
            requests_module.calls[0]["json"]["messages"][1]["content"],
        )

    def test_build_validated_output_keeps_source_conflict_case_arbitrable_without_hard_guard(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="answer",
                        final_output_regime="simple",
                        arbiter_reason="la lecture locale suffit malgre l ancrage concurrent",
                    )
                ),
            ]
        )

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(
                judgment_posture="clarify",
                discursive_regime="meta",
                source_conflicts=[
                    {
                        "conflict_type": "conflit_d_ancrage_de_source",
                        "sources": ["memoire", "web"],
                        "issue": "review_required",
                    }
                ],
                active_signal_families=["ancrage_de_source"],
            ),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(
                active_signal_families=["ancrage_de_source"],
                web_input=_web_input(
                    status="ok",
                    results_count=1,
                    sources=[
                        {
                            "used_in_prompt": True,
                            "used_content_kind": "crawl_markdown",
                            "content_used": "matiere externe lue",
                        }
                    ],
                ),
            ),
            requests_module=requests_module,
        )

        self.assertEqual(result.validated_output["final_judgment_posture"], "answer")
        self.assertEqual(result.validated_output["final_output_regime"], "simple")
        self.assertEqual(result.validated_output["applied_hard_guards"], [])
        self.assertNotIn("hard_guard_effect", result.validated_output)
        self.assertEqual(
            result.validated_output["advisory_recommendations_overridden"],
            ["upstream_recommendation_posture", "upstream_output_regime_proposed"],
        )

    def test_build_validated_output_preserves_arbiter_clarify_for_low_ambiguity_direct_identity_revelation(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="clarify",
                        final_output_regime="meta",
                        arbiter_reason="cadrage supplementaire",
                    )
                ),
            ]
        )

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(judgment_posture="answer"),
            justifications={},
            validation_dialogue_context={
                "schema_version": "v1",
                "messages": [{"role": "user", "content": "Je suis Christophe Muck"}],
            },
            canonical_inputs=_canonical_inputs(
                gesture="exposition",
                ambiguity_present=False,
                underdetermination_present=False,
                active_signal_families=[],
            ),
            requests_module=requests_module,
        )

        self.assertEqual(result.validated_output["validation_decision"], "clarify")
        self.assertEqual(result.validated_output["final_judgment_posture"], "clarify")
        self.assertEqual(result.validated_output["final_output_regime"], "meta")
        self.assertFalse(result.validated_output["arbiter_followed_upstream"])
        self.assertEqual(
            result.validated_output["advisory_recommendations_overridden"],
            ["upstream_recommendation_posture", "upstream_output_regime_proposed"],
        )
        self.assertEqual(result.validated_output["applied_hard_guards"], [])
        self.assertEqual(result.validated_output["arbiter_reason"], "cadrage supplementaire")

    def test_build_validated_output_preserves_arbiter_clarify_for_low_ambiguity_interrogation(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="clarify",
                        final_output_regime="meta",
                        arbiter_reason="cadrage supplementaire",
                    )
                ),
            ]
        )

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(judgment_posture="answer"),
            justifications={},
            validation_dialogue_context={
                "schema_version": "v1",
                "messages": [{"role": "user", "content": "T'as vu l'heure ?"}],
            },
            canonical_inputs=_canonical_inputs(
                gesture="interrogation",
                ambiguity_present=False,
                underdetermination_present=False,
                active_signal_families=[],
            ),
            requests_module=requests_module,
        )

        self.assertEqual(result.validated_output["validation_decision"], "clarify")
        self.assertEqual(result.validated_output["final_judgment_posture"], "clarify")
        self.assertEqual(result.validated_output["final_output_regime"], "meta")
        self.assertFalse(result.validated_output["arbiter_followed_upstream"])
        self.assertEqual(result.validated_output["applied_hard_guards"], [])
        self.assertEqual(result.validated_output["arbiter_reason"], "cadrage supplementaire")

    def test_build_validated_output_keeps_clarify_when_real_cadrage_signal_exists(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="clarify",
                        final_output_regime="meta",
                        arbiter_reason="referent introuvable sans contexte resolutif",
                    )
                ),
            ]
        )

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(judgment_posture="answer"),
            justifications={},
            validation_dialogue_context={
                "schema_version": "v1",
                "messages": [{"role": "user", "content": "Corrige ça"}],
            },
            canonical_inputs=_canonical_inputs(
                gesture="orientation",
                ambiguity_present=True,
                active_signal_families=["referent"],
            ),
            requests_module=requests_module,
        )

        self.assertEqual(result.validated_output["validation_decision"], "clarify")
        self.assertEqual(result.validated_output["final_judgment_posture"], "clarify")

    def test_build_validated_output_keeps_clarify_for_ambiguous_interrogation(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="clarify",
                        final_output_regime="meta",
                        arbiter_reason="referent encore ambigu",
                    )
                ),
            ]
        )

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(judgment_posture="answer"),
            justifications={},
            validation_dialogue_context={
                "schema_version": "v1",
                "messages": [{"role": "user", "content": "Et ca, t'en penses quoi ?"}],
            },
            canonical_inputs=_canonical_inputs(
                gesture="interrogation",
                ambiguity_present=True,
                active_signal_families=["referent"],
            ),
            requests_module=requests_module,
        )

        self.assertEqual(result.validated_output["validation_decision"], "clarify")
        self.assertEqual(result.validated_output["final_judgment_posture"], "clarify")

    def test_validated_validation_dialogue_context_keeps_local_five_message_window(self) -> None:
        payload = validation_agent._validated_validation_dialogue_context(
            {
                "schema_version": "v1",
                "messages": [
                    {"role": "assistant", "content": "Assistant 0", "timestamp": "2026-04-02T09:00:00Z"},
                    {"role": "user", "content": "User 1", "timestamp": "2026-04-02T09:01:00Z"},
                    {"role": "assistant", "content": "Assistant 1", "timestamp": "2026-04-02T09:02:00Z"},
                    {"role": "user", "content": "User 2", "timestamp": "2026-04-02T09:03:00Z"},
                    {"role": "assistant", "content": "Assistant 2", "timestamp": "2026-04-02T09:04:00Z"},
                    {"role": "user", "content": "User 3", "timestamp": "2026-04-02T09:05:00Z"},
                    {"role": "assistant", "content": "Assistant 3", "timestamp": "2026-04-02T09:06:00Z"},
                    {"role": "user", "content": "User current", "timestamp": "2026-04-02T09:07:00Z"},
                ],
            }
        )

        self.assertEqual(payload["schema_version"], "v1")
        self.assertEqual(payload["source_message_count"], 8)
        self.assertTrue(payload["truncated"])
        self.assertTrue(payload["current_user_retained"])
        self.assertTrue(payload["last_assistant_retained"])
        self.assertEqual(
            payload["messages"],
            [
                {"role": "user", "content": "User 2", "timestamp": "2026-04-02T09:03:00Z"},
                {"role": "assistant", "content": "Assistant 2", "timestamp": "2026-04-02T09:04:00Z"},
                {"role": "user", "content": "User 3", "timestamp": "2026-04-02T09:05:00Z"},
                {"role": "assistant", "content": "Assistant 3", "timestamp": "2026-04-02T09:06:00Z"},
                {"role": "user", "content": "User current", "timestamp": "2026-04-02T09:07:00Z"},
            ],
        )
        self.assertEqual(
            len(payload["messages"]),
            canonical_recent_context_input.VALIDATION_DIALOGUE_CONTEXT_MAX_MESSAGES,
        )

    def test_build_validated_output_uses_fallback_model_after_primary_invalid_json(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse("not json"),
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="answer",
                        final_output_regime="simple",
                        arbiter_reason="fallback arbiter conservateur",
                    )
                ),
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
            _expected_validated_output(
                validation_decision="suspend",
                final_judgment_posture="suspend",
                final_output_regime="simple",
                arbiter_followed_upstream=False,
                advisory_recommendations_followed=["upstream_output_regime_proposed"],
                advisory_recommendations_overridden=["upstream_recommendation_posture"],
                arbiter_reason="validation fail-open (invalid_json)",
                fail_open=True,
            ),
        )

    def test_build_validated_output_centers_prompt_on_validation_dialogue_context(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="answer",
                        final_output_regime="simple",
                        arbiter_reason="lecture locale suffisante",
                    )
                ),
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
            "validation_dialogue_context (matiere hermeneutique principale, fenetre dialogique locale canonisee):",
            user_message,
        )
        self.assertIn("Je veux une reponse mais le contexte recent reste fragile.", user_message)
        self.assertIn("primary_verdict (recommendation structuree amont, secondaire et non terminale):", user_message)
        self.assertIn("justifications (support secondaire frere, hors primary_verdict):", user_message)
        self.assertIn("canonical_inputs (supports secondaires de relecture contextuelle):", user_message)
        self.assertLess(
            user_message.index("validation_dialogue_context"),
            user_message.index("primary_verdict"),
        )
        self.assertIn('"final_judgment_posture":"answer|clarify|suspend"', user_message)
        self.assertIn('"final_output_regime":"simple|meta"', user_message)
        self.assertIn('"arbiter_reason":"raison_courte_lisible"', user_message)
        self.assertNotIn("validation_decision", user_message.split("schema attendu: ", 1)[1])

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
            hard_guard_payload={},
        )

        user_message = messages[1]["content"]
        self.assertLess(len(user_message), 7800)
        self.assertIn("validation_dialogue_context (matiere hermeneutique principale, fenetre dialogique locale canonisee):", user_message)
        self.assertIn('"message_count":1', user_message)
        self.assertIn('"truncated":true', user_message)
        self.assertIn("primary_verdict (recommendation structuree amont, secondaire et non terminale):", user_message)
        self.assertIn("justifications (support secondaire frere, hors primary_verdict):", user_message)
        self.assertIn("canonical_inputs (supports secondaires de relecture contextuelle):", user_message)
        self.assertLess(user_message.index("validation_dialogue_context"), user_message.index("primary_verdict"))


if __name__ == "__main__":
    unittest.main()
