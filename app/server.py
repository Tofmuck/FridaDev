#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import codecs
import logging
import re
import time
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Any

import requests
from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context

import config
from core import llm_client as llm
from core import prompt_loader
from tools import web_search as ws
from core import conv_store
from core import chat_service
from core import conversations_service
from admin import (
    admin_identity_governance_service,
    admin_identity_static_edit_service,
    admin_identity_mutable_edit_service,
    admin_identity_read_model_service,
    admin_logs,
    admin_hermeneutics_service,
    admin_settings_service,
)
from admin import admin_actions
from admin import runtime_settings
from core import token_utils
from identity import identity
from identity import static_identity_content
from memory import summarizer
from memory import memory_store
from memory import arbiter
from observability import chat_turn_logger
from observability import log_store
from observability import log_markdown_export
from observability import prompt_injection_summary


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return 'missing'


def _runtime_fingerprint() -> dict[str, str]:
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

def _parse_admin_cidr_allowlist(raw_cidrs: str) -> list[Any]:
    allowlist: list[Any] = []
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


_ADMIN_SETTINGS_PREFIX = '/api/admin/settings'
_ADMIN_SETTINGS_ROUTE_SECTIONS = {
    'main-model': 'main_model',
    'arbiter-model': 'arbiter_model',
    'summary-model': 'summary_model',
    'stimmung-agent-model': 'stimmung_agent_model',
    'validation-agent-model': 'validation_agent_model',
    'embedding': 'embedding',
    'database': 'database',
    'services': 'services',
    'resources': 'resources',
}


def _assistant_message_count(conversation: dict[str, Any]) -> int:
    messages = conversation.get('messages', [])
    if not isinstance(messages, list):
        return 0
    return sum(1 for message in messages if str(message.get('role') or '') == 'assistant')


class _ConvStoreChatLogProxy:
    def __init__(self, base_module: Any, token_utils_module: Any) -> None:
        self._base = base_module
        self._token_utils = token_utils_module

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    def load_conversation(self, conversation_id: str, system_prompt: str):
        conversation = self._base.load_conversation(conversation_id, system_prompt)
        if isinstance(conversation, dict):
            chat_turn_logger.update_conversation_id(str(conversation.get('id') or ''))
        return conversation

    def new_conversation(self, system_prompt: str, conversation_id: str | None = None, title: str = ''):
        if conversation_id is None and not title:
            conversation = self._base.new_conversation(system_prompt)
        else:
            try:
                conversation = self._base.new_conversation(
                    system_prompt,
                    conversation_id=conversation_id,
                    title=title,
                )
            except TypeError:
                # Compatibility with legacy test doubles exposing `new_conversation(system_prompt)` only.
                conversation = self._base.new_conversation(system_prompt)
        if isinstance(conversation, dict):
            chat_turn_logger.update_conversation_id(str(conversation.get('id') or ''))
        return conversation

    def build_prompt_messages(self, conversation: dict[str, Any], model: str, **kwargs: Any):
        prompt_messages = self._base.build_prompt_messages(conversation, model, **kwargs)
        try:
            estimated_context_tokens = int(self._token_utils.estimate_tokens(prompt_messages, model))
        except Exception:
            estimated_context_tokens = 0

        memory_prompt_injection = prompt_injection_summary.build_memory_prompt_injection_summary(
            prompt_messages,
            memory_traces=kwargs.get('memory_traces'),
            context_hints=kwargs.get('context_hints'),
        )
        memory_items_used = int(memory_prompt_injection.get('memory_traces_injected_count') or 0)
        chat_turn_logger.set_state('memory_prompt_injection', memory_prompt_injection)
        chat_turn_logger.set_state('memory_items_used', memory_items_used)

        token_limit = int(config.MAX_TOKENS)
        chat_turn_logger.emit(
            'context_build',
            status='ok',
            payload={
                'estimated_context_tokens': estimated_context_tokens,
                'token_limit': token_limit,
                'truncated': bool(estimated_context_tokens >= token_limit),
            },
        )

        summary_count_used = sum(
            1
            for message in prompt_messages
            if str(message.get('role') or '') == 'system'
            and str(message.get('content') or '').startswith('[Résumé actif')
        )
        if summary_count_used > 0:
            chat_turn_logger.emit(
                'summaries',
                status='ok',
                payload={
                    'active_summary_present': True,
                    'summary_count_used': summary_count_used,
                    'summary_usage': 'prompt_injection',
                    'in_prompt': True,
                    'summary_generation_observed': False,
                },
            )
        else:
            chat_turn_logger.emit(
                'summaries',
                status='skipped',
                reason_code='no_data',
                payload={
                    'active_summary_present': False,
                    'summary_count_used': 0,
                    'summary_usage': 'prompt_injection',
                    'in_prompt': False,
                    'summary_generation_observed': False,
                },
            )
            chat_turn_logger.emit_branch_skipped(
                reason_code='no_data',
                reason_short='no_active_summary_in_prompt',
            )

        return prompt_messages

    def save_conversation(self, conversation: dict[str, Any], *args: Any, **kwargs: Any):
        result = self._base.save_conversation(conversation, *args, **kwargs)
        chat_turn_logger.emit(
            'persist_response',
            status='ok',
            payload={
                'conversation_saved': True,
                'messages_written': _assistant_message_count(conversation),
            },
        )
        return result


class _LlmChatLogProxy:
    def __init__(self, base_module: Any, token_utils_module: Any) -> None:
        self._base = base_module
        self._token_utils = token_utils_module

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    def build_payload(
        self,
        messages: list[dict[str, Any]],
        temperature: float,
        top_p: float,
        max_tokens: int,
        *,
        stream: bool = False,
    ) -> dict[str, Any]:
        payload = self._base.build_payload(messages, temperature, top_p, max_tokens, stream=stream)
        model = str(payload.get('model') or '')
        try:
            estimated_prompt_tokens = int(self._token_utils.estimate_tokens(messages, model))
        except Exception:
            estimated_prompt_tokens = 0
        memory_prompt_injection = chat_turn_logger.get_state('memory_prompt_injection')
        if not isinstance(memory_prompt_injection, dict):
            memory_prompt_injection = prompt_injection_summary.empty_memory_prompt_injection_summary()
        chat_turn_logger.emit(
            'prompt_prepared',
            status='ok',
            model=model,
            prompt_kind='chat_system_augmented',
            payload={
                'messages_count': len(messages),
                'estimated_prompt_tokens': estimated_prompt_tokens,
                'memory_items_used': int(chat_turn_logger.get_state('memory_items_used', 0) or 0),
                'memory_prompt_injection': dict(memory_prompt_injection),
            },
        )
        return payload


class _RequestsChatLogProxy:
    def __init__(self, base_module: Any) -> None:
        self._base = base_module

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    def post(self, url: str, *args: Any, **kwargs: Any):
        is_llm_call = '/chat/completions' in str(url)
        started_at = time.perf_counter()
        payload = kwargs.get('json') or {}
        headers = kwargs.get('headers') or {}
        model = str(payload.get('model') or '')
        stream_mode = bool(kwargs.get('stream'))
        timeout_s = kwargs.get('timeout')
        provider_caller = llm.resolve_provider_caller_from_headers(headers)
        provider_title = str(
            headers.get('X-OpenRouter-Title')
            or headers.get('X-Title')
            or llm.resolve_provider_title(provider_caller)
            or ''
        )
        provider_identity_payload = {
            'provider_caller': provider_caller,
            'provider_title': provider_title,
        }
        request_kwargs = kwargs
        sanitized_headers = llm.strip_internal_provider_headers(headers)
        if sanitized_headers != headers:
            request_kwargs = dict(kwargs)
            request_kwargs['headers'] = sanitized_headers

        try:
            response = self._base.post(url, *args, **request_kwargs)
        except Exception as exc:
            if is_llm_call:
                chat_turn_logger.set_state('llm_stream_call_meta', None)
                chat_turn_logger.set_state('llm_provider_response_meta', None)
                chat_turn_logger.emit(
                    'llm_call',
                    status='error',
                    model=model,
                    duration_ms=(time.perf_counter() - started_at) * 1000.0,
                    error_code='upstream_error',
                    payload={
                        'mode': 'stream' if stream_mode else 'json',
                        'timeout_s': timeout_s,
                        'response_chars': 0,
                        'error_class': exc.__class__.__name__,
                        **provider_identity_payload,
                    },
                )
                chat_turn_logger.emit_error(
                    error_code='upstream_error',
                    error_class=exc.__class__.__name__,
                    message_short=str(exc),
                )
            raise

        if is_llm_call:
            if stream_mode:
                chat_turn_logger.set_state(
                    'llm_stream_call_meta',
                    {
                        'model': model,
                        'timeout_s': timeout_s,
                        'started_at': started_at,
                        **provider_identity_payload,
                    },
                )
            else:
                response_chars = 0
                provider_fields = dict(provider_identity_payload)
                try:
                    llm_json = llm.read_openrouter_response_payload(response)
                    response_chars = len(str(llm.extract_openrouter_text(llm_json) or ''))
                    provider_fields.update(
                        llm.build_provider_observability_fields(
                            caller=provider_caller,
                            provider_metadata=llm.extract_openrouter_provider_metadata(
                                llm_json,
                                requested_model=model,
                            ),
                        )
                    )
                    if provider_title:
                        provider_fields['provider_title'] = provider_title
                except Exception:
                    response_chars = 0

                chat_turn_logger.emit(
                    'llm_call',
                    status='ok',
                    model=model,
                    duration_ms=(time.perf_counter() - started_at) * 1000.0,
                    payload={
                        'mode': 'json',
                        'timeout_s': timeout_s,
                        'response_chars': response_chars,
                        **provider_fields,
                    },
                )
        return response


class _AdminLogsChatLogProxy:
    def __init__(self, base_module: Any) -> None:
        self._base = base_module

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    def log_event(self, event: str, level: str = 'INFO', **fields: Any) -> None:
        self._base.log_event(event, level=level, **fields)
        if event == 'llm_provider_response':
            provider_fields = {
                key: value
                for key, value in fields.items()
                if str(key).startswith('provider_')
            }
            chat_turn_logger.set_state('llm_provider_response_meta', provider_fields)
            return
        if event in {'llm_error', 'llm_stream_error'}:
            chat_turn_logger.emit_error(
                error_code='upstream_error',
                error_class=event,
                message_short=str(fields.get('error') or 'llm error'),
            )


# ── /api/chat ─────────────────────────────────────────────────────────────────

@app.post("/api/chat")
def api_chat():
    data = request.get_json(force=True, silent=True) or {}
    user_msg = str(data.get('message') or '')
    web_search_on = bool(data.get('web_search'))
    conversation_id_hint = conv_store.normalize_conversation_id(data.get('conversation_id'))
    turn_token = chat_turn_logger.begin_turn(
        conversation_id=conversation_id_hint,
        user_msg=user_msg,
        web_search_enabled=web_search_on,
    )
    if not web_search_on:
        chat_turn_logger.emit(
            'web_search',
            status='skipped',
            reason_code='feature_disabled',
            payload={
                'enabled': False,
                'query_preview': '',
                'results_count': 0,
                'context_injected': False,
                'truncated': False,
            },
        )
        chat_turn_logger.emit_branch_skipped(
            reason_code='feature_disabled',
            reason_short='web_search_disabled',
        )

    conv_proxy = _ConvStoreChatLogProxy(conv_store, token_utils)
    llm_proxy = _LlmChatLogProxy(llm, token_utils)
    requests_proxy = _RequestsChatLogProxy(requests)
    admin_logs_proxy = _AdminLogsChatLogProxy(admin_logs)

    try:
        result = chat_service.chat_response(
            data,
            prompt_loader_module=prompt_loader,
            conv_store_module=conv_proxy,
            memory_store_module=memory_store,
            runtime_settings_module=runtime_settings,
            summarizer_module=summarizer,
            identity_module=identity,
            admin_logs_module=admin_logs_proxy,
            llm_module=llm_proxy,
            requests_module=requests_proxy,
            token_utils_module=token_utils,
            arbiter_module=arbiter,
            web_search_module=ws,
            config_module=config,
            logger=logger,
        )
    except Exception as exc:
        chat_turn_logger.emit_error(
            error_code='upstream_error',
            error_class=exc.__class__.__name__,
            message_short=str(exc),
        )
        chat_turn_logger.end_turn(turn_token, final_status='error')
        raise

    if result['kind'] == 'stream':
        def _stream_with_turn_finalize():
            final_status = 'ok'
            stream_response_chars = 0
            stream_chunk_count = 0
            llm_call_error_class: str | None = None
            utf8_decoder = codecs.getincrementaldecoder('utf-8')('ignore')
            try:
                for chunk in result['stream']:
                    if isinstance(chunk, (bytes, bytearray)):
                        stream_response_chars += len(utf8_decoder.decode(bytes(chunk), final=False))
                    else:
                        stream_response_chars += len(str(chunk or ''))
                    stream_chunk_count += 1
                    yield chunk
            except Exception as exc:
                final_status = 'error'
                llm_call_error_class = exc.__class__.__name__
                chat_turn_logger.emit_error(
                    error_code='upstream_error',
                    error_class=exc.__class__.__name__,
                    message_short=str(exc),
                )
                raise
            finally:
                stream_meta = chat_turn_logger.get_state('llm_stream_call_meta', {}) or {}
                stream_started_at = stream_meta.get('started_at')
                if isinstance(stream_started_at, (int, float)):
                    llm_call_duration_ms = max(0.0, (time.perf_counter() - float(stream_started_at)) * 1000.0)
                else:
                    llm_call_duration_ms = None

                # Flush pending UTF-8 continuation bytes to keep response_chars accurate
                # when a multi-byte character spans two streamed byte chunks.
                stream_response_chars += len(utf8_decoder.decode(b'', final=True))

                llm_payload = {
                    'mode': 'stream',
                    'timeout_s': stream_meta.get('timeout_s'),
                    'response_chars': stream_response_chars,
                    'stream_chunks': stream_chunk_count,
                }
                provider_meta = chat_turn_logger.get_state('llm_provider_response_meta', {}) or {}
                if isinstance(provider_meta, dict):
                    llm_payload.update(provider_meta)
                for key in ('provider_caller', 'provider_title'):
                    if key not in llm_payload and stream_meta.get(key):
                        llm_payload[key] = stream_meta.get(key)
                llm_status = 'error' if llm_call_error_class else 'ok'
                if llm_call_error_class:
                    llm_payload['error_class'] = llm_call_error_class
                chat_turn_logger.emit(
                    'llm_call',
                    status=llm_status,
                    model=str(stream_meta.get('model') or ''),
                    duration_ms=llm_call_duration_ms,
                    error_code='upstream_error' if llm_call_error_class else None,
                    payload=llm_payload,
                )
                chat_turn_logger.set_state('llm_stream_call_meta', None)
                chat_turn_logger.set_state('llm_provider_response_meta', None)
                chat_turn_logger.end_turn(turn_token, final_status=final_status)

        response = Response(
            stream_with_context(_stream_with_turn_finalize()),
            content_type='text/plain; charset=utf-8',
        )
        for key, value in result['headers'].items():
            response.headers[key] = value
        return response

    status_code = int(result['status'])
    final_status = 'ok' if status_code < 400 else 'error'
    if final_status == 'error':
        error_payload = result['payload'] if isinstance(result.get('payload'), dict) else {}
        chat_turn_logger.emit_error(
            error_code='upstream_error' if status_code >= 500 else 'not_applicable',
            error_class='chat_response_error',
            message_short=str(error_payload.get('error') or f'chat status {status_code}'),
        )

    response = jsonify(result['payload'])
    response.status_code = status_code
    for key, value in result['headers'].items():
        response.headers[key] = value
    chat_turn_logger.end_turn(turn_token, final_status=final_status)
    return response


# ── /api/admin/* ──────────────────────────────────────────────────────────────


def _admin_settings_section_response(section: str) -> dict[str, Any]:
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


@app.get(f'{_ADMIN_SETTINGS_PREFIX}/stimmung-agent-model')
def api_admin_settings_stimmung_agent_model_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['stimmung-agent-model'])


@app.get(f'{_ADMIN_SETTINGS_PREFIX}/validation-agent-model')
def api_admin_settings_validation_agent_model_get():
    return _admin_settings_single_section_json(_ADMIN_SETTINGS_ROUTE_SECTIONS['validation-agent-model'])


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


@app.patch(f'{_ADMIN_SETTINGS_PREFIX}/stimmung-agent-model')
def api_admin_settings_stimmung_agent_model_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['stimmung-agent-model'])


@app.patch(f'{_ADMIN_SETTINGS_PREFIX}/validation-agent-model')
def api_admin_settings_validation_agent_model_patch():
    return _admin_settings_section_patch_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['validation-agent-model'])


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


@app.post(f'{_ADMIN_SETTINGS_PREFIX}/stimmung-agent-model/validate')
def api_admin_settings_stimmung_agent_model_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['stimmung-agent-model'])


@app.post(f'{_ADMIN_SETTINGS_PREFIX}/validation-agent-model/validate')
def api_admin_settings_validation_agent_model_validate():
    return _admin_settings_section_validate_response(_ADMIN_SETTINGS_ROUTE_SECTIONS['validation-agent-model'])


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


@app.get('/api/admin/logs/chat')
def api_admin_chat_logs():
    raw_limit = request.args.get('limit', '100')
    raw_offset = request.args.get('offset', '0')
    try:
        limit = int(raw_limit)
        offset = int(raw_offset)
    except ValueError:
        return jsonify({'ok': False, 'error': 'invalid pagination parameters'}), 400

    if limit <= 0 or offset < 0:
        return jsonify({'ok': False, 'error': 'invalid pagination parameters'}), 400

    try:
        listing = log_store.read_chat_log_events(
            limit=limit,
            offset=offset,
            conversation_id=request.args.get('conversation_id'),
            turn_id=request.args.get('turn_id'),
            stage=request.args.get('stage'),
            status=request.args.get('status'),
            ts_from=request.args.get('ts_from'),
            ts_to=request.args.get('ts_to'),
        )
    except ValueError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400

    return jsonify(
        {
            'ok': True,
            'items': listing['items'],
            'count': listing['count'],
            'total': listing['total'],
            'limit': listing['limit'],
            'offset': listing['offset'],
            'next_offset': listing['next_offset'],
            'filters': listing['filters'],
        }
    )


@app.get('/api/admin/logs/chat/metadata')
def api_admin_chat_logs_metadata():
    try:
        metadata = log_store.read_chat_log_metadata(
            conversation_id=request.args.get('conversation_id'),
        )
    except ValueError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 500

    return jsonify(
        {
            'ok': True,
            'selected_conversation_id': metadata['selected_conversation_id'],
            'conversations': metadata['conversations'],
            'turns': metadata['turns'],
        }
    )


@app.delete('/api/admin/logs/chat')
def api_admin_chat_logs_delete():
    try:
        deletion = log_store.delete_chat_log_events(
            conversation_id=request.args.get('conversation_id'),
            turn_id=request.args.get('turn_id'),
        )
    except ValueError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 500

    return jsonify(
        {
            'ok': True,
            'scope': deletion['scope'],
            'conversation_id': deletion['conversation_id'],
            'turn_id': deletion['turn_id'],
            'deleted_count': deletion['deleted_count'],
        }
    )


def _safe_export_filename_token(value: str | None, fallback: str) -> str:
    token = str(value or '').strip()
    if not token:
        return fallback
    normalized = re.sub(r'[^a-zA-Z0-9._-]+', '-', token).strip('-')
    return normalized or fallback


@app.get('/api/admin/logs/chat/export.md')
def api_admin_chat_logs_export_markdown():
    conversation_id = request.args.get('conversation_id')
    turn_id = request.args.get('turn_id')
    try:
        exported = log_markdown_export.export_chat_logs_markdown(
            conversation_id=conversation_id,
            turn_id=turn_id,
        )
    except ValueError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 500

    conversation_slug = _safe_export_filename_token(exported['conversation_id'], 'conversation')
    if exported['scope'] == 'turn':
        turn_slug = _safe_export_filename_token(exported['turn_id'], 'turn')
        filename = f'chat-logs-{conversation_slug}-{turn_slug}.md'
    else:
        filename = f'chat-logs-{conversation_slug}.md'

    response = Response(exported['markdown'], content_type='text/markdown; charset=utf-8')
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@app.post("/api/admin/restart")
def api_admin_restart():
    admin_actions.restart_runtime_async("FridaDev")
    return jsonify({"ok": True, "target": "FridaDev", "mode": "container_self_exit"})


@app.get('/api/admin/identity/read-model')
def api_admin_identity_read_model():
    payload, status = admin_identity_read_model_service.identity_read_model_response(
        request.args,
        memory_store_module=memory_store,
        identity_module=identity,
        static_identity_content_module=static_identity_content,
    )
    return jsonify(payload), status


@app.post('/api/admin/identity/mutable')
def api_admin_identity_mutable_edit():
    data = request.get_json(force=True, silent=True) or {}
    payload, status = admin_identity_mutable_edit_service.identity_mutable_edit_response(
        data,
        memory_store_module=memory_store,
        admin_logs_module=admin_logs,
    )
    return jsonify(payload), status


@app.post('/api/admin/identity/static')
def api_admin_identity_static_edit():
    data = request.get_json(force=True, silent=True) or {}
    payload, status = admin_identity_static_edit_service.identity_static_edit_response(
        data,
        static_identity_content_module=static_identity_content,
        admin_logs_module=admin_logs,
    )
    return jsonify(payload), status


@app.get('/api/admin/identity/governance')
def api_admin_identity_governance():
    payload, status = admin_identity_governance_service.identity_governance_response(
        request.args,
        runtime_settings_module=runtime_settings,
        identity_module=identity,
    )
    return jsonify(payload), status


@app.post('/api/admin/identity/governance')
def api_admin_identity_governance_update():
    data = request.get_json(force=True, silent=True) or {}
    payload, status = admin_identity_governance_service.identity_governance_update_response(
        data,
        runtime_settings_module=runtime_settings,
        admin_logs_module=admin_logs,
        identity_module=identity,
    )
    return jsonify(payload), status



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


@app.get("/log")
def log_root():
    return send_from_directory(app.static_folder, "log.html")


@app.get("/hermeneutic-admin")
def hermeneutic_admin_root():
    return send_from_directory(app.static_folder, "hermeneutic-admin.html")


if __name__ == "__main__":
    app.run(host=config.WEB_HOST, port=config.WEB_PORT)
