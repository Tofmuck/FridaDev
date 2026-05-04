# Admin Runtime Settings Schema V1

## Objet

Ce document fige le schema runtime settings V1 effectivement expose par le code courant.

Il complete `app/docs/states/specs/admin-implementation-spec.md` et reste aligne sur `app/admin/runtime_settings_spec.py`, qui porte la liste executable des sections et champs.

## Principes

- La table primaire est `runtime_settings`.
- La granularite retenue est `une ligne par section JSONB`.
- Les sections V1 actuellement implementees sont: `main_model`, `arbiter_model`, `summary_model`, `stimmung_agent_model`, `validation_agent_model`, `embedding`, `database`, `services`, `resources`, `identity_governance`.
- Les sections exposees par `PATCH /api/admin/settings/<section>` sont: `main_model`, `arbiter_model`, `summary_model`, `stimmung_agent_model`, `validation_agent_model`, `embedding`, `database`, `services`, `resources`.
- `identity_governance` est une section runtime mais n'est pas exposee par `/api/admin/settings/<section>`; sa surface produit reste `/api/admin/identity/governance` et `/hermeneutic-admin`.
- `runtime_settings_history` est present des la V1.
- Les secrets sont stockes chiffres via `pgcrypto`.
- Les secrets ne ressortent jamais en clair cote lecture admin ; ils exposent seulement `is_secret=true` et `is_set=true|false`.
- `FRIDA_MEMORY_DB_DSN` reste le bootstrap DB externe minimal tant que la transition n'est pas achevee ; il n'est donc ni seede ni consomme depuis `runtime_settings` dans les premieres tranches.

## Secrets runtime V1

- Les secrets runtime V1 sont stockes chiffres en base via `pgcrypto`, jamais en clair.
- `FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY` reste externe a la base, au meme titre que le bootstrap DB minimal.
- `FRIDA_RUNTIME_SETTINGS_CRYPTO_KEY` ne transite jamais vers le frontend, les logs applicatifs, ni les reponses d'erreur.
- `FRIDA_MEMORY_DB_DSN` reste le bootstrap DB externe minimal meme si `database.dsn` devient stockable chiffre en base.

## Table `runtime_settings`

Colonnes cibles :

- `section TEXT PRIMARY KEY`
- `schema_version TEXT NOT NULL DEFAULT 'v1'`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_by TEXT NOT NULL`
- `payload JSONB NOT NULL DEFAULT '{}'::jsonb`

Contraintes cibles :

- `section` appartient strictement a : `main_model`, `arbiter_model`, `summary_model`, `stimmung_agent_model`, `validation_agent_model`, `embedding`, `database`, `services`, `resources`, `identity_governance`
- une seule ligne par section

## Table `runtime_settings_history`

Colonnes cibles :

- `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- `section TEXT NOT NULL`
- `schema_version TEXT NOT NULL DEFAULT 'v1'`
- `changed_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `changed_by TEXT NOT NULL`
- `payload_before JSONB NOT NULL`
- `payload_after JSONB NOT NULL`

Usage :

- historiser chaque seed initial
- historiser chaque modification admin
- conserver les secrets sous leur forme chiffree dans les snapshots, jamais en clair

## Forme du `payload`

Le `payload` d'une section est un objet JSONB dont chaque cle de configuration pointe vers un objet de champ.

Champ non secret :

```json
{
  "temperature": {
    "value": 0.4,
    "is_secret": false,
    "origin": "env_seed"
  }
}
```

Champ secret :

```json
{
  "api_key": {
    "value_encrypted": "<pgcrypto>",
    "is_secret": true,
    "is_set": true,
    "origin": "env_seed"
  }
}
```

Regles :

- les champs non secrets utilisent `value`
- les champs secrets utilisent `value_encrypted`
- tous les champs portent `is_secret`
- tous les champs secrets portent `is_set`
- tous les champs portent `origin`

Valeurs d'`origin` retenues :

- `env_seed`
- `admin_ui`
- `manual_sql`

## Sections V1

### `main_model`

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `base_url` | `text` | non | `OPENROUTER_BASE` |
| `model` | `text` | non | `OPENROUTER_MODEL` |
| `api_key` | `text` | oui | `OPENROUTER_API_KEY` |
| `referer` | `text` | non | `OPENROUTER_REFERER` |
| `referer_llm` | `text` | non | `OPENROUTER_REFERER_LLM` |
| `referer_arbiter` | `text` | non | `OPENROUTER_REFERER_ARBITER` |
| `referer_identity_extractor` | `text` | non | `OPENROUTER_REFERER_IDENTITY_EXTRACTOR` |
| `referer_resumer` | `text` | non | `OPENROUTER_REFERER_RESUMER` |
| `referer_stimmung_agent` | `text` | non | `OPENROUTER_REFERER_STIMMUNG_AGENT` |
| `referer_validation_agent` | `text` | non | `OPENROUTER_REFERER_VALIDATION_AGENT` |
| `app_name` | `text` | non | `OPENROUTER_APP_NAME` |
| `title_llm` | `text` | non | `OPENROUTER_TITLE_LLM` |
| `title_arbiter` | `text` | non | `OPENROUTER_TITLE_ARBITER` |
| `title_identity_extractor` | `text` | non | `OPENROUTER_TITLE_IDENTITY_EXTRACTOR` |
| `title_resumer` | `text` | non | `OPENROUTER_TITLE_RESUMER` |
| `title_stimmung_agent` | `text` | non | `OPENROUTER_TITLE_STIMMUNG_AGENT` |
| `title_validation_agent` | `text` | non | `OPENROUTER_TITLE_VALIDATION_AGENT` |
| `temperature` | `float` | non | valeur par defaut `/api/chat` = `0.4` |
| `top_p` | `float` | non | valeur par defaut `/api/chat` = `1.0` |
| `response_max_tokens` | `int` | non | valeur par defaut `/api/chat` = `8192` |

Notes:

- Pour la surface chat principale first-party (`/`), `main_model.response_max_tokens` est la source de verite du budget de reponse.
- Le frontend principal n'envoie plus de surcharge silencieuse `max_tokens`.
- L'override `max_tokens` de `/api/chat` reste un contrat d'API de compatibilite pour les clients externes explicites.

### `arbiter_model`

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `model` | `text` | non | `ARBITER_MODEL` |
| `temperature` | `float` | non | hardcode `app/memory/arbiter.py` = `0.0` |
| `top_p` | `float` | non | hardcode `app/memory/arbiter.py` = `1.0` |
| `timeout_s` | `int` | non | `ARBITER_TIMEOUT_S` |

### `summary_model`

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `model` | `text` | non | `SUMMARY_MODEL` |
| `temperature` | `float` | non | hardcode `app/memory/summarizer.py` = `0.3` |
| `top_p` | `float` | non | hardcode `app/memory/summarizer.py` = `1.0` |

### `stimmung_agent_model`

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `primary_model` | `text` | non | defaut runtime `openai/gpt-5.4-mini` |
| `fallback_model` | `text` | non | defaut runtime `openai/gpt-5.4-nano` |
| `timeout_s` | `int` | non | defaut runtime `10` |
| `temperature` | `float` | non | defaut runtime `0.1` |
| `top_p` | `float` | non | defaut runtime `1.0` |
| `max_tokens` | `int` | non | defaut runtime `220` |

Convention explicite:

- cette section pilote le noeud `stimmung_agent` du pipeline hermeneutique;
- elle expose les modeles primaire/fallback et les parametres de generation necessaires au jugement affectif;
- elle ne remplace pas `primary_node`, qui reste une etape runtime du pipeline et non une section de modele editable.

### `validation_agent_model`

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `primary_model` | `text` | non | defaut runtime `openai/gpt-5.4-mini` |
| `fallback_model` | `text` | non | defaut runtime `openai/gpt-5.4-nano` |
| `timeout_s` | `int` | non | defaut runtime `10` |
| `temperature` | `float` | non | defaut runtime `0.0` |
| `top_p` | `float` | non | defaut runtime `1.0` |
| `max_tokens` | `int` | non | defaut runtime `80` |

Convention explicite:

- cette section pilote le `validation_agent` du pipeline hermeneutique;
- `max_tokens` reste borne par le contrat de validation serveur;
- elle ne donne pas au `validation_agent` un pouvoir de persistence direct sur l'identite.

### `embedding`

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `endpoint` | `text` | non | `EMBED_BASE_URL` |
| `model` | `text` | non | valeur courante observee via `GET /info` sur le service actif : `intfloat/multilingual-e5-small` |
| `token` | `text` | oui | `EMBED_TOKEN` |
| `dimensions` | `int` | non | `EMBED_DIM` |
| `top_k` | `int` | non | `MEMORY_TOP_K` |

Constat d'exploitation actuel :

- endpoint actif : `https://embed.frida-system.fr`
- acces protege par `X-Embed-Token`
- `GET /info` retourne actuellement `model_id=intfloat/multilingual-e5-small`
- le service annonce `model_dtype=float32`, `max_input_length=512`, `version=1.9.1`

### `database`

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `backend` | `text` | non | valeur cible `postgresql` |
| `dsn` | `text` | oui | champ cible V1, non seede tant que `FRIDA_MEMORY_DB_DSN` reste bootstrap externe |

Regle de transition :

- `database.dsn` existe dans le schema cible
- `FRIDA_MEMORY_DB_DSN` reste la source effective d'acces DB pendant la transition
- le seed initial n'ecrit pas `database.dsn` tant que la phase dediee au basculement bootstrap n'est pas atteinte

### `services`

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `searxng_url` | `text` | non | `SEARXNG_URL` |
| `searxng_results` | `int` | non | `SEARXNG_RESULTS` |
| `crawl4ai_url` | `text` | non | `CRAWL4AI_URL` |
| `crawl4ai_token` | `text` | oui | `CRAWL4AI_TOKEN` |
| `crawl4ai_top_n` | `int` | non | `CRAWL4AI_TOP_N` |
| `crawl4ai_max_chars` | `int` | non | `CRAWL4AI_MAX_CHARS` |
| `crawl4ai_explicit_url_max_chars` | `int` | non | `CRAWL4AI_EXPLICIT_URL_MAX_CHARS` |

### `resources`

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `llm_identity_path` | `text` | non | `FRIDA_LLM_IDENTITY_PATH` |
| `user_identity_path` | `text` | non | `FRIDA_USER_IDENTITY_PATH` |

Convention explicite:

- la valeur visible cote admin reste un chemin runtime du type `data/identity/...`;
- en deploiement Docker standard, cette convention pointe vers `/app/data/...`;
- sur OVH, `/app/data` est alimente par le bind mount `/opt/platform/fridadev/state/data -> /app/data` declare dans `/opt/platform/fridadev-app/docker-compose.yml`;
- la source-of-truth host-side retenue pour `llm.static` et `user.static` est donc `state/data/identity/...` dans le checkout hote, pas une copie parallele dans `fridadev-app`;
- les validations et lectures host-side reutilisent cette meme convention et resolvent le mirror `state/data/...` quand le chemin relatif `app/data/...` n'existe pas localement.
- un chemin absolu ne reste acceptable que s'il resolve dans ces racines identity canoniques; un fichier arbitraire existant hors perimetre est refuse.
- depuis `Lot 4`, ces champs restent des references de ressource; l'edition du contenu statique actif passe par `POST /api/admin/identity/static` et la section `Vue unifiee identity` de `/hermeneutic-admin`.

### `identity_governance`

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `IDENTITY_MIN_CONFIDENCE` | `float` | non | `config.IDENTITY_MIN_CONFIDENCE` |
| `IDENTITY_DEFER_MIN_CONFIDENCE` | `float` | non | `config.IDENTITY_DEFER_MIN_CONFIDENCE` |
| `IDENTITY_MIN_RECURRENCE_FOR_DURABLE` | `int` | non | `config.IDENTITY_MIN_RECURRENCE_FOR_DURABLE` |
| `IDENTITY_RECURRENCE_WINDOW_DAYS` | `int` | non | `config.IDENTITY_RECURRENCE_WINDOW_DAYS` |
| `IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS` | `int` | non | `config.IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS` |
| `IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS` | `int` | non | `config.IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS` |
| `CONTEXT_HINTS_MAX_ITEMS` | `int` | non | `config.CONTEXT_HINTS_MAX_ITEMS` |
| `CONTEXT_HINTS_MAX_TOKENS` | `int` | non | `config.CONTEXT_HINTS_MAX_TOKENS` |
| `CONTEXT_HINTS_MAX_AGE_DAYS` | `int` | non | `config.CONTEXT_HINTS_MAX_AGE_DAYS` |
| `CONTEXT_HINTS_MIN_CONFIDENCE` | `float` | non | `config.CONTEXT_HINTS_MIN_CONFIDENCE` |

Convention explicite:

- cette section runtime porte seulement le sous-ensemble identity gouvernable en live;
- elle ne remplace ni le read-model identity, ni les editeurs static/mutable;
- la surface operateur de lecture/edition reste `/hermeneutic-admin`;
- `/admin` generique peut exposer cette section comme metadonnee runtime, mais ce n'est pas la surface produit de gouvernance identity.

## API de lecture cible

Forme de lecture admin attendue :

- champ non secret : `value`, `is_secret`, `origin`
- champ secret : `is_secret`, `is_set`, `origin`

Exemple :

```json
{
  "api_key": {
    "is_secret": true,
    "is_set": true,
    "origin": "admin_ui"
  }
}
```

## Hors de ce document

- le detail d'implementation SQL, porte par `app/admin/sql/runtime_settings_v1.sql`
- la facade runtime et ses caches, portes par `app/admin/runtime_settings.py`
- les routes HTTP, portees par `app/admin/admin_settings_routes.py` et les routes identity dediees
- la bascule effective de `FRIDA_MEMORY_DB_DSN`
