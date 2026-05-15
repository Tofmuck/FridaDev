from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence


SENSITIVE_TEXT_PATTERNS = (
    re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----', re.IGNORECASE),
    re.compile(r'\b(?:sk|pk|rk)-[A-Za-z0-9_\-]{16,}\b'),
    re.compile(r'\b(?:api[_-]?key|token|secret|password|passwd|credential|authorization)\s*[:=]', re.IGNORECASE),
    re.compile(r'\b(?:postgres|postgresql|mysql|redis|mongodb)://', re.IGNORECASE),
    re.compile(r'\b[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|PRIVATE_KEY|DSN)\s*=', re.IGNORECASE),
    re.compile(r'\.env\b', re.IGNORECASE),
)

CONTENT_ITEM_SPECS: tuple[dict[str, Any], ...] = (
    {
        'key': 'conversation_input',
        'label_fr': 'Message recu par Frida',
        'stage_prefixes': ('turn_start', 'UserMessage'),
        'exact_paths': (('user_msg',), ('message',), ('content',)),
        'partial_paths': (('message_preview',), ('preview',)),
    },
    {
        'key': 'main_model_payload',
        'label_fr': 'Payload du modele principal',
        'stage_prefixes': ('llm_payload', 'llm_call', 'prompt_prepared'),
        'payload_filters': ({'provider_caller': 'llm'}, {'main_llm_payload': True}),
        'exact_paths': (
            ('prompt_messages',),
            ('messages',),
            ('prompt',),
            ('payload', 'messages'),
            ('request_payload', 'messages'),
            ('model_payload', 'messages'),
        ),
        'partial_paths': (('messages_preview',), ('prompt_preview',), ('payload_preview',)),
    },
    {
        'key': 'secondary_provider_payloads',
        'label_fr': 'Payloads des providers secondaires',
        'stage_suffixes': ('_prompt_prepared',),
        'payload_filters': ({'secondary_provider_payload': True},),
        'exact_paths': (
            ('messages',),
            ('prompt',),
            ('provider_payload',),
            ('payload', 'messages'),
        ),
        'partial_paths': (('messages_preview',), ('prompt_preview',), ('preview',)),
    },
    {
        'key': 'memory_content',
        'label_fr': 'Contenu memoire injecte',
        'stage_prefixes': ('memory',),
        'exact_paths': (
            ('memory_traces',),
            ('memory_context',),
            ('trace_content',),
            ('summary_content',),
            ('content',),
        ),
        'partial_paths': (('content_preview',), ('summary_preview',), ('preview',)),
    },
    {
        'key': 'identity_content',
        'label_fr': 'Contenu identite injecte',
        'stage_contains': ('identity',),
        'exact_paths': (('identity_block',), ('identity_content',), ('content',)),
        'partial_paths': (('identity_preview',), ('content_preview',), ('preview',)),
    },
    {
        'key': 'web_content',
        'label_fr': 'Contenu web injecte',
        'stage_contains': ('web',),
        'exact_paths': (('context_block',), ('query',), ('results',), ('content',)),
        'partial_paths': (('context_preview',), ('query_preview',), ('preview',)),
    },
    {
        'key': 'hermeneutic_content',
        'label_fr': 'Contenu hermeneutique',
        'stage_contains': ('hermeneutic', 'primary_node'),
        'exact_paths': (('judgment',), ('node_state',), ('content',)),
        'partial_paths': (('judgment_preview',), ('content_preview',), ('preview',)),
    },
)

_EVIDENCE_KEY_ALLOWLIST = {
    'model',
    'provider_caller',
    'provider_title',
    'prompt_kind',
    'payload_kind',
    'status',
    'reason_code',
    'error_code',
    'message_count',
    'messages_count',
    'role_counts',
    'schema_version',
    'main_llm_payload',
    'secondary_provider_payload',
    'query_present',
    'results',
    'results_count',
}

_FORBIDDEN_EVIDENCE_KEYS = {
    'message',
    'messages',
    'prompt',
    'prompt_messages',
    'payload',
    'request_payload',
    'model_payload',
    'content',
    'context_block',
    'query',
    'identity_block',
    'memory_traces',
    'memory_context',
    'canonical_inputs',
    'provider_payload',
}


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _text(value: Any) -> str:
    return str(value or '').strip()


def _short_hash(value: Any) -> str | None:
    text = _serialize_content(value)
    if not text:
        return None
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def _serialize_content(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    except (TypeError, ValueError):
        return str(value)


def _path_get(payload: Mapping[str, Any], path: Sequence[str]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current.get(key)
    return current


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _contains_sensitive_text(value: Any) -> bool:
    text = _serialize_content(value)
    if not text:
        return False
    return any(pattern.search(text) for pattern in SENSITIVE_TEXT_PATTERNS)


def _stage_matches(event: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    stage = _text(event.get('stage'))
    payload = _mapping(event.get('payload'))
    prefixes = tuple(str(item) for item in _sequence(spec.get('stage_prefixes')))
    suffixes = tuple(str(item) for item in _sequence(spec.get('stage_suffixes')))
    contains = tuple(str(item) for item in _sequence(spec.get('stage_contains')))
    filters = _sequence(spec.get('payload_filters'))

    if prefixes and any(stage == prefix or stage.startswith(prefix) for prefix in prefixes):
        return True
    if suffixes and any(stage.endswith(suffix) for suffix in suffixes):
        return True
    if contains and any(part in stage for part in contains):
        return True
    for expected in filters:
        expected_mapping = _mapping(expected)
        if expected_mapping and all(payload.get(key) == value for key, value in expected_mapping.items()):
            return True
    return False


def _compact_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    for key, value in sorted(payload.items(), key=lambda item: str(item[0])):
        key_s = str(key or '')
        if not key_s or key_s in _FORBIDDEN_EVIDENCE_KEYS:
            continue
        if (
            key_s in _EVIDENCE_KEY_ALLOWLIST
            or key_s.endswith('_chars')
            or key_s.endswith('_sha256_12')
            or key_s.endswith('_count')
            or key_s.endswith('_counts')
            or key_s.endswith('_present')
            or key_s.endswith('_available')
            or key_s.endswith('_included')
            or key_s.endswith('_injected')
        ):
            if isinstance(value, (str, int, float, bool)) or value is None:
                evidence[key_s] = value
            elif isinstance(value, Mapping):
                nested = {
                    str(nested_key): nested_value
                    for nested_key, nested_value in value.items()
                    if isinstance(nested_value, (str, int, float, bool)) or nested_value is None
                }
                if nested:
                    evidence[key_s] = nested
    return evidence


def _event_summary(event: Mapping[str, Any]) -> dict[str, Any]:
    payload = _mapping(event.get('payload'))
    return {
        'event_id': _text(event.get('event_id')) or None,
        'stage': _text(event.get('stage')) or None,
        'status': _text(event.get('status')) or None,
        'ts': _text(event.get('ts')) or None,
        'evidence': _compact_evidence(payload),
    }


def _item_from_content(
    *,
    spec: Mapping[str, Any],
    event: Mapping[str, Any],
    value: Any,
    status: str,
    explanation_fr: str,
) -> dict[str, Any]:
    serialized = _serialize_content(value)
    base = {
        'key': _text(spec.get('key')),
        'label_fr': _text(spec.get('label_fr')),
        'status': status,
        'status_fr': _status_label_fr(status),
        'content_chars': len(serialized),
        'content_sha256_12': _short_hash(value),
        'source': _event_summary(event),
        'explanation_fr': explanation_fr,
        'redaction': {'secret_blocked': False},
    }
    if _contains_sensitive_text(value):
        base.update(
            {
                'status': 'blocked_sensitive',
                'status_fr': _status_label_fr('blocked_sensitive'),
                'content_text': None,
                'explanation_fr': (
                    'Un contenu existe pour cette source, mais il ressemble a un secret ou credential. '
                    'Il est bloque par le gate.'
                ),
                'redaction': {'secret_blocked': True},
            }
        )
        return base
    base['content_text'] = serialized
    return base


def _status_label_fr(status: str) -> str:
    labels = {
        'exact_available': 'contenu exact disponible',
        'partial_available': 'contenu partiel disponible',
        'fingerprint_only': 'empreinte seule disponible',
        'not_reconstructible': 'non reconstructible',
        'blocked_sensitive': 'bloque par garde secret',
    }
    return labels.get(status, 'a verifier')


def _best_item_for_spec(spec: Mapping[str, Any], events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    matching_events = [event for event in events if _stage_matches(event, spec)]
    exact_paths = tuple(tuple(path) for path in _sequence(spec.get('exact_paths')))
    partial_paths = tuple(tuple(path) for path in _sequence(spec.get('partial_paths')))

    for event in matching_events:
        payload = _mapping(event.get('payload'))
        for path in exact_paths:
            value = _path_get(payload, path)
            if _has_value(value):
                return _item_from_content(
                    spec=spec,
                    event=event,
                    value=value,
                    status='exact_available',
                    explanation_fr='Contenu exact retrouve dans un evenement source existant.',
                )

    for event in matching_events:
        payload = _mapping(event.get('payload'))
        for path in partial_paths:
            value = _path_get(payload, path)
            if _has_value(value):
                return _item_from_content(
                    spec=spec,
                    event=event,
                    value=value,
                    status='partial_available',
                    explanation_fr='Seul un extrait ou une representation partielle existe dans les logs sources.',
                )

    evidence_events = [
        event
        for event in matching_events
        if _compact_evidence(_mapping(event.get('payload')))
    ]
    if evidence_events:
        return {
            'key': _text(spec.get('key')),
            'label_fr': _text(spec.get('label_fr')),
            'status': 'fingerprint_only',
            'status_fr': _status_label_fr('fingerprint_only'),
            'content_chars': None,
            'content_sha256_12': None,
            'content_text': None,
            'source': _event_summary(evidence_events[0]),
            'explanation_fr': (
                'Les logs sources prouvent des statuts, tailles, counts ou empreintes, '
                'mais pas le contenu exact.'
            ),
            'redaction': {'secret_blocked': False},
        }

    return {
        'key': _text(spec.get('key')),
        'label_fr': _text(spec.get('label_fr')),
        'status': 'not_reconstructible',
        'status_fr': _status_label_fr('not_reconstructible'),
        'content_chars': None,
        'content_sha256_12': None,
        'content_text': None,
        'source': None,
        'explanation_fr': (
            'Aucun evenement source disponible ne contient ce contenu ni une empreinte suffisante '
            'pour le reconstruire.'
        ),
        'redaction': {'secret_blocked': False},
    }


def content_gate_summary(fact: Mapping[str, Any]) -> dict[str, Any]:
    availability = _mapping(fact.get('content_availability'))
    return {
        'kind': 'dashboard_content_gate_summary',
        'action_available': True,
        'action_label_fr': 'Afficher le contenu complet',
        'default_state': 'not_loaded',
        'warning_fr': (
            'Action volontaire: peut afficher du contenu brut si un artefact exact existe. '
            'Aucun contenu complet n est charge avant ce clic.'
        ),
        'availability_hint': {
            'content_comprehension_status': _text(availability.get('content_comprehension_status')) or 'unknown',
            'prompt_manifest_available': bool(availability.get('prompt_manifest_available')),
            'full_content_gate_available': bool(availability.get('full_content_gate_available')),
            'reason_code': _text(availability.get('reason_code')) or None,
        },
        'redaction': {'raw_content_included': False},
    }


def build_content_gate_payload(
    *,
    fact: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    events_truncated: bool = False,
) -> dict[str, Any]:
    normalized_events = [_mapping(event) for event in events]
    items = [_best_item_for_spec(spec, normalized_events) for spec in CONTENT_ITEM_SPECS]
    status_counts: dict[str, int] = {}
    for item in items:
        status = _text(item.get('status')) or 'not_reconstructible'
        status_counts[status] = status_counts.get(status, 0) + 1

    exact_count = status_counts.get('exact_available', 0)
    partial_count = status_counts.get('partial_available', 0)
    fingerprint_count = status_counts.get('fingerprint_only', 0)
    blocked_count = status_counts.get('blocked_sensitive', 0)
    if exact_count and exact_count + partial_count == len(items):
        overall_status = 'exact_available'
    elif exact_count or partial_count:
        overall_status = 'partial_available'
    elif fingerprint_count or blocked_count:
        overall_status = 'fingerprint_only'
    else:
        overall_status = 'not_reconstructible'

    return {
        'kind': 'dashboard_turn_content_gate',
        'conversation_id': _text(fact.get('conversation_id')),
        'turn_id': _text(fact.get('turn_id')),
        'availability': {
            'status': overall_status,
            'status_fr': _status_label_fr(overall_status),
            'status_counts': status_counts,
            'loaded_after_explicit_action': True,
            'preloaded': False,
            'events_truncated': bool(events_truncated),
            'warning_fr': (
                'Contenu charge uniquement apres action explicite. '
                'Les secrets et credentials evidents sont bloques.'
            ),
        },
        'items': items,
        'redaction': {
            'raw_content_included': bool(exact_count or partial_count),
            'secret_blocked_count': blocked_count,
        },
    }


def audit_payload_for_content_gate(payload: Mapping[str, Any]) -> dict[str, Any]:
    availability = _mapping(payload.get('availability'))
    return {
        'surface': 'dashboard',
        'action': 'open_full_content_gate',
        'raw_content_included': False,
        'loaded_after_explicit_action': True,
        'content_status': _text(availability.get('status')) or 'unknown',
        'content_status_counts': _mapping(availability.get('status_counts')),
        'events_truncated': bool(availability.get('events_truncated')),
    }
