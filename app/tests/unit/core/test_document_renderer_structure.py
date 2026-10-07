"""AUD-01: real child inspection, complete pair, source and collection fences."""
import io
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from core import document_renderer_artifacts as artifacts
from core import document_renderer_contract as c
from core.document_rendering import RenderingSession
from tests.support import document_renderer_fixtures as f
from tests.support import document_renderer_structure_fixtures as s
from tests.support.document_renderer_fake import FakeRenderer


class RendererStructureTests(unittest.TestCase):
    def make(self, **kw):
        return c.make_request(job_id=f.JOB, revision_id=f.REVISION, canonical=f.canonical(),
            canonical_sha256=c.digest(c.json_bytes(f.canonical())), format='docx', engine=f.ENGINE, **kw)

    def refused(self, callback):
        with self.assertRaises(c.RendererError) as caught:
            callback()
        self.assertEqual(str(caught.exception), 'renderer_source_unsupported')

    def structural_probe(self, xml):
        request = self.make()
        wire, docx = s.pair(c, request, xml)
        self.refused(lambda: artifacts.inspect_docx(docx))
        self.refused(lambda: c.validate_result(wire, request=request, expected_engine=f.ENGINE))

    def accepted(self, xml):
        request = self.make()
        wire, docx = s.pair(c, request, xml)
        self.assertEqual(artifacts.inspect_docx(docx), 0)
        self.assertEqual(c.validate_result(wire, request=request, expected_engine=f.ENGINE).docx, docx)

    def test_two_bodies_and_foreign_root_child_refused_before_release(self):
        for name, xml in s.INVALID_AUD01.items():
            with self.subTest(name=name):
                self.structural_probe(xml)
                request = self.make()
                wire, _ = s.pair(c, request, xml)
                worker = FakeRenderer()
                events = []
                validate = c.validate_result
                def result(req):
                    self.assertEqual(req.identity, request.identity)
                    worker.events.append('result')
                    events.append('result')
                    return wire
                def checked(*args, **kw):
                    try:
                        return validate(*args, **kw)
                    except c.RendererError:
                        events.append('validation_refused')
                        raise
                cancel = worker.cancel_release
                def abandoned(req, *, cancel=False):
                    self.assertEqual(req.identity, request.identity)
                    self.assertTrue(cancel)
                    events.append('abandon')
                    return abandoned_original(req, cancel=cancel)
                abandoned_original = cancel
                worker.result = result
                worker.cancel_release = abandoned
                session = RenderingSession(client=worker, expected_engine=f.ENGINE, wait=lambda: None)
                with patch.object(c, 'validate_result', checked):
                    self.refused(lambda: session.collect(request, check=lambda: None))
                self.assertEqual(events, ['result', 'validation_refused', 'abandon'])
                self.assertEqual(worker.events, ['capabilities', 'submit', 'status', 'result', 'cancel'])
                self.assertIsNone(session.collected)

    def test_optional_body_and_background_structures_preserved(self):
        for children in ('', '<w:body/>', '<w:background w:color="FFFFFF"/>',
                '<w:background/><w:body/>',
                '<w:background><v:background/></w:background><w:body/>'):
            with self.subTest(children=children):
                self.accepted(s.document(children, declarations='xmlns:v="urn:schemas-microsoft-com:vml"'))

    def test_equivalent_prefixes_default_namespace_and_extra_attributes_preserved(self):
        for xml in (s.document('<w:body>'+s.PARAGRAPH+'</w:body>').replace('w:', 'word:').replace('xmlns:w=', 'xmlns:word='),
                f'<document xmlns="{s.WORD}"><body><p><r><t>Synthetic document</t></r></p></body></document>',
                s.document('<w:body><w:p w14:paraId="12345678"><w:r><w:t>Synthetic</w:t></w:r></w:p></w:body>',
                    declarations=f'xmlns:w14="{s.WORD14}" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" mc:Ignorable="w14"')):
            self.accepted(xml)

    def test_paragraphs_titles_styles_tables_lists_breaks_and_passive_links_preserved(self):
        body = ('<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:rPr><w:b/><w:i/></w:rPr><w:t>Title</w:t></w:r></w:p>'
            '<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>List</w:t><w:br w:type="page"/></w:r></w:p>'
            '<w:tbl><w:tblPr/><w:tblGrid><w:gridCol w:w="100"/></w:tblGrid><w:tr><w:tc><w:p><w:r><w:t>Cell</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
            '<w:p><w:hyperlink r:id="rIdLink"><w:r><w:t>Passive</w:t></w:r></w:hyperlink></w:p>')
        request = self.make()
        manifest, docx, pdf = f.result(c, request)
        docx = s.replace_document(docx, s.document('<w:body>'+body+'</w:body>',
            declarations='xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'))
        out = io.BytesIO(docx)
        with zipfile.ZipFile(out, 'a') as archive:
            archive.writestr('word/_rels/document.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdLink" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://synthetic.invalid/passive" TargetMode="External"/></Relationships>')
        docx = out.getvalue()
        manifest['artifacts']['docx'].update(byte_size=len(docx), sha256=c.digest(docx))
        manifest['page_evidence']['docx_sha256'] = c.digest(docx)
        self.assertEqual(c.validate_result(f.response(c, manifest, docx, pdf), request=request, expected_engine=f.ENGINE).docx, docx)

    def test_body_metadata_and_paragraph_section_properties_preserved(self):
        body = ('<w:proofErr w:type="spellStart"/><w:permStart w:id="1"/><w:permEnd w:id="1"/>'
            '<w:bookmarkStart w:id="2" w:name="Synthetic"/><w:bookmarkEnd w:id="2"/>'
            '<w:commentRangeStart w:id="3"/><w:commentRangeEnd w:id="3"/>'
            '<w14:customXmlConflictInsRangeStart w:id="4"/><w14:customXmlConflictInsRangeEnd w:id="4"/>'
            '<w:p><w:pPr><w:sectPr/></w:pPr><w:r><w:t>Synthetic</w:t></w:r></w:p><w:sectPr/>')
        self.accepted(s.document('<w:body>'+body+'</w:body>', declarations=f'xmlns:w14="{s.WORD14}"'))

    def test_skeleton_qnames_placement_cardinality_and_order_refused(self):
        for children in ('<w:background/><w:background/>', '<w:body/><w:background/>',
                '<fake:body/>', '<w:body><w:p><w:body/></w:p></w:body>',
                '<w:body><w:document/></w:body>', '<w:body><w:p><w:background/></w:p></w:body>',
                '<w:background><w:body/></w:background>',
                '<w:background><v:background/><v:background/></w:background>'):
            with self.subTest(children=children):
                self.structural_probe(s.document(children, declarations='xmlns:fake="urn:synthetic" xmlns:v="urn:schemas-microsoft-com:vml"'))

    def test_body_direct_children_and_terminal_section_refused(self):
        for body in ('<foreign/>', '<w:r><w:t>Run outside paragraph</w:t></w:r>',
                '<w:sectPr/><w:sectPr/>', '<w:sectPr/>'+s.PARAGRAPH,
                '<fake:p/>', '<w:background/>'):
            with self.subTest(body=body):
                self.structural_probe(s.document('<w:body>'+body+'</w:body>', declarations='xmlns:fake="urn:synthetic"'))

    def test_element_only_xml_whitespace_preserved_other_text_refused(self):
        self.accepted(s.document(' \t\r\n<w:body>\n'+s.PARAGRAPH+' \t\r\n</w:body>\n'))
        for children in ('text<w:body/>', '<w:body/>text', '\u00a0<w:body/>',
                '<w:body>text'+s.PARAGRAPH+'</w:body>', '<w:body>'+s.PARAGRAPH+'\u00a0</w:body>',
                '<w:background>text</w:background>'):
            with self.subTest(children=children):
                self.structural_probe(s.document(children))

    def test_external_and_frida_source_admission_uses_same_structural_guard(self):
        for origin in ('external', 'frida'):
            for xml in (s.document('<w:body>'+s.PARAGRAPH+'</w:body>'), *s.INVALID_AUD01.values()):
                content = s.replace_document(f.docx(), xml)
                source = dict(kind='docx', origin=origin, byte_size=len(content), sha256=c.digest(content),
                    source_revision_id=f.SOURCE_REVISION if origin=='frida' else None,
                    canonical=f.canonical('Previous revision') if origin=='frida' else None,
                    canonical_sha256=c.digest(c.json_bytes(f.canonical('Previous revision'))) if origin=='frida' else None)
                with self.subTest(origin=origin, xml=xml):
                    if xml in s.INVALID_AUD01.values():
                        self.refused(lambda: self.make(source=source, source_content=content))
                    else:
                        self.assertEqual(self.make(source=source, source_content=content).source_content, content)

    def test_malformed_xml_and_active_content_still_refused(self):
        for xml in (f'<w:document xmlns:w="{s.WORD}"><w:body>',
                s.document('<w:body><w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r></w:p></w:body>')):
            self.structural_probe(xml)

    def test_causal_detector_catches_only_structural_guard_neutralized_in_real_child(self):
        original = artifacts.subprocess.run
        script = str(Path(artifacts.__file__).resolve())
        # Test-only child mutation: run the unchanged fixed entry point, with
        # identical resource limits, archive/XML/relationship/content guards.
        code = ("import runpy,sys;sys.path.insert(0,"+repr(str(Path(script).parent.parent))+");"
            "from core import document_renderer_artifacts as a;"
            "a._check_docx_structure=lambda root:None;"
            "sys.argv=["+repr(script)+",'docx'];runpy.run_path("+repr(script)+",run_name='__main__')")
        def neutralized(argv, **kw):
            if argv[-1]=='docx':
                argv=[argv[0], '-I', '-B', '-c', code]
            return original(argv, **kw)
        with patch.object(artifacts.subprocess, 'run', neutralized):
            for xml in s.INVALID_AUD01.values():
                with self.assertRaises(AssertionError):
                    self.structural_probe(xml)
                request = self.make()
                wire, docx = s.pair(c, request, xml)
                self.assertEqual(c.validate_result(wire, request=request, expected_engine=f.ENGINE).docx, docx)
            self.structural_probe(f'<w:document xmlns:w="{s.WORD}"><w:body>')
