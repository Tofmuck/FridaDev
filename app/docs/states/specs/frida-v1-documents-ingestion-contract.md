# Frida V1 - Documents ingestion contract

Statut: spec vivante Documents V1 cloture par Lot Z
Date: 2026-06-17
Roadmap archivee: `app/docs/todo-done/product/frida-v1-documents-ingestion-todo.md`
Audit Lot 0: `app/docs/states/audits/frida-v1-documents-ingestion-lot0-audit-2026-06-17.md`
Socle dossiers source: `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
Contrat documents actifs source: `app/docs/states/specs/active-conversation-documents-contract.md`

## 1. Verdict de plan

Existe-t-il un meilleur plan ?

Non. Le bon plan est de graver ce contrat source-of-truth avant tout runtime
Documents V1. Les prochains lots doivent appliquer ce contrat. Si un lot futur
rencontre une contradiction produit, il doit s'arreter avant patch et ouvrir un
micro-lot de recalage documentaire.

Le Lot 1 a livre ce contrat en docs-only. Le Lot 2 a livre le read-model local
derive autour de `workspace_files`, sans migration DB. Le Lot 3 a livre
l'ingestion/rangement Nextcloud-first des nouveaux documents via la route
workspace files existante, avec transport WebDAV borne, preuve synthetique et
compensation stricte. Le Lot 4 a livre la liste utilisateur. Le Lot 5 a livre la
preparation texte/PDF textuel bornee. Le Lot 6 a livre le fallback visuel unifie
pour images et PDF sans texte. Le Lot 7 a traite les fichiers workspace
existants par copie/rangement controle non destructif. Le Lot 8 a consolide
l'observabilite et les smokes. Le Lot Z cloture Documents V1 avec verdict
`met_with_documented_limit`.

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
- depuis le correctif Lot 6, le chemin par defaut d'un PDF direct sans texte est
  un `active_document` `media_kind=file` injectable comme PDF visuel multimodal
  ponctuel; le chemin OCR durable reste une capacite explicite distincte;
- l'OCR borne existant des `active_document` reste une capacite archivee du
  chantier documents actifs, mais Documents V1 ne doit pas presenter un PDF
  image comme lu textuellement sans preuve explicite de texte exploitable.

Limites V1 du fallback visuel:

- `25 pages`;
- `25 Mo`;
- `180` secondes pour toute preparation externe bornee si elle est utilisee;
- refus simple au-dela des limites;
- la limite `25 pages` est verifiee avant construction de `file_data`, data URL
  ou base64 provider.

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
`app/core/workspace_folder_documents.py`. La projection d'usage conversationnel
`document_v1_usage` est isolee dans
`app/core/workspace_folder_document_usage.py` depuis le micro-correctif
d'hygiene post-Lot 5.

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
  redacted selon le champ; les ids techniques `workspace_file_id` et
  `workspace_folder_id` ne sont exposes que s'ils sont des UUID valides, sinon
  ils sont vides et les refs utilisent un hash court redacted;
- `document_v1_usage`: projection de selection conversationnelle; lien explicite
  conversation -> document de dossier -> usage, sans stockage durable
  `active_document`, sans Biblio et sans Memory/RAG/Identity/Summary; depuis
  Lot 5, cette projection peut indiquer `selected`, `readable`,
  `pdf_visual_required`, `too_large`, `unsupported`, `unavailable` ou
  `not_injected` selon le resultat de preparation du tour.

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

- les fichiers workspace existants ne sont pas encore copies/ranges sous
  `Documents`;
- la preparation de lecture et le fallback visuel complet restent des lots
  separes.

## 12.1 Ingestion/rangement des nouveaux documents livre au Lot 3

Le runtime Lot 3 branche la route existante
`/api/workspace-folders/<id>/files` sur une orchestration Documents V1
Nextcloud-first.

Decision technique Lot 3:

- aucun modele produit parallele n'est cree;
- `workspace_files` reste le registre local du document persistant;
- `workspace_file_nextcloud_links` persiste uniquement le lien technique interne
  `workspace_file` -> cible Nextcloud pour retrouver la cible distante exacte
  sans re-sanitisation; cette table ne cree pas une deuxieme notion produit de
  document;
- le transport WebDAV fichier est isole dans
  `app/core/workspace_document_nextcloud_client.py`;
- l'orchestration validation -> Nextcloud -> persistence locale ->
  compensation est isolee dans
  `app/core/workspace_document_nextcloud_runtime.py`;
- `app/server.py` ne porte aucune logique Nextcloud, seulement le wiring du
  module runtime.

Regles runtime:

- un dossier non `linked` bloque le depot avant lecture du contenu;
- `app/server.py` borne le corps multipart a `40 MiB` (`41943040` octets)
  avec `MAX_CONTENT_LENGTH` Flask avant materialisation non bornee, y compris
  pour un flux WSGI termine sans `Content-Length` exploitable;
- le service workspace applique ensuite un plafond defensif propre au lecteur
  fichier: il lit par blocs jusqu'a `40 MiB + 1 octet` au plus, accepte `40
  MiB` exacts lorsqu'il est teste seul et refuse `limite + 1` avant
  extraction, validation, ecriture disque, persistence locale ou appel
  Nextcloud;
- ce bord lecteur n'est pas atteignable par un fichier de `40 MiB` dans une
  requete reelle: l'enveloppe multipart compte dans le plafond du corps `40
  MiB`, donc la taille fichier effectivement admissible est strictement
  inferieure et depend de l'enveloppe;
- le prefixe observe lors d'un refus n'est jamais transmis comme document;
- le sous-dossier standard `Documents` est verifie en `PROPFIND` Depth 0 et doit
  etre une collection WebDAV;
- une cible `Documents` absente, non-collection, conflictuelle ou indisponible
  refuse le depot avec reason code content-free;
- le nom cible du document est sanitise localement et limite avant ecriture;
- extension absente, nom vide ou nom invalide refusent le depot;
- conflit local de nom sanitise refuse le depot avant tout appel Nextcloud;
- l'ecriture Nextcloud utilise `PUT` avec anti-ecrasement; seul un statut de
  creation sure est accepte, et tout statut update-like est traite comme conflit
  ou erreur redacted content-free;
- conflit Nextcloud ou tentative d'overwrite refuse le depot;
- la persistence locale `workspace_files` n'a lieu qu'apres succes Nextcloud;
- la persistence du lien Nextcloud a lieu juste apres la persistence locale du
  `workspace_file`;
- si l'ecriture Nextcloud reussit mais que la persistence locale ou la
  persistence du lien echoue, le runtime tente une compensation `DELETE`
  strictement bornee au fichier cree dans ce flux et nettoie l'artefact local
  cree dans le meme flux si necessaire;
- la compensation ne touche jamais un fichier historique ou utilisateur
  preexistant;
- la suppression explicite d'un document Documents V1 lie utilise le lien
  persiste pour supprimer la cible Nextcloud exacte avant le tombstone local;
- si la lecture du lien Nextcloud echoue ou devient ambigue, la suppression
  fail-closed: aucune suppression distante n'est tentee et aucun tombstone local
  n'est produit;
- si la suppression distante echoue, le fichier local actif n'est pas tombstone;
- un fichier historique/local-only sans lien Nextcloud conserve le comportement
  local existant;
- si la suppression distante et le tombstone local reussissent mais que le
  marquage local du lien `deleted` echoue, l'API remonte un etat partiel
  content-free (`link_mark_state=failed`) au lieu de pretendre a un cleanup
  parfaitement propre;
- la projection utilisateur peut exposer le `display_name`;
- le payload technique et les preuves n'exposent que hash/ref court, statuts,
  classes HTTP et reason codes; le nom distant brut reste interne a la
  persistance applicative et n'est jamais expose dans les logs, JSONL,
  observabilite technique ou payloads techniques.

Le plafond du corps HTTP `40 MiB`, le plafond defensif du lecteur fichier `40
MiB`, le fallback visuel `25 MiB` / `25 pages`, les limites OCR et la fenetre
de contexte restent distincts. Une selection conversationnelle continue
d'injecter le document entier ou de l'exclure entierement; l'exclusion
maintient le tour et permet a Frida de dire honnetement qu'elle ne dispose pas
du document.

Preuve Lot 3:

- tests unitaires: `app/tests/unit/core/test_workspace_documents_ingestion.py`;
- smoke live synthetique content-free:
  `app/docs/states/baselines/documents-smokes/frida-v1-documents-lot3-live-ingestion-20260617T142304Z.jsonl`;
- smoke correctif Lot 3.1 content-free:
  `app/docs/states/baselines/documents-smokes/frida-v1-documents-lot3-1-link-delete-20260617T145211Z.jsonl`;
- cleanup strict du fichier et du dossier synthetiques crees pendant le smoke.

## 12.2 Liste utilisateur des documents livree au Lot 4

Le Lot 4 livre la liste Documents utilisateur par dossier via la route existante
`/api/workspace-folders/<id>/files`.

Regles runtime:

- aucune route Documents parallele n'est creee;
- la liste est derivee du registre local `workspace_files`;
- les fichiers `deleted` / tombstones sont exclus par le store existant;
- chaque item actif est enrichi par l'etat local `workspace_file_nextcloud_links`
  si un lien existe;
- un document avec lien `linked` est expose comme range Nextcloud dans
  `document_v1_user`;
- un document sans lien est expose honnetement comme `local_only`;
- un echec de lecture du lien local est expose comme `sync_error` avec
  `folder_document_link_lookup_failed`;
- aucun appel WebDAV/Nextcloud live n'est effectue pour lister;
- les cas cible `Documents` absente, non-collection ou transport sont representes
  par les etats locaux persistants disponibles, pas par un nouveau probe live.

Surfaces:

- `document_v1_user` peut exposer `display_name`, type, taille, dates, statut,
  readiness et label utilisateur d'etat Nextcloud;
- `document_v1_technical` n'expose que refs/hashs courts, statuts et reason
  codes content-free;
- `nextcloud_target_name`, nom distant brut, `storage_key`, chemin disque, URL
  DAV, XML, secret, contenu et nom de fichier utilisateur restent absents des
  projections techniques, logs, JSONL et observabilite.

Limites restantes apres Lot 6, avant Lot 7:

- les fichiers workspace historiques restent Lot 7;
- aucun Notes / Exports / Images runtime n'est livre par Lot 6.

## 12.3 Preparation de lecture bornee livree au Lot 5

Le Lot 5 livre la preparation de lecture des documents deja presents dans un
dossier Frida sans ajouter de transport Nextcloud ni de fallback visuel complet.

Regles runtime:

- seule une selection explicite via les surfaces existantes
  `workspace_file_selections` rend un document utilisable dans une conversation;
- un document texte, Markdown/MD, DOCX, ODT ou PDF textuel reutilise
  l'extracteur texte existant;
- si le document est lisible et respecte le budget, il est injecte en entier
  dans la lane documentaire du tour;
- si le document est trop volumineux, absent, supprime, non supporte ou en
  erreur, il est refuse proprement avec un reason code content-free;
- aucune troncature silencieuse n'est autorisee;
- au Lot 5, un PDF sans texte exploitable ou une image de dossier restait hors
  payload multimodal; le Lot 6 active le fallback visuel unifie;
- les decisions `workspace_file_selection` dans l'observabilite technique ne
  contiennent pas de nom de fichier brut; elles utilisent refs/hashs courts,
  statuts, media type allowliste et reason codes;
- le contenu extrait peut etre envoye au modele seulement dans la lane de prompt
  prevue pour le tour courant; il ne doit pas etre journalise brut et ne doit
  pas alimenter Memory/RAG/Identity/Summary.

## 12.4 Fallback visuel unifie livre au Lot 6

Le Lot 6 aligne les fichiers de dossier selectionnes et les PDF directs sans
texte avec la lane multimodale `active_document` existante sans ajouter d'OCR
durable, de WebDAV live ni de route parallele.

Regles runtime:

- un PDF textuel de dossier continue a utiliser l'extracteur texte borne; il ne
  passe pas par le fallback visuel et n'est pas OCRise par ce lot;
- un PDF de dossier en statut `ocr_required`, ou un PDF dont l'extraction texte
  retourne `document_ocr_required`, devient un document prompt `media_kind=file`
  injectable uniquement pour le tour courant;
- un PDF direct upload dont l'extraction texte retourne `document_ocr_required`
  devient par defaut un `active_document` `media_kind=file`; il peut etre injecte
  comme PDF visuel uniquement au tour courant et n'est jamais presente comme
  texte OCRise;
- une image de dossier devient un document prompt `media_kind=image` injectable
  uniquement pour le tour courant;
- les bytes image/PDF peuvent etre charges en memoire dans l'objet prompt et
  transformes en `data:image` ou `data:application/pdf` seulement dans le
  message provider;
- les logs, projections techniques, observabilite, JSONL et docs de preuve ne
  contiennent jamais image brute, PDF brut, base64, data URL, texte OCR, contenu
  extrait, `storage_key`, chemin disque, URL DAV, XML ou secret;
- le plafond provider commun est `25 MiB` avant encodage base64 et `25 pages`
  pour les PDF visuels; les tests prouvent que les refus taille/pages
  interviennent avant construction de la data URL;
- si le modele principal ne supporte pas image/fichier multimodal, si les bytes
  manquent ou si la taille est trop grande, la decision est exclue avec reason
  code content-free et Frida ne pretend pas avoir lu le document;
- le message systeme indique explicitement qu'un PDF visuel injecte est un
  fichier multimodal, pas un texte OCR garanti;
- `document_v1_usage` expose `visual_ready` apres injection visuelle reussie,
  conserve `pdf_visual_required` quand le modele ne peut pas l'utiliser, et
  garde `too_large` / `unavailable` pour les refus correspondants;
- `folder_document_pdf_visual_ready` signale la preparation visuelle reussie;
  les reason codes workspace existants signalent les refus techniques:
  `workspace_file_model_unsupported`,
  `workspace_file_pdf_visual_model_unsupported`,
  `workspace_file_pdf_visual_bytes_missing`,
  `workspace_file_pdf_visual_too_large`,
  `workspace_file_pdf_visual_page_count_failed`,
  `workspace_file_too_large`, `folder_document_too_many_pages` ou
  `workspace_file_unreadable`;
- les reason codes directs `file_too_many_pages_for_provider_payload` et
  `file_page_count_failed` signalent les refus PDF visuels actifs sans exposer
  PDF brut, base64 ou payload provider.

Limites restantes apres Lot 6:

- aucun OCR durable nouveau n'est livre;
- aucun fichier historique n'est copie/range sous `Documents`;
- aucun contenu visuel ou PDF brut n'est persiste dans une surface technique;
- Lot 7 reste necessaire pour traiter les fichiers workspace existants.

## 12.5 Fichiers workspace existants livres au Lot 7

Le Lot 7 traite les fichiers workspace actifs deja rattaches aux dossiers Frida
sans supprimer leur source locale.

Regles runtime:

- l'orchestrateur `workspace_document_existing_files.py` reste un runner borne
  operateur, pas une route utilisateur parallele;
- l'inventaire lit le registre applicatif `workspace_files` et les liens locaux
  `workspace_file_nextcloud_links`, sans acces DB Nextcloud direct;
- une panne d'inventaire dossiers ou fichiers est fail-closed:
  `folder_document_existing_inventory_failed`, `ok=false`, `verdict=failed`;
  elle ne doit jamais etre exposee comme inventaire vide ou `0 a traiter`;
- seuls les fichiers actifs local-only de dossiers Frida `linked` sont
  eligibles;
- le sous-dossier standard `Documents` est verifie comme collection WebDAV par
  status-only avant copie;
- la cible fichier exacte est verifiee par status-only avant PUT, sans
  PROPFIND Depth:1 ni listing de contenu;
- la copie utilise le PUT anti-ecrasement deja livre au Lot 3 et n'accepte
  qu'une creation sure;
- si la cible existe deja, le fichier reste no-go/conflit avec
  `folder_document_existing_copy_conflict`; Frida ne renomme pas
  automatiquement et n'ecrase jamais;
- apres creation distante, le lien technique `workspace_file_nextcloud_links`
  est persiste en `linked`, operation `reconcile`, reason code
  `folder_document_existing_copy_ok`;
- si la persistance du lien echoue apres creation distante, Frida tente un
  rollback DELETE strict sur la cible creee par ce flux uniquement;
- la source locale n'est jamais supprimee par Lot 7;
- les preuves Lot 7 restent content-free: compteurs, refs/hashs courts, status
  classes, reason codes et flags seulement.

Preuve runtime Lot 7:

- artefact:
  `app/docs/states/baselines/documents-smokes/frida-v1-documents-lot7-existing-files-20260617T203920Z.jsonl`;
- inventaire preflight: `10` fichiers actifs, `10` local-only, `0` conflit,
  `0` erreur;
- execution: `10` copies creees, `10` liens persistants, `10` sources
  preservees, `0` rollback, `0` conflit;
- inventaire final: `10` fichiers actifs `linked`, `0` local-only;
- verification distante finale status-only: `10` liens verifies, `10` reponses
  `2xx`, `0` erreur;
- aucun nom de fichier brut, contenu, chemin disque, URL DAV, XML,
  `storage_key`, secret, token, cookie ou payload WebDAV brut n'est present
  dans l'artefact.
- correctif avant pause: l'acces inventaire fail-closed est isole dans
  `workspace_document_existing_inventory.py` pour eviter d'etendre le runner
  Lot 7 deja proche de la limite haute.

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
- `folder_document_local_only`;
- `folder_document_local_persistence_failed`;
- `folder_document_link_persistence_failed`;
- `folder_document_link_lookup_failed`;
- `folder_document_link_missing`;
- `folder_document_link_mark_failed`;
- `folder_document_delete_ok`;
- `folder_document_remote_delete_failed`;
- `folder_document_local_delete_failed`;
- `folder_document_remote_compensation_ok`;
- `folder_document_remote_compensation_failed`;
- `folder_document_content_redacted`;
- `folder_document_existing_copy_required`;
- `folder_document_existing_copy_ok`;
- `folder_document_existing_copy_conflict`;
- `folder_document_existing_source_preserved`;
- `folder_document_existing_source_missing`;
- `folder_document_existing_inventory_failed`;
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

Lot 8 observabilite / smokes live livre le
`2026-06-18`:

- artefact:
  `app/docs/states/baselines/documents-smokes/frida-v1-documents-lot8-observability-smokes-20260618T063834Z.jsonl`;
- artefact correctif Lot 8 avant Lot Z:
  `app/docs/states/baselines/documents-smokes/frida-v1-documents-lot8-1-pdf-visual-proof-20260618T071616Z.jsonl`;
- cas `met`: runtime redacted, upload texte, liste utilisateur, preparation
  texte, PDF texte, fallback visuel via image synthetique de dossier, PDF sans
  texte de dossier injecte comme `media_kind=file` /
  `payload_order=text_then_file`, PDF sans texte upload direct active-document
  injecte comme `media_kind=file` / `payload_order=text_then_file`, conflit de
  nom, inventaire fichiers existants Lot 7, read-model observabilite, scan logs,
  scan artefact et cleanup distant strict;
- cas `LOT8_NON_LINKED_REFUSAL`: `partial` documente sans mutation DB forcee,
  car aucun dossier actif non `linked` n'etait disponible; le refus reste un
  invariant runtime/teste via `folder_document_folder_not_linked`; la preuve live
  complete non `linked` n'est pas vendue comme fermee et ne doit etre rejouee au
  Lot Z que si une preuve propre existe sans manipulation DB artificielle;
- cleanup correctif: fichier PDF de dossier synthetique supprime via la route
  produit avec cible distante absente en status-only, active document direct
  retire, conversations synthetiques tombstone;
- invariant observe et consolide: apres upload Documents V1 reussi, la reponse
  immediate doit exposer `nextcloud_sync_state=linked` dans les projections
  utilisateur et technique si la liaison `workspace_file_nextcloud_links` a ete
  persistee; elle ne doit jamais afficher `local_only` par fallback mensonger;
- les lignes JSONL Lot 8 restent content-free: aucun contenu, nom de fichier
  brut, chemin disque, URL DAV, XML, `storage_key`, secret, token, cookie,
  app-password ou payload WebDAV brut.

Lot Z cloture Documents V1 le `2026-06-18`:

- artefact:
  `app/docs/states/baselines/documents-smokes/frida-v1-documents-lotz-closure-20260618T073325Z.jsonl`;
- verdict final: `met_with_documented_limit`;
- cas `met`: preflight, upload texte, liste utilisateur, selection /
  preparation texte, PDF texte, PDF sans texte de dossier injecte comme
  `media_kind=file` / `payload_order=text_then_file`, PDF sans texte upload
  direct injecte comme `media_kind=file` / `payload_order=text_then_file`,
  conflit de nom, statut fichiers existants, scan observabilite, scan artefact
  et cleanup synthetique;
- cas `LOTZ_NON_LINKED_REFUSAL`: `not_applicable`, car aucun dossier actif non
  `linked` naturel n'existait; le refus reste couvert par tests
  unitaires/serveur et aucune mutation DB artificielle n'a ete faite;
- cleanup: `6` operations synthetiques, `0` echec, aucune suppression
  utilisateur reelle;
- aucune fuite de contenu, PDF brut, base64, data URL, `file_data`,
  `storage_key`, chemin disque, URL DAV, XML, secret, token, cookie,
  `app-password` ou payload WebDAV brut dans l'artefact.

## 16. Criteres de cloture Lot Z

Documents V1 est clos par Lot Z avec verdict `met_with_documented_limit`.

Preuves livrees:

- un dossier Frida `linked` recoit un document synthetique sous `Documents`;
- le refus d'un dossier non `linked` reste un invariant fail-closed couvert par
  tests unitaires/serveur; la preuve live est `not_applicable` tant qu'aucun
  dossier actif non `linked` naturel n'existe et ne doit pas etre fabrique par
  mutation DB artificielle;
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
