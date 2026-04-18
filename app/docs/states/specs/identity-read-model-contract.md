# Identity Read Model Contract

Statut: spec vivante  
Portee: lecture operator-facing read-only reemployee par `/hermeneutic-admin` et `/identity`
Lot ferme: `Lot 2`

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
- `legacy_identity_pipeline_status = "legacy_diagnostic_only"`
- `legacy_identity_pipeline_recorded_via = "persist_identity_entries"`
- `legacy_identity_pipeline_storage = "identities + identity_evidence + identity_conflicts"`
- `read_surface_stage = "lot_b5_identity_operator_truth"`
- `used_identity_ids = []`
- `used_identity_ids_count = 0`
- `governance_read_via = "/api/admin/identity/governance"`
- `governance_editable_via = "/api/admin/identity/governance"`
- `runtime_representations_read_via = "/api/admin/identity/runtime-representations"`
- `identity_runtime_regime` comme rappel compact des caps/seuils actifs (`mutable_budget`, `staging_target_pairs`, seuils `0.35 / 0.60`, promotion et suspension)
- `identity_staging` comme verite read-only distincte du canon actif injecte

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
  "identity_staging": {},
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
- `buffer_frozen`
- `last_agent_status`
- `last_agent_reason`
- `last_agent_run_ts`
- `updated_ts`
- `auto_canonization_suspended`
- `latest_agent_activity`

Semantique:
- ce bloc ne requalifie pas le staging en canon actif;
- il montre l'etat du buffer et du dernier passage agent sans dump du buffer brut;
- `latest_agent_activity` resume compactement le dernier verdict utile, les promotions recentes et les tensions ouvertes `raise_conflict` pour cette conversation;
- quand un run se termine sans write canonique mais garde au moins une tension ouverte, son resume compact ne doit pas etre aplati en `completed_no_change` et utilise `completed_with_open_tension`;
- les tensions ouvertes du nouvel agent y vivent seulement comme activite periodique compacte conversation-scoped, avec `open_tension_count`, `open_tensions_storage_kind = "identity_periodic_agent_latest_activity"`, `open_tensions_scope_kind = "conversation_scoped_latest"` et `open_tensions_actively_injected = false`;
- ces tensions ouvertes ne requalifient pas `identity_conflicts` en source active et ne rejoignent pas le canon injecte.

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

Semantique:
- source physique: table `identity_mutables`;
- cette couche reste une couche identitaire mouvante et non un sous-prompt operatoire;
- `actively_injected` signifie seulement qu'elle participe a la forme compilee active;
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
- conserve l'historique fragmentaire legacy du pipeline diagnostique `persist_identity_entries(...)`;
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
- ne sert pas de persistence aux tensions `raise_conflict` du regime periodique actif, qui restent dans `latest_agent_activity` seulement.

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
- ne sert pas de persistence aux tensions `raise_conflict` du regime periodique actif, qui restent dans `latest_agent_activity` seulement.

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

Depuis la fermeture du lot 5 de la surface `/identity`, cette page reemploie ce meme contrat:
- pour l'etat courant par sujet;
- sans le confondre avec le texte injecte ni la fiche structuree de jugement;
- en mode synthese compacte pour ne pas recopier exhaustivement les statuts deja visibles dans `Pilotage canonique actif`.
- en gardant sur `/identity` seulement un repere compact des representations runtime.
- en reservant le detail read-only exhaustif des representations runtime a `/hermeneutic-admin`.

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
