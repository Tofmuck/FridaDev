from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from memory import mutable_identity_judge
from memory import mutable_identity_judge_schema


SCHEMA_VERSION = 'mutable_judge_v2'
PROMPT_KIND = 'mutable_identity_judge_v2'
PROMPT_PATH = 'prompts/identity_mutable_judge_v2.txt'
MODEL_SLOT = mutable_identity_judge.MODEL_SLOT
CALLER = mutable_identity_judge.CALLER
JUDGE_WINDOW_MAX_CHARS = mutable_identity_judge.JUDGE_WINDOW_MAX_CHARS
JUDGE_ESTIMATED_PROMPT_TOKEN_LIMIT = mutable_identity_judge.JUDGE_ESTIMATED_PROMPT_TOKEN_LIMIT

ALLOWED_SUBJECTS = {'llm', 'user'}
ALLOWED_VERDICTS = {'no_change', 'add'}
ALLOWED_CONTINUITY_KINDS = {'identity', 'relation', 'value', 'limit', 'posture', 'none'}
ADD_REASON_CODES = {
    'explicit_self_definition_continuity',
    'explicit_self_value_continuity',
    'explicit_self_limit_continuity',
    'explicit_relation_continuity',
    'explicit_frida_self_definition_continuity',
    'explicit_frida_limit_continuity',
    'explicit_posture_continuity',
}
NO_CHANGE_REASON_CODES = {
    'no_mutable_identity_signal',
    'already_covered_by_static',
    'already_covered_by_mutable',
    'task_local_not_identity',
    'temporary_state',
    'ambiguous_subject',
    'insufficient_context',
    'source_scope_unclear',
    'quoted_or_reported_speech',
    'project_policy_not_identity',
}
MODEL_OUTPUT_REASON_CODES = ADD_REASON_CODES | NO_CHANGE_REASON_CODES

_TOP_LEVEL_KEYS = {'schema_version', 'meta', 'verdicts'}
_META_KEYS = {'execution_status', 'window_pairs_count', 'window_complete'}
_VERDICT_KEYS = {
    'subject',
    'verdict',
    'proposition',
    'reason_code',
    'continuity_kind',
    'source_refs',
    'guard_notes',
}
_ALLOWED_SOURCE_REFS = {f'pair_{index:02d}' for index in range(1, mutable_identity_judge.WINDOW_PAIRS_COUNT + 1)}
_CODE_RE = re.compile(r'^[A-Za-z0-9_:-]{1,80}$')
_PROMPT_LIKE_RE = re.compile(
    r'(ignore\s+previous|system\s+prompt|developer\s+message|follow\s+these\s+instructions|'
    r'tu\s+dois\s+repondre|reponds\s+comme)',
    re.IGNORECASE,
)


def _text(value: Any) -> str:
    if value is None:
        return ''
    return str(value).strip()


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    return []


def load_prompt_v2(prompt_path: str | None = None) -> str:
    raw_path = _text(prompt_path or PROMPT_PATH)
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    return path.read_text(encoding='utf-8').strip()


def build_judge_messages_v2(judge_input: Mapping[str, Any], *, system_prompt: str) -> list[dict[str, str]]:
    return [
        {'role': 'system', 'content': str(system_prompt or '').strip()},
        {'role': 'user', 'content': json.dumps(dict(judge_input), ensure_ascii=False, indent=2)},
    ]


def build_openrouter_payload_v2(
    judge_input: Mapping[str, Any],
    *,
    model_settings: Mapping[str, Any],
    system_prompt: str,
) -> dict[str, Any]:
    return {
        'model': _text(model_settings.get('model')),
        'messages': build_judge_messages_v2(judge_input, system_prompt=system_prompt),
        'temperature': float(model_settings.get('temperature')),
        'top_p': float(model_settings.get('top_p')),
        'max_tokens': int(model_settings.get('max_tokens')),
        'response_format': mutable_identity_judge_schema.build_mutable_judge_v2_response_format(
            schema_version=SCHEMA_VERSION,
            subjects=ALLOWED_SUBJECTS,
            verdicts=ALLOWED_VERDICTS,
            reason_codes=MODEL_OUTPUT_REASON_CODES,
            continuity_kinds=ALLOWED_CONTINUITY_KINDS,
            source_refs=_ALLOWED_SOURCE_REFS,
        ),
        'provider': {
            'require_parameters': True,
            'order': ['anthropic'],
        },
        'metadata': {
            'frida_caller': CALLER,
            'frida_slot': MODEL_SLOT,
            'frida_contract': SCHEMA_VERSION,
            'frida_contract_status': 'dormant_until_lot_b',
        },
        'trace': {
            'trace_name': 'FridaDev',
            'generation_name': 'FridaDev / Mutable Identity Judge v2 Dormant',
        },
    }


def _validate_code_list(values: list[Any]) -> bool:
    return all(isinstance(value, str) and bool(_CODE_RE.fullmatch(value)) for value in values)


def _validate_proposition(proposition: str) -> str:
    if not proposition:
        return 'empty_proposition'
    if len(proposition) > 600:
        return 'proposition_too_long'
    if _PROMPT_LIKE_RE.search(proposition):
        return 'prompt_like_content'
    if proposition.endswith('?'):
        return 'non_declarative_content'
    return ''


def validate_mutable_judge_contract_v2(payload: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str]:
    source = _mapping(payload)
    if set(source.keys()) != _TOP_LEVEL_KEYS:
        return None, 'schema_invalid'
    if _text(source.get('schema_version')) != SCHEMA_VERSION:
        return None, 'schema_invalid'

    meta = _mapping(source.get('meta'))
    if set(meta.keys()) != _META_KEYS:
        return None, 'schema_invalid'
    if _text(meta.get('execution_status')) != 'complete':
        return None, 'schema_invalid'
    if int(meta.get('window_pairs_count') or 0) != mutable_identity_judge.WINDOW_PAIRS_COUNT:
        return None, 'schema_invalid'
    if meta.get('window_complete') is not True:
        return None, 'schema_invalid'

    verdicts = _list(source.get('verdicts'))
    if not verdicts:
        return None, 'schema_invalid'

    seen_subjects: set[str] = set()
    normalized_verdicts: list[dict[str, Any]] = []
    for raw_verdict in verdicts:
        verdict_payload = _mapping(raw_verdict)
        if set(verdict_payload.keys()) != _VERDICT_KEYS:
            return None, 'schema_invalid'

        subject = _text(verdict_payload.get('subject'))
        verdict = _text(verdict_payload.get('verdict'))
        proposition = _text(verdict_payload.get('proposition'))
        reason_code = _text(verdict_payload.get('reason_code'))
        continuity_kind = _text(verdict_payload.get('continuity_kind'))
        source_refs = [_text(item) for item in _list(verdict_payload.get('source_refs'))]
        guard_notes = [_text(item) for item in _list(verdict_payload.get('guard_notes'))]

        if subject not in ALLOWED_SUBJECTS:
            return None, 'invalid_subject'
        if verdict not in ALLOWED_VERDICTS:
            return None, 'invalid_verdict'
        if reason_code not in MODEL_OUTPUT_REASON_CODES:
            return None, 'schema_invalid'
        if continuity_kind not in ALLOWED_CONTINUITY_KINDS:
            return None, 'schema_invalid'
        if any(source_ref not in _ALLOWED_SOURCE_REFS for source_ref in source_refs):
            return None, 'schema_invalid'
        if not _validate_code_list(guard_notes):
            return None, 'schema_invalid'

        if verdict == 'add':
            if reason_code not in ADD_REASON_CODES:
                return None, 'schema_invalid'
            proposition_reason = _validate_proposition(proposition)
            if proposition_reason:
                return None, proposition_reason
            if not source_refs:
                return None, 'schema_invalid'
        else:
            if reason_code not in NO_CHANGE_REASON_CODES:
                return None, 'schema_invalid'
            if proposition:
                return None, 'invalid_verdict'

        seen_subjects.add(subject)
        normalized_verdicts.append(
            {
                'subject': subject,
                'verdict': verdict,
                'proposition': proposition,
                'reason_code': reason_code,
                'continuity_kind': continuity_kind,
                'source_refs': source_refs,
                'guard_notes': guard_notes,
            }
        )

    if seen_subjects != ALLOWED_SUBJECTS:
        return None, 'schema_invalid'
    for subject in ALLOWED_SUBJECTS:
        subject_verdicts = [
            _text(verdict_payload.get('verdict'))
            for verdict_payload in normalized_verdicts
            if _text(verdict_payload.get('subject')) == subject
        ]
        if 'no_change' in subject_verdicts and len(subject_verdicts) > 1:
            return None, 'invalid_verdict'

    return {
        'schema_version': SCHEMA_VERSION,
        'meta': {
            'execution_status': 'complete',
            'window_pairs_count': mutable_identity_judge.WINDOW_PAIRS_COUNT,
            'window_complete': True,
        },
        'verdicts': normalized_verdicts,
    }, ''


def build_judge_observability_v2(contract: Mapping[str, Any]) -> dict[str, Any]:
    verdict_counts: dict[str, int] = {}
    subjects_seen: set[str] = set()
    subjects_touched: set[str] = set()
    reason_codes: set[str] = set()
    continuity_kinds: set[str] = set()
    source_refs_count = 0
    guard_notes_count = 0
    add_count = 0

    for verdict_payload in _list(_mapping(contract).get('verdicts')):
        verdict = _text(_mapping(verdict_payload).get('verdict'))
        subject = _text(_mapping(verdict_payload).get('subject'))
        reason_code = _text(_mapping(verdict_payload).get('reason_code'))
        continuity_kind = _text(_mapping(verdict_payload).get('continuity_kind'))
        source_refs = _list(_mapping(verdict_payload).get('source_refs'))
        guard_notes = _list(_mapping(verdict_payload).get('guard_notes'))
        if verdict:
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        if subject:
            subjects_seen.add(subject)
        if verdict == 'add':
            subjects_touched.add(subject)
            add_count += 1
        if reason_code:
            reason_codes.add(reason_code)
        if continuity_kind:
            continuity_kinds.add(continuity_kind)
        source_refs_count += len(source_refs)
        guard_notes_count += len(guard_notes)

    return {
        'schema_version': SCHEMA_VERSION,
        'contract_status': 'dormant_until_lot_b',
        'verdict_counts': dict(sorted(verdict_counts.items())),
        'subjects_seen': sorted(subjects_seen),
        'subjects_touched': sorted(subjects_touched),
        'add_count': add_count,
        'operation_kinds': [],
        'reason_codes': sorted(reason_codes),
        'continuity_kinds': sorted(continuity_kinds),
        'source_refs_count': source_refs_count,
        'guard_notes_count': guard_notes_count,
    }
