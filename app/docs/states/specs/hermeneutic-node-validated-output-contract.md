# Hermeneutic Node Validated Output Contract

Statut: spec historique partiellement supersedee
Portee: deuxieme pause normative du Lot 9 pour `validated_output`, relue apres le lot 2 runtime

Note runtime 2026-04-19:

- la sortie souveraine n'est plus une combinaison normative pilotee par `validation_decision`;
- `validated_output` expose maintenant directement le verdict final arbitral;
- `validation_decision` peut subsister comme trace legacy derivee, mais elle n'a plus d'autorite normative propre.

## 1. Purpose

Cette spec ouvre la deuxieme pause normative du Lot 9.

Elle tranchait initialement:

- la nature exacte de la sortie validee minimale
- une table de combinaison normative minimale entre verdict primaire et decision de validation
- le statut initial de `challenge`
- la forme canonique minimale de la sortie finale post-validation
- le statut minimal de `pipeline_directives_final`
- la frontiere avec `primary_verdict`, `validation_dialogue_context` et l'aval

Le runtime lot 2 a depuis precise:

- que `validated_output` transporte un verdict arbitral final direct;
- que l'aval ne rederive plus la posture finale depuis un couple primaire + `validation_decision`;
- que le seam compact d'observabilite lit deja ce verdict final et sa projection.

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

- exposer le verdict final arbitral directement consommable par l'aval
- exposer `pipeline_directives_final`
- exposer une trace compacte de suivi vs override
- eviter que l'aval ait a re-deduire lui-meme la posture finale

Elle ne sert pas a:

- recopier integralement `primary_verdict`
- recopier `validation_dialogue_context`
- transporter les `justifications`
- remplacer l'observabilite

## 5. Decision Retenue Pour La Sortie Terminale

La sortie validee minimale retient explicitement:

- `final_judgment_posture`
- `final_output_regime`
- `pipeline_directives_final`
- `arbiter_reason`

Champs de transition acceptes en lot 2:

- `validation_decision`
  - trace legacy derivee du verdict final et des recommandations amont;
  - non souveraine;
- `arbiter_followed_upstream`
- `advisory_recommendations_followed`
- `advisory_recommendations_overridden`
- `applied_hard_guards`

Taxonomie retenue pour `final_judgment_posture`:

- `answer`
- `clarify`
- `suspend`

Taxonomie retenue pour `final_output_regime`:

- `simple`
- `meta`

Regles fortes:

- l'aval ne rederive plus `final_judgment_posture` depuis `validation_decision`;
- la table de combinaison primaire/validation n'est plus normative dans le runtime lot 2;
- `validation_decision` peut encore aider la compatibilite ou la lecture historique, mais elle est derivee apres coup.

## 6. Legacy Combination Table Status

La table de combinaison documentee dans les versions precedentes de cette spec devient historique.

Depuis le lot 2 runtime:

- le verdict final arbitral est choisi directement par `validation_agent`;
- tout champ `validation_decision` eventuel est derive downstream a titre de compatibilite;
- aucune combinaison primaire + `validation_decision` ne doit redevenir souveraine pour l'aval.

## 7. Minimal Canonical Shape Of `validated_output`

La forme canonique minimale retenue est:

```python
{
    "schema_version": "v1",
    "final_judgment_posture": "answer",
    "final_output_regime": "simple",
    "pipeline_directives_final": ["posture_answer", "regime_simple"],
    "arbiter_followed_upstream": False,
    "advisory_recommendations_followed": [],
    "advisory_recommendations_overridden": ["primary_judgment_posture", "primary_output_regime_proposed"],
    "applied_hard_guards": [],
    "arbiter_reason": "lecture locale suffisante",
}
```

Invariants minimaux:

- un seul format canonique
- `final_judgment_posture` appartient a:
  - `answer`
  - `clarify`
  - `suspend`
- `final_output_regime` appartient a:
  - `simple`
  - `meta`
- `pipeline_directives_final` reste une liste compacte de codes stables
- aucun dump de `primary_verdict`
- aucun dump de `validation_dialogue_context`
- aucun bloc de `justifications`
- `validation_decision`, si present, est un champ legacy derive et non souverain

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
