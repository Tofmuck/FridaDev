from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

import requests

import config
from admin import runtime_settings
from core import llm_client


logger = logging.getLogger('frida.mutable_identity_judge')


SCHEMA_VERSION = 'mutable_judge_v1'
INPUT_SCHEMA_VERSION = 'mutable_identity_judge_input_v1'
WINDOW_PAIRS_COUNT = 5
PROMPT_KIND = 'mutable_identity_judge'
MODEL_SLOT = 'identity_periodic_model'
CALLER = 'mutable_identity_judge'
JUDGE_WINDOW_MAX_CHARS = 32_000
JUDGE_ESTIMATED_PROMPT_TOKEN_LIMIT = 12_000
_CHARS_PER_TOKEN_ESTIMATE = 4

ALLOWED_SUBJECTS = {'llm', 'user'}
ALLOWED_VERDICTS = {'no_change', 'reject', 'defer', 'raise_tension', 'persist'}
PERSIST_OPERATIONS = {'add', 'tighten', 'merge', 'clear_obsolete'}
ALLOWED_CONTINUITY_KINDS = {'identity', 'relation', 'value', 'limit', 'posture', 'tension', 'none'}
PERSISTENCE_REASON_CODES = {
    'explicit_self_definition_continuity',
    'explicit_self_value_continuity',
    'explicit_self_limit_continuity',
    'explicit_relation_continuity',
    'explicit_frida_self_definition_continuity',
    'explicit_frida_limit_continuity',
    'explicit_posture_continuity',
    'mutable_tightening',
    'mutable_merge',
    'mutable_obsolete_explicitly_removed',
}
NON_PERSISTENCE_REASON_CODES = {
    'no_mutable_identity_signal',
    'already_covered_by_static',
    'already_covered_by_mutable',
    'task_local_not_identity',
    'format_or_operator_policy_not_identity',
    'memory_summary_not_identity',
    'irony_roleplay_or_quote',
    'temporary_state',
    'ambiguous_subject',
    'insufficient_context',
    'source_scope_unclear',
    'contradiction_open',
    'relation_tension_open',
    'quoted_or_reported_speech',
    'project_policy_not_identity',
}
TECHNICAL_REASON_CODES = {
    'window_too_large',
    'judge_timeout',
    'judge_transport_error',
    'judge_invalid_json',
    'schema_invalid',
    'invalid_subject',
    'invalid_verdict',
    'invalid_operation',
    'invalid_target',
    'empty_proposition',
    'proposition_too_long',
    'prompt_like_content',
    'non_declarative_content',
    'impossible_mutation',
    'mutable_content_too_long',
    'runtime_safety_violation',
    'mutable_store_unavailable',
    'canonical_write_failed',
}
NO_CHANGE_REASON_CODES = {
    'no_mutable_identity_signal',
    'already_covered_by_static',
    'already_covered_by_mutable',
}
REJECT_REASON_CODES = {
    'task_local_not_identity',
    'format_or_operator_policy_not_identity',
    'memory_summary_not_identity',
    'irony_roleplay_or_quote',
    'temporary_state',
    'ambiguous_subject',
    'quoted_or_reported_speech',
    'project_policy_not_identity',
    'already_covered_by_static',
    'already_covered_by_mutable',
}
DEFER_REASON_CODES = {
    'ambiguous_subject',
    'insufficient_context',
    'source_scope_unclear',
    'contradiction_open',
    'relation_tension_open',
}
RAISE_TENSION_REASON_CODES = {
    'contradiction_open',
    'relation_tension_open',
}
ADD_REASON_CODES = {
    'explicit_self_definition_continuity',
    'explicit_self_value_continuity',
    'explicit_self_limit_continuity',
    'explicit_relation_continuity',
    'explicit_frida_self_definition_continuity',
    'explicit_frida_limit_continuity',
    'explicit_posture_continuity',
}
MODEL_OUTPUT_REASON_CODES = PERSISTENCE_REASON_CODES | NON_PERSISTENCE_REASON_CODES
_REASON_CODES_BY_VERDICT = {
    'persist': PERSISTENCE_REASON_CODES,
    'no_change': NO_CHANGE_REASON_CODES,
    'reject': REJECT_REASON_CODES,
    'defer': DEFER_REASON_CODES,
    'raise_tension': RAISE_TENSION_REASON_CODES,
}
_PERSISTENCE_REASON_CODES_BY_OPERATION = {
    'add': ADD_REASON_CODES,
    'tighten': {'mutable_tightening'},
    'merge': {'mutable_merge'},
    'clear_obsolete': {'mutable_obsolete_explicitly_removed'},
}

_TOP_LEVEL_KEYS = {'schema_version', 'meta', 'verdicts'}
_META_KEYS = {'execution_status', 'window_pairs_count', 'window_complete'}
_VERDICT_KEYS = {
    'subject',
    'verdict',
    'operation',
    'proposition',
    'target',
    'targets',
    'reason_code',
    'continuity_kind',
    'source_refs',
    'guard_notes',
}
_CODE_RE = re.compile(r'^[A-Za-z0-9_:-]{1,80}$')
_ALLOWED_SOURCE_REFS = {f'pair_{index:02d}' for index in range(1, WINDOW_PAIRS_COUNT + 1)}
_PROMPT_LIKE_RE = re.compile(
    r'(ignore\s+previous|system\s+prompt|developer\s+message|follow\s+these\s+instructions|'
    r'tu\s+dois\s+repondre|tu\s+dois\s+répondre|reponds\s+comme|réponds\s+comme)',
    re.IGNORECASE,
)
_RAW_ANNOTATION_KEYS = {
    'content',
    'text',
    'raw',
    'prompt',
    'message',
    'messages',
    'proposition',
    'excerpt',
    'preview',
}


def _text(value: Any) -> str:
    if value is None:
        return ''
    return str(value).strip()


def _content_text(value: Any) -> str:
    if value is None:
        return ''
    return str(value)


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    return []


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()[:12]


def _identity_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return _text(value.get('content'))
    return _text(value)


def _normalize_message(value: Any, *, expected_role: str) -> dict[str, Any]:
    payload = _mapping(value)
    role = _text(payload.get('role')).lower()
    if role != expected_role:
        raise ValueError('window_pair_role_mismatch')
    normalized = {
        'role': expected_role,
        'content': _content_text(payload.get('content')),
    }
    for optional_key in ('timestamp', 'temporal_source_guard', 'source_guard', 'source_id'):
        optional_value = _text(payload.get(optional_key))
        if optional_value:
            normalized[optional_key] = optional_value
    return normalized


def _normalize_pair(value: Any, *, index: int) -> dict[str, Any]:
    if isinstance(value, Mapping) and 'user' in value and 'assistant' in value:
        user_message = value.get('user')
        assistant_message = value.get('assistant')
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = list(value)
        if len(items) != 2:
            raise ValueError('window_pair_incomplete')
        user_message, assistant_message = items
    else:
        raise ValueError('window_pair_invalid')

    return {
        'id': f'pair_{index:02d}',
        'user': _normalize_message(user_message, expected_role='user'),
        'assistant': _normalize_message(assistant_message, expected_role='assistant'),
    }


def _normalize_window_pairs(window_pairs: Sequence[Any]) -> list[dict[str, Any]]:
    pairs = list(window_pairs or [])
    if len(pairs) != WINDOW_PAIRS_COUNT:
        raise ValueError('window_pairs_count_invalid')
    return [_normalize_pair(pair, index=index) for index, pair in enumerate(pairs, start=1)]


def _compact_annotation_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        compact: dict[str, Any] = {}
        for raw_key, raw_item in value.items():
            key = _text(raw_key)
            if not key or key.lower() in _RAW_ANNOTATION_KEYS:
                continue
            compact[key] = _compact_annotation_value(raw_item)
        return compact
    if isinstance(value, list):
        return [_compact_annotation_value(item) for item in value]
    if isinstance(value, tuple):
        return [_compact_annotation_value(item) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(float(value), 6)
    text_value = _text(value)
    if not text_value:
        return ''
    if _CODE_RE.fullmatch(text_value):
        return text_value
    return {
        'chars': len(text_value),
        'sha256_12': _short_hash(text_value),
    }


def _normalized_identities(identities: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    source = _mapping(identities)
    return {
        subject: {
            'static': _identity_text(_mapping(source.get(subject)).get('static')),
            'mutable_current': _identity_text(_mapping(source.get(subject)).get('mutable_current')),
        }
        for subject in ('llm', 'user')
    }


def _normalized_budget(mutable_budget: Mapping[str, Any]) -> dict[str, int]:
    budget = _mapping(mutable_budget)
    return {
        'target_chars': int(budget.get('target_chars') or config.IDENTITY_MUTABLE_TARGET_CHARS),
        'max_chars': int(budget.get('max_chars') or config.IDENTITY_MUTABLE_MAX_CHARS),
    }


def build_judge_input(
    *,
    window_pairs: Sequence[Any],
    identities: Mapping[str, Any],
    mutable_budget: Mapping[str, Any],
    source_annotations: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        'schema_version': INPUT_SCHEMA_VERSION,
        'window_pairs': _normalize_window_pairs(window_pairs),
        'identities': _normalized_identities(identities),
        'mutable_budget': _normalized_budget(mutable_budget),
        'judgment_rules': {
            'judge_reads_full_window': True,
            'python_must_not_score_identity': True,
            'python_must_not_preselect_semantic_candidates': True,
            'static_writes_forbidden': True,
            'same_regime_for_subjects': ['llm', 'user'],
            'allowed_verdicts': sorted(ALLOWED_VERDICTS),
            'allowed_continuity_kinds': sorted(ALLOWED_CONTINUITY_KINDS),
            'model_output_reason_codes': {
                'persistence': sorted(PERSISTENCE_REASON_CODES),
                'add': sorted(ADD_REASON_CODES),
                'no_change': sorted(NO_CHANGE_REASON_CODES),
                'reject': sorted(REJECT_REASON_CODES),
                'defer': sorted(DEFER_REASON_CODES),
                'raise_tension': sorted(RAISE_TENSION_REASON_CODES),
            },
            'technical_reason_codes_not_model_output': sorted(TECHNICAL_REASON_CODES),
            'persistent_operations_only_for_persist': sorted(PERSIST_OPERATIONS),
            'raise_tension_persists_canon': False,
        },
        'source_annotations': _compact_annotation_value(source_annotations or {}),
    }


def load_prompt(prompt_path: str | None = None) -> str:
    raw_path = _text(prompt_path or getattr(config, 'IDENTITY_MUTABLE_JUDGE_PROMPT_PATH', 'prompts/identity_mutable_judge.txt'))
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    return path.read_text(encoding='utf-8').strip()


def build_judge_messages(judge_input: Mapping[str, Any], *, system_prompt: str) -> list[dict[str, str]]:
    return [
        {'role': 'system', 'content': str(system_prompt or '').strip()},
        {'role': 'user', 'content': _judge_input_json(judge_input)},
    ]


def _judge_input_json(judge_input: Mapping[str, Any]) -> str:
    return json.dumps(dict(judge_input), ensure_ascii=False, indent=2)


def build_openrouter_payload(
    judge_input: Mapping[str, Any],
    *,
    model_settings: Mapping[str, Any],
    system_prompt: str,
) -> dict[str, Any]:
    return {
        'model': _text(model_settings.get('model')),
        'messages': build_judge_messages(judge_input, system_prompt=system_prompt),
        'temperature': float(model_settings.get('temperature')),
        'top_p': float(model_settings.get('top_p')),
        'max_tokens': int(model_settings.get('max_tokens')),
        'metadata': {
            'frida_caller': CALLER,
            'frida_slot': MODEL_SLOT,
        },
        'trace': {
            'trace_name': 'FridaDev',
            'generation_name': 'FridaDev / Mutable Identity Judge',
        },
    }


def _runtime_payload_value(payload: Mapping[str, Any], field: str, default: Any) -> Any:
    field_payload = payload.get(field)
    if not isinstance(field_payload, Mapping):
        return default
    resolved = field_payload.get('value')
    if resolved in (None, ''):
        return default
    return resolved


def runtime_model_settings() -> dict[str, Any]:
    view = runtime_settings.get_identity_periodic_model_settings()
    payload = view.payload
    return {
        'model': _text(_runtime_payload_value(payload, 'model', config.IDENTITY_PERIODIC_MODEL))
        or config.IDENTITY_PERIODIC_MODEL,
        'temperature': float(_runtime_payload_value(payload, 'temperature', config.IDENTITY_PERIODIC_TEMPERATURE)),
        'top_p': float(_runtime_payload_value(payload, 'top_p', config.IDENTITY_PERIODIC_TOP_P)),
        'max_tokens': int(_runtime_payload_value(payload, 'max_tokens', config.IDENTITY_PERIODIC_MAX_TOKENS)),
        'timeout_s': int(_runtime_payload_value(payload, 'timeout_s', config.IDENTITY_PERIODIC_TIMEOUT_S)),
    }


def _headers() -> dict[str, Any]:
    return llm_client.or_headers_custom(
        caller=CALLER,
        referer=config.OR_REFERER_IDENTITY_PERIODIC,
        title='FridaDev / Mutable Identity Judge',
    )


def _safe_json_loads(raw: Any) -> Mapping[str, Any] | None:
    try:
        parsed = json.loads(_text(raw))
    except Exception:
        return None
    if not isinstance(parsed, Mapping):
        return None
    return parsed


def _failure_result(reason_code: str, observability_fields: Mapping[str, Any] | None = None) -> dict[str, Any]:
    observability = {
        'status': 'skipped',
        'reason_code': reason_code,
        'prompt_kind': PROMPT_KIND,
    }
    observability.update(dict(_mapping(observability_fields)))
    return {
        'status': 'skipped',
        'reason_code': reason_code,
        'contract': None,
        'observability': observability,
    }


def _estimated_prompt_tokens(char_count: int) -> int:
    if char_count <= 0:
        return 0
    return (int(char_count) + _CHARS_PER_TOKEN_ESTIMATE - 1) // _CHARS_PER_TOKEN_ESTIMATE


def _judge_window_chars(judge_input: Mapping[str, Any]) -> int:
    total = 0
    for pair in _list(judge_input.get('window_pairs')):
        pair_payload = _mapping(pair)
        for role_key in ('user', 'assistant'):
            message = _mapping(pair_payload.get(role_key))
            total += len(str(message.get('content') or ''))
    return total


def _judge_size_guard(
    *,
    judge_input: Mapping[str, Any],
    system_prompt: str,
    model_input_json: str,
) -> dict[str, Any]:
    window_chars = _judge_window_chars(judge_input)
    payload_chars = len(model_input_json)
    estimated_prompt_tokens = _estimated_prompt_tokens(len(system_prompt or '') + payload_chars)
    ok = (
        window_chars <= JUDGE_WINDOW_MAX_CHARS
        and estimated_prompt_tokens <= JUDGE_ESTIMATED_PROMPT_TOKEN_LIMIT
    )
    return {
        'ok': ok,
        'window_chars': window_chars,
        'payload_chars': payload_chars,
        'estimated_prompt_tokens': estimated_prompt_tokens,
        'max_window_chars': JUDGE_WINDOW_MAX_CHARS,
        'max_estimated_prompt_tokens': JUDGE_ESTIMATED_PROMPT_TOKEN_LIMIT,
    }


def _max_proposition_chars(mutable_budget: Mapping[str, Any] | None = None) -> int:
    budget = _mapping(mutable_budget)
    try:
        value = int(budget.get('max_chars') or config.IDENTITY_MUTABLE_MAX_CHARS)
    except (TypeError, ValueError):
        value = int(config.IDENTITY_MUTABLE_MAX_CHARS)
    return max(1, value)


def _validate_code_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    codes: list[str] = []
    for item in value:
        code = _text(item)
        if not code or not _CODE_RE.fullmatch(code):
            return None
        codes.append(code)
    return codes


def _validate_source_refs(value: Any) -> list[str] | None:
    refs = _validate_code_list(value)
    if refs is None:
        return None
    if any(ref not in _ALLOWED_SOURCE_REFS for ref in refs):
        return None
    return refs


def _validate_proposition(value: Any, *, mutable_budget: Mapping[str, Any] | None = None) -> tuple[str | None, str]:
    proposition = _text(value)
    if not proposition:
        return None, 'empty_proposition'
    if len(proposition) > _max_proposition_chars(mutable_budget):
        return None, 'proposition_too_long'
    if '\n' in proposition or _PROMPT_LIKE_RE.search(proposition):
        return None, 'prompt_like_content'
    if proposition.endswith('?'):
        return None, 'non_declarative_content'
    return proposition, ''


def _validate_target(value: Any) -> tuple[str | None, str]:
    target = _text(value)
    if not target:
        return None, 'invalid_target'
    return target, ''


def persist_reason_code_matches_operation(operation: str, reason_code: str) -> bool:
    operation_key = _text(operation).lower()
    reason_key = _text(reason_code)
    allowed = _PERSISTENCE_REASON_CODES_BY_OPERATION.get(operation_key)
    return bool(allowed and reason_key in allowed)


def _empty_persistence_fields(item: Mapping[str, Any]) -> bool:
    return (
        _text(item.get('operation')) == ''
        and _text(item.get('proposition')) == ''
        and _text(item.get('target')) == ''
        and _list(item.get('targets')) == []
    )


def _validate_verdict_item(
    item: Mapping[str, Any],
    *,
    mutable_budget: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str]:
    if set(item.keys()) != _VERDICT_KEYS:
        return None, 'schema_invalid'

    subject = _text(item.get('subject')).lower()
    if subject not in ALLOWED_SUBJECTS:
        return None, 'invalid_subject'
    verdict = _text(item.get('verdict')).lower()
    if verdict not in ALLOWED_VERDICTS:
        return None, 'invalid_verdict'
    reason_code = _text(item.get('reason_code'))
    allowed_reason_codes = _REASON_CODES_BY_VERDICT.get(verdict, set())
    if reason_code not in allowed_reason_codes:
        return None, 'schema_invalid'
    continuity_kind = _text(item.get('continuity_kind')).lower()
    if continuity_kind not in ALLOWED_CONTINUITY_KINDS:
        return None, 'schema_invalid'

    source_refs = _validate_source_refs(item.get('source_refs'))
    if source_refs is None:
        return None, 'schema_invalid'
    guard_notes = _validate_code_list(item.get('guard_notes'))
    if guard_notes is None:
        return None, 'schema_invalid'

    operation = _text(item.get('operation')).lower()
    proposition = _text(item.get('proposition'))
    target = _text(item.get('target'))
    targets = [_text(target_item) for target_item in _list(item.get('targets'))]

    if verdict != 'persist':
        if not _empty_persistence_fields(item):
            return None, 'invalid_operation'
        return {
            'subject': subject,
            'verdict': verdict,
            'operation': '',
            'proposition': '',
            'target': '',
            'targets': [],
            'reason_code': reason_code,
            'continuity_kind': continuity_kind,
            'source_refs': source_refs,
            'guard_notes': guard_notes,
        }, ''

    if operation not in PERSIST_OPERATIONS:
        return None, 'invalid_operation'
    if not persist_reason_code_matches_operation(operation, reason_code):
        return None, 'invalid_operation'

    if operation == 'add':
        if target or targets:
            return None, 'invalid_target'
        proposition_value, reason = _validate_proposition(proposition, mutable_budget=mutable_budget)
        if reason:
            return None, reason
        canonical_target = ''
        canonical_targets: list[str] = []
    elif operation == 'tighten':
        canonical_target, reason = _validate_target(target)
        if reason:
            return None, reason
        if targets:
            return None, 'invalid_target'
        proposition_value, reason = _validate_proposition(proposition, mutable_budget=mutable_budget)
        if reason:
            return None, reason
        canonical_targets = []
    elif operation == 'merge':
        if target or len(targets) < 2 or any(not item for item in targets) or len(set(targets)) != len(targets):
            return None, 'invalid_target'
        proposition_value, reason = _validate_proposition(proposition, mutable_budget=mutable_budget)
        if reason:
            return None, reason
        canonical_target = ''
        canonical_targets = targets
    else:
        canonical_target, reason = _validate_target(target)
        if reason:
            return None, reason
        if proposition or targets:
            return None, 'invalid_operation'
        proposition_value = ''
        canonical_targets = []

    return {
        'subject': subject,
        'verdict': verdict,
        'operation': operation,
        'proposition': proposition_value,
        'target': canonical_target,
        'targets': canonical_targets,
        'reason_code': reason_code,
        'continuity_kind': continuity_kind,
        'source_refs': source_refs,
        'guard_notes': guard_notes,
    }, ''


def _validate_persistent_operation_compatibility(subject_verdicts: Sequence[Mapping[str, Any]]) -> str:
    tighten_targets: set[str] = set()
    clear_targets: set[str] = set()
    merge_targets: set[str] = set()
    for item in subject_verdicts:
        if _text(item.get('verdict')) != 'persist':
            continue
        operation = _text(item.get('operation'))
        if operation == 'tighten':
            target = _text(item.get('target'))
            if target in tighten_targets or target in clear_targets or target in merge_targets:
                return 'impossible_mutation'
            tighten_targets.add(target)
        elif operation == 'clear_obsolete':
            target = _text(item.get('target'))
            if target in clear_targets or target in tighten_targets or target in merge_targets:
                return 'impossible_mutation'
            clear_targets.add(target)
        elif operation == 'merge':
            targets = set(_text(target) for target in _list(item.get('targets')))
            if targets & tighten_targets or targets & clear_targets or targets & merge_targets:
                return 'impossible_mutation'
            merge_targets.update(targets)
    return ''


def validate_mutable_judge_contract(
    payload: Mapping[str, Any],
    *,
    mutable_budget: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str]:
    if not isinstance(payload, Mapping):
        return None, 'schema_invalid'
    if set(payload.keys()) != _TOP_LEVEL_KEYS:
        return None, 'schema_invalid'
    if _text(payload.get('schema_version')) != SCHEMA_VERSION:
        return None, 'schema_invalid'

    meta = _mapping(payload.get('meta'))
    if set(meta.keys()) != _META_KEYS:
        return None, 'schema_invalid'
    if _text(meta.get('execution_status')) != 'complete':
        return None, 'schema_invalid'
    if int(meta.get('window_pairs_count') or 0) != WINDOW_PAIRS_COUNT:
        return None, 'schema_invalid'
    if meta.get('window_complete') is not True:
        return None, 'schema_invalid'

    raw_verdicts = payload.get('verdicts')
    if not isinstance(raw_verdicts, list) or not raw_verdicts:
        return None, 'schema_invalid'

    verdicts: list[dict[str, Any]] = []
    by_subject: dict[str, list[dict[str, Any]]] = {'llm': [], 'user': []}
    for raw_item in raw_verdicts:
        item = _mapping(raw_item)
        if not item:
            return None, 'schema_invalid'
        validated, reason = _validate_verdict_item(item, mutable_budget=mutable_budget)
        if validated is None:
            return None, reason or 'schema_invalid'
        verdicts.append(validated)
        by_subject[validated['subject']].append(validated)

    if not by_subject['llm'] or not by_subject['user']:
        return None, 'schema_invalid'
    for subject, subject_verdicts in by_subject.items():
        if len(subject_verdicts) > 1 and any(item['verdict'] == 'no_change' for item in subject_verdicts):
            return None, 'schema_invalid'
        compatibility_reason = _validate_persistent_operation_compatibility(subject_verdicts)
        if compatibility_reason:
            return None, compatibility_reason

    return {
        'schema_version': SCHEMA_VERSION,
        'meta': {
            'execution_status': 'complete',
            'window_pairs_count': WINDOW_PAIRS_COUNT,
            'window_complete': True,
        },
        'verdicts': verdicts,
    }, ''


def build_judge_observability(contract: Mapping[str, Any]) -> dict[str, Any]:
    verdicts = [_mapping(item) for item in _list(contract.get('verdicts'))]
    verdict_counts: dict[str, int] = {}
    subjects_touched: set[str] = set()
    subjects_seen: set[str] = set()
    operation_kinds: set[str] = set()
    continuity_kinds: set[str] = set()
    reason_codes: set[str] = set()
    source_refs_count = 0
    guard_notes_count = 0
    persistent_operation_count = 0
    for item in verdicts:
        subject = _text(item.get('subject'))
        verdict = _text(item.get('verdict'))
        operation = _text(item.get('operation'))
        continuity_kind = _text(item.get('continuity_kind'))
        reason_code = _text(item.get('reason_code'))
        if subject:
            subjects_seen.add(subject)
        if verdict:
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
            if verdict in {'persist', 'raise_tension', 'reject', 'defer'} and subject:
                subjects_touched.add(subject)
        if operation:
            operation_kinds.add(operation)
            persistent_operation_count += 1
        if continuity_kind:
            continuity_kinds.add(continuity_kind)
        if reason_code:
            reason_codes.add(reason_code)
        source_refs_count += len(_list(item.get('source_refs')))
        guard_notes_count += len(_list(item.get('guard_notes')))

    meta = _mapping(contract.get('meta'))
    return {
        'status': 'ok',
        'reason_code': 'judge_complete',
        'schema_version': _text(contract.get('schema_version')),
        'prompt_kind': PROMPT_KIND,
        'window_pairs_count': int(meta.get('window_pairs_count') or 0),
        'window_complete': meta.get('window_complete') is True,
        'verdict_count': len(verdicts),
        'verdict_counts': verdict_counts,
        'subjects_seen': sorted(subjects_seen),
        'subjects_touched': sorted(subjects_touched),
        'operation_kinds': sorted(operation_kinds),
        'persistent_operation_count': persistent_operation_count,
        'continuity_kinds': sorted(continuity_kinds),
        'reason_codes': sorted(reason_codes),
        'source_refs_count': source_refs_count,
        'guard_notes_count': guard_notes_count,
    }


def run_mutable_identity_judge(judge_input: Mapping[str, Any]) -> dict[str, Any]:
    settings = runtime_model_settings()
    try:
        system_prompt = load_prompt()
    except Exception:
        return _failure_result('runtime_safety_violation')
    model_input_json = _judge_input_json(judge_input)
    size_guard = _judge_size_guard(
        judge_input=judge_input,
        system_prompt=system_prompt,
        model_input_json=model_input_json,
    )
    if not size_guard['ok']:
        logger.warning(
            'mutable_identity_judge_window_too_large model=%s window_chars=%s payload_chars=%s estimated_prompt_tokens=%s',
            settings['model'],
            size_guard['window_chars'],
            size_guard['payload_chars'],
            size_guard['estimated_prompt_tokens'],
        )
        return _failure_result(
            'window_too_large',
            {
                key: value
                for key, value in size_guard.items()
                if key != 'ok'
            },
        )
    model_payload = build_openrouter_payload(
        judge_input,
        model_settings=settings,
        system_prompt=system_prompt,
    )

    try:
        response = requests.post(
            llm_client.or_chat_completions_url(),
            json=model_payload,
            headers=_headers(),
            timeout=settings['timeout_s'],
        )
        response.raise_for_status()
        response_payload = llm_client.read_openrouter_response_payload(response)
        provider_metadata = llm_client.extract_openrouter_provider_metadata(
            response_payload,
            requested_model=settings['model'],
        )
        provider_metadata.setdefault('provider_caller', CALLER)
        provider_metadata.setdefault('provider_title', 'FridaDev / Mutable Identity Judge')
        llm_client.log_provider_metadata(
            logger,
            'mutable_identity_judge_provider_response',
            provider_metadata,
        )
        raw = llm_client.extract_openrouter_text(response_payload)
    except requests.exceptions.Timeout:
        logger.warning('mutable_identity_judge_timeout model=%s', settings['model'])
        return _failure_result('judge_timeout')
    except requests.exceptions.RequestException as exc:
        logger.warning('mutable_identity_judge_transport_error model=%s err=%s', settings['model'], exc.__class__.__name__)
        return _failure_result('judge_transport_error')
    except Exception as exc:
        logger.error('mutable_identity_judge_transport_error err=%s', exc.__class__.__name__)
        return _failure_result('judge_transport_error')

    parsed = _safe_json_loads(raw)
    if parsed is None:
        return _failure_result('judge_invalid_json')

    validated, reason = validate_mutable_judge_contract(
        parsed,
        mutable_budget=_mapping(judge_input.get('mutable_budget')),
    )
    if validated is None:
        return _failure_result(reason or 'schema_invalid')
    return {
        'status': 'ok',
        'reason_code': 'judge_complete',
        'contract': validated,
        'observability': build_judge_observability(validated),
    }
