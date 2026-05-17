# Hermeneutic - triade Warum / Wofür / Wozu - brouillon TODO

Statut: brouillon de cadrage actif
Classement: `app/docs/todo-todo/memory/`
Portee: cadrage d'une discipline hermeneutique de lecture du texte par la triade `Warum / Wofür / Wozu`
Etat runtime vise: aucun patch runtime dans ce document
Nature: hypothese de chantier futur, pas encore roadmap executable

References liees:
- `app/docs/states/specs/response-arbiter-power-contract.md`
- `app/docs/states/specs/hermeneutic-node-validation-agent-contract.md`
- `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- `app/core/hermeneutic_node/validation/validation_agent.py`
- `app/core/chat_prompt_context.py`
- `app/prompts/validation_agent.txt`
- `app/prompts/main_hermeneutical.txt`

## 1. Question prealable

Question:

> Existe-t-il un meilleur plan que de prolonger tel quel le brouillon actuel de "centre interpretatif du tour" ?

Verdict:

- oui, prolonger tel quel le brouillon precedent figerait une mauvaise formulation;
- le sujet n'est plus un petit objet de sortie du type `user_real_request / turn_stakes / must_not_lose`;
- le sujet est une discipline de lecture du texte selon la triade `Warum / Wofür / Wozu`;
- le meilleur geste documentaire est donc de remplacer l'ancien brouillon par celui-ci, plutot que de conserver deux documents concurrents.

Ce document reprend l'emplacement actif du brouillon precedent, mais en deplace le centre de gravite.

## 2. Requalification du brouillon precedent

Le brouillon precedent etait utile pour poser une intuition:

- Frida peut respecter la posture finale tout en ratant le coeur local d'un tour;
- il faut aider la lecture du tour sans ajouter une nouvelle institution;
- le `validation_agent` et `[JUGEMENT HERMENEUTIQUE]` restent les frontieres les plus probables.

Mais sa formulation etait insuffisante.

Elle risquait de transformer l'intuition en:

- un artefact compact de plus;
- une fiche JSON du tour;
- un pseudo-resume de l'intention utilisateur;
- une nouvelle chose a produire plutot qu'un geste de lecture a tenir.

La correction conceptuelle est la suivante:

> Il ne s'agit pas d'extraire le "centre" du tour comme un objet. Il s'agit de faire travailler la lecture hermeneutique du texte dans la tension des trois pourquoi: Warum, Wofür, Wozu.

## 3. Objet reel du futur chantier

Le futur chantier, s'il s'ouvre, ne doit pas porter d'abord sur une structure de sortie.

Il doit porter sur une discipline de lecture:

- du dernier enonce utilisateur;
- du dialogue comme texte total en cours;
- de la relation entre ce dernier enonce et ce qui s'est deja ecrit dans la conversation.

Cette lecture doit rester textualiste:

- elle porte sur le texte present;
- elle porte sur le dialogue comme texte en devenir;
- elle ne reconstruit pas une psychologie supposee de l'utilisateur;
- elle ne fabrique pas un auteur-totalite derriere l'enonce;
- elle ne confond pas comprehension du texte et divination d'une intention interieure.

## 4. La triade

La triade ne doit pas etre lue comme trois cases independantes.

Elle designe trois modes du pourquoi qui prennent leur force ensemble.

### 4.1 Warum

`Warum` est le pourquoi causal.

Il demande:

- de quoi ce texte procede;
- quelle genese discursive ou argumentative le rend intelligible;
- quel mouvement anterieur, dans le dialogue, le fait advenir.

Sa force:

- il empeche la lecture de flotter hors de toute genese;
- il rappelle qu'un enonce n'arrive pas de nulle part;
- il oblige a relire le dernier tour dans le fil du dialogue.

Son danger:

- rabattre le texte sur un principe auctorial;
- lire le discours comme simple expression d'une intention ou d'une volonte d'auteur;
- reconstruire un auteur-totalite du type "chez Platon" ou "ce que l'utilisateur veut vraiment au fond";
- psychologiser ce qui doit rester lu comme texte.

`Warum` reste donc necessaire, mais reducteur s'il regne seul.

### 4.2 Wofür

`Wofür` est le pourquoi final sous l'angle de l'utilite.

Il demande:

- a quoi ce texte sert;
- ce qu'il permet;
- ce qu'on en fait;
- quel usage, effet ou deplacement il rend possible dans la conversation.

Sa force:

- il empeche la lecture de se croire sans effet;
- il rappelle qu'un texte agit dans une situation;
- il aide Frida a comprendre ce que la reponse doit rendre possible.

Son danger:

- rabattre le texte sur l'usage;
- lire le texte comme avantage, benefice ou consommation culturelle;
- reduire la conversation a ce qui est utile immediatement;
- oublier que le texte peut valoir autrement que par sa rentabilite locale.

`Wofür` participe donc a la comprehension, mais devient reducteur s'il regne seul.

### 4.3 Wozu

`Wozu` est le pour-quoi au sens fort.

Il demande:

- pour-quoi ce texte vaut;
- quelle necessite l'appelle;
- quel fondement echappe au texte tout en le rendant necessaire;
- vers quoi le texte est tendu sans se reduire a son origine ou a son usage.

Sa force:

- il empeche `Warum` et `Wofür` de reduire le texte a sa genese ou a son utilite;
- il ouvre la question de la necessite du texte;
- il maintient la possibilite qu'un texte porte plus que son contexte d'origine ou son usage immediat.

Son danger:

- elever trop vite le texte vers une finalite abstraite;
- produire une profondeur artificielle;
- transformer la lecture en surplomb metaphysique;
- devenir un principe souverain qui ecrase les deux autres modes du pourquoi.

`Wozu` est donc indispensable, mais il ne doit pas devenir le seul principe directeur.

## 5. Ce qui fait la force de la triade

La force n'est pas dans le seul `Wozu`.

La force est dans la tenue ensemble des trois questions:

- `Warum` interroge ce dont le texte procede;
- `Wofür` interroge ce a quoi le texte sert, ce qu'il rend possible, ce qu'il produit comme usage ou effet;
- `Wozu` interroge ce pour quoi le texte vaut, le fondement ou la necessite qui l'appelle.

Pris separement, chacun peut deformer le texte:

- `Warum` le rabat sur l'auteur, l'origine ou la cause;
- `Wofür` le rabat sur l'utilite, l'effet ou la consommation;
- `Wozu` l'eleve trop vite vers une finalite abstraite.

Tenus ensemble, ils se corrigent mutuellement:

- `Warum` empeche `Wozu` de flotter hors de toute genese;
- `Wofür` empeche la lecture de se croire sans effet ni usage;
- `Wozu` empeche `Warum` et `Wofür` de reduire le texte a son origine ou a son utilite.

Le futur chantier, s'il existe, devra donc porter sur cette tension reciproque.

Il ne devra pas designer un vainqueur parmi les trois pourquoi.

## 6. Frontiere avec la psychologie de l'utilisateur

Point non negociable:

- les trois questions portent sur le texte;
- elles ne portent pas sur une psychologie supposee de l'utilisateur.

Mauvais usages:

- "Pourquoi l'utilisateur veut-il vraiment cela au fond ?";
- "Quel besoin cache exprime-t-il ?";
- "Quelle intention psychologique explique ce tour ?";
- "Quel profil affectif faut-il inferer de cette demande ?"

Bons usages:

- "De quoi cet enonce procede-t-il dans le dialogue comme texte ?";
- "Que rend-il possible dans l'echange maintenant ?";
- "Pour-quoi ce texte vaut-il ici, dans cette conversation ?"

La triade doit donc renforcer la lecture du dialogue, pas transformer Frida en interprete psychologique de l'utilisateur.

## 7. Relation avec le systeme courant

Le systeme courant a deja des frontieres fortes:

- `validation_agent` est l'arbitre souverain de la posture finale;
- il lit d'abord `validation_dialogue_context`;
- `validated_output` porte le verdict final;
- `[JUGEMENT HERMENEUTIQUE]` projette vers le modele principal la posture finale et les directives resolues;
- le prompt principal sait que ce bloc ne contient pas tout le dossier interne.

La triade, si elle est un jour implementee, devrait probablement transformer d'abord le geste de lecture du `validation_agent`:

- comment il relit `validation_dialogue_context`;
- comment il comprend le dernier tour dans le dialogue comme texte total;
- comment il evite de confondre origine, usage et necessite;
- comment il tranche sans psychologiser.

Mais ce brouillon ne decide pas encore:

- si cela appartient au prompt du `validation_agent`;
- si cela doit apparaitre dans une spec normative;
- si cela doit produire un champ explicite;
- si cela doit etre projete dans `[JUGEMENT HERMENEUTIQUE]`;
- si cela doit rester une discipline interne de lecture sans nouveau payload.

## 8. Ce que ce chantier ne doit pas devenir

Ce brouillon ne doit pas ouvrir:

- un nouvel agent;
- une nouvelle memoire;
- un nouveau dashboard;
- une table durable;
- un scoring hermeneutique;
- une taxonomie mecanique;
- un objet JSON de plus par reflexe;
- une grille de trois cases a remplir a chaque tour;
- une boucle d'apprentissage;
- un chantier de reception hermeneutique apres coup.

La triade ne doit pas devenir:

- une checklist;
- un rubric score;
- une classification visible dans la reponse finale;
- une justification libre;
- un moyen de produire du meta-discours pseudo-profond.

Elle doit rester, si elle est retenue, une discipline de lecture.

## 9. Forme de travail possible

Hypothese legere a explorer plus tard:

1. documenter une spec courte de lecture triadique;
2. verifier si le prompt du `validation_agent` peut etre ajuste sans changer l'architecture;
3. tester sur un petit corpus de tours ou Frida respecte la posture mais manque le coeur du texte;
4. n'envisager une projection dans `[JUGEMENT HERMENEUTIQUE]` que si elle apporte une clarte reelle;
5. ne produire un champ runtime que si la discipline de lecture ne suffit pas.

Cette sequence preserve l'intuition qu'une mise en oeuvre pourrait rester relativement legere.

Elle inverse la tentation du brouillon precedent:

- d'abord le geste de lecture;
- ensuite seulement un eventuel artefact.

## 10. Questions a trancher avant tout chantier executable

Avant tout lot runtime, il faudra repondre:

- la triade doit-elle vivre seulement dans le prompt du `validation_agent` ?
- doit-elle rester implicite comme discipline de lecture, ou produire une trace compacte ?
- comment verifier qu'elle aide sans transformer la reponse en commentaire hermeneutique ?
- comment empecher `Warum` de psychologiser ?
- comment empecher `Wofür` de consumériser le texte ?
- comment empecher `Wozu` de devenir une finalite abstraite souveraine ?
- comment tester que les trois questions restent tenues ensemble ?
- faut-il une preuve content-free dans les logs, ou serait-ce deja trop ?

## 11. Condition de non-prolongation

Ce brouillon doit rester ferme sur son scope.

Il ne lance pas:

- le runtime;
- un prompt patch;
- une spec normative;
- une evaluation hermeneutique apres coup;
- une refonte du `validation_agent`;
- une nouvelle doctrine de memoire.

Si un futur chantier s'ouvre, son premier lot devra etre documentaire et devra prouver:

- que la triade porte bien sur le texte;
- que les trois questions sont maintenues ensemble;
- que `Wozu` n'est pas traite comme seul principe directeur;
- que l'utilisateur n'est pas psychologise;
- que l'architecture existante suffit peut-etre a porter le geste sans nouvel agent.

## 12. Statut final de ce brouillon

Ce document remplace le brouillon precedent de "centre interpretatif du tour".

La raison du remplacement est conceptuelle:

- l'ancien brouillon cherchait encore une forme d'artefact compact;
- le cadrage actuel cherche une discipline triadique de lecture du texte;
- l'emplacement probable reste le sillage du `validation_agent`, mais la question runtime est volontairement suspendue.

Le chantier ne doit pas etre ouvert comme implementation tant que cette discipline n'a pas ete stabilisee comme doctrine de lecture.
