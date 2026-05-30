# Validation finale Biblio native / Frida Catalogue - 2026-05-29

Statut: valide et archive
Roadmap archivee: `app/docs/todo-done/product/frida-biblio-native-catalogue-todo.md`
Audit-plan archive: `app/docs/todo-done/product/frida-biblio-native-catalogue-audit-plan.md`
Spec source-of-truth: `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`

## Verdict

Le chantier Biblio native est clos apres les Lots 0 a 8.

FridaDev sait, sur toggle explicite, detecter une demande bibliographique conservatrice, consulter le Catalogue via client GET-only, resoudre un document et un locator, extraire un passage borne, formater une lane prompt dediee et emettre une observabilite content-free.

## Corrections finales Lot 8

- Parsing oral: `126b de l Apologie` est nettoye en titre `Apologie`, sans casser `126b de la Republique`.
- Parsing range: `126b -> 126e` ne laisse plus `->` dans le titre.
- Les ranges restent non extraits par contrat: l'extracteur retourne `range_extraction_not_supported` au lieu d'extraire silencieusement un debut.

## Invariants revus

- Biblio reste separee des documents actifs, du workspace, de Memory/RAG, Identity, Summary, Web, Hermeneutic, AnythingLLM et de l'OCR ponctuel des documents actifs.
- Le client Catalogue FridaDev reste GET-only: pas de DELETE, PUT, POST, ecriture DB Catalogue, suppression, OCR ou backfill.
- Toggle off: aucun client Catalogue construit.
- Toggle on sans signal bibliographique clair: aucun client Catalogue construit.
- Toggle on avec signal clair: resolution/extraction bornee possible.
- La lane est injectee seulement si un passage est extrait.
- Le passage brut ne peut apparaitre que dans la lane prompt explicite.
- Logs, admin, dashboard et read-model restent content-free: pas de passage brut, payload Catalogue brut, prompt complet, titre/auteur/locator/requete brute, secret, token, cookie ou DSN.
- Le frontend expose `btnBiblioMode` juste apres Adobe, avec icone livre, `aria-pressed`, et payload `biblio_enabled`.

## Preuves executees

Commandes locales:

```bash
python3 -m py_compile app/biblio/*.py app/core/chat_service.py app/core/chat_llm_flow.py app/server.py
python3 -m unittest \
  app.tests.unit.biblio.test_catalogue_client \
  app.tests.unit.biblio.test_document_resolver \
  app.tests.unit.biblio.test_passage_extractor \
  app.tests.unit.biblio.test_prompt_lane \
  app.tests.unit.biblio.test_observability \
  app.tests.unit.biblio.test_chat_runtime
node --check app/web/app.js
node --check app/web/chat_biblio_mode.js
node --test app/tests/unit/frontend_chat/test_biblio_mode_module.js
```

Commandes live conteneur:

```bash
docker exec -w /app platform-fridadev python -m unittest \
  tests.unit.biblio.test_catalogue_client \
  tests.unit.biblio.test_document_resolver \
  tests.unit.biblio.test_passage_extractor \
  tests.unit.biblio.test_prompt_lane \
  tests.unit.biblio.test_observability \
  tests.unit.biblio.test_chat_runtime \
  tests.test_server_chat_biblio_contract \
  tests.test_server_admin_chat_logs_contract
```

Resultat: suites vertes au moment de la cloture.

## Limites volontaires

- Pas d'extraction de ranges `126b -> 126e`.
- Pas de recherche semantique large ni RAG documentaire.
- Pas d'UI Catalogue dans FridaDev.
- Pas d'ecriture Catalogue depuis FridaDev.
- Pas de backfill, OCR general ou re-OCR Catalogue.

Toute evolution de ces limites doit ouvrir un nouveau lot explicite.

## Addendum correctif bibliothecaire - 2026-05-30

Statut: correctif produit applique sur le chantier archive.

Motif: deux demandes Biblio reelles etaient classees a tort `biblio_no_bibliographic_signal` malgre un Catalogue joignable: liste des premiers ouvrages et extraction naturelle d'un passage du Theetete de Platon avec range Stephanus.

Changements valides:

- ajout de `app/biblio/query_planner.py` pour produire un plan structure (`list_catalog`, `search_catalog`, `resolve_work`, `extract_passage`, `extract_range`, `clarify_ambiguous`);
- ajout de `app/biblio/work_resolver.py` pour relier oeuvre interne, document physique Catalogue et ancre non textuelle issue de `/search`;
- ajout de `app/biblio/library_runtime.py` pour executer la consultation GET-only et produire soit une lane de consultation, soit la lane passage existante;
- `chat_runtime.py` orchestre ces modules sans devenir un fourre-tout;
- `BiblioDocumentResolver` accepte des ancres `locator_anchor_page` / `locator_anchor_para` et resout les document-id via `/metadata`;
- `BiblioPassageExtractor` accepte les ranges bornes sur une meme page et garde un refus explicite pour les ranges non surs.

Limites mises a jour:

- les ranges ne sont plus tous refuses par principe; seuls les ranges resolus de maniere sure, bornee, sur une meme page et sous les limites de taille peuvent produire un passage;
- les autres ranges restent `range_extraction_not_supported`, `too_long`, `ambiguous`, `not_found` ou autre statut explicite;
- aucune route plateforme nouvelle n'a ete necessaire.

Les invariants GET-only, toggle off, separation des documents actifs et observabilite content-free restent inchanges.
