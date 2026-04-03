# Frida State - 03/04/2026

## Objet du document
Ce document fixe un etat lisible du repository `FridaDev` au **3 avril 2026**.
Il devient la reference principale de l'etat projet courant, sans ecraser les etats dates du 23/03/2026 et du 28/03/2026.

Methode:
- constats tires du code, de la documentation vivante et du runtime local verifies le 2026-04-03;
- inferes signalees explicitement;
- recommandations courtes, sans rouvrir le Lot 9.

## 1. Resume executif
Au 03/04/2026, `FridaDev` est un runtime exploitable dont le pipeline hermeneutique complet est branche et observable.

Constats principaux:
- `docker compose ps` confirme un conteneur `FridaDev` sain sur `0.0.0.0:8093->8089`.
- `GET /api/admin/hermeneutics/dashboard` confirme `mode=enforced_all`, sans alertes, avec `parse_error_rate=0.0` et `fallback_rate=0.0` au moment de la verification.
- `/log` et `/hermeneutic-admin` repondent en `200 OK`.
- `app/core/chat_service.py` enchaine maintenant `stimmung_agent -> primary_node -> validation_agent -> injection [JUGEMENT HERMENEUTIQUE] -> LLM principal`.
- `app/core/chat_memory_flow.py` applique reellement l'enforcement memoire et identite lorsque le mode est `enforced_all`, avec des marqueurs observables `memory_mode_apply` et `identity_mode_apply`.
- `app/prompts/main_system.txt` recadre Frida comme interlocuteur de travail et de reflexion, non comme simple assistant d'execution.
- Les transports OpenRouter sont differencies par composant (`llm`, `arbiter`, `identity_extractor`, `resumer`, `stimmung_agent`, `validation_agent`) avec `HTTP-Referer` et `X-OpenRouter-Title` distincts.
- L'observabilite distingue les compteurs locaux `estimated_*` et la verite provider post-call `provider_*`.

Changements marquants depuis le state du 28/03/2026:
- le Lot 9 est ferme et sa roadmap sort des TODO actives;
- la cible hermeneutique n'est plus un horizon de rollout, mais un runtime reel actif;
- une surface `Hermeneutic admin` distincte de `/log` existe et reste exploitable;
- les sections admin `stimmung_agent_model` et `validation_agent_model` sont presentes et branchees;
- le bloc `[JUGEMENT HERMENEUTIQUE]` est desormais une projection aval active de `validated_output`.

## 2. Perimetre reel du depot
### 2.1 Ce que le depot versionne
- code applicatif backend/frontend (`app/`)
- prompts statiques (`app/prompts/`)
- scripts d'exploitation (`stack.sh`, `docker-compose.yml`, `app/run.sh`)
- tests (`app/tests/`)
- documentation structuree (`app/docs/`)

### 2.2 Ce que le depot ne versionne pas
- `app/.env` et variantes locales
- runtime state local `state/`
- artefacts runtime montes dans `state/conv`, `state/logs`, `state/data`
- environnements/caches Python et residus systeme/editeur

### 2.3 Consequence pratique sur clone neuf
Un clone neuf ne suffit pas seul pour executer la stack:
- un `.env` valide reste necessaire
- un backend PostgreSQL joignable reste necessaire
- le state local monte par Docker doit exister

## 3. Runtime verifie au 03/04/2026
### 3.1 Stack locale
- `docker compose ps` montre un conteneur `FridaDev` sain
- port publie: `8093 -> 8089`
- entree container canonique: `python server.py`

### 3.2 Mode hermeneutique reel
- le dashboard hermeneutique retourne `mode=enforced_all`
- `alerts=[]`
- `parse_error_rate=0.0`
- `fallback_rate=0.0`
- latences runtime presentes pour `retrieve`, `arbiter`, `identity_extractor`

### 3.3 Surfaces operateur actives
- `/log` retourne `200 OK`
- `/hermeneutic-admin` retourne `200 OK`
- `GET /api/admin/hermeneutics/dashboard` retourne des champs reels `mode`, `alerts`, `counters`, `rates`, `latency_ms`, `runtime_metrics`
- `GET /api/admin/settings/main-model` expose des `referer_*` et `title_*` distincts par composant OpenRouter

## 4. Architecture reelle actuelle
### 4.1 Backend HTTP
`app/server.py` reste l'entree Flask unique.
Il porte:
- routes chat publiques
- routes admin settings
- routes logs applicatifs
- routes admin hermeneutiques
- route backend-only de restart
- routes statiques `/`, `/admin`, `/log`, `/hermeneutic-admin`

### 4.2 Core applicatif et pipeline
`app/core/` distingue maintenant clairement:
- `chat_service.py`: orchestration globale du tour
- `chat_session_flow.py`: resolution session/conversation
- `chat_memory_flow.py`: retrieval, arbitrage, application de mode
- `chat_llm_flow.py`: appel LLM JSON/stream
- `chat_prompt_context.py`: systeme augmente, reference temporelle, injection web et bloc `[JUGEMENT HERMENEUTIQUE]`
- `llm_client.py`: transport OpenRouter et metadonnees provider

Le chemin runtime de haut niveau est:
- resolution de session
- grounding temporel
- retrieval memoire et arbitrage
- `stimmung_agent`
- `primary_node`
- `validation_agent`
- projection `[JUGEMENT HERMENEUTIQUE]`
- appel du modele principal
- persistence et logs

### 4.3 Admin et observabilite
- `app/admin/` porte runtime settings, services admin et dashboard hermeneutique
- `app/observability/` porte les evenements compacts par stage
- `/log` reste la lecture transverse des tours et des stages
- `/hermeneutic-admin` fournit une lecture plus detaillee du dispositif hermeneutique

### 4.4 Prompts
- `main_system.txt` pose une posture d'interlocuteur de travail et de reflexion
- `main_hermeneutical.txt` fixe l'ordre de priorite des briques runtime et la place du bloc `[JUGEMENT HERMENEUTIQUE]`

### 4.5 Tests
- `58` fichiers `test_*.py` sont presents sous `app/tests/`
- la couverture inclut les logs applicatifs, la surface hermeneutique, les transports OpenRouter et les flux `stimmung_agent` / `validation_agent`

## 5. Chantiers integres et verifies
- Lot 9 est ferme en documentation et en runtime
- le pipeline hermeneutique complet est actif et observable
- `memory_mode_apply` et `identity_mode_apply` rendent visibles les effets reels du mode `enforced_all`
- les tokens provider post-call OpenRouter sont captures en `provider_*`
- les compteurs locaux gardent une distinction explicite `estimated_*`
- les identites transport OpenRouter sont distinctes par composant apres le restart live
- le prompt principal a quitte la posture d'assistant d'execution au profit d'une posture d'interlocuteur de travail

## 6. Dette structurelle restante
Constats:
- `app/minimal_validation.py` reste volumineux (`1211` lignes)
- `app/server.py` reste un point de couplage transversal important (`1094` lignes)
- `app/admin/runtime_settings.py` reste une facade lourde (`1066` lignes)
- `app/web/admin.js` reste dense (`1367` lignes)
- `app/web/log/log.js` reste concentre (`564` lignes)
- `app/memory/memory_store.py` reste relativement dense (`583` lignes)

Point important:
- `app/core/conv_store.py` n'est plus le monolithe principal du repo; le blocage majeur s'est deplace vers les facades HTTP/runtime/frontend encore lourdes.

## 7. Priorites recommandees
1. Desepaissir progressivement `app/server.py` par sous-surfaces de routes, sans changer les contrats HTTP.
2. Continuer a reduire `app/admin/runtime_settings.py` en gardant les responsabilites explicites entre facade, repo, validation et secrets.
3. Poursuivre la modularisation utile de `app/web/admin.js` et `app/web/log/log.js`.
4. Garder le Lot 9 ferme; porter la suite sur `app/docs/todo-todo/memory/hermeneutical-add-todo.md` et `app/docs/todo-todo/product/Frida-installation-config.md`.

## 8. Documents de reference associes
- state precedent FR: `app/docs/states/project/Frida-State-french-28-03-26.md`
- equivalent EN meme date: `app/docs/states/project/Frida-State-english-03-04-26.md`
- audit canonique: `app/docs/todo-done/audits/fridadev_repo_audit.md`
- archive de cloture Lot 9: `app/docs/todo-done/refactors/hermeneutic-convergence-node-todo.md`
- operations rollout hermeneutique: `app/docs/states/operations/hermeneutic-full-rollout-preconditions.md`
