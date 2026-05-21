#!/usr/bin/env python3
from __future__ import annotations

"""Export a redacted, synthetic main-chat OpenRouter payload.

This script is an audit aid. It does not call OpenRouter, does not read secrets,
does not query the runtime DB, and must not be used as a production endpoint.
"""

import argparse
import base64
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


APP_DIR = Path(__file__).resolve().parents[1]
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
    encoded = text.split(";base64,", 1)[1]
    try:
        byte_count = len(base64.b64decode(encoded.encode("ascii"), validate=False))
    except Exception:
        byte_count = 0
    return f"[{label} data URL redacted: mime={mime} bytes={byte_count}]"


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


def _render_markdown(payload: Mapping[str, Any], *, notes: Sequence[str]) -> str:
    redacted = _redact_payload(dict(payload))
    messages = list(redacted.get("messages") or [])
    lines = [
        "# Export synthétique du prompt effectif FridaDev",
        "",
        "Cet artefact est généré localement, sans appel provider, sans secret et sans conversation réelle.",
        "Les data URLs multimodales sont expurgées.",
        "",
        "## Résumé payload",
        "",
        f"- model: `{redacted.get('model')}`",
        f"- message_count: `{len(messages)}`",
        f"- temperature: `{redacted.get('temperature')}`",
        f"- top_p: `{redacted.get('top_p')}`",
        f"- max_tokens: `{redacted.get('max_tokens')}`",
        f"- stream: `{bool(redacted.get('stream'))}`",
        "",
        "## Notes",
        "",
    ]
    lines.extend(f"- {note}" for note in notes)
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


def _format_from_output(path: Path, explicit_format: str) -> str:
    if explicit_format != "auto":
        return explicit_format
    return "json" if path.suffix.lower() == ".json" else "md"


def _write_output(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export a redacted synthetic main-chat prompt payload for FridaDev audit.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    synthetic = subparsers.add_parser("synthetic", help="build a synthetic non-sensitive main-chat payload")
    synthetic.add_argument("--output", required=True, help="output .md or .json path")
    synthetic.add_argument("--format", choices=("auto", "md", "json"), default="auto")
    synthetic.add_argument("--model", default="openai/gpt-5.1")
    synthetic.add_argument("--now", default="2026-05-21T12:00:00Z")
    synthetic.add_argument("--stream", action="store_true")

    args = parser.parse_args(argv)
    output_path = Path(args.output)
    payload, notes = build_synthetic_payload(
        model=str(args.model),
        now_iso=str(args.now),
        stream=bool(args.stream),
    )
    output_format = _format_from_output(output_path, str(args.format))
    if output_format == "json":
        rendered = _render_json(payload)
    else:
        rendered = _render_markdown(payload, notes=notes)
    _write_output(output_path, rendered)
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
