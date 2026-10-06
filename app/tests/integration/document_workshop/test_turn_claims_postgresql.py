"""Independent SQL connections; only synthetic data in an explicit proof database."""
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4
import psycopg
from core import conv_store, document_workshop_contexts as contexts
from tests.integration.document_workshop import test_claim_transport_postgresql as fixture
C, F, O = (fixture.C, fixture.F, fixture.O)

@unittest.skipUnless(os.environ.get('M3_PROOF_PG_SOCKET'), 'isolated PostgreSQL proof required')
class TurnClaimsPostgresqlTests(unittest.TestCase):
    conn = fixture.ClaimTransportPostgresqlTests.conn

    def setUp(self):
        fixture.ClaimTransportPostgresqlTests.setUp(self)
        from core import conversation_turn_claims
        self.store = conversation_turn_claims
        self.claim_patch = patch.object(self.store, '_db_conn', self.conn)
        self.claim_patch.start()
        self.addCleanup(self.claim_patch.stop)
        self.store.init_db()
        self.store.init_db()

    def claim(self, conversation=C, kind='chat', context=None, identity=None, fingerprint='a' * 64, **kwargs):
        return self.store.acquire(conversation_id=conversation, turn_id=identity or str(uuid4()), request_fingerprint=fingerprint, kind=kind, context_id=context, **kwargs)

    def aged_context(self, context):
        aged_id = str(uuid4())
        with self.conn() as conn:
            conn.execute("""INSERT INTO document_workshop_contexts
                    (id,conversation_id,workspace_folder_id,target_file_id,target_relative_path,
                     target_document_ref,target_remote_identity,state,created_at)
                SELECT %s::uuid, conversation_id, workspace_folder_id, target_file_id,
                    target_relative_path, target_document_ref, target_remote_identity, state, '2000-01-01'::timestamptz
                FROM document_workshop_contexts WHERE id=%s::uuid""", (aged_id,context['id']))
        return contexts.get_context(aged_id)

    def snapshot(self, token, text='Synthetic final', outcome='succeeded'):
        v = conv_store.load_conversation(C, 'BACKEND SYSTEM PROMPT')
        conv_store.append_message(v, 'assistant', text)
        return conv_store.save_conversation(v, turn_claim=token, claim_outcome=outcome)

    def test_independent_connections_one_owner_same_turn_no_replay(self):
        identity = str(uuid4())
        barrier = threading.Barrier(2)

        def acquire():
            barrier.wait()
            return self.claim(identity=identity)
        with ThreadPoolExecutor(2) as pool:
            a, b = list(pool.map(lambda _: acquire(), range(2)))
        self.assertEqual(sum((r.token is not None for r in (a, b))), 1)
        winner = a if a.token else b
        self.assertTrue(self.snapshot(winner.token).ok)
        self.store.finish(winner.token)
        repeat = self.claim(identity=identity)
        self.assertIsNone(repeat.token)
        self.assertEqual(repeat.record['state'], 'succeeded')
        with self.assertRaises(self.store.ClaimError):
            self.claim(identity=identity, fingerprint='b' * 64)

    def test_sql_unique_active_conversation_and_independent_conversation(self):
        a = self.claim()
        with self.assertRaises(self.store.ClaimError) as e:
            self.claim()
        self.assertEqual(e.exception.reason_code, 'conversation_turn_conflict')
        v = conv_store.new_conversation('BACKEND SYSTEM PROMPT', conversation_id=O)
        self.assertTrue(conv_store.save_conversation(v).ok)
        b = self.claim(conversation=O)
        self.assertIsNotNone(b.token)
        with self.conn() as c:
            self.assertEqual(c.execute("SELECT count(*) FROM conversation_turn_claims WHERE state='active'").fetchone()[0], 2)
        self.store.finish(a.token, 'interrupted')
        self.store.finish(b.token, 'interrupted')

    def test_renew_expiry_successor_generation_and_all_old_operations_refused(self):
        a = self.claim()
        self.store.renew(a.token)
        with self.conn() as c:
            c.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second' WHERE turn_id=%s", (a.token.turn_id,))
        b = self.claim()
        self.assertGreater(b.token.generation, a.token.generation)
        self.assertFalse(self.snapshot(a.token, 'Late result').ok)
        for method in (self.store.renew, self.store.finish, self.store.cancel):
            with self.subTest(method=method.__name__), self.assertRaises(self.store.ClaimError):
                method(a.token)
        self.assertEqual(self.store.read(a.token.turn_id)['state'], 'lost')
        self.assertEqual(self.store.read(b.token.turn_id)['state'], 'active')
        self.assertIsNone(self.claim(identity=a.token.turn_id).token)
        self.assertTrue(self.snapshot(b.token).ok)
        self.store.finish(b.token)

    def test_document_claim_blocks_normal_chat_and_old_proposal_has_no_ttl(self):
        from core import document_workshop_contexts
        r = document_workshop_contexts.create_context(conversation_id=C, workspace_folder_id=F)
        r = self.aged_context(r)
        a = self.claim(kind='confirmation', context=r['id'])
        with self.assertRaises(self.store.ClaimError):
            self.claim()
        self.assertIsNotNone(a.token)
        self.store.finish(a.token, 'interrupted')
        b = self.claim(kind='preparation', context=r['id'])
        self.store.cancel(b.token)
        self.assertEqual(self.store.read(b.token.turn_id)['state'], 'cancelled')
        self.assertFalse(self.snapshot(b.token, 'After cancel').ok)

    def test_scope_move_roundtrip_cancels_old_authority_atomically(self):
        from core import document_workshop_contexts
        r = document_workshop_contexts.create_context(conversation_id=C, workspace_folder_id=F)
        a = self.claim(kind='preparation', context=r['id'])
        with self.conn() as c:
            c.execute('UPDATE conversations SET workspace_folder_id=%s WHERE id=%s', (O, C))
        with self.conn() as c:
            c.execute('UPDATE conversations SET workspace_folder_id=%s WHERE id=%s', (F, C))
        self.assertFalse(self.snapshot(a.token, 'Old scope').ok)
        self.assertEqual(self.store.read(a.token.turn_id)['state'], 'invalidated')
        self.assertEqual(document_workshop_contexts.get_context(r['id'])['state'], 'invalidated')
        b = self.claim()
        self.assertIsNotNone(b.token)
        with self.assertRaises(self.store.ClaimError):
            self.store.finish(a.token)
        self.assertEqual(self.store.read(b.token.turn_id)['state'], 'active')

    def test_final_snapshot_sql_failure_rolls_back_outcome_and_preserves_initial_user(self):
        a = self.claim()
        v = conv_store.load_conversation(C, 'BACKEND SYSTEM PROMPT')
        conv_store.append_message(v, 'user', 'Synthetic request', meta={'client_turn_id': a.token.turn_id})
        self.assertTrue(conv_store.save_conversation(v, turn_claim=a.token).ok)
        with self.conn() as c:
            c.execute("CREATE FUNCTION reject_assistant() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.role='assistant' THEN RAISE EXCEPTION 'synthetic write refusal'; END IF; RETURN NEW; END $$; CREATE TRIGGER proof_refusal BEFORE INSERT ON conversation_messages FOR EACH ROW EXECUTE FUNCTION reject_assistant()")
        self.assertFalse(self.snapshot(a.token).ok)
        r = self.store.read(a.token.turn_id)
        self.assertEqual(r['state'], 'active')
        self.assertIsNone(r['outcome'])
        with self.conn() as c:
            self.assertEqual(c.execute("SELECT role FROM conversation_messages WHERE role<>'system'").fetchall(), [('user',)])
        self.store.finish(a.token, 'interrupted')

    def test_cancel_document_token_closes_its_context_and_refuses_new_confirmation(self):
        from core import document_workshop_contexts
        context = document_workshop_contexts.create_context(conversation_id=C, workspace_folder_id=F)
        admission = self.claim(kind='preparation', context=context['id'])
        self.store.cancel(admission.token)
        self.assertEqual(document_workshop_contexts.get_context(context['id'])['state'], 'cancelled')
        with self.assertRaises(self.store.ClaimError):
            self.claim(kind='confirmation', context=context['id'])

    def test_inactivity_is_durable_and_renewal_does_not_rearm_m0_progress(self):
        from core import document_workshop_contexts
        from core.document_workshop_progress import DocumentPreparation
        from core.document_workshop_contract import DocumentWorkshopError
        context = document_workshop_contexts.create_context(conversation_id=C, workspace_folder_id=F)
        admission = self.claim(kind='preparation', context=context['id'])
        clock = [0]
        progress = DocumentPreparation(monotonic=lambda: clock[0])
        progress.complete_step('payload_prepared')
        progress.complete_step('admitted')
        progress.begin_exchange()
        for tick in (119, 238, 357):
            clock[0] = tick
            progress._receive_provider_content('Synthetic useful content')
            self.store.renew(admission.token)
            self.assertEqual(progress.snapshot().state, 'preparing')
        clock[0] = 476
        self.store.renew(admission.token)
        progress.check()
        clock[0] = 477
        self.store.renew(admission.token)
        with self.assertRaises(DocumentWorkshopError) as error:
            progress.check()
        self.assertEqual(error.exception.reason_code, 'document_inactivity')
        self.store.finish(admission.token, 'failed', reason_code=error.exception.reason_code)
        record = self.store.read(admission.token.turn_id)
        self.assertEqual(record['state'], 'failed')
        self.assertEqual(record['reason_code'], 'document_inactivity')
        with self.assertRaises(self.store.ClaimError):
            self.store.renew(admission.token)

    def test_supplied_snapshot_transaction_does_not_commit_and_rollback_is_independent(self):
        v = conv_store.load_conversation(C, 'BACKEND SYSTEM PROMPT')
        conv_store.append_message(v, 'user', 'Synthetic uncommitted turn')
        with self.assertRaisesRegex(RuntimeError, 'synthetic rollback'):
            with self.conn() as owner:
                conv_store.save_conversation_snapshot_in_transaction(v, owner)
                with self.conn() as observer:
                    self.assertEqual(observer.execute("SELECT count(*) FROM conversation_messages WHERE role='user'").fetchone()[0], 0)
                raise RuntimeError('synthetic rollback')
        with self.conn() as observer:
            self.assertEqual(observer.execute("SELECT count(*) FROM conversation_messages WHERE role='user'").fetchone()[0], 0)

    def test_request_scope_reuse_is_incompatible_even_with_identical_fingerprint(self):
        admission = self.claim()
        v = conv_store.new_conversation('BACKEND SYSTEM PROMPT', conversation_id=O)
        self.assertTrue(conv_store.save_conversation(v).ok)
        with self.assertRaises(self.store.ClaimError) as error:
            self.claim(conversation=O, identity=admission.token.turn_id)
        self.assertEqual(error.exception.reason_code, 'conversation_turn_id_incompatible')

    def target_context(self):
        from core import document_workshop_contexts
        with self.conn() as conn:
            conn.execute("INSERT INTO workspace_files VALUES (%s,%s,'active','document','text','.md',NULL)", (fixture.T, F))
            conn.execute('INSERT INTO workspace_file_nextcloud_links VALUES (%s,%s,\'linked\',\'Spec.md\',\'workspace-file:synthetic\',\'Documents/Spec.md\',%s,\'1\',\'"synth1"\')', (fixture.T, F, 'a' * 64))
        return document_workshop_contexts.create_context(conversation_id=C, workspace_folder_id=F, target_file_id=fixture.T, target_relative_path='Documents/Spec.md', target_document_ref='workspace-file:synthetic', target_remote_identity='a' * 64 + ':1')

    def test_ancient_confirmation_checks_current_target_etag_without_age_limit(self):
        context = self.target_context()
        context = self.aged_context(context)
        with self.assertRaises(self.store.ClaimError):
            self.claim(kind='confirmation', context=context['id'], expected_etag='"old"')
        admission = self.claim(kind='confirmation', context=context['id'], expected_etag='"synth1"')
        self.assertIsNotNone(admission.token)
        self.store.finish(admission.token, 'interrupted')

    def test_target_round_trip_never_restores_old_context_or_token(self):
        context = self.target_context()
        admission = self.claim(kind='preparation', context=context['id'])
        with self.conn() as conn:
            conn.execute("UPDATE workspace_file_nextcloud_links SET nextcloud_relative_path='Documents/Other.md'")
        with self.conn() as conn:
            conn.execute("UPDATE workspace_file_nextcloud_links SET nextcloud_relative_path='Documents/Spec.md'")
        self.assertEqual(self.store.read(admission.token.turn_id)['state'], 'invalidated')
        self.assertFalse(self.snapshot(admission.token).ok)
        with self.assertRaises(self.store.ClaimError):
            self.claim(kind='confirmation', context=context['id'])

    def test_new_target_context_invalidates_previous_even_after_reselection(self):
        from core import document_workshop_contexts
        context = self.target_context()
        admission = self.claim(kind='preparation', context=context['id'])
        next_context = document_workshop_contexts.create_context(conversation_id=C, workspace_folder_id=F)
        self.assertEqual(next_context['state'], 'editing')
        restored = document_workshop_contexts.create_context(conversation_id=C, workspace_folder_id=F, target_file_id=fixture.T, target_relative_path='Documents/Spec.md', target_document_ref='workspace-file:synthetic', target_remote_identity='a' * 64 + ':1')
        self.assertEqual(restored['state'], 'editing')
        self.assertNotEqual(restored['id'], context['id'])
        self.assertEqual(self.store.read(admission.token.turn_id)['state'], 'invalidated')
        self.assertFalse(self.snapshot(admission.token).ok)

    def test_forged_owner_or_generation_cannot_write_renew_cancel_or_finish(self):
        from dataclasses import replace
        admission = self.claim()
        for forged in (replace(admission.token, owner_id=str(uuid4())), replace(admission.token, generation=admission.token.generation + 1)):
            with self.subTest(generation=forged.generation):
                self.assertFalse(self.snapshot(forged).ok)
                for method in (self.store.renew, self.store.finish, self.store.cancel):
                    with self.assertRaises(self.store.ClaimError):
                        method(forged)
        self.assertEqual(self.store.read(admission.token.turn_id)['state'], 'active')

    def test_schema_replay_keeps_generation_and_existing_claims(self):
        admission = self.claim()
        self.store.init_db()
        self.store.init_db()
        self.assertEqual(self.store.read(admission.token.turn_id)['state'], 'active')
        self.store.renew(admission.token)
        with self.conn() as conn:
            tables = {row[0] for row in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")}
        self.assertFalse(tables & {'document_actions', 'document_revisions', 'document_receipts', 'document_artifacts'})
        self.store.finish(admission.token, 'interrupted')
        successor = self.claim()
        self.assertGreater(successor.token.generation, admission.token.generation)

    def test_sql_exclusion_between_distinct_processes(self):
        import multiprocessing
        ctx = multiprocessing.get_context('fork')
        ready, results = (ctx.Queue(), ctx.Queue())
        gate = ctx.Event()
        identity = str(uuid4())

        def acquire_in_process():
            ready.put(True)
            if not gate.wait(5):
                raise RuntimeError('proof rendezvous timed out')
            admission = self.claim(identity=identity)
            results.put((admission.token is not None, admission.record['state']))
        processes = [ctx.Process(target=acquire_in_process) for _ in range(2)]
        try:
            for process in processes:
                process.start()
            for _ in processes:
                self.assertTrue(ready.get(timeout=5))
            gate.set()
            observations = [results.get(timeout=5) for _ in processes]
            for process in processes:
                process.join(timeout=5)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(sum((owner for owner, _ in observations)), 1)
            with self.conn() as conn:
                self.assertEqual(conn.execute("SELECT count(*) FROM conversation_turn_claims WHERE state='active'").fetchone()[0], 1)
        finally:
            gate.set()
            for process in processes:
                if process.is_alive():
                    process.terminate()
                process.join(timeout=5)
            ready.close()
            results.close()

    def test_pre_final_node_state_write_is_fenced_on_the_same_sql_connection(self):
        from memory import memory_store, hermeneutic_node_state
        with self.conn() as conn:
            with conn.cursor() as cursor:
                hermeneutic_node_state.ensure_table(cursor)
        first = self.claim()
        state = {'schema_version': 'v1', 'conversation_id': C, 'updated_at': '2026-10-06T10:00:00Z', 'last_judgment_posture': 'answer', 'last_answer_output_regime': {'discursive_regime': 'simple', 'resituation_level': 'none', 'time_reference_mode': 'atemporal'}}
        with patch.object(memory_store, '_conn', self.conn):
            self.assertTrue(memory_store.write_hermeneutic_node_state(C, state, turn_claim=first.token)['written'])
            with self.conn() as conn:
                conn.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second'")
            successor = self.claim()
            state['last_judgment_posture'] = 'suspend'
            self.assertFalse(memory_store.write_hermeneutic_node_state(C, state, turn_claim=first.token)['written'])
        with self.conn() as conn:
            self.assertEqual(conn.execute('SELECT last_judgment_posture FROM hermeneutic_node_states').fetchone()[0], 'answer')
        self.assertEqual(self.store.read(successor.token.turn_id)['state'], 'active')

    def test_token_cannot_be_transplanted_to_another_conversation_with_same_generation(self):
        from dataclasses import replace
        first=self.claim()
        v=conv_store.new_conversation('BACKEND SYSTEM PROMPT',conversation_id=O)
        self.assertTrue(conv_store.save_conversation(v).ok)
        second=self.claim(conversation=O)
        self.assertEqual(first.token.generation,second.token.generation)
        forged=replace(first.token,conversation_id=O)
        conv_store.append_message(v,'assistant','Synthetic transplanted result')
        self.assertFalse(conv_store.save_conversation(v,turn_claim=forged,claim_outcome='succeeded').ok)
        for method in (self.store.renew,self.store.finish,self.store.cancel):
            with self.assertRaises(self.store.ClaimError):method(forged)
        self.assertEqual(self.store.read(first.token.turn_id)['state'],'active')
        self.assertEqual(self.store.read(second.token.turn_id)['state'],'active')


    def test_folder_link_round_trip_permanently_invalidates_document_claim(self):
        context = contexts.create_context(conversation_id=C, workspace_folder_id=F)
        first = self.claim(kind='preparation', context=context['id'])
        for reference in ('folder-b', 'folder-a'):
            with self.conn() as conn:
                conn.execute('UPDATE workspace_folder_nextcloud_links SET nextcloud_folder_ref=%s WHERE workspace_folder_id=%s', (reference,F))
        with self.assertRaises(self.store.ClaimError):
            self.store.renew(first.token)
        self.assertEqual(self.store.read(first.token.turn_id)['state'], 'invalidated')
        self.assertEqual(contexts.get_context(context['id'])['state'], 'invalidated')

    def test_context_identity_cannot_be_rewritten_in_place(self):
        context = contexts.create_context(conversation_id=C, workspace_folder_id=F)
        with self.assertRaises(psycopg.Error):
            with self.conn() as conn:
                conn.execute('UPDATE document_workshop_contexts SET workspace_folder_id=%s WHERE id=%s', (O,context['id']))
        self.assertEqual(contexts.get_context(context['id'])['workspace_folder_id'], F)

    def test_document_inactivity_never_applies_to_normal_chat(self):
        first = self.claim()
        with self.assertRaises(self.store.ClaimError):
            self.store.finish(first.token, 'failed', reason_code='document_inactivity')
        self.assertEqual(self.store.read(first.token.turn_id)['state'], 'active')

    def test_folder_delete_and_document_admission_do_not_deadlock(self):
        from core import workspace_folders_store, workspace_folder_nextcloud_links_store
        from types import SimpleNamespace
        context = contexts.create_context(conversation_id=C, workspace_folder_id=F)
        with self.conn() as conn:
            conn.execute('''ALTER TABLE workspace_folders ADD COLUMN display_name text DEFAULT 'Synthetic',
                ADD COLUMN icon_key text DEFAULT '', ADD COLUMN description text DEFAULT '',
                ADD COLUMN sort_order integer DEFAULT 0, ADD COLUMN created_at timestamptz DEFAULT now(),
                ADD COLUMN updated_at timestamptz DEFAULT now()''')
            conn.execute('DROP TABLE workspace_folder_nextcloud_links')
            workspace_folder_nextcloud_links_store.ensure_schema(conn.cursor())
        conversation_locked, folder_locked = threading.Event(), threading.Event()
        original_scope = self.store._scope
        def scope_after_conversation(*args, **kwargs):
            conversation_locked.set()
            self.assertTrue(folder_locked.wait(10))
            return original_scope(*args, **kwargs)
        owner = self
        class Cursor:
            def __init__(self, cur): self.cur = cur
            def __enter__(self): return self
            def __exit__(self, *args): return self.cur.__exit__(*args)
            def __getattr__(self, name): return getattr(self.cur, name)
            def execute(self, query, params=None):
                result = self.cur.execute(query, params)
                if 'UPDATE workspace_folders' in query:
                    folder_locked.set()
                    owner.assertTrue(conversation_locked.wait(10))
                return result
        class Connection:
            def __init__(self): self.conn = owner.conn()
            def __enter__(self): return self
            def __exit__(self, *args): return self.conn.__exit__(*args)
            def __getattr__(self, name): return getattr(self.conn, name)
            def cursor(self, *args, **kwargs): return Cursor(self.conn.cursor(*args, **kwargs))
        with patch.object(self.store, '_scope', scope_after_conversation), ThreadPoolExecutor(2) as pool:
            admission = pool.submit(self.claim, kind='preparation', context=context['id'])
            self.assertTrue(conversation_locked.wait(10))
            deletion = pool.submit(workspace_folders_store.soft_delete_workspace_folder, F,
                db_conn_func=Connection, logger=SimpleNamespace(warning=lambda *a, **k: None))
            self.assertIsNotNone(deletion.result(timeout=10))
            with self.assertRaises(self.store.ClaimError) as caught:
                admission.result(timeout=10)
            self.assertEqual(caught.exception.reason_code, 'conversation_turn_conflict')
        self.assertEqual(contexts.get_context(context['id'])['state'], 'invalidated')

    def test_folder_rename_cannot_restore_document_scope(self):
        with self.conn() as conn:
            conn.execute("ALTER TABLE workspace_folders ADD COLUMN display_name text DEFAULT 'Synthetic A'")
        context = contexts.create_context(conversation_id=C, workspace_folder_id=F)
        admission = self.claim(kind='preparation', context=context['id'])
        for name in ('Synthetic B','Synthetic A'):
            with self.conn() as conn:
                conn.execute('UPDATE workspace_folders SET display_name=%s WHERE id=%s', (name,F))
        self.assertEqual(self.store.read(admission.token.turn_id)['state'], 'invalidated')
        with self.assertRaises(self.store.ClaimError): self.store.renew(admission.token)
