"""Synthetic M8-C corpus. No Writer/layout/font claim, no Exports renderer."""
import copy
import hashlib
import io
import json
import zipfile

JOB='10000000-0000-4000-8000-000000000001'
REVISION='10000000-0000-4000-8000-000000000002'
SOURCE_REVISION='10000000-0000-4000-8000-000000000004'
ENGINE=dict(renderer_version='synthetic-m8c-1',image_id='synthetic-writer',image_digest='sha256:'+'a'*64,
    writer_version='synthetic-writer-0',uno_version='synthetic-uno-0',profile='frida_document_v1',locale='fr-FR',
    filters=dict(docx='Office Open XML Text',pdf='writer_pdf_Export'),
    fonts=[dict(role=role,file_id='synthetic-'+role+'.ttf',sha256='b'*64,license_id='synthetic-license')
           for role in ('regular','bold','italic','bold_italic')])

def canonical(text='Synthetic document',link=None):
    return dict(schema_version=1,profile='frida_document_v1',blocks=[dict(type='paragraph',spans=[
        dict(text=text,bold=False,italic=False,link=link)])])

def docx():
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as z:
        def write(name,data):
            info=zipfile.ZipInfo(name,date_time=(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
        write('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        write('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        write('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Synthetic document</w:t></w:r></w:p></w:body></w:document>')
    return out.getvalue()

def pdf(pages=1):
    from pypdf import PdfWriter
    writer=PdfWriter()
    for _ in range(pages):writer.add_blank_page(width=595.276,height=841.89)
    out=io.BytesIO();writer.write(out);return out.getvalue()

def result(c,request,*,pages=1):
    d,p=docx(),pdf(pages)
    r=request.data
    manifest=dict(schema='render_result_v1',protocol_version=1,job_id=r['job_id'],revision_id=r['revision_id'],
        canonical_sha256=r['canonical_sha256'],request_sha256=request.identity,source_sha256=r['source']['sha256'] if r['source'] else None,
        status='ready',reason_code='renderer_ready',engine=copy.deepcopy(ENGINE),
        source_evidence=None if r['source'] is None else dict(inspection='frida_correspondence' if r['source']['origin']=='frida' else 'external_docx_preflight_uno',
            source_sha256=r['source']['sha256'],inventory_complete=True,representable=True,repair_used=False,loss_detected=False),
        artifacts={fmt:dict(media_type=c.MEDIA_TYPES[fmt],byte_size=len(body),sha256=c.digest(body),writer_pages=pages,
                       **({'pdf_pages':pages} if fmt=='pdf' else {})) for fmt,body in (('docx',d),('pdf',p))},
        page_evidence=dict(method='writer_reload_layout_v1',revision_id=r['revision_id'],canonical_sha256=r['canonical_sha256'],
            docx_sha256=c.digest(d),pdf_sha256=c.digest(p),writer_pages=pages,pdf_pages=pages,
            sequence=['docx_saved','docx_reloaded','layout_stable','writer_pages_measured','pdf_exported','pdf_pages_measured']))
    return manifest,d,p

def response(c,manifest,d,p):
    return c.encode_multipart([('manifest','application/json',c.json_bytes(manifest)),('docx',c.MEDIA_TYPES['docx'],d),('pdf',c.MEDIA_TYPES['pdf'],p)],limit=c.MAX_RESULT_BYTES)


def external_docx():
    """Independent synthetic OOXML, authored here; never emitted by Frida/Writer.

    Same ZIP builder as M2; explicit styles, flat numbering and a 2x2 table.
    No canonical/revision/receipt is embedded or used to generate the bytes.
    """
    from tests.unit.core.test_workspace_document_source_extraction_m2 import archive_bytes, WORD
    return archive_bytes([
        ('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
         '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
         '<Default Extension="xml" ContentType="application/xml"/>'
         '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
         '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
         '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/></Types>'),
        ('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
         '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'),
        ('word/_rels/document.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
         '<Relationship Id="styles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
         '<Relationship Id="numbers" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/></Relationships>'),
        ('word/styles.xml', f'<w:styles xmlns:w="{WORD}"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
         '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>'
         '<w:pPr><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/></w:rPr></w:style></w:styles>'),
        ('word/numbering.xml', f'<w:numbering xmlns:w="{WORD}"><w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="singleLevel"/>'
         '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl></w:abstractNum>'
         '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>'),
        ('word/document.xml', f'<w:document xmlns:w="{WORD}"><w:body>'
         '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>External title</w:t></w:r></w:p>'
         '<w:p><w:r><w:t xml:space="preserve">Original text </w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>bold</w:t></w:r>'
         '<w:r><w:t xml:space="preserve"> and </w:t></w:r><w:r><w:rPr><w:i/></w:rPr><w:t>italic</w:t></w:r></w:p>'
         '<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>First item</w:t></w:r></w:p>'
         '<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>Second item</w:t></w:r></w:p>'
         '<w:tbl><w:tblPr><w:tblW w:w="9000" w:type="dxa"/></w:tblPr><w:tblGrid><w:gridCol w:w="4500"/><w:gridCol w:w="4500"/></w:tblGrid>'
         '<w:tr><w:tc><w:tcPr><w:tcW w:w="4500" w:type="dxa"/></w:tcPr><w:p><w:r><w:t>A</w:t></w:r></w:p></w:tc>'
         '<w:tc><w:tcPr><w:tcW w:w="4500" w:type="dxa"/></w:tcPr><w:p><w:r><w:t>B</w:t></w:r></w:p></w:tc></w:tr>'
         '<w:tr><w:tc><w:tcPr><w:tcW w:w="4500" w:type="dxa"/></w:tcPr><w:p><w:r><w:t>C</w:t></w:r></w:p></w:tc>'
         '<w:tc><w:tcPr><w:tcW w:w="4500" w:type="dxa"/></w:tcPr><w:p><w:r><w:t>D</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
         '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr>'
         '</w:body></w:document>')])


def external_candidate(text='Revised text '):
    """Synthetic model answer; independent of the OOXML fixture writer above."""
    from tests.unit.core.test_document_workshop_canonical_paths import span
    value=canonical()
    value['blocks']=[dict(type='heading',level=1,spans=[span('External title')]),
        dict(type='paragraph',spans=[span(text),span('bold')|dict(bold=True),span(' and '),span('italic')|dict(italic=True)]),
        dict(type='list',ordered=True,items=[[span('First item')],[span('Second item')]]),
        dict(type='table',rows=[[[span('A')],[span('B')]],[[span('C')],[span('D')]]])]
    return value
