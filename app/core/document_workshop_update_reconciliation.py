"""One targeted metadata repair under a new M3 owner; never a DAV mutation.

Only acknowledged success persisted in the existing journal can authorize
repair. Matching bytes after a lost DAV reply cannot establish authorship.
"""
from dataclasses import replace
import hashlib
from types import SimpleNamespace
from uuid import uuid4
from . import document_workshop_execution_store as store, conversation_turn_claims as claims
from . import document_workshop_update_target as target
from .document_workshop_contract import DocumentWorkshopError


def guard(conn,run,token):
    claims.check_in_transaction(conn,token,conversation_id=token.conversation_id)
    row=store.actions._read(conn,run.action['id'])
    folder=store._resources(conn,row)
    store._versions(conn,row)
    row=store.actions._read(conn,run.action['id'],lock=True)
    if (row['state']!='remote_uncertain' or row['operation']!='update'
            or store._json(folder)!=run._folder or store._json(store._revision(conn,row))!=run._revision
            or str(row['confirmation_turn_id'])!=run.action['confirmation_turn_id']
            or str(row['revision_id'])!=run.action['revision_id']
            or store._json(row['target_version'])!=store._json(run.action['target_version'])
            or token.turn_id==str(row['confirmation_turn_id'])):
        raise DocumentWorkshopError('document_publication_unknown')
    original=claims._read(conn,str(row['confirmation_turn_id']))
    if not original or original['state']=='active':raise DocumentWorkshopError('document_publication_unknown')
    return row


def reconcile(action_id,executor):
    if not executor.supports_update:return
    token=None
    try:
        with store._db_conn() as conn:
            row=store.actions._read(conn,action_id)
            if not row or row['state']!='remote_uncertain' or row['operation']!='update':return
            original=claims._read(conn,str(row['confirmation_turn_id']))
            if not original or original['state']=='active':return
            # A GET is a bounded repair attempt, never a recurrent job. Failed
            # or expired repair stays unknown and requires intervention.
            if conn.execute("SELECT 1 FROM document_execution_journal WHERE action_id=%s::uuid AND event='metadata_reconciliation'",(action_id,)).fetchone():return
            from psycopg.rows import dict_row
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT * FROM document_execution_journal WHERE action_id=%s::uuid AND event='remote_outcome'",(action_id,));outcomes=cur.fetchall()
                cur.execute("SELECT * FROM document_execution_journal WHERE action_id=%s::uuid AND event='put_intent'",(action_id,));puts=cur.fetchall()
            if len(outcomes)!=1 or len(puts)!=1:return
            outcome=outcomes[0]
            if (outcome['state']!='known_success' or outcome['http_status'] not in (200,204)
                    or not store.validated_strong_etag(outcome['etag'])
                    or str(outcome['confirmation_turn_id'])!=str(row['confirmation_turn_id'])
                    or str(outcome['owner_id'])!=str(original['owner_id']) or outcome['generation']!=original['generation']):return
            revision=store._revision(conn,row)
            if outcome['content_sha256']!=revision['markdown_sha256'] or outcome['canonical_sha256']!=revision['canonical_sha256']:return
            for put in puts:
                if (str(put['confirmation_turn_id'])!=str(row['confirmation_turn_id']) or str(put['owner_id'])!=str(original['owner_id'])
                        or put['generation']!=original['generation'] or put['path_sha256']!=hashlib.sha256(row['relative_path'].encode()).hexdigest()):return
            folder=store._resources(conn,row)
            old_token=claims.TurnClaim(str(original['turn_id']),str(original['conversation_id']),str(original['owner_id']),original['generation'],str(original['context_id']))
            run=store.ConfirmedExecution(old_token,store._json(row),store._json(revision),store._json(folder))
        version=run.action['target_version']
        admission=claims.acquire(conversation_id=run.token.conversation_id,turn_id=str(uuid4()),
            request_fingerprint=hashlib.sha256(('metadata:'+action_id).encode()).hexdigest(),kind='confirmation',
            context_id=run.token.context_id,expected_etag=version['etag'])
        token=admission.token
        with store._db_conn() as conn:
            guard(conn,run,token)
            if conn.execute("SELECT 1 FROM document_execution_journal WHERE action_id=%s::uuid AND event='metadata_reconciliation'",(action_id,)).fetchone():return
            store._append(conn,replace(run,token=token),'metadata_reconciliation',state='remote_uncertain',etag=outcome['etag'])
        reader=executor.client._reader
        folder_name=run.folder['nextcloud_target_name']
        if reader.scope_key(folder_name)!=version['scope_key']:return
        resource=reader.stat_resource(folder_name,version['relative_path'],expected_etag=outcome['etag'])
        if resource.file_id!=version['remote_file_id']:return
        content=reader.read_file(folder_name,resource)
        if hashlib.sha256(content).hexdigest()!=run.revision['markdown_sha256']:return
        expected=executor._render(run)
        if content!=expected:return
        result=SimpleNamespace(state='known_success',resource=resource,creation_etag=resource.etag)
        from .document_workshop_update_publication import publish
        try:
            publish(run,result=result,content=content,scope_key=version['scope_key'],storage_root=executor.storage_root,repair_token=token)
        except store.PublicationFailure:
            # Fresh GET proof can establish an already committed repair. No
            # old token, retry publication, delete or remote write is attempted.
            store.verify_committed_action(action_id,storage_root=executor.storage_root)
    except Exception:
        return
    finally:
        if token is not None:
            try:claims.finish(token,'interrupted')
            except Exception:pass
