from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from flask import Flask


def register_chat_dialogue_audio_routes(
    app: Flask,
    *,
    get_request: Callable[[], Any],
    dialogue_stt_service_module: Any,
    dialogue_tts_service_module: Any,
    requests_module: Any,
    config_module: Any,
    llm_module: Any,
    logger_obj: Any,
    jsonify_func: Callable[..., Any],
) -> tuple[Callable[[], Any], Callable[[], Any]]:
    def api_chat_dialogue_transcribe():
        current_request = get_request()
        body_guard = dialogue_stt_service_module.request_body_size_guard_result(
            current_request.content_length
        )
        if body_guard is not None:
            return jsonify_func(body_guard.to_payload()), body_guard.http_status

        if not _is_multipart(current_request.content_type):
            return _local_failure(
                dialogue_stt_service_module,
                jsonify_func,
                "multipart_required",
            )

        files = current_request.files
        form = current_request.form
        file_keys = set(_mapping_keys(files))
        if _mapping_keys(form) or (file_keys and file_keys != {"audio"}):
            return _local_failure(
                dialogue_stt_service_module,
                jsonify_func,
                "audio_field_invalid",
            )
        if "audio" not in file_keys:
            return _local_failure(
                dialogue_stt_service_module,
                jsonify_func,
                "audio_missing",
            )

        uploads = _file_values(files, "audio")
        if len(uploads) != 1:
            reason_code = "audio_multiple" if len(uploads) > 1 else "audio_missing"
            return _local_failure(
                dialogue_stt_service_module,
                jsonify_func,
                reason_code,
            )
        upload = uploads[0]

        mime_type = _mime_type(upload)
        expected_extension = (
            dialogue_stt_service_module.SUPPORTED_AUDIO_MIME_EXTENSIONS.get(
                mime_type
            )
        )
        if expected_extension is None:
            return _local_failure(
                dialogue_stt_service_module,
                jsonify_func,
                "audio_type_unsupported",
            )
        actual_extension = Path(str(getattr(upload, "filename", "") or "")).suffix.lower()
        if not actual_extension:
            return _local_failure(
                dialogue_stt_service_module,
                jsonify_func,
                "audio_extension_unsupported",
            )
        if actual_extension not in set(
            dialogue_stt_service_module.SUPPORTED_AUDIO_MIME_EXTENSIONS.values()
        ):
            return _local_failure(
                dialogue_stt_service_module,
                jsonify_func,
                "audio_extension_unsupported",
            )
        if actual_extension != expected_extension:
            return _local_failure(
                dialogue_stt_service_module,
                jsonify_func,
                "audio_type_mismatch",
            )

        try:
            audio_bytes = _read_bounded_audio(
                upload,
                max_bytes=dialogue_stt_service_module.MAX_DIALOGUE_STT_FILE_BYTES,
                chunk_bytes=dialogue_stt_service_module.UPLOAD_READ_CHUNK_BYTES,
            )
        except _AudioTooLarge:
            return _local_failure(
                dialogue_stt_service_module,
                jsonify_func,
                "audio_file_too_large",
            )
        except Exception:
            return _local_failure(
                dialogue_stt_service_module,
                jsonify_func,
                "audio_unreadable",
            )
        if not audio_bytes:
            return _local_failure(
                dialogue_stt_service_module,
                jsonify_func,
                "audio_empty",
            )

        result = dialogue_stt_service_module.transcribe_dialogue_audio(
            audio_bytes,
            mime_type,
            requests_module=requests_module,
            config_module=config_module,
            llm_module=llm_module,
            logger_obj=logger_obj,
        )
        return jsonify_func(result.to_payload()), result.http_status

    def api_chat_dialogue_speech():
        current_request = get_request()
        payload = current_request.get_json(silent=True)
        if not isinstance(payload, Mapping):
            return _local_failure(
                dialogue_tts_service_module,
                jsonify_func,
                "dialogue_tts_text_payload_invalid",
            )
        if set(_mapping_keys(payload)) != {"text"}:
            return _local_failure(
                dialogue_tts_service_module,
                jsonify_func,
                "dialogue_tts_text_field_invalid",
            )

        text = payload.get("text")
        result = dialogue_tts_service_module.synthesize_dialogue_speech(
            text,
            requests_module=requests_module,
            config_module=config_module,
            llm_module=llm_module,
            logger_obj=logger_obj,
        )
        if not result.ok:
            return jsonify_func(result.to_payload()), result.http_status

        response = app.response_class(
            result.audio_bytes,
            status=result.http_status,
            content_type=result.content_type,
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    app.add_url_rule(
        "/api/chat/dialogue/transcribe",
        endpoint="api_chat_dialogue_transcribe",
        view_func=api_chat_dialogue_transcribe,
        methods=["POST"],
    )
    app.add_url_rule(
        "/api/chat/dialogue/speech",
        endpoint="api_chat_dialogue_speech",
        view_func=api_chat_dialogue_speech,
        methods=["POST"],
    )
    return api_chat_dialogue_transcribe, api_chat_dialogue_speech


class _AudioTooLarge(Exception):
    pass


def _read_bounded_audio(file_storage: Any, *, max_bytes: int, chunk_bytes: int) -> bytes:
    chunks: list[bytes] = []
    observed_bytes = 0
    observed_limit = int(max_bytes) + 1
    while observed_bytes < observed_limit:
        read_size = min(int(chunk_bytes), observed_limit - observed_bytes)
        chunk = bytes(file_storage.read(read_size) or b"")
        if not chunk:
            break
        chunks.append(chunk)
        observed_bytes += len(chunk)
    if observed_bytes > max_bytes:
        raise _AudioTooLarge
    return b"".join(chunks)


def _local_failure(service_module: Any, jsonify_func: Callable[..., Any], reason_code: str):
    result = service_module.failure_result(reason_code)
    return jsonify_func(result.to_payload()), result.http_status


def _is_multipart(content_type: Any) -> bool:
    return "multipart/form-data" in str(content_type or "").strip().lower()


def _mapping_keys(values: Mapping[str, Any] | None) -> list[str]:
    if values is None or not hasattr(values, "keys"):
        return []
    return [str(key) for key in values.keys()]


def _file_values(files: Any, key: str) -> list[Any]:
    getlist = getattr(files, "getlist", None)
    if callable(getlist):
        return list(getlist(key))
    value = files.get(key) if hasattr(files, "get") else None
    return [] if value is None else [value]


def _mime_type(file_storage: Any) -> str:
    return str(
        getattr(file_storage, "mimetype", "")
        or getattr(file_storage, "content_type", "")
        or ""
    ).strip().lower()
