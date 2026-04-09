# Identity Surface Canonical Layout TODO

Statut: actif
Classement: `app/docs/todo-todo/admin/`
Surface cible: `/identity`
Origine: formalisation canonique du diagnostic UX/runtime produit sur OVH apres constat de surface trop dense, trop redondante et peu exploitable pour le pilotage immediat.

## Objectif

Refondre la surface `/identity` pour qu'elle devienne une surface de pilotage operateur d'abord, et une surface de diagnostic ensuite.

Le futur patch doit produire une page ou l'operateur voit et modifie sans scroll important:

- LLM statique
- LLM mutable
- User statique
- User mutable

Le reste doit etre range en dessous, replie ou extrait selon son statut reel:

- lecture runtime detaillee
- diagnostics / historique
- gouvernance
- corrections recentes

## Decision produit non negociable

- Decision produit explicite: `LLM vide` = etat degrade.
- Le sujet `llm` ne doit pas etre vide dans l'etat nominal du produit.
- Un `llm` vide est un etat degrade / incorrect, pas un etat normal.
- L'UI doit rendre cet etat visible immediatement en haut de page.
- Un `llm` vide ne doit jamais etre noye dans une longue pile readonly ni masque par la presence d'autres couches (`legacy`, `evidence`, `conflicts`, representations runtime, etc.).

Conséquences operatoires obligatoires:

- si `llm.static` est vide, l'operateur doit le voir immediatement dans le bloc `LLM statique`
- si `llm.mutable` est vide, l'operateur doit le voir immediatement dans le bloc `LLM mutable`
- l'etat degrade doit etre signale par un libelle explicite, compact et non ambigu
- la page ne doit pas laisser croire que `llm` est "introuvable"; elle doit montrer clairement qu'il est absent et que c'est anormal

## Constat de depart sur la surface actuelle

Etat actuel observe dans le code:

- la page commence par une hero et une longue explication conceptuelle avant les zones d'edition
- le flux principal enchaine:
  - structure reelle
  - etat courant par sujet
  - runtime representations
  - editeurs statique
  - editeurs mutable
  - gouvernance
  - legacy / evidence / conflicts
  - corrections recentes
- le read model montre deja `static`, `mutable`, `legacy_fragments`, `evidence` et `conflicts` dans une meme lecture
- la page rerend ensuite une partie de ces informations dans d'autres sections

Etat runtime constate sur OVH au moment de la redaction:

- `llm.static`: vide
- `llm.mutable`: vide
- `user.static`: present
- `user.mutable`: present

Interpretation produit imposee:

- cet etat `llm` vide n'est pas un cas nominal a rendre "acceptable"
- la future UI doit le signaler comme un etat degrade a corriger

## Invariants canoniques de la page

### 1. Pilotage canonique actif

La premiere zone utile de `/identity` doit etre une zone `Pilotage canonique actif`.

Cette zone doit afficher les 4 blocs canoniques, sans scroll important:

- `LLM statique`
- `LLM mutable`
- `User statique`
- `User mutable`

Ordre obligatoire:

- desktop: grille 2x2
- mobile: pile verticale dans cet ordre exact

Les 4 blocs ne doivent pas etre repousses sous la ligne de flottaison par:

- une grande intro conceptuelle
- des explications produit trop longues
- des panneaux readonly diagnostiques

### 2. Runtime detaille

La lecture runtime detaillee reste utile, mais ne doit pas preceder les 4 blocs canoniques.

Cette couche peut montrer:

- la fiche structuree pour le jugement
- le texte identity injecte au modele
- les metas globales de contrat actif

Mais elle doit vivre plus bas dans la page et etre repliee par defaut si son volume est important.

### 3. Diagnostics / historique

La couche `Diagnostics / historique` ne doit pas vivre dans le meme flux visuel que le pilotage canonique.

Elle regroupe:

- `legacy_fragments`
- `evidence`
- `conflicts`
- corrections recentes

Cette couche doit etre:

- plus bas dans la page
- repliee par defaut
- ou extraite dans une surface dediee si le volume reste trop important

## Contrat canonique des 4 blocs

Chaque bloc doit exposer immediatement:

- etat principal: `Absent` / `Present`
- etat runtime: `Charge` / `Non charge`
- etat injection: `Injecte` / `Non injecte`
- `len`
- provenance compacte
- derniere mise a jour si disponible
- zone editable
- actions

Le bloc ne doit pas exiger l'ouverture d'un autre panneau pour repondre a la question operatoire de base:

```text
Est-ce que ce contenu existe, est-il charge, est-il injecte, puis-je l'editer maintenant ?
```

### Contrat du statique

Pour `LLM statique` et `User statique`, la provenance compacte doit au minimum exposer:

- nature du stockage: `resource_path`
- champ runtime concerne
- resolution de chemin
- chemin resolu ou etat de resolution

Le statique doit aussi montrer:

- `Present` si le contenu actif est non vide
- `Absent` si le contenu actif est vide
- `Charge` si le runtime charge ce contenu
- `Injecte` si ce contenu participe a l'injection active

### Contrat de la mutable

Pour `LLM mutable` et `User mutable`, la provenance compacte doit au minimum exposer:

- nature du stockage: `identity_mutables`
- `updated_by`
- `updated_ts`
- raison de mise a jour si elle existe

La mutable doit aussi montrer:

- `Present` si le contenu canonique stocke est non vide
- `Absent` si le contenu canonique stocke est vide
- `Charge` si le runtime charge cette mutable
- `Injecte` si elle participe a l'injection active

## Contrat produit attendu par bloc

### LLM statique

- nominal: non vide
- vide interdit a l'etat nominal
- doit etre charge au runtime
- doit etre visible comme participant a l'identite active quand le contrat `static + mutable narrative` est en vigueur
- si vide: etat degrade visible immediatement, sans ambiguite

### LLM mutable

- nominal: non vide
- vide interdit a l'etat nominal
- doit etre charge au runtime
- doit etre visible comme participant a l'identite active quand le contrat `static + mutable narrative` est en vigueur
- si vide: etat degrade visible immediatement, sans ambiguite

### User statique

- nominal: non vide
- vide non souhaite
- doit etre charge au runtime quand configure
- l'UI doit rendre visible son etat reel sans le confondre avec `llm`
- si vide: etat degrade visible, mais moins critique que `llm`

### User mutable

- nominal: presente quand la couche dynamique user est en usage
- vide tolere temporairement seulement si l'operateur le comprend explicitement comme un manque de matiere courante
- doit afficher clairement sa derniere mise a jour et sa provenance
- si vide: l'UI doit le dire explicitement, sans laisser croire que la mutable est cachee

## Regles de presentation des etats

L'UI doit distinguer clairement:

- `Absent`: contenu vide ou non configure
- `Present`: contenu non vide
- `Charge`: contenu pris en compte par le runtime actuel
- `Non charge`: contenu stocke mais non pris en compte
- `Injecte`: contribue a l'identite active ou au bloc prompt actif
- `Non injecte`: visible seulement, hors injection active
- `Editable`: modifiable depuis cette page
- `Etat degrade`: etat non nominal necessitant une action operateur

Regle specifique `llm`:

- si `llm.static` ou `llm.mutable` est vide, le bloc doit afficher un signal degrade fort et immediat
- ce signal doit etre plus visible que les compteurs readonly historiques

## Deduplication obligatoire

Les redondances suivantes doivent disparaitre dans le futur patch:

- ne pas montrer `static` / `mutable` trois fois sous des formes equivalentes
- ne pas garder `legacy`, `evidence` et `conflicts` dans le meme flux que le pilotage canonique
- ne pas laisser une grande intro conceptuelle repousser les 4 blocs sous la ligne de flottaison
- ne pas faire coexister un "etat courant" deja exhaustif avec des editeurs qui reracontent les memes statuts sans changement de niveau de lecture
- ne pas dupliquer les couches historiques a la fois dans le read model principal et dans une section diagnostics separee

## Rangement canonique impose

Ordre cible de la page:

1. bandeau de statut compact
2. `Pilotage canonique actif`
3. metas runtime globales compactes
4. `Runtime detaille`
5. gouvernance
6. `Diagnostics / historique`

Regles associees:

- `Pilotage canonique actif` reste ouvert et visible
- `Runtime detaille` peut etre replie par defaut
- `Diagnostics / historique` doit etre replie par defaut
- les corrections recentes ne doivent pas etre traitees comme le probleme principal de volume

## Lotissement d'implementation

### Lot 1 - Hierarchie et remontee des 4 blocs

- remonter les 4 blocs canoniques tout en haut
- imposer l'ordre desktop 2x2 / mobile vertical
- reduire l'intro de tete a une forme compacte

### Lot 2 - Traitement explicite des etats degrades `llm`

- introduire le signal visuel degrade pour `llm.static` vide
- introduire le signal visuel degrade pour `llm.mutable` vide
- rendre cet etat visible des l'arrivee sur la page

### Lot 3 - Deduplication des vues

- retirer du flux principal les redites entre read model, runtime et editeurs
- reduire la repetition des chips `stored / loaded / injected / len`
- faire du read model une lecture de synthese, pas un second flux exhaustif concurrent

### Lot 4 - Relegation / repli des diagnostics

- sortir `legacy`, `evidence`, `conflicts` du parcours principal
- replier par defaut `Diagnostics / historique`
- garder un acces operateur, mais non concurrent du pilotage immediat

### Lot 5 - Arbitrage sur runtime representations / diagnostics dedies

- trancher si les runtime representations detaillees restent sur `/identity`
- ou si elles doivent migrer vers une surface plus clairement diagnostique
- conserver seulement ce qui aide reellement l'operateur a comprendre l'etat actif

## Hors scope

- refonte complete du contrat memoire / identite
- modification backend du sens de `loaded_for_runtime` ou `actively_injected`
- redesign global de tout l'admin
- nouvelle campagne d'audit generale

## Definition de done du futur patch

Le futur lot d'implementation sera considere comme boucle quand:

- les 4 blocs sont visibles immediatement
- l'etat `llm` vide est visible comme degrade
- le scroll principal avant edition est fortement reduit
- `Pilotage canonique actif`, `Runtime detaille` et `Diagnostics / historique` sont nettement separes
- les redondances principales ont disparu
- l'operateur peut comprendre en quelques secondes quoi editer et ce qui est reellement absent
