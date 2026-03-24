from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from core import conv_store
import config


class ConvStorePhase4DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def _db_database_view(self, *, backend: str = "postgresql", dsn_is_set: bool = True):
        payload = {
            "backend": {"value": backend, "origin": "db"},
            "dsn": {"value_encrypted": "ciphertext", "origin": "db"},
        }
        if not dsn_is_set:
            payload["dsn"] = {"is_set": False, "origin": "db"}
        return runtime_settings.RuntimeSectionView(
            section="database",
            payload=runtime_settings.normalize_stored_payload("database", payload),
            source="db",
            source_reason="db_row",
        )

    def test_db_conn_uses_external_bootstrap_dsn_with_runtime_postgresql_backend(self) -> None:
        observed = {"dsn": None}
        original_get_settings = conv_store.runtime_settings.get_database_settings
        original_connect = conv_store.psycopg.connect
        original_dsn = config.FRIDA_MEMORY_DB_DSN

        def fake_connect(dsn):
            observed["dsn"] = dsn
            return object()

        conv_store.runtime_settings.get_database_settings = self._db_database_view
        conv_store.psycopg.connect = fake_connect
        config.FRIDA_MEMORY_DB_DSN = "postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db"
        try:
            conn = conv_store._db_conn()
        finally:
            conv_store.runtime_settings.get_database_settings = original_get_settings
            conv_store.psycopg.connect = original_connect
            config.FRIDA_MEMORY_DB_DSN = original_dsn

        self.assertIsNotNone(conn)
        self.assertEqual(
            observed["dsn"],
            "postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db",
        )

    def test_db_conn_rejects_unsupported_runtime_database_backend(self) -> None:
        original_get_settings = conv_store.runtime_settings.get_database_settings
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        conv_store.runtime_settings.get_database_settings = lambda: self._db_database_view(backend="mysql")
        config.FRIDA_MEMORY_DB_DSN = "postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db"
        try:
            with self.assertRaisesRegex(ValueError, "unsupported runtime database backend: mysql"):
                conv_store._db_conn()
        finally:
            conv_store.runtime_settings.get_database_settings = original_get_settings
            config.FRIDA_MEMORY_DB_DSN = original_dsn

    def test_bootstrap_database_dsn_requires_env_fallback_while_db_secret_decryption_is_unavailable(self) -> None:
        original_get_settings = conv_store.runtime_settings.get_database_settings
        original_get_secret = conv_store.runtime_settings.get_runtime_secret_value
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        observed = {'called': False}

        def fake_get_runtime_secret_value(section: str, field: str):
            observed['called'] = True
            raise AssertionError('database bootstrap must not resolve runtime secret values')

        conv_store.runtime_settings.get_database_settings = self._db_database_view
        conv_store.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        config.FRIDA_MEMORY_DB_DSN = ""
        try:
            with self.assertRaisesRegex(
                runtime_settings.RuntimeSettingsSecretRequiredError,
                "runtime secret decryption is not available",
            ):
                conv_store._bootstrap_database_dsn()
        finally:
            conv_store.runtime_settings.get_database_settings = original_get_settings
            conv_store.runtime_settings.get_runtime_secret_value = original_get_secret
            config.FRIDA_MEMORY_DB_DSN = original_dsn

        self.assertFalse(observed['called'])


if __name__ == "__main__":
    unittest.main()
