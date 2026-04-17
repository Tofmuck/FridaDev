from __future__ import annotations

import copy
import sys
import unittest
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

from memory import memory_identity_periodic_agent


def _pair(index: int) -> list[dict[str, Any]]:
    return [
        {'role': 'user', 'content': f'utilisateur {index}'},
        {'role': 'assistant', 'content': f'assistant {index}'},
    ]


class _InMemoryIdentityStore:
    def __init__(self) -> None:
        self.mutable: dict[str, dict[str, Any]] = {}
        self.staging: dict[str, dict[str, Any]] = {}
        self.upsert_calls: list[tuple[str, str, str, str]] = []

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
    ) -> dict[str, Any] | None:
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

    def get_identity_staging_state(self, conversation_id: str) -> dict[str, Any] | None:
        state = self.staging.get(conversation_id)
        return copy.deepcopy(state) if state is not None else None

    def append_identity_staging_pair(
        self,
        conversation_id: str,
        pair: list[dict[str, Any]],
        *,
        target_pairs: int = 15,
    ) -> dict[str, Any] | None:
        state = copy.deepcopy(
            self.staging.get(
                conversation_id,
                {
                    'conversation_id': conversation_id,
                    'buffer_pairs': [],
                    'buffer_pairs_count': 0,
                    'buffer_target_pairs': int(target_pairs),
                    'auto_canonization_suspended': False,
                    'last_agent_status': 'buffering',
                    'last_agent_reason': None,
                    'last_agent_run_ts': None,
                },
            )
        )
        current_pairs = list(state['buffer_pairs'])
        buffer_frozen = len(current_pairs) >= int(target_pairs)
        if buffer_frozen:
            state['buffer_pairs'] = current_pairs[: int(target_pairs)]
        else:
            state['buffer_pairs'] = current_pairs + [copy.deepcopy({'user': pair[0], 'assistant': pair[1]})]
        state['buffer_pairs_count'] = len(state['buffer_pairs'])
        state['buffer_target_pairs'] = int(target_pairs)
        state['buffer_frozen'] = bool(buffer_frozen)
        self.staging[conversation_id] = copy.deepcopy(state)
        return copy.deepcopy(state)

    def mark_identity_staging_status(
        self,
        conversation_id: str,
        *,
        status: str,
        reason: str = '',
        touch_run_ts: bool = False,
    ) -> dict[str, Any] | None:
        state = self.get_identity_staging_state(conversation_id)
        if state is None:
            return None
        state['last_agent_status'] = status
        state['last_agent_reason'] = reason or None
        if touch_run_ts:
            state['last_agent_run_ts'] = '2026-04-17T00:00:00Z'
        self.staging[conversation_id] = copy.deepcopy(state)
        return copy.deepcopy(state)

    def clear_identity_staging_buffer(
        self,
        conversation_id: str,
        *,
        status: str,
        reason: str = '',
    ) -> dict[str, Any] | None:
        state = self.get_identity_staging_state(conversation_id)
        if state is None:
            return None
        state['buffer_pairs'] = []
        state['buffer_pairs_count'] = 0
        state['last_agent_status'] = status
        state['last_agent_reason'] = reason or None
        state['last_agent_run_ts'] = '2026-04-17T00:00:00Z'
        self.staging[conversation_id] = copy.deepcopy(state)
        return copy.deepcopy(state)


class IdentityPeriodicAgentPhase1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_load_llm = memory_identity_periodic_agent.identity.load_llm_identity
        self.original_load_user = memory_identity_periodic_agent.identity.load_user_identity
        memory_identity_periodic_agent.identity.load_llm_identity = lambda: 'Frida garde une tenue sobre.'
        memory_identity_periodic_agent.identity.load_user_identity = lambda: 'Tof garde une orientation stable.'

    def tearDown(self) -> None:
        memory_identity_periodic_agent.identity.load_llm_identity = self.original_load_llm
        memory_identity_periodic_agent.identity.load_user_identity = self.original_load_user

    def test_does_not_call_agent_before_fifteen_pairs(self) -> None:
        store = _InMemoryIdentityStore()
        calls: list[dict[str, Any]] = []
        arbiter_module = SimpleNamespace(
            run_identity_periodic_agent=lambda payload: calls.append(copy.deepcopy(payload)) or {}
        )

        for index in range(1, 15):
            summary = memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-before-threshold',
                _pair(index),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        self.assertEqual(summary['status'], 'buffering')
        self.assertEqual(summary['reason_code'], 'below_threshold')
        self.assertEqual(summary['buffer_pairs_count'], 14)
        self.assertEqual(calls, [])
        self.assertEqual(store.get_identity_staging_state('conv-before-threshold')['buffer_pairs_count'], 14)

    def test_calls_agent_at_exact_threshold_and_clears_buffer_only_after_clean_completion(self) -> None:
        store = _InMemoryIdentityStore()
        observed_payloads: list[dict[str, Any]] = []

        def fake_run_identity_periodic_agent(payload: dict[str, Any]) -> dict[str, Any]:
            observed_payloads.append(copy.deepcopy(payload))
            return {
                'llm': {
                    'operations': [
                        {'kind': 'no_change', 'proposition': '', 'reason': 'stable canon'},
                    ]
                },
                'user': {
                    'operations': [
                        {
                            'kind': 'add',
                            'proposition': 'Tof maintient une attention durable aux details stables.',
                            'reason': 'durable identity signal',
                        }
                    ]
                },
                'meta': {
                    'execution_status': 'complete',
                    'buffer_pairs_count': 15,
                    'window_complete': True,
                },
            }

        arbiter_module = SimpleNamespace(run_identity_periodic_agent=fake_run_identity_periodic_agent)
        for index in range(1, 15):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-threshold',
                _pair(index),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-threshold',
            _pair(15),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(len(observed_payloads), 1)
        self.assertEqual(observed_payloads[0]['buffer_pairs_count'], 15)
        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'applied')
        self.assertTrue(summary['buffer_cleared'])
        self.assertTrue(summary['writes_applied'])
        self.assertEqual(store.get_identity_staging_state('conv-threshold')['buffer_pairs_count'], 0)
        self.assertIn('attention durable', store.mutable['user']['content'])
        self.assertEqual(store.upsert_calls[0][2], 'identity_periodic_agent')

    def test_does_not_partially_commit_when_one_subject_is_terminally_rejected(self) -> None:
        store = _InMemoryIdentityStore()

        def fake_run_identity_periodic_agent(_payload: dict[str, Any]) -> dict[str, Any]:
            return {
                'llm': {
                    'operations': [
                        {
                            'kind': 'add',
                            'proposition': 'x' * 1651,
                            'reason': 'overflow',
                        }
                    ]
                },
                'user': {
                    'operations': [
                        {
                            'kind': 'add',
                            'proposition': 'Tof maintient un fil identitaire stable.',
                            'reason': 'durable identity signal',
                        }
                    ]
                },
                'meta': {
                    'execution_status': 'complete',
                    'buffer_pairs_count': 15,
                    'window_complete': True,
                },
            }

        arbiter_module = SimpleNamespace(run_identity_periodic_agent=fake_run_identity_periodic_agent)
        for index in range(1, 15):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-all-or-nothing',
                _pair(index),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-all-or-nothing',
            _pair(15),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'all_or_nothing_rejected')
        self.assertEqual(summary['last_agent_status'], 'apply_failed')
        self.assertFalse(summary['buffer_cleared'])
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(summary['rejection_reasons'], {'llm': 'mutable_content_too_long'})
        self.assertEqual(store.upsert_calls, [])
        self.assertEqual(store.mutable, {})
        self.assertEqual(store.get_identity_staging_state('conv-all-or-nothing')['buffer_pairs_count'], 15)
        self.assertIn(
            {
                'subject': 'user',
                'action': 'no_change',
                'reason_code': 'not_committed_due_to_peer_rejection',
                'old_len': 0,
                'new_len': 0,
            },
            summary['outcomes'],
        )

    def test_preserves_buffer_when_agent_returns_invalid_contract(self) -> None:
        store = _InMemoryIdentityStore()
        arbiter_module = SimpleNamespace(
            run_identity_periodic_agent=lambda _payload: {
                'llm': {'operations': []},
                'user': {'operations': []},
            }
        )

        for index in range(1, 15):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-invalid-contract',
                _pair(index),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-invalid-contract',
            _pair(15),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['last_agent_status'], 'contract_invalid')
        self.assertFalse(summary['buffer_cleared'])
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.get_identity_staging_state('conv-invalid-contract')['buffer_pairs_count'], 15)
        self.assertEqual(store.upsert_calls, [])

    def test_retry_reuses_exact_same_fifteen_pair_window_after_failed_attempt(self) -> None:
        store = _InMemoryIdentityStore()
        observed_payloads: list[dict[str, Any]] = []
        responses = [
            {
                'llm': {'operations': []},
                'user': {'operations': []},
            },
            {
                'llm': {
                    'operations': [
                        {'kind': 'no_change', 'proposition': '', 'reason': 'stable canon'},
                    ]
                },
                'user': {
                    'operations': [
                        {
                            'kind': 'add',
                            'proposition': 'Tof maintient une attention stable.',
                            'reason': 'durable identity signal',
                        }
                    ]
                },
                'meta': {
                    'execution_status': 'complete',
                    'buffer_pairs_count': 15,
                    'window_complete': True,
                },
            },
        ]

        def fake_run_identity_periodic_agent(payload: dict[str, Any]) -> dict[str, Any]:
            observed_payloads.append(copy.deepcopy(payload))
            return copy.deepcopy(responses.pop(0))

        arbiter_module = SimpleNamespace(run_identity_periodic_agent=fake_run_identity_periodic_agent)
        for index in range(1, 15):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-retry-frozen',
                _pair(index),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        first_summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-retry-frozen',
            _pair(15),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )
        second_summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-retry-frozen',
            _pair(16),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(first_summary['status'], 'skipped')
        self.assertEqual(first_summary['last_agent_status'], 'contract_invalid')
        self.assertFalse(first_summary['buffer_cleared'])
        self.assertEqual(len(observed_payloads), 2)
        self.assertEqual(observed_payloads[0]['buffer_pairs_count'], 15)
        self.assertEqual(observed_payloads[1]['buffer_pairs_count'], 15)
        self.assertEqual(observed_payloads[0]['buffer_pairs'], observed_payloads[1]['buffer_pairs'])
        self.assertEqual(
            observed_payloads[1]['buffer_pairs'][-1]['user']['content'],
            'utilisateur 15',
        )
        self.assertTrue(second_summary['buffer_frozen'])
        self.assertTrue(second_summary['buffer_cleared'])
        self.assertEqual(store.get_identity_staging_state('conv-retry-frozen')['buffer_pairs_count'], 0)
        self.assertIn('attention stable', store.mutable['user']['content'])

    def test_preserves_buffer_when_agent_raises_timeout(self) -> None:
        store = _InMemoryIdentityStore()

        def boom(_payload: dict[str, Any]) -> dict[str, Any]:
            raise TimeoutError('timeout')

        arbiter_module = SimpleNamespace(run_identity_periodic_agent=boom)
        for index in range(1, 15):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-timeout',
                _pair(index),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-timeout',
            _pair(15),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'agent_call_error')
        self.assertEqual(summary['last_agent_status'], 'agent_call_error')
        self.assertFalse(summary['buffer_cleared'])
        self.assertEqual(store.get_identity_staging_state('conv-timeout')['buffer_pairs_count'], 15)
        self.assertEqual(store.upsert_calls, [])


if __name__ == '__main__':
    unittest.main()
