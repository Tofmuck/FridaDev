from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support import web_search_golden_matrix


class WebSearchGoldenMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = web_search_golden_matrix.exercise_web_matrix()
        cls.projection = tuple(
            web_search_golden_matrix.project_web_case(case) for case in cls.cases
        )

    def test_status_reason_and_evidence_matrix_is_exact(self) -> None:
        web_search_golden_matrix.assert_web_golden_matrix(self.projection)

    def test_context_golden_is_structural_and_content_free(self) -> None:
        web_search_golden_matrix.assert_content_free_projection(self.projection)
        for row in self.projection:
            item = dict(zip(web_search_golden_matrix.GOLDEN_FIELDS, row))
            with self.subTest(case_id=item["case_id"]):
                self.assertEqual(item["context_injected"], item["event_context_injected"])
                self.assertEqual(item["context_injected"], bool(item["used_content_kinds"]))

    def test_runtime_event_matrix_redacts_all_raw_sentinels(self) -> None:
        encoded = json.dumps(
            [case["events"] for case in self.cases],
            ensure_ascii=False,
            sort_keys=True,
        )
        for sentinel in (
            web_search_golden_matrix.RAW_USER_SENTINEL,
            web_search_golden_matrix.RAW_QUERY_SENTINEL,
            web_search_golden_matrix.RAW_CONTENT_SENTINEL,
            web_search_golden_matrix.RAW_URL_SENTINEL,
            web_search_golden_matrix.RAW_EXCEPTION_SENTINEL,
            web_search_golden_matrix.RAW_SECRET_SENTINEL,
        ):
            self.assertNotIn(sentinel, encoded)
        self.assertNotIn("https://", encoded)
        for row in self.projection:
            item = dict(zip(web_search_golden_matrix.GOLDEN_FIELDS, row))
            self.assertFalse(item["event_query_included"])
            self.assertFalse(item["event_explicit_url_included"])

    def test_golden_rejects_controlled_semantic_and_content_mutations(self) -> None:
        indexes = {name: index for index, name in enumerate(web_search_golden_matrix.GOLDEN_FIELDS)}
        mutations: list[list[list[object]]] = []
        for row_index, field, value in (
            (4, "status", "error"),
            (1, "read_state", "page_read"),
            (3, "used_content_kinds", ("crawl_markdown",)),
            (6, "web_evidence_status", "sufficient"),
            (7, "error_event_count", 2),
        ):
            mutated = [list(row) for row in copy.deepcopy(self.projection)]
            mutated[row_index][indexes[field]] = value
            mutations.append(mutated)
        for mutated in mutations:
            with self.assertRaises(AssertionError):
                web_search_golden_matrix.assert_web_golden_matrix(
                    tuple(tuple(row) for row in mutated)
                )

        raw_mutation = list(copy.deepcopy(self.projection))
        raw_mutation.append((web_search_golden_matrix.RAW_CONTENT_SENTINEL,))
        with self.assertRaises(AssertionError):
            web_search_golden_matrix.assert_content_free_projection(raw_mutation)


if __name__ == "__main__":
    unittest.main()
