# Hermeneutic - centre interpretatif du tour - brouillon TODO

Statut: brouillon de cadrage actif
Classement: `app/docs/todo-todo/memory/`
Portee: cadrage d'un possible artefact compact de tour courant, derive du verdict hermeneutique final
Etat runtime vise: aucun patch runtime dans ce document
Nature: hypothese de chantier futur, pas encore roadmap executable

References liees:
- `app/docs/states/specs/response-arbiter-power-contract.md`
- `app/docs/states/specs/hermeneutic-node-primary-verdict-contract.md`
- `app/docs/states/specs/hermeneutic-node-validation-agent-contract.md`
- `app/docs/states/specs/hermeneutic-node-downstream-branching-contract.md`
- `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- `app/core/hermeneutic_node/validation/validation_agent.py`
- `app/core/chat_prompt_context.py`
- `app/prompts/validation_agent.txt`
- `app/prompts/main_hermeneutical.txt`

## 1. Question de depart

Question prealable:

> Existe-t-il un meilleur plan que d'ajouter encore une nouvelle couche hermeneutique ?

Verdict de cadrage:

- oui, le meilleur plan n'est pas d'ajouter une institution de plus;
- le systeme sait deja arbitrer la posture finale `answer / clarify / suspend` et le regime de sortie via `validation_agent`;
- `[JUGEMENT HERMENEUTIQUE]` projette deja le verdict final valide vers le modele principal;
- l'hypothese utile, si elle se confirme, est plus petite: formuler le centre interpretatif du tour a l'interieur de ce verdict final ou dans sa projection compacte.

Ce brouillon existe donc pour cadrer une idee, pas pour ouvrir directement un lot runtime.

## 2. Pourquoi cette idee existe

Le systeme courant sait deja dire, en forme compacte:

- quelle posture finale adopter;
- quel regime de sortie appliquer;
- quelles directives finales sont actives.

Cette stabilisation est importante, mais elle ne formule pas toujours explicitement le noyau local du tour:

- ce que l'utilisateur demande reellement ici;
- ce qui est en jeu dans ce tour precis;
- ce qu'une bonne reponse ne doit surtout pas perdre.

L'intuition produit est que certaines reponses peuvent respecter la posture finale tout en ratant le coeur concret du tour.

Le `centre interpretatif du tour` viserait a aider le modele principal a garder ce coeur en vue, sans grossir le systeme.

## 3. Etat courant revalide

### 3.1 Ce qui existe deja

Le repo a deja ferme plusieurs frontieres:

- `validation_agent` est l'arbitre souverain du verdict final;
- l'amont hermeneutique reste conseiller, non souverain;
- les garde-fous durs sont rares et bornent seulement certains cas;
- `validated_output` porte `final_judgment_posture`, `final_output_regime`, `pipeline_directives_final`, `arbiter_reason` et les traces de suivi / override;
- `[JUGEMENT HERMENEUTIQUE]` est la projection aval compacte vers le prompt principal;
- le prompt principal sait lire `[JUGEMENT HERMENEUTIQUE]` comme une brique normative derivee de `validated_output`.

### 3.2 Ce qui manque eventuellement

Le verdict final courant decide la posture et le regime, mais ne porte pas encore une formulation structuree du centre local de la demande.

`arbiter_reason` existe, mais il reste une raison courte d'arbitrage. Il n'est pas contracte comme:

- une reformulation de la demande reelle;
- une qualification de l'enjeu local;
- un rappel du point a ne pas perdre.

Le manque pressenti n'est donc pas un manque de pouvoir institutionnel, mais un manque possible de matiere interpretative compacte pour le modele principal.

## 4. Ce que serait le centre interpretatif

Le centre interpretatif serait:

- un artefact compact du tour courant;
- produit dans le sillage du verdict final;
- lisible par le modele principal;
- borne a quelques champs courts;
- revisable a chaque tour;
- non persistant durable par defaut.

Il ne serait pas:

- une analyse longue;
- un nouveau resume;
- une memoire;
- un objet `node_state`;
- une justification libre;
- une decision autonome;
- un score de qualite;
- un agent supplementaire;
- une nouvelle couche souveraine.

Formulation courte:

> Le centre interpretatif ne decide pas quoi faire a la place du verdict final. Il aide a ne pas perdre ce que le tour demande vraiment.

## 5. Emplacement pressenti

Hypothese la plus sobre:

1. `validation_agent` produit ou stabilise le centre interpretatif en meme temps que le verdict final.
2. `validated_output` porte une forme compacte optionnelle, si le chantier est ouvert plus tard.
3. `chat_prompt_context.py` projette cette forme dans `[JUGEMENT HERMENEUTIQUE]`, avec une prose courte et stable.

Ce placement respecte les frontieres existantes:

- pas de nouvel agent;
- pas de nouvelle institution hermeneutique;
- pas de persistence durable dans `node_state` par defaut;
- pas de branchement aval qui consommerait le `primary_verdict` brut;
- pas de prompt principal charge de re-deduire lui-meme le centre depuis tout le dossier interne.

Emplacements a eviter par defaut:

- `node_state`: risque de transformer un centre local et revisable en etat durable;
- Memory/RAG: risque de transformer une lecture du tour en souvenir;
- prompt principal seul: risque de demander au modele de deviner ce qui aurait du etre arbitre en amont;
- nouvel agent: complexite institutionnelle inutile a ce stade.

## 6. Forme cible minimale

Ne pas figer prematurement un schema runtime, mais la forme logique maximale acceptable pour un premier essai serait proche de:

```json
{
  "interpretive_center": {
    "user_real_request": "phrase courte",
    "turn_stakes": "phrase courte",
    "must_not_lose": "phrase courte"
  }
}
```

Contraintes fortes:

- trois champs courts maximum pour la V1;
- pas de taxonomie lourde;
- pas de classification pseudo-savante;
- pas de justification longue;
- pas de duplication de `arbiter_reason` si celui-ci suffit deja;
- pas de contenu brut supplementaire expose aux logs;
- pas de persistance durable par defaut.

Projection possible dans `[JUGEMENT HERMENEUTIQUE]`:

```text
Centre du tour: <demande reelle compacte>.
Enjeu local: <ce qui est en jeu>.
Point a ne pas perdre: <point decisif>.
```

Cette projection ne doit etre envisagee que si elle ameliore effectivement la reponse finale.

## 7. Benefices attendus

Benefices possibles:

- reponses plus justes localement;
- moindre risque de respecter formellement la posture tout en ratant la demande;
- meilleure attention au point concret du tour;
- matiere compacte pour une future evaluation de justesse hermeneutique apres coup;
- meilleure separation entre "posture de reponse" et "coeur interpretatif de la demande".

Ce benefice reste a prouver.

Le brouillon ne suppose pas encore que cette idee merite implementation.

## 8. Risques

Risques principaux:

- gonfler le pipeline hermeneutique;
- produire du meta-discours pseudo-profond;
- doubler les justifications;
- contraindre trop tot une lecture qui devrait rester revisable;
- faire croire que ce centre remplace la lecture directe du dialogue;
- transformer un artefact local en nouvelle memoire;
- confondre centre interpretatif et reception hermeneutique apres coup;
- rendre `[JUGEMENT HERMENEUTIQUE]` trop bavard pour le prompt principal.

Risque produit important:

- une mauvaise formulation du centre pourrait ecraser la demande utilisateur au lieu de l'eclairer.

## 9. Questions a trancher avant tout lot executable

Avant d'ouvrir un vrai lot runtime, il faudrait repondre a ces questions:

- `arbiter_reason` peut-il etre clarifie pour porter deja cette fonction, sans nouveau champ ?
- faut-il trois champs, deux champs, ou un seul champ ?
- le centre doit-il etre expose au prompt principal a chaque tour ou seulement dans les cas ambigus ?
- quelle est la longueur maximale acceptable dans `[JUGEMENT HERMENEUTIQUE]` ?
- comment tester que le centre aide vraiment sans juger subjectivement toute reponse ?
- quelles donnees content-free doivent etre journalisees, si quelque chose doit l'etre ?

## 10. Condition de non-prolongation

Ce brouillon ne doit pas ouvrir:

- un nouvel agent;
- une nouvelle memoire;
- une nouvelle table durable;
- un nouveau dashboard;
- un scoring complexe;
- une boucle d'apprentissage;
- un chantier de reception hermeneutique complet;
- une refonte du `validation_agent`;
- une reecriture generale de `[JUGEMENT HERMENEUTIQUE]`.

Si cette idee devient un chantier, son premier lot devra rester documentaire et prouver que:

- `validation_agent` est bien le bon lieu;
- le centre interpretatif ne double pas `arbiter_reason`;
- le prompt principal beneficie d'une projection compacte;
- aucune nouvelle souverainete n'est creee.

## 11. Relation avec un futur chantier de reception

Le centre interpretatif du tour est prospectif et local:

- il aide a repondre maintenant.

Un eventuel futur chantier de reception hermeneutique serait retrospectif:

- il regarderait apres coup si la reponse a ete juste, fine ou adequate.

Ces deux idees doivent rester distinctes.

Le present brouillon ne lance pas le chantier de reception.

## 12. Statut final de ce brouillon

Cette idee merite un chantier separe seulement si un prochain cadrage demontre qu'elle apporte quelque chose que `arbiter_reason`, `pipeline_directives_final` et `[JUGEMENT HERMENEUTIQUE]` ne portent pas deja.

A ce stade, l'emplacement le plus probable reste:

- dans le sillage du `validation_agent`;
- projete eventuellement par `chat_prompt_context.py`;
- consomme par le modele principal dans `[JUGEMENT HERMENEUTIQUE]`.

Tout autre emplacement devrait etre justifie par un besoin plus fort que celui etabli ici.
