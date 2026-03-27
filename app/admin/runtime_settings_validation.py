from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlparse


def _validation_check(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {
        'name': name,
        'ok': bool(ok),
        'detail': str(detail),
    }


def _runtime_text_value(view: Any, field: str) -> str:
    payload = view.payload.get(field) or {}
    return str(payload.get('value') or '').strip()


def _runtime_int_value(view: Any, field: str) -> int | None:
    payload = view.payload.get(field) or {}
    value = payload.get('value')
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _runtime_float_value(view: Any, field: str) -> float | None:
    payload = view.payload.get(field) or {}
    value = payload.get('value')
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_http_url(value: str) -> bool:
    parsed = urlparse(str(value or '').strip())
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)


def _resolve_app_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parents[1] / path


def validate_runtime_section(
    section: str,
    patch_payload: Mapping[str, Any] | None = None,
    *,
    fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None = None,
    candidate_runtime_section: Callable[..., Any],
    resolve_runtime_secret_from_view: Callable[[Any, str], Any],
    secret_required_error_cls: type[Exception],
    secret_resolution_error_cls: type[Exception],
    config_module: Any,
) -> dict[str, Any]:
    view = candidate_runtime_section(section, patch_payload=patch_payload, fetcher=fetcher)
    checks: list[dict[str, Any]] = []

    if section == 'main_model':
        base_url = _runtime_text_value(view, 'base_url')
        model = _runtime_text_value(view, 'model')
        temperature = _runtime_float_value(view, 'temperature')
        top_p = _runtime_float_value(view, 'top_p')
        try:
            api_key_secret = resolve_runtime_secret_from_view(view, 'api_key')
            api_key_ok = bool(str(api_key_secret.value).strip())
            api_key_detail = f'main_model.api_key available from {api_key_secret.source}'
        except (secret_required_error_cls, secret_resolution_error_cls) as exc:
            api_key_ok = False
            api_key_detail = str(exc)
        checks.extend(
            (
                _validation_check('base_url', _is_http_url(base_url), f'base_url={base_url or "missing"}'),
                _validation_check('model', bool(model), f'model={model or "missing"}'),
                _validation_check(
                    'temperature',
                    temperature is not None and 0.0 <= temperature <= 2.0,
                    f'temperature={temperature!r}',
                ),
                _validation_check(
                    'top_p',
                    top_p is not None and 0.0 < top_p <= 1.0,
                    f'top_p={top_p!r}',
                ),
                _validation_check('api_key_runtime', api_key_ok, api_key_detail),
            )
        )
    elif section == 'arbiter_model':
        model = _runtime_text_value(view, 'model')
        timeout_s = _runtime_int_value(view, 'timeout_s')
        temperature = _runtime_float_value(view, 'temperature')
        top_p = _runtime_float_value(view, 'top_p')
        checks.extend(
            (
                _validation_check('model', bool(model), f'model={model or "missing"}'),
                _validation_check('timeout_s', timeout_s is not None and timeout_s > 0, f'timeout_s={timeout_s!r}'),
                _validation_check(
                    'temperature',
                    temperature is not None and 0.0 <= temperature <= 2.0,
                    f'temperature={temperature!r}',
                ),
                _validation_check(
                    'top_p',
                    top_p is not None and 0.0 < top_p <= 1.0,
                    f'top_p={top_p!r}',
                ),
            )
        )
    elif section == 'summary_model':
        model = _runtime_text_value(view, 'model')
        temperature = _runtime_float_value(view, 'temperature')
        top_p = _runtime_float_value(view, 'top_p')
        checks.extend(
            (
                _validation_check('model', bool(model), f'model={model or "missing"}'),
                _validation_check(
                    'temperature',
                    temperature is not None and 0.0 <= temperature <= 2.0,
                    f'temperature={temperature!r}',
                ),
                _validation_check(
                    'top_p',
                    top_p is not None and 0.0 < top_p <= 1.0,
                    f'top_p={top_p!r}',
                ),
            )
        )
    elif section == 'embedding':
        endpoint = _runtime_text_value(view, 'endpoint')
        model = _runtime_text_value(view, 'model')
        dimensions = _runtime_int_value(view, 'dimensions')
        top_k = _runtime_int_value(view, 'top_k')
        try:
            token_secret = resolve_runtime_secret_from_view(view, 'token')
            token_ok = bool(str(token_secret.value).strip())
            token_detail = f'embedding.token available from {token_secret.source}'
        except (secret_required_error_cls, secret_resolution_error_cls) as exc:
            token_ok = False
            token_detail = str(exc)
        checks.extend(
            (
                _validation_check('endpoint', _is_http_url(endpoint), f'endpoint={endpoint or "missing"}'),
                _validation_check('model', bool(model), f'model={model or "missing"}'),
                _validation_check('dimensions', dimensions is not None and dimensions > 0, f'dimensions={dimensions!r}'),
                _validation_check('top_k', top_k is not None and top_k > 0, f'top_k={top_k!r}'),
                _validation_check('token_runtime', token_ok, token_detail),
            )
        )
    elif section == 'database':
        backend = _runtime_text_value(view, 'backend')
        dsn = str(config_module.FRIDA_MEMORY_DB_DSN or '').strip()
        checks.extend(
            (
                _validation_check(
                    'backend',
                    backend == 'postgresql',
                    f'backend={backend or "missing"}',
                ),
                _validation_check(
                    'dsn_transition',
                    bool(dsn),
                    'FRIDA_MEMORY_DB_DSN env bootstrap available'
                    if dsn
                    else 'FRIDA_MEMORY_DB_DSN env bootstrap missing during transition',
                ),
            )
        )
    elif section == 'services':
        searxng_url = _runtime_text_value(view, 'searxng_url')
        searxng_results = _runtime_int_value(view, 'searxng_results')
        crawl4ai_url = _runtime_text_value(view, 'crawl4ai_url')
        crawl4ai_top_n = _runtime_int_value(view, 'crawl4ai_top_n')
        crawl4ai_max_chars = _runtime_int_value(view, 'crawl4ai_max_chars')
        try:
            crawl4ai_token_secret = resolve_runtime_secret_from_view(view, 'crawl4ai_token')
            crawl4ai_token_ok = bool(str(crawl4ai_token_secret.value).strip())
            crawl4ai_token_detail = f'services.crawl4ai_token available from {crawl4ai_token_secret.source}'
        except (secret_required_error_cls, secret_resolution_error_cls) as exc:
            crawl4ai_token_ok = False
            crawl4ai_token_detail = str(exc)
        checks.extend(
            (
                _validation_check('searxng_url', _is_http_url(searxng_url), f'searxng_url={searxng_url or "missing"}'),
                _validation_check(
                    'searxng_results',
                    searxng_results is not None and searxng_results > 0,
                    f'searxng_results={searxng_results!r}',
                ),
                _validation_check('crawl4ai_url', _is_http_url(crawl4ai_url), f'crawl4ai_url={crawl4ai_url or "missing"}'),
                _validation_check(
                    'crawl4ai_top_n',
                    crawl4ai_top_n is not None and crawl4ai_top_n > 0,
                    f'crawl4ai_top_n={crawl4ai_top_n!r}',
                ),
                _validation_check(
                    'crawl4ai_max_chars',
                    crawl4ai_max_chars is not None and crawl4ai_max_chars > 0,
                    f'crawl4ai_max_chars={crawl4ai_max_chars!r}',
                ),
                _validation_check('crawl4ai_token_runtime', crawl4ai_token_ok, crawl4ai_token_detail),
            )
        )
    elif section == 'resources':
        llm_identity_path = _resolve_app_path(_runtime_text_value(view, 'llm_identity_path'))
        user_identity_path = _resolve_app_path(_runtime_text_value(view, 'user_identity_path'))
        checks.extend(
            (
                _validation_check(
                    'llm_identity_path',
                    llm_identity_path.is_file(),
                    f'llm_identity_path={llm_identity_path}',
                ),
                _validation_check(
                    'user_identity_path',
                    user_identity_path.is_file(),
                    f'user_identity_path={user_identity_path}',
                ),
            )
        )
    else:  # pragma: no cover - SECTION_NAMES locks known values
        raise KeyError(f'unknown runtime settings section: {section}')

    return {
        'section': section,
        'source': view.source,
        'source_reason': view.source_reason,
        'valid': all(check['ok'] for check in checks),
        'checks': checks,
    }
