"""Document-only options, single schema ownership, and measured immutable bytes."""
import copy
import json
import unittest
from unittest.mock import patch

from core import llm_client, token_utils
from core.document_workshop_output_schema import document_response_format
from tests.unit.core import test_document_workshop_admission as base


class OutputAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.env = base.DocumentAdmissionTests(); self.env.setUp()
        self.addCleanup(self.env.doCleanups)

    def test_late_builder_and_schema_mutation_cannot_change_measured_body(self):
        real = llm_client.build_payload
        built, counted = [], []
        def builder(*args, **kw):
            payload = real(*args, **kw); built.append(payload); return payload
        def counter(messages, model):
            counted.append(copy.deepcopy(messages))
            built[0]['response_format']['json_schema']['schema'].clear()
            built[0]['provider']['require_parameters'] = False
            return token_utils.estimate_tokens(messages, model)
        with patch.object(llm_client, 'build_payload', builder):
            call = self.env.prepare(counter=counter)
        body = json.loads(call.body)
        self.assertEqual(body['response_format'], document_response_format())
        self.assertEqual(json.loads(counted[0][-1]['content']), body['response_format'])
        self.assertEqual(counted[0][:-1], body['messages'])
        self.assertTrue(body['provider']['require_parameters'])

    def test_competing_schema_is_refused_before_measure_or_transport_resolution(self):
        real = llm_client.build_payload
        counters = []
        with patch.object(llm_client, 'build_payload', lambda *a, **kw: {
                **real(*a, **kw), 'response_format': dict(type='json_object')}):
            with self.assertRaises(self.env.error) as caught:
                self.env.prepare(counter=lambda *_: counters.append(1) or 100)
        self.assertEqual(caught.exception.reason_code, 'document_payload_invalid')
        self.assertEqual(counters, []); self.env.headers.assert_not_called()

    def test_schema_estimation_mutation_refused_before_transport_resolution(self):
        def mutate(messages, _model):
            messages[-1]['content'] = '{}'
            return 10
        with self.assertRaises(self.env.error) as caught: self.env.prepare(counter=mutate)
        self.assertEqual(caught.exception.reason_code, 'document_estimation_input_mutated')
        self.env.headers.assert_not_called()

    def test_normal_options_and_overrides_survive_documentary_local_omission(self):
        for budget in (8192, 12345):
            normal_before = llm_client.build_payload([dict(role='user', content='Synthetic')], .3, .9, budget, stream=True)
            doc = json.loads(self.env.prepare(temperature=.3, top_p=.9).body)
            normal_after = llm_client.build_payload([dict(role='user', content='Synthetic')], .3, .9, budget, stream=True)
            self.assertEqual(normal_before, normal_after)
            self.assertEqual(normal_after['temperature'], .3); self.assertEqual(normal_after['top_p'], .9)
            self.assertEqual(normal_after['max_tokens'], budget)
            self.assertTrue(normal_after['stop'])
            self.assertNotIn('response_format', normal_after); self.assertNotIn('provider', normal_after)
            for key in ('temperature', 'top_p', 'stop'): self.assertNotIn(key, doc)
            self.assertEqual(doc['max_tokens'], 24000)

    def test_schema_cost_can_make_complete_input_exceed_unchanged_budget(self):
        counts = []
        def count(messages, model):
            counts.append(json.loads(messages[-1]['content']))
            # Nominal messages at the boundary; mandatory schema pushes over it.
            return 376000 + token_utils.estimate_tokens(messages[-1:], model)
        with self.assertRaises(self.env.error) as caught: self.env.prepare(counter=count)
        self.assertEqual(caught.exception.reason_code, 'document_estimated_context_limit')
        self.assertEqual(counts, [document_response_format()]); self.env.headers.assert_not_called()
