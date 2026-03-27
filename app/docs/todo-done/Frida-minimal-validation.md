# Couche minimale de validation - FridaDev

Objet: ajouter un filet de securite simple, executable et peu couteux, pour verifier `FridaDev` sans refaire toute la migration a la main.

## Script

Script principal:

- `app/minimal_validation.py`

Commande conseillee sur l'instance, en executant le script dans le conteneur `FridaDev`:

```bash
docker exec FridaDev sh -lc 'cd /app && PYTHONPATH=/app python minimal_validation.py --base-url http://127.0.0.1:8089 --json'
```

Version sans checks HTTP live:

```bash
docker exec FridaDev sh -lc 'cd /app && PYTHONPATH=/app python minimal_validation.py --skip-live --json'
```

Si le script n'est pas encore visible dans le conteneur apres une mise a jour a chaud, le recopier d'abord:

```bash
docker cp /home/tof/docker-stacks/fridadev/app/minimal_validation.py FridaDev:/app/minimal_validation.py
```

## Ce que le script verifie

### 1. Demarrage / import runtime

- import de `server.py`
- presence de `server.app`
- presence d'un `_RUNTIME_FINGERPRINT` coherent
- chemins critiques resolus

### 2. Schema DB / migrations

- presence des extensions `vector` et `pgcrypto`
- presence des tables attendues
- presence des colonnes critiques sur :
  - `conversations`
  - `conversation_messages`
  - `traces`
  - `summaries`
  - `identities`
  - `identity_evidence`
  - `identity_conflicts`
  - `arbiter_decisions`

### 3. Prompts et identites statiques

- presence des fichiers :
  - `llm_identity.txt`
  - `user_identity.txt`
  - `prompts/arbiter.txt`
  - `prompts/identity_extractor.txt`
- contenu non vide
- presence des marqueurs attendus dans `web/app.js`

### 4. Checks UI statiques

- presence des assets :
  - `index.html`
  - `admin.html`
  - `styles.css`
  - `app.js`
  - `admin.js`
  - `frida.svg`
- presence des references attendues entre ces fichiers

### 5. Smoke tests API

- `GET /`
- `GET /admin`
- `GET /api/conversations?limit=1`
- `GET /api/admin/logs?limit=1`
- route conversation absente -> `404`

### 6. Garde non-regression JSON legacy

Le script cree un faux fichier `state/conv/<uuid>.json`, puis verifie que :

- `GET /api/conversations/<uuid>/messages` renvoie `404`
- `POST /api/chat` avec ce `conversation_id` renvoie `404`

Le fichier de test est ensuite supprime.

## Positionnement

Cette couche minimale ne remplace pas le scenario `DB-only` complet.

Elle complete :

- `docs/todo-done/Frida-db-only-validation-report.md`

Regle simple :

- `minimal_validation.py` = filet de securite frequent
- `Frida-db-only-validation-report.md` = scenario profond de reference
