# Identity Surface Contract

Statut: spec vivante
Portee: page `/identity`, navigation globale `Identity` et articulation avec la lecture diagnostique runtime sur `/hermeneutic-admin`
Lot ferme: `Lot 5`

## But

Ce contrat ferme la surface `Identity` dediee en reemployant les contrats deja stabilises des Lots 2 a 5.

La page doit montrer, en francais clair:
- une introduction compacte qui ne repousse pas la zone de travail;
- les 4 blocs canoniques editables comme premiere vraie zone de pilotage;
- l'etat operateur `Present / Absente`, `Charge / Non charge` et `Injecte / Non injecte` directement dans ces 4 blocs;
- `llm.static` vide comme etat degrade critique visible immediatement;
- `llm.mutable` vide comme etat explicite `Absente`, sans la surqualifier comme la meme anomalie fondamentale;
- la structure reelle du systeme identity;
- la difference entre source canonique, pilotage systeme distinct et formes runtime compilees;
- l'etat courant par sujet comme synthese compacte, sans recopier exhaustivement les cartes canoniques;
- un rappel compact des formes runtime compilees utile au pilotage immediat;
- un acces explicite vers leur detail diagnostique sur `/hermeneutic-admin`;
- l'edition du statique et de la mutable;
- les seuils et limites;
- un bloc `Diagnostics / historique` replie par defaut;
- dans ce bloc replie: legacy / evidence-only, conflits et corrections recentes utiles.

## Routes

- `GET /identity`
- `GET /api/admin/identity/runtime-representations`

La page `/identity` reste une surface HTML servie comme les autres surfaces admin.

La route read-only `runtime-representations` est:
- distincte de `GET /api/admin/identity/read-model`;
- distincte des routes d'edition `POST /api/admin/identity/mutable` et `POST /api/admin/identity/static`;
- distincte de `GET /api/admin/identity/governance`;
- protegee par la meme garde admin que les autres routes `/api/admin/*`;
- reemployee par `/identity` pour son repere compact et par `/hermeneutic-admin` pour le detail diagnostique.

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

La projection structuree compilee pour le jugement expose:
- `technical_name = "identity_input"`
- `role = "hermeneutic_judgment"`
- `present`
- `schema_version`
- `data`

`data` porte la forme exacte retournee par `build_identity_input()`.

Cette representation:
- est une projection runtime compilee a partir de la base canonique;
- ne decrit pas le prompt systeme;
- ne devient pas pour autant une source canonique concurrente;
- sert a lire la base identitaire et sa projection de jugement sans la confondre avec des consignes operatoires.

Sur `/identity`, elle n'apparait plus en dump detaille: seule une synthese compacte reste visible.
Le detail read-only complet vit sur `/hermeneutic-admin`.

### `injected_identity_text`

La forme runtime compilee injectee au modele expose:
- `technical_name = "identity_block"`
- `role = "final_model_system_prompt"`
- `present`
- `content`

`content` porte le texte exact retourne par `build_identity_block()` pour la partie identity injectee dans le prompt systeme augmente.

Cette representation:
- est une forme compilee d'injection runtime;
- occupe un slot technique `final_model_system_prompt` sans devenir pour autant le pilotage systeme source;
- ne doit pas etre lue comme la source canonique de l'identite;
- ne doit pas faire oublier que la source canonique reste `llm.static` / `user.static` plus les mutables canoniques.

Sur `/identity`, elle n'apparait plus comme long texte detaille dans le flux principal.
Le detail complet reste disponible sur `/hermeneutic-admin`.

## Pilotage systeme distinct

La page `/identity` ne doit pas laisser croire que le pilotage systeme vit dans les couches identity.

Le pilotage systeme reste distinct:
- il vit dans `main_system` et `main_hermeneutical`;
- il porte methode, priorites, securite, outils, format et contraintes operatoires;
- il n'est pas editable depuis les blocs statique / mutable;
- il n'est pas remplace par la projection structuree ni par la forme runtime compilee injectee.

### Semantique

- ce ne sont pas deux verites concurrentes;
- c'est la meme base identity projetee en deux formes;
- ni l'une ni l'autre ne doivent etre lues comme "le prompt qui definit la personnalite";
- la fiche structuree sert au jugement hermeneutique;
- la forme runtime compilee sert a la reponse finale;
- `used_identity_ids` peut rester vide si le legacy n'est pas reactif sur le chemin actif.

## Ordre de lecture attendu sur la page

La page `/identity` doit presenter, dans cet ordre ou equivalent:
- une introduction compacte;
- `Pilotage canonique actif` avec `LLM statique`, `LLM mutable`, `User statique`, `User mutable`;
- dans ces 4 blocs, un etat visible sans clic pour `Present / Absente`, `Charge / Non charge` et `Injecte / Non injecte`;
- la structure reelle du systeme identity;
- l'etat courant par sujet comme synthese compacte;
- un repere runtime compile utile au pilotage, avec lien explicite vers le detail diagnostique;
- les seuils et limites;
- `Diagnostics / historique`, replie par defaut;
- dans ce bloc replie, le legacy / evidence-only, les conflits et les corrections recentes utiles.

La page `/hermeneutic-admin` porte, elle, le detail complet:
- de la projection structuree compilee pour le jugement;
- de la forme runtime compilee injectee au modele.

## Langage operateur

Les titres principaux de la page doivent rester en francais clair.

Acceptables:
- `Pilotage canonique actif`
- `LLM statique`
- `LLM mutable`
- `User statique`
- `User mutable`
- `Etat degrade`
- `Absente`
- `Charge`
- `Non charge`
- `Injecte`
- `Non injecte`
- `Etat courant par sujet`
- `Projection structuree compilee pour le jugement`
- `Forme runtime compilee injectee au modele`
- `Seuils et limites`
- `Legacy, evidences et conflits`

Interdits comme titres principaux seuls:
- `read-model`
- `payload`
- `runtime`
- `governance`
- `identity_input`
- `Prompt`

## CSS et composition frontend

La page `/identity` doit:
- reutiliser `admin.css` comme socle partage;
- garder les ajouts CSS bornees dans `admin.css` plutot que recreer une feuille parallele;
- ne pas introduire une nouvelle CSS parallele;
- rester dans le langage visuel deja partage par `/admin`, `/log` et `/hermeneutic-admin`.

La page peut reemployer les modules frontend Lots 2 a 5 si la responsabilite reste explicite et bornee.

## Hors scope

Ce contrat ne couvre pas:
- une refonte visuelle des surfaces admin;
- une nouvelle doctrine identity;
- la resurrection du legacy comme source active;
- une navigation globale plus large que l'ajout borne du lien `Identity`.
