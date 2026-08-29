from __future__ import annotations

from typing import Any, Callable

from admin import runtime_settings_validation_support as support
from core import main_llm_reasoning


MODEL_SECTIONS = frozenset(
    {
        'main_model',
        'memory_arbiter_model',
        'identity_extractor_model',
        'identity_periodic_model',
        'arbiter_model',
        'summary_model',
        'web_reformulation_model',
        'stimmung_agent_model',
        'validation_agent_model',
        'biblio_librarian_agent',
    }
)

_BIBLIO_AGENT_MODES = {'off', 'shadow', 'candidate', 'active'}
_BIBLIO_AGENT_REASONING_EFFORTS = {'none', 'minimal', 'low', 'medium', 'high', 'xhigh'}


def _validation_agent_max_tokens_cap() -> int:
    from core.hermeneutic_node.validation import validation_agent

    return int(validation_agent.MAX_RESPONSE_TOKENS)


def _shared_transport_check(
    *,
    fetcher: Callable[[], dict[str, dict[str, dict[str, Any]]]] | None,
    candidate_runtime_section: Callable[..., Any],
    resolve_runtime_secret_from_view: Callable[[Any, str], Any],
    secret_required_error_cls: type[Exception],
    secret_resolution_error_cls: type[Exception],
) -> dict[str, Any]:
    ok, detail = support.shared_openrouter_transport_status(
        fetcher=fetcher,
        candidate_runtime_section=candidate_runtime_section,
        resolve_runtime_secret_from_view=resolve_runtime_secret_from_view,
        secret_required_error_cls=secret_required_error_cls,
        secret_resolution_error_cls=secret_resolution_error_cls,
    )
    return support.validation_check('shared_transport_runtime', ok, detail)


def _validate_main_model(
    view: Any,
    *,
    resolve_runtime_secret_from_view: Callable[[Any, str], Any],
    secret_required_error_cls: type[Exception],
    secret_resolution_error_cls: type[Exception],
) -> list[dict[str, Any]]:
    base_url = support.runtime_text_value(view, 'base_url')
    model = support.runtime_text_value(view, 'model')
    referer = support.runtime_text_value(view, 'referer')
    component_referers = (
        ('referer_llm', support.runtime_text_value(view, 'referer_llm')),
        (
            'referer_web_reformulation',
            support.runtime_text_value(view, 'referer_web_reformulation'),
        ),
        ('referer_web_discovery', support.runtime_text_value(view, 'referer_web_discovery')),
        ('referer_arbiter', support.runtime_text_value(view, 'referer_arbiter')),
        (
            'referer_identity_extractor',
            support.runtime_text_value(view, 'referer_identity_extractor'),
        ),
        (
            'referer_identity_periodic',
            support.runtime_text_value(view, 'referer_identity_periodic'),
        ),
        ('referer_resumer', support.runtime_text_value(view, 'referer_resumer')),
        (
            'referer_stimmung_agent',
            support.runtime_text_value(view, 'referer_stimmung_agent'),
        ),
        (
            'referer_validation_agent',
            support.runtime_text_value(view, 'referer_validation_agent'),
        ),
    )
    temperature = support.runtime_float_value(view, 'temperature')
    top_p = support.runtime_float_value(view, 'top_p')
    reasoning_effort = main_llm_reasoning.runtime_payload_reasoning_effort(view.payload)
    raw_reasoning_effort = support.runtime_text_value(view, 'reasoning_effort')
    reasoning_effort_valid = raw_reasoning_effort in main_llm_reasoning.SUPPORTED_REASONING_EFFORTS
    reasoning_effort_supported = main_llm_reasoning.model_supports_reasoning_effort(model)
    api_key_ok, api_key_detail = support.secret_runtime_status(
        view,
        'api_key',
        'main_model.api_key',
        resolve_runtime_secret_from_view=resolve_runtime_secret_from_view,
        secret_required_error_cls=secret_required_error_cls,
        secret_resolution_error_cls=secret_resolution_error_cls,
    )

    checks = [
        support.validation_check(
            'base_url',
            support.is_http_url(base_url),
            f'base_url={base_url or "missing"}',
        ),
        support.validation_check('model', bool(model), f'model={model or "missing"}'),
        support.validation_check(
            'referer',
            (not referer) or support.is_http_url(referer),
            f'referer={referer or "missing"}',
        ),
    ]
    checks.extend(
        support.validation_check(
            name,
            support.component_referer_valid_or_shared_fallback(value, referer),
            f'{name}={value or "missing"}; shared_referer={referer or "missing"}',
        )
        for name, value in component_referers
    )
    checks.extend(
        (
            support.validation_check(
                'temperature',
                temperature is not None and 0.0 <= temperature <= 2.0,
                f'temperature={temperature!r}',
            ),
            support.validation_check(
                'top_p',
                top_p is not None and 0.0 < top_p <= 1.0,
                f'top_p={top_p!r}',
            ),
            support.validation_check(
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
            support.validation_check('api_key_runtime', api_key_ok, api_key_detail),
        )
    )
    return checks


def _validate_single_model(
    section: str,
    view: Any,
    *,
    shared_transport_check: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    model = support.runtime_text_value(view, 'model')
    timeout_s = support.runtime_int_value(view, 'timeout_s')
    temperature = support.runtime_float_value(view, 'temperature')
    top_p = support.runtime_float_value(view, 'top_p')
    max_tokens = support.runtime_int_value(view, 'max_tokens')
    checks = [
        support.validation_check('model', bool(model), f'model={model or "missing"}'),
        support.validation_check(
            'timeout_s',
            timeout_s is not None and timeout_s > 0,
            f'timeout_s={timeout_s!r}',
        ),
        support.validation_check(
            'temperature',
            temperature is not None and 0.0 <= temperature <= 2.0,
            f'temperature={temperature!r}',
        ),
    ]
    if section != 'web_reformulation_model':
        checks.append(
            support.validation_check(
                'top_p',
                top_p is not None and 0.0 < top_p <= 1.0,
                f'top_p={top_p!r}',
            )
        )
    if section != 'arbiter_model':
        checks.append(
            support.validation_check(
                'max_tokens',
                max_tokens is not None and max_tokens > 0,
                f'max_tokens={max_tokens!r}',
            )
        )
    if shared_transport_check is not None:
        checks.append(shared_transport_check)
    return checks


def _validate_dual_model_agent(
    section: str,
    view: Any,
    *,
    shared_transport_check: dict[str, Any],
) -> list[dict[str, Any]]:
    primary_model = support.runtime_text_value(view, 'primary_model')
    fallback_model = support.runtime_text_value(view, 'fallback_model')
    timeout_s = support.runtime_int_value(view, 'timeout_s')
    temperature = support.runtime_float_value(view, 'temperature')
    top_p = support.runtime_float_value(view, 'top_p')
    max_tokens = support.runtime_int_value(view, 'max_tokens')
    reasoning_effort = support.runtime_text_value(view, 'reasoning_effort')
    max_tokens_cap = _validation_agent_max_tokens_cap() if section == 'validation_agent_model' else None
    max_tokens_ok = max_tokens is not None and max_tokens > 0
    max_tokens_detail = f'max_tokens={max_tokens!r}'
    if max_tokens_cap is not None:
        max_tokens_ok = max_tokens_ok and max_tokens <= max_tokens_cap
        max_tokens_detail = f'max_tokens={max_tokens!r}; max_allowed={max_tokens_cap}'
    checks = [
        support.validation_check(
            'primary_model',
            bool(primary_model),
            f'primary_model={primary_model or "missing"}',
        ),
        support.validation_check(
            'fallback_model',
            bool(fallback_model),
            f'fallback_model={fallback_model or "missing"}',
        ),
        support.validation_check(
            'timeout_s',
            timeout_s is not None and timeout_s > 0,
            f'timeout_s={timeout_s!r}',
        ),
        support.validation_check(
            'temperature',
            temperature is not None and 0.0 <= temperature <= 2.0,
            f'temperature={temperature!r}',
        ),
        support.validation_check(
            'top_p',
            top_p is not None and 0.0 < top_p <= 1.0,
            f'top_p={top_p!r}',
        ),
        support.validation_check('max_tokens', max_tokens_ok, max_tokens_detail),
        shared_transport_check,
    ]
    if section == 'validation_agent_model':
        from core.hermeneutic_node.validation import validation_transport

        active_policy = (
            primary_model == validation_transport.PRIMARY_MODEL
            and fallback_model == validation_transport.FALLBACK_MODEL
            and timeout_s == validation_transport.REQUEST_TIMEOUT_S
            and temperature == 0.0
            and top_p == 1.0
            and max_tokens == validation_transport.PRIMARY_MAX_TOKENS
            and reasoning_effort == validation_transport.PRIMARY_REASONING_EFFORT
        )
        rollback_policy = (
            primary_model == validation_transport.LEGACY_PRIMARY_MODEL
            and fallback_model == validation_transport.FALLBACK_MODEL
            and timeout_s == validation_transport.REQUEST_TIMEOUT_S
            and temperature == 0.0
            and top_p == 1.0
            and max_tokens == validation_transport.LEGACY_MAX_TOKENS
            and reasoning_effort == validation_transport.PRIMARY_REASONING_EFFORT
        )
        checks.extend(
            (
                support.validation_check(
                    'reasoning_effort',
                    reasoning_effort == validation_transport.PRIMARY_REASONING_EFFORT,
                    f'reasoning_effort={reasoning_effort or "missing"}; required=medium',
                ),
                support.validation_check(
                    'request_policy',
                    active_policy or rollback_policy,
                    'validation request policy must match active cutover or bounded rollback',
                ),
            )
        )
    return checks


def _validate_biblio_agent(
    view: Any,
    *,
    shared_transport_check: dict[str, Any],
) -> list[dict[str, Any]]:
    mode = support.runtime_text_value(view, 'mode')
    primary_model = support.runtime_text_value(view, 'primary_model')
    timeout_s = support.runtime_int_value(view, 'timeout_s')
    temperature = support.runtime_float_value(view, 'temperature')
    top_p = support.runtime_float_value(view, 'top_p')
    max_tokens = support.runtime_int_value(view, 'max_tokens')
    max_tool_calls = support.runtime_int_value(view, 'max_tool_calls')
    max_model_calls = support.runtime_int_value(view, 'max_model_calls')
    max_recent_turns = support.runtime_int_value(view, 'max_recent_turns')
    reasoning_effort = support.runtime_text_value(view, 'reasoning_effort')
    return [
        support.validation_check('mode', mode in _BIBLIO_AGENT_MODES, f'mode={mode or "missing"}'),
        support.validation_check(
            'primary_model',
            bool(primary_model),
            f'primary_model={primary_model or "missing"}',
        ),
        support.validation_check(
            'timeout_s',
            timeout_s is not None and timeout_s > 0,
            f'timeout_s={timeout_s!r}',
        ),
        support.validation_check(
            'temperature',
            temperature is not None and 0.0 <= temperature <= 2.0,
            f'temperature={temperature!r}',
        ),
        support.validation_check(
            'top_p',
            top_p is not None and 0.0 < top_p <= 1.0,
            f'top_p={top_p!r}',
        ),
        support.validation_check(
            'max_tokens',
            max_tokens is not None and max_tokens > 0,
            f'max_tokens={max_tokens!r}',
        ),
        support.validation_check(
            'max_tool_calls',
            max_tool_calls is not None and max_tool_calls > 0,
            f'max_tool_calls={max_tool_calls!r}',
        ),
        support.validation_check(
            'max_model_calls',
            max_model_calls is not None and max_model_calls > 0,
            f'max_model_calls={max_model_calls!r}',
        ),
        support.validation_check(
            'max_recent_turns',
            max_recent_turns is not None and max_recent_turns >= 0,
            f'max_recent_turns={max_recent_turns!r}',
        ),
        support.validation_check(
            'reasoning_effort',
            reasoning_effort in _BIBLIO_AGENT_REASONING_EFFORTS,
            (
                f'reasoning_effort={reasoning_effort or "missing"}; '
                f'allowed={",".join(sorted(_BIBLIO_AGENT_REASONING_EFFORTS))}'
            ),
        ),
        shared_transport_check,
    ]


def validate_model_section(
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
    del config_module
    if section == 'main_model':
        return _validate_main_model(
            view,
            resolve_runtime_secret_from_view=resolve_runtime_secret_from_view,
            secret_required_error_cls=secret_required_error_cls,
            secret_resolution_error_cls=secret_resolution_error_cls,
        )

    shared_transport_check = None
    if section != 'arbiter_model':
        shared_transport_check = _shared_transport_check(
            fetcher=fetcher,
            candidate_runtime_section=candidate_runtime_section,
            resolve_runtime_secret_from_view=resolve_runtime_secret_from_view,
            secret_required_error_cls=secret_required_error_cls,
            secret_resolution_error_cls=secret_resolution_error_cls,
        )
    if section in {
        'memory_arbiter_model',
        'identity_extractor_model',
        'identity_periodic_model',
        'arbiter_model',
        'summary_model',
        'web_reformulation_model',
    }:
        return _validate_single_model(
            section,
            view,
            shared_transport_check=shared_transport_check,
        )
    if section in {'stimmung_agent_model', 'validation_agent_model'}:
        return _validate_dual_model_agent(
            section,
            view,
            shared_transport_check=shared_transport_check,
        )
    if section == 'biblio_librarian_agent':
        return _validate_biblio_agent(
            view,
            shared_transport_check=shared_transport_check,
        )
    raise KeyError(f'unknown model runtime settings section: {section}')
