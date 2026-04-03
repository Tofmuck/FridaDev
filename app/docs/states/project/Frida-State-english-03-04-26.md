# Frida State - 2026-04-03 (English)

## Purpose
This document captures a readable repository state for `FridaDev` as of **April 3, 2026**.
It becomes the main current project-state reference without overwriting the dated states from 2026-03-23 and 2026-03-28.

Method:
- findings from code, living documentation, and local runtime verified on 2026-04-03
- explicit separation between findings and inferences
- short recommendations, without reopening Lot 9

## 1. Executive summary
As of 2026-04-03, `FridaDev` is an operational runtime with the full hermeneutic pipeline wired and observable.

Main findings:
- `docker compose ps` confirms a healthy `FridaDev` container on `0.0.0.0:8093->8089`.
- `GET /api/admin/hermeneutics/dashboard` confirms `mode=enforced_all`, no alerts, and `parse_error_rate=0.0` / `fallback_rate=0.0` at verification time.
- `/log` and `/hermeneutic-admin` both return `200 OK`.
- `app/core/chat_service.py` now chains `stimmung_agent -> primary_node -> validation_agent -> [JUGEMENT HERMENEUTIQUE] injection -> main LLM`.
- `app/core/chat_memory_flow.py` effectively enforces memory and identity when the mode is `enforced_all`, with observable `memory_mode_apply` and `identity_mode_apply` markers.
- `app/prompts/main_system.txt` now frames Frida as a work/reflection interlocutor rather than a generic execution assistant.
- OpenRouter transport identity is split by component (`llm`, `arbiter`, `identity_extractor`, `resumer`, `stimmung_agent`, `validation_agent`) with distinct `HTTP-Referer` and `X-OpenRouter-Title`.
- Observability keeps local `estimated_*` counters distinct from post-call provider truth in `provider_*`.

Notable changes since the 2026-03-28 state:
- Lot 9 is closed and its roadmap leaves the active TODO area
- the hermeneutic target is no longer only a rollout objective; it is a live runtime state
- a dedicated `Hermeneutic admin` surface now exists alongside `/log`
- admin sections `stimmung_agent_model` and `validation_agent_model` are present and wired
- `[JUGEMENT HERMENEUTIQUE]` is now an active downstream projection of `validated_output`

## 2. Real repository scope
### 2.1 What is versioned
- backend/frontend application code (`app/`)
- static prompts (`app/prompts/`)
- operator scripts (`stack.sh`, `docker-compose.yml`, `app/run.sh`)
- tests (`app/tests/`)
- structured documentation (`app/docs/`)

### 2.2 What is not versioned
- `app/.env` and local variants
- local runtime state under `state/`
- runtime artifacts mounted into `state/conv`, `state/logs`, `state/data`
- Python env/cache artifacts and OS/editor residue

### 2.3 Practical consequence for a fresh clone
A fresh clone is still not self-sufficient at runtime:
- a valid `.env` is required
- a reachable PostgreSQL backend is required
- Docker-mounted local runtime state must exist

## 3. Runtime verified on 2026-04-03
### 3.1 Local stack
- `docker compose ps` shows a healthy `FridaDev` container
- published port: `8093 -> 8089`
- canonical container entrypoint: `python server.py`

### 3.2 Effective hermeneutic mode
- the hermeneutic dashboard returns `mode=enforced_all`
- `alerts=[]`
- `parse_error_rate=0.0`
- `fallback_rate=0.0`
- runtime latencies are present for `retrieve`, `arbiter`, and `identity_extractor`

### 3.3 Live operator surfaces
- `/log` returns `200 OK`
- `/hermeneutic-admin` returns `200 OK`
- `GET /api/admin/hermeneutics/dashboard` returns real runtime fields: `mode`, `alerts`, `counters`, `rates`, `latency_ms`, `runtime_metrics`
- `GET /api/admin/settings/main-model` exposes distinct OpenRouter `referer_*` and `title_*` fields per component

## 4. Current architecture
### 4.1 HTTP backend
`app/server.py` remains the single Flask entrypoint.
It carries:
- public chat routes
- admin settings routes
- application logs routes
- admin hermeneutics routes
- backend-only restart route
- static routes `/`, `/admin`, `/log`, `/hermeneutic-admin`

### 4.2 Core application and pipeline
`app/core/` now separates:
- `chat_service.py`: turn orchestration
- `chat_session_flow.py`: session/conversation resolution
- `chat_memory_flow.py`: retrieval, arbitration, and mode application
- `chat_llm_flow.py`: JSON/stream LLM call path
- `chat_prompt_context.py`: augmented system, time reference, web injection, `[JUGEMENT HERMENEUTIQUE]`
- `llm_client.py`: OpenRouter transport and provider metadata

The high-level runtime path is now:
- session resolution
- time grounding
- memory retrieval and arbitration
- `stimmung_agent`
- `primary_node`
- `validation_agent`
- `[JUGEMENT HERMENEUTIQUE]` projection
- main-model call
- persistence and logs

### 4.3 Admin and observability
- `app/admin/` carries runtime settings, admin services, and hermeneutic dashboard logic
- `app/observability/` carries compact per-stage event emission
- `/log` remains the cross-cutting turn/stage observability surface
- `/hermeneutic-admin` provides a more detailed reading of the hermeneutic device

### 4.4 Prompts
- `main_system.txt` defines a work/reflection interlocutor posture
- `main_hermeneutical.txt` defines runtime brick priority and the place of `[JUGEMENT HERMENEUTIQUE]`

### 4.5 Tests
- `58` `test_*.py` files are present under `app/tests/`
- coverage includes application logs, hermeneutic surfaces, OpenRouter transport metadata, and `stimmung_agent` / `validation_agent` flows

## 5. Integrated and verified workstreams
- Lot 9 is closed both in documentation and in runtime reality
- the full hermeneutic pipeline is live and observable
- `memory_mode_apply` and `identity_mode_apply` expose the real effects of `enforced_all`
- post-call OpenRouter provider tokens are captured in `provider_*`
- local estimates remain explicitly separated in `estimated_*`
- OpenRouter transport identities are distinct per component after the live restart
- the main prompt has moved away from a pure execution-assistant posture toward a work/reflection interlocutor posture

## 6. Remaining structural debt
Findings:
- `app/minimal_validation.py` remains large (`1211` lines)
- `app/server.py` remains a significant cross-cutting surface (`1094` lines)
- `app/admin/runtime_settings.py` remains a heavy facade (`1066` lines)
- `app/web/admin.js` remains dense (`1367` lines)
- `app/web/log/log.js` remains concentrated (`564` lines)
- `app/memory/memory_store.py` remains moderately dense (`583` lines)

Important note:
- `app/core/conv_store.py` is no longer the repository's primary monolith; the main structural weight has moved to the remaining HTTP/runtime/frontend facades.

## 7. Recommended priorities
1. Keep slimming `app/server.py` through route sub-surfaces without changing HTTP contracts.
2. Continue reducing `app/admin/runtime_settings.py` while keeping explicit boundaries between facade, repo, validation, and secrets.
3. Continue useful modularization of `app/web/admin.js` and `app/web/log/log.js`.
4. Keep Lot 9 closed; carry the next steps through `app/docs/todo-todo/memory/hermeneutical-add-todo.md` and `app/docs/todo-todo/product/Frida-installation-config.md`.

## 8. Related references
- previous EN state: `app/docs/states/project/Frida-State-english-28-03-26.md`
- same-date FR counterpart: `app/docs/states/project/Frida-State-french-03-04-26.md`
- canonical audit: `app/docs/todo-done/audits/fridadev_repo_audit.md`
- closed Lot 9 archive: `app/docs/todo-done/refactors/hermeneutic-convergence-node-todo.md`
- hermeneutic rollout operations note: `app/docs/states/operations/hermeneutic-full-rollout-preconditions.md`
