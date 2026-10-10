-- M8-A explicit, additive internal snapshot only. Public formats stay closed.
-- BYTEA keeps the pair and manifest in the same atomic durable transaction.
CREATE TABLE IF NOT EXISTS document_renderer_snapshots (
 action_id UUID PRIMARY KEY REFERENCES document_actions(id) ON DELETE CASCADE,
 revision_id UUID NOT NULL REFERENCES document_revisions(id),
 confirmation_turn_id UUID NOT NULL UNIQUE REFERENCES conversation_turn_claims(turn_id),
 canonical_sha256 TEXT NOT NULL CHECK (canonical_sha256 ~ '^[0-9a-f]{64}$'),
 request_sha256 TEXT NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
 manifest BYTEA NOT NULL CHECK (octet_length(manifest) BETWEEN 1 AND 1048576),
 docx BYTEA NOT NULL CHECK (octet_length(docx) BETWEEN 1 AND 16777216),
 pdf BYTEA NOT NULL CHECK (octet_length(pdf) BETWEEN 1 AND 16777216),
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
DROP TRIGGER IF EXISTS document_execution_immutable ON document_renderer_snapshots;
CREATE TRIGGER document_execution_immutable BEFORE UPDATE ON document_renderer_snapshots
 FOR EACH ROW EXECUTE FUNCTION document_execution_immutable();
