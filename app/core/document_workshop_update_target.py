"""M7 explicit target proof, separate from read sources and the current DOM."""
from psycopg.rows import dict_row
from .document_workshop_contract import DocumentWorkshopError
from .workspace_document_adoption_store import remote_identity
from .workspace_nextcloud_etag import validated_strong_etag


def available(conn):
    columns=conn.execute("""SELECT column_name FROM information_schema.columns
        WHERE table_schema=current_schema() AND table_name='document_actions'""").fetchall()
    trigger=conn.execute("""SELECT 1 FROM pg_trigger WHERE tgrelid='document_actions'::regclass
        AND tgname='document_update_target_immutable' AND tgenabled IN ('O','A')""").fetchone()
    constraints=conn.execute("""SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE convalidated AND
        conrelid IN ('document_actions'::regclass,'document_receipts'::regclass,'document_execution_journal'::regclass)
        AND conname=ANY(%s)""",(['document_update_target_shape','document_actions_operation_check',
            'document_actions_state_check','document_receipts_operation_check','document_receipts_creation_author_check',
            'document_execution_journal_event_check'],)).fetchall()
    index=conn.execute("SELECT 1 FROM pg_index WHERE indexrelid=to_regclass('document_artifacts_file_identity') AND indisvalid AND indisunique").fetchone()
    identity=conn.execute("SELECT strpos(pg_get_functiondef('document_action_identity_immutable()'::regprocedure),'metadata_published')>0").fetchone()
    # M5 uses several of the same constraint names. Their effective definitions
    # must also contain the M7 values; names alone admit a partial restoration.
    required={
        'document_update_target_shape':('target_version IS NOT NULL','?&',"'base_revision_id'","'mime_type'"),
        'document_actions_operation_check':("'update'",),
        'document_actions_state_check':("'conflict'",),
        'document_receipts_operation_check':("'update'",),
        'document_receipts_creation_author_check':("'update'","'external'"),
        'document_execution_journal_event_check':("'metadata_reconciliation'","'metadata_published'"),
    }
    effective=dict(constraints)
    return (('target_version',) in columns and bool(trigger) and len(constraints)==6 and bool(index)
        and bool(identity and identity[0]) and all(all(value in effective.get(name,'') for value in values)
            for name,values in required.items()))


def snapshot(conn, context, source):
    if not available(conn):raise DocumentWorkshopError('document_update_unavailable')
    file_id=str(context['target_file_id']) if context['target_file_id'] else None
    if (source is None or source.workspace_file_id!=file_id
            or source.workspace_folder_id!=str(context['workspace_folder_id'])
            or source.relative_path!=context['target_relative_path']
            or source.remote_identity!=context['target_remote_identity'] or source.source_extension!='.md'
            or not validated_strong_etag(source.etag)):
        raise DocumentWorkshopError('document_update_target_invalid')
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute('SELECT * FROM workspace_files WHERE id=%s::uuid FOR SHARE NOWAIT',(file_id,));file=cur.fetchone()
        cur.execute('SELECT * FROM workspace_file_nextcloud_links WHERE workspace_file_id=%s::uuid FOR SHARE NOWAIT',(file_id,));link=cur.fetchone()
    if (not file or not link or file['deleted_at'] or file['status']!='active'
            or str(file['workspace_folder_id'])!=str(context['workspace_folder_id'])
            or file['content_kind']!='document' or file['media_kind']!='text' or file['source_extension']!='.md'
            or link['nextcloud_sync_state']!='linked' or link['nextcloud_document_ref']!=context['target_document_ref']
            or str(link['workspace_folder_id'])!=str(context['workspace_folder_id'])
            or remote_identity(link['nextcloud_scope_key'],link['nextcloud_file_id'])!=source.remote_identity
            or link['nextcloud_etag']!=source.etag or link['observed_sha256']!=source.sha256
            or file['sha256']!=source.sha256 or file['byte_size']!=source.byte_size
            or link['nextcloud_relative_path']!=source.relative_path
            or file['original_filename']!=source.relative_path.split('/')[-1]
            or file['display_name']!=file['original_filename'] or link['document_origin'] not in ('frida','external')):
        raise DocumentWorkshopError('document_remote_changed')
    return dict(workspace_file_id=file_id,workspace_folder_id=str(context['workspace_folder_id']),
        relative_path=source.relative_path,remote_identity=source.remote_identity,etag=source.etag,
        sha256=source.sha256,byte_size=source.byte_size,observed_at=source.observed_at,
        scope_key=link['nextcloud_scope_key'],remote_file_id=link['nextcloud_file_id'],
        document_ref=link['nextcloud_document_ref'],document_origin=link['document_origin'],
        creation_author=link['document_origin'],source_kind=file['source_kind'],
        name=file['original_filename'],created_at=file['created_at'].isoformat(),mime_type=file['mime_type'],
        nextcloud_target_name=link['nextcloud_target_name'],nextcloud_name_hash=link['nextcloud_name_hash'])


def verify_local(conn, action):
    version=action.get('target_version')
    if (action['operation']!='update' or not version or not available(conn)
            or version['workspace_folder_id']!=str(action['workspace_folder_id'])
            or version['relative_path']!=action['relative_path'] or not validated_strong_etag(version['etag'])):
        raise DocumentWorkshopError('document_update_target_invalid')
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute('SELECT * FROM document_workshop_contexts WHERE id=%s::uuid',(action['context_id'],));context=cur.fetchone()
    from types import SimpleNamespace
    observed=SimpleNamespace(**{k:version[k] for k in ('workspace_file_id','workspace_folder_id','relative_path','remote_identity','etag','sha256','byte_size','observed_at')},source_extension='.md')
    current=snapshot(conn,context,observed)
    if any(current[k]!=version[k] for k in current):raise DocumentWorkshopError('document_remote_changed')
    artifact=conn.execute('SELECT workspace_file_id::text,current_revision_id::text FROM document_artifacts WHERE id=%s::uuid FOR UPDATE NOWAIT',(action['artifact_id'],)).fetchone()
    if not artifact or artifact!=(version['workspace_file_id'],version['base_revision_id']):
        raise DocumentWorkshopError('document_remote_changed')


def verify_fresh(action, source):
    version=action['target_version']
    if source is None or any(getattr(source,k)!=version[k] for k in
            ('workspace_file_id','workspace_folder_id','relative_path','remote_identity','etag','sha256','byte_size')):
        raise DocumentWorkshopError('document_remote_changed')
