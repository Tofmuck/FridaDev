# Hermeneutic Node State Persistence Contract

Statut: contrat runtime actif
Portee: persistance runtime compacte du `node_state` hermeneutique

Note runtime 2026-05-14:

- le `node_state` est persiste en PostgreSQL dans `hermeneutic_node_states`;
- le runtime chat relit cet etat par `conversation_id` avant `build_primary_node(existing_node_state=...)`;
- le runtime chat reecrit l'etat derive du verdict final valide par `validation_agent`, pas du verdict primaire pre-validation;
- l'observabilite reste compacte et ne journalise pas le contenu brut de l'etat.

## 1. Purpose

Elle tranche:

- la nature exacte de `node_state`
- sa frontiere avec le payload primaire, l'observabilite et les futurs snapshots d'audit
- son schema minimal de persistance
- ses regles minimales d'inertie
- son articulation avec `output_regime`
- sa compatibilite explicite avec la politique DB-only du repo
- son activation runtime dans le chat

Elle ne ferme ni le payload unique complet du noeud, ni l'auditabilite complete par tour.

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

Les cibles code sont:

- `app/core/hermeneutic_node/runtime/node_state.py`
- `app/memory/hermeneutic_node_state.py`
- `app/memory/memory_store_infra.py`
- `app/core/chat_service.py`
- `app/observability/hermeneutic_node_logger.py`

## 3. Doctrine / Runtime / Observability Boundary

`node_state` appartient au runtime du noeud hermeneutique.

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

`node_state` est un etat persistant de pilotage hermeneutique du noeud.

Il est:

- conversation-scoped
- durable
- borne
- oriente inertie minimale

Il sert a:

- fournir une continuite minimale d'un tour au suivant
- porter une inertie doctrinale simple et reversible
- eviter que la forme de sortie reparte de zero quand rien n'impose de rupture
- rester lu avant le noeud primaire, puis reecrit depuis le verdict final valide par le `validation_agent`

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
- `validated_output`
  - verdict final arbitral consomme par l'aval et source de mise a jour du state persistant
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
  - derniere posture finale validee
- `last_answer_output_regime`
  - dernier `output_regime` substantif reutilisable

Regle structurante:

- `last_answer_output_regime` ne conserve que le dernier regime substantif reutilisable
- il ne doit pas devenir un mini-historique
- il n'est mis a jour que lorsque `validated_output.final_judgment_posture = answer`

## 7. Minimal Inertia Rules

Les regles minimales d'inertie retenues sont:

1. conserver le dernier `last_answer_output_regime` seulement si rien, dans le tour courant, n'impose une rupture nette
2. casser immediatement l'inertie si un signal doctrinal nouveau fort apparait
3. ne jamais laisser un `clarify` ou un `suspend` precedent devenir une norme durable automatique
4. n'utiliser l'inertie que pour stabiliser la forme de sortie, pas pour ecraser un arbitrage nouveau

Lecture operationnelle minimale:

- `answer`
  - peut mettre a jour `last_answer_output_regime` quand le verdict final valide reste `answer`
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

La persistance de `node_state` est compatible avec la politique DB-only du repo.

Regles:

- pas de fichier de state comme source de verite;
- `node_state` est un state durable technique par conversation;
- la source de verite durable est PostgreSQL locale;
- le bootstrap est idempotent via `CREATE TABLE IF NOT EXISTS` et `CREATE INDEX IF NOT EXISTS`;
- la table ne contient pas de prompt, message, trace, summary, identite, canonical input ou contenu conversationnel brut.

Table runtime:

- `hermeneutic_node_states`

Colonnes:

- `conversation_id TEXT PRIMARY KEY`
- `schema_version TEXT NOT NULL DEFAULT 'v1'`
- `state_updated_at TIMESTAMPTZ NOT NULL`
- `last_judgment_posture TEXT NOT NULL`
- `last_answer_output_regime_json JSONB`
- `state_sha256_12 TEXT NOT NULL`
- `created_ts TIMESTAMPTZ DEFAULT now()`
- `updated_ts TIMESTAMPTZ DEFAULT now()`

Contraintes:

- `schema_version = 'v1'`
- `last_judgment_posture IN ('answer', 'clarify', 'suspend')`

Index:

- `hermeneutic_node_states_updated_ts_idx ON hermeneutic_node_states (updated_ts DESC)`

Semantique:

- une ligne represente l'etat courant d'une conversation;
- un nouvel etat remplace l'etat courant de la meme conversation;
- l'historique complet des etats n'est pas conserve dans cette table;
- l'audit par tour reste porte par `observability.chat_log_events`.

## 11. Link With Existing Observability

Le repo dispose deja de:

- `observability.chat_log_events`
- `hermeneutic_node_logger.py`

Regles minimales:

- `node_state` ne remplace pas cette observabilite
- l'observabilite ne devient pas la source metier de `node_state`
- `node_state` n'est pas le lieu du detail evenementiel par tour
- l'audit fin par tour reste distinct du state persistant
- l'event `primary_node` expose seulement une empreinte compacte de lecture/ecriture:
  - presence/validite de la lecture
  - reason code compact
  - tentative/succes/changement de l'ecriture
  - schema version
  - hash court de l'etat valide

## 12. Non-goals

Cette spec ne fixe pas:

- le payload unique complet du noeud
- les champs complets d'auditabilite
- une table de snapshots hermeneutiques complets
- une table d'historique complet du `node_state`
- un backfill des conversations historiques
- une source d'injection active distincte du jugement hermeneutique courant
