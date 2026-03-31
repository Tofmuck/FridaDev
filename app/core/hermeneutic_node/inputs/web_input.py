from __future__ import annotations

from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "v1"


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _canonical_runtime(runtime_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    runtime = runtime_payload if isinstance(runtime_payload, Mapping) else {}
    return {
        'searxng_results': _optional_int(runtime.get('searxng_results')),
        'crawl4ai_top_n': _optional_int(runtime.get('crawl4ai_top_n')),
        'crawl4ai_max_chars': _optional_int(runtime.get('crawl4ai_max_chars')),
    }


def _canonical_source(source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        'rank': _optional_int(source.get('rank')),
        'title': str(source.get('title') or ''),
        'url': str(source.get('url') or ''),
        'source_domain': _optional_str(source.get('source_domain')),
        'search_snippet': str(source.get('search_snippet') or ''),
        'used_in_prompt': bool(source.get('used_in_prompt', False)),
        'used_content_kind': str(source.get('used_content_kind') or 'none'),
        'content_used': str(source.get('content_used') or ''),
        'truncated': bool(source.get('truncated', False)),
    }


def build_web_input(
    *,
    enabled: bool,
    status: str,
    reason_code: str | None = None,
    original_user_message: str = '',
    query: str | None = None,
    results_count: int = 0,
    runtime: Mapping[str, Any] | None = None,
    sources: Sequence[Mapping[str, Any]] = (),
    context_block: str = '',
) -> dict[str, Any]:
    return {
        'schema_version': SCHEMA_VERSION,
        'enabled': bool(enabled),
        'status': str(status),
        'reason_code': _optional_str(reason_code),
        'original_user_message': str(original_user_message or ''),
        'query': _optional_str(query),
        'results_count': int(results_count),
        'runtime': _canonical_runtime(runtime),
        'sources': [_canonical_source(source) for source in sources],
        'context_block': str(context_block or ''),
    }


def build_web_input_from_runtime_payload(runtime_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = runtime_payload if isinstance(runtime_payload, Mapping) else {}
    return build_web_input(
        enabled=bool(payload.get('enabled', False)),
        status=str(payload.get('status') or 'skipped'),
        reason_code=_optional_str(payload.get('reason_code')),
        original_user_message=str(payload.get('original_user_message') or ''),
        query=_optional_str(payload.get('query')),
        results_count=_optional_int(payload.get('results_count')) or 0,
        runtime=payload.get('runtime') if isinstance(payload.get('runtime'), Mapping) else None,
        sources=payload.get('sources') if isinstance(payload.get('sources'), Sequence) else (),
        context_block=str(payload.get('context_block') or ''),
    )
