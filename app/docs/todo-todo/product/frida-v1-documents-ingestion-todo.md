# Frida V1 - Documents sources / ingestion / lecture / PDF fallback - TODO

Statut: Lot 2 modele local/read-model livre; prete pour Lot 3 ingestion/rangement
Date: 2026-06-17
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`
Socle dossiers source: `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
Contrat Documents V1 source: `app/docs/states/specs/frida-v1-documents-ingestion-contract.md`
Contrat documents actifs source: `app/docs/states/specs/active-conversation-documents-contract.md`

## 1. Intention produit

Frida V1 doit pouvoir travailler avec des documents sources persistants
rattaches a un dossier Frida `linked`.

Regle cible:

```text
document source d'un dossier Frida -> /Frida/<dossier>/Documents
```

Pour un dossier Frida `linked`, Frida doit pouvoir:

- deposer ou ranger des documents dans le sous-dossier standard `Documents`;
- lister les documents disponibles dans ce dossier;
- relier document, dossier, conversation et usage;
- lire ou preparer la lecture d'un document;
- traiter les PDF sans texte comme des images;
- appliquer le meme fallback visuel/image pour un PDF ajoute directement dans le
  chat et pour un PDF present dans un dossier Nextcloud;
- garder les memes limites, messages utilisateur et preuves sur les deux
  chemins PDF;
- rester content-free dans les logs, JSONL, dashboard et preuves.

Ce chantier vient apres la cloture du socle dossiers Frida V1 / Nextcloud. Il ne
rouvre pas ce socle et ne change pas le modele produit `workspace_folders`.

## 2. Alignement Nextcloud folders

Source normative:
`app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`

Regles obligatoires:

- seuls les dossiers Frida `linked` peuvent recevoir des ecritures Documents;
- un dossier `local_only`, `sync_pending`, `sync_error`, `conflict` ou `deleted`
  bloque toute ecriture Nextcloud;
- le sous-dossier standard `Documents` doit exister et etre une collection
  WebDAV valide avant depot/rangement;
- une cible `Documents` absente, non-collection, inaccessible ou ambigue doit
  produire une erreur content-free;
- les fichiers workspace existants ne sont pas copies/ranges automatiquement;
- aucun chemin DAV brut, URL DAV, XML brut, `storage_key`, payload Nextcloud,
  secret, token, cookie, `app-password`, nom sensible ou contenu fichier ne doit
  apparaitre dans les logs, JSONL, dashboard ou preuves.

Constante produit autorisee dans les docs/preuves:

```text
Documents
```

Les noms de fichiers utilisateur ne sont pas des constantes produit. Les preuves
doivent preferer compteurs, ids applicatifs, refs redacted, hash courts et
reason codes.

## 3. Frontieres produit

### 3.1 Documents persistants de dossier

Un document source de dossier est un fichier durable rattache a un
`workspace_folder` et range, a terme, sous:

```text
/Frida/<dossier>/Documents
```

Il peut etre utilise dans une conversation, mais il n'est pas limite a une seule
conversation par nature.

### 3.2 Documents actifs de conversation

Les `active_document` existent deja et restent:

- temporaires;
- conversation-scoped;
- actifs par action utilisateur;
- injectes entiers ou exclus entiers par tour;
- hors Memory/RAG/Identity/Summary;
- hors Biblio.

Le chantier Documents V1 peut reutiliser des briques d'extraction, de limites et
de fallback, mais il ne doit pas stocker les documents persistants dans l'etat
`active_document` ni transformer un document actif ponctuel en document durable
sans action explicite.

### 3.3 Biblio / Catalogue

Biblio reste un chantier distinct. Les termes suivants ne doivent pas etre
utilises pour les documents de dossier Frida:

- `library_document`;
- `catalogue_document`;
- `passage documentaire`.

Un document de dossier n'est pas automatiquement une entree Biblio, n'est pas
indexe globalement et ne cree pas de RAG documentaire par confusion.

### 3.4 Notes / Exports / Images

Ce chantier ne livre pas:

- Notes Markdown dans `Notes`;
- exports Markdown/TXT/DOCX/PDF dans `Exports`;
- stockage des images generees dans `Images`;
- mail;
- Agenda;
- Biblio.

Il doit seulement rester compatible avec ces futurs lots.

## 4. Garde-fous generaux

- Pas de runtime dans le lot de detail de cette TODO.
- Pas de Nextcloud live avant les lots explicitement prevus.
- Pas de Sauron sauf besoin plateforme explicite dans un futur lot.
- Pas de secret dans le repo, les docs, logs, JSONL, dashboard ou reponses.
- Pas de lecture de contenu utilisateur pour une preuve d'infrastructure.
- Pas de listing Nextcloud de contenu comme preuve generale.
- Pas de copie/rangement silencieux des fichiers existants.
- Pas de suppression source silencieuse apres copie.
- Pas de route ou modele parallele qui contourne `workspace_folders`.
- Pas de confusion entre document persistant de dossier et document actif de
  conversation.
- Pas de confusion entre Documents et Biblio.
- Pas de lancement anticipe Notes, Exports ou Images.

## 5. Decisions produit gravees au Lot 1

- Le chantier Documents V1 vient apres la cloture du socle dossiers Frida V1 /
  Nextcloud.
- Le dossier Frida visible dans l'UI reste le `workspace_folder`.
- Le dossier Frida frontend actif est la racine produit du rangement
  documentaire.
- La cible produit des documents sources et fichiers persistants est
  `/Frida/<dossier>/Documents`.
- Les ecritures Documents sont autorisees seulement pour un dossier Frida
  `linked`.
- Un dossier `local_only`, `sync_pending`, `sync_error`, `conflict` ou `deleted`
  bloque toute ecriture Nextcloud Documents.
- Le sous-dossier `Documents` doit etre une collection WebDAV valide.
- Les documents persistants de dossier ne sont pas des `active_document`.
- Les `active_document` restent temporaires, conversation-scoped, injectes
  entiers ou exclus entiers, hors Memory/RAG/Identity/Summary et hors Biblio.
- Les documents persistants de dossier ne sont pas des `library_document`,
  `catalogue_document` ou `passage documentaire`.
- Le modele local Documents V1 s'appuie sur `workspace_files` comme registre /
  read-model applicatif des documents persistants de dossier. Les lots runtime
  peuvent ajouter une liaison technique stricte a `workspace_files` et
  `workspace_folders`, sans creer une deuxieme notion produit de document.
- La surface primaire de depot Documents V1 est la surface fichier/document d'un
  dossier Frida `linked`.
- Un depot depuis le chat vers Documents V1 est autorise seulement comme action
  explicite de rangement dans le dossier Frida courant `linked`.
- Un upload direct dans le chat sans action de rangement explicite reste un
  `active_document` temporaire.
- La liste utilisateur des documents appartient au dossier Frida courant.
- Les noms de fichiers peuvent etre visibles dans l'interface utilisateur et
  dans les reponses utilisateur quand c'est utile au travail documentaire.
- Les noms de fichiers ne doivent pas fuiter dans les logs, JSONL,
  observabilite technique, reason codes ou preuves content-free.
- Un document de dossier est utilise dans une conversation seulement apres une
  selection ou une demande explicite de l'utilisateur.
- Frida ne doit pas injecter automatiquement tous les documents d'un dossier.
- Frida ne doit jamais presenter une extraction partielle, tronquee ou visuelle
  comme une lecture textuelle complete.
- Un PDF avec texte exploitable suit la voie extraction texte bornee.
- Un PDF sans texte exploitable suit le fallback visuel/PDF image.
- Le fallback visuel PDF/image est unifie pour un PDF ajoute directement dans le
  chat et pour un PDF present dans un dossier Nextcloud: memes limites, memes
  messages utilisateur, memes reason codes et memes preuves content-free.
- Les limites V1 du fallback visuel sont `25 pages`, `25 Mo` et `180` secondes
  pour toute preparation externe bornee si elle est utilisee.
- Le contenu des documents, le texte OCR, les images, PDF/base64 et payloads
  provider ne doivent jamais etre logges bruts.
- Documents V1 doit reutiliser l'extracteur texte existant pour TXT, Markdown /
  MD, DOCX, ODT et PDF textuel.
- Si une incompatibilite runtime reelle apparait entre cet extracteur et le
  read-model Documents V1, le lot concerne doit s'arreter en no-go avant patch
  ou ouvrir un micro-lot de recalage docs/spec.
- Les fichiers workspace actifs deja rattaches aux dossiers Frida existants
  doivent etre traites dans Documents V1.
- Pas de copie/rangement silencieux des fichiers existants.
- Pas de suppression source silencieuse.
- Pas d'ecrasement d'une cible Nextcloud existante.
- Si l'inventaire confirme des fichiers workspace actifs rattaches a un dossier
  Frida, un lot obligatoire de copie/rangement controle vers
  `/Frida/<dossier>/Documents` doit etre livre.
- Si l'inventaire prouve `0` fichier actif a traiter, le lot fichiers existants
  peut se fermer par preuve content-free `0 a traiter`; il ne peut pas se fermer
  par choix abstrait de non-traitement.
- Dans cette TODO, le mot migration est refuse comme raccourci ambigu: s'il
  apparait, il signifie uniquement copie/rangement controle non destructif,
  jamais migration automatique, silencieuse ou destructrice.
- Le contrat `active_document` existant distingue deja deux chemins pour les PDF
  sans texte:
  - OCR borne via Stirling, qui peut produire un texte exploitable;
  - injection visuelle/PDF multimodale ponctuelle, qui ne promet pas une lecture
    textuelle complete.
- Documents V1 ne doit pas brouiller ces deux statuts.

Contrat source-of-truth Lot 1:
`app/docs/states/specs/frida-v1-documents-ingestion-contract.md`

Tout lot runtime Documents V1 doit appliquer ce contrat. Si une contradiction
produit apparait, le lot doit s'arreter avant patch et ouvrir un micro-lot
docs/spec explicite.

## 6. Reason codes Documents V1 initiaux

Catalogue initial a appliquer dans les lots runtime:

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

## 7. Nature des lots

- Lot 0: audit read-only/docs-only.
- Lot 1: contrat produit docs-only; livre la spec source-of-truth.
- Lot 2: modele local / read-model; runtime local possible, sans Nextcloud live.
- Lot 3: ingestion/rangement; runtime applicatif avec ecriture Nextcloud.
- Lot 4: liste documents; runtime applicatif et read-model.
- Lot 5: lecture/preparation; runtime applicatif sans Biblio/RAG global.
- Lot 6: PDF image / fallback visuel unifie.
- Lot 7: fichiers existants; obligatoire si l'audit trouve des fichiers actifs,
  fermable par preuve `0 a traiter` sinon.
- Lot 8: observabilite / smokes live; preuves JSONL content-free.
- Lot Z: validation/cloture Documents V1; live proof sur documents synthetiques.

## 8. Lots proposes

Ne cocher que les lots reellement livres et prouves.

### Lot 0 - Audit existant

- [x] Relire les surfaces runtime des documents actifs de conversation.
- [x] Relire l'upload direct dans le chat et les routes existantes
  `active_document`.
- [x] Relire l'extraction texte existante: PDF textuel, DOCX, ODT, MD, TXT.
- [x] Relire l'OCR / PDF image existant et ses limites V1.
- [x] Relire le fallback visuel/image existant pour les documents actifs.
- [x] Relire les surfaces `workspace_files`, selections et fichiers rattaches a
  un dossier.
- [x] Relire les surfaces UI liees aux fichiers/documents dans un dossier.
- [x] Relire les read-models et logs existants lies aux documents.
- [x] Identifier les briques reutilisables telles quelles.
- [x] Identifier les briques reutilisables partiellement.
- [x] Identifier les surfaces a eviter ou hors-scope.
- [x] Identifier les risques de melange avec Biblio, Notes, Exports et Images.
- [x] Produire un audit content-free date sous `app/docs/states/audits/`.

Sortie attendue:

- cartographie des fichiers/modules existants;
- classification "reutiliser / adapter / eviter / auditer plus tard";
- aucun patch runtime.

Preuve Lot 0:

- audit content-free:
  `app/docs/states/audits/frida-v1-documents-ingestion-lot0-audit-2026-06-17.md`;
- aucune implementation runtime;
- aucun acces Nextcloud/WebDAV/Sauron;
- aucun fichier utilisateur lu, copie, range, migre ou supprime.

### Lot 1 - Contrat produit Documents V1

- [x] Creer la spec source-of-truth:
  `app/docs/states/specs/frida-v1-documents-ingestion-contract.md`.
- [x] Graver le document source rattache a un `workspace_folder`.
- [x] Graver le prerequis strict: dossier Frida `linked`.
- [x] Graver la cible normative `/Frida/<dossier>/Documents`.
- [x] Graver la relation document -> dossier -> conversation -> usage.
- [x] Graver ce qu'un document de dossier peut devenir dans une conversation
  sans devenir automatiquement `active_document`.
- [x] Graver les surfaces utilisateur: depot par dossier `linked`, liste par
  dossier, selection explicite, usage conversationnel borne.
- [x] Graver les regles de noms visibles utilisateur vs preuves content-free.
- [x] Graver la strategie PDF texte: extraction texte bornee.
- [x] Graver la strategie PDF image: fallback visuel unifie, sans fausse
  promesse de lecture textuelle.
- [x] Graver la politique fichiers existants: copie/rangement controle
  obligatoire si fichiers actifs, jamais silencieux ni destructif.
- [x] Graver les etats produit minimaux: disponible, en preparation, lisible,
  non injecte, PDF sans texte, image/fallback requis, erreur, supprime ou
  indisponible.
- [x] Graver les reason codes content-free initiaux.
- [x] Graver les messages utilisateur sobres: document disponible, preparation
  en cours, document trop lourd, PDF sans texte, fallback visuel impossible,
  dossier non synchronise, cible Documents indisponible.
- [x] Graver la frontiere stricte avec `active_document`.
- [x] Graver la frontiere stricte avec Biblio / Catalogue.
- [x] Graver la frontiere stricte avec Notes, Exports et Images.
- [x] Graver les preuves attendues pour fermer le contrat.
- [x] Mettre a jour les index documentaires avec la nouvelle spec.

### Lot 2 - Modele local / read-model

- [x] Appliquer le contrat Lot 1: `workspace_files` devient le registre /
  read-model applicatif des documents persistants de dossier.
- [x] Relier document, dossier, conversation et usage sans creer de Biblio.
- [x] Relier un usage conversationnel a un document de dossier sans polluer
  Memory/RAG/Identity/Summary.
- [x] Appliquer les champs content-free minimaux: id applicatif, folder id,
  ref redacted, hash court du nom si utile, media type, taille, statut,
  timestamps, reason code.
- [x] Appliquer les statuts: disponible, en preparation, lisible, non lisible,
  PDF texte, PDF image/fallback, erreur, absent, deleted.
- [x] Separer explicitement projection utilisateur et projection technique.
- [x] Projection utilisateur: exposer le `display_name` / nom de fichier, type,
  taille, date, statut et readiness quand c'est utile a la liste documentaire.
- [x] Projection technique, logs, JSONL et observabilite: exposer seulement refs
  redacted, hashes courts, compteurs, statuts et reason codes, jamais le nom de
  fichier brut.
- [x] Appliquer l'observabilite content-free du read-model.
- [x] Tester qu'aucun `storage_key`, chemin disque, URL DAV, XML, secret ou
  contenu brut ne sort dans le payload.

Point de vigilance:

- le document persistant peut etre visible dans une UI produit; les logs et
  preuves ne doivent pas pour autant reprendre son nom brut si ce n'est pas
  indispensable.
- la projection technique doit allowlister les valeurs elles-memes, pas
  seulement filtrer les noms de cles; tout `mime_type`, `content_kind`,
  `media_kind`, `source_extension`, statut, readiness ou reason code suspect
  doit devenir `unknown`, vide ou redacted selon le champ.
- `parse_error` est un etat `error` avec reason code
  `folder_document_parse_error`, distinct de `unsupported`.

Preuve Lot 2:

- module local derive `app/core/workspace_folder_documents.py`;
- projections `document_v1_user`, `document_v1_technical` et
  `document_v1_usage`;
- aucune migration DB;
- aucun Nextcloud/WebDAV live;
- aucune copie/rangement/suppression de fichier utilisateur;
- tests unitaires et serveur couvrant projection utilisateur, projection
  technique redacted, dossier non `linked`, usage conversationnel et absence de
  confusion `active_document` / Biblio.
- correctif Lot 2.1: tests unitaires dedies sous
  `app/tests/unit/core/test_workspace_folder_documents.py`, projection technique
  allowlistee par valeurs et `parse_error` classe en `error`.

### Lot 3 - Ingestion / rangement nouveaux documents

- [ ] Appliquer le contrat Lot 1: depot par surface fichier/document du dossier
  Frida `linked`, ou action explicite de rangement depuis le chat courant.
- [ ] Bloquer tout depot si le dossier Frida n'est pas `linked`.
- [ ] Verifier `Documents` en `PROPFIND` Depth 0 seulement si live.
- [ ] Refuser une cible `Documents` absente, non-collection ou inaccessible avec
  reason code content-free.
- [ ] Sanitiser le nom cible sans exposer le nom brut dans les preuves.
- [ ] Gerer nom vide, extension absente, type interdit, nom trop long et
  collision apres sanitisation.
- [ ] Gerer conflit de nom local et conflit Nextcloud sans overwrite.
- [ ] Deposer le nouveau document dans `/Frida/<dossier>/Documents` seulement
  apres validations locales et Nextcloud.
- [ ] Ne pas deplacer silencieusement de fichier existant.
- [ ] Ne pas supprimer la source locale sans decision explicite et preuve.
- [ ] Appliquer rollback/compensation si depot Nextcloud reussit puis persistence
  locale echoue.
- [ ] Tester documents texte, PDF texte, PDF image, type refuse, conflit de nom
  et dossier non `linked`.

Interdits Lot 3:

- copie/rangement de fichiers historiques hors Lot 7;
- Biblio;
- Notes;
- Exports;
- Images;
- listing de contenu Nextcloud comme preuve large.

### Lot 4 - Liste des documents d'un dossier

- [ ] Appliquer le contrat Lot 1: liste utilisateur par dossier Frida courant.
- [ ] Lister les documents disponibles sans fuite de contenu.
- [ ] Ne pas faire de listing Nextcloud non borne comme preuve operateur.
- [ ] Appliquer le contrat Lot 1: noms de fichiers visibles en UI/reponse
  utilisateur utile, redacted en logs/preuves/observabilite technique.
- [ ] Exposer media type, taille, statut, date et readiness sans contenu.
- [ ] Gerer dossier non `linked`, `Documents` absent, `Documents` non-collection
  et erreur transport.
- [ ] Distinguer liste utilisateur et preuve JSONL content-free.
- [ ] Tester anti-fuite: pas de contenu, XML brut, URL DAV, chemin serveur,
  `storage_key`, secret, token, cookie ou `app-password`.

### Lot 5 - Lecture / preparation de lecture

- [ ] Appliquer le contrat Lot 1: selection explicite, preparation bornee,
  injection entiere ou refus, jamais troncature silencieuse.
- [ ] Reutiliser l'extracteur texte existant pour TXT, Markdown / MD, DOCX, ODT
  et PDF textuel.
- [ ] S'arreter en no-go avant patch ou ouvrir un micro-lot docs/spec si une
  incompatibilite runtime reelle empeche cette reutilisation.
- [ ] Appliquer les limites runtime du contrat: document entier ou absent,
  refus simple si trop lourd, preuves content-free.
- [ ] Ne jamais tronquer silencieusement un document en pretendant l'avoir lu.
- [ ] Appliquer la frontiere entre preparation de lecture et usage
  conversationnel.
- [ ] Appliquer l'usage conversationnel explicite d'un document de dossier.
- [ ] Ne pas creer d'index RAG global ni de passage Biblio.
- [ ] Ne pas alimenter Memory, Identity ou Summary avec le contenu document.
- [ ] Donner une reponse utilisateur honnete si le document est trop gros,
  indisponible, non supporte ou en erreur.
- [ ] Tester lecture nominale, trop gros, non supporte, parse error et
  non-contamination.

### Lot 6 - PDF image / fallback visuel unifie

- [ ] Appliquer le contrat Lot 1: PDF textuel par extraction texte bornee, PDF
  sans texte par fallback visuel/PDF image.
- [ ] Detecter PDF sans texte depuis un document de dossier.
- [ ] Detecter PDF sans texte depuis un upload direct dans le chat.
- [ ] Appliquer le meme fallback visuel aux deux chemins.
- [ ] Appliquer les limites V1 du fallback visuel: `25 pages`, `25 Mo`,
  `180` secondes pour toute preparation externe bornee si elle est utilisee.
- [ ] Ne pas melanger OCR borne et injection visuelle/PDF ponctuelle dans un
  statut ambigu.
- [ ] Garantir qu'un PDF deja textuel n'est pas OCRise.
- [ ] Garantir que Frida ne pretend pas avoir lu un PDF non injecte, non OCRise
  ou non preparable.
- [ ] Aligner les messages utilisateur pour PDF upload direct et PDF depuis
  Nextcloud.
- [ ] Aligner les reason codes et preuves pour les deux chemins.
- [ ] Ne pas exposer images, PDF, base64, texte OCR, contenu brut ou payload
  provider dans logs, dashboard, JSONL ou docs de preuve.
- [ ] Tester les deux chemins avec un PDF texte et un PDF image.

### Lot 7 - Fichiers existants

- [ ] Inventorier content-free les fichiers workspace existants rattaches a un
  dossier.
- [ ] Si l'inventaire trouve au moins un fichier actif rattache a un dossier
  Frida, livrer un rangement/copie controle vers
  `/Frida/<dossier>/Documents`.
- [ ] Si l'inventaire trouve `0` fichier actif a traiter, fermer le lot par
  preuve content-free `0 a traiter`.
- [ ] Interdire toute copie/rangement automatique.
- [ ] Travailler dossier par dossier.
- [ ] Conserver la source tant que preuve, verification et rollback ne sont pas
  actees.
- [ ] Ne jamais supprimer silencieusement la source.
- [ ] Ne jamais ecraser une cible Nextcloud existante sans decision humaine.
- [ ] Produire preuve content-free avant/apres.
- [ ] Documenter rollback et no-go.

### Lot 8 - Observabilite / smokes live

- [ ] Appliquer le catalogue initial des reason codes Documents V1 grave au
  Lot 1.
- [ ] Ajouter ou consolider les events content-free: depot, liste, preparation,
  lecture, PDF image detecte, fallback, conflit, erreur.
- [ ] Exposer compteurs et statuts, pas contenu.
- [ ] Exposer ids applicatifs, refs redacted ou hash courts, pas chemins.
- [ ] Verifier que dashboard/read-model ne fuit ni contenu ni nom sensible non
  necessaire.
- [ ] Produire JSONL content-free pour les smokes.
- [ ] Prouver un depot/liste/preparation avec document synthetique.
- [ ] Prouver le refus dossier non `linked`.
- [ ] Prouver le conflit de nom.
- [ ] Prouver PDF texte et PDF image/fallback sur les deux chemins.
- [ ] Scanner les artefacts contre contenu, nom sensible, chemin DAV, URL DAV,
  XML brut, `storage_key`, token, cookie, `app-password`, secret.

Artefacts attendus:

- audit ou baseline sous `app/docs/states/audits/` ou
  `app/docs/states/baselines/`;
- JSONL content-free avec `case_id`, `verdict`, `reason_code`, compteurs,
  `user_content_touched=false`, `secret_exposed=false`.

### Lot Z - Cloture Documents V1

- [ ] Appliquer les criteres de cloture Lot Z graves dans
  `app/docs/states/specs/frida-v1-documents-ingestion-contract.md`.
- [ ] Prouver qu'un dossier Frida `linked` peut recevoir un document sous
  `Documents`.
- [ ] Prouver que la liste utilisateur montre les documents disponibles sans
  fuite.
- [ ] Prouver qu'un document texte ou PDF texte peut etre prepare/lu selon le
  contrat.
- [ ] Prouver qu'un PDF image suit le meme fallback depuis upload direct et
  depuis dossier Nextcloud.
- [ ] Prouver que les limites, messages et reason codes sont coherents sur les
  deux chemins PDF.
- [ ] Prouver qu'un dossier non `linked` bloque les ecritures.
- [ ] Prouver absence de confusion avec Biblio, Notes, Exports et Images.
- [ ] Prouver absence de copie/rangement silencieux des fichiers existants.
- [ ] Prouver absence de fuite de contenu, nom sensible, chemin DAV, URL DAV,
  XML brut, `storage_key`, token, cookie, `app-password` et secret.
- [ ] Documenter limites V1 et lots suivants.
- [ ] Archiver les preuves content-free.

## 9. Points faibles a surveiller

- Confondre documents actifs de conversation et documents persistants de
  dossier.
- Confondre Documents et Biblio / Catalogue.
- Copier/ranger silencieusement les fichiers existants.
- Faire fuiter noms de fichiers ou contenu dans logs/preuves.
- Avoir deux comportements differents entre PDF upload direct et PDF depuis
  Nextcloud.
- Lire ou lister le contenu Nextcloud pour prouver un etat qui devrait etre
  prouve par status, compteurs ou document synthetique.
- Lancer trop tot Exports, Notes ou Images.
- Ajouter une route parallele ou un modele produit parallele inutile.
- Presenter une extraction partielle comme complete.
- Pretendre avoir lu un document trop gros, non injecte ou en erreur.

## 10. Hors-scope strict des Lots 1-2 livres

- Aucun runtime Nextcloud.
- Aucun acces Nextcloud live.
- Aucun WebDAV live.
- Aucun Sauron.
- Aucun secret.
- Aucun Docker/rebuild plateforme/global; un rebuild applicatif FridaDev cible
  reste autorise pour verifier un patch runtime Documents V1.
- Aucune copie/rangement fichier.
- Aucune creation de document, note, export ou image.
- Aucun lancement Biblio.
- Aucun changement de route/API/UI.
- Aucun `utils.py` ou `helpers.py`.

## 11. Prochain lot recommande

Ouvrir `Lot 3 - Ingestion / rangement nouveaux documents`.

Objectif Lot 3:

- appliquer le contrat source-of-truth Documents V1;
- deposer/ranger de nouveaux documents dans `/Frida/<dossier>/Documents`
  seulement pour un dossier Frida `linked`;
- refuser proprement les dossiers non `linked`, cibles `Documents` invalides,
  types interdits et conflits de nom;
- garder les payloads, logs et preuves content-free.
