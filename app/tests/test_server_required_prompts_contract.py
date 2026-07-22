from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import chat_service, prompt_loader
from tests.support.server_test_bootstrap import load_server_module_for_tests


class _NoCalls:
    def __getattr__(self, name: str):
        raise AssertionError(f'unexpected downstream call: {name}')


def _prompt_loader_without(prompt_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        get_main_system_prompt=lambda: '' if prompt_id == 'main_system' else 'SYNTHETIC SYSTEM',
        get_main_hermeneutical_prompt=(
            lambda: '' if prompt_id == 'main_hermeneutical' else 'SYNTHETIC HERMENEUTICAL'
        ),
    )


class RequiredPromptChatServiceContractTests(unittest.TestCase):
    def test_chat_refuses_each_missing_constitutive_prompt_before_session_resolution(self) -> None:
        for prompt_id in ('main_system', 'main_hermeneutical'):
            for stream in (False, True):
                with self.subTest(prompt_id=prompt_id, stream=stream):
                    with patch.object(
                        chat_service.chat_session_flow,
                        'resolve_chat_session',
                        side_effect=AssertionError('session resolution must not run'),
                    ) as resolve_session:
                        result = chat_service.chat_response(
                            {'message': 'SYNTHETIC USER TURN', 'stream': stream},
                            prompt_loader_module=_prompt_loader_without(prompt_id),
                            conv_store_module=_NoCalls(),
                            memory_store_module=_NoCalls(),
                            runtime_settings_module=_NoCalls(),
                            summarizer_module=_NoCalls(),
                            identity_module=_NoCalls(),
                            admin_logs_module=_NoCalls(),
                            llm_module=_NoCalls(),
                            requests_module=_NoCalls(),
                            token_utils_module=_NoCalls(),
                            arbiter_module=_NoCalls(),
                            web_search_module=_NoCalls(),
                            config_module=_NoCalls(),
                            logger=_NoCalls(),
                        )

                    resolve_session.assert_not_called()
                    self.assertEqual(result['kind'], 'json')
                    self.assertEqual(result['status'], 503)
                    self.assertEqual(
                        result['payload'],
                        {
                            'ok': False,
                            'error': 'service temporairement indisponible',
                            'reason_code': 'critical_prompt_unavailable',
                            'prompt_id': prompt_id,
                        },
                    )
                    self.assertEqual(result['headers'], {})

    def test_chat_maps_file_and_decode_failures_to_bounded_prompt_refusal(self) -> None:
        decode_error = UnicodeDecodeError('utf-8', b'x', 0, 1, 'SYNTHETIC PRIVATE DETAIL')
        cases = (
            ('main_system_missing', [FileNotFoundError(), 'SYNTHETIC HERMENEUTICAL'], 'main_system'),
            ('main_hermeneutical_permission', ['SYNTHETIC SYSTEM', PermissionError()], 'main_hermeneutical'),
            ('main_hermeneutical_decode', ['SYNTHETIC SYSTEM', decode_error], 'main_hermeneutical'),
        )
        for label, read_effects, prompt_id in cases:
            with self.subTest(label=label):
                with (
                    patch.object(Path, 'read_text', side_effect=read_effects),
                    patch.object(
                        chat_service.chat_session_flow,
                        'resolve_chat_session',
                        side_effect=AssertionError('session resolution must not run'),
                    ) as resolve_session,
                ):
                    result = chat_service.chat_response(
                        {'message': 'SYNTHETIC USER TURN'},
                        prompt_loader_module=prompt_loader,
                        conv_store_module=_NoCalls(),
                        memory_store_module=_NoCalls(),
                        runtime_settings_module=_NoCalls(),
                        summarizer_module=_NoCalls(),
                        identity_module=_NoCalls(),
                        admin_logs_module=_NoCalls(),
                        llm_module=_NoCalls(),
                        requests_module=_NoCalls(),
                        token_utils_module=_NoCalls(),
                        arbiter_module=_NoCalls(),
                        web_search_module=_NoCalls(),
                        config_module=_NoCalls(),
                        logger=_NoCalls(),
                    )

                resolve_session.assert_not_called()
                self.assertEqual(result['status'], 503)
                self.assertEqual(result['payload']['prompt_id'], prompt_id)
                serialized = json.dumps(result['payload'], ensure_ascii=True, sort_keys=True)
                self.assertNotIn('SYNTHETIC PRIVATE DETAIL', serialized)


class RequiredPromptRoutesContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()

    def test_api_chat_returns_bounded_503_for_each_prompt_and_transport_mode(self) -> None:
        for prompt_id in ('main_system', 'main_hermeneutical'):
            for stream in (False, True):
                with self.subTest(prompt_id=prompt_id, stream=stream):
                    with (
                        patch.object(
                            self.server.prompt_loader,
                            'get_main_system_prompt',
                            return_value='' if prompt_id == 'main_system' else 'SYNTHETIC SYSTEM',
                        ),
                        patch.object(
                            self.server.prompt_loader,
                            'get_main_hermeneutical_prompt',
                            return_value=(
                                '' if prompt_id == 'main_hermeneutical' else 'SYNTHETIC HERMENEUTICAL'
                            ),
                        ),
                        patch.object(
                            self.server.chat_service.chat_session_flow,
                            'resolve_chat_session',
                            side_effect=AssertionError('session resolution must not run'),
                        ) as resolve_session,
                    ):
                        response = self.client.post(
                            '/api/chat',
                            json={
                                'message': 'SYNTHETIC USER TURN',
                                'conversation_id': 'synthetic-existing-conversation',
                                'stream': stream,
                            },
                            buffered=True,
                        )

                    resolve_session.assert_not_called()
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(response.content_type, 'application/json')
                    self.assertEqual(
                        response.get_json(),
                        {
                            'ok': False,
                            'error': 'service temporairement indisponible',
                            'reason_code': 'critical_prompt_unavailable',
                            'prompt_id': prompt_id,
                        },
                    )
                    self.assertNotIn('"event"', response.get_data(as_text=True))

    def test_api_conversations_refuses_missing_main_system_before_creation_or_save(self) -> None:
        with (
            patch.object(self.server.prompt_loader, 'get_main_system_prompt', return_value='  '),
            patch.object(
                self.server.conv_store,
                'new_conversation',
                side_effect=AssertionError('conversation creation must not run'),
            ) as new_conversation,
            patch.object(
                self.server.conv_store,
                'save_conversation',
                side_effect=AssertionError('conversation save must not run'),
            ) as save_conversation,
        ):
            response = self.client.post('/api/conversations', json={'title': 'SYNTHETIC TITLE'})

        new_conversation.assert_not_called()
        save_conversation.assert_not_called()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json(),
            {
                'ok': False,
                'error': 'service temporairement indisponible',
                'reason_code': 'critical_prompt_unavailable',
                'prompt_id': 'main_system',
            },
        )
        serialized = json.dumps(response.get_json(), ensure_ascii=True, sort_keys=True)
        for forbidden in ('SYNTHETIC USER TURN', 'SYNTHETIC TITLE', '/app/', 'Traceback'):
            self.assertNotIn(forbidden, serialized)


if __name__ == '__main__':
    unittest.main()
