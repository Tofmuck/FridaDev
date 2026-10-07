"""M6 product wiring: real SQL, Flask and production DAV on loopback only."""
import hashlib
import importlib
import importlib.util
import json
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from core.document_canonical import validate_canonical
from core import conv_store, document_workshop_actions as actions
from core import workspace_files, workspace_folders
from tests.integration.document_workshop import test_execution_postgresql as fixture
from tests.unit.core.test_workspace_document_mutation_client_m5 import dav_server, creation_responses
from tests.support.server_test_bootstrap import load_server_module_for_tests


@unittest.skipUnless(os.environ.get('M5_PROOF_PG_SOCKET'), 'isolated PostgreSQL required')
class ProductM6PostgresqlTests(unittest.TestCase):
    def setUp(self):
        self.env = fixture.ExecutionPostgresqlTests('runTest')
        self.env.setUp(); self.addCleanup(self.env.doCleanups)
        self.conn = self.env.conn
        self.server = load_server_module_for_tests()
        self.password = self.env.env.root / 'synthetic-password'
        self.password.write_text('synthetic-only')
        self.assertIsNotNone(importlib.util.find_spec('core.document_workshop_runtime'),
                             'M6 production executor factory is missing')
        self.runtime = importlib.import_module('core.document_workshop_runtime')
        self.assertIsNotNone(importlib.util.find_spec('core.document_workshop_receipts'),
                             'M6 durable receipt projection is missing')
        self.receipts = importlib.import_module('core.document_workshop_receipts')

    def configured(self, base):
        return patch.dict(os.environ, dict(FRIDA_NEXTCLOUD_BASE_URL=base,
            FRIDA_NEXTCLOUD_USERNAME='test', FRIDA_NEXTCLOUD_ROOT_NAME='Frida',
            FRIDA_NEXTCLOUD_APP_PASSWORD_FILE=str(self.password)))

    def confirm(self):
        with self.server.app.test_client() as client:
            return client.post('/api/document-workshop/actions/'+self.env.request_turn+'/confirm', json=self.env.body())

    def responses(self):
        replies=creation_responses(self.env.action["relative_path"],self.content())
        return replies[:3]+replies

    def content(self):
        return fixture.serialize_markdown(validate_canonical(fixture.canonical())).encode()

    def test_server_factory_announces_and_executes_exact_bytes_then_reopens_receipt_and_link(self):
        path=self.env.action['relative_path']; content=self.content()
        with dav_server(self.responses()) as (base,seen), self.configured(base):
            with self.server.app.test_client() as client:
                context=client.get('/api/document-workshop/contexts/'+self.env.context).json['context']
                self.assertTrue(context['capabilities']['confirm'])
                self.assertEqual(seen,[],'GET must not contact DAV')
            response=self.confirm()
            self.assertEqual(response.status_code,200,response.json)
            action=response.json['action']; self.assertEqual(action['state'],'succeeded')
            receipt=action['receipt']
            self.assertEqual(receipt['request_turn_id'],self.env.request_turn)
            self.assertEqual(receipt['confirmation_turn_id'],action['confirmation_turn_id'])
            self.assertEqual(receipt['relative_path'],path)
            self.assertEqual(receipt['name'],'Exact  e\u0301.md')
            self.assertEqual(receipt['publication_evidence'],'historical')
            self.assertEqual(receipt['content_sha256'],hashlib.sha256(content).hexdigest())
            self.assertNotIn('canonical',receipt); self.assertNotIn('nextcloud_scope_key',receipt)
            with self.server.app.test_client() as client:
                opened=client.get(receipt['product_link'])
                self.assertEqual(opened.status_code,200)
                self.assertEqual(opened.data,content)
                self.assertIn('attachment',opened.headers['Content-Disposition'])
                self.assertEqual(client.get('/api/document-workshop/actions/'+self.env.request_turn).json['action']['receipt'],receipt)
            self.assertEqual(self.confirm().json['action']['receipt'],receipt)
            puts=[r for r in seen if r[0]=='PUT']; self.assertEqual(len(puts),1)
            self.assertEqual(puts[0][3],content); self.assertEqual(puts[0][2]['If-None-Match'],'*')
            self.assertEqual(len(workspace_files.list_workspace_files(self.env.folder)),1)
            self.assertEqual(self.env.rows('SELECT count(*) FROM document_receipts'),[(1,)])

    def test_missing_configuration_or_schema_or_cache_refuses_without_claim_or_dav(self):
        with dav_server([]) as (base,seen),self.configured(base):
            self.password.unlink()
            self.assertIsNone(self.runtime.get_executor())
            self.assertEqual(self.confirm().status_code,503)
            self.password.write_text('synthetic-only')
            with patch.object(workspace_files,'_storage_root',lambda:self.env.env.root/'absent'):
                self.assertIsNone(self.runtime.get_executor())
                self.assertEqual(self.confirm().status_code,503)
            with self.conn() as conn:conn.execute('ALTER TABLE document_receipts RENAME COLUMN creation_author TO absent_author')
            self.assertIsNone(self.runtime.get_executor())
            self.assertEqual(self.confirm().status_code,503)
            with self.conn() as conn:conn.execute('ALTER TABLE document_receipts RENAME COLUMN absent_author TO creation_author')
            with self.conn() as conn:conn.execute('DROP TABLE document_execution_journal')
            self.assertIsNone(self.runtime.get_executor())
            self.assertEqual(self.confirm().status_code,503)
            self.assertEqual(seen,[])
            self.assertEqual(self.env.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation'"),[(0,)])

    def test_receipt_and_link_require_the_complete_published_bundle_and_correct_folder(self):
        with dav_server(self.responses()) as (base,seen),self.configured(base):
            response=self.confirm(); self.assertEqual(response.status_code,200,response.json)
            receipt=response.json['action']['receipt']; file_id=receipt['workspace_file_id']
            with self.server.app.test_client() as client:
                wrong=receipt['product_link'].replace(self.env.folder,str(uuid4()))
                self.assertEqual(client.get(wrong).status_code,404)
                self.assertEqual(client.get(receipt['product_link']+'?path=../../escape').status_code,400)
                with self.conn() as conn:conn.execute('DELETE FROM document_revision_renders')
                result=client.get('/api/document-workshop/actions/'+self.env.request_turn).json['action']
                self.assertEqual(result['state'],'remote_uncertain'); self.assertNotIn('receipt',result)
                self.assertEqual(client.get(receipt['product_link']).status_code,503)
            self.assertEqual(len([r for r in seen if r[0]=='PUT']),1)

    def test_latest_receipt_is_scope_bound_metadata_only_and_never_reads_dav(self):
        with dav_server(self.responses()) as (base,seen),self.configured(base):
            response=self.confirm(); self.assertEqual(response.status_code,200,response.json)
            before=len(seen)
            with patch.object(self.env.store,'verify_committed_action',side_effect=AssertionError('no document reread in next-turn metadata')):
                receipt=self.receipts.latest(self.env.conversation,self.env.folder)
            self.assertEqual(receipt,response.json['action']['receipt'])
            self.assertIsNone(self.receipts.latest(str(uuid4()),self.env.folder))
            self.assertIsNone(self.receipts.latest(self.env.conversation,str(uuid4())))
            self.assertEqual(len(seen),before)
            self.assertEqual(self.env.rows('SELECT count(*) FROM document_receipts'),[(1,)])
            self.assertEqual(self.env.rows("SELECT count(*) FROM conversation_messages WHERE role='tool'"),[(0,)])

    def test_inventory_sql_read_failure_is_unavailable_not_an_empty_success(self):
        with self.conn() as conn:
            conn.execute('ALTER TABLE workspace_files RENAME COLUMN byte_size TO unreadable_byte_size')
        with self.server.app.test_client() as client:
            response=client.get('/api/workspace-folders/'+self.env.folder+'/files')
        self.assertEqual(response.status_code,503,response.json)
        self.assertFalse(response.json['ok']); self.assertNotIn('items',response.json)

    def test_link_folder_sql_failure_is_unavailable_and_not_a_missing_file(self):
        with dav_server(self.responses()) as (base,seen),self.configured(base):
            receipt=self.confirm().json['action']['receipt']
            with self.conn() as conn:
                conn.execute('ALTER TABLE workspace_folders RENAME COLUMN display_name TO unreadable_name')
            response=self.server.app.test_client().get(receipt['product_link'])
            self.assertEqual(response.status_code,503,response.json)
            self.assertEqual(len([r for r in seen if r[0]=='PUT']),1)

    def test_default_wiring_verifies_a_real_commit_after_lost_ack_without_delete_or_retry(self):
        factory=self.conn; lost=[]
        class LostReply:
            def __init__(inner):inner.real=factory();inner.published=False
            def __enter__(inner):return inner
            def __getattr__(inner,key):return getattr(inner.real,key)
            def execute(inner,query,args=()):
                if "SET state='succeeded',phase='complete'" in query:inner.published=True
                return inner.real.execute(query,args)
            def __exit__(inner,kind,value,tb):
                if kind is None and inner.published and not lost:
                    inner.real.commit();inner.real.close();lost.append(True)
                    raise OSError('synthetic lost acknowledgement')
                return inner.real.__exit__(kind,value,tb)
        with dav_server(self.responses()) as (base,seen),self.configured(base),patch.object(self.env.store,'_db_conn',lambda:LostReply()):
            response=self.confirm();self.assertEqual(response.status_code,200,response.json)
            receipt=response.json['action']['receipt']
            self.assertEqual(self.server.app.test_client().get(receipt['product_link']).data,self.content())
            self.assertEqual(lost,[True]);self.assertEqual([r[0] for r in seen if r[0] in ('PUT','DELETE')],['PUT'])
            self.assertEqual(self.confirm().json['action']['receipt'],receipt)

    def test_missing_immutable_receipt_trigger_refuses_capability_before_effect(self):
        with dav_server([]) as (base,seen),self.configured(base):
            with self.conn() as conn:conn.execute('DROP TRIGGER document_execution_immutable ON document_receipts')
            self.assertIsNone(self.runtime.get_executor())
            self.assertEqual(self.confirm().status_code,503)
            self.assertEqual(seen,[])
            self.assertEqual(self.env.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation'"),[(0,)])

    def test_missing_publication_link_column_refuses_before_claim_or_dav(self):
        with dav_server([]) as (base,seen),self.configured(base):
            with self.conn() as conn:conn.execute('ALTER TABLE workspace_file_nextcloud_links RENAME COLUMN document_origin TO missing_origin')
            self.assertIsNone(self.runtime.get_executor())
            self.assertEqual(self.confirm().status_code,503)
            self.assertEqual(seen,[])
            self.assertEqual(self.env.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation'"),[(0,)])

    def test_link_active_folder_with_unavailable_sync_is_503_not_missing(self):
        with dav_server(self.responses()) as (base,seen),self.configured(base):
            receipt=self.confirm().json['action']['receipt']
            with self.conn() as conn:conn.execute("UPDATE workspace_folder_nextcloud_links SET nextcloud_sync_state='sync_error' WHERE workspace_folder_id=%s",(self.env.folder,))
            response=self.server.app.test_client().get(receipt['product_link'])
            self.assertEqual(response.status_code,503,response.json)
            self.assertEqual(len([r for r in seen if r[0]=='PUT']),1)

    def test_missing_conversation_scope_trigger_refuses_before_claim_or_dav(self):
        with dav_server([]) as (base,seen),self.configured(base):
            with self.conn() as conn:conn.execute('DROP TRIGGER workshop_scope_change ON conversations')
            self.assertIsNone(self.runtime.get_executor())
            self.assertEqual(self.confirm().status_code,503)
            self.assertEqual(seen,[])
            self.assertEqual(self.env.rows("SELECT count(*) FROM conversation_turn_claims WHERE kind='confirmation'"),[(0,)])
