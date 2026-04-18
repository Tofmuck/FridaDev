from __future__ import annotations

import copy
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import config
from identity import active_identity_projection
from memory import memory_identity_periodic_apply


def _supportive_buffer(*, proposition: str, support_indexes: set[int]) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for index in range(15):
        if index in support_indexes:
            user_content = f'Utilisateur confirme que {proposition}'
            assistant_content = f'Assistant reformule: {proposition}'
        else:
            user_content = f'utilisateur {index} parle d autre chose'
            assistant_content = f'assistant {index} ne reprend pas ce trait'
        pairs.append(
            {
                'user': {'role': 'user', 'content': user_content},
                'assistant': {'role': 'assistant', 'content': assistant_content},
            }
        )
    return pairs


def _contract_for_user_operations(*operations: dict[str, Any]) -> dict[str, Any]:
    return {
        'llm': {
            'operations': [
                {'kind': 'no_change', 'proposition': '', 'reason': 'stable canon'},
            ]
        },
        'user': {'operations': list(operations)},
        'meta': {
            'execution_status': 'complete',
            'buffer_pairs_count': 15,
            'window_complete': True,
        },
    }


def _build_near_target_mutable(*, slack: int = 70) -> str:
    lines: list[str] = []
    content = ''
    index = 1
    while len(content) < (int(config.IDENTITY_MUTABLE_TARGET_CHARS) - max(1, int(slack))):
        lines.append(f'Tof garde un axe stable {index}.')
        content = '\n'.join(lines)
        index += 1
    return content


class _MutableStore:
    def __init__(self, initial: dict[str, dict[str, Any]] | None = None) -> None:
        self.mutable = copy.deepcopy(initial or {})
        self.upsert_calls: list[tuple[str, str, str, str]] = []
        self.clear_calls: list[str] = []

    def get_mutable_identity(self, subject: str) -> dict[str, Any] | None:
        item = self.mutable.get(subject)
        return copy.deepcopy(item) if item is not None else None

    def upsert_mutable_identity(
        self,
        subject: str,
        content: str,
        source_trace_id: str | None = None,
        *,
        updated_by: str = 'system',
        update_reason: str = '',
    ) -> dict[str, Any]:
        payload = {
            'subject': subject,
            'content': content,
            'source_trace_id': source_trace_id,
            'updated_by': updated_by,
            'update_reason': update_reason,
        }
        self.mutable[subject] = payload
        self.upsert_calls.append((subject, content, updated_by, update_reason))
        return copy.deepcopy(payload)

    def clear_mutable_identity(self, subject: str) -> dict[str, Any] | None:
        self.clear_calls.append(subject)
        previous = self.mutable.pop(subject, None)
        return copy.deepcopy(previous) if previous is not None else None


class IdentityPeriodicContractValidationPhase2Tests(unittest.TestCase):
    def test_validate_periodic_agent_contract_rejects_invalid_topology_meta_and_types(self) -> None:
        cases = [
            (
                'invalid_root',
                [],
                'contract_top_level_keys_invalid',
            ),
            (
                'missing_meta',
                {
                    'llm': {'operations': []},
                    'user': {'operations': []},
                },
                'contract_top_level_keys_invalid',
            ),
            (
                'subject_missing_operations_key',
                {
                    'llm': {},
                    'user': {'operations': []},
                    'meta': {
                        'execution_status': 'complete',
                        'buffer_pairs_count': 15,
                        'window_complete': True,
                    },
                },
                'contract_llm_keys_invalid',
            ),
            (
                'operations_wrong_type',
                {
                    'llm': {'operations': []},
                    'user': {'operations': 'oops'},
                    'meta': {
                        'execution_status': 'complete',
                        'buffer_pairs_count': 15,
                        'window_complete': True,
                    },
                },
                'contract_user_operations_invalid',
            ),
            (
                'meta_window_complete_false',
                {
                    'llm': {'operations': []},
                    'user': {'operations': []},
                    'meta': {
                        'execution_status': 'complete',
                        'buffer_pairs_count': 15,
                        'window_complete': False,
                    },
                },
                'contract_window_complete_invalid',
            ),
            (
                'meta_buffer_mismatch',
                {
                    'llm': {'operations': []},
                    'user': {'operations': []},
                    'meta': {
                        'execution_status': 'complete',
                        'buffer_pairs_count': 14,
                        'window_complete': True,
                    },
                },
                'contract_buffer_pairs_count_mismatch',
            ),
        ]

        for label, payload, expected_reason in cases:
            with self.subTest(label=label):
                contract, reason = memory_identity_periodic_apply.validate_periodic_agent_contract(
                    payload,
                    buffer_pairs_count=15,
                    target_pairs=15,
                )

                self.assertIsNone(contract)
                self.assertEqual(reason, expected_reason)

    def test_validate_periodic_agent_contract_rejects_unknown_partial_and_contradictory_operations(self) -> None:
        cases = [
            (
                'unknown_operation_kind',
                _contract_for_user_operations(
                    {'kind': 'rewrite', 'proposition': 'Tof garde un axe stable.', 'reason': 'legacy wording'},
                ),
                'contract_operation_kind_invalid',
            ),
            (
                'add_missing_reason',
                _contract_for_user_operations(
                    {'kind': 'add', 'proposition': 'Tof garde un axe stable.'},
                ),
                'contract_operation_reason_missing',
            ),
            (
                'no_change_with_payload',
                _contract_for_user_operations(
                    {'kind': 'no_change', 'proposition': 'Tof garde un axe stable.', 'reason': 'bad payload'},
                ),
                'contract_no_change_proposition_not_empty',
            ),
            (
                'tighten_without_target',
                _contract_for_user_operations(
                    {
                        'kind': 'tighten',
                        'proposition': 'Tof garde un axe stable et sobre.',
                        'reason': 'missing target',
                    },
                ),
                'contract_tighten_keys_invalid',
            ),
            (
                'merge_duplicated_targets',
                _contract_for_user_operations(
                    {
                        'kind': 'merge',
                        'targets': ['Tof garde un axe stable.', 'Tof garde un axe stable.'],
                        'proposition': 'Tof garde un axe stable.',
                        'reason': 'duplicate targets',
                    },
                ),
                'contract_merge_targets_duplicated',
            ),
            (
                'no_change_mixed_with_add',
                _contract_for_user_operations(
                    {'kind': 'no_change', 'proposition': '', 'reason': 'contradiction'},
                    {'kind': 'add', 'proposition': 'Tof garde un axe stable.', 'reason': 'contradiction'},
                ),
                'contract_user_no_change_mixed',
            ),
        ]

        for label, payload, expected_reason in cases:
            with self.subTest(label=label):
                contract, reason = memory_identity_periodic_apply.validate_periodic_agent_contract(
                    payload,
                    buffer_pairs_count=15,
                    target_pairs=15,
                )

                self.assertIsNone(contract)
                self.assertEqual(reason, expected_reason)


class IdentityPeriodicApplyPhase2Tests(unittest.TestCase):
    def test_contradiction_helper_ignores_local_negative_refinement(self) -> None:
        self.assertFalse(
            memory_identity_periodic_apply._has_explicit_contradiction_cue(
                'Tof garde une voix sobre.',
                'Tof garde une voix sobre, pas froide.',
            )
        )
        self.assertTrue(
            memory_identity_periodic_apply._has_explicit_contradiction_cue(
                'Tof garde une presence discrete.',
                'Tof ne garde pas une presence discrete.',
            )
        )

    def test_supported_add_writes_canonical_mutable_without_promotion(self) -> None:
        proposition = 'Tof maintient une orientation stable et ritualisee.'
        store = _MutableStore()

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {'kind': 'add', 'proposition': proposition, 'reason': 'strong signal'},
            ),
            buffer_pairs=_supportive_buffer(
                proposition=proposition,
                support_indexes=set(range(15)),
            ),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: 'Tof garde une orientation stable.',
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'applied')
        self.assertTrue(summary['writes_applied'])
        self.assertEqual(store.mutable['user']['content'], proposition)
        user_outcome = next(item for item in summary['outcomes'] if item['subject'] == 'user')
        self.assertEqual(user_outcome['action'], 'add')
        self.assertEqual(user_outcome['reason_code'], 'add_applied')
        self.assertEqual(user_outcome['threshold_verdict'], 'accepted')

    def test_deferred_candidate_does_not_write_canonical_mutable(self) -> None:
        proposition = 'Tof revient souvent a une attention patiente.'
        store = _MutableStore()

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {'kind': 'add', 'proposition': proposition, 'reason': 'mid signal'},
            ),
            buffer_pairs=_supportive_buffer(
                proposition=proposition,
                support_indexes={10, 11, 12, 13, 14},
            ),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: 'Tof garde une orientation stable.',
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'completed_no_change')
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.upsert_calls, [])
        user_outcome = next(item for item in summary['outcomes'] if item['subject'] == 'user')
        self.assertEqual(user_outcome['reason_code'], 'strength_deferred')
        self.assertEqual(user_outcome['threshold_verdict'], 'deferred')
        self.assertEqual(user_outcome['support_pairs'], 5)

    def test_tighten_with_target_only_support_does_not_canonize_new_formulation(self) -> None:
        current = 'Tof garde une clarte durable.'
        proposition = 'Tof garde une clarte durable, sobre et ritualisee.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': current,
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {
                    'kind': 'tighten',
                    'target': current,
                    'proposition': proposition,
                    'reason': 'legacy target support only',
                },
            ),
            buffer_pairs=_supportive_buffer(
                proposition=current,
                support_indexes=set(range(15)),
            ),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: 'Tof garde une orientation stable.',
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'completed_no_change')
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.mutable['user']['content'], current)
        user_outcome = next(item for item in summary['outcomes'] if item['subject'] == 'user')
        self.assertEqual(user_outcome['reason_code'], 'strength_below_threshold')
        self.assertEqual(user_outcome['support_pairs'], 0)
        self.assertEqual(user_outcome['threshold_verdict'], 'rejected')

    def test_merge_with_targets_only_support_does_not_canonize_merged_formulation(self) -> None:
        target_a = 'Tof garde une clarte durable.'
        target_b = 'Tof garde un axe de travail stable.'
        proposition = 'Tof garde une clarte durable et un axe de travail stable.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': '\n'.join([target_a, target_b]),
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )
        buffer_pairs: list[dict[str, Any]] = []
        for index in range(15):
            buffer_pairs.append(
                {
                    'user': {'role': 'user', 'content': f'Utilisateur confirme {target_a} {target_b}'},
                    'assistant': {'role': 'assistant', 'content': f'Assistant reprend {target_a} {target_b}'},
                }
            )

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {
                    'kind': 'merge',
                    'targets': [target_a, target_b],
                    'proposition': proposition,
                    'reason': 'legacy targets support only',
                },
            ),
            buffer_pairs=buffer_pairs,
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: 'Tof garde une orientation stable.',
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'completed_no_change')
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.mutable['user']['content'], '\n'.join([target_a, target_b]))
        user_outcome = next(item for item in summary['outcomes'] if item['subject'] == 'user')
        self.assertEqual(user_outcome['reason_code'], 'strength_below_threshold')
        self.assertEqual(user_outcome['support_pairs'], 0)
        self.assertEqual(user_outcome['threshold_verdict'], 'rejected')

    def test_supported_tighten_uses_local_operation_semantics(self) -> None:
        current = 'Tof garde une clarte durable.'
        proposition = 'Tof garde une clarte durable, sobre et ritualisee.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': current,
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {
                    'kind': 'tighten',
                    'target': current,
                    'proposition': proposition,
                    'reason': 'supported final wording',
                },
            ),
            buffer_pairs=_supportive_buffer(
                proposition=proposition,
                support_indexes=set(range(15)),
            ),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: 'Tof garde une orientation stable.',
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'applied')
        self.assertTrue(summary['writes_applied'])
        self.assertEqual(store.mutable['user']['content'], proposition)
        user_outcome = next(item for item in summary['outcomes'] if item['subject'] == 'user')
        self.assertEqual(user_outcome['action'], 'tighten')
        self.assertEqual(user_outcome['reason_code'], 'tighten_applied')
        self.assertEqual(user_outcome['threshold_verdict'], 'accepted')

    def test_tighten_allows_local_negative_refinement_without_raise_conflict(self) -> None:
        current = 'Tof garde une voix sobre.'
        proposition = 'Tof garde une voix sobre, pas froide.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': current,
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {
                    'kind': 'tighten',
                    'target': current,
                    'proposition': proposition,
                    'reason': 'supported refinement',
                },
            ),
            buffer_pairs=_supportive_buffer(
                proposition=proposition,
                support_indexes=set(range(15)),
            ),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: 'Tof garde une orientation stable.',
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'applied')
        self.assertTrue(summary['writes_applied'])
        self.assertEqual(store.mutable['user']['content'], proposition)
        user_outcome = next(item for item in summary['outcomes'] if item['subject'] == 'user')
        self.assertEqual(user_outcome['action'], 'tighten')
        self.assertEqual(user_outcome['reason_code'], 'tighten_applied')
        self.assertEqual(user_outcome['threshold_verdict'], 'accepted')

    def test_add_skips_candidate_already_covered_by_static(self) -> None:
        proposition = 'Tof maintient une orientation stable et ritualisee.'
        store = _MutableStore()

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {'kind': 'add', 'proposition': proposition, 'reason': 'already in static'},
            ),
            buffer_pairs=_supportive_buffer(
                proposition=proposition,
                support_indexes=set(range(15)),
            ),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: proposition,
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'completed_no_change')
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.upsert_calls, [])
        user_outcome = next(item for item in summary['outcomes'] if item['subject'] == 'user')
        self.assertEqual(user_outcome['action'], 'no_change')
        self.assertEqual(user_outcome['reason_code'], 'covered_by_static')
        self.assertEqual(user_outcome['threshold_verdict'], 'accepted')

    def test_add_skips_candidate_already_present_in_mutable(self) -> None:
        proposition = 'Tof maintient une orientation stable et ritualisee.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': proposition,
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {'kind': 'add', 'proposition': proposition, 'reason': 'already in mutable'},
            ),
            buffer_pairs=_supportive_buffer(
                proposition=proposition,
                support_indexes=set(range(15)),
            ),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: 'Tof garde une orientation stable.',
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'completed_no_change')
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.mutable['user']['content'], proposition)
        user_outcome = next(item for item in summary['outcomes'] if item['subject'] == 'user')
        self.assertEqual(user_outcome['action'], 'no_change')
        self.assertEqual(user_outcome['reason_code'], 'already_present')
        self.assertEqual(user_outcome['threshold_verdict'], 'accepted')

    def test_add_raises_open_tension_when_it_contradicts_static(self) -> None:
        static_line = 'Tof ne garde pas une presence discrete.'
        proposition = 'Tof garde une presence discrete.'
        store = _MutableStore()

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {'kind': 'add', 'proposition': proposition, 'reason': 'strong but contradictory'},
            ),
            buffer_pairs=_supportive_buffer(
                proposition=proposition,
                support_indexes=set(range(15)),
            ),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: static_line,
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'completed_no_change')
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.upsert_calls, [])
        user_outcome = next(item for item in summary['outcomes'] if item['subject'] == 'user')
        self.assertEqual(user_outcome['action'], 'raise_conflict')
        self.assertEqual(user_outcome['reason_code'], 'contradiction_with_static')
        self.assertEqual(user_outcome['threshold_verdict'], 'accepted')

    def test_add_raises_open_tension_when_it_contradicts_existing_mutable(self) -> None:
        current = 'Tof ne garde pas une presence discrete.'
        proposition = 'Tof garde une presence discrete.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': current,
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {'kind': 'add', 'proposition': proposition, 'reason': 'strong but contradictory'},
            ),
            buffer_pairs=_supportive_buffer(
                proposition=proposition,
                support_indexes=set(range(15)),
            ),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: 'Tof garde une orientation stable.',
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'completed_no_change')
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.mutable['user']['content'], current)
        user_outcome = next(item for item in summary['outcomes'] if item['subject'] == 'user')
        self.assertEqual(user_outcome['action'], 'raise_conflict')
        self.assertEqual(user_outcome['reason_code'], 'contradiction_with_mutable')
        self.assertEqual(user_outcome['threshold_verdict'], 'accepted')

    def test_supported_merge_uses_local_operation_semantics(self) -> None:
        target_a = 'Tof garde une clarte durable.'
        target_b = 'Tof garde un axe de travail stable.'
        proposition = 'Tof garde une clarte durable et un axe de travail stable.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': '\n'.join([target_a, target_b]),
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {
                    'kind': 'merge',
                    'targets': [target_a, target_b],
                    'proposition': proposition,
                    'reason': 'supported merged wording',
                },
            ),
            buffer_pairs=_supportive_buffer(
                proposition=proposition,
                support_indexes=set(range(15)),
            ),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: 'Tof garde une orientation stable.',
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'applied')
        self.assertTrue(summary['writes_applied'])
        self.assertEqual(store.mutable['user']['content'], proposition)
        user_outcome = next(item for item in summary['outcomes'] if item['subject'] == 'user')
        self.assertEqual(user_outcome['action'], 'merge')
        self.assertEqual(user_outcome['reason_code'], 'merge_applied')
        self.assertEqual(user_outcome['threshold_verdict'], 'accepted')

    def test_second_candidate_raises_open_tension_when_it_contradicts_first_candidate(self) -> None:
        proposition_a = 'Tof garde une presence discrete.'
        proposition_b = 'Tof ne garde pas une presence discrete.'
        buffer_pairs: list[dict[str, Any]] = []
        for index in range(15):
            buffer_pairs.append(
                {
                    'user': {
                        'role': 'user',
                        'content': f'Utilisateur confirme {proposition_a} puis {proposition_b}',
                    },
                    'assistant': {
                        'role': 'assistant',
                        'content': f'Assistant reprend {proposition_a} puis {proposition_b}',
                    },
                }
            )
        store = _MutableStore()

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {'kind': 'add', 'proposition': proposition_a, 'reason': 'first strong signal'},
                {'kind': 'add', 'proposition': proposition_b, 'reason': 'second contradictory signal'},
            ),
            buffer_pairs=buffer_pairs,
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: 'Tof garde une orientation stable.',
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'applied')
        self.assertTrue(summary['writes_applied'])
        self.assertEqual(store.mutable['user']['content'], proposition_a)
        user_outcomes = [item for item in summary['outcomes'] if item['subject'] == 'user']
        self.assertEqual(user_outcomes[0]['action'], 'add')
        self.assertEqual(user_outcomes[0]['reason_code'], 'add_applied')
        self.assertEqual(user_outcomes[1]['action'], 'raise_conflict')
        self.assertEqual(user_outcomes[1]['reason_code'], 'contradiction_with_candidate')
        self.assertEqual(user_outcomes[1]['threshold_verdict'], 'accepted')

    def test_raise_conflict_stays_conversation_scoped_without_writing_canon(self) -> None:
        proposition = 'Tof semble osciller entre retrait durable et besoin d exposition.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': 'Tof garde une orientation stable.',
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {
                    'kind': 'raise_conflict',
                    'proposition': proposition,
                    'reason': 'tension durable non resolue',
                },
            ),
            buffer_pairs=_supportive_buffer(
                proposition=proposition,
                support_indexes=set(range(15)),
            ),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: 'Tof garde une orientation stable.',
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'completed_no_change')
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.mutable['user']['content'], 'Tof garde une orientation stable.')
        user_outcome = next(item for item in summary['outcomes'] if item['subject'] == 'user')
        self.assertEqual(user_outcome['action'], 'raise_conflict')
        self.assertEqual(user_outcome['reason_code'], 'raise_conflict_open')
        self.assertEqual(user_outcome['threshold_verdict'], 'accepted')

    def test_rejects_utilitarian_proposition_fail_closed(self) -> None:
        proposition = 'Tof garde un repere utile pour mieux repondre au prochain tour.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': 'Tof garde une orientation stable.',
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {
                    'kind': 'add',
                    'proposition': proposition,
                    'reason': 'signal trop utilitaire',
                },
            ),
            buffer_pairs=_supportive_buffer(
                proposition=proposition,
                support_indexes=set(range(15)),
            ),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: 'Tof garde une orientation stable.',
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'all_or_nothing_rejected')
        self.assertEqual(summary['rejection_reasons'], {'user': 'mutable_content_utilitarian_framing'})
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.mutable['user']['content'], 'Tof garde une orientation stable.')

    def test_promotes_strongest_candidate_to_static_when_mutable_is_full(self) -> None:
        strong = 'Tof maintient une orientation stable et ritualisee.'
        medium = 'Tof garde un gout stable pour les architectures lisibles.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': _build_near_target_mutable(slack=70),
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            llm_path = Path(tmpdir) / 'llm_identity.txt'
            user_path = Path(tmpdir) / 'user_identity.txt'
            llm_path.write_text('Frida garde une tenue sobre.', encoding='utf-8')
            user_path.write_text('Tof garde une orientation stable.', encoding='utf-8')
            old_ts = 1_700_000_000
            os.utime(llm_path, (old_ts, old_ts))
            os.utime(user_path, (old_ts, old_ts))

            def read_snapshot(subject: str) -> SimpleNamespace:
                path = llm_path if subject == 'llm' else user_path
                raw_content = path.read_text(encoding='utf-8')
                return SimpleNamespace(
                    content=raw_content.strip(),
                    raw_content=raw_content,
                    resolved_path=path,
                )

            def write_static(subject: str, content: str, **_kwargs: Any) -> None:
                path = llm_path if subject == 'llm' else user_path
                path.write_text(content, encoding='utf-8')

            composite_buffer: list[dict[str, Any]] = []
            medium_support_indexes = {7, 8, 9, 10, 11, 12, 13, 14}
            for index in range(15):
                user_content = f'Utilisateur confirme que {strong}'
                assistant_content = f'Assistant reformule: {strong}'
                if index in medium_support_indexes:
                    user_content += f' {medium}'
                composite_buffer.append(
                    {
                        'user': {'role': 'user', 'content': user_content},
                        'assistant': {'role': 'assistant', 'content': assistant_content},
                    }
                )

            summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
                _contract_for_user_operations(
                    {'kind': 'add', 'proposition': strong, 'reason': 'strong signal'},
                    {'kind': 'add', 'proposition': medium, 'reason': 'secondary signal'},
                ),
                buffer_pairs=composite_buffer,
                memory_store_module=store,
                load_llm_identity_fn=lambda: llm_path.read_text(encoding='utf-8').strip(),
                load_user_identity_fn=lambda: user_path.read_text(encoding='utf-8').strip(),
                read_static_identity_snapshot_fn=read_snapshot,
                write_static_identity_content_fn=write_static,
            )

            self.assertEqual(summary['status'], 'ok')
            self.assertEqual(summary['reason_code'], 'applied')
            self.assertTrue(summary['writes_applied'])
            self.assertEqual(summary['promotion_count'], 1)
            self.assertEqual(summary['promotions'][0]['promotion_reason_code'], 'promoted_to_static')
            self.assertEqual(summary['promotions'][0]['operation_kind'], 'add')
            self.assertAlmostEqual(summary['promotions'][0]['strength'], 1.0, places=4)
            updated_static = user_path.read_text(encoding='utf-8').strip()
            self.assertIn(strong, updated_static)
            self.assertNotIn(strong, store.mutable['user']['content'])
            self.assertIn(medium, store.mutable['user']['content'])
            self.assertLessEqual(len(store.mutable['user']['content']), int(config.IDENTITY_MUTABLE_TARGET_CHARS))
            self.assertEqual(store.upsert_calls[-1][2], 'identity_periodic_agent')
            self.assertEqual(store.upsert_calls[-1][3], 'periodic_agent_promotion')

            projection = active_identity_projection.resolve_active_identity_projection(
                llm_static=llm_path.read_text(encoding='utf-8').strip(),
                user_static=updated_static,
                get_mutable_identity_fn=store.get_mutable_identity,
            )
            self.assertIn(strong, projection.block)
            self.assertNotIn(strong, projection.user_mutable['content'])
            self.assertIn(medium, projection.user_mutable['content'])

    def test_promotion_deduplicates_candidate_already_present_in_static(self) -> None:
        proposition = 'Tof maintient une orientation stable et ritualisee.'
        current_mutable = _build_near_target_mutable(slack=20)
        next_mutable = '\n'.join([current_mutable, proposition])

        promoted_mutable, promoted_static, promotions, rejection_reason, suspended = (
            memory_identity_periodic_apply._plan_subject_promotion(
                subject='user',
                current_mutable_content=current_mutable,
                next_mutable_content=next_mutable,
                static_snapshot={
                    'content': '\n'.join(
                        [
                            'Tof garde une orientation stable.',
                            proposition,
                        ]
                    )
                },
                accepted_operations=[
                    {
                        'kind': 'add',
                        'proposition': proposition,
                        'score': {
                            'support_pairs': 15,
                            'last_occurrence_distance': 0,
                            'frequency_norm': 1.0,
                            'recency_norm': 1.0,
                            'strength': 1.0,
                            'threshold_verdict': 'accepted',
                        },
                    }
                ],
            )
        )

        self.assertIsNone(rejection_reason)
        self.assertFalse(suspended)
        self.assertNotIn(proposition, promoted_mutable)
        self.assertIn(proposition, promoted_static)
        self.assertEqual(promotions[0]['promotion_reason_code'], 'deduplicated_with_static')
        self.assertEqual(promotions[0]['operation_kind'], 'add')

    def test_merge_skips_duplicate_proposition_already_present_in_mutable(self) -> None:
        target_a = 'Tof garde une clarte durable.'
        target_b = 'Tof garde un axe de travail stable.'
        existing = 'Tof garde un ancrage sobre.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': '\n'.join([target_a, target_b, existing]),
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {
                    'kind': 'merge',
                    'targets': [target_a, target_b],
                    'proposition': existing,
                    'reason': 'merged wording already present elsewhere',
                },
            ),
            buffer_pairs=_supportive_buffer(
                proposition=existing,
                support_indexes=set(range(15)),
            ),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: 'Tof garde une orientation stable.',
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'completed_no_change')
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.mutable['user']['content'], '\n'.join([target_a, target_b, existing]))
        user_outcome = next(item for item in summary['outcomes'] if item['subject'] == 'user')
        self.assertEqual(user_outcome['action'], 'no_change')
        self.assertEqual(user_outcome['reason_code'], 'merge_duplicate')
        self.assertEqual(user_outcome['threshold_verdict'], 'accepted')

    def test_double_saturation_suspends_canonization_without_writing(self) -> None:
        proposition = 'Tof maintient une orientation stable et ritualisee.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': _build_near_target_mutable(slack=20),
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            llm_path = Path(tmpdir) / 'llm_identity.txt'
            user_path = Path(tmpdir) / 'user_identity.txt'
            llm_path.write_text('Frida garde une tenue sobre.', encoding='utf-8')
            user_path.write_text(('Trait statique plein. ' * 180).strip(), encoding='utf-8')
            old_ts = 1_700_000_000
            os.utime(llm_path, (old_ts, old_ts))
            os.utime(user_path, (old_ts, old_ts))
            initial_static = user_path.read_text(encoding='utf-8')
            initial_mutable = store.mutable['user']['content']

            def read_snapshot(subject: str) -> SimpleNamespace:
                path = llm_path if subject == 'llm' else user_path
                raw_content = path.read_text(encoding='utf-8')
                return SimpleNamespace(
                    content=raw_content.strip(),
                    raw_content=raw_content,
                    resolved_path=path,
                )

            def write_static(subject: str, content: str, **_kwargs: Any) -> None:
                path = llm_path if subject == 'llm' else user_path
                path.write_text(content, encoding='utf-8')

            summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
                _contract_for_user_operations(
                    {'kind': 'add', 'proposition': proposition, 'reason': 'strong signal'},
                ),
                buffer_pairs=_supportive_buffer(
                    proposition=proposition,
                    support_indexes=set(range(15)),
                ),
                memory_store_module=store,
                load_llm_identity_fn=lambda: llm_path.read_text(encoding='utf-8').strip(),
                load_user_identity_fn=lambda: user_path.read_text(encoding='utf-8').strip(),
                read_static_identity_snapshot_fn=read_snapshot,
                write_static_identity_content_fn=write_static,
            )

            self.assertEqual(summary['status'], 'skipped')
            self.assertEqual(summary['reason_code'], 'double_saturation')
            self.assertFalse(summary['writes_applied'])
            self.assertTrue(summary['auto_canonization_suspended'])
            self.assertEqual(summary['promotion_count'], 0)
            self.assertEqual(user_path.read_text(encoding='utf-8'), initial_static)
            self.assertEqual(store.mutable['user']['content'], initial_mutable)

    def test_recent_admin_mutable_guard_blocks_tighten_on_recent_operator_edit(self) -> None:
        current = 'Tof garde une clarte durable.'
        proposition = 'Tof garde une clarte durable, sobre et ritualisee.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': current,
                    'updated_by': 'admin_identity_mutable_edit',
                    'updated_ts': datetime.now(timezone.utc).isoformat(),
                    'update_reason': 'correction operateur',
                }
            }
        )

        summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
            _contract_for_user_operations(
                {
                    'kind': 'tighten',
                    'target': current,
                    'proposition': proposition,
                    'reason': 'strong signal',
                },
            ),
            buffer_pairs=_supportive_buffer(
                proposition=proposition,
                support_indexes=set(range(15)),
            ),
            memory_store_module=store,
            load_llm_identity_fn=lambda: 'Frida garde une tenue sobre.',
            load_user_identity_fn=lambda: 'Tof garde une orientation stable.',
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'all_or_nothing_rejected')
        self.assertEqual(summary['rejection_reasons'], {'user': 'recent_admin_mutable_guard'})
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.mutable['user']['content'], current)

    def test_recent_auto_static_write_does_not_trigger_operator_guard(self) -> None:
        proposition = 'Tof maintient une orientation stable et ritualisee.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': _build_near_target_mutable(slack=20),
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            llm_path = Path(tmpdir) / 'llm_identity.txt'
            user_path = Path(tmpdir) / 'user_identity.txt'
            llm_path.write_text('Frida garde une tenue sobre.', encoding='utf-8')
            user_path.write_text('Tof garde une orientation stable.', encoding='utf-8')

            def read_snapshot(subject: str) -> SimpleNamespace:
                path = llm_path if subject == 'llm' else user_path
                raw_content = path.read_text(encoding='utf-8')
                return SimpleNamespace(
                    content=raw_content.strip(),
                    raw_content=raw_content,
                    resolved_path=path,
                    updated_by='identity_periodic_agent',
                    update_reason='periodic_agent_promotion',
                    updated_ts=datetime.now(timezone.utc).isoformat(),
                )

            def write_static(subject: str, content: str, **_kwargs: Any) -> None:
                path = llm_path if subject == 'llm' else user_path
                path.write_text(content, encoding='utf-8')

            summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
                _contract_for_user_operations(
                    {'kind': 'add', 'proposition': proposition, 'reason': 'strong signal'},
                ),
                buffer_pairs=_supportive_buffer(
                    proposition=proposition,
                    support_indexes=set(range(15)),
                ),
                memory_store_module=store,
                load_llm_identity_fn=lambda: llm_path.read_text(encoding='utf-8').strip(),
                load_user_identity_fn=lambda: user_path.read_text(encoding='utf-8').strip(),
                read_static_identity_snapshot_fn=read_snapshot,
                write_static_identity_content_fn=write_static,
            )

            self.assertEqual(summary['status'], 'ok')
            self.assertEqual(summary['reason_code'], 'applied')
            self.assertTrue(summary['writes_applied'])
            self.assertEqual(summary['promotion_count'], 1)
            self.assertEqual(summary['promotions'][0]['promotion_reason_code'], 'promoted_to_static')
            self.assertIn(proposition, user_path.read_text(encoding='utf-8').strip())

    def test_recent_static_edit_guard_suspends_promotion(self) -> None:
        proposition = 'Tof maintient une orientation stable et ritualisee.'
        store = _MutableStore(
            {
                'user': {
                    'subject': 'user',
                    'content': _build_near_target_mutable(slack=20),
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                }
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            llm_path = Path(tmpdir) / 'llm_identity.txt'
            user_path = Path(tmpdir) / 'user_identity.txt'
            llm_path.write_text('Frida garde une tenue sobre.', encoding='utf-8')
            user_path.write_text('Tof garde une orientation stable.', encoding='utf-8')

            def read_snapshot(subject: str) -> SimpleNamespace:
                path = llm_path if subject == 'llm' else user_path
                raw_content = path.read_text(encoding='utf-8')
                return SimpleNamespace(
                    content=raw_content.strip(),
                    raw_content=raw_content,
                    resolved_path=path,
                    updated_by='admin_identity_static_edit',
                    update_reason='correction operateur',
                    updated_ts=datetime.now(timezone.utc).isoformat(),
                )

            def write_static(subject: str, content: str, **_kwargs: Any) -> None:
                path = llm_path if subject == 'llm' else user_path
                path.write_text(content, encoding='utf-8')

            summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
                _contract_for_user_operations(
                    {'kind': 'add', 'proposition': proposition, 'reason': 'strong signal'},
                ),
                buffer_pairs=_supportive_buffer(
                    proposition=proposition,
                    support_indexes=set(range(15)),
                ),
                memory_store_module=store,
                load_llm_identity_fn=lambda: llm_path.read_text(encoding='utf-8').strip(),
                load_user_identity_fn=lambda: user_path.read_text(encoding='utf-8').strip(),
                read_static_identity_snapshot_fn=read_snapshot,
                write_static_identity_content_fn=write_static,
            )

            self.assertEqual(summary['status'], 'skipped')
            self.assertEqual(summary['reason_code'], 'static_recent_operator_edit_guard')
            self.assertTrue(summary['auto_canonization_suspended'])
            self.assertFalse(summary['writes_applied'])
            self.assertEqual(user_path.read_text(encoding='utf-8').strip(), 'Tof garde une orientation stable.')


if __name__ == '__main__':
    unittest.main()
