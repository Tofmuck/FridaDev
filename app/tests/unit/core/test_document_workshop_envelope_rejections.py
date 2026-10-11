"""Closed first-guard identity; no response data can cross the diagnostic sink."""
import json
import unittest

from core.document_workshop_contract import DocumentWorkshopError
from core.document_workshop_envelope import read_document_envelope
from core.document_canonical import strict_json_loads
from observability.observability_payload_guard import guard_payload
from tests.unit.core.test_document_workshop_output_schema import envelope


class EnvelopeRejectionTests(unittest.TestCase):
    def rejected(self, raw, site):
        with self.assertRaises(DocumentWorkshopError) as caught: read_document_envelope(raw)
        self.assertEqual(str(caught.exception), 'document_envelope_invalid')
        self.assertEqual(caught.exception.envelope_rejection, site)
        self.assertTrue(guard_payload(dict(envelope_rejection=site), stage='document_preparation').accepted)
        self.assertNotIn('PRIVATE_', repr(caught.exception))

    def test_parsing_strict_unicode_input_and_first_guard(self):
        for raw, site in ((None, 'raw_type'), ('\ud800', 'raw_unicode'), ('{PRIVATE_SENTINEL', 'json_syntax'),
                          ('{"a":1,"a":2}', 'json_duplicate_key'), ('{"a":NaN}', 'json_nonfinite'),
                          ('{"a":Infinity}', 'json_nonfinite'), ('[]', 'root_shape')):
            with self.subTest(site=site): self.rejected(raw, site)
        for raw in ('{"a":1,"a":2}', 'NaN', '{'):
            with self.assertRaises(DocumentWorkshopError) as caught: strict_json_loads(raw)
            self.assertEqual(str(caught.exception), 'document_canonical_invalid')
        value = envelope(); value['schema_version'] = 2; value['surface_text'] = ''
        self.rejected(json.dumps(value), 'root_version')

    def test_structure_surface_sources_and_limitations(self):
        cases = [
            (('schema_version',), True, 'root_version'), (('status',), 'PRIVATE_SENTINEL', 'root_status'),
            (('surface_text',), 1, 'surface_type'), (('surface_text',), ' ', 'surface_blank'),
            (('surface_text',), 'x'*2001, 'surface_limit'), (('surface_text',), '\u0000', 'surface_unicode'),
            (('surface_text',), '{"schema_version":1,"profile":"frida_document_v1","blocks":[]}', 'surface_protocol'),
            (('proposal',), None, 'proposal_shape'),
            (('proposal','operation'), 'PRIVATE_SENTINEL', 'operation'), (('proposal','format'), 'pdf', 'format'),
            (('proposal','source_file_ids'), {}, 'sources_type'), (('proposal','source_file_ids'), [1], 'source_type'),
            (('proposal','source_file_ids'), ['PRIVATE_SENTINEL'], 'source_uuid'),
            (('proposal','source_file_ids'), ['11111111-1111-4111-8111-111111111111']*2, 'source_duplicate'),
            (('proposal','limitations'), {}, 'limitations_type'), (('proposal','limitations'), ['PRIVATE_SENTINEL'], 'limitation_code'),
            (('proposal','limitations'), ['pdf_unavailable']*2, 'limitation_duplicate'),
        ]
        for path, bad, site in cases:
            value = envelope(); target = value
            for key in path[:-1]: target = target[key]
            target[path[-1]] = bad
            with self.subTest(site=site): self.rejected(json.dumps(value), site)
        value = envelope(); value['status'] = 'clarify'
        self.rejected(json.dumps(value), 'proposal_for_status')
        value = envelope(); value['proposal']['operation'] = 'copy'
        self.rejected(json.dumps(value), 'copy_source_required')

    def test_closed_sink_rejects_untrusted_values_extra_keys_and_other_stage(self):
        self.assertTrue(guard_payload(dict(envelope_rejection='json_syntax'), stage='document_preparation').accepted)
        for value in ('PRIVATE_SENTINEL', '', None, 1, {}, ['json_syntax']):
            decision = guard_payload(dict(envelope_rejection=value), stage='document_preparation')
            self.assertFalse(decision.accepted); self.assertNotIn('PRIVATE_', str(decision.payload))
        self.assertFalse(guard_payload(dict(envelope_rejection='json_syntax', content='PRIVATE_SENTINEL'), stage='document_preparation').accepted)
        self.assertFalse(guard_payload(dict(envelope_rejection='json_syntax'), stage='other').accepted)

    def test_other_contract_codes_never_become_envelope_rejections(self):
        for field, value, reason in (('relative_path', '../synthetic.docx', 'document_path_invalid'),
                                     ('canonical', {}, 'document_canonical_invalid')):
            data = envelope(); data['proposal'][field] = value
            with self.assertRaises(DocumentWorkshopError) as caught: read_document_envelope(json.dumps(data))
            self.assertEqual(caught.exception.reason_code, reason)
            self.assertIsNone(caught.exception.envelope_rejection)
