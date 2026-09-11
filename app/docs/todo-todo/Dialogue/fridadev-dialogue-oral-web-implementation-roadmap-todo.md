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
WAV PCM16 local, VAD Silero local via `@ricky0123/vad-web`, endpoints audio
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
- [x] La frontière backend TTS D2 existe ; D5 ajoute son consommateur dans le
  seul harnais synthétique. Elle reste inactive dans le produit normal.
- [ ] Aucun microphone, VAD produit, enregistrement navigateur ou raccord audio
  n'est activé dans le produit.

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
- `app/web/dialogue/dialogue_audio_client.js` : transports STT D4 et TTS D5
  vers les deux routes Frida existantes, sans accès fournisseur direct.
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
applicatif.**

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
- micro-correctif de refermeture D1 : la matrice multipart WSGI recense désormais
  explicitement les quatre routes et prouve pour Dialogue les bornes adjacentes,
  les longueurs absentes, invalides ou non positives, `wsgi.input_terminated`,
  l'absence de surlecture et la lecture fichier limitée à borne + 1 avec des
  buffers d'environ 1 Kio. Le transcript participe à nouveau à l'égalité de
  `DialogueSttResult` tout en restant exclu de son `repr`. Les sélections passent
  `31/31` puis `61/61` sans réseau ; les mutations du flag d'égalité et de
  l'inventaire WSGI remettent chacune leur témoin au rouge avant restauration
  SHA-256 exacte.

---

## Lot D2 — frontière TTS et flux audio

**Statut : définitivement refermé, poussé et livré par reconstruction ciblée
du seul service applicatif après classification de
`urllib3.exceptions.SSLError` pendant la lecture streaming. La frontière reste
inactive et D3 reste non commencé.**

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

- [x] **D2.1 — Revalider le contrat TTS OpenRouter**

  Vérifier endpoint, modèle, voix, format, limite de texte, prix, délai et
  politique de données. Arrêter si la voix exacte n'est plus acceptée ou si la
  réponse n'est plus un flux d'octets audio documenté.

- [x] **D2.2 — Écrire les tests rouges service et route**

  Couvrir : MP3 confirmé, texte vide, texte hors borne, voix rejetée, audio vide,
  mauvais content-type, timeout, transport, 401/403/429/5xx et absence de fuite
  du texte dans les erreurs.

  Exécuter :

  ```bash
  python -m unittest \
    tests.unit.chat.test_dialogue_tts_service \
    tests.integration.chat.test_chat_dialogue_audio_routes
  ```

- [x] **D2.3 — Implémenter le service et la route**

  Appeler `/api/v1/audio/speech` avec le modèle V1, la voix Soleil et `mp3`.
  Propager les octets seulement après succès HTTP et validation du content-type.
  Ne pas conserver l'audio sur disque et ne pas ajouter de cache.

- [x] **D2.4 — Vérifier les deux frontières ensemble**

  Exécuter les suites D1/D2, les contrats HTTP voisins et un test prouvant que
  STT et TTS ne partagent ni réponse, ni payload, ni traitement d'erreur ambigu.

- [x] **D2.5 — Contre-auditer, documenter, commit et push**

  Commit attendu : `feat(dialogue): add bounded OpenRouter speech`.

**Stop D2 :** aucun appel provider live n'est nécessaire. Si la voix ne peut
être fixée explicitement, ne pas substituer silencieusement une autre voix.

### Preuves D2 — 9 septembre 2026

- baseline : `main`, HEAD/upstream
  `af8d693fa9257d8e9bd4b4a1746f9c85e33ccc6f`, divergence `0/0`, worktree
  propre avant édition ;
- revalidation documentaire sans appel payant : endpoint brut
  `/api/v1/audio/speech`, modèle et voix Soleil toujours publiés, format `mp3`
  associé à `audio/mpeg`, prix `15 USD` par million de caractères et aucune
  limite d'entrée/sortie ni timeout TTS exact exploitable publié ;
- limites locales : `16 000` caractères sans troncature, réponse lue
  physiquement jusqu'à `16 Mio + 1`, et `timeout=60` Requests comme délai
  d'inactivité réseau, non comme deadline murale absolue ;
- rouge hermétique : `22` assertions causales sur le module, le résolveur et la
  route absents, sans erreur de harnais ;
- vert hermétique D1/D2, routes, WSGI et client OpenRouter : `80/80`, dans un
  conteneur jetable `--network none`, checkout monté en lecture seule et `/tmp`
  en `tmpfs` ;
- contre-audit initial du streaming : les deux témoins injectaient directement
  des exceptions Requests dans `response.raw.read()` et verrouillaient la
  classification visée sans reproduire les classes de la couche `urllib3`
  réellement utilisée ; le correctif causal est documenté ci-dessous ;
- mutation de lecture : neutraliser temporairement l'arrêt à borne plus un fait
  lire `10` octets au lieu de `5` et remet le témoin au rouge ;
- mutation de média : neutraliser temporairement le contrôle accepte à tort
  `application/json` et `audio/mpeg-private`, et remet les deux témoins au rouge ;
- après restauration, les deux témoins repassent au vert. Aucun provider réel,
  frontend, cache, fichier, persistance, retry, fallback, nouveau secret ou
  réglage Admin n'est ajouté ;
- commit applicatif poussé :
  `73af11ec4156bedd89553250b8d1f2b337c44b15` ;
- reconstruction sans pull implicite par `build --pull=false`, puis
  recréation `--no-deps --force-recreate` du seul service `fridadev`. Une
  première invocation avec le nom de projet supposé `platform` a été refusée
  avant toute interruption par conflit de nom ; les labels du conteneur ont
  établi que le projet d'autorité est `fridadev-app`, utilisé pour la recréation
  réussie sans suppression d'orphelin ;
- image livrée :
  `sha256:55f7934122709cfe8e5ed90ce5ece6febc11d67a9cb3d55957d74ac9b829b15b` ;
  image précédente récupérable sous
  `platform-fridadev-app:rollback-d2-20260909T161610Z` ;
- `platform-fridadev` est `running`, `healthy`, restart `0`, OOM `false` ; les
  31 voisins conservent le même inventaire et le même état, empreinte
  `5eadf6cf7b63bec7380a8af5355895b4e3d8df3c6b56ac33663b40aed1cb8ec0` avant
  et après ;
- HTTP interne `200`, route TTS présente et rejet local hermétique `422` sans
  appel provider ; empreintes identiques entre checkout et conteneur pour les
  cinq fichiers runtime, zéro ligne récente `ERROR`, `CRITICAL` ou `Traceback` ;
- la sélection `80/80` repasse depuis l'image réellement déployée, sans montage
  du checkout et toujours avec `--network none`, filesystem read-only et `/tmp`
  en `tmpfs`.

### Correctif de classification streaming D2 — 9 septembre 2026

**Statut : correctif minimal vérifié, poussé et livré par reconstruction ciblée
du seul service applicatif. D3 reste non commencé.**

- micro-réouverture depuis `main`, HEAD/upstream
  `b76419b96d5d0ec88f71b30b880bd556f20775e4`, divergence `0/0`, worktree
  propre ;
- environnement réellement embarqué : Requests `2.32.3`, `urllib3 2.7.0` ;
  `response.raw.read()` remonte notamment `ReadTimeoutError` et
  `ProtocolError`, qui n'héritent pas des exceptions Requests utilisées par le
  témoin précédent ;
- rouge causal hermétique : ces deux classes réelles produisaient à tort
  `502/dialogue_tts_provider_audio_unreadable` ;
- patch local à la lecture : `ReadTimeoutError` devient
  `503/dialogue_tts_provider_timeout`, `ProtocolError` devient
  `503/dialogue_tts_provider_transport_error`, tandis qu'une erreur de données
  générique telle que `OSError` reste `502` ;
- la sélection D1/D2, routes, WSGI et client OpenRouter repasse `82/82` sans
  réseau, dans un conteneur jetable, checkout en lecture seule et `/tmp` en
  `tmpfs` ;
- mutation contrôlée : retirer le raccord `ReadTimeoutError` remet le témoin
  central au rouge avec le `502` fautif ; après restauration, les empreintes du
  service reviennent exactement à leur valeur préalable et les deux témoins
  causaux repassent au vert ;
- `KeyboardInterrupt` et `SystemExit` ne sont pas absorbés et la réponse est
  néanmoins fermée une fois ; aucun corps fournisseur, texte, audio, exception
  brute, URL, header ou secret n'est projeté ou journalisé.
- commit applicatif poussé :
  `04ef9944772e2401fb3f202d3b4d9dcf9766d92c` ;
- reconstruction sans pull implicite par `build --pull=false`, puis recréation
  `--no-deps --force-recreate` du seul service `fridadev` ; image livrée
  `sha256:e69806fc023997ffca9e0dc922e27c2a8070a6ada241770794dc58427c7c6757`,
  image précédente récupérable sous
  `platform-fridadev-app:rollback-d2-stream-20260909T164936Z` ;
- `platform-fridadev` est `running`, `healthy`, restart `0`, OOM `false` ; les
  31 voisins conservent strictement leur identité, image et état, empreinte
  `1e07b24585e6113b7c44d38e2b5248c1e3f7197aef5ed167b380f079f9e68051`
  avant et après ;
- HTTP interne `200`, rejet local hermétique de la route TTS en `422` sans
  appel fournisseur, zéro succès TTS live et zéro ligne récente `ERROR`,
  `CRITICAL` ou `Traceback` ; empreintes du service et de son test identiques
  entre checkout et conteneur ;
- la sélection `82/82` repasse depuis l'image réellement déployée, sans montage
  du checkout, `--network none`, filesystem read-only et `/tmp` en `tmpfs`.

### Correctif de classification SSL streaming D2 — 9 septembre 2026

**Statut : correctif minimal vérifié, poussé et livré par reconstruction ciblée
du seul service applicatif. D3 reste non commencé.**

- micro-réouverture depuis `main`, HEAD/upstream
  `de588870ba19e5568886c0c15843d5cf1d073889`, divergence `0/0`, worktree
  propre ;
- environnement réellement embarqué : Requests `2.32.3`, `urllib3 2.7.0` ;
  `SSLError` hérite directement de `urllib3.exceptions.HTTPError`, ni de
  `ProtocolError` ni des exceptions Requests déjà reconnues ;
- rouge causal hermétique : `SSLError` pendant `response.raw.read()` produisait
  à tort `502/dialogue_tts_provider_audio_unreadable`, tandis que le sous-cas
  `ProtocolError` restait vert ;
- patch local au groupe transport de la lecture : `SSLError` devient
  `503/dialogue_tts_provider_transport_error`. Une erreur générique telle que
  `OSError` reste `502` ;
- le témoin réel vérifie une fermeture unique et l'absence de l'exception brute
  dans le résultat, le payload et les logs ;
- mutation contrôlée : retirer uniquement `SSLError` du groupe transport remet
  son sous-cas au rouge avec le `502` fautif ; les empreintes du service et du
  test reviennent exactement à leur valeur préalable après restauration ;
- la sélection D1/D2, routes, WSGI et client OpenRouter repasse `82/82` sans
  réseau, dans un conteneur jetable, checkout en lecture seule et `/tmp` en
  `tmpfs` ; aucun provider réel, frontend, STT, limite, streaming, timeout ou
  lot D3 n'est modifié.
- commit applicatif poussé :
  `9042f58f93aed5eb28cdb810ffca5f211547cbef` ;
- reconstruction sans pull implicite par `build --pull=false`, puis recréation
  `--no-deps --force-recreate` du seul service `fridadev` ; image livrée
  `sha256:668c2c62b8a77a345dcecd2b0d7976473364a02e6e7157cae13681d03249e09d`,
  image précédente récupérable sous
  `platform-fridadev-app:rollback-d2-ssl-20260909T165918Z` ;
- `platform-fridadev` est `running`, `healthy`, restart `0`, OOM `false` ; les
  31 voisins conservent strictement leur identité, image et état, empreinte
  `1e07b24585e6113b7c44d38e2b5248c1e3f7197aef5ed167b380f079f9e68051`
  avant et après ;
- HTTP interne `200`, rejet local hermétique de la route TTS en `422` sans
  appel fournisseur, zéro succès TTS live et zéro ligne récente `ERROR`,
  `CRITICAL` ou `Traceback` ; empreintes du service et de son test identiques
  entre checkout et conteneur ;
- la sélection `82/82` repasse depuis l'image réellement déployée, sans montage
  du checkout, `--network none`, filesystem read-only et `/tmp` en `tmpfs`.

---

## Lot D3 — VAD et enregistreur local sur Safari

**Statut : D3 rouvert le 9 septembre 2026 pour corriger deux défauts établis :
capture depuis armement et chargement VAD obligatoire au bootstrap du chat.
La clôture antérieure ne prouvait pas ces invariants. Après correction, rouges,
mutations, suites complètes et livraison vérifiée, D3 est définitivement refermé.
Le bouton produit reste désactivé et D4 n'est pas commencé.**

**Rectification du 10 septembre, D6.2b :** les preuves historiques ci-dessous
utilisaient legacy. L'affirmation du manifeste reliant ce modèle à la calibration
Safari du démonstrateur était fausse. Le raccord courant passe à V5 ; les valeurs
historiques restent ici datées et ne décrivent plus la segmentation courante.

**Livrable :** l'interface peut ouvrir une session locale de test, détecter une
parole et produire un blob borné ; elle n'appelle encore ni STT ni chat.

**Fichiers :**

- Créer : `app/web/dialogue/dialogue_vad_recorder.js`
- Créer : `app/web/dialogue/dialogue_vad_runtime.js`, adaptateur strict de la
  version VAD épinglée et de son cleanup partiel
- Ajouter : distribution locale épinglée de `@ricky0123/vad-web` et ses assets
  strictement nécessaires sous `app/web/vendor/dialogue-vad/`
- Modifier : `app/web/index.html`
- Modifier : `app/web/app.js`
- Créer : `app/tests/unit/frontend_chat/test_dialogue_vad_recorder_module.js`
- Créer : `app/tests/unit/frontend_chat/test_dialogue_vad_runtime_module.js`
- Créer : `app/tests/unit/frontend_chat/test_dialogue_vad_vendor_contract.js`
- Modifier : `app/tests/integration/frontend_browser/test_frontend_browser_smoke.js`
- Modifier : contrat et roadmap Dialogue

**Interfaces :**

- Produit : `createDialogueVadRecorder(options)` avec `arm()`, `pause()`,
  `resume()`, `stop()` et événements `speech-start`, `speech-end`, `blob`,
  `error`.
- L'événement `blob` porte un seul `Blob`, son MIME, sa durée et sa taille ;
  jamais une transcription.

- [x] **D3.1 — Écrire les tests rouges de cycle de vie**

  Avec fakes explicites de `getUserMedia`, horloge et inférence, et le vrai
  segmenter épinglé, prouver :
  aucun accès micro avant geste utilisateur, armement unique, bruit rejeté,
  parole reconnue, silence de fin, un blob unique, arrêt à la durée/poids
  maximum, pistes arrêtées, double appui sans double VAD et cleanup après
  erreur.

  Exécuter :

  ```bash
  node --test app/tests/unit/frontend_chat/test_dialogue_vad_recorder_module.js
  ```

- [x] **D3.2 — Implémenter la machine locale**

  Consommer le Float32 mono 16 kHz de `onSpeechEnd(audio)`, pré-roll borné
  inclus, et produire un unique WAV PCM16 local sans dépendance. Le VAD ferme
  l'énoncé ; l'attente silencieuse ne figure ni dans le blob ni dans sa durée.
  Les bornes sont appliquées au buffer fournisseur avant concaténation puis
  au WAV avant toute sortie. Supprimer la capture continue MediaRecorder.

- [x] **D3.3 — Neutraliser les médias contrôlables avant l'écoute**

  Suspendre le lecteur TTS possédé par Frida et les éléments audio/vidéo du
  document avant `arm()`. Ne jamais prétendre contrôler une radio automobile ou
  une application tierce que Safari ne peut pas piloter. Si un média local ne
  peut pas être mis en pause, l'armement échoue honnêtement.

- [x] **D3.4 — Prouver l'intégration visuelle sans réseau**

  Le smoke Chromium ouvre le mode par son harnais, simule parole et silence,
  vérifie `listening → user_speaking → listening`, la vérité des animations,
  Pause, Terminer, fermeture, safe areas et absence de requête audio/backend ;
  seuls les assets VAD locaux same-origin sont chargés, après ouverture
  explicite du harnais. La page normale ne charge aucun asset D3 et reste
  utilisable même si les assets sont absents ou refusés.

- [x] **D3.5 — Contre-auditer, documenter, commit et push**

  Vérifier qu'aucun CDN runtime, second VAD, transcript visible, requête
  fournisseur ou réarmement implicite n'a été ajouté.

  Commit attendu : `feat(dialogue): add local voice activity capture`.

**Stop D3 :** un échec de permission, d'initialisation VAD ou d'encodage doit
rester visible et récupérable ; ne pas contourner le VAD par un seuil de volume.

### Livraison D3 initiale — preuves historiques invalidées sur deux invariants

La livraison ci-dessous est historique : ses tests verts ne prouvaient ni le
pré-roll borné par énoncé ni l'isolation du bootstrap. La fermeture initiale et
le verdict « aucun finding » sont donc révoqués sur ces deux points.

- baseline : `/opt/platform/fridadev`, `main`, HEAD/upstream
  `44bd13ceafd289d93db618c3adca3643469c5f7d`, divergence `0/0`, worktree
  propre avant édition ;
- API revalidée : `@ricky0123/vad-web@0.0.30`,
  `onnxruntime-web@1.22.0`, `MicVAD.new()` avec `model: legacy`,
  `processorType: AudioWorklet`, `startOnLoad: false`, chemins locaux
  `baseAssetPath` et `onnxWASMBasePath`, puis flux propriétaire injecté par
  `getStream`, `pauseStream` et `resumeStream` ;
- défaut initial : MediaRecorder conservait le cycle complet depuis `arm()`.
  Ce choix violait le contrat de pré-roll et ne constituait pas un mécanisme
  équivalent autorisé. Il est retiré au profit de l'audio segmenté du VAD ;
- rouges déterministes observés : module absent, implémentation sentinelle
  `not implemented`, harnais navigateur absent, callbacks tardifs non gardés,
  arrêt pendant initialisation laissant une piste active, nettoyage partiel
  MicVAD laissant modèle/contexte ouverts, borne de durée exacte refusée et
  réjection d'inférence ONNX non convertie en erreur fermée, appels lifecycle
  concurrents résolus avant leur cleanup, reprise créant un second VAD avant la
  destruction du premier, instance VAD retournée trop tard et non détruite,
  finalisation sans événement `stop` devenue non bornée, puis exception
  `MediaRecorder.stop()` émettant un blob incomplet ; chaque témoin est ensuite
  repassé au vert sur son correctif minimal ;
- la frontière MicVAD épinglée complète le cleanup fournisseur partiel,
  enveloppe `processFrame` avant `start()` et convertit sa première réjection
  en `vad_runtime_error`; elle ne fabrique aucun callback fournisseur ;
- le smoke Chromium charge le modèle legacy, le module MJS et le WASM locaux
  sans appel micro, puis le harnais synthétique prouve le flux partagé, les
  états et animations, Pause/Reprendre/Terminer/fermer, y compris une fermeture
  pendant permission différée, sans POST audio, STT, chat ou TTS ;
- la borne accepte exactement `300 000 ms` et `24 000 000` octets, puis refuse
  l'octet ou la milliseconde suivante sans blob ni troncature ; les fragments,
  timers et pistes sont libérés avant toute attente de cleanup fournisseur. La
  deadline reste armée pendant la finalisation et libère aussi une attente
  `MediaRecorder.stop()` qui ne notifierait jamais sa fin ;
- `pause()` arrête le flux courant. Seul le geste explicite Reprendre ouvre un
  nouveau cycle, avec un unique nouveau flux de nouveau partagé par identité ;
  les appels concurrents attendent la même opération de cleanup et une instance
  VAD rendue tardivement est détruite explicitement ;
- preuves finales hôte : syntaxe JavaScript et sélection D3/Dialogue/Whisper/
  load-order `56/56`, tous les tests unitaires frontend `205/205`, smoke
  Chromium complet `25/25` ; voisins Python D1/D2/Whisper/frontend `76/76`
  dans un conteneur jetable read-only et sans réseau ;
- mutation contrôlée : retirer le seul `stopTracks(targetStream)` du cleanup
  remet au rouge le témoin d'arrêt pendant initialisation VAD (`live` au lieu
  de `ended`). À l'instant de la restauration, le module retrouve exactement
  son SHA-256 préalable
  `e7235b3b4f130d0715e27aa42e27bcd3dad711d84209e77bafd6194b42203a1c` et le
  témoin repasse au vert ;
- le verdict initial de revue sans finding restant était insuffisant :
  le préfixe complet n'était pas une limite acceptable et le chargement
  obligatoire du VAD avait échappé aux témoins du bootstrap ;
- commit applicatif poussé :
  `70489f46753d0569e0863ba7fbdb00a614f48290` ;
- reconstruction sans pull implicite par `build --pull=false`, toutes les
  couches de dépendances restant en cache, puis recréation
  `--no-deps --force-recreate` du seul service `fridadev` ; image livrée
  `sha256:9e9aac73d1015f870eea44cf3c58f4bc81b4a0786d9b5047e197f042efb154b1`,
  image précédente récupérable sous
  `platform-fridadev-app:rollback-d3-20260909T180603Z` ;
- `platform-fridadev` est `running`, `healthy`, restart `0`, OOM `false`. Les
  31 voisins conservent exactement identité, image et état, empreinte
  `600cd770bd575dab2981eee238e9773d4718ea7c21469eb17a2476b1db5501a9`
  avant et après ;
- HTTP interne `/` et chacun des scripts, worklet, modèle ONNX, MJS et WASM
  D3 répondent `200` avec le content-type attendu. L'arbre D3 checkout/conteneur
  partage l'empreinte
  `5352ce0976e66c075b17782f59d7fd0b52ee07c0dcfca0c61f75d809bdcf2c4e`
  et les deux entrypoints Web l'empreinte
  `9159560faffd4d4eb6879a0f53749369dc361b18a5b954cddc990b336e6f7768` ;
- les voisins Python repassent `76/76` depuis l'image effectivement livrée,
  sans montage du checkout, réseau coupé et filesystem read-only. Depuis le
  démarrage livré, les logs comptent zéro `ERROR`, `CRITICAL`, `Traceback` ou
  succès provider Dialogue ; l'unique warning n'appartient ni aux familles
  Dialogue, assets statiques, 404, OpenRouter, provider ou Whisper.

### Réouverture corrective D3 — 9 septembre 2026

- baseline : `main`, HEAD/upstream
  `de37545b5983b3e95353b065ef3f3a5353a05db3`, divergence `0/0`,
  worktree propre après fetch ;
- rouges observés avant correction : expiration après 384 secondes de
  silence/bruit rejeté ; durée dépendante de l'armement ; scripts ONNX/VAD
  chargés par la page normale, y compris quand refusés ;
- plan revalidé dans la distribution épinglée : Float32 mono 16 kHz,
  pré-roll legacy de 8 trames / 768 ms, WAV PCM16 sans nouvelle dépendance.
  300 s correspondent à 9 600 044 octets. Suppression de MediaRecorder ;
- chargement de tous les modules et assets D3 différé à l'ouverture explicite
  du harnais ; bornes du buffer fournisseur avant append/concaténation,
  puis validation du tableau et du WAV ; D1/D2 et D4 restent intacts ;
- preuves corrigées : D3 ciblé `28/28`, frontend unitaire complet `193/193`,
  Chromium complet `29/29`, voisins Python D1/D2/Whisper/frontend `76/76`
  dans un conteneur jetable read-only, réseau désactivé, checkout en lecture
  seule. Les anciennes assertions propres au MediaRecorder supprimé sont
  remplacées par des preuves WAV et du vrai segmenter épinglé ;
- Chromium prouve zéro asset D3 à l'ouverture normale, chat clavier utilisable
  avec assets refusés/absents, échec local D3 sans pageerror, et chargement
  explicite de tous les assets locaux, worklet inclus (observé côté serveur
  statique). Un flux AudioContext synthétique traverse le vrai MicVAD, une
  inférence ONNX locale puis la segmentation pilotée déterministement ; son WAV
  est décodé à 16 kHz en mono avec durée exacte de 2,592 s ;
- les contrôles gardent safe areas, états, animations exactes, Pause/Reprendre,
  Terminer et fermer. Rouge supplémentaire puis correction : Pause pendant
  permission différée construisait encore un VAD tardif ; le geste invalide
  maintenant immédiatement l'armement, avant toute reprise explicite ;
- mutation 1 : réintroduire le préfixe PCM depuis armement remet le témoin de
  long silence au rouge, et transforme une parole de 1 s après attente en
  240 s. Restauration exacte du module :
  `106640edd9b7690e72b08b6eb59005d07d4a99d0cd9587666d77f279f6ff8d7d` ;
- mutation 2 : réintroduire l'initialisation obligatoire VAD au bootstrap
  remet le témoin d'isolation au rouge. Restauration exacte de `app.js` :
  `39f8afa7898528eb745b8061f293dbd205ad65f0bb20480bfb33c1deb6ff6e20` ;
- après restauration, les suites complètes repassent sans skip, assertion
  affaiblie ni sleep ajouté. Le décodage WAV utilise un OfflineAudioContext
  à 16 kHz pour vérifier une durée exacte sans arrondi de rééchantillonnage ;
- contre-audit : aucun MediaRecorder D3, second flux, timer depuis armement,
  buffer non borné, réarmement implicite, CDN, nouvelle dépendance, route,
  contenu journalisé, transcript visible ou raccord D1/D2/Whisper/chat/TTS.
  Les assets et licences épinglés restent identiques. Le chat clavier,
  le contrôleur visuel, le CSS mobile/desktop et les backends sont inchangés ;
- aucun microphone réel, canari iPhone, provider, STT, TTS, chat backend ou DB
  opérateur appelé. Les POST clavier dans Chromium sont exclusivement simulés ;
- les internals épinglés et les performances Safari restent à revalider au
  futur canari autorisé : si une inférence locale chevauche la suivante, D3
  ferme en erreur sans accumuler ni perdre silencieusement l'audio ;
- commit correctif poussé :
  `53d60c1cd0f6f98f74f3ce3111c8269d119f5594` ;
- reconstruction `build --pull=false` sans pull Git, dépendances en cache,
  puis `up -d --no-deps --force-recreate fridadev` dans le projet
  `fridadev-app`. Seul `platform-fridadev` est recréé ;
- image corrective :
  `sha256:19ba1ac8e66e1d74396d37062f5295835df26d07c313b161066dcbe4251a220e` ;
  rollback conservé :
  `platform-fridadev-app:rollback-d3-preroll-20260909T184755Z` ;
- runtime `running/healthy`, restart `0`, OOM `false`; identité, image et
  état des 31 voisins strictement inchangés ;
- HTTP interne `200` sur la page et les 14 fichiers D3/entrypoint/licences,
  content-types attendus, hashes des réponses servis identiques aux fichiers.
  Le HTML servi ne charge aucun script D3. Empreinte agrégée des entrypoints,
  modules et assets/manifest/licences, identique checkout/conteneur :
  `98d0755c2b328636aeeb639bd831dd10c0a92f5a61d90054c503fb3125646dc4` ;
- les 76 tests voisins repassent depuis l'image réellement reconstruite,
  sans montage du checkout, réseau coupé, filesystem read-only et tmpfs ;
- la présente réconciliation finale est documentaire seulement : les fichiers
  runtime restent ceux du commit correctif livré, sans seconde recréation.

**D3 DÉFINITIVEMENT REFERMÉ — BOUTON PRODUIT TOUJOURS DÉSACTIVÉ —
D4 NON COMMENCÉ.**

---

## Lot D4 — raccord STT au pipeline chat canonique

**Statut : D4 fermé, poussé et livré après preuves rouges/vertes, mutations,
contre-audit et reconstruction ciblée. Bouton produit toujours désactivé.
D5 et D6 non commencés.**

**Livrable :** une parole produit un message utilisateur normal et traverse le
pipeline Frida existant une seule fois. Le TTS n'est pas encore enchaîné.

**Fichiers :**

- Créer : `app/web/dialogue/dialogue_audio_client.js`
- Créer : `app/web/dialogue/dialogue_session_controller.js`
- Modifier : `AGENTS.md` pour l'exception D4 explicite
- Modifier : `app/web/index.html` pour les deux petits modules D4
- Modifier : `app/web/app.js`
- Modifier : `app/web/chat_dialogue_mode.js` seulement si un état visuel manque
- Créer : `app/tests/unit/frontend_chat/test_canonical_chat_submission.js`
- Créer : `app/tests/unit/frontend_chat/test_dialogue_audio_client_module.js`
- Créer : `app/tests/unit/frontend_chat/test_dialogue_session_controller_module.js`
- Modifier : `app/tests/integration/frontend_browser/test_frontend_browser_smoke.js`
- Modifier : contrat et roadmap Dialogue

**Interfaces :**

- `dialogueAudioClient.transcribe(blob, { signal }?) -> Promise<string>`.
- `dialogueSessionController.start()` ouvre une génération et retourne son
  callback de capture ; `pause`, `resume`, `stop`, `close` et
  `conversationChanged` invalident les opérations selon leur état. Il reçoit
  par injection `submitCanonicalChatMessage(text, inputMode)`.
- `inputMode` vaut `dialogue`; le submit réutilise la même fonction interne que
  le formulaire et conserve `chatRequestInFlight`. Le transport reste
  exclusivement `voice` (Dialogue/Whisper) ou `keyboard` ; aucune valeur
  `dialogue` ne rejoint le backend.
- Le succès de `submitCanonicalChatMessage` retourne
  `{ ok: true, text: reply }`, où `reply` est le final lock canonique exact,
  y compris `""`. Les résultats fermés `busy`, `empty` et `chat_failed` ne
  retournent pas de texte ; le contrôleur D4 ignore encore le texte du succès.

- [x] **D4.1 — Extraire sans dupliquer la frontière de soumission**

  Écrire un test rouge prouvant qu'un texte clavier et un transcript Dialogue
  passent par une unique fonction de soumission, avec mêmes thread, streaming,
  sauvegarde, final lock et gestion d'erreur. Le refactor ne change pas le
  comportement clavier.

- [x] **D4.2 — Écrire les scénarios rouges de session**

  Couvrir : blob → `transcribing` → texte → `thinking`; transcript vide sans
  message ni appel chat ; STT échoué ; double événement blob ; conversation
  changée ; requête déjà en cours ; pause ou fin pendant STT ; réponse chat
  interrompue ; fermeture sans message fantôme.

- [x] **D4.3 — Implémenter le raccord minimal**

  La transcription n'est jamais injectée dans la vue Dialogue. Après succès,
  elle est soumise une seule fois comme message utilisateur ordinaire. Le
  contrôleur attend le résultat final de la fonction chat existante et ne lit
  pas directement le stream réseau.

- [x] **D4.4 — Prouver le chemin réel**

  Le smoke Chromium simule STT puis `/api/chat` et vérifie : un POST STT, un POST
  chat, un seul message utilisateur, la réponse finale existante, l'absence de
  transcript dans l'écran Dialogue et sa présence après retour au fil normal.

- [x] **D4.5 — Contre-auditer, documenter, commit et push**

  Rechercher tout second appel `sendToServer`, tout contournement du form guard,
  toute persistance frontend inventée et toute divergence clavier/Dialogue.

  Commit attendu : `feat(dialogue): route speech through canonical chat`.

**Stop D4 :** si la soumission canonique ne peut pas être extraite sans copie
ou modification comportementale large, arrêter après les preuves et rapporter
le blocage. Cette condition n'a pas été rencontrée : le corps existant est
extrait, sans second `sendToServer`.

### Preuves D4 — 9 septembre 2026

- baseline avant édition : `/opt/platform/fridadev`, `main`, HEAD/upstream
  `0f712369949bc4a1db80d9e8e4818ddfc03ef990`, worktree propre, divergence `0/0` ;
  travail dans l'IDE, sans SSH ni pull ;
- rouges initiaux : `40` assertions unitaires échouent causalement sur les deux
  modules absents et la fonction canonique non extraite. Les deux scénarios
  Chromium initiaux ne rejoignent pas `transcribing` depuis le WAV D3 ;
- rouges supplémentaires du contre-audit : reprise sous chargement affichée
  en pause, puis armement tardif après une deuxième pause (`1` acquisition au
  lieu de `0`) ; changement de thread pendant chargement laissant un micro
  vivant en `error` ; reprise après erreur de capture projetant à tort l'écoute
  d'un recorder mort ; même Blob accepté deux fois après reprise explicite ;
  chaque témoin est satisfait par un correctif borné dans D4/wiring ;
- la preuve de soumission exécute ensemble le vrai corps extrait et son vrai
  parseur streaming, avec seulement DOM/serveur substitués. Elle couvre les
  trois provenances, busy, message unique, thread, final lock, cache,
  métadonnées, réhydratation et erreurs. Le témoin Chromium instrumente la
  fonction réellement exécutée et inclut aussi le vrai module Whisper ;
- mutation 1 : contourner le submit commun pour Dialogue fait disparaître
  `dialogue` de la liste des appels canoniques, témoin Chromium rouge ;
  restauration exacte de `app.js` :
  `aa7f2c515fd731841d44fd758e272fc51db3fca17328312a9ed8c41b69cff064` ;
- mutation 2 : supprimer les gardes génération/conversation provoque une
  soumission au thread B, une soumission après Pause et des états tardifs sur
  une nouvelle session. Les témoins échouent sur ces effets observés, sans
  sleep ni attente non résolue ; restauration exacte du contrôleur :
  `e2d07a8a82e422640ab3873adb689f3afae3387455f7224a44661873028f40a1` ;
- après chaque restauration, le témoin concerné repasse avec exit `0` ;
- sélection finale D4 `43/43`, frontend unitaire complet `236/236`, D3 complet
  `28/28`, Chromium complet `34/34` (dont cinq scénarios D4), sans échec,
  annulation, skip ou TODO ; `node --check` passe sur les sept JS du lot,
  ainsi que `git diff --check` ;
- voisins Python D1/D2/routes, Whisper et input_mode `57/57`, dans l'image D3
  déjà déployée, avec checkout monté read-only, `--network none`, filesystem
  read-only, `/tmp` en tmpfs et `PYTHONDONTWRITEBYTECODE=1`. Les erreurs de
  transport/persistance injectées restent les témoins attendus, pas des accès
  au provider ou à la DB opérateur ;
- revue indépendante : aucun finding vivant après correction. Elle reproduit
  en plus fermeture/réouverture pendant permission différée, anciens callbacks
  inertes, un seul flux actif dans la nouvelle session puis zéro après sortie ;
- aucun backend, provider, schéma input_mode, prompt, persistance, modèle,
  licence/asset D3, Whisper, style ou contrôleur visuel n'est modifié. Aucune
  lecture audio, TTS, activation du bouton, dispatch artificiel de formulaire,
  stockage ou journal de transcript n'est introduit ;
- le Browser plugin est absent : le smoke Playwright/Chromium existant sert la
  page locale et intercepte les POST multipart/JSON natifs. Aucun provider,
  micro physique ni donnée opérateur n'est utilisé. Le canari Safari réel et
  le bruit de roulement restent hors D4.

Commandes frontend exécutées après restauration :

```bash
node --test app/tests/unit/frontend_chat/test_canonical_chat_submission.js app/tests/unit/frontend_chat/test_dialogue_audio_client_module.js app/tests/unit/frontend_chat/test_dialogue_session_controller_module.js
node --test app/tests/unit/frontend_chat/test_dialogue_vad_*.js
node --test app/tests/unit/frontend_chat/*.js
node --test app/tests/integration/frontend_browser/test_frontend_browser_smoke.js
```

Les sept JS modifiés/créés sont vérifiés individuellement par `node --check`.
La sélection Python est `tests.unit.chat.test_dialogue_stt_service`,
`tests.unit.chat.test_dialogue_tts_service`,
`tests.integration.chat.test_chat_dialogue_audio_routes`,
`tests.unit.chat.test_whisper_transcription_service`,
`tests.integration.frontend_chat.test_frontend_whisper_contract` et
`tests.integration.chat.test_chat_input_mode_route`, via `python -m unittest`
dans le conteneur hermétique décrit ci-dessus.

---

### Livraison D4 vérifiée — 9 septembre 2026

- commit applicatif poussé sur `main` : `69b19a2b24ab55036f7ebc04164d018ee06c7fb7`, message
  `feat(dialogue): route speech through canonical chat` ; HEAD/upstream égaux,
  divergence `0/0`, worktree propre avant reconstruction ;
- `docker compose -p fridadev-app -f /opt/platform/fridadev-app/docker-compose.yml build --pull=false fridadev`,
  dépendances en cache, puis `up -d --no-deps --force-recreate fridadev` : seul
  `platform-fridadev` est recréé, sans pull Git, changement Compose ou voisin ;
- image livrée : `sha256:34ce6038c3f8db1231df3019d7079bc8add9b25f70fcb2567b6c96f193ce946e` ;
- rollback conservé et vérifié : `platform-fridadev-app:rollback-d4-20260909T191410Z`,
  image précédente `sha256:19ba1ac8e66e1d74396d37062f5295835df26d07c313b161066dcbe4251a220e` ;
  un rollback applicatif peut réutiliser ce tag avec la même recréation ciblée,
  sans toucher les données ni les services voisins ;
- service `running/healthy`, restart `0`, OOM `false` ; identité, image,
  démarrage, état, restart/OOM et health des `31` voisins strictement inchangés,
  empreinte `f982e178b18f87f520be80384e8d115c3f03242c37557784b146414535bc1e41` ;
- HTTP interne `200` pour la page et `17` fichiers de scripts/assets/licences.
  Les `18` SHA-256 sont identiques entre checkout, disque du conteneur et corps
  HTTP servi ; médias JavaScript/HTML/WASM corrects. Le HTML servi conserve
  `disabled` et ne charge aucun script VAD/ONNX au bootstrap ; empreinte agrégée
  du relevé chemin/statut/média/SHA-256 :
  `1b72e3d1841b641bc3afbfcf8c138ec0775aa1a75ee74660dcc4df5ed47ce02c` ;
- depuis le démarrage livré, zéro ligne `ERROR`, `CRITICAL` ou `Traceback`,
  zéro POST `/api/chat/dialogue/*`. Aucun canari STT/provider ou audio réel ;
- la sélection Python `57/57` repasse depuis l'image effectivement livrée,
  sans montage du checkout, sans réseau et avec filesystem read-only/tmpfs ;
  le hostname public retourne `302` sans authentification ;
- cette réconciliation finale modifie seulement la documentation. Les quatre
  fichiers runtime D4 restent ceux du commit applicatif livré ; elle ne
  déclenche pas une deuxième recréation.

**D4 FERMÉ — BOUTON PRODUIT TOUJOURS DÉSACTIVÉ — D5 NON COMMENCÉ.**

---

## Lot D5 — lecture TTS et boucle semi-duplex

**Statut : D5 fermé, poussé et livré après vérification runtime.
Bouton produit toujours désactivé ; D6 non commencé.**

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

- `dialogueAudioClient.synthesize(text, { signal }?) -> Promise<Blob>`.
  Texte exact, comptage `Array.from(text).length`, HTTP 200 et MP3 borné.
- `dialogueSessionController.whenReady() -> Promise<boolean>` confirme
  préparation du lecteur et cleanup avant armement. `start()` appelle
  synchroniquement `play()` sur le silence local depuis le geste initial.
  Le lecteur est explicitement transmis au recorder D3, sans recherche DOM.
- Le contrôleur possède exactement un `HTMLAudioElement` et révoque chaque
  object URL après fin ou erreur.
- Le submit canonique de D4 retourne `{ ok: true, text }`, avec le texte exact
  du final lock, y compris `""`. D5 consomme cette valeur directement,
  sans relire le DOM, le cache ou un fragment de stream ; un échec fermé ne
  fournit aucun texte à lire.

- [x] **D5.1 — Écrire les tests rouges de vérité audio**

  Prouver : aucun TTS avant final lock ; un seul POST TTS ; amorce locale appelée
  synchroniquement dans le geste initial, refus fermé avant armement (Safari
  iPhone reste à valider matériellement en D6) ; état `tts_speaking` seulement
  après l'événement `playing` ;
  arrêt d'animation sur `pause`, `waiting`, `ended`, `error` et sortie ; aucun
  micro pendant lecture ; réarmement seulement après `ended`.

- [x] **D5.2 — Implémenter le lecteur possédé par la session**

  Créer puis réutiliser un élément audio préparé depuis le premier geste
  utilisateur ; la conservation de l'autorisation Safari reste à valider
  matériellement en D6. Remplacer sa source par l'object URL du MP3 reçu. Ne pas lire
  `innerHTML`, un brouillon, un placeholder ou un fragment de stream.

- [x] **D5.3 — Fermer la machine semi-duplex**

  Cycle nominal : `listening → user_speaking → transcribing → thinking →
  tts_pending → tts_speaking → listening`, avec `tts_pending` également pendant
  le buffering et le réarmement après cleanup. Pause désarme microphone et
  lecteur. Terminer ou fermer arrête pistes, VAD, recorder, requêtes frontend encore annulables,
  audio et animations, puis rend le fil normal interactif.

- [x] **D5.4 — Prouver échecs et reprises explicites**

  Couvrir refus `play()`, TTS indisponible, MP3 vide, fin de chat sans réponse
  assistant, arrêt utilisateur pendant synthèse et erreur après réponse déjà
  persistée. La réponse écrite reste vraie même si sa vocalisation échoue.

- [x] **D5.5 — Exécuter la sélection frontend complète**

  ```bash
  node --test app/tests/unit/frontend_chat/*.js
  node --check app/web/app.js
  node --check app/web/chat_dialogue_mode.js
  node --check app/web/dialogue/dialogue_audio_client.js
  node --check app/web/dialogue/dialogue_session_controller.js
  node --check app/web/dialogue/dialogue_vad_recorder.js
  ```

  Puis exécuter le smoke Chromium complet existant.

- [x] **D5.6 — Contre-auditer, documenter, commit et push**

  Vérifier zéro full-duplex, barge-in, chunking TTS, lecture anticipée, fuite
  textuelle ou boucle automatique après erreur.

  Commit attendu : `feat(dialogue): complete semi-duplex voice loop`.

**Stop D5 :** le bouton produit reste désactivé même si les tests hermétiques
sont verts. Son activation appartient exclusivement à D6.

### Design D5 approuvé et preuves finales — 9 septembre 2026

- baseline Git conforme : `/opt/platform/fridadev`, `main`, HEAD/upstream
  `fc2da991f97b9e61cdde2dddcf11f736fede7200`, divergence `0/0`, worktree propre ;
  travail directement dans l'IDE, sans SSH ni pull ;
- design explicitement approuvé avant édition : un lecteur dans la session
  existante, amorce PCM locale minuscule sans réseau, injection explicite à D3,
  projection `tts_pending`, autorisation de réarmement consommée par `ended`
  uniquement. Pas de nouveau module, dépendance, route ou pipeline ;
- rouge transport : les 15 nouveaux cas D5 échouent sur l'absence de
  `synthesize` ; sélection verte client `36/36`. Le texte Unicode composé,
  décomposé, astral, U+0085, U+001C et U+FEFF n'est jamais réécrit ;
- rouge visuel : `tts_pending` est absent. Après ajout, `4/4` preuves visuelles
  passent, notamment l'extinction des animations sans transformer Pause en
  Reprendre pendant le buffering ;
- rouges session : amorce/readiness absentes, promesse `play()` tardive bloquant
  le tour suivant après `ended`, puis reprise contournant une préparation
  annulée. La sélection D4/D5 session passe `36/36` après correction ;
- le premier rouge Chromium traverse le vrai wiring et constate le lecteur
  non transmis à la session ; l'ouverture crée désormais l'élément avant toute
  attente et l'injecte explicitement au recorder, puis attend `whenReady()` ;
- première sélection frontend unitaire complète `276/276`, sans échec,
  annulation ni skip. Les voisins Python D1/D2/routes, Whisper et input_mode
  passent `57/57` dans un conteneur jetable `--network none`, filesystem et
  checkout read-only, `/tmp` en tmpfs ; aucune donnée opérateur ni provider ;
- revue indépendante transport/visuel/wiring : `40/40` ciblés. L'hypothèse
  d'un rejet Unicode trop large est invalidée : l'exception U+FEFF préserve le
  texte valide D2, les autres différences de blanc restent tranchées par D2 ;
- contre-audit indépendant de la session et du wiring : `76/76` ciblés,
  aucun finding vivant confirmé ;
- image initiale observée :
  `sha256:d6907e75766bdc95af2ba2825f2294d147718edea89a8a62a1417766d6fcaa84`,
  différente de l'archive D4 mais les huit fichiers applicatifs vérifiés sont
  strictement identiques au HEAD initial. Service running/healthy, restart 0,
  OOM false ; labels d'autorité : projet `fridadev-app`, service `fridadev`,
  Compose `/opt/platform/fridadev-app/docker-compose.yml`.


---

### Vérification finale D5 avant livraison

- frontend unitaire complet après restauration des mutations : `276/276` ;
  D3 et états visuels `32/32` ; huit fichiers JavaScript modifiés vérifiés par
  `node --check`, sans erreur de syntaxe ;
- smoke Chromium complet : `39/39`, sans échec, annulation ni skip, dont six
  scénarios D5. Le vrai wiring traverse WAV D3, STT, soumission canonique et
  POST TTS natifs interceptés localement. Les contrôles du lecteur portent sur
  un vrai `HTMLAudioElement` aux événements/promesses contrôlés ;
- deux tours utilisent un seul lecteur, deux object URLs et deux révocations.
  `waiting` et `pause` éteignent les animations sans micro ; seul `ended`
  réarme, après cleanup. Un `ended` dupliqué et la course `ended` puis Pause
  ne produisent pas de capture fantôme ;
- final vide, TTS indisponible, MP3 vide, refus du second `play()` et erreur
  média aboutissent strictement à `error`, sans reprise automatique. Pour les
  pannes de vocalisation, la réponse finale écrite reste dans le fil après
  fermeture. Le refus initial simulé n'acquiert aucun microphone ;
- preuve Chromium native distincte : un vrai clic crée le lecteur et invoque
  son vrai `play()` dans le handler synchrone sur l'amorce locale ; le même
  élément est transmis par identité au recorder D3. Ce test valide ce chemin
  Chromium, pas Safari iPhone ni la sortie sonore matérielle ;
- mutation animation anticipée : le vrai smoke reçoit `tts_speaking` avant
  `playing`, au lieu de `tts_pending`, et échoue directement ;
- mutation réarmement sur `waiting` : le même smoke observe une piste vivante
  pendant le buffering et échoue ;
- mutation révocation supprimée : après deux tours, zéro révocation au lieu de
  deux remet le témoin au rouge. Les trois mutations sont tuées par la chaîne
  navigateur réelle, pas par une recherche textuelle ;
- chaque mutation restaure les octets originaux dans un `finally` ; le
  contrôleur retrouve l'empreinte exacte
  `9b4aa003eca250f0c2f33a0741133f081c8316053e3a7eb7e5b00b3301eb0192`,
  puis le smoke complet et la suite unitaire repassent au vert ;
- revue finale des tests/docs : aucun finding vivant. Le libellé d'un refus
  simulé est corrigé pour ne pas le présenter comme une preuve native ;
- contre-audit : aucun full-duplex, second lecteur actif, double réarmement,
  écoute pendant TTS, URL oubliée, callback tardif efficace, second pipeline,
  log de contenu, test affaibli, dépendance ou changement D6. Backends D1/D2,
  final lock, VAD/ONNX épinglés, Whisper et `input_mode` sont inchangés ;
- Browser plugin absent : Playwright existant, serveur local et transports
  synthétiques inspectables, sans provider ni microphone physique. Capture
  visuelle mobile `tts_pending` inspectée à 390 × 844 ; les données de test et
  artefacts temporaires restent hors dépôt.

---

### Livraison D5 vérifiée — 9 septembre 2026

- commit applicatif poussé sur `main` :
  `5afc5a416bbf944d3f247d0857008545f65b25e3`, message
  `feat(dialogue): complete semi-duplex voice loop` ; HEAD/upstream égaux,
  divergence `0/0`, worktree propre avant reconstruction ;
- reconstruction avec le Compose d'autorité :
  `docker compose -p fridadev-app -f /opt/platform/fridadev-app/docker-compose.yml build --pull=false fridadev`,
  puis `up -d --no-deps --force-recreate fridadev`. Seul `platform-fridadev`
  est recréé, sans pull Git ni modification de Compose ;
- image livrée :
  `sha256:d8ff6e73b8612b77831dba2b2d4b133bc0d3a1505f3d8bb175427a2a984a194a` ;
- rollback conservé et vérifié avant reconstruction :
  `platform-fridadev-app:rollback-d5-20260909T200335Z`, image précédente
  `sha256:d6907e75766bdc95af2ba2825f2294d147718edea89a8a62a1417766d6fcaa84`.
  Ce tag permet de rétablir l'image applicative avec la même recréation ciblée,
  sans toucher aux données ni aux services voisins ;
- service démarré à `2026-09-09T20:04:00.071788586Z`, `running/healthy`,
  restart `0`, OOM `false`. Identité, image, démarrage, état, restart/OOM et
  health des `31` voisins strictement inchangés ; SHA-256 du relevé JSON
  normalisé (clés triées, séparateurs compacts, sans retour final) :
  `04fb8394d097e7be2621370727f8c5d208645141194e5d36bd3c576414409bd1` ;
- page et `17` scripts/assets/licences servis en HTTP interne `200` ; leurs
  `18` empreintes sont identiques entre checkout, disque du conteneur et corps
  HTTP. Les médias HTML, JavaScript et WASM sont corrects. Les `24` fichiers
  vérifiés sur disque, incluant les tests D5 et frontières backend, correspondent
  au checkout. SHA-256 du relevé complet chemin/statut/média/empreintes,
  selon la même sérialisation JSON normalisée :
  `d9b85b5804bb6b966ede4b78684705dcb38dfa657534cec59c88c467e1b2864d` ;
- le HTML servi conserve littéralement `disabled` sur le bouton Dialogue et
  ne charge aucun script VAD/ONNX au bootstrap. Le contrôle public sans
  authentification retourne `302` avec `Accept: text/html`, `401` sans cet
  en-tête ; la différence initiale de commande est ainsi reproduite et expliquée ;
- depuis le démarrage livré : zéro ligne `ERROR`, `CRITICAL` ou `Traceback`,
  zéro POST `/api/chat/dialogue/*` et zéro marqueur de fin provider STT/TTS.
  Aucun microphone physique, canari ni appel provider réel n'a été exécuté ;
- les voisins Python D1/D2/routes, Whisper et `input_mode` repassent `57/57`
  depuis l'image effectivement livrée, sans montage du checkout, sans réseau,
  sans données opérateur, filesystem read-only et `/tmp` en tmpfs ;
- hypothèses H1 à H4 et H6 à H10 confirmées sur les frontières et preuves
  décrites ci-dessus. H5 est confirmée comme garde navigateur : seul `playing`
  autorise l'animation ; cela ne mesure pas la sortie sonore matérielle. Pour
  H9, l'inertie locale est prouvée indépendamment de l'annulation du fetch,
  qui ne garantit pas l'arrêt du traitement serveur déjà reçu ;
- la réconciliation de livraison modifie seulement le contrat, la roadmap et
  le hub. Les fichiers runtime restent ceux du commit applicatif livré ;
  aucune deuxième reconstruction ou recréation n'est nécessaire.

**D5 FERMÉ ET LIVRÉ — BOUTON PRODUIT TOUJOURS DÉSACTIVÉ — D6 NON COMMENCÉ.**

---

## Lot D6 — activation contrôlée, livraison et retour automobile

**Livrable :** après la preuve de bout en bout D6.2, le bouton Dialogue devient
utilisable sur l'iPhone et la version est livrée avec rollback ciblé. L'usage
automobile est ensuite apprécié qualitativement par Tof, sans inspection ni
relevé pendant la conduite.

**Fichiers :**

- Modifier : `app/web/index.html` pour retirer `disabled` seulement après les
  preuves de ce lot
- Modifier : `app/web/app.js` si le gate d'ouverture le requiert
- Modifier : `app/tests/integration/frontend_browser/test_frontend_browser_smoke.js`
- Modifier : contrat et roadmap Dialogue

- [x] **D6.1 — Préflight déployé sans appel fournisseur**

  Vérifier HTTPS, permission micro après geste, chargement local du VAD, codec
  choisi, routes STT/TTS présentes, absence de secret dans le bundle, UI mobile
  stable et chat clavier inchangé. En cas d'échec, ne pas appeler OpenRouter.

  **Fermé : prérequis D6.1a livré, blocage Safari reproduit puis corrigé par un
  primer WAV silencieux décodable ; VAD et sortie matérielle vérifiés, sans appel
  fournisseur.**

### D6.1a — raccord préparatoire approuvé le 10 septembre 2026

- Baseline revalidée : `main`, HEAD/upstream
  `62e09e4743c8156bb1ab1f7d8c6670c898fa59c9`, divergence `0/0`, worktree propre.
- F1/F2 confirmés : le harnais dépend des adaptateurs au bootstrap et le
  listener précédent ouvrait seulement la vue. F3 confirmé : `routeToChat: false`
  conserve volontairement D3 seul, sans amorce D5. Ce contrat est préservé.
- Une fonction interne unique ouvre `d3_local`, `full` ou `local_preflight`.
  Le contrôleur visuel reste inchangé avec `entryButtonEl: null`. Le bouton
  produit servi demeure littéralement `disabled`, sans changement accessible.
- L'autorité produit est capturée une fois depuis le HTML servi. Une activation
  DOM après bootstrap, sans marqueur ou avec marqueur malformé, n'ouvre aucune
  session. Le marqueur exact `data-dialogue-preflight="local_preflight"` est
  consommé au clic physique, avec redésactivation immédiate avant l'amorce
  synchrone sur le lecteur unique transmis à D3.
- Le préflight ne construit aucun client STT/TTS, ne reçoit aucun submit chat
  et ignore le blob avant le travail de transport. Le constructeur refuse
  explicitement des capacités de transport dans ce mode. Aucun nouveau harnais
  global, route, paramètre, stockage, dépendance ou réglage audio.
- Rouges causaux observés : ouverture visuelle indue après activation DOM sans
  autorité ; zéro amorce dans le bootstrap normal et le futur clic complet ;
  marqueur non consommé ; configuration locale permissive acceptée et blob
  traité par le chemin complet au lieu d'être ignoré.
- Verts : `281/281` tests unitaires frontend ; sélection Chromium `31/31`
  (`14` scénarios hors sélection), incluant les six scénarios D6.1a,
  D3–D5, clavier, Whisper, mobile et desktop. Tests D1/D2 et routes : `39/39`,
  conteneur jetable sans réseau, checkout read-only, sans volumes opérateur.
- Chromium sans adaptateurs de bootstrap : amorce native dans la pile du clic,
  même lecteur dans D3, flux synthétique partagé, vrais assets ONNX/worklet/WASM
  same-origin et une inférence locale. Le segmenter épinglé produit ensuite un
  blob synthétique complet, sans client créé ni requête de transport. Cette
  preuve n'est pas Safari iPhone et ne sollicite aucun microphone physique.
- Pause, Terminer, fermeture, `pagehide`, permission refusée, assets/VAD refusés,
  changement de conversation et callbacks tardifs couverts. Les pistes déjà
  acquises s'arrêtent immédiatement ; une permission en attente ne peut ouvrir
  un VAD après invalidation. La reprise reste explicite.
- Mutations contrôlées : conservation du marqueur → témoin rouge sur sa
  consommation ; orientation du mode local vers `full` → témoin rouge sur
  un véritable essai HTTP intercepté par le test. Restauration exacte du fichier
  après chaque mutation, vérifiée par SHA-256. Aucun transport fournisseur réel.
- L'artefact `/tmp/fridadev-d61-reproduction.json` a été identifié comme le JSON
  content-free de la reproduction précédente, supprimé seul et son absence
  vérifiée. Aucun audio ou transcript n'est conservé dans les preuves.

### Livraison D6.1a vérifiée — 10 septembre 2026

- Commit applicatif `e56e5899697d9536c576688d7c0173a75a62ac0d` poussé sur
  `main`, avec HEAD/upstream égaux, divergence `0/0` et worktree propre avant
  reconstruction.
- Reconstruction via le Compose applicatif existant, `build --pull=false
  fridadev`, puis `up -d --no-deps --force-recreate --no-build --pull never
  fridadev`. Seul `platform-fridadev` a été recréé.
- Image livrée :
  `sha256:97f1de558e2dc5c17bda0350d4c3b1baa6ee152134eef3622027fbcae1318cf3`.
  État `running/healthy`, restart `0`, OOM `false`.
- Rollback ciblé conservé et vérifié :
  `platform-fridadev-app:rollback-d61a-20260910T094824Z`, image précédente
  `sha256:d8ff6e73b8612b77831dba2b2d4b133bc0d3a1505f3d8bb175427a2a984a194a`.
  Le retour arrière consiste à réassigner cette image au tag applicatif local
  puis recréer le seul service `fridadev`, sans build ni pull.
- `18/18` ressources web : HTTP `200`, médias attendus et SHA-256 identiques
  entre checkout, disque conteneur et réponse HTTP. Les `10/10` empreintes du
  manifeste VAD sont conservées. Les trois fichiers backend D1/D2 contrôlés
  correspondent aussi au checkout. Le HTML servi conserve `disabled`, sans
  marqueur DOM de préflight.
- HTTPS public : certificat vérifié, sans contournement Authelia ; accès non
  authentifié `302` pour HTML et `401` pour JSON. Ce contrôle serveur ne prouve
  pas encore `isSecureContext` dans Safari iPhone.
- Deux seuls smokes POST réels, content-free, en loopback du conteneur : `{}`
  vers STT → `422/multipart_required` ; `{}` vers TTS →
  `422/dialogue_tts_text_field_invalid`. Ces branches retournent avant tout
  appel au service fournisseur, prouvé par les contrats/tests et leurs sources
  identiques déployées. Aucun chat ou audio réel envoyé.
- Noms sensibles absents des sept sources propres au bootstrap/Dialogue
  inspectées ; requêtes d'assets D3 observées dans Chromium same-origin et sans
  header d'autorisation, clé API ou credential. Aucune valeur de secret lue.
- `31/31` voisins inchangés : IDs conteneur, images, états/health, restart et
  OOM identiques. L'absence de l'ancien artefact de reproduction est revérifiée.
- Cette consignation de livraison est documentaire seulement : aucun second
  rebuild ou redémarrage pour elle.

### Préflight matériel Safari iPhone — rouge causal du 10 septembre 2026

Preuve distincte des tests Chromium, rapportée par Tof depuis Safari iPhone
et son inspecteur Web. Le checkout de consignation est `main` à
`3e925f6ffeb0c37ce1aa6715229e4788c7c09fe3`, identique à l'upstream après
fetch, divergence `0/0`, worktree initial propre. L'image applicative reste
celle de la livraison D6.1a ci-dessus, `running/healthy`, restart `0`, OOM `false`.

| Étape | Fait rapporté par Tof |
| --- | --- |
| Ouverture normale via Authelia | Chat affiché sur l'iPhone ; inspecteur ouvert sur cet onglet. |
| Contrôle initial | `https`, `secureContext`, `microphoneDisponible`, `boutonDesactive`, `marqueurAbsent`, `harnaisAbsent`, `vadNonCharge` : tous `true`. La disponibilité de l'API n'est pas une permission accordée. |
| Préparation éphémère | `marqueurExact`, `boutonActiveLocalement`, `sessionFermee` : tous `true`, avant le clic. Panneau Réseau vidé, sans filtre. |
| Clic physique unique | Aucune demande de permission microphone. `marqueurConsomme: true`, `boutonRedesactive: true`, `sessionActive: true`, `etatLocal: listening`, `vadCharge: false`. La valeur `recorderCharge`, masquée dans le retour, n'est pas connue. |
| Vérification réseau | Panneau Réseau rapporté vide. Aucune requête D3, STT, chat ou TTS observée pendant l'essai. |
| Arrêt de l'essai | Terminer actionné sur l'iPhone ; retour au chat confirmé. Aucun essai bruit/parole ou reprise n'est ensuite demandé. |

**Qualification :** le préflight n'atteint pas le chargement D3 ni une écoute
effective démontrée. L'état visuel `listening` apparaît déjà avant ces étapes.
Le code de `openDialogueSession` attend `sessionController.whenReady()` avant
`loadDialogueD3()` ; cette readiness dépend de l'amorce `audio.play()` du
contrôleur existant. Une amorce restant en attente est compatible avec les
observations, mais aucune mesure directe de sa promesse ou de son erreur
Safari ne prouve encore cette cause. Aucun diagnostic de permission refusée
ou de VAD défaillant n'est établi.

| Finding D6.1 | Verdict borné aux preuves disponibles |
| --- | --- |
| H1 | Validé sur iPhone par les retours HTTPS/secure context derrière Authelia. |
| H2 | Absence de chargement au bootstrap confirmée sur iPhone ; chargement same-origin prouvé en Chromium et côté serveur, non atteint sur l'iPhone. |
| H3 | Condition de sortie non satisfaite : clic reconnu, mais permission et démarrage audio effectif non démontrés. |
| H4 | Flux partagé et cleanup prouvés par les tests ; capture réelle et arrêt de ses pistes non exercés sur l'iPhone. Terminer prouve seulement le retour visuel au chat dans cet essai. |
| H5 | Compatibilité WAV/D1 prouvée par contrats et tests ; aucun WAV matériel iPhone produit ou inspecté. |
| H6 | Routes déployées et rejets locaux `422` prouvés avant transport lors du préflight serveur. |
| H7 | Contrôles statiques et requêtes Chromium bornés au périmètre décrit dans la livraison ; aucune nouvelle requête observée dans l'essai iPhone. |
| H8 | Préparation Inspector, consommation unique et ouverture locale confirmées ; le préflight audio complet reste bloqué. |
| H9 | Régressions clavier, Whisper, mobile et desktop vertes ; ouverture et retour au chat confirmés sur iPhone. Aucune nouvelle soumission clavier réelle n'est effectuée. |

Les tests et mutations précédents restent des preuves hermétiques ; ils ne
ferment pas ce blocage matériel. Aucun audio, transcript ou log brut n'est
collecté. Le mode local livré n'a aucune capacité de transport STT/TTS/chat,
et aucune requête fournisseur n'est effectuée par ce lot.

Cette première consignation était docs-only : aucune correction automatique,
nouvelle instrumentation runtime, relance, reconstruction ou recréation de
service. Le micro-lot correctif distinct ci-dessous lui succède.

### Correctif et preuve matérielle D6.1 — 10 septembre 2026

- Inspection directe du seul `HTMLMediaElement.play()` sur Safari iPhone : le
  primer WAV livré, limité à un échantillon PCM16, atteint `loadedmetadata` puis
  échoue avec `MediaError.code=3` ; la promesse reste en attente et empêche
  `whenReady()` de libérer le chargement D3.
- Matrice sur le même appareil : un échantillon échoue ; huit, 32, 80, 160,
  320, 800 et 1 600 échantillons atteignent `canplay`. Huit est retenu comme
  plus petit candidat observé, sans changer le rôle silencieux de l'amorce.
- Substitution diagnostique strictement locale de l'ancienne data URI par le
  candidat : `play()` résolu, assets D3 same-origin chargés, permission micro
  accordée, global VAD présent et écoute effective. Une parole articulée donne
  `ÉCOUTE ACTIVE` → `JE T’ÉCOUTE` → `ÉCOUTE ACTIVE` ; Terminer fait passer
  l'unique piste audio de `live` à `ended` et ferme la vue.
- Rouge TDD ajouté au contrôleur : le primer doit contenir exactement huit
  échantillons PCM16 complets, soit un chunk `data` de 16 octets et un RIFF de
  60 octets. Sur l'ancien code, il observe 2 octets au lieu de 16.
- Patch minimal dans `dialogue_session_controller.js` : seule la data URI du
  silence passe de un à huit échantillons. Aucun flux, ordre, timeout, VAD,
  transport, bouton, harnais ou état n'est modifié.
- Verts frais : contrôleur `42/42`, frontend unitaire complet `282/282`,
  Chromium complet `45/45`, `node --check` et `git diff --check` réussis.
- Commit applicatif `624e97a5bfada6033691711d5dceb0333d505280`
  (`fix(dialogue): use Safari-decodable silent primer`) poussé sur `main`.
- Image livrée :
  `sha256:9c3a8f8c7ba8ceae15d456e76d5ba2e5000eb03718592eac02176b51c54a8bb5`.
  Seul `platform-fridadev` a été recréé ; état `running/healthy`, restart `0`,
  OOM `false`, HTTP interne `200`. Les empreintes checkout, conteneur et asset
  servi concordent. Les 31 voisins restent inchangés. Rollback disponible :
  `platform-fridadev-app:rollback-d61-primer-20260910T120744Z`.
- Rechargement propre sur l'iPhone après livraison : l'ancien monkeypatch est
  absent ; le clic physique franchit l'amorce du vrai code et charge D3. Tof
  confirme ensuite le cycle parole/silence demandé puis Terminer. Aucune requête
  vers STT, chat ou TTS n'est observée. Aucun audio ou transcript n'est collecté.
- Le bouton produit reste littéralement `disabled`. D6.2 à D6.5 et Z restent
  explicitement non commencés.

**D6.1 FERMÉ — PRÉFLIGHT SAFARI IPHONE VERT — AUCUN APPEL FOURNISSEUR.**

### D6.2a — entrée ponctuelle du canari — 10 septembre 2026

- [x] **D6.2a — Prérequis technique fermé et livré**

  Le canari D6.2 reste ouvert et non exécuté. Sa préparation physique et son
  premier appel réel exigent encore un `GO canari` distinct. Aucun appel
  fournisseur n'est autorisé par D6.2a.

- Baseline conforme : `/opt/platform/fridadev`, `main`, HEAD/upstream
  `b6803e65f0e702a1d73f67f920cf175062da2aef`, divergence `0/0`, worktree propre,
  y compris après fetch ; sans SSH ni pull.
- Diagnostic confirmé : autorité produit fausse avec le HTML `disabled`,
  marqueur précédent limité à `local_preflight`, harnais complet conditionné
  aux adaptateurs absents du bootstrap normal.
- Décision minimale : un seul cas exact `full_canary` dans le listener existant,
  après suppression du marqueur et redésactivation du bouton, appelle
  `openDialogueSession('full')`. Aucun second mode de session, listener,
  contrôleur, global runtime ou transport. L'autorité produit reste immuable.
- Rouge causal : clic Chromium trusted, marqueur consommé et bouton désactivé,
  mais aucune ouverture au HEAD initial (`[]` au lieu de `['full']`). Les
  variantes absente, vide, espaces, suffixe, casse et graphies proches restent
  refusées ; un événement synthétique reste inerte.
- Vert central sans adaptateurs de bootstrap : une ouverture `full`, `play()`
  natif dans le listener trusted avec marqueur déjà absent et bouton désactivé,
  lecteur identique transmis au vrai recorder, vrais assets VAD/ONNX locaux et
  flux synthétique. Une inférence locale puis le segmenter épinglé produisent
  un WAV qui traverse les clients D4/D5 de production : un POST STT, une
  soumission canonique `dialogue` transportée en `voice`, un POST TTS.
  Ces requêtes sont interceptées ; le TTS répond délibérément 503 et ferme
  le témoin sans fabriquer une preuve de lecture réussie.
- Deuxième clic après consommation, y compris après réactivation DOM seule :
  aucune autre ouverture, piste ou requête. `local_preflight`, le futur bouton
  servi autorisé, le harnais existant, le clavier, Whisper, mobile et desktop
  conservent leurs preuves. L'usage unique borne l'entrée ; il ne limite pas
  le nombre de tours de la boucle D5. Le budget réel relève du protocole D6.2.
- Mutation 1 : retrait du cas exact → même rouge d'ouverture. Mutation 2 :
  acceptation d'un marqueur quelconque → ouverture interdite, témoin rouge.
  Restaurations exactes après chacune, SHA-256 de `app.js` :
  `3e55447931e8ab5cc54c1b17cee392ec7e195436b17f9291c7832178067d4728`.
- Tests ciblés D6.1a/D6.2a : `7/7`. Validation complète après restauration :
  frontend unitaire `282/282`, toutes les suites Chromium `52/52` dont le smoke
  Dialogue `46/46`, backend D1/D2/routes `39/39`, sans échec, skip, annulation
  ni TODO. Le backend tourne dans l'image existante, réseau coupé, filesystem
  et checkout read-only, `/tmp` en tmpfs, sans volumes opérateur.
- La première suite Chromium élargie observait `51/52` : le témoin voisin
  du tiroir comparait strictement `-0` à `0`. Le même échec est reproduit avec
  `app.js` de la baseline puis du patch, restauré exactement. Son attente
  acceptait prématurément l'arrondi pendant la transition. Seule cette attente
  de test exige désormais la coordonnée réellement nulle ; assertion, timeout
  et UI sont inchangés. La suite complète repasse `52/52`.
- Contre-audit : valeurs inconnues sans retombée produit, clic non trusted
  inerte, consommation avant amorce, une seule chaîne existante, aucun nouveau
  stockage, secret, route, harnais ou appel réel. `node --check` sur les trois
  JavaScript touchés et `git diff --check` réussissent.
- L'exception bornée est consignée dans `AGENTS.md`, le contrat et le hub.
  D6.3 devra supprimer les deux valeurs et tout le mécanisme de marqueur.
  La livraison ciblée est vérifiée ci-dessous.

Commandes complètes : `node --test app/tests/unit/frontend_chat/*.js`,
`node --test --test-concurrency=1 app/tests/integration/frontend_browser/test_*.js`
et `python -B -m unittest tests.unit.chat.test_dialogue_stt_service
tests.unit.chat.test_dialogue_tts_service
tests.integration.chat.test_chat_dialogue_audio_routes` dans l'enveloppe
hermétique décrite ci-dessus. Aucun temporaire de preuve n'est conservé.

Livraison du 10 septembre 2026 à 14:42 UTC :

- Commit applicatif `4c13966b925a3fd63d1e62b330204b278c8fedcc`, poussé sur
  `main` ; HEAD = upstream, divergence `0/0`, worktree propre avant build.
- Compose applicatif existant : build `--pull=false`, puis recréation du seul
  service `fridadev` avec `--no-deps --force-recreate --no-build --pull never`.
  Image livrée :
  `sha256:3dd43f33b41f4cb35946b4bc42b96028a82eb34995054fce1f30e33b04d9a1d6`.
- Image précédente conservée et vérifiée sous
  `platform-fridadev-app:rollback-d62a-20260910T144203Z` :
  `sha256:9c3a8f8c7ba8ceae15d456e76d5ba2e5000eb03718592eac02176b51c54a8bb5`.
  Aucun rollback n'a été nécessaire.
- `platform-fridadev` : `running/healthy`, restart `0`, OOM `false`.
  Les 31 voisins ont les mêmes identités, images, états, dates de démarrage,
  compteurs de restart et états OOM/health qu'avant le lot.
- Douze empreintes de sources D1–D6.2a concordent entre checkout et conteneur ;
  les sept fichiers Web concordent aussi avec les assets servis en HTTP `200`,
  médias `text/html` et `application/javascript`. L'empreinte `app.js` est celle
  vérifiée après mutations ci-dessus. HTML toujours `disabled`, sans marqueur.
- HTTPS public : `302` vers la protection existante, vérification TLS `0`,
  sans authentification ni contournement d'Authelia. Cette vérification serveur
  ne constitue pas une preuve Safari iPhone du canari complet.
- Aucun POST STT/chat/TTS vers le runtime, aucun appel fournisseur et aucun
  geste iPhone demandé. Cette clôture documentaire ne déclenche aucun second
  build ni restart. D6.2 reste ouvert, sous `GO canari` distinct.

**D6.2a FERMÉ ET LIVRÉ — D6.2 OUVERT — AUCUN APPEL FOURNISSEUR — GO CANARI DISTINCT REQUIS.**

### D6.2b — alignement sur le V5 validé dans le démonstrateur — 10 septembre 2026

- [x] **D6.2b — Correctif technique fermé et livré**

- Baseline conforme : `/opt/platform/fridadev`, `main`, HEAD/upstream
  `148fb82244c618018eabc10b2fa5efe255b454ea`, divergence `0/0`, worktree propre.
  Aucun SSH ni pull. L'autorisation utilisateur porte sur ce seul correctif,
  sans microphone matériel ni appel fournisseur.
- Diagnostic confirmé au HEAD : modèle `legacy`, seuils par défaut implicites,
  garde de frame `1536`, V5 local absent, affirmation de calibration Safari
  erronée dans le manifeste. Le WAV parasite non vide et la validation Safari
  du démonstrateur sont les faits rapportés par Tof, pas de nouvelles mesures
  de ce lot. Le seuil `0,96` est retiré ; aucun filtre sonore n'est ajouté.
- Sources primaires : [algorithme](https://github.com/ricky0123/vad/blob/master/docs/user-guide/algorithm.md),
  [source officiel du démonstrateur](https://github.com/ricky0123/vad/blob/8941bbf9116234748934d6b563c1751ce4d43c35/test-site/src/script-tags-example/index.html)
  (`v5`, `0.4/0.4`, ORT `1.22.0`) et distribution npm `0.0.30` vérifiée
  par son intégrité SHA-512. Le hostname du démonstrateur ne se résout pas
  depuis cette machine : ses assets déployés n'ont pas été relus directement.
  Les empreintes bundle/worklet fournies par Tof correspondent exactement aux
  fichiers locaux et à la distribution officielle épinglée.
- V5 extrait sans modification : 2 327 524 octets,
  SHA-256 `2623a2953f6ff3d2c1e61740c6cdb7168133479b267dfef114a4a3cc5bdd788f`.
  Le modèle legacy est supprimé du vendor et des listes d'assets actives.
  Le bundle upstream reste intact, y compris ses internals non sélectionnés.
- Quatre rouges causaux avant patch : sélection `legacy` au lieu de `v5`,
  frame V5 rejetée `vad_frame_invalid`, asset V5 absent, ancienne affirmation
  documentaire fausse. Aucun faux vert de harnais ni erreur d'import.
- Patch strict : modèle V5, probabilités `0.4/0.4`, AudioWorklet,
  `startOnLoad: false`, garde fixe `512`. Options temporelles inchangées
  800 / 1 400 / 400 ms ; le segmenter `0.0.30` les arrondit à 25 / 43 / 12
  frames de 32 ms. Aucune option d'entrée obsolète en frames n'est copiée.
- Segmentation déterministe : onze frames positives rejetées, douze acceptées ;
  quarante-deux négatives ne terminent pas, la quarante-troisième termine.
  Les probabilités `0.399` et `0.4` sont injectées indépendamment de l'amplitude
  des échantillons ; ce test n'est pas une classification acoustique.
- Après 384 s de bruit/silence synthétique, 25 frames de pré-roll, 15 de parole
  et 43 de fin produisent exactement 42 496 échantillons, 2 656 ms et
  85 036 octets WAV. En-tête RIFF/PCM16 mono 16 kHz et chaque échantillon PCM
  sont contrôlés. Une attente de 960 s reste bornée sans expiration ni blob.
  Les bornes 300 s / 24 000 000 octets et leur rejet adjacent restent vertes.
- Chromium utilise le vrai V5/ONNX local, une inférence réelle sur flux
  synthétique puis le segmenter piloté, avec décodage WAV à 16 kHz. Les chemins
  D3, `local_preflight` et `full_canary`, la consommation du marqueur, les
  états, le flux unique, le cleanup et les transports interceptés sont verts.
- Mutations : retour au modèle `legacy` → témoin de sélection rouge ; retour
  à `1536` → témoin de frame rouge. Après chacune, restauration exacte de
  `dialogue_vad_runtime.js`, SHA-256
  `6276365fb785ee002f69a5f54d0a55ef58fb60be8c17a2b6623bf7264c548208`,
  puis témoin vert.
- Validation après restauration : D3/D4/D5 ciblés `110/110`, frontend unitaire complet `286/286`,
  Chromium complet `52/52`, voisins Python D1/D2/routes/Whisper `63/63` ;
  aucun skip, échec, annulation ni timeout augmenté. Python utilise l'image
  applicative existante, `--network none`, filesystem et checkout read-only,
  `/tmp` en tmpfs, aucun volume opérateur. Ses tentatives d'initialisation DB
  loopback échouent dans cette enveloppe sans joindre la DB réelle.
- Contre-audit : aucun appelant Frida legacy actif, RMS, seuil de volume,
  second flux, nouveau transport, fallback, activation produit ou contenu
  collecté. D1/D2/D4/D5, recorder, bouton HTML et wiring D6.1a/D6.2a inchangés.
  STT vide/blanc → `paused`, aucun chat/TTS, reprise explicite uniquement.
  La correction de sélection ne prouve pas encore l'acceptabilité sur iPhone.
- `node --check` sur les sept JavaScript touchés, `git diff --check`, dix
  empreintes vendor et neuf liens locaux vérifiés. Aucun temporaire conservé.
  `AGENTS.md` reste inchangé : il autorise déjà les corrections de bugs et
  n'impose pas legacy ; aucune instruction agent supplémentaire n'est requise.

Commandes de preuve :

```bash
node --test app/tests/unit/frontend_chat/test_dialogue_vad_*.js
node --test app/tests/unit/frontend_chat/*.js
node --test --test-concurrency=1 app/tests/integration/frontend_browser/test_*.js
```

Python hermétique : `python -B -m unittest` avec
`tests.unit.chat.test_dialogue_stt_service`,
`tests.unit.chat.test_dialogue_tts_service`,
`tests.integration.chat.test_chat_dialogue_audio_routes`,
`tests.unit.chat.test_whisper_transcription_service`,
`tests.integration.chat.test_chat_transcription_route` et
`tests.integration.frontend_chat.test_frontend_whisper_contract`.

Livraison vérifiée le 10 septembre 2026 à 16:39 UTC :

- Commit applicatif `661cc4f29f121100b98f44238b6d6a09c709df1a` poussé sur
  `main`, HEAD = upstream, divergence `0/0`, worktree propre avant build.
- Image active précédente conservée sous
  `platform-fridadev-app:rollback-d62b-20260910T163913Z`, empreinte vérifiée
  `sha256:3dd43f33b41f4cb35946b4bc42b96028a82eb34995054fce1f30e33b04d9a1d6`.
- Compose applicatif inchangé : `build --pull=false fridadev`, dépendances en
  cache, puis `up -d --no-deps --force-recreate --no-build --pull never fridadev`.
  Seul `platform-fridadev` est recréé. Image livrée :
  `sha256:84d5d6448e065df38fdf786cc0a81e64608af832e32ec1cc166c5fdff3363bad`.
- Runtime `running/healthy`, restart `0`, OOM `false`. Les 31 voisins conservent
  exactement leurs identités, images, démarrages, états, health, restart et OOM.
- Vingt-trois empreintes checkout/conteneur concordent, dont dix-huit aussi
  avec les réponses HTTP `200`. V5 : `application/octet-stream`, 2 327 524
  octets, SHA-256 exact `2623a2953f6ff3d2c1e61740c6cdb7168133479b267dfef114a4a3cc5bdd788f`.
  Legacy absent sur disque et HTTP `404`. HTML toujours `disabled`, sans marqueur.
- Zéro marqueur de succès provider STT/TTS dans les logs depuis le nouveau
  démarrage (`2026-09-10T16:39:41.502444701Z`) ; également zéro pendant la
  fenêtre de contrôle pré-livraison depuis 16:29:47 UTC. Aucun log brut, contenu
  audio, transcript ou secret n'est conservé dans les preuves. Aucun appel réel
  STT/chat/TTS ni microphone matériel n'est déclenché par le lot.
- Cette clôture est documentaire seulement : aucun second rebuild/restart.
  Le nouveau canari iPhone reste à conduire par Tof dans un lot distinct.

**D6.2b FERMÉ — D6.2 OUVERT — NOUVEAU CANARI IPHONE REQUIS.**

- [x] **D6.2 — Canari fournisseur borné hors voiture**

  Nouveau canari matériel après alignement V5 D6.2b : une seule parole courte
  puis une seule réponse Frida, en ouvrant la session
  par le marqueur éphémère exact `full_canary` livré en D6.2a, après un
  `GO canari` distinct, tant que le bouton servi reste désactivé. Prouver
  dans le même thread : transcript envoyé une fois, traitement canonique,
  réponse persistée, voix Soleil entendue, animation calée sur l'audio,
  réarmement après fin.
  Budgéter explicitement le nombre maximum d'appels : un STT et un TTS, hors
  appel chat ordinaire déjà nécessaire.

  **Fermé le 11 septembre 2026 sur Safari réel, iPhone 11 :** le marqueur
  ponctuel `full_canary` a ouvert une session unique. Une parole courte a
  produit exactement un STT `200` (1 063 ms), un chat canonique `200`
  (15 922 ms) et un TTS `200` (1 418 ms), sans retry. La voix Soleil a été
  entendue. La projection observée a suivi `listening → user_speaking →
  transcribing → thinking → tts_pending → tts_speaking → tts_pending →
  listening`, puis l'action Terminer a retiré l'état Dialogue.

  Après réarmement, un raclement de gorge isolé suivi de cinq secondes
  d'attente n'a produit ni transition supplémentaire ni nouvel appel STT,
  chat ou TTS. La persistance a été contrôlée sans lire le contenu : avant et
  après recharge complète, le fil contenait les mêmes 408 messages, répartis
  en 204 tours utilisateur et 204 tours Frida. Après Terminer, le bouton était
  de nouveau désactivé, le marqueur absent et l'observateur content-free
  temporaire supprimé. Le canari n'établit pas encore le comportement en
  voiture ; celui-ci reste réservé au retour d'usage D6.5.

**D6.2 FERMÉ — D6.3-bis FERMÉ — D6.3 NON COMMENCÉ.**

- [x] **D6.3-bis — Stabiliser l'autorité de présentation téléphone**

  **Défaut utilisateur reproduit le 11 septembre 2026.** Sur l'iPhone, la
  présentation `Alternative B — Dialogue vivant` est actuellement décidée par
  le seul prédicat CSS/JavaScript `max-width: 640px`. En paysage, la largeur
  dépasse ce seuil et le navigateur rebascule vers la composition de bureau.
  Après un lancement à froid suivi du parcours Authelia, le premier retour vers
  FridaDev peut également présenter la composition de bureau ; fermer puis
  relancer l'application avec la session authentifiée rétablit la composition
  téléphone. Le premier défaut est reproduit automatiquement. Le mécanisme
  précis du retour d'authentification reste à mesurer ; l'architecture actuelle
  ne possède dans tous les cas aucune autorité stable « téléphone » à
  resynchroniser après ce retour.

  **Contrat attendu.** Sur un iPhone, la présentation téléphone reste active en
  portrait comme en paysage. L'orientation ne choisit jamais entre téléphone et
  bureau ; elle ne règle que la géométrie interne de la même présentation. Un
  lancement à froid, le retour d'Authelia et une restauration par le navigateur
  resynchronisent immédiatement cette autorité. Un navigateur de bureau reste
  sur la présentation de bureau. Le thème de bureau persisté, les conversations,
  répertoires, fichiers, notes, outils et le mode Dialogue ne changent pas.

  **Correctif borné.** Définir une seule autorité frontend de contexte téléphone
  dans `chat_theme.js`, sans branchement serveur ni sniffing de chaîne User-Agent,
  puis la projeter sur la racine du document. Faire consommer cette même autorité
  par le thème mobile, la sidebar, les outils mobiles, les sorties du mode
  Dialogue et les règles CSS de la composition iPhone. Le breakpoint étroit ne
  reste qu'un fallback responsive ; les media queries d'orientation ou de taille
  ne règlent que la géométrie. Resynchroniser sur le chargement, les changements
  pertinents et `pageshow`, notamment après retour d'authentification. Ne modifier
  ni Authelia, ni Caddy, ni backend, ni route, ni persistance, ni D1–D5.

  **Preuves obligatoires avant fermeture.** TDD rouge/vert sur : iPhone portrait,
  le même iPhone en paysage, retour simulé d'authentification/restauration,
  fallback responsive étroit et ordinateur large restant en bureau. Rejouer les
  tests unitaires frontend concernés, le smoke Chromium mobile et les voisins du
  chat clavier/Dialogue. Vérifier que la rotation ne ferme pas une session
  Dialogue uniquement parce que la largeur franchit 640 px. Contre-auditer les
  détecteurs concurrents, les règles CSS encore enfermées sous le breakpoint, la
  perte de capacités de sidebar et toute divergence desktop. Livrer uniquement
  `platform-fridadev` avec rollback si et seulement si les preuves sont vertes.

  D6.3-bis est exécuté avant l'activation produit D6.3 afin de stabiliser le
  contenant mobile ; il ne retire pas `disabled` et n'active aucun appel audio.

  **Fermeture du 11 septembre 2026.** Le cadrage a été consigné avant le code
  dans `fa4888b4cd4b3149b33f20f31c4bc43f2e2ec8b3`. Le rouge TDD a confirmé
  l'absence d'autorité téléphone stable : trois témoins unitaires échouaient et
  le scénario Chromium perdait la présentation en passant de `414 × 896` à
  `896 × 414`. Le correctif `62388eeb92e5b71a8701b08be9e9f744d5609538`
  centralise la décision dans `chat_theme.js` : petit côté d'écran borné,
  capacité tactile ou mode standalone, breakpoint étroit conservé comme
  fallback, sans sniffing User-Agent. `app.js` et les règles CSS consomment
  cette seule autorité ; `pageshow` la resynchronise après navigation,
  authentification ou restauration navigateur.

  Après restauration du correctif exact, les tests unitaires frontend passent
  `289/289` et les scénarios Chromium `53/53`, sans échec ni skip. La preuve
  navigateur conserve la composition téléphone, l'écran Dialogue, le menu et
  l'absence de débordement horizontal en portrait et paysage, puis restaure les
  attributs de présentation sur `pageshow`. Le grand écran tactile reste en
  bureau et le fallback responsive étroit est préservé. Le retour Authelia
  réel n'a pas été rejoué matériellement dans ce lot : sa frontière frontend
  est couverte par un chargement téléphone et par le témoin déterministe
  `pageshow`, sans changement d'Authelia ou de Caddy.

  Seul `platform-fridadev` a été reconstruit sans pull puis recréé avec
  `--no-deps`. Image livrée :
  `sha256:0e742e7d4f164afa87854120b9688ee1075e587fed772d1157840174d82fe6ee` ;
  rollback : `platform-fridadev-app:rollback-d63bis-20260911T071721Z`.
  Le service est `running/healthy`, HTTP interne `200`, restart `0`, OOM
  `false`. Les empreintes de `app.js`, `chat_theme.js` et `styles.css`
  concordent entre checkout, conteneur et HTTP servi ; les 31 voisins sont
  inchangés. Le bouton Dialogue reste littéralement `disabled`. D6.3 n'est pas
  commencé.

  **D6.3-bis FERMÉ ET LIVRÉ — D6.3 NON COMMENCÉ.**

- [ ] **D6.3 — Activer le bouton et rejouer les preuves**

  Retirer `disabled`, conserver l'accessibilité clavier et tactile, puis rejouer
  les tests frontend, les deux routes backend, le smoke mobile et le chemin chat
  clavier. Retirer explicitement tout le mécanisme DOM de D6.1a/D6.2a,
  y compris `local_preflight` et `full_canary`.
  Le HTML servi actif donnera l'autorité au bootstrap : conserver exactement
  le même listener et la même fonction d'ouverture vers `full`, sans second
  wiring. Aucun autre contrôle ou écran n'est ajouté.

- [ ] **D6.4 — Livrer avec rollback**

  Reconstruire et recréer seulement `platform-fridadev`, sans pull implicite ni
  dépendance. Vérifier HTTP, health, restart, OOM, empreintes et voisins. Conserver
  l'image précédente pour rollback ciblé.

  Commit attendu : `feat(dialogue): activate mobile voice conversation`.

- [ ] **D6.5 — Expérience réelle et retour utilisateur**

  Utiliser le mode Dialogue normalement sur l'iPhone, notamment en voiture,
  radio et médias arrêtés pendant l'écoute. Aucun inspecteur, métrique, relevé
  technique ni manipulation du téléphone n'est demandé pendant la conduite.
  Après le trajet, Tof donne seulement son appréciation d'usage : faux départs
  gênants, détection de la parole, coupures, délai ressenti, compréhension,
  qualité de la voix, réarmement et confort général. Le fil écrit ordinaire
  reste disponible après coup si une incompréhension doit être examinée.

  Ce retour qualitatif ne prétend pas mesurer le système. Un défaut rapporté
  est consigné comme symptôme d'usage, puis reproduit à l'arrêt avant tout
  correctif. Il ne justifie ni changement de modèle, ni filtre sonore, ni
  fallback sans micro-lot et décision explicites.

**Stop D6 :** si D6.3 révèle une régression d'activation ou si D6.4 échoue à
livrer proprement, ne pas activer ou conserver la version concernée. Pendant
D6.5, la sécurité de conduite prime absolument : aucune preuve technique n'est
collectée au volant. Corriger ensuite une seule cause reproductible dans un
micro-lot distinct.

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
