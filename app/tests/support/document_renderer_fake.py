"""Stateful synthetic worker/client implementing M8-C, no network or engine."""
from core import document_renderer_contract as c
from tests.support import document_renderer_fixtures as f

class FakeRenderer:
    def __init__(self,*,status_change=None,release_change=None,result_change=None,on_status=None,progress=None):
        self.events=[];self.jobs={};self.active=None;self.executions=0
        self.status_change=status_change or {};self.release_change=release_change or {}
        self.result_change=result_change;self.on_status=on_status;self.progress=list(progress or [])

    def json(self,value,status=200):return c.WireMessage('application/json',c.json_bytes(value),status)

    def capabilities(self):
        self.events.append('capabilities');return self.json(c.capabilities(f.ENGINE))

    def submit(self,request):
        self.events.append('submit')
        request=c.read_request(request.wire,expected_engine=f.ENGINE);job=request.data['job_id']
        if job in self.jobs:
            old=self.jobs[job]
            if old['identity']!=request.identity:return self.json(c.status_value(request,status='refused',reason_code='renderer_job_conflict'),409)
            if old['released']:return c.WireMessage('application/json',b'{}',410)
            return self.json(old['status'])
        if self.active is not None:return self.json(c.status_value(request,status='refused',reason_code='renderer_busy'),503)
        self.jobs[job]=dict(identity=request.identity,status=c.status_value(request),result=None,released=False)
        self.active=job;self.executions+=1
        return self.json(self.jobs[job]['status'],202)

    def status(self,request):
        self.events.append('status')
        if self.on_status:self.on_status(self)
        job=self.jobs.get(request.data['job_id'])
        if not job:return c.WireMessage('application/json',b'{}',404)
        if job['identity']!=request.identity:return self.json(c.status_value(request,status='refused',reason_code='renderer_job_conflict'),409)
        if job['released']:return c.WireMessage('application/json',b'{}',410)
        n=len(request.data['canonical']['blocks'])
        if self.progress:
            units,blocks=self.progress.pop(0)
            rank=(0 if units==0 else 1 if units==1 else 2 if units<=n+1 else units-n+1) if type(units) is int else -1
            phase=c.PHASES[rank] if 0<=rank<len(c.PHASES) else 'accepted'
            value=c.status_value(request,status='ready' if units==n+7 else 'rendering',reason_code='renderer_ready' if units==n+7 else None,phase=phase,blocks_completed=blocks)
            value['units_completed']=units
        else:value=c.status_value(request,status='ready',reason_code='renderer_ready',phase='pdf_pages_measured',blocks_completed=n)
        value.update(self.status_change);job['status']=value
        return self.json(value)

    def result(self,request):
        self.events.append('result');job=self.jobs.get(request.data['job_id'])
        if not job:return c.WireMessage('application/json',b'{}',404)
        if job['identity']!=request.identity:return self.json(c.status_value(request,status='refused',reason_code='renderer_job_conflict'),409)
        if job['released']:return c.WireMessage('application/json',b'{}',410)
        if job['status']['status']=='rendering':return c.WireMessage('application/json',b'{}',409)
        if job['result'] is None:
            m,d,p=f.result(c,request)
            if job['status']['status']!='ready':
                m.update(status=job['status']['status'],reason_code=job['status']['reason_code'],artifacts={},page_evidence=None,source_evidence=None)
                job['result']=c.encode_multipart([('manifest','application/json',c.json_bytes(m))],limit=c.MAX_RESULT_BYTES)
                return job['result']
            if self.result_change:self.result_change(m)
            job['result']=f.response(c,m,d,p)
        return job['result']

    def cancel_release(self,request,*,cancel=False):
        c.validate_delete(c.read_json(c.delete_message(request,cancel=cancel).body),request=request)
        self.events.append('cancel' if cancel else 'release')
        job=self.jobs.get(request.data['job_id'])
        if not job:return c.WireMessage('application/json',b'{}',404)
        if job['identity']!=request.identity:
            return self.json(c.release_value(request,cancel=cancel)|dict(state='failed',reason_code='renderer_job_conflict',workspace_removed=False),409)
        if job.get('ack') is not None:return job['ack']
        value=c.release_value(request,cancel=cancel);value.update(self.release_change)
        if value['workspace_removed'] is True:
            job['released']=True;job['result']=None;self.active=None
        ack=self.json(value,503 if value['state']=='failed' else 200)
        if job['released']:job['ack']=ack
        return ack

    def restart(self):self.jobs.clear();self.active=None
