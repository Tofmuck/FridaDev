# Memory Admin Surface Contract

## Objet

Ce document fige le contrat fonctionnel minimal de la surface produit `Memory Admin`, livree comme point d entree dedie a l observabilite memoire / RAG de FridaDev.

Le but n est pas de refaire `/admin`, `/log` ou `/hermeneutic-admin`, mais de rendre lisible depuis un seul endroit le domaine memoire / retrieval / arbitre / injection.

## Entrees canoniques

- Surface HTML canonique: `/memory-admin`
- Route API canonique: `GET /api/admin/memory/dashboard`

La surface est read-only pour ce lot. Elle reemploie ensuite des lectures deja existantes pour l inspection detaillee :

- `GET /api/admin/logs/chat/metadata`
- `GET /api/admin/logs/chat`
- `GET /api/admin/hermeneutics/arbiter-decisions`

## Contrat frontend retenu

- Le HTML reste a la racine de `app/web/`:
  - `app/web/memory-admin.html`
- La logique frontend specifique vit dans un sous-repertoire dedie:
  - `app/web/memory_admin/api.js`
  - `app/web/memory_admin/main.js`
  - `app/web/memory_admin/render_*.js`
- La surface reutilise `app/web/admin.css`
- Ce lot n ouvre pas le rangement general des `admin_section_*`

## Positionnement par rapport aux autres surfaces

`Memory Admin` est une surface dediee, distincte de l administration generale.

Elle ne doit pas etre decrite comme :

- un sous-onglet flou de `/admin`
- une simple extension de `/hermeneutic-admin`
- une copie cosmetique de `/log`

Repartition retenue :

- `/memory-admin` :
  - observabilite memoire / RAG regroupee
  - separation explicite des provenances de donnees
  - vue operateur par familles du domaine memoire
- `/log` :
  - timeline brute
  - filtres generiques
  - export et suppression scopes
- `/hermeneutic-admin` :
  - detail pipeline hermeneutique
  - detail identity
  - sections mixtes hors seul domaine memoire / RAG
- `/identity` :
  - pilotage canonique des couches identitaires
- `/admin` :
  - runtime settings et configuration operateur

## Familles d informations a rendre lisibles

La surface doit rendre lisibles, au minimum :

- etat memoire durable
- retrieval / RAG
- embeddings
- panier pre-arbitre
- arbitre
- injection memoire
- lectures recentes utiles par tour
- decisions arbitre persistees

Pour l inspection read-only par tour, la surface couvre les stages memory / RAG suivants quand ils existent dans les logs :

- `embedding`
- `memory_retrieve`
- `summaries`
- `arbiter`
- `hermeneutic_node_insertion`
- `prompt_prepared`
- `branch_skipped`

## Provenances a distinguer explicitement

La surface affiche explicitement quatre familles de provenance :

- `durable_persistence`
  - tables `traces`, `summaries`, `arbiter_decisions`
- `calculated_aggregate`
  - syntheses derivees de settings runtime, regroupements SQL et contracts documentaires
- `runtime_process_local`
  - compteurs en memoire du process Python courant
- `historical_logs`
  - `observability.chat_log_events`
  - `admin_logs`

Cette distinction est visible dans le cadrage de la page et dans les sections rendues.

## Reemploi backend retenu

Le lot 10E ajoute un seul endpoint dedie :

- `GET /api/admin/memory/dashboard`

Son role est d agreger en lecture seule les signaux utiles au domaine memoire / RAG sans rouvrir le backend metier.

Il peut reemployer :

- `memory_store`
- `arbiter.get_runtime_metrics()`
- `admin_logs.summarize_hermeneutic_mode_observation()`
- `observability.chat_log_events`
- les runtime settings deja exposes cote code

## Non-goals explicites de ce lot

- aucun reranker
- aucune refonte globale de `app/web/`
- aucun deplacement des `admin_section_*`
- aucune refonte de `/identity`
- aucune refonte de `/hermeneutic-admin`
- aucun patch plateforme OVH
- aucun changement du finding separe `record_arbiter_decisions()`
