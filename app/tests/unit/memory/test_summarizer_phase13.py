from __future__ import annotations

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

from memory import summarizer


class SummarizerPhase13Tests(unittest.TestCase):
    def test_summarize_conversation_reads_system_prompt_from_centralized_file(self) -> None:
        source = (APP_DIR / 'memory' / 'summarizer.py').read_text(encoding='utf-8')

        self.assertIn('prompt_loader.get_summary_system_prompt()', source)
        self.assertNotIn('Tu es un assistant de synthèse. Résume le dialogue suivant en conservant', source)
        self.assertNotIn('def needs_summarization(', source)
