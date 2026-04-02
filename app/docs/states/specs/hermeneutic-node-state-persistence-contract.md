# Hermeneutic Node State Persistence Contract

Statut: draft normatif ouvert
Portee: deuxieme pause normative du Lot 8 pour `state_persistence`

## 1. Purpose

Cette spec ouvre le second sous-pas normatif du Lot 8.

Elle tranche:

- la nature exacte de `node_state`
- sa frontiere avec le payload primaire, l'observabilite et les futurs snapshots d'audit
- son schema minimal de persistance
- ses regles minimales d'inertie
- son articulation avec `output_regime`
- sa compatibilite explicite avec la politique DB-only du repo

Elle ne code rien.
Elle ne ferme ni le payload unique complet du noeud, ni le fail-open primaire, ni l'auditabilite complete par tour.

## 2. Repo Grounding

Le repo a deja stabilise:

- `output_regime`
- `judgment_posture`
- `epistemic_regime`, `proof_regime`, `uncertainty_posture`
- `source_priority`
- `source_conflicts`

Le repo pose aussi deja:

- une politique DB-only pour le state metier
- une baseline du schema physique courant
- une observabilite existante via `observability.chat_log_events`

Notamment:

- `app/docs/states/specs/hermeneutic-node-output-regime-contract.md`
- `app/docs/states/policies/Frida-data-policy.md`
- `app/docs/states/baselines/database-schema-baseline.md`
- `app/observability/hermeneutic_node_logger.py`

La cible code de cette pause normative est:

- `app/core/hermeneutic_node/runtime/node_state.py`

Cette spec ne decide pas encore:

- la table SQL finale
- le schema physique final
- les migrations

## 3. Doctrine / Runtime / Observability Boundary

`node_state` appartient au runtime primaire du noeud.

Il ne se confond pas avec:

- `output_regime`
  - bloc doctrinal de sortie primaire
- le payload primaire complet
  - decision doctrinale du tour courant
- l'observabilite
  - evenements techniques, timings, branches, erreurs
- un futur snapshot d'audit hermeneutique
  - trace plus fine, potentiellement par tour

Frontiere minimale:

- `doctrine/`
  - ce que le noeud decide sur un tour
- `runtime/`
  - ce que le noeud retient d'un tour au suivant pour piloter son inertie
- `observability/`
  - ce que le systeme journalise pour lire son execution

## 4. Nature Exacte De `node_state`

`node_state` est un etat persistant de pilotage primaire du noeud.

Il est:

- conversation-scoped
- durable
- borne
- oriente inertie minimale

Il sert a:

- fournir une continuite minimale d'un tour au suivant
- porter une inertie doctrinale simple et reversible
- eviter que la forme de sortie reparte de zero quand rien n'impose de rupture

Il ne sert pas a:

- stocker tous les inputs
- conserver tout le payload primaire complet
- faire log technique
- faire audit exhaustif
- devenir un historique complet des verdicts

## 5. State / Payload / Observability Separation

Separation normative minimale:

- `node_state`
  - ce que le noeud retient pour piloter le tour suivant
- `primary verdict payload`
  - ce que le noeud decide sur ce tour
- `observability.chat_log_events`
  - evenements techniques du pipeline
- futur snapshot / audit hermeneutique
  - hors de cette tranche

Regle forte:

- une meme structure ne doit pas pretendre faire simultanement state, payload complet, event log et audit historique

## 6. Minimal Persistence Schema

Le schema minimal retenu est:

```python
{
    "schema_version": "v1",
    "conversation_id": "...",
    "updated_at": "...",
    "last_judgment_posture": "...",
    "last_answer_output_regime": {
        "discursive_regime": "...",
        "resituation_level": "...",
        "time_reference_mode": "...",
    },
}
```

Ce schema est retenu car il reste:

- conversation-scoped
- compact
- codable
- utile a l'inertie
- distinct du payload complet

Definitions minimales:

- `schema_version`
  - version du contrat de state
- `conversation_id`
  - portee conversationnelle unique
- `updated_at`
  - date de derniere mise a jour du state
- `last_judgment_posture`
  - derniere posture primaire observee
- `last_answer_output_regime`
  - dernier `output_regime` substantif reutilisable

Regle structurante:

- `last_answer_output_regime` ne conserve que le dernier regime substantif reutilisable
- il ne doit pas devenir un mini-historique

## 7. Minimal Inertia Rules

Les regles minimales d'inertie retenues sont:

1. conserver le dernier `last_answer_output_regime` seulement si rien, dans le tour courant, n'impose une rupture nette
2. casser immediatement l'inertie si un signal doctrinal nouveau fort apparait
3. ne jamais laisser un `clarify` ou un `suspend` precedent devenir une norme durable automatique
4. n'utiliser l'inertie que pour stabiliser la forme de sortie, pas pour ecraser un arbitrage nouveau

Lecture operationnelle minimale:

- `answer`
  - peut mettre a jour `last_answer_output_regime`
- `clarify`
  - met a jour `last_judgment_posture` mais ne remplace pas automatiquement `last_answer_output_regime`
- `suspend`
  - met a jour `last_judgment_posture` mais ne remplace pas automatiquement `last_answer_output_regime`

Discipline minimale:

- l'inertie est bornee
- l'inertie est reversible
- l'inertie ne doit pas fossiliser une mauvaise posture
- aucun compteur psychologique n'est requis dans cette V1

## 8. Link With `output_regime`

Le lien minimal avec `output_regime` est le suivant:

- `output_regime`
  - decide sur le tour courant la forme doctrinale de sortie
- `node_state`
  - retient seulement le dernier `output_regime` substantif utile a l'inertie

`node_state` ne doit donc pas:

- recopier tout le verdict primaire
- confondre le dernier `output_regime` avec tout le payload du tour
- reconstruire un historique riche des tours precedents

## 9. What Must Not Be Persisted Here

Ne doivent pas etre persistes dans `node_state`:

- les inputs bruts complets
- les textes bruts utilisateur
- les contenus bruts memoire, web, summary ou identity
- `source_conflicts` comme historique exhaustif
- les evenements d'observabilite
- le payload unique complet du noeud
- les justifications longues du verdict primaire

## 10. DB-only Compatibility

La cible de persistance de `node_state` est compatible avec la politique DB-only du repo.

Regles minimales:

- pas de fichier de state comme source de verite
- `node_state` doit etre pense comme state durable metier
- la source de verite durable cible reste PostgreSQL locale

Cette spec ne fixe pas encore:

- la table SQL finale
- les colonnes finales
- les indexes
- la migration physique

Constat de baseline:

- la baseline DB courante ne montre pas encore de table dediee a `node_state`
- cette spec n'implique donc aucune modification physique immediate

## 11. Link With Existing Observability

Le repo dispose deja de:

- `observability.chat_log_events`
- `hermeneutic_node_logger.py`

Regles minimales:

- `node_state` ne remplace pas cette observabilite
- l'observabilite ne devient pas la source metier de `node_state`
- `node_state` n'est pas le lieu du detail evenementiel par tour
- l'audit fin par tour reste distinct du state persistant

## 12. Non-goals

Cette pause normative ne fixe pas encore:

- le payload unique complet du noeud
- le fail-open primaire complet
- les champs complets d'auditabilite
- une table de snapshots hermeneutiques complets
- la table SQL finale de `node_state`
- les migrations SQL
- le wiring runtime de persistance
