"""Bounded binary type inspection; no render, extraction to disk or network."""
import io
import posixpath
import re
import subprocess
import sys
from pathlib import Path
import zipfile
if __name__!='__main__':
    from . import workspace_document_source_worker as reader

CT='{http://schemas.openxmlformats.org/package/2006/content-types}'
REL='{http://schemas.openxmlformats.org/package/2006/relationships}'
WORD='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
WORD14='{http://schemas.microsoft.com/office/word/2010/wordml}'
VML='{urn:schemas-microsoft-com:vml}'
# SDK CT_Body children. Existing profile guards still refuse active content
# and revisions; membership here does not grant permission to those features.
BODY_CHILDREN={WORD+name for name in (
    'altChunk','customXml','sdt','p','tbl','proofErr','permStart','permEnd',
    'bookmarkStart','bookmarkEnd','commentRangeStart','commentRangeEnd',
    'moveFromRangeStart','moveFromRangeEnd','moveToRangeStart','moveToRangeEnd',
    'customXmlInsRangeStart','customXmlInsRangeEnd','customXmlDelRangeStart','customXmlDelRangeEnd',
    'customXmlMoveFromRangeStart','customXmlMoveFromRangeEnd','customXmlMoveToRangeStart','customXmlMoveToRangeEnd',
    'ins','del','moveFrom','moveTo','contentPart','sectPr')}
BODY_CHILDREN.update(WORD14+name for name in (
    'customXmlConflictInsRangeStart','customXmlConflictInsRangeEnd',
    'customXmlConflictDelRangeStart','customXmlConflictDelRangeEnd','conflictIns','conflictDel'))


def _check_docx_structure(root):
    """Main-part skeleton only, not universal XSD validation or layout proof.

    CT_Document is background? then body?. CT_Body has block/metadata children
    followed by sectPr?. Prefixes/attributes and paragraph/table interiors do
    not determine the skeleton. No document bytes are repaired.
    """
    from .document_renderer_contract import fail
    def element_only(node):
        if any(char not in ' \t\r\n' for text in [node.text, *(child.tail for child in node)] for char in (text or '')):fail()
    if root.tag!=WORD+'document':fail()
    element_only(root)
    children=list(root)
    tags=[child.tag for child in children]
    if tags not in ([],[WORD+'background'],[WORD+'body'],[WORD+'background',WORD+'body']):fail()
    # These QNames belong only at these main-part positions. v:background is
    # distinct and allowed inside w:background; nested pPr/sectPr stays legal.
    for node in root.iter():
        if node.tag==WORD+'document' and node is not root:fail()
        if node.tag in (WORD+'background',WORD+'body') and node not in children:fail()
    for node in children:
        element_only(node)
        if node.tag==WORD+'background':
            if [child.tag for child in node] not in ([],[VML+'background']):fail()
        else:
            blocks=list(node)
            if any(child.tag not in BODY_CHILDREN for child in blocks):fail()
            sections=[i for i,child in enumerate(blocks) if child.tag==WORD+'sectPr']
            if sections and sections!=[len(blocks)-1]:fail()


def _inspect_docx(content):
    from .document_renderer_contract import fail
    try:
        # Reuse complete-source archive traversal/CRC/expansion/XML guards.
        reader.preflight_archive(content,'docx')
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            types=reader.xml_root(archive.read('[Content_Types].xml'))
            rels=reader.xml_root(archive.read('_rels/.rels'))
            if types.tag!=CT+'Types' or rels.tag!=REL+'Relationships':fail()
            main=[n for n in types if n.tag==CT+'Override' and n.get('PartName')=='/word/document.xml']
            if len(main)!=1 or main[0].get('ContentType')!='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml':fail()
            office=[n for n in rels if n.get('Type','').endswith('/officeDocument')]
            if len(office)!=1 or office[0].get('Target')!='word/document.xml' or office[0].get('TargetMode') is not None:fail()
            from .document_canonical import _link
            # Tracked revisions/dynamic fields cannot disappear into V1 text.
            for name in archive.namelist():
                if name.endswith(('.xml','.rels')):
                    root=reader.xml_root(archive.read(name))
                    if name=='word/document.xml':_check_docx_structure(root)
                    for node in root.iter():
                        if node.tag==REL+'Relationship':
                            target=node.get('Target','');mode=node.get('TargetMode')
                            if mode=='External':
                                if not node.get('Type','').endswith('/hyperlink') or _link(target) is None:fail()
                            else:
                                if mode is not None or not target or target.startswith('/') or any(ch in target for ch in ('\\',':','#')) or re.search('%[0-9a-fA-F]{2}',target):fail()
                                base='' if name=='_rels/.rels' else posixpath.dirname(posixpath.dirname(name))
                                resolved=posixpath.normpath(posixpath.join(base,target))
                                if resolved.startswith('../') or resolved not in archive.namelist():fail()
                        if node.tag.rsplit('}',1)[-1] in {'ins','del','moveFrom','moveTo','fldChar','sdt','subDoc'}:fail('renderer_source_unsupported')
    except SystemExit:
        fail('renderer_source_unsupported')
    except Exception:
        fail()



def _check_pdf_graph(root):
    """Visit reachable objects, including outlines; permit only passive actions."""
    from .document_renderer_contract import fail
    from pypdf.generic import IndirectObject
    stack=[root];seen=set();nodes=0
    while stack:
        value=stack.pop()
        if isinstance(value,IndirectObject):
            key=('indirect',value.idnum,value.generation)
            if key in seen:continue
            seen.add(key);value=value.get_object()
        if isinstance(value,(dict,list)):
            key=('direct',id(value))
            if key in seen:continue
            seen.add(key);nodes+=1
            if nodes>65536:fail('renderer_resource_limit')
        if isinstance(value,dict):
            # Resource names are arbitrary: /A can name an ExtGState/font.
            # Inspect actual action dictionaries and outline action carriers.
            actions=('/GoTo','/GoToR','/GoToE','/Launch','/Thread','/URI','/Sound','/Movie','/Hide','/Named','/SubmitForm','/ResetForm','/ImportData','/JavaScript','/SetOCGState','/Rendition','/Trans','/GoTo3DView','/RichMediaExecute')
            if '/A' in value and '/Title' in value and '/Parent' in value:
                reader.check_pdf_link({'/Subtype':'/Link','/A':value['/A']})
            if value.get('/Type')=='/Action' or value.get('/S') in actions:
                reader.check_pdf_link({'/Subtype':'/Link','/A':value})
            stack.extend(value.values())
        elif isinstance(value,list):stack.extend(value)


def _inspect_pdf(content):
    from .document_renderer_contract import fail
    try:
        from pypdf import PdfReader
        if not content.startswith(b'%PDF-') or not content.rstrip().endswith(b'%%EOF'):fail()
        # Existing reader primitives reject active annotations/fetch actions.
        pdf=PdfReader(io.BytesIO(content),strict=True)
        if pdf.is_encrypted:fail()
        root=pdf.trailer['/Root']
        _check_pdf_graph(root)
        if any(k in root for k in ('/AcroForm','/OpenAction','/AA')):fail()
        names=root.get('/Names',{})
        if hasattr(names,'get_object'):names=names.get_object()
        if any(k in names for k in ('/JavaScript','/EmbeddedFiles')):fail()
        pages=list(pdf.pages)
        if not pages:fail()
        for page in pages:
            if '/AA' in page:fail()
            resources=page.get('/Resources',{})
            if hasattr(resources,'get_object'):resources=resources.get_object()
            if resources.get('/XObject'):fail('renderer_source_unsupported')
            stream=page.get_contents()
            if stream is not None and any(op==b'INLINE IMAGE' for _,op in stream.operations):fail('renderer_source_unsupported')
            for annotation in page.get('/Annots',[]):reader.check_pdf_link(annotation.get_object())
        return len(pages)
    except SystemExit:
        fail('renderer_source_unsupported')
    except Exception:
        fail()


def _inspect(content,kind):
    from .document_renderer_contract import fail,check_size,MAX_SOURCE_BYTES
    if type(content) is not bytes or not content:fail()
    check_size(len(content),MAX_SOURCE_BYTES)
    try:
        process=subprocess.run([sys.executable,'-I','-B',str(Path(__file__).resolve()),kind],
            input=content,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            env={'PYTHONDONTWRITEBYTECODE':'1'},close_fds=True,check=False)
    except (OSError,ValueError):fail()
    if process.returncode or not process.stdout.isdigit() or len(process.stdout)>8:fail('renderer_source_unsupported')
    return int(process.stdout)


def inspect_docx(content):return _inspect(content,'docx')


def inspect_pdf(content):return _inspect(content,'pdf')


if __name__=='__main__':
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,)*2)
    resource.setrlimit(resource.RLIMIT_CPU,(20,20))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
    from core.document_renderer_artifacts import _inspect_docx,_inspect_pdf
    try:
        if len(sys.argv)!=2 or sys.argv[1] not in ('docx','pdf'):raise ValueError()
        data=sys.stdin.buffer.read(40*1024*1024+1)
        if len(data)>40*1024*1024:raise ValueError()
        pages=_inspect_docx(data) or 0 if sys.argv[1]=='docx' else _inspect_pdf(data)
        sys.stdout.write(str(pages))
    except BaseException:sys.exit(21)
