"""M8-C schema, source, framing, pair and identity adversaries."""
import copy
import importlib
import importlib.util
import io
import json
import unittest
import zipfile
from tests.support import document_renderer_fixtures as f

class RendererContractTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('core.document_renderer_contract'),'M8-C closed contract absent')
        self.c=importlib.import_module('core.document_renderer_contract')
        self.request=self.make()

    def make(self,**kw):
        return self.c.make_request(job_id=f.JOB,revision_id=f.REVISION,canonical=f.canonical(),
            canonical_sha256=self.c.digest(self.c.json_bytes(f.canonical())),format='docx',engine=f.ENGINE,**kw)

    def invalid(self,callback):
        with self.assertRaises(self.c.RendererError) as caught:callback()
        self.assertIn(caught.exception.reason_code,self.c.REASON_CODES)
        self.assertEqual(str(caught.exception),caught.exception.reason_code)

    def pair(self,change=None,*,pages=1):
        m,d,p=f.result(self.c,self.request,pages=pages)
        if change:change(m)
        return self.c.validate_result(f.response(self.c,m,d,p),request=self.request,expected_engine=f.ENGINE)

    def test_valid_pair_and_strict_snapshot(self):
        a=self.pair();self.assertEqual(a.docx,f.docx());self.assertEqual(a.manifest['job_id'],f.JOB)
        view=self.request.data;view['canonical']['blocks'].clear();self.assertTrue(self.request.data['canonical']['blocks'])
        self.assertEqual(self.c.read_request(self.request.wire,expected_engine=f.ENGINE).identity,self.request.identity)

    def test_candidate_mutation_never_changes_measured_snapshot(self):
        value=f.canonical();digest=self.c.digest(self.c.json_bytes(value))
        r=self.c.make_request(job_id=f.JOB,revision_id=f.REVISION,canonical=value,canonical_sha256=digest,format='pdf',engine=f.ENGINE)
        value['blocks'][0]['spans'][0]['text']='Changed';self.assertEqual(r.data['canonical'],f.canonical())
        self.invalid(lambda:self.c.make_request(job_id=f.JOB,revision_id=f.REVISION,canonical=value,canonical_sha256=digest,format='pdf',engine=f.ENGINE))

    def test_complete_request_identity_covers_format_revision_engine_and_source(self):
        r=self.request.data
        for key,value in [('format','pdf'),('revision_id','10000000-0000-4000-8000-000000000099')]:
            kw={k:r[k] for k in ('job_id','revision_id','canonical','canonical_sha256','format')};kw[key]=value
            self.assertNotEqual(self.c.make_request(**kw,engine=f.ENGINE).identity,self.request.identity)
        engine=copy.deepcopy(f.ENGINE);engine['writer_version']='synthetic-other'
        self.assertNotEqual(self.c.make_request(job_id=f.JOB,revision_id=f.REVISION,canonical=f.canonical(),canonical_sha256=r['canonical_sha256'],format='docx',engine=engine).identity,self.request.identity)
        self.assertNotEqual(self.make(source=self.source(),source_content=f.docx()).identity,self.request.identity)

    def source(self,kind='docx',origin='external'):
        body=f.docx() if kind=='docx' else f.pdf()
        return dict(kind=kind,origin=origin,byte_size=len(body),sha256=self.c.digest(body),
            source_revision_id=f.SOURCE_REVISION if origin=='frida' else None,
            canonical=f.canonical('Previous revision') if origin=='frida' else None,
            canonical_sha256=self.c.digest(self.c.json_bytes(f.canonical('Previous revision'))) if origin=='frida' else None)

    def test_source_modes_distinguish_previous_and_candidate_canonical(self):
        for kind,origin in [('docx','external'),('docx','frida'),('pdf','frida')]:
            s=self.source(kind,origin);r=self.make(source=s,source_content=f.docx() if kind=='docx' else f.pdf())
            self.assertEqual(r.data['source'],s)
            if origin=='frida':self.assertNotEqual(s['canonical_sha256'],r.data['canonical_sha256'])
        self.invalid(lambda:self.make(source=self.source('pdf','external'),source_content=f.pdf()))

    def test_source_forbidden_metadata_and_missing_correspondence(self):
        for key in ('url','path','command','target_dav','credential','filename','filter','template','uno'):
            s=self.source();s[key]='synthetic-forbidden';self.invalid(lambda:self.make(source=s,source_content=f.docx()))
        for key in ('source_revision_id','canonical','canonical_sha256'):
            s=self.source('pdf','frida');s[key]=None;self.invalid(lambda:self.make(source=s,source_content=f.pdf()))
        s=self.source();s['sha256']='0'*64;self.invalid(lambda:self.make(source=s,source_content=f.docx()))

    def test_passive_links_preserved_and_active_canonical_refused(self):
        value=f.canonical(link='https://synthetic.invalid/passive')
        r=self.c.make_request(job_id=f.JOB,revision_id=f.REVISION,canonical=value,canonical_sha256=self.c.digest(self.c.json_bytes(value)),format='pdf',engine=f.ENGINE)
        self.assertEqual(r.data['canonical'],value)
        for link in ('file:///etc/synthetic','javascript:synthetic','https://user:pass@synthetic.invalid'):
            value=f.canonical(link=link);self.invalid(lambda:self.c.make_request(job_id=f.JOB,revision_id=f.REVISION,canonical=value,canonical_sha256='0'*64,format='pdf',engine=f.ENGINE))

    def test_duplicate_unknown_keys_and_types_refused(self):
        for body in (b'{"a":1,"a":2}',b'{"a":NaN}',b'[]',b'{}'):
            self.invalid(lambda:self.c.read_json(body)) if body!=b'{}' else self.invalid(lambda:self.c.validate_capabilities({}))
        for key,value in [('protocol_version',True),('job_id','/tmp/private'),('profile','other'),('format','odt'),('unknown',1)]:
            obj=self.request.data;obj[key]=value
            wire=self.c.encode_multipart([('request','application/json',self.c.json_bytes(obj))],limit=self.c.MAX_REQUEST_BYTES)
            self.invalid(lambda:self.c.read_request(wire,expected_engine=f.ENGINE))

    def test_capabilities_require_explicit_caller_pins(self):
        caps=self.c.capabilities(f.ENGINE);self.c.validate_capabilities(caps,expected_engine=f.ENGINE)
        caps['engine']['image_digest']='sha256:'+'c'*64
        self.invalid(lambda:self.c.validate_capabilities(caps,expected_engine=f.ENGINE))
        caps=self.c.capabilities(f.ENGINE);caps['limits']['queue']=1
        self.invalid(lambda:self.c.validate_capabilities(caps,expected_engine=f.ENGINE))

    def test_pages_one_and_twenty_accepted(self):
        for pages in (1,20):self.assertEqual(self.pair(pages=pages).manifest['page_evidence']['writer_pages'],pages)

    def test_absent_zero_over_bool_float_or_pdf_only_pages_refused(self):
        for value in (None,0,21,True,1.0):
            self.invalid(lambda:self.pair(lambda m:m['page_evidence'].update(writer_pages=value)))
            self.invalid(lambda:self.pair(lambda m:m['artifacts']['docx'].update(writer_pages=value)))
        self.invalid(lambda:self.pair(lambda m:m.update(page_evidence=None)))
        self.invalid(lambda:self.pair(lambda m:m['page_evidence'].update(method='pdf_count_only')))
        self.invalid(lambda:self.pair(lambda m:m['page_evidence'].update(pdf_pages=2)))
        self.invalid(lambda:self.pair(lambda m:m['artifacts']['pdf'].update(pdf_pages=2)))

    def test_result_identity_and_pins_refused(self):
        for key,value in [('job_id','10000000-0000-4000-8000-000000000099'),('revision_id','10000000-0000-4000-8000-000000000099'),('canonical_sha256','0'*64),('request_sha256','0'*64),('source_sha256','0'*64)]:
            self.invalid(lambda:self.pair(lambda m:m.update({key:value})))
        for key,value in [('profile','other'),('locale','other'),('writer_version','synthetic-other')]:
            self.invalid(lambda:self.pair(lambda m:m['engine'].update({key:value})))

    def test_lengths_digests_and_real_binary_types_refused(self):
        for fmt in ('docx','pdf'):
            self.invalid(lambda:self.pair(lambda m:m['artifacts'][fmt].update(sha256='0'*64)))
            self.invalid(lambda:self.pair(lambda m:m['artifacts'][fmt].update(byte_size=1)))
            self.invalid(lambda:self.pair(lambda m:m['artifacts'][fmt].update(byte_size=True)))
        m,d,p=f.result(self.c,self.request)
        for fmt,body in [('docx',b'PK\x03\x04not-docx'),('pdf',b'%PDF-1.7\nnot-pdf\n%%EOF')]:
            m,d,p=f.result(self.c,self.request);m['artifacts'][fmt].update(byte_size=len(body),sha256=self.c.digest(body));m['page_evidence'][fmt+'_sha256']=self.c.digest(body)
            self.invalid(lambda:self.c.validate_result(f.response(self.c,m,body if fmt=='docx' else d,body if fmt=='pdf' else p),request=self.request,expected_engine=f.ENGINE))

    def test_multipart_missing_duplicate_unexpected_raw_and_incomplete_refused(self):
        m,d,p=f.result(self.c,self.request)
        parts=[('manifest','application/json',self.c.json_bytes(m)),('docx',self.c.MEDIA_TYPES['docx'],d),('pdf',self.c.MEDIA_TYPES['pdf'],p)]
        for items in (parts[:-1],parts+[parts[-1]],parts+[('other','application/octet-stream',b'x')]):
            wire=self.c.encode_multipart(items,limit=self.c.MAX_RESULT_BYTES)
            self.invalid(lambda:self.c.validate_result(wire,request=self.request,expected_engine=f.ENGINE))
        wire=f.response(self.c,m,d,p)
        for body in (d,wire.body[:-1],wire.body+b'x'):
            self.invalid(lambda:self.c.validate_result(self.c.WireMessage(wire.content_type,body),request=self.request,expected_engine=f.ENGINE))

    def test_archive_duplicate_traversal_symlink_expansion_and_active_content_refused(self):
        for name,body in [('../escape.xml',b'<x/>'),('word/vbaProject.bin',b'x'),('word/extra.xml',b'<x/>')]:
            data=io.BytesIO(f.docx())
            with zipfile.ZipFile(data,'a') as z:z.writestr(name,body)
            s=self.source();s.update(byte_size=len(data.getvalue()),sha256=self.c.digest(data.getvalue()))
            self.invalid(lambda:self.make(source=s,source_content=data.getvalue()))

    def test_protocol_error_never_contains_content_or_exception(self):
        wire=self.c.WireMessage('application/json',b'private synthetic exception')
        self.invalid(lambda:self.c.validate_result(wire,request=self.request,expected_engine=f.ENGINE))

    def test_wire_and_declared_limits_exact_and_plus_one(self):
        for name,limit in [('json',self.c.MAX_JSON_BYTES),('source',self.c.MAX_SOURCE_BYTES),('request',self.c.MAX_REQUEST_BYTES),('artifact',self.c.MAX_ARTIFACT_BYTES),('result',self.c.MAX_RESULT_BYTES)]:
            self.c.check_size(limit,limit);self.invalid(lambda:self.c.check_size(limit+1,limit))
        self.invalid(lambda:self.c.read_json(b' '*(self.c.MAX_JSON_BYTES+1)))
        self.invalid(lambda:self.c.parse_multipart(self.c.WireMessage('multipart/form-data; boundary=frida-v1',b'x'*(self.c.MAX_RESULT_BYTES+1)),limit=self.c.MAX_RESULT_BYTES))

    def test_unhashable_state_reason_source_are_content_free_protocol_errors(self):
        for field in ('status','reason_code'):
            self.invalid(lambda:self.pair(lambda m:m.update({field:[]})))
            value=self.c.status_value(self.request);value[field]=[]
            self.invalid(lambda:self.c.validate_status(value,request=self.request))
        obj=self.request.data;obj['source']={'kind':[]}
        wire=self.c.encode_multipart([('request','application/json',self.c.json_bytes(obj)),('source','application/pdf',f.pdf())],limit=self.c.MAX_REQUEST_BYTES)
        self.invalid(lambda:self.c.read_request(wire,expected_engine=f.ENGINE))

    def test_delete_request_is_closed_and_bound_to_job_identity(self):
        for cancel in (True,False):
            message=self.c.delete_message(self.request,cancel=cancel)
            self.assertEqual(self.c.validate_delete(self.c.read_json(message.body),request=self.request),'cancel' if cancel else 'release')
            value=self.c.read_json(message.body);value['path']='/tmp/synthetic'
            self.invalid(lambda:self.c.validate_delete(value,request=self.request))

    def test_engine_expected_snapshot_cannot_be_learned_from_forged_request(self):
        value=self.request.data;value['canonical']['blocks'][0]['spans'][0]['text']='Changed'
        forged=self.c.RenderRequest(self.c.json_bytes(value),None)
        m,d,p=f.result(self.c,forged)
        self.invalid(lambda:self.c.validate_result(f.response(self.c,m,d,p),request=forged,expected_engine=f.ENGINE))

    def test_causal_detector_catches_trusted_declared_hash_mutant(self):
        from unittest.mock import patch
        m,d,p=f.result(self.c,self.request);m['artifacts']['docx']['sha256']='0'*64;m['page_evidence']['docx_sha256']='0'*64
        wire=f.response(self.c,m,d,p)
        probe=lambda:self.invalid(lambda:self.c.validate_result(wire,request=self.request,expected_engine=f.ENGINE))
        probe()
        real=self.c.digest
        with patch.object(self.c,'digest',lambda body:'0'*64 if body==d else real(body)):
            with self.assertRaises(AssertionError):probe()

    def test_causal_detector_catches_missing_part_completion_mutant(self):
        from unittest.mock import patch
        m,d,p=f.result(self.c,self.request)
        wire=self.c.encode_multipart([('manifest','application/json',self.c.json_bytes(m)),('docx',self.c.MEDIA_TYPES['docx'],d)],limit=self.c.MAX_RESULT_BYTES)
        probe=lambda:self.invalid(lambda:self.c.validate_result(wire,request=self.request,expected_engine=f.ENGINE))
        probe();real=self.c.parse_multipart
        def permissive(message,**kw):
            parts=real(message,**kw)
            return parts+[('pdf',self.c.MEDIA_TYPES['pdf'],p)] if len(parts)==2 and parts[0][0]=='manifest' else parts
        with patch.object(self.c,'parse_multipart',permissive):
            with self.assertRaises(AssertionError):probe()

    def test_json_and_framing_actual_octets_exact_then_one_over(self):
        limit=self.c.MAX_JSON_BYTES
        self.assertEqual(self.c.read_json(b'{}'+b' '*(limit-2)),{})
        self.invalid(lambda:self.c.read_json(b'{}'+b' '*(limit-1)))
        for total in (self.c.MAX_REQUEST_BYTES,self.c.MAX_RESULT_BYTES):
            overhead=len(self.c.encode_multipart([('source','application/octet-stream',b'')],limit=total).body)
            # Account for the additional decimal digits in Content-Length.
            n=total-overhead-len(str(total-overhead))+1
            wire=self.c.encode_multipart([('source','application/octet-stream',b'x'*n)],limit=total)
            self.assertEqual(len(wire.body),total)
            self.invalid(lambda:self.c.encode_multipart([('source','application/octet-stream',b'x'*(n+1))],limit=total))

    def padded_docx(self,size,*,expanded=False,entries=None):
        data=io.BytesIO(f.docx())
        with zipfile.ZipFile(data,'a',compression=zipfile.ZIP_DEFLATED if expanded else zipfile.ZIP_STORED) as z:
            if entries is not None:
                for i in range(entries-3):z.writestr('docProps/core.xml' if i==0 else 'word/theme/t'+str(i)+'.xml','<x/>')
            else:z.writestr('docProps/custom.xml',b'<x><!--'+b'x'*size+b'--></x>')
        return data.getvalue()

    def test_source_artifact_real_octets_at_limit_and_one_over(self):
        # ZIP_STORED makes total wire octets controllable without fake inspectors.
        overhead=len(self.padded_docx(0))
        for limit,kind in ((self.c.MAX_SOURCE_BYTES,'source'),(self.c.MAX_ARTIFACT_BYTES,'artifact')):
            body=self.padded_docx(limit-overhead);self.assertEqual(len(body),limit)
            if kind=='source':
                source=self.source();source.update(byte_size=len(body),sha256=self.c.digest(body))
                r=self.make(source=source,source_content=body);self.assertEqual(len(r.source_content),limit)
                too_big=self.padded_docx(limit-overhead+1);source.update(byte_size=len(too_big),sha256=self.c.digest(too_big))
                self.invalid(lambda:self.make(source=source,source_content=too_big))
            else:
                m,d,p=f.result(self.c,self.request)
                m['artifacts']['docx'].update(byte_size=len(body),sha256=self.c.digest(body));m['page_evidence']['docx_sha256']=self.c.digest(body)
                self.c.validate_result(f.response(self.c,m,body,p),request=self.request,expected_engine=f.ENGINE)
                too_big=self.padded_docx(limit-overhead+1)
                m['artifacts']['docx'].update(byte_size=len(too_big),sha256=self.c.digest(too_big));m['page_evidence']['docx_sha256']=self.c.digest(too_big)
                self.invalid(lambda:self.c.validate_result(f.response(self.c,m,too_big,p),request=self.request,expected_engine=f.ENGINE))

    def test_archive_actual_expansion_and_entries_exact_then_one_over(self):
        from core.document_renderer_artifacts import inspect_docx
        base=sum(i.file_size for i in zipfile.ZipFile(io.BytesIO(f.docx())).infolist())
        comment_overhead=len(b'<x><!--' + b'--></x>')
        body=self.padded_docx(67_108_864-base-comment_overhead,expanded=True)
        inspect_docx(body)
        self.invalid(lambda:inspect_docx(self.padded_docx(67_108_864-base-comment_overhead+1,expanded=True)))
        inspect_docx(self.padded_docx(0,entries=4096))
        self.invalid(lambda:inspect_docx(self.padded_docx(0,entries=4097)))

    def test_multipart_header_duplicates_unexpected_headers_lengths_and_boundaries(self):
        m,d,p=f.result(self.c,self.request);wire=f.response(self.c,m,d,p)
        bodies=[wire.body.replace(b'Content-Type: application/json',b'X-Private: synthetic\r\nContent-Type: application/json',1),
            wire.body.replace(b'Content-Length: ',b'Content-Length: -',1),wire.body.replace(b'Content-Length: ',b'Content-Length: 0',1),
            b'prefix'+wire.body,wire.body+b'suffix']
        for body in bodies:self.invalid(lambda:self.c.validate_result(self.c.WireMessage(wire.content_type,body),request=self.request,expected_engine=f.ENGINE))

    def test_durable_offline_corpus_matches_expected_decisions(self):
        from tests.support.document_renderer_conformance import run
        results=run();self.assertEqual(len(results),32)
        self.assertEqual(sum(r['accepted'] for r in results),13)

    def test_result_http_status_must_be_strict_success(self):
        m,d,p=f.result(self.c,self.request);wire=f.response(self.c,m,d,p)
        for status in (True,202,503):self.invalid(lambda:self.c.validate_result(self.c.WireMessage(wire.content_type,wire.body,status),request=self.request,expected_engine=f.ENGINE))

    def test_docx_relationships_are_passive_admissible_links_or_in_archive_targets(self):
        from core.document_renderer_artifacts import inspect_docx
        prefix='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId2" '
        for target,mode,typ,accepted in [('https://synthetic.invalid/passive','External','hyperlink',True),('file:///tmp/private','External','hyperlink',False),('../../../etc/private','','styles',False),('https://synthetic.invalid/fetch','','styles',False)]:
            data=io.BytesIO(f.docx())
            xml=prefix+'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'+typ+'" Target="'+target+'"'+(' TargetMode="'+mode+'"' if mode else '')+'/></Relationships>'
            with zipfile.ZipFile(data,'a') as z:z.writestr('word/_rels/document.xml.rels',xml)
            if accepted:inspect_docx(data.getvalue())
            else:self.invalid(lambda:inspect_docx(data.getvalue()))

    def test_schema_and_validator_preserve_uppercase_passive_link(self):
        import re
        from tests.support.document_renderer_schema import schemas
        value=f.canonical(link='HTTPS://synthetic.invalid/passive')
        r=self.c.make_request(job_id=f.JOB,revision_id=f.REVISION,canonical=value,canonical_sha256=self.c.digest(self.c.json_bytes(value)),format='pdf',engine=f.ENGINE)
        pattern=schemas()['render_request_v1']['$defs']['span']['properties']['link']['anyOf'][1]['pattern']
        self.assertIsNotNone(re.search(pattern,r.data['canonical']['blocks'][0]['spans'][0]['link']))
        from tests.support.document_renderer_conformance import CORPUS
        for name,schema in schemas().items():
            self.assertEqual(json.loads((CORPUS/(name+'.schema.json')).read_text()),schema)

    def test_same_source_revision_cannot_claim_a_different_canonical(self):
        source=self.source('pdf','frida');source['source_revision_id']=f.REVISION
        self.invalid(lambda:self.make(source=source,source_content=f.pdf()))
        source['canonical']=f.canonical();source['canonical_sha256']=self.request.data['canonical_sha256']
        self.make(source=source,source_content=f.pdf())

    def test_pdf_active_outline_and_nested_action_refused(self):
        from core.document_renderer_artifacts import inspect_pdf
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject,NameObject,TextStringObject
        for outline in (True,False):
            writer=PdfWriter();writer.add_blank_page(width=595,height=842)
            action=DictionaryObject({NameObject('/S'):NameObject('/JavaScript'),NameObject('/JS'):TextStringObject('synthetic')})
            if outline:writer.add_outline_item('Synthetic',0).get_object()[NameObject('/A')]=action
            else:writer._root_object[NameObject('/Synthetic')]=DictionaryObject({NameObject('/A'):action})
            out=io.BytesIO();writer.write(out)
            self.invalid(lambda:inspect_pdf(out.getvalue()))

    def test_pdf_local_outline_and_resource_named_a_remain_passive(self):
        from core.document_renderer_artifacts import inspect_pdf
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject,NameObject,NumberObject
        writer=PdfWriter();page=writer.add_blank_page(width=595,height=842)
        writer.add_outline_item('Synthetic local destination',0)
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/ExtGState'):DictionaryObject({NameObject('/A'):DictionaryObject({NameObject('/Type'):NameObject('/ExtGState'),NameObject('/CA'):NumberObject(1)})})})
        out=io.BytesIO();writer.write(out)
        self.assertEqual(inspect_pdf(out.getvalue()),1)
