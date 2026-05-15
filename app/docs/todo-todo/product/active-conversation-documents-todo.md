# Documents actifs de conversation - TODO

Statut: actif
Date de creation: 2026-05-15
Classement: `app/docs/todo-todo/product/`
Audit-plan source: `app/docs/todo-todo/product/active-conversation-documents-audit-plan.md`
Spec fondatrice a creer: `app/docs/states/specs/active-conversation-documents-contract.md`
Portee: activation serveur de documents fournis a une conversation, injection entiere ou exclusion entiere par tour, frontend chat, observabilite content-free
Hors-scope du commit de creation: code runtime, endpoint, table DB, frontend, migration, OCR, RAG documentaire, stockage documentaire durable, rebuild

## 1. Intention

Ce TODO ouvre le chantier produit des documents actifs de conversation.

Le besoin n'est pas encore de construire une bibliotheque documentaire, un OCR ou un RAG documentaire. Le besoin est de permettre a l'utilisateur de fournir ponctuellement des fichiers a Frida dans une conversation et de garder ces fichiers actifs jusqu'a retrait manuel explicite.

Formats cibles du premier chantier:

- PDF deja textuels;
- DOCX;
- ODT;
- MD;
- TXT.

Regle centrale: un document actif est envoye entier au modele quand il rentre dans le payload du tour. S'il ne rentre pas entier, il est exclu entierement de ce tour, le tour continue, et Frida recoit un signal structure lui permettant de l'expliquer naturellement.

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
- Observabilite content-free par defaut.
- Contenu complet uniquement par action explicite compatible `Afficher le contenu complet`.
- Pas d'AnythingLLM ni OpenWebUI comme intermediaire principal de cette capacite.

## 3. Hors-scope du chantier

- OCR;
- documents scans;
- bibliotheque documentaire persistante;
- recherche documentaire durable;
- embeddings documentaires;
- chunking RAG documentaire;
- backfill historique;
- resume automatique des documents;
- modification de la doctrine Memory/RAG;
- modification de la doctrine Identity;
- stockage long terme de documents hors decision explicite;
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
- Memory/RAG/Identity/Summary ne sont pas contamines;
- le seuil de resume n'integre pas les documents actifs;
- les logs/read-models/dashboard montrent les metadonnees utiles sans contenu brut par defaut;
- le contenu complet, si disponible, passe par une action explicite;
- les tests prouvent les cas nominaux, trop gros, parsing error, retrait et non-contamination.

## 5. Condition de non-prolongation

Ne pas prolonger ce chantier vers OCR, RAG documentaire, bibliotheque persistante, recherche documentaire durable, indexation, chunking, stockage long terme ou ingestion multi-conversations.

La condition de non-prolongation est atteinte quand Frida sait lire ponctuellement des documents textuels fournis a une conversation, les garder actifs cote serveur jusqu'a retrait manuel, les injecter entierement quand possible, les exclure proprement quand ils sont trop gros, et prouver tout cela sans contaminer Memory/RAG/Identity/Summary.

Les capacites documentaires persistantes futures devront etre ouvertes dans un chantier separe.

## 6. Lots

### Lot 1 - Spec fondatrice et contrat de lanes

- [ ] Creer `app/docs/states/specs/active-conversation-documents-contract.md`.
- [ ] Fixer les formats supportes et l'absence d'OCR.
- [ ] Fixer le vocabulaire: document actif, activation, retrait manuel, injection entiere, exclusion entiere, lane documentaire, signal non injecte.
- [ ] Definir la frontiere stricte avec Memory/RAG/Identity/Summary.
- [ ] Definir la lane prompt structuree et ses balises stables.
- [ ] Definir les reason codes initiaux: `document_too_large_for_turn`, `document_parse_error`, `document_type_unsupported`, `document_runtime_unavailable`, `manual_remove`.
- [ ] Definir la doctrine content-free et le lien futur avec `Afficher le contenu complet`.

### Lot 2 - Etat actif serveur non memoire

- [ ] Choisir l'emplacement de code dedie apres relecture du depot.
- [ ] Creer le modele/service d'etat actif conversation-scoped.
- [ ] Persister metadonnees et texte extrait necessaire a la reinjection multi-tour, sans classer cette persistence comme memoire.
- [ ] Ajouter activation, liste, retrait/desactivation.
- [ ] Garantir que l'etat n'est pas reutilisable hors conversation.
- [ ] Definir retention et nettoyage minimal apres retrait ou suppression de conversation.
- [ ] Ajouter tests de deux tours successifs et retrait manuel.

### Lot 3 - Extraction texte des formats cibles

- [ ] Choisir les bibliotheques de parsing explicites pour PDF textuel, DOCX, ODT, MD, TXT.
- [ ] Ajouter fixtures compactes sans contenu sensible.
- [ ] Refuser ou marquer clairement les PDF scans / OCR requis.
- [ ] Normaliser le texte sans le resumer.
- [ ] Produire chars, bytes, token_estimate, hash court et status.
- [ ] Ne jamais presenter une extraction partielle comme complete.
- [ ] Tester succes, format non supporte, parse error et fichier vide.

### Lot 4 - Integration prompt entier ou rien

- [ ] Brancher les documents actifs apres la decision de resume et avant l'appel modele principal.
- [ ] Injecter une lane documentaire dediee avec balises stables.
- [ ] Calculer la decision entier ou exclu par tour.
- [ ] Ne jamais tronquer silencieusement.
- [ ] Ajouter le signal structure pour les documents actifs non injectes.
- [ ] Garder une politique stable quand plusieurs documents sont actifs.
- [ ] Tester document injecte entier, document trop gros exclu entier, tour non bloque.

### Lot 5 - Barriere Memory/RAG/Identity/Summary

- [ ] Prouver que les documents actifs ne creent pas de memory traces.
- [ ] Prouver qu'ils ne creent pas d'embeddings ni retrieval documentaire.
- [ ] Prouver qu'ils n'alimentent pas Identity.
- [ ] Prouver qu'ils ne sont pas stockes dans les summaries.
- [ ] Prouver qu'ils ne comptent pas dans le seuil de resume.
- [ ] Ajouter des tests anti-regression pour les chemins de contamination.

### Lot 6 - Frontend chat drag-and-drop et controle actif

- [ ] Ajouter drag-and-drop fichiers sur la surface chat.
- [ ] Ajouter controle visible pres des controles d'entree.
- [ ] Afficher les fichiers actifs avec nom, type, taille/statut et action retirer.
- [ ] Garder l'activation visible sur les tours suivants.
- [ ] Gerer erreurs de parsing/type/taille sans bloquer la saisie.
- [ ] Ne pas afficher le contenu du document dans l'UI par defaut.
- [ ] Tester desktop/mobile et absence de regression chat.

### Lot 7 - Observabilite, logs, read-models et dashboard

- [ ] Ajouter events compacts d'activation, retrait et decision par tour.
- [ ] Exposer par defaut seulement nom, type, bytes, chars, token_estimate, active, injected, reason_code, hashes courts ou refs.
- [ ] Ajouter le module observable `documents` reel sans dupliquer Memory/RAG.
- [ ] Enrichir l'inspection traduite du dashboard: document actif, injecte, non injecte car trop gros, erreur parsing, retrait manuel.
- [ ] Garder le contenu complet hors inspection ordinaire.
- [ ] Aligner l'acces volontaire futur avec le gate `Afficher le contenu complet` sans prechargement.
- [ ] Tester content-free strict et absence de contenu brut dans logs/read-models/dashboard.

### Lot 8 - Tests integration et preuves operateur

- [ ] Tester un document actif reinjecte sur deux tours successifs.
- [ ] Tester retrait manuel puis absence d'injection.
- [ ] Tester document trop gros: tour continue, document exclu, signal compact.
- [ ] Tester parse error: pas d'injection partielle.
- [ ] Tester absence de contamination Memory/RAG/Identity/Summary.
- [ ] Tester absence de contenu brut dans observabilite ordinaire.
- [ ] Tester comportement apres rechargement navigateur.
- [ ] Tester la preuve compacte dashboard/logs sans afficher le document.

### Lot 9 - Documentation de cloture et preparation future

- [ ] Mettre a jour les docs vivantes touchees par le comportement runtime.
- [ ] Documenter les limites restantes: pas OCR, pas RAG documentaire, pas bibliotheque persistante.
- [ ] Documenter la transition possible vers un futur systeme documentaire durable.
- [ ] Verifier que le TODO ne contient plus de case ouverte reelle.
- [ ] Archiver le TODO dans `app/docs/todo-done/product/` quand tous les lots sont fermes.

## 7. Tests attendus par le chantier

Les lots devront adapter les suites exactes au code courant, mais viser:

- tests unitaires du store/service d'etat actif;
- tests d'extraction par format;
- tests de decision budget entier ou exclu;
- tests du prompt pour lane documentaire et signal compact;
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
- Le contenu complet ne doit jamais etre precharge dans le DOM ou dans l'inspection ordinaire.
- Les recouvrements futurs avec le module dashboard `documents` doivent etre explicites, pas confus.
