from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = APP_DIR.parent
CONV_STORE_PATH = APP_DIR / "core" / "conv_store.py"
AUDIT_PATH = APP_DIR / "docs" / "fridadev_repo_audit.md"
SELF_PATH = Path(__file__).resolve()

SYNC_HELPERS = (
    "sync_catalog_from_json_files",
    "sync_messages_from_json_files",
    "get_storage_counts",
    "_load_json_conversation_file",
)


def _find_name_matches(paths: list[Path], name: str) -> list[Path]:
    pattern = re.compile(rf"\b{re.escape(name)}\b")
    matches: list[Path] = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        if pattern.search(source):
            matches.append(path)
    return matches


class ConvStoreJsonSyncInventoryPhase6Tests(unittest.TestCase):
    def test_sync_helpers_are_still_defined_in_conv_store(self) -> None:
        tree = ast.parse(CONV_STORE_PATH.read_text(encoding="utf-8"))
        declared = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        for helper_name in SYNC_HELPERS:
            self.assertIn(helper_name, declared)

    def test_sync_helpers_have_no_runtime_or_test_references_outside_conv_store(self) -> None:
        runtime_py_files = sorted(
            path
            for path in APP_DIR.rglob("*.py")
            if path != CONV_STORE_PATH and "tests" not in path.parts
        )
        test_py_files = sorted(
            path
            for path in (APP_DIR / "tests").rglob("*.py")
            if path.resolve() != SELF_PATH
        )

        for helper_name in SYNC_HELPERS:
            self.assertEqual(_find_name_matches(runtime_py_files, helper_name), [])
            self.assertEqual(_find_name_matches(test_py_files, helper_name), [])

    def test_sync_helpers_are_documented_in_repo_audit(self) -> None:
        docs_md_files = sorted((APP_DIR / "docs").rglob("*.md"))
        for helper_name in SYNC_HELPERS:
            matches = _find_name_matches(docs_md_files, helper_name)
            self.assertIn(AUDIT_PATH, matches)

    def test_load_json_helper_is_only_used_inside_sync_helpers(self) -> None:
        tree = ast.parse(CONV_STORE_PATH.read_text(encoding="utf-8"))
        callers: set[str] = set()

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for nested in ast.walk(node):
                if not isinstance(nested, ast.Call):
                    continue
                if isinstance(nested.func, ast.Name) and nested.func.id == "_load_json_conversation_file":
                    if node.name != "_load_json_conversation_file":
                        callers.add(node.name)

        self.assertEqual(
            callers,
            {
                "sync_catalog_from_json_files",
                "sync_messages_from_json_files",
                "get_storage_counts",
            },
        )

    def test_sync_helper_names_do_not_appear_in_shell_scripts(self) -> None:
        shell_scripts = sorted(REPO_DIR.rglob("*.sh"))
        for helper_name in SYNC_HELPERS:
            self.assertEqual(_find_name_matches(shell_scripts, helper_name), [])
