from __future__ import annotations

from typing import Any, Callable, Mapping

from admin import runtime_settings_validation_support as support
from agenda import runtime_config as agenda_runtime_config
from identity import static_identity_paths


PLATFORM_SECTIONS = frozenset(
    {
        'agenda_agent',
        'embedding',
        'database',
        'services',
        'resources',
        'identity_governance',
    }
)


def _validate_agenda_agent(view: Any) -> list[dict[str, Any]]:
    mode = agenda_runtime_config.normalize_agent_mode(support.runtime_text_value(view, 'mode'))
    caldav_account = support.runtime_text_value(view, 'caldav_account')
    secret_payload = view.payload.get(agenda_runtime_config.CALDAV_APP_PASSWORD_FIELD) or {}
    secret_configured = bool(secret_payload.get('is_set')) if isinstance(secret_payload, Mapping) else False
    secret_required = mode != 'off'
    return [
        support.validation_check(
            'mode',
            mode in agenda_runtime_config.AGENDA_AGENT_MODES,
            f'mode={mode or "missing"}; allowed={",".join(agenda_runtime_config.AGENDA_AGENT_MODES)}',
        ),
        support.validation_check(
            'caldav_identity',
            caldav_account == agenda_runtime_config.CALDAV_ACCOUNT_V1,
            (
                f'caldav_account={caldav_account or "missing"}; '
                f'expected={agenda_runtime_config.CALDAV_ACCOUNT_V1}; '
                'service_account=false'
            ),
        ),
        support.validation_check(
            'caldav_app_password_presence',
            (not secret_required) or secret_configured,
            (
                f'configured={secret_configured}; '
                f'required_for_mode={secret_required}; '
                'value=redacted'
            ),
        ),
        support.validation_check(
            'caldav_runtime_access',
            True,
            'lot2 configuration only; caldav_access=false; nextcloud_access=false',
        ),
    ]


def _validate_embedding(
    view: Any,
    *,
    resolve_runtime_secret_from_view: Callable[[Any, str], Any],
    secret_required_error_cls: type[Exception],
    secret_resolution_error_cls: type[Exception],
) -> list[dict[str, Any]]:
    endpoint = support.runtime_text_value(view, 'endpoint')
    model = support.runtime_text_value(view, 'model')
    dimensions = support.runtime_int_value(view, 'dimensions')
    top_k = support.runtime_int_value(view, 'top_k')
    token_ok, token_detail = support.secret_runtime_status(
        view,
        'token',
        'embedding.token',
        resolve_runtime_secret_from_view=resolve_runtime_secret_from_view,
        secret_required_error_cls=secret_required_error_cls,
        secret_resolution_error_cls=secret_resolution_error_cls,
    )
    return [
        support.validation_check(
            'endpoint',
            support.is_http_url(endpoint),
            f'endpoint={endpoint or "missing"}',
        ),
        support.validation_check('model', bool(model), f'model={model or "missing"}'),
        support.validation_check(
            'dimensions',
            dimensions is not None and dimensions > 0,
            f'dimensions={dimensions!r}',
        ),
        support.validation_check('top_k', top_k is not None and top_k > 0, f'top_k={top_k!r}'),
        support.validation_check('token_runtime', token_ok, token_detail),
    ]


def _validate_database(view: Any, *, config_module: Any) -> list[dict[str, Any]]:
    backend = support.runtime_text_value(view, 'backend')
    dsn = str(config_module.FRIDA_MEMORY_DB_DSN or '').strip()
    return [
        support.validation_check(
            'backend',
            backend == 'postgresql',
            f'backend={backend or "missing"}',
        ),
        support.validation_check(
            'dsn_transition',
            bool(dsn),
            (
                'FRIDA_MEMORY_DB_DSN env bootstrap available'
                if dsn
                else 'FRIDA_MEMORY_DB_DSN env bootstrap missing during transition'
            ),
        ),
    ]


def _validate_services(
    view: Any,
    *,
    resolve_runtime_secret_from_view: Callable[[Any, str], Any],
    secret_required_error_cls: type[Exception],
    secret_resolution_error_cls: type[Exception],
) -> list[dict[str, Any]]:
    searxng_url = support.runtime_text_value(view, 'searxng_url')
    searxng_results = support.runtime_int_value(view, 'searxng_results')
    crawl4ai_url = support.runtime_text_value(view, 'crawl4ai_url')
    crawl4ai_top_n = support.runtime_int_value(view, 'crawl4ai_top_n')
    crawl4ai_max_chars = support.runtime_int_value(view, 'crawl4ai_max_chars')
    crawl4ai_explicit_url_max_chars = support.runtime_int_value(
        view,
        'crawl4ai_explicit_url_max_chars',
    )
    crawl4ai_token_ok, crawl4ai_token_detail = support.secret_runtime_status(
        view,
        'crawl4ai_token',
        'services.crawl4ai_token',
        resolve_runtime_secret_from_view=resolve_runtime_secret_from_view,
        secret_required_error_cls=secret_required_error_cls,
        secret_resolution_error_cls=secret_resolution_error_cls,
    )
    return [
        support.validation_check(
            'searxng_url',
            support.is_http_url(searxng_url),
            f'searxng_url={searxng_url or "missing"}',
        ),
        support.validation_check(
            'searxng_results',
            searxng_results is not None and searxng_results > 0,
            f'searxng_results={searxng_results!r}',
        ),
        support.validation_check(
            'crawl4ai_url',
            support.is_http_url(crawl4ai_url),
            f'crawl4ai_url={crawl4ai_url or "missing"}',
        ),
        support.validation_check(
            'crawl4ai_top_n',
            crawl4ai_top_n is not None and crawl4ai_top_n > 0,
            f'crawl4ai_top_n={crawl4ai_top_n!r}',
        ),
        support.validation_check(
            'crawl4ai_max_chars',
            crawl4ai_max_chars is not None and crawl4ai_max_chars > 0,
            f'crawl4ai_max_chars={crawl4ai_max_chars!r}',
        ),
        support.validation_check(
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
        support.validation_check(
            'crawl4ai_token_runtime',
            crawl4ai_token_ok,
            crawl4ai_token_detail,
        ),
    ]


def _validate_resources(view: Any) -> list[dict[str, Any]]:
    llm_identity_path = static_identity_paths.resolve_static_identity_path(
        support.runtime_text_value(view, 'llm_identity_path')
    )
    user_identity_path = static_identity_paths.resolve_static_identity_path(
        support.runtime_text_value(view, 'user_identity_path')
    )
    return [
        support.validation_check(
            'llm_identity_path',
            llm_identity_path.exists,
            llm_identity_path.validation_detail('llm_identity_path'),
        ),
        support.validation_check(
            'user_identity_path',
            user_identity_path.exists,
            user_identity_path.validation_detail('user_identity_path'),
        ),
    ]


def _validate_identity_governance(view: Any, *, config_module: Any) -> list[dict[str, Any]]:
    identity_min_confidence = support.runtime_float_value(view, 'IDENTITY_MIN_CONFIDENCE')
    identity_defer_min_confidence = support.runtime_float_value(
        view,
        'IDENTITY_DEFER_MIN_CONFIDENCE',
    )
    identity_min_recurrence = support.runtime_int_value(
        view,
        'IDENTITY_MIN_RECURRENCE_FOR_DURABLE',
    )
    identity_recurrence_window_days = support.runtime_int_value(
        view,
        'IDENTITY_RECURRENCE_WINDOW_DAYS',
    )
    identity_min_distinct_conversations = support.runtime_int_value(
        view,
        'IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS',
    )
    identity_min_time_gap_hours = support.runtime_int_value(
        view,
        'IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS',
    )
    context_hints_max_items = support.runtime_int_value(view, 'CONTEXT_HINTS_MAX_ITEMS')
    context_hints_max_tokens = support.runtime_int_value(view, 'CONTEXT_HINTS_MAX_TOKENS')
    context_hints_max_age_days = support.runtime_int_value(view, 'CONTEXT_HINTS_MAX_AGE_DAYS')
    context_hints_min_confidence = support.runtime_float_value(
        view,
        'CONTEXT_HINTS_MIN_CONFIDENCE',
    )
    max_context_tokens = int(getattr(config_module, 'MAX_TOKENS', 0) or 0)
    return [
        support.validation_check(
            'IDENTITY_MIN_CONFIDENCE',
            identity_min_confidence is not None and 0.0 <= identity_min_confidence <= 1.0,
            f'IDENTITY_MIN_CONFIDENCE={identity_min_confidence!r}',
        ),
        support.validation_check(
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
        support.validation_check(
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
        support.validation_check(
            'IDENTITY_RECURRENCE_WINDOW_DAYS',
            identity_recurrence_window_days is not None
            and 1 <= identity_recurrence_window_days <= 365,
            f'IDENTITY_RECURRENCE_WINDOW_DAYS={identity_recurrence_window_days!r}',
        ),
        support.validation_check(
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
        support.validation_check(
            'IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS',
            identity_min_time_gap_hours is not None and 1 <= identity_min_time_gap_hours <= 168,
            f'IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS={identity_min_time_gap_hours!r}',
        ),
        support.validation_check(
            'CONTEXT_HINTS_MAX_ITEMS',
            context_hints_max_items is not None and 1 <= context_hints_max_items <= 10,
            f'CONTEXT_HINTS_MAX_ITEMS={context_hints_max_items!r}',
        ),
        support.validation_check(
            'CONTEXT_HINTS_MAX_TOKENS',
            context_hints_max_tokens is not None
            and 1 <= context_hints_max_tokens <= max_context_tokens,
            f'CONTEXT_HINTS_MAX_TOKENS={context_hints_max_tokens!r}; max_allowed={max_context_tokens}',
        ),
        support.validation_check(
            'CONTEXT_HINTS_MAX_AGE_DAYS',
            context_hints_max_age_days is not None and 1 <= context_hints_max_age_days <= 365,
            f'CONTEXT_HINTS_MAX_AGE_DAYS={context_hints_max_age_days!r}',
        ),
        support.validation_check(
            'CONTEXT_HINTS_MIN_CONFIDENCE',
            context_hints_min_confidence is not None and 0.0 <= context_hints_min_confidence <= 1.0,
            f'CONTEXT_HINTS_MIN_CONFIDENCE={context_hints_min_confidence!r}',
        ),
    ]


def validate_platform_section(
    section: str,
    view: Any,
    *,
    fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None,
    candidate_runtime_section: Callable[..., Any],
    resolve_runtime_secret_from_view: Callable[[Any, str], Any],
    secret_required_error_cls: type[Exception],
    secret_resolution_error_cls: type[Exception],
    config_module: Any,
) -> list[dict[str, Any]]:
    del fetcher, candidate_runtime_section
    if section == 'agenda_agent':
        return _validate_agenda_agent(view)
    if section == 'embedding':
        return _validate_embedding(
            view,
            resolve_runtime_secret_from_view=resolve_runtime_secret_from_view,
            secret_required_error_cls=secret_required_error_cls,
            secret_resolution_error_cls=secret_resolution_error_cls,
        )
    if section == 'database':
        return _validate_database(view, config_module=config_module)
    if section == 'services':
        return _validate_services(
            view,
            resolve_runtime_secret_from_view=resolve_runtime_secret_from_view,
            secret_required_error_cls=secret_required_error_cls,
            secret_resolution_error_cls=secret_resolution_error_cls,
        )
    if section == 'resources':
        return _validate_resources(view)
    if section == 'identity_governance':
        return _validate_identity_governance(view, config_module=config_module)
    raise KeyError(f'unknown platform runtime settings section: {section}')
