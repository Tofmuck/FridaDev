from __future__ import annotations

from typing import Any, Mapping, Sequence


EPISTEMIC_REGIMES = (
    "certain",
    "probable",
    "incertain",
    "suspendu",
    "contradictoire",
    "a_verifier",
)
PROOF_REGIMES = (
    "suffisant_en_l_etat",
    "source_explicite_requise",
    "verification_externe_requise",
    "arbitrage_requis",
)
UNCERTAINTY_POSTURES = (
    "discrete",
    "prudente",
    "explicite",
    "bloquante",
)

_WEB_REQUIRED_TYPES = {"scientifique"}
_CURRENT_FACT_TYPES = {"factuelle", "scientifique"}
_CAUTIONARY_SHIFT_STATES = {"candidate_shift", "shifted"}


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _text(value: Any) -> str:
    return str(value or "").strip()


def _explicit_conflict_signal(
    *,
    memory_arbitration: Mapping[str, Any],
    web_input: Mapping[str, Any],
) -> bool:
    # No canonical structured conflict signal is emitted yet by current runtime inputs.
    del memory_arbitration, web_input
    return False


def _required_provenances(user_turn_input: Mapping[str, Any]) -> set[str]:
    regime = _mapping(user_turn_input.get("regime_probatoire"))
    return {
        _text(value)
        for value in _sequence(regime.get("provenances"))
        if _text(value)
    }


def _requested_proof_types(user_turn_input: Mapping[str, Any]) -> set[str]:
    regime = _mapping(user_turn_input.get("regime_probatoire"))
    return {
        _text(value)
        for value in _sequence(regime.get("types_de_preuve_attendus"))
        if _text(value)
    }


def _current_temporal_scope(user_turn_input: Mapping[str, Any]) -> str:
    qualification = _mapping(user_turn_input.get("qualification_temporelle"))
    return _text(qualification.get("portee_temporelle"))


def _web_support_available(web_input: Mapping[str, Any]) -> bool:
    return _text(web_input.get("status")) == "ok" and _int_or_zero(web_input.get("results_count")) > 0


def _web_source_materially_used(source: Any) -> bool:
    if not isinstance(source, Mapping):
        return False
    if not bool(source.get("used_in_prompt")):
        return False
    if _text(source.get("used_content_kind")) in {"", "none"}:
        return False
    return bool(_text(source.get("content_used")))


def _web_evidence_available(web_input: Mapping[str, Any]) -> bool:
    if _text(web_input.get("status")) != "ok":
        return False
    return any(_web_source_materially_used(source) for source in _sequence(web_input.get("sources")))


def _summary_available(summary_input: Mapping[str, Any]) -> bool:
    return _text(summary_input.get("status")) == "available" and bool(_mapping(summary_input.get("summary")))


def _recent_trace_available(recent_window_input: Mapping[str, Any]) -> bool:
    return _int_or_zero(recent_window_input.get("turn_count")) > 0


def _memory_support_available(
    *,
    memory_retrieved: Mapping[str, Any],
    memory_arbitration: Mapping[str, Any],
) -> bool:
    if memory_arbitration:
        if _text(memory_arbitration.get("status")) == "error":
            return False
        return _int_or_zero(memory_arbitration.get("kept_count")) > 0
    return _int_or_zero(memory_retrieved.get("retrieved_count")) > 0


def _memory_is_univocal(memory_arbitration: Mapping[str, Any]) -> bool:
    return _int_or_zero(memory_arbitration.get("rejected_count")) == 0


def _satisfied_provenances(
    *,
    recent_window_input: Mapping[str, Any],
    summary_input: Mapping[str, Any],
    web_input: Mapping[str, Any],
) -> set[str]:
    satisfied: set[str] = set()
    if _recent_trace_available(recent_window_input):
        satisfied.add("dialogue_trace")
    if _summary_available(summary_input):
        satisfied.add("dialogue_resume")
    if _web_evidence_available(web_input):
        satisfied.add("web")
    return satisfied


def _signal_flags(user_turn_signals: Mapping[str, Any]) -> tuple[bool, bool, int]:
    active = _sequence(user_turn_signals.get("active_signal_families"))
    return (
        bool(user_turn_signals.get("ambiguity_present")),
        bool(user_turn_signals.get("underdetermination_present")),
        len([value for value in active if _text(value)]),
    )


def _stimmung_is_cautionary(stimmung_input: Mapping[str, Any]) -> bool:
    if not bool(stimmung_input.get("present")):
        return False
    if _text(stimmung_input.get("stability")) == "volatile":
        return True
    return _text(stimmung_input.get("shift_state")) in _CAUTIONARY_SHIFT_STATES


def _needs_external_verification(
    *,
    user_turn_input: Mapping[str, Any],
    web_input: Mapping[str, Any],
) -> bool:
    required_provenances = _required_provenances(user_turn_input)
    requested_types = _requested_proof_types(user_turn_input)
    temporal_scope = _current_temporal_scope(user_turn_input)
    web_evidence_available = _web_evidence_available(web_input)

    if requested_types & _WEB_REQUIRED_TYPES:
        return True
    if "web" in required_provenances and not web_evidence_available:
        return True
    if (
        temporal_scope in {"immediate", "actuelle", "prospective"}
        and requested_types & _CURRENT_FACT_TYPES
        and not web_evidence_available
    ):
        return True
    return False


def requires_external_verification(
    *,
    user_turn_input: Mapping[str, Any] | None = None,
    web_input: Mapping[str, Any] | None = None,
) -> bool:
    return _needs_external_verification(
        user_turn_input=_mapping(user_turn_input),
        web_input=_mapping(web_input),
    )


def _support_sources(
    *,
    memory_retrieved: Mapping[str, Any],
    memory_arbitration: Mapping[str, Any],
    summary_input: Mapping[str, Any],
    recent_window_input: Mapping[str, Any],
    web_input: Mapping[str, Any],
) -> set[str]:
    support: set[str] = set()
    if _memory_support_available(memory_retrieved=memory_retrieved, memory_arbitration=memory_arbitration):
        support.add("memory")
    if _summary_available(summary_input):
        support.add("dialogue_resume")
    if _recent_trace_available(recent_window_input):
        support.add("dialogue_trace")
    if _web_evidence_available(web_input):
        support.add("web")
    return support


def _build_result(
    epistemic_regime: str,
    proof_regime: str,
    uncertainty_posture: str,
) -> dict[str, str]:
    result = {
        "epistemic_regime": str(epistemic_regime),
        "proof_regime": str(proof_regime),
        "uncertainty_posture": str(uncertainty_posture),
    }

    if result["epistemic_regime"] == "certain":
        result["proof_regime"] = "suffisant_en_l_etat"
        result["uncertainty_posture"] = "discrete"
    elif result["epistemic_regime"] == "contradictoire":
        result["proof_regime"] = "arbitrage_requis"
        result["uncertainty_posture"] = "bloquante"
    elif result["epistemic_regime"] == "a_verifier":
        result["proof_regime"] = "verification_externe_requise"
        if result["uncertainty_posture"] not in {"explicite", "bloquante"}:
            result["uncertainty_posture"] = "explicite"
    elif result["epistemic_regime"] == "suspendu" and result["proof_regime"] == "suffisant_en_l_etat":
        result["proof_regime"] = "source_explicite_requise"

    if result["epistemic_regime"] not in EPISTEMIC_REGIMES:
        raise ValueError("invalid_epistemic_regime")
    if result["proof_regime"] not in PROOF_REGIMES:
        raise ValueError("invalid_proof_regime")
    if result["uncertainty_posture"] not in UNCERTAINTY_POSTURES:
        raise ValueError("invalid_uncertainty_posture")

    return result


def build_epistemic_regime(
    *,
    time_input: Mapping[str, Any] | None = None,
    memory_retrieved: Mapping[str, Any] | None = None,
    memory_arbitration: Mapping[str, Any] | None = None,
    summary_input: Mapping[str, Any] | None = None,
    identity_input: Mapping[str, Any] | None = None,
    recent_context_input: Mapping[str, Any] | None = None,
    recent_window_input: Mapping[str, Any] | None = None,
    user_turn_input: Mapping[str, Any] | None = None,
    user_turn_signals: Mapping[str, Any] | None = None,
    stimmung_input: Mapping[str, Any] | None = None,
    web_input: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    del time_input, identity_input, recent_context_input

    memory_retrieved_payload = _mapping(memory_retrieved)
    memory_arbitration_payload = _mapping(memory_arbitration)
    summary_input_payload = _mapping(summary_input)
    recent_window_input_payload = _mapping(recent_window_input)
    user_turn_input_payload = _mapping(user_turn_input)
    user_turn_signals_payload = _mapping(user_turn_signals)
    stimmung_input_payload = _mapping(stimmung_input)
    web_input_payload = _mapping(web_input)

    if not user_turn_input_payload:
        return _build_result("suspendu", "source_explicite_requise", "bloquante")

    if _explicit_conflict_signal(
        memory_arbitration=memory_arbitration_payload,
        web_input=web_input_payload,
    ):
        return _build_result("contradictoire", "arbitrage_requis", "bloquante")

    if requires_external_verification(
        user_turn_input=user_turn_input_payload,
        web_input=web_input_payload,
    ):
        return _build_result("a_verifier", "verification_externe_requise", "explicite")

    support_sources = _support_sources(
        memory_retrieved=memory_retrieved_payload,
        memory_arbitration=memory_arbitration_payload,
        summary_input=summary_input_payload,
        recent_window_input=recent_window_input_payload,
        web_input=web_input_payload,
    )
    support_count = len(support_sources)
    ambiguity_present, underdetermination_present, active_signal_families_count = _signal_flags(
        user_turn_signals_payload
    )
    stimmung_caution = _stimmung_is_cautionary(stimmung_input_payload)
    required_provenances = _required_provenances(user_turn_input_payload)
    satisfied_provenances = _satisfied_provenances(
        recent_window_input=recent_window_input_payload,
        summary_input=summary_input_payload,
        web_input=web_input_payload,
    )
    missing_required_provenances = required_provenances - satisfied_provenances
    missing_non_external_provenances = {value for value in missing_required_provenances if value != "web"}
    severe_blockage = (
        (ambiguity_present and underdetermination_present)
        or bool(missing_non_external_provenances and support_count == 0)
        or bool(active_signal_families_count >= 2 and support_count == 0)
    )

    if (
        support_count >= 2
        and not ambiguity_present
        and not underdetermination_present
        and not missing_non_external_provenances
        and not stimmung_caution
        and _memory_is_univocal(memory_arbitration_payload)
    ):
        return _build_result("certain", "suffisant_en_l_etat", "discrete")

    if support_count >= 1 and not severe_blockage:
        posture = "prudente" if (ambiguity_present or underdetermination_present or stimmung_caution) else "discrete"
        return _build_result("probable", "source_explicite_requise", posture)

    if severe_blockage:
        return _build_result("suspendu", "source_explicite_requise", "bloquante")

    return _build_result(
        "incertain",
        "source_explicite_requise",
        "explicite" if (ambiguity_present or underdetermination_present or stimmung_caution) else "prudente",
    )
