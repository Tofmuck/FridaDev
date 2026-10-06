-- M5 explicit migration, never applied by import, startup or a request.
ALTER TABLE document_actions DROP CONSTRAINT IF EXISTS document_actions_state_check;
ALTER TABLE document_actions ADD CONSTRAINT document_actions_state_check CHECK (state IN
 ('preparing','pending','executing','succeeded','remote_uncertain','clarify','refuse','failed',
  'cancelled','invalidated','superseded','interrupted','lost'));
ALTER TABLE document_actions ADD COLUMN IF NOT EXISTS confirmation_turn_id UUID UNIQUE REFERENCES conversation_turn_claims(turn_id),
 ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ,
 ADD COLUMN IF NOT EXISTS created_collections_count INTEGER CHECK (created_collections_count>=0),
 ADD COLUMN IF NOT EXISTS workspace_file_id UUID;
ALTER TABLE document_artifacts ADD COLUMN IF NOT EXISTS workspace_file_id UUID REFERENCES workspace_files(id) ON DELETE SET NULL,
 ADD COLUMN IF NOT EXISTS current_revision_id UUID REFERENCES document_revisions(id);

CREATE TABLE IF NOT EXISTS document_revision_renders (
 revision_id UUID PRIMARY KEY REFERENCES document_revisions(id) ON DELETE CASCADE,
 format TEXT NOT NULL CHECK (format='markdown'),
 serializer_version TEXT NOT NULL CHECK (serializer_version='frida_markdown_v1'),
 content_sha256 TEXT NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
 byte_size BIGINT NOT NULL CHECK (byte_size BETWEEN 1 AND 16777216),
 storage_key TEXT NOT NULL UNIQUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS document_receipts (
 id UUID PRIMARY KEY,
 action_id UUID NOT NULL UNIQUE REFERENCES document_actions(id) ON DELETE CASCADE,
 confirmation_turn_id UUID NOT NULL UNIQUE REFERENCES conversation_turn_claims(turn_id),
 request_turn_id UUID NOT NULL REFERENCES conversation_turn_claims(turn_id),
 conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
 workspace_folder_id UUID NOT NULL REFERENCES workspace_folders(id) ON DELETE CASCADE,
 artifact_id UUID NOT NULL REFERENCES document_artifacts(id),
 revision_id UUID NOT NULL REFERENCES document_revisions(id),
 workspace_file_id UUID NOT NULL,
 operation TEXT NOT NULL CHECK (operation IN ('create','copy')),
 format TEXT NOT NULL CHECK (format='markdown'),
 relative_path TEXT NOT NULL,
 creation_author TEXT NOT NULL CHECK (creation_author='frida'),
 revision_author TEXT NOT NULL CHECK (revision_author='frida'),
 canonical_sha256 TEXT NOT NULL CHECK (canonical_sha256 ~ '^[0-9a-f]{64}$'),
 content_sha256 TEXT NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
 nextcloud_scope_key TEXT NOT NULL CHECK (nextcloud_scope_key ~ '^[0-9a-f]{64}$'),
 nextcloud_file_id TEXT NOT NULL CHECK (nextcloud_file_id ~ '^[1-9][0-9]{0,63}$'),
 nextcloud_etag TEXT NOT NULL,
 confirmed_at TIMESTAMPTZ NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS document_execution_journal (
 id UUID PRIMARY KEY,
 action_id UUID NOT NULL REFERENCES document_actions(id) ON DELETE CASCADE,
 confirmation_turn_id UUID NOT NULL REFERENCES conversation_turn_claims(turn_id),
 owner_id UUID NOT NULL,
 generation BIGINT NOT NULL,
 event TEXT NOT NULL CHECK (event IN ('intent','mkcol_intent','put_intent','delete_intent','remote_outcome','compensation_outcome','publication_unknown')),
 path_sha256 TEXT CHECK (path_sha256 ~ '^[0-9a-f]{64}$'),
 canonical_sha256 TEXT NOT NULL CHECK (canonical_sha256 ~ '^[0-9a-f]{64}$'),
 content_sha256 TEXT NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
 serializer_version TEXT NOT NULL CHECK (serializer_version='frida_markdown_v1'),
 state TEXT CHECK (state IN ('known_success','known_failure','remote_uncertain','absence_certain','preserved')),
 reason_code TEXT,
 http_status INTEGER,
 etag TEXT,
 created_collections_count INTEGER CHECK (created_collections_count>=0),
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS document_execution_journal_action ON document_execution_journal(action_id,created_at);
CREATE OR REPLACE FUNCTION document_execution_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'document_execution_immutable'; END $$;
DROP TRIGGER IF EXISTS document_execution_immutable ON document_receipts;
CREATE TRIGGER document_execution_immutable BEFORE UPDATE ON document_receipts FOR EACH ROW EXECUTE FUNCTION document_execution_immutable();
DROP TRIGGER IF EXISTS document_execution_immutable ON document_revision_renders;
CREATE TRIGGER document_execution_immutable BEFORE UPDATE ON document_revision_renders FOR EACH ROW EXECUTE FUNCTION document_execution_immutable();
DROP TRIGGER IF EXISTS document_execution_immutable ON document_execution_journal;
CREATE TRIGGER document_execution_immutable BEFORE UPDATE ON document_execution_journal FOR EACH ROW EXECUTE FUNCTION document_execution_immutable();

CREATE OR REPLACE FUNCTION document_action_identity_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (NEW.id,NEW.context_id,NEW.conversation_id,NEW.workspace_folder_id,NEW.source_file_ids,NEW.created_at)
 IS DISTINCT FROM (OLD.id,OLD.context_id,OLD.conversation_id,OLD.workspace_folder_id,OLD.source_file_ids,OLD.created_at)
 OR (OLD.revision_id IS NOT NULL AND
  (NEW.revision_id,NEW.artifact_id,NEW.operation,NEW.format,NEW.relative_path,NEW.source_versions,NEW.limitations)
  IS DISTINCT FROM (OLD.revision_id,OLD.artifact_id,OLD.operation,OLD.format,OLD.relative_path,OLD.source_versions,OLD.limitations))
 OR (OLD.confirmation_turn_id IS NOT NULL AND
  (NEW.confirmation_turn_id,NEW.confirmed_at) IS DISTINCT FROM (OLD.confirmation_turn_id,OLD.confirmed_at)) THEN
  RAISE EXCEPTION 'document_action_identity_immutable';
 END IF;
 IF OLD.state NOT IN ('preparing','pending','executing') AND NEW.state IS DISTINCT FROM OLD.state THEN
  RAISE EXCEPTION 'document_action_closed';
 END IF;
 IF NEW.state IN ('executing','succeeded','remote_uncertain') AND NEW.confirmation_turn_id IS NULL THEN
  RAISE EXCEPTION 'document_confirmation_required';
 END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION document_actions_context_closed() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.state IN ('cancelled','invalidated') AND NEW.state IS DISTINCT FROM OLD.state THEN
  UPDATE document_actions SET state=NEW.state,reason_code='document_context_closed',updated_at=clock_timestamp()
   WHERE context_id=NEW.id AND state IN ('preparing','pending');
  UPDATE document_actions SET state=CASE WHEN EXISTS (SELECT 1 FROM document_execution_journal j WHERE j.action_id=document_actions.id)
   THEN 'remote_uncertain' ELSE NEW.state END,reason_code='document_context_closed',updated_at=clock_timestamp()
   WHERE context_id=NEW.id AND state='executing';
 END IF;
 RETURN NEW;
END $$;

-- The source invalidation function remains M4's function. Only its action
-- selection grows to include an execution before its final publication.
CREATE OR REPLACE FUNCTION document_actions_source_changed() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE source_id UUID; changed BOOLEAN;
BEGIN
 IF TG_TABLE_NAME='workspace_files' THEN
  source_id=OLD.id;
  IF TG_OP='DELETE' THEN changed=TRUE;
  ELSE changed=(NEW.workspace_folder_id,NEW.status,NEW.content_kind,NEW.media_kind,NEW.source_extension,NEW.deleted_at,
   to_jsonb(NEW)->'sha256',to_jsonb(NEW)->'byte_size') IS DISTINCT FROM
   (OLD.workspace_folder_id,OLD.status,OLD.content_kind,OLD.media_kind,OLD.source_extension,OLD.deleted_at,
   to_jsonb(OLD)->'sha256',to_jsonb(OLD)->'byte_size'); END IF;
 ELSE
  source_id=OLD.workspace_file_id;
  IF TG_OP='DELETE' THEN changed=TRUE;
  ELSE changed=(to_jsonb(NEW)-ARRAY['updated_at','last_sync_at','last_sync_operation','last_sync_reason_code','observed_at'])
   IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['updated_at','last_sync_at','last_sync_operation','last_sync_reason_code','observed_at']); END IF;
 END IF;
 IF changed THEN
  UPDATE document_workshop_contexts SET state='invalidated' WHERE state='editing' AND id IN
   (SELECT context_id FROM document_actions WHERE state IN ('preparing','pending','executing') AND source_file_ids ? source_id::text);
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$;
