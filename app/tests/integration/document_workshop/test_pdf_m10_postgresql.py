"""M10 delta on M9's real HTTP DAV, SQL and qualified ephemeral Writer."""
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from pypdf import PdfReader
from core import document_renderer_store as snapshots, document_workshop_runtime as runtime
from core import document_workshop_actions as actions, document_workshop_execution_store as store
from core import workspace_document_content_service as sources, workspace_files
from core.document_workshop_contract import DocumentWorkshopError
from tests.integration.document_workshop import test_docx_m9a_postgresql as docx
rich=docx.rich
from tests.unit.core.test_workspace_document_source_extraction_m2 import pdf_bytes
from tests.unit.core.test_document_workshop_canonical_paths import canonical


@unittest.skipUnless(os.environ.get('M5_PROOF_PG_SOCKET'),'isolated PostgreSQL required')
class PdfM10PostgresqlTests(unittest.TestCase):
    def setUp(self):
        self.h=docx.DocxM9APostgresqlTests('runTest');self.h.setUp();self.addCleanup(self.h.doCleanups)
        self.migration=self.h.migration.with_name('document_workshop_pdf_m10.sql')
        with self.h.conn() as conn:conn.execute(self.migration.read_text())

    def prepare(self,**kwargs):
        return self.h.prepare(**(dict(format='pdf',path='Documents/Étude.pdf')|kwargs))

    def create(self):
        action=self.prepare();response=self.h.confirm(action)
        self.assertEqual(response.status_code,200,response.json)
        return action,response.json['action']['receipt']

    def assert_no_publication(self,action,before):
        self.assertEqual(len(self.h.puts()),before)
        self.assertEqual(self.h.fx.rows('SELECT count(*) FROM document_receipts WHERE action_id=%s::uuid',(action['id'],)),[(0,)])

    def test_pdf_create_update_exact_pair_bytes_identity_and_single_confirmation(self):
        freezes=[];actual=snapshots.persist
        def freeze(run,request,result):
            actual(run,request,result);freezes.append((request.data,result))
            self.assertFalse(self.h.fx.rows('SELECT 1 FROM document_execution_journal WHERE action_id=%s::uuid',(run.action['id'],)))
        with patch.object(snapshots,'persist',freeze):
            first,r1=self.create();file_id=r1['workspace_file_id']
            before=workspace_files.get_workspace_file_storage_row(self.h.folder,file_id)
            with self.h.conn() as conn:
                conn.execute(self.migration.read_text())
                conn.execute(self.migration.read_text())
            self.assertEqual(self.h.client.get('/api/document-workshop/actions/'+first['id']).json['action']['receipt'],r1)
            value=rich();value['blocks'][0]=canonical('Révision demandée, été et cœur.')['blocks'][0]
            update=self.prepare(operation='update',target=file_id,value=value)
            response=self.h.confirm(update);self.assertEqual(response.status_code,200,response.json)
        r2=response.json['action']['receipt'];after=workspace_files.get_workspace_file_storage_row(self.h.folder,file_id)
        for k in ('id','original_filename','display_name','source_kind','created_at'):
            self.assertEqual(before[k],after[k],k)
        for k in ('workspace_file_id','name','format','relative_path','nextcloud_file_id','product_link'):
            self.assertEqual(r1[k],r2[k],k)
        self.assertEqual(r2['format'],'pdf');self.assertEqual(len(self.h.puts()),2)
        self.assertEqual(self.h.puts()[0][2]['If-None-Match'],'*')
        self.assertEqual(self.h.puts()[1][2]['If-Match'],r1['nextcloud_etag'])
        self.assertEqual(len(self.h.dav['files']),1)
        for n,(put,(request,result),receipt) in enumerate(zip(self.h.puts(),freezes,(r1,r2))):
            self.assertEqual(request['format'],'pdf');self.assertEqual(put[3],result.pdf)
            self.assertNotEqual(put[3],result.docx);self.assertEqual(put[2]['Content-Type'],'application/pdf')
            self.assertEqual(receipt['content_sha256'],hashlib.sha256(result.pdf).hexdigest())
            manifest=result.manifest;evidence=manifest['page_evidence']
            self.assertEqual(manifest['engine'],runtime.get_executor().renderer_session.expected_engine)
            self.assertEqual(evidence['method'],'writer_reload_layout_v1')
            self.assertEqual(evidence['revision_id'],receipt['revision_id'])
            self.assertEqual(evidence['canonical_sha256'],receipt['canonical_sha256'])
            self.assertEqual((evidence['writer_pages'],evidence['pdf_pages']),(1,1))
            reader=PdfReader(io.BytesIO(result.pdf));text=''.join(p.extract_text() for p in reader.pages)
            for expected in ('Titre structuré','Premier','Second','Puce','Gras','A','B','C','D','Lien'):
                self.assertIn(expected,text)
            self.assertIn('Révision demandée' if n else 'Français éè',text)
            if n:self.assertNotIn('Français éè',text)
            self.assertTrue(reader.pages[0].get('/Annots'))
            self.assertEqual(manifest['artifacts']['pdf']['byte_size'],len(result.pdf))
            self.assertEqual(self.h.fx.rows('SELECT byte_size FROM document_revision_renders WHERE revision_id=%s::uuid',(receipt['revision_id'],)),[(len(result.pdf),)])
        self.assertEqual(freezes[1][0]['source']['kind'],'pdf')
        self.assertEqual(freezes[1][0]['source']['source_revision_id'],r1['revision_id'])
        self.assertEqual(freezes[1][0]['source']['sha256'],r1['content_sha256'])
        self.assertEqual(freezes[1][0]['source']['canonical'],rich())
        self.assertNotEqual(r1['revision_id'],r2['revision_id'])
        download=self.h.client.get(r2['product_link'])
        self.assertEqual(download.mimetype,'application/pdf');self.assertEqual(download.data,freezes[1][1].pdf)
        self.assertEqual(download.headers['X-Content-Type-Options'],'nosniff')
        self.assertIn('attachment;',download.headers['Content-Disposition'])
        self.assertEqual(self.h.confirm(update).json['action']['receipt'],r2)
        self.assertEqual(self.h.client.get('/api/document-workshop/actions/'+first['id']).json['action']['receipt'],r1)
        self.assertEqual(len(self.h.puts()),2)
        self.assertEqual(self.h.fx.rows('SELECT count(*) FROM document_receipts'),[(2,)])
        print('M10_PROOF '+json.dumps([dict(action_id=a['id'],revision_id=r['revision_id'],receipt_id=r['id'],file_id=file_id,
            canonical_sha256=r['canonical_sha256'],pdf_sha256=r['content_sha256'],docx_sha256=f[1].manifest['artifacts']['docx']['sha256'],
            job_id=f[0]['job_id'],pages=1) for a,r,f in zip((first,update),(r1,r2),freezes)]),flush=True)

    def test_external_pdf_refuses_update_then_explicit_selected_copy_to_docx_preserves_source(self):
        body=pdf_bytes(count=21);path='Documents/External.pdf';file_id=self.h.adopt_external(body,path=path)
        self.assertIn('Synthetic page 21',sources.read_workspace_document_source(self.h.folder,file_id).text)
        with self.assertRaises(DocumentWorkshopError):self.prepare(operation='update',target=file_id,path=path)
        self.assertEqual(self.h.puts(),[]);self.assertEqual(self.h.fx.rows('SELECT count(*) FROM document_receipts'),[(0,)])
        action=self.h.prepare(operation='copy',source=file_id,path='Documents/Nouveau accepté.docx',value=canonical('Synthetic page 21 — texte demandé.'))
        response=self.h.confirm(action);self.assertEqual(response.status_code,200,response.json)
        receipt=response.json['action']['receipt'];self.assertEqual(receipt['format'],'docx')
        self.assertNotEqual(receipt['workspace_file_id'],file_id)
        self.assertEqual(self.h.dav['files'][path]['content'],body)
        self.assertEqual(self.h.dav['files'][path]['etag'],'"external-v1"')
        self.assertEqual(len(self.h.puts()),1);self.assertEqual(self.h.puts()[0][1],'Documents/Nouveau accepté.docx')

    def test_capability_migration_repeatable_and_missing_prerequisites_preserve_neighbors(self):
        with self.h.conn() as conn:
            before=conn.execute('SELECT id,state,format FROM document_actions').fetchall()
            conn.execute(self.migration.read_text());self.assertEqual(conn.execute('SELECT id,state,format FROM document_actions').fetchall(),before)
        self.assertEqual(actions.capabilities(runtime.get_executor())['formats'],['markdown','docx','pdf'])
        with self.h.conn() as conn:conn.execute(self.h.migration.read_text())
        self.assertEqual(actions.capabilities(runtime.get_executor())['formats'],['markdown','docx'])
        with self.assertRaises(DocumentWorkshopError) as caught:self.prepare()
        self.assertEqual(caught.exception.reason_code,'document_format_unavailable')
        self.assertEqual(self.h.puts(),[])
        with patch('core.document_workshop_runtime.Path.read_bytes',side_effect=OSError):
            self.assertEqual(actions.capabilities(runtime.get_executor())['formats'],['markdown'])
        self.assertEqual(actions.capabilities()['formats'],['markdown'])

    def test_pdf_partial_pair_wrong_revision_or_pages_refused_before_put(self):
        from core import document_renderer_contract as c
        from core.document_renderer_client import DocumentRendererClient
        actual=DocumentRendererClient.result
        for kind in ('partial','revision','pages','over_limit'):
            action=self.prepare(path='Documents/'+kind+'.pdf')
            def corrupt(client,request,**kwargs):
                wire=actual(client,request,**kwargs);parts=c.parse_multipart(wire,limit=c.MAX_RESULT_BYTES)
                manifest=c.read_json(parts[0][2]);self.assertEqual(manifest['status'],'ready')
                if kind=='partial':parts=parts[:2]
                elif kind=='revision':manifest['page_evidence']['revision_id']='00000000-0000-4000-8000-000000000000'
                elif kind=='pages':manifest['page_evidence']['pdf_pages']=2
                elif kind=='over_limit':manifest['page_evidence']['writer_pages']=21
                return c.encode_multipart([(parts[0][0],parts[0][1],c.json_bytes(manifest)),*parts[1:]],limit=c.MAX_RESULT_BYTES)
            with self.subTest(kind=kind),patch.object(DocumentRendererClient,'result',corrupt):
                response=self.h.confirm(action);self.assertEqual(response.status_code,503,response.json)
                self.assertEqual(response.json['reason_code'],'document_page_limit' if kind=='over_limit' else 'document_render_invalid')
                self.assert_no_publication(action,0)
                self.assertFalse(self.h.fx.rows('SELECT 1 FROM document_renderer_snapshots'))

    def test_pdf_metadata_failure_precedes_put(self):
        from core import workspace_document_source_extraction as extraction
        action=self.prepare();actual=store.file_metadata
        def fail(run,content):
            with patch.object(extraction.subprocess,'run',side_effect=OSError):return actual(run,content)
        with patch.object(store,'file_metadata',fail):response=self.h.confirm(action)
        self.assertEqual(response.status_code,503,response.json);self.assert_no_publication(action,0)

    def test_frida_missing_proof_fresh_bytes_canonical_revision_and_stale_etag_refuse(self):
        _,receipt=self.create();file_id=receipt['workspace_file_id'];original=sources.read_workspace_document_source
        for field in ('bytes','canonical','revision','etag'):
            action=self.prepare(operation='update',target=file_id)
            if field=='bytes':
                def wrong(*args,**kw):return replace(original(*args,**kw),content=b'wrong bytes')
                with patch.object(sources,'read_workspace_document_source',wrong):response=self.h.confirm(action)
            elif field=='etag':
                actual=snapshots.persist
                def stale(run,request,result):
                    actual(run,request,result);self.h.dav['files'][receipt['relative_path']]['etag']='"stale"'
                with patch.object(snapshots,'persist',stale):response=self.h.confirm(action)
                self.h.dav['files'][receipt['relative_path']]['etag']=receipt['nextcloud_etag']
            else:
                with self.h.conn() as conn:
                    if field=='revision':
                        conn.execute('UPDATE document_artifacts SET current_revision_id=NULL WHERE workspace_file_id=%s::uuid',(file_id,))
                    else:
                        old=conn.execute('SELECT canonical FROM document_revisions WHERE id=%s::uuid',(receipt['revision_id'],)).fetchone()[0]
                        conn.execute('ALTER TABLE document_revisions DISABLE TRIGGER document_revision_immutable')
                        conn.execute('UPDATE document_revisions SET canonical=%s::jsonb WHERE id=%s::uuid',(json.dumps(canonical('wrong canonical')),receipt['revision_id']))
                        conn.execute('ALTER TABLE document_revisions ENABLE TRIGGER document_revision_immutable')
                try:response=self.h.confirm(action)
                finally:
                    with self.h.conn() as conn:
                        if field=='revision':conn.execute('UPDATE document_artifacts SET current_revision_id=%s::uuid WHERE workspace_file_id=%s::uuid',(receipt['revision_id'],file_id))
                        else:
                            conn.execute('ALTER TABLE document_revisions DISABLE TRIGGER document_revision_immutable')
                            conn.execute('UPDATE document_revisions SET canonical=%s::jsonb WHERE id=%s::uuid',(json.dumps(old),receipt['revision_id']))
                            conn.execute('ALTER TABLE document_revisions ENABLE TRIGGER document_revision_immutable')
            self.assertNotEqual(response.status_code,200,(field,response.json));self.assert_no_publication(action,1)
        with self.h.conn() as conn:conn.execute('DELETE FROM document_renderer_snapshots')
        with self.assertRaises(DocumentWorkshopError):self.prepare(operation='update',target=file_id)
        self.assertEqual(len(self.h.puts()),1)

    def test_unusable_external_pdf_rejected_by_complete_reader_without_put(self):
        for body in (pdf_bytes(count=1,blank_last=True),pdf_bytes(count=1,encrypted=True),b'%PDF-1.7\ninvalid'):
            with self.assertRaises(DocumentWorkshopError):self.h.adopt_external(body,path='Documents/External.pdf')
            self.assertEqual(self.h.puts(),[]);self.assertEqual(self.h.fx.rows('SELECT count(*) FROM document_receipts'),[(0,)])

    def test_pdf_publication_rollback_repairs_metadata_without_second_put(self):
        _,r=self.create();action=self.prepare(operation='update',target=r['workspace_file_id'],value=canonical('Révision après rollback SQL.'))
        with self.h.conn() as conn:
            conn.execute("CREATE FUNCTION proof_fail_pdf() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic rollback'; END $$")
            conn.execute('CREATE TRIGGER proof_fail_pdf BEFORE INSERT ON document_revision_renders FOR EACH ROW EXECUTE FUNCTION proof_fail_pdf()')
        actual=store.file_metadata;observations=[]
        def metadata(run,content):
            observations.append(len(self.h.puts()));return actual(run,content)
        with patch.object(store,'file_metadata',metadata):
            response=self.h.confirm(action);self.assertEqual(response.status_code,503,response.json)
            self.assertEqual(observations,[1]) # Initial validation precedes the second (update) PUT.
            self.assertEqual(len(self.h.puts()),2);self.assert_no_publication(action,2)
            with self.h.conn() as conn:
                conn.execute('DROP TRIGGER proof_fail_pdf ON document_revision_renders; DROP FUNCTION proof_fail_pdf()')
            refreshed=self.h.client.get('/api/document-workshop/actions/'+action['id'])
            self.assertEqual(refreshed.json['action']['state'],'succeeded',refreshed.json)
            self.assertEqual(observations,[1,2]) # Existing SQL-only repair re-extracts known-success bytes.
        self.assertEqual(len(self.h.puts()),2);self.assertFalse(any(p[0]=='DELETE' for p in self.h.dav['seen']))
        receipt=refreshed.json['action']['receipt'];self.assertEqual(receipt['workspace_file_id'],r['workspace_file_id'])
        self.assertEqual(self.h.client.get(receipt['product_link']).data,self.h.puts()[-1][3])
        self.h.client.get('/api/document-workshop/actions/'+action['id'])
        self.assertEqual(len(self.h.puts()),2);self.assertEqual(self.h.fx.rows('SELECT count(*) FROM document_receipts'),[(2,)])
