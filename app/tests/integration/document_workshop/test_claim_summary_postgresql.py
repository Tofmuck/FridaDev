"""Pre-final summary persistence with real pgvector, isolated synthetic data only."""
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from core import conv_store, conversation_turn_claims as claims
from memory import memory_store, summarizer
from tests.integration.document_workshop import test_claim_transport_postgresql as fixture
C, F, O, T = (fixture.C, fixture.F, fixture.O, fixture.T)

@unittest.skipUnless(os.environ.get('M3_VECTOR_PROOF_PG_SOCKET'), 'isolated pgvector proof required')
class ClaimSummaryPostgresqlTests(unittest.TestCase):
    conn = fixture.ClaimTransportPostgresqlTests.conn
    pipeline = fixture.ClaimTransportPostgresqlTests.pipeline
    post = fixture.ClaimTransportPostgresqlTests.post

    def setUp(self):
        fixture.ClaimTransportPostgresqlTests.setUp(self)
        with self.conn() as conn:
            conn.execute('CREATE EXTENSION vector;\n                CREATE TABLE summaries(id uuid PRIMARY KEY,conversation_id uuid,start_ts timestamptz,\n                    end_ts timestamptz,content text,embedding vector);\n                CREATE TABLE traces(conversation_id uuid,timestamp timestamptz,summary_id uuid);')
        self.original_summarize = summarizer.maybe_summarize
        v = conv_store.load_conversation(C, 'BACKEND SYSTEM PROMPT')
        for role in ('user', 'assistant', 'user', 'assistant', 'user', 'assistant'):
            conv_store.append_message(v, role, 'Synthetic prior dialogue')
        self.assertTrue(conv_store.save_conversation(v).ok)

    def test_late_summary_after_lease_loss_cannot_commit_or_start_main_exchange(self):
        arrived, release = (threading.Event(), threading.Event())
        calls = []

        def summary(turns):
            arrived.set()
            self.assertTrue(release.wait(10))
            return 'Synthetic summary'
        with self.pipeline(lambda *a, **k: calls.append(1) or fixture.SyntheticResponse()), patch.object(summarizer, 'maybe_summarize', self.original_summarize), patch.object(summarizer, 'summarize_conversation', summary), patch.object(summarizer.config, 'SUMMARY_THRESHOLD_TOKENS', 0), patch.object(summarizer.config, 'SUMMARY_KEEP_TURNS', 1), patch.object(memory_store, '_conn', self.conn), patch.object(memory_store, 'embed', lambda *a, **k: [0.1, 0.2]), ThreadPoolExecutor(1) as pool:
            future = pool.submit(self.post)
            try:
                self.assertTrue(arrived.wait(10))
                with self.conn() as conn:
                    conn.execute("UPDATE conversation_turn_claims SET lease_until=clock_timestamp()-interval '1 second'")
                successor = claims.acquire(conversation_id=C, turn_id=O, request_fingerprint='a' * 64)
            finally:
                release.set()
            response = future.result(timeout=10)
        with self.conn() as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM summaries').fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT count(*) FROM conversation_messages WHERE summarized_by IS NOT NULL').fetchone()[0], 0)
        self.assertEqual(calls, [])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(claims.read(O)['state'], 'active')
        claims.finish(successor.token, 'interrupted')

    def test_nominal_summary_and_snapshot_share_current_authority_without_content_change(self):
        with self.pipeline(lambda *a, **k: fixture.SyntheticResponse()), patch.object(summarizer, 'maybe_summarize', self.original_summarize), patch.object(summarizer, 'summarize_conversation', lambda turns: 'Synthetic summary'), patch.object(summarizer.config, 'SUMMARY_THRESHOLD_TOKENS', 0), patch.object(summarizer.config, 'SUMMARY_KEEP_TURNS', 1), patch.object(memory_store, '_conn', self.conn), patch.object(memory_store, 'embed', lambda *a, **k: [0.1, 0.2]):
            response = self.post()
        self.assertEqual(response.status_code, 200)
        with self.conn() as conn:
            summary = conn.execute('SELECT id,content FROM summaries').fetchone()
            self.assertEqual(summary[1], 'Synthetic summary')
            self.assertEqual(conn.execute('SELECT count(*) FROM conversation_messages WHERE summarized_by=%s', (str(summary[0]),)).fetchone()[0], 5)
        self.assertEqual(claims.read(T)['state'], 'succeeded')
