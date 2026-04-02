# Hermeneutic Node Output Regime Contract

Statut: draft normatif ouvert
Portee: premiere pause normative du Lot 8 pour `output_regime`

## 1. Purpose

Cette spec ouvre le premier sous-pas normatif du Lot 8.

Elle tranche:

- la nature exacte de `output_regime`
- la taxonomie minimale de `discursive_regime`
- la taxonomie minimale de `resituation_level`
- la taxonomie minimale de `time_reference_mode`
- l'articulation explicite de ces trois axes avec `judgment_posture`
- le format compact minimal du futur bloc doctrinal de sortie

Elle ne code rien.
Elle ne ferme ni la persistance d'etat du noeud, ni le payload unique complet, ni le fail-open primaire.

## 2. Repo Grounding

Le repo a deja stabilise:

- `judgment_posture`
- `epistemic_regime`, `proof_regime`, `uncertainty_posture`
- `source_priority`
- `source_conflicts`

Notamment:

- `app/docs/states/specs/hermeneutic-node-judgment-posture-contract.md`
- `app/docs/states/specs/hermeneutic-node-epistemic-regime-contract.md`
- `app/docs/states/specs/hermeneutic-node-source-priority-contract.md`
- `app/docs/states/specs/hermeneutic-node-source-conflict-contract.md`

Le sous-pas traite ici reste:

- un module doctrinal de sortie primaire du noeud

La cible code de cette pause normative est donc:

- `app/core/hermeneutic_node/doctrine/output_regime.py`

Et non:

- `app/core/hermeneutic_node/runtime/node_state.py`
- `app/core/hermeneutic_node/inputs/output_regime_input.py`

## 3. Inputs / Doctrine / Runtime Boundary

`output_regime` est une sortie doctrinale du noeud primaire.

Il:

- consomme des entrees canoniques et des sorties doctrinales deja structurees
- ne constitue pas une nouvelle entree canonique
- ne constitue pas encore la sortie complete du noeud
- ne constitue pas la persistance d'etat du noeud
- ne constitue pas la validation finale aval

Frontiere minimale:

- `inputs/`
  - matieres canoniques recues par le noeud
- `doctrine/`
  - arbitrages doctrinaux primaires du noeud
- `runtime/`
  - persistance, inertie, wiring technique, fail-open, integration du payload unique

`output_regime` appartient explicitement a `doctrine/`, pas a `runtime/`.

## 4. Nature Exacte De `output_regime`

`output_regime` est un bloc doctrinal de sortie primaire borne.

Il fixe:

- `discursive_regime`
- `resituation_level`
- `time_reference_mode`

Il ne fixe pas encore:

- le texte final utilisateur
- la persistance de l'etat du noeud
- le payload unique complet du verdict primaire
- la table complete avec l'agent de validation

Lecture minimale des trois axes:

- `discursive_regime`
  - quelle forme discursive substantive prend la sortie
- `resituation_level`
  - combien la sortie recontextualise
- `time_reference_mode`
  - depuis quel mode temporel la sortie parle

## 5. Minimal Taxonomy For `discursive_regime`

La taxonomie retenue est:

- `meta`
- `simple`
- `cadre`
- `comparatif`
- `continuite`

Cette taxonomie est retenue car elle reste:

- courte
- directement codable
- distincte de `judgment_posture`
- distincte de `resituation_level`

Definitions minimales:

- `meta`
  - aucun regime discursif substantif n'est retenu en propre a ce tour
  - la sortie reste gouvernee directement par `judgment_posture`
- `simple`
  - la sortie substantive va droit au point sans organisation discursive speciale
- `cadre`
  - la sortie substantive pose d'abord un cadre, une limite ou une condition de lecture
- `comparatif`
  - la sortie substantive organise explicitement une comparaison entre lectures, options ou cas
- `continuite`
  - la sortie substantive se tient d'abord dans la reprise d'un fil deja etabli dans le dialogue

Regles minimales:

- `discursive_regime` ne doit jamais reexprimer `answer | clarify | suspend`
- `discursive_regime` ne doit jamais redoubler `resituation_level`
- `meta` n'est ni un synonyme de `clarify`, ni un synonyme de `suspend`

Decision normative minimale:

- dans cette V1, `discursive_regime` reste total
- si `judgment_posture = answer`, `discursive_regime` doit etre l'un de:
  - `simple`
  - `cadre`
  - `comparatif`
  - `continuite`
- si `judgment_posture != answer`, `discursive_regime = meta`

## 6. Minimal Taxonomy For `resituation_level`

La taxonomie retenue est:

- `none`
- `light`
- `explicit`
- `strong`

Definitions minimales:

- `none`
  - aucune recontextualisation explicite n'est requise
- `light`
  - un rappel bref ou une remise en contexte legere suffit
- `explicit`
  - la sortie doit expliciter clairement le cadre ou le rappel pertinent
- `strong`
  - la sortie doit recontextualiser de maniere marquee avant de tenir son point principal

Regles minimales:

- `resituation_level` dit combien on recontextualise, pas sous quelle forme on parle
- un meme `discursive_regime` peut exister avec plusieurs `resituation_level`
- `resituation_level` peut rester utile meme quand `judgment_posture != answer`

## 7. Minimal Taxonomy For `time_reference_mode`

La taxonomie retenue est:

- `immediate_now`
- `dialogue_relative`
- `anchored_past`
- `prospective`
- `atemporal`

Definitions minimales:

- `immediate_now`
  - la sortie parle depuis l'immediat du present du tour
- `dialogue_relative`
  - la sortie parle relativement a ce qui vient d'etre dit, decide ou corrige dans l'echange
- `anchored_past`
  - la sortie parle depuis un passe explicitement ancre
- `prospective`
  - la sortie parle depuis un futur vise, une suite attendue ou un possible a venir
- `atemporal`
  - la sortie parle sans ancrage temporel operatoire dominant

Regles minimales:

- `time_reference_mode` ne recopie ni `time_input`, ni `qualification_temporelle`
- il dit comment la sortie parle du temps, pas quel etait le payload temporel brut
- `time_input` et `qualification_temporelle` contraignent ce choix sans le determiner mecaniquement

## 8. Explicit Link With `judgment_posture`

Articulation minimale retenue:

- `judgment_posture`
  - dit sous quel regime de parole le noeud peut parler
- `discursive_regime`
  - dit quelle forme discursive substantive prend la sortie
- `resituation_level`
  - dit combien la sortie recontextualise
- `time_reference_mode`
  - dit depuis quel mode temporel la sortie parle

Discipline minimale:

- `judgment_posture` garde seul `answer | clarify | suspend`
- `discursive_regime` ne decide pas si le noeud clarifie ou suspend
- `resituation_level` ne dit pas si la parole est substantive, clarificatrice ou suspensive
- `time_reference_mode` ne dit pas si la parole est validee; il dit seulement comment elle se situe dans le temps

## 9. Minimal Output Shape

La forme minimale attendue est:

```python
{
    "discursive_regime": "meta",
    "resituation_level": "light",
    "time_reference_mode": "dialogue_relative",
}
```

Invariants minimaux:

- exactement trois champs
- aucune prose libre
- aucun champ decoratif supplementaire
- si `judgment_posture = answer`, `discursive_regime` ne doit pas etre `meta`
- si `judgment_posture != answer`, `discursive_regime` doit rester `meta` dans cette V1

## 10. Link With The Future Primary Verdict

Ce bloc devra plus tard s'articuler proprement avec:

- `epistemic_regime`
- `proof_regime`
- `judgment_posture`
- `source_priority`
- `source_conflicts`
- `pipeline_directives_provisional`

Mais cette spec ne fixe pas encore:

- le payload unique complet du noeud
- l'ordre exact d'integration runtime
- la persistance de cet etat doctrinal

## 11. Non-goals

Cette premiere pause normative de Lot 8 ne fixe pas encore:

- la persistance d'etat du noeud
- `node_state.py`
- les regles d'inertie
- le fail-open primaire complet
- les champs complets d'auditabilite
- la sortie finale post-validation
- la table de combinaison avec l'agent de validation
