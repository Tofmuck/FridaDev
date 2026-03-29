# Frida

## English

Frida is an independent AI R&D project.
This repository is a **working engineering state** of the Frida runtime and tooling.
Project state references are dated **March 28, 2026**, with operations/baseline docs updated on **March 29, 2026**.

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

### What Frida Does Today
- Receives a user message through `/api/chat` and resolves an existing conversation or creates a new one.
- Sets the turn generation present (`user_timestamp`) and appends the user turn with that timestamp.
- Optionally summarizes older unsummarized turns when thresholds are exceeded, stores the summary in DB, and links covered traces.
- Builds the augmented system message from backend prompts + identity block + canonical temporal reference (`[RÉFÉRENCE TEMPORELLE]`, `NOW`, `TIMEZONE`).
- Runs memory retrieval from embeddings, then applies hermeneutic arbitration depending runtime mode.
- Enriches selected memory traces with parent summaries and also fetches recent context hints.
- Rebuilds the prompt window from the current conversation with: active summary, context hints, memory-context summaries, memory traces, and recent turns.
- Anchors temporal reading to the same turn `NOW` (relative delta labels + silence markers between turns).
- Optionally reformulates/searches/crawls web sources and injects web context into the last user prompt.
- Calls the main LLM (JSON or stream), then persists the assistant turn, new traces, identity writes/evidence by mode, and structured admin/observability logs.

### What Frida Is Building
In progress (not fully implemented yet):
- Frida is building a decision layer between context assembly and final answer generation, so source arbitration is explicit instead of implicit.
- This layer is designed to ingest canonical inputs from: time, memory, web, identity, active summary, recent context, Stimmung, and the user request.
- A primary convergence node will produce a first verdict: how to answer, with what certainty level, with which source priority, and with what proof posture.
- That first verdict can lead to `answer`, `clarify`, or `suspend` when evidence is weak, ambiguous, or contradictory.
- A second-stage validation agent (revision judge) then re-reads the verdict before downstream use and can `confirm`, `challenge`, `clarify`, or `suspend`.
- Validation is sovereign on final acceptance, but not on criteria: criteria stay fixed by explicit doctrine contracts.
- Practical goal: better situated answers, clearer source hierarchy, stronger justification, fewer hallucinations, and explicit non-conclusion when needed.
- Target structure for this work is a clearer split between `inputs/`, `doctrine/`, `runtime/`, and `validation/`.

### What is versioned vs runtime-local
Versioned:
- code, prompts, scripts, tests, docs.

Not versioned:
- `app/.env`
- runtime state under `state/conv`, `state/logs`, `state/data` (host/operator view)
- local caches, venvs, and OS/editor residue.

Container mapping note:
- `/app/conv`, `/app/logs`, `/app/data` are internal container mount targets for those host `state/...` directories.

A fresh clone needs a valid local `.env`, reachable runtime dependencies, and initialized local runtime state under `state/...`.

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
Ce depot correspond a un **etat d'ingenierie vivant** du runtime et des outils Frida.
Les etats projet de reference sont dates du **28 mars 2026**, avec des docs operationnelles/baselines mises a jour au **29 mars 2026**.

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

### Ce que Frida fait aujourd'hui
- Recoit un message utilisateur via `/api/chat` et resout une conversation existante ou en cree une nouvelle.
- Fixe le present de generation du tour (`user_timestamp`) et ajoute le tour utilisateur avec ce timestamp.
- Peut resumer les anciens tours non resumes si les seuils sont depasses, persiste le resume en DB et rattache les traces couvertes.
- Construit le systeme augmente depuis les prompts backend + bloc identite + reference temporelle canonique (`[RÉFÉRENCE TEMPORELLE]`, `NOW`, `TIMEZONE`).
- Lance la recuperation memoire par embeddings puis l'arbitrage hermeneutique selon le mode runtime.
- Enrichit les traces memoire retenues avec leurs resumes parents et recupere aussi des indices contextuels recents.
- Reconstruit la fenetre de prompt depuis la conversation courante avec: resume actif, indices contextuels, contexte de souvenirs, traces memoire et tours recents.
- Relit la temporalite depuis le meme `NOW` de tour (labels relatifs Delta-T + marqueurs de silence entre tours).
- Peut reformuler/rechercher/crawler le web et injecter ce contexte dans le dernier message utilisateur.
- Appelle le LLM principal (JSON ou stream), puis persiste la reponse, les nouvelles traces, l'identite (ecriture ou evidence selon le mode) et les logs admin/observabilite.

### Ce que Frida est en train de construire
En cours (pas completement implemente):
- Frida construit une couche de decision entre l'assemblage du contexte et la generation finale, pour arbitrer les sources explicitement plutot que de les empiler.
- Cette couche est concue pour recevoir des entrees canoniques: temps, memoire, web, identite, resume actif, contexte recent, Stimmung et demande utilisateur.
- Un noeud primaire de convergence doit produire un premier verdict: comment repondre, avec quel niveau de certitude, avec quelle priorite de sources et avec quel regime de preuve.
- Ce premier verdict peut conduire a `answer`, `clarify` ou `suspend` quand les elements sont insuffisants, ambigus ou contradictoires.
- Un agent de validation en second niveau (juge de revision) relit ensuite ce verdict avant consommation aval et peut `confirm`, `challenge`, `clarify` ou `suspend`.
- La validation est souveraine sur l'acceptation finale, mais pas sur les criteres: les criteres restent fixes par des contrats doctrinaux explicites.
- Objectif pratique: mieux situer les reponses, mieux hierarchiser les sources, mieux justifier, moins halluciner et accepter explicitement de ne pas conclure quand il le faut.
- La cible de structuration est une separation plus nette entre `inputs/`, `doctrine/`, `runtime/` et `validation/`.

### Ce qui est versionne vs local runtime
Versionne:
- code, prompts, scripts, tests, docs.

Non versionne:
- `app/.env`
- etat runtime sous `state/conv`, `state/logs`, `state/data` (vue operateur cote hote)
- caches locaux, venvs et residus systeme/editeur.

Repere conteneur:
- `/app/conv`, `/app/logs`, `/app/data` sont les chemins internes montes depuis `state/...`.

Un clone neuf necessite un `.env` local valide, des dependances runtime accessibles et un state local initialise sous `state/...`.

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
