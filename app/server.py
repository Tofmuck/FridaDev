#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import json
import logging
import time
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Any, Dict, List

import requests
from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import config
from core import llm_client as llm
from core import prompt_loader
from tools import web_search as ws
from core import conv_store
from core import chat_service
from core import conversations_service
from admin import admin_logs, admin_hermeneutics_service, admin_settings_service
from admin import admin_actions
from admin import runtime_settings
from core import token_utils
from identity import identity
from memory import summarizer
from memory import memory_store
from memory import arbiter


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return 'missing'


def _runtime_fingerprint() -> Dict[str, str]:
    app_dir = Path(__file__).resolve().parent
    config_path = app_dir / 'config.py'
    conv_dir = Path(getattr(conv_store, 'CONV_DIR', app_dir / 'conv'))
    logs_path = Path(getattr(admin_logs, 'LOG_PATH', app_dir / 'logs' / 'admin.log.jsonl'))
    return {
        'config_path': str(config_path),
        'config_sha256': _sha256_file(config_path),
        'conv_dir': str(conv_dir),
        'logs_path': str(logs_path),
    }


app = Flask(__name__, static_folder="web", static_url_path="")
logging.basicConfig(level="INFO")
logger = logging.getLogger("frida.server")
config.log_hermeneutic_effective_config(logger)
try:
    _runtime_settings_db_init = runtime_settings.init_runtime_settings_db()
except RuntimeError as exc:
    logger.error('runtime_settings_init_failed err=%s', exc)
else:
    logger.info(
        'runtime_settings_init_ok tables=%s sql=%s',
        ','.join(_runtime_settings_db_init['tables']),
        _runtime_settings_db_init['sql_path'],
    )
try:
    _runtime_settings_bootstrap = runtime_settings.bootstrap_runtime_settings_from_env()
except runtime_settings.RuntimeSettingsDbUnavailableError as exc:
    logger.error('runtime_settings_bootstrap_failed err=%s', exc)
else:
    logger.info(
        'runtime_settings_bootstrap inserted_sections=%s inserted_fields=%s updated_sections=%s updated_fields=%s',
        ','.join(_runtime_settings_bootstrap['inserted_sections']) or 'none',
        len(_runtime_settings_bootstrap['inserted_fields']),
        ','.join(_runtime_settings_bootstrap['updated_sections']) or 'none',
        len(_runtime_settings_bootstrap['updated_fields']),
    )
conv_store.ensure_conv_dir()
memory_store.init_db()
conv_store.init_catalog_db()
conv_store.init_messages_db()
try:
    _runtime_secret_backfill = runtime_settings.backfill_runtime_secrets_from_env()
except (runtime_settings.RuntimeSettingsDbUnavailableError, runtime_settings.runtime_secrets.RuntimeSettingsCryptoKeyMissingError) as exc:
    logger.info('runtime_secret_backfill skipped reason=%s', exc)
else:
    logger.info(
        'runtime_secret_backfill updated_fields=%s updated_sections=%s',
        len(_runtime_secret_backfill['updated_fields']),
        ','.join(_runtime_secret_backfill['updated_sections']) or 'none',
    )
logger.info('conv_json_bootstrap disabled for db_only_migration')

_RUNTIME_FINGERPRINT = _runtime_fingerprint()
logger.info(
    'runtime_fingerprint config=%s sha256=%s conv_dir=%s logs=%s',
    _RUNTIME_FINGERPRINT['config_path'],
    _RUNTIME_FINGERPRINT['config_sha256'],
    _RUNTIME_FINGERPRINT['conv_dir'],
    _RUNTIME_FINGERPRINT['logs_path'],
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log_stage_latency(conversation_id: str, stage: str, started_at: float) -> float:
    duration_ms = max(0.0, (time.perf_counter() - started_at) * 1000.0)
    admin_logs.log_event(
        'stage_latency',
        conversation_id=conversation_id,
        stage=stage,
        duration_ms=round(duration_ms, 3),
    )
    return duration_ms


def _parse_admin_cidr_allowlist(raw_cidrs: str) -> List[Any]:
    allowlist: List[Any] = []
    for raw in str(raw_cidrs or '').split(','):
        cidr = raw.strip()
        if not cidr:
            continue
        try:
            allowlist.append(ip_network(cidr, strict=False))
        except ValueError:
            logger.warning('admin_allowlist_invalid_cidr cidr=%s', cidr)
    return allowlist


def _get_client_ip() -> str:
    forwarded_for = str(request.headers.get('X-Forwarded-For', '') or '').strip()
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return str(request.remote_addr or '').strip()


def _is_admin_ip_allowed(client_ip: str) -> bool:
    if not client_ip:
        return False
    try:
        ip = ip_address(client_ip)
    except ValueError:
        return False
    allowlist = _parse_admin_cidr_allowlist(config.FRIDA_ADMIN_ALLOWED_CIDRS)
    if not allowlist:
        return False
    return any(ip in network for network in allowlist)


def _admin_auth_error(reason: str, status_code: int, client_ip: str):
    admin_logs.log_event(
        'admin_access_denied',
        level='WARN',
        reason=reason,
        path=request.path,
        method=request.method,
        client_ip=client_ip,
    )
    return jsonify({'ok': False, 'error': 'admin access denied'}), status_code


@app.before_request
def enforce_admin_guard():
    if not request.path.startswith('/api/admin/'):
        return None

    client_ip = _get_client_ip()

    if config.FRIDA_ADMIN_LAN_ONLY and not _is_admin_ip_allowed(client_ip):
        return _admin_auth_error('ip_not_allowed', 403, client_ip)

    expected_token = str(config.FRIDA_ADMIN_TOKEN or '').strip()
    if expected_token:
        token = str(request.headers.get('X-Admin-Token', '') or '').strip()
        if token != expected_token:
            return _admin_auth_error('invalid_or_missing_token', 401, client_ip)

    return None


_HERMENEUTIC_MODE_OFF = 'off'
_HERMENEUTIC_MODE_SHADOW = 'shadow'
_HERMENEUTIC_MODE_ENFORCED_IDENTITIES = 'enforced_identities'
_HERMENEUTIC_MODE_ENFORCED_ALL = 'enforced_all'
_ADMIN_SETTINGS_PREFIX = '/api/admin/settings'
_ADMIN_SETTINGS_ROUTE_SECTIONS = {
    'main-model': 'main_model',
    'arbiter-model': 'arbiter_model',
    'summary-model': 'summary_model',
    'embedding': 'embedding',
    'database': 'database',
    'services': 'services',
    'resources': 'resources',
}


def _hermeneutic_mode() -> str:
    mode = str(config.HERMENEUTIC_MODE or _HERMENEUTIC_MODE_SHADOW).strip().lower()
    if mode == 'enforced':
        return _HERMENEUTIC_MODE_ENFORCED_ALL
    return mode


def _mode_runs_arbiter(mode: str) -> bool:
    return mode in {
        _HERMENEUTIC_MODE_SHADOW,
        _HERMENEUTIC_MODE_ENFORCED_IDENTITIES,
        _HERMENEUTIC_MODE_ENFORCED_ALL,
    }


def _mode_enforces_memory(mode: str) -> bool:
    return mode == _HERMENEUTIC_MODE_ENFORCED_ALL


def _mode_runs_identity(mode: str) -> bool:
    return mode in {
        _HERMENEUTIC_MODE_SHADOW,
        _HERMENEUTIC_MODE_ENFORCED_IDENTITIES,
        _HERMENEUTIC_MODE_ENFORCED_ALL,
    }


def _mode_enforces_identity(mode: str) -> bool:
    return mode in {
        _HERMENEUTIC_MODE_ENFORCED_IDENTITIES,
        _HERMENEUTIC_MODE_ENFORCED_ALL,
    }


def _record_identity_entries_for_mode(
    conversation_id: str,
    recent_turns: List[Dict[str, Any]],
    mode: str,
) -> None:
    if not _mode_runs_identity(mode):
        admin_logs.log_event(
            'identity_mode_apply',
            conversation_id=conversation_id,
            mode=mode,
            action='skip_mode_off',
            entries=0,
        )
        return

    _extract_t0 = time.perf_counter()
    id_entries = arbiter.extract_identities(recent_turns)
    _log_stage_latency(conversation_id, 'identity_extractor', _extract_t0)

    if _mode_enforces_identity(mode):
        memory_store.persist_identity_entries(conversation_id, id_entries)
        admin_logs.log_event(
            'identity_mode_apply',
            conversation_id=conversation_id,
            mode=mode,
            action='persist_enforced',
            entries=len(id_entries),
        )
        return

    preview_entries = memory_store.preview_identity_entries(id_entries)
    memory_store.record_identity_evidence(conversation_id, preview_entries)
    admin_logs.log_event(
        'identity_mode_apply',
        conversation_id=conversation_id,
        mode=mode,
        action='record_evidence_shadow',
        entries=len(preview_entries),
    )


# ── /api/chat ─────────────────────────────────────────────────────────────────

@app.post("/api/chat")
def api_chat():
    data = request.get_json(force=True, silent=True) or {}
    result = chat_service.chat_response(
        data,
        prompt_loader_module=prompt_loader,
        conv_store_module=conv_store,
        memory_store_module=memory_store,
        runtime_settings_module=runtime_settings,
        summarizer_module=summarizer,
        identity_module=identity,
        admin_logs_module=admin_logs,
        llm_module=llm,
        requests_module=requests,
        token_utils_module=token_utils,
        arbiter_module=arbiter,
        web_search_module=ws,
        config_module=config,
        logger=logger,
        now_iso=_now_iso,
        log_stage_latency=_log_stage_latency,
        hermeneutic_mode=_hermeneutic_mode,
        mode_runs_arbiter=_mode_runs_arbiter,
        mode_enforces_memory=_mode_enforces_memory,
        mode_enforces_identity=_mode_enforces_identity,
        record_identity_entries_for_mode=_record_identity_entries_for_mode,
    )

    if result['kind'] == 'stream':
        response = Response(
            stream_with_context(result['stream']),
            content_type='text/plain; charset=utf-8',
        )
        for key, value in result['headers'].items():
            response.headers[key] = value
        return response

    response = jsonify(result['payload'])
    response.status_code = int(result['status'])
    for key, value in result['headers'].items():
        response.headers[key] = value
    return response


# ── /api/admin/* ──────────────────────────────────────────────────────────────


def _admin_settings_section_response(section: str) -> Dict[str, Any]:
    return admin_settings_service.section_response(
        section,
        runtime_settings_module=runtime_settings,
    )


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


@app.get(_ADMIN_SETTINGS_PREFIX)
def api_admin_settings():
    return jsonify(
        admin_settings_service.aggregated_settings_response(
            runtime_settings_module=runtime_settings,
        )
    )


@app.get(f'{_ADMIN_SETTINGS_PREFIX}/status')
def api_admin_settings_status():
    return _admin_settings_status_json()


@app.get(f'{_ADMIN_SETTINGS_PREFIX}/main-model')
def api_admin_settings_main_model_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['main-model'])


@app.get(f'{_ADMIN_SETTINGS_PREFIX}/arbiter-model')
def api_admin_settings_arbiter_model_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['arbiter-model'])


@app.get(f'{_ADMIN_SETTINGS_PREFIX}/summary-model')
def api_admin_settings_summary_model_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['summary-model'])


@app.get(f'{_ADMIN_SETTINGS_PREFIX}/embedding')
def api_admin_settings_embedding_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['embedding'])


@app.get(f'{_ADMIN_SETTINGS_PREFIX}/database')
def api_admin_settings_database_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['database'])


@app.get(f'{_ADMIN_SETTINGS_PREFIX}/services')
def api_admin_settings_services_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['services'])


@app.get(f'{_ADMIN_SETTINGS_PREFIX}/resources')
def api_admin_settings_resources_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['resources'])


@app.patch(f'{_ADMIN_SETTINGS_PREFIX}/resources')
def api_admin_settings_resources_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['resources'])


@app.patch(f'{_ADMIN_SETTINGS_PREFIX}/services')
def api_admin_settings_services_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['services'])


@app.patch(f'{_ADMIN_SETTINGS_PREFIX}/database')
def api_admin_settings_database_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['database'])


@app.patch(f'{_ADMIN_SETTINGS_PREFIX}/embedding')
def api_admin_settings_embedding_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['embedding'])


@app.patch(f'{_ADMIN_SETTINGS_PREFIX}/summary-model')
def api_admin_settings_summary_model_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['summary-model'])


@app.patch(f'{_ADMIN_SETTINGS_PREFIX}/arbiter-model')
def api_admin_settings_arbiter_model_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['arbiter-model'])


@app.patch(f'{_ADMIN_SETTINGS_PREFIX}/main-model')
def api_admin_settings_main_model_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['main-model'])


@app.post(f'{_ADMIN_SETTINGS_PREFIX}/main-model/validate')
def api_admin_settings_main_model_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['main-model'])


@app.post(f'{_ADMIN_SETTINGS_PREFIX}/arbiter-model/validate')
def api_admin_settings_arbiter_model_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['arbiter-model'])


@app.post(f'{_ADMIN_SETTINGS_PREFIX}/summary-model/validate')
def api_admin_settings_summary_model_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['summary-model'])


@app.post(f'{_ADMIN_SETTINGS_PREFIX}/embedding/validate')
def api_admin_settings_embedding_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['embedding'])


@app.post(f'{_ADMIN_SETTINGS_PREFIX}/database/validate')
def api_admin_settings_database_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['database'])


@app.post(f'{_ADMIN_SETTINGS_PREFIX}/services/validate')
def api_admin_settings_services_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['services'])


@app.post(f'{_ADMIN_SETTINGS_PREFIX}/resources/validate')
def api_admin_settings_resources_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['resources'])


@app.get("/api/admin/logs")
def api_admin_logs():
    raw_limit = request.args.get("limit", "200")
    try:
        limit = max(1, min(int(raw_limit), 1000))
    except ValueError:
        limit = 200
    return jsonify({"ok": True, "logs": admin_logs.read_logs(limit=limit)})


@app.post("/api/admin/restart")
def api_admin_restart():
    admin_actions.restart_runtime_async("FridaDev")
    return jsonify({"ok": True, "target": "FridaDev", "mode": "container_self_exit"})



@app.get('/api/admin/hermeneutics/identity-candidates')
def api_admin_hermeneutics_identity_candidates():
    payload, status = admin_hermeneutics_service.identity_candidates_response(
        request.args,
        memory_store_module=memory_store,
    )
    return jsonify(payload), status


@app.get('/api/admin/hermeneutics/arbiter-decisions')
def api_admin_hermeneutics_arbiter_decisions():
    payload, status = admin_hermeneutics_service.arbiter_decisions_response(
        request.args,
        memory_store_module=memory_store,
    )
    return jsonify(payload), status


@app.post('/api/admin/hermeneutics/identity/force-accept')
def api_admin_hermeneutics_identity_force_accept():
    data = request.get_json(force=True, silent=True) or {}
    payload, status = admin_hermeneutics_service.identity_force_accept_response(
        data,
        memory_store_module=memory_store,
        admin_logs_module=admin_logs,
    )
    return jsonify(payload), status


@app.post('/api/admin/hermeneutics/identity/force-reject')
def api_admin_hermeneutics_identity_force_reject():
    data = request.get_json(force=True, silent=True) or {}
    payload, status = admin_hermeneutics_service.identity_force_reject_response(
        data,
        memory_store_module=memory_store,
        admin_logs_module=admin_logs,
    )
    return jsonify(payload), status


@app.post('/api/admin/hermeneutics/identity/relabel')
def api_admin_hermeneutics_identity_relabel():
    data = request.get_json(force=True, silent=True) or {}
    payload, status = admin_hermeneutics_service.identity_relabel_response(
        data,
        memory_store_module=memory_store,
        admin_logs_module=admin_logs,
    )
    return jsonify(payload), status



@app.get('/api/admin/hermeneutics/dashboard')
def api_admin_hermeneutics_dashboard():
    payload, status = admin_hermeneutics_service.dashboard_response(
        request.args,
        memory_store_module=memory_store,
        arbiter_module=arbiter,
        admin_logs_module=admin_logs,
        config_module=config,
    )
    return jsonify(payload), status


@app.get('/api/admin/hermeneutics/corrections-export')
def api_admin_hermeneutics_corrections_export():
    payload, status = admin_hermeneutics_service.corrections_export_response(
        request.args,
        admin_logs_module=admin_logs,
    )
    return jsonify(payload), status



# ── /api/conversations* ───────────────────────────────────────────────────────

@app.get('/api/conversations')
def api_list_conversations():
    payload = conversations_service.list_conversations(
        request.args,
        conv_store_module=conv_store,
    )
    return jsonify(payload)


@app.post('/api/conversations')
def api_create_conversation():
    data = request.get_json(silent=True) or {}
    payload, status = conversations_service.create_conversation(
        data,
        conv_store_module=conv_store,
        get_main_system_prompt=prompt_loader.get_main_system_prompt,
    )
    return jsonify(payload), status


@app.get('/api/conversations/<conversation_id>/messages')
def api_get_conversation_messages(conversation_id: str):
    payload, status = conversations_service.get_conversation_messages(
        conversation_id,
        conv_store_module=conv_store,
    )
    return jsonify(payload), status


@app.patch('/api/conversations/<conversation_id>')
def api_patch_conversation(conversation_id: str):
    data = request.get_json(silent=True) or {}
    payload, status = conversations_service.patch_conversation(
        conversation_id,
        data,
        conv_store_module=conv_store,
    )
    return jsonify(payload), status


@app.delete('/api/conversations/<conversation_id>')
def api_delete_conversation(conversation_id: str):
    payload, status = conversations_service.delete_conversation(
        conversation_id,
        conv_store_module=conv_store,
    )
    return jsonify(payload), status


# ── Statiques ─────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return send_from_directory(app.static_folder, "index.html")

@app.get("/admin")
def admin_root():
    return send_from_directory(app.static_folder, "admin.html")


if __name__ == "__main__":
    app.run(host=config.WEB_HOST, port=config.WEB_PORT)
