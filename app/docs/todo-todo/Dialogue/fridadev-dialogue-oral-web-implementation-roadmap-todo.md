# FridaDev — mode Dialogue oral Web — roadmap d'implémentation

> **Pour l'agent VS Code :** sous-compétence requise : utiliser
> `superpowers:executing-plans` et exécuter cette roadmap lot par lot. Ne jamais
> commencer le lot suivant avant revue explicite du précédent par Tof.

**But :** transformer le squelette mobile Figma déjà livré en une boucle orale
semi-duplex fiable sur iPhone : parole détectée localement, transcription en
ligne, pipeline Frida canonique, lecture de la réponse, puis réarmement.

**Architecture :** le navigateur tient uniquement le microphone, le VAD,
l'enregistrement et la lecture audio. Deux frontières backend étroites portent
le STT et le TTS vers OpenRouter. La transcription rejoint exactement le chemin
de soumission actuel du chat ; la réponse lue est exclusivement la réponse
finale canonique déjà produite et persistée par Frida. Aucun second pipeline
dialogique n'est créé.

**Socle technique :** Flask et Python, JavaScript navigateur sans framework,
`MediaRecorder`, VAD Silero local via `@ricky0123/vad-web`, endpoints audio
OpenRouter, tests `unittest`, tests Node et smoke Chromium existant, puis canari
manuel Safari sur iPhone 11.

**Contrat :**
[`fridadev-dialogue-oral-web-todo.md`](fridadev-dialogue-oral-web-todo.md).

## État initial autoritatif — 9 septembre 2026

- [x] La composition Figma mobile sombre `106:4` est intégrée.
- [x] Le contrôleur visuel fermé possède les états `listening`,
  `user_speaking`, `transcribing`, `thinking`, `tts_speaking`, `paused` et
  `error`.
- [x] Les animations synthétiques sont prouvées sans capacité audio.
- [x] Le VAD Silero a distingué la parole des bruits non articulés sur l'iPhone.
- [x] `microsoft/mai-transcribe-2` a été validé sur parole française réelle.
- [x] `microsoft/mai-voice-2-flash`, voix
  `fr-FR-Soleil:MAI-Voice-2`, a été validé dans Safari réel.
- [x] Le bouton produit reste désactivé.
- [x] La frontière backend STT D1 existe sans consommateur frontend et reste
  inactive dans le produit.
- [ ] Aucun microphone, VAD produit, enregistrement navigateur ou TTS n'est
  raccordé au produit.

Le commit de référence du squelette est
`0b190aeb485262f8c813f048740e0b2774d58a8b`.

## Contraintes globales

- Chaque lot exige un `GO` explicite propre. Il commence par `pwd`,
  `git rev-parse --show-toplevel`, la lecture de `AGENTS.md`, puis la preuve
  d'une branche, d'un upstream et d'un worktree propres.
- D1 ne commence qu'après décision explicite de lever l'invariant de
  consolidation pour cette extension audio strictement bornée et inscription
  de cette exception dans `AGENTS.md`. La rédaction de cette roadmap ne vaut
  pas cette autorisation.
- Le contrat OpenRouter courant est relu avant le premier appel audio :
  [Speech-to-Text](https://openrouter.ai/docs/guides/overview/multimodal/stt)
  et [Text-to-Speech](https://openrouter.ai/docs/guides/overview/multimodal/tts).
  Le STT utilise `/api/v1/audio/transcriptions`; le TTS utilise
  `/api/v1/audio/speech`. Ne pas les déduire de Chat Completions.
- Les choix V1 sont fixes tant qu'aucun fait nouveau ne les invalide : VAD
  Silero local, `microsoft/mai-transcribe-2`,
  `microsoft/mai-voice-2-flash`, `fr-FR-Soleil:MAI-Voice-2`.
- Aucun benchmark général, aucune nouvelle sélection de voix et aucun fallback
  automatique ne sont autorisés.
- L'audio utilisateur ne transite jamais par OpenRouter directement depuis le
  navigateur. Le navigateur appelle seulement Frida ; la clé OpenRouter reste
  côté serveur.
- Aucun audio brut, transcript, prompt, réponse, token, credential ou URL
  sensible n'est ajouté aux logs. L'observabilité reste content-free : état,
  durée, taille, format, statut et reason code fermés.
- Le mode V1 est semi-duplex. Avant d'armer le microphone, Frida neutralise sa
  propre lecture et demande la pause des médias contrôlables. Le microphone
  reste désarmé pendant le STT, le traitement et le TTS.
- La vue Dialogue ne montre pas le transcript. Le transcript accepté devient
  toutefois un message utilisateur normal, visible dans le fil après sortie du
  mode.
- Le résultat STT ne contourne ni `chatRequestInFlight`, ni la sauvegarde, ni
  Stimmung, Memory, Identity, Validation, outils ou final lock.
- Le TTS ne lit jamais un brouillon ni un fragment streaming : seulement le
  texte final canonique reçu du pipeline actuel.
- Les limites suivantes sont des valeurs initiales à verrouiller par test : un
  seul blob par énoncé, `24 000 000` octets maximum pour le fichier STT et
  `25 000 000` octets pour son corps multipart, 300 secondes maximum,
  température `0`, langue `fr`, réponse STT JSON, sortie TTS `mp3` en V1.
- Une erreur ne réarme pas automatiquement une boucle infinie. Elle place la
  session en `error`, conserve le chat canonique et laisse à Tof le choix de
  reprendre ou de quitter.
- Toute édition du dépôt se termine par tests ciblés, contre-audit,
  documentation, commit, push, puis preuve `HEAD = upstream`, divergence `0/0`
  et worktree propre.
- Un lot backend ou frontend runtime n'est dit livré qu'après reconstruction
  ciblée de `platform-fridadev`, contrôle HTTP, health, restart, OOM, empreintes
  checkout/conteneur et invariance des voisins.
- Un lot tests/docs-only ne déclenche ni rebuild ni restart.

## Décomposition des fichiers

Les noms ci-dessous fixent les responsabilités. Si le HEAD courant impose un
déplacement mineur, l'agent le justifie avant édition et conserve les mêmes
frontières.

- `app/core/dialogue_stt_service.py` : validation de l'audio et appel OpenRouter
  STT ; aucun état de session.
- `app/core/dialogue_tts_service.py` : validation du texte canonique et appel
  OpenRouter TTS ; aucun état de session.
- `app/chat_dialogue_audio_routes.py` : deux routes Flask audio, limites HTTP et
  mapping content-free des erreurs.
- `app/web/dialogue/dialogue_vad_recorder.js` : microphone, VAD, segmentation et
  production d'un blob unique.
- `app/web/dialogue/dialogue_audio_client.js` : transport navigateur vers les
  deux routes Frida et consommation sûre du flux audio.
- `app/web/dialogue/dialogue_session_controller.js` : machine d'orchestration
  semi-duplex et raccord au contrôleur visuel existant.
- `app/web/chat_dialogue_mode.js` : reste la projection visuelle pure ; aucune
  requête réseau ni possession du microphone.
- `app/web/app.js` : wiring minimal vers l'unique soumission chat existante.

---

## Lot D0 — squelette visuel Figma

**Statut : fermé et livré.**

La composition, les assets, les safe areas, les contrôles Pause/Terminer et la
vérité des animations sont déjà présents. D0 n'autorise aucune capacité audio.

---

## Lot D1 — contrat OpenRouter et frontière STT

**Statut : fermé, poussé et livré par reconstruction ciblée du seul service
applicatif. D2 reste non commencé.**

**Livrable :** une route STT Frida hermétique, bornée et testée, sans encore
être appelée par l'interface.

**Fichiers :**

- Créer : `app/core/dialogue_stt_service.py`
- Créer : `app/chat_dialogue_audio_routes.py`
- Modifier : `AGENTS.md` pour l'exception audio explicitement décidée avec Tof
- Modifier : `app/server.py`
- Modifier : `app/config.py`
- Modifier : `app/config.example.py`
- Créer : `app/tests/unit/chat/test_dialogue_stt_service.py`
- Créer : `app/tests/integration/chat/test_chat_dialogue_audio_routes.py`
- Modifier : `app/docs/todo-todo/Dialogue/fridadev-dialogue-oral-web-todo.md`
- Modifier : cette roadmap

**Interfaces :**

- Consomme : clé OpenRouter résolue par le mécanisme serveur existant.
- Produit : `transcribe_dialogue_audio(audio_bytes, mime_type) -> DialogueSttResult`
  avec `ok`, `text`, `reason_code`, `http_status`, `duration_ms`.
- Produit : `POST /api/chat/dialogue/transcribe`, multipart avec un seul champ
  `audio`, réponse JSON content-free hors `text` lorsqu'elle réussit.

- [x] **D1.1 — Revalider la documentation fournisseur**

  Après inscription de l'exception explicitement autorisée dans `AGENTS.md`,
  lire les pages OpenRouter STT, modèles, prix, confidentialité et journalisation.
  Consigner seulement les écarts par rapport au contrat du 9 septembre. Arrêter
  D1 si le modèle, l'endpoint, `language=fr`, `temperature=0`, le format reçu ou
  la limite d'upload ne correspondent plus.

- [x] **D1.2 — Écrire les tests rouges du service**

  Prouver avant le code : succès JSON, transcript vide légitime, timeout,
  erreur transport, 401/403/429/5xx, JSON invalide, champ texte absent, type
  incorrect, audio vide, MIME refusé, dépassement de `24 000 000` octets pour
  le fichier et de `25 000 000` octets pour le corps multipart. Le fake inspecte
  modèle, langue et température sans réseau.

  Exécuter :

  ```bash
  python -m unittest tests.unit.chat.test_dialogue_stt_service
  ```

  Attendu : échec causal parce que le service n'existe pas.

- [x] **D1.3 — Implémenter le service minimal**

  Envoyer exactement un fichier audio à l'endpoint transcription dédié.
  Conserver la clé et la réponse brute hors logs. Refuser localement toute
  entrée invalide. Ne pas ajouter de retry ni de fallback.

- [x] **D1.4 — Écrire puis satisfaire les tests rouges de route**

  La route accepte un seul fichier, applique les limites avant appel fournisseur,
  renvoie `200` avec le transcript confirmé, `422` pour l'entrée invalide,
  `502` pour une réponse fournisseur invalide et `503` pour une indisponibilité
  bornée. Aucun résultat d'échec ne contient d'audio, de transcript partiel ou
  de texte d'exception.

  Exécuter :

  ```bash
  python -m unittest \
    tests.unit.chat.test_dialogue_stt_service \
    tests.integration.chat.test_chat_dialogue_audio_routes
  ```

- [x] **D1.5 — Contre-auditer, documenter, commit et push**

  Vérifier que `/api/chat/transcribe` et le Whisper local restent inchangés,
  que la nouvelle route n'est appelée par aucun frontend, que le réseau est
  absent des tests et que le modèle n'est pas rendu éditable dans une surface
  Admin opportuniste.

  Commit attendu : `feat(dialogue): add bounded OpenRouter transcription`.

**Stop D1 :** arrêter si la réponse fournisseur ne prouve pas un transcript
final unique ou si les limites réelles ne peuvent pas être appliquées avant
l'envoi.

### Preuves D1 — 9 septembre 2026

- baseline : `main`, HEAD/upstream
  `c591909c93b2e31b7e7d11ecb89be9c8afe39ad9`, divergence `0/0`, worktree
  propre avant édition ;
- rouge initial hermétique : import du service absent et route non enregistrée,
  sans réseau ; la commande hôte documentée a dû être adaptée au conteneur de
  test parce que `python` n'existe pas dans le PATH et que `/usr/bin/python3`
  ne possède pas Werkzeug ;
- vert D1 : `18/18` tests service/route, dont le rejet pré-parsing d'un corps
  sans taille déclarée afin de préserver la borne D1 propre ;
- voisins Whisper : `22/22` ;
- résolution OpenRouter, carte golden et garde multipart : `46/46` ;
- contrats config/admin voisins : `11/11` ;
- mutation contrôlée : neutraliser la borne fichier pré-transport fait échouer
  `test_file_limit_is_enforced_before_transport`; après restauration, le
  SHA-256 du service retrouve exactement sa valeur préalable et la suite D1
  repassent au vert ;
- toutes ces commandes ont utilisé un conteneur jetable `--network none`, le
  checkout monté en lecture seule et `/tmp` en `tmpfs` ; aucun appel OpenRouter
  réel n'a été effectué ;
- commit applicatif poussé :
  `7402185c944e45c106d7952715aa473084091079` ;
- livraison sans pull implicite par `build --pull=false`, puis recréation
  `--no-deps --force-recreate` du seul service `fridadev` ; l'image livrée est
  `sha256:9ad85d835247a953760638fa532425c722cb5f20f72331f215f61f3509117979`
  et l'image précédente reste récupérable sous le tag
  `platform-fridadev-app:rollback-d1-20260909T143502Z` ;
- `platform-fridadev` est `running`, `healthy`, restart `0`, OOM `false` ; les
  31 voisins conservent strictement identité et état ;
- HTTP interne `200`, rejet local hermétique de la route D1 en `422`, empreintes
  des cinq fichiers runtime identiques entre checkout et conteneur, et zéro
  ligne récente `ERROR`, `CRITICAL` ou `Traceback` depuis le démarrage.

---

## Lot D2 — frontière TTS et flux audio

**Livrable :** une route TTS Frida qui retourne uniquement les octets audio
confirmés de la voix Soleil, sans encore activer le mode produit.

**Fichiers :**

- Créer : `app/core/dialogue_tts_service.py`
- Modifier : `app/chat_dialogue_audio_routes.py`
- Modifier : `app/config.py`
- Modifier : `app/config.example.py`
- Créer : `app/tests/unit/chat/test_dialogue_tts_service.py`
- Modifier : `app/tests/integration/chat/test_chat_dialogue_audio_routes.py`
- Modifier : contrat et roadmap Dialogue

**Interfaces :**

- Consomme : un texte final canonique non vide.
- Produit : `synthesize_dialogue_speech(text) -> DialogueTtsResult` avec
  `ok`, `audio_bytes`, `content_type`, `reason_code`, `http_status`,
  `duration_ms`.
- Produit : `POST /api/chat/dialogue/speech`, corps JSON `{ "text": "…" }`,
  réponse audio `audio/mpeg` en succès.

- [ ] **D2.1 — Revalider le contrat TTS OpenRouter**

  Vérifier endpoint, modèle, voix, format, limite de texte, prix, délai et
  politique de données. Arrêter si la voix exacte n'est plus acceptée ou si la
  réponse n'est plus un flux d'octets audio documenté.

- [ ] **D2.2 — Écrire les tests rouges service et route**

  Couvrir : MP3 confirmé, texte vide, texte hors borne, voix rejetée, audio vide,
  mauvais content-type, timeout, transport, 401/403/429/5xx et absence de fuite
  du texte dans les erreurs.

  Exécuter :

  ```bash
  python -m unittest \
    tests.unit.chat.test_dialogue_tts_service \
    tests.integration.chat.test_chat_dialogue_audio_routes
  ```

- [ ] **D2.3 — Implémenter le service et la route**

  Appeler `/api/v1/audio/speech` avec le modèle V1, la voix Soleil et `mp3`.
  Propager les octets seulement après succès HTTP et validation du content-type.
  Ne pas conserver l'audio sur disque et ne pas ajouter de cache.

- [ ] **D2.4 — Vérifier les deux frontières ensemble**

  Exécuter les suites D1/D2, les contrats HTTP voisins et un test prouvant que
  STT et TTS ne partagent ni réponse, ni payload, ni traitement d'erreur ambigu.

- [ ] **D2.5 — Contre-auditer, documenter, commit et push**

  Commit attendu : `feat(dialogue): add bounded OpenRouter speech`.

**Stop D2 :** aucun appel provider live n'est nécessaire. Si la voix ne peut
être fixée explicitement, ne pas substituer silencieusement une autre voix.

---

## Lot D3 — VAD et enregistreur local sur Safari

**Livrable :** l'interface peut ouvrir une session locale de test, détecter une
parole et produire un blob borné ; elle n'appelle encore ni STT ni chat.

**Fichiers :**

- Créer : `app/web/dialogue/dialogue_vad_recorder.js`
- Ajouter : distribution locale épinglée de `@ricky0123/vad-web` et ses assets
  strictement nécessaires sous `app/web/vendor/dialogue-vad/`
- Modifier : `app/web/index.html`
- Modifier : `app/web/app.js`
- Créer : `app/tests/unit/frontend_chat/test_dialogue_vad_recorder_module.js`
- Modifier : `app/tests/integration/frontend_browser/test_frontend_browser_smoke.js`
- Modifier : contrat et roadmap Dialogue

**Interfaces :**

- Produit : `createDialogueVadRecorder(options)` avec `arm()`, `pause()`,
  `resume()`, `stop()` et événements `speech-start`, `speech-end`, `blob`,
  `error`.
- L'événement `blob` porte un seul `Blob`, son MIME et sa durée ; jamais une
  transcription.

- [ ] **D3.1 — Écrire les tests rouges de cycle de vie**

  Avec fakes explicites de `getUserMedia`, VAD et `MediaRecorder`, prouver :
  aucun accès micro avant geste utilisateur, armement unique, bruit rejeté,
  parole reconnue, silence de fin, un blob unique, arrêt à la durée/poids
  maximum, pistes arrêtées, double appui sans double recorder et cleanup après
  erreur.

  Exécuter :

  ```bash
  node --test app/tests/unit/frontend_chat/test_dialogue_vad_recorder_module.js
  ```

- [ ] **D3.2 — Implémenter la machine locale**

  Sélectionner le premier type réellement supporté par
  `MediaRecorder.isTypeSupported()` dans une allowlist explicite Safari. Le VAD
  ferme l'énoncé après son événement de fin ; aucune minuterie basée sur le seul
  volume n'est ajoutée. Les limites du blob sont appliquées avant toute sortie.

- [ ] **D3.3 — Neutraliser les médias contrôlables avant l'écoute**

  Suspendre le lecteur TTS possédé par Frida et les éléments audio/vidéo du
  document avant `arm()`. Ne jamais prétendre contrôler une radio automobile ou
  une application tierce que Safari ne peut pas piloter. Si un média local ne
  peut pas être mis en pause, l'armement échoue honnêtement.

- [ ] **D3.4 — Prouver l'intégration visuelle sans réseau**

  Le smoke Chromium ouvre le mode par son harnais, simule parole et silence,
  vérifie `listening → user_speaking → listening`, la vérité des animations,
  Pause, Terminer, fermeture, safe areas et absence de fetch.

- [ ] **D3.5 — Contre-auditer, documenter, commit et push**

  Vérifier qu'aucun CDN runtime, second VAD, transcript visible, requête
  fournisseur ou réarmement implicite n'a été ajouté.

  Commit attendu : `feat(dialogue): add local voice activity capture`.

**Stop D3 :** un échec de permission, d'initialisation VAD ou de codec doit
rester visible et récupérable ; ne pas contourner le VAD par un seuil de volume.

---

## Lot D4 — raccord STT au pipeline chat canonique

**Livrable :** une parole produit un message utilisateur normal et traverse le
pipeline Frida existant une seule fois. Le TTS n'est pas encore enchaîné.

**Fichiers :**

- Créer : `app/web/dialogue/dialogue_audio_client.js`
- Créer : `app/web/dialogue/dialogue_session_controller.js`
- Modifier : `app/web/app.js`
- Modifier : `app/web/chat_dialogue_mode.js` seulement si un état visuel manque
- Créer : `app/tests/unit/frontend_chat/test_dialogue_audio_client_module.js`
- Créer : `app/tests/unit/frontend_chat/test_dialogue_session_controller_module.js`
- Modifier : `app/tests/integration/frontend_browser/test_frontend_browser_smoke.js`
- Modifier : contrat et roadmap Dialogue

**Interfaces :**

- `dialogueAudioClient.transcribe(blob) -> Promise<string>`.
- `dialogueSessionController.start()` possède le cycle mais reçoit par injection
  `submitCanonicalChatMessage(text, inputMode)`.
- `inputMode` vaut `dialogue`; le submit réutilise la même fonction interne que
  le formulaire et conserve `chatRequestInFlight`.

- [ ] **D4.1 — Extraire sans dupliquer la frontière de soumission**

  Écrire un test rouge prouvant qu'un texte clavier et un transcript Dialogue
  passent par une unique fonction de soumission, avec mêmes thread, streaming,
  sauvegarde, final lock et gestion d'erreur. Le refactor ne change pas le
  comportement clavier.

- [ ] **D4.2 — Écrire les scénarios rouges de session**

  Couvrir : blob → `transcribing` → texte → `thinking`; transcript vide sans
  message ni appel chat ; STT échoué ; double événement blob ; conversation
  changée ; requête déjà en cours ; pause ou fin pendant STT ; réponse chat
  interrompue ; fermeture sans message fantôme.

- [ ] **D4.3 — Implémenter le raccord minimal**

  La transcription n'est jamais injectée dans la vue Dialogue. Après succès,
  elle est soumise une seule fois comme message utilisateur ordinaire. Le
  contrôleur attend le résultat final de la fonction chat existante et ne lit
  pas directement le stream réseau.

- [ ] **D4.4 — Prouver le chemin réel**

  Le smoke Chromium simule STT puis `/api/chat` et vérifie : un POST STT, un POST
  chat, un seul message utilisateur, la réponse finale existante, l'absence de
  transcript dans l'écran Dialogue et sa présence après retour au fil normal.

- [ ] **D4.5 — Contre-auditer, documenter, commit et push**

  Rechercher tout second appel `sendToServer`, tout contournement du form guard,
  toute persistance frontend inventée et toute divergence clavier/Dialogue.

  Commit attendu : `feat(dialogue): route speech through canonical chat`.

**Stop D4 :** si la soumission canonique ne peut pas être réutilisée sans
copier le pipeline, faire un refactor borné séparé et garder le bouton désactivé.

---

## Lot D5 — lecture TTS et boucle semi-duplex

**Livrable :** après la réponse finale canonique, Frida la lit, anime uniquement
pendant le son effectif, puis réarme l'écoute.

**Fichiers :**

- Modifier : `app/web/dialogue/dialogue_audio_client.js`
- Modifier : `app/web/dialogue/dialogue_session_controller.js`
- Modifier : `app/web/chat_dialogue_mode.js` seulement pour projeter les faits
- Modifier : `app/web/app.js`
- Modifier : tests unitaires D4
- Modifier : `app/tests/integration/frontend_browser/test_frontend_browser_smoke.js`
- Modifier : contrat et roadmap Dialogue

**Interfaces :**

- `dialogueAudioClient.synthesize(text) -> Promise<Blob>`.
- Le contrôleur possède exactement un `HTMLAudioElement` et révoque chaque
  object URL après fin ou erreur.
- Le submit canonique de D4 retourne le texte final à lire ou un échec fermé.

- [ ] **D5.1 — Écrire les tests rouges de vérité audio**

  Prouver : aucun TTS avant final lock ; un seul POST TTS ; activation initiale
  Safari conservée ; état `tts_speaking` seulement après l'événement `playing` ;
  arrêt d'animation sur `pause`, `waiting`, `ended`, `error` et sortie ; aucun
  micro pendant lecture ; réarmement seulement après `ended`.

- [ ] **D5.2 — Implémenter le lecteur possédé par la session**

  Créer puis réutiliser un élément audio déverrouillé par le premier geste
  utilisateur. Remplacer sa source par l'object URL du MP3 reçu. Ne pas lire
  `innerHTML`, un brouillon, un placeholder ou un fragment de stream.

- [ ] **D5.3 — Fermer la machine semi-duplex**

  Cycle nominal exact : `listening → user_speaking → transcribing → thinking →
  tts_speaking → listening`. Pause désarme microphone et lecteur. Terminer ou
  fermer arrête pistes, VAD, recorder, requêtes frontend encore annulables,
  audio et animations, puis rend le fil normal interactif.

- [ ] **D5.4 — Prouver échecs et reprises explicites**

  Couvrir refus `play()`, TTS indisponible, MP3 vide, fin de chat sans réponse
  assistant, arrêt utilisateur pendant synthèse et erreur après réponse déjà
  persistée. La réponse écrite reste vraie même si sa vocalisation échoue.

- [ ] **D5.5 — Exécuter la sélection frontend complète**

  ```bash
  node --test app/tests/unit/frontend_chat/*.js
  node --check app/web/app.js
  node --check app/web/chat_dialogue_mode.js
  node --check app/web/dialogue/dialogue_audio_client.js
  node --check app/web/dialogue/dialogue_session_controller.js
  node --check app/web/dialogue/dialogue_vad_recorder.js
  ```

  Puis exécuter le smoke Chromium complet existant.

- [ ] **D5.6 — Contre-auditer, documenter, commit et push**

  Vérifier zéro full-duplex, barge-in, chunking TTS, lecture anticipée, fuite
  textuelle ou boucle automatique après erreur.

  Commit attendu : `feat(dialogue): complete semi-duplex voice loop`.

**Stop D5 :** le bouton produit reste désactivé même si les tests hermétiques
sont verts. Son activation appartient exclusivement à D6.

---

## Lot D6 — activation contrôlée et canari iPhone en voiture

**Livrable :** le bouton Dialogue devient utilisable sur l'iPhone seulement
après une preuve de bout en bout, avec rollback ciblé prêt.

**Fichiers :**

- Modifier : `app/web/index.html` pour retirer `disabled` seulement après les
  preuves de ce lot
- Modifier : `app/web/app.js` si le gate d'ouverture le requiert
- Modifier : `app/tests/integration/frontend_browser/test_frontend_browser_smoke.js`
- Modifier : contrat et roadmap Dialogue

- [ ] **D6.1 — Préflight déployé sans appel fournisseur**

  Vérifier HTTPS, permission micro après geste, chargement local du VAD, codec
  choisi, routes STT/TTS présentes, absence de secret dans le bundle, UI mobile
  stable et chat clavier inchangé. En cas d'échec, ne pas appeler OpenRouter.

- [ ] **D6.2 — Canari fournisseur borné hors voiture**

  Une seule parole courte puis une seule réponse Frida, en ouvrant la session
  par le harnais interne déjà prévu tant que le bouton reste désactivé. Prouver
  dans le même thread : transcript envoyé une fois, traitement canonique,
  réponse persistée, voix Soleil entendue, animation calée sur l'audio,
  réarmement après fin.
  Budgéter explicitement le nombre maximum d'appels : un STT et un TTS, hors
  appel chat ordinaire déjà nécessaire.

- [ ] **D6.3 — Canari automobile iPhone 11**

  Radio et médias arrêtés avant écoute. Vérifier successivement : bruit de
  roulement sans faux départ durable ; parole détectée sans appui supplémentaire ;
  pause naturelle non coupée abusivement ; fin d'énoncé raisonnablement rapide ;
  transcript acceptable dans le fil normal ; une seule réponse ; démarrage TTS
  audible ; réarmement ; Pause ; Terminer ; reprise du chat écrit. Consigner
  uniquement métriques et verdicts content-free.

- [ ] **D6.4 — Activer le bouton et rejouer les preuves**

  Retirer `disabled`, conserver l'accessibilité clavier et tactile, puis rejouer
  les tests frontend, les deux routes backend, le smoke mobile et le chemin chat
  clavier. Aucun autre contrôle ou écran n'est ajouté.

- [ ] **D6.5 — Livrer avec rollback**

  Reconstruire et recréer seulement `platform-fridadev`, sans pull implicite ni
  dépendance. Vérifier HTTP, health, restart, OOM, empreintes et voisins. Conserver
  l'image précédente pour rollback ciblé.

  Commit attendu : `feat(dialogue): activate mobile voice conversation`.

**Stop D6 :** si le canari automobile échoue sur VAD, latence, transcript,
lecture ou réarmement, le bouton reste désactivé. Corriger une seule cause dans
un micro-lot distinct ; ne pas changer de modèle ni ajouter un fallback sans
décision explicite.

---

## Lot Z — réconciliation et clôture

**Livrable :** preuve que le mode oral est un transport du chat existant, pas un
second produit conversationnel.

- [ ] **Z.1 — Matrice des invariants**

  Recroiser code, tests, runtime et contrat pour : un seul pipeline chat, une
  seule conversation, une seule soumission par parole, absence de transcript
  dans la vue Dialogue, transcript consultable dans le fil, TTS limité au final
  canonique, semi-duplex, animations factuelles et cleanup complet.

- [ ] **Z.2 — Sélections de tests autoritatives**

  Exécuter les suites unitaires et intégrations audio, les tests frontend Node,
  le smoke Chromium complet et les voisins immédiats du chat, du streaming, de
  la sauvegarde et de la dictée Whisper existante. Une découverte globale n'est
  lancée que si elle est explicitement décidée et si son résultat peut être
  capturé intégralement.

- [ ] **Z.3 — Contre-audit**

  Chercher : deuxième pipeline, double POST, réarmement sous TTS, microphone ou
  pistes résiduels, audio conservé, contenu brut loggé, secret frontend, CDN,
  fallback silencieux, transcript affiché dans le mode, animation décorative
  permanente, comportement desktop modifié et perte d'une capacité existante.

- [ ] **Z.4 — Documentation et archivage**

  En cas de preuves toutes vertes, synchroniser le contrat et le hub, déplacer
  cette roadmap dans `app/docs/todo-done/Dialogue/` et conserver la reconnaissance
  initiale comme provenance. Sinon, garder la roadmap active avec la cause exacte
  et le lot suivant strictement borné.

## Hors V1 et non bloquant

Les éléments suivants ne doivent pas être glissés dans D1–D6 : TTS par phrases
pendant le streaming, barge-in, full-duplex, identification du locuteur,
suppression active d'une radio tierce, wake word, conversation en arrière-plan,
mode natif iOS/macOS, fallback automatique ou benchmark général multi-modèles.
Chacun exige une décision et une roadmap distinctes après retour d'usage réel.
