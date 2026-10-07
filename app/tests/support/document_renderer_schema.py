"""Structural Draft 2020-12 schemas for the closed M8-C protocol.

Cross-field hashes, Unicode volume, actual bytes, source authority and lifecycle
are checked by document_renderer_contract/document_rendering, not JSON Schema.
"""
from core import document_renderer_contract as c


def schemas():
    def obj(properties):return dict(type='object',properties=properties,required=list(properties),additionalProperties=False)
    def arr(items,**kw):return dict(type='array',items=items,**kw)
    def ref(name):return {'$ref':'#/$defs/'+name}
    def nullable(value):return {'anyOf':[{'type':'null'},value]}
    def const(value):return {'const':value,'type':'integer' if type(value) is int else 'string'}
    integer=lambda lo,hi:dict(type='integer',minimum=lo,maximum=hi)
    boolean={'type':'boolean'}
    technical=dict(type='string',pattern=r'^[A-Za-z0-9][A-Za-z0-9_.+-]{0,95}$',not_={})
    technical.pop('not_');technical['not']={'pattern':r'\.\.'}
    sha=dict(type='string',pattern='^[0-9a-f]{64}$')
    uuid=dict(type='string',pattern='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    text=dict(type='string',minLength=1)
    span=obj(dict(text=text,bold=boolean,italic=boolean,link=nullable(dict(type='string',pattern='^[hH][tT][tT][pP][sS]?://',minLength=1))))
    spans=arr(ref('span'),minItems=1)
    blocks=[]
    for kind in ('paragraph','heading','quote'):
        fields=dict(type=const(kind),spans=spans)
        if kind=='heading':fields['level']=integer(1,6)
        blocks.append(obj(fields))
    blocks += [obj(dict(type=const('list'),ordered=boolean,items=arr(spans,minItems=1))),
        obj(dict(type=const('table'),rows=arr(arr(arr(ref('span')),minItems=1),minItems=1))),obj(dict(type=const('page_break')))]
    canonical=obj(dict(schema_version=const(1),profile=const(c.DOCUMENT_PROFILE),blocks=arr({'oneOf':blocks},minItems=1)))
    font=obj(dict(role=dict(type='string',enum=['regular','bold','italic','bold_italic']),file_id=technical,sha256=sha,license_id=technical))
    engine=obj(dict(renderer_version=technical,image_id=technical,image_digest=dict(type='string',pattern='^sha256:[0-9a-f]{64}$'),
        writer_version=technical,uno_version=technical,profile=const(c.DOCUMENT_PROFILE),locale=technical,
        filters=obj(dict(docx=const('Office Open XML Text'),pdf=const('writer_pdf_Export'))),
        fonts=dict(type='array',minItems=4,maxItems=4,prefixItems=[obj(font['properties']|{'role':const(role)}) for role in ('regular','bold','italic','bold_italic')],items=False)))
    source=obj(dict(kind=dict(type='string',enum=['docx','pdf']),origin=dict(type='string',enum=['frida','external']),byte_size=integer(1,c.MAX_SOURCE_BYTES),
        sha256=sha,source_revision_id=nullable(uuid),canonical=nullable(ref('canonical')),canonical_sha256=nullable(sha)))
    source['allOf']=[{'if':{'properties':{'origin':const('external')}},'then':{'properties':{'kind':const('docx'),'source_revision_id':{'type':'null'},'canonical':{'type':'null'},'canonical_sha256':{'type':'null'}}},
        'else':{'properties':{'source_revision_id':uuid,'canonical':ref('canonical'),'canonical_sha256':sha}}}]
    def envelope(name,fields):return obj(dict(schema=const(name),protocol_version=const(1),**fields))
    request=envelope('render_request_v1',dict(job_id=uuid,revision_id=uuid,canonical_sha256=sha,request_sha256=sha,profile=const(c.DOCUMENT_PROFILE),
        format=dict(type='string',enum=['docx','pdf']),expected_engine_sha256=sha,canonical=ref('canonical'),source=nullable(ref('source'))))
    capabilities=envelope('render_capabilities_v1',dict(engine=ref('engine'),limits=obj({k:const(v) for k,v in c.LIMITS.items()})))
    page=obj(dict(method=const('writer_reload_layout_v1'),revision_id=uuid,canonical_sha256=sha,docx_sha256=sha,pdf_sha256=sha,
        writer_pages=integer(1,20),pdf_pages=integer(1,20),sequence={'const':c.PAGE_SEQUENCE,'type':'array'}))
    artifacts={fmt:obj(dict(media_type=const(c.MEDIA_TYPES[fmt]),byte_size=integer(1,c.MAX_ARTIFACT_BYTES),sha256=sha,writer_pages=integer(1,20),
        **({'pdf_pages':integer(1,20)} if fmt=='pdf' else {}))) for fmt in ('docx','pdf')}
    source_evidence=obj(dict(inspection=dict(type='string',enum=['frida_correspondence','external_docx_preflight_uno']),source_sha256=sha,
        inventory_complete={'const':True,'type':'boolean'},representable={'const':True,'type':'boolean'},repair_used={'const':False,'type':'boolean'},loss_detected={'const':False,'type':'boolean'}))
    result=envelope('render_result_v1',dict(job_id=uuid,revision_id=uuid,canonical_sha256=sha,request_sha256=sha,source_sha256=nullable(sha),
        status=dict(type='string',enum=['ready','refused','failed','cancelled']),reason_code=dict(type='string',enum=sorted(c.REASON_CODES)),engine=ref('engine'),
        source_evidence=nullable(ref('source_evidence')),artifacts={'oneOf':[obj(artifacts),obj({})]},page_evidence=nullable(ref('pages'))))
    result['allOf']=[{'if':{'properties':{'status':const('ready')}},'then':{'properties':{'artifacts':obj(artifacts),'page_evidence':ref('pages')}},
        'else':{'properties':{'artifacts':obj({}),'page_evidence':{'type':'null'},'source_evidence':{'type':'null'}}}}]
    status=envelope('render_status_v1',dict(job_id=uuid,request_sha256=sha,status=dict(type='string',enum=sorted(c.STATES)),
        reason_code=nullable(dict(type='string',enum=sorted(c.REASON_CODES))),phase=dict(type='string',enum=list(c.PHASES)),
        blocks_completed=integer(0,c.MAX_JSON_BYTES),units_completed=integer(0,c.MAX_JSON_BYTES+7),units_total=integer(8,c.MAX_JSON_BYTES+7)))
    for target in (status,result):
        target.setdefault('allOf',[]).extend({'if':{'properties':{'status':const(state)}},'then':{'properties':{'reason_code':{'enum':sorted(reasons,key=lambda x:str(x))}}}} for state,reasons in c.STATUS_REASONS.items() if state in target['properties']['status']['enum'])
    delete=envelope('render_delete_v1',dict(job_id=uuid,request_sha256=sha,intent=dict(type='string',enum=['cancel','release'])))
    release=envelope('render_release_v1',dict(job_id=uuid,request_sha256=sha,state=dict(type='string',enum=['released','cancelled','failed','lost']),
        reason_code=dict(type='string',enum=['renderer_ready','renderer_cancelled','renderer_cleanup_failed','renderer_job_lost','renderer_job_conflict']),workspace_removed=boolean))
    release['allOf']=[{'if':{'properties':{'state':const(state)}},'then':{'properties':{'reason_code':const(reason),'workspace_removed':{'const':removed,'type':'boolean'}}}} for state,reason,removed in [('released','renderer_ready',True),('cancelled','renderer_cancelled',True),('lost','renderer_job_lost',False)]]
    release['allOf'].append({'if':{'properties':{'state':const('failed')}},'then':{'properties':{'reason_code':{'enum':['renderer_cleanup_failed','renderer_job_conflict']},'workspace_removed':{'const':False,'type':'boolean'}}}})
    defs=dict(span=span,canonical=canonical,engine=engine,source=source,pages=page,source_evidence=source_evidence)
    return {name:dict({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:frida:writer:'+name,'$defs':defs},**schema)
        for name,schema in [('render_request_v1',request),('render_result_v1',result),('render_capabilities_v1',capabilities),('render_status_v1',status),('render_delete_v1',delete),('render_release_v1',release)]}
