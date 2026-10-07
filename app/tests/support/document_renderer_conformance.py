"""Offline conformance runner: no Flask, SQL, provider or operator environment.

PYTHONPATH=app python -m tests.support.document_renderer_conformance
Needs only Python and the existing pypdf reader for binary type/page inspection.
"""
import base64
import json
from pathlib import Path
from core import document_renderer_contract as c

CORPUS=Path(__file__).resolve().parents[1]/'fixtures/document_renderer_v1'


def run(corpus=CORPUS):
    data=json.loads((corpus/'vectors.json').read_text())
    def wire(value):return c.WireMessage(value['content_type'],base64.b64decode(value['body_base64'],validate=True),value['http_status'])
    request=c.read_request(wire(data['request']),expected_engine=data['expected_engine'])
    reports=[]
    for vector in data['vectors']:
        reason=None;message=wire(vector)
        try:
            op=vector['operation']
            if op=='request':c.read_request(message,expected_engine=data['expected_engine'])
            elif op=='result':c.validate_result(message,request=request,expected_engine=data['expected_engine'])
            elif op=='capabilities':c.validate_capabilities(c.read_json(message.body),expected_engine=data['expected_engine'])
            elif op=='status':c.validate_status(c.read_json(message.body),request=request)
            elif op=='delete':c.validate_delete(c.read_json(message.body),request=request)
            elif op=='release':c.validate_release(c.read_json(message.body),request=request,cancel=vector.get('cancel',False))
            else:raise AssertionError('unknown vector operation')
        except c.RendererError as error:reason=error.reason_code
        if reason!=vector['reason_code']:raise AssertionError('conformance mismatch '+vector['name'])
        reports.append(dict(name=vector['name'],accepted=reason is None,reason_code=reason))
    return reports

if __name__=='__main__':print(json.dumps(dict(synthetic_only=True,vectors=run()),indent=2))
