from __future__ import annotations

from collections.abc import Iterable


RouteContract = tuple[str, tuple[str, ...], str, str, str]

PUBLIC_AUTHENTICATED = 'public_authenticated'
ADMIN_PROXY_OR_LOOPBACK = 'admin_proxy_identity_or_loopback'
GUARDED_TOOL_PROXY_OR_LOOPBACK = 'guarded_tool_proxy_identity_or_loopback'


def _row(
    path: str,
    methods: str,
    endpoint: str,
    family: str,
    guard: str = PUBLIC_AUTHENTICATED,
) -> RouteContract:
    return path, tuple(sorted(methods.split(','))), endpoint, family, guard


def _settings_rows() -> list[RouteContract]:
    rows = [
        _row('/api/admin/settings', 'GET', 'api_admin_settings', 'admin_settings', ADMIN_PROXY_OR_LOOPBACK),
        _row(
            '/api/admin/settings/status',
            'GET',
            'api_admin_settings_status',
            'admin_settings',
            ADMIN_PROXY_OR_LOOPBACK,
        ),
        _row(
            '/api/admin/settings/<section_route>/readonly-info/<key>/content',
            'POST',
            'api_admin_settings_readonly_content',
            'admin_settings',
            ADMIN_PROXY_OR_LOOPBACK,
        ),
    ]
    sections = (
        ('agenda-agent', 'agenda_agent'),
        ('arbiter-model', 'arbiter_model'),
        ('database', 'database'),
        ('embedding', 'embedding'),
        ('identity-extractor-model', 'identity_extractor_model'),
        ('identity-periodic-model', 'identity_periodic_model'),
        ('main-model', 'main_model'),
        ('memory-arbiter-model', 'memory_arbiter_model'),
        ('resources', 'resources'),
        ('services', 'services'),
        ('stimmung-agent-model', 'stimmung_agent_model'),
        ('summary-model', 'summary_model'),
        ('validation-agent-model', 'validation_agent_model'),
        ('web-reformulation-model', 'web_reformulation_model'),
    )
    for route_name, endpoint_name in sections:
        path = f'/api/admin/settings/{route_name}'
        rows.extend(
            (
                _row(path, 'GET', f'api_admin_settings_{endpoint_name}_get', 'admin_settings', ADMIN_PROXY_OR_LOOPBACK),
                _row(path, 'PATCH', f'api_admin_settings_{endpoint_name}_patch', 'admin_settings', ADMIN_PROXY_OR_LOOPBACK),
                _row(
                    f'{path}/validate',
                    'POST',
                    f'api_admin_settings_{endpoint_name}_validate',
                    'admin_settings',
                    ADMIN_PROXY_OR_LOOPBACK,
                ),
            )
        )
    return rows


def _expected_rows() -> list[RouteContract]:
    rows = [
        _row('/', 'GET', 'root', 'health_and_technical_surfaces'),
        _row('/admin', 'GET', 'admin_root', 'health_and_technical_surfaces'),
        _row('/dashboard', 'GET', 'dashboard_root', 'health_and_technical_surfaces'),
        _row('/hermeneutic-admin', 'GET', 'hermeneutic_admin_root', 'health_and_technical_surfaces'),
        _row('/identity', 'GET', 'identity_root', 'health_and_technical_surfaces'),
        _row('/log', 'GET', 'log_root', 'health_and_technical_surfaces'),
        _row('/memory-admin', 'GET', 'memory_admin_root', 'health_and_technical_surfaces'),
        _row('/api/chat', 'POST', 'api_chat', 'chat_and_transcription'),
        _row('/api/chat/transcribe', 'POST', 'api_chat_transcribe', 'chat_and_transcription'),
        _row(
            '/api/tools/image-generation',
            'POST',
            'api_tools_image_generation',
            'guarded_tools',
            GUARDED_TOOL_PROXY_OR_LOOPBACK,
        ),
        _row('/api/conversations', 'GET', 'api_list_conversations', 'conversations_documents_workspace'),
        _row('/api/conversations', 'POST', 'api_create_conversation', 'conversations_documents_workspace'),
        _row('/api/conversations/<conversation_id>', 'DELETE', 'api_delete_conversation', 'conversations_documents_workspace'),
        _row('/api/conversations/<conversation_id>', 'PATCH', 'api_patch_conversation', 'conversations_documents_workspace'),
        _row(
            '/api/conversations/<conversation_id>/messages',
            'GET',
            'api_get_conversation_messages',
            'conversations_documents_workspace',
        ),
        _row(
            '/api/conversations/<conversation_id>/workspace-file-selections',
            'GET',
            'api_list_workspace_file_selections',
            'conversations_documents_workspace',
        ),
        _row(
            '/api/conversations/<conversation_id>/workspace-file-selections',
            'POST',
            'api_select_workspace_file',
            'conversations_documents_workspace',
        ),
        _row(
            '/api/conversations/<conversation_id>/workspace-file-selections/<file_id>',
            'DELETE',
            'api_deselect_workspace_file',
            'conversations_documents_workspace',
        ),
        _row(
            '/api/conversations/<conversation_id>/active-documents',
            'GET',
            'api_list_active_conversation_documents',
            'conversations_documents_workspace',
        ),
        _row(
            '/api/conversations/<conversation_id>/active-documents',
            'POST',
            'api_upload_active_conversation_document',
            'conversations_documents_workspace',
        ),
        _row(
            '/api/conversations/<conversation_id>/active-documents/<document_id>',
            'DELETE',
            'api_remove_active_conversation_document',
            'conversations_documents_workspace',
        ),
        _row('/api/workspace-folders', 'GET', 'api_list_workspace_folders', 'conversations_documents_workspace'),
        _row('/api/workspace-folders', 'POST', 'api_create_workspace_folder', 'conversations_documents_workspace'),
        _row('/api/workspace-folders/<folder_id>', 'DELETE', 'api_delete_workspace_folder', 'conversations_documents_workspace'),
        _row('/api/workspace-folders/<folder_id>', 'PATCH', 'api_patch_workspace_folder', 'conversations_documents_workspace'),
    ]
    workspace_rows = (
        ('/api/workspace-folders/<folder_id>/files', 'GET', 'api_list_workspace_folder_files'),
        ('/api/workspace-folders/<folder_id>/files', 'POST', 'api_upload_workspace_folder_file'),
        ('/api/workspace-folders/<folder_id>/files/<file_id>', 'DELETE', 'api_delete_workspace_folder_file'),
        ('/api/workspace-folders/<folder_id>/files/<file_id>/ocr', 'POST', 'api_ocr_workspace_folder_file'),
        ('/api/workspace-folders/<folder_id>/files/<file_id>/ocr-markdown', 'GET', 'api_get_workspace_folder_file_ocr_markdown'),
        ('/api/workspace-folders/<folder_id>/files/<file_id>/ocr-markdown', 'PATCH', 'api_patch_workspace_folder_file_ocr_markdown'),
        ('/api/workspace-folders/<folder_id>/notes', 'GET', 'api_list_workspace_folder_notes'),
        ('/api/workspace-folders/<folder_id>/notes', 'POST', 'api_create_workspace_folder_note'),
        ('/api/workspace-folders/<folder_id>/notes/lookup', 'GET', 'api_lookup_workspace_folder_note'),
        ('/api/workspace-folders/<folder_id>/notes/<note_id>', 'GET', 'api_get_workspace_folder_note'),
        ('/api/workspace-folders/<folder_id>/notes/<note_id>/append', 'POST', 'api_append_workspace_folder_note'),
        ('/api/workspace-folders/<folder_id>/notes/<note_id>/prepare', 'POST', 'api_prepare_workspace_folder_note'),
        ('/api/workspace-folders/<folder_id>/exports', 'GET', 'api_list_workspace_folder_exports'),
        ('/api/workspace-folders/<folder_id>/exports', 'POST', 'api_create_workspace_folder_export'),
        ('/api/workspace-folders/<folder_id>/exports/<export_id>', 'GET', 'api_get_workspace_folder_export'),
        ('/api/workspace-folders/<folder_id>/exports/<export_id>/download', 'GET', 'api_download_workspace_folder_export'),
        ('/api/workspace-folders/<folder_id>/exports/<export_id>/open', 'GET', 'api_open_workspace_folder_export'),
        ('/api/workspace-folders/<folder_id>/generated-images', 'GET', 'api_list_workspace_folder_generated_images'),
        ('/api/workspace-folders/<folder_id>/generated-images', 'POST', 'api_create_workspace_folder_generated_image'),
        ('/api/workspace-folders/<folder_id>/generated-images/<image_id>', 'DELETE', 'api_delete_workspace_folder_generated_image'),
        ('/api/workspace-folders/<folder_id>/generated-images/<image_id>', 'GET', 'api_get_workspace_folder_generated_image'),
        ('/api/workspace-folders/<folder_id>/generated-images/<image_id>/download', 'GET', 'api_download_workspace_folder_generated_image'),
        ('/api/workspace-folders/<folder_id>/generated-images/<image_id>/open', 'GET', 'api_open_workspace_folder_generated_image'),
    )
    rows.extend(_row(path, methods, endpoint, 'conversations_documents_workspace') for path, methods, endpoint in workspace_rows)

    admin_rows = (
        ('/api/admin/logs', 'GET', 'api_admin_logs', 'admin_logs_dashboard'),
        ('/api/admin/logs/chat', 'DELETE', 'api_admin_chat_logs_delete', 'admin_logs_dashboard'),
        ('/api/admin/logs/chat', 'GET', 'api_admin_chat_logs', 'admin_logs_dashboard'),
        ('/api/admin/logs/chat/export.md', 'GET', 'api_admin_chat_logs_export_markdown', 'admin_logs_dashboard'),
        ('/api/admin/logs/chat/metadata', 'GET', 'api_admin_chat_logs_metadata', 'admin_logs_dashboard'),
        ('/api/admin/logs/chat/metrics', 'GET', 'api_admin_chat_logs_metrics', 'admin_logs_dashboard'),
        ('/api/admin/logs/chat/turns', 'GET', 'api_admin_chat_log_turns', 'admin_logs_dashboard'),
        ('/api/admin/dashboard/overview', 'GET', 'api_admin_dashboard_overview', 'admin_logs_dashboard'),
        ('/api/admin/dashboard/conversations', 'GET', 'api_admin_dashboard_conversations', 'admin_logs_dashboard'),
        ('/api/admin/dashboard/conversations/<conversation_id>/turns', 'GET', 'api_admin_dashboard_conversation_turns', 'admin_logs_dashboard'),
        ('/api/admin/dashboard/turns/<turn_id>/inspection', 'GET', 'api_admin_dashboard_turn_inspection', 'admin_logs_dashboard'),
        ('/api/admin/dashboard/turns/<turn_id>/content', 'GET', 'api_admin_dashboard_turn_content', 'admin_logs_dashboard'),
        ('/api/admin/agenda/observability', 'GET', 'api_admin_agenda_observability', 'biblio_agenda'),
        ('/api/admin/biblio/observability', 'GET', 'api_admin_biblio_observability', 'biblio_agenda'),
        ('/api/admin/memory/dashboard', 'GET', 'api_admin_memory_dashboard', 'admin_identity_memory_hermeneutics'),
        ('/api/admin/restart', 'POST', 'api_admin_restart', 'admin_identity_memory_hermeneutics'),
        ('/api/admin/hermeneutics/arbiter-decisions', 'GET', 'api_admin_hermeneutics_arbiter_decisions', 'admin_identity_memory_hermeneutics'),
        ('/api/admin/hermeneutics/corrections-export', 'GET', 'api_admin_hermeneutics_corrections_export', 'admin_identity_memory_hermeneutics'),
        ('/api/admin/hermeneutics/dashboard', 'GET', 'api_admin_hermeneutics_dashboard', 'admin_identity_memory_hermeneutics'),
        ('/api/admin/hermeneutics/identity-candidates', 'GET', 'api_admin_hermeneutics_identity_candidates', 'admin_identity_memory_hermeneutics'),
        ('/api/admin/hermeneutics/identity/force-accept', 'POST', 'api_admin_hermeneutics_identity_force_accept', 'admin_identity_memory_hermeneutics'),
        ('/api/admin/hermeneutics/identity/force-reject', 'POST', 'api_admin_hermeneutics_identity_force_reject', 'admin_identity_memory_hermeneutics'),
        ('/api/admin/hermeneutics/identity/relabel', 'POST', 'api_admin_hermeneutics_identity_relabel', 'admin_identity_memory_hermeneutics'),
        ('/api/admin/identity/governance', 'GET', 'api_admin_identity_governance', 'admin_identity_memory_hermeneutics'),
        ('/api/admin/identity/governance', 'POST', 'api_admin_identity_governance_update', 'admin_identity_memory_hermeneutics'),
        ('/api/admin/identity/mutable', 'POST', 'api_admin_identity_mutable_edit', 'admin_identity_memory_hermeneutics'),
        ('/api/admin/identity/read-model', 'GET', 'api_admin_identity_read_model', 'admin_identity_memory_hermeneutics'),
        ('/api/admin/identity/runtime-representations', 'GET', 'api_admin_identity_runtime_representations', 'admin_identity_memory_hermeneutics'),
        ('/api/admin/identity/static', 'POST', 'api_admin_identity_static_edit', 'admin_identity_memory_hermeneutics'),
    )
    rows.extend(
        _row(path, methods, endpoint, family, ADMIN_PROXY_OR_LOOPBACK)
        for path, methods, endpoint, family in admin_rows
    )
    rows.extend(_settings_rows())
    return rows


EXPECTED_ROUTE_CONTRACTS = tuple(sorted(_expected_rows()))


def classify_family(path: str) -> str:
    if path.startswith('/api/admin/settings'):
        return 'admin_settings'
    if path.startswith('/api/admin/logs') or path.startswith('/api/admin/dashboard'):
        return 'admin_logs_dashboard'
    if path.startswith('/api/admin/agenda') or path.startswith('/api/admin/biblio'):
        return 'biblio_agenda'
    if path.startswith('/api/admin/'):
        return 'admin_identity_memory_hermeneutics'
    if path.startswith('/api/chat'):
        return 'chat_and_transcription'
    if path.startswith('/api/tools/'):
        return 'guarded_tools'
    if path.startswith('/api/conversations') or path.startswith('/api/workspace-folders'):
        return 'conversations_documents_workspace'
    return 'health_and_technical_surfaces'


def classify_guard(path: str) -> str:
    if path.startswith('/api/admin/'):
        return ADMIN_PROXY_OR_LOOPBACK
    if path == '/api/tools/image-generation':
        return GUARDED_TOOL_PROXY_OR_LOOPBACK
    return PUBLIC_AUTHENTICATED


def route_contracts_from_app(app) -> tuple[RouteContract, ...]:
    rows = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint == 'static':
            continue
        path = str(rule.rule)
        methods = tuple(sorted(method for method in rule.methods if method not in {'HEAD', 'OPTIONS'}))
        rows.append((path, methods, str(rule.endpoint), classify_family(path), classify_guard(path)))
    return tuple(sorted(rows))


def assert_exact_route_contract(
    actual: Iterable[RouteContract],
    expected: Iterable[RouteContract] = EXPECTED_ROUTE_CONTRACTS,
) -> None:
    actual_rows = tuple(sorted(actual))
    expected_rows = tuple(sorted(expected))
    if actual_rows == expected_rows:
        return
    missing = sorted(set(expected_rows) - set(actual_rows))
    unexpected = sorted(set(actual_rows) - set(expected_rows))
    raise AssertionError(
        f'route contract mismatch missing={len(missing)} unexpected={len(unexpected)}'
    )
