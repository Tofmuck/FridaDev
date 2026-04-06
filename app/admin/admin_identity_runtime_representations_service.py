from __future__ import annotations

from typing import Any, Mapping, Tuple

from admin import admin_identity_read_model_service


REPRESENTATIONS_VERSION = 'v1'
READ_ROUTE = '/api/admin/identity/runtime-representations'


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def identity_runtime_representations_response(
    *,
    identity_module: Any,
) -> Tuple[dict[str, Any], int]:
    try:
        structured_identity = identity_module.build_identity_input()
        injected_identity_text, used_identity_ids = identity_module.build_identity_block()
    except Exception as exc:
        return (
            {
                'ok': False,
                'error': 'lecture identity runtime indisponible',
                'error_code': 'identity_runtime_representations_unavailable',
                'error_class': exc.__class__.__name__,
            },
            500,
        )

    structured_mapping = dict(_mapping(structured_identity))
    used_identity_ids_list = list(used_identity_ids or [])
    structured_schema_version = str(structured_mapping.get('schema_version') or 'v2')
    injected_text = str(injected_identity_text or '')

    return (
        {
            'ok': True,
            'representations_version': REPRESENTATIONS_VERSION,
            'read_via': READ_ROUTE,
            'active_prompt_contract': admin_identity_read_model_service.ACTIVE_PROMPT_CONTRACT,
            'active_identity_source': admin_identity_read_model_service.ACTIVE_IDENTITY_SOURCE,
            'identity_input_schema_version': structured_schema_version,
            'same_identity_basis': True,
            'structured_identity': {
                'technical_name': 'identity_input',
                'role': 'hermeneutic_judgment',
                'present': bool(structured_mapping),
                'schema_version': structured_schema_version,
                'data': structured_mapping,
            },
            'injected_identity_text': {
                'technical_name': 'identity_block',
                'role': 'final_model_system_prompt',
                'present': bool(injected_text.strip()),
                'content': injected_text,
            },
            'used_identity_ids': used_identity_ids_list,
            'used_identity_ids_count': len(used_identity_ids_list),
        },
        200,
    )
