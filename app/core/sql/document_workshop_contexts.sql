-- M1 context migration: idempotent, no document content or future action tables.
CREATE TABLE IF NOT EXISTS document_workshop_contexts (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    workspace_folder_id UUID NOT NULL REFERENCES workspace_folders(id) ON DELETE CASCADE,
    target_file_id UUID REFERENCES workspace_files(id) ON DELETE CASCADE,
    target_relative_path TEXT,
    target_document_ref TEXT,
    state TEXT NOT NULL DEFAULT 'editing' CHECK (state = 'editing'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((target_file_id IS NULL AND target_relative_path IS NULL AND target_document_ref IS NULL)
        OR (target_file_id IS NOT NULL AND target_relative_path IS NOT NULL AND target_document_ref IS NOT NULL))
);
