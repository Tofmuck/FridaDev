# FridaDev — dialogue oral greffé sur le pipeline Web

Date de cadrage initial : 7 septembre 2026.

**Statut : contrat initial consigné pour ne pas perdre la décision. Aucune
implémentation n'est encore autorisée par ce document.**

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
- Aucun second pipeline dialogique n'est créé.
- Le STT local actuel est contourné pour ce mode, pas présenté comme amélioré.
- Le microphone n'écoute pas les reprises pendant la lecture de Frida dans la
  première version.
- L'interruption de Frida, le full-duplex et la reprise pendant le TTS sont des
  évolutions ultérieures distinctes.
- Le choix du modèle STT, du modèle et de la voix TTS, du seuil `x`, du format
  audio et des fallbacks reste ouvert jusqu'à des preuves réelles sur téléphone
  dans la voiture.

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
figé par ce contrat initial. Le catalogue, les prix, les capacités et les
benchmarks devront être revérifiés au moment du lot d'implémentation.

## Formule de synthèse

Une conversation textuelle Frida parfaitement ordinaire, dont l'entrée et la
sortie sont automatisées par la voix : détection locale de la parole, STT en
ligne, traitement Frida inchangé, lecture TTS, puis réarmement automatique.

## Frontière d'autorisation

Ce mode constitue une extension fonctionnelle. Sa consignation documentaire
ne vaut ni levée implicite de la doctrine de consolidation, ni autorisation de
modifier le code, le runtime, les providers ou la configuration. Son
implémentation exigera une décision explicite et un cadrage séparé.
