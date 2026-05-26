from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Mapping

import requests

import config
from core import llm_client
from memory import mutable_identity_judge
from memory import mutable_identity_judge_schema


logger = logging.getLogger('frida.mutable_identity_judge')

SCHEMA_VERSION = 'mutable_judge_v2'
INPUT_SCHEMA_VERSION = 'mutable_identity_judge_input_v2'
PROMPT_KIND = 'mutable_identity_judge_v2'
PROMPT_PATH = 'prompts/identity_mutable_judge_v2.txt'
CONTRACT_STATUS = 'active_add_only_lot_b'
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
    r'tu\s+dois\s+repondre|tu\s+dois\s+répondre|reponds\s+comme|réponds\s+comme)',
    re.IGNORECASE,
)
_JSON_FENCE_RE = re.compile(r'^\s*```(?:json)?\s*(?P<body>.*?)\s*```\s*$', re.IGNORECASE | re.DOTALL)


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


def build_judge_input(
    *,
    window_pairs: Any,
    identities: Mapping[str, Any],
    mutable_budget: Mapping[str, Any],
    source_annotations: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        'schema_version': INPUT_SCHEMA_VERSION,
        'window_pairs': mutable_identity_judge._normalize_window_pairs(window_pairs),
        'identities': mutable_identity_judge._normalized_identities(identities),
        'mutable_budget': mutable_identity_judge._normalized_budget(mutable_budget),
        'judgment_rules': {
            'judge_reads_full_window': True,
            'python_must_not_score_identity': True,
            'python_must_not_preselect_semantic_candidates': True,
            'same_regime_for_subjects': ['llm', 'user'],
            'allowed_verdicts': sorted(ALLOWED_VERDICTS),
            'allowed_continuity_kinds': sorted(ALLOWED_CONTINUITY_KINDS),
            'model_output_reason_codes': {
                'add': sorted(ADD_REASON_CODES),
                'no_change': sorted(NO_CHANGE_REASON_CODES),
            },
            'technical_reason_codes_not_model_output': sorted(mutable_identity_judge.TECHNICAL_REASON_CODES),
            'automatic_operations_forbidden': [
                'tighten',
                'merge',
                'clear_obsolete',
                'target',
                'targets',
                'target_ref',
                'target_refs',
            ],
            'automatic_writes': ['identity_mutables'],
            'static_writes_forbidden': True,
        },
        'source_annotations': mutable_identity_judge._compact_annotation_value(source_annotations or {}),
    }


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
            'frida_contract_status': CONTRACT_STATUS,
        },
        'trace': {
            'trace_name': 'FridaDev',
            'generation_name': 'FridaDev / Mutable Identity Judge v2 Add-Only',
        },
    }


def _headers() -> dict[str, Any]:
    return llm_client.or_headers_custom(
        caller=CALLER,
        referer=config.OR_REFERER_IDENTITY_PERIODIC,
        title='FridaDev / Mutable Identity Judge v2',
    )


def _safe_json_loads(raw: Any) -> Mapping[str, Any] | None:
    text = _text(raw)
    candidates = [text]
    fenced = _JSON_FENCE_RE.fullmatch(text)
    if fenced:
        candidates.append(_text(fenced.group('body')))
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, Mapping):
            return parsed
    return None


def _failure_result(reason_code: str, observability_fields: Mapping[str, Any] | None = None) -> dict[str, Any]:
    observability = {
        'status': 'skipped',
        'reason_code': reason_code,
        'schema_version': SCHEMA_VERSION,
        'prompt_kind': PROMPT_KIND,
    }
    observability.update(dict(_mapping(observability_fields)))
    return {
        'status': 'skipped',
        'reason_code': reason_code,
        'contract': None,
        'observability': observability,
    }


def _request_exception_observability(exc: BaseException) -> dict[str, Any]:
    response = getattr(exc, 'response', None)
    status_code = getattr(response, 'status_code', None)
    payload: dict[str, Any] = {'error_class': exc.__class__.__name__}
    if status_code is not None:
        payload['http_status'] = int(status_code)
    return payload


def _estimated_prompt_tokens(char_count: int) -> int:
    if char_count <= 0:
        return 0
    return (int(char_count) + 3) // 4


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


def _verdict_failure_observability(item: Mapping[str, Any], *, reason_code: str, index: int) -> dict[str, Any]:
    return {
        'validation_reason': reason_code,
        'invalid_verdict_index': index,
        'invalid_subject': _text(item.get('subject')).lower(),
        'invalid_verdict': _text(item.get('verdict')).lower(),
        'invalid_reason_code': _text(item.get('reason_code')),
        'invalid_proposition_chars': len(_text(item.get('proposition'))),
        'invalid_source_refs_count': len(_list(item.get('source_refs'))),
        'invalid_guard_notes_count': len(_list(item.get('guard_notes'))),
    }


def _validation_failure_observability(payload: Mapping[str, Any], *, reason_code: str) -> dict[str, Any]:
    observability: dict[str, Any] = {'validation_reason': reason_code}
    verdicts = payload.get('verdicts')
    if not isinstance(verdicts, list):
        return observability
    for index, raw_item in enumerate(verdicts, start=1):
        item = _mapping(raw_item)
        if not item:
            return {**observability, 'invalid_verdict_index': index}
        validated, item_reason = validate_mutable_judge_contract_v2(
            {
                'schema_version': SCHEMA_VERSION,
                'meta': {
                    'execution_status': 'complete',
                    'window_pairs_count': mutable_identity_judge.WINDOW_PAIRS_COUNT,
                    'window_complete': True,
                },
                'verdicts': [item, _minimal_no_change('llm' if _text(item.get('subject')) == 'user' else 'user')],
            }
        )
        if validated is None:
            return _verdict_failure_observability(
                item,
                reason_code=item_reason or reason_code or 'schema_invalid',
                index=index,
            )
    return observability


def _minimal_no_change(subject: str) -> dict[str, Any]:
    return {
        'subject': subject,
        'verdict': 'no_change',
        'proposition': '',
        'reason_code': 'no_mutable_identity_signal',
        'continuity_kind': 'none',
        'source_refs': [],
        'guard_notes': [],
    }


def _validate_code_list(values: list[Any]) -> bool:
    return all(isinstance(value, str) and bool(_CODE_RE.fullmatch(value)) for value in values)


def _validate_proposition(proposition: str) -> str:
    if not proposition:
        return 'empty_proposition'
    if len(proposition) > 600:
        return 'proposition_too_long'
    if '\n' in proposition or _PROMPT_LIKE_RE.search(proposition):
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
        'status': 'ok',
        'reason_code': 'judge_complete',
        'schema_version': SCHEMA_VERSION,
        'prompt_kind': PROMPT_KIND,
        'contract_status': CONTRACT_STATUS,
        'window_pairs_count': int(_mapping(contract.get('meta')).get('window_pairs_count') or 0),
        'window_complete': _mapping(contract.get('meta')).get('window_complete') is True,
        'verdict_count': sum(verdict_counts.values()),
        'verdict_counts': dict(sorted(verdict_counts.items())),
        'subjects_seen': sorted(subjects_seen),
        'subjects_touched': sorted(subjects_touched),
        'add_count': add_count,
        'reason_codes': sorted(reason_codes),
        'continuity_kinds': sorted(continuity_kinds),
        'source_refs_count': source_refs_count,
        'guard_notes_count': guard_notes_count,
    }


def run_mutable_identity_judge_v2(judge_input: Mapping[str, Any]) -> dict[str, Any]:
    settings = mutable_identity_judge.runtime_model_settings()
    try:
        system_prompt = load_prompt_v2()
    except Exception:
        return _failure_result('runtime_safety_violation')
    model_input_json = json.dumps(dict(judge_input), ensure_ascii=False, indent=2)
    size_guard = _judge_size_guard(
        judge_input=judge_input,
        system_prompt=system_prompt,
        model_input_json=model_input_json,
    )
    if not size_guard['ok']:
        logger.warning(
            'mutable_identity_judge_v2_window_too_large model=%s window_chars=%s payload_chars=%s estimated_prompt_tokens=%s',
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

    model_payload = build_openrouter_payload_v2(
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
        provider_metadata.setdefault('provider_title', 'FridaDev / Mutable Identity Judge v2')
        provider_metadata.setdefault('provider_contract', SCHEMA_VERSION)
        llm_client.log_provider_metadata(
            logger,
            'mutable_identity_judge_provider_response',
            provider_metadata,
        )
        raw = llm_client.extract_openrouter_text(response_payload)
    except requests.exceptions.Timeout:
        logger.warning('mutable_identity_judge_v2_timeout model=%s', settings['model'])
        return _failure_result('judge_timeout')
    except requests.exceptions.RequestException as exc:
        logger.warning('mutable_identity_judge_v2_transport_error model=%s err=%s', settings['model'], exc.__class__.__name__)
        return _failure_result('judge_transport_error', _request_exception_observability(exc))
    except Exception as exc:
        logger.error('mutable_identity_judge_v2_transport_error err=%s', exc.__class__.__name__)
        return _failure_result('judge_transport_error')

    parsed = _safe_json_loads(raw)
    if parsed is None:
        return _failure_result('judge_invalid_json')

    validated, reason = validate_mutable_judge_contract_v2(parsed)
    if validated is None:
        failure_reason = reason or 'schema_invalid'
        return _failure_result(
            failure_reason,
            _validation_failure_observability(parsed, reason_code=failure_reason),
        )
    return {
        'status': 'ok',
        'reason_code': 'judge_complete',
        'contract': validated,
        'observability': build_judge_observability_v2(validated),
    }
