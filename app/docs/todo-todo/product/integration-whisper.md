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

Quand un tour provient de l'oral, le LLM doit le savoir explicitement.

Mais ce marquage ne doit pas apparaitre dans le texte visible de l'utilisateur.
Il doit donc etre:
- cache en UI;
- structure dans le payload;
- exploitable par le pipeline hermeneutique et prompt.

Decision retenue:
- ajouter `input_mode="voice"` dans le payload de chat;
- persister ce mode dans `meta` du message utilisateur;
- injecter un petit bloc systeme discret quand `input_mode=voice`.

Ce bloc doit rappeler que le dernier tour provient d'une transcription orale et que:
- hesitations;
- repetitions;
- ponctuation faible;
- relachement de formulation;

peuvent etre des effets d'oralite et ne doivent pas etre sur-interpretes comme baisse de rigueur, contradiction ou consigne stylistique.

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

Le `user_turn_input` doit recevoir l'information `input_mode` pour que le systeme sache que le tour courant provient d'une transcription orale.

### Prompt systemique

Un petit guard block conditionnel doit etre injecte seulement pour les tours `voice`.
Il ne doit pas changer la voix globale de Frida, mais seulement la lecture du tour present.

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
- memoire specifique du signal audio brut.

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

## Decision d'implementation pour le futur lot code

Si ce TODO est execute, la priorite d'implementation doit etre:
1. route backend de transcription;
2. bouton micro frontend + capture audio;
3. reinjection du transcript dans la textarea;
4. ajout de `input_mode` dans `/api/chat`;
5. persistance `meta.input_mode`;
6. guard block systemique pour les tours oraux;
7. tests frontend/backend minimaux;
8. documentation runtime associee.
