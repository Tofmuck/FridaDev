"""M8-A immutable internal snapshots, never a receipt or publication authority."""
from pathlib import Path

from . import document_renderer_contract as c
from . import document_workshop_execution_store as execution

_SCHEMA = Path(__file__).with_name('sql') / 'document_renderer_m8a.sql'


def init_db():
    """Explicit migration after M5; never run by import/startup/rendering."""
    with execution._db_conn() as conn:
        conn.execute(_SCHEMA.read_text(encoding='utf-8'))


def project_progress(run, value):
    # Session already validated the counters and calls only on useful progress.
    with execution._db_conn() as conn:
        execution._guard(conn, run)
        conn.execute('UPDATE document_actions SET phase=%s,updated_at=clock_timestamp() WHERE id=%s::uuid',
            (value['phase'], run.action['id']))


def persist(run, request, result):
    """Commit exact validated bytes before worker release; no network in SQL."""
    if type(request) is not c.RenderRequest or type(result) is not c.ValidatedResult:
        c.fail()
    r, m = request.data, result.manifest
    if (r['job_id'] != run.token.turn_id or r['revision_id'] != run.action['revision_id']
            or r['canonical_sha256'] != run.revision['canonical_sha256']
            or any(m[key] != r[key] for key in ('job_id', 'revision_id', 'canonical_sha256', 'request_sha256'))):
        c.fail()
    with execution._db_conn() as conn:
        execution._guard(conn, run)
        conn.execute('''INSERT INTO document_renderer_snapshots
            (action_id,revision_id,confirmation_turn_id,canonical_sha256,request_sha256,manifest,docx,pdf)
            VALUES (%s::uuid,%s::uuid,%s::uuid,%s,%s,%s,%s,%s)''',
            (run.action['id'], r['revision_id'], r['job_id'], r['canonical_sha256'], request.identity,
             result.manifest_bytes, result.docx, result.pdf))


def available(conn):
    """Effective M9-A schema, read-only; Markdown never needs this capability."""
    required = {
        'document_actions_format_check', 'document_receipts_format_check',
        'document_revision_renders_format_check', 'document_revision_renders_serializer_version_check',
        'document_execution_journal_serializer_version_check',
    }
    rows = conn.execute('''SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint
        WHERE convalidated AND conrelid IN ('document_actions'::regclass,'document_receipts'::regclass,
        'document_revision_renders'::regclass,'document_execution_journal'::regclass)
        AND conname=ANY(%s)''', (list(required),)).fetchall()
    definitions = dict(rows)
    return (set(definitions) == required and all("'docx'" in definitions[k] for k in required if 'journal' not in k)
        and "'frida_writer_v1'" in definitions['document_execution_journal_serializer_version_check']
        and "'frida_writer_v1'" in definitions['document_revision_renders_serializer_version_check']
        and bool(conn.execute('''SELECT 1 FROM pg_trigger WHERE
            tgrelid=to_regclass('document_renderer_snapshots') AND tgname='document_execution_immutable'
            AND tgenabled IN ('O','A')''').fetchone()))


def content(conn, action, revision):
    """Read the immutable, already validated pair. A snapshot grants no publication.

    Only the executor's successful session release reaches journal/publication;
    historical provenance additionally requires the durable render and receipt.
    """
    row = conn.execute('''SELECT revision_id::text,confirmation_turn_id::text,canonical_sha256,
        request_sha256,manifest,docx,pdf FROM document_renderer_snapshots WHERE action_id=%s::uuid''',
        (action['id'],)).fetchone()
    if not row or row[:3] != (str(action['revision_id']),str(action['confirmation_turn_id']),revision['canonical_sha256']):
        raise c.DocumentWorkshopError('document_revision_invalid')
    manifest = c.read_json(row[4])
    if (manifest['job_id'] != row[1] or manifest['revision_id'] != row[0]
            or manifest['canonical_sha256'] != row[2] or manifest['request_sha256'] != row[3]
            or manifest['status'] != 'ready'):
        raise c.DocumentWorkshopError('document_revision_invalid')
    for fmt, body in (('docx',row[5]),('pdf',row[6])):
        artifact = manifest['artifacts'][fmt]
        if artifact['sha256'] != c.digest(body) or artifact['byte_size'] != len(body):
            raise c.DocumentWorkshopError('document_revision_invalid')
    return row[5]
