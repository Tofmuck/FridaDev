# Migration FridaDev `tofnas` -> `frida-system.fr` TODO

Statut: ouvert
Classement: `app/docs/todo-todo/migration/`
Date: `2026-04-07`

## Contexte

- Depart en vacances lundi prochain.
- Besoin vise: une instance OVH utilisable sur `frida-system.fr`.
- Ce document ne migre rien: il cadre seulement le travail a faire.

## Source / destination

- Source locale: `tofnas`
- Destination OVH: `frida-system.fr`
- Repo source: `/home/tof/docker-stacks/fridadev`
- Plateforme cible existante: `/opt/platform`

## Objectif

Obtenir plus tard une copie fonctionnelle de FridaDev sur OVH, avec:
- l'application FridaDev
- sa base Postgres/pgvector
- son `state/`
- et les dependances web necessaires

## Non-objectifs

- pas de migration faite dans ce pas
- pas de secrets en Git
- pas de remplacement definitif de `tofnas`
- pas de suppression de l'instance locale
- pas de rebuild/restart Docker dans ce pas

## Etat constate sur `tofnas`

- Repo FridaDev local present et propre:
  - chemin: `/home/tof/docker-stacks/fridadev`
  - HEAD: `1d9b156f8b5337a4e08d1735876320c87750c5d2`
  - remote Git: `origin https://github.com/Tofmuck/FridaDev.git`
- Stack FridaDev:
  - conteneur: `FridaDev`
  - image: `fridadev-app:local`
  - port: `8093 -> 8089`
  - mounts: `state/conv`, `state/logs`, `state/data`
  - variables attendues cote app: `FRIDA_MEMORY_DB_DSN`, `OPENROUTER_API_KEY`, `SEARXNG_URL`, `CRAWL4AI_URL`, `CRAWL4AI_TOKEN`, `FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY`, `FRIDA_ADMIN_TOKEN`
- Stack DB locale:
  - conteneur: `postgres`
  - image: `pgvector/pgvector:pg17`
  - port: `5432 -> 5432`
  - volume bind: `/home/tof/docker-stacks/database/data`
  - inventaire DB visible: `frida`, `fridadev`, `postgres`
  - conteneur utilitaire present: `adminer` sur `8181 -> 8080`
- Stack browsing locale:
  - `browsing-searxng`: `ghcr.io/searxng/searxng:2026.3.3-b5c1c2804`, port `8092 -> 8080`
  - `browsing-crawl4ai`: `unclecode/crawl4ai:0.8.0`, port `11235 -> 11235`
  - `browsing-valkey`: `valkey/valkey:8-alpine`, pas de port public
  - token Crawl4AI local present par chemin: `/home/tof/docker-stacks/browsing/secrets/crawl4ai_api_token`
- Tailles approximatives:
  - `/home/tof/docker-stacks/fridadev/state`: `464K`
  - `/home/tof/docker-stacks/database/data`: `4.0K`
  - `/home/tof/docker-stacks/browsing`: `116K`

## Etat constate sur `frida-system.fr`

- Acces SSH batch valide depuis `tofnas`.
- `/opt/platform` est une plateforme Docker active, pas un repo Git.
- Plateforme existante:
  - `platform-caddy` publie `80/443`
  - `platform-searxng` present, non publie directement
  - `platform-crawl4ai` present, non publie directement
  - `platform-valkey-browsing` present
  - `platform-doc-pipeline-db` present en `postgres:16-alpine`
- Pas de conteneur FridaDev detecte.
- Pas de conteneur pgvector/Frida detecte.
- Caddy route deja:
  - `frida-system.fr` et `www.frida-system.fr`
  - hote search via `{$SEARCH_HOST}` vers `searxng:8080`
  - hote crawl via `{$CRAWL_HOST}` vers `crawl4ai:11235`
- Secrets/chemins OVH deja en place pour la plateforme:
  - `/opt/platform/secrets/crawl4ai_api_token`
  - `/opt/platform/secrets/openclaw_env`
  - `/opt/platform/secrets/doc_pipeline_env`
  - autres secrets plateforme Caddy/authelia/redis/nextcloud/n8n
- Taille approx visible:
  - `/opt/platform`: `4.5G`

## Ecarts a resoudre

- FridaDev existe sur `tofnas`, pas sur `frida-system.fr`.
- La base Frida locale utilise `pgvector/pgvector:pg17`; OVH n'a aujourd'hui qu'un Postgres `doc-pipeline` en `postgres:16-alpine`.
- `tofnas` publie SearXNG et Crawl4AI en ports host; OVH les expose via Caddy et reseaux Docker internes.
- `tofnas` a trois stacks separees (`fridadev`, `database`, `browsing`); OVH a une plateforme centralisee sous `/opt/platform`.
- Les reseaux Docker ne sont pas alignes:
  - `tofnas`: `fridadev_default`, `database_default`, `browsing_browsing_net`
  - OVH: `platform_platform_net`, `platform_browsing_net`, `platform_crawl_net`, `platform_auth_net`, `platform_proxy_net`
- Les secrets necessaires a FridaDev ne sont pas encore provisionnes sur OVH.

## Reutilisable cote OVH

- SearXNG deja present, meme image que sur `tofnas`
- Crawl4AI deja present, meme image que sur `tofnas`
- Valkey browsing deja present
- Caddy deja present pour routage HTTP/TLS
- Plateforme Docker deja stable et vivante

## Donnees et artefacts a migrer plus tard

- Base Postgres/pgvector Frida:
  - determiner quelle DB est autoritaire via `FRIDA_MEMORY_DB_DSN`
  - migrer au minimum la base effective Frida
- `state/` FridaDev:
  - `state/conv`
  - `state/data`
  - `state/logs` a arbitrer: utile pour observabilite/historique, pas forcement critique pour le boot
- Fichiers de configuration hors Git:
  - `app/.env`
  - `.env` DB
  - token Crawl4AI
  - tout secret OVH dedie FridaDev

## Ce qui doit rester hors Git

- tous les `.env`
- toutes les valeurs de secrets/tokens
- dumps DB
- `state/`
- volumes Docker

## Ce qui doit passer par GitHub

- code FridaDev
- docs FridaDev
- tests FridaDev
- definition eventuelle d'une stack de deploiement FridaDev si elle est versionnee dans le repo

## Strategie recommandee

- Garder deux deploiements paralleles:
  - `tofnas` = source locale de reference
  - `frida-system.fr` = cible OVH independante
- Ne pas injecter FridaDev a la va-vite dans le `docker-compose.yml` principal OVH.
- Privilegier une sous-stack FridaDev dediee sur OVH, raccordee proprement aux reseaux/utilitaires existants si necessaire.
- Ne pas reutiliser `platform-doc-pipeline-db` comme base Frida par defaut.
- Prevoir un conteneur Postgres/pgvector dedie a Frida si le besoin pgvector est confirme.
- Reutiliser si possible les services OVH deja presents pour:
  - SearXNG
  - Crawl4AI
  - Valkey browsing

## Plan par lots

- [x] Audit SSH / acces
- [x] Audit Docker source
- [x] Audit Docker destination
- [ ] Audit DB et strategie dump/restore
- [ ] Audit `state/`
- [ ] Choix d'integration Compose OVH
- [ ] Integration FridaDev dans `/opt/platform` ou sous-stack dediee
- [ ] Integration Postgres pgvector
- [ ] Secrets / `.env` / tokens
- [ ] Branchement SearXNG OVH
- [ ] Branchement Crawl4AI OVH
- [ ] Caddy / domaine / TLS
- [ ] Build FridaDev
- [ ] Migration DB
- [ ] Migration `state/`
- [ ] Smoke tests
- [ ] Rollback plan
- [ ] Documentation finale

## Risques

- collision ports / reseaux
- divergence future Crawl4AI / SearXNG entre `tofnas` et OVH
- secrets incomplets ou mal provisionnes
- integration Caddy / Authelia a arbitrer
- donnees runtime non versionnees
- double instance `tofnas` / `frida-system.fr` a garder coherente

## Decision recommandee

- Ne pas migrer avant validation de ce TODO.
- Prochain pas recommande: `Lot 1` de migration, pas implementation sauvage.
