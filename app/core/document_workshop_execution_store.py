"""M5 SQL authority. No network, runtime bootstrap or automatic replay."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from psycopg.rows import dict_row
from . import conversation_turn_claims as claims, document_workshop_actions as actions
from . import workspace_files_store, workspace_folders_store
from .document_canonical import validate_canonical
from .document_markdown import serialize_markdown
from .document_workshop_contract import DocumentWorkshopError
from .workspace_document_paths import validate_document_path, validate_document_source_path
from .workspace_document_adoption_store import remote_identity
from .workspace_nextcloud_etag import validated_strong_etag

_SCHEMA = Path(__file__).with_name('sql') / 'document_workshop_execution_m5.sql'
_OUTCOME_REASONS=frozenset(('document_remote_created','document_remote_updated','document_remote_mutation_uncertain','document_remote_changed',
    'document_remote_unavailable','document_remote_incompatible','document_remote_missing','document_target_collision',
    'document_collection_conflict','document_mutation_not_authorized','document_path_invalid','document_output_invalid',
    'document_compensation_absent','document_compensation_missing','document_compensation_ownership_unverified',
    'document_compensation_uncertain'))
_EXECUTION_REASONS=_OUTCOME_REASONS|frozenset(('document_publication_failed_compensated','document_publication_unknown',
    'document_confirmation_lost','document_revision_invalid','document_source_unavailable','document_execution_unavailable',
    'document_execution_closed','document_render_invalid','document_page_limit','document_page_evidence_invalid',
    'document_context_scope_changed','document_local_collision','document_format_unavailable'))


def _db_conn():
    return actions._db_conn()


def init_db():
    with _db_conn() as conn:
        conn.execute(_SCHEMA.read_text(encoding='utf-8'))
    return True


def _json(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=str)


@dataclass(frozen=True,repr=False)
class ConfirmedExecution:
    token: claims.TurnClaim
    _action: str
    _revision: str
    _folder: str

    @property
    def action(self):return json.loads(self._action)
    @property
    def revision(self):return json.loads(self._revision)
    @property
    def folder(self):return json.loads(self._folder)
    @property
    def target(self):return validate_document_path(self.action['relative_path'],format=self.action['format'])
    @property
    def collections(self):
        return tuple('/'.join(self.target.segments[:i]) for i in range(2,len(self.target.segments)))


class PublicationFailure(DocumentWorkshopError):
    def __init__(self, *, ambiguous, prepared=None):
        super().__init__('document_publication_unknown' if ambiguous else 'document_publication_failed')
        self.ambiguous,self.prepared=ambiguous,prepared


def _resources(conn,row):
    """Lock resources before context/claim/action, with downstream NOWAIT."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute('SELECT * FROM workspace_folders WHERE id=%s::uuid FOR UPDATE NOWAIT',(row['workspace_folder_id'],))
        folder=cur.fetchone()
        cur.execute('SELECT * FROM workspace_folder_nextcloud_links WHERE workspace_folder_id=%s::uuid FOR SHARE NOWAIT',
            (row['workspace_folder_id'],))
        link=cur.fetchone()
        if not folder or folder['deleted_at'] or not link or link['nextcloud_sync_state']!='linked' or not link['nextcloud_folder_ref']:
            raise DocumentWorkshopError('document_context_scope_changed')
        projection=workspace_folders_store.build_nextcloud_folder_projection(folder_id=str(folder['id']),
            display_name=folder.get('display_name'),deleted_at=folder['deleted_at'])
        if not projection.get('nextcloud_target_name'):
            raise DocumentWorkshopError('document_context_scope_changed')
        result=dict(nextcloud_target_name=projection['nextcloud_target_name'],nextcloud_folder_ref=link['nextcloud_folder_ref'],
            nextcloud_name_hash=link.get('nextcloud_name_hash'))
        cur.execute('SELECT id FROM workspace_files WHERE workspace_folder_id=%s::uuid FOR SHARE NOWAIT',(row['workspace_folder_id'],))
        cur.fetchall()
        cur.execute('SELECT workspace_file_id FROM workspace_file_nextcloud_links WHERE workspace_folder_id=%s::uuid FOR SHARE NOWAIT',
            (row['workspace_folder_id'],));cur.fetchall()
    return result


def _collision(conn,row):
    if row['operation']=='update':
        from .document_workshop_update_target import verify_local
        verify_local(conn,row)
        return
    target=validate_document_path(row['relative_path'],format=row['format'])
    inventory=conn.execute('''SELECT COALESCE(l.nextcloud_relative_path,'Documents/'||
        COALESCE(l.nextcloud_target_name,to_jsonb(f)->>'original_filename')) FROM workspace_files f
        LEFT JOIN workspace_file_nextcloud_links l ON l.workspace_file_id=f.id
        WHERE f.workspace_folder_id=%s::uuid AND f.deleted_at IS NULL AND f.status<>'deleted' ''',
        (row['workspace_folder_id'],)).fetchall()
    for item in inventory:
        try:collision=validate_document_source_path(item[0]).collision_key==target.collision_key
        except DocumentWorkshopError:collision=False
        if collision:raise DocumentWorkshopError('document_local_collision')


def _revision(conn,row):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute('SELECT * FROM document_revisions WHERE id=%s::uuid',(row['revision_id'],));revision=cur.fetchone()
    if not revision or revision['artifact_id']!=row['artifact_id']:
        raise DocumentWorkshopError('document_revision_invalid')
    canonical=validate_canonical(revision['canonical'])
    digest=hashlib.sha256(_json(canonical.as_dict()).encode()).hexdigest()
    markdown=serialize_markdown(canonical).encode('utf-8')
    if (revision['canonical_sha256']!=digest or revision['markdown_sha256']!=hashlib.sha256(markdown).hexdigest()
        or revision['serializer_version']!='frida_markdown_v1'
        or canonical.word_count!=revision['word_count'] or canonical.codepoint_count!=revision['codepoint_count']):
        raise DocumentWorkshopError('document_revision_invalid')
    return revision


def _versions(conn,row):
    actions._verify_versions(conn,dict(workspace_folder_id=row['workspace_folder_id']),
        row['source_file_ids'],row['source_versions'])
    if row['operation']=='update':
        from .document_workshop_update_target import verify_local
        verify_local(conn,row)


def _fingerprint(action_id,data):
    return hashlib.sha256(_json(dict(action_id=action_id,**{k:v for k,v in data.items() if k!='request_id'})).encode()).hexdigest()


def begin(action_id,data):
    """One transaction consumes the action and creates its distinct M3 claim."""
    with _db_conn() as conn:
        row=actions._read(conn,action_id)
        if not row:raise DocumentWorkshopError('document_action_missing')
        if any(str(row[k])!=data[k] for k in ('context_id','conversation_id','workspace_folder_id','revision_id')):
            raise DocumentWorkshopError('document_confirmation_scope_invalid')
        conversation=claims._conversation(conn,str(row['conversation_id']))
        claims._expire(conn,str(row['conversation_id']))
        existing=claims._read(conn,data['request_id'])
        fingerprint=_fingerprint(action_id,data)
        if existing and (existing['kind']!='confirmation' or existing['request_fingerprint']!=fingerprint
                or str(existing['conversation_id'])!=data['conversation_id'] or str(existing['context_id'])!=data['context_id']):
            raise claims.ClaimError('conversation_turn_id_incompatible')
        # A consumed action never creates another claim, including a fresh ID.
        row=actions._read(conn,action_id)
        if row['state']!='pending':return None
        if existing:raise claims.ClaimError('conversation_turn_id_incompatible')
        folder=_resources(conn,row)
        _versions(conn,row)
        claims._scope(conn,conversation,data['context_id'])
        if conn.execute("SELECT 1 FROM conversation_turn_claims WHERE conversation_id=%s::uuid AND state='active'",
            (data['conversation_id'],)).fetchone():raise claims.ClaimError('conversation_turn_conflict')
        row=actions._read(conn,action_id,lock=True)
        if row['state']!='pending':return None
        if row['format']!='markdown' or row['operation'] not in ('create','copy','update'):
            raise DocumentWorkshopError('document_operation_unavailable')
        _collision(conn,row);revision=_revision(conn,row)
        generation=conn.execute('UPDATE conversations SET turn_generation=turn_generation+1 WHERE id=%s::uuid RETURNING turn_generation',
            (data['conversation_id'],)).fetchone()[0]
        owner=str(uuid4())
        conn.execute('''INSERT INTO conversation_turn_claims(turn_id,conversation_id,owner_id,generation,kind,
            request_fingerprint,context_id,expected_etag,lease_until) VALUES(%s::uuid,%s::uuid,%s::uuid,%s,'confirmation',%s,%s::uuid,%s,
            clock_timestamp()+%s*interval '1 second')''',
            (data['request_id'],data['conversation_id'],owner,generation,fingerprint,data['context_id'],
             row['target_version']['etag'] if row['operation']=='update' else None,claims.LEASE_SECONDS))
        conn.execute("UPDATE document_actions SET state='executing',phase='confirmed',confirmation_turn_id=%s::uuid,confirmed_at=clock_timestamp(),updated_at=clock_timestamp() WHERE id=%s::uuid",
            (data['request_id'],action_id))
        row=actions._read(conn,action_id)
        token=claims.TurnClaim(data['request_id'],data['conversation_id'],owner,generation,data['context_id'])
        run=ConfirmedExecution(token,_json(row),_json(revision),_json(folder))
    return run


def _guard(conn,run):
    row=actions._read(conn,run.action['id'])
    if not row:raise DocumentWorkshopError('document_action_missing')
    claims._conversation(conn,run.token.conversation_id)
    folder=_resources(conn,row)
    _versions(conn,row)
    claims.check_in_transaction(conn,run.token,conversation_id=run.token.conversation_id)
    row=actions._read(conn,run.action['id'],lock=True)
    if row['state']!='executing' or str(row['confirmation_turn_id'])!=run.token.turn_id:
        raise DocumentWorkshopError('document_execution_closed')
    if _json(folder)!=run._folder or any(str(row[k])!=str(run.action[k]) for k in
        ('id','context_id','conversation_id','workspace_folder_id','revision_id','artifact_id','relative_path','operation','format')):
        raise DocumentWorkshopError('document_context_scope_changed')
    if _json(_revision(conn,row))!=run._revision:
        raise DocumentWorkshopError('document_revision_invalid')
    return row


def check(run):
    if not isinstance(run,ConfirmedExecution):raise DocumentWorkshopError('document_confirmation_required')
    with _db_conn() as conn:_guard(conn,run)


def verify_fresh_sources(run,sources):
    versions=run.action['source_versions']
    if len(sources)!=len(versions):raise DocumentWorkshopError('document_remote_changed')
    observed={s.workspace_file_id:s for s in sources}
    for version in versions:
        source=observed.get(version['workspace_file_id'])
        if not source or source.workspace_folder_id!=run.action['workspace_folder_id'] or any(
            getattr(source,key)!=version[key] for key in ('relative_path','remote_identity','etag','sha256')):
            raise DocumentWorkshopError('document_remote_changed')
    check(run)


def _append(conn,run,event,*,path=None,state=None,reason=None,http_status=None,etag=None,count=None):
    conn.execute('''INSERT INTO document_execution_journal(id,action_id,confirmation_turn_id,owner_id,generation,event,
        path_sha256,canonical_sha256,content_sha256,serializer_version,state,reason_code,http_status,etag,created_collections_count)
        VALUES(%s::uuid,%s::uuid,%s::uuid,%s::uuid,%s,%s,%s,%s,%s,'frida_markdown_v1',%s,%s,%s,%s,%s)''',
        (str(uuid4()),run.action['id'],run.token.turn_id,run.token.owner_id,run.token.generation,event,
        hashlib.sha256(path.encode()).hexdigest() if path else None,run.revision['canonical_sha256'],run.revision['markdown_sha256'],
        state,reason,http_status,etag,count))


def intent(run):
    with _db_conn() as conn:
        _guard(conn,run);_collision(conn,run.action)
        _append(conn,run,'intent',path=run.target.relative_path)


def before_mutation(run,method,path,*,compensation=False):
    allowed=(method=='MKCOL' and path in run.collections) or (method=='PUT' and path==run.target.relative_path)
    if compensation:allowed=method=='DELETE' and path==run.target.relative_path
    if run.action['operation']=='update':
        allowed=not compensation and method=='PUT' and path==run.target.relative_path
    if not allowed:raise DocumentWorkshopError('document_mutation_not_authorized')
    with _db_conn() as conn:
        _guard(conn,run)
        if not conn.execute("SELECT 1 FROM document_execution_journal WHERE action_id=%s::uuid AND event='intent'",(run.action['id'],)).fetchone():
            raise DocumentWorkshopError('document_mutation_not_authorized')
        if compensation:
            if not conn.execute("SELECT 1 FROM document_execution_journal WHERE action_id=%s::uuid AND event='remote_outcome' AND state='known_success' AND etag IS NOT NULL",(run.action['id'],)).fetchone():
                raise DocumentWorkshopError('document_mutation_not_authorized')
        else:_collision(conn,run.action)
        if method=='PUT' and conn.execute("SELECT 1 FROM document_execution_journal WHERE action_id=%s::uuid AND event='put_intent'",(run.action['id'],)).fetchone():
            raise DocumentWorkshopError('document_mutation_not_authorized')
        _append(conn,run,method.lower()+'_intent',path=path)
    return True


def observe(run,event,result):
    """The same live confirmed owner fences every observation write."""
    if event not in ('remote_outcome','compensation_outcome'):raise DocumentWorkshopError('document_journal_invalid')
    states=('known_success','known_failure','remote_uncertain') if event=='remote_outcome' else ('absence_certain','preserved','remote_uncertain')
    if result.state not in states:raise DocumentWorkshopError('document_journal_invalid')
    with _db_conn() as conn:
        _guard(conn,run)
        count=len(result.created_collections) if hasattr(result,'created_collections') else None
        reason=result.reason_code if result.reason_code in _OUTCOME_REASONS else 'document_remote_incompatible'
        status=result.http_status if type(result.http_status) is int and 0<=result.http_status<=599 else 0
        _append(conn,run,event,state=result.state,reason=reason,http_status=status,
            etag=validated_strong_etag(getattr(result,'creation_etag',None)) or None,count=count)


def finish(run,state,reason,*,created_collections_count=None):
    if state not in ('failed','invalidated','remote_uncertain','conflict'):raise DocumentWorkshopError('document_execution_state_invalid')
    with _db_conn() as conn:
        _guard(conn,run)
        reason=reason if reason in _EXECUTION_REASONS else 'document_execution_unavailable'
        conn.execute('UPDATE document_actions SET state=%s,phase=%s,reason_code=%s,created_collections_count=%s,updated_at=clock_timestamp() WHERE id=%s::uuid',
            (state,state,reason,created_collections_count,run.action['id']))
        conn.execute('UPDATE conversation_turn_claims SET state=%s,outcome=%s,finished_at=clock_timestamp() WHERE turn_id=%s::uuid',
            ('failed' if state in ('failed','invalidated','conflict') else 'interrupted','interrupted',run.token.turn_id))


def publication_unknown(run):
    """Close only the original still live owner, in one short SQL transaction."""
    with _db_conn() as conn:
        _guard(conn,run)
        _append(conn,run,'publication_unknown',state='remote_uncertain',reason='document_publication_unknown')
        conn.execute("UPDATE document_actions SET state='remote_uncertain',phase='publication_unknown',reason_code='document_publication_unknown',updated_at=clock_timestamp() WHERE id=%s::uuid",(run.action['id'],))
        conn.execute("UPDATE conversation_turn_claims SET state='interrupted',outcome='interrupted',finished_at=clock_timestamp() WHERE turn_id=%s::uuid",(run.token.turn_id,))


def reconcile(action_id):
    """Observe a dead confirmation once; no replay, rearm or new generation."""
    with _db_conn() as conn:row=actions._read(conn,action_id)
    if not row or row['state']!='executing':return
    claim=claims.read(str(row['confirmation_turn_id']))
    if claim and claim['state']=='active':return
    with _db_conn() as conn:
        claims._conversation(conn,str(row['conversation_id']),active=False)
        row=actions._read(conn,action_id,lock=True)
        if not row or row['state']!='executing':return
        claim=claims._read(conn,str(row['confirmation_turn_id']))
        if claim and claim['state']=='active':return
        has_intent=conn.execute('SELECT 1 FROM document_execution_journal WHERE action_id=%s::uuid LIMIT 1',(action_id,)).fetchone()
        conn.execute('UPDATE document_actions SET state=%s,phase=%s,reason_code=%s,updated_at=clock_timestamp() WHERE id=%s::uuid',
            ('remote_uncertain' if has_intent else 'failed','interrupted','document_confirmation_lost',action_id))


def discard(prepared):
    if prepared:
        try:Path(prepared).unlink(missing_ok=True)
        except OSError:pass


def publish(run,*,result,content,scope_key,storage_root):
    if run.action['operation']=='update':
        from .document_workshop_update_publication import publish
        return publish(run,result=result,content=content,scope_key=scope_key,storage_root=storage_root)
    target=run.target;resource=result.resource
    etag=validated_strong_etag(result.creation_etag)
    digest=hashlib.sha256(content).hexdigest()
    remote_identity(scope_key,resource.file_id)
    if (result.state!='known_success' or not etag or resource.is_collection or resource.relative_path!=target.relative_path
        or resource.etag!=etag or resource.byte_size!=len(content) or digest!=run.revision['markdown_sha256']):
        raise DocumentWorkshopError('document_remote_changed')
    file_id,receipt_id=str(uuid4()),str(uuid4())
    storage_key=str(uuid4())+'/'+str(uuid4())
    prepared=workspace_files_store.workspace_file_path(storage_root,storage_key)
    commit_started=False
    try:
        workspace_files_store.write_file_bytes(storage_root,storage_key,content)
        with _db_conn() as conn:
            row=_guard(conn,run);_collision(conn,row)
            name=target.segments[-1]
            conn.execute('''INSERT INTO workspace_files(id,workspace_folder_id,display_name,original_filename,storage_key,
                content_kind,media_kind,mime_type,source_extension,byte_size,sha256,sha256_12,text_chars,text_sha256_12,status,source_kind)
                VALUES(%s::uuid,%s::uuid,%s,%s,%s,'document','text','text/markdown','.md',%s,%s,%s,%s,%s,'active','document_workshop')''',
                (file_id,row['workspace_folder_id'],name,name,storage_key,len(content),digest,digest[:12],len(content.decode('utf-8')),digest[:12]))
            conn.execute('''INSERT INTO workspace_file_nextcloud_links(workspace_file_id,workspace_folder_id,nextcloud_sync_state,
                nextcloud_document_ref,nextcloud_name_hash,nextcloud_target_name,nextcloud_relative_path,nextcloud_collision_key,
                nextcloud_file_id,nextcloud_scope_key,nextcloud_etag,observed_at,observed_sha256,document_origin,
                last_sync_at,last_sync_operation,last_sync_reason_code)
                VALUES(%s::uuid,%s::uuid,'linked',%s,%s,%s,%s,%s,%s,%s,%s,clock_timestamp(),%s,'frida',clock_timestamp(),'upload','folder_document_upload_ok')''',
                (file_id,row['workspace_folder_id'],'workspace-file:'+file_id,hashlib.sha256(name.encode()).hexdigest()[:12],
                name,target.relative_path,target.collision_key,resource.file_id,scope_key,etag,digest))
            conn.execute("INSERT INTO document_revision_renders(revision_id,format,serializer_version,content_sha256,byte_size,storage_key) VALUES(%s::uuid,'markdown','frida_markdown_v1',%s,%s,%s)",
                (row['revision_id'],digest,len(content),storage_key))
            conn.execute('UPDATE document_artifacts SET workspace_file_id=%s::uuid,current_revision_id=%s::uuid WHERE id=%s::uuid',
                (file_id,row['revision_id'],row['artifact_id']))
            conn.execute('''INSERT INTO document_receipts(id,action_id,confirmation_turn_id,request_turn_id,conversation_id,
                workspace_folder_id,artifact_id,revision_id,workspace_file_id,operation,format,relative_path,creation_author,
                revision_author,canonical_sha256,content_sha256,nextcloud_scope_key,nextcloud_file_id,nextcloud_etag,confirmed_at)
                VALUES(%s::uuid,%s::uuid,%s::uuid,%s::uuid,%s::uuid,%s::uuid,%s::uuid,%s::uuid,%s::uuid,%s,'markdown',%s,'frida','frida',%s,%s,%s,%s,%s,%s)''',
                (receipt_id,row['id'],run.token.turn_id,row['id'],row['conversation_id'],row['workspace_folder_id'],row['artifact_id'],
                row['revision_id'],file_id,row['operation'],target.relative_path,run.revision['canonical_sha256'],digest,scope_key,resource.file_id,etag,row['confirmed_at']))
            conn.execute("UPDATE document_actions SET state='succeeded',phase='complete',workspace_file_id=%s::uuid,created_collections_count=%s,updated_at=clock_timestamp() WHERE id=%s::uuid",
                (file_id,len(result.created_collections),row['id']))
            conn.execute("UPDATE conversation_turn_claims SET state='succeeded',outcome='succeeded',finished_at=clock_timestamp() WHERE turn_id=%s::uuid",(run.token.turn_id,))
            commit_started=True
    except Exception:
        if not commit_started:discard(prepared)
        raise PublicationFailure(ambiguous=commit_started,prepared=prepared) from None


def publication_proof(run,*,result,content,scope_key,storage_root):
    """A commit reply may be lost. A fresh connection verifies the whole bundle."""
    if (type(content) is not bytes or result.state!='known_success' or result.resource is None
        or result.resource.relative_path!=run.target.relative_path or result.resource.is_collection
        or result.resource.byte_size!=len(content) or not validated_strong_etag(result.creation_etag)
        or result.creation_etag!=result.resource.etag or hashlib.sha256(content).hexdigest()!=run.revision['markdown_sha256']):
        return 'unknown'
    remote_identity(scope_key,result.resource.file_id)
    with _db_conn() as conn,conn.cursor(row_factory=dict_row) as cur:
        cur.execute('''SELECT to_jsonb(a) AS action,to_jsonb(r) AS receipt,to_jsonb(f) AS file,
            to_jsonb(l) AS link,to_jsonb(v) AS render,to_jsonb(ar) AS artifact,to_jsonb(c) AS claim
            FROM document_actions a
            LEFT JOIN document_receipts r ON r.action_id=a.id LEFT JOIN workspace_files f ON f.id=a.workspace_file_id
            LEFT JOIN workspace_file_nextcloud_links l ON l.workspace_file_id=f.id
            LEFT JOIN document_revision_renders v ON v.revision_id=a.revision_id
            LEFT JOIN document_artifacts ar ON ar.id=a.artifact_id
            LEFT JOIN conversation_turn_claims c ON c.turn_id=a.confirmation_turn_id WHERE a.id=%s::uuid''',(run.action['id'],))
        row=cur.fetchone()
    if not row:return 'unknown'
    a,r,f,l,v,ar,c=(row[k] or {} for k in ('action','receipt','file','link','render','artifact','claim'))
    if a.get('state')=='executing' and not a.get('workspace_file_id') and not r and not v and not ar.get('workspace_file_id') and not ar.get('current_revision_id'):
        return 'absent'
    if (a.get('state')!='succeeded' or r.get('nextcloud_scope_key')!=scope_key
        or r.get('nextcloud_file_id')!=result.resource.file_id or r.get('nextcloud_etag')!=result.creation_etag
        or r.get('revision_id')!=run.action['revision_id'] or r.get('confirmation_turn_id')!=run.token.turn_id
        or c.get('owner_id')!=run.token.owner_id or c.get('generation')!=run.token.generation):return 'unknown'
    from .document_workshop_publication_proof import verify
    return 'complete' if verify(run.action['id'],storage_root=storage_root) else 'unknown'


def verify_committed_action(action_id,*,storage_root):
    """Historical render and current linkage are distinct complete proofs."""
    from .document_workshop_publication_proof import verify
    return verify(action_id,storage_root=storage_root)
