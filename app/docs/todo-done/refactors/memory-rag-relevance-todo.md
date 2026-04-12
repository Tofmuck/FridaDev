# Memory RAG Relevance - TODO implementation roadmap (v2)

Statut: ferme au `2026-04-12`
Classement: `app/docs/todo-done/refactors/`
Portee: roadmap de travail pour la pertinence du retrieval memoire/RAG en amont de l'arbitre
Derniere revue documentaire: `2026-04-12`
Origine: audit doc + code + runtime OVH du `2026-04-10`
Doc liee: `app/docs/todo-todo/memory/hermeneutical-add-todo.md`

Legende minimale:
- `[x]` = ferme
- `[ ]` = a faire
- `[~]` = tente / evalue / non retenu a ce stade

## Intention

Transformer le TODO macro initial en plan de travail executable, borne, sequence et verifiable, sans lancer dans ce tour l'implementation de la V2 memoire/RAG.

La doctrine conservee est explicite:
- d'abord assainir le candidate generation;
- ensuite structurer le panier remis a l'arbitre;
- ensuite faire de `summaries` une vraie voie si elle devient disponible;
- ensuite prendre une decision documentaire explicite `go / no-go` sur un reranker de second rang;
- et seulement en fin de chantier, apres cette decision, ouvrir le lot de surface d'observabilite memoire/RAG dediee.

## Verdict d'audit integre

- [x] Le TODO precedent avait la bonne doctrine macro: recall avant reranker, et reranker tardif.
- [x] Le TODO precedent etait trop grossier pour piloter des lots petits et reversibles.
- [x] Le TODO precedent melangeait audit/probes, design de contrat, implementation et validation finale dans les memes items.
- [x] Le TODO precedent ne separait pas assez clairement:
  - ce que voit le retrieval,
  - ce que voit l'arbitre,
  - ce que recoit ensuite le prompt,
  - et ce qui est seulement logge pour le noeud hermeneutique.
- [x] Le TODO precedent ne figeait ni corpus de probes, ni taxonomy de faux positifs, ni gates entre phases.
- [x] Le TODO precedent n'explicitait pas assez les preconditions de la voie `summaries`, alors que le runtime OVH actif n'en contient actuellement aucune.
- [x] Le TODO precedent n'isolait pas encore explicitement un lot final de surface d'observabilite memoire/RAG distinct de l'admin general et posterieur a la decision reranker.

## Baseline runtime factuelle au 2026-04-10

- [x] Runtime observe sur OVH: `HERMENEUTIC_MODE=enforced_all`, `MEMORY_TOP_K=5`, `ARBITER_MAX_KEPT_TRACES=3`, `ARBITER_MIN_SEMANTIC_RELEVANCE=0.62`, `ARBITER_MIN_CONTEXTUAL_GAIN=0.55`.
- [x] Snapshot base observe: `traces=224` (`224` avec `embedding IS NOT NULL`), `summaries=0` (`0` avec `embedding IS NOT NULL`), `traces_with_summary_id=0`.
- [x] Repartition live des traces: `assistant=112`, `user=112`.
- [x] `memory_traces_summaries.retrieve()` interroge aujourd'hui `traces` seulement, via un rappel hybride borne: dense vectoriel, lane FTS `simple` et voie exacte indexee `pg_trgm`.
- [x] `summaries` est persiste en theorie mais n'est pas une voie de retrieval live; sur OVH au `2026-04-10`, la table est vide.
- [x] `chat_memory_flow.prepare_memory_context()` enrichit les traces avec `parent_summary` apres le retrieval, puis construit `memory_retrieved`.
- [x] `arbiter.filter_traces_with_diagnostics()` voit un payload plat compose de `id`, `role`, `content`, `ts`, `retrieval_score`, `semantic_score`, plus le contexte recent; il ne voit pas `parent_summary`.
- [x] Les decisions arbitre sont deja observables en base via `arbiter_decisions`; snapshot lu: `551` decisions, toutes `decision_source=llm`, avec `32` gardees et `519` rejetees.
- [x] Des doublons exacts existent deja dans `traces`; exemples lus: `Je suis Christophe Muck` (`6` occurrences), `Qui suis-je ?` (`5`), `Bonsoir Frida` (`5`).

## Probes runtime relues pendant cet audit

- [x] Probe `architecture modules externes arbiter STT TTS`: top-5 surtout assistant generique/procedural; aucun `summary_id`, aucun `parent_summary`.
- [x] Probe `memoire identite durable episodique utilisateur`: top-5 attire surtout des questions repetitives sur la memoire vive et le disque dur, pas des souvenirs identitaires utiles.
- [x] Probe `OVH migration Authelia Caddy Docker`: top-5 remonte un item parasite `codex-8192-live-1775296899` avant de vrais items OVH, signe de recall encore plat.
- [x] Probe `preferences utilisateur durables style reponse`: top-5 remonte surtout des requetes utilisateur generiques, pas une voie nette de preferences durables.
- [x] Probe `contexte circonstanciel recent ce soir fatigue`: top-5 remonte surtout des traces assistant circonstancielles ou de presse, sans voie contextuelle specialisee.
- [x] Pour tous les probes ci-dessus, l'enrichissement `parent_summary` est nul en pratique car `summaries=0`.

## Actifs deja presents a reutiliser

- [x] Tests existants pour `MEMORY_TOP_K` runtime et le retrieval de base: `app/tests/test_memory_store_phase4.py`.
- [x] Tests existants pour le contrat canonique `memory_retrieved` et la separation avec les champs arbitre: `app/tests/unit/chat/test_chat_memory_flow.py`.
- [x] Tests existants pour le cache d'enrichissement `parent_summary`: `app/tests/unit/memory/test_memory_store_blocks_phase8bis.py`.
- [x] Tests existants pour la persistence du modele effectif de l'arbitre malgre un changement runtime concurrent: `app/tests/test_memory_store_phase4.py`.
- [x] `/api/admin/hermeneutics/dashboard` existe deja et agrege des KPIs `memory_store`, des `runtime_metrics` process et des latences lues depuis les admin logs.
- [x] `/api/admin/hermeneutics/arbiter-decisions` existe deja comme lecture read-only des decisions arbitre persistees.
- [x] `observability.chat_log_events` existe deja comme persistence dediee des evenements tour par tour; snapshot lu pendant cet audit: `54646` events avec des stages incluant `embedding`, `prompt_prepared`, `context_build` et `branch_skipped`.
- [x] `admin_logs` constitue deja une deuxieme couche d'observation distincte, notamment pour le mode hermeneutique et certaines actions admin.
- [x] `/hermeneutic-admin` existe deja comme surface mixte de pilotage et d'inspection hermeneutique reemployant des APIs existantes; ce n'est pas encore une surface dediee memoire/RAG.
- [x] Une partie des `runtime_metrics` vient aujourd'hui du process en memoire; la future surface finale devra donc distinguer explicitement ce qui est persiste, ce qui est derive et ce qui est seulement process-local.
- [x] Le finding separe sur `record_arbiter_decisions()` reste hors scope de ce chantier et ne doit pas etre re-melange ici.

## Hypotheses de travail a tenir tant qu'aucune preuve contraire n'existe

- Le prochain gain principal de pertinence viendra d'abord de l'amont retrieval/panier, pas d'un durcissement supplementaire des seuils arbitre.
- Tant que `summaries=0` sur le runtime actif, la voie `summaries` est un chantier de design + preconditions, pas un levier live immediat.
- Tant que le panier pre-arbitre reste peu structure, l'arbitre compense partiellement mais ne peut pas reparer un recall mal calibre.
- Les doublons exacts et quasi-doublons doivent etre traites comme un sujet explicite de panier, pas comme un detail cosmetique.
- La decision `go / no-go` sur un reranker doit etre fondee sur les preuves deja accumulees, sans presumer un essai effectif si le dossier de necessite reste insuffisant.
- Le design final d'une surface d'observabilite memoire/RAG ne doit pas etre fige tant que le systeme de fond et la decision reranker ne sont pas stabilises.
- La future surface d'observabilite memoire/RAG devra etre pensee comme un systeme dedie distinct de l'admin general, meme si elle reemploie des briques communes.

## Hors scope explicite

- Aucun patch runtime ou code metier dans ce tour documentaire.
- Aucun changement de seuils `ARBITER_*` dans ce chantier documentaire.
- Aucun ajout immediat de reranker.
- Aucun changement de modele d'embedding sans baseline et preuves dediees.
- Aucun redesign complet de l'arbitre.
- Aucun couplage de ce sujet avec une architecture microservices.
- Aucun melange avec le fix separe de `record_arbiter_decisions()`.
- Aucun rebuild applicatif pour ce tour.

## Coherence avec `hermeneutical-add-todo.md`

- Cette roadmap traite la qualite des candidats memoire remis a l'arbitre.
- Elle ne reouvre pas silencieusement la doctrine `accept | defer | reject`, la politique identitaire ni le rollout hermeneutique deja cadres ailleurs.
- Si un futur lot touche la frontiere entre retrieval et contrat hermeneutique, il devra le documenter comme lot distinct et relier explicitement les deux roadmaps.

## Phase 0 - Baseline exploitable et corpus de probes

- [x] Figer un corpus de `5` a `10` requetes canoniques couvrant au minimum:
  - architecture / modules externes;
  - memoire / identite;
  - OVH / migration / exploitation;
  - preferences utilisateur durables;
  - contexte circonstanciel recent.
- [x] Pour chaque requete, ecrire:
  - la formulation exacte;
  - la raison du probe;
  - le type de souvenir attendu;
  - ce qui compterait comme faux positif typique.
- [x] Rejouer chaque probe avec le runtime actuel sans changer les settings.
- [x] Archiver pour chaque probe:
  - le `top_k` brut retourne;
  - les roles des items;
  - les scores de retrieval;
  - la presence ou absence de `summary_id`;
  - la presence ou absence de `parent_summary`;
  - un apercu texte des items.
- [x] Construire une taxonomy simple et stable des faux positifs observes:
  - assistant generique;
  - duplication exacte;
  - quasi-doublon;
  - item circonstanciel sans utilite;
  - item lexicalement voisin mais semantiquement plat;
  - item stale / procedural / hors axe.
- [x] Relever explicitement les probes ou le `top_k=5` actuel parait trop court.
  - Verdict Phase 0: aucun probe ne montre `top_k=5` comme probleme primaire; le probe identitaire de stress devra etre relu apres dedup.
- [x] Relever explicitement les probes ou le probleme principal n'est pas la taille du recall mais sa composition.
  - Verdict Phase 0: les `6` probes canoniques montrent un probleme de composition dominant.
- [x] Verifier si les exemples deja presents dans `arbiter_decisions` peuvent servir de baseline historique complementaire sans nouvelles ecritures.
  - Verdict Phase 0: oui comme source complementaire de faux positifs et de raisons arbitre, non comme substitut au corpus canonique.
- [x] Choisir l'emplacement de la preuve baseline future.
  - Emplacement retenu: `app/docs/states/baselines/memory-rag-relevance-baseline-2026-04-10.md`

### Gate 0

- [x] Le corpus de probes est fige.
- [x] La taxonomy de faux positifs est ecrite.
- [x] Un snapshot baseline exploitable existe pour chaque probe.
- [x] Aucun choix d'implementation n'a encore ete engage.

## Phase 1 - Cartographie exacte du pipeline courant

- [x] Documenter pas a pas la chaine actuelle:
  - query de retrieval;
  - retrieval brut;
  - enrichissement `parent_summary`;
  - panier vu par l'arbitre;
  - decisions arbitre;
  - injection finale dans le prompt.
  - Reference Phase 1: `app/docs/states/architecture/memory-rag-current-pipeline-cartography.md`
- [x] Distinguer explicitement quatre surfaces de donnees:
  - retrieval brut;
  - panier pre-arbitre;
  - sortie arbitre;
  - prompt final.
- [x] Lister pour chaque surface les champs disponibles et ceux absents.
- [x] Noter noir sur blanc que `parent_summary` enrichit aujourd'hui le prompt et `memory_retrieved`, mais pas le payload arbitre.
- [x] Noter noir sur blanc que `summaries` n'est pas une voie autonome live au `2026-04-10`.
- [x] Lister les observabilites deja presentes a reutiliser:
  - `memory_retrieved`;
  - `memory_arbitration`;
  - `arbiter_decisions`;
  - latences de stage.
- [x] Lister ce qui manque encore pour evaluer proprement la pertinence amont:
  - faux positifs par categorie;
  - provenance de lane;
  - duplication avant arbitre;
  - couverture traces vs summaries.

### Gate 1

- [x] La cartographie actuelle est stable et partagee.
- [x] Les frontieres retrieval / arbitre / prompt sont explicites.
- [x] Aucun lot suivant n'avance sans cette cartographie.

## Phase 2 - Design du candidate generation

- [x] Definir les lanes candidates a etudier avant toute implementation:
  - lane `traces` globale actuelle;
  - lane `user` dediee;
  - lane `assistant` dediee;
  - lane recence / diversite conversationnelle;
  - lane `summaries` future.
  - Reference Phase 2: `app/docs/states/architecture/memory-rag-candidate-generation-design.md`
- [x] Pour chaque lane, decrire:
  - objectif;
  - type de souvenirs vises;
  - risque principal de faux positifs;
  - signal attendu pour dire qu'elle aide vraiment.
- [x] Definir si l'amelioration vise plutot:
  - un `top_k` brut plus large;
  - une union multi-lanes;
  - une diversification par conversation;
  - un cap par role;
  - ou une combinaison borne.
- [x] Definir les cas ou les traces assistant doivent etre:
  - plafonnees;
  - penalisees;
  - ou gardees a parite avec les traces user.
- [x] Definir les cas ou la recence doit aider sans ecraser la pertinence durable.
- [x] Definir si une reformulation de query doit rester hors scope d'un premier lot.
- [x] Definir les dependances minimales pour tester un recall plus large sans toucher encore au reranker.
- [x] Rediger un choix recommande et au moins une alternative rejetee avec raison explicite.

### Gate 2

- [x] Une strategie de candidate generation est choisie.
- [x] Les alternatives rejetees sont notees.
- [x] Le lot suivant ne touche pas encore a l'arbitre ni aux seuils.

## Phase 3 - Contrat cible du panier pre-arbitre

- [x] Definir un schema candidat cible plus riche que le panier actuel.
- [x] Trancher quels champs doivent exister avant arbitre:
  - `source_kind`;
  - `source_lane`;
  - `conversation_id`;
  - `role`;
  - `timestamp`;
  - `retrieval_score`;
  - `summary_id`;
  - `parent_summary_present`;
  - cle de deduplication;
  - eventuels marqueurs de recence / diversite.
  - Reference Phase 3: `app/docs/states/specs/memory-rag-pre-arbiter-basket-contract.md`
- [x] Definir quels champs l'arbitre doit effectivement voir dans un premier lot V2.
- [x] Definir quels champs restent diagnostic-only ou prompt-only.
- [x] Definir la regle de dedup:
  - doublon exact;
  - quasi-doublon lexical;
  - collision meme conversation / meme idee;
  - collision trace / summary.
- [x] Definir la taille cible maximale du panier remis a l'arbitre.
- [x] Definir comment relier de facon stable:
  - l'item retrieve;
  - la decision arbitre;
  - l'item injecte.
- [x] Definir la place exacte de `parent_summary`:
  - absent du panier arbitre;
  - present comme hint arbitre;
  - ou present seulement en aval.
- [x] Definir comment éviter l'injection double d'une meme information quand trace et summary coexistent.

### Gate 3

- [x] Le schema cible du panier est fige.
- [x] La strategie de dedup est ecrite.
- [x] La place de `parent_summary` est tranchee explicitement.

## Phase 4 - Voie `summaries` comme chantier distinct

- [x] Verifier pourquoi le runtime actif a `summaries=0`:
  - absence de generation;
  - absence de trafic assez long;
  - autre cause a documenter si necessaire.
- [x] Decider si la preparation de cette voie doit commencer par:
  - fixtures de tests;
  - replay hors live;
  - ou attente de donnees live.
- [x] Definir le schema minimal d'un candidat `summary`.
- [x] Definir le mode de retrieval `summary` a comparer a la lane `traces`.
- [x] Definir la politique de fusion `traces + summaries`.
- [x] Definir la politique d'antidoublon entre une trace et son resume parent.
- [x] Definir comment mesurer qu'une lane `summaries` apporte un gain reel et pas seulement du texte plus long.
- [x] Definir les preuves minimales requises avant toute implementation de cette lane.
  - Reference Phase 4: `app/docs/states/specs/memory-rag-summaries-lane-contract.md`

### Gate 4

- [x] La voie `summaries` est soit prete a etre implementee, soit explicitement marquee comme bloquee par manque de donnees live.
- [x] La politique de fusion et d'antidoublon est ecrite.

## Phase 5 - Mesures de succes et feuille d'evaluation

- [x] Figer une grille de lecture manuelle des probes:
  - souvenir utile;
  - souvenir tolerable mais faible;
  - faux positif;
  - doublon;
  - item a garder pour contexte recent plutot que memoire durable.
- [x] Definir une mesure simple de couverture utile par probe.
- [x] Definir une mesure simple de bruit par probe.
- [x] Definir une mesure simple de duplication par probe.
- [x] Definir une mesure simple de diversite de conversations dans le panier.
- [x] Definir comment lire la contribution reelle de l'arbitre:
  - recall deja bon mais tri utile;
  - recall mauvais que l'arbitre ne peut pas sauver;
  - rejets surtout de nettoyage.
- [x] Definir le budget de latence acceptable par etape future.
- [x] Definir ce qui constituera une regression bloquante.
- [x] Definir le format de comparaison avant/apres a archiver.
  - Reference Phase 5: `app/docs/states/specs/memory-rag-evaluation-sheet.md`

### Gate 5

- [x] La feuille d'evaluation existe avant le premier patch d'implementation.
- [x] Les criteres de succes et d'echec sont explicites.

## Phase 6 - Lot d'implementation A: candidate generation

- [x] Une premiere tentative purement multi-lanes dense a ete ajournee; le lot retenu remplace cette variante par un recall reellement hybride.
- [x] Le lot 6A introduit un vrai nouveau signal de rappel:
  - lane dense vectorielle;
  - lane lexicale built-in PostgreSQL (`to_tsvector('simple', ...)`);
  - voie exacte pour codes, IDs, acronymes et URL.
- [x] Le lot 6A reste borne au candidate generation:
  - aucun changement des seuils arbitre;
  - aucun reranker;
  - aucune voie `summaries` live;
  - aucun redesign Phase `7B`.
- [x] `top_k` garde son sens de cap final de `memory_store.retrieve(...)`, malgre un recall interne elargi.
- [x] La shape retournee reste stable et compatible avec l'aval:
  - `conversation_id`;
  - `role`;
  - `content`;
  - `timestamp`;
  - `summary_id`;
  - `score`.
- [x] Les timestamps, `summary_id` et la compatibilite `parent_summary` sont preserves.
- [x] Mini-correctif immediat post-6A ferme:
  - voie exacte adossee a `traces_content_exact_trgm_gist_idx` et triee `<->` au lieu d'un scan lineaire;
  - contrat retrieval -> arbitre clarifie via `retrieval_score` / `semantic_score`;
  - fallback et payload arbitre ne lisent plus un `score` hybride ambigu.
- [x] Le lot 6A rejoue le corpus canonique avant/apres et ajoute des probes lexicales de stress pour prouver le nouveau signal.
- [x] Le lot 6A ajoute des tests structurels et des tests de valeur recall sur fixtures locales.
- [x] Une baseline d'evaluation datee archive le verdict et les limites du lot.
  - Reference Phase 6A: `app/docs/states/baselines/memory-rag-6A-evaluation-2026-04-10.md`
- [x] Les gains restent concentres sur certains cas exact-term / nom propre / URL, tandis que le bruit assistant residuel, la duplication identitaire et la platitude du panier restent a traiter en `7B`.

### Gate 6A

- [x] Gate franchie: un recall hybride defendable est implemente et garde.
- [x] Gate franchie: `top_k`, le contrat de shape et la compatibilite aval sont preserves.
- [x] Gate franchie: la dette exacte de scalabilite et l'ambiguite de score pre-arbitre sont fermees sans ouvrir `7B`.
- [x] Gate franchie: aucun blocker Phase 5 n'est observe sur la latence `retrieve` ni sur le chainage runtime.

## Phase 7 - Lot d'implementation B: structuration du panier et dedup

Statut de pilotage:
- phase fermee au `2026-04-10`;
- baseline de cloture: `app/docs/states/baselines/memory-rag-7B-evaluation-2026-04-10.md`

- [x] Le lot B ne change pas le candidate generation choisi en Phase 2 sauf necessite documentee.
- [x] Le lot B introduit le schema candidat cible retenu.
- [x] Le lot B traite explicitement doublons exacts et quasi-doublons.
- [x] Le lot B clarifie la place de `parent_summary`.
- [x] Le lot B ajoute des tests sur:
  - stabilite des IDs candidats;
  - dedup avant arbitre;
  - liens entre `memory_retrieved` et `memory_arbitration`;
  - non-regression prompt injection.
- [x] Le lot B rejoue le corpus de probes et compare le panier pre-arbitre.

### Gate 7B

- [x] Le panier est plus structure et moins redondant.
- [x] Les champs du contrat cible sont stables.
- [x] Le lot suivant peut mesurer la voie `summaries` sans ambiguite de schema.

## Phase 8 - Futur lot d'implementation C: voie `summaries`

Statut de pilotage:
- phase fermee au `2026-04-10`;
- baseline de cloture: `app/docs/states/baselines/memory-rag-8C-evaluation-2026-04-10.md`

- [x] Le lot C n'ouvre que la voie `summaries`.
- [x] Le lot C n'introduit pas encore de reranker.
- [x] Le lot C prouve la fusion propre `traces + summaries`.
- [x] Le lot C prouve l'absence d'injection double.
- [x] Le lot C ajoute des tests avec fixtures ou donnees live selon la decision de la Phase 4.
- [x] Le lot C rejoue le corpus de probes et compare la couverture utile sur les cas ou des resumes existent.

### Gate 8C

- [x] La voie `summaries` apporte un gain mesurable sur fixtures/replay et reste explicitement neutre en live tant que `summaries=0`.
- [x] Les collisions trace / summary sont gerees proprement.

## Phase 9 - Futur lot d'evaluation D: reranker tardif et optionnel

Statut de pilotage:
- phase fermee au `2026-04-11`;
- decision retenue: `no-go reranker for now`;
- note de decision: `app/docs/states/project/memory-rag-reranker-decision-2026-04-11.md`

- [x] Confirmer que les Gates `0` a `8C` sont fermes avant d'ouvrir cette phase.
- [x] Fonder la decision `go / no-go` reranker sur les probes, tests et comparaisons avant/apres deja figes; ne pas presumer qu'un reranker sera retenu.
- [x] Confirmer par preuves que le recall de base et le panier ont deja ete assainis sans reranker.
- [x] Conclure qu'aucune comparaison de solutions reranker ne doit etre ouverte tant que le dossier de necessite reste trop faible pour justifier cout, latence et complexite supplementaires.
- [x] Rappeler qu'un reranker, s'il etait reouvert plus tard, resterait un second passage sur un panier deja meilleur.
- [x] Conclure qu'aucun budget de latence, plan de rollback, choix de modele ou choix de provider ne doit etre engage tant que le dossier de necessite reste insuffisant.
- [x] Rejeter explicitement toute proposition de reranker servant seulement a masquer un retrieval encore plat.

### Gate 9D

- [x] Le reranker reste une option tardive, non un pretexte pour sauter les phases amont.
- [x] Une decision explicite `go / no-go` est prise et documentee.
- [x] Aucun lot final de surface d'observabilite memoire/RAG ne demarre avant cette decision explicite.

## Phase 10 - Lot final E: surface d'observabilite memoire/RAG dediee

Statut de pilotage:
- phase fermee au `2026-04-12`;
- contrat de surface: `app/docs/states/specs/memory-admin-surface-contract.md`
- validation de cloture: `app/docs/todo-done/validations/memory-admin-phase10e-validation-2026-04-12.md`

- [x] Confirmer que les Gates `0` a `9D` sont fermees avant d'ouvrir ce lot.
- [x] Confirmer que le systeme de fond est assez stabilise pour eviter de designer une surface finale sur des objets encore mouvants.
- [x] Ouvrir ce lot seulement apres la decision documentaire explicite `go / no-go` sur le reranker, qu'un reranker soit retenu ou non.
- [x] Definir la surface comme un systeme separe de l'administration generale, dedie a l'observabilite memoire / RAG dans FridaDev.
- [x] Definir le role fonctionnel de cette surface:
  - rendre lisible ce qui se passe dans le domaine memoire/RAG;
  - rendre les objets et etapes comprehensibles pour un operateur;
  - fournir des intitules lisibles et une legende de provenance;
  - permettre l'inspection sans obliger a croiser durablement plusieurs surfaces confuses.
- [x] Rendre lisibles dans la surface les familles suivantes:
  - etat memoire (`traces`, `summaries`, duplications notables);
  - retrieval / RAG;
  - embeddings;
  - panier pre-arbitre;
  - arbitre;
  - injection memoire;
  - tours recents et decisions arbitre persistees.
- [x] Distinguer explicitement ce qui vient:
  - d'une persistence durable;
  - d'une agregation calculee;
  - d'un etat process runtime;
  - ou d'une lecture historique de logs.
- [x] Faire l'inventaire explicite des informations du domaine aujourd hui dispersees entre:
  - `/admin`;
  - `/hermeneutic-admin`;
  - `dashboard`;
  - `arbiter-decisions`;
  - logs chat / `observability.chat_log_events`;
  - admin logs.
- [x] Trancher explicitement pour chaque famille inventoriee:
  - migration dans `Memory Admin` pour la vue memoire / RAG agregee;
  - maintien sur `/log`, `/identity` ou `/hermeneutic-admin` quand le sujet sort du seul domaine memoire / RAG;
  - absence de duplication confuse durable.
- [x] Interdire une duplication confuse durable entre l'admin general et la surface dediee.
- [x] Verifier que la surface n'est pas decrite comme une simple extension floue de l'admin general ou de `/hermeneutic-admin`.
- [x] Figer les non-goals de ce lot:
  - aucun reranker;
  - aucun nouveau systeme CSS;
  - aucune refonte globale de `app/web/`;
  - aucun rangement des `admin_section_*`;
  - aucun redesign d Identity ou d Hermeneutic admin.
- [x] Produire un cadrage fonctionnel final disant ce que la surface doit permettre de comprendre et l architecture frontend retenue:
  - `app/web/memory-admin.html` a la racine;
  - logique JS dans `app/web/memory_admin/`;
  - reutilisation de `admin.css`;
  - ajout d'une entree `Memory Admin` dans la navigation admin pertinente.

### Gate 10E

- [x] La decision reranker documentaire explicite est documentee et close.
- [x] Le perimetre fonctionnel de la surface dediee est ecrit sans rouvrir les phases amont.
- [x] La liste des informations a migrer, conserver ailleurs ou laisser hors surface est explicite.
- [x] La contrainte anti-redondance avec l'admin general est documentee.
- [x] Le lot est ferme sans reouvrir les phases de fond du systeme.

## Definition of done globale

- [x] Le corpus canonique de probes est versionne et reutilisable.
- [x] Une baseline avant/apres existe pour chaque lot d'implementation retenu.
- [x] Le candidate generation est plus propre sur les probes canoniques.
- [x] Le panier pre-arbitre a un schema stable, borne et moins redondant.
- [x] La place de `parent_summary` est documentee et testee.
- [x] La voie `summaries` est soit implementee avec preuves, soit ajournee explicitement avec cause.
- [x] La decision `go / no-go` reranker est prise sur preuves et documentee.
- [x] Le reranker reste absent tant que ses prerequis ne sont pas demontres.
- [x] Une surface finale d'observabilite memoire/RAG est cadree puis livree comme systeme dedie distinct de l'admin general.
- [x] Les informations memoire/RAG aujourd'hui dispersees sont migrees, maintenues ailleurs ou laissees hors surface explicitement; aucune duplication confuse durable n'est laissee en place.
- [x] Aucun lot n'a melange ce chantier avec le finding separe `record_arbiter_decisions()`.
- [x] La validation finale est archivee dans `app/docs/todo-done/validations/`.

## Ordre reel de travail recommande

1. Baseline probes et taxonomy de faux positifs.
2. Cartographie precise du pipeline courant.
3. Design du candidate generation.
4. Design du schema panier + dedup.
5. Preconditions et design de la voie `summaries`.
6. Feuille d'evaluation avant tout patch runtime.
7. Lots d'implementation separes: generation, panier, summaries.
8. Decision reranker documentaire explicite, avec issue `go / no-go`.
9. Surface finale d'observabilite memoire/RAG dediee, distincte de l'admin general, seulement apres cette decision.
