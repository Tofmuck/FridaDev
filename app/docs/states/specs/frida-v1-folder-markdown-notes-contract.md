# Frida V1 - Folder Markdown notes contract

Statut: spec source-of-truth Notes V1 ouverte par Lot 1 docs-only
Date: 2026-06-18
Roadmap active: `app/docs/todo-todo/product/frida-v1-folder-markdown-notes-todo.md`
Audit Lot 0: `app/docs/states/audits/frida-v1-folder-markdown-notes-lot0-audit-2026-06-18.md`
Socle dossiers source: `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
Contrat Documents source: `app/docs/states/specs/frida-v1-documents-ingestion-contract.md`

## 1. Verdict de plan

Existe-t-il un meilleur plan ?

Non. Le bon plan est de graver ce contrat Notes V1 en docs-only avant tout
runtime, toute migration DB, toute route serveur, tout patch frontend et tout
acces Nextcloud live.

Tout lot futur Notes V1 doit appliquer ce contrat. Si un lot rencontre une
contradiction produit, il s'arrete avant patch et ouvre un micro-lot de recalage
documentaire.

## 2. Modele produit Notes V1

Une note Notes V1 est un fichier Markdown rattache a un dossier Frida produit.

Regle centrale:

```text
workspace_folder linked -> note Markdown -> /Frida/<dossier>/Notes
```

Une note V1 appartient a un `workspace_folder`. Le dossier visible dans l'UI
reste le centre produit. Notes V1 ne cree pas une deuxieme notion de dossier et
ne depend jamais de la DB Nextcloud.

La cible normative d'une note est:

```text
/Frida/<dossier>/Notes/<titre_sanitise>.md
```

Invariants:

- seuls les dossiers Frida `linked` sont eligibles;
- les etats `local_only`, `sync_pending`, `sync_error`, `conflict` et `deleted`
  bloquent toute ecriture Notes;
- le sous-dossier standard `Notes` doit exister et etre une collection WebDAV
  valide;
- un `PROPFIND 207` seul ne prouve pas un dossier: la reponse est parsee en
  memoire et doit confirmer `collection`;
- une cible `Notes` absente, non-collection, inaccessible ou ambigue produit un
  refus content-free;
- aucun lot Notes V1 n'accede directement a la DB Nextcloud;
- aucun lot Notes V1 ne liste le contenu Nextcloud comme preuve generale.

## 3. Frontieres produit

### 3.1 Notes vs Documents

Documents V1 gere les documents sources et fichiers persistants sous:

```text
/Frida/<dossier>/Documents
```

Notes V1 gere uniquement des fichiers Markdown notes sous:

```text
/Frida/<dossier>/Notes
```

Notes V1 ne reutilise pas `workspace_files`, ne reutilise pas les routes
`/api/workspace-folders/<folder_id>/files` et ne reutilise pas
`workspace_file_selections`.

### 3.2 Notes vs Exports

Une note est un objet de travail vivant. Un export est un artefact produit par
le chantier Exports sous:

```text
/Frida/<dossier>/Exports
```

Notes V1 ne produit pas d'export Markdown, TXT, DOCX ou PDF.

### 3.3 Notes vs Images, Biblio, Agenda, Mail, Memory/RAG

Notes V1 ne livre pas:

- stockage d'images generees;
- Biblio ou Catalogue;
- Agenda;
- Mail;
- Memory/RAG global;
- Identity;
- Summary;
- TTS/SMS.

Lire ou completer une note dans une conversation ne nourrit pas Memory, RAG,
Identity ou Summary par confusion.

## 4. Modele local Notes

Notes V1 exige un modele local dedie Notes, distinct de `workspace_files`.

Cible recommandee:

```text
workspace_folder_notes
```

Cette table ou ce store est strictement rattache a `workspace_folders.id`. Son
absence est un no-go pour les lots runtime de creation, liste, lookup, append ou
lecture.

Le modele local stocke uniquement:

- id note applicatif;
- `workspace_folder_id`;
- titre user-facing lorsque utile a l'UI;
- hash/ref courte du titre pour les surfaces techniques;
- nom cible sanitise interne;
- etat local;
- etat Nextcloud;
- remote ref content-free;
- ETag exact interne pour `If-Match`;
- hash/ref technique de l'ETag;
- timestamps;
- reason code content-free.

Etats locaux initiaux:

- `available`;
- `sync_error`;
- `conflict`;
- `deleted`;
- `unavailable`.

Etats Nextcloud initiaux:

- `linked`;
- `sync_error`;
- `deleted`.

Notes V1 ne stocke jamais le corps Markdown localement. Le corps Markdown est
lu depuis Nextcloud a la demande, garde seulement en memoire pour le tour utile
ou l'append, puis non persiste localement.

Un cache local du corps Markdown est hors V1. Il releve d'un chantier post-V1
separe.

## 5. Surfaces API

L'API Notes V1 reste sous le namespace dossier:

```text
/api/workspace-folders/<folder_id>/notes*
```

Interdits V1:

- route globale `/api/notes*`;
- reutilisation de `/api/workspace-folders/<folder_id>/files`;
- reutilisation de `workspace_file_selections`;
- route parallele qui contourne `workspace_folders`.

Les surfaces HTTP futures separent:

- projection utilisateur, avec titre visible;
- projection technique content-free, sans titre brut sensible, corps Markdown,
  ETag brut, cible distante brute, URL DAV, chemin DAV, XML, payload WebDAV ou
  secret.

## 6. Operations V1

### 6.1 Creer une note

L'utilisateur demande la creation dans le dossier Frida courant ou dans un
dossier cible resolu sans ambiguite.

Flux attendu:

- verifier que le dossier est `linked`;
- verifier que le sous-dossier `Notes` existe et est une collection WebDAV;
- normaliser le titre utilisateur;
- construire la cible `<titre_sanitise>.md`;
- refuser titre absent, vide, invalide ou ambigu;
- refuser conflit local ou conflit Nextcloud;
- creer la note par ecriture anti-ecrasement;
- persister le modele local Notes;
- compenser strictement la cible creee par ce flux si la persistance locale
  echoue.

Creation anti-ecrasement:

```text
PUT + If-None-Match: *
```

ou mecanisme equivalent qui prouve une creation sans overwrite.

### 6.2 Lister les notes d'un dossier

La liste appartient au dossier Frida courant.

Projection utilisateur:

- titre visible;
- statut lisible;
- date de creation/modification lorsque disponible;
- taille ou compteur sobre lorsque disponible;
- etat de synchronisation comprehensible.

Projection technique:

- compteurs;
- refs/hashes courts;
- statuts;
- reason codes.

Les notes `deleted` sont exclues de la liste utilisateur active.

### 6.3 Retrouver une note

Resolution V1 autorisee:

- titre exact ou titre sanitise;
- selection explicite dans la liste;
- metadonnees du read-model local Notes.

Cible absente ou ambigue:

- refus propre;
- demande de clarification cote utilisateur;
- aucune selection automatique.

Notes V1 ne livre pas de recherche plein texte riche dans le corps Markdown.

### 6.4 Completer une note

Completer signifie append uniquement a la fin de la note existante.

Interdits:

- insertion au milieu;
- reecriture globale;
- remplacement complet;
- append sans cible claire;
- patch aveugle sans version distante.

Format d'append V1:

```text
\n\n---\n\n
```

suivi du bloc Markdown ajoute. V1 n'ajoute pas d'horodatage automatique.

Flux attendu:

- resoudre clairement la note cible;
- faire un `GET` borne;
- recuperer l'ETag exact;
- construire le nouveau corps en memoire;
- verifier la limite d'append entrant;
- ecrire par `PUT If-Match`;
- refuser tout conflit ETag/version;
- ne pas persister le corps Markdown localement.

### 6.5 Lire / preparer une note pour conversation

La lecture est autorisee uniquement apres demande explicite de l'utilisateur.

Regles:

- `GET` borne depuis Nextcloud;
- injection du corps Markdown seulement dans le tour utile;
- aucun stockage local du corps;
- aucune alimentation Memory/RAG/Identity/Summary;
- note entiere ou refus propre;
- pas de troncature silencieuse presentee comme lecture complete.

## 7. Operations hors V1

Notes V1 ne livre pas:

- suppression utilisateur de note;
- editeur Markdown complet;
- insertion au milieu;
- reecriture globale;
- remplacement complet;
- recherche plein texte riche;
- export Markdown/TXT/DOCX/PDF;
- stockage local du corps Markdown.

Suppression distante autorisee seulement pour rollback/cleanup strict d'une
cible synthetique ou creee par le flux courant. Ce n'est pas une fonction
utilisateur V1.

## 8. Ecriture et concurrence

Creation:

- ecriture anti-ecrasement;
- conflit de nom = refus content-free;
- aucun renommage automatique.

Append:

- `GET` borne;
- ETag exact interne;
- construction du nouveau corps en memoire;
- `PUT If-Match`;
- conflit ETag/version = refus content-free.

ETag:

- ETag brut interne uniquement;
- jamais expose dans logs;
- jamais expose dans JSONL;
- jamais expose dans observabilite;
- jamais expose dans payload technique;
- hash/ref technique autorise.

## 9. Limites V1

Lecture/preparation conversationnelle:

```text
120_000 caracteres Markdown maximum
```

Append entrant:

```text
20_000 caracteres Markdown maximum
```

Au-dela:

- refus propre;
- reason code content-free;
- aucune troncature silencieuse;
- aucune preuve contenant le corps Markdown.

## 10. Projections et content-free

Projection utilisateur autorisee:

- titre visible;
- statut lisible;
- date de creation/modification lorsque disponible;
- taille ou compteur sobre lorsque disponible;
- etat de synchronisation comprehensible.

Projection technique autorisee:

- `note_ref`;
- `title_hash`;
- `etag_hash` ou `etag_present`;
- `status`;
- `reason_code`;
- compteurs.

Interdits en projection technique, logs, JSONL, dashboard et observabilite:

- corps Markdown;
- titre brut sensible;
- ETag brut;
- cible distante brute;
- URL DAV;
- chemin DAV;
- XML;
- payload WebDAV;
- secret;
- token;
- cookie;
- app-password.

## 11. Reason codes Notes V1

Catalogue initial:

- `folder_note_folder_not_linked`;
- `folder_note_notes_target_missing`;
- `folder_note_notes_target_not_collection`;
- `folder_note_notes_target_unavailable`;
- `folder_note_name_invalid`;
- `folder_note_name_conflict`;
- `folder_note_create_ok`;
- `folder_note_append_ok`;
- `folder_note_list_ok`;
- `folder_note_lookup_ok`;
- `folder_note_lookup_ambiguous`;
- `folder_note_not_found`;
- `folder_note_too_large`;
- `folder_note_append_too_large`;
- `folder_note_version_conflict`;
- `folder_note_local_persistence_failed`;
- `folder_note_remote_compensation_ok`;
- `folder_note_remote_compensation_failed`;
- `folder_note_nextcloud_error_redacted`.

Reason codes interdits:

- titre utilisateur;
- corps Markdown;
- chemin DAV;
- URL DAV;
- ETag brut;
- detail XML;
- secret ou valeur d'authentification.

## 12. Invariants securite

- Pas de DB Nextcloud directe.
- Pas de listing Nextcloud comme preuve generale.
- Pas de contenu Markdown dans logs, JSONL, dashboard ou observabilite
  technique.
- Pas de titre brut sensible dans les surfaces techniques.
- Pas de chemin DAV, URL DAV, XML ou payload WebDAV brut.
- Pas de secret, token, cookie ou app-password.
- Pas d'ecriture si le dossier n'est pas `linked`.
- Pas d'ecriture si `Notes` n'est pas une collection valide.
- Pas d'overwrite.
- Pas de suppression utilisateur V1.
- Pas de route qui contourne `workspace_folders`.

## 13. Criteres Lot Z

Pour cloturer Notes V1, Lot Z doit prouver avec artefacts content-free:

- create synthetique;
- collision synthetique sans overwrite;
- list;
- lookup;
- append;
- read;
- refus taille lecture;
- refus taille append;
- conflit ETag fake/unit;
- smoke live ETag uniquement avec cible synthetique et preuve propre;
- smoke live ETag marque `not_applicable` / `covered_by_unit_tests` quand la
  preuve live propre n'existe pas;
- cleanup synthetique;
- scan anti-fuite logs/JSONL/docs.

Lot Z ne doit pas vendre `met` pour un conflit ETag live non prouve. Le verdict
`met_with_documented_limit` est acceptable quand le cas ETag live est couvert
par tests unitaires et documente comme non applicable live.

## 14. Points faibles a surveiller

- Confusion Note vs Document.
- Confusion Note vs Export.
- Creation dans `/Documents`.
- Reutilisation de `workspace_files`.
- Reutilisation des routes `/files`.
- Reutilisation de `workspace_file_selections`.
- Stockage local du corps Markdown.
- Fuite de titre ou corps Markdown dans observabilite.
- Append sans cible claire.
- ETag ignore.
- Route parallele.
- Choix produit reporte dans un lot applicatif.
