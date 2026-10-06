"""M3 conversation authority. SQL transactions only; no provider or task runner."""
from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
import config
from admin import runtime_settings
from . import runtime_db_bootstrap

LEASE_SECONDS = 90
RENEW_SECONDS = 15
_SCHEMA = Path(__file__).with_name('sql') / 'conversation_turn_claims.sql'


class ClaimError(RuntimeError):
    def __init__(self, reason_code, status=409):
        self.reason_code, self.status = reason_code, status
        super().__init__(reason_code)


@dataclass(frozen=True, repr=False)
class TurnClaim:
    turn_id: str
    conversation_id: str
    owner_id: str
    generation: int
    context_id: str | None = None


@dataclass(frozen=True, repr=False)
class ClaimAdmission:
    token: TurnClaim | None
    record: dict


def _db_conn():
    return runtime_db_bootstrap.connect_runtime_database(psycopg, config, runtime_settings)


def init_db():
    with _db_conn() as conn:
        conn.execute(_SCHEMA.read_text(encoding='utf-8'))
    return True


def _record(row):
    if not row:
        return None
    return {k: (v.isoformat() if hasattr(v, 'isoformat') else str(v) if isinstance(v, UUID) else v)
            for k, v in row.items()}


def _conversation(conn, conversation_id, *, active=True):
    conn.execute("SET LOCAL statement_timeout='5s'")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute('SELECT * FROM conversations WHERE id=%s::uuid FOR UPDATE', (conversation_id,))
        row = cur.fetchone()
    if not row or (active and row['deleted_at'] is not None):
        raise ClaimError('conversation_turn_invalidated')
    return row


def _expire(conn, conversation_id):
    # Resource mutations may already own a document claim and then update its
    # conversation. Do not wait downstream while holding the conversation.
    conn.execute("SELECT turn_id FROM conversation_turn_claims WHERE conversation_id=%s::uuid AND state='active' FOR UPDATE NOWAIT", (conversation_id,)).fetchall()
    conn.execute("""UPDATE conversation_turn_claims SET state='lost', finished_at=clock_timestamp()
        WHERE conversation_id=%s::uuid AND state='active' AND lease_until<=clock_timestamp()""", (conversation_id,))


def _read(conn, turn_id, *, lock=False):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute('SELECT * FROM conversation_turn_claims WHERE turn_id=%s::uuid' +
                    (' FOR UPDATE NOWAIT' if lock else ''), (turn_id,))
        return cur.fetchone()


def read(turn_id):
    try:
        with _db_conn() as conn:
            row = _read(conn, turn_id)
            if row:
                # Same lock order as acquisition/write/renewal. No lock on a
                # claim from a different conversation before its resource row.
                _conversation(conn, row['conversation_id'], active=False)
                _expire(conn, row['conversation_id'])
                row = _read(conn, turn_id)
            return _record(row)
    except psycopg.errors.LockNotAvailable:
        raise ClaimError('conversation_turn_conflict') from None
    except ClaimError:
        raise
    except Exception as exc:
        raise ClaimError('conversation_claim_unavailable', 503) from exc


def _scope(conn, conversation, context_id, expected_etag=None):
    if context_id is None:
        return
    # Read identity first, then lock resources before the context. Resource
    # triggers also acquire the context before its claims, never the reverse.
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute('SELECT * FROM document_workshop_contexts WHERE id=%s::uuid', (context_id,))
        ctx = cur.fetchone()
        if not ctx or str(ctx['conversation_id']) != str(conversation['id']):
            raise ClaimError('document_claim_scope_invalid')
        cur.execute('SELECT * FROM workspace_folders WHERE id=%s::uuid FOR SHARE NOWAIT', (ctx['workspace_folder_id'],))
        folder = cur.fetchone()
        if not folder or folder['deleted_at'] or conversation['workspace_folder_id'] != ctx['workspace_folder_id']:
            raise ClaimError('document_claim_scope_invalid')
        if ctx['target_file_id']:
            cur.execute('SELECT * FROM workspace_files WHERE id=%s::uuid FOR SHARE NOWAIT', (ctx['target_file_id'],))
            target = cur.fetchone()
            cur.execute('SELECT * FROM workspace_file_nextcloud_links WHERE workspace_file_id=%s::uuid FOR SHARE NOWAIT',
                        (ctx['target_file_id'],))
            link = cur.fetchone()
            path = (link or {}).get('nextcloud_relative_path') or 'Documents/' + str((link or {}).get('nextcloud_target_name') or '')
            identity = None
            if link and link.get('nextcloud_scope_key') and link.get('nextcloud_file_id'):
                identity = link['nextcloud_scope_key'] + ':' + link['nextcloud_file_id']
            if (not target or target['deleted_at'] or target['status'] != 'active'
                    or target['workspace_folder_id'] != ctx['workspace_folder_id']
                    or target['content_kind'] != 'document' or target['media_kind'] != 'text'
                    or target['source_extension'] not in ('.md', '.docx')
                    or not link or link['workspace_folder_id'] != ctx['workspace_folder_id']
                    or link['nextcloud_sync_state'] != 'linked'
                    or link['nextcloud_document_ref'] != ctx['target_document_ref']
                    or path != ctx['target_relative_path'] or identity != ctx['target_remote_identity']
                    or (expected_etag is not None and link.get('nextcloud_etag') != expected_etag)):
                raise ClaimError('document_claim_scope_invalid')
        elif expected_etag is not None:
            raise ClaimError('document_claim_scope_invalid')
        cur.execute('SELECT state FROM document_workshop_contexts WHERE id=%s::uuid FOR UPDATE NOWAIT', (context_id,))
        if cur.fetchone()['state'] != 'editing':
            raise ClaimError('document_claim_scope_invalid')


def acquire(*, conversation_id, turn_id, request_fingerprint, kind='chat', context_id=None, expected_etag=None):
    try:
        with _db_conn() as conn:
            conversation = _conversation(conn, conversation_id)
            _expire(conn, conversation_id)
            existing = _read(conn, turn_id)
            if existing:
                if (existing['request_fingerprint'] != request_fingerprint or existing['kind'] != kind
                        or str(existing['conversation_id']) != conversation_id
                        or (str(existing['context_id']) if existing['context_id'] else None) != context_id
                        or existing['expected_etag'] != expected_etag):
                    raise ClaimError('conversation_turn_id_incompatible')
                return ClaimAdmission(None, _record(existing))
            if kind not in ('chat', 'preparation', 'confirmation') or (kind == 'chat') != (context_id is None):
                raise ClaimError('conversation_claim_request_invalid', 400)
            _scope(conn, conversation, context_id, expected_etag)
            active = conn.execute("SELECT 1 FROM conversation_turn_claims WHERE conversation_id=%s::uuid AND state='active'",
                                  (conversation_id,)).fetchone()
            if active:
                raise ClaimError('conversation_turn_conflict')
            generation = conn.execute('UPDATE conversations SET turn_generation=turn_generation+1 WHERE id=%s::uuid RETURNING turn_generation',
                                      (conversation_id,)).fetchone()[0]
            owner_id = str(uuid4())
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("""INSERT INTO conversation_turn_claims
                    (turn_id,conversation_id,owner_id,generation,kind,request_fingerprint,context_id,expected_etag,lease_until)
                    VALUES (%s::uuid,%s::uuid,%s::uuid,%s,%s,%s,%s::uuid,%s,clock_timestamp()+%s*interval '1 second')
                    RETURNING *""", (turn_id,conversation_id,owner_id,generation,kind,request_fingerprint,context_id,expected_etag,LEASE_SECONDS))
                row = cur.fetchone()
            return ClaimAdmission(TurnClaim(turn_id,conversation_id,owner_id,generation,context_id), _record(row))
    except psycopg.errors.UniqueViolation:
        existing = read(turn_id)
        if (existing and existing['request_fingerprint'] == request_fingerprint and existing['kind'] == kind
                and existing['conversation_id'] == conversation_id and existing['context_id'] == context_id
                and existing['expected_etag'] == expected_etag):
            return ClaimAdmission(None, existing)
        raise ClaimError('conversation_turn_id_incompatible') from None
    except psycopg.errors.LockNotAvailable:
        raise ClaimError('conversation_turn_conflict') from None
    except ClaimError:
        raise
    except Exception as exc:
        raise ClaimError('conversation_claim_unavailable', 503) from exc


def check_in_transaction(conn, token, *, conversation_id, allow_outcome=False):
    """Fencing and scope locks MUST remain held through the caller's write."""
    if not isinstance(token, TurnClaim) or token.conversation_id != conversation_id:
        raise ClaimError('conversation_claim_token_invalid')
    conversation = _conversation(conn, conversation_id)
    row = _read(conn, token.turn_id)
    if not row:
        raise ClaimError('conversation_claim_lost')
    if (str(row['conversation_id']) != token.conversation_id
            or (str(row['context_id']) if row['context_id'] else None) != token.context_id):
        raise ClaimError('conversation_claim_token_invalid')
    _scope(conn, conversation, row['context_id'], row['expected_etag'])
    row = _read(conn, token.turn_id, lock=True)
    live = conn.execute('SELECT %s::timestamptz>clock_timestamp()', (row['lease_until'],)).fetchone()[0]
    if (row['state'] != 'active' or not live or str(row['owner_id']) != token.owner_id
            or row['generation'] != token.generation or conversation['turn_generation'] != token.generation
            or (row['outcome'] is not None and not allow_outcome)):
        raise ClaimError('conversation_claim_lost')
    return conversation, row


def record_outcome_in_transaction(conn, token, outcome):
    if outcome not in ('succeeded', 'interrupted'):
        raise ClaimError('conversation_claim_outcome_invalid')
    conn.execute('UPDATE conversation_turn_claims SET outcome=%s WHERE turn_id=%s::uuid', (outcome, token.turn_id))


@contextmanager
def fenced_connection(conn_factory, token, conversation_id):
    """For existing short SQL writers which already own their commit.

    Embedding/provider work must finish before entering this connection scope.
    No second connection and no check followed by an independent write.
    """
    with conn_factory() as conn:
        check_in_transaction(conn, token, conversation_id=conversation_id)
        yield conn


def _change(token, operation, state=None, reason_code=None):
    try:
        with _db_conn() as conn:
            _, row = check_in_transaction(conn, token, conversation_id=token.conversation_id, allow_outcome=True)
            if operation == 'renew':
                conn.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()+%s*interval '1 second' WHERE turn_id=%s::uuid",
                             (LEASE_SECONDS, token.turn_id))
            else:
                terminal = row['outcome'] or state or 'interrupted'
                if (terminal not in ('succeeded', 'interrupted', 'failed', 'cancelled')
                        or (state == 'succeeded' and row['outcome'] != 'succeeded')
                        or (terminal == 'succeeded' and row['outcome'] != 'succeeded')
                        or (reason_code is not None and (terminal != 'failed' or row['kind'] == 'chat'
                                                       or reason_code != 'document_inactivity'))):
                    raise ClaimError('conversation_claim_outcome_invalid')
                if terminal == 'cancelled' and row['context_id']:
                    conn.execute("UPDATE document_workshop_contexts SET state='cancelled' WHERE id=%s::uuid", (row['context_id'],))
                conn.execute('UPDATE conversation_turn_claims SET state=%s,reason_code=%s,finished_at=clock_timestamp() WHERE turn_id=%s::uuid',
                             (terminal, reason_code, token.turn_id))
    except psycopg.errors.LockNotAvailable:
        raise ClaimError('conversation_turn_conflict') from None
    except ClaimError:
        raise
    except Exception as exc:
        raise ClaimError('conversation_claim_unavailable', 503) from exc


def renew(token):
    _change(token, 'renew')


def finish(token, state=None, *, reason_code=None):
    _change(token, 'finish', state, reason_code)


def cancel(token):
    _change(token, 'finish', 'cancelled')
