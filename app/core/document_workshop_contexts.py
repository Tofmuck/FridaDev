"""M1 PostgreSQL context identities. No contents, TTL, claims or action state."""
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
import config
from admin import runtime_settings
from . import runtime_db_bootstrap

_SCHEMA = Path(__file__).with_name('sql') / 'document_workshop_contexts.sql'
_COLUMNS = 'id, conversation_id, workspace_folder_id, target_file_id, target_relative_path, target_document_ref, target_remote_identity, state, created_at'


def _db_conn():
    return runtime_db_bootstrap.connect_runtime_database(psycopg, config, runtime_settings)


def init_db():
    """Explicit bootstrap, following the existing stores; never run on import."""
    with _db_conn() as conn:
        conn.execute(_SCHEMA.read_text(encoding='utf-8'))
    return True


def _record(row):
    if row is None:
        return None
    result = dict(row)
    for key in ('id', 'conversation_id', 'workspace_folder_id', 'target_file_id'):
        result[key] = str(result[key]) if result[key] is not None else None
    result['created_at'] = result['created_at'].isoformat()
    return result


def create_context(*, conversation_id, workspace_folder_id, target_file_id=None,
                   target_relative_path=None, target_document_ref=None, target_remote_identity=None):
    # Recheck and lock resource rows inside the INSERT transaction. A move or
    # tombstone between service validation and registration cannot admit stale scope.
    with _db_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(f'''
                WITH scope AS (
                    SELECT c.id FROM conversations c JOIN workspace_folders f ON f.id=c.workspace_folder_id
                    WHERE c.id=%s::uuid AND f.id=%s::uuid AND c.deleted_at IS NULL AND f.deleted_at IS NULL
                    FOR SHARE OF c, f
                ), target AS (
                    SELECT wf.id FROM workspace_files wf JOIN workspace_file_nextcloud_links l ON l.workspace_file_id=wf.id
                    WHERE wf.id=%s::uuid AND wf.workspace_folder_id=%s::uuid AND wf.deleted_at IS NULL
                      AND wf.status='active' AND wf.content_kind='document' AND wf.media_kind='text'
                      AND wf.source_extension IN ('.md','.docx') AND l.workspace_folder_id=wf.workspace_folder_id
                      AND l.nextcloud_sync_state='linked' AND l.nextcloud_document_ref=%s
                      AND COALESCE(to_jsonb(l)->>'nextcloud_relative_path', 'Documents/' || l.nextcloud_target_name)=%s
                      AND ((to_jsonb(l)->>'nextcloud_scope_key') || ':' || (to_jsonb(l)->>'nextcloud_file_id')) IS NOT DISTINCT FROM %s
                    FOR SHARE OF wf, l
                )
                INSERT INTO document_workshop_contexts
                    (id, conversation_id, workspace_folder_id, target_file_id, target_relative_path, target_document_ref, target_remote_identity)
                SELECT %s::uuid, id, %s::uuid, %s::uuid, %s, %s, %s FROM scope
                WHERE %s::uuid IS NULL OR EXISTS (SELECT 1 FROM target)
                RETURNING {_COLUMNS}
                ''', (conversation_id, workspace_folder_id, target_file_id, workspace_folder_id,
                      target_document_ref, target_relative_path, target_remote_identity, str(uuid4()), workspace_folder_id,
                      target_file_id, target_relative_path, target_document_ref, target_remote_identity, target_file_id))
            return _record(cur.fetchone())


def get_context(context_id):
    with _db_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(f'SELECT {_COLUMNS} FROM document_workshop_contexts WHERE id=%s::uuid', (context_id,))
            return _record(cur.fetchone())
