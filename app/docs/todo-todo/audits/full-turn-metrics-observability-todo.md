# Full turn metrics observability - TODO

Statut: ouvert
Source: audit industriel d'un tour complet FridaDev du 2026-05-14
Classement: app/docs/todo-todo/audits/
Portee: preparation de metriques et agregats operateur pour un futur dashboard industriel du tour complet
Hors-scope: refonte generale de l'observabilite, observabilite frontend/admin UI, nouveaux logs dupliques, backfill massif, exposition de contenu brut, redesign admin global

## 1. Intention

Ce TODO transforme les restes non bloquants de l'audit "tour complet" en feuille de route bornee pour des metriques exploitables.

Le but n'est pas de refaire Identity, Memory/RAG ou le noeud hermeneutique. Ces chantiers ont deja leurs contrats et leurs remediations archivees.

Le but est de clarifier les mesures transverses du tour complet avant d'ouvrir un dashboard a courbes:

- partir des events et payloads compacts deja presents;
- separer les metriques ambigues avant de les agreger;
- rendre les futurs graphes impossibles a confondre entre LLM principal, providers secondaires, persistence, injection prompt et derivations post-save;
- garder une politique content-free stricte.

## 2. Source de verite

Sources a relire avant tout patch:

- `app/docs/states/specs/log-module-contract.md`
- `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`
- `app/docs/states/specs/memory-admin-surface-contract.md`
- `app/docs/states/specs/identity-surface-contract.md`
- `app/docs/states/specs/hermeneutic-node-state-persistence-contract.md`
- `app/core/chat_service.py`
- `app/core/chat_llm_flow.py`
- `app/core/chat_memory_flow.py`
- `app/core/chat_prompt_context.py`
- `app/observability/chat_turn_logger.py`
- `app/observability/log_store.py`
- surfaces admin concernees uniquement si un lot introduit une lecture operateur.

Les corrections P2 immediates de l'audit ont deja ete traitees:

- test contractuel stale `primary_node` aligne avec `node_state_*`;
- `web_reformulation_prompt_prepared` ajoute;
- logs web/search compactes;
- log Python `search_error` compacte.

Ce fichier ne doit pas les rouvrir.

## 3. Principes de non-duplication

- Ne pas creer une seconde couche d'audit parallele a `chat_log_events`, `admin_logs`, Memory Admin ou Hermeneutic Admin.
- Ne pas dupliquer un event si une lecture, un agregat ou une spec suffit.
- Toute nouvelle metrique doit pointer vers un stage existant, un champ compact existant, ou un champ compact strictement necessaire.
- Les graphes futurs doivent etre derives d'une semantique claire, pas de heuristiques UI fragiles.
- Les lots doivent rester fermables separement; aucun lot ne doit exiger de redesign complet du dashboard.

## 4. Hors-scope frontend/admin UI

Ce TODO prepare les metriques backend/logs qu'une UI pourra consommer plus tard. Il ne prouve pas que l'UI les rend correctement.

L'observabilite frontend et admin UI est hors-scope de ce fichier et devra faire l'objet d'un audit ou chantier dedie.

Exemples hors-scope:

- erreurs JavaScript navigateur;
- console errors;
- appels API frontend echoues;
- etats loading, empty ou error;
- boutons ou actions admin casses;
- incoherences entre payload backend et rendu UI;
- regressions responsive;
- tests Playwright, screenshots ou tests visuels;
- telemetrie UI content-free eventuelle;
- verification fonctionnelle des surfaces `/log`, `/admin`, `/memory-admin`, `/hermeneutic-admin` et `/identity`.

Le Lot 5 peut cadrer quelles metriques backend seraient utiles a un dashboard futur, mais il ne valide pas encore la qualite du rendu frontend.

## 5. Principes privacy et auditabilite

- Autorise: counts, booleens, durees, statuts, `reason_code`, `error_class`, longueurs, hash courts, caller/provider, lanes compactes.
- Interdit: contenu de message, prompt, identity, memory trace, summary, web query, result snippet, canonical input, DSN, token, cle ou traceback brut.
- Les metriques doivent expliquer un tour sans obliger a lire du contenu brut.
- Les logs historiques peuvent rester tels quels; pas de backfill massif dans ce chantier.
- Les valeurs legacy doivent etre marquees comme telles si elles sont deduites.

## 6. Ordre de correction recommande

1. Clarifier `persist_response`.
2. Segmenter les metriques `llm_call`.
3. Clarifier la barriere post-save JSON/streaming.
4. Definir le score de completude d'observabilite par tour.
5. Ouvrir seulement ensuite le lot dashboard/courbes.

Cet ordre evite de construire des courbes sur des signaux ambigus.

## Lot 1 - Clarifier persist_response

Objectif: rendre les metriques de persistence non ambigues entre user turn, summary, reponse finale assistant et interruptions.

Besoin couvert: l'audit du tour complet a montre que `persist_response` existe mais reste trop pauvre pour des agregats fiables de persistence par phase.

Fichiers probablement touches:

- `app/observability/chat_turn_logger.py`
- `app/core/chat_service.py`
- `app/server.py`
- `app/docs/states/specs/log-module-contract.md`
- tests `tests.test_server_chat_compact_observability_contract`, `tests.test_server_logs_phase3`, tests streaming/JSON concernes.

Hors-scope:

- changer le stockage conversationnel;
- modifier le protocole streaming;
- backfiller les logs historiques;
- renommer `persist_response` si un champ compact suffit.

Cases de correction:

- [x] Ajouter ou documenter un champ compact `persist_phase` sur `persist_response`.
- [x] Stabiliser le vocabulaire minimal, par exemple `user_turn`, `summary`, `assistant_final`, `assistant_interrupted`, ou noms locaux plus exacts.
- [x] Verifier que JSON et streaming emettent une phase exploitable pour la sauvegarde assistant finale.
- [x] Documenter dans `log-module-contract.md` la difference entre persistence canonique et ecritures derivees.

Tests attendus:

- [x] Test JSON: `persist_response.persist_phase=assistant_final` quand la reponse finale est sauvegardee.
- [x] Test streaming: meme contrat ou divergence explicitement documentee.
- [x] Test interruption si le chemin existe: phase distincte ou raison compacte.

Preuves runtime attendues:

- [x] Lecture compacte de tours recents montrant des phases distinctes sans contenu brut.

Condition de cloture:

- [x] Un operateur peut compter les sauvegardes finales assistant sans les confondre avec user turn, summary ou interruption.

## Lot 2 - Segmenter les metriques llm_call

Objectif: empecher les futures courbes de melanger le LLM principal et les providers secondaires.

Besoin couvert: `llm_call` et les events prompt-prepared secondaires doivent etre agregeables par caller sans confusion.

Fichiers probablement touches:

- `app/observability/chat_turn_logger.py`
- `app/observability/log_store.py`
- services admin/log si une lecture agregee est creee;
- `app/docs/states/specs/log-module-contract.md`.

Hors-scope:

- ajouter un nouvel event provider si les champs existants suffisent;
- changer les providers, models ou prompts;
- segmenter tout le dashboard dans ce lot.

Cases de correction:

- [ ] Formaliser que toute metrique LLM est groupee par `provider_caller`.
- [ ] Verifier les valeurs attendues: `llm`, `stimmung_agent`, `validation_agent`, `web_reformulation`.
- [ ] Distinguer explicitement payload principal et payload secondaire dans les lectures agregees.
- [ ] Ajouter un test ou une lecture agregee qui prouve que `llm_call[llm]` ne capture pas les providers secondaires.

Tests attendus:

- [ ] Test d'agregation sur plusieurs events avec callers distincts.
- [ ] Test de non-regression des payloads compacts `stimmung_prompt_prepared`, `validation_prompt_prepared`, `web_reformulation_prompt_prepared`.

Preuves runtime attendues:

- [ ] Counts par `provider_caller`, avec presence du principal et absence de fusion avec les secondaires.

Condition de cloture:

- [ ] Les futures courbes de latence, erreur et tokens peuvent etre filtrees par caller sans ambiguite.

## Lot 3 - Barriere post-save canonique JSON/streaming

Objectif: clarifier ou aligner l'ordre des ecritures derivees apres sauvegarde assistant.

Besoin couvert: traces memoire, identity writes et autres derivations doivent etre reliees a une reponse assistant canonique deja sauvegardee, ou documenter explicitement leur difference JSON/streaming.

Fichiers probablement touches:

- `app/core/chat_service.py`
- `app/core/chat_memory_flow.py`
- `app/memory/memory_store.py`
- `app/docs/states/specs/log-module-contract.md`
- tests chat JSON/streaming et logs.

Hors-scope:

- refactor global du tour chat;
- changer la doctrine Memory ou Identity;
- modifier le contenu injecte au prompt;
- reorganiser toute la persistence conversationnelle.

Cases de correction:

- [ ] Cartographier l'ordre effectif JSON et streaming autour de save assistant, traces, identity writes et summaries.
- [ ] Choisir: alignement runtime minimal ou documentation/test explicite de la divergence.
- [ ] Si champ ajoute, garder une preuve compacte de type `after_assistant_save=true` ou `post_save_phase`.
- [ ] Ne pas dupliquer les events existants si `persist_phase` du Lot 1 suffit.

Tests attendus:

- [ ] Test JSON: ecritures derivees apres sauvegarde assistant canonique, ou divergence explicite.
- [ ] Test streaming: meme preuve ou divergence documentee.
- [ ] Test qu'aucun contenu brut n'est ajoute aux logs de phase.

Preuves runtime attendues:

- [ ] Timeline compacte d'un tour montrant l'ordre des stages concernes.

Condition de cloture:

- [ ] Les metriques futures savent si une trace/identity write appartient a une reponse assistant effectivement sauvegardee.

## Lot 4 - Score de completude d'observabilite par tour

Objectif: preparer un indicateur operateur par tour sans inventer de logs nouveaux si les logs actuels suffisent.

Besoin couvert: un dashboard industriel aura besoin de savoir si un tour est observable de bout en bout, pas seulement s'il a repondu.

Fichiers probablement touches:

- `app/observability/log_store.py`
- service admin/log ou service dedie de lecture compacte;
- tests logs/admin;
- `app/docs/states/specs/log-module-contract.md`.

Hors-scope:

- scoring produit de qualite de reponse;
- lecture de contenu brut;
- dashboard UI final;
- backfill historique.

Cases de correction:

- [ ] Definir un funnel attendu: `turn_start -> prompt_prepared -> llm_call[llm] -> persist_response[assistant_final] -> turn_end`.
- [ ] Integrer les empreintes Identity, Memory et Hermeneutic quand elles sont attendues.
- [ ] Integrer providers secondaires quand ils sont presents: stimmung, validation, web reformulation.
- [ ] Integrer statut web quand web est demande: requested, skipped, success, injected.
- [ ] Integrer `node_state` read/write quand le noeud hermeneutique tourne.
- [ ] Produire un resultat compact: score numerique ou checklist par tour.

Tests attendus:

- [ ] Tour complet nominal: score/checklist complet.
- [ ] Tour sans web: absence web marquee non applicable, pas comme erreur.
- [ ] Tour avec fallback/fail-open: score degrade avec `reason_code`.
- [ ] Tour legacy incomplet: score partiel sans exception.

Preuves runtime attendues:

- [ ] Lecture compacte d'un tour recent avec checklist, statuses et reasons, sans prompt ni messages.

Condition de cloture:

- [ ] Un operateur peut distinguer tour sain, tour partiellement observable et tour degrade sans ouvrir les contenus.

## Lot 5 - Preparation dashboard/courbes

Objectif: cadrer le futur dashboard industriel apres clarification des metriques de base.

Besoin couvert: definir les courbes utiles sans les ouvrir avant que les signaux Lots 1-4 soient fiables.

Fichiers probablement touches:

- services admin/log ou Memory Admin selon le point d'entree retenu;
- `app/web/` uniquement si une UI dashboard est vraiment ouverte;
- specs admin/log concernees.

Hors-scope:

- ouvrir ce lot avant fermeture Lots 1-4;
- redesign global de `/admin`, `/log`, `/memory-admin` ou `/hermeneutic-admin`;
- creer un nouvel entrepot de donnees;
- backfill massif.

Cases de correction:

- [ ] Proposer les courbes de latence par `provider_caller`.
- [ ] Proposer les taux fallback/fail-open par `reason_code`.
- [ ] Proposer les lanes prompt: trace memory, summaries, context hints, identity, hermeneutic block.
- [ ] Proposer le funnel RAG: retrieved, basketed, kept, injected.
- [ ] Proposer les metriques `node_state`: hit rate, invalid rate, write changed/unchanged.
- [ ] Proposer les metriques web: requested, skipped, successful, injected chars, `read_state`.
- [ ] Proposer les erreurs par stage.
- [ ] Choisir une surface sans dupliquer `/log`, Memory Admin et Hermeneutic Admin.

Tests attendus:

- [ ] Tests d'agregats avec fixtures compactes multi-stages.
- [ ] Tests de filtrage par periode, stage et provider/caller si expose.
- [ ] Tests de redaction: aucune courbe ou tooltip ne charge du contenu brut.

Preuves runtime attendues:

- [ ] Snapshot compact de metriques agregees sur une fenetre courte, sans contenu.

Condition de cloture:

- [ ] Les courbes proposees reposent uniquement sur signaux clarifies par Lots 1-4.

## 7. Condition de non-prolongation

Le chantier se ferme quand:

- [x] `persist_response` est non ambigu pour les metriques de persistence.
- [ ] Les metriques LLM sont segmentees par `provider_caller`.
- [ ] La barriere post-save JSON/streaming est testee ou documentee explicitement.
- [ ] Un score/checklist de completude par tour existe ou est specifiable sans logs nouveaux.
- [ ] Le dashboard/courbes futur est cadre avec des signaux fiables, sans implementation prematuree.

Ne pas prolonger ce TODO pour:

- refondre Identity, Memory/RAG ou le noeud hermeneutique;
- creer de nouveaux prompts ou providers;
- nettoyer tout l'historique;
- redesign complet des surfaces admin;
- absorber l'audit frontend/admin UI dedie;
- ajouter des metriques produit subjectives.

## 8. Matrice besoins -> lots

| Besoin / risque | Lot |
| --- | --- |
| `persist_response` trop ambigu pour compter une sauvegarde finale assistant | Lot 1 |
| Courbes LLM qui melangent principal et providers secondaires | Lot 2 |
| Ecritures derivees difficiles a relier a la sauvegarde assistant canonique | Lot 3 |
| Dashboard impossible a fiabiliser sans score/checklist par tour | Lot 4 |
| Courbes industrielles a cadrer sans inventer une deuxieme observabilite | Lot 5 |
| Risque de confondre metriques backend et observabilite frontend/admin UI | Hors-scope dedie |
| Risque privacy sur contenus bruts dans metriques ou tooltips | Tous les lots |

## 9. Notes de prudence

- [ ] Avant chaque lot, verifier si un event existant suffit.
- [ ] Avant toute nouvelle UI, verifier si `/log`, `/memory-admin` ou `/hermeneutic-admin` peut porter la lecture sans duplication.
- [ ] Toute aggregation doit etre content-free par defaut.
- [ ] Les logs historiques ne doivent pas etre reecrits sans decision separee.
- [ ] Un graphe joli mais base sur une semantique ambigue doit rester bloque.
- [ ] Ne pas traiter les bugs de rendu frontend/admin UI dans ce TODO.
