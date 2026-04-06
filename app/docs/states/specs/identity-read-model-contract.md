# Identity Read Model Contract

Statut: spec vivante  
Portee: lecture operator-facing read-only avant la future surface `Identity`  
Lot ferme: `Lot 2`

## But

Ce contrat definit une lecture unifiee et honnete du systeme identity reel, sans rouvrir le runtime actif ni lancer encore les lots d'edition (`Lot 3`, `Lot 4`) ou de gouvernance des caps (`Lot 5`).

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
- `stored`
- `loaded_for_runtime`
- `actively_injected`
- `content`
- `source`

Semantique:
- source physique: ressource statique referencee par le runtime;
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

Avant la future page `Identity`, la surface `/hermeneutic-admin` expose une section read-only minimale:
- `Vue unifiee identity`
- au-dessus de `Fragments legacy d'identite`
- sans mutateur
- sans navigation globale nouvelle

Cette surface montre:
- la verite active runtime;
- la lecture par sujet `llm` / `user`;
- les couches stockees legacy/evidence/conflicts;
- la separation `stored` vs `actively_injected`.

Le rendu frontend de cette section dans `/hermeneutic-admin` est porte par un module dedie:
- `app/web/hermeneutic_admin/render_identity_read_model.js`
- distinct de `app/web/hermeneutic_admin/render.js`, qui reste la facade hermeneutique generale.

## Hors scope

Ce contrat ne couvre pas encore:
- l'edition du dynamique (`Lot 3`);
- l'edition du statique (`Lot 4`);
- la gouvernance UI/backend des caps et seuils (`Lot 5`);
- la future page dediee `Identity` et sa navigation globale (`Lot 6`).
