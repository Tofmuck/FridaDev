"""M3 triggers on the real M2 adoption path; isolated SQL and synthetic DAV only."""
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
from core import conversation_turn_claims as claims, document_workshop_contexts as contexts
from core import workspace_files_store
from tests.integration.document_workshop import test_adoption_postgresql as m2


@unittest.skipUnless(os.environ.get('M3_PROOF_PG_SOCKET'), 'isolated PostgreSQL proof required')
class ClaimAdoptionPostgresqlTests(unittest.TestCase):
    connection = m2.AdoptionPostgresqlTests.connection
    conversation = m2.AdoptionPostgresqlTests.conversation
    client = m2.AdoptionPostgresqlTests.client
    listing = m2.AdoptionPostgresqlTests.listing
    adopt = m2.AdoptionPostgresqlTests.adopt
    responses = m2.AdoptionPostgresqlTests.responses
    rows = m2.AdoptionPostgresqlTests.rows

    def setUp(self):
        m2.AdoptionPostgresqlTests.setUp(self)
        p = patch.object(claims, '_db_conn', self.connection)
        p.start()
        self.addCleanup(p.stop)
        claims.init_db()
        with self.connection() as conn:
            conn.execute('CREATE TABLE workspace_file_selections(workspace_file_id uuid, deleted_at timestamptz, updated_at timestamptz, last_excluded_reason_code text)')

    def target(self):
        row = self.rows()[0]
        link = row['link']
        self.context = contexts.create_context(conversation_id=m2.CONV, workspace_folder_id=m2.FOLDER,
            target_file_id=str(row['id']), target_relative_path=link['nextcloud_relative_path'],
            target_document_ref=link['nextcloud_document_ref'],
            target_remote_identity=link['nextcloud_scope_key']+':'+link['nextcloud_file_id'])
        return row

    def test_identical_readoption_rotates_cache_without_invalidating_authority(self):
        with m2.dav_server(self.responses()+self.responses()) as (base, _):
            client = self.client(base)
            listing, _ = self.listing(client)
            self.assertEqual(self.adopt(client, listing['items'][0]['reference'])[1], 201)
            before = self.target()
            admission = claims.acquire(conversation_id=m2.CONV, turn_id=str(uuid4()),
                request_fingerprint='a'*64, kind='confirmation', context_id=self.context['id'],
                expected_etag='"v1"')
            listing, _ = self.listing(client)
            payload, status = self.adopt(client, listing['items'][0]['reference'])
        self.assertEqual(status, 200, payload)
        self.assertNotEqual(before['storage_key'], self.rows()[0]['storage_key'])
        self.assertEqual(contexts.get_context(self.context['id'])['state'], 'editing')
        self.assertEqual(claims.read(admission.token.turn_id)['state'], 'active')
        claims.renew(admission.token)
        claims.finish(admission.token, 'interrupted')

    def test_adoption_and_actual_file_delete_have_no_lock_cycle(self):
        with m2.dav_server(self.responses()+self.responses()) as (base, _):
            client = self.client(base)
            listing, _ = self.listing(client)
            self.assertEqual(self.adopt(client, listing['items'][0]['reference'])[1], 201)
            row = self.target()
            listing, _ = self.listing(client)
            reference = listing['items'][0]['reference']
            before_file, file_locked = threading.Event(), threading.Event()
            owner = self
            class Cursor:
                def __init__(self, cur, adopting): self.cur, self.adopting = cur, adopting
                def __enter__(self): return self
                def __exit__(self, *args): return self.cur.__exit__(*args)
                def __getattr__(self, name): return getattr(self.cur, name)
                def execute(self, query, params=None):
                    locking_file = 'workspace_files' in query and 'FOR ' in query
                    if self.adopting and locking_file:
                        before_file.set()
                        owner.assertTrue(file_locked.wait(10))
                    result = self.cur.execute(query, params)
                    if not self.adopting and locking_file:
                        file_locked.set()
                    return result
            class Connection:
                def __init__(self, adopting): self.conn, self.adopting = owner.connection(), adopting
                def __enter__(self): return self
                def __exit__(self, *args): return self.conn.__exit__(*args)
                def __getattr__(self, name): return getattr(self.conn, name)
                def cursor(self, *args, **kwargs): return Cursor(self.conn.cursor(*args, **kwargs), self.adopting)
            diagnostics = []
            logger = SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: diagnostics.append(k.get('error_type') or str(a)))
            with patch.object(self.store, '_db_conn', lambda: Connection(True)), ThreadPoolExecutor(2) as pool:
                adoption = pool.submit(self.adopt, client, reference)
                self.assertTrue(before_file.wait(10))
                deletion = pool.submit(workspace_files_store.delete_workspace_file, m2.FOLDER, str(row['id']),
                    db_conn_func=lambda: Connection(False), storage_root=self.root, logger=logger)
                self.assertIsNotNone(deletion.result(timeout=10), diagnostics)
                payload, status = adoption.result(timeout=10)
                self.assertEqual(status, 409, payload)
            self.assertEqual(contexts.get_context(self.context['id'])['state'], 'invalidated')
