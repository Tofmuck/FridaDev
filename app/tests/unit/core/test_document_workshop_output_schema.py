"""Offline JSON Schema corpus, independent of provider acceptance/generation."""
import copy
import importlib
import json
import unittest

from core.document_workshop_contract import DocumentWorkshopError
from core.document_workshop_envelope import read_document_envelope
from tests.unit.core.test_document_workshop_canonical_paths import canonical, span


def envelope():
    value = dict(schema_version=1, status='prepared', surface_text='Proposition synthétique.',
                 proposal=dict(operation='create', format='docx', relative_path='Documents/Synthetic.docx',
                               source_file_ids=[], limitations=[], canonical=canonical()))
    value['proposal']['canonical']['blocks'] = [
        dict(type='heading', level=2, spans=[span('Titre')]),
        dict(type='paragraph', spans=[dict(text='Gras italique', bold=True, italic=True, link=None)]),
        dict(type='quote', spans=[dict(text='Lien', bold=False, italic=False, link='https://example.invalid/')]),
        dict(type='list', ordered=False, items=[[span('Alpha')], [span('Bêta')]]),
        dict(type='list', ordered=True, items=[[span('Un')]]),
        dict(type='table', rows=[[[span('A')], [span('1')]], [[span('B')], []]]),
        dict(type='page_break'),
    ]
    return value


class DocumentOutputSchemaTests(unittest.TestCase):
    def setUp(self):
        import jsonschema
        self.schema_module = importlib.import_module('core.document_workshop_output_schema')
        self.format = self.schema_module.document_response_format()
        self.schema = self.format['json_schema']['schema']
        jsonschema.Draft202012Validator.check_schema(self.schema)
        self.validator = jsonschema.Draft202012Validator(self.schema)

    def test_all_statuses_operations_formats_blocks_and_rich_shapes(self):
        for status in ('prepared', 'clarify', 'refuse'):
            for operation in ('create', 'copy', 'update'):
                for fmt, suffix in (('markdown', 'md'), ('docx', 'docx'), ('pdf','pdf')):
                    value = envelope(); value['status'] = status
                    proposal = value['proposal']
                    proposal.update(operation=operation, format=fmt, relative_path='Documents/Synthetic.' + suffix,
                                    source_file_ids=['11111111-1111-4111-8111-111111111111'])
                    if status != 'prepared': value['proposal'] = None
                    with self.subTest(status=status, operation=operation, format=fmt):
                        self.validator.validate(value)
                        self.assertEqual(read_document_envelope(json.dumps(value)).as_dict(), value)

    def test_closed_required_variants_enums_types_and_references(self):
        cases = []
        for path in ((), ('proposal',), ('proposal', 'canonical'), ('proposal', 'canonical', 'blocks', 0),
                     ('proposal', 'canonical', 'blocks', 0, 'spans', 0)):
            for kind in ('extra', 'missing'):
                value = envelope(); target = value
                for key in path: target = target[key]
                if kind == 'extra': target['unexpected'] = None
                else: target.pop(next(iter(target)))
                cases.append(value)
        for key, bad in (('schema_version', True), ('schema_version', 2), ('status', 'other'), ('surface_text', 3)):
            value = envelope(); value[key] = bad; cases.append(value)
        for key, bad in (('operation', 'delete'), ('format', 'odt'), ('source_file_ids', [1]),
                         ('limitations', ['other']), ('canonical', None)):
            value = envelope(); value['proposal'][key] = bad; cases.append(value)
        for bad in (dict(type='page_break', spans=None), dict(type='heading', level=7, spans=[]),
                    dict(type='list', ordered=1, items=[]), dict(type='table', rows=[[['wrong-cell']]])):
            value = envelope(); value['proposal']['canonical']['blocks'] = [bad]; cases.append(value)
        for index, value in enumerate(cases):
            with self.subTest(index=index): self.assertFalse(self.validator.is_valid(value))

    def test_schema_conformance_does_not_replace_local_business_guards(self):
        cases = []
        def changed(path, value):
            data = envelope(); target = data
            for key in path[:-1]: target = target[key]
            target[path[-1]] = value; return data
        cases += [(changed(('schema_version',), 1.0), 'document_envelope_invalid'),
                  (changed(('surface_text',), ' '), 'document_envelope_invalid'),
                  (changed(('surface_text',), '\x00'), 'document_envelope_invalid'),
                  (changed(('proposal', 'source_file_ids'), ['invalid']), 'document_envelope_invalid'),
                  (changed(('proposal', 'canonical', 'blocks'), []), 'document_canonical_invalid'),
                  (changed(('proposal', 'canonical', 'blocks', 5, 'rows'), [[[span('x')]], [[], []]]), 'document_canonical_invalid'),
                  (changed(('proposal', 'canonical', 'blocks', 0, 'spans', 0, 'text'), 'x' * 75001), 'document_character_limit'),
                  (changed(('proposal', 'canonical', 'blocks', 2, 'spans', 0, 'link'), 'file:///synthetic'), 'document_canonical_invalid')]
        value = envelope(); value['status'] = 'clarify'; cases.append((value, 'document_envelope_invalid'))
        for index, (value, code) in enumerate(cases):
            with self.subTest(index=index):
                self.validator.validate(value)
                with self.assertRaises(DocumentWorkshopError) as caught: read_document_envelope(json.dumps(value))
                self.assertEqual(caught.exception.reason_code, code)

    def test_schema_uses_only_documented_subset_and_fresh_owned_objects(self):
        allowed = {'type', 'properties', 'required', 'additionalProperties', 'enum', 'items', 'anyOf', '$defs', '$ref', 'description'}
        objects, property_names, enums = [], [], []
        def inspect(node):
            self.assertLessEqual(set(node), allowed)
            if node.get('type') == 'object':
                objects.append(node)
                self.assertIs(node['additionalProperties'], False)
                self.assertEqual(set(node['required']), set(node['properties']))
                property_names.extend(node['properties'])
            enums.extend(node.get('enum', []))
            for category in ('properties', '$defs'):
                for child in node.get(category, {}).values(): inspect(child)
            for child in node.get('anyOf', []): inspect(child)
            if 'items' in node: inspect(node['items'])
        inspect(self.schema)
        self.assertEqual(self.schema['type'], 'object'); self.assertNotIn('anyOf', self.schema)
        self.assertLessEqual(len(property_names), 100); self.assertLessEqual(len(enums), 1000)
        self.assertLess(len(json.dumps(self.schema)), 15000)
        def container_depth(node):
            if '$ref' in node:
                return container_depth(self.schema['$defs'][node['$ref'].split('/')[-1]])
            children = list(node.get('properties', {}).values()) + node.get('anyOf', [])
            if 'items' in node: children.append(node['items'])
            return int(node.get('type') in ('object', 'array')) + max(map(container_depth, children), default=0)
        # Conservative count including arrays, references expanded, root = 1.
        self.assertEqual(container_depth(self.schema), 9)
        before = copy.deepcopy(self.format)
        self.format['json_schema']['schema'].clear()
        self.assertEqual(self.schema_module.document_response_format(), before)
