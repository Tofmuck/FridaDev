# Contrat visuel du chat Web — bureau clair/sombre et iPhone

Date d'autorité : 2026-09-11
Statut : stabilité portrait/paysage et premier retour Authelia validés sur iPhone

Autorité Figma : fichier `FridaDev — Chat Web et dialogue oral`
(`OiGP7QIP4XiEKjm901DEvY`), vues complètes `18:3` pour le mode clair et
`27:34` pour le mode sombre, réunies dans `29:30`, puis composition mobile
`Alternative B — Dialogue vivant` dans `71:2` (`71:9` pour l'écran de
conversation) et écran dialogue `Mobile sombre — Mode dialogue — Écoute` dans
`106:4`.

## Portée

Sur bureau, le chat Web possède une structure unique et deux présentations
visuelles : `light` et `dark`. Le bouton de la barre supérieure bascule entre
elles et le choix est conservé localement sous `frida.chat.theme`. Aucun
réglage serveur, cookie métier, route ou schéma n'est ajouté.

Les deux thèmes partagent la même structure fonctionnelle et font varier les
tokens et effets CSS. Ils conservent exactement la même géométrie du
compositeur, le même DOM fonctionnel et les mêmes contrôles. Le mode sombre ne
constitue pas une seconde interface. À `1440 × 900`, la sidebar mesure
`272 px`, la barre supérieure `46 px`, la zone principale `1168 px` et le
compositeur `1080 × 134 px`, placé à `316 × 744`.

La hauteur effective du compositeur alimente sa variable de layout à chaque
redimensionnement. Les panneaux d'outil restent ainsi au-dessus de lui quand
le viewport existant passe du bureau au format étroit.

Sur un téléphone tactile dont le petit côté d'écran ne dépasse pas `640 px`, le
même DOM fonctionnel adopte la composition sombre dédiée `Dialogue vivant`, en
portrait comme en paysage. `navigator.standalone` et `display-mode: standalone`
complètent cette reconnaissance sans sniffing de chaîne User-Agent ; le
breakpoint `max-width: 640px` subsiste seulement comme fallback responsive pour
une fenêtre étroite. Un terminal tactile plus grand ne devient donc pas un
téléphone par sa seule capacité tactile.

À `414 × 896`, la barre supérieure mesure `414 × 62 px` hors safe area iOS et
le compositeur mesure `390 × 146 px`, à `12 px` des bords. En paysage
`896 × 414`, la même présentation téléphone et le même écran Dialogue restent
actifs ; seules leurs dimensions internes s'adaptent. Le thème de présentation
téléphone ne réécrit pas le choix desktop conservé. Une fenêtre de bureau
réduite qui utilisait le fallback responsive restitue `light` ou `dark` en
retrouvant une largeur normale.

Le mode installé Safari respecte `viewport-fit=cover`, les safe areas et
`100dvh`. L'autorité téléphone est resynchronisée au chargement, lors des
changements de présentation et sur `pageshow`. Cette mécanique conserve la
présentation en rotation. Une première recette matérielle du 11 septembre 2026
avait affiché la composition de bureau au premier retour Authelia, sans cause
établie. La recette contrôlée de clôture a ensuite invalidé uniquement la
session Authelia dans l'application installée, sans effacer cache ni stockage,
puis a obtenu directement la composition téléphone au premier retour. Web
Inspector a confirmé `navigator.standalone=true`, le mode d'affichage
`standalone`, un écran `414 × 896`, un viewport `414 × 848` et les attributs
`phone` / `mobile-dialogue`. Le témoin synthétique `pageshow` complète cette
preuve réelle mais ne la remplace pas. Le document ne dessine ni barre d'état iOS ni indicateur d'accueil :
ces éléments appartiennent au système. Le manifeste et le chrome mobile
utilisent le fond `#060913` afin d'éviter un flash clair au démarrage. Le fil
conversationnel est strictement vertical : son contenu ne dépasse pas la
largeur du viewport et les gestes horizontaux ne déplacent pas le rail de
lecture. Le zoom par pincement reste autorisé.

## Invariants fonctionnels

Dans les deux thèmes restent présents et opérants :

- nouveau chat, sélection, renommage et déplacement des conversations ;
- création, renommage, déplacement, repli et icône des répertoires ;
- ajout, sélection, OCR et édition des fichiers ;
- création et sélection des notes, Exports et Images ;
- dictée, Web, document actif, génération d'image, Adobe, Biblio, Notes,
  Agenda, niveau de raisonnement et envoi ;
- heure et copie de chaque bulle, ainsi que l'export de conversation.

Sur iPhone, le menu ouvre la sidebar existante dans un tiroir de `354 px`
maximum. Nouveau chat, création de répertoire, icône, déplacement, renommage,
ajout de fichier, note, OCR, sélection et conversations continuent donc
d'utiliser leurs callbacks existants. Dans un répertoire ouvert, les six
commandes possèdent chacune une cible tactile de `44 × 44 px` à `414 px` de
large. Le bouton `…` du compositeur déploie Adobe, Biblio, Notes et Agenda ; il
ne remplace ni ne désactive ces outils.

Le changement de thème ne déclenche aucune requête applicative et ne réordonne
aucun état. La même règle vaut après rechargement de la page.

La sidebar conserve une seule structure dans les deux thèmes. À `1440 × 900`,
son contenu utile mesure `244 px` dans les `272 px` du panneau. Les libellés de
section sont `DOSSIERS` et `CONVERSATIONS`. Chaque répertoire occupe une ligne
de `34 px` au repos ; son ouverture révèle, dans cet ordre, ses conversations,
ses fichiers puis ses panneaux Notes, Exports et Images. Les commandes du
répertoire suivent l'ordre Figma : monter, descendre, renommer, ajouter un
fichier, créer une note, supprimer. Les icônes de répertoire choisies par
l'utilisateur restent distinctes de ces commandes. Les chevrons, le crayon,
le trombone, la note et la corbeille sont les icônes visibles de ces
commandes. Le nombre de conversations et l'état Nextcloud restent disponibles
dans le nom accessible et l'infobulle du répertoire ; ils ne compriment pas
son nom dans la ligne visuelle.

## Identité visuelle

Le PNG transparent officiel `fridalogo.png` reste l'unique image d'identité.
Le logo de la sidebar et les miniatures précédant les réponses de Frida sont
posés sur un halo radial CSS. Le halo et l'ombre portée sont extérieurs à
l'image, circulaires et non rognés par un conteneur rectangulaire.

Le compositeur est une surface flottante arrondie et translucide. Les bulles,
la sidebar et la barre supérieure utilisent les mêmes rayons, transparences et
hiérarchie dans les deux thèmes ; seules les couleurs changent. Le titre de la
conversation et l'état de présence occupent la partie gauche de la barre ; la
navigation, l'export et le bouton de thème occupent sa partie droite dans cet
ordre.

Sur bureau, les fonds du viewport sont des aplats, sans image ni halo décoratif
global : `#fbf8f3` en clair et `#0d1117` en sombre. Le seul halo visuel
volontaire est celui de l'identité Frida. L'icône de thème provient de l'asset
Figma exporté, et non d'un glyphe ou d'un dessin CSS approché.

Les commandes compactes de la sidebar utilisent les SVG de la bibliothèque
Lucide distribués avec leur licence ISC. Aucun caractère typographique ou
emoji ne sert d'icône. Les titres et libellés ARIA conservent le nom complet de
chaque action ; l'iconographie ne retire donc ni fonction ni accessibilité.

La composition mobile suit la direction B : fond bleu nuit en dégradé, halos
cyan/indigo, bulles assistant et utilisateur de même famille lumineuse,
topbar compacte avec identité Frida et compositeur flottant à deux niveaux.
Le bouton `Dialogue` est actif. Son nom accessible, « Démarrer le mode
Dialogue », décrit son action ; un clic utilisateur ouvre l'unique chaîne
semi-duplex livrée.

L'écran dialogue est intégré comme couche mobile. Il reprend la topbar, l'orbe
Frida, le signal vocal, le statut et les deux commandes de la maquette Figma.
Il utilise la capture VAD/WAV, le STT, le chat canonique et le TTS livrés par
D1 à D5. Aucun transcript n'apparaît dans cette vue. L'onde ne s'anime que sur
une parole déclarée active ; l'orbe ne s'anime que sur l'état distinct
`tts_speaking`.

## Limites

Le champ de recherche de
conversations visible dans la maquette reste absent : FridaDev ne possédait pas
ce workflow et ce lot visuel n'ajoute pas de contrôle inerte ni de capacité
produit. Les contours et ombres externes du cadre Figma appartiennent à sa
présentation sur le canevas, pas au viewport Web.

La composition mobile et le dialogue oral semi-duplex sont livrés. Leur
appréciation en usage réel demeure ouverte dans D6.5.

## Preuves minimales

```bash
node --test app/tests/unit/frontend_chat/test_chat_theme_module.js
node --test app/tests/unit/frontend_chat/test_dialogue_mode_module.js
node --test --test-name-pattern="chat theme switch preserves" \
  app/tests/integration/frontend_browser/test_frontend_browser_smoke.js
node --test --test-name-pattern="workspace folders start collapsed" \
  app/tests/integration/frontend_browser/test_frontend_browser_workspace_folders.js
node --test --test-name-pattern="iPhone chat uses Figma Dialogue vivant|iPhone navigation keeps the Figma B drawer" \
  app/tests/integration/frontend_browser/test_frontend_browser_smoke.js \
  app/tests/integration/frontend_browser/test_frontend_browser_workspace_folders.js
node --test --test-name-pattern="iPhone dialogue preview keeps the Figma layout" \
  app/tests/integration/frontend_browser/test_frontend_browser_smoke.js
node --test --test-name-pattern="iPhone keeps the phone presentation" \
  app/tests/integration/frontend_browser/test_frontend_browser_smoke.js
```

La preuve navigateur doit comparer les rectangles du formulaire, du textarea
et de la grille d'outils avant et après bascule, vérifier les dimensions et les
couleurs Figma à `1440 × 900`, la persistance après rechargement et la présence
des contrôles existants. La preuve Workspace verrouille séparément les
dimensions clair/sombre, les icônes et leur ordre, ainsi que les actions de
répertoire, conversation, fichier, note, export, image, sélection, OCR et
déplacement de conversation.

La preuve iPhone impose en plus : présentation mobile sombre sans écraser le
thème desktop stocké, géométrie `414 × 62` et `390 × 146`, logo officiel,
composer principal `textarea + micro + envoi`, rail bas, bouton Dialogue
actif, ouverture/fermeture des outils secondaires, tiroir de navigation et
présence effective des actions de répertoire. Elle vérifie aussi l'égalité des
largeurs `scrollWidth/clientWidth` du document, de la zone principale et du fil,
ainsi que son verrouillage tactile sur l'axe vertical.

La preuve de contexte téléphone impose aussi la conservation de cette
présentation après passage de `414 × 896` à `896 × 414`, sans fermeture de
l'écran Dialogue, puis sa restauration sur un événement `pageshow`. Le même
test vérifie que le menu reste visible et que le bouton Dialogue reste actif.
Le témoin unitaire sépare le téléphone d'un grand écran tactile et
conserve le fallback responsive étroit.

La preuve de l'écran dialogue impose en plus les dimensions `414 × 896`, la
topbar hors safe area à `82 px`, l'orbe `344 × 344`, le panneau inférieur
`390 × 84`, le chargement des SVG Figma, l'absence de champ de transcription,
l'inertie du chat masqué et les déclenchements d'animation distincts pour Tof
et Frida.
