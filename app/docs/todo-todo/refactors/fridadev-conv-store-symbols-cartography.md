# FridaDev - conv_store symbols cartography

## 1) Objet
Cette cartographie est la memoire de travail explicite du refactor de `app/core/conv_store.py`.

Regle:
- elle est bloquante avant toute extraction;
- elle fixe la surface publique reelle, les appelants reels, et la facade de transition;
- elle evite un decoupage cosmetique ou une casse invisible de contrat.

## 2) Surface publique actuelle de `conv_store`

| Symbole | Type | Role actuel | Famille metier | Statut de transition prevu |
|---|---|---|---|---|
| `CONV_DIR` | constante module | chemin legacy JSON conversations | maintenance / compat legacy | reste facade |
| `ensure_conv_dir` | fonction publique | garantit dossier legacy `conv/` | maintenance / bootstrap | reste facade |
| `normalize_conversation_id` | fonction publique | validation UUID conversation | conversation store | reste facade |
| `new_conversation` | fonction publique | cree objet conversation initial | conversation store | reste facade |
| `conversation_path` | fonction publique | chemin JSON legacy d'une conversation | maintenance / compat legacy | reste facade |
| `load_conversation` | fonction publique | lecture conversation DB-first | conversation store | reste facade |
| `save_conversation` | fonction publique | ecriture conversation + catalogue + messages | conversation store | reste facade |
| `append_message` | fonction publique | ajout message en memoire avant persistance | conversation store | reste facade |
| `init_catalog_db` | fonction publique | init table/index conversations | maintenance / bootstrap DB | migre (facade conservee) |
| `init_messages_db` | fonction publique | init table/index conversation_messages | maintenance / bootstrap DB | migre (facade conservee) |
| `upsert_conversation_catalog` | fonction publique | upsert metadonnees catalogue conversation | conversation store | migre (facade conservee) |
| `sync_catalog_from_json_files` | fonction publique | sync legacy JSON -> conversations | maintenance / migration legacy | migre (facade conservee) |
| `sync_messages_from_json_files` | fonction publique | sync legacy JSON -> conversation_messages | maintenance / migration legacy | migre (facade conservee) |
| `get_storage_counts` | fonction publique | inventaire JSON vs DB | maintenance / inventaire | migre (facade conservee) |
| `list_conversations` | fonction publique | pagination catalogue | conversation store | reste facade |
| `get_conversation_summary` | fonction publique | lecture metadonnees conversation | conversation store | reste facade |
| `read_conversation` | fonction publique | lecture conversation pour API messages | conversation store | reste facade |
| `rename_conversation` | fonction publique | rename conversation | conversation store | reste facade |
| `soft_delete_conversation` | fonction publique | suppression logique conversation | conversation lifecycle | reste facade |
| `delta_t_label` | fonction publique | format relatif Delta-T | temporalite / prompt window | migre (facade conservee) |
| `build_prompt_messages` | fonction publique | reconstruction fenetre prompt + injections memoire/summary/hints | prompt window | reste facade |
| `delete_conversation` | fonction publique | purge forte conversation + tables associees | maintenance destructive | migre (facade conservee) |
| `_db_conn` | helper interne | connexion runtime DB | infra interne (test-coupled) | reste local |
| `_bootstrap_database_dsn` | helper interne | resolution DSN bootstrap DB | infra interne (test-coupled) | reste local |
| `_silence_label` | helper interne | marqueur silence entre tours | temporalite / prompt window | migre (facade/test-compat a confirmer) |

Notes:
- surface publique = fonctions non prefixees par `_` + constante `CONV_DIR` effectivement consommee.
- helpers internes externes (`_db_conn`, `_bootstrap_database_dsn`, `_silence_label`) sont couples aux tests et doivent etre traites explicitement.

## 3) Cartographie des appelants reels

| Appelant | Symboles `conv_store` utilises | Type d'appel | Compatibilite requise pendant transition |
|---|---|---|---|
| `app/server.py` (bootstrap/app init) | `ensure_conv_dir`, `init_catalog_db`, `init_messages_db`, `normalize_conversation_id` | runtime critique | oui (strict) |
| `app/server.py` (`_ConvStoreChatLogProxy`) | `load_conversation`, `new_conversation`, `build_prompt_messages`, `save_conversation` (+ `__getattr__` pour le reste) | runtime critique + observabilite | oui (strict) |
| `app/core/chat_session_flow.py` | `normalize_conversation_id`, `load_conversation`, `new_conversation`, `save_conversation`, `conversation_path` | runtime critique (entree session chat) | oui (strict) |
| `app/core/chat_service.py` | `append_message`, `save_conversation`, `build_prompt_messages` | runtime critique (pipeline chat) | oui (strict) |
| `app/core/chat_llm_flow.py` | `append_message`, `save_conversation` | runtime critique (sortie LLM) | oui (strict) |
| `app/core/conversations_service.py` | `list_conversations`, `new_conversation`, `save_conversation`, `get_conversation_summary`, `normalize_conversation_id`, `read_conversation`, `rename_conversation`, `soft_delete_conversation` | runtime critique (API conversations) | oui (strict) |
| `app/minimal_validation.py` | `CONV_DIR`, `ensure_conv_dir` | smoke/operations | oui |
| `app/tests/test_server_phase12.py` | `new_conversation`, `save_conversation`, `append_message`, `conversation_path`, `build_prompt_messages`, `init_*` | tests service/runtime | oui (strict, monkeypatch) |
| `app/tests/test_server_phase13.py` | `new_conversation`, `save_conversation`, `append_message`, `conversation_path`, `build_prompt_messages`, `list_conversations`, `normalize_conversation_id`, `read_conversation`, `get_conversation_summary`, `rename_conversation`, `soft_delete_conversation`, `init_*` | tests service/runtime | oui (strict, monkeypatch) |
| `app/tests/test_server_phase14.py` | `normalize_conversation_id`, `load_conversation`, `new_conversation`, `init_*` | tests service/runtime | oui (strict, monkeypatch) |
| `app/tests/unit/core/test_conv_store_time_labels.py` | `build_prompt_messages`, `delta_t_label`, `_silence_label` | tests unitaires temporalite | oui (sorties exactes) |
| `app/tests/test_conv_store_phase4_database.py` | `_db_conn`, `_bootstrap_database_dsn` | tests unitaires infra conv_store | oui (ou adaptation test explicite) |
| `app/tests/test_conv_store_json_sync_inventory_phase6.py` | `sync_catalog_from_json_files`, `sync_messages_from_json_files`, `get_storage_counts` (presence source) | tests inventaire structure | oui (presence/API) |

Point important:
- pas d'appel runtime direct observe pour `delete_conversation`; la route API conversations passe par `soft_delete_conversation`.

## 4) Regroupements metier reels

### A. Stockage conversation / catalogue / messages (`conversations_store.py`)
Symboles:
- `normalize_conversation_id`, `new_conversation`, `load_conversation`, `save_conversation`, `append_message`;
- `upsert_conversation_catalog`, `list_conversations`, `get_conversation_summary`, `read_conversation`, `rename_conversation`, `soft_delete_conversation`.

Pourquoi:
- meme responsabilite metier: etat conversationnel durable DB-first.

### B. Prompt window / reconstruction (`conversations_prompt_window.py`)
Symboles:
- `build_prompt_messages`, `delta_t_label`, `_silence_label`;
- helpers de composition prompt actuellement internes (`_get_active_summary`, `_make_*_message`, etc.).

Pourquoi:
- meme sortie metier: prompt final a envoyer au LLM, avec temporalite et memoire injectees.

### C. Maintenance / sync / delete fort (`conversations_maintenance.py`)
Symboles:
- `init_catalog_db`, `init_messages_db`;
- `sync_catalog_from_json_files`, `sync_messages_from_json_files`, `get_storage_counts`;
- `delete_conversation`, `ensure_conv_dir`, `conversation_path`, `CONV_DIR`.

Pourquoi:
- operations bootstrap/migration/destruction hors flux nominal chat.

### D. Infra interne non exposee (`conv_store.py` ou module infra dedie a confirmer)
Symboles:
- `_db_conn`, `_bootstrap_database_dsn` (+ wrappers runtime DB).

Pourquoi:
- usage interne technique; couplage tests present mais pas contrat metier public.

## 5) Facade cible de transition

Pendant tout le refactor:
- `app/core/conv_store.py` reste point d'entree unique importe par `server.py` et les tests;
- la signature des symboles publics existants reste stable;
- `conv_store.py` delegue progressivement vers les nouveaux fichiers;
- aucun appelant runtime ne doit changer d'import dans le premier passage.

Etat code (etape 1 realisee):
- facade de transition explicitement gelee dans `conv_store.py`;
- surface publique explicite via `__all__` alignee sur cette cartographie;
- sections metier explicites ajoutees sans extraction vers de nouveaux fichiers.

A ne pas casser en premier passage:
- contrats utilises par `chat_session_flow`, `chat_service`, `chat_llm_flow`, `conversations_service`;
- monkeypatching tests `self.server.conv_store.*`;
- sorties textuelles exactes de `delta_t_label` / `_silence_label`.

## 6) Risques de refactor
- Dependances circulaires probables entre store et prompt window si les helpers DB/summary ne sont pas clairement places.
- Zone tres sensible: `build_prompt_messages` (ordre des briques, budget token, labels temporels, silence).
- Zone sensible: dualite `soft_delete_conversation` (API) vs `delete_conversation` (purge forte).
- Couplage tests non trivial sur symboles internes (`_db_conn`, `_bootstrap_database_dsn`, `_silence_label`).
- `ConvStoreChatLogProxy` ajoute un contrat implicite d'observabilite autour de `build_prompt_messages` et `save_conversation`.

## 7) Ordre minimal sur
1. **Etape 0 (bloquante):** cartographie symboles/appelants/facade (ce document).
2. **Etape 1 (realisee):** figer la facade de transition (`conv_store.py` surface publique explicite, contrats stables).
3. **Etape 2:** extraire `conversations_prompt_window.py` (plus sensible comportementalement).
4. **Etape 3:** extraire `conversations_store.py` (coeur persistence).
5. **Etape 4:** extraire `conversations_maintenance.py` (legacy/sync/delete fort).
6. **Etape 5:** nettoyage final de facade + verification non-regression complete.

Regle:
- aucune extraction ne commence sans etape 0 validee.
