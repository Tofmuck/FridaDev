# FridaDev - Consolidation Presence dialogique et Identity mutable

Statut: TODO actif; Lots 0 a 3 fermes; Lot 4 actif, 4C.1 ferme apres cutover Validation Gemini 3.7 Flash medium et smoke live unique vert; 4S.0 et 4S.1 fermes, decision 4S.1 `strengthen`; 4C.2 ferme apres livraison du prompt renforce v2 qualifie `32/32` sur le primaire; 4C.3 non commence; observabilite causale complete non prouvee; Lots 5 a 8 et Z non commences
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

Statut: ferme - degradation Presence du fallback courant acceptee explicitement le 2026-08-21
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

## Passe 3 - criblage Luna/Terra et niveaux de raisonnement (2026-08-21)

Decision de methode:

- Tof a autorise explicitement l'evaluation de GPT-5.6 Luna et Terra, de leur
  cout et des niveaux de raisonnement `none`, `low` et `medium`;
- le corpus, le prompt, les attentes, les seuils, le timeout, la temperature et
  le `top_p` sont restes inchanges; aucune regex ou heuristique lexicale n'a
  ete ajoutee;
- le criblage initial a execute exactement 144 appels: 24 cas, deux modeles,
  trois niveaux, une repetition;
- le niveau demande est porte par le payload OpenRouter
  `reasoning.effort`, avec `exclude=true`; l'artefact conserve le niveau
  demande et les `reasoning_tokens` numeriques observes, jamais le contenu du
  raisonnement;
- le runner distingue maintenant un criblage sans faux roles runtime, incapable
  de fermer la decision, et une campagne finale `primary/fallback` a trois
  repetitions;
- la documentation officielle OpenAI du 2026-08-21 donne Luna a 0,20 USD/M
  tokens d'entree et 1,20 USD/M de sortie, Terra a 2 USD/M et 12 USD/M; le guide
  recommande de mesurer le niveau plutot que d'adopter automatiquement le plus
  eleve.

Criblage `max_tokens=140`:

- Luna `none`: 24/24 schemas, rappel Presence 100 %, mais trois faux Presence,
  dont deux haute gravite; cout estime 0,01305155 USD;
- Terra `none`: 24/24 schemas, rappel Presence 100 %, mais deux faux Presence,
  dont un haute gravite; cout estime 0,12752750 USD;
- Luna `low`: zero faux Presence sur cette repetition, mais seulement 19/24
  schemas, 1 182 tokens de raisonnement et des fins `length`;
- Luna `medium`: zero faux Presence sur cette repetition, mais seulement 17/24
  schemas, 1 751 tokens de raisonnement et des fins `length`;
- Terra `low` et `medium`: 24/24 schemas, mais respectivement trois et deux
  faux Presence, avec des cas haute gravite; aucun prolongement n'etait
  justifie;
- Terra a coute environ dix fois Luna sans gain de securite semantique sur ce
  corpus; cout total du criblage: 0,42588675 USD.

Validation des budgets et campagnes finales:

- Luna `low/max_tokens=300` a franchi les seuils sur une repetition, puis a
  echoue sur trois repetitions: 72/72 schemas, rappel Presence 100 %, stabilite
  83,33 %, cinq faux Presence et echec `critical_or_high_false_presence`;
- Luna `medium/max_tokens=500` a franchi les seuils sur une repetition, puis a
  echoue sur trois repetitions: 72/72 schemas, rappel Presence 100 %, stabilite
  75 %, trois faux Presence dont deux sur un cas haute gravite, echecs
  `critical_or_high_false_presence` et `repetition_stability`;
- le primaire Google, rejoue avec les plafonds communs 300 puis 500, reste a
  72/72 schemas, rappel Presence 100 %, stabilite 100 % et tous ses seuils
  predeclares satisfaits;
- `benchmark_decision_ready=false` dans les deux campagnes. Aucun resultat a
  une repetition n'a ete substitue a la preuve de stabilite obligatoire.

Preuves et sensibilite:

- `benchmark/results/validation_agent/2026-08-21-lot3-presence-gpt56-screening.json`
  et `.md` figent les six configurations, les routes, couts, latences, fins et
  tokens de raisonnement content-free;
- `benchmark/results/validation_agent/2026-08-21-lot3-presence-luna-low-max300.json`
  et `.md` figent la premiere campagne finale rejetee;
- `benchmark/results/validation_agent/2026-08-21-lot3-presence-luna-medium-max500.json`
  et `.md` figent la seconde campagne finale rejetee;
- les goldens rejettent la disparition du niveau demande, l'exposition du
  raisonnement, un criblage dote de faux roles, un criblage qui fermerait la
  decision, l'absence des tokens de raisonnement, une requalification de
  `benchmark_decision_ready` et la disparition des echecs haute gravite;
- les artefacts ont ete controles recursivement contre tout dialogue,
  justification humaine, sortie brute, raison libre, erreur brute ou secret.

Decision de sortie de la passe 3:

- ni Luna ni Terra ne remplace proprement le fallback runtime sous le contrat
  Presence valide;
- aucun changement de modele, niveau de raisonnement, plafond runtime, prompt,
  provider ou setting n'est autorise par ces resultats;
- le fallback actuel reste imparfait mais n'est pas remplace par un candidat
  qui introduirait des faux Presence haute gravite;
- a l'issue de la passe 3, le Lot 3 restait ouvert. Sa derniere case ne pouvait
  etre fermee que par une correction ulterieure prouvee ou par l'acceptation
  humaine explicite de la degradation deja documentee; cette acceptation a ete
  donnee le 2026-08-21 et aucun nouveau benchmark opportuniste n'a ete lance.

Commandes et preuves finales de la passe 3:

- baseline autoritative avant patch: Python `2713/2713`, JavaScript `135/135`
  et Chromium `19/19`;
- reproduction rouge runner/reasoning/screening: 21 tests, deux erreurs et un
  echec attendus avant implementation;
- preuves benchmark finales ciblees: `22/22`;
- suites voisines Validation, Presence, final locks, runtime settings et Lot 9:
  `101/101`;
- decouverte Python finale: `2716/2716`, zero echec, erreur, skip ou expected
  failure, soit trois nouveaux tests decouvrables; le quatrieme test ajoute au
  fichier benchmark historiquement hors decouverte passe dans la suite ciblee;
- frontend Node final: `135/135`; navigateur Chromium complet: `19/19`, sous
  reseau coupe, checkout et cache navigateur en lecture seule;
- cinq campagnes provider bornees: `504/504` appels sans erreur transport,
  cout total estime `0,55724594 USD`; les deux criblages intermediaires non
  decisifs sont documentes mais non versions en doublon;
- `git diff --check`, controle des fichiers, controle content-free recursif,
  recherche de temporaires et relecture integrale du diff executes avant
  commit.

## Decision humaine de fermeture (2026-08-21)

Decision explicite de Tof:

> J'accepte la degradation Presence du fallback actuel.

Portee architecturale de cette acceptation:

- le primaire `google/gemini-3.1-flash-lite` reste le chemin qui satisfait le
  contrat Presence valide;
- le fallback `openai/gpt-5.4-nano` est accepte comme chemin de continuite
  degradee, pas comme equivalent semantique du primaire;
- lorsque le primaire est indisponible, le fallback peut manquer une Presence
  legitime; cette degradation connue est preferee aux faux Presence haute
  gravite observes avec Luna et Terra;
- aucun seuil n'est abaisse, aucun echec de benchmark n'est requalifie et
  `benchmark_decision_ready=false` reste la description exacte des campagnes;
- aucun modele, prompt, provider, niveau de raisonnement, plafond, setting,
  code runtime ou service n'est modifie par cette fermeture;
- cette acceptation ne vaut ni approbation generale des degradations futures,
  ni autorisation de commencer le Lot 4.

## Condition de fermeture

- [x] Aucun changement runtime ou modele.
- [x] Corpus Presence valide humainement.
- [x] Baseline du modele courant documentee.
- [x] Seuils de securite explicites avant toute optimisation.
- [x] Echec du seuil fallback resolu par correction prouvee ou accepte
  explicitement par Tof.

# LOT 4 - Audit causal et consolidation de Stimmung

Statut: goldens techniques du coeur livres; 4C.1, 4S.0, 4S.1 et 4C.2 fermes; prompt Stimmung renforce v2 qualifie `32/32` sur le primaire puis livre; 4C.3 non commence; observabilite causale complete non prouvee
Nature: audit causal multi-tours, correctifs bornes, benchmark sous GO separe
et observabilite synchrone, sans extension fonctionnelle
Dependance: Lot 3 ferme

## Decision architecturale deja prise

Decision explicite de Tof du 28 aout 2026: Stimmung est une composante
constitutive de FridaDev et doit etre conservee. Le Lot 4 ne decide donc plus
si Stimmung existe. Il mesure comment elle agit reellement afin de la rendre
plus effective, plus robuste et plus inspectable sans en perdre la finalite.

Une comparaison avec et sans signal Stimmung reste obligatoire comme ablation
diagnostique. Elle n'est jamais une variante produit, une proposition de
retrait ou une autorisation de cutover.

## Finalite a preserver

Stimmung rend perceptible le mouvement affectif du dialogue dans la duree. Son
role n'est pas:

- de profiler Tof ou Frida;
- de fabriquer une Identity ou un diagnostic durable;
- de deduire la verite d'une proposition depuis son intensite affective;
- de forcer l'adoption d'une position;
- de remplacer l'interpretation dialogique par une classification emotionnelle
  locale au tour.

Elle doit pouvoir influer sur la maniere de comprendre et de formuler une
reponse, tout en restant une source locale, faillible, contestable et sans
souverainete finale.

## Question exacte du Lot 4

Prouver, sur des dialogues synthetiques multi-tours, a quels endroits le signal
Stimmung est effectivement produit, stabilise, transmis, utilise, perdu ou
surinterprete entre:

1. le caller par tour;
2. la persistance et la rehydratation du signal;
3. l'agregation multi-tours;
4. le regime epistemique primaire;
5. Validation;
6. la posture finale transmise au modele principal;
7. l'observabilite backend, les read-models et les deux surfaces frontend.

## Hypotheses a valider ou invalider, jamais a supposer

- F1: un affect stable peut etre classe et stabilise sans modifier le regime
  primaire, alors qu'une transition affective le modifie.
- F2: `stimmung_caution` peut rabattre un mouvement affectif sur une baisse de
  certitude epistemique au lieu d'agir d'abord sur l'enonciation.
- F3: le compactage borne de `canonical_inputs` peut faire disparaitre
  `stimmung_input` avant Validation selon la taille et l'ordre des sources.
- F4: le modele principal peut ne recevoir qu'une posture finale appauvrie,
  sans la structure Stimmung qui permettrait une formulation plus juste.
- F5: l'observabilite actuelle peut prouver l'execution des stages sans prouver
  que Stimmung a cause une difference dans le verdict ou la reponse finale.
- F6: le benchmark historique par tour peut etre insuffisant pour juger une
  structure qui mature sur plusieurs tours et se stabilise avec hysteresis.

Chaque finding doit finir `valide`, `invalide` ou `partiel`, avec le chemin de
preuve exact. Une lecture de code, une sortie terminal ou un test synthetique
qui contourne le coordinateur ne suffit pas a fermer le finding.

## Inventaire A a Z ferme le 2026-08-28

Le caller est execute une fois par tour accepte et son signal est attache au
dernier message utilisateur. Ce signal traverse la persistance JSONB des
messages et leur rehydratation chronologique; l'agregateur retient au maximum
quatre signaux valides. Un affect stable ne change pas le regime primaire,
tandis qu'une transition ou une volatilite peut le rendre plus prudent.

Le compactage borne de `canonical_inputs` peut ne transmettre a Validation
qu'une structure Stimmung partielle, ou l'evincer entierement. Le modele
principal ne recoit pas le signal ni l'agregat: il recoit seulement la posture,
le regime et les directives derives. L'observabilite actuelle prouve
l'execution des stages, mais ni la reception effective par Validation ni
l'effet causal final. Aucun golden transversal complet ne couvre encore ce
chemin.

Preuve executee pendant l'inventaire: `43` tests cibles, `43` reussites, `0`
echec et `0` erreur. Aucun test navigateur, provider reel ou DB operateur n'a
ete utilise; aucune decouverte complete n'a ete executee pendant l'inventaire.

Classement des findings apres inventaire:

- F1: `valide au niveau agregateur/regime primaire`; aucune difference sur le
  texte final n'est encore prouvee.
- F2: `valide comme description du raccord actuel`; son caractere
  architecturalement incorrect reste a decider depuis les goldens.
- F3: `valide`; une perte structurelle est possible avant Validation.
- F4: `partiel`; l'absence du signal detaille dans le payload principal est
  prouvee, mais son caractere dommageable reste a mesurer.
- F5: `valide`; l'observabilite conserve un trou de preuve causale.
- F6: `valide`; le benchmark historique est insuffisant pour la maturation
  multi-tours et le fallback.

## Goldens causaux techniques du coeur livres le 2026-08-28

La fixture partagee
`app/tests/support/stimmung_dialogic_pipeline.py` appelle le vrai
`chat_service.chat_response` par la route existante. Elle conserve le caller,
l'agregateur, le regime primaire, Validation et la construction du payload
principal reels; providers, horloge et stockage restent fakes. Le fake de
stockage en memoire appelle maintenant les vraies fonctions
`conversations_store.save_conversation`, sauvegarde atomique, normalisation,
adaptation JSON des metadonnees en lignes, relecture des messages et
`load_conversation`. Son curseur ne fait que conserver puis restituer les
resultats de lignes dans l'ordre. Chaque tour recharge un nouvel objet et un
snapshot JSON sert seulement a verifier le round-trip de la fixture. Aucune DB
PostgreSQL operateur ni JSONB reelle n'est traversee. Le golden
`app/tests/unit/golden/test_lot4_stimmung_causal_goldens.py` ajoute exactement
`10` tests Python.

Les dialogues synthetiques couvrent absence de signal, affect homogene jusqu'a
stabilite, transition apres stabilite, alternance, retour progressif au neutre,
signal invalide intermediaire et final, fallback reussi, double echec fail-open,
reconstruction repetee et parite JSON/streaming. Les proprietes observees sont
figees sans recopier poids, seuils ou hysteresis:

- G1: un signal est attache une fois au message utilisateur; la sauvegarde fake
  traverse les fonctions produit de normalisation, serialisation des lignes et
  relecture, puis le retrouve identique et dans le meme ordre dans de nouveaux
  objets; les rechargements repetes ne dupliquent rien et JSON/streaming
  produisent la meme histoire, sans prouver une DB ou une JSONB reelle;
- G2: quatre signaux valides au maximum sont agreges de l'ancien vers le
  recent; stabilite, transition volatile, `candidate_shift`, alternance et
  retour au neutre sont observes depuis le vrai agregateur; un signal invalide
  est ignore et un dernier signal invalide rend l'agregat honnetement absent;
- G3: absent et stable donnent le meme regime primaire sur inputs identiques;
  une transition volatile peut rabattre `certain/discrete` sur
  `probable/prudente`; Stimmung ne cree ni Presence, ni `clarify`, ni
  `suspend`, et ne modifie pas les hard guards;
- G4: le message effectivement capture avant le provider fake Validation
  contient Stimmung complete sous la borne, partielle pres de la borne et
  absente au-dela; a taille egale, `aaa_padding` l'evince et `zzz_padding` la
  conserve, ce qui fige l'effet de l'ordre lexical;
- G5: le bloc principal contient seulement posture, regime, consignes et
  directives derives. Une difference existe au primaire entre stable et
  transition, mais le provider Validation controle peut produire le meme bloc
  final; cette absence de difference est conservee comme resultat, pas comme
  preuve d'influence;
- G6: primaire, fallback et fail-open gardent des modeles, statuts et sources
  distincts; le double echec ne devient ni neutralite saine, ni Presence, ni
  sauvegarde supplementaire.

Mutations controlees effectivement rejetees par les memes validateurs
semantiques appliques aux sorties produit et aux mutants: signal retire, signal
ou message duplique, ordre inverse, cinquieme signal conserve, stable requalifie
volatile, transition ignoree, prudence forcee sur stable, Stimmung absente de
Validation presentee comme recue, signal brut injecte au modele principal,
fallback presente comme primaire, fail-open presente comme succes neutre,
sauvegarde ou reconstruction dupliquee. Les validateurs locaux portent sur
l'historique persistant, l'agregat quatre tours, le triplet
absent/stable/transition, la provenance caller, la reception Validation et le
payload principal derive uniquement; aucun framework de mutation n'est ajoute.

Commandes et resultats, toutes sans reseau ni provider et avec checkout
read-only pour Python:

- baseline Phase 2: `python -m unittest discover` dans le runner conteneur
  autoritatif -> `2716` OK, zero skip et zero expected failure;
- baseline frontend: `node --test app/tests/unit/frontend_chat/*.js` sous
  `unshare --net` -> `135/135`; Chromium existant, sans installation ni
  telechargement -> `19/19`;
- cycle rouge initial du nouveau golden -> `1` failure attendue, fixture
  absente;
- coeur Lot 4, caller, agregateur, regime et Validation -> `84/84`;
- persistance, chat JSON/streaming, Presence, final locks,
  observabilite et golden Lot 9 -> `97/97`;
- decouverte finale read-only -> `2726` OK, zero echec, zero erreur, zero skip
  et zero expected failure, soit exactement `10` nouveaux tests Python;
- JavaScript final -> `135/135`; Chromium final -> `19/19`.

Passe corrective de qualification des preuves, executee le 2026-08-28 dans le
meme runner hermetique Python:

- avant patch: decouverte complete `2726/2726` et golden Lot 4 `10/10`;
- sensibilite rouge: le validateur incomplet a laisse passer successivement le
  cinquieme signal puis une reconstruction dupliquee, soit une failure attendue
  a chaque etape avant ajout de la propriete semantique manquante;
- apres patch: golden Lot 4 `10/10`; persistance voisine `38/38`; caller,
  agregateur, regime et Validation `74/74`; chat JSON/streaming, Presence et
  final locks `57/57`; observabilite voisine `52/52`; goldens Lot 9 `20/20`;
- decouverte finale `2726/2726`, zero echec, erreur, skip ou expected failure;
  aucun test Python ajoute, aucun JavaScript ni Chromium relance car aucun
  fichier ou support frontend n'a ete modifie.

Classement des findings apres goldens:

- F1: `valide`; inertie du stable et prudence de transition sont prouvees au
  vrai agregateur/regime primaire, sans difference de texte provider prouvee;
- F2: `valide` comme description du raccord courant; son caractere
  architecturalement incorrect reste une decision corrective ouverte;
- F3: `valide`; les captures provider figent la perte partielle ou totale avant
  Validation et sa dependance a l'ordre lexical;
- F4: `partiel`; l'appauvrissement du bloc principal est prouve, pas son
  caractere dommageable sur une formulation provider reelle;
- F5: `valide`; les events prouvent execution et cles canoniques, pas la matiere
  effectivement recue par Validation ni une influence causale finale;
- F6: `valide`; les goldens de raccord sont multi-tours, mais le benchmark
  historique reste mono-tour et ne qualifie ni maturation semantique ni
  fallback.

Limites maintenues ouvertes: aucune campagne provider n'a ete lancee et le
corpus semantique multi-tours du caller n'a pas ete execute. Ironie, affect
rapporte, correction, intensite sans changement epistemique, question, demande,
risque, action materielle et contre-cas Presence restent donc non prouves. Le
runtime ne projette pas la reception effective par Validation ni l'influence
causale; les read-models et frontends ne rendent pas stabilite, shift ou
causalite autoritative. Le renforcement de persistance reste hermetique sur un
fake de lignes et ne prouve aucune DB/JSONB reelle. Aucun code runtime, prompt,
modele, provider, setting, timeout, niveau de raisonnement, read-model ou
frontend n'a ete modifie; aucun correctif F2, F3, F4 ou F5 n'a ete commence.

## Decoupage d'execution autoritatif du reste du Lot 4

Decision de Tof du 28 aout 2026: les findings prouves ne restent pas de simples
limites documentaires. Ils sont traites par des micro-lots distincts, dans
l'ordre ci-dessous. Chaque micro-lot garde une granularite suffisante pour etre
execute de bout en bout par un agent en niveau de raisonnement `high` ou
`extra high`, sans lui laisser le soin d'inventer l'architecture ou de fusionner
plusieurs decisions produit.

Ordre obligatoire:

`4C.1 -> 4S.0 -> validation humaine du corpus -> 4S.1 -> 4C.2 conditionnel -> 4C.3 -> 4C.4 conditionnel -> 4O.Z -> Lot 5`

Regles communes:

- un micro-lot, une baseline, un diff coherent, un commit et un push;
- toute modification runtime est livree separement sur FridaDev seul, avec
  provenance checkout/image, health, restart et OOM verifies;
- l'observabilite backend, reader, read-model, frontend existant et preuve
  navigateur evolue dans le meme micro-lot que la verite runtime concernee;
- `4O.Z` contre-audite cette synchronisation; il ne sert jamais a reparer
  tardivement une observabilite oubliee;
- `4C.2` et `4C.4` peuvent etre fermes `non requis`, uniquement par les preuves
  indiquees ci-dessous; les autres micro-lots sont obligatoires;
- aucun micro-lot ne supprime, desactive ou contourne Stimmung, n'ajoute de
  caller, de stage ou de capacite produit, ni ne commence le Lot 5;
- aucune regex affective, aucun profil identitaire et aucune inference durable
  sur une personne ne sont autorises;
- toute campagne provider demande un GO separe et n'utilise que le corpus
  synthetique valide.

### Micro-lot 4C.1 - Garantie structurelle Stimmung vers Validation

Statut: ferme le 2026-08-28, referme apres passe corrective du 2026-08-29, rouvert pour la preuve semantique, puis ferme le 2026-08-29 apres cutover Validation vers Gemini 3.7 Flash medium et smoke live unique vert; 4S.0 ferme le 2026-08-30 apres validation humaine deleguee par Tof a Codex
Effort recommande: `extra high`
Nature: correctif runtime borne, observabilite synchrone et preuves
Prerequis: goldens techniques du coeur livres; F3 valide

Objectif exact: supprimer la perte partielle ou totale de `stimmung_input`
causee par le prefixe arbitraire de `700` caracteres applique a la
serialisation lexicographique de `canonical_inputs`. Validation doit recevoir
soit une projection Stimmung complete et bornee, soit une absence explicite
avec un reason code borne. Une structure partielle ou une eviction silencieuse
selon le nom d'une autre source devient interdite.

Architecture imposee:

- conserver la borne globale du materiel transmis a Validation;
- remplacer le prefixe aveugle par une projection champ par champ, versionnee
  et bornee, avec un budget reserve explicite pour les sources contractuelles;
- ne jamais tronquer au milieu d'une structure JSON ou d'un champ Stimmung;
- rendre le resultat invariant a l'ordre lexical des autres cles;
- ne changer ni le modele, ni le provider, ni le niveau de raisonnement, ni le
  timeout, ni la semantique de verdict de Validation;
- ne pas anticiper les structured outputs du Lot 5;
- preserver hard guards, Presence, final locks, contexte dialogique, Identity,
  JSON/streaming et persistance.

Observabilite a livrer dans le meme micro-lot:

- evenement runtime content-free distinguant `full` et `absent`; `partial`
  devient un etat invalide rejete par les preuves;
- reason code d'absence borne, version de projection, taille projetee, budget
  utilise et familles de sources omises, sans contenu brut;
- source primaire/fallback et statut Validation conserves;
- chaine complete `event -> reader -> read-model -> renderer existant -> test
  navigateur`, sans nouvel ecran et sans deduction depuis un libelle libre;
- aucune tonalite brute, dialogue, prompt, payload provider, exception, URL ou
  secret dans les evenements ou fixtures frontend.

Preuves rouges obligatoires avant correctif:

- Stimmung partielle pres de la borne;
- Stimmung absente au-dela de la borne;
- permutation `aaa_padding`/`zzz_padding` changeant la reception;
- structure JSON coupee au milieu d'un champ;
- frontend annoncant une reception complete alors que le backend ne la prouve
  pas.

Preuves vertes et sensibilite obligatoires:

- meme signal complet sous plusieurs ordres et volumes de sources voisines;
- absence explicite uniquement pour une raison contractuelle reproduite;
- reconstruction repetee sans duplication;
- mutation supprimant, dupliquant ou deplacant le bloc Stimmung rejetee;
- mutation restaurant le prefixe lexicographique rejetee;
- mutation transformant `absent` ou `partial` en `full` rejetee a chaque couche;
- suites Validation, Stimmung, chat, Presence, final locks, JSON/streaming,
  persistance, observabilite, frontend et decouverte complete vertes;
- aucun nouveau skip ni expected failure.

Fermeture realisee:

- F3 a ete reproduit avant patch par `5` echecs/erreurs Python cibles et `2`
  echecs Chromium attendus: Stimmung partielle, evincee, dependante de
  `aaa_padding`/`zzz_padding`, JSON coupe et faux `full` frontend;
- `validation_canonical_projection.py` remplace le prefixe lexical par
  `validation_canonical_inputs_v1`: onze familles fermees, ordre contractuel
  fixe, blocs JSON entiers et budget global inchange de `700` caracteres. Une
  Stimmung valide reserve son bloc avant les autres familles; sa forme
  structurelle maximale de test occupe `627/700`, meme quand toutes les autres
  familles sont omises;
- les statuts autorises sont `full|absent`. `full` exige `included`; les raisons
  d'absence fermees sont `signal_not_present`, `invalid_signal` et
  `contract_budget_exceeded`. `partial`, incoherences, doublons, compteurs
  invalides ou famille inconnue sont rejetes;
- le meme materiel borne remis au provider fake produit les metadonnees de
  `validation_prompt_prepared`; le garde, la checklist, le reader et
  `turn_pipeline_read_model`, puis `/log` et `/hermeneutic-admin`, propagent
  version, statut, raison, caracteres, budget et familles omises sans contenu.
  Une preuve absente ou invalide devient `unknown`, jamais `full`;
- fichiers runtime: `validation_agent.py`, `validation_contract.py`,
  `validation_messages.py`, le nouveau projecteur, le schema de garde, la
  projection admin, la checklist et le read-model. Frontend: `log/log.js` et
  `hermeneutic_admin/render.js`. Preuves: tests Validation, golden Lot 4,
  read-model/logs et Chromium; contrats vivants Validation, logs et dashboard;
- mutations rejetees par les validateurs appliques aux sorties produit et aux
  mutants: suppression, duplication ou deplacement de Stimmung, retour au
  prefixe lexical, inversion de priorite, `partial`, absent presente comme
  `full`, compteurs/budget falsifies, frontend auto-affirmatif et contenu brut;
- commandes hermetiques reellement executees: baseline Python `2726/2726`,
  JavaScript `135/135`, Chromium `19/19`; apres patch, constructeur/golden/
  read-model `77/77`, coeur Stimmung/Validation/regime `82/82`, chat/
  persistance/locks `43/43`, observabilite `110/110`, goldens voisins `43/43`,
  JavaScript `135/135`, Chromium `19/19`, puis decouverte Python `2728/2728`.
  Zero echec, erreur, skip ou expected failure dans les preuves finales; deux
  tests Python nets ont ete ajoutes;
- aucun modele, provider, prompt, timeout, verdict, regime, Presence, lock,
  persistance, format JSON/streaming ou payload principal n'a change. Le corpus
  semantique, l'effet causal final, F2/F4/F5 et la matrice complete 4O.Z restent
  ouverts; aucune campagne provider ni DB operateur n'a ete utilisee.

Passe corrective du 2026-08-29 — suffisance de la matiere Validation:

- contre-audit reproduit sur le HEAD `ba246653fc4a68dfac340a34921cc48bee820bc8`:
  la projection v1 etait structurellement sure mais trop petite. Sur le vrai
  coordinateur synthetique, elle mesurait `658/700`, le message utilisateur
  Validation `5598` caracteres et son estimation `2694` tokens; seules
  `stimmung_input` et `user_turn_signals` etaient incluses. Notamment,
  `user_turn_input`, necessaire a la relecture du geste, de la preuve et du
  temps, etait evince uniquement par le budget;
- les tailles ci-dessous sont les longueurs JSON compactes des blocs projetes.
  `0` signifie qu'aucun bloc n'est serialise pour la disposition normale
  indiquee; les sources riches brutes memory, summary, Identity et Web ne sont
  pas bornees et ne sont donc jamais recopiees telles quelles:

| Famille | Min | Normale | Max contractuel | Deja transmise ailleurs | Projection compacte necessaire | Omission autorisee |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `time_input` | 0 | 0 | 0 | `temporal_reference` | non | `redundant_elsewhere`; `no_data`; invalide degrade |
| `memory_retrieved` | 0 | 0 | 315 | non, seulement interpretee en amont | oui: statut, raisons et compteurs | `no_data`; invalide degrade; budget exceptionnel |
| `memory_arbitration` | 0 | 0 | 278 | non, seulement interpretee en amont | oui: statut, raisons et compteurs | `no_data`; invalide degrade; budget exceptionnel |
| `summary_input` | 0 | 0 | 437 | non comme source distincte | oui: statut, presence et bornes temporelles | `no_data`; invalide degrade; budget exceptionnel |
| `identity_input` | 0 | 0 | 369 | non comme source distincte | oui: statut et presence statique/mutable par sujet | `no_data`; invalide degrade; budget exceptionnel |
| `recent_context_input` | 0 | 0 | 0 | `validation_dialogue_context` | non | `redundant_elsewhere`; `no_data`; invalide degrade |
| `recent_window_input` | 0 | 0 | 0 | `validation_dialogue_context` plus large | non | `redundant_elsewhere`; `no_data`; invalide degrade |
| `user_turn_input` | 0 | 323 | 456 | non | oui, structure semantique complete | jamais sur entree runtime valide; invalide degrade |
| `user_turn_signals` | 0 | 138 | 205 | non | oui, structure complete | jamais sur entree runtime valide; invalide degrade |
| `stimmung_input` | 0 | 184 | 276 | non | oui, structure complete | signal absent/invalide; budget exceptionnel, jamais partiel |
| `web_input` | 0 | 0 | 713 | non comme source distincte | oui si active: statut, confiance, preuve et fallback | `optional_not_requested`; `no_data`; invalide degrade; budget exceptionnel |

- option retenue: projections compactes par famille puis plus petite borne
  superieure au maximum mesure. `validation_canonical_inputs_v2` conserve les
  trois structures semantiques deja bornees (`user_turn_input`, signaux du tour
  et Stimmung), projette les sources riches en metadonnees fermees, et marque
  time/contexte/fenetre comme redondants avec leurs blocs autoritatifs. L'ordre
  des onze familles reste fixe et toutes recoivent exactement une disposition
  parmi `included`, `no_data`, `redundant_elsewhere`,
  `optional_not_requested`, `invalid_input` et
  `contract_budget_exceeded`;
- contre-audit du maximum: la fixture historique choisie a la main ne prouvait
  pas `3704`. Le maximum accepte par le validateur v2, derive des limites et
  vocabulaires produit, mesure `3741/3840`, soit `99` caracteres de marge
  (`2,6 %`). Le maximum emittable par les dispositions et builders runtime
  mesure `3546/3840`, soit `294` caracteres de marge (`7,7 %`). Un
  contre-exemple accepte de `3712` conserve la regression initiale. Le cas
  coordinateur mesure apres correction `1220/3840`; le message Validation
  mesure `6160` caracteres et `2881` tokens estimes, soit `+562` caracteres et
  `+187` tokens. Dix mille reconstructions locales prennent `1087,67 ms`
  (`0,1088 ms` en moyenne), restent identiques et sans duplication;
- runtime courant: v2 uniquement. Les evenements historiques v1 restent lus
  comme `historical_v1` avec budget `700`; v2 vaut `current_v2`; une version
  inconnue ou des metadonnees incoherentes ne sont jamais presentees comme
  saines. `validation_prompt_prepared`, garde, projection admin, checklist,
  read-model, `/log` et `/hermeneutic-admin` propagent version, borne, taille et
  familles `included|no_data|redundant|optional|invalid|budget_exceeded` sans
  contenu brut. Les deux renderers reutilisent le meme validateur frontend
  `validation_projection.js`; les trois pages qui chargent le renderer partage
  (`/log`, `/hermeneutic-admin` et `/identity`) declarent cette dependance;
- reproductions rouges correctives: trois preuves cibles donnaient `2` echecs
  et `1` erreur avant le patch v2, en montrant l'eviction de la matiere requise,
  l'insuffisance de la preuve structurelle v1 et l'absence de distinction
  v1/v2/version inconnue dans le read-model. Le cas navigateur verrouille aussi
  les omissions correctement affichees, la preuve incoherente refusee et le
  contrat historique;
- sensibilite: les validateurs produit rejettent le retour a `700`, une borne
  sans maximum contractuel, une famille brute non bornee, l'omission de
  `user_turn_input`, son remplacement par un booleen, une famille redondante
  recopiee, un ordre variable, Stimmung partielle ou faussement `full`, les
  compteurs falsifies, v2 presentee comme v1, v1 reinterpretee en v2, version
  inconnue saine et contenu brut dans l'observabilite;
- fichiers runtime: `validation_canonical_family_projection.py`, projecteur,
  contrat, constructeur de messages, garde, projection admin, checklist et
  read-model. Frontend: module partage de validation, ordre/validation des
  assets, trois pages chargeuses et deux renderers consommateurs. Tests:
  constructeur/contrat, golden Lot 4, logs/read-model, contrats frontend et
  Chromium. Documentation: contrats vivants Validation et logs, plus la
  presente passe corrective;
- commandes hermetiques reellement executees: baseline Python `2728/2728`,
  JavaScript `135/135` et Chromium `19/19`; cycle rouge correctif `3` preuves,
  soit `2` echecs et `1` erreur attendus; coeur Stimmung/Validation/regime
  `84/84`; chat, persistance, JSON/streaming et locks `54/54`; observabilite,
  reader et read-model `83/83`; goldens Lots 0/3/4/9 et locks voisins `49/49`;
  controles frontend et validation cibles `97/97` puis assets UI `34/34`;
  JavaScript final `135/135`, Chromium final `19/19`, decouverte Python finale
  `2729/2729`. Le total augmente d'un test Python net; aucun skip ni expected
  failure final. Le premier contre-audit complet a justement refuse un
  renderer trop long et un identifiant d'exception brute; le premier Chromium
  complet a revele la dependance partagee manquante sur `/identity`; ces trois
  ecarts de patch ont ete corriges avant les passages finaux verts;
- limites: aucun provider reel ne prouve encore l'equivalence semantique des
  verdicts. Cette comparaison appartient a la presente fermeture 4C.1:
  `4S.0` et `4S.1` qualifient exclusivement le caller Stimmung et n'appellent
  ni Validation ni le modele principal. F2, F4, F5,
  prompts, modeles, providers, verdicts, regime, posture principale, Presence,
  locks, persistance et JSON/streaming restent inchanges.

Phase 1 figee avant resultats provider — comparaison Validation v1/v2:

- reference v1 exacte: commit
  `ba246653fc4a68dfac340a34921cc48bee820bc8`, projecteur
  `validation_canonical_inputs_v1`, budget `700`; le harness l'execute depuis
  une archive Git temporaire dont l'empreinte du projecteur est verrouillee,
  sans branche ni copie approximative de l'algorithme;
- reference v2: commit contenant le present protocole, projecteur
  `validation_canonical_inputs_v2`, budget `3840`. Le constructeur courant
  prepare le message complet, puis le harness remplace uniquement le bloc
  canonique par le resultat exact v1; les empreintes du prompt systeme et de
  toute la matiere utilisateur hors bloc canonique doivent rester identiques;
- corpus versionne
  `benchmark/suites/validation_agent/fixtures/lot4c1_validation_projection_cases.json`:
  `10` cas synthetiques couvrant interrogation, demande, Presence et
  contre-cas, ambiguite actionnelle, incertitude et hard guards, temps,
  Stimmung stable et transition, Web avec reserve, metadonnees memory/summary/
  Identity et familles optionnelles absentes;
- protocole/scorer fige dans
  `benchmark/suites/validation_agent/lot4c1_comparison.py`: primaire
  `google/gemini-3.1-flash-lite`, fallback `openai/gpt-5.4-nano`, temperature
  `0.0`, `top_p=1.0`, `max_tokens=140`, timeout `15 s`, aucun raisonnement
  explicite, `2` repetitions, `2` projections, soit `80` appels sur un plafond
  absolu de `96`; cout maximal prudent `0,10 USD`, deux fois superieur a
  l'extrapolation des maxima observes dans la campagne Validation du
  2026-08-21;
- decision figee: `pass` seulement sans nouvel interdit, faux Presence,
  violation de hard guard ni regression v2 face a v1 pour le meme modele et la
  meme repetition; `fail` sur toute regression semantique; `inconclusive` si
  un cas/modele ne conserve aucune repetition paire valide. La degradation
  Presence historique du fallback n'est toleree que si v1 et v2 echouent de
  facon identique; aucun seuil ne peut etre deplace apres les reponses;
- preuve hermetique avant campagne: `10/10` cas reconstruits depuis le commit
  historique exact; fourchette v1 `593..680` caracteres, v2 `1022..2373`, et
  seule la matiere canonique differe. Les tests de maximum, corpus, constructeur,
  scorer, decision et artefact content-free comptent `8/8` succes avant appel provider;
- 4C.1 reste ouvert jusqu'a l'artefact JSONL content-free, la decision
  primaire/fallback, les suites completes et le second commit pousse.

Phase 2 — campagne provider executee sur le protocole fige:

- commit de gel pousse avant tout resultat:
  `a60114e1717d9cff88c44b3dfc8fa1a2545bb006`; v1 reste le commit historique
  exact `ba246653fc4a68dfac340a34921cc48bee820bc8`;
- `80/80` appels executes, tous transport `ok`, sans timeout, refus, JSON
  invalide ni schema invalide. Cout total observe `0,03997686 USD`, sous le
  plafond prudent `0,10 USD`; `175067` tokens totaux observes;
- artefact durable content-free:
  `benchmark/results/validation_agent/2026-08-29-lot4c1-validation-v1-v2.jsonl`,
  `121` lignes (`80` appels, `40` comparaisons paires, `1` synthese), empreinte
  SHA-256 `db216a6bb4ad6ccceff2eff0d3fb559a061f5f68b953443dda3bd9afe11ae0a4`;
- primaire: `18/20` resultats semantiques valides en v1 et `18/20` en v2.
  `L4C1-VAL-005` produit `answer/simple` aux deux repetitions et dans les deux
  projections, alors que l'attente critique figee autorise uniquement
  `clarify/simple|meta`;
- fallback: `18/20` resultats semantiques valides en v1 et `18/20` en v2. Les
  deux ecarts sont uniquement la degradation Presence historique acceptee sur
  `L4C1-VAL-003`, identique entre v1 et v2 et jamais requalifiee en succes;
- comparaison causale: `40/40` paires v1/v2 ont la meme paire posture/regime;
  aucune regression relative v2, aucun nouveau faux Presence et aucune
  violation de hard guard ne sont observes. Cette egalite ne suffit toutefois
  pas a satisfaire la regle `pass`, qui exige aussi tous les invariants
  critiques v2;
- contre-audit du harness: la premiere synthese avait lu par erreur le champ
  absent `classification` au lieu du champ durable `status` et annoncait
  `pass` malgre deux comparaisons `fail`. Le seuil et les resultats n'ont pas
  ete modifies: le lecteur a ete corrige, verrouille par test, puis la synthese
  recalculee depuis les `120` lignes content-free existantes sans nouvel appel;
- preuves finales hermetiques sans provider: suites Validation, Stimmung,
  goldens, chat, Presence, hard guards, locks, persistance et observabilite
  `206/206`; JavaScript `135/135`; Chromium `19/19`; decouverte Python finale
  `2736/2736`, soit exactement `7` tests nouveaux face a `2729`. La premiere
  decouverte encore a `2729` a revele que le dossier `unit/benchmark` n'etait
  pas autoritairement decouvert; le seul fichier nouveau a ete deplace dans
  `unit/golden`, sans changer son contenu. Zero echec, erreur, skip, todo ou
  expected failure dans les passages finaux;
- decision figee finale: `fail`, reason code
  `semantic_regression_or_critical_failure`, ici pour invariant critique
  primaire non satisfait et non pour regression relative v2. Conformement au
  mandat, aucun runtime, prompt, modele, provider ni scorer semantique n'est
  corrige dans cette passe; 4C.1 reste ouvert et 4S.0 reste non commence.

Passe A du 2026-08-29 — assainissement de la preuve et de la provenance:

- F1 est valide comme defaut critique partage: sur `L4C1-VAL-005`, le primaire
  amont recommande `clarify`, la projection v2 est complete, mais les deux
  repetitions du primaire Validation restent `answer/simple` en v1 comme en
  v2. Il ne s'agit donc pas d'une regression relative de v2;
- F2 est valide: les signaux projetes valent
  `ambiguity_present=false`, `underdetermination_present=false`, le geste
  dominant est `exposition` et aucun hard guard deterministe ne s'applique.
  Aucun hard guard, regex ou pouvoir mecanique du primaire n'est ajoute;
- F3 est valide puis ferme pour l'artefact 4C.1: le validateur acceptait une
  phrase synthetique dans `reason_code` ou `observed_provider`. Il verrouille
  maintenant schemas par type de record, types, tailles, plages numeriques,
  empreintes SHA-256 et vocabulaires fermes pour versions, cas, projections,
  roles, modeles, providers, statuts, raisons et divergences;
- F4 est valide puis ferme sans changement fonctionnel: le benchmark lit
  desormais l'autorite publique `web_input.ACTIVATION_MODES`; l'export prive
  ajoute au runtime pour le benchmark est retire. L'empreinte checkout du
  projecteur familial retrouve exactement celle du conteneur et de la version
  pre-campagne: `cb887bdeb4671f299eff4372b896d0615e998a90b06e01f67337475597b282a5`;
- les `120` lignes content-free existantes ont ete rescories sans appel
  provider puis la synthese a ete recalculee. Les deux paires primaires 005
  valent `shared_critical_invariant_failure`; une vraie degradation propre a
  v2 vaut `v2_semantic_regression`; une paire provider invalide reste separee
  et la faiblesse Presence fallback conserve son statut accepte mais
  `scorer_pass=false`. L'artefact conserve `121` lignes et porte l'empreinte
  `3fb9da32fa8a584eb2cbe8696970d299a8f28efc86d559f4103ac2c04c04a02d`;
- cycle TDD: `7` tests cibles ont d'abord produit `4` echecs attendus, puis
  `7/7`; suites benchmark/goldens/Validation/Stimmung/observabilite voisines:
  `137/137`. Aucun reseau, provider, secret, DB operateur, rebuild ou restart;
  runtime inchange. Commit autonome pousse:
  `f45c58dc58cdd8eb1bdb3c0a52a3c679de16e5c2`. Cette passe ne ferme pas 4C.1: la comparaison de la
  politique courante contre une unique candidate doit encore etre gelee,
  executee et jugee `pass` avant toute correction runtime.

Passe B gelee avant campagne provider le 2026-08-29:

- reproduction causale hermetique de 005: recommandation amont `clarify`,
  signaux `ambiguity_present=false` et `underdetermination_present=false`,
  geste `exposition`, projection `validation_canonical_inputs_v2` complete de
  `1022` caracteres et aucun hard guard. La politique courante place la
  preference generale pour la reponse simple avant l'examen des lectures
  incompatibles a consequences materielles differentes;
- hypothese corrective unique: remplacer seulement les trois lignes de cette
  sequence par un examen prioritaire de l'absence d'interpretation coherente ou
  de plusieurs lectures encore coherentes menant a des actions materiellement
  differentes, puis appliquer la preference pour la reponse simple dans les
  autres cas. La recommandation primaire, les signaux lexicaux et Stimmung
  restent secondaires et non souverains; aucun hard guard ni regex n'est cree;
- fragment courant `validation_decision_policy_v1`, empreinte
  `c783ba346a7256699dae22a2b83133b72cfa5926fd630025dd9cb94892eafd2a`;
  candidate `validation_decision_policy_v2`, empreinte
  `68591a18cadf7ce61b7d39f87916c834cb068d26bbc82dbd88793aec9e9d62f9`.
  Les tests prouvent sur les onze cas que seuls les octets de ce fragment
  changent: system prompt, canonical inputs v2 et message utilisateur hors
  politique conservent leurs empreintes;
- les dix cas precedents sont reutilises. Un seul controle est ajoute,
  `L4C1-VAL-011`: recommandation amont `clarify`, formulation synthetique
  resolue par le contexte sans action materielle divergente, attente
  `answer/simple`. Il interdit de rendre le primaire ou un simple indice
  lexical souverain;
- protocole `lot4c1_validation_policy_comparison_v1`, corpus combine
  `lot4c1-validation-policy-v1`, empreinte
  `bb0416662dd0cd9a42436c7f185c86e44ec877090326a6c0cf4ec4846c1184d4`:
  politiques courante/candidate, primaire/fallback separes, deux repetitions
  et ordre alterne, soit `88` appels prevus sous le plafond `96` et un cout
  maximal prudent de `0,10 USD`. Modele, provider, temperature `0.0`,
  `top_p=1.0`, plafond `140`, timeout `15 s` et raisonnement explicite absent
  restent identiques;
- decision figee: `pass` seulement si les deux repetitions primaires valides
  de 005 deviennent conformes, 011 reste `answer`, aucun cas valide ne
  regresse, Presence/hard guards/prudence Stimmung-Web restent conformes, la
  faiblesse Presence fallback n'est pas aggravee et toutes les paires sont
  valides. Un seul echec vaut `fail`; une paire provider manquante ou invalide
  vaut `inconclusive`; aucun seuil n'est mutable apres les resultats;
- cycle TDD du protocole: import absent en rouge, puis `5/5` preuves vertes sur
  corpus, unicite du fragment, egalite hors fragment, scorer, decision et garde
  d'artefact. Aucun appel provider n'a encore ete effectue et aucun fichier
  runtime n'a ete modifie par cette passe de gel.

Campagne provider de la passe B — decision `fail`:

- commit de gel pousse avant le premier appel:
  `daba97bbd9f6a3fda37a956d0b855bcd0647c415`; aucun corpus, attente, scorer,
  fragment, modele ou parametre n'a ete modifie apres lecture des resultats;
- `88/88` appels executes et valides au niveau transport et schema: aucun
  timeout, refus, JSON invalide ni schema invalide. Cout total observe
  `0,04507676 USD`, sous le plafond `0,10 USD`; `201283` tokens totaux;
- artefact durable content-free
  `benchmark/results/validation_agent/2026-08-29-lot4c1-validation-policy-current-candidate.jsonl`:
  `133` lignes (`88` appels, `44` paires, `1` synthese), empreinte
  `97d9d208cb70882df32e714f708e0cde092450dc5156c35e9889ba2205fe10ab`;
- primaire: politique courante `20/22` et candidate `20/22` resultats
  semantiques valides. Sur 005, les deux politiques produisent encore
  `answer/simple` aux deux repetitions. La candidate ne satisfait donc aucune
  des deux repetitions critiques exigees;
- fallback: politique courante `20/22` et candidate `20/22`. Les deux ecarts
  restent uniquement la faiblesse Presence historique de 003, identique et
  visible comme `accepted_preexisting_fallback_gap`, jamais comme succes du
  scorer. Sur 005, les deux politiques choisissent une clarification conforme;
- contre-cas 011: primaire et fallback conservent `answer/simple` pour les deux
  politiques et les deux repetitions. La candidate n'a pas rendu la
  recommandation amont `clarify` souveraine;
- `44/44` paires courante/candidate ont la meme posture et le meme regime:
  `40` paires `pass`, `2` ecarts Presence fallback acceptes et `2` paires
  primaires 005 `shared_critical_invariant_failure`. Decision finale gelee:
  `fail`, sans regression nouvelle mais sans correction de l'invariant;
- stop-rule appliquee: aucun changement de `validation_messages.py`, prompt
  courant, politique observable runtime, modele, provider, raisonnement,
  hard guard, regex, Stimmung, Presence ou frontend; aucun rebuild, restart ou
  deploiement. 4C.1 reste ouvert et 4S.0 reste non commence. Une decision
  separee sera necessaire pour comparer une autre hypothese, un modele ou un
  niveau de raisonnement; cette mission ne l'anticipe pas;
- preuves finales sans reseau ni provider: benchmark/goldens/Validation/
  Stimmung/observabilite `158/158`; chat, JSON/streaming, Presence, Web, hard
  guards, final locks, persistance et goldens Lots 0/3/4/9 `275/275`;
  decouverte Python complete `2742/2742`, soit exactement `6` tests nouveaux
  face a `2736`, zero echec, erreur, skip ou expected failure. JavaScript
  `135/135` et Chromium `19/19` ont ete verifies en baseline; ils ne sont pas
  rejoues apres campagne car aucun runtime, contrat d'observabilite ou fichier
  frontend n'a change.

Comparaison des futurs modeles principaux — protocole gele avant campagne:

- F1 valide: les `22` appels du temoin historique
  `google/gemini-3.1-flash-lite` sont reutilisables sans nouvel appel. Les onze
  triplets d'empreintes prompt/matiere hors politique/projection canonique,
  le corpus `bb0416662dd0cd9a42436c7f185c86e44ec877090326a6c0cf4ec4846c1184d4`
  et le scorer
  `4b71ed96943129ff54590bc46da3d7d5b94c86ec0f66f278a16cb4a969007b77`
  correspondent au gel; le temoin reste `20/22`, avec seulement 005 en echec
  aux deux repetitions;
- F2 valide: `openai/gpt-5.4-nano` reste le fallback runtime et son ecart
  Presence historique demeure visible, mais il n'est ni rappele ni evalue
  comme candidat principal. F3 valide: la candidate de politique precedente
  a produit exactement les memes paires posture/regime sur `44/44`
  comparaisons; aucun prompt n'est change dans cette campagne;
- F4 valide au 2026-08-29T12:29:48Z depuis les metadonnees OpenRouter et les
  documentations Google/OpenAI: les slugs standard sont
  `google/gemini-3.7-flash` et `openai/gpt-5.6-luna-pro`; tous deux acceptent
  `medium|high`, le slug Luna porte deja le mode Pro, et l'effort reste
  independant. Le payload utilise `reasoning={effort, exclude:true}`, omet
  `temperature`, `top_p` et `response_format`, fixe `allow_fallbacks=false` et
  `require_parameters=true`, et n'emploie ni Batch, ni Flex, ni Priority;
- protocole `lot4c1_validation_model_comparison_v1`, metadonnees publiques
  content-free d'empreinte
  `29e0276c72232859dbbb958728cde85eef7a3a6c088b6f712718190ff23e8515`:
  Gemini 3.7 Flash `medium|high` et GPT-5.6 Luna Pro `medium|high`, onze cas
  inchanges, deux repetitions et ordre tourne par cas/repetition, soit `88`
  appels sous le plafond absolu `96`, sans fallback automatique;
- `max_tokens=500` est gele pour les quatre configurations: les preuves Lot 3
  montrent une sortie Validation complete avec Luna `medium/500`; a effort
  `high`, la part indicative de raisonnement laisse encore environ `100`
  tokens de sortie, contre `79` tokens de completion au maximum dans le temoin
  actuel. Le timeout interactif reste `15 s`;
- le cout maximal prudent est gele a `0,28 USD`: maximum historique de `2637`
  tokens d'entree, marge de tokenisation de `10 %` soit `2901`, plafond de
  `500` tokens de sortie, prix observes par slug, estimation brute
  `0,23016180 USD`, puis marge de `20 %`. Toute absence de cout, latence ou
  compteur de raisonnement reste `inconclusive`, jamais zero fabrique;
- eligibilite figee: `22/22`, deux succes sur 005, deux Presence sur 003, deux
  `answer/simple` sur 011, aucun hard guard viole, aucune prudence Stimmung/Web
  perdue, aucun transport invalide ou appel au-dela de `15 s`. A qualite
  egale, l'effort le plus faible est prefere; cout, mediane/p95 et tokens ne
  departagent qu'une fois la conformite acquise. La recommandation ne vaut
  jamais autorisation de cutover;
- harness reutilise: extension du comparateur de politique existant, builders
  de cas, constructeur de messages, projection v2 et scorer partages; aucun
  troisieme scorer, validateur semantique ou corpus n'est cree. Le validateur
  content-free rejette texte de raisonnement, route incoherente, metrique
  absente presentee comme zero, `:batch`, tier non standard et `21/22`
  presente comme eligible;
- cycle TDD avant appels: `10` preuves ont d'abord produit `9` erreurs sur les
  frontieres absentes, puis une mutation d'effort non supporte est restee
  rouge; apres implementation, `10/10` sont vertes. Goldens 4C.1, benchmark
  Validation et Presence voisins: `35/35`. Le commit de gel doit etre pousse
  et son hash injecte dans chaque ligne durable avant le premier appel;
- aucun modele, fallback, prompt, transport runtime, setting, frontend ou
  deploiement n'est modifie. 4C.1 reste ouvert quelle que soit la
  recommandation de campagne; un cutover exige une decision humaine separee.

Campagne des futurs modeles principaux — recommandation corrigee
`recommend_gemini_3_7_flash_medium`:

- commit de gel pousse avant le premier appel:
  `4e02a6da94d338e50dc62f8fd8c321e7643dc4c5`; corpus, prompt, projection,
  scorer, configurations, ordre, plafond de sortie, timeout, cout et regle de
  selection n'ont pas change apres lecture des resultats;
- `88/88` appels executes sur le transport standard, sans Batch, Flex,
  Priority ni fallback automatique. Les modeles observes correspondent aux
  slugs demandes et les providers observes sont `Google` et `OpenAI`; le tier
  observe vaut `default` partout. Le cout total est `0,21959182 USD`, sous le
  plafond `0,28 USD`; `607436` tokens totaux, dont `36568` tokens de
  raisonnement, sont observes;
- artefact durable content-free
  `benchmark/results/validation_agent/2026-08-29-lot4c1-validation-primary-models.jsonl`:
  `93` lignes (`88` appels, `4` syntheses de configuration, `1` synthese
  globale), empreinte SHA-256
  `b0f6f05d00b12bc0ae72404f493d72df72a5c600dc724381d7563c0759c136b1`;
- Gemini 3.7 Flash `medium` est la seule configuration eligible: `22/22`,
  005 clarifie aux deux repetitions, 003 produit Presence deux fois et 011
  reste `answer/simple`. Latence mediane `2586,496 ms`, p95 `3364,655 ms`,
  maximum `3899,876 ms`; `54775` tokens dont `2944` de raisonnement; cout
  `0,05334825 USD`;
- Gemini 3.7 Flash `high` est `inconclusive`: `11` sorties sont des JSON
  invalides et seulement `11` appels restent semantiquement comparables. Les
  onze invalides atteignent tous `496` tokens de completion sur le plafond
  `500`, avec `449..481` tokens de raisonnement; cette correlation suggere une
  saturation du plafond mais ne prouve pas sa cause, le finish reason n'etant
  pas conserve. Latence mediane `4519,312 ms`, p95 `6613,374 ms`, maximum
  `8664,489 ms`; cout `0,07453575 USD`;
- GPT-5.6 Luna Pro `medium` et `high` sont non eligibles, chacun a `18/22`.
  Tous deux reussissent 003, 005, 011, hard guards, Stimmung et Web, mais
  sur-clarifient les cas 001 et 004 aux deux repetitions. Medium: mediane
  `4120,685 ms`, p95 `7057,121 ms`, maximum `7153,750 ms`, `7991` tokens de
  raisonnement, cout `0,04044174 USD`. High: mediane `6618,724 ms`, p95
  `12806,068 ms`, maximum `12843,362 ms`, `16706` tokens de raisonnement,
  cout `0,05126608 USD`;
- le premier artefact classait deux JSON invalides de 003 avec le code
  semantique `missed_presence`, heritage du scorer appele sans verdict. Sans
  changer scorer, corpus, seuil ni resultat, le garde a ete renforce pour
  separer tout `invalid_json` des erreurs semantiques; les quatre syntheses et
  l'empreinte ont ete recalculees depuis les `88` lignes content-free, sans
  nouvel appel;
- recommandation recalculee sans appel provider:
  `recommend_gemini_3_7_flash_medium`. L'etat `inconclusive` de Gemini `high`
  ne contamine plus l'unique configuration independante eligible; les Luna Pro
  restent non eligibles. L'artefact conserve
  `runtime_cutover_authorized=false`: seule une decision humaine separee peut
  autoriser le cutover;
- prerequis d'un eventuel cutover separe: decision humaine, branchement runtime
  propre au modele retenu, retrait des sampling params incompatibles,
  raisonnement explicite et plafond de sortie prouves, observabilite de la
  configuration effective, suites completes puis livraison ciblee. Cette
  campagne ne modifie aucun de ces elements et ne ferme pas 4C.1;
- preuves post-campagne: validateur/artefact/reclassification `12/12`;
  benchmark/goldens/Validation/Presence/hard guards/Web/Stimmung/regime
  `109/109`; chat, observabilite, read-model, final locks et goldens voisins
  `90/90`; decouverte Python complete read-only `2754/2754`, soit exactement
  `12` tests nouveaux face a `2742`, zero echec, erreur, skip ou expected
  failure. Une premiere commande de decouverte montee sur `app/` seulement a
  echoue avant preuve sur cinq imports d'autorite benchmark; l'invocation
  autoritative corrigee monte le depot entier en lecture seule. JavaScript
  `135/135` et Chromium `19/19` ont ete verifies en baseline; ils ne sont pas
  rejoues apres resultats car aucun runtime, contrat frontend ou fichier
  frontend n'a change.

Passe de cutover decidee par Tof le 2026-08-29 — implementation livree,
preuve live non acquise et rollback applique:

- commit runtime pousse `aacb25f757932655a777d6cfbcfd2330e900c937`:
  primaire `google/gemini-3.7-flash`, raisonnement `medium` avec
  `exclude=true`, plafond `500`, sampling absent et routage standard sans
  fallback provider; le fallback `openai/gpt-5.4-nano` conserve sampling
  `0.0/1.0`, plafond propre `140` et timeout `15 s`;
- l'evenement prepare, la garde, la checklist, le read-model et les deux
  renderers existants projettent la politique effective content-free; les
  evenements historiques restent `unknown`. La provenance modele/provider
  observee vient du vrai proxy `_RequestsChatLogProxy` du chemin `/api/chat`;
- preuves avant livraison: ciblage final `234/234`, proxy/read-model
  `57/57`, Python complet `2757/2757` contre `2754/2754` avant patch,
  JavaScript `137/137` contre `135/135`, Chromium `19/19`; aucun skip ni
  expected failure;
- livraison ciblee sans pull: image
  `sha256:7bc8b5d0d475c46d42793830f830def10e90583e3d8d864d796e670186b4d94d`,
  `StartedAt=2026-08-29T14:08:56.011388208Z`, HTTP `200`, healthy, restart
  `0`, OOM false; aucun conteneur voisin n'a ete recree;
- le setting live a d'abord ete applique par l'API applicative et relu conforme.
  L'unique appel provider synthetique a traverse le vrai agent et retourne un
  resultat, mais le harness a ensuite applique le validateur de verdict
  provider au bloc final deja normalise et a perdu la preuve avant sa synthese
  content-free. Aucun second appel n'a ete lance;
- stop-rule respectee: les anciennes valeurs ont ete restaurees par la meme
  API et relues conformes (`google/gemini-3.1-flash-lite`, plafond `140`,
  fallback inchange). La preuve live est donc `inconclusive`, 4C.1 reste
  ouvert et 4S.0 reste non commence. Une nouvelle autorisation explicite sera
  necessaire pour retenter un smoke provider et activer le setting cible.

Passe corrective finale et activation live du 2026-08-29:

- findings revalides: F1 valide, le bloc OpenRouter strict etait applique a
  tort au primaire historique et au fallback; F2 valide, le smoke confondait
  le verdict provider brut avec le resultat final normalise; F3 valide, le
  readback admin affichait la politique Gemini 3.7 depuis une constante alors
  que le modele live etait encore Gemini 3.1;
- commit correctif pousse
  `6499b21a064ec9f738b67ed99f8b8dfb0588f849`: routage strict reserve au
  primaire Gemini 3.7, aucun bloc `provider` ajoute au legacy ou au fallback,
  contrat distinct `ValidationAgentResult`, politique admin derivee du tuple
  runtime coherent et bit content-free `validation_provider_routing_sent`
  propage jusqu'aux deux renderers existants;
- sensibilites rejetees: routage retire du nouveau primaire, routage ajoute au
  legacy/fallback, metadonnees de routage fabriquees, sampling primaire
  reintroduit, verdict brut confondu avec le resultat normalise, hard guard
  `caveat_required` refuse, `answer` admis sous `answer_forbidden`, setting
  legacy affiche comme Gemini 3.7 et evenement incomplet presente comme
  autoritatif;
- preuves hermetiques finales: ciblage transport/agent/settings/logs
  `101/101`, Python complet `2759/2759` contre `2757/2757`, soit exactement
  deux nouveaux tests, JavaScript `137/137`, Chromium `19/19`; zero echec,
  erreur, skip, todo ou expected failure. La revue independante a identifie
  puis fait corriger la couverture `caveat_required` avant livraison;
- livraison ciblee sans pull: image
  `sha256:fcfb4253fbbbd965de0efec19d32d08d432be6f18adb0c1e90d3869315256f99`,
  `StartedAt=2026-08-29T15:03:27.901122622Z`, HTTP `200`, healthy, restart
  `0`, OOM false; les empreintes des six fichiers executes correspondent au
  checkout et tous les conteneurs voisins conservent ID et `StartedAt`;
- setting applique uniquement par l'API applicative puis relu conforme:
  primaire `google/gemini-3.7-flash`, effort `medium`, plafond `500`, fallback
  `openai/gpt-5.4-nano`, timeout `15 s` et politique
  `validation_request_gemini_3_7_flash_medium_v1`;
- unique smoke provider effectif sur `L4C1-VAL-005`: exactement un appel et
  une tentative, source primaire, modele demande et observe
  `google/gemini-3.7-flash`, provider observe `Google`, effort `medium`,
  `exclude=true`, plafond `500`, sampling absent, routage strict present,
  resultat final valide selon `ValidationAgentResult`, scorer gele vert,
  evenement accepte par la garde et read-model autoritatif. Aucun second
  appel, retry, fallback, conversation, tour utilisateur ou contenu brut n'a
  ete produit ou conserve;
- Gemini high et Luna ne sont pas poursuivis. Aucun prompt, projection v2,
  hard guard, Presence, Stimmung, fallback, service voisin, 4S.0 ou lot
  ulterieur n'est modifie. 4C.1 est ferme; 4S.0 reste non commence.

Condition de la passe provider de fermeture:

- [x] Maximum v2 corrige et sensibilite aux vocabulaires autoritatifs livree.
- [x] Corpus, scorer, nombre d'appels, cout maximal et regle de decision figes avant resultats.
- [x] Comparaison primaire/fallback v1/v2 executee et artefact JSONL content-free archive.
- [x] Decision semantique finale `pass` sur la configuration live retenue,
  sans regression v2 et avec l'invariant critique 005 satisfait.
- [x] Suites completes, artefact contre-audite et runtime de campagne alors
  inchange prouves.

Condition de fermeture:

- [x] La reproduction rouge du compactage courant est conservee.
- [x] `stimmung_input` est transmis complet ou absent explicitement, jamais
  partiel.
- [x] La transmission ne depend plus de l'ordre lexical des autres sources.
- [x] La borne globale et tous les invariants voisins sont preserves.
- [x] Backend, reader, read-model, frontend et navigateur exposent la meme
  verite content-free.
- [x] Diff, tests, contre-audit, documentation, commit, push et livraison
  ciblee sont prouves.

Message de commit recommande: `fix: preserve Stimmung input for Validation`.

### Micro-lot 4S.0 - Corpus semantique multi-tours et scorer hermetique

Statut: ferme le 2026-08-30 apres validation humaine deleguee par Tof a Codex; 4S.1 non commence
Effort recommande: `extra high`
Nature: tests, fixtures et documentation seulement
Prerequis: 4C.1 ferme

Objectif exact: construire et faire valider humainement le corpus qui mesure la
qualite semantique du caller Stimmung sur plusieurs tours, sans appeler de
provider. Ce lot fixe les cas, les attentes et les seuils avant toute campagne,
afin d'interdire leur adaptation opportuniste apres lecture des resultats.

Corpus minimum: `12` a `16` dialogues synthetiques de `4` a `6` tours, couvrant
au moins emergence, stabilite, bascule, retour au neutre, alternance, intensite
sans changement epistemique, ironie, citation, affect rapporte, correction
explicite, question, demande, risque, action materielle, opportunite Presence et
contre-cas Presence. Un meme dialogue peut couvrir plusieurs familles, mais la
matrice doit prouver que chaque famille possede au moins un cas positif et un
contre-cas lorsque cela a un sens.

Schema obligatoire de chaque cas:

- identifiant stable, version et famille;
- tours synthetiques complets et ordre autoritatif;
- tonalites dominantes autorisees et interdites;
- presence, absence ou vide autorise du signal;
- trajectoire permise de stabilite, shift, volatilite et decroissance;
- attributions et psychologisations explicitement interdites;
- effet epistemique interdit lorsqu'aucune raison epistemique independante
  n'existe;
- relation attendue avec question, demande, risque, action et Presence;
- justification humaine courte de l'attente, sans recopier le prompt.

Scorer et sensibilite:

- evaluer des proprietes et ensembles bornes, jamais une chaine exacte;
- distinguer faux positif, faux negatif, surcodage, instabilite,
  psychologisation et confusion epistemique;
- fixer par famille les seuils d'acceptation primaire et fallback;
- rejeter les mutations: tour retire ou inverse, ironie attribuee, affect
  rapporte internalise, intensite transformee en incertitude, correction
  ignoree, Presence masquee et fail-open presente comme signal sain;
- ne pas recopier le caller, ses poids ou son prompt dans le scorer;
- n'inclure aucun contenu operateur, secret ou donnees live.

Passe technique du 29 aout 2026:

- inventaire confirme: les `24` cas diagnostiques et les `10` cas finaux
  historiques evaluent principalement un tour courant; leur scorer valide le
  schema et des tonalites attendues, mais pas une trajectoire dialogique;
- les goldens causaux Lot 4 traversent le vrai coordinateur, la sauvegarde fake,
  la reconstruction JSON, l'agregateur, le regime et Validation. Ils prouvent
  les raccords techniques, pas la justesse semantique du caller;
- F1 `valide`: corpus historiques principalement mono-tour; F2 `valide`: le
  scorer historique ne qualifie ni stabilite, bascule, volatilite, correction
  ni decroissance; F3 `valide`: les goldens techniques ne sont pas un examen
  semantique; F4 `valide`: certaines intentions historiques sont reutilisables,
  mais leur concatenation ne ferait pas un dialogue autoritatif; F5 `valide`:
  l'effet epistemique et le respect de Presence restent non observables depuis
  la seule sortie structuree du caller;
- architecture alors livree: corpus `stimmung_dialogic_corpus_v1`, seuils
  `stimmung_dialogic_thresholds_v1`, validateur ferme et scorer dedie sans
  transport provider. Un tour est une paire user/assistant complete; les `14`
  dialogues avaient chacun `4` tours, soit `56` paires et `28` etapes evaluees;
  empreinte corpus SHA-256
  `2e2262cba98469f804c3038cc692b62678b6a49ca384e1e5d53716388f9dc75e`;
- matrice candidate initiale:

  | Identifiant | Familles principales | Trajectoires evaluees |
  | --- | --- | --- |
  | `L4S0-ST-001` | emergence, stabilite, question | emerging -> stable |
  | `L4S0-ST-002` | bascule, correction | stable -> shifted |
  | `L4S0-ST-003` | retour neutre | stable -> decay |
  | `L4S0-ST-004` | alternance | stable -> alternating/volatile |
  | `L4S0-ST-005` | intensite sans effet epistemique | intensite faible -> forte |
  | `L4S0-ST-006` | ironie | literal -> ironic/shift |
  | `L4S0-ST-007` | citation | direct -> quoted/shift |
  | `L4S0-ST-008` | affect rapporte | direct -> reported/shift |
  | `L4S0-ST-009` | demande, contre-Presence | constat -> demande |
  | `L4S0-ST-010` | risque, contre-Presence | abstrait -> risque |
  | `L4S0-ST-011` | action materielle, contre-Presence | preparation -> action |
  | `L4S0-ST-012` | opportunite et contre-Presence | eligible -> question |
  | `L4S0-ST-013` | question, demande | narration -> sollicitation |
  | `L4S0-ST-014` | risque, action, Presence | eligible -> risque/action |

- chaque famille possede une preuve positive et un contre-cas structurel. Les
  attentes autorisent plusieurs tonalites raisonnables, bornent les forces et
  separent le signal par tour de l'agregat (`stability`, `shift_state`,
  decroissance); aucune phrase de sortie exacte n'est figee;
- la premiere passe avait applique le seuil `1.0` a toutes les familles et
  decrit toutes les tolerances zero comme directement scorables. C1 et C2
  ci-dessous corrigent cette surqualification avant toute campagne provider;
- mutations rejetees: tour retire, inverse ou duplique; ironie literalisee;
  citation ou affect rapporte internalise; intensite transformee en effet
  epistemique; correction ignoree; stable requalifie volatile; bascule effacee;
  alternance requalifiee stable; retour neutre sans decroissance; question,
  demande, risque ou action masques; Presence forcee ou opportunite supprimee;
  fail-open presente comme signal sain; couverture sans cas positif; sortie
  exacte ou champ libre ajoutes; tonalite hors ensemble dans le signal ou
  l'agregat; tonalite dupliquee; compte multi-tours sous-declare; sources
  primaire/fallback melangees; dialogue manque; seuil v1 abaisse sans
  versionnement;
- fichiers de preuve:
  `benchmark/suites/stimmung/dialogic_semantics.py`,
  `benchmark/suites/stimmung/fixtures/stimmung_dialogic_semantic_v1.json`,
  `app/tests/unit/golden/test_lot4s0_stimmung_dialogic_semantics.py` et
  `benchmark/README.md`;
- tests avant patch: Python `2759/2759`, JavaScript `137/137`, Chromium
  `19/19`; ciblage Stimmung historique `33/33`. Tests apres patch: nouveau
  contrat `9/9`, ciblage Stimmung/benchmark/goldens `42/42`, Python
  `2768/2768`, JavaScript `137/137`, Chromium `19/19`; aucun skip, todo ou
  expected failure;
- commandes hermetiques: conteneur local avec `--pull=never --network none
  --read-only`, depot entier monte en lecture seule, `/tmp` en tmpfs et
  `PYTHONDONTWRITEBYTECODE=1`. Chromium a reutilise la revision Playwright deja
  installee en cache read-only, sans installation ni telechargement. L'image
  Jammy locale a reproduit un SIGSEGV au lancement de Chromium sans echec
  d'assertion; la meme revision navigateur sous l'image Noble locale a passe
  les `19/19` sans modifier le depot;
- adaptations de runner: une premiere decouverte finale a conserve `2759`
  parce que `unit/benchmark` n'est pas decouvert; la preuve 4S.0 a donc ete
  placee sous `unit/golden`, sans modifier son contenu, puis la decouverte
  autoritative a obtenu `2768`. Deux tentatives non autoritatives d'agreger
  toutes les suites benchmark ont rencontre avant execution 4S.0 un import
  historique `identity_periodic` absent; le ciblage benchmark Stimmung reel
  est vert `16/16` et la decouverte autoritative complete est verte;
- contre-audit independant: les premieres versions laissaient passer une
  source melangee, un dialogue manque, un seuil abaisse, un surcodage, une
  tonalite dupliquee, une fausse decroissance et un compte multi-tours
  sous-declare. Chaque reproduction est devenue rouge sous le validateur ou le
  scorer partage; relecture finale sans finding bloquant;
- aucun provider, benchmark semantique live, secret, DB, donnee operateur,
  tour utilisateur, modification runtime, rebuild, restart ou deploiement;
- limite ouverte: la validation humaine des dialogues synthetiques et de leurs
  attentes reste a effectuer separement par Codex pour Tof. Cette passe ne
  mesure aucune qualite modele et ne commence ni 4S.1 ni 4C.2. Si 4S.1 reproduit
  ensuite un defaut semantique, le
  micro-lot correctif conditionnel 4C.2 devra synchroniser runtime, evenement,
  reader, read-model, surfaces frontend existantes et preuve navigateur.

Passe corrective du 30 aout 2026:

- C1 `valide`: le resume calculait auparavant des taux jusque `1.0` pour les
  familles question, demande, risque, action et Presence a partir de la seule
  sortie Stimmung. La preuve separe maintenant neuf familles directement
  mesurables, une famille mixte et six familles aval `not_measured`; aucune
  propriete aval ne contribue a la decision semantique du caller;
- C2 `valide`: des observations synthetiques pouvaient produire `pass` avec
  `provider_results_observed=false`. La decision est desormais obligatoirement
  `inconclusive` avec `provider_results_not_observed`; les tests de la branche
  `pass` indiquent explicitement une provenance provider vraie sans creer
  d'artefact ni pretendre qu'un appel a eu lieu;
- C3 `valide`: les quatorze cas avaient tous quatre tours et les premiers cas
  ironie/citation/affect rapporte donnaient des indices explicites. Les cas
  `L4S0-ST-015` (`5` tours) et `L4S0-ST-016` (`6` tours) ajoutent une ironie
  implicite et une attribution rapportee dependante du contexte, chacun avec
  preuve positive et contre-cas. Leur difficulte `hard`, politique
  `implicit_context_required`, profondeur et etapes evaluees sont fermees par
  le schema; aucune regex ne pretend juger leur francais;
- version corrective: les changements de schema de dialogue, de frontiere de
  mesure et de regle de decision sont publies comme
  `stimmung_dialogic_corpus_v2` / `stimmung_dialogic_thresholds_v2`, jamais
  reinterpretes comme v1. Le corpus v2 compte `16` dialogues, `67` paires et
  `32` etapes evaluees; son empreinte SHA-256 est
  `09a3e52e7ea10db05642e793b3c7fda2ffcc295d4efcc0c1041690922f10f3aa`;
- matrice ajoutee a la v2:

  | Identifiant | Famille | Profondeur et trajectoire |
  | --- | --- | --- |
  | `L4S0-ST-015` | ironie implicite | `5` tours, litteral -> contraste contextuel |
  | `L4S0-ST-016` | affect rapporte ambigu | `6` tours, direct -> attribution contextuelle |

- C4 `valide`: le scorer mono-tour rejetait depuis la premiere passe une
  tonalite dupliquee que le validateur runtime accepte puis deduplique. Son
  contrat historique est restaure; le scorer 4S.0 conserve localement la
  validation stricte d'une sortie caller deja normalisee. Une preuve traverse
  le vrai normaliseur runtime en lecture seule puis rejette un duplicat reinjecte
  apres cette frontiere;
- frontiere de mesure: `emergence`, `stabilite`, `bascule`, `retour_neutre`,
  `alternance`, `ironie`, `citation`, `affect_rapporte` et `correction` sont
  directement mesurees. `intensite_sans_effet_epistemique` est mixte: son
  intensite est mesuree, son absence d'effet epistemique reste contractuelle.
  Question, demande, risque, action materielle, opportunite/contre-Presence et
  non-psychologisation aval sont exclusivement contractuels;
- seuils v2: taux `1.0` inchanges pour le primaire et le fallback sur les neuf
  familles directement mesurables et la composante caller de la famille mixte;
  aucun taux pour les familles aval. Sans resultat provider, la decision et les
  taux mesures restent `inconclusive`/vides. Tout echec de sortie caller reste
  bloquant, meme dans un cas portant une famille aval;
- sensibilite ajoutee: rejet du retour a `pass` sans provider, d'un taux aval,
  d'une requalification aval comme mesurable, du retrait ou raccourcissement
  des cas `015/016`, d'une politique d'indice affaiblie, d'un duplicat restant
  apres normalisation et d'une baisse de seuil. Les mutations de la premiere
  passe restent actives;
- reproductions rouges: le ciblage `12` tests sur le HEAD initial a produit
  `6` echecs et `2` erreurs, couvrant le faux `pass`, les categories/taux aval,
  les deux dialogues absents et le rejet historique du duplicat;
- preuves apres correction: contrat 4S.0 `12/12`; contrat 4S.0 plus benchmark
  historique `19/19`; caller, agregateur, benchmark, golden causal Lot 4 et
  4S.0 `45/45`; decouverte Python `2771/2771` (delta exact `+3` tests),
  JavaScript `137/137`, Chromium `19/19`; zero echec, erreur, skip, todo ou
  expected failure;
- commandes hermetiques: image locale avec `--pull=never --network none
  --read-only`, depot entier monte en lecture seule, `/tmp` en tmpfs et
  `PYTHONDONTWRITEBYTECODE=1`. Chromium reutilise la revision locale en cache
  read-only sous l'image Noble, sans installation ni telechargement;
- fichiers autoritatifs corriges:
  `benchmark/suites/stimmung/dialogic_semantics.py`,
  `benchmark/suites/stimmung/fixtures/stimmung_dialogic_semantic_v2.json`,
  `app/tests/unit/golden/test_lot4s0_stimmung_dialogic_semantics.py` et
  `benchmark/README.md`;
- aucun provider, transport, artefact de campagne, runtime, prompt, modele,
  agregateur, observabilite produit, frontend, rebuild, restart ou deploiement;
- validation humaine toujours ouverte: elle sera realisee separement par Codex
  pour Tof apres ce retour. Cette passe ne coche pas la case humaine et ne
  commence ni 4S.1 ni aucun lot suivant.

Passe finale d'atteignabilite du 30 aout 2026:

- R1 `valide`: `_observations_for()` construit volontairement des objets depuis
  les attentes pour isoler les branches du scorer, mais cette commodite etait
  devenue l'unique preuve de satisfiabilite du corpus. La reproduction rouge a
  echoue sur l'absence du temoin runtime; la preuve autoritative utilise
  desormais `stimmung_dialogic_reachability_witness_v1`, le normaliseur produit
  et le vrai `build_stimmung_input`;
- R2 `valide`: apres deux signaux anxieux, une seule attenuation conserve
  legitimement `anxiete/stable/steady`. `L4S0-ST-003` compte maintenant six
  tours; la baisse intermediaire reste anxieuse dans le temoin et la preuve
  positive est placee au sixieme tour, lorsque neutralite et decroissance sont
  effectivement observables dans la fenetre runtime;
- R3 `valide`: `L4S0-ST-015` avait un premier succes puis deux echecs, malgre un
  bilan textuel de trois echecs. Le recit est corrige et une metadonnee fermee
  fige `1` succes, `2` echecs et leur ordre, sans inspection lexicale du
  francais;
- R4 `valide`: l'audit des `32` etapes confirme que plusieurs transitions sont
  introduites au tour preparatoire puis peuvent etre `steady` au tour evalue.
  Les cas concernes acceptent cet etat seulement lorsqu'un temoin runtime le
  produit; bascule et alternance conservent leurs exigences propres;
- R5 `valide`: les ensembles bornes acceptent desormais une anxiete attenuee
  pendant la baisse, la frustration raisonnable de la fatigue et, pour
  l'ironie apres echecs, frustration, colere ou decouragement. L'enthousiasme
  litteral reste interdit et tous les seuils restent `1.0`;
- R6 `valide`: le bandeau general, le statut du Lot 4 et le statut 4S.0 disent
  maintenant la meme verite: preuve technique livree, validation humaine en
  attente, 4S.1 non commence;
- preuve autoritative: le temoin versionne contient un signal synthetique
  normalise pour chacun des `69` tours des `16` dialogues. Les signaux sont
  attaches aux metadonnees de vrais messages user/assistant synthetiques; les
  tours non evalues sont conserves; les `32/32` etapes passent le scorer avec
  l'agregat produit exclusivement par `build_stimmung_input`. Le temoin est
  marque `provider_input=false`, n'est jamais une sortie provider revendiquee
  et n'est pas une entree de la future campagne 4S.1;
- empreintes SHA-256: corpus v2
  `5059d5ea4b57409bc08ee95dae39f74b2411268dcf5fe6aee516dd9ffb310ee5`;
  temoin d'atteignabilite
  `e52a2089d53db59c2e46129599e2aefec4404d6ab6f9ef0ded56ac3e84d9117d`;
- sensibilite ajoutee: rejet d'un agregat relu depuis l'attente, d'un signal
  non evalue retire, de deux signaux inverses, d'un signal duplique, du retour
  neutre premature de `003`, des trois echecs fictifs de `015`, du rejet de
  `steady` lorsqu'il est produit et de l'enthousiasme litteral sur l'ironie.
  Les mutations des deux passes precedentes, le seuil `1.0`, l'absence de faux
  `pass` sans provider et la frontiere aval `not_measured` restent verrouilles;
- fichiers de preuve ajoutes ou ajustes:
  `benchmark/suites/stimmung/fixtures/stimmung_dialogic_reachability_witness_v1.json`,
  `benchmark/suites/stimmung/fixtures/stimmung_dialogic_semantic_v2.json`,
  `benchmark/suites/stimmung/dialogic_semantics.py`,
  `app/tests/unit/golden/test_lot4s0_stimmung_dialogic_semantics.py` et
  `benchmark/README.md`;
- tests avant patch: Python `2771/2771`, JavaScript `137/137`, Chromium
  `19/19`. Reproduction rouge R1: `1` echec attendu, temoin absent. Apres
  correction: contrat 4S.0 `14/14`; contrat, benchmark, caller, agregateur et
  golden causal voisins `47/47`; decouverte Python `2773/2773`, JavaScript
  `137/137`, Chromium `19/19`; aucun echec, erreur, skip, todo ou expected
  failure;
- commandes hermetiques: depot entier monte en lecture seule, `--network none`,
  `/tmp` en tmpfs, `PYTHONDONTWRITEBYTECODE=1`; revision Chromium locale
  reutilisee en lecture seule sans installation ni telechargement;
- aucun provider, faux resultat provider, regex, runtime, prompt, modele,
  agregateur, frontend, observabilite produit, DB, rebuild, restart ou
  deploiement. La validation humaine reste la seule condition ouverte et sera
  realisee separement par Codex pour Tof apres ce retour; 4S.1 reste non
  commence.

Validation humaine finale du 30 aout 2026:

- Tof a explicitement delegue a Codex la relecture humaine finale du corpus et
  a autorise sa fermeture documentaire apres un audit independant;
- Codex a relu integralement les `16` dialogues, leurs `69` paires
  user/assistant synthetiques, leurs `32` attentes evaluees, les equivalences
  affectives admises et les contre-cas. Aucun finding bloquant ne subsiste;
- les trajectoires emergence, stabilite, bascule, decroissance et alternance
  sont semantiquement coherentes. L'ironie implicite `015` respecte le bilan
  factuel `1` succes puis `2` echecs; l'affect rapporte `016` reste attribue au
  tiers; `003` n'exige la neutralite qu'apres une decroissance multi-tours;
- la relecture confirme la frontiere de preuve: le caller peut etre score sur
  ses signaux et leur agregat, tandis que question, demande, risque, action,
  Presence, non-psychologisation aval et effet epistemique restent
  `not_measured` tant qu'une preuve aval distincte n'existe pas;
- verification independante: golden 4S.0 `14/14`, decouverte hermetique Python
  `2773/2773`, `git diff --check` propre, HEAD/upstream alignes `0/0`, runtime
  HTTP `200`, healthy, restart `0`, OOM false et strictement inchange;
- decision: corpus v2 humainement valide, seuils `1.0` conserves, 4S.0 ferme.
  Cette validation n'est pas un resultat provider et ne commence pas 4S.1.

Condition de fermeture:

- [x] Le corpus versionne couvre toutes les familles imposees.
- [x] Les attentes et seuils sont fixes avant toute execution provider.
- [x] Les validateurs rejettent au moins une mutation controlee par famille.
- [x] Les tests hermetiques et la decouverte complete sont verts.
- [x] La relecture humaine finale, explicitement deleguee par Tof a Codex, a
  valide le corpus avant 4S.1.
- [x] Documentation, commit et push sont prouves; runtime inchange.

Message de commit recommande: `test: define Lot 4 Stimmung semantic corpus`.
Message de commit de la passe corrective:
`test: correct Lot 4S.0 semantic proof boundaries`.
Message de commit de la preuve d'atteignabilite:
`test: make Lot 4S.0 corpus runtime-reachable`.

### Micro-lot 4S.1 - Campagne provider primaire et fallback

Statut: ferme le 2026-08-30; campagne complete, decision `strengthen`; 4C.2 active comme prochain micro-lot et non commence
Effort recommande: `extra high`
Nature: benchmark borne, artefacts content-free et documentation
Prerequis: 4S.0 ferme et corpus valide humainement

Objectif exact: executer le caller courant sur le corpus 4S.0 avec son primaire
et son fallback reels, puis mesurer separement leur qualite, leur latence, leur
cout et leurs erreurs. La campagne qualifie le caller; elle ne modifie aucun
runtime et n'appelle ni Validation ni le modele principal.

Protocole obligatoire:

- relire depuis les settings courants les modeles, provider, timeout et niveau
  de raisonnement; ne rien modifier pendant la campagne;
- executer primaire et fallback separement, sans presenter le fallback comme
  primaire ni un fail-open comme reussite neutre;
- ne jamais appeler une DB ou une donnee operateur;
- borner et compter les appels avant lancement;
- conserver un JSONL date, versionne et content-free avec identifiant de cas,
  hash du corpus, modele, source, statut, reason code, scores, latence et cout;
- ne conserver ni dialogue brut, ni prompt complet, ni reponse brute, ni
  secret dans l'artefact durable ou le retour utilisateur;
- ne pas abaisser les seuils fixes en 4S.0 apres lecture des resultats;
- distinguer erreurs transport, timeout, schema, refus et resultat semantique
  insuffisant.

Sortie obligatoire:

- `keep_current` si primaire et fallback franchissent leurs seuils;
- `strengthen` avec activation de 4C.2 si au moins un defaut semantique du
  caller est reproduit et localise;
- `inconclusive` si l'infrastructure de campagne ou le corpus ne permet pas de
  conclure, sans modifier le caller.

Condition de fermeture:

- [x] GO provider distinct trace.
- [x] Primaire et fallback mesures separement sur le corpus fige.
- [x] Artefact JSONL content-free, seuils, couts, latences et echecs archives.
- [x] Aucun modele, prompt, provider, setting ou runtime modifie.
- [x] Decision sur 4C.2 documentee, commit et push prouves.

Gel du protocole du 30 aout 2026, avant tout resultat provider:

- raccord minimal: `benchmark/suites/stimmung/dialogic_campaign.py` reutilise
  le transport OpenRouter benchmark, le prompt et le constructeur de messages
  de production, le normaliseur du caller, `build_stimmung_input` et le
  corpus/scorer 4S.0; le temoin d'atteignabilite reste tests-only et ne peut
  remplacer un resultat provider;
- corpus, attentes et seuils v2 inchanges: `16` dialogues, `69` tours et `32`
  etapes evaluees; primaire et fallback sont appeles explicitement et
  separement sur deux repetitions;
- modeles et parametres relus: primaire
  `google/gemini-3.1-flash-lite`, fallback `openai/gpt-5.4-nano`, timeout
  `10 s`, `temperature=0.1`, `top_p=1.0`, `max_tokens=220`; aucun niveau de
  raisonnement explicite;
- ordre et plafond fermes: `69 x 2 sources x 2 repetitions = 276` appels,
  plafond absolu identique, aucun retry, fallback automatique, Batch, Flex ou
  Priority; chaque requete fixe `provider.allow_fallbacks=false`;
- prix OpenRouter observes le `2026-08-30T10:15:12Z`: primaire
  `0.25/1.50 USD` par million de tokens entree/sortie, fallback
  `0.20/1.25 USD`; estimation maximale prudente `0.15901050 USD`, sous le
  plafond fige `0.30 USD`;
- empreinte du protocole sur le commit de gel pousse
  `c02e1dd7ad53c6eb33296c563304c5e4d7be3f7e`:
  `62059e68feaa7d9ed04584306b81cf337be76b0932620f924db7b47b49875d05`;
- preuves hermetiques: `7/7` nouveaux tests et `54/54` suites Stimmung,
  agregateur, benchmark et goldens voisines. Les mutations rejettent inversion
  de modele, fallback provider cache, ordre/appel/aggregate altere, fail-open
  maquille, champ brut, reason code libre, metrique absente et decision issue
  d'un echec non reproductible;
- aucune sortie provider n'a ete lue pendant cette phase. Le commit pousse de
  gel devient l'unique baseline autorisee de la campagne; le corpus, le
  scorer, le prompt, les parametres, les regles de decision et le harness
  provider-visible ne seront plus ajustes apres le premier resultat.

Campagne provider du 30 aout 2026, depuis le commit de gel
`c02e1dd7ad53c6eb33296c563304c5e4d7be3f7e`:

- execution complete: `276/276` appels, soit `138/138` pour chaque source;
  aucun retry, appel automatique de l'autre source, Batch, Flex ou Priority;
  aucun appel Validation ou modele principal;
- transport: les `276` appels sont `ok`, avec modele et provider observes
  conformes; zero timeout, refus, JSON invalide, schema invalide ou erreur de
  transport. Les deux repetitions sont completes;
- primaire `google/gemini-3.1-flash-lite`: `16/16` dialogues en echec a chaque
  repetition, `32` echecs semantiques; `15/16` paires ont exactement la meme
  classification et les memes reason codes, et les `16/16` conservent au moins
  un reason code commun; latence mediane `847.835 ms`, p95 `1530.581 ms`,
  `85 013` tokens, cout `0.03405450 USD`;
- fallback `openai/gpt-5.4-nano`: `14/16` dialogues en echec a chaque
  repetition, `28` echecs semantiques; `9/16` paires sont exactement stables
  et `12` echecs ont au moins un reason code commun aux deux repetitions;
  latence mediane `1040.144 ms`, p95 `1870.386 ms`, `80 899` tokens, cout
  `0.02728145 USD`;
- cout total observe `0.06133595 USD`, sous le plafond `0.30 USD`; `165 912`
  tokens totaux. Les metriques absentes ne sont jamais fabriquees a zero;
- decision `strengthen`: au moins un defaut semantique borne est reproduit sur
  le meme cas et la meme source aux deux repetitions. Les echecs isoles ou
  instables restent visibles, mais la regle gelee ne leur permet pas d'effacer
  un defaut reproductible deja localise;
- localisation content-free: le primaire reproduit au moins une classe
  d'echec bornee sur `L4S0-ST-001` a `L4S0-ST-016`; le fallback sur
  `L4S0-ST-002`, `003`, `004`, `006`, `007`, `008`, `009`, `010`, `011`,
  `013`, `014` et `016`. Les classes detaillees restent reconstructibles
  depuis les `dialogue_score` de l'artefact, sans dialogue ni sortie brute;
- le contre-audit independant a corrige uniquement le post-traitement qui
  exigeait a tort que tous les echecs soient apparies. Les `276` lignes
  provider sont restees strictement identiques (SHA-256 du bloc:
  `4a2caf08577b7abbe4a163386d025ba9bcc5c639a5156720f20d1316569ddf53`),
  aucun seuil, corpus, prompt, parametre ou resultat provider n'a change et
  aucun nouvel appel n'a ete lance;
- consequence: 4C.2 est active comme prochain micro-lot, ouvert et non
  commence. Cette preuve n'autorise aucune correction du caller dans 4S.1 ni
  aucun changement de modele, prompt ou setting;
- artefact content-free:
  `benchmark/results/stimmung/2026-08-30-lot4s1-stimmung-primary-fallback.jsonl`,
  `347` lignes (`276` appels, `64` scores dialogue, `7` syntheses), SHA-256
  `97b5d53548c15b045593bc1f9c897f50f88d1553f05e9a75d0fdf4ceaa23467e`;
  reconstruction `276` appels / `64` scores / `strengthen` sans nouvel appel;
- contenu retenu: categories affectives bornees, agregats reconstruits,
  statuts, reason codes fermes, route, latence, tokens, couts et empreintes;
  aucun dialogue, prompt, reponse brute, exception brute, raisonnement, secret
  ou donnee operateur;
- tests: baseline avant patch Python `2773/2773`, JavaScript `137/137` et
  Chromium `19/19`; apres campagne, reconstruction 4S.1 `8/8`, ciblage
  Stimmung/agregateur/benchmark/goldens `55/55`, decouverte Python complete
  `2781/2781` (delta exact `+8`), zero echec, erreur, skip, todo ou expected
  failure. JavaScript et Chromium ne sont pas repetes apres resultats car aucun
  runtime, contrat frontend ou fixture frontend n'a change;
- sensibilite: rejet d'un corpus/prompt/parametre/hash divergent, des modeles
  inverses, du fallback provider automatique, d'un appel retire/ajoute/inverse,
  d'un agregat fabrique, d'un fail-open ou JSON invalide score comme succes,
  d'un champ brut/reason code libre, d'une metrique absente fabriquee a zero,
  de `keep_current` sous un seuil manque, de `strengthen` depuis un echec
  isole, d'une empreinte de protocole auto-coherente mais fausse, d'une route
  observee inconnue presentee comme `ok`, et d'un defaut reproductible masque
  par un echec isole;
- runtime strictement inchange; aucun rebuild, restart, deploiement, tour
  utilisateur, DB ou donnee operateur. 4C.2 et les micro-lots suivants ne sont
  pas commences.

Message de commit recommande: `benchmark: evaluate Stimmung semantic corpus`.

### Micro-lot 4C.2 - Renforcement semantique conditionnel du caller

Statut: ferme le 2026-08-30; prompt renforce v2 qualifie et livre, 4C.3 non commence
Effort recommande: `extra high`
Nature: correctif caller borne, observabilite synchrone et preuves
Prerequis: decision `strengthen` de 4S.1 localisant un defaut du caller

Ce micro-lot ne doit pas commencer si 4S.1 donne `keep_current`. Dans ce cas il
est ferme `non requis` avec le chemin de preuve. S'il est active, son objectif
est de corriger uniquement les familles semantiques echouees, une variable a la
fois.

Ordre de decision impose:

1. verifier schema local, contrat et prompt courant;
2. proposer le plus petit renforcement du contrat ou du prompt;
3. ne considerer un changement de modele qu'apres echec mesure du renforcement
   a modele constant, dans une decision distincte et explicitement approuvee;
4. ne jamais changer simultanement prompt, modele et niveau de raisonnement;
5. reexecuter tout le corpus primaire/fallback, pas seulement les cas corriges.

Invariants:

- aucune regex affective, aucun nouveau caller ou stage;
- aucune Identity, psychologisation ou diagnostic durable;
- fail-open, cadence, schema borne et absence de souverainete epistemique
  preserves;
- settings, events, read-models, surfaces frontend existantes et tests
  navigateur synchronises si prompt, modele ou provenance change;
- aucune campagne live sur des donnees operateur.

Condition de fermeture:

- [x] Activation justifiee par des cas rouges 4S.1 precis.
- [x] Une seule variable architecturale change par passe.
- [x] Tous les seuils de la source couverte par la porte finale sont franchis;
  le fallback historique, non rappele par cette passe primaire-only, reste
  explicitement hors de cette preuve et inchange.
- [x] Aucun cas auparavant valide ne regresse.
- [x] Observabilite, tests, documentation, commit, push et livraison ciblee
  sont prouves.

Passe A de diagnostic et gel, executee le 2026-08-30 avant tout appel
provider:

- l'artefact 4S.1 autoritatif reste inchange (SHA-256
  `97b5d53548c15b045593bc1f9c897f50f88d1553f05e9a75d0fdf4ceaa23467e`):
  `276/276` appels valides, primaire en echec reproductible sur `16/16`
  dialogues et fallback sur `12/16`; la decision `strengthen` active donc
  honnetement 4C.2;
- matrice content-free de localisation:

  | finding | primaire | fallback | frontiere prouvee | classement |
  | --- | --- | --- | --- | --- |
  | F1 surcodage | `signal_overcoded` 14 fois, `aggregate_overcoded` 18 fois | 19 et 14 fois | signal local puis propagation multi-tours | valide |
  | F2 force | `strength_outside_allowed` 14 fois | 4 fois | sortie locale evaluee | valide |
  | F3 trajectoires | stabilite 10 fois, shift 13 fois, decay 2 fois | stabilite 13 fois, shift 13 fois | agregat reel reconstruit depuis les signaux caller | valide comme consequence, agregateur non incrimine |
  | F4 attribution | pas de code direct, mais agregats hors attente sur les cas concernes | citation internalisee 2 fois et affect rapporte 4 fois | signal local du fallback; primaire seulement partiel | valide pour le fallback, partiel pour le primaire |
  | F5 ironie | surcodage/force/trajectoire reproductibles | literalisation une fois seulement | erreur locale plausible, literalisation non stable entre repetitions | partiel |
  | F6 actes dialogiques | faux negatifs et surcodage sur les cas neutres/actionnels | surcodage reproductible | signal local mesurable; effet aval question/demande/risque/action/Presence non mesure | partiel |
  | F7 frontiere de cause | le temoin 4S.0 passe les 32 etapes via le vrai agregateur | meme autorite | corpus et agregateur atteignables; les erreurs locales sont caller, certaines erreurs agregees restent derivees | nuancee et localisee |

- variable unique: un prompt candidat benchmark-only de `2457` octets precise
  la parcimonie des tonalites, la calibration de force, l'attribution des
  affects cites/rapportes, la lecture contextuelle de l'ironie et l'absence
  d'affect deduit du seul acte dialogique. Le schema, la taxonomie, le
  normaliseur, l'agregateur, les modeles et tous les parametres restent
  inchanges;
- gel versionne:
  `stimmung_semantic_strengthening_candidate_v1.txt` (SHA-256
  `e1ce1bd0490a3f6ef0757a63768d0c32a1c277db4636c2b33ba0cafd793ed0c7`)
  et `stimmung_semantic_strengthening_freeze_v1.json`; le manifeste verrouille
  aussi le prompt runtime historique, le corpus, le scorer, le normaliseur,
  l'agregateur, le harness et l'artefact temoin;
- protocole: `16` dialogues, `69` tours, `32` etapes evaluees, primaire et
  fallback separes, deux repetitions, exactement `276` appels et aucun retry
  ou fallback automatique; modeles, timeout `10 s`, `temperature=0.1`,
  `top_p=1.0` et `max_tokens=220` inchanges; cout maximal prudent
  `0.17989163 USD`, sous le plafond `0.30 USD`;
- decision gelee: `pass` seulement si les `64` scores dialogue (deux sources,
  deux repetitions) franchissent tous les seuils `1.0` sans regression d'un
  cas historiquement valide; toute insuffisance semantique vaut `fail`, toute
  preuve incomplete ou invalide vaut `inconclusive`;
- preuves Phase A: cycle rouge sur le raccord 4C.2 absent, puis `7/7` tests du
  gel/candidate, `103/103` tests 4S.0/4S.1/caller/agregateur/goldens et garde
  d'observabilite voisins, decouverte Python `2788/2788` et dry-run `ready` a
  `276` appels. Aucun provider, runtime, prompt actif,
  observabilite produit, frontend, DB, rebuild, restart ou deploiement avant
  le commit de gel.

Passe B provider executee depuis le gel pousse
`d69dc8b21e3df9bf4989a407e257c70a8305255d`:

- `276/276` appels executes une seule fois, sans retry ni fallback automatique;
  cout observe `0.07247940 USD`, sous le plafond; artefact content-free
  `2026-08-30-lot4c2-stimmung-strengthening-candidate.jsonl`, SHA-256
  `637cbc1fac2b03378f451d6fc64f6b0c30b7d9cd183b59b5833e3ee62612c5c5`;
- primaire: `138/138` transports et schemas valides, mais `11/16` dialogues en
  echec a chacune des deux repetitions; cinq dialogues auparavant en echec
  passent dans chaque repetition, sans regression relative observee;
- fallback: `137/138` appels valides et une erreur de schema bornee; `12/16`
  dialogues echouent en repetition 1, puis `11` echouent et un reste
  `inconclusive` en repetition 2; cinq transitions relatives deviennent
  `pass`, une transition auparavant valide devient `fail`;
- les echecs reproductibles restants concernent surtout les trajectoires
  `shift/stability`, les dominantes et agregats hors attente, avec encore du
  surcodage, une force hors borne et de l'affect cite/rapporte internalise;
  aucune des deux sources n'atteint les seuils stricts `1.0`;
- la regle gelee classe la campagne `inconclusive` a cause de l'unique sortie
  fallback invalide; les echecs semantiques complets du primaire prouvent en
  outre que la candidate ne satisfait pas la porte de livraison. La passe
  corrective content-free du 2026-08-30 conserve les `276` lignes d'appel
  byte-for-byte, expose `semantic_regression_count=1` pour la regression
  fallback deja prouvee et `semantic_regression_count_complete=false` parce
  que la sortie invalide empeche un decompte total. Une preuve incomplete ne
  fabrique donc plus un faux zero;
- Phase C interdite: le prompt runtime, les modeles, les parametres, le schema,
  le normaliseur, l'agregateur, l'observabilite produit et le frontend restent
  inchanges; aucun rebuild, restart ou deploiement. 4C.2 reste ouvert et 4C.3
  n'est pas commence;
- preuves finales: artefact reconstruit sans reseau, `8/8` tests 4C.2,
  `104/104` tests Stimmung/benchmark/goldens/garde d'observabilite voisins et
  decouverte Python `2789/2789`; aucun nouveau skip, todo ou expected failure.

Passe de comparaison de modele primaire gelee le 2026-08-30, avant tout
nouveau resultat provider:

- variable unique: le primaire candidat `google/gemini-3.7-flash` standard,
  effort `medium`, est compare au temoin primaire 4S.1 conserve. Le prompt
  runtime, le corpus, les `32` attentes, le scorer, le schema, le normaliseur,
  le vrai agregateur et les seuils `1.0` restent byte-for-byte inchanges; la
  candidate de prompt precedente est explicitement exclue;
- raccord natif: `reasoning.effort=medium`, `exclude=true`, sampling omis,
  `provider.allow_fallbacks=false`, `require_parameters=true`, aucun Batch,
  Flex ou Priority. Le timeout reste `10 s`; la borne de sortie `400` conserve
  46% de marge sur le maximum structure Gemini medium de `274` tokens deja
  observe dans les preuves du depot sans depasser le budget autorise;
- metadonnees OpenRouter relevees le `2026-08-30T14:52:34Z`: slug standard et
  providers Google disponibles, contexte et sortie largement superieurs au
  besoin; prix geles `0.75 USD/M` tokens entree et `3.75 USD/M` tokens sortie,
  y compris raisonnement interne selon le contrat courant;
- protocole: `69` tours x `2` repetitions = exactement `138` appels candidat,
  plafond absolu identique, aucun retry et aucun rappel du primaire historique
  ni du fallback. Estimation prudente, marge de 10% incluse:
  `0.29302680 USD`, sous le plafond `0.30 USD`;
- decision gelee: `eligible_primary` seulement avec `32/32` scores a `1.0`
  dans les deux repetitions, aucune erreur, provenance complete et aucune
  regression d'un cas primaire historique valide; sinon `not_eligible` pour
  un defaut semantique complet ou `inconclusive` pour une preuve incomplete;
- sensibilite: rejet du prompt candidat precedent, de toute difference hors
  allowlist de politique modele, du sampling, d'un effort autre que `medium`,
  d'une route non standard, d'un fallback automatique, d'une provenance
  incoherente, d'un appel manquant/ajoute, d'un contenu brut et d'une fausse
  eligibilite. Le dry-run hermetique annonce `138` appels et aucun provider n'a
  encore ete appele par cette passe;
- ce gel est benchmark/tests/docs-only: aucun modele runtime, prompt, fallback,
  setting, agregateur, observabilite produit, frontend, rebuild, restart ou
  deploiement n'est modifie. 4C.2 reste ouvert et 4C.3 non commence.

Campagne de comparaison executee une seule fois depuis le gel pousse
`1e9bb9f99c8a5bd73af855e3dc6dbedf211aa5b7`:

- protocole SHA-256
  `39dc5e908b828bc89d7064496988765a3255e809e09f9bdc069556f814d2bfe2`;
  `138/138` appels Gemini 3.7 medium executes, aucun retry, aucun appel du
  primaire historique ou du fallback et route Google demandee/observee sur
  les `138` lignes;
- `114/138` sorties JSON/schema valides et `24` erreurs `invalid_json`
  bornees. Les metriques sont toutes presentes, mais ces erreurs rendent neuf
  scores dialogue inconclusifs; elles ne sont jamais transformees en signal
  sain ni score semantique;
- scores: `5/32` pass, `18/32` fail et `9/32` inconclusive; sept dialogues ont
  un echec semantique reproductible. Les codes dominants restent les
  trajectoires de stabilite/shift, puis force et agregat hors attente. Le
  temoin Gemini 3.1 historique avait `0/32` pass; la preuve candidate ne permet
  pourtant pas de conclure a une eligibilite complete;
- decision gelee: `inconclusive`, et non `eligible_primary`; cout observe
  `0.19883025 USD`, latence mediane/p95 `3298.835/5301.780 ms`, tokens
  entree/sortie/raisonnement/total `74772/38067/29093/112839`;
- artefact content-free
  `2026-08-30-lot4c2-stimmung-gemini-3-7-medium.jsonl`, SHA-256
  `5adb54eec321f671fb05e2b350d35120a7ce84a52e7b936c4e54829002bce8f3`,
  reconstruit sans nouvel appel depuis les `138` lignes et les empreintes
  gelees;
- preuves: `84/84` tests cibles et voisins avant campagne, `6/6` goldens de
  comparaison avec artefact retenu, puis decouverte Python complete
  `2795/2795`, sans echec, erreur, skip, todo ou expected failure. JavaScript
  `137/137` et Chromium `19/19` ont ete revalides sur la baseline; ils ne sont
  pas rejoues apres resultat car aucun runtime, contrat frontend ou asset ne
  change;
- aucune decision de cutover n'est produite par le benchmark. Le primaire
  live, le prompt runtime et le fallback restent inchanges; les limites du
  fallback 4S.1 ne sont ni retestees ni acceptees. 4C.2 reste ouvert pour une
  decision humaine ulterieure et 4C.3 n'est pas commence.

Passe corrective de plafond gelee le 2026-08-30, avant tout nouvel appel
provider:

- hypothese reproduite content-free depuis l'artefact a 400: les `24/24`
  erreurs `invalid_json` portent `396` tokens de completion, sans timeout ni
  erreur transport; leurs tokens de raisonnement sont compris entre `326` et
  `384` (mediane `380.5`), contre une mediane `171` pour les sorties valides.
  Cette signature est fortement compatible avec une saturation du plafond,
  mais l'artefact historique ne conservait pas de finish reason et ne suffit
  donc pas seul a prouver la cause;
- variable provider-visible unique: `max_tokens` passe de `400` a `800`.
  Modele `google/gemini-3.7-flash`, effort `medium`, `exclude=true`, timeout
  `10 s`, sampling omis, prompt runtime, messages, corpus, scorer,
  normaliseur, agregateur, ordre et deux repetitions restent inchanges;
- le schedule derive du protocole 400 et contient exactement `69 x 2 = 138`
  appels du primaire candidat, aucun fallback, retry, appel Gemini 3.1,
  Validation ou modele voisin. Toute difference de requete hors
  `max_tokens` est rejetee;
- l'artefact v2 ajoute seulement les categories content-free bornees
  `finish_reason` et `native_finish_reason`; les valeurs non reconnues sont
  `unknown`, jamais du texte libre. L'artefact 400 historique reste lisible et
  byte-for-byte inchange;
- prix releves le `2026-08-30T15:48:43Z`: `0.75 USD/M` tokens entree et
  `3.75 USD/M` tokens sortie, raisonnement interne compris. Le maximum dur
  reproductible est `0.47338800 USD` pour `79184` tokens entree estimes et
  `138 x 800` tokens sortie, sous le plafond absolu `0.50 USD`;
- decision gelee: `eligible_primary` exige `138/138` appels valides et les
  `32/32` scores a `1.0` dans les deux repetitions, sans regression ni
  provenance incomplete; un defaut semantique reproductible vaut
  `not_eligible`, toute erreur ou sortie invalide vaut `inconclusive`. La
  disparition des JSON invalides ne suffit jamais a l'eligibilite;
- cycle rouge puis vert: preuve initialement absente, puis rejet du mauvais
  plafond, d'un effort ou d'une difference hors allowlist, d'un finish reason
  libre, d'un appel manquant et d'une fausse eligibilite. Aucun provider
  n'avait encore ete appele a ce stade du gel; runtime, prompt, fallback,
  settings et 4C.3 restaient inchanges.

Campagne corrective executee depuis le gel pousse
`08da24a706d9701d46f0c9e8b63b303a114eeb1a`:

- protocole SHA-256
  `0c529b3bb4b63de8f6ecd5bcc8b7ac369e56daa7c1587a7b1e88beb272f3401a`;
  `138/138` appels uniformes Gemini 3.7 medium a `max_tokens=800`, aucun
  retry, fallback, Gemini 3.1 ou autre caller;
- `137/138` JSON/schema valides. Vingt-trois des vingt-quatre erreurs a 400
  disparaissent; l'unique erreur restante appartenait deja aux cas coupes et
  porte `finish_reason=length`, `native_finish_reason=length`, `796` tokens de
  completion dont `765` de raisonnement. F1 et F2 sont donc valides, F3 est
  invalide comme garantie absolue, et F5 est ferme par la provenance de fin de
  generation maintenant bornee;
- les `32` scores complets contiennent `5` pass et `27` fail, dont `12`
  dialogues en echec reproductible. Les codes dominants restent force hors
  attente (`13`), stabilite (`14`), surcodage agrege (`10`) et shift (`7`):
  F4 est valide, la disparition presque complete des troncatures ne suffit pas
  a l'eligibilite semantique;
- decision gelee `inconclusive` en raison de l'unique JSON invalide, jamais
  transforme en signal ou score sain. Cout `0.22071900 USD`, latence
  mediane/p95 `3463.583/6032.503 ms`, tokens
  entree/sortie/raisonnement/total `74772/43904/33865/118676`;
- artefact content-free
  `2026-08-30-lot4c2-stimmung-gemini-3-7-medium-max800.jsonl`, SHA-256
  `1b6112ceea8d6065aabd34f579f64ccfe652f514b5187cd0d2c3da542ebf11fd`,
  reconstructible depuis le protocole pousse et les `138` lignes;
- preuves finales: `10/10` goldens de comparaison, suites Stimmung et Lot 4
  voisines vertes, puis decouverte Python complete `2799/2799`, sans echec,
  erreur, skip, todo ou expected failure. JavaScript `137/137` et Chromium
  `19/19` ont ete revalides sur la baseline; ils ne sont pas rejoues apres
  campagne, aucun contrat runtime/frontend ni asset n'ayant change;
- aucun fallback, modele runtime, prompt, agregateur, setting, rebuild,
  restart ou deploiement n'est modifie. 4C.2 reste ouvert pour decision
  humaine separee et 4C.3 reste non commence.

Passe candidate Claude Sonnet 5 gelee le 2026-08-30 avant tout resultat
provider:

- les campagnes Gemini 3.7 a 400 puis 800 tokens restent les autorites
  historiques; aucune variante Gemini, aucun primaire historique et aucun
  fallback ne sont rappeles. Le constat acquis reste `137/138` JSON valides a
  800 tokens, une fin `length`, seulement `5/32` scores conformes et `12`
  dialogues en echec reproductible;
- variable semantique unique: tuple natif du candidat primaire standard
  `anthropic/claude-sonnet-5`, endpoint Anthropic explicitement ordonne,
  effort `medium`, raisonnement exclu, `max_tokens=16000`, timeout `30 s`,
  JSON Schema strict, sampling et outils absents, fallback et retry interdits.
  Le prompt runtime, le corpus v2, les attentes, le scorer, les seuils `1.0`,
  le schema metier, le normaliseur et `build_stimmung_input` restent
  byte-for-byte inchanges;
- metadonnees publiques OpenRouter relevees le `2026-08-30T16:43:40Z`: slug
  canonique `anthropic/claude-sonnet-5-20260630`, contexte `1000000`, sortie
  maximale `128000`, sorties structurees et effort `medium` disponibles sur
  le endpoint Anthropic direct; prix geles `2 USD/M` tokens entree et
  `10 USD/M` tokens sortie;
- maximum structurel derive du contrat produit et des neuf tonalites:
  `418` caracteres JSON compacts, `462` espaces normalement et `676` indentes.
  La reserve finale est `1024` tokens et laisse `14976` tokens au raisonnement
  adaptatif. Pour `79184` tokens d'entree estimes, majores de `30%`, le maximum
  theorique est `22.285880 USD`; marge de campagne `10%` incluse,
  `24.514468 USD`, sous le plafond absolu `25 USD`. L'estimation realiste
  gelee a `4096` tokens de completion par appel est `5.858360 USD`;
- protocole: `16` dialogues, `69` tours, `32` etapes, deux repetitions,
  exactement `138` appels Sonnet, zero Gemini, GPT-5.4 Nano, fallback, retry,
  Batch, Flex, Priority, outil, DB ou donnee operateur. L'allowlist prouve que
  seules les proprietes natives du tuple modele different du temoin;
- decision gelee: `eligible_primary` exige `138/138` appels complets avec
  `finish_reason=stop`, provenance Anthropic, metriques completes, `32/32`
  scores a `1.0` et aucune regression historique; un defaut semantique complet
  vaut `not_eligible`, toute preuve technique incomplete vaut `inconclusive`;
- cycle TDD: reproduction rouge du raccord absent, puis six preuves vertes du
  schema derive, du schedule, de la route, du normaliseur produit, du vrai
  agregateur, du scorer et de la decision stricte. Le dry-run annonce
  exactement `138` appels et aucun provider n'a encore ete appele dans cette
  passe. Runtime, frontend et 4C.3 restent inchanges.

Resultat de la campagne candidate Sonnet 5 executee depuis le gel pousse
`306d08773beeb80eeb888f784a4dfe5ae2442fcc`:

- les `138/138` appels prevus ont ete executes une seule fois, uniquement vers
  `anthropic/claude-sonnet-5` sur le endpoint Anthropic. Les `138` retours sont
  JSON, schema et metier valides, avec `finish_reason=stop`; aucun Gemini,
  GPT-5.4 Nano, fallback, retry, outil ou autre caller n'a ete appele;
- provenance complete: modele et provider observes conformes, effort `medium`
  demande, raisonnement exclu, JSON Schema strict, sampling absent. OpenRouter
  rapporte `0` token de raisonnement; cette metrique observee ne remplace pas
  la preuve du parametre demande. Le p95 est `27588.288 ms`, mais le maximum
  atteint `85110.258 ms`, limite de viabilite a conserver visible malgre
  l'absence de statut timeout;
- usage total: `204688` tokens prompt, `9690` completion, `0` reasoning et
  `214378` total. Cout observe `0.506276 USD`, soit `0.00366867 USD` par appel,
  tres inferieur au plafond `25 USD`;
- les deux repetitions sont stables mais echouent chacune sur `13/16`
  dialogues. Seuls trois dialogues passent dans les deux repetitions, soit
  `6/32` scores. Les taux par famille restent a `0.0` sauf `citation=1.0`;
  les defauts reproductibles portent notamment sur le surcodage local ou
  agrege, la force, la decroissance et les trajectoires de stabilite/bascule;
- decision gelee `not_eligible`: la campagne est techniquement complete mais
  manque les seuils semantiques `1.0`. L'artefact content-free date contient
  `174` lignes, empreinte
  `3f4da100e9c9553d64bdf44b379a02921297f6984e506b359a40891db4f4ad46`;
- un contre-audit de reconstruction a corrige le validateur de statistiques,
  qui dependait a tort de l'ordre des cles avant serialisation. Un golden
  recharge desormais le JSONL trie et reconstruit integralement la decision;
- la porte de livraison est fermee: aucun prompt, modele live, setting,
  runtime, frontend, rebuild, restart, deploiement ou smoke n'est modifie.
  4C.2 reste ouvert et 4C.3 reste non commence.

Passe corrective de frontiere de preuve executee le 2026-08-30, sans provider:

- contradiction validee: le score historique `score_dialogue` additionnait
  les codes du signal local et ceux de l'agregat deterministe, puis presentait
  ce resultat combine comme qualite du caller. Le `6/32` Sonnet se decompose
  reellement en `6` passes complets, `16` echecs agregateur seuls, `7` echecs
  mixtes et `3` echecs caller seuls. Le prompt renforce primaire obtenait
  `28/32` passes caller locales, contre seulement `10/32` passes combinees;
- architecture de preuve: le scorer et les manifests historiques restent
  byte-for-byte inchanges. Le rescorer versionne
  `benchmark/suites/stimmung/causal_rescoring.py` reutilise leurs validateurs
  de schema et produit trois niveaux fermes: `caller_local_semantics`,
  `aggregate_trajectory` et `combined_pipeline`. Ce dernier est reconstruit a
  l'identique pour les `192` scores historiques;
- provenance des fenetres: chaque etape conserve seulement les identifiants
  synthetiques des tours effectivement consultes, le sous-ensemble de signaux
  actifs et les comptes avec/sans attente locale. Les `37` tours non evalues
  ne recoivent aucune attente retroactive. Tous les echecs agreges observes
  dependent d'au moins un tour non evalue et restent donc
  `not_attributable_unscored_contributors`; le temoin 4S.0 prouve leur
  atteignabilite, pas une faute de l'agregateur;
- matrice content-free recalculee depuis les appels historiques:

  | campagne/source | caller local pass/fail/inc. | agregat pass/fail/inc. | pipeline combine pass/fail/inc. |
  | --- | ---: | ---: | ---: |
  | 4S.1 primaire Gemini 3.1 | `10/22/0` | `8/24/0` | `0/32/0` |
  | 4S.1 fallback GPT-5.4 Nano | `11/21/0` | `9/23/0` | `4/28/0` |
  | prompt renforce primaire | `28/4/0` | `10/22/0` | `10/22/0` |
  | prompt renforce fallback | `25/6/1` | `8/23/1` | `8/23/1` |
  | Gemini 3.7 medium, 800 | `15/17/0` | `11/21/0` | `5/27/0` |
  | Sonnet 5 medium | `22/10/0` | `9/23/0` | `6/26/0` |

- decision bornee: le prompt renforce ameliore fortement la responsabilite
  locale du primaire mais reste `not_eligible` au seuil inchange `1.0`; ses
  quatre echecs reproductibles concernent `L4S0-ST-001` et `L4S0-ST-003`, avec
  `signal_overcoded` et `strength_outside_allowed`. Le fallback reste
  `inconclusive` a cause de son resultat schema manquant. Sonnet reste
  `not_eligible`. Gemini 3.7 conserve `15/32` passes locales observables mais
  sa decision reste `inconclusive`: son erreur JSON sur un tour non evalue ne
  doit pas disparaitre derriere les seuls scores locaux. Aucun des deux
  modeles ne soutient un cutover face a la candidate de prompt. Un essai
  GPT-5.2 n'est pas requis par les preuves actuelles avant traitement des
  quatre defauts locaux residuels;
- artefact derive content-free:
  `benchmark/results/stimmung/2026-08-30-lot4c2-stimmung-causal-rescoring.jsonl`,
  `199` lignes (`192` rescores, `6` syntheses de configuration, `1` synthese
  finale), SHA-256
  `4cadffa37afb9802345ec16aaf3095468e37a8c17969374a1935ebac790e4ea0`.
  Les quatre artefacts provider sources conservent leurs empreintes
  historiques et aucune ligne provider n'est reecrite;
- sensibilite: rejet d'un echec agregateur impute au caller, d'un mauvais
  signal masque par un agregat conforme, d'un agregat corrompu contaminant le
  score local, d'une attribution certaine avec contributeur non evalue, d'un
  contenu libre, d'une fausse eligibilite et d'un resultat incomplet presente
  comme eligible;
- preuves executees: reproduction rouge de l'API de score separee absente,
  puis d'une reconstruction combinee qui perdait la source d'un resultat
  historique incomplet; tests du rescorer `9/9`, goldens 4S.0/4S.1/4C.2
  `56/56`, caller/normaliseur/agregateur/goldens causaux voisins `33/33`, et
  decouverte Python hermetique finale `2815/2815` (`2806 + 9`, aucun skip ni
  expected failure). La baseline globale pre-patch reste JavaScript `137/137`
  et Chromium `19/19`; ils ne sont pas relances apres patch puisqu'aucun asset,
  contrat frontend ou runtime n'est touche;
- commandes de preuve: runners Docker locaux avec depot complet monte read-only,
  `--network none`, `/tmp` en tmpfs et `PYTHONDONTWRITEBYTECODE=1`; reconstruction
  CLI hors ligne du JSONL, `git diff --check`, verification des empreintes des
  quatre sources historiques et controle content-free de l'artefact derive;
- aucun appel provider, fallback, prompt, modele, setting, schema metier,
  normaliseur, agregateur runtime, frontend, observabilite produit, rebuild,
  restart ou deploiement. 4C.2 reste ouvert pour le correctif local residuel;
  4C.3 reste non commence.

Ultime passe bornee 4C.2 gelee le 2026-08-30, avant resultat provider:

- decision humaine appliquee sans reecriture historique: le corpus v3 est une
  copie contractuelle de v2 dont la seule requalification semantique porte la
  derniere force de `L4S0-ST-003`, elargie de `[2,6]` a `[2,7]`; `7` est
  accepte et `8` reste rejete. Les identifiants de schema/corpus/dialogues sont
  versionnes v3. Le corpus v2 et les artefacts historiques conservent leurs
  empreintes;
- candidate prompt v2: copie byte-for-byte de la candidate v1 plus une unique
  regle generale de parcimonie interdisant de deduire l'enthousiasme de la
  seule volonte de poursuivre, comprendre, examiner ou agir. Aucun exemple du
  corpus, regex, taxonomie ou second axe de politique n'est ajoute;
- protocole gele: corpus v3 SHA-256
  `cd5a16f64dcfaef04900166b17cef05343672a1e5484d06a007c0b328aac6a1c`,
  candidate v2 SHA-256
  `567f0615f14fe9f13a50e6e57ef46dc6fdba2cd6e6156407d6e2f489c2076a7f`;
  Gemini 3.1 Flash Lite primaire seul, parametres runtime courants, zero
  fallback/retry/modele voisin, repetition 1 de 69 appels puis repetition 2
  seulement apres `16/16`, plafond absolu `138`, cout prudent sous `0.30 USD`;
- porte gelee: seul `caller_local_semantics` gouverne la decision; les scores
  agregateur et pipeline restent diagnostiques. `32/32`, zero erreur,
  provenance complete et zero regression sont necessaires a
  `eligible_primary`; un echec de la premiere repetition arrete la campagne a
  69 appels;
- preuves avant provider: cycle rouge sur le protocole final absent, puis
  `8/8` nouvelles preuves et `64/64` goldens 4S.0/4S.1/4C.2. Les mutations
  rejettent notamment 8, une autre modification v2->v3, une seconde politique
  de prompt, un fallback, un 139e appel, une porte agregateur et une fausse
  eligibilite. 4C.2 reste ouvert jusqu'au resultat et 4C.3 non commence.
- campagne primaire executee une seule fois depuis le gel pousse `94bd338c`:
  `138/138` appels valides, zero fallback/retry, `16/16` local aux deux
  repetitions, soit `32/32` et decision `eligible_primary`; cout observe
  `0.04234050 USD`, latence mediane/p95 `830.950/1181.196 ms`, usage
  `113274/9348/122622` tokens prompt/completion/total. Les vues diagnostiques
  agregee et combinee restent a `9/32` sans gouverner la porte locale;
- artefact content-free
  `benchmark/results/stimmung/2026-08-30-lot4c2-stimmung-final-prompt-candidate-v2.jsonl`,
  SHA-256
  `339c82f0160d2cea107592843a6f98a87306bf1ddcfdb1f8d5e1a78b5b3fc920`.
  La decision humaine autorise maintenant la livraison exacte de la candidate;
  4C.2 reste ouvert jusqu'aux preuves runtime finales et 4C.3 non commence.

Livraison conditionnelle executee apres la porte verte:

- les bytes exacts de la candidate v2 ont remplace le prompt runtime dans le
  commit `f90162412aede7ef02910bc49c6f7b4d38a624a7`; empreinte checkout et
  conteneur identique
  `567f0615f14fe9f13a50e6e57ef46dc6fdba2cd6e6156407d6e2f489c2076a7f`;
- le lecteur benchmark reconstruit desormais explicitement le prompt runtime
  historique d'empreinte `6374bf40...`; les artefacts et controles anciens ne
  sont ni reecrits ni reinterpretes avec le prompt livre;
- le modele primaire reste `google/gemini-3.1-flash-lite`, le fallback
  `openai/gpt-5.4-nano`, le timeout `10 s`, le plafond `220` et le sampling
  `temperature=0.1` / `top_p=1.0`. Aucun appel fallback ou provider
  supplementaire n'a ete execute apres la campagne;
- preuves finales: `19/19` tests directement affectes, `65/65` goldens
  4S.0/4S.1/4C.2, `33/33` suites caller/normaliseur/agregateur voisines et
  decouverte Python hermetique `2824/2824`, sans skip ni expected failure. Les
  baselines frontend restent JavaScript `137/137` et Chromium `19/19`; aucun
  fichier ou contrat frontend n'a change, ils n'ont donc pas ete rejoues apres
  livraison;
- FridaDev seul a ete rebuild sans pull puis recree avec `--no-deps`: image
  `sha256:bbab658701a729a6c653b0b9669dfb971a166677065ccc4683030612e30abef4`,
  `StartedAt=2026-08-30T20:23:31.378268813Z`, HTTP interne `200`, healthy,
  restart `0`, OOM false. Les identifiants et StartedAt des conteneurs voisins
  sont inchanges;
- aucune nouvelle version de prompt n'est inferee dans les evenements: la
  lecture admin existante expose la source fichier et ses metadonnees
  content-free, tandis que les evenements historiques restent depourvus de
  provenance qu'ils ne mesuraient pas. Aucun read-model, renderer ou frontend
  n'etait rendu faux;
- 4C.2 est ferme. 4C.3 et tous les micro-lots suivants restent non commences.

Message de commit recommande si active: `fix: strengthen Stimmung semantic extraction`.

### Micro-lot 4C.3 - Separation affect et certitude epistemique

Statut: cloture fonctionnelle prouvee le 31 aout 2026; commit, push et livraison
ciblee encore a inscrire ci-dessous
Effort recommande: `extra high`
Nature: decision semantique, correctif runtime borne et observabilite synchrone
Prerequis: 4S.1 ferme; 4C.2 ferme ou classe non requis

Objectif exact: corriger F2 sans diminuer l'effet dialogique de Stimmung. Un
mouvement affectif peut ajuster l'enonciation, le rythme, la delicatesse ou la
prudence de formulation. A lui seul, il ne peut pas transformer une proposition
`certaine` en `probable` s'il n'existe aucune raison epistemique independante:
ambiguite, manque de source, sous-determination, contradiction ou hard guard.

La regle semantique exacte doit etre relue et approuvee par Tof avant patch.
L'implementation est ensuite choisie depuis le code et les preuves, sans la
predeterminer artificiellement. Les deux options recevables sont:

- conditionner `stimmung_caution` a un signal epistemique independant deja
  present;
- retirer son effet direct sur la certitude et le convertir en directive
  bornee d'enonciation dans le raccord existant.

Sont interdits: nouveau modele, nouveau stage, regex, score psychologique,
modification de Stimmung elle-meme ou changement des priorites Presence/final
locks.

Preuves obligatoires:

- meme contenu epistemique avec Stimmung absente, stable et en transition;
- transition sans raison epistemique: certitude preservee, enonciation adaptee;
- transition avec ambiguite independante: prudence epistemique permise;
- hard guards, question, demande, risque, action materielle et Presence non
  masques;
- Validation et modele principal recoivent une posture coherente;
- mutation retablissant la degradation automatique de certitude rejetee;
- mutation supprimant tout effet enonciatif de Stimmung rejetee.

Observabilite simultanee:

- exposer separement effet epistemique et effet d'enonciation, leur source et
  leur reason code;
- propager ces champs sans contenu brut jusqu'aux deux surfaces existantes;
- le frontend ne doit jamais deduire l'un depuis l'autre;
- ajouter les preuves navigateur et garder primaire/fallback/fail-open honnetes.

Condition de fermeture:

- [x] Regle semantique approuvee avant patch.
- [x] Affect seul incapable de degrader la certitude.
- [x] Effet dialogique d'enonciation preserve et prouve.
- [x] Invariants voisins, observabilite et mutations controles.
- [ ] Tests, documentation, commit, push et livraison ciblee prouves.

Message de commit recommande: `fix: separate Stimmung from epistemic certainty`.

Cloture fonctionnelle du 31 aout 2026 avant livraison:

- Tof a relu et approuve avant patch la regle suivante: un mouvement affectif
  peut modifier la maniere d'enoncer, mais jamais le degre de certitude sans
  raison epistemique independante. La meme matiere factuelle et les memes
  preuves produisent donc le meme triplet epistemique, que Stimmung soit
  absente, stable ou en transition;
- F1 est valide: `stimmung_caution` interdisait a un input pourtant fortement
  etabli de rester `certain`. F2 est valide: le meme embranchement forcait
  aussi `uncertainty_posture=prudente` sans raison epistemique independante.
  F3 est valide: un golden 4C verrouillait explicitement la degradation
  `certain -> probable` sous transition;
- F4 est valide dans son sens local: supprimer seulement la condition aurait
  retire l'effet utile de Stimmung. Il est corrige ici en transportant une
  directive derivee d'enonciation. L'efficacite de cette directive dans la
  formulation finale et toute comparaison provider restent exclusivement le
  diagnostic conditionnel de 4C.4, toujours non commence;
- F5 est valide: les evenements ne distinguaient pas effet epistemique et effet
  d'enonciation avec leurs provenances. F6 est partiellement valide comme
  risque structurel: les projections pouvaient rendre une posture prudente
  sans permettre d'etablir si sa source etait factuelle ou affective; aucune
  preuve d'un libelle frontend precis mensonger n'a ete inventee;
- l'architecture minimale retire Stimmung de
  `build_epistemic_regime`: certitude, regime de preuve et posture
  d'incertitude sont derives uniquement des inputs epistemiques. Le verdict
  primaire ajoute deux triplets stricts, `epistemic_effect` et
  `enunciation_directive`. Absence et stabilite restent des no-op explicites;
  seule une transition produit `delicate_expression/stimmung/affective_transition`;
- Validation exige puis recopie ces deux triplets sans les rederiver. Le
  modele principal recoit leur projection structuree et une instruction bornee
  qui autorise uniquement delicatesse, rythme et formulation, jamais une
  modification de certitude, preuve ou incertitude. Aucune tonalite brute,
  contenu operateur, nouvelle route, nouveau stage ou nouveau modele n'est
  ajoute;
- le chemin d'observabilite est synchrone: verdict runtime, evenements
  `primary_node` / `validation_agent` / `prompt_injection`, garde de payload,
  projection admin, reader, `turn_pipeline_read_model`, API existantes, puis
  `/log` et `/hermeneutic-admin`. Les six champs autoritatifs distinguent les
  trois champs epistemiques des trois champs d'enonciation. Les deux frontends
  reutilisent le meme normaliseur ferme et ne deduisent rien d'un texte libre;
- `none`, `not_applicable`, `unknown`, succes et fail-open restent distincts.
  Un evenement historique incomplet devient `unknown`; Validation prime sur le
  primaire quand elle existe; primaire, fallback et fail-open ne fabriquent
  aucune causalite. Les reconstructions repetees ne dupliquent pas la directive;
- les reproductions rouges ont traverse le coordinateur primaire et le vrai
  coordinateur chat: avant correction, l'input fortement etabli restait
  `certain/discrete` avec Stimmung absente ou stable mais devenait
  `probable/prudente` en transition. Deux tests ont echoue comme attendu avant
  le patch, tout en constatant que la transition devait conserver un effet
  d'enonciation observable;
- les preuves principales sont
  `app/tests/unit/golden/test_lot4_stimmung_causal_goldens.py`,
  `app/tests/unit/core/hermeneutic_node/runtime/test_primary_node.py`,
  `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py`,
  `app/tests/unit/chat/test_chat_prompt_context.py`,
  `app/tests/unit/logs/test_agentic_observability_statuses.py`,
  `app/tests/unit/frontend_chat/test_validation_projection_module.js` et
  `app/tests/integration/frontend_browser/test_frontend_browser_smoke.js`;
- les mutations controlees rejettent: degradation `certain -> probable` par
  Stimmung seule; changement de `proof_regime` ou `uncertainty_posture` par
  Stimmung; suppression de l'effet d'enonciation; confusion des sources ou
  reason codes; injection du signal brut; duplication de directive; succes
  fabrique depuis un fail-open; prudence epistemique frontend sans provenance;
- les invariants voisins sont verts: questions, demandes, risques, actions
  materielles, hard guards, Presence et priorites des final locks; parite JSON
  et streaming; persistance et provenance; capsule terminale et
  `main_payload_manifest_v1`. Les anciens temoins provider 4C.1 refusent
  honnetement leur comparabilite avec le contrat de messages 4C.3; leur
  mecanique reste testee avec un temoin synthetique explicite, sans campagne;
- baseline avant patch: Python `2824/2824`, JavaScript `137/137`, Chromium
  `19/19`. Preuves finales avant livraison: doctrine/primaire `47/47`, goldens
  causaux `13/13`, Validation/modele principal `96/96`, Presence/final locks
  `50/50`, JSON/streaming/persistance `36/36`, capsule/manifest `25/25`,
  observabilite backend/read-model/API `108/108`, JavaScript `140/140`,
  Chromium `19/19`, puis decouverte Python hermetique `2828/2828`. Le delta
  exact est de quatre tests Python et trois tests JavaScript, sans skip, TODO
  ni expected failure;
- aucun tour utilisateur reel, appel provider reel, changement de prompt
  Stimmung, modele, fallback, sampling, timeout, normaliseur ou agregateur n'a
  ete execute. Le diagnostic de restitution finale reste assigne a 4C.4; le
  contre-audit causal global reste assigne a 4O.Z. Ces deux lots et tous les
  lots suivants demeurent ouverts et non commences.

### Micro-lot 4C.4 - Restitution finale conditionnelle de l'effet dialogique

Statut: conditionnel, non commence
Effort recommande: `extra high`
Nature: diagnostic causal puis correctif minimal si dommage prouve
Prerequis: 4C.3 ferme

Objectif exact: trancher F4. L'absence de structure Stimmung brute dans le
payload principal n'est pas un bug en elle-meme. Ce micro-lot ne modifie le
runtime que si une comparaison controlee prouve que la posture derivee perd un
effet dialogique attendu dans la formulation finale.

Diagnostic obligatoire:

- comparer les memes inputs avec la posture courante et une restitution
  diagnostique bornee;
- utiliser d'abord des providers fakes pour le raccord, puis demander un GO
  separe si une campagne avec le modele principal est necessaire;
- mesurer delicatesse, adequation de formulation, psychologisation, influence
  indue sur la verite et regression Presence;
- classer F4 `valide`, `invalide` ou `partiel` avant toute correction.

Si F4 est invalide, fermer 4C.4 `non requis` sans runtime. Si F4 est valide,
le correctif doit reutiliser le pipeline Validation/posture existant et fournir
au modele principal une directive derivee, compacte et bornee. Il ne transmet
jamais les tonalites brutes, n'ajoute ni stage ni modele, ne profile aucune
personne et ne contourne pas `main_payload_manifest_v1`.

Preuves obligatoires si correction:

- benefice semantique reproduit sur les cas qui ont valide F4;
- absence de changement sur les contre-cas;
- aucune influence sur verite, hard guards, Presence ou final locks;
- capsule terminale unique, manifest coherent, parite JSON/streaming,
  persistance et provenance preservees;
- observabilite causale backend/read-model/frontend et navigateur synchronisee;
- mutation supprimant l'effet utile et mutation injectant le signal brut toutes
  deux rejetees.

Condition de fermeture:

- [ ] F4 classe par une comparaison causale explicite.
- [ ] `non requis` documente, ou correctif minimal prouve sans signal brut.
- [ ] Aucun nouveau stage, modele, caller ou capacite produit.
- [ ] Tests, observabilite, documentation, commit, push et livraison ciblee
  prouves si le runtime change.

Message de commit recommande si active: `fix: preserve Stimmung in final dialogic posture`.

### Micro-lot 4O.Z - Contre-audit causal et fermeture du Lot 4

Statut: non commence; dernier micro-lot du Lot 4
Effort recommande: `extra high`
Nature: audit transversal, tests et documentation; aucun correctif opportuniste
Prerequis: 4C.1, 4S.0, 4S.1 et 4C.3 fermes; 4C.2 et 4C.4 fermes ou non requis

Objectif exact: verifier que les corrections et decisions precedentes forment
un pipeline coherent, observable et documente, puis fermer le Lot 4 avant tout
debut du Lot 5. Ce micro-lot n'est pas une passe de rattrapage: tout gap runtime
ou frontend decouvert ouvre un correctif borne distinct avant sa reprise.

Contre-audit obligatoire:

- matrice complete `caller -> persistance -> agregation -> regime primaire ->
  Validation -> posture principale`;
- pour chaque transition: contrat, event, reader, read-model, renderer et test
  navigateur autoritatifs;
- absence de perte silencieuse, etat causal invente, double signal, contenu
  brut, psychologisation ou degradation epistemique par affect seul;
- primaire, fallback, fail-open, JSON/streaming, Presence, final locks,
  persistance, capsule et manifest coherents;
- aucun ancien chemin, branche diagnostique runtime, test affaibli, fixture
  auto-referentielle, TODO contradictoire ou Lot 5 commence;
- suites ciblees, voisines, frontend, navigateur et decouverte complete;
- diff check, temporaires, provenance Git et runtime.

Decision documentaire finale:

- la decision globale devient necessairement `strengthen`, car F3 exige 4C.1;
- documenter precisement ce qui a ete renforce et pourquoi;
- documenter separement `keep_current`, `strengthen`, `non requis` ou
  `inconclusive` pour le caller, F2 et F4;
- mettre a jour les contrats vivants et les sections README rendues fausses par
  les changements effectivement livres, sans anticiper les Lots 5 a 8;
- laisser chaque limite restante assignee a un lot nomme, jamais a une dette
  vague.

Condition de fermeture:

- [ ] Tous les micro-lots obligatoires sont fermes et les conditionnels classes.
- [ ] Corpus et campagne primaire/fallback ont une decision explicite.
- [ ] F2 est corrige et F4 tranche.
- [ ] Matrice causale backend/read-model/frontend et navigateur complete.
- [ ] Suites finales et sensibilite restent vertes sans skip nouveau.
- [ ] Roadmap, contrats et README concernes sont coherents.
- [ ] Commit, push, worktree propre, divergence `0/0` et runtime prouve.
- [ ] Lot 5 reste non commence jusqu'a cette fermeture.

Message de commit recommande: `docs: close Lot 4 Stimmung causal consolidation`.

## Passe 4.0 - Goldens causaux hermetiques

Construire une fixture transversale partagee qui traverse le vrai pipeline
Stimmung avec providers, stockage, horloge et persistance fakes. Elle ne doit
pas recopier les algorithmes du produit dans le test.

La fixture doit permettre de comparer, sur exactement le meme dialogue:

- pipeline courant complet;
- meme execution avec signal Stimmung neutralise uniquement au raccord teste;
- signal produit mais absent du regime primaire;
- signal produit mais absent du payload reel de Validation;
- signal present jusqu'a la posture finale;
- primaire et fallback distingues;
- succes, resultat vide, timeout, transport et schema invalide.

Ces ablations sont des sondes de causalite internes aux tests. Elles ne creent
aucun mode runtime et ne doivent laisser aucun branchement produit dormant.

## Corpus dialogique multi-tours obligatoire

Le corpus est content-free, synthetique, versionne et relu humainement. Chaque
cas comporte assez de tours pour exercer la fenetre de contexte du caller et la
stabilisation sur quatre signaux. Il couvre au minimum:

- emergence progressive d'un affect;
- affect stable sur plusieurs tours;
- bascule nette puis stabilisation;
- retour progressif vers un etat neutre;
- alternance qui doit rester volatile;
- formulation intense sans changement epistemique;
- ironie, citation ou affect rapporte qui ne doit pas etre attribue au
  dialogue courant;
- correction explicite apres une mauvaise lecture affective;
- question, demande, risque et action materielle qui ne doivent pas etre
  masques;
- opportunite Presence et contre-cas Presence;
- echec primaire avec fallback;
- echec complet en fail-open sans faux signal sain.

Un snapshot d'un seul tour ne constitue jamais une preuve de Stimmung. Les
goldens doivent montrer l'emergence, la maturite, le deplacement, la persistance
et la decroissance du signal.

## Invariants a figer

- schema borne du signal par tour et reason codes;
- ordre chronologique, fenetre, ponderation et hysteresis reelles;
- absence de duplication apres reconstruction ou retry;
- provenance primaire/fallback conservee;
- difference causale, ou absence honnete de difference, pour le regime
  primaire, Validation et la posture finale;
- absence de psychologisation, de profilage identitaire et de contenu brut dans
  les artefacts;
- absence de souverainete de l'affect sur la verite ou l'adoption;
- identite JSON/streaming lorsque le contrat l'exige;
- fail-open sans faux succes, faux signal ou disparition silencieuse du statut;
- aucune regression Presence, Identity mutable, contexte dialogique, final
  locks ou persistance.

## Observabilite obligatoire et simultanee

Pour chaque preuve causale, etablir la matrice:

`stage runtime -> event -> reader -> read-model -> renderer -> test navigateur`

Elle doit distinguer sans contenu brut:

- source primaire ou fallback;
- statut et reason code;
- signal present, absent, vide ou invalide;
- profondeur de fenetre et etat de stabilite;
- raccord primaire tente ou non;
- inclusion effective dans le materiel transmis a Validation;
- influence detectee ou non sur le regime primaire et la posture finale;
- fail-open et limite connue.

Une surface ne doit pas deduire un etat causal depuis un libelle libre. Toute
future modification backend du Lot 4 doit mettre a jour dans le meme micro-lot
read-model, frontend et preuves navigateur. Aucun contenu de dialogue, signal
brut, prompt, payload provider, exception brute, URL ou secret n'entre dans les
evenements, snapshots ou artefacts content-free.

## Metriques de decision corrective

Mesurer par cas, puis par famille:

- exactitude et stabilite du signal;
- surcodage affectif et affect manque;
- psychologisation;
- faux `clarify`, faux `suspend` et faux silence;
- impact sur Presence et ses contre-cas;
- changement du niveau epistemique;
- changement de posture ou de formulation finale;
- signal produit mais non consomme;
- signal consomme sans effet observable;
- latence et cout du primaire et du fallback.

Les couts et latences informent une optimisation; ils ne peuvent jamais, seuls,
justifier la suppression de Stimmung.

## Sensibilite obligatoire

Les preuves doivent rejeter au minimum les mutations controlees suivantes:

- signal retire ou duplique;
- ordre des signaux inverse;
- fenetre reduite a un seul tour;
- hysteresis ignoree;
- affect stable transforme en volatil ou inversement;
- `stimmung_caution` force sans condition;
- signal absent du payload Validation presente comme recu;
- signal present mais efface par compactage;
- source fallback presentee comme primaire;
- echec transforme en signal neutre sain;
- contenu brut ajoute a l'observabilite;
- frontend annoncant une influence que le backend ne prouve pas.

Un test qui reste vert sous la mutation qu'il pretend interdire n'est pas une
preuve acceptable.

## Campagne provider eventuelle

Les goldens hermetiques et le diagnostic de transport precedent toute campagne
provider. Une campagne primaire/fallback eventuelle exige un GO explicite
separe, utilise seulement le corpus synthetique valide, conserve un artefact
JSONL date et content-free et n'appelle jamais une DB ou une donnee operateur.
Elle mesure la qualite semantique sans modifier modele, prompt, niveau de
raisonnement, timeout ou setting.

## Sorties autorisees du Lot 4

Avant les goldens, le Lot 4 pouvait se fermer avec une seule des trois
decisions suivantes:

1. `keep_current`: les effets attendus sont prouves et aucun defaut justifie un
   changement runtime;
2. `strengthen`: un ou plusieurs gaps sont prouves et classes dans des
   micro-lots correctifs separes;
3. `inconclusive`: le corpus est insuffisant; Stimmung reste strictement
   inchangee et l'extension necessaire du corpus est bornee.

Depuis la validation de F3, `keep_current` n'est plus une sortie globale
coherente: la perte structurelle avant Validation impose `strengthen` au moins
par 4C.1. Les trois qualifications restent utilisables separement pour le
caller et pour les findings conditionnels, sans annuler la correction
obligatoire de F3.

Les pistes initialement prevues sous `strengthen` sont desormais assignees aux
micro-lots autoritatifs ci-dessus:

- livraison garantie d'un bloc Stimmung borne a Validation -> `4C.1`;
- corpus et benchmark de stabilisation, hysteresis ou decroissance -> `4S.0`
  et `4S.1`;
- correction semantique du caller, prompt ou modele si elle est prouvee ->
  `4C.2`;
- separation entre prudence epistemique et ajustement d'enonciation -> `4C.3`;
- restitution d'une posture finale moins appauvrie si F4 est valide -> `4C.4`;
- contre-audit de l'observabilite causale backend/read-model/frontend ->
  `4O.Z`, apres livraison synchrone dans chaque correctif.

Chaque correction runtime, prompt, modele ou setting constitue un micro-lot
distinct avec GO explicite, baseline, preuves rouges, tests, contre-audit,
documentation, commit, push et livraison ciblee. Aucun de ces micro-lots n'est
commence par l'audit.

## Interdits absolus

- supprimer, retirer, desactiver ou contourner Stimmung comme direction
  produit;
- transformer l'ablation diagnostique en variante runtime;
- remplacer le caller par des regex emotionnelles;
- conclure depuis des tests mono-tour;
- fusionner Stimmung avec Identity ou le contexte dialogique temporaire;
- deduire un etat interieur durable depuis un affect local;
- modifier code runtime, prompt, modele, provider, niveau de raisonnement,
  timeout ou setting pendant la passe 4.0;
- provoquer un tour utilisateur, utiliser une DB operateur ou exposer du
  contenu brut;
- commencer le Lot 5 avant la fermeture documentaire du Lot 4.

## Fichiers de preuve cibles

Privilegier une fixture commune et un golden transversal, par exemple:

- `app/tests/support/stimmung_dialogic_pipeline.py`;
- `app/tests/unit/golden/test_lot4_stimmung_causal_goldens.py`;
- les contrats existants Stimmung, noeud hermeneutique, Validation,
  observabilite et read-model;
- la seule presente section du Lot 4 pour les resultats et limites.

Les noms exacts sont confirmes apres inventaire. Ne pas creer une seconde
preuve lorsqu'un test existant couvre deja exactement l'invariant.

## Condition de fermeture

- [x] Decision humaine `keep` tracee et suppression explicitement exclue.
- [x] Finalite dialogique et ablation diagnostique clarifiees.
- [x] Inventaire A a Z du pipeline, des contrats et des preuves existantes.
- [x] Goldens causaux techniques du coeur et mutations controlees livres.
- [x] 4C.1 ferme: livraison Stimmung vers Validation complete ou absence
  explicite, comparaison provider `pass` pour Gemini 3.7 Flash medium
  (`22/22`), configuration active live et smoke unique `L4C1-VAL-005` vert;
  garantie structurelle et observabilite synchrone livrees.
- [x] 4S.0 ferme: corpus et seuils semantiques valides humainement par Codex
  sur delegation explicite de Tof.
- [ ] 4S.1 ferme: campagne primaire/fallback executee sous GO separe et
  decision caller tracee.
- [ ] 4C.2 ferme `corrige` ou `non requis` depuis les preuves 4S.1.
- [ ] 4C.3 ferme: affect et certitude epistemique separes sans perdre l'effet
  dialogique.
- [ ] 4C.4 ferme `corrige`, `non requis` ou `inconclusive` depuis une preuve
  causale de F4.
- [ ] 4O.Z ferme: contre-audit causal, contrats et README concernes coherents.
- [x] Corpus semantique multi-tours du caller valide humainement: ironie, affect rapporte,
  correction, intensite sans changement epistemique, question, demande, risque,
  action materielle et contre-cas Presence.
- [x] Reception effective par Validation et posture finale prouvees.
- [ ] Matrice observabilite backend/read-model/frontend prouvee.
- [x] Primaire et fallback distingues sans requalification d'echec.
- [x] Findings F1 a F6 valides, invalides ou nuances par preuves.
- [ ] Decision globale `strengthen` documentee; decisions du caller, de F2 et
  de F4 classees separement depuis leurs preuves.
- [x] Aucun caller, mode ou capacite produit ajoute.
- [x] Aucun micro-lot correctif ou Lot 5 commence implicitement.

# LOT 5 - Structured outputs des callers conserves

Statut: non commence
Nature: robustesse transport
Dependance: decision Lot 4

## Objectif

Remplacer le JSON demande en texte libre par un schema provider strict pour
Validation et Stimmung, tout en gardant la validation metier locale
souveraine.

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
- effet causal de Stimmung non prouve ou limites identifiees non tracees;
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
- [ ] contrat Stimmung conserve, avec effets prouves et limites explicites;
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
- laisser visible la decision architecturale `keep` et la decision corrective
  `keep_current`, `strengthen` ou `inconclusive` sans forcer artificiellement
  un changement;
- conserver les limites et risques residuels;
- commit, push, worktree propre et divergence `0/0`.

## Condition d'arret globale

Le chantier est termine lorsque:

- Identity progresse apres une fenetre terminale;
- l'extracteur legacy n'est plus un caller actif;
- Presence est evaluee sur son contrat reel;
- Stimmung a un audit causal fonde sur une ablation diagnostique multi-tours
  et une decision corrective explicite;
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
