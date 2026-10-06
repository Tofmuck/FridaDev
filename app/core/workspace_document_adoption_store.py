"""M2 local publication: immutable cache revisions and one SQL transaction.

No DAV, extraction, schema bootstrap or distributed-atomicity claim. Previously
published revisions are retained; an uncertain commit retains its prepared cache
and is never replayed automatically. Only definite failures discard owned bytes.
"""
import hashlib
from pathlib import Path
import re
from uuid import uuid4

from psycopg.rows import dict_row
from . import workspace_files, workspace_files_store, workspace_folders_store
from .document_workshop_contract import DocumentWorkshopError
from .workspace_document_paths import validate_document_source_path
from .workspace_document_nextcloud_read_client import MAX_SOURCE_BYTES
from .workspace_nextcloud_etag import validated_strong_etag

_SCHEMA = Path(__file__).with_name('sql') / 'workspace_document_adoption.sql'


def _db_conn():
    return workspace_files._db_conn()


def init_db():
    """Explicit migration; no import, request or shared bootstrap invokes this."""
    with _db_conn() as conn:
        conn.execute(_SCHEMA.read_text(encoding='utf-8'))
    return True


def remote_identity(scope_key, file_id):
    if (type(scope_key) is not str or not re.fullmatch(r'[0-9a-f]{64}', scope_key)
            or type(file_id) is not str or not re.fullmatch(r'[1-9][0-9]{0,63}', file_id)):
        raise DocumentWorkshopError('document_remote_identity_invalid')
    return scope_key + ':' + file_id


def check_resource(scope_key, resource):
    if resource.is_collection:
        raise DocumentWorkshopError('document_collection')
    path = validate_document_source_path(resource.relative_path)
    remote_identity(scope_key, resource.file_id)
    if not validated_strong_etag(resource.etag):
        raise DocumentWorkshopError('document_remote_version_invalid')
    if type(resource.byte_size) is not int or resource.byte_size <= 0:
        raise DocumentWorkshopError('document_remote_size_invalid')
    if resource.byte_size > MAX_SOURCE_BYTES:
        raise DocumentWorkshopError('document_source_limit')
    return path


def _candidates(cur, folder_id):
    cur.execute('''SELECT wf.*, to_jsonb(l) AS link FROM workspace_files wf
        LEFT JOIN workspace_file_nextcloud_links l ON l.workspace_file_id=wf.id
        WHERE wf.workspace_folder_id=%s::uuid''', (folder_id,))
    return cur.fetchall()


def list_candidates(folder_id):
    with _db_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Also proves migration presence, even when the local folder is empty.
            cur.execute('SELECT nextcloud_file_id FROM workspace_file_nextcloud_links LIMIT 0')
            return _candidates(cur, folder_id)


def classify_resource(rows, scope_key, resource):
    """Preliminary local match; the same rule runs again under publication locks."""
    path = check_resource(scope_key, resource)
    same = None
    for row in rows:
        link = row.get('link') or {}
        identity_matches = (link.get('nextcloud_scope_key') == scope_key and link.get('nextcloud_file_id') == resource.file_id)
        active = not row.get('deleted_at') and row.get('status') == 'active'
        if identity_matches:
            if not active or link.get('nextcloud_sync_state') != 'linked':
                raise DocumentWorkshopError('document_local_collision')
            if same is not None and str(same['id']) != str(row['id']):
                raise DocumentWorkshopError('document_local_collision')
            same = row
        if row.get('deleted_at') or row.get('status') == 'deleted':
            continue
        relative = link.get('nextcloud_relative_path')
        if relative is None:
            name = link.get('nextcloud_target_name') if link else row.get('original_filename')
            relative = 'Documents/' + name if type(name) is str and '/' not in name else None
        try:
            collision = validate_document_source_path(relative).collision_key == path.collision_key
        except DocumentWorkshopError:
            collision = False
        if not collision or identity_matches:
            continue
        legacy = (active and link and link.get('nextcloud_sync_state') == 'linked'
                  and link.get('nextcloud_file_id') is None and link.get('nextcloud_scope_key') is None
                  and relative == resource.relative_path)
        if not legacy or same is not None:
            raise DocumentWorkshopError('document_local_collision')
        same = row
    if same:
        known = (same.get('link') or {}).get('nextcloud_file_id') is not None
        return ('already_linked' if known else 'adoptable',
                'document_already_linked' if known else 'legacy_verification_required', same)
    return 'adoptable', 'document_adoptable', None


def _lock_scope(cur, folder_id, context_id, folder):
    cur.execute(f'''SELECT {workspace_folders_store._workspace_folder_select_columns()}
        FROM workspace_folders folders JOIN workspace_folder_nextcloud_links links ON links.workspace_folder_id=folders.id
        WHERE folders.id=%s::uuid AND folders.deleted_at IS NULL FOR UPDATE OF folders, links''', (folder_id,))
    current = workspace_folders_store.serialize_workspace_folder_row(cur.fetchone())
    if (not current or current.get('nextcloud_sync_state') != 'linked'
            or any(current.get(key) != folder.get(key) for key in ('nextcloud_target_name', 'nextcloud_folder_ref'))):
        raise DocumentWorkshopError('document_context_scope_changed')
    # Same historical rows/lock strength, before context authority. A deletion
    # locks the file before its invalidation trigger locks that context.
    cur.execute('SELECT id FROM workspace_files WHERE workspace_folder_id=%s::uuid FOR UPDATE', (folder_id,))
    cur.fetchall()
    cur.execute('SELECT workspace_file_id FROM workspace_file_nextcloud_links WHERE workspace_folder_id=%s::uuid FOR UPDATE', (folder_id,))
    cur.fetchall()
    cur.execute('''SELECT dc.* FROM document_workshop_contexts dc JOIN conversations c ON c.id=dc.conversation_id
        WHERE dc.id=%s::uuid AND dc.workspace_folder_id=%s::uuid AND dc.state='editing'
          AND c.workspace_folder_id=dc.workspace_folder_id AND c.deleted_at IS NULL FOR SHARE OF c''', (context_id,folder_id))
    context = cur.fetchone()
    if not context:
        raise DocumentWorkshopError('document_context_scope_changed')
    cur.execute("SELECT state FROM document_workshop_contexts WHERE id=%s FOR SHARE", (context_id,))
    if cur.fetchone()['state'] != 'editing':
        raise DocumentWorkshopError('document_context_scope_changed')
    if context['target_file_id'] is not None:
        cur.execute('''SELECT wf.id FROM workspace_files wf JOIN workspace_file_nextcloud_links l ON l.workspace_file_id=wf.id
            WHERE wf.id=%s AND wf.workspace_folder_id=%s::uuid AND wf.deleted_at IS NULL
              AND wf.status='active' AND wf.content_kind='document' AND wf.media_kind='text' AND wf.source_extension IN ('.md','.docx')
              AND l.workspace_folder_id=wf.workspace_folder_id AND l.nextcloud_sync_state='linked'
              AND l.nextcloud_document_ref=%s
              AND COALESCE(l.nextcloud_relative_path,'Documents/' || l.nextcloud_target_name)=%s
              AND (l.nextcloud_scope_key || ':' || l.nextcloud_file_id) IS NOT DISTINCT FROM %s FOR SHARE OF wf,l''',
            (context['target_file_id'],folder_id,context['target_document_ref'],context['target_relative_path'],context['target_remote_identity']))
        if not cur.fetchone():
            raise DocumentWorkshopError('document_context_scope_changed')


def _legacy_proof(row, content_digest, storage_root):
    if not row or (row.get('link') or {}).get('nextcloud_file_id') is not None:
        return None
    try:
        with workspace_files_store.workspace_file_path(storage_root, row['storage_key']).open('rb') as handle:
            data = handle.read(MAX_SOURCE_BYTES + 1)
        if len(data) > MAX_SOURCE_BYTES or hashlib.sha256(data).hexdigest() != content_digest:
            raise ValueError
    except (OSError, ValueError, KeyError):
        raise DocumentWorkshopError('document_local_collision') from None
    return tuple(row.get(key) for key in ('id','storage_key','sha256','updated_at'))


def _discard(path):
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass  # An unreferenced prepared cache is preferable to losing published data.


def publish_adoption(*, folder_id, context_id, folder, scope_key, resource, content, extraction, storage_root):
    path = check_resource(scope_key, resource)
    if type(content) is not bytes or len(content) != resource.byte_size or extraction.status != 'complete':
        raise DocumentWorkshopError('document_remote_incompatible')
    digest = hashlib.sha256(content).hexdigest()
    _, _, previous = classify_resource(list_candidates(folder_id), scope_key, resource)
    legacy_proof = _legacy_proof(previous, digest, storage_root)
    # Random revision UUID is independent of both file ID and every human name.
    storage_key = str(uuid4()) + '/' + str(uuid4())
    prepared = workspace_files_store.workspace_file_path(storage_root, storage_key)
    commit_started = False
    try:
        workspace_files_store.write_file_bytes(storage_root, storage_key, content)
        with _db_conn() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                _lock_scope(cur, folder_id, context_id, folder)
                _, _, previous = classify_resource(_candidates(cur, folder_id), scope_key, resource)
                if previous:
                    link = previous.get('link') or {}
                    if link.get('nextcloud_file_id') is None:
                        if legacy_proof is None or legacy_proof != tuple(previous.get(key) for key in ('id','storage_key','sha256','updated_at')):
                            raise DocumentWorkshopError('document_local_collision')
                    elif link.get('nextcloud_etag') == resource.etag and link.get('observed_sha256') != digest:
                        raise DocumentWorkshopError('document_remote_changed')
                file_id = str(previous['id']) if previous else str(uuid4())
                name = path.segments[-1]
                values = (file_id,folder_id,name,name,storage_key,extraction.media_type,extraction.source_extension,len(content),digest,digest[:12],extraction.chars,extraction.sha256_12)
                cur.execute('''INSERT INTO workspace_files (id,workspace_folder_id,display_name,original_filename,storage_key,
                    content_kind,media_kind,mime_type,source_extension,byte_size,sha256,sha256_12,text_chars,text_sha256_12,status,source_kind)
                    VALUES (%s::uuid,%s::uuid,%s,%s,%s,'document','text',%s,%s,%s,%s,%s,%s,%s,'active','nextcloud_adoption')
                    ON CONFLICT (id) DO UPDATE SET display_name=EXCLUDED.display_name,original_filename=EXCLUDED.original_filename,
                    storage_key=EXCLUDED.storage_key,mime_type=EXCLUDED.mime_type,source_extension=EXCLUDED.source_extension,
                    byte_size=EXCLUDED.byte_size,sha256=EXCLUDED.sha256,sha256_12=EXCLUDED.sha256_12,text_chars=EXCLUDED.text_chars,
                    text_sha256_12=EXCLUDED.text_sha256_12,updated_at=now() RETURNING *''', values)
                row = cur.fetchone()
                existing_link = (previous or {}).get('link') or {}
                document_ref = existing_link.get('nextcloud_document_ref') or 'workspace-file:' + file_id
                origin = existing_link.get('document_origin') if previous else 'external'
                cur.execute('''INSERT INTO workspace_file_nextcloud_links (workspace_file_id,workspace_folder_id,nextcloud_sync_state,
                    nextcloud_document_ref,nextcloud_name_hash,nextcloud_target_name,nextcloud_relative_path,nextcloud_collision_key,
                    nextcloud_file_id,nextcloud_scope_key,nextcloud_etag,observed_at,observed_sha256,document_origin,last_sync_at,last_sync_operation,last_sync_reason_code)
                    VALUES (%s::uuid,%s::uuid,'linked',%s,%s,%s,%s,%s,%s,%s,%s,now(),%s,%s,now(),'observe','folder_document_list_ok')
                    ON CONFLICT (workspace_file_id) DO UPDATE SET nextcloud_relative_path=EXCLUDED.nextcloud_relative_path,
                    nextcloud_collision_key=EXCLUDED.nextcloud_collision_key,nextcloud_target_name=EXCLUDED.nextcloud_target_name,
                    nextcloud_file_id=EXCLUDED.nextcloud_file_id,nextcloud_scope_key=EXCLUDED.nextcloud_scope_key,
                    nextcloud_etag=EXCLUDED.nextcloud_etag,observed_at=now(),observed_sha256=EXCLUDED.observed_sha256,
                    nextcloud_name_hash=EXCLUDED.nextcloud_name_hash,last_sync_at=now(),last_sync_operation='observe',updated_at=now()''',
                    (file_id,folder_id,document_ref,hashlib.sha256(name.encode()).hexdigest()[:12],name,path.relative_path,path.collision_key,
                     resource.file_id,scope_key,resource.etag,digest,origin))
            commit_started = True
        item = workspace_files_store.serialize_workspace_file_row(row)
        item.update(document_relative_path=path.relative_path,document_remote_delete_available=False)
        if origin == 'external':
            item['document_origin'] = 'external'
        return {'category': 'already_linked' if previous else 'adopted', 'file': item}
    except Exception as exc:
        if not commit_started:
            _discard(prepared)
        if isinstance(exc, DocumentWorkshopError):
            raise
        raise DocumentWorkshopError('document_adoption_commit_unknown' if commit_started else 'document_adoption_storage_unavailable') from None
