# Identity Surface Canonical Layout TODO

Statut: actif
Classement: `app/docs/todo-todo/admin/`
Surface cible: `/identity`
Origine: formalisation canonique du diagnostic UX/runtime produit sur OVH apres constat de surface trop dense, trop redondante et peu exploitable pour le pilotage immediat.

## Objectif

- [x] Garder ce chantier distinct du chantier doctrinal `identity != prompt`, maintenant archive dans `app/docs/todo-done/refactors/identity-vs-prompt-separation-todo.md`.
- [x] Garder ce chantier distinct du mini-lot admin `app/docs/todo-todo/admin/hermeneutic-dashboard-mode-since-todo.md`.
- [x] Transformer `/identity` en surface de pilotage operateur d'abord, et en surface de diagnostic ensuite.

## Decisions acquises

- [x] `llm.static` vide est un etat degrade reel.
- [x] `llm.mutable` vide doit etre visible explicitement.
- [x] `llm.mutable` vide ne doit pas etre surelevee comme la meme anomalie fondamentale que `llm.static` vide.
- [x] La page `/identity` doit separer `Pilotage canonique actif`, `Runtime detaille` et `Diagnostics / historique`.
- [x] La page ne doit pas laisser croire que `llm` est introuvable; elle doit montrer clairement ce qui est absent, ce qui est present et ce qui releve d'un etat degrade reel.
- [x] Le futur patch doit rester borne au layout, a la hierarchie et a la lisibilite operateur, sans rouvrir les lots memoire deja fermes.

## Snapshot de depart utile

- [x] Au `2026-04-09`, le runtime OVH montre `llm.static` presente, chargee et injectee.
- [x] Au `2026-04-09`, le runtime OVH montre `llm.mutable` vide, non chargee et non injectee.
- [x] La page actuelle commence encore par une hero et une longue explication conceptuelle avant les zones d'edition.
- [x] Le flux principal actuel enchaine structure reelle, etat courant par sujet, runtime representations, editeurs, gouvernance, legacy/evidence/conflicts et corrections recentes.
- [x] Le read-model montre deja `static`, `mutable`, `legacy_fragments`, `evidence` et `conflicts` dans une meme lecture.
- [x] La page rerend ensuite une partie de ces informations dans d'autres sections.

## Invariants UX / produit

### Pilotage canonique actif

- [x] La premiere zone utile de `/identity` doit etre `Pilotage canonique actif`.
- [x] Cette zone doit afficher les 4 blocs canoniques:
  - `LLM statique`
  - `LLM mutable`
  - `User statique`
  - `User mutable`
- [x] Ordre obligatoire:
  - desktop: grille 2x2
  - mobile: pile verticale dans cet ordre exact
- [x] Les 4 blocs ne doivent pas etre repousses sous la ligne de flottaison par une longue intro ou des panneaux readonly diagnostiques.

### Runtime detaille

- [x] La lecture runtime detaillee reste utile.
- [x] Elle ne doit pas preceder les 4 blocs canoniques.
- [x] Elle doit vivre plus bas dans la page et pouvoir etre repliee par defaut si son volume est important.

### Diagnostics / historique

- [x] `Diagnostics / historique` ne doit pas vivre dans le meme flux visuel que le pilotage canonique.
- [x] Cette couche regroupe `legacy_fragments`, `evidence`, `conflicts` et les corrections recentes.
- [x] Cette couche doit etre plus bas dans la page, repliee par defaut, ou extraite si le volume reste trop important.

## Checklist des exigences canoniques

### 1. Visibilite immediate des 4 blocs

- [x] Remonter `LLM statique`, `LLM mutable`, `User statique` et `User mutable` tout en haut de la page.
- [x] Rendre ces 4 blocs visibles sans scroll important.
- [x] Garder l'ordre desktop `2x2` et mobile vertical.
- [x] Reduire l'intro de tete a une forme compacte qui ne concurrence pas l'edition.

### 2. Contrat d'information minimal par bloc

- [x] Afficher `Absent / Present` pour chaque bloc.
- [x] Afficher `Charge / Non charge` pour chaque bloc.
- [x] Afficher `Injecte / Non injecte` pour chaque bloc.
- [x] Afficher `len` pour chaque bloc.
- [x] Afficher une provenance compacte pour chaque bloc.
- [x] Afficher la derniere mise a jour si elle existe.
- [x] Garder la zone editable et les actions dans le meme bloc.
- [x] Permettre de repondre sans autre panneau a la question:
  - `Est-ce que ce contenu existe, est-il charge, est-il injecte, puis-je l'editer maintenant ?`

### 3. Contrat du statique

- [x] Montrer la provenance `resource_path` pour `LLM statique` et `User statique`.
- [x] Montrer le champ runtime concerne pour le statique.
- [x] Montrer la resolution de chemin et le chemin resolu, ou l'etat de resolution.
- [x] Signaler `llm.static` vide comme etat degrade visible immediatement.

### 4. Contrat de la mutable

- [x] Montrer la provenance `identity_mutables` pour `LLM mutable` et `User mutable`.
- [x] Montrer `updated_by`.
- [x] Montrer `updated_ts`.
- [x] Montrer la raison de mise a jour si elle existe.
- [x] Afficher `llm.mutable` vide comme `Absente`, sans laisser croire a un bloc cache ou introuvable.
- [x] Ne pas marquer par defaut `llm.mutable` vide comme la meme anomalie fondamentale que `llm.static` vide.

### 5. Separation des couches

- [x] Garder `Pilotage canonique actif` dans le flux principal visible.
- [x] Sortir le detail runtime complet du flux principal de `/identity` et ne garder qu'un repere compact avec acces clair au detail diagnostique.
- [x] Releguer `Diagnostics / historique` plus bas et le rendre repliable par defaut.
- [x] Eviter que les couches runtime ou historiques ecrasent la lecture des 4 blocs canoniques.

### 6. Deduplication

- [x] Ne pas montrer `static` / `mutable` trois fois sous des formes equivalentes.
- [x] Ne pas garder `legacy`, `evidence` et `conflicts` dans le meme flux que le pilotage canonique.
- [x] Ne pas faire coexister un `etat courant` deja exhaustif avec des editeurs qui reracontent les memes statuts sans gain de lecture.
- [x] Ne pas dupliquer les couches historiques a la fois dans le read-model principal et dans une section diagnostics separee.

## Lots d'implementation

### Lot 1 - Hierarchie et remontee des 4 blocs

- [x] Remonter les 4 blocs canoniques tout en haut.
- [x] Imposer l'ordre desktop `2x2` / mobile vertical.
- [x] Reduire l'intro de tete a une forme compacte.

### Lot 2 - Traitement explicite des etats `llm`

- [x] Introduire le signal visuel degrade pour `llm.static` vide.
- [x] Introduire un etat explicite `Absente` pour `llm.mutable` vide, distinct d'un etat degrade critique.
- [x] Rendre ces etats visibles des l'arrivee sur la page.

### Lot 3 - Deduplication des vues

- [x] Retirer du flux principal les redites entre read-model, runtime et editeurs.
- [x] Reduire la repetition des chips `stored / loaded / injected / len`.
- [x] Faire du read-model une lecture de synthese, pas un second flux exhaustif concurrent.

### Lot 4 - Relegation / repli des diagnostics

- [x] Sortir `legacy`, `evidence` et `conflicts` du parcours principal.
- [x] Replier par defaut `Diagnostics / historique`.
- [x] Garder un acces operateur utile, mais non concurrent du pilotage immediat.

### Lot 5 - Arbitrage sur runtime representations / diagnostics dedies

- [x] Trancher que les runtime representations detaillees ne restent plus dans le flux principal de `/identity`.
- [x] Migrer leur detail complet vers une surface plus clairement diagnostique: `/hermeneutic-admin`.
- [x] Conserver sur `/identity` seulement ce qui aide reellement l'operateur a comprendre l'etat actif.

## Definition of done

- [x] Les 4 blocs canoniques sont visibles immediatement.
- [x] L'absence de `llm.static` est visible comme degrade.
- [x] L'absence de `llm.mutable` reste visible sans ambiguite, sans etre confondue avec l'anomalie `llm.static` vide.
- [x] Le scroll principal avant edition est fortement reduit.
- [x] `Pilotage canonique actif`, `Runtime detaille` et `Diagnostics / historique` sont nettement separes.
- [x] Les redondances principales ont disparu.
- [x] L'operateur peut comprendre en quelques secondes quoi editer et ce qui est reellement absent.

## Hors scope

- [x] Ne pas fusionner ce chantier avec `hermeneutic-dashboard-mode-since-todo.md`.
- [x] Ne pas reouvrir le chantier doctrinal `identity vs prompt`.
- [x] Ne pas patcher frontend ou backend dans le present document.
- [x] Ne pas lancer un redesign global de tout l'admin dans le present document.
- [x] Ne pas traiter ici le finding `arbiter model drift`.
