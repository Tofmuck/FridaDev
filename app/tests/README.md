# Tests Taxonomy (Phase 7 Target)

## Reference interpreter

For Python tests on this host/repo, use the project interpreter from the repo root:
- `./.venv/bin/python`
- absolute equivalent: `/home/tof/docker-stacks/fridadev/.venv/bin/python`

Do not use `/usr/bin/python3` to judge test state or missing dependencies.
If another script or doc points to a different venv/interpreter, signal that mismatch explicitly instead of guessing.

Repo-root examples:
- `./.venv/bin/python -m unittest app.tests.unit.chat.test_chat_session_flow`
- `./.venv/bin/python -m unittest app.tests.test_server_phase13 app.tests.test_server_phase14`

This directory is migrated progressively.
First migrated lot:
- `integration/frontend_chat/test_frontend_chat_contract.py`
- `integration/frontend_admin/test_frontend_admin_contract.py`
Second migrated lot:
- `unit/chat/test_chat_session_flow.py`
- `unit/chat/test_chat_prompt_context.py`
- `unit/chat/test_chat_memory_flow.py`
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
