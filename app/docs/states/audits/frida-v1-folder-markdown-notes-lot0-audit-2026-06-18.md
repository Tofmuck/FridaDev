# Frida V1 - Notes Markdown par dossier - Lot 0 audit existant

Date: 2026-06-18
Statut: audit read-only / docs-only
TODO source: `app/docs/todo-todo/product/frida-v1-folder-markdown-notes-todo.md`
Socle dossiers source: `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
Documents V1 source: `app/docs/states/specs/frida-v1-documents-ingestion-contract.md`

## Verdict de plan

Existe-t-il un meilleur plan ?

Non. Le bon plan est de preparer Notes V1 par audit read-only avant toute spec
runtime, tout modele local, toute route et tout acces Nextcloud live.

## Perimetre et discipline

Ce Lot 0 n'a pas modifie le runtime, n'a pas contacte Nextcloud, n'a pas lu de
secret, n'a pas cree de note et n'a pas applique de migration DB.

L'audit reste content-free:

- aucun corps Markdown;
- aucun nom de note utilisateur;
- aucun contenu utilisateur;
- aucun chemin DAV ou URL DAV;
- aucun XML;
- aucun payload WebDAV brut;
- aucun `storage_key`;
- aucun token, cookie, app-password ou secret.

## Sources relues

Documentation:

- `AGENTS.md`;
- `app/docs/todo-todo/product/frida-v1-folder-markdown-notes-todo.md`;
- `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`;
- `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`;
- `app/docs/states/specs/frida-v1-documents-ingestion-contract.md`;
- `app/docs/todo-done/product/frida-v1-documents-ingestion-todo.md`.

Code et tests:

- `app/core/workspace_folders.py`;
- `app/core/workspace_folders_service.py`;
- `app/core/workspace_folders_store.py`;
- `app/core/workspace_folder_nextcloud_client.py`;
- `app/core/workspace_folder_nextcloud_runtime.py`;
- `app/core/workspace_folder_nextcloud_links_store.py`;
- `app/core/workspace_folder_standard_subfolders.py`;
- `app/core/workspace_document_nextcloud_client.py`;
- `app/core/workspace_document_nextcloud_runtime.py`;
- `app/core/workspace_file_nextcloud_links_store.py`;
- `app/core/workspace_folder_documents.py`;
- `app/core/workspace_folder_document_list.py`;
- `app/core/workspace_folder_document_usage.py`;
- `app/core/workspace_files.py`;
- `app/core/workspace_files_service.py`;
- `app/web/chat_workspace_folders.js`;
- `app/web/chat_workspace_folders_sidebar.js`;
- `app/tests/unit/core/test_workspace_folders_contract.py`;
- `app/tests/unit/core/test_workspace_documents_ingestion.py`;
- `app/tests/unit/core/test_workspace_folder_documents.py`;
- `app/tests/test_server_workspace_folders_contract.py`;
- `app/tests/unit/frontend_chat/test_workspace_folders_module.js`.

## Synthese

Le chantier Notes peut s'appuyer sur trois acquis solides:

- `workspace_folders` est deja le modele produit des dossiers Frida;
- le sous-dossier standard `Notes` est deja cree/verifie comme collection pour
  les dossiers `linked`;
- Documents V1 a livre les patterns de transport fichier, projection
  user-facing vs projection technique, rollback, liens locaux et tests
  anti-fuite.

Mais Notes ne doit pas reprendre le modele Documents:

- `workspace_files` est reserve aux documents sources;
- la route `/api/workspace-folders/<id>/files` est une surface Documents;
- l'OCR Markdown de Documents est hors-scope Notes;
- les projections `document_v1_*` ne doivent pas devenir des projections Notes.

## Cartographie par surface

| Surface | Responsabilite actuelle | Classification Notes V1 |
| --- | --- | --- |
| `workspace_folders.py` | Facade dossier Frida, create/rename/delete, etat Nextcloud | Reutiliser tel quel comme entree dossier |
| `workspace_folders_service.py` | Reponses API dossiers et observabilite content-free | Reutiliser les patterns de reponse |
| `workspace_folders_store.py` | Validation nom dossier, projection dossier, CRUD local | Reutiliser les patterns de validation, pas le modele Note |
| `workspace_folder_nextcloud_client.py` | WebDAV dossier borne, `PROPFIND` Depth 0, collection XML parsee en memoire | Reutiliser tel quel pour verifier parent et `Notes` |
| `workspace_folder_nextcloud_runtime.py` | Creation/rename dossier Nextcloud-first, rollback | Reutiliser le pattern d'orchestration |
| `workspace_folder_nextcloud_links_store.py` | Lien dossier `workspace_folder` -> cible Nextcloud | Reutiliser comme source d'etat dossier `linked` |
| `workspace_folder_standard_subfolders.py` | Verification/creation `Documents`, `Notes`, `Exports`, `Images` | Reutiliser pour preconditions `Notes` |
| `workspace_document_nextcloud_client.py` | WebDAV fichier Documents: status, PUT create, DELETE exact | Adapter pour Notes; il manque GET et ETag/If-Match |
| `workspace_document_nextcloud_runtime.py` | Orchestration Documents Nextcloud-first | Adapter comme modele, sans reutiliser Documents |
| `workspace_file_nextcloud_links_store.py` | Lien technique document -> cible Nextcloud | Adapter le pattern; ne pas reutiliser la table |
| `workspace_folder_documents.py` | Projections Documents user/tech redacted | Adapter les principes; ne pas reutiliser les statuts Documents |
| `workspace_folder_document_list.py` | Liste Documents depuis `workspace_files` | Eviter pour Notes |
| `workspace_folder_document_usage.py` | Usage conversationnel Documents | Adapter les garde-fous, pas les types |
| `workspace_files.py` | Facade fichiers workspace Documents | Eviter comme modele Notes |
| `workspace_files_service.py` | Routes fichiers Documents, upload/delete/OCR | Eviter comme surface Notes |
| `chat_workspace_folders.js` | Normalisation UI dossiers et fichiers Documents | Adapter pattern de normalisation UI |
| `chat_workspace_folders_sidebar.js` | Sidebar dossiers, fichiers, OCR Markdown Documents | Adapter layout, eviter actions fichiers/OCR |
| Tests workspace folders | Fake WebDAV, collection, rollback, anti-fuite | Reutiliser les patterns de fake/test |
| Tests Documents | Upload/list/read/delete, liens, anti-fuite | Adapter les scenarios, pas les entites |

## Reutilisable tel quel

### Dossier produit et etat `linked`

`workspace_folders` reste le centre produit. Les lots Notes doivent obtenir le
dossier par les surfaces existantes et refuser toute ecriture si l'etat
Nextcloud n'est pas `linked`.

Reutilisable:

- normalisation d'id dossier;
- validation d'existence et tombstone dossier;
- projection `nextcloud_sync_state`;
- reason codes content-free de dossier;
- suppression dossier qui preserve fichiers/documents.

### Verification WebDAV collection

`workspace_folder_nextcloud_client.py` verifie deja une ressource WebDAV avec
`PROPFIND` Depth 0 et parse le XML en memoire pour confirmer `collection`.

Reutilisable:

- `folder_status_path(parent, "Notes")`;
- mapping 404 / conflit / indisponible;
- redaction des erreurs;
- interdiction de logger XML brut.

### Sous-dossiers standards

`workspace_folder_standard_subfolders.py` connait deja `Notes` comme constante
produit. Il fournit les patterns de records content-free pour cible existante,
cible creee, conflit et indisponibilite.

Notes V1 ne doit pas recreer cette responsabilite.

### Observabilite content-free

Les patterns existants utilisent:

- reason codes allowlistes;
- refs redacted;
- hash courts;
- compteurs;
- status classes;
- separation user-facing / technique.

Ces patterns sont reutilisables pour les futures projections Notes.

### Tests anti-fuite et fake WebDAV

Les tests existants prouvent deja:

- `PROPFIND 207` non-collection refuse;
- sous-dossier standard existant accepte;
- cible standard absente creee par `MKCOL`;
- payloads techniques sans contenu brut;
- frontend qui retire champs internes et valeurs dangereuses.

Ces tests fournissent le style a reproduire pour Notes.

## A adapter

### Transport WebDAV fichier

`workspace_document_nextcloud_client.py` apporte un bon modele:

- verification du sous-dossier cible comme collection;
- creation anti-ecrasement par `PUT` avec `If-None-Match: *`;
- acceptation stricte de `201` pour creation;
- `DELETE` exact pour rollback ou suppression cible connue;
- aucun listing large.

Pour Notes, il faut un client dedie ou un module tres explicitement parametre
sur le sous-dossier `Notes`.

Manques pour Notes:

- lecture bornee du corps Markdown par `GET`;
- recuperation de version distante / ETag;
- ecriture append par relecture + `PUT` avec `If-Match`;
- refus content-free si ETag absent ou conflit de version;
- limite de taille lecture et append;
- interdiction de logguer le corps Markdown.

### Orchestration Nextcloud-first

`workspace_document_nextcloud_runtime.py` est un modele pour:

- validation locale avant remote;
- conflit local avant ecriture;
- ecriture remote avant persistance locale;
- rollback remote si persistance locale echoue;
- payload technique content-free;
- log content-free.

Notes doit adapter ce pattern avec ses propres reason codes et son propre modele
local. Il ne doit pas appeler l'orchestration Documents.

### Liens locaux stricts

`workspace_file_nextcloud_links_store.py` montre:

- schema de liaison stricte avec FK applicatives;
- etats `linked`, `sync_error`, `deleted`;
- refs et hashes;
- fail-closed sur lookup si demande;
- marquage `deleted`.

Pour Notes, le pattern est utile mais la table ne doit pas etre reutilisee. Le
futur modele local Notes peut porter directement la liaison Nextcloud de la note
ou l'isoler dans une table dediee Notes, mais dans les deux cas la FK doit etre
`workspace_folders.id`.

### Projections user-facing vs techniques

`workspace_folder_documents.py` separe:

- projection utilisateur avec `display_name`;
- projection technique allowlistee et redacted;
- normalisation stricte des statuts et reason codes;
- ids non valides redacted.

Notes doit reprendre le principe avec des champs Notes:

- titre visible cote utilisateur;
- titre hash/ref courte cote technique;
- corps jamais present dans projection technique;
- ETag jamais expose brut.

### UI sidebar

La sidebar sait deja grouper par dossier et afficher une liste d'elements sous
un dossier. Ce pattern peut porter Notes, mais pas les composants fichiers:

- les actions upload fichier, OCR et edition OCR sont Documents;
- une future section Notes doit utiliser des libelles Notes;
- le corps Markdown ne doit pas etre mis dans l'etat UI technique ou logs.

### Routes existantes

La namespace existante `/api/workspace-folders*` est le bon ancrage. Le futur
runtime Notes devrait rester sous le dossier, par exemple une sous-surface
`/api/workspace-folders/<folder_id>/notes*`.

Ce n'est pas une route parallele produit si elle reste rattachee au dossier. A
l'inverse, une route globale `/api/notes*` serait a justifier fortement.

## A eviter

- Reutiliser `workspace_files` comme modele produit Notes.
- Stocker les notes sous `/Frida/<dossier>/Documents`.
- Confondre une note Markdown avec un document source ou un OCR Markdown derive.
- Reutiliser `/api/workspace-folders/<id>/files` pour Notes.
- Reutiliser `workspace_file_selections` comme selection de notes.
- Lancer une recherche plein texte riche non cadree.
- Injecter automatiquement les notes dans Memory/RAG/Identity/Summary.
- Logger un titre sensible, un corps Markdown, une cible distante brute ou un
  payload WebDAV.
- Etendre `workspace_files_service.py` ou `workspace_folder_documents.py` pour
  Notes.
- Ajouter du comportement a `workspace_folder_nextcloud_reconcile.py`.
- Faire une migration DB ou une route runtime dans Lot 0.

## Recommandation pour le modele local Notes futur

Lot 0 recommande de creer un modele local dedie Notes, porte par des modules
cibles:

- `app/core/workspace_folder_notes.py` pour projections et statuts;
- `app/core/workspace_folder_notes_store.py` pour persistance;
- `app/core/workspace_folder_note_nextcloud_client.py` pour transport WebDAV
  fichier sous `Notes`;
- `app/core/workspace_folder_note_nextcloud_runtime.py` pour orchestration
  create/append/read/delete test-only si necessaire.

Le nom exact des modules sera fixe dans la spec Lot 1, mais la responsabilite
doit rester separee de Documents.

### Table locale recommandee

Un schema dedie type `workspace_folder_notes` est recommande, avec FK stricte
vers `workspace_folders.id`.

Champs a cadrer en Lot 1:

- id note applicatif;
- `workspace_folder_id`;
- titre user-facing;
- hash/ref courte du titre;
- nom cible sanitise interne;
- etat local: available, sync_error, conflict, deleted, unavailable;
- etat Nextcloud: linked, sync_error, deleted;
- remote ref content-free;
- ETag exact stocke pour `If-Match`, jamais expose brut;
- hash court de l'ETag pour projection technique;
- timestamps;
- reason code content-free.

### Corps Markdown local

Decision Lot 0: Notes V1 ne stocke pas le corps Markdown en local.

Le modele local Notes stocke uniquement:

- metadonnees;
- statut local et statut Nextcloud;
- refs content-free;
- titre utilisateur si necessaire;
- cible interne;
- ETag exact interne pour `If-Match`;
- hash/ref technique;
- timestamps;
- reason codes.

Raison:

- Nextcloud est la source de verite du fichier Markdown;
- le stockage local du corps augmente le risque de fuite;
- l'append V1 fait `GET` borne, verifie ETag, construit le nouveau corps
  en memoire, puis `PUT If-Match`;
- la lecture conversationnelle fait `GET` borne a la demande utilisateur;
- le corps Markdown reste seulement en memoire pour le tour utile ou la
  construction d'append, puis n'est pas persiste localement.

Un cache local du corps Markdown est hors V1. S'il devient voulu plus tard, il
devra etre un chantier post-V1 separe avec politique de redaction, retention,
rollback et tests anti-fuite.

### Projections

Projection utilisateur:

- titre/nom de note visible;
- statut lisible;
- date de creation/modification;
- taille ou compteur sobre si disponible;
- etat sync comprehensible.

Projection technique:

- note_ref;
- title_hash;
- etag_hash ou etag_present;
- status;
- reason_code;
- counters;
- jamais le corps Markdown;
- jamais ETag brut;
- jamais cible distante brute.

## Surface API/UI recommandee

API:

- rester sous `/api/workspace-folders/<folder_id>/notes*`;
- ne pas creer `/api/notes*` tant qu'un besoin produit transverse n'existe pas;
- separer projections utilisateur et technique;
- refuser dossier non `linked` avant toute ecriture remote;
- renvoyer conflits et erreurs avec reason codes Notes content-free.

UI:

- reutiliser le pattern de section sous dossier dans la sidebar;
- ajouter une section Notes distincte des fichiers Documents;
- titres visibles pour l'utilisateur;
- corps visible seulement quand l'utilisateur ouvre/lit/complete la note;
- ne pas reutiliser les boutons OCR ou upload fichiers.

## Risques techniques avant Lot 1

- Le transport Notes a besoin de `GET` borne et ETag; le client Documents actuel
  ne les fournit pas.
- `If-Match` doit utiliser un ETag exact; l'ETag brut ne doit jamais sortir dans
  logs/preuves/projections.
- L'append implique une reecriture complete du fichier distant avec version
  distante; il faut tester conflit de version.
- Sans modele local Notes dedie, les listes et resolutions par titre pousseront
  vers un listing Nextcloud trop large ou vers `workspace_files`.
- Une UI qui melange fichiers et notes rendra l'utilisateur confus et brouillera
  les tests.
- Les fichiers existants de type OCR Markdown ne sont pas des Notes V1.
- La recherche plein texte riche doit rester hors V1 tant qu'elle n'a pas de
  contrat.
- Les modules Documents et tests existants sont deja volumineux; Notes doit
  demarrer dans des fichiers dedies.

## No-go avant Lot 1

- Demarrer un runtime Notes sans spec Notes V1 source-of-truth.
- Demarrer un runtime Notes sans modele local Notes dedie.
- Reutiliser `workspace_files` pour Notes.
- Faire une migration DB sans micro-lot avec backup/test/rollback.
- Lire ou lister Nextcloud live pour prouver Lot 0.
- Ajouter une route globale Notes hors namespace dossier.
- Stocker localement le corps Markdown dans Notes V1.
- Livrer append sans ETag / `If-Match`.
- Presenter un smoke ETag comme `met` si seul le test unitaire existe.

## Inputs pour Lot 1

Lot 1 doit produire une spec Notes V1 qui grave:

- modele local Notes dedie et schema cible;
- interdiction V1 de stocker le corps Markdown localement; cache local eventuel
  = post-V1 separe;
- API sous `/api/workspace-folders/<folder_id>/notes*`;
- transport WebDAV Notes: status collection, create, bounded GET, If-Match PUT,
  delete rollback strict si necessaire;
- limites 120_000 caracteres lecture/preparation et 20_000 caracteres append;
- format d'append `\n\n---\n\n`;
- reason codes Notes;
- projections utilisateur et technique;
- ETag brut interne uniquement, hash/ref en technique;
- tests anti-fuite;
- criteres Lot Z, dont conflit ETag fake/unit et live `not_applicable` si
  impossible proprement.
