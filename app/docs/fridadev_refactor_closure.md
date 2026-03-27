# FridaDev Refactor Closure (Phase 9 — Tranche 1)

## 1) Scope de cette tranche
- Objectif: produire une preuve de clôture croisée entre `app/docs/fridadev_repo_audit.md` et l’état réel du repo.
- Nature: documentaire uniquement (pas de nouveau refacto structurel).
- Résultat attendu ici: statut explicite des points majeurs de l’audit + décision explicite des questions ouvertes.

## 2) Méthode de vérification
- Sources de référence:
  - `app/docs/fridadev_repo_audit.md`
  - `app/docs/fridadev_refactor_todo.md`
  - `app/docs/fridadev_conventions.md`
- Vérifications repo (lecture croisée):
  - contrats startup/chat/arbiter dans `app/Dockerfile`, `app/run.sh`, `app/config.py`, `app/server.py`, `app/web/app.js`, `app/tools/web_search.py`, `app/core/chat_prompt_context.py`, `app/memory/memory_store.py`
  - extraction/modularisation dans `app/core/*`, `app/admin/*`, `app/web/*`, `app/tests/*`
- Tests de preuve exécutés dans cette tranche:
  - `tests/test_phase4_transversal.py`
  - `tests/test_conv_store_json_sync_inventory_phase6.py`
  - `tests/test_logging_conventions_phase8.py`
  - `tests/test_minimal_validation_phase9.py`

## 3) Matrice croisée des points importants de l’audit

| Point important (audit) | Statut | Décision finale | Preuve courte | Réserve |
| --- | --- | --- | --- | --- |
| Contrat startup runtime (`Dockerfile`/`run.sh`/`server.py`/env) | Corrigé + documenté | Entrée canonique runtime container: `python server.py`; `run.sh` conservé comme wrapper opératoire local | `app/Dockerfile`, `app/config.py` (`WEB_HOST/WEB_PORT`), `app/server.py` (`app.run(host=config.WEB_HOST, port=config.WEB_PORT)`), `app/run.sh`; test `test_phase4_transversal.py` | Aucune dans ce périmètre |
| Contrat `/api/chat` sur `history` | Corrigé | `history` retiré du frontend; backend tolérant (ignorant) | `app/web/app.js` (payload sans `history`), `app/server.py` route `/api/chat`; tests `test_phase4_transversal.py`, `test_server_phase12.py` | Aucune observée |
| Provenance du modèle arbitre persisté (`arbiter_decisions.model`) | Corrigé | Persistance du modèle effectivement utilisé (pas de re-résolution tardive) | `app/memory/memory_store.py` (`record_arbiter_decisions(..., effective_model=...)`), `app/memory/arbiter.py`; tests `test_memory_store_phase4.py` (dont cas de changement runtime entre décision et insert) | Aucune observée |
| Duplication bootstrap runtime DB (`conv_store`/`memory_store`/`minimal_validation`) | Corrigé | Implémentation partagée via module dédié | `app/core/runtime_db_bootstrap.py` + appels dans les 3 modules; cases Phase 2 cochées dans TODO | Vérification structurelle déjà faite, pas rerun exhaustive ici |
| Monolithe `runtime_settings.py` | Requalifié (partiellement réduit) | Spécification, repo DB/seed/backfill et validation extraits; façade compat conservée | `app/admin/runtime_settings_spec.py`, `runtime_settings_repo.py`, `runtime_settings_validation.py`, re-exports/tests dans `test_runtime_settings.py` | `runtime_settings.py` reste volumineux (façade + orchestration) |
| Monolithe `server.py` | Requalifié (fortement réduit) | Routes + composition + garde admin; orchestration déplacée en services | `app/server.py` (~535 lignes), `app/core/chat_service.py`, `app/core/conversations_service.py`, `app/admin/admin_settings_service.py`, `app/admin/admin_hermeneutics_service.py`; tests server phases 4/5bis/8/12/13/14 | Des couplages inter-modules persistent (niveau normal de composition) |
| Monolithe `admin.js` | Requalifié (fortement réduit) | Modules `api`, `state`, `ui_common`, sections extraits; contrat DOM/endpoints verrouillé | `app/web/admin_*.js`, `app/web/admin.html`, tests `test_minimal_validation_phase9.py` + `tests/integration/frontend_admin/test_frontend_admin_contract.py` | `admin.js` reste un point d’entrée orchestrateur |
| Reliquats certain/probable (panel, MAX_CONTEXT_MESSAGES, `needs_summarization`, flag web_search) | Corrigé + documenté | Reliquats “certain” supprimés; flag `ticketmaster` supprimé; sync JSON conservée explicitement comme outillage | `app/web/app.js`, `app/memory/summarizer.py`, `app/tools/web_search.py` (`build_context` 3-tuple), `app/core/chat_prompt_context.py`; tests `test_phase4_transversal.py`, `test_web_search_phase13.py` | Sync JSON non supprimée (décision assumée) |
| Statut sync JSON `conv_store` | Documenté / arbitré | Conservation explicite comme outillage opératoire hors runtime principal | `app/core/conv_store.py` (commentaire “Legacy sync subset…”), `app/docs/fridadev_refactor_todo.md` (arbitrage 2026-03-26), test `test_conv_store_json_sync_inventory_phase6.py` | À réévaluer seulement si politique produit change |
| Conventions minimales (`frida.*`, typage progressif, garde-fou) | Documenté + appliqué | Namespace logger canonique `frida.*`; harmonisation typage par tranches utiles; garde-fou anti-dérive | `app/docs/fridadev_conventions.md`, `app/tests/test_logging_conventions_phase8.py`, absence de `kiki` dans fichiers trackés (`rg -n "kiki" $(git ls-files)`) | Harmonisation typage volontairement progressive, non “uniformité absolue” |

## 4) Questions ouvertes de l’audit initial: décision explicite

| Question ouverte (audit §12) | Décision explicite | Statut |
| --- | --- | --- |
| `run.sh` utilisé hors Docker ? | Conservé explicitement comme wrapper opératoire local; non canonique pour le runtime container | Clos (documenté) |
| Fonctions sync JSON `conv_store` à supprimer ? | Conservation explicite comme outillage opératoire (suppression non retenue) | Clos (arbitré) |
| Namespace logger canonique `frida.*` ? | Oui, `frida.*` retenu et verrouillé par test ciblé | Clos (arbitré) |
| Champ `history` frontend chat ? | Retiré du contrat frontend; backend reste tolérant si présent | Clos (corrigé) |
| Exclusion `docs/states/*` par `.gitignore` à long terme ? | Point maintenu en l’état (whitelist stricte actuelle). Décision long terme non tranchée dans cette tranche | Reste ouvert (documenté) |

## 5) Conclusion de tranche
- La preuve croisée est suffisante pour acter que les points majeurs de l’audit sont désormais soit corrigés, soit documentés/arbitrés, avec un reliquat explicitement ouvert (`.gitignore` / `docs/states`).
- La clôture globale du chantier n’est pas encore déclarée dans cette tranche: il reste à traiter les cases Phase 9 de convergence architecturelle complète (contradictions, monolithes, dépendances, “god module”, convergence cible, verdict final).
