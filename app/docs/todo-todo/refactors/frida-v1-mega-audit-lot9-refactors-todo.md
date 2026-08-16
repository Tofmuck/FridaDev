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

`app/docs/todo-todo/refactors/frida-v1-mega-audit-lot9-refactor-before-9b-todo.md`

Statut: ferme le 16 aout 2026. La TODO autoritative a classe et corrige les
38 en-tetes historiques, explique la variation de `2549` a `2552` tests et
prouve une decouverte complete hermetique a `0` echec, `0` erreur, `0`
skip et `0` expected failure. Les suites critiques et les goldens Lot 9
restent verts. Le Lot 9B.0 est donc degele; il devient le prochain lot
executable mais reste non commence.

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

### Lot 9C.4 - Runtime event projection boundary

Golden tests prealables:

- matrice 9C.0;
- tests Web observability et `chat_turn_logger`;
- payloads synthetiques prouvant l'absence de query, URL ou contenu brut.

Patch attendu:

- isoler les summaries/counters et la projection content-free de
  `_emit_web_search_runtime_event`;
- ne changer ni collecte, ni evidence/confidence, ni status/reason codes.

Critere de sortie:

- emetteur sans responsabilite de requete ou de crawl;
- schema observable identique et branches de projection reduites.

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
