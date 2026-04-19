# Hermeneutic Node Judgment Posture Contract

Statut: draft normatif ouvert
Portee: contrat doctrinal minimal pour `judgment_posture`

## 1. Purpose

Cette spec fixe le socle doctrinal minimal du Lot 5.

Elle tranche:

- la nature exacte de `judgment_posture`
- la definition minimale de `answer`, `clarify`, `suspend`
- les criteres minimaux de decision
- le lien explicite avec les signaux du Lot 2
- le lien explicite avec `epistemic_regime`, `proof_regime` et `uncertainty_posture` du Lot 4
- les effets doctrinaux minimaux de chaque posture

Elle ne code rien.
Elle ferme le contrat doctrinal qui devra preceder `app/core/hermeneutic_node/doctrine/judgment_posture.py`.

## 2. Repo Grounding

Le repo a deja stabilise:

- des entrees canoniques du noeud sous `app/core/hermeneutic_node/inputs/`
- un module doctrinal `epistemic_regime.py` sous `app/core/hermeneutic_node/doctrine/`

Notamment:

- `user_turn_input.py`
- `epistemic_regime.py`

Le Lot 5 reste dans le meme cadre:

- `inputs/` = matieres canoniques recues par le noeud
- `doctrine/` = logique doctrinale elaboree par le noeud

La cible code de ce lot reste donc:

- `app/core/hermeneutic_node/doctrine/judgment_posture.py`

Et non:

- `app/core/hermeneutic_node/inputs/judgment_posture_input.py`

## 3. Inputs / Doctrine Boundary

`judgment_posture` est une sortie doctrinale du noeud.

Elle:

- consomme des entrees canoniques deja structurees
- ne constitue pas une nouvelle entree canonique
- n'est pas encore la validation finale aval
- n'est pas un simple switch d'action pipeline
- n'est pas une decision d'absence de sortie textuelle

`judgment_posture` designe la posture primaire de parole et de jugement legitime pour le tour.

## 4. Minimal Taxonomy

La taxonomie minimale retenue est:

- `answer`
- `clarify`
- `suspend`

Ces trois valeurs sont retenues car elles restent:

- courtes
- mutuellement distinctes
- directement codables
- suffisantes pour separer parole substantive, parole clarificatrice et parole suspensive

## 5. Minimal Definitions

### 5.1 `answer`

`answer` designe un regime de parole substantive.

Le noeud peut prendre en charge la demande telle qu'elle est et soutenir une reponse de fond.

Cela n'implique pas une assertivite maximale.
Une reponse `answer` peut rester prudente, nuancee, ou conditionnelle si le Lot 4 l'impose.

### 5.2 `clarify`

`clarify` designe un regime de parole clarificatrice.

Le noeud parle pour demander la precision qui manque encore a la determination responsable de la demande.

Le blocage principal se situe du cote:

- de l'ambiguite de referent
- de la sous-determination de visee
- du critere manquant
- de la portee insuffisamment fixee
- d'un ancrage de source non determine

### 5.3 `suspend`

`suspend` designe un regime de parole suspensive.

Le noeud parle pour expliciter qu'il ne peut pas trancher proprement dans l'etat.

Le blocage principal se situe du cote:

- de la soutenabilite epistemique
- du manque probatoire
- de la verification manquante
- d'un conflit actif
- ou d'un blocage doctrinal fort deja etabli

`suspend` n'est:

- ni un silence
- ni un abort de tour
- ni une absence de reponse

`suspend` reste une forme de parole:

- de suspension du jugement
- de non-tranchage explicite
- de retenue assertive sur le point bloque

## 6. Minimal Decision Rules

Regle directrice:

- `suspend` si le blocage principal vient de la soutenabilite du jugement
- `clarify` si le blocage principal vient de la determination inachevee de la demande et peut etre leve par une precision utilisateur
- `answer` sinon, si une prise en charge substantive reste legitime

Discipline minimale:

- ne pas confondre manque de preuve et manque de cadrage
- ne pas transformer toute incertitude en `suspend`
- ne pas transformer toute ambiguite en `suspend`
- ne pas produire `answer` si le Lot 4 porte deja un blocage epistemique dur

## 7. Link With Lot 2

Les signaux du Lot 2 servent prioritairement a discriminer `clarify` contre `answer`.

Signaux canoniques pertinents:

- `ambiguity_present`
- `underdetermination_present`
- `active_signal_families`
- `active_signal_families_count`

Lecture minimale des familles:

- `referent`
  - pousse vers `clarify`
- `visee`
  - pousse vers `clarify`
- `critere`
  - pousse vers `clarify`
- `portee`
  - pousse vers `clarify`
- `ancrage_de_source`
  - pousse vers `clarify`
- `coherence`
  - pousse vers `clarify` si le blocage reste local au cadrage de la demande

Regles minimales:

- ces signaux ne doivent pas, a eux seuls, fabriquer `suspend`
- ils orientent vers `clarify` tant qu'une precision utilisateur peut lever le manque principal
- ils ne dominent pas un blocage epistemique deja durci par le Lot 4

## 8. Link With Lot 4

`judgment_posture` ne duplique pas `epistemic_regime`.

`epistemic_regime`, `proof_regime` et `uncertainty_posture` disent quel est l'etat de soutenabilite de la lecture.
`judgment_posture` dit quelle forme de parole reste legitime a partir de cet etat.

Regles minimales de correspondance:

- `contradictoire` -> `suspend`
- `a_verifier` n'impose plus a lui seul `suspend`
- `suspendu` -> `suspend`
- `certain` -> tend normalement vers `answer`
- `probable` -> tend normalement vers `answer`
- `incertain` -> peut aller vers `clarify` ou `answer` selon que le manque principal est de cadrage ou de soutenabilite legere

Modulations minimales:

- `certain` et `probable` peuvent quand meme produire `clarify` si les signaux du Lot 2 montrent qu'une precision utilisateur reste necessaire
- `incertain` ne doit pas aller automatiquement vers `suspend`
- une `uncertainty_posture = bloquante` pousse vers `suspend`
- une `uncertainty_posture = explicite` ne suffit pas a elle seule a produire `suspend`
- `proof_regime = verification_externe_requise` n'impose plus a lui seul `suspend`
- le lot 5 ferme `answer` downstream via garde-fou dur si la verification externe manque reellement
- `proof_regime = arbitrage_requis` pousse vers `suspend`

## 9. Minimal Effects

Effets doctrinaux minimaux:

- `answer`
  - autorise une reponse substantive
  - autorise une assertivite seulement dans les bornes deja fixees par le Lot 4
- `clarify`
  - autorise une demande de precision ciblee
  - interdit de faire comme si la demande etait deja completement determinee
- `suspend`
  - autorise une suspension explicite du jugement
  - autorise une parole de non-tranchage responsable
  - interdit une assertivite pleine sur le point bloque

Ces effets ne fixent pas encore:

- le wording final
- l'UX detaillee
- le format exact de la reponse aval

## 10. Minimal Output Shape

La forme minimale attendue du bloc doctrinal correspondant est:

```python
{
    "judgment_posture": "clarify",
}
```

Invariants minimaux:

- une valeur unique
- aucune prose libre dans le payload minimal
- pas de justification longue integree

## 11. Non-goals

Cette spec n'ouvre pas encore:

- la validation finale aval
- la formulation exacte de la reponse utilisateur
- la table complete entre `judgment_posture` primaire et decision de validation
- une UX complete des messages de clarification
- une theorie generale de l'echec conversationnel
