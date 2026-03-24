#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import json
import logging
import math
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
from tools import web_search as ws
from core import conv_store
from admin import admin_logs
from admin import admin_actions
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
conv_store.ensure_conv_dir()
memory_store.init_db()
conv_store.init_catalog_db()
conv_store.init_messages_db()
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


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    rank = max(0.0, min(1.0, p)) * (len(vals) - 1)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return float(vals[lo])
    weight = rank - lo
    return float(vals[lo] * (1.0 - weight) + vals[hi] * weight)


def _compute_stage_latencies(log_entries: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    buckets: Dict[str, List[float]] = {
        'retrieve': [],
        'arbiter': [],
        'identity_extractor': [],
    }
    for entry in log_entries:
        if entry.get('event') != 'stage_latency':
            continue
        stage = str(entry.get('stage') or '').strip()
        if stage not in buckets:
            continue
        try:
            duration = float(entry.get('duration_ms') or 0.0)
        except (TypeError, ValueError):
            continue
        if duration < 0:
            continue
        buckets[stage].append(duration)

    out: Dict[str, Dict[str, float]] = {}
    for stage, values in buckets.items():
        out[stage] = {
            'count': int(len(values)),
            'p50_ms': round(_percentile(values, 0.50), 3),
            'p95_ms': round(_percentile(values, 0.95), 3),
        }
    return out


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
    data             = request.get_json(force=True, silent=True) or {}
    user_msg         = (data.get("message") or "").strip()
    system_prompt    = (data.get("system")  or "").strip()
    conversation_id_raw = data.get("conversation_id")
    temperature      = float(data.get("temperature") or 0.4)
    top_p            = float(data.get("top_p")        or 1.0)
    max_tokens       = int(data.get("max_tokens")     or 1500)
    stream_req       = bool(data.get("stream"))
    web_search_on    = bool(data.get("web_search"))

    if not user_msg:
        return jsonify({"ok": False, "error": "message vide"}), 400

    # ── Conversation
    conversation_id = conv_store.normalize_conversation_id(conversation_id_raw)
    if conversation_id:
        conversation = conv_store.load_conversation(conversation_id, system_prompt)
        if not conversation:
            return jsonify({"ok": False, "error": "conversation introuvable"}), 404
    else:
        if conversation_id_raw:
            logger.info("conv_id_invalid raw=%s", conversation_id_raw)
        conversation = conv_store.new_conversation(system_prompt)
        conv_store.save_conversation(conversation)
        logger.info("conv_created id=%s path=%s",
                    conversation["id"], conv_store.conversation_path(conversation["id"]))
        memory_store.decay_identities()  # nouvelle session → décroissance des identités

    # ── Enregistrement message utilisateur
    user_timestamp = _now_iso()
    user_tokens = token_utils.count_tokens([{"content": user_msg}], config.OR_MODEL)
    admin_logs.log_event("UserMessage", conversation_id=conversation["id"],
                         user_tokens=user_tokens, message_timestamp=user_timestamp)
    conv_store.append_message(conversation, "user", user_msg, timestamp=user_timestamp)

    # ── Résumé périodique (si seuil dépassé)
    if summarizer.maybe_summarize(conversation, config.OR_MODEL):
        conv_store.save_conversation(conversation)
        admin_logs.log_event("summary_generated", conversation_id=conversation["id"])

    # ── System prompt augmenté : identités + référence temporelle
    now_iso    = user_timestamp
    _tz_paris  = ZoneInfo(config.FRIDA_TIMEZONE)
    _now_paris = datetime.now(_tz_paris)
    now_fmt    = _now_paris.strftime("%A %d %B %Y à %H:%M") + f" (heure de Paris, UTC{_now_paris.strftime('%z')[:3]})"
    id_block, identity_ids = identity.build_identity_block()
    delta_rule = (
        f"[RÉFÉRENCE TEMPORELLE]\n"
        f"Nous sommes le {now_fmt}. C'est ton \'maintenant\'.\n"
        "Les messages ci-dessous sont horodatés relativement à ce maintenant (ex : \'il y a 2 jours\').\n"
        "Les marqueurs [\u2014 silence de X \u2014] indiquent une interruption de la conversation. "
        "Tu n'as pas à les mentionner, mais tu peux en tenir compte dans ton ton si c'est pertinent.\n"
        "Ne mentionne jamais spontanément la date ou l'heure dans tes réponses, "
        "sauf si on te le demande explicitement."
    )
    summary_rule = (
        "[MÉMOIRE RÉSUMÉE]\n"
        "Des blocs [Résumé de la période du X au Y] peuvent apparaître dans la conversation. "
        "Ils contiennent une synthèse fiable de tours de dialogue antérieurs. "
        "Traite-les comme ta mémoire du passé : appuie-toi dessus pour maintenir la continuité. "
        "Ne mentionne jamais spontanément leur existence."
    )
    memory_rule = (
        "[MÉMOIRE SÉMANTIQUE]\n"
        "Des blocs [Mémoire — souvenirs pertinents] peuvent apparaître dans la conversation. "
        "Ils contiennent des extraits de conversations passées jugés pertinents pour ta réponse. "
        "Utilise-les pour enrichir ta réponse si approprié. "
        "Ne mentionne jamais spontanément leur existence."
    )
    context_rule = (
        "[CONTEXTE DES SOUVENIRS]\n"
        "Des blocs [Contexte du souvenir — résumé du X au Y] peuvent précéder les souvenirs pertinents. "
        "Ils contiennent le résumé de la période dans laquelle s'inscrit le souvenir retenu. "
        "Utilise ce contexte pour mieux interpréter et situer le souvenir. "
        "Ne mentionne jamais spontanément leur existence."
    )
    parts = [p for p in [id_block, delta_rule, summary_rule, memory_rule, context_rule, system_prompt] if p]
    augmented_system = "\n\n".join(parts)
    if conversation["messages"] and conversation["messages"][0]["role"] == "system":
        conversation["messages"][0]["content"] = augmented_system

    # ── Récupération mémoire RAG + arbitrage
    hermeneutic_mode = _hermeneutic_mode()
    admin_logs.log_event(
        'hermeneutic_mode',
        conversation_id=conversation['id'],
        mode=hermeneutic_mode,
    )

    _retrieve_t0 = time.perf_counter()
    raw_traces = memory_store.retrieve(user_msg)
    _log_stage_latency(conversation['id'], 'retrieve', _retrieve_t0)

    recent_turns = [
        m for m in conversation.get("messages", [])
        if m.get("role") in {"user", "assistant"}
    ][-10:]

    if raw_traces:
        admin_logs.log_event("memory_retrieved", conversation_id=conversation["id"],
                             count=len(raw_traces))

        memory_traces = list(raw_traces)
        filtered_traces: List[Dict[str, Any]] = []
        arbiter_decisions: List[Dict[str, Any]] = []

        if _mode_runs_arbiter(hermeneutic_mode):
            _arbiter_t0 = time.perf_counter()
            filtered_traces, arbiter_decisions = arbiter.filter_traces_with_diagnostics(raw_traces, recent_turns)
            _log_stage_latency(conversation['id'], 'arbiter', _arbiter_t0)

            memory_store.record_arbiter_decisions(conversation["id"], raw_traces, arbiter_decisions)
            admin_logs.log_event("memory_arbitrated", conversation_id=conversation["id"],
                                 raw=len(raw_traces), kept=len(filtered_traces), decisions=len(arbiter_decisions))

            if _mode_enforces_memory(hermeneutic_mode):
                memory_traces = filtered_traces
                memory_source = 'arbiter_enforced'
            else:
                memory_source = 'raw_shadow_non_blocking'
        else:
            memory_source = 'raw_mode_off'

        admin_logs.log_event(
            'memory_mode_apply',
            conversation_id=conversation['id'],
            mode=hermeneutic_mode,
            source=memory_source,
            raw=len(raw_traces),
            selected=len(memory_traces),
            filtered=len(filtered_traces),
        )

        if memory_traces:
            memory_traces = memory_store.enrich_traces_with_summaries(memory_traces)
    else:
        memory_traces = []

    context_hints = memory_store.get_recent_context_hints(
        max_items=config.CONTEXT_HINTS_MAX_ITEMS,
        max_age_days=config.CONTEXT_HINTS_MAX_AGE_DAYS,
        min_confidence=config.CONTEXT_HINTS_MIN_CONFIDENCE,
    )
    if context_hints:
        admin_logs.log_event(
            "context_hints_selected",
            conversation_id=conversation["id"],
            count=len(context_hints),
        )

    prompt_messages = conv_store.build_prompt_messages(
        conversation,
        config.OR_MODEL,
        now=now_iso,
        memory_traces=memory_traces or None,
        context_hints=context_hints or None,
    )

    # ── Recherche web (optionnelle)
    if web_search_on:
        ctx, search_query, n_results, has_tm = ws.build_context(user_msg)
        if ctx:
            for i in range(len(prompt_messages) - 1, -1, -1):
                if prompt_messages[i].get("role") == "user":
                    prompt_messages[i] = {
                        "role": "user",
                        "content": ctx + "\n\nQuestion : " + prompt_messages[i]["content"],
                    }
                    break
            admin_logs.log_event("web_search", conversation_id=conversation["id"],
                                 query=search_query, original=user_msg,
                                 results=n_results, ticketmaster=has_tm)

    # ── Appel LLM
    if not config.OR_KEY:
        return jsonify({"ok": False, "error": "OPENROUTER_API_KEY manquant"}), 500

    headers = llm.or_headers(caller="llm")
    payload = llm.build_payload(prompt_messages, temperature, top_p, max_tokens, stream=stream_req)
    call_model = str(payload["model"])
    url     = f"{config.OR_BASE}/chat/completions"

    admin_logs.log_event("llm_payload", conversation_id=conversation["id"], model=call_model,
                         temperature=temperature, top_p=top_p, max_tokens=max_tokens,
                         stream=stream_req, message_count=len(prompt_messages))

    try:
        # ── Mode synchrone
        if not stream_req:
            logger.info("llm_call id=%s model=%s messages=%s", conversation["id"], call_model, len(prompt_messages))
            admin_logs.log_event("llm_call", conversation_id=conversation["id"],
                                 model=call_model, message_count=len(prompt_messages), stream=False)
            r = requests.post(url, json=payload, headers=headers, timeout=config.TIMEOUT_S)
            r.raise_for_status()
            obj  = r.json()
            text = llm._sanitize_encoding(obj["choices"][0]["message"]["content"])
            updated_at = _now_iso()
            conv_store.append_message(conversation, "assistant", text, timestamp=updated_at)
            assistant_tokens = token_utils.count_tokens([{"content": text}], model)
            admin_logs.log_event("AssistantText", conversation_id=conversation["id"],
                                 assistant_tokens=assistant_tokens, message_timestamp=updated_at)
            memory_store.save_new_traces(conversation)
            # Extraction identitaire sur les 2 derniers tours (user + assistant)
            recent_2 = [m for m in conversation.get("messages", [])
                        if m.get("role") in {"user", "assistant"}][-2:]
            _record_identity_entries_for_mode(conversation["id"], recent_2, hermeneutic_mode)
            # Réactivation des entrées identitaires injectées dans ce tour
            if identity_ids and _mode_enforces_identity(hermeneutic_mode):
                memory_store.reactivate_identities(identity_ids)
            conv_store.save_conversation(conversation, updated_at=updated_at)
            resp = jsonify({"ok": True, "text": text, "conversation_id": conversation["id"],
                            "created_at": conversation["created_at"], "updated_at": updated_at})
            resp.headers["X-Conversation-Id"]         = conversation["id"]
            resp.headers["X-Conversation-Created-At"] = conversation["created_at"]
            resp.headers["X-Conversation-Updated-At"] = updated_at
            return resp

        # ── Mode streaming
        response_updated_at = _now_iso()
        def event_stream():
            assistant_chunks: list[str] = []
            try:
                with requests.post(url, json=payload, headers=headers,
                                   timeout=config.TIMEOUT_S, stream=True) as resp:
                    resp.raise_for_status()
                    resp.encoding = resp.encoding or "utf-8"
                    for line in resp.iter_lines(decode_unicode=True, delimiter="\n"):
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        delta   = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            assistant_chunks.append(content)
                            yield llm._sanitize_encoding(content)
            except requests.exceptions.RequestException as exc:
                logger.error("llm_stream_error id=%s err=%s", conversation["id"], exc)
                admin_logs.log_event("llm_stream_error", level="ERROR",
                                     conversation_id=conversation["id"], model=call_model, error=str(exc))
            finally:
                assistant_text = llm._sanitize_encoding("".join(assistant_chunks)).strip()
                if assistant_text:
                    conv_store.append_message(conversation, "assistant", assistant_text, timestamp=response_updated_at)
                    assistant_tokens = token_utils.count_tokens([{"content": assistant_text}], config.OR_MODEL)
                    admin_logs.log_event("AssistantText", conversation_id=conversation["id"],
                                         assistant_tokens=assistant_tokens,
                                         message_timestamp=response_updated_at)
                memory_store.save_new_traces(conversation)
                recent_2 = [m for m in conversation.get("messages", [])
                            if m.get("role") in {"user", "assistant"}][-2:]
                _record_identity_entries_for_mode(conversation["id"], recent_2, hermeneutic_mode)
                # Réactivation des entrées identitaires injectées dans ce tour
                if identity_ids and _mode_enforces_identity(hermeneutic_mode):
                    memory_store.reactivate_identities(identity_ids)
                conv_store.save_conversation(conversation, updated_at=response_updated_at)

        logger.info("llm_call id=%s model=%s messages=%s stream=true",
                    conversation["id"], call_model, len(prompt_messages))
        admin_logs.log_event("llm_call", conversation_id=conversation["id"],
                             model=call_model, message_count=len(prompt_messages), stream=True)
        resp = Response(stream_with_context(event_stream()),
                        content_type="text/plain; charset=utf-8")
        resp.headers["X-Conversation-Id"]         = conversation["id"]
        resp.headers["X-Conversation-Created-At"] = conversation["created_at"]
        resp.headers["X-Conversation-Updated-At"] = response_updated_at
        return resp

    except requests.exceptions.RequestException as e:
        conv_store.save_conversation(conversation)
        admin_logs.log_event("llm_error", level="ERROR",
                             conversation_id=conversation["id"], model=call_model, error=str(e))
        return jsonify({"ok": False, "error": f"Connexion au LLM: {e}"}), 502
    except Exception as e:
        conv_store.save_conversation(conversation)
        admin_logs.log_event("llm_error", level="ERROR",
                             conversation_id=conversation["id"], model=call_model, error=str(e))
        return jsonify({"ok": False, "error": f"Erreur: {e}"}), 500


# ── /api/admin/* ──────────────────────────────────────────────────────────────

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
    raw_limit = request.args.get('limit', '200')
    try:
        limit = max(1, min(int(raw_limit), 1000))
    except ValueError:
        limit = 200

    raw_subject = str(request.args.get('subject', 'all') or 'all').strip().lower()
    if raw_subject in {'user', 'llm'}:
        subjects = [raw_subject]
    elif raw_subject in {'all', ''}:
        subjects = ['user', 'llm']
    else:
        return jsonify({'ok': False, 'error': 'subject invalide'}), 400

    raw_status = str(request.args.get('status', 'all') or 'all').strip().lower()
    if raw_status in {'all', ''}:
        status = None
    elif raw_status in {'accepted', 'deferred', 'rejected'}:
        status = raw_status
    else:
        return jsonify({'ok': False, 'error': 'status invalide'}), 400

    entries = []
    for subject in subjects:
        entries.extend(memory_store.get_identities(subject, top_n=limit, status=status))

    entries.sort(key=lambda e: float(e.get('weight') or 0.0), reverse=True)
    entries = entries[:limit]
    return jsonify({'ok': True, 'items': entries, 'count': len(entries)})


@app.get('/api/admin/hermeneutics/arbiter-decisions')
def api_admin_hermeneutics_arbiter_decisions():
    raw_limit = request.args.get('limit', '200')
    try:
        limit = max(1, min(int(raw_limit), 1000))
    except ValueError:
        limit = 200

    conversation_id = str(request.args.get('conversation_id', '') or '').strip() or None
    decisions = memory_store.get_arbiter_decisions(limit=limit, conversation_id=conversation_id)
    return jsonify({'ok': True, 'items': decisions, 'count': len(decisions)})


@app.post('/api/admin/hermeneutics/identity/force-accept')
def api_admin_hermeneutics_identity_force_accept():
    data = request.get_json(force=True, silent=True) or {}
    identity_id = str(data.get('identity_id') or '').strip()
    reason = str(data.get('reason') or '').strip()
    actor = str(data.get('actor') or 'admin').strip() or 'admin'
    if not identity_id:
        return jsonify({'ok': False, 'error': 'identity_id manquant'}), 400

    ok = memory_store.set_identity_override(
        identity_id,
        'force_accept',
        reason=reason,
        actor=actor,
    )
    if not ok:
        return jsonify({'ok': False, 'error': 'identity introuvable'}), 404

    admin_logs.log_event(
        'identity_override',
        action='force_accept',
        identity_id=identity_id,
        actor=actor,
    )
    return jsonify({'ok': True, 'identity_id': identity_id, 'override_state': 'force_accept'})


@app.post('/api/admin/hermeneutics/identity/force-reject')
def api_admin_hermeneutics_identity_force_reject():
    data = request.get_json(force=True, silent=True) or {}
    identity_id = str(data.get('identity_id') or '').strip()
    reason = str(data.get('reason') or '').strip()
    actor = str(data.get('actor') or 'admin').strip() or 'admin'
    if not identity_id:
        return jsonify({'ok': False, 'error': 'identity_id manquant'}), 400

    ok = memory_store.set_identity_override(
        identity_id,
        'force_reject',
        reason=reason,
        actor=actor,
    )
    if not ok:
        return jsonify({'ok': False, 'error': 'identity introuvable'}), 404

    admin_logs.log_event(
        'identity_override',
        action='force_reject',
        identity_id=identity_id,
        actor=actor,
    )
    return jsonify({'ok': True, 'identity_id': identity_id, 'override_state': 'force_reject'})


@app.post('/api/admin/hermeneutics/identity/relabel')
def api_admin_hermeneutics_identity_relabel():
    data = request.get_json(force=True, silent=True) or {}
    identity_id = str(data.get('identity_id') or '').strip()
    if not identity_id:
        return jsonify({'ok': False, 'error': 'identity_id manquant'}), 400

    stability = data.get('stability')
    utterance_mode = data.get('utterance_mode')
    scope = data.get('scope')
    reason = str(data.get('reason') or '').strip()
    actor = str(data.get('actor') or 'admin').strip() or 'admin'

    allowed_stability = {'durable', 'episodic', 'unknown'}
    allowed_utterance_mode = {
        'self_description',
        'projection',
        'role_play',
        'irony',
        'speculation',
        'unknown',
    }
    allowed_scope = {'user', 'llm', 'situation', 'mixed', 'unknown'}

    if stability is not None and str(stability).strip() not in allowed_stability:
        return jsonify({'ok': False, 'error': 'stability invalide'}), 400
    if utterance_mode is not None and str(utterance_mode).strip() not in allowed_utterance_mode:
        return jsonify({'ok': False, 'error': 'utterance_mode invalide'}), 400
    if scope is not None and str(scope).strip() not in allowed_scope:
        return jsonify({'ok': False, 'error': 'scope invalide'}), 400
    if stability is None and utterance_mode is None and scope is None:
        return jsonify({'ok': False, 'error': 'aucun champ a relabel'}), 400

    ok = memory_store.relabel_identity(
        identity_id,
        stability=str(stability).strip() if stability is not None else None,
        utterance_mode=str(utterance_mode).strip() if utterance_mode is not None else None,
        scope=str(scope).strip() if scope is not None else None,
        reason=reason,
        actor=actor,
    )
    if not ok:
        return jsonify({'ok': False, 'error': 'identity introuvable'}), 404

    admin_logs.log_event(
        'identity_relabel',
        identity_id=identity_id,
        actor=actor,
        stability=stability,
        utterance_mode=utterance_mode,
        scope=scope,
    )
    return jsonify({'ok': True, 'identity_id': identity_id})



@app.get('/api/admin/hermeneutics/dashboard')
def api_admin_hermeneutics_dashboard():
    raw_window_days = request.args.get('window_days', '7')
    raw_log_limit = request.args.get('log_limit', '5000')

    try:
        window_days = max(1, min(int(raw_window_days), 365))
    except ValueError:
        window_days = 7

    try:
        log_limit = max(100, min(int(raw_log_limit), 10000))
    except ValueError:
        log_limit = 5000

    kpis = memory_store.get_hermeneutic_kpis(window_days=window_days)
    runtime_metrics = arbiter.get_runtime_metrics()

    parse_error_count = int(runtime_metrics.get('arbiter_parse_error_count', 0)) + int(
        runtime_metrics.get('identity_parse_error_count', 0)
    )
    parse_denominator = int(runtime_metrics.get('arbiter_call_count', 0)) + int(
        runtime_metrics.get('identity_extractor_call_count', 0)
    )
    parse_error_rate = (float(parse_error_count) / parse_denominator) if parse_denominator > 0 else 0.0

    runtime_fallback_rate = (
        float(runtime_metrics.get('arbiter_fallback_count', 0))
        / int(runtime_metrics.get('arbiter_call_count', 1) or 1)
    )

    log_entries = admin_logs.read_logs(limit=log_limit)
    stage_latencies = _compute_stage_latencies(log_entries)

    fallback_rate = max(float(kpis.get('fallback_rate', 0.0)), runtime_fallback_rate)

    alerts: List[str] = []
    if parse_error_rate > 0.05:
        alerts.append('parse_error_rate_gt_5pct')
    if fallback_rate > 0.10:
        alerts.append('fallback_rate_gt_10pct')

    counters = {
        'identity_accept_count': int(kpis.get('identity_accept_count', 0)),
        'identity_defer_count': int(kpis.get('identity_defer_count', 0)),
        'identity_reject_count': int(kpis.get('identity_reject_count', 0)),
        'identity_override_count': int(kpis.get('identity_override_count', 0)),
        'arbiter_fallback_count': int(kpis.get('arbiter_fallback_count', 0)),
        'parse_error_count': parse_error_count,
    }

    return jsonify(
        {
            'ok': True,
            'mode': config.HERMENEUTIC_MODE,
            'window_days': window_days,
            'counters': counters,
            'rates': {
                'parse_error_rate': round(parse_error_rate, 6),
                'fallback_rate': round(fallback_rate, 6),
                'runtime_fallback_rate': round(runtime_fallback_rate, 6),
            },
            'latency_ms': stage_latencies,
            'runtime_metrics': runtime_metrics,
            'alerts': alerts,
        }
    )


@app.get('/api/admin/hermeneutics/corrections-export')
def api_admin_hermeneutics_corrections_export():
    raw_window_days = request.args.get('window_days', '7')
    raw_limit = request.args.get('limit', '5000')

    try:
        window_days = max(1, min(int(raw_window_days), 365))
    except ValueError:
        window_days = 7

    try:
        limit = max(100, min(int(raw_limit), 20000))
    except ValueError:
        limit = 5000

    cutoff = datetime.now(timezone.utc).timestamp() - (window_days * 86400)
    entries = []
    for item in admin_logs.read_logs(limit=limit):
        event = str(item.get('event') or '')
        if event not in {'identity_override', 'identity_relabel'}:
            continue

        ts_raw = str(item.get('timestamp') or '').strip()
        try:
            ts_epoch = datetime.fromisoformat(ts_raw.replace('Z', '+00:00')).timestamp()
        except ValueError:
            continue
        if ts_epoch < cutoff:
            continue

        entries.append(item)

    return jsonify(
        {
            'ok': True,
            'window_days': window_days,
            'count': len(entries),
            'items': entries,
        }
    )



# ── /api/conversations* ───────────────────────────────────────────────────────

@app.get('/api/conversations')
def api_list_conversations():
    raw_limit = str(request.args.get('limit', '100') or '100').strip()
    raw_offset = str(request.args.get('offset', '0') or '0').strip()
    raw_include_deleted = str(request.args.get('include_deleted', '') or '').strip().lower()

    try:
        limit = int(raw_limit)
    except ValueError:
        limit = 100

    try:
        offset = int(raw_offset)
    except ValueError:
        offset = 0

    include_deleted = raw_include_deleted in {'1', 'true', 'yes', 'on'}

    payload = conv_store.list_conversations(
        limit=limit,
        offset=offset,
        include_deleted=include_deleted,
    )
    return jsonify({'ok': True, **payload})


@app.post('/api/conversations')
def api_create_conversation():
    data = request.get_json(silent=True) or {}
    title = str(data.get('title') or '').strip()
    requested_system = data.get('system')
    system_prompt = str(requested_system).strip() if isinstance(requested_system, str) else ''
    if not system_prompt:
        system_prompt = ''

    conversation = conv_store.new_conversation(system_prompt, title=title)
    conv_store.save_conversation(conversation)

    summary = conv_store.get_conversation_summary(conversation['id']) or {
        'id': conversation['id'],
        'title': conversation.get('title') or 'Nouvelle conversation',
        'created_at': conversation.get('created_at'),
        'updated_at': conversation.get('updated_at'),
        'message_count': 0,
        'last_message_preview': '',
        'deleted_at': None,
    }
    return jsonify({'ok': True, 'conversation_id': conversation['id'], 'conversation': summary}), 201


@app.get('/api/conversations/<conversation_id>/messages')
def api_get_conversation_messages(conversation_id: str):
    conv_id = conv_store.normalize_conversation_id(conversation_id)
    if not conv_id:
        return jsonify({'ok': False, 'error': 'conversation_id invalide'}), 400

    conversation = conv_store.read_conversation(conv_id, '')
    if not conversation:
        return jsonify({'ok': False, 'error': 'conversation introuvable'}), 404

    summary = conv_store.get_conversation_summary(conv_id, include_deleted=True)
    if summary is None:
        summary = {
            'title': conversation.get('title') or 'Nouvelle conversation',
            'created_at': conversation.get('created_at'),
            'updated_at': conversation.get('updated_at'),
            'message_count': sum(
                1
                for msg in conversation.get('messages', [])
                if str(msg.get('role') or '').strip() in {'user', 'assistant'}
            ),
            'last_message_preview': '',
            'deleted_at': None,
        }

    return jsonify(
        {
            'ok': True,
            'conversation_id': conv_id,
            'title': summary.get('title') or 'Nouvelle conversation',
            'created_at': summary.get('created_at') or conversation.get('created_at'),
            'updated_at': summary.get('updated_at') or conversation.get('updated_at'),
            'deleted_at': summary.get('deleted_at'),
            'messages': conversation.get('messages', []),
        }
    )


@app.patch('/api/conversations/<conversation_id>')
def api_patch_conversation(conversation_id: str):
    conv_id = conv_store.normalize_conversation_id(conversation_id)
    if not conv_id:
        return jsonify({'ok': False, 'error': 'conversation_id invalide'}), 400

    data = request.get_json(silent=True) or {}
    title = str(data.get('title') or '').strip()
    if not title:
        return jsonify({'ok': False, 'error': 'title requis'}), 400

    summary = conv_store.rename_conversation(conv_id, title)
    if summary is None:
        return jsonify({'ok': False, 'error': 'conversation introuvable'}), 404
    return jsonify({'ok': True, 'conversation': summary})


@app.delete('/api/conversations/<conversation_id>')
def api_delete_conversation(conversation_id: str):
    conv_id = conv_store.normalize_conversation_id(conversation_id)
    if not conv_id:
        return jsonify({'ok': False, 'error': 'conversation_id invalide'}), 400

    if not conv_store.soft_delete_conversation(conv_id):
        return jsonify({'ok': False, 'error': 'conversation introuvable'}), 404
    return jsonify({'ok': True, 'conversation_id': conv_id})


# ── Statiques ─────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return send_from_directory(app.static_folder, "index.html")

@app.get("/admin")
def admin_root():
    return send_from_directory(app.static_folder, "admin.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.WEB_PORT)
