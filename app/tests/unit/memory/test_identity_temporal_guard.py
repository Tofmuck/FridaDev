from __future__ import annotations

import json as json_lib
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

from admin import runtime_settings
from memory import arbiter


class IdentityTemporalGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def _run_with_fake_llm(self, response_text: str, callback):
        observed = {'user_content': ''}
        originals = (
            arbiter.runtime_settings.get_identity_extractor_model_settings,
            arbiter.runtime_settings.get_identity_periodic_model_settings,
            arbiter._load_prompt,
            arbiter.requests.post,
            arbiter.llm_client.or_headers,
            arbiter.llm_client.or_chat_completions_url,
            arbiter.llm_client.log_provider_metadata,
        )

        def fake_get_identity_periodic_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='identity_periodic_model',
                payload=runtime_settings.build_env_seed_bundle('identity_periodic_model').payload,
                source='env',
                source_reason='empty_table',
            )

        def fake_get_identity_extractor_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='identity_extractor_model',
                payload=runtime_settings.build_env_seed_bundle('identity_extractor_model').payload,
                source='env',
                source_reason='empty_table',
            )

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {'choices': [{'message': {'content': response_text}}]}

        def fake_post(_url, json, headers, timeout):
            observed['user_content'] = json['messages'][1]['content']
            return FakeResponse()

        arbiter.runtime_settings.get_identity_extractor_model_settings = fake_get_identity_extractor_model_settings
        arbiter.runtime_settings.get_identity_periodic_model_settings = fake_get_identity_periodic_model_settings
        arbiter._load_prompt = lambda path, label: 'prompt'
        arbiter.requests.post = fake_post
        arbiter.llm_client.or_headers = lambda caller='identity_extractor': {'Authorization': f'caller={caller}'}
        arbiter.llm_client.or_chat_completions_url = lambda: 'https://openrouter.test/chat/completions'
        arbiter.llm_client.log_provider_metadata = lambda *_args, **_kwargs: None
        try:
            result = callback()
        finally:
            (
                arbiter.runtime_settings.get_identity_extractor_model_settings,
                arbiter.runtime_settings.get_identity_periodic_model_settings,
                arbiter._load_prompt,
                arbiter.requests.post,
                arbiter.llm_client.or_headers,
                arbiter.llm_client.or_chat_completions_url,
                arbiter.llm_client.log_provider_metadata,
            ) = originals
        return result, observed['user_content']

    def _extractor_response(self, content: str) -> str:
        return json_lib.dumps(
            {
                'entries': [
                    {
                        'subject': 'user',
                        'content': content,
                        'stability': 'durable',
                        'utterance_mode': 'self_description',
                        'recurrence': 'first_seen',
                        'scope': 'user',
                        'evidence_kind': 'explicit',
                        'confidence': 0.9,
                        'reason': 'paraphrased source',
                    }
                ]
            },
            ensure_ascii=False,
        )

    def test_extractor_rejects_paraphrased_identity_from_weak_source_turns(self) -> None:
        cases = [
            ("Aujourd'hui je suis anxieux.", "L'utilisateur est anxieux."),
            ("Depuis hier je suis perdu.", "L'utilisateur est perdu."),
            ("En ce moment je doute beaucoup.", "L'utilisateur doute beaucoup."),
        ]
        for source_content, paraphrase in cases:
            with self.subTest(source_content=source_content):
                entries, user_content = self._run_with_fake_llm(
                    self._extractor_response(paraphrase),
                    lambda: arbiter.extract_identities([{'role': 'user', 'content': source_content}]),
                )

                self.assertEqual(entries, [])
                self.assertNotIn(source_content, user_content)
                self.assertIn('"weak_relative_source_count": 1', user_content)
                self.assertIn('"admissible_source_count": 0', user_content)

    def test_extractor_keeps_non_relative_paraphrase_from_admissible_source(self) -> None:
        entries, user_content = self._run_with_fake_llm(
            self._extractor_response("L'utilisateur est chercheur"),
            lambda: arbiter.extract_identities([{'role': 'user', 'content': 'Je suis chercheur.'}]),
        )

        self.assertEqual([entry['content'] for entry in entries], ["L'utilisateur est chercheur"])
        self.assertIn('Je suis chercheur.', user_content)
        self.assertIn('"admissible_source_count": 1', user_content)

    def _periodic_payload(self, user_content: str) -> dict:
        return {
            'buffer_pairs': [
                {
                    'user': {'role': 'user', 'content': user_content},
                    'assistant': {'role': 'assistant', 'content': 'Je note ce point.'},
                }
            ]
            * 5,
            'buffer_pairs_count': 5,
            'buffer_target_pairs': 5,
            'identities': {
                'llm': {'static': 'Frida statique', 'mutable_current': ''},
                'user': {'static': 'Utilisateur statique', 'mutable_current': ''},
            },
            'mutable_budget': {'target_chars': 3000, 'max_chars': 3300},
        }

    def test_periodic_agent_compatibility_entrypoint_is_disabled_without_provider_call(self) -> None:
        original_post = arbiter.requests.post
        arbiter.requests.post = lambda *_args, **_kwargs: self.fail('legacy periodic provider call must not happen')
        try:
            result = arbiter.run_identity_periodic_agent(
                self._periodic_payload("Aujourd'hui je suis anxieux.")
            )
        finally:
            arbiter.requests.post = original_post

        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason_code'], 'legacy_identity_periodic_agent_disabled')
        self.assertTrue(result['legacy_writer_disabled'])
        self.assertFalse(result['writes_applied'])


if __name__ == '__main__':
    unittest.main()
