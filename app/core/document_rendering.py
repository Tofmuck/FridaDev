"""M8-C request-owned collection, useful progress and separate release.

Client is explicitly injected. No default worker, socket, retry or binary product
executor exists. ConfirmedExecution remains the only application authority.
"""
from dataclasses import dataclass
import time
from . import document_renderer_contract as c

@dataclass(frozen=True,repr=False)
class ReleasedRender:
    result: c.ValidatedResult
    release_bytes: bytes
    @property
    def docx(self):return self.result.docx
    @property
    def pdf(self):return self.result.pdf
    @property
    def manifest(self):return self.result.manifest
    @property
    def release(self):return c.read_json(self.release_bytes)


class RenderingSession:
    def __init__(self,*,client,expected_engine,monotonic=time.monotonic,wait=None):
        self.client=client
        self._engine_bytes=c.json_bytes(c.validate_engine(expected_engine))
        self._clock=monotonic
        self._wait=wait or (lambda:time.sleep(.05))
        self.collected=None
        self._released=None
        self._attempted=None

    @property
    def expected_engine(self):return c.read_json(self._engine_bytes)

    def _call(self,method,*args,**kwargs):
        try:return getattr(self.client,method)(*args,**kwargs)
        except c.RendererError:raise
        except Exception:c.fail()

    def _json(self,response,allowed):
        if type(response) is not c.WireMessage or type(response.http_status) is not int: c.fail()
        if response.http_status in (404,410):c.fail('renderer_job_lost')
        if response.http_status not in allowed or response.content_type!='application/json':c.fail()
        return c.read_json(response.body)

    def collect(self,request,*,check):
        check()
        if type(request) is not c.RenderRequest:c.fail()
        request=c.read_request(request.wire,expected_engine=self.expected_engine)
        if self._attempted is not None:
            if self._attempted!=request.identity:c.fail('renderer_job_conflict')
            if self._released is None:c.fail('renderer_job_lost')
            check();return self._released
        self._attempted=request.identity
        submitted=False
        release_attempted=False
        last=self._clock();units=0;phase_rank=0
        try:
            capabilities=self._call('capabilities');check()
            c.validate_capabilities(self._json(capabilities,{200}),expected_engine=self.expected_engine)
            check();last=self._clock()
            # A response can be lost after acceptance. Identity-bound DELETE is
            # safe; suppress it only for a validated explicit refusal.
            submitted=True
            response=self._call('submit',request)
            status=self._json(response,{200,202,409,422,503})
            c.validate_status(status,request=request)
            check()
            http=response.http_status
            if (http==202 and status.get('status')!='rendering'
                or http==409 and (status.get('status'),status.get('reason_code'))!=('refused','renderer_job_conflict')
                or http==422 and (status.get('status')!='refused' or status.get('reason_code') not in ('renderer_input_invalid','renderer_source_unsupported','renderer_profile_mismatch','renderer_page_limit'))
                or http==503 and (status.get('status'),status.get('reason_code'))!=('refused','renderer_busy')):c.fail()
            submitted=http in (200,202)
            while True:
                if self._clock()-last>=120:c.fail('renderer_inactivity')
                value=c.validate_status(status,request=request)
                current=value['units_completed']
                rank=c.PHASES.index(value['phase'])
                if current<units or rank<phase_rank:c.fail()
                phase_rank=rank
                if current>units:units=current;last=self._clock()
                if value['status']!='rendering':
                    if value['status']!='ready':c.fail(value['reason_code'])
                    break
                check();self._wait();check()
                if self._clock()-last>=120:c.fail('renderer_inactivity')
                status=self._json(self._call('status',request),{200});check()
            check();wire=self._call('result',request);check()
            if self._clock()-last>=120:c.fail('renderer_inactivity')
            if type(wire) is not c.WireMessage or wire.http_status!=200:c.fail('renderer_job_lost' if getattr(wire,'http_status',None) in (404,410) else 'renderer_incomplete')
            # Full immutable bytes/manifests are held locally before worker release.
            self.collected=c.validate_result(wire,request=request,expected_engine=self.expected_engine)
            if self._clock()-last>=120:c.fail('renderer_inactivity')
            check();release_attempted=True
            message=self._call('cancel_release',request,cancel=False);check()
            ack=c.validate_release_message(message,request=request)
            check()
            # Release acknowledges cleanup, not useful rendering progress.
            if self._clock()-last>=120:c.fail('renderer_inactivity')
            self._released=ReleasedRender(self.collected,c.json_bytes(ack))
            return self._released
        except Exception:
            if submitted and not release_attempted:
                # Cleanup has no publication authority. One best effort only;
                # lost worker/cleanup failure never hides the original failure.
                try:c.validate_release_message(self._call('cancel_release',request,cancel=True),request=request,cancel=True)
                except Exception:pass
            raise


def render_confirmed(run,format,session):
    """Inactive binary seam, exercised behind the actual M5 confirmation only."""
    from . import document_workshop_execution_store as store
    store.check(run)
    if type(session) is not RenderingSession:c.fail('renderer_input_invalid')
    try:
        request=c.make_request(job_id=run.token.turn_id,revision_id=run.action['revision_id'],
            canonical=run.revision['canonical'],canonical_sha256=run.revision['canonical_sha256'],
            format=format,engine=session.expected_engine)
        result=session.collect(request,check=lambda:store.check(run))
        store.check(run)
        return result
    except c.RendererError as error:
        # Preserve M5's existing public/storage error vocabulary, no migration.
        raise c.DocumentWorkshopError('document_page_limit' if error.reason_code=='renderer_page_limit' else 'document_render_invalid') from None
