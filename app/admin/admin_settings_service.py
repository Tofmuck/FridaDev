from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple


def section_response(section: str, *, runtime_settings_module: Any) -> Dict[str, Any]:
    view = runtime_settings_module.get_runtime_section_for_api(section)
    return {
        'section': section,
        'payload': view.payload,
        'readonly_info': runtime_settings_module.get_section_readonly_info(section),
        'secret_sources': runtime_settings_module.describe_secret_sources(section, view.payload),
        'source': view.source,
        'source_reason': view.source_reason,
    }


def single_section_response(section: str, *, runtime_settings_module: Any) -> Dict[str, Any]:
    return {'ok': True, **section_response(section, runtime_settings_module=runtime_settings_module)}


def aggregated_settings_response(*, runtime_settings_module: Any) -> Dict[str, Any]:
    sections = {
        section: section_response(section, runtime_settings_module=runtime_settings_module)
        for section in runtime_settings_module.list_sections()
    }
    return {'ok': True, 'sections': sections}


def settings_status_response(*, runtime_settings_module: Any) -> Dict[str, Any]:
    status = runtime_settings_module.get_runtime_status()
    return {'ok': True, **status}


def patch_section_response(
    section: str,
    data: Any,
    *,
    runtime_settings_module: Any,
) -> Tuple[Dict[str, Any], int]:
    if not isinstance(data, Mapping):
        return {'ok': False, 'error': 'patch request must be a mapping'}, 400
    if 'readonly_info' in data:
        return {'ok': False, 'error': 'readonly_info is read-only and cannot be patched'}, 400
    patch_payload = data.get('payload')
    if isinstance(patch_payload, Mapping) and 'readonly_info' in patch_payload:
        return {'ok': False, 'error': 'readonly_info is read-only and cannot be patched'}, 400
    updated_by = str(data.get('updated_by') or 'admin_api').strip() or 'admin_api'

    try:
        view = runtime_settings_module.update_runtime_section(
            section,
            patch_payload,
            updated_by=updated_by,
        )
    except runtime_settings_module.RuntimeSettingsValidationError as exc:
        return {'ok': False, 'error': str(exc)}, 400
    except runtime_settings_module.RuntimeSettingsDbUnavailableError as exc:
        return {'ok': False, 'error': str(exc)}, 503

    return (
        {
            'ok': True,
            'section': view.section,
            'payload': view.payload,
            'readonly_info': runtime_settings_module.get_section_readonly_info(section),
            'secret_sources': runtime_settings_module.describe_secret_sources(section, view.payload),
            'source': view.source,
            'source_reason': view.source_reason,
        },
        200,
    )


def validate_section_response(
    section: str,
    data: Any,
    *,
    runtime_settings_module: Any,
) -> Tuple[Dict[str, Any], int]:
    if data is None:
        patch_payload = None
    else:
        if not isinstance(data, Mapping):
            return {'ok': False, 'error': 'validation payload must be a mapping'}, 400
        patch_payload = data.get('payload')
        if patch_payload is not None and not isinstance(patch_payload, Mapping):
            return {'ok': False, 'error': 'validation payload must be a mapping'}, 400

    try:
        result = runtime_settings_module.validate_runtime_section(section, patch_payload=patch_payload)
    except runtime_settings_module.RuntimeSettingsValidationError as exc:
        return {'ok': False, 'error': str(exc)}, 400

    return {'ok': True, **result}, 200
