# Tests Taxonomy (Phase 7 Target)

## OVH interpreter discipline

On OVH, do not assume that a historical repo venv still exists.

Reference rules:
- for runtime-coupled proofs, prefer container execution from `/opt/platform/fridadev-app`
- example: `docker exec platform-fridadev python tests/test_server_phase4.py`
- for repo unit tests outside the container, first discover a real project interpreter in the current environment; if none exists, report that absence instead of guessing
- do not use `/usr/bin/python3` as proof that the repo dependencies are installed and healthy

Example when a real project interpreter has been discovered explicitly:
- `<project-python> -m unittest app.tests.unit.chat.test_chat_session_flow`
- `<project-python> -m unittest app.tests.test_server_phase13 app.tests.test_server_chat_synthetic_logs_contract app.tests.test_server_chat_conversation_id_contract`

## Frontend browser smoke tests

The browser smoke harness lives in `integration/frontend_browser/`.

Setup on OVH:
- `npm install`
- `npx playwright install chromium`
- if Chromium cannot start because native libraries are missing: `npx playwright install-deps chromium`

Run:
- `npm run test:frontend-browser`
- equivalent direct command: `node --test app/tests/integration/frontend_browser/*.js`

What this proves:
- real Chromium loads `index.html`, `admin.html` and `log.html` from `app/web/`;
- chat stream nominal handles a `done` terminal, renders the assistant bubble, keeps the timestamp from the terminal and refreshes conversations;
- chat stream error without `updated_at` stays visibly interrupted, forces rehydration and does not turn partial content into an optimistic canonical assistant message;
- admin settings validate/save displays invalid checks and blocks the PATCH path when validation fails;
- logs filter/export sends the expected query parameters and downloads the scoped Markdown export.

The older Python frontend tests under `integration/frontend_chat/` and `integration/frontend_admin/` remain useful source and contract guards. They should not be treated as sufficient UX integration proof because they mostly inspect asset text and route contracts without a browser DOM/event loop.

This directory is migrated progressively.
First migrated lot:
- `integration/frontend_chat/test_frontend_chat_contract.py`
- `integration/frontend_admin/test_frontend_admin_contract.py`
Second migrated lot:
- `unit/chat/test_chat_session_flow.py`
- `unit/chat/test_chat_prompt_context.py`
- `unit/chat/test_chat_memory_flow_prepare_context_observability.py`
- `unit/chat/test_chat_memory_flow_prepare_context_contracts.py`
- `unit/chat/test_chat_memory_flow_identity_mode_pipeline.py`
- `unit/chat/test_chat_memory_flow_identity_content_guards.py`
- `unit/chat/test_chat_llm_flow.py`
Third migrated lot:
- `unit/runtime_settings/test_runtime_settings.py`
- `unit/runtime_settings/test_runtime_secrets.py`
- `unit/runtime_settings/test_runtime_settings_sql.py`
Fourth migrated lot:
- `unit/web_search/test_web_search_phase4.py`
- `unit/web_search/test_web_search_services_phase4.py`
- `unit/web_search/test_web_search_phase13.py`
Fifth migrated lot:
- `unit/memory/test_arbiter_phase4.py`
- `unit/memory/test_summarizer_phase4.py`
- `unit/memory/test_summarizer_phase13.py`

## Target levels

- `unit/`: isolated behavior of a module/function, no external side effects (network, real DB, filesystem writes outside temp fixtures).
- `integration/`: composition and contract checks between modules/adapters (HTTP routes, runtime settings composition, DB/bootstrap integration, frontend asset contract checks).
- `smoke/`: global health checks used to validate a full baseline quickly.

## Target domains

- `chat`
- `conversations`
- `admin_settings`
- `admin_hermeneutics`
- `runtime_settings`
- `memory`
- `identity`
- `web_search`
- `frontend_admin`
- `frontend_chat`
- `bootstrap_runtime`

## Naming target (progressive)

- file pattern: `test_<domain>_<behavior>.py`
- keep historical `phase*` files executable until migrated in later tranches

## Smoke global

- `app/minimal_validation.py` remains the explicit global smoke layer.
- folder `tests/smoke/` is a target location for future dedicated smoke tests, without replacing `minimal_validation.py`.

## Transition guardrails

- no big-bang moves
- migrate by small batches
- keep `python -m unittest discover -s tests -p 'test_*.py'` working during transition when run inside `app/` with the reference project interpreter
