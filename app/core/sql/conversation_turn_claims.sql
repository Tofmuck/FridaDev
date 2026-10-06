-- M3 only. Explicit migration, never applied by import or server bootstrap.
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS turn_generation BIGINT NOT NULL DEFAULT 0;
ALTER TABLE document_workshop_contexts DROP CONSTRAINT IF EXISTS document_workshop_contexts_state_check;
ALTER TABLE document_workshop_contexts ADD CONSTRAINT document_workshop_contexts_state_check
    CHECK (state IN ('editing', 'cancelled', 'invalidated'));

CREATE TABLE IF NOT EXISTS conversation_turn_claims (
    turn_id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    owner_id UUID NOT NULL,
    generation BIGINT NOT NULL CHECK (generation > 0),
    kind TEXT NOT NULL CHECK (kind IN ('chat', 'preparation', 'confirmation')),
    request_fingerprint TEXT NOT NULL CHECK (request_fingerprint ~ '^[0-9a-f]{64}$'),
    context_id UUID REFERENCES document_workshop_contexts(id) ON DELETE CASCADE,
    expected_etag TEXT,
    state TEXT NOT NULL DEFAULT 'active' CHECK (state IN
        ('active', 'succeeded', 'interrupted', 'failed', 'cancelled', 'invalidated', 'lost')),
    outcome TEXT CHECK (outcome IN ('succeeded', 'interrupted')),
    reason_code TEXT CHECK (reason_code IN ('document_inactivity')),
    lease_until TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ,
    UNIQUE (conversation_id, generation),
    CHECK ((kind = 'chat' AND context_id IS NULL AND expected_etag IS NULL)
        OR (kind <> 'chat' AND context_id IS NOT NULL)),
    CHECK (reason_code IS NULL OR (kind <> 'chat' AND state = 'failed'))
);
CREATE UNIQUE INDEX IF NOT EXISTS conversation_turn_claims_one_active
    ON conversation_turn_claims(conversation_id) WHERE state = 'active';

-- Scope changes are irreversible, including A -> B -> A. Trigger writes share
-- the resource mutation transaction. No wall-clock expiry on a context/proposal.
CREATE OR REPLACE FUNCTION document_workshop_invalidate_scope() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'conversations' THEN
        IF NEW.workspace_folder_id IS DISTINCT FROM OLD.workspace_folder_id
           OR NEW.deleted_at IS DISTINCT FROM OLD.deleted_at THEN
            UPDATE document_workshop_contexts SET state='invalidated'
                WHERE conversation_id=NEW.id AND state='editing';
            IF NEW.deleted_at IS NOT NULL THEN
                UPDATE conversation_turn_claims SET state='invalidated', finished_at=clock_timestamp()
                    WHERE conversation_id=NEW.id AND state='active';
            END IF;
        END IF;
    ELSIF TG_TABLE_NAME = 'workspace_folders' THEN
        IF (NEW.deleted_at, to_jsonb(NEW)->'display_name')
            IS DISTINCT FROM (OLD.deleted_at, to_jsonb(OLD)->'display_name') THEN
            UPDATE document_workshop_contexts SET state='invalidated'
                WHERE workspace_folder_id=NEW.id AND state='editing';
        END IF;
    ELSIF TG_TABLE_NAME = 'workspace_files' THEN
        IF (NEW.workspace_folder_id, NEW.status, NEW.content_kind, NEW.media_kind,
            NEW.source_extension, NEW.deleted_at, to_jsonb(NEW)->'sha256', to_jsonb(NEW)->'byte_size')
            IS DISTINCT FROM (OLD.workspace_folder_id, OLD.status, OLD.content_kind, OLD.media_kind,
            OLD.source_extension, OLD.deleted_at, to_jsonb(OLD)->'sha256', to_jsonb(OLD)->'byte_size') THEN
            UPDATE document_workshop_contexts SET state='invalidated'
                WHERE target_file_id=NEW.id AND state='editing';
        END IF;
    ELSIF TG_TABLE_NAME = 'workspace_folder_nextcloud_links' THEN
        IF (NEW.nextcloud_sync_state, NEW.nextcloud_folder_ref, NEW.nextcloud_name_hash)
            IS DISTINCT FROM (OLD.nextcloud_sync_state, OLD.nextcloud_folder_ref, OLD.nextcloud_name_hash) THEN
            UPDATE document_workshop_contexts SET state='invalidated'
                WHERE workspace_folder_id=NEW.workspace_folder_id AND state='editing';
        END IF;
    ELSIF TG_TABLE_NAME = 'workspace_file_nextcloud_links' THEN
        IF (to_jsonb(NEW) - ARRAY['updated_at','last_sync_at','last_sync_operation','last_sync_reason_code','observed_at'])
            IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['updated_at','last_sync_at','last_sync_operation','last_sync_reason_code','observed_at']) THEN
            UPDATE document_workshop_contexts SET state='invalidated'
                WHERE target_file_id=NEW.workspace_file_id AND state='editing';
        END IF;
    END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION document_workshop_context_authority() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP='INSERT' THEN
        UPDATE document_workshop_contexts SET state='invalidated'
            WHERE conversation_id=NEW.conversation_id AND state='editing'
              AND (workspace_folder_id, target_file_id, target_relative_path, target_document_ref, target_remote_identity)
                  IS DISTINCT FROM (NEW.workspace_folder_id, NEW.target_file_id, NEW.target_relative_path,
                                    NEW.target_document_ref, NEW.target_remote_identity);
    ELSIF (NEW.id, NEW.conversation_id, NEW.workspace_folder_id, NEW.target_file_id,
           NEW.target_relative_path, NEW.target_document_ref, NEW.target_remote_identity, NEW.created_at)
        IS DISTINCT FROM (OLD.id, OLD.conversation_id, OLD.workspace_folder_id, OLD.target_file_id,
           OLD.target_relative_path, OLD.target_document_ref, OLD.target_remote_identity, OLD.created_at) THEN
        RAISE EXCEPTION 'document_context_identity_immutable';
    ELSIF NEW.state IS DISTINCT FROM OLD.state THEN
        IF OLD.state <> 'editing' THEN
            RAISE EXCEPTION 'document_context_authority_closed';
        END IF;
        UPDATE conversation_turn_claims SET state=NEW.state, finished_at=clock_timestamp()
            WHERE context_id=NEW.id AND state='active';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS workshop_scope_change ON conversations;
CREATE TRIGGER workshop_scope_change AFTER UPDATE ON conversations FOR EACH ROW
    EXECUTE FUNCTION document_workshop_invalidate_scope();
DROP TRIGGER IF EXISTS workshop_scope_change ON workspace_folders;
CREATE TRIGGER workshop_scope_change AFTER UPDATE ON workspace_folders FOR EACH ROW
    EXECUTE FUNCTION document_workshop_invalidate_scope();
DROP TRIGGER IF EXISTS workshop_scope_change ON workspace_files;
CREATE TRIGGER workshop_scope_change AFTER UPDATE ON workspace_files FOR EACH ROW
    EXECUTE FUNCTION document_workshop_invalidate_scope();
DROP TRIGGER IF EXISTS workshop_scope_change ON workspace_file_nextcloud_links;
CREATE TRIGGER workshop_scope_change AFTER UPDATE ON workspace_file_nextcloud_links FOR EACH ROW
    EXECUTE FUNCTION document_workshop_invalidate_scope();
DROP TRIGGER IF EXISTS workshop_scope_change ON workspace_folder_nextcloud_links;
CREATE TRIGGER workshop_scope_change AFTER UPDATE ON workspace_folder_nextcloud_links FOR EACH ROW
    EXECUTE FUNCTION document_workshop_invalidate_scope();
DROP TRIGGER IF EXISTS workshop_context_authority ON document_workshop_contexts;
CREATE TRIGGER workshop_context_authority BEFORE INSERT OR UPDATE ON document_workshop_contexts
    FOR EACH ROW EXECUTE FUNCTION document_workshop_context_authority();
