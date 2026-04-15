from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Mapping

import requests


logger = logging.getLogger('frida.whisper_transcription')

_SUCCESS_INPUT_MODE = 'voice'
_DEFAULT_MODEL = 'whisper-1'
_DEFAULT_RESPONSE_FORMAT = 'json'
_DEFAULT_TIMEOUT_S = 120
_DEFAULT_CONTENT_TYPE = 'application/octet-stream'


@dataclass(frozen=True)
class TranscriptionUpload:
    filename: str
    content_type: str
    data: bytes


class WhisperTranscriptionServiceError(Exception):
    def __init__(self, *, status_code: int, error: str) -> None:
        super().__init__(error)
        self.status_code = int(status_code)
        self.error = str(error)

    def as_response(self) -> tuple[dict[str, Any], int]:
        return ({'ok': False, 'error': self.error}, self.status_code)


def _text(value: Any) -> str:
    return str(value or '').strip()


def _multipart_request(content_type: Any) -> bool:
    return 'multipart/form-data' in _text(content_type).lower()


def _timeout_s(config_module: Any) -> int:
    raw_timeout = getattr(config_module, 'WHISPER_API_TIMEOUT_S', _DEFAULT_TIMEOUT_S)
    try:
        timeout_s = int(raw_timeout)
    except (TypeError, ValueError):
        timeout_s = _DEFAULT_TIMEOUT_S
    return max(1, timeout_s)


def _api_url(config_module: Any) -> str:
    return _text(getattr(config_module, 'WHISPER_API_URL', '')).rstrip('/')


def _auth_headers(config_module: Any) -> dict[str, str]:
    api_key = _text(getattr(config_module, 'WHISPER_API_KEY', ''))
    if not api_key:
        return {}
    return {'Authorization': f'Bearer {api_key}'}


def _request_error_classes(requests_module: Any) -> tuple[type[Any] | None, type[Any] | None]:
    exceptions = getattr(requests_module, 'exceptions', None)
    return (
        getattr(exceptions, 'Timeout', None),
        getattr(exceptions, 'RequestException', None),
    )


def _response_json(response: Any) -> Mapping[str, Any]:
    try:
        payload = response.json()
    except Exception as exc:
        raise WhisperTranscriptionServiceError(
            status_code=502,
            error='transcription indisponible',
        ) from exc
    if not isinstance(payload, Mapping):
        raise WhisperTranscriptionServiceError(
            status_code=502,
            error='transcription indisponible',
        )
    return payload


def _response_detail(response: Any) -> str:
    text_value = _text(getattr(response, 'text', ''))
    if text_value:
        return text_value[:200]
    try:
        payload = response.json()
    except Exception:
        return ''
    if isinstance(payload, Mapping):
        detail = payload.get('detail') or payload.get('error') or payload.get('message')
        return _text(detail)[:200]
    return ''


def prepare_upload(
    *,
    content_type: Any,
    files: Mapping[str, Any],
) -> TranscriptionUpload:
    if not _multipart_request(content_type):
        raise WhisperTranscriptionServiceError(
            status_code=400,
            error='multipart/form-data requis',
        )

    file_storage = files.get('file') if hasattr(files, 'get') else None
    if file_storage is None:
        raise WhisperTranscriptionServiceError(
            status_code=400,
            error='file requis',
        )

    raw_data = file_storage.read()
    data = bytes(raw_data or b'')
    if not data:
        raise WhisperTranscriptionServiceError(
            status_code=400,
            error='file vide',
        )

    filename = _text(getattr(file_storage, 'filename', '')) or 'audio.bin'
    mime_type = (
        _text(getattr(file_storage, 'mimetype', ''))
        or _text(getattr(file_storage, 'content_type', ''))
        or _DEFAULT_CONTENT_TYPE
    )
    return TranscriptionUpload(
        filename=filename,
        content_type=mime_type,
        data=data,
    )


def transcribe_upload(
    upload: TranscriptionUpload,
    *,
    requests_module: Any = requests,
    config_module: Any,
    logger_obj: Any = logger,
) -> str:
    api_url = _api_url(config_module)
    if not api_url:
        raise WhisperTranscriptionServiceError(
            status_code=502,
            error='transcription indisponible',
        )

    timeout_s = _timeout_s(config_module)
    timeout_cls, request_cls = _request_error_classes(requests_module)
    try:
        response = requests_module.post(
            f'{api_url}/v1/audio/transcriptions',
            files={
                'file': (
                    upload.filename,
                    upload.data,
                    upload.content_type,
                )
            },
            data={
                'model': _DEFAULT_MODEL,
                'response_format': _DEFAULT_RESPONSE_FORMAT,
            },
            headers=_auth_headers(config_module),
            timeout=timeout_s,
        )
    except Exception as exc:
        if timeout_cls is not None and isinstance(exc, timeout_cls):
            raise WhisperTranscriptionServiceError(
                status_code=504,
                error="transcription timeout",
            ) from exc
        if request_cls is not None and isinstance(exc, request_cls):
            logger_obj.warning(
                'whisper_upstream_request_failed url=%s timeout_s=%s err=%s',
                api_url,
                timeout_s,
                exc.__class__.__name__,
            )
            raise WhisperTranscriptionServiceError(
                status_code=502,
                error='transcription indisponible',
            ) from exc
        raise

    status_code = int(getattr(response, 'status_code', 0) or 0)
    if status_code == 504:
        logger_obj.warning(
            'whisper_upstream_timeout_response url=%s timeout_s=%s detail=%s',
            api_url,
            timeout_s,
            _response_detail(response),
        )
        raise WhisperTranscriptionServiceError(
            status_code=504,
            error='transcription timeout',
        )
    if status_code >= 400 or status_code == 0:
        logger_obj.warning(
            'whisper_upstream_bad_status url=%s status=%s detail=%s',
            api_url,
            status_code,
            _response_detail(response),
        )
        raise WhisperTranscriptionServiceError(
            status_code=502,
            error='transcription indisponible',
        )

    payload = _response_json(response)
    if 'text' not in payload:
        logger_obj.warning(
            'whisper_upstream_invalid_payload url=%s keys=%s',
            api_url,
            ','.join(sorted(str(key) for key in payload.keys())),
        )
        raise WhisperTranscriptionServiceError(
            status_code=502,
            error='transcription indisponible',
        )
    return str(payload.get('text') or '')


def transcribe_http_request(
    *,
    content_type: Any,
    files: Mapping[str, Any],
    requests_module: Any = requests,
    config_module: Any,
    logger_obj: Any = logger,
) -> tuple[dict[str, Any], int]:
    upload = prepare_upload(
        content_type=content_type,
        files=files,
    )
    text = transcribe_upload(
        upload,
        requests_module=requests_module,
        config_module=config_module,
        logger_obj=logger_obj,
    )
    return (
        {
            'ok': True,
            'text': text,
            'input_mode': _SUCCESS_INPUT_MODE,
        },
        200,
    )
