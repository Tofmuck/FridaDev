"""Stable-file SQL publication. No network, trigger bypass or compensation."""
import hashlib
from uuid import uuid4
from . import document_workshop_execution_store as store, workspace_files_store
from .document_workshop_contract import DocumentWorkshopError
from .workspace_nextcloud_etag import validated_strong_etag


def publish(run,*,result,content,scope_key,storage_root,repair_token=None):
    version=run.action['target_version'];resource=result.resource
    digest=hashlib.sha256(content).hexdigest()
    if (result.state!='known_success' or resource is None or resource.is_collection
            or resource.relative_path!=run.target.relative_path or resource.file_id!=version['remote_file_id']
            or scope_key!=version['scope_key'] or resource.byte_size!=len(content)
            or not validated_strong_etag(result.creation_etag) or resource.etag!=result.creation_etag
            or digest!=run.revision['markdown_sha256']):
        raise DocumentWorkshopError('document_remote_changed')
    storage_key=str(uuid4())+'/'+str(uuid4())
    prepared=workspace_files_store.workspace_file_path(storage_root,storage_key)
    commit_started=False
    try:
        workspace_files_store.write_file_bytes(storage_root,storage_key,content)
        with store._db_conn() as conn:
            if repair_token:
                from .document_workshop_update_reconciliation import guard
                row=guard(conn,run,repair_token)
            else:row=store._guard(conn,run)
            file_id=version['workspace_file_id']
            conn.execute("INSERT INTO document_revision_renders(revision_id,format,serializer_version,content_sha256,byte_size,storage_key) VALUES(%s::uuid,'markdown','frida_markdown_v1',%s,%s,%s)",
                (row['revision_id'],digest,len(content),storage_key))
            conn.execute('''INSERT INTO document_receipts(id,action_id,confirmation_turn_id,request_turn_id,conversation_id,
                workspace_folder_id,artifact_id,revision_id,workspace_file_id,operation,format,relative_path,creation_author,
                revision_author,canonical_sha256,content_sha256,nextcloud_scope_key,nextcloud_file_id,nextcloud_etag,confirmed_at)
                VALUES(%s::uuid,%s::uuid,%s::uuid,%s::uuid,%s::uuid,%s::uuid,%s::uuid,%s::uuid,%s::uuid,'update','markdown',%s,%s,
                'frida',%s,%s,%s,%s,%s,%s)''',
                (str(uuid4()),row['id'],row['confirmation_turn_id'],row['id'],row['conversation_id'],row['workspace_folder_id'],
                row['artifact_id'],row['revision_id'],file_id,version['relative_path'],version['creation_author'],
                run.revision['canonical_sha256'],digest,scope_key,resource.file_id,resource.etag,row['confirmed_at']))
            conn.execute('UPDATE document_artifacts SET current_revision_id=%s::uuid WHERE id=%s::uuid',(row['revision_id'],row['artifact_id']))
            # Close our authority before the real file/link triggers invalidate
            # every stale target/source context, including this historical one.
            token=repair_token or run.token
            conn.execute("UPDATE conversation_turn_claims SET state='succeeded',outcome='succeeded',finished_at=clock_timestamp() WHERE turn_id=%s::uuid",(token.turn_id,))
            if repair_token:
                from dataclasses import replace
                store._append(conn,replace(run,token=repair_token),'metadata_published',state='known_success',etag=resource.etag)
            conn.execute("UPDATE document_actions SET state='succeeded',phase='complete',reason_code=NULL,workspace_file_id=%s::uuid,created_collections_count=0,updated_at=clock_timestamp() WHERE id=%s::uuid",(file_id,row['id']))
            conn.execute('''UPDATE workspace_files SET storage_key=%s,byte_size=%s,sha256=%s,sha256_12=%s,
                text_chars=%s,text_sha256_12=%s,updated_at=clock_timestamp() WHERE id=%s::uuid''',
                (storage_key,len(content),digest,digest[:12],len(content.decode('utf-8')),digest[:12],file_id))
            conn.execute('''UPDATE workspace_file_nextcloud_links SET nextcloud_etag=%s,observed_sha256=%s,
                observed_at=clock_timestamp(),last_sync_at=clock_timestamp(),last_sync_operation='observe',
                last_sync_reason_code='folder_document_list_ok',updated_at=clock_timestamp() WHERE workspace_file_id=%s::uuid''',
                (resource.etag,digest,file_id))
            commit_started=True
    except Exception:
        if not commit_started:store.discard(prepared)
        raise store.PublicationFailure(ambiguous=commit_started,prepared=prepared) from None
