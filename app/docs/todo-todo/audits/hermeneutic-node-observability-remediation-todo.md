# Hermeneutic node observability remediation - TODO

Statut: ouvert
Source: audit Noeud hermeneutique du 2026-05-14 sur `f9775a8`
Classement: `app/docs/todo-todo/audits/`
Portee: observabilite, surfaces admin, payloads provider, fallbacks et activation runtime du `node_state` du noeud hermeneutique
Hors-scope: refonte du noeud hermeneutique, changement des prompts, changement des seuils ou providers, reouverture des chantiers Identity et Memory/RAG, exposition de contenu brut, refactor general du chat flow

## 1. Intention

Ce TODO transforme l'audit industriel du noeud hermeneutique en feuille de route de remediation bornee.

L'audit n'a pas demande de remplacer la doctrine hermeneutique ni de rouvrir les chantiers Identity ou Memory/RAG. Le probleme a corriger est plus operatoire: l'operateur doit pouvoir prouver, sans contenu brut, ce que le noeud recoit, ce qu'il transmet aux providers, ce qui est injecte dans le prompt principal, ce qui echoue en fail-open, et quel etat hermeneutique est porte d'un tour au suivant.

Decision produit explicite: le `node_state` ne doit pas rester un objet calcule/teste mais non actif dans le runtime chat. Il doit etre persiste par conversation, relu au tour suivant, passe a `build_primary_node(existing_node_state=...)`, mis a jour apres jugement hermeneutique, observe compactement, et teste sur au moins deux tours successifs.

Ce chantier vise uniquement:
- a retirer le brut legacy Identity de la surface Hermeneutic Admin par defaut;
- a tracer une empreinte compacte du bloc hermeneutique effectivement injecte;
- a observer l'exposition provider secondaire du `stimmung_agent`;
- a rendre visibles les stages critiques provider/prompt dans Hermeneutic Admin;
- a conserver la cause technique compacte des fail-open du `primary_node`;
- a activer le `node_state` persistant en runtime chat;
- a corriger les docs actives devenues stale sur logs/tests.

## 2. Source de verite

- [ ] Traiter ce fichier comme la source de travail active des remediations issues de l'audit Noeud hermeneutique du 2026-05-14.
- [ ] Garder les specs `app/docs/states/specs/hermeneutic-node-*.md` comme contrats vivants a mettre a jour seulement quand un champ expose, un comportement runtime ou une preuve operateur change.
- [ ] Garder `app/docs/states/specs/log-module-contract.md` comme contrat des events logs tant qu'il n'est pas explicitement mis a jour.
- [ ] Garder les archives `app/docs/todo-done/notes/hermeneutical-add-todo.md`, `app/docs/todo-done/validations/hermeneutical-post-stabilization-todo.md` et `app/docs/todo-done/refactors/hermeneutic-convergence-node-todo.md` comme sources historiques, sans les rouvrir comme travaux actifs.
- [ ] Relire l'etat courant du code avant chaque lot, notamment les fichiers listes dans le lot, pour eviter de corriger un finding deja devenu stale.
- [ ] Ne jamais utiliser un contenu brut de conversation, prompt, trace, summary, identite, candidat, token, DSN ou secret comme preuve de cloture.

## 3. Principes de cloture

- [ ] Chaque lot doit etre ferme par un patch petit, reversible et teste.
- [ ] Chaque preuve runtime doit rester compacte: presence, counts, longueurs, statuts, timestamps, noms de stage, reason codes, error classes et hash courts.
- [ ] Les lots d'observabilite ne doivent pas modifier les decisions du noeud hermeneutique.
- [ ] Aucun lot ne doit modifier la composition du prompt principal sauf si le lot vise explicitement l'observation de ce qui est deja injecte.
- [ ] Aucun lot ne doit exposer de contenu brut dans les logs compacts, les read-models admin, le frontend admin ou les preuves de retour.
- [ ] Les tests ajoutes doivent echouer avec le finding initial, pas seulement verifier une forme triviale.
- [ ] Le lot `node_state` doit prouver deux tours successifs en runtime de test: lecture d'un etat initial, passage a `build_primary_node`, persistence d'un nouvel etat, puis relecture au tour suivant.

## 4. Ordre de correction recommande

1. Lot 1: compacter `identity-candidates` dans Hermeneutic Admin.
2. Lot 2: ajouter `hermeneutic_prompt_injection` dans `prompt_prepared`.
3. Lot 3: ajouter `stimmung_prompt_prepared` content-free.
4. Lot 4: afficher les stages critiques provider/prompt dans Hermeneutic Admin.
5. Lot 5: conserver la cause compacte des fail-open `primary_node`.
6. Lot 6: activer le `node_state` persistant en runtime chat.
7. Lot 7: corriger les docs stale et cloturer le TODO.

Cet ordre ferme d'abord les deux P1 d'auditabilite et de redaction, puis les P2 de provider secondaire, admin et fallbacks, puis livre l'activation runtime du `node_state`, qui est le seul lot fonctionnel obligatoire du chantier.

## Lot 1 - Compacter identity-candidates dans Hermeneutic Admin

Objectif: faire en sorte que la surface Hermeneutic Admin par defaut ne serve plus de contenu brut legacy Identity dans l'apercu `identity-candidates`.

Finding couvert:
- P1: Hermeneutic Admin sert encore du brut legacy Identity par defaut.

Fichiers probablement touches:
- `app/admin/admin_hermeneutics_service.py`
- `app/admin/admin_hermeneutics_routes.py`
- `app/web/hermeneutic_admin/api.js`
- `app/web/hermeneutic_admin/render.js`
- `app/docs/states/specs/admin-implementation-spec.md`
- `app/docs/states/specs/log-module-contract.md` si la surface log/admin change
- `app/tests/test_server_admin_hermeneutics_phase4.py`
- `app/tests/integration/frontend_admin/test_frontend_hermeneutic_admin_phase6.py`

Hors-scope:
- [x] Ne pas supprimer les donnees legacy en DB.
- [x] Ne pas requalifier le legacy Identity comme source d'injection active.
- [x] Ne pas ajouter une route de detail brut dans ce lot.
- [x] Ne pas changer les surfaces Identity canoniques hors redaction de la vue Hermeneutic Admin.

Cases de correction:
- [x] Identifier les champs bruts actuellement servis par defaut dans `identity-candidates`.
- [x] Remplacer les champs bruts par une projection compacte: `subject`, `source_kind`, `status`, `weight`, `chars`, `sha256_12`, timestamps et reason codes quand disponibles.
- [x] Supprimer de la reponse par defaut les cles qui portent du texte brut ou qui permettent de reconstruire un contenu identitaire.
- [x] Adapter le rendu frontend pour afficher les champs compacts sans supposer un titre extrait du contenu brut.
- [x] Mettre a jour la spec admin si le contrat API expose change.

Tests attendus:
- test API Hermeneutic Admin: absence des cles brutes dans `identity-candidates`;
- test API: presence des empreintes compactes utiles;
- test frontend: la page reste rendue avec la projection compacte;
- test de redaction: aucune valeur brute identitaire, conversationnelle ou prompt-like dans la reponse par defaut.

Preuves runtime attendues:
- lecture compacte de l'endpoint admin montrant les cles compactes et l'absence des cles brutes;
- preuve que la page Hermeneutic Admin reste fonctionnelle sans recevoir le brut;
- aucune citation de contenu identitaire dans la preuve.

Condition de cloture:
- [x] L'admin Hermeneutic charge par defaut une projection `identity-candidates` exploitable sans servir de contenu legacy Identity brut au navigateur.

## Lot 2 - Empreinte du bloc hermeneutique injecte

Objectif: ajouter a `prompt_prepared` une preuve compacte du bloc hermeneutique reellement injecte dans le prompt principal.

Finding couvert:
- P1: pas d'empreinte compacte du bloc hermeneutique reellement injecte dans le prompt principal.

Fichiers probablement touches:
- `app/core/chat_prompt_context.py`
- `app/core/chat_llm_flow.py`
- `app/core/chat_service.py`
- `app/observability/chat_turn_logger.py`
- `app/observability/hermeneutic_node_logger.py`
- `app/core/prompt_injection_summary.py` si l'empreinte rejoint les syntheses de prompt
- `app/tests/test_server_logs_phase3.py`
- `app/tests/test_server_chat_hermeneutic_insertion_contract.py`
- `app/tests/unit/logs/test_chat_turn_logger_hermeneutic_observability.py`

Hors-scope:
- [x] Ne pas modifier le texte du bloc hermeneutique injecte.
- [x] Ne pas modifier le prompt principal ni les decisions du noeud.
- [x] Ne pas logger le bloc, le prompt, les messages ou les canonical inputs bruts.
- [x] Ne pas melanger cette empreinte avec les empreintes Identity ou Memory/RAG deja existantes.

Cases de correction:
- [x] Calculer l'empreinte depuis le meme bloc que celui assemble pour le prompt principal.
- [x] Ajouter un objet compact `hermeneutic_prompt_injection` dans `prompt_prepared` ou un event adjacent du meme tour.
- [x] Inclure uniquement des metriques content-free: `present`, `chars`, `sha256_12`, `final_judgment_posture`, `final_output_regime`, `epistemic_regime`, `directives_count`, `source` et flags de fallback si disponibles.
- [x] Distinguer bloc absent, bloc present normal et bloc present apres fallback.
- [x] Verifier que l'empreinte ne contient aucune directive brute.

Tests attendus:
- test prompt principal avec bloc hermeneutique present: `hermeneutic_prompt_injection.present=true`;
- test de redaction: aucun contenu du bloc, prompt, message ou canonical input dans `prompt_prepared`;
- test fallback hermeneutique: l'empreinte reste presente avec un `source` ou `reason_code` compact;
- test de non-regression des champs Identity/Memory existants dans `prompt_prepared`.

Preuves runtime attendues:
- lecture du dernier `prompt_prepared` montrant seulement presence, longueurs, hash court et regimes;
- preuve que l'empreinte correspond au prompt principal sans dump du prompt;
- preuve que l'absence de bloc, si elle arrive, est explicite.

Condition de cloture:
- [x] Pour un tour donne, l'operateur peut prouver quel bloc hermeneutique a ete injecte par empreinte compacte, sans lire le prompt complet.

## Lot 3 - stimmung_prompt_prepared content-free

Objectif: observer content-free ce que le `stimmung_agent` prepare et expose a son provider secondaire.

Finding couvert:
- P2: exposition provider secondaire `stimmung_agent` non observee par un event prepare compact.

Fichiers probablement touches:
- `app/core/stimmung_agent.py`
- `app/core/chat_turn_runtime_inputs.py`
- `app/core/llm_client.py`
- `app/observability/chat_turn_logger.py`
- `app/observability/hermeneutic_node_logger.py`
- `app/docs/states/specs/hermeneutic-node-stimmung-input-contract.md`
- `app/docs/states/specs/log-module-contract.md`
- `app/tests/unit/core/test_stimmung_agent.py`
- `app/tests/unit/logs/test_chat_turn_logger_hermeneutic_observability.py`
- `app/tests/test_server_logs_phase3.py`

Hors-scope:
- [x] Ne pas modifier le prompt du `stimmung_agent`.
- [x] Ne pas modifier ses decisions, son modele, ses settings ou son fail-open.
- [x] Ne pas logger le prompt secondaire, les messages, le recent window ou le tour utilisateur brut.
- [x] Ne pas fusionner l'observabilite `stimmung_agent` avec celle du validation agent.

Cases de correction:
- [x] Ajouter un event compact `stimmung_prompt_prepared` ou un nom equivalent coherent avec le logger existant.
- [x] Relier l'event au tour quand les IDs sont disponibles, sans creer de couplage fragile.
- [x] Inclure les metriques content-free utiles: provider caller, model id hash ou famille non sensible, input sections presentes, counts, longueurs, hash courts si necessaire, fail-open status.
- [x] Distinguer exposition provider secondaire du payload principal LLM.
- [x] Garantir l'absence de cles brutes comme `prompt`, `messages`, `content`, `user_message`, `recent_window`.

Tests attendus:
- test avec appel provider fake prouvant l'emission de l'event prepare;
- test avec inputs contenant recent context/memory flags prouvant les counts sans contenu;
- test de redaction stricte;
- test de non-regression du fail-open `stimmung_agent`.

Preuves runtime attendues:
- lecture compacte d'un event `stimmung_prompt_prepared`;
- preuve que `stimmung_agent` et payload principal sont distinguables par stage/caller;
- aucune exposition de prompt ou message brut.

Condition de cloture:
- [x] L'operateur peut savoir qu'un provider secondaire `stimmung_agent` a recu un payload, avec quelles familles d'inputs compactes, sans voir le contenu expose.

## Lot 4 - Hermeneutic Admin affiche les stages critiques

Objectif: rendre visibles dans Hermeneutic Admin les stages critiques deja disponibles dans les logs, notamment provider/prompt, validation et fallbacks.

Finding couvert:
- P2: Hermeneutic Admin masque des stages critiques disponibles dans les logs.

Fichiers probablement touches:
- `app/admin/admin_hermeneutics_service.py`
- `app/admin/admin_logs.py`
- `app/admin/admin_stage_latency_summary.py`
- `app/web/hermeneutic_admin/api.js`
- `app/web/hermeneutic_admin/main.js`
- `app/web/hermeneutic_admin/render.js`
- `app/docs/states/specs/log-module-contract.md`
- `app/docs/states/specs/admin-implementation-spec.md`
- `app/tests/test_server_admin_hermeneutics_phase4.py`
- `app/tests/test_server_logs_phase3.py`
- `app/tests/test_server_logs_phase6.py`
- `app/tests/integration/frontend_admin/test_frontend_hermeneutic_admin_phase6.py`

Hors-scope:
- [x] Ne pas creer une nouvelle base de logs.
- [x] Ne pas afficher de payload brut dans l'admin.
- [x] Ne pas changer les events runtime pour compenser une liste frontend incomplete, sauf si un event manque vraiment.
- [x] Ne pas refondre l'UX Hermeneutic Admin au-dela de la lisibilite des stages.

Cases de correction:
- [x] Lister les stages critiques attendus: `stimmung_agent`, `stimmung_prompt_prepared`, `hermeneutic_node_insertion`, `primary_node`, `validation_prompt_prepared`, `validation_agent`, `prompt_prepared`, `llm_call`.
- [x] Exposer ou afficher ces stages quand ils existent dans les logs compacts.
- [x] Rendre explicite un stage absent: `not_observed`, `not_applicable` ou `missing`.
- [x] Preserver les reason codes, error classes, provider callers et latences compactes.
- [x] Adapter les tests frontend/admin aux stages ajoutes.

Tests attendus:
- test service admin: les stages critiques presents en logs sont retournes;
- test frontend: les stages provider/prompt sont visibles ou marques absents sans contenu brut;
- test de redaction sur les payloads compactes;
- test de non-regression des filtres existants.

Preuves runtime attendues:
- lecture Hermeneutic Admin ou endpoint admin montrant les stages critiques avec status/counts;
- preuve que les stages provider secondaires sont distinguables du provider principal;
- aucune valeur brute de prompt ou conversation dans la preuve.

Condition de cloture:
- [x] L'operateur peut suivre les stages hermeneutiques critiques depuis l'admin sans ouvrir la DB ni lire des payloads bruts.

## Lot 5 - Fail-open primary_node avec cause compacte

Objectif: conserver la cause technique compacte quand le `primary_node` tombe en fail-open.

Finding couvert:
- P2: fail-open du `primary_node` perd la cause technique.

Fichiers probablement touches:
- `app/core/hermeneutic_node/runtime/primary_node.py`
- `app/core/chat_service.py`
- `app/observability/hermeneutic_node_logger.py`
- `app/observability/chat_turn_logger.py`
- `app/docs/states/specs/hermeneutic-node-primary-verdict-contract.md`
- `app/docs/states/specs/log-module-contract.md`
- `app/tests/unit/core/hermeneutic_node/runtime/test_primary_node.py`
- `app/tests/unit/logs/test_chat_turn_logger_hermeneutic_observability.py`
- `app/tests/test_server_chat_hermeneutic_insertion_contract.py`

Hors-scope:
- [x] Ne pas changer les conditions de fail-open.
- [x] Ne pas bloquer la reponse utilisateur sur une erreur du noeud.
- [x] Ne pas logger exception message complet, stack trace complete, canonical inputs ou contenu prompt.
- [x] Ne pas modifier le validation agent dans ce lot sauf pour preserver la cause compacte deja produite.

Cases de correction:
- [x] Definir un vocabulaire compact: `reason_code`, `error_class`, `fallback_used`, `fallback_source`, `node_stage`.
- [x] Conserver cette cause dans le payload `primary_node` et dans le log de tour.
- [x] Distinguer parse error, invalid input, invalid node_state, provider/runtime error et unknown error quand c'est possible sans fuite.
- [x] Garantir que les erreurs techniques longues sont reduites a classe/code/hash court.
- [x] Adapter l'admin si les causes fail-open doivent etre visibles dans une synthese existante.

Tests attendus:
- test `primary_node` exception -> fallback avec `reason_code` stable;
- test invalid `existing_node_state` -> cause compacte;
- test logger/admin sans message d'exception brut;
- test de non-regression: le fail-open reste bien fail-open.

Preuves runtime attendues:
- preuve de test ou event synthetique compact montrant `fallback_used=true`, `reason_code` et `error_class`;
- aucune stack trace, prompt ou canonical input brut dans l'event compact.

Condition de cloture:
- [x] Un fail-open `primary_node` est operable: on sait pourquoi il a degrade, sans exposer de contenu ni casser la reponse.

## Lot 6 - Activation runtime du node_state persistant

Objectif: activer le `node_state` en runtime chat en le persistant par conversation, en le relisant au tour suivant et en le passant a `build_primary_node(existing_node_state=...)`.

Finding couvert:
- P2: `node_state` calcule/teste mais pas persiste/rehydrate en runtime chat.

Decision produit:
- Le `node_state` doit absolument etre actif en runtime chat. Ce lot est une activation fonctionnelle obligatoire, pas une simple clarification documentaire.

Fichiers probablement touches:
- `app/core/hermeneutic_node/runtime/node_state.py`
- `app/core/hermeneutic_node/runtime/primary_node.py`
- `app/core/chat_service.py`
- `app/core/chat_turn_runtime_inputs.py`
- `app/memory/memory_store.py`
- `app/memory/memory_store_infra.py`
- nouveau module dedie possible: `app/memory/hermeneutic_node_state.py`
- migration/bootstrap DB idempotent si persistence SQL ajoutee
- `app/observability/hermeneutic_node_logger.py`
- `app/observability/chat_turn_logger.py`
- `app/docs/states/specs/hermeneutic-node-state-persistence-contract.md`
- `app/tests/unit/core/hermeneutic_node/runtime/test_node_state.py`
- `app/tests/test_server_chat_hermeneutic_insertion_contract.py`
- tests DB/memory store a creer si persistence ajoutee

Hors-scope:
- [x] Ne pas changer la doctrine de calcul du `node_state`.
- [x] Ne pas stocker de prompt, message, trace, summary, identite ou canonical input brut dans l'etat persiste.
- [x] Ne pas utiliser le `node_state` comme source souveraine contre les guards du tour courant.
- [x] Ne pas modifier le provider, les prompts, les seuils ou les decisions hors passage effectif de l'etat existant.
- [x] Ne pas backfiller une production historique dans ce lot.

Cases de correction:
- [x] Definir le stockage durable minimal du `node_state` par `conversation_id`, avec schema/version, timestamps et champs deja valides par `validate_node_state()`.
- [x] Ajouter une initialisation/migration idempotente si une table ou colonne nouvelle est necessaire.
- [x] Lire le `node_state` courant avant l'appel a `build_primary_node()`.
- [x] Passer explicitement `existing_node_state=...` a `build_primary_node()`.
- [x] Mettre a jour le `node_state` apres jugement hermeneutique selon la sortie runtime retenue.
- [x] Observer compactement la lecture/ecriture: `state_read_present`, `state_read_valid`, `state_write_attempted`, `state_write_changed`, `state_schema_version`, hash court et reason code.
- [x] Gerer les etats invalides en fail-open compact: ignorer l'etat invalide, logger `invalid_node_state`, continuer le tour.
- [x] Mettre a jour la spec de persistence si le contrat runtime est modifie.

Tests attendus:
- test unitaire persistence: set/get par conversation sans contenu brut;
- test migration/bootstrap idempotent si DB modifiee;
- test chat deux tours successifs: le premier tour persiste un `node_state`, le second le relit et le passe a `build_primary_node(existing_node_state=...)`;
- test etat invalide: ignored + reason_code compact + tour continue;
- test observabilite: event compact sans contenu brut;
- test de non-regression: un nouveau `conversation_id` demarre sans etat preexistant.

Preuves runtime attendues:
- preuve in-container ou endpoint admin/log montrant counts d'etats lus/ecrits et timestamps sans contenu brut;
- event compact pour deux tours successifs montrant `state_read_present=false` puis `state_read_present=true`;
- preuve que le payload principal ne contient pas de dump du `node_state` au-dela des effets normaux du jugement hermeneutique.

Condition de cloture:
- [x] Le runtime chat persiste, relit, passe et met a jour le `node_state` par conversation, avec preuve compacte et test de deux tours successifs.

## Lot 7 - Docs stale et cloture

Objectif: corriger les docs actives devenues stale sur logs/tests et fermer ce TODO uniquement quand les lots runtime sont livres.

Finding couvert:
- P3: docs actives partiellement stale sur logs/tests.

Fichiers probablement touches:
- `app/docs/states/specs/log-module-contract.md`
- `app/docs/states/specs/hermeneutic-node-validation-agent-contract.md`
- `app/docs/states/specs/hermeneutic-node-state-persistence-contract.md`
- `app/docs/states/specs/hermeneutic-node-stimmung-input-contract.md`
- `app/docs/states/specs/admin-implementation-spec.md`
- `app/docs/README.md` si les points d'entree changent
- ce TODO

Hors-scope:
- [ ] Ne pas reecrire les specs doctrinales sans changement runtime livre.
- [ ] Ne pas archiver ce TODO avant que tous les lots soient coches et prouves.
- [ ] Ne pas creer un Lot 8 de confort ou de refactor.
- [ ] Ne pas deplacer les archives historiques.

Cases de correction:
- [ ] Aligner la liste des stages logs actifs avec les events livres par les lots 2 a 5.
- [ ] Corriger les references de tests obsoletes ou chemins stale.
- [ ] Documenter la persistence runtime effective du `node_state` apres le Lot 6.
- [ ] Verifier les references croisees dans `app/docs/README.md` si elles changent.
- [ ] Cocher les conditions de non-prolongation une fois les sept lots fermes.
- [ ] Ajouter une note de cloture et deplacer le fichier vers `app/docs/todo-done/audits/` dans un patch d'archivage separe.

Tests attendus:
- `git diff --check`;
- greps de references stale aux stages/logs/tests;
- verification que toutes les cases de lot sont fermees avant cloture;
- aucune suite runtime requise si ce lot reste docs-only.

Preuves runtime attendues:
- aucune preuve runtime nouvelle attendue pour le lot docs-only;
- les preuves des lots 1 a 6 doivent etre referencees par leurs commits/tests de cloture.

Condition de cloture:
- [ ] Les docs actives de logs/admin/node_state refletent le runtime livre, et le TODO est pret a etre archive.

## Condition de non-prolongation

- [ ] Les deux P1 sont couverts par preuves content-free.
- [ ] Les quatre P2 sont couverts par patchs testes, dont l'activation runtime obligatoire du `node_state`.
- [ ] Le P3 documentaire est ferme sans rouvrir la doctrine hermeneutique.
- [ ] Aucune correction n'a introduit d'exposition brute dans les logs, admin surfaces ou preuves de cloture.
- [ ] Aucun seuil, prompt, provider ou scoring n'a ete change hors decision explicite documentee.
- [ ] Le chantier se ferme apres les sept lots: pas de Lot 8, pas de refactor general du noeud hermeneutique.

## Matrice findings -> lots

| Finding audit | Severite | Lot |
| --- | --- | --- |
| Hermeneutic Admin sert encore du brut legacy Identity par defaut | P1 | Lot 1 |
| Pas d'empreinte compacte du bloc hermeneutique reellement injecte dans le prompt principal | P1 | Lot 2 |
| Exposition provider secondaire `stimmung_agent` non observee par un event prepare compact | P2 | Lot 3 |
| Hermeneutic Admin masque des stages critiques disponibles dans les logs | P2 | Lot 4 |
| Fail-open du `primary_node` perd la cause technique | P2 | Lot 5 |
| `node_state` calcule/teste mais pas persiste/rehydrate en runtime chat | P2 | Lot 6 |
| Docs actives partiellement stale sur logs/tests | P3 | Lot 7 |

## Notes de prudence

- [ ] Le `node_state` persistant est une memoire technique du noeud hermeneutique par conversation; il ne remplace ni Identity, ni Memory/RAG, ni les guards du tour courant.
- [ ] Les payloads provider secondaires doivent etre observables par empreintes compactes, jamais par dumps de prompts ou messages.
- [ ] Les surfaces admin doivent rester utiles pour operer, mais content-minimized par defaut.
- [ ] Les erreurs/fallbacks doivent etre lisibles par `reason_code` et `error_class`, sans stack trace longue ni contenu runtime brut.
- [ ] Les docs ne doivent etre corrigees qu'apres verification du runtime courant, pour eviter de documenter une intention au lieu d'un comportement livre.
