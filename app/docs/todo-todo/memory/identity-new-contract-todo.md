# Identity New Contract - TODO operatoire code-first

Statut: TODO operatoire ouvert
Classement: `app/docs/todo-todo/memory/`
Source doctrinale: `app/docs/todo-todo/memory/identity-new-contract-plan.md`
Portee: traduire le plan doctrinal en lots d'implementation, de migration, de nettoyage legacy, d'admin, d'observabilite et de tests
Decision du 2026-04-17: conserver le document doctrinal existant comme plan cible, puis produire ici un TODO operatoire fonde sur l'etat reel du code courant
Decision runtime du 2026-04-17: le lot B1+B2 est maintenant actif; ce TODO suit desormais l'etat reel post-staging/agent periodique et laisse B3/B4/B5/B6 ouverts

## 1. Regle de travail

- [x] Le plan doctrinal reste dans `identity-new-contract-plan.md`; ce TODO ne re-raconte pas la doctrine, il la traduit en travail executable.
- [x] La baseline auditee du 2026-04-17 est maintenant le regime `static + mutable narrative` avec staging distinct, buffer de 15 paires conversation-scoped et agent identitaire periodique fail-closed; B3/B4/B5/B6 restent ouverts.
- [ ] Garder ce TODO comme check-list lotable: chaque case future doit correspondre a un patch ferme, testable et reversible.

## A. Audit code-first de l'existant

### A1. Cadence, point d'appel runtime et payload actuel

- [x] `app/core/chat_llm_flow.py` appelle `record_identity_entries_for_mode(...)` apres finalisation assistant avec une paire complete `user/assistant`; la couture active n'utilise plus `recent_2`.
- [x] `app/core/chat_memory_flow.py` persiste d'abord les entrees legacy via `persist_identity_entries(...)`, puis appelle `_run_periodic_identity_agent(...)`; la maintenance canonique ne passe plus par un rewriter per-turn.
- [x] `app/core/chat_memory_flow.py` garde le chemin agent periodique en `fail-closed` sur le canon: si le staging, l'appel agent ou l'applicateur cassent, `identity_mode_apply.action=persist_enforced_buffered` reste vrai, la conversation continue et le buffer n'est pas purge.
- [x] `app/memory/memory_identity_periodic_agent.py::_build_agent_payload()` envoie aujourd'hui `buffer_pairs`, `buffer_pairs_count`, `buffer_target_pairs`, `identities.{llm,user}.{static,mutable_current}` et `mutable_budget.{target_chars,max_chars}`.
- [x] `app/memory/memory_identity_staging.py` introduit un staging identitaire distinct de `identity_mutables` avec buffer temporaire, compteur de paires, statut du dernier run et flag `auto_canonization_suspended` encore passif.

### A2. Prompt actuel, contrat agent et garde d'admission

- [x] `app/prompts/identity_periodic_agent.txt` remplace le prompt runtime actif et demande un JSON strict par sujet avec operations locales et bloc `meta`.
- [x] Le contrat technique actif n'accepte plus `rewrite/no_change`; il attend `no_change|add|tighten|merge|raise_conflict`, plus `meta.execution_status`, `meta.buffer_pairs_count` et `meta.window_complete`.
- [x] `app/memory/memory_identity_periodic_apply.py::validate_periodic_agent_contract()` ferme la structure du JSON, interdit les mixes `no_change + autres ops` et exige les ancres explicites de `tighten` et `merge`.
- [x] `app/identity/mutable_identity_validation.py` reste seulement un garde prompt-like/system/tool/runtime meta; la fermeture metier contre preferences, conforts conversationnels et reprises utilitaires reste a enrichir.
- [x] `app/memory/arbiter.py::run_identity_periodic_agent()` appelle maintenant un LLM unique `identity_periodic_agent` avec `temperature=0.0`, `max_tokens=1400` et une sortie attendue a operations locales.

### A3. Persistence de la mutable et projection active

- [x] `app/memory/memory_identity_mutables.py` reste le stockage canonique actif du `mutable` par sujet; le staging est desormais distinct et additif.
- [x] `app/memory/memory_identity_periodic_apply.py` applique cote Python les operations locales au canon actif, degrade vers `no_change` en cas de doute et n'efface jamais le buffer sur contrat casse.
- [x] `app/identity/active_identity_projection.py` compile encore simplement `[STATIQUE]` + `[MUTABLE]` par sujet; aucune projection du buffer temporaire, du dernier verdict agent ou d'une suspension automatique n'est disponible.
- [x] `app/core/hermeneutic_node/inputs/identity_input.py` n'expose que `static` et `mutable`; le noeud hermeneutique ne lit pas encore un staging identitaire ni des metadonnees d'agent.
- [x] `app/identity/identity.py` et `build_identity_block()` supposent encore que le canon actif se limite a `static` et `mutable`, sans couche intermediaire.

### A4. Surfaces admin, `/identity` et observabilite

- [x] `app/admin/admin_identity_read_model_service.py` expose `static`, `mutable`, `legacy_fragments`, `evidence`, `conflicts`; aucun bloc `identity_staging` ni resume du dernier passage agent n'est prevu.
- [x] `app/admin/admin_identity_runtime_representations_service.py` expose seulement `structured_identity` et `injected_identity_text`; aucun etat du buffer ni verdict compact du dernier agent.
- [x] `app/web/hermeneutic_admin/render_identity_mutable_editor.js` encode en dur `TARGET_CHARS = 1500` et `MAX_CHARS = 1650` et raconte encore une mutable canonique unique, pas un regime `canon actif + staging`.
- [x] `app/admin/admin_identity_mutable_edit_contract.py` expose encore `mutable_budget` depuis `config.IDENTITY_MUTABLE_TARGET_CHARS` et `config.IDENTITY_MUTABLE_MAX_CHARS`, tandis que `app/admin/admin_identity_mutable_edit_service.py` continue a rejeter une edition admin au-dela de `config.IDENTITY_MUTABLE_MAX_CHARS`; l'API admin mutable raconte donc encore et enforce l'ancien regime budgetaire meme si l'UI ou la gouvernance evoluent plus tard.
- [x] `app/web/hermeneutic_admin/render_identity_read_model.js` et `app/web/identity/render_identity_runtime_representations.js` ne savent montrer ni buffer, ni dernier run, ni suspension de canonisation.
- [x] `app/core/chat_memory_flow.py` journalise maintenant `identity_periodic_agent_apply` et `app/memory/memory_identity_periodic_agent.py` journalise `identity_periodic_agent`; les anciennes surfaces `identity_mutable_rewrite*` ne sont plus la couture runtime active.
- [x] `app/docs/states/specs/log-module-contract.md` impose deja des logs identity compacts, mais ne couvre pas encore les champs du nouveau regime `buffer/staging/scores/operations/promotion/suspension`.

### A5. Specs, docs et tests qui encodent encore l'ancien regime

- [x] `app/docs/states/specs/identity-mutable-edit-contract.md` aligne encore l'edition admin sur le `identity_mutable_rewriter` courant et autorise des preferences de conversation sur des themes techniques.
- [x] `app/docs/states/specs/identity-governance-contract.md` et `app/identity/identity_governance.py` presentent encore `IDENTITY_MUTABLE_TARGET_CHARS = 1500` et `IDENTITY_MUTABLE_MAX_CHARS = 1650` comme doctrine verrouillee du rewriter actif.
- [x] `app/docs/states/specs/identity-read-model-contract.md` et `app/docs/states/specs/identity-surface-contract.md` decrivent encore une base active sans staging, sans verdict agent et sans suspension automatique.
- [x] `app/tests/unit/memory/test_identity_mutable_rewriter_phase1b.py` encode `rewrite/no_change`, accepte des preferences et des interets techniques comme contenu mutable valide, et suppose `updated_by = identity_mutable_rewriter`.
- [x] `app/tests/unit/chat/test_chat_memory_flow.py` couvre maintenant la couture `persist_identity_entries(...) -> staging/agent periodique`, le fail-closed et la paire bufferisee nettoyee.
- [x] `app/tests/unit/memory/test_arbiter_phase4.py` couvre maintenant `arbiter.run_identity_periodic_agent(...)`, le nouveau caller OpenRouter et le prompt runtime actif.
- [x] `app/tests/unit/logs/test_chat_turn_logger_phase2.py` et plusieurs tests serveur/admin encodent encore les reason codes `rewrite_applied`, `no_change`, `update_reason = rewrite` et l'absence de staging dans les surfaces `/identity`.

## B. Checklist de migration du runtime

### B1. Introduire le buffer de 15 paires et la nouvelle couture d'execution

- [x] Remplacer la dependance a `recent_2` dans `app/core/chat_llm_flow.py` par une accumulation de paires completes `user/assistant` distincte du `mutable` canonique.
- [x] Definir un module proprietaire de staging sous `app/memory/` pour stocker le buffer temporaire, `buffer_pairs_count`, `buffer_target_pairs`, `last_agent_run_ts`, `last_agent_status` et `auto_canonization_suspended`.
- [x] Choisir explicitement une persistence additive du staging sans reutiliser `identity_mutables` comme faux buffer.
- [x] Faire en sorte que le buffer soit consomme puis efface seulement apres un passage agent termine; interdire tout effacement silencieux sur timeout, exception, JSON invalide ou rejet deterministe.
- [x] Requalifier `identity_mode_apply` pour qu'il ne laisse plus croire qu'une canonisation mutable se produit a chaque tour.

### B2. Remplacer le rewriter per-turn par un agent identitaire periodique

- [x] Introduire une couture d'agent identitaire periodique qui lit `static`, `mutable` et staging buffer; l'alimentation explicite en evidences utiles et tensions ouvertes reste reportee a B6.
- [x] Revoir `app/memory/arbiter.py` pour sortir du label et de l'appel `identity_mutable_rewriter` actifs.
- [x] Remplacer le schema binaire `no_change|rewrite` par un JSON strict d'operations `no_change|add|tighten|merge|raise_conflict`, avec bloc `meta` ferme.
- [x] Introduire un applicateur deterministe cote Python qui verifie types, champs obligatoires, meta, ancres explicites de `tighten|merge` et doublons exacts; les scores/plages complets restent reportes a B3.
- [x] Garder l'agent periodique decouple de l'edition admin `POST /api/admin/identity/mutable`, qui continue a toucher le canon actif et jamais le staging.

### B3. Introduire la ponderation et les seuils deterministes

- [ ] Calculer `support_pairs`, `last_occurrence_distance`, `frequency_norm`, `recency_norm` et `strength` dans une couche deterministe, pas seulement dans le prompt.
- [ ] Encoder les seuils `strength < 0.35`, `0.35 <= strength < 0.60` et `strength >= 0.60` dans l'applicateur final, avec journalisation compacte des verdicts.
- [ ] Interdire qu'un LLM invente ses propres scores sans reconciliation deterministe cote Python.
- [ ] Rendre visibles les scores compacts par sujet et par operation dans les surfaces admin/logs sans exposer de texte brut.

### B4. Introduire la promotion `mutable -> static` et la double saturation

- [ ] Definir un detecteur de saturation du `mutable` compatible avec la cible `3000` caracteres et la projection active `static + mutable narrative`.
- [ ] Choisir l'algorithme deterministe qui promeut vers `static` le ou les traits les plus forts sans dupliquer ce qui est deja fixe.
- [ ] Recaler explicitement le budget de projection du `static` pour qu'une promotion n'agrandisse pas `static` d'une main puis ne le fasse pas tronquer silencieusement de l'autre.
- [ ] Introduire la suspension automatique de canonisation si `mutable` et `static` sont tous deux satures, puis l'exposer comme verite operateur.
- [ ] Garantir qu'une promotion automatique n'ecrase ni les editions operateur du statique ni les corrections humaines recentes.

### B5. Adapter la projection active, le read-model et les representations runtime

- [ ] Etendre `app/core/hermeneutic_node/inputs/identity_input.py` seulement quand le staging a une forme stable, en preservant la compatibilite du noeud hermeneutique.
- [ ] Etendre `app/identity/active_identity_projection.py` et `app/identity/identity.py` pour conserver le canon actif `static + mutable` tout en exposant separement l'etat staging.
- [ ] Ajouter a `app/admin/admin_identity_read_model_service.py` un bloc `identity_staging` coherent avec le plan (`buffer_pairs_count`, `buffer_target_pairs`, `last_agent_run_ts`, `last_agent_status`, `auto_canonization_suspended`).
- [ ] Ajouter a `app/admin/admin_identity_runtime_representations_service.py` le staging et le resume compact du dernier verdict agent, sans mentir sur la base active injectee.
- [ ] Migrer explicitement la seam admin budget encore active: `app/admin/admin_identity_mutable_edit_contract.py` ne doit plus exposer `mutable_budget` depuis les caps legacy de `app/config.py`, `app/admin/admin_identity_mutable_edit_service.py` ne doit plus enforce implicitement `IDENTITY_MUTABLE_MAX_CHARS` comme verite du nouveau regime, et le raccord `app/config.py` doit etre requalifie ou remplace en coherence avec la nouvelle doctrine.
- [ ] Adapter les frontends `app/web/hermeneutic_admin/render_identity_read_model.js`, `app/web/hermeneutic_admin/render_identity_mutable_editor.js`, `app/web/hermeneutic_admin/render_identity_governance.js` et `app/web/identity/render_identity_runtime_representations.js` au nouveau regime.

### B6. Revoir l'articulation avec le legacy identity

- [ ] Decider explicitement si `persist_identity_entries(...)`, `identity_evidence` et `identity_conflicts` restent strictement legacy/diagnostic ou s'ils servent aussi le nouvel agent comme matiere auxiliaire.
- [ ] Ne pas laisser le staging devenir une resurrection masquee du legacy fragmentaire `accepted|deferred|rejected`.
- [ ] Trancher le sort des tensions ouvertes du nouvel agent: reutilisation explicite de `identity_conflicts` ou nouvelle persistence dediee.
- [ ] Maintenir `identities`, `identity_evidence` et `identity_conflicts` hors injection active tant qu'une migration explicite n'a pas ete decidee.

## C. Nettoyage de l'ancien systeme

### C1. Ce qui devra disparaitre

- [ ] Supprimer le schema binaire `rewrite/no_change` des contrats agent, des parseurs, des tests et des reason codes qui presentent encore la reecriture globale comme verite active.
- [ ] Supprimer le declenchement a chaque tour branche sur `recent_2` dans `app/core/chat_llm_flow.py`.
- [ ] Supprimer les hypotheses tests/docs qui lient automatiquement `identity_mode_apply.action=persist_enforced` a une reecriture mutable immediate.
- [ ] Supprimer les valeurs UI en dur `target=1500` et `max=1650` une fois la nouvelle gouvernance livree.

### C2. Ce qui devra etre remplace

- [ ] Remplacer `app/prompts/identity_mutable_rewriter.txt` par un prompt d'agent identitaire periodique fonde sur des propositions identitaires et des operations locales.
- [ ] Remplacer `app/memory/memory_identity_mutable_rewriter.py::validate_rewriter_contract()` par un validateur de contrat multi-operations et multi-scores.
- [ ] Remplacer `app/identity/mutable_identity_validation.py` comme simple garde prompt-like par une garde d'admission plus riche qui refuse aussi preferences, conforts conversationnels et formulations utilitaires.
- [ ] Remplacer les evenements `identity_mutable_rewrite` et `identity_mutable_rewrite_apply` par un contrat d'observabilite qui raconte le nouveau regime reel, ou versionner explicitement ces events.
- [ ] Remplacer les assumptions `updated_by = identity_mutable_rewriter` et `update_reason = rewrite` dans les surfaces admin/tests par une semantique qui distingue agent periodique, application deterministe, promotion et correction operateur.

### C3. Ce qui devra etre garde

- [ ] Garder `identity_mutables` comme stockage du canon actif `mutable`, distinct du staging.
- [ ] Garder la projection runtime active `static + mutable narrative` tant qu'aucune autre projection n'a ete explicitement decidee.
- [ ] Garder les routes admin `POST /api/admin/identity/static`, `POST /api/admin/identity/mutable`, `GET /api/admin/identity/read-model` et `GET /api/admin/identity/runtime-representations`, mais les faire dire vrai sur le nouveau regime.
- [ ] Garder la politique de logs compacts sans dump de contenu brut.

### C4. Ce qui devra seulement etre requalifie

- [ ] Requalifier `identity-governance` pour distinguer les caps doctrinaux cibles du nouveau regime et les caps encore actifs du runtime non migre.
- [ ] Requalifier `identity-read-model` et `/identity` pour distinguer canon actif, staging temporaire et verdict agent sans les confondre.
- [ ] Requalifier les roadmaps/clotures archivees qui parlaient d'une `mutable narrative` reecrite, afin qu'elles restent historiques sans redevenir une verite active.
- [ ] Requalifier les tests qui continueraient a passer tout en validant en fait l'ancien monde.

## D. Garde-fous de regression

### D1. Tests unitaires a ecrire ou remplacer

- [ ] Ecrire des tests de buffer: accumulation tour par tour, declenchement a 15 paires exactes, absence d'appel agent avant seuil, effacement du buffer seulement apres application reussie.
- [ ] Ecrire des tests de contrat JSON strict: root invalide, champs manquants, types invalides, scores hors bornes, operation inconnue, bloc `meta` incoherent.
- [ ] Ecrire des tests deterministes pour `frequency_norm`, `recency_norm`, `strength` et les seuils `0.35/0.60`.
- [ ] Ecrire des tests d'application deterministe pour `add`, `tighten`, `merge`, `raise_conflict`, non-doublon avec `static`, non-doublon avec `mutable`, et contradiction semantique.
- [ ] Ecrire des tests de promotion `mutable -> static`, de recalage du budget de projection et de suspension automatique en cas de double saturation.

### D2. Tests d'integration admin, read-model et representations runtime

- [ ] Adapter les tests serveur/admin pour verifier `identity_staging`, `last_agent_status`, `buffer_pairs_count` et `auto_canonization_suspended`.
- [ ] Verifier que `/api/admin/identity/read-model` et `/api/admin/identity/runtime-representations` continuent a dire vrai sur le canon actif injecte tout en montrant le staging separement.
- [ ] Verifier que `/identity` et `/hermeneutic-admin` n'affichent jamais le staging comme s'il etait deja canonise.
- [ ] Verifier que l'edition operateur du `mutable` reste coherente avec le read-model et ne consomme jamais le buffer temporaire.

### D3. Compatibilite runtime et comportement fail-closed

- [ ] Verifier que `build_identity_input()` et `build_identity_block()` restent compatibles avec le noeud hermeneutique et le main LLM pendant toute la migration.
- [ ] Verifier qu'un JSON agent invalide, partiel ou contradictoire n'ecrit rien dans le canon actif, ne purge pas le buffer et laisse un statut observable.
- [ ] Verifier qu'un timeout ou une exception agent laisse la conversation principale saine et observable, sans fausse canonisation.
- [ ] Verifier que l'observabilite reste compacte: pas de dump brut du buffer, pas de dump brut des candidats, pas de dump brut des textes canoniques.

## E. Sort explicite des documents et specs existants

### E1. Documents a modifier quand la migration runtime commencera

- [ ] Modifier `app/docs/states/specs/identity-mutable-edit-contract.md` pour retirer les formulations qui admettent encore preferences de conversation, positionnement relationnel ou interets utilitaires comme contenu mutable recevable.
- [ ] Modifier `app/docs/states/specs/identity-governance-contract.md` et `app/identity/identity_governance.py` pour sortir du cadrage doctrinal ferme `1500/1650` propre au rewriter courant.
- [ ] Modifier `app/docs/states/specs/identity-read-model-contract.md` et `app/docs/states/specs/identity-surface-contract.md` pour introduire `identity_staging`, le dernier verdict agent et la suspension automatique.
- [ ] Modifier `app/docs/states/specs/log-module-contract.md` pour decrire les champs du nouveau regime identitaire.
- [ ] Modifier les textes UI `/identity` et `/hermeneutic-admin` qui presentent encore la mutable unique comme seule couche mouvante.

### E2. Documents a relire avant patch runtime, puis a traiter comme sources historiques

- [ ] Relire `app/docs/todo-done/refactors/identity-vs-prompt-separation-todo.md` comme base historique de separation `identity/prompt`, sans en reutiliser tel quel le contrat `rewrite narrative`.
- [ ] Relire `app/docs/todo-done/refactors/identity-control-surface-todo.md` comme historique de la surface actuelle `static + mutable narrative`, pas comme cible du nouveau staging.
- [ ] Relire `app/docs/todo-done/notes/hermeneutical-add-todo.md` uniquement pour les dependances historiques avec l'hermeneutique.
- [ ] Relire `app/docs/todo-todo/memory/hermeneutical-post-stabilization-todo.md` pour identifier les coutures actives avec le noeud hermeneutique et les preuves post-rollout a conserver.

### E3. References depot a garder separees

- [ ] Garder `README.md`, `app/docs/README.md` et `AGENTS.md` avec deux references distinctes: `identity-new-contract-plan.md` pour la doctrine cible et `identity-new-contract-todo.md` pour le chantier operatoire.
- [ ] Eviter de re-fusionner plus tard le plan doctrinal et le TODO operatoire dans un meme fichier.

## F. Sort explicite de l'ancien prompt `identity_mutable_rewriter`

- [ ] Relire ligne par ligne `app/prompts/identity_mutable_rewriter.txt` avant tout patch runtime et marquer chaque consigne comme `a retirer`, `a remplacer` ou `a conserver`.
- [ ] Retirer du prompt legacy tout ce qui autorise encore `tone`, `relational positioning`, `continuity of voice`, `durable interests` ou `conversational preferences` comme porte d'entree generale du `mutable`.
- [ ] Remplacer l'instruction de reecriture globale du bloc par un contrat d'agent qui travaille sur des propositions identitaires canonisables et des operations locales.
- [ ] Verifier qu'aucun autre appel, test, doc ou nom d'event ne continue a presenter ce prompt legacy comme la source active du nouveau regime.
- [ ] Traiter comme risque majeur le cas ou ce prompt serait oublie: il pourrait continuer a recanoniser des preferences ou du positionnement relationnel meme si une partie de l'applicateur Python a deja migre.

## G. Definition of done operatoire

- [ ] Le runtime n'appelle plus un rewriter global par tour et n'utilise plus `recent_2` comme base identitaire canonique.
- [ ] Le staging de 15 paires existe, reste distinct du canon actif et est observable cote admin.
- [ ] L'agent identitaire periodique renvoie un JSON strict par operations, applique par une couche deterministe et fail-closed.
- [ ] Les scores `frequency_norm`, `recency_norm` et `strength`, les seuils, la promotion `mutable -> static` et la suspension automatique sont implementes et testes.
- [ ] Le read-model, les runtime representations, `/identity`, `/hermeneutic-admin` et les logs disent vrai sur le nouveau regime sans exposer de contenu brut.
- [ ] Les specs vivantes et les tests ne valident plus silencieusement l'ancien monde `rewrite/no_change` par tour.
