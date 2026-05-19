from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support.server_test_bootstrap import load_server_module_for_tests


class ServerImageGenerationRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = load_server_module_for_tests()
        self.client = self.server.app.test_client()

    def test_api_tools_image_generation_delegates_to_tool(self) -> None:
        observed = {}
        original = self.server.image_generation.generate_image_response

        def fake_generate_image_response(payload):
            observed['payload'] = payload
            return (
                {
                    'ok': True,
                    'generator_key': 'image_generator_nano_banana',
                    'model': 'google/gemini-2.5-flash-image',
                    'display_name': 'Nano Banana',
                    'pricing_label': 'prix API observe',
                    'aspect_ratio': '1:1',
                    'image_size': '1K',
                    'image_data_url': 'data:image/png;base64,AAAA',
                    'mime_type': 'image/png',
                    'provider_model': 'google/gemini-2.5-flash-image',
                    'usage': {},
                },
                200,
            )

        self.server.image_generation.generate_image_response = fake_generate_image_response
        try:
            response = self.client.post(
                '/api/tools/image-generation',
                json={
                    'generator_key': 'image_generator_nano_banana',
                    'prompt': 'blue circle',
                    'aspect_ratio': '1:1',
                    'image_size': '1K',
                },
            )
        finally:
            self.server.image_generation.generate_image_response = original

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['payload']['prompt'], 'blue circle')
        self.assertTrue(response.get_json()['ok'])

    def test_api_tools_image_generation_returns_normalized_errors_without_secret(self) -> None:
        original = self.server.image_generation.generate_image_response

        def fake_generate_image_response(payload):
            return (
                {
                    'ok': False,
                    'error_code': 'invalid_prompt',
                    'message': 'A non-empty prompt is required.',
                },
                400,
            )

        self.server.image_generation.generate_image_response = fake_generate_image_response
        try:
            response = self.client.post('/api/tools/image-generation', json={})
        finally:
            self.server.image_generation.generate_image_response = original

        body = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body['error_code'], 'invalid_prompt')
        self.assertNotIn('Authorization', body)
        self.assertNotIn('api_key', body)


if __name__ == '__main__':
    unittest.main()
