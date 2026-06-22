from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

import requests


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import workspace_folder_generated_image_provider
from core import workspace_folder_generated_image_validation
from tools import image_generation


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeRequests:
    def __init__(self, response: _FakeResponse | None = None, *, exc: Exception | None = None) -> None:
        self.response = response or _FakeResponse(_provider_payload())
        self.exc = exc
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, *, json: dict[str, Any], headers: dict[str, Any], timeout: int) -> _FakeResponse:
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        if self.exc:
            raise self.exc
        return self.response


class _FakeLlm:
    def or_chat_completions_url(self) -> str:
        return "https://openrouter.example/api/v1/chat/completions"

    def or_headers_custom(self, *, caller: str, referer: str, title: str) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": "redacted-test-token",
            "X-Frida-Caller": caller,
            "HTTP-Referer": referer,
            "X-OpenRouter-Title": title,
        }

    def read_openrouter_response_payload(self, response: _FakeResponse) -> dict[str, Any]:
        return response.json()


class _FakeLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, tuple[Any, ...]]] = []

    def info(self, message: str, *args: Any) -> None:
        self.events.append((message, args))

    def warning(self, message: str, *args: Any) -> None:
        self.events.append((message, args))


def _valid_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "generator_key": "image_generator_nano_banana",
        "prompt": "synthetic harmless image prompt",
        "aspect_ratio": "1:1",
        "image_size": "1K",
    }
    payload.update(overrides)
    return payload


def _provider_payload(*, image_url: str | None = "data:image/png;base64,AAAA") -> dict[str, Any]:
    message: dict[str, Any] = {}
    if image_url is not None:
        message["images"] = [{"image_url": {"url": image_url}}]
    return {
        "id": "gen-test",
        "model": "google/gemini-2.5-flash-image",
        "choices": [{"finish_reason": "stop", "message": message}],
        "usage": {"prompt_tokens": 12},
    }


class WorkspaceFolderGeneratedImageProviderTests(unittest.TestCase):
    def test_v1_data_url_limit_is_not_the_v0_browser_limit(self) -> None:
        self.assertGreater(
            workspace_folder_generated_image_validation.V1_IMAGE_DATA_URL_MAX_CHARS,
            image_generation.IMAGE_DATA_URL_MAX_CHARS,
        )

    def test_success_uses_v0_generator_specs_without_exposing_prompt_or_base64_in_logs(self) -> None:
        logger = _FakeLogger()
        prompt = "private prompt should stay out of logs"
        result = workspace_folder_generated_image_provider.generate_generated_image_data_url(
            _valid_payload(prompt=prompt),
            requests_module=_FakeRequests(
                _FakeResponse(_provider_payload(image_url="data:image/png;base64,SECRETIMAGEBYTES"))
            ),
            llm_module=_FakeLlm(),
            logger_obj=logger,
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.generator_key, "image_generator_nano_banana")
        self.assertEqual(result.provider_model, "google/gemini-2.5-flash-image")
        self.assertEqual(result.data_url, "data:image/png;base64,SECRETIMAGEBYTES")
        log_text = repr(logger.events)
        self.assertNotIn(prompt, log_text)
        self.assertNotIn("SECRETIMAGEBYTES", log_text)

    def test_invalid_inputs_fail_before_provider_call(self) -> None:
        cases = [
            (_valid_payload(generator_key="openrouter/auto"), "folder_generated_image_generator_unsupported"),
            (_valid_payload(prompt=" "), "folder_generated_image_prompt_missing"),
            (_valid_payload(prompt="x" * 2001), "folder_generated_image_prompt_too_large"),
            (_valid_payload(aspect_ratio="4:1"), "folder_generated_image_aspect_ratio_unsupported"),
            (_valid_payload(image_size="4K"), "folder_generated_image_size_unsupported"),
        ]
        for payload, reason_code in cases:
            with self.subTest(reason_code=reason_code):
                requests_module = _FakeRequests()
                result = workspace_folder_generated_image_provider.generate_generated_image_data_url(
                    payload,
                    requests_module=requests_module,
                    llm_module=_FakeLlm(),
                    logger_obj=_FakeLogger(),
                )
                self.assertFalse(result.ok)
                self.assertEqual(result.reason_code, reason_code)
                self.assertFalse(requests_module.calls)

    def test_provider_timeout_and_no_image_are_content_free_failures(self) -> None:
        timeout = workspace_folder_generated_image_provider.generate_generated_image_data_url(
            _valid_payload(),
            requests_module=_FakeRequests(exc=requests.Timeout()),
            llm_module=_FakeLlm(),
            logger_obj=_FakeLogger(),
        )
        self.assertFalse(timeout.ok)
        self.assertEqual(timeout.reason_code, "folder_generated_image_provider_timeout")

        no_image = workspace_folder_generated_image_provider.generate_generated_image_data_url(
            _valid_payload(),
            requests_module=_FakeRequests(_FakeResponse(_provider_payload(image_url=None))),
            llm_module=_FakeLlm(),
            logger_obj=_FakeLogger(),
        )
        self.assertFalse(no_image.ok)
        self.assertEqual(no_image.reason_code, "folder_generated_image_provider_no_image")
        self.assertNotIn("choices", str(no_image))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
