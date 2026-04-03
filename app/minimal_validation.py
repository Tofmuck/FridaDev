#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List

import psycopg
import requests

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import config
from admin import runtime_settings
from core import conv_store
from core import runtime_db_bootstrap


def _resolve_app_path(raw: str) -> Path:
    path = Path(str(raw or ""))
    if not path.is_absolute():
        path = APP_DIR / path
    return path


def _runtime_resource_path(field: str) -> Path:
    view = runtime_settings.get_resources_settings()
    payload = view.payload.get(field) or {}
    if 'value' in payload:
        return _resolve_app_path(str(payload['value']))

    env_bundle = runtime_settings.build_env_seed_bundle('resources')
    fallback = env_bundle.payload.get(field) or {}
    if 'value' in fallback:
        return _resolve_app_path(str(fallback['value']))

    raise KeyError(f'missing resources runtime value: {field}')


def _runtime_database_view() -> runtime_settings.RuntimeSectionView:
    return runtime_db_bootstrap.runtime_database_view(runtime_settings)


def _runtime_database_backend() -> str:
    return runtime_db_bootstrap.runtime_database_backend(runtime_settings)


def _bootstrap_database_dsn() -> str:
    return runtime_db_bootstrap.bootstrap_database_dsn(config, runtime_settings)


def _db_conn():
    return runtime_db_bootstrap.connect_runtime_database(psycopg, config, runtime_settings)


def _http_json(method: str, url: str, **kwargs: Any) -> requests.Response:
    timeout = kwargs.pop("timeout", (5, 20))
    return requests.request(method=method, url=url, timeout=timeout, **kwargs)


def _admin_request_kwargs() -> Dict[str, Any]:
    token = str(config.FRIDA_ADMIN_TOKEN or "").strip()
    if not token:
        return {}
    return {"headers": {"X-Admin-Token": token}}


def _build_non_secret_patch_payload(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    patch_payload: Dict[str, Dict[str, Any]] = {}
    for field, field_payload in payload.items():
        if not isinstance(field_payload, dict):
            continue
        if "value" not in field_payload:
            continue
        patch_payload[str(field)] = {"value": field_payload["value"]}

    if not patch_payload:
        raise RuntimeError("aucune valeur non secrete disponible pour le smoke PATCH")

    return patch_payload


def _assert_masked_secret_fields(section_payloads: Dict[str, Any]) -> None:
    for section in runtime_settings.list_sections():
        payload = section_payloads.get(section) or {}
        if not isinstance(payload, dict):
            raise RuntimeError(f"payload admin settings invalide pour {section}")
        for field in runtime_settings.get_section_spec(section).fields:
            if not field.is_secret:
                continue
            secret_payload = payload.get(field.key)
            if not isinstance(secret_payload, dict):
                raise RuntimeError(f"payload secret manquant pour {section}.{field.key}")
            if set(secret_payload.keys()) != {"is_secret", "is_set", "origin"}:
                raise RuntimeError(f"payload secret non masque pour {section}.{field.key}")
            if secret_payload.get("is_secret") is not True:
                raise RuntimeError(f"payload secret invalide pour {section}.{field.key}")
            if not isinstance(secret_payload.get("is_set"), bool):
                raise RuntimeError(f"etat secret invalide pour {section}.{field.key}")


def _assert_no_env_fallback_for_persisted_non_secret_fields(
    section_payloads: Dict[str, Any],
    section_statuses: Dict[str, Any],
) -> None:
    for section in runtime_settings.list_sections():
        section_status = section_statuses.get(section) or {}
        if str(section_status.get("source") or "") != "db":
            continue

        payload = section_payloads.get(section) or {}
        if not isinstance(payload, dict):
            raise RuntimeError(f"payload admin settings invalide pour {section}")

        for field in runtime_settings.get_section_spec(section).fields:
            if field.is_secret:
                continue
            field_payload = payload.get(field.key)
            if not isinstance(field_payload, dict):
                raise RuntimeError(f"payload champ manquant pour {section}.{field.key}")
            if str(field_payload.get("origin") or "") == "env_seed":
                raise RuntimeError(
                    f"persisted non-secret field still uses env fallback origin: {section}.{field.key}"
                )


def _run_check(
    results: List[Dict[str, Any]],
    name: str,
    fn: Callable[[], Dict[str, Any]],
) -> None:
    try:
        details = fn()
        results.append({"name": name, "ok": True, "details": details})
    except Exception as exc:
        results.append({"name": name, "ok": False, "error": str(exc)})


def _check_startup_import() -> Dict[str, Any]:
    server = importlib.import_module("server")
    app = getattr(server, "app", None)
    fingerprint = getattr(server, "_RUNTIME_FINGERPRINT", {})
    if app is None:
        raise RuntimeError("server.app manquant")
    if not isinstance(fingerprint, dict):
        raise RuntimeError("_RUNTIME_FINGERPRINT invalide")

    config_path = Path(str(fingerprint.get("config_path") or ""))
    conv_dir = Path(str(fingerprint.get("conv_dir") or ""))
    logs_path = Path(str(fingerprint.get("logs_path") or ""))
    config_sha256 = str(fingerprint.get("config_sha256") or "").strip()

    if not config_path.exists():
        raise RuntimeError(f"config_path introuvable: {config_path}")
    if not conv_dir.exists():
        raise RuntimeError(f"conv_dir introuvable: {conv_dir}")
    if not logs_path.parent.exists():
        raise RuntimeError(f"logs_path parent introuvable: {logs_path.parent}")
    if len(config_sha256) < 12:
        raise RuntimeError("config_sha256 absent ou trop court")

    return {
        "config_path": str(config_path),
        "conv_dir": str(conv_dir),
        "logs_parent": str(logs_path.parent),
        "config_sha256": config_sha256[:12],
    }


def _check_db_schema() -> Dict[str, Any]:
    required_tables: Dict[str, set[str]] = {
        "conversations": {
            "id",
            "title",
            "created_at",
            "updated_at",
            "message_count",
            "last_message_preview",
            "deleted_at",
        },
        "conversation_messages": {
            "conversation_id",
            "seq",
            "role",
            "content",
            "timestamp",
            "summarized_by",
            "embedded",
            "meta",
        },
        "traces": {
            "id",
            "conversation_id",
            "role",
            "content",
            "timestamp",
            "embedding",
            "summary_id",
        },
        "summaries": {
            "id",
            "conversation_id",
            "start_ts",
            "end_ts",
            "content",
            "embedding",
        },
        "identities": {
            "id",
            "conversation_id",
            "subject",
            "content",
            "weight",
            "created_ts",
            "last_seen_ts",
            "stability",
            "utterance_mode",
            "recurrence",
            "scope",
            "evidence_kind",
            "confidence",
            "status",
            "content_norm",
            "last_reason",
            "override_state",
            "override_reason",
            "override_actor",
            "override_ts",
        },
        "identity_evidence": {
            "id",
            "conversation_id",
            "subject",
            "content",
            "content_norm",
            "stability",
            "utterance_mode",
            "recurrence",
            "scope",
            "evidence_kind",
            "confidence",
            "status",
            "reason",
            "source_trace_id",
            "created_ts",
        },
        "identity_conflicts": {
            "id",
            "identity_id_a",
            "identity_id_b",
            "confidence_conflict",
            "reason",
            "resolved_state",
            "created_ts",
            "resolved_ts",
        },
        "arbiter_decisions": {
            "id",
            "conversation_id",
            "candidate_id",
            "candidate_role",
            "candidate_content",
            "candidate_ts",
            "candidate_score",
            "keep",
            "semantic_relevance",
            "contextual_gain",
            "redundant_with_recent",
            "reason",
            "model",
            "decision_source",
            "created_ts",
        },
        "runtime_settings": {
            "section",
            "schema_version",
            "updated_at",
            "updated_by",
            "payload",
        },
        "runtime_settings_history": {
            "id",
            "section",
            "schema_version",
            "changed_at",
            "changed_by",
            "payload_before",
            "payload_after",
        },
    }

    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT extname
                FROM pg_extension
                WHERE extname IN ('vector', 'pgcrypto')
                ORDER BY extname
                """
            )
            extensions = {str(row[0]) for row in cur.fetchall()}
            if {"vector", "pgcrypto"} - extensions:
                missing = sorted({"vector", "pgcrypto"} - extensions)
                raise RuntimeError(f"extensions manquantes: {', '.join(missing)}")

            details: Dict[str, Any] = {
                "extensions": sorted(extensions),
                "tables": {},
            }

            for table_name, expected_columns in required_tables.items():
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = %s
                    """,
                    (table_name,),
                )
                columns = {str(row[0]) for row in cur.fetchall()}
                if not columns:
                    raise RuntimeError(f"table absente: {table_name}")
                missing_columns = sorted(expected_columns - columns)
                if missing_columns:
                    raise RuntimeError(
                        f"colonnes manquantes pour {table_name}: {', '.join(missing_columns)}"
                    )
                details["tables"][table_name] = {
                    "column_count": len(columns),
                    "checked_columns": sorted(expected_columns),
                }

    return details


def _check_prompt_files() -> Dict[str, Any]:
    required_files = {
        "llm_identity": _runtime_resource_path('llm_identity_path'),
        "user_identity": _runtime_resource_path('user_identity_path'),
        "main_system_prompt": _resolve_app_path(config.MAIN_SYSTEM_PROMPT_PATH),
        "main_hermeneutical_prompt": _resolve_app_path(config.MAIN_HERMENEUTICAL_PROMPT_PATH),
        "summary_system_prompt": _resolve_app_path(config.SUMMARY_SYSTEM_PROMPT_PATH),
        "web_reformulation_prompt": _resolve_app_path(config.WEB_REFORMULATION_PROMPT_PATH),
        "arbiter_prompt": _resolve_app_path(config.ARBITER_PROMPT_PATH),
        "identity_extractor_prompt": _resolve_app_path(config.IDENTITY_EXTRACTOR_PROMPT_PATH),
    }

    app_js = (APP_DIR / "web" / "app.js").read_text(encoding="utf-8")
    index_html = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")
    summarizer_py = (APP_DIR / "memory" / "summarizer.py").read_text(encoding="utf-8")
    web_search_py = (APP_DIR / "tools" / "web_search.py").read_text(encoding="utf-8")

    forbidden_inline_markers = {
        "app_js": [
            "const SYSTEM_PROMPT =",
            "system: cfg.system,",
            "cfg.system",
        ],
        "index_html": [
            'id="system"',
        ],
        "summarizer_py": [
            "Tu es un assistant de synthèse. Résume le dialogue suivant en conservant",
        ],
        "web_search_py": [
            "Tu es un assistant qui transforme un message en requête de recherche web courte et efficace.",
        ],
    }

    for marker in forbidden_inline_markers["app_js"]:
        if marker in app_js:
            raise RuntimeError(f"prompt inline legacy inattendu dans app.js: {marker}")
    for marker in forbidden_inline_markers["index_html"]:
        if marker in index_html:
            raise RuntimeError(f"prompt inline legacy inattendu dans index.html: {marker}")
    for marker in forbidden_inline_markers["summarizer_py"]:
        if marker in summarizer_py:
            raise RuntimeError(f"prompt inline legacy inattendu dans summarizer.py: {marker}")
    for marker in forbidden_inline_markers["web_search_py"]:
        if marker in web_search_py:
            raise RuntimeError(f"prompt inline legacy inattendu dans web_search.py: {marker}")

    details: Dict[str, Any] = {
        "forbidden_inline_markers": forbidden_inline_markers,
    }
    for name, path in required_files.items():
        if not path.exists():
            raise RuntimeError(f"fichier prompt/identity absent: {path}")
        content = path.read_text(encoding="utf-8").strip()
        if len(content) < 20:
            raise RuntimeError(f"fichier trop court ou vide: {path}")
        details[name] = {"path": str(path), "chars": len(content)}

    return details


def _check_ui_assets() -> Dict[str, Any]:
    web_dir = APP_DIR / "web"
    required_files = {
        "index_html": web_dir / "index.html",
        "admin_html": web_dir / "admin.html",
        "hermeneutic_admin_html": web_dir / "hermeneutic-admin.html",
        "admin_css": web_dir / "admin.css",
        "styles_css": web_dir / "styles.css",
        "app_js": web_dir / "app.js",
        "admin_api_js": web_dir / "admin_api.js",
        "admin_ui_common_js": web_dir / "admin_ui_common.js",
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
        "admin_js": web_dir / "admin.js",
        "hermeneutic_admin_api_js": web_dir / "hermeneutic_admin" / "api.js",
        "hermeneutic_admin_render_js": web_dir / "hermeneutic_admin" / "render.js",
        "hermeneutic_admin_main_js": web_dir / "hermeneutic_admin" / "main.js",
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

    index_html = required_files["index_html"].read_text(encoding="utf-8")
    admin_html = required_files["admin_html"].read_text(encoding="utf-8")
    hermeneutic_admin_html = required_files["hermeneutic_admin_html"].read_text(encoding="utf-8")
    admin_api_js = required_files["admin_api_js"].read_text(encoding="utf-8")
    admin_ui_common_js = required_files["admin_ui_common_js"].read_text(encoding="utf-8")
    admin_state_js = required_files["admin_state_js"].read_text(encoding="utf-8")
    admin_section_main_model_js = required_files["admin_section_main_model_js"].read_text(encoding="utf-8")
    admin_section_arbiter_model_js = required_files["admin_section_arbiter_model_js"].read_text(encoding="utf-8")
    admin_section_summary_model_js = required_files["admin_section_summary_model_js"].read_text(encoding="utf-8")
    admin_section_stimmung_agent_model_js = required_files["admin_section_stimmung_agent_model_js"].read_text(encoding="utf-8")
    admin_section_validation_agent_model_js = required_files["admin_section_validation_agent_model_js"].read_text(encoding="utf-8")
    admin_section_embedding_js = required_files["admin_section_embedding_js"].read_text(encoding="utf-8")
    admin_section_database_js = required_files["admin_section_database_js"].read_text(encoding="utf-8")
    admin_section_services_js = required_files["admin_section_services_js"].read_text(encoding="utf-8")
    admin_section_resources_js = required_files["admin_section_resources_js"].read_text(encoding="utf-8")
    admin_js = required_files["admin_js"].read_text(encoding="utf-8")
    hermeneutic_admin_api_js = required_files["hermeneutic_admin_api_js"].read_text(encoding="utf-8")
    hermeneutic_admin_render_js = required_files["hermeneutic_admin_render_js"].read_text(encoding="utf-8")
    hermeneutic_admin_main_js = required_files["hermeneutic_admin_main_js"].read_text(encoding="utf-8")
    admin_front_js = (
        f"{admin_api_js}\n"
        f"{admin_ui_common_js}\n"
        f"{admin_state_js}\n"
        f"{admin_section_main_model_js}\n"
        f"{admin_section_arbiter_model_js}\n"
        f"{admin_section_summary_model_js}\n"
        f"{admin_section_stimmung_agent_model_js}\n"
        f"{admin_section_validation_agent_model_js}\n"
        f"{admin_section_embedding_js}\n"
        f"{admin_section_database_js}\n"
        f"{admin_section_services_js}\n"
        f"{admin_section_resources_js}\n"
        f"{admin_js}"
    )
    hermeneutic_admin_front_js = (
        f"{hermeneutic_admin_api_js}\n"
        f"{hermeneutic_admin_render_js}\n"
        f"{hermeneutic_admin_main_js}"
    )

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
        "hermeneutic_admin/api.js",
        "hermeneutic_admin/render.js",
        "hermeneutic_admin/main.js",
    ]
    hermeneutic_admin_script_srcs = re.findall(r'<script\s+src="([^"]+)"></script>', hermeneutic_admin_html)
    if hermeneutic_admin_script_srcs != hermeneutic_admin_script_order:
        raise RuntimeError(
            "ordre scripts hermeneutic admin invalide: "
            f"attendu={hermeneutic_admin_script_order}, trouve={hermeneutic_admin_script_srcs}"
        )

    expected_admin_settings_endpoints = {
        "/api/admin/settings",
        "/api/admin/settings/status",
        "/api/admin/settings/main-model",
        "/api/admin/settings/main-model/validate",
        "/api/admin/settings/arbiter-model",
        "/api/admin/settings/arbiter-model/validate",
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

    if 'const TOKEN_KEY = "frida.adminToken";' not in admin_api_js:
        raise RuntimeError("contrat token admin manquant (frida.adminToken)")
    if 'headers.set("X-Admin-Token", token);' not in admin_api_js:
        raise RuntimeError("contrat header admin manquant (X-Admin-Token)")

    dom_hook_ids = sorted(set(re.findall(r'document\.getElementById\("([^"]+)"\)', admin_front_js)))
    missing_dom_hook_ids = [hook_id for hook_id in dom_hook_ids if f'id="{hook_id}"' not in admin_html]
    if missing_dom_hook_ids:
        raise RuntimeError(f"hooks DOM admin manquants dans admin.html: {missing_dom_hook_ids}")

    dynamic_getelement_templates = sorted(
        set(re.findall(r'document\.getElementById\(`([^`]*\$\{[^`]+\}[^`]*)`\)', admin_front_js))
    )
    expected_dynamic_getelement_templates = {
        "adminMainModel-${field}",
        "adminMainModelFieldError-${field}",
        "adminMainModelSource-${spec.key}",
        "adminArbiterModel-${field}",
        "adminArbiterModelFieldError-${field}",
        "adminArbiterModelSource-${spec.key}",
        "adminSummaryModel-${field}",
        "adminSummaryModelFieldError-${field}",
        "adminSummaryModelSource-${spec.key}",
        "adminStimmungAgentModel-${field}",
        "adminStimmungAgentModelFieldError-${field}",
        "adminStimmungAgentModelSource-${spec.key}",
        "adminValidationAgentModel-${field}",
        "adminValidationAgentModelFieldError-${field}",
        "adminValidationAgentModelSource-${spec.key}",
        "adminEmbedding-${field}",
        "adminEmbeddingFieldError-${field}",
        "adminEmbeddingSource-${spec.key}",
        "adminDatabase-${field}",
        "adminDatabaseFieldError-${field}",
        "adminDatabaseSource-${spec.key}",
        "adminServices-${field}",
        "adminServicesFieldError-${field}",
        "adminServicesSource-${spec.key}",
        "adminResources-${field}",
        "adminResourcesFieldError-${field}",
        "adminResourcesSource-${spec.key}",
    }
    if set(dynamic_getelement_templates) != expected_dynamic_getelement_templates:
        missing = sorted(expected_dynamic_getelement_templates - set(dynamic_getelement_templates))
        extra = sorted(set(dynamic_getelement_templates) - expected_dynamic_getelement_templates)
        raise RuntimeError(
            "templates getElementById dynamiques invalides: "
            f"missing={missing}, extra={extra}"
        )

    dynamic_id_assignment_templates = sorted(
        set(re.findall(r'\.id\s*=\s*`([^`]*\$\{[^`]+\}[^`]*)`', admin_front_js))
    )
    expected_dynamic_id_assignment_templates = {
        "adminMainModel-${spec.key}",
        "adminMainModelFieldError-${spec.key}",
        "adminMainModelSource-${spec.key}",
        "adminArbiterModel-${spec.key}",
        "adminArbiterModelFieldError-${spec.key}",
        "adminArbiterModelSource-${spec.key}",
        "adminSummaryModel-${spec.key}",
        "adminSummaryModelFieldError-${spec.key}",
        "adminSummaryModelSource-${spec.key}",
        "adminStimmungAgentModel-${spec.key}",
        "adminStimmungAgentModelFieldError-${spec.key}",
        "adminStimmungAgentModelSource-${spec.key}",
        "adminValidationAgentModel-${spec.key}",
        "adminValidationAgentModelFieldError-${spec.key}",
        "adminValidationAgentModelSource-${spec.key}",
        "adminEmbedding-${spec.key}",
        "adminEmbeddingFieldError-${spec.key}",
        "adminEmbeddingSource-${spec.key}",
        "adminDatabase-${spec.key}",
        "adminDatabaseFieldError-${spec.key}",
        "adminDatabaseSource-${spec.key}",
        "adminServices-${spec.key}",
        "adminServicesFieldError-${spec.key}",
        "adminServicesSource-${spec.key}",
        "adminResources-${spec.key}",
        "adminResourcesFieldError-${spec.key}",
        "adminResourcesSource-${spec.key}",
    }
    if set(dynamic_id_assignment_templates) != expected_dynamic_id_assignment_templates:
        missing = sorted(expected_dynamic_id_assignment_templates - set(dynamic_id_assignment_templates))
        extra = sorted(set(dynamic_id_assignment_templates) - expected_dynamic_id_assignment_templates)
        raise RuntimeError(
            "templates id dynamiques generes invalides: "
            f"missing={missing}, extra={extra}"
        )

    def _normalize_dynamic_id_template(raw: str) -> str:
        return re.sub(r"\$\{[^}]+\}", "${*}", raw)

    normalized_dynamic_getelement_templates = sorted(
        {_normalize_dynamic_id_template(template) for template in dynamic_getelement_templates}
    )
    normalized_dynamic_id_assignment_templates = sorted(
        {_normalize_dynamic_id_template(template) for template in dynamic_id_assignment_templates}
    )
    if normalized_dynamic_getelement_templates != normalized_dynamic_id_assignment_templates:
        raise RuntimeError(
            "coherence templates dynamiques getElementById/id assignee invalide: "
            f"lookup={normalized_dynamic_getelement_templates}, "
            f"generated={normalized_dynamic_id_assignment_templates}"
        )

    query_selector_matches = re.findall(
        r'document\.querySelector\("([^"]+)"\)|document\.querySelector\(`([^`]+)`\)',
        admin_front_js,
    )
    query_selectors = sorted(
        {
            selector
            for quoted_selector, template_selector in query_selector_matches
            for selector in [quoted_selector or template_selector]
            if selector
        }
    )
    expected_query_selectors = {
        ".admin-secret-card",
        '[data-field="${field}"]',
        '[data-arbiter-field="${field}"]',
        '[data-summary-field="${field}"]',
        '[data-stimmung-agent-field="${field}"]',
        '[data-validation-agent-field="${field}"]',
        '[data-embedding-field="${field}"]',
        '[data-database-field="${field}"]',
        '[data-services-field="${field}"]',
        '[data-resources-field="${field}"]',
    }
    if set(query_selectors) != expected_query_selectors:
        missing = sorted(expected_query_selectors - set(query_selectors))
        extra = sorted(set(query_selectors) - expected_query_selectors)
        raise RuntimeError(
            "query selectors admin invalides: "
            f"missing={missing}, extra={extra}"
        )

    if 'class="admin-secret-card"' not in admin_html:
        raise RuntimeError("class admin-secret-card absente de admin.html")

    data_selectors = sorted(
        {
            match.group(1)
            for selector in query_selectors
            for match in [re.match(r'^\[(data-[a-z-]+)="\$\{field\}"\]$', selector)]
            if match
        }
    )

    def _camel_to_kebab(raw: str) -> str:
        return re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", raw).lower()

    dataset_attrs = sorted(
        {
            f"data-{_camel_to_kebab(dataset_key)}"
            for dataset_key in re.findall(r"field\.dataset\.([a-zA-Z0-9_]+)\s*=\s*spec\.key", admin_front_js)
        }
    )
    if set(data_selectors) != set(dataset_attrs):
        missing = sorted(set(data_selectors) - set(dataset_attrs))
        extra = sorted(set(dataset_attrs) - set(data_selectors))
        raise RuntimeError(
            "dataset attrs admin invalides: "
            f"missing={missing}, extra={extra}"
        )

    field_container_ids = [
        "adminMainModelFields",
        "adminArbiterModelFields",
        "adminSummaryModelFields",
        "adminStimmungAgentModelFields",
        "adminValidationAgentModelFields",
        "adminEmbeddingFields",
        "adminDatabaseFields",
        "adminServicesFields",
        "adminResourcesFields",
    ]
    missing_field_containers = [field_id for field_id in field_container_ids if f'id="{field_id}"' not in admin_html]
    if missing_field_containers:
        raise RuntimeError(f"containers champs section manquants dans admin.html: {missing_field_containers}")

    index_markers = [
        'src="./fridalogo.png"',
        'href="styles.css"',
        'script src="app.js"',
        'id="threads"',
        'id="log"',
        'id="message"',
    ]
    for marker in index_markers:
        if marker not in index_html:
            raise RuntimeError(f"marker index.html manquant: {marker}")
    index_hermeneutic_markers = [
        'id="btnHermeneuticAdmin"',
        'href="/hermeneutic-admin"',
        'target="_blank"',
        'rel="noopener noreferrer"',
    ]
    for marker in index_hermeneutic_markers:
        if marker not in index_html:
            raise RuntimeError(f"marker index.html hermeneutic admin manquant: {marker}")

    admin_markers = [
        "Admin de configuration",
        'href="admin.css"',
        'script src="admin_api.js"',
        'script src="admin_ui_common.js"',
        'script src="admin_state.js"',
        'script src="admin_section_main_model.js"',
        'script src="admin_section_arbiter_model.js"',
        'script src="admin_section_summary_model.js"',
        'script src="admin_section_stimmung_agent_model.js"',
        'script src="admin_section_validation_agent_model.js"',
        'script src="admin_section_embedding.js"',
        'script src="admin_section_database.js"',
        'script src="admin_section_services.js"',
        'script src="admin_section_resources.js"',
        'script src="admin.js"',
        'id="adminRefresh"',
        'id="adminStatusBanner"',
        'id="adminMainModelForm"',
        'id="adminMainModelValidate"',
        'id="adminMainModelSave"',
        'id="adminMainModelApiKeyReplace"',
        'id="adminMainModelSystemPromptInfo"',
        'id="adminMainModelHermeneuticalPromptInfo"',
        'id="adminMainModelReadonlyInfo"',
        "System Prompt",
        "Hermeneutical Prompt",
        'id="adminMainModelChecks"',
        'id="adminArbiterModelForm"',
        'id="adminArbiterModelValidate"',
        'id="adminArbiterModelSave"',
        'id="adminArbiterModelReadonlyInfo"',
        'id="adminArbiterModelChecks"',
        'id="adminSummaryModelForm"',
        'id="adminSummaryModelValidate"',
        'id="adminSummaryModelSave"',
        'id="adminSummaryModelReadonlyInfo"',
        'id="adminSummaryModelChecks"',
        'id="adminStimmungAgentModelForm"',
        'id="adminStimmungAgentModelValidate"',
        'id="adminStimmungAgentModelSave"',
        'id="adminStimmungAgentModelReadonlyInfo"',
        'id="adminStimmungAgentModelChecks"',
        'id="adminValidationAgentModelForm"',
        'id="adminValidationAgentModelValidate"',
        'id="adminValidationAgentModelSave"',
        'id="adminValidationAgentModelReadonlyInfo"',
        'id="adminValidationAgentModelChecks"',
        'id="adminEmbeddingForm"',
        'id="adminEmbeddingValidate"',
        'id="adminEmbeddingSave"',
        'id="adminEmbeddingTokenReplace"',
        'id="adminEmbeddingChecks"',
        'id="adminDatabaseForm"',
        'id="adminDatabaseValidate"',
        'id="adminDatabaseSave"',
        'id="adminDatabaseDsnReplace"',
        'id="adminDatabaseChecks"',
        'id="adminServicesForm"',
        'id="adminServicesValidate"',
        'id="adminServicesSave"',
        'id="adminServicesCrawl4aiTokenReplace"',
        'id="adminServicesReadonlyInfo"',
        'id="adminServicesChecks"',
        'id="adminResourcesForm"',
        'id="adminResourcesValidate"',
        'id="adminResourcesSave"',
        'id="adminResourcesChecks"',
        'id="adminSectionGrid"',
    ]
    for marker in admin_markers:
        if marker not in admin_html:
            raise RuntimeError(f"marker admin.html manquant: {marker}")
    admin_html_forbidden_markers = [
        'id="rows"',
        'id="restart"',
        "admin-old.html",
        "admin-old.js",
        "/admin-old",
    ]
    for marker in admin_html_forbidden_markers:
        if marker in admin_html:
            raise RuntimeError(f"marker admin.html legacy inattendu: {marker}")

    hermeneutic_admin_markers = [
        "Hermeneutic admin",
        'href="admin.css"',
        'script src="admin_api.js"',
        'script src="admin_ui_common.js"',
        'script src="hermeneutic_admin/api.js"',
        'script src="hermeneutic_admin/render.js"',
        'script src="hermeneutic_admin/main.js"',
        'id="hermeneuticAdminRefresh"',
        'id="hermeneuticConversationId"',
        'id="hermeneuticTurnId"',
        'id="hermeneuticTurnStages"',
        'id="hermeneuticArbiterList"',
        'id="hermeneuticIdentityList"',
        'id="hermeneuticCorrectionsList"',
        "Vue d'ensemble",
        "Inspection par tour",
        "Decisions arbitre",
        "Identites candidates",
        "Corrections recentes",
    ]
    for marker in hermeneutic_admin_markers:
        if marker not in hermeneutic_admin_html:
            raise RuntimeError(f"marker hermeneutic-admin.html manquant: {marker}")

    expected_hermeneutic_admin_endpoints = {
        "/api/admin/hermeneutics/dashboard",
        "/api/admin/hermeneutics/identity-candidates",
        "/api/admin/hermeneutics/arbiter-decisions",
        "/api/admin/hermeneutics/corrections-export",
        "/api/admin/logs/chat",
        "/api/admin/logs/chat/metadata",
    }
    found_hermeneutic_admin_endpoints = set(
        re.findall(
            r"/api/admin/(?:hermeneutics/[a-z-]+|logs/chat(?:/metadata)?)",
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

    admin_js_markers = [
        "/api/admin/settings/status",
        "/api/admin/settings/main-model",
        "/api/admin/settings/main-model/validate",
        "/api/admin/settings/arbiter-model",
        "/api/admin/settings/arbiter-model/validate",
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
        "frida.adminToken",
        "window.FridaAdminState",
        "createAdminState",
        "initializeAdminSectionDrafts",
        "adminMainModelSave",
        "adminMainModelApiKeyReplace",
        "adminMainModelSystemPromptInfo",
        "adminMainModelHermeneuticalPromptInfo",
        "adminMainModelReadonlyInfo",
        "hermeneutical_prompt",
        "renderReadonlyInfoEntries",
        "renderReadonlyInfoCards",
        "applyFieldError",
        "createMainModelSectionController",
        "createArbiterModelSectionController",
        "createSummaryModelSectionController",
        "createStimmungAgentModelSectionController",
        "createValidationAgentModelSectionController",
        "createEmbeddingSectionController",
        "createDatabaseSectionController",
        "createServicesSectionController",
        "createResourcesSectionController",
        "response_max_tokens",
        "adminArbiterModelSave",
        "adminArbiterModelReadonlyInfo",
        "adminSummaryModelSave",
        "adminSummaryModelReadonlyInfo",
        "adminStimmungAgentModelSave",
        "adminStimmungAgentModelReadonlyInfo",
        "adminValidationAgentModelSave",
        "adminValidationAgentModelReadonlyInfo",
        "adminEmbeddingSave",
        "adminEmbeddingTokenReplace",
        "adminDatabaseSave",
        "adminDatabaseDsnReplace",
        "adminServicesSave",
        "adminServicesCrawl4aiTokenReplace",
        "adminServicesReadonlyInfo",
        "adminResourcesSave",
        "adminSectionGrid",
    ]
    for marker in admin_js_markers:
        if marker not in admin_front_js:
            raise RuntimeError(f"marker admin frontend manquant: {marker}")
    admin_js_forbidden_markers = [
        "/api/admin/logs",
        "/api/admin/restart",
        "loadLogs",
        "restartService",
        "admin-old",
    ]
    for marker in admin_js_forbidden_markers:
        if marker in admin_front_js:
            raise RuntimeError(f"marker admin frontend legacy inattendu: {marker}")

    return {
        "files": {name: str(path) for name, path in required_files.items()},
        "legacy_admin_assets_absent": {name: str(path) for name, path in forbidden_files.items()},
        "admin_script_order": admin_script_order,
        "admin_script_srcs": admin_script_srcs,
        "admin_settings_endpoints_expected": sorted(expected_admin_settings_endpoints),
        "admin_settings_endpoints_found": sorted(found_admin_settings_endpoints),
        "hermeneutic_admin_script_order": hermeneutic_admin_script_order,
        "hermeneutic_admin_script_srcs": hermeneutic_admin_script_srcs,
        "hermeneutic_admin_endpoints_expected": sorted(expected_hermeneutic_admin_endpoints),
        "hermeneutic_admin_endpoints_found": sorted(found_hermeneutic_admin_endpoints),
        "admin_dom_hook_ids_checked": dom_hook_ids,
        "admin_dynamic_getelement_templates_expected": sorted(expected_dynamic_getelement_templates),
        "admin_dynamic_getelement_templates_found": dynamic_getelement_templates,
        "admin_dynamic_id_assignment_templates_expected": sorted(expected_dynamic_id_assignment_templates),
        "admin_dynamic_id_assignment_templates_found": dynamic_id_assignment_templates,
        "admin_dynamic_templates_lookup_families_checked": normalized_dynamic_getelement_templates,
        "admin_dynamic_templates_generated_families_checked": normalized_dynamic_id_assignment_templates,
        "admin_query_selectors_expected": sorted(expected_query_selectors),
        "admin_query_selectors_found": query_selectors,
        "admin_data_selectors_checked": data_selectors,
        "admin_dataset_attrs_checked": dataset_attrs,
        "admin_field_containers_checked": field_container_ids,
        "index_markers": index_markers,
        "index_hermeneutic_markers": index_hermeneutic_markers,
        "admin_markers": admin_markers,
        "hermeneutic_admin_markers": hermeneutic_admin_markers,
        "admin_html_forbidden_markers": admin_html_forbidden_markers,
        "admin_js_markers": admin_js_markers,
        "admin_js_forbidden_markers": admin_js_forbidden_markers,
    }


def _check_api_smoke(base_url: str) -> Dict[str, Any]:
    root = _http_json("GET", f"{base_url}/")
    if root.status_code != 200 or "Frida" not in root.text:
        raise RuntimeError("root invalide")

    admin = _http_json("GET", f"{base_url}/admin")
    if admin.status_code != 200 or "Admin de configuration" not in admin.text:
        raise RuntimeError("admin invalide")

    hermeneutic_admin = _http_json("GET", f"{base_url}/hermeneutic-admin")
    if hermeneutic_admin.status_code != 200 or "Hermeneutic admin" not in hermeneutic_admin.text:
        raise RuntimeError("hermeneutic-admin invalide")

    admin_old = _http_json("GET", f"{base_url}/admin-old")
    if admin_old.status_code != 404:
        raise RuntimeError("admin-old devrait etre absent (404)")

    conv_list = _http_json("GET", f"{base_url}/api/conversations?limit=1")
    conv_payload = conv_list.json()
    if conv_list.status_code != 200 or conv_payload.get("ok") is not True:
        raise RuntimeError("api conversations invalide")
    if not isinstance(conv_payload.get("items"), list):
        raise RuntimeError("api conversations sans items")

    admin_settings = _http_json("GET", f"{base_url}/api/admin/settings", **_admin_request_kwargs())
    admin_settings_payload = admin_settings.json()
    if admin_settings.status_code != 200 or admin_settings_payload.get("ok") is not True:
        raise RuntimeError("api admin settings invalide")
    if not isinstance(admin_settings_payload.get("sections"), dict):
        raise RuntimeError("api admin settings sans sections")
    expected_sections = set(runtime_settings.list_sections())
    if set(admin_settings_payload["sections"].keys()) != expected_sections:
        raise RuntimeError("api admin settings sections invalides")
    _assert_masked_secret_fields(
        {
            section: section_payload.get("payload")
            for section, section_payload in admin_settings_payload["sections"].items()
        }
    )
    _assert_no_env_fallback_for_persisted_non_secret_fields(
        {
            section: section_payload.get("payload")
            for section, section_payload in admin_settings_payload["sections"].items()
        },
        {
            section: {
                "source": section_payload.get("source"),
                "source_reason": section_payload.get("source_reason"),
            }
            for section, section_payload in admin_settings_payload["sections"].items()
        },
    )

    resources_get = _http_json("GET", f"{base_url}/api/admin/settings/resources", **_admin_request_kwargs())
    resources_payload = resources_get.json()
    if resources_get.status_code != 200 or resources_payload.get("ok") is not True:
        raise RuntimeError("api admin resources invalide")
    resources_patch_payload = _build_non_secret_patch_payload(resources_payload.get("payload") or {})
    resources_patch = _http_json(
        "PATCH",
        f"{base_url}/api/admin/settings/resources",
        json={"updated_by": "minimal_validation", "payload": resources_patch_payload},
        **_admin_request_kwargs(),
    )
    resources_patch_result = resources_patch.json()
    if resources_patch.status_code != 200 or resources_patch_result.get("ok") is not True:
        raise RuntimeError("api admin resources patch invalide")
    resources_invalid_patch = _http_json(
        "PATCH",
        f"{base_url}/api/admin/settings/resources",
        json={"updated_by": "minimal_validation", "payload": {"llm_identity_path": {"value": 123}}},
        **_admin_request_kwargs(),
    )
    resources_invalid_patch_result = resources_invalid_patch.json()
    if resources_invalid_patch.status_code != 400 or resources_invalid_patch_result.get("ok") is not False:
        raise RuntimeError("api admin resources invalid patch should fail with 400")
    if "invalid text value for resources.llm_identity_path" not in str(resources_invalid_patch_result.get("error") or ""):
        raise RuntimeError("api admin resources invalid patch error invalide")

    admin_logs = _http_json("GET", f"{base_url}/api/admin/logs?limit=1", **_admin_request_kwargs())
    admin_logs_payload = admin_logs.json()
    if admin_logs.status_code != 200 or admin_logs_payload.get("ok") is not True:
        raise RuntimeError("api admin logs invalide")
    if not isinstance(admin_logs_payload.get("logs"), list):
        raise RuntimeError("api admin logs sans logs")

    random_id = str(uuid.uuid4())
    missing = _http_json("GET", f"{base_url}/api/conversations/{random_id}/messages")
    missing_payload = missing.json()
    if missing.status_code != 404:
        raise RuntimeError("route conversation manquante devrait renvoyer 404")
    if missing_payload.get("ok") is not False:
        raise RuntimeError("payload conversation manquante invalide")

    return {
        "root_status": root.status_code,
        "admin_status": admin.status_code,
        "hermeneutic_admin_status": hermeneutic_admin.status_code,
        "admin_old_status": admin_old.status_code,
        "conversations_status": conv_list.status_code,
        "admin_settings_status": admin_settings.status_code,
        "admin_resources_status": resources_get.status_code,
        "admin_resources_patch_status": resources_patch.status_code,
        "admin_resources_invalid_patch_status": resources_invalid_patch.status_code,
        "admin_logs_status": admin_logs.status_code,
        "missing_conversation_status": missing.status_code,
    }


def _check_legacy_json_guard(base_url: str) -> Dict[str, Any]:
    legacy_id = str(uuid.uuid4())
    legacy_path = conv_store.CONV_DIR / f"{legacy_id}.json"
    payload = {
        "id": legacy_id,
        "title": "LEGACY JSON VALIDATION",
        "created_at": "2026-03-23T09:00:00Z",
        "updated_at": "2026-03-23T09:00:00Z",
        "messages": [
            {"role": "system", "content": "", "timestamp": "2026-03-23T09:00:00Z"},
            {"role": "user", "content": "legacy should stay ignored", "timestamp": "2026-03-23T09:00:00Z"},
        ],
    }

    conv_store.ensure_conv_dir()
    legacy_path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    try:
        get_messages = _http_json("GET", f"{base_url}/api/conversations/{legacy_id}/messages")
        if get_messages.status_code != 404:
            raise RuntimeError("fallback JSON encore actif sur GET /messages")

        chat = _http_json(
            "POST",
            f"{base_url}/api/chat",
            json={
                "conversation_id": legacy_id,
                "message": "validation legacy json guard",
            },
        )
        if chat.status_code != 404:
            raise RuntimeError("fallback JSON encore actif sur POST /api/chat")

        return {
            "legacy_id": legacy_id,
            "messages_status": get_messages.status_code,
            "chat_status": chat.status_code,
        }
    finally:
        if legacy_path.exists():
            legacy_path.unlink()


def _format_text(summary: Dict[str, Any]) -> str:
    lines = [
        f"Minimal validation: {'OK' if summary['ok'] else 'FAIL'}",
        f"Checks: {summary['passed']}/{summary['total']}",
    ]
    for item in summary["results"]:
        prefix = "[OK]" if item["ok"] else "[KO]"
        lines.append(f"{prefix} {item['name']}")
        details = item.get("details") or item.get("error")
        if details:
            lines.append(f"  {details}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validation minimale FridaDev")
    parser.add_argument(
        "--base-url",
        default=f"http://127.0.0.1:{config.WEB_PORT}",
        help="URL de base du runtime FridaDev",
    )
    parser.add_argument(
        "--skip-live",
        action="store_true",
        help="Ne pas executer les checks HTTP live",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Sortie JSON",
    )
    args = parser.parse_args()

    results: List[Dict[str, Any]] = []
    _run_check(results, "startup_import", _check_startup_import)
    _run_check(results, "db_schema", _check_db_schema)
    _run_check(results, "prompt_files", _check_prompt_files)
    _run_check(results, "ui_assets", _check_ui_assets)

    if not args.skip_live:
        _run_check(results, "api_smoke", lambda: _check_api_smoke(args.base_url))
        _run_check(results, "legacy_json_guard", lambda: _check_legacy_json_guard(args.base_url))

    passed = sum(1 for item in results if item["ok"])
    total = len(results)
    summary = {
        "ok": passed == total,
        "base_url": args.base_url,
        "passed": passed,
        "total": total,
        "results": results,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=True, sort_keys=True, indent=2))
    else:
        print(_format_text(summary))

    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
