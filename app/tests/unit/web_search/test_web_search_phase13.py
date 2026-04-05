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


class WebSearchPhase13Tests(unittest.TestCase):
    def test_reformulate_reads_system_prompt_from_centralized_file(self) -> None:
        source = (APP_DIR / 'tools' / 'web_search.py').read_text(encoding='utf-8')

        self.assertIn('prompt_loader.get_web_reformulation_prompt().format(today=today)', source)
        self.assertNotIn(
            'Tu es un assistant qui transforme un message en requête de recherche web courte et efficace.',
            source,
        )
        self.assertIn('def build_context(', source)
        self.assertIn('requests_module: Any = requests', source)
        self.assertIn('llm_module: Any | None = None', source)
        self.assertNotIn('ticketmaster', source)
