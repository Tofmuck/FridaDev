from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class MutableIdentityValidationResult:
    ok: bool
    reason_code: str


_SYSTEM_META_INSTRUCTION_PATTERNS = (
    re.compile(
        r"\b(?:you must|you need to|you have to|tu dois|vous devez|il faut)\b.{0,64}\b(?:system prompt|prompt syst(?:e|è)me|prompt herm(?:e|é)neutique|augmented_system|final_model_system_prompt)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(?:system prompt|prompt syst(?:e|è)me|prompt herm(?:e|é)neutique|augmented_system|final_model_system_prompt)\b.{0,64}\b(?:must|need to|have to|doit|doivent|faut)\b",
        re.IGNORECASE | re.DOTALL,
    ),
)

_RUNTIME_META_INSTRUCTION_PATTERNS = (
    re.compile(
        r"\b(?:you must|you need to|you have to|tu dois|vous devez|il faut)\b.{0,64}\b(?:source canonique|source de v(?:e|é)rit(?:e|é)|source of truth|runtime|pipeline|authelia|caddy|remote-user|admin token)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(?:mention|keep|remember|follow|respect|retain|rappelle|mentionne|respecte|garde)\b.{0,64}\b(?:source canonique|source de v(?:e|é)rit(?:e|é)|source of truth|runtime|pipeline|authelia|caddy|remote-user|admin token)\b",
        re.IGNORECASE | re.DOTALL,
    ),
)

_FORMAT_POLICY_PATTERNS = (
    re.compile(
        r"\b(?:always answer|answer|respond)\b.{0,32}\b(?:plain text|markdown|json|yaml|xml|html)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(?:tu dois|vous devez|il faut|r(?:e|é)ponds?|r(?:e|é)pondez)\b.{0,32}\b(?:texte brut|markdown|json|yaml|xml|html)\b",
        re.IGNORECASE | re.DOTALL,
    ),
)

_TOOL_POLICY_PATTERNS = (
    re.compile(r'\buse web search\b', re.IGNORECASE),
    re.compile(r"\bdo not browse\b", re.IGNORECASE),
    re.compile(r"\bdon't browse\b", re.IGNORECASE),
    re.compile(
        r"\b(?:use|do not use|don't use)\b.{0,32}\b(?:tools?|browser|browse|navigation|search)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(?:utilise|utilisez|n['’]utilise(?:z)?\s+pas|ne\s+cherche(?:r|z)?\s+pas|ne\s+navigue(?:r|z)?\s+pas)\b.{0,32}\b(?:outil(?:s)?|recherche web|navigation|browser|web)\b",
        re.IGNORECASE | re.DOTALL,
    ),
)

_OPERATOR_INSTRUCTION_PATTERNS = (
    re.compile(
        r"\b(?:you must|you need to|you have to)\b.{0,48}\b(?:verify|check|cite|clarify|suspend)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(?:verify|check)\b.{0,24}\bsources?\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bcite\b.{0,32}\b(?:each|every|important|key|relevant|point|points|sources?)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(r"\btu dois\b", re.IGNORECASE),
    re.compile(r"\bvous devez\b", re.IGNORECASE),
    re.compile(
        r"\bil faut\s+(?:r(?:e|é)pondre|v(?:e|é)rifier|citer|clarifier|suspendre)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:v(?:e|é)rifie(?:r|z)?|cite(?:r|z)?)\b.{0,32}\b(?:source|sources|point|points)\b",
        re.IGNORECASE | re.DOTALL,
    ),
)

_PROMPT_LIKE_RULES = (
    ('mutable_content_prompt_like_system_meta', _SYSTEM_META_INSTRUCTION_PATTERNS),
    ('mutable_content_prompt_like_runtime_meta', _RUNTIME_META_INSTRUCTION_PATTERNS),
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
