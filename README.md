# Frida

Current repository state as of Sunday, May 17, 2026.
Etat courant du depot au dimanche 17 mai 2026.

## English

FridaDev is the application repository for Frida: a working AI dialogue runtime with memory, identity, hermeneutic judgment, active conversation documents, and operator observability. This repository is not a generic scaffold; it contains the backend runtime, browser UI, admin surfaces, observability read-models, tests, prompts, and structured documentation for the live OVH instance.

Primary current-state references:

- Documentation hub: `app/docs/README.md`
- Current runtime pipeline: `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`
- Active conversation documents contract: `app/docs/states/specs/active-conversation-documents-contract.md`
- Archived active conversation documents OCR roadmap: `app/docs/todo-done/product/active-conversation-documents-ocr-todo.md`
- Long-term dashboard contract: `app/docs/states/specs/dashboard-long-term-observability-contract.md`
- Memory Admin contract: `app/docs/states/specs/memory-admin-surface-contract.md`
- Log module contract: `app/docs/states/specs/log-module-contract.md`
- Archived prompt/payload semantic audit: `app/docs/todo-done/audits/model-prompt-payload-interpretation-audit-2026-05-16.md`

Historical milestones:

- `app/docs/states/project/Frida-State-english-03-04-26.md`
- `app/docs/states/project/Frida-State-french-03-04-26.md`

### Runtime Pipeline

Detailed companion: `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`

```text
Browser chat
  |- typed message, optional voice transcription, optional web search
  |- active conversation documents upload/list/remove, with bounded OCR V1 for eligible scanned PDFs
  v
POST /api/chat
  |- session and conversation resolution
  |- persist user turn
  |- maybe_summarize() on dialogue-only user/assistant text
  v
Prompt preparation
  |- system and hermeneutic prompts
  |- NOW / time grounding
  |- identity block
  |- active summary and recent dialogue window
  |- Memory/RAG retrieval, summaries, context hints, arbiter choices
  |- hermeneutic branch: stimmung_agent -> primary_node -> validation_agent
  |- guards and optional web context
  |- active_document lane injected after summary decision, whole or absent
  v
Main LLM call
  |- plain-text output contract
  |- JSON or text/plain streaming response with terminal control frame
  v
Canonical persistence
  |- full assistant message saved only on verified done
  |- interrupted marker saved only on verified error marker
  |- post-save derived writes: AssistantText log, identity writes, memory traces
  v
Frontend rehydration and operator observability
  |- chat thread rehydration
  |- /dashboard, /log, /memory-admin, /hermeneutic-admin, /identity, /admin
```

### What the system does today

- The browser chat sends typed turns or optional voice transcripts to `POST /api/chat`; the server validates `input_mode`, resolves or creates the conversation, persists the user turn, and only then builds the assistant response.
- Conversation summaries are triggered from dialogue-only `user` / `assistant` text. System prompts, identity, memory, web, hermeneutic context, and active documents do not count toward the summary threshold.
- Prompt construction combines the main prompt, hermeneutic contract, time grounding, identity block, active summary, recent dialogue, Memory/RAG traces with parent summaries, context hints, optional web context, and the validated hermeneutic judgment.
- Active conversation documents are temporary, conversation-scoped files supplied by the user. Supported formats are PDF text, DOCX, ODT, MD, TXT, plus eligible scanned PDFs after bounded OCR V1 through `platform-stirling-pdf`. OCR is attempted only after `document_ocr_required`, with `fra+eng+deu`, `25 pages`, `25 Mo`, and `180 s` limits; the OCRized PDF is reprocessed by the FridaDev extractor and becomes active only if the final extraction is `complete`.
- Active documents, including OCRized ones, are injected into the model whole when they fit the explicit document admission rule, or excluded whole with a compact reason signal; they are never silently truncated.
- Active documents are not Memory/RAG, not Identity, not Summary, not Web, and not Biblio. They are not embedded, indexed, summarized, promoted to memory, or reused outside their conversation.
- Active document OCR is not general OCR, not image multimodality, not Biblio, and not a durable document pipeline. It does not use n8n or doc-pipeline in the nominal path, and ordinary UI/logs/dashboard surfaces do not expose raw OCR text.
- The main LLM call runs under a plain-text output contract. Streaming uses visible text chunks plus one terminal control frame.
- On `done`, Frida saves the complete assistant text, verifies canonical persistence, then emits derived writes. On `error`, it stores an interrupted marker when that marker save is proven; it does not canonicalize partial assistant text.
- `/dashboard` is the long-term operator dashboard: recent health, materialized metrics, conversation comparison, translated inspection, and content-free summaries.
- `/log` remains the technical debug timeline. Memory Admin, Hermeneutic Admin, and Identity remain specialized domain or editing surfaces.
- The future Biblio native / Frida Catalogue workstream is separate: it concerns persistent `library_document` / `catalogue_document` lookup and bounded `passage documentaire` extraction. It is not implemented by the active conversation documents feature.

### What the repository contains

- Flask backend orchestration in `app/server.py`
- Core chat and prompt flows in `app/core/`
- Active conversation document state, extraction, upload service, and prompt lane in `app/core/`
- Memory and identity pipelines in `app/memory/` and `app/identity/`
- Admin/runtime settings and domain admin services in `app/admin/`
- Observability, dashboard analytics, and read-models in `app/observability/`
- Browser chat and admin frontend in `app/web/`
- Tests in `app/tests/`
- Structured documentation in `app/docs/`

### Operator surfaces

- `/`: chat runtime and active conversation documents controls.
- `/dashboard`: non-technical overview, long-period metrics, conversations, translated inspection, and content gate status.
- `/log`: technical event timeline, filters, export, and scoped debugging.
- `/memory-admin`: Memory/RAG read-model and diagnostics.
- `/hermeneutic-admin`: hermeneutic pipeline and identity diagnostics.
- `/identity`: canonical identity control and editing surface.
- `/admin`: runtime settings and operator configuration.

### Documentation anchors

- Docs hub: `app/docs/README.md`
- Current runtime pipeline: `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`
- Active conversation documents contract: `app/docs/states/specs/active-conversation-documents-contract.md`
- Archived active conversation documents roadmap: `app/docs/todo-done/product/active-conversation-documents-todo.md`
- Archived active conversation documents audit-plan: `app/docs/todo-done/product/active-conversation-documents-audit-plan.md`
- Archived active conversation documents OCR roadmap: `app/docs/todo-done/product/active-conversation-documents-ocr-todo.md`
- Active Biblio native / Frida Catalogue roadmap: `app/docs/todo-todo/product/frida-biblio-native-catalogue-todo.md`
- Long-term dashboard contract: `app/docs/states/specs/dashboard-long-term-observability-contract.md`
- Archived long-term dashboard roadmap: `app/docs/todo-done/admin/dashboard-long-term-observability-todo.md`
- Streaming protocol source-of-truth: `app/docs/states/specs/streaming-protocol.md`
- Chat enunciation / identity / time-gap doctrine: `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- Active identity doctrine plan: `app/docs/states/policies/identity-new-contract-plan.md`
- Archived identity implementation roadmap: `app/docs/todo-done/refactors/identity-new-contract-todo.md`
- Memory Admin surface contract: `app/docs/states/specs/memory-admin-surface-contract.md`
- Response arbiter power contract: `app/docs/states/specs/response-arbiter-power-contract.md`
- Global audit dated 2026-05-03: `app/docs/states/audits/fridadev-global-audit-2026-05-03.md`
- Archived global audit remediation: `app/docs/todo-done/audits/fridadev-global-audit-remediation-todo.md`
- Active installation roadmap: `app/docs/todo-todo/product/Frida-installation-config.md`

### Versioned vs runtime-local

Versioned:

- code, prompts, scripts, tests, docs;
- static examples and provisioning notes under `state/data/identity/`.

Not versioned:

- `app/.env`;
- runtime state under `state/conv`, `state/logs`, and mounted runtime data;
- local operator-provisioned identity files under `state/data/identity/*.txt`;
- caches, virtualenvs, editor files, and machine residue.

Container mapping note:

- `/app/conv`, `/app/logs`, and `/app/data` are container mount targets for host `state/...` directories.

A fresh clone still needs a valid local `.env`, reachable runtime dependencies, and initialized local runtime state under `state/...`.

### Stack operations

```bash
./stack.sh up
./stack.sh ps
./stack.sh health
```

### Essential paths

- `docker-compose.yml`
- `stack.sh`
- `app/server.py`
- `app/minimal_validation.py`
- `app/docs/README.md`

### Website and contact

- website: [https://frida-ai.fr](https://frida-ai.fr)
- contact: [tofmuck@frida-ai.fr](mailto:tofmuck@frida-ai.fr)

### License

This repository is distributed under the **MIT License**. See [LICENSE](LICENSE).

---

## Francais

FridaDev est le depot applicatif de Frida: un runtime IA de dialogue avec memoire, identite, jugement hermeneutique, documents actifs de conversation et observabilite operateur. Ce depot n'est pas un scaffold generique; il contient le backend runtime, l'UI navigateur, les surfaces admin, les read-models d'observabilite, les tests, les prompts et la documentation structuree de l'instance OVH active.

References principales pour l'etat courant:

- Hub documentaire: `app/docs/README.md`
- Pipeline runtime courant: `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`
- Contrat des documents actifs de conversation: `app/docs/states/specs/active-conversation-documents-contract.md`
- Roadmap archivee OCR des documents actifs: `app/docs/todo-done/product/active-conversation-documents-ocr-todo.md`
- Contrat du dashboard long terme: `app/docs/states/specs/dashboard-long-term-observability-contract.md`
- Contrat Memory Admin: `app/docs/states/specs/memory-admin-surface-contract.md`
- Contrat du module logs: `app/docs/states/specs/log-module-contract.md`
- Audit archive du contrat semantique prompt/payload: `app/docs/todo-done/audits/model-prompt-payload-interpretation-audit-2026-05-16.md`

Jalons historiques:

- `app/docs/states/project/Frida-State-french-03-04-26.md`
- `app/docs/states/project/Frida-State-english-03-04-26.md`

### Pipeline runtime

Document compagnon detaille: `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`

```text
Chat navigateur
  |- message tape, transcription vocale optionnelle, recherche web optionnelle
  |- upload/list/retrait des documents actifs de conversation, avec OCR V1 bornee pour les PDF scannes eligibles
  v
POST /api/chat
  |- resolution session et conversation
  |- persistance du tour utilisateur
  |- maybe_summarize() sur le seul dialogue user/assistant
  v
Preparation du prompt
  |- prompts systeme et hermeneutique
  |- NOW / ancrage temporel
  |- bloc identite
  |- resume actif et fenetre de dialogue recente
  |- traces Memory/RAG avec resumes parents, context hints, arbitrage
  |- branche hermeneutique: stimmung_agent -> primary_node -> validation_agent
  |- gardes et contexte web optionnel
  |- lane active_document injectee apres la decision de resume, entiere ou absente
  v
Appel LLM principal
  |- contrat de sortie texte brut
  |- reponse JSON ou stream text/plain avec terminal de controle
  v
Persistance canonique
  |- message assistant complet seulement sur done verifie
  |- marqueur interrompu seulement sur erreur verifiee
  |- derives post-save: log AssistantText, identite, traces memoire
  v
Rehydratation frontend et observabilite operateur
  |- rehydratation du fil chat
  |- /dashboard, /log, /memory-admin, /hermeneutic-admin, /identity, /admin
```

### Ce que fait aujourd'hui le systeme

- Le chat navigateur envoie les tours tapes ou les transcriptions vocales optionnelles vers `POST /api/chat`; le serveur valide `input_mode`, resolve ou cree la conversation, persiste le tour utilisateur, puis fabrique la reponse assistant.
- Les resumes de conversation sont declenches depuis le seul texte dialogique `user` / `assistant`. Les prompts systeme, l'identite, la memoire, le web, le contexte hermeneutique et les documents actifs ne comptent pas dans le seuil de resume.
- La construction du prompt combine prompt principal, contrat hermeneutique, ancrage temporel, bloc identite, resume actif, dialogue recent, traces Memory/RAG avec resumes parents, context hints, contexte web optionnel et jugement hermeneutique valide.
- Les documents actifs de conversation sont des fichiers temporaires, fournis par l'utilisateur et scopes a une conversation. Les formats supportes sont PDF textuel, DOCX, ODT, MD, TXT, et certains PDF scannes apres OCR V1 bornee via `platform-stirling-pdf`. L'OCR est tentee seulement apres `document_ocr_required`, avec les limites `fra+eng+deu`, `25 pages`, `25 Mo` et `180 s`; le PDF OCRise est repasse dans l'extracteur FridaDev et devient actif seulement si l'extraction finale est `complete`.
- Les documents actifs, y compris OCRises, sont injectes entiers si la regle explicite d'admission documentaire le permet, ou exclus entiers avec un signal compact; ils ne sont jamais tronques silencieusement.
- Les documents actifs ne sont ni Memory/RAG, ni Identity, ni Summary, ni Web, ni Biblio. Ils ne sont pas embedded, indexes, resumes, promus en memoire ou reutilises hors conversation.
- L'OCR des documents actifs n'est pas une OCR generale, pas une modalite image, pas Biblio et pas un pipeline documentaire durable. Elle n'utilise ni n8n ni doc-pipeline dans le chemin nominal, et les surfaces ordinaires UI/logs/dashboard n'exposent pas le texte OCR brut.
- L'appel LLM principal suit un contrat de sortie texte brut. Le streaming utilise des chunks texte visibles et un seul terminal de controle.
- Sur `done`, Frida sauvegarde le texte assistant complet, verifie la persistance canonique, puis emet les ecritures derivees. Sur `error`, Frida sauvegarde un marqueur interrompu lorsque cette sauvegarde est prouvee; elle ne canonise pas de texte assistant partiel.
- `/dashboard` est le dashboard operateur long terme: sante recente, metriques materialisees, comparaison des conversations, inspection traduite et statut du content gate.
- `/log` reste la timeline technique de debug. Memory Admin, Hermeneutic Admin et Identity restent des surfaces specialisees de domaine ou d'edition.
- Le futur chantier Biblio native / Frida Catalogue est separe: il concerne la consultation de `library_document` / `catalogue_document` persistants et l'extraction bornee de `passage documentaire`. Il n'est pas implemente par la fonctionnalite documents actifs.

### Ce que contient le depot

- Orchestration backend Flask dans `app/server.py`
- Flux chat et prompt dans `app/core/`
- Etat, extraction, service upload et lane prompt des documents actifs dans `app/core/`
- Pipelines memoire et identite dans `app/memory/` et `app/identity/`
- Services admin/runtime settings et domaines admin dans `app/admin/`
- Observabilite, analytics dashboard et read-models dans `app/observability/`
- Chat navigateur et frontend admin dans `app/web/`
- Tests dans `app/tests/`
- Documentation structuree dans `app/docs/`

### Surfaces operateur

- `/`: chat runtime et controles des documents actifs de conversation.
- `/dashboard`: vue lisible non-technicien, metriques longue periode, conversations, inspection traduite et etat du content gate.
- `/log`: timeline technique, filtres, exports et debug scope.
- `/memory-admin`: read-model et diagnostics Memory/RAG.
- `/hermeneutic-admin`: diagnostics du pipeline hermeneutique et de l'identite.
- `/identity`: pilotage canonique et edition de l'identite.
- `/admin`: runtime settings et configuration operateur.

### Ancres documentaires

- Hub docs: `app/docs/README.md`
- Pipeline runtime courant: `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`
- Contrat documents actifs de conversation: `app/docs/states/specs/active-conversation-documents-contract.md`
- Roadmap archivee documents actifs de conversation: `app/docs/todo-done/product/active-conversation-documents-todo.md`
- Audit-plan archive documents actifs de conversation: `app/docs/todo-done/product/active-conversation-documents-audit-plan.md`
- Roadmap archivee OCR des documents actifs: `app/docs/todo-done/product/active-conversation-documents-ocr-todo.md`
- Roadmap active Biblio native / Frida Catalogue: `app/docs/todo-todo/product/frida-biblio-native-catalogue-todo.md`
- Contrat dashboard long terme: `app/docs/states/specs/dashboard-long-term-observability-contract.md`
- Roadmap archivee dashboard long terme: `app/docs/todo-done/admin/dashboard-long-term-observability-todo.md`
- Spec source-of-truth du protocole streaming: `app/docs/states/specs/streaming-protocol.md`
- Doctrine voix / identite / gap temporel: `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- Plan doctrinal actif identity: `app/docs/states/policies/identity-new-contract-plan.md`
- Roadmap implementation identity archivee: `app/docs/todo-done/refactors/identity-new-contract-todo.md`
- Contrat Memory Admin: `app/docs/states/specs/memory-admin-surface-contract.md`
- Contrat de pouvoir de l'arbitre de reponse: `app/docs/states/specs/response-arbiter-power-contract.md`
- Audit global date du 2026-05-03: `app/docs/states/audits/fridadev-global-audit-2026-05-03.md`
- Remediation archivee de l'audit global: `app/docs/todo-done/audits/fridadev-global-audit-remediation-todo.md`
- Roadmap installation active: `app/docs/todo-todo/product/Frida-installation-config.md`

### Ce qui est versionne vs local runtime

Versionne:

- code, prompts, scripts, tests, docs;
- exemples statiques et notes de provisionnement sous `state/data/identity/`.

Non versionne:

- `app/.env`;
- etat runtime sous `state/conv`, `state/logs` et donnees runtime montees;
- fichiers d'identite locaux provisionnes par l'operateur sous `state/data/identity/*.txt`;
- caches, virtualenvs, fichiers editeur et residus machine.

Repere conteneur:

- `/app/conv`, `/app/logs` et `/app/data` sont les cibles de montage conteneur des repertoires hote `state/...`.

Un clone neuf necessite toujours un `.env` local valide, des dependances runtime joignables et un etat local initialise sous `state/...`.

### Exploitation de la stack

```bash
./stack.sh up
./stack.sh ps
./stack.sh health
```

### Chemins essentiels

- `docker-compose.yml`
- `stack.sh`
- `app/server.py`
- `app/minimal_validation.py`
- `app/docs/README.md`

### Site et contact

- site: [https://frida-ai.fr](https://frida-ai.fr)
- contact: [tofmuck@frida-ai.fr](mailto:tofmuck@frida-ai.fr)

### Licence

Ce depot est distribue sous licence **MIT**. Voir [LICENSE](LICENSE).
