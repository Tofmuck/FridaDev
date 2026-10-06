import unittest
from observability.observability_payload_guard import guard_payload
from core.document_workshop_progress import DocumentPreparation
from core.document_workshop_contract import DocumentWorkshopError

class M4ProgressAndObservabilityTests(unittest.TestCase):
    def test_closed_documentary_event_schema_accepts_only_technical_values(self):
        payload = dict(action_id='11111111-1111-4111-8111-111111111111',context_id='22222222-2222-4222-8222-222222222222',
            state='preparing',phase='provider_content',received_content_codepoints=123)
        self.assertTrue(guard_payload(payload,stage='document_preparation').accepted)
        self.assertTrue(guard_payload(payload|{'status_schema_version':'agentic_v1'},stage='document_preparation').accepted)
        for key,value in [('text','synthetic'),('relative_path','Documents/Synthetic.md'),('canonical',{}),
                          ('exception','synthetic'),('phase','synthetic prose'),('action_id','synthetic'),
                          ('received_content_codepoints',True)]:
            with self.subTest(key=key):
                self.assertFalse(guard_payload(payload|{key:value},stage='document_preparation').accepted)
        self.assertFalse(guard_payload(payload,stage='other').accepted)

    def test_upstream_steps_renew_effective_progress_without_total_deadline(self):
        now=[0.]
        progress=DocumentPreparation(monotonic=lambda:now[0])
        for step in ('user_saved','summary_ready','identity_ready','memory_ready','stimmung_ready','hermeneutic_ready','dialogue_ready'):
            now[0]+=119;progress.complete_input_step(step)
        for source in ('one','two','three'):
            now[0]+=119;progress.complete_source(source)
        now[0]+=119;progress.complete_input_step('sources_ready')
        self.assertGreater(now[0],120)
        now[0]+=119.999;progress.check()
        now[0]+=.001
        with self.assertRaisesRegex(DocumentWorkshopError,'document_inactivity'):progress.check()

    def test_repeated_steps_or_sources_cannot_forge_progress(self):
        progress=DocumentPreparation()
        progress.complete_input_step('user_saved')
        with self.assertRaisesRegex(DocumentWorkshopError,'document_progress_invalid'):progress.complete_input_step('user_saved')
        for step in ('summary_ready','identity_ready','memory_ready','stimmung_ready','hermeneutic_ready','dialogue_ready'):
            progress.complete_input_step(step)
        progress.complete_source('one')
        with self.assertRaisesRegex(DocumentWorkshopError,'document_progress_invalid'):progress.complete_source('one')
