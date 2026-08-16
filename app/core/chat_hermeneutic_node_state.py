from __future__ import annotations

from typing import Any, Mapping

from core.hermeneutic_node.runtime import node_state as runtime_node_state


_FINAL_ANSWER_OUTPUT_REGIME = {
    'discursive_regime': 'simple',
    'resituation_level': 'none',
    'time_reference_mode': 'atemporal',
}
_FINAL_NON_ANSWER_OUTPUT_REGIME = {
    'discursive_regime': 'meta',
    'resituation_level': 'none',
    'time_reference_mode': 'atemporal',
}


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _text(value: Any) -> str:
    return str(value or '').strip()


def _read_hermeneutic_node_state(
    *,
    memory_store_module: Any,
    conversation_id: str,
) -> dict[str, Any]:
    reader = getattr(memory_store_module, 'read_hermeneutic_node_state', None)
    if not callable(reader):
        return {
            'state': None,
            'present': False,
            'valid': False,
            'reason_code': 'reader_unavailable',
            'schema_version': '',
            'state_sha256_12': '',
        }
    try:
        result = reader(conversation_id)
    except Exception as exc:
        return {
            'state': None,
            'present': False,
            'valid': False,
            'reason_code': 'read_error',
            'schema_version': '',
            'state_sha256_12': '',
            'error_class': exc.__class__.__name__,
        }
    return _mapping(result)


def _existing_node_state_from_read(read_result: Mapping[str, Any] | None) -> dict[str, Any] | None:
    payload = _mapping(read_result)
    if not bool(payload.get('valid', False)):
        return None
    state = _mapping(payload.get('state'))
    return state or None


def _skipped_hermeneutic_node_state_write(reason_code: str) -> dict[str, Any]:
    return {
        'attempted': False,
        'written': False,
        'changed': False,
        'reason_code': _text(reason_code) or 'not_applicable',
        'schema_version': '',
        'state_sha256_12': '',
    }


def _write_hermeneutic_node_state(
    *,
    memory_store_module: Any,
    conversation_id: str,
    node_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    writer = getattr(memory_store_module, 'write_hermeneutic_node_state', None)
    if not callable(writer):
        return {
            'attempted': False,
            'written': False,
            'changed': False,
            'reason_code': 'writer_unavailable',
            'schema_version': '',
            'state_sha256_12': '',
        }
    try:
        result = writer(conversation_id, node_state_payload)
    except Exception as exc:
        return {
            'attempted': True,
            'written': False,
            'changed': False,
            'reason_code': 'write_error',
            'schema_version': '',
            'state_sha256_12': '',
            'error_class': exc.__class__.__name__,
        }
    return _mapping(result)


def _build_final_hermeneutic_node_state(
    *,
    conversation_id: str,
    now_iso: str,
    validated_result: Any,
    existing_node_state: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, str]:
    validated_output = _mapping(getattr(validated_result, 'validated_output', None))
    if not validated_output:
        return None, 'validated_output_missing'

    final_judgment_posture = _text(validated_output.get('final_judgment_posture'))
    final_output_regime = _text(validated_output.get('final_output_regime'))
    if final_output_regime == 'presence':
        if final_judgment_posture != 'answer':
            return None, 'invalid_presence_judgment_posture'
        return None, 'presence_turn_local'
    if final_judgment_posture == 'answer':
        if final_output_regime != 'simple':
            return None, 'unsupported_final_output_regime'
        output_regime = _FINAL_ANSWER_OUTPUT_REGIME
    elif final_judgment_posture in {'clarify', 'suspend'}:
        output_regime = _FINAL_NON_ANSWER_OUTPUT_REGIME
    else:
        return None, 'invalid_final_judgment_posture'

    try:
        state = runtime_node_state.build_node_state(
            conversation_id=conversation_id,
            updated_at=now_iso,
            judgment_posture=final_judgment_posture,
            output_regime=output_regime,
            existing_node_state=existing_node_state,
        )
    except Exception:
        return None, 'invalid_validated_node_state'
    return state, ''
