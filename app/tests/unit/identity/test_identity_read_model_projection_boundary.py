from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_identity_read_model_projection


RAW_LEGACY_SENTINEL = 'synthetic-legacy-text-must-not-escape'


def _legacy_snapshot(item: dict[str, object]) -> dict[str, object]:
    return {'total_count': 1, 'limit': 7, 'items': [item]}


def _semantic_projection(payload: dict[str, object]) -> dict[str, object]:
    return {
        'canonical': {
            'static_active': payload['static']['actively_injected'],
            'mutable_active': payload['mutable']['actively_injected'],
            'audit_reason': payload['mutable']['last_mutation_audit']['reason_code'],
        },
        'legacy': tuple(
            (
                payload[layer]['storage_kind'],
                payload[layer]['runtime_authority'],
                payload[layer]['actively_injected'],
                payload[layer]['content_minimized'],
            )
            for layer in ('legacy_fragments', 'evidence', 'conflicts')
        ),
    }


class IdentityReadModelProjectionBoundaryTests(unittest.TestCase):
    def test_subject_projection_keeps_canonical_authority_and_minimizes_legacy_layers(self) -> None:
        payload = admin_identity_read_model_projection.build_subject_block(
            subject='llm',
            active_side={
                'static': {
                    'content': 'synthetic-canonical-static',
                    'source': 'synthetic-static-source',
                },
                'mutable': {
                    'content': 'synthetic-canonical-mutable',
                    'source_trace_id': 'trace-synthetic-1',
                    'updated_by': 'synthetic-writer',
                    'update_reason': 'synthetic-reason-code',
                    'updated_ts': '2026-08-19T08:00:00+00:00',
                },
            },
            static_snapshot={
                'raw_content': 'synthetic-canonical-static',
                'source_kind': 'resource_path_content',
                'resource_field': 'llm_identity_path',
                'configured_path': 'synthetic/llm.txt',
                'resolution_kind': 'synthetic',
                'resolved_path': '/synthetic/llm.txt',
                'editable_via': '/api/admin/identity/static',
            },
            mutable_audit={
                'subject': 'llm',
                'mutation_kind': 'set',
                'actor': 'synthetic-writer',
                'reason_code': 'set_applied',
                'old_chars': 0,
                'new_chars': 27,
                'source_trace_id': 'trace-synthetic-1',
                'created_ts': '2026-08-19T08:00:00+00:00',
            },
            legacy_fragments=_legacy_snapshot(
                {
                    'identity_id': 'legacy-fragment-1',
                    'content': RAW_LEGACY_SENTINEL,
                    'content_norm': RAW_LEGACY_SENTINEL,
                    'last_reason': RAW_LEGACY_SENTINEL,
                    'override_reason': RAW_LEGACY_SENTINEL,
                }
            ),
            evidence=_legacy_snapshot(
                {
                    'evidence_id': 'legacy-evidence-1',
                    'content': RAW_LEGACY_SENTINEL,
                    'content_norm': RAW_LEGACY_SENTINEL,
                    'reason': RAW_LEGACY_SENTINEL,
                }
            ),
            conflicts=_legacy_snapshot(
                {
                    'conflict_id': 'legacy-conflict-1',
                    'content_a': RAW_LEGACY_SENTINEL,
                    'content_b': RAW_LEGACY_SENTINEL,
                    'reason': RAW_LEGACY_SENTINEL,
                }
            ),
        )

        expected = {
            'canonical': {
                'static_active': True,
                'mutable_active': True,
                'audit_reason': 'set_applied',
            },
            'legacy': (
                ('identities', 'historical_only', False, True),
                ('identity_evidence', 'historical_only', False, True),
                ('identity_conflicts', 'historical_only', False, True),
            ),
        }
        self.assertEqual(_semantic_projection(payload), expected)
        self.assertNotIn(RAW_LEGACY_SENTINEL, json.dumps({
            'legacy_fragments': payload['legacy_fragments'],
            'evidence': payload['evidence'],
            'conflicts': payload['conflicts'],
        }, sort_keys=True))
        self.assertEqual(payload['legacy_fragments']['items'][0]['content_chars'], len(RAW_LEGACY_SENTINEL))
        self.assertEqual(payload['conflicts']['items'][0]['identity_pair_count'], 2)

        inverted_authority = copy.deepcopy(payload)
        inverted_authority['legacy_fragments']['runtime_authority'] = 'active'
        self.assertNotEqual(_semantic_projection(inverted_authority), expected)


if __name__ == '__main__':
    unittest.main()
