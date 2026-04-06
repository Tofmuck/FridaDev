# Identity Read Model Contract

Statut: spec vivante  
Portee: lecture operator-facing read-only avant la future surface `Identity`  
Lot ferme: `Lot 2`

## But

Ce contrat definit une lecture unifiee et honnete du systeme identity reel, sans rouvrir le runtime actif.

Le read-model lui-meme reste read-only, meme si la meme section operator-facing peut aussi porter, depuis `Lot 3` et `Lot 4`, des editions bornees documentees a part.

Il sert a :
- montrer la verite active runtime;
- distinguer clairement ce qui est charge, stocke, injecte, legacy, evidence et conflit;
- fournir une base stable pour la future surface `Identity`.

## Route

- `GET /api/admin/identity/read-model`

Cette route est:
- read-only;
- protegee par la meme garde admin que les autres routes `/api/admin/*`;
- distincte de `/api/admin/hermeneutics/identity-candidates`, qui reste legacy / evidence-only.

## Verite active exposee

Le read-model doit exposer explicitement:
- `active_identity_source = "identity_mutables"`
- `active_static_source = "resource_path_content"`
- `active_prompt_contract = "static + mutable narrative"`
- `identity_input_schema_version = "v2"`
- `used_identity_ids = []`
- `used_identity_ids_count = 0`

Le read-model ne doit pas:
- reparser le prompt rendu comme source de verite;
- laisser croire que `identities` pilote encore l'injection active;
- masquer la separation entre runtime actif et couches legacy.

## Structure canonique

Top-level:

```json
{
  "ok": true,
  "read_model_version": "v1",
  "active_runtime": {},
  "subjects": {
    "llm": {},
    "user": {}
  }
}
```

Chaque sujet expose exactement ces couches:
- `static`
- `mutable`
- `legacy_fragments`
- `evidence`
- `conflicts`

## Couches par sujet

### `static`

Bloc read-only du contenu statique actuellement charge puis injecte.

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
- les runtime settings conservent la reference de ressource, pas l'edition du contenu;
- `stored`, `loaded_for_runtime` et `actively_injected` passent a `false` quand le contenu est vide, meme si la reference de ressource reste configuree;
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

Semantique:
- source physique: table `identity_mutables`;
- verite active: oui, si `content` est present.

### `legacy_fragments`

Bloc read-only du legacy fragmentaire issu de `identities`.

Champs minimaux:
- `storage_kind`
- `stored`
- `loaded_for_runtime`
- `actively_injected`
- `total_count`
- `limit`
- `items[]`

Semantique:
- conserve l'historique fragmentaire legacy;
- n'est plus une verite d'injection active.

### `evidence`

Bloc read-only des evidences brutes/historiques issues de `identity_evidence`.

Champs minimaux:
- `storage_kind`
- `stored`
- `loaded_for_runtime`
- `actively_injected`
- `total_count`
- `limit`
- `items[]`

### `conflicts`

Bloc read-only des contradictions issues de `identity_conflicts`.

Champs minimaux:
- `storage_kind`
- `stored`
- `loaded_for_runtime`
- `actively_injected`
- `total_count`
- `limit`
- `items[]`

## Affichage operateur minimal

Avant la future page `Identity`, la surface `/hermeneutic-admin` expose une section minimale:
- `Vue unifiee identity`
- au-dessus de `Fragments legacy d'identite`
- sans navigation globale nouvelle

Cette surface montre:
- la verite active runtime;
- la lecture par sujet `llm` / `user`;
- les couches stockees legacy/evidence/conflicts;
- la separation `stored` vs `actively_injected`.

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

Ce contrat ne couvre pas encore:
- le mutateur de la mutable canonique de `Lot 3`, documente separement dans `identity-mutable-edit-contract.md`;
- le mutateur du statique canonique de `Lot 4`, documente separement dans `identity-static-edit-contract.md`;
- la gouvernance UI/backend des caps et seuils (`Lot 5`);
- la future page dediee `Identity` et sa navigation globale (`Lot 6`).
