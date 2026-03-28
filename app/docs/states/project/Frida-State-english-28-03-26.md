# Frida State — 2026-03-28 (English)

## Purpose
This document captures a readable repository state for `FridaDev` as of **March 28, 2026**.
It is intended as a baseline for subsequent audits.

Method:
- findings from real code and repository structure;
- explicit separation between findings, inferences, and recommendations;
- short, actionable priorities.

## 1. Executive summary
As of 2026-03-28, `FridaDev` is an operational application base with:
- a stable local Docker stack (`docker-compose.yml` + `stack.sh`);
- one Flask backend entrypoint (`app/server.py`) orchestrating chat, admin settings, hermeneutics, and observability;
- conversation and memory persistence in PostgreSQL (DB-first in nominal flow);
- centralized backend prompts split into `main_system.txt` and `main_hermeneutical.txt`;
- dedicated chat-turn observability (`app/observability/`) with metadata/read-delete-export routes and `/log` UI.

Structural changes since the 2026-03-23 state:
- chat pipeline split into `core/chat_session_flow.py`, `core/chat_memory_flow.py`, `core/chat_llm_flow.py`, with orchestration in `core/chat_service.py`;
- runtime-settings partial split (`runtime_settings_spec.py`, `runtime_settings_repo.py`, `runtime_settings_validation.py`, `runtime_secrets.py`) while keeping `runtime_settings.py` as the stable facade;
- admin frontend split into focused modules (`admin_api.js`, `admin_state.js`, `admin_section_*.js`, `admin_ui_common.js`), even though `admin.js` remains large;
- logs follow-ups stabilized (metadata selectors, scoped deletion, Markdown export, associated tests);
- chat time-grounding aligned between prompt and runtime (`NOW`, `TIMEZONE`, relative labels/silence markers, temporal guardrails).

Critical open points:
- residual monoliths (`server.py`, `conv_store.py`, `runtime_settings.py`, `admin.js`, `log.js`);
- hard-delete behavior in code remains more destructive than long-term documentary intent;
- admin security posture still depends on runtime flags (`FRIDA_ADMIN_TOKEN`, `FRIDA_ADMIN_LAN_ONLY`) rather than strict safe defaults.

## 2. Real repository scope
### 2.1 What is versioned
- backend/frontend application code (`app/`);
- static prompts (`app/prompts/`);
- operator scripts (`stack.sh`, `docker-compose.yml`, `app/run.sh`);
- tests (`app/tests/`);
- structured documentation (`app/docs/`).

### 2.2 What is not versioned
(from `.gitignore`)
- `app/.env` and local env variants;
- runtime state under `state/`;
- runtime artifacts under `app/conv/`, `app/data/`, and runtime log files;
- Python env/cache artifacts and OS/editor residue.

### 2.3 Practical consequence for a fresh clone
A fresh clone is not self-sufficient at runtime:
- a valid `.env` is required;
- reachable PostgreSQL runtime backend is required;
- local mounted runtime state (`state/`) must exist, including runtime identity files.

## 3. Stack and execution
### 3.1 Docker orchestration
`docker-compose.yml` currently defines:
- project `fridadev`;
- service `fridadev` / container `FridaDev`;
- image `fridadev-app:local` built from `app/Dockerfile`;
- published port `8093 -> 8089`;
- mounted volumes `state/conv`, `state/logs`, `state/data` into `/app/*`;
- HTTP healthcheck on `/`.

### 3.2 Operator script
`stack.sh` exposes `up`, `down`, `restart`, `logs`, `ps`, `config`, `health`.
`restart` performs `docker compose up -d --build`.

### 3.3 Runtime entrypoint
- canonical container entrypoint: `python server.py` (`app/Dockerfile`);
- `app/run.sh` is a local convenience wrapper (env + venv), not the canonical Docker entrypoint.

## 4. Current architecture
### 4.1 HTTP backend
`app/server.py` (1009 lines) is still the single HTTP entrypoint.
It contains:
- admin guard (`before_request`) with token/CIDR checks;
- public chat routes (`/api/chat`, `/api/conversations*`);
- admin settings routes (`/api/admin/settings*`);
- admin hermeneutics routes (`/api/admin/hermeneutics/*`);
- observability routes (`/api/admin/logs/chat*`, metadata, scoped delete, Markdown export);
- static routes (`/`, `/admin`, `/log`).

### 4.2 Core application layer
`app/core/` now separates:
- chat orchestration (`chat_service.py`);
- chat session/conversation resolution (`chat_session_flow.py`);
- memory/arbiter/identity pipeline (`chat_memory_flow.py`);
- LLM call path, including stream flow (`chat_llm_flow.py`);
- prompt assembly + temporal labels (`conv_store.py`);
- augmented system prompt + time reference block (`chat_prompt_context.py`).

### 4.3 Memory / identity / admin
- `app/memory/`: retrieval, summaries, arbiter, identity write path, arbiter audit, SQL persistence;
- `app/identity/identity.py`: hybrid identity block (static + dynamic);
- `app/admin/`: runtime settings, admin services, admin logs, runtime actions.

### 4.4 Application observability
- dedicated package `app/observability/` (renamed from conflicting historical package path);
- SQL storage for chat-turn events (`log_store.py`);
- per-stage event emission (`chat_turn_logger.py`);
- backend Markdown export per conversation/turn (`log_markdown_export.py`).

### 4.5 Prompts
Centralized static prompts:
- `main_system.txt`
- `main_hermeneutical.txt`
- `summary_system.txt`
- `arbiter.txt`
- `identity_extractor.txt`
- `web_reformulation.txt`

### 4.6 Web surface
- chat: `web/index.html` + `web/app.js`;
- admin settings: `web/admin.html` + `admin.js` and section modules;
- logs UI: `web/log.html` + `web/log/log.js`;
- shared admin visual language in `web/admin.css`.

### 4.7 Tests
- 46 `test_*.py` files under `app/tests/`;
- mixed state: legacy `phase*` naming + progressive migration into `tests/unit/*` and `tests/integration/*`;
- explicit coverage for logs/time-grounding lots (server, prompt loader, prompt context, frontend logs).

### 4.8 Documentation
- `app/docs/states/`: durable references/specs/project states;
- `app/docs/todo-todo/`: active workstreams;
- `app/docs/todo-done/`: completed workstream traces.

## 5. Status of major integrated workstreams (code-verified)
- DB-first conversation flow confirmed in normal runtime path (`conversations`, `conversation_messages`, summaries/traces in SQL);
- centralized backend prompts with explicit system/hermeneutical split;
- logs follow-ups stabilized:
  - paginated read,
  - metadata selectors conversation/turn,
  - scoped deletion by conversation/turn,
  - dedicated Markdown export backend,
  - dedicated logs UI;
- chat-time-grounding stabilized on the implemented scope:
  - single turn-level NOW source,
  - `[RÉFÉRENCE TEMPORELLE]` block with `NOW` and `TIMEZONE`,
  - relative labels and silence markers injected into prompt messages,
  - explicit temporal guardrails in hermeneutical prompt;
- runtime settings already partially decoupled into dedicated submodules with backward-compatible facade.

## 6. Remaining structural debt
Findings:
- `app/core/conv_store.py` (1312 lines) still combines conversation persistence, token windowing, temporal labels, summaries, memory context, and hard delete;
- `app/server.py` (1009 lines) remains a major cross-cutting coupling point;
- `app/admin/runtime_settings.py` (939 lines) remains a heavy facade despite internal split;
- frontend remains dense: `app/web/admin.js` (1073 lines), `app/web/log/log.js` (564 lines).

Potential side effects:
- higher regression cost for cross-layer changes;
- risk of cosmetic refactors (moving complexity without reducing coupling) if next steps are not responsibility-driven.

## 7. Verified contradictions and watchpoints
- admin security:
  - guard exists, but is runtime-configuration-dependent (`FRIDA_ADMIN_TOKEN`, `FRIDA_ADMIN_LAN_ONLY`),
  - permissive runtime setup leaves admin surface broadly reachable on local/LAN contexts;
- retention/deletion:
  - API conversation deletion is soft delete,
  - hard delete path still exists and remains destructive in `conv_store.delete_conversation`;
- DB-only transition:
  - active flow is DB-first,
  - filesystem compatibility traces remain (`ensure_conv_dir`, mounted `state/conv`).

## 8. Recommended priority order
1. Reduce `server.py` coupling by progressively externalizing route sub-surfaces without changing HTTP contracts.
2. Slim `conv_store.py` by responsibility (time labels, prompt assembly, conversation persistence, retention) with targeted non-regression tests.
3. Harden admin default security posture for shared deployments (explicit token requirement / startup guardrail).
4. Continue test taxonomy migration toward domain naming without breaking legacy discoverability patterns.
5. Align long-term retention/deletion documentary policy with effective hard-delete implementation.

## 9. Related references
- previous English state: `app/docs/states/project/Frida-State-english-23-03-26.md`
- same-date FR counterpart: `app/docs/states/project/Frida-State-french-28-03-26.md`
- time-grounding contract: `app/docs/states/specs/chat-time-grounding-contract.md`
- logs contract: `app/docs/states/specs/log-module-contract.md`
