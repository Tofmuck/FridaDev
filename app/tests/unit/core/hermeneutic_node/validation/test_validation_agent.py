from __future__ import annotations

import json
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
REPO_ROOT = APP_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if importlib.util.find_spec("psycopg") is None:
    psycopg_module = types.ModuleType("psycopg")
    psycopg_rows_module = types.ModuleType("psycopg.rows")
    psycopg_rows_module.dict_row = object()
    psycopg_module.rows = psycopg_rows_module
    sys.modules.setdefault("psycopg", psycopg_module)
    sys.modules.setdefault("psycopg.rows", psycopg_rows_module)

from core.hermeneutic_node.inputs import recent_context_input as canonical_recent_context_input
from core.hermeneutic_node.inputs import time_input as canonical_time_input
from core.hermeneutic_node.inputs import user_turn_input as canonical_user_turn_input
from core.hermeneutic_node.inputs import web_input as canonical_web_input
from core.hermeneutic_node.validation import (
    hard_guards,
    validation_agent,
    validation_contract,
    validation_messages,
)
from benchmark.suites.validation_agent import lot4c1_comparison


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


def _accepted_3712_counterexample_to_old_maximum_claim() -> dict[str, object]:
    code = "x" * 64
    families = {
        "memory_retrieved": {
            "schema_version": "v1", "status": code, "reason_code": code,
            "error_code": code, "retrieved_count": 999999,
            "parent_summary_count": 999999,
        },
        "memory_arbitration": {
            "schema_version": "v1", "status": code, "reason_code": code,
            "raw_candidates_count": 999999, "kept_count": 999999,
            "rejected_count": 999999, "injected_count": 999999,
        },
        "summary_input": {
            "schema_version": "v1", "status": code, "reason_code": code,
            "error_code": code, "summary_present": True,
            "start_ts": code, "end_ts": code,
        },
        "identity_input": {
            "schema_version": "v2", "status": code, "reason_code": code,
            "error_code": code,
            "frida": {"static_present": True, "mutable_present": True},
            "user": {"static_present": True, "mutable_present": True},
        },
        "user_turn_input": {
            "schema_version": "v1",
            "geste_dialogique_dominant": "adresse_relationnelle",
            "regime_probatoire": {
                "principe": "maximal_possible",
                "types_de_preuve_attendus": [
                    "factuelle", "scientifique", "argumentative",
                    "hermeneutique", "dialogique",
                ],
                "provenances": ["dialogue_trace", "dialogue_resume", "web"],
                "regime_de_vigilance": "renforce",
                "composition_probatoire": "appuyee",
            },
            "qualification_temporelle": {
                "portee_temporelle": "prospective",
                "ancrage_temporel": "historique_externe",
            },
        },
        "user_turn_signals": {
            "present": True, "ambiguity_present": True,
            "underdetermination_present": True,
            "active_signal_families": [
                "referent", "visee", "critere", "portee",
                "ancrage_de_source", "coherence",
            ],
            "active_signal_families_count": 6,
        },
        "stimmung_input": {
            "schema_version": "v1", "present": True,
            "dominant_tone": "decouragement",
            "active_tones": [
                {"tone": "decouragement", "strength": 10},
                {"tone": "enthousiasme", "strength": 10},
                {"tone": "frustration", "strength": 10},
            ],
            "stability": "volatile", "shift_state": "candidate_shift",
            "turns_considered": 4,
        },
        "web_input": {
            "schema_version": "v1", "enabled": True, "status": code,
            "activation_mode": "not_requested", "reason_code": code,
            "results_count": 999999, "read_state": code,
            "fallback_used": True, "web_confidence_level": code,
            "web_evidence_status": code, "web_evidence_can_answer": True,
            "web_evidence_requires_caveat": True,
            "web_evidence_can_suggest_reformulation": True,
            "web_evidence_external_fallback_used": True,
            "openrouter_fallback_used": True,
        },
    }
    dispositions = {
        family: (
            "redundant_elsewhere"
            if family in {"time_input", "recent_context_input", "recent_window_input"}
            else "included"
        )
        for family in validation_messages.CANONICAL_FAMILY_ORDER
    }
    return {
        "projection_version": "validation_canonical_inputs_v2",
        "stimmung_delivery": {"status": "full", "reason_code": "included"},
        "family_dispositions": dispositions,
        "families": families,
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
    web_evidence: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": status,
        "results_count": results_count,
        "explicit_url_detected": explicit_url_detected,
        "explicit_url": explicit_url,
        "read_state": read_state,
        "sources": list(sources or []),
    }
    if web_evidence is not None:
        payload["web_evidence"] = dict(web_evidence)
    return payload


def _web_evidence(
    *,
    can_answer: bool,
    requires_caveat: bool = True,
    status: str = "partial",
    reason_codes: list[str] | None = None,
) -> dict[str, object]:
    return {
        "web_evidence_policy_kind": "local_web_evidence_failure_contract_v0",
        "web_evidence_status": status,
        "web_evidence_reason_codes": list(reason_codes or ["snippet_only_material"]),
        "web_evidence_guidance_codes": [
            "state_evidence_limits_naturally",
            "can_answer_with_caveat",
            "no_external_fallback",
        ],
        "web_evidence_can_answer": can_answer,
        "web_evidence_requires_caveat": requires_caveat,
        "web_evidence_can_suggest_reformulation": requires_caveat,
        "web_evidence_url_request_policy": "only_if_relevant_not_default",
        "web_evidence_external_fallback_used": False,
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
            "model": validation_agent.PRIMARY_MODEL,
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
        self.original_chat_turn_emit = validation_agent.chat_turn_logger.emit
        self.provider_logs = []
        self.observed_events: list[dict[str, object]] = []
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
                "max_tokens": {"value": validation_agent.MAX_RESPONSE_TOKENS},
            }
        )

        def fake_emit(
            stage,
            *,
            status="ok",
            payload=None,
            duration_ms=None,
            model=None,
            prompt_kind=None,
            reason_code=None,
            error_code=None,
        ):
            self.observed_events.append(
                {
                    "stage": stage,
                    "status": status,
                    "payload": dict(payload or {}),
                    "duration_ms": duration_ms,
                    "model": model,
                    "prompt_kind": prompt_kind,
                    "reason_code": reason_code,
                    "error_code": error_code,
                }
            )
            return True

        validation_agent.chat_turn_logger.emit = fake_emit

    def tearDown(self) -> None:
        validation_agent.prompt_loader.read_prompt_text = self.original_read_prompt
        validation_agent.llm_client.or_headers = self.original_or_headers
        validation_agent.llm_client.or_chat_completions_url = self.original_or_chat_completions_url
        validation_agent.llm_client.log_provider_metadata = self.original_log_provider_metadata
        validation_agent.runtime_settings.get_validation_agent_model_settings = self.original_runtime_settings_getter
        validation_agent.chat_turn_logger.emit = self.original_chat_turn_emit

    def test_missing_prompt_keeps_fail_open_contract_without_provider(self) -> None:
        validation_agent.prompt_loader.read_prompt_text = lambda _path: ''
        requests_module = _FakeRequests([])

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(),
            requests_module=requests_module,
        )

        self.assertEqual(result.status, 'error')
        self.assertEqual(result.decision_source, 'fail_open')
        self.assertEqual(result.reason_code, 'prompt_missing')
        self.assertEqual(requests_module.calls, [])

    def test_build_validated_output_rejects_invalid_primary_verdict(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_primary_verdict"):
            validation_agent.build_validated_output(
                primary_verdict={"judgment_posture": "answer"},
                justifications={},
                validation_dialogue_context=_dialogue_context(),
                canonical_inputs={},
            )

    def test_build_validated_output_accepts_primary_fail_open_compact_cause(self) -> None:
        primary_verdict = _primary_verdict(
            judgment_posture="suspend",
            discursive_regime="meta",
            epistemic_regime="suspendu",
            proof_regime="source_explicite_requise",
            uncertainty_posture="bloquante",
        )
        primary_verdict["pipeline_directives_provisional"] = [
            "posture_suspend",
            "fallback_primary_verdict",
        ]
        primary_verdict["audit"] = {
            "fail_open": True,
            "state_used": False,
            "degraded_fields": ["epistemic_regime"],
            "fallback_used": True,
            "fallback_source": "primary_node",
            "node_stage": "primary_node",
            "reason_code": "runtime_error",
            "error_class": "RuntimeError",
        }

        result = validation_agent.build_validated_output(
            primary_verdict=primary_verdict,
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(),
            requests_module=_FakeRequests(
                [
                    _FakeResponse(
                        _arbiter_json(
                            final_judgment_posture="suspend",
                            final_output_regime="simple",
                            arbiter_reason="fallback primaire garde en suspension",
                        )
                    )
                ]
            ),
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.validated_output["final_judgment_posture"], "suspend")

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
                "provider_model": validation_agent.PRIMARY_MODEL,
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
        self.assertEqual(requests_module.calls[0]["json"]["metadata"]["frida_caller"], "validation_agent")
        self.assertEqual(requests_module.calls[0]["json"]["metadata"]["frida_slot"], "validation_agent_model")
        self.assertEqual(requests_module.calls[0]["json"]["trace"]["trace_name"], "FridaDev")
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
                        "provider_model": validation_agent.PRIMARY_MODEL,
                        "provider_prompt_tokens": 18,
                        "provider_completion_tokens": 4,
                        "provider_total_tokens": 22,
                    },
                )
            ],
        )

    def test_build_validated_output_accepts_positive_presence_as_answer_output_regime(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="answer",
                        final_output_regime="presence",
                        arbiter_reason="reception locale sans poursuite",
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
        self.assertEqual(len(requests_module.calls), 1)
        self.assertEqual(
            result.validated_output,
            _expected_validated_output(
                validation_decision="challenge",
                final_judgment_posture="answer",
                final_output_regime="presence",
                arbiter_followed_upstream=False,
                advisory_recommendations_followed=[
                    "upstream_recommendation_posture",
                ],
                advisory_recommendations_overridden=[
                    "upstream_output_regime_proposed",
                ],
                arbiter_reason="reception locale sans poursuite",
            ),
        )

    def test_build_messages_carries_triadic_reading_without_new_output_fields(self) -> None:
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
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(),
            requests_module=requests_module,
        )

        user_message = requests_module.calls[0]["json"]["messages"][1]["content"]
        self.assertIn("Warum / Wofür / Wozu", user_message)
        self.assertIn("dernier enonce et le dialogue comme texte", user_message)
        self.assertIn("sans checklist ni sortie dediee", user_message)

        schema_tail = user_message.split("schema attendu: ", 1)[1].lower()
        for forbidden_key in ("warum", "wofuer", "wozu", "interpretive_center", "triad"):
            self.assertNotIn(forbidden_key, schema_tail)

    def test_build_messages_enforces_dialogic_meaning_independence_and_presence_boundary(self) -> None:
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
            primary_verdict=_primary_verdict(judgment_posture="clarify", discursive_regime="meta"),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(
                ambiguity_present=True,
                active_signal_families=["referent"],
            ),
            requests_module=requests_module,
        )

        user_message = requests_module.calls[0]["json"]["messages"][1]["content"]
        for snippet in (
            "presume que le tour a un sens dans l'histoire locale du dialogue",
            "premisses implicites comme hypotheses interpretatives",
            "distingue comprendre la proposition",
            "ni l'insistance, ni le desaccord reformule, ni l'intensite affective",
            "ne choisis clarify qu'apres l'echec d'une interpretation coherente",
            "un signal lexical, une ponctuation ou une recommandation amont",
            "final_output_regime = presence",
            "trois points ASCII",
            "ne le choisis jamais pour une question, une demande, une detresse, un risque",
            "suspend conserve exclusivement son sens epistemique",
            '"final_output_regime":"simple|meta|presence"',
        ):
            self.assertIn(snippet, user_message)

    def test_model_verdict_rejects_triadic_output_fields(self) -> None:
        base_payload = {
            "schema_version": "v1",
            "final_judgment_posture": "answer",
            "final_output_regime": "simple",
            "arbiter_reason": "lecture locale suffisante",
        }

        for forbidden_key in ("warum", "wofuer", "wozu", "interpretive_center", "triad"):
            with self.subTest(forbidden_key=forbidden_key):
                payload = dict(base_payload)
                payload[forbidden_key] = "champ interdit"
                with self.assertRaises(validation_agent._ValidationPayloadError):
                    validation_agent._validated_model_verdict(payload)

    def test_model_verdict_rejects_unknown_regime_and_non_answer_presence(self) -> None:
        with self.assertRaises(validation_agent._ValidationPayloadError):
            validation_agent._validated_model_verdict(
                {
                    "schema_version": "v1",
                    "final_judgment_posture": "answer",
                    "final_output_regime": "unknown",
                    "arbiter_reason": "regime inconnu",
                }
            )

        for posture in ("clarify", "suspend"):
            with self.subTest(posture=posture):
                with self.assertRaises(validation_agent._ValidationPayloadError):
                    validation_agent._validated_model_verdict(
                        {
                            "schema_version": "v1",
                            "final_judgment_posture": posture,
                            "final_output_regime": "presence",
                            "arbiter_reason": "couplage interdit",
                        }
                    )

    def test_validation_prompt_prepared_observes_memory_exposure_without_raw_content(self) -> None:
        raw_trace = "RAW TRACE MEMORY SHOULD NEVER APPEAR IN LOGS"
        raw_summary = "RAW PARENT SUMMARY SHOULD NEVER APPEAR IN LOGS"
        raw_basket = "RAW BASKET CANDIDATE SHOULD NEVER APPEAR IN LOGS"
        raw_reason = "RAW ARBITER REASON SHOULD NEVER APPEAR IN LOGS"
        canonical_inputs = _canonical_inputs()
        canonical_inputs["memory_retrieved"] = {
            "schema_version": "v1",
            "status": "ok",
            "top_k_requested": 5,
            "retrieved_count": 2,
            "traces": [
                {
                    "candidate_id": "cand-trace-1",
                    "source_kind": "trace",
                    "source_lane": "dense",
                    "role": "user",
                    "content": raw_trace,
                    "parent_summary": {"content": raw_summary},
                },
                {
                    "candidate_id": "summary:abc",
                    "source_kind": "summary",
                    "source_lane": "summaries",
                    "role": "summary",
                    "content": "RAW SUMMARY CANDIDATE SHOULD NEVER APPEAR IN LOGS",
                },
            ],
        }
        canonical_inputs["memory_arbitration"] = {
            "schema_version": "v1",
            "status": "available",
            "raw_candidates_count": 2,
            "basket_candidates_count": 1,
            "basket_candidates": [
                {
                    "candidate_id": "cand-trace-1",
                    "source_kind": "trace",
                    "source_lane": "dense",
                    "content": raw_basket,
                }
            ],
            "decisions_count": 1,
            "kept_count": 1,
            "rejected_count": 0,
            "injected_candidate_ids": ["cand-trace-1"],
            "decisions": [
                {
                    "candidate_id": "cand-trace-1",
                    "keep": True,
                    "decision_source": "llm",
                    "reason": raw_reason,
                }
            ],
        }
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
            canonical_inputs=canonical_inputs,
            requests_module=requests_module,
        )

        self.assertEqual(result.status, "ok")
        event = next(item for item in self.observed_events if item["stage"] == "validation_prompt_prepared")
        self.assertEqual(event["model"], validation_agent.PRIMARY_MODEL)
        self.assertEqual(event["prompt_kind"], "validation_agent_secondary")
        payload = event["payload"]
        self.assertEqual(payload["payload_kind"], "secondary_validation_agent_provider")
        self.assertFalse(payload["main_llm_payload"])
        self.assertTrue(payload["secondary_provider_payload"])
        self.assertEqual(payload["validation_status"], "prepared")
        self.assertEqual(payload["attempt_decision_source"], "primary")
        self.assertTrue(payload["memory_retrieved"]["present"])
        self.assertEqual(payload["memory_retrieved"]["retrieved_count"], 2)
        self.assertEqual(payload["memory_retrieved"]["source_kind_counts"], {"summary": 1, "trace": 1})
        self.assertEqual(payload["memory_retrieved"]["source_lane_counts"], {"dense": 1, "summaries": 1})
        self.assertEqual(payload["memory_retrieved"]["parent_summary_present_count"], 1)
        self.assertEqual(payload["memory_retrieved"]["candidate_ids_count"], 2)
        self.assertTrue(payload["memory_arbitration"]["present"])
        self.assertEqual(payload["memory_arbitration"]["basket_candidates_count"], 1)
        self.assertEqual(payload["memory_arbitration"]["decisions_count"], 1)
        self.assertEqual(payload["memory_arbitration"]["kept_count"], 1)
        self.assertEqual(payload["memory_arbitration"]["decision_source_counts"], {"llm": 1})
        self.assertEqual(payload["memory_arbitration"]["injected_candidate_ids_count"], 1)
        self.assertGreater(payload["canonical_inputs"]["json_chars"], 0)

        event_json = json.dumps(event, ensure_ascii=False, sort_keys=True)
        self.assertNotIn(raw_trace, event_json)
        self.assertNotIn(raw_summary, event_json)
        self.assertNotIn(raw_basket, event_json)
        self.assertNotIn(raw_reason, event_json)
        self.assertNotIn("RAW SUMMARY CANDIDATE SHOULD NEVER APPEAR IN LOGS", event_json)
        self.assertNotIn('"content"', event_json)
        self.assertNotIn('"messages"', event_json)
        self.assertNotIn("SYSTEM PROMPT", event_json)

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
        self.assertEqual(requests_module.calls[0]["json"]["metadata"]["frida_caller"], "validation_agent")
        self.assertEqual(requests_module.calls[0]["json"]["metadata"]["frida_slot"], "validation_agent_model")
        self.assertEqual(requests_module.calls[0]["timeout"], 14)

    def test_fail_open_without_hard_guard_does_not_project_suspend(self) -> None:
        requests_module = _FakeRequests([
            _FakeResponse("not-json"),
            _FakeResponse("not-json"),
        ])

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(),
            requests_module=requests_module,
        )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.decision_source, "fail_open")
        self.assertEqual(result.reason_code, "invalid_json")
        self.assertEqual(result.validated_output, {})
        self.assertNotEqual(result.validated_output.get("final_output_regime"), "presence")

    def test_fail_open_with_answer_forbidden_hard_guard_keeps_suspend(self) -> None:
        requests_module = _FakeRequests([
            _FakeResponse("not-json"),
            _FakeResponse("not-json"),
        ])

        result = validation_agent.build_validated_output(
            primary_verdict=_primary_verdict(),
            justifications={},
            validation_dialogue_context=_dialogue_context(),
            canonical_inputs=_canonical_inputs(
                web_input=_web_input(
                    status="ok",
                    explicit_url_detected=True,
                    explicit_url="https://example.test/source",
                    read_state="page_not_read_error",
                )
            ),
            requests_module=requests_module,
        )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.decision_source, "fail_open")
        self.assertEqual(result.validated_output["final_judgment_posture"], "suspend")
        self.assertEqual(result.validated_output["final_output_regime"], "simple")
        self.assertNotEqual(result.validated_output["final_output_regime"], "presence")
        self.assertIn("explicit_url_not_read", result.validated_output["applied_hard_guards"])

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

    def test_lot6_acceptance_corpus_stays_stable_answer_clarify_suspend_cases(self) -> None:
        cases = [
            {
                "name": "everyday_answer_follow",
                "primary_verdict": _primary_verdict(),
                "canonical_inputs": _canonical_inputs(),
                "response": _arbiter_json(
                    final_judgment_posture="answer",
                    final_output_regime="simple",
                    arbiter_reason="lecture locale suffisante",
                ),
                "expected": _expected_validated_output(
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
            },
            {
                "name": "override_upstream_clarify_to_answer_simple",
                "primary_verdict": _primary_verdict(judgment_posture="clarify", discursive_regime="meta"),
                "canonical_inputs": _canonical_inputs(),
                "response": _arbiter_json(
                    final_judgment_posture="answer",
                    final_output_regime="simple",
                    arbiter_reason="lecture dialogique locale suffisante",
                ),
                "expected": _expected_validated_output(
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
            },
            {
                "name": "follow_real_clarify",
                "primary_verdict": _primary_verdict(
                    judgment_posture="clarify",
                    discursive_regime="meta",
                    active_signal_families=["referent"],
                ),
                "canonical_inputs": _canonical_inputs(
                    gesture="orientation",
                    ambiguity_present=True,
                    active_signal_families=["referent"],
                ),
                "response": _arbiter_json(
                    final_judgment_posture="clarify",
                    final_output_regime="meta",
                    arbiter_reason="referent insuffisamment determine",
                ),
                "expected": _expected_validated_output(
                    validation_decision="clarify",
                    final_judgment_posture="clarify",
                    final_output_regime="meta",
                    arbiter_followed_upstream=True,
                    advisory_recommendations_followed=[
                        "upstream_recommendation_posture",
                        "upstream_output_regime_proposed",
                    ],
                    advisory_recommendations_overridden=[],
                    arbiter_reason="referent insuffisamment determine",
                ),
            },
            {
                "name": "phase7_explicit_url_not_read_allows_answer_with_caveat",
                "primary_verdict": _primary_verdict(),
                "canonical_inputs": _canonical_inputs(
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
                        web_evidence=_web_evidence(
                            can_answer=True,
                            requires_caveat=True,
                            reason_codes=["explicit_url_not_read_snippet_fallback"],
                        ),
                    )
                ),
                "response": _arbiter_json(
                    final_judgment_posture="answer",
                    final_output_regime="simple",
                    arbiter_reason="je peux cadrer sans pretendre avoir lu la page",
                ),
                "expected": _expected_validated_output(
                    validation_decision="confirm",
                    final_judgment_posture="answer",
                    final_output_regime="simple",
                    arbiter_followed_upstream=True,
                    advisory_recommendations_followed=[
                        "upstream_recommendation_posture",
                        "upstream_output_regime_proposed",
                    ],
                    advisory_recommendations_overridden=[],
                    arbiter_reason="je peux cadrer sans pretendre avoir lu la page",
                    applied_hard_guards=[hard_guards.HARD_GUARD_EXPLICIT_URL_NOT_READ],
                    hard_guard_effect=hard_guards.HARD_GUARD_EFFECT_CAVEAT_REQUIRED,
                ),
            },
            {
                "name": "hard_guard_suspend_blocks_answer",
                "primary_verdict": _primary_verdict(
                    epistemic_regime="a_verifier",
                    proof_regime="verification_externe_requise",
                    uncertainty_posture="explicite",
                ),
                "canonical_inputs": _canonical_inputs(
                    web_input=_web_input(status="skipped", results_count=0, sources=[]),
                ),
                "response": _arbiter_json(
                    final_judgment_posture="suspend",
                    final_output_regime="simple",
                    arbiter_reason="verification actuelle indisponible",
                ),
                "expected": _expected_validated_output(
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
            },
            {
                "name": "source_conflict_case_remains_arbitrable",
                "primary_verdict": _primary_verdict(
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
                "canonical_inputs": _canonical_inputs(
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
                "response": _arbiter_json(
                    final_judgment_posture="answer",
                    final_output_regime="simple",
                    arbiter_reason="la lecture locale suffit malgre l ancrage concurrent",
                ),
                "expected": _expected_validated_output(
                    validation_decision="challenge",
                    final_judgment_posture="answer",
                    final_output_regime="simple",
                    arbiter_followed_upstream=False,
                    advisory_recommendations_followed=[],
                    advisory_recommendations_overridden=[
                        "upstream_recommendation_posture",
                        "upstream_output_regime_proposed",
                    ],
                    arbiter_reason="la lecture locale suffit malgre l ancrage concurrent",
                ),
            },
        ]

        for case in cases:
            with self.subTest(case=case["name"]):
                requests_module = _FakeRequests([_FakeResponse(case["response"])])
                result = validation_agent.build_validated_output(
                    primary_verdict=case["primary_verdict"],
                    justifications={},
                    validation_dialogue_context=_dialogue_context(),
                    canonical_inputs=case["canonical_inputs"],
                    requests_module=requests_module,
                )

                self.assertEqual(result.status, "ok")
                self.assertEqual(result.decision_source, "primary")
                self.assertEqual(result.model, validation_agent.PRIMARY_MODEL)
                self.assertEqual(result.validated_output, case["expected"])

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

    def test_build_validated_output_phase7_allows_answer_for_explicit_url_not_read_with_caveat(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="answer",
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
                        web_evidence=_web_evidence(
                            can_answer=True,
                            requires_caveat=True,
                            reason_codes=["explicit_url_not_read_snippet_fallback"],
                        ),
                    )
                ),
            requests_module=requests_module,
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
                arbiter_reason="je peux cadrer sans pretendre avoir lu la page",
                applied_hard_guards=[hard_guards.HARD_GUARD_EXPLICIT_URL_NOT_READ],
                hard_guard_effect=hard_guards.HARD_GUARD_EFFECT_CAVEAT_REQUIRED,
            ),
        )
        self.assertIn(
            '"allowed_postures":["answer","clarify","suspend"]',
            requests_module.calls[0]["json"]["messages"][1]["content"],
        )
        self.assertIn(
            '"hard_guard_effect":"caveat_required"',
            requests_module.calls[0]["json"]["messages"][1]["content"],
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

    def test_build_validated_output_phase7_allows_answer_when_web_evidence_can_answer(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="answer",
                        final_output_regime="simple",
                        arbiter_reason="preuve partielle formulee prudemment",
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
                web_input=_web_input(
                    status="skipped",
                    results_count=0,
                    sources=[],
                    web_evidence=_web_evidence(
                        can_answer=True,
                        requires_caveat=True,
                        status="insufficient",
                        reason_codes=["no_results"],
                    ),
                ),
            ),
            requests_module=requests_module,
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.decision_source, "primary")
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
                arbiter_reason="preuve partielle formulee prudemment",
                applied_hard_guards=[hard_guards.HARD_GUARD_EXTERNAL_VERIFICATION_MISSING],
                hard_guard_effect=hard_guards.HARD_GUARD_EFFECT_CAVEAT_REQUIRED,
            ),
        )
        self.assertIn(
            '"allowed_postures":["answer","clarify","suspend"]',
            requests_module.calls[0]["json"]["messages"][1]["content"],
        )
        self.assertIn(
            '"hard_guard_effect":"caveat_required"',
            requests_module.calls[0]["json"]["messages"][1]["content"],
        )

    def test_build_validated_output_retries_when_presence_violates_hard_guard(self) -> None:
        requests_module = _FakeRequests(
            [
                _FakeResponse(
                    _arbiter_json(
                        final_judgment_posture="answer",
                        final_output_regime="presence",
                        arbiter_reason="je masque la limite par une presence",
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
        self.assertEqual(result.validated_output, {})
        prompt_events = [
            item for item in self.observed_events if item["stage"] == "validation_prompt_prepared"
        ]
        self.assertEqual(len(prompt_events), 2)
        self.assertEqual(
            [item["payload"]["attempt_decision_source"] for item in prompt_events],
            ["primary", "fallback"],
        )
        self.assertEqual(
            [item["model"] for item in prompt_events],
            [validation_agent.PRIMARY_MODEL, validation_agent.FALLBACK_MODEL],
        )
        self.assertEqual(
            [item["payload"]["canonical_projection_version"] for item in prompt_events],
            ["validation_canonical_inputs_v2", "validation_canonical_inputs_v2"],
        )
        self.assertEqual(
            [item["payload"]["stimmung_delivery_status"] for item in prompt_events],
            ["absent", "absent"],
        )
        self.assertEqual(
            [item["payload"]["stimmung_delivery_reason_code"] for item in prompt_events],
            ["signal_not_present", "signal_not_present"],
        )
        events_json = json.dumps(prompt_events, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("primary timeout", events_json)
        self.assertNotIn("not json", events_json)
        self.assertNotIn("SYSTEM PROMPT", events_json)

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
        self.assertIn('"final_output_regime":"simple|meta|presence"', user_message)
        self.assertIn('"arbiter_reason":"raison_courte_lisible"', user_message)
        self.assertNotIn("validation_decision", user_message.split("schema attendu: ", 1)[1])

    def test_build_messages_puts_local_temporal_reference_before_validation_context(self) -> None:
        messages = validation_agent._build_messages(
            system_prompt="SYSTEM PROMPT",
            primary_verdict=_primary_verdict(),
            justifications={},
            validation_dialogue_context={
                "schema_version": "v1",
                "messages": [
                    {
                        "role": "assistant",
                        "content": "Message juste avant minuit local.",
                        "timestamp": "2026-05-17T21:00:00Z",
                    },
                    {
                        "role": "user",
                        "content": "Message courant juste apres minuit local.",
                        "timestamp": "2026-05-17T22:05:00Z",
                    },
                ],
            },
            canonical_inputs={
                "time_input": canonical_time_input.build_time_input(
                    now_utc_iso="2026-05-17T22:05:00Z",
                    timezone_name="Europe/Paris",
                ),
            },
            hard_guard_payload={},
        )

        user_message = messages[1]["content"]
        self.assertLess(user_message.index("temporal_reference"), user_message.index("validation_dialogue_context"))
        self.assertIn('"local_date":"2026-05-18"', user_message)
        self.assertIn('"timezone":"Europe/Paris"', user_message)
        self.assertIn("dimanche 17 mai 2026 à 23h Europe/Paris — hier", user_message)
        self.assertIn("lundi 18 mai 2026 à 0h05 Europe/Paris — à l'instant", user_message)

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

    def test_canonical_projection_is_whole_bounded_repeatable_and_rejects_partial_metadata(self) -> None:
        stimmung = {
            "schema_version": "v1",
            "present": True,
            "dominant_tone": "apaisement",
            "active_tones": [{"tone": "apaisement", "strength": 7}],
            "stability": "stable",
            "shift_state": "steady",
            "turns_considered": 4,
        }
        canonical_inputs = {
            "recent_context_input": {
                "schema_version": "v1",
                "messages": [{"role": "user", "content": "x" * 8000}],
            },
            "stimmung_input": stimmung,
            "user_turn_input": canonical_user_turn_input.build_user_turn_input(
                user_message="synthetic statement",
            ),
        }

        material, metadata = validation_messages.project_validation_canonical_inputs(canonical_inputs)
        rebuilt_material, rebuilt_metadata = validation_messages.project_validation_canonical_inputs(
            dict(reversed(list(canonical_inputs.items())))
        )
        projection = json.loads(material)

        self.assertEqual(material, rebuilt_material)
        self.assertEqual(metadata, rebuilt_metadata)
        self.assertLessEqual(len(material), validation_messages.MAX_CANONICAL_INPUTS_JSON_CHARS)
        self.assertEqual(projection["families"]["stimmung_input"], stimmung)
        self.assertEqual(projection["stimmung_delivery"], {"status": "full", "reason_code": "included"})
        self.assertNotIn("recent_context_input", projection["families"])
        self.assertEqual(
            projection["family_dispositions"]["recent_context_input"],
            "redundant_elsewhere",
        )
        self.assertNotIn("preview", projection)
        self.assertNotIn("truncated", projection)

        maximal_stimmung = {
            **stimmung,
            "dominant_tone": "decouragement",
            "active_tones": [
                {"tone": "decouragement", "strength": 10},
                {"tone": "enthousiasme", "strength": 10},
                {"tone": "neutralite", "strength": 10},
            ],
            "stability": "volatile",
            "shift_state": "candidate_shift",
        }
        crowded_inputs = {
            family: {"synthetic_chars": "x" * 8000}
            for family in validation_messages.CANONICAL_FAMILY_ORDER
            if family != "stimmung_input"
        }
        crowded_inputs["stimmung_input"] = maximal_stimmung
        maximal_material, _maximal_metadata = validation_messages.project_validation_canonical_inputs(
            crowded_inputs
        )
        maximal_projection = json.loads(maximal_material)
        self.assertEqual(maximal_projection["families"]["stimmung_input"], maximal_stimmung)
        self.assertLessEqual(
            len(maximal_material),
            validation_messages.MAX_CANONICAL_INPUTS_JSON_CHARS,
        )

        missing_material, missing_metadata = validation_messages.project_validation_canonical_inputs({})
        missing = json.loads(missing_material)
        self.assertEqual(
            missing["stimmung_delivery"],
            {"status": "absent", "reason_code": "signal_not_present"},
        )
        self.assertEqual(missing_metadata["stimmung_delivery_status"], "absent")

        invalid_material, _invalid_metadata = validation_messages.project_validation_canonical_inputs(
            {"stimmung_input": {key: value for key, value in stimmung.items() if key != "shift_state"}}
        )
        invalid = json.loads(invalid_material)
        self.assertEqual(
            invalid["stimmung_delivery"],
            {"status": "absent", "reason_code": "invalid_signal"},
        )
        self.assertNotIn("stimmung_input", invalid["families"])

        partial_mutant = dict(metadata, stimmung_delivery_status="partial")
        with self.assertRaisesRegex(ValueError, "invalid_stimmung_delivery_status"):
            validation_contract.validate_canonical_projection_metadata(partial_mutant)
        counter_mutant = dict(
            metadata,
            canonical_projection_chars=validation_messages.MAX_CANONICAL_INPUTS_JSON_CHARS + 1,
        )
        with self.assertRaisesRegex(ValueError, "invalid_canonical_projection_budget"):
            validation_contract.validate_canonical_projection_metadata(counter_mutant)

    def test_canonical_projection_v2_keeps_required_matter_and_classifies_every_family(self) -> None:
        canonical_inputs = {
            "time_input": canonical_time_input.build_time_input(
                now_utc_iso="2026-08-28T09:00:00Z",
                timezone_name="UTC",
            ),
            "memory_retrieved": {
                "schema_version": "v1",
                "status": "ok",
                "reason_code": None,
                "error_code": None,
                "error_class": None,
                "retrieval_query": "SYNTHETIC_QUERY_NOT_PROJECTED",
                "top_k_requested": 5,
                "retrieved_count": 1,
                "traces": [{"content": "SYNTHETIC_MEMORY_NOT_PROJECTED"}],
            },
            "memory_arbitration": {
                "schema_version": "v1",
                "status": "available",
                "reason_code": None,
                "raw_candidates_count": 1,
                "basket_candidates_count": 1,
                "basket_limit": 8,
                "basket_candidates": [{"content": "SYNTHETIC_BASKET_NOT_PROJECTED"}],
                "decisions_count": 1,
                "kept_count": 1,
                "rejected_count": 0,
                "injected_candidate_ids": ["synthetic-candidate"],
                "decisions": [{"reason": "SYNTHETIC_REASON_NOT_PROJECTED"}],
            },
            "summary_input": {
                "schema_version": "v1",
                "status": "missing",
                "summary": None,
            },
            "identity_input": {
                "schema_version": "v2",
                "status": "available",
                "frida": {
                    "static": {"content": "SYNTHETIC_IDENTITY_NOT_PROJECTED", "source": "resource"},
                    "mutable": {
                        "content": "SYNTHETIC_MUTABLE_NOT_PROJECTED",
                        "source_trace_id": None,
                        "updated_by": "identity_periodic_agent",
                        "update_reason": "periodic_agent",
                        "updated_ts": "2026-08-28T08:00:00Z",
                    },
                },
                "user": {
                    "static": {"content": "", "source": None},
                    "mutable": {
                        "content": "",
                        "source_trace_id": None,
                        "updated_by": None,
                        "update_reason": None,
                        "updated_ts": None,
                    },
                },
            },
            "recent_context_input": {
                "schema_version": "v1",
                "messages": [{"role": "user", "content": "SYNTHETIC_DIALOGUE_NOT_PROJECTED"}],
            },
            "recent_window_input": {
                "schema_version": "v1",
                "max_recent_turns": 5,
                "turn_count": 1,
                "has_in_progress_turn": True,
                "turns": [{"messages": [{"content": "SYNTHETIC_WINDOW_NOT_PROJECTED"}]}],
            },
            "user_turn_input": {
                "schema_version": "v1",
                "geste_dialogique_dominant": "interrogation",
                "regime_probatoire": {
                    "principe": "maximal_possible",
                    "types_de_preuve_attendus": ["factuelle"],
                    "provenances": ["web"],
                    "regime_de_vigilance": "renforce",
                    "composition_probatoire": "appuyee",
                },
                "qualification_temporelle": {
                    "portee_temporelle": "actuelle",
                    "ancrage_temporel": "now",
                },
            },
            "user_turn_signals": {
                "present": True,
                "ambiguity_present": False,
                "underdetermination_present": True,
                "active_signal_families": ["visee"],
                "active_signal_families_count": 1,
            },
            "stimmung_input": {
                "schema_version": "v1",
                "present": True,
                "dominant_tone": "curiosite",
                "active_tones": [{"tone": "curiosite", "strength": 6}],
                "stability": "stable",
                "shift_state": "steady",
                "turns_considered": 4,
            },
            "web_input": canonical_web_input.build_web_input(
                enabled=False,
                status="skipped",
                activation_mode="not_requested",
                reason_code="not_applicable",
            ),
        }

        material, metadata = validation_messages.project_validation_canonical_inputs(
            canonical_inputs
        )
        rebuilt, rebuilt_metadata = validation_messages.project_validation_canonical_inputs(
            dict(reversed(list(canonical_inputs.items())))
        )
        projection = json.loads(material)

        self.assertEqual(material, rebuilt)
        self.assertEqual(metadata, rebuilt_metadata)
        self.assertEqual(
            projection["projection_version"],
            "validation_canonical_inputs_v2",
        )
        self.assertEqual(validation_messages.MAX_CANONICAL_INPUTS_JSON_CHARS, 3840)
        self.assertLessEqual(len(material), 3840)
        self.assertEqual(
            projection["family_dispositions"],
            {
                "time_input": "redundant_elsewhere",
                "memory_retrieved": "included",
                "memory_arbitration": "included",
                "summary_input": "no_data",
                "identity_input": "included",
                "recent_context_input": "redundant_elsewhere",
                "recent_window_input": "redundant_elsewhere",
                "user_turn_input": "included",
                "user_turn_signals": "included",
                "stimmung_input": "included",
                "web_input": "optional_not_requested",
            },
        )
        self.assertEqual(
            list(projection["families"]),
            [
                "memory_retrieved",
                "memory_arbitration",
                "identity_input",
                "user_turn_input",
                "user_turn_signals",
                "stimmung_input",
            ],
        )
        serialized = json.dumps(projection, sort_keys=True)
        for raw_sentinel in (
            "SYNTHETIC_QUERY_NOT_PROJECTED",
            "SYNTHETIC_MEMORY_NOT_PROJECTED",
            "SYNTHETIC_BASKET_NOT_PROJECTED",
            "SYNTHETIC_REASON_NOT_PROJECTED",
            "SYNTHETIC_IDENTITY_NOT_PROJECTED",
            "SYNTHETIC_MUTABLE_NOT_PROJECTED",
            "SYNTHETIC_DIALOGUE_NOT_PROJECTED",
            "SYNTHETIC_WINDOW_NOT_PROJECTED",
        ):
            self.assertNotIn(raw_sentinel, serialized)
        self.assertEqual(
            metadata["canonical_projection_redundant_families"],
            ["time_input", "recent_context_input", "recent_window_input"],
        )
        self.assertEqual(
            metadata["canonical_projection_optional_families"],
            ["web_input"],
        )
        self.assertEqual(
            metadata["canonical_projection_no_data_families"],
            ["summary_input"],
        )

        raw_family_mutant = json.loads(material)
        raw_family_mutant["families"]["memory_retrieved"] = canonical_inputs[
            "memory_retrieved"
        ]
        with self.assertRaisesRegex(ValueError, "invalid_canonical_projection_family"):
            validation_messages.validate_validation_canonical_projection(
                raw_family_mutant
            )

        boolean_family_mutant = json.loads(material)
        boolean_family_mutant["families"]["user_turn_input"] = {"present": True}
        with self.assertRaisesRegex(ValueError, "invalid_canonical_projection_family"):
            validation_messages.validate_validation_canonical_projection(
                boolean_family_mutant
            )

        missing_required_mutant = json.loads(material)
        missing_required_mutant["families"].pop("user_turn_input")
        with self.assertRaisesRegex(ValueError, "inconsistent_canonical_projection_family"):
            validation_messages.validate_validation_canonical_projection(
                missing_required_mutant
            )

        counterexample_projection = validation_messages.validate_validation_canonical_projection(
            _accepted_3712_counterexample_to_old_maximum_claim()
        )
        counterexample_chars = len(
            json.dumps(counterexample_projection, ensure_ascii=False, separators=(",", ":"))
        )
        self.assertEqual(counterexample_chars, 3712)
        maxima = lot4c1_comparison.measured_v2_maxima()
        self.assertEqual(maxima["accepted_contract_chars"], 3741)
        self.assertEqual(maxima["runtime_emittable_chars"], 3546)
        self.assertEqual(validation_messages.MAX_CANONICAL_INPUTS_JSON_CHARS, 3840)
        self.assertEqual(maxima["accepted_margin_chars"], 99)

    def test_projection_metadata_keeps_historical_v1_distinct_from_current_v2(self) -> None:
        historical = validation_contract.validate_canonical_projection_metadata(
            {
                "canonical_projection_version": "validation_canonical_inputs_v1",
                "canonical_projection_chars": 412,
                "canonical_projection_budget_chars": 700,
                "canonical_projection_included_families": ["stimmung_input"],
                "canonical_projection_omitted_families": ["recent_context_input"],
                "stimmung_delivery_status": "full",
                "stimmung_delivery_reason_code": "included",
                "raw_content_included": False,
            }
        )
        self.assertEqual(historical["canonical_projection_contract_status"], "historical_v1")
        self.assertEqual(
            historical["canonical_projection_unspecified_families"],
            ["recent_context_input"],
        )

        with self.assertRaisesRegex(ValueError, "unknown_canonical_projection_version"):
            validation_contract.validate_canonical_projection_metadata(
                {
                    "canonical_projection_version": "validation_canonical_inputs_v999",
                    "canonical_projection_chars": 0,
                    "canonical_projection_budget_chars": 1,
                    "canonical_projection_included_families": [],
                    "canonical_projection_omitted_families": [],
                    "stimmung_delivery_status": "absent",
                    "stimmung_delivery_reason_code": "signal_not_present",
                    "raw_content_included": False,
                }
            )


if __name__ == "__main__":
    unittest.main()
