# Frida V1 - Exports contract

Statut: spec source-of-truth Exports V1 ouverte, Lot 2 read-model livre
Date: 2026-06-18
Roadmap active: `app/docs/todo-todo/product/frida-v1-exports-todo.md`
Audit Lot 0: `app/docs/states/audits/frida-v1-exports-lot0-audit-2026-06-18.md`
Socle dossiers source: `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
Contrat Documents source: `app/docs/states/specs/frida-v1-documents-ingestion-contract.md`
Contrat Notes source: `app/docs/states/specs/frida-v1-folder-markdown-notes-contract.md`
Contrat export navigateur source: `app/docs/states/specs/chat-copy-export-contract.md`

## 1. Verdict de plan

Existe-t-il un meilleur plan ?

Non. Les decisions produit bloquantes ont ete donnees explicitement avant ce
Lot 1. Le bon plan est donc de graver le contrat Exports V1 en docs-only, sans
runtime, sans route serveur, sans UI, sans migration DB, sans Nextcloud/WebDAV
live, sans smoke et sans rebuild.

Tout lot futur Exports V1 doit appliquer ce contrat. Si un lot rencontre une
decision produit manquante ou une contradiction reelle, il doit s'arreter avant
tout patch qui figerait ou inventerait cette decision, y compris docs/spec,
avant commit et avant de cocher un lot. Il doit demander explicitement et ne
doit pas choisir en avancant.

## 2. Portee produit Exports V1

Un export V1 est un artefact documentaire produit par Frida a partir d'une
source explicitement choisie par l'utilisateur, rattache a un dossier Frida
produit et range durablement sous le sous-dossier standard `Exports`.

Regle centrale:

```text
workspace_folder linked -> export V1 -> /Frida/<dossier>/Exports
```

Le dossier visible dans l'UI reste le `workspace_folder`. Exports V1 ne cree
pas une deuxieme notion de dossier, ne depend pas de la DB Nextcloud et ne
remplace pas les chantiers Documents, Notes, Images, Biblio, Agenda ou Mail.

Exports V1 doit livrer une capacite utile mais bornee:

- produire Markdown, TXT, DOCX et PDF;
- ranger automatiquement l'export cree sous `/Frida/<dossier>/Exports`;
- retrouver et reutiliser un export existant selon le sens defini en section 10;
- rester content-free dans les surfaces techniques;
- refuser proprement ce qui depasse les limites V1.

## 3. Sources exportables V1

Les sources exportables V1 sont uniquement:

- conversation complete explicitement demandee;
- selection explicite de messages;
- reponse de Frida explicitement choisie;
- note Markdown existante Notes V1;
- document prepare ou lu par Documents V1, seulement si la lecture Documents V1
  est deja disponible proprement et si l'utilisateur choisit explicitement ce
  document comme source.

Regles communes:

- la source doit etre explicite;
- la source doit etre rattachee au dossier Frida cible ou resolue sans ambiguite
  dans ce dossier;
- le contenu exporte est complet ou l'operation est refusee;
- aucune troncature silencieuse n'est vendue comme export complet;
- une source ambigue, implicite ou hors contrat est refusee.

Sources refusees en V1:

- Biblio / Catalogue;
- Agenda;
- Mail;
- images generees comme objet produit;
- Memory/RAG;
- Identity;
- Summary;
- export admin logs;
- source implicite deduite du contexte sans action utilisateur explicite.

## 4. Acquisition des sources

Exports V1 ne lit jamais une source seulement parce qu'elle est listee,
retrouvee ou presente dans le dossier. Toute acquisition de contenu exige une
action utilisateur explicite et une capacite source deja livree proprement.

### 4.1 Conversation complete

La conversation complete est acquise depuis le store conversationnel deja utilise
par le chat et par l'export Markdown navigateur.

Regles:

- action utilisateur explicite obligatoire;
- messages systeme, outils et techniques exclus selon
  `chat-copy-export-contract.md`, sauf decision future explicite;
- conversation lue dans un ordre stable;
- si la conversation ne peut pas etre relue completement, export refuse avec un
  reason code content-free.

### 4.2 Selection explicite de messages

Une selection de messages contient uniquement les messages explicitement
selectionnes par l'utilisateur ou par une API qui les designe sans ambiguite.

Regles:

- aucun message ajoute par contexte implicite;
- ordre stable;
- messages introuvables, ambigus ou techniques refuses;
- selection complete ou refus.

### 4.3 Reponse de Frida choisie

Une reponse de Frida comme source doit etre explicitement designee.

Regles:

- pas de "derniere reponse" implicite;
- une action UI/API peut designer la derniere reponse seulement si cette action
  la nomme explicitement comme source;
- reponse absente, partielle ou ambigue = refus content-free.

### 4.4 Note Markdown existante

Une note Markdown existante est acquise via les capacites Notes V1 explicites.

Regles:

- lecture Notes V1 entiere ou refus;
- pas de reutilisation du read-model Notes comme read-model Exports;
- pas de stockage local durable du corps Markdown par Exports;
- pas d'append, modification ou suppression de note;
- pas de lecture implicite d'une note parce qu'elle est listee ou retrouvee.

### 4.5 Document prepare ou lu

Un document est exportable seulement si Documents V1 peut fournir une
lecture/preparation complete selon son contrat.

Regles:

- lecture complete ou refus;
- pas de relance ingestion par Exports;
- pas de relance OCR par Exports;
- pas de relance fallback visuel par Exports;
- pas de lecture implicite d'un document parce qu'il existe dans le dossier;
- si Documents V1 ne peut pas fournir une source proprement preparee, export
  refuse avec reason code content-free.

### 4.6 Export existant comme source d'un nouvel export

Un export existant peut devenir source d'un nouvel export uniquement par action
utilisateur explicite.

Regles:

- lecture bornee;
- contenu complet ou refus;
- pas d'injection chat automatique;
- pas de conversion implicite;
- pas de lecture parce qu'un export est liste ou retrouve.

## 5. Formats V1 et fidelite attendue

Formats livres par Exports V1:

- Markdown `.md`;
- texte brut `.txt`;
- DOCX `.docx`;
- PDF `.pdf`.

Fidelite V1:

- structure simple et honnete;
- titres, paragraphes et listes basiques conserves quand la source les expose;
- tableaux, images, styles avances, pagination fine, en-tetes/pieds de page et
  mise en page complexe hors V1 sauf preuve explicite dans un lot futur;
- si le moteur d'un format ne peut pas produire une sortie conforme aux limites
  V1, Frida refuse clairement l'export au lieu de produire un faux succes.

Politique par format:

- Markdown: format texte structure simple, lisible humainement, sans
  metadonnees techniques.
- TXT: texte brut lisible, sans promesse de structure riche.
- DOCX: document bureautique simple; un moteur minimal OOXML standard-library
  est autorise si les tests prouvent son ouverture et sa fidelite V1. Une
  dependance dediee est autorisee seulement si Lot 4 la documente, la teste et
  la garde bornable.
- PDF: rendu simple et honnete; une dependance ou un moteur dedie doit etre
  valide en Lot 4 avant tout runtime PDF. Si le moteur est absent ou
  incompatible, reason code de dependance indisponible et refus utilisateur.

Limites V1 initiales:

- contenu source normalise: `120_000` caracteres maximum par export;
- append ou composition incrementale d'export: hors V1;
- artefact genere: `25 MiB` maximum;
- generation: `180` secondes maximum;
- PDF genere: `100` pages maximum si le moteur expose un comptage fiable;
- si une limite ne peut pas etre verifiee proprement, l'export est refuse;
- pas de troncature silencieuse: contenu complet ou refus.

## 6. Modele local / read-model Exports

Exports V1 exige un modele local dedie, distinct de `workspace_files` et de
`workspace_folder_notes`.

Table applicative obligatoire cible:

```text
workspace_folder_exports
```

Cette table est strictement rattachee a `workspace_folders.id`. Elle ne remplace
pas `workspace_files`, ne reutilise pas `workspace_folder_notes` et ne cree pas
une deuxieme notion utilisateur de dossier.

Absence de cette table ou de son store applicatif = no-go Lot 2/runtime.

Lot 2 livre:

- table applicative `workspace_folder_exports` creee via le pattern applicatif
  `ensure_schema(cur)`;
- module de projection `app/core/workspace_folder_exports.py`;
- store dedie `app/core/workspace_folder_exports_store.py`;
- raccordement au schema applicatif par `app/core/conversations_maintenance.py`;
- tests unitaires dedies
  `app/tests/unit/core/test_workspace_folder_exports.py`.

Le modele local stocke uniquement des metadonnees et refs necessaires:

- id export applicatif;
- `workspace_folder_id`;
- titre/nom user-facing lorsque necessaire;
- hash/ref courte du titre;
- nom cible sanitise interne;
- format;
- source kind;
- source refs content-free;
- hash/ref de contenu ou de source pour la reutilisation explicite;
- etat local;
- etat Nextcloud;
- remote ref content-free;
- ETag exact interne si disponible;
- hash/ref technique de l'ETag;
- tailles/compteurs sobres;
- timestamps;
- reason code content-free.

Exports V1 ne stocke pas le contenu exporte brut localement. Les bytes generes
existent en memoire pour la generation, le stockage Nextcloud-first, un
telechargement explicite ou une reutilisation explicite, puis ne sont pas
persistes en DB applicative.

Un cache local de contenu exporte est hors V1 et doit faire l'objet d'un contrat
post-V1 separe.

Les lectures du store Exports V1 fail-closed par defaut. Une panne DB/store ne
doit jamais etre transformee en liste vide ou en export absent. Les erreurs
applicatives exposees restent content-free et utilisent
`folder_export_lookup_failed`; les causes brutes sont masquees.

## 7. Cible Nextcloud et stockage

La cible normative est:

```text
/Frida/<dossier>/Exports/<nom_sanitise>.<format>
```

Invariants:

- seul un `workspace_folder` `linked` est eligible;
- les etats `local_only`, `sync_pending`, `sync_error`, `conflict` et `deleted`
  bloquent les ecritures Exports;
- `Exports` doit exister et etre une collection WebDAV valide;
- `PROPFIND 207` seul ne suffit pas: la reponse doit confirmer `collection` en
  memoire uniquement;
- aucune DB Nextcloud directe;
- pas de listing large de contenu Nextcloud comme preuve;
- pas d'overwrite;
- pas de suppression automatique d'exports existants.

Ecriture V1:

- generation locale bornee en memoire;
- verification du sous-dossier `Exports`;
- PUT anti-ecrasement avec creation sure;
- persistance locale apres succes distant;
- si la persistance locale echoue apres creation distante, compensation stricte
  de la cible creee par ce flux;
- si la compensation est impossible ou echoue, etat content-free explicite, pas
  de succes silencieux.

## 8. API et surfaces UI autorisees

Les surfaces HTTP Exports V1 restent sous le namespace dossier:

```text
/api/workspace-folders/<folder_id>/exports*
```

Interdits V1:

- route globale `/api/exports*`;
- route qui contourne `workspace_folders`;
- reutilisation de `/api/workspace-folders/<folder_id>/files`;
- reutilisation de routes Notes;
- reutilisation de routes admin logs.

Surfaces autorisees par la spec:

- API dossier pour creer/generer un export;
- API dossier pour lister/retrouver un export;
- API dossier pour telecharger/ouvrir un export existant;
- API dossier pour utiliser explicitement un export existant comme source d'un
  nouvel export;
- UI chat/dossier minimale qui envoie une source explicite et un dossier cible.

Le bouton navigateur actuel d'export Markdown conversationnel reste une capacite
locale et humaine. Exports V1 ne le remplace pas, ne le detourne pas et ne le
change pas sans decision explicite ulterieure.

## 9. Nommage, collision et versioning

Nom cible:

- un titre utilisateur explicite est autorise et preferentiellement utilise;
- a defaut, Frida peut proposer un nom derive du type de source et d'un
  timestamp UTC;
- le nom est sanitise avant usage distant;
- l'extension est determinee par le format demande.

Collision:

- aucune collision ne declenche d'overwrite;
- aucune collision ne declenche un renommage automatique silencieux;
- si la cible existe, l'operation retourne un conflit content-free;
- l'utilisateur peut relancer explicitement avec un nouveau titre;
- le versioning automatique est hors V1, sauf si un lot futur le documente par
  micro-contrat avant runtime.

Les noms/titres peuvent etre visibles dans l'UI utilisateur. Les surfaces
techniques utilisent refs/hashes et jamais un nom sensible brut.

## 10. Sens exact de "reutiliser un export"

En V1, reutiliser un export signifie uniquement:

- retrouver/lister un export existant;
- telecharger ou ouvrir explicitement cet export;
- utiliser explicitement cet export comme source d'un nouvel export.

Reutiliser ne signifie pas:

- injection automatique du contenu exporte dans le chat;
- lecture implicite du contenu;
- alimentation Memory/RAG/Identity/Summary;
- conversion implicite vers un autre format;
- duplication sans action utilisateur explicite.

Toute reutilisation qui lit le contenu exporte doit etre une action utilisateur
explicite, bornee, complete ou refusee, et content-free en observabilite.

## 11. Garde-fous content-free

Projection utilisateur autorisee:

- titre ou nom d'export;
- format;
- statut lisible;
- date de creation/modification si disponible;
- taille ou compteur sobre;
- action disponible: ouvrir/telecharger/reutiliser.

Projection technique autorisee:

- `export_ref`;
- `folder_ref`;
- `title_hash`;
- `format`;
- `source_kind`;
- `source_ref`;
- `source_hash`;
- `content_hash`;
- `etag_present` ou `etag_hash`;
- status;
- reason code;
- compteurs.

Interdits en projection technique, logs, JSONL, observabilite et preuves:

- contenu exporte brut;
- nom sensible brut;
- ETag brut;
- cible distante brute;
- chemin DAV;
- URL DAV;
- XML;
- payload WebDAV;
- secret, token, cookie, app-password, Authorization;
- base64 ou data URL de document genere.

## 12. Reason codes initiaux

Catalogue initial content-free:

- `folder_export_folder_not_linked`;
- `folder_export_folder_deleted`;
- `folder_export_exports_target_missing`;
- `folder_export_exports_target_not_collection`;
- `folder_export_exports_target_unavailable`;
- `folder_export_name_invalid`;
- `folder_export_name_conflict`;
- `folder_export_source_missing`;
- `folder_export_source_ambiguous`;
- `folder_export_source_unsupported`;
- `folder_export_source_unavailable`;
- `folder_export_source_not_prepared`;
- `folder_export_source_read_unavailable`;
- `folder_export_source_read_too_large`;
- `folder_export_format_unsupported`;
- `folder_export_dependency_unavailable`;
- `folder_export_too_large`;
- `folder_export_generation_failed_redacted`;
- `folder_export_create_ok`;
- `folder_export_store_ok`;
- `folder_export_list_ok`;
- `folder_export_lookup_ok`;
- `folder_export_lookup_failed`;
- `folder_export_download_ok`;
- `folder_export_reuse_ok`;
- `folder_export_local_persistence_failed`;
- `folder_export_remote_compensation_ok`;
- `folder_export_remote_compensation_failed`;
- `folder_export_nextcloud_error_redacted`.

Reason codes interdits:

- reason code contenant un titre brut;
- reason code contenant une cible distante;
- reason code contenant une URL, un chemin, un ETag brut, du XML, un secret ou
  du contenu exporte.

## 13. Frontieres avec les chantiers voisins

### 13.1 Nextcloud folders

Exports V1 reutilise le socle `workspace_folder linked` et le sous-dossier
standard `Exports`. Il ne rouvre pas creation, renommage, suppression ou
reconciliation des dossiers.

### 13.2 Documents

Documents V1 reste la source des documents persistants sous `Documents`.
Exports V1 peut exporter un document seulement si Documents V1 l'a deja prepare
ou lu proprement et si l'utilisateur le choisit explicitement comme source.
Exports V1 ne relance pas ingestion, fallback PDF, OCR ou rangement Documents.
Exports V1 ne doit pas inventer une lane de lecture parallele a Documents.

### 13.3 Notes

Notes V1 reste la source des notes Markdown vivantes sous `Notes`. Exports V1
peut exporter une note existante explicitement choisie, mais ne modifie pas la
note et ne reutilise pas le read-model Notes comme read-model exports.
Exports V1 ne doit pas inventer une lane de lecture parallele a Notes.

### 13.4 Export navigateur

Le bouton actuel d'export Markdown navigateur reste local, humain et sans
metadonnees techniques. Il ne prouve pas Exports V1 et ne doit pas etre remplace
sans decision explicite ulterieure.

### 13.5 Export admin logs

L'export admin logs reste une surface operateur. Exports V1 ne reutilise pas son
contenu, son read-model, ses IDs, ses payloads compactes ou son format
technique. Seuls des patterns mecaniques limites peuvent etre repris: reponse
HTTP, attachement Markdown ou forme de tests.

### 13.6 Images, Biblio, Agenda, Mail, Memory

Exports V1 ne livre pas Images, Biblio/Catalogue, Agenda, Mail,
Memory/RAG/Identity/Summary. Un export ne doit jamais nourrir ces surfaces par
confusion.

## 14. Criteres Lot Z

Lot Z Exports V1 ne peut etre coche que si des preuves content-free demontrent:

- generation Markdown, TXT, DOCX et PDF selon les limites V1;
- refus clair si DOCX/PDF est indisponible ou hors limite;
- stockage Nextcloud-first sous `/Frida/<dossier>/Exports`;
- no overwrite en cas de collision;
- read-model local aligne avec la cible distante;
- liste/retrouver/ouvrir/telecharger;
- reutilisation explicite comme source d'un nouvel export;
- refus dossier non `linked`;
- refus source ambigue;
- refus taille sans troncature silencieuse;
- cleanup distant/local des exports synthetiques de smoke;
- scans anti-fuite sur JSONL, logs, docs et diff.

Les preuves Lot Z doivent rester synthetiques et content-free. Aucun contenu
utilisateur reel ne doit etre lu, exporte, liste ou supprime pour cloturer V1.

## 15. No-go pour Lot 2+

Les lots runtime Exports V1 ne doivent jamais inventer en avancant:

- nouvelle source exportable;
- nouveau sens de reutiliser;
- route globale;
- stockage local de contenu exporte;
- injection chat implicite;
- conversion implicite;
- lecture d'une source parce qu'elle est seulement listee ou retrouvee;
- lane de lecture parallele pour Notes ou Documents;
- relance ingestion, OCR ou fallback visuel Documents;
- versioning automatique;
- dependance DOCX/PDF non documentee;
- reuse de `workspace_files` ou `workspace_folder_notes` comme read-model
  exports;
- modele admin logs comme modele produit;
- preuve technique contenant contenu exporte, nom sensible, ETag brut, DAV/XML,
  payload brut ou secret.

Si l'acquisition complete d'une source n'est pas disponible proprement, l'export
est refuse avec reason code content-free. Si un besoin reel depasse ce contrat,
le lot s'arrete avant tout patch qui figerait ou inventerait une decision, y
compris docs/spec, avant commit et avant de cocher un lot.
