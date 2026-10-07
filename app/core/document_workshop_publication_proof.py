"""Read-only complete historical evidence plus the separately current revision.

An old receipt owns its immutable render/cache. The inventory/link own the
artifact's current revision. Neither substitutes the other's bytes or hashes.
"""
import hashlib
from datetime import datetime
from psycopg.rows import dict_row
from . import document_workshop_execution_store as store, workspace_files_store
from .document_canonical import validate_canonical
from .document_markdown import serialize_markdown
from .workspace_document_paths import validate_document_path
from .workspace_nextcloud_etag import validated_strong_etag


def _bundle(conn,action_id):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute('''SELECT to_jsonb(a) AS action,to_jsonb(r) AS receipt,to_jsonb(v) AS render,
            to_jsonb(d) AS revision,to_jsonb(c) AS claim,to_jsonb(ar) AS artifact
            FROM document_actions a LEFT JOIN document_receipts r ON r.action_id=a.id
            LEFT JOIN document_revision_renders v ON v.revision_id=a.revision_id
            LEFT JOIN document_revisions d ON d.id=a.revision_id
            LEFT JOIN conversation_turn_claims c ON c.turn_id=a.confirmation_turn_id
            LEFT JOIN document_artifacts ar ON ar.id=a.artifact_id WHERE a.id=%s::uuid''',(action_id,))
        return cur.fetchone()


def _cache(root,render,content):
    if (not render.get('storage_key') or render.get('format')!='markdown'
            or render.get('serializer_version')!='frida_markdown_v1'
            or render.get('content_sha256')!=hashlib.sha256(content).hexdigest() or render.get('byte_size')!=len(content)):
        return False
    try:
        with workspace_files_store.workspace_file_path(root,render['storage_key']).open('rb') as handle:
            return handle.read(16*1024*1024+1)==content
    except (OSError,ValueError):return False


def _historical(conn,bundle,root):
    if not bundle:return False
    a,r,v,d,c,ar=(bundle[k] or {} for k in ('action','receipt','render','revision','claim','artifact'))
    required=('conversation_id','workspace_folder_id','artifact_id','revision_id','operation','format','relative_path')
    if (a.get('state')!='succeeded' or not a.get('workspace_file_id')
            or a.get('operation') not in ('create','copy','update') or a.get('format')!='markdown'
            or any(a.get(k)!=r.get(k) for k in required)
            or r.get('action_id')!=a['id'] or r.get('request_turn_id')!=a['id']
            or r.get('confirmation_turn_id')!=a.get('confirmation_turn_id') or r.get('confirmed_at')!=a.get('confirmed_at')
            or r.get('workspace_file_id')!=a['workspace_file_id'] or r.get('revision_author')!='frida'
            or ar.get('workspace_file_id')!=a['workspace_file_id'] or ar.get('workspace_folder_id')!=a.get('workspace_folder_id')
            or ar.get('id')!=a.get('artifact_id') or d.get('id')!=a.get('revision_id') or d.get('artifact_id')!=a.get('artifact_id')
            or v.get('revision_id')!=a.get('revision_id') or c.get('kind')!='confirmation'
            or c.get('turn_id')!=a.get('confirmation_turn_id') or c.get('conversation_id')!=a.get('conversation_id')
            or c.get('context_id')!=a.get('context_id')
            or c.get('request_fingerprint')!=store._fingerprint(a['id'],{k:a[k] for k in ('context_id','conversation_id','workspace_folder_id','revision_id')})):
        return False
    canonical=validate_canonical(d['canonical']);content=serialize_markdown(canonical).encode('utf-8')
    canonical_hash=hashlib.sha256(store._json(canonical.as_dict()).encode()).hexdigest()
    content_hash=hashlib.sha256(content).hexdigest()
    if (d.get('canonical_sha256')!=canonical_hash or d.get('markdown_sha256')!=content_hash
            or d.get('serializer_version')!='frida_markdown_v1' or d.get('schema_version')!=1
            or d.get('word_count')!=canonical.word_count or d.get('codepoint_count')!=canonical.codepoint_count
            or r.get('canonical_sha256')!=canonical_hash or r.get('content_sha256')!=content_hash
            or not _cache(root,v,content)):
        return False
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM document_execution_journal WHERE action_id=%s::uuid ORDER BY created_at,id",(a['id'],));journal=cur.fetchall()
    intents=[j for j in journal if j['event']=='intent'];puts=[j for j in journal if j['event']=='put_intent']
    outcomes=[j for j in journal if j['event']=='remote_outcome']
    if len(intents)!=1 or len(puts)!=1 or len(outcomes)!=1:return False
    outcome=outcomes[0]
    if (outcome['state']!='known_success' or outcome['http_status'] not in ((200,204) if a['operation']=='update' else (201,))
            or not validated_strong_etag(outcome['etag']) or outcome['etag']!=r.get('nextcloud_etag')):return False
    for j in intents+puts+outcomes:
        if (str(j['confirmation_turn_id'])!=a['confirmation_turn_id'] or str(j['owner_id'])!=c.get('owner_id')
                or j['generation']!=c.get('generation') or j['canonical_sha256']!=canonical_hash
                or j['content_sha256']!=content_hash or j['serializer_version']!='frida_markdown_v1'):
            return False
    if any(j['path_sha256']!=hashlib.sha256(a['relative_path'].encode()).hexdigest() for j in intents+puts):return False
    repaired=[j for j in journal if j['event']=='metadata_published']
    repair_intents=[j for j in journal if j['event']=='metadata_reconciliation']
    if repaired:
        if len(repaired)!=1 or len(repair_intents)!=1 or a['operation']!='update' or c.get('state')=='active':return False
        j=repaired[0];repair=store.claims._read(conn,str(j['confirmation_turn_id']))
        if (not repair or repair['state']!='succeeded' or repair['outcome']!='succeeded' or repair['kind']!='confirmation'
                or str(repair['turn_id'])==a['confirmation_turn_id'] or str(repair['owner_id'])!=str(j['owner_id'])
                or repair['generation']!=j['generation'] or str(repair['conversation_id'])!=a['conversation_id']
                or str(repair['context_id'])!=a['context_id'] or j['content_sha256']!=content_hash
                or j['canonical_sha256']!=canonical_hash or j['etag']!=r['nextcloud_etag']
                or repair['request_fingerprint']!=hashlib.sha256(('metadata:'+a['id']).encode()).hexdigest()
                or repair['expected_etag']!=a['target_version']['etag'] or j['serializer_version']!='frida_markdown_v1'):return False
        initial=repair_intents[0]
        if any(initial[key]!=j[key] for key in ('confirmation_turn_id','owner_id','generation','canonical_sha256',
                'content_sha256','serializer_version','etag')) or initial['state']!='remote_uncertain' or j['state']!='known_success':return False
    elif c.get('state')!='succeeded' or c.get('outcome')!='succeeded':return False
    version=a.get('target_version') if a['operation']=='update' else None
    if a['operation']=='update':
        if (not version or r.get('creation_author')!=version.get('creation_author')
                or c.get('expected_etag')!=version.get('etag')
                or r.get('workspace_file_id')!=version.get('workspace_file_id')
                or r.get('relative_path')!=version.get('relative_path')
                or r.get('nextcloud_scope_key')!=version.get('scope_key')
                or r.get('nextcloud_file_id')!=version.get('remote_file_id')):return False
    elif r.get('creation_author')!='frida':return False
    # Valid identity shape is required even on an historical resource.
    store.remote_identity(r['nextcloud_scope_key'],r['nextcloud_file_id'])
    return True


def verify(action_id,*,storage_root):
    if storage_root is None:return False
    with store._db_conn() as conn,conn.cursor(row_factory=dict_row) as cur:
        original=_bundle(conn,action_id)
        if not _historical(conn,original,storage_root):return False
        a,ar=original['action'],original['artifact']
        cur.execute('SELECT id::text FROM document_actions WHERE artifact_id=%s::uuid AND revision_id=%s::uuid AND state=\'succeeded\'',
            (ar['id'],ar['current_revision_id']));matches=cur.fetchall()
        if len(matches)!=1:return False
        selected=matches[0]
        current=original if selected['id']==action_id else _bundle(conn,selected['id'])
        if current is not original and not _historical(conn,current,storage_root):return False
        r,v,ca=current['receipt'],current['render'],current['action']
        cur.execute('SELECT * FROM workspace_files WHERE id=%s::uuid',(a['workspace_file_id'],));f=cur.fetchone()
        cur.execute('SELECT * FROM workspace_file_nextcloud_links WHERE workspace_file_id=%s::uuid',(a['workspace_file_id'],));l=cur.fetchone()
        version=ca.get('target_version') if ca['operation']=='update' else None
        origin=version['document_origin'] if version else 'frida'
        source_kind=version['source_kind'] if version else 'document_workshop'
        target=validate_document_path(r['relative_path'],format='markdown')
        if (not f or not l or str(f['workspace_folder_id'])!=a['workspace_folder_id'] or f['deleted_at'] is not None
                or f['status']!='active' or f['content_kind']!='document' or f['media_kind']!='text' or f['source_extension']!='.md'
                or f['mime_type']!=(version['mime_type'] if version else 'text/markdown')
                or version and datetime.fromisoformat(version['created_at'])!=f['created_at']
                or f['source_kind']!=source_kind or f['display_name']!=target.segments[-1] or f['original_filename']!=target.segments[-1]
                or f['storage_key']!=v['storage_key'] or f['byte_size']!=v['byte_size'] or f['sha256']!=r['content_sha256']
                or str(l['workspace_folder_id'])!=a['workspace_folder_id'] or l['nextcloud_sync_state']!='linked'
                or l['document_origin']!=origin or l['nextcloud_relative_path']!=r['relative_path']
                or l['nextcloud_collision_key']!=target.collision_key or l['observed_sha256']!=r['content_sha256']
                or l['nextcloud_target_name']!=(version['nextcloud_target_name'] if version else target.segments[-1])
                or l['nextcloud_name_hash']!=(version['nextcloud_name_hash'] if version else hashlib.sha256(target.segments[-1].encode()).hexdigest()[:12])
                or l['nextcloud_document_ref']!=(version['document_ref'] if version else 'workspace-file:'+a['workspace_file_id'])
                or any(l[k]!=r[k] for k in ('nextcloud_scope_key','nextcloud_file_id','nextcloud_etag'))
                or ca['workspace_file_id']!=a['workspace_file_id'] or current['artifact']['id']!=ar['id']):return False
    return True
