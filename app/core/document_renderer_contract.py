"""Closed Writer protocol v1. No server, secret resolution, renderer or transport."""
from dataclasses import dataclass
import hashlib
import json
import re
from uuid import UUID
from .document_canonical import validate_canonical,strict_json_loads
from .document_workshop_contract import DOCUMENT_PROFILE,DocumentWorkshopError,validate_writer_page_count
from .document_renderer_wire import WireMessage,encode_multipart,parse_multipart

MAX_JSON_BYTES=1_048_576
MAX_SOURCE_BYTES=41_943_040
MAX_REQUEST_BYTES=44_040_192
MAX_ARTIFACT_BYTES=16_777_216
MAX_RESULT_BYTES=34_603_008
LIMITS=dict(json_bytes=MAX_JSON_BYTES,source_bytes=MAX_SOURCE_BYTES,request_bytes=MAX_REQUEST_BYTES,
    artifact_bytes=MAX_ARTIFACT_BYTES,result_bytes=MAX_RESULT_BYTES,expanded_bytes=67_108_864,archive_entries=4096,
    active_jobs=1,queue=0,inactivity_seconds=120,words=10000,codepoints=75000,writer_pages=20)
MEDIA_TYPES=dict(docx='application/vnd.openxmlformats-officedocument.wordprocessingml.document',pdf='application/pdf')
REASON_CODES=frozenset(('renderer_ready','renderer_busy','renderer_input_invalid','renderer_source_unsupported',
    'renderer_profile_mismatch','renderer_page_limit','renderer_incomplete','renderer_inactivity',
    'renderer_resource_limit','renderer_cancelled','renderer_job_conflict','renderer_job_lost','renderer_cleanup_failed'))
STATES=frozenset(('rendering','ready','refused','failed','cancelled'))
PHASES=('accepted','source_inspected','canonical_applied','docx_saved','docx_reloaded','layout_stable',
    'writer_pages_measured','pdf_exported','pdf_pages_measured')
PAGE_SEQUENCE=list(PHASES[3:])
STATUS_REASONS=dict(rendering={None},ready={'renderer_ready'},cancelled={'renderer_cancelled'},
    refused={'renderer_busy','renderer_input_invalid','renderer_source_unsupported','renderer_profile_mismatch','renderer_page_limit','renderer_job_conflict'},
    failed={'renderer_incomplete','renderer_inactivity','renderer_resource_limit','renderer_cleanup_failed'})

class RendererError(DocumentWorkshopError):
    def __init__(self,reason_code='renderer_incomplete'):
        super().__init__(reason_code if type(reason_code) is str and reason_code in REASON_CODES else 'renderer_incomplete')


def fail(code='renderer_incomplete'):raise RendererError(code) from None


def check_size(size,limit):
    if type(size) is not int or not 0<=size<=limit:fail('renderer_resource_limit')


def digest(body):return hashlib.sha256(body).hexdigest()


def json_bytes(value):
    try:return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    except (TypeError,ValueError,UnicodeError,RecursionError):fail('renderer_input_invalid')


def read_json(body):
    if type(body) is not bytes:fail()
    check_size(len(body),MAX_JSON_BYTES)
    try:value=strict_json_loads(body.decode('utf-8'))
    except (DocumentWorkshopError,UnicodeError):fail('renderer_input_invalid')
    if type(value) is not dict:fail('renderer_input_invalid')
    return value


def closed(value,keys):
    if type(value) is not dict or set(value)!=set(keys):fail()
    return value


def integer(value,low,high):
    if type(value) is not int or not low<=value<=high:fail()
    return value


def sha(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}',value) is None:fail()
    return value


def identifier(value):
    try:
        if type(value) is not str or str(UUID(value))!=value:fail()
    except (ValueError,TypeError,AttributeError):fail()
    return value


def technical(value):
    if type(value) is not str or re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.+-]{0,95}',value) is None or '..' in value:fail()


def canonical_snapshot(value):
    try:return validate_canonical(value).as_dict()
    except DocumentWorkshopError:fail('renderer_input_invalid')


def validate_engine(value):
    closed(value,('renderer_version','image_id','image_digest','writer_version','uno_version','profile','locale','filters','fonts'))
    for key in ('renderer_version','image_id','writer_version','uno_version','locale'):technical(value[key])
    if type(value['image_digest']) is not str or not value['image_digest'].startswith('sha256:'):fail()
    sha(value['image_digest'][7:])
    if value['profile']!=DOCUMENT_PROFILE:fail('renderer_profile_mismatch')
    closed(value['filters'],('docx','pdf'))
    if value['filters']!=dict(docx='Office Open XML Text',pdf='writer_pdf_Export'):fail('renderer_profile_mismatch')
    if type(value['fonts']) is not list or len(value['fonts'])!=4:fail()
    roles=[]
    for font in value['fonts']:
        closed(font,('role','file_id','sha256','license_id'))
        roles.append(font['role']);technical(font['file_id']);technical(font['license_id']);sha(font['sha256'])
    if roles!=['regular','bold','italic','bold_italic']:fail()
    return read_json(json_bytes(value))


def capabilities(engine):
    return dict(schema='render_capabilities_v1',protocol_version=1,engine=validate_engine(engine),limits=dict(LIMITS))


def validate_capabilities(value,*,expected_engine=None):
    closed(value,('schema','protocol_version','engine','limits'))
    if value['schema']!='render_capabilities_v1' or type(value['protocol_version']) is not int or value['protocol_version']!=1:fail()
    closed(value['limits'],LIMITS)
    if any(type(value['limits'][k]) is not int or value['limits'][k]!=v for k,v in LIMITS.items()):fail()
    engine=validate_engine(value['engine'])
    if expected_engine is not None and json_bytes(engine)!=json_bytes(validate_engine(expected_engine)):fail('renderer_profile_mismatch')
    return value

@dataclass(frozen=True,repr=False)
class RenderRequest:
    envelope_bytes: bytes
    source_content: bytes|None
    @property
    def data(self):return read_json(self.envelope_bytes)
    @property
    def identity(self):return self.data['request_sha256']
    @property
    def wire(self):
        parts=[('request','application/json',self.envelope_bytes)]
        if self.source_content is not None:parts.append(('source',MEDIA_TYPES[self.data['source']['kind']],self.source_content))
        return encode_multipart(parts,limit=MAX_REQUEST_BYTES)


def _source(value,content):
    if value is None:
        if content is not None:fail('renderer_source_unsupported')
        return None
    closed(value,('kind','origin','byte_size','sha256','source_revision_id','canonical','canonical_sha256'))
    if value['kind'] not in ('docx','pdf') or value['origin'] not in ('frida','external') or (value['kind']=='pdf' and value['origin']!='frida'):fail('renderer_source_unsupported')
    if type(content) is not bytes or not content:fail('renderer_source_unsupported')
    check_size(len(content),MAX_SOURCE_BYTES)
    if type(value['byte_size']) is not int or value['byte_size']!=len(content) or sha(value['sha256'])!=digest(content):fail()
    if value['origin']=='external':
        if any(value[k] is not None for k in ('source_revision_id','canonical','canonical_sha256')):fail()
    else:
        identifier(value['source_revision_id'])
        canonical=canonical_snapshot(value['canonical'])
        if sha(value['canonical_sha256'])!=digest(json_bytes(canonical)):fail()
    from .document_renderer_artifacts import inspect_docx,inspect_pdf
    (inspect_docx if value['kind']=='docx' else inspect_pdf)(content)
    return read_json(json_bytes(value))


def make_request(*,job_id,revision_id,canonical,canonical_sha256,format,engine,source=None,source_content=None):
    engine=validate_engine(engine);canonical=canonical_snapshot(canonical)
    identifier(job_id);identifier(revision_id)
    if format not in ('docx','pdf'):fail('renderer_input_invalid')
    if sha(canonical_sha256)!=digest(json_bytes(canonical)):fail('renderer_input_invalid')
    source=_source(source,source_content)
    if source is not None and source['source_revision_id']==revision_id and source['canonical_sha256']!=canonical_sha256:
        fail('renderer_input_invalid')
    value=dict(schema='render_request_v1',protocol_version=1,job_id=job_id,revision_id=revision_id,
        canonical_sha256=canonical_sha256,profile=DOCUMENT_PROFILE,format=format,expected_engine_sha256=digest(json_bytes(engine)),
        canonical=canonical,source=source)
    value['request_sha256']=digest(json_bytes(value));raw=json_bytes(value);check_size(len(raw),MAX_JSON_BYTES)
    request=RenderRequest(raw,source_content);request.wire
    return request


def read_request(wire,*,expected_engine):
    parts=parse_multipart(wire,limit=MAX_REQUEST_BYTES)
    if len(parts) not in (1,2) or parts[0][:2]!=('request','application/json'):fail()
    value=read_json(parts[0][2])
    closed(value,('schema','protocol_version','job_id','revision_id','canonical_sha256','request_sha256','profile','format','expected_engine_sha256','canonical','source'))
    if value['schema']!='render_request_v1' or type(value['protocol_version']) is not int or value['protocol_version']!=1 or value['profile']!=DOCUMENT_PROFILE:fail()
    source=value['source'];content=None
    if len(parts)==2:
        if type(source) is not dict or type(source.get('kind')) is not str or source.get('kind') not in MEDIA_TYPES or parts[1][:2]!=('source',MEDIA_TYPES[source['kind']]):fail()
        content=parts[1][2]
    request=make_request(**{k:value[k] for k in ('job_id','revision_id','canonical','canonical_sha256','format','source')},engine=expected_engine,source_content=content)
    if value!=request.data:fail('renderer_input_invalid')
    return request


def status_value(request,*,status='rendering',reason_code=None,phase='accepted',blocks_completed=0):
    n=len(request.data['canonical']['blocks']);rank=PHASES.index(phase)
    completed=0 if rank==0 else 1+blocks_completed if rank<=2 else n+rank-1
    return dict(schema='render_status_v1',protocol_version=1,job_id=request.data['job_id'],request_sha256=request.identity,
        status=status,reason_code=reason_code,phase=phase,blocks_completed=blocks_completed,units_completed=completed,units_total=n+7)


def validate_status(value,*,request):
    closed(value,('schema','protocol_version','job_id','request_sha256','status','reason_code','phase','blocks_completed','units_completed','units_total'))
    if value['schema']!='render_status_v1' or type(value['protocol_version']) is not int or value['protocol_version']!=1:fail()
    if value['job_id']!=request.data['job_id'] or value['request_sha256']!=request.identity:fail()
    state=value['status']
    if type(state) is not str or state not in STATES:fail('renderer_job_lost')
    if value['reason_code'] is not None and type(value['reason_code']) is not str or value['reason_code'] not in STATUS_REASONS[state]:fail()
    n=len(request.data['canonical']['blocks'])
    integer(value['blocks_completed'],0,n);integer(value['units_completed'],0,n+7);integer(value['units_total'],n+7,n+7)
    if value['phase'] not in PHASES:fail()
    rank=PHASES.index(value['phase']);blocks=value['blocks_completed']
    if rank<2 and blocks!=0 or rank>2 and blocks!=n:fail()
    expected=status_value(request,status=state,reason_code=value['reason_code'],phase=value['phase'],blocks_completed=blocks)
    if value!=expected or state=='ready' and value['units_completed']!=n+7:fail()
    return value



def delete_message(request,*,cancel=False):
    if type(cancel) is not bool:fail()
    value=dict(schema='render_delete_v1',protocol_version=1,job_id=request.data['job_id'],request_sha256=request.identity,
        intent='cancel' if cancel else 'release')
    return WireMessage('application/json',json_bytes(value))


def validate_delete(value,*,request):
    closed(value,('schema','protocol_version','job_id','request_sha256','intent'))
    if value['schema']!='render_delete_v1' or type(value['protocol_version']) is not int or value['protocol_version']!=1 or value['job_id']!=request.data['job_id'] or value['request_sha256']!=request.identity or value['intent'] not in ('cancel','release'):fail()
    return value['intent']


def release_value(request,*,cancel=False):
    return dict(schema='render_release_v1',protocol_version=1,job_id=request.data['job_id'],request_sha256=request.identity,
        state='cancelled' if cancel else 'released',reason_code='renderer_cancelled' if cancel else 'renderer_ready',workspace_removed=True)


def validate_release(value,*,request,cancel=False):
    closed(value,('schema','protocol_version','job_id','request_sha256','state','reason_code','workspace_removed'))
    if type(value['protocol_version']) is not int or value['protocol_version']!=1 or value['schema']!='render_release_v1' or value['job_id']!=request.data['job_id'] or value['request_sha256']!=request.identity:fail()
    outcomes={'released':(('renderer_ready',),True),'cancelled':(('renderer_cancelled',),True),'failed':(('renderer_cleanup_failed','renderer_job_conflict'),False),'lost':(('renderer_job_lost',),False)}
    state=value['state']
    if type(state) is not str or state not in outcomes or type(value['workspace_removed']) is not bool or type(value['reason_code']) is not str or value['reason_code'] not in outcomes[state][0] or value['workspace_removed'] is not outcomes[state][1]:fail()
    if state!=('cancelled' if cancel else 'released'):fail(value['reason_code'])
    return value


def validate_release_message(message,*,request,cancel=False):
    if type(message) is not WireMessage or type(message.http_status) is not int:fail()
    if message.http_status in (404,410):fail('renderer_job_lost')
    if message.content_type!='application/json' or message.http_status not in (200,409,503):fail()
    value=read_json(message.body)
    expected={200:('cancelled','renderer_cancelled') if cancel else ('released','renderer_ready'),
        409:('failed','renderer_job_conflict'),503:('failed','renderer_cleanup_failed')}
    if (value.get('state'),value.get('reason_code'))!=expected[message.http_status]:fail()
    return validate_release(value,request=request,cancel=cancel)


@dataclass(frozen=True,repr=False)
class ValidatedResult:
    manifest_bytes: bytes
    docx: bytes
    pdf: bytes
    @property
    def manifest(self):return read_json(self.manifest_bytes)


def _pages(value):
    try:return validate_writer_page_count(value)
    except DocumentWorkshopError as error:fail('renderer_page_limit' if error.reason_code=='document_page_limit' else 'renderer_incomplete')


def validate_result(wire,*,request,expected_engine):
    if type(wire) is not WireMessage or type(wire.http_status) is not int or wire.http_status!=200:fail()
    if type(request) is not RenderRequest:fail()
    expected=validate_engine(expected_engine)
    request=read_request(request.wire,expected_engine=expected)
    if digest(json_bytes(expected))!=request.data['expected_engine_sha256']:fail('renderer_profile_mismatch')
    parts=parse_multipart(wire,limit=MAX_RESULT_BYTES)
    if parts[0][:2]!=('manifest','application/json'):fail()
    m=read_json(parts[0][2]);r=request.data
    closed(m,('schema','protocol_version','job_id','revision_id','canonical_sha256','request_sha256','source_sha256','status','reason_code','engine','source_evidence','artifacts','page_evidence'))
    if m['schema']!='render_result_v1' or type(m['protocol_version']) is not int or m['protocol_version']!=1:fail()
    if any(m[k]!=r[k] for k in ('job_id','revision_id','canonical_sha256','request_sha256')):fail()
    if m['source_sha256']!=(r['source']['sha256'] if r['source'] else None):fail()
    if json_bytes(validate_engine(m['engine']))!=json_bytes(expected):fail('renderer_profile_mismatch')
    state=m['status']
    if type(state) is not str or state not in STATES-{'rendering'}:fail('renderer_job_lost')
    if type(m['reason_code']) is not str or m['reason_code'] not in STATUS_REASONS[state]:fail()
    if state!='ready':
        if len(parts)!=1 or m['artifacts']!={} or m['page_evidence'] is not None or m['source_evidence'] is not None:fail()
        fail(m['reason_code'])
    if len(parts)!=3 or parts[1][:2]!=('docx',MEDIA_TYPES['docx']) or parts[2][:2]!=('pdf',MEDIA_TYPES['pdf']):fail()
    closed(m['artifacts'],('docx','pdf'));counts=[]
    for fmt,_,body in parts[1:]:
        a=m['artifacts'][fmt];closed(a,('media_type','byte_size','sha256','writer_pages','pdf_pages') if fmt=='pdf' else ('media_type','byte_size','sha256','writer_pages'))
        check_size(len(body),MAX_ARTIFACT_BYTES)
        if not body or a['media_type']!=MEDIA_TYPES[fmt] or type(a['byte_size']) is not int or a['byte_size']!=len(body) or sha(a['sha256'])!=digest(body):fail()
        counts.append(_pages(a['writer_pages']))
        if fmt=='pdf':counts.append(_pages(a['pdf_pages']))
    e=closed(m['page_evidence'],('method','revision_id','canonical_sha256','docx_sha256','pdf_sha256','writer_pages','pdf_pages','sequence'))
    if e['method']!='writer_reload_layout_v1' or e['sequence']!=PAGE_SEQUENCE or any(e[k]!=r[k] for k in ('revision_id','canonical_sha256')):fail()
    if e['docx_sha256']!=digest(parts[1][2]) or e['pdf_sha256']!=digest(parts[2][2]):fail()
    counts.extend((_pages(e['writer_pages']),_pages(e['pdf_pages'])))
    from .document_renderer_artifacts import inspect_docx,inspect_pdf
    inspect_docx(parts[1][2]);counts.append(_pages(inspect_pdf(parts[2][2])))
    if len(set(counts))!=1:fail()
    s=m['source_evidence']
    if r['source'] is None:
        if s is not None:fail()
    else:
        closed(s,('inspection','source_sha256','inventory_complete','representable','repair_used','loss_detected'))
        if s!=dict(inspection='frida_correspondence' if r['source']['origin']=='frida' else 'external_docx_preflight_uno',source_sha256=r['source']['sha256'],inventory_complete=True,representable=True,repair_used=False,loss_detected=False):fail()
        if any(type(s[k]) is not bool for k in ('inventory_complete','representable','repair_used','loss_detected')):fail()
    return ValidatedResult(json_bytes(m),parts[1][2],parts[2][2])
