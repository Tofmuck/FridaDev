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
- `state/conv`, `state/logs`, `state/data` (etat runtime cote hote);
- artefacts runtime locaux (`app/conv/`, `app/data/`, `app/logs/*.jsonl`, `app/logs/*.log`) hors suivi git.

Repere important:
- en mode Docker, les chemins operateur a manipuler sont `state/...` cote hote;
- `/app/conv`, `/app/logs`, `/app/data` sont les chemins internes du conteneur (cibles de montage).

Consequence pour un clone neuf:
- aucun secret n'est present;
- aucun state local n'est present;
- aucune identite locale (`state/data/identity/*` cote hote) n'est presente.

## 4. Dependances de service a prevoir

Schema global de base a date (lecture rapide):
- `app/docs/states/baselines/database-schema-baseline.md`

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

2. SearXNG (repere historique du guide initial)
- source: `SEARXNG_URL`, `SEARXNG_RESULTS`
- impact historique si indisponible: la recherche Web manuelle et l'ancien
  chemin auto-borne pouvaient etre degrades. Ce libelle ne decrit pas une
  activation lexicale automatique actuelle; les conditions et providers du
  pipeline Web courant sont documentes dans
  `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`.

3. Crawl4AI
- source: `CRAWL4AI_URL`, `CRAWL4AI_TOKEN`, `CRAWL4AI_TOP_N`, `CRAWL4AI_MAX_CHARS`, `CRAWL4AI_EXPLICIT_URL_MAX_CHARS`
- impact si indisponible: enrichissement web degrade.

4. Dictation vocale Whisper
- source: `WHISPER_API_URL`, `WHISPER_API_TIMEOUT_S` (defaut applicatif
  inchange de `180 s` pour une dictee bornee a cinq minutes)
- contrat de taille et duree: arret navigateur a `300 s`, un blob, un upload et
  une transcription; fichier audio reel limite a `16 Mio` (`16 777 216`
  octets) dans FridaDev, corps HTTP declare limite a `17 Mio` (`17 825 792`
  octets) sur la route et dans Caddy, tolerance aval Whisper limitee a `305 s`.
- contrat de normalisation: une duree d'entree connue est validee avant
  `ffmpeg`; une duree d'entree inconnue autorise uniquement une normalisation
  provisoire bornee a `306 s`. La duree du WAV normalise doit ensuite etre
  connue et inferieure ou egale a `305 s` avant `whisper-cli`. Si la
  normalisation echoue alors que la duree d'entree etait inconnue, aucun
  fallback brut ni appel Whisper n'est autorise.
- si le service Whisper amont active une authentification par cle, `FridaDev` doit recevoir la meme `WHISPER_API_KEY` pour que `/api/chat/transcribe` reste utilisable.
- observabilite: les logs de diagnostic doivent rester content-free (`request_id`, tailles, durees, raison d'arret, latences, `transcript_chars`), sans audio brut ni transcription.

## 4.3 Point reseau critique en mode Docker

En mode conteneur, `127.0.0.1` vise le conteneur lui-meme.
Les endpoints externes dans `app/.env` doivent etre resolvables depuis le conteneur (nom DNS/service reseau Docker/host adapte).

## 5. Configuration minimale

## 5.1 Initialiser le fichier local

```bash
cd /path/to/fridadev
cp app/.env.example app/.env
```

## 5.2 Variables minimales a verifier avant `up`

Indispensable:
- `FRIDA_MEMORY_DB_DSN`: DSN PostgreSQL valide et joignable depuis le conteneur.
- `OPENROUTER_API_KEY`: cle API pour les appels LLM.

Fortement recommande:
- `FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY`: cle de chiffrement des secrets runtime admin.

Selon usages actives:
- embeddings: `EMBED_BASE_URL`, `EMBED_TOKEN`, `EMBED_DIM`;
- web: `SEARXNG_URL`, `CRAWL4AI_URL`, `CRAWL4AI_TOKEN`.
- dictation vocale: `WHISPER_API_URL`; si l'amont Whisper exige une auth Bearer, fournir aussi `WHISPER_API_KEY` au runtime Frida.

Option identites statiques (sinon bloc identite vide):
- `FRIDA_LLM_IDENTITY_PATH` (defaut: `data/identity/llm_identity.txt`);
- `FRIDA_USER_IDENTITY_PATH` (defaut: `data/identity/user_identity.txt`).
- la source canonique attendue reste les fichiers operateur locaux sous `state/data/identity/*`, non versionnes dans Git.
- le repo fournit seulement `state/data/identity/README.md` et les fichiers `*.example.txt` pour bootstrap/provisionnement.
- en exploitation Docker standard sur OVH, ces fichiers sont consommes via le bind mount `/opt/platform/fridadev/state/data -> /app/data` declare dans `/opt/platform/fridadev-app/docker-compose.yml`.
- le contrat visible reste `data/identity/...` car le runtime applicatif lit ces chemins sous `/app`.
- hors conteneur, les chargeurs et validations host-side resolvent le mirror `state/data/identity/...` si `app/data/identity/...` est absent.

## 5.3 Bootstrap state local recommande

```bash
cd /path/to/fridadev
mkdir -p state/conv state/logs state/data/identity
cp -n state/data/identity/llm_identity.example.txt state/data/identity/llm_identity.txt
cp -n state/data/identity/user_identity.example.txt state/data/identity/user_identity.txt
```

## 6. Demarrage

Sequence minimale:

```bash
cd /path/to/fridadev
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

2. Admin status:

```bash
docker exec FridaDev python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8089/api/admin/settings/status', timeout=5).status)"
```

Cette commande est une preuve technique par loopback **depuis le conteneur**.
Un appel depuis l'hote vers le port Docker publie n'est pas ce loopback
conteneur autorise. L'usage humain des surfaces `/api/admin/*` passe par le
proxy Caddy/Authelia authentifie avec `Remote-User`; aucun
`FRIDA_ADMIN_TOKEN` ne doit etre reinstaure.

3. Chat minimal:

```bash
curl -sS -X POST http://127.0.0.1:8093/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Ping", "web_search": false}'
```

Attendu pour le chat:
- `ok=true` si les secrets/services requis sont disponibles;
- erreur explicite sinon (secret manquant, dependance indisponible).

Repere historique du guide initial, desormais supersede: `web_search=false`
n'activait pas l'ancien Web pre-node lexical et le rattrapage anti-suspension
etait alors decrit comme non implemente. Le pipeline courant conserve
`/api/chat`, separe les activations Web effectives et n'autorise pas a rouvrir
l'auto-Web lexical depuis ce passage historique; voir
`app/docs/states/architecture/fridadev-current-runtime-pipeline.md`.

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

Le chantier produit est archive dans:
- `app/docs/todo-done/product/Frida-installation-config.md`.
