# Hermeneutic Node Validated Output Contract

Statut: draft normatif ouvert
Portee: deuxieme pause normative du Lot 9 pour `validated_output`

## 1. Purpose

Cette spec ouvre la deuxieme pause normative du Lot 9.

Elle tranche:

- la nature exacte de la sortie validee minimale
- la table de combinaison normative minimale entre verdict primaire et decision de validation
- le statut exact de `challenge`
- la forme canonique minimale de la sortie finale post-validation
- le statut minimal de `pipeline_directives_final`
- la frontiere avec `primary_verdict`, `validation_dialogue_context` et l'aval

Elle ne code rien.
Elle ne ferme ni `validation_agent.py`, ni le wiring aval, ni l'observabilite complete du dispositif final.

## 2. Repo Grounding

Le repo a deja stabilise:

- `primary_verdict`
- `validation_agent`
- la frontiere `primary_node -> validation -> aval`
- `pipeline_directives_provisional`
- la centralite de `validation_dialogue_context`

Notamment:

- `app/docs/states/specs/hermeneutic-node-primary-verdict-contract.md`
- `app/docs/states/specs/hermeneutic-node-validation-agent-contract.md`
- `app/docs/states/architecture/hermeneutic_convergence_node.md`
- `app/core/hermeneutic_node/runtime/primary_node.py`

La cible code la plus propre pour cette pause normative reste:

- `app/core/hermeneutic_node/validation/validation_agent.py`

Cette spec ne cree ni ce fichier, ni sa sortie runtime.

## 3. Validation / Final Output / Downstream Boundary

La sortie validee minimale est:

- la premiere sortie finale consommable par l'aval
- produite apres `primary_verdict`
- produite apres decision du `validation_agent`

Elle n'est pas:

- `primary_verdict`
- `node_state`
- un event log
- un dump de `validation_dialogue_context`

Regle forte:

- l'aval ne consomme jamais `primary_verdict` brut
- l'aval consomme uniquement la sortie validee minimale

## 4. Nature Exacte De `validated_output`

`validated_output` est l'enveloppe canonique minimale de la sortie post-validation.

Elle sert a:

- exposer la decision de validation
- exposer une posture finale directement consommable par l'aval
- exposer `pipeline_directives_final`
- eviter que l'aval ait a re-deduire lui-meme la posture finale

Elle ne sert pas a:

- recopier integralement `primary_verdict`
- recopier `validation_dialogue_context`
- transporter les `justifications`
- remplacer l'observabilite

## 5. Decision Retenue Pour La Sortie Terminale

La sortie validee minimale retient explicitement:

- `validation_decision`
- `final_judgment_posture`
- `pipeline_directives_final`

Decision normative:

- `final_judgment_posture` est requis

Raison:

- l'aval ne doit pas re-deduire lui-meme la posture finale a partir de `validation_decision` et du verdict primaire

Taxonomie retenue pour `final_judgment_posture`:

- `answer`
- `clarify`
- `suspend`

Decision normative sur `challenge`:

- `challenge` reste visible comme `validation_decision`
- `challenge` n'est pas une posture aval-consommable terminale
- `challenge` doit etre resolu par la table de combinaison vers `final_judgment_posture`
- `challenge` sur un primaire `answer` ne doit pas etre rabattu mecaniquement sur `clarify`
- en V1, il peut deboucher sur `final_judgment_posture = answer` quand la validation juge qu'une correction du verdict primaire reste compatible avec une reponse finale normale

## 6. Minimal Normative Combination Table

Table minimale retenue:

```python
{
    "answer": {
        "confirm": "answer",
        "challenge": "answer",
        "clarify": "clarify",
        "suspend": "suspend",
    },
    "clarify": {
        "confirm": "clarify",
        "challenge": "clarify",
        "clarify": "clarify",
        "suspend": "suspend",
    },
    "suspend": {
        "confirm": "suspend",
        "challenge": "suspend",
        "clarify": "clarify",
        "suspend": "suspend",
    },
}
```

Lecture normative compacte:

1. `confirm` preserve la `judgment_posture` primaire
2. `clarify` force `final_judgment_posture = clarify`
3. `suspend` force `final_judgment_posture = suspend`
4. `challenge` n'est pas terminal pour l'aval
5. `challenge` se resout vers:
   - `answer` si la posture primaire etait `answer`
   - `clarify` si la posture primaire etait `clarify`
   - `suspend` si la posture primaire etait deja `suspend`
6. cette resolution garde `challenge` visible comme decision de validation sans exclure artificiellement une posture finale `answer`

Regle forte:

- cette table s'applique apres une decision de validation deja pesee par `validation_dialogue_context`
- elle ne reduit pas la validation a une simple mecanique detachee du contexte dialogique elargi

## 7. Minimal Canonical Shape Of `validated_output`

La forme canonique minimale retenue est:

```python
{
    "schema_version": "v1",
    "validation_decision": "challenge",
    "final_judgment_posture": "answer",
    "pipeline_directives_final": ["..."],
}
```

Invariants minimaux:

- un seul format canonique
- `validation_decision` appartient a:
  - `confirm`
  - `challenge`
  - `clarify`
  - `suspend`
- `final_judgment_posture` appartient a:
  - `answer`
  - `clarify`
  - `suspend`
- `pipeline_directives_final` reste une liste compacte de codes stables
- aucun dump de `primary_verdict`
- aucun dump de `validation_dialogue_context`
- aucun bloc de `justifications`

## 8. Minimal Status Of `pipeline_directives_final`

`pipeline_directives_final`:

- appartient a `validated_output`
- remplace fonctionnellement `pipeline_directives_provisional` pour l'aval
- reste compact, stable et codable
- ne doit pas etre un blob texte libre

Discipline minimale:

- pas de doublons
- pas de prose UX finale
- pas de recopie brute de `pipeline_directives_provisional`

Cette pause normative ne ferme pas encore:

- le vocabulaire complet de `pipeline_directives_final`
- son runtime exact

## 9. Boundary With `primary_verdict` And `validation_dialogue_context`

Frontiere minimale:

- `primary_verdict`
  - reste un artefact amont de lecture et de revision
- `validation_dialogue_context`
  - pese fortement sur la decision de validation
- `validated_output`
  - reste la seule enveloppe minimale aval-consommable

Regles fortes:

- `validated_output` ne recopie pas integralement `primary_verdict`
- `validated_output` ne dump pas `validation_dialogue_context`
- `justifications` restent hors `primary_verdict` et hors `validated_output`
- la combinaison normative sert justement a eviter que l'aval doive relire lui-meme les artefacts amont

## 10. Non-goals

Cette pause normative ne ferme pas encore:

- `validation_agent.py`
- le wiring aval
- l'observabilite complete du dispositif final
- les KPI de stabilite
- les preconditions shadow
- la shadow globale
