# Hermeneutical Post-Stabilization - TODO automatisable

Statut: ouvert
Classement: `app/docs/todo-todo/memory/`
Portee: preuves automatisees post-stabilisation du pipeline memoire / hermeneutique deja livre
Origine: extraction du chantier archive `app/docs/todo-done/notes/hermeneutical-add-todo.md`
Recadrage: `2026-05-04`, apres audit global et remediation lots 1 a 6

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
3. Lot 3 - Rapport de cloture: si tous les tests/probes passent, archiver ce TODO dans `todo-done/notes/` ou `todo-done/validations/`.

## Lot 1 - Contrats post-stabilisation automatises

- [x] HPS-L1-C1 Prouver que `[Contexte du souvenir]` apparait uniquement quand une trace porte un `parent_summary`, et qu'un `parent_summary` duplique n'est injecte qu'une fois.
  - Preuve: `app/tests/unit/memory/test_hermeneutical_post_stabilization_contract.py::test_parent_summary_is_the_only_source_of_contexte_du_souvenir_block`
  - Couvre: ancienne case `[Contexte du souvenir]`.
- [x] HPS-L1-C2 Prouver que `irony|role_play` restent rejetes par la politique identitaire diagnostique meme avec `durable`, `habitual` et forte confiance.
  - Preuve: `app/tests/unit/memory/test_hermeneutical_post_stabilization_contract.py::test_identity_preview_rejects_irony_and_role_play_even_with_durable_high_confidence`
  - Couvre: ancienne case `irony|role_play` cote extracteur / legacy diagnostic.
  - Limite: la validation par corpus du chemin agent periodique actif reste en HPS-L2-C2.
- [x] HPS-L1-C3 Prouver que l'absence normale de memoire et l'erreur technique de retrieval ne se confondent plus.
  - Preuves: `app/tests/unit/chat/test_chat_memory_flow_prepare_context_observability.py`, `app/tests/test_server_admin_memory_surface_phase10e.py`, `app/tests/test_server_logs_phase3.py`
  - Couvre: distinction `no_data` / `retrieve_error` / diagnostic admin.
- [x] HPS-L1-C4 Prouver que `prompt_prepared`, `memory_arbitration` et `hermeneutic_node_insertion` exposent une observabilite compacte et relisible sans contenu brut.
  - Preuves: `app/tests/test_server_chat_compact_observability_contract.py`, `app/tests/test_server_chat_synthetic_logs_contract.py`, `app/tests/test_server_logs_phase3.py`
  - Couvre: ancienne case explicabilite admin/logs.
- [x] HPS-L1-C5 Prouver que le scope courant de la synthese `stage_latency` est explicite et ne se fait pas passer pour un cout global complet.
  - Preuve: `app/tests/unit/memory/test_hermeneutical_post_stabilization_contract.py::test_stage_latency_probe_scope_is_explicit_and_ignores_untracked_stages`
  - Couvre: ancienne case cout/latence en la requalifiant: les latences `retrieve`, `arbiter`, `identity_extractor` sont agregees; le cout global complet reste HPS-L2-C4.

## Lot 2 - Corpus controle memoire / identity

- [ ] HPS-L2-C1 Remplacer "bruit identitaire circonstanciel baisse par rapport a la baseline" par un corpus fixture versionne.
  - Attendu: fixture sous `app/tests/support/` avec cas circonstanciels, cas durables, humeur locale et preferences de reponse.
  - Validation: commande de test qui compare statuts attendus `accepted|deferred|rejected`, sans lire de donnees live privees.
  - Critere: le test echoue si une formulation circonstancielle devient canon durable.
- [ ] HPS-L2-C2 Verifier le chemin identity actif `staging -> identity_periodic_agent -> apply` sur cas `irony|role_play`.
  - Attendu: fixture de 15 paires controlees ou fake agent deterministe, avec operations attendues `no_change` ou rejet applicateur.
  - Validation: test unitaire ou contrat prouvant qu'aucune proposition issue du role-play / ironie n'est appliquee au canon `mutable` sans override humain.
  - Critere: pas d'ecriture canonique, statut observable, buffer non presente comme canon.
- [ ] HPS-L2-C3 Mesurer le rappel memoire utile sur un corpus minimal stable.
  - Attendu: corpus controle avec trois requetes: `no_data`, `retrieve_error` simule, et memoire utile gardee par l'arbitre.
  - Validation: test/probe qui verifie `memory_retrieved`, panier pre-arbitre, `memory_arbitration`, `prompt_prepared.memory_prompt_injection`.
  - Critere: les IDs candidats restent lies du retrieval au prompt, et les erreurs ne deviennent pas `no_data`.
- [ ] HPS-L2-C4 Consolider le cout `tokens + latence` du pipeline memoire/hermeneutique complet.
  - Attendu: probe synthetique ou test de contrat qui lit les evenements `context_build`, `prompt_prepared`, `llm_call`, `turn_end`, `stage_latency`.
  - Validation: rapport de compteurs et durees disponibles, plus liste explicite des stages non chronometres.
  - Critere: le systeme ne pretend pas exposer un cout global si seuls des sous-stages sont mesures.
- [ ] HPS-L2-C5 Verifier qu'aucun fallback global de type "garder tout" ou "injecter sans preuve" ne reapparait.
  - Attendu: source guard ou test de contrat sur l'arbitre, le fallback retrieval et la validation agent.
  - Validation: test qui force parse/retrieval failure et attend une branche borneee `skipped`, `retrieve_error`, ou fallback top-1 sous seuil explicite.
  - Critere: aucune branche ne reinjecte tout le panier sous erreur.

## Lot 3 - Cloture documentaire

- [ ] HPS-L3-C1 Executer tous les tests/probes listes par ce TODO dans un seul bloc de verification.
- [ ] HPS-L3-C2 Ajouter une note de validation sous `app/docs/todo-done/validations/` avec commandes, resultats et limites.
- [ ] HPS-L3-C3 Archiver ce TODO si HPS-L1 et HPS-L2 sont complets, sans ouvrir de nouveau chantier runtime.

## Matrice de remplacement des anciennes cases

| Ancienne formulation | Statut actuel | Nouvelle validation |
| --- | --- | --- |
| Valider sur corpus post-stabilisation que le bruit identitaire circonstanciel baisse reellement par rapport a la baseline. | Reformulee, non cloturee. | HPS-L2-C1, corpus fixture versionne. |
| Verifier sur corpus post-stabilisation qu'aucune entree `irony|role_play` n'arrive en identite durable sans override humain explicite. | Partiellement prouve cote policy legacy diagnostic; actif canon a prouver. | HPS-L1-C2 puis HPS-L2-C2. |
| Mesurer sur conversations longues / corpus de stabilisation que le rappel memoire utile reste stable. | Reformulee, non cloturee. | HPS-L2-C3, corpus controle no_data / retrieve_error / utile. |
| Consolider le surcout global `tokens + latence`. | Scope courant explicite, global non cloture. | HPS-L1-C5 puis HPS-L2-C4. |
| Verifier sur une fenetre durable qu'aucun fallback global ne reapparait. | Reformulee, pas de fenetre durable. | HPS-L2-C5, source guard / test de branches d'erreur. |
| Echantillonner l'explicabilite via les logs admin. | Largement couvert par contrats existants. | HPS-L1-C3 et HPS-L1-C4. |
| Trancher le statut reel du bloc `[Contexte du souvenir]`. | Contrat precise: derive de `parent_summary`; live precedent neutre si `summaries=0`. | HPS-L1-C1; HPS-L2-C3 si un corpus summary utile est ajoute. |

## Commandes de verification

Commandes minimales pour Lot 1:

```bash
docker run --rm -v /opt/platform/fridadev/app:/app -w /app platform-fridadev-app:local python tests/unit/memory/test_hermeneutical_post_stabilization_contract.py
docker exec platform-fridadev python tests/unit/chat/test_chat_memory_flow_prepare_context_observability.py
docker exec platform-fridadev python tests/unit/chat/test_chat_memory_flow_prepare_context_contracts.py
docker exec platform-fridadev python tests/test_server_chat_compact_observability_contract.py
docker exec platform-fridadev python tests/test_server_chat_synthetic_logs_contract.py
docker exec platform-fridadev python tests/test_server_admin_memory_surface_phase10e.py
docker exec platform-fridadev python tests/test_server_admin_hermeneutics_phase4.py
```

Note: le premier test est nouveau dans ce lot docs+tests. Tant que l'image live n'a pas ete rebuild, il doit etre execute avec le repo monte dans l'image locale; apres rebuild applicatif, la commande `docker exec platform-fridadev python tests/unit/memory/test_hermeneutical_post_stabilization_contract.py` redevient equivalente.

Commandes a garder dans les lots suivants:

```bash
docker exec platform-fridadev python tests/test_memory_store_phase4.py
docker exec platform-fridadev python tests/unit/memory/test_memory_store_blocks_phase8bis.py
docker exec platform-fridadev python tests/test_server_logs_phase3.py
```

## Hors scope

- pas de nouvelle couche `moment_memory`;
- pas de chantier `Frida_from_herself`;
- pas de refonte identity;
- pas de refonte memory_store;
- pas de refonte frontend;
- pas de modification Caddy / Authelia / plateforme;
- pas de lecture `.env`, secrets, DSN complets ou donnees conversationnelles privees.
