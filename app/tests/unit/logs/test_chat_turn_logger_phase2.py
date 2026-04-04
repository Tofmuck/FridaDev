from __future__ import annotations

import sys
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

from observability import chat_turn_logger
from observability import hermeneutic_node_logger
from observability import log_store
from identity import identity
from memory import memory_arbiter_audit
from memory import memory_context_read
from memory import memory_identity_dynamics
from memory import memory_store
from memory import memory_traces_summaries
from tools import web_search


class ChatTurnLoggerPhase2Tests(unittest.TestCase):
    def test_begin_end_emits_turn_start_and_turn_end(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-phase2',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        self.assertEqual(observed[0]['stage'], 'turn_start')
        self.assertEqual(observed[0]['status'], 'ok')
        self.assertEqual(observed[-1]['stage'], 'turn_end')
        self.assertEqual(observed[-1]['payload_json']['final_status'], 'ok')

    def test_end_turn_uses_error_status_when_final_status_is_error(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-error',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.end_turn(token, final_status='error')
        finally:
            log_store.insert_chat_log_event = original_insert

        turn_end_event = observed[-1]
        self.assertEqual(turn_end_event['stage'], 'turn_end')
        self.assertEqual(turn_end_event['status'], 'error')
        self.assertEqual(turn_end_event['payload_json']['final_status'], 'error')

    def test_pending_conversation_buffers_until_real_conversation_id(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id=None,
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.emit(
                'web_search',
                status='skipped',
                reason_code='feature_disabled',
                payload={
                    'enabled': False,
                    'query_preview': '',
                    'results_count': 0,
                    'context_injected': False,
                    'truncated': False,
                },
            )
            self.assertEqual(observed, [])
            chat_turn_logger.update_conversation_id('conv-real')
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        self.assertEqual(observed[0]['stage'], 'turn_start')
        self.assertEqual(observed[1]['stage'], 'web_search')
        self.assertTrue(all(event['conversation_id'] == 'conv-real' for event in observed))
        self.assertNotIn('__pending__', {event['conversation_id'] for event in observed})

    def test_emit_is_best_effort_when_store_insert_raises(self) -> None:
        original_insert = log_store.insert_chat_log_event

        def fake_insert_raise(*_args: Any, **_kwargs: Any) -> bool:
            raise RuntimeError('store down')

        log_store.insert_chat_log_event = fake_insert_raise
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-phase2',
            user_msg='bonjour',
            web_search_enabled=True,
        )
        try:
            # No exception must propagate despite insert failures.
            self.assertFalse(chat_turn_logger.emit('context_build', status='ok', payload={'estimated_context_tokens': 12}))
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

    def test_emit_sanitizes_preview_payload(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-preview',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.emit(
                'identities_read',
                status='ok',
                payload={
                    'preview': ['x' * 300, 'y' * 300, 'z' * 300, 'w' * 300],
                    'keys': ['a' * 200, 'b' * 200, 'c' * 200, 'd' * 200],
                    'truncated': False,
                },
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        identities_event = next(event for event in observed if event['stage'] == 'identities_read')
        payload = identities_event['payload_json']
        self.assertEqual(len(payload['preview']), 3)
        self.assertEqual(len(payload['keys']), 3)
        self.assertTrue(payload['truncated'])
        self.assertTrue(all(len(item) <= 120 for item in payload['preview']))
        self.assertTrue(all(len(item) <= 64 for item in payload['keys']))

    def test_event_contract_required_fields_and_status_taxonomy(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-contract',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.emit('context_build', status='ok', payload={'estimated_context_tokens': 42, 'token_limit': 4000})
            chat_turn_logger.emit_branch_skipped(reason_code='no_data', reason_short='no_optional_branch')
            chat_turn_logger.emit_error(
                error_code='upstream_error',
                error_class='RuntimeError',
                message_short='boom',
            )
            chat_turn_logger.end_turn(token, final_status='error')
        finally:
            log_store.insert_chat_log_event = original_insert

        self.assertTrue(observed)
        required = {'event_id', 'conversation_id', 'turn_id', 'ts', 'stage', 'status'}
        statuses: set[str] = set()
        for event in observed:
            self.assertTrue(required.issubset(set(event.keys())))
            for field in required:
                self.assertTrue(str(event[field] or '').strip(), msg=f'empty field {field} in {event}')
            statuses.add(str(event['status']))

        self.assertTrue({'ok', 'error', 'skipped'}.issubset(statuses))

    def test_hermeneutic_node_insertion_emits_compact_presence_quality_payload(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-hermeneutic-insertion',
            user_msg='bonjour',
            web_search_enabled=True,
        )
        try:
            hermeneutic_node_logger.emit_hermeneutic_node_insertion(
                time_input={
                    'schema_version': 'v1',
                    'now_utc_iso': '2026-03-31T09:30:00Z',
                    'timezone': 'Europe/Paris',
                    'now_local_iso': '2026-03-31T11:30:00+02:00',
                    'local_date': '2026-03-31',
                    'local_time': '11:30',
                    'local_weekday': 'tuesday',
                    'day_part_class': 'morning',
                    'day_part_human': 'matin',
                },
                current_mode='shadow',
                memory_retrieved={
                    'retrieved_count': 2,
                },
                memory_arbitration={
                    'status': 'available',
                    'decisions_count': 2,
                    'kept_count': 1,
                    'rejected_count': 1,
                },
                summary_input={
                    'status': 'available',
                },
                identity_input={
                    'frida': {'static': {'content': 'Frida'}, 'dynamic': [{'id': 'f1'}]},
                    'user': {'static': {'content': ''}, 'dynamic': [{'id': 'u1'}, {'id': 'u2'}]},
                },
                recent_context_input={
                    'messages': [{'role': 'user'}, {'role': 'assistant'}],
                },
                recent_window_input={
                    'turn_count': 1,
                    'has_in_progress_turn': False,
                    'max_recent_turns': 5,
                },
                user_turn_input={
                    'schema_version': 'v1',
                    'geste_dialogique_dominant': 'interrogation',
                    'regime_probatoire': {
                        'principe': 'maximal_possible',
                        'types_de_preuve_attendus': ['factuelle', 'dialogique'],
                        'provenances': ['dialogue_trace'],
                        'regime_de_vigilance': 'standard',
                        'composition_probatoire': 'appuyee',
                    },
                    'qualification_temporelle': {
                        'portee_temporelle': 'passee',
                        'ancrage_temporel': 'dialogue_trace',
                    },
                },
                user_turn_signals={
                    'present': True,
                    'ambiguity_present': False,
                    'underdetermination_present': True,
                    'active_signal_families': ['critere'],
                    'active_signal_families_count': 1,
                },
                stimmung_input={
                    'schema_version': 'v1',
                    'present': True,
                    'dominant_tone': 'frustration',
                    'active_tones': [
                        {'tone': 'frustration', 'strength': 6},
                        {'tone': 'confusion', 'strength': 3},
                    ],
                    'stability': 'stable',
                    'shift_state': 'steady',
                    'turns_considered': 4,
                },
                web_input={
                    'enabled': True,
                    'status': 'ok',
                    'results_count': 3,
                },
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        event = next(item for item in observed if item['stage'] == 'hermeneutic_node_insertion')
        payload = event['payload_json']
        self.assertEqual(event['status'], 'ok')
        self.assertTrue(payload['insertion_point_reached'])
        self.assertEqual(payload['mode'], 'shadow')
        self.assertTrue(payload['inputs']['time']['present'])
        self.assertEqual(payload['inputs']['time']['timezone'], 'Europe/Paris')
        self.assertEqual(payload['inputs']['time']['day_part_class'], 'morning')
        self.assertEqual(payload['inputs']['memory_retrieved']['retrieved_count'], 2)
        self.assertEqual(payload['inputs']['memory_arbitration']['status'], 'available')
        self.assertEqual(payload['inputs']['memory_arbitration']['decisions_count'], 2)
        self.assertEqual(payload['inputs']['memory_arbitration']['kept_count'], 1)
        self.assertEqual(payload['inputs']['memory_arbitration']['rejected_count'], 1)
        self.assertEqual(payload['inputs']['summary']['status'], 'available')
        self.assertTrue(payload['inputs']['identity']['frida']['static_present'])
        self.assertFalse(payload['inputs']['identity']['user']['static_present'])
        self.assertEqual(payload['inputs']['identity']['frida']['dynamic_count'], 1)
        self.assertEqual(payload['inputs']['identity']['user']['dynamic_count'], 2)
        self.assertEqual(payload['inputs']['recent_context']['messages_count'], 2)
        self.assertEqual(payload['inputs']['recent_window']['turn_count'], 1)
        self.assertFalse(payload['inputs']['recent_window']['has_in_progress_turn'])
        self.assertEqual(payload['inputs']['recent_window']['max_recent_turns'], 5)
        self.assertTrue(payload['inputs']['user_turn']['present'])
        self.assertEqual(payload['inputs']['user_turn']['geste_dialogique_dominant'], 'interrogation')
        self.assertEqual(payload['inputs']['user_turn']['regime_probatoire']['principe'], 'maximal_possible')
        self.assertEqual(
            payload['inputs']['user_turn']['regime_probatoire']['types_de_preuve_attendus'],
            ['factuelle', 'dialogique'],
        )
        self.assertEqual(payload['inputs']['user_turn']['regime_probatoire']['regime_de_vigilance'], 'standard')
        self.assertEqual(payload['inputs']['user_turn']['qualification_temporelle']['portee_temporelle'], 'passee')
        self.assertEqual(
            payload['inputs']['user_turn']['qualification_temporelle']['ancrage_temporel'],
            'dialogue_trace',
        )
        self.assertTrue(payload['inputs']['user_turn_signals']['present'])
        self.assertFalse(payload['inputs']['user_turn_signals']['ambiguity_present'])
        self.assertTrue(payload['inputs']['user_turn_signals']['underdetermination_present'])
        self.assertEqual(payload['inputs']['user_turn_signals']['active_signal_families'], ['critere'])
        self.assertEqual(payload['inputs']['user_turn_signals']['active_signal_families_count'], 1)
        self.assertTrue(payload['inputs']['stimmung']['present'])
        self.assertEqual(payload['inputs']['stimmung']['dominant_tone'], 'frustration')
        self.assertEqual(
            payload['inputs']['stimmung']['active_tones'],
            [
                {'tone': 'frustration', 'strength': 6},
                {'tone': 'confusion', 'strength': 3},
            ],
        )
        self.assertEqual(payload['inputs']['stimmung']['stability'], 'stable')
        self.assertEqual(payload['inputs']['stimmung']['shift_state'], 'steady')
        self.assertEqual(payload['inputs']['stimmung']['turns_considered'], 4)
        self.assertTrue(payload['inputs']['web']['enabled'])
        self.assertEqual(payload['inputs']['web']['status'], 'ok')
        self.assertEqual(payload['inputs']['web']['results_count'], 3)

    def test_stimmung_agent_stage_emits_compact_upstream_payload(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-stimmung-stage',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            chat_turn_logger.emit(
                'stimmung_agent',
                status='error',
                model='openai/gpt-5.4-nano',
                payload={
                    'present': False,
                    'dominant_tone': None,
                    'tones_count': 0,
                    'tones': [],
                    'confidence': 0.0,
                    'decision_source': 'fail_open',
                    'reason_code': 'invalid_json',
                },
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        event = next(item for item in observed if item['stage'] == 'stimmung_agent')
        payload = event['payload_json']
        self.assertEqual(event['status'], 'error')
        self.assertEqual(payload['model'], 'openai/gpt-5.4-nano')
        self.assertFalse(payload['present'])
        self.assertEqual(payload['tones_count'], 0)
        self.assertEqual(payload['tones'], [])
        self.assertEqual(payload['decision_source'], 'fail_open')
        self.assertEqual(payload['reason_code'], 'invalid_json')
        self.assertNotIn('user_msg', payload)
        self.assertNotIn('prompt', payload)
        self.assertNotIn('raw_output', payload)


class ChatInstrumentationPhase2Tests(unittest.TestCase):
    def test_embedding_events_include_source_kind_for_query_trace_and_summary(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event
        original_runtime_embedding_value = memory_store._runtime_embedding_value
        original_runtime_embedding_token = memory_store._runtime_embedding_token
        original_embed_impl = memory_store.memory_store_infra.embed
        original_trace_exists = memory_traces_summaries._trace_exists_for_message

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, _params: tuple[Any, ...]) -> None:
                return None

            def fetchall(self) -> list[tuple[Any, ...]]:
                return []

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

            def commit(self) -> None:
                return None

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        def fake_runtime_embedding_value(field: str) -> Any:
            if field == 'endpoint':
                return 'https://embed.example/v1'
            if field == 'dimensions':
                return 1536
            return None

        log_store.insert_chat_log_event = fake_insert
        memory_store._runtime_embedding_value = fake_runtime_embedding_value
        memory_store._runtime_embedding_token = lambda: 'token-test'
        memory_store.memory_store_infra.embed = lambda *_args, **_kwargs: [0.1, 0.2, 0.3]
        memory_traces_summaries._trace_exists_for_message = lambda *_args, **_kwargs: False

        token = chat_turn_logger.begin_turn(
            conversation_id='conv-embedding-kinds',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            memory_traces_summaries.save_new_traces(
                {
                    'id': 'conv-embedding-kinds',
                    'messages': [
                        {'role': 'user', 'content': 'hello user', 'timestamp': '2026-03-28T10:00:00Z'},
                        {'role': 'assistant', 'content': 'hello assistant', 'timestamp': '2026-03-28T10:00:01Z'},
                    ],
                },
                conn_factory=lambda: FakeConn(),
                embed_fn=memory_store.embed,
                logger=SimpleNamespace(info=lambda *_a, **_k: None, warning=lambda *_a, **_k: None, error=lambda *_a, **_k: None),
            )
            memory_traces_summaries.retrieve(
                'search memory',
                top_k=1,
                runtime_embedding_value_fn=lambda _field: 1,
                conn_factory=lambda: FakeConn(),
                embed_fn=memory_store.embed,
                logger=SimpleNamespace(warning=lambda *_a, **_k: None, error=lambda *_a, **_k: None),
            )
            memory_traces_summaries.save_summary(
                'conv-embedding-kinds',
                {
                    'id': 'summary-1',
                    'content': 'summary content',
                    'start_ts': '2026-03-28T10:00:00Z',
                    'end_ts': '2026-03-28T10:05:00Z',
                },
                conn_factory=lambda: FakeConn(),
                embed_fn=memory_store.embed,
                logger=SimpleNamespace(info=lambda *_a, **_k: None, warning=lambda *_a, **_k: None, error=lambda *_a, **_k: None),
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert
            memory_store._runtime_embedding_value = original_runtime_embedding_value
            memory_store._runtime_embedding_token = original_runtime_embedding_token
            memory_store.memory_store_infra.embed = original_embed_impl
            memory_traces_summaries._trace_exists_for_message = original_trace_exists

        embedding_events = [event for event in observed if event['stage'] == 'embedding' and event['status'] == 'ok']
        source_kinds = [event['payload_json'].get('source_kind') for event in embedding_events]
        self.assertCountEqual(
            source_kinds,
            ['trace_user', 'trace_assistant', 'query', 'summary'],
        )
        for event in embedding_events:
            payload = event['payload_json']
            self.assertIn(payload.get('source_kind'), {'query', 'trace_user', 'trace_assistant', 'summary'})
            self.assertIn('mode', payload)
            self.assertIn('provider', payload)
            self.assertIn('dimensions', payload)
            self.assertNotIn('text', payload)
            self.assertNotIn('content', payload)
            self.assertNotIn('vector', payload)

    def test_get_identities_emits_identities_read_with_frida_side(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, _params: tuple[Any, ...]) -> None:
                return None

            def fetchall(self) -> list[tuple[Any, ...]]:
                return [
                    (
                        '11111111-1111-1111-1111-111111111111',
                        'llm',
                        'Frida style identity',
                        1.0,
                        None,
                        None,
                        None,
                        'durable',
                        'self_description',
                        'repeated',
                        'llm',
                        'strong',
                        0.9,
                        'accepted',
                        'frida style identity',
                        'policy:accepted',
                        'conv-a',
                        'none',
                        None,
                        None,
                        None,
                    )
                ]

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-identities',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            rows = memory_context_read.get_identities(
                'llm',
                top_n=5,
                status='accepted',
                conn_factory=lambda: FakeConn(),
                default_top_n=5,
                logger=SimpleNamespace(error=lambda *_a, **_k: None),
            )
            self.assertEqual(len(rows), 1)
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        identities_events = [event for event in observed if event['stage'] == 'identities_read']
        self.assertTrue(identities_events)
        payload = identities_events[0]['payload_json']
        self.assertEqual(payload['target_side'], 'frida')
        self.assertEqual(payload['source_kind'], 'durable')
        self.assertEqual(payload['frida_count'], 1)
        self.assertEqual(payload['user_count'], 0)

    def test_build_identity_block_emits_identities_read_for_static_sources(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event
        original_load_llm_identity = identity.load_llm_identity
        original_load_user_identity = identity.load_user_identity
        original_estimate_tokens = identity._estimate_tokens
        original_build_dynamic_lines = identity._build_dynamic_lines

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        identity.load_llm_identity = lambda: 'Frida static identity'
        identity.load_user_identity = lambda: 'User static identity'
        identity._estimate_tokens = lambda _text: 1
        identity._build_dynamic_lines = lambda _subject, _max_tokens: ([], [])
        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-static-identities',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            block, used_ids = identity.build_identity_block()
            self.assertIn('DU MOD', block)
            self.assertIn("L'UTILISATEUR", block)
            self.assertEqual(used_ids, [])
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert
            identity.load_llm_identity = original_load_llm_identity
            identity.load_user_identity = original_load_user_identity
            identity._estimate_tokens = original_estimate_tokens
            identity._build_dynamic_lines = original_build_dynamic_lines

        identities_events = [event for event in observed if event['stage'] == 'identities_read']
        static_events = [event for event in identities_events if event['payload_json'].get('source_kind') == 'static']
        self.assertEqual(len(static_events), 2)
        sides = {event['payload_json'].get('target_side') for event in static_events}
        self.assertSetEqual(sides, {'frida', 'user'})
        for event in static_events:
            payload = event['payload_json']
            self.assertEqual(payload['selected_count'], 1)
            self.assertEqual(len(payload.get('preview', [])), 1)
            self.assertLessEqual(len(payload.get('preview', [''])[0]), 120)

    def test_persist_identity_entries_emits_identity_write_for_both_sides(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-write',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            memory_identity_dynamics.persist_identity_entries(
                'conv-write',
                entries=[],
                source_trace_id='trace-1',
                preview_identity_entries_fn=lambda _entries: [
                    {
                        'subject': 'llm',
                        'content': 'Frida keeps this ' + ('x' * 220),
                        'status': 'accepted',
                        'stability': 'durable',
                        'utterance_mode': 'self_description',
                        'recurrence': 'repeated',
                        'scope': 'llm',
                        'evidence_kind': 'strong',
                        'confidence': 0.9,
                        'reason': 'policy:accepted',
                    },
                    {
                        'subject': 'user',
                        'content': 'User preference ' + ('y' * 220),
                        'status': 'deferred',
                        'stability': 'episodic',
                        'utterance_mode': 'self_description',
                        'recurrence': 'repeated',
                        'scope': 'user',
                        'evidence_kind': 'weak',
                        'confidence': 0.7,
                        'reason': 'policy:defer',
                    },
                    {
                        'subject': 'user',
                        'content': 'Rejected noise ' + ('z' * 220),
                        'status': 'rejected',
                        'stability': 'unknown',
                        'utterance_mode': 'irony',
                        'recurrence': 'single',
                        'scope': 'user',
                        'evidence_kind': 'weak',
                        'confidence': 0.2,
                        'reason': 'policy:reject',
                    },
                    {
                        'subject': 'user',
                        'content': 'Another retained user identity ' + ('k' * 220),
                        'status': 'accepted',
                        'stability': 'durable',
                        'utterance_mode': 'self_description',
                        'recurrence': 'repeated',
                        'scope': 'user',
                        'evidence_kind': 'strong',
                        'confidence': 0.85,
                        'reason': 'policy:accepted',
                    },
                ],
                record_identity_evidence_fn=lambda *_args, **_kwargs: None,
                add_identity_fn=lambda *_args, **_kwargs: 'identity-id',
                detect_and_record_conflicts_fn=lambda *_args, **_kwargs: None,
                normalize_identity_content_fn=lambda text: text.strip().lower(),
                apply_defer_policy_for_content_fn=lambda *_args, **_kwargs: None,
                expire_stale_deferred_global_fn=lambda: None,
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        identity_write_events = [event for event in observed if event['stage'] == 'identity_write']
        self.assertEqual({event['payload_json']['target_side'] for event in identity_write_events}, {'frida', 'user'})
        user_payload = next(event['payload_json'] for event in identity_write_events if event['payload_json']['target_side'] == 'user')
        self.assertTrue(user_payload['truncated'])
        self.assertEqual(user_payload.get('persisted_count'), 3)
        self.assertEqual(user_payload.get('retained_count'), 2)
        for event in identity_write_events:
            payload = event['payload_json']
            self.assertEqual(payload.get('write_mode'), 'durable')
            self.assertEqual(payload.get('write_effect'), 'durable_write')
            self.assertGreaterEqual(int(payload.get('persisted_count') or 0), int(payload.get('retained_count') or 0))
            self.assertIn('evidence_count', payload)
            self.assertIn('preview_count', payload)
            self.assertIn('actions_count', payload)
            self.assertIn('retained_count', payload)
            self.assertSetEqual(set(payload['actions_count'].keys()), {'add', 'update', 'override', 'reject', 'defer'})
            self.assertLessEqual(len(payload.get('preview', [])), 3)
            self.assertTrue(all(len(item) <= 120 for item in payload.get('preview', [])))
            self.assertNotIn('entries', payload)
            self.assertNotIn('raw_identities', payload)

    def test_persist_identity_entries_emits_per_side_visibility_when_one_side_has_no_data(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-write-single-side',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            memory_identity_dynamics.persist_identity_entries(
                'conv-write-single-side',
                entries=[],
                source_trace_id='trace-1',
                preview_identity_entries_fn=lambda _entries: [
                    {
                        'subject': 'llm',
                        'content': 'Frida durable identity',
                        'status': 'accepted',
                        'stability': 'durable',
                        'utterance_mode': 'self_description',
                        'recurrence': 'repeated',
                        'scope': 'llm',
                        'evidence_kind': 'strong',
                        'confidence': 0.95,
                        'reason': 'policy:accepted',
                    }
                ],
                record_identity_evidence_fn=lambda *_args, **_kwargs: None,
                add_identity_fn=lambda *_args, **_kwargs: 'identity-id',
                detect_and_record_conflicts_fn=lambda *_args, **_kwargs: None,
                normalize_identity_content_fn=lambda text: text.strip().lower(),
                apply_defer_policy_for_content_fn=lambda *_args, **_kwargs: None,
                expire_stale_deferred_global_fn=lambda: None,
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        identity_write_events = [event for event in observed if event['stage'] == 'identity_write']
        self.assertEqual(len(identity_write_events), 2)
        by_side = {event['payload_json']['target_side']: event for event in identity_write_events}
        self.assertSetEqual(set(by_side.keys()), {'frida', 'user'})

        frida_event = by_side['frida']
        self.assertEqual(frida_event['status'], 'ok')
        self.assertEqual(frida_event['payload_json']['write_mode'], 'durable')
        self.assertEqual(frida_event['payload_json']['write_effect'], 'durable_write')
        self.assertEqual(frida_event['payload_json']['persisted_count'], 1)
        self.assertEqual(frida_event['payload_json']['evidence_count'], 1)
        self.assertEqual(frida_event['payload_json']['retained_count'], 1)

        user_event = by_side['user']
        self.assertEqual(user_event['status'], 'skipped')
        self.assertEqual(user_event['payload_json']['reason_code'], 'no_data')
        self.assertEqual(user_event['payload_json']['write_mode'], 'durable')
        self.assertEqual(user_event['payload_json']['write_effect'], 'none')
        self.assertEqual(user_event['payload_json']['persisted_count'], 0)
        self.assertEqual(user_event['payload_json']['evidence_count'], 0)
        self.assertEqual(user_event['payload_json']['preview_count'], 0)
        self.assertEqual(user_event['payload_json']['retained_count'], 0)
        self.assertEqual(user_event['payload_json']['preview'], [])

        for event in identity_write_events:
            payload = event['payload_json']
            self.assertNotIn('entries', payload)
            self.assertNotIn('raw_identities', payload)

    def test_persist_identity_entries_tracks_persisted_count_for_rejected_entries(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-write-rejected-only',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            memory_identity_dynamics.persist_identity_entries(
                'conv-write-rejected-only',
                entries=[],
                source_trace_id='trace-rj',
                preview_identity_entries_fn=lambda _entries: [
                    {
                        'subject': 'llm',
                        'content': 'Rejected Frida identity',
                        'status': 'rejected',
                        'stability': 'unknown',
                        'utterance_mode': 'irony',
                        'recurrence': 'single',
                        'scope': 'llm',
                        'evidence_kind': 'weak',
                        'confidence': 0.2,
                        'reason': 'policy:reject',
                    }
                ],
                record_identity_evidence_fn=lambda *_args, **_kwargs: None,
                add_identity_fn=lambda *_args, **_kwargs: 'identity-rejected-id',
                detect_and_record_conflicts_fn=lambda *_args, **_kwargs: None,
                normalize_identity_content_fn=lambda text: text.strip().lower(),
                apply_defer_policy_for_content_fn=lambda *_args, **_kwargs: None,
                expire_stale_deferred_global_fn=lambda: None,
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        identity_write_events = [event for event in observed if event['stage'] == 'identity_write']
        by_side = {event['payload_json']['target_side']: event for event in identity_write_events}
        self.assertSetEqual(set(by_side.keys()), {'frida', 'user'})

        frida_payload = by_side['frida']['payload_json']
        self.assertEqual(by_side['frida']['status'], 'ok')
        self.assertEqual(frida_payload.get('write_mode'), 'durable')
        self.assertEqual(frida_payload.get('write_effect'), 'durable_write')
        self.assertEqual(frida_payload.get('persisted_count'), 1)
        self.assertEqual(frida_payload.get('retained_count'), 0)
        self.assertEqual(frida_payload.get('actions_count', {}).get('reject'), 1)

        user_payload = by_side['user']['payload_json']
        self.assertEqual(by_side['user']['status'], 'skipped')
        self.assertEqual(user_payload.get('persisted_count'), 0)
        self.assertEqual(user_payload.get('retained_count'), 0)

    def test_get_recent_context_hints_emits_identities_read_for_user_side(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, _params: tuple[Any, ...]) -> None:
                return None

            def fetchall(self) -> list[tuple[Any, ...]]:
                now = datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)
                return [
                    ('conv-u1', 'User context hint alpha ' + ('a' * 200), 'norm-alpha', now, 0.9, 'user', 'episodic', 'self_description', 1.2),
                    ('conv-u2', 'User context hint beta ' + ('b' * 200), 'norm-beta', now, 0.8, 'user', 'episodic', 'self_description', 1.1),
                ]

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-hints',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            hints = memory_context_read.get_recent_context_hints(
                max_items=2,
                max_age_days=7,
                min_confidence=0.6,
                conn_factory=lambda: FakeConn(),
                default_max_items=2,
                default_max_age_days=7,
                default_min_confidence=0.6,
                logger=SimpleNamespace(error=lambda *_a, **_k: None),
            )
            self.assertEqual(len(hints), 2)
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        identities_events = [event for event in observed if event['stage'] == 'identities_read']
        self.assertTrue(identities_events)
        payload = identities_events[0]['payload_json']
        self.assertEqual(payload['target_side'], 'user')
        self.assertEqual(payload['source_kind'], 'context_hint')
        self.assertEqual(payload['frida_count'], 0)
        self.assertEqual(payload['user_count'], 2)
        self.assertEqual(payload['selected_count'], 2)
        self.assertLessEqual(len(payload['keys']), 3)
        self.assertLessEqual(len(payload['preview']), 3)
        self.assertTrue(all(len(item) <= 64 for item in payload['keys']))
        self.assertTrue(all(len(item) <= 120 for item in payload['preview']))
        self.assertNotIn('content', payload)
        self.assertNotIn('raw_identities', payload)

    def test_record_arbiter_decisions_emits_compact_arbiter_reasons_and_fallback(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, _params: tuple[Any, ...]) -> None:
                return None

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

            def commit(self) -> None:
                return None

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-arbiter-logs',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            memory_arbiter_audit.record_arbiter_decisions(
                'conv-arbiter-logs',
                traces=[
                    {'role': 'assistant', 'content': 'trace kept', 'timestamp': '2026-03-27T10:00:00Z', 'score': 0.9},
                    {'role': 'assistant', 'content': 'trace rejected 1', 'timestamp': '2026-03-27T10:01:00Z', 'score': 0.4},
                    {'role': 'assistant', 'content': 'trace rejected 2', 'timestamp': '2026-03-27T10:02:00Z', 'score': 0.3},
                ],
                decisions=[
                    {
                        'candidate_id': '0',
                        'keep': True,
                        'semantic_relevance': 0.92,
                        'contextual_gain': 0.88,
                        'redundant_with_recent': False,
                        'reason': 'kept',
                        'decision_source': 'llm',
                        'model': 'openrouter/arbiter-v1',
                    },
                    {
                        'candidate_id': '1',
                        'keep': False,
                        'semantic_relevance': 0.40,
                        'contextual_gain': 0.20,
                        'redundant_with_recent': False,
                        'reason': 'below_contextual_gain_threshold | lexical_near_duplicate_low_context_gain(sim=0.84)',
                        'decision_source': 'llm',
                        'model': 'openrouter/arbiter-v1',
                    },
                    {
                        'candidate_id': '2',
                        'keep': False,
                        'semantic_relevance': 0.20,
                        'contextual_gain': 0.10,
                        'redundant_with_recent': False,
                        'reason': 'fallback:parse_or_runtime_error',
                        'decision_source': 'fallback',
                        'model': 'openrouter/arbiter-v1',
                    },
                ],
                effective_model='openrouter/arbiter-v1',
                mode='shadow',
                conn_factory=lambda: FakeConn(),
                trace_float_fn=lambda value: float(value or 0.0),
                logger=SimpleNamespace(error=lambda *_a, **_k: None, info=lambda *_a, **_k: None),
            )
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert

        arbiter_events = [event for event in observed if event['stage'] == 'arbiter']
        self.assertEqual(len(arbiter_events), 1)
        payload = arbiter_events[0]['payload_json']
        self.assertEqual(payload['raw_candidates'], 3)
        self.assertEqual(payload['kept_candidates'], 1)
        self.assertEqual(payload['rejected_candidates'], 2)
        self.assertEqual(payload['mode'], 'shadow')
        self.assertEqual(payload['model'], 'openrouter/arbiter-v1')
        self.assertEqual(payload['decision_source'], 'mixed')
        self.assertTrue(payload['fallback_used'])
        self.assertEqual(payload['fallback_decisions'], 1)
        self.assertEqual(payload['rejection_reason_counts']['below_contextual_gain_threshold'], 1)
        self.assertEqual(payload['rejection_reason_counts']['fallback:parse_or_runtime_error'], 1)
        self.assertNotIn('candidate_content', payload)
        self.assertNotIn('candidates', payload)

    def test_record_arbiter_decisions_keeps_true_counts_when_persistence_fails(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event

        class FailingCursor:
            def __enter__(self) -> 'FailingCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, _params: tuple[Any, ...]) -> None:
                raise RuntimeError('db insert failed')

        class FailingConn:
            def __enter__(self) -> 'FailingConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FailingCursor:
                return FailingCursor()

            def commit(self) -> None:
                return None

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-arbiter-db-fail',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            memory_arbiter_audit.record_arbiter_decisions(
                'conv-arbiter-db-fail',
                traces=[
                    {'role': 'assistant', 'content': 'trace kept', 'timestamp': '2026-03-27T10:00:00Z', 'score': 0.9},
                    {'role': 'assistant', 'content': 'trace rejected 1', 'timestamp': '2026-03-27T10:01:00Z', 'score': 0.4},
                    {'role': 'assistant', 'content': 'trace rejected 2', 'timestamp': '2026-03-27T10:02:00Z', 'score': 0.3},
                ],
                decisions=[
                    {
                        'candidate_id': '0',
                        'keep': True,
                        'semantic_relevance': 0.92,
                        'contextual_gain': 0.88,
                        'redundant_with_recent': False,
                        'reason': 'kept',
                        'decision_source': 'llm',
                        'model': 'openrouter/arbiter-v1',
                    },
                    {
                        'candidate_id': '1',
                        'keep': False,
                        'semantic_relevance': 0.40,
                        'contextual_gain': 0.20,
                        'redundant_with_recent': False,
                        'reason': 'below_contextual_gain_threshold',
                        'decision_source': 'llm',
                        'model': 'openrouter/arbiter-v1',
                    },
                    {
                        'candidate_id': '2',
                        'keep': False,
                        'semantic_relevance': 0.20,
                        'contextual_gain': 0.10,
                        'redundant_with_recent': False,
                        'reason': 'fallback:parse_or_runtime_error',
                        'decision_source': 'fallback',
                        'model': 'openrouter/arbiter-v1',
                    },
                ],
                effective_model='openrouter/arbiter-v1',
                mode='shadow',
                conn_factory=lambda: FailingConn(),
                trace_float_fn=lambda value: float(value or 0.0),
                logger=SimpleNamespace(error=lambda *_a, **_k: None, info=lambda *_a, **_k: None),
            )
            chat_turn_logger.end_turn(token, final_status='error')
        finally:
            log_store.insert_chat_log_event = original_insert

        arbiter_events = [event for event in observed if event['stage'] == 'arbiter']
        self.assertEqual(len(arbiter_events), 1)
        self.assertEqual(arbiter_events[0]['status'], 'error')
        payload = arbiter_events[0]['payload_json']
        self.assertEqual(payload['raw_candidates'], 3)
        self.assertEqual(payload['kept_candidates'], 1)
        self.assertEqual(payload['rejected_candidates'], 2)
        self.assertEqual(payload['decision_source'], 'mixed')
        self.assertTrue(payload['fallback_used'])
        self.assertEqual(payload['fallback_decisions'], 1)
        self.assertEqual(payload['rejection_reason_counts']['below_contextual_gain_threshold'], 1)
        self.assertEqual(payload['rejection_reason_counts']['fallback:parse_or_runtime_error'], 1)
        self.assertEqual(payload['error_class'], 'RuntimeError')

    def test_web_search_build_context_emits_ok_and_skipped(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_format_context = web_search._format_context

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        try:
            token_ok = chat_turn_logger.begin_turn(
                conversation_id='conv-web-ok',
                user_msg='bonjour',
                web_search_enabled=True,
            )
            web_search.reformulate = lambda _msg: 'query ok'
            web_search.search = lambda _query: [{'title': 'A', 'url': 'https://a', 'content': 'x'}]
            web_search._format_context = lambda _query, _results: 'CTX OK'
            try:
                ctx, query, count = web_search.build_context('bonjour')
                self.assertEqual((ctx, query, count), ('CTX OK', 'query ok', 1))
                chat_turn_logger.end_turn(token_ok, final_status='ok')
            finally:
                web_search.reformulate = original_reformulate
                web_search.search = original_search
                web_search._format_context = original_format_context

            token_skip = chat_turn_logger.begin_turn(
                conversation_id='conv-web-skip',
                user_msg='bonjour',
                web_search_enabled=True,
            )
            web_search.reformulate = lambda _msg: 'query none'
            web_search.search = lambda _query: []
            web_search._format_context = lambda _query, _results: ''
            try:
                ctx, query, count = web_search.build_context('bonjour')
                self.assertEqual((ctx, query, count), ('', 'query none', 0))
                chat_turn_logger.end_turn(token_skip, final_status='ok')
            finally:
                web_search.reformulate = original_reformulate
                web_search.search = original_search
                web_search._format_context = original_format_context

            token_truncated = chat_turn_logger.begin_turn(
                conversation_id='conv-web-truncated',
                user_msg='bonjour',
                web_search_enabled=True,
            )
            web_search.reformulate = lambda _msg: 'query truncated'
            web_search.search = lambda _query: [{'title': 'A', 'url': 'https://a', 'content': 'x'}]
            web_search._format_context = lambda _query, _results: 'CTX [...contenu tronqué]'
            try:
                ctx, query, count = web_search.build_context('bonjour')
                self.assertEqual((ctx, query, count), ('CTX [...contenu tronqué]', 'query truncated', 1))
                chat_turn_logger.end_turn(token_truncated, final_status='ok')
            finally:
                web_search.reformulate = original_reformulate
                web_search.search = original_search
                web_search._format_context = original_format_context
        finally:
            log_store.insert_chat_log_event = original_insert

        web_search_events = [event for event in observed if event['stage'] == 'web_search']
        self.assertGreaterEqual(len(web_search_events), 3)
        statuses = {event['status'] for event in web_search_events}
        self.assertIn('ok', statuses)
        self.assertIn('skipped', statuses)
        for event in web_search_events:
            payload = event['payload_json']
            self.assertEqual(payload.get('prompt_kind'), 'chat_web_reformulation')
            self.assertIn('enabled', payload)
            self.assertIn('query_preview', payload)
            self.assertIn('results_count', payload)
            self.assertIn('context_injected', payload)
            self.assertIn('truncated', payload)
            self.assertLessEqual(len(str(payload.get('query_preview') or '')), 120)
            self.assertNotIn('context', payload)
            self.assertNotIn('results', payload)

        skipped_events = [event for event in web_search_events if event['status'] == 'skipped']
        self.assertTrue(skipped_events)
        self.assertTrue(all(event['payload_json'].get('reason_code') == 'no_data' for event in skipped_events))
        truncated_event = next(
            event for event in web_search_events
            if event['payload_json'].get('query_preview') == 'query truncated'
        )
        self.assertTrue(truncated_event['payload_json']['truncated'])

    def test_web_search_build_context_payload_exposes_structured_sources(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_crawl_with_status = web_search.crawl_with_status
        original_runtime_services_value = web_search._runtime_services_value

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        web_search.reformulate = lambda _msg: 'query structuree'
        web_search.search = lambda _query: [
            {'title': 'Source A', 'url': 'https://a.example/article', 'content': 'snippet a'},
            {'title': 'Source B', 'url': 'https://b.example/article', 'content': 'snippet b' * 200},
        ]
        web_search.crawl_with_status = (
            lambda url: {'status': 'success', 'markdown': 'markdown a', 'error_class': None}
            if 'a.example' in url
            else {'status': 'empty', 'markdown': '', 'error_class': None}
        )
        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 1,
            'crawl4ai_max_chars': 20,
        }[field]
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-web-structured',
            user_msg='bonjour',
            web_search_enabled=True,
        )
        try:
            payload = web_search.build_context_payload('bonjour')
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search.crawl_with_status = original_crawl_with_status
            web_search._runtime_services_value = original_runtime_services_value

        self.assertTrue(payload['enabled'])
        self.assertEqual(payload['status'], 'ok')
        self.assertEqual(payload['query'], 'query structuree')
        self.assertEqual(payload['results_count'], 2)
        self.assertFalse(payload['explicit_url_detected'])
        self.assertIsNone(payload['read_state'])
        self.assertEqual(payload['primary_source_kind'], 'search')
        self.assertFalse(payload['primary_read_attempted'])
        self.assertEqual(payload['primary_read_status'], 'not_attempted')
        self.assertFalse(payload['fallback_used'])
        self.assertEqual(payload['collection_path'], 'search_only')
        self.assertEqual(payload['runtime']['searxng_results'], 5)
        self.assertEqual(payload['runtime']['crawl4ai_top_n'], 1)
        self.assertEqual(payload['runtime']['crawl4ai_max_chars'], 20)
        self.assertEqual(payload['sources'][0]['rank'], 1)
        self.assertEqual(payload['sources'][0]['source_domain'], 'a.example')
        self.assertEqual(payload['sources'][0]['used_content_kind'], 'crawl_markdown')
        self.assertTrue(payload['sources'][0]['used_in_prompt'])
        self.assertEqual(payload['sources'][0]['crawl_status'], 'success')
        self.assertEqual(payload['sources'][1]['used_content_kind'], 'search_snippet')
        self.assertTrue(payload['sources'][1]['truncated'])
        self.assertTrue(payload['context_block'].startswith('[RECHERCHE WEB'))

        web_event = next(event for event in observed if event['stage'] == 'web_search')
        self.assertEqual(web_event['status'], 'ok')
        self.assertEqual(web_event['payload_json']['results_count'], 2)
        self.assertTrue(web_event['payload_json']['truncated'])
        self.assertFalse(web_event['payload_json']['explicit_url_detected'])
        self.assertIsNone(web_event['payload_json']['read_state'])
        self.assertEqual(web_event['payload_json']['primary_read_status'], 'not_attempted')
        self.assertFalse(web_event['payload_json']['fallback_used'])
        self.assertEqual(web_event['payload_json']['collection_path'], 'search_only')

    def test_web_search_build_context_payload_logs_explicit_url_primary_path(self) -> None:
        observed: list[dict[str, Any]] = []
        explicit_url = 'https://example.com/article'
        original_insert = log_store.insert_chat_log_event
        original_crawl_with_status = web_search.crawl_with_status
        original_reformulate = web_search.reformulate
        original_search = web_search.search
        original_runtime_services_value = web_search._runtime_services_value

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        web_search.crawl_with_status = lambda url: {
            'status': 'success',
            'markdown': 'contenu primaire',
            'error_class': None,
        }
        web_search.reformulate = lambda _msg: (_ for _ in ()).throw(
            AssertionError('generic search should not run on explicit URL direct success')
        )
        web_search.search = lambda _query: (_ for _ in ()).throw(
            AssertionError('search should not run on explicit URL direct success')
        )
        web_search._runtime_services_value = lambda field: {
            'searxng_results': 5,
            'crawl4ai_top_n': 2,
            'crawl4ai_max_chars': 50,
        }[field]
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-web-explicit-url',
            user_msg='bonjour',
            web_search_enabled=True,
        )
        try:
            payload = web_search.build_context_payload(f'lis cette page: {explicit_url}')
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            log_store.insert_chat_log_event = original_insert
            web_search.crawl_with_status = original_crawl_with_status
            web_search.reformulate = original_reformulate
            web_search.search = original_search
            web_search._runtime_services_value = original_runtime_services_value

        self.assertTrue(payload['explicit_url_detected'])
        self.assertEqual(payload['read_state'], 'page_read')
        self.assertEqual(payload['primary_source_kind'], 'explicit_url')
        self.assertTrue(payload['primary_read_attempted'])
        self.assertEqual(payload['primary_read_status'], 'success')
        self.assertFalse(payload['fallback_used'])
        self.assertEqual(payload['collection_path'], 'explicit_url_direct')
        self.assertEqual(payload['sources'][0]['source_origin'], 'explicit_url')
        self.assertTrue(payload['sources'][0]['is_primary_source'])

        web_event = next(event for event in observed if event['stage'] == 'web_search')
        self.assertEqual(web_event['status'], 'ok')
        self.assertEqual(web_event['payload_json']['prompt_kind'], 'chat_web_explicit_url')
        self.assertTrue(web_event['payload_json']['explicit_url_detected'])
        self.assertEqual(web_event['payload_json']['explicit_url'], explicit_url)
        self.assertEqual(web_event['payload_json']['read_state'], 'page_read')
        self.assertEqual(web_event['payload_json']['primary_source_kind'], 'explicit_url')
        self.assertTrue(web_event['payload_json']['primary_read_attempted'])
        self.assertEqual(web_event['payload_json']['primary_read_status'], 'success')
        self.assertFalse(web_event['payload_json']['fallback_used'])
        self.assertEqual(web_event['payload_json']['collection_path'], 'explicit_url_direct')

    def test_web_search_build_context_emits_error_event(self) -> None:
        observed: list[dict[str, Any]] = []
        original_insert = log_store.insert_chat_log_event
        original_reformulate = web_search.reformulate

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed.append(event)
            return True

        log_store.insert_chat_log_event = fake_insert
        web_search.reformulate = lambda _msg: (_ for _ in ()).throw(RuntimeError('reformulation boom'))
        token = chat_turn_logger.begin_turn(
            conversation_id='conv-web-error',
            user_msg='message source',
            web_search_enabled=True,
        )
        try:
            context, query, count = web_search.build_context('message source')
            self.assertEqual((context, query, count), ('', 'message source', 0))
            chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            web_search.reformulate = original_reformulate
            log_store.insert_chat_log_event = original_insert

        error_event = next(event for event in observed if event['stage'] == 'web_search' and event['status'] == 'error')
        payload = error_event['payload_json']
        self.assertEqual(payload.get('prompt_kind'), 'chat_web_reformulation')
        self.assertTrue(payload.get('enabled'))
        self.assertEqual(payload.get('results_count'), 0)
        self.assertFalse(payload.get('context_injected'))
        self.assertIn('error_class', payload)
        self.assertEqual(payload.get('query_preview'), 'message source')
        self.assertNotIn('context', payload)
        self.assertNotIn('results', payload)
        logger_error_event = next(event for event in observed if event['stage'] == 'error' and event['status'] == 'error')
        self.assertEqual(logger_error_event['payload_json']['message_short'], 'reformulation boom')


if __name__ == '__main__':
    unittest.main()
