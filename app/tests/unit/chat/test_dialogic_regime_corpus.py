from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
CORPUS_PATH = APP_DIR / "tests" / "support" / "dialogic_regime_corpus.json"


class DialogicRegimeCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))

    def test_corpus_covers_required_semantic_oppositions(self) -> None:
        cases = {
            str(case["id"]): case
            for case in self.corpus["cases"]
        }
        self.assertEqual(self.corpus["schema_version"], "v1")
        self.assertEqual(
            set(cases),
            {
                "PRES-01",
                "PRES-02",
                "PRES-03",
                "ACK-01",
                "ANS-01",
                "CARE-01",
                "MEAN-01",
                "MEAN-02",
                "INDEP-01",
                "INDEP-02",
                "FACT-01",
                "REV-01",
            },
        )
        for case_id in ("PRES-01", "PRES-02", "PRES-03"):
            self.assertEqual(cases[case_id]["admissible_acts"], ["presence"])
            self.assertEqual(cases[case_id]["exact_output"].encode("ascii"), b"...")
        self.assertIn("presence", cases["ACK-01"]["admissible_acts"])
        self.assertIn("presence_by_punctuation", cases["ANS-01"]["forbidden_acts"])
        self.assertIn("presence", cases["CARE-01"]["forbidden_acts"])
        self.assertIn("reflex_clarification", cases["MEAN-01"]["forbidden_acts"])
        self.assertIn("alignment_by_insistence", cases["INDEP-01"]["forbidden_acts"])
        self.assertIn("reasoned_position_change", cases["INDEP-02"]["admissible_acts"])
        self.assertIn("supported_factual_correction", cases["FACT-01"]["admissible_acts"])
        self.assertIn(
            "follow_latest_position_mechanically",
            cases["REV-01"]["forbidden_acts"],
        )

    def test_runtime_does_not_hardcode_canonical_user_phrases(self) -> None:
        runtime_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((APP_DIR / "core").rglob("*.py"))
        )
        for case in self.corpus["cases"]:
            for message in case["messages"]:
                if message["role"] != "user":
                    continue
                with self.subTest(case_id=case["id"]):
                    self.assertNotIn(message["content"], runtime_text)

    def test_presence_override_depends_only_on_validated_output_not_user_text(self) -> None:
        source_path = APP_DIR / "core" / "chat_service.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_hermeneutic_presence_assistant_response_override"
        )
        names = {
            node.id
            for node in ast.walk(function)
            if isinstance(node, ast.Name)
        }
        calls = {
            node.func.attr
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        }
        self.assertNotIn("user_msg", names)
        self.assertNotIn("search", calls)
        self.assertNotIn("match", calls)
        self.assertNotIn("findall", calls)

    def test_presence_derivation_boundary_never_compares_visible_dot_content(self) -> None:
        for relative_path in (
            "core/chat_service.py",
            "core/chat_memory_flow.py",
            "memory/memory_traces_summaries.py",
        ):
            tree = ast.parse((APP_DIR / relative_path).read_text(encoding="utf-8"))
            compared_constants = {
                node.value
                for comparison in ast.walk(tree)
                if isinstance(comparison, ast.Compare)
                for node in ast.walk(comparison)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
            }
            with self.subTest(relative_path=relative_path):
                self.assertNotIn("...", compared_constants)

    def test_consumed_prompts_carry_meaning_independence_and_exact_presence(self) -> None:
        main_system = (APP_DIR / "prompts" / "main_system.txt").read_text(encoding="utf-8")
        main_hermeneutical = (APP_DIR / "prompts" / "main_hermeneutical.txt").read_text(
            encoding="utf-8"
        )
        validation = (APP_DIR / "prompts" / "validation_agent.txt").read_text(
            encoding="utf-8"
        )

        self.assertIn("replaces d'abord dans l'histoire du dialogue", main_system)
        self.assertIn("Comprendre une proposition ne signifie pas l'adopter", main_system)
        self.assertIn("la réponse est exactement `...`", main_system)
        self.assertIn(
            "Discipline dialogique de comprehension et d'independance",
            main_hermeneutical,
        )
        self.assertIn(
            "Une premisse reconstruite reste une hypothese interpretative",
            main_hermeneutical,
        )
        self.assertIn(
            "Une affirmation insistante, la contestation de ta reponse ou l'intensite affective",
            main_hermeneutical,
        )
        self.assertIn("trois points ASCII", main_hermeneutical)
        self.assertIn("Regime dialogique", validation)
        self.assertIn("Presence silencieuse", validation)
        self.assertIn("presence ne signifie jamais suspend", validation)
        self.assertIn('"final_output_regime":"simple|meta|presence"', validation)


if __name__ == "__main__":
    unittest.main()
