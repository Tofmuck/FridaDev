from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import web_read_state


class WebReadStateTests(unittest.TestCase):
    def test_canonical_read_state_values_match_runtime_contract(self) -> None:
        self.assertEqual(web_read_state.READ_STATE_PAGE_READ, 'page_read')
        self.assertEqual(web_read_state.READ_STATE_PAGE_PARTIALLY_READ, 'page_partially_read')
        self.assertEqual(
            web_read_state.READ_STATE_PAGE_NOT_READ_CRAWL_EMPTY,
            'page_not_read_crawl_empty',
        )
        self.assertEqual(web_read_state.READ_STATE_PAGE_NOT_READ_ERROR, 'page_not_read_error')
        self.assertEqual(
            web_read_state.READ_STATE_PAGE_NOT_READ_SNIPPET_FALLBACK,
            'page_not_read_snippet_fallback',
        )


if __name__ == '__main__':
    unittest.main()
