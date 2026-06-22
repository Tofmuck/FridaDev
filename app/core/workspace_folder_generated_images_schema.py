from __future__ import annotations

"""Database schema setup for the Generated Images V1 read-model."""

from typing import Any


def ensure_schema(cur: Any) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_folder_generated_images (
            id                       UUID PRIMARY KEY,
            workspace_folder_id      UUID        NOT NULL REFERENCES workspace_folders(id) ON DELETE CASCADE,
            display_name             TEXT        NOT NULL DEFAULT '',
            display_name_hash        TEXT        NOT NULL DEFAULT '',
            target_name_internal     TEXT        NOT NULL DEFAULT '',
            target_ref               TEXT        NOT NULL DEFAULT '',
            mime_type                TEXT        NOT NULL DEFAULT '',
            image_format             TEXT        NOT NULL DEFAULT 'png',
            byte_size                BIGINT      NOT NULL DEFAULT 0,
            width                    INTEGER     NOT NULL DEFAULT 0,
            height                   INTEGER     NOT NULL DEFAULT 0,
            content_hash             TEXT        NOT NULL DEFAULT '',
            content_hash_short       TEXT        NOT NULL DEFAULT '',
            generator_key            TEXT        NOT NULL DEFAULT '',
            provider_model           TEXT        NOT NULL DEFAULT '',
            aspect_ratio             TEXT        NOT NULL DEFAULT '',
            image_size               TEXT        NOT NULL DEFAULT '',
            prompt_present           BOOLEAN     NOT NULL DEFAULT FALSE,
            prompt_length_bucket     TEXT        NOT NULL DEFAULT '',
            local_state              TEXT        NOT NULL DEFAULT 'available',
            nextcloud_sync_state     TEXT        NOT NULL DEFAULT 'sync_error',
            etag_value               TEXT        NOT NULL DEFAULT '',
            etag_hash                TEXT        NOT NULL DEFAULT '',
            last_reason_code         TEXT        NOT NULL DEFAULT '',
            created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at               TIMESTAMPTZ,
            CONSTRAINT workspace_folder_generated_images_local_state_chk
                CHECK (local_state IN ('available', 'sync_error', 'conflict', 'deleted', 'unavailable')),
            CONSTRAINT workspace_folder_generated_images_nextcloud_state_chk
                CHECK (nextcloud_sync_state IN ('linked', 'sync_error', 'conflict', 'deleted', 'unavailable')),
            CONSTRAINT workspace_folder_generated_images_format_chk
                CHECK (image_format IN ('png', 'jpeg', 'webp')),
            CONSTRAINT workspace_folder_generated_images_prompt_bucket_chk
                CHECK (prompt_length_bucket IN ('', 'chars_001_to_250', 'chars_251_to_500', 'chars_501_to_1000', 'chars_1001_to_1500', 'chars_1501_to_2000')),
            CONSTRAINT workspace_folder_generated_images_target_name_chk
                CHECK (target_name_internal ~ '^generated-image-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\.(png|jpg|webp)$'),
            CONSTRAINT workspace_folder_generated_images_target_ref_chk
                CHECK (target_ref ~ '^generated-image-target:[0-9a-f]{12}$'),
            CONSTRAINT workspace_folder_generated_images_size_chk
                CHECK (byte_size >= 0 AND width >= 0 AND height >= 0)
        );
        """
    )
    for column_sql in (
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS workspace_folder_id UUID;",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS display_name TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS display_name_hash TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS target_name_internal TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS target_ref TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS mime_type TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS image_format TEXT NOT NULL DEFAULT 'png';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS byte_size BIGINT NOT NULL DEFAULT 0;",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS width INTEGER NOT NULL DEFAULT 0;",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS height INTEGER NOT NULL DEFAULT 0;",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS content_hash TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS content_hash_short TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS generator_key TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS provider_model TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS aspect_ratio TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS image_size TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS prompt_present BOOLEAN NOT NULL DEFAULT FALSE;",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS prompt_length_bucket TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS local_state TEXT NOT NULL DEFAULT 'available';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS nextcloud_sync_state TEXT NOT NULL DEFAULT 'sync_error';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS etag_value TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS etag_hash TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS last_reason_code TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();",
        "ALTER TABLE workspace_folder_generated_images ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;",
    ):
        cur.execute(column_sql)
    cur.execute(
        """
        ALTER TABLE workspace_folder_generated_images
        ALTER COLUMN nextcloud_sync_state SET DEFAULT 'sync_error';
        """
    )
    cur.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'workspace_folder_generated_images_target_name_chk'
            ) THEN
                ALTER TABLE workspace_folder_generated_images
                ADD CONSTRAINT workspace_folder_generated_images_target_name_chk
                CHECK (target_name_internal ~ '^generated-image-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\.(png|jpg|webp)$');
            END IF;
        END
        $$;
        """
    )
    cur.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'workspace_folder_generated_images_target_ref_chk'
            ) THEN
                ALTER TABLE workspace_folder_generated_images
                ADD CONSTRAINT workspace_folder_generated_images_target_ref_chk
                CHECK (target_ref ~ '^generated-image-target:[0-9a-f]{12}$');
            END IF;
        END
        $$;
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS workspace_folder_generated_images_folder_active_idx
        ON workspace_folder_generated_images (workspace_folder_id, deleted_at, updated_at DESC);
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS workspace_folder_generated_images_folder_target_active_idx
        ON workspace_folder_generated_images (workspace_folder_id, target_ref)
        WHERE deleted_at IS NULL AND target_ref <> '';
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS workspace_folder_generated_images_state_idx
        ON workspace_folder_generated_images (local_state, nextcloud_sync_state, deleted_at);
        """
    )
