# FridaDev Repo Audit / Audit du depot FridaDev

Statut: audit canonique current-state
Date cible / Target date: jeudi 16 avril 2026 - 12:22 Europe/Paris
HEAD audite / Audited HEAD: `725b644` (`2026-04-16 09:59:10 UTC`)
Portee / Scope: delta repo depuis l'audit canonique du 03/04/2026, validation contre le code reel, cartographie current-state

## 1. Methode / Method

- Sources utilisees / Sources used:
  - historique Git du fichier d'audit et du repo;
  - code courant du depot;
  - tests versionnes servant de preuves de contrat;
  - documentation structuree versionnee.
- Aucune source web externe n'a ete utilisee.
- Aucune reconstruction runtime n'a ete faite pour ce refresh: le chantier est documentaire et s'appuie sur code + tests + histoire Git.
- Controle temporel:
  - `HEAD` n'a pas depasse la cible `2026-04-16 10:22:00Z`;
  - `git rev-list --count --after='2026-04-16T10:22:00Z' HEAD` retourne `0`;
  - l'audit peut donc decrire l'etat courant reel sans trahir la date cible.

## 2. Point de depart Git / Git baseline

| Role | Commit | Note |
| --- | --- | --- |
| Introduction de l'audit / Audit introduction | `1e1d540` | Cree `app/docs/fridadev_repo_audit.md` |
| Canonisation du chemin / Canonical path move | `efd6433` | Deplace l'audit vers `app/docs/todo-done/audits/fridadev_repo_audit.md` |
| Base honnete du delta current-state / Honest current-state delta base | `8f7750a` | Ferme le Lot 9 et fixe la version canonique "03/04/2026" de l'audit |
| Retouche mineure / Minor maintenance touch | `09acfc0` | Met a jour seulement le nombre documente de fichiers de tests |
| HEAD audite / Audited HEAD | `725b644` | Etat courant du repo encore situe avant la date cible |

Base retenue pour mesurer le delta jusqu'a aujourd'hui / Chosen base for the delta:
- `8f7750a` est la base la plus honnete.
- `1e1d540` reste utile comme origine historique, mais il decrit une autre arborescence docs et un repo encore tres different.
- `09acfc0` ne change pas la lecture du repo; c'est une retouche d'entretien documentaire, pas un nouveau socle canonique.

## 3. Resume executif / Executive summary

### FR

- `FridaDev` n'est plus seulement le snapshot hermeneutique du 03/04/2026. Le repo courant ajoute un contrat streaming public ferme, une couche memoire/RAG plus epaisse, des surfaces admin identite/memoire plus vastes, et un chemin voix/Whisper reel cote chat.
- L'entree runtime reste un Flask monolithique (`app/server.py`), mais le pipeline utile est aujourd'hui bien plus explicite et contract-teste: session, grounding temporel, retrieval/arbitrage, `stimmung_agent`, `primary_node`, `validation_agent`, injection `[JUGEMENT HERMENEUTIQUE]`, appel LLM principal, controle de stream, persistence et rehydratation frontend.
- Le delta majeur depuis l'audit de base n'est pas une refonte d'architecture pure. C'est une densification reelle du produit: streaming robuste, surfaces operateur nouvelles, specs sources-of-truth, cartographies memoire/RAG, archives de migration OVH, et contrats frontend/backend plus testables.
- La securite admin a change de nature: on n'est plus dans le contrat token/LAN de l'audit du 03/04. Le code courant impose un acces `/api/admin/*` via proxy de confiance + identite `Remote-User`, avec exception loopback pour les preuves techniques in-container.
- La dette principale reste structurelle: `app/server.py`, `app/minimal_validation.py`, `app/admin/runtime_settings.py`, `app/web/app.js`, `app/web/admin.js` et `app/memory/memory_store.py` concentrent encore beaucoup de responsabilites.
- Finding `record_arbiter_decisions()` requalifie le `2026-05-04`: le modele arbitre effectif est capture/passe jusqu'a la persistence, et le cas de changement de runtime setting entre appel et insert est couvert par test. Ne plus le traiter comme finding actif sans regression.

### EN

- `FridaDev` is no longer only the April 3 hermeneutic snapshot. The current repository adds a closed public streaming contract, a thicker memory/RAG layer, broader identity/memory admin surfaces, and a real voice/Whisper path on the chat surface.
- The runtime still enters through a monolithic Flask file (`app/server.py`), but the useful pipeline is now much more explicit and contract-tested: session, time grounding, retrieval/arbitration, `stimmung_agent`, `primary_node`, `validation_agent`, `[JUGEMENT HERMENEUTIQUE]` injection, main LLM call, stream control, persistence, and frontend rehydration.
- The major delta since the base audit is not a clean architectural rewrite. It is a real product thickening: hardened streaming, new operator surfaces, source-of-truth specs, memory/RAG cartography, OVH migration archives, and more testable frontend/backend contracts.
- Admin security has changed in kind: the current code no longer matches the old token/LAN reading from the April 3 audit. `/api/admin/*` is now guarded through a trusted proxy plus `Remote-User` identity, with loopback-only bypass for in-container technical proofs.
- The main debt remains structural: `app/server.py`, `app/minimal_validation.py`, `app/admin/runtime_settings.py`, `app/web/app.js`, `app/web/admin.js`, and `app/memory/memory_store.py` still concentrate a large share of the system's moving parts.
- Active finding to keep visible but out of scope here: `app/memory/memory_store.py` can still persist an arbiter model different from the one that actually produced the decision if the runtime setting changes between the LLM call and the insert.

## 4. Delta majeur depuis `8f7750a` / Major delta since `8f7750a`

| Theme | Audit de base (03/04/2026) | Etat courant (16/04/2026) | Preuves principales |
| --- | --- | --- | --- |
| Streaming chat | Flux plain-text en place, mais pas encore de spec publique source-of-truth ni de politique canonique complete pour les interruptions. | Contrat public explicite `text/plain` + terminal inline (`done`/`error`), metadata terminales `updated_at`, taxonomie frontend observable (`upstream/server/network`), persistance canonique des interruptions, exclusion prompt/traces, spec normative et batterie lot 0-7 fermee. | `app/core/chat_stream_control.py`, `app/core/chat_llm_flow.py`, `app/web/app.js`, `app/docs/states/specs/streaming-protocol.md`, `app/tests/test_server_phase14.py`, `app/tests/test_server_logs_phase3.py`, `app/tests/unit/chat/test_chat_stream_control.py`, `app/tests/integration/frontend_chat/test_frontend_chat_contract.py` |
| Admin / securite operateur | Audit encore centre sur token + LAN/CIDR et surfaces `/log` + `/hermeneutic-admin`. | Garde admin proxy-first (`platform-caddy`/`caddy` + `Remote-User`), loopback accepte pour preuves techniques, surfaces publiques `/identity` et `/memory-admin`, route `GET /api/admin/memory/dashboard`, et contrat OVH documente dans `AGENTS.md`. | `app/server.py`, `AGENTS.md`, `app/tests/test_server_admin_settings_phase5.py`, `app/tests/test_server_admin_memory_surface_phase10e.py` |
| Memoire / traces / summaries / arbiter | Le 03/04 montrait surtout le pipeline hermeneutique et l'arbitre, sans cartographie detaillee des voies summaries / pre-arbiter basket / surfaces Memory Admin. | Retrieval hybride pour l'arbitre, enrichissement summaries, pre-arbiter basket, piste summaries, Memory Admin, identity governance/edit/read-model, mutable identity rewrite, filtrage des marqueurs assistant interrompus hors traces. | `app/core/chat_memory_flow.py`, `app/memory/memory_store.py`, `app/memory/memory_traces_summaries.py`, `app/docs/states/architecture/memory-rag-current-pipeline-cartography.md`, `app/tests/unit/memory/test_memory_store_blocks_phase8bis.py` |
| Frontend chat / Whisper | Surface chat plain-text, sans dictation Whisper ni machine d'etats stream cote bulle assistant. | `input_mode`, `/api/chat/transcribe`, module `whisper_dictation.js`, etat visuel stream (`preparing`, `waiting_visible_content`, `streaming`, `interrupted`), rehydratation via `assistant_turn` et `terminal.updated_at`. | `app/web/app.js`, `app/core/chat_session_flow.py`, `app/server.py`, `app/tests/integration/frontend_chat/test_frontend_whisper_contract.py`, `app/tests/unit/frontend_chat/test_streaming_ui_state_module.js` |
| Docs et structure documentaire | Arborescence docs fraichement stabilisee autour du state du 03/04 et de la cloture Lot 9. | Le repo a gagne des specs stables (streaming, identity, memory admin, memory RAG), des baselines d'evaluation, une trace de migration OVH, des roadmaps archives de produit, et une cartographie plus mature des pipelines. | `app/docs/README.md`, `app/docs/states/specs/`, `app/docs/states/architecture/`, `app/docs/todo-done/migrations/fridadev-to-frida-system-migration-todo.md` |

## 5. Etat courant du repo / Current repository state

### 5.1 Cartographie structurelle rapide / Fast structural cartography

- Racine / Root:
  - `docker-compose.yml`, `stack.sh`, `README.md`, `AGENTS.md`
  - `app/` concentre code, tests et docs structurees
- Backend Python:
  - entree HTTP unique: `app/server.py`
  - orchestration chat: `app/core/`
  - memoire + summaries + arbiter + writes identitaires: `app/memory/`
  - identite runtime et gouvernance: `app/identity/`
  - settings/runtime/admin/memory dashboard: `app/admin/`
  - observabilite par tour et par stage: `app/observability/`
- Frontend:
  - chat principal: `app/web/index.html`, `app/web/app.js`, `app/web/whisper/`
  - admin settings: `app/web/admin.html`, `app/web/admin.js`
  - logs: `app/web/log.html`, `app/web/log/log.js`
  - hermeneutic admin: `app/web/hermeneutic-admin.html`, `app/web/hermeneutic_admin/`
  - identity: `app/web/identity.html`, `app/web/identity/`
  - memory admin: `app/web/memory-admin.html`, `app/web/memory_admin/`
- Documentation:
  - `app/docs/states/`: references stables
  - `app/docs/todo-done/`: audits, notes, validations, archives produit
  - `app/docs/todo-todo/`: chantiers actifs bornes

### 5.2 Modules lourds a surveiller / Heavy modules to watch

| Fichier | Lignes |
| --- | ---: |
| `app/minimal_validation.py` | 1544 |
| `app/web/admin.js` | 1346 |
| `app/web/app.js` | 1291 |
| `app/server.py` | 1278 |
| `app/admin/runtime_settings.py` | 1125 |
| `app/memory/memory_store.py` | 696 |
| `app/web/log/log.js` | 565 |

Lecture / Reading:
- le poids principal s'est deplace vers des facades HTTP/runtime/frontend plus nombreuses, pas vers un unique monolithe historique;
- `app/web/app.js` est maintenant lui aussi une surface structurante, car il porte streaming, rehydratation, Whisper, threads et contrat chat principal.

### 5.3 Tests et preuves de contrat / Tests and contract evidence

- `84` fichiers Python `test_*.py` sous `app/tests/`
- `3` fichiers JS `test_*.js`
- La couverture relevante pour le current-state comprend notamment:
  - streaming serveur/frontend/logs;
  - surfaces admin identite/memoire;
  - prompts/gardes chat;
  - pipeline memoire/RAG et filtrage des traces;
  - route Whisper `/api/chat/transcribe`.

## 6. Pipeline runtime actuel / Current runtime pipeline

Le schema "one-glance" compagnon vit ici / The companion one-glance schema lives here:
- `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`

Chaine runtime utile / Practical runtime chain:

| Etape / Stage | Modules courants | Ce que le repo fait reellement |
| --- | --- | --- |
| HTTP + session | `app/server.py`, `app/core/chat_service.py`, `app/core/chat_session_flow.py` | valide `message`, `conversation_id`, `stream`, `web_search`, `input_mode`; cree ou recharge la conversation; persiste le tour user |
| Grounding + systeme augmente | `app/core/chat_prompt_context.py` | construit system prompt + bloc identitaire + reference temporelle + gardes locales |
| Memoire / arbitrage | `app/core/chat_memory_flow.py`, `app/memory/memory_store.py`, `app/memory/arbiter.py`, `app/memory/memory_pre_arbiter_basket.py`, `app/memory/memory_traces_summaries.py` | recupere traces et summaries, construit le panier pre-arbitre, arbitre selon le mode hermeneutique, selectionne candidats prompt et context hints |
| Pipeline hermeneutique | `app/core/stimmung_agent.py`, `app/core/hermeneutic_node/runtime/primary_node.py`, `app/core/hermeneutic_node/validation/validation_agent.py`, `app/observability/hermeneutic_node_logger.py` | calcule signal affectif, verdict primaire, validation finale et projection `[JUGEMENT HERMENEUTIQUE]` |
| Web et gardes chat | `app/core/chat_prompt_context.py`, `app/tools/web_search.py` | injecte garde lecture web, garde revelation identitaire directe, garde voix, contrat texte brut, et contexte web si activation `manual`/`auto` |
| Appel LLM principal | `app/core/chat_llm_flow.py`, `app/core/llm_client.py`, `app/core/assistant_output_contract.py` | appelle OpenRouter avec identite `caller=llm`; normalise/bufferise selon la politique de sortie |
| Streaming public | `app/core/chat_stream_control.py`, `app/server.py`, `app/web/app.js` | expose `text/plain; charset=utf-8` + terminal unique inline `RS + JSON + LF`; parse cote navigateur; distingue `done`, `error`, `network_error` (inference client-side) |
| Persistance canonique | `app/core/chat_llm_flow.py`, `app/core/assistant_turn_state.py`, `app/core/conversations_prompt_window.py` | `done` persiste un vrai assistant complet; `error` persiste un marqueur assistant interrompu vide; les interruptions sont exclues du prompt canonique |
| Memoire derivee | `app/memory/memory_store.py`, `app/memory/memory_traces_summaries.py` | `save_new_traces()` ne part qu'apres `done` canonique; les marqueurs interrompus et fragments rollbackes n'entrent pas dans traces |
| Frontend render / rehydratation | `app/web/app.js` | rend la bulle assistant, les etats stream, utilise `terminal.updated_at` si disponible, rehydrate le thread si necessaire, et relit `assistant_turn` au reload |
| Observabilite operateur | `app/observability/chat_turn_logger.py`, `app/observability/hermeneutic_node_logger.py`, `/log`, `/hermeneutic-admin`, `/memory-admin` | suit les turns, etapes hermeneutiques, provider metadata, stats stream et surfaces d'inspection |

## 7. Frontieres reelles et couplages restants / Real boundaries and remaining couplings

- `app/server.py` reste la facade la plus transversale:
  - bootstrap runtime;
  - garde admin proxy-first;
  - `/api/chat`, `/api/chat/transcribe`, routes conversations;
  - routes admin settings/logs/hermeneutics/memory;
  - routage statique des surfaces web.
- `app/admin/runtime_settings.py` reste une facade epaisse malgre le split `spec` / `validation` / `sql`.
- `app/web/app.js` reste un point de convergence fort entre chat, threads, streaming, Whisper, rehydratation et UX premier-party.
- `app/memory/memory_store.py` reste une facade publique dense, meme si l'implementation a ete reventilee vers des blocs pipeline-first.
- La securite admin actuelle est plus forte que celle du 03/04, mais elle reste bien runtime-dependent:
  - resolution dynamique des IPs du proxy de confiance;
  - dependance au header `Remote-User`;
  - loopback autorise pour les preuves techniques.

## 8. Risques et points de vigilance / Risks and watchpoints

- Ne pas decrire `FridaDev` comme une architecture a couches strictes deja propre: le repo a clarifie ses seams, mais pas elimine ses facades lourdes.
- Ne pas confondre le state du 03/04/2026 avec l'etat courant: les documents `Frida-State-*03-04-26.md` restent des jalons historiques, pas le resume complet du repo du 16/04.
- Ne pas rouvrir les chantiers clos (Lot 9, streaming 0->7, roadmaps archivees) sans motif explicite: l'audit s'appuie dessus, il ne les requalifie pas en TODO actives.
- Finding arbiter requalifie:
  - `record_arbiter_decisions()` ne doit plus etre presente comme finding actif: le modele effectif est capture/passe jusqu'a la persistence et le cas de changement de runtime setting entre generation et insert DB est couvert par test.

## 9. Suites recommandees / Recommended next steps

### FR

1. Utiliser cet audit et la cartographie pipeline comme points d'entree current-state, et laisser les etats `03/04/2026` jouer leur role de jalons historiques.
2. Conserver les tests de provenance du modele arbitre comme garde; ne rouvrir ce finding que sur regression prouvee.
3. Continuer a desepaissir les facades les plus lourdes (`server.py`, `runtime_settings.py`, `app.js`, `admin.js`) par tranches bornees, sans rouvrir les chantiers streaming ou doctrinaux clos.
4. Garder les index docs synchronises avec les references stables (`audit`, `pipeline`, `spec streaming`, `Memory Admin`, migration OVH).

### EN

1. Use this audit and the pipeline cartography as the current-state entry points, and keep the dated `03/04/2026` states as historical milestones.
2. Address the active arbiter-model provenance finding as a separate bounded task.
3. Keep thinning the heaviest facades (`server.py`, `runtime_settings.py`, `app.js`, `admin.js`) in narrow slices, without reopening closed streaming or doctrinal workstreams.
4. Keep the doc indexes aligned with the stable references (`audit`, `pipeline`, `streaming spec`, `Memory Admin`, OVH migration trace).

## 10. References code / tests / docs

- Docs et histoire:
  - `app/docs/states/project/Frida-State-french-03-04-26.md`
  - `app/docs/states/project/Frida-State-english-03-04-26.md`
  - `app/docs/states/specs/streaming-protocol.md`
  - `app/docs/states/architecture/memory-rag-current-pipeline-cartography.md`
  - `app/docs/todo-done/migrations/fridadev-to-frida-system-migration-todo.md`
- Code:
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
  - `app/memory/arbiter.py`
  - `app/memory/memory_traces_summaries.py`
  - `app/observability/hermeneutic_node_logger.py`
  - `app/web/app.js`
- Tests de contrat utiles:
  - `app/tests/test_server_phase14.py`
  - `app/tests/test_server_logs_phase3.py`
  - `app/tests/test_server_phase13.py`
  - `app/tests/unit/chat/test_chat_llm_flow.py`
  - `app/tests/unit/chat/test_chat_stream_control.py`
  - `app/tests/integration/frontend_chat/test_frontend_chat_contract.py`
  - `app/tests/integration/frontend_chat/test_frontend_whisper_contract.py`
  - `app/tests/unit/frontend_chat/test_stream_control_parser_module.js`
  - `app/tests/unit/frontend_chat/test_streaming_ui_state_module.js`
  - `app/tests/unit/memory/test_memory_store_blocks_phase8bis.py`
