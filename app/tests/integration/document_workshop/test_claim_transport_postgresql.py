"""Real Flask/service/persistence authority on explicit isolated PostgreSQL.

Providers and unrelated Memory/settings lanes are synthetic. Every conversation
snapshot, claim and scope mutation here uses an independent SQL connection.
"""
import json
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import psycopg
from core import conv_store, conversation_turn_claims as claims
from core import document_workshop_contexts as contexts
from core import document_workshop_context_service as scope, chat_stream_control
from core.chat_llm_flow import AssistantResponseOverride
from tests.support.server_test_bootstrap import load_server_module_for_tests
from tests.support.server_chat_pipeline import patch_server_chat_pipeline

C = '11111111-1111-4111-8111-111111111111'
F = '22222222-2222-4222-8222-222222222222'
O = '33333333-3333-4333-8333-333333333333'
T = '44444444-4444-4444-8444-444444444444'


class SyntheticResponse:
    encoding = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def raise_for_status(self):
        pass

    def json(self):
        return {'choices': [{'message': {'content': 'Synthetic final'}}]}

    def iter_lines(self, **_):
        yield 'data: {"choices":[{"delta":{"content":"Synthetic final"}}]}'
        yield 'data: [DONE]'


@unittest.skipUnless(os.environ.get('M3_PROOF_PG_SOCKET'), 'isolated PostgreSQL proof required')
class ClaimTransportPostgresqlTests(unittest.TestCase):
    def conn(self):
        return psycopg.connect(host=os.environ['M3_PROOF_PG_SOCKET'], dbname='m1proof', user='m1proof')

    def setUp(self):
        self.server = load_server_module_for_tests()
        with self.conn() as conn:
            conn.execute('DROP SCHEMA public CASCADE; CREATE SCHEMA public')
            conn.execute('''
                CREATE TABLE workspace_folders(id uuid PRIMARY KEY, deleted_at timestamptz);
                CREATE TABLE workspace_folder_nextcloud_links(workspace_folder_id uuid PRIMARY KEY,
                    nextcloud_sync_state text, nextcloud_folder_ref text, nextcloud_name_hash text);
                CREATE TABLE conversations(id uuid PRIMARY KEY, title text, created_at timestamptz,
                    updated_at timestamptz, message_count integer, last_message_preview text,
                    workspace_folder_id uuid, deleted_at timestamptz);
                CREATE TABLE conversation_messages(conversation_id uuid REFERENCES conversations(id),
                    seq integer, role text, content text, timestamp timestamptz, summarized_by text,
                    embedded boolean, meta jsonb, PRIMARY KEY(conversation_id,seq));
                CREATE TABLE workspace_files(id uuid PRIMARY KEY, workspace_folder_id uuid, status text,
                    content_kind text, media_kind text, source_extension text, deleted_at timestamptz);
                CREATE TABLE workspace_file_nextcloud_links(workspace_file_id uuid PRIMARY KEY,
                    workspace_folder_id uuid, nextcloud_sync_state text, nextcloud_target_name text,
                    nextcloud_document_ref text, nextcloud_relative_path text, nextcloud_scope_key text,
                    nextcloud_file_id text, nextcloud_etag text);
            ''')
            conn.execute('INSERT INTO workspace_folders VALUES (%s,NULL),(%s,NULL)', (F, O))
            conn.execute("INSERT INTO workspace_folder_nextcloud_links VALUES (%s,'linked','folder-a','hash-a')", (F,))
        for store in (conv_store, contexts, claims):
            patcher = patch.object(store, '_db_conn', self.conn)
            patcher.start()
            self.addCleanup(patcher.stop)
        conversation = conv_store.new_conversation('BACKEND SYSTEM PROMPT', conversation_id=C)
        conversation['workspace_folder_id'] = F
        self.assertTrue(conv_store.save_conversation(conversation).ok)
        contexts.init_db()
        claims.init_db()

    @contextmanager
    def pipeline(self, provider, *, summary=False):
        real_load, real_save = conv_store.load_conversation, conv_store.save_conversation
        def dispatch(*args, **kwargs):
            # Constitutive validation exchanges remain in the real pipeline;
            # only the main exchange receives the test's gate/error/stream.
            if (kwargs.get('json') or {}).get('model') == 'openrouter/runtime-main-model':
                return provider(*args, **kwargs)
            return SyntheticResponse()
        observed, restore = patch_server_chat_pipeline(self.server,
            conversation=real_load(C, 'BACKEND SYSTEM PROMPT'), requests_post=dispatch,
            existing_conversation=True, disable_chat_log_storage=True,
            summarize_user_turn=summary, claim_store=claims)
        try:
            with patch.object(conv_store, 'normalize_conversation_id', lambda value: str(value)), \
                 patch.object(conv_store, 'load_conversation', real_load), \
                 patch.object(conv_store, 'save_conversation', real_save):
                yield observed
        finally:
            restore()

    def post(self, *, identity=T, stream=False, legacy=False, conversation=C, message='Synthetic request', **extra):
        body = dict(message=message, conversation_id=conversation, stream=stream, **extra)
        if not legacy:
            body['client_turn_id'] = identity
        with self.server.app.test_client() as client:
            return client.post('/api/chat', json=body, buffered=True)

    def claim(self):
        with self.conn() as conn:
            row = conn.execute('SELECT turn_id FROM conversation_turn_claims WHERE conversation_id=%s', (C,)).fetchone()
        return claims.read(str(row[0]))

    def assert_user_only(self):
        with self.conn() as conn:
            self.assertEqual(conn.execute("SELECT role FROM conversation_messages WHERE role<>'system' ORDER BY seq").fetchall(), [('user',)])

    def assert_no_open_transaction(self):
        with self.conn() as conn:
            conn.execute('SELECT id FROM conversations WHERE id=%s FOR UPDATE NOWAIT', (C,))
            self.assertEqual(conn.execute("SELECT count(*) FROM pg_stat_activity WHERE datname='m1proof' AND state='idle in transaction' AND clock_timestamp()-state_change>interval '100 milliseconds'").fetchone()[0], 0)

    def simultaneous(self, same, *, legacy=False):
        arrived, release = threading.Event(), threading.Event()
        calls = []

        def provider(*_, **__):
            calls.append(1)
            arrived.set()
            self.assertTrue(release.wait(10))
            return SyntheticResponse()

        with self.pipeline(provider), ThreadPoolExecutor(2) as pool:
            first = pool.submit(self.post, legacy=legacy)
            self.assertTrue(arrived.wait(10))
            self.assert_no_open_transaction()
            second = pool.submit(self.post, identity=T if same else O, legacy=legacy)
            try:
                response = second.result(timeout=2)
                self.assertEqual(response.status_code, 409)
                self.assertEqual(len(calls), 1)
            finally:
                release.set()
                first_response = first.result(timeout=10)
                second.result(timeout=10)
            self.assertEqual(first_response.status_code, 200)
            self.assertEqual(self.claim()['state'], 'succeeded')

    def test_same_turn_has_one_protected_start(self):
        self.simultaneous(True)

    def test_different_turn_same_conversation_has_one_protected_start(self):
        self.simultaneous(False)

    def test_legacy_requests_still_conflict_without_identity(self):
        self.simultaneous(False, legacy=True)

    def test_round_trip_does_not_restore_context_authority(self):
        record = contexts.create_context(conversation_id=C, workspace_folder_id=F)
        with self.conn() as conn:
            conn.execute('UPDATE conversations SET workspace_folder_id=%s WHERE id=%s', (O, C))
        with self.conn() as conn:
            conn.execute('UPDATE conversations SET workspace_folder_id=%s WHERE id=%s', (F, C))
        _, status = scope.get_context(record['id'], store=contexts, conversations=conv_store,
            folders=SimpleNamespace(get_workspace_folder=lambda _: dict(id=F)), files=None)
        self.assertEqual(status, 409)

    def test_repeat_success_and_incompatible_id_do_not_duplicate_or_call_provider(self):
        calls = []
        with self.pipeline(lambda *a, **k: calls.append(1) or SyntheticResponse()):
            first = self.post()
            repeat = self.post()
            changed = self.post(input_mode='voice')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()['text'], 'Synthetic final')
        self.assertEqual(repeat.status_code, 409)
        self.assertEqual(repeat.get_json()['turn']['state'], 'succeeded')
        self.assertEqual(changed.get_json()['reason_code'], 'conversation_turn_id_incompatible')
        self.assertEqual(len(calls), 1)
        with self.conn() as conn:
            self.assertEqual(conn.execute("SELECT role FROM conversation_messages WHERE role<>'system' ORDER BY seq").fetchall(), [('user',), ('assistant',)])
            meta = conn.execute("SELECT meta FROM conversation_messages WHERE role='user'").fetchone()[0]
            self.assertEqual(meta['client_turn_id'], T)
        self.assertNotIn('Synthetic', json.dumps(repeat.get_json()))

    def test_normal_against_internal_document_confirmation_conflicts(self):
        context = contexts.create_context(conversation_id=C, workspace_folder_id=F)
        admission = claims.acquire(conversation_id=C, turn_id=O, request_fingerprint='a'*64,
            kind='confirmation', context_id=context['id'])
        calls = []
        with self.pipeline(lambda *a, **k: calls.append(1) or SyntheticResponse()):
            response = self.post()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(calls, [])
        self.assertEqual(claims.read(O)['state'], 'active')
        claims.finish(admission.token, 'interrupted')

    def test_missing_claim_schema_refuses_before_provider_without_fallback(self):
        with self.conn() as conn:
            conn.execute('DROP TABLE conversation_turn_claims CASCADE')
        calls = []
        with self.pipeline(lambda *a, **k: calls.append(1) or SyntheticResponse()):
            for legacy in (False, True):
                response = self.post(legacy=legacy)
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.get_json()['reason_code'], 'conversation_claim_unavailable')
        self.assertEqual(calls, [])
        with self.conn() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM conversation_messages WHERE role='user'").fetchone()[0], 0)

    def refuse_inserts(self, role):
        with self.conn() as conn:
            conn.execute('''CREATE FUNCTION proof_refusal() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN IF NEW.role=TG_ARGV[0] THEN RAISE EXCEPTION 'synthetic write refusal'; END IF;
                RETURN NEW; END $$''')
            conn.execute("CREATE TRIGGER proof_refusal BEFORE INSERT ON conversation_messages FOR EACH ROW EXECUTE FUNCTION proof_refusal('"+role+"')")

    def test_initial_user_failure_makes_no_provider_call(self):
        self.refuse_inserts('user')
        calls = []
        with self.pipeline(lambda *a, **k: calls.append(1) or SyntheticResponse()):
            response = self.post()
            repeat = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(repeat.status_code, 409)
        self.assertEqual(calls, [])
        self.assertEqual(self.claim()['state'], 'interrupted')

    def test_final_write_failure_rolls_back_and_announces_no_success(self):
        self.refuse_inserts('assistant')
        with self.pipeline(lambda *a, **k: SyntheticResponse()):
            response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assert_user_only()
        self.assertEqual(self.claim()['state'], 'interrupted')
        self.assertIsNone(self.claim()['outcome'])

    def test_close_failure_never_becomes_json_success(self):
        with self.conn() as conn:
            conn.execute('''CREATE FUNCTION proof_refusal() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN IF NEW.state='succeeded' THEN RAISE EXCEPTION 'synthetic close refusal'; END IF;
                RETURN NEW; END $$;
                CREATE TRIGGER proof_refusal BEFORE UPDATE ON conversation_turn_claims
                    FOR EACH ROW EXECUTE FUNCTION proof_refusal()''')
        with self.pipeline(lambda *a, **k: SyntheticResponse()):
            response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.claim()['state'], 'active')
        self.assertEqual(self.claim()['outcome'], 'succeeded')
        self.assertEqual(response.get_json()['reason_code'], 'conversation_claim_unavailable')

    def test_provider_error_keeps_user_and_durable_interrupted_state(self):
        calls = []
        def fail(*a, **k):
            calls.append(1)
            raise self.server.requests.exceptions.RequestException('synthetic provider failure')
        with self.pipeline(fail):
            response = self.post()
            repeat = self.post()
        self.assertEqual(response.status_code, 502)
        self.assertEqual(repeat.status_code, 409)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.claim()['state'], 'interrupted')
        self.assert_user_only()

    def test_summary_snapshot_is_fenced_and_keeps_transcript(self):
        with self.pipeline(lambda *a, **k: SyntheticResponse(), summary=True):
            response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.claim()['state'], 'succeeded')
        with self.conn() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM conversation_messages WHERE role='user'").fetchone()[0], 1)

    def test_consumed_stream_closes_only_after_canonical_save_and_preserves_terminal(self):
        with self.pipeline(lambda *a, **k: SyntheticResponse()):
            response = self.post(stream=True)
        self.assertEqual(response.status_code, 200)
        text, terminal = chat_stream_control.split_text_and_terminal(response.get_data())
        self.assertEqual(text, 'Synthetic final')
        self.assertEqual(terminal['event'], 'done')
        self.assertEqual(self.claim()['state'], 'succeeded')
        self.assertEqual(response.get_data().count(chat_stream_control.STREAM_CONTROL_PREFIX.encode()), 1)

    def open_response(self):
        # Call the actual registered route inside a request context; unlike
        # test_client.post, this does not consume the first streaming chunk.
        return self.server.api_chat()

    def test_never_consumed_response_close_releases_without_provider_or_assistant(self):
        calls = []
        with self.pipeline(lambda *a, **k: calls.append(1) or SyntheticResponse()), \
             self.server.app.test_request_context('/api/chat', method='POST',
                 json=dict(message='Synthetic request', conversation_id=C, client_turn_id=T, stream=True)):
            response = self.open_response()
            self.assertEqual(calls, [])
            self.assertEqual(self.claim()['state'], 'active')
            response.close()
        self.assertEqual(self.claim()['state'], 'interrupted')
        self.assertEqual(calls, [])
        self.assert_user_only()

    def test_early_stream_close_and_repeat_do_not_canonize_fragment(self):
        calls = []
        with self.pipeline(lambda *a, **k: calls.append(1) or SyntheticResponse()), \
             self.server.app.test_request_context('/api/chat', method='POST',
                 json=dict(message='Synthetic request', conversation_id=C, client_turn_id=T, stream=True)):
            response = self.open_response()
            iterator = iter(response.response)
            self.assertEqual(next(iterator), 'Synthetic final')
            self.assertEqual(self.claim()['state'], 'active')
            response.close()
            repeat = self.post()
        self.assertEqual(repeat.status_code, 409)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.claim()['state'], 'interrupted')
        self.assert_user_only()

    def test_abandoned_stream_expiry_and_late_consumption_do_not_release_successor(self):
        calls = []
        with self.pipeline(lambda *a, **k: calls.append(1) or SyntheticResponse()), \
             self.server.app.test_request_context('/api/chat', method='POST',
                 json=dict(message='Synthetic request', conversation_id=C, client_turn_id=T, stream=True)):
            response = self.open_response()
            with self.conn() as conn:
                conn.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second'")
            successor = claims.acquire(conversation_id=C, turn_id=O, request_fingerprint='a'*64)
            text, terminal = chat_stream_control.split_text_and_terminal(response.get_data())
            response.close()
            self.assertEqual(text, '')
            self.assertEqual(terminal, {'event': 'error', 'error_code': 'conversation_persist_failed'})
            self.assertEqual(claims.read(T)['state'], 'lost')
            self.assertEqual(claims.read(O)['state'], 'active')
            self.assertEqual(calls, [])
            claims.finish(successor.token, 'interrupted')

    def test_stream_final_save_failure_has_one_error_terminal_no_updated_at(self):
        self.refuse_inserts('assistant')
        with self.pipeline(lambda *a, **k: SyntheticResponse()):
            response = self.post(stream=True)
        text, terminal = chat_stream_control.split_text_and_terminal(response.get_data())
        self.assertEqual(text, 'Synthetic final')
        self.assertEqual(terminal, {'event': 'error', 'error_code': 'conversation_persist_failed'})
        self.assertEqual(self.claim()['state'], 'interrupted')
        self.assert_user_only()

    def test_final_locks_share_authority_for_json_and_real_stream_consumption(self):
        original = self.server.chat_service.prepare_main_payload
        def locked(**kwargs):
            return replace(original(**kwargs), assistant_response_override=AssistantResponseOverride(
                content='...', source='synthetic_final_lock', meta={'final_lock': True}))
        calls = []
        with self.pipeline(lambda *a, **k: calls.append(1) or SyntheticResponse()), \
             patch.object(self.server.chat_service, 'prepare_main_payload', locked):
            first = self.post()
            second = self.post(identity=O, stream=True)
        self.assertEqual(first.get_json()['text'], '...')
        text, terminal = chat_stream_control.split_text_and_terminal(second.get_data())
        self.assertEqual(text, '...')
        self.assertEqual(terminal['event'], 'done')
        self.assertEqual(calls, [])
        self.assertEqual(claims.read(T)['state'], 'succeeded')
        self.assertEqual(claims.read(O)['state'], 'succeeded')

    def test_late_json_result_after_successor_has_no_commit_or_release(self):
        arrived, release = threading.Event(), threading.Event()
        def provider(*a, **k):
            arrived.set()
            self.assertTrue(release.wait(10))
            return SyntheticResponse()
        with self.pipeline(provider) as observed, ThreadPoolExecutor(1) as pool:
            future = pool.submit(self.post)
            self.assertTrue(arrived.wait(10))
            self.assert_no_open_transaction()
            with self.conn() as conn:
                conn.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second'")
            successor = claims.acquire(conversation_id=C, turn_id=O, request_fingerprint='a'*64)
            release.set()
            response = future.result(timeout=10)
            repeat = self.post()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()['reason_code'], 'conversation_claim_lost')
        self.assertEqual(repeat.get_json()['turn']['state'], 'lost')
        self.assertEqual(claims.read(O)['state'], 'active')
        self.assertEqual(observed['save_new_traces_calls'], [])
        self.assert_user_only()
        claims.finish(successor.token, 'interrupted')

    def test_late_stream_result_and_its_fallback_cannot_write_successor(self):
        arrived, release = threading.Event(), threading.Event()
        class BlockedStream(SyntheticResponse):
            def iter_lines(inner, **_):
                yield 'data: {"choices":[{"delta":{"content":"Synthetic fragment"}}]}'
                arrived.set()
                self.assertTrue(release.wait(10))
                raise self.server.requests.exceptions.RequestException('synthetic interruption')
        with self.pipeline(lambda *a, **k: BlockedStream()), ThreadPoolExecutor(1) as pool:
            future = pool.submit(self.post, stream=True)
            self.assertTrue(arrived.wait(10))
            self.assert_no_open_transaction()
            with self.conn() as conn:
                conn.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second'")
            successor = claims.acquire(conversation_id=C, turn_id=O, request_fingerprint='a'*64)
            release.set()
            response = future.result(timeout=10)
        text, terminal = chat_stream_control.split_text_and_terminal(response.get_data())
        self.assertEqual(text, 'Synthetic fragment')
        self.assertEqual(terminal, {'event': 'error', 'error_code': 'conversation_persist_failed'})
        self.assertEqual(claims.read(T)['state'], 'lost')
        self.assertEqual(claims.read(O)['state'], 'active')
        self.assert_user_only()
        claims.finish(successor.token, 'interrupted')

    def test_supervisor_renews_real_sql_lease_during_blocked_provider(self):
        arrived, renewed, release = threading.Event(), threading.Event(), threading.Event()
        original = claims.renew
        deadlines = []
        def renew(token):
            before = claims.read(token.turn_id)['lease_until']
            original(token)
            after = claims.read(token.turn_id)['lease_until']
            deadlines.append((before, after))
            renewed.set()
        def provider(*a, **k):
            arrived.set()
            self.assertTrue(release.wait(10))
            return SyntheticResponse()
        with patch.object(claims, 'RENEW_SECONDS', 0.02), patch.object(claims, 'renew', renew), \
             self.pipeline(provider), ThreadPoolExecutor(1) as pool:
            future = pool.submit(self.post)
            try:
                self.assertTrue(arrived.wait(10))
                self.assertTrue(renewed.wait(5))
                self.assertTrue(any(after > before for before, after in deadlines))
                self.assert_no_open_transaction()
                conflict = self.post(identity=O)
                self.assertEqual(conflict.status_code, 409)
            finally:
                release.set()
            response = future.result(timeout=10)
        self.assertEqual(response.status_code, 200)

    def test_summary_snapshot_failure_stops_before_main_exchange(self):
        # A real SQL trigger rejects the second user snapshot (the summary save),
        # but permits the initial user barrier. A transaction-local mock cannot
        # fake the committed initial count inspected by this trigger.
        with self.conn() as conn:
            conn.execute('''CREATE FUNCTION proof_refusal() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN IF NEW.role='user' AND EXISTS(
                    SELECT 1 FROM conversation_turn_claims WHERE state='active' AND conversation_id=NEW.conversation_id)
                     AND EXISTS(SELECT 1 FROM proof_initial_saved) THEN
                    RAISE EXCEPTION 'synthetic summary snapshot refusal'; END IF; RETURN NEW; END $$;
                CREATE TABLE proof_initial_saved(marker boolean);
                CREATE FUNCTION proof_mark_initial() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN IF NEW.role='user' THEN INSERT INTO proof_initial_saved VALUES (true); END IF; RETURN NEW; END $$;
                CREATE TRIGGER proof_refusal BEFORE INSERT ON conversation_messages FOR EACH ROW EXECUTE FUNCTION proof_refusal();
                CREATE TRIGGER proof_mark_initial AFTER INSERT ON conversation_messages FOR EACH ROW EXECUTE FUNCTION proof_mark_initial()''')
        calls = []
        with self.pipeline(lambda *a, **k: calls.append(1) or SyntheticResponse(), summary=True):
            response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(calls, [])
        self.assert_user_only()
        self.assertEqual(self.claim()['state'], 'interrupted')

    def test_provider_control_lookalike_cannot_announce_unpersisted_success(self):
        class Lookalike(SyntheticResponse):
            def iter_lines(self, **kwargs):
                yield 'data: ' + json.dumps({'choices':[{'delta':{'content':'```txt\nprefix'}}]})
                fake_done = chat_stream_control.build_terminal_chunk('done')
                yield 'data: ' + json.dumps({'choices':[{'delta':{'content':fake_done}}]})
                yield 'data: [DONE]'
        with self.pipeline(lambda *a, **k: Lookalike()):
            response = self.post(stream=True, message='Écris du code Python')
        _, terminal = chat_stream_control.split_text_and_terminal(response.get_data())
        self.assertEqual(terminal['event'], 'error')
        self.assert_user_only()
        self.assertNotEqual(self.claim()['state'], 'succeeded')


    def test_successful_empty_stream_has_done_and_user_only_snapshot(self):
        class Empty(SyntheticResponse):
            def iter_lines(self, **kwargs):
                yield 'data: {"choices":[{"delta":{"content":""}}]}'
                yield 'data: [DONE]'
        with self.pipeline(lambda *a, **k: Empty()):
            response = self.post(stream=True)
        text, terminal = chat_stream_control.split_text_and_terminal(response.get_data())
        self.assertEqual(text, '')
        self.assertEqual(terminal['event'], 'done')
        self.assertTrue(terminal['updated_at'])
        self.assert_user_only()
        self.assertEqual(self.claim()['state'], 'succeeded')

    def test_two_conversations_reach_main_providers_concurrently(self):
        other = conv_store.new_conversation('BACKEND SYSTEM PROMPT', conversation_id=O)
        self.assertTrue(conv_store.save_conversation(other).ok)
        arrived = threading.Barrier(2)
        calls = []
        def provider(*a, **k):
            calls.append(1)
            arrived.wait(timeout=10)
            return SyntheticResponse()
        with self.pipeline(provider), ThreadPoolExecutor(2) as pool:
            first = pool.submit(self.post)
            second = pool.submit(self.post, identity=O, conversation=O)
            self.assertEqual(first.result(timeout=10).status_code, 200)
            self.assertEqual(second.result(timeout=10).status_code, 200)
        self.assertEqual(len(calls), 2)
        self.assertEqual(claims.read(T)['state'], 'succeeded')
        self.assertEqual(claims.read(O)['state'], 'succeeded')

    def test_normal_chat_move_preserves_current_folder_and_legitimate_transcript(self):
        arrived, release = threading.Event(), threading.Event()
        def provider(*a, **k):
            arrived.set()
            self.assertTrue(release.wait(10))
            return SyntheticResponse()
        with self.pipeline(provider), ThreadPoolExecutor(1) as pool:
            future = pool.submit(self.post)
            self.assertTrue(arrived.wait(10))
            with self.conn() as conn:
                conn.execute('UPDATE conversations SET workspace_folder_id=%s WHERE id=%s', (O,C))
            release.set()
            self.assertEqual(future.result(timeout=10).status_code, 200)
        conversation = conv_store.load_conversation(C, 'BACKEND SYSTEM PROMPT')
        self.assertEqual(conversation['workspace_folder_id'], O)
        self.assertEqual([m['role'] for m in conversation['messages']], ['system','user','assistant'])

    def test_deleted_conversation_cannot_be_resurrected_by_late_result(self):
        arrived, release = threading.Event(), threading.Event()
        def provider(*a, **k):
            arrived.set()
            self.assertTrue(release.wait(10))
            return SyntheticResponse()
        with self.pipeline(provider), ThreadPoolExecutor(1) as pool:
            future = pool.submit(self.post)
            self.assertTrue(arrived.wait(10))
            with self.conn() as conn:
                conn.execute('UPDATE conversations SET deleted_at=clock_timestamp() WHERE id=%s', (C,))
            release.set()
            self.assertEqual(future.result(timeout=10).status_code, 409)
        self.assertEqual(claims.read(T)['state'], 'invalidated')
        self.assert_user_only()
        with self.conn() as conn:
            self.assertIsNotNone(conn.execute('SELECT deleted_at FROM conversations WHERE id=%s', (C,)).fetchone()[0])

    def test_json_success_requires_a_durable_canonical_outcome(self):
        # Fault at the existing exchange boundary: a nominal result without a
        # final snapshot must still fail the real SQL completion authority.
        false_result = dict(kind='json', status=200, payload={'text':'Synthetic unpersisted'}, headers={})
        with self.pipeline(lambda *a, **k: SyntheticResponse()), \
             patch.object(self.server.chat_service.chat_llm_flow, 'run_llm_exchange', return_value=false_result):
            response = self.post()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()['reason_code'], 'conversation_claim_outcome_invalid')
        self.assert_user_only()
        self.assertNotEqual(self.claim()['state'], 'succeeded')
