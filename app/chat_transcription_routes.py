from typing import Any, Callable

from flask import Flask


def register_chat_transcription_route(
    app: Flask,
    *,
    get_request: Callable[[], Any],
    whisper_transcription_service_module: Any,
    requests_module: Any,
    config_module: Any,
    logger_obj: Any,
    jsonify_func: Callable[..., Any],
) -> Callable[[], Any]:
    def api_chat_transcribe():
        current_request = get_request()
        body_guard = (
            whisper_transcription_service_module.request_body_size_guard_response(
                current_request.content_length
            )
        )
        if body_guard:
            payload, status = body_guard
            return jsonify_func(payload), status

        try:
            payload, status = (
                whisper_transcription_service_module.transcribe_http_request(
                    content_type=current_request.content_type,
                    files=current_request.files,
                    form=current_request.form,
                    requests_module=requests_module,
                    config_module=config_module,
                    logger_obj=logger_obj,
                )
            )
        except (
            whisper_transcription_service_module.WhisperTranscriptionServiceError
        ) as exc:
            payload, status = exc.as_response()
        return jsonify_func(payload), status

    app.add_url_rule(
        "/api/chat/transcribe",
        endpoint="api_chat_transcribe",
        view_func=api_chat_transcribe,
        methods=["POST"],
    )
    return api_chat_transcribe
