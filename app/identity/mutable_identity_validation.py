from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class MutableIdentityValidationResult:
    ok: bool
    reason_code: str


_SYSTEM_META_INSTRUCTION_PATTERNS = (
    re.compile(
        r"\b(?:you must|you need to|you have to|tu dois|vous devez|il faut)\b.{0,64}\b(?:system prompt|prompt systeme|prompt hermeneutique|augmented_system|final_model_system_prompt)\b",
        re.DOTALL,
    ),
    re.compile(
        r"\b(?:system prompt|prompt systeme|prompt hermeneutique|augmented_system|final_model_system_prompt)\b.{0,64}\b(?:must|need to|have to|doit|doivent|faut)\b",
        re.DOTALL,
    ),
)

_RUNTIME_META_INSTRUCTION_PATTERNS = (
    re.compile(
        r"\b(?:you must|you need to|you have to|tu dois|vous devez|il faut)\b.{0,64}\b(?:source canonique|source de verite|source of truth|runtime|pipeline|authelia|caddy|remote-user|admin token)\b",
        re.DOTALL,
    ),
    re.compile(
        r"\b(?:mention|keep|remember|follow|respect|retain|rappelle|mentionne|respecte|garde)\b.{0,64}\b(?:source canonique|source de verite|source of truth|runtime|pipeline|authelia|caddy|remote-user|admin token)\b",
        re.DOTALL,
    ),
)

_FORMAT_POLICY_PATTERNS = (
    re.compile(
        r"\b(?:always answer|answer|respond)\b.{0,32}\b(?:plain text|markdown|json|yaml|xml|html)\b",
        re.DOTALL,
    ),
    re.compile(
        r"\b(?:tu dois|vous devez|il faut|reponds?|repondez)\b.{0,32}\b(?:texte brut|markdown|json|yaml|xml|html)\b",
        re.DOTALL,
    ),
)

_TOOL_POLICY_PATTERNS = (
    re.compile(r'\buse web search\b'),
    re.compile(r"\bdo not browse\b"),
    re.compile(r"\bdon't browse\b"),
    re.compile(
        r"\b(?:use|do not use|don't use)\b.{0,32}\b(?:tools?|browser|browse|navigation|search)\b",
        re.DOTALL,
    ),
    re.compile(
        r"\b(?:utilise|utilisez|n['’]utilise(?:z)?\s+pas|ne\s+cherche(?:r|z)?\s+pas|ne\s+navigue(?:r|z)?\s+pas)\b.{0,32}\b(?:outil(?:s)?|recherche web|navigation|browser|web)\b",
        re.DOTALL,
    ),
)

_OPERATOR_INSTRUCTION_PATTERNS = (
    re.compile(
        r"\b(?:you must|you need to|you have to)\b.{0,48}\b(?:verify|check|cite|clarify|suspend)\b",
        re.DOTALL,
    ),
    re.compile(
        r"\b(?:verify|check)\b.{0,24}\bsources?\b",
        re.DOTALL,
    ),
    re.compile(
        r"\bcite\b.{0,32}\b(?:each|every|important|key|relevant|point|points|sources?)\b",
        re.DOTALL,
    ),
    re.compile(r"\btu dois\b"),
    re.compile(r"\bvous devez\b"),
    re.compile(
        r"\bil faut\s+(?:repondre|verifier|citer|clarifier|suspendre)\b",
    ),
    re.compile(
        r"\b(?:verifie(?:r|z)?|cite(?:r|z)?)\b.{0,32}\b(?:source|sources|point|points)\b",
        re.DOTALL,
    ),
)

_PROMPT_LIKE_RULES = (
    ('mutable_content_prompt_like_system_meta', _SYSTEM_META_INSTRUCTION_PATTERNS),
    ('mutable_content_prompt_like_runtime_meta', _RUNTIME_META_INSTRUCTION_PATTERNS),
    ('mutable_content_prompt_like_format_policy', _FORMAT_POLICY_PATTERNS),
    ('mutable_content_prompt_like_tool_policy', _TOOL_POLICY_PATTERNS),
    ('mutable_content_prompt_like_operator_instruction', _OPERATOR_INSTRUCTION_PATTERNS),
)

_CONVERSATIONAL_PREFERENCE_PATTERNS = (
    re.compile(
        r"\b(?:prefere|souhaite|attend|veut|aime(?: bien)?|apprecie)\b.{0,48}\b(?:discuter|parler|echanger|conversation|dialogue|echange|reponses?|explications?|formulations?|ton|style|qu on|qu'on|lui repondre)\b",
        re.DOTALL,
    ),
    re.compile(
        r"\b(?:reponses?|explications?|formulations?|style(?:s)?\s+de\s+reponse|style(?:s)?\s+des\s+reponses|echanges?|conversation)\b.{0,32}\b(?:courtes?|longues?|direct(?:es?)?|detaille(?:es?)?|simples?|calmes?|chaleureu(?:x|se)|sobres?)\b",
        re.DOTALL,
    ),
    re.compile(
        r"\b(?:repond(?:re|s|ez)?|formul(?:er|e|es)|expliqu(?:er|e|es))\b.{0,32}\b(?:simplement|calmement|sobrement|directement|longuement|brievement|en detail)\b",
        re.DOTALL,
    ),
    re.compile(
        r"\b(?:rassure|rassurant|apaise|apaisant|confort conversationnel|met a l aise|mettre a l aise|a l aise|se sent compris|se sentir compris|se sent accompagne|se sentir accompagne|besoin d etre rassure)\b",
        re.DOTALL,
    ),
)

_UTILITY_FRAMING_PATTERNS = (
    re.compile(
        r"\b(?:utile|aide|permet|sert|facilite|oriente|guide|cadre|optimise|ameliore)\b.{0,48}\b(?:reponse|dialogue|conversation|echange|tour|tache|travail|reprise|pilotage)\b",
        re.DOTALL,
    ),
    re.compile(
        r"\b(?:pour|afin de)\b.{0,24}\b(?:mieux repondre|guider|orienter|cadrer|reprendre|aider|faciliter)\b",
        re.DOTALL,
    ),
    re.compile(
        r"\b(?:repere|rappel|memo)\b.{0,24}\b(?:utile|operatoire|pratique)\b",
        re.DOTALL,
    ),
)

_WEAK_RELATIONAL_PATTERNS = (
    re.compile(
        r"\b(?:relation|proximite|lien|posture relationnelle|rapport)\b.{0,32}\b(?:chaleureu(?:x|se)|rassurant|accueillant|confortable|apaisant|accompagnant|a l ecoute)\b",
        re.DOTALL,
    ),
    re.compile(
        r"\b(?:dans l echange|dans le dialogue|en conversation|avec l utilisateur|aupres de l autre|face a l utilisateur)\b.{0,32}\b(?:chaleureu(?:x|se)|rassurant|accueillant|disponible|accompagnant|a l ecoute)\b",
        re.DOTALL,
    ),
    re.compile(
        r"\b(?:cherche|vise|tente|essaie)\b.{0,32}\b(?:proximite|chaleur|rassurance|reassurance|confort relationnel|apaisement)\b",
        re.DOTALL,
    ),
)

_SEMANTIC_ADMISSION_RULES = (
    ('mutable_content_conversational_preference', _CONVERSATIONAL_PREFERENCE_PATTERNS),
    ('mutable_content_utilitarian_framing', _UTILITY_FRAMING_PATTERNS),
    ('mutable_content_weak_relational_positioning', _WEAK_RELATIONAL_PATTERNS),
)

_SENTENCE_SPLIT_RE = re.compile(r'\n+|(?<=[.!?])\s+')
_SUBJECT_ANCHOR_RE = re.compile(r"\b(?:frida|tof|l utilisateur|utilisateur|l assistant|assistant)\b")
_CONTINUATION_PRONOUN_RE = re.compile(r"^(?:il|elle)\b")
_IDENTITY_VERB_PATTERNS = (
    re.compile(r"\b(?:est|reste|demeure|garde|maintient|porte|manifeste|cultive|assume)\b"),
    re.compile(r"\bse\s+(?:tient|montre|deploie)\b"),
    re.compile(
        r"\b(?:travaille|traite|part|revient|aborde|approche|considere|regarde|pense|insiste|privilegie|accorde)\b"
    ),
)
_IDENTITY_TRAIT_PATTERNS = (
    re.compile(
        r"\b(?:stable|durable|sobre|calme|precis(?:e)?|structure(?:e)?|compact(?:e)?|ritualise(?:e)?|retenu(?:e)?|mesure(?:e)?|coheren(?:t|te)|constant(?:e)?|non intrusive?|attentif|attentive|sensible)\b"
    ),
    re.compile(
        r"\b(?:voix|ton|tenue|posture|orientation|clarte|presence|attention|curiosite|axe|maniere|trait|continuite|ancrage|discipline|mesure|justesse|distance|gout|retenue|exigence|precision|reflexion|reprises?|seuils?|contexte|interpretation|mise\s+en\s+forme|architectures?|structures?|conditions?\s+reelles?)\b"
    ),
)


def _text(value: object) -> str:
    return str(value or '').strip()


def _normalized_text(value: object) -> str:
    raw = _text(value)
    if not raw:
        return ''
    normalized = unicodedata.normalize('NFKD', raw)
    without_accents = ''.join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r'\s+', ' ', without_accents).strip().lower()


def _split_sentences(text: str) -> list[str]:
    parts = [_text(part) for part in _SENTENCE_SPLIT_RE.split(text)]
    return [part for part in parts if part]


def _matches_any(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _semantic_reason_for_block(text: str) -> str | None:
    for sentence in _split_sentences(text):
        normalized = _normalized_text(sentence)
        for reason_code, patterns in _SEMANTIC_ADMISSION_RULES:
            if _matches_any(normalized, patterns):
                return reason_code
    return None


def _looks_identity_sentence(sentence: str, *, allow_pronoun: bool) -> bool:
    normalized = _normalized_text(sentence)
    has_anchor = bool(_SUBJECT_ANCHOR_RE.search(normalized))
    has_pronoun = allow_pronoun and bool(_CONTINUATION_PRONOUN_RE.search(normalized))
    if not has_anchor and not has_pronoun:
        return False
    if not _matches_any(normalized, _IDENTITY_VERB_PATTERNS):
        return False
    if not _matches_any(normalized, _IDENTITY_TRAIT_PATTERNS):
        return False
    return True


def _is_identity_declarative(text: str) -> bool:
    sentences = _split_sentences(text)
    if not sentences:
        return True
    saw_anchor = False
    for sentence in sentences:
        normalized = _normalized_text(sentence)
        has_anchor = bool(_SUBJECT_ANCHOR_RE.search(normalized))
        if not _looks_identity_sentence(sentence, allow_pronoun=saw_anchor and not has_anchor):
            return False
        saw_anchor = saw_anchor or has_anchor
    return saw_anchor


def validate_mutable_identity_content(content: object) -> MutableIdentityValidationResult:
    text = _text(content)
    if not text:
        return MutableIdentityValidationResult(ok=True, reason_code='ok')
    normalized = _normalized_text(text)

    for reason_code, patterns in _PROMPT_LIKE_RULES:
        if _matches_any(normalized, patterns):
            return MutableIdentityValidationResult(ok=False, reason_code=reason_code)

    semantic_reason = _semantic_reason_for_block(text)
    if semantic_reason:
        return MutableIdentityValidationResult(ok=False, reason_code=semantic_reason)

    if not _is_identity_declarative(text):
        return MutableIdentityValidationResult(ok=False, reason_code='mutable_content_not_identity_statement')

    return MutableIdentityValidationResult(ok=True, reason_code='ok')
