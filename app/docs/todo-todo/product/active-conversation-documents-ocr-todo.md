# Documents actifs de conversation - OCR TODO

Statut: actif
Date de creation: 2026-05-17
Classement: `app/docs/todo-todo/product/`
Spec source: `app/docs/states/specs/active-conversation-documents-contract.md`
Chantier parent archive: `app/docs/todo-done/product/active-conversation-documents-todo.md`
Chantier distinct a ne pas demarrer ici: `app/docs/todo-todo/product/frida-biblio-native-catalogue-todo.md`
Portee: extension OCR bornee des `active_document` PDF scannes, sans Biblio, sans RAG documentaire, sans ingestion persistante
Hors-scope du commit de creation: runtime, endpoint, frontend, changement plateforme, n8n, doc-pipeline nominal, Biblio, image multimodale, rebuild

## 1. Verdict de plan

Existe-t-il un meilleur plan ?

Non pour ce cycle docs-only. La preuve technique prealable a valide la chaine:

```text
document_ocr_required -> Stirling OCR -> PDF OCRise -> extracteur FridaDev -> complete
```

Le bon plan est donc de creer un mini-chantier actif, strictement borne, qui prolonge `active_document` sans rouvrir le chantier archive des documents actifs et sans commencer la Biblio native.

Ce TODO n'est pas un audit-plan. Il transforme l'arbitrage deja fait en feuille de route executable.

## 2. Intention produit

Le besoin est d'accepter, pour les documents actifs de conversation, certains PDF scannes qui sont aujourd'hui refuses avec:

- status `ocr_required`;
- reason `document_ocr_required`.

Apres OCR, si et seulement si le texte devient extractible de facon complete par l'extracteur FridaDev existant, le document rejoint le flux normal `active_document`.

Une fois actif, un document OCRise est traite exactement comme un autre document actif:

- temporaire;
- conversation-scoped;
- fourni volontairement par l'utilisateur;
- retire manuellement;
- injecte entier ou exclu entier par tour;
- hors Memory/RAG/Identity/Summary;
- hors Biblio.

## 3. Frontieres non negociables

Ce chantier couvre seulement:

- OCR de PDF scannes pour `active_document`;
- extraction texte finale via l'extracteur FridaDev existant;
- activation serveur du document seulement si le resultat final est `complete`;
- UI et observabilite content-free de l'etape OCR.

Ce chantier ne couvre pas:

- images multimodales generales;
- interpretation visuelle d'images;
- Biblio native;
- `library_document`;
- `catalogue_document`;
- `passage documentaire`;
- stockage documentaire durable;
- ingestion Catalogue;
- RAG documentaire;
- chunking documentaire;
- indexation;
- n8n dans le chemin nominal;
- doc-pipeline dans le chemin nominal V1.

Le chemin nominal V1 est:

```text
FridaDev active_document upload -> client OCR Stirling -> PDF OCRise -> extracteur FridaDev -> active_document
```

## 4. Architecture V1 retenue

Decision:

- `active_document` reste maitre du flux;
- l'OCR n'est appelee que lorsque l'extracteur actuel conclut `ocr_required`;
- les PDF deja textuels ne sont jamais OCRises;
- V1 utilise un client borne FridaDev vers `platform-stirling-pdf`;
- Stirling renvoie un PDF OCRise;
- FridaDev repasse toujours ce PDF OCRise dans `app/core/active_document_text_extraction.py`;
- seul un resultat final `complete` peut activer le document;
- si le resultat final reste non-complete, le document reste non actif avec reason compact;
- le texte OCR brut n'est jamais renvoye a l'UI ordinaire;
- aucune ecriture Catalogue ou doc-pipeline n'est faite.

Preuve technique prealable, faite le 2026-05-17:

- avant OCR: l'extracteur FridaDev a classe un PDF image-only en `ocr_required` / `document_ocr_required`;
- Stirling a repondu `200` avec `content-type=application/pdf`;
- le PDF OCRise repasse dans l'extracteur FridaDev avec `status=complete`;
- les artefacts temporaires de preuve ont ete supprimes.

## 5. Parametres operateur fixes pour la V1

Valeurs cible a graver dans la spec et la config runtime:

- timeout OCR maximal: `180` secondes;
- langues OCR par defaut: `fra+eng+deu`;
- plafond V1: `25 pages` maximum;
- plafond V1: `25 Mo` maximum;
- moteur V1: `Stirling PDF` via `platform-stirling-pdf`;
- OCR synchrone bornee pendant l'upload.

Au-dela de `25 pages` ou `25 Mo`, le document doit etre refuse pour ce chantier avec un motif clair. A cette echelle, le besoin releve plutot du futur chantier Biblio / Catalogue, pas du document actif ponctuel.

Les valeurs ci-dessus ne doivent pas etre confondues avec:

- `ACTIVE_DOCUMENT_PROMPT_MAX_TOKENS`, qui decide l'admission du document dans le prompt par tour;
- `FRIDA_MAX_TOKENS`, qui reste un soft limit d'observabilite du prompt complet;
- les limites futures Biblio.

## 6. Reason codes et libelles attendus

Reason codes runtime a stabiliser:

- `document_ocr_failed`;
- `document_ocr_timeout`;
- `document_ocr_empty`;
- `document_ocr_too_large`;
- `document_ocr_too_many_pages`.

La regle de cloture OCR reste:

```text
Si, apres OCR, l'extracteur final ne rend pas complete, le document ne devient pas actif.
```

Libelles UI attendus, a formuler sobrement:

- OCR impossible;
- OCR trop long;
- OCR sans texte lisible;
- PDF trop volumineux pour l'OCR de conversation;
- PDF trop long pour l'OCR de conversation.

Ne pas exposer les reason codes bruts comme lecture principale utilisateur.

## 7. UI attendue

Pendant l'OCR:

- progression tres discrete mais claire;
- pas de faux pourcentage si aucune vraie progression n'est disponible;
- indication du type `OCR en cours` ou equivalent;
- saisie du chat non bloquee durablement au-dela du traitement upload courant.

Apres succes:

- le document apparait actif comme les autres documents actifs;
- l'UI indique discretement qu'il est OCRise;
- aucun texte OCR n'est affiche par defaut.

Apres echec ou refus:

- le document reste non actif;
- le motif humain est visible;
- le chat reste utilisable.

## 8. Observabilite cible

Observabilite content-free minimale:

- `ocr_applied`;
- `ocr_engine`;
- `ocr_languages`;
- `ocr_duration_ms`;
- statut final;
- reason code compact;
- bytes source;
- pages detectees si disponible;
- raw content absent.

Le texte OCR brut ne doit pas apparaitre par defaut dans:

- logs ordinaires;
- read-models;
- dashboard;
- UI chat;
- events admin compacts.

La future Biblio garde son observabilite separee: requete, document resolu, locator, passage extrait, ambiguite, confiance.

## 9. Dashboard

Une petite surface dashboard peut etre incluse seulement si elle reste proportionnee au mini-chantier:

- compter OCR reussies vs echouees;
- afficher une serie compacte ou une petite courbe si les buckets existants le rendent naturel;
- raconter les motifs d'echec/refus en francais simple;
- ne jamais afficher le texte OCR brut.

Si cette partie fait gonfler le chantier ou demande une nouvelle projection large, elle doit etre repoussee explicitement a un lot ulterieur plutot que promise vaguement.

## 10. Lots

### Lot 1 - Spec OCR active documents

- [ ] Mettre a jour `app/docs/states/specs/active-conversation-documents-contract.md`.
- [ ] Graver que l'OCR est maintenant une extension bornee de `active_document`, pas Biblio.
- [ ] Graver le chemin V1: `ocr_required` -> `Stirling` -> PDF OCRise -> extracteur FridaDev -> `complete`.
- [ ] Graver les limites: `180` secondes, `fra+eng+deu`, `25 pages`, `25 Mo`.
- [ ] Graver les reason codes OCR.
- [ ] Graver la doctrine content-free de l'OCR.

### Lot 2 - Client OCR Stirling et configuration

- [ ] Choisir l'emplacement code exact apres relecture.
- [ ] Ajouter un client borne vers `platform-stirling-pdf`.
- [ ] Ajouter config URL interne, timeout, langues, page limit et byte limit.
- [ ] Detecter le nombre de pages avant OCR.
- [ ] Refuser `document_ocr_too_large` et `document_ocr_too_many_pages` avant appel OCR.
- [ ] Tester health/unavailable, timeout, erreur HTTP et retour non-PDF.

### Lot 3 - Integration upload OCR

- [ ] Brancher l'OCR seulement quand l'extraction initiale retourne `document_ocr_required`.
- [ ] Ne jamais OCRiser les PDF deja textuels.
- [ ] Repasser le PDF OCRise dans l'extracteur FridaDev.
- [ ] Activer seulement si le resultat final est `complete`.
- [ ] Refuser avec reason compact si le resultat final est vide, erreur ou non-complete.
- [ ] Garantir que le texte OCR ne fuit pas dans la reponse upload.
- [ ] Tester succes OCR, echec OCR, timeout, vide, trop gros, trop de pages.

### Lot 4 - UI et etats utilisateur

- [ ] Afficher un etat discret pendant l'OCR.
- [ ] Ne pas afficher de faux pourcentage.
- [ ] Afficher qu'un document actif est OCRise apres succes.
- [ ] Afficher un motif humain simple apres echec/refus.
- [ ] Garder le libelle `documents actifs de conversation`, sans bouton generique `Documents`.
- [ ] Tester desktop/mobile et absence de contenu brut.

### Lot 5 - Observabilite et dashboard proportionne

- [ ] Ajouter events compacts OCR content-free.
- [ ] Exposer `ocr_applied`, `ocr_engine`, `ocr_languages`, `ocr_duration_ms`, statut et reason code.
- [ ] Alimenter le module observable `documents` sans dupliquer Memory/RAG.
- [ ] Ajouter une lecture dashboard seulement si elle reste petite et naturelle.
- [ ] Tester OCR succes/echec dans logs/read-models/dashboard sans texte brut.

### Lot 6 - Tests et preuves bout-en-bout

- [ ] Tester PDF scanne non sensible -> OCR -> activation.
- [ ] Tester PDF deja textuel -> pas d'OCR.
- [ ] Tester PDF scanne trop gros / trop long -> non actif avec motif.
- [ ] Tester OCR timeout / erreur Stirling -> non actif avec motif.
- [ ] Tester OCR vide -> non actif avec motif.
- [ ] Tester que le document OCRise actif est ensuite injecte entier ou exclu entier par tour comme les autres `active_document`.
- [ ] Tester non-contamination Memory/RAG/Identity/Summary.
- [ ] Tester absence de n8n et de doc-pipeline dans le chemin nominal.

### Lot 7 - Documentation de cloture

- [ ] Mettre a jour docs vivantes touchees.
- [ ] Documenter les limites restantes: qualite OCR, documents volumineux, Biblio separee.
- [ ] Verifier qu'aucune case ouverte reelle ne reste.
- [ ] Archiver ce TODO dans `app/docs/todo-done/product/` quand tous les lots sont fermes.

## 11. Criteres de fermeture

Le chantier pourra etre clos seulement si:

- un PDF scanne non sensible peut devenir un `active_document` apres OCR;
- l'OCR n'est appelee que sur `document_ocr_required`;
- un PDF textuel ne passe pas par l'OCR;
- les limites `180`, `fra+eng+deu`, `25 pages`, `25 Mo` sont configurables ou gravees selon la spec;
- les reason codes OCR sont testes;
- l'UI raconte clairement succes/echec/refus sans contenu brut;
- l'observabilite prouve l'OCR sans texte OCR brut;
- le document OCRise respecte la regle entier ou absent;
- Memory/RAG/Identity/Summary restent non contamines;
- Biblio, n8n et doc-pipeline restent hors chemin nominal.

## 12. Condition de non-prolongation

Ne pas prolonger ce chantier vers:

- Biblio native;
- `library_document`;
- `catalogue_document`;
- `passage documentaire`;
- OCR de masse;
- OCR asynchrone long courrier;
- ingestion Nextcloud;
- doc-pipeline nominal;
- n8n nominal;
- RAG documentaire;
- image multimodale generale;
- stockage durable inter-conversations.

Si un document depasse l'echelle `25 pages` / `25 Mo` ou demande une structuration documentaire durable, il doit etre renvoye vers le futur chantier Biblio / Catalogue, pas force dans `active_document`.

## 13. Risques connus

- Qualite OCR variable: un resultat `complete` signifie texte extractible, pas garantie semantique parfaite.
- Latence: `180` secondes est un plafond, pas une promesse de rapidite.
- Charge CPU: l'OCR doit rester bornee et rare.
- Disponibilite Stirling: si `platform-stirling-pdf` est indisponible, l'upload doit echouer proprement sans bloquer le chat.
- Retour non-PDF ou PDF non extractible: le document ne doit pas devenir actif.
- Observabilite: ne jamais transformer une preuve OCR en fuite de contenu OCR.

## 14. Notes de preuve prealable

Preuve technique effectuee avant creation de ce TODO:

- PDF image-only temporaire cree sans document utilisateur reel;
- extraction FridaDev avant OCR: `ocr_required` / `document_ocr_required`;
- appel Stirling interne: `200`, `application/pdf`;
- extraction FridaDev apres OCR: `complete`, texte non vide;
- artefacts temporaires supprimes.

Cette preuve valide l'architecture V1, mais ne remplace pas les tests automatises du chantier.
