# Identity Governance Contract

Statut: spec vivante  
Portee: caps, seuils et budgets identity visibles dans `/hermeneutic-admin` puis reemployes par `/identity`
Lot ferme: `Lot 5`

## But

Ce contrat expose une gouvernance identity distincte du read-model:
- lecture compacte des knobs identity reels;
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

Le backing store editable retenu est:
- `runtime_settings.identity_governance`

Cette section runtime ne remplace pas le contrat read-model:
- elle porte seulement les knobs operator-gouvernables;
- l'edition operateur reste exposee dans `/hermeneutic-admin`, pas dans `/admin` generique;
- `/api/admin/settings` peut la montrer comme section runtime existante, mais la surface produit de gouvernance identity reste la section `Gouvernance identity`.

## Contrat JSON de lecture

Top-level:

```json
{
  "ok": true,
  "governance_version": "v1",
  "item_count": 0,
  "editable_count": 0,
  "readonly_count": 0,
  "legacy_inactive_count": 0,
  "active_runtime_count": 0,
  "active_subpipeline_count": 0,
  "read_via": "/api/admin/identity/governance",
  "editable_via": "/api/admin/identity/governance",
  "source_of_truth": "runtime_settings.identity_governance",
  "active_prompt_contract": "static + mutable narrative",
  "identity_input_schema_version": "v2",
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

Pour les knobs runtime-backed editables, l'item expose aussi:
- `source_state`
- `source_reason`

## Taxonomie retenue

Categories utilisees:
- `active_runtime_editable`
- `active_subpipeline_editable`
- `doctrine_locked_readonly`
- `active_subpipeline_readonly`
- `legacy_inactive_readonly`

Semantique:
- `active_runtime_*`: agit encore sur le runtime actif `static + mutable narrative`
- `active_subpipeline_*`: agit encore sur un sous-pipeline identity reel sans piloter directement l'injection active
- `doctrine_locked_readonly`: agit reellement mais reste verrouille par doctrine deja fermee
- `legacy_inactive_readonly`: survivance de code legacy visible mais non branchée sur le chemin actif

## Inventaire minimal ferme en Lot 5

### Editables

- `IDENTITY_MIN_CONFIDENCE`
- `IDENTITY_DEFER_MIN_CONFIDENCE`
- `IDENTITY_MIN_RECURRENCE_FOR_DURABLE`
- `IDENTITY_RECURRENCE_WINDOW_DAYS`
- `IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS`
- `IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS`
- `CONTEXT_HINTS_MAX_ITEMS`
- `CONTEXT_HINTS_MAX_TOKENS`
- `CONTEXT_HINTS_MAX_AGE_DAYS`
- `CONTEXT_HINTS_MIN_CONFIDENCE`

### Read-only doctrinaux ou actifs non rouverts

- `IDENTITY_MUTABLE_TARGET_CHARS`
- `IDENTITY_MUTABLE_MAX_CHARS`
- `identity_extractor_max_tokens`
- `IDENTITY_DECAY_FACTOR`

### Legacy inactifs visibles seulement

- `IDENTITY_TOP_N`
- `IDENTITY_MAX_TOKENS`

Important:
- `IDENTITY_TOP_N` et `IDENTITY_MAX_TOKENS` restent exposes pour dire vrai sur les survivances legacy;
- ils ne doivent pas etre requalifies comme knobs actifs ni redevenir editables;
- le statique n'introduit pas de cap caracteres Lot 5 distinct;
- la mutable garde sa doctrine `3000 / 3300`, visible mais verrouillee.

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
- seules les cles editables sont acceptees
- aucune mutation partielle ambigue
- validation fail-closed avant ecriture

## Invariants minimums

- `IDENTITY_DEFER_MIN_CONFIDENCE <= IDENTITY_MIN_CONFIDENCE`
- `IDENTITY_MIN_RECURRENCE_FOR_DURABLE >= IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS`
- `IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS >= 1`
- `IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS >= 1`
- `CONTEXT_HINTS_MAX_ITEMS >= 1`
- `CONTEXT_HINTS_MAX_TOKENS >= 1`
- `CONTEXT_HINTS_MAX_TOKENS <= config.MAX_TOKENS`
- `CONTEXT_HINTS_MAX_AGE_DAYS >= 1`
- tous les ratios restent dans `[0.0, 1.0]`

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
- rendre editable uniquement le sous-ensemble runtime-safe retenu;
- rester distincte du read-model et des editeurs static/mutable.

Depuis `Lot 6`, la page `/identity` reemploie ce meme contrat:
- sans changer les routes `GET/POST /api/admin/identity/governance`;
- avec une lecture plus explicite pour l'operateur final;
- sans requalifier les knobs legacy inactifs.

## Hors scope

Ce contrat ne couvre pas:
- la composition de la page `Identity`, documentee separement dans `identity-surface-contract.md`;
- une refonte large du systeme runtime settings admin;
- la resurrection du legacy comme source active.
