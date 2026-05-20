# FridaDev - atelier documentaire / répertoires de travail - TODO

Statut: ouvert
Date de creation: 2026-05-20
Classement: `app/docs/todo-todo/product/`
Boussole produit source: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`
Spec source-of-truth Lot 0: `app/docs/states/specs/workspace-folders-contract.md`
Specs et archives sources:
- `app/docs/states/specs/workspace-folders-contract.md`
- `app/docs/states/specs/active-conversation-documents-contract.md`
- `app/docs/todo-done/product/active-conversation-documents-todo.md`
- `app/docs/todo-done/product/active-conversation-documents-ocr-todo.md`
- `app/docs/todo-done/product/fridadev-active-image-documents-todo.md`
Portée: organisation de répertoires de travail, conversations, fichiers persistants, ressources OCR dérivées, sélection explicite vers les documents actifs.
Hors-scope initial: mémoire par répertoire, Biblio, RAG documentaire par répertoire, prompt de projet, identité, résumé, multi-utilisateur.

## 1. Verdict de plan

Existe-t-il un meilleur plan ?

Non pour ce cycle. Le bon plan est un audit court du code et des docs existants, puis la création d'un TODO produit conforme aux surfaces déjà livrées. Il ne faut pas implémenter maintenant: le chantier touche DB, disque, UI sidebar, active documents, images actives, OCR et non-contamination. Une mauvaise architecture ferait vite une Biblio déguisée ou un prompt de projet déguisé.

## 2. Concept central

Créer des répertoires de travail visibles dans la sidebar gauche du chat.

Ils servent à organiser:

- conversations;
- fichiers persistants;
- ressources OCR dérivées.

Ils ne sont pas:

- une mémoire;
- une Biblio;
- un RAG documentaire;
- un prompt de projet;
- une identité;
- un résumé;
- un espace cognitif séparé.

Formule source:

```text
Documents actifs = ce que Frida peut lire maintenant.
Atelier documentaire = ce que l'utilisateur garde à portée de main.
Biblio = ce qui est conservé durablement comme fonds/catalogue.
```

La mémoire/RAG existante reste globale et transversale. Il n'y a pas de mémoire/RAG par répertoire.

## 3. Audit court du code existant

Surfaces réellement trouvées:

- `app/core/active_conversation_documents.py`: état DB `active_conversation_documents`, conversation-scoped, avec texte ou image, soft deactivation, metadata content-free, `list_active_documents_for_prompt()`, `record_document_injected()`, `record_document_excluded()`, purge des documents désactivés.
- `app/core/active_document_upload_service.py`: routes métier upload/list/remove, validation de conversation, extraction texte, OCR PDF bornée seulement après `document_ocr_required`, upload image via validation dédiée, réponses content-free.
- `app/core/active_document_text_extraction.py`: formats texte supportés `TXT`, `MD`, `PDF`, `DOCX`, `ODT`; extraction complète ou statut explicite; pas de résumé, pas de chunk.
- `app/core/active_document_image_validation.py`: images V0 `PNG`, `JPEG`, `WEBP`; sniff bytes/dimensions; refus GIF V0; plafond source 32 MiB; reason codes image.
- `app/core/active_document_ocr_client.py`: OCR PDF bornée via Stirling, `25 pages`, `25 Mo`, `180` secondes, `fra+eng+deu`; retourne PDF OCRisé en mémoire et metadata compactes.
- `app/core/active_document_prompt_lane.py`: injection entière ou exclusion entière; contrat système séparé; contenu documentaire en message `user`; images envoyées en `text` puis `image_url`; allowlist image active `anthropic/claude-sonnet-4.6` et `openai/gpt-5.1`; plafond provider image 8 MiB.
- `app/observability/active_documents_observability.py`: événements content-free d'activation, échec, retrait et décision par tour; pas de contenu brut; `future_biblio_included=False`.
- `app/server.py`: routes `GET/POST/DELETE /api/conversations/<conversation_id>/active-documents*` et routes conversations `GET/POST/PATCH/DELETE /api/conversations*`.
- `app/core/conversations_maintenance.py`, `app/core/conversations_store.py`, `app/core/conversations_service.py`: catalogue conversationnel DB avec `conversations`, `conversation_messages`, titre, timestamps, soft delete, renommage.
- `app/web/chat_threads_sidebar.js`: sidebar conversations actuelle avec liste, création, renommage manuel, suppression, chargement et cache messages.
- `app/web/chat_active_documents.js`: upload multi-fichiers, drag-and-drop sur la surface chat, chips de documents actifs, retrait, statuts OCR/image/erreurs.
- `app/web/app.js`, `app/web/index.html`, `app/web/styles.css`: intégration UI chat, bouton document actif, input fichiers, sidebar gauche existante, active documents bar.

Alignement du TODO avec l'existant:

- le futur atelier doit réutiliser le contrat `active_document` pour l'injection, pas inventer une nouvelle lane souveraine;
- le stockage de répertoire doit être durable, mais la visibilité modèle doit rester une sélection explicite par conversation;
- les fichiers persistants du répertoire ne doivent pas devenir automatiquement des documents actifs;
- l'OCR image n'existe pas aujourd'hui: il doit être contracté comme nouveau sous-flux, distinct de l'OCR PDF actif actuel;
- la sidebar dispose déjà d'un contrôleur conversations, mais pas de notion de répertoire;
- le système actuel stocke certains contenus actifs en DB; le chantier répertoire doit décider explicitement le contrat DB/disque durable au lieu de réutiliser naïvement cette table courte durée;
- les logs et read-models doivent rester content-free, comme l'observabilité active documents existante.

## 4. UX sidebar attendue

Les répertoires de travail apparaissent dans la sidebar gauche.

Règles UX:

- répertoires affichés au-dessus des conversations hors répertoire;
- conversations hors répertoire listées sous les répertoires;
- ligne de séparation très fine entre répertoires et conversations hors répertoire;
- création de répertoire;
- renommage de répertoire;
- suppression de répertoire;
- ordre manuel des répertoires;
- déplacement de conversations dans un répertoire, idéalement par glisser-déposer;
- possibilité de sortir une conversation d'un répertoire;
- renommage manuel des conversations conservé;
- nommage automatique des conversations à prévoir dans ce chantier ou dans un lot séparé proche.

V0 recommandée:

- une conversation peut être hors répertoire;
- une conversation appartient à zéro ou un répertoire;
- supprimer un répertoire ne supprime pas automatiquement les conversations;
- les conversations reviennent hors répertoire si le répertoire est supprimé, sauf décision future explicitement documentée.

## 5. Icônes et description

Chaque répertoire peut avoir un petit logo/icône.

Contraintes V0:

- environ 15 icônes disponibles;
- style minimaliste, doux, compatible Frida;
- pas d'emoji système criard;
- pas d'upload de logo custom en V0;
- stocker une clé d'icône allowlistée, par exemple `icon_key`;
- icônes petites, lisibles, mignonnes, sobres.

Familles possibles:

- livre;
- plume;
- étoile;
- feuille;
- dossier;
- lune;
- cercle;
- fragment;
- archive;
- loupe;
- note;
- image;
- carte;
- dialogue;
- étincelle sobre.

Description courte:

- un répertoire peut avoir une description très courte optionnelle;
- la description sert l'UI et la lisibilité opérateur;
- elle n'est pas injectée au modèle par défaut en V0;
- ce n'est pas un prompt de répertoire;
- ce n'est pas une doctrine;
- ce n'est pas une personnalité;
- si elle est utilisée plus tard, elle doit rester une provenance faible, jamais une instruction système.

Formulation à conserver:

```text
Le répertoire peut avoir une description pour l'interface et la lisibilité opérateur. Cette description n'est pas un prompt et ne gouverne pas la réponse.
```

## 6. Conversations

Règles produit:

- une conversation peut être hors répertoire;
- une conversation peut être déplacée dans un répertoire;
- V0 recommandée: une conversation appartient à zéro ou un répertoire;
- supprimer un répertoire ne doit pas supprimer automatiquement les conversations;
- les conversations reviennent hors répertoire si le répertoire est supprimé, sauf choix contraire explicitement documenté;
- le renommage manuel existant doit rester disponible;
- le nommage automatique des conversations doit être prévu, soit dans ce chantier, soit dans un lot séparé proche.

Point DB pressenti:

- ajouter une relation conversation -> répertoire de travail, probablement nullable;
- préserver les conversations existantes hors répertoire;
- préserver le soft delete actuel des conversations;
- ne pas créer de séparation mémoire/identity/summary par répertoire.

## 7. Fichiers de répertoire

Un répertoire contient des fichiers persistants.

Les fichiers doivent exister:

- physiquement sur le serveur;
- en base de données.

Contrat DB/disque à définir:

- chaque répertoire de travail doit correspondre à un espace physique dédié côté serveur, ou à un préfixe disque stable réservé à ce répertoire;
- ne pas utiliser les noms humains des répertoires ou fichiers comme chemins fiables;
- utiliser un identifiant stable côté serveur pour construire l'espace disque ou le préfixe interne;
- la DB garde le lien entre nom logique, répertoire, fichiers, identifiant stable et chemin interne;
- chemin physique interne non exposé directement à l'UI;
- nom logique affiché à l'utilisateur;
- hash;
- taille;
- MIME;
- type;
- dates;
- lien au répertoire;
- état supprimé ou suppression réelle selon politique retenue;
- stratégie d'incohérence DB/disque.

Les chemins restent internes. L'UI ne doit jamais exposer le chemin physique ni l'identifiant disque complet: elle affiche seulement les noms logiques, états et métadonnées utiles.

Types attendus:

- documents texte/PDF selon ce que supporte déjà FridaDev;
- images `PNG`, `JPEG`, `WEBP`;
- fichiers OCR dérivés Markdown;
- autres types uniquement si déjà supportés par le système actuel.

Vigilance:

- les fichiers persistants de répertoire ne sont pas la table courte durée `active_conversation_documents`;
- l'état actif de conversation reste la surface d'injection;
- le stockage durable doit avoir sa propre politique de suppression, de cohérence et de migration.

## 8. Sélection et injection

Règle centrale:

```text
Une conversation dans un répertoire ne voit pas automatiquement tous les fichiers du répertoire.
```

Le répertoire rend les fichiers disponibles. Frida ne reçoit que les fichiers explicitement cochés ou sélectionnés.

Raisons:

- éviter du payload inutile;
- garder le contrôle utilisateur;
- préserver le contrat active documents;
- empêcher l'injection silencieuse.

Exigences:

- sélection multi-fichiers;
- fichiers non sélectionnés invisibles pour le modèle;
- un fichier du répertoire n'est jamais injecté par défaut;
- une fois coché dans une conversation, il reste actif pour cette conversation jusqu'à décochage explicite, comme les documents actifs actuels;
- la sélection est conversation-scoped, pas globale au répertoire;
- une autre conversation du même répertoire ne reçoit pas automatiquement cette sélection;
- intégration avec la lane `active_document`;
- injection entière ou exclusion entière;
- jamais de troncature silencieuse;
- exclusion claire avec reason code si fichier trop gros, non supporté, absent, supprimé ou illisible;
- Frida ne doit jamais prétendre avoir lu un fichier non injecté;
- aucune injection par défaut lors de l'ouverture d'une conversation dans un répertoire.

## 9. OCR images, PDF et Markdown dérivé

Le chantier doit intégrer explicitement que l'OCR ne concerne pas seulement les PDF.

L'OCR doit aussi couvrir les images:

- captures d'écran;
- photos de pages;
- notes manuscrites;
- scans image.

Politique pressentie:

- OCR image manuel ou semi-manuel;
- pas d'OCR automatique sur toutes les images;
- bouton/action `Extraire le texte` sur une image;
- raison: manuscrit fréquent, OCR incertain, coût/bruit possible;
- l'OCR produit un fichier dérivé Markdown visible à côté de l'image source.

Contrat souhaité:

```text
photo-page-12.jpg
photo-page-12.ocr.md
```

Le fichier OCR dérivé:

- garde un lien de provenance vers l'image source;
- est visible dans le répertoire;
- est sélectionnable comme fichier texte;
- peut être ouvert par double-clic;
- s'ouvre dans une petite fenêtre ou un panneau UI;
- le texte est éditable;
- propose un bouton enregistrer;
- la sauvegarde met à jour le fichier Markdown et la référence DB.

L'OCR doit être marquée comme extraction imparfaite, surtout pour le manuscrit. Elle ne doit jamais être présentée comme vérité visuelle totale.

Lien avec l'existant:

- l'OCR PDF actuel est borné et synchrone pendant l'upload active document;
- le futur OCR de répertoire devra probablement produire un artefact durable `.ocr.md`;
- l'artefact Markdown dérivé peut ensuite suivre le chemin texte des documents actifs quand il est explicitement sélectionné.

## 10. Suppression et incohérences

Suppression fichier:

- suppression utilisateur = le fichier n'est plus accessible, plus sélectionnable, plus injectable, et les bytes physiques sont supprimés;
- supprimer les bytes physiques du serveur;
- faire disparaître le fichier des listings actifs;
- supprimer toute sélection active liée;
- empêcher toute sélection ou injection future;
- rendre le fichier non injectable après suppression, même si une ancienne référence existe encore;
- conserver éventuellement une tombstone DB content-free si c'est utile pour audit ou cohérence;
- ne jamais conserver une entrée active ambiguë;
- ne jamais stocker dans la tombstone de contenu brut, base64 ou chemin exposé à l'UI;
- gérer les erreurs DB/disque proprement;
- journaliser en logs content-free.

Test attendu plus tard:

```text
suppression fichier -> non listé, non sélectionnable, non injectable, bytes absents
```

Suppression répertoire:

- demander confirmation forte si le répertoire contient fichiers ou conversations;
- les fichiers peuvent être supprimés physiquement après confirmation;
- les conversations ne doivent pas être supprimées automatiquement;
- les conversations doivent plutôt repasser hors répertoire, sauf décision contraire explicite.

Cas d'incohérence à prévoir:

- DB présente, fichier absent;
- fichier présent, DB absente;
- DB supprimée, disque échoue;
- disque supprimé, DB échoue;
- fichier OCR dérivé présent mais source absente;
- source présente mais fichier OCR dérivé absent;
- conversation liée à un répertoire supprimé.

## 11. Non-contamination

Le chantier doit réaffirmer:

- pas de mémoire automatique;
- pas d'identity automatique;
- pas de résumé automatique;
- pas de Biblio automatique;
- pas de RAG documentaire par répertoire;
- pas de base64 image dans logs, read-models, historique ou dashboard;
- pas de contenu brut dans l'observabilité;
- pas d'injection silencieuse;
- pas de troncature silencieuse;
- pas de prompt de répertoire en V0;
- pas de mémoire/RAG par répertoire;
- pas de résumé conversationnel alimenté par les fichiers non sélectionnés;
- pas de promotion automatique d'un fichier OCR dérivé vers une connaissance durable.

## 12. Lots proposés

### Lot 0 - Audit/spec

- [x] Relire `app/core/active_conversation_documents.py`.
- [x] Relire `app/core/active_document_upload_service.py`.
- [x] Relire `app/core/active_document_prompt_lane.py`.
- [x] Relire `app/core/active_document_text_extraction.py`.
- [x] Relire `app/core/active_document_image_validation.py`.
- [x] Relire `app/core/active_document_ocr_client.py`.
- [x] Relire `app/core/conversations_service.py`, `app/core/conversations_store.py`, `app/core/conversations_maintenance.py`.
- [x] Relire `app/web/chat_threads_sidebar.js`, `app/web/chat_active_documents.js`, `app/web/app.js`, `app/web/index.html`, `app/web/styles.css`.
- [x] Relire `app/observability/active_documents_observability.py`.
- [x] Produire un contrat source-of-truth avant code: `app/docs/states/specs/workspace-folders-contract.md`.
- [x] Définir le modèle DB/disque.
- [x] Définir les reason codes.
- [x] Définir la stratégie de migration des conversations existantes hors répertoire.

Note Lot 0 livré le 2026-05-20: la spec `app/docs/states/specs/workspace-folders-contract.md` est créée comme source de vérité du chantier. Aucune implémentation runtime, DB, frontend, prompt ou provider n'a été faite.

### Lot 1 - Modèle répertoires + conversations

- [x] Ajouter tables/migrations pour les répertoires de travail.
- [x] Ajouter création de répertoire.
- [x] Ajouter renommage de répertoire.
- [x] Ajouter suppression de répertoire avec confirmation forte côté UI.
- [x] Ajouter ordre manuel des répertoires.
- [x] Ajouter `icon_key` allowlisté.
- [x] Ajouter description courte non injectée.
- [x] Ajouter déplacement conversations -> répertoire.
- [x] Ajouter sortie de conversation vers hors répertoire.
- [x] Préserver conversations existantes hors répertoire.
- [x] Garantir qu'une conversation appartient à zéro ou un répertoire en V0.
- [x] Tester suppression de répertoire sans suppression automatique des conversations.

Note Lot 1 livré le 2026-05-20: socle DB/API/UI minimal livré pour répertoires + rattachement conversation. Le déplacement V0 utilise un select par conversation; le glisser-déposer reste ouvert en Lot 5 / polish pour éviter de fragiliser la sidebar. Aucun fichier persistant, stockage disque, sélection multi-fichiers, OCR `.ocr.md` ou injection documentaire n'a été ouvert.

### Lot 2 - Stockage fichiers de répertoire

- [x] Ajouter upload de fichiers dans un répertoire.
- [x] Définir stockage physique serveur.
- [x] Créer références DB des fichiers.
- [x] Stocker nom logique, chemin interne, hash, taille, MIME, type, dates, répertoire.
- [x] Ajouter listing fichiers par répertoire.
- [x] Ajouter suppression DB + disque.
- [x] Ajouter garde incohérences DB/disque.
- [x] Refuser les types non supportés.
- [x] Ne pas exposer les chemins physiques à l'UI.
- [x] Journaliser content-free.

Note Lot 2 livré le 2026-05-20: stockage durable `workspace_files` livré avec DB + disque sous préfixe stable par identifiant de répertoire, routes `GET/POST/DELETE /api/workspace-folders/<folder_id>/files`, UI minimale de listing/upload/suppression et réutilisation des validateurs documents actifs. L'upload document actif de conversation reste inchangé et séparé. Aucun fichier de répertoire n'est sélectionné, injecté, lu par le modèle, mémorisé, résumé, ajouté à identity/Biblio ou OCRisé en `.ocr.md` dans ce lot. Correctif du même jour: la suppression de répertoire ne masque plus un échec partiel de suppression fichiers (`workspace_folder_file_delete_failed`) et l'observabilité content-free couvre upload succès/échec, delete succès/échec, listing `disk_missing` et résumé de suppression de répertoire, sans contenu brut, bytes, chemin disque, `storage_key`, base64, secret ou prompt.

### Lot 3 - Sélection/injection

- [x] Ajouter sélection multi-fichiers depuis un répertoire.
- [x] Garantir qu'aucun fichier n'est injecté par défaut.
- [x] Intégrer la sélection explicite au flux `active_document`.
- [x] Garder les fichiers non sélectionnés invisibles pour le modèle.
- [x] Conserver injection entière ou exclusion entière.
- [x] Conserver absence de troncature silencieuse.
- [x] Ajouter reason codes pour absent, supprimé, trop gros, non supporté, illisible.
- [x] Tester payload texte.
- [x] Tester payload image `text` puis `image_url`.
- [x] Tester non-contamination Memory/RAG/Identity/Summary/Biblio.

Note Lot 3 livré le 2026-05-20: sélection persistante `workspace_file_selections` livrée, conversation-scoped par `conversation_id + workspace_file_id`, avec routes `GET/POST/DELETE /api/conversations/<conversation_id>/workspace-file-selections`. Un fichier n'est jamais injecté par défaut: il devient lisible seulement s'il est coché dans la conversation courante, et cette sélection ne s'applique pas aux autres conversations du même répertoire. Au moment du prompt, les fichiers sélectionnés sont convertis en items compatibles avec la lane `active_document`, sans copie de contenu dans `conversation_messages`, mémoire, identity, summary, Biblio ou RAG. Les textes sont injectés en entier ou exclus en entier; les images suivent le payload multimodal `text` puis `image_url`; les exclusions utilisent des reason codes `workspace_*` (`workspace_file_deleted`, `workspace_file_disk_missing`, `workspace_file_too_large`, `workspace_file_type_unsupported`, `workspace_file_unreadable`, `workspace_file_ocr_required`, `workspace_file_model_unsupported`, `workspace_selection_stale`). L'observabilité reste content-free. Lot 4 OCR `.ocr.md` reste fermé.

### Lot 4 - OCR images/PDF et fichiers Markdown dérivés

- [ ] Définir action OCR manuelle ou semi-manuelle.
- [ ] Couvrir les images en plus des PDF.
- [ ] Garder l'OCR image hors automatique global.
- [ ] Produire un fichier `.ocr.md` dérivé.
- [ ] Stocker le lien de provenance vers le fichier source.
- [ ] Afficher le fichier Markdown dérivé à côté de la source.
- [ ] Rendre le `.ocr.md` sélectionnable comme fichier texte.
- [ ] Ouvrir le `.ocr.md` par double-clic dans une petite fenêtre ou un panneau.
- [ ] Permettre l'édition du texte OCR.
- [ ] Ajouter bouton enregistrer.
- [ ] Sauvegarder le Markdown et la référence DB.
- [ ] Signaler que l'OCR est imparfait, surtout manuscrit.
- [ ] Tester source image + dérivé Markdown + sélection explicite.

### Lot 5 - UI sidebar/polish

- [ ] Afficher les répertoires au-dessus des conversations hors répertoire.
- [ ] Ajouter ligne fine entre répertoires et conversations hors répertoire.
- [ ] Ajouter glisser-déposer des conversations dans un répertoire si faisable.
- [ ] Ajouter action de sortie d'un répertoire.
- [ ] Ajouter icônes allowlistées.
- [ ] Ajouter ordre manuel.
- [ ] Ajouter états vides.
- [ ] Ajouter états erreur/suppression.
- [ ] Préserver le comportement mobile/responsive si applicable.
- [ ] Prévoir le nommage automatique des conversations dans ce chantier ou un lot proche.

### Lot 6 - Tests et preuves finales

- [ ] Tests unitaires modèle DB répertoires.
- [ ] Tests serveur routes répertoires.
- [ ] Tests serveur routes fichiers.
- [ ] Tests sélection/injection active documents.
- [ ] Tests non-contamination.
- [ ] Tests suppression DB/disque.
- [ ] Tests incohérences DB/disque.
- [ ] Tests OCR PDF.
- [ ] Tests OCR image.
- [ ] Tests UI sidebar.
- [ ] Tests navigateur drag-and-drop si disponible.
- [ ] Preuve migration conversations existantes hors répertoire.
- [ ] Preuve absence base64 dans logs/read-models/historique.

## 13. Hors scope strict

Ne pas faire dans ce chantier initial:

- changement runtime;
- changement DB live hors migration versionnée du chantier;
- changement prompts globaux;
- changement du modèle principal;
- appel OpenRouter hors tests explicitement bornés du futur chantier;
- changement Docker;
- changement Caddy/Authelia;
- changement mémoire;
- changement identity;
- changement summary;
- démarrage Biblio;
- démarrage recherche web;
- RAG documentaire par répertoire;
- multi-utilisateur;
- upload de logo custom en V0;
- prompt de répertoire.

## 14. Risques à surveiller

- Complexité DB/disque: une suppression partielle ou une incohérence peut laisser des fichiers orphelins ou des lignes DB fantômes.
- Biblio déguisée: un répertoire de travail ne doit pas devenir un catalogue durable consulté automatiquement.
- Prompt de répertoire déguisé: la description courte ne doit pas gouverner la réponse.
- OCR manuscrit incertain: l'extraction doit rester éditable et marquée comme imparfaite.
- Suppression physique dangereuse: confirmation forte, logs content-free et stratégie d'échec sont obligatoires.
- Payload trop large: la sélection multi-fichiers peut exploser le prompt; il faut conserver sélection explicite, exclusion entière et reason codes.
- UI sidebar fragile: la sidebar porte déjà conversations, rename, delete, cache messages et mobile; éviter un patch monolithique.
