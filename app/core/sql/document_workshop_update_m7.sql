-- M7 explicit migration AFTER M1/M2/M3/M4/M5. Never apply at startup/GET.
ALTER TABLE document_actions ADD COLUMN IF NOT EXISTS target_version JSONB;
ALTER TABLE document_actions DROP CONSTRAINT IF EXISTS document_actions_operation_check;
ALTER TABLE document_actions ADD CONSTRAINT document_actions_operation_check CHECK (operation IN ('create','copy','update'));
ALTER TABLE document_actions DROP CONSTRAINT IF EXISTS document_actions_state_check;
ALTER TABLE document_actions ADD CONSTRAINT document_actions_state_check CHECK (state IN
 ('preparing','pending','executing','succeeded','remote_uncertain','conflict','clarify','refuse','failed',
  'cancelled','invalidated','superseded','interrupted','lost'));
ALTER TABLE document_actions DROP CONSTRAINT IF EXISTS document_update_target_shape;
ALTER TABLE document_actions ADD CONSTRAINT document_update_target_shape CHECK
 ((operation IS DISTINCT FROM 'update' AND target_version IS NULL) OR
  (operation='update' AND target_version IS NOT NULL AND jsonb_typeof(target_version)='object' AND
   target_version ?& ARRAY['workspace_file_id','workspace_folder_id','relative_path','remote_identity','etag','sha256',
    'scope_key','remote_file_id','document_ref','creation_author','document_origin','source_kind','base_revision_id','created_at','name','byte_size','observed_at',
    'mime_type','nextcloud_target_name','nextcloud_name_hash']));
ALTER TABLE document_receipts DROP CONSTRAINT IF EXISTS document_receipts_operation_check;
ALTER TABLE document_receipts ADD CONSTRAINT document_receipts_operation_check CHECK (operation IN ('create','copy','update'));
ALTER TABLE document_receipts DROP CONSTRAINT IF EXISTS document_receipts_creation_author_check;
ALTER TABLE document_receipts ADD CONSTRAINT document_receipts_creation_author_check CHECK
 (creation_author='frida' OR (operation='update' AND creation_author='external'));
CREATE UNIQUE INDEX IF NOT EXISTS document_artifacts_file_identity ON document_artifacts(workspace_file_id)
 WHERE workspace_file_id IS NOT NULL;
ALTER TABLE document_execution_journal DROP CONSTRAINT IF EXISTS document_execution_journal_event_check;
ALTER TABLE document_execution_journal ADD CONSTRAINT document_execution_journal_event_check CHECK (event IN
 ('intent','mkcol_intent','put_intent','delete_intent','remote_outcome','compensation_outcome','publication_unknown',
  'metadata_reconciliation','metadata_published'));

CREATE OR REPLACE FUNCTION document_update_target_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.revision_id IS NOT NULL AND NEW.target_version IS DISTINCT FROM OLD.target_version THEN
  RAISE EXCEPTION 'document_update_target_immutable';
 END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS document_update_target_immutable ON document_actions;
CREATE TRIGGER document_update_target_immutable BEFORE UPDATE ON document_actions FOR EACH ROW
 EXECUTE FUNCTION document_update_target_immutable();

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
  -- Sole terminal repair: proven metadata publication with a NEW succeeded M3
  -- owner. No old-owner rearm, pending transition or remote mutation permission.
  IF NOT (OLD.state='remote_uncertain' AND NEW.state='succeeded' AND OLD.operation='update' AND EXISTS (
   SELECT 1 FROM document_execution_journal j JOIN conversation_turn_claims c ON c.turn_id=j.confirmation_turn_id
   JOIN document_receipts r ON r.action_id=OLD.id JOIN document_revision_renders v ON v.revision_id=r.revision_id
   WHERE j.action_id=OLD.id AND j.event='metadata_published' AND c.turn_id<>OLD.confirmation_turn_id
    AND c.state='succeeded' AND c.outcome='succeeded' AND c.owner_id=j.owner_id AND c.generation=j.generation
    AND c.conversation_id=OLD.conversation_id AND c.context_id=OLD.context_id AND c.kind='confirmation'
    AND r.revision_id=OLD.revision_id AND v.content_sha256=j.content_sha256)) THEN
   RAISE EXCEPTION 'document_action_closed';
  END IF;
 END IF;
 IF NEW.state IN ('executing','succeeded','remote_uncertain') AND NEW.confirmation_turn_id IS NULL THEN
  RAISE EXCEPTION 'document_confirmation_required';
 END IF;
 RETURN NEW;
END $$;
