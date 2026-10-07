"""M4 durable preparation authority. Snapshot and proposal share one transaction."""
from pathlib import Path
from uuid import UUID, uuid4
import hashlib
import json
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from . import conversation_turn_claims as claims, runtime_db_bootstrap
from .document_workshop_contract import DocumentWorkshopError
from .workspace_document_paths import validate_document_path, validate_document_source_path
import config
from admin import runtime_settings

_SCHEMA = Path(__file__).with_name('sql') / 'document_workshop_actions.sql'
LIMITATIONS = ('write_confirmation_unavailable', 'markdown_pagination_reader_dependent', 'markdown_style_reader_dependent', 'docx_pdf_unavailable', 'update_unavailable')
CAPABILITIES = dict(prepare=True, confirm=False, formats=['markdown'], operations=['create','copy'], update=False)


def capabilities(executor=None):
    result=dict(CAPABILITIES,confirm=executor is not None)
    if getattr(executor,'supports_update',False):result.update(operations=['create','copy','update'],update=True)
    return result


def _db_conn():
    return runtime_db_bootstrap.connect_runtime_database(psycopg, config, runtime_settings)


def init_db():
    with _db_conn() as conn:
        conn.execute(_SCHEMA.read_text(encoding='utf-8'))
    return True


def _read(conn, action_id, *, lock=False):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute('SELECT * FROM document_actions WHERE id=%s::uuid' + (' FOR UPDATE NOWAIT' if lock else ''), (action_id,))
        return cur.fetchone()


def _public(row):
    if not row: return None
    keys = ('id','context_id','conversation_id','workspace_folder_id','state','phase','received_content_codepoints',
            'reason_code','revision_id','artifact_id','operation','format','relative_path','limitations','created_at','updated_at')
    result = {k: (str(row[k]) if isinstance(row[k], UUID) else row[k].isoformat() if hasattr(row[k], 'isoformat') else row[k]) for k in keys}
    result['turn_id'] = result['id']
    result['name'] = row['relative_path'].split('/')[-1] if row['relative_path'] else None
    for key in ('confirmation_turn_id','confirmed_at','created_collections_count','workspace_file_id'):
        if key in row:
            value=row[key]
            result[key]=str(value) if isinstance(value,UUID) else value.isoformat() if hasattr(value,'isoformat') else value
    result['capabilities'] = dict(confirm=False, cancel=row['state'] in ('preparing','pending','executing'))
    return result


def get_action(action_id):
    with _db_conn() as conn:
        row = _read(conn, action_id)
    if row and row['state']=='executing':
        from . import document_workshop_execution_store as execution
        execution.reconcile(action_id)
        with _db_conn() as conn:row=_read(conn,action_id)
    if row and row['state'] == 'preparing':
        claim = claims.read(str(row['id']))
        if claim and claim['state'] != 'active':
            # Expiry is claim authority; it never expires a valid pending.
            with _db_conn() as conn:
                conn.execute("UPDATE document_actions SET state=%s,reason_code=%s,updated_at=clock_timestamp() WHERE id=%s::uuid AND state='preparing'",
                    (claim['state'] if claim['state'] in ('lost','interrupted','cancelled','invalidated','failed') else 'interrupted',
                     claim.get('reason_code') or 'document_claim_closed', action_id))
                row = _read(conn, action_id)
    return _public(row)


def latest(context_id):
    with _db_conn() as conn:
        row = conn.execute('SELECT id FROM document_actions WHERE context_id=%s::uuid ORDER BY created_at DESC LIMIT 1', (context_id,)).fetchone()
    return get_action(str(row[0])) if row else None


def _source_rows(conn, folder_id, file_ids):
    result = {}
    for file_id in sorted(file_ids):
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('SELECT * FROM workspace_files WHERE id=%s::uuid FOR SHARE NOWAIT', (file_id,))
            file = cur.fetchone()
            cur.execute('SELECT * FROM workspace_file_nextcloud_links WHERE workspace_file_id=%s::uuid FOR SHARE NOWAIT', (file_id,))
            link = cur.fetchone()
        if (not file or str(file['workspace_folder_id']) != folder_id or file['deleted_at'] is not None
                or file['status'] != 'active' or file['content_kind'] != 'document' or file['media_kind'] != 'text'
                or not link or str(link['workspace_folder_id']) != folder_id or link['nextcloud_sync_state'] != 'linked'
                or not all(link.get(k) for k in ('nextcloud_relative_path','nextcloud_scope_key','nextcloud_file_id','nextcloud_etag','observed_sha256'))):
            raise DocumentWorkshopError('document_source_reference_invalid')
        result[file_id] = link
    return result


def _authority(conn, token):
    current, claim = claims.check_in_transaction(conn, token, conversation_id=token.conversation_id)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute('SELECT * FROM document_workshop_contexts WHERE id=%s::uuid', (token.context_id,))
        ctx = cur.fetchone()
    return current, ctx, claim


def save_initial(token, conversation, source_ids, *, snapshot):
    with _db_conn() as conn:
        current, ctx, _ = _authority(conn, token)
        _source_rows(conn, str(ctx['workspace_folder_id']), source_ids)
        conversation['workspace_folder_id'] = str(current['workspace_folder_id'])
        snapshot(conversation, conn)
        conn.execute('''INSERT INTO document_actions(id,context_id,conversation_id,workspace_folder_id,source_file_ids)
            VALUES (%s::uuid,%s::uuid,%s::uuid,%s::uuid,%s)''',
            (token.turn_id,token.context_id,token.conversation_id,str(ctx['workspace_folder_id']),Jsonb(list(source_ids))))
    return get_action(token.turn_id)


def project_progress(token, snapshot):
    with _db_conn() as conn:
        _authority(conn, token)
        row = _read(conn, token.turn_id, lock=True)
        if not row or row['state'] != 'preparing':
            raise DocumentWorkshopError('document_preparation_closed')
        conn.execute('UPDATE document_actions SET phase=%s,received_content_codepoints=%s,updated_at=clock_timestamp() WHERE id=%s::uuid',
                     (snapshot.phase,snapshot.received_content_codepoints,token.turn_id))


def check_active(token):
    with _db_conn() as conn:
        _authority(conn, token)
        row = _read(conn, token.turn_id)
        if not row or row['state'] != 'preparing':
            raise DocumentWorkshopError('document_preparation_closed')


def _verify_versions(conn, ctx, source_ids, versions):
    links = _source_rows(conn, str(ctx['workspace_folder_id']), source_ids)
    if len(versions) != len(source_ids) or {v['workspace_file_id'] for v in versions} != set(source_ids):
        raise DocumentWorkshopError('document_source_reference_invalid')
    for source in versions:
        link = links[source['workspace_file_id']]
        if (source['remote_identity'] != link['nextcloud_scope_key'] + ':' + link['nextcloud_file_id']
                or source['etag'] != link['nextcloud_etag'] or source['sha256'] != link['observed_sha256']
                or source['relative_path'] != link['nextcloud_relative_path']):
            raise DocumentWorkshopError('document_remote_changed')


def finalize(token, conversation, envelope, versions, markdown, *, snapshot, target_source=None):
    revision_id = artifact_id = None
    with _db_conn() as conn:
        current, ctx, _ = _authority(conn, token)
        row = _read(conn, token.turn_id, lock=True)
        if not row or row['state'] != 'preparing':
            raise DocumentWorkshopError('document_preparation_closed')
        source_ids = row['source_file_ids']
        _verify_versions(conn, ctx, source_ids, versions)
        state = envelope.status
        if state == 'prepared':
            path = validate_document_path(envelope.relative_path, format='markdown')
            if not set(envelope.source_file_ids).issubset(source_ids):
                raise DocumentWorkshopError('document_source_reference_invalid')
            if envelope.operation=='update':
                from . import document_workshop_update_target as update
                target_version=update.snapshot(conn,ctx,target_source)
                if path.relative_path!=target_version['relative_path']:
                    raise DocumentWorkshopError('document_update_target_invalid')
            else:target_version=None
            if ctx['target_file_id'] and envelope.operation!='update' and (envelope.operation != 'copy' or str(ctx['target_file_id']) not in envelope.source_file_ids):
                raise DocumentWorkshopError('document_operation_unavailable')
            # A known inventory collision is useful conflict, never rename/update.
            inventory = conn.execute('''SELECT COALESCE(l.nextcloud_relative_path,
                    'Documents/'||COALESCE(l.nextcloud_target_name,to_jsonb(f)->>'original_filename'))
                FROM workspace_files f LEFT JOIN workspace_file_nextcloud_links l ON f.id=l.workspace_file_id
                WHERE f.workspace_folder_id=%s::uuid AND f.deleted_at IS NULL AND f.status<>'deleted'
                ''', (str(ctx['workspace_folder_id']),)).fetchall()
            for item in inventory:
                try:
                    collision = validate_document_source_path(item[0]).collision_key == path.collision_key
                except DocumentWorkshopError:
                    # Same preliminary collision rule as M2; unrelated image
                    # uploads and unreadable legacy paths do not grant authority.
                    collision = False
                if collision and envelope.operation!='update':
                    raise DocumentWorkshopError('document_local_collision')
            revision_id, artifact_id = str(uuid4()), str(uuid4())
            if target_version:
                existing=conn.execute('SELECT id::text,current_revision_id::text FROM document_artifacts WHERE workspace_file_id=%s::uuid FOR UPDATE NOWAIT',
                    (target_version['workspace_file_id'],)).fetchone()
                if existing:artifact_id=existing[0]
                else:conn.execute('INSERT INTO document_artifacts(id,workspace_folder_id,workspace_file_id) VALUES(%s::uuid,%s::uuid,%s::uuid)',
                    (artifact_id,str(ctx['workspace_folder_id']),target_version['workspace_file_id']))
                target_version['base_revision_id']=existing[1] if existing else None
            else:conn.execute('INSERT INTO document_artifacts(id,workspace_folder_id) VALUES (%s::uuid,%s::uuid)', (artifact_id,str(ctx['workspace_folder_id'])))
            raw = json.dumps(envelope.canonical.as_dict(), ensure_ascii=False, sort_keys=True, separators=(',',':'))
            conn.execute('''INSERT INTO document_revisions(id,artifact_id,schema_version,canonical,canonical_sha256,
                markdown_sha256,serializer_version,word_count,codepoint_count) VALUES (%s::uuid,%s::uuid,1,%s,%s,%s,'frida_markdown_v1',%s,%s)''',
                (revision_id,artifact_id,Jsonb(envelope.canonical.as_dict()),hashlib.sha256(raw.encode()).hexdigest(),
                 hashlib.sha256(markdown.encode()).hexdigest(),envelope.canonical.word_count,envelope.canonical.codepoint_count))
            conn.execute("UPDATE document_actions SET state='superseded',reason_code='document_superseded',updated_at=clock_timestamp() WHERE context_id=%s::uuid AND state='pending'", (token.context_id,))
            state = 'pending'
        meta = conversation['messages'][-1]['meta']
        meta['document_workshop']['revision_id'] = revision_id
        conversation['workspace_folder_id'] = str(current['workspace_folder_id'])
        snapshot(conversation, conn)
        target_assignment=',target_version=%s' if envelope.operation=='update' else ''
        values=(state,Jsonb(versions),revision_id,artifact_id,envelope.operation,envelope.format,envelope.relative_path,
             Jsonb(list(dict.fromkeys(list(envelope.limitations)+[code for code in LIMITATIONS if code!='update_unavailable' or envelope.operation!='update']))))
        conn.execute('''UPDATE document_actions SET state=%s,phase='complete',source_versions=%s,
            revision_id=%s::uuid,artifact_id=%s::uuid,operation=%s,format=%s,relative_path=%s,
            limitations=%s,updated_at=clock_timestamp()'''+target_assignment+' WHERE id=%s::uuid',
            values+((Jsonb(target_version),) if target_assignment else ())+(token.turn_id,))
        claims.record_outcome_in_transaction(conn, token, 'succeeded')
        conn.execute("UPDATE conversation_turn_claims SET state='succeeded',finished_at=clock_timestamp() WHERE turn_id=%s::uuid", (token.turn_id,))
        result=_public(_read(conn,token.turn_id))
    return result


def fail(token, conversation, reason, *, snapshot):
    with _db_conn() as conn:
        _authority(conn, token)
        row = _read(conn, token.turn_id, lock=True)
        if not row or row['state'] != 'preparing':
            raise DocumentWorkshopError('document_preparation_closed')
        snapshot(conversation, conn)
        conn.execute("UPDATE document_actions SET state='failed',phase='failed',reason_code=%s,updated_at=clock_timestamp() WHERE id=%s::uuid", (reason,token.turn_id))
        claims.record_outcome_in_transaction(conn, token, 'interrupted')
        conn.execute("UPDATE conversation_turn_claims SET state='failed',reason_code=%s,finished_at=clock_timestamp() WHERE turn_id=%s::uuid",
            ('document_inactivity' if reason=='document_inactivity' else None,token.turn_id))


def cancel(action_id, context_id):
    with _db_conn() as conn:
        row = _read(conn, action_id)
        if not row or str(row['context_id']) != context_id:
            raise DocumentWorkshopError('document_action_missing')
        if row['state'] not in ('preparing','pending','executing'):
            return _public(row)
        current = claims._conversation(conn, str(row['conversation_id']))
        claims._scope(conn, current, context_id)
        # Finalization may have won the conversation lock since the first read.
        # A pending proposal no longer owns a live treatment: leave its successful
        # historical claim, and any other turn in this context, untouched.
        row = _read(conn, action_id)
        if row and row['state'] == 'preparing':
            conn.execute('SELECT turn_id FROM conversation_turn_claims WHERE turn_id=%s::uuid FOR UPDATE NOWAIT', (action_id,))
        elif row and row['state']=='executing':
            conn.execute('SELECT turn_id FROM conversation_turn_claims WHERE turn_id=%s::uuid FOR UPDATE NOWAIT',(row['confirmation_turn_id'],))
        row = _read(conn, action_id, lock=True)
        if not row:
            raise DocumentWorkshopError('document_action_missing')
        if row['state'] not in ('preparing','pending','executing'):
            return _public(row)
        if row['state'] == 'preparing':
            conn.execute("""UPDATE conversation_turn_claims SET state='cancelled',reason_code=NULL,
                finished_at=clock_timestamp() WHERE turn_id=%s::uuid AND conversation_id=%s::uuid
                AND context_id=%s::uuid AND kind='preparation' AND state='active'""",
                (action_id,str(row['conversation_id']),context_id))
        if row['state']=='executing':
            conn.execute("""UPDATE conversation_turn_claims SET state='cancelled',outcome='interrupted',finished_at=clock_timestamp()
                WHERE turn_id=%s::uuid AND conversation_id=%s::uuid AND context_id=%s::uuid
                AND kind='confirmation' AND state='active' AND lease_until>clock_timestamp()""",
                (row['confirmation_turn_id'],str(row['conversation_id']),context_id))
            intended=conn.execute('SELECT 1 FROM document_execution_journal WHERE action_id=%s::uuid LIMIT 1',(action_id,)).fetchone()
            conn.execute("UPDATE document_actions SET state=%s,phase='cancelled',reason_code='document_execution_cancelled',updated_at=clock_timestamp() WHERE id=%s::uuid",
                ('remote_uncertain' if intended else 'cancelled',action_id))
        else:conn.execute("""UPDATE document_actions SET state='cancelled',reason_code='document_preparation_cancelled',
            updated_at=clock_timestamp() WHERE id=%s::uuid AND context_id=%s::uuid
            AND state IN ('preparing','pending')""", (action_id,context_id))
    return get_action(action_id)


def abort(token, reason):
    """Failure during blocked upstream inputs: close without a stale snapshot."""
    with _db_conn() as conn:
        _authority(conn, token)
        row = _read(conn, token.turn_id, lock=True)
        if not row or row['state'] != 'preparing':
            raise DocumentWorkshopError('document_preparation_closed')
        conn.execute("UPDATE document_actions SET state='failed',phase='failed',reason_code=%s,updated_at=clock_timestamp() WHERE id=%s::uuid", (reason,token.turn_id))
        conn.execute("UPDATE conversation_turn_claims SET state='failed',outcome='interrupted',reason_code=%s,finished_at=clock_timestamp() WHERE turn_id=%s::uuid",
            ('document_inactivity' if reason == 'document_inactivity' else None,token.turn_id))
