from __future__ import annotations

from typing import Any, Iterable, Mapping


def _sorted(values: Iterable[str]) -> list[str]:
    return sorted(str(value) for value in values)


def build_mutable_judge_response_format(
    *,
    schema_version: str,
    subjects: Iterable[str],
    verdicts: Iterable[str],
    operations: Iterable[str],
    reason_codes: Iterable[str],
    continuity_kinds: Iterable[str],
    source_refs: Iterable[str],
) -> dict[str, Any]:
    """Return the OpenRouter strict JSON Schema envelope for mutable_judge_v1."""
    operation_values = [''] + _sorted(operations)
    return {
        'type': 'json_schema',
        'json_schema': {
            'name': schema_version,
            'strict': True,
            'schema': {
                'type': 'object',
                'additionalProperties': False,
                'required': ['schema_version', 'meta', 'verdicts'],
                'properties': {
                    'schema_version': {'type': 'string', 'enum': [schema_version]},
                    'meta': {
                        'type': 'object',
                        'additionalProperties': False,
                        'required': ['execution_status', 'window_pairs_count', 'window_complete'],
                        'properties': {
                            'execution_status': {'type': 'string', 'enum': ['complete']},
                            'window_pairs_count': {'type': 'integer', 'enum': [5]},
                            'window_complete': {'type': 'boolean', 'enum': [True]},
                        },
                    },
                    'verdicts': {
                        'type': 'array',
                        'minItems': 1,
                        'items': {
                            'type': 'object',
                            'additionalProperties': False,
                            'required': [
                                'subject',
                                'verdict',
                                'operation',
                                'proposition',
                                'target',
                                'targets',
                                'target_ref',
                                'target_refs',
                                'reason_code',
                                'continuity_kind',
                                'source_refs',
                                'guard_notes',
                            ],
                            'properties': {
                                'subject': {'type': 'string', 'enum': _sorted(subjects)},
                                'verdict': {'type': 'string', 'enum': _sorted(verdicts)},
                                'operation': {'type': 'string', 'enum': operation_values},
                                'proposition': {'type': 'string'},
                                'target': {'type': 'string'},
                                'targets': {
                                    'type': 'array',
                                    'items': {'type': 'string'},
                                },
                                'target_ref': {'type': 'string'},
                                'target_refs': {
                                    'type': 'array',
                                    'items': {'type': 'string'},
                                },
                                'reason_code': {'type': 'string', 'enum': _sorted(reason_codes)},
                                'continuity_kind': {'type': 'string', 'enum': _sorted(continuity_kinds)},
                                'source_refs': {
                                    'type': 'array',
                                    'items': {'type': 'string', 'enum': _sorted(source_refs)},
                                },
                                'guard_notes': {
                                    'type': 'array',
                                    'items': {
                                        'type': 'string',
                                        'minLength': 1,
                                        'maxLength': 80,
                                        'pattern': '^[A-Za-z0-9_:-]{1,80}$',
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    }


def response_format_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    response_format = payload.get('response_format')
    json_schema = response_format.get('json_schema') if isinstance(response_format, Mapping) else {}
    schema = json_schema.get('schema') if isinstance(json_schema, Mapping) else {}
    return {
        'response_format_type': response_format.get('type') if isinstance(response_format, Mapping) else None,
        'json_schema_name': json_schema.get('name') if isinstance(json_schema, Mapping) else None,
        'json_schema_strict': bool(json_schema.get('strict')) if isinstance(json_schema, Mapping) else False,
        'json_schema_additional_properties': schema.get('additionalProperties') if isinstance(schema, Mapping) else None,
    }
