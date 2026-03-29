# Frida

## English

Frida is an independent AI R&D project.
This repository is a **working engineering state** of the Frida runtime and tooling as of **March 28, 2026**.

Primary references for this repository state:
- `app/docs/states/project/Frida-State-english-28-03-26.md`
- `app/docs/states/project/Frida-State-french-28-03-26.md`
- `app/docs/states/operations/frida-installation-operations.md` (installation/exploitation initial guide)

### Website and contact
- website: [https://frida-ai.fr](https://frida-ai.fr)
- contact: [tofmuck@frida-ai.fr](mailto:tofmuck@frida-ai.fr)

### What this repository contains
- Flask backend (`app/server.py`) with chat routes, admin settings routes, hermeneutics routes, and observability routes.
- Core chat flows split by responsibility under `app/core/`.
- Memory/identity pipeline under `app/memory/` and `app/identity/`.
- Runtime admin settings services under `app/admin/`.
- Dedicated observability package under `app/observability/`.
- Static prompts under `app/prompts/`.
- Web UI under `app/web/` (`/`, `/admin`, `/log`).
- Tests under `app/tests/`.
- Structured docs under `app/docs/`.

### What is versioned vs runtime-local
Versioned:
- code, prompts, scripts, tests, docs.

Not versioned:
- `app/.env`
- runtime state under `state/`
- runtime artifacts under `app/conv/` and `app/data/`
- local caches, venvs, and OS/editor residue.

A fresh clone needs a valid local `.env`, reachable runtime dependencies, and initialized local runtime state.

### Stack operations
```bash
./stack.sh up
./stack.sh ps
./stack.sh health
```

### Essential paths
- `docker-compose.yml`: local stack definition
- `stack.sh`: operator commands (`up`, `down`, `restart`, `logs`, `ps`, `config`, `health`)
- `app/server.py`: HTTP entrypoint/orchestration
- `app/minimal_validation.py`: global smoke validation layer
- `app/docs/README.md`: documentation map

### Documentation map
- `app/docs/states/`: durable reference docs (specs, baselines, project states, policies, operations)
- `app/docs/todo-todo/`: active workstreams
- `app/docs/todo-done/`: completed workstream traces

### License
This repository is distributed under the **MIT License**. See [LICENSE](LICENSE).

---

## Français

Frida est un projet indépendant de R&D en intelligence artificielle.
Ce depot correspond a un **etat d'ingenierie vivant** du runtime et des outils Frida au **28 mars 2026**.

References principales pour l'etat du depot:
- `app/docs/states/project/Frida-State-french-28-03-26.md`
- `app/docs/states/project/Frida-State-english-28-03-26.md`
- `app/docs/states/operations/frida-installation-operations.md` (guide d'installation/exploitation initiale)

### Site et contact
- site: [https://frida-ai.fr](https://frida-ai.fr)
- contact: [tofmuck@frida-ai.fr](mailto:tofmuck@frida-ai.fr)

### Ce que contient ce depot
- Backend Flask (`app/server.py`) avec routes chat, admin settings, hermeneutique et observabilite.
- Flux chat decoupes par responsabilite dans `app/core/`.
- Pipeline memoire/identite dans `app/memory/` et `app/identity/`.
- Services runtime settings admin dans `app/admin/`.
- Package d'observabilite dedie dans `app/observability/`.
- Prompts statiques dans `app/prompts/`.
- UI web dans `app/web/` (`/`, `/admin`, `/log`).
- Tests dans `app/tests/`.
- Documentation structuree dans `app/docs/`.

### Ce qui est versionne vs local runtime
Versionne:
- code, prompts, scripts, tests, docs.

Non versionne:
- `app/.env`
- etat runtime sous `state/`
- artefacts runtime sous `app/conv/` et `app/data/`
- caches locaux, venvs et residus systeme/editeur.

Un clone neuf necessite un `.env` local valide, des dependances runtime accessibles et un state local initialise.

### Exploitation de la stack
```bash
./stack.sh up
./stack.sh ps
./stack.sh health
```

### Chemins essentiels
- `docker-compose.yml`: definition de la stack locale
- `stack.sh`: commandes operateur (`up`, `down`, `restart`, `logs`, `ps`, `config`, `health`)
- `app/server.py`: point d'entree HTTP/orchestration
- `app/minimal_validation.py`: couche smoke globale
- `app/docs/README.md`: carte de la documentation

### Carte documentaire
- `app/docs/states/`: references stables (specs, baselines, etats projet, policies, operations)
- `app/docs/todo-todo/`: chantiers actifs
- `app/docs/todo-done/`: traces de chantiers termines

### Licence
Ce depot est distribue sous licence **MIT**. Voir [LICENSE](LICENSE).
