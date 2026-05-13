# Memory RAG observability remediation - TODO

Statut: ouvert
Source: audit Memory/RAG du 2026-05-13
Classement: `app/docs/todo-todo/memory/`
Portee: observabilite, preuves operateur et surfaces compactes du systeme Memory/RAG
Hors-scope: refonte RAG, changement de doctrine memoire, modification des seuils, top-k, scoring, prompts, creation d'une nouvelle architecture retrieval, exposition de contenu brut

## 1. Intention

Ce TODO transforme l'audit Memory/RAG du 2026-05-13 en feuille de route bornee.

L'audit a etabli que le RAG est actif dans le runtime courant: traces et summaries sont persistees, embeddings et index sont presents, le retrieval hybride fonctionne, l'arbitre memoire est execute et le prompt principal recoit des blocs memoire quand le mode et les decisions le permettent.

Le probleme a corriger n'est donc pas: "remplacer le RAG".

Le probleme est: l'operateur doit pouvoir prouver, sans contenu brut, ce qui a ete recupere, dedupe, arbitre, rejete, retenu, injecte dans le prompt principal, et expose eventuellement a un provider secondaire.

Ce chantier vise uniquement:
- a rendre visible l'exposition memoire du validation agent;
- a produire une preuve compacte par tour de la chaine `retrieved -> basket -> drop/keep -> injected`;
- a stabiliser les reason codes de l'arbitre memoire;
- a rendre l'admin Memory content-minimized par defaut;
- a separer les metriques d'injection par lane;
- a mettre a jour les docs actives sur la lane summaries et la semantique top-k.

## 2. Source de verite

- [ ] Traiter ce fichier comme la source de travail active des six remediations issues de l'audit Memory/RAG du 2026-05-13.
- [ ] Garder `app/docs/states/architecture/memory-rag-current-pipeline-cartography.md` comme cartographie active a corriger quand les constats runtime summaries/top-k sont documentes.
- [ ] Garder `app/docs/states/specs/memory-rag-pre-arbiter-basket-contract.md` comme contrat du panier pre-arbitre.
- [ ] Garder `app/docs/states/specs/memory-rag-summaries-lane-contract.md` comme contrat minimal de la lane summaries, a rafraichir sans changer la doctrine.
- [ ] Garder `app/docs/states/specs/memory-admin-surface-contract.md` comme contrat de surface admin tant qu'il n'est pas explicitement modifie.
- [ ] Relire l'etat courant du code avant chaque lot pour eviter de corriger un finding deja stale.
- [ ] Ne jamais utiliser un contenu brut conversationnel, trace, summary, prompt, message, token, DSN ou secret comme preuve documentaire.

## 3. Principes de cloture

- [ ] Chaque lot doit etre ferme par un patch petit, reversible et teste.
- [ ] Chaque preuve runtime doit rester compacte: presence, counts, longueurs, statuts, timestamps, source kinds, reason codes, hash courts.
- [ ] Aucun lot ne doit changer les seuils, le scoring, le top-k, les prompts ou la composition runtime hors bug explicitement confirme.
- [ ] Aucun lot ne doit exposer de contenu brut dans les logs compacts, le read-model admin ou les preuves de cloture.
- [ ] Les specs vivantes ne sont modifiees que si un champ expose, une attente operateur ou une preuve attendue change.
- [ ] Chaque lot runtime doit ajouter ou adapter au moins un test qui aurait echoue avec le finding initial.
- [ ] Les lots de documentation ne doivent pas deplacer la doctrine memoire ni ouvrir un refactor general.

## 4. Ordre de correction recommande

1. Lot 1: observer l'exposition memoire du validation agent/provider secondaire.
2. Lot 2: ajouter le snapshot compact de chaine memoire tour par tour.
3. Lot 3: remplacer les raisons libres agregees de l'arbiter par des reason codes stables.
4. Lot 4: rendre l'admin Memory content-minimized par defaut.
5. Lot 5: separer les metriques d'injection par lane.
6. Lot 6: corriger les docs actives summaries/top-k.

Cet ordre commence par les deux P1 d'auditabilite, puis ferme les risques de redaction et de lisibilite operateur, puis corrige la documentation active.

## Lot 1 - Observabilite provider secondaire / validation agent

Objectif: prouver content-free ce que le validation agent expose au provider secondaire.

Finding couvert:
- P1: le payload provider secondaire du validation agent n'est pas observable comme exposition memoire.

Fichiers probablement touches:
- `app/core/hermeneutic_node/validation/validation_agent.py`
- `app/core/chat_service.py`
- `app/observability/chat_turn_logger.py`
- tests chat / hermeneutic node / validation agent

Hors-scope:
- [x] Ne pas modifier les decisions du validation agent.
- [x] Ne pas modifier le prompt principal.
- [x] Ne pas afficher le contenu de `canonical_inputs`.
- [x] Ne pas faire de vrai appel provider dans les tests.

Cases de correction:
- [x] Ajouter un event compact lie au tour, par exemple `validation_prompt_prepared` ou equivalent.
- [x] Inclure seulement des metriques content-free: presence des inputs, tailles, counts, source kinds, hash courts si necessaire.
- [x] Distinguer clairement exposition provider secondaire et payload principal.
- [x] Garantir que les champs `content`, `prompt`, `messages`, `trace`, `summary`, `conversation` bruts ne sont pas logges.
- [x] Documenter le nouveau champ ou event si le contrat operateur/log change.

Tests attendus:
- test avec `requests.post` fake prouvant que le validation agent expose une empreinte compacte;
- test de redaction prouvant l'absence de contenu brut dans l'event;
- test de non-regression du fail-open validation agent.

Preuves runtime attendues:
- lecture compacte d'un event de validation agent sans contenu brut;
- preuve qu'un tour peut distinguer `main_payload` et `validation_payload` par counts/status.

Condition de cloture:
- [x] L'operateur peut savoir qu'une memoire a ete visible du validation agent, sous quelle forme compacte, sans voir le contenu expose.

## Lot 2 - Snapshot compact de chaine memoire

Objectif: produire une preuve compacte par tour de la chaine `retrieved -> dedup/basket -> arbiter drop/keep -> injected`.

Finding couvert:
- P1: pas de snapshot compact durable complet `retrieved -> basket -> drop/keep -> injected`.

Fichiers probablement touches:
- `app/core/chat_memory_flow.py`
- `app/memory/memory_traces_summaries.py`
- `app/memory/memory_pre_arbiter_basket.py`
- `app/memory/arbiter.py`
- `app/memory/memory_arbiter_audit.py`
- `app/observability/chat_turn_logger.py`
- `app/observability/hermeneutic_node_logger.py`
- tests memory flow / pre-arbiter / observability

Hors-scope:
- [ ] Ne pas stocker le contenu des candidats dans le snapshot compact.
- [ ] Ne pas changer les decisions de dedup, basket ou arbiter.
- [ ] Ne pas modifier le seuil du panier pre-arbitre.
- [ ] Ne pas modifier l'injection finale dans le prompt principal.

Cases de correction:
- [ ] Definir un snapshot content-free par candidat: `candidate_id`, `source_kind`, `source_lane`, score bucket ou score arrondi, rang, dedup status, arbiter status, injected bool.
- [ ] Relier les candidats retrieved aux candidats basket via IDs stables.
- [ ] Capturer les candidats ecartes avant arbiter avec un `reason_code` non sensible quand disponible.
- [ ] Capturer les decisions arbiter keep/drop avec reason code ou reason key compact.
- [ ] Capturer les IDs injectes dans le prompt principal et distinguer `none`, `hints_only`, `summary_only`, `trace_memory`.
- [ ] Rendre le snapshot lisible via logs ou read-model admin sans ouvrir les tables brutes.

Tests attendus:
- test retrieval avec candidat qui entre dans le basket et candidat dedupe;
- test arbiter keep/drop avec snapshot final;
- test prompt injection avec ID injecte;
- test de redaction sans contenu brut.

Preuves runtime attendues:
- lecture d'un tour recent montrant counts et IDs/hash courts sur les quatre etapes;
- preuve qu'un candidat non injecte a un statut explicite sans relecture de contenu brut.

Condition de cloture:
- [ ] Pour un tour donne, l'operateur peut expliquer compactement ce qui a ete recupere, ecarte, garde et injecte.

## Lot 3 - Reason codes stables pour l'arbiter

Objectif: remplacer les raisons libres agregees par des codes stables, avec eventuellement longueur/hash court de la raison brute, mais jamais le texte libre dans les agregats compacts.

Finding couvert:
- P2: les raisons de rejet arbiter sont des textes libres tronques, pas des reason codes.

Fichiers probablement touches:
- `app/memory/arbiter.py`
- `app/memory/memory_arbiter_audit.py`
- `app/admin/admin_memory_history_dashboard.py`
- `app/observability/chat_turn_logger.py`
- tests arbiter / logs / admin memory

Hors-scope:
- [ ] Ne pas modifier le prompt ou le jugement de l'arbiter.
- [ ] Ne pas modifier les seuils `semantic_relevance` ou `contextual_gain`.
- [ ] Ne pas supprimer l'audit durable existant sans decision separee.
- [ ] Ne pas exposer la raison libre dans les agregats compacts.

Cases de correction:
- [ ] Definir un vocabulaire minimal de `reason_code` stable pour les rejets courants.
- [ ] Mapper les raisons libres du modele vers ces codes au moment de l'observabilite compacte.
- [ ] Conserver au besoin `reason_chars` et `reason_sha256_12`, sans texte brut.
- [ ] Preserver les champs existants utiles: kept/dropped counts, decision_source, model, fallback_used.
- [ ] Adapter les surfaces admin qui affichent les agregats de rejet.

Tests attendus:
- test rejection reason libre longue ou sensible -> code stable seulement dans l'event compact;
- test fallback arbiter conserve un code stable;
- test admin agregats par reason_code.

Preuves runtime attendues:
- event `arbiter` compact avec `rejection_reason_code_counts`;
- verification explicite qu'aucune phrase libre n'apparait dans l'agregat compact.

Condition de cloture:
- [ ] Les rejets arbiter sont aggregables par codes stables sans fuite de texte libre.

## Lot 4 - Admin Memory content-minimized par defaut

Objectif: eviter que l'apercu admin arbiter expose directement `candidate_content` et `reason` dans la surface par defaut.

Finding couvert:
- P2: Admin Memory expose encore du contenu brut dans l'apercu arbiter.

Fichiers probablement touches:
- `app/admin/admin_memory_durable_dashboard.py`
- `app/admin/admin_memory_service.py`
- `app/web/` surfaces Memory admin si le contrat UI change
- `app/docs/states/specs/memory-admin-surface-contract.md`
- tests admin Memory / frontend admin

Hors-scope:
- [ ] Ne pas supprimer les traces ou decisions durables existantes.
- [ ] Ne pas casser une eventuelle surface de detail explicitement protegee.
- [ ] Ne pas afficher de contenus bruts dans les preuves de test.
- [ ] Ne pas changer les droits admin OVH.

Cases de correction:
- [ ] Remplacer l'apercu par defaut par des champs compacts: role, score, keep, reason_code, chars, hash court, timestamps.
- [ ] Supprimer `candidate_content` et `reason` bruts de la reponse par defaut.
- [ ] Si un detail brut reste necessaire, le placer derriere une route/action explicite et documentee, hors vue de synthese.
- [ ] Mettre a jour le contrat admin si la reponse API change.

Tests attendus:
- test API dashboard: absence de `candidate_content` et `reason` bruts dans l'apercu par defaut;
- test presence des empreintes compactes;
- test frontend si les colonnes changent.

Preuves runtime attendues:
- lecture compacte `/api/admin/memory/dashboard` montrant les nouvelles cles;
- preuve que la synthese reste exploitable sans contenu brut.

Condition de cloture:
- [ ] L'admin Memory par defaut donne une preuve arbiter exploitable sans exposer de contenu candidat brut.

## Lot 5 - Separer les metriques d'injection par lane

Objectif: distinguer clairement `trace memory` injectee, `summary/context parent` injecte et `context hints` injectes.

Finding couvert:
- P2: la metrique `injected` melange traces memoire, summaries parents et context hints.

Fichiers probablement touches:
- `app/observability/prompt_injection_summary.py`
- `app/admin/admin_memory_history_dashboard.py`
- `app/core/chat_prompt_context.py`
- `app/core/chat_memory_flow.py`
- tests prompt context / logs / admin memory

Hors-scope:
- [ ] Ne pas modifier les blocs de prompt eux-memes.
- [ ] Ne pas changer les decisions d'injection.
- [ ] Ne pas requalifier les context hints comme memoire durable.
- [ ] Ne pas supprimer l'ancien champ avant compatibilite explicite si l'UI en depend.

Cases de correction:
- [ ] Ajouter des booleens/champs distincts: `trace_memory_injected`, `summary_context_injected`, `context_hints_injected`.
- [ ] Garder des counts separes pour chaque lane.
- [ ] Clarifier la synthese admin: injection memoire durable vs contexte recent/hints.
- [ ] Conserver ou deprecier proprement le bool `injected` global.

Tests attendus:
- test prompt avec trace memory seule;
- test prompt avec context hints seuls;
- test prompt avec parent summary/context seul;
- test admin aggregats par lane.

Preuves runtime attendues:
- lecture `prompt_prepared` montrant les trois lanes separees;
- exemple compact d'un tour `hints_only` et d'un tour `trace_memory`.

Condition de cloture:
- [ ] L'operateur peut savoir si une injection vient de la memoire durable, d'un summary/context parent ou des context hints.

## Lot 6 - Corriger les docs actives summaries/top-k

Objectif: mettre a jour la cartographie RAG et le contrat summaries lane pour refleter le runtime courant: summaries live, lane additive, `top_k_returned` pouvant depasser `top_k_requested`.

Findings couverts:
- P2: les docs actives disent encore que la lane summaries est neutre live.
- P3: la semantique `top_k_returned > top_k_requested` est correcte mais peu lisible.

Fichiers probablement touches:
- `app/docs/states/architecture/memory-rag-current-pipeline-cartography.md`
- `app/docs/states/specs/memory-rag-summaries-lane-contract.md`
- `app/docs/states/specs/memory-rag-pre-arbiter-basket-contract.md`
- `app/docs/states/specs/memory-admin-surface-contract.md` si les champs admin sont clarifies

Hors-scope:
- [ ] Ne pas changer le code retrieval.
- [ ] Ne pas changer `top_k`, la limite summaries ou le panier pre-arbitre.
- [ ] Ne pas faire passer une baseline runtime ponctuelle pour une garantie permanente.
- [ ] Ne pas reouvrir les roadmaps archivees.

Cases de correction:
- [ ] Remplacer les mentions actives `summaries=0` / lane neutre live par un statut date et verifiable.
- [ ] Documenter que la lane summaries peut etre additive dans le chemin pre-arbitre.
- [ ] Clarifier la difference entre `top_k_requested`, candidats traces, candidats summaries et `top_k_returned`.
- [ ] Ajouter une preuve runtime compacte datee sans contenu brut.

Tests attendus:
- docs-only: `git diff --check`, grep des anciennes formulations, coherence des references.
- si des champs admin sont ajustes par un lot precedent, tests admin correspondants.

Preuves runtime attendues:
- counts summaries/traces/embeddings;
- probe retrieval compact montrant trace candidates + summary candidates.

Condition de cloture:
- [ ] Les docs actives ne contredisent plus le runtime observe sur summaries et top-k.

## Condition de non-prolongation

- [ ] Le chantier se ferme quand les six lots ci-dessus couvrent les sept findings de l'audit par tests et preuves compactes.
- [ ] Aucun lot 7 ne doit etre ajoute pour refondre Memory/RAG, changer les seuils, ajouter un reranker, creer une nouvelle memoire ou revoir la doctrine.
- [ ] Les sujets decouverts hors observabilite compacte doivent etre sortis dans un audit ou TODO separe, avec justification explicite.
- [ ] La cloture ne depend pas d'une amelioration subjective de la pertinence RAG, seulement de la capacite a prouver la chaine existante.
- [ ] Une fois les six lots livres, ce fichier doit etre marque clos puis archive dans `app/docs/todo-done/` selon les conventions du depot.

## Matrice findings -> lots

| Finding audit Memory/RAG | Severite | Lot de remediation |
| --- | --- | --- |
| Payload provider secondaire du validation agent non observable comme exposition memoire | P1 | Lot 1 |
| Pas de snapshot compact durable complet `retrieved -> basket -> drop/keep -> injected` | P1 | Lot 2 |
| Raisons de rejet arbiter en textes libres tronques, pas en reason codes | P2 | Lot 3 |
| Admin Memory expose du contenu brut dans l'apercu arbiter | P2 | Lot 4 |
| Metrique `injected` melange traces memoire, summaries parents et context hints | P2 | Lot 5 |
| Docs actives disent encore que la lane summaries est neutre live | P2 | Lot 6 |
| Semantique `top_k_returned > top_k_requested` correcte mais peu lisible | P3 | Lot 6 |

## Notes de prudence

- [ ] Ne jamais transformer ce chantier en refactor general de `app/memory/`.
- [ ] Ne jamais confondre memoire durable RAG, summaries, context hints, recent context, stimmung et identities.
- [ ] Ne jamais presenter un hash comme une anonymisation cryptographique suffisante si le contenu source est faible ou devinable.
- [ ] Ne jamais stocker un prompt, message, trace, summary ou conversation brut dans un nouvel event compact.
- [ ] Ne jamais introduire un endpoint admin brut par commodite sans contrat explicite et test de redaction de la surface par defaut.
- [ ] Ne jamais modifier les decisions de retrieval/arbitrage pour satisfaire une preuve d'observabilite.
- [ ] Ne pas requalifier le choix "pas de reranker actif" sans rouvrir explicitement la decision documentaire existante.
