# Frida Biblio vraie bibliotheque - remediation produit P1

Statut: livre et archive
Date de reouverture: 2026-05-30
Date d'archivage: 2026-05-30
Classement: `app/docs/todo-done/product/`
Spec source-of-truth: `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
Validation requalifiee: `app/docs/todo-done/validations/frida-biblio-real-library-passage-search-validation-2026-05-30.md`
Roadmap technique archivee: `app/docs/todo-done/product/frida-biblio-real-library-passage-search-todo.md`
Priorite: P1 produit

## 1. Reouverture

La cloture `a20c0f0 Archive Biblio real library validation` est valide comme preuve technique content-free, mais invalide comme validation produit finale.

Ecart live observe:

- une demande de table des matieres d'un fonds Platon est routee comme recherche de passage et finit en `not_found`;
- une demande de liste de la bibliotheque utilise une page Catalogue `limit=5`, ce qui peut etre presente par le modele comme la totalite du fonds;
- la surface Catalogue live contient `total`, `chapter_count`, `toc_source` et des lignes `document_chapters`, mais FridaDev ne dispose pas encore d'une route GET legere pour lister les chapitres d'un gros document sans passer par `/doc/{id}`.

## 2. Findings valides

P1 liste Catalogue:

- `/catalog?limit=5` ne doit jamais etre presente comme toute la bibliotheque;
- pour le fonds courant et proche, FridaDev doit demander et afficher tout le catalogue jusqu'a 100 ouvrages;
- au-dela, la pagination doit etre explicite: total connu, nombre affiche, possibilite de continuer.

P1 table des matieres:

- Catalogue possede des signaux TOC (`chapter_count`, `toc_source`, `document_chapters`);
- FridaDev ne peut pas lister de maniere fiable les chapitres d'un gros document via la seule route existante `/doc/{id}`, trop lourde en live;
- il faut une surface GET Catalogue legere, par exemple `/doc/{id}/chapters`, avant de declarer GO produit complet pour les tables des matieres.

P1 architecture:

- le bibliothecaire deterministe actuel couvre les actions documentaires bornees (`list_catalog`, `open_document`, `show_table_of_contents`, `search_passage`, `extract_passage`);
- un planner LLM structure ne corrigerait pas a lui seul une surface Catalogue manquante;
- il reste une option future si les intents naturels continuent a depasser les regles deterministes, mais elle doit rester sous JSON strict et allowlist GET-only.

## 3. Correctif applicatif immediat

- [x] Lister tout le catalogue jusqu'a 100 ouvrages.
- [x] Rendre les listes paginees explicites quand `total > displayed`.
- [x] Reconnaissance naturelle: `quels ouvrages`, `combien d'ouvrages`, `liste la bibliotheque`, `c'est tout ?`.
- [x] Ajouter intents `open_document` et `show_table_of_contents`.
- [x] Pour TOC: utiliser les metadonnees Catalogue disponibles et ne pas pretendre que la table detaillee est absente si seule la route legere manque.
- [x] Smokes live content-free incluant liste complete et demande TOC.

Correctif applicatif livre dans cette reouverture:

- `list_catalog` demande 100 ouvrages par defaut et expose `total_count`, `displayed_count`, `truncated`;
- `show_table_of_contents` reconnait les demandes de sommaire/chapitres et retourne une lane de consultation TOC;
- si la route detaillee serait trop lourde pour un gros document, la lane signale explicitement le besoin d'un GET leger de chapitres au lieu de conclure que la table n'existe pas;
- `open_document` retourne une synthese Catalogue bornee issue de `/catalog`;
- le smoke strict ajoute un cas table des matieres content-free.

Preuves live content-free du correctif applicatif:

- `/catalog` live: `total=10`, `limit=5` retourne 5, `limit=100` retourne 10;
- tous les documents live ont `chapter_count > 0` et `toc_source` signale;
- les tables de chapitres existent en DB Catalogue (`document_chapters`) avec 973 lignes;
- `/doc/{id}` peut timeouter meme pour un document Catalogue cible, car la route renvoie une vue document lourde;
- apres patch, les demandes de liste retournent `total_count=10`, `displayed_count=10`, `truncated=false`;
- avant la route legere, une demande TOC Platon retournait `status=toc_summary`, `reason_code=biblio_table_of_contents_detail_route_skipped`, `endpoint_kinds=[catalog]`, sans fuite brute;
- apres livraison de la route legere, une demande TOC Platon retourne `status=toc_listed`, `reason_code=biblio_table_of_contents_listed`, `endpoint_kinds=[catalog, chapters]`, sans fuite brute.

## 4. Correctif plateforme requis avant GO produit complet

- [x] Ajouter cote Catalogue une route GET read-only legere pour chapitres/table des matieres, sans texte OCR: `GET /doc/{id}/chapters`.
- [x] Rebuild doc-pipeline apres backup, uniquement dans un lot Sauron explicite.
- [x] Etendre `CatalogueClient` FridaDev avec cette route GET allowlistee.
- [x] Raccorder `show_table_of_contents` a cette route, via un module TOC dedie pour eviter de regonfler `library_runtime.py`.
- [x] Smoke live: table des matieres Platon retourne des entrees de chapitres, pas seulement un compteur.

Contrat livre:

- route plateforme: `GET /doc/{id}/chapters?limit=<1..1000>&offset=<0..100000>`;
- lecture seule: `documents` + `document_chapters`;
- payload autorise: `document_id`, compteurs, `total`, `limit`, `offset`, `count`, `truncated`, et chapitres `{chapter_no, title, unit_no, source}`;
- payload interdit: texte OCR, paragraphe, excerpt, page text, raw unit, prompt ou secret;
- FridaDev observe seulement endpoint/status/counts/id court/longueurs; les titres de chapitres peuvent apparaitre dans la lane produit de consultation, pas dans les projections techniques.

## 5. Invariants

- FridaDev reste GET-only vers Catalogue.
- Aucun DELETE, PUT ou POST depuis FridaDev.
- Pas d'ecriture DB FridaDev ou Catalogue.
- Pas d'OCR/re-OCR.
- Pas de Memory/RAG documentaire global.
- Pas de confusion avec documents actifs, workspace, Web, Identity, Summary ou Hermeneutic.
- Observabilite/admin/dashboard/read-model content-free.
- Les titres et auteurs peuvent apparaitre dans une lane produit quand l'utilisateur demande la liste ou l'ouverture de la bibliotheque, mais pas dans les projections techniques ordinaires.

## 6. Decision actuelle

GO technique pour le chaînon table des matieres: FridaDev sait maintenant demander une TOC detaillee via la route GET legere Catalogue et construire une lane produit de consultation.

GO produit conditionnel:

- la bibliotheque n'est plus reduite a une preview de 5 ouvrages;
- Frida sait ouvrir un document et signaler ses compteurs;
- Frida sait lister les chapitres d'un document dont Catalogue expose `document_chapters`;
- les recherches thematiques et extractions deja livrees restent fonctionnelles.

Reste a surveiller hors ce lot:

- qualite bibliographique des titres/chapitres produits par OCR/TOC source;
- intents naturels futurs qui pourraient necessiter un bibliothecaire structure plus riche;
- pagination explicite si le catalogue depasse durablement 100 ouvrages ou si une TOC depasse 500 entrees.
