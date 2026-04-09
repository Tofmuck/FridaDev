# Identity Read Model Contract

Statut: spec vivante  
Portee: lecture operator-facing read-only reemployee par `/hermeneutic-admin` et `/identity`
Lot ferme: `Lot 2`

## But

Ce contrat definit une lecture unifiee et honnete du systeme identity reel, sans rouvrir le runtime actif.

Le read-model lui-meme reste read-only, meme si les surfaces operator-facing peuvent aussi porter, depuis `Lot 3`, `Lot 4`, `Lot 5` et `Lot 6`, des editions ou lectures distinctes documentees a part.

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
- `used_identity_ids = []`
- `used_identity_ids_count = 0`
- `governance_read_via = "/api/admin/identity/governance"`
- `governance_editable_via = "/api/admin/identity/governance"`
- `runtime_representations_read_via = "/api/admin/identity/runtime-representations"`

Le read-model ne doit pas:
- reparser le prompt rendu comme source de verite;
- laisser croire que `active_prompt_contract` designe le pilotage systeme source;
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
- la source-of-truth host-side attendue reste donc le fichier suivi par le repo sous `state/data/identity/...`, pas une copie parallele dans la stack runtime;
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

Semantique:
- source physique: table `identity_mutables`;
- cette couche reste une couche identitaire mouvante et non un sous-prompt operatoire;
- `actively_injected` signifie seulement qu'elle participe a la forme compilee active;
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

Depuis `Lot 6`, la page `/identity` reemploie ce meme contrat:
- pour l'etat courant par sujet;
- sans le confondre avec le texte injecte ni la fiche structuree de jugement;
- en le combinant avec `GET /api/admin/identity/runtime-representations`.

Depuis `Lot 5`, cette meme surface peut aussi pointer vers une gouvernance identity distincte:
- via `GET /api/admin/identity/governance` et `POST /api/admin/identity/governance`;
- avec inventaire honnete des caps/seuils/budgets;
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
