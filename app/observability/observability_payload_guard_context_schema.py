"""Exact writer-side paths; no additions to the general key or text policy."""
from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any

from observability.observability_payload_guard_safe_code_policy import (
    _dangerous_value_class, _is_safe_code_text,
)


MEMORY_CANDIDATE_COMMON = {
    'candidate_id_sha256_12': 'hash', 'source_kind': 'code', 'source_lane': 'code',
    'retrieval_score': 'number_or_none', 'retrieval_score_bucket': 'code',
    'arbiter_status': 'arbiter_status', 'prompt_injection_status': 'code',
}
MEMORY_RETRIEVED_CANDIDATE = {
    **MEMORY_CANDIDATE_COMMON, 'retrieval_rank': 'int', 'basket_status': 'code',
    'pre_arbiter_reason_code': 'code', 'basket_candidate_id_sha256_12': 'hash',
}
MEMORY_BASKET_CANDIDATE = {
    **MEMORY_CANDIDATE_COMMON, 'basket_rank': 'int', 'source_candidate_count': 'int',
    'source_candidate_id_sha256_12': ('list', 8, 'hash'), 'dedup_reason_code': 'code',
    'decision_source': 'code', 'semantic_relevance': 'number_or_none',
    'contextual_gain': 'number_or_none', 'redundant_with_recent': 'bool',
    'reason_code': 'code', 'reason_chars': 'int',
    'reason_sha256_12': 'hash',
}
MEMORY_SNAPSHOT = {
    'schema_version': ('enum', 'v1'), 'mode': 'code', 'status_schema_version': 'code',
    'retrieval': {'status': 'code', 'reason_code': 'code', 'error_code': 'code',
                  'error_class': 'class', 'top_k_requested': 'int_or_none',
                  'retrieved_count': 'int', 'source_kind_counts': 'counts', 'source_lane_counts': 'counts'},
    'basket': {'status': 'code', 'reason_code': 'code', 'basket_candidates_count': 'int',
               'deduped_retrieved_count': 'int', 'not_basketed_count': 'int', 'basket_status_counts': 'counts'},
    'arbiter': {'status': 'code', 'reason_code': 'code', 'decisions_count': 'int',
                'kept_count': 'int', 'rejected_count': 'int', 'arbiter_status_counts': 'arbiter_counts',
                'decision_source_counts': 'counts'},
    'injection': {'injection_class': 'code', 'injected_candidate_count': 'int',
                  'injected_candidate_id_sha256_12': ('list', 8, 'hash'),
                  'context_hints_count': 'int', 'candidate_status_counts': 'counts'},
    'retrieved_candidates': ('list', 24, MEMORY_RETRIEVED_CANDIDATE),
    'basket_candidates': ('list', 24, MEMORY_BASKET_CANDIDATE), 'truncated': 'bool',
    'reason_code': 'code', 'error_code': 'code',
}

BIBLIO_STATE = {
    'schema_version': ('enum', 'biblio_conversation_state_v1'),
    'persistence_mode': ('enum', 'conversation_message_meta'),
    'present': 'bool', 'conversation_id_present': 'bool', 'current_document_present': 'bool',
    'current_document_doc_id_short': 'doc_ref', 'current_document_id_present': 'bool',
    'current_work_present': 'bool', 'page_no': 'int_or_none', 'para_no': 'int_or_none',
    'paragraph_id': 'int_or_none', 'last_passage_hash': 'hash', 'last_result_present': 'bool',
    'last_result_status': 'biblio_code', 'last_result_reason_code': 'biblio_code',
    'last_result_interval_kind': 'biblio_code', 'last_result_interval_mode': 'biblio_code',
    'last_result_interval_state': 'biblio_code', 'last_result_interval_end_page_no': 'int_or_none',
    'last_result_interval_end_para_no': 'int_or_none', 'last_result_interval_requested_end_page_no': 'int_or_none',
    'last_result_interval_section_id_present': 'bool', 'last_result_interval_section_no': 'int_or_none',
    'last_result_interval_chapter_no': 'int_or_none', 'last_result_interval_section_kind': 'biblio_code',
    'last_result_interval_section_level': 'int_or_none', 'last_result_interval_parent_section_id_present': 'bool',
    'last_result_interval_next_page_no': 'int_or_none', 'last_result_interval_next_para_no': 'int_or_none',
    'last_result_interval_incomplete_page_no': 'int_or_none', 'last_candidate_count': ('int_max', 8),
    'last_ambiguity_present': 'bool', 'last_ambiguity_candidate_count': 'int',
    'last_intent': 'biblio_code', 'updated_at_present': 'bool',
}
BIBLIO_TRANSITION = {
    'before_present': 'bool', 'after_present': 'bool', 'changed': 'bool',
    'reason_code': 'biblio_code', 'source_event': 'biblio_code',
    'persistence_mode': ('enum', 'conversation_message_meta'), 'attached_to_message_meta': 'bool',
    'persistence_status': ('enum', 'pending_normal_conversation_save'),
    'persistence_guarantee': ('enum', 'after_normal_conversation_save'),
}
PARENT_SUMMARY = {
    'summary_id': 'code', 'summary_id_sha256_12': 'hash',
    'start_ts': 'timestamp_or_none', 'end_ts': 'timestamp_or_none', 'linked_trace_count': 'int',
}


def context_rule(stage: str, path: tuple[str, ...]) -> Any:
    if stage == 'memory_chain_snapshot' and not path:
        return MEMORY_SNAPSHOT
    if stage == 'biblio':
        if path == ('state',):
            return BIBLIO_STATE
        if path == ('state_transition',):
            return BIBLIO_TRANSITION
    if stage == 'llm_call':
        if path == ('provider_generation_id_present',):
            return 'bool'
        if path == ('provider_generation_id_sha256_12',):
            return 'hash'
    if stage == 'prompt_prepared' and path == ('memory_prompt_injection', 'parent_summaries_injected'):
        return ('list', 24, PARENT_SUMMARY)
    if stage == 'prompt_prepared' and path == ('memory_prompt_injection', 'injected_candidate_ids'):
        return ('list', 24, 'candidate_ref')
    prefix = ('inputs', 'web') if stage == 'hermeneutic_node_insertion' else ()
    if stage in {'web_search', 'hermeneutic_node_insertion'} and path in {
        (*prefix, key, '[]', 'source_domain')
        for key in ('source_material_summary', 'crawl4ai_extraction_summary', 'web_pdf_read_summary')
    }:
        return 'hostname'
    return None


def valid_context_scalar(kind: Any, value: Any) -> bool:
    if isinstance(kind, tuple):
        if kind[0] == 'enum':
            return type(value) is str and value in kind[1:]
        if kind[0] == 'int_max':
            return type(value) is int and 0 <= value <= kind[1]
        return False
    if kind.endswith('_or_none') and value is None:
        return True
    if kind == 'bool':
        return type(value) is bool
    if kind in {'int', 'int_or_none'}:
        return type(value) is int and 0 <= value <= 2**63 - 1
    if kind == 'number_or_none':
        return type(value) in (int, float) and abs(value) <= 1e9 and math.isfinite(value)
    if type(value) is not str or any(ord(c) < 32 or ord(c) == 127 for c in value) or value != value.strip():
        return False
    if kind == 'hash':
        return value == '' or bool(re.fullmatch(r'[0-9a-f]{12}', value))
    if kind == 'hostname':
        # Only a DNS hostname at a source-domain path, never an URL, port or userinfo.
        labels = value.split('.')
        return value == '' or (len(value) <= 253 and len(labels) >= 2
            and all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
                    and not _dangerous_value_class('source_domain', label) for label in labels))
    if _dangerous_value_class('', value):
        return False
    if kind == 'timestamp_or_none':
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', value):
            return False
        try:
            datetime.fromisoformat(value.replace('Z', '+00:00'))
            return True
        except ValueError:
            return False
    if kind == 'candidate_ref':
        return bool(re.fullmatch(r'(?:cand-[0-9a-f]{16}|summary:[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})', value))
    if kind in {'biblio_code', 'doc_ref'} and re.fullmatch(r'sha256:[0-9a-f]{12}', value):
        return True
    if kind == 'doc_ref':
        return value == '' or bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,159}', value))
    if kind == 'class':
        return value == '' or bool(re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,159}', value))
    if kind == 'arbiter_status' and value.startswith('skipped:'):
        return _is_safe_code_text(value[8:], allow_empty=False)
    return kind in {'code', 'biblio_code', 'arbiter_status'} and _is_safe_code_text(value)
