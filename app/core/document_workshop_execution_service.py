"""Closed confirmation HTTP service; M6 composes available execution lazily."""
from . import conversation_turn_claims as claims, document_workshop_actions as actions
from . import document_workshop_execution_store as store
from . import document_workshop_receipts as receipts
from .document_workshop_context_service import _id
from .document_workshop_contract import DocumentWorkshopError
from .workspace_document_paths import validate_document_path

_FIELDS=frozenset(('context_id','conversation_id','workspace_folder_id','revision_id','request_id'))
_PUBLIC=frozenset(('id','context_id','conversation_id','workspace_folder_id','state','phase','received_content_codepoints',
    'reason_code','revision_id','artifact_id','operation','format','relative_path','limitations','created_at','updated_at',
    'turn_id','name','workspace_file_id','confirmation_turn_id','confirmed_at','created_collections_count'))


def project_action(record,*,executor=None):
    if record is None:return None
    result={key:record[key] for key in _PUBLIC if key in record}
    if record.get('state')=='succeeded':
        try:receipt=receipts.for_action(record['id'],storage_root=getattr(executor,'storage_root',None))
        except Exception:receipt=None
        if receipt is None:
            result.update(state='remote_uncertain',reason_code='document_publication_unknown')
        else:
            result['receipt']=receipt
    eligible=record.get('state')=='pending' and record.get('format')=='markdown' and record.get('operation') in ('create','copy')
    collections=[]
    if record.get('relative_path'):
        try:
            path=validate_document_path(record['relative_path'],format=record.get('format'))
            collections=['/'.join(path.segments[:i]) for i in range(2,len(path.segments))]
        except DocumentWorkshopError:eligible=False
    result['collections']=collections
    if executor is not None:
        result['limitations']=[code for code in record.get('limitations',[]) if code!='write_confirmation_unavailable']
    result['capabilities']=dict(confirm=executor is not None and eligible,cancel=record.get('state') in ('preparing','pending','executing'))
    return result


def confirm(action_id,data,*,executor=None):
    if not _id(action_id) or type(data) is not dict or set(data)!=_FIELDS or any(not _id(data[k]) for k in _FIELDS):
        return dict(ok=False,reason_code='document_action_request_invalid'),400
    if executor is None:
        return dict(ok=False,reason_code='document_execution_unavailable'),503
    data={key:_id(value) for key,value in data.items()}
    action_id=_id(action_id)
    try:
        run=store.begin(action_id,data)
        if run is not None:
            outcome=executor.execute(run)
            if outcome is not None and outcome.state=='remote_uncertain':
                return dict(ok=False,reason_code=outcome.reason_code or 'document_publication_unknown'),503
        action=actions.get_action(action_id)
        if not action:return dict(ok=False,reason_code='document_action_missing'),404
        projected=project_action(action,executor=executor)
        payload=dict(ok=projected['state'] in ('succeeded','executing'),action=projected)
        if projected['state'] not in ('succeeded','executing'):
            payload['reason_code']=projected.get('reason_code') or 'document_execution_closed'
        return payload,200 if payload['ok'] else 503 if projected['state'] in ('failed','remote_uncertain') else 409
    except claims.ClaimError as error:
        return dict(ok=False,reason_code=error.reason_code),error.status
    except DocumentWorkshopError as error:
        return dict(ok=False,reason_code=error.reason_code),404 if error.reason_code=='document_action_missing' else 409
    except Exception:
        return dict(ok=False,reason_code='document_action_storage_unavailable'),503
