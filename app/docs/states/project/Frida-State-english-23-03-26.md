# Frida State — 23/03/2026 (English)

## Purpose of this document

This document establishes a **readable and structured state of the code** as of **March 23, 2026**.  
It is intended to be **rewritten regularly** as changes are made, while keeping the same logic:

- describe the repository’s real scope;
- make the current technical invariants visible;
- point out what is clean, what remains open, and what must be watched;
- serve as a comparison baseline for future audits.

This document does not replace the project’s conceptual documentation. It describes **the actual code and architecture state** of the `FridaDev` repository at this moment in time.

## 1. Executive summary

As of 03/23/2026, the `FridaDev` repository is an autonomous application base for **Frida**, organized around:

- a dedicated Docker stack;
- a single Flask application;
- a business-memory layer primarily backed by PostgreSQL + `pgvector`;
- a minimalist web interface;
- a hermeneutic layer built on traces, summaries, identities, and arbitration;
- an administration toolset and a minimal validation layer.

One central point has significantly progressed: **conversation business state is now DB-first, and in practice almost DB-only** for the normal flow.

Conversations, messages, summaries, traces, identities, evidences, conflicts, and arbiter decisions now live in the database. Static prompts, web assets, and technical logs remain in files, which is consistent with the current direction.

The repository is already usable, but it is not yet fully ready for a clean public first push without selection:

- default admin security remains too open for a shared repository;
- hard purge is still more destructive than the documentary policy now being targeted;
- bootstrapping a fresh clone still requires explicit runtime preparation for `state/data`.

## 2. Scope and conventions

### 2.1 Project identity

- **Repository / stack name**: `FridaDev`
- **AI name in the product**: `Frida`
- **Website**: <https://frida-ai.fr>
- **Contact**: <tofmuck@frida-ai.fr>

### 2.2 Documentation structure

The current documentation tree is the following:

- `app/docs/states/`: structured states, baselines, specs, and situation documents;
- `app/docs/todo-done/`: internal working documents for completed items;
- `app/docs/todo-todo/`: internal working documents for open items.

From this state onward:

- `todo-done/` and `todo-todo/` must be treated as **internal to the team**;
- they are excluded from the first push by default;
- `states/` becomes the place for recurring audits and durable reference documents.

## 3. Repository state

### 3.1 Root

At the root, the repository versions:

- `README.md`
- `docker-compose.yml`
- `stack.sh`
- `.gitignore`
- `app/`

### 3.2 What the repository actually versions

The repository currently versions:

- the Flask application code;
- the memory, identity, admin, and tooling modules;
- the static prompts;
- the web interface;
- the operational scripts;
- the configuration examples;
- the reference documents located in `app/docs/states/`.

### 3.3 What the repository does not version

The repository is not meant to version:

- `app/.env`
- `state/`
- `app/conv/`
- `app/logs/`
- `app/data/`
- backups, `.bak` files, temporary files, and macOS system files
- internal documents in `app/docs/todo-done/`
- internal documents in `app/docs/todo-todo/`

### 3.4 Practical consequence

The repository therefore describes **the code and the architecture**, but not a fully self-contained runtime.  
A fresh clone still requires:

- a real `app/.env`;
- runtime storage under `state/`;
- runtime identity files in `state/data/identity/`.

## 4. Stack and runtime

### 4.1 Docker / orchestration

`docker-compose.yml` defines a simple stack:

- Compose project: `fridadev`
- service: `fridadev`
- container: `FridaDev`
- local image: `fridadev-app:local`
- published port: `8093 -> 8089`

Mounted volumes:

- `./state/conv:/app/conv`
- `./state/logs:/app/logs`
- `./state/data:/app/data`

### 4.2 Operator script

`stack.sh` provides the commands:

- `up`
- `down`
- `restart`
- `logs`
- `ps`
- `config`
- `health`

The logic is simple and readable.  
The current `restart` is a `docker compose up -d --build`, which matches the present workflow on both frontend and backend.

### 4.3 Application health

The Docker healthcheck queries `/` through Python.  
The stack is therefore driven by a very simple signal: the interface must answer over HTTP on internal port `8089`.

## 5. Configuration and external dependencies

### 5.1 Central configuration

Application configuration is centralized in `app/config.py`.  
It currently contains the following parameter families:

- LLM provider (`OpenRouter`);
- web search (`SearXNG`);
- crawl (`Crawl4AI`);
- embedding service;
- PostgreSQL memory storage;
- summary settings;
- hermeneutic settings;
- admin security.

### 5.2 External dependencies currently assumed

The code assumes the presence of, or access to, the following services:

- `OpenRouter` for the main LLM, the arbiter, and the summarizer;
- `SearXNG` for web search;
- `Crawl4AI` for content extraction;
- an embedding service;
- PostgreSQL with the `pgvector` and `pgcrypto` extensions.

### 5.3 Positive point

Ticketmaster and weather have been removed from the active product.  
The external surface is therefore more coherent with Frida’s direction as a work and research tool.

### 5.4 Watchpoint

Infrastructure configuration is still **mostly driven by `.env`**.  
The future `Infrastructure` page is not implemented yet. As of today:

- providers are configured at runtime;
- they are not yet manageable from the admin interface;
- changes still require operator action.

## 6. HTTP surface and API

### 6.1 Public interface

Main routes:

- `POST /api/chat`
- `GET /api/conversations`
- `POST /api/conversations`
- `GET /api/conversations/<conversation_id>/messages`
- `PATCH /api/conversations/<conversation_id>`
- `DELETE /api/conversations/<conversation_id>`
- `GET /`
- `GET /admin`

### 6.2 Admin interface

Observed admin routes:

- `GET /api/admin/logs`
- `POST /api/admin/restart`
- `GET /api/admin/hermeneutics/identity-candidates`
- `GET /api/admin/hermeneutics/arbiter-decisions`
- `POST /api/admin/hermeneutics/identity/force-accept`
- `POST /api/admin/hermeneutics/identity/force-reject`
- `POST /api/admin/hermeneutics/identity/relabel`
- `GET /api/admin/hermeneutics/dashboard`
- `GET /api/admin/hermeneutics/corrections-export`

### 6.3 Current admin security policy

The admin guard does exist in `server.py`, but its activation still depends on:

- `FRIDA_ADMIN_LAN_ONLY`
- `FRIDA_ADMIN_TOKEN`

In the current config examples, the token is empty and LAN-only mode is disabled.  
Conclusion: **the code knows how to protect admin access, but the default configuration is not hardened yet**.

## 7. Conversations: persistence and lifecycle

### 7.1 Actual state

The active conversation flow is now stored in the database through two tables:

- `conversations`
- `conversation_messages`

Persisted messages notably include:

- `role`
- `content`
- `timestamp`
- `summarized_by`
- `embedded`
- `meta`

### 7.2 What structurally changed

JSON bootstrap at startup has been disabled.  
`save_conversation()`, `load_conversation()`, and `read_conversation()` are now aligned with PostgreSQL for the normal flow.

The `app/conv/` directory still exists in the code and in the stack for operational compatibility, but it is no longer the primary source of business state.

### 7.3 Logical deletion

Deletion exposed through the UI relies on `deleted_at`:

- a conversation can disappear from the frontend;
- it remains in the database;
- the standard catalog filters on `deleted_at IS NULL`.

This logic is coherent with the policy currently being targeted:

- disappearance from the UI;
- preservation of the raw material in the database;
- no silent destruction.

### 7.4 Hard purge

A hard-delete function still exists (`delete_conversation`), but it is more destructive than the most recent documentary policy:

- it purges the conversation;
- it also purges linked messages, traces, summaries, decisions, evidences, identities, and conflicts.

Conclusion: **the hard purge logic still exists as a technical tool**, but it is not yet aligned with the longer-term goal of consolidated memory.

## 8. Memory, summaries, and identity

### 8.1 Business tables

`memory_store.py` initializes the following tables:

- `traces`
- `summaries`
- `identities`
- `identity_evidence`
- `arbiter_decisions`
- `identity_conflicts`

Indexes are created for frequent access patterns, including those needed by `pgvector`.

### 8.2 Traces

Traces are stored in the database with embeddings.  
Memory retrieval relies on vector similarity, with a configurable `top_k`.

The `save_new_traces()` mechanism has been made idempotent:

- an already existing trace is not reinserted;
- the `embedded` flag is persisted on the message side;
- the system avoids duplicates after restarts.

### 8.3 Summaries

Conversation summaries are stored in SQL.  
The active summary is selected using timestamps (`start_ts`, `end_ts`) rather than a merely volatile state.

`build_prompt_messages()` reconstructs context from:

- the active summary;
- messages after the cutoff;
- memory traces;
- recent identity hints.

### 8.4 Identities

The identity layer combines:

- static identities in files;
- dynamic identities persisted in the database.

The identity block injected into the final prompt is therefore hybrid by design:

- static for reference files;
- dynamic for consolidated identity memory.

### 8.5 Conflicts and arbitration

The system has an explicit memory of identity tensions:

- `identity_evidence`
- `identity_conflicts`
- `arbiter_decisions`

This layer gives Frida a more interpretive working basis than a simple linear conversational chat.

## 9. Hermeneutics and arbitration

### 9.1 Current position

The hermeneutic architecture is clearly installed in the code:

- `off` mode
- `shadow` mode
- `enforced_identities` mode
- `enforced_all` mode

### 9.2 Visible invariants

Several invariants already visible in the code align with the project’s philosophy:

- partial separation between generation and validation;
- hierarchical ordering of traces;
- the possibility of filtering retained memory;
- uncertainty handling through the arbiter;
- extraction and consolidation of identities;
- manual correction possible through the admin interface.

### 9.3 Current limitation

The hermeneutic layer is present and serious, but it is still strongly tied to configuration thresholds and internal implementation choices.  
It is not yet exposed as a fully documented and end-to-end administrable system.

## 10. Admin, logs, and observability

### 10.1 Admin

The admin currently has two main functions:

- observe;
- intervene on the hermeneutic layer.

The admin restart no longer pilots an old external service: it triggers the runtime to exit, allowing Docker to restart the container.

### 10.2 Admin logs

Admin logs are written as JSONL, with:

- rotation;
- redaction of certain sensitive fields;
- migration from an old legacy path when needed.

The solution is simple, robust, and well adapted to the project’s current state.

### 10.3 Watchpoint

Legacy logger names were still present in several modules:

- `core/conv_store.py`
- `memory/memory_store.py`
- `memory/arbiter.py`
- `identity/identity.py`
- `tools/web_search.py`
- `admin/admin_logs.py`

This is not technically blocking, but it is a leftover from derivation that should be cleaned for a proper public repository.

## 11. Frontend

### 11.1 Current direction

The web interface has been simplified around a more sober and more adult design:

- branding reduced to `Frida` + logo;
- a lighter chat interface;
- a clear separation from admin.

### 11.2 Behaviors already in place

The current frontend already handles:

- conversation listing;
- rename;
- logical deletion;
- toggleable web search;
- redirection of the settings button to `admin.html`;
- message timestamp display;
- `Vous` / `Frida` bylines.

### 11.3 Watchpoint

The frontend is already coherent, but it remains a living worksite:

- conversational ergonomics are still evolving;
- the design system is not frozen yet;
- the UI does not yet reflect the full architectural ambition of the backend.

## 12. Validation and quality

### 12.1 Minimal validation

The `app/minimal_validation.py` script already checks several useful invariants:

- server import and boot;
- presence and structure of expected SQL tables;
- presence of required prompts/files;
- presence of UI assets;
- HTTP/API smoke tests;
- a guard against the resurrection of legacy JSON files.

### 12.2 Reading the quality state

This minimal validation layer is already a good safety net for continuing to move the product without falling back into the old hybrid behavior.

It is not yet an exhaustive test suite, but it is already enough to:

- verify the foundation;
- replay the most critical invariants;
- secure the next frontend and infrastructure workstreams.

## 13. Strong points as of 03/23/2026

- dedicated Docker separation and simple operations;
- business memory strongly re-centered on PostgreSQL;
- a conversation store now consistent with the DB-first strategy;
- identities, evidences, conflicts, and arbitration already present in the database;
- removal of parasitic integrations (weather, Ticketmaster);
- a hermeneutic admin already useful;
- minimal validation already operational;
- product identity clarified around `Frida`.

## 14. Known gaps and risks

### 14.1 Default admin security

The biggest immediate gap before publication remains default admin security:

- empty token in the examples;
- LAN-only access disabled by default;
- protection present in the code, but not hardened by default.

### 14.2 Bootstrapping a fresh clone

The repository is not yet completely plug-and-play:

- `state/` is ignored, which is normal;
- but `state/data/identity/*` is still required at runtime;
- a documented bootstrap or an initialization mechanism is still missing.

### 14.3 Hard purge not aligned

Hard deletion still exists according to a logic that is too destructive compared to the current memory doctrine.

### 14.4 Legacy names

Legacy logger namespace remnants remained in logger names and in some documentary leftovers.

### 14.5 Repository documentation

Documentation is now better structured, but `states/` still contains several historical documents that are not all homogeneous with one another.  
Progressive curation remains useful.

## 15. Recommendations for the next states

For each new `Frida-State-*` audit, the following should be checked explicitly:

- the effective admin security;
- the real degree of `DB-only`;
- coherence between documentary policy and purge logic;
- the status of the future `Infrastructure` page;
- the state of legacy loggers;
- the ability of a fresh clone to start cleanly;
- frontend quality after future iterations.

## 16. Conclusion

On March 23, 2026, `FridaDev` is no longer a mere derived clone: it is already a coherent software base for **Frida**, with:

- a clarified identity;
- structured memory;
- a real hermeneutic architecture;
- a frontend that has become usable again;
- documentation that is beginning to stabilize.

The worksite is not finished, but it is now **readable**.  
The next challenge is no longer to determine whether the system stands up at all: it is above all to **harden, clarify, and publish it cleanly** without losing the project’s philosophical and technical rigor.
