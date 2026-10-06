"""Admission/manifest boundary: occurrence metadata stays outside frozen JSON."""
import copy
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from core import llm_client, token_utils
from observability import main_payload_manifest
from observability.observability_payload_guard import guard_payload
from tests.unit.core import test_document_workshop_admission as fixture


class DocumentProvenanceBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.env = fixture.DocumentAdmissionTests()
        self.addCleanup(self.env.doCleanups)
        self.env.setUp()

    def admission_manifest(self, *, response_format=False):
        data = 'RESUME INDICES CONTEXTUELS synthetic source data'
        messages = [dict(role='user', content='Synthetic request'),
                    dict(role='system', content=data), dict(role='system', content=data)]
        indexed = {1: dict(logical_roles=['document_lane'], origin='core.workspace_document_content_service',
            origin_stage='document_preparation_sources', content_kind='document_source_data')}
        manifests, measured = [], []
        original = llm_client.build_payload
        outside = dict(type='json_schema', json_schema=dict(name='synthetic', schema=dict(description='estimate only')))
        def builder(*args, **kwargs):
            result = original(*args, **kwargs)
            if response_format:
                result['response_format'] = outside
            return json.loads(json.dumps(result))
        def counter(final_messages, model):
            measured.append(copy.deepcopy(final_messages))
            estimate = token_utils.estimate_tokens(final_messages, model)
            manifest = main_payload_manifest.build_main_payload_manifest(conversation={}, prompt_messages=final_messages,
                runtime_main_model=model, temperature=.7, top_p=1, max_tokens=24000, stream_req=True,
                assistant_output_policy=None, assistant_response_override=None, count_tokens_func=lambda *_: estimate,
                active_document_lane=SimpleNamespace(decisions=(SimpleNamespace(media_kind='text', text_chars=len(data), injected=True),),
                    injected_count=1, read_status='ok'), message_sources=indexed)
            manifests.append(manifest)
            # Caller objects have already crossed the JSON boundary. Altering
            # them cannot rewrite the admitted occurrence or request body.
            messages[1]['content'] = 'caller replacement'
            return estimate
        with patch.object(llm_client, 'build_payload', side_effect=builder):
            call = self.env.prepare(messages=messages, counter=counter)
        body = json.loads(call.body)
        self.assertEqual(len(measured), 1)
        self.assertEqual(body['messages'][1], dict(role='system', content=data))
        self.assertEqual(body['messages'][1], body['messages'][2])
        self.assertTrue(all(set(message)=={'role','content'} for message in body['messages']))
        entry, neighbor = manifests[0]['messages'][1:3]
        self.assertEqual(entry['index'], 1)
        self.assertEqual(entry['logical_roles'], ['document_lane'])
        self.assertEqual(entry['origin'], 'core.workspace_document_content_service')
        self.assertEqual(entry['origin_stage'], 'document_preparation_sources')
        self.assertEqual(entry['content_kind'], 'document_source_data')
        self.assertEqual(neighbor['logical_roles'], ['summary'])
        self.assertEqual(sum('document_lane' in m['logical_roles'] for m in manifests[0]['messages']), 1)
        self.assertTrue(guard_payload(manifests[0]).accepted)
        self.assertNotIn(data, json.dumps(manifests))
        self.assertEqual(measured[0][:len(body['messages'])], body['messages'])
        self.assertEqual(len(measured[0]), len(body['messages'])+int(response_format))
        if response_format:
            self.assertEqual(json.loads(measured[0][-1]['content']), outside)
            self.assertEqual(body['response_format'], outside)
            self.assertNotIn('document_lane', manifests[0]['messages'][-1]['logical_roles'])
        self.assertEqual(call.admission.estimated_input_tokens, token_utils.estimate_tokens(measured[0], body['model']))

    def test_indexed_source_survives_json_clones_and_identical_neighbor(self):
        self.admission_manifest()

    def test_response_format_estimation_adapter_does_not_change_sent_source_index(self):
        self.admission_manifest(response_format=True)
