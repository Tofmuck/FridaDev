"""Default registrar is a closed boundary, even with no M5 schema/runtime."""
import unittest
from flask import Flask
import document_workshop_routes

A = 'a1111111-1111-4111-8111-111111111111'
BODY = {name: value for name, value in zip(
    ('context_id', 'conversation_id', 'workspace_folder_id', 'revision_id', 'request_id'),
    ('b1111111-1111-4111-8111-111111111111', 'c1111111-1111-4111-8111-111111111111',
     'd1111111-1111-4111-8111-111111111111', 'e1111111-1111-4111-8111-111111111111',
     'f1111111-1111-4111-8111-111111111111'))}


class ConfirmationRouteM5Tests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        def forbidden():
            self.fail('Default confirmation touched a storage/runtime dependency')
        document_workshop_routes.register_document_workshop_routes(self.app,
            get_store=forbidden, get_conversations=forbidden, get_folders=forbidden, get_files=forbidden)
        self.client = self.app.test_client()

    def test_constructed_confirmation_is_unavailable_before_any_storage_or_mutation(self):
        response = self.client.post(f'/api/document-workshop/actions/{A}/confirm', json=BODY)
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json['ok'])
        self.assertEqual(response.json['reason_code'], 'document_execution_unavailable')
        self.assertNotIn('action', response.json)

    def test_get_and_confirm_do_not_alias_a_chat_or_preparation_submission(self):
        response = self.client.get(f'/api/document-workshop/actions/{A}/confirm')
        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.client.post(f'/api/document-workshop/actions/{A}/confirm', json=BODY).status_code, 503)

    def test_forged_content_path_etag_does_not_obtain_mutator_authority(self):
        for field, value in [('relative_path', 'Documents/other.md'), ('content', 'synthetic'), ('etag', '"v1"')]:
            with self.subTest(field=field):
                response = self.client.post(f'/api/document-workshop/actions/{A}/confirm', json=BODY | {field: value})
                self.assertIsInstance(response.json, dict)
                self.assertFalse(response.json['ok'])
                self.assertIn(response.status_code, (400, 503))
                self.assertNotIn('content', response.json)


if __name__ == '__main__':
    unittest.main()
