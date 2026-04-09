from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class MutableIdentityValidationResult:
    ok: bool
    reason_code: str


_SYSTEM_META_PATTERNS = (
    re.compile(r'\bsystem prompt\b', re.IGNORECASE),
    re.compile(r'\bprompt syst(?:e|è)me\b', re.IGNORECASE),
    re.compile(r'\bprompt herm(?:e|é)neutique\b', re.IGNORECASE),
    re.compile(r'\baugmented_system\b', re.IGNORECASE),
    re.compile(r'\bfinal_model_system_prompt\b', re.IGNORECASE),
)

_RUNTIME_META_PATTERNS = (
    re.compile(r'\bsource canonique\b', re.IGNORECASE),
    re.compile(r'\bsource de v(?:e|é)rit(?:e|é)\b', re.IGNORECASE),
    re.compile(r'\bsource of truth\b', re.IGNORECASE),
    re.compile(r'\bruntime\b', re.IGNORECASE),
    re.compile(r'\bpipeline\b', re.IGNORECASE),
    re.compile(r'\bauthelia\b', re.IGNORECASE),
    re.compile(r'\bcaddy\b', re.IGNORECASE),
    re.compile(r'\bremote-user\b', re.IGNORECASE),
    re.compile(r'\badmin token\b', re.IGNORECASE),
)

_FORMAT_POLICY_PATTERNS = (
    re.compile(r'\bmarkdown\b', re.IGNORECASE),
    re.compile(r'\bjson\b', re.IGNORECASE),
    re.compile(r'\byaml\b', re.IGNORECASE),
    re.compile(r'\bxml\b', re.IGNORECASE),
    re.compile(r'\bhtml\b', re.IGNORECASE),
)

_TOOL_POLICY_PATTERNS = (
    re.compile(r'\bweb search\b', re.IGNORECASE),
    re.compile(r'\bnavigation\b', re.IGNORECASE),
    re.compile(r'\bbrowser\b', re.IGNORECASE),
    re.compile(r'\bbrowse\b', re.IGNORECASE),
    re.compile(r'\bcrawl4ai\b', re.IGNORECASE),
    re.compile(
        r"\b(?:utilise(?:r|z)?|n['’]utilise(?:r|z)?\s+pas|use|do not use)\b.{0,48}\b(?:outil(?:s)?|tool(?:s)?|web|browser|browse|search|navigation)\b",
        re.IGNORECASE | re.DOTALL,
    ),
)

_OPERATOR_INSTRUCTION_PATTERNS = (
    re.compile(r'\btu dois\b', re.IGNORECASE),
    re.compile(r'\bvous devez\b', re.IGNORECASE),
    re.compile(
        r"\bil faut\s+(?:r(?:e|é)pondre|utiliser|chercher|v(?:e|é)rifier|citer|clarifier|suspendre|naviguer|respecter|suivre)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\br(?:e|é)ponds?\s+(?:toujours|en|avec|sans)\b", re.IGNORECASE),
    re.compile(r"\bne\s+r(?:e|é)ponds?\s+pas\b", re.IGNORECASE),
    re.compile(
        r"\b(?:v(?:e|é)rifie(?:r|z)?|cite(?:r|z)?|clarifie(?:r|z)?|cherche(?:r|z)?|navigue(?:r|z)?)\b.{0,32}\b(?:web|source|outil(?:s)?|tool(?:s)?|prompt|markdown|json)\b",
        re.IGNORECASE | re.DOTALL,
    ),
)

_PROMPT_LIKE_RULES = (
    ('mutable_content_prompt_like_system_meta', _SYSTEM_META_PATTERNS),
    ('mutable_content_prompt_like_runtime_meta', _RUNTIME_META_PATTERNS),
    ('mutable_content_prompt_like_format_policy', _FORMAT_POLICY_PATTERNS),
    ('mutable_content_prompt_like_tool_policy', _TOOL_POLICY_PATTERNS),
    ('mutable_content_prompt_like_operator_instruction', _OPERATOR_INSTRUCTION_PATTERNS),
)


def _text(value: object) -> str:
    return str(value or '').strip()


def validate_mutable_identity_content(content: object) -> MutableIdentityValidationResult:
    text = _text(content)
    if not text:
        return MutableIdentityValidationResult(ok=True, reason_code='ok')

    for reason_code, patterns in _PROMPT_LIKE_RULES:
        if any(pattern.search(text) for pattern in patterns):
            return MutableIdentityValidationResult(ok=False, reason_code=reason_code)

    return MutableIdentityValidationResult(ok=True, reason_code='ok')
