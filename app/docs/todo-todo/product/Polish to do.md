# FridaDev - Polish UI chat - TODO

Classement: `app/docs/todo-todo/product/`
Statut: actif, mini-lots bornes; Lots 1-3 livres le 2026-05-23
Date de creation: 2026-05-23

## Intention

Ce TODO regroupe les petits polishs du chat FridaDev. Il ne porte pas un redesign, un changement de theme global ni une refonte des workflows.

Regle de conduite: avancer point par point, cocher seulement ce qui est livre, garder les patches petits, tester le rendu desktop/mobile quand une surface visible change.

## Hors-scope

- Pas de refonte couleurs globale.
- Pas de theming multi-palette.
- Pas de modification backend sans bug prouve.
- Pas de changement du protocole streaming.
- Pas de changement web search, Adobe, Whisper backend, Memory, Identity ou Summary.

## Points de polish identifies

### 1. Animations d'attente unifiees

- [x] Reutiliser les trois points ondulants pour l'etat `Generation en cours` du panneau image.
- [x] Conserver `prefers-reduced-motion: reduce`.
- [x] Ne pas changer le backend de generation d'image.

### 2. Etats actifs des boutons du composer

- [x] Rendre les etats actifs un peu plus lisibles sans redesign.
- [x] Garder le bouton envoyer prioritaire.
- [x] Ne pas changer les comportements Web / Adobe / document / image / Whisper.

### 3. Controle reasoning plus discret

- [x] Auditer le rendu actuel du controle `Raisonnement`.
- [x] Proposer un micro-ajustement sans cacher le reglage global.
- [x] Tester desktop/mobile.

### 4. Ligne contexte au-dessus du champ

- [x] Auditer l'empilement `documents actifs` / `Adobe` / `reasoning`.
- [x] Proposer une ligne contexte unique si le besoin est confirme.
- [x] Ne pas rouvrir les contrats fonctionnels.

### 5. Panneau generation image

- [ ] Polir l'etat vide et l'etat resultat.
- [ ] Verifier le rendu mobile apres generation.
- [ ] Garder le panneau utilitaire, pas marketing.

### 6. Messages, byline et copie

- [ ] Auditer le bouton copie et son feedback.
- [ ] Verifier hover/focus clavier.
- [ ] Ne pas changer le rendu texte brut des messages.

## Lot 1 - Attentes image + etats actifs composer

Statut: livre le 2026-05-23.

### PATCH

- [x] `chat_image_generation.js`: expose `data-image-generation-state="generating"` pendant la generation.
- [x] `styles.css`: applique les trois points ondulants existants a l'etat image en cours.
- [x] `styles.css`: renforce legerement les boutons actifs du composer avec `surface-active` et un inset subtil.

### TESTS

- [x] Tests frontend navigateur couvrant l'etat `Generation en cours`.
- [x] Tests frontend unitaires existants.
- [x] Tests integration frontend chat existants.
- [x] Verification live apres rebuild.

### RISQUES

- [x] Animation trop presente: reduite au meme langage visuel que Whisper/assistant.
- [x] Etats actifs trop forts: ajustement volontairement leger.


## Lot 2 - Controle reasoning plus discret

Statut: livre le 2026-05-23.

### PATCH

- [x] `index.html`: label visible raccourci en `Rais.` avec titre complet et `aria-label` complet sur le select.
- [x] `styles.css`: controle rendu plus compact, moins saillant, sans masquer le reglage global.
- [x] `styles.css`: contraintes mobiles explicites pour eviter l'etalement horizontal.

### TESTS

- [x] Test navigateur desktop/mobile du controle compact.
- [x] Tests frontend unitaires existants.
- [x] Tests integration frontend chat existants.

### RISQUES

- [x] Reglage trop cache: conserve un libelle visible, un titre complet et l'aria-label complet.
- [x] Regression fonctionnelle: aucun changement de payload, endpoint, valeurs ou persistance.


## Lot 3 - Ligne contexte au-dessus du champ

Statut: livre le 2026-05-23.

### PATCH

- [x] `index.html`: regroupe documents actifs, reasoning et choix Adobe dans `composerContextRow`.
- [x] `styles.css`: ligne contexte flex, avec documents a gauche et controles contexte a droite.
- [x] `styles.css`: repli mobile explicite, documents au-dessus et controles contexte dessous quand l'espace manque.

### TESTS

- [x] Test navigateur reasoning desktop/mobile et bornes de la ligne contexte.
- [x] Test navigateur Adobe avec choix produit dans la ligne contexte.
- [x] Test navigateur documents actifs mobile avec absence de chevauchement.
- [x] Tests integration frontend chat existants.

### RISQUES

- [x] Contrats fonctionnels rouverts: aucun changement d'id, payload, endpoint ou logique JS.
- [x] Ligne trop chargee: repli mobile et wrapping conserves.
