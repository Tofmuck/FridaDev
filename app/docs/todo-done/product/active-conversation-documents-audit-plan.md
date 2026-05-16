# Documents actifs de conversation - audit-plan

Statut: clos / archive
Date: 2026-05-15
Date de cloture: 2026-05-16
Classement: `app/docs/todo-done/product/`
TODO derive archive: `app/docs/todo-done/product/active-conversation-documents-todo.md`
Portee: documents fournis volontairement par l'utilisateur a une conversation active, injectes au modele principal tant qu'ils restent actifs
Chantier distinct: `app/docs/todo-todo/product/frida-biblio-native-catalogue-audit-plan.md`
Hors-scope: OCR, RAG documentaire, Biblio native / bibliotheque documentaire persistante, AnythingLLM/OpenWebUI comme intermediaire principal, indexation, resume documentaire, promotion memoire, patch runtime dans ce commit

Note de cloture 2026-05-16: ce document conserve le cadrage initial du chantier. L'implementation active_document a ete livree ensuite dans la roadmap archivee; les constats "pas encore" ci-dessous doivent etre lus comme l'etat pre-implementation de l'audit-plan, pas comme l'etat runtime courant.

## 1. Question initiale et verdict

Existe-t-il un meilleur plan ?

Non pour ce cycle docs-only. Le meilleur plan est de cadrer d'abord la frontiere produit et runtime, puis de deriver un TODO lotable avant tout endpoint, parsing ou frontend.

Le code courant ne possede pas encore de lane documentaire active:

- le chat envoie aujourd'hui un payload JSON simple a `/api/chat`, pas un multipart documentaire;
- la seule surface d'upload reperee cote runtime est la transcription audio, pas les fichiers de conversation;
- le seuil de resume est calcule depuis les messages `user` / `assistant` non resumes;
- la fenetre de prompt assemble deja des lanes distinctes pour resume, indices contextuels, memoire, Identity, web et hermeneutique;
- le dashboard possede deja une architecture modulaire avec un futur module `documents`, mais aucun event documentaire materialise.

### Meilleure architecture cible

La meilleure architecture cible pour ces documents actifs de conversation dans l'etat actuel de FridaDev est une **couche serveur dediee d'etat actif de conversation**, DB-backed ou equivalent durable court terme, separee de Memory/RAG/Identity/Summary, qui:

- stocke par conversation les metadonnees et le texte extrait necessaire a la reinjection tant que l'utilisateur n'a pas retire le document;
- n'indexe pas, ne resume pas et ne promeut jamais ce texte en memoire;
- decide a chaque tour si chaque document actif peut etre injecte entier dans le prompt;
- exclut entierement le document du tour si l'injection entiere ne rentre pas;
- transmet au modele un signal structure compact quand un document actif n'a pas ete injecte;
- enseigne explicitement au modele que la lane est un **document actif de conversation** fourni volontairement par l'utilisateur pour le travail direct du tour courant;
- expose par defaut seulement des metadonnees content-free aux logs, read-models et dashboard;
- ne promet pas l'ouverture du texte complet du document dans le dashboard; une telle capacite demanderait une decision produit separee.

Cette architecture cree une capacite produit de lecture ponctuelle dans la conversation sans construire prematurement un systeme documentaire persistant.

### Frontiere avec la future Biblio native

L'audit complementaire du 2026-05-16 a confirme que les **documents actifs de conversation** et la future **Biblio / Frida Catalogue** sont deux capacites differentes mais compatibles.

Vocabulaire a reserver des maintenant:

- `document actif de conversation` / `active_document`: fichier fourni volontairement par l'utilisateur, temporaire, conversation-scoped, actif jusqu'au retrait manuel;
- `document de bibliotheque` / `library_document` / `catalogue_document`: document persistant deja connu d'une bibliotheque native, consulte a la demande;
- `passage documentaire`: extrait borne issu d'un `library_document` / `catalogue_document`, injecte pour repondre a une demande precise.

Decision:

- le chantier courant ne cree pas de Biblio;
- l'etat actif serveur temporaire ne doit jamais devenir le stockage de la bibliotheque persistante;
- il faut reserver deux lanes distinctes:
  - lane `documents actifs`: fichiers fournis par l'utilisateur dans la conversation courante;
  - future lane `Biblio / Catalogue`: passages recuperes a la demande depuis une bibliotheque persistante;
- l'observabilite doit rester separee:
  - documents actifs: actif, injecte, retire, trop gros, parsing error;
  - Biblio: requete, document resolu, locator, passage extrait, ambiguite, confiance;
- l'UI ne doit pas introduire un bouton ou vocabulaire generique `Documents` qui melangerait upload temporaire et bibliotheque persistante;
- AnythingLLM et OpenWebUI peuvent rester des precedents a relire, mais ne sont pas le chemin principal cible pour cette capacite.

La compatibilite entre les deux chantiers tient donc a un contrat de lanes, de vocabulaire et d'observabilite; elle ne passe pas par un etat serveur commun.

## 2. Doctrine produit non negociable

Le premier chantier documentaire de Frida n'est pas une bibliotheque documentaire persistante, ni un OCR, ni un RAG documentaire.

C'est un systeme de documents actifs de conversation:

- formats cibles initiaux: PDF deja textuels, DOCX, ODT, MD, TXT;
- pas d'OCR dans ce chantier;
- contenu textuel envoye entier au modele quand c'est possible;
- aucune troncature silencieuse;
- si un document ne peut pas entrer entier dans le payload du tour, il est entierement exclu de ce tour;
- le tour ne doit jamais etre bloque par un document trop gros;
- Frida doit recevoir un signal structure lui permettant de dire naturellement que le fichier est trop gros pour ce tour;
- un document actif reste dans le payload a chaque tour jusqu'a retrait manuel explicite;
- l'etat actif vit cote serveur, pas seulement dans le navigateur;
- l'etat actif est distinct de la memoire, du RAG, de l'Identity et du resume;
- le document actif ne doit pas entrer dans le calcul du seuil de tokens qui declenche le resume de conversation.

Le prompt principal doit identifier explicitement la lane documentaire par des balises ou un encadrement structure clair, distinct de:

- contenu conversationnel;
- Memory/RAG;
- Identity;
- Web;
- Hermeneutic;
- resume de conversation.

Ce balisage ne suffit pas a lui seul. Le prompt principal doit aussi contenir un contrat d'interpretation clair: un document actif de conversation est un document temporaire fourni volontairement par l'utilisateur dans la conversation courante, utilisable comme contexte de travail direct tant qu'il reste actif. Quand l'utilisateur demande de travailler "sur le document", le modele doit comprendre cette demande a partir de cette lane documentaire active, et non comme un souvenir, un resume, un contexte web ou une piece peripherique. Si un document actif est signale mais non injecte sur le tour courant, le modele ne doit jamais pretendre l'avoir lu.

## 3. Etat actuel cartographie

### Chat et API

Le chat courant envoie des messages via `/api/chat` avec des champs conversationnels (`message`, `conversation_id`, `stream`, `web_search`, `input_mode`). Aucun chemin documentaire actif n'est visible dans le frontend chat actuel.

`app/server.py` expose une route statique `/dashboard` et des routes admin dashboard, mais pas de route produit de type upload/list/delete pour documents actifs.

La route multipart existante la plus proche est orientee transcription audio, pas documents texte.

### Session et conversation

`app/core/chat_service.py` orchestre:

- resolution de session;
- append du message utilisateur;
- eventuel resume;
- contexte memoire;
- contexte web;
- jugement hermeneutique;
- construction du prompt;
- appel modele principal;
- persistence finale.

La lane documentaire devra etre injectee sans changer la nature des messages conversationnels et sans polluer les flows memoire ou summary.

### Resume

`app/memory/summarizer.py` calcule le seuil de resume depuis les messages bruts `user` / `assistant` non encore resumes.

Risque majeur: si un document actif est stocke comme message utilisateur ou fusionne dans le contenu utilisateur avant ce calcul, il declenchera le resume a tort et pourra etre resume comme dialogue.

Regle cible: les documents actifs doivent rester hors de `conversation["messages"]` et hors de la matiere resumee. Leur injection doit se faire apres la decision de resume et via une lane dediee.

### Prompt

`app/core/conversations_prompt_window.py` construit deja des blocs systeme separes:

- resume actif;
- indices contextuels;
- contexte memoire;
- traces memoire;
- fenetre recente de conversation.

`app/core/chat_prompt_context.py` sait injecter certains contextes dans le prompt, notamment web. Le futur chemin documentaire doit eviter une fusion opaque dans le message utilisateur: la lane documentaire doit rester nommee et bornee.

### Memory/RAG et Identity

Memory/RAG est une chaine de retrieval, arbitration et injection de souvenirs. Les documents actifs ne doivent pas y entrer:

- pas d'embedding;
- pas d'index;
- pas de `memory_trace`;
- pas de `summary_id`;
- pas de promotion automatique;
- pas d'alimentation Identity.

Identity reste une doctrine canonique separee. Un document actif peut contenir des informations identitaires, mais ce chantier ne doit pas les extraire ni les appliquer.

### Observabilite et dashboard

Le dashboard long terme possede deja:

- faits par tour;
- agregats longue periode;
- modules observables;
- inspection traduite;
- gate `Afficher le contenu complet` pour les contenus deja decides par le chantier dashboard.

Le catalogue contient deja un module futur `documents`, mais il est declaratif: aucun event documentaire runtime n'est encore materialise.

La cible documentaire doit donc ajouter plus tard des events et facts content-free, sans recopier le contenu dans l'inspection ordinaire et sans deduire automatiquement un acces au texte complet du document depuis le gate existant.

### Dependances de parsing

Les dependances Python actuelles visibles dans `app/requirements.txt` ne couvrent pas encore l'extraction PDF/DOCX/ODT. Les lots de code devront choisir explicitement des bibliotheques de parsing sobres, testables et compatibles conteneur, au lieu de supposer leur presence.

## 4. Points de contamination a eviter

### Memory/RAG

Risque: traiter le document actif comme une source memoire.

Garde-fou cible:

- module dedie hors `app/memory/`;
- aucun embedding;
- aucun retrieval;
- aucune insertion dans traces, summaries ou arbiter decisions;
- observabilite separee avec module `documents`.

### Identity

Risque: extraire des faits identitaires depuis le document.

Garde-fou cible:

- aucun branchement vers les services Identity;
- aucun candidat mutable;
- aucune correction canonique;
- mention explicite dans les specs que le document est seulement un contexte de tour.

### Summary

Risque: compter les documents dans le seuil de resume ou les resumer comme dialogue.

Garde-fou cible:

- stockage hors messages `user` / `assistant`;
- injection apres `maybe_summarize()`;
- tests prouvant que deux tours avec document actif ne modifient pas le seuil de resume par le poids du document.

### Prompt

Risque: fusionner le document dans le message utilisateur et perdre la frontiere.

Garde-fou cible:

- bloc systeme dedie avec en-tete stable;
- inventaire compact des documents actifs injectes ou exclus;
- contenu exact seulement dans la lane documentaire injectee, jamais dans les logs compacts.

### Logs et dashboard

Risque: fuite du contenu dans payloads de debug ou inspection ordinaire.

Garde-fou cible:

- events content-free par defaut;
- noms, types, tailles, chars, token_estimate, status, injected, reason_code;
- hashes courts ou refs internes si utile;
- pas de texte complet du document dans le dashboard par defaut, ni dans l'inspection documentaire ordinaire.

## 5. Architecture cible recommandee

### 5.1 Etat actif serveur

Creer plus tard une responsabilite dediee, par exemple `app/core/active_conversation_documents.py` ou un nom equivalent apres relecture du depot.

Responsabilites:

- enregistrer un document actif pour une conversation;
- conserver metadonnees et texte extrait tant que le document est actif;
- lister les documents actifs;
- desactiver/supprimer sur action manuelle;
- refuser toute reutilisation hors conversation;
- exposer des projections content-free.

Stockage recommande: table applicative dediee ou stockage serveur equivalent, non classe comme memoire. La persistence courte est justifiee parce qu'un document doit rester actif sur plusieurs tours et survivre au rechargement navigateur. Elle ne doit pas devenir une bibliotheque documentaire longue duree.

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
- `last_excluded_turn_id`;
- `last_excluded_reason_code`.

Le texte extrait peut etre necessaire au runtime pour reinjection, mais il ne doit pas etre expose par defaut ni alimente dans Memory/RAG/Identity/Summary.

### 5.2 Activation et desactivation

Flux cible:

1. Le frontend garantit une conversation courante.
2. L'utilisateur glisse-depose un fichier.
3. Le serveur valide type/extension via l'extracteur et mesure la taille brute; aucun couperet arbitraire de taille upload n'est ajoute sans decision operateur explicite.
4. Le serveur extrait le texte.
5. Le document devient actif si l'extraction est complete et exploitable.
6. Le frontend affiche pres de la zone de saisie les documents actifs.
7. L'utilisateur retire manuellement un document actif.
8. Le serveur desactive/supprime l'etat actif et logge un event compact.

Un document dont l'extraction echoue ne doit pas devenir une injection partielle silencieuse. Il peut rester visible comme erreur d'activation avec raison compacte.

### 5.3 Extraction texte

Formats initiaux:

- TXT: texte UTF-8 ou detection stricte documentee;
- MD: texte brut Markdown, sans rendu HTML obligatoire;
- PDF: uniquement PDF textuels, sans OCR;
- DOCX: extraction du texte principal;
- ODT: extraction du texte principal.

Regles:

- pas d'OCR;
- pas de parsing partiel presente comme complet;
- si extraction partielle unavoidable par une bibliotheque, le document doit etre marque `parse_error` ou `partial_extraction_not_supported` et non injecte comme complet;
- normalisation minimale des fins de ligne;
- conservation d'une longueur et d'un hash compact pour preuve.

### 5.4 Decision entier ou exclu

La decision se fait a chaque tour, au plus pres de l'appel modele principal, quand le prompt hors documents est connu.

Regles:

- si un document actif rentre entier dans le budget documentaire du tour, il peut etre injecte entier;
- si plusieurs documents sont actifs, la politique d'ordre doit etre explicite et stable;
- aucun document ne doit etre tronque pour "faire rentrer";
- un document trop gros est entierement exclu de ce tour;
- le tour continue sans blocage;
- Frida recoit un signal structure content-free: nom, type, taille/longueur, raison compacte.

Raisons compactes attendues:

- `document_too_large_for_turn`;
- `document_parse_error`;
- `document_type_unsupported`;
- `document_not_active`;
- `document_runtime_unavailable`.

Le signal au modele ne doit pas imposer une phrase mecanique; il doit simplement rendre la situation comprehensible.

### 5.5 Lane documentaire dans le prompt

La lane documentaire doit etre un bloc dedie, avec en-tete stable, par exemple:

```text
[Documents actifs fournis par l'utilisateur]
...
[/Documents actifs fournis par l'utilisateur]
```

Le nom exact doit etre fixe dans une future spec, mais la frontiere est obligatoire.

La future spec devra aussi fixer le **contrat d'interpretation prompt** de cette lane. Le modele doit recevoir une instruction explicite indiquant que:

- cette lane contient des documents actifs de conversation;
- ces documents ont ete fournis volontairement par l'utilisateur;
- ils font partie du contexte de travail direct du tour courant tant qu'ils restent actifs et injectes;
- une demande de type "travaille sur le document" ou "resume/analyse/corrige ce fichier" doit etre interpretee en priorite a partir de cette lane;
- la lane documentaire est distincte de Memory/RAG, du resume de conversation, d'Identity, du Web et du jugement hermeneutique;
- un document actif non injecte pour cause de taille, parsing ou indisponibilite ne doit pas etre traite comme lu.

Le bloc doit distinguer:

- documents actifs injectes;
- documents actifs non injectes;
- raisons compactes;
- contenu textuel exact seulement pour les documents injectes.

Le bloc documentaire ne doit pas etre confondu avec:

- Memory/RAG;
- Identity;
- Web;
- Hermeneutic;
- resume.

Le lot d'integration prompt ne devra donc pas seulement ajouter un bloc de texte dans le payload: il devra aussi enseigner au modele le statut semantique de ce bloc.

### 5.6 Exclusion du seuil de resume

La decision de resume doit rester fondee sur les messages conversationnels. Les documents actifs ne doivent pas:

- etre ajoutes a `conversation["messages"]`;
- etre comptes par `_raw_dialogue()`;
- etre stockes dans les summaries;
- produire de `summary_id`;
- declencher `maybe_summarize()` par leur poids.

L'injection documentaire doit donc intervenir apres la decision de resume et etre verifiee par tests.

### 5.7 Observabilite cible

Par defaut, les logs et read-models doivent montrer:

- document actif oui/non;
- nom de fichier;
- type;
- taille bytes;
- longueur texte;
- token estimate;
- actif oui/non;
- injecte oui/non;
- raison compacte si non injecte;
- turn_id concerne;
- document_id ou hash court;
- source `active_conversation_documents`.

L'inspection exhaustive documentaire ne doit pas derouler le fichier: elle doit prouver quel fichier nomme etait actif, s'il a ete injecte, et sinon pourquoi.

Ils ne doivent pas montrer:

- texte complet du document;
- extraits de contenu;
- prompt complet;
- payload modele complet;
- secret ou credential.

Le dashboard pourra raconter un tour ainsi:

- "1 document etait actif sur ce tour."
- "Le document `rapport.pdf` a ete envoye entier au modele."
- "Le document `annexe.pdf` etait actif mais trop gros pour ce tour; il n'a pas ete envoye."
- "Le document `scan.pdf` n'a pas ete exploite: OCR hors scope."

Le texte complet du document n'est pas une promesse de ce chantier. Si le produit decide un jour de permettre son ouverture depuis le dashboard, ce sera une decision separee avec garde-fous dedies, pas une consequence automatique du gate existant.

### 5.8 Extension future

Ce chantier doit preparer le futur systeme documentaire sans le construire.

Preparer:

- module observable `documents`;
- noms d'events stables;
- metadonnees content-free;
- references content-free compatibles avec une decision produit future, sans ouverture automatique du texte complet;
- separation claire entre document actif et futur document persistant.

Ne pas preparer:

- index documentaire;
- embeddings documentaires;
- recherche documentaire durable;
- OCR;
- connecteur AnythingLLM/OpenWebUI comme chemin principal.

## 6. Alternatives considerees

### Etat navigateur seulement

Rejete. Un document actif doit rester visible sur plusieurs tours et etre verifiable cote serveur. Un etat navigateur ne suffit pas pour l'audit, l'injection fiable ni le retrait manuel robuste.

### Memory/RAG documentaire immediat

Rejete. Le besoin court terme est de donner au modele le document fourni, pas de l'indexer ni de le retrouver plus tard. Le RAG introduirait selection, scoring, chunks et ambiguite alors que la doctrine demande entier ou rien.

### Troncature automatique

Rejetee. Elle ferait croire au modele qu'il a vu le document alors qu'une partie manque. La regle produit est plus claire: injecte entier ou exclu entier.

### Bloquer le tour si le document est trop gros

Rejete. Le tour doit continuer. Frida doit seulement recevoir un signal structure pour expliquer naturellement la limite.

### Resume documentaire

Rejete dans ce chantier. Resumer le document transformerait la capacite en pipeline documentaire et contaminerait la promesse "contenu entier quand possible".

### Bibliotheque documentaire durable maintenant

Rejetee. Elle pourra venir plus tard, avec ses propres decisions de retention, recherche, droits, OCR et RAG. Le chantier actuel reste conversationnel et actif.

Le futur chantier est explicitement separe sous le nom Biblio native / Frida Catalogue. Il devra consulter des `library_document` / `catalogue_document`, resoudre des locators, extraire des passages documentaires (`passage documentaire`), puis injecter ces passages dans une lane dediee. Il ne doit pas reutiliser l'etat `active_document`.

## 7. Risques a traiter par les lots de code

- Taille provider / contexte: il faudra connaitre le budget reel du modele principal et eviter les additions approximatives.
- Parsing partiel: certaines bibliotheques peuvent extraire un texte incomplet sans erreur nette.
- Confusion document actif vs memoire: le nommage module et les tests devront verrouiller la frontiere.
- Resume declenche a tort: le document ne doit pas gonfler `_raw_dialogue()`.
- Fuite dans logs: les events doivent etre content-free stricts.
- Vie des fichiers: la retention apres desactivation, suppression conversation ou restart doit etre explicite.
- Redemarrage serveur: si l'etat actif est seulement en memoire process, la promesse multi-tour est fragile.
- Multiples documents actifs: il faudra une politique d'ordre et de budget stable.
- Derive de perimetre: le gate `Afficher le contenu complet` existe deja pour le dashboard, mais il ne doit pas devenir automatiquement un acces au texte complet des documents actifs.

## 8. Observabilite attendue par scenario

### Document actif injecte

Defaut visible:

- filename;
- type;
- chars;
- bytes;
- token_estimate;
- active=true;
- injected=true;
- reason_code=null.

Contenu complet:

- non promis dans le dashboard par ce chantier; l'inspection exhaustive reste limitee aux metadonnees et au statut d'injection.

### Document actif trop gros

Defaut visible:

- active=true;
- injected=false;
- reason_code=`document_too_large_for_turn`;
- token_estimate;
- budget estimate si disponible.

Modele:

- recoit un signal structure, pas le contenu.

### Erreur de parsing

Defaut visible:

- active=false ou activation_failed selon design retenu;
- injected=false;
- reason_code=`document_parse_error`;
- type;
- bytes;
- parser_kind si utile.

### Retrait manuel

Defaut visible:

- active=false;
- deactivated_at;
- reason_code=`manual_remove`.

Tour suivant:

- le document ne doit plus etre injecte.

## 9. Preuves attendues quand le code commencera

Les lots de code devront prouver au minimum:

- upload et activation d'un TXT/MD;
- extraction PDF textuel/DOCX/ODT avec fixtures;
- refus clair OCR/scans;
- deux tours successifs avec document actif reinjecte;
- retrait manuel puis absence d'injection;
- document trop gros exclu entierement sans bloquer le tour;
- prompt principal contenant le contrat d'interpretation de la lane document actif de conversation;
- test prouvant que le modele recoit l'instruction qui distingue le document actif de la memoire, du resume, d'Identity et du web;
- summary non declenche par le poids documentaire;
- Memory/RAG/Identity non alimentes;
- logs/read-models/dashboard content-free;
- texte complet du document absent de l'inspection ordinaire;
- aucune promesse d'ouverture du texte complet du document sans decision produit separee.
