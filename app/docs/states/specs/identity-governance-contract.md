# Identity Governance Contract

Statut: spec vivante  
Portee: gouvernance identity visible dans `/hermeneutic-admin` puis reemployee par `/identity`
Lot ferme: `Lot 5`

## But

Ce contrat expose une gouvernance identity distincte du read-model:
- lecture compacte des knobs identity reels;
- lecture structuree du regime actif readonly, sans le traiter comme une simple liste de caps;
- classification honnete entre actif, editable, readonly doctrinal et legacy inactif;
- edition bornee du sous-ensemble runtime-safe;
- aucun melange avec le legacy fragmentaire ni avec l'edition du contenu static/mutable.

## Routes

- `GET /api/admin/identity/governance`
- `POST /api/admin/identity/governance`

Ces routes sont:
- protegees par la meme garde admin que les autres routes `/api/admin/*`;
- distinctes de `GET /api/admin/identity/read-model`;
- distinctes de `POST /api/admin/identity/mutable`;
- distinctes de `POST /api/admin/identity/static`;
- distinctes du legacy `/api/admin/hermeneutics/identity-candidates`.

## Source de verite

Le backing store retenu est:
- `runtime_settings.identity_governance`

Cette section runtime ne remplace pas le contrat read-model:
- elle conserve dix valeurs runtime-backed, dont six seuils historiques readonly;
- seules les quatre cles `CONTEXT_HINTS_*` sont operator-gouvernables depuis cette API;
- l'edition operateur reste exposee dans `/hermeneutic-admin`, pas dans `/admin` generique;
- `/api/admin/settings` peut la montrer comme section runtime existante, mais la surface produit de gouvernance identity reste la section `Gouvernance identity`.

## Contrat JSON de lecture

Top-level:

```json
{
  "ok": true,
  "governance_version": "v1",
  "item_count": 0,
  "regime_section_count": 0,
  "editable_count": 0,
  "readonly_count": 0,
  "legacy_inactive_count": 0,
  "active_judge_v2_count": 0,
  "active_auxiliary_count": 0,
  "active_legacy_compatibility_count": 0,
  "regime_active_readonly_count": 0,
  "regime_doctrine_locked_count": 0,
  "regime_legacy_inactive_count": 0,
  "read_via": "/api/admin/identity/governance",
  "editable_via": "/api/admin/identity/governance",
  "source_of_truth": "runtime_settings.identity_governance",
  "active_prompt_contract": "static + mutable narrative",
  "identity_input_schema_version": "v2",
  "regime_sections": [],
  "items": []
}
```

Chaque item expose au minimum:
- `key`
- `label`
- `category`
- `current_value`
- `value_type`
- `unit`
- `source_kind`
- `source_ref`
- `active_scope`
- `editable`
- `editable_via`
- `validation`
- `operator_note`

Pour tous les knobs runtime-backed, editables ou historiques readonly, l'item expose aussi:
- `source_state`
- `source_reason`

Chaque `regime_section` expose au minimum:
- `key`
- `label`
- `classification`
- `active_scope`
- `source_kind`
- `source_ref`
- `editable = false`
- `operator_note`
- `details`

## Taxonomie retenue

Categories utilisees:
- `active_judge_v2_readonly`
- `active_auxiliary_editable`
- `active_auxiliary_readonly`
- `active_legacy_compatibility_readonly`
- `legacy_inactive_readonly`

Classifications utilisees pour `regime_sections`:
- `active_readonly`
- `doctrine_locked`
- `legacy_inactive`

Semantique:
- `active_judge_v2_readonly`: valeur lue par le juge mutable V2 courant ou sa garde d'apply;
- `active_auxiliary_*`: valeur lue par un auxiliaire runtime actif, sans autorite sur le juge V2;
- `active_legacy_compatibility_readonly`: traitement legacy encore execute mais sans autorite sur le canon ni le juge V2;
- `legacy_inactive_readonly`: valeur historique visible, sans consommateur dans le chemin chat courant.

## Inventaire minimal ferme en Lot 5

### Runtime-backed historiques readonly

- `IDENTITY_MIN_CONFIDENCE`
- `IDENTITY_DEFER_MIN_CONFIDENCE`
- `IDENTITY_MIN_RECURRENCE_FOR_DURABLE`
- `IDENTITY_RECURRENCE_WINDOW_DAYS`
- `IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS`
- `IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS`

Ces six valeurs restent lues depuis leur ligne `runtime_settings` pour que la
surface expose la valeur persistee. Elles ne sont plus dans `EDITABLE_KEYS`:
leurs seuls consommateurs metier appartiennent a
`preview_identity_entries` / `persist_identity_entries`, writer fragmentaire
retire du chemin chat courant. Elles n'atteignent ni le juge V2, ni son apply.

### Auxiliaires actifs editables

- `CONTEXT_HINTS_MAX_ITEMS`
- `CONTEXT_HINTS_MAX_TOKENS`
- `CONTEXT_HINTS_MAX_AGE_DAYS`
- `CONTEXT_HINTS_MIN_CONFIDENCE`

### Juge V2 actif readonly

- `IDENTITY_MUTABLE_TARGET_CHARS`
- `IDENTITY_MUTABLE_MAX_CHARS`

### Auxiliaire actif readonly

- `identity_extractor_max_tokens`

### Compatibilite legacy encore executee readonly

- `IDENTITY_DECAY_FACTOR`

### Legacy inactifs visibles seulement

- `IDENTITY_TOP_N`
- `IDENTITY_MAX_TOKENS`

Important:
- `IDENTITY_TOP_N` et `IDENTITY_MAX_TOKENS` restent exposes pour dire vrai sur les survivances legacy;
- ils ne doivent pas etre requalifies comme knobs actifs ni redevenir editables;
- `identity_extractor_max_tokens` est une lecture readonly de `identity_extractor_model.max_tokens`; l'edition reste dans les runtime settings du caller;
- `IDENTITY_DECAY_FACTOR` est lu a la creation d'une nouvelle conversation et multiplie seulement `identities.weight`; la table legacy n'alimente plus le canon actif;
- le statique n'introduit pas de cap caracteres Lot 5 distinct;
- la mutable garde sa doctrine `3000 / 3300`, visible mais verrouillee;
- ces caps ne racontent pas a eux seuls tout le regime runtime: la gouvernance distingue juge V2, hints actifs, compatibilite legacy executee et valeurs legacy inactives.
- transition 2026-05-25: ces sections pre-refonte restent des lectures du runtime livre, mais ne sont plus doctrine cible du writer mutable. Le contrat cible est `mutable-identity-judge-contract.md`.

## Sections readonly du regime actif

`regime_sections` complete les `items` sans dupliquer le read-model:
- `active_canon_contract`: rappelle que le canon actif injecte reste `static + mutable narrative`, distinct du staging;
- `staging_contract`: rappelle la fenetre technique `conversation_scoped_latest`, sa cible a `5` paires completes et son statut non injecte / non editable;
- `scoring_contract`: rappelle le scoring Python deterministe du runtime pre-refonte comme legacy a supprimer; il ne porte plus de seuil numerique actif et ne doit plus agir comme writer canonique score-first dans le chemin mutable actif;
- `promotion_and_suspension_contract`: rappelle la promotion `mutable -> static` et la suspension automatique comme capacites pre-refonte neutralisees dans le chemin mutable actif; toute future promotion devra etre un chantier separe;
- `mutable_budget_contract`: rappelle que `3000 / 3300` borne seulement la mutable canonique, doctrine verrouillee;
- `legacy_identity_contract`: rappelle que `identities`, `identity_evidence` et `identity_conflicts` restent `legacy_diagnostic_only`, hors injection active.

## Contrat JSON d'update

Requete:

```json
{
  "updates": {
    "CONTEXT_HINTS_MAX_ITEMS": 3
  },
  "reason": "ajustement exploitation"
}
```

Regles:
- `updates` requis
- `reason` requis
- `reason` max: `240` caracteres
- seules `CONTEXT_HINTS_MAX_ITEMS`, `CONTEXT_HINTS_MAX_TOKENS`, `CONTEXT_HINTS_MAX_AGE_DAYS` et `CONTEXT_HINTS_MIN_CONFIDENCE` sont acceptees;
- les six seuils historiques runtime-backed sont refuses avec `governance_key_readonly`;
- aucune route `/api/admin/settings/*` n'expose la section `identity_governance` en PATCH; seule la route dediee applique l'allowlist `EDITABLE_KEYS`;
- aucune mutation partielle ambigue
- validation fail-closed avant ecriture

## Invariants minimums

- `CONTEXT_HINTS_MAX_ITEMS >= 1`
- `CONTEXT_HINTS_MAX_TOKENS >= 1`
- `CONTEXT_HINTS_MAX_TOKENS <= config.MAX_TOKENS`
- `CONTEXT_HINTS_MAX_AGE_DAYS >= 1`
- tous les ratios restent dans `[0.0, 1.0]`

Le validateur de la section conserve les controles historiques des six valeurs
stockees afin de ne pas modifier le contrat de stockage. Ces controles ne les
rendent ni actives ni editables.

## Reponse compacte d'update

Reponse attendue:
- `ok`
- `governance_version`
- `reason_code`
- `validation_ok`
- `validation_error`
- `changed_keys`
- `changed_count`
- `editable_via`
- `source_of_truth`
- `active_prompt_contract = "static + mutable narrative"`
- `identity_input_schema_version = "v2"`

Mapping HTTP:
- rejets contrat / readonly / invariant / validation: `400`
- indisponibilite runtime-settings store (`reason_code = governance_store_unavailable`): `500`

## Audit compact

Chaque tentative d'update produit:
- `event = "identity_governance_admin_edit"`
- `changed_keys`
- `changed_count`
- `old_values`
- `new_values`
- `validation_ok`
- `validation_error`
- `reason_code`
- `reason_len`
- `source_of_truth`

Interdits:
- contenu identity brut
- preview textuelle
- excerpt du statique ou de la mutable

Cet event alimente aussi `Corrections recentes` via:
- `GET /api/admin/hermeneutics/corrections-export`
- avec payload compact seulement

## Surface operateur

`/hermeneutic-admin` expose:
- `Vue unifiee identity`
- `Gouvernance identity`
- `Fragments legacy d'identite`

`Gouvernance identity` doit:
- montrer la classification de chaque knob;
- montrer aussi les sections readonly du regime actif, distinctes des simples knobs;
- rappeler que `3000 / 3300` borne seulement la mutable canonique et non tout le regime identity;
- afficher des groupes distincts `juge V2`, `auxiliaire actif`, `compatibilite legacy active` et `legacy inactif`;
- rendre editables uniquement les quatre cles de hints;
- rester distincte du read-model et des editeurs static/mutable.

L'editeur mutable:
- lit le budget runtime depuis le payload identity actif expose (`mutable_budget`);
- ne doit plus embarquer un fallback UI silencieux `3000 / 3300`;
- si ce budget manque, doit le signaler explicitement au lieu d'inventer une pseudo source locale.

Depuis `Lot 6`, la page `/identity` reemploie ce meme contrat:
- sans changer les routes `GET/POST /api/admin/identity/governance`;
- avec une lecture plus explicite pour l'operateur final;
- sans requalifier les knobs legacy inactifs.

## Hors scope

Ce contrat ne couvre pas:
- la composition de la page `Identity`, documentee separement dans `identity-surface-contract.md`;
- une refonte large du systeme runtime settings admin;
- la resurrection du legacy comme source active.
