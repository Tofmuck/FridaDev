from __future__ import annotations

from typing import Any, Callable, Mapping

from admin import runtime_settings_model_validation
from admin import runtime_settings_platform_validation


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
    validator_kwargs = {
        'fetcher': fetcher,
        'candidate_runtime_section': candidate_runtime_section,
        'resolve_runtime_secret_from_view': resolve_runtime_secret_from_view,
        'secret_required_error_cls': secret_required_error_cls,
        'secret_resolution_error_cls': secret_resolution_error_cls,
        'config_module': config_module,
    }
    if section in runtime_settings_model_validation.MODEL_SECTIONS:
        checks = runtime_settings_model_validation.validate_model_section(
            section,
            view,
            **validator_kwargs,
        )
    elif section in runtime_settings_platform_validation.PLATFORM_SECTIONS:
        checks = runtime_settings_platform_validation.validate_platform_section(
            section,
            view,
            **validator_kwargs,
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
