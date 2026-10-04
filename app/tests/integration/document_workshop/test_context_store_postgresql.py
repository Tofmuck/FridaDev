"""Execute M1 migration and store on an explicitly supplied isolated Unix socket."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import psycopg

from core import document_workshop_contexts as store
from core import document_workshop_context_service as service, workspace_files

CONV = '11111111-1111-4111-8111-111111111111'
FOLDER = '22222222-2222-4222-8222-222222222222'
OTHER = '33333333-3333-4333-8333-333333333333'
FILE = '44444444-4444-4444-8444-444444444444'


@unittest.skipUnless(os.environ.get('M1_PROOF_PG_SOCKET'), 'explicit isolated PostgreSQL proof runner required')
class ContextPostgresqlTests(unittest.TestCase):
    def connection(self):
        return psycopg.connect(host=os.environ['M1_PROOF_PG_SOCKET'], dbname='m1proof', user='m1proof')

    def setUp(self):
        with self.connection() as conn:
            conn.execute('DROP SCHEMA public CASCADE; CREATE SCHEMA public')
            conn.execute('''CREATE TABLE workspace_folders (id uuid PRIMARY KEY, deleted_at timestamptz);
                CREATE TABLE conversations (id uuid PRIMARY KEY, workspace_folder_id uuid, deleted_at timestamptz);
                CREATE TABLE workspace_files (id uuid PRIMARY KEY, workspace_folder_id uuid, status text,
                    content_kind text, media_kind text, source_extension text, deleted_at timestamptz);
                CREATE TABLE workspace_file_nextcloud_links (workspace_file_id uuid PRIMARY KEY,
                    workspace_folder_id uuid, nextcloud_sync_state text, nextcloud_target_name text,
                    nextcloud_document_ref text, nextcloud_name_hash text DEFAULT '', last_sync_at timestamptz,
                    last_sync_reason_code text DEFAULT '', last_sync_operation text,
                    created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now());''')
            conn.execute('INSERT INTO workspace_folders VALUES (%s, NULL), (%s, NULL)', (FOLDER, OTHER))
            conn.execute('INSERT INTO conversations VALUES (%s,%s,NULL)', (CONV, FOLDER))
            conn.execute("INSERT INTO workspace_files VALUES (%s,%s,'active','document','text','.md',NULL)", (FILE,FOLDER))
            conn.execute("INSERT INTO workspace_file_nextcloud_links (workspace_file_id,workspace_folder_id,nextcloud_sync_state,nextcloud_target_name,nextcloud_document_ref) VALUES (%s,%s,'linked','Ébauche.md','workspace-file:test')", (FILE,FOLDER))
        patcher = patch.object(store, '_db_conn', self.connection)
        patcher.start(); self.addCleanup(patcher.stop)
        self.assertTrue(store.init_db())
        self.assertTrue(store.init_db())

    def create(self, target=False):
        return store.create_context(conversation_id=CONV, workspace_folder_id=FOLDER,
            target_file_id=FILE if target else None,
            target_relative_path='Documents/Ébauche.md' if target else None,
            target_document_ref='workspace-file:test' if target else None)

    def test_migration_is_idempotent_and_committed_row_survives_new_connection(self):
        record = self.create()
        self.assertEqual(record['state'], 'editing')
        self.assertEqual(store.get_context(record['id']), record)
        with self.connection() as independent:
            self.assertEqual(independent.execute('SELECT count(*) FROM document_workshop_contexts').fetchone()[0], 1)
        self.assertIsNone(store.get_context('55555555-5555-4555-8555-555555555555'))

    def test_target_identity_and_original_unicode_path_are_persisted(self):
        record = self.create(target=True)
        reread = store.get_context(record['id'])
        self.assertEqual(reread['target_file_id'], FILE)
        self.assertEqual(reread['target_relative_path'], 'Documents/Ébauche.md')
        self.assertEqual(reread['target_document_ref'], 'workspace-file:test')

    def test_sql_rechecks_scope_after_service_validation_before_insert(self):
        updates = [
            ('UPDATE conversations SET workspace_folder_id=%s WHERE id=%s', (OTHER,CONV)),
            ('UPDATE workspace_folders SET deleted_at=now() WHERE id=%s', (FOLDER,)),
            ("UPDATE workspace_files SET status='deleted' WHERE id=%s", (FILE,)),
            ("UPDATE workspace_file_nextcloud_links SET nextcloud_document_ref='replaced' WHERE workspace_file_id=%s", (FILE,)),
        ]
        for sql, params in updates:
            with self.subTest(sql=sql):
                self.setUp()
                with self.connection() as conn:
                    conn.execute(sql, params)
                self.assertIsNone(self.create(target=True))

    def test_foreign_keys_and_closed_state_reject_invalid_persistence(self):
        record = self.create()
        with self.connection() as conn:
            with self.assertRaises(psycopg.errors.CheckViolation):
                conn.execute("UPDATE document_workshop_contexts SET state='pending' WHERE id=%s", (record['id'],))
        with self.connection() as conn:
            conn.execute('DELETE FROM conversations WHERE id=%s', (CONV,))
        self.assertIsNone(store.get_context(record['id']))

    def test_existing_link_reader_keeps_legacy_default_and_preserves_workshop_identity(self):
        name = 'Épreuve  française.md'
        with self.connection() as conn:
            conn.execute('UPDATE workspace_file_nextcloud_links SET nextcloud_target_name=%s', (name,))
        with patch.object(workspace_files, '_db_conn', self.connection):
            legacy = workspace_files.get_nextcloud_link(FILE, fail_closed=True)
            exact = workspace_files.get_nextcloud_link(FILE, fail_closed=True, preserve_target_identity=True)
            self.assertEqual(legacy['nextcloud_target_name'], 'Épreuve française.md')
            self.assertEqual(exact['nextcloud_target_name'], name)
            files = SimpleNamespace(get_nextcloud_link=workspace_files.get_nextcloud_link,
                get_workspace_file_storage_row=lambda *_: dict(id=FILE, workspace_folder_id=FOLDER,
                    status='active',content_kind='document',media_kind='text',source_extension='.md'))
            conversations = SimpleNamespace(get_conversation_summary=lambda *_: dict(id=CONV, workspace_folder_id=FOLDER))
            folders = SimpleNamespace(get_workspace_folder=lambda *_: dict(id=FOLDER))
            payload, status = service.create_context(dict(conversation_id=CONV, workspace_folder_id=FOLDER,target_file_id=FILE),
                store=store, conversations=conversations, folders=folders, files=files)
            self.assertEqual(status, 201)
            self.assertEqual(payload['context']['target_relative_path'], 'Documents/' + name)
            persisted = store.get_context(payload['context']['id'])
            self.assertEqual(persisted['target_relative_path'], 'Documents/' + name)
            with self.connection() as conn:
                conn.execute("UPDATE workspace_file_nextcloud_links SET nextcloud_target_name='../Épreuve.md'")
            rejected, status = service.get_context(persisted['id'], store=store, conversations=conversations, folders=folders, files=files)
            self.assertEqual(status, 422)
            self.assertFalse(rejected['ok'])
