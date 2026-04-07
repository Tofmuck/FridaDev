from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
import config
from identity import static_identity_paths
import minimal_validation


class MinimalValidationPhase4ResourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_check_prompt_files_uses_runtime_resource_paths_from_db_when_present(self) -> None:
        original_get_resources = minimal_validation.runtime_settings.get_resources_settings
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            llm_file = tmp_path / 'app' / 'data' / 'identity' / 'llm.txt'
            user_file = tmp_path / 'app' / 'data' / 'identity' / 'user.txt'
            llm_file.parent.mkdir(parents=True)
            llm_file.write_text('identite llm db minimale suffisamment longue', encoding='utf-8')
            user_file.write_text('identite user db minimale suffisamment longue', encoding='utf-8')

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

            minimal_validation.runtime_settings.get_resources_settings = fake_get_resources_settings
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            try:
                details = minimal_validation._check_prompt_files()
            finally:
                minimal_validation.runtime_settings.get_resources_settings = original_get_resources
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root

        self.assertEqual(details['llm_identity']['path'], str(llm_file))
        self.assertEqual(details['user_identity']['path'], str(user_file))
        self.assertEqual(
            details['main_system_prompt']['path'],
            str(APP_DIR / config.MAIN_SYSTEM_PROMPT_PATH),
        )
        self.assertEqual(
            details['main_hermeneutical_prompt']['path'],
            str(APP_DIR / config.MAIN_HERMENEUTICAL_PROMPT_PATH),
        )
        self.assertEqual(
            details['summary_system_prompt']['path'],
            str(APP_DIR / config.SUMMARY_SYSTEM_PROMPT_PATH),
        )
        self.assertEqual(
            details['web_reformulation_prompt']['path'],
            str(APP_DIR / config.WEB_REFORMULATION_PROMPT_PATH),
        )
        self.assertEqual(
            details['identity_mutable_rewriter_prompt']['path'],
            str(APP_DIR / config.IDENTITY_MUTABLE_REWRITER_PROMPT_PATH),
        )
        self.assertIn('const SYSTEM_PROMPT =', details['forbidden_inline_markers']['app_js'])
        self.assertIn('cfg.system', details['forbidden_inline_markers']['app_js'])
        self.assertIn('id="system"', details['forbidden_inline_markers']['index_html'])
        self.assertIn(
            'Tu es un assistant de synthèse. Résume le dialogue suivant en conservant',
            details['forbidden_inline_markers']['summarizer_py'],
        )
        self.assertIn(
            'Tu es un assistant qui transforme un message en requête de recherche web courte et efficace.',
            details['forbidden_inline_markers']['web_search_py'],
        )

    def test_check_prompt_files_keeps_env_fallback_when_db_row_is_missing(self) -> None:
        original_get_resources = minimal_validation.runtime_settings.get_resources_settings
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
            llm_file.write_text('identite llm env minimale suffisamment longue', encoding='utf-8')
            user_file.write_text('identite user env minimale suffisamment longue', encoding='utf-8')

            config.FRIDA_LLM_IDENTITY_PATH = str(llm_file)
            config.FRIDA_USER_IDENTITY_PATH = str(user_file)

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.build_env_seed_bundle('resources').payload,
                    source='env',
                    source_reason='empty_table',
                )

            minimal_validation.runtime_settings.get_resources_settings = fake_get_resources_settings
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            try:
                details = minimal_validation._check_prompt_files()
            finally:
                minimal_validation.runtime_settings.get_resources_settings = original_get_resources
                config.FRIDA_LLM_IDENTITY_PATH = original_llm_path
                config.FRIDA_USER_IDENTITY_PATH = original_user_path
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root

        self.assertEqual(details['llm_identity']['path'], str(llm_file))
        self.assertEqual(details['user_identity']['path'], str(user_file))
        self.assertEqual(
            details['main_system_prompt']['path'],
            str(APP_DIR / config.MAIN_SYSTEM_PROMPT_PATH),
        )
        self.assertEqual(
            details['main_hermeneutical_prompt']['path'],
            str(APP_DIR / config.MAIN_HERMENEUTICAL_PROMPT_PATH),
        )
        self.assertEqual(
            details['summary_system_prompt']['path'],
            str(APP_DIR / config.SUMMARY_SYSTEM_PROMPT_PATH),
        )
        self.assertEqual(
            details['web_reformulation_prompt']['path'],
            str(APP_DIR / config.WEB_REFORMULATION_PROMPT_PATH),
        )
        self.assertEqual(
            details['identity_mutable_rewriter_prompt']['path'],
            str(APP_DIR / config.IDENTITY_MUTABLE_REWRITER_PROMPT_PATH),
        )

    def test_check_prompt_files_rejects_identity_resource_outside_allowed_roots(self) -> None:
        original_get_resources = minimal_validation.runtime_settings.get_resources_settings

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            llm_file = tmp_path / 'outside-llm.txt'
            user_file = tmp_path / 'outside-user.txt'
            llm_file.write_text('identite llm hors perimetre minimale', encoding='utf-8')
            user_file.write_text('identite user hors perimetre minimale', encoding='utf-8')

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

            minimal_validation.runtime_settings.get_resources_settings = fake_get_resources_settings
            try:
                with self.assertRaises(RuntimeError) as ctx:
                    minimal_validation._check_prompt_files()
            finally:
                minimal_validation.runtime_settings.get_resources_settings = original_get_resources

        self.assertIn('within_allowed_roots=False', str(ctx.exception))

    def test_check_prompt_files_resolves_standard_runtime_data_paths_via_host_state_mirror(self) -> None:
        original_get_resources = minimal_validation.runtime_settings.get_resources_settings
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
            llm_file.write_text('identite llm host mirror minimale suffisamment longue', encoding='utf-8')
            user_file.write_text('identite user host mirror minimale suffisamment longue', encoding='utf-8')

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

            minimal_validation.runtime_settings.get_resources_settings = fake_get_resources_settings
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            try:
                details = minimal_validation._check_prompt_files()
            finally:
                minimal_validation.runtime_settings.get_resources_settings = original_get_resources
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root

        self.assertEqual(details['llm_identity']['configured_path'], 'data/identity/llm_identity.txt')
        self.assertEqual(details['user_identity']['configured_path'], 'data/identity/user_identity.txt')
        self.assertEqual(details['llm_identity']['path'], str(llm_file.resolve()))
        self.assertEqual(details['user_identity']['path'], str(user_file.resolve()))
        self.assertEqual(details['llm_identity']['resolved_path'], str(llm_file.resolve()))
        self.assertEqual(details['user_identity']['resolved_path'], str(user_file.resolve()))
        self.assertEqual(details['llm_identity']['resolution'], 'host_state_mirror')
        self.assertEqual(details['user_identity']['resolution'], 'host_state_mirror')
        self.assertEqual(
            details['identity_mutable_rewriter_prompt']['path'],
            str(APP_DIR / config.IDENTITY_MUTABLE_REWRITER_PROMPT_PATH),
        )


class MinimalValidationPhase4DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def test_identity_archive_and_hermeneutic_suspension_todo_are_aligned(self) -> None:
        governance_spec = (
            APP_DIR / 'docs' / 'states' / 'specs' / 'identity-governance-contract.md'
        ).read_text(encoding='utf-8')
        read_model_spec = (
            APP_DIR / 'docs' / 'states' / 'specs' / 'identity-read-model-contract.md'
        ).read_text(encoding='utf-8')
        surface_spec = (
            APP_DIR / 'docs' / 'states' / 'specs' / 'identity-surface-contract.md'
        ).read_text(encoding='utf-8')
        dual_feed_spec = (
            APP_DIR / 'docs' / 'states' / 'specs' / 'hermeneutic-node-dual-feed-contract.md'
        ).read_text(encoding='utf-8')
        operations_doc = (
            APP_DIR / 'docs' / 'states' / 'operations' / 'frida-installation-operations.md'
        ).read_text(encoding='utf-8')
        archived_identity_todo = (
            APP_DIR / 'docs' / 'todo-done' / 'refactors' / 'identity-control-surface-todo.md'
        ).read_text(encoding='utf-8')
        suspension_todo = (
            APP_DIR / 'docs' / 'todo-todo' / 'memory' / 'hermeneutic-suspension-auto-web-todo.md'
        ).read_text(encoding='utf-8')

        self.assertIn('Lot ferme: `Lot 5`', governance_spec)
        self.assertIn('GET /api/admin/identity/governance', governance_spec)
        self.assertIn('POST /api/admin/identity/governance', governance_spec)
        self.assertIn('identity-governance-contract.md', read_model_spec)
        self.assertIn('Lot ferme: `Lot 6`', surface_spec)
        self.assertIn('GET /identity', surface_spec)
        self.assertIn('GET /api/admin/identity/runtime-representations', surface_spec)
        self.assertIn('identity-surface-contract.md', read_model_spec)
        self.assertIn('activation_mode = manual|auto|not_requested', dual_feed_spec)
        self.assertIn("l'injection web dans le prompt principal depend du runtime web reel", dual_feed_spec)
        self.assertIn('web search manuelle et auto-bornee degradees', operations_doc)
        self.assertIn("`web_search=false` ne bloque plus absolument le web", operations_doc)
        self.assertIn('une demande explicite de source, de lien ou de reference', operations_doc)
        self.assertIn('les demandes pures de verification restent traitees a part', operations_doc)
        self.assertIn('- [x] Lot 4 - Ouvrir une edition controlee du statique', archived_identity_todo)
        self.assertIn('- [x] Lot 5 - Rendre les caps, seuils et budgets lisibles et gouvernables', archived_identity_todo)
        self.assertIn('- [x] Lot 6 - Assembler la surface `Identity` et sa navigation globale', archived_identity_todo)
        self.assertIn('Statut: ferme', archived_identity_todo)
        self.assertIn('Classement: `app/docs/todo-done/refactors/`', archived_identity_todo)
        self.assertIn('Statut: ouvert', suspension_todo)
        self.assertIn('Classement: `app/docs/todo-todo/memory/`', suspension_todo)
        self.assertIn('verification_externe_requise', suspension_todo)
        self.assertIn('suspension', suspension_todo.lower())
        self.assertIn('## Diagnostic confirme sur le cas observe', suspension_todo)
        self.assertIn('## Etat apres premier patch runtime', suspension_todo)
        self.assertIn('## Etat apres deuxieme pas runtime', suspension_todo)
        self.assertIn('## Etat apres troisieme pas runtime', suspension_todo)
        self.assertIn('## Contradiction apparente: verdict', suspension_todo)
        self.assertIn('## Ce qui reste hypothese a ce stade', suspension_todo)
        self.assertIn('## Preuves attendues avant implementation', suspension_todo)
        self.assertIn('`decision_source = primary`', suspension_todo)
        self.assertIn('`provenances`', suspension_todo)
        self.assertIn('`activation_mode = manual|auto|not_requested`', suspension_todo)
        self.assertIn('`preuve`', suspension_todo)
        self.assertIn('`lien`', suspension_todo)
        self.assertIn('Les demandes explicites de verification, de source, de reference et de lien restent classables', suspension_todo)
        self.assertIn('La cause de bascule vers une verification externe devient plus lisible', suspension_todo)
        self.assertIn('Preuve d\'observabilite: les traces exposent maintenant `provenances`', suspension_todo)
        self.assertIn('`web_search=false` ne vaut plus interdiction absolue', suspension_todo)
        self.assertIn('La branche trop large `factuelle + atemporale + sans provenance => web` a ete retiree', suspension_todo)
        self.assertIn('Le vrai rattrapage anti-suspension pour les demandes pures de verification reste a implementer', suspension_todo)
        self.assertNotIn('Promethee', suspension_todo)
        self.assertNotIn('Jonas', suspension_todo)
        self.assertNotIn('techne', suspension_todo)

    def _db_database_view(self, *, backend: str = 'postgresql'):
        return runtime_settings.RuntimeSectionView(
            section='database',
            payload=runtime_settings.normalize_stored_payload(
                'database',
                {
                    'backend': {'value': backend, 'origin': 'db'},
                    'dsn': {'value_encrypted': 'ciphertext', 'origin': 'db'},
                },
            ),
            source='db',
            source_reason='db_row',
        )

    def test_check_db_schema_uses_bootstrap_database_dsn_helper(self) -> None:
        source = (APP_DIR / 'minimal_validation.py').read_text(encoding='utf-8')
        self.assertIn('with _db_conn() as conn:', source)
        self.assertNotIn('psycopg.connect(config.FRIDA_MEMORY_DB_DSN)', source)

    def test_check_db_schema_rejects_unsupported_runtime_database_backend(self) -> None:
        original_get_database = minimal_validation.runtime_settings.get_database_settings
        minimal_validation.runtime_settings.get_database_settings = lambda: self._db_database_view(backend='mysql')
        try:
            with self.assertRaisesRegex(ValueError, 'unsupported runtime database backend: mysql'):
                minimal_validation._check_db_schema()
        finally:
            minimal_validation.runtime_settings.get_database_settings = original_get_database

    def test_bootstrap_database_dsn_requires_env_fallback_while_db_secret_decryption_is_unavailable(self) -> None:
        original_get_database = minimal_validation.runtime_settings.get_database_settings
        original_get_secret = minimal_validation.runtime_settings.get_runtime_secret_value
        original_dsn = config.FRIDA_MEMORY_DB_DSN
        observed = {'called': False}

        def fake_get_runtime_secret_value(section: str, field: str):
            observed['called'] = True
            raise AssertionError('database bootstrap must not resolve runtime secret values')

        minimal_validation.runtime_settings.get_database_settings = self._db_database_view
        minimal_validation.runtime_settings.get_runtime_secret_value = fake_get_runtime_secret_value
        config.FRIDA_MEMORY_DB_DSN = ''
        try:
            with self.assertRaisesRegex(
                runtime_settings.RuntimeSettingsSecretRequiredError,
                'runtime secret decryption is not available',
            ):
                minimal_validation._bootstrap_database_dsn()
        finally:
            minimal_validation.runtime_settings.get_database_settings = original_get_database
            minimal_validation.runtime_settings.get_runtime_secret_value = original_get_secret
            config.FRIDA_MEMORY_DB_DSN = original_dsn

        self.assertFalse(observed['called'])


class MinimalValidationPhase4IdentityDocsTests(unittest.TestCase):
    def test_identity_read_model_contract_no_longer_contradicts_lot3(self) -> None:
        source = (APP_DIR / 'docs' / 'states' / 'specs' / 'identity-read-model-contract.md').read_text(
            encoding='utf-8'
        )

        self.assertIn("Depuis `Lot 3`, cette meme section peut aussi porter une edition controlee", source)
        self.assertIn(
            "le mutateur de la mutable canonique de `Lot 3`, documente separement",
            source,
        )
        self.assertNotIn("lancer encore les lots d'edition (`Lot 3`, `Lot 4`)", source)
        self.assertNotIn("- l'edition du dynamique (`Lot 3`);", source)


if __name__ == '__main__':
    unittest.main()
