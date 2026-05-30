# Frida Biblio vraie bibliotheque / recherche de passages - validation finale

Date: 2026-05-30
Statut: GO final
Classement: `app/docs/todo-done/validations/`
Roadmap archivee: `app/docs/todo-done/product/frida-biblio-real-library-passage-search-todo.md`
Spec source-of-truth: `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
Commit de cloture: commit d'archivage Lot 8 portant cette note.

## Decision

Le chantier P1 "Biblio vraie bibliotheque" est valide.

Biblio sait maintenant:

- lister les premiers ouvrages Catalogue;
- traiter une demande bibliographique explicite seulement quand `biblio_enabled=true`;
- ne pas construire de client Catalogue quand le toggle est off ou quand le signal bibliographique est absent;
- resoudre des demandes d'extraction explicites, dont le smoke Theetete `126b a 128a`;
- chercher des passages thematiques via `GET /search`, puis valider un top-N borne via `GET /doc/{id}/context`;
- injecter une lane `[PASSAGES DE BIBLIOTHEQUE CONSULTES]` quand un passage extrait ou des passages candidats plausibles existent;
- conserver une ambiguite honnete quand plusieurs contextes restent proches, sans transformer un candidat provisoire en certitude.

## Invariants valides

- FridaDev reste GET-only cote Catalogue.
- Aucun patch plateforme, API Catalogue, DB Catalogue, OCR ou re-OCR n'a ete necessaire.
- Biblio reste separee de `active_document`, workspace, Memory/RAG, Identity, Summary, Web, Hermeneutic, AnythingLLM et OCR des documents actifs.
- Le passage brut est autorise seulement dans la lane prompt produit et les objets internes necessaires a cette lane.
- Logs, admin, dashboard, read-model, smokes et retour technique restent content-free.
- Les objets resultats actifs ne retiennent pas de `CatalogueResponse.payload`.

## Preuves executees

Commandes locales:

```bash
python3 -m py_compile app/biblio/*.py app/core/chat_service.py app/core/chat_llm_flow.py app/server.py
python3 -m unittest discover app/tests/unit/biblio
```

Resultat:

- py_compile: OK;
- unitaires Biblio locaux: 138 tests OK.

Commandes live conteneur:

```bash
docker exec -w /app platform-fridadev python -m unittest discover tests/unit/biblio
docker exec -w /app platform-fridadev python -m unittest \
  tests.test_server_chat_biblio_contract \
  tests.test_server_admin_chat_logs_contract \
  tests.unit.logs.test_dashboard_analytics_lot2 \
  tests.unit.logs.test_dashboard_observable_modules_lot3 \
  tests.unit.logs.test_dashboard_read_model_lot4
docker exec -w /app platform-fridadev python -m biblio.smoke_live --jsonl
```

Resultat:

- unitaires Biblio live: 138 tests OK;
- contrats chat/admin/dashboard/read-model live: 55 tests OK;
- smoke strict: exit 0.

## Smokes live content-free

Cas couverts par le runner strict:

- liste des premiers ouvrages;
- extraction range Theetete `126b a 128a`;
- recherche thematique dans le Theetete;
- recherche theme seul dans la bibliotheque;
- formulation dictee approximative sans accents.

Resultats compacts:

- liste: `status=listed`, `query_kind=list_catalog`, `client_count=1`, `lane_injected=true`, `payload_objects_retained=0`, `raw_marker_leaks=false`;
- range: `status=extracted`, `query_kind=extract_range`, `passage_count=1`, `lane_injected=true`, `payload_objects_retained=0`, `raw_marker_leaks=false`;
- thematique: `status=ambiguous`, `query_kind=search_catalog`, `candidate_count=8`, `context_call_count=3`, `selected_count=0`, `passage_count=3`, `lane_injected=true`, `payload_objects_retained=0`, `raw_marker_leaks=false`.

Les sorties de smoke ne contiennent pas les formulations utilisateur, titres, auteurs, locators, passages, payloads Catalogue, prompts complets, cookies, tokens ou DSN.

## Risques restants acceptes

- Les recherches thematiques peuvent rester `ambiguous` quand plusieurs contextes plausibles sont proches. C'est le comportement voulu: l'ambiguite est preferee a une citation faussement certaine.
- Le ranking reste deterministe et lexical/structurel. Une recherche semantique plus large, un planner LLM bibliothecaire ou un RAG documentaire global restent hors scope et exigeraient un nouveau lot explicite.
- La qualite depend des metadonnees et positions disponibles dans Catalogue. FridaDev ne corrige pas Catalogue, ne lance pas OCR et ne backfill pas.

## Reouverture future

Ouvrir un nouveau chantier explicite avant tout changement touchant:

- ecriture Catalogue ou edition de metadonnees depuis FridaDev;
- nouvelle route Catalogue;
- OCR/re-OCR;
- recherche semantique large;
- RAG documentaire;
- UI Catalogue FridaDev;
- affichage admin/dashboard de contenu d'ouvrage;
- modification des frontieres avec documents actifs, Memory/RAG, Web, Identity, Summary ou Hermeneutic.
