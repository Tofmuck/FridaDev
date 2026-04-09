# Memory RAG Relevance - TODO

Statut: actif
Classement: `app/docs/todo-todo/memory/`
Origine: audit SSH OVH du `2026-04-09` sur la memoire persistee en base (`traces`, `summaries`) et sur la pertinence du panier remis a l'arbitre.

## Objectif

Ameliorer la pertinence du systeme de memoire/RAG qui alimente l'arbitre, sans changer la logique metier de haut niveau:
- mieux produire les candidats,
- mieux structurer ce qui est remis a l'arbitre,
- faire des resumes une vraie voie de memoire quand ils existeront,
- evaluer un reranker seulement quand le recall de base sera deja assaini,
- gagner en pertinence avant de durcir davantage les seuils d'arbitrage.

## Constat runtime retenu au 2026-04-09

Snapshot OVH observe:
- `traces`: `224`
- `summaries`: `0`
- `embedded_traces`: `224`
- `embedded_summaries`: `0`
- `MEMORY_TOP_K`: `5` par defaut
- `ARBITER_MAX_KEPT_TRACES`: `3`

Constats code/runtime retenus:
- le retrieval travaille aujourd'hui sur `traces` seulement;
- `summaries` est persiste et enrichit ensuite les traces, mais n'est pas encore une voie de retrieval autonome;
- la requete de retrieval part du seul `user_msg` brut;
- l'arbitre voit un panier de candidats encore peu structure (role, contenu, score, timestamp) et peut difficilement rattraper un mauvais recall;
- une probe reelle sur une requete `architecture/modules externes/arbiter/STT/TTS` remonte surtout des traces assistant generiques, ce qui indique un recall encore trop plat avant arbitrage.

## Hypothese de travail

Le prochain gain de pertinence ne viendra pas d'abord d'un arbitre plus severe, mais de quatre ameliorations amont:
- meilleur candidate generation;
- meilleure structuration des candidats;
- vraie integration des resumes dans la memoire de retrieval;
- et, seulement ensuite si le panier est deja meilleur, un eventuel reranker de second rang.

## Travail actif borne

- [ ] Figer un jeu de probes de pertinence memoire/RAG base sur des questions reelles FridaDev:
  - architecture / modules externes,
  - memoire / identite,
  - infra OVH / migration,
  - preferences utilisateur durables,
  - contexte circonstanciel recent.
- [ ] Requalifier le candidate generation avant arbitre:
  - verifier si `top_k=5` est trop court;
  - tester un recall plus large avant filtrage;
  - etudier une selection plus stratifiee (`user`, `assistant`, proximite conversationnelle, ou lanes distinctes) au lieu d'un top-k plat unique.
- [ ] Mieux structurer les candidats remis a l'arbitre:
  - `source_kind` explicite (`trace`, `summary`, `hint`, etc.);
  - role, age, conversation_id, summary parent si disponible;
  - reduction des quasi-doublons avant arbitrage.
- [ ] Faire de `summaries` une voie de retrieval de premier rang quand des resumes existent:
  - retrieval direct sur `summaries`;
  - fusion propre `traces + summaries`;
  - contrat stable pour ne pas injecter deux fois la meme information.
- [ ] Evaluer un petit reranker seulement apres le premier travail de tri:
  - sous forme locale ou service Docker/API si c'est coherent avec l'architecture globale;
  - uniquement apres amelioration du candidate generation et de la structuration du panier;
  - pour reranker un recall deja meilleur, pas pour compenser un retrieval encore plat.
- [ ] Definir les mesures de succes:
  - pertinence percue des items gardes;
  - baisse des faux positifs generiques;
  - meilleure couverture des souvenirs vraiment utiles;
  - absence de regression latence/cout excessive.
- [ ] Documenter la V2 retenue avant implementation lourde.

## Hors scope

- changement de doctrine identite / prompt;
- redesign complet de l'arbitre;
- ajout immediat d'un reranker pour masquer un recall encore mauvais;
- changement de modele d'embedding sans preuve prealable;
- microservices / extraction d'agents externes;
- refactor opportuniste large de `memory_store.py`;
- fix separe du finding actif `record_arbiter_decisions()` sur le modele effectif persiste.

## Notes de reprise

Ordre de travail recommande:
1. probes et metrique de pertinence;
2. candidate generation / recall;
3. structuration du panier arbitre;
4. voie `summaries` autonome;
5. evaluation eventuelle d'un reranker seulement apres assainissement du panier candidat;
6. ajustement eventuel des seuils arbitre seulement apres amelioration amont.
