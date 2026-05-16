from __future__ import annotations

"""Prompt lane builder for active conversation documents.

The lane is deliberately separate from the active document state store and from
text extraction. It decides, per turn, which active documents can be injected in
full, and emits compact non-injection signals for the rest.
"""

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

REASON_TOO_LARGE = "document_too_large_for_turn"
REASON_EMPTY = "document_empty_text"

LANE_HEADER = "[DOCUMENTS ACTIFS DE CONVERSATION]"
LANE_FOOTER = "[/DOCUMENTS ACTIFS DE CONVERSATION]"
INJECTED_HEADER = "[DOCUMENTS ACTIFS INJECTES]"
INJECTED_FOOTER = "[/DOCUMENTS ACTIFS INJECTES]"
NOT_INJECTED_HEADER = "[DOCUMENTS ACTIFS NON INJECTES]"
NOT_INJECTED_FOOTER = "[/DOCUMENTS ACTIFS NON INJECTES]"


@dataclass(frozen=True)
class ActiveDocumentPromptDecision:
    document_id: str
    filename: str
    media_type: str
    source_extension: str
    byte_size: int
    text_chars: int
    token_estimate: int
    text_sha256_12: str
    injected: bool
    reason_code: str = ""
    text_content: str = ""


@dataclass(frozen=True)
class ActiveDocumentPromptLane:
    message: dict[str, str] | None
    decisions: tuple[ActiveDocumentPromptDecision, ...]

    @property
    def injected_count(self) -> int:
        return sum(1 for decision in self.decisions if decision.injected)

    @property
    def not_injected_count(self) -> int:
        return sum(1 for decision in self.decisions if not decision.injected)


def build_active_document_prompt_lane(
    active_documents: Sequence[Mapping[str, Any]] | None,
    *,
    model: str,
    base_messages: Sequence[Mapping[str, Any]],
    count_tokens_func: Callable[[list[dict[str, Any]], str], int],
    max_tokens: int,
) -> ActiveDocumentPromptLane:
    documents = _stable_documents(active_documents)
    if not documents:
        return ActiveDocumentPromptLane(message=None, decisions=())

    injected: list[ActiveDocumentPromptDecision] = []
    not_injected: list[ActiveDocumentPromptDecision] = []

    for document in documents:
        decision = _decision_from_document(document, injected=False)
        if not decision.text_content:
            not_injected.append(_replace_decision(decision, reason_code=REASON_EMPTY))
            continue

        candidate_decision = _replace_decision(decision, injected=True, reason_code="")
        candidate_message = _message_from_decisions([*injected, candidate_decision], not_injected)
        candidate_messages = [dict(message) for message in base_messages]
        candidate_messages.append(candidate_message)
        try:
            estimated_tokens = int(count_tokens_func(candidate_messages, model))
        except Exception:
            estimated_tokens = max_tokens + 1 if max_tokens > 0 else 0

        if max_tokens > 0 and estimated_tokens > max_tokens:
            not_injected.append(_replace_decision(decision, reason_code=REASON_TOO_LARGE))
            continue
        injected.append(candidate_decision)

    message = _message_from_decisions(injected, not_injected)
    return ActiveDocumentPromptLane(
        message=message,
        decisions=tuple([*injected, *not_injected]),
    )


def inject_active_document_prompt_lane(
    prompt_messages: list[dict[str, Any]],
    active_documents: Sequence[Mapping[str, Any]] | None,
    *,
    model: str,
    count_tokens_func: Callable[[list[dict[str, Any]], str], int],
    max_tokens: int,
) -> ActiveDocumentPromptLane:
    lane = build_active_document_prompt_lane(
        active_documents,
        model=model,
        base_messages=prompt_messages,
        count_tokens_func=count_tokens_func,
        max_tokens=max_tokens,
    )
    if lane.message is None:
        return lane
    prompt_messages.insert(_first_dialogue_index(prompt_messages), lane.message)
    return lane


def _stable_documents(active_documents: Sequence[Mapping[str, Any]] | None) -> list[Mapping[str, Any]]:
    docs = [doc for doc in (active_documents or []) if isinstance(doc, Mapping)]
    return sorted(
        docs,
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("filename") or ""),
            str(item.get("document_id") or ""),
        ),
    )


def _first_dialogue_index(prompt_messages: Sequence[Mapping[str, Any]]) -> int:
    for index, message in enumerate(prompt_messages):
        if message.get("role") in {"user", "assistant"}:
            return index
    return len(prompt_messages)


def _decision_from_document(document: Mapping[str, Any], *, injected: bool) -> ActiveDocumentPromptDecision:
    return ActiveDocumentPromptDecision(
        document_id=_text(document.get("document_id")),
        filename=_text(document.get("filename")) or "document",
        media_type=_text(document.get("media_type")),
        source_extension=_text(document.get("source_extension")),
        byte_size=_safe_int(document.get("byte_size") if "byte_size" in document else document.get("bytes")),
        text_chars=_safe_int(document.get("text_chars") if "text_chars" in document else document.get("chars")),
        token_estimate=_safe_int(document.get("token_estimate")),
        text_sha256_12=_text(document.get("text_sha256_12") if "text_sha256_12" in document else document.get("sha256_12")),
        injected=injected,
        text_content=str(document.get("text_content") or ""),
    )


def _replace_decision(
    decision: ActiveDocumentPromptDecision,
    *,
    injected: bool | None = None,
    reason_code: str | None = None,
) -> ActiveDocumentPromptDecision:
    return ActiveDocumentPromptDecision(
        document_id=decision.document_id,
        filename=decision.filename,
        media_type=decision.media_type,
        source_extension=decision.source_extension,
        byte_size=decision.byte_size,
        text_chars=decision.text_chars,
        token_estimate=decision.token_estimate,
        text_sha256_12=decision.text_sha256_12,
        injected=decision.injected if injected is None else bool(injected),
        reason_code=decision.reason_code if reason_code is None else reason_code,
        text_content=decision.text_content,
    )


def _message_from_decisions(
    injected: Sequence[ActiveDocumentPromptDecision],
    not_injected: Sequence[ActiveDocumentPromptDecision],
) -> dict[str, str]:
    lines: list[str] = [
        LANE_HEADER,
        "Contrat d'interpretation:",
        "- Un document actif de conversation est un fichier fourni volontairement par l'utilisateur dans cette conversation.",
        "- Quand il est injecte ci-dessous, il fait partie du contexte de travail direct du tour courant.",
        "- Cette lane est distincte de la memoire, des resumes, du Web, de l'identite et du jugement hermeneutique.",
        "- Si l'utilisateur demande de travailler sur le document, le fichier, le PDF ou le texte joint, utilise les documents actifs injectes ci-dessous.",
        "- Un document liste comme non injecte est connu mais son contenu n'a pas ete envoye dans ce tour; ne pretends jamais l'avoir lu.",
    ]

    if injected:
        lines.append(INJECTED_HEADER)
        for index, decision in enumerate(injected, start=1):
            lines.extend(_injected_document_lines(decision, index=index))
        lines.append(INJECTED_FOOTER)

    if not_injected:
        lines.append(NOT_INJECTED_HEADER)
        for index, decision in enumerate(not_injected, start=1):
            lines.append(_not_injected_document_line(decision, index=index))
        lines.append(NOT_INJECTED_FOOTER)

    lines.append(LANE_FOOTER)
    return {"role": "system", "content": "\n".join(lines)}


def _injected_document_lines(decision: ActiveDocumentPromptDecision, *, index: int) -> list[str]:
    return [
        f"Document actif injecte {index}:",
        f"- filename: {decision.filename}",
        f"- media_type: {decision.media_type or 'unknown'}",
        f"- source_extension: {decision.source_extension or 'unknown'}",
        f"- byte_size: {decision.byte_size}",
        f"- text_chars: {decision.text_chars}",
        f"- token_estimate: {decision.token_estimate}",
        f"- text_sha256_12: {decision.text_sha256_12 or 'none'}",
        "Contenu complet du document actif:",
        decision.text_content,
        "Fin du document actif.",
    ]


def _not_injected_document_line(decision: ActiveDocumentPromptDecision, *, index: int) -> str:
    return (
        f"- document_actif_non_injecte {index}: filename={decision.filename}; "
        f"media_type={decision.media_type or 'unknown'}; "
        f"source_extension={decision.source_extension or 'unknown'}; "
        f"byte_size={decision.byte_size}; text_chars={decision.text_chars}; "
        f"token_estimate={decision.token_estimate}; "
        f"text_sha256_12={decision.text_sha256_12 or 'none'}; "
        f"reason_code={decision.reason_code or REASON_TOO_LARGE}"
    )


def _text(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
