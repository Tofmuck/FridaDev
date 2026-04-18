# Identity New Contract - Archive operatoire de cloture

Statut: chantier termine, archive le 2026-04-18
Classement: `app/docs/todo-done/refactors/`
Source doctrinale: `app/docs/states/policies/identity-new-contract-plan.md`
Portee: conserver la trace lotable du chantier operatoire termine, ses preuves, ses lots fermes et ses decisions de migration
Decision du 2026-04-17: conserver le document doctrinal existant comme plan cible, puis produire ici un TODO operatoire fonde sur l'etat reel du code courant
Decision runtime du 2026-04-17: les lots B1-B6 sont maintenant actifs; ce TODO suit desormais l'etat reel post-staging/agent periodique, scoring deterministe, promotion et suspension automatique; les tensions `raise_conflict` restent des verdicts conversation-scoped compacts dans la derniere activite periodique, sans reutiliser `identity_conflicts`
Decision de cloture du 2026-04-18: le chantier operatoire `identity-new-contract` est termine; ce document devient une archive de reference et ne doit plus etre traite comme un TODO actif.

## 1. Regle de travail

- [x] Le plan doctrinal reste dans `identity-new-contract-plan.md`; ce TODO ne re-raconte pas la doctrine, il la traduit en travail executable.
- [x] La baseline auditee du 2026-04-17 est maintenant le regime `static + mutable narrative` avec staging distinct, buffer de 15 paires conversation-scoped, agent identitaire periodique fail-closed, scoring deterministe, promotion vers `static` et suspension automatique; B5 et B6 sont fermes dans l'etat courant.
- [x] Garder ce TODO comme check-list lotable: chaque case future doit correspondre a un patch ferme, testable et reversible.

## A. Audit code-first de l'existant

### A1. Cadence, point d'appel runtime et payload actuel

- [x] `app/core/chat_llm_flow.py` appelle `record_identity_entries_for_mode(...)` apres finalisation assistant avec une paire complete `user/assistant`; la couture active n'utilise plus `recent_2`.
- [x] `app/core/chat_memory_flow.py` persiste d'abord les entrees legacy via `persist_identity_entries(...)`, puis appelle `_run_periodic_identity_agent(...)`; la maintenance canonique ne passe plus par un rewriter per-turn.
- [x] `app/core/chat_memory_flow.py` garde le chemin agent periodique en `fail-closed` sur le canon: si le staging, l'appel agent ou l'applicateur cassent, `identity_mode_apply.action=record_legacy_identity_diagnostics_and_stage` reste vrai, la conversation continue et le buffer n'est pas purge.
- [x] `app/memory/memory_identity_periodic_agent.py::_build_agent_payload()` envoie aujourd'hui `buffer_pairs`, `buffer_pairs_count`, `buffer_target_pairs`, `identities.{llm,user}.{static,mutable_current}` et `mutable_budget.{target_chars,max_chars}`.
- [x] `app/memory/memory_identity_staging.py` introduit un staging identitaire distinct de `identity_mutables` avec buffer temporaire, compteur de paires, statut du dernier run et flag `auto_canonization_suspended` maintenant actif.

### A2. Prompt actuel, contrat agent et garde d'admission

- [x] `app/prompts/identity_periodic_agent.txt` remplace le prompt runtime actif et demande un JSON strict par sujet avec operations locales et bloc `meta`.
- [x] Le contrat technique actif n'accepte plus `rewrite/no_change`; il attend `no_change|add|tighten|merge|raise_conflict`, plus `meta.execution_status`, `meta.buffer_pairs_count` et `meta.window_complete`.
- [x] `app/memory/memory_identity_periodic_apply.py::validate_periodic_agent_contract()` ferme la structure du JSON, interdit les mixes `no_change + autres ops` et exige les ancres explicites de `tighten` et `merge`.
- [x] `app/identity/mutable_identity_validation.py` ferme maintenant aussi l'entree metier du `mutable`: refus prompt-like, preferences conversationnelles, conforts d'echange, cadrages utilitaires, positionnements relationnels trop faibles et formulations non assez identitaires.
- [x] `app/memory/arbiter.py::run_identity_periodic_agent()` appelle maintenant un LLM unique `identity_periodic_agent` avec `temperature=0.0`, `max_tokens=1400` et une sortie attendue a operations locales.

### A3. Persistence de la mutable et projection active

- [x] `app/memory/memory_identity_mutables.py` reste le stockage canonique actif du `mutable` par sujet; le staging est desormais distinct et additif.
- [x] `app/memory/memory_identity_periodic_apply.py` applique cote Python les operations locales au canon actif, degrade vers `no_change` en cas de doute et n'efface jamais le buffer sur contrat casse.
- [x] `app/identity/active_identity_projection.py` compile encore simplement `[STATIQUE]` + `[MUTABLE]` par sujet; aucune projection du buffer temporaire, du dernier verdict agent ou d'une suspension automatique n'est disponible.
- [x] `app/core/hermeneutic_node/inputs/identity_input.py` n'expose que `static` et `mutable`; le noeud hermeneutique ne lit pas encore un staging identitaire ni des metadonnees d'agent.
- [x] `app/identity/identity.py` et `build_identity_block()` supposent encore que le canon actif se limite a `static` et `mutable`, sans couche intermediaire.

### A4. Surfaces admin, `/identity` et observabilite

- [x] `app/admin/admin_identity_read_model_service.py` expose maintenant `identity_staging`, le canon actif et les couches `legacy_fragments` / `evidence` / `conflicts`; B6 y requalifie aussi le legacy comme diagnostique seulement.
- [x] `app/admin/admin_identity_runtime_representations_service.py` expose maintenant `structured_identity`, `injected_identity_text` et `identity_staging` avec scope conversationnel compact.
- [x] `app/web/hermeneutic_admin/render_identity_mutable_editor.js` encode encore en dur `TARGET_CHARS = 3000` et `MAX_CHARS = 3300` et raconte une mutable canonique unique, pas encore un regime `canon actif + staging + promotion + suspension`.
- [x] `app/admin/admin_identity_mutable_edit_contract.py` expose toujours `mutable_budget` depuis `config.IDENTITY_MUTABLE_TARGET_CHARS` et `config.IDENTITY_MUTABLE_MAX_CHARS`, tandis que `app/admin/admin_identity_mutable_edit_service.py` continue a rejeter une edition admin au-dela de `config.IDENTITY_MUTABLE_MAX_CHARS`; l'API admin mutable raconte donc encore le budget canonique courant sans exposer staging, promotion ni suspension.
- [x] `app/web/hermeneutic_admin/render_identity_read_model.js` et `app/web/identity/render_identity_runtime_representations.js` montrent maintenant le staging, le dernier run utile et la qualification legacy diagnostique hors canon actif.
- [x] `app/core/chat_memory_flow.py` journalise maintenant `identity_periodic_agent_apply` et `app/memory/memory_identity_periodic_agent.py` journalise `identity_periodic_agent`; les anciennes surfaces `identity_mutable_rewrite*` ne sont plus la couture runtime active.
- [x] `app/docs/states/specs/log-module-contract.md` impose des logs identity compacts et couvre maintenant les champs du regime `buffer/staging/scores/operations/promotion/suspension`.

### A5. Specs, docs et tests qui encodent encore l'ancien regime

- [x] `app/docs/states/specs/identity-mutable-edit-contract.md` aligne maintenant le budget admin et la garde d'admission sur le regime periodique actif; il reste borne a la mutable canonique et n'expose pas le staging.
- [x] `app/docs/states/specs/identity-governance-contract.md` et `app/identity/identity_governance.py` presentent maintenant `IDENTITY_MUTABLE_TARGET_CHARS = 3000` et `IDENTITY_MUTABLE_MAX_CHARS = 3300` comme doctrine verrouillee du regime periodique actif; la requalification complete des surfaces admin reste a faire.
- [x] `app/docs/states/specs/identity-read-model-contract.md` et `app/docs/states/specs/identity-surface-contract.md` racontent maintenant le staging, le verdict agent utile et la separation legacy diagnostique / canon actif.
- [x] `app/tests/unit/memory/test_identity_mutable_rewriter_phase1b.py` est maintenant borne a une compatibilite legacy retiree: il ne valide plus `rewrite/no_change` comme verite runtime active et n'attend plus d'ecriture canonique.
- [x] `app/tests/unit/chat/test_chat_memory_flow.py` couvre maintenant la couture `persist_identity_entries(...) -> staging/agent periodique`, le fail-closed et la paire bufferisee nettoyee.
- [x] `app/tests/unit/memory/test_arbiter_phase4.py` couvre maintenant `arbiter.run_identity_periodic_agent(...)`, le nouveau caller OpenRouter et le prompt runtime actif.
- [x] `app/tests/unit/logs/test_chat_turn_logger_phase2.py` et les tests serveur/admin racontent maintenant le legacy comme `legacy_diagnostic*` ou `identity_periodic_agent`, sans revalider silencieusement `update_reason = rewrite`.

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

- [x] Calculer `support_pairs`, `last_occurrence_distance`, `frequency_norm`, `recency_norm` et `strength` dans une couche deterministe `app/memory/memory_identity_periodic_scoring.py`, pas seulement dans le prompt.
- [x] Encoder les seuils `strength < 0.35`, `0.35 <= strength < 0.60` et `strength >= 0.60` dans l'applicateur final, avec verdicts `rejected|deferred|accepted`.
- [x] Interdire qu'un LLM invente ses propres scores sans reconciliation deterministe cote Python; le prompt runtime lui interdit maintenant d'emettre des champs de score.
- [x] Rendre visibles les scores compacts par sujet et par operation dans `identity_periodic_agent`, `identity_periodic_agent_apply` et les summaries runtime, sans exposer de texte brut.

### B4. Introduire la promotion `mutable -> static` et la double saturation

- [x] Definir un detecteur de saturation du `mutable` compatible avec la cible `3000` caracteres et la projection active `static + mutable narrative`.
- [x] Choisir l'algorithme deterministe qui promeut vers `static` le ou les traits les plus forts sans dupliquer ce qui est deja fixe.
- [x] Recaler explicitement le budget utile du `static` a `3000` caracteres pour qu'une promotion n'agrandisse pas `static` d'une main puis ne le fasse pas tronquer silencieusement de l'autre.
- [x] Introduire la suspension automatique de canonisation si `mutable` et `static` sont tous deux satures, puis l'exposer comme verite operateur via `auto_canonization_suspended`, les reason codes et le staging preserve.
- [x] Garantir qu'une promotion automatique n'ecrase ni les editions operateur recentes du `mutable`, ni les edits recents du statique utilises comme garde-fou minimal avant auto-promotion.

### B5. Adapter la projection active, le read-model et les representations runtime

- [x] Preserver `app/core/hermeneutic_node/inputs/identity_input.py` en `v2` et garder le staging hors injection tant qu'aucune forme stable n'a ete explicitement ajoutee au noeud hermeneutique.
- [x] Preserver le canon actif `static + mutable` dans `app/identity/active_identity_projection.py` et `app/identity/identity.py`, puis exposer separement l'etat staging dans les surfaces admin/runtime au lieu de l'absorber dans la projection active.
- [x] Ajouter a `app/admin/admin_identity_read_model_service.py` un bloc `identity_staging` coherent avec le plan (`buffer_pairs_count`, `buffer_target_pairs`, `last_agent_run_ts`, `last_agent_status`, `last_agent_reason`, `buffer_frozen`, `auto_canonization_suspended`) ainsi qu'un resume compact de la derniere activite agent et des promotions recentes.
- [x] Ajouter a `app/admin/admin_identity_runtime_representations_service.py` le staging, le resume compact du dernier verdict agent et la distinction explicite entre canon actif injecte et staging non injecte.
- [x] Recontextualiser la seam admin budget encore active: `app/admin/admin_identity_mutable_edit_contract.py` expose toujours `mutable_budget` depuis `app/config.py`, `app/admin/admin_identity_mutable_edit_service.py` continue a faire respecter `IDENTITY_MUTABLE_MAX_CHARS`, mais la reponse operateur raconte maintenant aussi staging, promotion et suspension comme verite du regime actif.
- [x] Adapter les frontends `app/web/hermeneutic_admin/render_identity_read_model.js`, `app/web/hermeneutic_admin/render_identity_mutable_editor.js`, `app/web/hermeneutic_admin/render_identity_governance.js` et `app/web/identity/render_identity_runtime_representations.js` au nouveau regime sans afficher le staging comme deja canonise.

### B6. Revoir l'articulation avec le legacy identity

- [x] Decider explicitement si `persist_identity_entries(...)`, `identity_evidence` et `identity_conflicts` restent strictement legacy/diagnostic ou s'ils servent aussi le nouvel agent comme matiere auxiliaire.
- [x] Ne pas laisser le staging devenir une resurrection masquee du legacy fragmentaire `accepted|deferred|rejected`.
- [x] Trancher le sort des tensions ouvertes du nouvel agent: `raise_conflict` reste une tension ouverte conversation-scoped visible seulement dans la derniere activite periodique compacte (`identity_periodic_agent.latest_activity` / `identity_staging.latest_agent_activity`), sans reutiliser `identity_conflicts` ni creer une nouvelle source active de canon.
- [x] Maintenir `identities`, `identity_evidence` et `identity_conflicts` hors injection active tant qu'une migration explicite n'a pas ete decidee.

## C. Nettoyage de l'ancien systeme

### C1. Ce qui devra disparaitre

- [x] Supprimer le schema binaire `rewrite/no_change` des contrats agent, des parseurs, des tests et des reason codes qui presentent encore la reecriture globale comme verite active.
- [x] Supprimer le declenchement a chaque tour branche sur `recent_2` dans `app/core/chat_llm_flow.py`.
- [x] Supprimer les hypotheses tests/docs qui lient automatiquement `identity_mode_apply.action=persist_enforced` a une reecriture mutable immediate.
- [x] Supprimer les valeurs UI en dur `target=3000` et `max=3300` une fois la nouvelle gouvernance livree.

### C2. Ce qui devra etre remplace

- [x] Requalifier `app/prompts/identity_mutable_rewriter.txt` en repere legacy retire, pour qu'il ne puisse plus se faire passer pour un prompt runtime actif.
- [x] Requalifier `app/memory/memory_identity_mutable_rewriter.py::validate_rewriter_contract()` en shim legacy retire fail-closed, hors regime runtime actif.
- [x] Remplacer `app/identity/mutable_identity_validation.py` comme simple garde prompt-like par une garde d'admission plus riche qui refuse aussi preferences, conforts conversationnels et formulations utilitaires.
- [x] Retirer les evenements `identity_mutable_rewrite` et `identity_mutable_rewrite_apply` de l'observabilite active, au profit d'un contrat qui raconte le regime reel.
- [x] Remplacer les assumptions `updated_by = identity_mutable_rewriter` et `update_reason = rewrite` dans les surfaces admin/tests par une semantique qui distingue agent periodique, application deterministe, promotion et correction operateur.

### C3. Ce qui devra etre garde

- [x] Garder `identity_mutables` comme stockage du canon actif `mutable`, distinct du staging.
- [x] Garder la projection runtime active `static + mutable narrative` tant qu'aucune autre projection n'a ete explicitement decidee.
- [x] Garder les routes admin `POST /api/admin/identity/static`, `POST /api/admin/identity/mutable`, `GET /api/admin/identity/read-model` et `GET /api/admin/identity/runtime-representations`, mais les faire dire vrai sur le nouveau regime.
- [x] Garder la politique de logs compacts sans dump de contenu brut.

### C4. Ce qui devra seulement etre requalifie

- [x] Requalifier `identity-governance` pour distinguer les caps doctrinaux cibles du nouveau regime et les caps encore actifs du runtime non migre.
- [x] Requalifier `identity-read-model` et `/identity` pour distinguer canon actif, staging temporaire et verdict agent sans les confondre.
- [x] Requalifier les roadmaps/clotures archivees qui parlaient d'une `mutable narrative` reecrite, afin qu'elles restent historiques sans redevenir une verite active.
- [x] Requalifier les tests qui continueraient a passer tout en validant en fait l'ancien monde.

### C5. Decisions B6 appliquees

- [x] `persist_identity_entries(...)` reste en service seulement comme pipeline legacy diagnostique vers `identities`, `identity_evidence` et `identity_conflicts`; il ne pilote plus le canon actif ni le staging.
- [x] `identity_evidence` et `identity_conflicts` restent relisibles pour support/historique, mais sont explicitement qualifies legacy diagnostiques hors injection active.
- [x] `memory_identity_mutable_rewriter.py` est requalifie en shim legacy retire fail-closed; il ne pilote plus la mutable canonique ni aucun appel LLM actif.
- [x] `app/prompts/identity_mutable_rewriter.txt` devient un repere historique retire, pas un prompt runtime actif.
- [x] Les evenements et labels qui racontaient encore `identity_mutable_rewriter` / `rewrite` comme verite active sont remplaces par des coutures qui disent `legacy diagnostique` ou `identity_periodic_agent`.
- [x] `raise_conflict` ne reutilise pas `identity_conflicts`: il reste une tension ouverte conversation-scoped, compacte, non injectee et visible seulement dans la derniere activite periodique utile.

## D. Garde-fous de regression

### D1. Tests unitaires a ecrire ou remplacer

- [x] Ecrire des tests de buffer: accumulation tour par tour, declenchement a 15 paires exactes, absence d'appel agent avant seuil, effacement du buffer seulement apres application reussie.
- [x] Ecrire des tests de contrat JSON strict: root invalide, champs manquants, types invalides, operation inconnue, bloc `meta` incoherent et payload contradictoire.
- [x] Ecrire des tests deterministes pour `frequency_norm`, `recency_norm`, `strength` et les seuils `0.35/0.60`.
- [x] Ecrire des tests d'application deterministe pour `add`, `tighten`, `merge`, `raise_conflict`, non-doublon avec `static`, non-doublon avec `mutable`, et contradiction semantique.
- [x] Ecrire des tests de promotion `mutable -> static`, de recalage du budget de projection et de suspension automatique en cas de double saturation.

### D2. Tests d'integration admin, read-model et representations runtime

- [x] Adapter les tests serveur/admin pour verifier `identity_staging`, `last_agent_status`, `buffer_pairs_count` et `auto_canonization_suspended`.
- [x] Verifier que `/api/admin/identity/read-model` et `/api/admin/identity/runtime-representations` continuent a dire vrai sur le canon actif injecte tout en montrant le staging separement.
- [x] Verifier que `/identity` et `/hermeneutic-admin` n'affichent jamais le staging comme s'il etait deja canonise.
- [x] Verifier que l'edition operateur du `mutable` reste coherente avec le read-model et ne consomme jamais le buffer temporaire.

### D3. Compatibilite runtime et comportement fail-closed

- [x] Verifier que `build_identity_input()` et `build_identity_block()` restent compatibles avec le noeud hermeneutique et le main LLM pendant toute la migration.
- [x] Verifier qu'un JSON agent invalide, partiel ou contradictoire n'ecrit rien dans le canon actif, ne purge pas le buffer et laisse un statut observable.
- [x] Verifier qu'un timeout ou une exception agent laisse la conversation principale saine et observable, sans fausse canonisation.
- [x] Verifier que l'observabilite reste compacte: pas de dump brut du buffer, pas de dump brut des candidats, pas de dump brut des textes canoniques.

## E. Sort explicite des documents et specs existants

### E1. Documents a modifier quand la migration runtime commencera

- [x] Modifier `app/docs/states/specs/identity-mutable-edit-contract.md` pour retirer les formulations qui admettent encore preferences de conversation, positionnement relationnel ou interets utilitaires comme contenu mutable recevable.
- [x] Requalifier `app/docs/states/specs/identity-governance-contract.md` et `app/identity/identity_governance.py` au-dela du simple budget `3000/3300` pour rendre visibles scoring, promotion, staging et suspension sans les traiter comme de simples caps.
- [x] Modifier `app/docs/states/specs/identity-read-model-contract.md` et `app/docs/states/specs/identity-surface-contract.md` pour introduire `identity_staging`, le dernier verdict agent et la suspension automatique.
- [x] Modifier `app/docs/states/specs/log-module-contract.md` pour decrire les champs du nouveau regime identitaire.
- [x] Modifier les textes UI `/identity` et `/hermeneutic-admin` qui presentent encore la mutable unique comme seule couche mouvante.

### E2. Documents a relire avant patch runtime, puis a traiter comme sources historiques

- [x] Relire `app/docs/todo-done/refactors/identity-vs-prompt-separation-todo.md` comme base historique de separation `identity/prompt`, sans en reutiliser tel quel le contrat `rewrite narrative`.
- [x] Relire `app/docs/todo-done/refactors/identity-control-surface-todo.md` comme historique de la surface actuelle `static + mutable narrative`, pas comme cible du nouveau staging.
- [x] Relire `app/docs/todo-done/notes/hermeneutical-add-todo.md` uniquement pour les dependances historiques avec l'hermeneutique.
- [x] Relire `app/docs/todo-todo/memory/hermeneutical-post-stabilization-todo.md` pour identifier les coutures actives avec le noeud hermeneutique et les preuves post-rollout a conserver.

### E3. References depot a garder separees

- [x] Garder `README.md`, `app/docs/README.md` et `AGENTS.md` avec deux references distinctes: `identity-new-contract-plan.md` pour la doctrine cible active et `app/docs/todo-done/refactors/identity-new-contract-todo.md` pour l'archive operatoire de cloture.
- [x] Eviter de re-fusionner plus tard le plan doctrinal actif et l'archive operatoire de cloture dans un meme fichier.

## F. Sort explicite de l'ancien prompt `identity_mutable_rewriter`

- [x] Requalifier `app/prompts/identity_mutable_rewriter.txt` comme repere legacy retire pour qu'il ne puisse plus etre lu comme consigne runtime active.
- [x] Retirer du prompt legacy tout ce qui autorise encore `tone`, `relational positioning`, `continuity of voice`, `durable interests` ou `conversational preferences` comme porte d'entree generale du `mutable`.
- [x] Remplacer l'instruction de reecriture globale du bloc par un contrat d'agent qui travaille sur des propositions identitaires canonisables et des operations locales.
- [x] Verifier qu'aucun autre appel, test, doc ou nom d'event ne continue a presenter ce prompt legacy comme la source active du nouveau regime.
- [x] Traiter comme risque majeur le cas ou ce prompt serait oublie: il pourrait continuer a recanoniser des preferences ou du positionnement relationnel meme si une partie de l'applicateur Python a deja migre.

## G. Definition of done operatoire

- [x] Le runtime n'appelle plus un rewriter global par tour et n'utilise plus `recent_2` comme base identitaire canonique.
- [x] Le staging de 15 paires existe, reste distinct du canon actif et est observable cote admin.
- [x] L'agent identitaire periodique renvoie un JSON strict par operations, applique par une couche deterministe et fail-closed.
- [x] Les scores `frequency_norm`, `recency_norm` et `strength`, les seuils, la promotion `mutable -> static` et la suspension automatique sont implementes et testes.
- [x] Le read-model, les runtime representations, `/identity`, `/hermeneutic-admin` et les logs disent vrai sur le nouveau regime sans exposer de contenu brut.
- [x] Les specs vivantes et les tests ne valident plus silencieusement l'ancien monde `rewrite/no_change` par tour.
