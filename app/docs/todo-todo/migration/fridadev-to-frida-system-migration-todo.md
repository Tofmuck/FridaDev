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
- sa base Postgres/pgvector migree depuis `tofnas` sans perte de donnees
- son `state/`
- et les dependances web necessaires

## Non-objectifs

- pas de migration faite dans ce pas
- pas de secrets en Git
- pas de remplacement definitif de `tofnas`
- pas de suppression de l'instance locale
- pas de bascule applicative finale ni de restart destructif sur `tofnas`, Caddy ou Homepage dans ce pas

## Etat constate sur `tofnas`

- Repo FridaDev local present et propre:
  - chemin: `/home/tof/docker-stacks/fridadev`
  - HEAD observe pour ce lot: `a52d115e7ad346a8bddbb883a7e2c7ec3310eafb`
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
  - `/home/tof/docker-stacks/database/data`: `106M` via `sudo du`; le `4.0K` sans sudo etait un artefact de permission
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
- Sous-stack DB Frida dediee creee pour test sous:
  - `/opt/platform/fridadev-db`
  - conteneur `platform-fridadev-postgres`
  - image `pgvector/pgvector:pg17`
  - reseau dedie `platform_fridadev_db_net`
  - aucun port Postgres publie sur l'hote
- Working copy Git OVH creee:
  - `/opt/platform/fridadev`
  - HEAD clone pour ce lot `a52d115e7ad346a8bddbb883a7e2c7ec3310eafb`
  - remote `origin https://github.com/Tofmuck/FridaDev.git`
- Sous-stack applicative interne creee:
  - `/opt/platform/fridadev-app`
  - conteneur `platform-fridadev`
  - image `platform-fridadev-app:local`
  - reseaux `platform_fridadev_db_net`, `platform_browsing_net`, `platform_crawl_net`
  - aucun port host public publie
- Caddy route deja:
  - `frida-system.fr` et `www.frida-system.fr`
  - hote search via `{$SEARCH_HOST}` vers `searxng:8080`
  - hote crawl via `{$CRAWL_HOST}` vers `crawl4ai:11235`
- Secrets/chemins OVH deja en place pour la plateforme:
  - `/opt/platform/secrets/crawl4ai_api_token`
  - `/opt/platform/secrets/doc_pipeline_env`
  - autres secrets plateforme Caddy/authelia/redis/nextcloud/n8n
- Taille approx visible:
  - `/opt/platform`: `4.5G`

## Ecarts a resoudre

- FridaDev existe sur `tofnas` et tourne maintenant en interne sur `frida-system.fr`, mais sans exposition publique, sans Homepage et sans bascule.
- La base Frida locale utilise `pgvector/pgvector:pg17`; OVH dispose maintenant d'une cible test dediee `platform-fridadev-postgres`, et l'app OVH interne l'utilise deja, mais le dump final et la bascule restent ouverts.
- `tofnas` publie SearXNG et Crawl4AI en ports host; OVH les expose via Caddy et reseaux Docker internes.
- `tofnas` a trois stacks separees (`fridadev`, `database`, `browsing`); OVH a une plateforme centralisee sous `/opt/platform`.
- Les reseaux Docker ne sont pas alignes:
  - `tofnas`: `fridadev_default`, `database_default`, `browsing_browsing_net`
  - OVH: `platform_platform_net`, `platform_browsing_net`, `platform_crawl_net`, `platform_auth_net`, `platform_proxy_net`
- Les secrets applicatifs sont maintenant provisionnes hors Git sur OVH pour un test interne, mais l'exposition publique et les arbitrages admin restent ouverts.

## Exigence critique: migration DB sans perte

- La base Frida source sur `tofnas` reste autoritaire tant que la migration n'est pas validee.
- La cible OVH ne doit pas recevoir une base vide comme etat final.
- La DB effective a migrer doit etre identifiee via `FRIDA_MEMORY_DB_DSN` avant tout dump/restore.
- La migration DB doit etre traitee comme un lot bloquant, avec:
  - dump source controle
  - sauvegarde de rollback gardee avant toute bascule
  - restauration cible controlee
  - verification des extensions attendues, notamment `pgvector`
  - verification schema / tables / comptages ou checks equivalents avant et apres restauration
  - verification finale avant ouverture du service OVH
- Il faut prevoir un gel des ecritures ou une fenetre de bascule pour eviter les doubles ecritures `tofnas` / `frida-system.fr`.
- Aucune bascule ne doit etre consideree valide tant que les checks de coherence DB ne sont pas termines.

### Lot 1 DB - constat pre-migration

- DB effective confirmee via `FRIDA_MEMORY_DB_DSN`:
  - scheme: `postgresql`
  - host: `192.168.0.36`
  - port: `5432`
  - database: `fridadev`
  - username: `tof`
  - password: `<redacted>`
- Conteneur source confirme:
  - `postgres`
- Image source confirmee:
  - `pgvector/pgvector:pg17`
- Volume source confirme:
  - `/home/tof/docker-stacks/database/data -> /var/lib/postgresql/data`
- Taille reelle du volume source:
  - `106M` via `sudo du`
- Extensions observees dans `fridadev`:
  - `pgcrypto`
  - `plpgsql`
  - `vector`
- Schemas observes dans `fridadev`:
  - `public`
  - `observability`
- Tables runtime recentes observees dans `fridadev`:
  - `public.runtime_settings`
  - `public.runtime_settings_history`
  - `public.identity_mutables`
  - `observability.chat_log_events`
- Comptages de reference non sensibles dans `fridadev`:
  - `public.conversations = 56`
  - `public.conversation_messages = 262`
  - `public.traces = 208`
  - `public.summaries = 0`
  - `public.runtime_settings = 10`
  - `public.runtime_settings_history = 25`
  - `public.identities = 88`
  - `public.identity_mutables = 1`
  - `observability.chat_log_events = 53772`
- Comparaison `frida` vs `fridadev`:
  - le DSN runtime pointe vers `fridadev`
  - `fridadev` contient les tables runtime recentes et le schema `observability`
  - `frida` ne contient pas `observability.chat_log_events`
  - `frida` ne contient pas `public.runtime_settings`
  - `frida` ne contient pas `public.runtime_settings_history`
  - `frida` ne contient pas `public.identity_mutables`
  - `frida` ne doit donc pas etre migree par reflexe
- Etat cible OVH confirme:
  - avant le lot 2, aucun conteneur Postgres/pgvector dedie a Frida n'etait present
  - `platform-doc-pipeline-db` existe en `postgres:16-alpine`
  - `platform-doc-pipeline-db` ne doit pas etre reutilise par defaut pour Frida
  - avant le lot 2, aucune restauration ne devait etre tentee sur OVH tant que la cible pgvector dediee n'etait pas definie

### Plan technique DB sans perte

- Ce lot 1 reste non destructif:
  - aucun dump
  - aucune restauration
  - aucune creation de DB cible
- Preparer un dump source controle de `fridadev`, pas de `frida`.
- Nommer le dump avec horodatage explicite, par exemple `fridadev-YYYYMMDD-HHMMSS.dump`.
- Stocker le dump hors Git.
- Verifier le dump avant transfert.
- Transferer le dump vers OVH hors Git.
- Creer un Postgres/pgvector cible dedie a Frida sur OVH dans un lot ulterieur.
- Restaurer uniquement par restore controle dans la DB cible dediee.
- Verifier apres restore:
  - extensions attendues
  - schemas attendus
  - tables attendues
  - comptages ou checks equivalents vs source
- Faire un smoke test FridaDev sur OVH avant toute bascule.
- Ne basculer qu'apres validation complete des checks DB et applicatifs.
- Garder le dump de rollback et la DB source `tofnas` comme reference tant que la bascule n'est pas validee.
- Definir une fenetre de gel des ecritures avant le dump final servant a la bascule.

### Lot 2 DB - sous-stack cible + dump/restore test

- Sous-stack cible creee sur OVH:
  - chemin: `/opt/platform/fridadev-db`
  - compose: `/opt/platform/fridadev-db/docker-compose.yml`
  - env_file: `/opt/platform/fridadev-db/.env`
  - data dir: `/opt/platform/fridadev-db/data`
  - imports dir: `/opt/platform/fridadev-db/imports`
- Conteneur cible cree:
  - `platform-fridadev-postgres`
  - image `pgvector/pgvector:pg17`
  - statut observe: `healthy`
  - aucun port public publie
- Reseau cible cree:
  - `platform_fridadev_db_net`
- Mot de passe cible genere cote OVH et garde hors Git:
  - present dans `.env`
  - non affiche
- Dump source de test cree hors Git sur `tofnas`:
  - dossier `/home/tof/docker-stacks/fridadev-migration-dumps`
  - format custom `pg_dump -Fc --no-owner --no-acl`
  - verification de structure realisee via `pg_restore --list` depuis le conteneur source `postgres` car l'hote local n'a pas `pg_restore`
- Dump de test transfere hors Git vers OVH:
  - dossier `/opt/platform/fridadev-db/imports`
- Restore test effectue dans la cible dediee OVH:
  - aucune restauration dans `platform-doc-pipeline-db`
  - aucune reutilisation de la DB doc-pipeline
  - methode retenue: montage `./imports:/imports:ro` puis `pg_restore --clean --if-exists --no-owner --no-acl`
- Verification cible apres restore:
  - extensions `pgcrypto`, `plpgsql`, `vector`
  - schemas `public`, `observability`
  - tables runtime recentes presentes
  - comptages observes coherents avec l'inventaire source capture avant dump
- Aucun changement applicatif dans ce lot:
  - aucune bascule
  - aucun FridaDev OVH demarre
  - aucun runtime ne pointe vers la DB OVH
  - `tofnas` reste la source autoritaire

### Lot applicatif OVH - stack interne sans bascule

- Working copy Git OVH creee:
  - chemin: `/opt/platform/fridadev`
  - HEAD clone pour ce lot: `a52d115e7ad346a8bddbb883a7e2c7ec3310eafb`
  - remote: `origin https://github.com/Tofmuck/FridaDev.git`
  - worktree propre au moment du clone
- Sous-stack app OVH creee:
  - chemin: `/opt/platform/fridadev-app`
  - compose: `/opt/platform/fridadev-app/docker-compose.yml`
  - env_file: `/opt/platform/fridadev-app/.env`
  - conteneur: `platform-fridadev`
  - image: `platform-fridadev-app:local`
  - statut observe apres correction du healthcheck: `healthy`
  - aucun port host public publie
- Reseaux attaches:
  - `platform_fridadev_db_net`
  - `platform_browsing_net`
  - `platform_crawl_net`
  - `platform_platform_net` non attache dans ce lot initial; il a ete ajoute ensuite au lot d'acces OVH pour permettre le routage Caddy propre du clone
- `.env` OVH cree hors Git:
  - `FRIDA_MEMORY_DB_DSN` pointe vers `platform-fridadev-postgres:5432/fridadev`
  - `FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY` est preserve depuis `tofnas`
  - `OPENROUTER_API_KEY` est present
  - `FRIDA_ADMIN_TOKEN` reste vide, conforme a la source actuelle sur `tofnas`
  - `SEARXNG_URL=http://searxng:8080`
  - `CRAWL4AI_URL=http://crawl4ai:11235`
  - `EMBED_BASE_URL=https://embed.frida-system.fr`
  - `EMBED_DIM=384`
  - tokens Crawl4AI et embedding presents, non exposes
- Snapshot `state/` de test copie hors Git:
  - source: `/home/tof/docker-stacks/fridadev/state/`
  - cible: `/opt/platform/fridadev-app/state/`
  - usage: snapshot de test uniquement, pas migration finale du `state/`
- Smoke tests internes reussis:
  - `http://127.0.0.1:8089/` -> `200`
  - DB depuis l'app: `current_database() = fridadev`, `current_user = tof`
  - comptages verifies: `public.conversations = 56`, `observability.chat_log_events = 53772`
  - `SEARXNG_URL` -> `200`
  - `CRAWL4AI_URL/health` -> `200`
  - embedding via `https://embed.frida-system.fr/embed` -> `200`, dimension `384`
- Ce lot reste borne:
  - aucune route Caddy ajoutee
  - aucune card Homepage ajoutee
  - aucune bascule appliquee
  - aucun dump final
  - aucun gel des ecritures
  - `tofnas` reste la source autoritaire

### Lot acces OVH - Caddy / Authelia / Homepage du clone

- Hostname FridaDev retenu pour ce lot:
  - `fridadev.137-74-204-229.sslip.io`
- Hostname DB/admin retenu pour ce lot:
  - `fridadev-db.137-74-204-229.sslip.io`
- Statut DNS:
  - les hostnames preferes `fridadev.frida-system.fr` et `fridadev-db.frida-system.fr` ne resolvent pas encore
  - les hostnames `sslip.io` ci-dessus resolvent vers `137.74.204.229`
  - ce lot valide donc un acces temporaire `sslip.io`, pas encore le DNS final
- Reseaux et upstreams:
  - `platform-fridadev` rejoint maintenant `platform_platform_net`
  - `platform-caddy` atteint `platform-fridadev:8089`
  - l'interface DB admin retenue est `Adminer`
  - conteneur cree: `platform-frida-adminer`
  - `platform-caddy` atteint `platform-frida-adminer:8080`
- Protection web obligatoire:
  - tout le hostname FridaDev passe derriere `import authn`
  - aucune exception de chemin `/admin` ou `/api`
  - tout le hostname DB/admin passe derriere `import authn`
  - `FRIDA_ADMIN_TOKEN` ne remplace pas cette protection: l'exposition OVH est bien protegee par Caddy + Authelia au niveau du hostname entier
- Routage Caddy ajoute:
  - `{$FRIDADEV_HOST}` -> `platform-fridadev:8089`
  - `{$FRIDADEV_DB_HOST}` -> `platform-frida-adminer:8080`
- Homepage mis a jour:
  - card `FridaDev` ajoutee dans le groupe `AI`
  - card `FridaDev DB Admin` ajoutee dans le groupe `Administration`
  - champs Docker renseignes:
    - `server: local-docker`
    - `container: platform-fridadev`
    - `container: platform-frida-adminer`
- Smoke tests d'acces reussis:
  - Caddy -> FridaDev interne: `ok`
  - Caddy -> Adminer interne: `ok`
  - acces public sans session sur `fridadev.137-74-204-229.sslip.io` -> `302` vers Authelia
  - acces public sans session sur `fridadev-db.137-74-204-229.sslip.io` -> `302` vers Authelia
  - aucun `200` direct non protege observe sur ces hostnames
- Ce lot reste borne:
  - `tofnas` reste vivant et n'a pas ete desactive
  - aucune suppression de la DB source
  - aucun dump final dans ce lot
  - aucun gel des ecritures dans ce lot
  - aucune synchronisation continue automatique entre `tofnas` et OVH
  - la DB cible OVH est encore alignee sur les comptages sources observes pendant ce lot, donc aucun snapshot DB supplementaire n'a ete juge necessaire ici

### Lot DNS final OVH - hostnames `frida-system.fr`

- Objectif de ce lot:
  - remplacer les hostnames temporaires `sslip.io` par `fridadev.frida-system.fr` et `fridadev-db.frida-system.fr`
- Reprise apres creation manuelle OVH:
  - les records DNS ont ete crees manuellement par l'utilisateur dans l'interface OVH
- Resolution DNS observee apres reprise:
  - `fridadev.frida-system.fr` -> `137.74.204.229`
  - `fridadev-db.frida-system.fr` -> `137.74.204.229`
  - `auth.frida-system.fr` -> `137.74.204.229`
  - `frida-system.fr` -> `137.74.204.229`
  - resolution revalidee depuis `tofnas`, depuis OVH, et via `@1.1.1.1` / `@8.8.8.8`
  - aucun `AAAA` n'a ete retenu pour ce lot
- Delegation DNS observee:
  - `frida-system.fr` est delegue a `dns14.ovh.net`
  - `frida-system.fr` est delegue a `ns14.ovh.net`
- Caddy mis a jour vers les hostnames finaux avec fallback temporaire:
  - `FRIDADEV_CADDY_HOSTS=fridadev.frida-system.fr, fridadev.137-74-204-229.sslip.io`
  - `FRIDADEV_DB_CADDY_HOSTS=fridadev-db.frida-system.fr, fridadev-db.137-74-204-229.sslip.io`
  - les blocs Caddy gardent `import authn` sur tout le hostname FridaDev et sur tout le hostname DB/admin
- Homepage mis a jour:
  - `FridaDev` pointe maintenant vers `https://fridadev.frida-system.fr`
  - `FridaDev DB Admin` pointe maintenant vers `https://fridadev-db.frida-system.fr`
- Smoke tests publics reussis:
  - `https://fridadev.frida-system.fr/` -> `302` vers `https://auth.frida-system.fr/...`
  - `https://fridadev.frida-system.fr/admin` -> `302` vers `https://auth.frida-system.fr/...`
  - `https://fridadev.frida-system.fr/api/admin` -> `302` vers `https://auth.frida-system.fr/...`
  - `https://fridadev-db.frida-system.fr/` -> `302` vers `https://auth.frida-system.fr/...`
  - aucun `200` direct non protege observe sur les hostnames finaux
- Fallback temporaire conserve:
  - `fridadev.137-74-204-229.sslip.io` reste actif
  - `fridadev-db.137-74-204-229.sslip.io` reste actif
  - ces deux hostnames `sslip.io` continuent eux aussi a renvoyer `302` vers Authelia
- Ce lot reste borne:
  - aucune modification de `tofnas`
  - aucun dump final / restore final
  - aucune suppression de `tofnas`
  - aucune synchronisation continue automatique entre `tofnas` et OVH

## Exigence critique: alias frontend / Caddy

- Un hostname / alias dedie doit etre choisi pour acceder au frontend FridaDev sur OVH.
- Sans alias/routage, l'instance OVH peut tourner mais rester inutilisable depuis l'exterieur.
- Le lot d'acces frontend doit couvrir:
  - choix explicite du hostname final
  - verification DNS / domaine
  - integration dans la plateforme Caddy existante sous `/opt/platform`
  - verification TLS
  - decision explicite sur l'eventuelle protection Auth / Authelia
  - routage du hostname final vers le service FridaDev OVH
  - smoke test HTTP du frontend via le nom de domaine retenu

## Exigence critique: embedding FridaDev

- FridaDev utilise actuellement le modele d'embedding `intfloat/multilingual-e5-small` en `384` dimensions.
- L'endpoint actuel cote FridaDev est `EMBED_BASE_URL=https://embed.frida-system.fr`.
- Le token d'acces embedding est present mais reste secret et ne doit jamais etre affiche dans la doc, les logs ou les scripts de migration.
- Le service OVH existe deja dans le conteneur `platform-embeddings`.
- Image actuelle:
  - `ghcr.io/huggingface/text-embeddings-inference:cpu-latest`
- Cache/modele cote OVH:
  - `/opt/platform/data/embeddings/models--intfloat--multilingual-e5-small`
- Routage existant:
  - Caddy route `embed.frida-system.fr` vers `embeddings:8080`
- Reseau Docker cible:
  - conteneur sur `platform_platform_net`
  - alias Docker `embeddings`
  - alias Docker `platform-embeddings`
- Le lot d'integration OVH devra choisir explicitement entre:
  - option simple/stable: garder `EMBED_BASE_URL=https://embed.frida-system.fr`
  - option interne Docker: utiliser `http://embeddings:8080` ou `http://platform-embeddings:8080`
- Si l'option interne est retenue, le conteneur FridaDev OVH devra rejoindre `platform_platform_net`.
- Ce choix doit rester ouvert dans ce TODO: il ne doit pas etre tranche avant le lot d'integration OVH.
- Avant bascule, il faudra verifier:
  - que le modele reste `intfloat/multilingual-e5-small`
  - que `EMBED_DIM=384`
  - que le token est present mais non expose
  - et qu'un smoke test embedding reussit depuis le futur conteneur FridaDev OVH

## Exigence critique: Homepage dashboard

- Le dashboard Homepage OVH est configure dans `/opt/platform/homepage/services.yaml`.
- FridaDev doit avoir une card/entree Homepage apres migration.
- L'interface DB Frida doit aussi avoir une card/entree Homepage si une interface DB admin est effectivement retenue sur OVH.
- Les cards Homepage doivent utiliser les champs Docker adaptes:
  - `server: local-docker`
  - `container: <nom-du-conteneur-ovh>`
- Les noms de conteneurs exacts doivent etre figes au lot Compose OVH.
- Exemples de noms a decider, sans les imposer:
  - `platform-fridadev`
  - `platform-frida-adminer`
  - `platform-frida-postgres`
- La card FridaDev devra pointer vers le hostname frontend final retenu pour OVH.
- La card interface DB ne devra pointer vers un hostname ou chemin final que si cette interface est volontairement exposee.
- L'interface DB devra etre protegee ou limitee selon la decision prise sur Auth / Authelia / acces admin.
- Un smoke test Homepage devra verifier que les cards apparaissent et pointent vers les bonnes URLs finales.

## Reutilisable cote OVH

- SearXNG deja present, meme image que sur `tofnas`
- Crawl4AI deja present, meme image que sur `tofnas`
- Valkey browsing deja present
- Embedding deja present via `platform-embeddings`
- Homepage deja present via `/opt/platform/homepage/services.yaml`
- Caddy deja present pour routage HTTP/TLS
- Plateforme Docker deja stable et vivante

## Donnees et artefacts a migrer plus tard

- Base Postgres/pgvector Frida:
  - determiner quelle DB est autoritaire via `FRIDA_MEMORY_DB_DSN`
  - migrer au minimum la base effective Frida sans perte de donnees
  - ne pas remplacer la cible finale par une base vide
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
- [x] Identifier la base source autoritaire via `FRIDA_MEMORY_DB_DSN`
- [x] Creer une sous-stack DB Frida dediee sous `/opt/platform/fridadev-db`
- [ ] Definir dump source + sauvegarde de rollback avant toute bascule
- [ ] Definir restauration cible controlee sans perte et sans base vide finale
- [x] Verifier extensions, notamment `pgvector`, schema, tables et comptages avant/apres restauration
- [ ] Definir gel des ecritures ou fenetre de bascule pour eviter les doubles ecritures
- [x] Audit `state/`
- [x] Choix d'integration Compose OVH
- [x] Integration FridaDev dans `/opt/platform` ou sous-stack dediee
- [x] Integration Postgres pgvector dedie a Frida si confirme par le DSN reel
- [x] Secrets / `.env` / tokens
- [x] Branchement SearXNG OVH
- [x] Branchement Crawl4AI OVH
- [x] Retenir pour ce lot l'acces embedding OVH via `https://embed.frida-system.fr`
- [ ] Verifier que FridaDev OVH rejoint `platform_platform_net` si l'option embedding interne est retenue
- [x] Verifier que le modele embedding reste `intfloat/multilingual-e5-small`
- [x] Verifier que `EMBED_DIM=384`
- [x] Verifier que le token embedding est present mais non expose
- [x] Choisir l'interface DB admin OVH, par exemple Adminer ou autre, ou decider de ne pas en exposer
- [x] Ajouter la card Homepage FridaDev dans `/opt/platform/homepage/services.yaml`
- [x] Ajouter la card Homepage DB/admin si l'interface DB est retenue
- [x] Renseigner `server: local-docker` et les bons `container:` pour les cards Homepage
- [x] Verifier que les cards Homepage pointent vers les hostnames finaux
- [x] Choisir le hostname / alias frontend FridaDev OVH
- [x] Verifier DNS / domaine / Caddy / TLS / eventuelle Auth ou Authelia pour l'alias retenu
- [x] Router le hostname final vers le service FridaDev OVH
- [x] Build FridaDev
- [x] Dump/restore test de `fridadev` dans la cible OVH dediee sans bascule applicative
- [ ] Migration DB sans perte avec verification avant bascule
- [ ] Migration `state/` finale
- [x] Smoke test embedding depuis le futur conteneur FridaDev OVH
- [x] Smoke tests internes FridaDev OVH sans exposition publique
- [x] Smoke test Homepage apres restart de la plateforme
- [x] Smoke tests backend et frontend via le hostname final
- [ ] Rollback plan
- [ ] Documentation finale

## Risques

- collision ports / reseaux
- divergence future Crawl4AI / SearXNG entre `tofnas` et OVH
- secrets incomplets ou mal provisionnes
- integration Caddy / Authelia a arbitrer
- donnees runtime non versionnees
- double instance `tofnas` / `frida-system.fr` a garder coherente
- perte de donnees si dump / restauration / verification sont incomplets
- double-ecriture `tofnas` / OVH pendant la bascule
- migration de la mauvaise DB si `frida` vs `fridadev` n'est pas tranche par le DSN reel
- instance OVH fonctionnelle mais inaccessible faute d'alias ou de routage
- collision avec les hotes Caddy deja en place
- TLS / Auth / Authelia mal alignes sur le hostname final
- embedding casse si FridaDev OVH n'a pas acces au bon endpoint
- confusion entre route publique Caddy et route interne Docker pour l'embedding
- bypass involontaire de la protection Caddy/token si l'endpoint interne est retenu
- mismatch modele/dimensions avec les vecteurs existants
- instance OVH fonctionnelle mais absente du dashboard Homepage
- entree Homepage pointant vers un mauvais conteneur
- exposition d'une interface DB sans protection suffisante
- divergence entre hostname Caddy et `href` Homepage
- `FRIDA_ADMIN_TOKEN` source reste vide: ne pas supposer une protection admin deja prete avant exposition OVH
- fallback `sslip.io` encore conserve temporairement: il faudra decider plus tard quand le retirer apres validation humaine des hostnames finaux
- aucune synchronisation continue automatique entre `tofnas` et OVH: un futur dump de fraicheur restera un snapshot ponctuel, pas une replication

### Mode operatoire vacances - travailler depuis OVH

- Si OVH devient l'environnement de travail temporaire pendant les vacances, commencer chaque session dans `/opt/platform/fridadev` par:
  - `git pull --ff-only origin main`
  - `git status --short`
- Coder, committer et pousser depuis `/opt/platform/fridadev` tant que cette working copy reste l'environnement actif temporaire.
- Apres une modification de code runtime, rebuild uniquement la sous-stack app OVH:
  - `cd /opt/platform/fridadev-app && docker compose up -d --build`
- Verifier ensuite au minimum:
  - le conteneur `platform-fridadev`
  - l'acces protege par Authelia
  - les smoke tests applicatifs utiles pour le lot modifie
- Ne pas croire que `tofnas` et OVH se synchronisent automatiquement.
- Au retour a la maison, repuller d'abord sur `tofnas`, puis decider explicitement s'il faut resynchroniser la DB et/ou `state/`.

## Decision recommandee

- Ne pas migrer avant validation de ce TODO.
- Prochain pas recommande: valider en usage humain le clone OVH sur `fridadev.frida-system.fr` et `fridadev-db.frida-system.fr`, puis ouvrir plus tard un lot de retrait du fallback `sslip.io` si ce secours ne sert plus, sans couper `tofnas`.
- Ne pas lancer encore la bascule finale: le dump final de synchronisation, le gel des ecritures, la migration DB finale et la migration `state/` finale restent ouverts.
