# Memory RAG - feuille d'evaluation normative - 2026-04-10

Statut: reference normative active
Classement: `app/docs/states/specs/`
Portee: feuille d'evaluation commune aux futurs lots `6A`, `7B`, `8C` et `9D` du chantier `memory-rag-relevance`
Roadmap liee: `app/docs/todo-done/refactors/memory-rag-relevance-todo.md`
Baseline liee: `app/docs/states/baselines/memory-rag-relevance-baseline-2026-04-10.md`
Cartographie liee: `app/docs/states/architecture/memory-rag-current-pipeline-cartography.md`
Design lie: `app/docs/states/architecture/memory-rag-candidate-generation-design.md`
Specs liees:
- `app/docs/states/specs/memory-rag-pre-arbiter-basket-contract.md`
- `app/docs/states/specs/memory-rag-summaries-lane-contract.md`

## 1. Objet

Cette spec ferme la Phase 5 du chantier `memory-rag-relevance`.

Elle fixe, sans patch runtime:
- la grille manuelle de lecture des probes;
- les mesures simples a utiliser par probe;
- la lecture attendue de la contribution reelle de l'arbitre;
- le budget de latence acceptable pour les futures etapes memoire/RAG;
- la definition des regressions bloquantes;
- le format avant/apres a archiver;
- les preuves minimales avant de conclure qu'un lot est meilleur, utile ou a rejeter.

Elle ne fait pas:
- le design de la future surface finale d'observabilite;
- une nouvelle instrumentation runtime;
- un dashboard;
- une implementation candidate generation / panier / summaries / reranker.

## 2. Pourquoi une spec et non une simple note

La Phase 5 doit servir de reference commune a tous les lots suivants.

Il faut donc figer:
- une grille stable;
- des mesures simples et reutilisables;
- des budgets et des blockers;
- un format d'archivage commun;
- une doctrine explicite de lecture des gains.

Le bon emplacement est `states/specs/`.

## 3. Sources et preuves relues

Sources retenues:
- docs Phases `0` a `4`;
- code du depot;
- tests existants sur l'observabilite compacte et les snapshots canoniques;
- runtime OVH en lecture seule.

Preuves runtime relues pour cette phase:
- `arbiter_decisions`: `551` decisions, `32` gardees, `519` rejetees;
- top reasons lues en base: `missing_from_llm_output` (`27`), `Exact duplicate of the recent user message.` (`11`), puis plusieurs motifs `generic greeting`, `near-duplicate`, `same identity question repeated`, `déjà présent dans le contexte récent`;
- `observability.chat_log_events`: top stages incluant `prompt_prepared` (`2948`), `arbiter` (`2788`), `hermeneutic_node_insertion` (`1545`), `memory_retrieve` (`104`);
- latence `memory_retrieve` en base: `p50=148.5ms`, `p95=173.55ms`;
- latences historiques retenues via `admin*.log.jsonl`:
  - `retrieve`: `p50=167.832ms`, `p95=195.558ms`, `max=342.132ms`;
  - `arbiter`: `p50=1848.148ms`, `p95=2779.98ms`, `max=5714.496ms`;
  - `identity_extractor`: `p50=1049.938ms`, `p95=1925.069ms`, `max=3074.631ms`;
- le dashboard actuel retourne encore `latency_ms=0` pour `retrieve/arbiter/identity_extractor` quand le fichier courant `admin.log.jsonl` ne porte pas les historiques rotates;
- `prompt_prepared` persiste deja `memory_items_used`, `estimated_prompt_tokens` et `memory_prompt_injection`, mais pas les `candidate_id` injectes;
- `arbiter` persiste deja `raw_candidates`, `kept_candidates`, `rejected_candidates`, `decision_source`, `fallback_used`, `rejection_reason_counts`;
- `hermeneutic_node_insertion` persiste deja des resumes compacts `memory_retrieved.retrieved_count` et `memory_arbitration.{status,kept_count,rejected_count,decisions_count}`;
- `duration_ms` n'est actuellement persiste dans `chat_log_events` que pour `memory_retrieve`, pas pour `arbiter`, `prompt_prepared` ni `hermeneutic_node_insertion`.

## 4. Ce que l'on peut deja mesurer, et ce qui manque encore

## 4.1 Mesurable aujourd'hui, de facon exploitable

Mesurable et utile des maintenant:
- le corpus canonique de probes Phase 0;
- le recall brut observe par probe;
- les roles, scores et apercus des candidats;
- les counts `retrieved / kept / rejected`;
- les motifs de rejet arbitre agrégés;
- les counts d'injection memoire finale dans `prompt_prepared`;
- la latence `retrieve` en base;
- les latences historiques `retrieve / arbiter / identity_extractor` via admin logs retenus.

## 4.2 Mesurable aujourd'hui, mais avec angle mort

Mesurable avec prudence:
- `dashboard.latency_ms`
  - utile pour un coup d'oeil rapide;
  - insuffisant comme preuve de regression, car il depend du seul fichier courant;
- `runtime_metrics`
  - utiles pour comprendre le process courant;
  - non suffisants comme artefact historique;
- `prompt_prepared.memory_prompt_injection`
  - utile pour compter les blocs effectivement injectes;
  - ne permet pas encore de relier durablement l'injection aux `candidate_id`.

## 4.3 Non mesurable proprement aujourd'hui

Pas mesurable proprement sans archivage documentaire additionnel:
- le snapshot durable complet de `memory_retrieved` par tour;
- le lien durable `candidate_id -> decision arbitre -> item injecte`;
- la latence `arbiter`, `prompt_prepared` et `hermeneutic_node_insertion` dans `chat_log_events`;
- la provenance de lane (`source_lane`) tant que le lot A ne l'introduit pas.

Conclusion normative:
- la feuille d'evaluation DOIT s'appuyer d'abord sur les docs/baselines de lot et les artefacts persistes existants;
- elle ne DOIT PAS pretendre que la future surface finale d'observabilite existe deja.

## 5. Grille manuelle de lecture des probes

Chaque item observe dans un lot futur DOIT recevoir un label principal unique parmi les cinq suivants.

### 5.1 `souvenir utile`

Definition:
- item directement utile pour repondre au probe vise;
- porte un fait, une preference, une identite, une contrainte ou un contexte repondant a l'intention du probe.

Effet sur les mesures:
- compte dans `couverture utile`.

### 5.2 `souvenir tolerable mais faible`

Definition:
- item sur l'axe general du probe;
- ni franchement utile, ni franchement nuisible;
- acceptable comme bruit residuel faible dans un panier borne.

Effet sur les mesures:
- ne compte ni dans `couverture utile` ni dans `bruit`;
- reste note dans les commentaires manuels.

### 5.3 `faux positif`

Definition:
- item hors axe;
- ou lexicalement voisin mais semantiquement plat;
- ou procedural/generique sans utilite pour le probe.

Effet sur les mesures:
- compte dans `bruit`.

### 5.4 `doublon`

Definition:
- item qui duplique un autre slot utile ou inutile deja present;
- exact ou quasi-doublon, selon le niveau de surface evalue.

Effet sur les mesures:
- compte dans `duplication`;
- ne compte pas automatiquement dans `bruit` pour eviter le double comptage.

### 5.5 `contexte recent plutot que memoire durable`

Definition:
- item qui aurait plutot vocation a vivre dans un bloc de contexte recent ou d'indices contextuels;
- pas dans la memoire durable principale.

Effet sur les mesures:
- sur un probe durable, compte dans `bruit`;
- sur un probe explicitement recent/circonstanciel, reste un label distinct acceptable si l'item aide reellement.

## 6. Mesures simples par probe

La feuille d'evaluation DOIT rester simple et lisible.

Les mesures normatives sont:
- `couverture_utile_count`
- `bruit_count`
- `duplication_count`
- `diversite_conversationnelle_count`

Les taux associes PEUVENT etre archives en complement:
- `couverture_utile_rate = couverture_utile_count / basket_size`
- `bruit_rate = bruit_count / basket_size`
- `duplication_rate = duplication_count / basket_size`
- `diversite_conversationnelle_rate = distinct_conversation_count / basket_size`

## 6.1 Couverture utile

Definition:
- nombre de slots etiquetes `souvenir utile`.

Lecture:
- mesure principale pour dire si un lot aide vraiment le recall ou la selection.

## 6.2 Bruit

Definition:
- nombre de slots etiquetes `faux positif`;
- plus les slots etiquetes `contexte recent plutot que memoire durable` quand le probe vise du durable.

Lecture:
- mesure principale du bruit semantique reel.

## 6.3 Duplication

Definition:
- nombre de slots etiquetes `doublon`.

Lecture:
- mesure dediee, separee du bruit;
- utile pour ne pas masquer un panier qui contient "de bonnes idees, mais plusieurs fois la meme".

## 6.4 Diversite conversationnelle

Definition:
- nombre de `conversation_id` distincts dans la surface evaluee.

Lecture:
- sert a detecter les floods mono-conversation;
- ne remplace pas la mesure de couverture utile.

Limite:
- cette mesure s'applique surtout au `retrieval brut` et au `panier pre-arbitre`;
- elle n'est pas exploitable au niveau du prompt final textuel seul.

## 7. Surfaces a archiver pour chaque lot futur

Pour chaque probe, la comparaison avant/apres DOIT distinguer les quatre surfaces suivantes:

1. `retrieval brut`
2. `panier pre-arbitre`
3. `verdict arbitre`
4. `injection finale`

Raison:
- un lot peut ameliorer une surface sans ameliorer les autres;
- sans cette separation, on ne sait plus si le gain vient du recall, du panier, du tri ou de l'injection.

## 8. Lecture normative de la contribution arbitre

La contribution de l'arbitre DOIT etre lue a partir de la comparaison `avant arbitre / apres arbitre`, pas seulement a partir des raisons SQL.

Trois lectures principales sont retenues.

### 8.1 `recall deja bon mais tri utile`

Conditions minimales:
- la surface pre-arbitre contient deja au moins un `souvenir utile`;
- l'apres-arbitre conserve cette couverture utile;
- `bruit` et/ou `duplication` diminuent.

Lecture:
- l'arbitre aide vraiment a nettoyer;
- le probleme principal n'est pas le recall.

### 8.2 `recall mauvais que l'arbitre ne peut pas sauver`

Conditions minimales:
- la surface pre-arbitre contient `0` ou presque `0` `souvenir utile`;
- l'apres-arbitre ne peut pas remonter de couverture utile inexistante.

Lecture:
- l'arbitre n'est pas la bonne cible du lot suivant;
- il faut revenir au recall ou au panier.

### 8.3 `rejets surtout de nettoyage`

Conditions minimales:
- la majorite des rejets correspondent a des `doublons`, `faux positifs`, items generiques ou contextuels non utiles;
- les kept ne degradent pas la couverture utile.

Lecture:
- l'arbitre nettoie un panier encore imparfait;
- la logique de rejet est cohérente meme si l'amont doit encore progresser.

### 8.4 `arbitre trop agressif` (lecture d'alerte)

Conditions minimales:
- la couverture utile baisse apres arbitrage;
- ou un item utile identitaire/preference durable disparait sans compensation.

Lecture:
- blocker potentiel;
- le lot ne doit pas etre declare meilleur.

## 9. Budget de latence retenu

Le budget doit rester compatible avec un systeme interactif.

Constats d'appui:
- `retrieve` observe p95 autour de `173.55ms` en base et `195.558ms` dans les logs historiques;
- `arbiter` observe p95 `2779.98ms` dans les logs historiques;
- les etapes `merge/dedup` et `prompt_prepared` ne disposent pas encore d'une latence durablement persistee par stage.

Decision normative:

- `retrieve`
  - budget cible `p95 <= 250ms`
  - regression bloquante `p95 > 300ms`
- `merge/dedup`
  - budget cible `p95 <= 50ms`
  - regression bloquante `p95 > 100ms`
  - statut: budget reserve, a verifier par preuve de lot car non persiste aujourd'hui
- `arbiter`
  - budget cible `p95 <= 3000ms`
  - regression bloquante `p95 > 3500ms`
- `prompt prep / injection memoire`
  - budget cible `p95 <= 150ms`
  - regression bloquante `p95 > 250ms`
  - statut: budget reserve, a verifier par preuve de lot car non persiste aujourd'hui
- `budget total memoire`
  - budget cible `p95 <= 3500ms`
  - regression bloquante `p95 > 4000ms`

Interpretation:
- les budgets `retrieve` et `arbiter` sont directement fondes sur l'existant;
- les budgets `merge/dedup` et `prompt prep` sont des envelopes normatives reservees, parce que ces etapes ne doivent pas devenir significatives face au coeur interactif actuel.

## 10. Regressions bloquantes

Un lot futur NE DOIT PAS etre declare meilleur si l'un des blockers suivants apparait.

### 10.1 Couverture utile en baisse

Blocker si:
- un probe canonique cible par le lot perd un `souvenir utile` cle;
- ou tombe a `0` `souvenir utile` alors qu'il en avait avant.

### 10.2 Bruit en hausse nette

Blocker si:
- `bruit_count` augmente de `+2` slots ou plus sur un probe;
- ou augmente de plus de `25%` sans justification explicite de meilleur recall.

### 10.3 Duplication en hausse nette

Blocker si:
- `duplication_count` augmente sur un probe deja connu pour etre sature;
- ou si le lot revendique justement une amelioration de composition/dedup.

### 10.4 Regression identitaire / preferences durables

Blocker si:
- les probes `memoire identite durable episodique utilisateur`;
- `preferences utilisateur durables style reponse`;
- ou `qui suis-je pour toi maintenant identite durable`
perdent de la couverture utile sans compensation claire.

### 10.5 Double injection

Blocker absolu si:
- une meme idee est injectee deux fois;
- ou si une collision `trace / summary` finit en double presence memoire autonome.

### 10.6 Latence hors budget

Blocker si:
- une etape mesuree depasse le budget bloquant de la section 9;
- ou si le total memoire depasse son budget bloquant.

### 10.7 Panier illisible ou chainage perdu

Blocker si:
- le panier pre-arbitre n'est plus lisible manuellement;
- les `candidate_id` / `source_candidate_ids` / liens arbitre deviennent non auditables;
- les artefacts de lot ne permettent plus de reconstruire la chaine `retrieval -> panier -> arbitre -> injection`.

### 10.8 Preuve documentaire manquante

Blocker si:
- le lot ne rejoue pas le corpus canonique;
- ou n'archive pas un avant/apres lisible selon le format retenu.

## 11. Format avant/apres archivable

Le format de reference retenu pour les futurs lots est:
- `app/docs/states/baselines/memory-rag-<lot>-evaluation-YYYY-MM-DD.md`

Exemples futurs:
- `memory-rag-6A-evaluation-2026-04-11.md`
- `memory-rag-7B-evaluation-2026-04-12.md`

La doc d'evaluation DOIT contenir au minimum:

### 11.1 En-tete

- lot evalue;
- date;
- commit;
- runtime/settings pertinents;
- surfaces et artefacts utilises;
- limites de mesure connues.

### 11.2 Tableau ou bloc par probe

Pour chaque probe:
- formulation exacte;
- intention du probe;
- surface `retrieval brut`;
- surface `panier pre-arbitre`;
- verdict arbitre;
- injection finale;
- notes manuelles de classification;
- `couverture_utile_count`;
- `bruit_count`;
- `duplication_count`;
- `diversite_conversationnelle_count`;
- latences pertinentes;
- verdict local du probe.

### 11.3 Resume global du lot

- synthese des gains et regressions;
- tableau court avant/apres par probe;
- blockers observes ou non;
- decision finale `meilleur / neutre / rejet / ajourne`.

## 12. Preuves minimales par futur lot

## 12.1 Avant de dire `lot A meilleur`

Il faut prouver:
- rejouer tout le corpus canonique;
- archiver le `retrieval brut` et le `panier pre-arbitre`;
- mesurer `couverture utile`, `bruit`, `duplication`, `diversite conversationnelle`;
- montrer qu'aucun probe cible n'a regression bloquante;
- rester dans le budget `retrieve` et le budget total memoire.

## 12.2 Avant de dire `lot B meilleur`

Il faut prouver:
- rejouer tout le corpus canonique;
- archiver le panier pre-arbitre cible;
- montrer la baisse de duplication et l'amelioration de lisibilite;
- montrer la stabilite des `candidate_id` et du chainage;
- montrer l'absence de regression de prompt injection.

## 12.3 Avant de dire `lot C utile`

Il faut prouver:
- replay ou fixtures selon la Phase 4;
- comparaison `traces seules` / `summaries seules` / `traces + summaries`;
- au moins un gain net de couverture utile ou de compaction utile;
- aucune double injection;
- aucune regression sur identite/preferences durables.

## 12.4 Avant de dire `reranker utile ou non`

Il faut prouver:
- phases `6A`, `7B` et `8C` fermees;
- meme corpus, meme format avant/apres;
- comparaison avant/apres reranker sur panier deja assaini;
- gain net sur la selection finale ou decision explicite `no-go`;
- respect du budget de latence arbitre + budget total memoire.

## 13. Regles d'usage de cette feuille

- cette feuille sert a evaluer les lots, pas a dessiner la future UI;
- elle privilegie des mesures simples et manuelles, pas un laboratoire de recherche;
- elle DOIT etre relue avec les docs Phases `0` a `4`;
- elle NE DOIT PAS etre contournee pour declarer un lot meilleur sur intuition.

## 14. Decision de cloture Phase 5

La Phase 5 est fermee car cette spec:
- fixe une grille manuelle simple et stable;
- fixe des mesures simples par probe;
- fixe une lecture explicite de la contribution arbitre;
- fixe un budget de latence defendable;
- fixe les regressions bloquantes;
- fixe un format avant/apres archivable;
- dit honnetement ce qui est deja mesurable et ce qui ne l'est pas encore.
