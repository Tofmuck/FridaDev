"""Explicit isolated Writer proof through the delivered client and real M3/M5.

Usage: python -B -m tests.support.probe_document_renderer_m8a SOCKET PINS
Requires M5_PROOF_PG_SOCKET pointing only to a disposable PostgreSQL instance.
No model, DAV, live service bootstrap or public document format is involved.
"""
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

from core import document_renderer_contract as c, document_rendering as rendering
from core.chat_turn_reservation import ChatReservation
from core.document_renderer_client import DocumentRendererClient
from tests.integration.document_workshop import test_execution_postgresql as fixture
from tests.unit.core.test_document_workshop_canonical_paths import canonical, span


def main():
    socket_path, pins_path = sys.argv[1:]
    pins = c.validate_engine(c.read_json(Path(pins_path).read_bytes()))
    value = canonical('Preuve interne Writer M8-A.')
    value['blocks'].append(dict(type='list', ordered=True,
        items=[[span('Premier item.')], [span('Second item.')]]))
    fx = fixture.ExecutionPostgresqlTests(methodName='runTest')
    reservation = None
    started = time.monotonic()
    try:
        with patch.object(fixture, 'canonical', lambda: value):
            fx.setUp()
        run = fx.store.begin(fx.request_turn, fx.body())
        reservation = ChatReservation(run.token)
        client = DocumentRendererClient(socket_path=socket_path)
        session = rendering.RenderingSession(client=client, expected_engine=pins)
        result = rendering.render_confirmed(run, 'docx', session)
        assert result.release['state'] == 'released' and result.release['workspace_removed'] is True
        assert result.manifest['job_id'] == run.token.turn_id
        assert result.manifest['revision_id'] == run.action['revision_id']
        snapshot = fx.rows('SELECT manifest,docx,pdf FROM document_renderer_snapshots WHERE action_id=%s::uuid', (run.action['id'],))
        assert snapshot == [(result.result.manifest_bytes, result.docx, result.pdf)]
        assert fx.rows('SELECT count(*) FROM document_execution_journal') == [(0,)]
        assert fx.rows('SELECT count(*) FROM document_receipts') == [(0,)]
        fx.assert_no_transaction()
        fx.store.finish(run, 'failed', 'document_format_unavailable')
        reservation.stop_after_commit()
        print(json.dumps(dict(case='m8a_confirmed_compact_list', renderer='real_isolated_m8s',
            image_digest=pins['image_digest'], expected_engine_sha256=c.digest(c.json_bytes(pins)),
            pages=result.manifest['page_evidence']['writer_pages'],
            docx_bytes=len(result.docx), pdf_bytes=len(result.pdf),
            docx_sha256=c.digest(result.docx), pdf_sha256=c.digest(result.pdf),
            durable_pair_matches=True, release_acknowledged=True, journal=0, receipts=0,
            no_model=True, no_dav=True, wall_seconds=round(time.monotonic()-started, 3))))
    finally:
        if reservation is not None: reservation.close()
        fx.doCleanups()


if __name__ == '__main__': main()
