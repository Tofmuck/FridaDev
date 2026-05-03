# FridaDev Current Runtime Pipeline

Statut: reference architecture active
Date de reference: jeudi 16 avril 2026 - 12:22 Europe/Paris
Classement: `app/docs/states/architecture/`
Portee: schema one-glance du pipeline runtime courant de `FridaDev`

## Objet / Purpose

- FR: ce document donne une cartographie compacte et exacte du pipeline chat/runtime courant, sans re-raconter tout le repo.
- EN: this document gives a compact and exact one-glance map of the current chat/runtime pipeline, without retelling the whole repository.

## Schema one-glance

```text
[Browser / index.html + app.js]
  |- optional voice draft -> /api/chat/transcribe -> whisper_transcription_service
  |- send POST /api/chat {message, conversation_id, stream=true, web_search, input_mode}
  v
[server.py / /api/chat]
  |- begin_turn + public chat entrypoint
  v
[chat_session_flow]
  |- validate message / conversation_id / input_mode
  |- create or reload thread
  v
[User turn persistence]
  |- append user message
  |- maybe_summarize()
  v
[Prompt base]
  |- backend system prompt
  |- hermeneutical prompt
  |- time grounding
  |- identity block
  v
[Memory branch / chat_memory_flow]
  |- retrieve_for_arbiter()
  |- enrich_traces_with_summaries()
  |- pre_arbiter_basket
  |- arbiter decisions (mode-dependent)
  |- selected prompt traces + context_hints
  v
[Hermeneutic branch]
  |- stimmung_agent
  |- primary_node
  |- validation_agent
  |- build [JUGEMENT HERMENEUTIQUE]
  v
[Prompt guards + optional web context]
  |- direct identity revelation guard
  |- voice transcription guard
  |- web reading guard
  |- plain-text output contract
  |- optional injected web context
  v
[Main LLM call / chat_llm_flow + llm_client]
  |- OpenRouter caller=llm
  |- json response OR text/plain streaming response
  v
[Streaming contract]
  |- assistant_output_contract decides buffering policy
  |- visible content chunks
  |- terminal control chunk = RS + JSON + LF
  |- event = done | error(error_code, updated_at only when persistence is proven)
  v
[Canonical persistence]
  |- save_conversation() returns catalog/messages proof
  |- done  -> full assistant message + verified save_conversation(updated_at)
  |- done  -> traces, identity writes and reactivation only after verified canonical save
  |- error -> assistant_turn interrupted marker only when the marker save is verified
  |- persist failure -> terminal error conversation_persist_failed without updated_at
  |- interrupted turns excluded from prompt window and traces
  v
[Frontend render + rehydration]
  |- live bubble state machine
  |- upstream/server/network interruption taxonomy
  |- use terminal.updated_at only when present as persistence proof
  |- force hydrate conversation messages if updated_at is missing
  v
[Observability + operator surfaces]
  |- chat_turn_logger + /log
  |- hermeneutic_node_logger + /hermeneutic-admin
  |- /identity
  |- /memory-admin
```

## Notes d'interpretation / Reading notes

1. `network_error` n'est pas un evenement backend emis dans le flux.
FR: c'est une inference frontend a partir d'un echec `fetch` / `ReadableStream`.
EN: it is a frontend-side inference from a `fetch` / `ReadableStream` failure.

2. Le flux public n'est pas du SSE navigateur.
FR: le provider amont parle SSE-like; le protocole public Frida reste `text/plain` avec terminal inline.
EN: the upstream provider uses an SSE-like stream; the public Frida contract remains `text/plain` with an inline terminal frame.

3. La persistance ne suit pas la meme regle selon le terminal.
FR: `done` cree un vrai message assistant complet seulement si la sauvegarde catalog/messages est prouvee; `error` cree un marqueur assistant interrompu seulement si ce marqueur est lui-meme sauvegarde. En cas d'echec de sauvegarde finale, le terminal public devient `conversation_persist_failed` sans `updated_at`.
EN: `done` stores a full canonical assistant message only when catalog/messages persistence is proven; `error` stores an interrupted assistant marker only when that marker is itself saved. If final persistence fails, the public terminal becomes `conversation_persist_failed` without `updated_at`.

4. `save_new_traces()` n'est pas une consequence generale de tout tour assistant.
FR: seules les fins `done` canonisees et verifiees peuvent alimenter les traces memoire derivees; les ecritures identitaires derivees suivent la meme barriere.
EN: only verified canonical `done` turns are allowed to feed derived memory traces; derived identity writes use the same barrier.

5. Les surfaces operateur ne sont pas des pipelines paralleles.
FR: `/log`, `/hermeneutic-admin`, `/identity` et `/memory-admin` lisent le runtime et ses derives; elles ne remplacent pas le pipeline principal.
EN: `/log`, `/hermeneutic-admin`, `/identity`, and `/memory-admin` inspect runtime state and derivatives; they do not replace the main pipeline.

## References

- `app/server.py`
- `app/core/chat_service.py`
- `app/core/chat_session_flow.py`
- `app/core/chat_memory_flow.py`
- `app/core/chat_prompt_context.py`
- `app/core/chat_llm_flow.py`
- `app/core/chat_stream_control.py`
- `app/core/assistant_turn_state.py`
- `app/core/conversations_prompt_window.py`
- `app/memory/memory_store.py`
- `app/memory/memory_traces_summaries.py`
- `app/observability/hermeneutic_node_logger.py`
- `app/web/app.js`
- `app/docs/states/specs/streaming-protocol.md`
