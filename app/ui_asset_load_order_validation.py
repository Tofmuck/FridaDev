from __future__ import annotations

import re
from typing import Any, Dict

from ui_asset_validation_context import UiAssetContents


def validate_ui_script_order(assets: UiAssetContents) -> Dict[str, Any]:
    admin_html = assets["admin_html"]
    dashboard_html = assets["dashboard_html"]
    hermeneutic_admin_html = assets["hermeneutic_admin_html"]
    identity_html = assets["identity_html"]
    memory_admin_html = assets["memory_admin_html"]
    admin_front_js = assets.admin_front_js

    admin_script_order = [
        "admin_api.js",
        "admin_ui_common.js",
        "admin_state.js",
        "admin_section_main_model.js",
        "admin_section_arbiter_model.js",
        "admin_section_summary_model.js",
        "admin_section_stimmung_agent_model.js",
        "admin_section_validation_agent_model.js",
        "admin_section_embedding.js",
        "admin_section_database.js",
        "admin_section_services.js",
        "admin_section_resources.js",
        "admin_settings_catalog.js",
        "admin.js",
    ]
    admin_script_srcs = re.findall(r'<script\s+src="([^"]+)"></script>', admin_html)
    if admin_script_srcs != admin_script_order:
        raise RuntimeError(
            "ordre scripts admin invalide: "
            f"attendu={admin_script_order}, trouve={admin_script_srcs}"
        )
    hermeneutic_admin_script_order = [
        "admin_api.js",
        "admin_ui_common.js",
        "validation_projection.js",
        "hermeneutic_admin/api.js",
        "hermeneutic_admin/render.js",
        "hermeneutic_admin/render_identity_read_model.js",
        "hermeneutic_admin/render_identity_static_editor.js",
        "hermeneutic_admin/render_identity_mutable_editor.js",
        "hermeneutic_admin/render_identity_governance.js",
        "identity/render_identity_runtime_representations.js",
        "hermeneutic_admin/main.js",
    ]
    hermeneutic_admin_script_srcs = re.findall(r'<script\s+src="([^"]+)"></script>', hermeneutic_admin_html)
    if hermeneutic_admin_script_srcs != hermeneutic_admin_script_order:
        raise RuntimeError(
            "ordre scripts hermeneutic admin invalide: "
            f"attendu={hermeneutic_admin_script_order}, trouve={hermeneutic_admin_script_srcs}"
        )
    identity_script_order = [
        "admin_api.js",
        "admin_ui_common.js",
        "validation_projection.js",
        "hermeneutic_admin/api.js",
        "hermeneutic_admin/render.js",
        "hermeneutic_admin/render_identity_read_model.js",
        "hermeneutic_admin/render_identity_static_editor.js",
        "hermeneutic_admin/render_identity_mutable_editor.js",
        "hermeneutic_admin/render_identity_governance.js",
        "identity/api.js",
        "identity/render_identity_runtime_representations.js",
        "identity/main.js",
    ]
    identity_script_srcs = re.findall(r'<script\s+src="([^"]+)"></script>', identity_html)
    if identity_script_srcs != identity_script_order:
        raise RuntimeError(
            "ordre scripts identity invalide: "
            f"attendu={identity_script_order}, trouve={identity_script_srcs}"
        )
    memory_admin_script_order = [
        "admin_api.js",
        "admin_ui_common.js",
        "memory_admin/api.js",
        "memory_admin/render_overview.js",
        "memory_admin/render_turns.js",
        "memory_admin/main.js",
    ]
    memory_admin_script_srcs = re.findall(r'<script\s+src="([^"]+)"></script>', memory_admin_html)
    if memory_admin_script_srcs != memory_admin_script_order:
        raise RuntimeError(
            "ordre scripts memory admin invalide: "
            f"attendu={memory_admin_script_order}, trouve={memory_admin_script_srcs}"
        )
    dashboard_script_order = ["admin_api.js", "dashboard/main.js"]
    dashboard_script_srcs = re.findall(r'<script\s+src="([^"]+)"></script>', dashboard_html)
    if dashboard_script_srcs != dashboard_script_order:
        raise RuntimeError(
            "ordre scripts dashboard invalide: "
            f"attendu={dashboard_script_order}, trouve={dashboard_script_srcs}"
        )
    expected_admin_settings_endpoints = {
        "/api/admin/settings",
        "/api/admin/settings/status",
        "/api/admin/settings/main-model",
        "/api/admin/settings/main-model/validate",
        "/api/admin/settings/arbiter-model",
        "/api/admin/settings/arbiter-model/validate",
        "/api/admin/settings/identity-extractor-model",
        "/api/admin/settings/identity-extractor-model/validate",
        "/api/admin/settings/identity-periodic-model",
        "/api/admin/settings/identity-periodic-model/validate",
        "/api/admin/settings/memory-arbiter-model",
        "/api/admin/settings/memory-arbiter-model/validate",
        "/api/admin/settings/summary-model",
        "/api/admin/settings/summary-model/validate",
        "/api/admin/settings/stimmung-agent-model",
        "/api/admin/settings/stimmung-agent-model/validate",
        "/api/admin/settings/validation-agent-model",
        "/api/admin/settings/validation-agent-model/validate",
        "/api/admin/settings/embedding",
        "/api/admin/settings/embedding/validate",
        "/api/admin/settings/database",
        "/api/admin/settings/database/validate",
        "/api/admin/settings/services",
        "/api/admin/settings/services/validate",
        "/api/admin/settings/resources",
        "/api/admin/settings/resources/validate",
    }
    found_admin_settings_endpoints = set(
        re.findall(r"/api/admin/settings(?:/[a-z-]+(?:/validate)?)?", admin_front_js)
    )
    if found_admin_settings_endpoints != expected_admin_settings_endpoints:
        missing = sorted(expected_admin_settings_endpoints - found_admin_settings_endpoints)
        extra = sorted(found_admin_settings_endpoints - expected_admin_settings_endpoints)
        raise RuntimeError(
            "endpoints admin settings invalides: "
            f"missing={missing}, extra={extra}"
        )
    return {
        "admin_script_order": admin_script_order,
        "admin_script_srcs": admin_script_srcs,
        "admin_settings_endpoints_expected": sorted(expected_admin_settings_endpoints),
        "admin_settings_endpoints_found": sorted(found_admin_settings_endpoints),
        "hermeneutic_admin_script_order": hermeneutic_admin_script_order,
        "hermeneutic_admin_script_srcs": hermeneutic_admin_script_srcs,
        "identity_script_order": identity_script_order,
        "identity_script_srcs": identity_script_srcs,
        "memory_admin_script_order": memory_admin_script_order,
        "memory_admin_script_srcs": memory_admin_script_srcs,
        "dashboard_script_order": dashboard_script_order,
        "dashboard_script_srcs": dashboard_script_srcs,
    }


def validate_hermeneutic_admin_endpoints(assets: UiAssetContents) -> Dict[str, Any]:
    hermeneutic_admin_front_js = assets.hermeneutic_admin_front_js

    expected_hermeneutic_admin_endpoints = {
        "/api/admin/hermeneutics/dashboard",
        "/api/admin/identity/read-model",
        "/api/admin/identity/mutable",
        "/api/admin/identity/static",
        "/api/admin/identity/governance",
        "/api/admin/hermeneutics/identity-candidates",
        "/api/admin/hermeneutics/arbiter-decisions",
        "/api/admin/hermeneutics/corrections-export",
        "/api/admin/logs/chat",
        "/api/admin/logs/chat/metadata",
    }
    found_hermeneutic_admin_endpoints = set(
        re.findall(
            r"/api/admin/(?:hermeneutics/[a-z-]+|identity/(?:read-model|mutable|static|governance)|logs/chat(?:/metadata)?)",
            hermeneutic_admin_front_js,
        )
    )
    if found_hermeneutic_admin_endpoints != expected_hermeneutic_admin_endpoints:
        missing = sorted(expected_hermeneutic_admin_endpoints - found_hermeneutic_admin_endpoints)
        extra = sorted(found_hermeneutic_admin_endpoints - expected_hermeneutic_admin_endpoints)
        raise RuntimeError(
            "endpoints hermeneutic admin invalides: "
            f"missing={missing}, extra={extra}"
        )
    return {
        "hermeneutic_admin_endpoints_expected": sorted(expected_hermeneutic_admin_endpoints),
        "hermeneutic_admin_endpoints_found": sorted(found_hermeneutic_admin_endpoints),
    }


def validate_dashboard_endpoints(assets: UiAssetContents) -> Dict[str, Any]:
    dashboard_main_js = assets["dashboard_main_js"]

    expected_dashboard_endpoints = {
        "/api/admin/dashboard/overview",
        "/api/admin/dashboard/conversations",
        "/api/admin/dashboard/turns",
    }
    found_dashboard_endpoints = set(
        re.findall(r"/api/admin/dashboard/(?:overview|conversations|turns|inspection)", dashboard_main_js)
    )
    if found_dashboard_endpoints != expected_dashboard_endpoints:
        missing = sorted(expected_dashboard_endpoints - found_dashboard_endpoints)
        extra = sorted(found_dashboard_endpoints - expected_dashboard_endpoints)
        raise RuntimeError(
            "endpoints dashboard frontend invalides: "
            f"missing={missing}, extra={extra}"
        )
    return {
        "dashboard_endpoints_expected": sorted(expected_dashboard_endpoints),
        "dashboard_endpoints_found": sorted(found_dashboard_endpoints),
    }


def validate_identity_endpoints(assets: UiAssetContents) -> Dict[str, Any]:
    identity_front_js = assets.identity_front_js

    expected_identity_endpoints = {
        "/api/admin/identity/read-model",
        "/api/admin/identity/runtime-representations",
        "/api/admin/identity/mutable",
        "/api/admin/identity/static",
        "/api/admin/identity/governance",
        "/api/admin/hermeneutics/corrections-export",
    }
    found_identity_endpoints = set(
        re.findall(
            r"/api/admin/(?:identity/(?:read-model|runtime-representations|mutable|static|governance)|hermeneutics/corrections-export)",
            identity_front_js,
        )
    )
    if found_identity_endpoints != expected_identity_endpoints:
        missing = sorted(expected_identity_endpoints - found_identity_endpoints)
        extra = sorted(found_identity_endpoints - expected_identity_endpoints)
        raise RuntimeError(
            "endpoints identity invalides: "
            f"missing={missing}, extra={extra}"
        )
    return {
        "identity_endpoints_expected": sorted(expected_identity_endpoints),
        "identity_endpoints_found": sorted(found_identity_endpoints),
    }


def validate_memory_admin_endpoints(assets: UiAssetContents) -> Dict[str, Any]:
    memory_admin_front_js = assets.memory_admin_front_js

    expected_memory_admin_endpoints = {
        "/api/admin/memory/dashboard",
        "/api/admin/logs/chat",
        "/api/admin/logs/chat/metadata",
        "/api/admin/hermeneutics/arbiter-decisions",
    }
    found_memory_admin_endpoints = set(
        re.findall(
            r"/api/admin/(?:memory/dashboard|logs/chat(?:/metadata)?|hermeneutics/arbiter-decisions)",
            memory_admin_front_js,
        )
    )
    if found_memory_admin_endpoints != expected_memory_admin_endpoints:
        missing = sorted(expected_memory_admin_endpoints - found_memory_admin_endpoints)
        extra = sorted(found_memory_admin_endpoints - expected_memory_admin_endpoints)
        raise RuntimeError(
            "endpoints memory admin invalides: "
            f"missing={missing}, extra={extra}"
        )
    return {
        "memory_admin_endpoints_expected": sorted(expected_memory_admin_endpoints),
        "memory_admin_endpoints_found": sorted(found_memory_admin_endpoints),
    }
