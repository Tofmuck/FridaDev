from __future__ import annotations

import inspect
import unittest

from core import chat_service


class ChatMainPayloadBoundaryTests(unittest.TestCase):
    def test_chat_service_reexports_named_main_payload_boundary(self) -> None:
        self.assertTrue(
            hasattr(chat_service, 'prepare_main_payload'),
            'Lot 9B.4 requires a named main-payload preparation boundary',
        )
        self.assertTrue(hasattr(chat_service, 'PreparedMainPayload'))
        self.assertEqual(
            chat_service.prepare_main_payload.__module__,
            'core.chat_main_payload',
        )
        self.assertEqual(
            chat_service.PreparedMainPayload.__module__,
            'core.chat_main_payload',
        )

    def test_chat_response_delegates_lane_injection_capsule_and_manifest(self) -> None:
        source = inspect.getsource(chat_service.chat_response)

        self.assertIn('prepared_main_payload = prepare_main_payload(', source)
        for low_level_call in (
            'workspace_folder_notes_prompt_lane.inject_workspace_folder_notes_prompt_lane',
            'active_document_prompt_lane.inject_active_document_prompt_lane',
            'biblio_chat_runtime.inject_biblio_prompt_lane',
            'adobe_docs_prompt_lane.inject_adobe_prompt_lane',
            'continuity_capsule.resolve_continuity_capsule',
            'main_payload_manifest.build_main_payload_manifest',
        ):
            with self.subTest(low_level_call=low_level_call):
                self.assertNotIn(low_level_call, source)


if __name__ == '__main__':
    unittest.main()
