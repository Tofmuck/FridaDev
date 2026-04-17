# Identity Static Edit Contract

Statut: spec vivante  
Portee: edition operateur controlee du statique canonique, exposee dans `/hermeneutic-admin` puis reemployee dans `/identity`
Lot ferme: `Lot 4`

## But

Ce contrat ouvre une edition controlee du statique canonique actif, sans rouvrir:
- la gouvernance des caps et seuils (`Lot 5`);
- le legacy fragmentaire comme source active;
- la doctrine runtime `static + mutable narrative`.

Ici, `statique` veut dire:
- le contenu du fichier actuellement reference par `resources.llm_identity_path` ou `resources.user_identity_path`;
- charge puis injecte activement par le runtime;
- la couche identitaire canonique stable (`personnalite`, `voix`, `posture`, `continuite`), et non un sous-prompt operatoire;
- distinct de la mutable canonique `identity_mutables`;
- distinct du legacy `identities`, `identity_evidence`, `identity_conflicts`.

Donc:
- le statique edite ici ne doit pas devenir une zone d'instructions de travail, de methode, de priorites, de format ou d'outillage;
- le fait qu'il soit ensuite injecte dans le runtime n'en fait pas une source de prompt canonique.

## Route

- `POST /api/admin/identity/static`

Cette route est:
- protegee par la meme garde admin que les autres routes `/api/admin/*`;
- distincte de `GET /api/admin/identity/read-model`, qui reste read-only;
- distincte de `POST /api/admin/identity/mutable`, qui reste borne a la mutable canonique;
- distincte du legacy `/api/admin/hermeneutics/identity-candidates`, qui reste legacy / evidence-only.

## Verite durable retenue

La verite durable du statique reste file-backed:
- les runtime settings `resources.llm_identity_path` et `resources.user_identity_path` restent des references de ressource;
- l'edition operateur agit sur le contenu du fichier resolu par ces references;
- aucune deuxieme verite DB du statique n'est introduite.

Le perimetre autorise reste borne aux racines identity canoniques:
- `app/data/identity/...`;
- et son mirror host-side `state/data/identity/...` quand la ressource runtime relative est resolue hors conteneur;
- un chemin absolu n'est accepte que s'il resolve dans une de ces racines;
- tout fichier existant hors de ce perimetre est refuse fail-closed.

Depuis le regime periodique identity, cette verite file-backed inclut aussi un fichier compagnon de metadata d'ecriture:
- `.{nom-du-fichier}.identity-meta.json` a cote de la ressource statique active;
- ce sidecar stocke `updated_by`, `update_reason` et `updated_ts`;
- il reste file-backed, pas DB-backed, et ne cree pas une deuxieme verite canonique du statique;
- il sert a distinguer un edit operateur recent d'une auto-promotion du `identity_periodic_agent`.

Sur OVH et dans le deploiement Docker standard actuellement retenu:
- la source canonique de `llm.static` est le fichier operateur local `state/data/identity/llm_identity.txt`, non versionne dans Git;
- la source canonique de `user.static` est le fichier operateur local `state/data/identity/user_identity.txt`, non versionne dans Git;
- le repo versionne seulement `state/data/identity/README.md` et les exemples `*.example.txt`;
- le runtime consomme cette meme arborescence via le bind mount `/opt/platform/fridadev/state/data -> /app/data` declare dans `/opt/platform/fridadev-app/docker-compose.yml`;
- le read-model et l'admin continuent d'exposer la reference runtime `data/identity/...`, mais cette reference doit toujours resoudre vers cette arborescence canonique.

`clear` ne supprime pas le fichier:
- il conserve la ressource referencee;
- il ecrit un contenu vide;
- il laisse la validation du path intacte.

Si la ressource runtime referencee est introuvable ou non resolue:
- rejet fail-closed;
- aucune creation magique de fichier;
- aucune ecriture partielle.

## Contrat JSON

Requete:

```json
{
  "subject": "llm",
  "action": "set",
  "content": "Frida garde une voix sobre et structuree.",
  "reason": "correction operateur"
}
```

Ou pour vidage:

```json
{
  "subject": "user",
  "action": "clear",
  "content": "",
  "reason": "statique obsolete"
}
```

Regles:
- `subject` requis: `llm` | `user`
- `action` requis: `set` | `clear`
- `reason` requis pour chaque action
- `reason` max: `240` caracteres
- `content` requis pour `set`
- `content` doit etre vide pour `clear`
- aucune troncature cachee
- aucun plafond Lot 5 n'est introduit ici

No-op explicites:
- `set` avec contenu fichier brut identique -> `changed = false`, `reason_code = "unchanged"`
- `clear` alors que le contenu fichier brut est deja vide -> `changed = false`, `reason_code = "already_cleared"`

Depuis `Lot 5`:
- aucun budget caracteres statique distinct n'est introduit;
- la gouvernance identity expose explicitement cette absence de cap doctrinal pour le statique.

## Effets de bord autorises

La route peut seulement:
- lire la ressource statique active resolue par le runtime;
- ecrire atomiquement le contenu du fichier resolu;
- ecrire un contenu vide pour `clear`;
- ecrire ou mettre a jour le sidecar `.{nom-du-fichier}.identity-meta.json` associe a cette ressource;
- y tracer `updated_by`, `update_reason` et `updated_ts` comme write-trace file-backed du statique;
- emettre un audit admin compact.

Cette write-trace file-backed sert aussi de source de verite operateur pour le garde `recent static operator edit`:
- un edit `admin_identity_static_edit` recent peut suspendre une auto-promotion `mutable -> static`;
- une auto-promotion `identity_periodic_agent` ne doit pas etre relue comme un edit operateur humain.

La route ne doit pas:
- modifier `identity_mutables`;
- modifier le legacy fragmentaire comme verite active;
- requalifier `resources.*_identity_path` en editeur de contenu.
- ecrire dans un fichier existant hors des racines identity autorisees.

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
- `active_static_source = "resource_path_content"`
- `static_source_kind = "resource_path"`
- `resource_field`
- `resolution_kind`
- `editable_via = "/api/admin/identity/static"`
- `active_prompt_contract = "static + mutable narrative"`
- `identity_input_schema_version = "v2"`

Convention:
- le fichier recoit exactement le contenu demande pour `set`;
- `old_len` et `new_len` refletent la longueur du contenu fichier brut avant/apres ecriture;
- la normalisation runtime (`strip`) reste reservee a l'injection active et ne doit pas fausser `clear`, `unchanged` ou `stored_after`.
- sur un bind mount repo, le remplacement atomique doit preserver le mode et l'ownership du fichier cible existant; une edition admin ne doit pas rendre la ressource canonique root-owned par derive du conteneur.

## Audit compact

Chaque tentative d'edition produit un event admin compact:
- `event = "identity_static_admin_edit"`
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
- `static_source_kind`
- `resource_field`
- `resolution_kind`
- `active_static_source`
- `active_prompt_contract`
- `identity_input_schema_version`

Interdits:
- contenu statique brut
- preview textuelle
- excerpt du texte operateur

Cet event alimente aussi `Corrections recentes` via:
- `GET /api/admin/hermeneutics/corrections-export`
- sans exposer de contenu brut

## Surface operateur

`/hermeneutic-admin` expose:
- la section `Vue unifiee identity`
- une edition controlee bornee au statique canonique `llm` / `user`
- le read-model unifie en dessous
- la section `Fragments legacy d'identite` toujours read-only / legacy-only

Les runtime settings `resources.*_identity_path` restent visibles sur `/admin`:
- comme references de ressource;
- pas comme pseudo-editeur de contenu.

Depuis `Lot 6`, la page `/identity` reemploie le meme contrat:
- sans changer la route `POST /api/admin/identity/static`;
- en rappelant explicitement qu'on edite le contenu reel de la ressource active;
- sans transformer `/admin` en editeur de contenu.

## Hors scope

Ce contrat ne couvre pas:
- la gouvernance identity `Lot 5`, documentee separement dans `identity-governance-contract.md`;
- la composition de la page `Identity`, documentee separement dans `identity-surface-contract.md`.
