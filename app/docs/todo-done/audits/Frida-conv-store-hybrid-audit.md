# Frida - Audit du stockage hybride dans conv_store

Objectif: cartographier precisement les chemins hybrides encore actifs entre JSON et PostgreSQL avant la migration "DB only".

## 1. Point d'ancrage fichier

`app/core/conv_store.py` declare encore:

- `CONV_DIR = Path(__file__).resolve().parent.parent / "conv"`
- `conversation_path(conversation_id) -> CONV_DIR / "<id>.json"`

Le repertoire `app/conv/` reste donc un stockage primaire actif pour les conversations.

## 2. Ecriture hybride actuelle

### `save_conversation()`

Le flux actuel est:

1. normalisation de `conversation["messages"]`
2. ecriture de la conversation en JSON dans `app/conv/<id>.json`
3. mise a jour du catalogue SQL via `upsert_conversation_catalog()`
4. mise a jour des messages SQL via `_upsert_conversation_messages()`

Conclusion:

- l'ecriture n'est pas "DB first";
- le JSON est ecrit avant la base;
- la conversation est dupliquee entre fichier et SQL.

## 3. Lecture hybride actuelle

### `load_conversation()`

Le flux actuel est:

1. lecture du catalogue SQL via `get_conversation_summary()`
2. lecture des messages SQL via `_load_messages_from_db()`
3. si la base repond suffisamment, reconstruction depuis SQL
4. sinon fallback vers `app/conv/<id>.json`
5. si le JSON est absent, creation d'une nouvelle conversation puis sauvegarde hybride
6. si le JSON est present, relecture du JSON puis resauvegarde hybride

Conclusion:

- la lecture est "DB first", mais pas "DB only";
- le JSON reste un fallback fonctionnel;
- une conversation absente ou incomplete en base peut encore etre restauree depuis un fichier.

### `read_conversation()`

Le flux actuel est semblable:

1. tentative de lecture via SQL
2. fallback JSON si necessaire
3. resauvegarde hybride de la conversation lue depuis le JSON

Conclusion:

- le JSON reste dans le chemin nominal de lecture;
- la simple lecture peut encore repropager le state fichier vers la base.

## 4. Suppression encore liee aux fichiers

### `delete_conversation()`

Le flux actuel supprime uniquement:

- `app/conv/<id>.json`

Il ne supprime pas a lui seul:

- l'entree `conversations`
- les lignes `conversation_messages`
- les donnees memoire liees

Conclusion:

- la suppression n'est pas pilotee par la base;
- elle reste historiquement centree sur le fichier JSON.

## 5. Bootstrap JSON au demarrage

### `server.py`

Au demarrage du runtime, `app/server.py` appelle encore:

- `conv_store.sync_catalog_from_json_files(max_files=5000)`
- `conv_store.sync_messages_from_json_files(max_files=5000, force=False)`

Ces deux appels rebalayent `app/conv/*.json` pour recharger la base.

Conclusion:

- le runtime n'est pas encore autonome par rapport aux JSON;
- un redemarrage peut reintroduire des donnees presentes en fichiers;
- la bascule "DB only" exige la suppression de ce bootstrap.

## 6. Resumes encore attaches a l'objet conversation

### `build_prompt_messages()`

Dans `conv_store.py`, la reconstruction du prompt s'appuie encore sur:

- `conversation["summaries"]`

Le resume actif est pris comme:

- le dernier element de `conversation["summaries"]`

Conclusion:

- le prompt ne relit pas encore les resumes depuis SQL;
- une partie du state memoire reste accrochee a l'objet conversation en memoire.

## 7. Marqueurs volatils relies aux resumes et embeddings

### `memory/summarizer.py`

Le resume:

- est ajoute a `conversation["summaries"]`
- marque les messages couverts avec `m["summarized_by"] = summary_id`

### `memory/memory_store.py`

L'insertion des traces:

- ne prend que les messages sans `embedded`
- enregistre `summary_id` depuis `m.get("summarized_by")`
- pose ensuite `m["embedded"] = True`

### Limite structurelle actuelle

Dans `conv_store.py`, `_normalize_messages_for_storage()` ne persiste que:

- `role`
- `content`
- `timestamp`
- `meta`

Il ne persiste pas:

- `summarized_by`
- `embedded`

Conclusion:

- une partie de la logique resume/embedding repose encore sur des marqueurs volatils en RAM;
- ces marqueurs ne sont pas durables dans le stockage conversationnel actuel;
- la migration "DB only" devra soit persister ces marqueurs, soit reconstruire autrement cet etat.

## 8. Resume du chantier a mener

Pour atteindre un vrai fonctionnement "DB only", il faudra au minimum:

- retirer l'ecriture JSON primaire;
- retirer les fallbacks de lecture JSON;
- retirer le bootstrap JSON au demarrage;
- rendre la suppression pilotee par la base;
- sortir les resumes actifs de `conversation["summaries"]`;
- traiter durablement les marqueurs `summarized_by` et `embedded`.
