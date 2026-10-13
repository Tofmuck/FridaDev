"""M10 uses the existing measured schema and closed envelope."""
import json
import unittest
from core.document_workshop_envelope import read_document_envelope
from core.document_workshop_output_schema import document_response_format
from tests.unit.core.test_document_workshop_envelope import envelope, SOURCE_ID

class PdfPreparationTests(unittest.TestCase):
    def test_pdf_operations_use_existing_schema_and_envelope(self):
        self.assertIn('pdf',document_response_format()['json_schema']['schema']['properties']['proposal']['anyOf'][0]['properties']['format']['enum'])
        for operation in ('create','copy','update'):
            result=read_document_envelope(json.dumps(envelope(operation=operation,format='pdf',
                relative_path='Documents/Étude.pdf',source_file_ids=[SOURCE_ID] if operation=='copy' else [])))
            self.assertEqual((result.operation,result.format),(operation,'pdf'))
