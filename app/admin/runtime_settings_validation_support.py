from __future__ import annotations

from typing import Any, Callable
from urllib.parse import urlparse


def validation_check(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {
        'name': name,
        'ok': bool(ok),
        'detail': str(detail),
    }


def runtime_text_value(view: Any, field: str) -> str:
    payload = view.payload.get(field) or {}
    return str(payload.get('value') or '').strip()


def runtime_int_value(view: Any, field: str) -> int | None:
    payload = view.payload.get(field) or {}
    value = payload.get('value')
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def runtime_float_value(view: Any, field: str) -> float | None:
    payload = view.payload.get(field) or {}
    value = payload.get('value')
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_http_url(value: str) -> bool:
    parsed = urlparse(str(value or '').strip())
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)


def component_referer_valid_or_shared_fallback(
    component_referer: str,
    shared_referer: str,
) -> bool:
    component_value = str(component_referer or '').strip()
    if component_value:
        return is_http_url(component_value)
    return is_http_url(shared_referer)


def secret_runtime_status(
    view: Any,
    field: str,
    field_ref: str,
    *,
    resolve_runtime_secret_from_view: Callable[[Any, str], Any],
    secret_required_error_cls: type[Exception],
    secret_resolution_error_cls: type[Exception],
) -> tuple[bool, str]:
    try:
        secret = resolve_runtime_secret_from_view(view, field)
        return (
            bool(str(secret.value).strip()),
            f'{field_ref} available from {secret.source}',
        )
    except (secret_required_error_cls, secret_resolution_error_cls) as exc:
        return False, f'{field_ref} unavailable ({exc.__class__.__name__})'


def shared_openrouter_transport_status(
    *,
    fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None,
    candidate_runtime_section: Callable[..., Any],
    resolve_runtime_secret_from_view: Callable[[Any, str], Any],
    secret_required_error_cls: type[Exception],
    secret_resolution_error_cls: type[Exception],
) -> tuple[bool, str]:
    main_model_view = candidate_runtime_section('main_model', fetcher=fetcher)
    base_url = runtime_text_value(main_model_view, 'base_url')
    secret_ok, secret_detail = secret_runtime_status(
        main_model_view,
        'api_key',
        'main_model.api_key',
        resolve_runtime_secret_from_view=resolve_runtime_secret_from_view,
        secret_required_error_cls=secret_required_error_cls,
        secret_resolution_error_cls=secret_resolution_error_cls,
    )
    if not secret_ok:
        return False, secret_detail
    return (
        is_http_url(base_url),
        f'main_model.base_url={base_url or "missing"}; {secret_detail}',
    )
