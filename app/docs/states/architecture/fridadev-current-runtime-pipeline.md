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
  |- event = done | error(error_code, updated_at)
  v
[Canonical persistence]
  |- done  -> full assistant message + save_conversation(updated_at)
  |- done  -> save_new_traces() only after canonical save
  |- error -> assistant_turn interrupted marker (empty content)
  |- interrupted turns excluded from prompt window and traces
  v
[Frontend render + rehydration]
  |- live bubble state machine
  |- upstream/server/network interruption taxonomy
  |- use terminal.updated_at when present
  |- force hydrate conversation messages if needed
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
FR: `done` cree un vrai message assistant complet; `error` cree un marqueur assistant interrompu, sans texte partiel canonique.
EN: `done` stores a full canonical assistant message; `error` stores an interrupted assistant marker with no canonical partial text.

4. `save_new_traces()` n'est pas une consequence generale de tout tour assistant.
FR: seules les fins `done` canonisees peuvent alimenter les traces memoire derivees.
EN: only canonical `done` turns are allowed to feed derived memory traces.

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
