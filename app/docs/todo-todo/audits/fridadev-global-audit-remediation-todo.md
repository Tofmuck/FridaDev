# Remediation audit global FridaDev - TODO actif

Statut: TODO actif de correction structurelle
Source: audit global du 2026-05-03
Portee: depot applicatif `FridaDev`, OVH, sans modification plateforme

## Intention

Ce TODO transforme l'audit global du 2026-05-03 en feuille de route de correction.

Le but n'est pas de fermer neuf tickets un par un. Le but est de remettre d'aplomb les structures qui peuvent produire une verite runtime trompeuse: persistance conversationnelle, ecritures derivees, validation settings, observabilite memoire, preuves frontend et source-of-truth documentaire.

Chaque lot doit rester petit, testable et reversible. Une correction peut fermer plusieurs findings si elle remet une structure commune en etat; elle ne doit pas multiplier les sous-lots pour donner une impression d'avancement.

## Source de verite

- [ ] Garder comme source de verite de depart `app/docs/states/audits/fridadev-global-audit-2026-05-03.md`.
- [ ] Relire les details du finding concerne avant chaque lot, puis verifier l'etat courant du code avant de patcher.
- [ ] Ne pas rouvrir les roadmaps archivees dans `app/docs/todo-done/` sauf si le lot documentaire le demande explicitement pour requalifier un finding stale.

## Principe de cloture

- [ ] Aucun finding `AUDIT-20260503-001` a `AUDIT-20260503-009` ne doit rester sans case de traitement dans la matrice finale.
- [ ] Un lot n'est clos que si ses tests/proofs couvrent le comportement reel, pas seulement une lecture de source.
- [ ] Les docs vivantes doivent etre alignees dans le meme cycle quand une correction change un contrat runtime, une attente operateur ou une source-of-truth.
- [ ] Les corrections doivent preserve le contrat OVH: pas de token humain admin, pas de lecture de secret, pas de modification plateforme hors depot.

## Ordre de correction recommande

- [x] Lot 1: securiser la persistance conversationnelle canonique avant toute ecriture derivee.
- [x] Lot 2: rendre la validation settings bloquante cote serveur.
- [ ] Lot 3: rendre les erreurs memoire aval observables sans casser le fail-open produit.
- [ ] Lot 4: ajouter des preuves frontend reelles sur les transitions critiques.
- [ ] Lot 5: clarifier le contrat admin OVH et les knobs obsoletes.
- [ ] Lot 6: fermer les findings stale et remettre les docs source-of-truth a jour.

## Condition de non-prolongation

- [ ] Ne pas creer de sous-lot supplementaire si la structure visee est deja remise d'aplomb, testee et documentee.
- [ ] Ne pas transformer ce TODO en refactor general de `server.py`, `runtime_settings.py`, `app.js` ou `memory_store.py`.
- [ ] Ne pas ajouter une abstraction si un retour de statut explicite, une validation bloquante ou un test de contrat suffit.
- [ ] Apres chaque lot clos, cocher seulement les cases reellement prouvees et ajouter la preuve de commit dans la section du lot.

## Lot 1 - Persistance conversationnelle canonique

Findings couverts: `AUDIT-20260503-001`, `AUDIT-20260503-002`, `AUDIT-20260503-004`

Objectif structurel: `save_conversation()` doit produire une preuve exploitable de sauvegarde canonique. Le flux chat ne doit plus annoncer un succes si les messages ne sont pas effectivement persistés. Les traces memoire, les ecritures identitaires derivees et les terminaux stream ne doivent pas s'appuyer sur une persistance non prouvee.

Fichiers probablement touches:
- `app/core/conversations_store.py`
- `app/core/chat_llm_flow.py`
- `app/server.py`
- `app/core/chat_service.py` si le statut doit traverser l'orchestration
- `app/core/chat_stream_control.py` si le terminal doit exposer un marqueur `persisted`
- `app/web/app.js`
- `app/web/chat_streaming.js`
- tests chat, stream, logs et persistence
- specs `app/docs/states/architecture/fridadev-current-runtime-pipeline.md` et `app/docs/states/specs/streaming-protocol.md` si le contrat terminal evolue

Cases de correction:
- [x] `L1-C1` Definir un resultat explicite de persistance conversationnelle: catalog, messages, timestamp, erreur eventuelle, sans fail-soft silencieux.
- [x] `L1-C2` Faire cesser `persist_response ok` quand l'ecriture messages n'est pas prouvee, avec log distinct pour catalog/messages.
- [x] `L1-C3` Aligner le chemin non-stream sur le stream: sauvegarde canonique verifiee avant `save_new_traces()`, identity staging et reactivation.
- [x] `L1-C4` En stream, ne pas emettre `updated_at` comme preuve terminale si la persistance finale echoue; forcer une rehydratation frontend quand la preuve manque.
- [x] `L1-C5` Documenter le nouveau contrat de persistance/terminal si le payload public change.
- [x] `L1-C6` Rendre la preuve catalog/messages atomique: un echec messages ne laisse pas de catalogue mis a jour pour le tour non sauvegarde.

Tests a ajouter ou modifier:
- test unitaire `conversations_store.save_conversation()` avec echec catalog et echec messages;
- test unitaire prouvant le rollback atomique du catalogue quand l'ecriture messages echoue;
- test `/api/chat` non-stream simulant une sauvegarde messages en echec et verifiant absence de traces/identite derivees;
- test stream simulant l'echec de sauvegarde finale et verifiant terminal sans `updated_at` ou avec statut non persiste explicite;
- test `chat_turn_logger` prouvant `persist_response` en erreur;
- test frontend rehydratation quand terminal sans preuve de persistance.

Preuves runtime attendues:
- selection chat conteneur: `test_server_chat_route_transport_contract.py`, `test_server_chat_web_runtime_contract.py`, `test_server_chat_synthetic_logs_contract.py`, `test_server_chat_compact_observability_contract.py`, `test_server_chat_conversation_id_contract.py`;
- test stream/frontend Node ou browser du terminal sans `updated_at`;
- verification live minimale apres rebuild si le lot touche runtime: conteneur healthy et `/admin` protege par Authelia.

Risques:
- changer la signature de `save_conversation()` peut casser des appels transverses;
- le stream a des chemins `done` et `error` sensibles, avec risque de double terminal;
- il faut eviter d'ecrire des traces ou identites partielles pendant le traitement d'erreur.

Critere de cloture:
- [x] Aucune sauvegarde conversationnelle echouee ne peut produire `persist_response ok`.
- [x] Aucune sauvegarde messages echouee ne peut laisser un catalogue committe pour le meme tour.
- [x] Aucune trace memoire ni ecriture identitaire derivee n'est ecrite avant sauvegarde canonique verifiee.
- [x] Aucun terminal stream ne laisse croire a une persistance prouvee si les messages ne sont pas sauvegardes.
- [x] Les specs runtime/streaming refletent le comportement corrige.

## Lot 2 - Validation bloquante des settings runtime

Findings couverts: `AUDIT-20260503-003`

Objectif structurel: `PATCH /api/admin/settings/<section>` doit appliquer la meme validation semantique que `/validate`, ou une validation serveur equivalente, avant toute ecriture DB/history.

Fichiers probablement touches:
- `app/admin/admin_settings_service.py`
- `app/admin/runtime_settings.py`
- `app/admin/runtime_settings_validation.py`
- `app/admin/runtime_settings_write_path.py`
- `app/web/admin_api.js`
- `app/web/admin_section_*.js` si le format d'erreur serveur change
- tests settings read/patch/validate

Cases de correction:
- [x] `L2-C1` Inserer une validation serveur bloquante dans le chemin PATCH avant `update_runtime_section()`.
- [x] `L2-C2` Garantir qu'un PATCH invalide ne modifie ni `runtime_settings`, ni `runtime_settings_history`, ni cache.
- [x] `L2-C3` Normaliser la reponse d'erreur pour que le frontend conserve ses messages de validation sans diverger du backend.
- [x] `L2-C4` Ajouter des tests PATCH directs pour valeurs hors bornes sur `main_model`, `stimmung_agent_model`, `validation_agent_model`, `embedding`, `database`, `services` et `resources`, plus une preuve write-path pour `identity_governance` qui n'est pas expose par `/api/admin/settings/<section>`.

Tests a ajouter ou modifier:
- `tests/test_server_admin_settings_patch_contract.py`: refus `top_p=2`, `temperature=3`, `model=""`, timeout non positif, `validation_agent_model.max_tokens` au-dessus du cap;
- test DB/history ou mock write path prouvant absence d'ecriture apres validation invalide;
- tests frontend admin si le format des erreurs change.

Preuves runtime attendues:
- tests settings conteneur: read, patch, validate;
- probe non-mutateur ou test isole confirmant que `normalize_admin_patch_payload()` seul n'est plus la source de verite semantique;
- pas de PATCH live invalide sur la configuration OVH de production.

Risques:
- les validations qui resolvent des secrets peuvent refuser un PATCH partiel si le secret runtime est absent;
- une validation trop large peut bloquer des sections non exposees par `/admin` mais actives cote identity/hermeneutics.

Critere de cloture:
- [x] Un client API direct ne peut plus enregistrer un etat runtime invalide.
- [x] `/validate` et `PATCH` partagent les memes invariants semantiques ou documentent explicitement leur difference.
- [x] Le frontend admin reste compatible avec les erreurs backend.

## Lot 3 - Observabilite memoire et erreurs aval

Findings couverts: `AUDIT-20260503-005`

Objectif structurel: une erreur technique de retrieval memoire ne doit plus etre indistincte d'une absence normale de donnee. Le produit peut rester fail-open, mais l'observabilite doit dire la verite.

Fichiers probablement touches:
- `app/memory/memory_traces_summaries.py`
- `app/core/chat_memory_flow.py`
- `app/memory/memory_store.py` si l'API publique de retrieval doit porter un statut
- `app/admin/admin_memory_service.py`
- `app/admin/admin_memory_*_dashboard.py`
- `app/observability/chat_turn_logger.py`
- tests memoire, chat memory flow, Memory Admin et logs

Cases de correction:
- [ ] `L3-C1` Remplacer le retour `[]` indistinct par un resultat structure `ok|empty|error`, ou par une enveloppe equivalente.
- [ ] `L3-C2` Propager `retrieve_error` jusqu'a `memory_arbitration`, `prompt_prepared` et aux logs synthetiques.
- [ ] `L3-C3` Garder le fail-open produit uniquement si l'erreur est explicitement observable par `/log` et `/memory-admin`.
- [ ] `L3-C4` Ajouter une lecture admin qui distingue absence normale, embeddings indisponibles et erreur DB/retrieval.

Tests a ajouter ou modifier:
- test `prepare_memory_context()` avec retrieval en erreur;
- test `memory_arbitration.reason_code == "retrieve_error"`;
- test Memory Admin/logs qui differencie `no_data` et `retrieve_error`;
- test de non-regression: absence normale de memoire reste `no_data`.

Preuves runtime attendues:
- tests memoire unitaires et integration chat concernes;
- tests logs et Memory Admin;
- pas de simulation qui masque l'erreur en vidant simplement les fixtures.

Risques:
- changer l'API retrieval peut toucher plusieurs consommateurs historiques;
- trop exposer l'erreur peut polluer le prompt ou l'UX si le statut est mal place;
- il faut ne pas inclure de secrets ou DSN dans les details d'erreur.

Critere de cloture:
- [ ] Une erreur retrieval est visible comme erreur technique dans les logs/surfaces admin.
- [ ] Une absence normale de memoire reste distincte.
- [ ] La reponse utilisateur peut continuer si le choix produit est fail-open, mais le diagnostic operateur ne ment plus.

## Lot 4 - Preuves frontend reelles

Findings couverts: `AUDIT-20260503-006`

Objectif structurel: les transitions critiques du chat et de l'admin doivent etre prouvees par un harness navigateur minimal, pas seulement par assertions de source.

Fichiers probablement touches:
- `app/tests/integration/frontend_chat/test_frontend_chat_contract.py`
- `app/tests/integration/frontend_admin/test_frontend_admin_contract.py`
- nouveau dossier ou module de support browser sous `app/tests/integration/frontend_*` si necessaire
- `package.json` ou configuration Node seulement si le repo adopte un harness JS
- `app/web/app.js`, `app/web/chat_streaming.js`, `app/web/chat_threads_sidebar.js` seulement si les tests exposent une vraie regression

Cases de correction:
- [ ] `L4-C1` Choisir un harness navigateur minimal compatible OVH et documenter comment l'executer.
- [ ] `L4-C2` Couvrir chat stream nominal: terminal `done`, rendu bulle, cache thread, timestamp et refresh.
- [ ] `L4-C3` Couvrir chat stream erreur: terminal `error`, absence ou presence controlee de `updated_at`, interruption visible, rehydratation attendue.
- [ ] `L4-C4` Couvrir admin settings validate/save: validation refusee, PATCH refuse, affichage des checks et statuts.
- [ ] `L4-C5` Couvrir logs/filter/export par preuve navigateur; si le repo ou l'environnement OVH ne le permet pas raisonnablement, ajouter dans le lot une justification ecrite et une preuve alternative maintenable.
- [ ] `L4-C6` Requalifier les tests source-only comme gardes structurelles, sans les presenter seuls comme integration UX.

Tests a ajouter ou modifier:
- smoke browser chat avec `fetch` mocke ou serveur test;
- smoke browser admin settings validate/save;
- smoke browser logs filter/export, ou preuve alternative maintenable documentee si le harness navigateur ne peut pas couvrir ce parcours;
- conserver les tests Node purs du parser/state machine/sidebar.

Preuves runtime attendues:
- execution locale OVH du harness navigateur ou justification claire si le navigateur n'est pas disponible;
- tests Node existants toujours OK;
- pas de dependance a Authelia pour le harness si la preuve peut rester sur fichiers statiques + mocks.

Risques:
- installation navigateur peut etre lourde sur OVH;
- les mocks fetch doivent rester proches du protocole public, sinon le test devient decoratif;
- ne pas transformer ce lot en refonte UI.

Critere de cloture:
- [ ] Au moins les parcours chat stream nominal, chat stream erreur, admin validate/save sont prouves en environnement navigateur.
- [ ] Logs/filter/export est couvert par une preuve navigateur, ou par une justification ecrite avec preuve alternative maintenable.
- [ ] Les tests source-only sont conserves comme filets structurels, mais la documentation de test ne les surestime plus.
- [ ] Le harness est assez petit pour etre maintenu.

## Lot 5 - Contrat admin OVH et knobs obsoletes

Findings couverts: `AUDIT-20260503-007`

Objectif structurel: le contrat admin OVH doit rester proxy-first Authelia/Caddy + `Remote-User`, sans retour implicite a un token humain applicatif.

Fichiers probablement touches:
- `app/config.py`
- `app/config.example.py`
- `app/server.py` uniquement pour tests/garanties si necessaire
- `AGENTS.md`
- `README.md`
- `app/docs/README.md`
- `app/docs/states/operations/admin-operations.md`
- `app/docs/todo-done/migrations/fridadev-to-frida-system-migration-todo.md` seulement pour annotation historique minimale, sans effacer l'archive
- tests admin guard/config

Cases de correction:
- [ ] `L5-C1` Inventorier les consommateurs reels de `FRIDA_ADMIN_TOKEN`, `FRIDA_ADMIN_LAN_ONLY`, `FRIDA_ADMIN_ALLOWED_CIDRS`.
- [ ] `L5-C2` Supprimer les knobs si aucun consommateur actif ne reste, ou les marquer explicitement obsoletes si une compatibilite transitoire est requise.
- [ ] `L5-C3` Ajouter un test qui interdit la reintroduction de `X-Admin-Token` ou d'un garde humain par token dans `server.py`.
- [ ] `L5-C4` Aligner config exemple, docs operateur et instructions agents sans afficher de secret.

Tests a ajouter ou modifier:
- test source guard: absence de `FRIDA_ADMIN_TOKEN` et `X-Admin-Token` dans le chemin `/api/admin/*`;
- tests admin read/patch existants;
- grep documentaire confirmant que les references restantes sont historiques ou obsoletes.

Preuves runtime attendues:
- `docker ps` healthy apres rebuild si config runtime change;
- `curl -sSI https://fridadev.frida-system.fr/admin` redirige toujours vers Authelia;
- aucune lecture de `.env`, token, DSN ou valeur secrete.

Risques:
- les archives de migration contiennent des decisions historiques avec ancien vocabulaire; il faut les annoter sans les falsifier;
- supprimer trop vite une variable encore consommee par un script local casserait l'onboarding.

Critere de cloture:
- [ ] Le garde admin actif ne peut pas redevenir token humain par accident local.
- [ ] Les knobs obsoletes sont supprimes ou clairement declares obsoletes.
- [ ] Les docs operateur distinguent contrat actif et historique.

## Lot 6 - Findings stale et documentation source-of-truth

Findings couverts: `AUDIT-20260503-008`, `AUDIT-20260503-009`

Objectif structurel: les documents de pilotage doivent refleter l'etat prouve du code. Le finding `record_arbiter_decisions()` doit etre requalifie comme corrige/stale si les tests continuent a le prouver, et la spec runtime settings doit decrire le schema reel.

Fichiers probablement touches:
- `AGENTS.md`
- `README.md`
- `app/docs/README.md`
- `app/docs/todo-done/audits/fridadev_repo_audit.md`
- `app/docs/states/specs/admin-runtime-settings-schema.md`
- `app/docs/states/specs/memory-admin-surface-contract.md` si son rappel devient stale
- `app/docs/todo-done/refactors/fridadev-repo-cleanup-prioritized-todo.md` seulement si une annotation d'archive est indispensable
- tests memory arbiter et settings docs/source si ajoutes

Cases de correction:
- [ ] `L6-C1` Re-verifier le finding `record_arbiter_decisions()` sur l'etat courant avant toute requalification documentaire.
- [ ] `L6-C2` Mettre a jour les docs de pilotage pour dire que le finding substantif est corrige/stale, avec references aux tests qui le prouvent.
- [ ] `L6-C3` Mettre a jour `admin-runtime-settings-schema.md` pour inclure `stimmung_agent_model`, `validation_agent_model`, `identity_governance` et les sections actives.
- [ ] `L6-C4` Indexer proprement `states/audits/` et `todo-todo/audits/` dans les docs mainteneur.
- [ ] `L6-C5` Ajouter une garde doc/source legere si elle evite que la spec settings diverge a nouveau du `SECTION_NAMES`.

Tests a ajouter ou modifier:
- relancer `tests/test_memory_store_phase4.py`;
- relancer `tests/unit/memory/test_memory_store_blocks_phase8bis.py`;
- tests settings read/validate;
- eventuel test doc/source comparant la liste publique des sections settings a la spec.

Preuves runtime attendues:
- pas de rebuild runtime si le lot est docs-only;
- si un test source est ajoute, execution dans le conteneur ou justification de l'environnement Python disponible;
- `git diff --check` et relire les diffs docs touches.

Risques:
- requalifier une archive trop agressivement peut effacer l'histoire du chantier;
- la spec settings doit distinguer sections visibles dans `/admin` et sections pilotees via `/identity` ou `/hermeneutic-admin`.

Critere de cloture:
- [ ] Aucun document de pilotage actif ne presente le finding arbiter stale comme correction runtime encore ouverte.
- [ ] La spec settings decrit le schema runtime reel.
- [ ] Les nouveaux dossiers d'audit et de remediation sont trouvables depuis `app/docs/README.md`.

## Matrice de couverture finale

| Finding | Lot/cases de traitement | Statut attendu |
| --- | --- | --- |
| `AUDIT-20260503-001` | `L1-C1`, `L1-C2`, `L1-C6` | persistance conversationnelle verifiable, atomique et logs non mensongers |
| `AUDIT-20260503-002` | `L1-C1`, `L1-C3` | traces/identite derivees apres sauvegarde canonique |
| `AUDIT-20260503-003` | `L2-C1`, `L2-C2`, `L2-C3`, `L2-C4` | PATCH settings invalide refuse avant ecriture |
| `AUDIT-20260503-004` | `L1-C1`, `L1-C4`, `L4-C3` | terminal stream non trompeur et rehydratation prouvee |
| `AUDIT-20260503-005` | `L3-C1`, `L3-C2`, `L3-C3`, `L3-C4` | erreur retrieval distinguee de `no_data` |
| `AUDIT-20260503-006` | `L4-C1`, `L4-C2`, `L4-C3`, `L4-C4`, `L4-C5`, `L4-C6` | preuves navigateur minimales en place |
| `AUDIT-20260503-007` | `L5-C1`, `L5-C2`, `L5-C3`, `L5-C4` | contrat admin OVH aligne avec config/docs |
| `AUDIT-20260503-008` | `L6-C1`, `L6-C2` | finding arbiter requalifie stale/corrige si toujours prouve |
| `AUDIT-20260503-009` | `L6-C3`, `L6-C5` | spec settings alignee sur schema runtime reel |

- [ ] Relecture finale: aucun finding `AUDIT-20260503-001` a `AUDIT-20260503-009` n'est orphelin.
- [ ] Relecture finale: chaque lot a un critere de cloture testable.
- [ ] Relecture finale: les lots n'introduisent pas de correction hors scope.

## Suivi de cloture

| Lot | Statut | Commit de correction | Notes |
| --- | --- | --- | --- |
| Lot 1 - Persistance conversationnelle canonique | clos | `6df238cd8c7298fda04644d7132bf7ede7d4267f` | Correctif review atomicite ajoute dans le lot `Tighten conversation persistence atomicity`; fermeture prouvee par tests persistence/chat/stream/frontend. |
| Lot 2 - Validation bloquante des settings runtime | clos | `eda1e752758f3c9694c822fa5a4fd47b715d2b51` | Validation PATCH bloquante et garde write-path prouves par tests settings/admin. |
| Lot 3 - Observabilite memoire et erreurs aval | ouvert |  |  |
| Lot 4 - Preuves frontend reelles | ouvert |  |  |
| Lot 5 - Contrat admin OVH et knobs obsoletes | ouvert |  |  |
| Lot 6 - Findings stale et documentation source-of-truth | ouvert |  |  |
