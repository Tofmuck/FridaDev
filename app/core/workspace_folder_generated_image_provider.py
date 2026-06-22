from __future__ import annotations

"""Generated Images V1 provider adapter.

This module reuses the V0 generator allowlist and OpenRouter payload shape, but
does not expose the provider data URL as a product result. The data URL is an
internal transient value consumed by the V1 validator and Nextcloud-first
runtime.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Mapping

import requests

from tools import image_generation

from . import workspace_folder_generated_images
from . import workspace_folder_generated_image_validation


logger = logging.getLogger("frida.workspace_folder_generated_image_provider")


@dataclass(frozen=True)
class GeneratedImageProviderResult:
    ok: bool
    reason_code: str
    status: int = 502
    data_url: str = ""
    generator_key: str = ""
    provider_model: str = ""
    aspect_ratio: str = ""
    image_size: str = ""
    prompt_length: int = 0
    data_url_chars: int = 0


def generate_generated_image_data_url(
    request_payload: Any,
    *,
    requests_module: Any = requests,
    llm_module: Any | None = None,
    logger_obj: Any = logger,
) -> GeneratedImageProviderResult:
    validated, failure = _validate_request_payload(request_payload)
    if failure is not None:
        return failure
    spec, prompt, aspect_ratio, image_size = validated
    llm_module = llm_module or _default_llm_module()

    provider_payload = image_generation.build_openrouter_payload(
        spec=spec,
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
    )
    started_at = time.monotonic()
    _log_event(
        logger_obj,
        "info",
        "generated_image_provider_requested",
        generator_key=spec.generator_key,
        model=spec.openrouter_model_id,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        status="requested",
    )
    try:
        headers = llm_module.or_headers_custom(
            caller=spec.generator_key,
            referer=spec.openrouter_referer,
            title=spec.openrouter_title,
        )
        url = llm_module.or_chat_completions_url()
        response = requests_module.post(
            url,
            json=provider_payload,
            headers=headers,
            timeout=image_generation.IMAGE_GENERATION_TIMEOUT_S,
        )
    except requests.Timeout:
        return _provider_failure(
            workspace_folder_generated_images.REASON_PROVIDER_TIMEOUT,
            spec=spec,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            logger_obj=logger_obj,
            started_at=started_at,
            status=504,
        )
    except requests.RequestException:
        return _provider_failure(
            workspace_folder_generated_images.REASON_PROVIDER_ERROR_REDACTED,
            spec=spec,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            logger_obj=logger_obj,
            started_at=started_at,
            status=502,
        )
    except Exception:
        return _provider_failure(
            workspace_folder_generated_images.REASON_PROVIDER_ERROR_REDACTED,
            spec=spec,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            logger_obj=logger_obj,
            started_at=started_at,
            status=502,
        )

    provider_status = int(getattr(response, "status_code", 200) or 200)
    if provider_status >= 400:
        return _provider_failure(
            workspace_folder_generated_images.REASON_PROVIDER_ERROR_REDACTED,
            spec=spec,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            logger_obj=logger_obj,
            started_at=started_at,
            provider_status=provider_status,
            status=502,
        )

    try:
        provider_response = llm_module.read_openrouter_response_payload(response)
    except Exception:
        return _provider_failure(
            workspace_folder_generated_images.REASON_PROVIDER_PAYLOAD_INVALID,
            spec=spec,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            logger_obj=logger_obj,
            started_at=started_at,
            status=502,
        )

    data_url = image_generation._extract_first_image_data_url(provider_response)
    provider_model = image_generation._provider_model(provider_response, spec)
    if not data_url:
        return _provider_failure(
            workspace_folder_generated_images.REASON_PROVIDER_NO_IMAGE,
            spec=spec,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            logger_obj=logger_obj,
            started_at=started_at,
            provider_model=provider_model,
            status=502,
        )
    data_url_chars = len(data_url)
    if data_url_chars > workspace_folder_generated_image_validation.V1_IMAGE_DATA_URL_MAX_CHARS:
        return _provider_failure(
            workspace_folder_generated_images.REASON_DATA_URL_TOO_LARGE,
            spec=spec,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            logger_obj=logger_obj,
            started_at=started_at,
            provider_model=provider_model,
            data_url_chars=data_url_chars,
            status=413,
        )

    _log_event(
        logger_obj,
        "info",
        "generated_image_provider_completed",
        generator_key=spec.generator_key,
        model=spec.openrouter_model_id,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        status="ok",
        latency_ms=_elapsed_ms(started_at),
        provider_model=provider_model,
        data_url_chars=data_url_chars,
    )
    return GeneratedImageProviderResult(
        True,
        workspace_folder_generated_images.REASON_CREATE_OK,
        status=200,
        data_url=data_url,
        generator_key=spec.generator_key,
        provider_model=provider_model,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        prompt_length=len(prompt),
        data_url_chars=data_url_chars,
    )


def runtime_secret_status() -> dict[str, Any]:
    try:
        from admin import runtime_settings

        secret = runtime_settings.get_runtime_secret_value("main_model", "api_key")
        available = bool(str(secret.value or "").strip())
        source = str(secret.source or "").strip() or "unknown"
    except Exception:
        available = False
        source = "unavailable"
    return {
        "secret_available": available,
        "source_type": workspace_folder_generated_images.safe_token(source, max_chars=40),
        "source_ref": "[redacted]",
        "value_displayed": False,
    }


def _validate_request_payload(
    payload: Any,
) -> tuple[
    tuple[image_generation.ImageGeneratorSpec, str, str, str] | None,
    GeneratedImageProviderResult | None,
]:
    if not isinstance(payload, Mapping):
        return None, _failure(workspace_folder_generated_images.REASON_PROMPT_MISSING, status=400)

    generator_key = str(payload.get("generator_key") or "").strip()
    spec = image_generation.IMAGE_GENERATORS.get(generator_key)
    if spec is None:
        return None, _failure(
            workspace_folder_generated_images.REASON_GENERATOR_UNSUPPORTED,
            status=400,
        )

    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        return None, _failure(workspace_folder_generated_images.REASON_PROMPT_MISSING, status=400)
    if len(prompt) > image_generation.PROMPT_MAX_CHARS:
        return None, _failure(
            workspace_folder_generated_images.REASON_PROMPT_TOO_LARGE,
            status=413,
        )

    aspect_ratio = str(payload.get("aspect_ratio") or "").strip()
    if aspect_ratio not in spec.supported_aspect_ratios:
        return None, _failure(
            workspace_folder_generated_images.REASON_ASPECT_RATIO_UNSUPPORTED,
            status=400,
        )

    image_size = str(payload.get("image_size") or "").strip()
    if image_size not in spec.supported_image_sizes:
        return None, _failure(
            workspace_folder_generated_images.REASON_SIZE_UNSUPPORTED,
            status=400,
        )

    return (spec, prompt, aspect_ratio, image_size), None


def _provider_failure(
    reason_code: str,
    *,
    spec: image_generation.ImageGeneratorSpec,
    aspect_ratio: str,
    image_size: str,
    logger_obj: Any,
    started_at: float,
    status: int,
    provider_status: int | None = None,
    provider_model: str = "",
    data_url_chars: int = 0,
) -> GeneratedImageProviderResult:
    _log_event(
        logger_obj,
        "warning",
        "generated_image_provider_failed",
        generator_key=spec.generator_key,
        model=spec.openrouter_model_id,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        status="error",
        reason_code=reason_code,
        latency_ms=_elapsed_ms(started_at),
        provider_status=provider_status,
        provider_model=provider_model,
        data_url_chars=data_url_chars,
    )
    return GeneratedImageProviderResult(
        False,
        reason_code,
        status=status,
        generator_key=spec.generator_key,
        provider_model=provider_model,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        data_url_chars=data_url_chars,
    )


def _failure(reason_code: str, *, status: int) -> GeneratedImageProviderResult:
    return GeneratedImageProviderResult(False, reason_code, status=status)


def _elapsed_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)


def _log_event(logger_obj: Any, level: str, event: str, **fields: Any) -> None:
    log_method = getattr(logger_obj, level, None)
    if not callable(log_method):
        return
    log_method(
        "%s generator_key=%s model=%s aspect_ratio=%s image_size=%s status=%s "
        "reason_code=%s latency_ms=%s provider_status=%s provider_model=%s data_url_chars=%s",
        event,
        fields.get("generator_key") or "",
        fields.get("model") or "",
        fields.get("aspect_ratio") or "",
        fields.get("image_size") or "",
        fields.get("status") or "",
        fields.get("reason_code") or "",
        fields.get("latency_ms"),
        fields.get("provider_status"),
        fields.get("provider_model") or "",
        fields.get("data_url_chars") or 0,
    )


def _default_llm_module() -> Any:
    from core import llm_client

    return llm_client
