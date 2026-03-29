# Frida - Guide d'installation et d'exploitation initiale

Date de reference: 2026-03-29

## 1. Objet

Ce guide documente le demarrage initial de `FridaDev` depuis un clone neuf, en mode operatoire.

Il couvre:
- les prerequis techniques;
- les dependances externes reelles;
- la configuration minimale;
- la sequence de demarrage;
- les verifications post-demarrage;
- les blocages frequents sur un environnement vierge.

Il ne couvre pas:
- la conception produit/admin complete;
- la future UX d'installation adminisee;
- les chantiers de parametrage avance hors bootstrap.

Public cible:
- exploitant technique;
- developpeur qui reprend le repo sans contexte implicite.

## 2. Prerequis

Prerequis machine:
- Docker Engine + plugin `docker compose`;
- shell POSIX (`bash`);
- `curl` pour checks rapides HTTP.

Prerequis infra externe:
- un PostgreSQL joignable;
- un provider LLM joignable;
- selon usage: service embeddings, SearXNG, Crawl4AI.

Acces requis:
- capacite a editer `app/.env` local;
- connectivite reseau sortante depuis le conteneur `FridaDev` vers les services externes.

## 3. Ce qui est versionne vs non versionne

Versionne:
- code (`app/`);
- prompts (`app/prompts/`);
- docs (`app/docs/`);
- scripts (`stack.sh`, `docker-compose.yml`).

Non versionne (cf `.gitignore`):
- `app/.env` et variantes locales;
- `state/` (etat runtime monte dans le conteneur);
- `app/conv/` et `app/data/`;
- logs runtime `app/logs/*.jsonl` et `app/logs/*.log`.

Consequence pour un clone neuf:
- aucun secret n'est present;
- aucun state local n'est present;
- aucune identite locale (`data/identity/*`) n'est presente.

## 4. Dependances de service a prevoir

## 4.1 Obligatoires pour un fonctionnement utile

1. PostgreSQL (bootstrap runtime + persistance)
- source: `FRIDA_MEMORY_DB_DSN`
- utilise par: conversations, memoire, runtime settings, observabilite.
- contrainte technique: extensions `pgcrypto` et `vector` (pgvector) doivent pouvoir etre creees ou deja exister.

2. Provider LLM principal (OpenRouter par defaut)
- source: `OPENROUTER_BASE`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`
- utilise par: `/api/chat`, reformulation web, pipeline principal.

## 4.2 Optionnelles selon usage

1. Service embeddings
- source: `EMBED_BASE_URL`, `EMBED_TOKEN`, `EMBED_DIM`
- impact si indisponible: retrieval memoire degrade (retours vides), pipeline chat maintenu mais moins contextualise.

2. SearXNG
- source: `SEARXNG_URL`, `SEARXNG_RESULTS`
- impact si indisponible: web search inactive/degradee quand `web_search=true`.

3. Crawl4AI
- source: `CRAWL4AI_URL`, `CRAWL4AI_TOKEN`, `CRAWL4AI_TOP_N`, `CRAWL4AI_MAX_CHARS`
- impact si indisponible: enrichissement web degrade.

## 4.3 Point reseau critique en mode Docker

En mode conteneur, `127.0.0.1` vise le conteneur lui-meme.
Les endpoints externes dans `app/.env` doivent etre resolvables depuis le conteneur (nom DNS/service reseau Docker/host adapte).

## 5. Configuration minimale

## 5.1 Initialiser le fichier local

```bash
cd /home/tof/docker-stacks/fridadev
cp app/.env.example app/.env
```

## 5.2 Variables minimales a verifier avant `up`

Indispensable:
- `FRIDA_MEMORY_DB_DSN`: DSN PostgreSQL valide et joignable depuis le conteneur.
- `OPENROUTER_API_KEY`: cle API pour les appels LLM.

Fortement recommande:
- `FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY`: cle de chiffrement des secrets runtime admin.
- `FRIDA_ADMIN_TOKEN`: protection des routes `/api/admin/*`.

Selon usages actives:
- embeddings: `EMBED_BASE_URL`, `EMBED_TOKEN`, `EMBED_DIM`;
- web: `SEARXNG_URL`, `CRAWL4AI_URL`, `CRAWL4AI_TOKEN`.

Option identites statiques (sinon bloc identite vide):
- `FRIDA_LLM_IDENTITY_PATH` (defaut: `data/identity/llm_identity.txt`);
- `FRIDA_USER_IDENTITY_PATH` (defaut: `data/identity/user_identity.txt`).

## 5.3 Bootstrap state local recommande

```bash
cd /home/tof/docker-stacks/fridadev
mkdir -p state/conv state/logs state/data/identity
touch state/data/identity/llm_identity.txt state/data/identity/user_identity.txt
```

## 6. Demarrage

Sequence minimale:

```bash
cd /home/tof/docker-stacks/fridadev
./stack.sh up
./stack.sh ps
./stack.sh health
```

Diagnostic rapide si besoin:

```bash
./stack.sh logs
```

Rappel:
- le service expose `8093` en local hote vers `8089` dans le conteneur;
- `stack.sh health` verifie `GET /` sur `http://127.0.0.1:8093/`.

## 7. Verifications minimales apres demarrage

1. HTTP racine:

```bash
curl -fsS http://127.0.0.1:8093/ >/dev/null && echo "root ok"
```

2. Admin status (avec token si configure):

```bash
curl -fsS http://127.0.0.1:8093/api/admin/settings/status
```

Si `FRIDA_ADMIN_TOKEN` est defini:

```bash
curl -fsS -H "X-Admin-Token: <TOKEN>" \
  http://127.0.0.1:8093/api/admin/settings/status
```

3. Chat minimal:

```bash
curl -sS -X POST http://127.0.0.1:8093/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Ping", "web_search": false}'
```

Attendu:
- `ok=true` si les secrets/services requis sont disponibles;
- erreur explicite sinon (secret manquant, dependance indisponible).

## 8. Points de friction connus (clone neuf)

1. DSN PostgreSQL invalide ou non joignable:
- le conteneur peut demarrer, mais persistance/runtime settings/memoire seront en echec partiel ou total.

2. Extensions SQL non disponibles:
- `pgcrypto` et `vector` doivent etre installables ou preinstallees sur la DB cible.

3. Endpoints par defaut non resolvables depuis le conteneur:
- valeurs `127.0.0.1` dans `app/.env` souvent incorrectes en mode Docker multi-services.

4. `OPENROUTER_API_KEY` absent:
- `/api/chat` renvoie une erreur runtime (pas de generation LLM).

5. `FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY` absent:
- le runtime peut demarrer;
- mais le chiffrement/dechiffrement des secrets runtime admin est limite (backfill secrets saute).

6. Fichiers identite absents:
- pas bloquant pour le demarrage;
- mais validation section `resources` et experience identitaire degradees.

## 9. Frontieres

Ce guide:
- documente l'etat reel du repo au 2026-03-29;
- ne remplace pas la future page produit/admin d'installation;
- ne promet pas une installation one-click.

Le chantier produit reste ouvert dans:
- `app/docs/todo-todo/product/Frida-installation-config.md`.
