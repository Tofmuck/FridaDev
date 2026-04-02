# Hermeneutic Node Lot 8 Validation Report

## Statut

Lot 8 est ferme au niveau normatif et runtime.

## Briques fermees

- `output_regime`
  - spec: `app/docs/states/specs/hermeneutic-node-output-regime-contract.md`
  - runtime: `app/core/hermeneutic_node/doctrine/output_regime.py`
- `state_persistence`
  - spec: `app/docs/states/specs/hermeneutic-node-state-persistence-contract.md`
  - runtime: `app/core/hermeneutic_node/runtime/node_state.py`
- `primary_verdict`
  - spec: `app/docs/states/specs/hermeneutic-node-primary-verdict-contract.md`
  - runtime: `app/core/hermeneutic_node/runtime/primary_node.py`

## Resultat structurel ferme

- `output_regime` calcule `discursive_regime`, `resituation_level` et `time_reference_mode`.
- `node_state` porte un state minimal conversation-scoped avec inertie bornee.
- `primary_node` produit un `primary_verdict` canonique unique.
- le `primary_verdict` inclut un fail-open primaire explicite dans la meme forme canonique.
- le `primary_verdict` reste distinct de `node_state`, de l'observability et des `justifications`.

## Verification runtime presente

- `app/tests/unit/core/hermeneutic_node/doctrine/test_output_regime.py`
- `app/tests/unit/core/hermeneutic_node/runtime/test_node_state.py`
- `app/tests/unit/core/hermeneutic_node/runtime/test_primary_node.py`

## Limites explicitement laissees ouvertes

- validation hermeneutique finale
- `justifications`
- `pipeline_directives_final`
- branchement aval sur sortie revisee
- observabilite finale du dispositif complet
- shadow globale hors scope

## Frontiere

- le `primary_verdict` n'est pas la sortie finale consommee par l'aval
- Lot 9 commence a la validation du verdict primaire
