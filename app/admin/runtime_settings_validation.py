from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from agenda import runtime_config as agenda_runtime_config
from core import main_llm_reasoning
from identity import static_identity_paths

_BIBLIO_AGENT_MODES = {'off', 'shadow', 'candidate', 'active'}
_BIBLIO_AGENT_REASONING_EFFORTS = {'none', 'minimal', 'low', 'medium', 'high', 'xhigh'}


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


def _component_referer_valid_or_shared_fallback(component_referer: str, shared_referer: str) -> bool:
    component_value = str(component_referer or '').strip()
    if component_value:
        return _is_http_url(component_value)
    return _is_http_url(shared_referer)


def _resolve_app_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parents[1] / path


def _validation_agent_max_tokens_cap() -> int:
    from core.hermeneutic_node.validation import validation_agent

    return int(validation_agent.MAX_RESPONSE_TOKENS)


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
        referer = _runtime_text_value(view, 'referer')
        referer_llm = _runtime_text_value(view, 'referer_llm')
        referer_web_reformulation = _runtime_text_value(view, 'referer_web_reformulation')
        referer_web_discovery = _runtime_text_value(view, 'referer_web_discovery')
        referer_arbiter = _runtime_text_value(view, 'referer_arbiter')
        referer_identity_extractor = _runtime_text_value(view, 'referer_identity_extractor')
        referer_identity_periodic = _runtime_text_value(view, 'referer_identity_periodic')
        referer_resumer = _runtime_text_value(view, 'referer_resumer')
        referer_stimmung_agent = _runtime_text_value(view, 'referer_stimmung_agent')
        referer_validation_agent = _runtime_text_value(view, 'referer_validation_agent')
        temperature = _runtime_float_value(view, 'temperature')
        top_p = _runtime_float_value(view, 'top_p')
        reasoning_effort = main_llm_reasoning.runtime_payload_reasoning_effort(view.payload)
        raw_reasoning_effort = _runtime_text_value(view, 'reasoning_effort')
        reasoning_effort_valid = raw_reasoning_effort in main_llm_reasoning.SUPPORTED_REASONING_EFFORTS
        reasoning_effort_supported = main_llm_reasoning.model_supports_reasoning_effort(model)
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
                    'referer',
                    (not referer) or _is_http_url(referer),
                    f'referer={referer or "missing"}',
                ),
                _validation_check(
                    'referer_llm',
                    _component_referer_valid_or_shared_fallback(referer_llm, referer),
                    f'referer_llm={referer_llm or "missing"}; shared_referer={referer or "missing"}',
                ),
                _validation_check(
                    'referer_web_reformulation',
                    _component_referer_valid_or_shared_fallback(referer_web_reformulation, referer),
                    (
                        'referer_web_reformulation='
                        f'{referer_web_reformulation or "missing"}; shared_referer={referer or "missing"}'
                    ),
                ),
                _validation_check(
                    'referer_web_discovery',
                    _component_referer_valid_or_shared_fallback(referer_web_discovery, referer),
                    (
                        'referer_web_discovery='
                        f'{referer_web_discovery or "missing"}; shared_referer={referer or "missing"}'
                    ),
                ),
                _validation_check(
                    'referer_arbiter',
                    _component_referer_valid_or_shared_fallback(referer_arbiter, referer),
                    f'referer_arbiter={referer_arbiter or "missing"}; shared_referer={referer or "missing"}',
                ),
                _validation_check(
                    'referer_identity_extractor',
                    _component_referer_valid_or_shared_fallback(referer_identity_extractor, referer),
                    (
                        'referer_identity_extractor='
                        f'{referer_identity_extractor or "missing"}; shared_referer={referer or "missing"}'
                    ),
                ),
                _validation_check(
                    'referer_identity_periodic',
                    _component_referer_valid_or_shared_fallback(referer_identity_periodic, referer),
                    (
                        'referer_identity_periodic='
                        f'{referer_identity_periodic or "missing"}; shared_referer={referer or "missing"}'
                    ),
                ),
                _validation_check(
                    'referer_resumer',
                    _component_referer_valid_or_shared_fallback(referer_resumer, referer),
                    f'referer_resumer={referer_resumer or "missing"}; shared_referer={referer or "missing"}',
                ),
                _validation_check(
                    'referer_stimmung_agent',
                    _component_referer_valid_or_shared_fallback(referer_stimmung_agent, referer),
                    (
                        'referer_stimmung_agent='
                        f'{referer_stimmung_agent or "missing"}; shared_referer={referer or "missing"}'
                    ),
                ),
                _validation_check(
                    'referer_validation_agent',
                    _component_referer_valid_or_shared_fallback(referer_validation_agent, referer),
                    (
                        'referer_validation_agent='
                        f'{referer_validation_agent or "missing"}; shared_referer={referer or "missing"}'
                    ),
                ),
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
                _validation_check(
                    'reasoning_effort',
                    reasoning_effort_valid,
                    (
                        f'reasoning_effort={raw_reasoning_effort or "missing"}; '
                        f'allowed={",".join(main_llm_reasoning.SUPPORTED_REASONING_EFFORTS)}; '
                        f'model={model or "missing"}; '
                        f'effective={reasoning_effort}; '
                        f'model_supported={reasoning_effort_supported}'
                    ),
                ),
                _validation_check('api_key_runtime', api_key_ok, api_key_detail),
            )
        )
    elif section in {'memory_arbiter_model', 'identity_extractor_model', 'identity_periodic_model'}:
        model = _runtime_text_value(view, 'model')
        timeout_s = _runtime_int_value(view, 'timeout_s')
        temperature = _runtime_float_value(view, 'temperature')
        top_p = _runtime_float_value(view, 'top_p')
        max_tokens = _runtime_int_value(view, 'max_tokens')
        main_model_view = candidate_runtime_section('main_model', fetcher=fetcher)
        base_url = _runtime_text_value(main_model_view, 'base_url')
        try:
            api_key_secret = resolve_runtime_secret_from_view(main_model_view, 'api_key')
            shared_transport_ok = _is_http_url(base_url) and bool(str(api_key_secret.value).strip())
            shared_transport_detail = (
                f'main_model.base_url={base_url or "missing"}; '
                f'main_model.api_key available from {api_key_secret.source}'
            )
        except (secret_required_error_cls, secret_resolution_error_cls) as exc:
            shared_transport_ok = False
            shared_transport_detail = str(exc)
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
                _validation_check(
                    'max_tokens',
                    max_tokens is not None and max_tokens > 0,
                    f'max_tokens={max_tokens!r}',
                ),
                _validation_check('shared_transport_runtime', shared_transport_ok, shared_transport_detail),
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
        max_tokens = _runtime_int_value(view, 'max_tokens')
        timeout_s = _runtime_int_value(view, 'timeout_s')
        main_model_view = candidate_runtime_section('main_model', fetcher=fetcher)
        base_url = _runtime_text_value(main_model_view, 'base_url')
        try:
            api_key_secret = resolve_runtime_secret_from_view(main_model_view, 'api_key')
            shared_transport_ok = _is_http_url(base_url) and bool(str(api_key_secret.value).strip())
            shared_transport_detail = (
                f'main_model.base_url={base_url or "missing"}; '
                f'main_model.api_key available from {api_key_secret.source}'
            )
        except (secret_required_error_cls, secret_resolution_error_cls) as exc:
            shared_transport_ok = False
            shared_transport_detail = str(exc)
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
                _validation_check(
                    'max_tokens',
                    max_tokens is not None and max_tokens > 0,
                    f'max_tokens={max_tokens!r}',
                ),
                _validation_check('shared_transport_runtime', shared_transport_ok, shared_transport_detail),
            )
        )
    elif section == 'web_reformulation_model':
        model = _runtime_text_value(view, 'model')
        timeout_s = _runtime_int_value(view, 'timeout_s')
        temperature = _runtime_float_value(view, 'temperature')
        max_tokens = _runtime_int_value(view, 'max_tokens')
        main_model_view = candidate_runtime_section('main_model', fetcher=fetcher)
        base_url = _runtime_text_value(main_model_view, 'base_url')
        try:
            api_key_secret = resolve_runtime_secret_from_view(main_model_view, 'api_key')
            shared_transport_ok = _is_http_url(base_url) and bool(str(api_key_secret.value).strip())
            shared_transport_detail = (
                f'main_model.base_url={base_url or "missing"}; '
                f'main_model.api_key available from {api_key_secret.source}'
            )
        except (secret_required_error_cls, secret_resolution_error_cls) as exc:
            shared_transport_ok = False
            shared_transport_detail = str(exc)
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
                    'max_tokens',
                    max_tokens is not None and max_tokens > 0,
                    f'max_tokens={max_tokens!r}',
                ),
                _validation_check('shared_transport_runtime', shared_transport_ok, shared_transport_detail),
            )
        )
    elif section in {'stimmung_agent_model', 'validation_agent_model'}:
        primary_model = _runtime_text_value(view, 'primary_model')
        fallback_model = _runtime_text_value(view, 'fallback_model')
        timeout_s = _runtime_int_value(view, 'timeout_s')
        temperature = _runtime_float_value(view, 'temperature')
        top_p = _runtime_float_value(view, 'top_p')
        max_tokens = _runtime_int_value(view, 'max_tokens')
        max_tokens_cap = _validation_agent_max_tokens_cap() if section == 'validation_agent_model' else None
        max_tokens_ok = max_tokens is not None and max_tokens > 0
        max_tokens_detail = f'max_tokens={max_tokens!r}'
        if max_tokens_cap is not None:
            max_tokens_ok = max_tokens_ok and max_tokens <= max_tokens_cap
            max_tokens_detail = f'max_tokens={max_tokens!r}; max_allowed={max_tokens_cap}'
        main_model_view = candidate_runtime_section('main_model', fetcher=fetcher)
        base_url = _runtime_text_value(main_model_view, 'base_url')
        try:
            api_key_secret = resolve_runtime_secret_from_view(main_model_view, 'api_key')
            shared_transport_ok = _is_http_url(base_url) and bool(str(api_key_secret.value).strip())
            shared_transport_detail = (
                f'main_model.base_url={base_url or "missing"}; '
                f'main_model.api_key available from {api_key_secret.source}'
            )
        except (secret_required_error_cls, secret_resolution_error_cls) as exc:
            shared_transport_ok = False
            shared_transport_detail = str(exc)
        checks.extend(
            (
                _validation_check('primary_model', bool(primary_model), f'primary_model={primary_model or "missing"}'),
                _validation_check('fallback_model', bool(fallback_model), f'fallback_model={fallback_model or "missing"}'),
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
                _validation_check('max_tokens', max_tokens_ok, max_tokens_detail),
                _validation_check('shared_transport_runtime', shared_transport_ok, shared_transport_detail),
            )
        )
    elif section == 'biblio_librarian_agent':
        mode = _runtime_text_value(view, 'mode')
        primary_model = _runtime_text_value(view, 'primary_model')
        timeout_s = _runtime_int_value(view, 'timeout_s')
        temperature = _runtime_float_value(view, 'temperature')
        top_p = _runtime_float_value(view, 'top_p')
        max_tokens = _runtime_int_value(view, 'max_tokens')
        max_tool_calls = _runtime_int_value(view, 'max_tool_calls')
        max_model_calls = _runtime_int_value(view, 'max_model_calls')
        max_recent_turns = _runtime_int_value(view, 'max_recent_turns')
        reasoning_effort = _runtime_text_value(view, 'reasoning_effort')
        main_model_view = candidate_runtime_section('main_model', fetcher=fetcher)
        base_url = _runtime_text_value(main_model_view, 'base_url')
        try:
            api_key_secret = resolve_runtime_secret_from_view(main_model_view, 'api_key')
            shared_transport_ok = _is_http_url(base_url) and bool(str(api_key_secret.value).strip())
            shared_transport_detail = (
                f'main_model.base_url={base_url or "missing"}; '
                f'main_model.api_key available from {api_key_secret.source}'
            )
        except (secret_required_error_cls, secret_resolution_error_cls) as exc:
            shared_transport_ok = False
            shared_transport_detail = str(exc)
        checks.extend(
            (
                _validation_check('mode', mode in _BIBLIO_AGENT_MODES, f'mode={mode or "missing"}'),
                _validation_check('primary_model', bool(primary_model), f'primary_model={primary_model or "missing"}'),
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
                _validation_check('max_tokens', max_tokens is not None and max_tokens > 0, f'max_tokens={max_tokens!r}'),
                _validation_check(
                    'max_tool_calls',
                    max_tool_calls is not None and max_tool_calls > 0,
                    f'max_tool_calls={max_tool_calls!r}',
                ),
                _validation_check(
                    'max_model_calls',
                    max_model_calls is not None and max_model_calls > 0,
                    f'max_model_calls={max_model_calls!r}',
                ),
                _validation_check(
                    'max_recent_turns',
                    max_recent_turns is not None and max_recent_turns >= 0,
                    f'max_recent_turns={max_recent_turns!r}',
                ),
                _validation_check(
                    'reasoning_effort',
                    reasoning_effort in _BIBLIO_AGENT_REASONING_EFFORTS,
                    (
                        f'reasoning_effort={reasoning_effort or "missing"}; '
                        f'allowed={",".join(sorted(_BIBLIO_AGENT_REASONING_EFFORTS))}'
                    ),
                ),
                _validation_check('shared_transport_runtime', shared_transport_ok, shared_transport_detail),
            )
        )
    elif section == 'agenda_agent':
        mode = agenda_runtime_config.normalize_agent_mode(_runtime_text_value(view, 'mode'))
        caldav_account = _runtime_text_value(view, 'caldav_account')
        secret_payload = view.payload.get(agenda_runtime_config.CALDAV_APP_PASSWORD_FIELD) or {}
        secret_configured = bool(secret_payload.get('is_set')) if isinstance(secret_payload, Mapping) else False
        secret_required = mode != 'off'
        checks.extend(
            (
                _validation_check(
                    'mode',
                    mode in agenda_runtime_config.AGENDA_AGENT_MODES,
                    f'mode={mode or "missing"}; allowed={",".join(agenda_runtime_config.AGENDA_AGENT_MODES)}',
                ),
                _validation_check(
                    'caldav_identity',
                    caldav_account == agenda_runtime_config.CALDAV_ACCOUNT_V1,
                    (
                        f'caldav_account={caldav_account or "missing"}; '
                        f'expected={agenda_runtime_config.CALDAV_ACCOUNT_V1}; '
                        'service_account=false'
                    ),
                ),
                _validation_check(
                    'caldav_app_password_presence',
                    (not secret_required) or secret_configured,
                    (
                        f'configured={secret_configured}; '
                        f'required_for_mode={secret_required}; '
                        'value=redacted'
                    ),
                ),
                _validation_check(
                    'caldav_runtime_access',
                    True,
                    'lot2 configuration only; caldav_access=false; nextcloud_access=false',
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
        crawl4ai_explicit_url_max_chars = _runtime_int_value(view, 'crawl4ai_explicit_url_max_chars')
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
                _validation_check(
                    'crawl4ai_explicit_url_max_chars',
                    crawl4ai_explicit_url_max_chars is not None
                    and crawl4ai_explicit_url_max_chars > 0
                    and (
                        crawl4ai_max_chars is None
                        or crawl4ai_explicit_url_max_chars >= crawl4ai_max_chars
                    ),
                    (
                        'crawl4ai_explicit_url_max_chars='
                        f'{crawl4ai_explicit_url_max_chars!r}; '
                        f'crawl4ai_max_chars={crawl4ai_max_chars!r}'
                    ),
                ),
                _validation_check('crawl4ai_token_runtime', crawl4ai_token_ok, crawl4ai_token_detail),
            )
        )
    elif section == 'resources':
        llm_identity_path = static_identity_paths.resolve_static_identity_path(
            _runtime_text_value(view, 'llm_identity_path')
        )
        user_identity_path = static_identity_paths.resolve_static_identity_path(
            _runtime_text_value(view, 'user_identity_path')
        )
        checks.extend(
            (
                _validation_check(
                    'llm_identity_path',
                    llm_identity_path.exists,
                    llm_identity_path.validation_detail('llm_identity_path'),
                ),
                _validation_check(
                    'user_identity_path',
                    user_identity_path.exists,
                    user_identity_path.validation_detail('user_identity_path'),
                ),
            )
        )
    elif section == 'identity_governance':
        identity_min_confidence = _runtime_float_value(view, 'IDENTITY_MIN_CONFIDENCE')
        identity_defer_min_confidence = _runtime_float_value(view, 'IDENTITY_DEFER_MIN_CONFIDENCE')
        identity_min_recurrence = _runtime_int_value(view, 'IDENTITY_MIN_RECURRENCE_FOR_DURABLE')
        identity_recurrence_window_days = _runtime_int_value(view, 'IDENTITY_RECURRENCE_WINDOW_DAYS')
        identity_min_distinct_conversations = _runtime_int_value(
            view,
            'IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS',
        )
        identity_min_time_gap_hours = _runtime_int_value(view, 'IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS')
        context_hints_max_items = _runtime_int_value(view, 'CONTEXT_HINTS_MAX_ITEMS')
        context_hints_max_tokens = _runtime_int_value(view, 'CONTEXT_HINTS_MAX_TOKENS')
        context_hints_max_age_days = _runtime_int_value(view, 'CONTEXT_HINTS_MAX_AGE_DAYS')
        context_hints_min_confidence = _runtime_float_value(view, 'CONTEXT_HINTS_MIN_CONFIDENCE')
        max_context_tokens = int(getattr(config_module, 'MAX_TOKENS', 0) or 0)
        checks.extend(
            (
                _validation_check(
                    'IDENTITY_MIN_CONFIDENCE',
                    identity_min_confidence is not None and 0.0 <= identity_min_confidence <= 1.0,
                    f'IDENTITY_MIN_CONFIDENCE={identity_min_confidence!r}',
                ),
                _validation_check(
                    'IDENTITY_DEFER_MIN_CONFIDENCE',
                    identity_defer_min_confidence is not None
                    and 0.0 <= identity_defer_min_confidence <= 1.0
                    and (
                        identity_min_confidence is None
                        or identity_defer_min_confidence <= identity_min_confidence
                    ),
                    (
                        'IDENTITY_DEFER_MIN_CONFIDENCE='
                        f'{identity_defer_min_confidence!r}; '
                        f'IDENTITY_MIN_CONFIDENCE={identity_min_confidence!r}'
                    ),
                ),
                _validation_check(
                    'IDENTITY_MIN_RECURRENCE_FOR_DURABLE',
                    identity_min_recurrence is not None
                    and 1 <= identity_min_recurrence <= 10
                    and (
                        identity_min_distinct_conversations is None
                        or identity_min_recurrence >= identity_min_distinct_conversations
                    ),
                    (
                        'IDENTITY_MIN_RECURRENCE_FOR_DURABLE='
                        f'{identity_min_recurrence!r}; '
                        'IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS='
                        f'{identity_min_distinct_conversations!r}'
                    ),
                ),
                _validation_check(
                    'IDENTITY_RECURRENCE_WINDOW_DAYS',
                    identity_recurrence_window_days is not None and 1 <= identity_recurrence_window_days <= 365,
                    f'IDENTITY_RECURRENCE_WINDOW_DAYS={identity_recurrence_window_days!r}',
                ),
                _validation_check(
                    'IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS',
                    identity_min_distinct_conversations is not None
                    and 1 <= identity_min_distinct_conversations <= 10
                    and (
                        identity_min_recurrence is None
                        or identity_min_distinct_conversations <= identity_min_recurrence
                    ),
                    (
                        'IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS='
                        f'{identity_min_distinct_conversations!r}; '
                        'IDENTITY_MIN_RECURRENCE_FOR_DURABLE='
                        f'{identity_min_recurrence!r}'
                    ),
                ),
                _validation_check(
                    'IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS',
                    identity_min_time_gap_hours is not None and 1 <= identity_min_time_gap_hours <= 168,
                    f'IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS={identity_min_time_gap_hours!r}',
                ),
                _validation_check(
                    'CONTEXT_HINTS_MAX_ITEMS',
                    context_hints_max_items is not None and 1 <= context_hints_max_items <= 10,
                    f'CONTEXT_HINTS_MAX_ITEMS={context_hints_max_items!r}',
                ),
                _validation_check(
                    'CONTEXT_HINTS_MAX_TOKENS',
                    context_hints_max_tokens is not None
                    and 1 <= context_hints_max_tokens <= max_context_tokens,
                    f'CONTEXT_HINTS_MAX_TOKENS={context_hints_max_tokens!r}; max_allowed={max_context_tokens}',
                ),
                _validation_check(
                    'CONTEXT_HINTS_MAX_AGE_DAYS',
                    context_hints_max_age_days is not None and 1 <= context_hints_max_age_days <= 365,
                    f'CONTEXT_HINTS_MAX_AGE_DAYS={context_hints_max_age_days!r}',
                ),
                _validation_check(
                    'CONTEXT_HINTS_MIN_CONFIDENCE',
                    context_hints_min_confidence is not None and 0.0 <= context_hints_min_confidence <= 1.0,
                    f'CONTEXT_HINTS_MIN_CONFIDENCE={context_hints_min_confidence!r}',
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
