# AGENTS.md

## Scope

These instructions apply to the whole `FridaDev` repository.

## Working method

- Work one minimal, closed, reversible step at a time.
- Do not implement multiple unrelated changes in the same patch.
- Do not reopen decisions already fixed in `app/docs/admin-todo.md`.
- Do not perform opportunistic refactors outside the requested scope.
- Prefer small, testable increments over large rewrites.
- After each completed step: validate, then commit, then push.

## Required response format

For every non-trivial task, respond and work using:

PLAN
PATCH
TEST
RISKS

Meaning:
- PLAN: exact scope, files touched, what is intentionally out of scope
- PATCH: minimal implementation only
- TEST: exact checks executed
- RISKS: side effects, edge cases, follow-up watch points

## Testing policy

- No code patch without executable verification.
- Every implementation phase must add or update the tests that correspond exactly to the change.
- Keep `app/minimal_validation.py` as the global smoke-check layer.
- Put new focused tests in `app/tests/`.
- Prefer simple, explicit backend/integration tests over heavy test scaffolding.
- If a change affects routes, persistence, or runtime config, add or update tests for that behavior.
- Run the relevant tests before commit.
- If tests fail, fix the failure before moving to the next step.

## Admin migration rules

For the admin migration tracked in `app/docs/admin-todo.md`:

- Treat `app/docs/admin-todo.md` as the authoritative roadmap.
- The roadmap covers the full chantier A -> Z.
- Execution must still happen one minimal tranche at a time.
- `admin-old.*` must be preserved when the roadmap says so.
- The new admin must be built from scratch in `admin.html` / `admin.js` when the relevant phase is reached.
- The admin V1 scope is limited to contingent deployment variables stored in DB and read by code from DB.
- Logs are a separate later chantier.
- `FRIDA_MEMORY_DB_DSN` remains part of the minimal external bootstrap until the roadmap phase that explicitly changes that.

## Repository conventions

- Put new tests in `app/tests/`.
- Keep commits small and meaningful.
- Use commit messages that describe the exact change.
- Do not modify unrelated files just because they are nearby.
- Preserve the current application behavior unless the requested step explicitly changes it.

## When uncertain

- Prefer asking whether a point is already decided in `app/docs/admin-todo.md` before inventing a new direction.
- If the roadmap already decides something, follow it.
- If a real technical ambiguity remains, state it explicitly in RISKS instead of silently improvising. - Do not create a large patch when a smaller validated patch is possible.
