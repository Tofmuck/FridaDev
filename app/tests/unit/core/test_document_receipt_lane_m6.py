"""Receipt lane is late metadata, distinct from documents and canonical dialogue."""
import importlib
import importlib.util
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from core import chat_main_payload, continuity_capsule
from biblio.chat_runtime import BiblioChatResult
from agenda.chat_runtime import AgendaChatResult
from observability import main_payload_manifest
from observability.observability_payload_guard import guard_payload

C='11111111-1111-4111-8111-111111111111'
F='22222222-2222-4222-8222-222222222222'

class ReceiptLaneM6Tests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('core.document_workshop_receipts'), 'M6 metadata lane missing')
        self.module=importlib.import_module('core.document_workshop_receipts')
        self.receipt=dict(id=C,action_id=C,conversation_id=C,workspace_folder_id=F,workspace_file_id=F,
            revision_id=C,artifact_id=C,request_turn_id=C,confirmation_turn_id=F,operation='create',format='markdown',
            name='RECEIPT_MARKER.md',relative_path='Documents/RECEIPT_MARKER.md',creation_author='frida',revision_author='frida',
            product_link=f'/api/workspace-folders/{F}/files/{F}/content',confirmed_at='2026-10-07T00:00:00+00:00',
            created_at='2026-10-07T00:00:01+00:00',canonical_sha256='a'*64,content_sha256='b'*64,
            nextcloud_file_id='42',nextcloud_etag='"v1"',publication_evidence='historical')
        self.conversation=dict(id=C,workspace_folder_id=F,messages=[dict(role='user',content='REAL_WORD_MARKER')])

    def test_lane_only_appends_metadata_and_does_not_change_canonical_conversation(self):
        messages=[dict(role='user',content='REAL_WORD_MARKER')]
        with patch.object(self.module,'latest',return_value=self.receipt | dict(canonical='DOCUMENT_MARKER',journal='JOURNAL_MARKER',request='REQUEST_COPY')):
            lane=self.module.inject_receipt_lane(messages,self.conversation)
        self.assertEqual(self.conversation['messages'],[dict(role='user',content='REAL_WORD_MARKER')])
        self.assertEqual(len(messages),2); self.assertEqual(messages[1]['role'],'system')
        self.assertIn('RECEIPT_MARKER',messages[1]['content'])
        for marker in ('DOCUMENT_MARKER','JOURNAL_MARKER','REQUEST_COPY'):self.assertNotIn(marker,str(messages))
        self.assertEqual(lane.injected_count,1)
        self.assertEqual(lane.message_sources[1]['logical_roles'],['document_receipt_lane'])
        self.assertEqual(lane.message_sources[1]['content_kind'],'document_receipt_metadata')

    def test_missing_receipt_or_read_failure_never_invents_metadata(self):
        for value in (None,RuntimeError('synthetic unavailable')):
            messages=[dict(role='user',content='REAL_WORD_MARKER')]
            options={'side_effect':value} if isinstance(value,Exception) else {'return_value':value}
            with patch.object(self.module,'latest',**options):lane=self.module.inject_receipt_lane(messages,self.conversation)
            self.assertEqual(len(messages),1);self.assertEqual(lane.injected_count,0)
            self.assertEqual(lane.status,'failed' if isinstance(value,Exception) else 'not_selected')

    def test_normal_payload_has_receipt_before_terminal_capsule_and_exact_manifest(self):
        manifests=[]
        def build(*_,**__):return [dict(role='system',content='System'),dict(role='user',content='REAL_WORD_MARKER')]
        with patch.object(self.module,'latest',return_value=self.receipt),patch.object(chat_main_payload.main_payload_manifest,'emit_main_payload_manifest',lambda value,**_:manifests.append(value)):
            result=chat_main_payload.prepare_main_payload(conversation=self.conversation,user_msg='REAL_WORD_MARKER',
                runtime_main_model='openai/gpt-5.1',now_iso_value='2026-10-07T00:00:00+00:00',memory_traces=[],context_hints=[],
                web_runtime_payload={},web_search_module=SimpleNamespace(),admin_logs_module=SimpleNamespace(),
                document_prompt_read=SimpleNamespace(documents=[],status='not_selected',reason_code=''),
                workspace_notes_read=SimpleNamespace(note_reads=[],status='not_selected',reason_code='',requested_count=0,invalid_requested_count=0,over_limit_count=0),
                biblio_result=BiblioChatResult(enabled=False,used=False,reason_code="biblio_disabled",query_kind="not_requested",observability_payload={}),agenda_result=AgendaChatResult(enabled=False,used=False,status="disabled",reason_code="agenda_disabled",observability_payload={}),adobe_request=SimpleNamespace(active=False),adobe_context=None,
                validated_result=None,assistant_output_policy=None,hermeneutic_node_runtime={},hermeneutic_judgment_block='',
                biblio_recent_dialogue=[],agenda_recent_dialogue=[],summary_payload={},identity_payload={},recent_context_payload={},recent_window_payload={},
                current_mode='default',memory_retrieved={},memory_arbitration={},temperature=.7,top_p=1,max_tokens=8192,stream_req=False,
                config_module=SimpleNamespace(MAX_TOKENS=400000,CONTINUITY_CAPSULE_ENABLED=True,CONTINUITY_CAPSULE_TEXT="Synthetic capsule"),count_tokens_func=lambda msgs,model:len(str(msgs)),
                active_document_prompt_max_tokens=1000,record_active_document_prompt_decisions_func=lambda **_:None,
                workspace_file_selections_module=SimpleNamespace(),logger=None,conv_store_module=SimpleNamespace(build_prompt_messages=build))
        entries=[e for e in manifests[0]['messages'] if 'document_receipt_lane' in e['logical_roles']]
        self.assertEqual(len(entries),1)
        self.assertIn('RECEIPT_MARKER',result.prompt_messages[entries[0]['index']]['content'])
        self.assertEqual(manifests[0]['lane_statuses']['document_receipt_lane']['injected_count'],1)
        self.assertEqual(manifests[0]['lane_statuses']['document_lane']['injected_count'],0)
        self.assertIn('Synthetic capsule',result.prompt_messages[-1]['content'])
        self.assertLess(entries[0]['index'],len(result.prompt_messages)-1)
        self.assertTrue(guard_payload(manifests[0]).accepted)
        self.assertEqual(manifests[0]['lane_conflicts']['message_lane_status_mismatch_count'],0)
        self.assertEqual(manifests[0]['budgets']['prompt']['estimated_prompt_tokens'],len(str(result.prompt_messages)))
