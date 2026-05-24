# FridaDev - Polish UI chat - TODO

Classement: `app/docs/todo-done/product/`
Statut: termine et archive le 2026-05-24
Date de creation: 2026-05-23
Date de cloture: 2026-05-24

## Intention

Ce TODO regroupe les petits polishs du chat FridaDev. Il ne porte pas un redesign, un changement de theme global ni une refonte des workflows.

Regle de conduite: avancer point par point, cocher seulement ce qui est livre, garder les patches petits, tester le rendu desktop/mobile quand une surface visible change.

## Cloture 2026-05-24

Chantier termine cote utilisateur. Les points de polish identifies sont livres, y compris le point 6 `Messages, byline et copie` et le lot PWA Safari iPhone.

Validation utilisateur 2026-05-24: installation Safari iPhone reussie depuis Safari, icone Frida visible sur le telephone, lancement depuis l'ecran d'accueil OK.

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

- [x] Polir l'etat vide et l'etat resultat.
- [x] Verifier le rendu mobile apres generation.
- [x] Garder le panneau utilitaire, pas marketing.

### 6. Messages, byline et copie

- [x] Auditer le bouton copie et son feedback.
- [x] Verifier hover/focus clavier.
- [x] Ne pas changer le rendu texte brut des messages.

### 7. Manifest PWA Safari iPhone

- [x] Ajouter un manifeste PWA pour permettre `Ajouter a l'ecran d'accueil` depuis Safari iPhone.
- [x] Declarer `name`, `short_name`, `start_url`, `scope`, `display: standalone`, `theme_color` et `background_color`.
- [x] Utiliser l'icone Frida existante `app/web/fridalogo.png`, avec tailles/types adaptes si necessaire.
- [x] Ajouter les balises Safari/iOS utiles: `apple-touch-icon`, `apple-mobile-web-app-capable`, `apple-mobile-web-app-title`, et status bar si pertinent.
- [x] Verifier que la PWA respecte Authelia et ne contourne aucun flux d'authentification.

## Lot futur - Manifest PWA Safari iPhone

Statut: livre et valide utilisateur le 2026-05-24.

### INTENTION

Permettre a l'utilisateur d'installer FridaDev comme petite web app depuis Safari sur iPhone, avec l'icone Frida, un nom propre, une couleur d'habillage coherente et un affichage `standalone`.

### PATCH A PREVOIR

- [x] Creer un manifeste PWA versionne, par exemple `app/web/manifest.webmanifest`.
- [x] Pointer le manifeste depuis `app/web/index.html`.
- [x] Declarer `name`, `short_name`, `description`, `start_url`, `scope`, `display: standalone`, `theme_color`, `background_color`.
- [x] Reutiliser `app/web/fridalogo.png` comme source d'icone; generer des variantes uniquement si les tailles Safari/PWA l'exigent.
- [x] Ajouter les meta tags iOS/Safari necessaires sans modifier la logique chat.

### TESTS / PREUVES

- [x] Verifier que le manifeste est servi avec un contenu JSON/WebManifest valide.
- [x] Verifier que `index.html` reference bien le manifeste et l'icone Apple.
- [x] Verifier que `fridalogo.png` existe et que les tailles declarees sont coherentes.
- [x] Faire une validation manuelle Safari iPhone: ouvrir FridaDev, `Partager`, `Ajouter a l'ecran d'accueil`, lancer l'app installee.

Note 2026-05-24: le runtime est pret pour l'installation Safari iPhone, sans service worker ni cache offline. Validation utilisateur recue le 2026-05-24: installation Safari iPhone reussie, icone Frida visible, lancement depuis l'ecran d'accueil OK.

### RISQUES / REDUCTION

- [x] Ne pas ajouter de service worker ni de cache offline dans ce lot sans decision explicite: risque de confusion avec Authelia, sessions, assets stale et donnees sensibles.
- [x] Ne pas changer Caddy, Authelia, headers plateforme ou auth dans ce lot.
- [x] Ne pas stocker de donnees utilisateur cote client au pretexte de PWA.
- [x] Garder le manifest comme polish d'installation, pas comme refonte mobile.

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


## Lot 4 - Panneau generation image

Statut: livre le 2026-05-23.

### PATCH

- [x] `index.html`: ajoute un etat vide discret `Aucune image` dans le panneau image.
- [x] `index.html` / `styles.css`: cadre le resultat image avec une frame preview et un footer meta/telechargement.
- [x] `chat_image_generation.js` / `app.js`: masque l'etat vide pendant la generation et apres resultat sans changer le payload.

### TESTS

- [x] Test navigateur couvrant etat vide, generation, resultat et masquage de l'etat vide.
- [x] Test navigateur desktop/mobile apres generation avec controles dans les bornes du panneau.
- [x] Tests frontend unitaires existants.
- [x] Verification live apres rebuild.

### RISQUES

- [x] Panneau trop narratif: texte limite a `Aucune image`, pas de marketing ni d'aide longue.
- [x] Regression runtime: aucun changement backend, endpoint image ou contrat de requete.
