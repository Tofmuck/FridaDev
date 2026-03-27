# Migration FridaDev - Etat de reference

Date: 2026-03-23
Scope: photographie de `FridaDev` avant migration vers une base autonome.
Important: les secrets sont volontairement masques dans ce document.

## 1. Runtime observe

- Stack: `/home/tof/docker-stacks/fridadev`
- Service compose: `fridadev`
- Conteneur: `FridaDev`
- Image active: `fridadev-fridadev`
- Publication reseau: `8093 -> 8089`
- Etat runtime: `healthy`
- Verification HTTP locale: `GET http://127.0.0.1:8093/ -> 200`

## 2. Volumes et donnees actuellement montees

Volumes declares dans `docker-compose.yml`:

- `./state/conv:/app/conv`
- `./state/logs:/app/logs`
- `./state/data:/app/data`

Etat constate dans `state/`:

- `state/conv`: 43 fichiers JSON de conversation
- `state/logs`: 3 fichiers de logs admin
- `state/data/identity`: 2 fichiers
- `state/data/prompts`: 2 fichiers
- `state/data/migrations`: 4 rapports de migration

Arborescence observee:

- `state/conv`
- `state/logs`
- `state/data/identity`
- `state/data/prompts`
- `state/data/migrations`

Conclusion baseline:
`FridaDev` ne part pas d'un etat vierge. Les volumes montes contiennent deja des conversations, des logs, des identites et des prompts issus du clone courant.

## 3. Configuration active observee

Chemin runtime:

- `/home/tof/docker-stacks/fridadev/app/.env`

Elements structurants observes:

- LLM local present: `LLAMA_BASE=http://192.168.0.50:49253/v1`
- OpenRouter actif: `https://openrouter.ai/api/v1`
- Modele principal: `openai/gpt-5.1`
- Nom OpenRouter expose: `FridaDev`
- Base memoire actuelle: PostgreSQL sur `192.168.0.36:5432`, base `frida`, utilisateur `tof`
- Embeddings actifs: `https://embed.frida-system.fr`
- Recherche locale active: SearXNG via `http://192.168.0.36:8092`
- Crawl actif: `http://192.168.0.36:11235`
- Meteo active via `open-meteo`
- Ticketmaster active via cle configuree
- Admin token actif
- Admin restreint au LAN via allowlist CIDR

Anomalie a conserver dans le point de depart:

- La ligne `.env` contient actuellement `FRIDA_PORT=8501SEARXNG_URL=http://192.168.0.36:8092` sur une seule ligne. Elle doit etre consideree comme une anomalie existante du baseline, pas comme une modification introduite pendant la migration.

## 4. Base de donnees actuellement utilisee

DSN runtime actuel, masque:

- `postgresql://tof:[masked]@192.168.0.36:5432/frida`

Impact code:

- `core/conv_store.py` ouvre la DB via `config.FRIDA_MEMORY_DB_DSN`
- `memory/memory_store.py` ouvre la meme DB via `config.FRIDA_MEMORY_DB_DSN`

Conclusion baseline:
`FridaDev` ecrit encore dans la base `frida`, donc il n'est pas isole du live sur le plan persistance.

## 5. Routes exposees actuellement

Routes publiques:

- `POST /api/chat`
- `GET /api/weather`
- `GET /api/budget`
- `GET /api/conversations`
- `POST /api/conversations`
- `PATCH /api/conversations/<conversation_id>`
- `DELETE /api/conversations/<conversation_id>`
- `GET /api/conversations/<conversation_id>/messages`
- `GET /`
- `GET /admin`

Routes admin:

- `GET /api/admin/logs`
- `POST /api/admin/restart`
- `POST /api/admin/budget/increase`
- `GET /api/admin/hermeneutics/identity-candidates`
- `GET /api/admin/hermeneutics/arbiter-decisions`
- `POST /api/admin/hermeneutics/identity/force-accept`
- `POST /api/admin/hermeneutics/identity/force-reject`
- `POST /api/admin/hermeneutics/identity/relabel`
- `GET /api/admin/hermeneutics/dashboard`
- `GET /api/admin/hermeneutics/corrections-export`

## 6. Integrations externes constatees

Integrations appelees directement par le code ou la config:

- OpenRouter
- service d'embedding externe
- SearXNG
- Crawl4AI
- Ticketmaster
- Open-Meteo
- endpoint LLM local `LLAMA_BASE`
- PostgreSQL/pgvector local au serveur

Conclusion baseline:
Le produit actuel depend d'un melange d'integrations locales, internes et externes. Elles devront etre requalifiees une par une pendant la migration.

## 7. Couplages legacy encore visibles dans le code

Couplages constates:

- redemarrage admin encore branche sur `frida-mini.service`
- valeurs par defaut `Frida-Mini` dans `config.py` et `config.example.py`
- loggers nommes `kiki.*`
- UI encore marquee `kiki.ia`, `KikiKawai`, `Kiki`
- front avec references `Olive`
- clefs `localStorage` encore prefixees `kiki.*`
- commentaire CSS `Bulle utilisateur (Olive)`
- `run.sh` annonce encore `kiki-mini`

Conclusion baseline:
`FridaDev` est aujourd'hui un clone fonctionnel, mais pas un produit detaché. Les dependances symboliques et techniques au legacy sont encore presentes a plusieurs niveaux.

## 8. Ancrage rollback / comparaison

Points simples de comparaison pour la suite:

- Stack Docker: `/home/tof/docker-stacks/fridadev/docker-compose.yml`
- Config runtime: `/home/tof/docker-stacks/fridadev/app/.env`
- Code serveur: `/home/tof/docker-stacks/fridadev/app/server.py`
- Front: `/home/tof/docker-stacks/fridadev/app/web/*`
- Donnees runtime: `/home/tof/docker-stacks/fridadev/state/*`

Verification rapide de reference:

- `docker compose ps`
- `curl -I http://127.0.0.1:8093/`
- comptage des fichiers dans `state/`
- relecture du DSN actif et des integrations configurees

## 9. Statut du point 1

Le point 1 est considere comme fige:

- le runtime actuel est documente
- les volumes et donnees de depart sont identifies
- la DB actuellement utilisee est identifiee
- les routes exposees sont listees
- les integrations externes sont listees
- les couplages legacy visibles sont inventories

Aucune modification fonctionnelle n'a ete appliquee pendant cette etape, uniquement de la documentation de reference.
