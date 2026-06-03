from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import catalogue_client as catalogue
from biblio import librarian_navigation_runtime as navigation_runtime
from biblio import librarian_tools as tools


class BiblioNavigationRuntimeTests(unittest.TestCase):
    def test_tool_lines_include_chapter_hint_for_navigation(self) -> None:
        result = tools.BiblioLibrarianToolResult(
            tool_name=tools.TOOL_PAGE_READ,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_PAGE,
            observation=tools.BiblioLibrarianToolObservation(
                tool_name=tools.TOOL_PAGE_READ,
                endpoint_kind=catalogue.ENDPOINT_PAGE,
                status=tools.STATUS_OK,
                reason_code=tools.REASON_OK,
                fields={},
            ),
            document_summary={"document_id": "doc-1", "doc_id_short": "doc-1", "title": "Platon"},
            chapter_hint={
                "chapter_no": 4,
                "title": "Theetete",
                "unit_start": 25,
                "unit_end": 32,
                "source": "toc",
                "next_chapter_no": 5,
                "next_chapter_title": "Sophiste",
            },
            positions=({"page_no": 28},),
            page_text="Texte borne",
        )

        lines = navigation_runtime._tool_lines(result)
        joined = "\n".join(lines)

        self.assertIn("Repere TOC: chapitre 4 - Theetete", joined)
        self.assertIn("Chapitre suivant: 5 - Sophiste", joined)


if __name__ == "__main__":
    unittest.main()
