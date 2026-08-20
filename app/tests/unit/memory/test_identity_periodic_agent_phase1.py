from __future__ import annotations

import copy
import sys
import unittest
from contextlib import nullcontext
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

from observability import chat_turn_logger
from observability import log_store
from memory import memory_identity_periodic_agent
from identity import static_identity_content


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


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys: set[str] = set()
        for key, item in value.items():
            keys.add(str(key))
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list):
        keys = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _no_change(subject: str) -> dict[str, Any]:
    return {
        'subject': subject,
        'verdict': 'no_change',
        'proposition': '',
        'reason_code': 'no_mutable_identity_signal',
        'continuity_kind': 'none',
        'source_refs': [],
        'guard_notes': [],
    }


def _persist_add(subject: str, proposition: str, *, reason_code: str | None = None) -> dict[str, Any]:
    return {
        'subject': subject,
        'verdict': 'add',
        'proposition': proposition,
        'reason_code': reason_code
        or ('explicit_frida_self_definition_continuity' if subject == 'llm' else 'explicit_self_limit_continuity'),
        'continuity_kind': 'posture' if subject == 'llm' else 'limit',
        'source_refs': ['pair_05'],
        'guard_notes': ['not_task_local'],
    }


def _raise_tension(subject: str, proposition: str) -> dict[str, Any]:
    return {
        'subject': subject,
        'verdict': 'raise_tension',
        'proposition': '',
        'reason_code': 'relation_tension_open',
        'continuity_kind': 'tension',
        'source_refs': ['pair_05'],
        'guard_notes': ['not_persisted'],
    }


def _non_persist(subject: str, verdict: str, reason_code: str, *, continuity_kind: str = 'none') -> dict[str, Any]:
    return {
        'subject': subject,
        'verdict': verdict,
        'proposition': '',
        'reason_code': reason_code,
        'continuity_kind': continuity_kind,
        'source_refs': ['pair_05'] if verdict in {'reject', 'defer'} else [],
        'guard_notes': ['not_persisted'] if verdict in {'reject', 'defer'} else [],
    }


def _contract(*verdicts: dict[str, Any]) -> dict[str, Any]:
    items = list(verdicts)
    subjects = {str(item.get('subject') or '') for item in items}
    if 'llm' not in subjects:
        items.append(_no_change('llm'))
    if 'user' not in subjects:
        items.append(_no_change('user'))
    return {
        'schema_version': 'mutable_judge_v2',
        'meta': {
            'execution_status': 'complete',
            'window_pairs_count': memory_identity_periodic_agent.BUFFER_TARGET_PAIRS,
            'window_complete': True,
        },
        'verdicts': items,
    }


def _judge_ok(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        'status': 'ok',
        'reason_code': 'judge_complete',
        'contract': copy.deepcopy(contract),
        'observability': {
            'status': 'ok',
            'reason_code': 'judge_complete',
            'schema_version': 'mutable_judge_v2',
            'prompt_kind': 'mutable_identity_judge_v2',
            'window_pairs_count': memory_identity_periodic_agent.BUFFER_TARGET_PAIRS,
            'window_complete': True,
            'verdict_count': len(contract['verdicts']),
            'verdict_counts': {
                verdict: sum(1 for item in contract['verdicts'] if item['verdict'] == verdict)
                for verdict in {item['verdict'] for item in contract['verdicts']}
            },
            'subjects_seen': sorted({item['subject'] for item in contract['verdicts']}),
            'subjects_touched': sorted(
                {
                    item['subject']
                    for item in contract['verdicts']
                    if item['verdict'] == 'add'
                }
            ),
            'continuity_kinds': sorted({item['continuity_kind'] for item in contract['verdicts']}),
            'reason_codes': sorted({item['reason_code'] for item in contract['verdicts']}),
            'source_refs_count': sum(len(item['source_refs']) for item in contract['verdicts']),
            'guard_notes_count': sum(len(item['guard_notes']) for item in contract['verdicts']),
        },
    }


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

    def apply_mutable_identity_subject_updates(
        self,
        updates: list[dict[str, Any]],
        **_staging_fence: Any,
    ) -> list[dict[str, Any]] | None:
        next_mutable = copy.deepcopy(self.mutable)
        upsert_calls: list[tuple[str, str, str, str]] = []
        results: list[dict[str, Any]] = []
        for update in updates:
            subject = str(update.get('subject') or '')
            mutation_kind = str(update.get('mutation_kind') or '')
            if mutation_kind == 'set':
                content = str(update.get('content') or '')
                payload = {
                    'subject': subject,
                    'content': content,
                    'source_trace_id': update.get('source_trace_id'),
                    'updated_by': str(update.get('updated_by') or 'system'),
                    'update_reason': str(update.get('update_reason') or ''),
                }
                next_mutable[subject] = payload
                upsert_calls.append((subject, content, payload['updated_by'], payload['update_reason']))
                results.append(copy.deepcopy(payload))
                continue
            if mutation_kind == 'clear':
                old = next_mutable.pop(subject, None)
                if old is None:
                    return None
                results.append(copy.deepcopy(old))
                continue
            return None
        self.mutable = next_mutable
        self.upsert_calls.extend(upsert_calls)
        return results

    def get_identity_staging_state(self, conversation_id: str) -> dict[str, Any] | None:
        state = self.staging.get(conversation_id)
        return copy.deepcopy(state) if state is not None else None

    def append_identity_staging_pair(
        self,
        conversation_id: str,
        pair: list[dict[str, Any]],
        *,
        target_pairs: int = memory_identity_periodic_agent.BUFFER_TARGET_PAIRS,
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
            state['last_agent_reason'] = None
        if buffer_already_frozen:
            state['buffer_pairs'] = current_pairs[: int(target_pairs)]
        else:
            state['buffer_pairs'] = current_pairs + [copy.deepcopy({'user': pair[0], 'assistant': pair[1]})]
        state['buffer_pairs_count'] = len(state['buffer_pairs'])
        state['buffer_target_pairs'] = int(target_pairs)
        state['buffer_frozen'] = state['buffer_pairs_count'] >= int(target_pairs)
        state['pair_appended'] = not buffer_already_frozen
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
        **_expected: Any,
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
        state['transition_applied'] = True
        self.staging[conversation_id] = copy.deepcopy(state)
        return copy.deepcopy(state)

    def identity_staging_processing_lock(
        self,
        _conversation_id: str,
        _window_fingerprint: str,
    ) -> Any:
        return nullcontext(True)

    def clear_identity_staging_buffer(
        self,
        conversation_id: str,
        *,
        status: str,
        reason: str = '',
        auto_canonization_suspended: bool = False,
        next_pair: Any = None,
        **_expected: Any,
    ) -> dict[str, Any] | None:
        state = self.get_identity_staging_state(conversation_id)
        if state is None:
            return None
        state['buffer_pairs'] = (
            [copy.deepcopy({'user': next_pair[0], 'assistant': next_pair[1]})]
            if next_pair is not None
            else []
        )
        state['buffer_pairs_count'] = len(state['buffer_pairs'])
        state['last_agent_status'] = 'buffering' if next_pair is not None else status
        state['last_agent_reason'] = None if next_pair is not None else (reason or None)
        state['last_agent_run_ts'] = '2026-04-17T00:00:00Z'
        state['auto_canonization_suspended'] = bool(auto_canonization_suspended)
        state['transition_applied'] = True
        self.staging[conversation_id] = copy.deepcopy(state)
        return copy.deepcopy(state)


class IdentityPeriodicAgentPhase1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_load_llm = memory_identity_periodic_agent.mutable_identity_runtime.identity.load_llm_identity
        self.original_load_user = memory_identity_periodic_agent.mutable_identity_runtime.identity.load_user_identity
        memory_identity_periodic_agent.mutable_identity_runtime.identity.load_llm_identity = (
            lambda: 'Frida garde une tenue sobre.'
        )
        memory_identity_periodic_agent.mutable_identity_runtime.identity.load_user_identity = (
            lambda: 'Tof garde une orientation stable.'
        )

    def tearDown(self) -> None:
        memory_identity_periodic_agent.mutable_identity_runtime.identity.load_llm_identity = self.original_load_llm
        memory_identity_periodic_agent.mutable_identity_runtime.identity.load_user_identity = self.original_load_user

    def test_staging_keeps_presence_user_and_buffers_empty_assistant_projection(self) -> None:
        store = _InMemoryIdentityStore()

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-presence-staging',
            [
                {'role': 'user', 'content': 'Dépôt synthétique.'},
                {'role': 'assistant', 'content': ''},
            ],
            arbiter_module=SimpleNamespace(),
            memory_store_module=store,
        )

        state = store.get_identity_staging_state('conv-presence-staging')
        self.assertEqual(summary['status'], 'buffering')
        self.assertEqual(
            state['buffer_pairs'],
            [
                {
                    'user': {'role': 'user', 'content': 'Dépôt synthétique.'},
                    'assistant': {'role': 'assistant', 'content': ''},
                }
            ],
        )

    def _run_threshold_window_with_logged_final_turn(
        self,
        *,
        conversation_id: str,
        proposition: str,
        arbiter_module: Any,
    ) -> tuple[_InMemoryIdentityStore, dict[str, Any], dict[str, Any]]:
        store = _InMemoryIdentityStore()
        for index in range(1, memory_identity_periodic_agent.BUFFER_TARGET_PAIRS):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                conversation_id,
                _support_pair(index, proposition),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id=conversation_id,
            user_msg='redacted final turn',
            web_search_enabled=False,
        )
        try:
            summary = memory_identity_periodic_agent.stage_identity_turn_pair(
                conversation_id,
                _support_pair(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS, proposition),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        event = next(item for item in observed if item['stage'] == 'mutable_identity_judge')
        return store, summary, event

    def _assert_periodic_event_is_redacted(
        self,
        payload: dict[str, Any],
        *,
        forbidden_texts: list[str],
    ) -> None:
        self.assertTrue(
            {'buffer_pairs', 'buffer_pairs_json', 'content', 'proposition', 'prompt', 'messages'}.isdisjoint(
                _collect_keys(payload)
            )
        )
        serialized = repr(payload)
        for text in forbidden_texts:
            self.assertNotIn(text, serialized)

    def test_completed_summary_state_treats_non_write_outcomes_as_no_change(self) -> None:
        status, reason = memory_identity_periodic_agent._completed_summary_state(
            {
                'reason_code': 'completed_no_change',
                'writes_applied': False,
                'outcomes': [
                    {
                        'subject': 'user',
                        'action': 'raise_conflict',
                        'reason_code': 'contradiction_with_static',
                    }
                ],
            }
        )

        self.assertEqual(status, 'completed_no_change')
        self.assertEqual(reason, 'completed_no_change')

    def test_periodic_agent_event_marks_legacy_writer_disabled_for_valid_no_change_run(self) -> None:
        proposition = 'Tof maintient une observation stable sans nouvelle canonisation.'
        arbiter_module = SimpleNamespace(
            run_mutable_identity_judge=lambda _payload: _judge_ok(_contract())
        )

        _store, summary, event = self._run_threshold_window_with_logged_final_turn(
            conversation_id='conv-log-no-change',
            proposition=proposition,
            arbiter_module=arbiter_module,
        )
        payload = event['payload_json']

        self.assertEqual(event['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'completed_no_change')
        self.assertEqual(payload['reason_code'], 'completed_no_change')
        self.assertFalse(payload['writes_applied'])
        self.assertTrue(payload['legacy_writer_disabled'])
        self.assertFalse(payload['score_first_writer_enabled'])
        self.assertEqual(payload['promotion_count'], 0)
        self.assertEqual(payload['rejection_reasons'], {})
        self.assertEqual(payload['verdict_counts'], {'no_change': 2})
        self._assert_periodic_event_is_redacted(payload, forbidden_texts=[proposition, 'utilisateur 5', 'assistant 5'])

    def test_periodic_agent_event_neutralizes_valid_legacy_write_contract(self) -> None:
        proposition = 'Tof tient une attention durable aux details stables.'
        arbiter_module = SimpleNamespace(
            run_mutable_identity_judge=lambda _payload: _judge_ok(_contract(_persist_add('user', proposition)))
        )

        store, summary, event = self._run_threshold_window_with_logged_final_turn(
            conversation_id='conv-log-applied',
            proposition=proposition,
            arbiter_module=arbiter_module,
        )
        payload = event['payload_json']

        self.assertEqual(event['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'applied')
        self.assertEqual(payload['reason_code'], 'applied')
        self.assertTrue(payload['writes_applied'])
        self.assertTrue(payload['legacy_writer_disabled'])
        self.assertEqual(payload['promotion_count'], 0)
        self.assertEqual(store.mutable['user']['content'], proposition)
        self.assertEqual(store.upsert_calls[0][2], 'mutable_identity_judge_apply')
        self.assertEqual(payload['verdict_counts']['add'], 1)
        self._assert_periodic_event_is_redacted(payload, forbidden_texts=[proposition, 'attention durable'])

    def test_periodic_agent_event_rejects_legacy_tension_contract(self) -> None:
        proposition = 'Tof semble osciller entre retrait durable et besoin d exposition.'
        arbiter_module = SimpleNamespace(
            run_mutable_identity_judge=lambda _payload: _judge_ok(_contract(_raise_tension('user', proposition)))
        )

        _store, summary, event = self._run_threshold_window_with_logged_final_turn(
            conversation_id='conv-log-open-tension',
            proposition=proposition,
            arbiter_module=arbiter_module,
        )
        payload = event['payload_json']

        self.assertEqual(event['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'invalid_verdict')
        self.assertEqual(summary['last_agent_status'], 'retry_pending')
        self.assertEqual(payload['reason_code'], 'invalid_verdict')
        self.assertFalse(payload['writes_applied'])
        self.assertTrue(payload['legacy_writer_disabled'])
        self.assertEqual(payload['verdict_counts']['raise_tension'], 1)
        self.assertFalse(payload['buffer_cleared'])
        self._assert_periodic_event_is_redacted(payload, forbidden_texts=[proposition, 'osciller'])

    def test_does_not_call_agent_before_five_pairs(self) -> None:
        store = _InMemoryIdentityStore()
        calls: list[dict[str, Any]] = []
        arbiter_module = SimpleNamespace(
            run_mutable_identity_judge=lambda payload: calls.append(copy.deepcopy(payload)) or _judge_ok(_contract())
        )

        for index in range(1, memory_identity_periodic_agent.BUFFER_TARGET_PAIRS):
            summary = memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-before-threshold',
                _pair(index),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )
            self.assertEqual(summary['status'], 'buffering')
            self.assertEqual(summary['reason_code'], 'below_threshold')
            self.assertEqual(summary['buffer_pairs_count'], index)
            self.assertEqual(summary['buffer_target_pairs'], memory_identity_periodic_agent.BUFFER_TARGET_PAIRS)
            self.assertFalse(summary['buffer_cleared'])
            self.assertFalse(summary['writes_applied'])
            self.assertEqual(
                store.get_identity_staging_state('conv-before-threshold')['buffer_pairs_count'],
                index,
            )

        self.assertEqual(summary['status'], 'buffering')
        self.assertEqual(summary['reason_code'], 'below_threshold')
        self.assertEqual(summary['buffer_pairs_count'], memory_identity_periodic_agent.BUFFER_TARGET_PAIRS - 1)
        self.assertEqual(calls, [])
        self.assertEqual(
            store.get_identity_staging_state('conv-before-threshold')['buffer_pairs_count'],
            memory_identity_periodic_agent.BUFFER_TARGET_PAIRS - 1,
        )

    def test_incomplete_turn_pair_does_not_call_agent_or_append_window(self) -> None:
        store = _InMemoryIdentityStore()
        calls: list[dict[str, Any]] = []
        arbiter_module = SimpleNamespace(
            run_mutable_identity_judge=lambda payload: calls.append(copy.deepcopy(payload)) or _judge_ok(_contract())
        )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-incomplete-pair',
            [{'role': 'user', 'content': 'utilisateur seul'}],
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'incomplete_turn_pair')
        self.assertEqual(summary['buffer_pairs_count'], 0)
        self.assertEqual(summary['buffer_target_pairs'], memory_identity_periodic_agent.BUFFER_TARGET_PAIRS)
        self.assertEqual(calls, [])
        self.assertIsNone(store.get_identity_staging_state('conv-incomplete-pair'))

    def test_calls_agent_at_exact_threshold_and_clears_buffer_after_valid_transitional_run(self) -> None:
        store = _InMemoryIdentityStore()
        observed_payloads: list[dict[str, Any]] = []
        proposition = 'Tof tient une attention durable aux details stables.'

        def fake_run_mutable_identity_judge(payload: dict[str, Any]) -> dict[str, Any]:
            observed_payloads.append(copy.deepcopy(payload))
            return _judge_ok(_contract(_persist_add('user', proposition)))

        arbiter_module = SimpleNamespace(run_mutable_identity_judge=fake_run_mutable_identity_judge)
        for index in range(1, memory_identity_periodic_agent.BUFFER_TARGET_PAIRS):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-threshold',
                _support_pair(index, proposition),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-threshold',
            _support_pair(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS, proposition),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(len(observed_payloads), 1)
        self.assertEqual(len(observed_payloads[0]['window_pairs']), memory_identity_periodic_agent.BUFFER_TARGET_PAIRS)
        for expected_index, pair in enumerate(observed_payloads[0]['window_pairs'], start=1):
            self.assertEqual(pair['user']['role'], 'user')
            self.assertEqual(pair['assistant']['role'], 'assistant')
            self.assertIn(f'utilisateur {expected_index}', pair['user']['content'])
            self.assertIn(f'assistant {expected_index}', pair['assistant']['content'])
        score_fields = {'strength', 'frequency_norm', 'recency_norm', 'threshold_verdict'}
        self.assertTrue(score_fields.isdisjoint(_collect_keys(observed_payloads[0])))
        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'applied')
        self.assertTrue(summary['buffer_cleared'])
        self.assertTrue(summary['writes_applied'])
        self.assertTrue(summary['legacy_writer_disabled'])
        self.assertEqual(store.get_identity_staging_state('conv-threshold')['buffer_pairs_count'], 0)
        self.assertEqual(store.mutable['user']['content'], proposition)
        self.assertEqual(store.upsert_calls[0][2], 'mutable_identity_judge_apply')

    def test_legacy_tension_contract_preserves_buffer_as_invalid_v2(self) -> None:
        store = _InMemoryIdentityStore()
        proposition = 'Tof semble osciller entre retrait durable et besoin d exposition.'

        arbiter_module = SimpleNamespace(
            run_mutable_identity_judge=lambda _payload: _judge_ok(_contract(_raise_tension('user', proposition)))
        )

        for index in range(1, memory_identity_periodic_agent.BUFFER_TARGET_PAIRS):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-open-tension',
                _support_pair(index, proposition),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-open-tension',
            _support_pair(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS, proposition),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'invalid_verdict')
        self.assertEqual(summary['last_agent_status'], 'retry_pending')
        self.assertFalse(summary['buffer_cleared'])
        self.assertFalse(summary['writes_applied'])
        self.assertTrue(summary['legacy_writer_disabled'])
        self.assertEqual(summary['verdict_counts']['raise_tension'], 1)
        staging_state = store.get_identity_staging_state('conv-open-tension')
        self.assertEqual(staging_state['buffer_pairs_count'], memory_identity_periodic_agent.BUFFER_TARGET_PAIRS)
        self.assertEqual(staging_state['last_agent_status'], 'retry_pending')
        self.assertEqual(staging_state['last_agent_reason'], 'invalid_verdict')

        next_summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-open-tension',
            _support_pair(16, proposition),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(next_summary['status'], 'skipped')
        self.assertEqual(next_summary['reason_code'], 'invalid_verdict')
        self.assertEqual(next_summary['last_agent_status'], 'terminal_discarded')
        self.assertEqual(store.get_identity_staging_state('conv-open-tension')['buffer_pairs_count'], 1)

    def test_reject_and_defer_are_invalid_v2_and_preserve_buffer(self) -> None:
        store = _InMemoryIdentityStore()
        arbiter_module = SimpleNamespace(
            run_mutable_identity_judge=lambda _payload: _judge_ok(
                _contract(
                    _non_persist('user', 'reject', 'task_local_not_identity'),
                    _non_persist('llm', 'defer', 'insufficient_context'),
                )
            )
        )

        for index in range(1, memory_identity_periodic_agent.BUFFER_TARGET_PAIRS):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-reject-defer',
                _pair(index),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-reject-defer',
            _pair(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'invalid_verdict')
        self.assertEqual(summary['last_agent_status'], 'retry_pending')
        self.assertFalse(summary['buffer_cleared'])
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(summary['verdict_counts'], {'defer': 1, 'reject': 1})
        self.assertEqual(store.mutable, {})
        self.assertEqual(
            store.get_identity_staging_state('conv-reject-defer')['buffer_pairs_count'],
            memory_identity_periodic_agent.BUFFER_TARGET_PAIRS,
        )

    def test_shadow_mode_runs_judge_without_canonical_write(self) -> None:
        store = _InMemoryIdentityStore()
        observed_payloads: list[dict[str, Any]] = []
        proposition = 'Tof tient une preference durable pour les preuves compactes.'

        def fake_run_mutable_identity_judge(payload: dict[str, Any]) -> dict[str, Any]:
            observed_payloads.append(copy.deepcopy(payload))
            return _judge_ok(_contract(_persist_add('user', proposition)))

        arbiter_module = SimpleNamespace(run_mutable_identity_judge=fake_run_mutable_identity_judge)
        for index in range(1, memory_identity_periodic_agent.BUFFER_TARGET_PAIRS):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-shadow-runtime',
                _support_pair(index, proposition),
                arbiter_module=arbiter_module,
                memory_store_module=store,
                enforce_writes=False,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-shadow-runtime',
            _support_pair(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS, proposition),
            arbiter_module=arbiter_module,
            memory_store_module=store,
            enforce_writes=False,
        )

        self.assertEqual(len(observed_payloads), 1)
        self.assertEqual(len(observed_payloads[0]['window_pairs']), memory_identity_periodic_agent.BUFFER_TARGET_PAIRS)
        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'shadow_completed')
        self.assertEqual(summary['last_agent_status'], 'shadow_completed')
        self.assertEqual(summary['write_mode'], 'shadow')
        self.assertTrue(summary['shadow_mode'])
        self.assertTrue(summary['buffer_cleared'])
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(store.mutable, {})
        self.assertEqual(store.upsert_calls, [])

    def test_valid_legacy_contract_does_not_enter_old_all_or_nothing_applicator(self) -> None:
        store = _InMemoryIdentityStore()
        existing_llm_content = _build_large_identity_block('Frida', min_length=3290)
        store.mutable['llm'] = {
            'subject': 'llm',
            'content': existing_llm_content,
            'updated_by': 'identity_periodic_agent',
            'update_reason': 'periodic_agent',
        }
        llm_proposition = 'Frida tient un axe de synthese stable.'
        user_proposition = 'Tof tient un fil identitaire stable.'

        def fake_run_mutable_identity_judge(_payload: dict[str, Any]) -> dict[str, Any]:
            return _judge_ok(_contract(_persist_add('llm', llm_proposition), _persist_add('user', user_proposition)))

        arbiter_module = SimpleNamespace(run_mutable_identity_judge=fake_run_mutable_identity_judge)
        for index in range(1, memory_identity_periodic_agent.BUFFER_TARGET_PAIRS):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-all-or-nothing',
                _support_pair(index, f'{llm_proposition} {user_proposition}'),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-all-or-nothing',
            _support_pair(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS, f'{llm_proposition} {user_proposition}'),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'mutable_content_too_long')
        self.assertEqual(summary['last_agent_status'], 'retry_pending')
        self.assertFalse(summary['buffer_cleared'])
        self.assertFalse(summary['writes_applied'])
        self.assertTrue(summary['legacy_writer_disabled'])
        self.assertEqual(summary['rejection_reasons'], {})
        self.assertEqual(store.upsert_calls, [])
        self.assertEqual(store.mutable['llm']['content'], existing_llm_content)
        self.assertNotIn('user', store.mutable)
        self.assertEqual(
            store.get_identity_staging_state('conv-all-or-nothing')['buffer_pairs_count'],
            memory_identity_periodic_agent.BUFFER_TARGET_PAIRS,
        )
        self.assertGreater(summary['failed_count'], 0)

    def test_preserves_buffer_when_new_applicator_raises_unexpected_error(self) -> None:
        store = _InMemoryIdentityStore()
        proposition = 'Tof maintient une limite durable sur les promesses intenables.'
        arbiter_module = SimpleNamespace(
            run_mutable_identity_judge=lambda _payload: _judge_ok(_contract(_persist_add('user', proposition)))
        )
        original_apply = (
            memory_identity_periodic_agent.mutable_identity_runtime
            .mutable_identity_apply
            .apply_mutable_judge_contract
        )

        def boom(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            raise RuntimeError('unexpected apply failure')

        memory_identity_periodic_agent.mutable_identity_runtime.mutable_identity_apply.apply_mutable_judge_contract = boom
        try:
            for index in range(1, memory_identity_periodic_agent.BUFFER_TARGET_PAIRS):
                memory_identity_periodic_agent.stage_identity_turn_pair(
                    'conv-apply-raises',
                    _support_pair(index, proposition),
                    arbiter_module=arbiter_module,
                    memory_store_module=store,
                )

            summary = memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-apply-raises',
                _support_pair(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS, proposition),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )
        finally:
            (
                memory_identity_periodic_agent.mutable_identity_runtime
                .mutable_identity_apply
                .apply_mutable_judge_contract
            ) = original_apply

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'canonical_write_failed')
        self.assertEqual(summary['last_agent_status'], 'write_recovery_pending')
        self.assertFalse(summary['buffer_cleared'])
        self.assertTrue(summary['buffer_frozen'])
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(summary['failed_count'], 1)
        staging = store.get_identity_staging_state('conv-apply-raises')
        self.assertEqual(staging['buffer_pairs_count'], memory_identity_periodic_agent.BUFFER_TARGET_PAIRS)
        self.assertEqual(staging['last_agent_status'], 'write_recovery_pending')
        self.assertEqual(staging['last_agent_reason'], 'canonical_write_failed')
        self.assertEqual(store.mutable, {})
        self.assertEqual(store.upsert_calls, [])

    def test_preserves_buffer_when_agent_returns_invalid_contract(self) -> None:
        store = _InMemoryIdentityStore()
        arbiter_module = SimpleNamespace(
            run_mutable_identity_judge=lambda _payload: {
                'status': 'skipped',
                'reason_code': 'schema_invalid',
                'contract': None,
                'observability': {'status': 'skipped', 'reason_code': 'schema_invalid'},
            }
        )

        for index in range(1, memory_identity_periodic_agent.BUFFER_TARGET_PAIRS):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-invalid-contract',
                _pair(index),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-invalid-contract',
            _pair(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['last_agent_status'], 'retry_pending')
        self.assertFalse(summary['buffer_cleared'])
        self.assertTrue(summary['buffer_frozen'])
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(
            store.get_identity_staging_state('conv-invalid-contract')['buffer_pairs_count'],
            memory_identity_periodic_agent.BUFFER_TARGET_PAIRS,
        )
        self.assertEqual(store.upsert_calls, [])

    def test_preserves_buffer_when_agent_returns_contradictory_no_change_mix(self) -> None:
        store = _InMemoryIdentityStore()
        proposition = 'Tof maintient une tension encore mal tranchee.'
        arbiter_module = SimpleNamespace(
            run_mutable_identity_judge=lambda _payload: {
                'status': 'skipped',
                'reason_code': 'schema_invalid',
                'contract': None,
                'observability': {'status': 'skipped', 'reason_code': 'schema_invalid'},
            }
        )

        for index in range(1, memory_identity_periodic_agent.BUFFER_TARGET_PAIRS):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-no-change-mixed',
                _support_pair(index, proposition),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-no-change-mixed',
            _support_pair(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS, proposition),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'schema_invalid')
        self.assertEqual(summary['last_agent_status'], 'retry_pending')
        self.assertFalse(summary['buffer_cleared'])
        self.assertTrue(summary['buffer_frozen'])
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(
            store.get_identity_staging_state('conv-no-change-mixed')['buffer_pairs_count'],
            memory_identity_periodic_agent.BUFFER_TARGET_PAIRS,
        )
        self.assertEqual(store.upsert_calls, [])

    def test_preserves_buffer_when_agent_skips_window_too_large(self) -> None:
        store = _InMemoryIdentityStore()
        arbiter_module = SimpleNamespace(
            run_mutable_identity_judge=lambda _payload: {
                'status': 'skipped',
                'reason_code': 'window_too_large',
                'contract': None,
                'observability': {
                    'status': 'skipped',
                    'reason_code': 'window_too_large',
                'window_chars': 25000,
                'payload_chars': 28000,
                'estimated_prompt_tokens': 8500,
                'max_window_chars': 32000,
                'max_estimated_prompt_tokens': 12000,
                },
            }
        )

        for index in range(1, memory_identity_periodic_agent.BUFFER_TARGET_PAIRS):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-window-too-large',
                _pair(index),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-window-too-large',
            _pair(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'window_too_large')
        self.assertEqual(summary['last_agent_status'], 'terminal_discarded')
        self.assertTrue(summary['buffer_cleared'])
        self.assertTrue(summary['buffer_frozen'])
        self.assertFalse(summary['writes_applied'])
        self.assertEqual(summary['window_chars'], 25000)
        self.assertEqual(summary['payload_chars'], 28000)
        self.assertEqual(summary['estimated_prompt_tokens'], 8500)
        self.assertEqual(summary['max_window_chars'], 32000)
        self.assertEqual(summary['max_estimated_prompt_tokens'], 12000)
        self.assertEqual(
            store.get_identity_staging_state('conv-window-too-large')['buffer_pairs_count'],
            0,
        )
        self.assertEqual(store.upsert_calls, [])

    def test_retry_reuses_exact_same_five_pair_window_after_failed_attempt(self) -> None:
        store = _InMemoryIdentityStore()
        observed_payloads: list[dict[str, Any]] = []
        proposition = 'Tof tient une attention stable.'
        responses = [
            {
                'status': 'skipped',
                'reason_code': 'schema_invalid',
                'contract': None,
                'observability': {'status': 'skipped', 'reason_code': 'schema_invalid'},
            },
            _judge_ok(_contract(_persist_add('user', proposition))),
        ]

        def fake_run_mutable_identity_judge(payload: dict[str, Any]) -> dict[str, Any]:
            observed_payloads.append(copy.deepcopy(payload))
            return copy.deepcopy(responses.pop(0))

        arbiter_module = SimpleNamespace(run_mutable_identity_judge=fake_run_mutable_identity_judge)
        for index in range(1, memory_identity_periodic_agent.BUFFER_TARGET_PAIRS):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-retry-frozen',
                _support_pair(index, proposition),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        first_summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-retry-frozen',
            _support_pair(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS, proposition),
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
        self.assertEqual(first_summary['last_agent_status'], 'retry_pending')
        self.assertFalse(first_summary['buffer_cleared'])
        self.assertEqual(len(observed_payloads), 2)
        self.assertEqual(len(observed_payloads[0]['window_pairs']), memory_identity_periodic_agent.BUFFER_TARGET_PAIRS)
        self.assertEqual(len(observed_payloads[1]['window_pairs']), memory_identity_periodic_agent.BUFFER_TARGET_PAIRS)
        self.assertEqual(observed_payloads[0]['window_pairs'], observed_payloads[1]['window_pairs'])
        self.assertEqual(
            observed_payloads[1]['window_pairs'][-1]['user']['content'],
            f'utilisateur {memory_identity_periodic_agent.BUFFER_TARGET_PAIRS} {proposition}',
        )
        self.assertTrue(second_summary['buffer_frozen'])
        self.assertTrue(second_summary['buffer_cleared'])
        self.assertEqual(second_summary['reason_code'], 'applied')
        self.assertTrue(second_summary['writes_applied'])
        self.assertEqual(store.get_identity_staging_state('conv-retry-frozen')['buffer_pairs_count'], 1)
        self.assertEqual(store.mutable['user']['content'], proposition)

    def test_new_runtime_does_not_call_legacy_scoring_or_static_writer(self) -> None:
        store = _InMemoryIdentityStore()
        proposition = 'Tof tient une limite durable sur les promesses intenables.'
        original_write_static = static_identity_content.write_static_identity_content
        calls = {'static': 0}

        def forbidden_static(*_args: Any, **_kwargs: Any) -> Any:
            calls['static'] += 1
            raise AssertionError('static identity must not be written')

        arbiter_module = SimpleNamespace(
            run_mutable_identity_judge=lambda _payload: _judge_ok(_contract(_persist_add('user', proposition)))
        )
        static_identity_content.write_static_identity_content = forbidden_static
        try:
            for index in range(1, memory_identity_periodic_agent.BUFFER_TARGET_PAIRS):
                memory_identity_periodic_agent.stage_identity_turn_pair(
                    'conv-no-legacy-score',
                    _support_pair(index, proposition),
                    arbiter_module=arbiter_module,
                    memory_store_module=store,
                )

            summary = memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-no-legacy-score',
                _support_pair(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS, proposition),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )
        finally:
            static_identity_content.write_static_identity_content = original_write_static

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'applied')
        self.assertTrue(summary['writes_applied'])
        self.assertEqual(calls, {'static': 0})
        self.assertEqual(store.mutable['user']['content'], proposition)

    def test_judge_first_contract_does_not_enter_double_saturation_static_promotion(self) -> None:
        store = _InMemoryIdentityStore()
        proposition = 'Tof tient une orientation stable et ritualisee.'
        filler = _build_large_identity_block('Tof', min_length=2980)
        store.mutable['user'] = {
            'subject': 'user',
            'content': filler,
            'updated_by': 'legacy_fixture',
            'update_reason': 'pre_refactor_fixture',
        }

        arbiter_module = SimpleNamespace(
            run_mutable_identity_judge=lambda _payload: _judge_ok(_contract(_persist_add('user', proposition)))
        )

        for index in range(1, memory_identity_periodic_agent.BUFFER_TARGET_PAIRS):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-double-saturation',
                _support_pair(index, proposition),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-double-saturation',
            _support_pair(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS, proposition),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'applied')
        self.assertEqual(summary['last_agent_status'], 'applied')
        self.assertTrue(summary['buffer_cleared'])
        self.assertTrue(summary['buffer_frozen'])
        self.assertFalse(summary['auto_canonization_suspended'])
        self.assertTrue(summary['writes_applied'])
        self.assertTrue(summary['legacy_writer_disabled'])
        staging_state = store.get_identity_staging_state('conv-double-saturation')
        self.assertEqual(staging_state['buffer_pairs_count'], 0)
        self.assertFalse(staging_state['auto_canonization_suspended'])
        self.assertIn(proposition, store.mutable['user']['content'])
        self.assertTrue(store.mutable['user']['content'].startswith(filler))

    def test_preserves_buffer_when_agent_raises_timeout(self) -> None:
        store = _InMemoryIdentityStore()

        def boom(_payload: dict[str, Any]) -> dict[str, Any]:
            raise TimeoutError('timeout')

        arbiter_module = SimpleNamespace(run_mutable_identity_judge=boom)
        for index in range(1, memory_identity_periodic_agent.BUFFER_TARGET_PAIRS):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-timeout',
                _pair(index),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-timeout',
            _pair(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'judge_transport_error')
        self.assertEqual(summary['last_agent_status'], 'retry_pending')
        self.assertFalse(summary['buffer_cleared'])
        self.assertEqual(
            store.get_identity_staging_state('conv-timeout')['buffer_pairs_count'],
            memory_identity_periodic_agent.BUFFER_TARGET_PAIRS,
        )
        self.assertEqual(store.upsert_calls, [])

    def test_preserves_buffer_when_agent_raises_runtime_error(self) -> None:
        store = _InMemoryIdentityStore()

        def boom(_payload: dict[str, Any]) -> dict[str, Any]:
            raise RuntimeError('provider blew up')

        arbiter_module = SimpleNamespace(run_mutable_identity_judge=boom)
        for index in range(1, memory_identity_periodic_agent.BUFFER_TARGET_PAIRS):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                'conv-runtime-error',
                _pair(index),
                arbiter_module=arbiter_module,
                memory_store_module=store,
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            'conv-runtime-error',
            _pair(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS),
            arbiter_module=arbiter_module,
            memory_store_module=store,
        )

        self.assertEqual(summary['status'], 'skipped')
        self.assertEqual(summary['reason_code'], 'judge_transport_error')
        self.assertEqual(summary['last_agent_status'], 'retry_pending')
        self.assertFalse(summary['buffer_cleared'])
        self.assertTrue(summary['buffer_frozen'])
        self.assertEqual(
            store.get_identity_staging_state('conv-runtime-error')['buffer_pairs_count'],
            memory_identity_periodic_agent.BUFFER_TARGET_PAIRS,
        )
        self.assertEqual(store.upsert_calls, [])


if __name__ == '__main__':
    unittest.main()
