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
| Conventions minimales (`frida.*`, typage progressif, garde-fou) | Documenté + appliqué | Namespace logger canonique `frida.*`; harmonisation typage par tranches utiles; garde-fou anti-dérive | `app/docs/fridadev_conventions.md`, `app/tests/test_logging_conventions_phase8.py`, absence du token legacy logger dans les fichiers trackés (vérification `rg` sur `git ls-files`) | Harmonisation typage volontairement progressive, non “uniformité absolue” |

## 3 bis) Contradictions de contrat (audit §5) — statut de fermeture

| Contradiction signalée dans l’audit | Statut actuel | Preuve vérifiable | Réserve |
| --- | --- | --- | --- |
| Startup (`Dockerfile` vs `run.sh` vs `server.py`/env) | Fermée (corrigée + documentée) | `app/Dockerfile` (`CMD ["python", "server.py"]`), `app/config.py` (`WEB_HOST/WEB_PORT` depuis env), `app/server.py` (`app.run(host=config.WEB_HOST, port=config.WEB_PORT)`), `app/run.sh` (wrapper local explicite), test `test_phase4_transversal.py` | `run.sh` reste non canonique pour le runtime container (décision assumée) |
| `/api/chat` (`history` envoyé frontend mais ignoré backend) | Fermée (corrigée) | `app/web/app.js` (payload chat sans `history`), backend tolérant via `request.get_json(... )` sans dépendance à `history`; test `test_phase4_transversal.py` | Tolérance backend maintenue volontairement (pas de rupture API) |
| `arbiter_decisions.model` (modèle potentiellement re-résolu au save) | Fermée (corrigée) | `app/memory/memory_store.py` (`record_arbiter_decisions(..., effective_model=...)`), `app/memory/arbiter.py` (décisions portant le modèle runtime effectif), test `test_memory_store_phase4.py` (cas “runtime change before insert”) | Aucune observée |
| Migration DB-only vs reliquats JSON `conv_store` | Fermée (requalifiée/documentée) | Runtime principal DB-only (`app/server.py`: bootstrap DB + log `conv_json_bootstrap disabled for db_only_migration`), reliquats JSON confinés au sous-ensemble sync (`app/core/conv_store.py`), inventaire d’usage verrouillé (`test_conv_store_json_sync_inventory_phase6.py`) | Conservation du sous-ensemble sync reste un choix opératoire explicite |
| Flux web search (flag mort et champ de log legacy) | Fermée (corrigée) | `app/tools/web_search.py` (`build_context` en 3-tuple), `app/core/chat_prompt_context.py` (log `web_search` sans champ legacy), test `test_web_search_phase13.py` | Aucune observée |

## 3 ter) Monolithes identifiés (audit §§1,4,8) — statut de réduction/requalification

| Monolithe signalé par l’audit | Statut actuel | Décision de clôture (cette tranche) | Preuve vérifiable | Réserve |
| --- | --- | --- | --- | --- |
| `app/server.py` | Réduit + requalifié | Contrat “routes + composition” atteint et stabilisé | `app/server.py` (~535 lignes), orchestration déplacée vers `app/core/chat_service.py`, `app/core/conversations_service.py`, `app/admin/admin_settings_service.py`, `app/admin/admin_hermeneutics_service.py`; test `test_server_phase14.py` | Module central HTTP conservé par design |
| `app/admin/runtime_settings.py` | Partiellement réduit + requalifié | Requalification acceptée: façade compat + responsabilités majeures externalisées | Extraction vers `app/admin/runtime_settings_spec.py`, `app/admin/runtime_settings_repo.py`, `app/admin/runtime_settings_validation.py`; `runtime_settings.py` reste façade publique (~939 lignes); test `tests/unit/runtime_settings/test_runtime_settings.py` | Taille encore élevée, mais frontières internes explicites |
| `app/web/admin.js` | Réduit + requalifié | Requalification acceptée: point d’entrée orchestrateur après extraction modulaire | `app/web/admin.js` (~1073 lignes, vs 3654 audit), modules `admin_api.js`, `admin_state.js`, `admin_ui_common.js`, `admin_section_*.js`; test `test_minimal_validation_phase9.py` | Point d’entrée encore dense (bootstrap DOM + wiring) |
| `app/memory/memory_store.py` | Réduit + requalifié | Requalification acceptée: façade publique lisible + blocs pipeline extraits | `app/memory/memory_store.py` (~531 lignes, façade avec `__all__` et délégations explicites), modules `memory_store_infra.py`, `memory_traces_summaries.py`, `memory_context_read.py`, `memory_arbiter_audit.py`, `memory_identity_write.py`, `memory_identity_dynamics.py`; tests `test_memory_store_blocks_phase8bis.py` + non-régression `test_memory_store_phase4.py`/`test_chat_memory_flow.py`/`test_server_admin_hermeneutics_phase4.py` | Couplages pipeline mémoire toujours présents, mais frontières de responsabilité désormais explicites |

## 3 quater) Reliquats legacy / code mort (audit §6) — statut de traitement/justification

| Reliquat signalé (audit §6) | Statut actuel | Décision finale | Preuve vérifiable | Réserve |
| --- | --- | --- | --- | --- |
| `needs_summarization()` dans `app/memory/summarizer.py` | Supprimé / traité | Suppression conservée | `app/memory/summarizer.py` (aucune définition), test `test_phase4_transversal.py` | Aucune |
| `const panel = $("#panel")` dans `app/web/app.js` | Supprimé / traité | Suppression conservée | `app/web/app.js` (plus de variable `panel`), test `test_phase4_transversal.py` | Aucune |
| `MAX_CONTEXT_MESSAGES` dans `app/web/app.js` | Supprimé / traité | Suppression conservée | `app/web/app.js` (constante absente), test `test_phase4_transversal.py` | Aucune |
| Payload `history` envoyé/ignoré (`app/web/app.js` + `app/server.py`) | Supprimé / traité | Contrat frontend aligné (sans `history`), backend tolérant | `app/web/app.js` (payload `/api/chat` sans champ `history`), `app/server.py` (`request.get_json(...)` tolérant), test `test_phase4_transversal.py` | Tolérance backend volontaire |
| `build_context(...)->(..., False)` flag mort (`app/tools/web_search.py`) | Supprimé / traité | Signature stabilisée en 3-tuple | `app/tools/web_search.py` (`def build_context(user_msg: str) -> tuple[str, str, int]`), `app/core/chat_prompt_context.py` (unpack 3 valeurs), test `test_web_search_phase13.py` | Aucune |
| Fonctions sync JSON `conv_store` (`sync_catalog_from_json_files`, `sync_messages_from_json_files`, `get_storage_counts`) | Conservé mais justifié | Conservation explicite comme outillage opératoire hors runtime principal | `app/core/conv_store.py` (commentaire “Legacy sync subset kept intentionally…”), test `test_conv_store_json_sync_inventory_phase6.py` | Réévaluation seulement si politique produit change |
| `_load_json_conversation_file` (`app/core/conv_store.py`) | Conservé mais justifié | Conservation limitée au sous-ensemble sync JSON | `app/core/conv_store.py` (appelée depuis les helpers sync), test `test_conv_store_json_sync_inventory_phase6.py` (usage borné) | Aucune |
| `delete_conversation` (purge forte) dans `app/core/conv_store.py` | Conservé mais justifié | Helper technique conservé, non exposé au flux produit standard | `app/core/conversations_service.py` (`DELETE /api/conversations` branche `soft_delete_conversation`), `app/server.py` route delete, test `test_server_phase13.py` | Purge forte non branchée API par défaut; reste outil technique |
| `app/run.sh` à vérifier | Conservé mais justifié | Wrapper opératoire local documenté; runtime container canonique inchangé | `app/run.sh` (commentaire explicite wrapper local), `app/Dockerfile` (`CMD ["python", "server.py"]`), test `test_phase4_transversal.py` | Script non canonique pour runtime container (décision assumée) |

## 3 quinquies) Dépendances inter-couches (audit §§7,9) — statut de diminution / non-aggravation

| Zone inter-couches auditée | Statut actuel | Décision finale | Preuve vérifiable | Réserve |
| --- | --- | --- | --- | --- |
| `server` ↔ `core/admin/memory` | Réduit + clarifié | Le point d’entrée HTTP conserve l’orchestration haute, mais les responsabilités métier sont majoritairement déléguées à des services/modules dédiés | `app/server.py` (délégations vers `chat_service`, `conversations_service`, `admin_settings_service`, `admin_hermeneutics_service`), tests `test_server_phase14.py` et `test_minimal_validation_phase9.py` | Couplage de composition toujours présent (normal pour une couche d’entrée) |
| `web/admin` ↔ APIs admin backend | Réduit + verrouillé | Le contrat front/back est centralisé et explicite (routes, token header, validate endpoints), sans dépendance implicite nouvelle | `app/web/admin_api.js` (`sectionEndpoints`, `sectionValidateEndpoints`, `X-Admin-Token`), `app/server.py` (`_ADMIN_SETTINGS_ROUTE_SECTIONS` + routes settings/validate), `app/web/admin.html` (ordre de scripts), tests `tests/integration/frontend_admin/test_frontend_admin_contract.py`, `test_minimal_validation_phase9.py` | Le frontend reste couplé aux routes REST, mais ce couplage est intentionnel et documenté |
| `runtime_settings` façade ↔ `spec/repo/validation` | Réduit + requalifié | Split interne effectif: règles de schéma, accès DB/seed/backfill et validation runtime sont séparés; la façade publique reste stable | `app/admin/runtime_settings.py` (façade), `app/admin/runtime_settings_spec.py`, `app/admin/runtime_settings_repo.py`, `app/admin/runtime_settings_validation.py`; tests `tests/unit/runtime_settings/test_runtime_settings.py` | La façade reste volumineuse, mais les frontières sont explicites et testées |
| `memory_store` façade ↔ blocs pipeline mémoire ↔ flows chat/admin | Réduit + requalifié | Pas de nouveau couplage transversal problématique créé par les wrappers: le couplage restant est borné au package `memory` et rendu explicite par blocs pipeline-first | `app/memory/memory_store.py` (façade + `__all__`), modules `memory_store_infra.py`, `memory_traces_summaries.py`, `memory_context_read.py`, `memory_arbiter_audit.py`, `memory_identity_write.py`, `memory_identity_dynamics.py`; appels consommateurs dans `core/chat_memory_flow.py` et `admin/admin_hermeneutics_service.py`; tests `tests/unit/memory/test_memory_store_blocks_phase8bis.py`, `tests/unit/chat/test_chat_memory_flow.py` | Le pipeline identité conserve un couplage interne (write path/dynamics) mais sans aggravation inter-couches |
| `conv_store` ↔ reliquats JSON / services | Stable, non aggravé, mieux borné | Runtime principal DB inchangé; sous-ensemble JSON conservé comme outillage explicite hors runtime principal | `app/core/conv_store.py` (subset sync + `_load_json_conversation_file`), `app/core/conversations_service.py` (`soft_delete_conversation`), `app/server.py` (routes via service), test `test_conv_store_json_sync_inventory_phase6.py` | `conv_store` reste un module central et encore couplé à `admin.runtime_settings`/`admin_logs` |

## 3 sexies) Vérification “nouveau god module” (Phase 9)

| Candidat évalué | Qualification retenue | Statut | Preuve vérifiable | Réserve |
| --- | --- | --- | --- | --- |
| `app/server.py` | Orchestrateur central légitime (HTTP composition) | Pas un nouveau god module | ~535 lignes (vs ~1201 audit), délégations explicites vers `chat_service`, `conversations_service`, `admin_settings_service`, `admin_hermeneutics_service`; tests `test_server_phase14.py`, `test_minimal_validation_phase9.py` | Le fichier reste central par design de routeur Flask |
| `app/admin/runtime_settings.py` | Façade de compatibilité dense mais bornée | Pas un nouveau god module | Split effectif vers `runtime_settings_spec.py`, `runtime_settings_repo.py`, `runtime_settings_validation.py`; test `tests/unit/runtime_settings/test_runtime_settings.py` | Façade encore volumineuse (~939 lignes), à surveiller |
| `app/core/conv_store.py` | Module historique dense non aggravé | Pas un nouveau god module créé par le refacto | Module déjà massif dans l’audit; responsabilités DB+catalog/messages+legacy sync inchangées en nature; test `test_minimal_validation_phase9.py` + inventaire `test_conv_store_json_sync_inventory_phase6.py` | Reste un hotspot historique, mais non “nouveau” |
| `app/memory/memory_store.py` | Façade de compatibilité lisible (pipeline-first) | Pas un nouveau god module | ~531 lignes avec `__all__` explicite et délégations vers `memory_store_infra.py`, `memory_traces_summaries.py`, `memory_context_read.py`, `memory_arbiter_audit.py`, `memory_identity_write.py`, `memory_identity_dynamics.py`; test direct `tests/unit/memory/test_memory_store_blocks_phase8bis.py` | Couplage pipeline mémoire encore présent mais borné et visible |
| `app/web/admin.js` | Orchestrateur frontend légitime (wiring) | Pas un nouveau god module | ~1073 lignes (vs ~3654 audit), dépendances vérifiées vers `admin_api.js`, `admin_state.js`, `admin_ui_common.js`, `admin_section_*.js`; test `test_minimal_validation_phase9.py` | Toujours dense côté bootstrap DOM |
| `app/memory/memory_identity_dynamics.py` (candidat additionnel) | Module dense mais borné à un sous-domaine métier unique | Pas un nouveau god module | ~550 lignes, imports limités (`math`, `typing`), API centrée sur conflicts/defer/preview/persist/decay/reactivate; couvert par `tests/unit/memory/test_memory_store_blocks_phase8bis.py` | Taille à surveiller si de nouvelles règles y sont ajoutées |

Verdict de tranche: aucun module introduit pendant le refacto ne cumule de nouvelles responsabilités transversales opaques au point de constituer un nouveau “god module”.

## 3 septies) Convergence vers la cible architecture (audit §9)

| Axe comparé | Cible annoncée (audit §9) | Etat réel du repo | Verdict | Preuve vérifiable | Réserve |
| --- | --- | --- | --- | --- | --- |
| Entrée HTTP et orchestration | `interfaces/http` minces + services applicatifs dédiés | `app/server.py` reste routeur principal mais délègue les flux métier | Cible approchée / requalifiée | `app/server.py` + `app/core/chat_service.py` + `app/core/conversations_service.py` + `app/admin/admin_settings_service.py` + `app/admin/admin_hermeneutics_service.py`; test `test_server_phase14.py` | Pas de `app_factory.py` dédié, routes encore concentrées dans `server.py` |
| Split services métier (`chat`, `conversations`, admin) | Couche `application/` explicite | Services extraits et testés, mais localisés dans `core/` et `admin/` | Cible approchée / requalifiée | `app/core/chat_service.py`, `app/core/conversations_service.py`, `app/admin/admin_settings_service.py`, `app/admin/admin_hermeneutics_service.py`; tests `test_server_phase14.py`, `test_chat_memory_flow.py` | Nommage/rangement encore pragmatique, pas calqué mot a mot sur l’arborescence cible |
| Split `runtime_settings` | Séparation spec/repo/validation/runtime service | Split effectif en 4 modules avec façade de compatibilité stable | Cible approchée / requalifiée | `app/admin/runtime_settings_spec.py`, `app/admin/runtime_settings_repo.py`, `app/admin/runtime_settings_validation.py`, `app/admin/runtime_settings.py`; test `tests/unit/runtime_settings/test_runtime_settings.py` | `runtime_settings.py` reste dense (~939 lignes) |
| Split `memory_store` (Phase 8 bis) | Frontières mémoire explicites (`domain`/`infra`) | Découpage pipeline-first effectif + façade stable | Cible approchée / requalifiée | `app/memory/memory_store.py` + `memory_store_infra.py` + `memory_traces_summaries.py` + `memory_context_read.py` + `memory_arbiter_audit.py` + `memory_identity_write.py` + `memory_identity_dynamics.py`; test `tests/unit/memory/test_memory_store_blocks_phase8bis.py` | Pas de séparation stricte package `domain` vs `infrastructure` |
| Frontend admin modulaire | `interfaces/web/admin`: `state.js`, `api.js`, `forms.js`, `readonly.js` | Modules `admin_api`, `admin_state`, `admin_ui_common`, `admin_section_*`; `admin.js` réduit en orchestrateur | Cible atteinte sur l’intention (modularité) | `app/web/admin.html` (scripts modulaires), `app/web/admin_api.js`, `app/web/admin_state.js`, `app/web/admin_ui_common.js`, `app/web/admin_section_*.js`; tests `test_minimal_validation_phase9.py`, `tests/integration/frontend_admin/test_frontend_admin_contract.py` | Le découpage “forms/readonly” est réalisé via `ui_common` + sections, pas via noms de fichiers identiques au schéma cible |
| Statut `conv_store` | Tendance vers `infrastructure/db` découplée | Module historique encore massif, mais stabilisé (runtime DB, soft-delete API, sync JSON bornée) | Ecart residuel acceptable (non bloquant pour convergence suffisante) | `app/core/conv_store.py`, `app/core/conversations_service.py`, `app/server.py`, test `test_conv_store_json_sync_inventory_phase6.py` | `conv_store.py` reste un hotspot et n’est pas encore scindé en repository dédié |

Verdict convergence cible (cette tranche): les ecarts residuels restants (notamment `conv_store.py` dense, absence d’arborescence `domain/application/interfaces` stricte) sont requalifies et documentes, sans contradiction de contrat ouverte; la convergence vers la cible section 9 est jugee suffisante a ce stade.

## 4) Questions ouvertes de l’audit initial: décision explicite

| Question ouverte (audit §12) | Décision explicite | Statut |
| --- | --- | --- |
| `run.sh` utilisé hors Docker ? | Conservé explicitement comme wrapper opératoire local; non canonique pour le runtime container | Clos (documenté) |
| Fonctions sync JSON `conv_store` à supprimer ? | Conservation explicite comme outillage opératoire (suppression non retenue) | Clos (arbitré) |
| Namespace logger canonique `frida.*` ? | Oui, `frida.*` retenu et verrouillé par test ciblé | Clos (arbitré) |
| Champ `history` frontend chat ? | Retiré du contrat frontend; backend reste tolérant si présent | Clos (corrigé) |
| Exclusion `docs/states/*` par `.gitignore` à long terme ? | Décision explicite actée: `states/` est une zone pérenne versionnée; la whitelist stricte actuelle est transitoire; implémentation matérielle (`.gitignore` + nettoyage `states/`/`todo-*`) différée à une tranche de nettoyage post-Phase 9 | Clos (décision explicite, implémentation différée) |

## 5) Conclusion de tranche
- La preuve croisée est suffisante pour acter que les points majeurs de l’audit sont désormais soit corrigés, soit documentés/arbitrés; la décision sur `.gitignore` / `docs/states` est explicitement prise, avec implémentation volontairement différée à une tranche de nettoyage dédiée.
- Les contradictions de contrat, les reliquats legacy/code mort, les monolithes, les dépendances inter-couches, le contrôle “nouveau god module” et la convergence vers la cible section 9 sont fermés/documentés; la clôture globale reste néanmoins ouverte sur la validation finale explicite du statut “traite” vs “traite partiellement”.
- Une phase dédiée `memory_store.py` est désormais intercalée avant la clôture finale (Phase 8 bis), avec plan pipeline-first documenté dans `app/docs/fridadev_memory_store_refactor_plan.md`.
