"""Minimal chat wiring for native Biblio.

This module decides whether an already user-enabled Biblio turn is explicit
enough to consult Catalogue.  It stays content-free outside the prompt lane:
raw titles, locators and passages are only used internally to resolve and
extract a bounded passage.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .catalogue_client import CatalogueClient
from .document_resolver import BiblioResolveRequest
from .observability import build_biblio_event_payload
from .passage_extractor import BiblioPassageExtractor, BiblioPassageRequest, BiblioPassageResult
from .prompt_lane import BiblioPromptLane, build_biblio_prompt_lane


PAYLOAD_KEY_BIBLIO_ENABLED = "biblio_enabled"

REASON_TOGGLE_DISABLED = "biblio_toggle_disabled"
REASON_NO_BIBLIOGRAPHIC_SIGNAL = "biblio_no_bibliographic_signal"
REASON_ADOBE_TOPIC_IGNORED = "biblio_adobe_topic_ignored"
REASON_DOCUMENT_SIGNAL_DETECTED = "biblio_document_signal_detected"
REASON_DOCUMENT_LOCATOR_SIGNAL_DETECTED = "biblio_document_locator_signal_detected"
REASON_RUNTIME_ERROR = "biblio_runtime_error"

QUERY_KIND_NOT_REQUESTED = "not_requested"
QUERY_KIND_NO_SIGNAL = "no_signal"
QUERY_KIND_DOCUMENT = "document"
QUERY_KIND_DOCUMENT_LOCATOR = "document_locator"

_STEPLIKE_LOCATOR_RE = re.compile(r"\b([1-9][0-9]{1,3}[a-e])\b", re.IGNORECASE)
_STEPLIKE_RANGE_RE = re.compile(
    r"\b([1-9][0-9]{1,3}[a-e])\s*(?:->|-->|-|a|à)\s*([1-9][0-9]{1,3}[a-e])\b",
    re.IGNORECASE,
)
_DOC_ID_RE = re.compile(
    r"\b(?:catalogue_doc|document_id|doc_id)\s*[:=]\s*([A-Za-z0-9][A-Za-z0-9_.:-]{2,127})",
    re.IGNORECASE,
)
_QUOTED_TITLE_RE = re.compile(
    r"\b(?:titre|ouvrage|document)\s*[:=]?\s*[\"'“”]([^\"'“”\n]{2,120})[\"'“”]",
    re.IGNORECASE,
)
_INLINE_TITLE_RE = re.compile(
    r"\b(?:titre|ouvrage|document)\s*[:=]\s*([^,.;?!\n]{2,120})",
    re.IGNORECASE,
)
_DANS_RE = re.compile(r"\b(?:dans|chez)\s+([^,.;?!\n]{2,120})", re.IGNORECASE)
_AUTHOR_RE = re.compile(r"\bauteur\s*[:=]\s*([^,.;?!\n]{2,80})", re.IGNORECASE)


@dataclass(frozen=True)
class BiblioChatDecision:
    enabled: bool
    should_attempt: bool
    reason_code: str
    query_kind: str = QUERY_KIND_NOT_REQUESTED
    resolve_request: BiblioResolveRequest | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True, repr=False)
class BiblioChatResult:
    enabled: bool
    used: bool
    reason_code: str
    query_kind: str
    observability_payload: dict[str, Any]
    passage_result: BiblioPassageResult | None = field(default=None, repr=False, compare=False)
    prompt_lane: BiblioPromptLane | None = field(default=None, repr=False, compare=False)

    @property
    def prompt_message(self) -> dict[str, Any] | None:
        if self.prompt_lane is None:
            return None
        return self.prompt_lane.message


def resolve_biblio_chat_decision(data: Mapping[str, Any], user_msg: str) -> BiblioChatDecision:
    enabled = _truthy(data.get(PAYLOAD_KEY_BIBLIO_ENABLED))
    if not enabled:
        return BiblioChatDecision(
            enabled=False,
            should_attempt=False,
            reason_code=REASON_TOGGLE_DISABLED,
            query_kind=QUERY_KIND_NOT_REQUESTED,
        )

    folded = _fold(user_msg)
    if _adobe_topic_without_biblio_signal(folded):
        return BiblioChatDecision(
            enabled=True,
            should_attempt=False,
            reason_code=REASON_ADOBE_TOPIC_IGNORED,
            query_kind=QUERY_KIND_NO_SIGNAL,
        )

    request = _resolve_request_from_message(user_msg)
    if request is None:
        return BiblioChatDecision(
            enabled=True,
            should_attempt=False,
            reason_code=REASON_NO_BIBLIOGRAPHIC_SIGNAL,
            query_kind=QUERY_KIND_NO_SIGNAL,
        )

    has_locator = bool(request.locator or request.locator_end)
    return BiblioChatDecision(
        enabled=True,
        should_attempt=True,
        reason_code=REASON_DOCUMENT_LOCATOR_SIGNAL_DETECTED if has_locator else REASON_DOCUMENT_SIGNAL_DETECTED,
        query_kind=QUERY_KIND_DOCUMENT_LOCATOR if has_locator else QUERY_KIND_DOCUMENT,
        resolve_request=request,
    )


def run_biblio_chat_turn(
    data: Mapping[str, Any],
    *,
    user_msg: str,
    config_module: Any = None,
    client_factory: Any = CatalogueClient,
    extractor_factory: Any = BiblioPassageExtractor,
    lane_builder: Any = build_biblio_prompt_lane,
    observability_builder: Any = build_biblio_event_payload,
) -> BiblioChatResult:
    decision = resolve_biblio_chat_decision(data, user_msg)
    if not decision.should_attempt or decision.resolve_request is None:
        status = "not_applicable" if not decision.enabled else "not_used"
        payload = observability_builder(
            enabled=decision.enabled,
            used=False,
            query_kind=decision.query_kind,
            status=status,
            reason_code=decision.reason_code,
        )
        return BiblioChatResult(
            enabled=decision.enabled,
            used=False,
            reason_code=decision.reason_code,
            query_kind=decision.query_kind,
            observability_payload=payload,
        )

    try:
        client = client_factory(config_module=config_module)
        extractor = extractor_factory(client)
        passage_result = extractor.extract(
            BiblioPassageRequest(resolve_request=decision.resolve_request)
        )
        prompt_lane = lane_builder([passage_result])
        payload = observability_builder(
            enabled=True,
            used=True,
            query_kind=decision.query_kind,
            resolution=passage_result.resolution,
            passage_result=passage_result,
            prompt_lane=prompt_lane,
            reason_code=decision.reason_code,
        )
        return BiblioChatResult(
            enabled=True,
            used=True,
            reason_code=decision.reason_code,
            query_kind=decision.query_kind,
            passage_result=passage_result,
            prompt_lane=prompt_lane,
            observability_payload=payload,
        )
    except Exception as exc:
        payload = observability_builder(
            enabled=True,
            used=True,
            query_kind=decision.query_kind,
            status="error",
            reason_code=REASON_RUNTIME_ERROR,
            client_error={
                "status": "error",
                "reason_code": REASON_RUNTIME_ERROR,
                "error_class": exc.__class__.__name__,
            },
        )
        return BiblioChatResult(
            enabled=True,
            used=True,
            reason_code=REASON_RUNTIME_ERROR,
            query_kind=decision.query_kind,
            observability_payload=payload,
        )


def inject_biblio_prompt_lane(
    prompt_messages: list[dict[str, Any]],
    result: BiblioChatResult,
) -> bool:
    message = result.prompt_message
    if not message:
        return False
    insert_at = _before_last_user_index(prompt_messages)
    prompt_messages[insert_at:insert_at] = [dict(message)]
    return True


def _resolve_request_from_message(user_msg: str) -> BiblioResolveRequest | None:
    text = str(user_msg or "").strip()
    if not text:
        return None
    folded = _fold(text)
    if "document actif" in folded or "documents actifs" in folded:
        return None

    document_id = _extract_document_id(text)
    locator, locator_end = _extract_locator_pair(folded)
    title = _extract_title(text, folded, locator=locator)
    author = _extract_author(text)

    if not document_id and not title and not author:
        return None
    if _only_vague_book_signal(folded, title=title, author=author, document_id=document_id):
        return None

    return BiblioResolveRequest(
        document_id=document_id,
        title=title,
        author=author,
        locator=locator,
        locator_end=locator_end,
        locator_kind="stephanus" if locator or locator_end else "stephanus",
    )


def _extract_document_id(text: str) -> str:
    match = _DOC_ID_RE.search(text)
    return match.group(1).strip() if match else ""


def _extract_locator_pair(folded_text: str) -> tuple[str, str]:
    range_match = _STEPLIKE_RANGE_RE.search(folded_text)
    if range_match:
        return range_match.group(1).lower(), range_match.group(2).lower()
    locator_match = _STEPLIKE_LOCATOR_RE.search(folded_text)
    if locator_match:
        return locator_match.group(1).lower(), ""
    return "", ""


def _extract_title(text: str, folded_text: str, *, locator: str) -> str:
    for regex in (_QUOTED_TITLE_RE, _INLINE_TITLE_RE):
        match = regex.search(text)
        if match:
            candidate = _clean_title_candidate(match.group(1), locator=locator)
            if _is_usable_title(candidate):
                return candidate

    for match in _DANS_RE.finditer(text):
        candidate = _clean_title_candidate(match.group(1), locator=locator)
        if _is_usable_title(candidate):
            return candidate

    if locator and _has_biblio_catalogue_cue(folded_text):
        candidate = _title_before_locator(text, locator)
        if _is_usable_title(candidate):
            return candidate
    return ""


def _extract_author(text: str) -> str:
    match = _AUTHOR_RE.search(text)
    if not match:
        return ""
    candidate = _clean_title_candidate(match.group(1), locator="")
    return candidate if _is_usable_title(candidate) else ""


def _title_before_locator(text: str, locator: str) -> str:
    if not locator:
        return ""
    index = _fold(text).find(locator.lower())
    if index <= 0:
        return ""
    prefix = text[:index]
    parts = re.split(r"\b(?:bibliotheque|bibliothèque|catalogue|biblio|passage|cherche|recherche|consulte)\b", prefix, flags=re.IGNORECASE)
    return _clean_title_candidate(parts[-1] if parts else "", locator=locator)


def _clean_title_candidate(value: str, *, locator: str) -> str:
    text = str(value or "").strip(" \t\r\n'\"“”")
    text = re.sub(
        r"\s+(?:dans\s+|du\s+|de\s+)?(?:le\s+|la\s+)?(?:catalogue|bibliotheque|bibliothèque|biblio)\b.*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\b(?:le|la|les|un|une|du|de la|des)\s+", "", text, count=1, flags=re.IGNORECASE).strip()
    text = _STEPLIKE_LOCATOR_RE.sub("", text)
    if locator:
        text = re.sub(re.escape(locator), "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:passage|stephanus|page|paragraphe|dans|chez|cherche|recherche|consulte|catalogue|bibliotheque|bibliothèque|biblio)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" ,;:-")
    return text[:120]


def _is_usable_title(candidate: str) -> bool:
    text = str(candidate or "").strip()
    if len(text) < 2:
        return False
    folded = _fold(text)
    rejected = {
        "bibliotheque",
        "biblio",
        "catalogue",
        "livre",
        "ouvrage",
        "document",
        "document actif",
        "documents actifs",
        "web",
        "adobe",
        "photoshop",
        "illustrator",
    }
    if folded in rejected:
        return False
    if re.fullmatch(r"(?:mon|ma|mes|ton|ta|tes|son|sa|ses|ce|cet|cette|le|la|un|une)?\s*(?:livre|ouvrage)s?", folded):
        return False
    return True


def _has_biblio_catalogue_cue(folded: str) -> bool:
    return any(
        cue in folded
        for cue in (
            "bibliotheque",
            "biblio",
            "catalogue",
            "cherche dans",
            "recherche dans",
            "consulte",
            "stephanus",
        )
    )


def _adobe_topic_without_biblio_signal(folded: str) -> bool:
    if not any(term in folded for term in ("adobe", "photoshop", "illustrator")):
        return False
    return not _has_biblio_catalogue_cue(folded)


def _only_vague_book_signal(folded: str, *, title: str, author: str, document_id: str) -> bool:
    if title or author or document_id:
        return False
    return "livre" in folded or "ouvrage" in folded


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "on", "enabled", "active"}


def _before_last_user_index(prompt_messages: Sequence[Mapping[str, Any]]) -> int:
    for index in range(len(prompt_messages) - 1, -1, -1):
        if str(prompt_messages[index].get("role") or "") == "user":
            return index
    return len(prompt_messages)


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()
