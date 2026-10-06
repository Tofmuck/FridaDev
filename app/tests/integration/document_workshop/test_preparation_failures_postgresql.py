"""M4 failure/concurrency proofs; SQL fixture reused without inherited tests."""
import asyncio
import json
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from unittest.mock import patch

import psycopg
from core import conversation_turn_claims as claims
from tests.integration.document_workshop import test_preparation_postgresql as fixture
from tests.support.server_test_bootstrap import load_server_module_for_tests

C, F, O, T = fixture.C, fixture.F, fixture.O, fixture.T
Provider = fixture.Provider


class LateProvider(Provider):
    """A cancelled synthetic result is deliberately produced after closure."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.late_returned = threading.Event()

    async def send(self, prepared):
        self.calls.append(prepared)
        self.arrived.set()
        while not self.release.is_set():
            try:
                await asyncio.sleep(.01)
            except asyncio.CancelledError:
                pass
        self.late_returned.set()
        return 200


@unittest.skipUnless(os.environ.get('M4_PROOF_PG_SOCKET'), 'isolated PostgreSQL proof required')
class PreparationFailuresPostgresqlTests(unittest.TestCase):
    def setUp(self):
        self.env = fixture.PreparationPostgresqlTests()
        self.addCleanup(self.env.doCleanups)
        self.env.setUp()
        self.actions = self.env.actions

    def rows(self, query, args=()):
        with self.env.conn() as independent:
            return independent.execute(query, args).fetchall()

    def count(self, table):
        self.assertIn(table, ('document_artifacts', 'document_revisions', 'document_actions', 'workspace_files'))
        return self.rows('SELECT count(*) FROM ' + table)[0][0]

    def action(self, turn=T):
        return self.actions.get_action(turn)

    def get(self, turn=T, *, server=None):
        with (server or self.env.server).app.test_client() as client:
            return client.get('/api/document-workshop/actions/' + turn)

    def cancel(self, turn=T, context=None):
        with self.env.server.app.test_client() as client:
            return client.post('/api/document-workshop/actions/' + turn + '/cancel',
                               json={'context_id': context or self.env.context['id']})

    def roles(self):
        return self.rows("SELECT role,content FROM conversation_messages WHERE role<>'system' ORDER BY seq")

    def assert_no_proposal(self):
        self.assertEqual(self.count('document_artifacts'), 0)
        self.assertEqual(self.count('document_revisions'), 0)
        self.assertEqual(self.count('workspace_files'), 0)
        self.assertEqual(self.rows("SELECT count(*) FROM document_actions WHERE state='pending'")[0][0], 0)
        self.assertEqual(self.rows("SELECT count(*) FROM conversation_turn_claims WHERE outcome='succeeded'")[0][0], 0)
        self.assertNotIn('Proposition préparée.', [content for _, content in self.roles()])
        self.env.assert_no_open_transaction()

    @contextmanager
    def fault(self, table, operation, condition='TRUE'):
        # Faults are actual PostgreSQL trigger exceptions inside the transaction
        # under proof; no store or transaction completion is simulated.
        with self.env.conn() as independent:
            independent.execute('CREATE SEQUENCE m4_proof_hits')
            independent.execute('''CREATE FUNCTION m4_proof_failure() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN IF ''' + condition + ''' THEN
                PERFORM nextval('m4_proof_hits');
                RAISE EXCEPTION 'synthetic M4 boundary refusal'; END IF;
                RETURN NEW; END $$''')
            independent.execute('CREATE TRIGGER m4_proof_failure BEFORE ' + operation + ' ON ' + table +
                                ' FOR EACH ROW EXECUTE FUNCTION m4_proof_failure()')
        try:
            yield
        finally:
            with self.env.conn() as independent:
                hits, called = independent.execute('SELECT last_value,is_called FROM m4_proof_hits').fetchone()
                independent.execute('DROP TRIGGER m4_proof_failure ON ' + table)
                independent.execute('DROP FUNCTION m4_proof_failure()')
                independent.execute('DROP SEQUENCE m4_proof_hits')
            # Sequences survive transaction rollback. This proves the intended
            # failing boundary was reached, rather than an unrelated rejection.
            self.assertTrue(called)
            self.assertEqual(hits, 1)

    def initial_failure(self, table, operation, condition='TRUE'):
        provider = Provider()
        with self.fault(table, operation, condition), self.env.pipeline(provider) as (normal, _):
            response = self.env.document()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(provider.calls, [])
        self.assertEqual(normal, [])
        self.assertEqual(self.roles(), [])
        self.assertEqual(self.count('document_actions'), 0)
        self.assert_no_proposal()
        self.assertEqual(claims.read(T)['state'], 'interrupted')

    def final_failure(self, table, operation, condition='TRUE'):
        provider = Provider()
        with self.fault(table, operation, condition), self.env.pipeline(provider) as (normal, _):
            response = self.env.document()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(normal, [])
        self.assertTrue(provider.closed.is_set())
        self.assert_no_proposal()
        action = self.action()
        self.assertEqual(action['state'], 'failed')
        self.assertIsNone(action['revision_id'])
        self.assertIsNone(action['artifact_id'])
        self.assertEqual([role for role, _ in self.roles()], ['user', 'assistant'])
        self.assertEqual(claims.read(T)['outcome'], 'interrupted')
        self.assertEqual(claims.read(T)['state'], 'failed')
        self.assertNotIn('synthetic M4 boundary refusal', str(response.get_json()))

    def test_initial_user_snapshot_failure_rolls_back_without_provider(self):
        self.initial_failure('conversation_messages', 'INSERT', "NEW.role='user'")

    def test_initial_action_insert_failure_rolls_back_user_snapshot_without_provider(self):
        self.initial_failure('document_actions', 'INSERT')

    def test_artifact_insert_failure_rolls_back_complete_final_transaction(self):
        self.final_failure('document_artifacts', 'INSERT')

    def test_revision_insert_failure_rolls_back_artifact_and_final_transaction(self):
        self.final_failure('document_revisions', 'INSERT')

    def test_assistant_snapshot_failure_rolls_back_revision_artifact_and_action(self):
        self.final_failure('conversation_messages', 'INSERT', "NEW.role='assistant' AND NEW.content='Proposition préparée.'")

    def test_pending_action_update_failure_rolls_back_final_snapshot_and_revision(self):
        self.final_failure('document_actions', 'UPDATE', "NEW.state='pending'")

    def test_canonical_outcome_failure_rolls_back_pending_and_final_snapshot(self):
        self.final_failure('conversation_turn_claims', 'UPDATE', "NEW.outcome='succeeded'")

    def test_claim_completion_failure_rolls_back_outcome_and_pending(self):
        self.final_failure('conversation_turn_claims', 'UPDATE', "NEW.state='succeeded'")

    def reject_canonical_surface(self, status, prefix=''):
        value = fixture.envelope(status)
        value['surface_text'] = prefix + json.dumps(fixture.canonical())
        provider = Provider(value)
        identity_calls = []
        with self.env.pipeline(provider) as (normal, observed), \
             patch.object(self.env.server.chat_service, '_record_identity_entries_for_mode',
                          lambda *a, **kw: identity_calls.append((a, kw))):
            response = self.env.document()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(normal, [])
        self.assertTrue(provider.closed.is_set())
        self.assert_no_proposal()
        self.assertEqual(self.roles(), [('user', 'Synthetic request'),
            ('assistant', 'La préparation a été interrompue. Aucun document n’a été écrit.')])
        self.assertEqual(observed['save_new_traces_calls'], [])
        self.assertEqual(identity_calls, [])
        self.assertNotIn('frida_document_v1', str(response.get_json()))
        self.assertEqual(self.action()['state'], 'failed')

    def test_prepared_raw_canonical_surface_never_reaches_transcript_or_faculty_sinks(self):
        self.reject_canonical_surface('prepared')

    def test_clarify_raw_canonical_surface_never_reaches_transcript_or_faculty_sinks(self):
        self.reject_canonical_surface('clarify')

    def test_prepared_prefixed_canonical_surface_never_reaches_transcript_or_faculty_sinks(self):
        self.reject_canonical_surface('prepared', prefix='Document : ')

    def test_clarify_prefixed_canonical_surface_never_reaches_transcript_or_faculty_sinks(self):
        self.reject_canonical_surface('clarify', prefix='Document : ')

    def test_completed_client_turn_repeat_and_incompatible_input_never_call_again(self):
        provider = Provider()
        with self.env.pipeline(provider) as (normal, _):
            initial = self.env.document()
            before = self.action()
            repeat = self.env.document(stream=True)
            incompatible = self.env.document(input_mode='voice')
        self.assertEqual(initial.status_code, 200)
        self.assertEqual(repeat.status_code, 409)
        self.assertEqual(repeat.get_json()['turn']['state'], 'succeeded')
        self.assertEqual(incompatible.status_code, 409)
        self.assertEqual(incompatible.get_json()['reason_code'], 'conversation_turn_id_incompatible')
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(normal, [])
        self.assertEqual(self.action(), before)
        self.assertEqual(self.count('document_actions'), 1)
        self.assertEqual([role for role, _ in self.roles()], ['user', 'assistant'])

    def test_blocked_document_conflicts_with_same_turn_and_normal_chat(self):
        provider = Provider(gate=True)
        with self.env.pipeline(provider) as (normal, _), ThreadPoolExecutor(1) as pool:
            pending = pool.submit(self.env.document)
            self.assertTrue(provider.arrived.wait(5))
            try:
                self.env.assert_no_open_transaction()
                repeat = self.env.document()
                incompatible = self.env.document(message='Different synthetic request')
                ordinary = self.env.post(identity=O)
                self.assertEqual(repeat.status_code, 409)
                self.assertEqual(incompatible.status_code, 409)
                self.assertEqual(incompatible.get_json()['reason_code'], 'conversation_turn_id_incompatible')
                self.assertEqual(ordinary.status_code, 409)
                self.assertEqual(ordinary.get_json()['reason_code'], 'conversation_turn_conflict')
                self.assertEqual(self.roles(), [('user', 'Synthetic request')])
                self.assertEqual(len(provider.calls), 1)
                self.assertEqual(normal, [])
            finally:
                provider.release.set()
                result = pending.result(timeout=10)
            self.assertEqual(result.status_code, 200)

    def test_blocked_normal_chat_excludes_document_before_document_provider(self):
        arrived, release = threading.Event(), threading.Event()
        normal_calls = []
        provider = Provider()
        def normal_provider(*args, **kwargs):
            normal_calls.append(1)
            arrived.set()
            self.assertTrue(release.wait(10))
            return fixture.fixture.SyntheticResponse()
        from core import document_workshop_turn
        with self.env.pipeline_base(normal_provider), patch.object(document_workshop_turn, 'DocumentHTTPTransport', lambda: provider), ThreadPoolExecutor(1) as pool:
            pending = pool.submit(self.env.post)
            self.assertTrue(arrived.wait(5))
            try:
                response = self.env.document(identity=O)
                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.get_json()['reason_code'], 'conversation_turn_conflict')
                self.assertEqual(provider.calls, [])
                self.assertEqual(normal_calls, [1])
                self.assertEqual(self.count('document_actions'), 0)
            finally:
                release.set()
                self.assertEqual(pending.result(timeout=10).status_code, 200)

    def test_cancel_during_blocked_provider_closes_transport_and_refuses_late_result(self):
        provider = LateProvider(gate=True)
        with self.env.pipeline(provider) as (normal, _), ThreadPoolExecutor(1) as pool:
            pending = pool.submit(self.env.document)
            self.assertTrue(provider.arrived.wait(5))
            try:
                response = self.cancel()
                self.assertEqual(response.status_code, 200, response.get_json())
                self.assertEqual(response.get_json()['action']['state'], 'cancelled')
                self.assertTrue(provider.closed.wait(5))
            finally:
                provider.release.set()
                result = pending.result(timeout=10)
            self.assertEqual(result.status_code, 503)
            self.assertEqual(normal, [])
            self.assertTrue(provider.late_returned.is_set())
            self.assertEqual(len(provider.calls), 1)
        self.assertEqual(self.action()['state'], 'cancelled')
        self.assertEqual(claims.read(T)['state'], 'cancelled')
        self.assertEqual(self.roles(), [('user', 'Synthetic request')])
        self.assert_no_proposal()

    def test_cancelled_client_turn_repeat_returns_terminal_identity_without_replay(self):
        provider = Provider(gate=True)
        with self.env.pipeline(provider) as (normal, _), ThreadPoolExecutor(1) as pool:
            pending = pool.submit(self.env.document)
            self.assertTrue(provider.arrived.wait(5))
            try:
                self.assertEqual(self.cancel().status_code, 200)
                self.assertTrue(provider.closed.wait(5))
            finally:
                provider.release.set()
                self.assertEqual(pending.result(timeout=10).status_code, 503)
            before = self.roles()
            action = self.action()
            repeat = self.env.document()
            self.assertEqual(repeat.status_code, 409)
            self.assertEqual(repeat.get_json()['reason_code'], 'conversation_turn_repeated')
            self.assertEqual(repeat.get_json()['turn']['state'], 'cancelled')
            self.assertEqual(self.roles(), before)
            self.assertEqual(self.action(), action)
            self.assertEqual(len(provider.calls), 1)
            self.assertEqual(normal, [])
        self.assert_no_proposal()

    def authority_loss(self, mutation, expected):
        provider = LateProvider(gate=True)
        with self.env.pipeline(provider) as (normal, _), ThreadPoolExecutor(1) as pool:
            pending = pool.submit(self.env.document)
            self.assertTrue(provider.arrived.wait(5))
            try:
                with self.env.conn() as independent:
                    mutation(independent)
                self.assertTrue(provider.closed.wait(5))
            finally:
                provider.release.set()
                response = pending.result(timeout=10)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(normal, [])
            self.assertTrue(provider.late_returned.is_set())
            self.assertEqual(len(provider.calls), 1)
        self.assertEqual(claims.read(T)['state'], expected)
        self.assertEqual(self.action()['state'], expected)
        self.assertEqual(self.roles(), [('user', 'Synthetic request')])
        self.assert_no_proposal()

    def test_expired_claim_lease_fences_late_document_result(self):
        self.authority_loss(lambda conn: conn.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second' WHERE turn_id=%s", (T,)), 'lost')

    def test_context_scope_round_trip_irreversibly_fences_late_document_result(self):
        def move(conn):
            conn.execute('UPDATE conversations SET workspace_folder_id=%s WHERE id=%s', (O, C))
            conn.execute('UPDATE conversations SET workspace_folder_id=%s WHERE id=%s', (F, C))
        self.authority_loss(move, 'invalidated')
        self.assertEqual(self.rows('SELECT workspace_folder_id FROM conversations WHERE id=%s', (C,))[0][0].hex, F.replace('-', ''))

    def test_committed_pending_can_be_cancelled_without_rewriting_revision(self):
        with self.env.pipeline(Provider()):
            self.assertEqual(self.env.document().status_code, 200)
        before = self.action()
        revision = self.rows('SELECT canonical,canonical_sha256,markdown_sha256 FROM document_revisions')[0]
        response = self.cancel()
        self.assertEqual(response.status_code, 200, response.get_json())
        after = response.get_json()['action']
        self.assertEqual(after['state'], 'cancelled')
        self.assertEqual(after['revision_id'], before['revision_id'])
        self.assertEqual(after['artifact_id'], before['artifact_id'])
        self.assertEqual(self.rows('SELECT canonical,canonical_sha256,markdown_sha256 FROM document_revisions')[0], revision)
        self.assertEqual(self.count('workspace_files'), 0)
        repeated = self.cancel()
        self.assertEqual(repeated.status_code, 200, repeated.get_json())
        self.assertEqual(repeated.get_json()['action'], after)

    def test_failed_successor_rolls_back_supersession_and_preserves_previous_pending(self):
        with self.env.pipeline(Provider()):
            self.assertEqual(self.env.document().status_code, 200)
        before = self.action()
        original = self.rows('SELECT canonical,canonical_sha256,markdown_sha256 FROM document_revisions')[0]
        provider = Provider()
        with self.fault('document_actions', 'UPDATE', "NEW.state='pending'"), self.env.pipeline(provider) as (normal, _):
            response = self.env.document(identity=O, message='Prepare failed successor')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.action(), before)
        self.assertEqual(self.action(O)['state'], 'failed')
        self.assertEqual(self.count('document_revisions'), 1)
        self.assertEqual(self.count('document_artifacts'), 1)
        self.assertEqual(self.rows('SELECT canonical,canonical_sha256,markdown_sha256 FROM document_revisions')[0], original)
        self.assertEqual(self.rows("SELECT id FROM document_actions WHERE state='pending'")[0][0].hex, T.replace('-', ''))
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(normal, [])

    def test_new_preparation_supersedes_only_previous_pending_revision(self):
        with self.env.pipeline(Provider()):
            self.assertEqual(self.env.document().status_code, 200)
        first = self.action()
        value = fixture.envelope()
        value['proposal']['canonical'] = fixture.canonical('Revised synthetic document')
        provider = Provider(value)
        with self.env.pipeline(provider) as (normal, _):
            self.assertEqual(self.env.document(identity=O, message='Prepare revised synthetic document').status_code, 200)
        second = self.action(O)
        self.assertEqual(self.action()['state'], 'superseded')
        self.assertEqual(self.action()['revision_id'], first['revision_id'])
        self.assertEqual(second['state'], 'pending')
        self.assertNotEqual(second['revision_id'], first['revision_id'])
        self.assertEqual(self.count('document_revisions'), 2)
        self.assertEqual(self.rows("SELECT count(*) FROM document_actions WHERE state='pending'")[0][0], 1)
        self.assertEqual(self.count('workspace_files'), 0)
        self.assertEqual(normal, [])

    def test_pending_survives_sql_age_and_fresh_app_instance_without_provider(self):
        provider = Provider()
        with self.env.pipeline(provider):
            self.assertEqual(self.env.document().status_code, 200)
        before = self.action()
        with self.env.conn() as independent:
            independent.execute("UPDATE document_actions SET updated_at=clock_timestamp()-interval '100 days' WHERE id=%s", (T,))
            independent.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '100 days' WHERE turn_id=%s", (T,))
        fresh = load_server_module_for_tests()
        response = self.get(server=fresh)
        self.assertEqual(response.status_code, 200, response.get_json())
        action = response.get_json()['action']
        self.assertEqual(action['state'], 'pending')
        for field in ('id','context_id','revision_id','artifact_id','operation','format','relative_path'):
            self.assertEqual(action[field], before[field])
        self.assertEqual(len(provider.calls), 1)
        self.assertNotIn('canonical', str(response.get_json()))

    def test_revision_and_bound_action_fields_are_sql_immutable(self):
        with self.env.pipeline(Provider()):
            self.assertEqual(self.env.document().status_code, 200)
        before = self.action()
        original = self.rows('SELECT canonical,canonical_sha256,markdown_sha256 FROM document_revisions')[0]
        for sql, args in (('UPDATE document_revisions SET canonical=%s::jsonb WHERE id=%s', ('{}', before['revision_id'])),
                          ('UPDATE document_actions SET relative_path=%s WHERE id=%s', ('Documents/Other.md', T))):
            with self.subTest(boundary=sql.split()[1]):
                with self.assertRaises(psycopg.errors.RaiseException):
                    with self.env.conn() as independent:
                        independent.execute(sql, args)
        self.assertEqual(self.action(), before)
        self.assertEqual(self.rows('SELECT canonical,canonical_sha256,markdown_sha256 FROM document_revisions')[0], original)

    def test_cancel_waiting_at_final_commit_has_one_serialized_durable_outcome(self):
        staged, release, cancel_arrived = threading.Event(), threading.Event(), threading.Event()
        identity = {}
        finalize = self.actions.finalize
        conversation_lock = claims._conversation
        def staged_finalize(*args, **kwargs):
            snapshot = kwargs['snapshot']
            def staged_snapshot(conversation, conn):
                snapshot(conversation, conn)
                staged.set()
                self.assertTrue(release.wait(10))
            return finalize(*args, **(kwargs | {'snapshot': staged_snapshot}))
        def observe_lock(conn, conversation, **kwargs):
            if threading.get_ident() == identity.get('cancel'):
                cancel_arrived.set()
            return conversation_lock(conn, conversation, **kwargs)
        def cancelling():
            identity['cancel'] = threading.get_ident()
            return self.cancel()
        provider = Provider()
        with self.env.pipeline(provider) as (normal, _), patch.object(self.actions, 'finalize', staged_finalize), \
             patch.object(claims, '_conversation', observe_lock), ThreadPoolExecutor(2) as pool:
            pending = pool.submit(self.env.document)
            self.assertTrue(staged.wait(5))
            cancelled = pool.submit(cancelling)
            try:
                self.assertTrue(cancel_arrived.wait(5))
                self.assertFalse(cancelled.done())
                # Independently visible state is still the initial user/action;
                # artifacts, revision and assistant are uncommitted together.
                self.assertEqual(self.roles(), [('user', 'Synthetic request')])
                self.assertEqual(self.count('document_revisions'), 0)
                self.assertEqual(self.rows('SELECT state FROM document_actions WHERE id=%s', (T,))[0][0], 'preparing')
            finally:
                release.set()
                result = pending.result(timeout=10)
                cancellation = cancelled.result(timeout=10)
        self.assertEqual(result.status_code, 200, result.get_json())
        self.assertEqual(cancellation.status_code, 200, cancellation.get_json())
        self.assertEqual(self.action()['state'], 'cancelled')
        self.assertEqual(claims.read(T)['outcome'], 'succeeded')
        self.assertEqual(self.count('document_revisions'), 1)
        self.assertEqual([role for role, _ in self.roles()], ['user','assistant'])
        self.assertEqual(normal, [])
        self.env.assert_no_open_transaction()
