# FridaDev Current Runtime Pipeline

Statut: reference architecture active
Date de reference: dimanche 17 mai 2026
Classement: `app/docs/states/architecture/`
Portee: schema compact du pipeline chat/runtime courant de `FridaDev`

## Objet / Purpose

- FR: ce document donne une cartographie compacte du pipeline chat/runtime courant, incluant les documents actifs de conversation et les surfaces operateur actuelles.
- EN: this document gives a compact map of the current chat/runtime pipeline, including active conversation documents and the current operator surfaces.

## Schema one-glance

```text
[Browser / index.html + app.js]
  |- typed message
  |- optional voice draft -> /api/chat/transcribe -> whisper_transcription_service
  |- optional web_search flag
  |- active documents UI -> /api/conversations/<id>/active-documents
  |- scanned PDF active_document OCR V1 -> platform-stirling-pdf when extractor says document_ocr_required
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
  |- maybe_summarize() on dialogue-only user/assistant messages
  v
[Prompt base]
  |- backend system prompt
  |- hermeneutical prompt
  |- NOW / time grounding
  |- identity block
  |- active summary + recent dialogue window
  v
[Memory branch / chat_memory_flow]
  |- retrieve_for_arbiter()
  |- enrich_traces_with_summaries()
  |- parent summaries for injected traces
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
[Prompt guards + optional context lanes]
  |- direct identity revelation guard
  |- voice transcription guard
  |- web reading guard
  |- plain-text output contract
  |- optional injected web context
  |- active_document lane, whole or absent, after summary decision
  v
[Main LLM call / chat_llm_flow + llm_client]
  |- OpenRouter caller=llm
  |- JSON response OR text/plain streaming response
  v
[Streaming contract]
  |- assistant_output_contract decides buffering policy
  |- visible content chunks
  |- terminal control chunk = RS + JSON + LF
  |- event = done | error(error_code, updated_at only when persistence is proven)
  v
[Canonical persistence]
  |- save_conversation() returns atomic catalog/messages proof
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
  |- reload active documents from server state
  v
[Observability + operator surfaces]
  |- /dashboard: long-term metrics, conversations, translated inspection
  |- /log: technical event timeline
  |- /memory-admin: Memory/RAG domain diagnostics
  |- /hermeneutic-admin: hermeneutic and identity diagnostics
  |- /identity: canonical identity control
  |- /admin: runtime settings
```

## Notes d'interpretation / Reading notes

1. `network_error` n'est pas un evenement backend emis dans le flux.
FR: c'est une inference frontend a partir d'un echec `fetch` / `ReadableStream`.
EN: it is a frontend-side inference from a `fetch` / `ReadableStream` failure.

2. Le flux public n'est pas du SSE navigateur.
FR: le provider amont parle SSE-like; le protocole public Frida reste `text/plain` avec terminal inline.
EN: the upstream provider uses an SSE-like stream; the public Frida contract remains `text/plain` with an inline terminal frame.

3. La persistance ne suit pas la meme regle selon le terminal.
FR: `done` cree un vrai message assistant complet seulement si la sauvegarde atomique catalog/messages est prouvee; `error` cree un marqueur assistant interrompu seulement si ce marqueur est lui-meme sauvegarde. En cas d'echec de sauvegarde finale, le terminal public devient `conversation_persist_failed` sans `updated_at`.
EN: `done` stores a full canonical assistant message only when atomic catalog/messages persistence is proven; `error` stores an interrupted assistant marker only when that marker is itself saved. If final persistence fails, the public terminal becomes `conversation_persist_failed` without `updated_at`.

4. `save_new_traces()` n'est pas une consequence generale de tout tour assistant.
FR: seules les fins `done` canonisees et verifiees peuvent alimenter les traces memoire derivees; les ecritures identitaires derivees suivent la meme barriere.
EN: only verified canonical `done` turns are allowed to feed derived memory traces; derived identity writes use the same barrier.

5. La barriere post-save est commune a JSON et streaming.
FR: sur le chemin JSON nominal, la sauvegarde assistant finale precede `AssistantText`, les traces, les ecritures identitaires et les reactivations. Sur le chemin streaming nominal, la sauvegarde assistant finale precede aussi ces derivations et le terminal `done(updated_at)`. L'ordre relatif entre traces et identite peut differer apres cette barriere; il ne doit pas etre interprete comme une difference de canonisation.
EN: on the nominal JSON path, the final assistant save precedes `AssistantText`, traces, identity writes, and reactivations. On the nominal streaming path, the final assistant save also precedes these derivations and the `done(updated_at)` terminal. The relative order between traces and identity can differ after that barrier; it must not be interpreted as a canonicalization difference.

6. Les documents actifs de conversation ne sont pas de la memoire.
FR: `active_document` est un etat serveur temporaire scope conversation. Il accepte les formats textuels supportes et certains PDF scannes apres OCR V1 bornee via Stirling (`document_ocr_required` -> PDF OCRise -> extracteur FridaDev -> `complete`). Il est injecte dans une lane prompt dediee apres la decision de resume, entier ou absent. Il ne compte pas dans le seuil de resume, ne cree pas de traces memoire, n'alimente pas Identity et n'est pas Biblio.
EN: `active_document` is temporary conversation-scoped server state. It accepts supported textual formats and eligible scanned PDFs after bounded OCR V1 through Stirling (`document_ocr_required` -> OCRized PDF -> FridaDev extractor -> `complete`). It is injected into a dedicated prompt lane after the summary decision, whole or absent. It does not count toward the summary threshold, does not create memory traces, does not feed Identity, and is not Biblio.

6bis. L'OCR V1 reste bornee.
FR: l'OCR des documents actifs est synchrone, limitee a `25 pages`, `25 Mo`, `180` secondes et `fra+eng+deu`. Elle n'est pas une OCR generale, pas une modalite image, pas Biblio, et n'utilise ni n8n ni doc-pipeline dans le chemin nominal. Les surfaces ordinaires ne publient pas le texte OCR brut.
EN: active document OCR is synchronous and bounded by `25 pages`, `25 Mo`, `180` seconds, and `fra+eng+deu`. It is not general OCR, not image multimodality, not Biblio, and does not use n8n or doc-pipeline in the nominal path. Ordinary surfaces do not publish raw OCR text.

7. Les surfaces operateur ne sont pas des pipelines paralleles.
FR: `/dashboard`, `/log`, `/hermeneutic-admin`, `/identity`, `/memory-admin` et `/admin` lisent le runtime et ses derives; elles ne remplacent pas le pipeline principal.
EN: `/dashboard`, `/log`, `/hermeneutic-admin`, `/identity`, `/memory-admin`, and `/admin` inspect runtime state and derivatives; they do not replace the main pipeline.

8. La Biblio native reste separee.
FR: les futurs `library_document` / `catalogue_document` et `passage documentaire` appartiennent au chantier Biblio native / Frida Catalogue. Ils ne reutilisent pas l'etat `active_document`.
EN: future `library_document` / `catalogue_document` and `passage documentaire` belong to the native Biblio / Frida Catalogue workstream. They do not reuse `active_document` state.

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
- `app/core/active_conversation_documents.py`
- `app/core/active_document_text_extraction.py`
- `app/core/active_document_ocr_client.py`
- `app/core/active_document_prompt_lane.py`
- `app/core/active_document_upload_service.py`
- `app/memory/memory_store.py`
- `app/memory/memory_traces_summaries.py`
- `app/observability/hermeneutic_node_logger.py`
- `app/observability/active_documents_observability.py`
- `app/observability/dashboard_read_model.py`
- `app/web/app.js`
- `app/web/chat_active_documents.js`
- `app/docs/states/specs/streaming-protocol.md`
- `app/docs/states/specs/active-conversation-documents-contract.md`
- `app/docs/states/specs/dashboard-long-term-observability-contract.md`
