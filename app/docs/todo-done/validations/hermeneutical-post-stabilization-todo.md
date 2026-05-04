# Hermeneutical Post-Stabilization - archive de validation

Statut: cloture
Classement: `app/docs/todo-done/validations/`
Portee: preuves automatisees post-stabilisation du pipeline memoire / hermeneutique deja livre
Origine: extraction du chantier archive `app/docs/todo-done/notes/hermeneutical-add-todo.md`
Recadrage: `2026-05-04`, apres audit global et remediation lots 1 a 6
Validation de cloture: `app/docs/todo-done/validations/hermeneutical-post-stabilization-validation-2026-05-04.md`

## Source de verite runtime

- Pipeline courant: `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`
- Cartographie memoire/RAG: `app/docs/states/architecture/memory-rag-current-pipeline-cartography.md`
- Jugement hermeneutique: `app/docs/states/specs/hermeneutic-judgment-spec.md`
- Panier pre-arbitre: `app/docs/states/specs/memory-rag-pre-arbiter-basket-contract.md`
- Lane summaries: `app/docs/states/specs/memory-rag-summaries-lane-contract.md`
- Logs applicatifs: `app/docs/states/specs/log-module-contract.md`
- Doctrine identity: `app/docs/states/policies/identity-new-contract-plan.md`
- Cloture operatoire identity: `app/docs/todo-done/refactors/identity-new-contract-todo.md`
- Cloture audit global: `app/docs/todo-done/audits/fridadev-global-audit-remediation-todo.md`

## Decision de recadrage

Ce document ne depend plus d'une attente passive de production.

Toute case restante doit etre cloturee par une preuve reproductible:
- test unitaire;
- test de contrat;
- fixture ou corpus controle;
- log synthetique;
- probe read-only explicite et rejouable;
- source guard documentaire quand le point est purement documentaire.

Les formulations du type "observer pendant une fenetre durable", "attendre trois semaines" ou "verifier plus tard en prod" sont hors contrat pour ce TODO.

## Etat reel actuel

Ce qui est deja livre dans le code courant:
- le pipeline chat appelle la branche `stimmung_agent -> primary_node -> validation_agent` avant le LLM final;
- le mode hermeneutique `enforced_all` est supporte par `app/memory/hermeneutics_policy.py`;
- la distinction `no_data` / `retrieve_error` est propagee dans `prepare_memory_context()`, `memory_arbitration`, `branch_skipped`, `prompt_prepared` et Memory Admin;
- la persistance canonique verifiee est la barriere avant traces, ecritures identitaires derivees et reactivation;
- l'identite active repose sur `static + mutable` avec staging / agent periodique / garde deterministe, pas sur les controles legacy;
- les controles legacy `force_accept`, `force_reject`, `relabel` sont neutralises dans les surfaces admin legacy;
- la lane `summaries` et `parent_summary` existent en code et en contrat, mais le runtime OVH observe precedemment restait sans donnees live `summary`;
- le bloc `[Contexte du souvenir]` doit etre lu comme un bloc derive de `parent_summary`, pas comme une memoire de moment autonome;
- Memory Admin et `/log` exposent les evenements `memory_retrieve`, `arbiter`, `prompt_prepared`, `hermeneutic_node_insertion`, `branch_skipped` et les syntheses de latence disponibles.

Ce qui reste reellement a prouver n'est donc plus "est-ce que le chantier hermeneutique existe ?", mais:
- les invariants restent-ils vrais sur fixtures controlees ?
- les surfaces d'observabilite permettent-elles de diagnostiquer les branches utiles ?
- les zones non live, comme `summaries` / `parent_summary`, sont-elles qualifiees sans mentir ?
- les metriques de cout/latence exposent-elles assez de donnees, ou leur manque est-il explicite ?

## Principe de cloture

Une case est cloturable seulement si elle cite:
- le test/probe execute;
- le chemin exact du test ou de la fixture;
- le resultat obtenu;
- le commit de correction si un patch est necessaire.

Ne pas multiplier les sous-lots si une meme preuve couvre plusieurs anciennes cases. Ne pas ouvrir de nouvelle couche memoire, `moment_memory`, `Frida_from_herself` ou refonte identity depuis ce TODO.

## Ordre de lots recommande

1. Lot 1 - Contrats post-stabilisation automatises: fermer les invariants qui peuvent etre prouves sans corpus long ni donnees privees.
2. Lot 2 - Corpus controle memoire / identity: remplacer les anciennes validations "post-prod" par fixtures de conversation et probes read-only.
3. Lot 3 - Rapport de cloture: execute le `2026-05-04`; ce TODO est archive dans `todo-done/validations/`.

## Lot 1 - Contrats post-stabilisation automatises

- [x] HPS-L1-C1 Prouver que `[Contexte du souvenir]` apparait uniquement quand une trace porte un `parent_summary`, et qu'un `parent_summary` duplique n'est injecte qu'une fois.
  - Preuve: `app/tests/unit/memory/test_hermeneutical_post_stabilization_contract.py::test_parent_summary_is_the_only_source_of_contexte_du_souvenir_block`
  - Couvre: ancienne case `[Contexte du souvenir]`.
- [x] HPS-L1-C2 Prouver que `irony|role_play` restent rejetes par la politique identitaire diagnostique meme avec `durable`, `habitual` et forte confiance.
  - Preuve: `app/tests/unit/memory/test_hermeneutical_post_stabilization_contract.py::test_identity_preview_rejects_irony_and_role_play_even_with_durable_high_confidence`
  - Couvre: ancienne case `irony|role_play` cote extracteur / legacy diagnostic.
  - Suite: la validation par corpus du chemin agent periodique actif est cloturee en HPS-L2-C2.
- [x] HPS-L1-C3 Prouver que l'absence normale de memoire et l'erreur technique de retrieval ne se confondent plus.
  - Preuves: `app/tests/unit/chat/test_chat_memory_flow_prepare_context_observability.py`, `app/tests/test_server_admin_memory_surface_phase10e.py`, `app/tests/test_server_logs_phase3.py`
  - Couvre: distinction `no_data` / `retrieve_error` / diagnostic admin.
- [x] HPS-L1-C4 Prouver que `prompt_prepared`, `memory_arbitration` et `hermeneutic_node_insertion` exposent une observabilite compacte et relisible sans contenu brut.
  - Preuves: `app/tests/test_server_chat_compact_observability_contract.py`, `app/tests/test_server_chat_synthetic_logs_contract.py`, `app/tests/test_server_logs_phase3.py`
  - Couvre: ancienne case explicabilite admin/logs.
- [x] HPS-L1-C5 Prouver que le scope courant de la synthese `stage_latency` est explicite et ne se fait pas passer pour un cout global complet.
  - Preuve: `app/tests/unit/memory/test_hermeneutical_post_stabilization_contract.py::test_stage_latency_probe_scope_is_explicit_and_ignores_untracked_stages`
  - Couvre: ancienne case cout/latence en la requalifiant; HPS-L2-C4 liste maintenant les compteurs disponibles et les manques sans pretendre exposer un cout global complet.

## Lot 2 - Corpus controle memoire / identity

- [x] HPS-L2-C1 Remplacer "bruit identitaire circonstanciel baisse par rapport a la baseline" par un corpus fixture versionne.
  - Fixture: `app/tests/support/hermeneutical_post_stabilization_l2_corpus.json`
  - Preuve: `app/tests/unit/memory/test_hermeneutical_post_stabilization_contract.py::test_l2_fixture_blocks_circumstantial_noise_from_mutable_canon`
  - Resultat: OK via `docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python tests/unit/memory/test_hermeneutical_post_stabilization_contract.py`.
  - Limite: le corpus reste synthetique; il verrouille l'admission canonique active, pas une statistique de bruit live.
- [x] HPS-L2-C2 Verifier le chemin identity actif `staging -> identity_periodic_agent -> apply` sur cas `irony|role_play`.
  - Fixture: fenetre controlee de 15 paires `role_play|irony` dans `app/tests/support/hermeneutical_post_stabilization_l2_corpus.json`.
  - Correction runtime bornee: `app/core/chat_memory_flow.py` vide le contenu des roles marques `irony|role_play` par l'extracteur avant staging actif, afin que le scoring deterministe ne puisse pas transformer cette fenetre en support canonique.
  - Preuve: `app/tests/unit/memory/test_hermeneutical_post_stabilization_contract.py::test_l2_active_identity_staging_does_not_canonize_role_play_or_irony_window`
  - Resultat: OK; aucune ecriture `mutable`, `canonical_write_applied=false`, buffer vide apres `completed_no_change`.
  - Limite: la detection `irony|role_play` depend encore de l'extracteur; le garde evite la canonisation quand ce signal existe.
- [x] HPS-L2-C3 Mesurer le rappel memoire utile sur un corpus minimal stable.
  - Fixture: cas `no_data`, `retrieve_error` simule et trace utile avec `parent_summary` dans `app/tests/support/hermeneutical_post_stabilization_l2_corpus.json`.
  - Preuve: `app/tests/unit/memory/test_hermeneutical_post_stabilization_contract.py::test_l2_memory_corpus_links_retrieval_basket_arbitration_and_prompt_injection`
  - Resultat: OK; `retrieve_error` reste distinct de `no_data`, les IDs candidats restent lies de `memory_retrieved` a `memory_arbitration` puis `memory_prompt_injection`.
  - Limite: corpus minimal synthetique; la qualite de rappel live reste un sujet de corpus futur, pas une attente passive de prod.
- [x] HPS-L2-C4 Consolider le cout `tokens + latence` du pipeline memoire/hermeneutique complet.
  - Preuve: `app/tests/unit/memory/test_hermeneutical_post_stabilization_contract.py::test_l2_cost_latency_probe_names_available_counters_and_missing_global_cost`
  - Resultat: OK; compteurs disponibles listes: `context_build.estimated_context_tokens`, `prompt_prepared.estimated_prompt_tokens`, `prompt_prepared.memory_items_used`, `llm_call.duration_ms`, `turn_end.duration_ms`, latences agregees `retrieve|arbiter|identity_extractor`.
  - Limite explicite: `identity_periodic_agent` et `hermeneutic_node_insertion` peuvent emettre des latences brutes mais ne sont pas agreges par `admin_stage_latency_summary`; aucun cout global complet n'est pretendu.
- [x] HPS-L2-C5 Verifier qu'aucun fallback global de type "garder tout" ou "injecter sans preuve" ne reapparait.
  - Preuves: `app/tests/unit/memory/test_hermeneutical_post_stabilization_contract.py::test_l2_arbiter_parse_failure_never_reinjects_the_full_basket` et `app/tests/unit/chat/test_chat_memory_flow_prepare_context_observability.py::test_prepare_memory_context_propagates_retrieve_error_without_calling_arbiter`.
  - Resultat: OK; parse/runtime failure arbitre garde au plus le top-1 au-dessus du seuil explicite, garde zero sous seuil, et retrieval failure passe par `retrieve_error` sans arbitre.
  - Limite: le fallback top-1 reste un comportement fail-open assume; il est borne par `ARBITER_MIN_SEMANTIC_RELEVANCE`, pas supprime.

## Lot 3 - Cloture documentaire

- [x] HPS-L3-C1 Executer tous les tests/probes listes par ce TODO dans un seul bloc de verification.
  - Preuve: bloc de verification execute le `2026-05-04`, voir `app/docs/todo-done/validations/hermeneutical-post-stabilization-validation-2026-05-04.md`.
  - Resultat: OK sur toutes les suites HPS-L1/HPS-L2 et contrats adjacents listes ci-dessous.
- [x] HPS-L3-C2 Ajouter une note de validation sous `app/docs/todo-done/validations/` avec commandes, resultats et limites.
  - Preuve: `app/docs/todo-done/validations/hermeneutical-post-stabilization-validation-2026-05-04.md`.
- [x] HPS-L3-C3 Archiver ce TODO si HPS-L1 et HPS-L2 sont complets, sans ouvrir de nouveau chantier runtime.
  - Preuve: deplacement par `git mv` vers `app/docs/todo-done/validations/hermeneutical-post-stabilization-todo.md`.
  - Resultat: aucun nouveau chantier runtime ouvert; HPS-L1 et HPS-L2 restent couverts par tests/probes automatises.

## Matrice de remplacement des anciennes cases

| Ancienne formulation | Statut actuel | Nouvelle validation |
| --- | --- | --- |
| Valider sur corpus post-stabilisation que le bruit identitaire circonstanciel baisse reellement par rapport a la baseline. | Remplacee par fixture synthetique versionnee, cloturee. | HPS-L2-C1. |
| Verifier sur corpus post-stabilisation qu'aucune entree `irony|role_play` n'arrive en identite durable sans override humain explicite. | Cloturee cote legacy diagnostic et chemin canon actif quand le signal `utterance_mode` existe. | HPS-L1-C2 puis HPS-L2-C2. |
| Mesurer sur conversations longues / corpus de stabilisation que le rappel memoire utile reste stable. | Remplacee par corpus minimal rejouable `no_data` / `retrieve_error` / utile, cloturee pour ce TODO. | HPS-L2-C3. |
| Consolider le surcout global `tokens + latence`. | Requalifiee: les compteurs disponibles et les manques sont explicites; pas de pretention de cout global. | HPS-L1-C5 puis HPS-L2-C4. |
| Verifier sur une fenetre durable qu'aucun fallback global ne reapparait. | Remplacee par test de branches d'erreur et fallback arbitre borne, cloturee. | HPS-L2-C5. |
| Echantillonner l'explicabilite via les logs admin. | Largement couvert par contrats existants. | HPS-L1-C3 et HPS-L1-C4. |
| Trancher le statut reel du bloc `[Contexte du souvenir]`. | Contrat precise: derive de `parent_summary`; live precedent neutre si `summaries=0`. | HPS-L1-C1; HPS-L2-C3 si un corpus summary utile est ajoute. |

## Commandes de verification

Bloc HPS execute pour la validation de cloture le `2026-05-04`:

```bash
docker exec platform-fridadev python tests/unit/memory/test_hermeneutical_post_stabilization_contract.py
docker exec platform-fridadev python tests/unit/memory/test_memory_store_blocks_phase8bis.py
docker exec platform-fridadev python tests/test_memory_store_phase4.py
docker exec platform-fridadev python tests/unit/chat/test_chat_memory_flow_prepare_context_observability.py
docker exec platform-fridadev python tests/unit/chat/test_chat_memory_flow_prepare_context_contracts.py
docker exec platform-fridadev python tests/test_server_chat_compact_observability_contract.py
docker exec platform-fridadev python tests/test_server_chat_synthetic_logs_contract.py
docker exec platform-fridadev python tests/test_server_admin_memory_surface_phase10e.py
docker exec platform-fridadev python tests/test_server_admin_hermeneutics_phase4.py
docker exec platform-fridadev python tests/test_server_logs_phase3.py
docker exec platform-fridadev python tests/unit/chat/test_chat_memory_flow_identity_mode_pipeline.py
docker exec platform-fridadev python tests/unit/chat/test_chat_memory_flow_identity_content_guards.py
```

Preuve live minimale executee dans le meme cycle:

```bash
docker ps --filter name=platform-fridadev --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
curl --max-time 12 -sSI https://fridadev.frida-system.fr/admin | sed -n '1,12p'
```

## Hors scope

- pas de nouvelle couche `moment_memory`;
- pas de chantier `Frida_from_herself`;
- pas de refonte identity;
- pas de refonte memory_store;
- pas de refonte frontend;
- pas de modification Caddy / Authelia / plateforme;
- pas de lecture `.env`, secrets, DSN complets ou donnees conversationnelles privees.
