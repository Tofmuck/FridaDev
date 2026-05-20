from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import conversations_maintenance
from core import active_document_prompt_lane
from core import chat_service
from core import workspace_file_selection_prompt
from core import workspace_file_selections_store
from core import workspace_files_store
from core import workspace_folders_store


class _FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.conn.queries.append(" ".join(str(sql).split()))


class _FakeConn:
    def __init__(self):
        self.queries = []
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, *args, **kwargs):
        return _FakeCursor(self)

    def commit(self):
        self.commits += 1


class _CaptureLogger:
    def __init__(self):
        self.lines = []

    def info(self, msg, *args, **_kwargs):
        self.lines.append(msg % args if args else str(msg))

    def warning(self, msg, *args, **_kwargs):
        self.lines.append(msg % args if args else str(msg))

    def error(self, msg, *args, **_kwargs):
        self.lines.append(msg % args if args else str(msg))


class _WorkspaceFilesCursor:
    def __init__(self, conn):
        self.conn = conn
        self.result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        normalized_sql = " ".join(str(sql).split()).lower()
        params = tuple(params or ())
        self.conn.queries.append(normalized_sql)
        if "select id::text from workspace_files" in normalized_sql:
            folder_id = params[0]
            self.result = [
                (row["id"],)
                for row in self.conn.rows.values()
                if row["workspace_folder_id"] == folder_id and row.get("deleted_at") is None
            ]
            return
        if "select id, workspace_folder_id, storage_key from workspace_files" in normalized_sql:
            file_id, folder_id = params
            row = self.conn.rows.get(file_id)
            if row and row["workspace_folder_id"] == folder_id and row.get("deleted_at") is None:
                self.result = {
                    "id": row["id"],
                    "workspace_folder_id": row["workspace_folder_id"],
                    "storage_key": row["storage_key"],
                }
            else:
                self.result = None
            return
        if "update workspace_files" in normalized_sql:
            status, reason_code, file_id, folder_id = params
            row = self.conn.rows.get(file_id)
            if row and row["workspace_folder_id"] == folder_id:
                row["status"] = status
                row["reason_code"] = reason_code
                row["deleted_at"] = "2026-05-20T00:04:00Z"
                row["updated_at"] = "2026-05-20T00:04:00Z"
                self.result = dict(row)
            else:
                self.result = None
            return
        if "update workspace_file_selections" in normalized_sql:
            self.result = None
            return
        raise AssertionError(f"unexpected SQL: {normalized_sql}")

    def fetchall(self):
        return list(self.result or [])

    def fetchone(self):
        return self.result


class _WorkspaceFilesConn:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, *args, **kwargs):
        return _WorkspaceFilesCursor(self)

    def commit(self):
        self.commits += 1


def _workspace_file_row(folder_id, file_id, storage_key):
    return {
        "id": file_id,
        "workspace_folder_id": folder_id,
        "display_name": "note.txt",
        "original_filename": "note.txt",
        "storage_key": storage_key,
        "content_kind": "document",
        "media_kind": "text",
        "mime_type": "text/plain",
        "source_extension": ".txt",
        "byte_size": 7,
        "sha256": "full-hash-hidden",
        "sha256_12": "abc123def456",
        "text_chars": 7,
        "text_sha256_12": "text12345678",
        "image_width": 0,
        "image_height": 0,
        "status": "active",
        "reason_code": "",
        "source_kind": "upload",
        "source_file_id": None,
        "created_at": "2026-05-20T00:00:00Z",
        "updated_at": "2026-05-20T00:00:00Z",
        "deleted_at": None,
    }


class _SelectionPromptCursor:
    def __init__(self, conn):
        self.conn = conn
        self.result = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        normalized_sql = " ".join(str(sql).split()).lower()
        params = tuple(params or ())
        self.conn.queries.append(normalized_sql)
        if "from workspace_file_selections" not in normalized_sql:
            raise AssertionError(f"unexpected SQL: {normalized_sql}")
        conversation_id = params[0]
        file_id = params[1] if len(params) > 1 else None
        self.result = [
            dict(row)
            for row in self.conn.rows
            if row["conversation_id"] == conversation_id and (file_id is None or row["workspace_file_id"] == file_id)
        ]

    def fetchall(self):
        return list(self.result)

    def fetchone(self):
        return self.result[0] if self.result else None


class _SelectionPromptConn:
    def __init__(self, rows):
        self.rows = list(rows)
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, *args, **kwargs):
        return _SelectionPromptCursor(self)


def _selection_prompt_row(
    *,
    conversation_id,
    folder_id,
    file_id,
    storage_key,
    display_name="note.txt",
    media_kind="text",
    mime_type="text/plain",
    source_extension=".txt",
    byte_size=7,
    sha256_12="abc123def456",
    image_width=0,
    image_height=0,
    file_status="active",
):
    return {
        "conversation_id": conversation_id,
        "workspace_file_id": file_id,
        "selected_at": "2026-05-20T00:10:00Z",
        "selection_updated_at": "2026-05-20T00:10:00Z",
        "selection_deleted_at": None,
        "last_injected_turn_id": "",
        "last_excluded_turn_id": "",
        "last_excluded_reason_code": "",
        "conversation_workspace_folder_id": folder_id,
        "conversation_deleted_at": None,
        "workspace_folder_id": folder_id,
        "display_name": display_name,
        "original_filename": display_name,
        "storage_key": storage_key,
        "content_kind": "image" if media_kind == "image" else "document",
        "media_kind": media_kind,
        "mime_type": mime_type,
        "source_extension": source_extension,
        "byte_size": byte_size,
        "sha256": "full-hash-hidden",
        "sha256_12": sha256_12,
        "text_chars": 0,
        "text_sha256_12": "",
        "image_width": image_width,
        "image_height": image_height,
        "file_status": file_status,
        "file_reason_code": "",
        "source_kind": "upload",
        "source_file_id": None,
        "file_created_at": "2026-05-20T00:00:00Z",
        "file_updated_at": "2026-05-20T00:00:00Z",
        "file_deleted_at": None,
    }


class WorkspaceFoldersContractTests(unittest.TestCase):
    def test_catalog_init_creates_workspace_table_and_nullable_conversation_relation(self) -> None:
        conn = _FakeConn()
        logger = type("Logger", (), {"info": lambda *_args, **_kwargs: None, "error": lambda *_args, **_kwargs: None})()

        conversations_maintenance.init_catalog_db(db_conn_func=lambda: conn, logger=logger)

        sql = "\n".join(conn.queries).lower()
        self.assertIn("create table if not exists workspace_folders", sql)
        self.assertIn("create table if not exists workspace_files", sql)
        self.assertIn("create table if not exists workspace_file_selections", sql)
        self.assertIn("add column if not exists workspace_folder_id uuid", sql)
        self.assertIn("conversations_workspace_folder_id_fkey", sql)
        self.assertIn("on delete set null", sql)
        self.assertIn("workspace_folders_active_sort_idx", sql)
        self.assertIn("workspace_files_folder_active_idx", sql)
        self.assertIn("workspace_files_storage_key_idx", sql)
        self.assertIn("workspace_file_selections_conversation_active_idx", sql)
        self.assertEqual(conn.commits, 1)

    def test_folder_validation_keeps_allowlisted_icons_and_short_ui_metadata(self) -> None:
        self.assertEqual(workspace_folders_store.normalize_icon_key("folder"), "folder")
        self.assertEqual(workspace_folders_store.normalize_icon_key("spark"), "spark")
        self.assertIsNone(workspace_folders_store.normalize_icon_key("<svg>"))
        self.assertEqual(workspace_folders_store.sanitize_display_name("  Projet   A  "), "Projet A")
        self.assertLessEqual(
            len(workspace_folders_store.sanitize_display_name("x" * 120)),
            workspace_folders_store.DISPLAY_NAME_MAX_CHARS,
        )
        self.assertLessEqual(
            len(workspace_folders_store.sanitize_description("d" * 400)),
            workspace_folders_store.DESCRIPTION_MAX_CHARS,
        )

    def test_workspace_file_storage_key_uses_stable_ids_and_serializer_hides_internal_path(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        file_id = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        storage_key = workspace_files_store.storage_key_for(folder_id, file_id, ".PDF")

        self.assertEqual(storage_key, f"{folder_id}/{file_id}.pdf")
        serialized = workspace_files_store.serialize_workspace_file_row(
            {
                "id": file_id,
                "workspace_folder_id": folder_id,
                "display_name": "  Scan   Tulu.pdf ",
                "original_filename": "../Scan Tulu.pdf",
                "storage_key": storage_key,
                "content_kind": "document",
                "media_kind": "text",
                "mime_type": "application/pdf",
                "source_extension": ".pdf",
                "byte_size": 12,
                "sha256": "full-hash-should-not-render",
                "sha256_12": "abc123",
                "status": "active",
                "reason_code": "",
            }
        )

        self.assertEqual(serialized["display_name"], "Scan Tulu.pdf")
        self.assertEqual(serialized["original_filename"], "Scan Tulu.pdf")
        self.assertNotIn("storage_key", serialized)
        self.assertNotIn("internal_path", serialized)
        self.assertNotIn("sha256", serialized)

    def test_workspace_file_bytes_are_written_under_folder_prefix_and_removed_physically(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        file_id = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        storage_key = workspace_files_store.storage_key_for(folder_id, file_id, ".txt")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = workspace_files_store.write_file_bytes(root, storage_key, b"bonjour")

            self.assertTrue(path.exists())
            self.assertEqual(path.relative_to(root).parts[0], folder_id)
            self.assertEqual(path.read_bytes(), b"bonjour")
            self.assertTrue(workspace_files_store.delete_file_bytes(root, storage_key))
            self.assertFalse(path.exists())

    def test_folder_file_delete_summary_deletes_all_bytes_and_tombstones_rows(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        file_id_1 = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        file_id_2 = "bbbbbbbb-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_1 = workspace_files_store.storage_key_for(folder_id, file_id_1, ".txt")
            key_2 = workspace_files_store.storage_key_for(folder_id, file_id_2, ".txt")
            path_1 = workspace_files_store.write_file_bytes(root, key_1, b"bonjour")
            path_2 = workspace_files_store.write_file_bytes(root, key_2, b"salut")
            conn = _WorkspaceFilesConn(
                {
                    file_id_1: _workspace_file_row(folder_id, file_id_1, key_1),
                    file_id_2: _workspace_file_row(folder_id, file_id_2, key_2),
                }
            )
            logger = _CaptureLogger()

            summary = workspace_files_store.delete_workspace_files_for_folder(
                folder_id,
                db_conn_func=lambda: conn,
                storage_root=root,
                logger=logger,
            )

            self.assertEqual(summary["requested"], 2)
            self.assertEqual(summary["deleted"], 2)
            self.assertEqual(summary["failed"], 0)
            self.assertFalse(path_1.exists())
            self.assertFalse(path_2.exists())
            self.assertEqual(conn.rows[file_id_1]["status"], "deleted")
            self.assertEqual(conn.rows[file_id_2]["reason_code"], "workspace_file_deleted")
            self.assertIn("workspace_files_folder_delete_summary", "\n".join(logger.lines))

    def test_folder_file_delete_summary_reports_partial_failure_without_masking_it(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        file_id_ok = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        file_id_bad = "bbbbbbbb-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_ok = workspace_files_store.storage_key_for(folder_id, file_id_ok, ".txt")
            path_ok = workspace_files_store.write_file_bytes(root, key_ok, b"bonjour")
            conn = _WorkspaceFilesConn(
                {
                    file_id_ok: _workspace_file_row(folder_id, file_id_ok, key_ok),
                    file_id_bad: _workspace_file_row(folder_id, file_id_bad, "../escape.txt"),
                }
            )
            logger = _CaptureLogger()

            summary = workspace_files_store.delete_workspace_files_for_folder(
                folder_id,
                db_conn_func=lambda: conn,
                storage_root=root,
                logger=logger,
            )

            self.assertEqual(summary["requested"], 2)
            self.assertEqual(summary["deleted"], 1)
            self.assertEqual(summary["failed"], 1)
            self.assertEqual(summary["failed_file_ids"], [file_id_bad])
            self.assertEqual(summary["reason_code"], "workspace_folder_file_delete_failed")
            self.assertFalse(path_ok.exists())
            self.assertEqual(conn.rows[file_id_ok]["status"], "deleted")
            self.assertIsNone(conn.rows[file_id_bad]["deleted_at"])
            logged = "\n".join(logger.lines)
            self.assertIn("workspace_files_delete_failed", logged)
            self.assertNotIn("../escape", logged)

    def test_workspace_file_logs_are_content_free(self) -> None:
        logger = _CaptureLogger()

        workspace_files_store.log_content_free_event(
            logger,
            "upload_ok",
            folder_id="11111111-2222-4333-8444-555555555555",
            file_id="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
            storage_key="/tmp/secret/path.txt",
            internal_path="/tmp/secret/path.txt",
            text_content="contenu brut",
            binary_content=b"secret",
            base64="data:image/png;base64,secret",
            mime_type="text/plain",
            byte_size=12,
            sha256_12="abc123def456",
        )

        logged = "\n".join(logger.lines)
        self.assertIn("workspace_files_upload_ok", logged)
        self.assertIn("mime_type=text/plain", logged)
        self.assertIn("sha256_12=abc123def456", logged)
        self.assertNotIn("storage_key", logged)
        self.assertNotIn("internal_path", logged)
        self.assertNotIn("/tmp/secret", logged)
        self.assertNotIn("contenu brut", logged)
        self.assertNotIn("data:image", logged)
        self.assertNotIn("base64", logged)

    def test_workspace_file_prompt_lane_injects_text_without_active_document_persistence(self) -> None:
        raw_text = "texte choisi explicitement"
        prompt_messages = [{"role": "system", "content": "SYSTEM"}, {"role": "user", "content": "question"}]

        lane = active_document_prompt_lane.inject_active_document_prompt_lane(
            prompt_messages,
            [
                {
                    "source": "workspace_file_selection",
                    "document_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "workspace_file_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "workspace_folder_id": "11111111-2222-4333-8444-555555555555",
                    "filename": "note.txt",
                    "media_type": "text/plain",
                    "source_extension": ".txt",
                    "byte_size": len(raw_text.encode("utf-8")),
                    "text_chars": len(raw_text),
                    "text_sha256_12": "abc123def456",
                    "media_kind": "text",
                    "text_content": raw_text,
                    "injectable": True,
                }
            ],
            model="openai/gpt-5.1",
            count_tokens_func=lambda _messages, _model: 10,
            max_tokens=1000,
        )

        joined = "\n".join(str(message.get("content") or "") for message in prompt_messages)
        self.assertEqual(lane.injected_count, 1)
        self.assertIn("Fichier de repertoire selectionne injecte", joined)
        self.assertIn(raw_text, joined)
        self.assertEqual(lane.decisions[0].source, "workspace_file_selection")

    def test_workspace_file_prompt_lane_excludes_too_large_with_workspace_reason(self) -> None:
        prompt_messages = [{"role": "system", "content": "SYSTEM"}, {"role": "user", "content": "question"}]

        lane = active_document_prompt_lane.inject_active_document_prompt_lane(
            prompt_messages,
            [
                {
                    "source": "workspace_file_selection",
                    "document_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "workspace_file_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "filename": "note.txt",
                    "media_type": "text/plain",
                    "source_extension": ".txt",
                    "byte_size": 10,
                    "text_chars": 10,
                    "media_kind": "text",
                    "text_content": "trop long",
                    "injectable": True,
                }
            ],
            model="openai/gpt-5.1",
            count_tokens_func=lambda _messages, _model: 9999,
            max_tokens=10,
        )

        joined = "\n".join(str(message.get("content") or "") for message in prompt_messages)
        self.assertEqual(lane.injected_count, 0)
        self.assertEqual(lane.not_injected_count, 1)
        self.assertEqual(lane.decisions[0].reason_code, "workspace_file_too_large")
        self.assertIn("workspace_file_too_large", joined)

    def test_workspace_file_image_payload_uses_text_then_image_url(self) -> None:
        prompt_messages = [{"role": "system", "content": "SYSTEM"}, {"role": "user", "content": "question"}]

        lane = active_document_prompt_lane.inject_active_document_prompt_lane(
            prompt_messages,
            [
                {
                    "source": "workspace_file_selection",
                    "document_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "workspace_file_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "filename": "image.png",
                    "media_type": "image/png",
                    "source_extension": ".png",
                    "byte_size": 8,
                    "media_kind": "image",
                    "content_sha256_12": "abc123def456",
                    "image_width": 40,
                    "image_height": 40,
                    "image_content": b"pngbytes",
                    "injectable": True,
                }
            ],
            model="openai/gpt-5.1",
            count_tokens_func=lambda _messages, _model: 10,
            max_tokens=1000,
        )

        content = next(message["content"] for message in prompt_messages if isinstance(message.get("content"), list))
        self.assertEqual(lane.injected_count, 1)
        self.assertIsInstance(content, list)
        self.assertEqual(content[0]["type"], "text")
        self.assertEqual(content[1]["type"], "image_url")
        self.assertNotIn("imageUrl", content[1])

    def test_workspace_file_selection_prompt_reads_text_bytes_from_disk(self) -> None:
        conversation_id = "11111111-1111-4111-8111-111111111111"
        folder_id = "22222222-2222-4222-8222-222222222222"
        file_id = "33333333-3333-4333-8333-333333333333"
        raw_text = "bonjour depuis le disque"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage_key = workspace_files_store.storage_key_for(folder_id, file_id, ".txt")
            workspace_files_store.write_file_bytes(root, storage_key, raw_text.encode("utf-8"))
            conn = _SelectionPromptConn(
                [
                    _selection_prompt_row(
                        conversation_id=conversation_id,
                        folder_id=folder_id,
                        file_id=file_id,
                        storage_key=storage_key,
                        byte_size=len(raw_text.encode("utf-8")),
                    )
                ]
            )
            logger = _CaptureLogger()

            documents = workspace_file_selection_prompt.list_selected_files_for_prompt(
                conversation_id,
                db_conn_func=lambda: conn,
                storage_root=root,
                logger=logger,
            )

        self.assertEqual(len(documents), 1)
        document = documents[0]
        self.assertEqual(document["source"], workspace_file_selections_store.SOURCE)
        self.assertEqual(document["document_id"], file_id)
        self.assertEqual(document["workspace_file_id"], file_id)
        self.assertEqual(document["workspace_folder_id"], folder_id)
        self.assertEqual(document["media_kind"], "text")
        self.assertTrue(document["injectable"])
        self.assertEqual(document["text_content"], raw_text)
        self.assertGreater(document["token_estimate"], 0)
        encoded = str(document)
        self.assertNotIn("storage_key", document)
        self.assertNotIn("internal_path", document)
        self.assertNotIn(storage_key, encoded)
        self.assertNotIn(str(root), encoded)

    def test_workspace_file_selection_prompt_reads_image_bytes_without_data_url(self) -> None:
        conversation_id = "11111111-1111-4111-8111-111111111111"
        folder_id = "22222222-2222-4222-8222-222222222222"
        file_id = "33333333-3333-4333-8333-333333333333"
        image_bytes = b"\x89PNG\r\nimagebytes"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage_key = workspace_files_store.storage_key_for(folder_id, file_id, ".png")
            workspace_files_store.write_file_bytes(root, storage_key, image_bytes)
            conn = _SelectionPromptConn(
                [
                    _selection_prompt_row(
                        conversation_id=conversation_id,
                        folder_id=folder_id,
                        file_id=file_id,
                        storage_key=storage_key,
                        display_name="capture.png",
                        media_kind="image",
                        mime_type="image/png",
                        source_extension=".png",
                        byte_size=len(image_bytes),
                        image_width=40,
                        image_height=30,
                    )
                ]
            )

            documents = workspace_file_selection_prompt.list_selected_files_for_prompt(
                conversation_id,
                db_conn_func=lambda: conn,
                storage_root=root,
                logger=_CaptureLogger(),
            )

        self.assertEqual(len(documents), 1)
        document = documents[0]
        self.assertEqual(document["source"], workspace_file_selections_store.SOURCE)
        self.assertEqual(document["media_kind"], "image")
        self.assertTrue(document["injectable"])
        self.assertEqual(document["image_content"], image_bytes)
        self.assertEqual(document["image_width"], 40)
        self.assertEqual(document["image_height"], 30)
        encoded = str(document)
        self.assertNotIn("storage_key", document)
        self.assertNotIn("internal_path", document)
        self.assertNotIn(storage_key, encoded)
        self.assertNotIn(str(root), encoded)
        self.assertNotIn("data:image", encoded)
        self.assertNotIn("base64", encoded)

    def test_workspace_file_selection_prompt_excludes_disk_missing_content_free(self) -> None:
        conversation_id = "11111111-1111-4111-8111-111111111111"
        folder_id = "22222222-2222-4222-8222-222222222222"
        file_id = "33333333-3333-4333-8333-333333333333"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage_key = workspace_files_store.storage_key_for(folder_id, file_id, ".txt")
            conn = _SelectionPromptConn(
                [
                    _selection_prompt_row(
                        conversation_id=conversation_id,
                        folder_id=folder_id,
                        file_id=file_id,
                        storage_key=storage_key,
                    )
                ]
            )
            logger = _CaptureLogger()

            documents = workspace_file_selection_prompt.list_selected_files_for_prompt(
                conversation_id,
                db_conn_func=lambda: conn,
                storage_root=root,
                logger=logger,
            )

        self.assertEqual(len(documents), 1)
        document = documents[0]
        self.assertFalse(document["injectable"])
        self.assertEqual(document["reason_code"], "workspace_file_disk_missing")
        self.assertNotIn("text_content", document)
        self.assertNotIn("image_content", document)
        logged = "\n".join(logger.lines)
        self.assertIn("workspace_files_selection_prompt_excluded", logged)
        self.assertIn("reason_code=workspace_file_disk_missing", logged)
        self.assertNotIn(storage_key, logged)
        self.assertNotIn(str(root), logged)

    def test_workspace_file_selection_prompt_excludes_ocr_required_without_running_lot4(self) -> None:
        conversation_id = "11111111-1111-4111-8111-111111111111"
        folder_id = "22222222-2222-4222-8222-222222222222"
        file_id = "33333333-3333-4333-8333-333333333333"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage_key = workspace_files_store.storage_key_for(folder_id, file_id, ".pdf")
            workspace_files_store.write_file_bytes(root, storage_key, b"%PDF scanned")
            conn = _SelectionPromptConn(
                [
                    _selection_prompt_row(
                        conversation_id=conversation_id,
                        folder_id=folder_id,
                        file_id=file_id,
                        storage_key=storage_key,
                        display_name="scan.pdf",
                        mime_type="application/pdf",
                        source_extension=".pdf",
                        byte_size=12,
                        file_status=workspace_files_store.STATUS_OCR_REQUIRED,
                    )
                ]
            )
            logger = _CaptureLogger()

            documents = workspace_file_selection_prompt.list_selected_files_for_prompt(
                conversation_id,
                db_conn_func=lambda: conn,
                storage_root=root,
                logger=logger,
            )

        self.assertEqual(len(documents), 1)
        document = documents[0]
        self.assertFalse(document["injectable"])
        self.assertEqual(document["reason_code"], "workspace_file_ocr_required")
        self.assertNotIn("text_content", document)
        self.assertNotIn("image_content", document)
        self.assertIn("reason_code=workspace_file_ocr_required", "\n".join(logger.lines))

    def test_chat_decision_record_routes_workspace_files_to_selection_store(self) -> None:
        class _SelectionStore:
            def __init__(self):
                self.injected = []
                self.excluded = []

            def record_selection_injected(self, conversation_id, file_id, *, turn_id):
                self.injected.append((conversation_id, file_id, turn_id))
                return True

            def record_selection_excluded(self, conversation_id, file_id, *, turn_id, reason_code):
                self.excluded.append((conversation_id, file_id, turn_id, reason_code))
                return True

        lane = active_document_prompt_lane.ActiveDocumentPromptLane(
            contract_message=None,
            content_message=None,
            decisions=(
                active_document_prompt_lane.ActiveDocumentPromptDecision(
                    document_id="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    workspace_file_id="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    filename="note.txt",
                    media_type="text/plain",
                    source_extension=".txt",
                    byte_size=4,
                    text_chars=4,
                    token_estimate=1,
                    text_sha256_12="abc123def456",
                    injected=True,
                    source="workspace_file_selection",
                ),
            ),
        )
        selection_store = _SelectionStore()

        chat_service._record_active_document_prompt_decisions(
            conversation={"id": "11111111-2222-4333-8444-555555555555"},
            lane=lane,
            turn_id="turn-1",
            active_documents_module=object(),
            workspace_file_selections_module=selection_store,
        )

        self.assertEqual(
            selection_store.injected,
            [("11111111-2222-4333-8444-555555555555", "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee", "turn-1")],
        )


if __name__ == "__main__":
    unittest.main()
