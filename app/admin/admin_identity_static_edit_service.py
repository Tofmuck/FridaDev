from __future__ import annotations

from typing import Any, Mapping, Tuple

from admin import admin_identity_static_edit_audit as audit
from admin import admin_identity_static_edit_contract as contract


def _audit_and_return(
    admin_logs_module: Any,
    response: dict[str, Any],
    *,
    reason_len: int,
) -> Tuple[dict[str, Any], int]:
    audit.log_compact_edit(
        admin_logs_module,
        subject=response['subject'],
        action=response['action'],
        old_len=response['old_len'],
        new_len=response['new_len'],
        changed=response['changed'],
        stored_after=response['stored_after'],
        validation_ok=response['validation_ok'],
        validation_error=response.get('validation_error'),
        reason_code=response['reason_code'],
        reason_len=reason_len,
        resource_field=response['resource_field'],
        resolution_kind=response['resolution_kind'],
    )
    status = 200 if response['ok'] else 400
    if response.get('error_code') == 'static_store_unavailable':
        status = 500
    if response.get('error_code') == 'static_write_failed':
        status = 500
    if response.get('error_code') == 'static_resource_unresolved':
        status = 409
    if response.get('error_code') == 'static_resource_outside_allowed_roots':
        status = 409
    return response, status


def _write_static_content(
    write_content: Any,
    *,
    subject: str,
    content: str,
    reason: str,
) -> Any:
    try:
        return write_content(
            subject,
            content,
            updated_by=contract.EDIT_UPDATED_BY,
            update_reason=reason,
        )
    except TypeError as exc:
        if 'unexpected keyword' not in str(exc) and 'positional arguments' not in str(exc):
            raise
        return write_content(subject, content)


def identity_static_edit_response(
    data: Mapping[str, Any],
    *,
    static_identity_content_module: Any,
    admin_logs_module: Any,
) -> Tuple[dict[str, Any], int]:
    payload = data if isinstance(data, Mapping) else {}
    raw_subject = contract.text(payload.get('subject')).lower()
    raw_action = contract.text(payload.get('action')).lower()
    reason = contract.text(payload.get('reason'))
    content = contract.raw_content(payload.get('content'))
    reason_len = len(reason)
    new_len = len(content) if raw_action == 'set' else 0

    subject = contract.normalize_subject(raw_subject)
    action = contract.normalize_action(raw_action)

    read_snapshot = getattr(static_identity_content_module, 'read_static_identity_snapshot', None)
    write_content = getattr(static_identity_content_module, 'write_static_identity_content', None)
    resource_field_for_subject = getattr(static_identity_content_module, 'resource_field_for_subject', lambda _s: '')
    if not callable(read_snapshot) or not callable(write_content):
        response = contract.response_payload(
            ok=False,
            subject=subject or raw_subject,
            action=action or raw_action,
            old_len=0,
            new_len=new_len,
            changed=False,
            stored_after=False,
            validation_ok=False,
            validation_error='static_store_unavailable',
            reason_code='static_store_unavailable',
            resource_field='',
            resolution_kind='unavailable',
            error='edition statique indisponible',
        )
        return _audit_and_return(admin_logs_module, response, reason_len=reason_len)

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
            resource_field='',
            resolution_kind='invalid_subject',
            error='subject invalide',
        )
        return _audit_and_return(admin_logs_module, response, reason_len=reason_len)

    try:
        current_snapshot = read_snapshot(subject)
    except Exception:
        response = contract.response_payload(
            ok=False,
            subject=subject,
            action=action or raw_action,
            old_len=0,
            new_len=new_len,
            changed=False,
            stored_after=False,
            validation_ok=False,
            validation_error='static_resource_unresolved',
            reason_code='static_resource_unresolved',
            resource_field=resource_field_for_subject(subject),
            resolution_kind='unresolved',
            error='ressource statique active introuvable',
        )
        return _audit_and_return(admin_logs_module, response, reason_len=reason_len)

    current_raw_content = str(getattr(current_snapshot, 'raw_content', current_snapshot.content or ''))
    old_len = len(current_raw_content)
    resource_field = current_snapshot.resource_field
    resolution_kind = current_snapshot.resolution_kind

    if current_snapshot.resolved_path is None:
        response = contract.response_payload(
            ok=False,
            subject=subject,
            action=action or raw_action,
            old_len=old_len,
            new_len=new_len,
            changed=False,
            stored_after=False,
            validation_ok=False,
            validation_error='static_resource_unresolved',
            reason_code='static_resource_unresolved',
            resource_field=resource_field,
            resolution_kind=resolution_kind,
            error='ressource statique active introuvable',
        )
        return _audit_and_return(admin_logs_module, response, reason_len=reason_len)
    if not bool(getattr(current_snapshot, 'within_allowed_roots', False)):
        response = contract.response_payload(
            ok=False,
            subject=subject,
            action=action or raw_action,
            old_len=0,
            new_len=new_len,
            changed=False,
            stored_after=False,
            validation_ok=False,
            validation_error='static_resource_outside_allowed_roots',
            reason_code='static_resource_outside_allowed_roots',
            resource_field=resource_field,
            resolution_kind=resolution_kind,
            error='ressource statique active hors perimetre autorise',
        )
        return _audit_and_return(admin_logs_module, response, reason_len=reason_len)

    if not action:
        response = contract.response_payload(
            ok=False,
            subject=subject,
            action=raw_action,
            old_len=old_len,
            new_len=new_len,
            changed=False,
            stored_after=bool(current_raw_content),
            validation_ok=False,
            validation_error='contract_action_invalid',
            reason_code='contract_action_invalid',
            resource_field=resource_field,
            resolution_kind=resolution_kind,
            error='action invalide',
        )
        return _audit_and_return(admin_logs_module, response, reason_len=reason_len)

    if not reason:
        response = contract.response_payload(
            ok=False,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=new_len,
            changed=False,
            stored_after=bool(current_raw_content),
            validation_ok=False,
            validation_error='contract_reason_missing',
            reason_code='contract_reason_missing',
            resource_field=resource_field,
            resolution_kind=resolution_kind,
            error='reason obligatoire',
        )
        return _audit_and_return(admin_logs_module, response, reason_len=reason_len)

    if reason_len > contract.REASON_MAX_CHARS:
        response = contract.response_payload(
            ok=False,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=new_len,
            changed=False,
            stored_after=bool(current_raw_content),
            validation_ok=False,
            validation_error='contract_reason_too_long',
            reason_code='contract_reason_too_long',
            resource_field=resource_field,
            resolution_kind=resolution_kind,
            error='reason trop longue',
        )
        return _audit_and_return(admin_logs_module, response, reason_len=reason_len)

    if action == 'clear' and content:
        response = contract.response_payload(
            ok=False,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=0,
            changed=False,
            stored_after=bool(current_raw_content),
            validation_ok=False,
            validation_error='contract_clear_has_content',
            reason_code='contract_clear_has_content',
            resource_field=resource_field,
            resolution_kind=resolution_kind,
            error='clear n accepte pas de contenu',
        )
        return _audit_and_return(admin_logs_module, response, reason_len=reason_len)

    if action == 'set' and not content:
        response = contract.response_payload(
            ok=False,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=0,
            changed=False,
            stored_after=bool(current_raw_content),
            validation_ok=False,
            validation_error='contract_set_missing_content',
            reason_code='contract_set_missing_content',
            resource_field=resource_field,
            resolution_kind=resolution_kind,
            error='content obligatoire pour set',
        )
        return _audit_and_return(admin_logs_module, response, reason_len=reason_len)

    if action == 'set' and current_raw_content == content:
        response = contract.response_payload(
            ok=True,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=len(content),
            changed=False,
            stored_after=bool(current_raw_content),
            validation_ok=True,
            validation_error=None,
            reason_code='unchanged',
            resource_field=resource_field,
            resolution_kind=resolution_kind,
        )
        return _audit_and_return(admin_logs_module, response, reason_len=reason_len)

    if action == 'clear' and not current_raw_content:
        response = contract.response_payload(
            ok=True,
            subject=subject,
            action=action,
            old_len=0,
            new_len=0,
            changed=False,
            stored_after=False,
            validation_ok=True,
            validation_error=None,
            reason_code='already_cleared',
            resource_field=resource_field,
            resolution_kind=resolution_kind,
        )
        return _audit_and_return(admin_logs_module, response, reason_len=reason_len)

    try:
        next_snapshot = _write_static_content(
            write_content,
            subject=subject,
            content='' if action == 'clear' else content,
            reason=reason,
        )
    except Exception as exc:
        error_code = getattr(exc, 'error_code', 'static_write_failed')
        response = contract.response_payload(
            ok=False,
            subject=subject,
            action=action,
            old_len=old_len,
            new_len=new_len,
            changed=False,
            stored_after=bool(current_raw_content),
            validation_ok=False,
            validation_error=error_code,
            reason_code=error_code,
            resource_field=resource_field,
            resolution_kind=resolution_kind,
            error=(
                'ressource statique active hors perimetre autorise'
                if error_code == 'static_resource_outside_allowed_roots'
                else 'ressource statique active introuvable'
                if error_code == 'static_resource_unresolved'
                else 'ecriture statique indisponible'
            ),
        )
        return _audit_and_return(admin_logs_module, response, reason_len=reason_len)

    next_raw_content = str(getattr(next_snapshot, 'raw_content', next_snapshot.content or ''))
    response = contract.response_payload(
        ok=True,
        subject=subject,
        action=action,
        old_len=old_len,
        new_len=len(next_raw_content),
        changed=True,
        stored_after=bool(next_raw_content),
        validation_ok=True,
        validation_error=None,
        reason_code='clear_applied' if action == 'clear' else 'set_applied',
        resource_field=next_snapshot.resource_field,
        resolution_kind=next_snapshot.resolution_kind,
    )
    return _audit_and_return(admin_logs_module, response, reason_len=reason_len)
