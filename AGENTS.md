# AGENTS.md

## Scope

These instructions apply to the whole `FridaDev` repository.

## Repository intent

`FridaDev` is a working repository, not a generic scaffold.
Agents must optimize for:

- explicit boundaries between modules and responsibilities
- readable structure over clever abstraction
- small, testable, reversible changes
- documentation that is easy to classify and retrieve quickly
- no false refactors that merely move complexity around

## Working method

- Work one minimal, closed, reversible step at a time.
- Do not implement multiple unrelated changes in the same patch.
- Do not perform opportunistic refactors outside the requested scope.
- Prefer small, testable increments over large rewrites.
- Do not silently reopen decisions already archived in `app/docs/todo-done/` unless the user explicitly asks to revisit them.
- When users paste `Review findings`, re-verify each finding against current repository state; mark already-fixed items as `stale` and do not re-apply them.
- After each completed step: validate, then commit, then push.

## Architecture discipline

The repository is expected to stay readable by responsibility:

- `app/server.py`: HTTP entrypoints and orchestration only
- `app/core/`: application flows and conversation services
- `app/admin/`: runtime settings, admin-side logic, admin support services
- `app/memory/`: memory pipeline, persistence, retrieval, arbitration, identity logic
- `app/web/`: browser-side UI and admin frontend code
- `app/docs/`: structured working documentation

Rules:

- Keep module boundaries explicit.
- Prefer extraction by real responsibility or pipeline stage, not by convenience.
- Do not create new god modules.
- Do not create vague dump files such as `utils.py`, `helpers.py`, or similar catch-all modules.
- A facade or orchestrator is acceptable only if it stays readable, bounded, and delegates clearly.
- If coupling cannot be removed yet, make it explicit and bounded rather than hiding it behind a cosmetic split.
- Do not rename or move files as a cosmetic gesture; every move must improve classification, readability, or dependency structure.

## Documentation placement rules

`app/docs/` is intentionally structured and its root must stay minimal.

- `app/docs/README.md` is the entrypoint.
- New documentation should not be dropped at the root of `app/docs/` unless the user explicitly asks for that.

Use these destinations:

- `app/docs/states/architecture/`: architecture notes, repository conventions, structural decisions
- `app/docs/states/specs/`: normative specs and schemas
- `app/docs/states/operations/`: operational guides and runbooks
- `app/docs/states/baselines/`: dated baselines and technical snapshots
- `app/docs/states/policies/`: governance, retention, and similar policies
- `app/docs/states/project/`: project state reference documents
- `app/docs/states/legacy/`: explicit legacy archives, not active references

- `app/docs/todo-done/audits/`: completed audits
- `app/docs/todo-done/validations/`: completed validation reports
- `app/docs/todo-done/refactors/`: completed refactor roadmaps and closure documents
- `app/docs/todo-done/migrations/`: archived migration roadmaps
- `app/docs/todo-done/notes/`: cleanup notes and supporting documentary traces

- `app/docs/todo-todo/memory/`: active memory / hermeneutics work items
- `app/docs/todo-todo/product/`: active product / installation / deployment work items
- `app/docs/todo-todo/admin/`: active admin-side work items
- `app/docs/todo-todo/migration/`: active migration work items

Practical rule:

- If a document describes a reference state, put it under `states/`.
- If a document proves completed work, put it under `todo-done/`.
- If a document drives unfinished work, put it under `todo-todo/`.

If asked to create a new TODO document, choose the correct `todo-todo/` subdirectory immediately and state that choice in `PLAN`.
If asked to create a new spec, policy, baseline, or operations note, place it directly under the corresponding `states/` subdirectory.
When moving docs, update live references in `AGENTS.md`, `README.md`, `app/docs/README.md`, and any still-active roadmap or closure document that points to them.

For entry/surface documents (repo root `README.md`, `app/docs/README.md`, and key operational entry guides), enforce higher readability: immediate clarity, compact structure, precise wording.
When FR/EN sections coexist in the same entry document, keep semantic parity and update both sections in the same patch.

## Database baseline discipline

- `app/docs/states/baselines/database-schema-baseline.md` is the repository snapshot reference for the physical DB schema.
- Any patch that adds/removes/renames/changes a durable DB table, column, index, schema, or relation must update `app/docs/states/baselines/database-schema-baseline.md` in the same patch.
- Do not leave durable DB schema changes implicit in Python/SQL sources only.

## Current authoritative documents

Use these documents as living anchors unless the user explicitly changes the strategy:

- `app/docs/todo-todo/memory/hermeneutical-add-todo.md`: active memory / hermeneutics roadmap
- `app/docs/todo-todo/product/Frida-installation-config.md`: active product / installation roadmap
- `app/docs/todo-done/refactors/admin-todo.md`: archived admin roadmap whose decisions must not be silently reopened
- `app/docs/todo-done/refactors/fridadev_refactor_closure.md`: closure record for the repository audit/refactor cycle
- `app/docs/todo-done/refactors/fridadev_refactor_todo.md`: completed refactor checklist kept as trace, not as an active roadmap

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

After a commit, also report:

- commit hash
- explicit push status

## Testing and proof policy

- No code patch without executable verification.
- Every implementation phase must add or update the tests that correspond exactly to the change.
- Keep `app/minimal_validation.py` as the global smoke-check layer.
- Put new focused tests in `app/tests/`.
- Prefer simple, explicit backend or integration tests over heavy scaffolding.
- If a change affects routes, persistence, runtime config, memory flow, or admin behavior, add or update tests for that behavior.
- Run the relevant tests before commit.
- If tests fail, fix the failure before moving to the next step.
- On this host/repo, the reference Python interpreter for repo test execution is `/home/tof/docker-stacks/fridadev/.venv/bin/python`.
- Do not use `/usr/bin/python3` to judge repository test health or missing Python dependencies.
- If a script or document points to another environment or interpreter, flag the mismatch explicitly instead of improvising.

For docs-only patches, replace executable behavior tests with concrete proof checks such as:

- path inventory
- reference grep
- ignored-file status
- link/path consistency checks

## Repository conventions

- Keep commits small and meaningful.
- Use commit messages that describe the exact change.
- Do not modify unrelated files just because they are nearby.
- Preserve current application behavior unless the requested step explicitly changes it.
- Preserve documentation classification: active, completed, reference, and legacy must not be mixed casually.
- Do not leave temporary planning docs in active locations once their status becomes completed or archived.

## When uncertain

- First inspect the relevant files under `app/docs/states/`, `app/docs/todo-done/`, and `app/docs/todo-todo/` before inventing a direction.
- If a decision already exists in an archived roadmap or closure document, follow it unless the user explicitly reopens it.
- If the correct location for a new doc is obvious, place it there directly and state the choice in `PLAN`.
- If the location is genuinely ambiguous, state the ambiguity explicitly in `RISKS` instead of improvising silently.
- Do not create a large patch when a smaller validated patch is possible.
