# Log Module Contract (MVP Chat Turn)

## 1) Scope and goal
This contract defines the phase-0 baseline for application logs linked to the chat turn pipeline.
It is normative for implementation slices documented in `app/docs/todo-done/refactors/log-module-todo.md`.

Goal:
- provide usable observability for one chat turn,
- without turning logs into a business data source,
- and without dumping large raw payloads.

## 2) Boundary: business memory vs application logs
Business memory (source of truth, unchanged by log deletion):
- conversations / messages
- traces
- summaries
- identities
- identity_evidence
- context hints
- arbiter decisions

Application logs (observability only):
- per-stage events,
- timing and counters,
- status (`ok|error|skipped`),
- concise diagnostics.

Hard rule:
- deleting logs must never delete or mutate business-memory tables/records.
- logs must not be rebuilt opportunistically from business memory after deletion.

## 3) Common event fields (mandatory)
Each log event must include:
- `event_id`: unique id for the log event
- `conversation_id`: conversation scope id
- `turn_id`: stable turn id inside the conversation
- `ts`: ISO-8601 UTC timestamp
- `stage`: event name
- `status`: `ok` | `error` | `skipped`

Optional cross-event fields (when relevant):
- `duration_ms`
- `model`
- `prompt_kind`
- `reason_code` (required for `status=skipped`)
- `error_code` (required for `status=error`)

## 4) `status=skipped` contract
When `status=skipped`, `reason_code` is mandatory.
Stable initial taxonomy:
- `feature_disabled`
- `mode_off`
- `no_input`
- `no_data`
- `not_applicable`
- `policy_blocked`
- `upstream_error`

Optional: `reason_short` (human-readable, short, no multiline dump).

## 5) `prompt_kind` initial taxonomy
`prompt_kind` is mandatory on prompt-related events only.
Initial values:
- `chat_system_main`
- `chat_system_hermeneutical`
- `chat_system_augmented`
- `chat_web_reformulation`
- `chat_summary_system`

Mapping guidance (MVP):
- `prompt_prepared` uses `chat_system_augmented`
- `web_search` can use `chat_web_reformulation` when reformulation is called
- `summaries` can use `chat_summary_system` when summary generation is executed

## 6) MVP event list and minimum payload
The MVP event list is:
- `turn_start`
- `embedding`
- `memory_retrieve`
- `summaries`
- `identities_read`
- `identity_write`
- `web_search`
- `context_build`
- `prompt_prepared`
- `llm_call`
- `arbiter`
- `persist_response`
- `turn_end`
- `error`
- `branch_skipped`

Minimum event-specific details:

- `turn_start`
  - `web_search_enabled`, `user_msg_chars`

- `embedding`
  - `mode`, `provider`, `dimensions`

- `memory_retrieve`
  - `top_k_requested`, `top_k_returned`

- `summaries`
  - `active_summary_present`, `summary_count_used`

- `identities_read`
  - `frida_count`, `user_count`, `selected_count`, `truncated`
  - `keys` (short identity keys), `preview` (short excerpts)
  - side mapping is explicit: `frida` side includes assistant/LLM identity material, `user` side includes user identity material

- `identity_write`
  - `target_side` (mandatory): `frida` | `user`
  - one event is emitted per side; if both sides are written in one turn, emit two `identity_write` events
  - `retained_count`
  - `actions_count` map with stable action keys:
    - `add`, `update`, `override`, `reject`, `defer`
  - `preview` (short retained items only), `truncated`
  - goal: visibility on what arbiter/identity policy effectively retained for write-path, without raw dump

- `web_search`
  - dedicated event (not only a boolean in `turn_start`)
  - `enabled`, `query_preview`, `results_count`, `context_injected`, `truncated`
  - if skipped: `status=skipped` + `reason_code`

- `context_build`
  - `context_tokens`, `token_limit`, `truncated`

- `prompt_prepared`
  - `prompt_kind`, `messages_count`, `estimated_prompt_tokens`, `memory_items_used`

- `llm_call`
  - `model`, `mode`, `timeout_s`, `response_chars`

- `arbiter`
  - `raw_candidates`, `kept_candidates`, `mode`

- `persist_response`
  - `conversation_saved`, `messages_written`

- `turn_end`
  - `total_duration_ms`, `final_status`

- `error`
  - `error_code`, `error_class`, `message_short`

- `branch_skipped`
  - `reason_code`, `reason_short`

## 7) Redaction policy (allowed vs forbidden)
Allowed by default:
- counters, booleans, durations, limits, truncated flags
- short previews and keys

Forbidden by default:
- full prompt dumps
- full context dumps
- full LLM request/response payload dumps
- full identity blocks/evidence dumps
- embedding vectors

`preview` contract (all events):
- list of max 3 items
- each item max 120 chars
- single-line text only
- no sensitive raw payload

## 8) MVP deletion scope decision
MVP retained scope:
- `conversation_logs` (delete logs for one conversation)
- `turn_logs` (delete logs for one turn inside one conversation)

Deferred scopes (not in MVP phase):
- `all_logs`

Why:
- `conversation_logs` is the base operator scope with low ambiguity.
- `turn_logs` is retained for focused cleanup when a single turn must be removed.
- `all_logs` is intentionally not retained for MVP to avoid broad destructive action.

## 9) Non-regression rule
`delete logs` is never allowed to affect business-memory continuity.
After deleting logs:
- the log viewer remains empty for the deleted scope,
- logs reappear only from new runtime events,
- memory replay/reconstruction is forbidden.

## 10) UI contract baseline
Future logs UI must:
- reuse `app/web/admin.css` first,
- reuse existing admin component language (`admin-shell`, cards, chips, statuses, buttons),
- avoid a parallel visual system for MVP.
