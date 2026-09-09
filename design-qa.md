# Design QA — chat Web FridaDev

Date : 2026-09-09

## Référence

- Figma : `FridaDev — Chat Web et dialogue oral`
- fichier : `OiGP7QIP4XiEKjm901DEvY`
- clair : `18:3`
- sombre : `27:34`
- viewport de comparaison : `1440 × 900`

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

Une seconde comparaison ciblée sur la sidebar a vérifié les frames `18:4` et
`27:35` face aux rendus applicatifs `1440 × 900`. Elle confirme la largeur
`272/244 px`, la ligne de répertoire `34 px`, les sections sans carte parasite,
l'ordre conversation → fichiers → panneaux et l'égalité géométrique des deux
thèmes.

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
copie pas les données fictives de la maquette. Le champ de recherche en bas de
sidebar n'est pas reproduit, car il n'existe pas dans le produit courant et ce
lot n'autorise ni contrôle inerte ni nouveau workflow. L'ombre extérieure du
cadre Figma appartient au canevas de présentation, pas à la page Web.

final result: passed
