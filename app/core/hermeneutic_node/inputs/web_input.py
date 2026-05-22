from __future__ import annotations

from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "v1"
ACTIVATION_MODES = ("manual", "auto", "not_requested")


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


def _activation_mode(value: Any, *, enabled: bool) -> str:
    text = str(value or '').strip()
    if text in ACTIVATION_MODES:
        return text
    return 'manual' if enabled else 'not_requested'


def _canonical_runtime(runtime_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    runtime = runtime_payload if isinstance(runtime_payload, Mapping) else {}
    return {
        'searxng_results': _optional_int(runtime.get('searxng_results')),
        'crawl4ai_top_n': _optional_int(runtime.get('crawl4ai_top_n')),
        'crawl4ai_max_chars': _optional_int(runtime.get('crawl4ai_max_chars')),
    }


def _canonical_query_plan(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = payload if isinstance(payload, Mapping) else {}
    return {
        'query_plan_kind': _optional_str(data.get('query_plan_kind')),
        'query_count': _optional_int(data.get('query_count')) or 0,
        'primary_query_sha256_12': _optional_str(data.get('primary_query_sha256_12')),
        'secondary_query_count': _optional_int(data.get('secondary_query_count')) or 0,
        'secondary_query_sha256_12': [
            str(value)
            for value in data.get('secondary_query_sha256_12') or []
            if str(value or '')
        ],
        'raw_result_count': _optional_int(data.get('raw_result_count')) or 0,
        'deduped_result_count': _optional_int(data.get('deduped_result_count')) or 0,
    }


def _canonical_searxng_profile_params(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = payload if isinstance(payload, Mapping) else {}
    return {
        'searxng_profile_params_kind': _optional_str(data.get('searxng_profile_params_kind')),
        'searxng_profile_params_policy': _optional_str(data.get('searxng_profile_params_policy')),
        'searxng_categories': [
            str(value)
            for value in data.get('searxng_categories') or []
            if str(value or '')
        ],
        'searxng_engines': [
            str(value)
            for value in data.get('searxng_engines') or []
            if str(value or '')
        ],
        'searxng_time_range': _optional_str(data.get('searxng_time_range')),
        'searxng_language': _optional_str(data.get('searxng_language')),
        'searxng_safesearch': _optional_str(data.get('searxng_safesearch')),
    }


def _canonical_reranking(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = payload if isinstance(payload, Mapping) else {}
    reason_counts = data.get('rerank_reason_counts')
    if not isinstance(reason_counts, Mapping):
        reason_counts = {}
    return {
        'rerank_applied': bool(data.get('rerank_applied', False)),
        'rerank_policy': _optional_str(data.get('rerank_policy')),
        'rerank_input_count': _optional_int(data.get('rerank_input_count')) or 0,
        'rerank_output_count': _optional_int(data.get('rerank_output_count')) or 0,
        'rerank_profile': _optional_str(data.get('rerank_profile')),
        'rerank_top_domains_before': [
            str(value)
            for value in data.get('rerank_top_domains_before') or []
            if str(value or '')
        ],
        'rerank_top_domains_after': [
            str(value)
            for value in data.get('rerank_top_domains_after') or []
            if str(value or '')
        ],
        'rerank_reason_counts': {
            str(key): _optional_int(value) or 0
            for key, value in dict(reason_counts).items()
            if str(key or '')
        },
        'rerank_promoted_count': _optional_int(data.get('rerank_promoted_count')) or 0,
        'rerank_downranked_count': _optional_int(data.get('rerank_downranked_count')) or 0,
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
        'source_origin': str(source.get('source_origin') or 'search_result'),
        'is_primary_source': bool(source.get('is_primary_source', False)),
        'crawl_status': str(source.get('crawl_status') or 'not_attempted'),
        'crawl_filter': _optional_str(source.get('crawl_filter')),
        'crawl_filter_requested': _optional_str(source.get('crawl_filter_requested')),
        'crawl_policy_kind': _optional_str(source.get('crawl_policy_kind')),
        'crawl_policy_reason': _optional_str(source.get('crawl_policy_reason')),
        'crawl_cache_mode': _optional_str(source.get('crawl_cache_mode')),
        'crawl_query_sha256_12': _optional_str(source.get('crawl_query_sha256_12')),
        'crawl_query_chars': _optional_int(source.get('crawl_query_chars')) or 0,
        'crawl_fallback_used': bool(source.get('crawl_fallback_used', False)),
        'crawl_fallback_reason': _optional_str(source.get('crawl_fallback_reason')),
        'crawl_primary_status': _optional_str(source.get('crawl_primary_status')),
        'crawl_fallback_status': _optional_str(source.get('crawl_fallback_status')),
        'crawl_markdown_chars': _optional_int(source.get('crawl_markdown_chars')) or 0,
        'crawl_max_chars': _optional_int(source.get('crawl_max_chars')) or 0,
        'raw_rank': _optional_int(source.get('raw_rank')),
        'reranked_rank': _optional_int(source.get('reranked_rank')),
        'rerank_score': source.get('rerank_score'),
        'rerank_bucket': _optional_str(source.get('rerank_bucket')),
        'rerank_reason_codes': [
            str(value)
            for value in source.get('rerank_reason_codes') or []
            if str(value or '')
        ],
    }


def _source_content_chars(source: Mapping[str, Any]) -> int:
    return len(str(source.get('content_used') or ''))


def _canonical_source_material_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        'rank': _optional_int(entry.get('rank')) or 0,
        'url': str(entry.get('url') or ''),
        'source_origin': str(entry.get('source_origin') or 'search_result'),
        'is_primary_source': bool(entry.get('is_primary_source', False)),
        'used_in_prompt': bool(entry.get('used_in_prompt', False)),
        'used_content_kind': str(entry.get('used_content_kind') or 'none'),
        'crawl_status': str(entry.get('crawl_status') or 'not_attempted'),
        'content_chars': _optional_int(entry.get('content_chars')) or 0,
        'truncated': bool(entry.get('truncated', False)),
    }


def _derive_source_material_summary(sources: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            'rank': _optional_int(source.get('rank')) or 0,
            'url': str(source.get('url') or ''),
            'source_origin': str(source.get('source_origin') or 'search_result'),
            'is_primary_source': bool(source.get('is_primary_source', False)),
            'used_in_prompt': bool(source.get('used_in_prompt', False)),
            'used_content_kind': str(source.get('used_content_kind') or 'none'),
            'crawl_status': str(source.get('crawl_status') or 'not_attempted'),
            'content_chars': _source_content_chars(source),
            'truncated': bool(source.get('truncated', False)),
        }
        for source in sources
    ]


def _canonical_source_material_summary(
    source_material_summary: Sequence[Mapping[str, Any]] | None,
    *,
    sources: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(source_material_summary, Sequence) and not isinstance(source_material_summary, (str, bytes, bytearray)):
        summary = [
            _canonical_source_material_entry(entry)
            for entry in source_material_summary
            if isinstance(entry, Mapping)
        ]
        if summary:
            return summary
    return _derive_source_material_summary(sources)


def _canonical_crawl4ai_extraction_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        'rank': _optional_int(entry.get('rank')) or 0,
        'url': str(entry.get('url') or ''),
        'source_origin': str(entry.get('source_origin') or 'search_result'),
        'is_primary_source': bool(entry.get('is_primary_source', False)),
        'crawl_status': str(entry.get('crawl_status') or 'not_attempted'),
        'crawl_filter': _optional_str(entry.get('crawl_filter')),
        'crawl_filter_requested': _optional_str(entry.get('crawl_filter_requested')),
        'crawl_policy_kind': _optional_str(entry.get('crawl_policy_kind')),
        'crawl_policy_reason': _optional_str(entry.get('crawl_policy_reason')),
        'crawl_cache_mode': _optional_str(entry.get('crawl_cache_mode')),
        'crawl_query_sha256_12': _optional_str(entry.get('crawl_query_sha256_12')),
        'crawl_query_chars': _optional_int(entry.get('crawl_query_chars')) or 0,
        'crawl_fallback_used': bool(entry.get('crawl_fallback_used', False)),
        'crawl_fallback_reason': _optional_str(entry.get('crawl_fallback_reason')),
        'crawl_primary_status': _optional_str(entry.get('crawl_primary_status')),
        'crawl_fallback_status': _optional_str(entry.get('crawl_fallback_status')),
        'crawl_markdown_chars': _optional_int(entry.get('crawl_markdown_chars')) or 0,
        'crawl_max_chars': _optional_int(entry.get('crawl_max_chars')) or 0,
        'used_content_kind': str(entry.get('used_content_kind') or 'none'),
        'content_chars': _optional_int(entry.get('content_chars')) or 0,
        'truncated': bool(entry.get('truncated', False)),
    }


def _canonical_crawl4ai_extraction_summary(
    crawl4ai_extraction_summary: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    if not (
        isinstance(crawl4ai_extraction_summary, Sequence)
        and not isinstance(crawl4ai_extraction_summary, (str, bytes, bytearray))
    ):
        return []
    return [
        _canonical_crawl4ai_extraction_entry(entry)
        for entry in crawl4ai_extraction_summary
        if isinstance(entry, Mapping)
    ]


def _canonical_used_content_kinds(
    used_content_kinds: Sequence[Any] | None,
    *,
    source_material_summary: Sequence[Mapping[str, Any]],
) -> list[str]:
    if isinstance(used_content_kinds, Sequence) and not isinstance(used_content_kinds, (str, bytes, bytearray)):
        deduped: list[str] = []
        for kind in used_content_kinds:
            text = str(kind or '')
            if text and text not in deduped:
                deduped.append(text)
        if deduped:
            return deduped

    deduped: list[str] = []
    for source in source_material_summary:
        if not bool(source.get('used_in_prompt', False)):
            continue
        kind = str(source.get('used_content_kind') or 'none')
        if kind == 'none' or kind in deduped:
            continue
        deduped.append(kind)
    return deduped


def _derive_injected_chars(source_material_summary: Sequence[Mapping[str, Any]]) -> int:
    total = 0
    for source in source_material_summary:
        if not bool(source.get('used_in_prompt', False)):
            continue
        total += _optional_int(source.get('content_chars')) or 0
    return total


def build_web_input(
    *,
    enabled: bool,
    status: str,
    activation_mode: str | None = None,
    reason_code: str | None = None,
    original_user_message: str = '',
    search_profile: str | None = None,
    query: str | None = None,
    results_count: int = 0,
    explicit_url_detected: bool = False,
    explicit_url: str | None = None,
    read_state: str | None = None,
    primary_source_kind: str | None = None,
    primary_read_attempted: bool = False,
    primary_read_status: str | None = None,
    primary_read_filter: str | None = None,
    primary_read_raw_fallback_used: bool = False,
    fallback_used: bool = False,
    collection_path: str | None = None,
    runtime: Mapping[str, Any] | None = None,
    query_plan: Mapping[str, Any] | None = None,
    searxng_profile_params: Mapping[str, Any] | None = None,
    reranking: Mapping[str, Any] | None = None,
    sources: Sequence[Mapping[str, Any]] = (),
    context_block: str = '',
    used_content_kinds: Sequence[Any] | None = None,
    injected_chars: int | None = None,
    context_chars: int | None = None,
    source_material_summary: Sequence[Mapping[str, Any]] | None = None,
    crawl4ai_extraction_summary: Sequence[Mapping[str, Any]] | None = None,
    crawl4ai_policy_kinds: Sequence[Any] | None = None,
    crawl4ai_filter_counts: Mapping[str, Any] | None = None,
    crawl4ai_cache_modes: Mapping[str, Any] | None = None,
    crawl4ai_fallback_used_count: int | None = None,
    crawl4ai_query_sha256_12: Sequence[Any] | None = None,
) -> dict[str, Any]:
    canonical_sources = [
        _canonical_source(source)
        for source in sources
        if isinstance(source, Mapping)
    ]
    canonical_context_block = str(context_block or '')
    canonical_source_material_summary = _canonical_source_material_summary(
        source_material_summary,
        sources=canonical_sources,
    )
    canonical_used_content_kinds = _canonical_used_content_kinds(
        used_content_kinds,
        source_material_summary=canonical_source_material_summary,
    )
    canonical_injected_chars = _optional_int(injected_chars)
    if canonical_injected_chars is None:
        canonical_injected_chars = _derive_injected_chars(canonical_source_material_summary)
    canonical_context_chars = _optional_int(context_chars)
    if canonical_context_chars is None:
        canonical_context_chars = len(canonical_context_block)
    canonical_crawl4ai_extraction_summary = _canonical_crawl4ai_extraction_summary(crawl4ai_extraction_summary)
    canonical_enabled = bool(enabled)
    return {
        'schema_version': SCHEMA_VERSION,
        'enabled': canonical_enabled,
        'status': str(status),
        'activation_mode': _activation_mode(activation_mode, enabled=canonical_enabled),
        'reason_code': _optional_str(reason_code),
        'original_user_message': str(original_user_message or ''),
        'search_profile': _optional_str(search_profile),
        'query': _optional_str(query),
        'results_count': int(results_count),
        'explicit_url_detected': bool(explicit_url_detected),
        'explicit_url': _optional_str(explicit_url),
        'read_state': _optional_str(read_state),
        'primary_source_kind': _optional_str(primary_source_kind),
        'primary_read_attempted': bool(primary_read_attempted),
        'primary_read_status': _optional_str(primary_read_status),
        'primary_read_filter': _optional_str(primary_read_filter),
        'primary_read_raw_fallback_used': bool(primary_read_raw_fallback_used),
        'fallback_used': bool(fallback_used),
        'collection_path': _optional_str(collection_path),
        'runtime': _canonical_runtime(runtime),
        'query_plan': _canonical_query_plan(query_plan),
        'searxng_profile_params': _canonical_searxng_profile_params(searxng_profile_params),
        'reranking': _canonical_reranking(reranking),
        'used_content_kinds': canonical_used_content_kinds,
        'injected_chars': canonical_injected_chars,
        'context_chars': canonical_context_chars,
        'source_material_summary': canonical_source_material_summary,
        'crawl4ai_extraction_summary': canonical_crawl4ai_extraction_summary,
        'crawl4ai_policy_kinds': [
            str(value)
            for value in crawl4ai_policy_kinds or []
            if str(value or '')
        ],
        'crawl4ai_filter_counts': {
            str(key): _optional_int(value) or 0
            for key, value in dict(crawl4ai_filter_counts or {}).items()
            if str(key or '')
        },
        'crawl4ai_cache_modes': {
            str(key): _optional_int(value) or 0
            for key, value in dict(crawl4ai_cache_modes or {}).items()
            if str(key or '')
        },
        'crawl4ai_fallback_used_count': _optional_int(crawl4ai_fallback_used_count) or 0,
        'crawl4ai_query_sha256_12': [
            str(value)
            for value in crawl4ai_query_sha256_12 or []
            if str(value or '')
        ],
        'sources': canonical_sources,
        'context_block': canonical_context_block,
    }


def build_web_input_from_runtime_payload(runtime_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = runtime_payload if isinstance(runtime_payload, Mapping) else {}
    return build_web_input(
        enabled=bool(payload.get('enabled', False)),
        status=str(payload.get('status') or 'skipped'),
        activation_mode=_optional_str(payload.get('activation_mode')),
        reason_code=_optional_str(payload.get('reason_code')),
        original_user_message=str(payload.get('original_user_message') or ''),
        search_profile=_optional_str(payload.get('search_profile')),
        query=_optional_str(payload.get('query')),
        results_count=_optional_int(payload.get('results_count')) or 0,
        explicit_url_detected=bool(payload.get('explicit_url_detected', False)),
        explicit_url=_optional_str(payload.get('explicit_url')),
        read_state=_optional_str(payload.get('read_state')),
        primary_source_kind=_optional_str(payload.get('primary_source_kind')),
        primary_read_attempted=bool(payload.get('primary_read_attempted', False)),
        primary_read_status=_optional_str(payload.get('primary_read_status')),
        primary_read_filter=_optional_str(payload.get('primary_read_filter')),
        primary_read_raw_fallback_used=bool(payload.get('primary_read_raw_fallback_used', False)),
        fallback_used=bool(payload.get('fallback_used', False)),
        collection_path=_optional_str(payload.get('collection_path')),
        runtime=payload.get('runtime') if isinstance(payload.get('runtime'), Mapping) else None,
        query_plan=payload,
        searxng_profile_params=payload,
        reranking=payload,
        sources=payload.get('sources') if isinstance(payload.get('sources'), Sequence) else (),
        context_block=str(payload.get('context_block') or ''),
        used_content_kinds=payload.get('used_content_kinds') if isinstance(payload.get('used_content_kinds'), Sequence) else (),
        injected_chars=_optional_int(payload.get('injected_chars')),
        context_chars=_optional_int(payload.get('context_chars')),
        source_material_summary=payload.get('source_material_summary')
        if isinstance(payload.get('source_material_summary'), Sequence)
        else (),
        crawl4ai_extraction_summary=payload.get('crawl4ai_extraction_summary')
        if isinstance(payload.get('crawl4ai_extraction_summary'), Sequence)
        else (),
        crawl4ai_policy_kinds=payload.get('crawl4ai_policy_kinds')
        if isinstance(payload.get('crawl4ai_policy_kinds'), Sequence)
        else (),
        crawl4ai_filter_counts=payload.get('crawl4ai_filter_counts')
        if isinstance(payload.get('crawl4ai_filter_counts'), Mapping)
        else {},
        crawl4ai_cache_modes=payload.get('crawl4ai_cache_modes')
        if isinstance(payload.get('crawl4ai_cache_modes'), Mapping)
        else {},
        crawl4ai_fallback_used_count=_optional_int(payload.get('crawl4ai_fallback_used_count')),
        crawl4ai_query_sha256_12=payload.get('crawl4ai_query_sha256_12')
        if isinstance(payload.get('crawl4ai_query_sha256_12'), Sequence)
        else (),
    )
