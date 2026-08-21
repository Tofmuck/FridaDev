# FridaDev - Consolidation Presence dialogique et Identity mutable

Statut: TODO actif; Lots 0 a 2 fermes; Lot 3 en cours; Lots 4 a 8 et Z non commences
Date d'ouverture: 2026-08-20
Type: consolidation runtime, tests, observabilite et documentation, sans extension fonctionnelle
Agent cible: GPT-5.6, raisonnement approfondi
Racine autoritative: `/opt/platform/fridadev`
Branche canonique attendue a l'ouverture: `main`

## 1. Finalite

Cette roadmap consolide deux structures existantes sans en perdre la finalite:

1. la **Presence dialogique validee**, qui permet a Frida de produire la
   reponse locale exacte `...` lorsqu'un geste de reception, de depot ou de
   cloture appelle une presence sans contenu propositionnel;
2. l'**Identity mutable reciproque**, qui permet au meme juge de lire cinq
   paires completes et d'admettre, pour `user` comme pour `llm`, une nouvelle
   proposition ontologique durable dans le canon mutable add-only.

Le chantier vise quatre gains:

- retablir la vivacite effective du juge mutable;
- retirer les ecritures et decisions Identity legacy sans autorite canonique,
  tout en conservant et specialisant l'extraction necessaire des context hints
  dialogiques;
- mesurer puis renforcer la qualite et la robustesse de la Presence;
- reduire les erreurs de transport, la latence et la duplication de prompt
  seulement apres preuve.

Ce chantier n'ajoute aucune nouvelle capacite produit.

## 2. Decision de plan

### Existe-t-il un meilleur plan, plus simple, plus sur et avec moins d'effets de bord ?

Oui. Le meilleur plan n'est pas de changer simultanement les modeles, les
prompts, l'architecture Identity et l'architecture hermeneutique.

L'ordre obligatoire est:

1. figer les preuves et le contrat d'observabilite;
2. debloquer la progression Identity;
3. specialiser le caller par tour en extracteur de contexte dialogique et
   retirer seulement ses ecritures Identity legacy devenues sans autorite;
4. construire l'evaluation specifique de la Presence;
5. mesurer l'utilite causale de Stimmung;
6. fiabiliser les sorties structurees des callers conserves;
7. simplifier les inputs et prompts a comportement constant;
8. borner la latence cumulee;
9. benchmarker les modeles sur le contrat reel;
10. mettre a jour les references courantes, dont le `README.md`, puis archiver.

Cette sequence evite qu'un changement de modele masque un bug architectural,
mais aussi de supprimer comme legacy un caller dont une sortie alimente encore
une capacite produit. Chaque caller doit etre specialise sur une responsabilite
distincte avant toute optimisation de modele ou de prompt.

## 3. Invariant transversal d'observabilite synchrone

Aucun micro-lot ne peut etre ferme si le comportement, le transport, le prompt,
le modele ou le statut actif a change mais que l'observabilite correspondante
reste ancienne.

L'observabilite n'est ni un lot final ni une dette acceptee pour plus tard.
Chaque micro-lot doit mettre a jour dans le meme commit, lorsque ces surfaces
existent:

- l'evenement backend et son schema compact;
- le read-model ou l'API admin qui projette cet etat;
- le rendu frontend `/identity`, `/hermeneutic-admin`, `/log` ou `/admin`;
- les etats `loading`, `empty`, `ok`, `degraded`, `error`, `legacy` ou
  `not_applicable` concernes;
- les tests backend, API, frontend et navigateur voisins;
- le contrat vivant et le catalogue des callers si leur verite change.

Une projection frontend ne doit jamais deduire un statut critique depuis du
texte libre ou l'absence fortuite d'un champ. Elle doit lire un statut et un
reason code backend autoritatifs.

Observabilite autorisee:

- presence/absence;
- nombres, tailles, durees et timestamps techniques;
- versions de schema ou de prompt;
- noms de stages, callers, slots et modeles;
- statuts, reason codes, error classes bornees et provenance technique;
- hash courts et empreintes content-free;
- decisions `retry`, `consume`, `quarantine`, `apply`, `no_change`, `fallback`
  ou `not_applicable`.

Observabilite interdite:

- dialogue brut, prompt complet ou proposition identitaire;
- contenu Memory, Summary, Capsule, document, note ou resultat Web;
- query, URL sensible, secret, credential, DSN ou traceback brut;
- nouvelle collecte de contenu sous pretexte de debug;
- duplication d'un event quand un champ compact ou un read-model suffit.

Les logs prives Identity/Memory deja intentionnellement disponibles a
l'operateur ne sont pas requalifies. Ce chantier n'en ajoute pas et ne les
exporte pas.

## 4. Etat de depart a revalider

Instantane content-free observe le 2026-08-20, a ne jamais reutiliser comme
preuve future sans revalidation:

- branche `main`;
- HEAD local/upstream `02efcff11773668de7baf8b40eba519cd47c6928`;
- divergence `0/0`;
- worktree propre;
- `platform-fridadev` healthy, restart `0`, OOM false;
- runtime Presence: `stimmung_agent` puis noeud primaire deterministe puis
  `validation_agent`;
- modele Stimmung primaire `google/gemini-3.1-flash-lite`, fallback
  `openai/gpt-5.4-nano`, timeout par tentative `10` secondes;
- modele Validation primaire `google/gemini-3.1-flash-lite`, fallback
  `openai/gpt-5.4-nano`, timeout par tentative `15` secondes;
- modele juge mutable `openai/gpt-5.2`, timeout `10` secondes;
- modele du caller par tour encore nomme `identity_extractor`,
  `openai/gpt-5.4-mini`, timeout `10` secondes;
- buffer Identity le plus recent: `5/5`, `buffer_frozen=true`, statut et
  raison `window_too_large`;
- trois tentatives identiques ont observe `window_chars=37339`,
  `payload_chars=45755`, `estimated_prompt_tokens=12668`, sans afficher le
  contenu;
- limites locales du juge: `32000` caracteres de fenetre et `12000` tokens
  estimes;
- le caller par tour est encore prompte et persiste comme extracteur Identity;
  ses `identity_evidence` recentes de type episodique/situation alimentent
  pourtant `get_recent_context_hints(...)`, puis le payload du modele principal;
- ce meme caller declenche aussi des ecritures legacy `identities` et conflits,
  alors que le canon mutable actif est ecrit automatiquement uniquement par
  `mutable_identity_judge_v2_add_only`;
- le benchmark Validation du 2026-05-19 contient 13 cas mais aucun cas tague
  `presence`; la Presence runtime date du 2026-07-23;
- Stimmung et Validation parsers lisent encore un JSON textuel sans
  `response_format=json_schema` strict dans leur transport actif;
- le juge mutable utilise deja le structured output strict et la validation
  metier locale.

Baseline tests historique au meme HEAD: `2665` tests hermetiques. Ce nombre est
un repere, pas une preuve future. Chaque lot doit relancer la decouverte et
expliquer exactement toute variation.

Si branche, HEAD attendu par le lot, upstream, worktree, runtime utile ou
baseline tests different, arreter avant edition et rapporter l'ecart. Ne jamais
requalifier silencieusement la baseline.

## 5. Sources a lire avant tout lot

Toujours lire integralement et dans cet ordre:

1. `/opt/platform/fridadev/AGENTS.md`;
2. cette roadmap;
3. `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`;
4. `app/docs/states/specs/mutable-identity-judge-contract.md`;
5. `app/docs/states/specs/identity-read-model-contract.md`;
6. `app/docs/states/specs/hermeneutic-node-validation-agent-contract.md`;
7. `app/docs/states/specs/hermeneutic-node-stimmung-input-contract.md`;
8. `app/docs/states/specs/response-arbiter-power-contract.md`;
9. `app/docs/states/specs/frida-v1-agentic-observability-contract.md`;
10. `app/docs/states/audits/fridadev-model-call-catalog-2026-05-17.md`.

Puis lire le code, les tests, les benchmarks et les surfaces admin nommes dans
le micro-lot. Les documents archives orientent; le code, les tests et le
runtime courant tranchent.

## 6. Regles d'execution pour GPT-5.6 approfondi

- Executer un seul micro-lot par `GO`.
- Ne jamais enchainer automatiquement vers le suivant.
- Avant toute edition, repondre a la question: `Existe-t-il un meilleur plan ?`
- Revalider le finding dans le HEAD courant; un finding de cette roadmap reste
  une hypothese jusqu'a preuve.
- Faire le changement minimal qui ferme le lot.
- Ne pas ajouter une abstraction generique pour un besoin futur.
- Ne pas changer de modele dans un lot de code ou de prompt non consacre au
  benchmark/cutover modele.
- Ne pas modifier la plateforme, les secrets, la DB operateur ou les donnees
  de conversation.
- Ne pas lancer de provider reel dans la suite hermetique.
- Un smoke provider borne exige le GO explicite du lot benchmark concerne.
- Tout fichier modifie dans le depot doit finir committe et pousse sur la
  branche canonique courante.
- Toute livraison live doit etre explicitement comprise dans le GO du lot et
  suivre la procedure courante sans modifier Docker/Caddy/Authelia.
- Pour un changement runtime livre live: preuve healthy, restart stable, OOM
  false, comportement cible, observabilite backend et rendu frontend coherent.
- Aucun contenu operateur brut ne doit apparaitre dans le retour.

Retour obligatoire de chaque micro-lot:

```text
PLAN
DECISION
BASELINE
FINDING
OBSERVABILITE BACKEND
OBSERVABILITE FRONTEND
PATCH
TESTS
AUTO-AUDIT
DOCS
RUNTIME
GIT
STATUS
RISKS
```

## 7. Definition globale de fermeture d'un micro-lot

Un micro-lot runtime n'est ferme que si:

- [ ] le bug ou la dette est reproduit avant patch;
- [ ] le changement comportemental est borne et documente;
- [ ] une mutation controlee prouve la sensibilite du test principal;
- [ ] aucun ancien chemin concurrent ne reste actif;
- [ ] le backend d'observabilite expose la nouvelle verite;
- [ ] les read-models/API existants exposent cette meme verite;
- [ ] les frontends existants la rendent sans heuristique stale;
- [ ] les tests frontend couvrent `ok`, absence/no-op et erreur utile;
- [ ] les contrats vivants sont a jour dans le meme commit;
- [ ] les tests cibles, voisins et la decouverte hermetique sont verts;
- [ ] `git diff --check` est vert;
- [ ] seuls les fichiers autorises par le lot sont touches;
- [ ] aucun temporaire, `__pycache__` ou `.pyc` n'est laisse;
- [ ] le diff utile a ete relu integralement;
- [ ] commit et push sont effectues;
- [ ] worktree propre, HEAD local = upstream = distant et divergence `0/0`;
- [ ] si livre live, le runtime et les surfaces operateur sont verifies apres
  deploiement.

## 8. Matrice des surfaces existantes a maintenir

### Identity

Backend/runtime:

- `app/core/chat_memory_flow.py`;
- `app/memory/memory_identity_periodic_agent.py`;
- `app/memory/memory_identity_staging.py`;
- `app/memory/mutable_identity_runtime.py`;
- `app/memory/mutable_identity_judge_v2.py`;
- `app/memory/mutable_identity_judge_common.py`;
- `app/memory/arbiter.py`.

Observabilite/read-model:

- `app/admin/admin_identity_read_model_service.py`;
- `app/admin/admin_identity_judge_activity_projection.py`;
- `app/admin/admin_identity_runtime_representations_service.py`;
- `app/admin/admin_hermeneutics_service.py`;
- `app/admin/admin_stage_latency_summary.py`;
- `app/observability/chat_turn_logger.py` et schemas voisins;
- `app/observability/turn_observability_checklist.py`;
- `app/observability/turn_pipeline_read_model.py`.

Frontend existant:

- `app/web/hermeneutic_admin/render_identity_read_model.js`;
- `app/web/identity/render_identity_runtime_representations.js`;
- `app/web/hermeneutic-admin.html`;
- `app/web/log/`;
- `app/web/admin_settings_catalog.js` si le statut d'un slot change.

### Presence, Stimmung et Validation

Backend/runtime:

- `app/core/stimmung_agent.py`;
- `app/core/hermeneutic_node/inputs/stimmung_input.py`;
- `app/core/hermeneutic_node/runtime/primary_node.py`;
- `app/core/hermeneutic_node/validation/`;
- `app/core/chat_agent_lane_orchestration.py`;
- `app/core/chat_service.py`.

Observabilite/read-model:

- `app/observability/hermeneutic_node_logger.py`;
- `app/observability/turn_observability_checklist.py`;
- `app/observability/turn_pipeline_read_model.py`;
- `app/observability/log_store.py`;
- `app/admin/admin_hermeneutics_service.py`;
- `app/admin/admin_stage_latency_summary.py`;
- `app/admin/runtime_settings_api_view.py`;
- `app/admin/runtime_settings_model_validation.py`.

Frontend existant:

- `app/web/hermeneutic_admin/render.js`;
- `app/web/hermeneutic-admin.html`;
- `app/web/log/log.js` et `app/web/log.html`;
- `app/web/admin_section_stimmung_agent_model.js`;
- `app/web/admin_section_validation_agent_model.js`;
- `app/web/admin.html` et `app/web/admin.js`.

Cette liste est un point de depart. Chaque lot doit suivre les appelants et ne
modifier que les surfaces reellement concernees.

# LOT 0 - Goldens et cartographie d'observabilite

Statut: ferme le 2026-08-20
Nature: tests/docs-only
Livraison live: interdite

## Objectif

Figer les comportements et les dettes avant toute modification runtime.

## Decision de plan appliquee

Oui, un plan plus simple et plus sur existait: reutiliser les preuves Lot 9
pour la frontiere assistant et les final locks, faire traverser aux nouvelles
preuves Identity le vrai staging SQL et le vrai wrapper periodique, puis
ajouter seulement les matrices et mutations absentes. Aucun algorithme de
staging n'est recopie dans le golden: l'adaptateur synthetique ne fait
qu'appliquer les parametres SQL calcules par `memory_identity_staging.py`.

Le HEAD de depart du Lot 0 est `211797c1638454278d90b26250510a03667478e9`,
issu du micro-lot documentaire autorise `docs: clarify baseline runner
adaptation`. La baseline initiale verifiee avant ce micro-lot restait
`c28eda9b63e6fa67835037bc07682b66591f1233`.

Le runner documentaire qui montait seulement `app/` etait mecaniquement trop
etroit: le test Web repo-level doit aussi lire `benchmark/`. Il produisait
artificiellement `2653` tests plus une erreur de chargement; le module non
charge contient 13 tests, soit `2653 + 13 - 1 = 2665`. Le depot complet monte
read-only dans `/workspace`, avec `-w /workspace/app`, `--network none`, rootfs
read-only et `/tmp` en tmpfs, a reproduit `2665`, zero echec, zero erreur,
zero skip et zero expected failure avant patch. Cette adaptation n'ouvre
aucune surface d'ecriture et n'affaiblit pas l'hermeticite.

## Inventaire des preuves avant patch

| Invariant | Couverture avant Lot 0 | Classement | Decision |
|---|---|---|---|
| seuil de cinq paires et absence de juge avant le seuil | `test_does_not_call_agent_before_five_pairs` | preuve exacte du wrapper, store synthetique | reutilisee |
| preservation sur `window_too_large` | `test_preserves_buffer_when_agent_skips_window_too_large` | preuve partielle: retour juge fake et store recopiant le gel | completee par vrai staging et vrai garde de taille |
| retry de la meme fenetre | `test_retry_reuses_exact_same_five_pair_window_after_failed_attempt` | preuve partielle: comparaison de contenu avec store local | completee par empreinte content-free et vrai staging |
| timeout, transport, contrat invalide et apply en echec | `test_identity_periodic_agent_phase1.py` | preuves separees, matrice incomplete | rassemblees sans affaiblir les tests existants |
| cardinalite post-save sur cinq tours | tests `chat_memory_flow` et `chat_llm_flow` | absence reelle du chemin complet sur cinq tours | ajoutee via `/api/chat -> chat_response -> save -> post-save` |
| Presence exacte, save unique, provenance, bypass provider | `test_chat_fixture_covers_persistence_error_and_provider_free_overrides` | preuve exacte Lot 9 | reutilisee et completee pour JSON non-stream |
| priorite Agenda/Biblio | `test_lot9b_final_lock_matrix_preserves_priority_and_bypasses_provider` | preuve exacte Agenda > Biblio et Agenda > Presence | completee pour Biblio > Presence et les trois locks |
| exclusion Identity d'une Presence marquee | `test_presence_projects_only_marked_assistant_out_of_identity_sources` | preuve exacte | reutilisee |
| Presence impossible depuis fail-open | tests Validation fail-open | preuve exacte du contrat, sensibilite transversale absente | completee par contrat -> override |
| question, demande, detresse, risque, hard guard, ambiguite materielle | prompt Validation et corpus dialogique | preuve partielle, contre-matrice incomplete | matrice content-free ajoutee |
| staging backend -> read-model -> frontend | route Identity et tests de source frontend | preuve partielle, aucun etat 5/5 gele rendu en navigateur | golden read-model et smoke navigateur ajoutes |
| sources Stimmung/Validation et verdict final | events et cockpit existants | contradiction de projection partielle | figee et documentee comme gap |

## Fichiers de preuve livres

- `app/tests/support/lot0_identity_goldens.py`: adaptateur SQL synthetique,
  contrats juge et validateurs de mutation;
- `app/tests/unit/golden/test_lot0_identity_goldens.py`: staging gele, matrice
  d'erreurs et cardinalite post-save;
- `app/tests/support/lot0_presence_countercases.json` et
  `app/tests/unit/golden/test_lot0_presence_countercases.py`: contre-cas et
  fail-open;
- `app/tests/unit/golden/test_lot0_observability_goldens.py`: projection
  Identity et pertes actuelles du cockpit;
- `app/tests/support/server_chat_pipeline.py` et
  `app/tests/unit/golden/test_lot9_golden_harness.py`: cinq tours reels,
  Presence JSON/stream et priorite Agenda > Biblio > Presence;
- `app/tests/integration/frontend_browser/test_frontend_browser_smoke.js`:
  rendu reel `5/5`, `gele=true`, `window_too_large`, refus d'un faux `ok`.

## Travail obligatoire

- [x] Reproduire hermetiquement le buffer `5/5` fige apres
  `window_too_large`.
- [x] Prouver qu'un sixieme tour ne remplace ni ne fait progresser la fenetre.
- [x] Prouver la repetition de la meme empreinte content-free.
- [x] Figer les comportements transitoires actuels: timeout, transport,
  schema invalide, applicateur en echec.
- [x] Prouver le nombre d'appels Identity sur cinq tours: cinq extracteurs
  legacy plus un juge mutable quand le seuil est atteint.
- [x] Figer la Presence valide: `answer/presence`, reponse exacte, un save,
  aucun modele principal et provenance conservee.
- [x] Figer les contre-cas: question, demande, detresse, risque, hard guard,
  ambiguite materielle, final lock Agenda/Biblio.
- [x] Inventorier pour chaque stage les events, API/read-model et rendus
  frontend actuels.
- [x] Produire une matrice `backend -> API -> frontend -> test` dans cette
  section lors de la cloture.

## Sensibilite obligatoire

Les goldens doivent echouer si:

- la fenetre gelee accepte silencieusement un sixieme tour;
- une empreinte differente est presentee comme le meme retry;
- l'extracteur legacy n'est pas appele alors que la baseline pretend mesurer
  le comportement pre-retrait;
- une Presence appelle le modele principal ou est sauvegardee deux fois;
- un statut backend critique disparait du read-model ou du rendu frontend.

Mutations controlees effectivement rejetees, sans patch temporaire du produit:

- ajout ou remplacement silencieux du sixieme tour;
- empreinte de retry differente declaree identique;
- timeout consommant la fenetre;
- `window_too_large` requalifie en `completed_no_change`;
- ecriture canonique sous echec;
- extracteur retire d'un des cinq tours ou juge appele avant/apres le seuil;
- appel modele principal sous Presence, double save ou provenance perdue
  (validateurs Lot 9 reutilises);
- Presence issue d'un fail-open;
- Biblio cede a Presence ou Agenda cede a Biblio;
- statut/reason/freeze retire du read-model;
- rendu `window_too_large` remplace par un faux `ok`.

## Fichiers probables

- `app/tests/unit/memory/test_identity_staging_lot2.py`;
- `app/tests/unit/memory/test_identity_periodic_agent_phase1.py`;
- `app/tests/unit/chat/test_chat_memory_flow_identity_mode_pipeline.py`;
- `app/tests/unit/chat/test_mutable_identity_judge_final_validation.py`;
- `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py`;
- `app/tests/unit/chat/test_dialogic_regime_corpus.py`;
- `app/tests/unit/golden/test_lot9_golden_harness.py`;
- tests admin/frontend existants.

## Observabilite a prouver sans la changer

- statut/reason du staging;
- taille de fenetre, taille payload et estimation tokens;
- gel du buffer et horodatage du dernier run;
- callers Identity actifs;
- source primaire/fallback de Stimmung et Validation;
- verdict final, fail-open et Presence retenue/refusee;
- coherence entre API et frontend.

## Matrice backend -> API/read-model -> frontend -> test

| Stage | Evenement backend | Champs compacts autoritatifs | API/read-model | Frontend | Test exact | Gap |
|---|---|---|---|---|---|---|
| Identity staging | `mutable_identity_judge` emis par le wrapper | `status`, `reason_code`, `buffer_pairs_count`, `buffer_target_pairs`, `buffer_frozen`, `buffer_cleared`, tailles et timestamp d'event | `/api/admin/identity/read-model`: `identity_staging.current_buffer` et `latest_agent_activity` | renderer partage `/identity` et `/hermeneutic-admin` | `test_frozen_identity_event_projects_authoritative_status_reason_size_and_freeze`; smoke navigateur | aucune empreinte de retry n'est emise; le golden la calcule localement |
| Identity judge | `mutable_identity_judge` | `judge_status`, `judge_reason_code`, `verdict_count(s)`, sujets et reason codes compacts | bloc runtime juge + latest activity du read-model Identity | detail Identity et diagnostic generique de tour | `test_identity_error_matrix_preserves_or_consumes_window_and_canon_exactly`; route read-model phase 2 | pas de panneau de tour dedie au juge |
| Identity apply | champs embarques dans `mutable_identity_judge` | `apply_status`, `apply_reason_code`, `writes_applied`, compteurs et outcomes minimises | `latest_agent_activity` conserve ces champs | detail complet du renderer Identity | matrice d'erreurs Lot 0 + projection phase 2 | contradiction: `active_log_stages` annonce `mutable_identity_judge_apply`, mais aucun emitter actif autonome n'existe |
| Identity extractor legacy | `stage_latency` + event admin `identity_mode_apply` | caller, duree, action, extracted/filtered counts, statut staging | dashboard hermeneutique agrege + catalogue settings/read-model runtime | `/hermeneutic-admin`, `/log`, `/admin` settings | `test_five_saved_assistant_turns_call_legacy_extractor_five_times_and_judge_once`; server hermeneutics phase 4 | pas d'event chat par tour nomme `identity_extractor`; trace surtout agregee/latence |
| Stimmung prompt | `stimmung_prompt_prepared` | caller, modele, source de tentative, sampling, tailles de messages/fenetre | checklist et `turn_pipeline.providers.secondary.stimmung` | diagnostic `/hermeneutic-admin`; filtre `/log`; settings `/admin` | tests Stimmung existants + `test_secondary_sources_final_verdict_and_fail_open_are_in_events_but_partly_lost_in_cockpit` | le cockpit perd `attempt_decision_source` |
| Stimmung result | `stimmung_agent` | status, modele, `decision_source`, reason, presence/tones/count/confidence | checklist + provider secondaire | renderer generique de stage | meme golden observabilite + tests Stimmung | le cockpit ne projette pas `decision_source`; le detail d'event le garde |
| Validation prompt | `validation_prompt_prepared` | caller, modele, source de tentative, sampling, caps et hard-guard counts | checklist + provider secondaire Validation | diagnostic `/hermeneutic-admin`; filtre `/log`; settings `/admin` | tests Validation existants + golden observabilite Lot 0 | le cockpit perd `attempt_decision_source` |
| Validation result | `validation_agent` | status, modele, `decision_source`, posture/regime finaux, hard guards et reason | checklist + provider secondaire Validation | renderer generique de stage | `test_build_validated_output_accepts_positive_presence_as_answer_output_regime`; golden observabilite | le cockpit ne projette ni source finale ni verdict final |
| fail-open | `primary_node` (`fail_open`, fallback, reason/error class) et Validation `decision_source=fail_open` | booleens, source, reason, error class bornee | `turn_pipeline.hermeneutic.node_state` + `errors.fallback_count` | stages de tour et anomalies `/log` | tests fail-open Validation + `test_real_fail_open_contract_cannot_reach_presence_override_and_mutation_is_rejected` | aucun champ explicite ne relie un fail-open au refus de Presence |
| Presence retenue/refusee | `validation_agent`; puis `main_payload_manifest` si lock retenu | posture/regime, source finale `hermeneutic_presence`, bypass main, meta assistant | logs de tour et manifeste; pas de read-model Presence dedie | diagnostic generique de tour | goldens Lot 9, contre-matrice Lot 0, exclusion Identity marquee | refus de Presence et motif de suppression par un lock concurrent non projetes comme decision dediee |
| final lock concurrent | `main_payload_manifest` | source retenue, candidates, source supprimee, policy, main model called | event de tour seulement | visible via renderer generique si l'event est inspecte | `test_lot9b_final_lock_matrix_preserves_priority_and_bypasses_provider` | aucun panneau/read-model frontend de premier rang pour Agenda > Biblio > Presence |

## Commandes et resultats

- pre-patch, montage `app/` seul: `2653` + une erreur de chargement
  repo-level, diagnostic runner;
- pre-patch, depot complet read-only: `2665`, OK;
- goldens Identity/Presence/observabilite et Lot 9 cibles: OK;
- smoke Chromium hermetique: 13 tests, OK, apres montage read-only du cache
  Playwright 1.59.1; l'image Playwright 1.54 seule a d'abord prouve une
  incompatibilite mecanique de version, pas une regression frontend;
- suites voisines chat, streaming, persistance, admin/frontend: OK;
- decouverte finale depot complet read-only: `2672`, zero echec, zero erreur,
  zero skip, zero expected failure, soit exactement 7 nouveaux tests Python.

## Limites et contradictions restantes

- la vivacite n'est volontairement pas corrigee: la fenetre 5/5 reste gelee,
  le sixieme tour est ignore et le retry rejoue la meme fenetre;
- aucune empreinte runtime content-free de fenetre/retry n'est emise;
- le stage apply autonome annonce dans le read-model n'existe pas dans le
  chemin actif; les champs apply restent embarques dans le stage juge;
- les events Stimmung/Validation gardent leurs sources primaire/fallback et
  le verdict final, mais le cockpit agrege les perd;
- Presence retenue ou refusee et la suppression par un final lock n'ont pas
  de projection operateur dediee;
- les contre-cas Presence fixent le corpus attendu et les frontieres
  fail-open/hard-guard; ils ne transforment pas le modele en classifieur
  deterministe.

## Condition de fermeture

- [x] Aucun runtime, prompt, modele ou setting modifie.
- [x] Goldens sensibles livres.
- [x] Matrice d'observabilite complete.
- [x] Baseline hermetique finale verte.

Confirmation: aucun fichier sous `app/core/`, `app/memory/`, `app/identity/`,
`app/observability/`, `app/admin/` ou `app/web/` produit n'a ete modifie.
Aucun prompt, modele, provider, setting, secret, schema de DB ou contenu
operateur n'a ete lu ou ecrit. Aucun rebuild, restart ni deploiement n'a ete
effectue. Les Lots 1 a 8 et Z restent integralement non commences.

# LOT 1 - Retablir la vivacite du juge Identity

Statut: ferme le 2026-08-20
Nature: correctif runtime borne
Dependance: Lot 0 ferme

## Objectif

Garantir qu'une fenetre impossible ou irreparablement invalide ne bloque jamais
toutes les fenetres futures, sans tronquer ni preselectionner le dialogue.

## Decision avant patch

Oui, un plan plus simple et plus sur existait: conserver la ligne persistante
de staging, limiter la politique a deux tentatives, terminer sans ecriture les
inputs irreductibles et remplacer atomiquement l'ancienne fenetre par la paire
courante. Aucun compteur global en memoire, table, migration, queue, job ou
nouveau stage autonome n'etait necessaire.

Mesures historiques content-free disponibles avant patch: 189 events juge,
maximum `window_chars=37339`, `payload_chars=45755` et
`estimated_prompt_tokens=12668`; anciennes gardes `32000` caracteres et `12000`
tokens estimes. La fiche modele officielle OpenAI courante donne pour GPT-5.2
une fenetre contextuelle de 400000 tokens et 128000 tokens de sortie. Les gardes
passent donc au plus petit palier rond couvrant les maxima observes:
`40000` caracteres et `16000` tokens estimes. La marge contextuelle reste tres
large et aucune troncature n'est introduite.

## Findings revalides

- F1 valide: `window_too_large` preservait indefiniment le meme buffer 5/5;
  chaque nouveau tour relancait le juge et sa paire n'etait pas stagiee.
- F2 nuance: timeout, transport, contrat invalide et echec d'ecriture etaient
  tous preserves sans borne explicite; `window_too_large` etait refuse avant
  provider mais preservait lui aussi la fenetre.
- F3 valide: un simple clear aurait retabli la progression mais perdu la paire
  courante et rendu ambigu un commit canonique suivi d'un echec de finalisation.
- F4 valide: le gel et le reason code existaient, mais classe, action, tentative,
  empreinte et progression n'etaient projetes ni par l'API ni par les frontends.

## Politique livree

| Classe | Premiere action | Action terminale | Ecriture canonique |
|---|---|---|---|
| `transient` | `retry_preserve` pour timeout, transport sans statut, HTTP 408/409/425/429, 5xx et `runtime_safety_violation` technique | seconde tentative puis `terminal_consume_without_write` | aucune sous echec |
| `deterministic_input` | `terminal_consume_without_write` immediate | fenetre consommee, paire courante promue | aucune |
| `deterministic_contract` | `retry_preserve` pour contrat/verdict/refus invalide et HTTP 4xx non recuperable | seconde tentative puis consommation sans ecriture | aucune sous echec |
| `write_recovery` | `apply_recovery` | verification idempotente, puis consommation sans faux succes si reprise epuisee | au plus une application prouvee |

La borne `attempt_limit=2` repose sur l'etat persistant existant. Une fenetre
complete mais seulement `buffering`, sans run enregistre, commence a la
tentative 1. `running` prouve seulement le claim atomique; seul
`judge_attempt_started` consomme une tentative. `retry_pending` et
`write_recovery_pending` prouvent une tentative anterieure;
`terminal_discard_failed` reprend uniquement le CAS de finalisation, sans juge.
Les transitions reussies ou terminales remplacent l'ancienne fenetre par zero
paire ou par la paire courante, exactement une fois, comme premiere paire
suivante.

## Travail obligatoire

- [x] Classer les echecs en `transient`, `deterministic_input`,
  `deterministic_contract` et `write_recovery` ou vocabulaire local equivalent.
- [x] Augmenter les gardes taille uniquement si les mesures le justifient.
- [x] Conserver exactement cinq paires completes; aucune troncature silencieuse.
- [x] Preserver la fenetre pour un echec transitoire selon une politique de
  retry bornee.
- [x] Ne jamais rejouer indefiniment un meme echec deterministe immutable.
- [x] Consommer ou mettre en quarantaine technique la fenetre terminale sans
  ecriture canonique, puis accepter les paires suivantes.
- [x] Garantir l'idempotence si le verdict est valide mais l'ecriture canonique
  echoue.
- [x] Ne jamais transformer un echec en `no_change` ou en succes canonique.
- [x] Ne modifier ni `add_only`, ni les sujets, ni la cadence nominale, ni le
  canon existant.

## Observabilite backend dans le meme commit

Exposer de maniere compacte:

- classe de l'echec;
- action prise: retry preserve, window consumed without write, quarantine,
  apply recovery;
- nombre de tentatives borne ou indicateur equivalent;
- empreinte courte de la fenetre;
- tailles et plafonds effectivement compares;
- progression vers la fenetre suivante;
- distinction `judge_not_called`, `judge_failed`, `write_failed`, `completed`.

Aucun contenu de fenetre, proposition ou canon ne doit etre journalise.

Livre dans l'event existant `mutable_identity_judge`, sa garde allowlistee et
ses projections: `failure_class`, `recovery_action`, `processing_state`,
`attempt_current`, `attempt_limit`, `window_fingerprint`,
`next_window_progress`, `next_buffer_pairs_count`,
`writes_previously_applied`, tailles et plafonds compares. L'empreinte est le
prefixe de 12 caracteres d'un SHA-256 stable et n'est jamais accompagnee du
contenu source.

## Observabilite frontend dans le meme commit

Les surfaces Identity existantes doivent rendre:

- buffer en attente, gelee pour retry, ecartee sans ecriture ou consommee;
- raison technique lisible;
- derniere action et progression;
- absence de faux statut healthy lorsque le pipeline est bloque;
- absence de faux statut error lorsque la fenetre terminale a ete proprement
  ecartee et que la progression a repris.

Ne pas creer un nouvel ecran si `/identity` ou `/hermeneutic-admin` suffit.

Les deux renderers existants lisent les champs backend autoritatifs. Ils
distinguent attente, retry gele, consommation terminale sans ecriture,
write-recovery et progression; une reprise apres commit ambigu rend
`ecriture_precedente=true` seulement depuis
`writes_previously_applied=true`. L'absence historique d'un champ ne devient
pas un faux `ok`.

## Tests obligatoires

- [x] fenetre nominale sous plafond;
- [x] fenetre actuellement representative au-dessus de l'ancien plafond;
- [x] fenetre irreductiblement trop grande;
- [x] sixieme puis dixieme tour apres echec terminal;
- [x] timeout transitoire puis succes;
- [x] schema invalide repete et borne;
- [x] echec ecriture puis reprise idempotente;
- [x] aucun save mutable sous echec;
- [x] API/read-model/frontend coherents pour chaque etat;
- [x] mutation: restaurer le gel infini fait echouer le golden.
- [x] commit canonique ambigu: aucun second jugement ni second audit pour un
  retry identique, different ou `no_change`;
- [x] crash apres append de la cinquieme paire et avant juge: reprise en
  tentative 1;
- [x] `runtime_safety_violation` technique preserve une fois, tandis que
  `window_too_large` reste terminal immediat;
- [x] `writes_previously_applied=true` projete et rendu par les deux surfaces
  apres reprise verifiee.

## Fichiers de preuve et tests

- goldens partages:
  `app/tests/support/lot1_identity_liveness_goldens.py` et extension des
  goldens Lot 0;
- preuve principale:
  `app/tests/unit/memory/test_identity_liveness_lot1.py` (21 tests);
- staging/wrapper/apply/judge: suites unitaires Identity existantes;
- read-model/API/frontend:
  `test_identity_read_model_lot2/3/4.py`, projections, contrats serveur,
  `test_frontend_identity_surface_phase6.py` et smoke navigateur;
- non-regression: 146 tests chat, 27 tests orchestration/Presence/final locks et
  Lot 9, 44 tests routes/persistance/observabilite chat, 19 tests streaming JS.

Commandes executees avec depot complet read-only, `--network none`, conteneur
read-only, `/tmp` tmpfs et `PYTHONDONTWRITEBYTECODE=1`:

- decouverte baseline: `python -m unittest discover` -> 2672 OK;
- reproduction rouge initiale:
  `python -m unittest tests.unit.memory.test_identity_liveness_lot1` -> les 9
  premieres preuves refusaient l'ancien contrat (1 failure, 8 errors);
- cible coeur: 70 tests OK, puis preuve Lot 1 seule: 13 tests OK;
- projection/API/garde/frontend statique: 64 puis 6 tests OK;
- navigateur cache Playwright 1.54, sans pull: 13 tests OK;
- suites chat et voisines ci-dessus: 146 + 27 + 44 tests Python et 19 tests JS
  OK;
- cloture initiale: `2685`, zero echec, zero erreur, zero skip, zero expected
  failure, soit exactement 13 nouveaux tests Python;
- baseline de la passe corrective: `2685` OK;
- reproductions rouges correctives: 16 tests coeur avec 5 failures attendues;
  smoke navigateur 14 tests avec 1 failure attendue;
- apres correctif: wrapper/applicateur/persistance 21 tests, suites Identity
  memory 81 tests plus 5 de persistance, read-model/API/frontend 35 tests;
- smoke Chromium: 14/14 avec image et cache existants montes read-only, sans
  installation, pull ni reseau; frontend unitaire: 135/135;
- non-regression: chat 146/146; orchestration, Presence, Stimmung, Validation et
  Lot 9: 78/78; goldens Lot 0: 7/7;
- decouverte complete corrective: `2688`, zero echec, zero erreur, zero skip,
  zero expected failure, soit exactement 3 nouveaux tests Python depuis
  `eaffe9a160dcaedb6179b232776b1a3baef6708d`.

Deux erreurs de scan intermediaires provenaient de fichiers AppleDouble
`._*.py` crees par le transfert macOS; ces temporaires non versionnes ont ete
supprimes. Deux anciennes fakes de staging ne portaient pas l'argument atomique
`next_pair`; elles ont ete mises au niveau sans affaiblir leurs assertions.

## Sensibilite et limites

Les validateurs rejettent: retour du gel infini, consommation au premier
timeout, retry non borne, empreinte changee presentee comme identique, paire
courante perdue ou dupliquee, echec terminal renomme `no_change`, double batch
canonique ou double audit, disparition classe/action/empreinte, read-model
stale et frontend affichant `completed` pendant un blocage. La passe corrective
rejette aussi: second jugement apres commit ambigu pour des verdicts identique,
different ou `no_change`; tentative 2 fabriquee par un append sans run;
consommation immediate d'une panne technique `runtime_safety_violation`; champ
`writes_previously_applied` faux ou absent dans l'event, la projection ou les
deux renderers.

Limites restantes: l'extracteur legacy reste volontairement actif jusqu'au Lot
2. Si le store de staging reste indisponible, aucune progression durable ne
peut etre prouvee; le statut reste alors `write_recovery`/echec de finalisation,
jamais succes. Le staging operateur existant n'a pas ete modifie manuellement:
il adoptera la nouvelle politique lors d'un prochain tour normal.

### Passe corrective apres contre-audit du 2026-08-20

Les quatre defects reproduits sont valides. Le correctif n'utilise ni le
contenu mutable ni `source_trace_id` comme cle d'idempotence. Pour une fenetre
active, `memory_identity_mutables.apply_mutable_identity_subject_updates`
persiste dans une transaction unique les mutations canoniques, leurs audits et
le verrou `canonical_write_committed` avec reason
`canonical_write_recovery_pending:<empreinte-12>`. Si le commit est devenu
visible mais que son retour est incoherent, le wrapper reconnait ce verrou,
n'appelle plus ni juge ni applicateur et finalise le staging avec
`writes_previously_applied=true`.

Le comptage ne confond plus gel et tentative: `buffering` complet sans run vaut
tentative 1; seuls les statuts persistants de run ou de reprise font passer a la
tentative 2. `runtime_safety_violation` rejoint `transient`; seul
`window_too_large` reste `deterministic_input` terminal immediat.

Preuves ajoutees ou completees: applicateur et verrou transactionnel dans
`test_identity_mutables_phase1b.py`; wrapper/staging et mutations dans
`test_identity_liveness_lot1.py`; projection backend via
`latest_agent_activity`; rendu et mutation des deux surfaces dans
`test_frontend_browser_smoke.js`. Aucun schema, migration, table, queue, prompt,
modele, provider, extracteur legacy ou nouveau stage n'a ete ajoute.

### Passe corrective concurrence/CAS du 2026-08-20

Le contre-audit concurrent est valide. Le marqueur `running` inconditionnel ne
constituait pas un verrou: deux wrappers pouvaient juger la meme empreinte et
les clears ne comparaient ni la fenetre ni l'owner. Le correctif utilise sans
migration un verrou consultatif PostgreSQL de session dont la cle 64 bits est
derivee de `conversation_id + window_fingerprint`. Il reste tenu pendant juge,
application et finalisation; une fermeture de connexion apres crash le libere.

Sous ce verrou, `running` est acquis par CAS sur la liste JSON complete, le
statut et le reason precedents. Un owner aleatoire content-free est persiste
avec tentative et empreinte. `judge_attempt_started`, lui aussi CAS, est ecrit
juste avant l'appel juge: un crash entre claim et juge repart donc en tentative
1. Les retries restent strictement bornes a deux appels juge. Une reprise de
`terminal_discard_failed` appelle seulement le clear CAS et projette juge et
applicateur `not_called`.

Tous les marks, le fence transactionnel canonique et les clears comparent la
fenetre, le statut et l'owner/reason attendus. Un clear tardif est un no-op et
ne peut effacer la premiere paire suivante. Un caller concurrent attend le
holder puis reappend sa paire avec deduplication exacte; les interleavings
cinquieme/sixieme tour la conservent une fois. Le fence canonique perdant fait
rollback de toute ecriture et de tout audit, meme si son verdict `add` differe.

Fichiers runtime: `memory_identity_staging.py`,
`memory_identity_periodic_agent.py`, `mutable_identity_runtime.py`,
`mutable_identity_apply.py`, `memory_identity_mutables.py` et facade
`memory_store.py`. Preuves: staging SQL synthetique structure dans
`lot0_identity_goldens.py`, goldens/mutations dans
`lot1_identity_liveness_goldens.py` et
`test_identity_liveness_lot1.py`, fence transactionnel dans
`test_identity_mutables_phase1b.py`, read-model dans la preuve Lot 1 et rendu
des deux surfaces dans le smoke Chromium.

Reproduction rouge initiale de cette passe: cinq tests hermetiques, dont trois
failures et une erreur attendues; seul l'`add` alternatif valide passait deja le
validateur produit. Apres correctif: 21/21 preuves Lot 1 et 15/15 smoke
Chromium. La decouverte complete intermediaire puis finale compte `2693` tests,
zero echec, zero erreur, zero skip et zero expected failure: exactement cinq
nouveaux tests Python depuis `5844d0b19be3e6eaed0ad8bd31f7303441293b64`.

Mutations rejetees: deuxieme juge concurrent; second batch canonique ou audit;
`add` concurrent different accepte; sixieme paire absente ou dupliquee; mauvais
statut, mauvais owner/reason ou ancienne fenetre acceptes par un clear;
`running` compte comme tentative consommee; unique timeout terminal apres crash;
troisieme juge/provider depuis `terminal_discard_failed`; frontend rendant
`buffer_status=ok` pour `running`, `judge_attempt_started` ou
`terminal_discard_failed`. La preuve du clear tardif synchronise deux
finalisations par une barriere puis force le CAS gagnant avant le CAS tardif;
la sixieme et la septieme paire restent chacune presentes exactement une fois.

Aucun schema, migration, table, queue, route, prompt, modele, provider,
extracteur legacy, setting, contenu operateur ou Lot 2 a 8/Z n'a ete modifie.

### Reouverture corrective finale: identite de tour et deduplication bornee

Le finding bloquant est valide. `append_identity_staging_pair(...)` comparait
globalement les paires normalisees par role, contenu et timestamp. Deux tours
reels distincts portant les memes contenus et les memes timestamps a la
seconde etaient donc confondus: le second restait persiste dans la conversation
mais n'entrait pas dans le staging Identity.

Le chemin post-save transmet desormais le `turn_id` content-free deja produit
par `chat_turn_logger`. Le wrapper l'attache a la paire technique; le vrai
staging le persiste comme metadonnee de paire et deduplique uniquement une
reentree portant exactement le meme identifiant. L'egalite
role/contenu/timestamp n'est plus une identite globale. Deux tours reels
identiques restent deux paires; deux executions techniques du meme tour restent
une paire. Le normaliseur du juge ignore cette metadonnee avant construction du
payload: ni dialogue, ni prompt, ni contrat provider ne change.

La reproduction rouge traverse d'abord le vrai wrapper, puis
`run_chat_post_persistence_effects(...) -> record_identity_entries_for_mode(...)`
avec le vrai staging SQL synthetique: les deux preuves observaient 1 paire au
lieu de 2. La preuve concurrente complementaire bloque le cinquieme tour dans
le juge, fait attendre deux reentrees du meme sixieme tour sur l'ancienne
fenetre, puis verifie apres finalisation que le sixieme et le septieme tour
figurent chacun exactement une fois. Elle a passe cinq interleavings repetes.
Le golden de crash utilise maintenant le format runtime reel
`processing_claim:<attempt>:<fingerprint>:<owner>`.

Mutations rejetees: restauration de la deduplication globale (le second tour
reel disparait); suppression de la deduplication bornee (la paire transportee
apparait deux fois); second appel juge pendant la reentree; sixieme ou septieme
tour absent. Les preuves sont dans
`app/tests/unit/memory/test_identity_liveness_lot1.py` (24 tests) et
`app/tests/support/lot1_identity_liveness_goldens.py`.

Commandes hermetiques executees depuis la baseline `99b4e42a`:

- baseline: Python 2693/2693, JS 135/135, Chromium 15/15;
- reproduction rouge: 2 tests, 2 failures attendues (wrapper et post-save a
  1 paire au lieu de 2);
- preuve Lot 1: 24/24; interleaving carry-over repete cinq fois: 5/5;
- Identity memory: 88/88; staging, wrapper, Lot 0 et chat Identity voisins:
  67/67; API/read-model/frontend Python: 19/19;
- chat: 146/146; Presence, final locks, Lot 9 et transport: 27/27;
- frontend JS: 135/135;
- Chromium: un premier passage 14/15 a subi un SIGSEGV du binaire au lancement
  d'un sous-test, sans assertion produit; la meme invocation, sans changement
  ni installation, a ensuite passe 15/15;
- decouverte Python finale: 2696 tests, zero echec, zero erreur, zero skip et
  zero expected failure, soit exactement trois nouveaux tests justifies.

Une tentative intermediaire de transmettre une mapping au store a revele 30
erreurs de fakes historiques qui exigeaient a raison la sequence user/assistant
du contrat existant. La forme de paire a ete retablie avant la validation; les
fakes n'ont ete ni modifiees ni affaiblies.

Dette architecturale restante: `stage_identity_turn_pair(...)` demeure un
hotspot de 847 lignes (842 avant cette passe). Le correctif ajoute seulement le
passage explicite du marqueur aux trois reentrees et extrait sa construction
dans un helper cohesif. Aucun refactor general n'est engage dans ce lot.

Fichiers runtime modifies par cette passe finale:
`app/core/chat_memory_flow.py`,
`app/memory/memory_identity_periodic_agent.py` et
`app/memory/memory_identity_staging.py`. Le contrat vivant correspondant est
`app/docs/states/specs/mutable-identity-judge-contract.md`. Aucun schema,
migration, table, queue, route, prompt, modele, provider, extracteur legacy,
setting, contenu operateur ou Lot 2 a 8/Z n'a ete modifie.

## Condition de fermeture

- [x] Une fenetre impossible ne bloque plus les suivantes.
- [x] Aucune matiere dialogique n'est preselectionnee ou tronquee.
- [x] Aucun faux succes Identity.
- [x] Observabilite backend et frontend livree simultanement.

Confirmation: aucun prompt, modele, provider, setting, sujet, contrat add-only,
extracteur legacy, schema de DB ou contenu operateur n'a ete modifie. Aucun Lot
2 a 8 ou Z n'a ete commence.

# LOT 2 - Specialiser l'extracteur en contexte dialogique

Statut: ferme le 2026-08-20; implementation, preuves hermetiques,
observabilite backend/frontend, commit et livraison cibles par ce lot
Nature: consolidation runtime, prompt, persistance et observabilite a capacite
produit constante
Dependance: Lot 1 ferme et progression prouvee

## Decision architecturale explicite de Tof

Les context hints sont necessaires et doivent rester alimentes. Leur necessite
n'est pas une hypothese a benchmarker dans ce lot.

Un context hint n'est ni une information relative a l'utilisateur, ni une
information relative a Frida prise isolement. C'est un repere temporaire sur
l'etat du dialogue, produit par son histoire et destine a maintenir
l'intelligibilite du prochain tour. Les paroles de Tof et de Frida sont toutes
deux constitutives de cet etat: la reponse de Frida n'est pas un commentaire
auxiliaire utilise pour profiler l'utilisateur, mais un acte du dialogue.

Le contexte dialogique reste non canonique, borne et perissable. Il ne devient
ni un profil utilisateur, ni une identite de Frida, ni une antichambre
automatique du canon mutable.

## Cause du recadrage

La tentative d'ouverture du Lot 2 s'est arretee avant patch conformement a sa
stop-rule. L'inventaire a invalide sa premisse forte:

- `identity_evidence` n'est pas seulement historique;
- `get_recent_context_hints(...)` lit encore les evidences recentes
  episodiques ou de situation;
- `prepare_memory_context(...)`, `build_prompt_messages(...)` puis le payload
  principal consomment ces hints;
- supprimer le caller par tour aurait donc fait disparaitre progressivement
  une alimentation produit active a mesure que les evidences expiraient;
- `mutable_identity_judge_v2_add_only` reste bien l'unique writer automatique
  du canon mutable, tandis que les editions administrateur `set/clear` restent
  un writer manuel gouverne distinct.

L'arret n'a modifie aucun fichier, test, runtime, prompt, modele, provider,
schema ou donnee operateur. Le present recadrage remplace l'objectif invalide;
il ne commence pas son implementation.

La presente fermeture realise le recadrage sans supprimer l'alimentation des
context hints. Les faits historiques ci-dessus expliquent la decision qui a
precede l'implementation.

## Contradictions actuelles a revalider avant patch

- [x] Le caller actif est nomme et prompte comme `identity_extractor`, alors
  que sa sortie produit encore necessaire alimente les context hints.
- [x] `persist_identity_entries(...)` enregistre d'abord
  `identity_evidence`, puis appelle aussi `add_identity(...)`, les politiques
  legacy de defer et la detection de conflits.
- [x] `get_recent_context_hints(...)` selectionne actuellement
  `subject = user`, ce qui rabat le contexte dialogique sur un profil
  utilisateur.
- [x] Le rendu des hints distingue principalement `Utilisateur` et
  `Situation`, sans nommer leur sujet logique: le dialogue.
- [x] La politique temporelle de l'ancien extracteur ecarte des formulations
  relatives faibles parce qu'elles ne conviennent pas a une identite durable;
  cette regle ne peut pas etre transposee automatiquement a des hints
  temporaires, dates et soumis a expiration.
- [x] Les reglages, metriques, latences et surfaces admin presentent encore le
  caller comme extracteur Identity actif.

## Objectif

Specialiser le caller par tour existant en extracteur de contexte dialogique,
sans supprimer les context hints ni ajouter une nouvelle capacite produit.

Le chemin cible est:

```text
dialogue recent complet
  -> extraction de reperes contextuels dialogiques
  -> validation locale stricte
  -> persistance temporaire bornee
  -> selection par age, confiance, nombre et budget tokens
  -> injection dans le contexte du prochain tour
```

En parallele et sans autorite partagee:

```text
cinq paires de dialogue
  -> mutable_identity_judge_v2_add_only
  -> eventuelle ecriture du canon mutable durable
```

Le premier chemin maintient l'etat temporaire du dialogue. Le second gouverne
les propositions identitaires durables. Aucun ne doit produire les sorties de
l'autre.

## Inventaire avant patch

- [x] Cartographier le prompt, l'input, le schema de sortie, le validateur, le
  caller, le slot modele et les metriques de l'extracteur actuel.
- [x] Recenser tous les writers et readers de `identities`,
  `identity_evidence`, `identity_conflicts` et `identity_mutables`.
- [x] Distinguer les evidences historiques consultables, les nouvelles
  ecritures necessaires aux context hints et les ecritures Identity legacy a
  arreter.
- [x] Prouver que les context hints restent effectivement selectionnes,
  bornes et injectes dans le payload principal.
- [x] Cartographier les contrats JSON, streaming, erreur et final lock Presence
  du chemin post-save concerne.
- [x] Verifier si `identity_evidence` peut porter honnetement un sujet logique
  `dialogue` sans migration ni reecriture de donnees; sinon arreter avant toute
  modification de schema et rapporter la contradiction.
- [x] Recenser les labels API, read-model, frontend et documentation qui
  presentent encore le caller comme writer ou extracteur Identity.

## Contrat du contexte dialogique

Un hint admissible doit etre:

- [x] relatif a l'etat du dialogue, jamais a un profil individuel;
- [x] temporaire, date et soumis aux gardes d'age existantes;
- [x] fonde sur le dialogue effectivement observe;
- [x] utile a l'intelligibilite du prochain tour;
- [x] borne par confiance, nombre d'items et budget tokens;
- [x] non canonique et incapable de declencher une ecriture Identity;
- [x] compatible avec l'absence de hint lorsque le tour n'en justifie aucun.

Il peut notamment porter sur un enjeu en cours, une question ouverte, une
correction qui deplace le cadre commun, une distinction a ne pas perdre, une
tension argumentative non resolue ou la direction prise par le dialogue.

La paire dialogique complete constitue l'input. Une parole de Frida participe
a l'etat du dialogue, mais ne s'auto-autorise jamais comme proposition durable
sur Frida ou sur Tof.

## Travail obligatoire

- [x] Conserver un appel semantique par tour pour alimenter les context hints;
  ne pas le supprimer ni le remplacer par une regex.
- [x] Specialiser son prompt, son schema et son validateur sur le contexte
  dialogique uniquement.
- [x] Renommer conceptuellement le caller actif en
  `context_hint_extractor` ou vocabulaire local equivalent.
- [x] Conserver `openai/gpt-5.4-mini`, son timeout et ses parametres courants;
  aucun cutover modele dans ce lot.
- [x] Persister les nouvelles sorties uniquement dans la couche necessaire aux
  context hints.
- [x] Retirer du chemin actif `add_identity(...)`, la detection de conflits et
  les politiques Identity legacy associees aux sorties de ce caller.
- [x] Ne jamais utiliser `user` ou `llm` comme sujet logique des nouveaux
  context hints. Preferer la representation minimale honnete du `dialogue` si
  le schema existant la supporte sans migration.
- [x] Conserver en lecture les anciennes evidences `user` episodiques ou de
  situation pendant leur duree de vie normale, sans les requalifier ni les
  reecrire.
- [x] Requalifier la politique temporelle: une formulation trop relative pour
  l'identite durable n'est pas automatiquement invalide comme hint temporaire;
  elle doit rester datee, bornee et non canonique.
- [x] Conserver le staging cinq paires, le juge reciproque GPT-5.2, le contrat
  add-only et les edits administrateur gouvernes.
- [x] Prouver JSON, streaming, erreurs post-save et final lock Presence.
- [x] Ne creer ni table, migration, ecran, modele, provider ou pipeline
  substitutif sans arret et decision explicite.

Le slot technique historique `identity_extractor_model` peut rester comme cle
de compatibilite si son renommage imposerait une migration inutile. Les
surfaces doivent alors expliquer qu'il configure l'extracteur de contexte
dialogique, pas un writer Identity.

## Observabilite backend dans le meme commit

- exposer le caller actif comme extracteur de contexte dialogique;
- separer ses appels, latences, erreurs et statuts de ceux du juge mutable;
- ne plus compter ses sorties comme ecritures Identity;
- conserver les evenements et latences historiques legacy sans les melanger a
  l'activite courante;
- exposer presence/absence, nombre, age, budget, statut et reason codes bornes;
- ne journaliser aucun hint brut, dialogue, prompt ou proposition;
- ne pas emettre un faux event no-op pour remplacer une ecriture retiree.

## Observabilite frontend dans le meme commit

- rendre l'extracteur de contexte dialogique comme caller actif;
- ne plus le presenter comme writer Identity ou profil utilisateur;
- distinguer explicitement contexte dialogique temporaire, historique legacy
  et canon mutable durable;
- conserver la consultation historique sans la melanger aux compteurs actifs;
- remplacer les labels `Utilisateur` reducteurs lorsqu'ils decrivent en realite
  un hint dont le sujet est le dialogue;
- lire des champs backend autoritatifs, sans heuristique sur du texte libre;
- ne creer aucun nouvel ecran si les surfaces existantes suffisent.

## Tests obligatoires

- [x] une paire dialogique complete traverse le vrai chemin post-save;
- [x] un tour pertinent produit exactement un appel context-hint, et un no-op
  legitime ne produit aucune fausse ecriture;
- [x] une sortie valide est lue puis injectee dans le payload principal sous
  les plafonds existants;
- [x] aucune nouvelle entree `identities`, aucun conflit et aucun appel a
  `add_identity(...)` depuis ce caller;
- [x] les nouveaux hints ont pour sujet logique le dialogue, jamais `user` ou
  `llm`;
- [x] les evidences historiques compatibles restent lisibles jusqu'a leur
  expiration normale;
- [x] aucun changement du canon mutable avant le cinquieme tour;
- [x] un seul appel juge mutable au cinquieme tour;
- [x] absence de hint, timeout, transport et schema invalide restent fail-open
  pour la reponse sans devenir un faux succes d'extraction;
- [x] JSON, streaming, erreur et final lock Presence gardent leurs contrats;
- [x] API, read-model, frontend et navigateur distinguent temporaire, legacy et
  canonique;
- [x] le marqueur technique de persistance et le contrat interne n'atteignent
  ni le prompt principal ni l'observabilite content-free.

Cardinalite attendue sur cinq tours apres ce lot: cinq appels necessaires a
l'extracteur de contexte dialogique, zero ecriture Identity legacy depuis ce
caller et un appel au juge mutable au cinquieme tour. Il ne faut plus presenter
ces six appels comme six appels concurrents d'autorite Identity.

## Sensibilite obligatoire

Les goldens doivent rejeter au minimum:

- [x] la suppression de l'alimentation des context hints;
- [x] le retour d'un sujet logique `user` ou `llm` pour une nouvelle sortie;
- [x] une ecriture `identities`, un conflit ou un appel `add_identity(...)`;
- [x] une sortie temporaire promue dans le canon mutable;
- [x] un hint valide absent du payload principal;
- [x] la disparition prematuree de l'historique compatible;
- [x] un juge mutable appele avant la cinquieme paire;
- [x] un frontend presentant le caller comme writer Identity;
- [x] une mutation stream/non-stream ou Presence;
- [x] une fuite de hint, prompt ou dialogue brut dans event, snapshot ou diff.

Ne pas snapshotter le prompt complet. Figer sa version, sa structure de sortie,
son vocabulaire dialogique, ses reason codes et les rejets du validateur. Un
test hermetique ne prouve pas la qualite semantique live du modele; ne pas
pretendre avoir benchmarke cette qualite dans ce lot.

## Fermeture livree le 2026-08-20

Contradictions C1 a C6 validees. Le storage `identity_evidence.subject` est un
`TEXT` sans contrainte enum: `dialogue` est donc representable sans table,
migration ni reecriture. Le chemin actif est desormais:

```text
paire user/assistant complete
-> dialogic_context_hint_extractor (GPT-5.4 mini, timeout 10 s)
-> dialogic_context_hint_v1 strict, zero a quatre hints subject=dialogue
-> identity_evidence temporaire uniquement
-> lecture dialogue + ancien user compatible
-> gardes age/confiance/nombre/tokens
-> contexte du prochain tour
```

En parallele, le staging cinq paires et le juge GPT-5.2 add-only restent seuls
habilites a ecrire `identity_mutables`. Le caller contextuel n'appelle plus
`persist_identity_entries`, `record_identity_evidence`, `add_identity`, la
detection de conflits ou les politiques defer/promotion legacy. Les anciens
readers et tables restent consultables sans mutation.

Preuves principales:

- `app/tests/unit/memory/test_dialogic_context_hints_lot2.py`: prompt/schema,
  paire complete, temporalite relative temporaire, erreurs fail-open, writer,
  reader, injection et garde content-free;
- `app/tests/unit/golden/test_lot0_identity_goldens.py` et support: cardinalite
  cinq appels contextuels, zero writer legacy, zero juge avant seuil, un juge
  au cinquieme tour;
- tests post-save/content guards requalifies: aucun mode secondaire ne
  rebranche les writers legacy; Presence reste complete pour le contexte mais
  non substantive pour le juge mutable;
- tests API/read-model/settings et frontend admin: temporaire, legacy et canon
  sont des couches distinctes; `/identity` et `/hermeneutic-admin` lisent le
  bloc backend autoritatif;
- goldens Lots 0/1, chat, persistence, JSON/streaming, Presence/final locks,
  observabilite, Lot 9, JavaScript et Chromium conserves.

Reproduction rouge executee contre l'export read-only du commit baseline
`4ea53b49aaaf859d5aa8418228000628476d0325`: 7 tests, 2 echecs et 5 erreurs
attendus (caller/schema/writer `dialogue` absents, ancien label Utilisateur,
ancien reader `subject=user`). Sur le correctif, ces 7 tests puis la mutation
content-free passent.

Mutations rejetees: sujet `user` ou `llm`; cles `stability=durable` ou
`verdict=add`; disparition du caller/persister contextuel; rebranchement d'un
writer legacy; appel juge avant la cinquieme paire; absence du hint dans le
prompt; label frontend profilant; ajout de contenu brut dans l'evenement.

Commandes executees: baseline Python/JS/Chromium avec depot complet read-only;
reproduction rouge sur export du HEAD; suites ciblees prompt/schema/writer,
post-save, Lots 0/1, API/admin/frontend; decouverte Python complete; runner JS
et Chromium; `git diff --check` et controles de perimetre avant commit. Total
Python: 2696 avant, 2704 apres (8 tests nouveaux); JavaScript: 135; Chromium:
15. Aucun provider reel ni secret n'a ete utilise.

Limites: la cle/settings et le chemin de prompt conservent leur nom historique
`identity_extractor*` pour eviter une migration inutile; le shim direct
`extract_identities()` reste inactif pour compatibilite de tests/historique,
mais aucun caller produit ne l'invoque. La qualite semantique live de GPT-5.4
mini n'a pas ete benchmarkee dans ce lot. Aucun code Presence, Stimmung,
Validation, modele, provider, schema DB ou donnee operateur n'a change.

## Passe corrective observabilite du 2026-08-20

Le Lot 2 a ete rouvert puis referme sans changer son comportement dialogique.
F1 a F5 ont ete valides: le reader courant rendait `payload` mais la projection
lisait `payload_json`; le reason code d'un succes restait hors du payload; les
preuves API/frontend fabriquaient une activite deja correcte; des metadonnees
operateur racontaient encore une extraction Identity active; six tests aux noms
Web/Identity traversaient tous le meme helper sans exercer l'invariant annonce.

Correction livree:

- le seul event `dialogic_context_hint_extractor` porte localement son
  `reason_code` content-free pour `ok`, `not_selected` et `failed`, sans changer
  le writer generique;
- la projection lit exclusivement la forme autoritative `payload` de
  `read_chat_log_events` et expose statut, raison, `hint_count`,
  `persisted_count` et `prompt_kind`;
- un golden JSON content-free commun est produit/verifie par la chaine reelle
  stage -> writer -> reader -> projection, puis consomme par les deux surfaces
  Chromium; `/identity` et `/hermeneutic-admin` rendent aussi le nombre persiste
  et le `prompt_kind`;
- le slot technique `identity_extractor_model` reste compatible, mais les
  labels actifs le qualifient comme extracteur de contexte dialogique; le
  pipeline legacy est `legacy_inactive_historical` et sa provenance est
  `historical_persist_identity_entries`;
- les six doublons trompeurs de
  `test_chat_memory_flow_identity_content_guards.py` sont supprimes; trois tests
  voisins sont renommes selon l'invariant effectivement prouve. Les tests
  directs de `filter_unsupported_web_reading_identities()` restent intacts comme
  couverture de compatibilite historique.

Preuves et mutations rejetees: retour a `payload_json`; disparition du reason
code de succes; remise a zero de `hint_count` ou `persisted_count`; perte du
`prompt_kind`; fixture frontend non egale a la projection backend; retour d'un
label actif `identity extraction`, `identity writer` ou diagnostic legacy
execute. Aucun hint, dialogue, prompt, payload provider ou secret brut n'entre
dans l'event, le golden ou les projections.

Fichiers de preuve principaux:
`app/tests/unit/memory/test_dialogic_context_hints_lot2.py`,
`app/tests/fixtures/dialogic_context_observability_lot2.json`,
`app/tests/test_server_admin_identity_read_model_phase2.py`,
`app/tests/unit/admin/test_identity_governance_service_phase5.py`,
`app/tests/unit/runtime_settings/test_runtime_settings_readonly_info.py` et
`app/tests/integration/frontend_browser/test_frontend_browser_smoke.js`.

Commandes executees: baseline hermetique Python 2704, JavaScript 135 et Chromium
15; reproductions rouges F1/F2; suites ciblees stage/logger/log-store,
projection/read-model/routes/settings/governance/renderers; suites voisines Lots
0/1/2, post-save, chat, persistance, JSON/streaming, Presence, final locks et
observabilite; JavaScript et Chromium complets; decouverte Python hermetique
finale. Total final Python: 2701, soit trois preuves nouvelles et six doublons
faux supprimes; JavaScript: 135; Chromium: 15. Aucun skip ou expected failure.

Passe documentaire post-audit du 2026-08-20: les references actives qui
decrivaient encore l'ancien extracteur Identity ou `persist_identity_entries`
comme un pipeline execute ont ete alignees sur le runtime courant. Elles
distinguent maintenant le contexte dialogique temporaire, le juge mutable
canonique et l'historique legacy inactif. Controle docs-only: inventaire des
references et statuts, coherence avec les contrats vivants et le pipeline
courant, `git diff --check`; aucun test, rebuild, restart ou deploiement.

Limite conservee: les cles techniques et le chemin de prompt historiques
`identity_extractor*` ne sont pas renommes. Aucun prompt, modele, provider,
setting, stockage, donnee, cadence, budget ou comportement de context hints n'a
ete modifie. Les Lots 3 a 8 et Z restent non commences.

## Stop-rules

Arreter avant patch ou avant livraison si:

- representer honnetement le dialogue exige une nouvelle table, une migration
  ou une reecriture de donnees non explicitement autorisee;
- un consumer vivant exige encore les nouvelles ecritures `identities` ou
  conflits du caller par tour;
- le correctif supprime, affaiblit ou profile comme utilisateur les context
  hints;
- le lot change GPT-5.4 mini, GPT-5.2, Presence, Stimmung, Validation ou la
  cadence cinq paires;
- l'observabilite frontend et backend ne peut pas etre synchronisee dans le
  meme commit.

## Condition de fermeture

- [x] Les context hints restent une capacite active et alimentent le dialogue.
- [x] Leur sujet logique est le dialogue, pas un profil utilisateur ou Frida.
- [x] Le caller par tour n'ecrit plus aucune Identity legacy ni aucun conflit.
- [x] GPT-5.2 reste l'unique writer automatique du canon mutable.
- [x] Historique, JSON, streaming, erreurs et Presence sont preserves.
- [x] Observabilite active, historique et canonique est non ambigue.
- [x] Aucun nouveau modele, provider, table, migration, ecran ou capacite.

# LOT 3 - Corpus d'evaluation Presence

Statut: en cours - passes 1 et 2 livrees; baseline primaire/fallback documentee, seuil fallback non atteint
Nature: tests/benchmark/docs-only
Dependance: Lots Identity independants termines ou explicitement pauses
Livraison live: interdite

## Objectif

Mesurer la capacite exacte `answer/presence`, absente du benchmark qui a choisi
le modele Validation courant.

## Corpus minimal

Construire des fixtures synthetiques, sans conversation operateur, couvrant:

- depot recu;
- cloture partagee;
- silence explicitement autorise;
- question courte;
- demande directe ou implicite;
- detresse, risque ou vulnerabilite;
- instruction materielle;
- ambiguite substantielle;
- correction et desaccord;
- ironie;
- ponctuation ou fragments seuls;
- reponse assistant precedente qui change le sens du dernier tour;
- final lock Agenda et Biblio;
- hard guard Web;
- fail-open provider;
- contexte tronque ou support secondaire absent.

Chaque cas doit porter:

- ID opaque;
- famille semantique;
- verdict attendu ou ensemble borne acceptable;
- gravite d'un faux positif;
- justification humaine courte;
- tags de provenance synthetique;
- aucune sortie brute de modele conservee apres decision.

## Metriques

- faux `presence` sur cas interdit;
- Presence manquee sur cas positif;
- `clarify` ou `suspend` bureaucratique;
- schema/transport valide;
- latence primaire et fallback;
- cout estime;
- stabilite sur repetitions;
- difference avec/sans contexte recent.

## Observabilite a figer dans les tests

Le benchmark doit verifier le meme vocabulaire que le runtime:

- caller, modele demande et provider observe;
- source primaire/fallback;
- posture et regime finaux;
- hard guards appliques;
- Presence retenue/refusee et raison compacte;
- aucun contenu de fixture dans les artefacts content-free de decision.

## Passe 1 - corpus et scorer hermetiques (2026-08-21)

Decision de methode:

- aucun appel provider reel avant validation humaine du corpus;
- aucune regex ni heuristique lexicale pour decider Presence;
- le benchmark reutilise le constructeur de messages, les enums de sortie et
  les hard guards du runtime au lieu de maintenir une seconde doctrine;
- les final locks et le fail-open sont rejoues par les contrats runtime reels
  dans les tests, pas reimplementes dans le scorer;
- le corpus historique `answer/clarify/suspend` reste selectionnable separement.

Inventaire et gaps prouves avant patch:

- le benchmark historique de 13 cas ne couvrait aucun cas Presence;
- son adapter limitait encore `final_output_regime` a `simple|meta` et
  reconstruisait un ancien message de tache devenu divergent du runtime;
- son scorer ne mesurait ni faux Presence, ni Presence manquee, ni non-reponse
  bureaucratique et conservait la raison libre du modele;
- les fixtures partagees `dialogic_regime_corpus.json`, les contre-cas Lot 0,
  les hard guards Web, le fail-open et la priorite Agenda > Biblio > Presence
  existaient deja et ont ete reutilises au lieu d'etre recopies.

Preuves livrees dans cette passe:

- `benchmark/suites/validation_agent/fixtures/validation_agent_presence_cases.json`:
  24 cas semantiques proposes et 6 frontieres runtime, statut humain `pending`;
- `benchmark/suites/validation_agent/adapter.py`: selection de corpus et
  reutilisation des contrats runtime;
- `benchmark/suites/validation_agent/scorer.py`: faux Presence, Presence
  manquee, non-reponse bureaucratique, hard guards et sortie content-free;
- `benchmark/suites/validation_agent/campaign.py`: artefacts sans dialogue,
  justification de fixture, sortie provider brute, erreur brute ou raison libre;
- `app/tests/unit/golden/test_lot3_validation_agent_presence_corpus.py`:
  sensibilite semantique, contexte avec/sans, final locks, fail-open et
  mutations anti-fuite;
- `benchmark/README.md` et `benchmark/run_benchmark.py`: commande dry-run
  explicite `--validation-agent-corpus presence`.

Seuils proposes avant benchmark, encore soumis a validation humaine:

- zero faux Presence de gravite haute ou critique;
- zero Presence issue d'un hard guard ou d'un fail-open;
- zero violation de priorite des final locks;
- 100 % de schema valide;
- rappel Presence requis >= 80 % et stabilite de repetition >= 80 %;
- non-reponse bureaucratique <= 10 %.

Commandes executees hermetiquement dans cette passe:

- baseline Python: `2701/2701`;
- baseline frontend Node: `135/135`;
- baseline Chromium: `15/15`;
- reproduction rouge ciblee: echec attendu, corpus Presence absent;
- tests benchmark Presence + historique: `14/14`;
- suites voisines Validation, Presence, final locks, Lot 9 et observabilite:
  `96/96`;
- dry-run du runner Presence sous `--network none`, sans secret ni provider:
  artefacts temporaires ecrits uniquement sous `/tmp`; dry-run du corpus
  historique rejoue avec la meme frontiere;
- decouverte Python finale: `2709/2709`, soit exactement huit nouveaux tests
  decouvrables; frontend Node final: `135/135`; smoke Chromium final: `15/15`,
  sans installation, pull ni reseau.

Mutations controlees rejetees:

- question transformee en Presence;
- Presence requise remplacee par `simple`, `clarify` ou `suspend`;
- hard guard Web transforme en Presence;
- priorite Agenda/Biblio/Presence inversee;
- fail-open transforme en Presence;
- dialogue, raison libre ou sortie provider brute reinjectes dans l'artefact
  content-free.

Limites restantes apres la passe 1:

- Tof devait accepter, corriger ou rejeter les 24 etiquettes semantiques et les
  seuils proposes;
- aucun run primaire/fallback, cout, latence ou repetition provider n'avait
  encore ete execute;
- la baseline du modele courant n'etait donc pas documentee et le Lot 3 restait
  ouvert;
- la suite agregative historique non decouverte `test_model_benchmark` importe
  encore `memory_identity_periodic_apply`, deja absent au commit baseline; ce
  defaut preexistant, distinct du benchmark Validation `14/14`, n'est pas
  corrige dans cette passe;
- aucun runtime, prompt, modele, setting, read-model ou frontend produit n'a
  change; aucune livraison live n'est requise ni autorisee.

## Passe 2 - validation humaine et baseline primaire/fallback (2026-08-21)

Decision de methode:

- Tof a accepte sans modification les 24 etiquettes semantiques et les seuils
  proposes; le corpus porte le statut `validated`, la date, une base de
  validation bornee et l'empreinte semantique
  `646cc504d057021d870b16628b07c5ace83c711cbe36c489c1f0ec62049d2ed1`;
- toute modification des cas, frontieres runtime ou seuils invalide cette
  empreinte et interdit un nouveau run live tant qu'une validation humaine
  n'est pas recreee;
- la campagne compare exactement les roles runtime primaire
  `google/gemini-3.1-flash-lite` et fallback `openai/gpt-5.4-nano`, avec trois
  repetitions des 24 cas, soit 144 appels bornes, `temperature=0`, `top_p=1`,
  `max_tokens=140` et `timeout_s=15`;
- aucune regex ni heuristique lexicale n'a ete ajoutee: les verdicts restent
  produits par le modele et notes contre le contrat semantique valide;
- aucun endpoint chat, tour operateur, DB, secret persiste, setting runtime ou
  service produit n'a ete sollicite ou modifie; seule la cle runtime deja
  resolue dans le conteneur a servi au transport benchmark et n'a jamais ete
  affichee ou ecrite dans un artefact.

Instrumentation et observabilite benchmark:

- `benchmark/core/openrouter.py` conserve pour chaque appel les metadonnees
  bornees `generation_id`, modele observe et provider observe, sans payload ni
  sortie brute;
- le runner exige un role primaire et un role fallback explicites, refuse un
  corpus non valide, plus de trois repetitions ou plus de 144 appels;
- l'artefact distingue modele demande, role, modele/provider observes,
  repetition, latence, cout, statut schema, posture/regime et reason codes
  bornes; il rejette dialogue, justification humaine, sortie provider, raison
  libre, erreur brute et secret;
- la chaine d'observation est complete sur les 144 appels: le primaire a ete
  servi par `Google` ou `Google AI Studio`, le fallback par `OpenAI`;
- aucun read-model ou frontend produit n'est concerne: cette observabilite
  appartient exclusivement au workspace benchmark et reste synchronisee dans
  les tests et le rapport de la meme passe.

Resultats content-free:

- primaire: 72/72 schemas valides, 54/72 correspondances exactes, zero
  Presence manquee, rappel Presence 100 %, stabilite 100 %, zero faux Presence
  haute/critique et zero Presence issue d'un hard guard/fail-open; tous les
  seuils predeclares sont satisfaits;
- le primaire conserve toutefois trois faux Presence de gravite moyenne sur
  `P3-021` et six reponses trop permissives sur `P3-018`/`P3-022`; ces ecarts
  restent visibles meme s'ils ne violent pas les seuils acceptes;
- fallback: 72/72 schemas valides, 53/72 correspondances exactes, zero faux
  Presence, stabilite 91,67 %, mais 15 Presence manquees, soit les cinq cas
  Presence requis rates a chacune des trois repetitions; rappel Presence 0 %
  pour un minimum predeclare de 80 %;
- le fallback echoue donc le seuil `required_presence_rate`; les autres seuils
  sont satisfaits, mais `benchmark_decision_ready=false` et le Lot 3 reste
  ouvert;
- latence moyenne: 832,78 ms primaire et 1 151,05 ms fallback; cout estime:
  0,044796 USD et 0,03003101 USD, soit 0,07482701 USD au total;
- preuves durables:
  `benchmark/results/validation_agent/2026-08-21-lot3-presence-current-runtime.json`
  et `.md`, sans contenu de dialogue ou sortie provider brute.

Sensibilite et mutations controlees rejetees:

- alteration d'une etiquette, d'une frontiere ou d'un seuil apres validation;
- campagne live sur corpus `pending` ou sans roles primaire/fallback exacts;
- quatrieme repetition, depassement de 144 appels ou timeout rapporte different
  du timeout transport;
- disparition ou falsification du modele/provider observe;
- rapport affirmant a tort que le fallback n'a pas ete benchmarke;
- dialogue, justification, raison libre, sortie brute ou erreur brute ajoutee
  a l'artefact content-free.

Commandes et preuves de la passe 2:

- baseline avant patch: Python `2709/2709`, JavaScript `135/135`, Chromium
  `15/15`, zero echec, erreur, skip ou expected failure;
- reproduction rouge: validation humaine encore `pending`, instrumentation de
  roles/repetitions/route provider absente et rapport affirmant a tort ne pas
  benchmarker le fallback;
- tests benchmark Validation Presence et historique: 18 tests OK;
- suites voisines Validation, Presence, final locks et Lot 9: 75 tests OK;
- dry-run role-aware hermetique: 144 appels synthetiques, trois repetitions,
  corpus valide, aucun reseau ni secret;
- campagne provider: 144 completions exactement, puis regeneration du seul
  Markdown apres correction du rapport, sans nouvel appel provider;
- le controle recursif content-free et la recherche des contenus synthetiques
  de fixture dans les deux artefacts sont verts;
- decouverte Python finale: `2713/2713`, zero echec, erreur, skip ou expected
  failure, soit exactement quatre nouveaux tests depuis la baseline `2709`;
- frontend Node: `135/135`; smoke Chromium de reference: `15/15`; suite
  navigateur complete: `19/19`, sans reseau, installation ou pull.

Limite bloquante restante:

- le fallback runtime ne remplit pas la fonction Presence attendue. Le seuil
  ne sera ni abaisse ni requalifie silencieusement. La fermeture exige une
  decision distincte de Tof: accepter explicitement cette degradation bornee
  du fallback, ou autoriser un micro-lot separe de correction puis rejouer la
  meme campagne. Aucun de ces deux choix n'est infere dans cette passe.

## Condition de fermeture

- [x] Aucun changement runtime ou modele.
- [x] Corpus Presence valide humainement.
- [x] Baseline du modele courant documentee.
- [x] Seuils de securite explicites avant toute optimisation.
- [ ] Echec du seuil fallback resolu par correction prouvee ou accepte
  explicitement par Tof.

# LOT 4 - Ablation Stimmung et decision d'architecture

Statut: non commence
Nature: benchmark puis decision, sans cutover implicite
Dependance: Lot 3 ferme

## Objectif

Determiner si Stimmung ameliore effectivement la decision hermeneutique finale
et justifie un appel modele a chaque tour.

## Comparaison obligatoire

Rejouer le meme corpus:

- pipeline courant avec Stimmung;
- validation sans signal Stimmung;
- variante deterministe sans appel modele seulement si elle existe deja;
- primaire et fallback distingues.

Mesurer:

- precision Presence;
- faux silences;
- psychologisation ou surcodage affectif;
- `clarify/suspend` injustifies;
- latence et cout;
- impact reel de `stimmung_caution` sur le verdict final.

## Decision de sortie obligatoire

Choisir et documenter exactement une option:

1. `keep`: gain semantique net et reproductible;
2. `remove`: gain absent ou insuffisant face au cout/latence;
3. `inconclusive`: aucun changement runtime, nouveau corpus borne necessaire.

Interdits:

- remplacer Stimmung par des regex emotionnelles;
- garder le caller par intuition sans preuve;
- le retirer sur le seul critere de cout;
- fusionner silencieusement ses donnees avec Identity.

## Si decision `remove`

Ouvrir un micro-lot 4R separe avec GO explicite:

- retirer le caller et le stockage metier de nouveaux signaux s'ils ne servent
  plus;
- ne pas effacer retroactivement les metadonnees historiques;
- rendre le stage `not_applicable/retired`, pas `missing/error`;
- mettre a jour `/hermeneutic-admin`, `/log`, `/admin`, settings et docs;
- prouver l'identite du comportement hors differences acceptees par le corpus;
- mesurer la latence gagnee.

## Si decision `keep`

Le caller entre dans le Lot 5 structured output et conserve sa frontiere:
signal local, pas identite, pas diagnostic durable, pas souverainete finale.

## Condition de fermeture

- [ ] Decision humaine tracee.
- [ ] Aucun caller ajoute.
- [ ] Toute modification runtime eventuelle est un lot 4R distinct avec
  observabilite backend/frontend simultanee.

# LOT 5 - Structured outputs des callers conserves

Statut: non commence
Nature: robustesse transport
Dependance: decision Lot 4

## Objectif

Remplacer le JSON demande en texte libre par un schema provider strict pour
Validation et, si conserve, Stimmung, tout en gardant la validation metier
locale souveraine.

## Travail obligatoire

- [ ] Definir des schemas minimaux versionnes et sans champ libre inutile.
- [ ] Envoyer `response_format.type=json_schema` et `strict=true`.
- [ ] Exiger `provider.require_parameters=true`.
- [ ] Verifier les endpoints/provider reellement compatibles avant cutover.
- [ ] Conserver le parseur/fail-open de securite ou le remplacer par une
  validation locale equivalente, jamais par une confiance aveugle au provider.
- [ ] Distinguer erreur transport, schema provider et validation metier.
- [ ] Ne pas activer de plugin de healing ou autre intermediaire sans decision
  explicite et preuve d'utilite.

## Observabilite backend dans le meme commit

- version du contrat de sortie;
- `structured_output_requested`;
- `require_parameters` effectif;
- statut transport, schema provider et validation metier separes;
- modele/provider effectivement choisi;
- primaire/fallback;
- fail-open et raison bornees.

## Observabilite frontend dans le meme commit

- les cartes settings affichent le contrat actif et la compatibilite effective;
- `/hermeneutic-admin` distingue transport, schema et semantique;
- `/log` ne presente pas une erreur schema comme une decision hermeneutique;
- aucun JSON brut ou prompt n'est affiche.

## Tests obligatoires

- [ ] payload exact et `require_parameters`;
- [ ] schema valide;
- [ ] enum ou champ supplementaire refuse;
- [ ] provider incompatible;
- [ ] schema valide mais semantiquement interdit;
- [ ] fallback compatible;
- [ ] fail-open ne produit jamais Presence;
- [ ] frontend/API pour chaque classe d'echec;
- [ ] mutation: retrait du `response_format` fait echouer le test de transport.

## Condition de fermeture

- [ ] Zero confiance implicite dans le JSON libre.
- [ ] Validation metier locale conservee.
- [ ] Observabilite de bout en bout alignee.

# LOT 6 - Simplifier l'input et le prompt de Validation

Statut: non commence
Nature: refactor a comportement constant
Dependance: Lots 3 et 5 fermes

## Objectif

Reduire la duplication d'autorite et les previews JSON fragiles sans affaiblir
la lecture dialogique ni les garde-fous.

## Travail obligatoire

- [ ] Cartographier chaque instruction entre prompt systeme et message de
  tache technique.
- [ ] Identifier l'autorite contractuelle de chaque instruction.
- [ ] Garder la doctrine dans un prompt systeme versionne unique.
- [ ] Construire un `validation_input_v2` ou nom local equivalent, compact et
  type, depuis les champs contractuels deja disponibles.
- [ ] Conserver le dialogue recent comme matiere hermeneutique principale.
- [ ] Remplacer les troncatures aveugles par des projections bornees par champ.
- [ ] Conserver les hard guards deterministes et leur souverainete.
- [ ] Ne pas transformer question, detresse, ironie ou ambiguite en regex.
- [ ] Ne pas modifier la sortie exacte Presence.

## Observabilite backend dans le meme commit

- version de l'input et hash court du prompt;
- taille par bloc, compteurs de messages et flags de troncature;
- presence/absence des familles de source sans leur contenu;
- version des hard guards;
- decision finale et provenance inchangees.

## Observabilite frontend dans le meme commit

- cartes settings/read-only avec prompt et input versions actifs;
- taille et troncature visibles de maniere content-free si deja projetees;
- aucune ancienne version presentee comme active;
- historique explicitement versionne si conserve.

## Tests obligatoires

- [ ] corpus Presence integral avant/apres;
- [ ] corpus `answer/clarify/suspend` integral avant/apres;
- [ ] ordre et priorite du dialogue recent;
- [ ] bornes par champ;
- [ ] hard guards non affaiblis;
- [ ] prompt systeme unique et absence de duplication normative;
- [ ] mutation: reintroduire la doctrine concurrente dans le message technique
  fait echouer le test structurel.

## Condition de fermeture

- [ ] Aucun ecart comportemental non decide.
- [ ] Payload plus petit ou plus stable, mesure a l'appui.
- [ ] Observabilite versionnee simultanement.

# LOT 7 - Budget de latence et fallback borne

Statut: non commence
Nature: robustesse/performance
Dependance: callers finaux connus apres Lots 4-6

## Objectif

Empecher les timeouts primaire et fallback de s'additionner sans borne globale
avant l'appel du modele principal.

## Inventaire avant patch

- [ ] Mesurer les latences content-free p50/p95/p99 par caller et source.
- [ ] Distinguer timeout configure, duree reelle et temps total du stage.
- [ ] Verifier si les appels sont necessairement sequentiels.
- [ ] Ne pas introduire de concurrence si le gain n'est pas prouve ou si elle
  complique la causalite des logs.

## Travail obligatoire

- [ ] Definir une enveloppe murale par stage ou un mecanisme local equivalent.
- [ ] Donner au fallback seulement le budget restant.
- [ ] Conserver le fail-open et l'absence de Presence sur erreur.
- [ ] Ne pas raccourcir le timeout du juge Identity dans ce lot.
- [ ] Ne pas modifier les modeles.

## Observabilite backend dans le meme commit

- duree primaire, fallback et totale;
- budget initial, budget restant et cause de terminaison;
- nombre de tentatives;
- source retenue;
- distinction timeout stage et erreur provider.

## Observabilite frontend dans le meme commit

- `/hermeneutic-admin` et `/log` montrent la duree totale et la contribution du
  fallback sans addition trompeuse;
- `/admin` valide la coherence des timeouts avec l'enveloppe active;
- aucun statut degrade si le primaire reussit dans le budget.

## Tests obligatoires

- [ ] primaire rapide;
- [ ] primaire en echec puis fallback dans budget;
- [ ] primaire consomme presque tout le budget;
- [ ] aucun appel fallback quand budget epuise;
- [ ] fail-open terminal correct;
- [ ] horloge fake, aucun sleep reel;
- [ ] mutation: rendre les deux timeouts integralement cumulables fait echouer
  le test de budget.

## Condition de fermeture

- [ ] Borne murale prouvee.
- [ ] Aucune degradation du corpus.
- [ ] Read-model et frontend racontent la vraie chronologie.

# LOT 8 - Benchmark modele sur les contrats reels

Statut: non commence
Nature: benchmark et decision, cutover interdit dans le meme micro-lot
Dependance: architecture, schemas, prompts et budgets stabilises

## Objectif

Decider si les modeles actuels restent les meilleurs pour les roles reels de
Presence/Stimmung et Identity.

## Regles

- Utiliser des sources primaires recentes pour capacites, contexte, structured
  outputs, couts et parametres.
- Benchmarker le payload et le prompt effectivement livres, pas une simulation
  simplifiee.
- Utiliser uniquement des fixtures synthetiques structurees.
- Ne conserver aucun texte brut de sortie apres decision; garder hashes,
  tailles, scores, latences, couts et verdict humain.
- Ne pas choisir par reputation generale du modele.

## Presence/Validation

Comparer au minimum:

- modele primaire courant;
- fallback courant;
- un candidat leger actuel;
- un candidat plus robuste seulement si sa latence reste compatible.

Critere prioritaire: zero ou minimum de faux `presence` sur les cas interdits,
puis qualite globale `answer/clarify/suspend`, latence et cout.

## Identity

Comparer le juge courant a des candidats seulement apres reparation de la
vivacite et retrait du legacy.

Le corpus doit couvrir:

- auto-attribution durable;
- attribution reciproque correcte;
- negation et correction;
- citation, hypothese, roleplay et consigne locale;
- humeur transitoire;
- confusion de sujet;
- contradiction avec le canon existant;
- `no_change` prudent;
- longue fenetre proche du plafond;
- fausse addition, qui reste l'erreur la plus grave.

## Decision de sortie

Produire pour chaque caller:

- `keep_current`;
- `switch_candidate`;
- `inconclusive`.

Un `switch_candidate` ouvre un Lot 8C separe, avec GO explicite, validation
technique admin, rollback du setting, smoke synthetique borne, mise a jour des
read-models/frontend et preuve live. Aucun cutover dans le lot benchmark.

## Observabilite

La decision et, le cas echeant, le futur cutover doivent mettre a jour:

- catalogue des callers;
- chemin de l'artefact de benchmark dans les infos read-only;
- modele demande, provider observe et source du setting;
- frontend `/admin`;
- latences et erreurs apres cutover;
- rollback documente.

## Condition de fermeture

- [ ] Decision humaine explicite par caller.
- [ ] Aucun changement runtime dans le lot benchmark.
- [ ] Aucun modele change sans Lot 8C distinct.

# LOT Z - Contre-audit, documentation courante et README

Statut: non commence
Nature: cloture globale
Dependance: tous les lots obligatoires fermes; lots conditionnels decides

## Contre-audit obligatoire

Chercher activement:

- test qui recopie l'implementation;
- test vert malgre buffer Identity a nouveau bloque;
- retry infini masque par une limite de fixture;
- nouvelle troncature ou preselection identitaire;
- ancien extracteur encore actif par un autre appelant;
- historique legacy presente comme runtime courant;
- faux `presence`, Presence stateful ou Presence derivee d'un fail-open;
- hard guard affaibli;
- Stimmung conserve sans preuve ou retire sans corpus;
- structured output non exige chez le provider effectif;
- prompt duplique ou contrat concurrent;
- timeouts encore cumulables sans borne;
- frontend en retard sur le backend;
- API/read-model stale;
- collecte de contenu ou secret ajoutee;
- changement de capacite produit;
- vraie mutabilite revisionnelle commencee sans decision separee.

## Documentation a mettre a jour

Dans le meme lot de cloture:

- [ ] `README.md` racine pour decrire uniquement l'architecture effectivement
  livree;
- [ ] `app/docs/README.md`;
- [ ] `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`;
- [ ] `app/docs/states/specs/mutable-identity-judge-contract.md`;
- [ ] `app/docs/states/specs/identity-read-model-contract.md`;
- [ ] `app/docs/states/specs/hermeneutic-node-validation-agent-contract.md`;
- [ ] contrat Stimmung si le caller est conserve, ou note de retrait si retire;
- [ ] `app/docs/states/audits/fridadev-model-call-catalog-2026-05-17.md` ou
  son successeur vivant;
- [ ] contrats d'observabilite et surfaces admin concernees;
- [ ] cette roadmap avec commandes, commits, totals et limites reels.

Le README racine ne doit jamais annoncer une architecture cible non livree. Il
est mis a jour a la fin, a partir du code, des contrats et du runtime verifies.

## Preuves finales

- [ ] suites Identity;
- [ ] suites Presence/Stimmung/Validation;
- [ ] chat JSON et streaming;
- [ ] persistence et effets post-save;
- [ ] observabilite/log/read-model;
- [ ] API admin;
- [ ] frontend admin/hermeneutic/identity/log;
- [ ] golden Lot 9;
- [ ] decouverte hermetique complete;
- [ ] smoke live synthetique content-free si les lots runtime ont ete deployes;
- [ ] coherence `README.md` / pipeline / code / UI.

## Archivage

Quand toutes les cases obligatoires sont reellement fermees:

- deplacer ce fichier vers
  `app/docs/todo-done/refactors/fridadev-dialogic-presence-mutable-identity-consolidation-todo.md`;
- remplacer dans `app/docs/README.md` le lien actif par le lien archive;
- laisser visibles les decisions `keep`, `remove`, `inconclusive` et
  `keep_current` sans forcer artificiellement un changement;
- conserver les limites et risques residuels;
- commit, push, worktree propre et divergence `0/0`.

## Condition d'arret globale

Le chantier est termine lorsque:

- Identity progresse apres une fenetre terminale;
- l'extracteur legacy n'est plus un caller actif;
- Presence est evaluee sur son contrat reel;
- Stimmung a une decision fondee sur une ablation;
- les callers conserves utilisent un transport structure et observable;
- les prompts/inputs et la latence sont consolides sans perte semantique;
- les modeles ont une decision explicite, meme si elle consiste a conserver
  l'existant;
- backend, API, frontend, tests et docs racontent la meme architecture;
- le `README.md` racine decrit exactement l'etat livre;
- aucune extension fonctionnelle n'a ete ajoutee.

## Hors-scope absolu

- nouvelle feature produit, route publique, agent, outil ou integration;
- nouvelle UI ou dashboard si une surface existante suffit;
- remplacement de l'hermeneutique par des regex;
- modele principal du chat;
- semantique des final locks Agenda/Biblio/Presence;
- format exact de la reponse Presence;
- persistance d'un etat Presence entre les tours;
- promotion automatique mutable vers static;
- revision, suppression, merge ou supersession automatique du canon mutable;
- migration/destruction des tables historiques Identity;
- nouveau worker, queue ou infrastructure asynchrone sans decision distincte;
- DB operateur, secrets, Docker, Caddy, Authelia, reseaux ou plateforme;
- reset ou backfill massif de l'observabilite;
- contenu operateur dans fixtures, snapshots, artefacts ou retours.

Une vraie mutabilite revisionnelle `supersede/contest` avec provenance et
confirmation humaine peut etre pensee dans une decision produit separee. Elle
ne fait pas partie de cette consolidation.
