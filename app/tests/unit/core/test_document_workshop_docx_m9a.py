"""M9-A consumes the same closed preparation envelope as the product."""
import json
import unittest

from core.document_workshop_contract import DocumentWorkshopError
from core.document_workshop_envelope import read_document_envelope
from tests.unit.core.test_document_workshop_envelope import envelope, SOURCE_ID


class DocxPreparationTests(unittest.TestCase):
    def test_docx_create_copy_update_reach_existing_envelope_with_exact_target(self):
        for operation in ('create', 'copy', 'update'):
            with self.subTest(operation=operation):
                value = envelope(operation=operation, format='docx',
                    relative_path='Documents/Étude.docx',
                    source_file_ids=[SOURCE_ID] if operation == 'copy' else [])
                result = read_document_envelope(json.dumps(value))
                self.assertEqual(result.format, 'docx')
                self.assertEqual(result.operation, operation)
                self.assertEqual(result.relative_path, 'Documents/Étude.docx')

    def test_copy_without_explicit_source_stays_closed(self):
        for value in (envelope(operation='copy', format='pdf', relative_path='Documents/a.pdf'),
                      envelope(operation='copy', format='docx', relative_path='Documents/a.docx')):
            with self.assertRaises(DocumentWorkshopError):
                read_document_envelope(json.dumps(value))
