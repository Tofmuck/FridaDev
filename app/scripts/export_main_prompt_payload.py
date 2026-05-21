#!/usr/bin/env python3
from __future__ import annotations

"""Export a redacted main-chat OpenRouter payload.

This script is an audit aid. It does not call the main OpenRouter chat endpoint,
does not print secrets, and must not be used as a production endpoint.
"""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


APP_DIR = Path(os.environ.get("FRIDA_APP_DIR") or Path(__file__).resolve().parents[1])
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


class _IdentityModule:
    @staticmethod
    def build_identity_block() -> tuple[str, list[str]]:
        return (
            "[IDENTITÉ DU MODÈLE]\n"
            "[STATIQUE]\n"
            "- Frida répond en voix féminine, sobre, dialogique et attentive.\n\n"
            "[IDENTITÉ DE L'UTILISATEUR]\n"
            "[STATIQUE]\n"
            "- Utilisateur synthétique d'audit, sans donnée réelle.",
            ["synthetic-frida", "synthetic-user"],
        )


class _Config:
    FRIDA_TIMEZONE = "Europe/Paris"


@dataclass(frozen=True)
class PostureBlock:
    name: str
    origin: str
    activation: str
    block_type: str
    weight: str
    text: str


def _count_tokens(messages: Sequence[Mapping[str, Any]], _model: str) -> int:
    total = 0
    for message in messages:
        content = message.get("content")
        if isinstance(content, list):
            content = json.dumps(content, ensure_ascii=False, sort_keys=True)
        total += max(1, len(str(content or "")) // 4)
    return total


def _redact_data_url(value: Any, *, label: str) -> Any:
    text = str(value or "")
    if not text.startswith("data:") or ";base64," not in text:
        return value
    mime = text.split(";", 1)[0].removeprefix("data:") or "application/octet-stream"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    prefix = "file " if label == "file" else ""
    return f"[redacted {prefix}data URL: mime={mime}, chars={len(text)}, sha256_12={digest}]"


def _redact_payload(value: Any) -> Any:
    if isinstance(value, list):
        return [_redact_payload(item) for item in value]
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key == "url" and isinstance(item, str) and item.startswith("data:"):
                redacted[key] = _redact_data_url(item, label="image_url")
                continue
            if key == "file_data" and isinstance(item, str) and item.startswith("data:"):
                redacted[key] = _redact_data_url(item, label="file")
                continue
            if key.lower() in {"authorization", "api_key", "openrouter_api_key"}:
                redacted[key] = "[redacted]"
                continue
            redacted[key] = _redact_payload(item)
        return redacted
    return value


def _message_section(index: int, message: Mapping[str, Any]) -> str:
    role = str(message.get("role") or "unknown")
    content = message.get("content")
    lines = [f"### Message {index:02d} — role={role}"]
    if isinstance(content, list):
        for part_index, part in enumerate(content, start=1):
            part_payload = dict(part or {})
            part_type = str(part_payload.get("type") or "unknown")
            lines.append(f"Part {part_index}: type={part_type}")
            if part_type == "text":
                lines.append("```text")
                lines.append(str(part_payload.get("text") or ""))
                lines.append("```")
            else:
                lines.append("```json")
                lines.append(json.dumps(_redact_payload(part_payload), ensure_ascii=False, indent=2, sort_keys=True))
                lines.append("```")
        return "\n".join(lines)

    lines.append("```text")
    lines.append(str(content or ""))
    lines.append("```")
    return "\n".join(lines)


def _role_table(messages: Sequence[Mapping[str, Any]]) -> list[str]:
    lines = ["| # | role | content |", "| --- | --- | --- |"]
    for index, message in enumerate(messages, start=1):
        content = message.get("content")
        if isinstance(content, list):
            part_types = ", ".join(str(part.get("type") or "?") for part in content if isinstance(part, Mapping))
            summary = f"multimodal parts: {part_types}"
        else:
            summary = f"{len(str(content or ''))} chars"
        lines.append(f"| {index} | `{message.get('role') or 'unknown'}` | {summary} |")
    return lines


def _system_final_section(messages: Sequence[Mapping[str, Any]]) -> list[str]:
    for message in messages:
        if str(message.get("role") or "") != "system":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return ["## SYSTEM FINAL", "", "```text", content, "```", ""]
    return ["## SYSTEM FINAL", "", "Aucun message system textuel trouvé.", ""]


def _render_markdown(
    payload: Mapping[str, Any],
    *,
    notes: Sequence[str],
    title: str = "Export synthétique du prompt effectif FridaDev",
    limits: Sequence[str] = (),
    metadata: Mapping[str, Any] | None = None,
) -> str:
    redacted = _redact_payload(dict(payload))
    messages = list(redacted.get("messages") or [])
    lines = [
        f"# {title}",
        "",
        "Cet artefact est généré localement, sans appel provider et sans secret.",
        "Les data URLs multimodales sont expurgées.",
        "",
        "## Métadonnées générales",
        "",
    ]
    for key, value in dict(metadata or {}).items():
        lines.append(f"- {key}: `{value}`")
    if metadata:
        lines.append("")
    lines.extend(
        [
            "## Paramètres provider",
            "",
        f"- model: `{redacted.get('model')}`",
        f"- message_count: `{len(messages)}`",
        f"- temperature: `{redacted.get('temperature')}`",
        f"- top_p: `{redacted.get('top_p')}`",
        f"- max_tokens: `{redacted.get('max_tokens')}`",
        f"- stream: `{bool(redacted.get('stream'))}`",
        "",
        ]
    )
    lines.extend(["## Table des rôles", "", *_role_table(messages), ""])
    lines.extend(_system_final_section(messages))
    lines.extend(["## Notes", ""])
    lines.extend(f"- {note}" for note in notes)
    if limits:
        lines.extend(["", "## Limites de reconstruction", ""])
        lines.extend(f"- {limit}" for limit in limits)
    lines.extend(["", "## Messages", ""])
    for index, message in enumerate(messages, start=1):
        lines.append(_message_section(index, message))
        lines.append("")
    lines.extend(
        [
            "## JSON redacted",
            "",
            "```json",
            json.dumps(redacted, ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _render_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(_redact_payload(dict(payload)), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


class _NoopLogger:
    @staticmethod
    def info(*_args: Any, **_kwargs: Any) -> None:
        return None

    @staticmethod
    def warning(*_args: Any, **_kwargs: Any) -> None:
        return None

    @staticmethod
    def error(*_args: Any, **_kwargs: Any) -> None:
        return None


def _latest_user_turn_prefix(conversation: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], int]:
    messages = [dict(message or {}) for message in list(conversation.get("messages") or [])]
    latest_user_index = -1
    for index, message in enumerate(messages):
        if str(message.get("role") or "").strip().lower() == "user":
            latest_user_index = index
    if latest_user_index < 0:
        raise RuntimeError("conversation_has_no_user_turn")
    prefix = dict(conversation)
    prefix["messages"] = messages[: latest_user_index + 1]
    return prefix, messages[latest_user_index], latest_user_index


def _runtime_main_settings() -> dict[str, Any]:
    from admin import runtime_settings

    view = runtime_settings.get_main_model_settings()
    payload = view.payload
    return {
        "model": str(payload["model"]["value"]),
        "temperature": float(payload["temperature"]["value"]),
        "top_p": float(payload["top_p"]["value"]),
        "max_tokens": int(payload["response_max_tokens"]["value"]),
    }


def _load_conversation_by_id(conversation_id: str) -> tuple[dict[str, Any], str, str]:
    from core import chat_prompt_context
    from core import conv_store
    from core import prompt_loader

    system_prompt, hermeneutical_prompt = chat_prompt_context.resolve_backend_prompts(prompt_loader)
    conversation = conv_store.read_conversation(conversation_id, system_prompt)
    if not conversation:
        raise RuntimeError(f"conversation_not_found:{conversation_id}")
    return conversation, system_prompt, hermeneutical_prompt


def _latest_conversation_id(*, search_limit: int) -> str:
    from core import conv_store

    result = conv_store.list_conversations(limit=max(1, min(int(search_limit or 20), 100)))
    for item in list(result.get("items") or []):
        conversation_id = str((item or {}).get("id") or "").strip()
        if conversation_id:
            return conversation_id
    raise RuntimeError("no_conversation_available")


def _prepare_memory_for_real_export(
    *,
    conversation: Mapping[str, Any],
    user_msg: str,
    now_iso: str,
    include_current_memory: bool,
    limits: list[str],
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    from core import chat_memory_flow
    import config

    current_mode = chat_memory_flow.resolve_hermeneutic_mode(config)
    if not include_current_memory:
        limits.append(
            "Mémoire: retrieval/arbitrage non rejoués par défaut pour éviter tout appel embedding/provider et toute écriture d'audit; le prompt réel historique peut avoir contenu des souvenirs."
        )
        return current_mode, [], []

    from core.hermeneutic_node.inputs import memory_retrieved_input
    from memory import memory_pre_arbiter_basket
    from memory import memory_store

    top_k_requested = chat_memory_flow._resolve_retrieval_top_k_requested(  # type: ignore[attr-defined]
        memory_store_module=memory_store,
        config_module=config,
    )
    retrieval_outcome = chat_memory_flow._retrieve_raw_traces(  # type: ignore[attr-defined]
        memory_store_module=memory_store,
        user_msg=user_msg,
        top_k_requested=top_k_requested,
    )
    raw_traces = retrieval_outcome.traces
    if not raw_traces:
        context_hints = memory_store.get_recent_context_hints(
            max_items=chat_memory_flow._governed_config_value(config, "CONTEXT_HINTS_MAX_ITEMS"),  # type: ignore[attr-defined]
            max_age_days=chat_memory_flow._governed_config_value(config, "CONTEXT_HINTS_MAX_AGE_DAYS"),  # type: ignore[attr-defined]
            min_confidence=chat_memory_flow._governed_config_value(config, "CONTEXT_HINTS_MIN_CONFIDENCE"),  # type: ignore[attr-defined]
        )
        return current_mode, [], list(context_hints or [])

    retrieved_candidates = chat_memory_flow._enrich_retrieved_candidates(  # type: ignore[attr-defined]
        memory_store_module=memory_store,
        traces=raw_traces,
    )
    memory_retrieved = memory_retrieved_input.build_memory_retrieved_input(
        retrieval_query=user_msg,
        top_k_requested=retrieval_outcome.top_k_requested,
        traces=retrieved_candidates,
        status=retrieval_outcome.status,
        reason_code=retrieval_outcome.reason_code,
        error_code=retrieval_outcome.error_code,
        error_class=retrieval_outcome.error_class,
    )
    pre_arbiter_basket = memory_pre_arbiter_basket.build_pre_arbiter_basket(
        memory_retrieved=memory_retrieved,
        retrieved_candidates=retrieved_candidates,
        internal_traces=raw_traces,
    )
    memory_traces = memory_pre_arbiter_basket.select_prompt_candidates(pre_arbiter_basket)
    if current_mode == "enforced_all":
        limits.append(
            "Mémoire: le mode enforced_all dépend de l'arbitre LLM; l'export utilise le panier pré-arbitre courant et peut différer du tour réel."
        )
    else:
        limits.append(
            "Mémoire: traces reconstruites depuis l'état mémoire courant; cela peut différer du tour historique si la mémoire ou les embeddings ont changé."
        )
    context_hints = memory_store.get_recent_context_hints(
        max_items=chat_memory_flow._governed_config_value(config, "CONTEXT_HINTS_MAX_ITEMS"),  # type: ignore[attr-defined]
        max_age_days=chat_memory_flow._governed_config_value(config, "CONTEXT_HINTS_MAX_AGE_DAYS"),  # type: ignore[attr-defined]
        min_confidence=chat_memory_flow._governed_config_value(config, "CONTEXT_HINTS_MIN_CONFIDENCE"),  # type: ignore[attr-defined]
    )
    return current_mode, memory_traces, list(context_hints or [])


def build_real_conversation_payload(
    *,
    conversation_id: str,
    stream: bool,
    include_current_memory: bool,
) -> tuple[dict[str, Any], list[str], list[str], dict[str, Any]]:
    from core import active_document_prompt_lane
    from core import chat_prompt_context
    from core import chat_service
    from core import conv_store
    from core import llm_client
    from core import token_utils
    from identity import identity as identity_module
    import config

    conversation, system_prompt, hermeneutical_prompt = _load_conversation_by_id(conversation_id)
    prefix_conversation, target_user, target_index = _latest_user_turn_prefix(conversation)
    user_msg = str(target_user.get("content") or "")
    now_iso = str(target_user.get("timestamp") or conversation.get("updated_at") or "")
    settings = _runtime_main_settings()
    runtime_main_model = settings["model"]

    augmented_system, identity_ids = chat_prompt_context.build_augmented_system(
        system_prompt=system_prompt,
        hermeneutical_prompt=hermeneutical_prompt,
        config_module=config,
        identity_module=identity_module,
        now_iso=now_iso,
    )
    limits = [
        "Reconstruction depuis l'état actuel de la DB: les prompts sources, settings, identité, résumé actif, documents actifs et sélections workspace peuvent avoir changé depuis le tour historique.",
        "Le prompt historique exact n'est pas stocké en clair dans les logs; cet export reconstruit le chemin actuel jusqu'au payload sans appeler le main model.",
        "Stimmung fraîche, validation_agent fraîche et jugement herméneutique final du tour historique ne sont pas rejoués sans appel provider; le bloc [JUGEMENT HERMENEUTIQUE] historique n'est donc pas reconstruit ici.",
        "Web: le contexte web runtime du tour historique n'est pas stocké en clair; il n'est présent que s'il existe déjà dans les messages persistés, ce qui n'est normalement pas le cas.",
    ]

    chat_prompt_context.apply_augmented_system(prefix_conversation, augmented_system)
    current_mode, memory_traces, context_hints = _prepare_memory_for_real_export(
        conversation=prefix_conversation,
        user_msg=user_msg,
        now_iso=now_iso,
        include_current_memory=include_current_memory,
        limits=limits,
    )
    try:
        time_payload = chat_service._resolve_time_input(now_iso=now_iso, config_module=config)  # type: ignore[attr-defined]
        summary_payload = chat_service._resolve_summary_input(  # type: ignore[attr-defined]
            conversation_id=prefix_conversation.get("id"),
            conv_store_module=conv_store,
        )
        recent_context_payload = chat_service._resolve_recent_context_input(  # type: ignore[attr-defined]
            conversation=prefix_conversation,
            summary_payload=summary_payload,
        )
        recent_window_payload = chat_service._resolve_recent_window_input(  # type: ignore[attr-defined]
            recent_context_payload=recent_context_payload,
        )
        user_turn_payload, user_turn_signals_payload = chat_service._resolve_user_turn_runtime_inputs(  # type: ignore[attr-defined]
            user_msg=user_msg,
            recent_window_payload=recent_window_payload,
            time_payload=time_payload,
        )
        direct_identity_guard_block = chat_prompt_context.build_direct_identity_revelation_guard_block(
            user_msg=user_msg,
            user_turn_input=user_turn_payload,
            user_turn_signals=user_turn_signals_payload,
        )
        augmented_system = chat_prompt_context.inject_direct_identity_revelation_guard_block(
            augmented_system,
            direct_identity_guard_block,
        )
    except Exception as exc:
        limits.append(
            f"Garde de révélation identitaire directe non reconstruite: {exc.__class__.__name__}."
        )
    plain_text_guard_block = chat_prompt_context.build_plain_text_guard_block(user_msg=user_msg)
    augmented_system = chat_prompt_context.inject_plain_text_guard_block(augmented_system, plain_text_guard_block)
    input_mode = str((target_user.get("meta") or {}).get("input_mode") or "")
    voice_guard_block = chat_prompt_context.build_voice_transcription_guard_block(input_mode=input_mode)
    augmented_system = chat_prompt_context.inject_voice_transcription_guard_block(augmented_system, voice_guard_block)
    chat_prompt_context.apply_augmented_system(prefix_conversation, augmented_system)

    active_read = chat_service._active_documents_for_prompt(  # type: ignore[attr-defined]
        conversation=prefix_conversation,
        logger=_NoopLogger(),
    )
    workspace_read = chat_service._workspace_files_for_prompt(  # type: ignore[attr-defined]
        conversation=prefix_conversation,
        logger=_NoopLogger(),
    )
    document_read = chat_service._merge_document_prompt_reads(active_read, workspace_read)  # type: ignore[attr-defined]
    prompt_messages = conv_store.build_prompt_messages(
        prefix_conversation,
        runtime_main_model,
        now=now_iso,
        memory_traces=memory_traces or None,
        context_hints=context_hints or None,
    )
    lane = active_document_prompt_lane.inject_active_document_prompt_lane(
        prompt_messages,
        document_read.documents,
        model=runtime_main_model,
        count_tokens_func=chat_service._prompt_token_counter(token_utils),  # type: ignore[attr-defined]
        max_tokens=chat_service._active_document_prompt_max_tokens(config),  # type: ignore[attr-defined]
        read_status=document_read.status,
        read_reason_code=document_read.reason_code,
    )
    payload = llm_client.build_payload(
        prompt_messages,
        settings["temperature"],
        settings["top_p"],
        settings["max_tokens"],
        stream=stream,
    )
    notes = [
        "Conversation réelle chargée depuis le store runtime.",
        "Préfixe retenu: messages jusqu'au dernier message utilisateur; les réponses assistant postérieures sont exclues.",
        f"Mode mémoire runtime détecté: {current_mode}.",
        f"Identités injectées: {len(identity_ids)}.",
        f"Documents/fichiers prompt-time: injected={lane.injected_count}, excluded={lane.not_injected_count}.",
        "Aucun appel au modèle principal OpenRouter n'est effectué par cet export.",
    ]
    metadata = {
        "conversation_id": conversation_id,
        "target_user_message_index": target_index,
        "target_user_timestamp": now_iso,
        "reconstruction_kind": "real_conversation_best_effort",
        "include_current_memory": include_current_memory,
    }
    return payload, notes, limits, metadata


def _delta_label(ts_msg: str, ts_now: str) -> str:
    from core.hermeneutic_node.inputs import time_input

    return time_input.render_delta_label(ts_msg, ts_now, timezone_name=_Config.FRIDA_TIMEZONE)


def _silence_label(ts_before: str, ts_after: str) -> str:
    from core.hermeneutic_node.inputs import time_input

    return time_input.render_silence_label(ts_before, ts_after)


def _dialogue_message(role: str, content: str, timestamp: str, *, now_iso: str) -> dict[str, str]:
    label = _delta_label(timestamp, now_iso)
    prefix = f"[{label}] " if label else ""
    return {"role": role, "content": f"{prefix}{content}"}


def build_synthetic_payload(*, model: str, now_iso: str, stream: bool) -> tuple[dict[str, Any], list[str]]:
    from core import active_document_prompt_lane
    from core import chat_prompt_context
    from core import prompt_loader
    from core.web_read_state import READ_STATE_PAGE_PARTIALLY_READ

    system_prompt, hermeneutical_prompt = chat_prompt_context.resolve_backend_prompts(prompt_loader)
    augmented_system, _identity_ids = chat_prompt_context.build_augmented_system(
        system_prompt=system_prompt,
        hermeneutical_prompt=hermeneutical_prompt,
        config_module=_Config,
        identity_module=_IdentityModule,
        now_iso=now_iso,
    )
    augmented_system = chat_prompt_context.inject_hermeneutic_judgment_block(
        augmented_system,
        chat_prompt_context.build_hermeneutic_judgment_block(
            validated_output={
                "final_judgment_posture": "answer",
                "final_output_regime": "simple",
                "pipeline_directives_final": [
                    "répondre depuis les traces effectivement visibles",
                    "ne pas prétendre avoir lu une pièce non injectée",
                ],
            }
        ),
    )
    augmented_system = chat_prompt_context.inject_voice_transcription_guard_block(
        augmented_system,
        chat_prompt_context.build_voice_transcription_guard_block(input_mode="voice"),
    )
    augmented_system = chat_prompt_context.inject_direct_identity_revelation_guard_block(
        augmented_system,
        chat_prompt_context.build_direct_identity_revelation_guard_block(
            user_msg="Je suis Camille. Peux-tu analyser les pièces ?",
            user_turn_input={"geste_dialogique_dominant": "exposition"},
            user_turn_signals={},
        ),
    )
    web_input = {
        "read_state": READ_STATE_PAGE_PARTIALLY_READ,
        "explicit_url": "https://example.invalid/source",
    }
    augmented_system = chat_prompt_context.inject_web_reading_guard_block(
        augmented_system,
        chat_prompt_context.build_web_reading_guard_block(web_input=web_input),
    )
    augmented_system = chat_prompt_context.inject_plain_text_guard_block(
        augmented_system,
        chat_prompt_context.build_plain_text_guard_block(
            user_msg="Je suis Camille. Peux-tu analyser les pièces ?",
        ),
    )

    messages: list[dict[str, Any]] = [{"role": "system", "content": augmented_system}]
    messages.append(
        {
            "role": "system",
            "content": (
                "[Résumé de la période du 2026-05-20]\n"
                "Résumé synthétique non sensible: une discussion précédente a cadré un dossier de travail."
            ),
        }
    )
    messages.append(
        {
            "role": "system",
            "content": (
                "[Indices contextuels recents]\n"
                "- [jeudi 21 mai 2026 à 13h45 Europe/Paris — il y a 15 minutes] "
                "Situation: l'utilisateur prépare une relecture de traces hétérogènes (confidence: 0.82)"
            ),
        }
    )
    messages.append(
        {
            "role": "system",
            "content": (
                "[Contexte du souvenir S1 — résumé du 2026-05-20]\n"
                "Résumé parent synthétique non sensible d'une période antérieure."
            ),
        }
    )
    messages.append(
        {
            "role": "system",
            "content": (
                "[Mémoire — souvenirs pertinents]\n"
                "[mercredi 20 mai 2026 à 18h00 Europe/Paris — hier] "
                "Utilisateur [contexte S1] : Souvenir synthétique non sensible."
            ),
        }
    )
    messages.append(
        _dialogue_message(
            "user",
            "Question précédente synthétique.",
            "2026-05-21T11:40:00Z",
            now_iso=now_iso,
        )
    )
    silence = _silence_label("2026-05-21T11:40:00Z", "2026-05-21T11:45:00Z")
    if silence:
        messages.append({"role": "system", "content": silence})
    messages.append(
        _dialogue_message(
            "assistant",
            "Réponse précédente synthétique.",
            "2026-05-21T11:45:00Z",
            now_iso=now_iso,
        )
    )
    final_user = _dialogue_message(
        "user",
        "Je suis Camille. Peux-tu analyser les pièces ?",
        "2026-05-21T12:00:00Z",
        now_iso=now_iso,
    )
    final_user["content"] = (
        "[RECHERCHE WEB — synthétique]\n"
        "J'ai effectué une recherche pour : exemple non sensible.\n"
        "Source 1: Example Domain — https://example.invalid/source\n"
        "Contenu utilisé: extrait synthétique tronqué.\n"
        "[FIN DES RÉSULTATS WEB]\n\n"
        "Question : "
        + final_user["content"]
    )
    messages.append(final_user)

    documents = [
        {
            "document_id": "active-text-synthetic",
            "filename": "note-active.md",
            "media_type": "text/markdown",
            "source_extension": ".md",
            "byte_size": 96,
            "text_chars": 72,
            "token_estimate": 18,
            "text_sha256_12": "text12345678",
            "text_content": "Contenu documentaire synthétique non sensible, injecté en entier.",
        },
        {
            "source": "workspace_file_selection",
            "document_id": "workspace-text-synthetic",
            "workspace_file_id": "workspace-text-synthetic",
            "workspace_folder_id": "workspace-folder-synthetic",
            "filename": "atelier-note.txt",
            "media_type": "text/plain",
            "source_extension": ".txt",
            "byte_size": 64,
            "text_chars": 52,
            "token_estimate": 13,
            "text_sha256_12": "worktxt12345",
            "text_content": "Texte workspace synthétique sélectionné explicitement.",
        },
        {
            "document_id": "active-image-synthetic",
            "filename": "capture.png",
            "media_type": "image/png",
            "source_extension": ".png",
            "byte_size": len(b"synthetic image bytes"),
            "media_kind": "image",
            "content_sha256_12": "img123456789",
            "image_width": 640,
            "image_height": 360,
            "image_content": b"synthetic image bytes",
        },
        {
            "source": "workspace_file_selection",
            "document_id": "workspace-pdf-synthetic",
            "workspace_file_id": "workspace-pdf-synthetic",
            "workspace_folder_id": "workspace-folder-synthetic",
            "filename": "scan.pdf",
            "media_type": "application/pdf",
            "source_extension": ".pdf",
            "byte_size": len(b"%PDF-1.4 synthetic pdf bytes"),
            "media_kind": "file",
            "content_sha256_12": "pdf123456789",
            "file_content": b"%PDF-1.4 synthetic pdf bytes",
        },
    ]
    lane = active_document_prompt_lane.inject_active_document_prompt_lane(
        messages,
        documents,
        model=model,
        count_tokens_func=_count_tokens,
        max_tokens=0,
        read_status=active_document_prompt_lane.READ_STATUS_OK,
    )
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "top_p": 1.0,
        "max_tokens": 8192,
        "stop": ["<|endoftext|>", "<|return|>", "<|call|>"],
        "metadata": {
            "frida_caller": "main_chat",
            "frida_slot": "main_model",
            "audit_mode": "synthetic",
        },
        "trace": {
            "trace_name": "FridaDev",
            "generation_name": "FridaDev / Main Chat",
        },
    }
    if stream:
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}
    notes = [
        "Le système augmenté contient main_system, main_hermeneutical, NOW/TIMEZONE, identité, jugement herméneutique et guards runtime.",
        "Le dernier message user contient un contexte web synthétique préfixé.",
        "La lane documents actifs est insérée avant le premier message de dialogue.",
        f"Décisions documentaires synthétiques: injected={lane.injected_count}, excluded={lane.not_injected_count}.",
        "Les parties image/PDF existent dans le payload en mémoire, puis sont expurgées avant écriture.",
    ]
    return payload, notes


def _posture_time_reference_block(*, now_iso: str) -> str:
    from core.hermeneutic_node.inputs import time_input

    canonical_time_input = time_input.build_time_input(
        now_utc_iso=now_iso,
        timezone_name=_Config.FRIDA_TIMEZONE,
    )
    return time_input.build_time_reference_block(canonical_time_input)


def _posture_document_contract_block(*, model: str) -> str:
    from core import active_document_prompt_lane

    documents = [
        {
            "document_id": "posture-text-synthetic",
            "filename": "document-synthetique.txt",
            "media_type": "text/plain",
            "source_extension": ".txt",
            "byte_size": 64,
            "text_chars": 52,
            "token_estimate": 13,
            "text_sha256_12": "posturetxt12",
            "text_content": "Texte synthétique content-free pour déclencher le contrat documentaire.",
        },
        {
            "source": "workspace_file_selection",
            "document_id": "posture-image-synthetic",
            "workspace_file_id": "posture-image-synthetic",
            "workspace_folder_id": "posture-folder-synthetic",
            "filename": "capture-synthetique.png",
            "media_type": "image/png",
            "source_extension": ".png",
            "byte_size": len(b"synthetic posture image bytes"),
            "media_kind": "image",
            "content_sha256_12": "postureimg12",
            "image_width": 320,
            "image_height": 180,
            "image_content": b"synthetic posture image bytes",
        },
        {
            "source": "workspace_file_selection",
            "document_id": "posture-pdf-synthetic",
            "workspace_file_id": "posture-pdf-synthetic",
            "workspace_folder_id": "posture-folder-synthetic",
            "filename": "scan-synthetique.pdf",
            "media_type": "application/pdf",
            "source_extension": ".pdf",
            "byte_size": len(b"%PDF-1.4 synthetic posture pdf bytes"),
            "media_kind": "file",
            "content_sha256_12": "posturepdf12",
            "file_content": b"%PDF-1.4 synthetic posture pdf bytes",
        },
        {
            "source": "workspace_file_selection",
            "document_id": "posture-excluded-synthetic",
            "workspace_file_id": "posture-excluded-synthetic",
            "workspace_folder_id": "posture-folder-synthetic",
            "filename": "non-injecte.pdf",
            "media_type": "application/pdf",
            "source_extension": ".pdf",
            "byte_size": 0,
            "media_kind": "file",
            "injectable": False,
            "reason_code": "workspace_file_disk_missing",
        },
    ]
    lane = active_document_prompt_lane.build_active_document_prompt_lane(
        documents,
        model=model,
        base_messages=[],
        count_tokens_func=_count_tokens,
        max_tokens=0,
        read_status=active_document_prompt_lane.READ_STATUS_OK,
    )
    contract = lane.contract_message or {}
    return str(contract.get("content") or "")


def build_posture_pack(*, model: str, now_iso: str) -> tuple[list[PostureBlock], dict[str, Any], list[str]]:
    from core import chat_prompt_context
    from core import prompt_loader
    from core.web_read_state import READ_STATE_PAGE_PARTIALLY_READ

    system_prompt, hermeneutical_prompt = chat_prompt_context.resolve_backend_prompts(prompt_loader)
    identity_block, identity_ids = _IdentityModule.build_identity_block()
    hermeneutic_judgment_block = chat_prompt_context.build_hermeneutic_judgment_block(
        validated_output={
            "final_judgment_posture": "answer",
            "final_output_regime": "simple",
            "pipeline_directives_final": [
                "répondre depuis les traces effectivement visibles",
                "ne pas prétendre avoir lu une pièce non injectée",
            ],
        }
    )
    direct_identity_guard_block = chat_prompt_context.build_direct_identity_revelation_guard_block(
        user_msg="Je suis Camille.",
        user_turn_input={"geste_dialogique_dominant": "exposition"},
        user_turn_signals={},
    )
    voice_guard_block = chat_prompt_context.build_voice_transcription_guard_block(input_mode="voice")
    web_guard_block = chat_prompt_context.build_web_reading_guard_block(
        web_input={
            "read_state": READ_STATE_PAGE_PARTIALLY_READ,
            "explicit_url": "https://example.invalid/source",
        }
    )
    plain_text_guard_block = chat_prompt_context.build_plain_text_guard_block(
        user_msg="Explique-moi simplement ce que ces traces impliquent."
    )
    blocks = [
        PostureBlock(
            name="Cadre de réponse général",
            origin="app/prompts/main_system.txt",
            activation="toujours actif",
            block_type="voix, style, forme, vérité",
            weight="fort",
            text=system_prompt,
        ),
        PostureBlock(
            name="Contrat herméneutique augmenté",
            origin="app/prompts/main_hermeneutical.txt",
            activation="toujours actif",
            block_type="source-priority, vérité, trace, temporalité, identity",
            weight="fort",
            text=hermeneutical_prompt,
        ),
        PostureBlock(
            name="Référence temporelle du tour",
            origin="core.hermeneutic_node.inputs.time_input.build_time_reference_block",
            activation="toujours actif, avec NOW runtime",
            block_type="temporalité, guard",
            weight="fort",
            text=_posture_time_reference_block(now_iso=now_iso),
        ),
        PostureBlock(
            name="Identité injectée",
            origin="identity.build_identity_block via chat_prompt_context.build_augmented_system",
            activation="toujours actif si identité disponible",
            block_type="identity, voix, relation",
            weight="fort",
            text=identity_block,
        ),
        PostureBlock(
            name="Jugement herméneutique final",
            origin="chat_prompt_context.build_hermeneutic_judgment_block",
            activation="conditionnel: validation herméneutique avec posture et directives finales",
            block_type="jugement herméneutique, guard, forme",
            weight="fort",
            text=hermeneutic_judgment_block,
        ),
        PostureBlock(
            name="Contrat texte brut",
            origin="assistant_output_contract.build_plain_text_guard_block",
            activation="toujours injecté pour le tour, modulé par la demande utilisateur",
            block_type="style, forme",
            weight="fort",
            text=plain_text_guard_block,
        ),
        PostureBlock(
            name="Garde de révélation identitaire",
            origin="chat_prompt_context.build_direct_identity_revelation_guard_block",
            activation="conditionnel: révélation identitaire explicite et non ambiguë",
            block_type="identity, guard",
            weight="moyen",
            text=direct_identity_guard_block,
        ),
        PostureBlock(
            name="Garde de lecture vocale",
            origin="chat_prompt_context.build_voice_transcription_guard_block",
            activation="conditionnel: tour courant issu d'une transcription vocale",
            block_type="style, vérité, guard",
            weight="moyen",
            text=voice_guard_block,
        ),
        PostureBlock(
            name="Garde de lecture web",
            origin="chat_prompt_context.build_web_reading_guard_block",
            activation="conditionnel: contexte web avec read_state",
            block_type="web, vérité, guard",
            weight="moyen",
            text=web_guard_block,
        ),
        PostureBlock(
            name="Contrat documents actifs et fichiers sélectionnés",
            origin="active_document_prompt_lane.build_active_document_prompt_lane",
            activation="conditionnel: documents actifs ou fichiers workspace sélectionnés/exclus",
            block_type="document, image, source-priority, vérité, guard",
            weight="fort",
            text=_posture_document_contract_block(model=model),
        ),
    ]
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": model,
        "source": "prompt sources + générateurs runtime synthétiques content-free",
        "now_example": now_iso,
        "identity_ids_example_count": len(identity_ids),
    }
    limits = [
        "Ce rapport isole les blocs normatifs/posturaux; il exclut volontairement historique, documents, web et contenu utilisateur long.",
        "Les blocs conditionnels sont rendus avec des exemples synthétiques non privés pour montrer leur texte exact quand ils sont actifs.",
        "Le jugement herméneutique d'un vrai tour peut varier selon validated_output; le bloc affiché ici montre la forme exacte injectée.",
        "L'identité affichée est synthétique: un vrai tour peut contenir une identité utilisateur ou modèle plus précise.",
    ]
    return blocks, metadata, limits


def _render_posture_pack(blocks: Sequence[PostureBlock], *, metadata: Mapping[str, Any], limits: Sequence[str]) -> str:
    lines = [
        "# Posture pack du modèle principal FridaDev",
        "",
        "Cet export isole ce qui dit au modèle principal comment répondre: voix, forme, hiérarchie, prudence, vérité, temporalité et guards.",
        "Il n'est pas un export complet du payload et ne contient pas de conversation privée.",
        "",
        "## Métadonnées",
        "",
    ]
    for key, value in dict(metadata).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Limites",
            "",
            *[f"- {limit}" for limit in limits],
            "",
            "## Table des blocs posturaux",
            "",
            "| Bloc | Origine | Activation | Type | Poids estimé |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for block in blocks:
        lines.append(
            f"| {block.name} | `{block.origin}` | {block.activation} | {block.block_type} | {block.weight} |"
        )

    lines.extend(["", "## Texte exact des blocs posturaux", ""])
    for index, block in enumerate(blocks, start=1):
        lines.extend(
            [
                f"### {index}. {block.name}",
                "",
                f"- origine: `{block.origin}`",
                f"- activation: {block.activation}",
                f"- type: {block.block_type}",
                f"- poids estimé: {block.weight}",
                "",
                "```text",
                block.text,
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "## Ce qui n'est pas postural",
            "",
            "- L'historique conversationnel complet: il apporte du contexte, mais n'est pas en soi un contrat de posture.",
            "- Le contenu documentaire, web, image ou PDF: il fournit des traces et des faits possibles, pas une autorité système.",
            "- Les réponses assistant passées: elles peuvent orienter la continuité locale, mais ne remplacent pas le contrat courant.",
            "- Les souvenirs factuels et résumés: ils éclairent la demande, mais leur poids est cadré par le contrat herméneutique.",
            "- Les fichiers workspace non cochés, les documents exclus et les bytes multimodaux: ils ne sont pas visibles au modèle.",
            "- Le JSON complet du payload, les data URLs, les secrets, les logs et les artefacts privés.",
            "",
            "## Lecture courte",
            "",
            "- Le plus structurant est le couple `main_system.txt` + `main_hermeneutical.txt`: voix, forme, hiérarchie des sources, prudence et ontologie de la trace.",
            "- Le bloc temps et le bloc identité ajoutent une contrainte forte de situation: Frida reçoit un NOW, une timezone et une identité active; elle ne les invente pas.",
            "- Le jugement herméneutique, quand il est présent, est le cadrage aval le plus immédiat: il ne rédige pas la réponse, mais fixe posture, régime et directives finales.",
            "- Les guards texte brut, web, voix, identité directe et documents actifs sont conditionnels ou locaux, mais ils peuvent fortement contraindre la formulation du tour.",
            "- Les redondances utiles portent surtout sur la prudence: ne pas inventer, ne pas prétendre avoir lu ce qui n'est pas injecté, distinguer trace, preuve, interprétation et autorité.",
            "- Le pack reste dense: si une future simplification est décidée, le premier candidat serait la consolidation des règles de forme entre `main_system.txt` et `[CONTRAT TEXTE BRUT]`.",
            "",
        ]
    )
    return "\n".join(lines)


def _format_from_output(path: Path, explicit_format: str) -> str:
    if explicit_format != "auto":
        return explicit_format
    return "json" if path.suffix.lower() == ".json" else "md"


def _write_output(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export a redacted main-chat prompt payload for FridaDev audit.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    synthetic = subparsers.add_parser("synthetic", help="build a synthetic non-sensitive main-chat payload")
    synthetic.add_argument("--output", required=True, help="output .md or .json path")
    synthetic.add_argument("--format", choices=("auto", "md", "json"), default="auto")
    synthetic.add_argument("--model", default="openai/gpt-5.1")
    synthetic.add_argument("--now", default="2026-05-21T12:00:00Z")
    synthetic.add_argument("--stream", action="store_true")

    conversation = subparsers.add_parser(
        "conversation",
        help="reconstruct a redacted payload for the latest user turn of one real conversation",
    )
    conversation.add_argument("--conversation-id", required=True)
    conversation.add_argument("--output", required=True, help="output .md or .json path")
    conversation.add_argument("--format", choices=("auto", "md", "json"), default="auto")
    conversation.add_argument("--stream", action="store_true")
    conversation.add_argument(
        "--include-current-memory",
        action="store_true",
        help="recompute current memory/context hints; may call the configured embedding provider",
    )

    latest = subparsers.add_parser(
        "latest",
        help="reconstruct a redacted payload for the latest non-deleted conversation",
    )
    latest.add_argument("--output", required=True, help="output .md or .json path")
    latest.add_argument("--format", choices=("auto", "md", "json"), default="auto")
    latest.add_argument("--stream", action="store_true")
    latest.add_argument("--search-limit", type=int, default=20)
    latest.add_argument(
        "--include-current-memory",
        action="store_true",
        help="recompute current memory/context hints; may call the configured embedding provider",
    )

    posture = subparsers.add_parser(
        "posture",
        help="export only the normative posture blocks that constrain the main model",
    )
    posture.add_argument("--output", required=True, help="output Markdown path")
    posture.add_argument("--model", default="openai/gpt-5.1")
    posture.add_argument("--now", default="2026-05-21T12:00:00Z")

    args = parser.parse_args(argv)
    output_path = Path(args.output)
    title = "Export synthétique du prompt effectif FridaDev"
    limits: list[str] = []
    metadata: dict[str, Any] = {}
    if args.command == "synthetic":
        payload, notes = build_synthetic_payload(
            model=str(args.model),
            now_iso=str(args.now),
            stream=bool(args.stream),
        )
    elif args.command == "posture":
        blocks, metadata, limits = build_posture_pack(
            model=str(args.model),
            now_iso=str(args.now),
        )
        rendered = _render_posture_pack(blocks, metadata=metadata, limits=limits)
        _write_output(output_path, rendered)
        print(f"wrote {output_path}")
        return 0
    else:
        try:
            conversation_id = (
                str(args.conversation_id)
                if args.command == "conversation"
                else _latest_conversation_id(search_limit=int(args.search_limit))
            )
            payload, notes, limits, metadata = build_real_conversation_payload(
                conversation_id=conversation_id,
                stream=bool(args.stream),
                include_current_memory=bool(args.include_current_memory),
            )
        except ModuleNotFoundError as exc:
            if getattr(exc, "name", "") == "psycopg":
                parser.error(
                    "real export requires runtime dependencies; run inside the app container "
                    "or set FRIDA_APP_DIR=/app with the container Python"
                )
            raise
        title = "Export local d'un prompt effectif réel FridaDev"
    output_format = _format_from_output(output_path, str(args.format))
    if output_format == "json":
        rendered = _render_json(payload)
    else:
        rendered = _render_markdown(
            payload,
            notes=notes,
            title=title,
            limits=limits,
            metadata=metadata,
        )
    _write_output(output_path, rendered)
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
