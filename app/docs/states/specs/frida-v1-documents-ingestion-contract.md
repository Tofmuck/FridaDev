# Frida V1 - Documents ingestion contract

Statut: spec vivante Lot 2
Date: 2026-06-17
Roadmap active: `app/docs/todo-todo/product/frida-v1-documents-ingestion-todo.md`
Audit Lot 0: `app/docs/states/audits/frida-v1-documents-ingestion-lot0-audit-2026-06-17.md`
Socle dossiers source: `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
Contrat documents actifs source: `app/docs/states/specs/active-conversation-documents-contract.md`

## 1. Verdict de plan

Existe-t-il un meilleur plan ?

Non. Le bon plan est de graver ce contrat source-of-truth avant tout runtime
Documents V1. Les prochains lots doivent appliquer ce contrat. Si un lot futur
rencontre une contradiction produit, il doit s'arreter avant patch et ouvrir un
micro-lot de recalage documentaire.

Le Lot 1 a livre ce contrat en docs-only. Le Lot 2 livre maintenant un
read-model local derive autour de `workspace_files`, sans migration DB, sans
acces Nextcloud live, sans OCR reel et sans rangement de fichier.

## 2. Modele produit Documents V1

Un document Documents V1 est un fichier persistant rattache a un dossier Frida
produit.

Regle centrale:

```text
workspace_folder linked -> document de dossier -> /Frida/<dossier>/Documents
```

Le dossier Frida visible dans l'interface reste le `workspace_folder`. Le
document de dossier ne cree pas une deuxieme notion de dossier, ne contourne pas
`workspace_folders` et ne depend pas de la DB Nextcloud.

Le modele local Documents V1 s'appuie sur les surfaces `workspace_files` comme
registre/read-model applicatif des documents persistants de dossier. Les lots
runtime peuvent ajouter des champs ou une liaison technique strictement rattachee
a `workspace_files` et `workspace_folders`, mais ils ne doivent pas transformer
`active_document` en stockage durable ni creer une Biblio parallele.

## 3. Frontiere Nextcloud folders

La cible normative d'un document de dossier est:

```text
/Frida/<dossier>/Documents
```

Invariants obligatoires:

- seul un dossier Frida `linked` peut recevoir une ecriture Documents;
- un dossier `local_only`, `sync_pending`, `sync_error`, `conflict` ou
  `deleted` bloque toute ecriture Nextcloud Documents;
- le sous-dossier standard `Documents` doit exister et etre une collection
  WebDAV valide;
- une cible absente, non-collection, inaccessible ou ambigue produit une erreur
  content-free;
- aucun lot Documents V1 n'accede directement a la DB Nextcloud;
- aucun lot Documents V1 ne liste le contenu Nextcloud comme preuve generale.

## 4. Frontiere workspace files

`workspace_files` est la surface locale a adapter pour les documents persistants
de dossier.

Les fichiers workspace actifs deja rattaches aux dossiers Frida existants doivent
etre traites dans Documents V1 par copie/rangement controle non destructif vers:

```text
/Frida/<dossier>/Documents
```

Cette copie/rangement est obligatoire si l'inventaire prouve au moins un fichier
actif a traiter. Si l'inventaire prouve `0` fichier actif, le lot peut se fermer
par preuve content-free `0 a traiter`.

Regles obligatoires:

- pas de migration automatique;
- pas de migration silencieuse;
- pas de suppression source silencieuse;
- pas d'ecrasement d'une cible Nextcloud existante;
- conservation de la source locale tant qu'une preuve de rangement Nextcloud et
  un rollback documente ne sont pas disponibles;
- aucune lecture de contenu utilisateur dans les preuves d'infrastructure.

Dans ce contrat, le mot migration signifie uniquement copie/rangement controle
non destructif. Il ne signifie jamais deplacement implicite, suppression source
ou ecrasement.

## 5. Frontiere active documents

`active_document` reste le stockage temporaire de documents actifs de
conversation.

Un document de dossier Documents V1 n'est pas un `active_document` par nature.
Il peut etre selectionne ou prepare pour une conversation, mais cette selection
ne doit pas:

- le stocker dans l'etat durable `active_document`;
- le promouvoir en Memory/RAG;
- l'ajouter a Identity;
- l'ajouter aux summaries;
- le transformer en document Biblio;
- le reutiliser hors du dossier et de l'usage explicitement demandes.

Le chemin `active_document` existant reste utile comme source d'inspiration pour
les extracteurs, limites et messages, mais il ne porte pas le stockage
persistant Documents V1.

## 6. Frontiere Biblio, Notes, Exports, Images

Documents V1 reste sobre: Frida doit lister, deposer, selectionner/preparer et
utiliser un document de dossier dans la conversation. Il ne construit pas une
bibliotheque savante parallele a Biblio.

Hors-scope Documents V1:

- `library_document`;
- `catalogue_document`;
- `passage documentaire`;
- Notes Markdown sous `Notes`;
- exports Markdown/TXT/DOCX/PDF sous `Exports`;
- images generees sous `Images`;
- Agenda;
- Mail;
- Memory/RAG global;
- TTS/SMS.

## 7. Surfaces utilisateur retenues

### 7.1 Depot

La surface primaire de depot Documents V1 est la surface fichier/document d'un
dossier Frida `linked`. Un depot depuis le chat est autorise seulement comme
action explicite de rangement dans le dossier Frida courant `linked`.

Un upload direct dans le chat sans action de rangement explicite reste un
`active_document` temporaire.

### 7.2 Liste

La liste utilisateur des documents appartient au dossier Frida courant. Elle peut
afficher les noms de fichiers, types, tailles, dates et statuts utiles au travail
documentaire.

Les preuves JSONL, logs techniques, dashboard technique et observabilite
content-free ne doivent pas reprendre les noms de fichiers bruts.

### 7.3 Selection et usage conversationnel

Un document de dossier est utilise dans une conversation seulement apres une
selection ou une demande explicite de l'utilisateur.

Regles:

- pas d'injection automatique de tous les documents d'un dossier;
- pas de troncature silencieuse presentee comme lecture complete;
- si le document ne peut pas etre prepare entierement selon les limites runtime,
  Frida doit refuser l'usage avec un message simple;
- un document utilise en conversation reste hors Memory/RAG/Identity/Summary.

## 8. Etats produit

Etats minimaux Documents V1:

- `available`: document connu et disponible dans un dossier `linked`;
- `preparing`: preparation de lecture en cours;
- `readable`: texte exploitable prepare selon le contrat;
- `not_injected`: document connu mais absent du tour courant;
- `pdf_text`: PDF textuel exploitable par extraction texte bornee;
- `pdf_visual_required`: PDF sans texte exploitable, a traiter comme visuel;
- `visual_ready`: fallback visuel pret pour le tour courant;
- `too_large`: document au-dela des limites runtime;
- `unsupported`: type non supporte;
- `error`: erreur content-free;
- `deleted`: document supprime ou tombstone cote Frida;
- `unavailable`: cible ou document indisponible.

## 9. Strategie PDF texte

Formats textuels Documents V1 a reutiliser depuis l'extracteur existant:

- TXT;
- Markdown / MD;
- DOCX;
- ODT;
- PDF textuel.

Si un lot runtime constate une incompatibilite reelle entre cet extracteur et le
read-model Documents V1, il doit s'arreter en no-go avant patch ou ouvrir un
micro-lot de recalage docs/spec. Il ne doit pas se clore par une simple note de
manque.

Un PDF avec texte exploitable suit la voie extraction texte bornee.

Regles:

- extraction texte uniquement si le PDF contient du texte exploitable;
- aucune OCR sur un PDF deja textuel;
- aucune extraction partielle presentee comme complete;
- si le texte extrait ne rentre pas dans l'usage conversationnel autorise, le
  document reste non injecte avec reason code content-free;
- le contenu extrait ne doit jamais etre logge brut.

## 10. Strategie PDF image / fallback visuel

Un PDF sans texte exploitable doit etre traite comme image/visuel.

Decision Documents V1:

- chemin PDF texte: extraction texte bornee;
- chemin PDF sans texte: fallback visuel/PDF image;
- meme fallback visuel pour un PDF ajoute directement dans le chat et pour un
  PDF present dans `/Frida/<dossier>/Documents`;
- memes limites, memes messages utilisateur, memes reason codes et memes preuves
  content-free sur les deux chemins;
- l'OCR borne existant des `active_document` reste une capacite archivee du
  chantier documents actifs, mais Documents V1 ne doit pas presenter un PDF
  image comme lu textuellement sans preuve explicite de texte exploitable.

Limites V1 du fallback visuel:

- `25 pages`;
- `25 Mo`;
- `180` secondes pour toute preparation externe bornee si elle est utilisee;
- refus simple au-dela des limites.

## 11. Noms visibles et content-free

Les noms de fichiers peuvent etre visibles:

- dans l'interface utilisateur;
- dans les reponses utilisateur quand c'est utile au travail documentaire.

Projection utilisateur:

- `display_name` / nom de fichier lisible autorise;
- type, taille, date, statut et readiness autorises;
- objectif: rendre la liste documentaire utilisable par l'utilisateur.

Projection technique, logs, JSONL et observabilite:

- nom de fichier brut interdit;
- refs redacted, hashes courts, compteurs et statuts seulement;
- aucun reason code ne contient de nom de fichier.

Les noms de fichiers ne doivent pas apparaitre:

- dans les logs techniques;
- dans les JSONL de preuve;
- dans l'observabilite content-free;
- dans les reason codes;
- dans les dashboards techniques.

Les surfaces content-free utilisent des ids applicatifs, refs redacted, hashes
courts, compteurs, types agreges, statuts et reason codes.

Interdits partout hors surface utilisateur explicite:

- contenu document brut;
- texte OCR brut;
- image/base64/PDF brut;
- chemin disque;
- chemin DAV brut;
- URL DAV;
- XML brut;
- `storage_key`;
- secret, token, cookie, `app-password`, `Authorization`;
- payload provider brut.

## 12. Read-model local livre au Lot 2

Le read-model local Documents V1 est livre par
`app/core/workspace_folder_documents.py`.

Decision technique Lot 2:

- `workspace_files` reste le registre/read-model local des documents
  persistants de dossier;
- aucune table Documents V1 separee n'est creee dans ce lot;
- aucune migration DB n'est appliquee;
- aucune operation Nextcloud/WebDAV n'est appelee;
- les routes workspace files et selections existantes sont enrichies, sans
  route parallele Documents V1.

Projections runtime:

- `document_v1_user`: projection utilisateur; `display_name` autorise avec type,
  taille, dates, statut, readiness et reason code;
- `document_v1_technical`: projection content-free; refs redacted, hash court du
  nom, ids applicatifs, media type, taille, statuts et reason codes, sans nom de
  fichier brut, `storage_key`, chemin disque, URL DAV, XML, secret ni contenu;
  cette projection est allowlistee par valeurs, pas seulement par noms de cles:
  `content_kind`, `media_kind`, `mime_type`, `source_extension`,
  `document_status`, `readiness` et `reason_code` doivent etre normalises
  strictement, et toute valeur inconnue ou suspecte devient `unknown`, vide ou
  redacted selon le champ;
- `document_v1_usage`: projection de selection conversationnelle; lien explicite
  conversation -> document de dossier -> usage, sans stockage durable
  `active_document`, sans Biblio et sans Memory/RAG/Identity/Summary.

Statuts projetes au Lot 2:

- `available`;
- `preparing`;
- `readable`;
- `not_injected`;
- `pdf_text`;
- `pdf_visual_required`;
- `visual_ready`;
- `too_large`;
- `unsupported`;
- `error`;
- `deleted`;
- `unavailable`.

Regles de projection:

- un dossier non `linked` rend le document `unavailable` avec
  `folder_document_folder_not_linked`;
- un PDF avec texte extrait devient `pdf_text`;
- un PDF sans texte exploitable marque `ocr_required` devient
  `pdf_visual_required`;
- une image devient `visual_ready`;
- un document texte prepare devient `readable`;
- un fichier en `parse_error` devient `error` avec
  `folder_document_parse_error`, pour ne pas confondre fichier illisible ou
  corrompu avec type non supporte;
- un reason code mal forme ou inconnu sur une projection technique/usage est
  redacted.

Limites restantes avant Lot 3:

- les nouveaux documents ne sont pas encore ranges dans Nextcloud;
- les fichiers workspace existants ne sont pas encore copies/ranges sous
  `Documents`;
- aucune verification live du sous-dossier `Documents` n'est faite par ce
  read-model;
- la preparation de lecture et le fallback visuel complet restent des lots
  separes.

## 13. Reason codes Documents V1

Catalogue initial obligatoire:

- `folder_document_folder_not_linked`;
- `folder_document_documents_target_missing`;
- `folder_document_documents_target_conflict`;
- `folder_document_documents_target_unavailable`;
- `folder_document_documents_target_not_collection`;
- `folder_document_name_invalid`;
- `folder_document_name_conflict`;
- `folder_document_type_unsupported`;
- `folder_document_upload_ok`;
- `folder_document_list_ok`;
- `folder_document_selected`;
- `folder_document_prepare_ok`;
- `folder_document_text_ready`;
- `folder_document_pdf_text_ready`;
- `folder_document_pdf_visual_required`;
- `folder_document_pdf_visual_ready`;
- `folder_document_too_large`;
- `folder_document_too_many_pages`;
- `folder_document_parse_error`;
- `folder_document_runtime_unavailable`;
- `folder_document_nextcloud_error_redacted`;
- `folder_document_content_redacted`;
- `folder_document_existing_copy_required`;
- `folder_document_existing_copy_ok`;
- `folder_document_existing_copy_conflict`;
- `folder_document_existing_source_preserved`;
- `folder_document_observation_redacted`.

Un reason code inconnu doit etre redacted avant exposition technique.

## 14. Messages utilisateur

Les messages utilisateur doivent etre simples et honnetes:

- document disponible;
- preparation en cours;
- document trop lourd;
- type non supporte;
- PDF sans texte lisible, traitement visuel utilise;
- PDF visuel indisponible ou hors limites;
- dossier non synchronise;
- cible Documents indisponible;
- conflit de nom;
- erreur technique redacted.

Frida ne doit jamais pretendre avoir lu integralement un document non prepare,
trop gros, partiel, visuel sans lecture textuelle, indisponible ou en erreur.

## 15. Preuves et observabilite

Les preuves Documents V1 doivent rester content-free:

- compteurs de dossiers et documents;
- statuts;
- media types agreges;
- classes d'erreur;
- ids applicatifs ou hashes courts;
- reason codes allowlistes;
- verdicts de smokes.

Les smokes live utilisent des documents synthetiques. Les preuves
d'infrastructure ne lisent pas et ne listent pas de contenu utilisateur.

## 16. Criteres de cloture Lot Z

Documents V1 est clos seulement si toutes les preuves suivantes sont livrees:

- un dossier Frida `linked` recoit un document synthetique sous `Documents`;
- un dossier non `linked` bloque proprement toute ecriture Documents;
- la liste utilisateur affiche les documents disponibles selon le contrat;
- les preuves techniques restent redacted et content-free;
- un document texte peut etre prepare et utilise dans une conversation;
- un PDF textuel suit l'extraction texte bornee;
- un PDF sans texte suit le meme fallback visuel depuis le dossier Nextcloud et
  depuis l'ajout direct dans le chat;
- les limites et messages utilisateur sont coherents sur les deux chemins PDF;
- les fichiers workspace existants sont copies/ranges de facon controlee si
  l'inventaire en trouve, ou prouves `0 a traiter`;
- aucune source locale n'est supprimee silencieusement;
- aucune confusion Biblio, Notes, Exports, Images, Agenda ou Mail n'est livree;
- aucun contenu, nom de fichier en preuve technique, chemin DAV, URL DAV, XML
  brut, `storage_key`, secret ou payload brut ne fuit.

## 17. Hors-scope strict

- Pas de runtime Nextcloud dans les Lots 1-2.
- Pas de migration DB dans les Lots 1-2.
- Pas d'acces Nextcloud live dans les Lots 1-2.
- Pas de WebDAV live dans les Lots 1-2.
- Pas de Sauron dans les Lots 1-2.
- Pas de secret.
- Pas de fichier utilisateur lu, copie, deplace, range ou supprime dans les
  Lots 1-2.
- Pas d'OCR reel dans les Lots 1-2.
- Pas de test multimodal live dans les Lots 1-2.
- Pas de Docker/rebuild plateforme/global dans les Lots 1-2; le Lot 2 peut
  necessiter un rebuild applicatif FridaDev cible parce qu'il livre du runtime
  local.
- Pas de Biblio, Notes, Exports, Images, Agenda, Mail, Memory/RAG global ou
  TTS/SMS.
