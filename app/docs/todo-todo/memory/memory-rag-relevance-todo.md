# Memory RAG Relevance - TODO implementation roadmap (v2)

Statut: actif
Classement: `app/docs/todo-todo/memory/`
Portee: roadmap de travail pour la pertinence du retrieval memoire/RAG en amont de l'arbitre
Derniere revue documentaire: `2026-04-10`
Origine: audit doc + code + runtime OVH du `2026-04-10`
Doc liee: `app/docs/todo-todo/memory/hermeneutical-add-todo.md`

## Intention

Transformer le TODO macro initial en plan de travail executable, borne, sequence et verifiable, sans lancer dans ce tour l'implementation de la V2 memoire/RAG.

La doctrine conservee est explicite:
- d'abord assainir le candidate generation;
- ensuite structurer le panier remis a l'arbitre;
- ensuite faire de `summaries` une vraie voie si elle devient disponible;
- et seulement ensuite evaluer un reranker de second rang.

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

## Baseline runtime factuelle au 2026-04-10

- [x] Runtime observe sur OVH: `HERMENEUTIC_MODE=enforced_all`, `MEMORY_TOP_K=5`, `ARBITER_MAX_KEPT_TRACES=3`, `ARBITER_MIN_SEMANTIC_RELEVANCE=0.62`, `ARBITER_MIN_CONTEXTUAL_GAIN=0.55`.
- [x] Snapshot base observe: `traces=224`, `summaries=0`, `embedded_traces=224`, `embedded_summaries=0`, `traces_with_summary_id=0`.
- [x] Repartition live des traces: `assistant=112`, `user=112`.
- [x] `memory_traces_summaries.retrieve()` interroge aujourd'hui `traces` seulement, sur un top-k vectoriel plat, avec le seul `user_msg` comme query.
- [x] `summaries` est persiste en theorie mais n'est pas une voie de retrieval live; sur OVH au `2026-04-10`, la table est vide.
- [x] `chat_memory_flow.prepare_memory_context()` enrichit les traces avec `parent_summary` apres le retrieval, puis construit `memory_retrieved`.
- [x] `arbiter.filter_traces_with_diagnostics()` voit un payload plat compose de `id`, `role`, `content`, `ts`, `score`, plus le contexte recent; il ne voit pas `parent_summary`.
- [x] Les decisions arbitre sont deja observables en base via `arbiter_decisions`; snapshot lu: `551` decisions, toutes `decision_source=llm`, avec `32` gardees et `519` rejetees.
- [x] Des doublons exacts existent deja dans `traces`; exemples lus: `Je suis Christophe Muck` (`6` occurrences), `Qui suis-je ?` (`5`), `Bonsoir Frida` (`5`), `Explique simplement la difference entre la memoire vive et le disque dur.` (`3`).

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
- [x] Le finding separe sur `record_arbiter_decisions()` reste hors scope de ce chantier et ne doit pas etre re-melange ici.

## Hypotheses de travail a tenir tant qu'aucune preuve contraire n'existe

- Le prochain gain principal de pertinence viendra d'abord de l'amont retrieval/panier, pas d'un durcissement supplementaire des seuils arbitre.
- Tant que `summaries=0` sur le runtime actif, la voie `summaries` est un chantier de design + preconditions, pas un levier live immediat.
- Tant que le panier pre-arbitre reste peu structure, l'arbitre compense partiellement mais ne peut pas reparer un recall mal calibre.
- Les doublons exacts et quasi-doublons doivent etre traites comme un sujet explicite de panier, pas comme un detail cosmetique.

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

- [ ] Figer un corpus de `5` a `10` requetes canoniques couvrant au minimum:
  - architecture / modules externes;
  - memoire / identite;
  - OVH / migration / exploitation;
  - preferences utilisateur durables;
  - contexte circonstanciel recent.
- [ ] Pour chaque requete, ecrire:
  - la formulation exacte;
  - la raison du probe;
  - le type de souvenir attendu;
  - ce qui compterait comme faux positif typique.
- [ ] Rejouer chaque probe avec le runtime actuel sans changer les settings.
- [ ] Archiver pour chaque probe:
  - le `top_k` brut retourne;
  - les roles des items;
  - les scores de retrieval;
  - la presence ou absence de `summary_id`;
  - la presence ou absence de `parent_summary`;
  - un apercu texte des items.
- [ ] Construire une taxonomy simple et stable des faux positifs observes:
  - assistant generique;
  - duplication exacte;
  - quasi-doublon;
  - item circonstanciel sans utilite;
  - item lexicalement voisin mais semantiquement plat;
  - item stale / procedural / hors axe.
- [ ] Relever explicitement les probes ou le `top_k=5` actuel parait trop court.
- [ ] Relever explicitement les probes ou le probleme principal n'est pas la taille du recall mais sa composition.
- [ ] Verifier si les exemples deja presents dans `arbiter_decisions` peuvent servir de baseline historique complementaire sans nouvelles ecritures.
- [ ] Choisir l'emplacement de la preuve baseline future:
  - soit `app/docs/states/baselines/`;
  - soit `app/docs/todo-done/validations/`;
  - sans ouvrir une nouvelle doc tant que le besoin n'est pas net.

### Gate 0

- [ ] Le corpus de probes est fige.
- [ ] La taxonomy de faux positifs est ecrite.
- [ ] Un snapshot baseline exploitable existe pour chaque probe.
- [ ] Aucun choix d'implementation n'a encore ete engage.

## Phase 1 - Cartographie exacte du pipeline courant

- [ ] Documenter pas a pas la chaine actuelle:
  - query de retrieval;
  - retrieval brut;
  - enrichissement `parent_summary`;
  - panier vu par l'arbitre;
  - decisions arbitre;
  - injection finale dans le prompt.
- [ ] Distinguer explicitement quatre surfaces de donnees:
  - retrieval brut;
  - panier pre-arbitre;
  - sortie arbitre;
  - prompt final.
- [ ] Lister pour chaque surface les champs disponibles et ceux absents.
- [ ] Noter noir sur blanc que `parent_summary` enrichit aujourd'hui le prompt et `memory_retrieved`, mais pas le payload arbitre.
- [ ] Noter noir sur blanc que `summaries` n'est pas une voie autonome live au `2026-04-10`.
- [ ] Lister les observabilites deja presentes a reutiliser:
  - `memory_retrieved`;
  - `memory_arbitration`;
  - `arbiter_decisions`;
  - latences de stage.
- [ ] Lister ce qui manque encore pour evaluer proprement la pertinence amont:
  - faux positifs par categorie;
  - provenance de lane;
  - duplication avant arbitre;
  - couverture traces vs summaries.

### Gate 1

- [ ] La cartographie actuelle est stable et partagee.
- [ ] Les frontieres retrieval / arbitre / prompt sont explicites.
- [ ] Aucun lot suivant n'avance sans cette cartographie.

## Phase 2 - Design du candidate generation

- [ ] Definir les lanes candidates a etudier avant toute implementation:
  - lane `traces` globale actuelle;
  - lane `user` dediee;
  - lane `assistant` dediee;
  - lane recence / diversite conversationnelle;
  - lane `summaries` future.
- [ ] Pour chaque lane, decrire:
  - objectif;
  - type de souvenirs vises;
  - risque principal de faux positifs;
  - signal attendu pour dire qu'elle aide vraiment.
- [ ] Definir si l'amelioration vise plutot:
  - un `top_k` brut plus large;
  - une union multi-lanes;
  - une diversification par conversation;
  - un cap par role;
  - ou une combinaison borne.
- [ ] Definir les cas ou les traces assistant doivent etre:
  - plafonnees;
  - penalisees;
  - ou gardees a parite avec les traces user.
- [ ] Definir les cas ou la recence doit aider sans ecraser la pertinence durable.
- [ ] Definir si une reformulation de query doit rester hors scope d'un premier lot.
- [ ] Definir les dependances minimales pour tester un recall plus large sans toucher encore au reranker.
- [ ] Rediger un choix recommande et au moins une alternative rejetee avec raison explicite.

### Gate 2

- [ ] Une strategie de candidate generation est choisie.
- [ ] Les alternatives rejetees sont notees.
- [ ] Le lot suivant ne touche pas encore a l'arbitre ni aux seuils.

## Phase 3 - Contrat cible du panier pre-arbitre

- [ ] Definir un schema candidat cible plus riche que le panier actuel.
- [ ] Trancher quels champs doivent exister avant arbitre:
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
- [ ] Definir quels champs l'arbitre doit effectivement voir dans un premier lot V2.
- [ ] Definir quels champs restent diagnostic-only ou prompt-only.
- [ ] Definir la regle de dedup:
  - doublon exact;
  - quasi-doublon lexical;
  - collision meme conversation / meme idee;
  - collision trace / summary.
- [ ] Definir la taille cible maximale du panier remis a l'arbitre.
- [ ] Definir comment relier de facon stable:
  - l'item retrieve;
  - la decision arbitre;
  - l'item injecte.
- [ ] Definir la place exacte de `parent_summary`:
  - absent du panier arbitre;
  - present comme hint arbitre;
  - ou present seulement en aval.
- [ ] Definir comment éviter l'injection double d'une meme information quand trace et summary coexistent.

### Gate 3

- [ ] Le schema cible du panier est fige.
- [ ] La strategie de dedup est ecrite.
- [ ] La place de `parent_summary` est tranchee explicitement.

## Phase 4 - Voie `summaries` comme chantier distinct

- [ ] Verifier pourquoi le runtime actif a `summaries=0`:
  - absence de generation;
  - absence de trafic assez long;
  - autre cause a documenter si necessaire.
- [ ] Decider si la preparation de cette voie doit commencer par:
  - fixtures de tests;
  - replay hors live;
  - ou attente de donnees live.
- [ ] Definir le schema minimal d'un candidat `summary`.
- [ ] Definir le mode de retrieval `summary` a comparer a la lane `traces`.
- [ ] Definir la politique de fusion `traces + summaries`.
- [ ] Definir la politique d'antidoublon entre une trace et son resume parent.
- [ ] Definir comment mesurer qu'une lane `summaries` apporte un gain reel et pas seulement du texte plus long.
- [ ] Definir les preuves minimales requises avant toute implementation de cette lane.

### Gate 4

- [ ] La voie `summaries` est soit prete a etre implementee, soit explicitement marquee comme bloquee par manque de donnees live.
- [ ] La politique de fusion et d'antidoublon est ecrite.

## Phase 5 - Mesures de succes et feuille d'evaluation

- [ ] Figer une grille de lecture manuelle des probes:
  - souvenir utile;
  - souvenir tolerable mais faible;
  - faux positif;
  - doublon;
  - item a garder pour contexte recent plutot que memoire durable.
- [ ] Definir une mesure simple de couverture utile par probe.
- [ ] Definir une mesure simple de bruit par probe.
- [ ] Definir une mesure simple de duplication par probe.
- [ ] Definir une mesure simple de diversite de conversations dans le panier.
- [ ] Definir comment lire la contribution reelle de l'arbitre:
  - recall deja bon mais tri utile;
  - recall mauvais que l'arbitre ne peut pas sauver;
  - rejets surtout de nettoyage.
- [ ] Definir le budget de latence acceptable par etape future.
- [ ] Definir ce qui constituera une regression bloquante.
- [ ] Definir le format de comparaison avant/apres a archiver.

### Gate 5

- [ ] La feuille d'evaluation existe avant le premier patch d'implementation.
- [ ] Les criteres de succes et d'echec sont explicites.

## Phase 6 - Futur lot d'implementation A: candidate generation

- [ ] Le lot A ne touche qu'au candidate generation.
- [ ] Le lot A ne touche pas aux seuils arbitre.
- [ ] Le lot A ne touche pas encore au reranker.
- [ ] Le lot A ajoute des tests unitaires ou integration sur:
  - taille du recall;
  - composition par role;
  - composition par conversation;
  - absence de regression du contrat existant.
- [ ] Le lot A rejoue le corpus de probes et archive un avant/apres.

### Gate 6A

- [ ] Le recall est meilleur ou plus propre sur le corpus.
- [ ] Le panier brut reste borne et lisible.
- [ ] Les regressions sont nulles ou documentees.

## Phase 7 - Futur lot d'implementation B: structuration du panier et dedup

- [ ] Le lot B ne change pas le candidate generation choisi en Phase 2 sauf necessite documentee.
- [ ] Le lot B introduit le schema candidat cible retenu.
- [ ] Le lot B traite explicitement doublons exacts et quasi-doublons.
- [ ] Le lot B clarifie la place de `parent_summary`.
- [ ] Le lot B ajoute des tests sur:
  - stabilite des IDs candidats;
  - dedup avant arbitre;
  - liens entre `memory_retrieved` et `memory_arbitration`;
  - non-regression prompt injection.
- [ ] Le lot B rejoue le corpus de probes et compare le panier pre-arbitre.

### Gate 7B

- [ ] Le panier est plus structure et moins redondant.
- [ ] Les champs du contrat cible sont stables.
- [ ] Le lot suivant peut mesurer la voie `summaries` sans ambiguite de schema.

## Phase 8 - Futur lot d'implementation C: voie `summaries`

- [ ] Le lot C n'ouvre que la voie `summaries`.
- [ ] Le lot C n'introduit pas encore de reranker.
- [ ] Le lot C prouve la fusion propre `traces + summaries`.
- [ ] Le lot C prouve l'absence d'injection double.
- [ ] Le lot C ajoute des tests avec fixtures ou donnees live selon la decision de la Phase 4.
- [ ] Le lot C rejoue le corpus de probes et compare la couverture utile sur les cas ou des resumes existent.

### Gate 8C

- [ ] La voie `summaries` apporte un gain mesurable ou est explicitement ajournee avec raison.
- [ ] Les collisions trace / summary sont gerees proprement.

## Phase 9 - Futur lot d'evaluation D: reranker tardif et optionnel

- [ ] Confirmer que les Gates `0` a `8C` sont fermes avant d'ouvrir cette phase.
- [ ] Confirmer par preuves que le recall de base et le panier ont deja ete assainis sans reranker.
- [ ] Comparer au moins deux options de reranker:
  - local;
  - service API / conteneur;
  - ou abandon motive si aucune n'est proportionnee.
- [ ] Limiter le reranker a un second passage sur un panier deja meilleur.
- [ ] Definir un budget de latence et un plan de rollback.
- [ ] Rejeter explicitement toute proposition de reranker servant seulement a masquer un retrieval encore plat.

### Gate 9D

- [ ] Le reranker reste une option tardive, non un pretexte pour sauter les phases amont.
- [ ] Une decision explicite `go / no-go` est prise et documentee.

## Definition of done globale

- [ ] Le corpus canonique de probes est versionne et reutilisable.
- [ ] Une baseline avant/apres existe pour chaque lot d'implementation retenu.
- [ ] Le candidate generation est plus propre sur les probes canoniques.
- [ ] Le panier pre-arbitre a un schema stable, borne et moins redondant.
- [ ] La place de `parent_summary` est documentee et testee.
- [ ] La voie `summaries` est soit implementee avec preuves, soit ajournee explicitement avec cause.
- [ ] Le reranker reste absent tant que ses prerequis ne sont pas demontres.
- [ ] Aucun lot n'a melange ce chantier avec le finding separe `record_arbiter_decisions()`.
- [ ] La validation finale est archivee dans `app/docs/todo-done/validations/`.

## Ordre reel de travail recommande

1. Baseline probes et taxonomy de faux positifs.
2. Cartographie precise du pipeline courant.
3. Design du candidate generation.
4. Design du schema panier + dedup.
5. Preconditions et design de la voie `summaries`.
6. Feuille d'evaluation avant tout patch runtime.
7. Lots d'implementation separes: generation, panier, summaries.
8. Reranker seulement si les gains amont sont deja visibles.
