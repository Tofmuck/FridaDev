from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tools import image_generation


INTERNAL_PROVIDER_CALLER_HEADER = 'X-Frida-Caller'


class FakeResponse:
    def __init__(self, payload: dict[str, Any], *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeRequests:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, *, json: dict[str, Any], headers: dict[str, Any], timeout: int) -> FakeResponse:
        self.calls.append(
            {
                'url': url,
                'json': json,
                'headers': headers,
                'timeout': timeout,
            }
        )
        return self.response


class FakeLlm:
    def __init__(self) -> None:
        self.header_calls: list[dict[str, str]] = []

    def or_chat_completions_url(self) -> str:
        return 'https://openrouter.example/api/v1/chat/completions'

    def or_headers_custom(self, *, caller: str, referer: str, title: str) -> dict[str, str]:
        self.header_calls.append({'caller': caller, 'referer': referer, 'title': title})
        return {
            'Content-Type': 'application/json',
            'Authorization': 'redacted-test-token',
            INTERNAL_PROVIDER_CALLER_HEADER: caller,
            'HTTP-Referer': referer,
            'X-OpenRouter-Title': title,
            'X-Title': title,
        }

    def read_openrouter_response_payload(self, response: FakeResponse) -> dict[str, Any]:
        return response.json()


class FakeLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, tuple[Any, ...]]] = []

    def info(self, message: str, *args: Any) -> None:
        self.events.append((message, args))

    def warning(self, message: str, *args: Any) -> None:
        self.events.append((message, args))


def _valid_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        'generator_key': 'image_generator_nano_banana',
        'prompt': 'blue circle on white background',
        'aspect_ratio': '1:1',
        'image_size': '1K',
    }
    payload.update(overrides)
    return payload


def _provider_payload(*, image_url: str | None = 'data:image/png;base64,AAAA') -> dict[str, Any]:
    message: dict[str, Any] = {}
    if image_url is not None:
        message['images'] = [{'image_url': {'url': image_url}}]
    return {
        'id': 'gen-test',
        'model': 'google/gemini-2.5-flash-image',
        'choices': [{'finish_reason': 'stop', 'message': message}],
        'usage': {'cost': 0.01, 'prompt_tokens': 12},
    }


class ImageGenerationToolTests(unittest.TestCase):
    def test_generator_table_exposes_four_generators(self) -> None:
        self.assertEqual(
            set(image_generation.IMAGE_GENERATORS),
            {
                'image_generator_openai',
                'image_generator_nano_banana',
                'image_generator_recraft',
                'image_generator_flux',
            },
        )
        self.assertEqual(
            image_generation.IMAGE_GENERATORS['image_generator_nano_banana'].openrouter_model_id,
            'google/gemini-2.5-flash-image',
        )
        self.assertEqual(
            image_generation.IMAGE_GENERATORS['image_generator_nano_banana'].supported_image_sizes,
            ('1K', '2K'),
        )
        self.assertNotIn('openrouter/auto', {spec.openrouter_model_id for spec in image_generation.IMAGE_GENERATORS.values()})

    def test_invalid_generator_is_rejected_without_provider_call(self) -> None:
        requests_module = FakeRequests(FakeResponse(_provider_payload()))
        payload, status = image_generation.generate_image_response(
            _valid_payload(generator_key='openrouter/auto'),
            requests_module=requests_module,
            llm_module=FakeLlm(),
            logger_obj=FakeLogger(),
        )

        self.assertEqual(status, 400)
        self.assertEqual(payload['error_code'], 'invalid_generator')
        self.assertFalse(requests_module.calls)

    def test_prompt_is_required_and_limited(self) -> None:
        requests_module = FakeRequests(FakeResponse(_provider_payload()))
        for request_payload in (
            _valid_payload(prompt='   '),
            _valid_payload(prompt='x' * (image_generation.PROMPT_MAX_CHARS + 1)),
        ):
            with self.subTest(prompt_len=len(request_payload['prompt'])):
                payload, status = image_generation.generate_image_response(
                    request_payload,
                    requests_module=requests_module,
                    llm_module=FakeLlm(),
                    logger_obj=FakeLogger(),
                )
                self.assertEqual(status, 400)
                self.assertEqual(payload['error_code'], 'invalid_prompt')
        self.assertFalse(requests_module.calls)

    def test_aspect_ratio_and_image_size_must_match_generator(self) -> None:
        requests_module = FakeRequests(FakeResponse(_provider_payload()))
        cases = [
            (_valid_payload(aspect_ratio='4:1'), 'invalid_aspect_ratio'),
            (_valid_payload(image_size='4K'), 'invalid_image_size'),
        ]
        for request_payload, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                payload, status = image_generation.generate_image_response(
                    request_payload,
                    requests_module=requests_module,
                    llm_module=FakeLlm(),
                    logger_obj=FakeLogger(),
                )
                self.assertEqual(status, 400)
                self.assertEqual(payload['error_code'], expected_error)
        self.assertFalse(requests_module.calls)

    def test_success_builds_provider_payload_headers_and_extracts_image(self) -> None:
        requests_module = FakeRequests(FakeResponse(_provider_payload()))
        llm_module = FakeLlm()
        payload, status = image_generation.generate_image_response(
            _valid_payload(),
            requests_module=requests_module,
            llm_module=llm_module,
            logger_obj=FakeLogger(),
        )

        self.assertEqual(status, 200)
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['generator_key'], 'image_generator_nano_banana')
        self.assertEqual(payload['model'], 'google/gemini-2.5-flash-image')
        self.assertEqual(payload['mime_type'], 'image/png')
        self.assertEqual(payload['image_data_url'], 'data:image/png;base64,AAAA')
        self.assertEqual(payload['provider_model'], 'google/gemini-2.5-flash-image')
        self.assertEqual(payload['usage']['cost'], 0.01)

        self.assertEqual(len(requests_module.calls), 1)
        call = requests_module.calls[0]
        self.assertEqual(call['timeout'], image_generation.IMAGE_GENERATION_TIMEOUT_S)
        self.assertEqual(call['json']['model'], 'google/gemini-2.5-flash-image')
        self.assertEqual(call['json']['messages'], [{'role': 'user', 'content': 'blue circle on white background'}])
        self.assertEqual(call['json']['modalities'], ['image', 'text'])
        self.assertEqual(call['json']['image_config'], {'aspect_ratio': '1:1', 'image_size': '1K'})
        self.assertEqual(
            call['json']['metadata'],
            {
                'frida_caller': 'image_generator_nano_banana',
                'frida_slot': 'image_generation_tool',
                'frida_image_model': 'google/gemini-2.5-flash-image',
            },
        )
        self.assertEqual(
            call['json']['trace'],
            {
                'trace_name': 'FridaDev',
                'generation_name': 'FridaDev / Image Generator / Nano Banana',
            },
        )
        self.assertEqual(call['headers']['HTTP-Referer'], 'https://fridadev.frida-system.fr/openrouter/image-generation/nano-banana')
        self.assertEqual(call['headers']['X-OpenRouter-Title'], 'FridaDev / Image Generator / Nano Banana')
        self.assertEqual(call['headers'][INTERNAL_PROVIDER_CALLER_HEADER], 'image_generator_nano_banana')
        self.assertEqual(llm_module.header_calls[0]['caller'], 'image_generator_nano_banana')

    def test_missing_image_returns_no_image(self) -> None:
        payload, status = image_generation.generate_image_response(
            _valid_payload(),
            requests_module=FakeRequests(FakeResponse(_provider_payload(image_url=None))),
            llm_module=FakeLlm(),
            logger_obj=FakeLogger(),
        )

        self.assertEqual(status, 502)
        self.assertEqual(payload['error_code'], 'no_image')
        self.assertNotIn('choices', payload)

    def test_non_image_data_url_is_rejected(self) -> None:
        payload, status = image_generation.generate_image_response(
            _valid_payload(),
            requests_module=FakeRequests(FakeResponse(_provider_payload(image_url='data:text/plain;base64,AAAA'))),
            llm_module=FakeLlm(),
            logger_obj=FakeLogger(),
        )

        self.assertEqual(status, 502)
        self.assertEqual(payload['error_code'], 'invalid_image_data_url')
        self.assertNotIn('data:text/plain', str(payload))

    def test_logs_do_not_include_prompt_or_base64(self) -> None:
        secret_prompt = 'private prompt should not be logged'
        logger_obj = FakeLogger()
        payload, status = image_generation.generate_image_response(
            _valid_payload(prompt=secret_prompt),
            requests_module=FakeRequests(FakeResponse(_provider_payload(image_url='data:image/png;base64,SECRETIMAGEBYTES'))),
            llm_module=FakeLlm(),
            logger_obj=logger_obj,
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload['mime_type'], 'image/png')
        logged = repr(logger_obj.events)
        self.assertNotIn(secret_prompt, logged)
        self.assertNotIn('SECRETIMAGEBYTES', logged)
        self.assertIn('data_url_chars', logged)


if __name__ == '__main__':
    unittest.main()
