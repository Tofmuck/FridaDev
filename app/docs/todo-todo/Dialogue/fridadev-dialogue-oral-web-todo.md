# FridaDev — dialogue oral greffé sur le pipeline Web

Date de cadrage initial : 7 septembre 2026.
Dernière mise à jour de reconnaissance : 10 septembre 2026.

**Statut : contrat initial et reconnaissance technique iPhone consignés. Les
choix V1 du VAD, du STT et du TTS sont retenus ; seule leur invalidation par le
test automobile réel peut les rouvrir. Le squelette visuel Figma et son
contrôleur local d'états sont intégrés. Les frontières backend STT D1 et TTS D2
sont implémentées et livrées. La capture locale D3 est corrigée, refermée et
livrée avec pré-roll borné et assets optionnels. D4 raccorde désormais le WAV à
D1 puis au chat canonique, initialement dans le harnais synthétique ; D4 est fermé,
poussé et livré après toutes les preuves et la vérification runtime. L'entrée
produit reste désactivée. D5 est fermé, poussé et livré après vérification runtime :
TTS frontend, lecteur possédé et réarmement après fin, initialement dans le harnais.
D6.1 est fermé : le préflight local sans transport fonctionne sur Safari iPhone
après remplacement du primer WAV d'un échantillon, rejeté par le décodeur, par
un primer silencieux de huit échantillons. Le VAD matériel, la distinction
parole/silence et la sortie de session ont été vérifiés sans appel fournisseur.
D6.2a prépare l'entrée ponctuelle `full_canary` vers cette même chaîne.
D6.2 reste ouvert, sans canari exécuté et sous `GO canari` distinct.
D6.3 à D6.5 et Z restent non commencés.**

## Intention

Le premier mode de dialogue oral reste volontairement simple : il se greffe
sur le chat Web existant. Le STT local actuel de `frida-system.fr`, jugé
médiocre pour cet usage, est contourné au profit d'un modèle STT en ligne. Le
pipeline dialogique de Frida reste inchangé.

Le lieu d'usage visé est la voiture, avec le téléphone. La référence pratique
est l'expérience déjà obtenue avec l'application ChatGPT : parler sans devoir
manipuler l'interface entre chaque tour, entendre la réponse, puis pouvoir
parler de nouveau.

## Contrat clair

1. Le mode dialogue arme le microphone.
2. Un détecteur local repère le début d'une parole articulée et commence
   l'enregistrement.
3. Après `x` secondes sans articulation — pas simplement sans bruit — l'énoncé
   est clôturé.
4. L'audio est envoyé à un modèle STT en ligne via le backend
   Frida/OpenRouter.
5. La transcription apparaît dans le chat et est automatiquement soumise comme
   l'est actuellement le résultat Whisper.
6. Tout le traitement habituel s'exécute sans exception : Stimmung, contexte,
   Memory, Identity, Validation, outils, sauvegarde et streaming.
7. La réponse de Frida est vocalisée.
8. À la fin de sa lecture, le microphone se réarme et le cycle recommence.

## Lecture la plus rapide possible

Deux niveaux sont distingués :

- première version sûre : attendre la réponse finale canonique, puis lancer
  immédiatement le TTS ;
- optimisation suivante : dès qu'une phrase stable arrive dans le stream,
  l'envoyer au TTS et la lire pendant que Frida génère la suite.

La seconde option réduit fortement la latence ressentie, mais ne fait pas
partie automatiquement de la première version.

## Détection et seuil de fin de tour

Le seuil `x` reste à déterminer expérimentalement. Il doit être réglable : un
seuil trop court coupe les hésitations et les pauses internes ; un seuil trop
long donne l'impression que Frida tarde à répondre.

La condition recherchée est une absence de parole articulée, non une simple
baisse de volume. Le détecteur de parole reste local au navigateur. Le STT en
ligne reçoit ensuite l'énoncé borné ; il ne devient pas le mécanisme permanent
d'écoute du microphone.

## Invariants de cette première version

- Le chat Web et la conversation courante restent l'autorité.
- La transcription devient un message utilisateur ordinaire du chat.
- La vue Dialogue n'affiche pas la transcription reconnue. En cas
  d'incompréhension, la réparation se fait dans le dialogue ; après avoir
  quitté ce mode, le texte effectivement envoyé reste consultable dans le fil
  normal comme tout message utilisateur.
- Aucun second pipeline dialogique n'est créé.
- Le STT local actuel est contourné pour ce mode, pas présenté comme amélioré.
- Le microphone n'écoute pas les reprises pendant la lecture de Frida dans la
  première version.
- L'interruption de Frida, le full-duplex et la reprise pendant le TTS sont des
  évolutions ultérieures distinctes.
- Le STT V1 retenu est `microsoft/mai-transcribe-2`. Le TTS V1 retenu est
  `microsoft/mai-voice-2-flash`, avec la voix
  `fr-FR-Soleil:MAI-Voice-2`. Ces deux choix ne sont pas remis en concurrence
  sans échec concret du test automobile ou changement du contrat fournisseur.
- Le seuil `x` reste à éprouver par le canari automobile. L'autorité D3 courante
  est un unique WAV `audio/wav`, PCM16 mono à 16 kHz, produit à partir du
  Float32 segmenté par le VAD. Il n'existe aucune préférence MP4/WebM/OGG,
  négociation de codec ni fallback automatique de format ou de modèle.

## Contrat visuel et animations

La maquette Figma distingue deux familles d'animation. Elle fixe leur aspect,
pas leur déclenchement runtime : aucune boucle exportée par Figma ne doit être
recopiée comme une animation permanente.

- Le petit signal à ondes représente une **parole effectivement détectée**. Il
  s'anime quand le VAD reconnaît la parole de Tof et, pendant la réponse, quand
  l'audio TTS de Frida est effectivement lu. Il ne réagit ni au silence, ni au
  bruit ambiant rejeté par le VAD, ni à une simple requête réseau en cours.
- L'animation propre de Frida — orbe, halo et relief autour du logo — est
  réservée à la voix de Frida. Elle ne commence qu'avec la lecture audio TTS
  effective et s'arrête ou se suspend sur pause, attente de données, fin,
  erreur, abandon ou neutralisation de cette lecture.
- En écoute armée mais silencieuse, l'orbe et le signal vocal restent dans leur
  état visuel de repos. Pendant la transcription et la réflexion de Frida, ils
  restent également au repos ; seul le libellé d'état change.
- Quand Tof parle, seul le signal vocal s'anime. Quand Frida parle, son
  animation et le signal vocal peuvent s'animer ensemble.
- Le mode reste semi-duplex : avant d'armer le microphone, la radio, les médias
  et le propre TTS de Frida sont neutralisés. Les animations ne doivent donc
  jamais fabriquer l'apparence de deux locuteurs simultanés.

La vue Dialogue n'est pas une surface de contrôle de dictée. Elle montre les
états fonctionnels nécessaires — écoute, transcription, réflexion, parole,
pause ou erreur — sans afficher le texte STT. Le fil normal demeure la surface
d'inspection a posteriori du texte réellement envoyé et de la réponse reçue.

### Squelette UI intégré — 9 septembre 2026

La composition Figma `Mobile sombre — Mode dialogue — Écoute` (`106:4`) est
intégrée au frontend mobile avec ses SVG d'autorité, le PNG transparent Frida,
les safe areas Safari et un contrôleur local fermé sur les états `listening`,
`user_speaking`, `transcribing`, `thinking`, `tts_speaking`, `paused` et
`error`. Elle ne dessine pas la barre d'état ni l'indicateur d'accueil iOS,
qui appartiennent au système.

Le harnais synthétique prouve les règles d'animation sans fabriquer de capacité
audio : repos en écoute silencieuse, onde seule pour `user_speaking`, repos en
transcription et réflexion, onde et orbe ensemble pour `tts_speaking`, repos en
pause ou erreur. Aucun microphone, VAD, enregistrement, STT, TTS, endpoint ou
provider n'est raccordé. Le bouton produit reste désactivé ; l'écran ne peut
être ouvert que par le contrôleur de test jusqu'au lot audio autorisé.

### Capture locale D3 corrigée — 9 septembre 2026

D3 a été rouvert : le cycle complet depuis `arm()` et le chargement obligatoire
du VAD au bootstrap étaient des défauts, pas des variantes autorisées du contrat.
La correction est prouvée, poussée et livrée ; D3 est définitivement refermé.

Le module `createDialogueVadRecorder(options)` conserve `arm()`, `pause()`,
`resume()`, `stop()` et les seuls événements `speech-start`, `speech-end`,
`blob`, `error`. Un blob contient exclusivement l'énoncé reconnu et son
pré-roll borné, jamais l'attente silencieuse depuis l'armement. Son événement
porte uniquement le Blob, `audio/wav`, sa durée et sa taille, sans transcript.

La distribution reste `@ricky0123/vad-web@0.0.30`,
`onnxruntime-web@1.22.0`, modèle Silero `legacy`; versions, intégrités npm,
SHA-256 et licences restent inchangés dans `vendor/dialogue-vad/MANIFEST.md`.
Aucun CDN, package nouveau ou téléchargement tiers au runtime.

Le code fournisseur épinglé est l'autorité technique :
`onSpeechEnd(audio)` reçoit un `Float32Array` mono à 16 000 Hz. Le worklet
rééchantillonne à cette fréquence. Le segmenter concatène son buffer seulement
après parole reconnue et fin VAD. En attente, il conserve au plus
`floor(800 / 96) = 8` trames legacy de 1 536 échantillons, soit 768 ms de
pré-roll effectif, inférieur au plafond configuré de 800 ms. Le début du premier
mot est conservé. La fin inclut le silence de fermeture VAD
(`floor(1400 / 96) = 14` trames, 1 344 ms), pas une attente antérieure libre.

D3 convertit ce seul tableau en WAV RIFF mono PCM16 little-endian : en-tête de
44 octets, 2 octets par échantillon. La durée est `audio.length / 16` ms,
indépendante de l'âge de `arm()`. À exactement 300 000 ms : 4 800 000
échantillons, 9 600 044 octets. Le plafond de 24 000 000 octets reste une
garde indépendante, naturellement non atteignable par ce WAV sous 300 s.
Les bornes sont inclusives ; le premier échantillon excédentaire ou le premier
octet excédentaire provoque `error`, sans émission ni troncature. Le MIME
`audio/wav` est déjà admis par D1 ; aucune négociation de codec ni fallback.

Il n'existe plus de MediaRecorder, de fragments continus ou de timer depuis
l'armement. Un seul MediaStream est acquis après geste et neutralisation certaine
des médias contrôlables, puis injecté par identité au VAD. L'adaptateur épinglé
contrôle aussi la taille projetée du buffer au callback interne
`FrameProcessed`, avant l'ajout de la trame et avant toute concaténation :
aucun énoncé en cours ne peut accumuler un buffer hors borne. Une inférence
concurrente est refusée en erreur fermée, sans file d'attente ni perte silencieuse.

Pause, sortie et erreur arrêtent immédiatement les pistes et détruisent VAD,
graphe, buffer, modèle et contexte possédé. Le cleanup attend une initialisation
ou une inférence en vol avant de libérer son modèle ; les callbacks invalidés
ne peuvent plus ajouter une trame ou émettre. Les appels concurrents partagent
le cleanup. Seule une reprise explicitement actionnée acquiert un nouveau flux ;
aucune erreur ne réarme. Bruit rejeté, misfire ou fin dupliquée : aucun blob
supplémentaire. Aucun buffer audio n'est conservé par le wiring visuel.

Le chargement normal du chat ne demande aucun script, modèle, worklet, WASM ou
MJS D3 et ne dépend d'aucun global VAD. L'ouverture explicite du harnais de test
ou du préflight local D6.1a décrit ci-dessous charge, une fois et dans l'ordre,
les scripts locaux, puis initialise le VAD.
Un asset absent/refusé met uniquement D3 en erreur ; le chat clavier demeure
utilisable. Pause ou fermeture pendant ce chargement ne déclenche aucun micro
tardif. Le bouton produit reste littéralement `disabled`.

L'adaptateur reste volontairement lié aux internals de la version épinglée ;
une montée de version doit revalider segmentation, pré-roll, ordre des callbacks,
bornes et cleanup. D3 projette seulement `listening → user_speaking → listening`,
pause et erreur. Il ne raccorde ni D1, ni D2, ni chat, ni Whisper, ni TTS.
Le raccord D4 distinct est décrit ci-dessous ; D3 seul conserve ce comportement.

## Raccord D4 au chat canonique — 9 septembre 2026

L'autorisation D4 est explicite et limitée au harnais existant :
`FridaDialogueD3Harness.openAndArm({ routeToChat: true })`. Sans cette option,
le harnais conserve les preuves locales D3 sans STT ; sans les adaptateurs de
test, ce harnais est absent. Le bouton produit reste littéralement `disabled`.
Le chargement normal ajoute seulement deux petits modules JavaScript D4,
sans charger les assets VAD/ONNX de D3.

`dialogueAudioClient.transcribe(blob, { signal }?)` valide avant fetch un vrai
Blob, le MIME exact `audio/wav` et une taille comprise entre 1 et 24 000 000
octets inclus. Il envoie une seule requête multipart vers
`/api/chat/dialogue/transcribe` avec un seul champ `audio` et un nom `.wav`.
Le navigateur construit la boundary. Un succès exige HTTP réussi, média JSON,
`ok === true` et `text` chaîne ; une chaîne vide est un succès vide. Les erreurs
HTTP, JSON, transport et interruption restent fermées et content-free. Aucun
retry, fallback, cache, journal de transcript ou appel OpenRouter direct.

La session possède ses générations et ses opérations. Dès le Blob, elle
suspend D3 et attend son cleanup avant le POST STT. Elle vérifie session,
conversation et `chatRequestInFlight` avant la transcription et la soumission.
Le changement de conversation invalide aussi un aller-retour vers le même
thread. Pause, Terminer et fermeture invalident et annulent le STT ; une réponse
qui ignore cette annulation ne peut plus créer de message ou modifier la vue.
Un Blob dupliqué est refusé, y compris après une reprise explicite ; la garde
utilise des références faibles, sans retenir l'audio.

Un transcript non vide mène à `thinking`, puis à l'unique
`submitCanonicalChatMessage(text, inputMode)` extraite du handler de formulaire.
Clavier, Whisper et Dialogue partagent le thread, le message utilisateur,
`chatRequestInFlight`, streaming, terminal/final lock, cache, réhydratation,
métadonnées et erreurs. La provenance interne `dialogue` devient `voice` avant
le transport ; Whisper reste `voice` et le clavier `keyboard`. Aucun schéma,
`chat_session_flow.py`, prompt, backend ou mécanisme de persistance ne change.
Le transcript ne remplit jamais le textarea et n'est jamais rendu dans la vue
Dialogue ; seul le message utilisateur normal du fil le rend consultable.
Le brouillon clavier déjà présent est conservé lors d'une soumission Dialogue.

La réussite finale canonique retourne `{ ok: true, text: reply }` : `reply` est
le texte du final lock et un `final_text: ""` reste exactement vide, sans
réutiliser le brouillon streamé. À la clôture D4, le contrôleur ignore `text`, projette
`paused` et garde le microphone désarmé. Les résultats `busy`, `empty` et
`chat_failed` ne portent aucun texte. Un STT vide, y compris uniquement des
espaces, ne produit ni message ni POST chat et finit également en pause ; la
reprise locale exige une action explicite. Une erreur STT,
capture ou chat reste `error` jusqu'à fermeture/réouverture du harnais. Un chat
déjà soumis garde sa finalisation canonique même si la vue est fermée ; D4
n'ajoute pas d'annulation de ce pipeline. Une reprise encore en initialisation
reste pausable : sa génération est revalidée avant armement et reprise D3.
L'armement initial n'accepte que `listening`, jamais `error` après changement
de thread. Orbe et onde restent au repos pendant `transcribing`, `thinking`
et `paused`.

Les preuves rouges, mutations, suites et résultats de livraison réels sont
consignés dans la [section D4 de la roadmap](fridadev-dialogue-oral-web-implementation-roadmap-todo.md#lot-d4--raccord-stt-au-pipeline-chat-canonique).
Aucun appel provider réel, TTS, lecture audio ou activation du bouton n'a été
exécuté dans D4. Le prolongement D5 distinct est décrit ci-dessous ; D6 reste
non commencé.

## Lecture TTS et boucle D5 — 9 septembre 2026

L'exception D5 explicitement approuvée prolonge seulement
`FridaDialogueD3Harness.openAndArm({ routeToChat: true })`. Aucun nouveau mode
de harnais concurrent : ce chemin enchaîne désormais D4 puis D5. Sans cette
option, D3 reste local ; sans adaptateurs de test, le harnais reste absent.
L'entrée ponctuelle D6.2a décrite ci-dessous réutilise cette chaîne complète.
Le bouton produit reste littéralement `disabled`. Le bootstrap normal ne crée
aucun lecteur et ne charge aucun asset lourd supplémentaire.

L'ouverture crée un unique `HTMLAudioElement`, possédé par la session et passé
explicitement au recorder D3 comme `ttsMediaElement`, sans recherche DOM.
`start()` appelle `play()` synchroniquement dans le geste initial sur un WAV
PCM silencieux fixe de huit échantillons depuis le correctif D6.1, embarqué
en data URI, sans réseau ni object URL. L'élément reste non muet. `whenReady()` doit confirmer le succès
de cette préparation et son nettoyage avant tout armement. Refus, annulation
ou erreur empêchent l'armement ; les événements de cette amorce ne sont jamais
des événements TTS métier. Le même élément sert tous les tours suivants.
Cette préparation a été validée matériellement en D6.1 sur Safari iPhone.
La lecture du MP3 fournisseur et le réarmement de la boucle restent à prouver
en D6.2 ; le smoke Chromium ne remplace pas cette preuve matérielle.

Après résolution complète du submit D4, seul le `text` du résultat
`{ ok: true, text }` est envoyé à `dialogueAudioClient.synthesize(text, { signal })`.
Aucun DOM, cache, placeholder ni fragment streaming n'est relu. Le texte reste
exact : pas de trim, normalisation, troncature ou réécriture ; la limite de
16 000 points de code est comptée par `Array.from(text).length`. Le client
refuse les types invalides, le vide et les blancs reconnus localement, sans
rejeter U+FEFF que D2 accepte. U+0085 et U+001C traversent inchangés : D2 reste
l'autorité finale pour les différences de définition du blanc. Le client fait
un seul POST JSON `{ text }` vers `/api/chat/dialogue/speech`, sans retry.
Un succès exige HTTP 200, média de base exactement `audio/mpeg`, Blob non vide
et d'au plus 16 Mio ; toute erreur reste content-free.

Après le final canonique, `tts_pending` affiche « AUDIO EN ATTENTE », onde et
orbe au repos, pendant la synthèse, l'attente de lecture et le buffering.
Seul `playing` de la lecture courante, avec source et propriétés cohérentes,
projette `tts_speaking` et active onde et orbe. La résolution de `play()`
ne suffit pas. `waiting` et `pause` média arrêtent les animations sans réarmer
ni terminer la session ; un nouveau `playing` valide les reprend. Le `pause`
naturel qui précède `ended` ne devient pas une erreur. La pause utilisateur
reste distincte et annule la lecture en cours.

Chaque lecture possède une object URL. Son nettoyage invalide d'abord ses
callbacks, arrête le lecteur, retire sa source, appelle `load()` pour annuler
les tâches média de l'ancienne ressource, puis révoque l'URL exactement une
fois. Session, génération, conversation, identité de lecture, source et état
du lecteur gardent les réponses TTS, événements et promesses `play()` tardifs.
Une fermeture/réouverture crée une nouvelle session sans réutiliser ses callbacks.

Seul `ended` confirmé de la lecture courante, après un `playing` observé,
autorise un réarmement automatique unique, après cleanup audio. Les gardes sont
revérifiées pendant la reprise D3 : Pause, sortie ou changement de conversation
neutralisent un armement en attente et ses pistes tardives. Le micro reste
désarmé pendant STT, chat, synthèse et lecture. Une promesse `play()` ancienne
ne bloque pas le cycle suivant. Un échec ou un final vide conduit à `error`,
sans réarmement automatique ; la réponse écrite déjà canonique demeure intacte.
Le STT vide conserve sa pause D4 avec reprise explicitement actionnée.

Annuler le fetch ne garantit pas l'arrêt d'un traitement D2 déjà reçu côté
serveur ; l'invalidation locale reste donc indépendante de cette annulation.
Aucun backend, modèle, voix, prompt, persistance, Whisper, VAD épinglé ou schéma
`input_mode` n'est modifié. Aucun provider réel ni canari n'est exercé en D5.
Les preuves et la livraison sont consignées dans la section D5 de la roadmap.

## Préflight local D6.1a — 10 septembre 2026

**Prérequis implémenté, testé, poussé et livré avec runtime vérifié. Le blocage
Safari iPhone a été reproduit, expliqué puis corrigé par un primer WAV silencieux
minimal décodable. D6.1 est fermé sans appel fournisseur ; D6.2 reste non
commencé.**

Le blocage de vérification précédent est requalifié : le harnais D3 n'existe
qu'avec les adaptateurs présents au bootstrap ; `routeToChat: false` exclut
volontairement D4/D5, donc son absence d'amorce n'est pas un bug produit.

`app.js` possède une seule fonction interne `openDialogueSession`, avec modes
fermés `d3_local`, `full`, `local_preflight`. Le harnais synthétique conserve
exactement son API et délègue `false` à `d3_local`, `true` à `full`.
Le contrôleur visuel reste inchangé ; `entryButtonEl: null` réserve le bouton
à l'unique listener applicatif.

L'autorité produit est un booléen immuable capturé depuis l'attribut HTML
`disabled` au bootstrap. Le bouton servi reste désactivé et ses attributs
accessibles sont conservés. Retirer ensuite `disabled` dans Inspector ne donne
aucune autorité produit : sans marqueur, aucun effet. Un marqueur malformé est
supprimé, le bouton redésactivé, et l'ouverture refusée.

Seul le marqueur exact `data-dialogue-preflight="local_preflight"` permet une
préparation locale depuis Safari Inspector. Lors du clic physique, le listener
supprime ce marqueur et redésactive le bouton avant toute attente. Il ouvre
`local_preflight` dans la même pile synchrone, crée l'unique HTMLAudioElement
et appelle l'amorce silencieuse D5 existante. Les événements synthétiques
n'autorisent pas cette ouverture. Aucune URL, variable globale supplémentaire,
route, cookie ou persistance ne sélectionne ce mode.

Après réussite de l'amorce seulement, les assets D3 same-origin sont chargés et
le recorder reçoit ce même lecteur avant d'acquérir son unique MediaStream.
Le VAD et la capture partagent le flux. L'acquisition micro intervient après
ce chargement ; la permission et le fonctionnement depuis ce seul geste
ont été validés matériellement sur Safari iPhone en D6.1, comme consigné ci-dessous.

Le mode local utilise le contrôleur de session existant, sans seconde machine.
Le wiring ne construit aucun client STT/TTS et ne transmet aucun callback chat.
Le constructeur rejette un mode local muni de ces capacités. Les événements
de parole projettent les états locaux ; un blob complet est ignoré avant
`consumeBlob`, sans requête, soumission, object URL, seconde lecture ni conservation
du contenu. Aucun transcript ou audio n'est affiché, persisté ou journalisé.
Seuls les assets D3 autorisés nécessitent un chargement réseau.

Pause arrête les pistes acquises ; seule Reprendre peut acquérir un autre flux.
Terminer, fermeture, `pagehide`, changement de conversation et erreur neutralisent
lecteur, capture et callbacks tardifs. `getUserMedia` en attente n'est pas
annulable : un flux reçu après invalidation est immédiatement arrêté avant VAD.
Aucune erreur ne réarme automatiquement.

Les preuves unitaires, Chromium, mutations et frontières D1/D2 hermétiques
figurent dans la section D6.1a de la roadmap. Elles ne constituent ni une preuve
matérielle iPhone ni une autorisation fournisseur. D6.4 devra retirer
explicitement le mécanisme de marqueur ; le retrait committé de `disabled`
donnera alors l'autorité au bootstrap et au même listener vers `full`.

### Verdict matériel Safari iPhone — 10 septembre 2026

Le premier essai content-free avait bien confirmé HTTPS, `isSecureContext`,
`getUserMedia`, le marqueur consommé une fois et le bouton redésactivé, mais il
restait bloqué avant D3. L'instrumentation directe de l'unique
`HTMLMediaElement.play()` a ensuite établi la cause : le primer WAV PCM local
d'un seul échantillon atteignait `loadedmetadata`, puis `error` avec
`MediaError.code=3` (`MEDIA_ERR_DECODE`) ; sa promesse restait en attente. Le
chargement D3, situé après `whenReady()`, ne pouvait donc pas commencer.

Une matrice locale sur le même Safari iPhone a montré qu'un échantillon échoue
et que huit échantillons atteignent `canplay`. La substitution transitoire de
la seule data URI par ce candidat de huit échantillons a fait résoudre
`play()`, charger les assets VAD same-origin, demander puis obtenir la permission
microphone et ouvrir l'écoute effective. Une phrase articulée a produit la
séquence `ÉCOUTE ACTIVE` → `JE T’ÉCOUTE` → `ÉCOUTE ACTIVE`. Terminer a arrêté
l'unique piste audio de `live` à `ended` et a ramené au chat. Aucune ressource
STT, chat ou TTS n'a été demandée.

Le correctif livré remplace exclusivement la data URI invalide par ce WAV
silencieux de huit échantillons, soit 16 octets PCM et 60 octets RIFF complets.
Après rechargement propre de la page, l'ancien monkeypatch était absent : un
nouveau clic physique sur l'image réellement déployée a de nouveau franchi
l'amorce et chargé D3 ; Tof a confirmé le cycle parole/silence puis Terminer.
Le panneau réseau n'a montré aucun transport STT, chat ou TTS. Le bouton produit
reste servi `disabled` et le mode local continue d'ignorer tout blob avant les
frontières réseau.

La preuve établit le préflight Safari iPhone et ferme D6.1. Elle n'autorise ni
appel fournisseur ni activation produit : D6.2 demeure le premier canari
borné et D6.4 devra toujours retirer explicitement le mécanisme de marqueur.

## Entrée ponctuelle D6.2a — 10 septembre 2026

Le diagnostic D6.2 est confirmé au HEAD initial
`b6803e65f0e702a1d73f67f920cf175062da2aef` : le HTML désactivé ne donne aucune
autorité produit ; le harnais complet est absent sans adaptateurs de test ;
le marqueur D6.1a ne permet que le préflight local.

L'exception D6.2a ajoute seulement la valeur exacte
`data-dialogue-preflight="full_canary"` au listener existant. Après préparation
éphémère dans Inspector et activation DOM locale du bouton, un clic trusted
consomme le marqueur, redésactive le bouton, puis appelle synchroniquement
`openDialogueSession('full')`. Les clients D4/D5 de production et la soumission
canonique sont ceux du chemin complet existant. Aucun adaptateur de bootstrap
n'est nécessaire à ce droit d'entrée, et aucun nouveau global n'est exposé.

Le marqueur est absent du HTML servi et de toute URL, configuration ou
persistance. Toute valeur autre que les deux valeurs exactes est consommée
puis refusée ; elle ne retombe jamais sur l'autorité produit. Sans marqueur,
le booléen immuable du bootstrap reste seul décisionnaire. `local_preflight`
conserve l'interdiction de transport et ignore les blobs. L'événement synthétique
reste inerte. D6.4 supprimera explicitement **tout** le mécanisme de marqueur.

Une préparation autorise une seule ouverture : un nouveau clic après consommation,
même après réactivation DOM seule, n'ouvre rien avec le HTML actuellement servi.
Cette propriété ne limite pas la session complète à un tour : la boucle et le
réarmement D5 restent inchangés. Le budget 1 STT / 1 chat / 1 TTS appartient
au protocole séparé D6.2, à établir avant son `GO canari` explicite.

Les preuves Chromium utilisent un vrai clic trusted, l'amorce native, les vrais
assets D3 et un flux synthétique sans microphone physique. Le WAV traverse les
vrais clients vers trois requêtes HTTP interceptées ; une réponse TTS 503
contrôlée termine ce témoin sans simuler une lecture réussie. Aucun audio,
transcript ou réponse opérateur n'est collecté. Les mutations et résultats
de livraison sont consignés dans la section D6.2a de la roadmap.

**D6.2a est un prérequis technique ; D6.2 reste ouvert, sans appel fournisseur,
avec `GO canari` distinct requis. D6.3 à D6.5 et Z restent non commencés.**

## Méthode obligatoire de choix du transport et des modèles

Avant tout choix de modèle ou début d'implémentation, le lot devra lire
intégralement la documentation officielle OpenRouter actuelle pertinente pour
ce mode. Cette lecture est une précondition d'architecture, pas une simple
référence ponctuelle. Elle partira de l'[index documentaire
officiel](https://openrouter.ai/docs/llms.txt) et couvrira au minimum :

- les contrats [Speech-to-Text](https://openrouter.ai/docs/guides/overview/multimodal/stt),
  [Text-to-Speech](https://openrouter.ai/docs/guides/overview/multimodal/tts)
  et [Audio](https://openrouter.ai/docs/guides/overview/multimodal/audio) ;
- la découverte des modèles et endpoints réellement disponibles, leurs
  formats, limites, réponses, erreurs et options propres aux providers ;
- le [routage des
  providers](https://openrouter.ai/docs/guides/routing/provider-selection),
  les fallbacks et les recommandations de [latence et
  performance](https://openrouter.ai/docs/guides/best-practices/latency-and-performance) ;
- les prix actuels ainsi que les règles de [collecte des
  données](https://openrouter.ai/docs/guides/privacy/data-collection), de
  [journalisation des
  providers](https://openrouter.ai/docs/guides/privacy/provider-logging) et de
  rétention applicables à l'audio et au texte.

Il est interdit de déduire le contrat audio par analogie avec le Chat
Completions déjà utilisé par Frida. Les endpoints, formats de réponse,
possibilités de streaming et règles de routage doivent être vérifiés dans la
documentation courante du modèle et de son endpoint avant d'écrire le design.

La sélection initiale ne doit pas déclencher par défaut une nouvelle campagne
de benchmarks Frida. Elle commence par les benchmarks publiés, comparaisons
indépendantes, model cards et mesures exposées par OpenRouter ou les providers,
après vérification de leur date, de leur protocole et de leur comparabilité avec
l'usage visé.

Pour le STT, la présélection doit notamment examiner le français conversationnel,
le bruit automobile, les hésitations et reprises, la fidélité des noms propres,
la latence et le coût. Pour le TTS, elle doit examiner l'intelligibilité et le
naturel en français, la stabilité de la voix, le délai jusqu'au premier son,
les formats et modes de diffusion réellement disponibles, ainsi que le coût.

Ces preuves existantes servent à former rapidement une courte liste ; elles ne
prouvent pas l'intégration de Frida. La validation propre au projet doit donc se
limiter ensuite à un essai d'acceptation borné, de bout en bout, avec le
téléphone dans la voiture. Cet essai vérifie la compatibilité réelle, la
latence ressentie et l'acceptabilité de la transcription et de la voix ; il ne
constitue pas un nouveau benchmark général des modèles.

Aucun modèle STT, modèle TTS, provider, voix ou politique de fallback n'est
figé au-delà de la décision V1 datée ci-dessous. Le catalogue, les prix, les
capacités et les contrats de transport devront être revérifiés au moment du lot
d'implémentation, sans recommencer la sélection si cette vérification ne révèle
aucune contradiction.

## Reconnaissance technique validée — 9 septembre 2026

Cette section est la preuve de décision à consommer par les prochains lots.
Elle évite de recommencer des comparaisons ou des essais déjà tranchés.

### 1. Lecture TTS répétée dans Safari

- Appareil : iPhone 11, Safari réel, hors session WebDriver.
- Modèle : `microsoft/mai-voice-2-flash` via OpenRouter.
- Voix : `fr-FR-Soleil:MAI-Voice-2`.
- Une activation utilisateur initiale a permis deux lectures TTS successives.
- Tof a entendu les deux lectures et a validé explicitement la voix Soleil.

Conclusion V1 : modèle et voix retenus. Ne pas relancer de sélection de voix
sans régression réelle ou changement du contrat OpenRouter.

### 2. Détection locale de parole sur l'iPhone

- La preuve a utilisé le VAD navigateur Silero fourni par
  `@ricky0123/vad-web`, dans Safari réel sur l'iPhone.
- La parole de Tof a produit la transition attendue
  `userSpeaking=false → true → false`.
- Tapotements, grattements, bruits non articulés et raclement de gorge sont
  restés à `false` ; la parole « bonjour messieurs dames » est immédiatement
  passée à `true`.
- Une voix de radio n'est pas un contre-cas pertinent pour un VAD : la V1 doit
  neutraliser toute radio, tout média et le propre TTS de Frida avant d'armer
  l'écoute. Le système n'a pas à identifier le locuteur au milieu d'une radio
  parlée.

Conclusion V1 : le principe du VAD local est validé. La résistance au bruit de
roulement reste à vérifier dans la voiture réelle ; elle ne justifie pas de
recommencer les essais de bruit non vocal déjà réussis.

### 3. Canari STT `MAI-Transcribe 2`

Le modèle retenu est
[`microsoft/mai-transcribe-2`](https://openrouter.ai/microsoft/mai-transcribe-2),
appelé par l'endpoint dédié `/api/v1/audio/transcriptions`, avec langue `fr` et
température `0`.

Preuves obtenues avec le microphone réel de l'iPhone exposé au Mac par
Continuité :

- un préflight synthétique exact sur « Bonjour Frida. » ;
- cinq prises de parole réelles : cinq réponses HTTP 200 ;
- latence de requête des cinq prises : de `0,713 s` à `1,097 s`, médiane
  `0,986 s` ;
- hésitations et reprises conservées ;
- `Habermas`, `John Rawls` et `Stimmung` correctement transcrits dans la parole
  spontanée ;
- un témoin de `4,40 s` ne contenant que tapotements et grattements a produit
  un transcript strictement vide en `0,972 s` ;
- coût total du préflight, des cinq prises et du témoin négatif :
  `0,001472222 USD` au tarif observé le jour du test.

Aucun taux d'erreur mot à mot n'est revendiqué : plusieurs phrases ont été
improvisées plutôt que lues, donc leur texte prévu ne constitue pas une vérité
terrain. Les enregistrements, transcriptions et scripts temporaires ont été
supprimés après calcul des métriques ; aucun audio ni transcript brut n'est
conservé dans le dépôt.

Conclusion V1 : `microsoft/mai-transcribe-2` est le STT principal retenu. Ne
pas lancer un nouveau benchmark général ni ajouter un fallback automatique.
Le seul essai restant est un canari borné avec parole réelle et bruit de
roulement dans la voiture.

### 4. Revalidation fournisseur pour D1 — 9 septembre 2026

La documentation OpenRouter courante maintient le contrat utilisé par D1 :

- `POST /api/v1/audio/transcriptions` est l'endpoint STT dédié, distinct de
  Chat Completions ; il accepte JSON base64 ou multipart OpenAI-compatible ;
  D1 utilise uniquement le multipart sortant avec `file`, `model`,
  `language=fr`, `temperature=0` et `response_format=json` ;
- le modèle `microsoft/mai-transcribe-2` reste disponible avec une seule route
  publiée, Azure, et annonce la température parmi ses paramètres supportés ;
  les paramètres STT normalisés `language`, `temperature` et
  `response_format` restent documentés au niveau de l'endpoint ;
- la réponse `json` exige un unique champ final `text` de type chaîne et peut
  aussi contenir `usage` ; `text=""` reste donc un succès fournisseur valide ;
- les formats communs documentés et admis localement sont WAV, MP3, FLAC, M4A,
  OGG, WebM et AAC, avec vérification conjointe du MIME et de l'extension ;
- le plafond multipart est désormais formulé `25 MB`, et non `25 MiB`. D1
  applique avant transport une borne fichier plus stricte de `24 000 000`
  octets et une borne de corps multipart de `25 000 000` octets ; la lecture
  applicative du fichier s'arrête à la borne plus un octet ;
- OpenRouter indique un timeout provider après `60 s` de traitement. Le client
  D1 est borné à `65 s`, sans retry, fallback, découpage ni streaming ;
- les préférences de routage `order`, `only` et `ignore` ne s'appliquent pas
  aux requêtes de transcription ; D1 n'ajoute donc aucune sélection provider
  cachée ;
- le prix publié reste `0,10 USD` par heure. Le stockage OpenRouter du contenu
  des entrées/sorties est désactivé par défaut sauf opt-in, tandis que les
  métadonnées de requête sont conservées. Les réglages de compte restent une
  responsabilité opérateur distincte du code.

Cette revalidation est documentaire et s'appuie aussi sur les métadonnées
publiques du modèle et de son endpoint. Aucun appel STT réel, canari ou
benchmark fournisseur n'a été exécuté dans D1.

### 5. Revalidation fournisseur et frontière inactive D2 — 9 septembre 2026

La documentation et les métadonnées publiques OpenRouter courantes maintiennent
le contrat requis par D2 :

- `POST /api/v1/audio/speech` est l'endpoint TTS dédié. Son succès renvoie les
  octets audio bruts, distinctement de l'audio base64 de Chat Completions ; avec
  `response_format=mp3`, le média documenté est `audio/mpeg` ;
- le modèle `microsoft/mai-voice-2-flash` reste publié et sa liste de voix
  accepte exactement `fr-FR-Soleil:MAI-Voice-2` ;
- le corps fournisseur D2 contient seulement `model`, `input`, `voice` et
  `response_format`. Aucun champ de routage, style, vitesse, instruction ou
  fallback n'est ajouté ;
- le prix publié est `15 USD` par million de caractères. Aucun plafond d'entrée,
  de sortie ou timeout TTS exact exploitable n'est publié pour l'endpoint du
  modèle : `16 000` caractères et `16 Mio` d'audio sont donc des bornes locales
  FridaDev, jamais présentées comme des limites OpenRouter. Le `timeout=60`
  transmis à Requests est un délai local d'inactivité réseau, pas une deadline
  murale absolue ;
- le texte accepté n'est ni tronqué ni réécrit. La réponse est lue en streaming
  par blocs jusqu'à la borne locale plus un octet, avec fermeture garantie ; un
  `Content-Length` valide déjà supérieur à la borne est refusé avant lecture ;
- un succès local exige le statut `200`, un média de base exactement
  `audio/mpeg`, des octets non vides et cohérents avec un éventuel
  `Content-Length`, puis une taille au plus égale à `16 Mio` ;
- le stockage OpenRouter du contenu des entrées/sorties est désactivé par défaut
  sauf opt-in, tandis que les métadonnées de requête sont conservées. D2 ne
  revendique aucune propriété de rétention ou d'entraînement propre au provider
  sous-jacent sans preuve primaire spécifique conservée.

La route locale `POST /api/chat/dialogue/speech` accepte uniquement l'objet JSON
`{"text":"…"}`. Elle retourne le MP3 avec `Cache-Control: no-store`, ou une
erreur JSON content-free : `422` pour l'entrée locale invalide, `502` pour une
réponse `200` invalide ou un rejet `400/404/422` du contrat fixe, et `503` pour
timeout, transport, `401/403/429` ou `5xx`. Aucun corps fournisseur, texte ou
audio partiel n'est projeté. Pendant la lecture de `response.raw`, les classes
réelles `urllib3.exceptions.ReadTimeoutError`, `ProtocolError` et `SSLError`
sont classées respectivement comme timeout, transport et transport ; les autres
erreurs de données illisibles restent des réponses `502` fermées.

À la clôture D2, aucun JavaScript n'appelait cette frontière. D5 ajoute son
consommateur dans le seul harnais synthétique ; elle reste inactive dans le
produit normal, dont le bouton Dialogue demeure désactivé. Aucun appel TTS
OpenRouter réel n'a été exécuté pour D2 ou D5.

### Règle de non-répétition

Un lot ultérieur ne doit pas recommencer le choix du VAD, du STT, du TTS ou de
la voix à partir de zéro. Il relit cette preuve, vérifie seulement que les
endpoints, modèles, tarifs et règles de confidentialité OpenRouter n'ont pas
changé, puis poursuit l'implémentation. Une réouverture exige un fait nouveau :
échec dans la voiture, régression Safari, retrait d'un modèle, changement de
contrat fournisseur ou mesure contradictoire reproductible.

## Formule de synthèse

Une conversation textuelle Frida parfaitement ordinaire, dont l'entrée et la
sortie sont automatisées par la voix : détection locale de la parole, STT en
ligne, traitement Frida inchangé, lecture TTS, puis réarmement automatique.

## Frontière d'autorisation

Ce mode constitue une extension fonctionnelle. L'exception UI du 9 septembre
autorise seulement le squelette décrit ci-dessus. Les exceptions distinctes D1
et D2 autorisent uniquement les frontières backend STT et TTS OpenRouter
inactives et bornées. L'exception D3 autorise uniquement la capture locale
testable décrite ci-dessus, sans entrée produit. Elle ne vaut pas autorisation
d'activer le bouton ni de lire le TTS. L'exception D4 explicitement approuvée
le 9 septembre autorise seulement le raccord WAV → D1 → chat canonique décrit
ci-dessus, dans le harnais synthétique. L'exception D5 distincte approuvée le
9 septembre autorise uniquement la lecture et la boucle décrites ci-dessus,
toujours sans provider réel ni activation produit. L'exception D6.1a approuvée
le 10 septembre autorise uniquement le prérequis local décrit ci-dessus.
D6.1 est fermé après la preuve iPhone et le correctif minimal du primer WAV.
L'exception D6.2a du 10 septembre autorise seulement l'entrée ponctuelle
`full_canary`, ses tests hermétiques et sa livraison applicative. D6.2 reste
ouvert et son exécution fournisseur exige encore un `GO canari` distinct.
D6.3 à D6.5 et Z restent non commencés et exigent des décisions explicites.

## Roadmap d'implémentation

La mise en œuvre est découpée dans la
[roadmap du mode Dialogue oral Web](fridadev-dialogue-oral-web-implementation-roadmap-todo.md).
Elle garde le bouton produit désactivé jusqu'au canari iPhone en voiture et
interdit de recommencer les choix VAD, STT, TTS ou voix sans fait nouveau.
