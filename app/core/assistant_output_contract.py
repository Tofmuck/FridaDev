from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class AssistantOutputPolicy:
    allow_structure: bool = False
    allow_code: bool = False


_EXPLICIT_LIST_REQUEST_PATTERNS = (
    re.compile(
        r'\b(?:donne(?:-moi)?|fais(?:-moi)?|fournis(?:-moi)?|propose|présente|presente|organise|structure|rédige|redige|montre(?:-moi)?)\b'
        r'[^.\n:;!?]{0,60}\b(?:plan|liste|list|étape|etape|étapes|etapes|puces|bullet)\b'
    ),
    re.compile(
        r'\b(?:fais|donne(?:-moi)?|fournis(?:-moi)?|propose|présente|presente)\b'
        r'[^.\n:;!?]{0,30}\b(?:une?\s+)?liste\b'
    ),
)
_EXPLICIT_CODE_REQUEST_PATTERNS = (
    re.compile(
        r'\b(?:donne(?:-moi)?|fais(?:-moi)?|fournis(?:-moi)?|montre(?:-moi)?|écris|ecris|génère|genere|propose)\b'
        r'[^.\n:;!?]{0,60}\b(?:exemple de code|code|snippet|commande|script)\b'
    ),
    re.compile(
        r'\b(?:donne(?:-moi)?|fais(?:-moi)?|fournis(?:-moi)?|montre(?:-moi)?|écris|ecris|génère|genere|propose)\b'
        r'[^.\n:;!?]{0,60}\b(?:bash|shell|python|javascript|typescript|js|sql|regex)\b'
    ),
)
_HEADER_RE = re.compile(r'^(\s*)#{1,6}\s+')
_BLOCKQUOTE_RE = re.compile(r'^(\s*)>\s*')
_HORIZONTAL_RULE_RE = re.compile(r'^\s*(?:-{3,}|\*{3,}|_{3,})\s*$')
_CODE_FENCE_OPEN_RE = re.compile(r'^\s*(`{3,})[^`]*$')
_CODE_FENCE_CLOSE_RE = re.compile(r'^\s*(`{3,})\s*$')
_BOLD_RE = re.compile(r'\*\*(.+?)\*\*|__(.+?)__')
_ITALIC_STAR_RE = re.compile(r'(?<!\*)\*([^*\n]+)\*(?!\*)')
_ITALIC_UNDERSCORE_RE = re.compile(r'(?<!_)_([^_\n]+)_(?!_)')


def _text(value: Any) -> str:
    return str(value or '').strip()


def _normalized_lower_text(value: Any) -> str:
    return _text(value).lower()


def _contains_any_pattern(value: Any, patterns: tuple[re.Pattern[str], ...]) -> bool:
    haystack = _normalized_lower_text(value)
    return any(pattern.search(haystack) for pattern in patterns)


def resolve_assistant_output_policy(user_msg: str) -> AssistantOutputPolicy:
    return AssistantOutputPolicy(
        allow_structure=_contains_any_pattern(user_msg, _EXPLICIT_LIST_REQUEST_PATTERNS),
        allow_code=_contains_any_pattern(user_msg, _EXPLICIT_CODE_REQUEST_PATTERNS),
    )


def build_plain_text_guard_block(policy: AssistantOutputPolicy) -> str:
    lines = [
        '[CONTRAT TEXTE BRUT]',
        'Privilégie une forme sobre et lisible, sans Markdown décoratif ou spectaculaire.',
        'Par défaut, réponds en paragraphes clairs.',
        "Quand l'analyse est longue ou structurée, tu peux utiliser des titres sobres, des listes simples ou un tableau si cela rend la réponse plus claire.",
    ]
    if policy.allow_structure:
        lines.append(
            "L'utilisateur demande explicitement un plan, des étapes ou une liste: une structure simple est bienvenue si elle aide la lecture."
        )
    else:
        lines.append(
            "N'ajoute pas de structure gratuite: utilise titres ou listes seulement s'ils clarifient vraiment la réponse."
        )

    if policy.allow_code:
        lines.append("L'utilisateur demande explicitement du code: un bloc de code est autorisé seulement si c'est vraiment utile.")
    else:
        lines.append("N'utilise pas de code fences ni de blocs de code, sauf si le format de la réponse l'exige vraiment.")

    return '\n'.join(lines)


def should_buffer_plain_text_stream(policy: AssistantOutputPolicy | None) -> bool:
    return True


def _strip_inline_markdown(text: str) -> str:
    without_bold = _BOLD_RE.sub(lambda m: m.group(1) or m.group(2) or '', text)
    without_star = _ITALIC_STAR_RE.sub(r'\1', without_bold)
    return _ITALIC_UNDERSCORE_RE.sub(r'\1', without_star)


def _normalize_line(line: str, policy: AssistantOutputPolicy) -> str:
    if _HORIZONTAL_RULE_RE.match(line):
        return ''

    normalized = _HEADER_RE.sub(r'\1', line)
    normalized = _BLOCKQUOTE_RE.sub(r'\1', normalized)

    if not policy.allow_code and normalized.lstrip().startswith('```'):
        return ''

    return _strip_inline_markdown(normalized)


def normalize_assistant_output(text: str, policy: AssistantOutputPolicy | None) -> str:
    current = policy or AssistantOutputPolicy()
    raw = str(text or '').replace('\r', '')
    normalized_lines: list[tuple[str, bool]] = []
    fenced_code_delimiter_length: int | None = None

    for line in raw.split('\n'):
        if fenced_code_delimiter_length is None:
            opening_fence = _CODE_FENCE_OPEN_RE.match(line)
            if opening_fence is None:
                normalized_line = _normalize_line(line, current)
                if (
                    not normalized_line
                    and normalized_lines
                    and not normalized_lines[-1][0]
                    and not normalized_lines[-1][1]
                ):
                    continue
                normalized_lines.append((normalized_line, False))
                continue
            fenced_code_delimiter_length = len(opening_fence.group(1))
            if not current.allow_code:
                continue
            normalized_lines.append((_normalize_line(line, current), False))
            continue

        closing_fence = _CODE_FENCE_CLOSE_RE.match(line)
        if (
            closing_fence is not None
            and len(closing_fence.group(1)) >= fenced_code_delimiter_length
        ):
            fenced_code_delimiter_length = None
            if current.allow_code:
                normalized_lines.append((_normalize_line(line, current), False))
            continue
        if current.allow_code:
            normalized_lines.append((line, True))

    normalized = '\n'.join(line for line, _is_code_body in normalized_lines)
    if normalized_lines and normalized_lines[-1][1]:
        return normalized.lstrip()
    return normalized.strip()
