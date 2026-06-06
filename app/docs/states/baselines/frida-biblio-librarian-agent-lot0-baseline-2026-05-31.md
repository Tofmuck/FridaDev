# Frida Biblio librarian agent Lot 0 baseline

Date: 2026-05-31
Statut: baseline Lot 0 validee
Classement: `app/docs/states/baselines/`
Roadmap active: `app/docs/todo-todo/product/frida-biblio-librarian-agent-todo.md`
Audit source: `app/docs/states/audits/frida-biblio-librarian-agent-architecture-audit-2026-05-31.md`
Contrat source: `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
Scope: docs-only, content-free, sans patch runtime, sans modification plateforme, sans rebuild.

## Note modele

Le job demandait le meilleur Codex disponible en mentionnant GPT-5.5. GPT-5.5 n'est pas selectionnable dans cet environnement; cette baseline a ete executee par Codex GPT-5.

## Meilleur plan retenu

Le plan le plus sur pour Lot 0 etait de separer deux preuves:

- baseline runtime FridaDev live strictement content-free;
- matrice Catalogue/API/plateforme live en lecture seule, sous discipline Sauron, sans modification de la stack.

Ce plan reduit le risque de confondre une limite deja presente avec une regression future du futur agent bibliothecaire.

## Sources relues

- `AGENTS.md`
- `README.md`
- `app/docs/README.md`
- `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
- `app/docs/states/audits/frida-biblio-librarian-agent-architecture-audit-2026-05-31.md`
- `app/docs/todo-todo/product/frida-biblio-librarian-agent-todo.md`
- `app/biblio/smoke_live.py`
- `app/biblio/chat_runtime.py`
- `app/biblio/library_runtime.py`
- `app/biblio/catalogue_client.py`

## Smoke strict existant

Commande:

```bash
docker exec -w /app platform-fridadev python -m biblio.smoke_live --jsonl
```

Resultat: exit code `0`.

| Cas smoke | Statut | Reason code | Query kind | Endpoint kinds | Signal content-free |
| --- | --- | --- | --- | --- | --- |
| S1 | `listed` | `biblio_catalog_listed` | `list_catalog` | `catalog` | `client_count=1`, `lane_injected=true`, `lane_chars=1279`, `passage_count=0`, `raw_marker_leaks=false`, `payload_objects_retained=0` |
| S2 | `extracted` | `biblio_passage_lane_ready` | `extract_range` | `catalog`, `search` | `client_count=2`, `lane_chars=7173`, `passage_count=1`, `passage_chars=6534`, `passage_hash=08c1de51a142`, `raw_marker_leaks=false`, `payload_objects_retained=0` |
| S3 | `ambiguous` | `biblio_context_candidates_ambiguous` | `search_catalog` | `context`, `search` | `client_count=12`, `candidate_count=8`, `context_call_count=3`, `selected_count=0`, `passage_count=3`, `raw_marker_leaks=false`, `payload_objects_retained=0` |
| S4 | `ambiguous` | `biblio_context_candidates_ambiguous` | `search_catalog` | `context`, `search` | `client_count=5`, `candidate_count=8`, `context_call_count=3`, `selected_count=0`, `passage_count=3`, `raw_marker_leaks=false`, `payload_objects_retained=0` |
| S5 | `ambiguous` | `biblio_context_candidates_ambiguous` | `search_catalog` | `context`, `search` | `client_count=12`, `candidate_count=8`, `context_call_count=3`, `selected_count=0`, `passage_count=3`, `raw_marker_leaks=false`, `payload_objects_retained=0` |
| S6 | `toc_listed` | `biblio_table_of_contents_listed` | `show_table_of_contents` | `catalog`, `chapters` | `client_count=2`, `lane_chars=1240`, `passage_count=0`, `raw_marker_leaks=false`, `payload_objects_retained=0` |

Endpoint kinds observes dans les smokes: `catalog`, `search`, `context`, `chapters`.

## Matrice produit content-free

Les cas ci-dessous reprennent les cas obligatoires de la roadmap active sous libelles courts, sans requete brute ni passage brut.

| Cas | Statut courant | Reason code | Query kind | Endpoint kinds | Etat Biblio | Diagnostic |
| --- | --- | --- | --- | --- | --- | --- |
| P01 catalog_complete_natural | `extracted` | `biblio_context_passage_extracted` | `search_catalog` | `context`, `search` | absent | Formulation naturelle mal routee: extraction au lieu de liste catalogue. |
| P02 catalog_limit_100 | `listed` | `biblio_catalog_listed` | `list_catalog` | `catalog` | absent | OK pour 10 items live, avec lane bornee. |
| P03 open_known_corpus | `not_used` | `biblio_no_bibliographic_signal` | `no_signal` | aucun | absent | Echec produit: pas d'ouverture ni de `current_document`. |
| P04 toc_known_corpus | `toc_listed` | `biblio_table_of_contents_listed` | `show_table_of_contents` | `catalog`, `chapters` | absent | OK sans etat durable; la reprise du document courant reste non prouvee. |
| P05 thematic_known_dialogue | `extracted` | `biblio_context_passage_extracted` | `search_catalog` | `context`, `search` | absent | OK sur formulation cible; passage hash `1ddf68180f58`. |
| P06 synonym_known_dialogue | `ambiguous` | `biblio_context_candidates_ambiguous` | `search_catalog` | `context`, `search` | absent | Clarification propre, mais pas de reprise d'ouvrage par etat. |
| P07 exact_range_known_dialogue | `not_found` | `document_not_found` | `extract_range` | `catalog` | absent | Fragilite de formulation: le smoke S2 extrait un range equivalent via une autre formulation. |
| P08 continue_after_result | `not_used` | `biblio_no_bibliographic_signal` | `no_signal` | aucun | absent | Echec attendu tant que `last_result` n'existe pas. |
| P09 previous_page | `not_used` | `biblio_no_bibliographic_signal` | `no_signal` | aucun | absent | Echec attendu sans `document_id`/`page_no` et sans outil page cote client. |
| P10 other_close_result | `ambiguous` | `biblio_context_candidates_ambiguous` | `search_catalog` | `context`, `search` | absent | Clarification propre; exclusion/declassement du dernier resultat non prouve. |
| P11 verify_origin | `invalid_request` | `locator_required_for_passage` | `resolve_work` | `search` | absent | Echec attendu sans ancre technique de passage dans l'etat. |

Synthese transverse:

- `state_present=false` pour tous les cas.
- `raw_marker_leaks=false` pour tous les cas.
- `payload_objects_retained=0` pour tous les cas observes.
- Les cas P08 et P11 prouvent directement le besoin Lot 1: etat conversationnel et ancres techniques.
- Les cas P03 et P09 sont des surveillances de regression pour Lot 1, pas des promesses de correction complete: P03 depend aussi du planner/intention, P09 depend aussi d'un outil page non expose par `CatalogueClient`.
- Les cas P01 et P07 prouvent une fragilite de planning deterministe avant agent.

## Matrice Catalogue / API / plateforme

Lecture faite en read-only sous discipline Sauron.

### Conteneurs observes

| Surface | Etat observe |
| --- | --- |
| `platform-fridadev` | up, healthy |
| `platform-fridadev-postgres` | up, healthy |
| `platform-doc-pipeline-api` | up |
| `platform-doc-library` | up |
| `platform-doc-pipeline-info` | up |
| `platform-doc-pipeline` | up |
| `platform-doc-pipeline-db` | up, healthy |

### Health et routes API

| Preuve | Resultat |
| --- | --- |
| `GET /health` | HTTP `200`, environ `0.015s`, content-free |
| OpenAPI | HTTP `200`, `33` routes GET, `6` routes mutantes |
| Routes GET utiles presentes | `/catalog`, `/search`, `/doc/{doc_id}/context`, `/doc/{doc_id}/chapters`, `/doc/{doc_id}/locate`, `/doc/{doc_id}/page/{page_no}`, `/doc/{doc_id}`, `/doc/latest/page/{page_no}` |
| Route specifique absente de l'OpenAPI | `/doc/latest/context`; la forme `latest` peut toutefois etre capturee par une route parametrique ou produire un comportement lourd |
| Routes mutantes exposees cote Catalogue | `DELETE /doc/{doc_id}`, `DELETE /doc/{doc_id}/with-files`, `POST /progress/recent/clear`, `POST /settings/reset`, `PUT /doc/{doc_id}/metadata`, `PUT /settings` |
| Routes mutantes appelees par Lot 0 | aucune |
| OCR / jobs doc-pipeline declenches | aucun |

### Probes API content-free

| Probe | Resultat |
| --- | --- |
| `GET /catalog?limit=100` | HTTP `200`, `10` items, premier id court capture, sans titre/auteur |
| `GET /search` | HTTP `200`, `2` resultats sur sonde bornee, sans extrait |
| `GET /doc/{id}/chapters` | HTTP `200`, `500` items sur sonde bornee |
| `GET /doc/{id}/context` | HTTP `200`, environ `838` caracteres de payload, contenu non affiche |
| `GET /doc/{id}/page/{page_no}` | HTTP `200`, environ `35332` caracteres de payload, contenu non affiche |
| `GET /doc/{id}/locate` | HTTP `404` sur label-sonde neutre, route presente |
| `GET /doc/{id}` | HTTP `200`, environ `10.159s`, environ `211262` caracteres de payload, route lourde a eviter pour l'agent |
| `GET /doc/latest/page/1` | `ReadTimeout` a `15s`, interdit par invariant sans `document_id` explicite |
| `GET /doc/latest/context` | `ReadTimeout` a `15s`; aucune route specifique declaree, forme `latest` probablement capturee par route parametrique ou comportement lourd, interdite sans `document_id` explicite |

### Counts DB content-free

| Table | Count |
| --- | ---: |
| `documents` | 10 |
| `document_chapters` | 973 |
| `pages` | 4837 |
| `paragraphs` | 101421 |
| `raw_units` | 378034 |
| `catalogue_human_metadata` | 10 |

Tables publiques observees: `catalogue_human_metadata`, `catalogue_human_metadata_audit`, `document_chapters`, `documents`, `milestones`, `pages`, `paragraphs`, `raw_units`, `schema_migrations`.

## Findings P0/P1/P2/P3

### P0

Aucun P0 confirme dans Lot 0. Le smoke strict passe, aucune fuite brute n'a ete observee dans les sorties content-free, aucune route mutante n'a ete appelee.

### P1

- Etat conversationnel Biblio absent: P08 et P11 echouent ou se degradent directement parce que `last_result` et ancre technique ne sont pas disponibles.
- Cadrage Lot 1 a borner: P03 depend aussi du planner/intention; P09 depend aussi d'un outil page non expose par `CatalogueClient`. Lot 1 doit preparer les ancres et clarifier proprement si l'etat ou l'outillage manque, sans promettre de corriger tout le planner ni d'ajouter la navigation page complete.
- Planning deterministe fragile sur formulations naturelles: P01 route une demande catalogue vers une extraction, et P07 echoue a retrouver un range alors que S2 prouve qu'un range equivalent peut etre extrait via une autre formulation.
- Navigation bibliotheque non livree: "continuer" et verification d'origine relevent du besoin d'etat; "page precedente" reste a surveiller mais exige aussi un outil page explicite cote client.

### P2

- `CatalogueClient` n'expose pas encore la route page alors que l'API expose `/doc/{doc_id}/page/{page_no}`.
- `/doc/{id}` reste lourd et ne doit pas devenir une strategie agentique par defaut.
- Les chemins `latest/page` et `latest/context` sont dangereux pour FridaDev: `latest/page` est expose, `latest/context` n'est pas declare comme route specifique mais peut etre capture par une route parametrique ou comportement lourd; dans tous les cas, ils violent l'invariant d'un `document_id` explicite et ne doivent jamais etre utilises par l'agent.
- Les routes mutantes existent cote Catalogue; elles doivent rester exclues de l'enveloppe d'outils FridaDev.

### P3

- La baseline Lot 0 manquait avant ce patch; elle est maintenant indexee et rattachee a la roadmap active.
- La verification OpenRouter/JSON reste volontairement non faite: elle appartient a un lot runtime futur, pas a Lot 0.

## Decision Lot 0

Lot 0 est valide.

Go Lot 1: oui, sous conditions:

- maintenir le chemin Biblio actuel disponible tant que l'etat conversationnel n'est pas valide;
- livrer seulement l'etat Biblio conversationnel explicite et les ancres techniques content-free necessaires;
- clarifier proprement quand l'etat, le planner ou l'outillage manque;
- ne jamais utiliser `latest/page` ou `latest/context`;
- ne pas appeler `/doc/{id}` comme strategie de navigation;
- garder P08 et P11 comme criteres centraux de Lot 1;
- garder P03 et P09 comme cas de regression a surveiller, sans promettre de corriger le planner/intention ni d'ajouter l'outil page dans Lot 1;
- ne pas faire deborder Lot 1 vers planner, outil page, navigation complete ou agent bibliothecaire complet.

## Rebuild / live

Aucun rebuild, restart ou changement runtime n'a ete effectue. La preuve live s'est limitee a des lectures API/DB et au smoke FridaDev existant.
