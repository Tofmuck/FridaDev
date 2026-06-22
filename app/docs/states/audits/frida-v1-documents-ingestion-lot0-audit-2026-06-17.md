# Frida V1 Documents ingestion - Lot 0 existing surfaces audit

Statut: audit read-only / docs-only
Date: 2026-06-17
Branche: `FridaV1-Nextcloud-Folders`
Source TODO: `app/docs/todo-todo/product/frida-v1-documents-ingestion-todo.md`
Source dossiers: `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
Source active documents: `app/docs/states/specs/active-conversation-documents-contract.md`

## 1. Perimetre

Ce Lot 0 inventorie les surfaces existantes avant tout runtime Documents V1.

Actions realisees:

- lecture des docs produit et specs liees aux dossiers Frida V1 / Nextcloud;
- lecture des docs archivees `active_document` et OCR;
- lecture des modules backend `active_document`, `workspace_files`,
  selections, OCR, prompt lane, chat service et routes serveur;
- lecture des surfaces UI chat / workspace folders;
- lecture des tests et observabilites existants par recherche repo.

Actions non realisees:

- aucun acces Nextcloud live;
- aucun WebDAV live;
- aucun Sauron;
- aucune lecture de secret;
- aucune lecture de contenu utilisateur;
- aucun dump DB;
- aucune copie/rangement de fichier;
- aucune suppression;
- aucun patch runtime.

Discipline content-free:

- cet audit ne contient aucun contenu de document;
- aucun nom de fichier utilisateur brut;
- aucun chemin disque utilisateur;
- aucune URL DAV;
- aucun XML brut;
- aucune valeur de secret, token, cookie ou app-password;
- aucun payload provider brut;
- aucun texte OCR brut.

## 2. Cartographie existante

### 2.1 Documents actifs de conversation

Modules:

- `app/core/active_conversation_documents.py`
- `app/core/active_document_upload_service.py`
- `app/core/active_document_text_extraction.py`
- `app/core/active_document_ocr_client.py`
- `app/core/active_document_prompt_lane.py`
- `app/core/active_document_image_validation.py`
- `app/observability/active_documents_observability.py`
- `app/web/chat_active_documents.js`

Routes:

- `GET /api/conversations/<conversation_id>/active-documents`
- `POST /api/conversations/<conversation_id>/active-documents`
- `DELETE /api/conversations/<conversation_id>/active-documents/<document_id>`

Table applicative:

- `active_conversation_documents`

Responsabilites:

- upload direct depuis le chat;
- activation / retrait manuel de documents conversation-scoped;
- extraction texte pour PDF textuel, DOCX, ODT, MD et TXT;
- detection PDF sans texte avec statut `ocr_required`;
- OCR borne via Stirling uniquement apres `document_ocr_required`;
- validation image active V0;
- injection prompt entiere ou exclusion entiere;
- observabilite content-free par tour et events admin compacts.

Classification: adapter.

Raisons:

- les extracteurs, reason codes et limites OCR sont des briques utiles;
- le modele `active_document` est temporaire et conversation-scoped;
- il ne doit pas devenir le stockage persistant de Documents V1;
- le flux expose deja des champs utilisateurs comme le nom affiche dans l'UI,
  ce qui doit etre decide explicitement pour Documents V1.

### 2.2 Extraction texte

Module:

- `app/core/active_document_text_extraction.py`

Formats supportes:

- TXT;
- MD;
- DOCX;
- ODT;
- PDF textuel.

Statuts:

- `complete`;
- `unsupported`;
- `parse_error`;
- `empty`;
- `ocr_required`.

Reason codes:

- `document_type_unsupported`;
- `document_parse_error`;
- `document_empty_text`;
- `document_ocr_required`;
- `document_runtime_unavailable`.

Classification: reutiliser partiellement.

Raisons:

- le parseur porte deja la regle "complet ou non complet";
- la detection PDF sans texte existe;
- les sorties contiennent du texte en memoire pour le service appelant;
- Documents V1 doit decider ou ce texte est autorise, et ne pas le faire sortir
  dans logs, JSONL ou dashboard.

### 2.3 OCR active documents

Module:

- `app/core/active_document_ocr_client.py`

Contrat observe:

- moteur Stirling;
- OCR seulement apres `document_ocr_required`;
- PDF deja textuel jamais OCRise;
- limites V1 archivees: `25 pages`, `25 Mo`, `180` secondes, langues
  `fra+eng+deu`;
- retour content-free sauf PDF OCRise en memoire vers l'appelant.

Classification: adapter.

Raisons:

- la logique de refus borne et les reason codes sont reutilisables;
- le runtime Documents V1 doit trancher OCR, visuel ou OCR puis visuel avant
  tout patch;
- le client appelle un service plateforme, donc il ne doit pas etre declenche
  par Lot 0 ni par un lot non decide.

### 2.4 Images et fallback visuel

Modules:

- `app/core/active_document_image_validation.py`
- `app/core/active_document_prompt_lane.py`
- `app/core/workspace_file_selection_prompt.py`

Comportements existants:

- images actives V0 conversation-scoped;
- PDF workspace en statut OCR requis peut devenir payload visuel ponctuel si
  explicitement selectionne;
- payload provider multimodal construit au moment du tour seulement;
- pas de promesse de lecture textuelle complete pour le visuel.

Classification: adapter avec decision bloquante.

Raisons:

- utile pour un fallback PDF image unifie;
- dangereux si Documents V1 presente le visuel comme lecture complete;
- aucune strategy runtime PDF Documents ne doit commencer avant arbitrage Lot 1.

### 2.5 Workspace files / fichiers de dossier

Modules:

- `app/core/workspace_files.py`
- `app/core/workspace_files_service.py`
- `app/core/workspace_files_store.py`
- `app/core/workspace_file_ocr_service.py`
- `app/core/workspace_file_ocr_store.py`
- `app/observability/workspace_files_observability.py`

Routes:

- `GET /api/workspace-folders/<folder_id>/files`
- `POST /api/workspace-folders/<folder_id>/files`
- `DELETE /api/workspace-folders/<folder_id>/files/<file_id>`
- `POST /api/workspace-folders/<folder_id>/files/<file_id>/ocr`
- `GET /api/workspace-folders/<folder_id>/files/<file_id>/ocr-markdown`
- `PATCH /api/workspace-folders/<folder_id>/files/<file_id>/ocr-markdown`

Tables applicatives:

- `workspace_files`
- `workspace_file_selections`

Responsabilites:

- upload fichier sous un `workspace_folder`;
- stockage local applicatif;
- metadonnees fichier et hashes courts;
- statut `active`, `ocr_required`, `deleted`, `disk_missing`;
- OCR de fichier workspace vers derive Markdown;
- lecture/edition explicite du Markdown OCR derive;
- suppression explicite d'un fichier;
- logs workspace files content-free.

Classification: adapter.

Raisons:

- c'est la surface la plus proche des documents persistants de dossier;
- elle est aujourd'hui locale, pas Nextcloud Documents;
- elle stocke une cle interne et des bytes locaux qui ne doivent pas fuir;
- les routes OCR Markdown peuvent exposer du contenu a l'utilisateur et ne sont
  pas des preuves content-free;
- la suppression fichier explicite supprime physiquement les bytes locaux et
  doit rester separee de toute copie/rangement Documents V1.

### 2.6 Selections de fichiers workspace

Modules:

- `app/core/workspace_file_selections.py`
- `app/core/workspace_file_selections_service.py`
- `app/core/workspace_file_selections_store.py`
- `app/core/workspace_file_selection_prompt.py`

Routes:

- `GET /api/conversations/<conversation_id>/workspace-file-selections`
- `POST /api/conversations/<conversation_id>/workspace-file-selections`
- `DELETE /api/conversations/<conversation_id>/workspace-file-selections/<file_id>`

Responsabilites:

- selection conversation-scoped d'un fichier persistant de dossier;
- verification que la conversation appartient au meme dossier que le fichier;
- injection prompt du fichier selectionne;
- exclusion content-free si selection stale, fichier supprime, disque absent,
  type non supporte, OCR requis ou modele incompatible;
- decision par tour enregistree sur la selection.

Classification: reutiliser partiellement.

Raisons:

- la relation dossier -> conversation -> usage existe deja;
- le code lit les bytes locaux pour construire le payload prompt;
- il ne cree pas de modele document persistant Nextcloud;
- Documents V1 doit decider explicitement comment un document de dossier est
  utilise par une conversation avant de reprendre cette lane.

### 2.7 Chat service et prompt lane

Modules:

- `app/core/chat_service.py`
- `app/core/active_document_prompt_lane.py`

Comportement:

- lit les documents actifs;
- lit les fichiers workspace selectionnes;
- fusionne les deux sources dans la lane `active_documents`;
- injecte avant l'appel modele principal;
- enregistre les decisions injecte/exclu;
- emet l'observabilite `active_documents`.

Classification: adapter / a cadrer en Lot 1.

Raisons:

- la lane prouve une integration conversationnelle reelle;
- elle mele deja deux sources techniques dans une meme surface prompt;
- pour Documents V1, le contrat doit distinguer document persistant de dossier,
  document actif temporaire et fichier workspace selectionne.

### 2.8 UI

Modules:

- `app/web/chat_active_documents.js`
- `app/web/chat_workspace_folders.js`
- `app/web/chat_workspace_folders_sidebar.js`
- `app/web/chat_threads_sidebar.js`
- `app/web/index.html`
- `app/web/styles.css`

Surfaces observees:

- barre documents actifs de conversation;
- upload/retrait document actif;
- dossier workspace avec liste de fichiers;
- upload fichier workspace;
- selection fichier pour la conversation courante;
- OCR workspace depuis la sidebar;
- affichage de statuts sobres.

Classification: adapter.

Raisons:

- la surface workspace folders porte deja "fichiers d'un dossier";
- la surface active documents porte un vocabulaire temporaire;
- Documents V1 doit trancher surface depot/liste et visibilite des noms avant
  runtime.

### 2.9 Tests existants

Suites principales:

- `app/tests/test_server_active_documents_contract.py`
- `app/tests/unit/core/test_active_conversation_documents.py`
- `app/tests/unit/core/test_active_document_text_extraction.py`
- `app/tests/unit/core/test_active_document_ocr_client.py`
- `app/tests/unit/core/test_active_document_upload_service_ocr.py`
- `app/tests/unit/core/test_active_document_prompt_lane.py`
- `app/tests/unit/core/test_active_document_non_contamination_lot5.py`
- `app/tests/unit/core/test_active_document_operator_proofs_lot8.py`
- `app/tests/unit/core/test_active_document_ocr_operator_proofs_lot6.py`
- `app/tests/unit/core/test_workspace_file_ocr_service.py`
- `app/tests/unit/core/test_workspace_folders_contract.py`
- `app/tests/unit/logs/test_active_documents_observability_lot7.py`
- `app/tests/unit/frontend_chat/test_active_documents_module.js`
- `app/tests/unit/frontend_chat/test_workspace_folders_module.js`
- `app/tests/integration/frontend_browser/test_frontend_browser_active_documents.js`
- `app/tests/integration/frontend_browser/test_frontend_browser_workspace_folders.js`

Classification: reutiliser partiellement.

Raisons:

- bonne couverture content-free, OCR, prompt lane, non-contamination et UI;
- beaucoup de tests utilisent fixtures/doubles, utiles pour Documents V1;
- il faudra ajouter des tests specifiques Documents V1, car les tests actuels
  peuvent passer tout en gardant un comportement produit faux pour Nextcloud
  Documents.

## 3. Documents actifs de conversation

Etat existant confirme:

- upload direct depuis chat;
- activation serveur conversation-scoped;
- retrait manuel;
- injection entiere ou exclusion entiere par tour;
- OCR borne PDF scanne via Stirling;
- image active V0 et PDF visuel ponctuel;
- limites OCR deja gravees pour `active_document`;
- frontiere explicite hors Memory/RAG/Identity/Summary;
- observabilite content-free existante.

A reutiliser:

- extraction texte complete ou non complete;
- reason codes `document_*` pour inspiration;
- limite OCR bornee;
- tests anti-contamination;
- pattern d'observabilite content-free.

A ne pas reutiliser tel quel:

- table `active_conversation_documents` comme stockage Documents V1;
- vocabulaire "document actif" pour documents persistants;
- injection automatique d'un document de dossier dans une conversation;
- exposition de noms dans les preuves sans decision amont.

Frontiere:

- `active_document` reste source d'inspiration et surface temporaire archivee;
- il ne devient pas le modele Documents V1.

## 4. Workspace files / fichiers de dossier

Etat existant confirme:

- un fichier workspace est rattache a `workspace_files.workspace_folder_id`;
- l'upload actuel est local applicatif;
- le stockage physique local est derive d'identifiants stables;
- le serializer ordinaire masque les chemins internes;
- la liste expose metadonnees et noms produits;
- OCR workspace cree ou met a jour un derive Markdown;
- selection conversation-scoped possible;
- prompt lane lit les bytes locaux seulement pour construire le tour;
- suppression fichier explicite supprime les bytes locaux et tombstone la ligne;
- suppression dossier V1 preserve les fichiers/documents workspace.

A reutiliser:

- relation fichier -> dossier;
- metadonnees content-free: type, taille, statuts, hashes courts;
- selection conversation-scoped;
- tests anti-fuite;
- logs workspace files allowlistes.

A adapter:

- modele de stockage local vers cible Nextcloud `Documents`;
- politique de nommage et collisions;
- copie/rangement controle des fichiers existants;
- statut des fichiers deja presents en local;
- lecture par conversation depuis un dossier `linked`.

A eviter:

- deplacer ou supprimer automatiquement la source locale;
- exposer la cle interne ou un chemin disque dans preuves/logs;
- utiliser le endpoint OCR Markdown comme preuve content-free;
- faire un listing Nextcloud large pour prouver l'inventaire.

## 5. PDF texte / PDF image / OCR / visuel

Deux chemins existent deja:

1. OCR borne via Stirling:
   - entre seulement apres `document_ocr_required`;
   - peut produire un PDF OCRise relu par l'extracteur;
   - promet un texte exploitable seulement si l'extraction finale est
     `complete`.
2. Injection visuelle / fichier multimodal ponctuelle:
   - peut injecter image ou PDF visuel au moment provider;
   - ne promet pas une lecture textuelle complete;
   - depend du modele principal et de limites provider.

Briques reutilisables:

- detection PDF sans texte;
- client OCR borne;
- reason codes OCR;
- payload multimodal content-free en observabilite;
- tests de non-contamination.

Briques a ne pas reutiliser telles quelles:

- presentation du visuel comme "lu";
- chemin PDF visuel reserve aux fichiers workspace selectionnes sans contrat
  Documents V1;
- OCR Markdown workspace comme statut general d'un document source.

Decisions bloquantes avant runtime:

- strategie PDF image: OCR seulement, visuel seulement, OCR puis visuel en
  fallback, ou autre strategie explicite;
- limites taille/pages/tokens du document persistant;
- statut utilisateur quand un PDF est non lisible ou seulement visuel;
- equivalence stricte entre upload direct et document venant de `Documents`.

Risques:

- fausse lecture si un PDF visuel est traite comme texte complet;
- fausse completude si un parse partiel est presente comme reussi;
- divergence entre upload direct et document Nextcloud;
- fuite de texte OCR dans une preuve.

## 6. Observabilite et logs

Surfaces existantes:

- `active_documents_observability` pour events de tour et events admin;
- `workspace_files_observability` pour logs content-free workspace files;
- dashboard observable module `documents` base sur les events
  `active_documents`.

Forces:

- champs metadonnees et compteurs deja disponibles;
- flag `raw_content_included=false`;
- reason code counts;
- tests anti-fuite.

Risques:

- l'observabilite active documents peut porter le nom affiche du document;
- la visibilite des noms doit etre tranchee avant read-model Documents V1;
- le dashboard `documents` actuel concerne surtout `active_documents`, pas les
  documents persistants de dossier;
- il manque un catalogue reason codes Documents V1 stabilise.

Classification: adapter.

## 7. Classifications principales

### Reutiliser tel quel

- constantes produit de formats textes supportes, comme inspiration;
- estimateur tokens et normalisation texte;
- patterns de tests content-free;
- allowlist de champs logs workspace files;
- verification que suppression dossier preserve les fichiers workspace.

### Reutiliser partiellement

- `active_document_text_extraction.py`;
- `active_document_ocr_client.py`;
- `active_document_prompt_lane.py`;
- `workspace_files_store.py`;
- `workspace_files_service.py`;
- `workspace_file_selections_store.py`;
- `workspace_file_selection_prompt.py`;
- observabilite active documents et workspace files.

### Adapter

- routes `/api/workspace-folders/<folder_id>/files*`;
- routes selections;
- UI workspace folders sidebar;
- tests serveur workspace folders;
- tests frontend workspace folders;
- dashboard/read-model `documents`.

### Eviter

- reutiliser `active_conversation_documents` comme stockage durable;
- lancer OCR ou visuel sans decision PDF Documents V1;
- exposer contenu ou noms sensibles dans JSONL;
- utiliser OCR Markdown comme preuve content-free;
- faire une suppression source pendant la copie/rangement initiale.

### Auditer plus tard

- inventaire applicatif DB des fichiers workspace actifs;
- volume et types reels agreges;
- presence de fichiers OCR derives;
- collisions de noms cible dans `/Frida/<dossier>/Documents`;
- surface UI exacte a retenir pour depot/liste.

### Hors-scope Documents V1

- Biblio / Catalogue;
- Notes Markdown;
- Exports;
- Images generees;
- Agenda;
- mail;
- Memory/RAG/Identity/Summary;
- DB directe Nextcloud.

## 8. Risques / effets de bord

- Confusion document persistant de dossier vs `active_document` temporaire.
- Confusion Documents vs Biblio / Catalogue.
- Copie/rangement silencieux des fichiers workspace existants.
- Suppression source silencieuse apres copie.
- Fuite de noms de fichiers, contenu, chemin disque, cle interne, XML, URL DAV
  ou secret.
- Injection involontaire dans Memory/RAG/Identity/Summary.
- Double pipeline OCR/PDF divergent entre upload direct et document Nextcloud.
- Route parallele qui contourne `workspace_folders`.
- Tests passant sur `active_document` mais faux pour Documents V1 persistant.
- Tests passant sur workspace files locaux mais faux pour Nextcloud `Documents`.
- OCR Markdown editable exposant du contenu si traite comme preuve.
- Prompt lane lisant des bytes locaux sans decision de surface utilisateur.

## 9. No-go avant Lot 1

- Ne pas coder tant que le contrat produit Documents V1 n'a pas tranche ou
  bloque explicitement les decisions ouvertes.
- Ne pas choisir un modele local Documents par opportunisme depuis
  `active_document` ou `workspace_files`.
- Ne pas ouvrir un runtime PDF Documents avant strategie OCR/visuel tranchee.
- Ne pas deplacer, copier, ranger ou supprimer les fichiers workspace existants.
- Ne pas ajouter de route parallele Documents hors `workspace_folders` sans
  justification contractuelle.
- Ne pas utiliser un listing Nextcloud ou une preuve contenant noms/contenu.
- Ne pas exposer la cle interne, chemin disque, URL DAV, XML ou secret.
- Ne pas reutiliser Biblio, Notes, Exports ou Images par confusion.

## 10. Inputs pour Lot 1

Decisions a trancher ou bloquer en contrat produit:

- modele local Documents:
  - table dediee stricte;
  - extension d'une surface existante;
  - read-model derive;
  - ou no-go motive.
- surface de depot:
  - UI dossier;
  - chat avec dossier courant;
  - surface fichiers existante;
  - autre surface documentee.
- surface de liste:
  - panneau dossier;
  - liste dans chat;
  - reprise workspace folders sidebar;
  - autre surface documentee.
- visibilite des noms de fichiers:
  - visibles en UI produit;
  - redacted dans preuves;
  - regle hybride stricte.
- lecture / usage conversationnel:
  - preparation de lecture;
  - injection conversationnelle;
  - selection explicite;
  - limites taille/pages/tokens.
- strategie PDF image:
  - OCR seulement;
  - visuel seulement;
  - OCR puis visuel fallback;
  - autre strategie documentee.
- politique operationnelle fichiers existants:
  - copie seule;
  - copie puis verification;
  - conservation source;
  - rollback;
  - collisions;
  - preuve `0 a traiter` si applicable.
- catalogue reason codes Documents V1:
  - codes depot;
  - codes liste;
  - codes lecture;
  - codes OCR/visuel;
  - codes Nextcloud;
  - codes redaction.
- criteres Lot Z:
  - formats minimum;
  - smokes live synthetiques;
  - preuves anti-fuite;
  - limites assumees.

## 11. Conclusion Lot 0

Le depot contient deja deux familles utiles mais distinctes:

- `active_document`: document temporaire de conversation, robuste pour upload,
  extraction, OCR borne, prompt lane et observabilite;
- `workspace_files`: fichier persistant local rattache a un dossier, deja
  selectionnable dans une conversation et deja teste content-free.

Documents V1 doit partir du modele dossier `workspace_folders` et du dossier
Nextcloud `Documents`, pas d'un simple renommage de `active_document`.

Recommandation Lot 1:

- definir un contrat produit Documents V1 qui garde `active_document` comme
  frontiere/inspiration;
- prendre `workspace_files` comme surface existante a adapter prudemment;
- bloquer tout runtime tant que modele local, surfaces UI, visibilite noms,
  strategie PDF image, politique fichiers existants, reason codes et criteres
  de cloture ne sont pas tranches.
