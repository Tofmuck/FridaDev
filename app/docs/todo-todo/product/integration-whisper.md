# Integration Whisper

## Intention

Objectif: ajouter une saisie vocale simple dans Frida pour remplacer, sur un tour donne, la frappe clavier, sans ouvrir une seconde surface de dialogue et sans bouleverser le pipeline conversationnel existant.

Le service Whisper ne devient pas une nouvelle interface de conversation.
Il sert a produire un transcript temporaire qui reintegre ensuite le chat existant.

Le gain recherche est d'abord ergonomique:
- reduction de la friction de saisie;
- possibilite de nourrir Frida a l'oral;
- conservation du meme systeme de conversation, de memoire et d'enonciation.

## Statut des lots

- Lot 0: fait
- Lot 1 et la suite: ouverts

## Principe directeur

La V1 doit rester sobre:
- enregistrement audio dans le navigateur;
- transcription par Whisper;
- reinjection du transcript dans la zone de saisie existante;
- correction eventuelle par l'utilisateur;
- envoi manuel via `/api/chat`.

Donc:
- pas de TTS dans ce lot;
- pas de transcript live;
- pas d'auto-envoi;
- pas de nouvelle surface de chat;
- pas de transformation Markdown complexe;
- pas de stockage audio.

Le transcript devient le texte du draft courant.

## Decision produit retenue

### UX cible V1

Dans le composer du chat, ajouter un bouton micro a cote des controles existants.

Etats UX minimaux:
- `idle`: micro disponible;
- `recording`: micro actif, animation visible;
- `transcribing`: enregistrement termine, transcription en cours;
- `error`: echec micro ou transcription;
- `busy`: tour assistant deja en cours, capture desactivee.

Interaction cible:
1. clic micro -> demande permission navigateur + debut enregistrement;
2. clic micro une seconde fois -> fin enregistrement;
3. envoi du fichier audio a Frida;
4. recuperation du transcript;
5. insertion du transcript dans la textarea existante;
6. l'utilisateur peut corriger puis envoyer normalement.

Regles V1:
- duree max d'enregistrement: 60 secondes;
- si la textarea est vide, le transcript la remplit;
- si elle contient deja du texte, le transcript s'ajoute a la suite avec separation propre;
- apres insertion, le focus revient dans la textarea;
- si un stream assistant est deja en cours, la capture est bloquee ou clairement desactivee;
- les tracks micro doivent etre fermees proprement apres stop ou erreur.

### Mode d'entree visible seulement en interne

Quand un tour provient d'une capture vocale, Frida doit le savoir.

Mais cette information ne doit pas apparaitre dans le texte visible de l'utilisateur.
Elle doit donc etre:
- cachee en UI;
- structuree dans le payload;
- exploitable par le backend et par le LLM final.

Decision retenue:
- ajouter `input_mode="voice"` dans le payload de chat;
- garder `keyboard` comme defaut explicite pour les tours ecrits;
- persister ce mode dans `meta` du message utilisateur.

Important:
- `input_mode` est un fait de transport et de provenance;
- ce n'est pas, a lui seul, une verite hermeneutique forte sur le statut complet du tour;
- un draft vocal peut etre ensuite corrige, resserre ou recompose au clavier.

## Doctrine `oral / ecrit`

### Principe retenu

`oral / ecrit` ne doit pas etre traite comme une simple etiquette technique.
Mais il ne doit pas non plus devenir trop vite un nouvel objet canonique fort du systeme.

La bonne distinction pour cette V1 est:
- `input_mode`
  - information de transport et de persistence (`voice` ou `keyboard`)
- `orality_hint`
  - indice interpretatif local pour lire le tour courant avec plus ou moins de tolerance aux scories d'oralite

Autrement dit:
- `input_mode` dit comment le texte est entre dans le systeme;
- `orality_hint` dit seulement comment Frida peut ajuster sa lecture du tour present;
- la V1 ne pose pas encore une equivalence doctrinale dure `voice -> oral` et `keyboard -> ecrit`.

### Ce que permet l'indice d'oralite

Quand un tour provient d'une transcription vocale, Frida peut presumer plus fortement:
- des hesitations;
- des repetitions;
- des auto-corrections;
- une ponctuation faible ou absente;
- un relachement syntaxique;
- une parole exploratoire ou phatique;
- une moindre densite propositionnelle locale.

Le LLM ne doit donc pas sur-interpreter comme manque de rigueur:
- une phrase inachevee;
- une reprise;
- une redondance;
- une articulation faible;
- une formulation relachee.

### Ce que l'indice d'oralite ne doit pas faire

Il ne doit pas:
- devenir un nouvel axe canonique dur de `user_turn_input` en V1;
- requalifier tout tour `voice` comme oral au sens plein;
- faire oublier qu'un transcript vocal peut etre edite ensuite;
- devenir une permission de minimiser systematiquement la densite du message utilisateur.

### Formulation directrice retenue

La formulation a conserver est:
- a partir d'une transcription vocale, la fonction phatique et exploratoire du langage est plus probable;
- a partir d'une saisie clavier, l'intention discursive et la densite locale de formulation sont en moyenne plus stables;
- mais ces traits restent des indices faibles et revisables, pas des equivalences absolues.

## Position par rapport a la `stimmung`

La `stimmung` actuelle est un determinant affectif stabilise.
Son contrat canonique reste affectif.

Decision retenue pour cette feature:
- ne pas injecter `oral / ecrit` dans la taxonomie des `tones`;
- ne pas faire du mode d'entree un sous-produit de la `stimmung` v1;
- ne pas melanger modalite d'enonciation et tonalite affective.

Donc, dans ce lot:
- le signal vocal reste hors de la `stimmung`;
- l'information passe par `meta.input_mode`;
- un helper ou guard block dedie peut en tirer un indice interpretatif local pour le tour courant.

Piste future possible, mais hors V1:
- ouvrir un determinant frere de la `stimmung` ou un objet canonique distinct si un besoin doctrinal durable apparait vraiment.

## Contrainte structurelle revisee

Cette integration doit etre pensee comme une feature autonome **autant que possible**, mais sans se raconter qu'elle restera sans coutures.

L'objectif realiste est:
- autonomie intellectuelle de la feature;
- impact physique borne sur les gros fichiers existants;
- reconnaissance explicite du fait que certaines coutures seront inevitables.

Regle de mise en oeuvre:
- sortir dans des modules dedies tout ce qui peut l'etre proprement;
- n'ajouter dans les fichiers existants que les points de branchement necessaires;
- ne pas vendre une autonomie absolue que le depot actuel ne permet pas;
- garder la logique Whisper et la lecture locale de l'oral comme une feature optionnelle, non comme un nouveau coeur diffus du systeme.

### Consequence architecturale

Le futur lot code doit viser une separation de cette forme:
- module frontend dedie pour capture audio + etats UI + appel transcription;
- module backend dedie pour proxy Whisper + gestion d'erreurs + contrat de transcription;
- extension bornee du chat pour accepter `input_mode`;
- helper prompt dedie pour la lecture locale des tours issus de la voix.

Mais il faut assumer des coutures reelles dans:
- `app/web/app.js` pour le wiring du composer et du submit;
- `app/web/index.html` et `app/web/styles.css` pour charger proprement un helper frontend dedie et etendre un composer aujourd'hui pense pour `textarea + web + send`;
- `app/server.py` pour la nouvelle route HTTP;
- `app/core/chat_session_flow.py` pour lire `input_mode`;
- `app/core/chat_service.py` pour persister `meta.input_mode` et propager l'information utile;
- possiblement `app/core/chat_prompt_context.py` pour le bloc systemique conditionnel;
- possiblement l'observabilite si l'on veut suivre le mode d'entree.

Autrement dit:
- `app.js` ne doit pas absorber toute la feature, mais il sera quand meme touche;
- `server.py` doit rester un simple point d'entree, mais il sera quand meme etendu;
- `chat_service.py` ne doit pas devenir le lieu principal de l'oralite, mais il recevra un minimum de plomberie;
- `stimmung` ne doit pas etre elargie opportunistement pour porter cette distinction.

## Architecture cible minimale

### 1. Frontend navigateur

Le frontend web du chat reste la surface de capture.
Il doit:
- utiliser `getUserMedia` pour le micro;
- utiliser `MediaRecorder` pour produire un blob audio;
- envoyer ce blob a une route Frida same-origin dediee;
- recevoir le transcript JSON;
- remplir la textarea existante;
- transmettre ensuite `input_mode="voice"` au moment du vrai `POST /api/chat`.

Contrainte de modularite:
- la logique de capture et de transcription frontend doit vivre dans un module dedie;
- `app.js` doit surtout deleguer l'etat et l'appel STT a ce module, mais il faudra assumer un vrai seam de bootstrapping dans un frontend qui charge aujourd'hui un seul script classique;
- selon le choix retenu, cela pourra demander soit un script supplementaire charge depuis `index.html`, soit une petite refonte du bootstrap de `app.js`;
- l'ajout du micro n'est pas un simple bouton "gratuit": le composer actuel devra etre explicitement etendu cote HTML/CSS;
- il faut prevoir explicitement les types MIME acceptes, le nettoyage des tracks micro, l'etat `busy`, le cancel et les erreurs permission navigateur.

### 2. Backend Frida comme proxy simple

Frida ne doit pas exposer directement le service Whisper au navigateur dans cette V1.
Le plus simple est:
- frontend -> `/api/chat/transcribe`;
- backend Frida -> `platform-whisper-api`;
- retour JSON au frontend.

Interet:
- same-origin simple;
- pas de cle Whisper exposee au frontend;
- pas de CORS a ouvrir;
- observabilite Frida possible;
- contrat applicatif stable meme si le backend STT change plus tard.

Contrainte de modularite:
- la logique de transcription backend doit vivre dans un flow ou service dedie;
- la route HTTP dans `server.py` doit rester un simple point d'entree;
- il faut assumer quand meme un petit passage par la session/app chat pour `input_mode`.

### 3. Service Whisper interne

Le backend Frida appelle le service interne deja disponible:
- `platform-whisper-api`
- endpoint `POST /v1/audio/transcriptions`

Etat reel du runtime actuel:
- authentification potentielle via `WHISPER_API_KEY` et `WHISPER_AUTH_MODE`;
- reponse minimale standard: `{"text": "..."}`

La V1 Frida peut enrober cette reponse dans son propre contrat, mais elle ne doit pas raconter un contrat Whisper different du runtime reel.

## Contrat d'interface propose

### Nouvelle route Frida

`POST /api/chat/transcribe`

Entree:
- `multipart/form-data`
- champ `file` obligatoire

Sortie succes minimale:
- `ok: true`
- `text: <transcript>`
- `input_mode: "voice"`

Champs optionnels si Frida choisit de les exposer:
- `backend`
- `language`

Sorties erreur minimales:
- `400` si fichier absent ou vide;
- `502` si Whisper echoue;
- `504` si Whisper timeoute.

### Extension de `/api/chat`

Le payload JSON du chat accepte un champ optionnel:
- `input_mode`

Valeurs V1:
- `keyboard`
- `voice`

Defaut:
- `keyboard`

## Integration au pipeline Frida

### Session / orchestration

`resolve_chat_session()` doit lire `input_mode` en plus de `message`, `stream` et `web_search`.

Attendu minimal:
- valider les valeurs admises `keyboard | voice`;
- normaliser l'absence vers `keyboard`;
- renvoyer cet etat au service chat sans disperser la validation dans plusieurs couches.

### Persistance conversationnelle

Le message utilisateur doit etre persiste avec:
- `meta.input_mode = "voice"` quand le draft envoye provient initialement de la voix.

Le texte du message reste le transcript final visible.
Aucun prefixe visible du type `[oral]` ne doit etre ajoute au contenu utilisateur.

### Lecture hermeneutique

Dans cette V1, on ne fait pas de `enunciation_mode = oral | ecrit` un nouvel objet canonique dur.

Le bon niveau est plus modeste:
- `input_mode` est persiste et circule;
- un helper prompt ou guard block conditionnel peut deriver un indice interpretatif faible pour le tour courant;
- cet indice n'a pas vocation a redefinir tout `user_turn_input` ni toute la doctrine d'enonciation du systeme.

Point de doctrine operatoire important:
- `meta.input_mode` seul n'a aucun effet direct sur le LLM final;
- dans l'etat actuel du depot, le LLM principal ne voit que ce qui est injecte textuellement dans le prompt augmente;
- la persistence en `meta` sert la trace, la relecture et l'observabilite, mais pas l'interpretation du tour sans injection explicite.

### Prompt systemique

Un petit guard block conditionnel peut etre injecte seulement pour les tours `voice`.
Il ne doit pas changer la voix globale de Frida, mais seulement la lecture du tour present.

Consequence structurelle:
- si aucun bloc conditionnel n'est injecte, `input_mode` reste une metadonnee backend sans effet interpretatif sur la reponse;
- le seam naturel pour cet effet est un helper dedie branche dans `app/core/chat_prompt_context.py`, plutot qu'une hypothese implicite sur la persistence seule.

Il doit au minimum rappeler:
- que le tour courant provient d'une transcription vocale;
- que les scories d'oralite ne doivent pas etre sur-interpretees;
- qu'un tour vocal peut rester phatique, exploratoire ou approximatif sans etre vide de sens;
- qu'un tour vocal ensuite edite peut etre partiellement mixte, donc qu'il faut lire ce signal avec souplesse.

## Configuration V1 retenue

La configuration Whisper reste backend et fixe dans ce lot.
Pas de nouvelle section admin.

Configuration cible minimale cote Frida:
- `WHISPER_API_URL`
- `WHISPER_API_TIMEOUT_S`
- eventuellement un branchement vers `WHISPER_API_KEY` si le backend l'exige

Etat reel du depot Frida au moment de ce TODO:
- le lot 0 a deja introduit le seam `WHISPER_API_URL`, `WHISPER_API_TIMEOUT_S` et `WHISPER_API_KEY` dans `app/config.py`;
- les usages backend doivent continuer a consommer ces valeurs via `config`, pas via des `os.getenv` disperses;
- toute extension future de ce seam devra mettre a jour la documentation operateur associee dans le meme cycle.

Le service vise par defaut sur OVH est l'interne:
- `http://platform-whisper-api:9001`

Le document Frida doit rester aligne avec le runtime Whisper reel:
- auth mode cote service;
- nom de cle cote service;
- forme minimale de reponse.

## Hors-scope explicite

Hors-scope de cette V1:
- synthese vocale de Frida;
- lecture audio de la reponse;
- transcript streaming en temps reel;
- diarisation;
- segmentation phrase par phrase;
- auto-envoi apres transcription;
- configuration admin Whisper;
- stockage des fichiers audio;
- memoire specifique du signal audio brut;
- integration de `oral / ecrit` dans la `stimmung` canonique;
- creation immediate d'un nouvel objet canonique `enunciation_mode`.

## Validation attendue

### UX
- le bouton micro apparait dans le composer;
- l'enregistrement est visible pendant la capture;
- l'arret declenche la transcription;
- le transcript remplit correctement la textarea;
- l'utilisateur peut corriger puis envoyer;
- pendant un stream assistant deja en cours, le comportement est explicite et stable;
- les erreurs permission micro, timeout et transcription n'abiment pas le draft existant.

### Backend
- `/api/chat/transcribe` accepte un audio valide et renvoie un transcript;
- erreur propre si pas de micro / pas de fichier / timeout / backend indisponible;
- la route Frida reste un simple proxy applicatif sans exposition directe de secrets.

### Chat
- `/api/chat` accepte `input_mode=voice`;
- le message user est persiste avec `meta.input_mode=voice`;
- le texte visible reste propre et non prefixe;
- le comportement par defaut clavier reste inchangé.

### Interpretation
- le tour issu de la voix est reconnu comme tel;
- Frida ajuste sa lecture locale du tour en tenant compte de l'oralite;
- cet ajustement reste un indice faible, non une requalification doctrinale totale du message.

### Architecture
- la feature reste principalement concentree dans des modules dedies;
- les gros fichiers existants ne recoivent que des coutures bornees, pas zero coutures;
- aucune inflation opportuniste de `stimmung` ou des modules coeur n'est introduite.

## Decision d'implementation pour le futur lot code

Si ce TODO est execute, la priorite d'implementation doit etre:
1. module backend de transcription dedie;
2. route backend de transcription comme simple wiring;
3. module frontend dedie pour capture audio et etats UI;
4. bouton micro frontend + capture audio;
5. reinjection du transcript dans la textarea;
6. gestion UX des etats `recording`, `transcribing`, `error`, `busy`;
7. ajout de `input_mode` dans `/api/chat`;
8. persistance `meta.input_mode`;
9. helper prompt ou guard block dedie pour les tours `voice`;
10. observabilite minimale du mode d'entree si utile;
11. tests frontend/backend minimaux;
12. documentation runtime associee.
