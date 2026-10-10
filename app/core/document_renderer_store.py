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
