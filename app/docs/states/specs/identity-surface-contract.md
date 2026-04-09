# Identity Surface Contract

Statut: spec vivante  
Portee: page `/identity`, navigation globale `Identity` et lecture read-only des deux representations runtime  
Lot ferme: `Lot 6`

## But

Ce contrat ferme la surface `Identity` dediee en reemployant les contrats deja stabilises des Lots 2 a 5.

La page doit montrer, en francais clair:
- la structure reelle du systeme identity;
- l'etat courant par sujet;
- la difference entre la fiche structuree pour le jugement et le texte identity injecte au modele;
- l'edition du statique et de la mutable;
- les seuils et limites;
- le legacy / evidence-only;
- les corrections recentes utiles.

## Routes

- `GET /identity`
- `GET /api/admin/identity/runtime-representations`

La page `/identity` reste une surface HTML servie comme les autres surfaces admin.

La route read-only `runtime-representations` est:
- distincte de `GET /api/admin/identity/read-model`;
- distincte des routes d'edition `POST /api/admin/identity/mutable` et `POST /api/admin/identity/static`;
- distincte de `GET /api/admin/identity/governance`;
- protegee par la meme garde admin que les autres routes `/api/admin/*`.

## Navigation globale

Le lien `Identity` doit exister depuis:
- `/`
- `/admin`
- `/log`
- `/hermeneutic-admin`

La page `/identity` doit renvoyer clairement vers:
- `/`
- `/admin`
- `/log`
- `/hermeneutic-admin`

## Reemploi des lots precedents

La surface `Identity` reemploie les contrats deja fermes:
- `GET /api/admin/identity/read-model`
- `POST /api/admin/identity/mutable`
- `POST /api/admin/identity/static`
- `GET /api/admin/identity/governance`
- `POST /api/admin/identity/governance`
- `GET /api/admin/hermeneutics/corrections-export`

Le legacy `identity-candidates` reste visible seulement comme couche legacy/evidence-only et ne redevient pas une verite d'injection active.

## Contrat JSON runtime representations

Top-level:

```json
{
  "ok": true,
  "representations_version": "v1",
  "read_via": "/api/admin/identity/runtime-representations",
  "active_prompt_contract": "static + mutable narrative",
  "active_identity_source": "identity_mutables",
  "identity_input_schema_version": "v2",
  "same_identity_basis": true,
  "structured_identity": {},
  "injected_identity_text": {},
  "used_identity_ids": [],
  "used_identity_ids_count": 0
}
```

### `structured_identity`

La fiche structuree pour le jugement expose:
- `technical_name = "identity_input"`
- `role = "hermeneutic_judgment"`
- `present`
- `schema_version`
- `data`

`data` porte la forme exacte retournee par `build_identity_input()`.

Cette representation:
- est une forme canonique structuree de l'identite;
- ne decrit pas le prompt systeme;
- sert a lire la base identitaire et sa projection de jugement sans la confondre avec des consignes operatoires.

### `injected_identity_text`

Le texte identity injecte au modele expose:
- `technical_name = "identity_block"`
- `role = "final_model_system_prompt"`
- `present`
- `content`

`content` porte le texte exact retourne par `build_identity_block()` pour la partie identity du prompt systeme augmente.

Cette representation:
- est une forme compilee d'injection runtime;
- ne doit pas etre lue comme la source canonique de l'identite;
- ne doit pas faire oublier que la source canonique reste `llm.static` / `user.static` plus les mutables canoniques.

### Semantique

- ce ne sont pas deux verites concurrentes;
- c'est la meme base identity projetee en deux formes;
- ni l'une ni l'autre ne doivent etre lues comme "le prompt qui definit la personnalite";
- la fiche structuree sert au jugement hermeneutique;
- le texte identity sert a la reponse finale;
- `used_identity_ids` peut rester vide si le legacy n'est pas reactif sur le chemin actif.

## Ordre de lecture attendu sur la page

La page `/identity` doit presenter, dans cet ordre ou equivalent:
- la structure reelle du systeme identity;
- l'etat courant par sujet;
- la fiche structuree pour le jugement;
- le texte identity injecte au modele;
- l'edition du statique canonique;
- l'edition de la mutable canonique;
- les seuils et limites;
- le legacy / evidence-only;
- les corrections recentes utiles.

## Langage operateur

Les titres principaux de la page doivent rester en francais clair.

Acceptables:
- `Etat courant par sujet`
- `Fiche identite pour le jugement`
- `Texte identity injecte au modele`
- `Editer le statique canonique`
- `Editer la mutable canonique`
- `Seuils et limites`
- `Legacy, evidences et conflits`

Interdits comme titres principaux seuls:
- `read-model`
- `payload`
- `runtime`
- `governance`
- `identity_input`

## CSS et composition frontend

La page `/identity` doit:
- reutiliser `admin.css` tel quel;
- ne pas modifier `admin.css`;
- ne pas introduire une nouvelle CSS parallele;
- rester dans le langage visuel deja partage par `/admin`, `/log` et `/hermeneutic-admin`.

La page peut reemployer les modules frontend Lots 2 a 5 si la responsabilite reste explicite et bornee.

## Hors scope

Ce contrat ne couvre pas:
- une refonte visuelle des surfaces admin;
- une nouvelle doctrine identity;
- la resurrection du legacy comme source active;
- une navigation globale plus large que l'ajout borne du lien `Identity`.
