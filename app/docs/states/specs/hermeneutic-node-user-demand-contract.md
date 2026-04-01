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
- ouvrir un deuxieme axe minimal sur le `besoin de preuve`;
- ouvrir un troisieme axe minimal sur la `qualification_temporelle`;
- preparer les autres qualificateurs secondaires sans les trancher ici.

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

## Secondary Axis - Besoin de preuve as Probative Regime

Le `besoin de preuve` n'est pas un simple curseur `faible / moyen / fort`.

Dans cette spec, il est ouvert comme un premier contrat de `regime probatoire`.

Regle directrice:

- le tour doit appeler le maximum de preuve possible au regard de ce qui est disponible et pertinent;
- ce maximum n'autorise ni l'exigence de l'impossible, ni la reduction de la preuve a un score unique;
- la force probatoire depend du type de preuve, de sa provenance, du regime de vigilance applicable, et de sa composition avec d'autres preuves.

Nom doctrinal provisoire:

- `maximal_possible`

Ce nom ne fixe pas encore un format runtime final. Il fixe seulement la logique de lecture minimale du deuxieme axe.

## Minimal Proof Types

Premiere taxonomie minimale des natures de preuve:

- `factuelle`
- `scientifique`
- `argumentative`
- `hermeneutique`
- `dialogique`

Regles minimales:

- cette taxonomie decrit des natures de preuve, pas une hierarchie finale entre elles;
- `factuelle` ne vaut pas automatiquement plus que `hermeneutique`;
- une preuve interpretee peut etre necessaire pour donner sens a un fait brut;
- une preuve dialogique peut etre decisive pour etablir la continuite d'un echange, meme sans valoir comme preuve scientifique;
- une preuve argumentative peut etre forte si elle est articulee avec d'autres preuves et faible si elle reste seule.

## Provenance

La provenance n'est pas identique au type de preuve.

Liste minimale de provenance ouverte ici:

- `dialogue_trace`
- `dialogue_resume`
- `web`

Regles normatives minimales:

- `dialogue_trace` designe l'ancrage dans les traces du dialogue et vaut en priorite comme ancrage `factuelle` ou `dialogique`;
- `dialogue_resume` designe un ancrage interprete et vaut en priorite comme support `hermeneutique`;
- `web` n'est jamais un type de preuve en soi; c'est une provenance possible de preuves `factuelle`, `scientifique`, `argumentative`, ou autres;
- aucune lecture probatoire ne doit confondre la nature de la preuve et son lieu de provenance.

## Vigilance Regime

Le regime de vigilance minimal distingue ici:

- `standard`
- `renforce`

Regles minimales:

- `web` implique toujours une `vigilance renforcee`;
- une preuve de provenance `web` exige une source explicite;
- une preuve de provenance `web` reste fortement revisable;
- une preuve de provenance `web` appelle un soupcon methodique;
- cette vigilance est partagee entre `FridaDev` et l'interlocuteur, pas externalisee sur un seul pole;
- `dialogue_trace` et `dialogue_resume` relevent par defaut de la vigilance `standard`, sans etre pour autant auto-suffisants en toute situation.

## Probative Composition

La force d'un regime probatoire depend aussi de la composition des preuves, pas seulement de leur type isole.

Categories minimales de composition:

- `isolee`
- `appuyee`
- `corroboree`
- `articulee`
- `convergente`
- `fragilisee`
- `sous_soupcon`

Regles minimales:

- une composition n'est renforcante que si les preuves restent relativement heterogenes ou independantes;
- plusieurs preuves du meme ordre, issues de la meme provenance, ne valent pas automatiquement corroboration;
- une composition n'est forte que si les preuves portent sur la meme these ou sur des aspects compatibles de cette these;
- une articulation probatoire doit etre explicite et non seulement juxtaposee;
- une contradiction non traitee fragilise la composition;
- une provenance sous vigilance renforcee peut rester recevable, mais ne doit pas se presenter comme auto-suffisante.

## Analytical Examples

Exemples analytiques minimaux:

- `scientifique + argumentative`
  - plus fort qu'une argumentation seule si l'argumentation articule correctement le support scientifique;
- `factuelle + hermeneutique`
  - plus legitime qu'un fait nu quand l'interpretation eclaire le sens du fait sans l'ecraser;
- `dialogique-trace + hermeneutique`
  - fort pour etablir une continuite de sens dans le dialogue;
- `resume + trace`
  - bon combo: le resume interprete, la trace ancre;
- `web sourcee + corroboration non-web`
  - recevable et parfois fort, mais sous vigilance renforcee;
- `web seule`
  - jamais pleinement auto-suffisante dans cette premiere pose doctrinale.

## Secondary Axis - Qualification temporelle

La `qualification_temporelle` qualifie le regime de temps du tour utilisateur.

Elle comporte deux dimensions distinctes mais jointes:

- `portee_temporelle`
- `ancrage_temporel`

Regle de structure:

- ces deux dimensions doivent rester distinctes;
- elles appartiennent pourtant a une meme `qualification_temporelle`;
- `portee_temporelle` ne dit pas quelle source prime;
- `ancrage_temporel` ne remplace pas la portee;
- un tour recoit une `portee_temporelle` dominante;
- un tour recoit un `ancrage_temporel` dominant, sauf si le cas est honnetement `mixte`.

## Portee temporelle

La `portee_temporelle` dit de quel temps parle le tour.

Taxonomie minimale:

- `atemporale`
- `immediate`
- `actuelle`
- `passee`
- `prospective`

Regles minimales:

- `atemporale`
  - contenu relativement independant d'un moment precis;
- `immediate`
  - maintenant strict du dialogue ou de l'action en cours;
- `actuelle`
  - etat courant, presentement valable, mais revisable;
- `passee`
  - etat, fait, sequence ou sens situes dans le passe;
- `prospective`
  - futur, projection, anticipation, plan.

## Ancrage temporel

L'`ancrage_temporel` dit depuis quelle matiere temporelle le tour se comprend ou s'etablit.

Taxonomie minimale:

- `now`
- `non_ancre`
- `dialogue_trace`
- `dialogue_resume`
- `historique_externe`
- `projection`
- `mixte`

Regles minimales:

- `now`
  - ancrage dans le maintenant strict du systeme ou du dialogue;
- `non_ancre`
  - le tour ne depend pas d'un ancrage temporel fort et ne mobilise pas honnetement plusieurs ancrages distincts;
- `dialogue_trace`
  - ancrage dans les traces du dialogue;
- `dialogue_resume`
  - ancrage dans le resume du dialogue;
- `historique_externe`
  - ancrage dans une histoire ou un passe exterieurs au dialogue;
- `projection`
  - ancrage dans un horizon d'anticipation ou de planification;
- `mixte`
  - plusieurs ancrages temporels sont reellement actifs sans reduction honnete a un seul.

## Minimal Temporal Examples

Exemples minimaux:

- "Qu'est-ce qu'on fait maintenant ?"
  - `portee_temporelle = immediate`
  - `ancrage_temporel = now`
- "Qu'est-ce qu'on s'est dit plus tot ?"
  - `portee_temporelle = passee`
  - `ancrage_temporel = dialogue_trace`
- "Selon ce qu'on a deja resume..."
  - `portee_temporelle = passee`
  - `ancrage_temporel = dialogue_resume`
- "Historiquement, cette notion vient d'ou ?"
  - `portee_temporelle = passee`
  - `ancrage_temporel = historique_externe`
- "Que devra-t-on faire ensuite ?"
  - `portee_temporelle = prospective`
  - `ancrage_temporel = projection`
- "C'est quoi un embedding ?"
  - `portee_temporelle = atemporale`
  - `ancrage_temporel = non_ancre`

## Temporal Qualification Frontier

Cette `qualification_temporelle` reste minimale.

Elle ne decide pas encore:

- quelle source prime;
- quel regime epistemique final s'impose;
- quelle posture de jugement adopter;
- quelle table de decision complete permet de deriver automatiquement chaque qualification temporelle.

## Minimal Canonical Object

L'objet canonique minimal `tour_utilisateur` est maintenant defini comme une structure exploitable, non finale, et suffisante pour porter:

- l'axe primaire `geste_dialogique_dominant`;
- le qualificateur secondaire `regime_probatoire`;
- le qualificateur secondaire `qualification_temporelle`.

Forme minimale normative:

- `schema_version`
- `geste_dialogique_dominant`
- `regime_probatoire`
- `qualification_temporelle`

Contraintes minimales:

- `schema_version` versionne explicitement le contrat canonique minimal;
- `geste_dialogique_dominant` porte un seul geste dominant dans cette premiere version;
- `regime_probatoire` reste structure et ne se reduit jamais a un score unique;
- `qualification_temporelle` contient explicitement `portee_temporelle` et `ancrage_temporel`;
- ce contrat est minimal et exploitable, mais il ne pretend pas fixer tous les axes futurs.

Le sous-objet `regime_probatoire` doit au minimum contenir:

- `principe`
- `types_de_preuve_attendus`
- `provenances`
- `regime_de_vigilance`
- `composition_probatoire`

Le sous-objet `qualification_temporelle` doit au minimum contenir:

- `portee_temporelle`
- `ancrage_temporel`

Exemple normatif compact:

```python
tour_utilisateur = {
    "schema_version": "v1",
    "geste_dialogique_dominant": "interrogation",
    "regime_probatoire": {
        "principe": "maximal_possible",
        "types_de_preuve_attendus": ["factuelle", "dialogique"],
        "provenances": ["dialogue_trace"],
        "regime_de_vigilance": "standard",
        "composition_probatoire": "appuyee",
    },
    "qualification_temporelle": {
        "portee_temporelle": "passee",
        "ancrage_temporel": "dialogue_trace",
    },
}
```

Cet exemple illustre le contrat minimal. Il ne fixe ni les extensions futures, ni les regles de derivation automatique.

## Repo / Program Grounding

Cette ouverture de contrat est grounded dans l'etat actuel du programme:

- `app/docs/todo-todo/memory/hermeneutic-convergence-node-todo.md` ouvre le sous-bloc B du Lot 2 pour `tour_utilisateur`;
- `app/docs/states/architecture/hermeneutic_convergence_node.md` fait du tour utilisateur un determinant du noeud, pas une simple metadonnee de requete;
- `app/docs/states/architecture/hermeneutic_convergence_node_matrix.md` indique qu'un socle canonique minimal est desormais pose pour `tour_utilisateur`, tout en laissant ses raffinements ouverts;
- `app/docs/states/specs/hermeneutic-node-dual-feed-contract.md` impose que les futures entrees canoniques restent lisibles au seam, sans dissoudre la matiere dans un texte opaque.
- `app/docs/states/specs/hermeneutic-recent-window-extraction-contract.md` pose deja `fenetre_recente` comme extraction mecanique distincte de toute qualification semantique, ce qui oblige a situer le `besoin de preuve` au-dessus de cette extraction et non a la place de celle-ci.
- le grounding temporel du repo existe deja comme entree canonique `temps`, mais cette spec ne transforme pas `qualification_temporelle` en doctrine finale du temps; elle fixe seulement la lecture minimale du temps du tour utilisateur.

Cette spec ne cree donc pas un axe doctrinal abstrait hors-sol. Elle ouvre le futur contrat d'entree `tour_utilisateur` la ou le chantier Lot 2 en a besoin.

## What Remains Open

Restent explicitement ouverts:

- les regles de decision permettant de choisir automatiquement le geste dominant;
- les regles permettant de deriver un regime probatoire operationnel a partir de cette premiere grammaire;
- les regles permettant de deriver automatiquement une `qualification_temporelle` stable dans les cas limites ou mixtes;
- la ponderation relative entre types de preuve, provenance et composition selon les familles de tours;
- la gestion des tours mixtes ou composes;
- la frontiere exacte entre qualification minimale et interpretation metier avancee;
- les extensions futures et la forme runtime detaillee du futur objet canonique `tour_utilisateur`;
- l'articulation avec la posture de jugement et le regime epistemique des lots suivants.

## Non-goals / Out of Scope

Cette premiere pose doctrinale ne tranche pas:

- un bareme final ou score unique de preuve;
- une table finale de decision probatoire par cas d'usage;
- une doctrine finale du temps ou une hierarchie des ancrages temporels;
- les signaux d'ambiguite ou de sous-determination;
- la taxonomie finale complete des sous-cas;
- le code runtime `user_demand.py`;
- l'implementation du classement automatique des tours.

## Next Axes To Discuss Later

Les axes secondaires a ouvrir apres cette premiere pose sont:

- `ambiguite / sous-determination`
- le raffinement du `besoin de preuve` en contrat operationnel plus fin
- le raffinement de la `qualification_temporelle` en contrat operationnel plus fin

Regle de lecture:

- ces axes viendront comme qualificateurs secondaires;
- ils ne doivent pas remplacer l'axe primaire du geste dialogique dominant deja retenu ici.
