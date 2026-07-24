# FridaDev Current Runtime Pipeline

Statut: reference architecture active
Date de reference: jeudi 23 juillet 2026
Classement: `app/docs/states/architecture/`
Portee: schema compact du pipeline chat/runtime courant de `FridaDev`

## Objet / Purpose

- FR: ce document donne une cartographie compacte du pipeline chat/runtime courant, incluant les documents actifs de conversation et les surfaces operateur actuelles.
- EN: this document gives a compact map of the current chat/runtime pipeline, including active conversation documents and the current operator surfaces.

## Schema one-glance

```text
[Browser / index.html + app.js]
  |- typed message
  |- optional voice draft, 300 s max, one final blob
  |    -> /api/chat/transcribe, declared body <= 17 MiB
  |    -> whisper_transcription_service, bounded audio <= 16 MiB
  |    -> Whisper platform, known input duration <= 305 s
  |       or unknown WebM duration -> bounded normalization <= 306 s
  |       -> normalized WAV duration required and <= 305 s before whisper-cli
  |- optional web_search flag
  |- active documents UI -> /api/conversations/<id>/active-documents
  |    -> Flask body <= 40 MiB, bounded file read <= 40 MiB + 1 byte observed
  |- workspace file upload -> /api/workspace-folders/<id>/files
  |    -> Flask body <= 40 MiB, bounded file read <= 40 MiB + 1 byte observed
  |- scanned PDF active_document OCR V1 -> platform-stirling-pdf when extractor says document_ocr_required
  v
[chat_transport_routes.py / POST /api/chat; wiring: server.py]
  |- begin_turn + public chat entrypoint
  v
[Required main prompt gate / chat_service]
  |- main_system and main_hermeneutical must be readable, decodable and non-empty
  |- failure -> JSON 503 critical_prompt_unavailable
  |- failure -> no resolve_chat_session, conversation mutation, secret or provider call
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
  |    -> presume le sens depuis la fenetre locale avant clarification
  |    -> distingue comprendre, correction, argument et adoption
  |    -> final_output_regime = simple | meta | presence
  |- missing secondary prompt -> local fail-open result, no secondary provider call
  |- fail-open/timeout/parse error -> never presence
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
  |- validated answer/presence -> existing AssistantResponseOverride("...")
  |    -> no main provider/secret/URL call
  |    -> server-only assistant_turn.status=dialogic_presence
  |- OpenRouter caller=llm
  |- final URL resolved by llm_client from runtime main_model.base_url
  |  (central config.OR_BASE fallback only when the runtime value is absent)
  |- chat_llm_flow consumes that final URL without rebuilding its suffix
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
  |- done  -> post-save AssistantText, traces and identity effects attempted independently
  |           and fail-open only after verified canonical save
  |- error -> assistant_turn interrupted marker only when the marker save is verified
  |- persist failure -> terminal error conversation_persist_failed without updated_at
  |- interrupted turns excluded from prompt window and traces
  |- presence -> exact assistant message "..." persisted once on normal success
  |    -> remains in canonical history
  |    -> user message keeps normal Memory and Identity post-save derivations
  |    -> marked assistant remains in dialogue but is excluded from Memory and
  |       projected as non-substantive at both Identity boundaries
  |    -> not written to hermeneutic node_state
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

5. La disponibilite des prompts est verifiee a leur frontiere d'usage.
FR: les deux prompts constitutifs refusent `/api/chat` avant toute resolution de
session; `main_system` refuse aussi la creation `/api/conversations` avant
`new_conversation()`. Les prompts de resume, reformulation Web et juge Identity
mutable ne bloquent que leur fonction et n'appellent aucun provider lorsqu'ils
sont indisponibles. Les prompts legacy ne sont pas des preconditions de
demarrage ou de validation offline.
EN: the two constitutive prompts reject `/api/chat` before session resolution;
`main_system` also rejects `/api/conversations` before `new_conversation()`.
Summary, Web reformulation and mutable Identity judge prompts only gate their
own function and never call a provider when unavailable. Legacy prompts are
not startup or offline-validation preconditions.

6. La barriere post-save est commune a JSON et streaming.
FR: sur les chemins JSON et streaming, normaux ou
`AssistantResponseOverride`, la sauvegarde assistant finale precede
`AssistantText`, les traces, les ecritures identitaires et les reactivations.
Une sauvegarde absente, negative ou levee reste fail-closed et n'ouvre aucun de
ces derives. Apres preuve positive, chaque derive est tente une fois et isole:
sa panne, comme celle du logger ou du journal admin qui tente de l'observer, ne
change plus le succes JSON ou le terminal `done`, ne declenche aucun second
save et ne modifie pas le message canonique. L'observation reste bornee a un
nom d'effet stable, au `conversation_id`, a la classe d'erreur et a un reason
code content-free. L'ordre relatif entre traces et identite peut differer apres
cette barriere; il ne doit pas etre interprete comme une difference de
canonisation.
EN: on JSON and streaming paths, whether normal or
`AssistantResponseOverride`, the final assistant save precedes
`AssistantText`, traces, identity writes, and reactivations. A missing,
negative, or raised save remains fail-closed and starts none of these derived
effects. After positive proof, each derived effect is attempted once and
isolated: its failure, like a failure of the logger or admin journal used to
observe it, no longer changes JSON success or the `done` terminal, triggers no
second save, and does not alter the canonical message. Observation is bounded
to a stable effect name, `conversation_id`, error class, and content-free
reason code. The relative order between traces and identity may differ after
that barrier; it must not be interpreted as a canonicalization difference.

7. Les documents actifs de conversation ne sont pas de la memoire.
FR: `active_document` est un etat serveur temporaire scope conversation. Il accepte les formats textuels supportes et certains PDF scannes apres OCR V1 bornee via Stirling (`document_ocr_required` -> PDF OCRise -> extracteur FridaDev -> `complete`). Il est injecte dans une lane prompt dediee apres la decision de resume, entier ou absent. Il ne compte pas dans le seuil de resume, ne cree pas de traces memoire, n'alimente pas Identity et n'est pas Biblio.
EN: `active_document` is temporary conversation-scoped server state. It accepts supported textual formats and eligible scanned PDFs after bounded OCR V1 through Stirling (`document_ocr_required` -> OCRized PDF -> FridaDev extractor -> `complete`). It is injected into a dedicated prompt lane after the summary decision, whole or absent. It does not count toward the summary threshold, does not create memory traces, does not feed Identity, and is not Biblio.

6bis. L'OCR V1 reste bornee.
FR: l'OCR des documents actifs est synchrone, limitee a `25 pages`, `25 Mo`, `180` secondes et `fra+eng+deu`. Elle n'est pas une OCR generale, pas une modalite image, pas Biblio, et n'utilise ni n8n ni doc-pipeline dans le chemin nominal. Les surfaces ordinaires ne publient pas le texte OCR brut.
EN: active document OCR is synchronous and bounded by `25 pages`, `25 Mo`, `180` seconds, and `fra+eng+deu`. It is not general OCR, not image multimodality, not Biblio, and does not use n8n or doc-pipeline in the nominal path. Ordinary surfaces do not publish raw OCR text.

6ter. La frontiere multipart documentaire est bornee avant et apres parsing.
FR: Flask applique `MAX_CONTENT_LENGTH=40 MiB` aux corps applicatifs. Avec
Flask `3.0.3` et Werkzeug `3.1.8`, un flux WSGI termine sans longueur fiable
est limite a cette valeur; sans longueur ni signal de terminaison, le flux est
vide par securite. Les services documents actifs et workspace lisent ensuite
par blocs jusqu'a `40 MiB + 1 octet` au plus. Ce plafond lecteur defensif
accepte sa limite exacte lorsqu'il est teste seul, mais le plafond du
corps inclut l'enveloppe multipart: un fichier de `40 MiB` n'est donc pas
uploadable de bout en bout. Au-dessus des bornes applicables, aucun extracteur,
OCR, stockage, activation ou Nextcloud n'est appele. Cette frontiere ne
modifie pas les plafonds image, PDF visuel/OCR, provider ou prompt. Le document
reste entier ou absent du tour, et le tour continue avec un signal d'exclusion
honnete.
EN: Flask applies `MAX_CONTENT_LENGTH=40 MiB` to application request bodies.
With Flask `3.0.3` and Werkzeug `3.1.8`, a terminated WSGI stream without a
reliable length is limited to that value; without a length or termination
signal, the safe fallback exposes an empty stream. Active-document and
workspace services then read in blocks up to `40 MiB + 1 byte`. The exact
reader limit is accepted when that defensive reader is exercised in isolation,
but the request-body limit includes the multipart envelope: a `40 MiB` file is
therefore not uploadable end to end. Above the applicable bounds no extractor,
OCR, storage, activation, or Nextcloud call runs. Image, visual/OCR PDF,
provider, and prompt limits remain separate. A document remains whole or
absent from the turn, which continues with an honest exclusion signal.

8. Les surfaces operateur ne sont pas des pipelines paralleles.
FR: `/dashboard`, `/log`, `/hermeneutic-admin`, `/identity`, `/memory-admin` et `/admin` lisent le runtime et ses derives; elles ne remplacent pas le pipeline principal.
EN: `/dashboard`, `/log`, `/hermeneutic-admin`, `/identity`, `/memory-admin`, and `/admin` inspect runtime state and derivatives; they do not replace the main pipeline.

9. La Biblio native reste separee.
FR: les futurs `library_document` / `catalogue_document` et `passage documentaire` appartiennent au chantier Biblio native / Frida Catalogue. Ils ne reutilisent pas l'etat `active_document`.
EN: future `library_document` / `catalogue_document` and `passage documentaire` belong to the native Biblio / Frida Catalogue workstream. They do not reuse `active_document` state.

10. La dictee Whisper reste un flux unique et borne.
FR: `MediaRecorder.start()` reste sans `timeslice`; le navigateur produit un
seul blob, effectue un seul upload et demande une seule transcription. FridaDev
refuse le corps declare au-dessus de `17 Mio` avant le parsing multipart, puis
lit le fichier par blocs jusqu'a `16 Mio + 1 octet` au plus pour accepter
exactement `16 Mio` ou refuser au-dessus. Les metadonnees de taille et duree du
client restent informatives.
Un WebM peut ne pas exposer de duree de conteneur lisible. Cette absence
autorise uniquement la normalisation `ffmpeg` bornee a `306 s`, jamais un appel
direct a Whisper. La duree du WAV normalise reste la decision finale: elle doit
etre connue et inferieure ou egale a `305 s` avant `whisper-cli`; si la
normalisation echoue dans le cas inconnu, aucun fallback brut n'est permis.
EN: `MediaRecorder.start()` remains without a `timeslice`; the browser produces
one blob, performs one upload, and requests one transcription. FridaDev rejects
a declared body above `17 MiB` before multipart parsing, then reads the file in
blocks up to `16 MiB + 1 byte` to accept exactly `16 MiB` or reject above it.
Client size and duration metadata remain informational.
A WebM container may not expose a readable duration. That absence authorizes
only `ffmpeg` normalization bounded to `306 s`, never a direct Whisper call.
The normalized WAV duration remains the final decision: it must be known and
at most `305 s` before `whisper-cli`; if normalization fails for an unknown
input duration, no raw fallback is allowed.

11. `presence` est un regime de sortie local, pas une suspension epistemique.
FR: seul un verdict positif `answer/presence` du `validation_agent` autorise
les trois points. Le runtime ne reconnait aucune phrase utilisateur par regex,
substring ou liste lexicale. La sortie reutilise la voie d'override et la
barriere de persistance communes; elle ne survit au tour que comme message de
conversation canonique, jamais comme inertie `node_state`. Le message assistant
porte le marqueur serveur borne
`assistant_turn.status=dialogic_presence`: cette meta, et jamais le texte,
l'exclut durablement des traces Memory et le projette sans contenu substantiel
vers l'extracteur et le staging Identity. Le message utilisateur conserve les
derives normaux du tour apres sauvegarde canonique. Une question, une detresse,
un risque, un hard guard ou une action materielle ambigue ne doivent pas etre
masques par ce regime.
EN: only a positive `answer/presence` verdict from `validation_agent`
authorizes the three dots. Runtime code recognizes no user phrase through
regex, substring, or lexical lists. The output reuses the common override and
persistence barrier; it survives only as a canonical conversation message,
never as `node_state` inertia. A bounded server marker, rather than the visible
text, durably excludes the assistant presence act from Memory and projects it
as non-substantive at both Identity boundaries; the user message keeps normal
post-save derivations. A question, distress, risk, hard guard, or ambiguous
material action must not be hidden by this regime.

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
- `app/core/document_upload_reader.py`
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
