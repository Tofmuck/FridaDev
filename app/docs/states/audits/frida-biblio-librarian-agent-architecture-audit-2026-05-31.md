# Audit Biblio / Catalogue et architecture agent bibliothecaire

Date: 2026-05-31
Statut: audit source
Classement: `app/docs/states/audits/`
Portee: plateforme Catalogue/OCR sur OVH, code FridaDev Biblio, repros live content-free, proposition d'agent bibliothecaire.
Patch runtime: aucun.
Patch plateforme: aucun.
DB/OCR: aucune ecriture, aucun OCR lance.

## 1. Plan

Existe-t-il un meilleur plan ?

Oui. Le meilleur plan est de traiter le sujet en deux passes:

1. cartographier la plateforme Catalogue et le wiring FridaDev en lecture seule, avec mesures content-free et timeouts larges;
2. seulement ensuite relier les repros produit aux limites d'architecture, puis proposer une couche agentique qui conserve Catalogue comme source de verite et reutilise les modules existants comme outils.

Ce plan est meilleur qu'un patch immediat parce que les echecs observes ne sont pas un seul bug local: ils viennent du couplage entre recherche lexicale, parsing deterministe, absence d'etat Biblio de conversation et routes Catalogue de poids tres different.

Note modele: GPT-5.5 n'etait pas selectionnable dans cette session Codex. L'audit a donc ete conduit avec le meilleur Codex disponible dans l'environnement courant.

## 2. Synthese brutale

Biblio est techniquement serieuse, mais pas encore une bibliothecaire produit.

Ce qui est solide:

- le client FridaDev est structurellement GET-only;
- le toggle off evite bien toute construction de client Catalogue et tout appel;
- la lane Biblio est separee des documents actifs, Memory/RAG, Web, Identity, Summary et Hermeneutic;
- l'observabilite ordinaire reste content-free dans les smokes et projections inspectees;
- Catalogue a une vraie DB: 10 documents, 101421 paragraphes, 378034 raw units, 973 chapitres, 26492 milestones;
- la route legere `GET /doc/{id}/chapters` existe et fonctionne vite;
- les routes `/search`, `/context`, `/page` et `/export/chunk` prouvent que le fonds peut etre consulte plus richement que ce que FridaDev exploite aujourd'hui.

Ce qui casse le produit:

- FridaDev raisonne principalement sur le dernier message utilisateur; il n'a pas d'etat Biblio multi-tour;
- le planner deterministe rate des formulations naturelles centrales;
- la recherche est encore trop lexicale et trop locale;
- les demandes "autour de ce resultat", "page precedente", "table des matieres ?" apres un tour precedent ne sont pas reprises;
- la route `/doc/{id}` est presente mais lourde et inadaptable a un usage runtime;
- FridaDev ne sait pas demander `/page`, `/export/chunk` ou une recherche document-scoped, meme quand Catalogue peut techniquement fournir la matiere;
- l'ambiguite est souvent honnete, mais pas active: le systeme ne sait pas iterer, reformuler, verifier ou demander une precision comme le ferait une bibliothecaire.

Decision d'audit: NO-GO produit pour "Frida a une bibliotheque devant les yeux". GO technique pour un socle d'outils GET-only a transformer en agent bibliothecaire borne.

## 3. Cartographie plateforme

### Conteneurs et exposition

Conteneurs observes:

- `platform-doc-pipeline-api`: FastAPI Catalogue, up, non publie directement en port host;
- `platform-doc-pipeline-db`: PostgreSQL 16, healthy;
- `platform-doc-library`: UI statique Catalogue, nginx, montee en lecture seule;
- `platform-doc-pipeline`: worker OCR/SQL idle, `sleep infinity`, declenche par n8n via `docker exec`;
- `platform-fridadev`: app FridaDev, healthy.

Caddy:

- `home.frida-system.fr` importe Authelia;
- `/bibliotheque*` reverse proxy vers `doc-library:80`;
- `/doc-api*` reverse proxy vers `doc-pipeline-api:8090`;
- aucune exposition directe host de `platform-doc-pipeline-api` n'a ete observee.

Volumes:

- API et worker montent `/opt/platform/data/nextcloud/data/tof/files` vers `/data`;
- API et worker montent `/opt/platform/doc-pipeline/data/config` vers `/app/data/config`;
- worker monte aussi `/opt/platform/doc-pipeline/logs` vers `/app/runtime-logs`;
- DB monte `/opt/platform/doc-pipeline/data/postgres`;
- UI `doc-library` monte `/opt/platform/doc-library` en lecture seule.

### OCR / ingestion

Flux observe dans `process_document.py` et la documentation plateforme:

1. entree attendue: `/data/OCR/job_to_do/<name>.pdf` ou `.epub`;
2. phase `ocr_pdf`: PDF searchable detecte et OCR image saute si `DOC_PIPELINE_OCR_TEXT_MODE=skip`, sinon OCR PDF;
3. phase `hocr_extract`: hOCR par page PDF ou extraction sections EPUB;
4. phase `parse_layout`: paragraphes, notes, TOC;
5. phase `markdown_llm`: structuration Markdown LLM si le pre-QA ne permet pas de sauter;
6. phase `json_qa`: QA JSON indicative;
7. phase `sql_insert`: insertion SQL;
8. phase `write_outputs`: artefacts dans `job_done`;
9. phase `cleanup_input`: retrait de l'entree traitee.

Etat live:

- `/progress`: `active_count=0`, `recent_count=11`, dernier statut recent `done`;
- `job_to_do`: 0 fichier;
- `job_failed`: 0 fichier;
- `job_done`: 25 fichiers, dont 10 `.json`, 10 `.md`, 5 `.pdf`;
- logs OCR: 13 fichiers `.log`;
- aucun OCR n'a ete lance pendant l'audit.

### DB Catalogue

Tables publiques:

- `documents`;
- `pages`;
- `paragraphs`;
- `raw_units`;
- `milestones`;
- `document_chapters`;
- `catalogue_human_metadata`;
- `catalogue_human_metadata_audit`;
- `schema_migrations`.

Compteurs live:

| table | count |
| --- | ---: |
| documents | 10 |
| pages | 4837 |
| paragraphs | 101421 |
| raw_units | 378034 |
| milestones | 26492 |
| document_chapters | 973 |
| catalogue_human_metadata | 10 |
| catalogue_human_metadata_audit | 18 |

Extensions:

- `plpgsql` uniquement.

Indexes utiles observes:

- `idx_paragraphs_fts`;
- `idx_pages_doc_page`;
- `idx_paragraphs_doc_page_para`;
- `idx_raw_units_doc_page_para`;
- `idx_milestones_lookup`;
- `idx_milestones_doc_page_para`;
- `idx_document_chapters_doc_no`;
- `idx_document_chapters_doc_unit`.

Qualite metadata:

- 10 documents ont une metadata humaine `validated`;
- 9 documents ont un titre canonique humain;
- 10 documents ont des auteurs humains;
- 0 note operateur non vide observee;
- 5 sources `epub`, 5 sources `pdf`;
- TOC: 5 `epub_toc`, 4 `llm_fallback`, 1 `pdf_outline`.

Limite DB/search importante:

- pas d'extension `unaccent`;
- pas de `pg_trgm`;
- la recherche `/search` repose sur `to_tsvector('simple', p.text)` puis fallback `ILIKE`;
- les recherches sans accents ou paraphrasees peuvent tomber a 0 resultat alors que des recherches reformulees trouvent un passage.

### API Catalogue

Routes observees via `openapi.json` et `query_api.py`.

Routes GET legeres utiles:

- `/health`;
- `/catalog`;
- `/doc/{doc_id}/metadata`;
- `/doc/{doc_id}/chapters`;
- `/doc/{doc_id}/locate`;
- `/doc/{doc_id}/milestones`;
- `/doc/{doc_id}/context`;
- `/doc/{doc_id}/page/{page_no}`;
- `/doc/{doc_id}/page/{page_no}/para/{para_no}`;
- `/search`.

Routes `latest` a eviter cote futur agent:

- `/doc/latest/page/{page_no}`;
- `/doc/latest/context`.

Lecture source plateforme du 2026-05-31: ces routes passent encore par `doc_latest()` ou `get_latest_document_overview()` avant de resoudre le document. Le futur agent ne doit donc pas utiliser `latest/page` ou `latest/context`: il doit resoudre un `document_id` explicite avant toute lecture de page ou de contexte. Si l'usage `latest/page` ou `latest/context` devient necessaire, ce sera un micro-lot Sauron separe pour les alleger comme `/doc/latest/chapters`, sans patch plateforme dans ce lot FridaDev.

Routes GET lourdes ou a borner:

- `/doc/{doc_id}`;
- `/doc/{doc_id}/export`;
- `/doc/{doc_id}/export.txt`;
- `/doc/{doc_id}/export/chunk`;
- routes export chapitre et by-title.

Routes mutatrices:

- `PUT /settings`;
- `POST /settings/reset`;
- `POST /progress/recent/clear`;
- `PUT /doc/{doc_id}/metadata`;
- `DELETE /doc/{doc_id}`;
- `DELETE /doc/{doc_id}/with-files`.

Mesures live content-free, timeout de sonde 60 s:

| route | resultat |
| --- | --- |
| `/health` | 200, env. 11 ms |
| `/catalog?limit=500` | 200, 10 items, env. 21 ms |
| `/catalog?q=Kant` | 200, 1 item, env. 17 ms |
| `/catalog?q=Platon` | 200, 1 item, env. 20 ms |
| `/search?q=Sapere+aude` | 200, 2 resultats, env. 17-32 ms |
| `/search?q=courage de te servir de ton propre entendement` | 200, 0 resultat, env. 633-752 ms |
| `/search?q=minorite usage entendement` | 200, 1 resultat, env. 17-18 ms |
| `/search?q=maieutique` sans accent | 200, 0 resultat, env. 606-740 ms |
| `/search?q=accouchement des ames` | 200, 0 resultat, env. 623-684 ms |
| `/doc/{kant}/chapters?limit=1000` | 200, 692 chapitres, env. 16-17 ms |
| `/doc/{platon}/chapters?limit=1000` | 200, 10 chapitres, env. 15 ms |
| `/doc/{kant}` | 200, 212621 bytes, env. 10.0 s |
| `/doc/{platon}` | 200, 16592 bytes, env. 58.5 s |
| `/doc/{kant}/export/chunk?max_chars=12000` | 200, texte 11501 chars, env. 226 ms |
| `/doc/{platon}/export/chunk?max_chars=12000` | 200, texte 11452 chars, env. 178 ms |
| `/doc/{platon}/locate?label=126b` | 200, `match_count=14`, env. 16-18 ms |
| `/doc/{kant}/context` depuis resultat `Sapere aude` | 200, 529 chars, env. 15 ms |
| `/doc/{kant}/page/{p-1,p,p+1}` autour d'un resultat | 200, env. 16-21 ms, pages 252 a 17408 chars bruts |

Lecture des mesures:

- `/doc/{id}` est present mais inadaptable comme route runtime generale;
- `/chapters`, `/context`, `/page`, `/export/chunk` sont des briques utiles;
- `/page` peut renvoyer une page tres large et doit etre bornee cote FridaDev avant injection;
- `/export/chunk` est rapide mais doit rester hors injection automatique de bibliotheque entiere;
- `/search` est rapide quand le tsvector trouve, mais certaines requetes vides prennent env. 600-750 ms.

### UI Catalogue

UI observee dans `/bibliotheque`:

- liste des ouvrages;
- recherche metadata/catalogue;
- compteurs docs, unites, chapitres, paragraphes;
- fiche metadata;
- edition metadata humaine via `PUT /doc/{id}/metadata`;
- liens `Fiche JSON` et `Page 1 JSON`;
- zone de suppression DB ou DB + fichiers, avec retape de l'identifiant complet.

Gaps UI:

- pas de visualisation TOC native dans la fiche, seulement `chapter_count`;
- pas de recherche passage dans l'UI;
- les routes destructrices sont dans la meme surface operator que la consultation;
- pas de separation visible lecteur vs administrateur destructeur.

## 4. Cartographie FridaDev

### Wiring chat

Flux observe:

- `app/web/chat_biblio_mode.js` persiste le toggle dans `localStorage` et envoie `biblio_enabled`;
- `app/core/chat_service.py` appelle `run_biblio_chat_turn(data, user_msg=dernier message)`;
- l'observabilite Biblio est emise avant l'injection prompt;
- `inject_biblio_prompt_lane()` insere la lane avant le dernier message user;
- `app/server.py` expose `/api/admin/biblio/observability`;
- le read-model dashboard sait resumer Biblio content-free.

Invariant verifie:

- toggle off: `enabled=False`, `used=False`, reason `biblio_toggle_disabled`, `client_event_count=0`.

### Modules

Tailles observees:

| module | lignes |
| --- | ---: |
| `catalogue_client.py` | 652 |
| `document_resolver.py` | 634 |
| `library_runtime.py` | 524 |
| `observability.py` | 687 |
| `passage_candidate_search.py` | 472 |
| `passage_context_search.py` | 663 |
| `passage_extractor.py` | 573 |
| `passage_selection.py` | 211 |
| `prompt_lane.py` | 330 |
| `query_normalizer.py` | 263 |
| `query_planner.py` | 652 |
| `smoke_live.py` | 259 |
| `table_of_contents_runtime.py` | 338 |
| `work_resolver.py` | 243 |

Lecture architecture:

- les responsabilites sont plutot separees par fichier;
- mais quatre fichiers depassent nettement la limite de vigilance 500-600 lignes;
- la complexite locale vient surtout du fait que le planner et les resolvers tentent de simuler une bibliothecaire sans etat ni boucle d'outils;
- ajouter encore des regex dans `query_planner.py` aggravera le probleme.

### Client Catalogue FridaDev

Points forts:

- refus structurel de tout verbe non GET;
- allowlist de routes;
- erreurs structurees et content-free;
- observabilite sans payload brut;
- bornes de parametres numeriques.

Limites:

- timeout runtime par defaut: 8 s, alors que `/doc/{id}` peut prendre 10 s a 58 s en live;
- `document()` reste allowliste alors que `/doc/{id}` est trop lourd pour un usage chat;
- pas d'allowlist actuelle pour `/page`, `/milestones`, `/export/chunk`, donc FridaDev ne peut pas servir page precedente/suivante ou extraction par chunk meme si Catalogue le peut;
- pas de notion de budget d'agent, seulement des appels par branche deterministe.

### Prompt lane et observabilite

Points forts:

- les passages bruts ne sortent que dans la lane produit;
- les smokes stricts indiquent `payload_objects_retained=0` et `raw_marker_leaks=false`;
- dashboard/read-model utilisent ids courts, hashes, longueurs, statuts, reason codes.

Risque:

- les lanes de consultation peuvent devenir tres grandes: TOC Kant a produit `lane_chars=43278`;
- cette taille est inferieure au max technique de `prompt_lane`, mais peut polluer un tour chat et doit etre decidee par budget d'agent, pas par simple branche TOC.

### Tests

Couverture existante:

- unitaires client, resolver, extractor, prompt lane, planner, context search, selection, smoke;
- contrat serveur: injection lane et event content-free;
- dashboard/read-model Biblio content-free;
- smokes live content-free.

Gaps tests:

- pas de vrai scenario multi-tour Biblio avec reprise d'un resultat precedent;
- pas de test "Sapere aude dans Kant" qui doit separer expression et document;
- pas de test "Dans Kant, trouve le passage sur..." qui doit inverser document et theme;
- pas de test "page precedente/suivante" apres resultat;
- pas de test "table des matieres ?" apres un document mentionne au tour precedent;
- peu de tests sur budgets agentiques et retries.

## 5. Repros live FridaDev

Execution: `platform-fridadev`, runtime Biblio reel, timeout Catalogue explicite 60 s pour l'audit, retours content-free.

| cas | status | reason | lecture |
| --- | --- | --- | --- |
| liste ouvrages | `listed` | `biblio_catalog_listed` | OK, 10 ids courts, 1 appel catalog |
| `C'est tout ?` | `listed` | `biblio_catalog_listed` | OK pour fonds actuel; pas une vraie continuation paginee |
| combien d'ouvrages | `listed` | `biblio_catalog_listed` | OK |
| `Tu as la table des matieres ?` sans cible | `ambiguous` | `biblio_document_ambiguous` | pas de reprise de document precedent |
| table des matieres Kant | `toc_listed` | `biblio_table_of_contents_listed` | OK mais lane 43278 chars |
| `Ouvre Platon et montre-moi les parties` | `not_used` | `biblio_no_bibliographic_signal` | echec planner |
| `Cherche Sapere aude dans Kant` | `not_found` | `biblio_context_not_found` | echec planning/requete, alors que Catalogue trouve `Sapere aude` |
| expression longue "courage..." | `not_found` | `biblio_context_not_found` | besoin de reformulation/iteration |
| passage autour de ce resultat | `not_used` | `biblio_no_bibliographic_signal` | absence d'etat de resultat |
| page precedente/suivante | `not_used` | `biblio_no_bibliographic_signal` | absence d'etat + client sans `/page` |
| Theetete maieutique | `ambiguous` | `biblio_context_candidates_ambiguous` | recherche reelle, 8 candidats, 3 contextes, pas de choix |
| Platon accouchement des ames | `not_found` | `biblio_context_not_found` | besoin de decomposition/requetes alternatives |
| Kant minorite/usage entendement | `not_found` | `biblio_context_not_found` | platform trouve une requete reformulee, FridaDev non |
| multi-tour T1 -> T4 | T2/T3 `not_used`, T4 `ambiguous` | n/a | pas d'etat Biblio conversationnel exploite |

## 6. Findings

### P0

Aucun P0 confirme.

Pas d'exposition non authentifiee observee pour `/doc-api` ou `/bibliotheque`: Caddy applique Authelia sur le hostname Home. FridaDev ne fait pas de PUT/POST/DELETE vers Catalogue.

### P1

P1-BIBLIO-01 - Absence d'etat Biblio multi-tour.

Le runtime Biblio recoit seulement `user_msg`. Il ne recoit ni dialogue recent structure, ni dernier document ouvert, ni dernier resultat, ni derniere position. Les demandes "ce resultat", "tout le passage", "page precedente" ou "table des matieres ?" apres un tour precedent echouent ou deviennent ambigues.

P1-BIBLIO-02 - Parser deterministe insuffisant sur des formulations centrales.

`Ouvre Platon et montre-moi les parties` tombe en `no_signal`. `Cherche Sapere aude dans Kant` et `Dans Kant, trouve le passage sur la minorite...` tombent en `not_found` alors que Catalogue possede des signaux consultables.

P1-BIBLIO-03 - Recherche lexicale sans iteration bibliothecaire.

Catalogue trouve `Sapere aude` et une reformulation courte autour de la minorite/entendement. FridaDev n'essaie pas de separer document, oeuvre, theme et expression, puis de relancer des variantes. Il execute une seule branche.

P1-BIBLIO-04 - Page precedente/suivante impossible cote FridaDev.

Catalogue expose `/doc/{id}/page/{page_no}` et les mesures prouvent que les pages voisines sont accessibles. Le client FridaDev ne l'allowliste pas et le runtime ne conserve pas la position precedente.

P1-BIBLIO-05 - Routes destructrices Catalogue dans la meme surface operator que la lecture.

`DELETE /doc/{id}` et `DELETE /doc/{id}/with-files` sont exposes sous `/doc-api`, et l'UI `/bibliotheque` contient des boutons de suppression. C'est protege par Authelia et confirmation id complet, donc pas P0 observe, mais la frontiere lecteur/admin destructeur reste trop faible pour une bibliotheque appelee a devenir centrale.

### P2

P2-BIBLIO-01 - `/doc/{id}` est trop lourd pour rester une primitive runtime.

Mesures: env. 10 s pour Kant, env. 58.5 s pour Platon, avec timeout runtime FridaDev par defaut a 8 s. Toute logique qui reutilise `client.document()` en chat risque de conclure a tort a une indisponibilite.

P2-BIBLIO-02 - Le timeout Catalogue runtime FridaDev est plus petit que certaines routes reelles.

Le timeout de config courant expose par l'admin Biblio est 8 s. L'audit a utilise 60 s pour ne pas confondre lenteur et absence. Les futures routes d'agent doivent definir des timeouts par outil, pas un seul timeout court.

P2-BIBLIO-03 - Recherche Catalogue accent-sensitive.

La DB n'a pas `unaccent`. Les recherches directes `maieutique`, `Theetete`, `accouchement des ames` peuvent tomber a 0 alors que des formes accentuees ou reformulees trouvent des candidats.

P2-BIBLIO-04 - Lane TOC trop volumineuse.

La TOC Kant injecte 43278 chars. C'est techniquement autorise aujourd'hui mais trop gros pour une action "tu as la table des matieres ?" sans budget conversationnel explicite.

P2-BIBLIO-05 - Plusieurs modules Biblio sont a la limite de maintenabilite.

`catalogue_client.py`, `document_resolver.py`, `observability.py`, `passage_context_search.py`, `query_planner.py` depassent ou frolent les limites de vigilance. Continuer par regex et fonctions locales poussera vers un grab-bag.

P2-BIBLIO-06 - Pas de recherche document-scoped dans l'API.

`/search` ne prend pas `doc_id`, `author`, `work`, ni filtre metadata. Le runtime doit filtrer/ranker apres coup. Une route optionnelle `GET /search?doc_id=...&q=...` ou un outil agent qui filtre strictement les resultats serait plus fiable.

### P3

P3-BIBLIO-01 - `app/config.py` et `app/config.example.py` disent encore que le client Biblio n'est pas branche au chat.

Le commentaire est stale: le chat, le frontend et l'admin observability sont branches.

P3-BIBLIO-02 - UI Catalogue ne montre pas encore la TOC ou la recherche passage.

Elle montre les compteurs et la fiche metadata, mais pas une experience bibliothecaire humaine complete.

P3-BIBLIO-03 - README/doc historiques parlent de validations requalifiees et de GO conditionnel; ce nouvel audit doit devenir le point d'entree courant.

## 7. Trous fonctionnels

- reprise de resultat precedent;
- page precedente/suivante;
- table des matieres du document courant sans redemander;
- recherche dans un ouvrage deja mentionne;
- extraction autour d'une expression suivie de "tout le passage";
- decomposition de paraphrase;
- iteration de requetes;
- desambiguisation active;
- citation avec position stable;
- budget explicite par action;
- journal technique content-free par etape d'agent.

## 8. Pourquoi le systeme actuel ne suffit pas

Le systeme actuel est une chaine deterministe: message unique -> regex/planner -> branche runtime -> un petit nombre d'appels GET -> lane.

Une bibliothecaire doit faire autre chose:

- se souvenir de ce qui vient d'etre ouvert;
- essayer plusieurs formulations;
- changer d'outil quand une recherche ne trouve rien;
- verifier un resultat avec `/context`;
- demander une page voisine;
- choisir entre plusieurs passages ou declarer l'ambiguite;
- expliquer qu'un passage est introuvable parce que l'OCR/search ne l'indexe pas, pas parce que l'oeuvre n'existe pas;
- produire une sortie structuree que Frida peut transformer en reponse naturelle.

La solution n'est pas de remplacer les modules livres. La solution est de les transformer en outils d'une couche agentique bornee.

## 9. Architecture cible: agent bibliothecaire

### Principes

- Catalogue reste source de verite.
- FridaDev reste client GET-only.
- Les modules existants deviennent des outils.
- L'agent recoit le dialogue recent Biblio, pas seulement la derniere phrase.
- L'agent a un etat Biblio leger: document courant, dernieres recherches, positions, passages retenus, ambiguites.
- L'agent itere avec budget explicite.
- Les contenus bruts ne sortent que dans la lane produit destinee a Frida.
- Dashboard/logs/admin restent content-free.
- Pas de DB write Catalogue.
- Pas de route destructive.
- Pas de Memory/RAG documentaire global.
- Pas d'injection de toute la bibliotheque.

### Outils proposes

Outils FridaDev existants a conserver:

- `catalogue_health`;
- `list_catalog`;
- `resolve_document`;
- `open_document_summary`;
- `list_chapters`;
- `locate_milestone`;
- `search_passages`;
- `fetch_context`;
- `rank_candidates`;
- `build_prompt_lane`;
- `build_observability`.

Outils a ajouter ou etendre:

- `fetch_page`: GET `/doc/{id}/page/{page_no}`, avec `document_id` explicite, `max_chars` et hash content-free; jamais `latest/page`;
- `fetch_export_chunk`: GET `/doc/{id}/export/chunk`, uniquement sur demande explicite d'ouverture/extrait long, jamais automatique;
- `search_with_document_scope`: wrapper qui filtre strictement par doc id en attendant une route Catalogue `doc_id`;
- `query_rewrite_variants`: outil non souverain qui produit 3 a 8 variantes, avec hashes en observabilite;
- `biblio_state_read` et `biblio_state_update`: etat conversationnel leger;
- `clarify_question`: sortie structuree quand plusieurs documents/passages restent plausibles.

### Etat Biblio conversationnel explicite

Stockage propose:

- Lot 1 doit introduire un etat Biblio interne explicite par conversation, meme leger;
- le dialogue recent aide l'agent a interpreter la demande, mais il n'est pas la source des references techniques de reprise;
- l'etat doit porter les references que le dialogue visible ne garantit pas: `document_id`, `page_no`, `para_no`, `paragraph_id`, dernier passage trouve et dernier resultat exploitable;
- l'observabilite reste content-free: ids courts, positions, hashes, longueurs et reason codes seulement;
- une V2 persistante legere peut etre ajoutee si l'etat doit survivre au runtime, mais le contrat Lot 1 ne doit pas rester seulement derive du dialogue recent.

Champs autorises:

```json
{
  "schema_version": "biblio_state_v1",
  "current_document": {
    "doc_id_short": "62db0e10",
    "document_id": "internal-only",
    "label_hash": "sha256_12",
    "source": "catalogue"
  },
  "last_result": {
    "doc_id_short": "62db0e10",
    "page_no": 468,
    "para_no": 3,
    "paragraph_id": 9324,
    "passage_hash": "94329db0cb4d",
    "passage_chars": 529
  },
  "last_action": "search_passage",
  "ambiguous": false,
  "updated_turn_id": "internal"
}
```

Surfaces admin/logs ne doivent voir que ids courts, positions, hashes, longueurs, statuts.

### Sortie JSON stricte de l'agent

```json
{
  "schema_version": "biblio_librarian_agent_v1",
  "status": "answered|ambiguous|not_found|error|needs_clarification",
  "reason_code": "string_token",
  "intent": "list_catalog|open_document|toc|search_passage|extract_context|neighbor_pages|export_chunk|clarify",
  "document": {
    "resolved": true,
    "doc_id_short": "62db0e10",
    "title_for_prompt": "optional product lane only"
  },
  "results": [
    {
      "result_id": "r1",
      "doc_id_short": "62db0e10",
      "page_no": 468,
      "para_no": 3,
      "paragraph_id": 9324,
      "passage": "product lane only",
      "passage_chars": 529,
      "passage_hash": "94329db0cb4d",
      "confidence": "low|medium|high",
      "limits": ["bounded_context"]
    }
  ],
  "clarification": {
    "question_for_frida": "",
    "choices": []
  },
  "observability": {
    "tool_calls": [],
    "endpoint_kinds": [],
    "query_hashes": [],
    "doc_id_shorts": [],
    "durations_ms": [],
    "raw_content_included": false
  }
}
```

### Lane prompt pour Frida

La lane doit contenir:

- contrat d'interpretation;
- statut et limites;
- document/passage utiles au produit;
- passages bruts bornes si l'utilisateur les demande;
- position page/paragraphe;
- ambiguite ou question de clarification.

La lane ne doit pas contenir:

- payload Catalogue complet;
- texte de tout l'ouvrage;
- secrets;
- journal technique complet;
- routes destructrices.

### Budgets cibles

Par tour:

- 12 appels outils max en nominal;
- 20 appels max si l'utilisateur demande explicitement une recherche large;
- 3 requetes `/search` initiales, puis 5 variantes max en retry;
- 5 contextes candidats max;
- 3 pages voisines max par demande;
- 1 export chunk max par tour, 12000 chars max;
- 8000 chars max de passages injectes par defaut;
- 50000 chars max pour TOC seulement si l'utilisateur demande explicitement la table complete;
- timeout outil rapide: 10 s;
- timeout route lourde: 60 s;
- stop immediat sur route mutatrice ou hors allowlist.

### Observabilite

Journal technique content-free:

- `agent_status`;
- `intent`;
- `tool_call_count`;
- endpoint kinds;
- durees;
- status HTTP;
- doc ids courts;
- query hashes;
- positions;
- passage hashes/longueurs;
- decisions de selection;
- budget consumed;
- reason codes.

Interdit:

- passage brut;
- page brute;
- prompt complet;
- payload complet;
- requete utilisateur brute;
- titre/auteur brut dans surfaces techniques ordinaires.

## 10. Plan par lots

Lot 0 - Stabiliser cet audit.

- livrer cette note;
- l'indexer;
- ne pas patcher runtime.

Lot 1 - Etat Biblio conversationnel minimal.

- ajouter un objet d'etat leger par conversation;
- conserver dernier document, derniere position, dernier passage hash;
- tests multi-tour obligatoires.

Lot 2 - Outils GET-only manquants.

- ajouter wrapper page voisine borne;
- ajouter wrapper export chunk borne;
- ajouter recherche document-scoped cote FridaDev ou route Catalogue GET optionnelle;
- timeouts par outil.

Lot 3 - Agent bibliothecaire V1.

- planner LLM ou boucle outillee avec JSON strict;
- budget max;
- retries/reformulations;
- desambiguisation;
- sortie structuree.

Lot 4 - Migration du runtime.

- `chat_runtime` appelle l'agent quand `biblio_enabled=true`;
- modules actuels restent outils;
- ancien planner garde un mode fallback;
- feature flag operator.

Lot 5 - Observabilite et dashboard.

- projections content-free agent;
- compteur budgets;
- reason codes nouveaux;
- alertes lenteur/ambiguite/not_found.

Lot 6 - Validation produit.

- matrice multi-tour live;
- tests unitaires agent avec faux Catalogue;
- smokes live content-free;
- non-regression GET-only et toggle off.

Rollback:

- feature flag `BIBLIO_LIBRARIAN_AGENT_ENABLED=0`;
- retour a `run_biblio_library_plan`;
- aucun changement DB Catalogue necessaire;
- aucun rebuild plateforme sauf nouvelle route Catalogue explicite.

## 11. Tests et preuves executees

Commandes/preuves:

- `git fetch origin main && git pull --ff-only origin main && git status --short`;
- lecture `AGENTS.md`, spec Biblio, docs Biblio archivees, `git log --oneline -20`;
- lecture des modules `app/biblio/*`;
- `docker ps`;
- `docker inspect ... --format '{{json .Mounts}}'`;
- lecture `query_api.py`, `db_store.py`, `process_document.py`, `doc-library/index.html`, Caddy;
- DB content-free via `psql` dans `platform-doc-pipeline-db`;
- routes Catalogue via `openapi.json`;
- mesures live Catalogue avec timeout 60 s;
- smokes Biblio stricts `python -m biblio.smoke_live --jsonl`;
- smoke Biblio `--no-strict` reserve au diagnostic, pas comme preuve principale;
- repros produit Biblio runtime avec timeout Catalogue 60 s;
- admin observability Biblio content-free;
- logs recents doc-pipeline/doc-pipeline-api filtres erreurs: aucun signal recent imprime.

Limites:

- aucune reponse LLM finale `/api/chat` n'a ete forcee, pour eviter cout et contenu brut inutile;
- l'audit produit repose sur le runtime Biblio qui construit les lanes et sur le wiring code de `chat_service`;
- aucun OCR ou rebuild n'a ete lance.

## 12. Rebuild / runtime

Aucun rebuild.

Aucun restart.

Aucune modification plateforme.

Aucune modification DB.

## 13. Docs creees

Cette note est la nouvelle entree d'audit courant pour Biblio agent bibliothecaire:

`app/docs/states/audits/frida-biblio-librarian-agent-architecture-audit-2026-05-31.md`

Index a tenir a jour dans le meme cycle:

- `AGENTS.md`;
- `README.md`;
- `app/docs/README.md`.

## 14. GO / NO-GO

GO:

- garder le socle Biblio actuel comme outils;
- garder Catalogue source de verite;
- garder GET-only;
- ouvrir un lot agent bibliothecaire borne.

NO-GO:

- declarer que Frida a deja une bibliotheque produit devant elle;
- ajouter seulement des regex au planner;
- utiliser `/doc/{id}` comme route runtime principale;
- exposer plus de contenu brut en observabilite;
- brancher Memory/RAG global;
- autoriser ecriture Catalogue depuis FridaDev;
- lancer OCR ou rebuild dans ce lot d'audit.
