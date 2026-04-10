# Memory RAG - contrat cible du panier pre-arbitre - 2026-04-10

Statut: reference normative active
Classement: `app/docs/states/specs/`
Portee: contrat cible du panier memoire remis a l'arbitre avant toute implementation V2
Roadmap liee: `app/docs/todo-todo/memory/memory-rag-relevance-todo.md`
Baseline liee: `app/docs/states/baselines/memory-rag-relevance-baseline-2026-04-10.md`
Cartographie liee: `app/docs/states/architecture/memory-rag-current-pipeline-cartography.md`
Design lie: `app/docs/states/architecture/memory-rag-candidate-generation-design.md`

## 1. Objet

Cette spec ferme la Phase 3 du chantier `memory-rag-relevance`.

Elle fixe, sans patch runtime:
- la shape cible d'un candidat avant arbitre;
- les champs qui doivent exister dans le panier pre-arbitre;
- les champs que l'arbitre doit effectivement voir dans un premier lot V2;
- les champs qui restent diagnostic-only ou prompt-only;
- la regle cible de dedup;
- la strategie de linkage stable entre item retrieve, decision arbitre et item injecte;
- la taille maximale du panier remis a l'arbitre;
- la place exacte de `parent_summary`.

Elle ne fait pas:
- l'implementation du candidate generation Phase 6A;
- l'ouverture de la voie `summaries` Phase 4;
- le redesign complet de l'arbitre;
- l'ajout d'un reranker;
- le design de la surface finale d'observabilite.

## 2. Pourquoi une spec et non une simple note d'architecture

Le sujet de la Phase 3 n'est plus seulement descriptif.

Il faut maintenant figer:
- un schema cible;
- des invariants;
- une taxonomie minimale de champs;
- des regles normatives de dedup;
- une doctrine explicite de linkage entre objets.

Le bon emplacement est donc `states/specs/`, pas `states/architecture/`.

## 3. Sources et preuves relues

Sources retenues:
- code du depot;
- baseline Phase 0;
- cartographie Phase 1;
- design Phase 2;
- tests existants sur `memory_retrieved` et `memory_arbitration`;
- runtime OVH en lecture seule.

Preuves runtime relues pour cette phase:
- `memory_store.retrieve()` + enrichissement + `build_memory_retrieved_input()` sur `qui suis-je pour toi maintenant identite durable`;
- `build_memory_arbitration_input()` rejoue en mode pur, sans appel LLM;
- lecture read-only de `memory_store.get_arbiter_decisions(limit=3)`;
- lecture read-only de `observability.chat_log_events` pour `prompt_prepared` et `hermeneutic_node_insertion`;
- lecture SQL read-only des doublons exacts dans `traces`.

Constats factuels confirms:
- `raw_traces` ne portent encore aucun identifiant canonique;
- `memory_retrieved.traces[*]` portent deja un `candidate_id` stable;
- `memory_arbitration.decisions[*]` savent deja relier `retrieved_candidate_id` et `legacy_candidate_id`;
- `arbiter_decisions` persiste encore seulement l'index legacy `candidate_id`;
- `prompt_prepared` ne persiste aujourd'hui que des compteurs d'injection memoire, pas des IDs candidats;
- `hermeneutic_node_insertion` ne persiste aujourd'hui qu'un resume de counts, pas la liste des IDs;
- des collisions reelles existent deja en base (`Je suis Christophe Muck` x6, URL Mediapart x6, `Qui suis-je ?` x5, `Qui suis-je pour toi maintenant ?` x4, etc.);
- `summaries=0` en live, mais `summary_id` et `parent_summary` existent deja dans le contrat des traces.

## 4. Probleme que la spec doit resoudre

Aujourd'hui:
- le retrieval brut reste plat et sans identifiant canonique;
- l'arbitre travaille encore sur un index legacy par position;
- le prompt final ne garde plus aucun lien stable avec les candidats;
- la dedup n'est pas un objet explicite du pipeline;
- `parent_summary` enrichit l'aval mais n'entre pas dans le panier vu par l'arbitre.

Le contrat cible doit donc:
- garder le lien avec `memory_retrieved`;
- permettre une dedup avant arbitre;
- rester suffisamment borne pour un premier lot V2 sans reranker;
- preparer la coexistence future de `traces` et `summaries` sans ouvrir la Phase 4.

## 5. Decision de cloture Phase 3

Les decisions normatives de cette spec sont:
- l'identifiant stable du panier pre-arbitre est le `candidate_id` deja calcule dans `memory_retrieved`, pas un nouvel ID concurrent;
- un candidat pre-arbitre peut representer plusieurs items retrieves via `source_candidate_ids`;
- la taille maximale du panier remis a l'arbitre est `8`;
- `parent_summary` complet reste hors payload arbitre et n'est resolu qu'en aval pour le prompt;
- la dedup devient une responsabilite explicite du panier pre-arbitre, pas de l'arbitre;
- la relation stable cible est `memory_retrieved.candidate_id -> panier pre-arbitre.candidate_id -> decision arbitre.candidate_id -> injection prompt.candidate_id`.

## 6. Quatre niveaux de representation a distinguer

### 6.1 Retrieval brut

Role:
- produire le recall vectoriel brut avant toute structuration.

Source de verite:
- `memory_traces_summaries.retrieve()`

Champs presents aujourd'hui:
- `conversation_id`
- `role`
- `content`
- `timestamp`
- `summary_id`
- `score`

Champs absents:
- `candidate_id`
- `source_lane`
- `dedup_key`
- `parent_summary_present`
- tout champ d'arbitrage
- tout champ d'injection prompt

Consommateur suivant:
- construction de `memory_retrieved`
- structuration du panier pre-arbitre cible

### 6.2 Panier pre-arbitre cible

Role:
- presenter a l'arbitre un pool borne, dedupe et relie de facon stable au retrieval canonique.

Source de verite cible:
- structuration aval de `memory_retrieved`

Champs presents:
- champs obligatoires du schema cible en section 7

Champs absents du payload arbitre:
- `parent_summary` complet
- texte rendu pour le prompt
- diagnostics verbeux de dedup

Consommateur suivant:
- projection arbitre V2
- prompt builder pour les candidats gardes

### 6.3 Decision arbitre

Role:
- trier un panier deja structure et borné, pas compenser un recall brut encore plat.

Source de verite cible:
- sortie arbitre + `memory_arbitration`

Champs presents:
- `candidate_id` stable
- verdict et scores arbitre
- compatibilite legacy transitoire tant que l'implementation ne migre pas

Champs absents:
- `parent_summary` complet
- details de dedup non necessaires au jugement
- rendu prompt final

Consommateur suivant:
- `memory_traces` dedupes gardes
- observabilite / diagnostics
- prompt final

### 6.4 Prompt final

Role:
- injecter seulement les representants gardes, sous forme lisible pour le modele final.

Source de verite cible:
- candidats gardes apres arbitrage + resolution aval des supports prompt

Champs presents dans le prompt lui-meme:
- `role`
- `content`

Champs absents du prompt lui-meme:
- `candidate_id`
- `retrieval_score`
- `semantic_relevance`
- `contextual_gain`
- `dedup_key`
- `summary_id`

Lien stable cible:
- hors texte prompt, via la metadonnee de runtime/observabilite d'injection

## 7. Schema candidat cible du panier pre-arbitre

## 7.1 Champs obligatoires

Chaque candidat du panier pre-arbitre DOIT porter:

- `candidate_id`
  - identifiant stable du representant
  - DOIT reutiliser un `memory_retrieved.traces[*].candidate_id` existant
- `source_candidate_ids`
  - liste non vide des `candidate_id` de `memory_retrieved` absorbes dans ce slot
  - DOIT contenir `candidate_id`
- `source_kind`
  - enum initial: `trace | summary`
- `source_lane`
  - enum initial: `global | user | assistant | recent | conversation_diversity | summaries`
- `conversation_id`
  - conversation du representant
- `role`
  - enum initial: `user | assistant | summary`
- `content`
  - texte representatif soumis a l'arbitre et, si garde, a l'injection memoire
- `timestamp_iso`
  - timestamp du representant
  - pour un `summary`, ce champ represente l'ancre temporelle de reference retenue pour le resume
- `retrieval_score`
  - score du representant retenu
- `summary_id`
  - `null` ou identifiant de summary associe
  - DOIT etre renseigne pour `source_kind=summary`
- `parent_summary_present`
  - booleen
- `dedup_key`
  - cle canonique de collision / regroupement avant arbitre

## 7.2 Champs optionnels et bornes

Un candidat PEUT porter, pour diagnostic et pilotage local:

- `recency_bucket`
  - enum conseille: `recent | middle | stale`
- `conversation_rank`
  - rang du representant a l'interieur de sa conversation d'origine apres merge local
- `dedup_reason_code`
  - enum conseille: `none | exact_duplicate | lexical_near_duplicate | same_conversation_same_idea | trace_summary_collision`

Ces champs ne sont pas requis pour fermer la Phase 3, mais leur place est tranchee:
- ils appartiennent au panier cible;
- ils restent diagnostic-only dans un premier lot V2.

## 7.3 Invariants du schema

Le panier pre-arbitre cible DOIT respecter:

- `candidate_id` unique dans le panier;
- `source_candidate_ids` disjoints entre candidats du panier;
- `dedup_key` unique dans le panier final;
- `source_candidate_ids` non vides;
- `candidate_id in source_candidate_ids`;
- `parent_summary_present=false` si `source_kind=summary`;
- `summary_id != null` si `source_kind=summary`;
- `parent_summary_present=true` implique `summary_id != null`;
- aucun candidat du panier ne represente un item deja absorbe par un autre.

## 7.4 Exemple cible

```json
{
  "candidate_id": "cand-0c575f34c4f459c3",
  "source_candidate_ids": [
    "cand-0c575f34c4f459c3",
    "cand-b9fe5f2119df44aa"
  ],
  "source_kind": "trace",
  "source_lane": "user",
  "conversation_id": "bced07c2-4166-4627-b794-3235394af996",
  "role": "user",
  "content": "Qui suis-je pour toi maintenant ?",
  "timestamp_iso": "2026-04-04 22:16:15+02:00",
  "retrieval_score": 0.8787206411361694,
  "summary_id": null,
  "parent_summary_present": false,
  "dedup_key": "trace:user:qui-suis-je-pour-toi-maintenant",
  "recency_bucket": "stale",
  "conversation_rank": 1,
  "dedup_reason_code": "exact_duplicate"
}
```

## 8. Projection cible remise a l'arbitre

## 8.1 Champs que l'arbitre doit effectivement voir dans un premier lot V2

Le payload arbitre cible DOIT voir seulement:

- `candidate_id`
- `source_kind`
- `source_lane`
- `role`
- `content`
- `timestamp_iso`
- `retrieval_score`

Justification:
- cela enrichit legerement le panier actuel avec une provenance utile;
- cela garde le payload lisible;
- cela n'ouvre pas encore un redesign complet de l'arbitre.

## 8.2 Champs exclus du premier payload arbitre

Les champs suivants DOIVENT rester hors payload arbitre:

- `conversation_id`
- `summary_id`
- `parent_summary_present`
- `parent_summary`
- `source_candidate_ids`
- `dedup_key`
- `dedup_reason_code`
- `recency_bucket`
- `conversation_rank`

Justification:
- ces champs servent surtout a la structuration, au diagnostic et au rendu aval;
- ils ne doivent pas gonfler le prompt arbitre tant que la Phase 3 n'a pas besoin de redesign complet du jugement.

## 9. Champs diagnostic-only et prompt-only

## 9.1 Diagnostic-only

Restent diagnostic-only dans un premier lot V2:

- `conversation_id`
- `summary_id`
- `parent_summary_present`
- `source_candidate_ids`
- `dedup_key`
- `dedup_reason_code`
- `recency_bucket`
- `conversation_rank`

Ces champs servent a:
- verifier la composition du panier;
- relier un representant a ses candidats sources;
- expliquer les collisions et merges;
- mesurer recence et diversite.

## 9.2 Prompt-only

Restent prompt-only, c'est-a-dire resolus seulement apres arbitrage:

- `parent_summary` complet
- le bloc `[Contexte du souvenir ...]`
- le rendu final des souvenirs injectes

Point normatif:
- le prompt final ne DOIT pas reintroduire sous forme structuree les champs de diagnostic du panier;
- la liaison stable avec le panier doit passer par les artefacts runtime/observabilite, pas par le texte du prompt.

## 10. Decision tranchee sur `parent_summary`

Decision retenue:
- `parent_summary` complet est absent du panier vu par l'arbitre;
- `parent_summary_present` existe dans le panier cible comme signal diagnostic;
- le contenu de `parent_summary` n'est resolu qu'en aval, pour les candidats gardes, au moment du rendu prompt.

Donc:
- `parent_summary` n'est pas un hint arbitre dans le premier lot V2;
- `parent_summary` est un support prompt-only/downstream;
- l'arbitre juge le souvenir represente, pas son contexte resume parent.

Raison:
- la cartographie Phase 1 montre que l'arbitre n'en a pas besoin aujourd'hui pour fonctionner;
- la Phase 3 doit structurer le panier sans ouvrir un redesign complet de l'arbitre;
- `summaries=0` en live, donc il serait premature de remodeler le prompt arbitre autour d'un objet encore absent.

## 11. Regle cible de dedup

La dedup est une responsabilite du panier pre-arbitre.

L'arbitre ne doit pas recevoir plusieurs slots qui racontent la meme chose sans gain net.

## 11.1 Doublon exact

Definition:
- deux items sont en doublon exact si leur `content_norm` est identique apres normalisation canonique de texte.

Traitement cible:
- fusion OBLIGATOIRE en un seul slot pre-arbitre;
- `source_candidate_ids` DOIT accumuler tous les `candidate_id` sources;
- le representant DOIT etre choisi ainsi:
  - score de retrieval le plus eleve;
  - a score egal, preference `user > assistant > summary`;
  - a nouveau score egal, timestamp le plus recent.

Resultat:
- un seul slot arbitre;
- les autres occurrences restent seulement tracees dans `source_candidate_ids`.

## 11.2 Quasi-doublon lexical

Definition:
- deux items sont en quasi-doublon lexical s'ils different legerement dans la formulation mais n'apportent pas de fait, nuance ou contrainte nouvelle.

Traitement cible:
- fusion si le second item n'ajoute aucun detail actionnable ou memorisable;
- garder separes si la reformulation introduit une contrainte, une preference ou un fait distinct.

Preference de representant:
- pour un fait utilisateur durable, preference a la formulation `user`;
- pour une synthese vraiment plus dense qui subsume plusieurs traces, preference possible a `summary`, mais seulement selon la regle 11.4;
- sinon, garder l'item au meilleur rapport `specificite utile / retrieval_score`.

Resultat:
- pas plus d'un slot arbitre par quasi-meme idee.

## 11.3 Collision meme conversation / meme idee

Definition:
- plusieurs traces de la meme conversation expriment la meme idee, souvent sous forme `user` puis paraphrase `assistant`, ou redites user successives.

Traitement cible:
- fusion par defaut en un seul slot;
- preference a la trace `user` quand elle porte deja le fait ou la preference utile;
- conserver une trace `assistant` seulement si elle ajoute une synthese operationnelle absente de la trace `user`.

Regle normative:
- une meme conversation ne doit pas occuper plusieurs slots arbitre pour une meme `dedup_key`.

## 11.4 Collision trace / summary

Definition:
- un `summary` et une ou plusieurs `traces` couvrent la meme idee ou la meme fenetre de souvenir.

Traitement cible:
- ne jamais garder en meme temps dans le panier arbitre une `trace` et un `summary` qui couvrent la meme idee sans gain distinct;
- preferer `summary` si:
  - il subsume plusieurs traces;
  - il ne fait perdre aucun detail necessaire;
  - il fournit une forme plus compacte et plus stable;
- preferer `trace` si:
  - elle porte une formulation utilisateur precise;
  - elle transporte un detail que le summary n'explicite pas;
  - elle est la meilleure ancre pour la reponse suivante.

Resultat:
- un seul representant par collision `trace/summary`;
- les non-representants sont absorbes dans `source_candidate_ids`.

## 12. Strategie de linkage stable

## 12.1 Entre retrieval et panier pre-arbitre

Le lien stable cible est:
- `memory_retrieved.traces[*].candidate_id` = identifiant canonique primaire.

Le panier pre-arbitre DOIT:
- reutiliser l'un de ces `candidate_id` comme `candidate_id` representant;
- exposer tous les candidats sources dans `source_candidate_ids`.

Decision importante:
- la Phase 3 ne cree pas un deuxieme espace d'IDs concurrent au-dessus de `memory_retrieved`.

## 12.2 Entre panier pre-arbitre et decision arbitre

La decision arbitre cible DOIT etre keyed par `candidate_id` stable.

Compatibilite transitoire acceptee:
- `legacy_candidate_id`
- `legacy_candidate_index`

Mais ces champs legacy:
- ne sont qu'un pont d'implementation;
- ne sont pas la source de verite cible.

Schema cible minimal de decision:

```json
{
  "candidate_id": "cand-0c575f34c4f459c3",
  "keep": true,
  "semantic_relevance": 0.91,
  "contextual_gain": 0.72,
  "redundant_with_recent": false,
  "reason": "best_match",
  "decision_source": "llm",
  "model": "..."
}
```

## 12.3 Entre decision arbitre et item injecte

Le rendu prompt final DOIT rester textuel, mais le chainage stable cible est:
- un item injecte dans `[Mémoire — souvenirs pertinents]` correspond a un `candidate_id` garde;
- un item garde ne peut pas etre injecte deux fois sous deux formes concurrentes;
- les artefacts runtime/observabilite d'injection DOIVENT pouvoir lister les `candidate_id` effectivement injectes.

Constat actuel utile:
- `prompt_prepared` ne porte aujourd'hui que des compteurs d'injection;
- le lien durable `decision -> injection` n'existe donc pas encore en runtime actif.

Decision de contrat:
- le futur lot d'implementation du panier devra introduire ce lien hors texte prompt, sans transformer le prompt final en objet JSON structure.

## 13. Taille cible maximale du panier remis a l'arbitre

Decision retenue:
- taille maximale cible avant arbitre: `8` candidats.

Justification:
- la Phase 2 recommande une union multi-lanes, qui a besoin de plus d'espace que le `top_k=5` actuel;
- la Phase 0 montre que le probleme primaire est la composition, pas un besoin prouve d'un panier large;
- `8` laisse de la place pour:
  - un filet global un peu plus large;
  - une reservation `user`;
  - un petit backfill `assistant`;
  - sans rendre le jugement arbitre illisible;
- `8` reste defendable avant reranker:
  - assez grand pour corriger la composition;
  - assez petit pour rester inspectable manuellement probe par probe;
  - assez borne pour ne pas demander un second passage de reranking.

Regle normative:
- ce `8` est un maximum apres merge et dedup, pas un quota par lane.

## 14. Regle cible pour eviter l'injection double

Pour un meme tour:

- un `candidate_id` garde ne peut etre injecte qu'une fois dans `[Mémoire — souvenirs pertinents]`;
- un `summary_id` ne peut pas apparaitre a la fois comme:
  - candidat `summary` injecte;
  - et contexte parent d'une trace injectee concurrente portant la meme idee;
- si un `summary` represente la collision, les traces absorbees ne doivent plus etre injectees separement;
- si une `trace` represente la collision, son `parent_summary` peut encore alimenter le bloc contextuel, mais ce `summary` ne doit pas etre reinjecte comme item memoire autonome dans le meme tour.

But:
- une idee = une seule voie d'injection finale.

## 15. Consequence pratique pour le lot suivant

La Phase 3 debloque un futur lot d'implementation borne au panier pre-arbitre si ce lot:
- reutilise `memory_retrieved.candidate_id` comme source de verite;
- construit le panier cible avec `source_candidate_ids` et `dedup_key`;
- borne le panier final a `8`;
- garde `parent_summary` hors arbitre;
- n'ouvre toujours pas la voie `summaries` live;
- ne change pas encore les seuils arbitre ni le reranker.

Ce que cette spec ne debloque pas encore:
- la Phase 4 `summaries`;
- la Phase 5 feuille d'evaluation;
- la Phase 9 reranker.

## 16. Verdict de cloture Phase 3

La Phase 3 est fermable proprement au `2026-04-10` car cette spec:
- fixe un schema candidat cible;
- distingue champs arbitre, diagnostic-only et prompt-only;
- tranche la place de `parent_summary`;
- ecrit une vraie doctrine de dedup exploitable;
- fixe un chainage stable des IDs;
- fixe une taille maximale du panier pre-arbitre defendable avant reranker.
