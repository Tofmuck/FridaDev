# FridaDev Repo Cleanup - TODO priorise

Statut: ouvert  
Classement: `app/docs/todo-todo/refactors/`  
Portee: transformer l'audit de nettoyage valide en feuille de route actionnable, sans relancer un nouvel audit large et sans ouvrir encore les refactors eux-memes.

## Cadre

Ce document ne rejuge pas tout le depot.

Il conserve l'ordre retenu par l'audit de nettoyage valide:
- quick wins d'abord;
- puis gros chantiers ordonnes par dependances et rendement;
- sans refactor big-bang ni patch runtime dans ce document.

## Quick wins

Pourquoi en tete: faible risque, rendement immediat, et reduction du cout de lecture avant les plus gros lots.

- [x] Clarifier `app/tests/README.md` pour l'aligner avec l'environnement OVH courant et retirer les chemins d'interpreteur stale.
- [x] Ajouter un mini-index doc `current-state / doctrine active / archives` depuis `app/docs/README.md` pour reduire le cout de navigation.
- [x] Remplacer les micro-tests de lecture de source `app/tests/test_server_phase4.py` et `app/tests/test_server_phase8.py` par de petits tests de comportement.

## Phase 1 - Surface de tests legacy

Pourquoi maintenant: c'est la dette la plus couteuse en lisibilite et celle qui rencherit tous les autres lots.

Ce qu'on fait:
- [x] Desepaissir les surfaces de tests legacy les plus couteuses jusqu'a ne plus laisser de grab-bag ambigu bloquant la suite, notamment autour des contrats chat issus de l'ancien `app/tests/test_server_phase14.py`, de `app/tests/unit/runtime_settings/test_runtime_settings.py` et de `app/tests/unit/logs/test_chat_turn_logger_phase2.py`.
- [x] Livrer le minimum utile de support partage pour les imports `server`, le bootstrap des seams repetes et les monkeypatches runtime recurrents, sans construire de framework generique de fixtures.
- [x] Requalifier les `phase*` les plus structurants en seams de tests plus stables ou en fichiers a responsabilite reelle, sans pretendre achever ici toute la migration du depot vers `unit/` et `integration/`.

Trace de progression:
- [x] Sous-lot 1 livre le `2026-04-21`: extraction de `app/tests/support/server_chat_pipeline.py` pour le bootstrap `server` et le patch baseline `/api/chat`, puis migration de `app/tests/test_server_phase14.py` comme premier consommateur.
- [x] Sous-lot 2 livre le `2026-04-21`: migration de `app/tests/test_server_phase12.py` comme deuxieme consommateur reel, avec une baseline rendue reutilisable via les coutures minimales `build_prompt_messages` / `build_payload` et des valeurs de test moins phase14-centriques.
- [x] Sous-lot 3 livre le `2026-04-21`: clarification de la frontiere entre `server_test_bootstrap.py` et `server_chat_pipeline.py`, puis migration de `app/tests/test_server_phase13.py` comme troisieme consommateur reel du seam chat.
- [x] Sous-lot 4 livre le `2026-04-21`: extension de `server_test_bootstrap.py` au seam voisin des logs admin via `app/tests/test_server_logs_phase3.py` et `app/tests/test_server_logs_phase4.py`, sans ouvrir encore `app/tests/test_server_admin_settings_phase5.py`.
- [x] Sous-lot 5 livre le `2026-04-21`: premiere entree bornee dans `app/tests/test_server_admin_settings_phase5.py` via `server_test_bootstrap.py`, sans embarquer encore `app/tests/unit/runtime_settings/test_runtime_settings.py` ni ouvrir le seam settings/admin en grand.
- [x] Sous-lot 6 livre le `2026-04-21`: premiere decoupe thematique de `app/tests/unit/runtime_settings/test_runtime_settings.py` via l'extraction du bloc `readonly_info` dans `app/tests/unit/runtime_settings/test_runtime_settings_readonly_info.py`, sans toucher encore `runtime_settings.py` ni nettoyer tout le seam runtime settings.
- [x] Sous-lot 7 livre le `2026-04-21`: poursuite de la scission de `app/tests/unit/runtime_settings/test_runtime_settings.py` via l'extraction du bloc `seed bundles / seed plans` dans `app/tests/unit/runtime_settings/test_runtime_settings_seed_bundles_and_plans.py`, sans toucher encore `app/admin/runtime_settings.py` ni nettoyer tout le seam runtime settings.
- [x] Sous-lot 8 livre le `2026-04-21`: poursuite de la scission de `app/tests/unit/runtime_settings/test_runtime_settings.py` via l'extraction du bloc `validate_runtime_section` dans `app/tests/unit/runtime_settings/test_runtime_settings_validation.py`, avec le test de facade associe, sans toucher encore `app/admin/runtime_settings.py` ni nettoyer tout le seam runtime settings.
- [x] Sous-lot 9 livre le `2026-04-21`: poursuite de la scission de `app/tests/unit/runtime_settings/test_runtime_settings.py` via l'extraction du bloc read-path runtime settings dans `app/tests/unit/runtime_settings/test_runtime_settings_runtime_read_path.py`, avec les tests de description des sources de secret lies, sans toucher encore `app/admin/runtime_settings.py` ni nettoyer tout le seam runtime settings.
- [x] Sous-lot 10 livre le `2026-04-21`: poursuite de la scission de `app/tests/unit/runtime_settings/test_runtime_settings.py` via l'extraction du bloc `normalize_admin_patch_payload` dans `app/tests/unit/runtime_settings/test_runtime_settings_admin_patch_normalization.py`, sans toucher encore `app/admin/runtime_settings.py` ni nettoyer tout le seam runtime settings.
- [x] Sous-lot 11 livre le `2026-04-21`: poursuite de la scission de `app/tests/unit/runtime_settings/test_runtime_settings.py` via l'extraction du bloc `update_runtime_section` dans `app/tests/unit/runtime_settings/test_runtime_settings_update_runtime_section.py`, sans toucher encore `app/admin/runtime_settings.py` ni nettoyer tout le seam runtime settings.
- [x] Sous-lot 12 livre le `2026-04-21`: poursuite de la scission de `app/tests/unit/runtime_settings/test_runtime_settings.py` via l'extraction du bloc `bootstrap_runtime_settings_from_env` dans `app/tests/unit/runtime_settings/test_runtime_settings_bootstrap_from_env.py`, sans toucher encore `app/admin/runtime_settings.py` ni nettoyer tout le seam runtime settings.
- [x] Sous-lot 13 livre le `2026-04-21`: poursuite de la scission de `app/tests/unit/runtime_settings/test_runtime_settings.py` via l'extraction du bloc `backfill_runtime_secrets_from_env` dans `app/tests/unit/runtime_settings/test_runtime_settings_backfill_runtime_secrets_from_env.py`, sans toucher encore `app/admin/runtime_settings.py` ni nettoyer tout le seam runtime settings.
- [x] Sous-lot 14 livre le `2026-04-21`: ouverture de `app/tests/unit/logs/test_chat_turn_logger_phase2.py` par l'extraction du bloc `web_search` dans `app/tests/unit/logs/test_chat_turn_logger_web_search.py`, sans nettoyer encore tout le seam logging.
- [x] Sous-lot 15 livre le `2026-04-21`: poursuite de l'ouverture de `app/tests/unit/logs/test_chat_turn_logger_phase2.py` par l'extraction du seam `identities_read` dans `app/tests/unit/logs/test_chat_turn_logger_identities_read.py`, sans nettoyer encore tout le logging identitaire.
- [x] Sous-lot 16 livre le `2026-04-21`: poursuite de l'ouverture de `app/tests/unit/logs/test_chat_turn_logger_phase2.py` par l'extraction du seam `identity_write` / `persist_identity_entries` dans `app/tests/unit/logs/test_chat_turn_logger_identity_write.py`, sans nettoyer encore tout le logging identitaire ni ouvrir le finding actif `record_arbiter_decisions`.
- [x] Sous-lot 17 livre le `2026-04-21`: poursuite de l'ouverture de `app/tests/unit/logs/test_chat_turn_logger_phase2.py` par l'extraction du seam `embedding` dans `app/tests/unit/logs/test_chat_turn_logger_embeddings.py`, en gardant la preuve compacte `identity_conflict_scan` associee, sans nettoyer encore tout le logging memoire ni ouvrir le finding actif `record_arbiter_decisions`.
- [x] Sous-lot 18 livre le `2026-04-21`: poursuite de l'ouverture de `app/tests/unit/logs/test_chat_turn_logger_phase2.py` par l'extraction du noyau de contrat du logger dans `app/tests/unit/logs/test_chat_turn_logger_core_contract.py`, sans nettoyer encore tout le logging applicatif ni ouvrir le finding actif `record_arbiter_decisions`.
- [x] Sous-lot 19 livre le `2026-04-21`: poursuite de l'ouverture de `app/tests/unit/logs/test_chat_turn_logger_phase2.py` par l'extraction de l'observabilite hermeneutique dans `app/tests/unit/logs/test_chat_turn_logger_hermeneutic_observability.py`, sans nettoyer encore tout le logging applicatif ni ouvrir le finding actif `record_arbiter_decisions`.
- [x] Sous-lot 20 livre le `2026-04-21`: ouverture de `app/tests/unit/chat/test_chat_memory_flow.py` par une premiere decoupe thematique autour de l'observabilite de `prepare_memory_context` dans `app/tests/unit/chat/test_chat_memory_flow_prepare_context_observability.py`, sans nettoyer encore tout le pipeline memoire/chat.
- [x] Sous-lot 21 livre le `2026-04-21`: poursuite de l'ouverture de `app/tests/unit/chat/test_chat_memory_flow.py` par l'extraction du reliquat `prepare_memory_context` dans `app/tests/unit/chat/test_chat_memory_flow_prepare_context_contracts.py`, sans nettoyer encore tout le pipeline memoire/chat.
- [x] Sous-lot 22 livre le `2026-04-21`: poursuite de l'ouverture de `app/tests/unit/chat/test_chat_memory_flow.py` par l'extraction du pipeline d'application de mode identitaire dans `app/tests/unit/chat/test_chat_memory_flow_identity_mode_pipeline.py`, sans nettoyer encore tout le pipeline memoire/chat.
- [x] Sous-lot 23 livre le `2026-04-21`: fermeture du reliquat `record_identity_entries_for_mode` cote tests legacy via l'extraction du catalogue des gardes fines de contenu dans `app/tests/unit/chat/test_chat_memory_flow_identity_content_guards.py`, sans traiter encore le finding actif `record_arbiter_decisions`.
- [x] Sous-lot 24 livre le `2026-04-21`: debut de l'ouverture de `app/tests/test_server_admin_settings_phase5.py` par l'extraction du read-path admin settings et du contrat d'acces GET dans `app/tests/test_server_admin_settings_read_contract.py`, sans ouvrir encore le gros bloc PATCH/validate.
- [x] Sous-lot 25 livre le `2026-04-21`: poursuite de l'ouverture de `app/tests/test_server_admin_settings_phase5.py` par l'extraction du contrat PATCH/write dans `app/tests/test_server_admin_settings_patch_contract.py`, sans ouvrir encore le bloc validate ni les derniers contrats admin legacy.
- [x] Sous-lot 26 livre le `2026-04-21`: poursuite de l'ouverture de `app/tests/test_server_admin_settings_phase5.py` par l'extraction du contrat POST `.../validate` dans `app/tests/test_server_admin_settings_validate_contract.py`, sans ouvrir encore les derniers contrats admin legacy voisins.
- [x] Sous-lot 27 livre le `2026-04-21`: fermeture propre du reliquat legacy de `app/tests/test_server_admin_settings_phase5.py` par requalification thematique dans `app/tests/test_server_admin_non_settings_contracts.py`, sans ouvrir encore `app/tests/test_server_phase14.py`.
- [x] Sous-lot 28 livre le `2026-04-21`: debut de l'ouverture de `app/tests/test_server_phase14.py` par extraction du contrat transport/stream de `/api/chat` dans `app/tests/test_server_chat_route_transport_contract.py`, en gardant hors lot les gros blocs hermeneutiques, web et observabilite.
- [x] Sous-lot 29 livre le `2026-04-21`: poursuite de l'ouverture de `app/tests/test_server_phase14.py` par extraction du seam d'insertion hermeneutique et des inputs canoniques non-web dans `app/tests/test_server_chat_hermeneutic_insertion_contract.py`, sans ouvrir encore le bloc web ni l'observabilite/synthetic logs.
- [x] Sous-lot 30 livre le `2026-04-21`: poursuite de l'ouverture de `app/tests/test_server_phase14.py` par extraction du bloc web runtime dans `app/tests/test_server_chat_web_runtime_contract.py`, sans ouvrir encore l'observabilite / synthetic logs ni le reliquat `invalid raw conversation id`.
- [x] Sous-lot 31 livre le `2026-04-21`: poursuite de l'ouverture de `app/tests/test_server_phase14.py` par extraction du bloc d'observabilite compacte dans `app/tests/test_server_chat_compact_observability_contract.py`, sans ouvrir encore les synthetic logs ni le reliquat `invalid raw conversation id`.
- [x] Sous-lot 32 livre le `2026-04-21`: fermeture propre du reliquat de `app/tests/test_server_phase14.py` par extraction des synthetic logs / validation logs dans `app/tests/test_server_chat_synthetic_logs_contract.py` et requalification du contrat `invalid raw conversation id` dans `app/tests/test_server_chat_conversation_id_contract.py`, ce qui supprime le legacy file au lieu de laisser un shell ambigu.

Point de sortie pratique:
- objectif utile de la phase 1 atteint;
- pas de perfectionnisme de seuil sur les fichiers encore denses si leur responsabilite est deja nette;
- les reliquats encore lourds sont acceptables tant qu'ils ne redeviennent pas des grab-bags ambigus;
- la suite logique est d'ouvrir la phase 2 plutot que de prolonger artificiellement la phase 1.

Ce qu'on ne fait pas encore:
- ne pas ouvrir en meme temps un split large de `app/server.py` ou du frontend chat.

## Phase 2 - Facade HTTP et seam settings/admin

Pourquoi maintenant: `app/server.py` reste le principal point de couplage structurel, et le seam settings/admin est la prochaine surface operateur la plus dense.

Ce qu'on fait:
- [x] Desepaissir `app/server.py` par groupes de routes/services admin coherents, en le ramenant vers un role plus net de composition HTTP et de wiring explicite, sans viser une decomposition exhaustive de toute la surface serveur.
- [x] Assainir le seam settings/admin: extraire les routes HTTP settings, ouvrir `app/admin/runtime_settings.py` par seams backend utiles, stabiliser les contrats read/patch/validate et sortir de `app/web/admin.js` le catalogue UI structurant, sans pretendre a une refonte totale du frontend admin.

Trace de progression:
- [x] Sous-lot 1 livre le `2026-05-03`: ouverture de la phase 2 par extraction du seam HTTP `/api/admin/settings*` hors de `app/server.py` vers `app/admin/admin_settings_routes.py`, en conservant `app/admin/admin_settings_service.py` comme assemblage de reponses et `app/admin/runtime_settings.py` comme facade stable. Ce sous-lot ne pretend pas nettoyer completement `runtime_settings.py` ni `app/web/admin.js`.
- [x] Sous-lot 2 livre le `2026-05-03`: poursuite de la phase 2 par extraction du seam de projection admin/API des runtime settings vers `app/admin/runtime_settings_api_view.py`, avec `app/admin/runtime_settings.py` conserve comme facade publique. Ce sous-lot borne la redaction API, les `secret_sources` et les `readonly_info`; il ne nettoie pas encore la resolution runtime/secret complete ni `app/web/admin.js`.
- [x] Sous-lot 3 livre le `2026-05-03`: poursuite de la phase 2 par extraction du seam runtime/read-path et resolution de secrets vers `app/admin/runtime_settings_runtime_resolution.py`, avec `app/admin/runtime_settings.py` conserve comme facade de compatibilite pour les entrees publiques et hooks de validation. Ce sous-lot ne refond pas encore la normalisation de patch, la persistence/update DB, la validation elle-meme ni `app/web/admin.js`.
- [x] Sous-lot 4 livre le `2026-05-03`: poursuite de la phase 2 par extraction du seam write-path des runtime settings vers `app/admin/runtime_settings_write_path.py`, en gardant `app/admin/runtime_settings.py` comme facade publique pour `normalize_admin_patch_payload(...)` et `update_runtime_section(...)`. Ce sous-lot couvre la coercition admin, la normalisation de patch, l'update DB/history et l'invalidation de cache; il ne refond pas `validate_runtime_section(...)`, le read-path deja extrait ni `app/web/admin.js`.
- [x] Sous-lot 5 livre le `2026-05-03`: poursuite de la phase 2 par extraction du catalogue UI admin settings vers `app/web/admin_settings_catalog.js`, charge explicitement par `app/web/admin.html` avant `app/web/admin.js`. Ce sous-lot sort les sections, field specs et check-field maps de `app/web/admin.js` sans refondre les controllers `admin_section_*`, le bootstrap DOM ni l'orchestration frontend globale.
- [x] Sous-lot 6 livre le `2026-05-03`: poursuite de la phase 2 par extraction du seam HTTP admin identity `/api/admin/identity*` hors de `app/server.py` vers `app/admin/admin_identity_routes.py`, avec `app/server.py` conserve comme point de composition explicite. Ce sous-lot garde les services `admin_identity_*_service.py` comme logique metier, laisse la page `/identity` avec les routes statiques et ne pretend pas traiter hermeneutics, logs, restart, memory ni `record_arbiter_decisions`.
- [x] Sous-lot 7 livre le `2026-05-03`: poursuite de la phase 2 par extraction du seam HTTP admin hermeneutics `/api/admin/hermeneutics*` hors de `app/server.py` vers `app/admin/admin_hermeneutics_routes.py`, en gardant `app/admin/admin_hermeneutics_service.py` comme logique metier. Ce sous-lot laisse `/hermeneutic-admin` avec les routes statiques et ne pretend pas traiter identity, logs, restart, memory ni le finding actif `record_arbiter_decisions`.

Point de sortie pratique:
- objectif utile de la phase 2 atteint;
- `app/server.py`, `app/admin/runtime_settings.py` et `app/web/admin.js` restent imparfaits, mais leurs responsabilites critiques sont mieux bornees et ne justifient plus de garder la phase ouverte;
- pas de mini-lots supplementaires juste pour gagner quelques lignes ou extraire mecaniquement chaque reliquat;
- la suite logique est d'ouvrir la phase 3 plutot que de prolonger artificiellement la phase 2.

Ce qu'on ne fait pas:
- ne pas transformer cette cloture en refonte generale de tout l'admin ni en reouverture des roadmaps admin archivees;
- ne pas traiter ici le finding actif `record_arbiter_decisions`.

## Phase 3 - Chat runtime et frontend chat

Pourquoi maintenant: une fois la surface de tests et la facade HTTP allegees, le seam chat devient beaucoup plus nettoyable sans multiplier les effets de bord.

Ce qu'on fait:
- [ ] Continuer a sortir les responsabilites de `app/core/chat_service.py` en seams plus explicites.
- [ ] Scinder `app/web/app.js` par blocs de responsabilite (`stream`, `store`, `network`, `render`, `dictation`).
- [ ] Recaler les gros tests de chat autour de seams comportementaux stables, notamment les contrats `/api/chat` issus de l'ancien `app/tests/test_server_phase14.py` et `app/tests/integration/chat/test_chat_input_mode_route.py`.

Ce qu'on ne fait pas encore:
- ne pas rouvrir ici les chantiers doctrinaux hermeneutiques ou identity deja archives.

## Phase 4 - Surface admin memory / observabilite

Pourquoi maintenant: cette surface est dense, mais elle devient plus sure a nettoyer une fois les seams tests/server/settings stabilises.

Ce qu'on fait:
- [ ] Separer dans `app/admin/admin_memory_service.py` les lectures durables, les agregats d'observabilite, les mappers de stages et l'assemblage dashboard.
- [ ] Eclater les gros tests associes (`app/tests/test_server_logs_phase3.py`, `app/tests/test_server_admin_memory_surface_phase10e.py`) par familles de contrat.

Ce qu'on ne fait pas encore:
- ne pas transformer ce lot en refonte generale du module logs ni du pipeline memoire.

## Phase 5 - Navigation documentaire

Pourquoi maintenant: la doc est deja structuree, donc le gain principal vient d'une meilleure navigation apres les coutures code/tests les plus couteuses.

Ce qu'on fait:
- [ ] Rendre plus visibles les portes d'entree `current-state`, `doctrine active` et `archives utiles`.
- [ ] Ajouter depuis `app/docs/README.md` des liens courts vers les ancres documentaires les plus utiles pour les mainteneurs.
- [ ] Clarifier les "docs a lire d'abord" pour un chantier transversal de nettoyage.

Ce qu'on ne fait pas encore:
- ne pas relancer un rangement massif ni une fusion de roadmaps archivees.

## Peut attendre

- [ ] Revenir sur `app/minimal_validation.py` seulement apres les phases 1 a 4, pour eviter de disperser le nettoyage.
- [ ] Reevaluer `app/memory/memory_store.py` plus tard si sa facade redevient un frein majeur apres les lots prioritaires.
- [ ] Laisser les docs doctrinales hermeneutiques/identity hors du present chantier tant qu'un lot runtime ne l'exige pas.

## Hors scope de ce document

- aucun patch runtime;
- aucun refactor effectif;
- aucune reouverture des roadmaps archivees comme si elles etaient redevenues actives;
- aucune requalification globale du repo en "tout a refaire".
