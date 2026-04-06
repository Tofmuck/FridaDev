from __future__ import annotations

from typing import Any, Mapping, Tuple

import config


ACTIVE_IDENTITY_SOURCE = 'identity_mutables'
ACTIVE_PROMPT_CONTRACT = 'static + mutable narrative'
IDENTITY_INPUT_SCHEMA_VERSION = 'v2'
EDIT_UPDATED_BY = 'admin_identity_mutable_edit'
REASON_MAX_CHARS = 240
_ALLOWED_SUBJECTS = {'llm', 'user'}
_ALLOWED_ACTIONS = {'set', 'clear'}


def _text(value: Any) -> str:
    return str(value or '').strip()


def _current_content(item: Mapping[str, Any] | None) -> str:
    if not isinstance(item, Mapping):
        return ''
    return _text(item.get('content'))


def _normalized_subject(value: Any) -> str:
    text = _text(value).lower()
    if text not in _ALLOWED_SUBJECTS:
        return ''
    return text


def _normalized_action(value: Any) -> str:
    text = _text(value).lower()
    if text not in _ALLOWED_ACTIONS:
        return ''
    return text


def _budget_payload() -> dict[str, int]:
    return {
        'target_chars': int(config.IDENTITY_MUTABLE_TARGET_CHARS),
        'max_chars': int(config.IDENTITY_MUTABLE_MAX_CHARS),
    }


def _response_payload(
    *,
    ok: bool,
    subject: str,
    action: str,
    old_len: int,
    new_len: int,
    changed: bool,
    stored_after: bool,
    validation_ok: bool,
    reason_code: str,
    validation_error: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    payload = {
        'ok': bool(ok),
        'subject': subject,
        'action': action,
        'old_len': int(old_len),
        'new_len': int(new_len),
        'changed': bool(changed),
        'stored_after': bool(stored_after),
        'validation_ok': bool(validation_ok),
        'validation_error': validation_error,
        'reason_code': reason_code,
        'active_identity_source': ACTIVE_IDENTITY_SOURCE,
        'active_prompt_contract': ACTIVE_PROMPT_CONTRACT,
        'identity_input_schema_version': IDENTITY_INPUT_SCHEMA_VERSION,
        'mutable_budget': _budget_payload(),
    }
    if error:
        payload['error'] = error
        payload['error_code'] = validation_error or reason_code
    return payload


def _log_compact_edit(
    admin_logs_module: Any,
    *,
    subject: str,
    action: str,
    old_len: int,
    new_len: int,
    changed: bool,
    stored_after: bool,
    validation_ok: bool,
    validation_error: str | None,
    reason_code: str,
    reason_len: int,
) -> None:
    log_event = getattr(admin_logs_module, 'log_event', None)
    if not callable(log_event):
        return
    log_event(
        'identity_mutable_admin_edit',
        subject=subject,
        action=action,
        old_len=int(old_len),
        new_len=int(new_len),
        changed=bool(changed),
        stored_after=bool(stored_after),
        validation_ok=bool(validation_ok),
        validation_error=validation_error,
        reason_code=reason_code,
        reason_len=int(reason_len),
        active_identity_source=ACTIVE_IDENTITY_SOURCE,
        active_prompt_contract=ACTIVE_PROMPT_CONTRACT,
        identity_input_schema_version=IDENTITY_INPUT_SCHEMA_VERSION,
    )


def identity_mutable_edit_response(
    data: Mapping[str, Any],
    *,
    memory_store_module: Any,
    admin_logs_module: Any,
) -> Tuple[dict[str, Any], int]:
    payload = data if isinstance(data, Mapping) else {}
    raw_subject = _text(payload.get('subject')).lower()
    raw_action = _text(payload.get('action')).lower()
    reason = _text(payload.get('reason'))
    content = _text(payload.get('content'))
    reason_len = len(reason)
    new_len = len(content) if raw_action == 'set' else 0

    subject = _normalized_subject(raw_subject)
    action = _normalized_action(raw_action)

    get_mutable_identity = getattr(memory_store_module, 'get_mutable_identity', None)
    upsert_mutable_identity = getattr(memory_store_module, 'upsert_mutable_identity', None)
    clear_mutable_identity = getattr(memory_store_module, 'clear_mutable_identity', None)
    if not callable(get_mutable_identity) or not callable(upsert_mutable_identity) or not callable(clear_mutable_identity):
        response = _response_payload(
            ok=False,
            subject=subject or raw_subject,
            action=action or raw_action,
            old_len=0,
            new_len=new_len,
            changed=False,
            stored_after=False,
            validation_ok=False,
            validation_error='mutable_store_unavailable',
            reason_code='mutable_store_unavailable',
            error='edition mutable indisponible',
        )
        _log_compact_edit(
            admin_logs_module,
            subject=response['subject'],
            action=response['action'],
            old_len=0,
            new_len=new_len,
            changed=False,
            stored_after=False,
            validation_ok=False,
            validation_error='mutable_store_unavailable',
            reason_code='mutable_store_unavailable',
            reason_len=reason_len,
        )
        return response, 500

    current_content = _current_content(get_mutable_identity(subject)) if subject else ''
    old_len = len(current_content)

    if not subject:
        response = _response_payload(
            ok=False,
            subject=raw_subject,
            action=raw_action,
            old_len=0,
            new_len=new_len,
            changed=False,
            stored_after=False,
            validation_ok=False,
            validation_error='contract_subject_invalid',
            reason_code='contract_subject_invalid',
            error='subject invalide',
        )
        _log_compact_edit(
            admin_logs_module,
            subject=raw_subject,
            action=raw_action,
            old_len=0,
            new_len=new_len,
            changed=False,
            stored_after=False,
            validation_ok=False,
            validation_error='contract_subject_invalid',
            reason_code='contract_subject_invalid',
            reason_len=reason_len,
        )
        return response, 400

    if not action:
        response = _response_payload(
            ok=False,
            subject=subject,
            action=raw_action,
            old_len=old_len,
            new_len=new_len,
            changed=False,
            stored_after=bool(current_content),
            validation_ok=False,
            validation_error='contract_action_invalid',
            reason_code='contract_action_invalid',
            error='action invalide',
        )
        _log_compact_edit(
            admin_logs_module,
            subject=subject,
            action=raw_action,
            old_len=old_len,
            new_len=new_len,
            changed=False,
            stored_after=bool(current_content),
            validation_ok=False,
            validation_error='contract_action_invalid',
            reason_code='contract_action_invalid',
            reason_len=reason_len,
        )
        return response, 400

    if not reason:
        response = _response_payload(
            ok=False,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=new_len,
            changed=False,
            stored_after=bool(current_content),
            validation_ok=False,
            validation_error='contract_reason_missing',
            reason_code='contract_reason_missing',
            error='reason obligatoire',
        )
        _log_compact_edit(
            admin_logs_module,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=new_len,
            changed=False,
            stored_after=bool(current_content),
            validation_ok=False,
            validation_error='contract_reason_missing',
            reason_code='contract_reason_missing',
            reason_len=reason_len,
        )
        return response, 400

    if reason_len > REASON_MAX_CHARS:
        response = _response_payload(
            ok=False,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=new_len,
            changed=False,
            stored_after=bool(current_content),
            validation_ok=False,
            validation_error='contract_reason_too_long',
            reason_code='contract_reason_too_long',
            error='reason trop longue',
        )
        _log_compact_edit(
            admin_logs_module,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=new_len,
            changed=False,
            stored_after=bool(current_content),
            validation_ok=False,
            validation_error='contract_reason_too_long',
            reason_code='contract_reason_too_long',
            reason_len=reason_len,
        )
        return response, 400

    if action == 'clear' and content:
        response = _response_payload(
            ok=False,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=new_len,
            changed=False,
            stored_after=bool(current_content),
            validation_ok=False,
            validation_error='contract_clear_has_content',
            reason_code='contract_clear_has_content',
            error='clear n accepte pas de contenu',
        )
        _log_compact_edit(
            admin_logs_module,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=new_len,
            changed=False,
            stored_after=bool(current_content),
            validation_ok=False,
            validation_error='contract_clear_has_content',
            reason_code='contract_clear_has_content',
            reason_len=reason_len,
        )
        return response, 400

    if action == 'set' and not content:
        response = _response_payload(
            ok=False,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=0,
            changed=False,
            stored_after=bool(current_content),
            validation_ok=False,
            validation_error='contract_set_missing_content',
            reason_code='contract_set_missing_content',
            error='content obligatoire pour set',
        )
        _log_compact_edit(
            admin_logs_module,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=0,
            changed=False,
            stored_after=bool(current_content),
            validation_ok=False,
            validation_error='contract_set_missing_content',
            reason_code='contract_set_missing_content',
            reason_len=reason_len,
        )
        return response, 400

    if action == 'set' and len(content) > int(config.IDENTITY_MUTABLE_MAX_CHARS):
        response = _response_payload(
            ok=False,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=len(content),
            changed=False,
            stored_after=bool(current_content),
            validation_ok=False,
            validation_error='mutable_content_too_long',
            reason_code='mutable_content_too_long',
            error='mutable trop longue',
        )
        _log_compact_edit(
            admin_logs_module,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=len(content),
            changed=False,
            stored_after=bool(current_content),
            validation_ok=False,
            validation_error='mutable_content_too_long',
            reason_code='mutable_content_too_long',
            reason_len=reason_len,
        )
        return response, 400

    if action == 'set' and content == current_content:
        response = _response_payload(
            ok=True,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=old_len,
            changed=False,
            stored_after=bool(current_content),
            validation_ok=True,
            reason_code='unchanged',
        )
        _log_compact_edit(
            admin_logs_module,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=old_len,
            changed=False,
            stored_after=bool(current_content),
            validation_ok=True,
            validation_error=None,
            reason_code='unchanged',
            reason_len=reason_len,
        )
        return response, 200

    if action == 'clear' and not current_content:
        response = _response_payload(
            ok=True,
            subject=subject,
            action=action,
            old_len=0,
            new_len=0,
            changed=False,
            stored_after=False,
            validation_ok=True,
            reason_code='already_cleared',
        )
        _log_compact_edit(
            admin_logs_module,
            subject=subject,
            action=action,
            old_len=0,
            new_len=0,
            changed=False,
            stored_after=False,
            validation_ok=True,
            validation_error=None,
            reason_code='already_cleared',
            reason_len=reason_len,
        )
        return response, 200

    if action == 'set':
        updated = upsert_mutable_identity(
            subject,
            content,
            updated_by=EDIT_UPDATED_BY,
            update_reason=reason,
        )
        stored_after = _current_content(updated) == content if updated is not None else False
        if not stored_after:
            response = _response_payload(
                ok=False,
                subject=subject,
                action=action,
                old_len=old_len,
                new_len=len(content),
                changed=False,
                stored_after=bool(current_content),
                validation_ok=False,
                validation_error='mutable_set_failed',
                reason_code='mutable_set_failed',
                error='ecriture mutable indisponible',
            )
            _log_compact_edit(
                admin_logs_module,
                subject=subject,
                action=action,
                old_len=old_len,
                new_len=len(content),
                changed=False,
                stored_after=bool(current_content),
                validation_ok=False,
                validation_error='mutable_set_failed',
                reason_code='mutable_set_failed',
                reason_len=reason_len,
            )
            return response, 500

        response = _response_payload(
            ok=True,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=len(content),
            changed=True,
            stored_after=True,
            validation_ok=True,
            reason_code='set_applied',
        )
        _log_compact_edit(
            admin_logs_module,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=len(content),
            changed=True,
            stored_after=True,
            validation_ok=True,
            validation_error=None,
            reason_code='set_applied',
            reason_len=reason_len,
        )
        return response, 200

    cleared = clear_mutable_identity(subject)
    stored_after = bool(_current_content(get_mutable_identity(subject)))
    if stored_after:
        response = _response_payload(
            ok=False,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=0,
            changed=False,
            stored_after=True,
            validation_ok=False,
            validation_error='mutable_clear_failed',
            reason_code='mutable_clear_failed',
            error='effacement mutable indisponible',
        )
        _log_compact_edit(
            admin_logs_module,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=0,
            changed=False,
            stored_after=True,
            validation_ok=False,
            validation_error='mutable_clear_failed',
            reason_code='mutable_clear_failed',
            reason_len=reason_len,
        )
        return response, 500

    changed = cleared is not None or old_len > 0
    response = _response_payload(
        ok=True,
        subject=subject,
        action=action,
        old_len=old_len,
        new_len=0,
        changed=changed,
        stored_after=False,
        validation_ok=True,
        reason_code='clear_applied',
    )
    _log_compact_edit(
        admin_logs_module,
        subject=subject,
        action=action,
        old_len=old_len,
        new_len=0,
        changed=changed,
        stored_after=False,
        validation_ok=True,
        validation_error=None,
        reason_code='clear_applied',
        reason_len=reason_len,
    )
    return response, 200
