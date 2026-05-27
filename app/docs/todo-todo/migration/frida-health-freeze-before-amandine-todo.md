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

- [ ] Inventorier les tables DB contenant des donnees utilisateur ou etat runtime:
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
- [ ] Pour chaque table, classer pour Amandine:
  - seed propre requis;
  - vide au depart;
  - valeur runtime a reseeder;
  - archive Frida a ne pas copier;
  - backup obligatoire avant action.
- [ ] Inventorier `state/` sans afficher contenu sensible:
  - chemins;
  - tailles;
  - counts;
  - extensions;
  - timestamps;
  - pas de dump de fichiers.
- [ ] Identifier les fichiers `state/` a rendre neufs pour Amandine:
  - conversations;
  - logs;
  - uploads;
  - active documents;
  - identity state;
  - caches.
- [ ] Identifier les fichiers de config/code a conserver depuis le repo:
  - prompts;
  - specs;
  - assets;
  - migrations SQL;
  - seeds non secrets.
- [ ] Preparer la future checklist backup/purge, sans l'executer:
  - backup DB Frida;
  - backup `state/`;
  - preuve de restauration minimale;
  - commande de creation DB neuve;
  - commande de seed runtime settings;
  - verification post-purge.
- [ ] Verifier que les logs recents ne contiennent pas de secret ou contenu brut evident:
  - grep content-free sur noms de variables sensibles;
  - pas d'affichage des valeurs.

### Tests/preuves Lot 3

- [ ] Inventaire DB content-free via requetes `count(*)`, tailles et noms de table seulement.
- [ ] Inventaire `state/` par `find`, `du`, counts, extensions.
- [ ] Grep secret-safe:
  - noms de patterns seulement;
  - aucun affichage de valeur secrete.

### Critere de sortie Lot 3

- [ ] Liste DB/state a neuver pour Amandine complete.
- [ ] Plan backup/purge futur ecrit, non execute.
- [ ] Aucun secret expose.
- [ ] Aucun nettoyage live effectue.

## Lot 4 - Freeze admin / observabilite / verite operateur

- [ ] Verifier `/admin`:
  - modules modeles lisibles;
  - `identity_periodic_model` explique la compatibilite de nom;
  - modele juge mutable `openai/gpt-5.2` visible;
  - prompt/contract/caller visibles;
  - secrets masques.
- [ ] Verifier `/dashboard`:
  - pas de statut mensonger;
  - erreurs et activites recentes comprehensibles;
  - pas de contenu brut sensible hors surfaces prevues.
- [ ] Verifier `/log`:
  - filtres fonctionnels;
  - events `mutable_identity_judge` / `mutable_identity_judge_apply`;
  - pas de fenetre brute;
  - pas de prompt complet.
- [ ] Verifier `/memory-admin`:
  - counts et sources;
  - pas de confusion Memory/RAG/Identity;
  - pas de scoring legacy comme verite active.
- [ ] Verifier `/identity` et `/hermeneutic-admin`:
  - `mutable_judge_v2_add_only` raconte le regime actif;
  - `identity_mutable_staging` raconte la fenetre, pas le canon;
  - read-model ne montre pas `15` comme cible active si un ancien staging existe.
- [ ] Verifier runtime settings:
  - secrets read-only masques;
  - source/source_reason coherents;
  - bootstrap DB externe documente sans DSN.
- [ ] Verifier docs source-of-truth:
  - `app/docs/README.md`;
  - `AGENTS.md`;
  - specs actives;
  - catalogue modeles.

### Tests/preuves Lot 4

- [ ] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_server_admin_settings_read_contract`
- [ ] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_server_admin_settings_read_contract`
- [ ] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_server_admin_identity_read_model_phase2`
- [ ] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_server_admin_identity_read_model_phase2`
- [ ] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.unit.admin.test_identity_governance_service_phase5`
- [ ] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.unit.admin.test_identity_governance_service_phase5`
- [ ] Working copy pre-rebuild: `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python -m unittest tests.test_server_admin_identity_read_model_phase2 tests.test_server_admin_settings_read_contract`
- [ ] Conteneur live apres rebuild: `docker exec platform-fridadev python -m unittest tests.test_server_admin_identity_read_model_phase2 tests.test_server_admin_settings_read_contract`
- [ ] Greps operateur:
  - `grep -RIn "Haiku\\|identity_periodic_agent\\|score-first\\|promotion_to_static_enabled.*true" app/admin app/web app/docs/states app/docs/todo-todo || true`

### Critere de sortie Lot 4

- [ ] Admin raconte le systeme reel.
- [ ] Observabilite utile sans contenu brut.
- [ ] Aucun ancien regime presente comme actif.
- [ ] Secrets masques.

## Lot 5 - Cleanup cible uniquement si bloquant

- [ ] A partir des Lots 0-4, lister uniquement les cleanups qui menacent la duplication.
- [ ] Classer chaque cleanup:
  - bloquant duplication;
  - a corriger avant duplication;
  - peut attendre apres duplication.
- [ ] Chercher code mort dangereux:
  - anciens writers mutables;
  - appels legacy encore actifs;
  - tests stale qui valident un ancien contrat actif;
  - chemins hardcodes Frida/Tof/hostname;
  - dependances implicites a `/opt/platform/fridadev` ou au hostname public.
- [ ] Chercher TODO actifs contradictoires:
  - `app/docs/todo-todo/`;
  - mentions "actif" dans `todo-done/`;
  - doublons de source-of-truth.
- [ ] Verifier modules trop gros/ambigus seulement si cela menace la duplication:
  - pas de refactor esthetique;
  - pas de renommage global;
  - correction minimale et testee si bloquant.
- [ ] Ne corriger dans ce lot que les P0/P1/P2 confirmes.

### Tests/preuves Lot 5

- [ ] Grep hostnames publics:
  - `grep -RIn "fridadev.frida-system.fr\\|fridadev-db.frida-system.fr" app AGENTS.md README.md --exclude-dir=.git || true`
- [ ] Grep chemins OVH / working copy:
  - `grep -RIn "/opt/platform/fridadev\\|/opt/platform/fridadev-app\\|/opt/platform/fridadev-db" app AGENTS.md README.md --exclude-dir=.git || true`
- [ ] Grep traces utilisateur/personnelles hors fixtures attendues:
  - `grep -RIn "Tof\\|Amandine" app AGENTS.md README.md --exclude-dir=.git || true`
- [ ] Inspection manuelle ciblee des identites/statics/prompts:
  - verifier `state/data/identity/`, `app/data/identity/` si present, `app/prompts/` et les docs source-of-truth sans lancer de grep global sur `Frida`;
  - garder `Frida` seulement pour des recherches ciblees par fichier ou section, car c'est le nom normal du produit.
- [ ] Grep legacy actif:
  - `grep -RIn "identity_periodic_agent\\|score_operation\\|apply_periodic_agent_contract\\|target_ref\\|clear_obsolete" app/core app/memory app/admin app/web app/tests || true`
- [ ] Tests cibles selon fichiers corriges.

### Critere de sortie Lot 5

- [ ] Aucun cleanup bloquant duplication ouvert.
- [ ] Les P3 acceptes sont listes.
- [ ] Aucun refactor opportuniste n'a ete lance.

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
