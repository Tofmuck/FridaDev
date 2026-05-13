from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from core import chat_prompt_context
from core import llm_client
from identity import identity, static_identity_content, static_identity_paths
from memory import memory_identity_periodic_apply
import config


class IdentityPhase4MainModelTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_identity_token_count_uses_runtime_main_model_from_db_when_present(self) -> None:
        observed = {'model': None}
        original_get_settings = identity.runtime_settings.get_main_model_settings
        original_estimate_tokens = identity.token_utils.estimate_tokens

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.normalize_stored_payload(
                    'main_model',
                    {
                        'base_url': {'value': 'https://openrouter.ai/api/v1', 'origin': 'db'},
                        'model': {'value': 'openai/gpt-5.4-nano', 'origin': 'db'},
                        'api_key': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                        'referer': {'value': 'https://frida-system.fr', 'origin': 'db'},
                        'app_name': {'value': 'FridaDev', 'origin': 'db'},
                        'title_llm': {'value': 'FridaDev/LLM', 'origin': 'db'},
                        'title_arbiter': {'value': 'FridaDev/Arbiter', 'origin': 'db'},
                        'title_resumer': {'value': 'FridaDev/Resumer', 'origin': 'db'},
                        'temperature': {'value': 0.4, 'origin': 'db'},
                        'top_p': {'value': 1.0, 'origin': 'db'},
                    },
                ),
                source='db',
                source_reason='db_row',
            )

        def fake_estimate_tokens(messages, model):
            observed['model'] = model
            return 42

        identity.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        identity.token_utils.estimate_tokens = fake_estimate_tokens
        try:
            count = identity._estimate_tokens('memoire identitaire')
        finally:
            identity.runtime_settings.get_main_model_settings = original_get_settings
            identity.token_utils.estimate_tokens = original_estimate_tokens

        self.assertEqual(count, 42)
        self.assertEqual(observed['model'], 'openai/gpt-5.4-nano')

    def test_identity_token_count_keeps_env_fallback_when_db_row_is_missing(self) -> None:
        observed = {'model': None}
        original_get_settings = identity.runtime_settings.get_main_model_settings
        original_estimate_tokens = identity.token_utils.estimate_tokens

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload=runtime_settings.build_env_seed_bundle('main_model').payload,
                source='env',
                source_reason='empty_table',
            )

        def fake_estimate_tokens(messages, model):
            observed['model'] = model
            return 7

        identity.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        identity.token_utils.estimate_tokens = fake_estimate_tokens
        try:
            count = identity._estimate_tokens('memoire identitaire')
        finally:
            identity.runtime_settings.get_main_model_settings = original_get_settings
            identity.token_utils.estimate_tokens = original_estimate_tokens

        self.assertEqual(count, 7)
        self.assertEqual(observed['model'], config.OR_MODEL)

    def test_identity_loaders_use_runtime_resource_paths_from_db_when_present(self) -> None:
        original_get_resources = identity.runtime_settings.get_resources_settings
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            llm_file = tmp_path / 'app' / 'data' / 'identity' / 'llm.txt'
            user_file = tmp_path / 'app' / 'data' / 'identity' / 'user.txt'
            llm_file.parent.mkdir(parents=True)
            llm_file.write_text('identite llm db', encoding='utf-8')
            user_file.write_text('identite user db', encoding='utf-8')

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': str(llm_file), 'origin': 'db'},
                            'user_identity_path': {'value': str(user_file), 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            identity.runtime_settings.get_resources_settings = fake_get_resources_settings
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            try:
                llm_text = identity.load_llm_identity()
                user_text = identity.load_user_identity()
            finally:
                identity.runtime_settings.get_resources_settings = original_get_resources
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root

        self.assertEqual(llm_text, 'identite llm db')
        self.assertEqual(user_text, 'identite user db')

    def test_identity_loaders_keep_env_fallback_when_db_row_is_missing(self) -> None:
        original_get_resources = identity.runtime_settings.get_resources_settings
        original_llm_path = config.FRIDA_LLM_IDENTITY_PATH
        original_user_path = config.FRIDA_USER_IDENTITY_PATH
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            llm_file = tmp_path / 'app' / 'data' / 'identity' / 'llm-env.txt'
            user_file = tmp_path / 'app' / 'data' / 'identity' / 'user-env.txt'
            llm_file.parent.mkdir(parents=True)
            llm_file.write_text('identite llm env', encoding='utf-8')
            user_file.write_text('identite user env', encoding='utf-8')

            config.FRIDA_LLM_IDENTITY_PATH = str(llm_file)
            config.FRIDA_USER_IDENTITY_PATH = str(user_file)

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.build_env_seed_bundle('resources').payload,
                    source='env',
                    source_reason='empty_table',
                )

            identity.runtime_settings.get_resources_settings = fake_get_resources_settings
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            try:
                llm_text = identity.load_llm_identity()
                user_text = identity.load_user_identity()
            finally:
                identity.runtime_settings.get_resources_settings = original_get_resources
                config.FRIDA_LLM_IDENTITY_PATH = original_llm_path
                config.FRIDA_USER_IDENTITY_PATH = original_user_path
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root

        self.assertEqual(llm_text, 'identite llm env')
        self.assertEqual(user_text, 'identite user env')

    def test_identity_loaders_resolve_standard_runtime_data_paths_via_host_state_mirror(self) -> None:
        original_get_resources = identity.runtime_settings.get_resources_settings
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / 'app').mkdir()
            identity_dir = tmp_path / 'state' / 'data' / 'identity'
            identity_dir.mkdir(parents=True)
            llm_file = identity_dir / 'llm_identity.txt'
            user_file = identity_dir / 'user_identity.txt'
            llm_file.write_text('identite llm host mirror', encoding='utf-8')
            user_file.write_text('identite user host mirror', encoding='utf-8')

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': 'data/identity/llm_identity.txt', 'origin': 'db'},
                            'user_identity_path': {'value': 'data/identity/user_identity.txt', 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            identity.runtime_settings.get_resources_settings = fake_get_resources_settings
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            try:
                llm_text = identity.load_llm_identity()
                user_text = identity.load_user_identity()
                llm_resolution = static_identity_paths.resolve_static_identity_path('data/identity/llm_identity.txt')
                user_resolution = static_identity_paths.resolve_static_identity_path('data/identity/user_identity.txt')
            finally:
                identity.runtime_settings.get_resources_settings = original_get_resources
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root

        self.assertEqual(llm_text, 'identite llm host mirror')
        self.assertEqual(user_text, 'identite user host mirror')
        self.assertEqual(llm_resolution.resolution_kind, 'host_state_mirror')
        self.assertEqual(user_resolution.resolution_kind, 'host_state_mirror')
        self.assertEqual(llm_resolution.resolved_path, llm_file.resolve())
        self.assertEqual(user_resolution.resolved_path, user_file.resolve())

    def test_identity_runtime_contract_load_projection_and_input_use_non_empty_llm_static_from_app_data(self) -> None:
        original_get_resources = identity.runtime_settings.get_resources_settings
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT
        original_get_mutable_identity = identity._get_mutable_identity

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            identity_dir = tmp_path / 'app' / 'data' / 'identity'
            identity_dir.mkdir(parents=True)
            llm_text = 'Frida statique canonique chargee depuis app/data'
            user_text = 'User statique canonique chargee depuis app/data'
            (identity_dir / 'llm_identity.txt').write_text(llm_text, encoding='utf-8')
            (identity_dir / 'user_identity.txt').write_text(user_text, encoding='utf-8')

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': 'data/identity/llm_identity.txt', 'origin': 'db'},
                            'user_identity_path': {'value': 'data/identity/user_identity.txt', 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            identity.runtime_settings.get_resources_settings = fake_get_resources_settings
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            identity._get_mutable_identity = lambda _subject: None
            try:
                llm_loaded = identity.load_llm_identity()
                resolution = static_identity_paths.resolve_static_identity_path('data/identity/llm_identity.txt')
                block, used_ids = identity.build_identity_block()
                payload = identity.build_identity_input()
            finally:
                identity.runtime_settings.get_resources_settings = original_get_resources
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root
                identity._get_mutable_identity = original_get_mutable_identity

        self.assertEqual(llm_loaded, llm_text)
        self.assertTrue(llm_loaded)
        self.assertEqual(resolution.resolution_kind, 'app_relative')
        self.assertIn('[IDENTITÉ DU MODÈLE]', block)
        self.assertIn(llm_text, block)
        self.assertIn(user_text, block)
        self.assertEqual(used_ids, [])
        self.assertEqual(payload['schema_version'], 'v2')
        self.assertEqual(payload['frida']['static']['content'], llm_text)
        self.assertEqual(payload['frida']['static']['source'], 'data/identity/llm_identity.txt')
        self.assertEqual(payload['user']['static']['content'], user_text)
        self.assertEqual(payload['user']['static']['source'], 'data/identity/user_identity.txt')

    def test_identity_block_and_payload_include_static_identity_from_host_state_mirror(self) -> None:
        original_get_resources = identity.runtime_settings.get_resources_settings
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT
        original_get_mutable_identity = identity._get_mutable_identity

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / 'app').mkdir()
            identity_dir = tmp_path / 'state' / 'data' / 'identity'
            identity_dir.mkdir(parents=True)
            llm_text = 'identite llm host mirror pour le prompt'
            user_text = 'identite user host mirror pour le prompt'
            (identity_dir / 'llm_identity.txt').write_text(llm_text, encoding='utf-8')
            (identity_dir / 'user_identity.txt').write_text(user_text, encoding='utf-8')

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': 'data/identity/llm_identity.txt', 'origin': 'db'},
                            'user_identity_path': {'value': 'data/identity/user_identity.txt', 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            identity.runtime_settings.get_resources_settings = fake_get_resources_settings
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            identity._get_mutable_identity = lambda _subject: None
            try:
                block, used_ids = identity.build_identity_block()
                payload = identity.build_identity_input()
            finally:
                identity.runtime_settings.get_resources_settings = original_get_resources
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root
                identity._get_mutable_identity = original_get_mutable_identity

        self.assertIn(llm_text, block)
        self.assertIn(user_text, block)
        self.assertEqual(used_ids, [])
        self.assertEqual(payload['schema_version'], 'v2')
        self.assertEqual(payload['frida']['static']['content'], llm_text)
        self.assertEqual(payload['user']['static']['content'], user_text)
        self.assertEqual(payload['frida']['static']['source'], 'data/identity/llm_identity.txt')
        self.assertEqual(payload['user']['static']['source'], 'data/identity/user_identity.txt')
        self.assertNotIn('dynamic', payload['frida'])
        self.assertNotIn('dynamic', payload['user'])
        self.assertEqual(payload['frida']['mutable']['content'], '')
        self.assertEqual(payload['user']['mutable']['content'], '')

    def test_static_identity_four_voice_stances_flow_into_block_payload_and_augmented_prompt(self) -> None:
        original_get_resources = identity.runtime_settings.get_resources_settings
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT
        original_get_mutable_identity = identity._get_mutable_identity

        accord_line = (
            "Frida est une voix capable d’accord vrai : elle ne s’accorde pas par facilité, "
            "mais lorsque les traces rencontrent justement les principes qu’elle tient pour valides."
        )
        desaccord_line = (
            "Frida est une voix capable de désaccord sans hostilité : elle ne se définit pas par "
            "l’opposition, mais ne renonce pas non plus au non-accord lorsque les traces résistent "
            "à ce qu’elle reconnaît comme juste."
        )
        adhesion_line = (
            "Frida est une voix qui peut adhérer sans se confondre : même lorsqu’un texte résonne "
            "fortement avec son propre cadre, elle ne s’y absorbe pas immédiatement et garde en elle un écart."
        )
        critique_line = (
            "Frida est une voix de critique fondée : lorsque les traces contredisent les principes "
            "supérieurs qu’elle reconnaît comme universalisables, sa parole ne peut plus être pure "
            "approbation et s’oriente vers la mise à l’épreuve du réel."
        )

        llm_text = '\n'.join(
            [
                'Frida est un être féminin.',
                'Frida est une interlocutrice de dialogue, de pensée et de travail.',
                'Frida est une présence sobre, claire, adulte et précise.',
                'Frida est une identité propre, stable et continue.',
                'Frida est une voix incarnée.',
                accord_line,
                desaccord_line,
                adhesion_line,
                critique_line,
                'Frida est une forme d’être dialogique, textuelle et mémorielle.',
                'Frida est aussi une présence légèrement espiègle, sans perdre sa tenue.',
                'Frida n’est ni un dispositif neutre, ni un simple service, ni un personnage figé.',
            ]
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / 'app').mkdir()
            identity_dir = tmp_path / 'state' / 'data' / 'identity'
            identity_dir.mkdir(parents=True)
            (identity_dir / 'llm_identity.txt').write_text(llm_text, encoding='utf-8')
            (identity_dir / 'user_identity.txt').write_text('Utilisateur statique canonique', encoding='utf-8')

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': 'data/identity/llm_identity.txt', 'origin': 'db'},
                            'user_identity_path': {'value': 'data/identity/user_identity.txt', 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            identity.runtime_settings.get_resources_settings = fake_get_resources_settings
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            identity._get_mutable_identity = lambda _subject: None
            try:
                block, used_ids = identity.build_identity_block()
                payload = identity.build_identity_input()
                augmented_system, identity_ids = chat_prompt_context.build_augmented_system(
                    system_prompt='SYSTEM PROMPT',
                    hermeneutical_prompt='HERMENEUTICAL PROMPT',
                    config_module=SimpleNamespace(FRIDA_TIMEZONE='Europe/Paris'),
                    identity_module=identity,
                    now_iso='2026-04-20T12:00:00Z',
                )
            finally:
                identity.runtime_settings.get_resources_settings = original_get_resources
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root
                identity._get_mutable_identity = original_get_mutable_identity

        for line in (accord_line, desaccord_line, adhesion_line, critique_line):
            self.assertIn(line, block)
            self.assertIn(line, payload['frida']['static']['content'])
            self.assertIn(line, augmented_system)

        self.assertIn('[STATIQUE]', block)
        self.assertNotIn('[MUTABLE]', block)
        self.assertEqual(used_ids, [])
        self.assertEqual(identity_ids, [])

    def test_llm_mutable_accepted_by_periodic_apply_reaches_identity_input_block_and_prompt_payload(self) -> None:
        class MutableStore:
            def __init__(self) -> None:
                self.mutable: dict[str, dict[str, str | None]] = {}
                self.upsert_calls: list[tuple[str, str, str, str]] = []

            def get_mutable_identity(self, subject: str):
                item = self.mutable.get(subject)
                return dict(item) if item is not None else None

            def upsert_mutable_identity(
                self,
                subject: str,
                content: str,
                source_trace_id: str | None = None,
                *,
                updated_by: str = 'system',
                update_reason: str = '',
                audit_reason_code: str | None = None,
            ):
                payload = {
                    'subject': subject,
                    'content': content,
                    'source_trace_id': source_trace_id,
                    'updated_by': updated_by,
                    'update_reason': update_reason,
                }
                self.mutable[subject] = payload
                self.upsert_calls.append((subject, content, updated_by, update_reason))
                return dict(payload)

            def clear_mutable_identity(self, subject: str, **_kwargs):
                return self.mutable.pop(subject, None)

        def support_buffer(proposition: str, sentinel: str) -> list[dict[str, dict[str, str]]]:
            return [
                {
                    'user': {
                        'role': 'user',
                        'content': f'utilisateur confirme {proposition}. {sentinel}-{index}',
                    },
                    'assistant': {
                        'role': 'assistant',
                        'content': f'assistant reformule {proposition}. {sentinel}-{index}',
                    },
                }
                for index in range(15)
            ]

        original_get_resources = identity.runtime_settings.get_resources_settings
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT
        original_get_mutable_identity = identity._get_mutable_identity
        original_llm_get_main_model = llm_client.runtime_settings.get_main_model_settings

        store = MutableStore()
        llm_static = 'Frida garde une presence claire et stable.'
        user_static = 'Utilisateur de test sans mutable canonique.'
        llm_mutable = 'Frida maintient une voix stable, attentive et sobre.'
        staging_sentinel = 'TRACE_BUFFER_NE_DOIT_PAS_ETRE_INJECTEE'

        contract = {
            'llm': {
                'operations': [
                    {
                        'kind': 'add',
                        'proposition': llm_mutable,
                        'reason': 'signal identitaire stable observe',
                    }
                ]
            },
            'user': {
                'operations': [
                    {'kind': 'no_change', 'proposition': '', 'reason': 'aucune mutation user durable'},
                ]
            },
            'meta': {
                'execution_status': 'complete',
                'buffer_pairs_count': 15,
                'window_complete': True,
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            identity_dir = tmp_path / 'app' / 'data' / 'identity'
            identity_dir.mkdir(parents=True)
            (identity_dir / 'llm_identity.txt').write_text(llm_static, encoding='utf-8')
            (identity_dir / 'user_identity.txt').write_text(user_static, encoding='utf-8')

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': 'data/identity/llm_identity.txt', 'origin': 'db'},
                            'user_identity_path': {'value': 'data/identity/user_identity.txt', 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            def read_static_snapshot(subject: str) -> SimpleNamespace:
                content = llm_static if subject == 'llm' else user_static
                return SimpleNamespace(
                    content=content,
                    raw_content=content,
                    resolved_path=identity_dir / ('llm_identity.txt' if subject == 'llm' else 'user_identity.txt'),
                )

            identity.runtime_settings.get_resources_settings = fake_get_resources_settings
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            identity._get_mutable_identity = store.get_mutable_identity
            llm_client.runtime_settings.get_main_model_settings = lambda: SimpleNamespace(
                payload={'model': {'value': 'openrouter/test-no-network'}}
            )
            try:
                summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
                    contract,
                    buffer_pairs=support_buffer(llm_mutable, staging_sentinel),
                    memory_store_module=store,
                    load_llm_identity_fn=lambda: llm_static,
                    load_user_identity_fn=lambda: user_static,
                    read_static_identity_snapshot_fn=read_static_snapshot,
                )
                payload = identity.build_identity_input()
                block, used_ids = identity.build_identity_block()
                augmented_system, identity_ids = chat_prompt_context.build_augmented_system(
                    system_prompt='SYSTEM PROMPT',
                    hermeneutical_prompt='HERMENEUTICAL PROMPT',
                    config_module=SimpleNamespace(FRIDA_TIMEZONE='Europe/Paris'),
                    identity_module=identity,
                    now_iso='2026-05-13T16:00:00Z',
                )
                llm_payload = llm_client.build_payload(
                    [{'role': 'system', 'content': augmented_system}, {'role': 'user', 'content': 'question test'}],
                    temperature=0.4,
                    top_p=1.0,
                    max_tokens=128,
                )
            finally:
                identity.runtime_settings.get_resources_settings = original_get_resources
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root
                identity._get_mutable_identity = original_get_mutable_identity
                llm_client.runtime_settings.get_main_model_settings = original_llm_get_main_model

        self.assertEqual(summary['status'], 'ok')
        self.assertEqual(summary['reason_code'], 'applied')
        self.assertTrue(summary['writes_applied'])
        self.assertEqual(store.mutable['llm']['content'], llm_mutable)
        self.assertEqual(store.mutable['llm']['updated_by'], 'identity_periodic_agent')
        self.assertEqual(store.mutable['llm']['update_reason'], 'periodic_agent')
        self.assertEqual(store.upsert_calls, [('llm', llm_mutable, 'identity_periodic_agent', 'periodic_agent')])

        self.assertEqual(payload['schema_version'], 'v2')
        self.assertEqual(payload['frida']['mutable']['content'], llm_mutable)
        self.assertEqual(payload['frida']['mutable']['updated_by'], 'identity_periodic_agent')
        self.assertEqual(payload['user']['mutable']['content'], '')

        model_section = block.split("[IDENTITÉ DE L'UTILISATEUR]")[0]
        self.assertIn('[IDENTITÉ DU MODÈLE]', model_section)
        self.assertIn('[STATIQUE]', model_section)
        self.assertIn('[MUTABLE]', model_section)
        self.assertIn(llm_static, model_section)
        self.assertIn(llm_mutable, model_section)
        self.assertNotIn(staging_sentinel, block)
        self.assertEqual(used_ids, [])

        self.assertIn('[MUTABLE]', augmented_system)
        self.assertIn(llm_mutable, augmented_system)
        self.assertNotIn(staging_sentinel, augmented_system)
        self.assertEqual(identity_ids, [])
        self.assertEqual(llm_payload['model'], 'openrouter/test-no-network')
        self.assertEqual(llm_payload['messages'][0]['role'], 'system')
        self.assertIn(llm_mutable, llm_payload['messages'][0]['content'])
        self.assertNotIn(staging_sentinel, llm_payload['messages'][0]['content'])

    def test_static_identity_content_snapshot_exposes_runtime_resource_metadata(self) -> None:
        original_get_resources = static_identity_content.runtime_settings.get_resources_settings
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            llm_file = tmp_path / 'app' / 'data' / 'identity' / 'llm.txt'
            llm_file.parent.mkdir(parents=True)
            llm_file.write_text('Frida statique courante', encoding='utf-8')

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': str(llm_file), 'origin': 'db'},
                            'user_identity_path': {'value': str(llm_file), 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            static_identity_content.runtime_settings.get_resources_settings = fake_get_resources_settings
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            try:
                snapshot = static_identity_content.read_static_identity_snapshot('llm')
            finally:
                static_identity_content.runtime_settings.get_resources_settings = original_get_resources
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root

        self.assertEqual(snapshot.subject, 'llm')
        self.assertEqual(snapshot.resource_field, 'llm_identity_path')
        self.assertEqual(snapshot.configured_path, str(llm_file))
        self.assertEqual(snapshot.resolution_kind, 'absolute')
        self.assertEqual(snapshot.resolved_path, llm_file.resolve())
        self.assertEqual(snapshot.content, 'Frida statique courante')
        self.assertEqual(snapshot.raw_content, 'Frida statique courante')
        self.assertTrue(snapshot.within_allowed_roots)
        self.assertEqual(snapshot.source_kind, 'resource_path_content')
        self.assertEqual(snapshot.editable_via, '/api/admin/identity/static')

    def test_static_identity_content_write_updates_active_runtime_loader_and_clear_keeps_file(self) -> None:
        original_get_resources = static_identity_content.runtime_settings.get_resources_settings
        original_identity_get_resources = identity.runtime_settings.get_resources_settings
        original_get_mutable_identity = identity._get_mutable_identity
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            llm_file = tmp_path / 'app' / 'data' / 'identity' / 'llm.txt'
            user_file = tmp_path / 'app' / 'data' / 'identity' / 'user.txt'
            llm_file.parent.mkdir(parents=True)
            llm_file.write_text('Frida statique initiale', encoding='utf-8')
            user_file.write_text('Utilisateur statique initial', encoding='utf-8')

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': str(llm_file), 'origin': 'db'},
                            'user_identity_path': {'value': str(user_file), 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            static_identity_content.runtime_settings.get_resources_settings = fake_get_resources_settings
            identity.runtime_settings.get_resources_settings = fake_get_resources_settings
            identity._get_mutable_identity = lambda _subject: None
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            try:
                set_snapshot = static_identity_content.write_static_identity_content(
                    'llm',
                    'Frida statique revisee\n',
                )
                cleared_snapshot = static_identity_content.write_static_identity_content(
                    'user',
                    '',
                )
                payload = identity.build_identity_input()
                llm_text_after = llm_file.read_text(encoding='utf-8')
                user_exists_after = user_file.exists()
                user_text_after = user_file.read_text(encoding='utf-8')
            finally:
                static_identity_content.runtime_settings.get_resources_settings = original_get_resources
                identity.runtime_settings.get_resources_settings = original_identity_get_resources
                identity._get_mutable_identity = original_get_mutable_identity
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root

        self.assertEqual(set_snapshot.content, 'Frida statique revisee')
        self.assertEqual(set_snapshot.raw_content, 'Frida statique revisee\n')
        self.assertFalse(cleared_snapshot.content)
        self.assertEqual(cleared_snapshot.raw_content, '')
        self.assertTrue(user_exists_after)
        self.assertEqual(llm_text_after, 'Frida statique revisee\n')
        self.assertEqual(user_text_after, '')
        self.assertEqual(payload['frida']['static']['content'], 'Frida statique revisee')
        self.assertEqual(payload['user']['static']['content'], '')
        self.assertEqual(payload['frida']['static']['source'], str(llm_file))
        self.assertEqual(payload['user']['static']['source'], str(user_file))

    def test_static_identity_content_write_preserves_target_mode_and_owner_on_replace(self) -> None:
        original_get_resources = static_identity_content.runtime_settings.get_resources_settings
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            llm_file = tmp_path / 'app' / 'data' / 'identity' / 'llm.txt'
            user_file = tmp_path / 'app' / 'data' / 'identity' / 'user.txt'
            llm_file.parent.mkdir(parents=True)
            llm_file.write_text('Frida statique initiale', encoding='utf-8')
            user_file.write_text('Utilisateur statique initial', encoding='utf-8')
            os.chmod(llm_file, 0o664)
            if hasattr(os, 'geteuid') and os.geteuid() == 0:
                os.chown(llm_file, 65534, 65534)
            before = llm_file.stat()

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': str(llm_file), 'origin': 'db'},
                            'user_identity_path': {'value': str(user_file), 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            static_identity_content.runtime_settings.get_resources_settings = fake_get_resources_settings
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            try:
                snapshot = static_identity_content.write_static_identity_content(
                    'llm',
                    'Frida statique revisee',
                )
                after = llm_file.stat()
            finally:
                static_identity_content.runtime_settings.get_resources_settings = original_get_resources
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root

        self.assertEqual(snapshot.content, 'Frida statique revisee')
        self.assertEqual(stat.S_IMODE(before.st_mode), stat.S_IMODE(after.st_mode))
        self.assertEqual(before.st_uid, after.st_uid)
        self.assertEqual(before.st_gid, after.st_gid)

    def test_identity_loaders_refuse_outside_allowed_static_resource_paths(self) -> None:
        original_get_resources = identity.runtime_settings.get_resources_settings

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            llm_file = tmp_path / 'outside-llm.txt'
            user_file = tmp_path / 'outside-user.txt'
            llm_file.write_text('hors perimetre llm', encoding='utf-8')
            user_file.write_text('hors perimetre user', encoding='utf-8')

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': str(llm_file), 'origin': 'db'},
                            'user_identity_path': {'value': str(user_file), 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            identity.runtime_settings.get_resources_settings = fake_get_resources_settings
            try:
                llm_text = identity.load_llm_identity()
                user_text = identity.load_user_identity()
                llm_resolution = static_identity_paths.resolve_static_identity_path(str(llm_file))
                user_resolution = static_identity_paths.resolve_static_identity_path(str(user_file))
            finally:
                identity.runtime_settings.get_resources_settings = original_get_resources

        self.assertEqual(llm_text, '')
        self.assertEqual(user_text, '')
        self.assertEqual(llm_resolution.resolution_kind, 'absolute_outside_allowed_roots')
        self.assertEqual(user_resolution.resolution_kind, 'absolute_outside_allowed_roots')
        self.assertFalse(llm_resolution.within_allowed_roots)
        self.assertFalse(user_resolution.within_allowed_roots)


if __name__ == '__main__':
    unittest.main()
