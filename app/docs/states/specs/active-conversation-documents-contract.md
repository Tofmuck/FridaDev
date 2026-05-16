# Active conversation documents contract

Statut: spec vivante
Date: 2026-05-16
Source active: `app/docs/todo-todo/product/active-conversation-documents-todo.md`
Audit-plan source: `app/docs/todo-todo/product/active-conversation-documents-audit-plan.md`
Chantier distinct: `app/docs/todo-todo/product/frida-biblio-native-catalogue-todo.md`
Portee: contrat produit, prompt, frontieres et observabilite des documents actifs de conversation
Hors-scope: runtime, endpoint, frontend, parsing, OCR, Biblio native, RAG documentaire, migration, stockage documentaire persistant

## 1. Verdict de plan

Existe-t-il un meilleur plan ?

Non pour le Lot 1. Le bon plan est de graver une spec fondatrice avant tout code, afin que les futurs lots ne confondent pas:

- document actif temporaire;
- memoire;
- resume;
- web;
- identite;
- hermeneutique;
- future Biblio native.

Cette spec ne livre aucune implementation. Elle fixe les mots, les frontieres, les lanes prompt et les preuves attendues.

## 2. Definition centrale

Un **document actif de conversation** est un fichier fourni volontairement par l'utilisateur dans une conversation courante, active cote serveur, et destine a servir de contexte de travail direct tant qu'il reste actif.

Nom technique stable:

- `active_document`.

Proprietes obligatoires:

- temporaire;
- conversation-scoped;
- active par action utilisateur;
- retire par action manuelle explicite;
- reinjecte a chaque tour tant qu'il reste actif et qu'il rentre entier;
- exclu entierement du tour s'il ne peut pas etre injecte entier;
- jamais indexe;
- jamais resume;
- jamais promu en memoire;
- jamais reutilise hors de la conversation active.

Un `active_document` n'est pas:

- un souvenir Memory/RAG;
- un resume de conversation;
- une entree Identity;
- un resultat web;
- un jugement hermeneutique;
- un document de bibliotheque;
- un passage documentaire extrait depuis une bibliotheque persistante.

## 3. Vocabulaire normatif

### 3.1 Documents actifs

- `active_document`: document actif de conversation.
- activation: action qui rend un fichier actif dans une conversation.
- retrait manuel: action utilisateur qui desactive explicitement un document actif.
- injection entiere: envoi du texte extrait complet du document actif dans la lane prompt du tour.
- exclusion entiere: absence totale du texte du document actif dans le prompt du tour.
- signal non injecte: preuve structuree qu'un document actif existe mais n'a pas ete injecte.
- document actif non injecte: etat visible cote modele et observabilite quand le fichier est actif mais absent du payload modele du tour.

### 3.2 Future Biblio native

Ces termes sont reserves pour le chantier separe Biblio native / Frida Catalogue:

- `library_document`: document persistant connu d'une bibliotheque native.
- `catalogue_document`: document persistant resolu via Frida Catalogue / doc-pipeline.
- `passage documentaire`: extrait borne issu d'un `library_document` ou `catalogue_document`.

Un `library_document` ou `catalogue_document` ne doit pas etre stocke dans l'etat `active_document`. Un `passage documentaire` ne doit pas devenir automatiquement un document actif.

## 4. Formats supportes et absence d'OCR

Formats cibles initiaux:

- PDF deja textuels;
- DOCX;
- ODT;
- MD;
- TXT.

OCR:

- hors-scope du chantier;
- aucun PDF scanne ne doit etre presente comme document textuel lu;
- aucune extraction OCR implicite ne doit etre ajoutee dans ce chantier.

Extraction:

- l'extraction doit viser le texte complet du fichier;
- une extraction partielle ne doit jamais etre presentee comme complete;
- un document partiellement extrait doit etre marque en erreur ou non injectable selon la raison compacte stabilisee par le lot implementation;
- le texte extrait n'est pas un resume;
- le texte extrait n'est pas un chunk RAG.

## 5. Regle entier ou absent

La regle centrale est:

```text
Un document actif est injecte entierement ou il est entierement absent du tour.
```

Implications:

- aucune troncature silencieuse;
- aucun chunking pour faire entrer un document trop gros;
- aucun resume automatique pour remplacer le document;
- aucun blocage du tour si le document est trop gros;
- le modele recoit un signal explicite si un document actif existe mais n'a pas ete injecte.

Si plusieurs documents actifs existent, les futurs lots devront fixer une politique d'ordre stable. Cette spec interdit seulement les politiques qui tronquent silencieusement un document.

## 6. Frontieres strictes

### 6.1 Memory / RAG

Les documents actifs ne doivent pas:

- creer de memory traces;
- creer d'embeddings;
- entrer dans le retrieval;
- entrer dans l'arbiter memoire;
- produire de `summary_id`;
- etre promus en souvenir;
- etre retrouves plus tard comme memoire.

### 6.2 Identity

Les documents actifs ne doivent pas:

- creer de candidats Identity;
- modifier le statique;
- modifier le mutable;
- produire de correction canonique;
- etre traites comme source identitaire automatique.

Un document actif peut contenir du texte parlant d'identite; ce chantier ne l'extrait pas.

### 6.3 Summary

Les documents actifs ne doivent pas:

- etre ajoutes aux messages `user` / `assistant`;
- entrer dans le calcul du seuil de resume;
- etre stockes dans un resume de conversation;
- declencher un resume par leur poids.

Le seuil de resume doit rester fonde sur la memoire dialogique directe: messages utilisateur et assistant non encore resumes.

### 6.4 Web

Les documents actifs ne sont pas des resultats web. Le prompt et l'observabilite doivent distinguer:

- document fourni par l'utilisateur;
- contexte web recupere depuis l'exterieur.

### 6.5 Hermeneutic

Les documents actifs ne sont pas un jugement hermeneutique. Le jugement hermeneutique peut coexister dans le prompt, mais il ne decrit pas la provenance documentaire.

### 6.6 Future Biblio native

La future Biblio native est separee:

- lane documents actifs: fichiers fournis par l'utilisateur, actifs jusqu'au retrait manuel;
- future lane Biblio / Catalogue: passages recuperes a la demande depuis une bibliotheque persistante.

Le chantier documents actifs ne cree pas:

- d'outil Catalogue;
- de resolution `library_document`;
- de locator Biblio;
- d'extraction `passage documentaire`;
- d'UI Biblio.

## 7. Lane prompt dediee

Le prompt principal doit contenir une lane dediee et bornee.

Balises stables a utiliser comme contrat initial:

```text
[DOCUMENTS ACTIFS DE CONVERSATION]
...
[/DOCUMENTS ACTIFS DE CONVERSATION]
```

La lane doit pouvoir contenir deux sous-sections conceptuelles:

```text
[DOCUMENTS ACTIFS INJECTES]
...
[/DOCUMENTS ACTIFS INJECTES]

[DOCUMENTS ACTIFS NON INJECTES]
...
[/DOCUMENTS ACTIFS NON INJECTES]
```

La future lane Biblio / Catalogue est reservee mais non implementee dans ce chantier. Elle ne doit pas reutiliser ces balises.

Nom conceptuel reserve pour la Biblio:

```text
[PASSAGES DE BIBLIOTHEQUE CONSULTES]
...
[/PASSAGES DE BIBLIOTHEQUE CONSULTES]
```

Ce nom reserve ne constitue pas une implementation Biblio. Il fixe seulement la separation de vocabulaire.

## 8. Contrat d'interpretation modele

Le prompt principal ne doit pas seulement injecter un bloc documentaire. Il doit enseigner son sens au modele.

Instruction attendue, a formuler dans le prompt final lors du lot implementation:

- un document actif de conversation est fourni volontairement par l'utilisateur;
- il appartient a la conversation courante;
- il fait partie du contexte de travail direct du tour seulement lorsqu'il est injecte;
- il reste actif jusqu'au retrait manuel explicite;
- si l'utilisateur demande de travailler "sur le document", "sur ce fichier", "sur le PDF", "sur le texte joint" ou formulation equivalente, le modele doit interpreter cette demande a partir de la lane `DOCUMENTS ACTIFS DE CONVERSATION`;
- cette lane est distincte de Memory/RAG, du resume de conversation, d'Identity, du Web et du jugement hermeneutique;
- un document actif non injecte est un document connu mais non lu sur le tour courant;
- si un document actif est signale comme non injecte, le modele ne doit jamais pretendre l'avoir lu;
- le modele peut expliquer naturellement que le document n'a pas ete envoye dans ce tour, sans phrase mecanique imposee.

Le contrat d'interpretation doit etre teste plus tard dans le prompt final. La presence du texte documentaire seul ne suffira pas comme preuve.

## 9. Signal document actif non injecte

Quand un document actif n'est pas injecte, le modele doit recevoir un signal structure compact.

Signal minimal conceptuel:

- document actif present: oui;
- nom de fichier;
- type / extension;
- taille ou longueur;
- reason_code;
- statut: non injecte.

Le signal ne doit pas inclure le texte complet du document.

Le modele doit comprendre que:

- le document existe dans la conversation;
- le contenu n'est pas disponible dans le payload du tour;
- il ne doit pas inventer son contenu;
- il peut demander une action utilisateur ou expliquer la limite si utile.

## 10. Reason codes initiaux

Reason codes obligatoires:

- `document_too_large_for_turn`: le document actif ne rentre pas entier dans le tour courant;
- `document_parse_error`: l'extraction texte a echoue;
- `document_type_unsupported`: le format n'est pas supporte dans ce chantier;
- `document_runtime_unavailable`: le service ou l'etat documentaire n'est pas disponible;
- `manual_remove`: l'utilisateur a retire le document actif.

Reason codes autorises en extension si necessaires aux lots implementation:

- `document_not_active`;
- `document_empty_text`;
- `document_partial_extraction_not_supported`;
- `document_ocr_required`.

Toute extension doit rester compacte et content-free.

## 11. Observabilite content-free

Par defaut, logs, read-models et dashboard peuvent exposer:

- `document_id` ou hash court;
- filename;
- media_type;
- source_extension;
- byte_size;
- text_chars;
- text_sha256_12;
- token_estimate;
- active true/false;
- injected true/false;
- reason_code;
- created_at;
- deactivated_at;
- last_injected_turn_id;
- last_excluded_reason_code;
- source `active_conversation_documents`.

Par defaut, ils ne doivent jamais exposer:

- texte complet du document;
- extrait du document;
- prompt complet;
- payload modele complet;
- contenu Memory/RAG brut;
- Identity brute;
- query web brute;
- secret, DSN, token, cle privee ou credential.

Le dashboard peut raconter:

- "1 document etait actif sur ce tour.";
- "Le document a ete envoye entier au modele.";
- "Le document etait actif mais trop gros pour ce tour.";
- "Le document a ete retire manuellement.";

Cette lecture doit rester metadata-only.

## 12. Gate dashboard et contenu complet

Le gate dashboard existant `Afficher le contenu complet` ne donne pas automatiquement acces au texte complet des documents actifs.

Doctrine:

- pas de texte complet de document dans l'inspection ordinaire;
- pas de prechargement du texte complet dans le DOM;
- pas de promesse produit d'ouverture du texte complet dans ce chantier;
- toute future ouverture du texte complet d'un document actif exige une decision produit separee, une spec dediee et des garde-fous dedies.

Le chantier courant peut prouver qu'un fichier nomme a ete actif et injecte. Il ne promet pas de derouler le fichier dans le dashboard.

## 13. Etat actif serveur conceptuel

Le Lot 2 devra definir l'implementation. Le contrat conceptuel est deja fixe:

- l'etat actif vit cote serveur;
- il est scoped par conversation;
- il survit au rechargement navigateur selon la retention decidee;
- il est retire par action manuelle explicite;
- il n'est pas Memory/RAG;
- il n'est pas Biblio;
- il n'est pas partage entre conversations.

Champs conceptuels minimaux:

- `document_id`;
- `conversation_id`;
- `filename`;
- `media_type`;
- `source_extension`;
- `byte_size`;
- `text_chars`;
- `text_sha256_12`;
- `token_estimate`;
- `status`;
- `created_at`;
- `deactivated_at`;
- `last_injected_turn_id`;
- `last_excluded_reason_code`.

## 14. Tests requis par les futurs lots

Les futurs lots devront prouver:

- formats supportes et absence d'OCR implicite;
- document injecte entier;
- document trop gros exclu entier;
- document actif non injecte visible au modele avec reason_code;
- absence de troncature silencieuse;
- retrait manuel;
- deux tours successifs avec document actif reinjecte;
- non-contamination Memory/RAG;
- non-contamination Identity;
- non-contamination Summary;
- exclusion du seuil de resume;
- distinction `active_document` vs `library_document` / `catalogue_document` / `passage documentaire`;
- absence de contenu brut dans logs/read-models/dashboard ordinaires;
- absence d'ouverture automatique du texte complet via le gate dashboard existant.

## 15. Condition de revision

Cette spec devra etre revisee si:

- un format supporte change;
- une decision produit autorise le texte complet des documents dans un gate dedie;
- le chantier Biblio native commence a definir sa lane prompt;
- l'etat actif serveur change de retention;
- un besoin OCR entre dans le produit.

Sans decision explicite, cette spec interdit la fusion entre documents actifs et Biblio native.
