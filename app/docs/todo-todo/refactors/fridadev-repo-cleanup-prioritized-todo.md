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
- [ ] Decouper la surface de tests la plus lourde autour de `app/tests/test_server_phase14.py`, `app/tests/test_server_admin_settings_phase5.py`, `app/tests/unit/runtime_settings/test_runtime_settings.py`, `app/tests/unit/logs/test_chat_turn_logger_phase2.py` et `app/tests/unit/chat/test_chat_memory_flow.py`.
- [ ] Extraire des fixtures/helpers partages pour les imports `server`, les monkeypatches runtime et les harness HTTP repetes.
- [ ] Migrer progressivement les `phase*` les plus structurants vers `unit/` et `integration/`, sans casser l'executabilite historique pendant la transition.

Trace de progression:
- [x] Sous-lot 1 livre le `2026-04-21`: extraction de `app/tests/support/server_chat_pipeline.py` pour le bootstrap `server` et le patch baseline `/api/chat`, puis migration de `app/tests/test_server_phase14.py` comme premier consommateur.
- [x] Sous-lot 2 livre le `2026-04-21`: migration de `app/tests/test_server_phase12.py` comme deuxieme consommateur reel, avec une baseline rendue reutilisable via les coutures minimales `build_prompt_messages` / `build_payload` et des valeurs de test moins phase14-centriques.
- [x] Sous-lot 3 livre le `2026-04-21`: clarification de la frontiere entre `server_test_bootstrap.py` et `server_chat_pipeline.py`, puis migration de `app/tests/test_server_phase13.py` comme troisieme consommateur reel du seam chat.
- [x] Sous-lot 4 livre le `2026-04-21`: extension de `server_test_bootstrap.py` au seam voisin des logs admin via `app/tests/test_server_logs_phase3.py` et `app/tests/test_server_logs_phase4.py`, sans ouvrir encore `app/tests/test_server_admin_settings_phase5.py`.
- [x] Sous-lot 5 livre le `2026-04-21`: premiere entree bornee dans `app/tests/test_server_admin_settings_phase5.py` via `server_test_bootstrap.py`, sans embarquer encore `app/tests/unit/runtime_settings/test_runtime_settings.py` ni ouvrir le seam settings/admin en grand.
- [x] Sous-lot 6 livre le `2026-04-21`: premiere decoupe thematique de `app/tests/unit/runtime_settings/test_runtime_settings.py` via l'extraction du bloc `readonly_info` dans `app/tests/unit/runtime_settings/test_runtime_settings_readonly_info.py`, sans toucher encore `runtime_settings.py` ni nettoyer tout le seam runtime settings.
- [x] Sous-lot 7 livre le `2026-04-21`: poursuite de la scission de `app/tests/unit/runtime_settings/test_runtime_settings.py` via l'extraction du bloc `seed bundles / seed plans` dans `app/tests/unit/runtime_settings/test_runtime_settings_seed_bundles_and_plans.py`, sans toucher encore `app/admin/runtime_settings.py` ni nettoyer tout le seam runtime settings.

Ce qu'on ne fait pas encore:
- ne pas ouvrir en meme temps un split large de `app/server.py` ou du frontend chat.

## Phase 2 - Facade HTTP et seam settings/admin

Pourquoi maintenant: `app/server.py` reste le principal point de couplage structurel, et le seam settings/admin est la prochaine surface operateur la plus dense.

Ce qu'on fait:
- [ ] Desepaissir `app/server.py` par groupes de routes/services, en le ramenant vers un vrai role d'entree HTTP et d'orchestration.
- [ ] Nettoyer le seam `app/admin/runtime_settings.py` + `app/web/admin.js` + tests associes (`app/tests/test_server_admin_settings_phase5.py`, `app/tests/unit/runtime_settings/test_runtime_settings.py`).

Ce qu'on ne fait pas encore:
- ne pas transformer cette phase en refonte generale de tout l'admin ni en reouverture des roadmaps admin archivees.

## Phase 3 - Chat runtime et frontend chat

Pourquoi maintenant: une fois la surface de tests et la facade HTTP allegees, le seam chat devient beaucoup plus nettoyable sans multiplier les effets de bord.

Ce qu'on fait:
- [ ] Continuer a sortir les responsabilites de `app/core/chat_service.py` en seams plus explicites.
- [ ] Scinder `app/web/app.js` par blocs de responsabilite (`stream`, `store`, `network`, `render`, `dictation`).
- [ ] Recaler les gros tests de chat autour de seams comportementaux stables, notamment `app/tests/test_server_phase14.py` et `app/tests/integration/chat/test_chat_input_mode_route.py`.

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
