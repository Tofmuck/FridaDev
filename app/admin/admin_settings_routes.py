from __future__ import annotations

from flask import Flask, jsonify, request

from admin import admin_settings_service, runtime_settings


_ADMIN_SETTINGS_PREFIX = '/api/admin/settings'
_ADMIN_SETTINGS_ROUTE_SECTIONS = {
    'main-model': 'main_model',
    'arbiter-model': 'arbiter_model',
    'identity-extractor-model': 'identity_extractor_model',
    'identity-periodic-model': 'identity_periodic_model',
    'memory-arbiter-model': 'memory_arbiter_model',
    'summary-model': 'summary_model',
    'web-reformulation-model': 'web_reformulation_model',
    'stimmung-agent-model': 'stimmung_agent_model',
    'validation-agent-model': 'validation_agent_model',
    'agenda-agent': 'agenda_agent',
    'embedding': 'embedding',
    'database': 'database',
    'services': 'services',
    'resources': 'resources',
}


def _admin_settings_single_section_json(section: str):
    return jsonify(
        admin_settings_service.single_section_response(
            section,
            runtime_settings_module=runtime_settings,
        )
    )


def _admin_settings_status_json():
    return jsonify(
        admin_settings_service.settings_status_response(
            runtime_settings_module=runtime_settings,
        )
    )


def _admin_settings_section_patch_response(section: str):
    data = request.get_json(force=True, silent=True) or {}
    payload, status = admin_settings_service.patch_section_response(
        section,
        data,
        runtime_settings_module=runtime_settings,
    )
    return jsonify(payload), status


def _admin_settings_section_validate_response(section: str):
    data = request.get_json(force=True, silent=True)
    payload, status = admin_settings_service.validate_section_response(
        section,
        data,
        runtime_settings_module=runtime_settings,
    )
    return jsonify(payload), status


def _admin_settings_section_readonly_content_response(section: str, key: str):
    data = request.get_json(force=True, silent=True)
    payload, status = admin_settings_service.readonly_info_content_response(
        section,
        key,
        data,
        runtime_settings_module=runtime_settings,
    )
    return jsonify(payload), status


def api_admin_settings():
    return jsonify(
        admin_settings_service.aggregated_settings_response(
            runtime_settings_module=runtime_settings,
        )
    )


def api_admin_settings_status():
    return _admin_settings_status_json()


def api_admin_settings_main_model_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['main-model'])


def api_admin_settings_arbiter_model_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['arbiter-model'])


def api_admin_settings_identity_extractor_model_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['identity-extractor-model'])


def api_admin_settings_identity_periodic_model_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['identity-periodic-model'])


def api_admin_settings_memory_arbiter_model_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['memory-arbiter-model'])


def api_admin_settings_summary_model_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['summary-model'])


def api_admin_settings_web_reformulation_model_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['web-reformulation-model'])


def api_admin_settings_stimmung_agent_model_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['stimmung-agent-model'])


def api_admin_settings_validation_agent_model_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['validation-agent-model'])


def api_admin_settings_agenda_agent_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['agenda-agent'])


def api_admin_settings_embedding_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['embedding'])


def api_admin_settings_database_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['database'])


def api_admin_settings_services_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['services'])


def api_admin_settings_resources_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['resources'])


def api_admin_settings_resources_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['resources'])


def api_admin_settings_services_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['services'])


def api_admin_settings_database_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['database'])


def api_admin_settings_embedding_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['embedding'])


def api_admin_settings_summary_model_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['summary-model'])


def api_admin_settings_web_reformulation_model_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['web-reformulation-model'])


def api_admin_settings_stimmung_agent_model_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['stimmung-agent-model'])


def api_admin_settings_validation_agent_model_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['validation-agent-model'])


def api_admin_settings_agenda_agent_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['agenda-agent'])


def api_admin_settings_arbiter_model_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['arbiter-model'])


def api_admin_settings_identity_extractor_model_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['identity-extractor-model'])


def api_admin_settings_identity_periodic_model_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['identity-periodic-model'])


def api_admin_settings_memory_arbiter_model_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['memory-arbiter-model'])


def api_admin_settings_main_model_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['main-model'])


def api_admin_settings_main_model_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['main-model'])


def api_admin_settings_arbiter_model_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['arbiter-model'])


def api_admin_settings_identity_extractor_model_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['identity-extractor-model'])


def api_admin_settings_identity_periodic_model_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['identity-periodic-model'])


def api_admin_settings_memory_arbiter_model_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['memory-arbiter-model'])


def api_admin_settings_summary_model_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['summary-model'])


def api_admin_settings_web_reformulation_model_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['web-reformulation-model'])


def api_admin_settings_stimmung_agent_model_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['stimmung-agent-model'])


def api_admin_settings_validation_agent_model_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['validation-agent-model'])


def api_admin_settings_agenda_agent_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['agenda-agent'])


def api_admin_settings_embedding_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['embedding'])


def api_admin_settings_database_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['database'])


def api_admin_settings_services_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['services'])


def api_admin_settings_resources_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['resources'])


def api_admin_settings_readonly_content(section_route: str, key: str):
    section = _ADMIN_SETTINGS_ROUTE_SECTIONS.get(section_route)
    if not section:
        return jsonify({
            'ok': False,
            'error': 'unknown runtime settings section',
            'section_route': section_route,
        }), 404
    return _admin_settings_section_readonly_content_response(section, key)


_ADMIN_SETTINGS_ROUTE_REGISTRATIONS = (
    (_ADMIN_SETTINGS_PREFIX, 'api_admin_settings', api_admin_settings, ('GET',)),
    (f'{_ADMIN_SETTINGS_PREFIX}/status', 'api_admin_settings_status', api_admin_settings_status, ('GET',)),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/main-model',
        'api_admin_settings_main_model_get',
        api_admin_settings_main_model_get,
        ('GET',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/arbiter-model',
        'api_admin_settings_arbiter_model_get',
        api_admin_settings_arbiter_model_get,
        ('GET',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/identity-extractor-model',
        'api_admin_settings_identity_extractor_model_get',
        api_admin_settings_identity_extractor_model_get,
        ('GET',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/identity-periodic-model',
        'api_admin_settings_identity_periodic_model_get',
        api_admin_settings_identity_periodic_model_get,
        ('GET',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/memory-arbiter-model',
        'api_admin_settings_memory_arbiter_model_get',
        api_admin_settings_memory_arbiter_model_get,
        ('GET',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/summary-model',
        'api_admin_settings_summary_model_get',
        api_admin_settings_summary_model_get,
        ('GET',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/web-reformulation-model',
        'api_admin_settings_web_reformulation_model_get',
        api_admin_settings_web_reformulation_model_get,
        ('GET',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/stimmung-agent-model',
        'api_admin_settings_stimmung_agent_model_get',
        api_admin_settings_stimmung_agent_model_get,
        ('GET',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/validation-agent-model',
        'api_admin_settings_validation_agent_model_get',
        api_admin_settings_validation_agent_model_get,
        ('GET',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/agenda-agent',
        'api_admin_settings_agenda_agent_get',
        api_admin_settings_agenda_agent_get,
        ('GET',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/embedding',
        'api_admin_settings_embedding_get',
        api_admin_settings_embedding_get,
        ('GET',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/database',
        'api_admin_settings_database_get',
        api_admin_settings_database_get,
        ('GET',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/services',
        'api_admin_settings_services_get',
        api_admin_settings_services_get,
        ('GET',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/resources',
        'api_admin_settings_resources_get',
        api_admin_settings_resources_get,
        ('GET',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/resources',
        'api_admin_settings_resources_patch',
        api_admin_settings_resources_patch,
        ('PATCH',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/services',
        'api_admin_settings_services_patch',
        api_admin_settings_services_patch,
        ('PATCH',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/database',
        'api_admin_settings_database_patch',
        api_admin_settings_database_patch,
        ('PATCH',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/embedding',
        'api_admin_settings_embedding_patch',
        api_admin_settings_embedding_patch,
        ('PATCH',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/summary-model',
        'api_admin_settings_summary_model_patch',
        api_admin_settings_summary_model_patch,
        ('PATCH',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/web-reformulation-model',
        'api_admin_settings_web_reformulation_model_patch',
        api_admin_settings_web_reformulation_model_patch,
        ('PATCH',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/stimmung-agent-model',
        'api_admin_settings_stimmung_agent_model_patch',
        api_admin_settings_stimmung_agent_model_patch,
        ('PATCH',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/validation-agent-model',
        'api_admin_settings_validation_agent_model_patch',
        api_admin_settings_validation_agent_model_patch,
        ('PATCH',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/agenda-agent',
        'api_admin_settings_agenda_agent_patch',
        api_admin_settings_agenda_agent_patch,
        ('PATCH',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/arbiter-model',
        'api_admin_settings_arbiter_model_patch',
        api_admin_settings_arbiter_model_patch,
        ('PATCH',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/identity-extractor-model',
        'api_admin_settings_identity_extractor_model_patch',
        api_admin_settings_identity_extractor_model_patch,
        ('PATCH',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/identity-periodic-model',
        'api_admin_settings_identity_periodic_model_patch',
        api_admin_settings_identity_periodic_model_patch,
        ('PATCH',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/memory-arbiter-model',
        'api_admin_settings_memory_arbiter_model_patch',
        api_admin_settings_memory_arbiter_model_patch,
        ('PATCH',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/main-model',
        'api_admin_settings_main_model_patch',
        api_admin_settings_main_model_patch,
        ('PATCH',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/main-model/validate',
        'api_admin_settings_main_model_validate',
        api_admin_settings_main_model_validate,
        ('POST',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/arbiter-model/validate',
        'api_admin_settings_arbiter_model_validate',
        api_admin_settings_arbiter_model_validate,
        ('POST',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/identity-extractor-model/validate',
        'api_admin_settings_identity_extractor_model_validate',
        api_admin_settings_identity_extractor_model_validate,
        ('POST',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/identity-periodic-model/validate',
        'api_admin_settings_identity_periodic_model_validate',
        api_admin_settings_identity_periodic_model_validate,
        ('POST',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/memory-arbiter-model/validate',
        'api_admin_settings_memory_arbiter_model_validate',
        api_admin_settings_memory_arbiter_model_validate,
        ('POST',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/summary-model/validate',
        'api_admin_settings_summary_model_validate',
        api_admin_settings_summary_model_validate,
        ('POST',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/web-reformulation-model/validate',
        'api_admin_settings_web_reformulation_model_validate',
        api_admin_settings_web_reformulation_model_validate,
        ('POST',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/stimmung-agent-model/validate',
        'api_admin_settings_stimmung_agent_model_validate',
        api_admin_settings_stimmung_agent_model_validate,
        ('POST',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/validation-agent-model/validate',
        'api_admin_settings_validation_agent_model_validate',
        api_admin_settings_validation_agent_model_validate,
        ('POST',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/agenda-agent/validate',
        'api_admin_settings_agenda_agent_validate',
        api_admin_settings_agenda_agent_validate,
        ('POST',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/embedding/validate',
        'api_admin_settings_embedding_validate',
        api_admin_settings_embedding_validate,
        ('POST',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/database/validate',
        'api_admin_settings_database_validate',
        api_admin_settings_database_validate,
        ('POST',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/services/validate',
        'api_admin_settings_services_validate',
        api_admin_settings_services_validate,
        ('POST',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/resources/validate',
        'api_admin_settings_resources_validate',
        api_admin_settings_resources_validate,
        ('POST',),
    ),
    (
        f'{_ADMIN_SETTINGS_PREFIX}/<section_route>/readonly-info/<key>/content',
        'api_admin_settings_readonly_content',
        api_admin_settings_readonly_content,
        ('POST',),
    ),
)


def register_admin_settings_routes(app: Flask) -> None:
    for rule, endpoint, view_func, methods in _ADMIN_SETTINGS_ROUTE_REGISTRATIONS:
        app.add_url_rule(
            rule,
            endpoint=endpoint,
            view_func=view_func,
            methods=list(methods),
        )
