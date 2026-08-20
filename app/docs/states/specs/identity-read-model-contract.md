# Identity Read Model Contract

Statut: spec vivante  
Portee: lecture operator-facing read-only reemployee par `/hermeneutic-admin` et `/identity`
Lot ferme: `Lot 5`

Transition refonte mutable 2026-05-26:
- le read-model expose maintenant le regime actif `mutable_identity_judge_v2_add_only`;
- le contrat source-of-truth du writer mutable reste `mutable-identity-judge-contract.md`;
- les champs de fenetre, statut, reason code, presence, longueurs, compteurs, IDs opaques et timestamps racontent `5 paires completes -> juge LLM mutable_judge_v2 -> add/no_change -> identity_mutables`;
- le scoring local et la promotion mutable -> static restent visibles seulement comme legacy pre-refonte inactive.

Transition contexte dialogique 2026-08-20:
- `dialogic_context` expose le caller actif par tour comme contexte temporaire,
  non comme writer Identity;
- son sujet logique est `dialogue`; le slot `identity_extractor_model` reste un
  nom de compatibilite pour GPT-5.4 mini et ses reglages;
- les collections `user/llm` restent historiques, tandis que le juge GPT-5.2
  demeure l'unique writer automatique du canon mutable.
- la projection de l'activite lit la forme autoritative `payload` retournee par
  `read_chat_log_events`; `payload_json` reste un detail du writer/stockage et
  n'est pas un champ du read-model;
- le reason code de succes du stage est porte explicitement dans son payload
  compact, comme les compteurs et le `prompt_kind`.

## But

Ce contrat definit une lecture unifiee et honnete du systeme identity reel, y compris le regime periodique `staging -> agent -> canon`, sans rouvrir le canon injecte lui-meme.

Le read-model lui-meme reste read-only, meme si les surfaces operator-facing peuvent aussi porter, depuis `Lot 3`, `Lot 4` et `Lot 5`, des editions ou lectures distinctes documentees a part.

Il sert a :
- montrer la base canonique active et les flags runtime associes;
- distinguer clairement ce qui est charge, stocke, injecte, legacy, evidence et conflit;
- rappeler que le pilotage systeme reste distinct de cette lecture identity;
- fournir une base stable pour la surface `Identity` dediee.

## Route

- `GET /api/admin/identity/read-model`

Cette route est:
- read-only;
- protegee par la meme garde admin que les autres routes `/api/admin/*`;
- distincte de `/api/admin/hermeneutics/identity-candidates`, qui reste legacy / evidence-only;
- distincte de `GET /api/admin/identity/governance`, qui porte la lecture des caps/seuils/budgets identity;
- distincte de `GET /api/admin/identity/runtime-representations`, qui porte une projection structuree compilee pour le jugement et une forme runtime compilee injectee au modele.

## Verite active exposee

Le read-model doit exposer explicitement:
- `active_identity_source = "identity_mutables"`
- `active_static_source = "resource_path_content"`
- `active_prompt_contract = "static + mutable narrative"`
- `active_prompt_contract` reste le nom technique du contrat de compilation identity runtime, pas un prompt canonique source-of-truth
- `identity_input_schema_version = "v2"`
- `legacy_identity_pipeline_status = "legacy_inactive_historical"`
- `legacy_identity_pipeline_recorded_via = "historical_persist_identity_entries"`
- `legacy_identity_pipeline_storage = "identities + identity_evidence + identity_conflicts"`
- `read_surface_stage = "lot_b5_identity_operator_truth"`
- `used_identity_ids = []`
- `used_identity_ids_count = 0`
- `governance_read_via = "/api/admin/identity/governance"`
- `governance_editable_via = "/api/admin/identity/governance"`
- `runtime_representations_read_via = "/api/admin/identity/runtime-representations"`
- `mutable_judge_runtime` comme fiche operateur du juge mutable actif: module `mutable_identity_judge_v2_add_only`, caller `mutable_identity_judge`, slot runtime `identity_periodic_model`, modele effectif, prompt actif, contrat `mutable_judge_v2`, structured output strict et verdicts `add` / `no_change`
- `identity_runtime_regime` comme rappel compact du regime runtime actif: `runtime_pipeline`, `window_target_pairs=5`, budget mutable, stages actifs, writer score-first desactive et promotion static desactivee
- `identity_staging` comme verite read-only distincte du canon actif injecte
- `dialogic_context` comme projection content-free de la couche temporaire:
  caller, sujet logique, statut/reason code, presence et comptes bornes,
  slot/model ainsi que la selection autoritative par age, confiance, nombre et
  budget tokens, et les drapeaux `identity_writer=false`,
  `mutable_authority=false`

Le read-model ne doit pas:
- reparser le prompt rendu comme source de verite;
- laisser croire que `active_prompt_contract` designe le pilotage systeme source;
- laisser croire que `identities` pilote encore l'injection active;
- laisser croire que le staging fait partie du canon `static + mutable`;
- masquer la separation entre runtime actif et couches legacy.

## Structure canonique

Top-level:

```json
{
  "ok": true,
  "read_model_version": "v2",
  "active_runtime": {},
  "dialogic_context": {},
  "identity_staging": {},
  "subjects": {
    "llm": {},
    "user": {}
  }
}
```

`dialogic_context` est une couche top-level distincte des sujets identitaires.
Sa persistance compatible utilise `identity_evidence` avec `subject=dialogue`,
sans migration; les items bruts restent minimises dans la projection. Les
evidences historiques `subject=user` eligibles peuvent encore etre lues par le
prompt jusqu'a leur expiration normale, sans reecriture ni autorite canonique.

Chaque sujet expose exactement ces couches:
- `static`
- `mutable`
- `legacy_fragments`
- `evidence`
- `conflicts`

## `active_runtime.mutable_judge_runtime`

Bloc read-only compact du caller modele actif qui pilote l'admission mutable automatique.

Champs minimaux:
- `module = "mutable_identity_judge_v2_add_only"`
- `caller = "mutable_identity_judge"`
- `runtime_slot = "identity_periodic_model"`
- `runtime_slot_compatibility = "legacy_compatible_name"`
- `model`
- `model_source`
- `model_source_reason`
- `prompt_kind = "mutable_identity_judge_v2"`
- `prompt_path = "prompts/identity_mutable_judge_v2.txt"`
- `contract = "mutable_judge_v2"`
- `contract_status`
- `structured_output = true`
- `structured_output_schema = "json_schema_strict"`
- `provider_require_parameters = true`
- `window_target_pairs = 5`
- `attempt_limit = 2`
- `max_window_chars = 40000`
- `max_estimated_prompt_tokens = 16000`
- `verdicts = ["add", "no_change"]`
- `role = "5_pairs_to_add_no_change_ontological_identity_mutables"`

Semantique:
- ce bloc ne modifie pas le runtime; il expose la verite operateur du slot qui est deja consomme par le juge;
- le nom `identity_periodic_model` reste une compatibilite de stockage/admin, pas une indication que `identity_periodic_agent` serait actif;
- aucune fenetre brute, proposition brute, prompt complet ou secret OpenRouter n'y apparait.

## `identity_staging`

Bloc read-only compact du staging identitaire conversation-scoped le plus recent connu par le runtime operateur.

Champs minimaux:
- `storage_kind = "identity_mutable_staging"`
- `scope_kind = "conversation_scoped_latest"`
- `present`
- `actively_injected = false`
- `conversation_id`
- `buffer_pairs_count`
- `buffer_target_pairs`
- `buffer_target_pairs_authority`
- `stored_buffer_target_pairs`
- `stored_buffer_target_pairs_authority`
- `stale_pre_refactor_target_pairs`
- `legacy_stored_buffer_target_pairs`
- `buffer_frozen`
- `last_agent_status`
- `last_agent_reason`
- `last_agent_run_ts`
- `current_buffer`
- `last_completed_agent`
- `updated_ts`
- `auto_canonization_suspended`
- `latest_agent_activity`

Semantique:
- ce bloc ne requalifie pas le staging en canon actif;
- `buffer_target_pairs` designe toujours la cible runtime active de la fenetre judge-first; une ancienne valeur stockee en DB peut rester visible seulement via `stored_buffer_target_pairs` / `legacy_stored_buffer_target_pairs`, non autoritatifs;
- il separe explicitement l'etat du buffer courant (`current_buffer`) du dernier run agent termine (`last_completed_agent`) sans dump du buffer brut;
- quand un nouveau buffer est en cours, `last_agent_reason` ne doit pas porter une ancienne raison terminale comme `completed_no_change`; cette raison reste lisible via `last_completed_agent.reason_code` quand disponible;
- `latest_agent_activity` resume compactement le dernier verdict utile, les compteurs, statuts, reason codes, longueurs, tailles de fenetre et eventuels evenements legacy compactes pour cette conversation;
- `latest_agent_activity.reason_code` lit le `reason_code` compact de l'event actif `mutable_identity_judge`, avec fallback historique vers `identity_periodic_agent`;
- `latest_agent_activity` projette explicitement `failure_class`,
  `recovery_action`, `processing_state`, `attempt_current`, `attempt_limit`,
  `window_fingerprint`, `next_window_progress`, `next_buffer_pairs_count` et
  `writes_previously_applied`;
- `writes_previously_applied=true` signifie que la meme empreinte porte deja un
  commit canonique verifie par le verrou transactionnel du staging; ce champ
  reste faux ou absent pour un simple retry, un echec avant ecriture et une
  consommation terminale sans ecriture;
- `/identity` et `/hermeneutic-admin` rendent ce booleen autoritatif sans
  l'inferer du reason code, d'un texte libre ou de l'absence d'un champ;
- `window_fingerprint` est uniquement le prefixe de 12 caracteres d'un SHA-256
  stable de la fenetre, destine a prouver qu'un retry porte sur la meme capture;
  aucun texte source, proposition, prompt ou canon ne l'accompagne;
- `last_agent_status=running` est un claim de traitement, pas la preuve d'une
  tentative consommee; `judge_attempt_started` porte cette preuve persistante;
- `terminal_discard_failed` est un blocage de finalisation uniquement. Son run
  suivant doit projeter `judge_status=not_called` et `apply_status=not_called`,
  puis `terminal_consume_without_write` si le CAS de consommation reussit;
- un event `concurrent_window_completed` signifie que le holder de la meme
  empreinte a deja finalise avant le second caller; il ne doit ni fabriquer un
  second verdict ni requalifier un blocage en succes;
- `raise_tension` ne fait plus partie du contrat actif `mutable_judge_v2`; les champs `open_tension_*` peuvent rester vides par compatibilite read-model, ou compacter uniquement d'anciens events pre-Lot-B;
- ces anciennes tensions compactes ne requalifient pas `identity_conflicts` en source active et ne rejoignent pas le canon injecte.
- `latest_agent_activity.outcome_summaries` peut exposer seulement des summaries content-free: sujet, verdict, statut, reason code, continuity kind, compteurs et longueurs; il ne contient jamais proposition brute, fenetre brute, prompt, contenu mutable ni hash court stable derive de ces textes.

## Couches par sujet

### `static`

Bloc read-only du contenu statique canonique actuellement charge puis utilise dans la compilation runtime.

Champs minimaux:
- `storage_kind`
- `source_kind`
- `stored`
- `loaded_for_runtime`
- `actively_injected`
- `content`
- `source`
- `resource_field`
- `configured_path`
- `resolution_kind`
- `resolved_path`
- `editable_via`

Semantique:
- source physique: contenu du fichier reference par `resources.llm_identity_path` / `resources.user_identity_path`;
- cette ressource doit rester dans les racines identity canoniques autorisees (`app/data/identity/...` ou mirror `state/data/identity/...`);
- sur OVH, le `resolved_path` runtime attendu est `/app/data/identity/...`, alimente par le bind mount `/opt/platform/fridadev/state/data -> /app/data` declare dans `/opt/platform/fridadev-app/docker-compose.yml`;
- la source-of-truth host-side attendue reste donc le fichier operateur local sous `state/data/identity/...`, pas une copie parallele dans la stack runtime;
- cette couche de contenu reste une couche identitaire canonique (`personnalite`, `voix`, `posture`, `continuite`) et non un prompt de methode;
- les runtime settings conservent la reference de ressource, pas l'edition du contenu;
- `stored` reflete la presence de contenu fichier brut;
- `loaded_for_runtime` et `actively_injected` refletent le contenu runtime normalise, une fois la ressource chargee puis trimmee;
- `actively_injected` signifie seulement que cette couche participe a la forme compilee du runtime actif; cela ne requalifie ni cette couche ni son contenu en source de prompt;
- verite active: oui, si `content` est present.

### `mutable`

Bloc read-only de la mutable canonique narrative du sujet.

Champs minimaux:
- `storage_kind`
- `stored`
- `loaded_for_runtime`
- `actively_injected`
- `content`
- `source_trace_id`
- `updated_by`
- `update_reason`
- `updated_ts`
- `last_mutation_audit`

Semantique:
- source physique: table `identity_mutables`;
- cette couche reste une couche identitaire mouvante et non un sous-prompt operatoire;
- `actively_injected` signifie seulement qu'elle participe a la forme compilee active;
- `last_mutation_audit` resume la derniere mutation connue issue de `identity_mutable_audit` avec `present`, `storage_kind`, `actively_injected=false`, `subject`, `mutation_kind`, `actor`, `reason_code`, `old_chars`, `new_chars`, `source_trace_id` et `created_ts`;
- les colonnes SQL historiques `old_sha256_12` / `new_sha256_12` peuvent rester en base pour compatibilite schema, mais depuis Lot 6E les nouveaux audits ecrivent `NULL` dans ces colonnes et les read-models identity ne les projettent plus;
- `last_mutation_audit.reason_code` est un code compact et stable (`set_applied`, `clear_applied`, `mutable_judge_add`, `mutable_judge_tighten`, `mutable_judge_merge`, `mutable_judge_clear_obsolete`, ou codes legacy historiques), pas la raison humaine libre d'une edition admin;
- `last_mutation_audit` ne contient jamais le contenu mutable brut et ne devient jamais une source d'injection;
- si la mutable courante est absente, `last_mutation_audit.present=true` permet de distinguer une absence apres `clear`; `present=false` signifie seulement qu'aucun historique durable connu n'existe;
- verite active: oui, si `content` est present.

### `legacy_fragments`

Bloc read-only du legacy fragmentaire issu de `identities`.

Champs minimaux:
- `storage_kind`
- `classification`
- `runtime_authority`
- `stored`
- `loaded_for_runtime`
- `actively_injected`
- `total_count`
- `limit`
- `items[]`

Semantique:
- conserve l'historique fragmentaire de l'ancien pipeline diagnostique `persist_identity_entries(...)`, desormais inactif;
- n'est plus une verite d'injection active;
- expose `classification = "legacy_diagnostic_only"` et `runtime_authority = "historical_only"` pour empecher toute lecture canonique.

### `evidence`

Bloc read-only des evidences brutes/historiques issues de `identity_evidence`.

Champs minimaux:
- `storage_kind`
- `classification`
- `runtime_authority`
- `stored`
- `loaded_for_runtime`
- `actively_injected`
- `total_count`
- `limit`
- `items[]`

Semantique:
- couche legacy diagnostique/historique seulement;
- hors injection active et hors staging;
- expose `classification = "legacy_diagnostic_only"` et `runtime_authority = "historical_only"`;
- ne sert pas de persistence aux anciens signaux `raise_tension`; dans le regime actif `mutable_judge_v2`, ces signaux ne sont plus emis.

### `conflicts`

Bloc read-only des contradictions issues de `identity_conflicts`.

Champs minimaux:
- `storage_kind`
- `classification`
- `runtime_authority`
- `stored`
- `loaded_for_runtime`
- `actively_injected`
- `total_count`
- `limit`
- `items[]`

Semantique:
- couche legacy diagnostique/historique seulement;
- hors injection active et hors staging;
- expose `classification = "legacy_diagnostic_only"` et `runtime_authority = "historical_only"`;
- ne sert pas de persistence aux anciens signaux `raise_tension`; dans le regime actif `mutable_judge_v2`, ces signaux ne sont plus emis.

## Affichage operateur

La surface `/hermeneutic-admin` expose une section minimale:
- `Vue unifiee identity`
- au-dessus de `Fragments legacy d'identite`
- sans pretendre devenir la page `Identity` complete

Cette surface montre:
- la base canonique active et ses flags runtime;
- la lecture par sujet `llm` / `user`;
- les couches stockees legacy/evidence/conflicts;
- la separation `stored` vs `actively_injected`;
- le fait que le pilotage systeme reste distinct de cette lecture identity.
- les etats autoritatifs attente normale, retry gele, consommation terminale
  sans ecriture, reprise d'ecriture et progression effective;
- la classe, l'action, la tentative bornee, l'empreinte courte et le reason
  code sans deduire un faux `ok` de l'absence d'un champ;
- une consommation terminale propre suivie d'une progression n'est pas rendue
  comme une panne active; un retry ou write recovery bloque n'est jamais rendu
  healthy.

Depuis la fermeture du lot 5 de la surface `/identity`, cette page reemploie ce meme contrat:
- pour l'etat courant par sujet;
- sans le confondre avec le texte injecte ni la fiche structuree de jugement;
- en mode synthese compacte pour ne pas recopier exhaustivement les statuts deja visibles dans `Pilotage canonique actif`.
- en gardant sur `/identity` seulement un repere compact des representations runtime.
- en reservant le detail read-only exhaustif des representations runtime a `/hermeneutic-admin`.

Depuis `Lot 5`, cette meme surface peut aussi pointer vers une gouvernance identity distincte:
- via `GET /api/admin/identity/governance` et `POST /api/admin/identity/governance`;
- avec inventaire honnete des caps, budgets et legacy inactif;
- sans surcharger le contrat read-only du read-model lui-meme.

Depuis `Lot 3`, cette meme section peut aussi porter une edition controlee de la mutable canonique:
- distincte du contrat read-only `GET /api/admin/identity/read-model`;
- bornee a `set` / `clear` de la mutable active;
- sans rendre editable le statique ni le legacy.

Depuis `Lot 4`, cette meme section peut aussi porter une edition controlee du statique canonique:
- distincte du contrat read-only `GET /api/admin/identity/read-model`;
- bornee a `set` / `clear` du contenu statique reel;
- sans transformer les runtime settings `resources.*_identity_path` en pseudo-editeur de contenu.

Le rendu frontend de cette section dans `/hermeneutic-admin` est porte par un module dedie:
- `app/web/hermeneutic_admin/render_identity_read_model.js`
- distinct de `app/web/hermeneutic_admin/render.js`, qui reste la facade hermeneutique generale.

## Hors scope

Ce contrat ne couvre pas:
- le mutateur de la mutable canonique de `Lot 3`, documente separement dans `identity-mutable-edit-contract.md`;
- le mutateur du statique canonique de `Lot 4`, documente separement dans `identity-static-edit-contract.md`;
- la gouvernance identity `Lot 5`, documentee separement dans `identity-governance-contract.md`;
- la composition de la page dediee `Identity`, documentee separement dans `identity-surface-contract.md`.
