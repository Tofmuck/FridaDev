"""Causal M2 scope, projection and mounted route boundaries."""
import importlib.util
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from core import document_workshop_context_service as contexts
from core import workspace_document_nextcloud_delete as deletion
from core import workspace_files_store, workspace_folder_document_list
from tests.test_server_document_workshop_contexts_contract import CONV, FOLDER, FILE, CTX
from tests.support.server_test_bootstrap import load_server_module_for_tests


class AdoptionBoundaryTests(unittest.TestCase):
    def test_m2_routes_are_mounted_and_reject_frontend_authority(self):
        server = load_server_module_for_tests()
        client = server.app.test_client()
        for suffix, body in [('remote', None), ('adopt', {'context_id': CTX, 'path': 'Documents/a.md'})]:
            response = (client.get if body is None else client.post)(f'/api/workspace-folders/{FOLDER}/documents/{suffix}', **({} if body is None else {'json': body}))
            self.assertEqual(response.status_code, 400)
            self.assertFalse(response.json['ok'])
        response = client.get(f'/api/workspace-folders/{FOLDER}/documents/remote?context_id={CTX}&context_id={CTX}')
        self.assertEqual(response.status_code, 400)

    def test_nested_m1_path_and_remote_identity_are_rechecked(self):
        link = dict(workspace_folder_id=FOLDER, nextcloud_sync_state='linked',
            nextcloud_target_name='a.md', nextcloud_document_ref='workspace-file:synthetic',
            nextcloud_relative_path='Documents/Nested/a.md', nextcloud_file_id='42', nextcloud_scope_key='a' * 64)
        deps = dict(conversations=SimpleNamespace(get_conversation_summary=lambda _: dict(id=CONV, workspace_folder_id=FOLDER)),
            folders=SimpleNamespace(get_workspace_folder=lambda _: dict(id=FOLDER)),
            files=SimpleNamespace(get_workspace_file_storage_row=lambda *_: dict(id=FILE, workspace_folder_id=FOLDER,
                status='active', content_kind='document', media_kind='text', source_extension='.md'),
                get_nextcloud_link=lambda *a, **kw: link))
        saved = {}
        def save(**fields):
            saved.update(fields, id=CTX, state='editing', created_at='2026-10-04')
            return saved.copy()
        store = SimpleNamespace(create_context=save, get_context=lambda _: saved.copy())
        payload, status = contexts.create_context(dict(conversation_id=CONV, workspace_folder_id=FOLDER, target_file_id=FILE), store=store, **deps)
        self.assertEqual(status, 201)
        self.assertEqual(payload['context']['target_relative_path'], 'Documents/Nested/a.md')
        link['nextcloud_file_id'] = '43'
        self.assertEqual(contexts.get_context(CTX, store=store, **deps)[1], 409)

    def test_enriched_link_never_calls_legacy_basename_delete(self):
        link = dict(nextcloud_relative_path='Documents/Nested/a.md', nextcloud_file_id='42',
                    nextcloud_target_name='a.md', nextcloud_sync_state='linked')
        files = SimpleNamespace(get_nextcloud_link=lambda *a, **kw: link)
        remote = Mock()
        result = deletion.prepare_workspace_document_delete_nextcloud_first(folder=dict(id=FOLDER, nextcloud_target_name='Scope'), file_id=FILE, workspace_files_module=files, nextcloud=remote)
        self.assertFalse(result['ok'])
        self.assertEqual(result['status'], 409)
        remote.delete_document.assert_not_called()

    def test_adopted_exact_name_and_product_path_never_enter_technical_projection(self):
        row = dict(id=FILE, workspace_folder_id=FOLDER, source_kind='nextcloud_adoption',
                   display_name='Épreuve  double.md', original_filename='Épreuve  double.md')
        item = workspace_files_store.serialize_workspace_file_row(row)
        self.assertEqual(item['display_name'], 'Épreuve  double.md')
        files = SimpleNamespace(list_workspace_files=lambda _: [item], get_nextcloud_link=lambda *a, **kw: dict(
            nextcloud_relative_path='Documents/Nested/Épreuve  double.md', document_origin='external', nextcloud_sync_state='linked'))
        item = workspace_folder_document_list.list_workspace_folder_documents(dict(id=FOLDER, nextcloud_sync_state='linked'), workspace_files_module=files)[0]
        self.assertEqual(item['document_relative_path'], 'Documents/Nested/Épreuve  double.md')
        self.assertEqual(item['document_origin'], 'external')
        self.assertFalse(item['document_remote_delete_available'])
        self.assertNotIn('Nested', str(item['document_v1_technical']))
        self.assertNotIn('Épreuve', str(item['document_v1_technical']))

    def test_source_and_adoption_interfaces_exist_without_import_side_effect(self):
        for name in ('workspace_document_adoption_service', 'workspace_document_adoption_store', 'workspace_document_content_service'):
            self.assertIsNotNone(importlib.util.find_spec('core.' + name), 'M2 interface absent')

    def test_identity_move_cannot_hide_an_existing_legacy_path_collision(self):
        from core.workspace_document_adoption_store import classify_resource
        from core.workspace_document_nextcloud_read_client import RemoteResource
        from core.document_workshop_contract import DocumentWorkshopError
        scope='a'*64
        known=dict(id=FILE,status='active',link=dict(nextcloud_scope_key=scope,nextcloud_file_id='42',nextcloud_relative_path='Documents/old.md',nextcloud_sync_state='linked'))
        legacy=dict(id=CTX,status='active',link=dict(nextcloud_target_name='new.md',nextcloud_sync_state='linked'))
        remote=RemoteResource('Documents/new.md',False,'42','"v1"',3,'text/markdown')
        for rows in ([legacy,known],[known,legacy]):
            with self.subTest(order=rows[0]['id']):
                with self.assertRaises(DocumentWorkshopError) as failure:
                    classify_resource(rows,scope,remote)
                self.assertEqual(failure.exception.reason_code,'document_local_collision')

    def test_ocr_required_local_file_is_still_a_path_collision(self):
        from core.workspace_document_adoption_store import classify_resource
        from core.workspace_document_nextcloud_read_client import RemoteResource
        from core.document_workshop_contract import DocumentWorkshopError
        with self.assertRaises(DocumentWorkshopError):
            classify_resource([dict(id=FILE,status='ocr_required',original_filename='a.pdf')],'a'*64,RemoteResource('Documents/a.pdf',False,'42','"v1"',3,'application/pdf'))

    def test_delete_lookup_typeerror_cannot_fall_back_to_an_unverified_basename(self):
        legacy_projection=dict(nextcloud_sync_state='linked',nextcloud_target_name='a.md')
        def obsolete_getter(file_id):
            return legacy_projection
        def faulty_getter(file_id,**kwargs):
            if kwargs:
                raise TypeError('synthetic lookup failure')
            return legacy_projection
        for getter in (obsolete_getter,faulty_getter):
            with self.subTest(getter=getter.__name__):
                remote=Mock()
                result=deletion.prepare_workspace_document_delete_nextcloud_first(folder=dict(id=FOLDER,nextcloud_target_name='Scope'),file_id=FILE,workspace_files_module=SimpleNamespace(get_nextcloud_link=getter),nextcloud=remote)
                self.assertFalse(result['ok'])
                self.assertEqual(result['status'],503)
                remote.delete_document.assert_not_called()


class FreshSourceVersionTests(unittest.TestCase):
    def inputs(self, reader, version):
        import hashlib
        folder=dict(id=FOLDER,nextcloud_sync_state='linked',nextcloud_target_name='Scope')
        file=dict(id=FILE,workspace_folder_id=FOLDER,status='active',content_kind='document',media_kind='text',byte_size=3)
        link=dict(workspace_folder_id=FOLDER,nextcloud_sync_state='linked',nextcloud_scope_key=reader.scope_key('Scope'),
                  nextcloud_file_id='42',nextcloud_relative_path='Documents/a.md',observed_sha256=hashlib.sha256(b'abc').hexdigest())
        link.update(version)
        return dict(folders=SimpleNamespace(get_workspace_folder=lambda _:folder),
                    files=SimpleNamespace(get_workspace_file_storage_row=lambda *_:file,get_nextcloud_link=lambda *a,**k:link))

    def responses(self):
        from tests.unit.core.test_workspace_document_read_client_m2 import resource, multistatus
        body=multistatus(resource('Documents/a.md',collection=False,file_id='42',etag='"v1"',size=3,media_type='text/markdown'))
        return [(207,{},body),(207,{},body),(200,{'ETag':'"v1"','Content-Length':'3'},b'abc'),(207,{},body)]

    def test_invalid_stored_version_refuses_before_client_configuration_or_transport(self):
        from core import workspace_document_content_service as service
        from core.document_workshop_contract import DocumentWorkshopError
        from core.workspace_document_nextcloud_read_client import NextcloudDocumentReadClient
        from core.workspace_folder_nextcloud_client import NextcloudFolderClientConfig
        from tests.unit.core.test_workspace_document_read_client_m2 import dav_server
        versions=[{}, {'nextcloud_etag':None}, {'nextcloud_etag':''}, {'nextcloud_etag':'W/"v1"'},
                  {'nextcloud_etag':'v1'}, {'nextcloud_etag':'"unclosed'}, {'nextcloud_etag':'"v1\r\n"'},
                  {'nextcloud_etag':' "v1"'}, {'nextcloud_etag':'"'+'x'*511+'"'}, {'nextcloud_etag':42}]
        for index,version in enumerate(versions):
            with self.subTest(case=index),dav_server(self.responses()) as (base,seen):
                reader=NextcloudDocumentReadClient(NextcloudFolderClientConfig(base,'test','synthetic'))
                with patch.object(service.NextcloudDocumentReadClient,'from_env',return_value=reader) as configure:
                    with self.assertRaises(DocumentWorkshopError) as failure:
                        service.read_workspace_document_source(FOLDER,FILE,**self.inputs(reader,version))
                    self.assertEqual(failure.exception.reason_code,'document_remote_version_invalid')
                    configure.assert_not_called()
                    self.assertEqual(seen,[])

    def test_valid_recorded_version_is_retained_and_every_remote_request_is_conditional(self):
        from core import workspace_document_content_service as service
        from core.workspace_document_nextcloud_read_client import NextcloudDocumentReadClient
        from core.workspace_folder_nextcloud_client import NextcloudFolderClientConfig
        from tests.unit.core.test_workspace_document_read_client_m2 import dav_server
        with dav_server(self.responses()) as (base,seen):
            reader=NextcloudDocumentReadClient(NextcloudFolderClientConfig(base,'test','synthetic'))
            with patch.object(service.NextcloudDocumentReadClient,'from_env',return_value=reader) as configure:
                source=service.read_workspace_document_source(FOLDER,FILE,**self.inputs(reader,{'nextcloud_etag':'"v1"'}))
            configure.assert_called_once_with()
        self.assertEqual(source.text,'abc'); self.assertEqual(source.etag,'"v1"')
        self.assertEqual([method for method,_,_ in seen],['PROPFIND','PROPFIND','GET','PROPFIND'])
        self.assertTrue(all(headers.get('If-Match')=='"v1"' for _,_,headers in seen))


class AdoptionMetadataReasonRoutesTests(unittest.TestCase):
    def test_mounted_api_distinguishes_metadata_refusals_without_download_or_publication(self):
        from core import workspace_document_adoption_service as service
        from core import workspace_document_adoption_store as adoption
        from core.workspace_document_nextcloud_read_client import NextcloudDocumentReadClient
        from core.workspace_folder_nextcloud_client import NextcloudFolderClientConfig
        from tests.unit.core.test_workspace_document_read_client_m2 import dav_server,resource,multistatus
        server=load_server_module_for_tests()
        context=dict(id=CTX,conversation_id=CONV,workspace_folder_id=FOLDER,target_file_id=None,
                     target_relative_path=None,target_document_ref=None,target_remote_identity=None,state='editing',created_at='2026-10-04')
        folder=dict(id=FOLDER,nextcloud_sync_state='linked',nextcloud_target_name='Scope')
        cases=[
            ('Documents/no-identity.md',dict(file_id=''),'document_remote_identity_invalid',422),
            ('Documents/ambiguous-identity.md',dict(file_id='042'),'document_remote_identity_invalid',422),
            ('Documents/no-version.md',dict(file_id='3',etag=''),'document_remote_version_invalid',422),
            ('Documents/weak-version.md',dict(file_id='4',etag='W/"v1"'),'document_remote_version_invalid',422),
            ('Documents/unknown-size.md',dict(file_id='5',size=None),'document_remote_size_invalid',422),
            ('Documents/empty-size.md',dict(file_id='6',size=0),'document_remote_size_invalid',422),
            ('Documents/invalid-size.md',dict(file_id='7',size='invalid'),'document_remote_size_invalid',422),
            ('Documents/large.md',dict(file_id='8',size=40*1024*1024+1),'document_source_limit',413),
            ('Documents/unsupported.exe',dict(file_id='9'),'document_type_unsupported',422),
        ]
        collection='Documents/Unverified'
        body=multistatus(resource(),*[resource(path,collection=False,**fields) for path,fields,_,_ in cases],resource(collection,file_id=''))
        with patch.object(server.document_workshop_contexts,'get_context',return_value=context), \
             patch.object(server.conv_store,'get_conversation_summary',return_value=dict(id=CONV,workspace_folder_id=FOLDER)), \
             patch.object(server.workspace_folders,'get_workspace_folder',return_value=folder), \
             patch.object(adoption,'list_candidates',return_value=[]), \
             patch.object(adoption,'publish_adoption') as publish, \
             patch.object(server.workspace_files,'_storage_root') as storage_root, \
             dav_server([(207,{},body)]) as (base,seen):
            reader=NextcloudDocumentReadClient(NextcloudFolderClientConfig(base,'test','synthetic'))
            with patch.object(service.NextcloudDocumentReadClient,'from_env',return_value=reader):
                browser=server.app.test_client()
                listing=browser.get(f'/api/workspace-folders/{FOLDER}/documents/remote?context_id={CTX}')
                self.assertEqual(listing.status_code,200); self.assertTrue(listing.json['complete'])
                self.assertEqual(len(listing.json['items']),len(cases)+1)
                items={item['relative_path']:item for item in listing.json['items']}
                for path,_,reason,status in cases:
                    item=items[path]
                    with self.subTest(action='list',reason=reason,path=path):
                        self.assertEqual(item['category'],'incompatible')
                        self.assertEqual(item['reason_code'],reason)
                    result=browser.post(f'/api/workspace-folders/{FOLDER}/documents/adopt',json=dict(context_id=CTX,resource_ref=item['reference']))
                    with self.subTest(action='adopt',reason=reason,path=path):
                        self.assertEqual(result.status_code,status)
                        self.assertEqual(result.json['reason_code'],reason)
                        self.assertEqual(result.json['category'],'incompatible')
                        self.assertFalse(result.json['ok']); self.assertNotIn('file',result.json)
                with self.subTest(action='collection-list'):
                    self.assertEqual(items[collection]['reason_code'],'document_remote_identity_invalid')
                result=browser.get(f'/api/workspace-folders/{FOLDER}/documents/remote?context_id={CTX}&collection_ref={items[collection]["reference"]}')
                with self.subTest(action='collection-open'):
                    self.assertEqual(result.status_code,422)
                    self.assertEqual(result.json['reason_code'],'document_remote_identity_invalid')
                    self.assertNotIn('items',result.json)
            self.assertEqual([(method,headers.get('Depth')) for method,_,headers in seen],[('PROPFIND','1')])
            publish.assert_not_called(); storage_root.assert_not_called()
