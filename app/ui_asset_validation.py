from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ui_admin_dom_validation import (
    validate_admin_dom,
    validate_admin_frontend_markers,
)
from ui_asset_load_order_validation import (
    validate_dashboard_endpoints,
    validate_hermeneutic_admin_endpoints,
    validate_identity_endpoints,
    validate_memory_admin_endpoints,
    validate_ui_script_order,
)
from ui_asset_validation_context import UiAssetContents
from ui_page_marker_validation import (
    validate_dashboard_page_markers,
    validate_foundation_page_markers,
    validate_identity_page_markers,
    validate_memory_admin_page_markers,
)


_TEXT_ASSET_NAMES = (
    "index_html",
    "admin_html",
    "dashboard_html",
    "log_html",
    "hermeneutic_admin_html",
    "identity_html",
    "memory_admin_html",
    "admin_api_js",
    "admin_ui_common_js",
    "validation_projection_js",
    "admin_state_js",
    "admin_section_main_model_js",
    "admin_section_arbiter_model_js",
    "admin_section_summary_model_js",
    "admin_section_stimmung_agent_model_js",
    "admin_section_validation_agent_model_js",
    "admin_section_embedding_js",
    "admin_section_database_js",
    "admin_section_services_js",
    "admin_section_resources_js",
    "admin_settings_catalog_js",
    "admin_js",
    "hermeneutic_admin_api_js",
    "hermeneutic_admin_render_js",
    "hermeneutic_admin_render_identity_read_model_js",
    "hermeneutic_admin_render_identity_static_editor_js",
    "hermeneutic_admin_render_identity_mutable_editor_js",
    "hermeneutic_admin_render_identity_governance_js",
    "hermeneutic_admin_main_js",
    "identity_api_js",
    "identity_render_runtime_representations_js",
    "identity_main_js",
    "memory_admin_api_js",
    "memory_admin_render_overview_js",
    "memory_admin_render_turns_js",
    "memory_admin_main_js",
    "dashboard_main_js",
)


def check_ui_assets(web_dir: Path) -> Dict[str, Any]:
    required_files = {
        "index_html": web_dir / "index.html",
        "admin_html": web_dir / "admin.html",
        "dashboard_html": web_dir / "dashboard.html",
        "log_html": web_dir / "log.html",
        "hermeneutic_admin_html": web_dir / "hermeneutic-admin.html",
        "identity_html": web_dir / "identity.html",
        "memory_admin_html": web_dir / "memory-admin.html",
        "admin_css": web_dir / "admin.css",
        "styles_css": web_dir / "styles.css",
        "app_js": web_dir / "app.js",
        "admin_api_js": web_dir / "admin_api.js",
        "admin_ui_common_js": web_dir / "admin_ui_common.js",
        "validation_projection_js": web_dir / "validation_projection.js",
        "admin_state_js": web_dir / "admin_state.js",
        "admin_section_main_model_js": web_dir / "admin_section_main_model.js",
        "admin_section_arbiter_model_js": web_dir / "admin_section_arbiter_model.js",
        "admin_section_summary_model_js": web_dir / "admin_section_summary_model.js",
        "admin_section_stimmung_agent_model_js": web_dir / "admin_section_stimmung_agent_model.js",
        "admin_section_validation_agent_model_js": web_dir / "admin_section_validation_agent_model.js",
        "admin_section_embedding_js": web_dir / "admin_section_embedding.js",
        "admin_section_database_js": web_dir / "admin_section_database.js",
        "admin_section_services_js": web_dir / "admin_section_services.js",
        "admin_section_resources_js": web_dir / "admin_section_resources.js",
        "admin_settings_catalog_js": web_dir / "admin_settings_catalog.js",
        "admin_js": web_dir / "admin.js",
        "hermeneutic_admin_api_js": web_dir / "hermeneutic_admin" / "api.js",
        "hermeneutic_admin_render_js": web_dir / "hermeneutic_admin" / "render.js",
        "hermeneutic_admin_render_identity_read_model_js": (
            web_dir / "hermeneutic_admin" / "render_identity_read_model.js"
        ),
        "hermeneutic_admin_render_identity_static_editor_js": (
            web_dir / "hermeneutic_admin" / "render_identity_static_editor.js"
        ),
        "hermeneutic_admin_render_identity_mutable_editor_js": (
            web_dir / "hermeneutic_admin" / "render_identity_mutable_editor.js"
        ),
        "hermeneutic_admin_render_identity_governance_js": (
            web_dir / "hermeneutic_admin" / "render_identity_governance.js"
        ),
        "hermeneutic_admin_main_js": web_dir / "hermeneutic_admin" / "main.js",
        "identity_api_js": web_dir / "identity" / "api.js",
        "identity_render_runtime_representations_js": (
            web_dir / "identity" / "render_identity_runtime_representations.js"
        ),
        "identity_main_js": web_dir / "identity" / "main.js",
        "memory_admin_api_js": web_dir / "memory_admin" / "api.js",
        "memory_admin_render_overview_js": web_dir / "memory_admin" / "render_overview.js",
        "memory_admin_render_turns_js": web_dir / "memory_admin" / "render_turns.js",
        "memory_admin_main_js": web_dir / "memory_admin" / "main.js",
        "dashboard_styles_css": web_dir / "dashboard" / "styles.css",
        "dashboard_main_js": web_dir / "dashboard" / "main.js",
        "frida_logo_png": web_dir / "fridalogo.png",
    }
    forbidden_files = {
        "admin_old_html": web_dir / "admin-old.html",
        "admin_old_js": web_dir / "admin-old.js",
    }

    for name, path in required_files.items():
        if not path.exists():
            raise RuntimeError(f"asset UI absent: {name} -> {path}")
        if path.stat().st_size <= 0:
            raise RuntimeError(f"asset UI vide: {path}")
    for name, path in forbidden_files.items():
        if path.exists():
            raise RuntimeError(f"asset UI legacy inattendu: {name} -> {path}")

    assets = UiAssetContents(
        {
            name: required_files[name].read_text(encoding="utf-8")
            for name in _TEXT_ASSET_NAMES
        }
    )

    # Keep the legacy validation sequence: when several assets are invalid,
    # the first reported contract remains unchanged.
    script_order = validate_ui_script_order(assets)
    admin_dom = validate_admin_dom(assets)
    foundation_pages = validate_foundation_page_markers(assets)
    hermeneutic_endpoints = validate_hermeneutic_admin_endpoints(assets)
    identity_page = validate_identity_page_markers(assets)
    memory_page = validate_memory_admin_page_markers(assets)
    dashboard_page = validate_dashboard_page_markers(assets)
    dashboard_endpoints = validate_dashboard_endpoints(assets)
    identity_endpoints = validate_identity_endpoints(assets)
    memory_endpoints = validate_memory_admin_endpoints(assets)
    admin_frontend = validate_admin_frontend_markers(assets)

    return {
        "files": {name: str(path) for name, path in required_files.items()},
        "legacy_admin_assets_absent": {name: str(path) for name, path in forbidden_files.items()},
        "admin_script_order": script_order["admin_script_order"],
        "admin_script_srcs": script_order["admin_script_srcs"],
        "admin_settings_endpoints_expected": script_order["admin_settings_endpoints_expected"],
        "admin_settings_endpoints_found": script_order["admin_settings_endpoints_found"],
        "hermeneutic_admin_script_order": script_order["hermeneutic_admin_script_order"],
        "hermeneutic_admin_script_srcs": script_order["hermeneutic_admin_script_srcs"],
        "hermeneutic_admin_endpoints_expected": hermeneutic_endpoints["hermeneutic_admin_endpoints_expected"],
        "hermeneutic_admin_endpoints_found": hermeneutic_endpoints["hermeneutic_admin_endpoints_found"],
        "identity_script_order": script_order["identity_script_order"],
        "identity_script_srcs": script_order["identity_script_srcs"],
        "identity_endpoints_expected": identity_endpoints["identity_endpoints_expected"],
        "identity_endpoints_found": identity_endpoints["identity_endpoints_found"],
        "memory_admin_script_order": script_order["memory_admin_script_order"],
        "memory_admin_script_srcs": script_order["memory_admin_script_srcs"],
        "dashboard_script_order": script_order["dashboard_script_order"],
        "dashboard_script_srcs": script_order["dashboard_script_srcs"],
        "dashboard_endpoints_expected": dashboard_endpoints["dashboard_endpoints_expected"],
        "dashboard_endpoints_found": dashboard_endpoints["dashboard_endpoints_found"],
        "memory_admin_endpoints_expected": memory_endpoints["memory_admin_endpoints_expected"],
        "memory_admin_endpoints_found": memory_endpoints["memory_admin_endpoints_found"],
        "admin_dom_hook_ids_checked": admin_dom["admin_dom_hook_ids_checked"],
        "admin_dynamic_getelement_templates_expected": admin_dom["admin_dynamic_getelement_templates_expected"],
        "admin_dynamic_getelement_templates_found": admin_dom["admin_dynamic_getelement_templates_found"],
        "admin_dynamic_id_assignment_templates_expected": admin_dom["admin_dynamic_id_assignment_templates_expected"],
        "admin_dynamic_id_assignment_templates_found": admin_dom["admin_dynamic_id_assignment_templates_found"],
        "admin_dynamic_templates_lookup_families_checked": admin_dom["admin_dynamic_templates_lookup_families_checked"],
        "admin_dynamic_templates_generated_families_checked": admin_dom["admin_dynamic_templates_generated_families_checked"],
        "admin_query_selectors_expected": admin_dom["admin_query_selectors_expected"],
        "admin_query_selectors_found": admin_dom["admin_query_selectors_found"],
        "admin_data_selectors_checked": admin_dom["admin_data_selectors_checked"],
        "admin_dataset_attrs_checked": admin_dom["admin_dataset_attrs_checked"],
        "admin_field_containers_checked": admin_dom["admin_field_containers_checked"],
        "index_markers": foundation_pages["index_markers"],
        "index_hermeneutic_markers": foundation_pages["index_hermeneutic_markers"],
        "admin_markers": foundation_pages["admin_markers"],
        "log_markers": foundation_pages["log_markers"],
        "hermeneutic_admin_markers": foundation_pages["hermeneutic_admin_markers"],
        "identity_markers": identity_page["identity_markers"],
        "memory_admin_markers": memory_page["memory_admin_markers"],
        "dashboard_markers": dashboard_page["dashboard_markers"],
        "dashboard_forbidden_markers": dashboard_page["dashboard_forbidden_markers"],
        "admin_html_forbidden_markers": foundation_pages["admin_html_forbidden_markers"],
        "admin_js_markers": admin_frontend["admin_js_markers"],
        "admin_js_forbidden_markers": admin_frontend["admin_js_forbidden_markers"],
    }
