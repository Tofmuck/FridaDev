# Contrat visuel du chat Web — bureau clair/sombre et iPhone

Date d'autorité : 2026-09-09
Statut : livré dans le frontend Web courant

Autorité Figma : fichier `FridaDev — Chat Web et dialogue oral`
(`OiGP7QIP4XiEKjm901DEvY`), vues complètes `18:3` pour le mode clair et
`27:34` pour le mode sombre, réunies dans `29:30`, puis composition mobile
`Alternative B — Dialogue vivant` dans `71:2` (`71:9` pour l'écran de
conversation).

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

À `640 px` de large ou moins, le même DOM fonctionnel adopte la composition
sombre dédiée `Dialogue vivant`. À `414 × 896`, la barre supérieure mesure
`414 × 62 px` hors safe area iOS et le compositeur mesure `390 × 146 px`, à
`12 px` des bords. Le thème de présentation mobile ne réécrit pas le choix
desktop conservé : revenir à un viewport large restitue `light` ou `dark` tel
qu'il était enregistré.

Le mode installé Safari respecte `viewport-fit=cover`, les safe areas et
`100dvh`. Le document ne dessine ni barre d'état iOS ni indicateur d'accueil :
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
Le bouton `Dialogue` est présent pour rendre lisible la direction de design,
mais il est désactivé et son nom accessible annonce explicitement que le mode
dialogique n'est pas encore disponible. Il ne déclenche aucun appel, aucun
état et aucune mutation.

## Limites

Le champ de recherche de
conversations visible dans la maquette reste absent : FridaDev ne possédait pas
ce workflow et ce lot visuel n'ajoute pas de contrôle inerte ni de capacité
produit. Les contours et ombres externes du cadre Figma appartiennent à sa
présentation sur le canevas, pas au viewport Web.

La composition mobile dédiée est livrée, mais pas le dialogue oral semi-duplex,
un nouveau STT ou un nouveau TTS. Le bouton `Dialogue` ne doit être activé que
par un lot produit ultérieur explicitement autorisé.

## Preuves minimales

```bash
node --test app/tests/unit/frontend_chat/test_chat_theme_module.js
node --test --test-name-pattern="chat theme switch preserves" \
  app/tests/integration/frontend_browser/test_frontend_browser_smoke.js
node --test --test-name-pattern="workspace folders start collapsed" \
  app/tests/integration/frontend_browser/test_frontend_browser_workspace_folders.js
node --test --test-name-pattern="iPhone chat uses Figma Dialogue vivant|iPhone navigation keeps the Figma B drawer" \
  app/tests/integration/frontend_browser/test_frontend_browser_smoke.js \
  app/tests/integration/frontend_browser/test_frontend_browser_workspace_folders.js
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
désactivé, ouverture/fermeture des outils secondaires, tiroir de navigation et
présence effective des actions de répertoire. Elle vérifie aussi l'égalité des
largeurs `scrollWidth/clientWidth` du document, de la zone principale et du fil,
ainsi que son verrouillage tactile sur l'axe vertical.
