# Integration Whisper

## Intention

Objectif: ajouter une saisie vocale simple dans Frida pour remplacer la frappe clavier sur un tour donne, sans changer la logique dialogique fondamentale du chat.

Le service Whisper ne devient pas une nouvelle surface de dialogue autonome.
Il sert uniquement a produire un texte transcrit qui rejoint ensuite le pipeline de chat existant comme si l'utilisateur l'avait ecrit, avec un marquage interne indiquant que le tour provient de l'oral.

Le gain vise est d'abord ergonomique:
- reduction de la friction de saisie;
- possibilite de nourrir Frida a l'oral;
- preservation du meme systeme de conversation, de memoire et d'enonciation.

## Principe directeur

La V1 doit rester la plus simple possible:
- enregistrement audio dans le navigateur;
- transcription par Whisper;
- injection du transcript dans la zone de saisie existante;
- correction eventuelle par l'utilisateur;
- envoi manuel via le flux `/api/chat` existant.

Donc:
- pas de TTS dans ce lot;
- pas de transcript live;
- pas d'auto-envoi;
- pas de nouvelle surface de chat;
- pas de transformation Markdown complexe.

Le transcript devient simplement le texte du draft courant.

## Decision produit retenue

### UX cible V1

Dans le composer du chat, ajouter un bouton micro a cote des controles existants.

Etats UX minimaux:
- `idle`: micro disponible;
- `recording`: micro actif, animation visible;
- `transcribing`: enregistrement termine, transcription en cours;
- `error`: echec micro ou transcription.

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
- apres insertion, le focus revient dans la textarea.

### Marquage dialogique obligatoire

Quand un tour provient de l'oral, le LLM final doit le savoir explicitement.

Mais ce marquage ne doit pas apparaitre dans le texte visible de l'utilisateur.
Il doit donc etre:
- cache en UI;
- structure dans le payload;
- exploitable par le pipeline hermeneutique et prompt.

Decision retenue:
- ajouter `input_mode="voice"` dans le payload de chat;
- garder `keyboard` comme defaut explicite pour les tours ecrits;
- persister ce mode dans `meta` du message utilisateur;
- deriver un axe interpretatif canonique `enunciation_mode = oral | ecrit` pour le tour courant.

## Doctrine `oral / ecrit`

### Principe hermeneutique

`oral / ecrit` ne doit pas etre traite comme une etiquette technique sans effet.
C'est une information interpretable par Frida.

Le systeme doit donc distinguer:
- `input_mode`
  - information de transport et de persistence (`voice` ou `keyboard`)
- `enunciation_mode`
  - lecture hermeneutique du tour (`oral` ou `ecrit`)

Le premier dit comment le texte est entre dans le systeme.
Le second dit comment Frida doit lire ce texte.

### Ce que signifie `oral`

Quand `enunciation_mode = oral`, Frida doit presumer plus fortement:
- des hesitations;
- des repetitions;
- des auto-corrections;
- une ponctuation faible ou absente;
- un relachement syntaxique;
- une parole exploratoire ou phatique;
- une moindre densite propositionnelle locale.

Autrement dit, a l'oral, le langage peut davantage accompagner, chercher, approcher, relancer ou soutenir sans formuler a chaque phrase une intention dense et stabilisee.

Le LLM ne doit donc pas sur-interpreter comme manque de rigueur:
- une phrase inachevee;
- une reprise;
- une redondance;
- une articulation faible;
- une formulation relachee.

### Ce que signifie `ecrit`

Quand `enunciation_mode = ecrit`, Frida doit presumer plus fortement:
- une formulation plus intentionnelle;
- une plus grande stabilite locale de la phrase;
- une plus grande densite semantique;
- une responsabilite plus forte de la formulation precise.

Cela ne veut pas dire que l'ecrit est toujours plus profond.
Cela veut dire que, par defaut, il est moins tolerant aux scories d'oralite et plus charge en intention de formulation.

### Effet doctrinal retenu

La formulation directrice a conserver est:
- a l'oral, la fonction phatique et exploratoire du langage est plus probable;
- a l'ecrit, l'intention discursive et la densite semantique sont presumees plus fortes.

Cette distinction doit etre active dans l'interpretation du tour, pas seulement stockee comme metadonnée.

## Position par rapport a la `stimmung`

La `stimmung` actuelle est un determinant affectif stabilise.
Son contrat canonique reste affectif.

Decision retenue pour cette feature:
- ne pas injecter `oral / ecrit` dans la taxonomie des `tones`;
- ne pas faire de `oral / ecrit` un sous-produit de la `stimmung` v1;
- ne pas melanger modalite d'enonciation et tonalite affective.

Donc, dans ce lot:
- `oral / ecrit` vit hors de la `stimmung`;
- l'information passe par `meta`, `user_turn_input` et un guard block systemique dedie.

Piste future possible, mais hors V1:
- ouvrir un determinant frere de la `stimmung`, par exemple `modalite_d_enonciation` ou `enunciation_mode`, si le systeme montre un vrai besoin doctrinal durable.

## Contrainte structurelle forte

Cette integration doit etre pensee comme une feature autonome.

Donc, dans le futur lot code, tout ce qui peut etre sorti dans un module dedie doit l'etre.
L'objectif est double:
- autonomie intellectuelle de la feature;
- impact physique minimal sur les gros fichiers existants.

Regle de mise en oeuvre:
- ne pas disperser la logique Whisper dans plusieurs fichiers centraux si un module dedie suffit;
- n'ajouter dans les fichiers existants que les coutures minimales necessaires;
- garder la logique metier de l'oral comme une feature optionnelle, non comme un nouveau coeur diffus du systeme.

### Consequence architecturale

Le futur lot code doit viser une separation de cette forme:
- module frontend dedie pour capture audio + etats UI + appel transcription;
- module backend dedie pour proxy Whisper + gestion d'erreurs + contrat de transcription;
- extension minimale du chat pour accepter `input_mode`;
- helper prompt dedie pour l'interpretation `oral / ecrit`.

Autrement dit:
- `app.js` ne doit pas absorber toute la feature;
- `server.py` ne doit pas contenir la logique Whisper autre que le wiring HTTP;
- `chat_service.py` ne doit pas devenir le lieu d'implementation principal de l'oralite;
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
- `app.js` doit seulement l'initialiser et brancher ses callbacks sur la textarea existante.

### 2. Backend Frida comme proxy simple

Frida ne doit pas exposer directement le service Whisper au navigateur dans cette V1.
Le plus simple est:
- frontend -> `/api/chat/transcribe`;
- backend Frida -> `platform-whisper-api`;
- retour JSON au frontend.

Interet:
- same-origin simple;
- pas de token Whisper expose au frontend;
- pas de CORS a ouvrir;
- observabilite Frida possible;
- contrat applicatif stable meme si le backend STT change plus tard.

Contrainte de modularite:
- la logique de transcription backend doit vivre dans un flow ou service dedie;
- la route HTTP dans `server.py` doit rester un simple point d'entree.

### 3. Service Whisper interne

Le backend Frida appelle le service interne deja disponible:
- `platform-whisper-api`
- endpoint `POST /v1/audio/transcriptions`

Le service est deja OpenAI-compatible pour la transcription audio.
La V1 Frida doit seulement l'utiliser proprement.

## Contrat d'interface propose

### Nouvelle route Frida

`POST /api/chat/transcribe`

Entree:
- `multipart/form-data`
- champ `file` obligatoire

Sortie succes:
- `ok: true`
- `text: <transcript>`
- `input_mode: "voice"`
- `language: "fr"`
- `backend: "whisper-cli"`

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

### Persistance conversationnelle

Le message utilisateur doit etre persiste avec:
- `meta.input_mode = "voice"` quand le tour vient de l'oral.

Le texte du message reste le transcript final visible.
Aucun prefixe visible du type `[oral]` ne doit etre ajoute au contenu utilisateur.

### Inputs hermeneutiques

Le `user_turn_input` doit recevoir l'information `input_mode` et exposer un `enunciation_mode` derive.

Forme cible minimale:
- `input_mode = voice | keyboard`
- `enunciation_mode = oral | ecrit`

### Prompt systemique

Un petit guard block conditionnel doit etre injecte seulement pour les tours `voice`.
Il ne doit pas changer la voix globale de Frida, mais seulement la lecture du tour present.

Il doit au minimum rappeler:
- que le tour courant provient d'une transcription orale;
- que les scories d'oralite ne doivent pas etre sur-interpretees;
- que la parole peut ici etre plus phatique, exploratoire ou approximative sans etre vide de sens.

## Configuration V1 retenue

La configuration Whisper reste backend et fixe dans ce lot.
Pas de nouvelle section admin.

Configuration cible minimale:
- `WHISPER_API_URL`
- `WHISPER_API_TOKEN` si necessaire
- `WHISPER_API_TIMEOUT_S`

Le service vise par defaut sur OVH est l'interne:
- `http://platform-whisper-api:9001`

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
- integration de `oral / ecrit` dans la `stimmung` canonique.

## Validation attendue

### UX
- le bouton micro apparait dans le composer;
- l'enregistrement est visible pendant la capture;
- l'arret declenche la transcription;
- le transcript remplit correctement la textarea;
- l'utilisateur peut corriger puis envoyer.

### Backend
- `/api/chat/transcribe` accepte un audio valide et renvoie un transcript;
- erreur propre si pas de micro / pas de fichier / timeout / backend indisponible.

### Chat
- `/api/chat` accepte `input_mode=voice`;
- le message user est persiste avec `meta.input_mode=voice`;
- le texte visible reste propre et non prefixe.

### Hermeneutique
- le tour oral est reconnu comme tel;
- Frida ajuste son interpretation du tour en tenant compte de l'oralite;
- les tours clavier restent inchanges.

### Architecture
- la feature reste concentree dans des modules dedies;
- les gros fichiers existants ne recoivent que des coutures minimales;
- aucune inflation opportuniste de `stimmung` ou des modules coeur n'est introduite.

## Decision d'implementation pour le futur lot code

Si ce TODO est execute, la priorite d'implementation doit etre:
1. module backend de transcription dedie;
2. route backend de transcription comme simple wiring;
3. module frontend dedie pour capture audio et etats UI;
4. bouton micro frontend + capture audio;
5. reinjection du transcript dans la textarea;
6. ajout de `input_mode` dans `/api/chat`;
7. derivation de `enunciation_mode` dans les inputs du tour utilisateur;
8. persistance `meta.input_mode`;
9. guard block systemique pour les tours oraux;
10. tests frontend/backend minimaux;
11. documentation runtime associee.
