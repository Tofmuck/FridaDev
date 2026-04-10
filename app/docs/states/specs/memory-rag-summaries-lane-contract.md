# Memory RAG - voie summaries - contrat minimal et statut de readiness - 2026-04-10

Statut: reference normative active
Classement: `app/docs/states/specs/`
Portee: contrat minimal de la lane `summaries`, doctrine de fusion `traces + summaries`, et decision de readiness Phase 4
Roadmap liee: `app/docs/todo-todo/memory/memory-rag-relevance-todo.md`
Baselines liees:
- `app/docs/states/baselines/memory-rag-relevance-baseline-2026-04-10.md`
- `app/docs/states/baselines/memory-rag-8C-evaluation-2026-04-10.md`
Cartographie liee: `app/docs/states/architecture/memory-rag-current-pipeline-cartography.md`
Design lie: `app/docs/states/architecture/memory-rag-candidate-generation-design.md`
Spec liee: `app/docs/states/specs/memory-rag-pre-arbiter-basket-contract.md`

## 1. Objet

Cette spec ferme la Phase 4 du chantier `memory-rag-relevance`.

Apres implementation du lot `8C`, elle reste la reference normative du contrat minimal de la lane `summaries`; la baseline `8C` archive le verdict runtime et rappelle que le live OVH reste neutre tant que `summaries=0`.

Elle fixe, sans patch runtime:
- la cause retenue de `summaries=0` sur le runtime OVH observe;
- le statut de readiness de la voie `summaries`;
- la strategie de preparation recommandee avant implementation;
- le schema minimal d'un candidat `summary`;
- le mode de retrieval `summary` a comparer a la lane `traces`;
- la politique de fusion `traces + summaries`;
- la politique d'antidoublon `trace / summary`;
- la mesure de gain reel attendue;
- les preuves minimales requises avant toute implementation du lot C.

Elle ne fait pas:
- l'implementation de la lane `summaries`;
- la generation live de nouveaux resumes;
- un patch des seuils de summarization;
- un redesign du panier Phase 3;
- un ajout de reranker;
- le design de la surface finale d'observabilite.

## 2. Pourquoi une spec et non une simple note d'architecture

Le sujet ne se limite plus a une description du runtime.

Il faut maintenant figer:
- un verdict de readiness;
- un schema minimal;
- une doctrine normative de coexistence `trace / summary`;
- une methode de comparaison avant implementation;
- une liste de preuves minimales.

Le bon emplacement est donc `states/specs/`, pas `states/architecture/`.

## 3. Sources et preuves relues

Sources retenues:
- code du depot;
- TODO Phase 4 actif;
- baseline Phase 0;
- cartographie Phase 1;
- design Phase 2;
- spec Phase 3 du panier pre-arbitre;
- tests existants sur `summarizer`, `memory_retrieved` et l'enrichissement `parent_summary`;
- runtime OVH en lecture seule.

Preuves runtime relues pour cette phase:
- baseline DB read-only sur `summaries`, `traces.summary_id`, `conversation_messages.summarized_by`;
- analyse read-only des conversations existantes contre `SUMMARY_THRESHOLD_TOKENS` et `SUMMARY_KEEP_TURNS`;
- probe `retrieve() + enrich_traces_with_summaries()` en no-op logger local pour verifier `summary_id` et `parent_summary`;
- lecture read-only des admin logs retenus pour `summary_generated`, `summarize_trigger`, `summarize_done`, `summary_db_save_failed`;
- lecture read-only de `observability.chat_log_events` pour verifier l'absence de stage `summary*`.

Constats factuels confirms:
- `summaries.total = 0` et `summaries.embedded = 0`;
- `traces.with_summary_id = 0 / 224`;
- `conversation_messages.summarized = 0 / 280`;
- le runtime actif expose bien une voie de summarization en code, mais aucune trace live de generation n'est retenue sur OVH;
- sur `54` conversations user/assistant relues, aucune ne depasse le seuil `35000` tokens;
- le plus gros lot non resume observe atteint `11658` tokens, donc reste tres en dessous du seuil;
- `SUMMARY_KEEP_TURNS = 5` laisse pourtant de la matiere resumable sur `3` conversations (`candidate_messages_to_summarize > 0`);
- le retrieval live enrichi reste sans `summary_id` et sans `parent_summary` sur les probes rejoues;
- aucun event `summary_generated`, `summarize_trigger`, `summarize_done` ou `summary_db_save_failed` n'apparait dans les admin logs retenus;
- aucun stage `summary*` n'apparait dans `observability.chat_log_events`.

## 4. Verdict Phase 4

Decision de cloture:
- la voie `summaries` est **specifiee mais bloquee live** sur le runtime OVH observe;
- elle n'est pas prete a etre evaluee live, car aucune donnee `summary` n'existe encore en base;
- la cause retenue de `summaries=0` est **l'absence de generation live declenchee**, elle-meme expliquee principalement par un volume conversationnel insuffisant au regard du seuil courant de `35000` tokens;
- `SUMMARY_KEEP_TURNS` n'est pas la cause principale observee: certaines conversations laisseraient deja des messages resumables si le seuil etait atteint;
- aucune autre cause live n'est necessaire pour expliquer le `0` actuel.

Ce verdict est fonde sur des preuves read-only, pas sur une intuition.

## 5. Cause retenue de `summaries=0`

### 5.1 Ce que fait le code

Le runtime peut generer un resume seulement si:
- `chat_service` appelle `summarizer.maybe_summarize()` pendant un vrai tour de chat;
- les messages `user`/`assistant` non resumes depassent `SUMMARY_THRESHOLD_TOKENS`;
- il reste, apres exclusion des `SUMMARY_KEEP_TURNS` derniers tours, des messages a resumer;
- l'appel LLM de summarization reussit, puis `save_summary()` et `update_traces_summary_id()` ecrivent en base.

### 5.2 Ce qui est observe live

Sur OVH:
- aucun resume n'est present en base;
- aucun message n'est marque `summarized_by`;
- aucune trace n'est liee a un `summary_id`;
- aucune conversation observee ne franchit le seuil `35000`;
- les plus grosses conversations restent a `11658` et `10620` tokens non resumes;
- `3` conversations laisseraient deja respectivement `26`, `12` et `4` messages resumables si le seuil etait franchi.

### 5.3 Cause retenue

La cause retenue est donc:
- **pas de generation live**, parce que **le seuil de summarization n'est jamais atteint sur les conversations observees**.

Ce n'est pas:
- une panne de table `summaries`;
- une panne evidente de backfill `summary_id`;
- une panne evidente de persistence `summarized_by`;
- ni un simple effet de `SUMMARY_KEEP_TURNS` seul.

## 6. Strategie de preparation retenue

Decision retenue:
- **combinaison ordonnee `fixtures de tests -> replay hors live`**;
- **attente de donnees live rejetee comme strategie principale**.

Ordre recommande:
1. Fixtures de tests pour figer le contrat minimal, la fusion et la non-double injection.
2. Replay hors live sur snapshots de conversations ou sur fixtures enrichies pour comparer `traces` vs `summaries`.
3. Eventuelle verification live plus tard seulement si des resumes existent reellement.

Pourquoi ce choix:
- attendre le live seul bloquerait le chantier sur un seuil actuellement jamais atteint;
- les fixtures permettent de fermer les invariants sans LLM ni ecritures live;
- le replay hors live permet une evaluation comparative sur probes sans polluer la prod.

## 7. Place de la lane `summaries` dans l'ordre du chantier

La voie `summaries` reste:
- distincte du candidate generation Phase 2;
- distincte du contrat de panier Phase 3;
- anterieure a toute decision reranker;
- distincte de la future surface finale d'observabilite.

Cette phase ne reouvre ni la Phase 2 ni la Phase 3.

Elle fixe seulement:
- le contrat minimal de la lane `summaries`;
- sa doctrine de coexistence avec `traces`;
- et les prerequis de preuve du futur lot C.

## 8. Schema minimal d'un candidat `summary`

## 8.1 Schema minimal de la lane `summaries` avant panier

Un candidat `summary` brut DOIT porter:
- `summary_id`
  - identifiant du resume en table `summaries`
- `conversation_id`
  - conversation d'origine du resume
- `content`
  - texte du resume
- `start_ts`
  - debut de la fenetre couverte
- `end_ts`
  - fin de la fenetre couverte
- `timestamp_iso`
  - ancre temporelle retenue pour la comparaison et la normalisation
  - decision retenue: `timestamp_iso = end_ts`
- `retrieval_score`
  - score vectoriel du resume pour la query
- `source_kind`
  - valeur fixee a `summary`
- `source_lane`
  - valeur fixee a `summaries`
- `role`
  - valeur fixee a `summary`

Un candidat `summary` brut PEUT porter:
- `covered_trace_count`
  - nombre de traces couvertes, si connu sans cout excessif
- `covered_trace_ids`
  - seulement en replay/fixtures, pas requis pour le retrieval minimal
- `window_label`
  - support diagnostic lisible derive de `start_ts` et `end_ts`

## 8.2 Relation avec le contrat Phase 3

Quand un candidat `summary` entre dans le panier pre-arbitre Phase 3, il DOIT etre normalise comme suit:
- `candidate_id = "summary:" + summary_id`
- `source_candidate_ids = [candidate_id]` tant qu'aucune trace n'a ete absorbee
- `source_kind = "summary"`
- `source_lane = "summaries"`
- `conversation_id = conversation_id`
- `role = "summary"`
- `content = content`
- `timestamp_iso = end_ts`
- `retrieval_score = retrieval_score`
- `summary_id = summary_id`
- `parent_summary_present = false`
- `dedup_key` derive de la cle semantique retenue par le lot B

Si un candidat `summary` absorbe ensuite des traces lors de la fusion, `source_candidate_ids` DOIT s'elargir pour inclure les `candidate_id` traces absorbes.

## 8.3 Invariants minimaux

Pour la lane `summaries`, les invariants suivants sont fixes:
- `summary_id` DOIT toujours etre non nul;
- `start_ts <= end_ts`;
- `timestamp_iso` DOIT correspondre a `end_ts`;
- `source_kind` DOIT toujours valoir `summary`;
- `source_lane` DOIT toujours valoir `summaries`;
- `role` DOIT toujours valoir `summary`;
- `parent_summary_present` DOIT rester `false` pour un candidat `summary`.

## 9. Retrieval `summary` a comparer

Decision retenue pour la comparaison minimale:
- utiliser le meme embedding de query que la lane `traces`;
- faire un retrieval vectoriel direct sur `summaries.embedding`;
- comparer une lane `summaries_top3` a la strategie `traces` figee en Phase 2;
- merger ensuite les deux lanes sous le contrat Phase 3, sans depasser le panier cible de `8` slots.

Pourquoi `top3`:
- un resume represente potentiellement plusieurs traces;
- la lane `summaries` doit rester un complement borne, pas remplacer tout le recall `traces`;
- un budget plus large gonflerait le panier avant meme d'avoir prouve un gain reel.

Ce qui est hors scope de ce premier compare:
- query rewriting;
- retrieval hybride lexical + vectoriel pour `summaries`;
- reranker;
- ouverture d'une lane `summaries` dominante.

## 10. Politique de fusion `traces + summaries`

Doctrine retenue:
- la lane `summaries` est une lane de **compression et de couverture d'idees**, pas une lane de remplacement automatique des traces;
- `traces` restent la source preferee pour les faits precis, preferences explicites, formulations identitaires, citations et details operatoires;
- `summaries` peuvent devenir representants quand ils couvrent plusieurs traces utiles sans perdre l'information necessaire au probe.

Regle de fusion:
1. Recuperer les candidats `traces` et `summaries` separement.
2. Normaliser les candidats `summary` au contrat Phase 3.
3. Detecter les collisions `trace / summary` avant arbitre.
4. Ne garder qu'un representant par idee candidate, sauf si le `summary` apporte une couverture supplementaire non redondante.
5. Resoudre `parent_summary` seulement en aval pour les traces gardees; un `summary` candidat ne doit pas reintroduire un deuxieme bloc prompt autonome pour la meme idee.

## 11. Politique d'antidoublon `trace / summary`

### 11.1 Meme idee, granularite comparable

Si une trace et un summary couvrent la meme idee a granularite proche:
- garder un seul slot;
- preferer le `summary` seulement s'il subsume la trace sans perte utile;
- sinon preferer la `trace`.

### 11.2 Meme idee, granularite differente

Si le `summary` est plus large mais la `trace` porte le fait utile:
- garder la `trace` comme representant;
- autoriser le `summary` seulement comme contexte aval si necessaire;
- interdire un double slot simultane pour la meme idee.

### 11.3 Summary trop large mais utile

Si le `summary` couvre plusieurs idees et reste pertinent:
- il PEUT representer plusieurs traces si le probe cherche une vue d'ensemble;
- il ne DOIT PAS evincer une trace precise si le probe vise une preference, une identite, une citation ou une decision concrete.

### 11.4 Summary redondant sans gain

Si le `summary` ne fait que reformuler une trace sans meilleure couverture:
- rejeter le `summary`;
- conserver la `trace` ou l'autre representant deja retenu.

### 11.5 Collision parent trace / summary

Si une trace et son propre resume parent coexistent:
- un seul slot memoire DOIT survivre dans le panier;
- la decision initiale preferee est:
  - `summary` si le probe est large et si le resume subsume sans perte;
  - `trace` si le probe demande un detail exact;
- si la `trace` gagne, le `summary` parent reste autorise seulement comme contexte prompt aval, pas comme second item memoire autonome.

## 12. Mesure du gain reel d'une lane `summaries`

La lane `summaries` ne sera pas consideree utile parce qu'elle produit "plus de texte" ou "un texte plus joli".

Le gain reel DOIT etre lu via:
- meilleure couverture utile sur le corpus canonique;
- reduction du bruit et de la duplication dans le panier pre-arbitre;
- meilleure couverture d'idees sans inflation du nombre de slots;
- absence d'injection double `trace + summary`;
- maintien ou amelioration de la lisibilite du prompt final.

Signaux positifs attendus:
- au moins un probe ou un `summary` apporte une idee utile absente ou mal couverte par `traces` seules;
- baisse du nombre de collisions `trace / summary` visibles dans le panier final;
- aucune degradation nette sur les probes identitaires ou de preferences durables.

Signaux d'echec:
- `summaries` ajoutent seulement des paraphrases;
- le panier grossit sans meilleure couverture;
- une meme idee est injectee deux fois;
- des traces precises utiles sont remplacees par des resumes trop vagues.

## 13. Preuves minimales avant implementation du lot C

Le lot C NE DOIT PAS commencer sans les preuves minimales suivantes.

### 13.1 Fixtures minimales

Il faut au minimum des fixtures couvrant:
- un `summary` qui subsume proprement plusieurs traces d'une meme idee;
- un cas ou une `trace` doit rester preferee a un `summary` plus large;
- un cas `trace + parent_summary` sans double injection;
- un cas `summary` redondant sans gain, donc rejete;
- un cas ou plusieurs traces d'une meme conversation sont remplacees par un seul `summary`.

### 13.2 Replay hors live minimal

Il faut un replay hors live qui:
- reutilise le corpus canonique de probes Phase 0;
- compare `traces` seules, `summaries` seules et merge `traces + summaries`;
- archive les resultats avant/apres de facon relisible;
- n'ecrit ni conversation live, ni logs applicatifs parasites.

### 13.3 Verifications de contrat

Il faut prouver:
- la stabilite du mapping `summary_id -> candidate_id`;
- la compatibilite du candidat `summary` avec le contrat Phase 3;
- l'absence de double comptage dans `source_candidate_ids`;
- l'absence d'injection double dans le prompt final;
- la lisibilite de la fusion quand une trace absorbe ou est absorbee par un `summary`.

### 13.4 Verifications de gain

Il faut prouver:
- qu'au moins un probe gagne en couverture utile ou en compaction utile;
- que le bruit et la duplication n'augmentent pas;
- qu'aucune regression nette n'apparait sur les probes de preferences durables et d'identite;
- que la lane `summaries` peut etre explicitement ajournee si aucun gain n'est demontre.

## 14. Non-goals explicites

Cette spec ne fige pas:
- l'implementation exacte du retrieval `summaries`;
- les requetes SQL finales;
- les endpoints admin ou d'observabilite;
- les composants UI;
- une modification de `SUMMARY_THRESHOLD_TOKENS`;
- une politique reranker.

## 15. Decision de cloture Phase 4

La Phase 4 est fermee avec le statut suivant:
- la voie `summaries` est **bloquee live** sur OVH au 2026-04-10;
- sa preparation est **choisie et ordonnee**: `fixtures -> replay hors live`;
- son schema minimal est ecrit;
- sa doctrine de fusion `traces + summaries` est ecrite;
- sa politique d'antidoublon `trace / summary` est ecrite;
- ses preuves minimales avant implementation sont ecrites.

Le futur lot C pourra donc:
- implementer la lane sur une base specifiee;
- ou conclure a son ajournement si les preuves hors live ne montrent aucun gain.
