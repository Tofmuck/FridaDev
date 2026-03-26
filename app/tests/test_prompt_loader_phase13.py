from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import config
from core import prompt_loader


class PromptLoaderPhase13Tests(unittest.TestCase):
    def test_main_prompt_paths_follow_phase13_convention(self) -> None:
        self.assertEqual(config.MAIN_SYSTEM_PROMPT_PATH, 'prompts/main_system.txt')
        self.assertEqual(config.MAIN_HERMENEUTICAL_PROMPT_PATH, 'prompts/main_hermeneutical.txt')
        self.assertEqual(config.SUMMARY_SYSTEM_PROMPT_PATH, 'prompts/summary_system.txt')
        self.assertEqual(config.WEB_REFORMULATION_PROMPT_PATH, 'prompts/web_reformulation.txt')

    def test_main_system_prompt_reads_centralized_prompt_file(self) -> None:
        path = prompt_loader.resolve_app_prompt_path(config.MAIN_SYSTEM_PROMPT_PATH)
        self.assertTrue(path.exists())
        self.assertEqual(prompt_loader.get_main_system_prompt(), path.read_text(encoding='utf-8').strip())
        self.assertIn('Cadre de réponse', prompt_loader.get_main_system_prompt())

    def test_main_hermeneutical_prompt_reads_centralized_prompt_file(self) -> None:
        path = prompt_loader.resolve_app_prompt_path(config.MAIN_HERMENEUTICAL_PROMPT_PATH)
        self.assertTrue(path.exists())
        self.assertEqual(
            prompt_loader.get_main_hermeneutical_prompt(),
            path.read_text(encoding='utf-8').strip(),
        )
        self.assertIn(
            "Contrat d'interpretation du prompt augmente",
            prompt_loader.get_main_hermeneutical_prompt(),
        )

    def test_main_hermeneutical_prompt_covers_runtime_bricks_and_explicit_limits(self) -> None:
        prompt = prompt_loader.get_main_hermeneutical_prompt()

        for snippet in [
            "Lis ce bloc comme un contrat d'interpretation stable.",
            "Priorite 1 : la question utilisateur finale",
            "[REFERENCE TEMPORELLE]",
            "[il y a ...]",
            "[-- silence de X --]",
            "[IDENTITE DU MODELE]",
            "[IDENTITE DE L'UTILISATEUR]",
            "[Resume de la periode ...]",
            "[Indices contextuels recents]",
            "[Contexte du souvenir -- resume ...]",
            "[Memoire -- souvenirs pertinents]",
            "[RECHERCHE WEB -- ...]",
            "[FIN DES RESULTATS WEB]",
            "Question :",
            "stability, recurrence et confidence reste partiellement provisoire",
            "Tu ne vois pas les sorties brutes de l'identity extractor.",
            "Tu ne vois pas les evenements internes de pipeline",
        ]:
            self.assertIn(snippet, prompt)

    def test_summary_system_prompt_reads_centralized_prompt_file(self) -> None:
        path = prompt_loader.resolve_app_prompt_path(config.SUMMARY_SYSTEM_PROMPT_PATH)
        self.assertTrue(path.exists())
        self.assertEqual(prompt_loader.get_summary_system_prompt(), path.read_text(encoding='utf-8').strip())
        self.assertIn('Tu es un assistant de synthèse.', prompt_loader.get_summary_system_prompt())

    def test_web_reformulation_prompt_reads_centralized_prompt_file(self) -> None:
        path = prompt_loader.resolve_app_prompt_path(config.WEB_REFORMULATION_PROMPT_PATH)
        self.assertTrue(path.exists())
        self.assertEqual(prompt_loader.get_web_reformulation_prompt(), path.read_text(encoding='utf-8').strip())
        self.assertIn('Nous sommes le {today}.', prompt_loader.get_web_reformulation_prompt())
