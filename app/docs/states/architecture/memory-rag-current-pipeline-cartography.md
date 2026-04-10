# Memory RAG - cartographie du pipeline courant - 2026-04-10

Statut: reference active
Classement: `app/docs/states/architecture/`
Portee: cartographie exacte du pipeline memoire/RAG courant apres implementation des lots 7B et 8C
Roadmap liee: `app/docs/todo-todo/memory/memory-rag-relevance-todo.md`
Baselines liees:
- `app/docs/states/baselines/memory-rag-relevance-baseline-2026-04-10.md`
- `app/docs/states/baselines/memory-rag-7B-evaluation-2026-04-10.md`

## 1. Objet

Cette note documente l'etat runtime courant du chantier `memory-rag-relevance` apres les lots `6A`, `7B` et `8C`.

Elle documente:
- la chaine exacte `user_msg -> retrieval -> enrichissement -> arbitre -> prompt`;
- les quatre surfaces de donnees a distinguer pour la suite;
- la place exacte de `parent_summary`;
- le role de `memory_retrieved` et `memory_arbitration`;
- les observabilites existantes;
- ce qu'il manque encore pour evaluer proprement la pertinence amont.

Elle ne fait pas:
- de redesign complet de l'arbitre;
- d'ouverture de la voie `summaries` live;
- de design de la future surface finale d'observabilite memoire/RAG.

## 2. Methode et preuves relues

Sources retenues:
- code du depot;
- tests existants sur les contrats canoniques et l'observabilite;
- runtime OVH en lecture seule;
- builders purs quand il fallait montrer une forme canonique sans appeler le LLM arbitre.

Preuves runtime relues pendant cette phase:
- probe read-only `memory_store.retrieve()` + `enrich_traces_with_summaries()` + `build_memory_retrieved_input()` sur `architecture modules externes arbiter STT TTS`;
- lecture read-only de `memory_store.get_arbiter_decisions(limit=1)`;
- lecture read-only des endpoints `GET /api/admin/hermeneutics/dashboard` et `GET /api/admin/hermeneutics/arbiter-decisions?limit=3`;
- lecture read-only de `observability.chat_log_events`;
- lecture read-only des `admin*.log.jsonl` via `admin_logs`.

Constats runtime directement verifies:
- `memory_store.retrieve()[0]` garde aujourd'hui les cles publiques `content`, `conversation_id`, `role`, `score`, `summary_id`, `timestamp`;
- `memory_store.retrieve_for_arbiter()` ajoute `retrieval_score` et `semantic_score` pour la frontiere pre-arbitre, et peut maintenant completer les traces par une petite lane `summaries` interne;
- l'enrichissement ajoute seulement `parent_summary`;
- `memory_retrieved` expose `schema_version`, `retrieval_query`, `top_k_requested`, `retrieved_count`, `traces`;
- `memory_retrieved.traces[*]` expose `candidate_id`, `source_kind`, `source_lane`, `conversation_id`, `role`, `content`, `timestamp_iso`, `start_ts`, `end_ts`, `retrieval_score`, `summary_id`, `parent_summary`;
- `memory_arbitration` expose maintenant `schema_version`, `status`, `reason_code`, `raw_candidates_count`, `basket_candidates_count`, `basket_limit`, `basket_candidates`, `decisions_count`, `kept_count`, `rejected_count`, `injected_candidate_ids`, `decisions`;
- `memory_arbitration.decisions[*]` expose maintenant `candidate_id`, `retrieved_candidate_id`, `legacy_candidate_id`, `legacy_candidate_index`, `source_candidate_ids`, `source_kind`, `source_lane`, `keep`, `semantic_relevance`, `contextual_gain`, `redundant_with_recent`, `reason`, `decision_source`, `model`;
- `arbiter_decisions` persiste maintenant le `candidate_id` stable du representant quand il existe, avec `candidate_content`, `candidate_role`, `candidate_ts`, `candidate_score`, plus verdict et scores;
- `prompt_prepared` persiste maintenant un resume de l'injection memoire effective dans le prompt, y compris `injected_candidate_ids`;
- `summaries=0` sur le runtime actif, donc la nouvelle lane `summaries` reste neutre live au `2026-04-10`;
- `parent_summary` reste actuellement nul en pratique sur OVH et le bloc `[Contexte du souvenir ...]` n'apparait pas live hors fixtures/replay.

## 3. Glossaire minimal pour lever les ambiguities

- `raw_traces`: sortie brute du retrieval hybride, issue de `memory_store.retrieve_for_arbiter(user_msg)` quand cette surface interne est disponible.
- `retrieved_candidates`: `raw_traces` apres enrichissement `parent_summary`.
- `memory_retrieved`: snapshot canonique de `retrieved_candidates`, construit avant l'arbitre.
- `pre_arbiter_basket`: panier borne et dedupe construit a partir de `memory_retrieved`.
- `filtered_traces`: sous-ensemble garde par l'arbitre a partir du panier pre-arbitre.
- `memory_arbitration`: snapshot canonique des decisions arbitre, relie a `memory_retrieved`.
- `memory_traces`: liste effectivement transmise au constructeur de prompt.
- `arbiter_decisions`: table SQL persistante, une ligne par decision candidate.
- `memory_retrieve`: stage `chat_log_events` du retrieval vectoriel.
- `memory_retrieved`: evenement `admin_logs` de comptage + snapshot canonique runtime.
- `memory_arbitrated`: evenement `admin_logs` de comptage apres tri arbitre.
- `memory_arbitration`: snapshot canonique runtime; ce n'est pas une table SQL.

## 4. Chaine exacte du pipeline courant

### 4.1 Entree

Point d'entree memoire courant:
- `prepare_memory_context(conversation, user_msg, ...)`
- query de retrieval reelle: le seul `user_msg`
- `top_k_requested`: resolve via runtime embedding settings avant l'appel de retrieval

### 4.2 Retrieval brut

Chemin:
- surface publique: `memory_store.retrieve(user_msg)`
- surface interne pre-arbitre: `memory_store.retrieve_for_arbiter(user_msg)`
- delegation commune vers `memory_traces_summaries.retrieve(query, top_k=None, ...)`

Ce que fait le retrieval:
- embed la query en mode `query`;
- lit `top_k` depuis le runtime embedding si aucun `top_k` explicite n'est passe;
- execute un rappel hybride borne sur `traces`:
  - lane dense vectorielle;
  - lane FTS `to_tsvector('simple', ...)`;
  - voie exacte `pg_trgm` sur contenu normalise, triee par distance `<->` quand elle s'active;
- quand la surface interne pre-arbitre est demandee, peut ajouter une lane vectorielle `summaries` bornee a `top3` interne si des resumes existent;
- garde `top_k` comme cap final public.

Forme de sortie publique reelle:
- `conversation_id`
- `role`
- `content`
- `timestamp`
- `summary_id`
- `score`

Forme de sortie interne pre-arbitre:
- meme base publique;
- plus `retrieval_score`;
- plus `semantic_score`.
- pour un candidat `summary` interne:
  - `source_kind=summary`
  - `source_lane=summaries`
  - `role=summary`
  - `timestamp_iso=end_ts`
  - `start_ts`
  - `end_ts`
  - `summary_id` non nul

Ce que la surface publique ne contient pas encore:
- aucun `candidate_id` canonique;
- aucun `parent_summary`;
- aucune metadonnee arbitre;
- aucune provenance de lane;
- aucune dedup;
- aucun statut d'injection prompt.

Observabilite associee:
- stage persiste `memory_retrieve` dans `observability.chat_log_events`;
- payload actuel: seulement `top_k_requested` et `top_k_returned`.

### 4.3 Enrichissement `parent_summary`

Chemin:
- `_enrich_retrieved_candidates(...)`
- `memory_store.enrich_traces_with_summaries(traces)`
- `memory_traces_summaries.enrich_traces_with_summaries(...)`

Ce que fait l'enrichissement:
- ajoute `trace['parent_summary']` a chaque trace;
- utilise un cache interne par `summary_id` ou `conversation_id@timestamp` pour eviter des lectures DB redondantes.

Forme de sortie:
- meme trace que le retrieval brut;
- plus `parent_summary`.

Point factuel important:
- au `2026-04-10`, `summaries=0` sur OVH;
- donc la lane `summaries` existe desormais en code mais reste vide live;
- `parent_summary` existe dans le contrat mais vaut `None` en pratique sur le runtime actif.

### 4.4 Construction de `memory_retrieved`

Chemin:
- `memory_retrieved_input.build_memory_retrieved_input(...)`

Nature:
- snapshot canonique du retrieval enrichi;
- construit avant tout tri arbitre;
- utilise pour stabiliser l'identite des candidats et fournir un contrat runtime partageable.

Ce que garde `memory_retrieved`:
- `schema_version`
- `retrieval_query`
- `top_k_requested`
- `retrieved_count`
- `traces[*].candidate_id`
- `traces[*].source_kind`
- `traces[*].source_lane`
- `traces[*].conversation_id`
- `traces[*].role`
- `traces[*].content`
- `traces[*].timestamp_iso`
- `traces[*].start_ts`
- `traces[*].end_ts`
- `traces[*].retrieval_score`
- `traces[*].summary_id`
- `traces[*].parent_summary`

Ce que `memory_retrieved` ne garde pas:
- `keep`
- `semantic_relevance`
- `contextual_gain`
- `redundant_with_recent`
- `reason`
- `decision_source`
- `model`

### 4.5 Ce que voit reellement l'arbitre

Chemin:
- `memory_pre_arbiter_basket.build_pre_arbiter_basket(...)`
- `arbiter.filter_traces_with_diagnostics(pre_arbiter_basket.prompt_candidates, recent_turns)`

Important:
- l'arbitre consomme un panier deja borne et dedupe;
- le panier peut maintenant contenir des representants `trace` ou `summary`;
- il ne voit toujours pas `parent_summary` complet;
- il ne voit pas `conversation_id` ni `summary_id` dans son payload explicite.

Panier vu par l'arbitre:
- contexte recent separe: concat des `recent_turns[-10:]` sous forme texte `ROLE: content`
- candidats JSON:
  - `candidate_id`
  - `source_kind`
  - `source_lane`
  - `role`
  - `content`
  - `timestamp_iso`
  - `retrieval_score`
  - `semantic_score`

Contrat de lecture important:
- `retrieval_score` = score hybride de rappel/rang;
- `semantic_score` = signal dense explicite consomme par l'arbitre et par le fallback deterministe;
- le fallback ne compare plus le `score` hybride comme s'il etait directement semantique.

Ce que le panier arbitre n'inclut pas:
- `conversation_id`
- `summary_id`
- `parent_summary`
- `source_candidate_ids`
- `dedup_key`
- `parent_summary_present`

### 4.6 Sortie arbitre

Sorties runtime:
- `filtered_traces`: sous-ensemble garde du panier pre-arbitre, avec `candidate_id` stable
- `arbiter_decisions`: liste de verdicts keyee par `candidate_id` stable

Persistence:
- `record_arbiter_decisions(conversation_id, pre_arbiter_basket.prompt_candidates, arbiter_decisions, ...)`
- insere une ligne SQL par decision dans `arbiter_decisions`

Forme persistante `arbiter_decisions`:
- `conversation_id`
- `candidate_id`
- `candidate_role`
- `candidate_content`
- `candidate_ts`
- `candidate_score`
  - score de rappel/ranking du candidat, pas le score semantique arbitre
- `keep`
- `semantic_relevance`
- `contextual_gain`
- `redundant_with_recent`
- `reason`
- `model`
- `decision_source`
- `created_ts`

Forme canonique runtime `memory_arbitration`:
- `schema_version`
- `status`
- `reason_code`
- `raw_candidates_count`
- `basket_candidates_count`
- `basket_limit`
- `basket_candidates[*].candidate_id`
- `basket_candidates[*].source_candidate_ids`
- `basket_candidates[*].source_kind`
- `basket_candidates[*].source_lane`
- `basket_candidates[*].role`
- `basket_candidates[*].content`
- `basket_candidates[*].timestamp_iso`
- `basket_candidates[*].start_ts`
- `basket_candidates[*].end_ts`
- `basket_candidates[*].retrieval_score`
- `basket_candidates[*].semantic_score`
- `basket_candidates[*].summary_id`
- `basket_candidates[*].parent_summary_present`
- `basket_candidates[*].dedup_key`
- `basket_candidates[*].dedup_reason_code`
- `decisions_count`
- `kept_count`
- `rejected_count`
- `injected_candidate_ids`
- `decisions[*].candidate_id`
- `decisions[*].retrieved_candidate_id`
- `decisions[*].legacy_candidate_id`
- `decisions[*].legacy_candidate_index`
- `decisions[*].source_candidate_ids`
- `decisions[*].source_kind`
- `decisions[*].source_lane`
- `decisions[*].keep`
- `decisions[*].semantic_relevance`
- `decisions[*].contextual_gain`
- `decisions[*].redundant_with_recent`
- `decisions[*].reason`
- `decisions[*].decision_source`
- `decisions[*].model`

### 4.7 Ce que devient `memory_traces`

`memory_traces` est la liste qui part vers le prompt builder. Ce n'est ni le retrieval brut, ni `memory_retrieved`, ni `arbiter_decisions`.

Regle actuelle:
- mode `enforced_all`: `memory_traces = candidats gardes du panier pre-arbitre`
- mode `shadow`: `memory_traces = panier pre-arbitre complet` meme si l'arbitre a tourne
- mode `off`: `memory_traces = panier pre-arbitre complet` et `memory_arbitration.status='skipped'`
- aucun candidat: `memory_traces = []`

Consequence:
- `memory_traces[*]` garde maintenant `candidate_id`, `source_candidate_ids`, `dedup_key`, `summary_id`, `timestamp` et `parent_summary`;
- meme quand l'arbitre ne voit pas `parent_summary`, le prompt final peut encore recevoir les traces representatives enrichies avec `parent_summary` si le mode final le permet.

### 4.8 Injection finale dans le prompt

Chemin:
- `conversations_prompt_window.build_prompt_window(...)`

Ordre memoire utile:
- `active_summary` de conversation si disponible
- `context_hints` si disponibles
- bloc contexte memoire construit a partir des `parent_summary` uniques de `memory_traces`
- bloc traces memoire construit a partir de `memory_traces`
- puis fenetre de conversation recente retenue par budget tokens

Ce que le prompt final injecte reellement:
- messages `role/content` seulement;
- les scores, verdicts arbitre, `candidate_id`, `summary_id` et metadonnees de retrieval ne sont pas reinjectes dans le texte prompt;
- `parent_summary` n'apparait pas comme champ JSON, seulement comme contenu textuel dans un bloc systeme dedie s'il existe.

Observabilite associee:
- `prompt_prepared` dans `observability.chat_log_events` resume l'injection effective via `memory_prompt_injection`, avec `injected_candidate_ids`.

### 4.9 Insertion dans le noeud hermeneutique

Chemin:
- `_run_hermeneutic_node_insertion_point(...)`

Ce qui est passe au noeud:
- `memory_retrieved`
- `memory_arbitration`
- d'autres snapshots canoniques (`time_input`, `summary_input`, `identity_input`, etc.)

Usages directs:
- `hermeneutic_node_logger.emit_hermeneutic_node_insertion(...)`
- `primary_node.build_primary_node(...)`
- `validation_agent.build_validated_output(..., canonical_inputs={...})`

Point important:
- le noeud hermeneutique voit les snapshots canoniques `memory_retrieved` et `memory_arbitration`;
- le prompt final, lui, voit seulement les messages systeme deja formates.

## 5. Quatre surfaces de donnees a distinguer

### Surface 1 - retrieval brut

Role:
- produire le recall vectoriel brut a partir du seul `user_msg`

Forme:
- liste de traces plates `raw_traces`

Champs disponibles:
- `conversation_id`
- `role`
- `content`
- `timestamp`
- `summary_id`
- `score`

Champs absents:
- `parent_summary`
- `candidate_id`
- tout champ arbitre
- tout champ prompt

Source de verite:
- `memory_traces_summaries.retrieve()`
- table `traces`

Consommateur suivant:
- enrichissement `parent_summary`
- projection panier arbitre

### Surface 2 - panier pre-arbitre

Role:
- fournir au LLM arbitre un panier minimal et recentre, plus contexte recent

Forme:
- `recent_text`
- liste `candidates[*]` en JSON dans `arbiter.filter_traces_with_diagnostics()`

Champs disponibles:
- `id`
- `role`
- `content`
- `ts`
- `score`

Champs absents:
- `conversation_id`
- `summary_id`
- `parent_summary`
- `candidate_id` canonique
- provenance de lane
- marqueurs de dedup

Source de verite:
- projection locale des `raw_traces` dans `arbiter.py`

Consommateur suivant:
- appel LLM arbitre
- puis mapping des decisions vers `raw_traces` par index legacy

### Surface 3 - sortie arbitre

Role:
- separer les candidats gardes des rejets et produire le diagnostic de tri

Formes couplees:
- `filtered_traces`: liste runtime pour la suite
- `memory_arbitration`: snapshot canonique de diagnostic
- `arbiter_decisions`: persistence SQL ligne a ligne

Champs disponibles cote `filtered_traces`:
- meme shape que `raw_traces`

Champs disponibles cote `memory_arbitration`:
- `status`
- `reason_code`
- `raw_candidates_count`
- `decisions_count`
- `kept_count`
- `rejected_count`
- `decisions[*].retrieved_candidate_id`
- `decisions[*].legacy_candidate_id`
- `decisions[*].legacy_candidate_index`
- `decisions[*].keep`
- `decisions[*].semantic_relevance`
- `decisions[*].contextual_gain`
- `decisions[*].redundant_with_recent`
- `decisions[*].reason`
- `decisions[*].decision_source`
- `decisions[*].model`

Champs absents cote `memory_arbitration`:
- `content`
- `role`
- `timestamp`
- `summary_id`
- `parent_summary`

Source de verite:
- `arbiter.filter_traces_with_diagnostics()`
- `memory_arbitration_input.build_memory_arbitration_input()`
- table `arbiter_decisions`

Consommateur suivant:
- re-enrichissement eventuel des traces gardees
- noeud hermeneutique
- prompt final via `memory_traces`

### Surface 4 - prompt final

Role:
- transformer la memoire utile en messages systeme lisibles par le modele final

Forme:
- messages `role/content`

Blocs memoire possibles:
- `[Indices contextuels recents]`
- `[Contexte du souvenir ...]`
- `[Mémoire — souvenirs pertinents]`

Champs disponibles:
- `role`
- `content`

Champs absents:
- `candidate_id`
- `retrieval_score`
- `semantic_relevance`
- `contextual_gain`
- `decision_source`
- `summary_id` explicite
- `parent_summary` comme structure

Source de verite:
- `conversations_prompt_window.build_prompt_window()`

Consommateur suivant:
- prompt LLM final
- resume `prompt_prepared` dans `chat_log_events`

## 6. Place exacte de `memory_retrieved` et `memory_arbitration`

### `memory_retrieved`

Nature:
- snapshot canonique du retrieval enrichi;
- pas une table SQL;
- pas le prompt final;
- pas le panier arbitre.

A quoi il sert:
- stabiliser l'identite des candidats via `candidate_id`;
- fournir une vue partageable du retrieval au noeud hermeneutique;
- servir d'ancrage pour relier ensuite les decisions arbitre aux candidats recuperes.

Ce qu'il garde:
- shape enrichie du retrieval avant tri;
- `parent_summary` quand disponible.

Ce qu'il ne garde pas:
- les verdicts arbitre;
- les metadonnees de prompt effectif;
- la selection finale `memory_traces`.

### `memory_arbitration`

Nature:
- snapshot canonique du tri arbitre;
- pas la table `arbiter_decisions`;
- pas le prompt final textuel.

A quoi il sert:
- fournir au noeud hermeneutique et a la validation une vue compacte du tri;
- exposer le panier pre-arbitre reellement juge;
- relier les decisions au `candidate_id` stable de `memory_retrieved`;
- exposer la liste des `candidate_id` effectivement injectes.

Ce qu'il garde:
- counts;
- statut;
- le panier pre-arbitre structure;
- raisons;
- scores arbitre;
- lien `retrieved_candidate_id`;
- `injected_candidate_ids`.

Ce qu'il ne garde pas:
- le `parent_summary` complet;
- le texte final du prompt;
- les champs JSON exclus du payload arbitre.

## 7. Place exacte de `parent_summary`

`parent_summary` apparait:
- apres `memory_store.enrich_traces_with_summaries(...)`;
- dans `retrieved_candidates`;
- dans `memory_retrieved.traces[*].parent_summary`;
- dans `pre_arbiter_basket.candidates[*].parent_summary_present`;
- dans `memory_traces` quand la liste injectee a ete enrichie;
- dans le prompt final uniquement via le bloc systeme `[Contexte du souvenir ...]`.

`parent_summary` n'apparait pas:
- dans la sortie brute `memory_store.retrieve()`;
- dans le panier vu par l'arbitre;
- dans les rows `arbiter_decisions`;
- dans `memory_arbitration.decisions[*]`.

Conclusion tranchee:
- `parent_summary` enrichit aujourd'hui `memory_retrieved` et le prompt final;
- `parent_summary` ne nourrit pas encore le payload arbitre.

## 8. Observabilites existantes a reutiliser

### 8.1 `observability.chat_log_events`

Nature:
- persistence SQL durable dans `observability.chat_log_events`

Stages pertinents verifies:
- `memory_retrieve` (`104` rows lues)
- `arbiter` (`2788` rows lues)
- `hermeneutic_node_insertion` (`1545` rows lues)
- `prompt_prepared` (`2948` rows lues)

Ce que chaque stage montre aujourd'hui:
- `memory_retrieve`: seulement `top_k_requested` / `top_k_returned`
- `arbiter`: counts, `mode`, `model`, `decision_source`, `fallback_used`, `rejection_reason_counts`
- `hermeneutic_node_insertion`: resume compact de `memory_retrieved` et `memory_arbitration`
- `prompt_prepared`: resume de l'injection memoire effective dans le prompt, avec `injected_candidate_ids`

Limite:
- pas de snapshot brut complet des candidats retrieval persiste dans cette table.

### 8.2 `arbiter_decisions`

Nature:
- persistence SQL durable, ligne a ligne, du tri arbitre

Ce que cette table apporte:
- contenu candidat;
- role candidat;
- score retrieval du candidat;
- verdict arbitre;
- scores arbitre;
- `reason`, `model`, `decision_source`, `created_ts`

Limite:
- elle ne persiste pas `parent_summary`;
- elle ne persiste pas `retrieved_candidate_id`;
- elle ne persiste pas `source_candidate_ids`.

### 8.3 `admin_logs`

Nature:
- JSONL file-backed avec rotation

Events memoire verifies sur la retention:
- `hermeneutic_mode`: `111`
- `memory_retrieved`: `110`
- `memory_arbitrated`: `110`
- `memory_mode_apply`: `110`
- `context_hints_selected`: `97`
- `stage_latency.retrieve`: `111`
- `stage_latency.arbiter`: `110`
- `stage_latency.identity_extractor`: `110`

Ce que ces events portent:
- `memory_retrieved`: count brut
- `memory_arbitrated`: `raw`, `kept`, `decisions`
- `memory_mode_apply`: `mode`, `source`, `raw`, `selected`, `filtered`
- `stage_latency`: stage + duration

Limite factuelle importante:
- `admin_logs.read_logs()` ne lit que le fichier courant `admin.log.jsonl`, pas les rotations;
- `dashboard.latency_ms` depend donc du fichier courant seulement et peut valoir `0` meme si les rotations gardent des `stage_latency` historiques;
- a l'inverse, `summarize_hermeneutic_mode_observation()` parcourt bien les fichiers rotates.

### 8.4 Dashboard hermeneutique

Nature:
- vue derivee, pas source de verite primaire

Ce qu'il agrege:
- KPIs depuis la DB via `get_hermeneutic_kpis()`
- `runtime_metrics` depuis `arbiter.get_runtime_metrics()` en memoire process
- `latency_ms` depuis `admin_logs.read_logs()`
- `mode_observation` depuis `admin_logs.summarize_hermeneutic_mode_observation()`

Conclusion pratique:
- le dashboard est utile pour une lecture operateur rapide;
- il ne remplace ni `chat_log_events`, ni `arbiter_decisions`, ni les snapshots canoniques runtime.

### 8.5 Ce qui est persiste, derive ou process-local

Persiste:
- `observability.chat_log_events`
- `arbiter_decisions`
- fichiers `admin*.log.jsonl`

Derive:
- `dashboard.latency_ms`
- `dashboard.rates`
- `dashboard.mode_observation`
- `prompt_prepared.memory_prompt_injection`

Process-local:
- `arbiter.get_runtime_metrics()`
- les objets runtime `memory_retrieved`, `memory_arbitration`, `memory_traces`

## 9. Ce qu'il manque encore pour evaluer proprement la pertinence amont

Manques explicitement confirmes a la fin de cette phase:
- faux positifs par categorie attaches a une observabilite durable par turn;
- provenance de lane ou `source_lane` pour chaque candidat;
- duplication avant arbitre comme objet observable natif;
- couverture `traces` vs `summaries` puisque la voie `summaries` n'est pas live;
- snapshot persiste complet du retrieval brut par tour, avec ses candidats et leurs cles stables;
- lien durable direct entre item injecte dans le prompt final et ligne SQL `arbiter_decisions`.

Ces manques restent des constats de cartographie. Cette phase ne propose pas encore leur implementation.

## 10. Verdict de cloture Phase 1

La Phase 1 est fermable proprement au `2026-04-10` car:
- la chaine exacte `retrieval -> enrichissement -> arbitre -> prompt` est documentee;
- les quatre surfaces retrieval / panier / sortie arbitre / prompt final sont explicitees;
- la place de `parent_summary` est tranchee sans ambiguite;
- le role de `memory_retrieved` et `memory_arbitration` est clarifie;
- les observabilites existantes sont inventoriees avec distinction `persiste / derive / process-local`;
- les manques restants pour evaluer la pertinence amont sont listes sans glisser vers la Phase 2.
