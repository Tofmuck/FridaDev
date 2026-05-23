# FridaDev Adobe Docs Mode - Live Validation 2026-05-23

Statut: validation live bornee
Date: 2026-05-23
TODO source: `app/docs/todo-todo/product/Adobe to do.md`
Spec source: `app/docs/states/specs/fridadev-adobe-docs-mode-contract.md`

## Verdict

Le mode Adobe Photoshop / Illustrator est valide en live sur le chemin nominal UI streaming:

- UI Adobe explicite;
- payload `/api/chat` avec `specialization_profile=adobe`;
- produit explicite `photoshop` ou `illustrator`;
- `web_search=false` quand Adobe est actif;
- mini-pipeline Adobe separe du web search general;
- Crawl4AI `/md` en `raw` avec cache desactive;
- selection de passages;
- lane prompt Adobe;
- reponse utilisateur produite.

Aucun index Adobe, aucune Biblio Adobe et aucun stockage durable de markdown ou passages Adobe n'ont ete crees.

## Preuves Live Content-Free

### UI streaming

Validation Playwright sur `http://172.23.0.4:8089/`, sans passer par Authelia:

- page chargee: HTTP applicatif OK, titre `Frida`;
- mode Adobe inactif par defaut;
- payload normal sans champ `specialization_profile` ni `adobe_product`;
- bouton web actif avant Adobe: `aria-pressed=true`;
- activation Photoshop: bouton Adobe actif, bouton web desactive, `aria-pressed=false` cote web;
- payload Photoshop: `specialization_profile=adobe`, `adobe_product=photoshop`, `web_search=false`;
- payload Illustrator: `specialization_profile=adobe`, `adobe_product=illustrator`, `web_search=false`;
- les trois POST UI `/api/chat` du parcours Adobe ont retourne HTTP 200 en streaming.

Note UI: deux messages console attendus en acces interne direct non authentifie signalent le refus HTTP 403 du controle admin `main_reasoning_control`; ils ne bloquent pas le chat ni le mode Adobe.

### Photoshop

Conversation live: `ed7986e2-d884-48e7-8586-1a160f538094` puis validation UI `88aeaa85-4e16-4ad1-920e-7f10309d6002`.

Metriques observees:

- product: `photoshop`;
- status: `success`;
- evidence: `sufficient`;
- seed_count: `3`;
- crawled_page_count: `5`;
- link_candidate_count: environ `1389`;
- ranked_link_count: `4`;
- selected_passage_count: `6`;
- injected_chars: environ `4225`;
- read_statuses: `success` sur les cinq pages;
- source_types observees: `known_issues`, `hub`, `release_notes`, `help_page`;
- reason_codes: `adobe_profile_owns_retrieval`, `accepted`, `crawl_raw_primary`, `selection_limit_applied`.

### Illustrator

Conversation live: `50b96bfd-99c9-4df6-a473-f53c37e1a952` puis validation UI `88aeaa85-4e16-4ad1-920e-7f10309d6002`.

Metriques observees:

- product: `illustrator`;
- status: `success`;
- evidence: `sufficient`;
- seed_count: `3`;
- crawled_page_count: `5`;
- link_candidate_count: environ `1483`;
- ranked_link_count: `4`;
- selected_passage_count: `6`;
- injected_chars: environ `3213`;
- read_statuses: `success` sur les cinq pages;
- source_types observees: `help_page`;
- reason_codes: `adobe_profile_owns_retrieval`, `accepted`, `crawl_raw_primary`, `selection_limit_applied`.

### Web + Adobe

Quand `web_search` etait actif avant Adobe:

- l'UI a desactive le bouton web;
- le payload Adobe a force `web_search=false`;
- le backend a journalise `web_search` en `skipped`;
- le reason code observe est `adobe_profile_owns_retrieval`.

### Adobe Desactive

Validation UI streaming:

- payload normal sans champs Adobe;
- web search actif cote UI envoie bien `web_search=true`;
- le backend journalise `web_search` en `ok`, `context_injected=true`, `results_count=5`.

## Privacy / Non-Stockage

Verifications effectuees:

- `observability.chat_log_events` ne contient pas les marqueurs `[ADOBE DOCS PASSAGES]`, `[ADOBE DOCS MODE]`, `Texte du passage:` ou `Passages Adobe HelpX selectionnes` dans `payload_json`;
- `/app/logs` et `/app/data` ne contiennent pas les marqueurs de passages Adobe;
- les evenements `adobe_docs` et `adobe_prompt_lane` exposes sont content-free: produit, statuts, counts, hashes courts, source types, reason codes, latences/counts;
- aucun markdown Adobe ni passage complet n'a ete affiche dans cette note.

## Dette Hors Mode Adobe - /api/chat stream=false

Deux probes directes `/api/chat` en JSON non-streaming, sans Adobe, ont retourne HTTP 500 avec l'erreur compacte `Erreur: 'NoneType' object has no attribute 'strip'`.

Requalification:

- ce n'est pas un bug du pipeline Adobe;
- ce n'est pas le chemin UI nominal, qui utilise le streaming et a retourne HTTP 200;
- le web search general en UI streaming a ete observe en `ok`;
- cela a ete traite dans un lot separe de robustesse du chemin `/api/chat stream=false`.

Statut post-correctif du 2026-05-23:

- finding valide par reproduction live avant patch: HTTP 500, `NoneType.strip`;
- cause racine: `message.content` provider peut etre `None` en non-streaming et `extract_openrouter_text()` appelait `.strip()` apres sanitation;
- correction: `sanitize_provider_text(None)` retourne maintenant une chaine vide;
- contrat retenu: une reponse provider vide est acceptee comme texte assistant vide, mais ne provoque plus d'exception brute ni de HTTP 500;
- tests ajoutes: sanitation provider `None` et `/api/chat stream=false` avec faux provider `content=None`.

## Commandes / Preuves

- `python3 -m unittest discover -s app/tests/integration/frontend_chat -p "test_*.py"`: OK, 23 tests.
- `node --test app/tests/unit/frontend_chat/test_adobe_mode_module.js`: OK, 3 tests.
- `node --test app/tests/integration/frontend_browser/test_frontend_browser_adobe_mode.js`: OK, 2 tests.
- Tests Adobe backend dans le conteneur `platform-fridadev`: OK, 65 tests.
- `git diff --check`: OK.
- `git diff --cached --check`: OK.

## Decision

Le Lot 7 est clos pour le mode Adobe: validation live bornee reussie, sous surveillance.

La dette `/api/chat stream=false` observee pendant la validation Adobe a ete corrigee hors cloture Adobe, sans changer le chemin UI streaming nominal.
