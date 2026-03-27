# Audit DB-only - Memoire metier Frida

Objet: confirmer que `traces`, `summaries`, `identities`, `identity_evidence`, `identity_conflicts` et `arbiter_decisions` vivent deja en base de donnees dans le code actif de `FridaDev`, sans dependance residuelle a `state/*`.

## Conclusion

Pour ces six familles de donnees, le runtime actif est deja `DB-only` en pratique.

La lecture, l'ecriture, la mise a jour et la restitution API passent par PostgreSQL, via `app/memory/memory_store.py` et les appels faits depuis `app/server.py` et `app/core/conv_store.py`.

Aucune lecture ni ecriture metier vers `state/*` n'a ete trouvee pour :

- `traces`
- `summaries`
- `identities`
- `identity_evidence`
- `identity_conflicts`
- `arbiter_decisions`

## Points verifies

### 1. Schema et persistance

Dans `app/memory/memory_store.py`, `init_db()` cree directement les tables suivantes :

- `traces`
- `summaries`
- `identities`
- `identity_evidence`
- `arbiter_decisions`
- `identity_conflicts`

Les index associes sont egalement crees en base, y compris les index vectoriels pour `traces` et `summaries`.

### 2. Traces

`save_new_traces()` :

- embedde les messages nouveaux ;
- insere dans `traces` ;
- ne lit ni n'ecrit de fichier `state/*`.

`retrieve()` :

- relit les traces depuis la table `traces` uniquement.

`get_summary_for_trace()` et `enrich_traces_with_summaries()` :

- relisent les resumes parents depuis `summaries` uniquement.

### 3. Resumes

`save_summary()` :

- persiste dans `summaries`.

`update_traces_summary_id()` :

- relie les `traces` aux resumes directement en SQL.

Dans `app/core/conv_store.py`, le resume actif est maintenant relu depuis `summaries`, plus depuis `conversation["summaries"]`.

### 4. Identites et evidence

`record_identity_evidence()` :

- insere dans `identity_evidence`.

`add_identity()` :

- lit et met a jour `identities`.

`get_identities()` :

- relit `identities` uniquement depuis SQL.

`get_recent_context_hints()` :

- relit les hints depuis `identity_evidence`.

### 5. Conflits

`detect_and_record_conflicts()` :

- lit `identities` ;
- cree les conflits dans `identity_conflicts` ;
- applique les changements de statut dans `identities`.

`_has_open_strong_conflict()` et `_conflict_already_open()` :

- ne consultent que la base.

### 6. Decisions d'arbitrage

`record_arbiter_decisions()` :

- insere dans `arbiter_decisions`.

`get_arbiter_decisions()` :

- relit `arbiter_decisions` uniquement depuis SQL.

Les KPIs hermeneutiques relisent eux aussi la base (`identity_evidence`, `identities`, `arbiter_decisions`).

### 7. Appels runtime verifies

Dans `app/server.py`, les flux actifs passent par les fonctions SQL suivantes :

- `memory_store.retrieve()`
- `memory_store.save_summary()`
- `memory_store.update_traces_summary_id()`
- `memory_store.get_identities()`
- `memory_store.get_recent_context_hints()`
- `memory_store.record_identity_evidence()`
- `memory_store.record_arbiter_decisions()`
- `memory_store.get_arbiter_decisions()`

Aucun de ces appels ne passe par `state/*`.

## Residus encore presents, mais hors perimetre de ce point

Les elements suivants existent encore en fichiers, volontairement ou par heritage, mais ne contredisent pas ce constat `DB-only` pour la memoire metier :

- `state/data/identity/llm_identity.txt`
- `state/data/identity/user_identity.txt`
- `state/logs/*.jsonl`
- les anciens helpers JSON de `app/core/conv_store.py`

Important :

- les fichiers `state/data/identity/*.txt` sont des prompts statiques d'identite ;
- ils ne sont pas le stockage SQL des `identities` metier ;
- les logs techniques restent en fichiers par choix de migration ;
- les helpers JSON restants dans `conv_store.py` concernent l'ancien stockage conversationnel, pas `traces`, `summaries`, `identities`, `identity_evidence`, `identity_conflicts` ou `arbiter_decisions`.

## Verdict

Pour le perimetre de ce sous-point, aucune dependance residuelle a `state/*` n'a ete identifiee dans le code actif.

Le prochain travail n'est donc plus de "sortir ces objets des fichiers", mais de definir leurs regles de retention, purge, anonymisation, export et suppression.
