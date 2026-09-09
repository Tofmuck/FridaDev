from __future__ import annotations

from dataclasses import dataclass, field
import logging
import time
from typing import Any, Mapping

import requests

import config
from core import llm_client


logger = logging.getLogger("frida.dialogue_stt")

DIALOGUE_STT_MODEL = "microsoft/mai-transcribe-2"
DIALOGUE_STT_LANGUAGE = "fr"
DIALOGUE_STT_TEMPERATURE = "0"
DIALOGUE_STT_RESPONSE_FORMAT = "json"

# OpenRouter documents a 25 MB multipart upload ceiling. The application keeps
# one decimal megabyte for the multipart envelope and rejects both boundaries
# before the provider call.
MAX_DIALOGUE_STT_FILE_BYTES = 24_000_000
MAX_DIALOGUE_STT_REQUEST_BYTES = 25_000_000
UPLOAD_READ_CHUNK_BYTES = 64 * 1024

SUPPORTED_AUDIO_MIME_EXTENSIONS = {
    "audio/wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/flac": ".flac",
    "audio/mp4": ".m4a",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
    "audio/aac": ".aac",
}

REASON_OK = "dialogue_stt_ok"
REASON_AUDIO_EMPTY = "audio_empty"
REASON_AUDIO_TYPE_UNSUPPORTED = "audio_type_unsupported"
REASON_AUDIO_FILE_TOO_LARGE = "audio_file_too_large"
REASON_AUDIO_REQUEST_TOO_LARGE = "audio_request_too_large"
REASON_AUDIO_REQUEST_SIZE_REQUIRED = "audio_request_size_required"
REASON_PROVIDER_NOT_CONFIGURED = "provider_not_configured"
REASON_PROVIDER_TIMEOUT = "provider_timeout"
REASON_PROVIDER_TRANSPORT_ERROR = "provider_transport_error"
REASON_PROVIDER_AUTH_ERROR = "provider_auth_error"
REASON_PROVIDER_RATE_LIMITED = "provider_rate_limited"
REASON_PROVIDER_UNAVAILABLE = "provider_unavailable"
REASON_PROVIDER_INVALID_RESPONSE = "provider_invalid_response"

_DEFAULT_TIMEOUT_S = 65


@dataclass(frozen=True)
class DialogueSttResult:
    ok: bool
    text: str = field(default="", repr=False)
    reason_code: str = ""
    http_status: int = 503
    duration_ms: int = 0

    def to_payload(self) -> dict[str, Any]:
        if self.ok:
            return {
                "ok": True,
                "text": self.text,
                "duration_ms": self.duration_ms,
            }
        return {
            "ok": False,
            "reason_code": self.reason_code,
            "duration_ms": self.duration_ms,
        }


def failure_result(
    reason_code: str,
    *,
    http_status: int = 422,
    duration_ms: int = 0,
) -> DialogueSttResult:
    return DialogueSttResult(
        ok=False,
        reason_code=reason_code,
        http_status=http_status,
        duration_ms=max(0, int(duration_ms)),
    )


def request_body_size_guard_result(content_length: Any) -> DialogueSttResult | None:
    try:
        body_size = int(content_length)
    except (TypeError, ValueError):
        return failure_result(REASON_AUDIO_REQUEST_SIZE_REQUIRED)
    if body_size <= 0:
        return failure_result(REASON_AUDIO_REQUEST_SIZE_REQUIRED)
    if body_size <= MAX_DIALOGUE_STT_REQUEST_BYTES:
        return None
    return failure_result(REASON_AUDIO_REQUEST_TOO_LARGE)


def transcribe_dialogue_audio(
    audio_bytes: bytes,
    mime_type: str,
    *,
    requests_module: Any = requests,
    config_module: Any = config,
    llm_module: Any = llm_client,
    logger_obj: Any = logger,
    monotonic: Any = time.monotonic,
) -> DialogueSttResult:
    started_at = monotonic()
    normalized_mime = str(mime_type or "").strip().lower()
    if not isinstance(audio_bytes, bytes) or not audio_bytes:
        return _failure(
            REASON_AUDIO_EMPTY,
            started_at=started_at,
            monotonic=monotonic,
            audio_bytes=0,
            mime_type=normalized_mime,
            logger_obj=logger_obj,
        )
    audio_size = len(audio_bytes)
    extension = SUPPORTED_AUDIO_MIME_EXTENSIONS.get(normalized_mime)
    if extension is None:
        return _failure(
            REASON_AUDIO_TYPE_UNSUPPORTED,
            started_at=started_at,
            monotonic=monotonic,
            audio_bytes=audio_size,
            mime_type=normalized_mime,
            logger_obj=logger_obj,
        )
    if audio_size > MAX_DIALOGUE_STT_FILE_BYTES:
        return _failure(
            REASON_AUDIO_FILE_TOO_LARGE,
            started_at=started_at,
            monotonic=monotonic,
            audio_bytes=audio_size,
            mime_type=normalized_mime,
            logger_obj=logger_obj,
        )

    try:
        provider_url = str(llm_module.or_audio_transcriptions_url() or "").strip()
        provider_headers = llm_module.or_headers_custom(
            caller="dialogue_stt",
            referer=str(
                getattr(config_module, "OR_REFERER_DIALOGUE_STT", "") or ""
            ).strip(),
            title=str(
                getattr(config_module, "OR_TITLE_DIALOGUE_STT", "") or ""
            ).strip(),
        )
        provider_headers = llm_module.strip_internal_provider_headers(
            provider_headers
        )
        provider_headers.pop("Content-Type", None)
        authorization = str(provider_headers.get("Authorization") or "").strip()
        if not provider_url or authorization == "Bearer":
            raise RuntimeError("provider configuration unavailable")
    except Exception:
        return _failure(
            REASON_PROVIDER_NOT_CONFIGURED,
            started_at=started_at,
            monotonic=monotonic,
            audio_bytes=audio_size,
            mime_type=normalized_mime,
            logger_obj=logger_obj,
            http_status=503,
        )

    timeout_s = _timeout_s(config_module)
    timeout_class, request_error_class = _request_error_classes(requests_module)
    try:
        response = requests_module.post(
            provider_url,
            files={
                "file": (
                    f"audio{extension}",
                    audio_bytes,
                    normalized_mime,
                )
            },
            data={
                "model": DIALOGUE_STT_MODEL,
                "language": DIALOGUE_STT_LANGUAGE,
                "temperature": DIALOGUE_STT_TEMPERATURE,
                "response_format": DIALOGUE_STT_RESPONSE_FORMAT,
            },
            headers=provider_headers,
            timeout=timeout_s,
        )
    except Exception as exc:
        if timeout_class is not None and isinstance(exc, timeout_class):
            reason_code = REASON_PROVIDER_TIMEOUT
        elif request_error_class is not None and isinstance(exc, request_error_class):
            reason_code = REASON_PROVIDER_TRANSPORT_ERROR
        else:
            reason_code = REASON_PROVIDER_TRANSPORT_ERROR
        return _failure(
            reason_code,
            started_at=started_at,
            monotonic=monotonic,
            audio_bytes=audio_size,
            mime_type=normalized_mime,
            logger_obj=logger_obj,
            http_status=503,
        )

    status_code = _status_code(response)
    if status_code != 200:
        reason_code = _provider_status_reason(status_code)
        return _failure(
            reason_code,
            started_at=started_at,
            monotonic=monotonic,
            audio_bytes=audio_size,
            mime_type=normalized_mime,
            logger_obj=logger_obj,
            http_status=503,
            provider_status=status_code,
        )

    try:
        payload = response.json()
    except Exception:
        payload = None
    if not isinstance(payload, Mapping) or not isinstance(payload.get("text"), str):
        return _failure(
            REASON_PROVIDER_INVALID_RESPONSE,
            started_at=started_at,
            monotonic=monotonic,
            audio_bytes=audio_size,
            mime_type=normalized_mime,
            logger_obj=logger_obj,
            http_status=502,
            provider_status=status_code,
        )

    duration_ms = _duration_ms(started_at, monotonic)
    text = payload["text"]
    _log(
        logger_obj,
        "info",
        (
            "dialogue_stt_completed status=200 reason_code=%s duration_ms=%s "
            "audio_bytes=%s mime_type=%s transcript_chars=%s"
        ),
        REASON_OK,
        duration_ms,
        audio_size,
        normalized_mime,
        len(text),
    )
    return DialogueSttResult(
        ok=True,
        text=text,
        reason_code=REASON_OK,
        http_status=200,
        duration_ms=duration_ms,
    )


def _failure(
    reason_code: str,
    *,
    started_at: float,
    monotonic: Any,
    audio_bytes: int,
    mime_type: str,
    logger_obj: Any,
    http_status: int = 422,
    provider_status: int | None = None,
) -> DialogueSttResult:
    duration_ms = _duration_ms(started_at, monotonic)
    _log(
        logger_obj,
        "warning",
        (
            "dialogue_stt_failed status=%s reason_code=%s duration_ms=%s "
            "audio_bytes=%s mime_type=%s provider_status=%s"
        ),
        http_status,
        reason_code,
        duration_ms,
        max(0, int(audio_bytes)),
        mime_type if mime_type in SUPPORTED_AUDIO_MIME_EXTENSIONS else "unsupported",
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
            getattr(config_module, "DIALOGUE_STT_TIMEOUT_S", _DEFAULT_TIMEOUT_S)
        )
    except (TypeError, ValueError):
        timeout_s = _DEFAULT_TIMEOUT_S
    return max(1, timeout_s)


def _request_error_classes(requests_module: Any) -> tuple[type[Any] | None, type[Any] | None]:
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


def _provider_status_reason(status_code: int) -> str:
    if status_code in {401, 403}:
        return REASON_PROVIDER_AUTH_ERROR
    if status_code == 429:
        return REASON_PROVIDER_RATE_LIMITED
    if status_code == 524:
        return REASON_PROVIDER_TIMEOUT
    return REASON_PROVIDER_UNAVAILABLE


def _log(logger_obj: Any, level: str, message: str, *args: Any) -> None:
    log_method = getattr(logger_obj, level, None)
    if callable(log_method):
        log_method(message, *args)
