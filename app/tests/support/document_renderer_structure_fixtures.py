"""Synthetic main-part structures; no Writer fidelity or universal OOXML claim."""
import io
import zipfile
from tests.support import document_renderer_fixtures as f

WORD = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
WORD14 = 'http://schemas.microsoft.com/office/word/2010/wordml'
PARAGRAPH = '<w:p><w:r><w:t>Synthetic document</w:t></w:r></w:p>'


def document(children='', *, declarations=''):
    return f'<w:document xmlns:w="{WORD}" {declarations}>{children}</w:document>'


INVALID_AUD01 = {
    'two_bodies': document(f'<w:body>{PARAGRAPH}</w:body><w:body>{PARAGRAPH}</w:body>'),
    'foreign_root_child': document('<foreign>Not a WordprocessingML body</foreign>'),
}


def replace_document(content, xml):
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(content)) as old, zipfile.ZipFile(out, 'w') as new:
        for member in old.infolist():
            new.writestr(member, xml.encode('utf-8') if member.filename == 'word/document.xml' else old.read(member))
    return out.getvalue()


def pair(c, request, xml):
    manifest, docx, pdf = f.result(c, request)
    docx = replace_document(docx, xml)
    manifest['artifacts']['docx'].update(byte_size=len(docx), sha256=c.digest(docx))
    manifest['page_evidence']['docx_sha256'] = c.digest(docx)
    return f.response(c, manifest, docx, pdf), docx
