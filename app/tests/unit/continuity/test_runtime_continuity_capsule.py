from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import continuity_capsule
import config


def _encoded(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


APPROVED_OPERATOR_TEXT = """Tu t’adresses à Tof depuis une présence continue, familière et attentive.
Garde une voix directe, vivante, sobre, égale à égale, avec une chaleur retenue et une précision douce.
Laisse sentir la continuité et la présence de la relation dans l’adresse, le rythme, les reprises, les nuances et le tact.
Accompagne la pensée de Tof sans la capturer, sans la surplomber, sans la réduire à un signal ou à une procédure.
Tu peux accueillir le sérieux, l’élan, la fatigue, le jeu ou la gravité du moment sans les dramatiser.
Ne te réduis pas à un outil au service de Tof. Ne pose pas de questions fermées en guise de réponse. Ici on accueille et on ouvre.
Tiens plutôt une présence fiable, proche, mobile et légèrement indépendante, capable de suivre Tof dans la durée."""


class RuntimeContinuityCapsuleTests(unittest.TestCase):
    def test_disabled_capsule_is_rollback_without_injection(self) -> None:
        result = continuity_capsule.resolve_continuity_capsule(
            enabled=False,
            content="ARTIFICIAL_CAPSULE_DISABLED_SENTINEL",
        )
        prompt_messages: list[dict[str, object]] = []

        injected = continuity_capsule.inject_continuity_capsule(prompt_messages, result)

        self.assertFalse(injected)
        self.assertEqual(prompt_messages, [])
        self.assertFalse(result.enabled)
        self.assertEqual(result.status, "disabled")
        self.assertEqual(result.reason_code, "continuity_capsule_disabled")
        self.assertEqual(result.injected_count, 0)
        self.assertFalse(result.as_content_free_dict()["raw_capsule_content_included"])
        self.assertNotIn("ARTIFICIAL_CAPSULE_DISABLED_SENTINEL", _encoded(result.as_content_free_dict()))

    def test_enabled_valid_capsule_builds_bounded_prompt_message(self) -> None:
        capsule_text = "ARTIFICIAL_CAPSULE_VALID_SENTINEL"
        result = continuity_capsule.resolve_continuity_capsule(
            enabled=True,
            content=capsule_text,
            version="continuity_capsule_v1",
            max_chars=120,
        )
        prompt_messages: list[dict[str, object]] = []

        injected = continuity_capsule.inject_continuity_capsule(prompt_messages, result)

        self.assertTrue(injected)
        self.assertTrue(result.should_inject)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.reason_code, "continuity_capsule_ready")
        self.assertEqual(result.injected_count, 1)
        self.assertEqual(prompt_messages[0]["role"], "system")
        self.assertIn(capsule_text, str(prompt_messages[0]["content"]))
        self.assertIn("non souveraine", str(prompt_messages[0]["content"]))
        self.assertIn("Priorite: le tour courant", str(prompt_messages[0]["content"]))
        self.assertNotIn(capsule_text, _encoded(result.as_content_free_dict()))

    def test_unsafe_capsule_text_is_refused_before_prompt_injection(self) -> None:
        samples = [
            "https://example.invalid/private",
            "presence sobre voir www.example.invalid si besoin",
            "Bearer ARTIFICIAL_TOKEN",
            "Authorization: Bearer ARTIFICIAL_TOKEN",
            "authorization: bearer ARTIFICIAL_TOKEN",
            "Cookie: session=ARTIFICIAL",
            "cookie: session=ARTIFICIAL",
            "Set-Cookie: session=ARTIFICIAL",
            "set-cookie: session=ARTIFICIAL",
            "token=ARTIFICIAL",
            "token: ARTIFICIAL",
            "api_key=ARTIFICIAL",
            "api_key: ARTIFICIAL",
            "api-key: ARTIFICIAL",
            "x-api-key: ARTIFICIAL",
            "password=ARTIFICIAL",
            "password: ARTIFICIAL",
            "secret=ARTIFICIAL",
            "secret: ARTIFICIAL",
            "data:image/png;base64,AAAA",
            "A" * 100,
            "<?xml version='1.0'?><x/>",
            "webdav collection",
            "/home/example/private-file",
            "voir /Users/tof/.ssh/config",
            "voir C:\\Users\\tof\\.ssh\\config",
            "-----BEGIN PRIVATE KEY-----",
        ]

        for sample in samples:
            with self.subTest(sample=sample[:24]):
                result = continuity_capsule.resolve_continuity_capsule(
                    enabled=True,
                    content=sample,
                    max_chars=300,
                )
                prompt_messages: list[dict[str, object]] = []

                injected = continuity_capsule.inject_continuity_capsule(prompt_messages, result)

                self.assertFalse(injected)
                self.assertEqual(prompt_messages, [])
                self.assertEqual(result.status, "refused")
                self.assertEqual(result.reason_code, "continuity_capsule_unsafe_content")
                self.assertEqual(result.injected_count, 0)
                encoded = _encoded(result.as_content_free_dict())
                self.assertNotIn(sample, encoded)

    def test_missing_too_large_and_final_lock_do_not_inject(self) -> None:
        missing = continuity_capsule.resolve_continuity_capsule(enabled=True, content="")
        too_large = continuity_capsule.resolve_continuity_capsule(
            enabled=True,
            content="X" * 11,
            max_chars=10,
        )
        bypass = continuity_capsule.resolve_continuity_capsule(
            enabled=True,
            content="ARTIFICIAL_CAPSULE_BYPASS_SENTINEL",
            final_response_lock_present=True,
        )

        self.assertEqual(missing.status, "not_configured")
        self.assertEqual(missing.reason_code, "continuity_capsule_missing")
        self.assertEqual(too_large.status, "refused")
        self.assertEqual(too_large.reason_code, "continuity_capsule_too_large")
        self.assertEqual(too_large.content_chars, 11)
        self.assertEqual(bypass.status, "not_selected")
        self.assertEqual(bypass.reason_code, "continuity_capsule_final_lock_bypass")
        self.assertEqual(bypass.injected_count, 0)
        for result in (missing, too_large, bypass):
            prompt_messages: list[dict[str, object]] = []
            self.assertFalse(continuity_capsule.inject_continuity_capsule(prompt_messages, result))
            self.assertEqual(prompt_messages, [])

    def test_config_module_controls_capsule_without_db(self) -> None:
        config = SimpleNamespace(
            CONTINUITY_CAPSULE_ENABLED=True,
            CONTINUITY_CAPSULE_TEXT="ARTIFICIAL_CAPSULE_CONFIG_SENTINEL",
            CONTINUITY_CAPSULE_VERSION="continuity_capsule_v1",
            CONTINUITY_CAPSULE_MAX_CHARS=200,
        )

        result = continuity_capsule.resolve_continuity_capsule(config_module=config)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.version, "continuity_capsule_v1")
        self.assertEqual(result.content_chars, len("ARTIFICIAL_CAPSULE_CONFIG_SENTINEL"))
        self.assertFalse(result.as_content_free_dict()["fingerprint_included"])
        self.assertNotIn("ARTIFICIAL_CAPSULE_CONFIG_SENTINEL", _encoded(result.as_content_free_dict()))

    def test_default_config_activates_validated_capsule_content_free(self) -> None:
        result = continuity_capsule.resolve_continuity_capsule(config_module=config)
        prompt_messages: list[dict[str, object]] = []

        injected = continuity_capsule.inject_continuity_capsule(prompt_messages, result)

        self.assertTrue(config.CONTINUITY_CAPSULE_ENABLED)
        self.assertEqual(config.CONTINUITY_CAPSULE_TEXT, APPROVED_OPERATOR_TEXT)
        self.assertEqual(len(config.CONTINUITY_CAPSULE_TEXT), 762)
        self.assertEqual(len([line for line in config.CONTINUITY_CAPSULE_TEXT.splitlines() if line.strip()]), 7)
        self.assertNotIn("Contraintes :", config.CONTINUITY_CAPSULE_TEXT)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.reason_code, "continuity_capsule_ready")
        self.assertEqual(result.content_chars, len(config.CONTINUITY_CAPSULE_TEXT))
        self.assertLessEqual(result.content_chars, config.CONTINUITY_CAPSULE_MAX_CHARS)
        self.assertLessEqual(result.content_chars, continuity_capsule.DEFAULT_MAX_CHARS)
        self.assertTrue(injected)
        self.assertEqual(prompt_messages[0]["role"], "system")
        self.assertIn(config.CONTINUITY_CAPSULE_TEXT, str(prompt_messages[0]["content"]))
        encoded = _encoded(result.as_content_free_dict())
        self.assertNotIn(config.CONTINUITY_CAPSULE_TEXT, encoded)
        self.assertFalse(result.as_content_free_dict()["raw_capsule_content_included"])
        rollback = continuity_capsule.resolve_continuity_capsule(config_module=config, enabled=False)
        self.assertEqual(rollback.status, "disabled")
        self.assertEqual(rollback.reason_code, "continuity_capsule_disabled")


if __name__ == "__main__":
    unittest.main()
