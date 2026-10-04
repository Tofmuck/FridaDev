"""Complete-payload admission using the *existing* shared token estimate.

No provider count claim, framing margin, tokenizer variant or normal-chat change.
Transport owns an immutable request body; caller/counter mutation cannot change it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Callable, Mapping, Any

from . import llm_client
from .document_canonical import CANONICAL_INSTRUCTIONS
from .document_workshop_contract import (
    DOCUMENT_CONTEXT_TOKENS, DOCUMENT_MODEL, DOCUMENT_OUTPUT_TOKENS,
    DocumentWorkshopError,
)

_PAYLOAD_FIELDS = {
    "model", "messages", "temperature", "top_p", "max_tokens", "stop",
    "reasoning", "stream", "stream_options", "metadata", "trace", "response_format",
}


def _snapshot(value: object) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise DocumentWorkshopError("document_payload_invalid") from None


def _messages(value: object) -> list[dict[str, str]]:
    if type(value) is not list or not value:
        raise DocumentWorkshopError("document_payload_invalid")
    for message in value:
        if (type(message) is not dict or set(message) != {"role", "content"}
                or type(message["role"]) is not str
                or message["role"] not in {"system", "user", "assistant"}
                or type(message["content"]) is not str):
            raise DocumentWorkshopError("document_payload_invalid")
    return json.loads(_snapshot(value))


@dataclass(frozen=True)
class DocumentAdmission:
    estimated_input_tokens: int
    estimated_total_tokens: int


@dataclass(frozen=True, repr=False)
class PreparedDocumentCall:
    body: bytes = field(repr=False)
    headers: tuple[tuple[str, str], ...] = field(repr=False)
    url: str = field(repr=False)
    stream: bool
    admission: DocumentAdmission


def prepare_document_call(
    messages: list[dict[str, str]],
    *,
    count_tokens_func: Callable[[list[dict[str, str]], str], int],
    temperature: float = 0.7,
    top_p: float = 1.0,
    stream: bool = True,
    llm_module: Any = llm_client,
    progress: Any = None,
) -> PreparedDocumentCall:
    """The caller supplies final prompt/dialogue/whole sources/context/metadata.

    This boundary appends its canonical instructions before counting. The sole
    supported model-consumed field outside messages is response_format, represented
    explicitly as one estimation-only system message using the *same* callable.
    Attribution metadata/trace, sampling/stop controls and HTTP headers are not
    prompt text. No source selection, truncation or chat-window reduction occurs.
    """
    if progress is not None:
        progress.check()
    final_messages = _messages(messages)
    final_messages.append({"role": "system", "content": CANONICAL_INSTRUCTIONS})
    payload = llm_module.build_payload(final_messages, temperature, top_p, DOCUMENT_OUTPUT_TOKENS, stream=stream)
    if type(payload) is not dict or set(payload) - _PAYLOAD_FIELDS:
        raise DocumentWorkshopError("document_payload_invalid")
    if payload.get("model") != DOCUMENT_MODEL:
        raise DocumentWorkshopError("document_model_outside_contract")
    if type(payload.get("max_tokens")) is not int or payload["max_tokens"] != DOCUMENT_OUTPUT_TOKENS:
        raise DocumentWorkshopError("document_payload_invalid")
    reasoning = payload.get("reasoning")
    if not isinstance(reasoning, Mapping) or reasoning.get("exclude") is not True:
        raise DocumentWorkshopError("document_payload_invalid")
    # Prevent OpenRouter provider failover as well as local retries. This is
    # request-local and does not alter settings or any normal caller's payload.
    payload["provider"] = {"allow_fallbacks": False}
    payload_json = _snapshot(payload)
    try:
        body = payload_json.encode("utf-8")
    except UnicodeError:
        raise DocumentWorkshopError("document_payload_invalid") from None
    frozen_payload = json.loads(payload_json)
    estimation_messages = _messages(frozen_payload.get("messages"))
    if "response_format" in frozen_payload:
        estimation_messages.append({"role": "system", "content": _snapshot(frozen_payload["response_format"])})
    measured_snapshot = _snapshot(estimation_messages)
    if progress is not None:
        progress.complete_step("payload_prepared")
    try:
        if not callable(count_tokens_func):
            raise TypeError
        estimated = count_tokens_func(estimation_messages, DOCUMENT_MODEL)
    except Exception:
        raise DocumentWorkshopError("document_estimation_unavailable") from None
    if _snapshot(estimation_messages) != measured_snapshot:
        raise DocumentWorkshopError("document_estimation_input_mutated")
    if type(estimated) is not int or estimated <= 0:
        raise DocumentWorkshopError("document_estimation_unavailable")
    estimated_total = estimated + DOCUMENT_OUTPUT_TOKENS
    if estimated_total > DOCUMENT_CONTEXT_TOKENS:
        raise DocumentWorkshopError("document_estimated_context_limit")
    if progress is not None:
        progress.complete_step("admitted")
    # Resolve only through existing server boundaries, after local admission.
    # Internal attribution headers are stripped exactly as at the HTTP boundary.
    headers = llm_module.strip_internal_provider_headers(llm_module.or_headers(caller="llm"))
    url = llm_module.or_chat_completions_url()
    if progress is not None:
        progress.check()
    return PreparedDocumentCall(body, tuple(headers.items()), url, stream, DocumentAdmission(estimated, estimated_total))
