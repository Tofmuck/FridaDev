# Frida V1 - Nextcloud folders - Lot 0 audit read-only

Date: 2026-06-16
Statut: audit Lot 0 valide, docs-only
Classement: `app/docs/states/audits/`
TODO source: `app/docs/todo-todo/product/frida-v1-nextcloud-folders-todo.md`
Branche: `FridaV1-Nextcloud-Folders`
Commit de depart: `abe1f09 docs: detail Frida V1 Nextcloud folders todo`

## 1. Perimetre

Ce Lot 0 est un audit repo read-only. Aucun acces Nextcloud live, CalDAV live,
WebDAV live, Docker, rebuild, creation de compte, modification plateforme,
route, UI ou runtime n'a ete fait.

Objectif: comprendre les surfaces FridaDev deja existantes autour des dossiers,
fichiers, documents actifs, exports, images, stockage et observabilite avant de
definir le socle Frida 1.0:

```text
un dossier frontend Frida = un repertoire Nextcloud
```

## 2. Sources relues

Docs produit et contrats:

- `AGENTS.md`
- `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`
- `app/docs/todo-todo/product/frida-v1-nextcloud-folders-todo.md`
- `app/docs/todo-todo/product/frida-v1-documents-ingestion-todo.md`
- `app/docs/todo-todo/product/frida-v1-folder-markdown-notes-todo.md`
- `app/docs/todo-todo/product/frida-v1-exports-todo.md`
- `app/docs/todo-todo/product/frida-v1-agentic-observability-todo.md`
- `app/docs/todo-todo/product/frida-v1-generated-images-todo.md`
- `app/docs/states/specs/workspace-folders-contract.md`
- `app/docs/states/specs/active-conversation-documents-contract.md`
- `app/docs/states/specs/chat-copy-export-contract.md`
- `app/docs/todo-done/product/fridadev-workspace-folders-todo.md`
- `app/docs/todo-done/product/active-conversation-documents-todo.md`
- `app/docs/todo-done/product/active-conversation-documents-ocr-todo.md`
- `app/docs/todo-done/product/fridadev-image-generation-openrouter-todo.md`
- `app/docs/todo-todo/product/frida-agenda-agent.md`
- `app/docs/states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`
- `app/docs/states/baselines/frida-agenda-agent-lot0-baseline-2026-06-08.md`

Code applicatif et frontend:

- `app/core/conversations_maintenance.py`
- `app/core/conversations_store.py`
- `app/core/conversations_service.py`
- `app/core/workspace_folders.py`
- `app/core/workspace_folders_store.py`
- `app/core/workspace_folders_service.py`
- `app/core/workspace_files.py`
- `app/core/workspace_files_store.py`
- `app/core/workspace_files_service.py`
- `app/core/workspace_file_selections.py`
- `app/core/workspace_file_selections_store.py`
- `app/core/workspace_file_selection_prompt.py`
- `app/core/workspace_file_ocr_service.py`
- `app/core/workspace_file_ocr_store.py`
- `app/core/active_conversation_documents.py`
- `app/core/active_document_upload_service.py`
- `app/core/active_document_text_extraction.py`
- `app/core/active_document_prompt_lane.py`
- `app/core/active_document_image_validation.py`
- `app/core/active_document_ocr_client.py`
- `app/core/chat_service.py`
- `app/observability/workspace_files_observability.py`
- `app/observability/active_documents_observability.py`
- `app/observability/log_markdown_export.py`
- `app/tools/image_generation.py`
- `app/server.py`
- `app/config.py`
- `app/web/chat_workspace_folders.js`
- `app/web/chat_workspace_folders_sidebar.js`
- `app/web/chat_active_documents.js`
- `app/web/chat_copy_export.js`
- `app/web/chat_image_generation.js`

## 3. Inventaire des surfaces existantes

### 3.1 Dossiers de travail FridaDev

Surfaces:

- tables: `workspace_folders`, `conversations.workspace_folder_id`;
- modules: `workspace_folders.py`, `workspace_folders_store.py`,
  `workspace_folders_service.py`;
- endpoints: `GET/POST/PATCH/DELETE /api/workspace-folders`;
- frontend: `chat_workspace_folders.js`, `chat_workspace_folders_sidebar.js`;
- docs: `workspace-folders-contract.md` et archive
  `fridadev-workspace-folders-todo.md`.

Constat:

- FridaDev a deja un modele de repertoires de travail locaux en sidebar;
- un repertoire peut organiser des conversations et fichiers persistants;
- une conversation peut etre hors repertoire ou rattachee a un repertoire;
- les conversations existantes restent hors repertoire par defaut;
- la suppression d'un repertoire sort les conversations du repertoire;
- la suppression d'un repertoire tente aussi de supprimer les fichiers locaux
  rattaches, puis refuse en `409` si suppression fichier incomplete;
- le nom humain est sanitise, mais le code actuel ne porte pas de contrat de
  conflit de nom Nextcloud;
- le modele actuel n'a pas de champ Nextcloud, WebDAV, droits, partage ou
  compte Frida.

Decision Lot 0:

- reutilisable partiellement pour le vocabulaire produit, la sidebar, les
  validations simples, les ids stables et la relation conversation-dossier;
- a eviter tel quel comme modele Nextcloud, car il est local DB/disque et
  contient deja des effets de suppression fichiers;
- a auditer en Lot 1 pour savoir si `workspace_folder` devient le dossier Frida
  V1 ou si un nouveau modele explicite est necessaire.

### 3.2 Fichiers persistants de repertoire

Surfaces:

- table: `workspace_files`;
- modules: `workspace_files.py`, `workspace_files_store.py`,
  `workspace_files_service.py`;
- endpoints:
  - `GET/POST/DELETE /api/workspace-folders/<folder_id>/files`;
  - `POST /api/workspace-folders/<folder_id>/files/<file_id>/ocr`;
  - `GET/PATCH /api/workspace-folders/<folder_id>/files/<file_id>/ocr-markdown`;
- stockage local: `WORKSPACE_FILES_DIR`, par defaut sous `app/conv/_workspace_files`;
- champs notables: `workspace_folder_id`, `display_name`,
  `original_filename`, `storage_key`, `content_kind`, `media_kind`,
  `mime_type`, `source_extension`, tailles, hashes, status, reason code,
  `source_kind`, `source_file_id`.

Constat:

- les bytes sont stockes sur disque local sous prefixe stable, pas dans
  Nextcloud;
- `storage_key` et chemins physiques sont internes et ne doivent pas sortir en
  UI/logs;
- le listing detecte `disk_missing`;
- la suppression fichier supprime les bytes locaux puis tombstone la DB;
- la suppression d'un dossier peut entrainer suppression de tous ses fichiers
  locaux actifs.

Decision Lot 0:

- reutilisable partiellement comme inspiration de metadonnees content-free,
  status, reason codes et reconciliation DB/stockage;
- a eviter dans Lot 1: le socle dossiers Nextcloud ne doit pas encore traiter
  fichiers, ingestion, OCR ou suppression de contenu;
- a garder hors-scope jusqu'aux lots documents/notes/exports/images.

### 3.3 Selections de fichiers workspace

Surfaces:

- table: `workspace_file_selections`;
- modules: `workspace_file_selections.py`,
  `workspace_file_selections_store.py`,
  `workspace_file_selection_prompt.py`;
- endpoints:
  `GET/POST/DELETE /api/conversations/<conversation_id>/workspace-file-selections`;
- integration runtime: `chat_service._workspace_files_for_prompt()`.

Constat:

- la selection est conversation-scoped;
- un fichier workspace n'est jamais injecte par defaut;
- la selection exige que la conversation appartienne au meme repertoire que le
  fichier;
- les fichiers selectionnes sont convertis au moment du prompt en items
  compatibles avec la lane `active_document`;
- les decisions d'injection/exclusion sont retracees en content-free.

Decision Lot 0:

- reutilisable partiellement plus tard pour documents/notes si le dossier
  Nextcloud devient source de fichiers persistants;
- hors-scope Lot 1, car le socle dossier doit d'abord definir
  dossier/droits/chemin sans injection modele;
- risque principal: confondre "dossier Frida existe" avec "ses fichiers sont
  lisibles par Frida".

### 3.4 Documents actifs de conversation

Surfaces:

- table: `active_conversation_documents`;
- modules: `active_conversation_documents.py`,
  `active_document_upload_service.py`, `active_document_text_extraction.py`,
  `active_document_prompt_lane.py`, `active_document_image_validation.py`,
  `active_document_ocr_client.py`;
- endpoints:
  `GET/POST/DELETE /api/conversations/<conversation_id>/active-documents`;
- frontend: `chat_active_documents.js`;
- observabilite: `active_documents_observability.py`.

Constat:

- un `active_document` est temporaire, conversation-scoped et retire par action
  manuelle;
- le contenu texte ou image peut etre stocke cote serveur pour la preparation
  du prompt;
- injection entiere ou exclusion entiere, jamais troncature silencieuse;
- les documents actifs restent hors Memory/RAG/Identity/Summary/Biblio;
- OCR PDF borne existe via Stirling seulement apres `document_ocr_required`;
- les images actives sont conversation-scoped.

Decision Lot 0:

- reutilisable plus tard pour la lecture/injection apres selection explicite;
- a eviter dans Lot 1: le socle Nextcloud folders ne doit pas uploader, lire,
  OCRiser ou injecter des contenus;
- hors-scope de ce lot sauf comme frontiere a ne pas melanger.

### 3.5 Uploads et OCR

Surfaces:

- uploads actifs: `active_document_upload_service.py`;
- uploads workspace: `workspace_files_service.py`;
- extracteur texte: `active_document_text_extraction.py`;
- OCR: `active_document_ocr_client.py`, `workspace_file_ocr_service.py`,
  `workspace_file_ocr_store.py`;
- config OCR: `ACTIVE_DOCUMENT_OCR_URL`,
  `ACTIVE_DOCUMENT_IMAGE_TO_PDF_URL`, timeout, langues, limites pages/bytes.

Constat:

- les deux chemins upload reutilisent les validateurs/extracteurs documents
  actifs;
- le workspace OCR peut creer ou mettre a jour un vrai fichier `.ocr.md`
  durable et editable;
- la route `ocr-markdown` peut retourner le contenu Markdown pour edition.

Decision Lot 0:

- hors-scope Lot 1;
- a auditer plus tard pour le lot notes Markdown et documents ingestion;
- attention: la lecture/edition de contenu Markdown est une surface de contenu
  brut, incompatible avec les preuves content-free du socle dossier.

### 3.6 Exports

Surfaces:

- export chat navigateur: `chat_copy_export.js`, declenche depuis `app.js`;
- spec: `chat-copy-export-contract.md`;
- export logs admin: `log_markdown_export.py`,
  `GET /api/admin/logs/chat/export.md`.

Constat:

- l'export chat produit un fichier Markdown navigateur a partir des messages
  visibles et exclut metadonnees techniques;
- l'export logs admin est une surface d'observabilite, pas un export produit
  range dans un dossier;
- aucun export produit Markdown/TXT/DOCX/PDF vers Nextcloud n'est livre dans le
  socle actuel.

Decision Lot 0:

- hors-scope Lot 1;
- a auditer plus tard dans `frida-v1-exports-todo.md`;
- ne pas reutiliser l'export logs admin pour le stockage produit utilisateur.

### 3.7 Images generees

Surfaces:

- backend: `app/tools/image_generation.py`;
- endpoint: `POST /api/tools/image-generation`;
- frontend: `chat_image_generation.js`;
- TODO V1 dediee: `frida-v1-generated-images-todo.md`.

Constat:

- le backend retourne une `image_data_url` au frontend;
- la V0 documentee ne persiste pas l'image dans FridaDev, ne l'injecte pas dans
  le dialogue et ne l'ajoute pas a Memory/Identity/Summary/active documents ou
  Biblio;
- les logs techniques sont content-free: generateur, modele, format, statut,
  erreur, latence, usage/cout, MIME et taille data URL;
- le rattachement d'image a un dossier est un chantier Frida V1 separe.

Decision Lot 0:

- hors-scope Lot 1;
- a auditer plus tard pour le lot images generees;
- ne pas faire du dossier Nextcloud un stockage implicite d'images tant que le
  modele dossier n'est pas defini.

### 3.8 Biblio, Catalogue et Agenda

Surfaces:

- Biblio/Catalogue: modules `app/biblio/`, contrats et archives dedies;
- Agenda: modules `app/agenda/`, TODO `frida-agenda-agent.md`, baseline et
  cloture pragmatique Agenda.

Constat:

- Biblio est un systeme documentaire separe, avec Catalogue GET-only et
  observabilite content-free;
- Agenda utilise CalDAV et, pour V1, le compte humain `tof` avec secret dedie;
- les docs Agenda disent explicitement: pas de DB directe Nextcloud, pas de
  compte service `frida` pour Agenda V1, un utilisateur `frida` pourra etre
  envisage plus tard pour Files/repertoire Frida;
- les preuves Agenda live existantes ne doivent pas etre rejouees ici.

Decision Lot 0:

- Biblio et Agenda sont hors-scope du socle dossiers;
- reutilisable seulement comme precedent de garde-fous: pas de DB directe
  Nextcloud, preuve content-free, secret redacted, fake/local avant live;
- Sauron reste requis pour compte Frida, droits, partage et secrets Files.

### 3.9 Observabilite

Surfaces:

- workspace: `workspace_files_observability.py`;
- documents actifs: `active_documents_observability.py`;
- dashboard/read-models: `dashboard_observable_modules.py`,
  `turn_pipeline_read_model.py`;
- logs chat: `chat_turn_logger.py`, `log_store.py`.

Constat:

- l'observabilite workspace autorise seulement des champs techniques bornes:
  ids, counts, status, reason codes, MIME, tailles, dimensions, hash court,
  type d'erreur;
- l'observabilite documents actifs pose `raw_content_included=False` et
  `future_biblio_included=False`;
- les projections savent distinguer `active_conversation_documents`,
  `workspace_file_selections` et mixte;
- aucun contrat specifique `nextcloud_folder_*` n'existe encore.

Decision Lot 0:

- reutilisable partiellement: conventions reason code, content-free fields,
  ids courts/hashes courts;
- Lot 1 doit definir le minimum observable dossier avant toute route live;
- Lot 6 gerera le schema complet d'observabilite dossiers.

## 4. Synthese reutilisation

| Surface | Decision |
| --- | --- |
| `workspace_folders` | Reutilisable partiellement: modele UI/DB local, relation conversation, ids stables. A ne pas brancher tel quel sur Nextcloud sans contrat. |
| `workspace_files` | Reutilisable plus tard pour metadonnees et reason codes. A eviter en Lot 1, car fichiers/bytes/suppression sont hors-scope. |
| `workspace_file_selections` | Reutilisable plus tard pour selection explicite. Hors-scope Lot 1. |
| `active_conversation_documents` | Reutilisable plus tard pour injection/lane. A eviter pour le socle dossier. |
| Extracteurs/OCR | A auditer plus tard pour ingestion/notes. Hors-scope Lot 1. |
| Export chat/logs | Hors-scope Lot 1. Ne couvre pas export produit vers dossier. |
| Image generation | Hors-scope Lot 1. Pas de persistence actuelle. |
| Agenda CalDAV | Precedent de garde-fous uniquement. Ne pas reutiliser pour Files. |
| Biblio/Catalogue | Hors-scope. Ne pas transformer le dossier Frida en Biblio ou RAG. |
| Observabilite content-free | Reutilisable partiellement pour style de reason codes et champs autorises. |

## 5. Risques avant code

- Doublon de modele dossier: `workspace_folder` existe deja, mais le contrat V1
  parle maintenant de repertoire Nextcloud; Lot 1 doit trancher extension ou
  nouveau modele explicite.
- Melange documents actifs / dossiers persistants: un dossier ne rend rien
  lisible par le modele sans selection explicite.
- Fuite de chemins: `storage_key`, chemins disque, URL DAV/WebDAV ou chemin
  Nextcloud brut ne doivent pas sortir en logs, JSONL, dashboard ou UI.
- Fuite de contenu: OCR Markdown, document actif et exports peuvent exposer du
  texte; ils restent hors Lot 1.
- Suppression trop large: le workflow workspace actuel supprime les fichiers du
  repertoire local; le futur socle Nextcloud ne doit jamais reprendre cette
  logique live sans confirmation humaine et borne synthetique.
- Conflit de nom: le code workspace actuel ne suffit pas a definir le conflit
  Nextcloud; Lot 1 doit specifier detection, message et reason code.
- Confusion conversation/dossier: `conversations.workspace_folder_id` organise
  les conversations, mais le dossier Frida V1 doit aussi porter le mapping vers
  un repertoire Nextcloud.
- Dette observabilite: aucun evenement `nextcloud_folder_*` n'existe encore.
- Scope creep: documents, notes, exports, images, mail, Agenda et Biblio sont
  des lots separes; les ouvrir pendant Lot 1 rendrait le socle incontrable.

## 6. Invariants confirmes

- Pas de DB directe Nextcloud depuis FridaDev.
- Pas de secret Nextcloud dans repo, docs, logs, JSONL, prompts, sorties
  terminal ou reponses.
- Pas de contenu utilisateur brut dans logs, preuves, JSONL ou dashboard par
  defaut.
- Fake/local avant tout live.
- Sauron requis avant toute creation de compte Nextcloud Frida, droits,
  partage, secret, app-password, backup ou verification serveur.
- Dossier frontend Frida = repertoire Nextcloud pour Frida 1.0, mais
  l'implementation reste a definir.
- Lot 0 n'a pas accede a Nextcloud, CalDAV, WebDAV, Docker ni plateforme.

## 7. Recommandation Lot 1

Lot 1 doit definir un contrat produit minimal avant code runtime.

Modele minimal a trancher:

- `frida_folder_id`: identifiant stable applicatif;
- `display_name`: nom affiche utilisateur;
- `status`: actif, supprime, erreur eventuelle;
- `nextcloud_logical_path` ou alias logique redacted, non brut serveur;
- `nextcloud_directory_ref` ou reference interne non sensible si necessaire;
- `owner_kind`: Frida/service ou autre decision Sauron;
- `share_state`: partage Tof attendu, confirme ou inconnu;
- `rights_state`: droits attendus, confirmes ou inconnus;
- timestamps creation/update/delete;
- reason codes: nom requis, nom invalide, conflit de nom, cible manquante,
  droits insuffisants, backend fake/local, Nextcloud indisponible redacted.

Fichiers probablement concernes apres Lot 1, si code ouvert plus tard:

- `app/core/workspace_folders.py`
- `app/core/workspace_folders_store.py`
- `app/core/workspace_folders_service.py`
- `app/core/conversations_store.py`
- `app/core/conversations_service.py`
- `app/server.py`
- `app/web/chat_workspace_folders.js`
- `app/web/chat_workspace_folders_sidebar.js`
- `app/observability/workspace_files_observability.py` ou un nouveau module
  dedie d'observabilite dossier.

Surfaces a ne pas toucher en Lot 1:

- `workspace_files*`;
- `workspace_file_selections*`;
- `active_conversation_documents*`;
- OCR;
- exports;
- image generation;
- Biblio;
- Agenda;
- Sauron/plateforme;
- Docker/rebuild;
- endpoints live Nextcloud.

Points a demander a Sauron plus tard, pas en Lot 1:

- existence/provisionnement du compte Nextcloud Frida;
- repertoire racine Frida;
- droits exacts;
- partage avec Tof;
- secret/app-password dedie, redacted et revocable;
- preuve read-only content-free avant toute ecriture;
- rollback/backup plateforme si une modification Nextcloud est necessaire.

Verdict Lot 0: le repo possede deja un atelier documentaire local tres proche
du besoin produit, mais le socle Frida V1 doit d'abord formaliser la frontiere
entre dossier applicatif et repertoire Nextcloud. Le meilleur Lot 1 est donc un
contrat produit minimal et fake/local, pas un branchement WebDAV/Nextcloud live.
