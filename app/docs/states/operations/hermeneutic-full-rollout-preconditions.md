# Preconditions de bascule hermeneutique full au redemarrage

## Objet

Definir les preconditions concretes d'une bascule hermeneutique `full + observability` a partir de l'infrastructure deja en place.

Ce document ne decrit pas une phase `shadow-only` prolongee.
Il fixe la cible normale de redemarrage reel:

- pipeline hermeneutique actif pour de vrai
- observability et inspection admin conservees
- rollback possible si la verification immediate echoue

## Mode runtime cible exact

La cible de bascule full au redemarrage est:

- `HERMENEUTIC_MODE=enforced_all`

Justification code:

- `shadow` garde l'observation sans enforcement complet
- `enforced_identities` n'est qu'un mode partiel
- `enforced_all` est le seul mode qui active a la fois:
  - l'enforcement memoire (`memory_mode_apply.source=arbiter_enforced`)
  - l'enforcement identite (`identity_mode_apply.action=persist_enforced`)

## Sens operationnel de `full + observability`

`full + observability` signifie ici:

- le runtime demarre directement en `enforced_all`
- un vrai tour `/api/chat` produit les effets runtime attendus
- `/log` reste utilisable pour inspecter les stages hermeneutiques par tour
- `/hermeneutic-admin` reste utilisable pour le dashboard, l'inspection par tour, les decisions arbitre et les identites candidates
- les signaux tokens/provider deja fermes restent visibles:
  - `estimated_*` pour l'estimation pre-call
  - `provider_*` pour la verite provider post-call

Ce document n'ajoute ni nouveau monitoring, ni nouvelle UI, ni nouveau KPI externe.

## Checklist pre-restart

Avant de redemarrer en mode full, verifier:

1. Sur `/admin`, les sections `stimmung_agent_model` et `validation_agent_model` sont presentes, lisibles et valides; le transport `main_model` est aussi configure.
2. Sur `/log`, un tour recent montre bien les stages `stimmung_agent`, `hermeneutic_node_insertion`, `primary_node` et `validation_agent`.
3. Sur `/hermeneutic-admin`, le dashboard et l'inspection par tour chargent correctement; la navigation admin reste utilisable.
4. La visibilite tokens/provider deja fermee reste lisible dans les surfaces existantes; aucun chantier token bloquant ne reste ouvert pour cette bascule.
5. Le token admin et la route backend `POST /api/admin/restart` sont disponibles; l'operateur sait que cette route provoque un auto-exit du runtime/conteneur.
6. La valeur cible preparee pour le redemarrage est explicitement `HERMENEUTIC_MODE=enforced_all`.

## Checklist post-restart immediate

Juste apres redemarrage:

1. Verifier via `/hermeneutic-admin` ou `/api/admin/hermeneutics/dashboard` que `mode=enforced_all`.
2. Executer un vrai tour `/api/chat`.
3. Verifier dans `/log` que le tour produit toujours les stages `stimmung_agent`, `hermeneutic_node_insertion`, `primary_node` et `validation_agent`.
4. Verifier que l'inspection reste disponible dans `/hermeneutic-admin` pour ce tour et que le dashboard conserve ses champs reels:
   - `mode`
   - `alerts`
   - `counters`
   - `rates`
   - `latency_ms`
   - `runtime_metrics`
5. Verifier cote backend via `GET /api/admin/logs` que les tours post-restart portent bien les marqueurs d'enforcement reel:
   - `memory_mode_apply` avec `mode=enforced_all` et `source=arbiter_enforced`
   - `identity_mode_apply` avec `mode=enforced_all` et `action=persist_enforced`

## Regle de decision operatoire

La bascule est acceptee seulement si:

- le runtime est effectivement en `enforced_all`
- le pipeline hermeneutique tourne reellement sur un tour post-restart
- les surfaces `/log` et `/hermeneutic-admin` restent exploitables
- les marqueurs d'enforcement memoire et identite sont visibles cote observability existante

Sinon:

- la bascule full n'est pas acceptee comme validee
- un rollback operatoire peut reutiliser `shadow` ou `off`
- la cible normale reste `enforced_all`; `shadow` n'est alors qu'un repli borne

## Place residuelle de `shadow`

Pour le Lot 9, la cible finale normale est:

- un runtime reel en `HERMENEUTIC_MODE=enforced_all`
- avec pipeline hermeneutique actif
- avec `/log`, `/hermeneutic-admin` et l'observability existante maintenus

`shadow` n'est donc plus:

- une destination normale
- un etat final `shadow-only`
- une phase d'observation prolongee pour se rassurer avant de decider

`shadow` reste seulement:

- un etat transitoire tant que les preconditions de ce document ne sont pas remplies
- un mode de repli si la verification immediate post-restart echoue
- un garde-fou borne avant retour vers `enforced_all`

`enforced_identities` reste de meme un mode partiel:

- utile comme mode intermediaire si un besoin ponctuel l'impose
- hors cible finale normale du Lot 9
