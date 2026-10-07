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
