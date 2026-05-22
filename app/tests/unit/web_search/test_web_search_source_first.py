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

from tools import web_search_profile, web_search_source_first


class WebSearchSourceFirstTests(unittest.TestCase):
    def _plan(self, message: str):
        return web_search_source_first.build_source_first_plan(
            message,
            message,
            web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
        )

    def test_adobe_photoshop_authority_and_domains(self) -> None:
        plan = self._plan("documentation officielle Adobe Photoshop")

        self.assertTrue(plan.active)
        self.assertEqual(plan.authority, "Adobe")
        self.assertEqual(plan.product, "Photoshop")
        self.assertEqual(plan.probable_domains, ("helpx.adobe.com", "developer.adobe.com", "adobe.com"))

    def test_adobe_illustrator_authority_and_domains(self) -> None:
        plan = self._plan("documentation officielle Adobe Illustrator")

        self.assertTrue(plan.active)
        self.assertEqual(plan.authority, "Adobe")
        self.assertEqual(plan.product, "Illustrator")

    def test_microsoft_graph_authority_and_learn_domain(self) -> None:
        plan = self._plan("documentation officielle Microsoft Graph API")

        self.assertTrue(plan.active)
        self.assertEqual(plan.authority, "Microsoft")
        self.assertEqual(plan.product, "Graph API")
        self.assertEqual(plan.probable_domains, ("learn.microsoft.com",))

    def test_stripe_checkout_authority_and_docs_domain(self) -> None:
        plan = self._plan("documentation officielle Stripe Checkout")

        self.assertTrue(plan.active)
        self.assertEqual(plan.authority, "Stripe")
        self.assertEqual(plan.product, "Checkout")
        self.assertEqual(plan.probable_domains, ("docs.stripe.com",))

    def test_openrouter_web_search_authority_and_docs_domain(self) -> None:
        plan = self._plan("documentation officielle OpenRouter web_search")

        self.assertTrue(plan.active)
        self.assertEqual(plan.authority, "OpenRouter")
        self.assertEqual(plan.product, "web search")
        self.assertIn("openrouter.ai/docs", plan.probable_domains)

    def test_mdn_fetch_api_authority_and_domain(self) -> None:
        plan = self._plan("documentation officielle MDN fetch API")

        self.assertTrue(plan.active)
        self.assertEqual(plan.authority, "MDN / Mozilla")
        self.assertEqual(plan.product, "fetch API")
        self.assertEqual(plan.probable_domains, ("developer.mozilla.org",))

    def test_docker_compose_authority_and_domain(self) -> None:
        plan = self._plan("documentation officielle Docker compose")

        self.assertTrue(plan.active)
        self.assertEqual(plan.authority, "Docker")
        self.assertEqual(plan.product, "Compose")
        self.assertEqual(plan.probable_domains, ("docs.docker.com",))

    def test_generic_documentation_does_not_promote_fixture_vendor(self) -> None:
        plan = self._plan("documentation officielle")

        self.assertFalse(plan.active)
        self.assertEqual(plan.authority, "")
        self.assertEqual(plan.probable_domains, ())
        self.assertIn("generic_documentation_request_without_authority", plan.reason_codes)

    def test_api_documentation_alone_does_not_promote_fixture_vendor(self) -> None:
        plan = self._plan("API documentation")

        self.assertFalse(plan.active)
        self.assertEqual(plan.authority, "")
        self.assertEqual(plan.probable_domains, ())

    def test_unknown_authority_is_extracted_without_domain_map(self) -> None:
        plan = self._plan("documentation officielle AcmeDB vector search")

        self.assertTrue(plan.active)
        self.assertEqual(plan.authority, "AcmeDB")
        self.assertEqual(plan.product, "vector")
        self.assertEqual(plan.probable_domains, ())
        self.assertIn("authority_extracted_without_domain_map", plan.reason_codes)

    def test_non_documentation_profile_is_not_source_first(self) -> None:
        plan = web_search_source_first.build_source_first_plan(
            "actualité IA Europe 2026",
            "actualité IA Europe 2026",
            web_search_profile.PROFILE_ACTUALITE,
        )

        self.assertFalse(plan.active)
        self.assertEqual(plan.policy_kind, "none")


if __name__ == "__main__":
    unittest.main()
