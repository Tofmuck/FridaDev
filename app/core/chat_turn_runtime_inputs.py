from __future__ import annotations

from typing import Any, Mapping

from core import conversations_prompt_window
from core import stimmung_agent
from core.hermeneutic_node.inputs import identity_input as canonical_identity_input
from core.hermeneutic_node.inputs import recent_context_input
from core.hermeneutic_node.inputs import recent_window_input as canonical_recent_window_input
from core.hermeneutic_node.inputs import stimmung_input as canonical_stimmung_input
from core.hermeneutic_node.inputs import summary_input
from core.hermeneutic_node.inputs import time_input as canonical_time_input
from core.hermeneutic_node.inputs import user_turn_input as canonical_user_turn_input
from core.hermeneutic_node.inputs import web_input as canonical_web_input
from observability import chat_turn_logger


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def resolve_time_input(
    *,
    now_iso: str,
    config_module: Any,
) -> dict[str, Any]:
    return canonical_time_input.build_time_input(
        now_utc_iso=now_iso,
        timezone_name=str(config_module.FRIDA_TIMEZONE),
    )


def resolve_summary_input(
    *,
    conversation_id: str | None,
    conv_store_module: Any,
) -> dict[str, Any]:
    db_conn_func = getattr(conv_store_module, '_db_conn', None)
    ts_to_iso_func = getattr(conv_store_module, '_ts_to_iso', None)
    conv_logger = getattr(conv_store_module, 'logger', None)
    if not callable(db_conn_func) or not callable(ts_to_iso_func) or conv_logger is None:
        return summary_input.build_summary_input(
            active_summary=None,
            conversation_id=conversation_id,
        )
    try:
        active_summary = conversations_prompt_window.get_active_summary(
            conversation_id,
            normalize_conversation_id_func=lambda value: str(value) if value else None,
            db_conn_func=db_conn_func,
            ts_to_iso_func=ts_to_iso_func,
            logger=conv_logger,
        )
    except Exception:
        active_summary = None
    return summary_input.build_summary_input(
        active_summary=active_summary,
        conversation_id=conversation_id,
    )


def resolve_identity_input(
    *,
    identity_module: Any,
) -> dict[str, Any]:
    build_identity_payload = getattr(identity_module, 'build_identity_input', None)
    if not callable(build_identity_payload):
        return canonical_identity_input.build_identity_input()
    try:
        return build_identity_payload()
    except Exception:
        return canonical_identity_input.build_identity_input()


def resolve_recent_context_input(
    *,
    conversation: Mapping[str, Any],
    summary_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return recent_context_input.build_recent_context_input(
        messages=conversation.get('messages', []),
        summary_input_payload=summary_payload,
    )


def resolve_validation_dialogue_context(
    *,
    conversation: Mapping[str, Any],
    recent_context_payload: Mapping[str, Any] | None,
    user_msg: str,
    now_iso: str,
) -> dict[str, Any]:
    base_messages = _mapping(recent_context_payload).get('messages')
    if isinstance(base_messages, list) and base_messages:
        return recent_context_input.build_validation_dialogue_context(
            messages=base_messages,
            summary_input_payload=None,
        )

    rebuilt_payload = recent_context_input.build_validation_dialogue_context(
        messages=conversation.get('messages', []),
        summary_input_payload=None,
    )
    rebuilt_messages = _mapping(rebuilt_payload).get('messages')
    if isinstance(rebuilt_messages, list) and rebuilt_messages:
        return rebuilt_payload

    return recent_context_input.build_validation_dialogue_context(
        messages=[
            {
                'role': 'user',
                'content': str(user_msg or ''),
                'timestamp': str(now_iso or '').strip() or None,
            }
        ],
        summary_input_payload=None,
    )


def resolve_recent_window_input(
    *,
    recent_context_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return canonical_recent_window_input.build_recent_window_input(
        recent_context_input_payload=recent_context_payload,
    )


def resolve_user_turn_runtime_inputs(
    *,
    user_msg: str,
    recent_window_payload: Mapping[str, Any] | None,
    time_payload: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    bundle = canonical_user_turn_input.build_user_turn_bundle(
        user_message=user_msg,
        recent_window_input_payload=recent_window_payload,
        time_input_payload=time_payload,
    )
    return (
        dict(bundle.get("user_turn") or {}),
        dict(bundle.get("user_turn_signals") or {}),
    )


def store_latest_user_affective_turn_signal(
    *,
    conversation: Mapping[str, Any],
    signal: Mapping[str, Any] | None,
) -> None:
    messages = conversation.get("messages")
    if not isinstance(messages, list):
        return

    canonical_signal = dict(signal or {})
    if not canonical_signal:
        return

    for message in reversed(messages):
        if not isinstance(message, dict):
            continue
        if str(message.get("role") or "") != "user":
            continue
        meta = dict(message.get("meta") or {})
        meta[canonical_stimmung_input.SIGNAL_META_KEY] = canonical_signal
        message["meta"] = meta
        return


def resolve_web_runtime_payload(
    *,
    user_msg: str,
    web_search_on: bool,
    web_search_module: Any,
    requests_module: Any,
    llm_module: Any,
) -> dict[str, Any]:
    activation_mode = 'manual' if web_search_on else 'not_requested'

    if activation_mode == 'not_requested':
        chat_turn_logger.emit(
            'web_search',
            status='skipped',
            reason_code='not_applicable',
            payload={
                'enabled': False,
                'activation_mode': 'not_requested',
                'query_preview': '',
                'results_count': 0,
                'context_injected': False,
                'truncated': False,
            },
        )
        chat_turn_logger.emit_branch_skipped(
            reason_code='not_applicable',
            reason_short='web_search_not_requested',
        )
        return {
            'enabled': False,
            'status': 'skipped',
            'activation_mode': 'not_requested',
            'reason_code': 'not_applicable',
            'original_user_message': str(user_msg or ''),
            'query': None,
            'results_count': 0,
            'runtime': {},
            'sources': [],
            'context_block': '',
        }
    build_context_payload = getattr(web_search_module, 'build_context_payload', None)
    if callable(build_context_payload):
        payload = dict(
            build_context_payload(
                user_msg,
                requests_module=requests_module,
                llm_module=llm_module,
            )
        )
        payload['activation_mode'] = activation_mode
        return payload

    ctx, query, n_results = web_search_module.build_context(
        user_msg,
        requests_module=requests_module,
        llm_module=llm_module,
    )
    return {
        'enabled': True,
        'status': 'ok' if ctx else 'skipped',
        'activation_mode': activation_mode,
        'reason_code': None if ctx else 'no_data',
        'original_user_message': str(user_msg or ''),
        'query': str(query or ''),
        'results_count': int(n_results),
        'runtime': {},
        'sources': [],
        'context_block': str(ctx or ''),
    }


def run_stimmung_agent_stage(
    *,
    user_msg: str,
    recent_window_payload: Mapping[str, Any] | None,
    requests_module: Any,
) -> dict[str, Any]:
    result = stimmung_agent.build_affective_turn_signal(
        user_msg=user_msg,
        recent_window_input_payload=recent_window_payload,
        requests_module=requests_module,
    )
    signal = dict(result.signal or {})
    tones = []
    for item in signal.get('tones', []):
        tone_payload = dict(item or {})
        tone = str(tone_payload.get('tone') or '').strip()
        strength = tone_payload.get('strength')
        if tone and isinstance(strength, int):
            tones.append({'tone': tone, 'strength': strength})

    payload = {
        'present': bool(signal.get('present', False)),
        'dominant_tone': signal.get('dominant_tone'),
        'tones_count': len(tones),
        'tones': tones,
        'confidence': float(signal.get('confidence') or 0.0),
        'decision_source': str(result.decision_source or ''),
    }
    if result.reason_code:
        payload['reason_code'] = str(result.reason_code)

    chat_turn_logger.emit(
        'stimmung_agent',
        status=str(result.status or 'ok'),
        payload=payload,
        model=str(result.model or ''),
    )
    return signal


def build_stimmung_input(
    *,
    conversation: Mapping[str, Any],
) -> dict[str, Any]:
    return canonical_stimmung_input.build_stimmung_input(
        messages=conversation.get("messages", []),
    )


def build_web_input_from_runtime_payload(
    runtime_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return canonical_web_input.build_web_input_from_runtime_payload(runtime_payload)
