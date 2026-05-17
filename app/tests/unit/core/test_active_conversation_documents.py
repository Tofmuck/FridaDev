from __future__ import annotations

import unittest
import sys
import types
from datetime import datetime, timezone

try:
    import psycopg  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - local host may not have repo deps.
    sys.modules["psycopg"] = types.ModuleType("psycopg")
    rows_module = types.ModuleType("psycopg.rows")
    rows_module.dict_row = object()
    sys.modules["psycopg.rows"] = rows_module

from core import active_conversation_documents as active_docs


CONV_A = "11111111-1111-1111-1111-111111111111"
CONV_B = "22222222-2222-2222-2222-222222222222"
DOC_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
DOC_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
NOW = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 5, 16, 12, 5, tzinfo=timezone.utc)


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self._one = None
        self._many = []
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        self.conn.queries.append(query)
        params = params or ()
        compact = " ".join(str(query).lower().split())
        self._one = None
        self._many = []
        self.rowcount = 0

        if compact.startswith("create ") or compact.startswith("alter ") or compact.startswith("create index"):
            return

        if compact.startswith("insert into active_conversation_documents"):
            row = {
                "document_id": params[0],
                "conversation_id": params[1],
                "filename": params[2],
                "media_type": params[3],
                "source_extension": params[4],
                "byte_size": params[5],
                "text_chars": params[6],
                "text_sha256_12": params[7],
                "token_estimate": params[8],
                "status": params[9],
                "text_content": params[10],
                "created_at": params[11],
                "deactivated_at": None,
                "last_injected_turn_id": None,
                "last_excluded_turn_id": None,
                "last_excluded_reason_code": None,
                "ocr_applied": params[12],
                "ocr_engine": params[13],
                "ocr_languages": params[14],
                "ocr_duration_ms": params[15],
            }
            self.conn.rows[row["document_id"]] = row
            self._one = self._project(row, include_text=False)
            self.rowcount = 1
            return

        if compact.startswith("select") and "from active_conversation_documents" in compact:
            conv_id = params[0]
            include_text = "text_content" in compact
            if "and document_id = %s::uuid" in compact:
                doc_id = params[1]
                row = self.conn.rows.get(doc_id)
                if row and self._is_active(row) and row["conversation_id"] == conv_id:
                    self._one = self._project(row, include_text=include_text)
                return

            rows = [
                self._project(row, include_text=include_text)
                for row in self.conn.rows.values()
                if self._is_active(row) and row["conversation_id"] == conv_id
            ]
            rows.sort(key=lambda row: (row["created_at"], row["filename"]))
            self._many = rows
            return

        if compact.startswith("update active_conversation_documents") and "set last_injected_turn_id" in compact:
            turn_id, conv_id, doc_id = params
            row = self.conn.rows.get(doc_id)
            if row and self._is_active(row) and row["conversation_id"] == conv_id:
                row["last_injected_turn_id"] = turn_id
                row["last_excluded_turn_id"] = ""
                row["last_excluded_reason_code"] = ""
                self.rowcount = 1
            return

        if compact.startswith("update active_conversation_documents") and "set last_excluded_turn_id" in compact:
            turn_id, reason_code, conv_id, doc_id = params
            row = self.conn.rows.get(doc_id)
            if row and self._is_active(row) and row["conversation_id"] == conv_id:
                row["last_excluded_turn_id"] = turn_id
                row["last_excluded_reason_code"] = reason_code
                self.rowcount = 1
            return

        if compact.startswith("update active_conversation_documents") and "set status" in compact:
            status, deactivated_at, reason_code, conv_id, doc_id = params
            row = self.conn.rows.get(doc_id)
            if row and self._is_active(row) and row["conversation_id"] == conv_id:
                row["status"] = status
                row["deactivated_at"] = deactivated_at
                row["last_excluded_reason_code"] = reason_code
                self.rowcount = 1
            return

        if compact.startswith("delete from active_conversation_documents"):
            if "deactivated_at is not null" in compact and "conversation_id = %s::uuid" in compact:
                conv_id, older_than = params
                to_delete = [
                    doc_id
                    for doc_id, row in self.conn.rows.items()
                    if row["conversation_id"] == conv_id
                    and row["deactivated_at"] is not None
                    and row["deactivated_at"] < older_than
                ]
            elif "deactivated_at is not null" in compact:
                older_than = params[0]
                to_delete = [
                    doc_id
                    for doc_id, row in self.conn.rows.items()
                    if row["deactivated_at"] is not None and row["deactivated_at"] < older_than
                ]
            else:
                conv_id = params[0]
                to_delete = [
                    doc_id
                    for doc_id, row in self.conn.rows.items()
                    if row["conversation_id"] == conv_id
                ]
            for doc_id in to_delete:
                self.conn.rows.pop(doc_id, None)
            self.rowcount = len(to_delete)
            return

        raise AssertionError(f"Unexpected SQL in fake cursor: {query}")

    def fetchone(self):
        return self._one

    def fetchall(self):
        return list(self._many)

    def _project(self, row, *, include_text):
        projected = {
            "document_id": row["document_id"],
            "conversation_id": row["conversation_id"],
            "filename": row["filename"],
            "media_type": row["media_type"],
            "source_extension": row["source_extension"],
            "byte_size": row["byte_size"],
            "text_chars": row["text_chars"],
            "text_sha256_12": row["text_sha256_12"],
            "token_estimate": row["token_estimate"],
            "status": row["status"],
            "created_at": row["created_at"],
            "deactivated_at": row["deactivated_at"],
            "last_injected_turn_id": row["last_injected_turn_id"],
            "last_excluded_turn_id": row["last_excluded_turn_id"],
            "last_excluded_reason_code": row["last_excluded_reason_code"],
            "ocr_applied": row["ocr_applied"],
            "ocr_engine": row["ocr_engine"],
            "ocr_languages": row["ocr_languages"],
            "ocr_duration_ms": row["ocr_duration_ms"],
        }
        if include_text:
            projected["text_content"] = row["text_content"]
        return projected

    def _is_active(self, row):
        return row["status"] == active_docs.ACTIVE_STATUS and row["deactivated_at"] is None


class FakeConn:
    def __init__(self):
        self.rows = {}
        self.queries = []
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, *args, **kwargs):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1


class ActiveConversationDocumentsTest(unittest.TestCase):
    def setUp(self):
        self.conn = FakeConn()
        self.conn_factory = lambda: self.conn

    def activate(
        self,
        conversation_id=CONV_A,
        document_id=DOC_A,
        text="texte entier du fichier",
        **kwargs,
    ):
        return active_docs.activate_document(
            conversation_id,
            document_id=document_id,
            filename="note.md",
            media_type="text/markdown",
            source_extension="MD",
            byte_size=123,
            token_estimate=8,
            text_content=text,
            conn_factory=self.conn_factory,
            now_func=lambda: NOW,
            **kwargs,
        )

    def test_init_db_creates_dedicated_conversation_scoped_table(self):
        self.assertTrue(active_docs.init_db(conn_factory=self.conn_factory))

        sql = "\n".join(self.conn.queries).lower()
        self.assertIn("active_conversation_documents", sql)
        self.assertIn("references conversations(id) on delete cascade", sql)
        self.assertNotIn("memory_traces", sql)
        self.assertNotIn("identity", sql)
        self.assertNotIn("summaries", sql)

    def test_active_document_survives_two_prompt_reads_without_exposing_text_in_metadata(self):
        metadata = self.activate(text="texte exact garde cote serveur")
        self.assertIsNotNone(metadata)
        self.assertNotIn("text_content", metadata)
        self.assertEqual(metadata["conversation_id"], CONV_A)
        self.assertEqual(metadata["source"], "active_conversation_documents")
        self.assertEqual(metadata["text_chars"], len("texte exact garde cote serveur"))
        self.assertEqual(metadata["source_extension"], "md")

        visible_metadata = active_docs.list_active_documents(CONV_A, conn_factory=self.conn_factory)
        self.assertEqual(len(visible_metadata), 1)
        self.assertNotIn("text_content", visible_metadata[0])

        first_turn = active_docs.list_active_documents_for_prompt(CONV_A, conn_factory=self.conn_factory)
        second_turn = active_docs.list_active_documents_for_prompt(CONV_A, conn_factory=self.conn_factory)
        self.assertEqual(len(first_turn), 1)
        self.assertEqual(first_turn, second_turn)
        self.assertEqual(first_turn[0]["text_content"], "texte exact garde cote serveur")
        self.assertEqual(first_turn[0]["status"], "active")
        self.assertIs(first_turn[0]["ocr_applied"], False)

    def test_ocr_metadata_is_persisted_content_free(self):
        metadata = self.activate(
            text="texte OCRise",
            ocr_applied=True,
            ocr_engine="stirling-pdf",
            ocr_languages="fra+eng+deu",
            ocr_duration_ms=42,
        )

        self.assertIs(metadata["ocr_applied"], True)
        self.assertEqual(metadata["ocr_engine"], "stirling-pdf")
        self.assertEqual(metadata["ocr_languages"], "fra+eng+deu")
        self.assertEqual(metadata["ocr_duration_ms"], 42)
        self.assertNotIn("text_content", metadata)

        prompt_doc = active_docs.get_active_document_for_prompt(
            CONV_A,
            DOC_A,
            conn_factory=self.conn_factory,
        )
        self.assertIsNotNone(prompt_doc)
        self.assertIs(prompt_doc["ocr_applied"], True)
        self.assertEqual(prompt_doc["ocr_engine"], "stirling-pdf")
        self.assertEqual(prompt_doc["text_content"], "texte OCRise")

    def test_manual_remove_hides_document_from_following_turns(self):
        self.activate()

        removed = active_docs.deactivate_document(
            CONV_A,
            DOC_A,
            reason_code="manual_remove",
            conn_factory=self.conn_factory,
            now_func=lambda: LATER,
        )

        self.assertTrue(removed)
        self.assertEqual(active_docs.list_active_documents(CONV_A, conn_factory=self.conn_factory), [])
        self.assertEqual(active_docs.list_active_documents_for_prompt(CONV_A, conn_factory=self.conn_factory), [])
        row = self.conn.rows[DOC_A]
        self.assertEqual(row["status"], "inactive")
        self.assertEqual(row["last_excluded_reason_code"], "manual_remove")

    def test_conversation_scope_prevents_cross_conversation_reuse(self):
        self.activate(conversation_id=CONV_A, document_id=DOC_A, text="document A")
        self.activate(conversation_id=CONV_B, document_id=DOC_B, text="document B")

        docs_a = active_docs.list_active_documents_for_prompt(CONV_A, conn_factory=self.conn_factory)
        docs_b = active_docs.list_active_documents_for_prompt(CONV_B, conn_factory=self.conn_factory)

        self.assertEqual([doc["document_id"] for doc in docs_a], [DOC_A])
        self.assertEqual([doc["document_id"] for doc in docs_b], [DOC_B])
        self.assertIsNone(
            active_docs.get_active_document_for_prompt(
                CONV_B,
                DOC_A,
                conn_factory=self.conn_factory,
            )
        )
        self.assertFalse(
            active_docs.deactivate_document(
                CONV_B,
                DOC_A,
                conn_factory=self.conn_factory,
                now_func=lambda: LATER,
            )
        )
        self.assertEqual(len(active_docs.list_active_documents_for_prompt(CONV_A, conn_factory=self.conn_factory)), 1)

    def test_delete_and_purge_are_scoped_cleanup_helpers(self):
        self.activate(conversation_id=CONV_A, document_id=DOC_A, text="document A")
        self.activate(conversation_id=CONV_B, document_id=DOC_B, text="document B")

        deleted = active_docs.delete_conversation_documents(CONV_A, conn_factory=self.conn_factory)

        self.assertEqual(deleted, 1)
        self.assertEqual(active_docs.list_active_documents_for_prompt(CONV_A, conn_factory=self.conn_factory), [])
        self.assertEqual(len(active_docs.list_active_documents_for_prompt(CONV_B, conn_factory=self.conn_factory)), 1)

        active_docs.deactivate_document(
            CONV_B,
            DOC_B,
            conn_factory=self.conn_factory,
            now_func=lambda: LATER,
        )
        purged = active_docs.purge_deactivated_documents(
            older_than=datetime(2026, 5, 16, 12, 10, tzinfo=timezone.utc),
            conn_factory=self.conn_factory,
        )
        self.assertEqual(purged, 1)
        self.assertEqual(self.conn.rows, {})

    def test_record_document_injected_updates_only_scoped_active_document(self):
        self.activate(conversation_id=CONV_A, document_id=DOC_A)

        self.assertFalse(
            active_docs.record_document_injected(
                CONV_B,
                DOC_A,
                turn_id="turn-b",
                conn_factory=self.conn_factory,
            )
        )
        self.assertTrue(
            active_docs.record_document_injected(
                CONV_A,
                DOC_A,
                turn_id="turn-a",
                conn_factory=self.conn_factory,
            )
        )
        self.assertEqual(self.conn.rows[DOC_A]["last_injected_turn_id"], "turn-a")
        self.assertEqual(self.conn.rows[DOC_A]["last_excluded_turn_id"], "")
        self.assertEqual(self.conn.rows[DOC_A]["last_excluded_reason_code"], "")

    def test_record_document_excluded_updates_only_scoped_active_document(self):
        self.activate(conversation_id=CONV_A, document_id=DOC_A)

        self.assertFalse(
            active_docs.record_document_excluded(
                CONV_B,
                DOC_A,
                turn_id="turn-b",
                reason_code="document_too_large_for_turn",
                conn_factory=self.conn_factory,
            )
        )
        self.assertTrue(
            active_docs.record_document_excluded(
                CONV_A,
                DOC_A,
                turn_id="turn-a",
                reason_code="document_too_large_for_turn",
                conn_factory=self.conn_factory,
            )
        )
        self.assertEqual(self.conn.rows[DOC_A]["last_excluded_turn_id"], "turn-a")
        self.assertEqual(self.conn.rows[DOC_A]["last_excluded_reason_code"], "document_too_large_for_turn")


if __name__ == "__main__":
    unittest.main()
