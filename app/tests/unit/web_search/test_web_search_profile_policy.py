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

from tools import web_search_profile, web_search_profile_policy, web_search_source_first


class WebSearchProfilePolicyTests(unittest.TestCase):
    def test_documentation_officielle_is_strict_source_first_when_authority_is_named(self) -> None:
        plan = web_search_source_first.build_source_first_plan(
            "documentation officielle Adobe Photoshop",
            "Adobe Photoshop documentation officielle",
            web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
        )
        policy = web_search_profile_policy.build_profile_policy(
            web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
            source_first_plan=plan,
        )

        self.assertEqual(policy.mode, 'source_first_strict_when_authority_named')
        self.assertIn('helpx.adobe.com', policy.expected_domains)
        self.assertIn('developer.adobe.com', policy.expected_domains)
        self.assertIn('stackoverflow.com', policy.downrank_domains)
        self.assertIn('third_party_qa_secondary_not_primary', policy.reason_codes)

    def test_documentation_officielle_unknown_authority_stays_open_assisted(self) -> None:
        plan = web_search_source_first.build_source_first_plan(
            "peux-tu trouver la documentation officielle de FooBar API",
            "FooBar API documentation officielle",
            web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
        )
        policy = web_search_profile_policy.build_profile_policy(
            web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
            source_first_plan=plan,
        )

        self.assertTrue(plan.active)
        self.assertEqual(plan.authority, 'FooBar')
        self.assertEqual(policy.mode, 'open_assisted_when_authority_unknown_or_floue')
        self.assertEqual(policy.expected_domains, ())
        self.assertIn('documentation_open_assisted_no_invented_authority', policy.reason_codes)

    def test_administratif_francais_marks_education_official_and_unions_situated_secondary(self) -> None:
        policy = web_search_profile_policy.build_profile_policy(
            web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS
        )

        self.assertIn('education.gouv.fr', policy.expected_domains)
        self.assertIn('eduscol.education.fr', policy.expected_domains)
        self.assertIn('enseignementsup-recherche.gouv.fr', policy.expected_domains)
        self.assertIn('onisep.fr', policy.expected_domains)
        self.assertIn('ac-*.fr', policy.expected_domains)
        self.assertIn('sudeducation.org', policy.secondary_domains)
        self.assertIn('cgt.fr', policy.secondary_domains)
        self.assertNotIn('sudeducation.org', policy.expected_domains)
        self.assertIn('union_sources_situated_secondary_not_administrative_authority', policy.reason_codes)

    def test_union_source_alone_is_visible_but_insufficient_for_administrative_authority(self) -> None:
        evidence = web_search_profile_policy.evaluate_profile_evidence(
            web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS,
            sources=[
                {
                    'url': 'https://www.sudeducation.org/communique-reforme',
                    'source_domain': 'www.sudeducation.org',
                    'used_in_prompt': True,
                    'used_content_kind': 'crawl_markdown',
                    'content_used': 'contenu situe',
                }
            ],
            policy_fields=web_search_profile_policy.build_profile_policy(
                web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS
            ).as_observability_fields(),
        )

        self.assertTrue(evidence['profile_situated_source_present'])
        self.assertTrue(evidence['profile_situated_material_used'])
        self.assertFalse(evidence['profile_expected_material_used'])
        self.assertTrue(evidence['profile_insufficient_evidence'])
        self.assertIn(
            'situated_secondary_without_official_material',
            evidence['profile_insufficient_evidence_reason_codes'],
        )

    def test_official_education_material_satisfies_administrative_expected_domain(self) -> None:
        evidence = web_search_profile_policy.evaluate_profile_evidence(
            web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS,
            sources=[
                {
                    'url': 'https://eduscol.education.fr/programmes/philosophie-terminale',
                    'used_in_prompt': True,
                    'used_content_kind': 'crawl_markdown',
                    'content_used': 'programme officiel',
                }
            ],
            policy_fields=web_search_profile_policy.build_profile_policy(
                web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS
            ).as_observability_fields(),
        )

        self.assertTrue(evidence['profile_expected_material_used'])
        self.assertFalse(evidence['profile_insufficient_evidence'])

    def test_academique_policy_is_broad_not_philosophy_only(self) -> None:
        policy = web_search_profile_policy.build_profile_policy(web_search_profile.PROFILE_ACADEMIQUE)

        self.assertIn('arxiv.org', policy.expected_domains)
        self.assertIn('pubmed.ncbi.nlm.nih.gov', policy.expected_domains)
        self.assertIn('openaire.eu', policy.expected_domains)
        self.assertIn('journals.openedition.org', policy.expected_domains)
        self.assertIn('academic_profile_broad_not_philosophy_only', policy.reason_codes)

    def test_crawl_budgets_are_capped_for_manual_latency_target(self) -> None:
        self.assertEqual(
            web_search_profile_policy.effective_crawl_top_n(web_search_profile.PROFILE_ACTUALITE, 5),
            2,
        )
        self.assertEqual(
            web_search_profile_policy.effective_crawl_max_chars(web_search_profile.PROFILE_ACADEMIQUE, 12000),
            8000,
        )
        self.assertEqual(
            web_search_profile_policy.effective_crawl_top_n(web_search_profile.PROFILE_GENERAL, 1),
            1,
        )

    def test_insufficient_signal_is_not_a_scripted_response(self) -> None:
        evidence = web_search_profile_policy.evaluate_profile_evidence(
            web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
            sources=[],
            policy_fields=web_search_profile_policy.build_profile_policy(
                web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE
            ).as_observability_fields(),
        )

        self.assertTrue(evidence['profile_insufficient_evidence'])
        self.assertIn('no_prompt_material', evidence['profile_insufficient_evidence_reason_codes'])
        self.assertNotIn('response_text', evidence)
        self.assertNotIn('message', evidence)


if __name__ == "__main__":
    unittest.main()
