"""Real PostgreSQL plus real urllib DAV, on isolated synthetic proof resources."""
import hashlib
import importlib
import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import psycopg
from psycopg.rows import dict_row
from core import document_workshop_contexts as contexts, workspace_files, workspace_folders
from core.workspace_folder_nextcloud_client import NextcloudFolderClientConfig
from core.workspace_document_nextcloud_read_client import NextcloudDocumentReadClient, RemoteResource
from core.document_workshop_contract import DocumentWorkshopError
from core.workspace_document_source_extraction import extract_complete_source
from tests.unit.core.test_workspace_document_read_client_m2 import dav_server, resource, multistatus
from tests.test_server_document_workshop_contexts_contract import CONV, FOLDER, OTHER, FILE


@unittest.skipUnless(os.environ.get('M2_PROOF_PG_SOCKET'), 'explicit isolated PostgreSQL proof runner required')
class AdoptionPostgresqlTests(unittest.TestCase):
    def connection(self):
        return psycopg.connect(host=os.environ['M2_PROOF_PG_SOCKET'], dbname='m1proof', user='m1proof')

    def setUp(self):
        for name in ('workspace_document_adoption_service', 'workspace_document_adoption_store', 'workspace_document_content_service'):
            self.assertIsNotNone(importlib.util.find_spec('core.' + name), 'M2 interface absent')
        self.store = importlib.import_module('core.workspace_document_adoption_store')
        self.service = importlib.import_module('core.workspace_document_adoption_service')
        self.content = importlib.import_module('core.workspace_document_content_service')
        with self.connection() as conn:
            conn.execute('DROP SCHEMA public CASCADE; CREATE SCHEMA public')
            conn.execute('''CREATE TABLE workspace_folders (id uuid PRIMARY KEY, display_name text, icon_key text DEFAULT '', description text DEFAULT '', sort_order int DEFAULT 0, created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now(), deleted_at timestamptz);
                CREATE TABLE conversations (id uuid PRIMARY KEY, workspace_folder_id uuid, deleted_at timestamptz);
                CREATE TABLE workspace_folder_nextcloud_links (workspace_folder_id uuid PRIMARY KEY, nextcloud_sync_state text, nextcloud_folder_ref text DEFAULT '', nextcloud_name_hash text DEFAULT '', last_sync_at timestamptz, last_sync_reason_code text DEFAULT '', last_sync_operation text, nextcloud_share_state text DEFAULT 'unknown', created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now());
                CREATE TABLE workspace_files (id uuid PRIMARY KEY, workspace_folder_id uuid REFERENCES workspace_folders(id), display_name text NOT NULL, original_filename text NOT NULL DEFAULT '', storage_key text NOT NULL UNIQUE, content_kind text NOT NULL DEFAULT 'document', media_kind text NOT NULL DEFAULT 'text', mime_type text, source_extension text, byte_size bigint, sha256 text, sha256_12 text, text_chars int, text_sha256_12 text, image_width int DEFAULT 0, image_height int DEFAULT 0, status text, reason_code text DEFAULT '', source_kind text, source_file_id uuid, created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now(), deleted_at timestamptz);
                CREATE TABLE workspace_file_nextcloud_links (workspace_file_id uuid PRIMARY KEY REFERENCES workspace_files(id), workspace_folder_id uuid REFERENCES workspace_folders(id), nextcloud_sync_state text, nextcloud_target_name text, nextcloud_document_ref text, nextcloud_name_hash text DEFAULT '', last_sync_at timestamptz, last_sync_reason_code text DEFAULT '', last_sync_operation text, created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now());''')
            conn.execute("INSERT INTO workspace_folders(id,display_name) VALUES (%s,'Scope'),(%s,'Other')", (FOLDER, OTHER))
            conn.execute("INSERT INTO workspace_folder_nextcloud_links(workspace_folder_id,nextcloud_sync_state,nextcloud_folder_ref) VALUES (%s,'linked','workspace:test')", (FOLDER,))
            conn.execute('INSERT INTO conversations VALUES (%s,%s,NULL)', (CONV,FOLDER))
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for module in (contexts, workspace_files, workspace_folders, self.store):
            p = patch.object(module, '_db_conn', self.connection); p.start(); self.addCleanup(p.stop)
        p = patch.object(workspace_files, '_storage_root', lambda: self.root); p.start(); self.addCleanup(p.stop)
        contexts.init_db(); self.store.init_db(); self.store.init_db()
        self.context = contexts.create_context(conversation_id=CONV, workspace_folder_id=FOLDER)
        self.deps = dict(store=contexts, conversations=SimpleNamespace(get_conversation_summary=self.conversation), folders=workspace_folders, files=workspace_files, adoption_store=self.store)
        self.refs = self.service.RemoteReferences()

    def conversation(self, _):
        with self.connection() as conn:
            row = conn.execute('SELECT id::text,workspace_folder_id::text,deleted_at FROM conversations WHERE id=%s', (CONV,)).fetchone()
            return dict(zip(('id','workspace_folder_id','deleted_at'),row)) if row else None

    def client(self, base):
        return NextcloudDocumentReadClient(NextcloudFolderClientConfig(base, 'test', 'synthetic'))

    def listing(self, client, collection_ref=None):
        return self.service.list_remote(FOLDER, dict(context_id=self.context['id'], **({'collection_ref':collection_ref} if collection_ref else {})), reader=client, references=self.refs, **self.deps)

    def adopt(self, client, ref):
        return self.service.adopt_remote(FOLDER, dict(context_id=self.context['id'], resource_ref=ref), reader=client, references=self.refs, **self.deps)

    def responses(self, *, path='Documents/a.md', data=b'abc', etag='"v1"', file_id='42', include_listing=True):
        node = resource(path, collection=False, file_id=file_id, etag=etag, size=len(data), media_type='text/markdown')
        responses = [(207, {}, multistatus(resource(), node))] if include_listing else []
        return responses + [(207, {}, multistatus(node)), (200, {'ETag':etag,'Content-Length':str(len(data))}, data), (207, {}, multistatus(node))]

    def rows(self):
        with self.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute('SELECT wf.*,to_jsonb(l) AS link FROM workspace_files wf LEFT JOIN workspace_file_nextcloud_links l ON l.workspace_file_id=wf.id')
                return cur.fetchall()

    def test_folder_listing_keeps_order_projection_and_deleted_filter(self):
        with self.connection() as conn:
            conn.execute('UPDATE workspace_folders SET sort_order=CASE WHEN id=%s THEN 1 ELSE 2 END', (OTHER,))
        folders = workspace_folders.list_workspace_folders()
        self.assertEqual([item['id'] for item in folders], [OTHER, FOLDER])
        self.assertEqual(folders[1]['nextcloud_sync_state'], 'linked')
        self.assertEqual(folders[1]['display_name'], 'Scope')
        with self.connection() as conn:
            conn.execute('UPDATE workspace_folders SET deleted_at=now() WHERE id=%s', (OTHER,))
        self.assertEqual([item['id'] for item in workspace_folders.list_workspace_folders()], [FOLDER])
        self.assertEqual([item['id'] for item in workspace_folders.list_workspace_folders(include_deleted=True)], [OTHER, FOLDER])

    def test_real_sql_listing_error_is_explicit_and_recovers_without_retry(self):
        from core.workspace_folders_store import WorkspaceFolderListError, REASON_LIST_FAILED
        from tests.support.server_test_bootstrap import load_server_module_for_tests
        server = load_server_module_for_tests()
        # Only this dedicated proof schema is changed. The normal SELECT now
        # raises PostgreSQL UndefinedColumn, rather than a mocked service result.
        with self.connection() as conn:
            conn.execute('ALTER TABLE workspace_folders RENAME COLUMN sort_order TO unreadable_sort_order')
        with self.assertRaises(WorkspaceFolderListError) as failure:
            workspace_folders.list_workspace_folders()
        self.assertIsInstance(failure.exception.__cause__, psycopg.errors.UndefinedColumn)
        with patch.object(server, 'workspace_folders', workspace_folders):
            response = server.app.test_client().get('/api/workspace-folders')
            self.assertEqual(response.status_code, 503)
            self.assertFalse(response.get_json()['ok'])
            self.assertEqual(response.get_json()['reason_code'], REASON_LIST_FAILED)
            self.assertNotIn('items', response.get_json())
            self.assertNotIn('sort_order', response.get_data(as_text=True))
            with self.connection() as conn:
                conn.execute('ALTER TABLE workspace_folders RENAME COLUMN unreadable_sort_order TO sort_order')
            recovered = server.app.test_client().get('/api/workspace-folders')
        self.assertEqual(recovered.status_code, 200)
        self.assertTrue(recovered.get_json()['ok'])
        self.assertEqual({item['id'] for item in recovered.get_json()['items']}, {FOLDER, OTHER})

    def test_complete_transport_adoption_and_fresh_read_use_one_identity(self):
        fresh = self.responses(include_listing=False)
        responses = self.responses() + self.responses() + [fresh[0]] + fresh
        with dav_server(responses) as (base, seen):
            client = self.client(base)
            listing,status = self.listing(client); self.assertEqual(status,200)
            self.assertEqual(listing['items'][0]['category'],'adoptable')
            adopted,status = self.adopt(client,listing['items'][0]['reference']); self.assertEqual(status,201)
            listing,status = self.listing(client); self.assertEqual(listing['items'][0]['category'],'already_linked')
            again,status = self.adopt(client,listing['items'][0]['reference']); self.assertEqual(status,200)
            self.assertEqual(again['workspace_file_id'],adopted['workspace_file_id'])
            source = self.content.read_workspace_document_source(FOLDER,adopted['workspace_file_id'],reader=client,folders=workspace_folders,files=workspace_files)
            self.assertEqual(source.text,'abc')
            self.assertEqual(source.sha256,hashlib.sha256(b'abc').hexdigest())
        self.assertEqual(len(self.rows()),1)
        row = self.rows()[0]
        self.assertEqual((self.root/row['storage_key']).read_bytes(),b'abc')
        self.assertEqual(row['link']['nextcloud_relative_path'],'Documents/a.md')
        self.assertEqual(row['link']['document_origin'],'external')
        self.assertEqual([m for m,_,_ in seen].count('GET'),3)
        self.assertTrue(all(m in ('GET','PROPFIND') for m,_,_ in seen))
        self.assertEqual([h.get('Depth') for m,_,h in seen if m=='PROPFIND'].count('1'),2)
        self.assertTrue(all(h.get('If-Match')=='"v1"' for m,_,h in seen if m=='GET'))

    def test_sql_failure_after_file_insert_rolls_back_both_and_owned_cache(self):
        with self.connection() as conn:
            conn.execute("CREATE FUNCTION fail_link() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic'; END $$; CREATE TRIGGER fail_link BEFORE INSERT ON workspace_file_nextcloud_links FOR EACH ROW EXECUTE FUNCTION fail_link()")
        with dav_server(self.responses()) as (base,seen):
            client=self.client(base); listing,_=self.listing(client)
            payload,status=self.adopt(client,listing['items'][0]['reference'])
        self.assertEqual(status,503); self.assertFalse(payload['ok'])
        self.assertEqual(self.rows(),[]); self.assertEqual([p for p in self.root.rglob('*') if p.is_file()],[])
        self.assertFalse(any(m in ('PUT','DELETE','MKCOL') for m,_,_ in seen))

    def test_same_etag_different_bytes_conflicts_and_preserves_previous_cache(self):
        fresh = self.responses(data=b'xyz',include_listing=False)
        with dav_server(self.responses()+self.responses(data=b'xyz')+[fresh[0]]+fresh) as (base,_):
            client=self.client(base); listing,_=self.listing(client); first,status=self.adopt(client,listing['items'][0]['reference']); self.assertEqual(status,201)
            old=self.rows()[0]
            listing,_=self.listing(client); payload,status=self.adopt(client,listing['items'][0]['reference'])
            self.assertEqual(status,409); self.assertEqual(payload['reason_code'],'document_remote_changed')
            with self.assertRaises(DocumentWorkshopError) as failure:
                self.content.read_workspace_document_source(FOLDER,first['workspace_file_id'],reader=client,folders=workspace_folders,files=workspace_files)
            self.assertEqual(failure.exception.reason_code,'document_remote_changed')
        new=self.rows()[0]; self.assertEqual(new['storage_key'],old['storage_key'])
        self.assertEqual(new['sha256'],old['sha256']); self.assertEqual((self.root/old['storage_key']).read_bytes(),b'abc')

    def test_new_etag_updates_observation_without_id_change_and_keeps_old_revision(self):
        with dav_server(self.responses()+self.responses(data=b'changed',etag='"v2"')) as (base,_):
            client=self.client(base); listing,_=self.listing(client); first,_=self.adopt(client,listing['items'][0]['reference']); old=self.rows()[0]
            listing,_=self.listing(client); updated,status=self.adopt(client,listing['items'][0]['reference'])
        self.assertEqual(status,200); self.assertEqual(first['workspace_file_id'],updated['workspace_file_id'])
        new=self.rows()[0]; self.assertNotEqual(old['storage_key'],new['storage_key'])
        self.assertEqual((self.root/old['storage_key']).read_bytes(),b'abc'); self.assertEqual((self.root/new['storage_key']).read_bytes(),b'changed')

    def test_transport_or_extraction_failure_never_publishes_partial_rows(self):
        for tail,reason in [([(412,{},b'')],'document_remote_changed'),
                (self.responses(data=b'a\x00c',include_listing=False),'document_parse_error')]:
            with self.subTest(reason=reason), dav_server([self.responses()[0]]+tail) as (base,_):
                client=self.client(base); listing,_=self.listing(client); payload,status=self.adopt(client,listing['items'][0]['reference'])
                self.assertFalse(payload['ok']); self.assertEqual(payload['reason_code'],reason)
                self.assertEqual(self.rows(),[])

    def test_context_or_mapping_changed_after_download_rejected_inside_transaction(self):
        for update in ("UPDATE conversations SET deleted_at=now()", "UPDATE workspace_folders SET display_name='Moved'"):
            with self.subTest(update=update):
                responses=self.responses()
                with dav_server(responses) as (base,_):
                    client=self.client(base); listing,_=self.listing(client)
                    real=client.read_file
                    def read(*a):
                        data=real(*a)
                        with self.connection() as conn: conn.execute(update)
                        return data
                    with patch.object(client,'read_file',side_effect=read):
                        payload,status=self.adopt(client,listing['items'][0]['reference'])
                self.assertEqual(status,409); self.assertEqual(self.rows(),[])
                with self.connection() as conn:
                    conn.execute('UPDATE conversations SET deleted_at=NULL'); conn.execute("UPDATE workspace_folders SET display_name='Scope' WHERE id=%s",(FOLDER,))

    def test_nested_path_m1_service_and_sql_identity_guard(self):
        self.assertTrue(hasattr(self.store,'publish_adoption'))
        client=self.client('http://synthetic.invalid')
        observation=RemoteResource('Documents/Nested/Épreuve  double.md',False,'42','"v1"',3,'text/markdown')
        result=self.publish(client,observation)
        file_id=result['file']['id']
        from core import document_workshop_context_service as context_service
        payload,status=context_service.create_context(dict(conversation_id=CONV,workspace_folder_id=FOLDER,target_file_id=file_id),**{k:v for k,v in self.deps.items() if k!='adoption_store'})
        self.assertEqual(status,201); self.assertEqual(payload['context']['target_relative_path'],observation.relative_path)
        saved=contexts.get_context(payload['context']['id'])
        with self.connection() as conn: conn.execute("UPDATE workspace_file_nextcloud_links SET nextcloud_file_id='43'")
        self.assertEqual(context_service.get_context(saved['id'],**{k:v for k,v in self.deps.items() if k!='adoption_store'})[1],409)
        self.assertIsNone(contexts.create_context(conversation_id=CONV,workspace_folder_id=FOLDER,target_file_id=file_id,
            target_relative_path=saved['target_relative_path'],target_document_ref=saved['target_document_ref'],target_remote_identity=saved['target_remote_identity']))

    def publish(self, client, observation, data=b'abc'):
        return self.store.publish_adoption(folder_id=FOLDER,context_id=self.context['id'],folder=workspace_folders.get_workspace_folder(FOLDER),
            scope_key=client.scope_key('Scope'),resource=observation,content=data,extraction=extract_complete_source(data,filename=observation.relative_path.split('/')[-1]),storage_root=self.root)

    def test_concurrent_same_identity_commits_once_and_sql_uniqueness_survives_tombstone(self):
        client=self.client('http://synthetic.invalid'); observation=RemoteResource('Documents/a.md',False,'42','"v1"',3,'text/markdown')
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.publish(client,observation),range(2)))
        self.assertEqual(results[0]['file']['id'],results[1]['file']['id']); self.assertEqual(len(self.rows()),1)
        with self.connection() as conn: conn.execute("UPDATE workspace_files SET deleted_at=now(),status='deleted'")
        with self.assertRaises(DocumentWorkshopError): self.publish(client,observation)
        with self.connection() as conn:
            conn.execute("INSERT INTO workspace_files(id,workspace_folder_id,display_name,storage_key) VALUES (%s,%s,'synthetic','synthetic-unused')",(FILE,FOLDER))
            with self.assertRaises(psycopg.errors.UniqueViolation):
                conn.execute("INSERT INTO workspace_file_nextcloud_links(workspace_file_id,workspace_folder_id,nextcloud_scope_key,nextcloud_file_id) SELECT %s,workspace_folder_id,nextcloud_scope_key,nextcloud_file_id FROM workspace_file_nextcloud_links",(FILE,))

    def test_unicode_case_collision_and_explicit_move_keep_identity(self):
        client=self.client('http://synthetic.invalid'); first=RemoteResource('Documents/Épreuve.md',False,'42','"v1"',3,'text/markdown')
        result=self.publish(client,first)
        with self.assertRaises(DocumentWorkshopError) as failure:
            self.publish(client,RemoteResource('Documents/E\u0301PREUVE.md',False,'43','"v1"',3,'text/markdown'))
        self.assertEqual(failure.exception.reason_code,'document_local_collision')
        moved=self.publish(client,RemoteResource('Documents/Nested/renamed.md',False,'42','"v1"',3,'text/markdown'))
        self.assertEqual(result['file']['id'],moved['file']['id']); self.assertEqual(len(self.rows()),1)

    def test_preexisting_legacy_link_binds_only_exact_path_and_complete_byte_hash(self):
        from core import workspace_files_store, workspace_file_nextcloud_links_store
        item = workspace_files_store.store_uploaded_file(FOLDER,original_filename='a.md',content=b'abc',metadata={'text_chars':3},db_conn_func=self.connection,storage_root=self.root,logger=None)
        workspace_file_nextcloud_links_store.upsert_link(workspace_file_id=item['id'],workspace_folder_id=FOLDER,nextcloud_sync_state='linked',nextcloud_document_ref='workspace-file:legacy',nextcloud_name_hash='',nextcloud_target_name='a.md',last_sync_reason_code='folder_document_list_ok',last_sync_operation='upload',db_conn_func=self.connection,logger=None)
        with dav_server(self.responses(data=b'xyz')+self.responses()) as (base,_):
            client=self.client(base); listing,_=self.listing(client)
            self.assertEqual(listing['items'][0]['reason_code'],'legacy_verification_required')
            failed,status=self.adopt(client,listing['items'][0]['reference']); self.assertEqual(status,409)
            self.assertIsNone(self.rows()[0]['link']['nextcloud_file_id'])
            listing,_=self.listing(client); adopted,status=self.adopt(client,listing['items'][0]['reference'])
        self.assertEqual(status,200); self.assertEqual(adopted['workspace_file_id'],item['id'])
        self.assertEqual(self.rows()[0]['link']['nextcloud_file_id'],'42')
        self.assertIsNone(self.rows()[0]['link']['document_origin'])

    def test_reference_wrong_folder_mapping_eviction_and_directory_replacement_refuse(self):
        body=multistatus(resource(),resource('Documents/Nested',file_id='12'))
        with dav_server([(207,{},body),(207,{},multistatus(resource('Documents/Nested',file_id='13')))]) as (base,seen):
            client=self.client(base); listing,status=self.listing(client); self.assertEqual(status,200)
            ref=listing['items'][0]['reference']
            with self.assertRaises(DocumentWorkshopError): self.refs.resolve(ref,OTHER,client.scope_key('Scope'))
            with self.assertRaises(DocumentWorkshopError): self.refs.resolve(ref,FOLDER,client.scope_key('Changed'))
            payload,status=self.listing(client,ref); self.assertEqual(status,409)
            self.assertFalse(payload['ok']); self.assertNotIn('items',payload)
        self.assertEqual([h.get('Depth') for _,_,h in seen],['1','1'])
        for _ in range(4096): self.refs.put(FOLDER,client.scope_key('Scope'),RemoteResource('Documents',True,'1','',None,''))
        with self.assertRaises(DocumentWorkshopError): self.refs.resolve(ref,FOLDER,client.scope_key('Scope'))

    def test_missing_migration_is_controlled_without_any_dav(self):
        with self.connection() as conn: conn.execute('ALTER TABLE workspace_file_nextcloud_links DROP COLUMN nextcloud_file_id CASCADE')
        with dav_server([]) as (base,seen):
            payload,status=self.listing(self.client(base))
        self.assertEqual(status,503); self.assertFalse(payload['ok']); self.assertEqual(seen,[])
        with self.connection() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM information_schema.columns WHERE table_name='workspace_file_nextcloud_links' AND column_name='nextcloud_file_id'").fetchone()[0],0)

    def test_failed_refresh_keeps_old_row_hash_and_bytes(self):
        with dav_server(self.responses()+self.responses(etag='"v2"',data=b'xyz')) as (base,_):
            client=self.client(base); listing,_=self.listing(client); self.assertEqual(self.adopt(client,listing['items'][0]['reference'])[1],201)
            old=self.rows()[0]
            with self.connection() as conn:
                conn.execute("CREATE FUNCTION fail_update() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic'; END $$; CREATE TRIGGER fail_update BEFORE UPDATE ON workspace_file_nextcloud_links FOR EACH ROW EXECUTE FUNCTION fail_update()")
            listing,_=self.listing(client); payload,status=self.adopt(client,listing['items'][0]['reference'])
        self.assertEqual(status,503)
        self.assertEqual(self.rows()[0],old)
        self.assertEqual((self.root/old['storage_key']).read_bytes(),b'abc')
        self.assertEqual(len([p for p in self.root.rglob('*') if p.is_file()]),1)

    def test_uncertain_commit_preserves_the_cache_of_a_possibly_published_row(self):
        connection=self.connection
        class LostAcknowledgement:
            def __enter__(self):
                self.conn=connection(); self.conn.__enter__(); return self.conn
            def __exit__(self,*args):
                self.conn.__exit__(*args)
                if args[0] is None: raise OSError('synthetic acknowledgement lost')
        # Only publication's transaction loses its acknowledgement, not preliminary reads.
        calls=0
        def factory():
            nonlocal calls
            calls+=1
            return LostAcknowledgement() if calls==2 else connection()
        client=self.client('http://synthetic.invalid')
        with patch.object(self.store,'_db_conn',side_effect=factory):
            with self.assertRaises(DocumentWorkshopError) as failure:
                self.publish(client,RemoteResource('Documents/a.md',False,'42','"v1"',3,'text/markdown'))
        self.assertEqual(failure.exception.reason_code,'document_adoption_commit_unknown')
        row=self.rows()[0]
        self.assertEqual((self.root/row['storage_key']).read_bytes(),b'abc')

    def test_mounted_flask_routes_compose_the_real_reader_and_transactional_store(self):
        from tests.support.server_test_bootstrap import load_server_module_for_tests
        server=load_server_module_for_tests()
        with patch.object(server,'document_workshop_contexts',contexts), patch.object(server,'workspace_folders',workspace_folders), patch.object(server,'workspace_files',workspace_files), patch.object(server.conv_store,'get_conversation_summary',side_effect=self.conversation), dav_server(self.responses()) as (base,seen):
            with patch.object(self.service.NextcloudDocumentReadClient,'from_env',side_effect=lambda:self.client(base)):
                browser=server.app.test_client()
                listing=browser.get(f'/api/workspace-folders/{FOLDER}/documents/remote?context_id={self.context["id"]}')
                self.assertEqual(listing.status_code,200)
                result=browser.post(f'/api/workspace-folders/{FOLDER}/documents/adopt',json=dict(context_id=self.context['id'],resource_ref=listing.json['items'][0]['reference']))
                self.assertEqual(result.status_code,201)
                inventory=browser.get(f'/api/workspace-folders/{FOLDER}/files')
                self.assertEqual(inventory.status_code,200)
                self.assertEqual(inventory.json['items'][0]['document_relative_path'],'Documents/a.md')
        self.assertEqual(len(self.rows()),1)
        self.assertEqual([m for m,_,_ in seen],['PROPFIND','PROPFIND','GET','PROPFIND'])

    def test_fresh_21_page_source_enters_complete_m0_estimation_without_transport(self):
        import json
        from core import llm_client, token_utils
        from core.document_workshop_admission import prepare_document_call
        from tests.unit.core.test_workspace_document_source_extraction_m2 import pdf_bytes
        data=pdf_bytes(21)
        fresh=self.responses(path='Documents/source.pdf',data=data,include_listing=False)
        with dav_server(self.responses(path='Documents/source.pdf',data=data)+[fresh[0]]+fresh) as (base,_):
            client=self.client(base); listing,_=self.listing(client); adopted,status=self.adopt(client,listing['items'][0]['reference'])
            self.assertEqual(status,201)
            source=self.content.read_workspace_document_source(FOLDER,adopted['workspace_file_id'],reader=client,folders=workspace_folders,files=workspace_files)
        for page in range(1,22): self.assertIn(f'Synthetic page {page}',source.text)
        messages=[{'role':'system','content':'Synthetic documentary instructions'},
            {'role':'user','content':'Complete synthetic prior dialogue'},
            {'role':'assistant','content':'Complete synthetic prior response'},
            {'role':'system','content':json.dumps({'etag':source.etag,'hash':source.sha256,'path':source.relative_path})},
            {'role':'user','content':source.text}, {'role':'user','content':'Another whole synthetic source'}]
        settings=SimpleNamespace(payload={'model':{'value':'openai/gpt-5.1'},'reasoning_effort':{'value':'medium'},'base_url':{'value':'https://provider.invalid/api/v1/'}})
        with patch.object(llm_client.runtime_settings,'get_main_model_settings',return_value=settings), patch.object(llm_client,'or_headers',return_value={'Content-Type':'application/json'}), patch.object(llm_client,'or_chat_completions_url',return_value='https://provider.invalid/api/v1/chat/completions'):
            prepared=prepare_document_call(messages,count_tokens_func=token_utils.estimate_tokens)
            payload=json.loads(prepared.body)
            self.assertEqual(payload['messages'][:-1],messages)
            self.assertEqual(prepared.admission.estimated_total_tokens,token_utils.estimate_tokens(payload['messages'],'openai/gpt-5.1')+24000)
            self.assertLessEqual(prepared.admission.estimated_total_tokens,400000)
            whole_text='x'*1_000_000
            extraction=extract_complete_source(whole_text.encode(),filename='large.md')
            source_only=prepare_document_call([{'role':'user','content':extraction.text}],count_tokens_func=token_utils.estimate_tokens)
            self.assertLessEqual(source_only.admission.estimated_total_tokens,400000)
            complete=messages+[{'role':'user','content':extraction.text},{'role':'assistant','content':'y'*500_000}]
            with self.assertRaises(DocumentWorkshopError) as failure:
                prepare_document_call(complete,count_tokens_func=token_utils.estimate_tokens)
            self.assertEqual(failure.exception.reason_code,'document_estimated_context_limit')
            self.assertEqual(len(complete[-2]['content']),1_000_000)

    def test_listing_four_categories_metadata_limits_and_no_download(self):
        nodes=[resource('Documents/a.md',collection=False,file_id='42'),
               resource('Documents/new.md',collection=False,file_id='50'),
               resource('Documents/A.md',collection=False,file_id='51'),
               resource('Documents/tool.exe',collection=False,file_id='52'),
               resource('Documents/weak.md',collection=False,file_id='53',etag='W/"v1"'),
               resource('Documents/no-id.md',collection=False,file_id=''),
               resource('Documents/ambiguous.md',collection=False,file_id='042'),
               resource('Documents/zero.md',collection=False,file_id='0'),
               resource('Documents/huge.md',collection=False,file_id='54',size=40*1024*1024+1)]
        with dav_server([(207,{},multistatus(resource(),*nodes))]) as (base,seen):
            client=self.client(base)
            self.publish(client,RemoteResource('Documents/a.md',False,'42','"v1"',3,'text/plain'))
            listing,status=self.listing(client)
            self.assertEqual(status,200); self.assertTrue(listing['complete'])
            self.assertEqual([item['category'] for item in listing['items']],['already_linked','adoptable','collision']+['incompatible']*6)
            for item in listing['items'][2:]:
                refused,status=self.adopt(client,item['reference'])
                self.assertIn(status,(409,413,422)); self.assertFalse(refused['ok'])
        self.assertEqual([m for m,_,_ in seen],['PROPFIND'])
        self.assertEqual(len(self.rows()),1)

    def test_oversized_collection_refuses_without_publishing_a_prefix(self):
        nodes=[resource(f'Documents/a{index}.md',collection=False,file_id=str(index+2)) for index in range(257)]
        with dav_server([(207,{},multistatus(resource(),*nodes))]) as (base,seen):
            result,status=self.listing(self.client(base))
        self.assertEqual(status,413); self.assertNotIn('items',result); self.assertNotIn('complete',result)
        self.assertEqual(self.rows(),[]); self.assertEqual(len(seen),1)

    def test_replaced_missing_or_changed_during_get_never_publish(self):
        original=self.responses()
        replacements=[[(404,{},b'')],[(207,{},multistatus(resource('Documents/a.md',collection=False,file_id='43',size=3,media_type='text/markdown')))],
            original[1:3]+[(207,{},multistatus(resource('Documents/a.md',collection=False,file_id='43',size=3,media_type='text/markdown')))]]
        for tail in replacements:
            with self.subTest(steps=len(tail)),dav_server([original[0]]+tail) as (base,_):
                client=self.client(base); listing,_=self.listing(client); result,status=self.adopt(client,listing['items'][0]['reference'])
                self.assertIn(status,(404,409)); self.assertFalse(result['ok']); self.assertEqual(self.rows(),[])
                self.assertEqual([p for p in self.root.rglob('*') if p.is_file()],[])

    def test_moved_stored_source_is_missing_without_tree_search(self):
        with dav_server(self.responses()+[(404,{},b'')]) as (base,seen):
            client=self.client(base); listing,_=self.listing(client); adopted,_=self.adopt(client,listing['items'][0]['reference'])
            with self.assertRaises(DocumentWorkshopError) as failure:
                self.content.read_workspace_document_source(FOLDER,adopted['workspace_file_id'],reader=client,folders=workspace_folders,files=workspace_files)
        self.assertEqual(failure.exception.reason_code,'document_remote_missing')
        self.assertEqual(len(seen),5); self.assertEqual(seen[-1][0],'PROPFIND'); self.assertEqual(seen[-1][2].get('Depth'),'0')
        self.assertTrue(seen[-1][1].endswith('/Documents/a.md'))

    def test_sql_rejects_noncanonical_identity_and_duplicate_active_path(self):
        client=self.client('http://synthetic.invalid')
        self.publish(client,RemoteResource('Documents/a.md',False,'42','"v1"',3,'text/markdown'))
        for value in ('0','042'):
            with self.connection() as conn:
                with self.assertRaises(psycopg.errors.CheckViolation):
                    conn.execute('UPDATE workspace_file_nextcloud_links SET nextcloud_file_id=%s',(value,))
        with self.connection() as conn:
            conn.execute("INSERT INTO workspace_files(id,workspace_folder_id,display_name,storage_key) VALUES (%s,%s,'synthetic','synthetic-unused')",(FILE,FOLDER))
            with self.assertRaises(psycopg.errors.UniqueViolation):
                conn.execute("INSERT INTO workspace_file_nextcloud_links(workspace_file_id,workspace_folder_id,nextcloud_collision_key,nextcloud_sync_state) VALUES (%s,%s,'documents/a.md','linked')",(FILE,FOLDER))

    def test_nested_navigation_is_lazy_and_adoption_keeps_exact_spelling(self):
        from urllib.parse import quote
        path='Documents/Nested/Épreuve  double.md'
        root=multistatus(resource(),resource('Documents/Nested',file_id='12'))
        child=resource(path,collection=False,file_id='42',size=3,media_type='text/markdown')
        nested=multistatus(resource('Documents/Nested',file_id='12'),child)
        with dav_server([(207,{},root),(207,{},nested)]+self.responses(path=path,include_listing=False)) as (base,seen):
            client=self.client(base); listing,status=self.listing(client); self.assertEqual(status,200)
            self.assertEqual(len(seen),1)
            nested_listing,status=self.listing(client,listing['items'][0]['reference']); self.assertEqual(status,200)
            self.assertEqual([m for m,_,_ in seen],['PROPFIND','PROPFIND'])
            self.assertEqual(nested_listing['items'][0]['relative_path'],path)
            adopted,status=self.adopt(client,nested_listing['items'][0]['reference']); self.assertEqual(status,201)
            self.assertEqual(adopted['file']['display_name'],'Épreuve  double.md')
            self.assertEqual(adopted['file']['document_relative_path'],path)
        self.assertEqual([h.get('Depth') for m,_,h in seen if m=='PROPFIND'],['1','1','0','0'])
        self.assertEqual([p for m,p,_ in seen if m=='GET'][0],'/remote.php/dav/files/test/Frida/Scope/'+quote(path,safe='/'))
