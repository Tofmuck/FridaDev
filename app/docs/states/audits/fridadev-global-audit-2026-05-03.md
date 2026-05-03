# Audit global FridaDev - 2026-05-03

## Resume executif

- statut global: repo exploitable et globalement coherent apres le chantier de nettoyage, mais deux coutures centrales peuvent encore produire une verite runtime trompeuse: persistance conversationnelle et ecriture des settings.
- niveau de risque: eleve mais bornable par lots courts.
- nombre de findings confirmes: 9.
- nombre de findings probables: 0.
- zones saines: garde admin OVH proxy-first, injection hermeneutique finale, surface identity static/mutable/staging, redaction des secrets admin, parser de stream frontend, tests runtime representatifs.
- zones les plus risquees: persistance canonique des tours, validation serveur des runtime settings, observabilite des erreurs memoire, tests frontend sans vrai navigateur.

## Methode

- commit audite: `7cc7cea5eba5a1c61d33e743a61b515417be7cb6`.
- environnement: OVH, depot `/opt/platform/fridadev`, app compose `/opt/platform/fridadev-app`, conteneur `platform-fridadev`, date `2026-05-03`, timezone `Etc/UTC`.
- sources lues:
  - `AGENTS.md`
  - `README.md`
  - `app/docs/README.md`
  - `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`
  - `app/docs/todo-done/audits/fridadev_repo_audit.md`
  - `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
  - `app/docs/states/specs/response-arbiter-power-contract.md`
  - `app/docs/states/policies/identity-new-contract-plan.md`
  - `app/docs/todo-done/refactors/identity-new-contract-todo.md`
  - `app/docs/states/specs/memory-admin-surface-contract.md`
  - `app/docs/states/specs/streaming-protocol.md`
  - `app/docs/todo-done/migrations/fridadev-to-frida-system-migration-todo.md`
  - code backend: `app/server.py`, `app/core/`, `app/memory/`, `app/identity/`, `app/admin/`, `app/observability/`, `app/config.py`, `app/minimal_validation.py`
  - frontend: `app/web/app.js`, `app/web/chat_streaming.js`, `app/web/chat_threads_sidebar.js`, `app/web/admin*.js`, `app/web/admin_section_*.js`, `app/web/hermeneutic_admin/`, `app/web/index.html`, `app/web/admin.html`
  - tests: `app/tests/`, `app/tests/unit/`, `app/tests/integration/`, `app/tests/support/`
  - docs: `app/docs/states/`, `app/docs/todo-todo/`, `app/docs/todo-done/`
- commandes executees:
  - `git fetch origin main`
  - `git pull --ff-only origin main`
  - `git status --short`
  - `git rev-parse HEAD`
  - `git rev-parse origin/main`
  - `find app -type f | sort`
  - `find app/docs -type f | sort`
  - `find app/tests -type f | sort`
  - `rg -n "TODO|FIXME|HACK|XXX|pass #|except Exception|except:|fallback|legacy|deprecated|not implemented|no_go|FRIDA_ADMIN_TOKEN|record_arbiter_decisions|secret|token|password|DSN" app README.md AGENTS.md -S`
  - `rg -n "def |class |@app\\.route|Blueprint|fetch\\(|addEventListener|localStorage|sessionStorage|console\\.|window\\." app -S`
  - `wc -l app/server.py app/core/*.py app/admin/*.py app/memory/*.py app/observability/*.py app/web/*.js app/tests/*.py`
  - `git ls-files`
  - `docker compose up -d --build fridadev`
  - probes non-mutateurs sur `normalize_admin_patch_payload()` et `conversations_store.save_conversation()`
  - `docker ps --filter name=platform-fridadev --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"`
  - `curl --max-time 12 -sSI https://fridadev.frida-system.fr/admin | sed -n '1,12p'`
- tests executes:
  - `docker exec platform-fridadev python tests/test_server_chat_route_transport_contract.py`
  - `docker exec platform-fridadev python tests/test_server_chat_hermeneutic_insertion_contract.py`
  - `docker exec platform-fridadev python tests/test_server_chat_web_runtime_contract.py`
  - `docker exec platform-fridadev python tests/test_server_chat_compact_observability_contract.py`
  - `docker exec platform-fridadev python tests/test_server_chat_synthetic_logs_contract.py`
  - `docker exec platform-fridadev python tests/test_server_chat_conversation_id_contract.py`
  - `docker exec platform-fridadev python tests/integration/chat/test_chat_input_mode_route.py`
  - `docker exec platform-fridadev python tests/test_server_admin_settings_read_contract.py`
  - `docker exec platform-fridadev python tests/test_server_admin_settings_patch_contract.py`
  - `docker exec platform-fridadev python tests/test_server_admin_settings_validate_contract.py`
  - `docker exec platform-fridadev python tests/test_server_admin_non_settings_contracts.py`
  - `docker exec platform-fridadev python tests/test_server_admin_identity_read_model_phase2.py`
  - `docker exec platform-fridadev python tests/test_server_admin_identity_mutable_edit_phase3.py`
  - `docker exec platform-fridadev python tests/test_server_admin_identity_static_edit_phase4.py`
  - `docker exec platform-fridadev python tests/test_server_admin_identity_governance_phase5.py`
  - `docker exec platform-fridadev python tests/test_server_admin_identity_surface_phase6.py`
  - `docker exec platform-fridadev python tests/test_server_admin_hermeneutics_phase4.py`
  - `docker exec platform-fridadev python tests/test_server_admin_memory_surface_phase10e.py`
  - `docker exec platform-fridadev python tests/test_server_admin_chat_logs_contract.py`
  - `docker exec platform-fridadev python tests/test_server_logs_phase3.py`
  - `docker exec platform-fridadev python tests/integration/frontend_chat/test_frontend_chat_contract.py`
  - `docker exec platform-fridadev python tests/integration/frontend_admin/test_frontend_admin_contract.py`
  - `docker exec platform-fridadev python tests/integration/frontend_admin/test_frontend_logs_phase5.py`
  - `docker exec platform-fridadev python tests/integration/frontend_admin/test_frontend_hermeneutic_admin_phase6.py`
  - `docker exec platform-fridadev python tests/test_memory_store_phase4.py`
  - `docker exec platform-fridadev python tests/unit/memory/test_memory_store_blocks_phase8bis.py`
  - `node --test app/tests/unit/frontend_chat/test_stream_control_parser_module.js`
  - `node --test app/tests/unit/frontend_chat/test_streaming_ui_state_module.js`
  - `node --test app/tests/unit/frontend_chat/test_threads_sidebar_module.js`
- tests non executes et pourquoi:
  - pas de suite complete exhaustive: la demande etait une selection representative, et la selection obligatoire a passe.
  - pas de test navigateur Playwright: aucun harness navigateur n'est configure dans le repo courant; le risque est note comme finding.
  - pas de PATCH settings live invalide: cela aurait modifie la configuration runtime; la preuve est limitee a la normalisation non-mutatrice et a la lecture de code.
  - pas de lecture de secrets runtime ni de `.env`: interdit par contrat securite.

## Findings prioritaires

### P0 - Bloquant

- Aucun P0 confirme.

### P1 - Critique

- `AUDIT-20260503-001` - La sauvegarde conversationnelle peut echouer silencieusement pendant que l'API et les logs disent succes.
- `AUDIT-20260503-002` - Le chemin non-stream persiste traces et identite avant la sauvegarde canonique du message assistant.
- `AUDIT-20260503-003` - Le PATCH admin settings accepte des valeurs semantiquement invalides; la validation est consultative, pas bloquante.

### P2 - Important

- `AUDIT-20260503-004` - Un terminal stream avec `updated_at` peut etre emis meme si le marqueur ou le message n'est pas reellement sauvegarde.
- `AUDIT-20260503-005` - Une erreur de retrieval memoire devient ensuite un `no_data` aval et peut masquer l'echec dans les surfaces synthetiques.
- `AUDIT-20260503-006` - Les tests frontend dits integration restent surtout des assertions de source, sans preuve navigateur des transitions critiques.

### P3 - Moyen / dette

- `AUDIT-20260503-007` - Les anciens knobs admin `FRIDA_ADMIN_TOKEN` / LAN restent dans la config active malgre le contrat OVH sans token humain.
- `AUDIT-20260503-008` - Le finding `record_arbiter_decisions()` est corrige dans le code teste, mais reste presente comme actif dans plusieurs docs de pilotage.
- `AUDIT-20260503-009` - La spec `admin-runtime-settings-schema.md` decrit encore une V1 plus petite que le schema runtime reel.

## Findings detailles

### AUDIT-20260503-001 - Persistance conversationnelle fail-soft mais succes annonce

- severite: P1
- statut: confirme
- domaine: Persistence / transactions, Observabilite / logs, Contrats produit
- fichiers:
  - `app/core/conversations_store.py`
  - `app/server.py`
  - `app/core/chat_llm_flow.py`
- lignes:
  - `app/core/conversations_store.py:562-591`
  - `app/server.py:297-306`
  - `app/core/chat_llm_flow.py:370-419`
- description:
  - `save_conversation()` appelle `upsert_conversation_catalog_func()` puis `upsert_conversation_messages_func()`, mais ne remonte pas l'echec: un `None` catalog ou un `False` messages ne bloque pas le flux.
  - Le proxy serveur emet ensuite `persist_response` avec `status=ok` sans verifier que la sauvegarde DB a vraiment reussi.
  - Le flux chat peut donc retourner un `200`, un terminal `done/error` et un `updated_at` qui ressemblent a une persistance canonique, alors que la table messages peut ne pas avoir ete mise a jour.
- preuve:
  - Lecture de code: `conversations_store.save_conversation()` log seulement `conv_messages_write_failed` puis retourne.
  - Probe non-mutateur execute dans le conteneur: avec `upsert_conversation_catalog_func=lambda ...: None` et `upsert_conversation_messages_func=lambda ...: False`, `save_conversation()` retourne sans exception et met `updated_at`.
  - Les tests obligatoires passent, ce qui confirme que ce chemin n'est pas actuellement bloque par la suite.
- impact:
  - perte apparente de message sans erreur utilisateur claire;
  - logs `persist_response` mensongers;
  - frontend pouvant croire a une rehydratation possible via `updated_at` alors que la source canonique n'a pas le message;
  - diagnostic operateur difficile, car le symptome arrive apres coup sur `/log`, `/memory-admin` ou les conversations.
- recommandation:
  - faire retourner un resultat structure par `save_conversation()` avec statut catalog/messages;
  - faire echouer `/api/chat` ou emettre un terminal `error` sans `updated_at` si la sauvegarde canonique echoue;
  - n'emettre `persist_response ok` qu'apres preuve de sauvegarde messages;
  - distinguer dans les logs `catalog_saved`, `messages_saved`, `messages_failed`.
- tests a ajouter ou modifier:
  - test unitaire `conversations_store.save_conversation()` qui exige un statut explicite quand l'upsert messages echoue;
  - test `/api/chat` non-stream et stream ou `conv_store.save_conversation` simule un echec messages et verifie absence de `ok` mensonger;
  - test `chat_turn_logger` prouvant `persist_response error`.
- ordre de correction suggere: lot 1, avant tout chantier memoire derivee.

### AUDIT-20260503-002 - Traces et identite non-stream avant sauvegarde canonique

- severite: P1
- statut: confirme
- domaine: Memoire / RAG / arbiter, Identite, Persistence / transactions
- fichiers:
  - `app/core/chat_llm_flow.py`
  - `app/memory/memory_traces_summaries.py`
  - `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`
  - `app/docs/states/specs/streaming-protocol.md`
- lignes:
  - `app/core/chat_llm_flow.py:146-168`
  - `app/memory/memory_traces_summaries.py:656-725`
  - `app/docs/states/architecture/fridadev-current-runtime-pipeline.md:67-70`
  - `app/docs/states/specs/streaming-protocol.md:240-246`
- description:
  - Dans le chemin JSON non-stream, le message assistant est append en memoire, puis `save_new_traces()` et `record_identity_entries_for_mode()` sont appeles avant `conv_store.save_conversation()`.
  - Les docs runtime disent que `save_new_traces()` arrive seulement apres sauvegarde canonique.
  - Si la sauvegarde conversationnelle echoue apres les traces ou l'identite, les donnees derivees peuvent exister sans message assistant canonique correspondant.
- preuve:
  - Lecture de code: `save_new_traces()` ligne 155 et identite lignes 156-165 precedent `save_conversation()` ligne 168.
  - Le chemin stream nominal est mieux ordonne: `save_conversation()` ligne 370 puis `save_new_traces()` lignes 411-412.
- impact:
  - memoire RAG pouvant se souvenir d'une reponse qui n'existe pas dans la conversation canonique;
  - staging identitaire et diagnostics legacy pouvant etre alimentes par une paire non sauvegardee;
  - incoherence entre `/memory-admin`, `/identity`, `/log` et l'historique conversationnel.
- recommandation:
  - aligner non-stream sur stream: sauvegarde canonique verifiee avant traces et identite;
  - rendre les ecritures derivees dependantes d'un resultat de persistance conversationnelle explicite;
  - si l'ecriture derivee echoue apres le save canonique, journaliser une erreur derivee sans invalider le message.
- tests a ajouter ou modifier:
  - test `chat_llm_flow` non-stream qui enregistre la sequence attendue `save_conversation -> save_new_traces -> identity`;
  - test simulant `save_conversation` en echec et verifiant qu'aucune trace ni identite n'est persistee.
- ordre de correction suggere: lot 2, juste apres le statut explicite de persistance.

### AUDIT-20260503-003 - PATCH settings sans validation semantique bloquante

- severite: P1
- statut: confirme
- domaine: Runtime settings, Frontend admin, Securite / admin OVH
- fichiers:
  - `app/admin/admin_settings_service.py`
  - `app/admin/runtime_settings_write_path.py`
  - `app/admin/runtime_settings_validation.py`
  - `app/web/admin_section_main_model.js`
  - `app/web/admin_section_embedding.js`
- lignes:
  - `app/admin/admin_settings_service.py:35-72`
  - `app/admin/runtime_settings_write_path.py:110-190`
  - `app/admin/runtime_settings_validation.py:151-160`
  - `app/web/admin_section_main_model.js:351-358`
  - `app/web/admin_section_embedding.js:326-333`
- description:
  - Les sections admin executent bien une validation frontend avant `patchSection()`.
  - Le backend `PATCH /api/admin/settings/<section>` appelle directement `update_runtime_section()` sans imposer `validate_runtime_section()`.
  - `normalize_admin_patch_payload()` ne verifie que type/forme/chiffrement secret; les bornes metier (`top_p`, `temperature`, URL, model non vide, timeout positif, etc.) vivent dans `/validate`.
  - Un client direct peut donc persister un `top_p=2.0` ou `temperature=3.0` alors que la validation les refuse.
- preuve:
  - Lecture de code: `patch_section_response()` lignes 50-55 ne fait aucun appel a `validate_runtime_section()`.
  - Probe non-mutateur dans le conteneur: `normalize_admin_patch_payload('main_model', {'top_p': {'value': 2.0}, 'temperature': {'value': 3.0}})` retourne les valeurs hors bornes.
  - Les tests `test_server_admin_settings_patch_contract.py` couvrent payload malformed/readonly/secrets, pas les invariants semantiques hors bornes.
- impact:
  - admin API et UI peuvent diverger: l'UI promet une validation, l'API source-of-truth ne la garantit pas;
  - settings runtime invalides peuvent casser appels LLM, embeddings ou services externes;
  - l'historique settings peut enregistrer une configuration invalide comme modification admin normale.
- recommandation:
  - faire de `validate_runtime_section(section, patch_payload)` un pre-requis du PATCH;
  - refuser un PATCH si `valid=False`, avec details de checks;
  - ajouter une option explicite si un jour un bypass operateur est voulu, mais pas par defaut.
- tests a ajouter ou modifier:
  - tests PATCH directs sur `main_model.top_p=2`, `temperature=3`, `model=""`;
  - tests PATCH sur `validation_agent_model.max_tokens` au-dessus du cap;
  - tests garantissant aucune ecriture DB/history quand la validation echoue.
- ordre de correction suggere: lot 3.

### AUDIT-20260503-004 - Terminal stream `updated_at` possible sans persistance prouvee

- severite: P2
- statut: confirme
- domaine: Frontend chat, Persistence / transactions, Observabilite / logs
- fichiers:
  - `app/core/chat_llm_flow.py`
  - `app/server.py`
  - `app/web/app.js`
  - `app/docs/states/specs/streaming-protocol.md`
- lignes:
  - `app/core/chat_llm_flow.py:371-419`
  - `app/server.py:576-665`
  - `app/web/app.js:299-315`
  - `app/web/app.js:323-337`
  - `app/docs/states/specs/streaming-protocol.md:226-229`
- description:
  - Le contrat streaming dit que `terminal.updated_at` sur `done` ou `error` represente le timestamp du message ou marqueur persiste.
  - Le serveur peut emettre un terminal avec `updated_at` depuis `final_updated_at` meme si la persistance conversationnelle sous-jacente n'a pas prouve la sauvegarde messages.
  - Le frontend applique ce `updated_at`, ajoute au cache local un assistant normal ou interrompu, puis ne force pas toujours la rehydratation.
- preuve:
  - Le chemin finalize construit le terminal lignes 415-419.
  - `app/web/app.js` utilise `hasReplyUpdatedAt` pour eviter la rehydratation forcee lignes 299-315.
  - Le catch stream ajoute un marqueur interrompu en cache si `errorTerminal.updated_at` existe lignes 329-336.
  - Ce finding est amplifie par `AUDIT-20260503-001`.
- impact:
  - cache frontend et conversation DB peuvent diverger;
  - l'utilisateur voit un tour qui semble canonique, mais une recharge serveur peut le faire disparaitre;
  - `/log` peut raconter une interruption ou une sauvegarde sans source conversationnelle correspondante.
- recommandation:
  - ne jamais emettre `updated_at` tant que la sauvegarde canonique n'a pas ete prouvee;
  - en cas d'echec de sauvegarde, terminal `error` sans `updated_at` + rehydratation forcee frontend;
  - ajouter un champ terminal optionnel `persisted=true|false` si le protocole doit rester explicite.
- tests a ajouter ou modifier:
  - test stream ou `upsert_conversation_messages` echoue silencieusement: terminal sans `updated_at`;
  - test frontend sur terminal error sans `updated_at`: rehydratation forcee et pas d'ajout cache canonique.
- ordre de correction suggere: lot 4, apres correction de la persistance.

### AUDIT-20260503-005 - Retrieval memoire fail-open requalifie en `no_data` aval

- severite: P2
- statut: confirme
- domaine: Memoire / RAG / arbiter, Observabilite / logs, Logique metier
- fichiers:
  - `app/memory/memory_traces_summaries.py`
  - `app/core/chat_memory_flow.py`
- lignes:
  - `app/memory/memory_traces_summaries.py:740-744`
  - `app/memory/memory_traces_summaries.py:757-769`
  - `app/memory/memory_traces_summaries.py:812-825`
  - `app/core/chat_memory_flow.py:427-455`
- description:
  - `retrieve()` documente et implemente un fail-open: en cas d'erreur embedding ou DB, il logge `memory_retrieve status=error` puis retourne `[]`.
  - Le niveau appelant recoit seulement une liste vide et emet ensuite `arbiter` skipped avec `reason_code='no_data'`.
  - L'echec technique initial et l'absence reelle de memoire deviennent donc difficiles a distinguer dans les payloads aval, sauf correlation fine des logs.
- preuve:
  - Les tests runtime obligatoires passent avec de nombreux `retrieve_embed_failed` dans la sortie, ce qui montre que le flux produit quand meme des reponses valides.
  - Lecture de code: `retrieve()` retourne `[]` sur erreurs, puis `chat_memory_flow` construit `memory_arbitration status='skipped', reason_code='no_data'`.
- impact:
  - Frida peut repondre sans memoire alors qu'une erreur technique a eu lieu, sans que le tour final porte explicitement "memoire indisponible";
  - `/memory-admin` ou `/hermeneutic-admin` peuvent resumer une absence plutot qu'une indisponibilite;
  - les regressions embeddings/DB peuvent rester discretes si personne ne lit le stage `memory_retrieve`.
- recommandation:
  - faire remonter un statut structure `retrieval_status=ok|empty|error`;
  - propager `reason_code='retrieve_error'` dans `memory_arbitration` et `prompt_prepared`;
  - conserver le fail-open produit si voulu, mais rendre l'indisponibilite visible.
- tests a ajouter ou modifier:
  - test `prepare_memory_context()` avec `retrieve()` en erreur: `memory_arbitration.reason_code == 'retrieve_error'`;
  - test `/memory-admin` qui distingue `no_data` de `retrieve_error`;
  - test `prompt_prepared.memory_prompt_injection` avec statut memoire.
- ordre de correction suggere: lot 5.

### AUDIT-20260503-006 - Tests frontend integration sans navigateur reel

- severite: P2
- statut: confirme
- domaine: Tests, Frontend chat, Frontend admin
- fichiers:
  - `app/tests/integration/frontend_chat/test_frontend_chat_contract.py`
  - `app/tests/integration/frontend_admin/test_frontend_admin_contract.py`
  - `app/tests/integration/frontend_admin/test_frontend_logs_phase5.py`
  - `app/tests/integration/frontend_admin/test_frontend_hermeneutic_admin_phase6.py`
- lignes:
  - `app/tests/integration/frontend_chat/test_frontend_chat_contract.py:20-260`
  - `app/tests/integration/frontend_admin/test_frontend_admin_contract.py:21-260`
  - `app/tests/integration/frontend_admin/test_frontend_logs_phase5.py:50-108`
  - `app/tests/integration/frontend_admin/test_frontend_hermeneutic_admin_phase6.py:21-188`
- description:
  - Beaucoup de tests "integration frontend" lisent les fichiers HTML/JS et cherchent des chaines.
  - Les trois tests Node couvrent correctement des modules purs (`chat_streaming`, state machine, sidebar), mais pas l'experience browser complete.
  - Les interactions critiques restent non prouvees en navigateur: stream live, catch terminal, cache/hydratation, navigation admin, save/validate, logs filters/export.
- preuve:
  - Les tests frontend chat/admin passent en quelques millisecondes car ils n'ouvrent pas de DOM navigateur complet.
  - Les assertions visibles sont du type `read_text()` + `assertIn` / `assertNotIn`.
- impact:
  - les tests peuvent passer si un ordre de scripts, un event listener, une race de cache ou un comportement `fetch` casse en vrai navigateur;
  - les regressions UI admin peuvent etre detectees tardivement, surtout sur les transitions validate -> patch -> status.
- recommandation:
  - ajouter un petit harness navigateur (Playwright ou equivalent) limite a 4 parcours:
    - chat stream done;
    - chat stream error terminal sans `updated_at`;
    - admin settings validation + save refuse;
    - logs metadata/filter/export;
  - conserver les tests source comme garde de structure, mais ne plus les appeler seuls "integration" pour les contrats UX.
- tests a ajouter ou modifier:
  - smoke browser chat avec `fetch` mocke;
  - smoke browser admin settings avec responses mockees;
  - test de rehydratation apres terminal sans `updated_at`.
- ordre de correction suggere: lot 6, apres stabilisation persistence/stream.

### AUDIT-20260503-007 - Knobs admin token/LAN obsoletes encore actifs dans la config

- severite: P3
- statut: confirme
- domaine: Securite / admin OVH, Config / environnement / deploiement, Documentation / specs
- fichiers:
  - `app/server.py`
  - `app/config.py`
  - `app/config.example.py`
  - `AGENTS.md`
  - `app/docs/todo-done/migrations/fridadev-to-frida-system-migration-todo.md`
- lignes:
  - `app/server.py:120-193`
  - `app/config.py:136-142`
  - `app/config.example.py:82-88`
  - `AGENTS.md:98-107`
  - `app/docs/todo-done/migrations/fridadev-to-frida-system-migration-todo.md:887-908`
- description:
  - Le code serveur courant preserve le contrat OVH: `/api/admin/*` exige loopback ou proxy de confiance + `Remote-User`.
  - Pourtant `FRIDA_ADMIN_TOKEN`, `FRIDA_ADMIN_LAN_ONLY` et `FRIDA_ADMIN_ALLOWED_CIDRS` restent dans `config.py` et `config.example.py`.
  - Ils ne semblent plus piloter le garde courant, mais leur presence active entretient une ambiguite operateur.
- preuve:
  - Lecture de code du garde: aucune branche token, seulement proxy/loopback.
  - Test live public `/admin`: `HTTP/2 302` vers Authelia.
  - Tests admin guard existants couvrent `Remote-User` et proxy de confiance.
- impact:
  - risque de reconfiguration inutile ou de reintroduction future du token humain;
  - onboarding operateur plus confus;
  - docs historiques plus difficiles a distinguer du contrat actif.
- recommandation:
  - supprimer ces variables si aucun consommateur runtime ne reste;
  - ou les marquer explicitement `obsolete_do_not_use` dans config/docs;
  - ajouter un test source qui interdit toute lecture de `FRIDA_ADMIN_TOKEN` dans le garde.
- tests a ajouter ou modifier:
  - test grep/source sur `server.py` qui confirme absence de `FRIDA_ADMIN_TOKEN` / `X-Admin-Token`;
  - test config/docs apres retrait.
- ordre de correction suggere: lot 7.

### AUDIT-20260503-008 - Finding `record_arbiter_decisions()` stale mais encore annonce actif

- severite: P3
- statut: confirme
- domaine: Documentation / specs, Memoire / RAG / arbiter, Tests
- fichiers:
  - `AGENTS.md`
  - `app/docs/todo-done/audits/fridadev_repo_audit.md`
  - `app/docs/todo-done/refactors/fridadev-repo-cleanup-prioritized-todo.md`
  - `app/memory/arbiter.py`
  - `app/memory/memory_arbiter_audit.py`
  - `app/tests/test_memory_store_phase4.py`
  - `app/tests/unit/memory/test_memory_store_blocks_phase8bis.py`
- lignes:
  - `AGENTS.md:186-190`
  - `app/docs/todo-done/audits/fridadev_repo_audit.md:162-170`
  - `app/memory/arbiter.py:321-322`
  - `app/memory/arbiter.py:488`
  - `app/memory/memory_arbiter_audit.py:39-51`
  - `app/tests/test_memory_store_phase4.py:617-725`
  - `app/tests/unit/memory/test_memory_store_blocks_phase8bis.py:234-272`
- description:
  - Le finding ancien disait que `record_arbiter_decisions()` pouvait relire un modele stale si le setting changeait entre appel LLM et insert DB.
  - Le code courant capture le modele dans `arbiter.filter_traces_with_diagnostics()`, l'attache aux decisions, et `memory_arbiter_audit` accepte un `effective_model`.
  - Les tests dedies simulent le changement de setting et prouvent la persistance du modele effectif.
  - Le probleme actuel est donc documentaire: plusieurs sources continuent a le presenter comme actif.
- preuve:
  - Tests `tests/test_memory_store_phase4.py` et `tests/unit/memory/test_memory_store_blocks_phase8bis.py` executes: OK.
  - Lecture de code confirme `model` attache aux decisions et fallback `effective_model`.
- impact:
  - risque de reouvrir un chantier deja corrige;
  - perte de confiance dans la liste des findings actifs;
  - risque de corriger deux fois et de complexifier le seam.
- recommandation:
  - requalifier le finding comme stale/faux positif dans les docs de pilotage;
  - conserver un micro-point ouvert seulement si l'on veut supprimer la compatibilite `TypeError` legacy de `chat_memory_flow`.
- tests a ajouter ou modifier:
  - aucun test fonctionnel obligatoire: les tests actuels couvrent le coeur.
  - eventuellement un test de route complete `prepare_memory_context()` qui verifie que le modele present dans les decisions est celui persiste.
- ordre de correction suggere: lot doc court, independant des P1.

### AUDIT-20260503-009 - Spec runtime settings V1 plus petite que le schema reel

- severite: P3
- statut: confirme
- domaine: Documentation / specs, Runtime settings, Frontend admin
- fichiers:
  - `app/docs/states/specs/admin-runtime-settings-schema.md`
  - `app/admin/runtime_settings_spec.py`
  - `app/docs/states/baselines/database-schema-baseline.md`
- lignes:
  - `app/docs/states/specs/admin-runtime-settings-schema.md:11-18`
  - `app/admin/runtime_settings_spec.py:7-18`
- description:
  - La spec runtime settings V1 liste encore les sections initiales sans `stimmung_agent_model`, `validation_agent_model` ni `identity_governance`.
  - Le code runtime expose desormais ces sections dans `SECTION_NAMES`.
  - Ce n'est pas un bug runtime, mais une spec vivante devenue partiellement stale.
- preuve:
  - Lecture comparee de la spec et du code.
  - Les tests admin settings read/patch/validate passent pour les sections extraites et nouvelles.
- impact:
  - un correcteur peut croire qu'une section runtime est hors contrat alors qu'elle est active;
  - risque de docs operateur ou schema SQL incomplets;
  - surface admin plus difficile a auditer ensuite.
- recommandation:
  - mettre a jour la spec schema pour decrire les sections actives et leur statut UI/API;
  - distinguer les sections `settings` editees dans `/admin` et `identity_governance` pilotee via `/identity`/`/hermeneutic-admin`.
- tests a ajouter ou modifier:
  - test doc/source leger qui compare la liste spec si le repo accepte ce type de garde;
  - sinon checklist docs dans le prochain lot admin settings.
- ordre de correction suggere: lot doc court, apres P1/P2.

## Verifications par domaine

### Logique metier

- ce qui semble sain:
  - le pipeline chat garde une orchestration lisible: session, runtime settings, memoire, stimmung, noeud hermeneutique, gardes prompt, appel LLM.
  - la validation hermeneutique est bien injectee dans le prompt final via `[JUGEMENT HERMENEUTIQUE]`.
  - `input_mode` vocal est persiste dans `message.meta` et injecte une garde specifique.
- findings associes: `AUDIT-20260503-001`, `AUDIT-20260503-002`, `AUDIT-20260503-005`.
- risques residuels:
  - les fallbacks memoire permettent une reponse normale avec contexte degrade.
  - le non-stream reste moins bien ordonne que le stream.
- preuves consultees:
  - `app/core/chat_service.py:192-408`
  - `app/core/chat_llm_flow.py:146-168`
  - `app/core/chat_memory_flow.py:276-474`
  - tests chat obligatoires OK.

### Contrats produit

- ce qui semble sain:
  - `/api/chat` couvre texte, vocal, stream, nouvelle conversation, conversation existante manquante et conversation id invalide selon les tests.
  - le comportement `conversation_id` invalide -> nouvelle conversation est explicite dans les tests actuels, donc classe en non-finding.
  - `/admin`, `/identity`, `/hermeneutic-admin`, `/memory-admin`, `/log` sont routes et coherentes au niveau endpoints.
- findings associes: `AUDIT-20260503-001`, `AUDIT-20260503-003`, `AUDIT-20260503-004`, `AUDIT-20260503-006`.
- risques residuels:
  - le contrat public peut dire "sauvegarde" alors que l'ecriture messages n'est pas prouvee.
  - pas de parcours navigateur complet pour verifier les surfaces.
- preuves consultees:
  - `app/server.py:501-690`
  - `app/core/chat_session_flow.py:19-79`
  - `app/tests/test_server_chat_conversation_id_contract.py`
  - tests frontend integration et Node OK.

### Memoire / RAG / arbiter

- ce qui semble sain:
  - pre-arbiter basket, decisions arbitre, `effective_model` et tests de race modele sont en place.
  - les marqueurs assistant interrompus sont exclus des traces par contrat et tests.
  - Memory Admin expose des agregats utiles.
- findings associes: `AUDIT-20260503-002`, `AUDIT-20260503-005`, `AUDIT-20260503-008`.
- risques residuels:
  - fail-open retrieval encore trop proche d'une absence normale de donnees.
  - traces non-stream peuvent preceder le canon.
- preuves consultees:
  - `app/memory/arbiter.py`
  - `app/memory/memory_arbiter_audit.py`
  - `app/memory/memory_traces_summaries.py`
  - `app/core/chat_memory_flow.py`
  - `tests/test_memory_store_phase4.py` OK
  - `tests/unit/memory/test_memory_store_blocks_phase8bis.py` OK.

### Identite

- ce qui semble sain:
  - separation static/mutable/staging preservee dans les services admin et surfaces.
  - `record_identity_entries_for_mode()` garde le legacy diagnostic distinct et route le canon via staging/periodic agent.
  - surfaces `/identity` et `/hermeneutic-admin` exposent read model, runtime representations, static/mutable edit, governance.
- findings associes: `AUDIT-20260503-002`, `AUDIT-20260503-006`.
- risques residuels:
  - identite non-stream peut etre alimentee avant sauvegarde canonique.
  - pas de preuve navigateur pour edition static/mutable.
- preuves consultees:
  - `app/core/chat_memory_flow.py:477-587`
  - `app/admin/admin_identity_*`
  - tests identity admin phase2-6 OK.

### Hermeneutique

- ce qui semble sain:
  - flux `stimmung_agent -> primary_node -> validation_agent` visible et ordonne.
  - les inputs canoniques sont passes a la validation.
  - la sortie `validated_output` est projetee en bloc final et consommee par le prompt principal.
  - les logs `hermeneutic_node_insertion`, `primary_node`, `validation_agent` restent compacts.
- findings associes: aucun finding direct.
- risques residuels:
  - si validation fail-open produit un bloc vide ou minimal, l'impact final reste a surveiller par tests metier qualitatifs.
- preuves consultees:
  - `app/core/chat_service.py:84-171`
  - `app/core/chat_service.py:300-330`
  - `app/core/chat_prompt_context.py:83-116`
  - `app/observability/hermeneutic_node_logger.py`
  - tests hermeneutic insertion et synthetic logs OK.

### Runtime settings

- ce qui semble sain:
  - lectures, redaction de secrets, backfill, cache invalidation et endpoints read/status sont bien couverts.
  - la validation technique existe et renvoie des checks structures.
- findings associes: `AUDIT-20260503-003`, `AUDIT-20260503-009`.
- risques residuels:
  - PATCH direct contourne les checks semantiques.
  - spec schema partiellement stale.
- preuves consultees:
  - `app/admin/runtime_settings.py`
  - `app/admin/runtime_settings_write_path.py`
  - `app/admin/runtime_settings_validation.py`
  - `app/admin/admin_settings_service.py`
  - tests settings read/patch/validate OK.

### Observabilite / logs

- ce qui semble sain:
  - `chat_turn_logger` bufferise les events tant que la conversation est pending.
  - payloads compacts, previews tronquees et exports markdown evintent les dumps massifs.
  - logs admin et chat log store ont des filtres scopes.
- findings associes: `AUDIT-20260503-001`, `AUDIT-20260503-004`, `AUDIT-20260503-005`.
- risques residuels:
  - `persist_response ok` trop optimiste;
  - `no_data` aval apres erreur retrieval;
  - export markdown compact mais sans politique de classification de contenu utilisateur, donc a relire humainement.
- preuves consultees:
  - `app/observability/chat_turn_logger.py`
  - `app/observability/log_store.py`
  - `app/observability/log_markdown_export.py`
  - tests logs phase3/phase5/phase6 OK.

### Persistence / transactions

- ce qui semble sain:
  - les tables conversation catalog/messages sont separees et le chargement prefere DB.
  - les traces dedoublonnent par conversation/role/content/timestamp.
  - le stream nominal sauvegarde avant traces.
- findings associes: `AUDIT-20260503-001`, `AUDIT-20260503-002`, `AUDIT-20260503-004`.
- risques residuels:
  - absence de transaction unique catalog + messages + traces;
  - fonctions bas niveau qui avalent les exceptions.
- preuves consultees:
  - `app/core/conversations_store.py:284-343`
  - `app/core/conversations_store.py:435-491`
  - `app/core/conversations_store.py:562-591`
  - `app/memory/memory_traces_summaries.py:656-725`.

### Securite / admin OVH

- ce qui semble sain:
  - le garde backend `/api/admin/*` respecte le contrat proxy de confiance + `Remote-User`, avec loopback pour preuves techniques.
  - le frontend admin n'envoie pas `X-Admin-Token`.
  - preuve live `/admin`: redirection Authelia `302`.
- findings associes: `AUDIT-20260503-007`.
- risques residuels:
  - vieux knobs config peuvent induire un futur retour token.
  - les routes HTML statiques reposent sur Authelia public, pas sur un garde backend applicatif, ce qui est conforme au contrat mais reste une dependance plateforme.
- preuves consultees:
  - `app/server.py:120-193`
  - `app/tests/test_server_admin_settings_read_contract.py:718-756`
  - `curl https://fridadev.frida-system.fr/admin` -> `302` Authelia.

### Frontend chat

- ce qui semble sain:
  - parser terminal RS robuste et teste en Node.
  - state machine stream prepare/waiting/streaming/done/interrupted testee.
  - sidebar conversations module testee sur normalisation/titres.
- findings associes: `AUDIT-20260503-004`, `AUDIT-20260503-006`.
- risques residuels:
  - cache local peut croire un terminal `updated_at` sans preuve serveur;
  - pas de test navigateur complet du submit live.
- preuves consultees:
  - `app/web/app.js:264-459`
  - `app/web/chat_streaming.js`
  - `app/web/chat_threads_sidebar.js`
  - 3 tests Node OK.

### Frontend admin

- ce qui semble sain:
  - sections admin chargees dans un ordre explicite.
  - UI valide avant save.
  - secrets utilisent `replace_value`, les champs readonly sont visibles et non patchables cote UI.
- findings associes: `AUDIT-20260503-003`, `AUDIT-20260503-006`, `AUDIT-20260503-009`.
- risques residuels:
  - l'API accepte encore ce que l'UI refuserait;
  - pas de preuve navigateur validate/save/status.
- preuves consultees:
  - `app/web/admin_api.js`
  - `app/web/admin_section_*.js`
  - `app/web/admin_settings_catalog.js`
  - tests frontend admin OK.

### Tests

- ce qui semble sain:
  - selection obligatoire large passee dans le conteneur.
  - tests dedies `record_arbiter_decisions` confirment que le finding ancien est stale.
  - Node couvre les modules purs critiques du stream.
- findings associes: `AUDIT-20260503-006`, `AUDIT-20260503-008`.
- risques residuels:
  - pas de full suite exhaustive dans ce lot.
  - pas de navigateur.
  - certains tests utilisent encore beaucoup de stubs permissifs et de lecture source.
- preuves consultees:
  - sorties des tests listees en methode.

### Documentation / specs

- ce qui semble sain:
  - les archives sont majoritairement rangees en `todo-done/` et lisibles comme historiques.
  - les specs hermeneutiques, identity et streaming donnent une doctrine utile.
  - la migration OVH documente la bascule Authelia/Caddy.
- findings associes: `AUDIT-20260503-008`, `AUDIT-20260503-009`, `AUDIT-20260503-007`.
- risques residuels:
  - certains documents projet anciens parlent encore token/LAN; ils sont historiques mais faciles a citer hors contexte.
  - `states/audits/` n'etait pas encore reference dans `app/docs/README.md`; ce lot ne le modifie pas par contrainte utilisateur.
- preuves consultees:
  - docs obligatoires de la demande;
  - inventaire `find app/docs -type f`.

### Architecture / maintenabilite

- ce qui semble sain:
  - les extractions recentes ont donne des responsabilites reelles: settings routes/service/write/validation, identity services, memory dashboard readers, hermeneutic admin modules.
  - `server.py` reste point de composition avec routes et proxies d'observabilite.
- findings associes: `AUDIT-20260503-001`, `AUDIT-20260503-006`.
- risques residuels:
  - `server.py` reste gros et porte encore des proxies de logs/prompt;
  - quelques facades de transition conservent des compatibilites legacy;
  - les dependances import-time sont nombreuses mais pas identifiees comme bug bloquant dans cet audit.
- preuves consultees:
  - `wc -l` des modules;
  - `rg` fonctions/classes/routes;
  - lectures `app/server.py`, `app/core/`, `app/admin/`.

### Config / environnement / deploiement

- ce qui semble sain:
  - build OVH `docker compose up -d --build fridadev` reussie.
  - `platform-fridadev` healthy.
  - `/admin` public redirige vers Authelia.
  - HEAD et `origin/main` alignes au depart.
- findings associes: `AUDIT-20260503-007`.
- risques residuels:
  - tests prouvent surtout que ca repond et que les contrats unitaires passent, pas un parcours post-auth complet dans Authelia.
  - pas de verification DB profonde en production pour eviter d'exposer ou muter des secrets/donnees.
- preuves consultees:
  - `docker ps` healthy;
  - `curl` public `302`;
  - tests in-container.

## Matrice de priorisation

| id | severite | domaine | effort estime | risque si non corrige | ordre conseille |
|---|---|---|---|---|---|
| AUDIT-20260503-001 | P1 | Persistence / observabilite | M | succes API/logs sans message DB canonique | 1 |
| AUDIT-20260503-002 | P1 | Memoire / identite / persistence | M | traces/identite derivees d'un tour non sauvegarde | 2 |
| AUDIT-20260503-003 | P1 | Runtime settings | S-M | configuration invalide persistable par API directe | 3 |
| AUDIT-20260503-004 | P2 | Stream / frontend / persistence | M | cache frontend et terminal `updated_at` mensongers | 4 |
| AUDIT-20260503-005 | P2 | Memoire / observabilite | S-M | erreur retrieval confondue avec absence de memoire | 5 |
| AUDIT-20260503-006 | P2 | Tests frontend | M | regressions UX non detectees | 6 |
| AUDIT-20260503-007 | P3 | Securite config | S | confusion operateur, reintroduction token | 7 |
| AUDIT-20260503-008 | P3 | Docs / arbiter | S | chantier stale rouvert inutilement | 8 |
| AUDIT-20260503-009 | P3 | Docs / settings | S | spec schema trompeuse | 9 |

## Non-findings / faux positifs

- `record_arbiter_decisions()` ne relit plus le modele runtime de facon stale dans le chemin teste: le modele effectif est capture et/ou passe via `effective_model`. Le finding substantif est stale; seul le pilotage documentaire reste a corriger.
- Le garde admin OVH ne repose pas sur `FRIDA_ADMIN_TOKEN` dans `server.py`; il utilise loopback ou proxy de confiance + `Remote-User`.
- `conversation_id` brut invalide dans `/api/chat` cree une nouvelle conversation: c'est discutable produit, mais explicitement verrouille par `test_resolve_chat_session_keeps_invalid_raw_contract_and_creates_conversation` et `test_server_chat_conversation_id_contract.py`.
- Les secrets runtime ne ressortent pas en clair dans les payloads admin lus; les surfaces exposent `is_secret` / `is_set` et les erreurs crypto testees ne doivent pas echo le secret.
- Le flux hermeneutique n'est pas une branche morte: `validated_output` influence bien le prompt via `build_hermeneutic_judgment_block()`.
- Les tests obligatoires Python et Node passent sur OVH apres rebuild.

## Limites de l'audit

- Audit principalement par lecture, tests contractuels et probes non-mutateurs; pas d'exploration manuelle post-auth dans un navigateur Authelia.
- Pas de PATCH live invalide sur la DB runtime pour ne pas polluer la configuration production.
- Pas de lecture de secrets, `.env`, DSN complet, tokens ou valeurs chiffrees.
- Pas de full suite exhaustive; la selection obligatoire et deux tests memoire complementaires ont ete executes.
- Pas de validation qualitative LLM live sur des conversations longues ou cas hermeneutiques reels.
- Pas de verification transactionnelle directe dans la DB de production.

## Suite recommandee

1. Lot persistence canonique: rendre `save_conversation()` verifiable, faire echouer ou degrader explicitement `/api/chat` quand messages/catalog ne sont pas sauvegardes, corriger `persist_response`.
2. Lot derivees non-stream: aligner l'ordre non-stream sur le stream, avec tests d'echec `save_conversation`.
3. Lot settings PATCH: imposer `validate_runtime_section()` cote backend avant ecriture DB/history.
4. Lot stream/frontend: ne jamais utiliser `updated_at` comme preuve sans `persisted`, et forcer rehydratation quand la preuve manque.
5. Lot memoire fail-open: propager `retrieve_error` jusqu'a `memory_arbitration`, `prompt_prepared`, Memory Admin.
6. Lot frontend tests: ajouter un mini harness navigateur pour chat stream, admin settings et logs.
7. Lot docs/config: retirer ou deprecier les knobs token/LAN, fermer le finding stale arbiter, mettre a jour la spec settings schema.
