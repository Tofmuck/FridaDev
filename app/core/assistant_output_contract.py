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
_BULLET_RE = re.compile(r'^(\s*)[-*•]\s+')
_NUMBERED_RE = re.compile(r'^(\s*)\d+[.)]\s+')
_CODE_FENCE_RE = re.compile(r'^\s*```')
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
        'Réponds pour cette surface en texte brut strict, lisible sans rendu Markdown.',
        'Interdit: titres Markdown, gras/italique Markdown, règles horizontales, blockquotes, tableaux Markdown.',
    ]
    if policy.allow_structure:
        lines.append(
            "L'utilisateur demande explicitement un plan, des étapes ou une liste: une structure textuelle minimale est autorisée, sans décoration Markdown."
        )
    else:
        lines.append(
            "Pour ce tour, n'utilise ni puces, ni listes numérotées, ni lignes commençant par `-`, `*`, `•`, `1)` ou `1.`."
        )
        lines.append('Réponds en courts paragraphes continus.')

    if policy.allow_code:
        lines.append("L'utilisateur demande explicitement du code: un bloc de code est autorisé seulement si c'est vraiment utile.")
    else:
        lines.append("Pour ce tour, n'utilise pas de code fences ni de blocs de code.")

    return '\n'.join(lines)


def should_buffer_plain_text_stream(policy: AssistantOutputPolicy | None) -> bool:
    current = policy or AssistantOutputPolicy()
    return not current.allow_structure and not current.allow_code


def _strip_inline_markdown(text: str) -> str:
    without_bold = _BOLD_RE.sub(lambda m: m.group(1) or m.group(2) or '', text)
    without_star = _ITALIC_STAR_RE.sub(r'\1', without_bold)
    return _ITALIC_UNDERSCORE_RE.sub(r'\1', without_star)


def _normalize_line(line: str, policy: AssistantOutputPolicy) -> str:
    if _HORIZONTAL_RULE_RE.match(line):
        return ''

    normalized = _HEADER_RE.sub(r'\1', line)
    normalized = _BLOCKQUOTE_RE.sub(r'\1', normalized)

    if not policy.allow_structure:
        normalized = _BULLET_RE.sub(r'\1', normalized)
        normalized = _NUMBERED_RE.sub(r'\1', normalized)

    if not policy.allow_code and normalized.lstrip().startswith('```'):
        return ''

    return _strip_inline_markdown(normalized)


def normalize_assistant_output(text: str, policy: AssistantOutputPolicy | None) -> str:
    current = policy or AssistantOutputPolicy()
    raw = str(text or '').replace('\r', '')
    normalized_lines: list[str] = []
    in_fenced_code_block = False

    for line in raw.split('\n'):
        if not current.allow_code and _CODE_FENCE_RE.match(line):
            in_fenced_code_block = not in_fenced_code_block
            continue
        if in_fenced_code_block and not current.allow_code:
            continue
        normalized_lines.append(_normalize_line(line, current))

    normalized = '\n'.join(normalized_lines)
    normalized = re.sub(r'\n{3,}', '\n\n', normalized)
    return normalized.strip()
