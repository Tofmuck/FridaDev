# FridaDev - Suivi d'audit complet du 2026-04-04

Objectif: transformer l'audit Claude Opus 4.6 et sa revalidation SSH en checklist d'execution claire, en separant ce qui a ete bien vu, ce qui a ete vu trop legerement, et ce qui doit etre prouve avant cloture.

Sources de travail retenues:
- [x] audit Claude Opus 4.6 du 2026-04-04
- [x] revalidation SSH sur `/home/tof/docker-stacks/fridadev`
- [x] runtime live `127.0.0.1:8093`
- [x] suite complete `python -m unittest discover -s tests -p "test_*.py"`

## 1. Findings confirmes apres revalidation

- [x] Realigner `app/docs/todo-todo/memory/hermeneutical-add-todo.md` avec le runtime live deja en `mode=enforced_all`, au minimum sur les Steps 2-4 de la Phase 13.
- [x] Decider quoi faire des criteres d'acceptation finaux encore ouverts dans `app/docs/todo-todo/memory/hermeneutical-add-todo.md`: les mesurer a posteriori, les reformuler, ou les deplacer si le rollout reel a deja saute l'etape progressive documentee.
- [x] Corriger la verite temporelle du stream dans `app/core/chat_llm_flow.py`: en chemin stream, `updated_at` ne doit plus etre capture avant la fin effective de la reponse.
- [x] Donner a `app/tools/web_search.py` un caller transport dedie pour la reformulation web, distinct du caller principal `llm`, afin de separer proprement observabilite, tokens et couts provider.
- [x] Extraire les constantes `READ_STATE_*` dans une source de verite unique puis migrer `app/tools/web_search.py`, `app/core/chat_prompt_context.py` et `app/memory/hermeneutics_policy.py` vers cet import commun.
- [x] Remplacer le couplage prive a `llm_module._sanitize_encoding(...)` dans `app/core/chat_llm_flow.py` par une API publique explicite ou un wrapper stable.

## 2. Ce que l'audit Claude a vu trop legerement ou trop globalement

- [x] Requalifier explicitement les `4 failures` restantes du HEAD courant par familles exactes, sans continuer a les presenter comme un seul probleme d'isolation DB:
  - `1` doc/test stale sur le sous-ensemble sync JSON `conv_store`;
  - `1` grep stale sur le token logger legacy limite a des archives/traces historiques;
  - `2` assertions de contrat stales dans `test_phase4_transversal.py`.
- [x] Reclasser l'item `app/tests/unit/logs/test_chat_turn_logger_phase2.py::test_build_identity_block_emits_identities_read_for_static_sources` comme deja ferme sur le HEAD courant par `ea81da4`; plus aucun correctif runtime n'etait requis dans cette tranche.
- [x] Corriger `app/tests/test_conv_store_json_sync_inventory_phase6.py` pour pointer la vraie trace normative encore vivante (`app/docs/todo-done/refactors/fridadev_refactor_closure.md`) au lieu de forcer `app/docs/todo-done/audits/fridadev_repo_audit.md`.
- [x] Corriger `app/tests/test_logging_conventions_phase8.py::test_repo_has_no_legacy_logger_token` en sortant explicitement les archives et traces historiques du grep, sans requalifier a tort ces occurrences documentaires en fuite runtime.
- [x] Mettre a jour `app/tests/test_phase4_transversal.py::test_frontend_chat_payload_contract_no_longer_serializes_history` sur la signature reelle actuelle de `sendToServer(...)` dans `app/web/app.js`.
- [x] Mettre a jour `app/tests/test_phase4_transversal.py::test_run_and_compose_runtime_binding_contract_is_unchanged` sur le wrapper runtime reel `resolve_python_bin()` / `PYTHON_BIN` de `app/run.sh`.
- [x] Rejouer la suite complete `python -m unittest discover -s tests -p "test_*.py"` jusqu'a `0 failure`, puis consigner la preuve de retour au vert.

## 3. Restes d'audit importants a ne pas perdre

- [x] Realigner le comptage stale des fichiers `test_*.py` sur la valeur courante `60` dans `app/docs/states/project/Frida-State-french-03-04-26.md`, `app/docs/states/project/Frida-State-english-03-04-26.md` et `app/docs/todo-done/audits/fridadev_repo_audit.md`.
- [x] Requalifier les reliquats ouverts `Verifier en conditions reelles...` et `Monitorer le surcout tokens + latence...` dans `app/docs/todo-todo/memory/hermeneutical-add-todo.md`: validation du bloc `[Contexte du souvenir]` rattachee aux criteres finaux post-rollout, et surcout global maintenu comme suivi post-stabilisation explicite.
- [x] Qualifier le bruit `admin_log_write_error err=[Errno 13] Permission denied: '/app'` observe pendant `unittest discover`: le bruit venait principalement d'un vrai probleme de chemin/logs hors conteneur, le fallback admin logs restant fixe sur `/app/logs/admin.log.jsonl`; `admin_logs.py` garde maintenant ce chemin quand `/app` est reellement inscriptible, et bascule sinon sur un path repo-local sur pour les tests host-side.
- [x] Qualifier le `ResourceWarning` sur `app/web/hermeneutic-admin.html` observe pendant la suite complete: il venait principalement du test `test_hermeneutic_admin_route_serves_dedicated_static_page` qui consommait une reponse `send_from_directory(...)` sans fermer explicitement le handle; le runtime est reste intact et le test ferme maintenant la reponse proprement.

## 4. Idees alignees avec Frida a arbitrer apres stabilisation

- [ ] Ajouter un indicateur `memory_traces_injected_in_prompt` ou equivalent, distinct de `memory_retrieved` et `memory_arbitrated`, pour voir ce qui arrive vraiment dans le prompt final.
- [ ] Ajouter dans le dashboard hermeneutique une indication `mode depuis` / `derniere bascule` pour rendre le rollout lisible sans replay documentaire manuel.

## 4bis. Travaux documentaires de consolidation

- [x] Produire une note de cloture lisible pour le chantier `lecture web URL explicite / Crawl4AI`, couvrant au minimum: bon contrat `/md`, strategie `fit -> raw if empty` pour URL explicite, budget explicite `25000`, fin de la troncature artificielle sur le cas Mediapart, et statut final honnete du comportement produit, maintenant consolidee dans `app/docs/todo-done/notes/web-reading-truth-todo.md`.
- [ ] Produire une note de cloture lisible pour le mini-lot `dialogique / identite`, couvrant au minimum: reduction de la surclarification sur les gestes evidents, meilleure classification des questions fictionnelles/speculatives, revelation identitaire utilisateur plus operatoire, filtrage de certaines ecritures durables Frida meta/pipeline, et fermeture du reliquat de couture `logs/identity`.
- [ ] Verifier si les docs actives ou archives liees a ces deux chantiers doivent recevoir un lien croise vers leur note de cloture, une mise a jour minimale de coherence, ou une mention d'archivage explicite.

## 5. Condition de cloture de ce TODO

- [ ] Les points confirmes de la section 1 sont traites ou explicitement reclasses.
- [ ] Les points trop legers ou incomplets de la section 2 sont requalifies avec preuves exactes.
- [ ] La suite complete du repo revient a `0 failure` sur le perimetre retenu.
- [ ] Les docs actives et l'etat runtime racontent enfin la meme histoire.
