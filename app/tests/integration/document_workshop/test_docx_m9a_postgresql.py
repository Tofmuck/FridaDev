"""Actual M9-A composition: SQL, Flask, DAV HTTP and qualified ephemeral Writer.

No format override, executor subclass, fake rendered bytes or provider call.
"""
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4
import zipfile
from xml.etree import ElementTree as ET

from core import document_workshop_actions as actions, document_workshop_contexts as contexts
from core import document_workshop_runtime as runtime, document_workshop_receipts as receipts
from core import document_workshop_execution_store as store, document_renderer_store as snapshots
from core import workspace_files, conv_store, conversation_turn_claims as claims
from core import workspace_document_content_service as sources
from core.document_markdown import serialize_markdown
from core.document_workshop_contract import DocumentWorkshopError
from core.document_workshop_envelope import read_document_envelope
from tests.integration.document_workshop import test_execution_postgresql as fixture
from tests.support.document_workshop_docx_dav import docx_dav
from tests.support.server_test_bootstrap import load_server_module_for_tests
from tests.unit.core.test_document_workshop_canonical_paths import canonical, span


def rich():
    value = canonical('Français éè, ligature œ et Unicode.')
    value['blocks'] += [dict(type='heading',level=2,spans=[span('Titre structuré')]),
        dict(type='paragraph',spans=[span('Gras')|dict(bold=True),span(' et italique')|dict(italic=True),
            span(' Lien')|dict(link='https://example.invalid/passive')]),
        dict(type='quote',spans=[span('Citation')]),
        dict(type='list',ordered=True,items=[[span('Premier')],[span('Second')]]),
        dict(type='list',ordered=False,items=[[span('Puce')]]),
        dict(type='table',rows=[[[span('A')],[span('B')]],[[span('C')],[span('D')]]])]
    return value


@unittest.skipUnless(os.environ.get('M5_PROOF_PG_SOCKET'), 'isolated PostgreSQL required')
class DocxM9APostgresqlTests(unittest.TestCase):
    def setUp(self):
        self.fx=fixture.ExecutionPostgresqlTests('runTest'); self.fx.setUp(); self.addCleanup(self.fx.doCleanups)
        self.conn=self.fx.conn; self.folder=self.fx.folder; self.conversation=self.fx.conversation
        self.migration=Path(__file__).parents[3]/'core/sql/document_workshop_docx_m9a.sql'
        self.assertTrue(self.migration.exists(),'explicit additive M9-A migration missing')
        with self.conn() as conn:
            conn.execute((self.migration.parent/'document_workshop_update_m7.sql').read_text())
            conn.execute(self.migration.read_text())
        self.server=load_server_module_for_tests()
        self.base,self.dav=self.enterContext(docx_dav())
        password=self.fx.env.root/'synthetic-password'; password.write_text('synthetic-only')
        self.enterContext(patch.dict(os.environ,dict(FRIDA_NEXTCLOUD_BASE_URL=self.base,
            FRIDA_NEXTCLOUD_USERNAME='test',FRIDA_NEXTCLOUD_ROOT_NAME='Frida',FRIDA_NEXTCLOUD_APP_PASSWORD_FILE=str(password))))
        self.client=self.server.app.test_client()
        from core.document_rendering import RenderingSession
        from core.document_renderer_contract import RendererError
        actual_collect=RenderingSession.collect
        def collect(session,*args,**kwargs):
            try:return actual_collect(session,*args,**kwargs)
            except RendererError as error:
                print('M9A renderer refusal:',error.reason_code,flush=True)
                raise
        self.enterContext(patch.object(RenderingSession,'collect',collect))

    def prepare(self, *, operation='create', target=None, source=None, value=None, path='Documents/M9.docx'):
        context=self.client.post('/api/document-workshop/contexts',json=dict(conversation_id=self.conversation,
            workspace_folder_id=self.folder,**(dict(target_file_id=target) if target else {})))
        self.assertEqual(context.status_code,201,context.json)
        ctx=context.json['context']; self.assertIn('docx',ctx['capabilities']['formats'])
        action_id=str(uuid4()); token=claims.acquire(conversation_id=self.conversation,turn_id=action_id,
            request_fingerprint='b'*64,kind='preparation',context_id=ctx['id']).token
        conversation=conv_store.load_conversation(self.conversation,'Synthetic system')
        conversation['messages'].append(dict(role='user',content='Explicit synthetic '+operation,
            timestamp='2026-10-10T00:00:00Z',meta={'client_turn_id':action_id}))
        ids=[source] if source else []
        actions.save_initial(token,conversation,ids,snapshot=self.fx.snapshot)
        observations=[sources.read_workspace_document_source(self.folder,i) for i in ids]
        versions=[{k:getattr(s,k) for k in ('workspace_file_id','remote_identity','etag','sha256','relative_path','observed_at')} for s in observations]
        target_source=sources.read_workspace_document_source(self.folder,target) if target else None
        envelope=read_document_envelope(json.dumps(dict(schema_version=1,status='prepared',surface_text='Prêt.',
            proposal=dict(operation=operation,format='docx',relative_path=path,source_file_ids=ids,limitations=[],canonical=value or rich()))))
        conversation['messages'].append(dict(role='assistant',content='Prêt.',timestamp='2026-10-10T00:00:01Z',meta={'document_workshop':{}}))
        actions.finalize(token,conversation,envelope,versions,serialize_markdown(envelope.canonical),
            snapshot=self.fx.snapshot,target_source=target_source)
        return actions.get_action(action_id)

    def confirm(self,a):
        return self.client.post('/api/document-workshop/actions/'+a['id']+'/confirm',json={
            **{k:a[k] for k in ('context_id','conversation_id','workspace_folder_id','revision_id')},'request_id':str(uuid4())})

    def puts(self): return [r for r in self.dav['seen'] if r[0]=='PUT']

    def create(self):
        a=self.prepare(); response=self.confirm(a)
        self.assertEqual(response.status_code,200,response.json)
        return a,response.json['action']['receipt']

    def test_real_create_explicit_copy_update_preserve_identity_histories_and_exact_bytes(self):
        freezes=[]; actual=snapshots.persist
        def freeze(run,request,result):
            actual(run,request,result)
            freezes.append((request.data,result))
            self.assertFalse(self.fx.rows("SELECT 1 FROM document_execution_journal WHERE action_id=%s::uuid",(run.action['id'],)))
        with patch.object(snapshots,'persist',freeze):
            created,r1=self.create();file_id=r1['workspace_file_id']
            before=workspace_files.get_workspace_file_storage_row(self.folder,file_id)
            copied=self.prepare(operation='copy',source=file_id,path='Documents/Copie.docx')
            r2=self.confirm(copied); self.assertEqual(r2.status_code,200,r2.json)
            candidate=rich();candidate['blocks'][0]=canonical('Candidat distinct')['blocks'][0]
            updated=self.prepare(operation='update',target=file_id,value=candidate,path=r1['relative_path'])
            r3=self.confirm(updated); self.assertEqual(r3.status_code,200,r3.json)
        receipt=r3.json['action']['receipt'];after=workspace_files.get_workspace_file_storage_row(self.folder,file_id)
        for k in ('id','display_name','original_filename','source_kind','created_at'):self.assertEqual(before[k],after[k],k)
        self.assertEqual(receipt['workspace_file_id'],file_id);self.assertEqual(receipt['product_link'],r1['product_link'])
        self.assertEqual(receipt['format'],'docx');self.assertNotEqual(receipt['revision_id'],r1['revision_id'])
        self.assertEqual(self.client.get('/api/document-workshop/actions/'+created['id']).json['action']['receipt'],r1)
        self.assertEqual(self.client.get(r1['product_link']).data,freezes[-1][1].docx)
        self.assertEqual(receipts.latest(self.conversation,self.folder)['id'],receipt['id'])
        self.assertNotIn('canonical',receipt);self.assertNotIn('text',receipt)
        self.assertEqual(len(self.puts()),3)
        for put,(_request,result) in zip(self.puts(),freezes):
            self.assertEqual(put[3],result.docx);self.assertNotEqual(put[3],result.pdf)
            self.assertEqual(result.manifest['page_evidence']['writer_pages'],1)
        self.assertEqual([p[2].get('If-None-Match') for p in self.puts()[:2]],['*','*'])
        self.assertEqual(self.puts()[-1][2]['If-Match'],r1['nextcloud_etag'])
        self.assertEqual(len(self.dav['files']),2);self.assertFalse(any(p.endswith('.pdf') for p in self.dav['files']))
        request=freezes[-1][0];self.assertEqual(request['source']['source_revision_id'],r1['revision_id'])
        self.assertNotEqual(request['source']['source_revision_id'],request['revision_id'])
        self.assertEqual(request['source']['canonical'],rich())
        for _request,render in freezes:
            with zipfile.ZipFile(io.BytesIO(render.docx)) as z:
                body=ET.fromstring(z.read('word/document.xml'));ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                for tag in ('tbl','hyperlink','b','i','numPr'):self.assertTrue(body.findall('.//w:'+tag,ns),tag)
                self.assertIn(b'Heading',z.read('word/styles.xml'))
                paragraphs=[''.join(p.itertext()) for p in body.findall('.//w:p',ns)]
                expected='Candidat distinct' if render is freezes[-1][1] else 'Français éè, ligature œ et Unicode.'
                self.assertIn(expected,paragraphs)
                if render is freezes[-1][1]:self.assertNotIn('Français éè, ligature œ et Unicode.',paragraphs)
        self.assertEqual(self.fx.rows('SELECT count(*) FROM workspace_files'),[(2,)])

    def test_markdown_card_limitations_follow_available_docx_capability(self):
        response=self.client.get('/api/document-workshop/actions/'+self.fx.action['id'])
        self.assertEqual(response.status_code,200,response.json)
        self.assertIn('docx',actions.capabilities(runtime.get_executor())['formats'])
        limitations=response.json['action']['limitations']
        self.assertNotIn('docx_pdf_unavailable',limitations)
        self.assertIn('pdf_unavailable',limitations)

    def test_twenty_writer_pages_accepted_twenty_one_refused_without_put(self):
        for pages in (20,21):
            value=canonical('Page 1')
            for n in range(2,pages+1):value['blocks'] += [dict(type='page_break'),canonical('Page '+str(n))['blocks'][0]]
            a=self.prepare(value=value,path='Documents/Pages'+str(pages)+'.docx');before=len(self.puts())
            response=self.confirm(a)
            self.assertEqual(response.status_code,200 if pages==20 else 503,response.json)
            self.assertEqual(len(self.puts()),before+(pages==20))
            if pages==20:
                manifest=self.fx.rows('SELECT manifest FROM document_renderer_snapshots WHERE action_id=%s::uuid',(a['id'],))[0][0]
                self.assertEqual(json.loads(manifest)['page_evidence']['writer_pages'],20)
            else:self.assertEqual(response.json['reason_code'],'document_page_limit')

    def test_changed_etag_during_writer_conflicts_before_put_and_real_412_preserves_prepared_if_match(self):
        _created,r=self.create();file_id=r['workspace_file_id']
        a=self.prepare(operation='update',target=file_id,path=r['relative_path']);before=len(self.puts())
        actual=snapshots.persist
        def change(run,request,result):
            actual(run,request,result);self.dav['files'][r['relative_path']]['etag']='"during-writer"'
        with patch.object(snapshots,'persist',change):response=self.confirm(a)
        self.assertEqual(response.status_code,409,response.json);self.assertEqual(len(self.puts()),before)
        self.dav['files'][r['relative_path']]['etag']=r['nextcloud_etag']
        a=self.prepare(operation='update',target=file_id,path=r['relative_path']);self.dav['race']=True
        response=self.confirm(a);self.assertEqual(response.status_code,409,response.json)
        self.assertEqual(self.puts()[-1][4],412);self.assertEqual(self.puts()[-1][2]['If-Match'],r['nextcloud_etag'])
        self.assertFalse(any(p[0]=='DELETE' for p in self.dav['seen']))

    def test_missing_or_desynchronized_frida_provenance_refuses_preparation(self):
        _created,r=self.create();before=len(self.puts())
        with self.conn() as conn:conn.execute('DELETE FROM document_renderer_snapshots')
        with self.assertRaises(DocumentWorkshopError):self.prepare(operation='update',target=r['workspace_file_id'],path=r['relative_path'])
        self.assertEqual(len(self.puts()),before)

    def test_migration_is_explicit_repeatable_preserves_existing_rows_and_pdf_stays_closed(self):
        before=self.fx.rows('SELECT id,state,format FROM document_actions')
        with self.conn() as conn:conn.execute(self.migration.read_text())
        self.assertEqual(before,self.fx.rows('SELECT id,state,format FROM document_actions'))
        self.assertNotIn('pdf',actions.capabilities(runtime.get_executor())['formats'])

    def test_download_mime_comes_from_proven_docx_format(self):
        _created,receipt=self.create()
        response=self.client.get(receipt['product_link'])
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.mimetype,'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        self.assertEqual(response.headers['X-Content-Type-Options'],'nosniff')
        self.assertIn('attachment;',response.headers['Content-Disposition'])

    def test_metadata_worker_failure_precedes_any_create_copy_or_update_put(self):
        _created,receipt=self.create()
        from core import workspace_document_source_extraction as extraction
        actual_metadata=store.file_metadata
        def failed_worker(run,content):
            with patch.object(extraction.subprocess,'run',side_effect=OSError('synthetic worker unavailable')):
                return actual_metadata(run,content)
        for operation in ('create','copy','update'):
            with self.subTest(operation=operation):
                a=self.prepare(operation=operation,
                    target=receipt['workspace_file_id'] if operation=='update' else None,
                    source=receipt['workspace_file_id'] if operation=='copy' else None,
                    path=receipt['relative_path'] if operation=='update' else 'Documents/Failed-'+operation+'.docx')
                before=len(self.puts())
                with patch.object(store,'file_metadata',failed_worker):response=self.confirm(a)
                self.assertEqual(len(self.puts()),before,'metadata failure must precede DAV mutation')
                self.assertEqual(response.json['action']['state'],'failed')
                self.assertNotIn('receipt',response.json['action'])
                self.assertFalse(any(row[0]=='DELETE' for row in self.dav['seen']))
    def test_fresh_source_bytes_and_durable_canonical_or_hash_mismatch_refuse_without_put(self):
        _created,r=self.create();file_id=r['workspace_file_id']
        for kind in ('bytes','canonical','hash'):
            with self.subTest(kind=kind):
                a=self.prepare(operation='update',target=file_id,path=r['relative_path']);before=len(self.puts())
                if kind=='bytes':
                    actual=sources.read_workspace_document_source
                    def changed(*args,**kw):
                        source=actual(*args,**kw)
                        return replace(source,content=source.content+b'changed')
                    with patch.object(sources,'read_workspace_document_source',changed):response=self.confirm(a)
                else:
                    with self.conn() as conn:
                        original=conn.execute('SELECT canonical,canonical_sha256 FROM document_revisions WHERE id=%s::uuid',(r['revision_id'],)).fetchone()
                        conn.execute('ALTER TABLE document_revisions DISABLE TRIGGER document_revision_immutable')
                        if kind=='canonical':
                            conn.execute('UPDATE document_revisions SET canonical=%s::jsonb WHERE id=%s::uuid',(json.dumps(canonical('Wrong source canonical')),r['revision_id']))
                        else:conn.execute('UPDATE document_revisions SET canonical_sha256=%s WHERE id=%s::uuid',('0'*64,r['revision_id']))
                        conn.execute('ALTER TABLE document_revisions ENABLE TRIGGER document_revision_immutable')
                    try:response=self.confirm(a)
                    finally:
                        with self.conn() as conn:
                            conn.execute('ALTER TABLE document_revisions DISABLE TRIGGER document_revision_immutable')
                            conn.execute('UPDATE document_revisions SET canonical=%s::jsonb,canonical_sha256=%s WHERE id=%s::uuid',(json.dumps(original[0]),original[1],r['revision_id']))
                            conn.execute('ALTER TABLE document_revisions ENABLE TRIGGER document_revision_immutable')
                self.assertNotEqual(response.status_code,200,response.json)
                self.assertEqual(len(self.puts()),before)
                self.assertNotEqual(response.json.get('action',{}).get('state'),'succeeded')
                if kind!='bytes':actions.cancel(a['id'],a['context_id'])

    def test_incompatible_expected_pins_refuse_real_client_before_snapshot_or_put(self):
        from core import document_workshop_execution_service as service
        from core.document_rendering import RenderingSession
        a=self.prepare();executor=runtime.get_executor()
        expected=executor.renderer_session.expected_engine|dict(writer_version='25.2.3.3')
        executor.renderer_session=RenderingSession(client=executor.renderer_session.client,expected_engine=expected)
        response,status=service.confirm(a['id'],dict(**{k:a[k] for k in ('context_id','conversation_id','workspace_folder_id','revision_id')},request_id=str(uuid4())),executor=executor)
        self.assertEqual(status,503,response);self.assertEqual(self.puts(),[])
        self.assertEqual(self.fx.rows('SELECT count(*) FROM document_renderer_snapshots'),[(0,)])
        self.assertEqual(self.fx.rows('SELECT count(*) FROM document_execution_journal'),[(0,)])

    def test_docx_sql_rollback_compensates_only_exact_create_etag_and_lost_reply_stays_unknown(self):
        with self.conn() as conn:
            conn.execute("CREATE FUNCTION m9_reject_render() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic'; END $$; CREATE TRIGGER m9_reject_render BEFORE INSERT ON document_revision_renders FOR EACH ROW EXECUTE FUNCTION m9_reject_render()")
        a=self.prepare();response=self.confirm(a)
        self.assertEqual(response.status_code,503,response.json)
        self.assertEqual(response.json['reason_code'],'document_publication_failed_compensated')
        self.assertEqual(len(self.puts()),1)
        deletion=[r for r in self.dav['seen'] if r[0]=='DELETE'];self.assertEqual(len(deletion),1)
        self.assertEqual(deletion[0][2]['If-Match'],'"v1"');self.assertEqual(self.dav['files'],{})
        self.assertEqual(self.fx.rows('SELECT count(*) FROM document_receipts'),[(0,)])
        with self.conn() as conn:conn.execute('DROP TRIGGER m9_reject_render ON document_revision_renders; DROP FUNCTION m9_reject_render()')
        a=self.prepare(path='Documents/Lost.docx');self.dav['drop']=True
        response=self.confirm(a);self.assertEqual(response.status_code,503,response.json)
        self.assertEqual(response.json['action']['state'],'remote_uncertain')
        before=len(self.puts());self.confirm(a)
        self.assertEqual(len(self.puts()),before);self.assertEqual(len([r for r in self.dav['seen'] if r[0]=='DELETE']),1)
        self.assertEqual(self.fx.rows('SELECT count(*) FROM document_receipts'),[(0,)])
