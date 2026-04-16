# Frida

## English

Frida is a working AI runtime focused on dialogue, memory, hermeneutic judgment, and operator observability.
This repository tracks the real engineering state of the system as of **April 3, 2026**.

Primary references for the current repository state:
- `app/docs/states/project/Frida-State-english-03-04-26.md`
- `app/docs/states/project/Frida-State-french-03-04-26.md`
- `app/docs/todo-done/audits/fridadev_repo_audit.md`
- `app/docs/README.md`

### What the system does today
- Flask runtime exposing `/`, `/admin`, `/log`, `/identity`, `/hermeneutic-admin`, `/memory-admin`, `/api/chat`, `/api/admin/settings/*`, `/api/admin/hermeneutics/*`, and the read-only Memory Admin route `GET /api/admin/memory/dashboard`.
- Verified local stack on `http://127.0.0.1:8093`, currently running with `HERMENEUTIC_MODE=enforced_all`.
- Chat flow wired as: session resolution -> time grounding -> memory retrieval/arbitration -> `stimmung_agent` -> `primary_node` -> `validation_agent` -> `[JUGEMENT HERMENEUTIQUE]` injection -> main LLM call -> persistence and logs.
- Operator observability keeping local `estimated_*` counters distinct from post-call OpenRouter `provider_*` truth.
- OpenRouter transport identity split by caller (`llm`, `arbiter`, `identity_extractor`, `resumer`, `stimmung_agent`, `validation_agent`) through dedicated `HTTP-Referer` and `X-OpenRouter-Title`.
- Main system prompt now framing Frida as a work/reflection interlocutor rather than a generic execution assistant.
- Main chat surface `/` remains plain-text; the main LLM is instructed to answer in strict plain text, without visible Markdown formatting unless code is explicitly requested.

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
- Current EN project state: `app/docs/states/project/Frida-State-english-03-04-26.md`
- Current FR project state: `app/docs/states/project/Frida-State-french-03-04-26.md`
- Canonical repo audit: `app/docs/todo-done/audits/fridadev_repo_audit.md`
- Installation/operations guide: `app/docs/states/operations/frida-installation-operations.md`
- Chat enunciation / identity / time-gap doctrine: `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- Streaming protocol source-of-truth: `app/docs/states/specs/streaming-protocol.md`
- Archived streaming hardening closure: `app/docs/todo-done/product/frida-response-streaming-todo.md`
- Active memory roadmap: `app/docs/todo-todo/memory/hermeneutical-add-todo.md`
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
Ce depot suit l'etat d'ingenierie reel du systeme au **3 avril 2026**.

References principales pour l'etat actuel du depot:
- `app/docs/states/project/Frida-State-french-03-04-26.md`
- `app/docs/states/project/Frida-State-english-03-04-26.md`
- `app/docs/todo-done/audits/fridadev_repo_audit.md`
- `app/docs/README.md`

### Ce que fait aujourd'hui le systeme
- Runtime Flask exposant `/`, `/admin`, `/log`, `/identity`, `/hermeneutic-admin`, `/memory-admin`, `/api/chat`, `/api/admin/settings/*`, `/api/admin/hermeneutics/*` et la route read-only `GET /api/admin/memory/dashboard`.
- Stack locale verifiee sur `http://127.0.0.1:8093`, actuellement en `HERMENEUTIC_MODE=enforced_all`.
- Pipeline chat branche ainsi: resolution de session -> grounding temporel -> retrieval/arbitrage memoire -> `stimmung_agent` -> `primary_node` -> `validation_agent` -> injection `[JUGEMENT HERMENEUTIQUE]` -> appel LLM principal -> persistance et logs.
- Observabilite operateur distinguant les compteurs locaux `estimated_*` et la verite OpenRouter post-call `provider_*`.
- Identite transport OpenRouter differenciee par composant (`llm`, `arbiter`, `identity_extractor`, `resumer`, `stimmung_agent`, `validation_agent`) via des `HTTP-Referer` et `X-OpenRouter-Title` dedies.
- Prompt systeme principal recadre comme interlocuteur de travail et de reflexion, et non comme simple assistant d'execution.
- La surface chat principale `/` reste en texte brut ; le LLM principal est desormais contraint a repondre en texte brut strict, sans Markdown visible sauf si du code est explicitement demande.

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
- Etat projet FR courant: `app/docs/states/project/Frida-State-french-03-04-26.md`
- Etat projet EN courant: `app/docs/states/project/Frida-State-english-03-04-26.md`
- Audit canonique du repo: `app/docs/todo-done/audits/fridadev_repo_audit.md`
- Guide installation/exploitation: `app/docs/states/operations/frida-installation-operations.md`
- Doctrine produit voix / identite / gap du chat: `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- Spec source-of-truth du protocole streaming: `app/docs/states/specs/streaming-protocol.md`
- Archive de cloture du chantier streaming: `app/docs/todo-done/product/frida-response-streaming-todo.md`
- Roadmap memoire active: `app/docs/todo-todo/memory/hermeneutical-add-todo.md`
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
