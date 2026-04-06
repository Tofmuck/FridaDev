# Identity Mutable Edit Contract

Statut: spec vivante  
Portee: edition operateur controlee de la mutable canonique avant la future surface `Identity`  
Lot ferme: `Lot 3`

## But

Ce contrat ouvre une edition controlee de la mutable canonique active, sans rouvrir:
- l'edition du statique (`Lot 4`);
- la gouvernance des caps et seuils (`Lot 5`);
- la future page `Identity` et sa navigation globale (`Lot 6`);
- les vieux mutateurs legacy `force_accept`, `force_reject`, `relabel`.

Ici, `dynamique` veut dire:
- la mutable canonique narrative stockee dans `identity_mutables`;
- injectee activement via `static + mutable narrative`;
- et non plus le legacy fragmentaire `accepted|deferred|rejected`.

## Route

- `POST /api/admin/identity/mutable`

Cette route est:
- protegee par la meme garde admin que les autres routes `/api/admin/*`;
- distincte de `GET /api/admin/identity/read-model`, qui reste read-only;
- distincte de `/api/admin/hermeneutics/identity-candidates`, qui reste legacy / evidence-only.

## Contrat JSON

Requete:

```json
{
  "subject": "llm",
  "action": "set",
  "content": "Frida conserve une voix sobre et concise.",
  "reason": "correction operateur"
}
```

Ou pour effacement:

```json
{
  "subject": "user",
  "action": "clear",
  "content": "",
  "reason": "mutable obsolete"
}
```

Regles:
- `subject` requis: `llm` | `user`
- `action` requis: `set` | `clear`
- `reason` requis pour chaque action
- `reason` max: `240` caracteres
- `content` requis pour `set`
- `content` doit etre vide pour `clear`

## Validation mutable

La mutable canonique editee par l'operateur suit la meme discipline doctrinale que le runtime:
- cible: `1500` caracteres
- plafond dur: `1650` caracteres
- aucune troncature cachee
- si `content > 1650`: rejet, aucune ecriture

No-op explicites:
- `set` avec contenu identique -> `changed = false`, `reason_code = "unchanged"`
- `clear` alors qu'aucune mutable n'est stockee -> `changed = false`, `reason_code = "already_cleared"`

## Effets de bord autorises

La route peut seulement:
- upserter la mutable canonique dans `identity_mutables`;
- effacer la mutable canonique pour un sujet;
- mettre a jour `updated_by = "admin_identity_mutable_edit"` et `update_reason`;
- emettre un audit admin compact.

La route ne doit pas:
- modifier le statique;
- ressusciter le legacy fragmentaire comme verite d'injection active;
- toucher a `identities`, `identity_evidence`, `identity_conflicts` comme source active;
- reouvrir `force_accept`, `force_reject`, `relabel`.

## Reponse

Reponse compacte attendue:
- `ok`
- `subject`
- `action`
- `old_len`
- `new_len`
- `changed`
- `stored_after`
- `validation_ok`
- `validation_error`
- `reason_code`
- `active_identity_source = "identity_mutables"`
- `active_prompt_contract = "static + mutable narrative"`
- `identity_input_schema_version = "v2"`
- `mutable_budget`

## Audit compact

Chaque tentative d'edition produit un event admin compact:
- `event = "identity_mutable_admin_edit"`
- `subject`
- `action`
- `old_len`
- `new_len`
- `changed`
- `stored_after`
- `validation_ok`
- `validation_error`
- `reason_code`
- `reason_len`
- `active_identity_source`
- `active_prompt_contract`
- `identity_input_schema_version`

Interdits:
- contenu mutable brut
- preview textuelle
- excerpt du texte operateur

Cet event alimente aussi `Corrections recentes` via:
- `GET /api/admin/hermeneutics/corrections-export`
- sans requalifier le legacy ni exposer de contenu brut

## Surface operateur minimale

Avant la future page `Identity`, `/hermeneutic-admin` expose:
- la section `Vue unifiee identity`
- une edition controlee bornee a la mutable canonique `llm` / `user`
- un editeur statique canonique distinct, documente a part pour `Lot 4`
- le read-model unifie en dessous
- la section `Fragments legacy d'identite` toujours read-only / legacy-only

## Hors scope

Ce contrat ne couvre pas encore:
- l'edition du statique (`Lot 4`);
- la gouvernance UI/backend des caps et seuils (`Lot 5`);
- la future page `Identity` et sa navigation globale (`Lot 6`).
