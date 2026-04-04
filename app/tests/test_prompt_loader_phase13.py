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
        self.assertNotEqual(config.MAIN_SYSTEM_PROMPT_PATH, config.MAIN_HERMENEUTICAL_PROMPT_PATH)

    def test_main_system_prompt_reads_centralized_prompt_file(self) -> None:
        path = prompt_loader.resolve_app_prompt_path(config.MAIN_SYSTEM_PROMPT_PATH)
        self.assertTrue(path.exists())
        self.assertEqual(prompt_loader.get_main_system_prompt(), path.read_text(encoding='utf-8').strip())
        self.assertIn('Cadre de réponse', prompt_loader.get_main_system_prompt())

    def test_main_system_prompt_enforces_strict_plain_text_contract(self) -> None:
        prompt = prompt_loader.get_main_system_prompt()

        for snippet in [
            'Par défaut, tu réponds en texte brut strict',
            "Tu n'utilises pas de mise en forme Markdown visible",
            "pas de titres `#`",
            "pas de `**`",
            "pas de `---`",
            "pas de blockquotes `>`",
            "Par défaut, tu n'utilises ni puces, ni listes numérotées",
            "Tu n'utilises pas de code fences sauf si l'utilisateur demande explicitement du code.",
            "Si l'utilisateur demande explicitement un plan, des étapes ou une liste",
        ]:
            self.assertIn(snippet, prompt)

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
            "Priorite 3 : le bloc [JUGEMENT HERMENEUTIQUE]",
            "Regles candidates de resolution",
            "Discipline temporelle d'application",
            "NOW: ...",
            "TIMEZONE: ...",
            "Si l'utilisateur dit explicitement qu'une information B remplace A",
            "Si plusieurs souvenirs pertinents se contredisent",
            "Le tri fort des briques faibles releve surtout du pipeline amont.",
            "[RÉFÉRENCE TEMPORELLE]",
            "[à l'instant]",
            "[il y a ...]",
            "[aujourd'hui à HhMM]",
            "[hier à HhMM]",
            "[— silence de X —]",
            "ne dis jamais que tu n'as pas acces au temps de reference du tour",
            "N'utilise `ce matin`, `cet apres-midi`, `ce soir` ou `cette nuit`",
            "quand est-ce qu'on a parle la derniere fois ?",
            "`relatif` prioritaire",
            "`absolu court`",
            "[IDENTITE DU MODELE]",
            "[IDENTITE DE L'UTILISATEUR]",
            "[Resume de la periode ...]",
            "[Indices contextuels recents]",
            "[Contexte du souvenir -- resume ...]",
            "[Memoire -- souvenirs pertinents]",
            "[RECHERCHE WEB -- ...]",
            "[FIN DES RESULTATS WEB]",
            "[JUGEMENT HERMENEUTIQUE]",
            "tu ne re-deduis ni `validation_decision` ni `final_judgment_posture`",
            "Question :",
            "stability, recurrence et confidence reste partiellement provisoire",
            "Tu ne vois pas les sorties brutes de l'identity extractor.",
            "Tu ne vois pas les evenements internes de pipeline",
        ]:
            self.assertIn(snippet, prompt)

    def test_main_system_and_hermeneutical_prompts_stay_physically_separate(self) -> None:
        system_path = prompt_loader.resolve_app_prompt_path(config.MAIN_SYSTEM_PROMPT_PATH)
        hermeneutical_path = prompt_loader.resolve_app_prompt_path(config.MAIN_HERMENEUTICAL_PROMPT_PATH)

        self.assertNotEqual(system_path, hermeneutical_path)
        self.assertNotEqual(prompt_loader.get_main_system_prompt(), prompt_loader.get_main_hermeneutical_prompt())
        self.assertIn('Cadre de réponse', prompt_loader.get_main_system_prompt())
        self.assertIn("Contrat d'interpretation du prompt augmente", prompt_loader.get_main_hermeneutical_prompt())

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
