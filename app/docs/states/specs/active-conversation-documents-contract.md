# Active conversation documents contract

Statut: spec vivante
Date: 2026-05-17
Roadmap archivee: `app/docs/todo-done/product/active-conversation-documents-todo.md`
Roadmap OCR active: `app/docs/todo-todo/product/active-conversation-documents-ocr-todo.md`
Audit-plan source archive: `app/docs/todo-done/product/active-conversation-documents-audit-plan.md`
Chantier distinct: `app/docs/todo-todo/product/frida-biblio-native-catalogue-todo.md`
Portee: contrat produit, prompt, frontieres et observabilite des documents actifs de conversation
Extension OCR V1: OCR bornee des PDF scannes via Stirling, seulement apres `document_ocr_required`, puis repassage par l'extracteur FridaDev.
Limites conservees: Biblio native, RAG documentaire, stockage documentaire persistant, ouverture automatique du texte complet dans le dashboard

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

## 4. Formats supportes et OCR bornee

Formats cibles initiaux:

- PDF deja textuels;
- DOCX;
- ODT;
- MD;
- TXT.

Lot 3 livre l'extraction dans:

- `app/core/active_document_text_extraction.py`.

Choix de parsing retenus:

- TXT / MD: decode texte UTF strict via la bibliotheque standard;
- DOCX: lecture ZIP + XML WordprocessingML via la bibliotheque standard;
- ODT: lecture ZIP + `content.xml` OpenDocument via la bibliotheque standard;
- PDF textuel: `pypdf`, ajoute comme dependance sobre dediee aux PDF.

OCR:

- l'extraction initiale sans OCR peut retourner `ocr_required`;
- aucun PDF scanne ne doit etre presente comme document textuel lu avant OCR explicite;
- aucune extraction OCR implicite ne doit etre ajoutee;
- l'OCR V1 est seulement le chemin explicite decrit en 4.1, apres `document_ocr_required`;
- un PDF deja textuel ne doit jamais etre OCRise.

Extraction:

- l'extraction doit viser le texte complet du fichier;
- une extraction partielle ne doit jamais etre presentee comme complete;
- un document partiellement extrait doit etre marque en erreur ou non injectable selon la raison compacte stabilisee par le lot implementation;
- le texte extrait n'est pas un resume;
- le texte extrait n'est pas un chunk RAG.

Statuts d'extraction stabilises:

- `complete`: texte extrait entierement et normalise, sans resume;
- `unsupported`: format non supporte, reason `document_type_unsupported`;
- `parse_error`: parsing impossible, reason `document_parse_error`;
- `empty`: fichier ou extraction textuelle vide, reason `document_empty_text`;
- `ocr_required`: PDF sans texte extractible sur au moins une page, reason `document_ocr_required`.

### 4.1 Extension OCR V1 des PDF scannes

L'OCR est une extension bornee de `active_document`. Elle ne cree pas une Biblio, ne cree pas de `library_document`, ne cree pas de `catalogue_document`, ne cree pas de `passage documentaire`, et ne transforme pas l'upload ponctuel en ingestion persistante.

Chemin V1 normatif:

```text
document_ocr_required -> Stirling -> PDF OCRise -> extracteur FridaDev -> complete
```

Regles obligatoires:

- `active_document` reste maitre du flux;
- l'OCR n'est appelee que lorsque l'extracteur initial retourne `ocr_required` avec reason `document_ocr_required`;
- un PDF deja textuel n'est jamais OCRise;
- le client V1 appelle `platform-stirling-pdf`;
- Stirling renvoie un PDF OCRise;
- FridaDev repasse toujours ce PDF OCRise dans `app/core/active_document_text_extraction.py`;
- seul un resultat final `complete` peut activer le document;
- si le resultat final reste non-`complete`, le document reste non actif avec reason compact;
- une fois actif, un document OCRise suit exactement les memes regles qu'un autre `active_document`: conversation-scoped, retire manuellement, injecte entier ou exclu entier par tour, hors Memory/RAG/Identity/Summary.

Parametres operateur V1:

- timeout OCR maximal: `180` secondes;
- langues OCR par defaut: `fra+eng+deu`;
- plafond V1: `25 pages` maximum;
- plafond V1: `25 Mo` maximum;
- OCR synchrone bornee pendant l'upload.

Lot 2 livre le client OCR borne dans:

- `app/core/active_document_ocr_client.py`.

Configuration runtime:

- `ACTIVE_DOCUMENT_OCR_URL`, defaut `http://platform-stirling-pdf:8080/pdf/api/v1/misc/ocr-pdf`;
- `ACTIVE_DOCUMENT_OCR_TIMEOUT_S`, defaut `180`;
- `ACTIVE_DOCUMENT_OCR_LANGUAGES`, defaut `fra+eng+deu`;
- `ACTIVE_DOCUMENT_OCR_MAX_PAGES`, defaut `25`;
- `ACTIVE_DOCUMENT_OCR_MAX_BYTES`, defaut `26214400` (`25 Mo`).

Le client detecte le nombre de pages avant l'appel OCR. Il refuse avant Stirling:

- `document_ocr_too_large` si le fichier depasse `ACTIVE_DOCUMENT_OCR_MAX_BYTES`;
- `document_ocr_too_many_pages` si le PDF depasse `ACTIVE_DOCUMENT_OCR_MAX_PAGES`.

Le client retourne seulement des statuts, reason codes, metadonnees et, en cas de succes, le PDF OCRise en memoire pour le lot d'integration suivant. Ses projections ordinaires restent content-free et n'exposent pas le texte OCR brut.

Lot 3 branche ce client dans `app/core/active_document_upload_service.py`:

- l'OCR est tentee seulement quand l'extraction initiale retourne `ocr_required` avec reason `document_ocr_required`;
- un PDF deja textuel, donc extrait en `complete`, ne passe pas par l'OCR;
- le PDF OCRise est repasse dans l'extracteur FridaDev existant;
- le document est active seulement si cette extraction finale retourne `complete`;
- en cas de succes OCR, l'etat serveur conserve les metadonnees compactes `ocr_applied`, `ocr_engine`, `ocr_languages`, `ocr_duration_ms`;
- si l'OCR echoue, expire, retourne vide, depasse les limites ou produit un PDF non extractible en `complete`, l'upload est refuse avec reason compact;
- les reponses ordinaires d'upload restent content-free et ne contiennent ni texte OCR brut, ni PDF OCRise.

Au-dela de `25 pages` ou `25 Mo`, le document doit etre refuse pour ce chantier avec un motif clair. A cette echelle, le besoin releve du futur chantier Biblio / Catalogue, pas du document actif ponctuel.

Frontieres OCR:

- pas d'OCR sur PDF deja textuel;
- pas de Biblio;
- pas de n8n nominal;
- pas de doc-pipeline nominal;
- pas d'OCR de masse;
- pas d'image multimodale generale;
- pas de stockage durable inter-conversations;
- pas de fuite du texte OCR brut dans l'UI, les logs ordinaires, les read-models ou le dashboard.

Le texte OCR brut peut seulement servir a produire le texte complet final du `active_document` si l'extracteur FridaDev conclut `complete`. Il ne doit pas etre expose par defaut.

Sortie metadata du parseur:

- `text`;
- `chars` / `text_chars`;
- `bytes` / `byte_size`;
- `token_estimate`;
- `sha256_12` / `text_sha256_12`;
- `status`;
- `reason_code`;
- `parser`.

Limite volontaire du Lot 3:

- le parseur retourne le texte au service appelant, mais ne l'active pas encore;
- aucun endpoint, frontend, prompt ou dashboard n'est branche dans ce lot;
- aucun OCR implicite n'est ajoute.

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

Lot 4 fixe la politique de tour:

- les documents actifs sont relus apres la decision de resume;
- ils sont ajoutes au prompt principal avant l'appel modele principal;
- l'ordre est stable: `created_at`, puis `filename`, puis `document_id`;
- chaque document est decide separement:
  - injecte entierement si aucune limite documentaire dure n'est configuree;
  - injecte entierement si le prompt du tour avec ce document reste sous `ACTIVE_DOCUMENT_PROMPT_MAX_TOKENS` quand cette limite vaut plus de `0`;
  - exclu entierement avec reason `document_too_large_for_turn` seulement si cette limite documentaire dure explicite est configuree et depassee;
- un document vide est exclu avec reason `document_empty_text`;
- le dialogue recent non resume n'est jamais coupe pour faire entrer un document actif;
- le tour continue meme si tous les documents actifs sont exclus.

`ACTIVE_DOCUMENT_PROMPT_MAX_TOKENS` est une limite dure optionnelle d'admission des documents actifs. Sa valeur par defaut est `0`, ce qui desactive ce couperet documentaire. Elle ne doit pas heriter implicitement de `FRIDA_MAX_TOKENS`, car `FRIDA_MAX_TOKENS` reste un soft limit d'observabilite du prompt complet. Une valeur non nulle doit correspondre a une decision operateur explicite de capacite documentaire / provider; elle ne doit jamais couper les messages `user` / `assistant` non resumes.

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

Lot 5 verrouille cette frontiere par tests:

- le payload LLM peut contenir la lane documentaire, mais `save_new_traces(conversation)` ne recoit que les messages conversationnels `user` / `assistant`;
- le retrieval Memory/RAG est appele avec le `user_msg` du tour, jamais avec le texte du document actif;
- aucun embedding documentaire ni retrieval documentaire n'est cree par le chantier documents actifs.

### 6.2 Identity

Les documents actifs ne doivent pas:

- creer de candidats Identity;
- modifier le statique;
- modifier le mutable;
- produire de correction canonique;
- etre traites comme source identitaire automatique.

Un document actif peut contenir du texte parlant d'identite; ce chantier ne l'extrait pas.

Lot 5 verrouille cette frontiere par test: le couple de tour donne a l'extraction Identity reste le couple `user` / `assistant` persiste, sans contenu de la lane documentaire active.

### 6.3 Summary

Les documents actifs ne doivent pas:

- etre ajoutes aux messages `user` / `assistant`;
- entrer dans le calcul du seuil de resume;
- etre stockes dans un resume de conversation;
- declencher un resume par leur poids.

Le seuil de resume doit rester fonde sur la memoire dialogique directe: messages utilisateur et assistant non encore resumes.

Lot 5 verrouille cette frontiere par test: le seuil de resume et le texte transmis au summarizer sont construits uniquement depuis les messages `user` / `assistant` non resumes, meme si une lane documentaire active existe ailleurs dans le prompt.

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

Lot 4 livre le builder de lane dans:

- `app/core/active_document_prompt_lane.py`.

Insertion runtime:

- `chat_service.chat_response()` lit les documents actifs de la conversation via `active_conversation_documents.list_active_documents_for_prompt()`;
- `conv_store.build_prompt_messages()` compose d'abord le prompt canonique apres la decision de resume, sans faire entrer les documents actifs dans la logique de fenetre dialogique;
- l'injection Web eventuelle est appliquee;
- `active_document_prompt_lane.inject_active_document_prompt_lane()` decide ensuite, sur le prompt courant du tour, quels documents entrent entiers;
- la lane est inseree comme message systeme avant le dialogue utilisateur/assistant, juste avant l'appel au modele principal.

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

La presence du texte documentaire seul ne suffit pas comme preuve. Lot 4 ferme cette exigence pour le prompt principal: les tests verifient la presence de l'instruction d'interpretation dans le prompt final, pas seulement la presence du texte documentaire.

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

Reason codes OCR V1:

- `document_ocr_failed`: le moteur OCR n'a pas produit un PDF OCRise exploitable;
- `document_ocr_timeout`: le traitement OCR a depasse le timeout borne;
- `document_ocr_empty`: le PDF OCRise ne donne pas de texte final exploitable;
- `document_ocr_too_large`: le fichier depasse le plafond `25 Mo`;
- `document_ocr_too_many_pages`: le fichier depasse le plafond `25 pages`.

Toute extension doit rester compacte et content-free.

## 11. Observabilite content-free

Implementation courante:

- l'activation reussie emet un event admin compact `active_document_activated`;
- l'echec d'activation emet un event admin compact hors tour `active_document_activation_failed`;
- le retrait manuel emet un event admin compact hors tour `active_document_removed`;
- chaque tour avec au moins un document actif emet un event de tour `active_documents`;
- la materialisation dashboard persistante expose `dashboard_turn_facts.documents_json`;
- le module observable dashboard `documents` est reel pour les documents actifs de conversation;
- cette observabilite ne couvre pas la future Biblio native.

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
- last_excluded_turn_id;
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

Cette lecture doit rester metadata-only.

Le read-model d'inspection peut dire qu'un document actif a ete injecte entier ou exclu,
citer son nom, son type, sa taille, son estimation de tokens, son hash court et sa raison compacte.
Il ne doit pas recopier le texte, ni faire passer cette lane pour Memory/RAG, Web, Identity, Summary ou Biblio.
Il ne doit pas rattacher artificiellement un echec d'activation ou un retrait manuel a un tour:
ces deux cas restent visibles dans les logs admin compacts tant qu'aucun read-model hors-tour dedie n'existe.

## 12. Gate dashboard et contenu complet

Le gate dashboard existant `Afficher le contenu complet` ne donne pas automatiquement acces au texte complet des documents actifs.

Doctrine:

- pas de texte complet de document dans l'inspection ordinaire;
- pas de prechargement du texte complet dans le DOM;
- pas de promesse produit d'ouverture du texte complet dans ce chantier;
- toute future ouverture du texte complet d'un document actif exige une decision produit separee, une spec dediee et des garde-fous dedies.

Le chantier courant peut prouver qu'un fichier nomme a ete actif et injecte. Il ne promet pas de derouler le fichier dans le dashboard.

## 13. Etat actif serveur

Lot 2 livre le service d'etat serveur dedie dans:

- `app/core/active_conversation_documents.py`.

Emplacement retenu:

- `app/core/`, car l'etat est un etat applicatif de conversation;
- pas `app/memory/`, car il ne doit pas etre Memory/RAG;
- pas `app/admin/`, car il n'est pas une surface admin;
- pas `app/observability/`, car il n'est pas seulement une projection de lecture.

Persistence retenue:

- table runtime dediee `active_conversation_documents`;
- cle primaire `document_id`;
- liaison stricte `conversation_id`;
- reference `conversations(id) ON DELETE CASCADE`;
- initialisation au demarrage serveur via `active_conversation_documents.init_db()`, apres le catalogue de conversations;
- soft deactivation sur retrait manuel;
- cleanup explicite possible des documents desactives ou d'une conversation;
- aucune table Memory/RAG/Identity/Summary n'est utilisee.

Le texte extrait necessaire a la reinjection multi-tour est persiste dans cette table d'etat actif court terme. Il ne doit pas etre expose par les projections ordinaires:

- `list_active_documents()` retourne seulement les metadonnees content-free;
- `list_active_documents_for_prompt()` est reserve au builder de prompt et retourne explicitement `text_content`;
- les lots frontend, logs, dashboard et inspection ne doivent pas utiliser le chemin prompt pour afficher le texte.

Contrat d'etat:

- l'etat actif vit cote serveur;
- il est scoped par conversation;
- il survit au rechargement navigateur selon la retention decidee;
- il est retire par action manuelle explicite;
- il n'est pas Memory/RAG;
- il n'est pas Biblio;
- il n'est pas partage entre conversations.

Champs minimaux:

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
- `last_excluded_turn_id`;
- `last_excluded_reason_code`;
- `ocr_applied`;
- `ocr_engine`;
- `ocr_languages`;
- `ocr_duration_ms`.

Retention et nettoyage:

- activation: insertion active pour une conversation unique;
- reinjection: relecture de tous les documents actifs de cette conversation;
- retrait manuel: `status=inactive`, `deactivated_at`, reason code `manual_remove`;
- tours suivants: un document desactive n'est plus relu pour le prompt;
- suppression dure de conversation: cascade DB ou cleanup explicite;
- purge court terme: les documents desactives peuvent etre supprimes par seuil temporel sans toucher aux documents actifs.

Limite volontaire du Lot 2 au moment de sa livraison:

- aucun endpoint;
- aucun parsing de fichier;
- aucune injection prompt;
- aucune observabilite dashboard;
- aucun branchement Memory/RAG/Identity/Summary.

## 14. Frontend chat et routes produit

Lot 6 livre le flux utilisateur reel cote chat.

Routes produit minimales:

- `GET /api/conversations/<conversation_id>/active-documents`: liste content-free des documents actifs de la conversation;
- `POST /api/conversations/<conversation_id>/active-documents`: upload d'un fichier, extraction texte complete, activation serveur si le format est supporte;
- `DELETE /api/conversations/<conversation_id>/active-documents/<document_id>`: retrait manuel explicite, reason `manual_remove`.

Contrat de retour:

- les reponses ordinaires exposent seulement les metadonnees content-free;
- le texte extrait n'est jamais renvoye a l'UI chat;
- les erreurs de parsing/type/OCR/vide sont renvoyees comme statuts et reason codes compacts;
- un upload non activable ne bloque pas la saisie du chat.

Surface chat:

- le controle visible est nomme et pense comme `document actif de conversation`, pas comme bouton generique `Documents`;
- le drag-and-drop sur la surface chat active les fichiers supportes;
- le controle pres du composer ouvre le selecteur de fichiers;
- la liste affiche nom, type/extension, taille, longueur et statut compact;
- pendant un upload PDF, l'UI affiche un etat discret de type `OCR si necessaire`, sans faux pourcentage;
- lorsqu'un document actif a `ocr_applied=true`, la liste affiche une mention discrete `OCRise`;
- les refus OCR sont traduits en libelles humains simples, sans exposer les reason codes comme lecture principale;
- le retrait manuel reste accessible par fichier;
- l'etat serveur est recharge a chaque ouverture/rechargement de conversation;
- le contenu brut du document n'est pas affiche dans l'UI ordinaire.

Limites conservees apres Lot 6 et Lot 7:

- pas de module Biblio;
- pas d'affichage du texte complet;
- pas de changement Memory/RAG/Identity/Summary;
- pas de read-model hors-tour dedie pour raconter les echecs d'activation et retraits manuels dans une vue dashboard separee. Ces evenements restent visibles dans les logs admin compacts.

## 15. Preuves de cloture du chantier

Le chantier archive a livre les preuves suivantes:

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

Roadmap de preuve archivee:

- `app/docs/todo-done/product/active-conversation-documents-todo.md`.

## 16. Condition de revision

Cette spec devra etre revisee si:

- un format supporte change;
- une decision produit autorise le texte complet des documents dans un gate dedie;
- le chantier Biblio native commence a definir sa lane prompt;
- l'etat actif serveur change de retention;
- l'architecture OCR V1, ses limites ou son moteur changent.

Sans decision explicite, cette spec interdit la fusion entre documents actifs et Biblio native.
