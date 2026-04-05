from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class ActiveIdentityProjection:
    block: str
    used_identity_ids: list[str]
    frida_mutable: dict[str, Any]
    user_mutable: dict[str, Any]


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _text(value: Any) -> str:
    return str(value or '').strip()


def _optional_str(value: Any) -> str | None:
    text = _text(value)
    return text or None


def _normalize_mutable(value: Any) -> dict[str, Any]:
    payload = _mapping(value)
    return {
        'content': _text(payload.get('content')),
        'source_trace_id': _optional_str(payload.get('source_trace_id')),
        'updated_by': _optional_str(payload.get('updated_by')),
        'update_reason': _optional_str(payload.get('update_reason')),
        'updated_ts': _optional_str(payload.get('updated_ts')) or _optional_str(payload.get('created_ts')),
    }


def _compose_section(title: str, *, static_text: str, mutable_text: str) -> str:
    parts: list[str] = []
    if static_text:
        parts.append('[STATIQUE]\n' + static_text)
    if mutable_text:
        parts.append('[MUTABLE]\n' + mutable_text)
    if not parts:
        return ''
    return f'[{title}]\n' + '\n\n'.join(parts)


def resolve_active_identity_projection(
    *,
    llm_static: str,
    user_static: str,
    get_mutable_identity_fn: Callable[[str], Any],
) -> ActiveIdentityProjection:
    frida_mutable = _normalize_mutable(get_mutable_identity_fn('llm'))
    user_mutable = _normalize_mutable(get_mutable_identity_fn('user'))
    block = '\n\n'.join(
        section
        for section in [
            _compose_section(
                'IDENTITÉ DU MODÈLE',
                static_text=_text(llm_static),
                mutable_text=_text(frida_mutable.get('content')),
            ),
            _compose_section(
                "IDENTITÉ DE L'UTILISATEUR",
                static_text=_text(user_static),
                mutable_text=_text(user_mutable.get('content')),
            ),
        ]
        if section
    )
    return ActiveIdentityProjection(
        block=block,
        used_identity_ids=[],
        frida_mutable=frida_mutable,
        user_mutable=user_mutable,
    )
