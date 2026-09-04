# Frida V1 - Folder Markdown notes contract

Statut: spec source-of-truth Notes V1 cloturee en Lot Z
Date: 2026-06-18
Roadmap archivee: `app/docs/todo-done/product/frida-v1-folder-markdown-notes-todo.md`
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

Depuis le Lot 2, le read-model local Notes est livre par:

- `app/core/workspace_folder_notes.py` pour statuts, sanitisation et projections
  user-facing / techniques content-free;
- `app/core/workspace_folder_notes_store.py` pour la table applicative
  obligatoire `workspace_folder_notes`;
- `app/core/conversations_maintenance.py` pour la creation idempotente de table
  via le pattern applicatif existant `ensure_schema(cur)`.

Le Lot 2 ne cree, lit, modifie ni supprime aucune note Nextcloud. Il ne livre
pas de route serveur Notes, pas de frontend Notes et pas de transport WebDAV
Notes. Ses statuts locaux preparent les garde-fous de creation, mais ne
constituent pas une preuve que le sous-dossier `Notes` existe ou est une
collection WebDAV valide; cette verification reelle commence au Lot 3.

Depuis le micro-correctif Lot 2.1, les lectures du read-model local Notes
peuvent fail-closed via `WorkspaceFolderNoteLookupError` avec le reason code
content-free `folder_note_lookup_failed`. Une panne DB/store ne doit pas etre
confondue avec une liste vide ou une note absente dans les futurs chemins
runtime Notes.

Depuis le Lot 3, la creation de note Markdown est livree par:

- `app/core/workspace_folder_note_nextcloud_client.py` pour le transport WebDAV
  Notes borne;
- `app/core/workspace_folder_note_nextcloud_runtime.py` pour l'orchestration
  creation Nextcloud-first puis persistance locale;
- `app/core/workspace_folder_notes_service.py` pour la surface HTTP
  namespaced;
- `POST /api/workspace-folders/<folder_id>/notes` pour creer une note dans le
  dossier Frida cible.

Le Lot 3 verifie reellement `Notes` par `PROPFIND Depth: 0` et confirmation
`collection`, ecrit avec `PUT + If-None-Match: *`, n'accepte que `201` comme
creation sure, persiste ensuite dans `workspace_folder_notes`, et ne compense
par DELETE qu'avec `If-Match` sur l'unique ETag fort, syntaxiquement valide et
conserve exactement, renvoye par cette creation. Wildcard `*`, ETag faible,
liste, valeur non citee, malformee ou hors borne valent propriete non prouvee,
sans DELETE. Si la precondition est refusee, la note distante est conservee et
le reliquat est signale content-free. La preuve live synthetique
content-free est:
`app/docs/states/baselines/notes-smokes/frida-v1-notes-lot3-create-live-20260618T095734Z.jsonl`.

Depuis le Lot 4, la liste utilisateur des notes d'un dossier est livree par:

- `app/core/workspace_folder_notes_list.py` pour l'orchestration de liste depuis
  le read-model local Notes;
- `GET /api/workspace-folders/<folder_id>/notes` pour la surface HTTP
  namespaced.

La liste Lot 4 ne contacte pas Nextcloud/WebDAV, ne lit pas le corps Markdown,
exclut les notes `deleted` par defaut et fail-closed avec
`folder_note_lookup_failed` si le store Notes est indisponible. Les titres sont
visibles dans `note_v1_user`; `note_v1_technical` reste content-free.

Depuis le Lot 5, la resolution d'une note dans un dossier est livree par:

- `app/core/workspace_folder_notes_lookup.py` pour le lookup local
  content-free;
- `GET /api/workspace-folders/<folder_id>/notes/<note_id>` pour la selection
  explicite par id de note;
- `GET /api/workspace-folders/<folder_id>/notes/lookup?title=...` pour le titre
  exact, le titre sanitise ou la cible `.md`.

Le lookup Lot 5 ne contacte pas Nextcloud/WebDAV, ne lit pas le corps Markdown,
ne fait aucune recherche plein texte, exclut les notes `deleted`, refuse une
ambiguite avec `folder_note_lookup_ambiguous`, distingue une note absente
`folder_note_not_found` d'une panne store `folder_note_lookup_failed`, et garde
la projection technique sans titre brut, corps Markdown, ETag brut, cible
distante brute, chemin/URL DAV, XML ou secret.

Depuis le Lot 6, l'append final d'une note existante est livre par:

- `app/core/workspace_folder_notes_append.py` pour l'orchestration `GET` borne,
  ETag, append en memoire et `PUT If-Match`;
- `POST /api/workspace-folders/<folder_id>/notes/<note_id>/append` pour la
  surface HTTP namespaced.

Le Lot 6 lit le corps Markdown distant uniquement en memoire pendant
l'operation, refuse append vide, append trop long, note totale trop longue,
ETag absent, conflit `If-Match`, note non eligible et panne locale/distante. Il
ne persiste jamais le corps Markdown localement. Si le PUT distant reussit sans
retourner d'ETag, l'operation reste un echec: le runtime tente une relecture
bornee pour recuperer un ETag courant et restaurer le contenu precedent avec
`If-Match` uniquement si le Markdown relu correspond exactement au Markdown
appendu attendu par Frida; si cette compensation n'est pas prouvable, le
read-model local est marque `sync_error` content-free. Si le PUT distant reussit
puis la persistance locale echoue, une compensation distante stricte tente de
restaurer le contenu precedent avec l'ETag post-append; si elle echoue ou est
impossible, l'API retourne un etat content-free d'echec partiel et jamais un
succes silencieux.

Depuis le Lot 7, la lecture / preparation conversationnelle d'une note existante
est livree par:

- `app/core/workspace_folder_notes_read.py` pour l'orchestration `GET` borne et
  la construction du payload conversationnel;
- `app/core/workspace_folder_notes_prompt_lane.py` pour l'injection current-turn
  dans le prompt chat depuis une selection explicite;
- `POST /api/workspace-folders/<folder_id>/notes/<note_id>/prepare` pour la
  surface HTTP namespaced de lecture/preparation API;
- `/api/chat` avec `workspace_note_id` ou `workspace_note_ids` pour l'injection
  conversationnelle reelle du tour courant.

Le Lot 7 lit le corps Markdown distant uniquement apres action explicite, garde
le corps seulement en memoire, le retourne dans `note_conversation` pour la
surface API et l'injecte dans une lane Notes dediee seulement quand le tour chat
porte explicitement la note demandee. Les projections techniques, logs, JSONL,
observabilite et `note_nextcloud` restent content-free.
La lecture applique la limite V1 de 120_000 caracteres Markdown et refuse une
note trop grande sans troncature silencieuse. Elle ne nourrit jamais
Memory/RAG/Identity/Summary.

Depuis le Lot 8, l'observabilite et les smokes transverses Notes V1 sont
valides par artefact content-free:
`app/docs/states/baselines/notes-smokes/frida-v1-notes-lot8-observability-smokes-20260618T125408Z.jsonl`.
La portee de cette preuve est clarifiee par:
`app/docs/states/baselines/notes-smokes/frida-v1-notes-lot8-1-proof-scope-20260618T131304Z.jsonl`.

Cette preuve couvre create, collision de nom, list, lookup, append,
read/prepare, injection de la lane Notes utilisee par `/api/chat`, cleanup
synthetique, scan d'observabilite et scan d'artefact. Le cas conflit
ETag/version live est volontairement `not_applicable` / `covered_by_unit_tests`
en Lot 8; il ne doit pas etre presente comme `met` sans preuve live propre sur
une cible synthetique.

Interpretation normative Lot 8.1:

- `LOT8_RUNTIME_REDACTED.secret_available=false` dans l'artefact historique ne
  prouve pas une absence de secret runtime. Lot Z doit utiliser une formulation
  non ambigue: `secret_configured_status=redacted` et
  `secret_value_displayed=false`.
- `LOT8_SYNTHETIC_CHAT_INJECTION.provider_live=false` signifie que Lot 8 prouve
  la lane applicative `/api/chat` avec provider fake et surfaces content-free.
  Lot 8 ne prouve pas une generation modele/provider live.

Depuis le Lot Z, Notes Markdown V1 est cloture avec verdict
`met_with_documented_limit` par artefact content-free:
`app/docs/states/baselines/notes-smokes/frida-v1-notes-lotz-closure-20260618T134905Z.jsonl`.

Le verdict Lot Z confirme create, collision sans overwrite, list, lookup,
append, read/prepare, injection de la lane applicative `/api/chat`, cleanup
distant/local et scans anti-fuite sur notes synthetiques uniquement. Le conflit
ETag/version live reste `not_applicable` / `covered_by_unit_tests`: il est
couvert par tests fake/unit et contrat serveur, sans etre vendu comme smoke
live `met`. Aucune generation provider live n'est prouvee par Lot Z; la preuve
chat reste une preuve de lane applicative avec provider fake.

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

Table applicative obligatoire:

```text
workspace_folder_notes
```

Cette table est strictement rattachee a `workspace_folders.id`, distincte de
`workspace_files` et obligatoire pour Notes V1.

Absence de la table `workspace_folder_notes` = no-go Lot 2 et no-go runtime de
creation, liste, lookup, append ou lecture.

Le store/module Python Notes est seulement l'acces applicatif a cette table. Il
ne remplace pas la persistance locale obligatoire.

La migration applicative Lot 2 est idempotente: `CREATE TABLE IF NOT EXISTS`,
`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, index `IF NOT EXISTS`. Toute
application sur la DB OVH active doit etre precedee d'un backup applicatif
FridaDev date et d'une strategie rollback documentee.

Backup OVH Lot 2 avant application live de la migration:
`/opt/platform/_codex_reports/frida-v1-notes-lot2-db-backup-20260618T093415Z.dump`.

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

Depuis le Lot 3, la premiere surface HTTP Notes livree est:

```text
POST /api/workspace-folders/<folder_id>/notes
```

Payload utilisateur minimal:

```json
{"title": "Titre utilisateur", "markdown": "# contenu initial optionnel"}
```

Cette route ne stocke pas le corps Markdown localement. Le titre est visible
cote utilisateur; la projection technique et `note_nextcloud` restent
content-free.

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

Etat Lot 3 livre:

- dossier non `linked`: refus avant WebDAV;
- titre absent/invalide ou collision locale de sanitisation: refus avant WebDAV;
- `Notes` absent, non-collection ou inaccessible: refus content-free;
- `PUT` anti-ecrasement: seul `201` est accepte comme creation sure;
- `200` / `204` / statut overwrite-like: conflit content-free;
- succes distant puis persistance locale echouee: DELETE conditionnel seulement
  sur l'unique ETag fort, syntaxiquement valide et conserve exactement, de la
  creation; toute autre forme vaut propriete non prouvee sans DELETE;
- cible absente, precondition refusee, propriete non prouvee et transport en
  echec restent des etats content-free distincts;
- corps Markdown jamais persiste localement;
- titre brut, corps Markdown, ETag brut, cible distante brute, URL DAV, chemin
  DAV, XML, payload WebDAV et secret interdits dans les surfaces techniques.

Creation anti-ecrasement:

```text
PUT + If-None-Match: *
```

ou mecanisme equivalent qui prouve une creation sans overwrite.

### 6.2 Lister les notes d'un dossier

La liste appartient au dossier Frida courant.

Surface livree Lot 4:

```text
GET /api/workspace-folders/<folder_id>/notes
```

Invariants Lot 4:

- la liste est servie depuis `workspace_folder_notes` uniquement;
- aucun appel WebDAV/Nextcloud live n'est fait pour lister;
- aucun corps Markdown n'est lu ou persiste;
- dossier inexistant ou supprime: refus HTTP content-free;
- dossier non `linked`: refus content-free avec `folder_note_folder_not_linked`;
- panne du store Notes: refus fail-closed avec `folder_note_lookup_failed`, pas
  de fausse liste vide;
- liste vide reelle: `ok=true`, `items=[]`, `count=0`;
- notes `sync_error` et `conflict` restent visibles avec un statut honnete;
- notes `deleted` exclues de la liste active.

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

Interdits dans la projection technique et les logs/events de liste:

- titre brut;
- corps Markdown;
- ETag brut;
- `target_name`;
- `remote_note_ref`;
- chemin ou URL DAV;
- XML ou payload WebDAV;
- secret, token, cookie ou app-password.

### 6.3 Retrouver une note

Resolution V1 autorisee:

- id note UUID explicite issu de la liste utilisateur;
- titre exact ou titre sanitise;
- selection explicite dans la liste;
- metadonnees du read-model local Notes.

Surfaces livrees Lot 5:

```text
GET /api/workspace-folders/<folder_id>/notes/<note_id>
GET /api/workspace-folders/<folder_id>/notes/lookup?title=...
```

Invariants Lot 5:

- read-model local Notes uniquement;
- aucun appel WebDAV/Nextcloud live;
- aucun corps Markdown lu;
- aucune recherche plein texte;
- dossier absent, supprime ou non `linked`: refus content-free;
- note `deleted`: non retournee;
- titre absent/invalide: refus content-free;
- cible absente: `folder_note_not_found`;
- cible ambigue: `folder_note_lookup_ambiguous`, sans choix arbitraire;
- panne store: `folder_note_lookup_failed`, jamais une fausse absence;
- projection utilisateur: titre visible;
- projection technique/logs/events: refs, hashes, statuts, reason codes et
  compteurs seulement.

Cible absente ou ambigue:

- refus propre;
- demande de clarification cote utilisateur;
- aucune selection automatique.

Notes V1 ne livre pas de recherche plein texte riche dans le corps Markdown.

### 6.4 Completer une note

Completer signifie append uniquement a la fin de la note existante.

Surface livree Lot 6:

```text
POST /api/workspace-folders/<folder_id>/notes/<note_id>/append
```

Payload utilisateur:

```json
{"markdown": "bloc Markdown a ajouter"}
```

Invariants Lot 6:

- resolution par `note_id` uniquement; un titre doit passer par le lookup Lot 5;
- dossier `linked` obligatoire;
- note active, disponible et `linked` obligatoire;
- corps Markdown lu depuis Nextcloud par GET borne uniquement en memoire;
- ETag distant obligatoire;
- append final uniquement, avec separateur `\n\n---\n\n` si la note existante
  n'est pas vide;
- ecriture par PUT avec `If-Match`;
- conflit ETag/version: `folder_note_version_conflict`;
- append vide: `folder_note_append_empty`;
- append entrant au-dessus de 20_000 caracteres: `folder_note_append_too_large`;
- note totale au-dessus de 120_000 caracteres apres append:
  `folder_note_too_large`;
- GET distant impossible: `folder_note_remote_read_failed`;
- PUT distant impossible: `folder_note_remote_write_failed`;
- ETag absent: `folder_note_etag_missing`;
- ETag post-ecriture absent: echec obligatoire, relecture bornee pour tenter de
  recuperer un ETag courant, restauration du contenu precedent seulement si le
  Markdown relu correspond exactement au Markdown appendu attendu par Frida,
  sinon note locale marquee `sync_error` content-free;
- panne de persistence locale apres PUT: `folder_note_local_persistence_failed`
  avec compensation distante tentee et resultat content-free;
- aucun corps Markdown, ETag brut, target name, chemin/URL DAV, XML, payload
  WebDAV ou secret dans logs, JSONL, observabilite ou projection technique.

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

Surface livree Lot 7:

```text
POST /api/workspace-folders/<folder_id>/notes/<note_id>/prepare
POST /api/chat avec workspace_note_id ou workspace_note_ids
```

Regles:

- `GET` borne depuis Nextcloud;
- injection du corps Markdown seulement dans le tour utile si `/api/chat` porte
  explicitement `workspace_note_id` ou `workspace_note_ids`;
- budget prompt Notes V1: une seule note injectee par tour et 120_000
  caracteres Markdown maximum au total;
- toute note valide demandee au-dela de la limite est signalee comme non
  injectee avec `folder_note_turn_limit_exceeded` avant lecture distante, sans
  recuperation Markdown silencieuse ni troncature;
- aucun stockage local du corps;
- aucune alimentation Memory/RAG/Identity/Summary;
- note entiere ou refus propre;
- pas de troncature silencieuse presentee comme lecture complete.

Invariants Lot 7:

- resolution par `note_id` uniquement; un titre doit passer par le lookup Lot 5;
- la route `/prepare` expose le payload de preparation API; l'injection reelle
  au modele passe par la lane Notes de `/api/chat`;
- dossier `linked` obligatoire;
- note active, disponible et `linked` obligatoire;
- corps Markdown lu depuis Nextcloud par GET borne uniquement en memoire;
- taille maximale: 120_000 caracteres Markdown;
- note trop grande: `folder_note_too_large`;
- limite de tour depassee: `folder_note_turn_limit_exceeded`;
- GET distant impossible: `folder_note_remote_read_failed`;
- succes: `folder_note_read_ok`;
- `note_conversation.markdown_content` est la surface API de preparation;
- la lane Notes de `/api/chat` peut contenir le Markdown uniquement dans le
  prompt du tour courant;
- `note_nextcloud`, projections techniques et events restent content-free;
- `note_conversation.memory_rag_identity_summary=not_used` rappelle la frontiere
  avec Memory/RAG/Identity/Summary.

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

Injection prompt Notes par tour:

```text
1 note injectee maximum
120_000 caracteres Markdown maximum au total
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
- `folder_note_read_ok`;
- `folder_note_list_ok`;
- `folder_note_lookup_ok`;
- `folder_note_lookup_ambiguous`;
- `folder_note_lookup_failed`;
- `folder_note_not_found`;
- `folder_note_too_large`;
- `folder_note_append_too_large`;
- `folder_note_version_conflict`;
- `folder_note_local_persistence_failed`;
- `folder_note_remote_compensation_ok`;
- `folder_note_remote_compensation_missing`;
- `folder_note_remote_compensation_precondition_failed`;
- `folder_note_remote_compensation_ownership_unverified`;
- `folder_note_remote_compensation_failed`;
- `folder_note_nextcloud_error_redacted`;
- `folder_note_turn_limit_exceeded`.

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
`met_with_documented_limit` est accepte pour Notes V1: le cas ETag live est
couvert par tests unitaires/serveur et documente comme non applicable live.

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
