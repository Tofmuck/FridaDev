# Freeze sante Frida avant duplication Amandine

Statut: actif sur `migration`
Portee: audit applicatif FridaDev avant creation d'une instance Amandine separee
But: prouver que Frida est assez saine pour servir de base produit, avec DB neuve et `state/` propre, sans lancer la duplication dans ce chantier.

## Principe

Ce freeze ne cree pas Amandine. Il fige une decision: est-ce que l'instance Frida courante est une base saine pour dupliquer le produit, ou faut-il corriger des points bloquants avant de partir.

La duplication cible est:

```text
repository FridaDev sain
+ DB neuve
+ state propre
+ runtime settings reinitialises/seedes
-> instance Amandine separee
```

Le freeze doit distinguer:

- **Bloquant duplication**: empeche de lancer Amandine proprement.
- **A corriger avant duplication**: non bloquant immediat, mais risquerait de produire une instance confuse ou fragile.
- **Acceptable apres duplication**: P3 connu, documente, sans impact sur la base produit.

## Statut

- [ ] Actif sur `migration`.
- [ ] Aucun changement de plateforme effectue.
- [ ] Aucune purge DB / `state/` effectuee.
- [ ] Aucun secret, DSN complet, token, cookie ou `.env` affiche dans les preuves.
- [ ] Decision finale de freeze non encore prise.

## Hors-scope

- [ ] Ne pas creer la stack Amandine.
- [ ] Ne pas modifier Caddy, Authelia, Docker global, reseaux, secrets ou hostnames.
- [ ] Ne pas purger, copier ou migrer la DB live.
- [ ] Ne pas nettoyer `state/` live.
- [ ] Ne pas changer le modele runtime sans lot separe.
- [ ] Ne pas refactorer le code hors correction bloquante.
- [ ] Ne pas transformer le freeze en audit infini: tout finding doit etre classe P0/P1/P2/P3 et rattache a la duplication.

## Convention d'execution des tests

Chaque preuve doit dire explicitement quel environnement elle teste:

- [ ] **Working copy montee**: utiliser cette forme avant rebuild, pour tester exactement `/opt/platform/fridadev/app`:
  - `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest <suite>`
- [ ] **Conteneur live**: utiliser cette forme apres rebuild, pour tester l'image effectivement servie:
  - `docker exec platform-fridadev python -m unittest <suite>`
- [ ] Un test `docker exec platform-fridadev ...` n'est autoritatif sur un patch recent que si l'app a ete rebuildee depuis ce patch.
- [ ] Pour un patch docs-only, ne pas rebuild; les preuves sont alors `git diff --check`, greps, liens et relecture.

## Lot 0 - Inventaire et cartographie du freeze

- [x] Verifier branche, dernier commit, et clean worktree:
  - `git status --short --branch`
  - `git log --oneline -10`
- [x] Cartographier les surfaces runtime a valider:
  - chat principal;
  - prompt augmente;
  - identity static / mutable;
  - juge mutable v2 add-only;
  - memory / RAG;
  - summaries;
  - web search;
  - active documents;
  - admin;
  - logs / observabilite;
  - runtime settings;
  - backup / restore minimal.
- [x] Lister les specs source-of-truth a relire avant test:
  - `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`;
  - `app/docs/states/audits/fridadev-model-call-catalog-2026-05-17.md`;
  - `app/docs/states/specs/mutable-identity-judge-contract.md`;
  - `app/docs/states/specs/identity-read-model-contract.md`;
  - `app/docs/states/specs/admin-runtime-settings-schema.md`;
  - `app/docs/states/specs/active-conversation-documents-contract.md`;
  - `app/docs/states/specs/fridadev-web-search-regimes-source-first-contract.md`;
  - `app/docs/states/specs/memory-admin-surface-contract.md`.
- [x] Definir le format de preuve content-free:
  - statuts;
  - counts;
  - model ids;
  - routes;
  - timestamps;
  - hashes courts si necessaire;
  - aucune conversation brute;
  - aucune mutable brute hors fixture synthetique.
- [x] Produire un tableau de findings avec colonnes:
  - id;
  - surface;
  - severite P0/P1/P2/P3;
  - duplication impact;
  - correction requise;
  - statut;
  - lien preuve.

### Tests/preuves Lot 0

- [x] `git status --short --branch`
- [x] `find app/docs/todo-todo app/docs/todo-done app/docs/states -maxdepth 3 -type f | sort`
- [x] `grep -RIn "TODO actif\\|chantier actif\\|migration\\|Amandine" app/docs README.md AGENTS.md || true`

### Critere de sortie Lot 0

- [x] Les surfaces a tester sont listees.
- [x] Les preuves attendues sont content-free.
- [x] Les severites P0/P1/P2/P3 sont definies.
- [x] Aucun test destructif n'est prevu.

### Photo operatoire Lot 0 - 2026-05-27

Etat git au demarrage du lot:

- branche: `migration`;
- upstream: `origin/migration`;
- dernier commit avant patch Lot 0: `d274d5a docs: clarify health freeze execution checks`;
- worktree: clean avant patch Lot 0.

Surfaces runtime a tester dans les lots suivants:

| Surface | Lots | Preuve attendue | Destructif |
| --- | --- | --- | --- |
| Chat principal / streaming / prompt augmente | Lot 1 | statuts routes, tests chat, smoke synthetique content-free | non |
| Identity static / mutable / juge mutable v2 add-only | Lot 2 | model id, module, contrat, counts, hashes courts, tests add-only | non |
| Memory / RAG / resumes | Lots 1-2 | counts, routes, status, tests existants, aucun contenu brut | non |
| Web search / documents actifs | Lot 1 | status, source regime, reason codes, non-contamination | non |
| Admin / read-model / runtime settings | Lots 1, 2, 4 | champs operateur, model ids, prompts, contrats | non |
| Logs / observabilite | Lots 1, 4 | events content-free, erreurs classees, aucun secret | non |
| DB / state / backup-restore minimal | Lot 3 | inventaire tables/fichiers, classification neuf/seed/legacy | lecture seule au freeze |
| Code / docs / TODO actifs | Lot 5 | greps classes, tests stale detectes, correction seulement si bloquante | non |

Specs source-of-truth relues ou verifiees:

| Spec | Statut Lot 0 |
| --- | --- |
| `app/docs/states/architecture/fridadev-current-runtime-pipeline.md` | presente |
| `app/docs/states/audits/fridadev-model-call-catalog-2026-05-17.md` | presente |
| `app/docs/states/specs/mutable-identity-judge-contract.md` | presente |
| `app/docs/states/specs/identity-read-model-contract.md` | presente |
| `app/docs/states/specs/admin-runtime-settings-schema.md` | presente |
| `app/docs/states/specs/active-conversation-documents-contract.md` | presente |
| `app/docs/states/specs/fridadev-web-search-regimes-source-first-contract.md` | presente |
| `app/docs/states/specs/memory-admin-surface-contract.md` | presente |

Format de preuve content-free retenu:

- autorise: statuts, counts, model ids, caller/module/contrat, routes, timestamps, reason codes, longueurs, hashes courts, exit codes;
- interdit: conversations brutes, mutables reelles brutes, prompts complets, documents utilisateur complets, secrets, cookies, DSN complets, `.env`;
- fixtures synthetiques autorisees si elles sont explicitement marquees comme telles et ne touchent pas la DB live.

Severites utilisables:

| Severite | Definition freeze |
| --- | --- |
| P0 | risque perte de donnees, fuite secret, corruption DB/state, ou duplication impossible immediatement |
| P1 | pipeline principal casse ou verite operateur fausse sur un mecanisme central avant duplication |
| P2 | incoherence serieuse a corriger avant duplication pour eviter une instance Amandine confuse ou fragile |
| P3 | confort, documentation, dette ou nettoyage acceptable apres duplication si explicitement accepte |

Findings Lot 0:

Aucun P0/P1/P2 ouvert au Lot 0. Un P3 documentaire a ete confirme par le grep `Statut: chantier actif|TODO actif|chantier actif` puis corrige dans les archives concernees.

| ID | Surface | Severite | Duplication impact | Correction requise | Statut | Lien preuve |
| --- | --- | --- | --- | --- | --- | --- |
| LOT0-P3-001 | Archives/docs liees | P3 | faible: grep de freeze plus bruyant, sans effet runtime | requalifier deux libelles archivees et un critere historique de spec qui se disaient encore actifs | corrige | `todo-done/admin/dashboard-long-term-observability-todo.md`; `todo-done/refactors/fridadev-main-model-gpt51-switch-todo.md`; `states/specs/dashboard-long-term-observability-contract.md` |

Risques evidents a surveiller dans les lots suivants:

- ne pas confondre working copy montee et conteneur live non rebuilde;
- ne jamais copier DB/state Frida/Tof vers Amandine par accident;
- verifier explicitement les docs actives qui parlent encore d'Amandine ou de chantiers produit ouverts;
- garder `identity_periodic_model` comme nom de compatibilite seulement, sans raconter l'ancien agent comme actif;
- ne pas convertir le freeze en refactor general: seuls les P0/P1/P2 bloquants doivent etre corriges avant decision.

Aucune action destructive prevue ou executee au Lot 0:

- pas de tests runtime;
- pas de smoke live;
- pas de rebuild;
- pas de lecture ou modification de secrets;
- pas de purge, copie, migration ou ecriture DB/state;
- pas d'action Caddy, Authelia, Docker global, reseaux ou hostnames.

## Lot 1 - Freeze fonctionnel runtime/live

- [x] Verifier que l'app live est healthy:
  - `docker ps --filter name=platform-fridadev --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"`;
  - `curl --max-time 12 -sSI https://fridadev.frida-system.fr/admin | grep -vi '^set-cookie:' | sed -n '1,12p'`.
- [x] Verifier que les routes principales repondent selon leur contrat:
  - `/`;
  - `/admin`;
  - `/dashboard`;
  - `/log`;
  - `/memory-admin`;
  - `/hermeneutic-admin`;
  - `/identity`.
- [x] Executer les tests runtime essentiels dans le conteneur:
  - tests chat flow;
  - tests admin settings read contract;
  - tests identity read-model;
  - tests mutable judge/apply;
  - tests active documents;
  - tests web search si disponibles sans provider externe.
- [x] Smoke chat principal avec conversation synthetique non sensible:
  - verifier reponse streaming;
  - verifier absence d'erreur serveur;
  - verifier prompt augmente actif par observabilite content-free;
  - verifier absence de fuite `reasoning_details`.
- [x] Smoke prompt augmente:
  - presence reference temporelle;
  - identity_input injecte quand attendu;
  - memory/RAG injecte seulement selon contrat;
  - active documents injectes seulement si attaches.
- [x] Smoke summaries:
  - verifier qu'un resume existant est lu sans erreur;
  - verifier qu'aucun resume ne promet une memoire durable inexistante.
- [x] Smoke web search:
  - web off => aucun appel externe;
  - URL explicite => lecture locale/controlee;
  - recherche ouverte => provider configure, observabilite content-free.
- [x] Smoke active documents:
  - document texte synthetique;
  - image/PDF seulement si deja couvert par les tests;
  - verifier non-contamination Memory/RAG/Identity/Summary.
- [x] Verifier absence d'erreurs runtime recentes bloquantes:
  - logs conteneur filtres par `ERROR|CRITICAL|Traceback`;
  - events applicatifs recents content-free;
  - ne pas afficher prompt complet, conversations, secrets.

### Tests/preuves Lot 1

- [x] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.unit.chat.test_chat_memory_flow_identity_mode_pipeline`
- [x] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.unit.chat.test_chat_memory_flow_identity_mode_pipeline`
- [x] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_server_admin_settings_read_contract tests.test_server_admin_identity_read_model_phase2`
- [x] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_server_admin_settings_read_contract tests.test_server_admin_identity_read_model_phase2`
- [x] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.unit.memory.test_mutable_identity_judge tests.unit.memory.test_mutable_identity_apply`
- [x] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.unit.memory.test_mutable_identity_judge tests.unit.memory.test_mutable_identity_apply`
- [x] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_minimal_validation_phase4`
- [x] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_minimal_validation_phase4`
- [x] Smoke live note avec status, routes, model ids et absence d'erreurs.

### Critere de sortie Lot 1

- [x] App live healthy.
- [x] Chat principal OK.
- [x] Admin OK.
- [x] Web/documents/summaries ne presentent aucun P0/P1/P2.
- [x] Les erreurs recentes sont classees ou absentes.

### Photo operatoire Lot 1 - 2026-05-27

Etat repo au demarrage:

- branche: `migration`;
- dernier commit avant patch Lot 1: `c65bce7 docs: clarify health freeze active labels`;
- worktree: clean avant patch Lot 1.

Health live:

| Preuve | Resultat |
| --- | --- |
| conteneur app | `platform-fridadev` up et healthy |
| conteneur DB | `platform-fridadev-postgres` up et healthy |
| `/admin` public | `HTTP/2 302` vers Authelia, cookies filtres |
| routes `/`, `/admin`, `/dashboard`, `/log`, `/memory-admin`, `/hermeneutic-admin`, `/identity` | toutes `HTTP/2 302` vers Authelia, cookies filtres |

Tests obligatoires:

Note: aucun patch runtime n'a ete fait au Lot 1, donc aucun rebuild n'a ete lance. Les lignes "conteneur live apres rebuild" ci-dessus sont cochees comme preuves du conteneur actuellement servi, pas comme validation d'une image rebuildee apres ce patch docs-only.

| Environnement | Suite | Resultat |
| --- | --- | --- |
| working copy montee | `tests.unit.chat.test_chat_memory_flow_identity_mode_pipeline` | OK, 5 tests |
| conteneur live | `tests.unit.chat.test_chat_memory_flow_identity_mode_pipeline` | OK, 5 tests |
| working copy montee | `tests.test_server_admin_settings_read_contract tests.test_server_admin_identity_read_model_phase2` | OK, 26 tests; logs DB indisponible attendus car `docker run` non attache au Postgres live |
| conteneur live | `tests.test_server_admin_settings_read_contract tests.test_server_admin_identity_read_model_phase2` | OK, 26 tests |
| working copy montee | `tests.unit.memory.test_mutable_identity_judge tests.unit.memory.test_mutable_identity_apply` | OK, 27 tests |
| conteneur live | `tests.unit.memory.test_mutable_identity_judge tests.unit.memory.test_mutable_identity_apply` | OK, 27 tests |
| working copy montee | `tests.test_minimal_validation_phase4` | OK, 9 tests |
| conteneur live | `tests.test_minimal_validation_phase4` | OK, 9 tests |

Smokes complementaires content-free:

| Surface | Environnement | Preuve | Resultat |
| --- | --- | --- | --- |
| chat stream / prompt augmente / summaries | working copy montee | tests cibles `test_server_logs_phase3` | OK, 4 tests; logs DB indisponible attendus en `docker run` |
| chat stream / prompt augmente / summaries | conteneur live | tests cibles `test_server_logs_phase3` | OK, 4 tests |
| documents actifs / non-contamination | working copy montee | `test_server_active_documents_contract`, `test_active_document_prompt_lane`, `test_active_document_non_contamination_lot5`, `test_active_documents_observability_lot7` | OK, 47 tests; fixtures synthetiques |
| documents actifs / non-contamination | conteneur live | memes suites | OK, 47 tests |
| web search source-first / observabilite | conteneur live | `tests.unit.web_search.test_web_search_phase4`, `tests.unit.web_search.test_web_search_source_first`, `tests.unit.web_search.test_web_search_observability`, `tests.unit.logs.test_chat_turn_logger_web_search` | OK, 48 tests |
| web search source-first / observabilite | working copy montee | memes suites importables | P3: 47/48 OK, 1 test depend de settings DB/secrets absents dans `docker run`; le conteneur live passe |

Observabilite live content-free:

| Surface | Resultat |
| --- | --- |
| admin settings `identity_periodic_model` | model `openai/gpt-5.2`, module `mutable_identity_judge_v2_add_only`, caller `mutable_identity_judge`, contract `mutable_judge_v2`, prompt resume par longueur/hash court seulement |
| admin settings `main_model` | model `openai/gpt-5.1`, `reasoning_effort=high`, secret `api_key` present mais valeur non visible |
| `/api/admin/logs/chat/metrics` in-container | `events_count=2000`, `errors_by_stage_count=0`, redaction keys presentes |
| `observability.log_store.read_chat_log_events(limit=120)` | 120 events lus, `error_like_count=0`, statuts `ok=114`, `skipped=6` |
| `docker logs --since 2h platform-fridadev | grep ERROR|CRITICAL|Traceback` | aucun hit recent |

Findings Lot 1:

| ID | Surface | Severite | Duplication impact | Correction requise | Statut | Lien preuve |
| --- | --- | --- | --- | --- | --- | --- |
| LOT1-P3-001 | Web search tests en working copy montee | P3 | faible: la preuve montee n'est pas autonome pour un test qui attend runtime settings DB/secrets; pas d'impact live observe | aucune avant duplication; utiliser le conteneur live ou un environnement de test avec DB/settings pour cette preuve | accepte | live OK 48/48; working copy montee 47/48 avec `missing secret config: main_model.api_key` |

Actions non effectuees au Lot 1:

- pas de creation Amandine;
- pas de purge, copie, migration ou ecriture DB/state volontaire;
- pas de rebuild;
- pas de changement modele;
- pas de modification Caddy, Authelia, Docker global, reseaux ou hostnames;
- pas d'affichage volontaire de secret, cookie, DSN complet, `.env`, conversation brute ou prompt complet dans la note de freeze.

## Lot 2 - Freeze identity / memoire / mutable

- [x] Verifier `identity_input` compile:
  - static user present si attendu;
  - static llm present si attendu;
  - mutable user present si attendu;
  - mutable llm present si attendu;
  - pas de legacy `identities` comme source active.
- [x] Verifier la surface `/identity`:
  - elle raconte static + mutable comme canon actif;
  - elle distingue staging et canon;
  - elle ne promet pas une memoire durable au-dela du mecanisme existant.
- [x] Verifier `/hermeneutic-admin` identity/read-model:
  - `mutable_judge_runtime.model = openai/gpt-5.2`;
  - `module = mutable_identity_judge_v2_add_only`;
  - `contract = mutable_judge_v2`;
  - `verdicts = add/no_change`;
  - `window_target_pairs = 5`.
- [x] Verifier l'admin settings:
  - `identity_periodic_model.model = openai/gpt-5.2`;
  - `active_module = mutable_identity_judge_v2_add_only`;
  - prompt actif `prompts/identity_mutable_judge_v2.txt`;
  - l'ancien benchmark Haiku est visible seulement comme legacy.
- [x] Smoke mutable add-only avec donnees synthetiques:
  - 5 paires completes;
  - au moins un add `llm`;
  - au moins un add `user`;
  - bruit ignore;
  - pas de `tighten`, `merge`, `clear_obsolete`, `target_ref`, `target_refs`;
  - audit content-free.
- [x] Verifier que la 6e paire repart sur un buffer 1/5 si le test pipeline est rejoue.
- [x] Verifier absence de score-first actif:
  - aucun appel actif `score_operation`;
  - aucun writer `apply_periodic_agent_contract`;
  - aucun scoring comme critere d'admission mutable.
- [x] Verifier absence d'ecriture static automatique:
  - pas de promotion mutable -> static;
  - pas d'appel runtime a `write_static_identity_content`.
- [x] Verifier Memory/RAG:
  - retrieval fonctionne;
  - admin memory raconte les sources et counts;
  - pas de confusion entre souvenirs, resume, identity, active documents.
- [x] Verifier promesses de memoire dans les prompts/UI:
  - pas de promesse de memorisation si aucun mecanisme ne porte l'inscription;
  - mention claire des couches static/mutable/memory quand elles sont exposees.

### Tests/preuves Lot 2

- [x] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.unit.memory.test_mutable_identity_judge tests.unit.memory.test_mutable_identity_apply`
- [x] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.unit.memory.test_mutable_identity_judge tests.unit.memory.test_mutable_identity_apply`
- [x] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.unit.chat.test_mutable_identity_judge_final_validation`
- [x] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.unit.chat.test_mutable_identity_judge_final_validation`
- [x] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_identity_phase4`
- [x] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_identity_phase4`
- [x] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_server_admin_identity_read_model_phase2`
- [x] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_server_admin_identity_read_model_phase2`
- [x] Grep non-concurrence:
  - `grep -RIn "score_operation\\|apply_periodic_agent_contract\\|mutable_judge_v1\\|target_ref\\|target_refs\\|clear_obsolete\\|mutable_tightening\\|mutable_merge" app/core app/memory app/admin app/tests app/docs/states app/docs/todo-todo || true`

### Critere de sortie Lot 2

- [x] Identity injectee coherente.
- [x] Mutable add-only actif et visible.
- [x] Aucun ancien regime mutable actif.
- [x] Aucun P0/P1/P2 identity/memory ouvert.

### Photo operatoire Lot 2 - 2026-05-27

Etat repo au demarrage:

- branche: `migration`;
- dernier commit avant patch Lot 2: `781f6fa docs: validate health freeze lot 1 runtime`;
- worktree: clean avant patch Lot 2.

Correction documentaire pre-Lot 2:

- le P3 de lisibilite Lot 1 sur les suites web-search abregees est corrige dans la photo Lot 1;
- les chemins importables notes sont maintenant `tests.unit.web_search.test_web_search_phase4`, `tests.unit.web_search.test_web_search_source_first`, `tests.unit.web_search.test_web_search_observability` et `tests.unit.logs.test_chat_turn_logger_web_search`.

Tests obligatoires:

Note: aucun patch runtime n'a ete fait au Lot 2, donc aucun rebuild n'a ete lance. Les lignes "conteneur live apres rebuild" ci-dessus sont cochees comme preuves du conteneur actuellement servi, pas comme validation d'une image rebuildee apres ce patch docs-only.

| Environnement | Suite | Resultat |
| --- | --- | --- |
| working copy montee | `tests.unit.memory.test_mutable_identity_judge tests.unit.memory.test_mutable_identity_apply` | OK, 27 tests |
| conteneur live | `tests.unit.memory.test_mutable_identity_judge tests.unit.memory.test_mutable_identity_apply` | OK, 27 tests |
| working copy montee | `tests.unit.chat.test_mutable_identity_judge_final_validation` | OK, 1 test |
| conteneur live | `tests.unit.chat.test_mutable_identity_judge_final_validation` | OK, 1 test |
| working copy montee | `tests.test_identity_phase4` | OK, 13 tests |
| conteneur live | `tests.test_identity_phase4` | OK, 13 tests |
| working copy montee | `tests.test_server_admin_identity_read_model_phase2` | OK, 3 tests; logs DB indisponible attendus car `docker run` non attache au Postgres live |
| conteneur live | `tests.test_server_admin_identity_read_model_phase2` | OK, 3 tests |

Preuves identity / mutable live content-free:

| Surface | Resultat |
| --- | --- |
| `identity_input` runtime | schema `v2`; `frida.static`, `frida.mutable`, `user.static`, `user.mutable` presents; longueurs et hashes courts verifies; mutables `updated_by=mutable_identity_judge_apply`, `update_reason=mutable_judge_add` |
| `/api/admin/identity/read-model` | `active_identity_source=identity_mutables`, `active_static_source=resource_path_content`, `identity_input_schema_version=v2`, `active_prompt_contract=static + mutable narrative` |
| `mutable_judge_runtime` | model `openai/gpt-5.2`, module `mutable_identity_judge_v2_add_only`, caller `mutable_identity_judge`, contract `mutable_judge_v2`, verdicts `add/no_change`, prompt `prompts/identity_mutable_judge_v2.txt` |
| regime runtime | pipeline `mutable_identity_judge_v2_add_only`, `window_target_pairs=5`, `score_first_writer_enabled=false`, `promotion_to_static_enabled=false`, `manager_operations_enabled=false`, staging non injecte |
| staging live | `identity_mutable_staging`, conversation-scoped latest, buffer `0/5`, non gele, latest activity `mutable_identity_judge` status `ok`, reason `applied`, pipeline v2 add-only |
| admin settings `identity_periodic_model` | model `openai/gpt-5.2`; benchmark courant pointe vers la validation mutable final; ancien benchmark Haiku visible seulement via `legacy_benchmark_decision` |
| `/identity` et runtime representations | route in-container `200`; la source canonique statique + mutable est distinguee de `identity_input`, du texte injecte et du staging; staging marque separe/non injecte |

Preuves Memory/RAG:

| Surface | Resultat |
| --- | --- |
| `/api/admin/memory/dashboard` | `200`, `ok=true`, surface `Memory Admin`, route `/memory-admin`, sections sources/counts disponibles |
| `/api/admin/hermeneutics/arbiter-decisions?limit=5` | `200`, `ok=true`, 5 items compacts |
| suites Memory/RAG live | `tests.test_memory_store_phase4`, `tests.unit.chat.test_chat_memory_flow_prepare_context_contracts`, `tests.test_server_admin_memory_surface_phase10e`: OK, 38 tests |

Smokes mutable add-only:

| Preuve | Resultat |
| --- | --- |
| crash test conversationnel `test_mutable_identity_judge_final_validation` | 5 premieres paires transmises au juge fake v2, add `llm` et `user`, bruit ignore, aucun champ v1, writer `mutable_identity_judge_apply`, aucune ecriture static |
| 6e paire | buffer repart sur `1/5`, non gele, sans rejuger/ecrire une seconde fois |

Greps et classements:

| Grep | Classement |
| --- | --- |
| non-concurrence `score_operation|apply_periodic_agent_contract|mutable_judge_v1|target_ref|target_refs|clear_obsolete|mutable_tightening|mutable_merge` | aucun appel actif score-first ou writer v1; hits restants = shim v1 retire, tests de rejet/absence, docs legacy pre-Lot-B, ou TODO de verification |
| static write / promotion | aucun appel runtime mutable vers `write_static_identity_content`; hits restants = service admin static explicite, tests d'absence ou docs legacy; `promotion_to_static_enabled=false` dans le read-model |
| promesses memoire | aucun hit dans `app/prompts`; hits restants = UI Memory Admin qui distingue memoire durable/contexte summary, docs de doctrine/evaluation, TODO qui interdit les fausses promesses |

Findings Lot 2:

| ID | Surface | Severite | Duplication impact | Correction requise | Statut | Lien preuve |
| --- | --- | --- | --- | --- | --- | --- |
| LOT2-P3-001 | Lot 1 docs | P3 | nul apres correction; les commandes web-search sont importables dans la photo Lot 1 | correction docs-only des chemins abreiges | corrige | photo Lot 1 mise a jour |
| LOT2-P3-002 | Memory/RAG tests en working copy montee | P3 | faible: une preuve montee n'est pas autonome pour un test qui attend runtime settings DB/secrets; pas d'impact live observe | aucune avant duplication; utiliser le conteneur live ou un environnement de test avec DB/settings pour cette preuve | accepte | live OK 38/38; working copy montee 37/38 avec `missing secret config: main_model.api_key` |

Actions non effectuees au Lot 2:

- pas de creation Amandine;
- pas de purge, copie ou migration DB/state;
- pas de modification des mutables/statics reels;
- pas de rebuild;
- pas de changement modele;
- pas de relachement du contrat add-only ontologique;
- pas d'affichage volontaire de conversation brute, mutable brute reelle, prompt complet, secret, cookie, DSN complet ou `.env`.

## Lot 3 - Freeze DB / state / logs et preparation purge future

- [x] Inventorier les tables DB contenant des donnees utilisateur ou etat runtime:
  - conversations;
  - messages;
  - memories;
  - summaries;
  - identity_mutables;
  - identity_mutable_audit;
  - identity_mutable_staging;
  - runtime_settings;
  - logs/events;
  - active documents;
  - documents uploades;
  - caches eventuels.
- [x] Pour chaque table, classer pour Amandine:
  - seed propre requis;
  - vide au depart;
  - valeur runtime a reseeder;
  - archive Frida a ne pas copier;
  - backup obligatoire avant action.
- [x] Inventorier `state/` sans afficher contenu sensible:
  - chemins;
  - tailles;
  - counts;
  - extensions;
  - timestamps;
  - pas de dump de fichiers.
- [x] Identifier les fichiers `state/` a rendre neufs pour Amandine:
  - conversations;
  - logs;
  - uploads;
  - active documents;
  - identity state;
  - caches.
- [x] Identifier les fichiers de config/code a conserver depuis le repo:
  - prompts;
  - specs;
  - assets;
  - migrations SQL;
  - seeds non secrets.
- [x] Preparer la future checklist backup/purge, sans l'executer:
  - backup DB Frida;
  - backup `state/`;
  - preuve de restauration minimale;
  - commande de creation DB neuve;
  - commande de seed runtime settings;
  - verification post-purge.
- [x] Verifier que les logs recents ne contiennent pas de secret ou contenu brut evident:
  - grep content-free sur noms de variables sensibles;
  - pas d'affichage des valeurs.

### Tests/preuves Lot 3

- [x] Inventaire DB content-free via requetes `count(*)`, tailles et noms de table seulement.
- [x] Inventaire `state/` par `find`, `du`, counts, extensions.
- [x] Grep secret-safe:
  - noms de patterns seulement;
  - aucun affichage de valeur secrete.

### Critere de sortie Lot 3

- [x] Liste DB/state a neuver pour Amandine complete.
- [x] Plan backup/purge futur ecrit, non execute.
- [x] Aucun secret expose.
- [x] Aucun nettoyage live effectue.

### Photo operatoire Lot 3 - 2026-05-27

Etat repo au demarrage:

- branche: `migration`;
- dernier commit avant patch Lot 3: `7e2c67e docs: validate health freeze lot 2 identity`;
- worktree: clean avant patch Lot 3.

Sources relues:

- `app/docs/todo-done/migrations/fridadev-to-frida-system-migration-todo.md`: archive OVH, DB dediee Frida, principe backup avant action;
- `app/docs/states/baselines/database-schema-baseline.md`: baseline DB historique, completee par introspection live;
- `app/admin/sql/runtime_settings_v1.sql`: sections runtime settings a reseeder, dont `identity_periodic_model`;
- modules de persistence: `memory_store.py`, `memory_identity_mutables.py`, `memory_identity_staging.py`, `observability/`, `core/active_conversation_documents.py`, workspace files.

Inventaire DB live content-free:

Note: inventaire par schemas/tables, counts, tailles, colonnes texte/json/bytea comptees, timestamps min/max seulement. Aucun contenu texte, JSON payload, document, conversation, mutable, secret ou DSN n'a ete affiche.

| Famille | Relations observees | Rows | Classification Amandine |
| --- | --- | --- | --- |
| conversations | `public.conversations`, `public.conversation_messages` | 107 / 861 | `frida_archive_do_not_copy`, `empty_for_amandine`, `backup_required_before_action` |
| memory/RAG | `public.traces`, `public.summaries`, `public.arbiter_decisions` | 743 / 2 / 1931 | `frida_archive_do_not_copy`, `empty_for_amandine`, `backup_required_before_action` |
| identity legacy/evidence | `public.identities`, `public.identity_evidence`, `public.identity_conflicts` | 395 / 415 / 1064 | `frida_archive_do_not_copy`, `empty_for_amandine`; legacy non source active mais a sauvegarder avant purge |
| identity mutable canon/audit/staging | `public.identity_mutables`, `public.identity_mutable_audit`, `public.identity_mutable_staging` | 2 / 9 / 22 | `frida_archive_do_not_copy`, `empty_for_amandine`; futur seed Amandine separe si decision produit |
| runtime settings | `public.runtime_settings`, `public.runtime_settings_history` | 14 / 65 | `runtime_setting_reseed`; historique Frida `frida_archive_do_not_copy`; secrets reseedes hors Git |
| active documents | `public.active_conversation_documents` | 6 | `frida_archive_do_not_copy`, `empty_for_amandine`, `backup_required_before_action` |
| workspace/catalogue files | `public.workspace_folders`, `public.workspace_files`, `public.workspace_file_selections` | 2 / 12 / 12 | `frida_archive_do_not_copy` sauf seed produit explicite; fichiers associes a neuver |
| hermeneutic state | `public.hermeneutic_node_states` | 22 | `frida_archive_do_not_copy`, `empty_for_amandine` |
| observability raw/events | `observability.chat_log_events` | 138885 | `frida_archive_do_not_copy`, `empty_for_amandine`, `backup_required_before_action` |
| observability projections | `observability.dashboard_turn_facts`, `dashboard_conversation_summaries`, `dashboard_metric_buckets`, `dashboard_materialization_status` | 1319 / 90 / 713 / 1 | `empty_for_amandine`; regenerable depuis events si events seedes, sinon repartir vide |

Etat DB support:

| Preuve | Resultat |
| --- | --- |
| schemas live | `public`, `observability` |
| extensions live | `pg_trgm`, `pgcrypto`, `plpgsql`, `vector` |
| `runtime_settings` | 14 sections, toutes avec marqueur `is_secret`; 4 lignes avec marqueur `value_encrypted`; valeurs non affichees |
| section modele mutable | `identity_periodic_model`, updated_by `celebrimbor_mutable_judge_model_cutover`, a reseeder pour Amandine vers le modele decide |

Inventaire `state/` / mounts runtime content-free:

Mounts observes sur `platform-fridadev`:

| Source hote | Destination conteneur | Classification Amandine |
| --- | --- | --- |
| `/opt/platform/fridadev-app/state/conv` | `/app/conv` | `empty_for_amandine`; contient fichiers workspace/documents Frida |
| `/opt/platform/fridadev-app/state/logs` | `/app/logs` | `empty_for_amandine`; logs Frida a archiver, ne pas copier |
| `/opt/platform/fridadev/state/data` | `/app/data` | seed a reconstruire: identites/prompts/data produit selon decision; backups Frida a ne pas copier |

Inventaire fichiers sans contenu:

| Racine | Counts / taille | Extensions | Bornes dates | Classification Amandine |
| --- | --- | --- | --- | --- |
| repo `state/data/identity` | 7 fichiers, 5263 bytes | `.json` 2, `.md` 1, `.txt` 4 | 2026-04-12 -> 2026-05-26 | `seed_required` ou redefinition produit; ne pas copier tel quel si identite Frida/Tof |
| repo `state/data/backups/manual-static-promotion/...` | 5 fichiers, 5723 bytes | `.json`/`.txt` | 2026-05-26 | `frida_archive_do_not_copy` |
| runtime `state/conv/_workspace_files/...` | 10 fichiers, environ 4.2 MiB | `.pdf` 8, `.docx` 1, `.md` 1 | 2026-05-20 -> 2026-05-27 | `frida_archive_do_not_copy`, `empty_for_amandine` |
| runtime `state/logs` | 15 fichiers, environ 1.2 MiB | `.jsonl` 15 | 2026-05-07 -> 2026-05-27 | `frida_archive_do_not_copy`, `empty_for_amandine` |
| runtime app `state/data` | environ 28 KiB | identity/prompts/migrations dirs | selon fichiers | conserver seulement seeds non secrets explicitement retenus |

Familles a rendre neuves pour Amandine:

- DB conversations/messages/traces/summaries/arbiter decisions;
- DB identity mutables/audit/staging et tables identity legacy/evidence/conflicts;
- DB active documents et workspace file selections/files/folders;
- DB observability raw events et projections dashboard;
- runtime `state/conv` et documents uploades;
- runtime `state/logs`;
- runtime identity/static files si elles portent Frida/Tof, a remplacer par seed Amandine explicite;
- runtime settings: reseed depuis valeurs produit, sans copier historique ni secrets Frida.

Fichiers de config/code a conserver depuis le repo:

- prompts applicatifs et prompts v2, apres verification produit;
- specs source-of-truth;
- assets UI;
- migrations SQL et code de creation tables;
- tests;
- seeds non secrets explicitement valides;
- pas les backups manuels Frida, logs live, uploads ou fichiers identity personnels.

Checklist future backup/purge, non executee:

1. annoncer gel des ecritures Frida si une purge/copie reelle est planifiee;
2. backup DB Frida complet hors Git, avec horodatage et verification `pg_restore --list`;
3. backup `state/` Frida hors Git: `fridadev-app/state/conv`, `fridadev-app/state/logs`, `fridadev/state/data`;
4. preuve de restauration minimale dans une DB temporaire dediee, jamais dans la DB live;
5. creation DB Amandine neuve avec extensions `pgcrypto`, `vector`, `pg_trgm` si le runtime les attend;
6. application migrations/schema depuis le repo;
7. seed runtime settings Amandine: modeles, services, resources, database, identity governance; secrets injectes hors Git;
8. seed identity/static Amandine seulement apres decision produit explicite;
9. verification post-seed: counts attendus vides, runtime settings presents, secrets masques, admin lisible;
10. aucun transfert de conversations, logs, documents, mutables, traces ou summaries Frida/Tof vers Amandine sans GO explicite.

Checks logs secret-safe:

| Source | Preuve | Resultat |
| --- | --- | --- |
| `/opt/platform/fridadev-app/state/logs` | compte par motif, sans lignes ni valeurs | 15 fichiers; `OPENROUTER_API_KEY`, `FRIDA_MEMORY_DB_DSN`, `Authorization`, `Bearer`, `Set-Cookie`, `Cookie:`, `password`, `secret`, `api_key`, `dsn`, `.env` = 0; motif generique `token` = 1688 occurrences, a verifier au Lot 4 si les logs doivent etre exportes |
| `/opt/platform/fridadev/state/data` | compte par motif, sans lignes ni valeurs | 12 fichiers; 0 occurrence sur tous les motifs sensibles testes |
| `docker logs --since 24h platform-fridadev` | compte motifs seulement | 0 bytes retournes; 0 `ERROR`, `CRITICAL`, `Traceback` et 0 motif secret teste |
| `observability.chat_log_events` recents | 7 events lus via API interne, motifs comptes sans payload affiche | 0 occurrence motif secret teste; 0 statut `error` |

Findings Lot 3:

| ID | Surface | Severite | Duplication impact | Correction requise | Statut | Lien preuve |
| --- | --- | --- | --- | --- | --- | --- |
| LOT3-P3-001 | `state/logs` | P3 | faible: le motif generique `token` apparait dans les logs jsonl, probablement noms de champs/counts; aucune valeur n'a ete affichee ni confirmee | verifier au Lot 4 avant tout export de logs; ne pas copier logs Frida vers Amandine | accepte | grep secret-safe counts |

Actions non effectuees au Lot 3:

- pas de creation Amandine;
- pas de purge, copie, dump, restore ou migration DB;
- pas d'ecriture DB/state volontaire;
- pas de nettoyage `state/`;
- pas de rebuild/restart;
- pas de modification modele/runtime/platforme;
- pas d'affichage volontaire de secret, cookie, DSN complet, `.env`, conversation brute, mutable brute, prompt complet, document utilisateur ou payload log brut.

## Lot 4 - Freeze admin / observabilite / verite operateur

- [x] Verifier `/admin`:
  - modules modeles lisibles;
  - `identity_periodic_model` explique la compatibilite de nom;
  - modele juge mutable `openai/gpt-5.2` visible;
  - prompt/contract/caller visibles;
  - secrets masques.
- [x] Verifier `/dashboard`:
  - pas de statut mensonger;
  - erreurs et activites recentes comprehensibles;
  - pas de contenu brut sensible hors surfaces prevues.
- [x] Verifier `/log`:
  - filtres fonctionnels;
  - events `mutable_identity_judge` / `mutable_identity_judge_apply`;
  - pas de fenetre brute;
  - pas de prompt complet.
- [x] Verifier `/memory-admin`:
  - counts et sources;
  - pas de confusion Memory/RAG/Identity;
  - pas de scoring legacy comme verite active.
- [x] Verifier `/identity` et `/hermeneutic-admin`:
  - `mutable_judge_v2_add_only` raconte le regime actif;
  - `identity_mutable_staging` raconte la fenetre, pas le canon;
  - read-model ne montre pas `15` comme cible active si un ancien staging existe.
- [x] Verifier runtime settings:
  - secrets read-only masques;
  - source/source_reason coherents;
  - bootstrap DB externe documente sans DSN.
- [x] Verifier docs source-of-truth:
  - `app/docs/README.md`;
  - `AGENTS.md`;
  - specs actives;
  - catalogue modeles.

### Tests/preuves Lot 4

- [x] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_server_admin_settings_read_contract`
- [x] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_server_admin_settings_read_contract`
- [x] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_server_admin_identity_read_model_phase2`
- [x] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_server_admin_identity_read_model_phase2`
- [x] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.unit.admin.test_identity_governance_service_phase5`
- [x] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.unit.admin.test_identity_governance_service_phase5`
- [x] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_server_admin_identity_read_model_phase2 tests.test_server_admin_settings_read_contract`
- [x] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_server_admin_identity_read_model_phase2 tests.test_server_admin_settings_read_contract`
- [x] Greps operateur:
  - `grep -RIn "Haiku\\|identity_periodic_agent\\|score-first\\|promotion_to_static_enabled.*true" app/admin app/web app/docs/states app/docs/todo-todo || true`

### Critere de sortie Lot 4

- [x] Admin raconte le systeme reel.
- [x] Observabilite utile sans contenu brut.
- [x] Aucun ancien regime presente comme actif.
- [x] Secrets masques.

### Photo operatoire Lot 4 - 2026-05-27

Etat repo au demarrage:

- branche: `migration`;
- dernier commit avant patch Lot 4: `efe988e docs: validate health freeze lot 3 state`;
- worktree: clean avant patch Lot 4.

Note: aucun patch runtime n'a ete fait au Lot 4, donc aucun rebuild n'a ete lance. Les lignes "conteneur live apres rebuild" ci-dessus sont cochees comme preuves du conteneur actuellement servi, pas comme validation d'une image rebuildee apres ce patch docs-only.

Tests obligatoires:

| Environnement | Suite | Resultat |
| --- | --- | --- |
| working copy montee | `tests.test_server_admin_settings_read_contract` | OK, 23 tests; logs DB indisponible attendus car `docker run` non attache au Postgres live |
| conteneur live | `tests.test_server_admin_settings_read_contract` | OK, 23 tests |
| working copy montee | `tests.test_server_admin_identity_read_model_phase2` | OK, 3 tests; logs DB indisponible attendus car `docker run` non attache au Postgres live |
| conteneur live | `tests.test_server_admin_identity_read_model_phase2` | OK, 3 tests |
| working copy montee | `tests.unit.admin.test_identity_governance_service_phase5` | OK, 6 tests |
| conteneur live | `tests.unit.admin.test_identity_governance_service_phase5` | OK, 6 tests |
| working copy montee | `tests.test_server_admin_identity_read_model_phase2 tests.test_server_admin_settings_read_contract` | OK, 26 tests; logs DB indisponible attendus car `docker run` non attache au Postgres live |
| conteneur live | `tests.test_server_admin_identity_read_model_phase2 tests.test_server_admin_settings_read_contract` | OK, 26 tests |

Verite operateur `/admin` et runtime settings:

| Surface | Resultat |
| --- | --- |
| admin settings `identity_periodic_model` | model `openai/gpt-5.2`, module `mutable_identity_judge_v2_add_only`, caller `mutable_identity_judge`, contract `mutable_judge_v2`, prompt `prompts/identity_mutable_judge_v2.txt` |
| structured output | `response_format=json_schema strict=true`; `provider.require_parameters=true` documente dans la surface readonly |
| compatibilite de nom | slot `identity_periodic_model` expose comme legacy-compatible, pas comme ancien agent periodique actif |
| benchmark courant | `app/docs/todo-done/validations/mutable-identity-judge-final-validation-2026-05-25.md` |
| benchmark Haiku | visible seulement via `legacy_benchmark_decision`, pas comme decision active |
| secrets settings | `main_model.api_key` et `database.dsn` detectes comme secrets; valeurs masquees/non affichees; aucun secret expose dans la preuve |

Verite `/dashboard`, `/log`, `/memory-admin`, `/identity`, `/hermeneutic-admin`:

| Surface | Resultat |
| --- | --- |
| `/dashboard` overview/conversations | routes API in-container OK; materialization OK; `error_count=0`; redaction active; pas de payload brut affiche |
| `/api/admin/logs/chat/metrics` | route OK; `raw_event_payloads_included=false`; metrics sur 2000 events avec troncature explicite |
| `/api/admin/logs/chat?limit=80` | route OK; 80 events compacts lus; statuts `ok=75`, `skipped=5`; longueur max de chaine observee 160 caracteres |
| `/api/admin/logs/chat?stage=mutable_identity_judge` | filtre stage OK; 9 events `mutable_identity_judge`; statuts `ok=3`, `skipped=6`; pas de fenetre brute ni prompt complet |
| `/api/admin/logs?limit=80` | route admin logs OK; 80 events compacts; `mutable_identity_judge_apply` present dans les stages recents; longueur max de chaine observee 52 caracteres |
| filesystem logs `/opt/platform/fridadev-app/state/logs` | `mutable_identity_judge_apply` present; aucun dump de ligne ni valeur affiche; anciens `identity_periodic_agent*` seulement historiques, dernier timestamp 2026-05-24 |
| `/memory-admin` | surface OK; scope distingue Memory Admin, logs, hermeneutic admin et identity; counts/sources disponibles sans scoring legacy actif |
| `/identity` / read-model | pipeline `mutable_identity_judge_v2_add_only`; staging `identity_mutable_staging` separe du canon; `window_target_pairs=5`; pas de cible active `15`; `promotion_to_static_enabled=false`; `score_first_writer_enabled=false` |
| `/hermeneutic-admin` | surface OK; pas de contradiction detectee avec le regime mutable v2 add-only dans les preuves lues |

Classification content-free du motif `token` dans `state/logs`:

| Cle contenant `token` | Count |
| --- | ---: |
| `estimated_prompt_window_tokens` | 196 |
| `estimated_user_tokens` | 192 |
| `max_tokens` | 192 |
| `provider_prompt_tokens` | 190 |
| `provider_completion_tokens` | 190 |
| `provider_total_tokens` | 190 |
| `estimated_assistant_tokens` | 182 |
| `prompt_soft_token_limit` | 153 |
| `token_estimate` | 7 |

Conclusion `token`: les occurrences confirmees sont des noms de cles metriques ou des noms d'evenements techniques, pas des valeurs de secret. Aucune valeur, ligne jsonl, conversation, prompt complet, cookie, DSN ou token d'authentification n'a ete affiche. Les logs Frida restent classes `frida_archive_do_not_copy` / `empty_for_amandine`.

Docs source-of-truth:

| Source | Resultat |
| --- | --- |
| `AGENTS.md` | pointe vers le contrat mutable add-only actif et le catalogue modeles |
| `app/docs/README.md` | indexe le freeze migration actif, les specs admin/identity/log/memory et le catalogue modeles |
| specs actives | `admin-runtime-settings-schema.md`, `identity-read-model-contract.md`, `log-module-contract.md`, `memory-admin-surface-contract.md`, `mutable-identity-judge-contract.md` alignes sur v2 add-only |
| catalogue modeles | runtime mutable documente comme `openai/gpt-5.2` via slot compat `identity_periodic_model`; Haiku reste historique |
| grep operateur | hits restants classes comme compat active explicite, historique date ou instructions de grep/TODO; aucun ancien regime presente comme actif |

Findings Lot 4:

| ID | Surface | Severite | Duplication impact | Correction requise | Statut | Lien preuve |
| --- | --- | --- | --- | --- | --- | --- |
| LOT4-P3-001 | `state/logs` motif `token` | P3 | faible: bruit d'audit secret si on grep le mot `token` sans parser JSON | aucune correction runtime; classifier comme cles metriques et ne pas copier/exporter les logs Frida vers Amandine | ferme | counts par cle token, sans valeurs |
| LOT4-P3-002 | `/log` / observabilite mutable apply | P3 | faible: `mutable_identity_judge` est visible dans `/api/admin/logs/chat`, tandis que `mutable_identity_judge_apply` est visible dans `/api/admin/logs` et les logs filesystem; l'operateur doit connaitre cette separation de sources | a reconsiderer au Lot 5 si `/log` doit unifier explicitement chat events et admin runtime logs; pas bloquant duplication | accepte | API content-free par stage |

Actions non effectuees au Lot 4:

- pas de creation Amandine;
- pas de purge, copie, migration DB/state ou modification logs live;
- pas de changement modele/runtime/prompt;
- pas de cleanup Lot 5;
- pas de rebuild/restart;
- pas d'affichage volontaire de secret, cookie, DSN complet, `.env`, conversation brute, mutable brute, prompt complet, payload log brut ou document utilisateur.

## Lot 5 - Cleanup cible uniquement si bloquant

- [x] A partir des Lots 0-4, lister uniquement les cleanups qui menacent la duplication.
- [x] Classer chaque cleanup:
  - bloquant duplication;
  - a corriger avant duplication;
  - peut attendre apres duplication.
- [x] Chercher code mort dangereux:
  - anciens writers mutables;
  - appels legacy encore actifs;
  - tests stale qui valident un ancien contrat actif;
  - chemins hardcodes Frida/Tof/hostname;
  - dependances implicites a `/opt/platform/fridadev` ou au hostname public.
- [x] Chercher TODO actifs contradictoires:
  - `app/docs/todo-todo/`;
  - mentions "actif" dans `todo-done/`;
  - doublons de source-of-truth.
- [x] Verifier modules trop gros/ambigus seulement si cela menace la duplication:
  - pas de refactor esthetique;
  - pas de renommage global;
  - correction minimale et testee si bloquant.
- [x] Ne corriger dans ce lot que les P0/P1/P2 confirmes.

### Tests/preuves Lot 5

- [x] Grep hostnames publics:
  - `grep -RIn "fridadev.frida-system.fr\\|fridadev-db.frida-system.fr" app AGENTS.md README.md --exclude-dir=.git || true`
- [x] Grep chemins OVH / working copy:
  - `grep -RIn "/opt/platform/fridadev\\|/opt/platform/fridadev-app\\|/opt/platform/fridadev-db" app AGENTS.md README.md --exclude-dir=.git || true`
- [x] Grep traces utilisateur/personnelles hors fixtures attendues:
  - `grep -RIn "Tof\\|Amandine" app AGENTS.md README.md --exclude-dir=.git || true`
- [x] Inspection manuelle ciblee des identites/statics/prompts:
  - verifier `state/data/identity/`, `app/data/identity/` si present, `app/prompts/` et les docs source-of-truth sans lancer de grep global sur `Frida`;
  - garder `Frida` seulement pour des recherches ciblees par fichier ou section, car c'est le nom normal du produit.
- [x] Grep legacy actif:
  - `grep -RIn "identity_periodic_agent\\|score_operation\\|apply_periodic_agent_contract\\|target_ref\\|clear_obsolete" app/core app/memory app/admin app/web app/tests || true`
- [x] Tests cibles selon fichiers corriges.

### Critere de sortie Lot 5

- [x] Aucun cleanup bloquant duplication ouvert.
- [x] Les P3 acceptes sont listes.
- [x] Aucun refactor opportuniste n'a ete lance.

### Photo operatoire Lot 5 - 2026-05-27

Etat repo au demarrage:

- branche: `migration`;
- dernier commit avant patch Lot 5: `9f333c7 docs: validate health freeze lot 4 admin`;
- worktree: clean avant patch Lot 5.

Greps executes:

| Preuve | Hits | Classification |
| --- | ---: | --- |
| hostnames publics `fridadev.frida-system.fr|fridadev-db.frida-system.fr` | 113 | majoritairement docs OVH, tests, examples et referers OpenRouter; pas de secret; defaults FridaDev a reseeder pour Amandine via runtime settings/env |
| chemins OVH `/opt/platform/fridadev*` | 76 | docs operations/freeze, AGENTS, archives et chemins de tests OVH; pas de dependance runtime cachee bloquante |
| traces `Tof|Amandine` | 215 apres patch | fixtures/tests/docs et contrat mutable contextualise par identite active; plus de label UI export actif hardcode `Tof` |
| legacy actif `identity_periodic_agent|score_operation|apply_periodic_agent_contract|target_ref|clear_obsolete` | 217 | wrapper technique de fenetre/slot compat, tests de rejet/absence, docs/tests legacy; aucun writer score-first actif |
| labels actifs dans docs `Statut: chantier actif|TODO actif|chantier actif` | 13 | todo-todo actifs, archives qui parlent historiquement de leur cloture, ou grep de freeze; pas de contradiction bloquante |
| inspection `state/data/identity`, `app/data/identity`, `app/prompts` | 19 fichiers | identites Frida/Tof et prompts a reseeder/revoir pour Amandine; aucune purge ou copie effectuee |

Corrections effectuees:

| ID | Surface | Severite | Duplication impact | Correction |
| --- | --- | --- | --- | --- |
| LOT5-P2-001 | export Markdown chat | P2 | une instance Amandine aurait exporte les messages user sous le label `Tof` | label actif remplace par `Utilisateur`; tests frontend et spec mis a jour |
| LOT5-P2-002 | juge mutable v2 | P2 | le validateur ontologique user etait trop lie a une whitelist globale: avant correction il acceptait `Tof` mais pas `Amandine`, puis un audit post-Lot 5 a montre que la whitelist inverse retenait toute mention connue, dont `Amandine` comme tiers sur Frida courante | validation v2 contextualisee par nom principal d'identite active: `Frida` cote `llm`; `Tof` sur Frida courante; `Amandine` seulement si une formulation principale de `user.static` / `user.mutable_current` etablit Amandine; `Utilisateur` reste un label UI export, pas un sujet canonique mutable |

Hits classes sans correction:

| Famille | Decision |
| --- | --- |
| `identity_periodic_agent` dans `chat_memory_flow`, `llm_client`, read-model/admin | compatibilite technique connue: wrapper de fenetre 5 paires et slot historique `identity_periodic_model`; pas de provider legacy ni writer score-first |
| `score_operation` | uniquement test d'absence sur l'applicateur mutable actif |
| `apply_periodic_agent_contract` | 0 hit actif dans les greps Lot 5 |
| `target_ref` / `clear_obsolete` | tests de rejet/absence et docs legacy source-of-truth; pas de champ runtime actif v2 |
| `mutable_judge_v1` / `persist` / `operation` dans tests | tests de shim retire, rejet v1 ou persistence basse couche; pas de test non cible qui valide v1 comme contrat actif |
| hostnames FridaDev dans `config.py`, `config.example.py`, `.env.example` et image generation | defaults/referers FridaDev actuels; Amandine devra reseeder runtime settings/env et eventuellement referers OpenRouter, deja liste dans la checklist DB/state Lot 3 |
| chemins OVH dans AGENTS/docs/tests | documentation de l'environnement courant; utile pour le freeze, pas un chemin applicatif cache |
| `Frida` dans produit/docs | nom normal du produit/assistant; pas grep global comme bruit de duplication |

Tests executes:

| Environnement | Suite | Resultat |
| --- | --- | --- |
| host Python | `python3 -m py_compile app/memory/mutable_identity_judge_v2.py app/memory/mutable_identity_apply.py app/core/chat_memory_flow.py` | OK |
| working copy montee | `tests.unit.memory.test_mutable_identity_judge tests.unit.memory.test_mutable_identity_apply tests.unit.chat.test_mutable_identity_judge_final_validation` | OK, 28 tests |
| host Node | `node --check web/chat_copy_export.js` | OK |
| host Node | `node --check tests/integration/frontend_browser/test_frontend_browser_smoke.js` | OK |
| host Node | `node --test tests/unit/frontend_chat/test_chat_copy_export_module.js` | OK, 4 tests |
| working copy montee | `tests.integration.frontend_chat.test_frontend_chat_contract` | OK, 22 tests |

Findings Lot 5:

| ID | Surface | Severite | Duplication impact | Correction requise | Statut | Lien preuve |
| --- | --- | --- | --- | --- | --- | --- |
| LOT5-P2-001 | export Markdown chat | P2 | label user `Tof` actif dans un export Amandine | remplacer par label generique et tests/spec | corrige | grep `EXPORT_USER_LABEL` |
| LOT5-P2-002 | mutable judge v2 | P2 | le nom canonique user devait suivre le nom principal de l'identite active, sans retenir les simples mentions de tiers | valider le nom de proposition par sujet et formulation principale d'identite active; refuser `Amandine` sur Frida courante si Amandine est seulement mentionnee comme tiers, et refuser `Utilisateur` comme sujet canonique | corrige | tests `mutable_identity_judge` + preuve live content-free |
| LOT5-P3-001 | referers/hostnames FridaDev par defaut | P3 | faible si le reseed runtime Amandine est bien execute; sinon analytics OpenRouter pourraient rester marques FridaDev | documente; reseed env/runtime settings requis au futur lot Amandine | accepte | grep hostnames publics |
| LOT5-P3-002 | separation `/log` judge/apply deja notee Lot 4 | P3 | faible: apply visible via admin logs/filesystem, pas chat events | peut attendre un lot d'unification observabilite si souhaite | accepte | Lot 4 |

Actions non effectuees au Lot 5:

- pas de creation Amandine;
- pas de purge, copie, migration DB/state;
- pas de cleanup large des archives;
- pas de refactor esthetique ni renommage global;
- pas de changement modele runtime;
- pas de modification plateforme;
- pas d'affichage volontaire de secret, cookie, DSN complet, `.env`, payload brut, conversation brute ou prompt complet.

## Lot 6 - Decision de freeze et note finale

- [ ] Rediger une note de validation finale dans `app/docs/todo-done/migrations/`.
- [ ] Inclure:
  - date;
  - branche;
  - commit;
  - tests executes;
  - smokes live;
  - inventaire DB/state;
  - P0/P1/P2 restants;
  - P3 acceptes;
  - decision GO / NO-GO.
- [ ] Si GO:
  - archiver cette TODO dans `app/docs/todo-done/migrations/`;
  - mettre a jour `app/docs/README.md`;
  - ouvrir le prochain plan Amandine uniquement apres decision explicite.
- [ ] Si NO-GO:
  - laisser cette TODO active;
  - ouvrir des micro-lots correctifs classes par severite;
  - ne pas commencer la duplication.

### Tests/preuves Lot 6

- [ ] `git status --short --branch`
- [ ] `git diff --check`
- [ ] Liens docs valides par grep.
- [ ] Note finale relue.

### Critere de sortie Lot 6

- [ ] Decision GO/NO-GO explicite.
- [ ] Preuves centralisees.
- [ ] Aucun P0/P1/P2 ouvert si GO.
- [ ] P3 restants acceptes explicitement.

## Criteres de sortie globaux

Frida est assez saine pour lancer la duplication Amandine si et seulement si:

- [ ] tests essentiels OK;
- [ ] live healthy;
- [ ] admin coherent;
- [ ] smoke chat OK;
- [ ] smoke identity mutable OK;
- [ ] smoke memory/RAG OK;
- [ ] smoke web/documents OK si la duplication Amandine doit utiliser ces capacites des le depart;
- [ ] runtime settings lisibles et secrets masques;
- [ ] modele juge mutable visible: `openai/gpt-5.2`;
- [ ] pipeline mutable actif visible: `mutable_identity_judge_v2_add_only`;
- [ ] aucun ancien regime mutable actif;
- [ ] aucune promotion mutable -> static automatique;
- [ ] inventaire DB/state pret;
- [ ] plan backup/purge futur pret, non execute;
- [ ] aucun P0/P1/P2 ouvert sur pipeline principal;
- [ ] P3 restants listes et acceptes.

## Risques

- Confondre freeze sante et duplication reelle.
- Nettoyer trop tot des donnees live sans backup.
- Copier des donnees Frida/Tof vers Amandine par accident.
- Laisser `identity_periodic_model` etre lu comme ancien agent periodic au lieu de slot de compatibilite du juge mutable.
- Rendre la surface admin rassurante alors que les smokes runtime n'ont pas ete faits.
- Exposer un secret dans une preuve trop bavarde.
- Transformer le freeze en refactor general et perdre le critere produit: base saine pour duplication.

## Definition de fini

- [ ] Les lots 0 a 6 sont coches ou explicitement classes non applicables.
- [ ] La note finale GO/NO-GO existe dans `app/docs/todo-done/migrations/`.
- [ ] Les index docs pointent vers la note finale ou vers cette TODO si elle reste ouverte.
- [ ] La duplication Amandine n'a pas commence dans ce chantier.
- [ ] La prochaine action est claire: corriger les bloquants, ou ouvrir le plan de duplication Amandine.
