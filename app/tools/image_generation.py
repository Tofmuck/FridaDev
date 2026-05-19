from __future__ import annotations

import logging
import re
import time
from dataclasses import asdict, dataclass
from typing import Any, Mapping

import requests


logger = logging.getLogger("frida.image_generation")

IMAGE_GENERATION_TIMEOUT_S = 180
PROMPT_MAX_CHARS = 2000
# Guard against absurd provider responses while allowing normal V0 images.
IMAGE_DATA_URL_MAX_CHARS = 6_000_000

ERROR_MESSAGES = {
    'invalid_generator': 'Unknown image generator.',
    'invalid_prompt': 'A non-empty prompt is required.',
    'invalid_aspect_ratio': 'Unsupported aspect ratio for this generator.',
    'invalid_image_size': 'Unsupported image size for this generator.',
    'provider_error': 'Image provider error.',
    'no_image': 'Provider response did not include an image.',
    'invalid_image_data_url': 'Provider returned an invalid image data URL.',
    'timeout': 'Image provider timeout.',
}


@dataclass(frozen=True)
class ImageGeneratorSpec:
    generator_key: str
    display_name: str
    openrouter_model_id: str
    openrouter_title: str
    openrouter_referer: str
    modalities: tuple[str, ...]
    supported_aspect_ratios: tuple[str, ...]
    supported_image_sizes: tuple[str, ...]
    pricing_label: str
    pricing_source: str
    is_preview: bool
    notes: str


IMAGE_GENERATORS: dict[str, ImageGeneratorSpec] = {
    'image_generator_openai': ImageGeneratorSpec(
        generator_key='image_generator_openai',
        display_name='OpenAI Image',
        openrouter_model_id='openai/gpt-5.4-image-2',
        openrouter_title='FridaDev / Image Generator / OpenAI',
        openrouter_referer='https://fridadev.frida-system.fr/openrouter/image-generation/openai',
        modalities=('image', 'text'),
        supported_aspect_ratios=('1:1', '16:9', '9:16'),
        supported_image_sizes=('1K',),
        pricing_label='prix API observe: prompt 0.000008 / completion 0.000015; prix image non expose',
        pricing_source='API modeles + smoke cout observe',
        is_preview=False,
        notes='rendu general; cout observe eleve au smoke',
    ),
    'image_generator_nano_banana': ImageGeneratorSpec(
        generator_key='image_generator_nano_banana',
        display_name='Nano Banana',
        openrouter_model_id='google/gemini-2.5-flash-image',
        openrouter_title='FridaDev / Image Generator / Nano Banana',
        openrouter_referer='https://fridadev.frida-system.fr/openrouter/image-generation/nano-banana',
        modalities=('image', 'text'),
        supported_aspect_ratios=(
            '1:1',
            '2:3',
            '3:2',
            '3:4',
            '4:3',
            '4:5',
            '5:4',
            '9:16',
            '16:9',
            '21:9',
        ),
        supported_image_sizes=('1K', '2K', '4K'),
        pricing_label='prix API observe: image 0.0000003 / prompt 0.0000003 / completion 0.0000025',
        pricing_source='API modeles + smoke cout observe',
        is_preview=False,
        notes='candidat rapide/economique; remplace Gemini 3.1 preview non concluant',
    ),
    'image_generator_recraft': ImageGeneratorSpec(
        generator_key='image_generator_recraft',
        display_name='Recraft',
        openrouter_model_id='recraft/recraft-v4.1',
        openrouter_title='FridaDev / Image Generator / Recraft',
        openrouter_referer='https://fridadev.frida-system.fr/openrouter/image-generation/recraft',
        modalities=('image',),
        supported_aspect_ratios=('1:1', '16:9', '9:16'),
        supported_image_sizes=('1K',),
        pricing_label="prix image non expose par l'API modeles",
        pricing_source='API modeles incomplete + smoke cout observe',
        is_preview=False,
        notes='illustration/design; sortie WEBP observee',
    ),
    'image_generator_flux': ImageGeneratorSpec(
        generator_key='image_generator_flux',
        display_name='Flux',
        openrouter_model_id='black-forest-labs/flux.2-pro',
        openrouter_title='FridaDev / Image Generator / Flux',
        openrouter_referer='https://fridadev.frida-system.fr/openrouter/image-generation/flux',
        modalities=('image',),
        supported_aspect_ratios=('1:1', '16:9', '9:16'),
        supported_image_sizes=('1K',),
        pricing_label="prix image non expose par l'API modeles",
        pricing_source='API modeles incomplete + smoke cout observe',
        is_preview=False,
        notes='option experimentale; sortie PNG volumineuse observee',
    ),
}

_DATA_URL_RE = re.compile(r'^data:(image/[A-Za-z0-9.+-]+);base64,')


def list_image_generators() -> list[dict[str, Any]]:
    return [_spec_to_public_payload(spec) for spec in IMAGE_GENERATORS.values()]


def generate_image_response(
    request_payload: Any,
    *,
    requests_module: Any = requests,
    llm_module: Any | None = None,
    logger_obj: Any = logger,
) -> tuple[dict[str, Any], int]:
    validated = _validate_request_payload(request_payload)
    if validated[1] is not None:
        return validated[1]
    spec, prompt, aspect_ratio, image_size = validated[0]
    llm_module = llm_module or _default_llm_module()

    provider_payload = build_openrouter_payload(
        spec=spec,
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
    )
    headers = llm_module.or_headers_custom(
        caller=spec.generator_key,
        referer=spec.openrouter_referer,
        title=spec.openrouter_title,
    )
    url = llm_module.or_chat_completions_url()
    started_at = time.monotonic()
    _log_event(
        logger_obj,
        'info',
        'image_generation_requested',
        generator_key=spec.generator_key,
        model=spec.openrouter_model_id,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        status='requested',
    )

    try:
        response = requests_module.post(
            url,
            json=provider_payload,
            headers=headers,
            timeout=IMAGE_GENERATION_TIMEOUT_S,
        )
    except requests.Timeout:
        latency_ms = _elapsed_ms(started_at)
        _log_failure(
            logger_obj,
            spec=spec,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            latency_ms=latency_ms,
            error_code='timeout',
        )
        return _error('timeout', status=504)
    except requests.RequestException:
        latency_ms = _elapsed_ms(started_at)
        _log_failure(
            logger_obj,
            spec=spec,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            latency_ms=latency_ms,
            error_code='provider_error',
        )
        return _error('provider_error', status=502)

    latency_ms = _elapsed_ms(started_at)
    status_code = int(getattr(response, 'status_code', 200) or 200)
    if status_code >= 400:
        _log_failure(
            logger_obj,
            spec=spec,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            latency_ms=latency_ms,
            error_code='provider_error',
            provider_status=status_code,
        )
        return _error('provider_error', status=502)

    try:
        provider_response = llm_module.read_openrouter_response_payload(response)
    except Exception:
        _log_failure(
            logger_obj,
            spec=spec,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            latency_ms=latency_ms,
            error_code='provider_error',
        )
        return _error('provider_error', status=502)

    image_data_url = _extract_first_image_data_url(provider_response)
    if not image_data_url:
        _log_failure(
            logger_obj,
            spec=spec,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            latency_ms=latency_ms,
            error_code='no_image',
            provider_model=_provider_model(provider_response, spec),
            usage=_usage_payload(provider_response),
        )
        return _error('no_image', status=502)

    if len(image_data_url) > IMAGE_DATA_URL_MAX_CHARS:
        _log_failure(
            logger_obj,
            spec=spec,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            latency_ms=latency_ms,
            error_code='invalid_image_data_url',
            provider_model=_provider_model(provider_response, spec),
            usage=_usage_payload(provider_response),
            data_url_chars=len(image_data_url),
        )
        return _error('invalid_image_data_url', status=502)

    mime_type = _mime_type_from_data_url(image_data_url)
    if not mime_type:
        _log_failure(
            logger_obj,
            spec=spec,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            latency_ms=latency_ms,
            error_code='invalid_image_data_url',
            provider_model=_provider_model(provider_response, spec),
            usage=_usage_payload(provider_response),
            data_url_chars=len(image_data_url),
        )
        return _error('invalid_image_data_url', status=502)

    provider_model = _provider_model(provider_response, spec)
    usage = _usage_payload(provider_response)
    _log_event(
        logger_obj,
        'info',
        'image_generation_completed',
        generator_key=spec.generator_key,
        model=spec.openrouter_model_id,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        status='ok',
        latency_ms=latency_ms,
        provider_model=provider_model,
        usage=usage,
        mime_type=mime_type,
        data_url_chars=len(image_data_url),
    )
    return (
        {
            'ok': True,
            'generator_key': spec.generator_key,
            'model': spec.openrouter_model_id,
            'display_name': spec.display_name,
            'pricing_label': spec.pricing_label,
            'aspect_ratio': aspect_ratio,
            'image_size': image_size,
            'image_data_url': image_data_url,
            'mime_type': mime_type,
            'provider_model': provider_model,
            'usage': usage,
        },
        200,
    )


def build_openrouter_payload(
    *,
    spec: ImageGeneratorSpec,
    prompt: str,
    aspect_ratio: str,
    image_size: str,
) -> dict[str, Any]:
    return {
        'model': spec.openrouter_model_id,
        'messages': [{'role': 'user', 'content': prompt}],
        'modalities': list(spec.modalities),
        'image_config': {
            'aspect_ratio': aspect_ratio,
            'image_size': image_size,
        },
        'stream': False,
        'metadata': {
            'frida_caller': spec.generator_key,
            'frida_slot': 'image_generation_tool',
            'frida_image_model': spec.openrouter_model_id,
        },
        'trace': {
            'trace_name': 'FridaDev',
            'generation_name': spec.openrouter_title,
        },
    }


def _validate_request_payload(
    payload: Any,
) -> tuple[tuple[ImageGeneratorSpec, str, str, str] | None, tuple[dict[str, Any], int] | None]:
    if not isinstance(payload, Mapping):
        return None, _error('invalid_prompt', message='Invalid request payload.')

    generator_key = str(payload.get('generator_key') or '').strip()
    spec = IMAGE_GENERATORS.get(generator_key)
    if spec is None:
        return None, _error('invalid_generator')

    prompt = str(payload.get('prompt') or '').strip()
    if not prompt:
        return None, _error('invalid_prompt')
    if len(prompt) > PROMPT_MAX_CHARS:
        return None, _error('invalid_prompt', message='Prompt is too long.')

    aspect_ratio = str(payload.get('aspect_ratio') or '').strip()
    if aspect_ratio not in spec.supported_aspect_ratios:
        return None, _error('invalid_aspect_ratio')

    image_size = str(payload.get('image_size') or '').strip()
    if image_size not in spec.supported_image_sizes:
        return None, _error('invalid_image_size')

    return (spec, prompt, aspect_ratio, image_size), None


def _spec_to_public_payload(spec: ImageGeneratorSpec) -> dict[str, Any]:
    payload = asdict(spec)
    payload['modalities'] = list(spec.modalities)
    payload['supported_aspect_ratios'] = list(spec.supported_aspect_ratios)
    payload['supported_image_sizes'] = list(spec.supported_image_sizes)
    return payload


def _error(error_code: str, *, message: str | None = None, status: int = 400) -> tuple[dict[str, Any], int]:
    return (
        {
            'ok': False,
            'error_code': error_code,
            'message': message or ERROR_MESSAGES.get(error_code, 'Image generation error.'),
        },
        status,
    )


def _extract_first_image_data_url(payload: Any) -> str | None:
    data = _mapping(payload)
    choices = data.get('choices')
    if not isinstance(choices, list) or not choices:
        return None

    choice = _mapping(choices[0])
    message = _mapping(choice.get('message'))
    images = message.get('images')
    if not isinstance(images, list) or not images:
        return None

    image = _mapping(images[0])
    image_url = image.get('image_url')
    if isinstance(image_url, str):
        return image_url.strip() or None
    image_url_map = _mapping(image_url)
    url = str(image_url_map.get('url') or '').strip()
    return url or None


def _mime_type_from_data_url(data_url: str) -> str | None:
    match = _DATA_URL_RE.match(str(data_url or ''))
    if not match:
        return None
    return match.group(1)


def _provider_model(payload: Any, spec: ImageGeneratorSpec) -> str:
    return str(_mapping(payload).get('model') or spec.openrouter_model_id)


def _usage_payload(payload: Any) -> dict[str, Any]:
    data = _mapping(payload)
    usage = dict(_mapping(data.get('usage')))
    cost = data.get('cost')
    if cost is not None and 'cost' not in usage:
        usage['cost'] = cost
    return usage


def _elapsed_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)


def _log_failure(
    logger_obj: Any,
    *,
    spec: ImageGeneratorSpec,
    aspect_ratio: str,
    image_size: str,
    latency_ms: int,
    error_code: str,
    provider_status: int | None = None,
    provider_model: str | None = None,
    usage: Mapping[str, Any] | None = None,
    data_url_chars: int | None = None,
) -> None:
    _log_event(
        logger_obj,
        'warning',
        'image_generation_failed',
        generator_key=spec.generator_key,
        model=spec.openrouter_model_id,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        status='error',
        error_code=error_code,
        latency_ms=latency_ms,
        provider_status=provider_status,
        provider_model=provider_model,
        usage=dict(usage or {}),
        data_url_chars=data_url_chars,
    )


def _log_event(logger_obj: Any, level: str, event: str, **fields: Any) -> None:
    log_method = getattr(logger_obj, level, None)
    if not callable(log_method):
        return
    log_method(
        '%s generator_key=%s model=%s aspect_ratio=%s image_size=%s status=%s error_code=%s latency_ms=%s provider_status=%s provider_model=%s usage=%s mime_type=%s data_url_chars=%s',
        event,
        fields.get('generator_key') or '',
        fields.get('model') or '',
        fields.get('aspect_ratio') or '',
        fields.get('image_size') or '',
        fields.get('status') or '',
        fields.get('error_code') or '',
        fields.get('latency_ms'),
        fields.get('provider_status'),
        fields.get('provider_model') or '',
        fields.get('usage') or {},
        fields.get('mime_type') or '',
        fields.get('data_url_chars'),
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _default_llm_module() -> Any:
    from core import llm_client

    return llm_client
