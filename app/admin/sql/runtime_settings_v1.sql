-- Admin runtime settings V1 migration.
-- This migration is idempotent and can run on an already initialized environment.
-- No extra PostgreSQL extension is required beyond pgcrypto.
-- FRIDA_MEMORY_DB_DSN remains the external bootstrap during the transition.
-- Do not seed database.dsn from this migration while bootstrap remains external.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS runtime_settings (
    section TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT runtime_settings_section_chk CHECK (
        section IN (
            'main_model',
            'arbiter_model',
            'summary_model',
            'embedding',
            'database',
            'services',
            'resources'
        )
    ),
    CONSTRAINT runtime_settings_payload_object_chk CHECK (
        jsonb_typeof(payload) = 'object'
    )
);

COMMENT ON TABLE runtime_settings IS
    'Runtime settings by section. One row per section JSONB payload.';
COMMENT ON COLUMN runtime_settings.payload IS
    'Field map. Secret fields are stored as objects using value_encrypted, is_secret, is_set, origin. Non-secret fields use value, is_secret, origin.';

CREATE INDEX IF NOT EXISTS runtime_settings_updated_at_idx
ON runtime_settings (updated_at DESC);

CREATE TABLE IF NOT EXISTS runtime_settings_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section TEXT NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    changed_by TEXT NOT NULL,
    payload_before JSONB NOT NULL,
    payload_after JSONB NOT NULL,
    CONSTRAINT runtime_settings_history_section_chk CHECK (
        section IN (
            'main_model',
            'arbiter_model',
            'summary_model',
            'embedding',
            'database',
            'services',
            'resources'
        )
    ),
    CONSTRAINT runtime_settings_history_before_object_chk CHECK (
        jsonb_typeof(payload_before) = 'object'
    ),
    CONSTRAINT runtime_settings_history_after_object_chk CHECK (
        jsonb_typeof(payload_after) = 'object'
    )
);

COMMENT ON TABLE runtime_settings_history IS
    'Revision log for runtime settings. Snapshots keep secret field structure under encrypted form only.';

CREATE INDEX IF NOT EXISTS runtime_settings_history_section_changed_at_idx
ON runtime_settings_history (section, changed_at DESC);
