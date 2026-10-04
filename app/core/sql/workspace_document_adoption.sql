-- M2 explicit deployment migration. Never called by import/shared startup.
ALTER TABLE workspace_file_nextcloud_links
    ADD COLUMN IF NOT EXISTS nextcloud_relative_path TEXT,
    ADD COLUMN IF NOT EXISTS nextcloud_collision_key TEXT,
    ADD COLUMN IF NOT EXISTS nextcloud_file_id TEXT,
    ADD COLUMN IF NOT EXISTS nextcloud_scope_key TEXT,
    ADD COLUMN IF NOT EXISTS nextcloud_etag TEXT,
    ADD COLUMN IF NOT EXISTS observed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS observed_sha256 TEXT,
    ADD COLUMN IF NOT EXISTS document_origin TEXT;
ALTER TABLE document_workshop_contexts ADD COLUMN IF NOT EXISTS target_remote_identity TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS workspace_document_remote_identity_uidx
    ON workspace_file_nextcloud_links(workspace_folder_id, nextcloud_scope_key, nextcloud_file_id)
    WHERE nextcloud_file_id IS NOT NULL;
-- Identity uniqueness includes tombstones; the path index covers linked observations.
CREATE UNIQUE INDEX IF NOT EXISTS workspace_document_active_path_uidx
    ON workspace_file_nextcloud_links(workspace_folder_id, nextcloud_collision_key)
    WHERE nextcloud_collision_key IS NOT NULL AND nextcloud_sync_state='linked';
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='workspace_file_nextcloud_links'::regclass AND conname='workspace_document_identity_shape') THEN
        ALTER TABLE workspace_file_nextcloud_links ADD CONSTRAINT workspace_document_identity_shape CHECK (
            (nextcloud_file_id IS NULL AND nextcloud_scope_key IS NULL) OR
            (nextcloud_file_id IS NOT NULL AND nextcloud_file_id ~ '^[1-9][0-9]{0,63}$'
             AND nextcloud_scope_key IS NOT NULL AND nextcloud_scope_key ~ '^[0-9a-f]{64}$'));
    END IF;
END $$;
