# Hermeneutic Node Primary Verdict Contract

Statut: draft normatif ouvert
Portee: troisieme brique normative du Lot 8 pour `primary_verdict`

## 1. Purpose

Cette spec ouvre puis ferme la troisieme brique normative du Lot 8.

Elle tranche:

- la nature exacte de `primary_verdict`
- la forme canonique minimale du payload primaire unique
- la place exacte des `justifications`
- le statut minimal de `pipeline_directives_provisional`
- le contrat minimal de fail-open primaire
- les champs minimaux d'auditabilite embarques dans le payload
- la frontiere avec `node_state`, l'observabilite et la validation

Elle ne code rien.
Elle ne fixe ni le runtime complet du noeud primaire, ni la persistance SQL detaillee, ni la sortie finale post-validation.

## 2. Repo Grounding

Le repo a deja stabilise:

- `epistemic_regime`, `proof_regime`, `uncertainty_posture`
- `judgment_posture`
- `source_priority`
- `source_conflicts`
- `output_regime`
- `node_state`

Notamment:

- `app/docs/states/specs/hermeneutic-node-epistemic-regime-contract.md`
- `app/docs/states/specs/hermeneutic-node-judgment-posture-contract.md`
- `app/docs/states/specs/hermeneutic-node-source-priority-contract.md`
- `app/docs/states/specs/hermeneutic-node-source-conflict-contract.md`
- `app/docs/states/specs/hermeneutic-node-output-regime-contract.md`
- `app/docs/states/specs/hermeneutic-node-state-persistence-contract.md`

Le repo pose aussi deja:

- une politique DB-only pour le state metier
- une observabilite existante via `observability.chat_log_events`

La cible code la plus propre pour cette brique reste:

- `app/core/hermeneutic_node/runtime/primary_node.py`

Cette spec ne cree ni ce fichier, ni son wiring.

## 3. Doctrine / Runtime / Observability / Validation Boundary

`primary_verdict` est la sortie primaire canonique unique du noeud.

Il:

- est produit avant validation
- agrege dans une meme forme les sorties doctrinales deja fermees
- reste compact, stable, testable et minimalement auditable
- est destine a etre revise par l'agent de validation

En V1, les `justifications` ne font pas partie de cette forme canonique minimale.
Elles restent un artefact frere destine a la validation.

Il n'est pas:

- une nouvelle entree canonique
- `node_state`
- un event log
- un historique complet du tour
- la sortie finale consommee par l'aval

Frontiere minimale:

- `doctrine/`
  - sorties doctrinales du tour courant
- `runtime/`
  - orchestration primaire, fail-open primaire, enveloppe canonique du verdict
- `observability/`
  - details d'execution, branches, erreurs, timings
- `validation/`
  - revision du verdict primaire et production de la sortie finale

## 4. Nature Exacte De `primary_verdict`

`primary_verdict` est l'enveloppe canonique unique du verdict primaire du noeud.

Il sert a:

- exposer le noyau doctrinal du tour dans un format unique
- transmettre un bloc provisoire lisible a la validation
- porter un minimum d'auditabilite sans devenir un log

Il ne sert pas a:

- recopier les inputs bruts
- remplacer `node_state`
- remplacer `chat_log_events`
- embarquer en V1 un bloc de `justifications`
- devenir une table d'audit hermeneutique complete

Regle structurante:

- en V1, `primary_verdict` reste la meme forme canonique en mode nominal et en fail-open primaire
- le fail-open degrade des valeurs dans cette forme; il n'introduit pas un second format concurrent
- en V1, les `justifications` restent hors `primary_verdict` pour conserver un payload compact et distinct de l'artefact argumentatif destine a la validation

## 5. Minimal Canonical Payload Shape

La forme canonique minimale retenue est:

```python
{
    "schema_version": "v1",
    "epistemic_regime": "...",
    "proof_regime": "...",
    "uncertainty_posture": "...",
    "judgment_posture": "...",
    "discursive_regime": "...",
    "resituation_level": "...",
    "time_reference_mode": "...",
    "source_priority": [...],
    "source_conflicts": [...],
    "pipeline_directives_provisional": ["..."],
    "audit": {
        "fail_open": False,
        "state_used": False,
        "degraded_fields": [],
    },
}
```

Regles minimales:

- `schema_version`
  - version de contrat du payload primaire
- `discursive_regime`, `resituation_level`, `time_reference_mode`
  - restent top-level en V1 pour eviter un second format concurrent, tout en formant ensemble le sous-bloc doctrinal `output_regime`
- `source_priority`
  - reste la hierarchie doctrinale compacte du Lot 6
- `source_conflicts`
  - est inclus dans le payload primaire minimal en V1
  - raison: c'est deja une sortie doctrinale compacte du noeud primaire, utile a la validation et a la relecture du verdict
- `justifications`
  - ne font pas partie du `primary_verdict` minimal en V1
  - raison: leur forme exacte releve du futur contrat de validation et les fusionner maintenant regonflerait un payload qui vient d'etre fixe comme compact
- `audit`
  - reste un bloc minimal de relecture du verdict
  - ne devient ni un journal technique, ni un snapshot complet du tour

Invariants minimaux:

- un seul format canonique
- aucune prose libre longue
- aucun dump des inputs
- aucune duplication integrale de `node_state`
- aucun champ d'observabilite detaille
- aucun bloc de `justifications` integre en V1

## 6. Minimal Status Of `pipeline_directives_provisional`

`pipeline_directives_provisional` est un bloc provisoire du noeud primaire.

Il:

- appartient au `primary_verdict`
- ne vaut pas `pipeline_directives_final`
- doit rester compact, stable et codable
- doit pouvoir etre revise par l'agent de validation

Forme minimale retenue en V1:

- une liste ordonnee de codes courts et stables

Discipline minimale:

- pas de blob textuel libre
- pas de detail UX final
- pas de fusion avec la validation
- pas de directives finales pretendument deja stabilisees
- pas de doublons dans la liste

## 7. Minimal Primary Fail-open Contract

Le fail-open primaire conserve la meme forme canonique de payload.

Il ne produit pas:

- un silence
- une reponse generique vide
- un faux verdict riche traite comme normal

Regles minimales:

1. tous les champs du `primary_verdict` restent presents
2. les valeurs degradees doivent rester dans les taxonomies deja fermees
3. `audit.fail_open = True`
4. `audit.degraded_fields` doit nommer les champs effectivement degrades
5. `pipeline_directives_provisional` doit contenir un code explicite de fallback, par exemple `fallback_primary_verdict`
6. le fail-open ne doit pas prendre la forme d'un verdict substantif normal

Contraintes minimales de surete:

- `judgment_posture` ne doit pas etre `answer` en fail-open primaire V1
- `discursive_regime` doit rester `meta` en fail-open primaire V1
- `source_priority` peut retomber sur l'ordre canonique par defaut
- `source_conflicts` peut retomber sur `[]` si aucun conflit n'a ete detecte proprement

Cette spec ne fige pas encore le tuple complet exact de fallback.
Elle fixe sa discipline minimale et sa forme canonique.

## 8. Minimal Auditability Fields

Les champs minimaux d'auditabilite retenus sont:

- `schema_version`
- `audit.fail_open`
- `audit.state_used`
- `audit.degraded_fields`

Definitions minimales:

- `schema_version`
  - permet d'identifier le contrat du payload lu
- `audit.fail_open`
  - dit si le payload provient d'un chemin degrade primaire
- `audit.state_used`
  - dit si `node_state` a ete mobilise pour stabiliser le verdict courant
- `audit.degraded_fields`
  - liste compacte des champs dont la valeur a ete degradee ou synthetisee par fallback

Regles fortes:

- ce bloc n'est pas un event log
- il ne porte ni timings, ni branches detaillees, ni erreurs longues
- il ne remplace pas une future table d'audit hermeneutique complete

## 9. Boundary With `node_state`

Separation minimale:

- `primary_verdict`
  - dit ce que le noeud decide sur ce tour
- `node_state`
  - retient ce qui sert a piloter le tour suivant

Regles minimales:

- `node_state` ne recopie pas integralement `primary_verdict`
- `primary_verdict` ne vaut pas store de continuite
- `audit.state_used` peut signaler une mobilisation du state sans dupliquer le contenu de `node_state`

## 10. Boundary With Observability

Le repo dispose deja de:

- `observability.chat_log_events`
- `app/observability/hermeneutic_node_logger.py`

Regles minimales:

- `primary_verdict` n'est pas un event log
- l'observabilite reste le lieu du detail d'execution
- l'auditabilite minimale du payload ne remplace pas `chat_log_events`
- `chat_log_events` ne vaut pas verdict primaire canonique

## 11. Link With Validation

Le validation agent recoit le `primary_verdict`.

Il doit ensuite:

- recevoir a cote un artefact frere de `justifications`
- le relire
- le reviser si necessaire
- transformer `pipeline_directives_provisional` vers `pipeline_directives_final`
- produire la sortie finale revisee, seule consommable par l'aval

Regles minimales:

- `primary_verdict` n'est pas encore la sortie finale
- `justifications` ne font pas partie du `primary_verdict` minimal en V1
- leur contrat exact reste a ouvrir au Lot 9
- `pipeline_directives_provisional` n'est pas directement aval-consommable
- cette spec n'ouvre pas encore la table de combinaison normative complete du Lot 9

## 12. Non-goals

Cette troisieme brique normative ne fixe pas encore:

- le runtime complet de `primary_node.py`
- le wiring complet du noeud primaire
- la persistance SQL detaillee
- le contrat exact des `justifications`
- une table d'audit hermeneutique complete
- la validation finale
- le branchement aval
- la shadow globale
