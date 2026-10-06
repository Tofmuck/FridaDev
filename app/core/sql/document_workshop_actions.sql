-- M4 explicit migration. No import/startup execution, receipt or remote mutation.
CREATE TABLE IF NOT EXISTS document_artifacts (
    id UUID PRIMARY KEY,
    workspace_folder_id UUID NOT NULL REFERENCES workspace_folders(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS document_revisions (
    id UUID PRIMARY KEY,
    artifact_id UUID NOT NULL REFERENCES document_artifacts(id) ON DELETE CASCADE,
    schema_version INTEGER NOT NULL CHECK (schema_version=1),
    canonical JSONB NOT NULL CHECK (jsonb_typeof(canonical)='object'),
    canonical_sha256 TEXT NOT NULL CHECK (canonical_sha256 ~ '^[0-9a-f]{64}$'),
    markdown_sha256 TEXT NOT NULL CHECK (markdown_sha256 ~ '^[0-9a-f]{64}$'),
    serializer_version TEXT NOT NULL CHECK (serializer_version='frida_markdown_v1'),
    word_count INTEGER NOT NULL CHECK (word_count BETWEEN 0 AND 10000),
    codepoint_count INTEGER NOT NULL CHECK (codepoint_count BETWEEN 1 AND 75000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS document_actions (
    id UUID PRIMARY KEY REFERENCES conversation_turn_claims(turn_id) ON DELETE CASCADE,
    context_id UUID NOT NULL REFERENCES document_workshop_contexts(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    workspace_folder_id UUID NOT NULL REFERENCES workspace_folders(id) ON DELETE CASCADE,
    state TEXT NOT NULL DEFAULT 'preparing' CHECK (state IN
        ('preparing','pending','clarify','refuse','failed','cancelled','invalidated','superseded','interrupted','lost')),
    phase TEXT NOT NULL DEFAULT 'preparing',
    received_content_codepoints BIGINT NOT NULL DEFAULT 0 CHECK (received_content_codepoints>=0),
    reason_code TEXT,
    source_file_ids JSONB NOT NULL CHECK (jsonb_typeof(source_file_ids)='array'),
    source_versions JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(source_versions)='array'),
    revision_id UUID UNIQUE REFERENCES document_revisions(id),
    artifact_id UUID REFERENCES document_artifacts(id),
    operation TEXT CHECK (operation IN ('create','copy')),
    format TEXT CHECK (format='markdown'),
    relative_path TEXT,
    limitations JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(limitations)='array'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK ((revision_id IS NULL AND artifact_id IS NULL AND operation IS NULL AND format IS NULL AND relative_path IS NULL)
        OR (revision_id IS NOT NULL AND artifact_id IS NOT NULL AND operation IS NOT NULL AND format IS NOT NULL AND relative_path IS NOT NULL)),
    CHECK (state<>'pending' OR revision_id IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS document_actions_context ON document_actions(context_id,created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS document_actions_one_pending_context ON document_actions(context_id) WHERE state='pending';
CREATE OR REPLACE FUNCTION document_revision_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'document_revision_immutable'; END $$;
DROP TRIGGER IF EXISTS document_revision_immutable ON document_revisions;
CREATE TRIGGER document_revision_immutable BEFORE UPDATE ON document_revisions FOR EACH ROW EXECUTE FUNCTION document_revision_immutable();

CREATE OR REPLACE FUNCTION document_action_identity_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.id,NEW.context_id,NEW.conversation_id,NEW.workspace_folder_id,NEW.source_file_ids,NEW.created_at)
        IS DISTINCT FROM (OLD.id,OLD.context_id,OLD.conversation_id,OLD.workspace_folder_id,OLD.source_file_ids,OLD.created_at)
       OR (OLD.revision_id IS NOT NULL AND
           (NEW.revision_id,NEW.artifact_id,NEW.operation,NEW.format,NEW.relative_path,NEW.source_versions,NEW.limitations)
            IS DISTINCT FROM (OLD.revision_id,OLD.artifact_id,OLD.operation,OLD.format,OLD.relative_path,OLD.source_versions,OLD.limitations)) THEN
        RAISE EXCEPTION 'document_action_identity_immutable';
    END IF;
    IF OLD.state NOT IN ('preparing','pending') AND NEW.state IS DISTINCT FROM OLD.state THEN
        RAISE EXCEPTION 'document_action_closed';
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS document_action_identity_immutable ON document_actions;
CREATE TRIGGER document_action_identity_immutable BEFORE UPDATE ON document_actions FOR EACH ROW EXECUTE FUNCTION document_action_identity_immutable();

CREATE OR REPLACE FUNCTION document_actions_context_closed() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.state IN ('cancelled','invalidated') AND NEW.state IS DISTINCT FROM OLD.state THEN
        UPDATE document_actions SET state=NEW.state,reason_code='document_context_closed',updated_at=clock_timestamp()
            WHERE context_id=NEW.id AND state IN ('preparing','pending');
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS document_actions_context_closed ON document_workshop_contexts;
CREATE TRIGGER document_actions_context_closed AFTER UPDATE ON document_workshop_contexts FOR EACH ROW EXECUTE FUNCTION document_actions_context_closed();

CREATE OR REPLACE FUNCTION document_actions_source_changed() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE source_id UUID; changed BOOLEAN;
BEGIN
    IF TG_TABLE_NAME='workspace_files' THEN
        source_id=OLD.id;
        IF TG_OP='DELETE' THEN changed=TRUE;
        ELSE changed=(NEW.workspace_folder_id,NEW.status,NEW.content_kind,NEW.media_kind,NEW.source_extension,NEW.deleted_at,
                to_jsonb(NEW)->'sha256',to_jsonb(NEW)->'byte_size')
            IS DISTINCT FROM (OLD.workspace_folder_id,OLD.status,OLD.content_kind,OLD.media_kind,OLD.source_extension,OLD.deleted_at,
                to_jsonb(OLD)->'sha256',to_jsonb(OLD)->'byte_size'); END IF;
    ELSE
        source_id=OLD.workspace_file_id;
        IF TG_OP='DELETE' THEN changed=TRUE;
        ELSE changed=(to_jsonb(NEW)-ARRAY['updated_at','last_sync_at','last_sync_operation','last_sync_reason_code','observed_at'])
            IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['updated_at','last_sync_at','last_sync_operation','last_sync_reason_code','observed_at']); END IF;
    END IF;
    IF changed THEN
        UPDATE document_workshop_contexts SET state='invalidated' WHERE state='editing' AND id IN
            (SELECT context_id FROM document_actions WHERE state IN ('preparing','pending') AND source_file_ids ? source_id::text);
    END IF;
    IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$;
DROP TRIGGER IF EXISTS document_actions_source_changed ON workspace_files;
CREATE TRIGGER document_actions_source_changed AFTER UPDATE OR DELETE ON workspace_files FOR EACH ROW EXECUTE FUNCTION document_actions_source_changed();
DROP TRIGGER IF EXISTS document_actions_source_changed ON workspace_file_nextcloud_links;
CREATE TRIGGER document_actions_source_changed AFTER UPDATE OR DELETE ON workspace_file_nextcloud_links FOR EACH ROW EXECUTE FUNCTION document_actions_source_changed();
