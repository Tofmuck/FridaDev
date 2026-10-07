"""M7 final HTTP request and causal concurrent-version rejection."""
import unittest
from unittest.mock import patch
from core.workspace_document_nextcloud_mutation_client import NextcloudDocumentMutationClient
from core.workspace_folder_nextcloud_client import NextcloudFolderClientConfig
from core.workspace_document_paths import validate_document_path
from tests.support.document_workshop_update_dav import update_dav


class UpdateClientM7Tests(unittest.TestCase):
    def update(self,base,state):
        client=NextcloudDocumentMutationClient(NextcloudFolderClientConfig(base,'test','synthetic'))
        self.assertTrue(callable(getattr(client,'update_document',None)), 'M7 conditional update absent')
        return client.update_document('Scope',validate_document_path(state['path'],format='markdown'),b'Revised\n',
            prepared_etag='"v1"',expected_file_id='42',before_mutation=lambda *_:True)

    def test_final_put_uses_exact_prepared_etag_and_preserves_identity(self):
        with update_dav() as (base,state):
            result=self.update(base,state)
            self.assertEqual(result.state,'known_success')
            self.assertEqual(result.resource.file_id,'42')
            self.assertEqual(state['content'],b'Revised\n')
            put=[r for r in state['seen'] if r[0]=='PUT'];self.assertEqual(len(put),1)
            self.assertEqual(put[0][2]['If-Match'],'"v1"');self.assertNotIn('If-None-Match',put[0][2])
            self.assertEqual(put[0][3],b'Revised\n')

    def test_change_after_prelecture_is_412_and_concurrent_bytes_survive(self):
        with update_dav() as (base,state):
            state['concurrent_before_put']=True
            result=self.update(base,state)
            self.assertEqual(result.state,'known_failure');self.assertEqual(result.http_status,412)
            self.assertEqual(state['content'],b'Concurrent\n')
            self.assertEqual([r[0] for r in state['seen'] if r[0] in ('PUT','DELETE','MKCOL')],['PUT'])

    def test_lost_dav_reply_keeps_unknown_effect_and_never_compensates(self):
        with update_dav() as (base,state):
            state['drop_put']=True
            result=self.update(base,state)
            self.assertEqual(result.state,'remote_uncertain');self.assertEqual(state['content'],b'Revised\n')
            self.assertEqual([r[0] for r in state['seen'] if r[0] in ('PUT','DELETE','MKCOL')],['PUT'])

    def negative_precondition(self,mode):
        with update_dav() as (base,state):
            actual=NextcloudDocumentMutationClient._mutation_request
            def unsafe(client,method,folder,path,*,data=None,headers=None):
                if method=='PUT':
                    state.update(etag='"current"',content=b'Concurrent\n');headers=dict(headers)
                    if mode=='absent':headers.pop('If-Match')
                    else:headers['If-Match']=state['etag']
                return actual(client,method,folder,path,data=data,headers=headers)
            with patch.object(NextcloudDocumentMutationClient,'_mutation_request',unsafe):
                result=self.update(base,state)
            # Same probe as the positive race proof MUST fail with a faulty
            # final production HTTP header. The peer actually overwrote bytes.
            with self.assertRaises(AssertionError):self.assertEqual(result.state,'known_failure')
            self.assertEqual(state['content'],b'Revised\n');self.assertEqual(result.state,'known_success')

    def test_negative_probe_detects_missing_final_if_match(self):self.negative_precondition('absent')
    def test_negative_probe_detects_refreshed_final_if_match(self):self.negative_precondition('current')
