from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from core.hermeneutic_node.inputs import recent_context_input as canonical_recent_context_input
from core.hermeneutic_node.inputs import time_input as canonical_time_input
from observability import chat_turn_logger
from . import validation_contract


SCHEMA_VERSION = validation_contract.SCHEMA_VERSION
MAX_VALIDATION_CONTEXT_MESSAGES = canonical_recent_context_input.VALIDATION_DIALOGUE_CONTEXT_MAX_MESSAGES
MAX_VALIDATION_CONTEXT_MESSAGE_CHARS = 420
MAX_VALIDATION_CONTEXT_JSON_CHARS = 4200
MAX_PRIMARY_VERDICT_JSON_CHARS = 1000
MAX_JUSTIFICATIONS_JSON_CHARS = 700
MAX_CANONICAL_INPUTS_JSON_CHARS = 700
MAX_RESPONSE_TOKENS = 140


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _compact_text(value: Any, *, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max(0, max_chars - 3)].rstrip()}..."


def _bounded_json_preview(value: Any, *, max_chars: int) -> str:
    raw = _compact_json(value)
    if len(raw) <= max_chars:
        return raw

    preview_chars = max(32, max_chars - 48)
    bounded = _compact_json({"truncated": True, "preview": _compact_text(raw, max_chars=preview_chars)})
    while len(bounded) > max_chars and preview_chars > 16:
        preview_chars -= 16
        bounded = _compact_json({"truncated": True, "preview": _compact_text(raw, max_chars=preview_chars)})
    return bounded


def _bounded_response_max_tokens(value: Any) -> int:
    try:
        candidate = int(value)
    except (TypeError, ValueError):
        return MAX_RESPONSE_TOKENS
    if candidate <= 0:
        return MAX_RESPONSE_TOKENS
    return min(candidate, MAX_RESPONSE_TOKENS)


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _sha256_12(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _count_by_key(items: Sequence[Any], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        payload = _mapping(item)
        label = _text(payload.get(key)) or "unknown"
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))


def _candidate_id_hashes(items: Sequence[Any], *, limit: int = 8) -> list[str]:
    hashes: list[str] = []
    for item in items:
        digest = _sha256_12(_mapping(item).get("candidate_id"))
        if digest:
            hashes.append(digest)
        if len(hashes) >= limit:
            break
    return hashes


def _content_chars(items: Sequence[Any], *, include_parent_summary: bool = False) -> int:
    total = 0
    for item in items:
        payload = _mapping(item)
        total += len(str(payload.get("content") or ""))
        if include_parent_summary:
            total += len(str(_mapping(payload.get("parent_summary")).get("content") or ""))
    return total


def _summarize_validation_dialogue_context(payload: Mapping[str, Any]) -> dict[str, Any]:
    messages = _sequence(payload.get("messages"))
    role_counts = _count_by_key(messages, "role")
    return {
        "present": bool(payload),
        "message_count": _int_or_zero(payload.get("source_message_count") or len(messages)),
        "retained_message_count": len(messages),
        "current_user_retained": bool(payload.get("current_user_retained", False)),
        "last_assistant_retained": bool(payload.get("last_assistant_retained", False)),
        "truncated": bool(payload.get("truncated", False)),
        "role_counts": role_counts,
        "content_chars_total": _content_chars(messages),
        "json_chars": len(_compact_json(payload)) if payload else 0,
    }


def _summarize_memory_retrieved(canonical_inputs: Mapping[str, Any]) -> dict[str, Any]:
    data = _mapping(canonical_inputs.get("memory_retrieved"))
    traces = _sequence(data.get("traces"))
    return {
        "present": bool(data),
        "status": _text(data.get("status")) or ("ok" if data else "missing"),
        "reason_code": _text(data.get("reason_code")),
        "error_code": _text(data.get("error_code")),
        "error_class": _text(data.get("error_class")),
        "top_k_requested": data.get("top_k_requested"),
        "retrieved_count": _int_or_zero(data.get("retrieved_count") or len(traces)),
        "traces_count": len(traces),
        "source_kind_counts": _count_by_key(traces, "source_kind"),
        "source_lane_counts": _count_by_key(traces, "source_lane"),
        "candidate_ids_count": sum(1 for item in traces if _text(_mapping(item).get("candidate_id"))),
        "candidate_id_hashes": _candidate_id_hashes(traces),
        "content_chars_total": _content_chars(traces, include_parent_summary=True),
        "parent_summary_present_count": sum(1 for item in traces if bool(_mapping(item).get("parent_summary"))),
    }


def _summarize_memory_arbitration(canonical_inputs: Mapping[str, Any]) -> dict[str, Any]:
    data = _mapping(canonical_inputs.get("memory_arbitration"))
    basket_candidates = _sequence(data.get("basket_candidates"))
    decisions = _sequence(data.get("decisions"))
    injected_ids = [
        _text(item)
        for item in _sequence(data.get("injected_candidate_ids"))
        if _text(item)
    ]
    return {
        "present": bool(data),
        "status": _text(data.get("status")) or ("available" if data else "missing"),
        "reason_code": _text(data.get("reason_code")),
        "raw_candidates_count": _int_or_zero(data.get("raw_candidates_count")),
        "basket_candidates_count": _int_or_zero(data.get("basket_candidates_count") or len(basket_candidates)),
        "decisions_count": _int_or_zero(data.get("decisions_count") or len(decisions)),
        "kept_count": _int_or_zero(data.get("kept_count")),
        "rejected_count": _int_or_zero(data.get("rejected_count")),
        "injected_candidate_ids_count": len(injected_ids),
        "injected_candidate_id_hashes": [_sha256_12(item) for item in injected_ids[:8]],
        "basket_source_kind_counts": _count_by_key(basket_candidates, "source_kind"),
        "basket_source_lane_counts": _count_by_key(basket_candidates, "source_lane"),
        "decision_source_counts": _count_by_key(decisions, "decision_source"),
        "basket_content_chars_total": _content_chars(basket_candidates),
    }


def _provider_message_summary(messages: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    role_counts = _count_by_key(messages, "role")
    content_chars = [len(str(_mapping(message).get("content") or "")) for message in messages]
    return {
        "messages_count": len(messages),
        "role_counts": role_counts,
        "content_chars_total": sum(content_chars),
        "system_message_chars": sum(
            len(str(_mapping(message).get("content") or ""))
            for message in messages
            if _text(_mapping(message).get("role")) == "system"
        ),
        "user_message_chars": sum(
            len(str(_mapping(message).get("content") or ""))
            for message in messages
            if _text(_mapping(message).get("role")) == "user"
        ),
    }


def _emit_validation_prompt_prepared(
    *,
    model: str,
    decision_source: str,
    messages: Sequence[Mapping[str, str]],
    validation_dialogue_context: Mapping[str, Any],
    canonical_inputs: Mapping[str, Any],
    hard_guard_payload: Mapping[str, Any],
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> None:
    canonical_input_keys = sorted(_text(key) for key in canonical_inputs.keys() if _text(key))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "payload_kind": "secondary_validation_agent_provider",
        "provider_caller": "validation_agent",
        "main_llm_payload": False,
        "secondary_provider_payload": True,
        "validation_status": "prepared",
        "attempt_decision_source": str(decision_source or "unknown"),
        "sampling": {
            "temperature": float(temperature),
            "top_p": float(top_p),
            "max_tokens": _bounded_response_max_tokens(max_tokens),
        },
        "provider_messages": _provider_message_summary(messages),
        "validation_dialogue_context": _summarize_validation_dialogue_context(
            validation_dialogue_context
        ),
        "canonical_inputs": {
            "present": bool(canonical_inputs),
            "input_keys": canonical_input_keys,
            "input_keys_count": len(canonical_input_keys),
            "json_chars": len(_compact_json(canonical_inputs)) if canonical_inputs else 0,
        },
        "memory_retrieved": _summarize_memory_retrieved(canonical_inputs),
        "memory_arbitration": _summarize_memory_arbitration(canonical_inputs),
        "hard_guard": {
            "present": bool(hard_guard_payload),
            "allowed_postures_count": len(_sequence(hard_guard_payload.get("allowed_postures"))),
            "applied_hard_guards_count": len(_sequence(hard_guard_payload.get("applied_hard_guards"))),
            "effect_present": bool(_text(hard_guard_payload.get("hard_guard_effect"))),
        },
    }
    chat_turn_logger.emit(
        "validation_prompt_prepared",
        status="ok",
        model=model,
        prompt_kind="validation_agent_secondary",
        payload=payload,
    )


emit_validation_prompt_prepared = _emit_validation_prompt_prepared


def validation_time_reference(canonical_inputs: Mapping[str, Any]) -> dict[str, Any]:
    time_payload = _mapping(_mapping(canonical_inputs).get("time_input"))
    now_utc_iso = _text(time_payload.get("now_utc_iso"))
    timezone_name = _text(time_payload.get("timezone"))
    if not now_utc_iso or not timezone_name:
        return {}
    if not _text(time_payload.get("now_local_iso")):
        try:
            time_payload = canonical_time_input.build_time_input(
                now_utc_iso=now_utc_iso,
                timezone_name=timezone_name,
            )
        except Exception:
            time_payload = dict(time_payload)
    return {
        "now_utc_iso": _text(time_payload.get("now_utc_iso")) or now_utc_iso,
        "timezone": timezone_name,
        "now_local_iso": _text(time_payload.get("now_local_iso")),
        "local_date": _text(time_payload.get("local_date")),
        "local_time": _text(time_payload.get("local_time")),
    }


def _message_temporal_label(timestamp: str, time_reference: Mapping[str, Any]) -> str:
    now_utc_iso = _text(time_reference.get("now_utc_iso"))
    timezone_name = _text(time_reference.get("timezone"))
    if not timestamp or not now_utc_iso or not timezone_name:
        return ""
    return canonical_time_input.render_delta_label(
        timestamp,
        now_utc_iso,
        timezone_name=timezone_name,
    )


def compacted_validation_dialogue_context(
    value: Any,
    *,
    time_reference: Mapping[str, Any] | None = None,
) -> str:
    payload = _mapping(value)
    raw_messages = payload.get("messages")
    if not isinstance(raw_messages, list):
        return _bounded_json_preview(payload, max_chars=MAX_VALIDATION_CONTEXT_JSON_CHARS)

    retained_messages: list[dict[str, Any]] = []
    content_truncated = False
    time_payload = _mapping(time_reference)
    for item in raw_messages[-MAX_VALIDATION_CONTEXT_MESSAGES:]:
        message_payload = _mapping(item)
        role = _text(message_payload.get("role"))
        if role not in {"user", "assistant"}:
            continue
        raw_content = _text(message_payload.get("content"))
        content = _compact_text(raw_content, max_chars=MAX_VALIDATION_CONTEXT_MESSAGE_CHARS)
        content_truncated = content_truncated or raw_content != content
        timestamp = _text(message_payload.get("timestamp")) or None
        retained = {
            "role": role,
            "timestamp": timestamp,
            "content": content,
        }
        if timestamp:
            temporal_label = _message_temporal_label(timestamp, time_payload)
            if temporal_label:
                retained["temporal_label"] = temporal_label
        retained_messages.append(retained)

    compacted_payload: dict[str, Any] = {
        "schema_version": _text(payload.get("schema_version")) or SCHEMA_VERSION,
        "message_count": int(payload.get("source_message_count") or len(raw_messages)),
        "retained_message_count": len(retained_messages),
        "current_user_retained": bool(
            payload.get(
                "current_user_retained",
                bool(retained_messages and _text(retained_messages[-1].get("role")) == "user"),
            )
        ),
        "last_assistant_retained": bool(
            payload.get(
                "last_assistant_retained",
                any(_text(item.get("role")) == "assistant" for item in retained_messages),
            )
        ),
        "messages": retained_messages,
        "truncated": bool(payload.get("truncated", False) or content_truncated),
    }
    if time_payload:
        compacted_payload["time_reference"] = {
            key: _text(time_payload.get(key))
            for key in ("now_utc_iso", "timezone", "now_local_iso", "local_date", "local_time")
            if _text(time_payload.get(key))
        }
    return _bounded_json_preview(
        compacted_payload,
        max_chars=MAX_VALIDATION_CONTEXT_JSON_CHARS,
    )


def build_messages(
    *,
    system_prompt: str,
    primary_verdict: Mapping[str, Any],
    justifications: Mapping[str, Any],
    validation_dialogue_context: Mapping[str, Any],
    canonical_inputs: Mapping[str, Any],
    hard_guard_payload: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    time_reference = validation_time_reference(canonical_inputs)
    compacted_time_reference = _bounded_json_preview(time_reference, max_chars=420) if time_reference else ""
    validation_dialogue_context_preview = compacted_validation_dialogue_context(
        validation_dialogue_context,
        time_reference=time_reference,
    )
    compacted_primary_verdict = _bounded_json_preview(primary_verdict, max_chars=MAX_PRIMARY_VERDICT_JSON_CHARS)
    compacted_justifications = _bounded_json_preview(justifications, max_chars=MAX_JUSTIFICATIONS_JSON_CHARS)
    compacted_canonical_inputs = _bounded_json_preview(canonical_inputs, max_chars=MAX_CANONICAL_INPUTS_JSON_CHARS)
    compacted_hard_guard_payload = _bounded_json_preview(
        _mapping(hard_guard_payload),
        max_chars=320,
    )
    hard_guard_block = ""
    if _mapping(hard_guard_payload):
        hard_guard_block = (
            "hard_guards (contraintes deterministes non cassables):\n"
            f"{compacted_hard_guard_payload}\n\n"
        )
    return [
        {"role": "system", "content": str(system_prompt or "")},
        {
            "role": "user",
            "content": (
                "temporal_reference (autorite locale pour lire le validation_dialogue_context):\n"
                f"{compacted_time_reference or '{}'}\n\n"
                "validation_dialogue_context (matiere hermeneutique principale, fenetre dialogique locale canonisee):\n"
                f"{validation_dialogue_context_preview}\n\n"
                "primary_verdict (recommendation structuree amont, secondaire et non terminale):\n"
                f"{compacted_primary_verdict}\n\n"
                "justifications (support secondaire frere, hors primary_verdict):\n"
                f"{compacted_justifications}\n\n"
                "canonical_inputs (supports secondaires de relecture contextuelle):\n"
                f"{compacted_canonical_inputs}\n\n"
                f"{hard_guard_block}"
                "Tache:\n"
                "- decide final_judgment_posture\n"
                "- decide final_output_regime\n"
                "- relis le dernier enonce et le dialogue comme texte dans la tension Warum / Wofür / Wozu, sans checklist ni sortie dediee\n"
                "- presume que le tour a un sens dans l'histoire locale du dialogue avant de traiter un signal structure secondaire comme une absence de sens\n"
                "- reconstruis les premisses implicites comme hypotheses interpretatives, sans attribuer une intention ou un etat interieur certain a l'utilisateur\n"
                "- identifie l'acte dialogique accompli avant d'evaluer: question, affirmation, correction, hypothese, depot, suspension, cloture ou autre\n"
                "- distingue comprendre la proposition, integrer une correction factuelle etayee, etre convaincue par un argument et adopter une position\n"
                "- ni l'insistance, ni le desaccord reformule, ni l'intensite affective ne prouvent qu'une position doit etre adoptee\n"
                "- ne fabrique pas non plus un desaccord pour simuler une independance\n"
                "- privilegie la lecture la plus coherente du tour, la continuite dialogique locale et la reponse simple\n"
                "- ne choisis clarify qu'apres l'echec d'une interpretation coherente depuis le contexte, ou si des lectures incompatibles entraineraient des actions materiellement differentes\n"
                "- un signal lexical, une ponctuation ou une recommandation amont de clarification ne suffit jamais seul a choisir clarify\n"
                "- si answer reste possible, privilegie final_output_regime = simple\n"
                "- reserve meta aux cas ou une reprise meta est reellement necessaire\n"
                "- choisis final_output_regime = presence seulement pour un acte local clairement compris qui appelle reception sans contenu propositionnel ni poursuite\n"
                "- presence signifie exclusivement une sortie visible exacte de trois points ASCII; ne le choisis jamais pour une question, une demande, une detresse, un risque, une action materielle ambigue ou par simple detection de mots\n"
                "- presence exige final_judgment_posture = answer; suspend conserve exclusivement son sens epistemique et doit rester explicite\n"
                "- si un hard guard interdit answer, choisis entre clarify et suspend\n"
                "- si hard_guard_effect = caveat_required, answer reste possible mais la prudence indiquee est obligatoire\n"
                "- un hard guard ne force pas a lui seul meta\n"
                "- validation_decision legacy sera derivee downstream: ne l'invente pas\n"
                "- reponds en JSON strict uniquement\n"
                '- schema attendu: {"schema_version":"v1","final_judgment_posture":"answer|clarify|suspend","final_output_regime":"simple|meta|presence","arbiter_reason":"raison_courte_lisible"}'
            ),
        },
    ]
