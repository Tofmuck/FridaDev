from __future__ import annotations

import hashlib
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import workspace_file_ocr_store
from core import workspace_files_store


FOLDER_ID = "11111111-2222-4333-8444-555555555555"
FILE_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
OTHER_FILE_ID = "bbbbbbbb-bbbb-4ccc-8ddd-eeeeeeeeeeee"
V0 = b"version-zero-private"
V1 = b"version-one-private"
V2 = b"version-two-private"


class WorkspaceFileOcrStoreTest(unittest.TestCase):
    def test_same_target_writer_waits_for_failed_writer_then_commits_consistently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backend = _TransactionalWorkspaceFilesFake(
                root,
                {FILE_ID: V0},
                blocked_digest=_digest(V1),
                blocked_error=True,
            )
            results: dict[str, object] = {}

            writer_a = _update_thread(
                "writer-a",
                backend,
                root,
                FILE_ID,
                V1,
                results,
            )
            writer_a.start()
            self.assertTrue(backend.blocked_update_entered.wait(5))

            writer_b = _update_thread(
                "writer-b",
                backend,
                root,
                FILE_ID,
                V2,
                results,
            )
            writer_b.start()
            self.assertTrue(backend.writer_b_state_known.wait(5))
            backend.allow_blocked_update.set()

            writer_a.join(5)
            writer_b.join(5)
            self.assertFalse(writer_a.is_alive())
            self.assertFalse(writer_b.is_alive())
            self.assertIsNone(results["writer-a"])
            self.assertIsNotNone(results["writer-b"])
            self.assertEqual(_path(root, FILE_ID).read_bytes(), V2)
            self.assertEqual(backend.rows[FILE_ID]["sha256"], _digest(V2))
            self.assertEqual(backend.rows[FILE_ID]["sha256_12"], _digest(V2)[:12])
            self.assertEqual(backend.rows[FILE_ID]["byte_size"], len(V2))
            self.assertTrue(backend.writer_b_waited_for_lock.is_set())
            self.assertEqual(
                backend.statement_connection_ids["writer-a"]["select"],
                backend.statement_connection_ids["writer-a"]["update"],
            )
            self.assertEqual(list(_temp_files(root)), [])

    def test_different_targets_progress_independently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backend = _TransactionalWorkspaceFilesFake(
                root,
                {FILE_ID: V0, OTHER_FILE_ID: V0},
                blocked_digest=_digest(V1),
                blocked_error=False,
            )
            results: dict[str, object] = {}

            writer_a = _update_thread(
                "writer-a",
                backend,
                root,
                FILE_ID,
                V1,
                results,
            )
            writer_a.start()
            self.assertTrue(backend.blocked_update_entered.wait(5))

            writer_b = _update_thread(
                "writer-b",
                backend,
                root,
                OTHER_FILE_ID,
                V2,
                results,
            )
            writer_b.start()
            self.assertTrue(backend.writer_b_committed.wait(5))
            self.assertFalse(backend.writer_b_waited_for_lock.is_set())
            backend.allow_blocked_update.set()

            writer_a.join(5)
            writer_b.join(5)
            self.assertFalse(writer_a.is_alive())
            self.assertFalse(writer_b.is_alive())
            self.assertIsNotNone(results["writer-a"])
            self.assertIsNotNone(results["writer-b"])
            self.assertEqual(_path(root, FILE_ID).read_bytes(), V1)
            self.assertEqual(_path(root, OTHER_FILE_ID).read_bytes(), V2)

    def test_delete_waits_for_inflight_update_before_removing_committed_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backend = _TransactionalWorkspaceFilesFake(
                root,
                {FILE_ID: V0},
                blocked_digest=_digest(V1),
                blocked_error=False,
            )
            results: dict[str, object] = {}
            writer_a = _update_thread(
                "writer-a",
                backend,
                root,
                FILE_ID,
                V1,
                results,
            )
            writer_a.start()
            self.assertTrue(backend.blocked_update_entered.wait(5))

            def delete() -> None:
                results["writer-delete"] = workspace_files_store.delete_workspace_file(
                    FOLDER_ID,
                    FILE_ID,
                    db_conn_func=backend.connect,
                    storage_root=root,
                    logger=backend.logger,
                )

            writer_delete = threading.Thread(target=delete, name="writer-delete")
            writer_delete.start()
            self.assertTrue(backend.deleter_state_known.wait(5))
            backend.allow_blocked_update.set()

            writer_a.join(5)
            writer_delete.join(5)
            self.assertFalse(writer_a.is_alive())
            self.assertFalse(writer_delete.is_alive())
            self.assertTrue(backend.deleter_waited_for_lock.is_set())
            self.assertIsNotNone(results["writer-a"])
            self.assertIsNotNone(results["writer-delete"])
            self.assertFalse(_path(root, FILE_ID).exists())
            self.assertEqual(backend.rows[FILE_ID]["status"], workspace_files_store.STATUS_DELETED)
            self.assertIsNotNone(backend.rows[FILE_ID]["deleted_at"])

    def test_failed_writer_does_not_restore_over_newer_committed_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backend = _TransactionalWorkspaceFilesFake(
                root,
                {FILE_ID: V0},
                blocked_digest=_digest(V1),
                blocked_error=True,
            )
            results: dict[str, object] = {}
            writer_a = _update_thread(
                "writer-a",
                backend,
                root,
                FILE_ID,
                V1,
                results,
            )
            writer_a.start()
            self.assertTrue(backend.blocked_update_entered.wait(5))

            workspace_files_store.write_file_bytes(root, _storage_key(FILE_ID), V2)
            backend.force_committed_version(FILE_ID, V2)
            backend.allow_blocked_update.set()

            writer_a.join(5)
            self.assertFalse(writer_a.is_alive())
            self.assertIsNone(results["writer-a"])
            self.assertEqual(_path(root, FILE_ID).read_bytes(), V2)
            self.assertEqual(backend.rows[FILE_ID]["sha256"], _digest(V2))
            self.assertEqual(backend.rows[FILE_ID]["byte_size"], len(V2))

    def test_sql_failure_without_other_writer_restores_exact_previous_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backend = _TransactionalWorkspaceFilesFake(
                root,
                {FILE_ID: V0},
                blocked_digest=_digest(V1),
                blocked_error=True,
            )
            backend.allow_blocked_update.set()

            result = _update(backend, root, FILE_ID, V1)

            self.assertIsNone(result)
            self.assertEqual(_path(root, FILE_ID).read_bytes(), V0)
            self.assertEqual(backend.rows[FILE_ID]["sha256"], _digest(V0))
            self.assertEqual(backend.rows[FILE_ID]["byte_size"], len(V0))
            self.assertGreaterEqual(backend.rollbacks, 1)
            self.assertEqual(list(_temp_files(root)), [])

    def test_success_keeps_file_full_hash_short_hash_size_and_sql_on_one_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backend = _TransactionalWorkspaceFilesFake(root, {FILE_ID: V0})

            result = _update(backend, root, FILE_ID, V1)

            self.assertIsNotNone(result)
            self.assertEqual(_path(root, FILE_ID).read_bytes(), V1)
            self.assertEqual(backend.rows[FILE_ID]["sha256"], _digest(V1))
            self.assertEqual(backend.rows[FILE_ID]["sha256_12"], _digest(V1)[:12])
            self.assertEqual(backend.rows[FILE_ID]["byte_size"], len(V1))
            self.assertEqual(backend.rows[FILE_ID]["text_chars"], len(V1))
            self.assertEqual(backend.rows[FILE_ID]["text_sha256_12"], _digest(V1)[:12])
            self.assertEqual(result["sha256_12"], _digest(V1)[:12])
            self.assertEqual(result["byte_size"], len(V1))
            self.assertEqual(list(_temp_files(root)), [])
            logged = "\n".join(backend.logger.lines)
            self.assertNotIn(V0.decode("ascii"), logged)
            self.assertNotIn(V1.decode("ascii"), logged)
            self.assertNotIn(str(root), logged)
            self.assertNotIn(_digest(V1), logged)

    def test_candidate_write_failure_keeps_v0_and_reports_disk_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backend = _TransactionalWorkspaceFilesFake(root, {FILE_ID: V0})
            original_write = workspace_files_store.write_file_bytes

            def fail_candidate(storage_root, storage_key, content):
                if bytes(content) == V1:
                    raise OSError("synthetic-candidate-write-failure")
                return original_write(storage_root, storage_key, content)

            with mock.patch.object(
                workspace_files_store,
                "write_file_bytes",
                side_effect=fail_candidate,
            ):
                result = _update(backend, root, FILE_ID, V1)

            self.assertIsNone(result)
            self.assertEqual(_path(root, FILE_ID).read_bytes(), V0)
            self.assertEqual(backend.rows[FILE_ID]["sha256"], _digest(V0))
            self.assertEqual(backend.update_attempts, 0)
            logged = "\n".join(backend.logger.lines)
            self.assertIn("reason_code=workspace_file_disk_missing", logged)
            self.assertNotIn("reason_code=workspace_file_db_missing", logged)

    def test_compensation_failure_never_returns_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backend = _TransactionalWorkspaceFilesFake(
                root,
                {FILE_ID: V0},
                blocked_digest=_digest(V1),
                blocked_error=True,
            )
            backend.allow_blocked_update.set()
            original_write = workspace_files_store.write_file_bytes

            def fail_restore(storage_root, storage_key, content):
                if bytes(content) == V0:
                    raise OSError("synthetic-compensation-failure")
                return original_write(storage_root, storage_key, content)

            with mock.patch.object(
                workspace_files_store,
                "write_file_bytes",
                side_effect=fail_restore,
            ):
                result = _update(backend, root, FILE_ID, V1)

            self.assertIsNone(result)
            self.assertEqual(_path(root, FILE_ID).read_bytes(), V1)
            self.assertEqual(backend.rows[FILE_ID]["sha256"], _digest(V0))
            self.assertGreaterEqual(backend.rollbacks, 1)

    def test_missing_previous_file_is_refused_without_candidate_or_sql_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backend = _TransactionalWorkspaceFilesFake(root, {FILE_ID: V0})
            _path(root, FILE_ID).unlink()

            result = _update(backend, root, FILE_ID, V1)

            self.assertIsNone(result)
            self.assertFalse(_path(root, FILE_ID).exists())
            self.assertEqual(backend.rows[FILE_ID]["sha256"], _digest(V0))
            self.assertEqual(backend.update_attempts, 0)

    def test_unreadable_previous_file_is_refused_without_false_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backend = _TransactionalWorkspaceFilesFake(root, {FILE_ID: V0})
            with mock.patch.object(
                workspace_file_ocr_store,
                "read_file_bytes",
                side_effect=PermissionError("synthetic-unreadable"),
            ):
                result = _update(backend, root, FILE_ID, V1)

            self.assertIsNone(result)
            self.assertEqual(_path(root, FILE_ID).read_bytes(), V0)
            self.assertEqual(backend.rows[FILE_ID]["sha256"], _digest(V0))
            self.assertEqual(backend.update_attempts, 0)

    def test_same_process_overlapping_writes_use_distinct_temporaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage_key = _storage_key(FILE_ID)
            first_replace_ready = threading.Event()
            allow_first_replace = threading.Event()
            writer_b_done = threading.Event()
            results: dict[str, object] = {}
            errors: dict[str, BaseException] = {}
            original_replace = Path.replace

            def controlled_replace(source: Path, target: Path) -> Path:
                if threading.current_thread().name == "temp-writer-a":
                    first_replace_ready.set()
                    if not allow_first_replace.wait(5):
                        raise AssertionError("temp writer A was not released")
                return original_replace(source, target)

            def write(name: str, content: bytes) -> None:
                try:
                    results[name] = workspace_files_store.write_file_bytes(
                        root,
                        storage_key,
                        content,
                    )
                except BaseException as exc:  # pragma: no cover - asserted below.
                    errors[name] = exc
                finally:
                    if name == "temp-writer-b":
                        writer_b_done.set()

            with mock.patch.object(Path, "replace", new=controlled_replace):
                writer_a = threading.Thread(target=write, args=("temp-writer-a", V1), name="temp-writer-a")
                writer_a.start()
                self.assertTrue(first_replace_ready.wait(5))
                writer_b = threading.Thread(target=write, args=("temp-writer-b", V2), name="temp-writer-b")
                writer_b.start()
                self.assertTrue(writer_b_done.wait(5))
                allow_first_replace.set()
                writer_a.join(5)
                writer_b.join(5)

            self.assertFalse(writer_a.is_alive())
            self.assertFalse(writer_b.is_alive())
            self.assertEqual(errors, {})
            self.assertEqual(set(results), {"temp-writer-a", "temp-writer-b"})
            self.assertEqual(_path(root, FILE_ID).read_bytes(), V1)
            self.assertEqual(list(_temp_files(root)), [])

    def test_temporary_is_cleaned_when_atomic_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(Path, "replace", side_effect=OSError("synthetic-replace-failure")):
                with self.assertRaises(OSError):
                    workspace_files_store.write_file_bytes(root, _storage_key(FILE_ID), V1)

            self.assertEqual(list(_temp_files(root)), [])


class _TransactionalWorkspaceFilesFake:
    def __init__(
        self,
        storage_root: Path,
        initial_versions: dict[str, bytes],
        *,
        blocked_digest: str = "",
        blocked_error: bool = False,
    ) -> None:
        self.storage_root = storage_root
        self.rows = {
            file_id: _row(file_id, content)
            for file_id, content in initial_versions.items()
        }
        for file_id, content in initial_versions.items():
            workspace_files_store.write_file_bytes(
                storage_root,
                _storage_key(file_id),
                content,
            )
        self.blocked_digest = blocked_digest
        self.blocked_error = blocked_error
        self.blocked_update_entered = threading.Event()
        self.allow_blocked_update = threading.Event()
        self.writer_b_state_known = threading.Event()
        self.writer_b_waited_for_lock = threading.Event()
        self.writer_b_committed = threading.Event()
        self.deleter_state_known = threading.Event()
        self.deleter_waited_for_lock = threading.Event()
        self.deletion_committed = threading.Event()
        self.row_locks = {file_id: threading.Lock() for file_id in initial_versions}
        self.state_lock = threading.Lock()
        self.statement_connection_ids: dict[str, dict[str, int]] = {}
        self.connection_count = 0
        self.commits = 0
        self.rollbacks = 0
        self.update_attempts = 0
        self.logger = _CaptureLogger()

    def connect(self) -> "_FakeConnection":
        with self.state_lock:
            self.connection_count += 1
            connection_id = self.connection_count
        return _FakeConnection(self, connection_id)

    def record_statement(self, operation: str, connection_id: int) -> None:
        name = threading.current_thread().name
        with self.state_lock:
            self.statement_connection_ids.setdefault(name, {})[operation] = connection_id

    def force_committed_version(self, file_id: str, content: bytes) -> None:
        with self.state_lock:
            self.rows[file_id] = _row(file_id, content)


class _FakeConnection:
    def __init__(self, backend: _TransactionalWorkspaceFilesFake, connection_id: int) -> None:
        self.backend = backend
        self.connection_id = connection_id
        self.staged_row: dict[str, object] | None = None
        self.held_lock: threading.Lock | None = None
        self.closed = False

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if self.held_lock is not None:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        self.closed = True
        return False

    def cursor(self, *args, **kwargs) -> "_FakeCursor":
        return _FakeCursor(self)

    def commit(self) -> None:
        if self.staged_row is not None:
            with self.backend.state_lock:
                self.backend.rows[str(self.staged_row["id"])] = dict(self.staged_row)
                self.backend.commits += 1
            if threading.current_thread().name == "writer-b":
                self.backend.writer_b_committed.set()
                self.backend.writer_b_state_known.set()
            if self.staged_row.get("deleted_at") is not None:
                self.backend.deletion_committed.set()
                self.backend.deleter_state_known.set()
            self.staged_row = None
        self._release_lock()

    def rollback(self) -> None:
        self.staged_row = None
        with self.backend.state_lock:
            self.backend.rollbacks += 1
        self._release_lock()

    def _release_lock(self) -> None:
        if self.held_lock is not None:
            self.held_lock.release()
            self.held_lock = None


class _FakeCursor:
    def __init__(self, conn: _FakeConnection) -> None:
        self.conn = conn
        self.result: dict[str, object] | None = None

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def execute(self, sql, params=None) -> None:
        normalized_sql = " ".join(str(sql).split()).lower()
        values = tuple(params or ())
        if normalized_sql.startswith("select storage_key"):
            file_id, folder_id = values
            self.conn.backend.record_statement("select", self.conn.connection_id)
            row_lock = self.conn.backend.row_locks[file_id]
            if "for update" in normalized_sql:
                if row_lock.locked() and threading.current_thread().name == "writer-b":
                    self.conn.backend.writer_b_waited_for_lock.set()
                    self.conn.backend.writer_b_state_known.set()
                row_lock.acquire()
                self.conn.held_lock = row_lock
            with self.conn.backend.state_lock:
                row = self.conn.backend.rows.get(file_id)
                self.result = (
                    {"storage_key": row["storage_key"]}
                    if row
                    and row["workspace_folder_id"] == folder_id
                    and row.get("deleted_at") is None
                    else None
                )
            return
        if normalized_sql.startswith("select id, workspace_folder_id, storage_key"):
            file_id, folder_id = values
            row_lock = self.conn.backend.row_locks[file_id]
            if "for update" in normalized_sql:
                if row_lock.locked() and threading.current_thread().name == "writer-delete":
                    self.conn.backend.deleter_waited_for_lock.set()
                    self.conn.backend.deleter_state_known.set()
                row_lock.acquire()
                self.conn.held_lock = row_lock
            with self.conn.backend.state_lock:
                row = self.conn.backend.rows.get(file_id)
                self.result = (
                    {
                        "id": row["id"],
                        "workspace_folder_id": row["workspace_folder_id"],
                        "storage_key": row["storage_key"],
                    }
                    if row
                    and row["workspace_folder_id"] == folder_id
                    and row.get("deleted_at") is None
                    else None
                )
            return
        if normalized_sql.startswith("update workspace_files") and "set deleted_at" in normalized_sql:
            status, reason_code, file_id, folder_id = values
            with self.conn.backend.state_lock:
                current = self.conn.backend.rows.get(file_id)
            if not current or current["workspace_folder_id"] != folder_id:
                self.result = None
                return
            next_row = dict(current)
            next_row.update(
                {
                    "deleted_at": "2026-09-04T18:30:00Z",
                    "updated_at": "2026-09-04T18:30:00Z",
                    "status": status,
                    "reason_code": reason_code,
                }
            )
            self.conn.staged_row = next_row
            self.result = dict(next_row)
            return
        if normalized_sql.startswith("update workspace_file_selections"):
            self.result = None
            return
        if normalized_sql.startswith("update workspace_files"):
            self.conn.backend.record_statement("update", self.conn.connection_id)
            (
                byte_size,
                digest,
                digest_12,
                text_chars,
                text_sha256_12,
                status,
                reason_code,
                file_id,
                folder_id,
            ) = values
            with self.conn.backend.state_lock:
                self.conn.backend.update_attempts += 1
                current = self.conn.backend.rows.get(file_id)
            if digest == self.conn.backend.blocked_digest:
                self.conn.backend.blocked_update_entered.set()
                if not self.conn.backend.allow_blocked_update.wait(5):
                    raise AssertionError("blocked SQL update was not released")
                if self.conn.backend.blocked_error:
                    raise RuntimeError("synthetic-sql-failure")
            if not current or current["workspace_folder_id"] != folder_id or current.get("deleted_at") is not None:
                self.result = None
                return
            next_row = dict(current)
            next_row.update(
                {
                    "byte_size": byte_size,
                    "sha256": digest,
                    "sha256_12": digest_12,
                    "text_chars": text_chars,
                    "text_sha256_12": text_sha256_12,
                    "status": status,
                    "reason_code": reason_code,
                    "updated_at": "2026-09-04T18:00:00Z",
                }
            )
            self.conn.staged_row = next_row
            self.result = dict(next_row)
            return
        raise AssertionError(f"unexpected SQL: {normalized_sql}")

    def fetchone(self):
        return self.result


class _CaptureLogger:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def info(self, message, *args, **kwargs) -> None:
        self.lines.append(message % args if args else str(message))

    def warning(self, message, *args, **kwargs) -> None:
        self.lines.append(message % args if args else str(message))

    def error(self, message, *args, **kwargs) -> None:
        self.lines.append(message % args if args else str(message))


def _update_thread(
    name: str,
    backend: _TransactionalWorkspaceFilesFake,
    root: Path,
    file_id: str,
    content: bytes,
    results: dict[str, object],
) -> threading.Thread:
    def run() -> None:
        results[name] = _update(backend, root, file_id, content)

    return threading.Thread(target=run, name=name)


def _update(
    backend: _TransactionalWorkspaceFilesFake,
    root: Path,
    file_id: str,
    content: bytes,
):
    return workspace_file_ocr_store.update_workspace_text_file(
        FOLDER_ID,
        file_id,
        content=content,
        metadata={
            "text_chars": len(content),
            "text_sha256_12": _digest(content)[:12],
            "status": workspace_files_store.STATUS_ACTIVE,
            "reason_code": "",
        },
        db_conn_func=backend.connect,
        storage_root=root,
        logger=backend.logger,
    )


def _row(file_id: str, content: bytes) -> dict[str, object]:
    return {
        "id": file_id,
        "workspace_folder_id": FOLDER_ID,
        "display_name": "synthetic.ocr.md",
        "original_filename": "synthetic.ocr.md",
        "storage_key": _storage_key(file_id),
        "content_kind": "document",
        "media_kind": "text",
        "mime_type": "text/markdown",
        "source_extension": ".md",
        "byte_size": len(content),
        "sha256": _digest(content),
        "sha256_12": _digest(content)[:12],
        "text_chars": len(content),
        "text_sha256_12": _digest(content)[:12],
        "image_width": 0,
        "image_height": 0,
        "status": "active",
        "reason_code": "",
        "source_kind": "ocr_derived",
        "source_file_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "created_at": "2026-09-04T17:00:00Z",
        "updated_at": "2026-09-04T17:00:00Z",
        "deleted_at": None,
    }


def _storage_key(file_id: str) -> str:
    return workspace_files_store.storage_key_for(FOLDER_ID, file_id, ".md")


def _path(root: Path, file_id: str) -> Path:
    return workspace_files_store.workspace_file_path(root, _storage_key(file_id))


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _temp_files(root: Path):
    return (path for path in root.rglob(".*.tmp") if path.is_file())


if __name__ == "__main__":
    unittest.main()
