from __future__ import annotations

import copy
import os
import sys
import tempfile
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


def _support_pair(index: int, proposition: str) -> list[dict[str, Any]]:
    return [
        {'role': 'user', 'content': f'utilisateur {index} {proposition}'},
        {'role': 'assistant', 'content': f'assistant {index} confirme {proposition}'},
    ]


def _build_large_identity_block(subject: str, *, min_length: int) -> str:
    lines: list[str] = []
    content = ''
    index = 1
    while len(content) < int(min_length):
        lines.append(f'{subject} garde un axe stable {index}.')
        content = '\n'.join(lines)
        index += 1
    return content


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
        buffer_already_frozen = len(current_pairs) >= int(target_pairs)
        if not current_pairs and state.get('last_agent_status') in {
            'applied',
            'completed_no_change',
            'completed_with_open_tension',
            'not_run',
        }:
            state['last_agent_status'] = 'buffering'
        if buffer_already_frozen:
            state['buffer_pairs'] = current_pairs[: int(target_pairs)]
        else:
            state['buffer_pairs'] = current_pairs + [copy.deepcopy({'user': pair[0], 'assistant': pair[1]})]
        state['buffer_pairs_count'] = len(state['buffer_pairs'])
        state['buffer_target_pairs'] = int(target_pairs)
        state['buffer_frozen'] = state['buffer_pairs_count'] >= int(target_pairs)
        self.staging[conversation_id] = copy.deepcopy(state)
        return copy.deepcopy(state)

    def mark_identity_staging_status(
        self,
        conversation_id: str,
        *,
        status: str,
        reason: str = '',
        touch_run_ts: bool = False,
        auto_canonization_suspended: bool | None = None,
    ) -> dict[str, Any] | None:
        state = self.get_identity_staging_state(conversation_id)
        if state is None:
            return None
        state['last_agent_status'] = status
        state['last_agent_reason'] = reason or None
        if auto_canonization_suspended is not None:
            state['auto_canonization_suspended'] = bool(auto_canonization_suspended)
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
        auto_canonization_suspended: bool = False,
    ) -> dict[str, Any] | None:
        state = self.get_identity_staging_state(conversation_id)
        if state is None:
            return None
        state['buffer_pairs'] = []
        state['buffer_pairs_count'] = 0
        state['last_agent_status'] = status
        state['last_agent_reason'] = reason or None
        state['last_agent_run_ts'] = '2026-04-17T00:00:00Z'
        state['auto_canonization_suspended'] = bool(auto_canonization_suspended)
        self.staging[conversation_id] = copy.deepcopy(state)
        return copy.deepcopy(state)


class IdentityPeriodicAgentPhase1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_load_llm = memory_identity_periodic_agent.identity.load_llm_identity
        self.original_load_user = memory_identity_periodic_agent.identity.load_user_identity
        self.original_read_static_snapshot = memory_identity_periodic_agent.static_identity_content.read_static_identity_snapshot
        self.original_write_static_content = memory_identity_periodic_agent.static_identity_content.write_static_identity_content
        memory_identity_periodic_agent.identity.load_llm_identity = lambda: 'Frida garde une tenue sobre.'
        memory_identity_periodic_agent.identity.load_user_identity = lambda: 'Tof garde une orientation stable.'
        memory_identity_periodic_agent.static_identity_content.read_static_identity_snapshot = lambda subject: SimpleNamespace(
            content='Frida garde une tenue sobre.' if subject == 'llm' else 'Tof garde une orientation stable.',
            raw_content='Frida garde une tenue sobre.' if subject == 'llm' else 'Tof garde une orientation stable.',
            resolved_path=None,
        )
        memory_identity_periodic_agent.static_identity_content.write_static_identity_content = lambda _subject, _content: None

    def tearDown(self) -> None:
        memory_identity_periodic_agent.identity.load_llm_identity = self.original_load_llm
        memory_identity_periodic_agent.identity.load_user_identity = self.original_load_user
        memory_identity_periodic_agent.static_identity_content.read_static_identity_snapshot = self.original_read_static_snapshot
        memory_identity_periodic_agent.static_identity_content.write_static_identity_content = self.original_write_static_content

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
            self.assertEqual(summary['buffer_pairs_count'], index)
            self.assertEqual(summary['buffer_target_pairs'], 15)
            self.assertFalse(summary['buffer_cleared'])
            self.assertFalse(summary['writes_applied'])
            self.assertEqual(
                store.get_identity_staging_state('conv-before-threshold')['buffer_pairs_count'],
                index,
            )

        self.assertEqual(summary['status'], 'buffering')
        self.assertEqual(summary['reason_code'], 'below_threshold')
        self.assertEqual(summary['buffer_pairs_count'], 14)
        self.assertEqual(calls, [])
        self.assertEqual(store.get_identity_staging_state('conv-before-threshold')['buffer_pairs_count'], 14)

    def test_calls_agent_at_exact_threshold_and_clears_buffer_only_after_clean_completion(self) -> None:
        store = _InMemoryIdentityStore()
        observed_payloads: list[dict[str, Any]] = []
        proposition = 'Tof maintient une attention durable aux details stables.'

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
                            'proposition': proposition,
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
                _support_pair(index, proposition),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-threshold',
            _support_pair(15, proposition),
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

    def test_marks_open_tension_without_flattening_it_to_completed_no_change(self) -> None:
        store = _InMemoryIdentityStore()
        proposition = 'Tof semble osciller entre retrait durable et besoin d exposition.'

        arbiter_module = SimpleNamespace(
            run_identity_periodic_agent=lambda _payload: {
                'llm': {
                    'operations': [
                        {'kind': 'no_change', 'proposition': '', 'reason': 'stable canon'},
                    ]
                },
                'user': {
                    'operations': [
                        {
                            'kind': 'raise_conflict',
                            'proposition': proposition,
                            'reason': 'tension durable non resolue',
                        }
                    ]
                },
                'meta': {
                    'execution_status': 'complete',
                    'buffer_pairs_count': 15,
                    'window_complete': True,
                },
            }
        )

        for index in range(1, 15):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-open-tension',
                _support_pair(index, proposition),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-open-tension',
            _support_pair(15, proposition),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'completed_with_open_tension')
        self.assertEqual(summary['last_agent_status'], 'completed_with_open_tension')
        self.assertTrue(summary['buffer_cleared'])
        self.assertFalse(summary['writes_applied'])
        user_outcome = next(item for item in summary['outcomes'] if item['subject'] == 'user')
        self.assertEqual(user_outcome['action'], 'raise_conflict')
        staging_state = store.get_identity_staging_state('conv-open-tension')
        self.assertEqual(staging_state['buffer_pairs_count'], 0)
        self.assertEqual(staging_state['last_agent_status'], 'completed_with_open_tension')
        self.assertEqual(staging_state['last_agent_reason'], 'completed_with_open_tension')

        next_summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-open-tension',
            _support_pair(16, proposition),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(next_summary['status'], 'buffering')
        self.assertEqual(next_summary['last_agent_status'], 'buffering')

    def test_does_not_partially_commit_when_one_subject_is_terminally_rejected(self) -> None:
        store = _InMemoryIdentityStore()
        existing_llm_content = _build_large_identity_block('Frida', min_length=3290)
        store.mutable['llm'] = {
            'subject': 'llm',
            'content': existing_llm_content,
            'updated_by': 'identity_periodic_agent',
            'update_reason': 'periodic_agent',
        }
        llm_proposition = 'Frida garde un axe de synthese stable.'
        user_proposition = 'Tof maintient un fil identitaire stable.'

        def fake_run_identity_periodic_agent(_payload: dict[str, Any]) -> dict[str, Any]:
            return {
                'llm': {
                    'operations': [
                        {
                            'kind': 'add',
                            'proposition': llm_proposition,
                            'reason': 'overflow',
                        }
                    ]
                },
                'user': {
                    'operations': [
                        {
                            'kind': 'add',
                            'proposition': user_proposition,
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
                _support_pair(index, f'{llm_proposition} {user_proposition}'),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-all-or-nothing',
            _support_pair(15, f'{llm_proposition} {user_proposition}'),
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
        self.assertEqual(store.mutable['llm']['content'], existing_llm_content)
        self.assertNotIn('user', store.mutable)
        self.assertEqual(store.get_identity_staging_state('conv-all-or-nothing')['buffer_pairs_count'], 15)
        user_outcome = next(item for item in summary['outcomes'] if item['subject'] == 'user')
        self.assertEqual(user_outcome['action'], 'no_change')
        self.assertEqual(user_outcome['reason_code'], 'not_committed_due_to_peer_rejection')
        self.assertEqual(user_outcome['old_len'], 0)
        self.assertEqual(user_outcome['new_len'], 0)

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
        self.assertTrue(summary['buffer_frozen'])
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.get_identity_staging_state('conv-invalid-contract')['buffer_pairs_count'], 15)
        self.assertEqual(store.upsert_calls, [])

    def test_preserves_buffer_when_agent_returns_contradictory_no_change_mix(self) -> None:
        store = _InMemoryIdentityStore()
        proposition = 'Tof maintient une tension encore mal tranchee.'
        arbiter_module = SimpleNamespace(
            run_identity_periodic_agent=lambda _payload: {
                'llm': {
                    'operations': [
                        {'kind': 'no_change', 'proposition': '', 'reason': 'stable canon'},
                    ]
                },
                'user': {
                    'operations': [
                        {'kind': 'no_change', 'proposition': '', 'reason': 'contradiction'},
                        {'kind': 'add', 'proposition': proposition, 'reason': 'contradiction'},
                    ]
                },
                'meta': {
                    'execution_status': 'complete',
                    'buffer_pairs_count': 15,
                    'window_complete': True,
                },
            }
        )

        for index in range(1, 15):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-no-change-mixed',
                _support_pair(index, proposition),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-no-change-mixed',
            _support_pair(15, proposition),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'contract_user_no_change_mixed')
        self.assertEqual(summary['last_agent_status'], 'contract_invalid')
        self.assertFalse(summary['buffer_cleared'])
        self.assertTrue(summary['buffer_frozen'])
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.get_identity_staging_state('conv-no-change-mixed')['buffer_pairs_count'], 15)
        self.assertEqual(store.upsert_calls, [])

    def test_retry_reuses_exact_same_fifteen_pair_window_after_failed_attempt(self) -> None:
        store = _InMemoryIdentityStore()
        observed_payloads: list[dict[str, Any]] = []
        proposition = 'Tof maintient une attention stable.'
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
                            'proposition': proposition,
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
                _support_pair(index, proposition),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        first_summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-retry-frozen',
            _support_pair(15, proposition),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )
        second_summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-retry-frozen',
            _support_pair(16, proposition),
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
            f'utilisateur 15 {proposition}',
        )
        self.assertTrue(second_summary['buffer_frozen'])
        self.assertTrue(second_summary['buffer_cleared'])
        self.assertEqual(store.get_identity_staging_state('conv-retry-frozen')['buffer_pairs_count'], 0)
        self.assertIn('attention stable', store.mutable['user']['content'])

    def test_marks_auto_canonization_suspension_and_preserves_buffer_when_double_saturation_blocks_promotion(self) -> None:
        store = _InMemoryIdentityStore()
        proposition = 'Tof maintient une orientation stable et ritualisee.'
        filler = _build_large_identity_block('Tof', min_length=2980)
        store.mutable['user'] = {
            'subject': 'user',
            'content': filler,
            'updated_by': 'identity_periodic_agent',
            'update_reason': 'periodic_agent',
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            user_path = Path(tmpdir) / 'user_identity.txt'
            user_path.write_text('Statique plein. ' * 220, encoding='utf-8')
            old_ts = 1_700_000_000
            os.utime(user_path, (old_ts, old_ts))

            def fake_read_snapshot(subject: str) -> SimpleNamespace:
                if subject == 'user':
                    content = user_path.read_text(encoding='utf-8')
                    return SimpleNamespace(
                        content=content.strip(),
                        raw_content=content,
                        resolved_path=user_path,
                    )
                return SimpleNamespace(
                    content='Frida garde une tenue sobre.',
                    raw_content='Frida garde une tenue sobre.',
                    resolved_path=None,
                )

            def fake_write_static(_subject: str, _content: str) -> None:
                raise AssertionError('double saturation must not write static content')

            memory_identity_periodic_agent.static_identity_content.read_static_identity_snapshot = fake_read_snapshot
            memory_identity_periodic_agent.static_identity_content.write_static_identity_content = fake_write_static

            arbiter_module = SimpleNamespace(
                run_identity_periodic_agent=lambda _payload: {
                    'llm': {
                        'operations': [
                            {'kind': 'no_change', 'proposition': '', 'reason': 'stable canon'},
                        ]
                    },
                    'user': {
                        'operations': [
                            {'kind': 'add', 'proposition': proposition, 'reason': 'durable identity signal'},
                        ]
                    },
                    'meta': {
                        'execution_status': 'complete',
                        'buffer_pairs_count': 15,
                        'window_complete': True,
                    },
                }
            )

            for index in range(1, 15):
                memory_identity_periodic_agent.stage_identity_turn_pair(
                    'conv-double-saturation',
                    _support_pair(index, proposition),
                    arbiter_module=arbiter_module,
                    memory_store_module=store,
                )

            summary = memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-double-saturation',
                _support_pair(15, proposition),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'double_saturation')
        self.assertEqual(summary['last_agent_status'], 'auto_canonization_suspended')
        self.assertFalse(summary['buffer_cleared'])
        self.assertTrue(summary['buffer_frozen'])
        self.assertTrue(summary['auto_canonization_suspended'])
        self.assertFalse(summary['writes_applied'])
        staging_state = store.get_identity_staging_state('conv-double-saturation')
        self.assertEqual(staging_state['buffer_pairs_count'], 15)
        self.assertTrue(staging_state['auto_canonization_suspended'])

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

    def test_preserves_buffer_when_agent_raises_runtime_error(self) -> None:
        store = _InMemoryIdentityStore()

        def boom(_payload: dict[str, Any]) -> dict[str, Any]:
            raise RuntimeError('provider blew up')

        arbiter_module = SimpleNamespace(run_identity_periodic_agent=boom)
        for index in range(1, 15):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-runtime-error',
                _pair(index),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-runtime-error',
            _pair(15),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'agent_call_error')
        self.assertEqual(summary['last_agent_status'], 'agent_call_error')
        self.assertFalse(summary['buffer_cleared'])
        self.assertTrue(summary['buffer_frozen'])
        self.assertEqual(store.get_identity_staging_state('conv-runtime-error')['buffer_pairs_count'], 15)
        self.assertEqual(store.upsert_calls, [])


if __name__ == '__main__':
    unittest.main()
