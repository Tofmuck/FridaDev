from __future__ import annotations

import ast
import contextlib
import inspect
import io
import sys
import textwrap
import unittest
from pathlib import Path
from unittest import mock


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import minimal_validation
from admin import runtime_settings


def _required_tables_schema() -> dict[str, set[str]]:
    source = textwrap.dedent(inspect.getsource(minimal_validation._check_db_schema))
    tree = ast.parse(source)
    function = tree.body[0]
    if not isinstance(function, ast.FunctionDef):
        raise AssertionError("unexpected _check_db_schema source shape")
    for node in function.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
            value_node = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value_node = node.value
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "required_tables":
                value = ast.literal_eval(value_node)
                if not isinstance(value, dict):
                    raise AssertionError("required_tables should be a dict literal")
                return value
    raise AssertionError("required_tables literal not found in _check_db_schema")


class MinimalValidationPhase11Tests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def _db_database_view(self) -> runtime_settings.RuntimeSectionView:
        return runtime_settings.RuntimeSectionView(
            section="database",
            payload=runtime_settings.normalize_stored_payload(
                "database",
                {
                    "backend": {"value": "postgresql", "origin": "db"},
                    "dsn": {"value_encrypted": "ciphertext", "origin": "db"},
                },
            ),
            source="db",
            source_reason="db_row",
        )

    def test_check_db_schema_raises_when_runtime_settings_table_is_missing(self) -> None:
        required_tables = _required_tables_schema()
        all_columns = sorted({column for columns in required_tables.values() for column in columns})
        observed_tables: list[str] = []

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, query, params=None):
                self.query = str(query)
                self.params = params

            def fetchall(self):
                if "FROM pg_extension" in self.query:
                    return [("pgcrypto",), ("vector",)]
                table_name = str((self.params or ("",))[0])
                observed_tables.append(table_name)
                if table_name == "runtime_settings":
                    return []
                return [(column,) for column in all_columns]

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

        with mock.patch.object(
            minimal_validation.runtime_settings,
            "get_database_settings",
            return_value=self._db_database_view(),
        ), mock.patch.object(
            minimal_validation,
            "_bootstrap_database_dsn",
            return_value="postgresql://bootstrap-user:bootstrap-pass@bootstrap-host/bootstrap-db",
        ), mock.patch.object(
            minimal_validation.psycopg,
            "connect",
            return_value=FakeConnection(),
        ):
            with self.assertRaisesRegex(RuntimeError, "table absente: runtime_settings"):
                minimal_validation._check_db_schema()

        self.assertIn("runtime_settings", observed_tables)

    def test_main_returns_non_zero_when_runtime_settings_table_is_missing(self) -> None:
        stdout = io.StringIO()

        with mock.patch.object(minimal_validation, "_check_startup_import", return_value={"ok": True}), mock.patch.object(
            minimal_validation,
            "_check_db_schema",
            side_effect=RuntimeError("table absente: runtime_settings"),
        ), mock.patch.object(
            minimal_validation,
            "_check_prompt_files",
            return_value={"ok": True},
        ), mock.patch.object(
            minimal_validation,
            "_check_ui_assets",
            return_value={"ok": True},
        ), mock.patch.object(
            sys,
            "argv",
            ["minimal_validation.py", "--skip-live", "--json"],
        ):
            with contextlib.redirect_stdout(stdout):
                exit_code = minimal_validation.main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertIn('"name": "db_schema"', output)
        self.assertIn('"ok": false', output)
        self.assertIn("table absente: runtime_settings", output)


if __name__ == "__main__":
    unittest.main()
