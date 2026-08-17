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

## Livraison dialogique technique et validation qualitative differee

Decision produit du 23 juillet 2026:

- le micro-lot autonome `presomption de sens, independance et presence
  silencieuse` est techniquement livre;
- il corrige un P2 comportemental avant que les golden tests ne figent la
  compulsion de reponse, la clarification reflexe ou le ralliement trop rapide;
- il ajoute `presence` uniquement a l'axe final de sortie du
  `validation_agent`, distinct de `suspend`, puis reutilise la voie
  `AssistantResponseOverride` et la frontiere de persistance existantes;
- son correctif de frontiere conserve les derives Memory/Identity du message
  utilisateur et exclut seulement l'assistant marque
  `assistant_turn.status=dialogic_presence`, sans reconnaissance du texte
  visible ni disparition de l'historique;
- il n'ajoute aucun agent, classificateur, heuristique lexicale, route, surface
  produit ou etat persistant;
- son corpus synthetique borne vit dans
  `app/tests/support/dialogic_regime_corpus.json`;
- la sortie exacte `...` apres un depot appelant le silence a ete validee par
  Tof dans le navigateur authentifie;
- la reponse a une question, le desaccord sans ralliement immediat et le
  deplacement apres correction argumentee restent a valider plus tard;
- cette validation qualitative globale reste ouverte. Elle n'est ni reussie,
  ni fermee, ni remplacee par les tests;
- elle ne bloque plus l'execution ou la fermeture technique de 9.0;
- les golden tests 9.0 figent seulement le regime technique `presence`, sa
  meta serveur et sa persistence. Ils ne mesurent ni ne prouvent l'identite,
  la comprehension, l'independance ou la qualite hermeneutique du modele;
- cette decision n'autorise aucun refactor 9A-9H.

Statut:

`LIVRAISON TECHNIQUE FERMEE - VALIDATION QUALITATIVE GLOBALE OUVERTE ET NON BLOQUANTE POUR 9.0`

La fermeture semantique globale reste interdite avant les trois retours
navigateur encore ouverts. La validation deja obtenue sur le depot silencieux
reste une validation partielle, pas une preuve generale.

## Gate de priorite et familles de destination

Apres la decision operateur ci-dessus, le seul lot executable etait
`Lot 9.0 - Golden test harness / preuve avant refactor`. Sa fermeture technique
ne ferme pas la validation dialogique qualitative globale. Les numeros 9A-9H
classent les destinations de la dette; ils ne fixent pas l'ordre d'execution
apres 9.0:

- Lot 9A - `server.py` route families;
- Lot 9B - orchestration chat, echange LLM et frontiere hermeneutique;
- Lot 9C - `web_search.py` clients/status/context/observabilite;
- Lot 9D - observabilite guard/read-models;
- Lot 9E - frontend chat scripts/load-order/panels et validation de ces assets;
- Lot 9F - Agenda runtime structure, fake/local only;
- Lot 9G - Biblio runtime structure, fake/local only;
- Lot 9H - Memory/Admin structure;
- Lot 9Z - stop point, archive and no-infinite-refactor decision.

Apres fermeture de 9.0, choisir un seul premier candidat selon, dans cet
ordre:

1. criticite et blast radius;
2. golden tests effectivement verts;
3. responsabilite extractible nette;
4. reduction mesurable de couplage ou de branches;
5. absence de changement produit.

Ne pas choisir ce candidat avant la preuve 9.0 et ne pas enchainer
automatiquement les lots. Chaque lot doit etre valide, committe et pousse
separement. Si un P1/P2 comportemental apparait, stopper le refactor et ouvrir
un lot correctif autonome.

## Baseline statique absorbee depuis le Lot 10G

Revalidation read-only au HEAD
`04e22eb04e8d4c39c22ca36966e1d430ee3047d8`, le 2026-07-22. Une ligne utile
est une ligne non vide et non commentaire. `ast_nodes` compte tous les noeuds
descendants de la fonction; `structural_nodes` compte les branches, boucles,
`try`, context managers, expressions conditionnelles, comprehensions et
operateurs booleens. Ces mesures sont une photographie, pas des seuils
automatiques.

Modules revalides:

| module | lignes physiques | lignes utiles | appelants directs / wiring courant |
| --- | ---: | ---: | --- |
| `app/tools/web_search.py` | 2680 | 2495 | `server.api_chat` injecte le module dans le tour; `chat_prompt_context` et `chat_turn_runtime_inputs` consomment son payload. |
| `app/server.py` | 1915 | 1628 | dispatcher Flask/WSGI; les routes deleguent notamment au chat et aux read-models admin. |
| `app/minimal_validation.py` | 1728 | 1607 | le runner CLI appelle `_check_ui_assets` via `_run_check`; l'addition est bornee a cette responsabilite UI. |
| `app/observability/dashboard_read_model.py` | 1688 | 1577 | cinq routes dashboard de `server.py`. |
| `app/observability/turn_pipeline_read_model.py` | 1391 | 1274 | `dashboard_analytics_projection.py` et `log_store.py`. |
| `app/observability/dashboard_observable_modules.py` | 1268 | 1155 | analytics, projection et stockage dashboard. |
| `app/core/chat_service.py` | 1275 | 1180 | `server.api_chat` et l'export synthetique du payload principal. |
| `app/biblio/librarian_tools.py` | 1187 | 1059 | registre partage par chat runtime, agent, planificateurs, methodes et objets de reponse Biblio. |
| `app/biblio/librarian_method_runtime.py` | 1176 | 1055 | `librarian_agent_first` appelle `complete_product_method_loop`. |
| `app/core/hermeneutic_node/validation/validation_agent.py` | 1128 | 996 | insertion hermeneutique de `chat_service` et validation des reglages runtime. |

Fonctions revalidees:

| fonction | longueur | ast_nodes | structural_nodes | appelant direct principal |
| --- | ---: | ---: | ---: | --- |
| `minimal_validation._check_ui_assets` | 957 | 3131 | 64 | runner `_run_check(..., "ui_assets", ...)`. |
| `runtime_settings_validation.validate_runtime_section` | 638 | 3626 | 136 | facade settings, write path, services admin settings et governance Identity. |
| `chat_llm_flow.run_llm_exchange` | 565 | 2563 | 74 | `chat_service.chat_response`. |
| `chat_service.chat_response` | 526 | 2147 | 20 | `server.api_chat`. |
| `chat_llm_flow.run_llm_exchange.event_stream` | 328 | 1506 | 62 | construction du resultat stream dans `run_llm_exchange`. |
| `web_search.build_context_payload` | 228 | 2126 | 130 | context prompt, resolution runtime du tour et facade legacy `build_context`. |
| `web_search._emit_web_search_runtime_event` | 273 | 1983 | 105 | `build_context_payload` et `build_context`. |
| `server.api_chat` | 199 | 1072 | 43 | dispatcher Flask de `POST /api/chat`. |

Les frontieres deja extraites restent utilisees: `chat_session_flow`,
`chat_turn_runtime_inputs`, `chat_prompt_context`, `chat_memory_flow` et
`chat_llm_flow` autour de `chat_service`; PDF reader et modules de policy autour
du Web; projection turn, analytics et registre observable autour du dashboard;
registry, agent-first, planners, passage extraction et answer objects autour de
Biblio. La taille seule ne justifie aucun autre lot. Le scan borne des modules
voisins ne revele aucune responsabilite nouvelle hors 9A-9H; les autres gros
modules observes restent couverts par 9D, 9G ou 9H selon leur domaine.

## Matrice hotspots courants vers Lot 9

| hotspot courant | responsabilites observees | destination Lot 9 | golden prerequisite | recouvrement ou absence | condition de sortie future |
| --- | --- | --- | --- | --- | --- |
| `app/tools/web_search.py` | discovery locale/externe, crawl/PDF, plans de requete, materiau de contexte, evidence et emission d'evenements | 9C | 9.0 puis 9C.0; tests Web phase 4, discovery et observabilite | deja nomme; emission detaillee absorbee par 9C.4 | facades publiques stables, clients/contexte/evenements separes et appels inter-responsabilites reduits sans changer status/reason. |
| `app/server.py` | bootstrap Flask, routes, guards, proxies chat logs et delegation aux services/read-models | 9A | 9.0 puis 9A.0; contrats routes server/admin/workspace/chat | deja nomme; aucun nouveau lot | route map et guards identiques; chaque extraction retire une famille de handlers sans logique metier ajoutee. |
| `app/minimal_validation.py` | checks startup/DB/prompts/UI/API et serialization du resultat; le hotspot cible est le check UI | 9E.3 | 9.0 et 9E.0; `test_minimal_validation_phase9.py`, phase 11 et smokes frontend | module additionnel justifie par 1607 lignes utiles; scope limite a `_check_ui_assets` | scan UI separe du runner generique, meme schema de resultat et moins de branches/couplage dans `_check_ui_assets`. |
| `app/observability/dashboard_read_model.py` | fenetres, overview, conversations, turns, inspection traduite et content gate | 9D.3 | 9.0 et 9D.0; dashboard read-model Lot 4 et contrat serveur dashboard | absence de la TODO initiale absorbee par 9D.3 | cinq facades publiques stables; builders/query/content gate separes et projection toujours content-free. |
| `app/observability/turn_pipeline_read_model.py` | syntheses persistence/providers/RAG/hermeneutique/Web/Documents/Biblio/erreurs | 9D.2 | 9.0 et 9D.0; snapshots multi-domaines, statuts agentiques et log store | deja nomme dans 9D.2 | `build_turn_pipeline_item` reste facade; builders de domaine extraits avec moins de branches croisees. |
| `app/observability/dashboard_observable_modules.py` | registre de modules, reducers, resume par domaine et projection publique | 9D.4 | 9.0 et 9D.0; `test_dashboard_observable_modules_lot3.py` et analytics projection | absence de la TODO initiale absorbee par 9D.4 | registre unique conserve; reducers et serialization separes sans deuxieme taxonomie. |
| `app/core/chat_service.py` | resolution session, persistance user, composition lanes/guards, hermeneutique, capsule/manifest et handoff LLM | 9B | 9.0 puis 9B.0; contrats chat/session/lanes/final locks | deja nomme; coordinateur explicite absorbe par 9B.4 | ordre produit inchange et `chat_response` reduit a un coordinateur de frontieres nommees. |
| `app/biblio/librarian_tools.py` | registry GET-only, validation des outils, appels Catalogue, observations et resultats bornes | 9G.1 | 9.0 puis 9G.0; `test_librarian_tools.py` et contrats Biblio | deja nomme dans 9G.1 | registry reste GET-only; validation/dispatch/resultats separes avec surface publique et reason codes inchanges. |
| `app/biblio/librarian_method_runtime.py` | boucle des methodes produit, navigation, extraction canonique et reparations bornees | 9G.2 | 9.0 puis 9G.0; `test_librarian_agent_first.py` et contrat final-lock serveur | deja nomme dans 9G.2 | planner, navigation et execution mecanique ne partagent plus un flow monolithique; aucune methode produit ajoutee. |
| `app/core/hermeneutic_node/validation/validation_agent.py` | validation d'entrees, hard guards, construction messages, appel modele, fallback et observabilite | 9B.6 | 9.0 puis 9B.0; tests unitaires validation, insertion hermeneutique et logs synthetiques | absence explicite absorbee par 9B.6 | contrat `build_validated_output` identique; validation pure, transport et fallback separes avec prompts inchanges. |
| `minimal_validation._check_ui_assets` | inventaire assets, liens HTML, load-order, globals, IDs et marqueurs interdits | 9E.3 | 9.0 et 9E.0; tests minimal validation phase 9/11 et frontend load-order | absence relation 9.0/9E absorbee | meme verdict detaille, mais inventaires/checks separes et reduction constatee du span, des branches et dependances. |
| `runtime_settings_validation.validate_runtime_section` | validation par section, secrets redacted, URLs, ressources, Identity et caps modeles | 9H.3 | 9.0 puis 9H.0; tests runtime settings validation et contrats admin validate/patch | deja nomme dans 9H.3 | facade et details content-free stables; validateurs de sections isoles et branches croisees reduites. |
| `chat_llm_flow.run_llm_exchange` | override, provider sync/stream, normalisation, persistence canonique, rollback et derives post-save | 9B.5 | 9.0 puis 9B.0; `test_chat_llm_flow.py`, stream control et transport route | absence explicite absorbee par 9B.5 | provider/persistence/finalisation deviennent des frontieres testables; stream/non-stream et Lot 10C restent identiques. |
| `chat_service.chat_response` | coordinateur du tour avant handoff LLM: session, user save, lanes, prompt, manifest et final locks | 9B.4 | 9.0 puis 9B.0; fixture lane-order/final-lock/capsule/persistence | aucun sous-lot initial; absorbe par 9B.4 | une orchestration lisible appelle des frontieres existantes; ordre, messages et metas inchanges avec reduction de couplage. |
| `chat_llm_flow.run_llm_exchange.event_stream` | lecture stream, accumulation, terminal, persistence, rollback et finalisation | 9B.5 | 9.0 puis 9B.0; tests stream success/error/persist-failed/post-persist | absent mais inseparable du meme refactor 9B.5 | terminal et `updated_at` contractuels inchanges; lecture provider et finalisation persistante deviennent separables. |
| `web_search.build_context_payload` | choix explicit URL/search, collecte, payload contexte, confidence/evidence et statut | 9C.3 | 9.0 puis 9C.0; tests phase 4, discovery et runtime inputs | deja nomme dans 9C.3 | builder de materiau distinct de la collecte et de l'emission; contrat source-first et fallback inchanges. |
| `web_search._emit_web_search_runtime_event` | derive summaries/counters, evaluation evidence/confidence et emission content-free | 9C.4 | 9.0 puis 9C.0; tests observabilite Web et logger | absence explicite absorbee par 9C.4 | projection d'evenement pure/testable, sans requete ni contenu, avec moins de branches dans l'emetteur. |
| `server.api_chat` | validation transport, proxies, stream decoding/terminal, finalisation du turn et mapping HTTP | 9A.3 | 9.0 puis 9A.0; transport route, input mode et stream fakes | deja nomme dans 9A.3 | endpoint et protocole identiques; transport Flask separe de la finalisation sans toucher `chat_response`. |

Aucune ligne ne reste `UNKNOWN` et chaque hotspot a une destination principale
unique. Les recouvrements secondaires servent uniquement de golden tests; ils
ne dupliquent pas la tache dans une autre famille.

## Lot 9.0 - Golden test harness / preuve avant refactor

Objectif:
figer les contrats qui empechent les refactors d'etre cosmetiques ou dangereux.

Statut:

`FERME LE 23 JUILLET 2026 - TESTS ET DOCUMENTATION UNIQUEMENT`

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

Inventaire livre:

| golden | contrat vivant | preuve voisine reutilisee | gap ferme / support commun | lots proteges |
| --- | --- | --- | --- | --- |
| chat | protocole stream, persistence canonique et axe technique `answer/presence` | `tests.unit.chat.test_chat_llm_flow`, `tests.test_server_chat_route_transport_contract`, corpus dialogique | `tests.support.server_chat_pipeline`: route Flask non-stream/stream, saves user puis assistant, terminal unique; frontiere LLM success/error, override sans provider principal et meta `dialogic_presence` | 9A, 9B |
| route map | routes Flask et guards admin/outils du HEAD | contrats `tests.test_server_*` et `tests.test_server_admin_*` | `tests.support.lot9_route_map_contract`: 122 entrees contractuelles construites par familles, methodes, endpoints et classes de garde; mutants retrait/ajout/methode/famille/garde | 9A |
| manifest/capsule | `main_payload_manifest_v1` et Continuity Capsule V1 | `tests.unit.logs.test_main_payload_manifest`, `tests.unit.continuity.test_runtime_continuity_capsule` | golden borne sur sections, fenetres, cardinalite utile, correspondance capsule/lane et flags raw; aucune copie du prompt ou du contenu capsule | 9B |
| observabilite | writer guard default-deny et projection admin content-free | `tests.unit.logs.test_observability_payload_guard`, `tests.unit.logs.test_observability_residual_redaction_lot5c` | `tests.support.lot9_content_free_harness.OBSERVABILITY_MATRIX`: formes compactes acceptees, contenu/champ inconnu/type invalide/valeur narrative refuses ou rediges | 9C, 9D |
| frontend | scripts globaux classiques et panels existants | `tests.unit.frontend_chat.*`, `tests.integration.frontend_chat.test_frontend_chat_contract` | `tests.support.frontend_load_order_contract`: dependances partielles, unicite, execution sequentielle en VM et globals requis; mutants doublon/inversion | 9E |
| JSONL | preuves et smokes content-free | smokes Biblio/Agenda existants et writer guard | `tests.support.lot9_content_free_harness`: schema test-only `lot9_smoke_v1`, JSON parseable deterministe, codes/counts/IDs bornes, rejet de cle ou sentinel de contenu | 9A-9E |

Runner checkout courant prouve:

- image courante `platform-fridadev-app:local`;
- checkout `app/` monte en lecture seule sous `/workspace/app`;
- conteneur ephemere `--rm`, filesystem read-only, `/tmp` tmpfs dedie,
  `--network none`, aucun volume runtime et aucune variable de secret;
- frontend Node execute dans un namespace reseau vide via
  `unshare --net --map-root-user`;
- aucun rebuild et aucun `docker exec` ne servent de preuve aux nouveaux
  fichiers.

Commandes golden communes:

```bash
docker run --rm --network none --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,noexec \
  --mount type=bind,src=/opt/platform/fridadev/app,dst=/workspace/app,readonly \
  -w /workspace/app -e PYTHONDONTWRITEBYTECODE=1 \
  platform-fridadev-app:local \
  python -m unittest -v tests.unit.golden.test_lot9_golden_harness

docker run --rm --network none --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,noexec \
  --mount type=bind,src=/opt/platform/fridadev/app,dst=/workspace/app,readonly \
  -w /workspace/app -e PYTHONDONTWRITEBYTECODE=1 \
  platform-fridadev-app:local \
  python -m unittest -v \
  tests.test_server_chat_route_transport_contract \
  tests.unit.chat.test_chat_llm_flow \
  tests.unit.chat.test_chat_stream_control \
  tests.unit.chat.test_dialogic_regime_corpus \
  tests.unit.core.test_conversations_store_save_result \
  tests.unit.logs.test_main_payload_manifest \
  tests.unit.continuity.test_runtime_continuity_capsule \
  tests.unit.logs.test_observability_payload_guard \
  tests.unit.logs.test_observability_residual_redaction_lot5c

unshare --net --map-root-user \
  node --test app/tests/unit/frontend_chat/*.js

git diff --check
```

Baseline et non-regression du 23 juillet 2026:

- suite Python voisine principale: `111 tests`, `OK` avant patch;
- frontend Node complet: `121 tests`, `121 pass` avant patch;
- le run voisin route/admin/frontend/minimal-validation comptait `44 tests`:
  les 39 contrats route/admin/frontend etaient verts et cinq erreurs
  preexistantes restaient dans les fixtures historiques
  `test_minimal_validation_phase9.py` / `phase11.py`; elles ne sont pas
  requalifiees ni absorbees par 9.0;
- les formes d'absence/fallback manifest/capsule restent portees par les suites
  voisines existantes; 9.0 ne les duplique pas.

Preuves de fermeture:

- golden Python 9.0: `7 tests`, `OK`;
- suite Python voisine principale rejouee: `111 tests`, `OK`;
- frontend Node complet avec les deux nouveaux goldens: `123 tests`,
  `123 pass`;
- les deux fixtures JSON synthetiques du support sont parsees;
- le run historique de `44 tests` conserve exactement ses cinq erreurs
  preexistantes et `39` tests passants.

Checklist:

- [x] Definir la fixture chat synthetic commune.
- [x] Definir la route map snapshot par familles.
- [x] Definir la matrice content-free JSONL.
- [x] Documenter les commandes communes Lot 9.
- [x] Prouver absence de contenu brut dans les fixtures.

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

Statut:

`FERME LE 23 JUILLET 2026 - PREUVES ABSORBEES DU LOT 9.0`

Cette fermeture reutilise sans les dupliquer les preuves livrees par le commit
Lot 9.0 `54f661193f410b3ef9ac65a82c2864a3dda41d2d`:

- `EXPECTED_ROUTE_CONTRACTS` decrit exactement les `122` routes Flask non
  statiques du HEAD avec chemin, methodes, endpoint, famille et classe de
  garde;
- les mutants retrait, ajout, methode, famille et garde sont rejetes;
- une source synthetique distante est refusee avec `403` sous
  `/api/admin/*` et sur `/api/tools/image-generation`;
- `/api/tools/image-generation` est l'unique route sensible hors
  `/api/admin/*` actuellement declaree dans `_GUARDED_TOOLS_PATHS`.

Aucun second lot de tests n'est ajoute et aucun travail 9A.1 n'est commence.

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

- [x] Ajouter snapshot route map.
- [x] Ajouter assertion guard families.
- [x] Documenter routes hors `/api/admin/*` mais sensibles.

### Lot 9A.1 - Admin logs/dashboard route extraction

Statut:

`FERME LE 23 JUILLET 2026 - EXTRACTION DE TRANSPORT A CONTRAT CONSTANT`

Le module `app/admin/admin_logs_dashboard_routes.py` enregistre et sert les
douze routes admin logs/dashboard: cinq lectures logs, cinq lectures dashboard,
la suppression bornee des logs chat et l'export Markdown. `app/server.py`
injecte explicitement les six modules existants dans un registre appele une
seule fois; les handlers dereferencent leurs attributs au moment de la requete.
Le guard global `before_request` reste dans `server.py`, sans garde locale ni
route concurrente.

Preuves de fermeture:

- route map triee strictement identique avant/apres: `122` routes et hash
  content-free SHA-256
  `e59cebe6485334027640b166a936fc585b6fa6042afba96179b43ab6d7c21aae`;
- compilation hermetique de `server.py` et du nouveau module: `OK`;
- suites ciblees routes/admin/frontend/golden: `61 tests`, `OK`;
- run hermetique impose des neuf suites: `94 tests`, avec exactement la
  baseline conservee de cinq echecs et une erreur preexistants hors 9A.1,
  sans nouveau cas;
- zero decorateur cible et zero forwarding wrapper dans `server.py`, douze
  registrations et douze endpoint strings explicites dans le nouveau module;
- aucune route chat/workspace, aucun read-model, service, frontend ou guard
  modifie; 9A.2 reste ouvert et non commence.

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

- [x] Extraire logs routes uniquement.
- [x] Extraire dashboard routes uniquement.
- [x] Verifier route map identique.
- [x] Verifier content-free export/projection.

### Lot 9A.2 - Workspace artifact routes extraction

Statut:

`FERME - MICRO-LOTS 9A.2A, 9A.2B, 9A.2C ET 9A.2D FERMES LE 23 JUILLET 2026`

#### Lot 9A.2a - Dossiers, fichiers et OCR

`app/workspace_folder_file_routes.py` enregistre les dix routes de transport
dossiers, fichiers et OCR. `app/server.py` injecte les trois services existants
et trois getters explicites qui resolvent a chaque requete les modules
`workspace_folders`, `workspace_files` et
`workspace_document_nextcloud_runtime`. Le handler global `413` reste dans
`server.py` et continue d'identifier l'endpoint d'upload conserve.

Preuves de fermeture 9A.2a:

- route maps simple et riche strictement identiques avant/apres: `122` routes,
  hash riche content-free
  `e59cebe6485334027640b166a936fc585b6fa6042afba96179b43ab6d7c21aae`;
- comparaison AST des dix handlers identique apres normalisation des seuls noms
  de modules injectes et des bindings getters requis;
- dix registrations, dix endpoint strings uniques, zero handler cible et un
  seul appel de registre dans `server.py`;
- hash structurel du handler global `413` inchange;
- suites Python workspace/multipart/OCR/golden: `31 tests`, `OK`;
- module frontend workspace folders: `18 tests`, `18 pass`;
- contrat navigateur workspace folders en namespace sans reseau, loopback
  local seul: `1 test`, `1 pass`;
- aucune route Notes, exports ou generated-images modifiee; 9A.2b, 9A.2c et
  9A.2d restent ouverts et non commences.

#### Lot 9A.2b - Notes

`app/workspace_folder_note_routes.py` enregistre les six routes Notes.
`app/server.py` injecte le service existant et cinq getters explicites qui
resolvent a chaque requete les modules folders, notes, append, read et runtime
Nextcloud. Les routes statiques `lookup`, `append` et `prepare` conservent leur
ordre et leurs endpoints face a la route dynamique `<note_id>`.

Preuves de fermeture 9A.2b:

- route maps simple et riche strictement identiques avant/apres: `122` routes,
  hash riche content-free
  `e59cebe6485334027640b166a936fc585b6fa6042afba96179b43ab6d7c21aae`;
- comparaison AST des six handlers identique apres normalisation des seuls noms
  injectes, affectations getters et variables locales;
- six registrations, six endpoint strings uniques, zero handler cible et un
  seul appel de registre dans `server.py`;
- suites Python Notes/chat/golden: `34 tests`, `OK`;
- modules frontend panneau Notes et Notes mode: `7 tests`, `7 pass`;
- decouverte elargie `test_server_workspace*.py`: `75 tests`, `OK`;
- aucune route dossiers/fichiers/OCR, exports ou generated-images modifiee;
  9A.2c et 9A.2d restent ouverts et non commences.

#### Lot 9A.2c - Exports

`app/workspace_folder_export_routes.py` enregistre les cinq routes Exports.
`app/server.py` injecte les deux services existants et quatre getters
explicites qui resolvent a chaque requete les modules folders, exports, runtime
Nextcloud et store de conversations. Les routes `download` et `open` restent
deux handlers distincts avec leurs dispositions respectives `attachment` et
`inline`; aucune route `/reuse` n'est exposee.

Preuves de fermeture 9A.2c:

- route maps simple et riche strictement identiques avant/apres: `122` routes,
  hash riche content-free
  `e59cebe6485334027640b166a936fc585b6fa6042afba96179b43ab6d7c21aae`;
- comparaison AST des cinq handlers identique apres normalisation des seuls
  noms de services injectes, affectations getters et variables locales;
- cinq registrations, cinq endpoint strings uniques, zero handler cible et un
  seul appel de registre dans `server.py`;
- contrats serveur Exports, contenu binaire, reuse et golden: `40 tests`,
  `OK`; contrats frontend Exports: `7 tests`, `7 pass`, panneau Exports:
  `9 tests`, `9 pass`, copie/export chat: `4 tests`, `4 pass`;
- decouverte elargie `test_server_workspace*.py`: `75 tests`, `OK`;
- la route interdite `/reuse` reste absente et rejetee sans effet aval;
- aucune route dossiers/fichiers/OCR, Notes ou generated-images modifiee;
  9A.2d reste ouvert et non commence.

#### Lot 9A.2d - Images generees

`app/workspace_folder_generated_image_routes.py` enregistre les six routes
Images generees. `app/server.py` injecte le service liste/creation existant et
quatre getters explicites qui resolvent a chaque requete les modules folders,
read-model Images, runtime Nextcloud et content-service. Le content-service
reste ainsi remplacable integralement par les contrats serveur existants.

Preuves de fermeture 9A.2d:

- route maps simple et riche strictement identiques avant/apres: `122` routes,
  hash riche content-free
  `e59cebe6485334027640b166a936fc585b6fa6042afba96179b43ab6d7c21aae`;
- comparaison AST des six handlers identique apres normalisation des seuls noms
  injectes, affectations getters et variables locales;
- six registrations, six endpoint strings uniques, zero handler cible et un
  seul appel de registre dans `server.py`;
- `download` et `open` conservent leurs dispositions, bytes et headers; delete
  conserve son appel unique remote-first et son retour JSON;
- contrats serveur, services Images et golden: `58 tests`, `OK`; quatre suites
  frontend Images/sidebar: `33 tests`, `33 pass`;
- decouverte elargie `test_server_workspace*.py`: `75 tests`, `OK`;
- decouverte complete differentielle parent/patch: `2533 tests`, `22 echecs`
  et `16 erreurs` historiques, avec les memes `38` identifiants et l'empreinte
  triee `3cba67198a772d52769947237cda5d9e285037e488a1ef5e3c40c6927e940364`;
- aucune route globale `/api/generated-images*` ou `/api/images*`; l'outil V0
  `/api/tools/image-generation` reste separe et inchange;
- aucune route dossiers/fichiers/OCR, Notes ou Exports modifiee; 9A.3 reste
  ouvert et non commence.

Fermeture transversale 9A.2:

- DELETE fichier workspace namespaced inchange;
- Exports open/download namespaced, bytes et headers inchanges;
- Images generees open/download/delete namespaced et inchanges;
- aucune route globale concurrente ni melange Documents, Notes, Exports et
  Images;
- les cinq cases 9A.2 sont fermees par la route map golden, les contrats
  existants et la decouverte workspace `75/75`.

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

- [x] Extraire folders/files routes.
- [x] Extraire notes routes.
- [x] Extraire exports routes.
- [x] Extraire generated-images routes.
- [x] Verifier actions open/download/delete.

### Lot 9A.3 - Chat transport route isolation

Statut:

`FERME LE 24 JUILLET 2026 - MICRO-LOTS 9A.3A ET 9A.3B FERMES`

#### Prerequis tests-only du micro-lot 9A.3b

Statut:

`FERME LE 24 JUILLET 2026 - P3-CEL-LOT9A3-SOURCE-OWNER-TEST-01`

Le test historique de secret runtime imposait par recherche textuelle que
`chat_service.chat_response(...)` reste physiquement dans `app/server.py`.
Le contrat structurel porte desormais sur exactement un appel AST
`.chat_response(...)` parmi les deux seuls proprietaires autorises:
`app/server.py` et, lorsqu'il existe, `app/chat_transport_routes.py`.

Le detecteur ignore commentaires, chaines et acces d'attribut non appeles; il
refuse zero appel, deux appels dans un meme fichier ou une duplication entre
les deux proprietaires. Ses autocontroles synthetiques restent dans le test
existant, sans ajouter de cas a la suite. Les assertions relatives au secret
runtime et aux fallbacks historiques sont conservees. Ce prerequis tests-only
livre par le commit `efa004a06ae94239d39c103df1da81bf7a1bf068`
ne rejoue pas 9A.3b, ne coche aucune case 9A.3 et ne commence pas le Lot 9B.0.

#### Micro-lot 9A.3a - route de transcription

La transcription est extraite separement du handler principal `/api/chat` afin
de ne toucher ni ses proxies, ni sa finalisation, ni sa persistance, ni son
protocole stream. `app/chat_transcription_routes.py` enregistre uniquement
`POST /api/chat/transcribe`; son registre retourne le handler donne a Flask,
que `app/server.py` reexpose sous le meme objet `api_chat_transcribe`.

Le raccord resout `request` tardivement par un getter appele une fois par
requete. Le guard global `RequestEntityTooLarge` reste dans `app/server.py` et
continue de reconnaitre l'endpoint stable `api_chat_transcribe`. Les preuves
hermetiques couvrent les 36 tests cibles, les contrats chat elargis, l'identite
de la route map riche a 122 routes et la comparaison differentielle complete.
Le micro-lot 9A.3b, reserve a la route principale `/api/chat`, est documente
separement ci-dessous.

#### Micro-lot 9A.3b - route principale du chat

`app/chat_transport_routes.py` enregistre uniquement `POST /api/chat` et
retourne le handler donne a Flask; `app/server.py` le reexpose sous le meme
objet `api_chat`. Les quatre proxies, le classificateur et la finalisation
restent dans `server.py`, sans wrapper ni second chemin. `request` est resolu
une fois au debut du handler et la finalisation est resolue tardivement, y
compris dans le `finally` du generateur stream.

Preuves de fermeture 9A.3b:

- route maps simple et riche strictement identiques avant/apres: `122` routes,
  hash riche content-free
  `e59cebe6485334027640b166a936fc585b6fa6042afba96179b43ab6d7c21aae`;
- identite entre le handler Flask et `server.api_chat`, un seul appel AST
  `.chat_response(...)` dans le nouveau proprietaire et zero dans
  `server.py`;
- corps du handler identique apres normalisation des seuls noms injectes,
  du getter de requete et des trois resolutions tardives de finalisation;
  AST des quatre proxies, des deux helpers et des autres fonctions de
  `server.py` inchange;
- gate phase5bis/transport/golden: `20 tests`, `OK`; integration chat:
  `16 tests`, `OK`; unit chat: `127 tests`, `OK`; phase12: `2 tests`, `OK`;
  controles frontend stream: `15 tests`, `15 pass`;
- bundle observabilite critique: `49 tests`, avec exactement les `7 echecs`
  et `1 erreur` historiques, sans nouvel identifiant;
- matrice synthetique avant/apres identique pour les statuts non-stream,
  stream paresseux, UTF-8 multioctet, terminal `done`/`error`, terminal
  absent/duplique, contenu apres terminal, erreur de persistance, headers,
  finalisation tardive et sentinelle interdite;
- decouverte chat: `69 tests`, `14 echecs` et `2 erreurs` historiques;
  decouverte complete differentielle: `2533 tests`, `22 echecs` et
  `16 erreurs`, memes `38` identifiants et empreinte triee
  `3cba67198a772d52769947237cda5d9e285037e488a1ef5e3c40c6927e940364`.

Le Lot 9A est ferme: 9A.0, 9A.1, 9A.2 et 9A.3 sont tous fermes. Le Lot 9B.0
reste entierement ouvert et non commence.

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

- [x] Isoler `/api/chat`.
- [x] Isoler `/api/chat/transcribe`.
- [x] Verifier stream terminal frame.
- [x] Verifier errors content-free.

## Lot 9B - `chat_service.py` orchestration boundaries

Objectif:
reduire la gravite orchestration sans changer l'ordre produit des lanes,
final locks, manifest ou persistence.

Fichiers vises:

- `app/core/chat_service.py`
- `app/core/chat_llm_flow.py`
- `app/core/hermeneutic_node/validation/validation_agent.py`
- modules `app/core/chat_*` existants si responsabilite claire
- tests chat/server/support

Hors scope:

- provider live;
- prompts;
- Memory/Agenda/Biblio semantics;
- server routes.

Sous-lots:

### Prerequis externe P2 avant 9B.0

`P2-CEL-WEB-TURN-PROVENANCE-CONTINUITY-01` reste un prerequis externe au Lot
9B.0. La correction technique persiste une provenance assistant V1
content-free, distingue modele principal et final lock, puis la projette au
tour suivant sans conserver les sources Web ni relancer une recherche.

Statut: ferme. La correction technique a ete auditee independamment le 25
juillet 2026, puis validee en dialogue live par Tof le 14 aout 2026. Le finding
P2 peut etre clos; aucune case 9B n'est cochee par cette correction.

### Prerequis de remise au vert avant 9B.0

La suite complete conserve une dette historique de tests qui empeche une
baseline lisible pour le refactor du coeur du chat. La TODO methodologique
autoritative est:

`app/docs/todo-done/refactors/frida-v1-mega-audit-lot9-refactor-before-9b-todo.md`

Statut: ferme le 16 aout 2026. La TODO autoritative a classe et corrige les
38 en-tetes historiques, explique la variation de `2549` a `2552` tests et
prouve une decouverte complete hermetique a `0` echec, `0` erreur, `0`
skip et `0` expected failure. Les suites critiques et les goldens Lot 9
restent verts. Le gate externe du Lot 9B est donc leve; l'etat courant de
chaque sous-lot est documente dans sa section ci-dessous.

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

- [x] Fixture lane-order.
- [x] Fixture final-lock conflict absent/present.
- [x] Fixture capsule/manifest.
- [x] Fixture persistence done/error.

Preuves livrees le 16 aout 2026:

- `app/tests/support/server_chat_pipeline.py` fournit une fixture transversale
  synthetique qui traverse `chat_service.chat_response` via la vraie route,
  avec transports, services et persistence fakes. Web, Documents, Notes,
  Agenda et Biblio sont activables independamment; aucun provider, secret,
  DB, reseau ou contenu operateur n'est utilise.
- `app/tests/unit/golden/test_lot9_golden_harness.py` ajoute quatre goldens
  semantiques. Ils figent l'ordre observable Web -> Notes -> Documents ->
  Biblio, les decisions Agenda et hermeneutiques, les absences/no-op par
  toggle, et l'unicite des injections sans recopier le corps des lanes.
- La matrice des final locks couvre absence, Biblio, Agenda, conflit
  Agenda/Biblio, presence hermeneutique, Agenda/presence, ainsi que locks
  Biblio/Agenda invalides. La priorite observee reste Agenda > Biblio >
  presence; tout lock valide evite appel modele principal, resolution de
  secret et resolution d'URL, tout en conservant une seule reponse assistant,
  une seule persistence, ses metas et sa provenance content-free.
- La Continuity Capsule reste V1, unique et terminale quand le modele
  principal est appele, et `not_selected` avec le reason code de bypass sous
  final lock. `main_payload_manifest_v1` conserve l'ordre logique Notes,
  Documents, Biblio, Capsule, ses compteurs/status et ses flags raw tous faux.
  Deux reconstructions identiques ne dupliquent aucune source.
- La persistence couvre user/assistant exactement une fois en succes
  non-stream, stream et final lock, terminal `done` unique, erreur provider
  avant resultat, erreur apres fragment stream avec assistant interrompu,
  echec de persistence assistant par resultat negatif sans `updated_at`, sans
  derive, seconde tentative ni doublon durable. Le fallback borne existant
  qui tente de persister un
  marqueur interrompu apres une exception de writer reste couvert par les
  contrats historiques et n'est pas modifie par 9B.0.

Sensibilites controlees rejetees: lane retiree, ajoutee, deplacee ou dupliquee;
priorite Agenda/Biblio inversee; appel provider sous final lock; capsule
absente, dupliquee ou non terminale; manifeste avec champ brut; assistant
sauvegarde deux fois; terminal absent ou double; erreur requalifiee en succes.

Commandes hermetiques executees avec `--network none`, checkout read-only et
`/tmp` en tmpfs:

- baseline avant patch: `python -m unittest discover` -> `2552`, OK;
- golden Lot 9/9B: `python -m unittest tests.unit.golden.test_lot9_golden_harness`
  -> `11`, OK;
- Web/Documents/Notes/Agenda/Biblio voisins -> `32`, OK;
- LLM flow/stream control/transport -> `32`, OK;
- manifest/capsule/observabilite -> `33`, OK;
- provenance persistence/rehydratation -> `16`, OK;
- decouverte complete finale: `python -m unittest discover` -> `2556`, OK.

Les quatre nouveaux tests expliquent seuls le passage de `2552` a `2556`.
Aucun frontend n'a ete rejoue: aucune fixture ni aucun fichier frontend n'est
touche. Aucun split/refactor 9B.1-9B.6, code runtime, prompt, rebuild ou restart
n'a ete execute.

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

- [x] Extraire reads documentaires.
- [x] Conserver decisions prompt.
- [x] Verifier observabilite content-free.

Preuves livrees le 16 aout 2026:

- `app/core/chat_document_prompt_reads.py` porte desormais
  `ActiveDocumentsPromptRead`, `_active_documents_for_prompt`,
  `_workspace_files_for_prompt` et `_merge_document_prompt_reads`.
  `app/core/chat_service.py` les reexporte aux memes noms afin de conserver
  les appels et points de substitution existants; le coordinateur passe de
  `1311` a `1216` lignes.
- Les trois corps de fonction et le dataclass sont AST-identiques avant/apres.
  L'ordre de fusion reste documents actifs puis fichiers workspace; une erreur
  de lecture conserve les documents lisibles et la priorite de reason code
  existante. Aucun budget, ordre d'injection ou decision de lane n'a change.
- Le test de frontiere renforce dans
  `app/tests/unit/core/test_active_document_prompt_lane.py` a d'abord echoue
  uniquement sur l'absence du module dedie, puis passe. Les contrats existants
  prouvent toujours document entier ou absent, selection workspace explicite,
  Notes sans selection/avec note selectionnee et aucune injection Markdown
  sans selection.
- Les suites Documents/workspace/Notes et le golden transversal passent
  `109/109`; capsule, manifest et observabilite passent `52/52`; la decouverte
  complete reste a `2556`, `0` echec et `0` erreur. Aucun test, skip ou
  expected failure n'est ajoute.
- Le contrat d'observabilite vivant attribue les deux readers au nouveau
  module et conserve l'enregistrement des decisions dans `chat_service.py`.
  Les resultats restent bornes a status, documents, reason code et classe;
  aucune projection content-free ne gagne de contenu brut.

Commandes hermetiques executees avec `--network none`, checkout read-only et
`/tmp` en tmpfs:

- baseline avant patch: `python -m unittest discover` -> `2556`, OK;
- RED frontiere documentaire: `tests.unit.core.test_active_document_prompt_lane`
  -> `31`, un echec attendu sur le module absent;
- GREEN frontiere documentaire: meme module -> `31`, OK;
- Documents/workspace/Notes/golden -> `109`, OK;
- capsule/manifest/observabilite -> `52`, OK;
- decouverte complete apres extraction -> `2556`, OK.

Limite: 9B.1 ne deplace ni la lane Notes, ni les decisions d'admission et
d'observabilite documentaires. Les Lots 9B.2 a 9B.6 restent ouverts et non
commences.

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

- [x] Extraire emission observability lanes.
- [x] Extraire override/meta resolution.
- [x] Verifier no-op statuses.

Preuves livrees le 16 aout 2026:

- `app/core/chat_agent_lane_orchestration.py` porte les cinq emissions
  Adobe contexte/prompt, Biblio, Agenda et Notes auparavant definies dans
  `chat_service.py`. Les dix helpers de projection observability et de
  conversion override/meta sont AST-identiques avant/apres; les runtimes de
  domaine et l'observabilite Web restent a leur emplacement.
- `resolve_agent_lane_assistant_output` constitue l'unique frontiere de
  resolution assistant des lanes. Elle conserve l'ordre d'evaluation existant,
  la priorite Agenda > Biblio > presence hermeneutique, le rejet des locks
  invalides ou vides, ainsi que la meta et l'enveloppe Biblio independantes du
  lock finalement selectionne. `chat_service.py` reexporte les anciens noms
  prives pour conserver les points de substitution existants et passe de
  `1216` a `1061` lignes.
- `app/tests/unit/core/test_chat_agent_lane_orchestration.py` ajoute trois
  preuves bornees: priorite et surface Biblio, fallback presence face aux locks
  domaine invalides, et absence totale d'evenement Notes sans selection. Les
  contrats existants conservent Adobe absent/error, Biblio
  disabled/not_selected/error, Agenda disabled, Web off/not_selected, ordre
  des lanes, bypass provider sous final lock, stream/non-stream, capsule,
  manifest et persistence.
- Sensibilites rejetees: frontiere absente, priorite Agenda/Biblio inversee,
  lock invalide accepte, fallback presence perdu, meta ou enveloppe Biblio
  effacee, et faux evenement Notes pour un no-op. Les goldens 9B.0 rejettent
  toujours lane ajoutee/retiree/deplacee, appel provider sous lock et
  duplication de persistence.

Commandes hermetiques executees avec `--network none`, checkout read-only et
`/tmp` en tmpfs:

- baseline avant patch: `python -m unittest discover` -> `2556`, OK;
- RED frontiere agent-lane: nouveau module de test -> `3`, deux echecs
  attendus sur la frontiere absente;
- GREEN frontiere agent-lane: meme module -> `3`, OK;
- Adobe/Biblio/Agenda/Notes/Web, regime dialogique et goldens -> `127`, OK;
- stream/persistence/capsule/manifest/observabilite transverse -> `89`, OK;
- decouverte complete apres extraction -> `2559`, OK.

Limite: 9B.2 ne deplace ni l'execution des runtimes domaine, ni l'injection des
lanes, ni l'observabilite Web. Les Lots 9B.3 a 9B.6 restent ouverts et non
commences.

### Lot 9B.3 - Hermeneutic node state boundary

Golden tests prealables:

- read/write node state;
- final node state build;
- Stimmung/primary/validation observability;
- compact observability Lot 6H.

Patch attendu:

- isoler state read/write/build; aucun changement prompts/agents.

Checklist:

- [x] Extraire state helpers.
- [x] Verifier observability compact.
- [x] Verifier aucun prompt ou payload brut.

Preuves livrees le 16 aout 2026:

- `app/core/chat_hermeneutic_node_state.py` porte les cinq adaptateurs de
  lecture, extraction du state rehydratable, ecriture ignoree, ecriture et
  construction du state final auparavant definis dans `chat_service.py`. Les
  cinq fonctions sont AST-identiques avant/apres; `chat_service.py` reexporte
  leurs noms prives existants et passe de `1061` a `936` lignes.
- `_run_hermeneutic_node_insertion_point(...)` reste le coordinateur dans
  `chat_service.py`: l'ordre lecture -> primary -> validation -> build/write,
  les appels Stimmung/primary/validation et leurs emissions observability ne
  bougent pas. Les prompts, agents, payloads provider et le domain builder
  `core.hermeneutic_node.runtime.node_state` sont inchanges.
- `app/tests/unit/core/test_chat_hermeneutic_node_state.py` ajoute cinq preuves
  bornees: propriete/reexport de la frontiere, read absent/error et filtrage
  d'un state invalide, write absent/error et semantique `attempted`, build
  answer/clarify avec bypass presence, puis rejet des combinaisons invalidees
  et des erreurs du domain builder. Les exceptions ne projettent que leur
  classe, jamais leur texte brut.
- Les contrats existants prouvent toujours la persistence et rehydratation sur
  deux tours, la persistence du state final valide answer/clarify/suspend, le
  no-write presence ou validation absente, ainsi que les evenements compacts
  Stimmung, primary et validation. Le guard observability, les goldens Lot 9B,
  le stream/non-stream, la persistence, la capsule et le manifest restent
  verts et content-free.

Sensibilites rejetees: frontiere absente ou helpers restes dans
`chat_service.py`; texte brut d'exception read/write/build expose; state
invalide rehydrate; writer absent marque comme tentative; write error
requalifie en succes; regimes answer/meta inverses; presence persistee;
posture/regime invalide accepte; erreur du domain builder propagee. Les
mutations 9B.0 rejettent toujours changement d'ordre, appel provider sous
final lock, duplication de capsule ou de persistence et payload brut.

Commandes hermetiques executees avec `--network none`, checkout read-only et
`/tmp` en tmpfs:

- baseline avant patch: `python -m unittest discover` -> `2559`, OK;
- RED frontiere state: nouveau module de test -> `5`, un echec attendu sur la
  propriete encore `core.chat_service`;
- GREEN frontiere state: meme module -> `5`, OK;
- state/insertion/observabilite/goldens -> `133`, OK;
- transport, stream/non-stream, persistence, capsule et manifest -> `90`, OK;
- decouverte complete apres extraction -> `2564`, OK.

Limite: 9B.3 ne deplace ni le coordinateur hermeneutique, ni les agents
primary/validation, ni l'emission observability. Les Lots 9B.4 a 9B.6 restent
ouverts et non commences.

### Lot 9B.4 - Chat turn coordinator boundary

Golden tests prealables:

- Lot 9B.0 ferme avec lane-order, final locks, capsule/manifest et persistence;
- contrats chat session, prompt lanes et refus avant mutation;
- stream et non-stream raccordes au meme handoff LLM.

Patch attendu:

- reduire `chat_service.chat_response` a un coordinateur des frontieres deja
  nommees, une responsabilite a la fois;
- ne changer ni ordre des lanes, ni messages, ni metas, ni final locks.

Critere de sortie:

- reduction mesuree du span, des branches ou des dependances directes du
  coordinateur;
- aucune nouvelle facade concurrente et aucun changement produit.

Statut: ferme le 16 aout 2026.

Preuves livrees:

- `app/core/chat_main_payload.py` porte l'unique frontiere privee
  `prepare_main_payload(...)`: construction du payload principal, injections
  tardives, resolution des final locks, capsule et manifest;
- `app/core/chat_service.py` conserve `chat_response(...)` comme coordinateur,
  les frontieres deja extraites et le handoff final vers
  `chat_llm_flow.run_llm_exchange(...)`;
- `app/tests/unit/core/test_chat_main_payload_boundary.py` verrouille la
  provenance de la frontiere et interdit la reintroduction des operations
  extraites dans le coordinateur;
- les goldens 9B.0 et les contrats existants traversant
  `chat_service.chat_response(...)` figent toujours ordre des lanes,
  injections, refus, final locks, capsule/manifest, stream/non-stream et
  persistance.

Mesures et invariants:

- `chat_response(...)`: 534 -> 412 lignes, 13 -> 11 branches et 144 -> 107
  appels directs; `chat_service.py`: 936 -> 815 lignes;
- le handoff final vers `run_llm_exchange(...)` est syntaxiquement identique
  avant/apres; aucun contrat SSE, message, meta, final lock ou persistance
  n'est modifie;
- les reexports et points de patch historiques de `chat_service` sont
  conserves; la nouvelle frontiere est explicite, privee et n'a qu'un appelant;
- mutations controlees rejetees en RED: frontiere absente ou de mauvais
  module, delegation absente, et reintroduction directe dans `chat_response`
  d'une injection Notes/Documents/Biblio/Adobe, de la capsule ou du manifest.

Commandes executees:

- baseline hermetique complete: `2564 tests`, 0 echec, 0 erreur;
- test structurel RED puis GREEN: 2 echecs attendus, puis `2 tests`, OK;
- goldens et suites chat principales: `17 tests`, OK;
- lanes et refus Web/Documents/Notes/Agenda/Biblio/Adobe: `83 tests`, OK;
- stream, persistance, capsule, manifest et observabilite: `96 tests`, OK;
- decouverte hermetique complete finale: `2566 tests`, 0 echec, 0 erreur,
  sans nouveau skip ni expected failure.

Limites restantes:

- l'interface privee comporte 39 arguments nommes: ce couplage preexistant est
  rendu explicite pour l'unique appelant, sans sac d'etat generique ni facade
  supplementaire;
- les lectures Documents et Notes restent dans leurs frontieres 9B.1 deja
  nommees; l'execution provider, le streaming et la persistance restent dans
  `chat_llm_flow` et relevent des lots ulterieurs;
- aucun travail des Lots 9B.5 et 9B.6 n'est commence.

### Lot 9B.5 - LLM exchange, stream and persistence boundaries

Golden tests prealables:

- `app/tests/unit/chat/test_chat_llm_flow.py`;
- `app/tests/unit/chat/test_chat_stream_control.py`;
- `app/tests/test_server_chat_route_transport_contract.py`;
- matrice Lot 10C des quatre surfaces et de la persistence fail-closed.

Patch attendu:

- separer dans `run_llm_exchange` la preparation/lecture provider, la
  finalisation persistante et les derives post-persistence;
- traiter son `event_stream` comme partie du meme sous-lot, pas comme tache
  concurrente.

Critere de sortie:

- URL, headers, payloads, timeouts, terminaux, rollback et persistence
  inchanges;
- stream et non-stream partagent des frontieres explicites avec moins de
  duplication et de branches croisees.

Statut: ferme le 16 aout 2026.

Preuves livrees:

- `app/core/chat_llm_provider_exchange.py` porte la resolution bornee du
  secret principal, la preparation URL/headers/payload, la lecture provider
  stream et non-stream et leur observabilite content-free;
- `app/core/chat_assistant_finalization.py` porte append/save, phase de
  persistence, rollback exact et derives post-persistence fail-open;
- `app/core/chat_llm_flow.py` conserve `run_llm_exchange(...)` comme unique
  coordinateur et son `event_stream` comme machine d'etat locale du meme lot;
- `app/tests/unit/chat/test_chat_llm_flow_boundaries.py` verrouille les
  proprietaires et interdit la reintroduction des POST et ecritures de
  conversation bas niveau dans le coordinateur;
- `app/tests/test_server_phase5bis.py` suit la resolution obligatoire du
  secret runtime dans son nouveau proprietaire sans retablir de fallback env.

Mesures et invariants:

- `chat_llm_flow.py`: 950 -> 728 lignes; `run_llm_exchange`: 574 -> 485
  lignes, 63 -> 41 noeuds de branchement AST et 149 -> 86 appels AST;
  l'`event_stream` principal: 327 -> 261 lignes, 55 -> 34 branchements et
  88 -> 50 appels;
- ordre de resolution secret/headers/payload/model/title/reasoning/URL et
  timeouts provider inchange; le final lock bypass toujours secret, URL et
  modele principal;
- stream et non-stream conservent normalisation, meta/provenance, terminal
  unique, `updated_at`, interruption, rollback et nombre de saves;
- aucun derive memoire/identite ni log AssistantText ne part d'un assistant
  non sauvegarde; l'ordre distinct des derives stream/non-stream est preserve;
- les objets de frontiere masquent headers, payload, URL, contenu et meta dans
  leur `repr`; aucun contenu utilisateur/provider ni secret n'est ajoute aux
  logs ou tests.

Sensibilite et contre-audit:

- RED structurel: `3 tests`, deux echecs attendus tant que modules et
  delegations etaient absents; la mutation interne etait deja verte;
- le golden rejette retrait de chaque delegation provider/persistence et
  reintroduction d'un POST, append ou save bas niveau dans le flow;
- la decouverte complete a revele puis fait corriger le seul contrat source
  Phase 5bis devenu obsolete: il exige toujours le secret runtime, dans son
  nouveau proprietaire, plus la delegation depuis le flow;
- contre-audit manuel: portees `try/except`, ordre des effets, double save,
  rollback apres exception, terminal erreur, meta interrompue, final lock,
  contenu sensible et perimetre 9B.6 relus integralement.

Commandes hermetiques executees avec `--network none`, checkout read-only et
`/tmp` en tmpfs:

- baseline complete avant patch: `2566 tests`, 0 echec, 0 erreur;
- flow/stream/transport/goldens: `46 tests`, OK; apres revalidation Phase
  5bis: `48 tests`, OK;
- lanes Web/Documents/Notes/Agenda/Biblio/Adobe: `56 tests`, OK;
- persistence/capsule/manifest/observabilite: `114 tests`, OK;
- contrat Phase 5bis cible: `2 tests`, OK;
- decouverte complete finale: `2569 tests`, 0 echec, 0 erreur, sans nouveau
  skip ni expected failure.

Limites restantes:

- `run_llm_exchange` reste un coordinateur de 485 lignes car les decisions de
  buffering, terminal et reprise interrompue forment une seule machine d'etat
  stream contractuelle; aucune seconde facade concurrente n'est ajoutee;
- les deux modules prives n'ont qu'un appelant produit et ne constituent pas
  une nouvelle capacite;
- la validation agent interne releve exclusivement de 9B.6, laisse ouvert et
  non commence.

### Lot 9B.6 - Validation agent internal boundaries

Golden tests prealables:

- `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py`;
- `app/tests/test_server_chat_hermeneutic_insertion_contract.py`;
- `app/tests/test_server_chat_synthetic_logs_contract.py`;
- contrat prompt/fallback et hard guards inchanges.

Patch attendu:

- separer validation pure, construction du message, transport et fallback
  interne sans modifier le prompt ou le verdict produit;
- conserver `build_validated_output` comme facade contractuelle.

Critere de sortie:

- moins de responsabilites par fonction et tests identiques sur verdict,
  fail-open local, observabilite et bornes payload.

Statut: ferme le 16 aout 2026.

Preuves livrees:

- `app/core/hermeneutic_node/validation/validation_contract.py` porte la
  validation pure des entrees et du verdict provider, la normalisation du
  verdict final et la construction des resultats nominaux/fail-open;
- `app/core/hermeneutic_node/validation/validation_messages.py` porte la
  construction deterministe et bornee des deux messages provider, y compris
  la reference temporelle, la compaction du dialogue et l'observabilite
  preparatoire content-free;
- `app/core/hermeneutic_node/validation/validation_transport.py` porte
  exclusivement l'attribution provider, URL/headers, POST, timeout, lecture
  de reponse et metadata provider;
- `app/core/hermeneutic_node/validation/validation_agent.py` conserve
  `build_validated_output(...)` comme facade contractuelle, les patch points
  historiques d'observabilite et la politique interne
  primary/fallback/fail-open;
- `app/tests/test_validation_agent_boundaries.py` exerce directement les
  trois frontieres sans introspection du texte source.

Mesures et invariants:

- `validation_agent.py`: 1141 -> 267 lignes;
  `build_validated_output`: 93 -> 46 lignes, 3 -> 1 noeuds de branchement AST
  et 17 -> 9 appels AST; `_call_model`: 66 -> 54 lignes et 14 -> 6 appels;
- la sequence fixe primary puis fallback reste explicite dans
  `_run_model_fallback`; le dernier reason code, le modele rapporte, les
  exceptions timeout/HTTP, le prompt manquant et le fail-open sous hard guard
  restent identiques;
- le prompt charge depuis `prompts/validation_agent.txt` est inchange
  byte-pour-byte; deux matrices de messages avant/apres, dont contexte large,
  temps local et hard guard, sont identiques;
- six comparaisons avant/apres verrouillent verdict valide, mutants invalides,
  payload final et fail-open absent/present; URL, headers, attribution,
  timeout, sampling, budget et metadata provider conservent leurs tests;
- `validation_prompt_prepared` conserve les memes comptes et bornes
  content-free; aucun prompt, message, contenu Memory/Web ou secret n'est
  ajoute aux logs, objets de frontiere ou nouvelles fixtures.

Sensibilite et contre-audit:

- RED TDD: le golden de frontieres echoue a l'import tant que les trois
  modules n'existent pas;
- le contrat pur rejette le mutant `presence + clarify`; le constructeur de
  messages rejette implicitement deplacement, debordement ou mutation des
  entrees par egalite repetee, ordre et bornes; le transport rejette appel
  duplique, alteration du payload/timeout ou interpretation prematuree du
  texte provider;
- une premiere decouverte complete, encore a `2569 tests`, a prouve que le
  golden sous l'arborescence unitaire non packagee n'etait pas collecte; son
  deplacement sans duplication vers `app/tests/` porte le total autoritatif a
  `2572`;
- la matrice ciblee a ensuite detecte `36` erreurs quand le patch point
  historique `validation_agent.chat_turn_logger` avait disparu; la facade
  reexporte le meme objet sans reprendre l'emission;
- contre-audit manuel: facade unique, patch points historiques, ordre
  observabilite/POST/parse, priorite primary/fallback, hard guards, payloads
  bornes, contenu sensible, prompt, dependances et perimetre 9C relus.

Commandes hermetiques executees avec `--network none`, checkout read-only et
`/tmp` en tmpfs:

- baseline complete avant patch: `2569 tests`, 0 echec, 0 erreur;
- RED des nouvelles frontieres: `1` erreur d'import attendue;
- frontieres + validation agent: `39 tests`, OK; avec verite temporelle:
  `44 tests`, OK;
- validation/insertion/logs synthetiques: `71 tests`, OK;
- insertion/observabilite/prompt/corpus/entrees runtime: `67 tests`, OK;
- decouverte complete finale: `2572 tests`, 0 echec, 0 erreur, sans nouveau
  skip ni expected failure.

Limites restantes:

- `validation_contract.py` reste un module cohesif de validation
  structurelle de 540 lignes; il ne contient ni transport, ni prompt, ni
  politique de retry et n'appelle aucun service externe;
- la composition content-free de `validation_prompt_prepared` reside avec le
  message provider; la facade reexporte le logger historique et conserve
  l'ordre exact emission puis transport;
- aucun travail du Lot 9C n'est commence.

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

- [x] Matrix status/reason codes.
- [x] Matrix context payload content-free.
- [x] Matrix log redaction.

Statut: ferme le 16 aout 2026.

Preuves livrees:

- `app/tests/support/web_search_golden_matrix.py` traverse la facade publique
  `build_context_payload(...)`, les vrais normalisateurs SearXNG/Crawl4AI et
  l'emetteur runtime avec transports, reader PDF, services et logger
  synthetiques; aucune DB, aucun provider ni secret reel n'est requis;
- `app/tests/unit/web_search/test_web_search_golden_matrix.py` fige une matrice
  compacte de huit cas: URL explicite lue, timeout Crawl4AI, erreur Crawl4AI,
  PDF direct, SearXNG sans resultat/erreur upstream et discovery sans
  citation/erreur upstream;
- les tests Phase 4, discovery, evidence, confiance, PDF et logger existants
  restent les preuves detaillees de chaque branche; le nouveau golden ne les
  duplique pas et ne snapshotte que leur composition observable commune.

Invariants figes:

- `no_data` reste `skipped`, distinct de `web_search_upstream_error` et
  `web_discovery_upstream_error`; les erreurs discovery conservent
  `WebDiscoveryUpstreamError` et `openrouter_config_error`;
- une erreur ou un timeout Crawl4AI sur URL explicite reste un echec de
  lecture `page_not_read_error`, sans faux succes ni faux contexte injecte;
- HTML lu et PDF direct restent `page_read`, avec respectivement
  `crawl_markdown` et `web_pdf_text`; le PDF contourne Crawl4AI;
- evidence/confiance restent `sufficient/high` pour les lectures reussies et
  `insufficient/low` pour absence de donnees ou upstream en erreur;
- status, reason, contexte injecte, branche skipped et event error restent
  coherents entre payload de contexte et projection runtime;
- la projection golden et les events n'exposent aucune requete, URL complete,
  contenu, exception ou secret synthetique; `query_preview` reste vide et
  `explicit_url_included=false`.

Sensibilite:

- le golden rejette cinq mutants semantiques controles: inversion
  `no_data/error`, faux succes de lecture apres timeout, PDF requalifie en
  Crawl4AI, preuve insuffisante requalifiee suffisante et event error duplique;
- la garde content-free rejette un mutant contenant la sentinelle brute.

Commandes hermetiques executees avec `--network none`, checkout read-only et
`/tmp` en tmpfs:

- baseline complete avant patch: `2572 tests`, 0 echec, 0 erreur;
- nouveau golden: `4 tests`, OK;
- tous les tests `tests/unit/web_search`: `167 tests`, OK;
- logger/guard/redaction: `52 tests`, OK;
- route Web, provenance, read-state et golden Lot 9: `36 tests`, OK;
- decouverte complete finale: `2576 tests`, 0 echec, 0 erreur, sans nouveau
  skip ni expected failure.

Limites restantes:

- la projection `web_search` PDF est bien content-free au point d'emission,
  mais la garde writer-side courante refuse ensuite le compteur
  `web_pdf_read_pages` comme `unknown_scalar_key`. Cette contradiction
  preexistante entre contrat PDF et allowlist n'est pas corrigee dans le lot
  tests/docs-only; elle devra etre resolue avant 9C.4 sans changer le schema
  observable voulu. Elle est resolue ulterieurement par la passe 1 du
  prerequis avant 9C.2 documentee ci-dessous;
- `app/tests/unit/benchmark/test_web_search_benchmark.py` n'est pas collecte
  par la decouverte autoritative; son execution isolee avec le depot complet
  monte s'arrete avant collecte sur l'import legacy deja retire
  `memory_identity_periodic_apply`. Cette dette preexistante n'est ni masquee
  ni corrigee hors perimetre 9C.0;
- aucun client, status mapper, reader, builder ou emetteur runtime n'est encore
  extrait: 9C.1 a 9C.4 restent ouverts et non commences.

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

- [x] Extraire local search client.
- [x] Extraire discovery client adapter.
- [x] Verifier timeout/error_class.

Statut: ferme le 16 aout 2026.

Preuves livrees:

- `app/tools/web_search_clients.py` porte desormais l'appel HTTP SearXNG, sa
  normalisation `ok/error` et l'adapter de selection local/OpenRouter Exa;
- `app/tools/web_search.py` conserve les facades `search(...)` et
  `search_with_status(...)`, les points d'injection historiques et le log
  content-free, mais ne construit plus lui-meme la requete HTTP ni la reponse
  discovery locale;
- `app/tests/unit/web_search/test_web_search_clients.py` ajoute cinq preuves
  hermetiques de transport, status et delegation; la matrice golden 9C.0
  continue de traverser le builder public complet.

Invariants figes:

- SearXNG reste appele sur `/search` avec un timeout explicite de `10 s`, les
  parametres profiles non vides et la meme borne de resultats;
- un succes SearXNG reste `status=ok`, y compris sans resultat, tandis qu'une
  exception devient `status=error`, `reason_code=web_search_upstream_error`,
  `results=[]` et conserve uniquement la classe d'erreur;
- l'adapter discovery preserve la distinction entre absence de donnees locale
  et erreur upstream locale; les reason codes
  `searxng_request_failed`/`web_search_upstream_error` ne sont ajoutes que dans
  le second cas;
- le provider externe conserve le timeout configure, le transport injecte,
  `openrouter_timeout` et les autres classifications existantes;
- le query plan, les readers Crawl4AI/PDF, le context/evidence builder et la
  projection runtime ne changent ni de responsabilite ni de semantique.

Sensibilite:

- les preuves echouent si le timeout SearXNG est retire ou modifie, si une
  erreur devient un succes vide, si `error_class` disparait, si les parametres
  profiles vides sont envoyes, si le timeout discovery est perdu, ou si les
  facades contournent les clients extraits;
- les sentinelles d'exception restent absentes des resultats normalises.

Commandes hermetiques executees avec `--network none`, checkout read-only et
`/tmp` en tmpfs:

- baseline complete avant patch: `2576 tests`, 0 echec, 0 erreur;
- preuve rouge avant implementation: import du module absent, `1 erreur`
  attendue;
- nouveaux tests et golden 9C.0: `9 tests`, OK;
- tous les tests `tests/unit/web_search`: `172 tests`, OK;
- logger/guard/redaction: `54 tests`, OK;
- route Web, provenance, read-state et golden Lot 9: `36 tests`, OK;
- decouverte complete finale: `2581 tests`, 0 echec, 0 erreur, sans nouveau
  skip ni expected failure.

Limites restantes:

- aucun provider reel, secret, DB ou reseau n'est sollicite; la preuve porte
  sur les contrats hermetiques et les fakes de transport;
- la contradiction preexistante `web_pdf_read_pages`/writer-side guard et le
  benchmark legacy non collecte sont tous deux encore ouverts a la fermeture
  de 9C.1; la premiere est resolue par la passe 1 ci-dessous, le second reste
  attribue a la passe 2;
- Crawl4AI/PDF, context/evidence et event projection restent integralement
  ouverts dans 9C.2 a 9C.4, sans commencement anticipe.

#### Prerequis avant 9C.2 - passe 1: compteur PDF et writer-side guard

Statut: ferme le 16 aout 2026.

Cause prouvee:

- le vrai payload runtime PDF produit par la matrice 9C.0 etait content-free,
  mais `web_pdf_read_pages` etait le seul compteur de son resume a ne
  correspondre ni a l'allowlist scalaire exacte ni a un suffixe metrique;
- la writer-side guard le refusait donc avec l'unique issue
  `unknown_scalar_key`, alors que les compteurs voisins `_bytes`, `_chars`,
  `_ms` et `_count` etaient deja admis.

Patch et preuves:

- `app/observability/observability_payload_guard_schema.py` ajoute uniquement
  `web_pdf_read_pages` a l'allowlist scalaire; aucun suffixe generique, champ
  voisin, contenu ou schema observable n'est ajoute;
- `app/tests/unit/logs/test_observability_payload_guard.py` traverse le vrai
  golden `explicit_url_pdf`, exige l'acceptation du compteur contractuel et
  prouve qu'un mutant voisin `web_pdf_page_number` reste refuse comme
  `unknown_scalar_key`;
- la premiere invocation rouge, invalide, a revele un nom de helper de test
  errone et a ete ecartee; apres correction, la preuve rouge valide donne
  `1 test`, `1 echec` sur le refus du payload, puis la preuve verte
  garde/logger/observabilite/golden Web donne `54 tests`, OK;
- decouverte complete: `2582 tests`, 0 echec, 0 erreur. L'unique nouveau test
  explique le passage de `2581` a `2582`.

Limites et frontiere:

- aucun reader PDF, payload builder, event projector, format de log ou contrat
  content-free n'est modifie;
- seul FridaDev doit etre rebuild pour livrer la correction de schema; 9C.2 a
  9C.4 restent non commences;
- la passe 2 benchmark ci-dessous reste ouverte et doit partir du commit propre
  de cette passe.

#### Prerequis avant 9C.2 - passe 2: benchmark Web autoritatif

Statut: ferme le 16 aout 2026.

Checklist:

- [x] Reproduire l'absence de collecte et l'echec isole.
- [x] Prouver la cause transitive exacte sans retablir Identity legacy.
- [x] Reintegrer le benchmark a la decouverte s'il reste contractuel, sinon
  prouver son obsolescence et l'archiver explicitement.
- [x] Etablir une nouvelle baseline complete avant 9C.2.

Autorite et cause prouvees:

- `benchmark/README.md`, `benchmark/web-search/README.md`, les fixtures Web et
  les douze preuves de `app/tests/unit/benchmark/test_web_search_benchmark.py`
  confirment que le benchmark Web reste un outil operateur contractuel; il ne
  doit donc pas etre archive;
- `app/tests/unit/benchmark/` n'etant pas un package de decouverte, ces preuves
  restaient absentes de la baseline applicative `2582`, sans skip ni signal;
- l'execution isolee avec `app/` et `benchmark/` disponibles echouait avant
  toute collecte: `benchmark.run_benchmark` importait avidement la campagne
  `identity_periodic`, laquelle importe le module supprime
  `memory_identity_periodic_apply`;
- ce module appartient au writer Identity score-first retire; le restaurer ou
  adapter sa campagne aurait contredit le contrat Identity vivant et elargi
  ce prerequis Web.

Patch et preuves:

- `benchmark/run_benchmark.py` ne charge plus la campagne
  `identity_periodic` au demarrage commun; elle n'est importee que si cette
  suite legacy est explicitement selectionnee. Aucun chemin Identity n'est
  retabli et les autres suites gardent leurs choix, modeles et payloads;
- `app/tests/unit/web_search/test_web_search_benchmark_authority.py` expose
  exactement le `WebSearchBenchmarkSuiteTests` existant a la decouverte Web;
  les autres benchmarks operateur, dont certains sont historiques, ne sont
  ni declares autoritatifs par effet de bord ni modifies dans cette passe;
- le benchmark Web ajoute une treizieme preuve qui traverse le vrai
  `benchmark_runner.main()` en dry-run, sans provider, et exige les trois
  artefacts attendus sous `/tmp`;
- la fixture `local/local_profiled` remplace et restaure desormais a la fois
  `sys.modules["tools.web_search"]` et l'attribut cache sur le package
  `tools`. La suite Web elargie a revele cette dependance d'ordre preexistante:
  le module isole passait, mais la suite de `185 tests` echouait auparavant
  avec une liste d'appels vide;
- la mutation controlee correspondant au bug est l'import eager de la campagne
  Identity: elle reproduit l'`ImportError` avant collecte. Retirer le pont de
  decouverte ramene silencieusement la baseline de `2595` a `2582`; conserver
  seulement `sys.modules` dans la fixture reproduit l'echec d'ordre de la
  suite Web.

Commandes hermetiques executees avec `--network none`, image read-only,
`/tmp` en tmpfs et seulement `app/` puis `benchmark/` montes read-only:

- baseline propre entre les deux passes: `2582 tests`, 0 echec, 0 erreur;
- reproduction isolee avant patch: `1 test`, `1 erreur` d'import avant
  collecte sur `memory_identity_periodic_apply`;
- module benchmark Web puis point d'entree autoritatif: `13 tests`, OK pour
  chacun;
- suite `tests/unit/web_search`: `185 tests`, OK apres reproduction puis
  correction de la dependance d'ordre;
- benchmarks voisins Stimmung et Validation Agent: `13 tests`, OK;
- decouverte complete avec montages bornes `app/` et `benchmark/`:
  `2595 tests`, 0 echec, 0 erreur. Le delta exact de treize correspond aux
  douze preuves Web jusque-la non collectees et au nouveau test du CLI.

Limites et frontiere:

- les campagnes benchmark ne deviennent pas du runtime produit et leur dry-run
  ne resout aucun provider, secret ou acces DB; `--network none` interdit tout
  service externe a l'ensemble de la decouverte;
- la branche `identity_periodic` du runner reste un artefact legacy incompatible
  avec le writer retire lorsqu'elle est explicitement invoquee; son
  archivage eventuel releve d'un lot Identity distinct, pas de ce prerequis
  Web;
- 9C.2 a 9C.4 restent ouverts et non commences. La baseline autoritative avant
  9C.2 inclut desormais le benchmark Web avec le second montage read-only
  `benchmark/`.

### Lot 9C.2 - Crawl4AI/PDF reader boundary

Statut: ferme le 16 aout 2026.

Patch attendu:

- isoler crawl markdown, explicit URL, PDF reader.

Risques:

- exposer URL query;
- changer policy PDF direct.

Checklist:

- [x] Extraire crawl client.
- [x] Extraire PDF reader adapter.
- [x] Verifier URL redaction.

Implementation livree:

- `app/tools/web_search_readers.py` porte desormais le client `/md`, sa
  normalisation de statut, la politique URL explicite `fit` puis `raw`
  uniquement apres un resultat `empty`, la politique de lecture d'un resultat
  de recherche et l'adaptateur vers le lecteur PDF borne existant;
- `app/tools/web_search.py` conserve des facades minces et tardivement liees
  pour les appelants et seams de test existants. Les builders de contexte et
  d'evidence ainsi que la projection d'evenements restent dans leur perimetre
  actuel: 9C.3 et 9C.4 ne sont pas commences;
- `app/tests/unit/web_search/test_web_search_readers.py` ajoute six preuves
  synthetiques et content-free: contrat `/md` et timeout, garde URL avant
  resolution de settings/secret/transport, fallback URL explicite, adaptation
  PDF directe, redaction des logs d'erreur et passage effectif par la nouvelle
  frontiere.

Invariants preserves:

- payload Crawl4AI, filtres, cache mode, query hash/compteur, statuts et reason
  codes inchanges; aucun provider ni reseau reel n'est utilise par les tests;
- une URL bloquee est refusee avant toute resolution de configuration, secret,
  payload ou transport; les logs n'exposent ni hote, path, query, fragment,
  token ni texte d'exception;
- une URL explicite tente `raw` seulement apres un `fit` vide; une erreur ou un
  succes `fit` ne declenche pas ce fallback;
- le lecteur PDF direct conserve detection, budget, probe content-type et
  resultat crawl-like sans ajouter stockage, cache, OCR ou autre capacite.

Preuves executees dans le runner hermetique `--network none`, checkout
read-only, `/tmp` en tmpfs, avec montages bornes `app/` et `benchmark/`:

- baseline avant patch: `2595 tests`, OK;
- RED cible: `tests.unit.web_search.test_web_search_readers`, ImportError
  attendu car la frontiere n'existait pas encore;
- GREEN cible: `6 tests`, OK;
- suite `tests/unit/web_search`: `191 tests`, OK;
- observabilite Web, garde payload et golden Lot 9: `59 tests`, OK;
- decouverte complete finale: `2601 tests`, 0 echec, 0 erreur, sans nouveau
  skip ni expected failure. Le delta exact de six correspond aux six preuves
  ajoutees.

Sensibilite et limites:

- les preuves echouent si la facade contourne la nouvelle frontiere, si le
  contrat `/md` ou son timeout change, si la garde SSRF est deplacee apres une
  resolution sensible, si `raw` est tente sans `fit` vide, si l'adaptateur PDF
  altere son budget ou si URL/query/secret/exception brute reapparaissent dans
  le log;
- aucun appel provider live n'a ete ajoute: les contrats existants et la
  decouverte hermetique sont l'autorite de non-regression pour ce refactor;
- 9C.3 et 9C.4 restent entierement ouverts et non commences.

### Lot 9C.3 - Context/evidence payload boundary

Statut: ferme le 16 aout 2026.

Patch attendu:

- isoler build context payload/evidence/status.

Risques:

- changer prompt material;
- casser evidence failure guidance.

Checklist:

- [x] Extraire context material builder.
- [x] Extraire evidence summary.
- [x] Verifier source-first contracts.

Implementation livree:

- `app/tools/web_search_context.py` porte desormais les transformations de
  materiau Web: normalisation des sources, budgets et troncatures, contexte
  recherche ou URL explicite, promotion/deduplication de l'URL primaire,
  read-state, classification `ok`/`skipped`/`error` et composition des
  evaluations profile/confidence/evidence;
- `app/tools/web_search.py` conserve les facades tardivement liees et
  l'orchestration de collecte. Le source payload builder reste au contact des
  readers 9C.2; les summaries/counters content-free et
  `_emit_web_search_runtime_event` restent en place pour 9C.4;
- `app/tests/unit/web_search/test_web_search_context.py` ajoute six preuves
  synthetiques: ordre des sources et terminaison du contexte, materiau PDF
  explicite et budget, matrice des read-states, matrice des statuts upstream,
  guidance d'evidence avec source situee sans autorite attendue, et passage
  effectif de la facade par la nouvelle frontiere.

Invariants preserves:

- l'ordre deja decide par source-first/rerank reste celui du payload et du
  prompt; l'URL explicite correspondante est promue une seule fois sans
  duplication dans le fallback;
- le prompt material, ses lignes d'attribution, son ordre, ses budgets, sa
  troncature et son terminal `[FIN DES RÉSULTATS WEB]` restent inchanges;
- les read-states distinguent lecture complete, partielle, fallback snippet,
  crawl vide et erreur; les erreurs SearXNG et discovery conservent leurs
  reason codes et classes distincts;
- l'evaluation profile/confidence/evidence conserve la guidance de limite et
  les champs source-first. Aucune query, URL ou source n'est ajoutee a la
  projection content-free.

Preuves executees dans le runner hermetique `--network none`, checkout
read-only, `/tmp` en tmpfs, avec montages bornes `app/` et `benchmark/`:

- baseline avant patch: `2601 tests`, OK;
- RED cible: `tests.unit.web_search.test_web_search_context`, ImportError
  attendu car la frontiere n'existait pas encore;
- GREEN cible: `6 tests`, OK;
- suite `tests/unit/web_search`: `197 tests`, OK;
- logger Web, garde payload, temporalite, golden 9C, benchmark Web et golden
  Lot 9: `81 tests`, OK;
- preuve resserree context/golden/source-first/evidence: `34 tests`, OK;
- decouverte complete finale: `2607 tests`, 0 echec, 0 erreur, sans nouveau
  skip ni expected failure. Le delta exact de six correspond aux six preuves
  ajoutees.

Sensibilite et limites:

- les preuves echouent si l'ordre des sources est inverse, si le terminal ou
  le materiau PDF disparait, si un read-state est confondu, si les priorites de
  statut local/discovery changent, si la guidance de preuve insuffisante est
  perdue ou si la facade contourne la frontiere extraite;
- aucun provider, secret, DB ou reseau reel n'est sollicite. Les goldens 9C.0,
  les tests source-first et les contrats Web existants restent l'autorite de
  non-regression du comportement produit;
- 9C.4 reste entierement ouvert et non commence.

### Lot 9C.4 - Runtime event projection boundary

Statut: ferme le 16 aout 2026.

Patch attendu:

- isoler les summaries/counters et la projection content-free de
  `_emit_web_search_runtime_event`;
- ne changer ni collecte, ni evidence/confidence, ni status/reason codes.

Checklist:

- [x] Isoler les summaries et counters Web.
- [x] Isoler la projection et l'emission content-free.
- [x] Prouver la facade, les redactions et les branches terminales.

Implementation livree:

- `app/tools/web_search_runtime_events.py` porte les summaries/counters,
  l'enrichissement observable du payload et la projection content-free de
  l'evenement `web_search`; il ne contient aucun client de recherche, reader,
  requete HTTP, crawl ni resolution de secret;
- `app/tools/web_search.py` conserve quatre facades privees tardivement liees
  et l'orchestration de collecte. La projection auparavant imbriquee y est
  supprimee, sans changement des appelants ni du schema emis;
- `app/tests/unit/web_search/test_web_search_runtime_events.py` ajoute six
  preuves synthetiques sur les summaries/counters, la redaction, la
  preservation d'evaluations fournies, l'exclusivite des terminaux
  `skipped`/`error` et le passage effectif de la facade par la frontiere.

Invariants preserves:

- les compteurs, statuts, reason codes, domaines et metadonnees bornees gardent
  leur schema et leur ordre; query, URL complete, contenu source, empreintes de
  query/URL et contenu de contexte ne sont jamais projetes;
- une evaluation confidence/evidence deja fournie n'est pas recalculee; les
  evaluateurs existants restent inchanges lorsqu'une evaluation manque;
- `skipped` emet exactement un `branch_skipped` et aucun `error`; `error` emet
  exactement un `error` et aucun `branch_skipped`;
- collecte, source-first, readers 9C.2, contexte/evidence 9C.3, statuts et
  reason codes ne sont pas modifies.

Preuves executees dans le runner hermetique `--network none`, checkout
read-only, `/tmp` en tmpfs, avec montages bornes `app/` et `benchmark/`:

- baseline avant patch: `2607 tests`, OK;
- RED cible: `tests.unit.web_search.test_web_search_runtime_events`, ImportError
  attendu car la frontiere n'existait pas encore;
- GREEN cible: `6 tests`, OK;
- suite `tests/unit/web_search`: `203 tests`, OK. Une premiere invocation sans
  le montage `benchmark/` a correctement echoue dans le runner; elle a ete
  remplacee par la commande hermetique complete, sans changement de code;
- logger Web, garde payload, golden 9C, observabilite/redaction, autorite
  benchmark et golden Lot 9: `80 tests`, OK;
- decouverte complete finale: `2613 tests`, 0 echec, 0 erreur, sans nouveau
  skip ni expected failure. Le delta exact de six correspond aux six preuves
  ajoutees.

Sensibilite et limites:

- les preuves echouent si un summary ou compteur derive diverge, si query, URL,
  contenu ou empreinte reapparait, si confidence/evidence est reevaluee malgre
  des champs fournis, si un terminal est absent ou double, ou si la facade
  contourne la frontiere extraite;
- la matrice 9C.0 et les contrats observabilite existants continuent de figer
  le schema exhaustif. La garde default-deny et ses read-models ne sont pas
  modifies: leur consolidation appartient au Lot 9D;
- aucun provider, secret, DB, donnee operateur ou reseau reel n'est sollicite.
  Aucune extension fonctionnelle n'est introduite.

Critere de sortie atteint: l'emetteur est sans responsabilite de requete ou de
crawl, le schema observable reste identique et la projection n'est plus
imbriquee dans l'orchestrateur Web.

## Lot 9D - Observabilite guard/read-models

Objectif:
reduire la croissance du schema guard et du read-model de turn sans relacher
la garde default-deny.

Fichiers vises:

- `app/observability/observability_payload_guard_schema.py`
- `app/observability/turn_pipeline_read_model.py`
- `app/observability/dashboard_read_model.py`
- `app/observability/dashboard_observable_modules.py`
- `app/observability/admin_log_projection.py`
- tests `app/tests/unit/logs/*`, dashboard contracts

Hors scope:

- accepter un payload non prouve;
- changer les contrats content-free;
- Lot 7 `/log` UI hors regression.

Sous-lots:

### Lot 9D.0 - Golden guard matrix

Statut: ferme le 17 aout 2026.

Golden tests prealables revalides:

- payload legitime par stage: chat_response, stream, arbiter, memory,
  identity, web, agenda, biblio, stimmung, manifest;
- payload dangereux refuse: prompt/message/content/raw/url query/token-like/
  provider payload/exception brute.

Checklist:

- [x] Matrix accepted by stage.
- [x] Matrix rejected dangerous.
- [x] Token-like safe-code regression.

Implementation et inventaire:

- `app/tests/support/observability_guard_golden_matrix.py` porte une fixture
  synthetique content-free de dix payloads legitimes, dans l'ordre contractuel
  `chat_response`, stream, arbiter, memory, identity, web, agenda, biblio,
  stimmung et manifest. Le `stage` reste une metadonnee de preuve: le garde
  runtime demeure volontairement payload-only dans ce lot;
- `app/tests/unit/logs/test_observability_payload_guard_golden_matrix.py`
  ajoute trois goldens: couverture exacte et sans doublon des dix familles,
  acceptation inchangee de chaque payload, puis rejet fail-closed du meme
  payload apres ajout d'un texte non contractuel;
- la matrice de refus existante dans
  `app/tests/unit/logs/test_observability_payload_guard.py` couvrait deja
  exactement prompt, message, content, raw, URL/query, provider payload et
  exception brute, avec rejet content-free. Elle est revalidee sans seconde
  preuve dupliquee;
- sa regression `test_token_like_safe_code_value_is_rejected_without_blocking_normal_codes`
  reste l'autorite: variantes synthetiques `sk-*`, `ghp_*`, `hf_*` et
  `xoxb-*` refusees, reason codes normaux et modele qualifie acceptes.

Invariants figes:

- les dix familles legitimes restent acceptees et rendues sans transformation;
- une cle texte non contractuelle ajoutee a n'importe quelle famille provoque
  un refus content-free sans recopier la sentinelle;
- les champs bruts ou dangereux restent default-deny, y compris sous une cle
  autrement allowlistee;
- la detection token-like ne s'etend pas aux reason codes ordinaires ni aux
  noms de modeles contractuels;
- aucun schema, allowlist, writer, projection, read-model ou frontend runtime
  n'est modifie. 9D.1 reste non commence.

Preuves executees dans le runner hermetique `--network none`, checkout
read-only et `/tmp` en tmpfs:

- baseline avant patch: `2613 tests`, OK;
- RED initial: ImportError attendu pour la fixture golden absente;
- correction de fixture observee: le mutant Memory avec
  `retrieval_reason_code` a ete refuse `unknown_string_key`; la fixture finale
  emploie le `reason_code` reel du stage;
- nouveaux goldens: `3 tests`, OK;
- garde historique plus nouvelle matrice: `44 tests`, OK;
- suite complete `tests/unit/logs`: `222 tests`, OK;
- producteurs Agenda/Biblio/Stimmung/Arbiter/Web, manifest, dashboard et golden
  Lot 9: `245 tests`, OK;
- decouverte complete finale: `2616 tests`, 0 echec, 0 erreur, sans nouveau
  skip ni expected failure. Le delta exact de trois correspond aux trois
  goldens ajoutes.

Sensibilite et limites:

- les goldens echouent si une famille est retiree, ajoutee, dupliquee ou
  deplacee, si un payload legitime est refuse ou modifie, ou si une famille
  accepte le mutant `private_sentence`;
- les preuves historiques echouent si une donnee brute dangereuse ou une
  valeur token-like redevient acceptable, ou si `skipped`,
  `provider_timeout`, `llm_call_ok` ou `openai/gpt-5.4-mini` devient un faux
  positif;
- la decomposition des politiques safe-code/token-like, manifest et familles
  de schema appartient exclusivement a 9D.1. Ce lot n'introduit aucune
  allowlist runtime parallele et ne modifie pas la surface `/log` du Lot 7.

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

### Lot 9D.3 - Dashboard read-model boundaries

Golden tests prealables:

- `app/tests/unit/logs/test_dashboard_read_model_lot4.py`;
- `app/tests/test_server_admin_dashboard_contract.py`;
- content gate explicite et erreurs routes content-free.

Patch attendu:

- separer query/window, overview/conversations, inspection/story et content
  gate en conservant les cinq facades publiques du read-model.

Critere de sortie:

- payloads et routes identiques;
- builders de domaine testables sans couplage aux requetes des autres vues.

### Lot 9D.4 - Observable module registry boundaries

Golden tests prealables:

- `app/tests/unit/logs/test_dashboard_observable_modules_lot3.py`;
- analytics projection/storage et ordre stable des modules;
- labels et explications content-free.

Patch attendu:

- isoler reducers et serialization publique autour d'un registre unique;
- ne creer ni seconde taxonomie, ni second catalogue de modules.

Critere de sortie:

- cles, ordre, labels et payloads inchanges;
- reducers de domaine separes et couplage au registre reduit.

## Lot 9E - Frontend chat scripts/load-order/panels

Objectif:
reduire la fragilite des scripts navigateur non-module sans redesign UI.

Fichiers vises:

- `app/web/chat_threads_sidebar.js`
- `app/web/app.js`
- `app/web/chat_workspace_folders_sidebar.js`
- `app/web/chat_workspace_folder_*`
- `app/minimal_validation.py`, uniquement `_check_ui_assets`
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

### Lot 9E.3 - UI asset validator boundaries

Golden tests prealables:

- Lot 9.0 et 9E.0 fermes;
- `app/tests/test_minimal_validation_phase9.py` et phase 11;
- smoke frontend load-order et inventaire des assets/globals/IDs.

Patch attendu:

- decomposer `_check_ui_assets` par responsabilite UI dans des modules de
  validation nommes, sans modifier le runner global ni son schema de resultat;
- ne pas transformer `minimal_validation.py` en condition de demarrage.

Critere de sortie:

- verdict et details identiques;
- span, branches et dependances directes de `_check_ui_assets` reduits sans
  nouveau seuil automatique.

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
