# Identity New Contract - TODO de cadrage

Statut: chantier documentaire ouvert  
Classement: `app/docs/todo-todo/memory/`  
Portee: contrat cible de separation entre identite canonique, hors-canon identitaire et artefact reflexif futur  
Etat runtime vise: aucun patch runtime dans ce document  
Contrainte dure: preserver explicitement l'observabilite identity actuelle et traiter toute evolution future comme un sujet de compatibilite/versionnement

References liees:
- `app/identity/active_identity_projection.py`
- `app/identity/identity.py`
- `app/identity/mutable_identity_validation.py`
- `app/memory/memory_identity_mutable_rewriter.py`
- `app/memory/memory_identity_mutables.py`
- `app/core/chat_memory_flow.py`
- `app/core/chat_prompt_context.py`
- `app/core/conversations_prompt_window.py`
- `app/core/hermeneutic_node/inputs/identity_input.py`
- `app/docs/states/specs/identity-read-model-contract.md`
- `app/docs/states/specs/identity-mutable-edit-contract.md`
- `app/docs/states/specs/identity-static-edit-contract.md`
- `app/docs/states/specs/identity-surface-contract.md`
- `app/docs/states/specs/identity-governance-contract.md`
- `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- `app/docs/todo-done/refactors/identity-vs-prompt-separation-todo.md`
- `app/docs/todo-todo/memory/Frida_from_herself.md`
- `app/docs/todo-todo/memory/memory-contextual-moments-todo.md`

## 1. Question pre-patch et decision d'ouverture

Question posee avant patch:

Existe-t-il un meilleur plan que d'ouvrir maintenant une branche documentaire `identity-new-contract`, de relire le contrat identitaire reel courant, puis de rediger dans `app/docs/todo-todo/memory/` un document-cadre qui separe strictement fixe, mutable, non-identitaire et artefact reflexif futur, tout en preservant explicitement l'observabilite existante ?

Reponse retenue: non.

Pourquoi:
- le runtime actuel identity est deja stabilise autour d'un contrat reel lisible: `static + mutable narrative`, surfaces admin live, read-model, diagnostics et logs compacts deja en production;
- le vrai risque n'est pas l'absence d'implementation immediate, mais un futur refactor doctrinal qui casserait silencieusement les coutures d'observabilite et les surfaces de lecture existantes;
- avant toute refonte runtime, il faut donc un contrat de separation plus strict, borne, relisible et compatible avec l'etat live.

Decision de chantier:
- ouvrir uniquement un chantier documentaire;
- ne toucher ni au pipeline runtime, ni a la DB, ni au frontend, ni a `Frida from herself`;
- figer d'abord un contrat cible qui dise clairement ce qui est identitaire, ce qui ne l'est pas, et ce qui devra vivre ailleurs.

## 2. Diagnostic de l'etat courant

### 2.1 Verite active actuelle

Le systeme identitaire actif repose aujourd'hui sur quatre blocs canoniques:
- `llm.static`: contenu fichier lu par `load_llm_identity()` via `static_identity_content`, injecte au runtime et expose au read-model comme source `resource_path_content`;
- `user.static`: contenu fichier lu par `load_user_identity()` selon le meme contrat file-backed;
- `llm.mutable`: ligne canonique de `identity_mutables` pour le sujet `llm`, lue par `get_mutable_identity()` puis injectee activement;
- `user.mutable`: ligne canonique de `identity_mutables` pour le sujet `user`, avec le meme statut.

Verification runtime OVH du `2026-04-17`, sans exposition de contenu brut:
- mode hermeneutique courant: `enforced_all`;
- schema runtime structure identity: `v2`;
- `llm.static`: source active `data/identity/llm_identity.txt`, longueur actuelle `2080`;
- `user.static`: source active `data/identity/user_identity.txt`, longueur actuelle `516`;
- `llm.mutable`: present, longueur actuelle `1537`;
- `user.mutable`: present, longueur actuelle `1555`.

### 2.2 Legacy encore visible, mais non souverain

Le legacy n'a pas disparu, mais il n'est plus la source active d'injection:
- `identities` reste visible comme `legacy_fragments`;
- `identity_evidence` reste visible comme `evidence`;
- `identity_conflicts` reste visible comme `conflicts`;
- `used_identity_ids` reste vide sur le chemin actif courant;
- le read-model expose explicitement `legacy_drives_active_injection = false`.

Autrement dit:
- le legacy reste lisible pour l'operateur;
- il reste utile pour l'evidence, le diagnostic, l'audit et certaines lectures secondaires;
- il n'est plus la souverainete canonique de l'identite injectee au runtime.

### 2.3 Ce qui est injecte aujourd'hui dans le runtime

Deux representations live coexistent deja et reposent sur la meme base canonique:

1. forme compilee injectee au modele final
- `build_identity_block()` relit `llm.static`, `user.static`, puis les deux mutables;
- `active_identity_projection.resolve_active_identity_projection()` compose un bloc texte avec sections `[IDENTITE DU MODELE]` / `[IDENTITE DE L'UTILISATEUR]`, puis `[STATIQUE]` et `[MUTABLE]`;
- `chat_prompt_context.build_augmented_system()` concatene ce bloc identity au prompt systeme augmente.

2. forme structuree compilee pour le jugement hermeneutique
- `build_identity_input()` produit `schema_version = "v2"`;
- cette forme separe `frida.static`, `frida.mutable`, `user.static`, `user.mutable`;
- elle alimente la couche de jugement sans se confondre avec le texte injecte au modele final.

Le contrat technique runtime actif est donc bien:
- `active_identity_source = "identity_mutables"`
- `active_static_source = "resource_path_content"`
- `active_prompt_contract = "static + mutable narrative"`

### 2.4 Observabilite deja branchee

L'observabilite identity n'est pas theorique: elle existe deja et sert de couture operateur live.

Elle passe aujourd'hui au minimum par:
- le stage `identities_read`, emis lors des lectures statiques et d'autres lectures compactes de type `durable` / `context_hint`;
- le stage `identity_write`, emis sur les ecritures/skips du pipeline identity;
- le resume `identity_mutable_rewrite`, emis par le rewriter de mutable;
- l'event admin `identity_mutable_rewrite_apply`, emis sur l'application du rewriter;
- l'event admin `identity_mode_apply`, qui rend lisible `persist_enforced`, `record_evidence_shadow` ou `skip_mode_off`;
- `GET /api/admin/identity/read-model`, qui expose `static`, `mutable`, `legacy_fragments`, `evidence`, `conflicts`;
- `GET /api/admin/identity/runtime-representations`, qui expose la forme structuree et la forme compilee injectee;
- les surfaces `/identity` et `/hermeneutic-admin`, qui reemploient ces lectures.

Le contrat de logs deja pose interdit les dumps bruts:
- identity reste en compact-only;
- sont permis: compteurs, drapeaux de presence, longueurs, reason codes, flags de validation;
- sont interdits: preview, raw identity text, raw filtered excerpts.

### 2.5 Ce qui existe deja hors canon identitaire: `context_hints`

Le runtime actuel dispose deja d'une premiere lane hors canon identitaire:
- `context_hints`, lus via `get_recent_context_hints()`;
- gouvernes par `CONTEXT_HINTS_MAX_ITEMS`, `CONTEXT_HINTS_MAX_TOKENS`, `CONTEXT_HINTS_MAX_AGE_DAYS`, `CONTEXT_HINTS_MIN_CONFIDENCE`;
- selectionnes dans `prepare_memory_context()`;
- injectes dans un bloc dedie `[Indices contextuels recents]`;
- distincts du canon `static` / `mutable`;
- distincts aussi de la memoire de moment contextuel, qui reste un chantier separe, et de `Frida from herself`, qui reste un artefact reflexif distinct.

Semantique actuelle de `context_hints`:
- hints recents, non durables, orientes rappel contextuel;
- issus aujourd'hui d'evidences user-side `episodic` ou `situation`;
- budgetes et bornes pour le prompt;
- explicitement hors promotion vers l'identite durable.

Conclusion de diagnostic:
- le systeme ne part pas de zero pour le hors canon identitaire;
- `context_hints` est deja la premiere forme operative de cette famille;
- le probleme restant n'est donc pas d'inventer une deuxieme lane, mais de fermer proprement son articulation doctrinale avec le futur contrat cible.

## 3. Probleme doctrinal actuel

Le probleme n'est plus de savoir si une couche identity existe. Elle existe.

Le probleme est que le mot `identite` reste encore trop large dans la pratique du `mutable`.

Constat doctrinal:
- le `mutable` actuel reste trop narratif et trop permissif;
- il peut encore absorber du non-identitaire important, mais non identitaire;
- la frontiere entre identite forte et preferences relationnelles/conversationnelles n'est pas assez fermee;
- le systeme dispose deja d'une premiere voie hors canon via `context_hints`, mais cette voie n'est pas encore formulee comme contrat general ferme pour tout le non-identitaire important;
- le risque n'est donc plus seulement la fuite du prompt dans l'identite, mais aussi la fuite du relationnel local, du contextuel et du quasi-narratif dans la mutable canonique.

Point de tension explicite dans l'etat courant:
- la spec actuelle du mutable autorise encore des formulations de type `aime discuter de`, `prefere des echanges sur`, `garde une voix`, si elles restent narratives;
- cette doctrine ferme bien le prompt-like, mais elle ne ferme pas encore assez la difference entre identite forte et patchwork relationnel;
- le resultat possible est un `mutable` qui ressemble moins a une identite et plus a un melange de modulation, preference, confort conversationnel et auto-description locale.

## 4. Contrat cible de separation

Le contrat cible propose ici une separation a quatre zones:
- `static` canonique;
- `mutable` canonique;
- `hors canon identitaire`;
- `artefact reflexif futur`.

### 4.1 Ce qui doit vivre dans `static`

`static` doit porter ce qui demeure vrai a travers le temps long, sans dependre de la conversation locale.

Il doit contenir, pour Frida comme pour Tof:
- traits forts et durables;
- caractere ou maniere d'etre de fond;
- posture profonde;
- voix de reference;
- continuites biographiques ou existentielles stables;
- bornes identitaires qui ne devraient pas osciller d'un lot, d'un tour ou d'un jour a l'autre.

`static` ne doit pas contenir:
- une methode de travail;
- une politique de format;
- une strategie de reponse;
- une preference circonstancielle de dialogue;
- une consigne liee au gap, a la reprise, au tour courant ou a la tache.

### 4.2 Ce qui doit vivre dans `mutable`

`mutable` doit devenir une zone beaucoup plus stricte que l'etat actuel.

`mutable` doit seulement porter:
- une modulation identitaire durable ou semi-durable du socle;
- une evolution reelle de posture profonde deja suffisamment stable pour meriter une canonisation;
- une nuance persistante de voix, de positionnement ou de continuite personnelle;
- une reformulation compacte de ce que Frida est ou de ce que Tof est, quand cette reformulation n'est pas encore assez stable pour entrer dans `static`, mais depasse deja nettement le contexte local.

`mutable` ne doit plus porter:
- preferences conversationnelles locales;
- conforts d'interaction;
- conditions de reprise apres silence;
- attentes de formulation d'une reponse dans le contexte recent;
- notes quasi-narratives sur le tour ou la phase de relation;
- recap de contexte;
- patchwork de micro-preferences sur la facon de parler ensemble;
- contenu important mais simplement relationnel, situationnel ou processuel.

Regle forte:
- `mutable` n'est pas un sas general pour tout ce qui compte;
- `mutable` n'est pas un refuge pour ce qu'on ne sait pas encore classer;
- si un contenu n'est pas identitaire au sens fort, il doit sortir de `mutable`, meme s'il semble utile.

### 4.3 Ce qui doit sortir du canon identitaire, et ou cela doit aller

Doivent sortir du canon identitaire:
- preferences conversationnelles locales ou semi-locales;
- cadrages relationnels utiles mais non identitaires;
- conditions de reprise et de re-situation;
- notes de confort ou d'evitement dans une interaction donnee;
- traces de moment ou de phase dialogique;
- formulations d'attente qui dependent surtout d'un contexte de conversation.

Decision doctrinale explicite:
- la formule `dialogue context` est abandonnee ici, car trop flottante et trop proche d'un pseudo-concept vide;
- la formule retenue est `voie contextuelle hors canon`;
- `context_hints` en est deja aujourd'hui la premiere forme operative;
- le futur chantier ne doit donc pas inventer une deuxieme lane parallele, mais durcir, clarifier ou requalifier cette voie existante si son scope doit s'elargir.

Ce que `context_hints` est aujourd'hui:
- une lane non canonique deja active;
- une voie de rappel contextuel recent, distincte de l'identite forte;
- une selection gouvernee, bornee et injectee hors canon sous `[Indices contextuels recents]`;
- une voie aujourd'hui surtout centree sur des indices user-side `episodic` / `situation`;
- une voie qui aide la reprise contextuelle sans devenir canon identitaire.

Pourquoi cela ne suffit pas encore a fermer tout le hors canon:
- `context_hints` reste aujourd'hui une voie recente, budgetee et orientee injection prompt;
- il ne couvre pas encore a lui seul toute la taxonomie future du non-identitaire important;
- il ne tranche pas encore completement ce qui doit rester hint recent, ce qui pourrait relever plus tard d'un moment contextuel, et ce qui doit rester hors canon reflexif.

Regle pour la suite:
- toute evolution du hors canon identitaire doit partir de `context_hints` comme base existante;
- si une extension de scope devient necessaire, elle devra etre presentee comme durcissement, requalification ou versionnement de cette `voie contextuelle hors canon`;
- il est interdit de creer plus tard une couche concurrente qui redirait silencieusement `context_hints` sous un autre nom;
- le chantier `memory-contextual-moments` reste distinct: il traite des objets memoire asynchrones de signifiance dialogique, pas une simple lane de hints recents;
- `Frida from herself` reste distincte aussi: artefact reflexif, non destination par defaut des contenus expulses du canon identitaire.

### 4.4 Place future de `Frida from herself`

`Frida from herself` n'appartient pas au canon identitaire fort.

Sa place cible est:
- un artefact reflexif separe;
- potentiellement asynchrone;
- consultable et relisible;
- editable sous conditions a definir plus tard;
- non souverain sur le runtime identitaire canonique.

En consequence:
- ce qui sort du `mutable` ne doit pas etre deverse automatiquement dans `Frida from herself`;
- sinon on ne purifierait pas le contrat, on deplacerait seulement le depot d'impuretes;
- `Frida from herself` doit rester un lieu ou Frida peut se dire, pas un second mutable ni une poubelle du non-identitaire.

## 5. Sens fort de l'identite

Le contrat cible doit donner au mot `identite` un sens fort.

Definition retenue:
- l'identite parle de ce qu'est Frida et de ce qu'est Tof;
- elle parle de traits, de caractere, de posture profonde, de maniere d'etre, de continuite forte;
- elle ne parle pas d'abord de ce qu'ils preferent dans une interaction locale;
- elle ne parle pas d'abord de ce qu'il faut faire pour bien repondre;
- elle ne parle pas d'abord d'un confort de conversation.

Test de canonisation propose:
- si l'on retire la tache du moment, le silence recent, la forme de la demande et la situation locale, la phrase dit-elle encore quelque chose de fort sur ce qu'est Frida ou Tof ?
- si oui, elle peut etre candidate pour `static` ou `mutable`;
- si non, elle doit sortir du canon identitaire.

Par defaut, ces formulations ne sont pas identitaires:
- `Tof prefere que`
- `Frida aime bien quand`
- `il attend une reponse`
- `elle veut qu'on reprenne de telle facon`

Elles ne deviennent acceptables que si une justification rigoureuse montre qu'elles designent en fait:
- une orientation profonde et stable;
- une maniere d'etre durable;
- une continuite forte deja verifiee a travers le temps.

Regle de prudence:
- une phrase a la premiere personne ou en style narratif n'est pas identitaire par nature;
- une phrase chaleureuse, habitee ou relationnelle n'est pas identitaire par nature;
- une phrase utile n'est pas identitaire par nature.

## 6. Taille et format cibles

### 6.1 Statut de la taille actuelle

Etat observe au runtime live:
- `llm.mutable = 1537` caracteres;
- `user.mutable = 1555` caracteres;
- budget doctrinal actuel visible: cible `1500`, plafond dur `1650`.

Lecture retenue:
- les deux mutables sont deja a la lisiere du budget doctrinal;
- ils sont encore compatibles avec le runtime courant, mais ils ne constituent pas un argument pour augmenter le cap;
- avant purification du contrat, augmenter la taille serait une erreur: cela donnerait plus d'espace au melange identitaire/non-identitaire au lieu de le resorber.

Position explicite:
- ne pas augmenter la taille du `mutable` avant purification du contrat;
- traiter `1500 / 1650` comme un plafond de compatibilite du systeme actuel, pas comme une invitation a remplir davantage;
- viser apres purification un `mutable` sensiblement plus compact que l'etat courant.

### 6.2 Taille cible

Position proposee pour le futur contrat:
- `static` peut rester plus ample, car il porte le socle fort;
- `mutable` doit devenir court, dense et reserve aux vraies inflexions identitaires;
- cible doctrinale souhaitee pour `mutable`: environ `600` a `900` caracteres par sujet apres purification;
- toute baisse eventuelle des caps runtime devra etre traitee plus tard comme evolution versionnee, pas comme ajustement invisible.

### 6.3 Format cible

Le format cible ne doit pas etre un long recit libre.

Format recommande:
- texte narratif compact;
- sections internes stables;
- vocabulaire sobre;
- structure relisible pour l'operateur et pour une future validation metier.

Forme cible suggeree:
- `noyau`
- `posture`
- `continuite`
- `inflexion durable` pour le `mutable` seulement

Pourquoi ce choix:
- le runtime actuel injecte encore du texte;
- l'observabilite actuelle lit deja longueurs, presence et representations texte;
- un texte compact a sections internes stabilisees permet de purifier le contenu sans casser d'emblee les coutures existantes;
- un schema plus structure pourra venir plus tard, mais seulement avec versionnement explicite.

## 7. Observabilite a preserver explicitement

La future refonte ne doit surtout pas casser ce qui suit.

### 7.1 Lecture operateur et read-model

Doivent rester lisibles:
- la lecture `static`;
- la lecture `mutable`;
- la lecture `legacy_fragments`;
- la lecture `evidence`;
- la lecture `conflicts`.

Invariants a preserver:
- `GET /api/admin/identity/read-model` doit continuer a dire vrai sur ces couches;
- `GET /api/admin/identity/runtime-representations` doit continuer a distinguer base structuree et texte compile injecte;
- `/identity` et `/hermeneutic-admin` doivent rester exploitables et coherents avec ces contrats;
- l'operateur ne doit jamais perdre la capacite de comprendre ce qui est canonique actif, ce qui est legacy visible et ce qui est compile pour le runtime.

### 7.2 Events et diagnostics

Ne doivent pas etre casses:
- `identities_read`;
- `identity_write`;
- `identity_mutable_rewrite`;
- `identity_mutable_rewrite_apply`;
- `identity_mode_apply`.

Regle de compatibilite:
- si le contrat identitaire change, les events existants doivent soit continuer a signifier quelque chose de stable, soit etre versionnes explicitement;
- il ne faut pas muter silencieusement la semantique d'un event deja exploite dans `/log` ou les surfaces admin.

Regle de redaction a preserver:
- rester en compact-only;
- continuer a exposer compteurs, drapeaux de presence, longueurs, budgets, reason codes, flags de validation;
- ne pas recommencer a exposer du texte brut identitaire dans les logs.

### 7.3 Versionnement futur obligatoire

Si le futur contrat ajoute une couche nouvelle ou requalifie le `mutable`:
- traiter cela comme un sujet de compatibilite;
- prevoir un versionnement explicite des read-models et/ou schemas;
- ne pas le faire comme un petit refactor invisible.

En particulier:
- `identity_input_schema_version`;
- `read_model_version`;
- `representations_version`;
- et toute nouvelle couche hors canon identitaire devra etre geree comme contrat, pas comme detail interne.

## 8. Positionnement de `Frida from herself`

### 8.1 Ce que ce brouillon est

`Frida from herself` est une piste pour un artefact ou Frida pourrait dire quelque chose d'elle-meme:
- sur sa maniere de dire;
- sur ses inflexions;
- sur ce a quoi elle tient;
- sur certains contrats du dire;
- avec datation, revisabilite et prudence.

### 8.2 Ce qu'il n'est pas

Ce n'est pas:
- le canon identitaire fort;
- une reecriture directe de `llm.mutable`;
- une nouvelle source active d'injection;
- un receptacle automatique pour les contenus expulses du `mutable`.

### 8.3 Pourquoi il ne doit pas absorber trop tot le contenu retire des mutables

Si l'on deverse trop tot dans `Frida from herself` tout ce qui sort du `mutable`:
- on recree une zone floue;
- on mele reflexivite, preferences, contrats relationnels et restes narratifs;
- on perd la clarification doctrinale cherchee par ce chantier;
- on donne trop tot a un artefact reflexif un poids qu'il n'a pas encore le droit d'avoir.

Position retenue:
- `Frida from herself` doit etre pensee comme module separe, probablement asynchrone, hors canon fort;
- sa relation future au canon identitaire ne pourra etre discutee qu'apres purification de `static` et `mutable`;
- aucune promotion automatique vers le canon n'est acceptable a ce stade.

## 9. Plan de travail futur, sans implementation dans ce lot

Ordre de travail recommande:

1. figer ce contrat doctrinal de separation;
2. auditer le contenu actuel de `llm.static`, `user.static`, `llm.mutable`, `user.mutable` ligne a ligne selon les nouvelles categories;
3. classer chaque bloc en `garder dans static`, `garder dans mutable`, `sortir du canon identitaire`, `laisser hors canon`, `candidat reflexif futur`;
4. durcir la `voie contextuelle hors canon` a partir de `context_hints` avant toute migration de contenu non identitaire;
5. seulement ensuite penser l'evolution versionnee des read-models, surfaces et schemas si elle devient necessaire;
6. seulement ensuite purifier le contenu reel statique/mutable;
7. seulement apres cette purification, rouvrir le chantier `Frida from herself`;
8. enfin, si besoin, traiter une evolution runtime versionnee du contrat identity.

Invariants de ce plan:
- aucun retour du legacy comme source active;
- aucun patch runtime avant clarification de compatibilite;
- aucune casse silencieuse de `/identity`, `/hermeneutic-admin`, `read-model`, `runtime-representations` et des events de diagnostic existants.

## 10. Decision doctrinale resumee

Decision principale:
- `identity` doit desormais parler de ce que Frida est et de ce que Tof est, au sens fort;
- `mutable` doit devenir une modulation identitaire compacte, pas un patchwork narratif;
- le hors canon identitaire doit partir de `context_hints` comme base existante, puis etre durci ou requalifie sans dupliquer cette lane;
- `Frida from herself` doit rester un artefact reflexif separe;
- l'observabilite identity existante est une contrainte dure de compatibilite, pas un detail de mise en oeuvre.
