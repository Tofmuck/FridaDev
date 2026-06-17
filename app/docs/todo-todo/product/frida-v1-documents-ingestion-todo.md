# Frida V1 - Documents sources / ingestion / lecture / PDF fallback - TODO

Statut: TODO detaillee, prete pour Lot 0 audit
Date: 2026-06-17
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`
Socle dossiers source: `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
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

## 5. Decisions produit deja prises

- Le chantier Documents V1 vient apres la cloture du socle dossiers Frida V1 /
  Nextcloud.
- Le dossier Frida visible dans l'UI reste le `workspace_folder`.
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

## 6. Decisions ouvertes avant runtime

Aucun lot runtime Documents V1 ne doit commencer si une decision ouverte de
cette section le bloque. Les decisions doivent etre tranchees dans Lot 1 ou dans
un micro-lot docs/spec explicite avant tout patch runtime concerne.

- Modele local Documents:
  - options a trancher: table applicative dediee, extension stricte d'une table
    existante, ou read-model derive;
  - bloque: Lot 2 et tous les lots runtime qui persistent ou projettent des
    documents de dossier.
- Surface utilisateur de depot:
  - options a trancher: depot depuis UI dossier, depuis chat avec dossier
    courant, ou autre surface existante documentee;
  - bloque: Lot 3.
- Surface utilisateur de liste:
  - options a trancher: panneau dossier, liste dans chat avec dossier courant,
    surface fichiers existante, ou autre surface documentee;
  - bloque: Lot 4.
- Visibilite des noms de fichiers:
  - options a trancher: noms visibles en UI produit, refs redacted en preuves,
    ou regle hybride stricte;
  - bloque: Lots 4, 8 et tout dashboard/read-model utilisateur.
- Lecture et usage conversationnel:
  - options a trancher: limites taille/pages/tokens, preparation de lecture vs
    injection conversationnelle, et maniere dont une conversation utilise un
    document de dossier;
  - bloque: Lot 5 et toute preuve Lot Z portant sur lecture/preparation.
- Strategie PDF image Documents V1:
  - options a trancher: OCR seulement, visuel seulement, OCR puis visuel en
    fallback, ou strategie differente clairement documentee;
  - bloque: Lot 6 et toute preuve Lot Z portant sur PDF image.
- Politique operationnelle des fichiers existants:
  - decision produit deja prise: traitement obligatoire si fichiers actifs
    confirmes;
  - restent a trancher avant runtime: copie seule, copie puis verification,
    conservation de source, rollback exact, gestion de collision;
  - bloque: Lot 7 runtime de copie/rangement.
- Catalogue reason codes Documents V1:
  - options a trancher: catalogue final minimal, noms des codes, codes
    partages avec `active_document`, codes specifiques Nextcloud et codes de
    redaction;
  - bloque: Lot 8 et Lot Z.
- Conditions exactes de cloture Documents V1:
  - doivent etre gravees avant Lot Z: smokes minimum, formats minimum,
    criteres PDF image, preuves anti-fuite et limites assumables;
  - bloque: Lot Z.

## 7. Nature des lots

- Lot 0: audit read-only/docs-only.
- Lot 1: contrat produit docs-only; il doit trancher ou bloquer explicitement
  les decisions ouvertes avant runtime.
- Lot 2: modele local / read-model; runtime local possible, sans Nextcloud live.
- Lot 3: ingestion/rangement; runtime applicatif avec ecriture Nextcloud.
- Lot 4: liste documents; runtime applicatif et read-model.
- Lot 5: lecture/preparation; runtime applicatif sans Biblio/RAG global.
- Lot 6: PDF image / OCR / fallback; runtime bloque tant que la strategie PDF
  image n'est pas tranchee.
- Lot 7: fichiers existants; obligatoire si l'audit trouve des fichiers actifs,
  fermable par preuve `0 a traiter` sinon.
- Lot 8: observabilite / smokes live; preuves JSONL content-free.
- Lot Z: validation/cloture Documents V1; live proof sur documents synthetiques.

## 8. Lots proposes

Ne cocher que les lots reellement livres et prouves.

### Lot 0 - Audit existant

- [ ] Relire les surfaces runtime des documents actifs de conversation.
- [ ] Relire l'upload direct dans le chat et les routes existantes
  `active_document`.
- [ ] Relire l'extraction texte existante: PDF textuel, DOCX, ODT, MD, TXT.
- [ ] Relire l'OCR / PDF image existant et ses limites V1.
- [ ] Relire le fallback visuel/image existant pour les documents actifs.
- [ ] Relire les surfaces `workspace_files`, selections et fichiers rattaches a
  un dossier.
- [ ] Relire les surfaces UI liees aux fichiers/documents dans un dossier.
- [ ] Relire les read-models et logs existants lies aux documents.
- [ ] Identifier les briques reutilisables telles quelles.
- [ ] Identifier les briques reutilisables partiellement.
- [ ] Identifier les surfaces a eviter ou hors-scope.
- [ ] Identifier les risques de melange avec Biblio, Notes, Exports et Images.
- [ ] Produire un audit content-free date sous `app/docs/states/audits/`.

Sortie attendue:

- cartographie des fichiers/modules existants;
- classification "reutiliser / adapter / eviter / auditer plus tard";
- aucun patch runtime.

### Lot 1 - Contrat produit Documents V1

- [ ] Graver le document source rattache a un `workspace_folder`.
- [ ] Graver le prerequis strict: dossier Frida `linked`.
- [ ] Graver la cible normative `/Frida/<dossier>/Documents`.
- [ ] Graver la relation document -> dossier -> conversation -> usage.
- [ ] Graver ce qu'un document de dossier peut devenir dans une conversation
  sans devenir automatiquement `active_document`.
- [ ] Graver les etats produit minimaux: disponible, en preparation, lisible,
  non injecte, PDF sans texte, image/fallback requis, erreur, supprime ou
  indisponible.
- [ ] Graver les reason codes content-free initiaux.
- [ ] Graver les messages utilisateur sobres: document disponible, preparation
  en cours, document trop lourd, PDF sans texte, fallback image/OCR impossible,
  dossier non synchronise, cible Documents indisponible.
- [ ] Graver la frontiere stricte avec `active_document`.
- [ ] Graver la frontiere stricte avec Biblio / Catalogue.
- [ ] Graver la frontiere stricte avec Notes, Exports et Images.
- [ ] Graver les preuves attendues pour fermer le contrat.
- [ ] Trancher ou bloquer explicitement chaque decision de la section
  "Decisions ouvertes avant runtime".

Reason codes candidats a stabiliser:

- `folder_document_folder_not_linked`;
- `folder_document_documents_target_missing`;
- `folder_document_documents_target_conflict`;
- `folder_document_name_invalid`;
- `folder_document_name_conflict`;
- `folder_document_upload_ok`;
- `folder_document_list_ok`;
- `folder_document_prepare_ok`;
- `folder_document_text_ready`;
- `folder_document_pdf_text_ready`;
- `folder_document_pdf_image_fallback_required`;
- `folder_document_ocr_too_large`;
- `folder_document_ocr_too_many_pages`;
- `folder_document_runtime_unavailable`;
- `folder_document_nextcloud_error_redacted`;
- `folder_document_content_redacted`.

### Lot 2 - Modele local / read-model

- [ ] Appliquer la decision amont sur la representation locale des documents
  persistants d'un dossier Frida.
- [ ] Refuser le lot si la decision "Modele local Documents" n'est pas tranchee.
- [ ] Relier document, dossier, conversation et usage sans creer de Biblio.
- [ ] Relier un usage conversationnel a un document de dossier sans polluer
  Memory/RAG/Identity/Summary.
- [ ] Appliquer les champs content-free minimaux: id applicatif, folder id,
  ref redacted, hash court du nom si utile, media type, taille, statut,
  timestamps, reason code.
- [ ] Appliquer les statuts: disponible, en preparation, lisible, non lisible,
  PDF texte, PDF image/fallback, erreur, absent, deleted.
- [ ] Appliquer les projections API/UI sans nom sensible si une ref courte suffit.
- [ ] Appliquer l'observabilite content-free du read-model.
- [ ] Tester qu'aucun `storage_key`, chemin disque, URL DAV, XML, secret ou
  contenu brut ne sort dans le payload.

Point de vigilance:

- le document persistant peut etre visible dans une UI produit; les logs et
  preuves ne doivent pas pour autant reprendre son nom brut si ce n'est pas
  indispensable.

### Lot 3 - Ingestion / rangement nouveaux documents

- [ ] Appliquer la decision amont sur la surface utilisateur de depot.
- [ ] Refuser le lot si la decision "Surface utilisateur de depot" n'est pas
  tranchee.
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

- [ ] Appliquer la decision amont sur la surface utilisateur de liste.
- [ ] Refuser le lot si la decision "Surface utilisateur de liste" n'est pas
  tranchee.
- [ ] Lister les documents disponibles sans fuite de contenu.
- [ ] Ne pas faire de listing Nextcloud non borne comme preuve operateur.
- [ ] Appliquer la decision amont sur la visibilite des noms de fichiers.
- [ ] Refuser le lot si la decision "Visibilite des noms de fichiers" n'est pas
  tranchee.
- [ ] Exposer media type, taille, statut, date et readiness sans contenu.
- [ ] Gerer dossier non `linked`, `Documents` absent, `Documents` non-collection
  et erreur transport.
- [ ] Distinguer liste utilisateur et preuve JSONL content-free.
- [ ] Tester anti-fuite: pas de contenu, XML brut, URL DAV, chemin serveur,
  `storage_key`, secret, token, cookie ou `app-password`.

### Lot 5 - Lecture / preparation de lecture

- [ ] Refuser le lot si la decision "Lecture et usage conversationnel" n'est
  pas tranchee.
- [ ] Reutiliser l'extracteur texte existant quand c'est compatible.
- [ ] Supporter document texte simple.
- [ ] Supporter PDF textuel.
- [ ] Supporter DOCX, ODT, Markdown et TXT si deja supportes par les briques
  existantes ou documenter les manques.
- [ ] Appliquer les limites taille/pages/tokens tranchees avant lecture.
- [ ] Ne jamais tronquer silencieusement un document en pretendant l'avoir lu.
- [ ] Appliquer la frontiere tranchee entre preparation de lecture et injection
  conversationnelle.
- [ ] Appliquer le mode d'usage conversationnel tranche pour un document de
  dossier.
- [ ] Ne pas creer d'index RAG global ni de passage Biblio.
- [ ] Ne pas alimenter Memory, Identity ou Summary avec le contenu document.
- [ ] Donner une reponse utilisateur honnete si le document est trop gros,
  indisponible, non supporte ou en erreur.
- [ ] Tester lecture nominale, trop gros, non supporte, parse error et
  non-contamination.

### Lot 6 - PDF image / OCR / fallback visuel unifie

- [ ] Refuser le lot si la decision "Strategie PDF image Documents V1" n'est
  pas tranchee.
- [ ] Detecter PDF sans texte depuis un document de dossier.
- [ ] Detecter PDF sans texte depuis un upload direct dans le chat.
- [ ] Appliquer la strategie PDF image tranchee aux deux chemins.
- [ ] Reutiliser les limites active documents si elles restent valides:
  `25 pages`, `25 Mo`, `180` secondes, `fra+eng+deu`.
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
- [ ] Refuser le runtime de copie si la decision "Politique operationnelle des
  fichiers existants" n'est pas tranchee.
- [ ] Interdire toute copie/rangement automatique.
- [ ] Travailler dossier par dossier.
- [ ] Conserver la source tant que preuve, verification et rollback ne sont pas
  actees.
- [ ] Ne jamais supprimer silencieusement la source.
- [ ] Ne jamais ecraser une cible Nextcloud existante sans decision humaine.
- [ ] Produire preuve content-free avant/apres.
- [ ] Documenter rollback et no-go.

### Lot 8 - Observabilite / smokes live

- [ ] Refuser le lot si la decision "Catalogue reason codes Documents V1" n'est
  pas tranchee.
- [ ] Appliquer le catalogue final des reason codes Documents V1.
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
- [ ] Prouver PDF texte et PDF image/fallback sur les deux chemins si le
  fallback est livre.
- [ ] Scanner les artefacts contre contenu, nom sensible, chemin DAV, URL DAV,
  XML brut, `storage_key`, token, cookie, `app-password`, secret.

Artefacts attendus:

- audit ou baseline sous `app/docs/states/audits/` ou
  `app/docs/states/baselines/`;
- JSONL content-free avec `case_id`, `verdict`, `reason_code`, compteurs,
  `user_content_touched=false`, `secret_exposed=false`.

### Lot Z - Cloture Documents V1

- [ ] Refuser Lot Z si les conditions exactes de cloture Documents V1 ne sont
  pas gravees avant validation.
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

## 10. Hors-scope strict de cette TODO de cadrage

- Aucun code runtime.
- Aucun acces Nextcloud live.
- Aucun WebDAV live.
- Aucun Sauron.
- Aucun secret.
- Aucun Docker/rebuild.
- Aucune copie/rangement fichier.
- Aucune creation de document, note, export ou image.
- Aucun lancement Biblio.
- Aucun changement de route/API/UI.
- Aucun `utils.py` ou `helpers.py`.

## 11. Prochain lot recommande

Ouvrir `Lot 0 - Audit existant`.

Objectif Lot 0:

- lire le code et les tests documents actifs / OCR / workspace files;
- produire un audit content-free date;
- valider les surfaces reutilisables;
- lister les no-go avant tout runtime Documents V1.
