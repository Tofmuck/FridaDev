# Log Module Contract (MVP Chat Turn)

## 1) Scope and goal
This contract defines the phase-0 baseline for application logs linked to the chat turn pipeline.
It is normative for implementation slices documented in `app/docs/todo-done/refactors/log-module-todo.md`.

Goal:
- provide usable observability for one chat turn,
- without turning logs into a business data source,
- and without dumping large raw payloads.
- keep local token heuristics explicitly labelled as estimates, distinct from provider truth.

## 2) Boundary: business memory vs application logs
Business memory (source of truth, unchanged by log deletion):
- conversations / messages
- traces
- summaries
- identities (legacy diagnostic history, not active canon)
- identity_evidence (legacy diagnostic history, not active canon)
- context hints
- arbiter decisions
- identity_conflicts (legacy diagnostic history, not active canon)

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
- `web_reformulation_prompt_prepared` uses `chat_web_reformulation`
- `web_search` can use `chat_web_reformulation` for the compact result of the web branch
- `summaries` can use `chat_summary_system` when summary generation is executed

## 6) MVP event list and minimum payload
The MVP event list is:
- `turn_start`
- `embedding`
- `identity_conflict_scan`
- `memory_retrieve`
- `summaries`
- `identities_read`
- `identity_write`
- `web_search`
- `web_reformulation_prompt_prepared`
- `context_build`
- `stimmung_prompt_prepared`
- `primary_node`
- `hermeneutic_node_insertion`
- `validation_prompt_prepared`
- `validation_agent`
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
  - `mode`, `provider`, `dimensions`, `source_kind`
  - stable initial `source_kind` values:
    - `query`
    - `trace_user`
    - `trace_assistant`
    - `summary`
    - `identity_conflict_current`
    - `identity_conflict_candidate`

- `identity_conflict_scan`
  - compact summary of one identity conflict pass
  - `candidate_count`, `same_content_skipped`, `open_conflict_skipped`
  - `similarity_comparisons`, `conflicts_detected`
  - `current_embedding_calls`, `candidate_embedding_calls`, `embedding_calls_total`
  - `current_embedding_reused`, `current_embedding_blocked`
  - goal: explain why a turn emitted several conflict-related embeddings without raw identity dumps

- `memory_retrieve`
  - `top_k_requested`, `top_k_returned`, `dense_candidates_count`, `lexical_candidates_count`, `summary_candidates_count`
  - `top_k_requested` is the trace-lane request; `top_k_returned` is the total returned to the pre-arbiter path, so it can exceed `top_k_requested` when `summary_candidates_count > 0`
  - if `status=error`: stable `error_code`, sanitized `error_class`, and `reason_code=retrieve_error`
  - a normal empty retrieval stays `status=ok` with `top_k_returned=0`; downstream no-memory branches may use `reason_code=no_data`

- `summaries`
  - `active_summary_present`, `summary_count_used`, `summary_usage`, `in_prompt`, `summary_generation_observed`
  - `active_summary_present` / `in_prompt` describe the final prompt effectivement construit, not only summary availability in storage
  - `summary_generation_observed` reports whether the current turn observed a `summary_generated` event before prompt preparation; `false` means "not observed on this turn", not "impossible"

- `identities_read`
  - `frida_count`, `user_count`, `selected_count`, `content_present`
  - `total_chars`, `max_chars`
  - optional selection cap metadata: `requested_limit`, `truncated`
  - side mapping is explicit: `frida` side includes assistant/LLM identity material, `user` side includes user identity material
  - forbidden for identity: `preview`, `keys`, raw excerpts, raw identity ids

Transition contexte dialogique 2026-08-20: `identity_write` decrit seulement
les evenements historiques de l'ancien pipeline diagnostique. Le caller actif
par tour est `dialogic_context_hint_extractor`; il n'emet pas d'`identity_write`
et ne possede aucune autorite Identity ou canonique.

- `identity_write`
  - `target_side` (mandatory): `frida` | `user`
  - one event is emitted per side; if both sides are written in one turn, emit two `identity_write` events
  - `persisted_count`, `evidence_count`, `observed_count`, `retained_count`
  - `write_mode`, `write_effect`
  - `content_present`, `observed_total_chars`, `observed_max_chars`
  - `actions_count` map with stable action keys:
    - `add`, `update`, `override`, `reject`, `defer`
  - historical `write_mode` values from the retired B6 seam:
    - `legacy_diagnostic`
    - `legacy_diagnostic_shadow`
    - `disabled`
  - goal: preserve visibility on historical events from the retired `persist_identity_entries` path without raw dump or false active-runtime presentation
  - forbidden for identity: `preview`, textual excerpts, fragment dumps

- `identity_periodic_agent`
  - transition 2026-05-25: this event describes the pre-refactor runtime seam; the target mutable writer observability is defined by `mutable-identity-judge-contract.md`
  - payload must include the terminal `reason_code` even when top-level `status = ok`
  - during Lot 1 corrected, valid legacy contracts are accepted only as a technical completion and emit `reason_code = legacy_writer_disabled`; the active seam must not write canonical mutables through score-first apply
  - oversized windows emit `reason_code = window_too_large` plus compact size fields, without raw text, provider call or canonical write
  - forbidden: raw propositions, raw buffer pairs, raw identity content, prompt excerpts

- `web_search`
  - dedicated event (not only a boolean in `turn_start`)
  - `enabled`, `query_present`, `query_chars`, `results_count`, `context_injected`, `truncated`
  - stable hashes of the query are intentionally absent; presence and length are the content-free proof
  - `query_preview` can remain as a backward-compatible key but must not carry raw query text in default logs
  - if skipped: `status=skipped` + `reason_code`

- `web_reformulation_prompt_prepared`
  - content-free proof of the secondary provider payload prepared by the web reformulation path before the provider call
  - must be distinguishable from the main LLM payload and from `stimmung_prompt_prepared` / `validation_prompt_prepared`
  - allowed fields: `payload_kind`, `provider_caller=web_reformulation`, secondary/main booleans, model/provider title, message counts, role counts, system/current-user presence, char counts, short hashes, sampling/timeouts
  - forbidden: raw prompt, raw messages, raw content, raw original user message, raw query, raw web context, search results, snippets or crawled material

- `context_build`
  - `estimated_context_tokens`, `prompt_soft_token_limit`, `prompt_soft_limit_exceeded`, `dialogue_messages_truncated`
  - `prompt_soft_limit_exceeded=true` means the complete prompt exceeded the observability soft limit; it is not a truncation proof
  - `dialogue_messages_truncated` must stay `false` unless a real dialogic-message cut occurred; a soft-limit overrun must not be reported as `truncated`

- `stimmung_prompt_prepared`
  - content-free proof of the secondary provider payload prepared by `stimmung_agent`
  - must be distinguishable from the main LLM payload and from `validation_prompt_prepared`
  - allowed fields: `payload_kind`, `provider_caller=stimmung_agent`, secondary/main booleans, model, effective sampling settings, `timeout_s`, message counts, role counts, prompt/user char counts, recent-window counts, attempt source, fail-open/reason flags
  - `stimmung_request` is a closed content-free block derived from the effective request: policy version, requested model/source, standard transport, effective output/timeout, sampling keys actually sent, provider routing with `allow_fallbacks=false` and `require_parameters=true`, and strict JSON Schema identity; historical events without it remain `unknown`
  - forbidden: raw prompt, raw messages, raw content, raw current user message, raw recent window, canonical input dumps

- `primary_node`
  - compact proof of the primary hermeneutic verdict status
  - allowed fields: upstream posture/regime labels, signal-family codes, conflict counts, `fail_open`, `state_used`, degraded-field counts
  - when `fail_open=true`, allowed cause fields are `fallback_used`, `fallback_source=primary_node`, `node_stage=primary_node`, stable `reason_code` and compact `error_class`
  - when runtime `node_state` persistence is attempted, allowed compact fields are `node_state_read_present`, `node_state_read_valid`, `node_state_read_reason_code`, `node_state_write_attempted`, `node_state_write_succeeded`, `node_state_write_changed`, `node_state_write_reason_code`, `node_state_schema_version`, and `node_state_sha256_12`
  - forbidden: exception message, stack trace, prompt, messages, identity, memory, traces, summaries, canonical input dumps

- `hermeneutic_node_insertion`
  - compact proof that the hermeneutic node entrypoint was reached, with a redacted input-shape summary
  - allowed fields: `insertion_point_reached`, mode, input-family presence flags, counts, lengths, statuses and compact reason/error codes for time, memory, summary, identity, recent context/window, user-turn signals, stimmung and web inputs
  - this stage does not describe the final `[JUGEMENT HERMENEUTIQUE]` block injected into the main prompt; that final block is observed through `prompt_prepared.hermeneutic_prompt_injection`
  - forbidden: raw `[JUGEMENT HERMENEUTIQUE]` block, raw validation rationale, prompt excerpts, canonical input dumps, raw messages, raw memory, raw identity or raw web content

- `validation_prompt_prepared`
  - content-free proof of the secondary provider payload prepared by `validation_agent`
  - must be distinguishable from the main LLM payload and from `stimmung_prompt_prepared`
  - allowed fields: `payload_kind`, `provider_caller=validation_agent`, secondary/main booleans, model, message counts, input-family presence flags, compact source-kind counts, char counts, sampling/timeouts when present
  - runtime `validation_canonical_inputs_v2` exposes the exact content-free transport truth: projection version and `current_v2` contract status, used chars, fixed budget, and a complete closed partition of included, no-data, redundant, optional, invalid, and budget-exceeded families; historical `validation_canonical_inputs_v1` remains readable as `historical_v1` without reclassifying its omissions
  - both versions expose `stimmung_delivery_status=full|absent`, bounded reason code, Validation attempt source and prepared status; an unknown version or an incoherent v2 partition is non-authoritative
  - `validation_request` is a closed content-free block built from the exact
    prepared provider request: policy version, requested model, primary/fallback
    source, standard transport, requested/effective effort, reasoning sent,
    `exclude`, effective output budget, effective presence of sampling keys,
    whether a provider-routing block was sent, fallback/parameter enforcement,
    and the effective `response_format.type`, schema name, `strict` and
    `additionalProperties` posture only when those blocks were actually
    present. Both active v2 arms require the strict
    `validation_agent_verdict_v1` schema; historical events without this block
    remain `unknown`. Model/provider observed come only from the matching
    provider event when available
  - `partial`, inconsistent counters, unknown family names, a raw-content flag set to true, or an unversioned `full` claim are invalid rather than normal display states
  - forbidden: raw prompt, raw messages, raw validation dialogue, raw canonical inputs, raw memory traces/summaries, raw identity content

- `validation_agent`
  - compact proof of the validation verdict retained by the runtime
  - allowed fields: final posture/regime labels, hard-guard codes, upstream follow/override flags, compact reason codes, fallback/fail-open flags, compact error classes
  - forbidden: raw arbiter rationale, raw validation dialogue, prompt excerpts, canonical input dumps

- `prompt_prepared`
  - `prompt_kind`, `messages_count`, `estimated_prompt_tokens`, `memory_items_used`
  - `memory_prompt_injection`:
    - compact redacted summary of what memory-related blocks really reached the final prompt
    - must separate the operator lanes `trace_memory`, `summary_context`, and `context_hints`
    - `injected` remains a backward-compatible global bool and must not be the only operator truth for durable RAG injection
    - allowed fields: booleans, counts, block presence/absence only
    - forbidden: raw memory content, raw context hints, raw prompt excerpts
  - `identity_prompt_injection`:
    - compact redacted fingerprint of the Identity block compiled into the main prompt
    - allowed fields: block presence, lengths, short hashes, subject/layer presence, `used_identity_ids_count`, `staging_included=false`, non-sensitive source/update metadata
    - forbidden: raw static identity, raw mutable identity, staging buffer content, raw prompt excerpts
  - `hermeneutic_prompt_injection`:
    - compact redacted fingerprint of the `[JUGEMENT HERMENEUTIQUE]` block compiled into the main prompt
    - must be computed from the same block string that is passed to prompt assembly, not from an approximate projection
    - allowed fields: `present`, `chars`, `fingerprint_present=false`, `fingerprint_included=false`, `prompt_block_hash_included=false`, final posture/regime labels, `epistemic_regime`, `directives_count`, `source`, `fallback`, compact `reason_code`
    - the injected block has no stable short hash, in accordance with the continuity payload contract
    - forbidden: raw hermeneutic block, raw directives, raw validation rationale, canonical inputs, raw prompt excerpts
  - `memory_retrieval`:
    - compact redacted status of retrieval availability for this turn
    - allowed fields: `status`, `reason_code`, `error_code`, `error_class`, `top_k_requested`, `top_k_returned`
    - forbidden: DSN, token, query text, raw traceback, raw memory content

- `llm_call`
  - `model`, `mode`, `timeout_s`, `response_chars`
  - every metric or dashboard derived from `llm_call` must group by compact `provider_caller`
  - `provider_caller=llm` is the only main-provider lane; secondary lanes currently expected in the full chat turn are `stimmung_agent`, `validation_agent`, and `web_reformulation`
  - legacy or missing `provider_caller` values must be classified explicitly as `unknown`, never merged into the main `llm` lane
  - optional provider truth fields when available from OpenRouter:
    - `provider_caller`, `provider_title`
    - `provider_generation_id`, `provider_model`
    - `provider_prompt_tokens`, `provider_completion_tokens`, `provider_total_tokens`

- `arbiter`
  - `raw_candidates`, `kept_candidates`, `mode`

- `persist_response`
  - `conversation_saved`, `messages_written`, `persist_phase`
  - stable `persist_phase` values:
    - `conversation_init`: conversation shell/catalog saved before the user message is appended
    - `user_turn`: user message preservation without a final assistant response
    - `summary`: save triggered after summary generation / summary markers
    - `assistant_final`: final assistant response save
    - `assistant_interrupted`: interrupted/partial assistant marker save
    - `unknown`: compatibility fallback for legacy or unclassified saves
  - goal: count final assistant saves without confusing them with user-turn preservation, summary saves or interrupted markers
  - `persist_response` describes the canonical conversation save only; derived writes such as memory traces or identity writes remain observed by their own stages/events
  - for `persist_phase=assistant_final`, derived memory traces, identity writes and identity reactivation must execute only after a successful canonical assistant save (`conversation_saved=true`)
  - JSON and streaming may keep different relative ordering between derived writes after that barrier; metrics must rely on the post-save barrier, not on a global order among trace and identity derivations
  - for `persist_phase=assistant_interrupted` or failed assistant persistence, final assistant-derived traces and identity writes must not be produced for the interrupted/unsaved assistant content
  - forbidden: raw conversation, raw messages, prompt excerpts

- `turn_end`
  - `total_duration_ms`, `final_status`

- `error`
  - `error_code`, `error_class`, `message_short`

- `branch_skipped`
  - `reason_code`, `reason_short`

## 7) Derived compact reads

These reads are not runtime events. They are content-free operator projections built from
`observability.chat_log_events`.

### `turn_observability_checklist`

Goal:
- classify one turn as `complete`, `degraded`, `partial`, or `legacy_incomplete`;
- expose a numeric completeness score for future dashboards;
- explain missing/degraded proof points without reading prompt, message, identity, memory, web query or provider payload content.

Source:
- existing events for one `(conversation_id, turn_id)`;
- no new runtime event is required for this read.

Minimum checklist groups:
- main funnel:
  - `turn_start`
  - `prompt_prepared`
  - `llm_call` where `provider_caller=llm`
  - `persist_response` where `persist_phase=assistant_final`
  - `turn_end`
- prompt fingerprints:
  - `identity_prompt_injection`
    - a present object is not enough: the checklist requires positive proof through `injected=true` or `identity_block_present=true`; otherwise the item is `degraded` with `reason_code=identity_block_absent`
  - `memory_prompt_injection`
  - `hermeneutic_prompt_injection`
- secondary providers when observed or expected:
  - `stimmung_prompt_prepared` / `stimmung_agent`
  - `validation_prompt_prepared` / `validation_agent`
  - `web_reformulation_prompt_prepared`
  - if a secondary provider is expected or called, the matching `*_prompt_prepared` proof is mandatory; a result event or `llm_call.provider_caller` alone is `degraded` with `reason_code=missing_secondary_provider_prepared`
  - when a Validation projection claim is present, its structural metadata is validated from `validation_prompt_prepared`; an invalid status such as `partial` degrades the Validation checklist item with the bounded validation error code
  - when a Validation request-policy claim is present, the same prepared
    event must satisfy the closed request policy; an incoherent effort, model,
    budget, sampling, routing or JSON Schema strict claim degrades the item;
    active v2 claims include content-free proof of `response_format`, schema
    name, `strict=true` and `additionalProperties=false`
- web:
  - `web_search` is `not_applicable` when web was not requested;
  - when web was requested, `ok`, `skipped` with `reason_code`, or `error` with compact cause must be represented without raw query/result content;
- node state:
  - compact `primary_node.node_state_*` read/write status when the hermeneutic node runs;
- status hygiene:
  - error stages and skipped stages without `reason_code`.

Allowed output fields:
- score, classification, item status, item `reason_code`, stage names, counts, booleans, compact node-state fields, web `read_state`, and provider caller classification.

Forbidden output fields:
- raw event payload copies;
- prompt, messages, content, identity text, memory traces/summaries, web query/result snippets, canonical inputs, DSN, credential tokens, exception messages or stack traces.

### `chat_turn_pipeline_read_model`

Goal:
- expose one compact operator row per `(conversation_id, turn_id)`;
- let `/log` or another admin surface render a cockpit table without parsing the raw timeline in the browser;
- consolidate existing event proofs rather than introduce a new storage layer or runtime event.

Source:
- existing `observability.chat_log_events`;
- `turn_observability_checklist` classification and score;
- `memory_chain_snapshot` when present, with a prompt fingerprint fallback for legacy turns;
- existing stage payload fingerprints for `prompt_prepared`, `llm_call`, `persist_response`, `primary_node`, `web_search` and secondary providers.

Current admin surface:
- `GET /api/admin/logs/chat/turns`;
- optional filters: `conversation_id`, `turn_id`, `ts_from`, `ts_to`;
- pagination: `limit` and `offset`;
- the read uses a bounded per-turn event window and must set explicit truncation flags when a turn exceeds that window.

Minimum item groups:
- identity of the row: `conversation_id`, `turn_id`, `first_ts`, `latest_ts`;
- global state: checklist `classification`, score and compact missing/degraded items;
- persistence: final assistant save present/saved/interrupted/missing;
- provider lanes:
  - main provider is only `llm_call.provider_caller=llm`;
  - secondary providers stay separated: `stimmung_agent`, `validation_agent`, `web_reformulation`;
  - the Validation lane projects `canonical_projection` only from a valid
    `validation_prompt_prepared`: authority marker, version/contract status,
    `full|absent`, reason code, chars/budget and classified family dispositions;
    missing, unknown-version or incoherent proof becomes
    `authoritative=false` and `stimmung_delivery_status=unknown`, never `full`;
  - the same lane projects `request` only from a coherent
    `validation_prompt_prepared.validation_request`; it joins observed
    model/provider from the actual `llm_call` lane and never infers current
    Gemini settings for historical events; active v2 requests also project
    the strict response-format and schema flags, while incomplete or old
    active-policy claims remain non-authoritative;
  - legacy or missing provider callers are counted as `unknown`, never merged with the main lane;
- RAG: `retrieved -> basket -> kept -> injected`, sourced from `memory_chain_snapshot` when available;
- Identity: block presence, chars, short hash and selected-id count only;
- Hermeneutic: block presence, chars, short hash and compact `primary_node.node_state_*` read/write status;
- Web: requested/not requested, success/skipped/error, result count, injected flag/chars, query length/hash only;
- errors/fallbacks: counts by stage/status/reason code;
- source flags: `events_truncated`, `source_kind`, `legacy_reason_code` and `raw_event_payloads_included=false`.

Allowed output fields:
- counts, booleans, timestamps, durations, classifications, scores, stage names, provider callers, model/provider labels, compact status/reason/error codes, lengths, hashes, truncation flags and source metadata.

Forbidden output fields:
- raw event payload copies;
- prompt, messages, content, raw identity text, memory trace/summary text, web query/result snippets, canonical input dumps, DSN, tokens, exception messages or stack traces;
- any new dashboard-specific browser/UI telemetry.

### `full_turn_metrics_snapshot`

Goal:
- prepare future dashboard curves from already-clarified log signals;
- expose one compact aggregate read over a short log window;
- avoid a second observability layer, a new event stream, or a separate metrics store.

Source:
- existing `observability.chat_log_events`;
- `turn_observability_checklist` derived per turn;
- `llm_call` provider metrics grouped by `provider_caller`;
- `prompt_prepared`, `memory_chain_snapshot`, `primary_node`, `web_search`, status and reason-code fields.

Current admin surface:
- `GET /api/admin/logs/chat/metrics`;
- optional filters: `ts_from`, `ts_to`, `event_limit`;
- aggregates are computed from the events actually read for that snapshot; if `source.events_truncated=true`, the output is a bounded-window metric, not a whole-history metric;
- the read is backend-only preparation for dashboards; it does not prove frontend rendering quality.

`/log` compact visualizations:
- checklist distribution:
  - source: `checklist.classification_counts` and `turns_observed_count`;
  - window: the `/api/admin/logs/chat/metrics` event window, currently requested by `/log` with `event_limit=2000`;
  - semantics: share/counts of observed turns classified as `complete`, `degraded`, `partial` or `legacy_incomplete`;
  - truncation: if `source.events_truncated=true`, the UI must label the window as truncated and treat counts as bounded-window counts;
  - empty/degraded behavior: render an empty state when no turn is observed, never infer history completeness from zeros.
- provider lanes:
  - source: `llm_call_provider_metrics`;
  - window: same metrics event window;
  - semantics: LLM calls grouped by `provider_caller`, with main and secondary lanes kept separate;
  - truncation: same `source.events_truncated` handling;
  - empty/degraded behavior: zero calls render as an empty/provider-missing state, not as a runtime failure.
- RAG funnel:
  - source: `rag_funnel`;
  - window: same metrics event window;
  - semantics: candidate counters for `retrieved -> basket -> kept -> injected`, plus legacy prompt fallback counts as a degraded compatibility signal;
  - truncation: same `source.events_truncated` handling;
  - empty/degraded behavior: zero candidates render as no RAG signal in the window, not as proof that RAG is disabled.
- web flow:
  - source: `web`;
  - window: same metrics event window;
  - semantics: requested turns, successful web events, injected turns, skipped events and error events;
  - truncation: same `source.events_truncated` handling;
  - empty/degraded behavior: zero requested turns render as web not requested in the window.
- errors/skips/fallbacks:
  - source: `errors_by_stage`, `skipped_by_stage`, `fallback_fail_open.by_stage`;
  - window: same metrics event window;
  - semantics: top stage names with error, skip or fallback counts;
  - truncation: same `source.events_truncated` handling;
  - empty/degraded behavior: empty stage counts render as no anomaly in the window; unknown/free-form labels must be sanitized before rendering.

Signals intentionally not charted in `/log` until their aggregate source is explicit:
- latency p50/p95 by stage/provider;
- persistence assistant finale as a whole-window curve;
- embeddings health;
- any legacy ambiguous or content-derived label.

Minimum aggregate groups:
- checklist distribution:
  - `turns_observed_count`;
  - classification counts (`complete`, `degraded`, `partial`, `legacy_incomplete`);
  - score min/avg/max.
- LLM/provider:
  - nested `llm_call_provider_metrics`;
  - all curves derived from `llm_call` must stay segmented by `provider_caller`.
- fallback/fail-open:
  - total count;
  - counts by compact `reason_code`;
  - counts by stage.
- prompt lanes:
  - trace memory injected turns/counts;
  - summary/context injected turns/counts;
  - context hints injected turns/counts;
  - identity block present turns/chars;
  - hermeneutic block present turns/chars;
  - mixed-lane turns.
- RAG funnel:
  - retrieved candidates;
  - basketed candidates;
  - deduped retrieved candidates;
  - kept candidates;
  - injected candidates;
  - prompt fallback counts when a legacy turn lacks `memory_chain_snapshot`.
- node state:
  - read observed, hit, miss and invalid counts;
  - read hit and invalid rates;
  - write attempted, changed, unchanged, failed and skipped counts.
- web:
  - requested/not-requested turns;
  - ok/skipped/error counts;
  - injected turns and injected chars;
  - `read_state` counts.
- status hygiene:
  - errors by stage;
  - skipped stages by stage.

Allowed output fields:
- counts, booleans, rates, compact classifications, stage names, provider callers, reason codes, status counts, char totals and explicit truncation/source metadata.

Forbidden output fields:
- raw event payload copies;
- prompt, messages, content, identity text, memory traces/summaries, web query/result snippets, canonical inputs, DSN, tokens, exception messages or stack traces;
- frontend/UI telemetry, browser console errors, Playwright screenshots or rendered dashboard assertions.

## 8) Redaction policy (allowed vs forbidden)
Allowed by default:
- counters, booleans, durations, limits, truncated flags
- short previews and keys

Forbidden by default:
- full prompt dumps
- full context dumps
- full LLM request/response payload dumps
- full identity blocks/evidence dumps
- embedding vectors

Identity exception:
- `identities_read`, `identity_write`, `mutable_identity_judge`, `mutable_identity_judge_apply`, legacy `identity_periodic_agent`, legacy `identity_periodic_agent_apply`, and identity admin/runtime summaries such as `identity_mode_apply` must stay compact-only
- transition 2026-05-26: `mutable_identity_judge` / `mutable_identity_judge_apply` are the active mutable judge v2 add-only stages. `identity_periodic_agent` / `identity_periodic_agent_apply` are pre-refactor observability labels only and must not be presented as the active writer.
- legacy `identity_mutable_rewrite*` observability is retired in B6; the live regime is described through `identity_write`, `identity_mode_apply`, `mutable_identity_judge` and `mutable_identity_judge_apply`
- allowed for identity: counts, presence/absence, char lengths, update flags, reason codes, budget/shape validation flags
- `mutable_identity_judge` and `mutable_identity_judge_apply` may also expose compact staging/governance fields such as `runtime_pipeline`, `write_mode`, `buffer_pairs_count`, `buffer_target_pairs`, `buffer_frozen`, `buffer_cleared`, `auto_canonization_suspended`, `legacy_writer_disabled`, `score_first_writer_enabled=false`, `verdict_counts`, `continuity_kinds`, compact `rejection_reasons`, compact size guard fields (`window_chars`, `payload_chars`, `estimated_prompt_tokens`, `max_window_chars`, `max_estimated_prompt_tokens`), compact validation failure diagnostics (`validation_reason`, `invalid_verdict_index`, `invalid_subject`, `invalid_verdict`, `invalid_reason_code`, `invalid_proposition_chars`, `invalid_source_refs_count`, `invalid_guard_notes_count`) and compact apply counts; they must not expose scores or raw propositions
- active v2 events must not expose manager-operation fields such as `operation_kinds`, `persistent_operation_count`, `target_ref`, `target_refs`, `invalid_operation`, `invalid_target_ref` or `invalid_target_refs_count`; those names are legacy pre-Lot-B only
- the read-model projection of those events may expose `outcome_summaries` only as content-free subject/verdict/status/reason/count/length/hash summaries; it must not expose raw `outcomes`, propositions, prompts, messages or window text
- legacy `identity_periodic_agent` and `identity_periodic_agent_apply` may only remain as historical/pre-refactor events
- when present in legacy pre-Lot-B events, `raise_tension` remains a compact latest-activity signal only; it is not emitted by the active v2 add-only contract and must not be presented as a write into canonical `identity_mutables`
- when present in legacy events, `raise_conflict` remains a compact latest-activity signal only; it is allowed through compact `outcomes` summaries but must not be presented as a write into legacy `identity_conflicts`
- forbidden for identity: `preview`, `keys`, `guard_filtered_preview`, raw identity text, raw filtered excerpts

`preview` contract (all events):
- list of max 3 items
- each item max 120 chars
- single-line text only
- no sensitive raw payload

## 9) MVP deletion scope decision
MVP retained scope:
- `conversation_logs` (delete logs for one conversation)
- `turn_logs` (delete logs for one turn inside one conversation)

Deferred scopes (not in MVP phase):
- `all_logs`

Why:
- `conversation_logs` is the base operator scope with low ambiguity.
- `turn_logs` is retained for focused cleanup when a single turn must be removed.
- `all_logs` is intentionally not retained for MVP to avoid broad destructive action.

## 10) Non-regression rule
`delete logs` is never allowed to affect business-memory continuity.
After deleting logs:
- the log viewer remains empty for the deleted scope,
- logs reappear only from new runtime events,
- memory replay/reconstruction is forbidden.

## 11) UI contract baseline
Future logs UI must:
- reuse `app/web/admin.css` first,
- reuse existing admin component language (`admin-shell`, cards, chips, statuses, buttons),
- avoid a parallel visual system for MVP.
