from __future__ import annotations

from dataclasses import dataclass, field
import logging
import time
from typing import Any

import requests
from urllib3 import exceptions as urllib3_exceptions

import config
from core import llm_client


logger = logging.getLogger("frida.dialogue_tts")

DIALOGUE_TTS_MODEL = "microsoft/mai-voice-2-flash"
DIALOGUE_TTS_VOICE = "fr-FR-Soleil:MAI-Voice-2"
DIALOGUE_TTS_RESPONSE_FORMAT = "mp3"
DIALOGUE_TTS_CONTENT_TYPE = "audio/mpeg"

# OpenRouter does not publish usable input or response-size limits for this
# endpoint. These local ceilings bound the inactive FridaDev boundary without
# truncating accepted text or reading an unbounded provider response.
MAX_DIALOGUE_TTS_TEXT_CHARS = 16_000
MAX_DIALOGUE_TTS_AUDIO_BYTES = 16 * 1024 * 1024
RESPONSE_READ_CHUNK_BYTES = 64 * 1024

REASON_OK = "dialogue_tts_ok"
REASON_TEXT_TYPE_INVALID = "dialogue_tts_text_type_invalid"
REASON_TEXT_EMPTY = "dialogue_tts_text_empty"
REASON_TEXT_TOO_LARGE = "dialogue_tts_text_too_large"
REASON_PROVIDER_NOT_CONFIGURED = "dialogue_tts_provider_not_configured"
REASON_PROVIDER_TIMEOUT = "dialogue_tts_provider_timeout"
REASON_PROVIDER_TRANSPORT_ERROR = "dialogue_tts_provider_transport_error"
REASON_PROVIDER_AUTH_ERROR = "dialogue_tts_provider_auth_error"
REASON_PROVIDER_RATE_LIMITED = "dialogue_tts_provider_rate_limited"
REASON_PROVIDER_UNAVAILABLE = "dialogue_tts_provider_unavailable"
REASON_PROVIDER_CONTRACT_REJECTED = "dialogue_tts_provider_contract_rejected"
REASON_PROVIDER_INVALID_MEDIA = "dialogue_tts_provider_invalid_media"
REASON_PROVIDER_AUDIO_EMPTY = "dialogue_tts_provider_audio_empty"
REASON_PROVIDER_AUDIO_TOO_LARGE = "dialogue_tts_provider_audio_too_large"
REASON_PROVIDER_AUDIO_TRUNCATED = "dialogue_tts_provider_audio_truncated"
REASON_PROVIDER_AUDIO_UNREADABLE = "dialogue_tts_provider_audio_unreadable"

_DEFAULT_TIMEOUT_S = 60


@dataclass(frozen=True)
class DialogueTtsResult:
    ok: bool
    audio_bytes: bytes = field(default=b"", repr=False)
    content_type: str = ""
    reason_code: str = ""
    http_status: int = 503
    duration_ms: int = 0

    def to_payload(self) -> dict[str, Any]:
        return {
            "ok": bool(self.ok),
            "reason_code": self.reason_code,
            "duration_ms": self.duration_ms,
        }


def failure_result(
    reason_code: str,
    *,
    http_status: int = 422,
    duration_ms: int = 0,
) -> DialogueTtsResult:
    return DialogueTtsResult(
        ok=False,
        reason_code=reason_code,
        http_status=http_status,
        duration_ms=max(0, int(duration_ms)),
    )


def synthesize_dialogue_speech(
    text: Any,
    *,
    requests_module: Any = requests,
    config_module: Any = config,
    llm_module: Any = llm_client,
    logger_obj: Any = logger,
    monotonic: Any = time.monotonic,
) -> DialogueTtsResult:
    started_at = monotonic()
    text_chars = len(text) if isinstance(text, str) else 0
    if not isinstance(text, str):
        return _failure(
            REASON_TEXT_TYPE_INVALID,
            started_at=started_at,
            monotonic=monotonic,
            text_chars=text_chars,
            audio_bytes=0,
            logger_obj=logger_obj,
        )
    if not text.strip():
        return _failure(
            REASON_TEXT_EMPTY,
            started_at=started_at,
            monotonic=monotonic,
            text_chars=text_chars,
            audio_bytes=0,
            logger_obj=logger_obj,
        )
    if text_chars > MAX_DIALOGUE_TTS_TEXT_CHARS:
        return _failure(
            REASON_TEXT_TOO_LARGE,
            started_at=started_at,
            monotonic=monotonic,
            text_chars=text_chars,
            audio_bytes=0,
            logger_obj=logger_obj,
        )

    try:
        provider_url = str(llm_module.or_audio_speech_url() or "").strip()
        provider_headers = llm_module.or_headers_custom(
            caller="dialogue_tts",
            referer=str(
                getattr(config_module, "OR_REFERER_DIALOGUE_TTS", "") or ""
            ).strip(),
            title=str(
                getattr(config_module, "OR_TITLE_DIALOGUE_TTS", "") or ""
            ).strip(),
        )
        provider_headers = llm_module.strip_internal_provider_headers(
            provider_headers
        )
        authorization = str(provider_headers.get("Authorization") or "").strip()
        if not provider_url or authorization in {"", "Bearer"}:
            raise RuntimeError("provider configuration unavailable")
    except Exception:
        return _failure(
            REASON_PROVIDER_NOT_CONFIGURED,
            started_at=started_at,
            monotonic=monotonic,
            text_chars=text_chars,
            audio_bytes=0,
            logger_obj=logger_obj,
            http_status=503,
        )

    timeout_s = _timeout_s(config_module)
    timeout_class, request_error_class = _request_error_classes(requests_module)
    try:
        response = requests_module.post(
            provider_url,
            json={
                "model": DIALOGUE_TTS_MODEL,
                "input": text,
                "voice": DIALOGUE_TTS_VOICE,
                "response_format": DIALOGUE_TTS_RESPONSE_FORMAT,
            },
            headers=provider_headers,
            timeout=timeout_s,
            stream=True,
        )
    except Exception as exc:
        reason_code = (
            REASON_PROVIDER_TIMEOUT
            if timeout_class is not None and isinstance(exc, timeout_class)
            else REASON_PROVIDER_TRANSPORT_ERROR
        )
        return _failure(
            reason_code,
            started_at=started_at,
            monotonic=monotonic,
            text_chars=text_chars,
            audio_bytes=0,
            logger_obj=logger_obj,
            http_status=503,
        )

    status_code = _status_code(response)
    try:
        if status_code != 200:
            reason_code, http_status = _provider_status_failure(status_code)
            return _failure(
                reason_code,
                started_at=started_at,
                monotonic=monotonic,
                text_chars=text_chars,
                audio_bytes=0,
                logger_obj=logger_obj,
                http_status=http_status,
                provider_status=status_code,
            )

        if _base_media_type(response) != DIALOGUE_TTS_CONTENT_TYPE:
            return _failure(
                REASON_PROVIDER_INVALID_MEDIA,
                started_at=started_at,
                monotonic=monotonic,
                text_chars=text_chars,
                audio_bytes=0,
                logger_obj=logger_obj,
                http_status=502,
                provider_status=status_code,
            )

        declared_length = _content_length(response)
        if (
            declared_length is not None
            and declared_length > MAX_DIALOGUE_TTS_AUDIO_BYTES
        ):
            return _failure(
                REASON_PROVIDER_AUDIO_TOO_LARGE,
                started_at=started_at,
                monotonic=monotonic,
                text_chars=text_chars,
                audio_bytes=0,
                logger_obj=logger_obj,
                http_status=502,
                provider_status=status_code,
            )

        try:
            audio_bytes = _read_bounded_response(response)
        except _ProviderAudioTooLarge as exc:
            return _failure(
                REASON_PROVIDER_AUDIO_TOO_LARGE,
                started_at=started_at,
                monotonic=monotonic,
                text_chars=text_chars,
                audio_bytes=exc.observed_bytes,
                logger_obj=logger_obj,
                http_status=502,
                provider_status=status_code,
            )
        except Exception as exc:
            if (
                timeout_class is not None and isinstance(exc, timeout_class)
            ) or isinstance(exc, urllib3_exceptions.ReadTimeoutError):
                reason_code = REASON_PROVIDER_TIMEOUT
                http_status = 503
            elif (
                request_error_class is not None
                and isinstance(exc, request_error_class)
            ) or isinstance(exc, urllib3_exceptions.ProtocolError):
                reason_code = REASON_PROVIDER_TRANSPORT_ERROR
                http_status = 503
            else:
                reason_code = REASON_PROVIDER_AUDIO_UNREADABLE
                http_status = 502
            return _failure(
                reason_code,
                started_at=started_at,
                monotonic=monotonic,
                text_chars=text_chars,
                audio_bytes=0,
                logger_obj=logger_obj,
                http_status=http_status,
                provider_status=status_code,
            )

        audio_size = len(audio_bytes)
        if declared_length is not None and audio_size != declared_length:
            return _failure(
                REASON_PROVIDER_AUDIO_TRUNCATED,
                started_at=started_at,
                monotonic=monotonic,
                text_chars=text_chars,
                audio_bytes=audio_size,
                logger_obj=logger_obj,
                http_status=502,
                provider_status=status_code,
            )
        if not audio_bytes:
            return _failure(
                REASON_PROVIDER_AUDIO_EMPTY,
                started_at=started_at,
                monotonic=monotonic,
                text_chars=text_chars,
                audio_bytes=0,
                logger_obj=logger_obj,
                http_status=502,
                provider_status=status_code,
            )

        duration_ms = _duration_ms(started_at, monotonic)
        _log(
            logger_obj,
            "info",
            (
                "dialogue_tts_completed status=200 reason_code=%s duration_ms=%s "
                "input_chars=%s audio_bytes=%s provider_status=%s"
            ),
            REASON_OK,
            duration_ms,
            text_chars,
            audio_size,
            status_code,
        )
        return DialogueTtsResult(
            ok=True,
            audio_bytes=audio_bytes,
            content_type=DIALOGUE_TTS_CONTENT_TYPE,
            reason_code=REASON_OK,
            http_status=200,
            duration_ms=duration_ms,
        )
    finally:
        _close_response(response)


class _ProviderAudioTooLarge(Exception):
    def __init__(self, observed_bytes: int) -> None:
        super().__init__("provider audio exceeds local response limit")
        self.observed_bytes = max(0, int(observed_bytes))


def _read_bounded_response(response: Any) -> bytes:
    chunks: list[bytes] = []
    observed_bytes = 0
    observed_limit = MAX_DIALOGUE_TTS_AUDIO_BYTES + 1
    raw = response.raw
    while observed_bytes < observed_limit:
        read_size = min(
            RESPONSE_READ_CHUNK_BYTES,
            observed_limit - observed_bytes,
        )
        chunk = bytes(raw.read(read_size) or b"")
        if not chunk:
            break
        chunks.append(chunk)
        observed_bytes += len(chunk)
    if observed_bytes > MAX_DIALOGUE_TTS_AUDIO_BYTES:
        raise _ProviderAudioTooLarge(observed_bytes)
    return b"".join(chunks)


def _failure(
    reason_code: str,
    *,
    started_at: float,
    monotonic: Any,
    text_chars: int,
    audio_bytes: int,
    logger_obj: Any,
    http_status: int = 422,
    provider_status: int | None = None,
) -> DialogueTtsResult:
    duration_ms = _duration_ms(started_at, monotonic)
    _log(
        logger_obj,
        "warning",
        (
            "dialogue_tts_failed status=%s reason_code=%s duration_ms=%s "
            "input_chars=%s audio_bytes=%s provider_status=%s"
        ),
        http_status,
        reason_code,
        duration_ms,
        max(0, int(text_chars)),
        max(0, int(audio_bytes)),
        provider_status if provider_status is not None else "none",
    )
    return failure_result(
        reason_code,
        http_status=http_status,
        duration_ms=duration_ms,
    )


def _duration_ms(started_at: float, monotonic: Any) -> int:
    return max(0, int(round((monotonic() - started_at) * 1000)))


def _timeout_s(config_module: Any) -> int:
    try:
        timeout_s = int(
            getattr(config_module, "DIALOGUE_TTS_TIMEOUT_S", _DEFAULT_TIMEOUT_S)
        )
    except (TypeError, ValueError):
        timeout_s = _DEFAULT_TIMEOUT_S
    return max(1, timeout_s)


def _request_error_classes(
    requests_module: Any,
) -> tuple[type[Any] | None, type[Any] | None]:
    exceptions = getattr(requests_module, "exceptions", None)
    return (
        getattr(exceptions, "Timeout", None),
        getattr(exceptions, "RequestException", None),
    )


def _status_code(response: Any) -> int:
    try:
        return int(getattr(response, "status_code", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _provider_status_failure(status_code: int) -> tuple[str, int]:
    if status_code in {400, 404, 422}:
        return REASON_PROVIDER_CONTRACT_REJECTED, 502
    if status_code in {401, 403}:
        return REASON_PROVIDER_AUTH_ERROR, 503
    if status_code == 429:
        return REASON_PROVIDER_RATE_LIMITED, 503
    if status_code == 524:
        return REASON_PROVIDER_TIMEOUT, 503
    return REASON_PROVIDER_UNAVAILABLE, 503


def _base_media_type(response: Any) -> str:
    headers = getattr(response, "headers", {})
    value = headers.get("Content-Type", "") if hasattr(headers, "get") else ""
    return str(value or "").split(";", 1)[0].strip().lower()


def _content_length(response: Any) -> int | None:
    headers = getattr(response, "headers", {})
    value = headers.get("Content-Length") if hasattr(headers, "get") else None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _close_response(response: Any) -> None:
    close = getattr(response, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            pass


def _log(logger_obj: Any, level: str, message: str, *args: Any) -> None:
    log_method = getattr(logger_obj, level, None)
    if callable(log_method):
        log_method(message, *args)
