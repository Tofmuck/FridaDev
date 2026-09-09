# Design QA — chat Web FridaDev

Date : 2026-09-09

## Référence

- Figma : `FridaDev — Chat Web et dialogue oral`
- fichier : `OiGP7QIP4XiEKjm901DEvY`
- clair : `18:3`
- sombre : `27:34`
- viewport de comparaison : `1440 × 900`
- mobile : `Alternative B — Dialogue vivant`, wrapper `71:2`, conversation
  `71:9`
- viewport mobile de comparaison : `414 × 896`

## Vérification visuelle

- géométrie identique entre clair et sombre : sidebar `272 px`, topbar
  `46 px`, main `1168 px`, compositeur `1080 × 134 px` à `316 × 744` ;
- fonds conformes et unis : `#fbf8f3` et `#0d1117`, sans image ni gradient ;
- ordre de la topbar, bulles, largeurs de conversation, compositeur à deux
  niveaux, bouton d'envoi et icône de thème conformes aux frames ;
- logo officiel transparent et miniatures Frida conservés, halos circulaires
  non rognés ;
- comparaison côte à côte effectuée avec la capture Figma et le rendu de test
  au même viewport dans les deux thèmes.

Une nouvelle comparaison ciblée sur la sidebar a vérifié les frames `18:4` et
`27:35` face aux rendus Safari réels à `1440 × 900`. Elle confirme la largeur
`272/244 px`, la ligne de répertoire `34 px`, l'égalité géométrique des deux
thèmes et l'ordre conversation → fichiers → panneaux. Les badges de compte et
de synchronisation qui écrasaient le nom visible ont été retirés de la ligne ;
les mêmes informations restent dans son nom accessible et son infobulle.

L'iconographie visible a été recroisée avec la maquette : chevrons pour le
déplacement, crayon pour le renommage, trombone pour l'ajout de fichier, note
et corbeille pour les autres actions. L'icône choisie pour chaque répertoire
reste distincte, avec un dossier rempli plus lisible dans les deux thèmes. Le
bouton d'export de la topbar reprend l'icône de sortie de la frame.

La passe navigateur complète a aussi exposé une hauteur de compositeur devenue
périmée après redimensionnement étroit. La hauteur est désormais resynchronisée
sur le rectangle réel ; le panneau de génération d'image reste au-dessus du
compositeur dans les preuves bureau et mobile existantes.

## Invariants produit contrôlés

La structure DOM reste unique. Les contrôles de conversation, répertoire,
fichier, note, export, image, OCR et outils du compositeur restent présents et
opérants. Les actions compactes d'un répertoire replié restent masquées jusqu'à
son ouverture afin de préserver sa cible de clic. Les commandes emploient les
assets Lucide locaux avec titres et libellés ARIA ; création, déplacement,
renommage, suppression, ajout de fichier, note, export, image, OCR et édition
restent reliés à leurs callbacks existants.

## Écarts intentionnels

Les contenus de conversation, noms et dossiers sont dynamiques : le test ne
copie pas les données fictives de la maquette. Lorsqu'un répertoire réel porte
des panneaux Notes, Exports ou Images, ils restent visibles afin de ne perdre
aucune commande produit ; la maquette n'en contient pas dans son exemple. Le
champ de recherche en bas de sidebar n'est pas reproduit, car il n'existe pas
dans le produit courant et ce lot n'autorise ni contrôle inerte ni nouveau
workflow. L'ombre extérieure du cadre Figma appartient au canevas de
présentation, pas à la page Web.

## Vérification mobile B

La composition rendue à `414 × 896` a été comparée à `71:2` : topbar sombre de
`62 px`, logo transparent sur halo cyan, présence, export, bulles arrondies,
fond nuit lumineux et compositeur `390 × 146 px` concordent avec la direction
`Dialogue vivant`. Le test ne reproduit ni la barre d'état ni l'indicateur
d'accueil dessinés dans la planche, car Safari/iOS en garde l'autorité.

Le compositeur conserve une entrée de `62 px`, un micro de `52 px`, un envoi
de `56 px`, le niveau de raisonnement, Web, document actif et image visibles.
Le bouton Dialogue reste honnêtement désactivé jusqu'au chantier oral. Le
bouton `…` rend Adobe, Biblio, Notes et Agenda accessibles dans une palette
secondaire au lieu de les supprimer.

L'état navigation a été contrôlé avec le tiroir ouvert à `354 px` : bouton de
fermeture, Nouveau chat, création de dossier, hiérarchie, conversation,
fichiers, OCR, note et six commandes du dossier restent reliés au DOM actuel.
Dans le dossier ouvert, ces six commandes disposent chacune d'une cible tactile
de `44 × 44 px`, comme dans l'état B de la maquette ; les lignes de conversation,
fichier et note conservent elles aussi une hauteur tactile minimale de `44 px`.
Le thème desktop stocké est restitué lorsque le viewport repasse au format
large.

final result: passed
