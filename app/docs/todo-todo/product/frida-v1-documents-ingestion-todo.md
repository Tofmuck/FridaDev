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
- les fichiers workspace existants ne sont pas migres automatiquement;
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
- Pas de migration silencieuse des fichiers existants.
- Pas de suppression source silencieuse apres copie.
- Pas de route ou modele parallele qui contourne `workspace_folders`.
- Pas de confusion entre document persistant de dossier et document actif de
  conversation.
- Pas de confusion entre Documents et Biblio.
- Pas de lancement anticipe Notes, Exports ou Images.

## 5. Lots proposes

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
- decision "reutiliser / adapter / eviter / auditer plus tard";
- aucun patch runtime.

### Lot 1 - Contrat produit Documents V1

- [ ] Definir le document source rattache a un `workspace_folder`.
- [ ] Definir le prerequis strict: dossier Frida `linked`.
- [ ] Definir la cible normative `/Frida/<dossier>/Documents`.
- [ ] Definir la relation document -> dossier -> conversation -> usage.
- [ ] Definir ce qu'un document de dossier peut devenir dans une conversation
  sans devenir automatiquement `active_document`.
- [ ] Definir les etats produit minimaux: disponible, en preparation, lisible,
  non injecte, PDF sans texte, image/fallback requis, erreur, supprime ou
  indisponible.
- [ ] Definir les reason codes content-free initiaux.
- [ ] Definir les messages utilisateur sobres: document disponible, preparation
  en cours, document trop lourd, PDF sans texte, fallback image/OCR impossible,
  dossier non synchronise, cible Documents indisponible.
- [ ] Definir la frontiere stricte avec `active_document`.
- [ ] Definir la frontiere stricte avec Biblio / Catalogue.
- [ ] Definir la frontiere stricte avec Notes, Exports et Images.
- [ ] Definir les preuves attendues pour fermer le contrat.

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

- [ ] Decider comment representer les documents persistants d'un dossier Frida.
- [ ] Decider si un modele/table applicatif dedie est necessaire ou si un
  read-model derive suffit pour le premier runtime.
- [ ] Relier document, dossier, conversation et usage sans creer de Biblio.
- [ ] Relier un usage conversationnel a un document de dossier sans polluer
  Memory/RAG/Identity/Summary.
- [ ] Definir les champs content-free minimaux: id applicatif, folder id,
  ref redacted, hash court du nom si utile, media type, taille, statut,
  timestamps, reason code.
- [ ] Definir les statuts: disponible, en preparation, lisible, non lisible,
  PDF texte, PDF image/fallback, erreur, absent, deleted.
- [ ] Definir les projections API/UI sans nom sensible si une ref courte suffit.
- [ ] Definir l'observabilite content-free du read-model.
- [ ] Tester qu'aucun `storage_key`, chemin disque, URL DAV, XML, secret ou
  contenu brut ne sort dans le payload.

Point de vigilance:

- le document persistant peut etre visible dans une UI produit; les logs et
  preuves ne doivent pas pour autant reprendre son nom brut si ce n'est pas
  indispensable.

### Lot 3 - Ingestion / rangement nouveaux documents

- [ ] Definir la surface utilisateur de depot: UI dossier, chat avec dossier
  courant, ou autre surface existante a confirmer par le Lot 1.
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
- [ ] Definir rollback/compensation si depot Nextcloud reussit puis persistence
  locale echoue.
- [ ] Tester documents texte, PDF texte, PDF image, type refuse, conflit de nom
  et dossier non `linked`.

Interdits Lot 3:

- migration de fichiers historiques;
- Biblio;
- Notes;
- Exports;
- Images;
- listing de contenu Nextcloud comme preuve large.

### Lot 4 - Liste des documents d'un dossier

- [ ] Definir la surface utilisateur de liste des documents d'un dossier.
- [ ] Lister les documents disponibles sans fuite de contenu.
- [ ] Ne pas faire de listing Nextcloud non borne comme preuve operateur.
- [ ] Decider si la liste utilisateur peut afficher les noms visibles ou si une
  projection redacted est requise selon contexte.
- [ ] Exposer media type, taille, statut, date et readiness sans contenu.
- [ ] Gerer dossier non `linked`, `Documents` absent, `Documents` non-collection
  et erreur transport.
- [ ] Distinguer liste utilisateur et preuve JSONL content-free.
- [ ] Tester anti-fuite: pas de contenu, XML brut, URL DAV, chemin serveur,
  `storage_key`, secret, token, cookie ou `app-password`.

### Lot 5 - Lecture / preparation de lecture

- [ ] Reutiliser l'extracteur texte existant quand c'est compatible.
- [ ] Supporter document texte simple.
- [ ] Supporter PDF textuel.
- [ ] Supporter DOCX, ODT, Markdown et TXT si deja supportes par les briques
  existantes ou documenter les manques.
- [ ] Definir limites taille/pages/tokens avant lecture.
- [ ] Ne jamais tronquer silencieusement un document en pretendant l'avoir lu.
- [ ] Definir preparation de lecture distincte de l'injection conversationnelle.
- [ ] Definir comment une conversation utilise un document de dossier.
- [ ] Ne pas creer d'index RAG global ni de passage Biblio.
- [ ] Ne pas alimenter Memory, Identity ou Summary avec le contenu document.
- [ ] Donner une reponse utilisateur honnete si le document est trop gros,
  indisponible, non supporte ou en erreur.
- [ ] Tester lecture nominale, trop gros, non supporte, parse error et
  non-contamination.

### Lot 6 - PDF image / OCR / fallback visuel unifie

- [ ] Detecter PDF sans texte depuis un document de dossier.
- [ ] Detecter PDF sans texte depuis un upload direct dans le chat.
- [ ] Appliquer une politique commune aux deux chemins.
- [ ] Reutiliser les limites active documents si elles restent valides:
  `25 pages`, `25 Mo`, `180` secondes, `fra+eng+deu`.
- [ ] Decider explicitement si le chemin Documents V1 utilise OCR, fallback
  visuel/multimodal, ou les deux selon statut.
- [ ] Garantir qu'un PDF deja textuel n'est pas OCRise.
- [ ] Garantir que Frida ne pretend pas avoir lu un PDF non injecte, non OCRise
  ou non preparable.
- [ ] Aligner les messages utilisateur pour PDF upload direct et PDF depuis
  Nextcloud.
- [ ] Aligner les reason codes et preuves pour les deux chemins.
- [ ] Ne pas exposer images, PDF, base64, texte OCR, contenu brut ou payload
  provider dans logs, dashboard, JSONL ou docs de preuve.
- [ ] Tester les deux chemins avec un PDF texte et un PDF image.

Point a trancher dans ce lot:

- le fallback visuel unifie doit-il etre une injection multimodale ponctuelle,
  une OCR bornee, ou une strategie ordonnee OCR puis visuel selon disponibilite
  modele/provider?

Si cette decision manque encore au moment du code, s'arreter et demander.

### Lot 7 - Fichiers existants

- [ ] Inventorier content-free les fichiers workspace existants rattaches a un
  dossier.
- [ ] Decider si une copie/migration vers `Documents` est ouverte ou repoussee.
- [ ] Confirmer qu'il n'y a pas de migration automatique.
- [ ] Si un lot de migration est ouvert, travailler dossier par dossier.
- [ ] Conserver la source tant que preuve, verification et rollback ne sont pas
  actees.
- [ ] Ne jamais supprimer silencieusement la source.
- [ ] Ne jamais ecraser une cible Nextcloud existante sans decision humaine.
- [ ] Produire preuve content-free avant/apres.
- [ ] Documenter rollback et no-go.

Ce lot peut rester une decision "no migration V1" si le produit n'exige pas de
reprendre les fichiers historiques avant cloture Documents.

### Lot 8 - Observabilite / smokes live

- [ ] Definir le catalogue final des reason codes Documents V1.
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
- [ ] Prouver absence de migration silencieuse des fichiers existants.
- [ ] Prouver absence de fuite de contenu, nom sensible, chemin DAV, URL DAV,
  XML brut, `storage_key`, token, cookie, `app-password` et secret.
- [ ] Documenter limites V1 et lots suivants.
- [ ] Archiver les preuves content-free.

## 6. Points faibles a surveiller

- Confondre documents actifs de conversation et documents persistants de
  dossier.
- Confondre Documents et Biblio / Catalogue.
- Migrer silencieusement les fichiers existants.
- Faire fuiter noms de fichiers ou contenu dans logs/preuves.
- Avoir deux comportements differents entre PDF upload direct et PDF depuis
  Nextcloud.
- Lire ou lister le contenu Nextcloud pour prouver un etat qui devrait etre
  prouve par status, compteurs ou document synthetique.
- Lancer trop tot Exports, Notes ou Images.
- Ajouter une route parallele ou un modele produit parallele inutile.
- Presenter une extraction partielle comme complete.
- Pretendre avoir lu un document trop gros, non injecte ou en erreur.

## 7. Hors-scope strict de cette TODO de cadrage

- Aucun code runtime.
- Aucun acces Nextcloud live.
- Aucun WebDAV live.
- Aucun Sauron.
- Aucun secret.
- Aucun Docker/rebuild.
- Aucune migration fichier.
- Aucune creation de document, note, export ou image.
- Aucun lancement Biblio.
- Aucun changement de route/API/UI.
- Aucun `utils.py` ou `helpers.py`.

## 8. Prochain lot recommande

Ouvrir `Lot 0 - Audit existant`.

Objectif Lot 0:

- lire le code et les tests documents actifs / OCR / workspace files;
- produire un audit content-free date;
- confirmer les surfaces reutilisables;
- lister les no-go avant tout runtime Documents V1.
