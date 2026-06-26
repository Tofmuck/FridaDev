# Frida V1 mega-audit - Lot 9 refactors TODO

Statut: actif, docs-only a la creation.

Source readiness:
`app/docs/states/audits/frida-v1-mega-audit-lot9-refactor-readiness-2026-06-26.md`

Source mega-audit:
`app/docs/todo-todo/audits/frida-v1-mega-audit-code-stack-todo.md`

## Intention

Lot 9 ne corrige pas un bug produit immediat. Il transforme la dette
structurelle confirmee par le mega-audit en refactors bornes, precedes de
golden tests. Le but est de reduire le risque de modification future, pas de
faire un grand rangement cosmetique.

## Principes Lot 9

- Aucun refactor sans golden tests prealables nommes.
- Un lot = une responsabilite extraite ou clarifiee.
- Pas de refactor opportuniste de surface voisine.
- Pas de `utils.py` / `helpers.py`.
- Pas de changement plateforme, DB, Caddy, Authelia, provider live ou migration.
- Pas de changement fonctionnel masque comme refactor.
- Si un P1/P2 comportemental apparait, stopper le refactor et ouvrir un lot
  correctif separe.
- Les preuves doivent rester content-free: pas de prompt brut, contenu
  utilisateur, payload de provider, identifiant sensible, secret, URL avec
  query ou log brut.

## Ordre recommande

1. Lot 9.0 - Golden test harness / preuve avant refactor.
2. Lot 9A - `server.py` route families.
3. Lot 9B - `chat_service.py` orchestration boundaries.
4. Lot 9C - `web_search.py` clients/status/context.
5. Lot 9D - Observabilite guard/read-models.
6. Lot 9E - Frontend chat scripts/load-order/panels.
7. Lot 9F - Agenda runtime structure, fake/local only.
8. Lot 9G - Biblio runtime structure, fake/local only.
9. Lot 9H - Memory/Admin structure.
10. Lot 9Z - Stop point, archive and no-infinite-refactor decision.

Ne pas enchainer automatiquement ces lots. Chaque lot doit etre valide,
committe et pousse separement.

## Lot 9.0 - Golden test harness / preuve avant refactor

Objectif:
figer les contrats qui empechent les refactors d'etre cosmetiques ou dangereux.

Fichiers vises:

- `app/tests/support/server_test_bootstrap.py`
- `app/tests/support/server_chat_pipeline.py`
- nouveaux tests sous `app/tests/unit/` ou `app/tests/integration/`
- docs Lot 9 uniquement

Hors scope:

- extraction de code runtime;
- modification des routes ou flows;
- rebuild.

Golden tests prealables:

- route map snapshot Flask content-free, par famille;
- chat turn synthetic fixture, non-stream et stream;
- main payload manifest / continuity capsule fixture;
- observability accepted/refused matrix;
- frontend script load-order smoke;
- JSONL content-free smoke format commun.

Patch attendu:

- ajouter tests/snapshots synthetiques sans contenu utilisateur brut;
- documenter les commandes communes Lot 9;
- ne modifier aucun module runtime hors tests.

Risques:

- snapshot trop rigide qui bloque des changements legitimes;
- snapshot trop vague qui ne protege rien.

Critere de sortie:

- commandes golden communes documentees;
- au moins une fixture content-free partageable par les lots 9A-9E;
- pas de runtime modifie.

Commandes de verification:

```bash
git diff --check
python3 -m py_compile app/server.py app/core/*.py app/observability/*.py app/tools/*.py
docker exec platform-fridadev python -m unittest tests.test_server_chat_route_transport_contract
```

Note d'execution Lot 9.0:

- `docker exec platform-fridadev ...` est OK seulement pour les tests deja
  presents dans l'image courante.
- Les nouveaux tests ajoutes en Lot 9.0 ne sont pas visibles dans
  `platform-fridadev` tant que l'image n'est pas reconstruite.
- Lot 9.0 restant tests/docs-only, ne pas demander de rebuild pour rendre ces
  nouveaux tests visibles.
- Lot 9.0 doit donc valider explicitement une strategie de runner avant de
  compter les nouveaux tests comme preuve: interpreter hote si les dependances
  repo sont presentes, ou conteneur ephemere avec code courant monte, ou autre
  methode prouvee.
- Si un futur lot modifie du runtime Python/JS, le rebuild applicatif redevient
  obligatoire comme decrit dans les commandes communes.

Checklist:

- [ ] Definir la fixture chat synthetic commune.
- [ ] Definir la route map snapshot par familles.
- [ ] Definir la matrice content-free JSONL.
- [ ] Documenter les commandes communes Lot 9.
- [ ] Prouver absence de contenu brut dans les fixtures.

## Lot 9A - `server.py` route families

Objectif:
reduire la gravite route/bootstrap de `app/server.py` sans changer les routes
publiques.

Fichiers vises:

- `app/server.py`
- modules existants `app/admin/`, `app/core/` seulement si extraction ciblee
- tests `app/tests/test_server_*`

Fichiers interdits / hors scope:

- Caddy/Authelia/plateforme;
- changement du guard admin;
- refactor chat_service;
- frontend.

Sous-lots:

### Lot 9A.0 - Golden route map

Golden tests prealables:

- snapshot `url_map` triee: route, methods, endpoint, famille;
- classification attendue: chat, guarded tools, admin logs, admin dashboard,
  workspace folders/files/notes/exports/images, conversations, static pages;
- preuve que `/api/admin/*` reste sous guard admin;
- preuve que `/api/tools/image-generation` reste sous guard outils.

Patch attendu:

- tests seulement.

Critere de sortie:

- route map stable et content-free.

Checklist:

- [ ] Ajouter snapshot route map.
- [ ] Ajouter assertion guard families.
- [ ] Documenter routes hors `/api/admin/*` mais sensibles.

### Lot 9A.1 - Admin logs/dashboard route extraction

Golden tests prealables:

- `tests.test_server_admin_chat_logs_contract`;
- `tests.test_server_admin_dashboard_contract`;
- `/log` projection frontend/backend apres Lot 7.2;
- export Markdown content-free.

Patch attendu:

- deplacer seulement les handlers admin logs/dashboard vers un module
  `app/admin/...` a responsabilite claire, ou une extension locale existante;
- conserver endpoint names si possible;
- aucun changement payload.

Risques:

- casser le guard implicite `before_request`;
- changer les status/error codes.

Critere de sortie:

- route map identique;
- tests admin logs/dashboard verts;
- diff ne touche pas chat/workspace routes.

Checklist:

- [ ] Extraire logs routes uniquement.
- [ ] Extraire dashboard routes uniquement.
- [ ] Verifier route map identique.
- [ ] Verifier content-free export/projection.

### Lot 9A.2 - Workspace artifact routes extraction

Golden tests prealables:

- `tests.test_server_workspace_folders_contract`;
- notes/files/exports/images server contracts;
- frontend panels normal empty/error non regression.

Patch attendu:

- extraire handlers workspace folders/files/notes/exports/generated-images par
  famille, sans toucher services core.

Risques:

- changer le mapping folder/conversation;
- melanger fichiers Documents et Notes;
- casser open/download/delete.

Critere de sortie:

- route map identique;
- tous contrats workspace verts;
- aucune modification Nextcloud/runtime.

Checklist:

- [ ] Extraire folders/files routes.
- [ ] Extraire notes routes.
- [ ] Extraire exports routes.
- [ ] Extraire generated-images routes.
- [ ] Verifier actions open/download/delete.

### Lot 9A.3 - Chat transport route isolation

Golden tests prealables:

- `tests.test_server_chat_route_transport_contract`;
- stream/non-stream fake;
- `chat_turn_log_payload_rejected` absent sur suites cibles;
- status/error codes Lot 6B/6I/6J.1 conserves.

Patch attendu:

- isoler uniquement transport Flask de `/api/chat` et transcription;
- ne pas toucher `chat_service.chat_response()`.

Risques:

- casser streaming terminal frame;
- casser finalization dashboard refresh;
- exposer erreur brute.

Critere de sortie:

- stream/non-stream contract vert;
- pas de changement de payload visible.

Checklist:

- [ ] Isoler `/api/chat`.
- [ ] Isoler `/api/chat/transcribe`.
- [ ] Verifier stream terminal frame.
- [ ] Verifier errors content-free.

## Lot 9B - `chat_service.py` orchestration boundaries

Objectif:
reduire la gravite orchestration sans changer l'ordre produit des lanes,
final locks, manifest ou persistence.

Fichiers vises:

- `app/core/chat_service.py`
- modules `app/core/chat_*` existants si responsabilite claire
- tests chat/server/support

Hors scope:

- provider live;
- prompts;
- Memory/Agenda/Biblio semantics;
- server routes.

Sous-lots:

### Lot 9B.0 - Golden lane-order / final-lock / capsule

Golden tests prealables:

- fixture de tour synthetic avec Web, Documents, Notes, Agenda, Biblio toggles;
- ordre attendu des injections et observations;
- final lock precedence Biblio/Agenda/others;
- `main_payload_manifest_v1` stable et content-free;
- persistence user/assistant/interrupted stable.

Patch attendu:

- tests/snapshots seulement.

Critere de sortie:

- aucun split `chat_service.py` avant ces tests.

Checklist:

- [ ] Fixture lane-order.
- [ ] Fixture final-lock conflict absent/present.
- [ ] Fixture capsule/manifest.
- [ ] Fixture persistence done/error.

### Lot 9B.1 - Document prompt reads boundary

Golden tests prealables:

- active documents prompt whole-or-absent;
- workspace files prompt selection;
- notes mode without selection / with note selected;
- no Markdown injection without selection.

Patch attendu:

- extraire `_active_documents_for_prompt`, `_workspace_files_for_prompt`,
  `_merge_document_prompt_reads` vers module core dedie si tests verts.

Risques:

- changer budget admission documents;
- confondre Notes et Documents.

Checklist:

- [ ] Extraire reads documentaires.
- [ ] Conserver decisions prompt.
- [ ] Verifier observabilite content-free.

### Lot 9B.2 - Agent lane orchestration boundary

Golden tests prealables:

- Adobe/Biblio/Agenda/Notes/Web observability emissions;
- assistant response override/meta Biblio/Agenda;
- toggles off/not_selected/noop.

Patch attendu:

- extraire orchestration de lanes agentiques sans toucher runtimes domaine.

Risques:

- changer no-op agentique en erreur;
- casser final lock.

Checklist:

- [ ] Extraire emission observability lanes.
- [ ] Extraire override/meta resolution.
- [ ] Verifier no-op statuses.

### Lot 9B.3 - Hermeneutic node state boundary

Golden tests prealables:

- read/write node state;
- final node state build;
- Stimmung/primary/validation observability;
- compact observability Lot 6H.

Patch attendu:

- isoler state read/write/build; aucun changement prompts/agents.

Checklist:

- [ ] Extraire state helpers.
- [ ] Verifier observability compact.
- [ ] Verifier aucun prompt ou payload brut.

## Lot 9C - `web_search.py` clients/status/context

Objectif:
separer clients, status mapping, crawl/read, payload/context et observabilite
sans regressions fail-open.

Fichiers vises:

- `app/tools/web_search.py`
- tests `app/tests/unit/web_search/*`
- `app/tests/unit/logs/test_chat_turn_logger_web_search.py`

Hors scope:

- reconfiguration SearXNG/Crawl4AI;
- provider live;
- changement politique Exa/OpenRouter;
- auto-web lexical.

Sous-lots:

### Lot 9C.0 - Golden web matrix

Golden tests prealables:

- explicit URL success/failure/PDF;
- SearXNG no results vs upstream error;
- discovery no results vs upstream error;
- Crawl4AI timeout/error;
- web evidence insufficient;
- query/content redaction.

Checklist:

- [ ] Matrix status/reason codes.
- [ ] Matrix context payload content-free.
- [ ] Matrix log redaction.

### Lot 9C.1 - SearXNG/discovery client boundary

Patch attendu:

- isoler HTTP calls/status normalization from context building.

Risques:

- reintroduire fail-open `[]`;
- perdre timeout explicite.

Critere de sortie:

- timeout explicite conserve;
- error/no_data distinct.

Checklist:

- [ ] Extraire local search client.
- [ ] Extraire discovery client adapter.
- [ ] Verifier timeout/error_class.

### Lot 9C.2 - Crawl4AI/PDF reader boundary

Patch attendu:

- isoler crawl markdown, explicit URL, PDF reader.

Risques:

- exposer URL query;
- changer policy PDF direct.

Checklist:

- [ ] Extraire crawl client.
- [ ] Extraire PDF reader adapter.
- [ ] Verifier URL redaction.

### Lot 9C.3 - Context/evidence payload boundary

Patch attendu:

- isoler build context payload/evidence/status.

Risques:

- changer prompt material;
- casser evidence failure guidance.

Checklist:

- [ ] Extraire context material builder.
- [ ] Extraire evidence summary.
- [ ] Verifier source-first contracts.

## Lot 9D - Observabilite guard/read-models

Objectif:
reduire la croissance du schema guard et du read-model de turn sans relacher
la garde default-deny.

Fichiers vises:

- `app/observability/observability_payload_guard_schema.py`
- `app/observability/turn_pipeline_read_model.py`
- `app/observability/admin_log_projection.py`
- tests `app/tests/unit/logs/*`, dashboard contracts

Hors scope:

- accepter un payload non prouve;
- changer les contrats content-free;
- Lot 7 `/log` UI hors regression.

Sous-lots:

### Lot 9D.0 - Golden guard matrix

Golden tests prealables:

- payload legitime par stage: chat_response, stream, arbiter, memory,
  identity, web, agenda, biblio, stimmung, manifest;
- payload dangereux refuse: prompt/message/content/raw/url query/token-like/
  provider payload/exception brute.

Checklist:

- [ ] Matrix accepted by stage.
- [ ] Matrix rejected dangerous.
- [ ] Token-like safe-code regression.

### Lot 9D.1 - Guard schema decomposition

Patch attendu:

- extraire constantes/sets/schema helpers par domaine si cela reduit la taille;
- garder une seule entree publique de validation.

Risques:

- relacher default-deny par accident;
- creer des allowlists paralleles incoherentes.

Checklist:

- [ ] Extraire safe-code/token-like policy.
- [ ] Extraire manifest rules.
- [ ] Extraire stage-specific allowlists.
- [ ] Verifier matrices.

### Lot 9D.2 - Turn pipeline read-model decomposition

Golden tests prealables:

- snapshot read-model synthetic multi-domain;
- messages_count/summary.status Lot 6H;
- Biblio/Agenda/Web/Documents summaries;
- error summary content-free.

Patch attendu:

- extraire summary builders par domaine;
- conserver `build_turn_pipeline_item()` facade.

Risques:

- modifier la projection admin;
- reintroduire hash/filename/raw values.

Checklist:

- [ ] Extraire Memory/RAG summary.
- [ ] Extraire Web summary.
- [ ] Extraire Documents summary.
- [ ] Extraire Biblio/Agenda summary.
- [ ] Verifier content-free snapshots.

## Lot 9E - Frontend chat scripts/load-order/panels

Objectif:
reduire la fragilite des scripts navigateur non-module sans redesign UI.

Fichiers vises:

- `app/web/chat_threads_sidebar.js`
- `app/web/app.js`
- `app/web/chat_workspace_folders_sidebar.js`
- `app/web/chat_workspace_folder_*`
- tests frontend Node/browser

Hors scope:

- nouveau bundler;
- redesign UI;
- changement backend;
- refactor admin frontend hors logs regression.

Sous-lots:

### Lot 9E.0 - Golden frontend load-order

Golden tests prealables:

- tous les globals attendus presents une seule fois;
- pas de redeclaration top-level type incident Lot 7.3;
- chat init nominal;
- panels Notes/Documents/Exports/Images empty/error.

Checklist:

- [ ] Smoke load-order browser.
- [ ] Test no duplicate global bindings.
- [ ] Panels empty/error matrix.

### Lot 9E.1 - `chat_threads_sidebar.js` separation

Patch attendu:

- separer conversation list, folder selection and artifact panel hooks without
  changing globals publics.

Risques:

- casser drag/drop conversation folder;
- casser chat boot.

Checklist:

- [ ] Extraire conversation list rendering.
- [ ] Extraire folder binding glue.
- [ ] Verifier browser smoke.

### Lot 9E.2 - Workspace folder sidebar/panels

Patch attendu:

- separer renderer folder tree, file rows, exports/images/notes panels.

Risques:

- reintroduire error-as-empty;
- casser actions file upload/delete/open.

Checklist:

- [ ] Extraire file rows.
- [ ] Extraire artifact panel hooks.
- [ ] Verifier error visible.

## Lot 9F - Agenda runtime structure

Objectif:
clarifier le runtime Agenda V1 implemente/cable/activable sans rouvrir la
roadmap Agenda large post-V1.

Fichiers vises:

- `app/agenda/chat_runtime.py`
- `app/agenda/read_execution.py`
- `app/agenda/proposal_execution.py`
- `app/agenda/observability_read_model.py`
- tests Agenda fake/local

Hors scope:

- CalDAV live;
- nouvelles capacites Agenda;
- provider live;
- DB/migration.

Golden tests prealables:

- toggle off/not_configured/error resolution;
- read-only plan with fake client;
- proposal/pending confirmation fake;
- observability admin projection child error precedence;
- no secret/ICS/DAV path.

Sous-lots:

- 9F.0 golden fake Agenda matrix;
- 9F.1 split client resolution from chat turn orchestration;
- 9F.2 split read/proposal execution adapters if needed;
- 9F.3 observability read-model cleanup.

Checklist:

- [ ] Golden fake Agenda matrix.
- [ ] Refactor client resolution only.
- [ ] Refactor execution only.
- [ ] Verify no product expansion.

## Lot 9G - Biblio runtime structure

Objectif:
clarifier Biblio sans rouvrir produit. Le deterministe tient les murs; le
bibliothecaire LLM fait le travail bibliothecaire.

Fichiers vises:

- `app/biblio/librarian_tools.py`
- `app/biblio/librarian_method_runtime.py`
- `app/biblio/chat_runtime.py`
- `app/biblio/passage_extractor.py`
- `app/biblio/answer_object.py`
- tests Biblio fake/local

Hors scope:

- Catalogue live;
- nouveaux outils;
- reinterpretation des 18 cas historiques;
- provider live.

Golden tests prealables:

- GET-only tool registry;
- method/runtime planning fake;
- passage context/search outputs;
- answer object/rendering;
- fallback repaired observability;
- no query/text raw in observability.

Sous-lots:

- 9G.0 golden Biblio method matrix;
- 9G.1 tool registry boundaries;
- 9G.2 planner/method runtime separation;
- 9G.3 passage extraction/search separation;
- 9G.4 answer object/rendering separation.

Checklist:

- [ ] Golden method matrix.
- [ ] Refactor tool registry only.
- [ ] Refactor planner/runtime only.
- [ ] Refactor passage search/extraction only.
- [ ] Verify no Catalogue live.

## Lot 9H - Memory/Admin structure

Objectif:
reduire les gros modules Memory/Admin sans changer la semantique identity,
memory traces, arbiter ou admin settings.

Fichiers vises:

- `app/memory/memory_traces_summaries.py`
- `app/memory/memory_store.py`
- `app/memory/arbiter.py`
- `app/admin/runtime_settings_validation.py`
- `app/admin/runtime_settings_api_view.py`
- `app/admin/admin_identity_read_model_service.py`

Hors scope:

- nouveau contrat identity;
- purge/reset/backfill;
- migrations;
- Lot 6 hashes/observability deja clos.

Golden tests prealables:

- memory traces/summaries fake store;
- arbiter decision provenance;
- identity read-model content-free contracts;
- runtime settings read/validate/patch contracts;
- admin guard unchanged.

Sous-lots:

- 9H.0 golden Memory/Admin matrix;
- 9H.1 memory traces summaries extraction;
- 9H.2 arbiter support boundaries;
- 9H.3 runtime settings validation split;
- 9H.4 identity read-model service split.

Checklist:

- [ ] Golden Memory/Admin matrix.
- [ ] Refactor memory traces only.
- [ ] Refactor settings validation only.
- [ ] Refactor identity read-model only.
- [ ] Verify no semantic identity change.

## Lot 9Z - Stop point / archive decision

Objectif:
empecher le refactor infini.

Critere de sortie:

- chaque lot execute a un commit et un push;
- tous les refactors restants sont classes `post_v1`, `accepted_limit` ou
  `needs_operator_decision`;
- pas de P1/P2 comportemental cree par Lot 9;
- TODO Lot 9 archivee seulement si les lots termines sont prouves et les
  restes explicitement acceptes.

Checklist:

- [ ] Mettre a jour le mega-audit Lot 9.
- [ ] Mettre a jour `app/docs/README.md`.
- [ ] Deplacer cette TODO vers `todo-done/refactors/` seulement apres decision
  explicite.
- [ ] Conserver Lot Z mega-audit separe.

## Commandes communes de verification

Docs-only:

```bash
git status --short --branch
git diff --check
git diff --cached --check
find app -path "*__pycache__*" -o -name "*.pyc"
find app -type f \( -name "utils.py" -o -name "helpers.py" \)
```

Python runtime touche:

```bash
python3 -m py_compile app/server.py app/admin/*.py app/core/*.py app/memory/*.py app/observability/*.py app/tools/*.py app/agenda/*.py app/biblio/*.py
docker exec platform-fridadev python -m unittest <suites_ciblees>
```

Note: `docker exec platform-fridadev` ne prouve que les tests deja embarques
dans l'image courante. Pour des tests nouvellement ajoutes sans rebuild,
valider d'abord un runner hote ou ephemere avec le code courant monte; ne pas
compter une suite absente de l'image comme preuve.

Frontend touche:

```bash
node --test app/tests/unit/frontend_chat/*.js
```

Rebuild seulement si runtime Python/JS modifie:

```bash
cd /opt/platform/fridadev-app
docker compose up -d --build fridadev
docker ps --filter name=platform-fridadev --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
curl --max-time 12 -sSI https://fridadev.frida-system.fr/admin | awk 'BEGIN{IGNORECASE=1} !/^set-/' | sed -n '1,12p'
```
