# Memory RAG - evaluation lot 8C voie summaries - 2026-04-10

Statut: baseline active
Classement: `app/docs/states/baselines/`
Lot evalue: `Phase 8C - voie summaries`
Roadmap liee: `app/docs/todo-todo/memory/memory-rag-relevance-todo.md`
Specs liees:
- `app/docs/states/specs/memory-rag-summaries-lane-contract.md`
- `app/docs/states/specs/memory-rag-pre-arbiter-basket-contract.md`
Cartographie liee: `app/docs/states/architecture/memory-rag-current-pipeline-cartography.md`

## 1. Objet

Valider que le lot `8C`:
- ajoute une vraie lane `summaries` au pipeline memoire/RAG;
- normalise les candidats `summary` sous le contrat `7B`;
- gere proprement les collisions `trace / summary`;
- evite la double injection `trace + summary parent`;
- garde intactes les surfaces publiques de retrieval et la compatibilite aval.

Ce lot n'evalue pas:
- la generation live de nouveaux resumes;
- un reranker;
- une refonte du recall `6A`;
- une refonte du panier `7B`;
- une nouvelle surface d'observabilite finale.

## 2. Preuves pre-patch relues

Constats live relus juste avant implementation:
- `summaries.total = 0`;
- `traces_with_summary_id = 0`;
- sur `OVH migration Authelia Caddy Docker`, `Christophe Muck`, `qui suis-je pour toi maintenant identite durable` et `preferences utilisateur durables style reponse`, `retrieve_for_arbiter()` ne pouvait remonter aucun candidat `summary`.

Conclusion avant patch:
- la voie `summaries` devait etre prouvee surtout sur fixtures/replay hors live;
- le live OVH ne permettait pas un gain spectaculaire immediat, mais n'empechait pas un lot runtime propre et borne.

## 3. Implementation evaluee

Le lot `8C` implemente:
- une retrieval lane vectorielle `summaries` bornee a `top3` interne et plafonnee par le budget pre-arbitre;
- une normalisation runtime des candidats `summary` avec:
  - `candidate_id = "summary:" + summary_id`
  - `source_kind = "summary"`
  - `source_lane = "summaries"`
  - `role = "summary"`
  - `timestamp_iso = end_ts`
  - `summary_id != null`
  - `parent_summary_present = false`
- une collision `trace / summary` conservative dans le panier:
  - le `summary` peut gagner s'il subsume plusieurs traces utiles sans perdre le slot;
  - une `trace` reste preferee si elle est seule face au `summary` ou si elle garde le detail utile;
- une prevention explicite de la double injection:
  - un `summary` injecte ne reintroduit pas son propre `parent_summary`;
  - une `trace` gagnante n'injecte pas aussi le `summary` comme souvenir autonome;
- un rendu prompt-side ou `role=summary` est explicite.

## 4. Evaluation fixtures / replay

Les cas ci-dessous ont ete rejoues en builder pur, sans LLM arbitre live.

### 4.1 Couverture d'idee a slots constants

Cas rejoue:
- `coverage_without_summary_lane`
- `coverage_with_summary_lane`

Sans lane `summaries` (`max_candidates=2`):
- `raw_count=3`
- `basket_count=2`
- les `2` slots sont consommes par deux traces preferences de la meme fenetre:
  - `Tu preferes les reponses courtes.`
  - `Tu veux un ton direct et calme.`

Avec lane `summaries` (`max_candidates=2`):
- `raw_count=4`
- `basket_count=2`
- le `summary:sum-prefs` absorbe les deux traces preferences;
- le deuxieme slot libere peut rester occupe par une idee differente:
  - `Migration OVH vers Authelia et Caddy.`

Verdict local:
- gain structurel reel a budget de slots constant;
- la lane `summaries` agit ici comme compression utile d'idee, pas comme inflation textuelle.

### 4.2 Summary qui remplace utilement plusieurs traces

Cas rejoue:
- `summary_replaces_multiple_traces`

Resultat:
- `raw_count=3`
- `basket_count=1`
- representant final:
  - `candidate_id = summary:sum-prefs`
  - `source_kind = summary`
  - `source_candidate_ids = ['summary:sum-prefs', 'cand-4632d0cc0a43244f', 'cand-ed15ca0e9b06d796']`
- `injected_candidate_ids = ['summary:sum-prefs']`
- `memory_context_summary_count = 0`

Verdict local:
- un seul souvenir autonome survit;
- pas de double injection `trace + summary parent`;
- la voie `summaries` est bien une voie de representation, pas un doublon de prompt.

### 4.3 Trace qui reste preferee

Cas rejoue:
- `trace_remains_preferred`

Resultat:
- `raw_count=2`
- `basket_count=1`
- representant final:
  - `candidate_id = cand-ac6f584be5e0fe85`
  - `source_kind = trace`
  - `source_candidate_ids = ['cand-ac6f584be5e0fe85', 'summary:sum-id']`
- le `summary` parent n'est pas reinjecte comme souvenir autonome;
- cote prompt, la trace garde son `parent_summary` aval:
  - `selected_parent_summary_id = sum-id`
  - `injected_candidate_ids = ['cand-ac6f584be5e0fe85']`
  - `memory_context_summary_count = 1`

Verdict local:
- la politique `trace > summary` reste conservative sur un detail identitaire precis;
- le chainage `trace -> summary_id -> parent_summary` reste intact.

## 5. Impact live honnete

Le live OVH reste volontairement neutre au `2026-04-10` faute de donnees `summary`.

Probes read-only rejoues via `memory_store.retrieve_for_arbiter()`:
- `OVH migration Authelia Caddy Docker`: `raw_count=5`, `summary_count=0`
- `Christophe Muck`: `raw_count=5`, `summary_count=0`
- `qui suis-je pour toi maintenant identite durable`: `raw_count=5`, `summary_count=0`
- `preferences utilisateur durables style reponse`: `raw_count=5`, `summary_count=0`

Lecture retenue:
- la lane `summaries` est bien active en code;
- elle reste live-neutre sur OVH tant que `summaries=0`;
- cela n'invalide pas le lot `8C`, puisque la readiness Phase 4 avait deja tranche que le gain principal devrait etre prouve sur fixtures/replay sans forcer de generation live.

## 6. Compatibilite avale

Compatibilites relues apres patch:
- la shape publique de `memory_store.retrieve()` reste stable:
  - `conversation_id`, `role`, `content`, `timestamp`, `summary_id`, `score`
- `retrieve_for_arbiter()` peut maintenant retourner des candidats `summary` internes, sans changer `retrieve()`;
- `memory_retrieved.traces[*]` porte maintenant aussi:
  - `source_kind`
  - `source_lane`
  - `start_ts`
  - `end_ts`
- pour un `summary` candidat:
  - `candidate_id = summary:<summary_id>`
  - `timestamp_iso = end_ts`
  - `parent_summary = null`
- `memory_arbitration.basket_candidates[*]` garde `candidate_id`, `source_candidate_ids`, `summary_id`, `timestamp_iso`, `start_ts`, `end_ts`, `source_kind`, `source_lane`;
- la prevention de la double injection est lisible via `injected_candidate_ids`.

## 7. Tests executes

Suites coeur `8C` en conteneur rebuilt:

```bash
docker exec -i platform-fridadev sh -lc 'cd /app && python -m unittest \
  tests.test_memory_store_phase4 \
  tests.unit.chat.test_chat_memory_flow \
  tests.unit.memory.test_memory_candidate_generation_phase6a \
  tests.unit.memory.test_arbiter_phase4 \
  tests.unit.memory.test_memory_pre_arbiter_basket_phase7b \
  tests.unit.memory.test_summarizer_phase4 \
  tests.unit.memory.test_memory_summaries_phase8c'
```

Resultat:
- `58 tests`, `OK`

Suites complementaires prompt/logs:

```bash
docker exec -i platform-fridadev sh -lc 'cd /app && python -m unittest \
  tests.unit.logs.test_chat_turn_logger_phase2 \
  tests.test_server_logs_phase3 \
  tests.test_server_phase14'
```

Resultat:
- `79 tests`, `OK`

## 8. Verdict

Verdict lot `8C`:
- oui, la lane `summaries` est implementee proprement et reste bornee;
- oui, les collisions `trace / summary` sont gerees proprement dans le panier;
- oui, l'absence de double injection est prouvee sur fixtures et tests;
- oui, `top_k`, `summary_id`, `timestamp_iso`, `start_ts`, `end_ts` et `parent_summary` restent coherents;
- oui, le lot est gardable meme si le live OVH reste neutre faute de donnees `summary`.

Limite restante assumee:
- aucun gain live spectaculaire n'est visible tant que `summaries=0`;
- la decision `reranker` reste un chantier distinct de Phase `9D`, non rouvert ici.
