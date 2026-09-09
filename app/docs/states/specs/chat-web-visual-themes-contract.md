# Contrat visuel du chat Web — clair et sombre

Date d'autorité : 2026-09-09
Statut : livré dans le frontend Web courant

Autorité Figma : fichier `FridaDev — Chat Web et dialogue oral`
(`OiGP7QIP4XiEKjm901DEvY`), vues complètes `18:3` pour le mode clair et
`27:34` pour le mode sombre, réunies dans `29:30`.

## Portée

Le chat Web possède une structure unique et deux présentations visuelles :
`light` et `dark`. Le bouton de la barre supérieure bascule entre elles et le
choix est conservé localement sous `frida.chat.theme`. Aucun réglage serveur,
cookie métier, route ou schéma n'est ajouté.

Les deux thèmes partagent la même structure fonctionnelle et font varier les
tokens et effets CSS. Ils conservent exactement la même géométrie du
compositeur, le même DOM fonctionnel et les mêmes contrôles. Le mode sombre ne
constitue pas une seconde interface. À `1440 × 900`, la sidebar mesure
`272 px`, la barre supérieure `46 px`, la zone principale `1168 px` et le
compositeur `1080 × 134 px`, placé à `316 × 744`.

La hauteur effective du compositeur alimente sa variable de layout à chaque
redimensionnement. Les panneaux d'outil restent ainsi au-dessus de lui quand
le viewport existant passe du bureau au format étroit.

## Invariants fonctionnels

Dans les deux thèmes restent présents et opérants :

- nouveau chat, sélection, renommage et déplacement des conversations ;
- création, renommage, déplacement, repli et icône des répertoires ;
- ajout, sélection, OCR et édition des fichiers ;
- création et sélection des notes, Exports et Images ;
- dictée, Web, document actif, génération d'image, Adobe, Biblio, Notes,
  Agenda, niveau de raisonnement et envoi ;
- heure et copie de chaque bulle, ainsi que l'export de conversation.

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

Les fonds du viewport sont des aplats, sans image ni halo décoratif global :
`#fbf8f3` en clair et `#0d1117` en sombre. Le seul halo visuel volontaire est
celui de l'identité Frida. L'icône de thème provient de l'asset Figma exporté,
et non d'un glyphe ou d'un dessin CSS approché.

Les commandes compactes de la sidebar utilisent les SVG de la bibliothèque
Lucide distribués avec leur licence ISC. Aucun caractère typographique ou
emoji ne sert d'icône. Les titres et libellés ARIA conservent le nom complet de
chaque action ; l'iconographie ne retire donc ni fonction ni accessibilité.

## Limites

Ce contrat couvre le chat Web responsive existant. Le champ de recherche de
conversations visible dans la maquette reste absent : FridaDev ne possédait pas
ce workflow et ce lot visuel n'ajoute pas de contrôle inerte ni de capacité
produit. Les contours et ombres externes du cadre Figma appartiennent à sa
présentation sur le canevas, pas au viewport Web.

Le contrat ne prétend pas livrer une composition mobile dédiée, le dialogue
oral semi-duplex, un nouveau STT ou un nouveau TTS.

## Preuves minimales

```bash
node --test app/tests/unit/frontend_chat/test_chat_theme_module.js
node --test --test-name-pattern="chat theme switch preserves" \
  app/tests/integration/frontend_browser/test_frontend_browser_smoke.js
node --test --test-name-pattern="workspace folders start collapsed" \
  app/tests/integration/frontend_browser/test_frontend_browser_workspace_folders.js
```

La preuve navigateur doit comparer les rectangles du formulaire, du textarea
et de la grille d'outils avant et après bascule, vérifier les dimensions et les
couleurs Figma à `1440 × 900`, la persistance après rechargement et la présence
des contrôles existants. La preuve Workspace verrouille séparément les
dimensions clair/sombre, les icônes et leur ordre, ainsi que les actions de
répertoire, conversation, fichier, note, export, image, sélection, OCR et
déplacement de conversation.
