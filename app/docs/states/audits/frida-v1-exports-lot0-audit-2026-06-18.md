# Frida V1 Exports - Lot 0 audit existant

Date: 2026-06-18
Statut: audit read-only / docs-only
TODO source: `app/docs/todo-todo/product/frida-v1-exports-todo.md`
Roadmap source: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`

## Verdict de plan

Existe-t-il un meilleur plan ?

Non. Le bon plan est de documenter l'existant avant tout contrat Exports V1,
runtime, UI ou stockage Nextcloud. Les surfaces export actuelles sont utiles,
mais elles ne livrent pas Exports V1 et ne doivent pas etre reprises comme
modele produit sans decisions Lot 1.

## Sources relues

- `app/docs/todo-todo/product/frida-v1-exports-todo.md`
- `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`
- `app/docs/states/specs/chat-copy-export-contract.md`
- `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
- `app/docs/states/specs/frida-v1-documents-ingestion-contract.md`
- `app/docs/states/specs/frida-v1-folder-markdown-notes-contract.md`
- `app/web/chat_copy_export.js`
- `app/web/app.js`
- `app/tests/unit/frontend_chat/test_chat_copy_export_module.js`
- `app/tests/integration/frontend_chat/test_frontend_chat_contract.py`
- `app/server.py`
- `app/observability/log_markdown_export.py`
- `app/tests/unit/logs/test_log_markdown_export_phase6.py`
- `app/tests/integration/frontend_admin/test_frontend_logs_phase5.py`
- `app/core/workspace_folder_standard_subfolders.py`
- `app/core/workspace_document_nextcloud_client.py`
- `app/core/workspace_document_nextcloud_runtime.py`
- `app/core/workspace_document_existing_files.py`
- `app/core/workspace_folder_note_nextcloud_client.py`
- `app/core/workspace_folder_note_nextcloud_runtime.py`
- `app/core/workspace_folder_notes_append.py`
- `app/core/workspace_folder_nextcloud_runtime.py`
- `app/requirements.txt`
- `package.json`

## Synthese content-free

Exports V1 n'existe pas encore comme runtime produit. Le depot contient deux
familles proches:

- un export Markdown conversationnel local au navigateur, humain et sans
  metadonnees techniques;
- un export Markdown admin des logs, technique, scope par conversation ou tour,
  et destine a l'operateur.

Aucune de ces surfaces ne rattache un export a `workspace_folders.id`, ne range
un artefact sous la cible logique `/Frida/<dossier>/Exports`, ne persiste un
read-model exports, ne gere DOCX/PDF, ne prouve un stockage Nextcloud-first, et
ne doit etre vendue comme Exports V1.

## Export Markdown conversationnel navigateur

### Contrat existant

`app/docs/states/specs/chat-copy-export-contract.md` definit une surface deja
livree:

- copie d'une bulle visible, locale au navigateur;
- export Markdown de la conversation courante;
- relecture forcee des messages avant generation;
- fichier humain lisible;
- exclusion des messages systeme et des metadonnees techniques;
- pas d'observabilite dediee.

Ce contrat interdit explicitement les identifiants internes, hashes, statuts
techniques, logs et metadonnees de conversation dans le fichier produit.

### Comportement reel

`app/web/chat_copy_export.js` fournit:

- `buildConversationMarkdown()`;
- `buildMarkdownFilename()`;
- `exportableMessages()`;
- `downloadMarkdownFile()`;
- helpers de copie locale.

Le format est volontairement humain:

- titre fixe lisible;
- date d'export;
- sections par message utilisateur/assistant;
- contenu des messages visibles preserve.

Le module filtre les roles et ne conserve que les messages utilisateur et
assistant. Il ne connait pas `workspace_folder`, Nextcloud, read-model local,
format TXT/DOCX/PDF ni stockage durable.

### Wiring frontend

Dans `app/web/app.js`, `exportCurrentConversation()`:

- exige une conversation courante;
- force `hydrateThreadMessages(currentId, { force: true })`;
- appelle `buildConversationMarkdown()`;
- genere un nom `.md`;
- declenche `downloadMarkdownFile()`;
- met a jour le titre du bouton selon succes/echec.

Le wiring ne contacte aucune route export produit. Il produit un telechargement
navigateur local. Il n'ecrit pas dans Nextcloud et ne cree pas d'objet export
persistant.

### Tests existants

`app/tests/unit/frontend_chat/test_chat_copy_export_module.js` prouve:

- Markdown lisible sans metadonnees techniques;
- roles systeme/outils exclus;
- copie limitee au texte fourni;
- extension `.md` stable.

`app/tests/integration/frontend_chat/test_frontend_chat_contract.py` prouve:

- chargement du module dans la surface chat;
- presence du bouton;
- appel a `hydrateThreadMessages(..., { force: true })`;
- absence de champs techniques dans le module d'export.

### Reutilisable pour Exports V1

Reutilisable comme inspiration ou brique locale, sous reserve Lot 1:

- format Markdown humain de base;
- filtrage role utilisateur/assistant;
- tests anti-metadonnees techniques;
- nommage `.md` simple;
- UX de bouton explicite.

### A garder separe

Doit rester separe tant que Lot 1 ne decide pas autrement:

- telechargement navigateur local;
- absence de read-model;
- absence de lien `workspace_folder`;
- absence de stockage Nextcloud;
- absence de statut export durable;
- absence de TXT/DOCX/PDF.

### Risques si remplace ou detourne

- casser une capacite utilisateur deja livree;
- transformer un export local humain en stockage produit sans decision;
- introduire des metadonnees techniques dans un fichier utilisateur;
- supposer que la conversation courante suffit a definir la source Exports V1;
- confondre "telecharger maintenant" et "produire un export durable".

## Export Markdown admin logs

### Route serveur

`app/server.py` expose `GET /api/admin/logs/chat/export.md`.

La route:

- lit `conversation_id` et `turn_id`;
- appelle `log_markdown_export.export_chat_logs_markdown()`;
- retourne `text/markdown`;
- ajoute un header d'attachement;
- construit un nom de fichier technique a partir du scope demande.

Cette route appartient au namespace admin/logs. Elle n'est pas sous
`/api/workspace-folders*` et ne cible pas un dossier Frida produit.

### Exporter observe

`app/observability/log_markdown_export.py`:

- lit des evenements d'observabilite en base applicative;
- supporte scope conversation ou tour;
- inclut des IDs techniques, stages, statuts, durees et champs techniques
  compactes;
- tronque des valeurs longues pour lisibilite operateur;
- retourne un Markdown de diagnostic.

Ce module est volontairement technique. Il n'a pas la semantique utilisateur
attendue d'un export produit et ne doit pas servir de modele de contenu
Exports V1.

### UI admin et tests

`app/tests/integration/frontend_admin/test_frontend_logs_phase5.py` prouve:

- page `/log` dediee;
- boutons d'export par conversation et par tour;
- appel a la route admin d'export Markdown;
- usage de filtres techniques;
- separation avec l'UI chat principale.

`app/tests/unit/logs/test_log_markdown_export_phase6.py` prouve:

- format compact stable;
- scope conversation/tour;
- ordre chronologique;
- filtrage SQL par conversation/tour;
- obligation d'un identifiant de conversation.

### Patterns tres limites reutilisables

Peut inspirer uniquement:

- reponse HTTP `text/markdown`;
- header d'attachement;
- tests de route avec fake exporter;
- pattern de nom de fichier sanitise cote serveur;
- tests de scopes explicites.

### A ne pas reutiliser comme base produit

Ne pas reutiliser pour Exports V1 utilisateur:

- contenu technique de logs;
- read-model observabilite;
- IDs techniques;
- champs compactes d'evenements;
- format `Frida Chat Logs Export`;
- scope admin conversation/tour;
- route admin;
- logique de lecture d'evenements d'observabilite.

Risque principal: produire un export utilisateur qui ressemble a une preuve
operateur, avec metadonnees techniques et confusion de finalite.

## Dependances Markdown / TXT / DOCX / PDF

### Existant repo

`app/requirements.txt` contient:

- Flask;
- requests;
- python-dotenv;
- psycopg;
- pypdf.

`package.json` expose seulement des dependances de test frontend autour de
Playwright.

Le depot contient de la lecture/extraction documentaire, pas de generation
complete d'exports DOCX/PDF:

- `app/core/active_document_text_extraction.py` lit TXT/Markdown via texte,
  DOCX via bibliotheque standard ZIP/XML, et PDF textuel via `pypdf`;
- `app/tools/web_pdf_reader.py` lit des PDF via `pypdf`;
- Notes V1 ecrit du Markdown sous `Notes`;
- Documents V1 sait manipuler des documents sources et PDFs, pas produire des
  exports finalises.

### Possible sans nouvelle dependance

Semble possible sans nouvelle dependance, apres decision Lot 1:

- Markdown simple depuis une source texte deja disponible;
- TXT simple depuis une source texte deja disponible;
- tests de conversion string-to-string;
- stockage de bytes generes dans Nextcloud via un futur client dedie;
- read-model local et projections content-free.

### A decider avant runtime

Doit etre decide en Lot 1:

- source exportable exacte;
- fidelite Markdown/TXT attendue;
- generation DOCX:
  - generation OOXML minimale via bibliotheque standard;
  - ou dependance dediee;
  - ou report/refus V1 si fidelite insuffisante;
- generation PDF:
  - dependance dediee;
  - moteur externe;
  - HTML/Markdown intermediate;
  - limites de mise en page;
  - comportement si dependance absente;
- limites de taille, duree, pages et formats;
- criteres de succes par format.

No-go avant Lot 1: vendre DOCX/PDF comme livres si le depot ne possede qu'une
lecture/extraction ou un brouillon partiel.

## Frontieres avec chantiers clos

### Nextcloud folders V1

Exports doit reutiliser le contrat de dossier Frida:

- `workspace_folder` reste le centre produit;
- seuls les dossiers `linked` sont eligibles;
- le sous-dossier standard `Exports` existe dans la liste des sous-dossiers;
- toute preuve runtime future doit rester bornee et content-free.

Exports ne doit pas rouvrir creation/renommage/suppression de dossiers.

### Documents V1

Documents gere les sources sous `/Frida/<dossier>/Documents`.

Exports ne doit pas:

- reutiliser `workspace_files` comme modele produit export sans decision;
- deplacer ou transformer automatiquement un document source;
- relancer ingestion, lecture ou fallback PDF Documents;
- lire des documents sources sans action utilisateur explicite et contrat Lot 1.

### Notes Markdown V1

Notes gere les notes vivantes sous `/Frida/<dossier>/Notes`.

Exports ne doit pas:

- reutiliser `workspace_folder_notes` comme read-model exports;
- modifier une note existante pour produire un export;
- convertir implicitement une note en export sans action explicite;
- stocker un export Markdown dans `Notes`.

### Images, Biblio, Agenda, Mail, Memory

Exports V1 ne doit pas ouvrir:

- Images generees;
- Biblio / Catalogue;
- Agenda;
- Mail;
- Memory/RAG/Identity/Summary.

Un export peut etre mentionne ou reutilise uniquement selon une decision Lot 1
et une action utilisateur explicite.

## Briques disponibles

### Patterns reutilisables

- constantes de sous-dossiers standards, dont `Exports`;
- patterns de tests anti-metadonnees de `chat_copy_export`;
- patterns frontend de bouton explicite si Lot 1 garde une surface chat;
- pattern de reponse HTTP Markdown et attachement, sans contenu admin;
- projections user/tech content-free deja pratiquees dans Documents/Notes.

Ces elements sont des patterns de conception, pas des blocs a copier. Tout
runtime Nextcloud Exports devra passer par un client Exports dedie, des reason
codes Exports et des tests Exports.

### A adapter

- generation Markdown conversationnelle locale: a rattacher a un dossier,
  source decidee, limites, read-model et stockage;
- export admin HTTP: uniquement pour mechanics de reponse, jamais pour contenu;
- clients WebDAV Documents/Notes: structure utile, mais un client Exports dedie
  est obligatoire;
- `PROPFIND Depth: 0` + verification collection: pattern a reprendre avec la
  cible `Exports`, pas code a copier tel quel;
- `PUT` anti-ecrasement et creation sure: pattern a adapter depuis Documents et
  Notes, avec reason codes Exports;
- rollback/compensation Nextcloud-first: patterns a auditer dans
  `app/core/workspace_folder_nextcloud_runtime.py`,
  `app/core/workspace_document_nextcloud_runtime.py`,
  `app/core/workspace_document_existing_files.py`,
  `app/core/workspace_folder_note_nextcloud_runtime.py` et
  `app/core/workspace_folder_notes_append.py`;
- chaque pattern de compensation doit etre revalide pour Exports: cible exacte,
  source preservee, absence d'overwrite, rollback strict et statut content-free;
- tests serveur Notes/Documents: utiles comme forme, pas comme modele produit.

### A eviter

- remplacer silencieusement le bouton export navigateur;
- creer une route globale hors `workspace_folders` sans decision Lot 1;
- reutiliser le read-model observabilite admin;
- reutiliser `workspace_files` ou `workspace_folder_notes` comme modele export;
- lire ou injecter le contenu d'un export par le seul mot "reutiliser";
- produire un DOCX/PDF incomplet presente comme final;
- logguer le contenu exporte ou des noms sensibles en preuve technique.

## Risques et no-go avant Lot 1

Decisions produit bloquantes avant runtime:

- source exportable V1;
- surface utilisateur primaire;
- sens exact de "reutiliser";
- modele local/read-model exports;
- politique de nommage, collision et versioning;
- fidelite DOCX/PDF;
- dependances de generation;
- limites de taille/duree/pages;
- politique de contenu complet vs refus.

Risques majeurs:

- ambiguite "reutiliser" menant a lecture/injection implicite;
- fuite de contenu exporte dans logs, JSONL ou observabilite;
- remplacement du bouton navigateur sans decision humaine;
- reprise du format admin logs comme produit utilisateur;
- generation DOCX/PDF partielle vendue comme complete;
- confusion avec Documents ou Notes;
- ecriture Nextcloud sans rollback/compensation;
- no-go mal presente comme liste vide ou succes partiel.

## Recommandation Lot 1

Lot 1 doit etre docs-only et creer la spec source-of-truth Exports V1. Il doit:

- fermer toutes les decisions produit bloquantes;
- definir le modele produit et le read-model local;
- definir les sources exportables et surfaces utilisateur;
- definir le sens exact de "reutiliser";
- definir formats, fidelite, limites et dependances;
- definir routes/API autorisees;
- definir politique de nommage/collision/version;
- definir reason codes et preuves Lot Z;
- confirmer que le bouton navigateur actuel reste separe ou documenter
  explicitement tout changement;
- confirmer que l'export admin logs reste strictement admin.

Si une decision humaine manque, Lot 1 doit s'arreter avant d'ecrire ou committer
la spec, avant de cocher Lot 1, et demander explicitement. Il ne doit pas
"fermer" une decision en l'inventant.
