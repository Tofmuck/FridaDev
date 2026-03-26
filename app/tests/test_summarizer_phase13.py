from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from memory import summarizer


class SummarizerPhase13Tests(unittest.TestCase):
    def test_summarize_conversation_reads_system_prompt_from_centralized_file(self) -> None:
        source = (APP_DIR / 'memory' / 'summarizer.py').read_text(encoding='utf-8')

        self.assertIn('prompt_loader.get_summary_system_prompt()', source)
        self.assertNotIn('Tu es un assistant de synthèse. Résume le dialogue suivant en conservant', source)
