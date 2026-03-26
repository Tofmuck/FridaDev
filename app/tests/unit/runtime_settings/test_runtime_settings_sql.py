from __future__ import annotations

import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
SQL_PATH = APP_DIR / 'admin' / 'sql' / 'runtime_settings_v1.sql'


class RuntimeSettingsSqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = SQL_PATH.read_text(encoding='utf-8')

    def test_sql_file_exists(self) -> None:
        self.assertTrue(SQL_PATH.exists())

    def test_migration_is_idempotent(self) -> None:
        self.assertIn('CREATE EXTENSION IF NOT EXISTS pgcrypto;', self.sql)
        self.assertIn('CREATE TABLE IF NOT EXISTS runtime_settings (', self.sql)
        self.assertIn('CREATE TABLE IF NOT EXISTS runtime_settings_history (', self.sql)
        self.assertIn('CREATE INDEX IF NOT EXISTS runtime_settings_updated_at_idx', self.sql)
        self.assertIn('CREATE INDEX IF NOT EXISTS runtime_settings_history_section_changed_at_idx', self.sql)

    def test_runtime_settings_primary_key_and_section_constraint_exist(self) -> None:
        self.assertIn('section TEXT PRIMARY KEY,', self.sql)
        for section in (
            "'main_model'",
            "'arbiter_model'",
            "'summary_model'",
            "'embedding'",
            "'database'",
            "'services'",
            "'resources'",
        ):
            self.assertIn(section, self.sql)

    def test_payload_structure_supports_secret_metadata(self) -> None:
        self.assertIn("payload JSONB NOT NULL DEFAULT '{}'::jsonb", self.sql)
        self.assertIn("jsonb_typeof(payload) = 'object'", self.sql)
        self.assertIn('value_encrypted, is_secret, is_set, origin', self.sql)

    def test_history_table_exists(self) -> None:
        self.assertIn('id UUID PRIMARY KEY DEFAULT gen_random_uuid(),', self.sql)
        self.assertIn('payload_before JSONB NOT NULL,', self.sql)
        self.assertIn('payload_after JSONB NOT NULL,', self.sql)
        self.assertIn("jsonb_typeof(payload_before) = 'object'", self.sql)
        self.assertIn("jsonb_typeof(payload_after) = 'object'", self.sql)

    def test_migration_documents_bootstrap_boundary(self) -> None:
        self.assertIn('No extra PostgreSQL extension is required beyond pgcrypto.', self.sql)
        self.assertIn('FRIDA_MEMORY_DB_DSN remains the external bootstrap during the transition.', self.sql)
        self.assertIn('Do not seed database.dsn from this migration while bootstrap remains external.', self.sql)


if __name__ == '__main__':
    unittest.main()
