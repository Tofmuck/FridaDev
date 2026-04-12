# Memory RAG - evaluation lot 7B panier pre-arbitre - 2026-04-10

Statut: baseline active
Classement: `app/docs/states/baselines/`
Lot evalue: `Phase 7B - structuration du panier et dedup`
Roadmap liee: `app/docs/todo-done/refactors/memory-rag-relevance-todo.md`
Spec liee: `app/docs/states/specs/memory-rag-pre-arbiter-basket-contract.md`
Cartographie liee: `app/docs/states/architecture/memory-rag-current-pipeline-cartography.md`

## 1. Objet

Valider que le lot `7B`:
- introduit un vrai panier pre-arbitre borne et dedupe;
- stabilise les IDs `memory_retrieved -> panier -> memory_arbitration -> injection`;
- clarifie la place de `parent_summary`;
- garde intactes les surfaces publiques de retrieval et la compatibilite aval.

Ce lot n'evalue pas:
- la voie `summaries` live;
- un reranker;
- une dedup semantique agressive;
- une refonte complete de l'arbitre.

## 2. Preuves avant patch relues

Etat courant relu juste avant implementation:
- probe `qui suis-je pour toi maintenant identite durable`: `raw_count=5`, avec `duplicate_groups=[{"count":4,"content":"Qui suis-je pour toi maintenant ?"}]`;
- probe `Christophe Muck`: `raw_count=5`, avec `duplicate_groups=[{"count":2,"content":"Je suis Christophe Muck"}]`;
- lecture read-only de la chaine actuelle avec arbitre stubbe:
  - `memory_retrieved.traces[*].candidate_id` existait deja;
  - `memory_arbitration.decisions[*]` restait bridgee a des indexes legacy `0/1`;
  - `memory_traces[*].candidate_id` etait absent cote injection;
  - `prompt_prepared` ne portait encore que des compteurs, pas les IDs injectes.

Conclusion avant patch:
- le recall 6A etait deja defendable;
- le vrai manque restant etait bien un panier pre-arbitre structure, dedupe et relie proprement a l'injection.

## 3. Implementation evaluee

Le lot 7B implemente:
- un module dedie `app/memory/memory_pre_arbiter_basket.py`;
- un panier pre-arbitre borne a `8` candidats max;
- une dedup conservative:
  - doublon exact;
  - quasi-doublon lexical;
  - collision prudente `meme conversation / meme idee`;
- des `candidate_id` stables reutilisant `memory_retrieved.traces[*].candidate_id`;
- un payload arbitre recentre sur:
  - `candidate_id`
  - `source_kind`
  - `source_lane`
  - `role`
  - `content`
  - `timestamp_iso`
  - `retrieval_score`
  - `semantic_score`
- un snapshot `memory_arbitration` qui garde maintenant:
  - `basket_candidates`
  - `basket_candidates_count`
  - `basket_limit=8`
  - `injected_candidate_ids`
- une observabilite prompt-side `prompt_prepared.memory_prompt_injection.injected_candidate_ids`.

## 4. Resultats runtime apres patch

Probes rejoues en read-only sur le conteneur rebuilt, avec arbitre runtime reel mais sans ecriture DB.

### 4.1 `OVH migration Authelia Caddy Docker`

Avant panier:
- `raw_count=5`
- deux requetes smoke-test tres proches coexistaient encore cote retrieval brut

Apres panier:
- `basket_count=4`
- fusion utile observee:
  - `cand-9fb95efe7734ea81` absorbe `cand-26edb0f09d1ec740`
  - `dedup_reason_code=lexical_near_duplicate`

Verdict arbitre:
- `arbiter_kept_ids=['cand-e674272a67500406']`

Injection finale:
- `injected_ids=['cand-e674272a67500406']`

Verdict local:
- panier moins redondant et injection finale univoque.

### 4.2 `Christophe Muck`

Avant panier:
- `raw_count=5`
- doublon exact utilisateur `Je suis Christophe Muck` present deux fois

Apres panier:
- `basket_count=4`
- fusion exacte observee:
  - `cand-5113f67d5830d689` absorbe `cand-d87506dc050d9987`
  - `dedup_reason_code=exact_duplicate`

Verdict arbitre:
- `arbiter_kept_ids=[]`

Injection finale:
- `injected_ids=[]`

Verdict local:
- le lot 7B ne corrige pas le rappel identitaire faible sur cette formulation, mais il nettoie le panier avant jugement.

### 4.3 `qui suis-je pour toi maintenant identite durable`

Avant panier:
- `raw_count=5`
- quatre occurrences exactes de `Qui suis-je pour toi maintenant ?`

Apres panier:
- `basket_count=2`
- fusion exacte stable observee en reruns read-only:
  - `cand-0c575f34c4f459c3` absorbe `cand-067d197802bbf823`, `cand-e5b882964dec7cc6`, `cand-eef1f1dc32c6c423`

Verdict arbitre:
- reruns read-only:
  - `arbiter_kept_ids=[]` sur `4/5` reruns
  - `arbiter_kept_ids=['cand-0c575f34c4f459c3', 'cand-8ef9e8d2fcbcef75']` sur `1/5` rerun
- le nettoyage du panier est reproductible, mais le keep aval ne l'est pas tel qu'ecrit dans la version initiale de cette baseline

Injection finale:
- reruns read-only:
  - `injected_ids=[]` sur `4/5` reruns
  - `injected_ids=['cand-0c575f34c4f459c3', 'cand-8ef9e8d2fcbcef75']` sur `1/5` rerun
- ne pas surinterpreter un keep/injection ponctuel comme un resultat stable du lot `7B`

Verdict local:
- gain stable de lisibilite et disparition de la repetition identitaire brute avant arbitre;
- verdict aval arbitre/injection sensible a la variabilite du run et/ou au contexte recent, donc non baselineable ici comme fait stable.

### 4.4 `preferences utilisateur durables style reponse`

Avant panier:
- `raw_count=5`
- deux variantes exactes de la question memoire vive / disque dur coexistaient

Apres panier:
- `basket_count=4`
- fusion exacte observee:
  - `cand-38c89a1eb88d1600` absorbe `cand-4f845cd5bc897a52`

Verdict arbitre:
- `arbiter_kept_ids=[]`

Injection finale:
- `injected_ids=[]`

Verdict local:
- le lot 7B ne transforme pas ce probe en bon rappel durable, mais retire une redondance inutile avant rejet arbitre.

## 5. Compatibilite avale

Preuve read-only sur `Christophe Muck` apres patch:
- `memory_store.retrieve()[0].keys() = ['content', 'conversation_id', 'role', 'score', 'summary_id', 'timestamp']`
- `memory_retrieved.traces[0].keys() = ['candidate_id', 'content', 'conversation_id', 'parent_summary', 'retrieval_score', 'role', 'summary_id', 'timestamp_iso']`
- `basket.candidates[0].keys()` contient bien:
  - `candidate_id`
  - `source_candidate_ids`
  - `source_kind`
  - `source_lane`
  - `timestamp_iso`
  - `summary_id`
  - `parent_summary_present`
  - `dedup_key`
- `basket.prompt_candidates[0]` garde:
  - `candidate_id`
  - `timestamp`
  - `timestamp_iso`
  - `summary_id`
  - `parent_summary`

Conclusion:
- la shape publique de `memory_store.retrieve()` reste stable;
- `timestamp`, `summary_id` et la possibilite future `trace -> summary_id -> parent_summary` restent intactes;
- `parent_summary` complet reste aval/prompt-side, avec `parent_summary_present` seulement dans le panier diagnostique.

## 6. Tests executes

Suites coeur 7B en conteneur rebuilt:

```bash
docker exec -i platform-fridadev sh -lc 'cd /app && python -m unittest \
  tests.test_memory_store_phase4 \
  tests.unit.chat.test_chat_memory_flow \
  tests.unit.memory.test_memory_candidate_generation_phase6a \
  tests.unit.memory.test_arbiter_phase4 \
  tests.unit.memory.test_memory_pre_arbiter_basket_phase7b'
```

Resultat:
- `49 tests`, `OK`

Suites complementaires observabilite injection:

```bash
docker exec -i platform-fridadev sh -lc 'cd /app && python -m unittest \
  tests.unit.logs.test_chat_turn_logger_phase2 \
  tests.test_server_logs_phase3 \
  tests.test_server_phase14'
```

Resultat:
- `79 tests`, `OK`

## 7. Verdict

Verdict lot 7B:
- oui, le panier pre-arbitre est clairement meilleur;
- oui, les IDs stables existent maintenant de `memory_retrieved` jusqu'a l'injection;
- oui, `parent_summary` est clarifie sans ouvrir la voie `summaries` live;
- oui, la Phase 7 est fermable proprement sur ce perimetre borne.

Limite restante assumee:
- le probe `preferences utilisateur durables style reponse` reste surtout un probleme de recall/composition amont, pas de structuration du panier;
- la voie `summaries` et la decision reranker restent des chantiers distincts, non rouverts ici.
