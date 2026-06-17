# Frida V1 Nextcloud folders - Lot 10A files policy audit

Date: 2026-06-17
Scope: audit applicatif read-only et politique fichiers par dossier
Classement: `app/docs/states/audits/`
TODO source: `app/docs/todo-todo/product/frida-v1-nextcloud-folders-todo.md`
Spec source: `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`

## 1. Perimetre

Ce Lot 10A ne deplace, copie, lit, migre ni supprime aucun fichier utilisateur.
Il ne fait aucun appel Nextcloud live, aucun WebDAV fichier, aucun Sauron et
n'accede pas a la DB Nextcloud.

L'audit inventorie uniquement les surfaces applicatives FridaDev deja
persistantes:

- dossiers Frida UI via `workspace_folders`;
- etat Nextcloud local via `workspace_folder_nextcloud_links`;
- fichiers persistants de dossier via `workspace_files`;
- selections conversationnelles de fichiers via `workspace_file_selections`;
- documents actifs de conversation via `active_conversation_documents`.

Les sorties restent content-free: aucun contenu, aucun nom de fichier, aucune
cle `storage_key`, aucun chemin disque, aucune URL DAV, aucun XML, aucun secret.

## 2. Methode d'inventaire

Commande appliquee: lecture seule de la DB applicative depuis le conteneur
runtime `platform-fridadev`, avec requetes `SELECT` uniquement.

Champs volontairement exclus:

- `display_name` et `original_filename` des fichiers;
- `storage_key`;
- contenu texte ou binaire;
- chemin disque;
- URL ou payload Nextcloud.

Les dossiers sont representes par `workspace-folder:<id8>:<hash12>` derive du
nom cible sanitise, sans afficher le nom utilisateur.

## 3. Inventaire content-free au 2026-06-17

```json
{
  "active_folders": 2,
  "folder_sync_state_counts": {
    "linked": 2
  },
  "linked_folders": 2,
  "active_workspace_files_attached_to_active_folder": 10,
  "files_per_folder_ref": {
    "workspace-folder:36032d33:19d8227c5fac": 9,
    "workspace-folder:6d7051a8:124a66b955cc": 1
  },
  "workspace_file_content_kind_counts": {
    "document": 10
  },
  "workspace_file_media_kind_counts": {
    "text": 10
  },
  "workspace_file_mime_family_counts": {
    "application": 9,
    "text": 1
  },
  "workspace_file_source_extension_counts": {
    ".docx": 1,
    ".md": 1,
    ".pdf": 8
  },
  "workspace_file_source_kind_counts": {
    "ocr_derived": 1,
    "upload": 9
  },
  "workspace_file_status_counts": {
    "active": 7,
    "ocr_required": 3
  },
  "active_conversation_documents_counts": [
    {
      "status": "inactive",
      "media_kind": "image",
      "count": 3
    },
    {
      "status": "inactive",
      "media_kind": "text",
      "count": 3
    }
  ],
  "read_only_app_db": true,
  "nextcloud_live": false,
  "user_content_touched": false,
  "file_content_read": false,
  "file_names_exposed": false,
  "storage_key_exposed": false,
  "server_path_exposed": false
}
```

Lecture:

- les 2 dossiers Frida actifs sont deja `linked` depuis le Lot 9;
- 10 fichiers workspace actifs restent actuellement rattaches a ces dossiers
  dans le stockage applicatif existant;
- aucun document actif de conversation n'est actif dans cet inventaire; seules
  des lignes historiques inactives existent;
- aucun fichier n'a ete lu, ouvert, copie, deplace ou supprime.

## 4. Politique fichiers existants

Decision Lot 10A:

- pas de migration automatique des fichiers existants dans ce lot;
- pas de copie silencieuse vers Nextcloud;
- pas de suppression source silencieuse;
- pas de lecture de contenu pour "deviner" une destination;
- les fichiers existants restent dans `workspace_files` et leur stockage
  applicatif courant jusqu'a un lot de migration/copie dedie.

Un futur lot de migration devra:

- travailler dossier par dossier;
- verifier que le dossier Frida est `linked`;
- produire une preuve content-free avant/apres;
- copier ou migrer de maniere bornee, jamais par deplacement massif implicite;
- conserver la source tant que la preuve et le rollback ne sont pas actees;
- traiter les conflits sans ecraser un fichier Nextcloud existant;
- ne supprimer la source qu'apres decision humaine explicite si une suppression
  devient necessaire.

## 5. Politique futurs fichiers

Decision cible:

- un futur upload/document rattache a un dossier Frida devra etre range dans le
  dossier Nextcloud correspondant a ce dossier Frida;
- l'operation devra refuser ou reporter proprement si le dossier Frida n'est pas
  `linked`;
- le transport fichier Nextcloud, les retries, conflits et rollbacks seront un
  lot runtime dedie;
- ce Lot 10A ne livre aucun `PUT`, `GET`, `MOVE`, `DELETE` ou listing fichier
  Nextcloud.

Tant que ce runtime fichier n'est pas livre, les routes fichiers existantes
restent le comportement applicatif courant et ne doivent pas etre reinterpretees
comme preuve de rangement Nextcloud.

## 6. Separation documents, notes, exports et images

Documents actifs:

- restent une surface conversationnelle separee;
- ne deviennent pas automatiquement des fichiers de dossier Frida;
- ne sont pas rouverts par ce Lot 10A.

Fichiers workspace:

- restent des fichiers persistants attaches a un `workspace_folder_id`;
- sont la surface a aligner plus tard avec le dossier Nextcloud du dossier
  Frida.

Notes Markdown:

- futur lot separe;
- pas de creation, lecture ou stockage dans ce lot.

Exports:

- futur lot separe;
- destination probable sous un sous-dossier standard de type `Exports`, a
  confirmer en Lot 11/12;
- aucun export n'est genere ou deplace ici.

Images generees:

- futur lot separe;
- aucune generation ni migration image dans ce lot.

## 7. Garde-fous a conserver

- Aucun contenu fichier dans logs, docs, JSONL ou rapport.
- Aucun nom de fichier sensible dans les preuves.
- Aucun `storage_key`, chemin serveur, URL DAV, XML, token, cookie,
  `app-password` ou secret.
- Aucun `PROPFIND` Depth 1 ou listing de contenu pour les futurs lots fichier.
- Aucun overwrite Nextcloud automatique.
- Aucun deplacement ou suppression large.
- Toute future migration fichier doit avoir rollback et preuve content-free.

## 8. Limites avant Lot 11/12

Lot 10A ferme la politique, pas le runtime fichier.

Restent a livrer:

- choix des sous-dossiers standards par dossier Frida;
- creation eventuelle de sous-dossiers `Documents`, `Notes`, `Exports`,
  `Images` ou variante documentee;
- runtime futur pour ranger les nouveaux fichiers dans Nextcloud;
- lot de migration/copie des fichiers existants, s'il est decide;
- preparation separee Notes / Exports / Images.
