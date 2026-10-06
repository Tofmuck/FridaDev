"""M1 exercises the mounted Flask routes, not direct service callbacks."""
import unittest
from unittest.mock import Mock, patch

from tests.support.server_test_bootstrap import load_server_module_for_tests
from core import document_workshop_actions

CONV = '11111111-1111-4111-8111-111111111111'
FOLDER = '22222222-2222-4222-8222-222222222222'
OTHER = '33333333-3333-4333-8333-333333333333'
FILE = '44444444-4444-4444-8444-444444444444'
CTX = '55555555-5555-4555-8555-555555555555'


class DocumentWorkshopRoutesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = load_server_module_for_tests()

    def setUp(self):
        self.client = self.server.app.test_client()
        self.conversation = {'id': CONV, 'workspace_folder_id': FOLDER, 'deleted_at': None}
        self.folder = {'id': FOLDER, 'deleted_at': None}
        self.file = {'id': FILE, 'workspace_folder_id': FOLDER, 'deleted_at': None,
                     'status': 'active', 'content_kind': 'document', 'media_kind': 'text',
                     'source_extension': '.md'}
        self.link = {'workspace_folder_id': FOLDER, 'nextcloud_sync_state': 'linked',
                     'nextcloud_target_name': 'Ébauche.md', 'nextcloud_document_ref': 'workspace-file:test'}
        self.saved = None
        self.store = Mock()
        def create(**fields):
            self.saved = dict(fields, id=CTX, state='editing', created_at='2026-10-04T14:00:00+00:00')
            return dict(self.saved)
        self.store.create_context.side_effect = create
        self.store.get_context.side_effect = lambda context_id: dict(self.saved) if self.saved and context_id == CTX else None
        patches = [
            patch.object(document_workshop_actions, 'latest', return_value=None),
            patch.object(self.server, 'document_workshop_contexts', self.store, create=True),
            patch.object(self.server.conv_store, 'get_conversation_summary', side_effect=lambda *_a, **_k: self.conversation),
            patch.object(self.server.workspace_folders, 'get_workspace_folder', side_effect=lambda *_a, **_k: self.folder),
            patch.object(self.server.workspace_files, 'get_workspace_file_storage_row', side_effect=lambda *_a, **_k: self.file),
            patch.object(self.server.workspace_files, 'get_nextcloud_link', side_effect=lambda *_a, **_k: self.link),
            patch.object(self.server.requests, 'post'), patch.object(self.server.requests, 'get'),
            patch.object(self.server.llm, 'build_payload'),
            patch.object(self.server.workspace_document_nextcloud_runtime, 'store_workspace_document_nextcloud_first'),
            patch.object(self.server.workspace_document_nextcloud_runtime, 'prepare_workspace_document_delete_nextcloud_first'),
            patch.object(self.server.workspace_document_nextcloud_runtime, '_client'),
        ]
        # Assert external boundaries without relying on an always-successful transport.
        for item in patches:
            item.start(); self.addCleanup(item.stop)
        self.external = [self.server.requests.post, self.server.requests.get, self.server.llm.build_payload,
                         self.server.workspace_document_nextcloud_runtime.store_workspace_document_nextcloud_first,
                         self.server.workspace_document_nextcloud_runtime.prepare_workspace_document_delete_nextcloud_first,
                         self.server.workspace_document_nextcloud_runtime._client]
        self.addCleanup(lambda: [mock.assert_not_called() for mock in self.external])

    def post(self, **extra):
        return self.client.post('/api/document-workshop/contexts', json={
            'conversation_id': CONV, 'workspace_folder_id': FOLDER, **extra})

    def test_create_and_get_editing_without_target_or_conversation_message(self):
        response = self.post()
        self.assertEqual(response.status_code, 201)
        context = response.json['context']
        self.assertEqual((context['id'], context['conversation_id'], context['workspace_folder_id'], context['state']),
                         (CTX, CONV, FOLDER, 'editing'))
        self.assertIsNone(context['target_file_id'])
        self.assertEqual(context['capabilities'], {'prepare': True, 'confirm': False,
            'formats': ['markdown'], 'operations': ['create', 'copy'], 'update': False})
        self.assertIsNone(context['preparation'])
        result = self.client.get(f'/api/document-workshop/contexts/{CTX}')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['context'], context)
        self.store.create_context.assert_called_once()

    def test_explicit_target_verified_and_server_path_preserved(self):
        response = self.post(target_file_id=FILE)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['context']['target_file_id'], FILE)
        self.assertEqual(response.json['context']['target_relative_path'], 'Documents/Ébauche.md')
        self.assertNotIn('nextcloud_document_ref', str(response.json))

    def test_absent_deleted_or_inconsistent_resources_never_insert(self):
        for resource in ('conversation', 'folder'):
            original = getattr(self, resource)
            for value in (None, dict(original, deleted_at='2026-10-04')):
                with self.subTest(resource=resource, value=value is None):
                    setattr(self, resource, value)
                    self.assertIn(self.post().status_code, (404, 409))
            setattr(self, resource, original)
        self.conversation['workspace_folder_id'] = OTHER
        self.assertEqual(self.post().status_code, 409)
        self.store.create_context.assert_not_called()

    def test_target_absent_deleted_foreign_unsupported_or_unlinked_rejected(self):
        original = dict(self.file)
        for value in (None, dict(original, deleted_at='gone'), dict(original, workspace_folder_id=OTHER),
                      dict(original, status='deleted'), dict(original, source_extension='.pdf'),
                      dict(original, source_extension='.txt'), dict(original, content_kind='image')):
            self.file = value
            with self.subTest(value=value):
                self.assertIn(self.post(target_file_id=FILE).status_code, (404, 409, 422))
        self.file = original
        for key, value in [('workspace_folder_id', OTHER), ('nextcloud_sync_state', 'deleted'),
                           ('nextcloud_target_name', '../Ébauche.md')]:
            saved = self.link[key]; self.link[key] = value
            self.assertIn(self.post(target_file_id=FILE).status_code, (409, 422))
            self.link[key] = saved
        self.store.create_context.assert_not_called()

    def test_frontend_authority_and_forged_identity_rejected(self):
        for fields in ({'target_file_id': 'invented'}, {'target_path': 'Documents/nom.md'},
                       {'state': 'pending'}, {'target_url': 'https://example.invalid/a.md'}):
            self.assertEqual(self.post(**fields).status_code, 400)
        self.store.create_context.assert_not_called()

    def test_get_revalidates_conversation_folder_target_and_link_identity(self):
        self.assertEqual(self.post(target_file_id=FILE).status_code, 201)
        for resource, key, value in [('conversation', 'workspace_folder_id', OTHER),
                                     ('folder', 'deleted_at', 'gone'), ('file', 'status', 'deleted'),
                                     ('link', 'nextcloud_target_name', 'Autre.md'),
                                     ('link', 'nextcloud_document_ref', 'different')]:
            obj = getattr(self, resource); old = obj[key]; obj[key] = value
            self.assertIn(self.client.get(f'/api/document-workshop/contexts/{CTX}').status_code, (404, 409, 422))
            obj[key] = old
        self.assertEqual(self.client.get(f'/api/document-workshop/contexts/{OTHER}').status_code, 404)
        self.assertEqual(self.client.get('/api/document-workshop/contexts/faux').status_code, 400)

    def test_storage_or_inventory_error_is_content_free(self):
        self.store.create_context.side_effect = RuntimeError('synthetic-sensitive-detail')
        response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('synthetic-sensitive-detail', response.get_data(as_text=True))

    def test_incomplete_documentary_request_refused_before_reservation_or_provider(self):
        with patch.object(self.server.chat_service.turn_claims, 'acquire') as acquire:
            for context_id in (CTX, 'forged', None, ''):
                response = self.client.post('/api/chat', json={'message': 'Synthétique', 'document_context_id': context_id})
                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.json['reason_code'], 'document_request_invalid')
            acquire.assert_not_called()
