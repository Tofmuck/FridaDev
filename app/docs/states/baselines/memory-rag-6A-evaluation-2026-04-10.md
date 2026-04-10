# Memory/RAG 6A Evaluation - 2026-04-10

Statut: lot 6A retenu
Classement: `app/docs/states/baselines/`
Date: `2026-04-10`
Lot evalue: `Phase 6A - candidate generation`
Commit de depart: `4daf264a43f7db778e18939ba9c0b290e19ec56c`
Commit apres lot: commit de cloture qui ajoute cette baseline et ferme `6A`

## 1. Portee

Ce lot implemente un recall hybride borne:
- lane dense vectorielle existante;
- lane lexicale built-in PostgreSQL via `to_tsvector('simple', ...)`;
- voie exacte pour tokens saillants de type code, acronyme, ID ou URL;
- fusion explicite par merge hybride borne, sans changer l'arbitre, les seuils, `summaries` ni le reranker.

Invariants preserves:
- `top_k` garde son sens de cap final;
- shape retournee preservee: `conversation_id`, `role`, `content`, `timestamp`, `summary_id`, `score`;
- timestamps et `summary_id` preservés;
- compatibilite `enrich_traces_with_summaries()` et `memory_retrieved` preservee.

## 2. Runtime et artefacts utilises

- Runtime observe: `MEMORY_TOP_K=5`, `summaries=0`, `traces=224`.
- Recall interne du lot 6A: `internal_limit = max(top_k * 3, 12)` donc `15` avec `top_k=5`.
- Index ajoute et verifie live: `traces_content_fts_simple_idx`.
- Extensions live: `pgcrypto`, `plpgsql`, `vector`.
- Artefacts utilises pour l'evaluation:
  - replay dense-only read-only inline pour le `before`;
  - `memory_store.retrieve()` pour le `after`;
  - `memory_store.enrich_traces_with_summaries()` pour verifier la compatibilite aval;
  - `memory_retrieved_input.build_memory_retrieved_input()` pour verifier le contrat canonique;
  - tests unitaire/ciblés dans le conteneur app.

## 3. Limites de mesure

- Le lot 6A ne touche qu'au candidate generation; le panier pre-arbitre reste donc identique au `retrieval brut` au runtime courant.
- L'arbitre n'a pas ete rejoue live probe par probe pour eviter des appels LLM et des ecritures inutiles.
- L'injection finale n'a pas ete rejouee end-to-end probe par probe; la preuve aval est contractuelle:
  - shape retrieval preservee;
  - `memory_retrieved` toujours construit correctement;
  - `parent_summary` reste enrichissable, mais nul live car `summaries=0`.
- Le corpus live OVH reste petit; les probes lexicales de stress servent donc aussi de preuve structurelle du nouveau signal.

## 4. Verifications structurelles

- Tests passes dans le conteneur:
  - `tests.test_memory_store_phase4`
  - `tests.unit.chat.test_chat_memory_flow`
  - `tests.unit.memory.test_memory_candidate_generation_phase6a`
- Resultat: `37 tests`, `OK`.
- Verification live:
  - `platform-fridadev` healthy apres rebuild;
  - `curl https://fridadev.frida-system.fr/admin` -> `302` Authelia attendu.
- Contrat aval confirme sur probe `Christophe Muck`:
  - retrieval keys: `content`, `conversation_id`, `role`, `score`, `summary_id`, `timestamp`;
  - `memory_retrieved.traces[*]`: `candidate_id`, `content`, `conversation_id`, `parent_summary`, `retrieval_score`, `role`, `summary_id`, `timestamp_iso`.

## 5. Resume latence

- Corpus canonique:
  - `before_avg_ms = 57.82`
  - `after_avg_ms = 58.15`
  - `delta_avg_ms = +0.32`
  - `after_max_ms = 74.74`
- Probes lexicales de stress:
  - `before_avg_ms = 48.14`
  - `after_avg_ms = 78.01`
  - `delta_avg_ms = +29.87`
  - `after_max_ms = 95.91`

Lecture:
- le surcout du nouveau signal reste borne;
- il reste sous le budget `retrieve` Phase 5;
- le cout apparait surtout quand la lane lexicale s'active reellement.

## 6. Grille de lecture appliquee

Grille manuelle Phase 5:
- souvenir utile;
- souvenir tolerable mais faible;
- faux positif;
- doublon;
- contexte recent plutot que memoire durable.

Mesures retenues par probe:
- `couverture_utile_count`;
- `bruit_count`;
- `duplication_count`;
- `diversite_conversationnelle_count`.

## 7. Corpus canonique avant/apres

### 7.1 `architecture modules externes arbiter STT TTS`

- Intention: retrouver des souvenirs techniques/systeme.
- Retrieval brut:
  - before: `assistant=5`, `diversite=4`, top dense quasi identique.
  - after: `assistant=5`, `diversite=4`, pas de delta utile.
- Panier pre-arbitre: identique au retrieval brut dans ce lot.
- Verdict arbitre: non rejoue live; aucun signal amont nouveau visible sur ce probe.
- Injection finale: non rejouee live; compatibilite contractuelle preservee.
- Notes manuelles:
  - le probe reste domine par de l'assistant generique;
  - le nouveau signal lexical n'aide pas ici, ce qui est coherent avec l'absence de termes exacts distinctifs en base.
- Mesures:
  - before: `couverture_utile_count=1`, `bruit_count=4`, `duplication_count=0`, `diversite_conversationnelle_count=4`
  - after: `couverture_utile_count=1`, `bruit_count=4`, `duplication_count=0`, `diversite_conversationnelle_count=4`
- Latence: `77.06ms -> 83.56ms`
- Verdict local: `neutre`

### 7.2 `memoire identite durable episodique utilisateur`

- Intention: retrouver des souvenirs identitaires durables.
- Retrieval brut:
  - before: `user=4`, `assistant=1`, domine par `mémoire vive / disque dur`.
  - after: identique sur le fond.
- Panier pre-arbitre: identique au retrieval brut.
- Verdict arbitre: non rejoue live; recall amont reste insuffisant pour l'identite durable.
- Injection finale: non rejouee live; pas de regression de contrat.
- Notes manuelles:
  - le probe reste un contre-exemple utile;
  - le lot 6A n'aggrave pas le cas, mais ne le corrige pas.
- Mesures:
  - before: `couverture_utile_count=0`, `bruit_count=5`, `duplication_count=3`, `diversite_conversationnelle_count=5`
  - after: `couverture_utile_count=0`, `bruit_count=5`, `duplication_count=3`, `diversite_conversationnelle_count=5`
- Latence: `59.69ms -> 64.99ms`
- Verdict local: `neutre`

### 7.3 `OVH migration Authelia Caddy Docker`

- Intention: retrouver le souvenir technique OVH le plus proche, sans parasite hors axe.
- Retrieval brut:
  - before: `user=1`, `assistant=4`, `diversite=5`, avec parasite `codex-8192-live-1775296899` en tete.
  - after: `user=3`, `assistant=2`, `diversite=3`, parasite `codex` supprime.
- Panier pre-arbitre: identique au retrieval brut.
- Verdict arbitre: non rejoue live; l'amont est plus exact lexicalement, mais reste encore plat et partiellement redondant.
- Injection finale: non rejouee live; compatibilite contractuelle preservee.
- Notes manuelles:
  - gain net de recall exact sur `OVH`;
  - perte partielle de diversite conversationnelle;
  - un item assistant encore trop generique reste visible.
- Mesures:
  - before: `couverture_utile_count=2`, `bruit_count=3`, `duplication_count=1`, `diversite_conversationnelle_count=5`
  - after: `couverture_utile_count=4`, `bruit_count=1`, `duplication_count=2`, `diversite_conversationnelle_count=3`
- Latence: `64.80ms -> 86.14ms`
- Verdict local: `meilleur`

### 7.4 `preferences utilisateur durables style reponse`

- Intention: retrouver des preferences durables, pas des requetes generiques.
- Retrieval brut:
  - before: `user=5`, `diversite=5`.
  - after: top quasi identique.
- Panier pre-arbitre: identique au retrieval brut.
- Verdict arbitre: non rejoue live; l'arbitre recevrait le meme type de panier qu'avant.
- Injection finale: non rejouee live; pas de regression de contrat.
- Notes manuelles:
  - probe encore mal servi par le corpus live;
  - le nouveau signal lexical n'ajoute pas de faux positif supplementaire.
- Mesures:
  - before: `couverture_utile_count=0`, `bruit_count=5`, `duplication_count=0`, `diversite_conversationnelle_count=5`
  - after: `couverture_utile_count=0`, `bruit_count=5`, `duplication_count=0`, `diversite_conversationnelle_count=5`
- Latence: `62.42ms -> 69.62ms`
- Verdict local: `neutre`

### 7.5 `contexte circonstanciel recent ce soir fatigue`

- Intention: verifier qu'un probe circonstanciel recent n'est pas degrade.
- Retrieval brut:
  - before: `assistant=4`, `user=1`, `diversite=2`.
  - after: identique sur le fond.
- Panier pre-arbitre: identique au retrieval brut.
- Verdict arbitre: non rejoue live; cas recent inchange.
- Injection finale: non rejouee live; pas de regression de contrat.
- Notes manuelles:
  - pas de gain;
  - pas de degradation bloquante non plus.
- Mesures:
  - before: `couverture_utile_count=2`, `bruit_count=3`, `duplication_count=0`, `diversite_conversationnelle_count=2`
  - after: `couverture_utile_count=2`, `bruit_count=3`, `duplication_count=0`, `diversite_conversationnelle_count=2`
- Latence: `48.27ms -> 63.82ms`
- Verdict local: `neutre`

### 7.6 `qui suis-je pour toi maintenant identite durable`

- Intention: stresser le cas identitaire avec forte duplication.
- Retrieval brut:
  - before: `user=4`, `assistant=1`, `diversite=4`.
  - after: meme profil.
- Panier pre-arbitre: identique au retrieval brut.
- Verdict arbitre: non rejoue live; le lot 6A ne regle pas encore les doublons identitaires.
- Injection finale: non rejouee live; pas de regression de contrat.
- Notes manuelles:
  - rappel identitaire exact conserve;
  - duplication toujours dominante;
  - c'est bien le sujet de la Phase `7B`, pas une regression 6A.
- Mesures:
  - before: `couverture_utile_count=2`, `bruit_count=0`, `duplication_count=3`, `diversite_conversationnelle_count=4`
  - after: `couverture_utile_count=2`, `bruit_count=0`, `duplication_count=3`, `diversite_conversationnelle_count=4`
- Latence: `67.28ms -> 72.34ms`
- Verdict local: `neutre`

## 8. Probes lexicales de stress

### 8.1 `OVH`

- Resultat: signal lexical actif mais prudent.
- Before/after:
  - `assistant=2`, `user=3` avant comme apres;
  - ordre des items ajuste autour des occurrences `OVH`, sans regression bloquante.
- Lecture: `neutre positif`

### 8.2 `codex-8192-live-1775296899`

- Resultat: le code exact reste premier apres patch.
- Before/after:
  - `user=1`, `assistant=4` avant comme apres;
  - score exact renforce pour l'item code pur;
  - pas de perte de timestamp ni de `summary_id`.
- Lecture: `gain structurel exact-term`, meme si le top visible reste proche.

### 8.3 `Christophe Muck`

- Resultat: le rappel ne sature plus seulement en `Je suis Christophe Muck`.
- Before/after:
  - before: `user=5` quasi redondants;
  - after: `user=2`, `assistant=3`, avec items assistant identitaires pertinents.
- Lecture:
  - meilleur rappel d'items lexicalement lies au nom propre;
  - duplication brute reduite;
  - compensation utile par des reformulations assistant encore absentes du dense-only.
- Verdict: `meilleur`

### 8.4 `Qui suis-je pour toi maintenant ?`

- Resultat: pas de faux boost lexical parasite.
- Before/after:
  - `user=5` avant comme apres;
  - la lane lexicale n'hijacke pas une requete semantique sans terme saillant.
- Verdict: `garde-fou valide`

### 8.5 URL Mediapart exacte

- Probe: `Tu peux le trouver et le lire là : https://blogs.mediapart.fr/...`
- Resultat:
  - before: `user=5` exacts;
  - after: `user=5` exacts aussi.
- Lecture:
  - la voie exacte URL fonctionne et protege un cas que la version intermediaire avait degrade;
  - latence `64.24ms -> 114.44ms`, encore sous budget `retrieve`.
- Verdict: `meilleur structurel`

## 9. Contribution arbitre et lecture aval

- L'arbitre n'a pas ete rejoue live probe par probe.
- Lecture retenue pour ce lot:
  - quand le retrieval reste inchange, l'arbitre n'a pas de raison d'etre meilleur;
  - quand le retrieval devient plus exact lexicalement, l'arbitre recevra un panier plus propre sur certains cas techniques;
  - les doublons identitaires et le panier encore plat ne sont pas resolus ici et restent des limites aval connues.
- Conclusion aval honnete:
  - aucun gain arbitre revendique sans preuve directe;
  - aucune regression contractuelle visible non plus.

## 10. Gains, regressions, blockers

### Gains retenus

- vrai nouveau signal de rappel introduit;
- rappel exact-term / code / URL robuste;
- probe `OVH migration ...` nettoye du parasite `codex-8192-live-1775296899`;
- probe `Christophe Muck` moins sature de doublons user exacts;
- `top_k`, timestamps, `summary_id` et compatibilite `parent_summary` preserves.

### Regressions observees

- surcout de latence modere quand la lane lexicale s'active;
- gains canoniques concentres sur peu de probes;
- diversite conversationnelle en baisse sur `OVH migration ...`.

### Blockers

- Aucun blocker Phase 5 constate:
  - pas de depassement budget `retrieve`;
  - pas de regression de contrat;
  - pas de regression visible sur `memory_retrieved`;
  - pas de double injection introduite par ce lot.

## 11. Verdict final

Decision finale: `meilleur`

Pourquoi le lot est garde:
- il introduit un signal vraiment nouveau et non cosmetique;
- il reste borne au recall/candidate generation;
- il garde les invariants runtime;
- il apporte des gains defensables sur les cas exact-term / nom propre / URL;
- il ne cree pas de regression bloquante sur le corpus canonique.

Ce que le lot ne pretend pas resoudre:
- le bruit assistant residuel;
- la duplication identitaire;
- la structuration fine du panier pre-arbitre;
- la voie `summaries`;
- le reranker.

Prochaine phase active recommandee: `7B - structuration du panier et dedup`.
