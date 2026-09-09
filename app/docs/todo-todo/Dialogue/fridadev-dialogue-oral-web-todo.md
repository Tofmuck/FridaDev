# FridaDev — dialogue oral greffé sur le pipeline Web

Date de cadrage initial : 7 septembre 2026.
Dernière mise à jour de reconnaissance : 9 septembre 2026.

**Statut : contrat initial et reconnaissance technique iPhone consignés. Les
choix V1 du VAD, du STT et du TTS sont retenus ; seule leur invalidation par le
test automobile réel peut les rouvrir. Le squelette visuel Figma et son
contrôleur local d'états sont intégrés. Les frontières backend STT D1 et TTS D2
sont implémentées et livrées sans consommateur frontend. La capture locale D3
est corrigée, refermée et livrée avec pré-roll borné et assets optionnels ; l'entrée
produit reste désactivée et aucun raccord STT frontend, chat, TTS, provider ou
lecture audio n'est activé.**

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
- Le seuil `x` reste à éprouver par le canari automobile. D3 fixe la préférence
  de conteneur à `audio/mp4`, puis `audio/webm` et `audio/ogg` seulement si le
  navigateur les déclare réellement supportés, sans paramètre codec inventé.
  La V1 ne doit pas ajouter de fallback automatique qui changerait
  silencieusement de modèle.

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
MJS D3 et ne dépend d'aucun global VAD. Seul `openAndArm()` du harnais de test
charge, une fois et dans l'ordre, les scripts locaux, puis initialise le VAD.
Un asset absent/refusé met uniquement D3 en erreur ; le chat clavier demeure
utilisable. Pause ou fermeture pendant ce chargement ne déclenche aucun micro
tardif. Le bouton produit reste littéralement `disabled`.

L'adaptateur reste volontairement lié aux internals de la version épinglée ;
une montée de version doit revalider segmentation, pré-roll, ordre des callbacks,
bornes et cleanup. D3 projette seulement `listening → user_speaking → listening`,
pause et erreur. Il ne raccorde ni D1, ni D2, ni chat, ni Whisper, ni TTS.
D4 reste strictement non commencé.

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

Cette frontière reste inactive : aucun JavaScript ne l'appelle, le bouton
Dialogue demeure désactivé et aucun appel TTS OpenRouter réel n'a été exécuté
pour D2.

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
d'activer le bouton, de raccorder le STT frontend ou le chat, ni de lire le TTS.
D4 à D6 exigent chacun un lot explicitement autorisé.

## Roadmap d'implémentation

La mise en œuvre est découpée dans la
[roadmap du mode Dialogue oral Web](fridadev-dialogue-oral-web-implementation-roadmap-todo.md).
Elle garde le bouton produit désactivé jusqu'au canari iPhone en voiture et
interdit de recommencer les choix VAD, STT, TTS ou voix sans fait nouveau.
