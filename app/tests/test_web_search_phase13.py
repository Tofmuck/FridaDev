from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


class WebSearchPhase13Tests(unittest.TestCase):
    def test_reformulate_reads_system_prompt_from_centralized_file(self) -> None:
        source = (APP_DIR / 'tools' / 'web_search.py').read_text(encoding='utf-8')

        self.assertIn('prompt_loader.get_web_reformulation_prompt().format(today=today)', source)
        self.assertNotIn(
            'Tu es un assistant qui transforme un message en requête de recherche web courte et efficace.',
            source,
        )
