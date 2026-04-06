from __future__ import annotations

from typing import Any, Mapping, Tuple

import config

from admin import admin_identity_mutable_edit_audit as audit
from admin import admin_identity_mutable_edit_contract as contract


def identity_mutable_edit_response(
    data: Mapping[str, Any],
    *,
    memory_store_module: Any,
    admin_logs_module: Any,
) -> Tuple[dict[str, Any], int]:
    payload = data if isinstance(data, Mapping) else {}
    raw_subject = contract.text(payload.get('subject')).lower()
    raw_action = contract.text(payload.get('action')).lower()
    reason = contract.text(payload.get('reason'))
    content = contract.text(payload.get('content'))
    reason_len = len(reason)
    new_len = len(content) if raw_action == 'set' else 0

    subject = contract.normalize_subject(raw_subject)
    action = contract.normalize_action(raw_action)

    get_mutable_identity = getattr(memory_store_module, 'get_mutable_identity', None)
    upsert_mutable_identity = getattr(memory_store_module, 'upsert_mutable_identity', None)
    clear_mutable_identity = getattr(memory_store_module, 'clear_mutable_identity', None)
    if not callable(get_mutable_identity) or not callable(upsert_mutable_identity) or not callable(clear_mutable_identity):
        response = contract.response_payload(
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
        audit.log_compact_edit(
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

    current_content = contract.current_content(get_mutable_identity(subject)) if subject else ''
    old_len = len(current_content)

    if not subject:
        response = contract.response_payload(
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
        audit.log_compact_edit(
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
        response = contract.response_payload(
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
        audit.log_compact_edit(
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
        response = contract.response_payload(
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
        audit.log_compact_edit(
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

    if reason_len > contract.REASON_MAX_CHARS:
        response = contract.response_payload(
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
        audit.log_compact_edit(
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
        response = contract.response_payload(
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
        audit.log_compact_edit(
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
        response = contract.response_payload(
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
        audit.log_compact_edit(
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
        response = contract.response_payload(
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
        audit.log_compact_edit(
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
        response = contract.response_payload(
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
        audit.log_compact_edit(
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
        response = contract.response_payload(
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
        audit.log_compact_edit(
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
            updated_by=contract.EDIT_UPDATED_BY,
            update_reason=reason,
        )
        stored_after = contract.current_content(updated) == content if updated is not None else False
        if not stored_after:
            response = contract.response_payload(
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
            audit.log_compact_edit(
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

        response = contract.response_payload(
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
        audit.log_compact_edit(
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
    stored_after = bool(contract.current_content(get_mutable_identity(subject)))
    if stored_after:
        response = contract.response_payload(
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
        audit.log_compact_edit(
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
    response = contract.response_payload(
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
    audit.log_compact_edit(
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
