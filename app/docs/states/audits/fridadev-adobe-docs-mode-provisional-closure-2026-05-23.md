# FridaDev Adobe Docs Mode - Cloture provisoire MVP 2026-05-23

Statut: MVP clos provisoirement, sous surveillance
Date: 2026-05-23
TODO source: `app/docs/todo-todo/product/Adobe to do.md`
Spec source: `app/docs/states/specs/fridadev-adobe-docs-mode-contract.md`
Validation live source: `app/docs/states/audits/fridadev-adobe-docs-mode-live-validation-2026-05-23.md`
Evaluation metier source: `app/docs/states/audits/fridadev-adobe-docs-mode-business-evaluation-2026-05-23.md`

## Verdict

Le MVP Adobe Docs Mode est clos provisoirement apres les Lots 1 a 9.

Ce qui est clos:

- mode Adobe explicite, inactif par defaut;
- choix produit explicite `Photoshop` ou `Illustrator`;
- absence de mode Auto;
- payload backend `specialization_profile=adobe` + `adobe_product=photoshop|illustrator`;
- mini-pipeline HelpX separe de la recherche web generale;
- lecture Crawl4AI `/md` en `raw`, cache desactive;
- liens internes HelpX bornes au produit choisi;
- selection de passages courts et sources;
- lane prompt Adobe dediee et non instructionnelle;
- observabilite content-free;
- non-stockage durable du markdown, des passages et de la lane Adobe;
- tests metier synthetiques pour Photoshop, Illustrator, release notes, known issues et preuve insuffisante.

Ce qui n'est pas clos:

- validation metier reelle par Amandine sur un cas Photoshop;
- validation metier reelle par Amandine sur un cas Illustrator;
- garantie d'exhaustivite HelpX;
- extension Learn, Community, PDF, GitHub AdobeDocs, Biblio ou index durable.

## Meilleur plan retenu

Le plan le plus sur etait une cloture docs-only apres preuves techniques:

- ne pas rouvrir l'architecture;
- ne pas patcher runtime;
- ne pas relancer de crawl massif;
- faire un smoke live borne;
- garder la TODO active tant que la validation Amandine reelle reste ouverte.

La TODO n'est pas deplacee en `todo-done` pour eviter de maquiller la limite metier restante.

## Smoke final

Smoke live borne via `platform-fridadev`, sans afficher les reponses ni les passages:

- Photoshop, mode Adobe streaming: HTTP 200, terminal `done`, environ `466` caracteres stream, reference Adobe/caveat detecte, latence environ `21.3 s`;
- Illustrator, mode Adobe streaming: HTTP 200, terminal `done`, environ `466` caracteres stream, reference Adobe/caveat detecte, latence environ `24.3 s`.

Le probe a force `web_search=true` dans le payload Adobe. Le contrat backend garde Adobe proprietaire de la recuperation et ignore la recherche web generale dans ce mode.

## Criteres de cloture

Valides:

- pas de mode Auto;
- Photoshop et Illustrator selectionnables explicitement;
- chat normal sans Adobe inchange par tests;
- web search general inchange hors Adobe par tests;
- Adobe actif possede son propre pipeline HelpX;
- Crawl4AI raw lit HelpX;
- liens internes HelpX bornes au produit choisi;
- pages lues par tour bornees;
- passages courts et sources;
- pas d'injection brute des grosses pages;
- logs et observabilite content-free;
- pas de stockage durable du markdown ni des passages Adobe;
- reponse avec source ou caveat d'insuffisance observee en smoke final;
- rollback simple: revenir au commit precedent ou desactiver le choix UI cote usage.

Limite clarifiee:

- une reponse finale assistant issue d'une conversation reste dans l'historique conversationnel normal de FridaDev;
- ce qui est interdit est la persistence documentaire du markdown HelpX, des passages Adobe bruts, de la lane prompt Adobe, d'un cache applicatif Adobe, d'une Biblio Adobe ou d'une contamination Memory/Identity/Summary/Biblio/Active Documents.

## Tests / preuves

- `python3 -m py_compile app/tools/adobe_docs_pipeline.py app/core/adobe_docs_prompt_lane.py app/tools/adobe_docs_passages.py`: OK.
- `python3 -m unittest app.tests.unit.tools.test_adobe_docs_sources app.tests.unit.tools.test_adobe_docs_reader app.tests.unit.tools.test_adobe_docs_links app.tests.unit.tools.test_adobe_docs_passages app.tests.unit.tools.test_adobe_docs_pipeline app.tests.unit.tools.test_adobe_docs_business_eval`: OK, 63 tests.
- `python3 -m unittest app.tests.unit.chat.test_adobe_docs_prompt_lane`: OK, 3 tests.
- `python3 -m unittest discover -s app/tests/integration/frontend_chat -p "test_*.py"`: OK, 23 tests.
- `node --test app/tests/unit/frontend_chat/test_adobe_mode_module.js`: OK, 3 tests.
- `docker exec platform-fridadev python -m unittest tests.unit.tools.test_adobe_docs_business_eval tests.unit.tools.test_adobe_docs_passages tests.unit.tools.test_adobe_docs_pipeline tests.unit.chat.test_adobe_docs_prompt_lane tests.test_server_chat_adobe_docs_contract`: OK, 32 tests.
- `docker ps --filter name=platform-fridadev --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"`: `platform-fridadev` healthy.
- `curl --max-time 12 -sSI https://fridadev.frida-system.fr/admin`: HTTP 302 vers Authelia, sans affichage de cookies.

## Decision

Le chantier Adobe Docs Mode peut etre considere livre en MVP technique, sous surveillance.

La validation produit forte reste volontairement ouverte jusqu'a validation Amandine sur au moins un cas Photoshop reel et un cas Illustrator reel.
