"""Inactive M0 single-exchange boundary, consuming injected provider transport.

No HTTP implementation is installed or selected here. The owned transport must
send the frozen body verbatim, have no retry, and close/abort promptly, including
an outstanding send/read. M4 must prove that contract for its real adapter.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import AsyncIterator, Protocol, Any, Callable

from . import llm_client, main_llm_reasoning
from .document_canonical import ValidatedCanonical, read_canonical_json, strict_json_loads
from .document_workshop_admission import PreparedDocumentCall, prepare_document_call
from .document_workshop_contract import (
    DOCUMENT_CONTEXT_TOKENS, DOCUMENT_OUTPUT_TOKENS, MAX_CANONICAL_JSON_BYTES,
    DocumentWorkshopError,
)
from .document_workshop_progress import DocumentPreparation


class DocumentTransport(Protocol):
    async def send(self, prepared: PreparedDocumentCall) -> int: ...
    async def read_json(self) -> object: ...
    def iter_lines(self) -> AsyncIterator[str]: ...
    def close(self) -> None: ...


@dataclass(frozen=True)
class ProviderUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    reasoning_tokens: int | None = None


@dataclass(frozen=True, repr=False)
class DocumentProviderResult:
    canonical: ValidatedCanonical = field(repr=False)
    finish_reason: str
    model: str
    provider_usage: ProviderUsage | None
    state: str = "complete"


@dataclass
class _Evidence:
    model: str | None = None
    finish_reason: str | None = None
    usage: ProviderUsage | None = None


def _error(payload: dict) -> None:
    if payload.get("error") is not None:
        error = payload["error"]
        code = error.get("code") if type(error) is dict else None
        reason = "document_provider_context_limit" if code in ("context_length_exceeded", "context_window_exceeded", 413) else "document_provider_error"
        raise DocumentWorkshopError(reason)


def _merge_metadata(payload: dict, evidence: _Evidence) -> None:
    metadata = llm_client.extract_openrouter_provider_metadata(payload)
    if "model" in payload:
        model = metadata.get("provider_model")
        if not main_llm_reasoning.model_supports_reasoning_effort(model) or (evidence.model and evidence.model != model):
            raise DocumentWorkshopError("document_provider_model_invalid")
        evidence.model = model
    usage = payload.get("usage")
    if usage is None:
        return
    if type(usage) is not dict:
        raise DocumentWorkshopError("document_provider_protocol_invalid")
    values = {}
    for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
        if name in usage:
            if type(usage[name]) is not int or usage[name] < 0:
                raise DocumentWorkshopError("document_provider_protocol_invalid")
            values[name] = metadata.get("provider_" + name)
    details = usage.get("completion_tokens_details")
    if type(details) is dict and "reasoning_tokens" in details:
        value = details["reasoning_tokens"]
        if type(value) is not int or value < 0:
            raise DocumentWorkshopError("document_provider_protocol_invalid")
        values["reasoning_tokens"] = value
    if values:
        previous = evidence.usage or ProviderUsage()
        evidence.usage = ProviderUsage(**{name: values.get(name, getattr(previous, name)) for name in ProviderUsage.__dataclass_fields__})
        if (evidence.usage.completion_tokens or 0) > DOCUMENT_OUTPUT_TOKENS or (evidence.usage.reasoning_tokens or 0) > DOCUMENT_OUTPUT_TOKENS:
            raise DocumentWorkshopError("document_provider_output_limit")
        # Known partial counters can prove an overflow even when total is
        # absent or inconsistent. Reasoning is part of completion, not added
        # again; its count is only a lower bound if completion is missing.
        completion_bound = max(evidence.usage.completion_tokens or 0,
                               evidence.usage.reasoning_tokens or 0)
        context_bound = (evidence.usage.prompt_tokens or 0) + completion_bound
        if max(evidence.usage.total_tokens or 0, context_bound) > DOCUMENT_CONTEXT_TOKENS:
            raise DocumentWorkshopError("document_provider_context_limit")


def _choice(payload: dict) -> dict | None:
    choices = payload.get("choices")
    if type(choices) is not list or len(choices) > 1:
        raise DocumentWorkshopError("document_provider_protocol_invalid")
    if not choices:
        return None
    choice = choices[0]
    if type(choice) is not dict or ("index" in choice and (type(choice["index"]) is not int or choice["index"] != 0)):
        raise DocumentWorkshopError("document_provider_protocol_invalid")
    return choice


def _content(message: dict) -> str:
    if message.get("refusal"):
        raise DocumentWorkshopError("document_provider_refused")
    if message.get("tool_calls") or message.get("function_call"):
        raise DocumentWorkshopError("document_provider_incomplete")
    content = message.get("content")
    if content is None:
        return ""
    if type(content) is not str:
        raise DocumentWorkshopError("document_provider_protocol_invalid")
    return content


def _finish(reason: object, evidence: _Evidence) -> None:
    if reason is None:
        return
    if reason == "length":
        raise DocumentWorkshopError("document_provider_length")
    if reason == "content_filter":
        raise DocumentWorkshopError("document_provider_refused")
    if reason == "error":
        raise DocumentWorkshopError("document_provider_error")
    if reason != "stop" or evidence.finish_reason is not None:
        raise DocumentWorkshopError("document_provider_incomplete")
    evidence.finish_reason = reason


def _validated_result(content: str, evidence: _Evidence, progress: DocumentPreparation) -> DocumentProviderResult:
    progress.check()
    if evidence.finish_reason != "stop":
        raise DocumentWorkshopError("document_provider_incomplete")
    if not evidence.model:
        raise DocumentWorkshopError("document_provider_model_invalid")
    if not content:
        raise DocumentWorkshopError("document_provider_empty")
    progress.complete_step("provider_finished")
    canonical = read_canonical_json(content)
    progress.complete_step("canonical_validated")
    return DocumentProviderResult(canonical, evidence.finish_reason, evidence.model, evidence.usage)


async def _sse_events(transport: DocumentTransport, progress: DocumentPreparation) -> AsyncIterator[str]:
    lines: list[str] = []
    frame_bytes = 0
    async for line in transport.iter_lines():
        # Both a per-frame check and a separate supervisor: uninterrupted
        # keepalives cannot starve the alarm, and a blocked read cannot defer it.
        await asyncio.sleep(0)
        progress.check()
        if type(line) is not str:
            raise DocumentWorkshopError("document_provider_protocol_invalid")
        if line == "":
            if lines:
                yield "\n".join(lines)
            lines = []
            frame_bytes = 0
        elif line.startswith("data:"):
            value = line[5:]
            if value.startswith(" "):
                value = value[1:]
            frame_bytes += len(value.encode("utf-8")) + 1
            if frame_bytes > MAX_CANONICAL_JSON_BYTES:
                raise DocumentWorkshopError("document_json_envelope_limit")
            lines.append(value)
        # Comments, event/id/retry and empty frames are control, never progress.
    if lines:
        yield "\n".join(lines)


async def _read_exchange(prepared: PreparedDocumentCall, transport: DocumentTransport,
                         progress: DocumentPreparation) -> DocumentProviderResult:
    progress.check()
    status = await transport.send(prepared)
    progress.check()
    if type(status) is not int or not 200 <= status < 300:
        raise DocumentWorkshopError("document_provider_context_limit" if status == 413 else "document_provider_error")
    evidence = _Evidence()
    if not prepared.stream:
        payload = await transport.read_json()
        progress.check()
        if type(payload) is not dict:
            raise DocumentWorkshopError("document_provider_protocol_invalid")
        payload = llm_client.strip_provider_reasoning_fields(payload)
        _error(payload)
        _merge_metadata(payload, evidence)
        choice = _choice(payload)
        if choice is None:
            raise DocumentWorkshopError("document_provider_incomplete")
        _finish(choice.get("finish_reason"), evidence)
        message = choice.get("message")
        if type(message) is not dict:
            raise DocumentWorkshopError("document_provider_protocol_invalid")
        content = _content(message)
        if content:
            progress._receive_provider_content(content)
        return _validated_result(content, evidence, progress)
    fragments: list[str] = []
    content_bytes = 0
    async for data in _sse_events(transport, progress):
        if data == "[DONE]":
            return _validated_result("".join(fragments), evidence, progress)
        try:
            payload = strict_json_loads(data)
        except DocumentWorkshopError:
            raise DocumentWorkshopError("document_provider_protocol_invalid") from None
        if type(payload) is not dict:
            raise DocumentWorkshopError("document_provider_protocol_invalid")
        payload = llm_client.strip_provider_reasoning_fields(payload)
        _error(payload)
        _merge_metadata(payload, evidence)
        choice = _choice(payload)
        if choice is None:
            continue
        delta = choice.get("delta")
        if type(delta) is not dict:
            raise DocumentWorkshopError("document_provider_protocol_invalid")
        content = _content(delta)
        if content:
            if evidence.finish_reason is not None:
                raise DocumentWorkshopError("document_provider_incomplete")
            content_bytes += len(content.encode("utf-8"))
            if content_bytes > MAX_CANONICAL_JSON_BYTES:
                raise DocumentWorkshopError("document_json_envelope_limit")
            fragments.append(content)
            progress._receive_provider_content(content)
        _finish(choice.get("finish_reason"), evidence)
    raise DocumentWorkshopError("document_provider_incomplete")


def _consume_task(task: asyncio.Task) -> None:
    # A cancellation-resistant late read can finish after its caller has failed.
    # Consume its outcome without publishing, retrying or logging raw exceptions.
    if not task.cancelled():
        task.exception()


async def prepare_and_read_document(
    messages: list[dict[str, str]], *, transport: DocumentTransport,
    count_tokens_func: Callable, progress: DocumentPreparation | None = None,
    temperature: float = 0.7, top_p: float = 1.0, stream: bool = True,
    llm_module: Any = llm_client,
) -> DocumentProviderResult:
    progress = progress if progress is not None else DocumentPreparation()
    exchange = watchdog = None
    try:
        prepared = prepare_document_call(messages, count_tokens_func=count_tokens_func,
                                         temperature=temperature, top_p=top_p, stream=stream,
                                         llm_module=llm_module, progress=progress)
        progress.begin_exchange()
        exchange = asyncio.create_task(_read_exchange(prepared, transport, progress))
        watchdog = asyncio.create_task(progress.watch_inactivity())
        done, _ = await asyncio.wait((exchange, watchdog), return_when=asyncio.FIRST_COMPLETED)
        if watchdog in done:
            watchdog.result()
        result = exchange.result()
        progress.check()
    except DocumentWorkshopError as error:
        progress.fail(error.reason_code)
        raise
    except asyncio.CancelledError:
        progress.cancel()
        raise
    except Exception:
        progress.fail("document_provider_error")
        raise DocumentWorkshopError("document_provider_error") from None
    finally:
        try:
            transport.close()
        except Exception:
            progress.fail("document_transport_close_failed")
            raise DocumentWorkshopError("document_transport_close_failed") from None
        finally:
            if exchange is not None:
                exchange.cancel()
                exchange.add_done_callback(_consume_task)
            if watchdog is not None:
                watchdog.cancel()
                await asyncio.gather(watchdog, return_exceptions=True)
    # Only after transport release, and only for this still-valid preparation.
    progress.succeed()
    return result
