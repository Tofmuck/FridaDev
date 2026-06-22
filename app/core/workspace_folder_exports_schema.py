from __future__ import annotations

"""Database schema setup for the Exports V1 read-model."""

from typing import Any


def ensure_schema(cur: Any) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_folder_exports (
            id                       UUID PRIMARY KEY,
            workspace_folder_id      UUID        NOT NULL REFERENCES workspace_folders(id) ON DELETE CASCADE,
            title                    TEXT        NOT NULL DEFAULT '',
            title_hash               TEXT        NOT NULL DEFAULT '',
            target_name              TEXT        NOT NULL DEFAULT '',
            export_format            TEXT        NOT NULL DEFAULT 'md',
            source_kind              TEXT        NOT NULL DEFAULT 'conversation',
            source_ref               TEXT        NOT NULL DEFAULT '',
            source_hash              TEXT        NOT NULL DEFAULT '',
            content_hash             TEXT        NOT NULL DEFAULT '',
            local_state              TEXT        NOT NULL DEFAULT 'available',
            nextcloud_sync_state     TEXT        NOT NULL DEFAULT 'sync_error',
            remote_export_ref        TEXT        NOT NULL DEFAULT '',
            etag_value               TEXT        NOT NULL DEFAULT '',
            etag_hash                TEXT        NOT NULL DEFAULT '',
            byte_size                BIGINT      NOT NULL DEFAULT 0,
            char_count               INTEGER     NOT NULL DEFAULT 0,
            reason_code              TEXT        NOT NULL DEFAULT '',
            created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at               TIMESTAMPTZ,
            CONSTRAINT workspace_folder_exports_local_state_chk
                CHECK (local_state IN ('available', 'sync_error', 'conflict', 'deleted', 'unavailable')),
            CONSTRAINT workspace_folder_exports_nextcloud_state_chk
                CHECK (nextcloud_sync_state IN ('linked', 'sync_error', 'deleted')),
            CONSTRAINT workspace_folder_exports_format_chk
                CHECK (export_format IN ('md', 'txt', 'docx', 'pdf')),
            CONSTRAINT workspace_folder_exports_source_kind_chk
                CHECK (source_kind IN ('conversation', 'message_selection', 'frida_response', 'note', 'document', 'export'))
        );
        """
    )
    for column_sql in (
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS workspace_folder_id UUID;",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS title TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS title_hash TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS target_name TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS export_format TEXT NOT NULL DEFAULT 'md';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS source_kind TEXT NOT NULL DEFAULT 'conversation';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS source_ref TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS source_hash TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS content_hash TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS local_state TEXT NOT NULL DEFAULT 'available';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS nextcloud_sync_state TEXT NOT NULL DEFAULT 'sync_error';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS remote_export_ref TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS etag_value TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS etag_hash TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS byte_size BIGINT NOT NULL DEFAULT 0;",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS char_count INTEGER NOT NULL DEFAULT 0;",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS reason_code TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;",
    ):
        cur.execute(column_sql)
    cur.execute(
        """
        ALTER TABLE workspace_folder_exports
        ALTER COLUMN nextcloud_sync_state SET DEFAULT 'sync_error';
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS workspace_folder_exports_folder_active_idx
        ON workspace_folder_exports (workspace_folder_id, deleted_at, updated_at DESC);
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS workspace_folder_exports_folder_title_format_active_idx
        ON workspace_folder_exports (workspace_folder_id, title_hash, export_format)
        WHERE deleted_at IS NULL;
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS workspace_folder_exports_state_idx
        ON workspace_folder_exports (local_state, nextcloud_sync_state, deleted_at);
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS workspace_folder_exports_source_idx
        ON workspace_folder_exports (workspace_folder_id, source_kind, source_hash);
        """
    )
