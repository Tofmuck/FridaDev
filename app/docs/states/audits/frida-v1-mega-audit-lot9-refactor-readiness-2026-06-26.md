# Frida V1 mega-audit - Lot 9 refactor readiness

Date: 2026-06-26

Statut: audit preparatoire docs-only. Aucun refactor runtime, aucun
deplacement de code, aucun rebuild.

Source canonique de suite:
`app/docs/todo-todo/refactors/frida-v1-mega-audit-lot9-refactors-todo.md`

## Question pre-action

Existe-t-il un meilleur plan ?

Non. Le meilleur plan est audit + TODO seulement. Les lots 4E et 7 ont montre
qu'aucun P1/P2 comportemental immediat ne justifie un refactor opportuniste.
Lot 9 doit commencer par des golden tests et seulement ensuite extraire par
responsabilite reelle.

## Surfaces inspectees

Inventaire docs/code par signatures, tailles et tests existants:

| Surface | Taille observee | Responsabilite dominante | Decision readiness |
| --- | ---: | --- | --- |
| `app/server.py` | 1884 lignes | routes HTTP, garde admin, chat transport, workspace, dashboard/admin, pages HTML | dette structurelle confirmee; pas d'extraction avant golden route map et contrats route par famille |
| `app/core/chat_service.py` | 1255 lignes | orchestration tour chat, lanes, final locks, hermeneutic node, capsule/manifest, persistence | dette orchestration confirmee; pas d'extraction avant golden lane-order/final-lock/capsule |
| `app/tools/web_search.py` | 2655 lignes | SearXNG, discovery, Crawl4AI, PDF web, context payload, evidence, observabilite | module multi-responsabilite; refactor seulement apres golden status/error/no_data et payload content-free |
| `app/observability/observability_payload_guard_schema.py` | 764 lignes | schema default-deny writer-side | schema central acceptable court terme; split apres matrice accept/refuse par stage |
| `app/observability/turn_pipeline_read_model.py` | 1391 lignes | projection cockpit content-free par domaine | read-model dense; extraction apres golden fixtures multi-stage |
| `app/web/chat_threads_sidebar.js` | 1341 lignes | conversations, dossiers, panels, global bootstrap chat | dette frontend; refactor seulement apres smoke load-order et tests panels |
| `app/web/app.js` | 751 lignes | bootstrap chat, wiring global, events principaux | dette bootstrap; depend de la stabilisation des scripts globaux |
| Agenda modules | 500+ lignes par module cle | runtime Agenda V1 borne, CalDAV fake/live separation, pending/actions, observabilite | ne pas rouvrir produit; golden fake/local avant split |
| Biblio modules | 500-1200+ lignes par module cle | bibliothecaire borne, outils GET-only, planning, passages, reponses, observabilite | ne pas rouvrir produit; golden methods/outils/fallbacks avant split |
| Memory/Admin larges | 500-1000+ lignes | store/memory traces, arbiter, identity read-models, settings/admin | extraire seulement avec contrats admin/read-model existants |

## Tests existants utiles

Socle deja present:

- routes/server/admin: `tests.test_server_*`, `tests.test_server_admin_*`;
- chat orchestration: `tests.unit.chat.*`,
  `tests.test_server_chat_*`, `tests.support.server_chat_pipeline`;
- web search: `tests.unit.web_search.*`,
  `tests.test_server_chat_web_runtime_contract`;
- observabilite: `tests.unit.logs.*`,
  `tests.test_server_admin_dashboard_contract`,
  `tests.test_server_chat_compact_observability_contract`;
- frontend: `app/tests/unit/frontend_chat/*.js`,
  `tests.integration.frontend_browser.*`,
  `tests.integration.frontend_admin.*`;
- Agenda: `tests.unit.agenda.*`,
  `tests.test_server_chat_agenda_contract`,
  `tests.test_server_admin_agenda_observability_contract`;
- Biblio: `tests.unit.biblio.*`,
  `tests.test_server_chat_biblio_contract`;
- Memory/Admin identity: `tests.unit.memory.*`,
  `tests.unit.admin.*`, `tests.test_server_admin_identity_*`,
  `tests.test_server_admin_memory_surface_phase10e`.

## Gaps de readiness

Les tests couvrent beaucoup de contrats cibles, mais Lot 9 manque encore:

- une route map snapshot stable de `server.py`, avec classifications par
  famille de routes et gardes attendues;
- des fixtures golden content-free pour `chat_service.py` prouvant l'ordre des
  lanes, final locks, overrides, persistence et manifest;
- une matrice web qui distingue explicit URL, SearXNG no results, upstream
  error, discovery error, Crawl4AI/PDF failure et observabilite;
- une matrice writer-side guard par stage legitimement accepte et payload
  dangereux refuse;
- des snapshots read-model content-free couvrant Memory/Web/Documents/Biblio/
  Agenda/Hermeneutic sur le meme tour synthetique;
- un smoke frontend load-order pour les scripts globaux non-module avant toute
  modularisation;
- des golden tests Agenda/Biblio fake/local qui figent les methodes produit sans
  rouvrir les chantiers riches;
- un critere de sortie empechant Lot 9 de devenir un refactor infini.

## Decision

Lot 9 est pret pour une TODO de refactor, pas pour du code. Le premier lot
operationnel doit etre `Lot 9.0 - golden test harness / preuve avant refactor`.

Tout patch runtime Lot 9 doit:

- citer le sous-lot cible;
- ajouter ou lancer les golden tests prealables;
- extraire une seule responsabilite;
- conserver les contrats content-free;
- ne pas creer `utils.py` / `helpers.py`;
- s'arreter si un P1/P2 comportemental nouveau apparait, pour le traiter hors
  refactor structurel.
