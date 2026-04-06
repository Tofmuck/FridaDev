from __future__ import annotations

from typing import Any, Mapping, Tuple

from admin import admin_identity_governance_audit as audit
from admin import admin_identity_governance_contract as contract
from admin import admin_identity_read_model_service
from identity import identity_governance


def _identity_input_schema_version(identity_module: Any) -> str:
    try:
        payload = identity_module.build_identity_input()
    except Exception:
        return 'v2'
    if isinstance(payload, Mapping):
        return str(payload.get('schema_version') or 'v2')
    return 'v2'


def _response_with_runtime(payload: dict[str, Any], *, identity_module: Any) -> dict[str, Any]:
    payload['active_prompt_contract'] = admin_identity_read_model_service.ACTIVE_PROMPT_CONTRACT
    payload['identity_input_schema_version'] = _identity_input_schema_version(identity_module)
    return payload


def _failed_validation_payload(
    *,
    identity_module: Any,
    validation_error: str,
    error: str,
    changed_keys: list[str] | None = None,
    failed_checks: list[str] | None = None,
) -> dict[str, Any]:
    return _response_with_runtime(
        contract.response_payload(
            ok=False,
            reason_code='governance_validation_failed',
            validation_ok=False,
            validation_error=validation_error,
            changed_keys=changed_keys or [],
            editable_via=identity_governance.UPDATE_ROUTE,
            source_of_truth=identity_governance.SOURCE_OF_TRUTH,
            error=error,
            failed_checks=failed_checks or [],
        ),
        identity_module=identity_module,
    )


def _audit_and_return(
    *,
    admin_logs_module: Any,
    identity_module: Any,
    response: dict[str, Any],
    changed_keys: list[str],
    old_values: Mapping[str, Any],
    new_values: Mapping[str, Any],
    reason_len: int,
) -> Tuple[dict[str, Any], int]:
    audit.log_compact_edit(
        admin_logs_module,
        changed_keys=changed_keys,
        old_values=old_values,
        new_values=new_values,
        validation_ok=response['validation_ok'],
        validation_error=response.get('validation_error'),
        reason_code=response['reason_code'],
        reason_len=reason_len,
        source_of_truth=response['source_of_truth'],
    )
    return _response_with_runtime(response, identity_module=identity_module), 200 if response['ok'] else 400


def identity_governance_response(
    _args: Mapping[str, Any],
    *,
    runtime_settings_module: Any,
    identity_module: Any,
) -> Tuple[dict[str, Any], int]:
    items = identity_governance.build_item_payloads(runtime_settings_module=runtime_settings_module)
    summary = identity_governance.summarize_items(items)
    return (
        _response_with_runtime(
            {
                'ok': True,
                'governance_version': identity_governance.GOVERNANCE_VERSION,
                'item_count': len(items),
                **summary,
                'read_via': identity_governance.READ_ROUTE,
                'editable_via': identity_governance.UPDATE_ROUTE,
                'source_of_truth': identity_governance.SOURCE_OF_TRUTH,
                'items': items,
            },
            identity_module=identity_module,
        ),
        200,
    )


def identity_governance_update_response(
    data: Mapping[str, Any],
    *,
    runtime_settings_module: Any,
    admin_logs_module: Any,
    identity_module: Any,
) -> Tuple[dict[str, Any], int]:
    payload = data if isinstance(data, Mapping) else {}
    reason = contract.text(payload.get('reason'))
    reason_len = len(reason)
    updates = contract.updates_mapping(payload.get('updates'))

    if not reason:
        response = _failed_validation_payload(
            identity_module=identity_module,
            validation_error='contract_reason_missing',
            error='reason obligatoire',
        )
        return _audit_and_return(
            admin_logs_module=admin_logs_module,
            identity_module=identity_module,
            response=response,
            changed_keys=[],
            old_values={},
            new_values={},
            reason_len=reason_len,
        )

    if reason_len > contract.REASON_MAX_CHARS:
        response = _failed_validation_payload(
            identity_module=identity_module,
            validation_error='contract_reason_too_long',
            error='reason trop longue',
        )
        return _audit_and_return(
            admin_logs_module=admin_logs_module,
            identity_module=identity_module,
            response=response,
            changed_keys=[],
            old_values={},
            new_values={},
            reason_len=reason_len,
        )

    if not updates:
        response = _failed_validation_payload(
            identity_module=identity_module,
            validation_error='governance_updates_missing',
            error='updates obligatoires',
        )
        return _audit_and_return(
            admin_logs_module=admin_logs_module,
            identity_module=identity_module,
            response=response,
            changed_keys=[],
            old_values={},
            new_values={},
            reason_len=reason_len,
        )

    for key in updates:
        if not contract.is_known_key(key):
            response = _failed_validation_payload(
                identity_module=identity_module,
                validation_error='governance_key_unknown',
                error=f'knob inconnu: {key}',
                failed_checks=[key],
            )
            return _audit_and_return(
                admin_logs_module=admin_logs_module,
                identity_module=identity_module,
                response=response,
                changed_keys=[],
                old_values={},
                new_values={},
                reason_len=reason_len,
            )
        if not contract.is_editable_key(key):
            response = _failed_validation_payload(
                identity_module=identity_module,
                validation_error='governance_key_readonly',
                error=f'knob non editable: {key}',
                failed_checks=[key],
            )
            return _audit_and_return(
                admin_logs_module=admin_logs_module,
                identity_module=identity_module,
                response=response,
                changed_keys=[],
                old_values={},
                new_values={},
                reason_len=reason_len,
            )

    patch_payload = contract.patch_payload(updates)
    try:
        validation = runtime_settings_module.validate_runtime_section(
            identity_governance.RUNTIME_SECTION,
            patch_payload=patch_payload,
        )
    except runtime_settings_module.RuntimeSettingsValidationError as exc:
        response = _failed_validation_payload(
            identity_module=identity_module,
            validation_error='governance_patch_invalid',
            error=str(exc),
        )
        return _audit_and_return(
            admin_logs_module=admin_logs_module,
            identity_module=identity_module,
            response=response,
            changed_keys=[],
            old_values={},
            new_values={},
            reason_len=reason_len,
        )

    failed_checks = [check['name'] for check in validation['checks'] if not check.get('ok')]
    if failed_checks:
        response = _failed_validation_payload(
            identity_module=identity_module,
            validation_error=failed_checks[0],
            error='validation gouvernance invalide',
            failed_checks=failed_checks,
        )
        return _audit_and_return(
            admin_logs_module=admin_logs_module,
            identity_module=identity_module,
            response=response,
            changed_keys=[],
            old_values={},
            new_values={},
            reason_len=reason_len,
        )

    current_view = runtime_settings_module.get_identity_governance_settings()
    current_values = identity_governance.editable_values_from_view(current_view)
    changed_keys = [
        key for key, next_value in updates.items()
        if current_values.get(key) != next_value
    ]
    old_values = {key: current_values.get(key) for key in changed_keys}
    new_values = {key: updates[key] for key in changed_keys}

    if not changed_keys:
        response = contract.response_payload(
            ok=True,
            reason_code='unchanged',
            validation_ok=True,
            validation_error=None,
            changed_keys=[],
            editable_via=identity_governance.UPDATE_ROUTE,
            source_of_truth=identity_governance.SOURCE_OF_TRUTH,
        )
        return _audit_and_return(
            admin_logs_module=admin_logs_module,
            identity_module=identity_module,
            response=response,
            changed_keys=[],
            old_values={},
            new_values={},
            reason_len=reason_len,
        )

    try:
        updated_view = runtime_settings_module.update_runtime_section(
            identity_governance.RUNTIME_SECTION,
            patch_payload,
            updated_by='identity_governance_admin',
        )
    except runtime_settings_module.RuntimeSettingsValidationError as exc:
        response = _failed_validation_payload(
            identity_module=identity_module,
            validation_error='governance_patch_invalid',
            error=str(exc),
        )
        return _audit_and_return(
            admin_logs_module=admin_logs_module,
            identity_module=identity_module,
            response=response,
            changed_keys=[],
            old_values={},
            new_values={},
            reason_len=reason_len,
        )
    except runtime_settings_module.RuntimeSettingsDbUnavailableError as exc:
        response = contract.response_payload(
            ok=False,
            reason_code='governance_store_unavailable',
            validation_ok=False,
            validation_error='governance_store_unavailable',
            changed_keys=[],
            editable_via=identity_governance.UPDATE_ROUTE,
            source_of_truth=identity_governance.SOURCE_OF_TRUTH,
            error=str(exc),
        )
        return _audit_and_return(
            admin_logs_module=admin_logs_module,
            identity_module=identity_module,
            response=_response_with_runtime(response, identity_module=identity_module),
            changed_keys=[],
            old_values={},
            new_values={},
            reason_len=reason_len,
        )

    persisted_values = identity_governance.editable_values_from_view(updated_view)
    response = contract.response_payload(
        ok=True,
        reason_code='update_applied',
        validation_ok=True,
        validation_error=None,
        changed_keys=changed_keys,
        editable_via=identity_governance.UPDATE_ROUTE,
        source_of_truth=identity_governance.SOURCE_OF_TRUTH,
    )
    return _audit_and_return(
        admin_logs_module=admin_logs_module,
        identity_module=identity_module,
        response=response,
        changed_keys=changed_keys,
        old_values=old_values,
        new_values={key: persisted_values.get(key) for key in changed_keys},
        reason_len=reason_len,
    )
