# Documents actifs de conversation - TODO

Statut: clos / archive
Date de creation: 2026-05-15
Date de cloture: 2026-05-16
Classement: `app/docs/todo-done/product/`
Audit-plan source: `app/docs/todo-done/product/active-conversation-documents-audit-plan.md`
Spec fondatrice: `app/docs/states/specs/active-conversation-documents-contract.md`
Chantier distinct reserve: `app/docs/todo-todo/product/frida-biblio-native-catalogue-todo.md`
Portee: activation serveur de documents fournis a une conversation, injection entiere ou exclusion entiere par tour, frontend chat, observabilite content-free
Hors-scope initial conserve: OCR, RAG documentaire, stockage documentaire durable, Biblio native, ouverture automatique du texte complet dans le dashboard

Note de cloture 2026-05-16: le chantier documents actifs de conversation est livre et archive. Les documents actifs sont temporaires, conversation-scoped, actifs jusqu'au retrait manuel, injectes entiers ou exclus entiers par tour, visibles dans l'UI chat et l'observabilite content-free, et verrouilles hors Memory/RAG/Identity/Summary. La Biblio native / Frida Catalogue reste un chantier separe actif, non lance runtime par cette cloture.

Note post-cloture 2026-05-17: l'OCR V1 bornee des PDF scannes a ensuite ete livree dans le mini-chantier archive `app/docs/todo-done/product/active-conversation-documents-ocr-todo.md`. Les lignes qui excluent l'OCR ci-dessous decrivent le perimetre du chantier initial, pas l'etat runtime courant.

Note post-cloture 2026-05-17 bis: le prompt des documents actifs a ete resserre sans rouvrir le chantier. Le contrat d'interpretation reste en `system`, mais le contenu complet fourni par l'utilisateur est transporte dans un message `user` separe et encadre comme contenu non autoritaire. La lecture runtime distingue aussi `ok`, `empty` et `error`, afin qu'une erreur de lecture ne soit plus confondue avec l'absence de document.

## 1. Intention

Ce TODO ouvre le chantier produit des documents actifs de conversation.

Le besoin initial n'etait pas de construire une bibliotheque documentaire, un chantier OCR ou un RAG documentaire. Le besoin etait de permettre a l'utilisateur de fournir ponctuellement des fichiers a Frida dans une conversation et de garder ces fichiers actifs jusqu'a retrait manuel explicite.

Decision produit issue de l'audit complementaire du 2026-05-16: ce chantier reste separe de la future Biblio native / Frida Catalogue.

Vocabulaire a reserver:

- `document actif de conversation` / `active_document`: fichier temporaire fourni volontairement par l'utilisateur dans la conversation courante;
- `document de bibliotheque` / `library_document` / `catalogue_document`: document persistant consulte plus tard via Biblio / Frida Catalogue;
- `passage documentaire`: extrait borne issu d'un `library_document` / `catalogue_document`.

Le chantier courant ne cree pas de Biblio. Il doit seulement eviter de fermer cette porte et eviter tout vocabulaire ou controle UI generique `Documents` qui melangerait upload temporaire et bibliotheque persistante.

Formats cibles du premier chantier:

- PDF deja textuels;
- DOCX;
- ODT;
- MD;
- TXT.

Regle centrale: un document actif est envoye entier au modele quand il rentre dans le payload du tour. S'il ne rentre pas entier, il est exclu entierement de ce tour, le tour continue, et Frida recoit un signal structure lui permettant de l'expliquer naturellement.

Regle semantique centrale: le modele ne doit pas seulement recevoir les octets du document. Il doit recevoir, dans le prompt principal, un contrat explicite lui permettant de comprendre que cette lane est un **document actif de conversation**: un document temporaire fourni volontairement par l'utilisateur, actif dans la conversation courante, et utilisable comme contexte de travail direct du tour tant qu'il reste actif et injecte.

## 2. Doctrine produit

- Aucune troncature silencieuse.
- Aucun blocage du tour quand un document actif est trop gros.
- Etat actif cote serveur, pas seulement dans le navigateur.
- Etat actif dedie, non memoire.
- Pas d'indexation.
- Pas de resume documentaire.
- Pas de promotion Memory/RAG.
- Pas d'alimentation Identity.
- Pas de reutilisation hors conversation active.
- Retrait manuel explicite par l'utilisateur.
- Exclusion explicite du seuil de resume de conversation.
- Lane documentaire bornee dans le prompt principal.
- Contrat d'interpretation prompt obligatoire pour la lane document actif de conversation.
- Le prompt principal doit expliquer que le document est fourni volontairement par l'utilisateur, actif dans la conversation courante et distinct de Memory/RAG, du resume, d'Identity et du Web.
- Quand l'utilisateur demande de travailler "sur le document", le modele doit interpreter cette demande a partir de la lane documentaire active injectee.
- Si un document actif n'est pas injecte sur un tour parce qu'il est trop gros, indisponible ou en erreur de parsing, le modele doit recevoir un signal explicite et ne jamais pretendre l'avoir lu.
- Observabilite content-free par defaut.
- Pas de promesse actuelle d'ouverture du texte complet du document dans le dashboard.
- Toute ouverture future du texte complet du document exige une decision produit separee; elle n'est pas une consequence automatique du gate dashboard existant.
- Pas d'AnythingLLM ni OpenWebUI comme intermediaire principal de cette capacite.
- Le chantier documents actifs ne cree pas de Biblio native.
- L'etat actif serveur temporaire ne doit jamais devenir le stockage de la bibliotheque persistante.
- La lane `documents actifs` est reservee aux fichiers fournis par l'utilisateur.
- La future lane `Biblio / Catalogue` est reservee aux passages recuperes a la demande depuis une bibliotheque persistante.
- L'observabilite documents actifs reste separee de l'observabilite Biblio:
  - documents actifs: actif, injecte, retire, trop gros, parsing error;
  - Biblio: requete, document resolu, locator, passage extrait, ambiguite, confiance.

## 3. Hors-scope du chantier

- OCR dans le chantier initial; extension V1 bornee livree ensuite separement;
- documents scans dans le chantier initial; certains PDF scannes sont desormais pris en charge par l'extension OCR V1 bornee;
- bibliotheque documentaire persistante;
- Biblio native / Frida Catalogue;
- recherche documentaire durable;
- embeddings documentaires;
- chunking RAG documentaire;
- backfill historique;
- resume automatique des documents;
- modification de la doctrine Memory/RAG;
- modification de la doctrine Identity;
- stockage long terme de documents hors decision explicite;
- stockage Catalogue ou `library_document` dans l'etat `active_document`;
- bouton ou vocabulaire generique `Documents` qui confondrait upload temporaire et bibliotheque persistante;
- exposition de contenu brut dans logs ou dashboard par defaut.

## 4. Criteres de fermeture du chantier

Le chantier pourra etre clos seulement si:

- une spec fondatrice active existe;
- les fichiers cibles textuels peuvent etre actives depuis le chat;
- l'etat actif est serveur, conversation-scoped et distinct de la memoire;
- un document actif reste injecte sur deux tours successifs tant qu'il est actif;
- le retrait manuel le rend absent des tours suivants;
- l'injection est entiere ou absente, jamais tronquee silencieusement;
- le document trop gros n'empeche pas le tour et produit un signal compact;
- le prompt principal enseigne explicitement au modele le statut de document actif de conversation et son usage attendu;
- les tests prouvent que le modele recoit cette instruction d'interpretation, pas seulement le contenu du document;
- le vocabulaire `active_document` est distingue de `library_document` / `catalogue_document` / `passage documentaire`;
- la future lane Biblio / Catalogue est reservee sans etre implementee dans ce chantier;
- Memory/RAG/Identity/Summary ne sont pas contamines;
- le seuil de resume n'integre pas les documents actifs;
- les logs/read-models/dashboard montrent les metadonnees utiles sans contenu brut par defaut;
- l'inspection dashboard montre metadonnees et statut d'injection, pas le texte complet du document;
- les tests prouvent les cas nominaux, trop gros, parsing error, retrait et non-contamination.

## 5. Condition de non-prolongation

Ne pas prolonger ce chantier initial vers RAG documentaire, bibliotheque persistante, recherche documentaire durable, indexation, chunking, stockage long terme ou ingestion multi-conversations. L'OCR V1 bornee a ete traitee ensuite comme mini-chantier separe, sans Biblio.

La condition de non-prolongation est atteinte quand Frida sait lire ponctuellement des documents textuels fournis a une conversation, les garder actifs cote serveur jusqu'a retrait manuel, les injecter entierement quand possible, les exclure proprement quand ils sont trop gros, et prouver tout cela sans contaminer Memory/RAG/Identity/Summary.

Les capacites documentaires persistantes futures devront etre ouvertes dans un chantier separe.

Ce chantier separe est desormais ouvert comme cadrage produit sous `app/docs/todo-todo/product/frida-biblio-native-catalogue-todo.md`, mais il ne doit pas etre execute par les lots documents actifs.

## 6. Lots

### Lot 1 - Spec fondatrice et contrat de lanes

- [x] Creer `app/docs/states/specs/active-conversation-documents-contract.md`.
- [x] Fixer les formats supportes et l'absence d'OCR dans le chantier initial.
- [x] Fixer le vocabulaire: document actif, activation, retrait manuel, injection entiere, exclusion entiere, lane documentaire, signal non injecte.
- [x] Fixer explicitement `document actif de conversation` / `active_document` et le distinguer des futurs `library_document` / `catalogue_document` / `passage documentaire`.
- [x] Definir la frontiere stricte avec Memory/RAG/Identity/Summary.
- [x] Definir la frontiere stricte avec la future Biblio native / Frida Catalogue.
- [x] Definir la lane prompt structuree et ses balises stables.
- [x] Reserver une future lane Biblio / Catalogue sans l'implementer dans ce chantier.
- [x] Definir le contrat d'interpretation prompt: document actif de conversation, fourni volontairement par l'utilisateur, contexte de travail direct du tour courant.
- [x] Definir les instructions que le prompt principal devra donner au modele pour distinguer cette lane de Memory/RAG, du resume, d'Identity, du Web et de l'hermeneutique.
- [x] Definir la semantique du signal "document actif non injecte": le modele sait qu'un document existe mais ne doit pas pretendre l'avoir lu.
- [x] Definir les reason codes initiaux: `document_too_large_for_turn`, `document_parse_error`, `document_type_unsupported`, `document_runtime_unavailable`, `manual_remove`.
- [x] Definir la doctrine content-free et interdire de transformer automatiquement le gate dashboard existant en acces au texte complet du document.

### Lot 2 - Etat actif serveur non memoire

- [x] Choisir l'emplacement de code dedie apres relecture du depot.
- [x] Creer le modele/service d'etat actif conversation-scoped.
- [x] Persister metadonnees et texte extrait necessaire a la reinjection multi-tour, sans classer cette persistence comme memoire.
- [x] Ajouter activation, liste, retrait/desactivation.
- [x] Garantir que l'etat n'est pas reutilisable hors conversation.
- [x] Definir retention et nettoyage minimal apres retrait ou suppression de conversation.
- [x] Ajouter tests de deux tours successifs et retrait manuel.

Note Lot 2 livre le service `app/core/active_conversation_documents.py`, la table dediee `active_conversation_documents` et son initialisation au demarrage serveur. Il ne branche pas encore endpoint, parsing, frontend, lane prompt ni observabilite; ces points restent dans les lots suivants.

### Lot 3 - Extraction texte des formats cibles

- [x] Choisir les bibliotheques de parsing explicites pour PDF textuel, DOCX, ODT, MD, TXT.
- [x] Ajouter fixtures compactes sans contenu sensible.
- [x] Refuser ou marquer clairement les PDF scans / OCR requis.
- [x] Normaliser le texte sans le resumer.
- [x] Produire chars, bytes, token_estimate, hash court et status.
- [x] Ne jamais presenter une extraction partielle comme complete.
- [x] Tester succes, format non supporte, parse error et fichier vide.

Note Lot 3 livre `app/core/active_document_text_extraction.py`. Il utilise `pypdf` pour les PDF textuels et la bibliotheque standard pour TXT/MD/DOCX/ODT. Il ne branche pas encore activation frontend, endpoint, lane prompt ni observabilite.

### Lot 4 - Integration prompt entier ou rien

- [x] Brancher les documents actifs apres la decision de resume et avant l'appel modele principal.
- [x] Injecter une lane documentaire dediee avec balises stables.
- [x] Ajouter au prompt principal le contrat d'interpretation de cette lane; ne pas se contenter d'injecter un bloc documentaire.
- [x] Enseigner explicitement au modele qu'un document actif de conversation est fourni volontairement par l'utilisateur et sert de contexte de travail direct quand il est injecte.
- [x] Enseigner explicitement que cette lane n'est ni un souvenir, ni un resume, ni un contexte web, ni une identite.
- [x] Calculer la decision entier ou exclu par tour.
- [x] Ne jamais tronquer silencieusement.
- [x] Ajouter le signal structure pour les documents actifs non injectes.
- [x] Garantir que le signal non injecte indique au modele de ne pas pretendre avoir lu le document.
- [x] Garder une politique stable quand plusieurs documents sont actifs.
- [x] Tester document injecte entier, document trop gros exclu entier, tour non bloque et instruction d'interpretation bien presente dans le prompt final.

Note Lot 4 livre `app/core/active_document_prompt_lane.py` et branche la lane dans `chat_service`, apres `conv_store.build_prompt_messages()` et apres l'injection Web eventuelle, juste avant l'appel au modele principal. La decision entier ou absent porte sur le prompt courant du tour. `ACTIVE_DOCUMENT_PROMPT_MAX_TOKENS` est une limite documentaire dure optionnelle, desactivee par defaut (`0`) et distincte du soft limit d'observabilite `FRIDA_MAX_TOKENS`; elle ne coupe jamais le dialogue recent non resume. Il ne branche pas encore frontend, endpoint produit, observabilite, dashboard ni anti-contamination complete du Lot 5.

### Lot 5 - Barriere Memory/RAG/Identity/Summary

- [x] Prouver que les documents actifs ne creent pas de memory traces.
- [x] Prouver qu'ils ne creent pas d'embeddings ni retrieval documentaire.
- [x] Prouver qu'ils n'alimentent pas Identity.
- [x] Prouver qu'ils ne sont pas stockes dans les summaries.
- [x] Prouver qu'ils ne comptent pas dans le seuil de resume.
- [x] Ajouter des tests anti-regression pour les chemins de contamination.

Note Lot 5 livre `app/tests/unit/core/test_active_document_non_contamination_lot5.py`. Le test prouve que la lane documentaire peut etre presente dans le payload LLM, mais qu'elle ne rejoint ni `save_new_traces(conversation)`, ni le couple Identity, ni la requete Memory/RAG, ni le seuil/texte de summary. Aucun runtime n'est modifie dans ce lot.

### Lot 6 - Frontend chat drag-and-drop et controle actif

- [x] Ajouter drag-and-drop fichiers sur la surface chat.
- [x] Ajouter controle visible pres des controles d'entree.
- [x] Afficher les fichiers actifs avec nom, type, taille/statut et action retirer.
- [x] Eviter un libelle ou bouton generique `Documents` qui melangerait documents actifs et future Biblio.
- [x] Garder l'activation visible sur les tours suivants.
- [x] Gerer erreurs de parsing/type/taille sans bloquer la saisie.
- [x] Ne pas afficher le contenu du document dans l'UI par defaut.
- [x] Tester desktop/mobile et absence de regression chat.

Note Lot 6 livre les routes produit `GET/POST/DELETE /api/conversations/<conversation_id>/active-documents`, le module frontend `app/web/chat_active_documents.js` et son integration dans le chat. Le controle parle de documents actifs de conversation, pas de Biblio; l'UI affiche uniquement metadonnees/statuts, jamais le texte du fichier.

Correction ciblee avant Lot 7: les decisions de lane prompt sont maintenant persistees dans l'etat actif court terme via `last_injected_turn_id`, `last_excluded_turn_id` et `last_excluded_reason_code`. L'UI peut donc relire apres un tour qu'un document actif a ete injecte ou exclu pour `document_too_large_for_turn`. La route d'upload mesure et expose `byte_size`, valide type/extension/parsing, mais n'impose pas de plafond arbitraire de taille brute upload dans ce chantier; la taille qui bloque un tour reste la limite documentaire explicite `ACTIVE_DOCUMENT_PROMPT_MAX_TOKENS` quand elle est configuree.

### Lot 7 - Observabilite, logs, read-models et dashboard

- [x] Ajouter events compacts d'activation, retrait et decision par tour.
- [x] Exposer par defaut seulement nom, type, bytes, chars, token_estimate, active, injected, reason_code, hashes courts ou refs.
- [x] Ajouter le module observable `documents` reel sans dupliquer Memory/RAG.
- [x] Garder une observabilite separee de la future Biblio: actif/injecte/retire/trop gros cote documents actifs, requete/document/locator/passage/ambiguite/confiance cote Biblio future.
- [x] Enrichir l'inspection traduite du dashboard par tour: document actif, injecte, non injecte car trop gros.
- [x] Garder `activation_failed` et `manual_remove` visibles dans les logs admin compacts hors tour, sans les rattacher artificiellement a un tour.
- [x] Limiter l'inspection exhaustive documentaire aux metadonnees, statuts d'injection et raisons compactes.
- [x] Documenter que tout acces futur au texte complet du document releve d'une decision produit separee.
- [x] Tester content-free strict et absence de contenu brut dans logs/read-models/dashboard.

Note Lot 7 livre `app/observability/active_documents_observability.py`, l'event de tour `active_documents`, les events admin hors tour `active_document_activated`, `active_document_activation_failed` et `active_document_removed`, la colonne persistante `dashboard_turn_facts.documents_json`, le module observable initial `documents`, et le recit dashboard content-free des documents actifs injectes ou exclus pendant un tour. La lecture de tour reste strictement metadonnees/statuts/raisons compactes; aucun texte de fichier n'est charge dans les logs/read-models/dashboard ordinaires. Les echecs d'activation et retraits manuels restent prouvables dans les logs admin compacts, pas dans l'inspection de tour tant qu'il n'existe pas de read-model hors-tour dedie. La future Biblio reste separee.

### Lot 8 - Tests integration et preuves operateur

- [x] Tester un document actif reinjecte sur deux tours successifs.
- [x] Tester retrait manuel puis absence d'injection.
- [x] Tester document trop gros: tour continue, document exclu, signal compact.
- [x] Tester parse error: pas d'injection partielle.
- [x] Tester absence de contamination Memory/RAG/Identity/Summary.
- [x] Tester absence de contenu brut dans observabilite ordinaire.
- [x] Tester comportement apres rechargement navigateur.
- [x] Tester la preuve compacte dashboard/logs sans afficher le document.

Note Lot 8 ajoute les preuves operateur bout-en-bout sans nouvelle fonctionnalite produit:

- `app/tests/unit/core/test_active_document_operator_proofs_lot8.py` prouve la reinjection sur deux tours, le retrait manuel suivi d'absence d'injection, et le cas trop gros avec tour qui continue, document exclu entier et event compact content-free.
- `app/tests/test_server_active_documents_contract.py` prouve aussi qu'un parse error ne cree aucune activation et ne renvoie aucun texte partiel.
- Les suites Lot 5, Lot 7, dashboard et browser prouvent respectivement la non-contamination Memory/RAG/Identity/Summary, l'observabilite content-free, la materialisation dashboard content-free, et la persistance visible apres reload navigateur.

### Lot 9 - Documentation de cloture et preparation future

- [x] Mettre a jour les docs vivantes touchees par le comportement runtime.
- [x] Documenter les limites restantes: pas OCR, pas RAG documentaire, pas bibliotheque persistante.
- [x] Documenter la transition possible vers un futur systeme documentaire durable.
- [x] Verifier que la transition mentionne la Biblio native comme chantier separe, pas comme prolongement automatique.
- [x] Verifier que le TODO ne contient plus de case ouverte reelle.
- [x] Archiver le TODO dans `app/docs/todo-done/product/` quand tous les lots sont fermes.

Note Lot 9 livre la cloture documentaire: README racine, hub docs, AGENTS, spec vivante, cartographie runtime et references Biblio sont alignes sur l'etat livre. Le chantier est archive sans lancer OCR, RAG documentaire, bibliotheque persistante ni Biblio native.

## 7. Tests attendus par le chantier

Les lots devront adapter les suites exactes au code courant, mais viser:

- tests unitaires du store/service d'etat actif;
- tests d'extraction par format;
- tests de decision budget entier ou exclu;
- tests du prompt pour lane documentaire, contrat d'interpretation modele et signal compact;
- tests prouvant que la lane document actif de conversation est distinguee de Memory/RAG, du resume, d'Identity et du Web;
- tests anti-contamination Memory/RAG/Identity/Summary;
- tests frontend chat drag-and-drop et retrait;
- tests observabilite/dashboard content-free;
- tests integration deux tours successifs;
- tests de non-regression du chat existant.

## 8. Notes d'implementation a revalider a chaque lot

- Le bon emplacement code doit etre revalide avant patch; `app/core/active_conversation_documents.py` est une hypothese, pas une obligation.
- La persistence courte d'etat actif ne doit pas etre appelee memoire.
- Les dependances de parsing ne sont pas encore presentes dans `app/requirements.txt`.
- Les budgets tokens doivent etre alignes avec le provider reel et les settings runtime.
- Le texte complet du document n'est pas promis par le dashboard; ne pas le precharger ni l'exposer sans decision produit separee.
- Les recouvrements futurs avec le module dashboard `documents` doivent etre explicites, pas confus.
- Les recouvrements futurs avec Biblio native doivent rester vocabulairement nets: `active_document` temporaire d'un cote, `library_document` / `catalogue_document` et `passage documentaire` de l'autre.
