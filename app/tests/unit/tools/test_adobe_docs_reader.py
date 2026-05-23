from __future__ import annotations

import builtins
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tools import adobe_docs_reader, adobe_docs_sources


SECRET_MARKDOWN = "# Adobe Secret\n\nTexte Adobe a ne pas logger.\n\n[Help](https://helpx.adobe.com/photoshop/using/layers.html)"


class FakeResponse:
    def __init__(self, payload: dict[str, object], *, raise_error: Exception | None = None) -> None:
        self.payload = payload
        self.raise_error = raise_error

    def raise_for_status(self) -> None:
        if self.raise_error:
            raise self.raise_error

    def json(self) -> dict[str, object]:
        return self.payload


class FakeRequests:
    def __init__(self, response: FakeResponse | None = None, *, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    def post(self, url: str, *, json: dict[str, object], headers: dict[str, str], timeout: int) -> FakeResponse:
        self.calls.append({'url': url, 'json': dict(json), 'headers': dict(headers), 'timeout': timeout})
        if self.error:
            raise self.error
        if self.response is None:
            raise RuntimeError('missing fake response')
        return self.response


class FakeLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, tuple[object, ...]]] = []

    def info(self, message: str, *args: object) -> None:
        self.events.append((message, args))


class AdobeDocsReaderTests(unittest.TestCase):
    def test_success_raw_with_fake_crawl4ai(self) -> None:
        fake_requests = FakeRequests(FakeResponse({'success': True, 'markdown': SECRET_MARKDOWN, 'filter': 'raw'}))
        logger = FakeLogger()

        result = adobe_docs_reader.read_adobe_url(
            'https://helpx.adobe.com/photoshop/desktop.html#intro',
            'photoshop',
            requests_module=fake_requests,
            crawl4ai_base_url='https://crawl.example',
            crawl4ai_token='token-test',
            timeout_s=7,
            logger_obj=logger,
        )

        self.assertEqual(result.status, adobe_docs_reader.STATUS_SUCCESS)
        self.assertEqual(result.product, adobe_docs_sources.PRODUCT_PHOTOSHOP)
        self.assertEqual(result.source_type, adobe_docs_sources.SOURCE_TYPE_HUB)
        self.assertEqual(result.canonical_url, 'https://helpx.adobe.com/photoshop/desktop.html')
        self.assertEqual(result.markdown, SECRET_MARKDOWN)
        self.assertEqual(result.chars, len(SECRET_MARKDOWN))
        self.assertEqual(result.headings, 1)
        self.assertEqual(result.link_count, 1)
        self.assertEqual(result.filter_used, 'raw')
        self.assertIn(adobe_docs_reader.REASON_CRAWL_RAW_PRIMARY, result.reason_codes)

        self.assertEqual(len(fake_requests.calls), 1)
        call = fake_requests.calls[0]
        self.assertEqual(call['url'], 'https://crawl.example/md')
        self.assertEqual(call['json'], {'url': 'https://helpx.adobe.com/photoshop/desktop.html', 'f': 'raw', 'c': '0'})
        self.assertEqual(call['headers']['Authorization'], 'Bearer token-test')
        self.assertEqual(call['timeout'], 7)

        self.assertNotIn(SECRET_MARKDOWN, repr(result))
        self.assertNotIn(result.canonical_url, repr(result))
        self.assertNotIn('Texte Adobe', _logger_dump(logger))

    def test_invalid_url_is_rejected_before_crawl4ai_call(self) -> None:
        fake_requests = FakeRequests(FakeResponse({'success': True, 'markdown': SECRET_MARKDOWN}))

        result = adobe_docs_reader.read_adobe_url(
            'https://community.adobe.com/p/photoshop',
            'photoshop',
            requests_module=fake_requests,
        )

        self.assertEqual(result.status, adobe_docs_reader.STATUS_INVALID_URL)
        self.assertEqual(result.reason_code, adobe_docs_sources.REASON_COMMUNITY_FORBIDDEN)
        self.assertEqual(result.markdown, '')
        self.assertFalse(fake_requests.calls)

    def test_wrong_product_is_rejected_before_crawl4ai_call(self) -> None:
        fake_requests = FakeRequests(FakeResponse({'success': True, 'markdown': SECRET_MARKDOWN}))

        result = adobe_docs_reader.read_adobe_url(
            'https://helpx.adobe.com/photoshop/desktop.html',
            'illustrator',
            requests_module=fake_requests,
        )

        self.assertEqual(result.status, adobe_docs_reader.STATUS_INVALID_URL)
        self.assertEqual(result.reason_code, adobe_docs_sources.REASON_WRONG_PRODUCT)
        self.assertFalse(fake_requests.calls)

    def test_timeout_is_reported_without_markdown(self) -> None:
        fake_requests = FakeRequests(error=TimeoutError('crawl timeout'))

        result = adobe_docs_reader.read_adobe_url(
            'https://helpx.adobe.com/photoshop/desktop.html',
            'photoshop',
            requests_module=fake_requests,
            crawl4ai_base_url='https://crawl.example',
        )

        self.assertEqual(result.status, adobe_docs_reader.STATUS_TIMEOUT)
        self.assertEqual(result.reason_code, adobe_docs_reader.REASON_CRAWL_TIMEOUT)
        self.assertEqual(result.markdown, '')
        self.assertEqual(len(fake_requests.calls), 1)

    def test_http_error_is_reported_without_markdown(self) -> None:
        fake_requests = FakeRequests(FakeResponse({'success': True, 'markdown': SECRET_MARKDOWN}, raise_error=RuntimeError('HTTP 500')))

        result = adobe_docs_reader.read_adobe_url(
            'https://helpx.adobe.com/photoshop/desktop.html',
            'photoshop',
            requests_module=fake_requests,
            crawl4ai_base_url='https://crawl.example',
        )

        self.assertEqual(result.status, adobe_docs_reader.STATUS_ERROR)
        self.assertEqual(result.reason_code, adobe_docs_reader.REASON_CRAWL_HTTP_ERROR)
        self.assertEqual(result.markdown, '')

    def test_connection_error_is_reported_without_markdown(self) -> None:
        fake_requests = FakeRequests(error=ConnectionError('crawl unavailable'))

        result = adobe_docs_reader.read_adobe_url(
            'https://helpx.adobe.com/photoshop/desktop.html',
            'photoshop',
            requests_module=fake_requests,
            crawl4ai_base_url='https://crawl.example',
        )

        self.assertEqual(result.status, adobe_docs_reader.STATUS_ERROR)
        self.assertEqual(result.reason_code, adobe_docs_reader.REASON_CRAWL_EXCEPTION)
        self.assertEqual(result.markdown, '')

    def test_empty_response_is_reported_as_empty(self) -> None:
        fake_requests = FakeRequests(FakeResponse({'success': True, 'markdown': '   ', 'filter': 'raw'}))

        result = adobe_docs_reader.read_adobe_url(
            'https://helpx.adobe.com/photoshop/desktop.html',
            'photoshop',
            requests_module=fake_requests,
            crawl4ai_base_url='https://crawl.example',
        )

        self.assertEqual(result.status, adobe_docs_reader.STATUS_EMPTY)
        self.assertEqual(result.reason_code, adobe_docs_reader.REASON_CRAWL_EMPTY)
        self.assertEqual(result.chars, 0)
        self.assertEqual(result.headings, 0)
        self.assertEqual(result.link_count, 0)

    def test_unsuccessful_response_is_error_without_returning_markdown(self) -> None:
        fake_requests = FakeRequests(FakeResponse({'success': False, 'markdown': SECRET_MARKDOWN, 'filter': 'raw'}))

        result = adobe_docs_reader.read_adobe_url(
            'https://helpx.adobe.com/photoshop/desktop.html',
            'photoshop',
            requests_module=fake_requests,
            crawl4ai_base_url='https://crawl.example',
        )

        self.assertEqual(result.status, adobe_docs_reader.STATUS_ERROR)
        self.assertEqual(result.reason_code, adobe_docs_reader.REASON_CRAWL_UNSUCCESSFUL)
        self.assertEqual(result.markdown, '')

    def test_logger_receives_content_free_metrics_only(self) -> None:
        fake_requests = FakeRequests(FakeResponse({'success': True, 'markdown': SECRET_MARKDOWN, 'filter': 'raw'}))
        logger = FakeLogger()

        result = adobe_docs_reader.read_adobe_url(
            'https://helpx.adobe.com/photoshop/desktop.html',
            'photoshop',
            requests_module=fake_requests,
            logger_obj=logger,
        )

        dumped = _logger_dump(logger)
        self.assertEqual(result.status, adobe_docs_reader.STATUS_SUCCESS)
        self.assertIn('adobe_docs_reader status=%s', dumped)
        self.assertIn(result.url_sha256_12, dumped)
        self.assertNotIn(SECRET_MARKDOWN, dumped)
        self.assertNotIn('Texte Adobe', dumped)

    def test_source_type_must_match_url_validation(self) -> None:
        fake_requests = FakeRequests(FakeResponse({'success': True, 'markdown': SECRET_MARKDOWN, 'filter': 'raw'}))

        result = adobe_docs_reader.read_adobe_url(
            'https://helpx.adobe.com/photoshop/desktop.html',
            'photoshop',
            source_type=adobe_docs_sources.SOURCE_TYPE_RELEASE_NOTES,
            requests_module=fake_requests,
        )

        self.assertEqual(result.status, adobe_docs_reader.STATUS_INVALID_URL)
        self.assertEqual(result.reason_code, adobe_docs_reader.REASON_SOURCE_TYPE_MISMATCH)
        self.assertFalse(fake_requests.calls)

    def test_raw_size_bound_truncates_in_memory_with_reason_code(self) -> None:
        fake_requests = FakeRequests(FakeResponse({'success': True, 'markdown': SECRET_MARKDOWN, 'filter': 'raw'}))

        result = adobe_docs_reader.read_adobe_url(
            'https://helpx.adobe.com/photoshop/desktop.html',
            'photoshop',
            requests_module=fake_requests,
            max_raw_chars=8,
        )

        self.assertEqual(result.status, adobe_docs_reader.STATUS_SUCCESS)
        self.assertEqual(result.markdown, SECRET_MARKDOWN[:8])
        self.assertTrue(result.markdown_truncated)
        self.assertIn(adobe_docs_reader.REASON_MARKDOWN_TRUNCATED, result.reason_codes)

    def test_no_temporary_file_is_opened(self) -> None:
        fake_requests = FakeRequests(FakeResponse({'success': True, 'markdown': SECRET_MARKDOWN, 'filter': 'raw'}))

        with patch.object(builtins, 'open', side_effect=AssertionError('file access forbidden')):
            result = adobe_docs_reader.read_adobe_url(
                'https://helpx.adobe.com/photoshop/desktop.html',
                'photoshop',
                requests_module=fake_requests,
            )

        self.assertEqual(result.status, adobe_docs_reader.STATUS_SUCCESS)


def _logger_dump(logger: FakeLogger) -> str:
    return '\n'.join(f'{message} {args!r}' for message, args in logger.events)


if __name__ == '__main__':
    unittest.main()
