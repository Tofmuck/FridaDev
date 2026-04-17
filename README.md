# Frida

Current repository state as of Thursday, April 16, 2026.
Etat courant du repository au jeudi 16 avril 2026.

## English

Frida is a working AI runtime focused on dialogue, memory, hermeneutic judgment, and operator observability.
This README describes the current FridaDev repository, runtime pipeline, and operator surfaces first.

Primary current-state references:
- `app/docs/todo-done/audits/fridadev_repo_audit.md`
- `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`
- `app/docs/README.md`

Historical milestone documents:
- `app/docs/states/project/Frida-State-english-03-04-26.md`
- `app/docs/states/project/Frida-State-french-03-04-26.md`

### Response Pipeline
Detailed companion: `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`

```text
+----------------------------------+
| User message / optional voice    |
| /api/chat/transcribe if needed   |
+----------------------------------+
                |
                v
+----------------------------------+
| POST /api/chat                   |
| message, conversation_id,        |
| stream, web_search, input_mode   |
+----------------------------------+
                |
                v
+----------------------------------+
| Session / thread resolution      |
| + persist user turn              |
+----------------------------------+
                |
                v
+----------------------------------+
| Augmented system base            |
| system prompt + time grounding   |
| + identity block                 |
+----------------------------------+
                |
        +-------+--------+
        |                |
        v                v
+--------------------+  +----------------------+
| Memory prep        |  | Hermeneutic branch   |
| traces, summaries  |  | stimmung_agent       |
| context hints      |  | primary_node         |
|                    |  | validation_agent     |
+--------------------+  +----------------------+
        |                        |
        v                        |
+--------------------+           v
| Memory arbiter     |  +----------------------+
| prompt candidates  |  | Final context build  |
| identity relevance |  | inject [JUGEMENT     |
|                    |  | HERMENEUTIQUE]       |
+--------------------+  | + guards + web ctx   |
        \               +----------------------+
         \
          \____________________/
                   |
                   v
        +-------------------------+
        | Main LLM call           |
        +-------------------------+
                   |
                   v
        +-------------------------+
        | Output contract         |
        | plain text + buffering  |
        | + stream terminal       |
        +-------------------------+
                   |
                   v
        +-------------------------+
        | Done finalization       |
        | append assistant text   |
        | identity writes         |
        | + possible reactivate   |
        +-------------------------+
                   |
                   v
        +-------------------------+
        | Canonical persistence   |
        | save_conversation       |
        | done or interrupted     |
        +-------------------------+
               |            |
               v            v
+-----------------------+  +----------------------+
| Derived traces only   |  | Frontend render /    |
| save_new_traces()     |  | rehydration          |
| after canonical save  |  | bubble + terminal    |
+-----------------------+  | updated_at + errors  |
               \           +----------------------+
                \__________________/
                         |
                         v
              +----------------------+
              | Observability        |
              | chat_turn_logger     |
              | /log + node logger   |
              +----------------------+
```

### What the system does today
- The browser chat surface sends either a typed turn or an optional voice transcript into `POST /api/chat`; the server validates `input_mode`, resolves or creates the thread, and persists the user turn before the assistant reply is built.
- Prompt construction combines the main and hermeneutical system prompts, time grounding, the identity block, retrieved memory traces and summaries, recent context hints, memory arbitration, and the hermeneutic branch `stimmung_agent -> primary_node -> validation_agent` before injecting `[JUGEMENT HERMENEUTIQUE]`.
- The main LLM call runs under a plain-text output contract. In streaming mode, visible content is emitted with a single terminal control chunk, while buffering depends on whether the turn must stay plain text or may expose structure/code.
- In the `done` path, Frida first appends the full assistant text, records identity entries for the current mode, and may reactivate identities before `save_conversation(...)`; only `save_new_traces()` is explicitly deferred until after the canonical save. In the `error` path, Frida stores an interrupted marker without canonical partial text.
- The frontend renders and rehydrates the thread from persisted conversation state, including terminal timestamps and interruption taxonomy, while `chat_turn_logger`, `/log`, and the hermeneutic node logger expose the main observability path.

### What the repository contains
- Flask backend orchestration in `app/server.py`
- Core chat flows in `app/core/`
- Memory and identity pipeline in `app/memory/` and `app/identity/`
- Admin/runtime settings and hermeneutic services in `app/admin/`
- Observability modules in `app/observability/`
- Web UI in `app/web/`
- Tests in `app/tests/`
- Structured documentation in `app/docs/`

### Documentation anchors
- Canonical current-state repo audit: `app/docs/todo-done/audits/fridadev_repo_audit.md`
- Current runtime pipeline one-glance: `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`
- Historical EN state milestone (2026-04-03): `app/docs/states/project/Frida-State-english-03-04-26.md`
- Historical FR state milestone (2026-04-03): `app/docs/states/project/Frida-State-french-03-04-26.md`
- Installation/operations guide: `app/docs/states/operations/frida-installation-operations.md`
- Chat enunciation / identity / time-gap doctrine: `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- Streaming protocol source-of-truth: `app/docs/states/specs/streaming-protocol.md`
- Archived streaming hardening closure: `app/docs/todo-done/product/frida-response-streaming-todo.md`
- Active hermeneutic post-stabilization TODO: `app/docs/todo-todo/memory/hermeneutical-post-stabilization-todo.md`
- Archived hermeneutic implementation roadmap: `app/docs/todo-done/notes/hermeneutical-add-todo.md`
- Memory Admin surface contract: `app/docs/states/specs/memory-admin-surface-contract.md`
- Active installation roadmap: `app/docs/todo-todo/product/Frida-installation-config.md`
- Archived chat enunciation prompt-first closure note: `app/docs/todo-done/notes/chat-enunciation-gap-validation-todo.md`
- Closed Lot 9 archive: `app/docs/todo-done/refactors/hermeneutic-convergence-node-todo.md`

### Versioned vs runtime-local
Versioned:
- code, prompts, scripts, tests, docs
- static identity examples and provisioning note under `state/data/identity/`

Not versioned:
- `app/.env`
- runtime state under `state/conv` and `state/logs`
- local operator-provisioned identity files under `state/data/identity/*.txt`
- local caches, virtualenvs, OS/editor residue

Container mapping note:
- `/app/conv`, `/app/logs`, `/app/data` are container mount targets for those host `state/...` directories.

A fresh clone still needs a valid local `.env`, reachable runtime dependencies, and initialized local runtime state under `state/...`.

### Stack operations
```bash
./stack.sh up
./stack.sh ps
./stack.sh health
```

### Essential paths
- `docker-compose.yml`
- `stack.sh`
- `app/server.py`
- `app/minimal_validation.py`
- `app/docs/README.md`

### Website and contact
- website: [https://frida-ai.fr](https://frida-ai.fr)
- contact: [tofmuck@frida-ai.fr](mailto:tofmuck@frida-ai.fr)

### License
This repository is distributed under the **MIT License**. See [LICENSE](LICENSE).

---

## Francais

Frida est un runtime IA de travail centre sur le dialogue, la memoire, le jugement hermeneutique et l'observabilite operateur.
Ce README raconte d'abord le depot FridaDev courant, son pipeline runtime et ses surfaces operateur.

References principales pour l'etat courant:
- `app/docs/todo-done/audits/fridadev_repo_audit.md`
- `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`
- `app/docs/README.md`

Jalons historiques:
- `app/docs/states/project/Frida-State-french-03-04-26.md`
- `app/docs/states/project/Frida-State-english-03-04-26.md`

### Pipeline de reponse
Document compagnon detaille: `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`

```text
+----------------------------------+
| Message utilisateur / voix       |
| optionnelle si necessaire        |
| /api/chat/transcribe             |
+----------------------------------+
                |
                v
+----------------------------------+
| POST /api/chat                   |
| message, conversation_id,        |
| stream, web_search, input_mode   |
+----------------------------------+
                |
                v
+----------------------------------+
| Resolution session + thread      |
| + persistance du tour user       |
+----------------------------------+
                |
                v
+----------------------------------+
| Base systeme augmentee           |
| prompt systeme + grounding temps |
| + bloc identitaire               |
+----------------------------------+
                |
        +-------+--------+
        |                |
        v                v
+--------------------+  +----------------------+
| Preparation memoire|  | Branche hermeneutique|
| traces, summaries  |  | stimmung_agent       |
| context hints      |  | primary_node         |
|                    |  | validation_agent     |
+--------------------+  +----------------------+
        |                        |
        v                        |
+--------------------+           v
| Arbitrage memoire  |  +----------------------+
| candidats prompt   |  | Construction du      |
| pertinence identite|  | contexte final       |
|                    |  | inject [JUGEMENT     |
+--------------------+  | HERMENEUTIQUE]       |
        \               | + gardes + web ctx   |
         \              +----------------------+
          \____________________/
                   |
                   v
        +-------------------------+
        | Appel LLM principal     |
        +-------------------------+
                   |
                   v
        +-------------------------+
        | Contrat de sortie       |
        | texte brut + buffering  |
        | + terminal de stream    |
        +-------------------------+
                   |
                   v
        +--------------------------+
        | Finalisation du done     |
        | append assistant complet |
        | ecritures identitaires   |
        | + reactivation eventuelle|
        +--------------------------+
                   |
                   v
        +--------------------------+
        | Persistance canonique    |
        | save_conversation        |
        | done ou interruption     |
        +--------------------------+
               |             |
               v             v
+------------------------+  +----------------------+
| Traces derivees seules |  | Rendu frontend /     |
| save_new_traces()      |  | rehydratation        |
| apres sauvegarde canon.|  | bulle + terminal     |
+------------------------+  | updated_at + erreurs |
               \           +----------------------+
                \__________________/
                         |
                         v
              +----------------------+
              | Observabilite        |
              | chat_turn_logger     |
              | /log + node logger   |
              +----------------------+
```

### Ce que fait aujourd'hui le systeme
- La surface chat navigateur envoie soit un tour tape au clavier, soit une transcription vocale optionnelle vers `POST /api/chat`; le serveur valide `input_mode`, resolve ou cree le thread, puis persiste le tour user avant de fabriquer la reponse assistant.
- La construction du prompt combine le prompt systeme principal, le prompt hermeneutique, le grounding temporel, le bloc identitaire, les traces memoire recuperees et leurs summaries, les context hints, l'arbitrage memoire, puis la branche `stimmung_agent -> primary_node -> validation_agent` avant l'injection du bloc `[JUGEMENT HERMENEUTIQUE]`.
- L'appel au LLM principal passe sous contrat de sortie texte brut. En mode streaming, Frida emet le contenu visible puis un unique terminal de controle, avec buffering ou non selon que le tour doit rester strictement texte brut ou peut exposer structure/code.
- Dans le chemin `done`, Frida ajoute d'abord le texte assistant complet, enregistre les ecritures identitaires du mode courant, puis peut reactiver des identites avant `save_conversation(...)`; seul `save_new_traces()` est explicitement repousse apres la sauvegarde canonique. Dans le chemin `error`, Frida persiste un marqueur interrompu sans texte partiel canonique.
- Le frontend rerend et rehydrate le thread a partir de l'etat persiste, y compris `updated_at` terminal et taxonomie des interruptions, tandis que `chat_turn_logger`, `/log` et le node logger hermeneutique exposent l'observabilite principale.

### Ce que contient le depot
- Orchestration backend Flask dans `app/server.py`
- Flux chat centraux dans `app/core/`
- Pipeline memoire et identite dans `app/memory/` et `app/identity/`
- Services admin/runtime settings et hermeneutiques dans `app/admin/`
- Modules d'observabilite dans `app/observability/`
- UI web dans `app/web/`
- Tests dans `app/tests/`
- Documentation structuree dans `app/docs/`

### Ancres documentaires
- Audit canonique current-state du repo: `app/docs/todo-done/audits/fridadev_repo_audit.md`
- Cartographie one-glance du pipeline runtime courant: `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`
- Jalon historique FR (2026-04-03): `app/docs/states/project/Frida-State-french-03-04-26.md`
- Jalon historique EN (2026-04-03): `app/docs/states/project/Frida-State-english-03-04-26.md`
- Guide installation/exploitation: `app/docs/states/operations/frida-installation-operations.md`
- Doctrine produit voix / identite / gap du chat: `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- Spec source-of-truth du protocole streaming: `app/docs/states/specs/streaming-protocol.md`
- Archive de cloture du chantier streaming: `app/docs/todo-done/product/frida-response-streaming-todo.md`
- TODO hermeneutique actif de post-stabilisation: `app/docs/todo-todo/memory/hermeneutical-post-stabilization-todo.md`
- TODO actif de resserrage du contrat identitaire et de sa frontiere hors canon: `app/docs/todo-todo/memory/identity-new-contract-todo.md`
- Archive de la grande roadmap hermeneutique: `app/docs/todo-done/notes/hermeneutical-add-todo.md`
- Contrat de surface Memory Admin: `app/docs/states/specs/memory-admin-surface-contract.md`
- Roadmap installation active: `app/docs/todo-todo/product/Frida-installation-config.md`
- Note archivee de cloture prompt-first voix / identite / gap du chat: `app/docs/todo-done/notes/chat-enunciation-gap-validation-todo.md`
- Archive de cloture Lot 9: `app/docs/todo-done/refactors/hermeneutic-convergence-node-todo.md`

### Ce qui est versionne vs local runtime
Versionne:
- code, prompts, scripts, tests, docs
- exemples d'identite statique et note de provisionnement sous `state/data/identity/`

Non versionne:
- `app/.env`
- etat runtime sous `state/conv` et `state/logs`
- fichiers d'identite operateur locaux sous `state/data/identity/*.txt`
- caches locaux, virtualenvs et residus systeme/editeur

Repere conteneur:
- `/app/conv`, `/app/logs`, `/app/data` sont les cibles de montage conteneur des repertoires hote `state/...`.

Un clone neuf necessite toujours un `.env` local valide, des dependances runtime joignables et un state local initialise sous `state/...`.

### Exploitation de la stack
```bash
./stack.sh up
./stack.sh ps
./stack.sh health
```

### Chemins essentiels
- `docker-compose.yml`
- `stack.sh`
- `app/server.py`
- `app/minimal_validation.py`
- `app/docs/README.md`

### Site et contact
- site: [https://frida-ai.fr](https://frida-ai.fr)
- contact: [tofmuck@frida-ai.fr](mailto:tofmuck@frida-ai.fr)

### Licence
Ce depot est distribue sous licence **MIT**. Voir [LICENSE](LICENSE).
