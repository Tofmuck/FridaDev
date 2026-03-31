# Contrat de qualification minimale du tour utilisateur

Date: 2026-03-31
Statut: draft normatif ouvert
Scope: premiere pose doctrinale pour qualifier le tour utilisateur comme geste dialogique dominant

## Purpose

Cette spec ouvre le contrat de qualification minimale du tour utilisateur pour le futur noeud hermeneutique de `FridaDev`.

Elle ne ferme pas encore le contrat complet.

Son objectif est plus borne:

- fixer un axe primaire de lecture du tour utilisateur;
- poser une premiere taxonomie minimale et totalisante;
- preparer les futurs qualificateurs secondaires sans les trancher ici.

L'axe primaire retenu est:

- le geste dialogique dominant du tour

## Why Not "Type de Demande" as Primary Axis

`type de demande` n'est pas retenu comme axe premier.

Raison:

- cet axe pousse vers une lecture utilitariste du tour;
- il traite l'utilisateur comme emetteur de requetes a satisfaire;
- il ecrase trop vite la dimension de reprise, d'objection, de regulation, d'exposition, ou d'adresse relationnelle;
- il est moins fidele au regime hermeneutique vise par le projet, ou le tour vaut d'abord comme mouvement dans l'echange.

Dans `FridaDev`, le tour utilisateur doit donc etre lu d'abord comme acte dialogique, et seulement ensuite comme demande au sens utilitaire eventuel.

## Primary Dialogic Taxonomy

Premiere taxonomie minimale, totalisante, et englobante du geste dialogique dominant:

- `exposition`
- `interrogation`
- `orientation`
- `positionnement`
- `regulation`
- `adresse_relationnelle`

Regle normative provisoire:

- un seul geste dialogique dominant est retenu par tour dans cette premiere version;
- la composition de gestes multiples reste un travail ulterieur, pas un contrat ferme ici.

## Taxon Descriptions

### `exposition`

Le tour apporte de la matiere au dialogue.

Cas typiques:

- raconter;
- decrire;
- contextualiser;
- signaler un etat ou un fait;
- partager une experience ou une situation.

### `interrogation`

Le tour ouvre une indetermination.

Cas typiques:

- demander;
- questionner;
- faire preciser;
- faire expliquer;
- faire verifier.

### `orientation`

Le tour oriente l'action du dialogue.

Cas typiques:

- demander de faire;
- proposer une suite;
- prescrire une methode;
- relancer vers un but;
- fixer une direction de travail.

### `positionnement`

Le tour prend position sur ce qui est dit ou fait.

Cas typiques:

- accord;
- desaccord;
- objection;
- validation;
- correction;
- preference;
- choix.

### `regulation`

Le tour agit sur le cadre meme de l'echange.

Cas typiques:

- arreter;
- reprendre;
- reformuler;
- changer le rythme;
- corriger le STT;
- recadrer la methode.

### `adresse_relationnelle`

Le tour travaille le lien interlocutif.

Cas typiques:

- saluer;
- remercier;
- s'excuser;
- rassurer;
- exprimer une tension ou une confiance.

## Repo / Program Grounding

Cette ouverture de contrat est grounded dans l'etat actuel du programme:

- `app/docs/todo-todo/memory/hermeneutic-convergence-node-todo.md` ouvre le sous-bloc B du Lot 2 pour `demande_utilisateur`;
- `app/docs/states/architecture/hermeneutic_convergence_node.md` fait de la demande utilisateur un determinant du noeud, pas une simple metadonnee de requete;
- `app/docs/states/architecture/hermeneutic_convergence_node_matrix.md` indique que la demande utilisateur n'est pas encore canonique, mais doit devenir une entree autonome;
- `app/docs/states/specs/hermeneutic-node-dual-feed-contract.md` impose que les futures entrees canoniques restent lisibles au seam, sans dissoudre la matiere dans un texte opaque.

Cette spec ne cree donc pas un axe doctrinal abstrait hors-sol. Elle ouvre le futur contrat d'entree `demande_utilisateur` la ou le chantier Lot 2 en a besoin.

## What Remains Open

Restent explicitement ouverts:

- les regles de decision permettant de choisir automatiquement le geste dominant;
- la gestion des tours mixtes ou composes;
- la frontiere exacte entre qualification minimale et interpretation metier avancee;
- la forme runtime finale du futur objet canonique `demande_utilisateur`;
- l'articulation avec la posture de jugement et le regime epistemique des lots suivants.

## Non-goals / Out of Scope

Cette premiere pose doctrinale ne tranche pas:

- le `besoin de preuve`;
- la `portee temporelle`;
- les signaux d'ambiguite ou de sous-determination;
- la taxonomie finale complete des sous-cas;
- le code runtime `user_demand.py`;
- l'implementation du classement automatique des tours.

## Next Axes To Discuss Later

Les axes secondaires a ouvrir apres cette premiere pose sont:

- `besoin de preuve`
- `portee temporelle`
- `ambiguite / sous-determination`

Regle de lecture:

- ces axes viendront comme qualificateurs secondaires;
- ils ne doivent pas remplacer l'axe primaire du geste dialogique dominant deja retenu ici.
