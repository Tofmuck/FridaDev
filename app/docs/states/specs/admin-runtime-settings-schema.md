# Admin Runtime Settings Schema V1

## Objet

Ce document fige le schema runtime settings V1 effectivement expose par le code courant.

Il complete `app/docs/states/specs/admin-implementation-spec.md` et reste aligne sur `app/admin/runtime_settings_spec.py`, qui porte la liste executable des sections et champs.

## Principes

- La table primaire est `runtime_settings`.
- La granularite retenue est `une ligne par section JSONB`.
- Les sections V1 actuellement implementees sont: `main_model`, `arbiter_model`, `identity_extractor_model`, `identity_periodic_model`, `memory_arbiter_model`, `summary_model`, `web_reformulation_model`, `stimmung_agent_model`, `validation_agent_model`, `biblio_librarian_agent`, `agenda_agent`, `embedding`, `database`, `services`, `resources`, `identity_governance`.
- Les sections exposees par `PATCH /api/admin/settings/<section>` sont: `main_model`, `arbiter_model`, `identity_extractor_model`, `identity_periodic_model`, `memory_arbiter_model`, `summary_model`, `web_reformulation_model`, `stimmung_agent_model`, `validation_agent_model`, `embedding`, `database`, `services`, `resources`.
- `agenda_agent` est exposee par le read-model agrege `/api/admin/settings` avec
  secrets redacted; aucune valeur d'app-password n'est lue ni affichee par ce
  read-model.
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

- `section` appartient strictement a : `main_model`, `arbiter_model`, `identity_extractor_model`, `identity_periodic_model`, `memory_arbiter_model`, `summary_model`, `web_reformulation_model`, `stimmung_agent_model`, `validation_agent_model`, `biblio_librarian_agent`, `agenda_agent`, `embedding`, `database`, `services`, `resources`, `identity_governance`
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
| `referer_web_reformulation` | `text` | non | `OPENROUTER_REFERER_WEB_REFORMULATION` |
| `referer_arbiter` | `text` | non | `OPENROUTER_REFERER_ARBITER` |
| `referer_identity_extractor` | `text` | non | `OPENROUTER_REFERER_IDENTITY_EXTRACTOR` |
| `referer_identity_periodic` | `text` | non | `OPENROUTER_REFERER_IDENTITY_PERIODIC` |
| `referer_resumer` | `text` | non | `OPENROUTER_REFERER_RESUMER` |
| `referer_stimmung_agent` | `text` | non | `OPENROUTER_REFERER_STIMMUNG_AGENT` |
| `referer_validation_agent` | `text` | non | `OPENROUTER_REFERER_VALIDATION_AGENT` |
| `app_name` | `text` | non | `OPENROUTER_APP_NAME` |
| `title_llm` | `text` | non | `OPENROUTER_TITLE_LLM` |
| `title_web_reformulation` | `text` | non | `OPENROUTER_TITLE_WEB_REFORMULATION` |
| `title_arbiter` | `text` | non | `OPENROUTER_TITLE_ARBITER` |
| `title_identity_extractor` | `text` | non | `OPENROUTER_TITLE_IDENTITY_EXTRACTOR` |
| `title_identity_periodic` | `text` | non | `OPENROUTER_TITLE_IDENTITY_PERIODIC` |
| `title_resumer` | `text` | non | `OPENROUTER_TITLE_RESUMER` |
| `title_stimmung_agent` | `text` | non | `OPENROUTER_TITLE_STIMMUNG_AGENT` |
| `title_validation_agent` | `text` | non | `OPENROUTER_TITLE_VALIDATION_AGENT` |
| `temperature` | `float` | non | valeur par defaut `/api/chat` = `0.4` |
| `top_p` | `float` | non | valeur par defaut `/api/chat` = `1.0` |
| `response_max_tokens` | `int` | non | valeur par defaut `/api/chat` = `8192` |

Notes:

- Decision operateur du 2026-05-20: le modele principal quotidien cible est `openai/gpt-5.1`, en conservant `base_url`, `api_key`, `temperature=0.7`, `top_p=1.0`, `response_max_tokens=8192`, `referer_llm` et `title_llm`.
- Pour la surface chat principale first-party (`/`), `main_model.response_max_tokens` est la source de verite du budget de reponse.
- Le frontend principal n'envoie plus de surcharge silencieuse `max_tokens`.
- L'override `max_tokens` de `/api/chat` reste un contrat d'API de compatibilite pour les clients externes explicites.
- Les champs `referer_*` et `title_*` nomment les callers OpenRouter via `HTTP-Referer`, `X-OpenRouter-Title` et `X-Title` compat. Les payloads runtime ajoutent aussi `metadata.frida_caller`, `metadata.frida_slot` et `trace.generation_name` sans utiliser le champ provider `user`.

### `arbiter_model`

Slot legacy conserve pour compatibilite. Aucun caller modele actif ne lit plus `arbiter_model` comme source effective: l'arbitre memoire utilise `memory_arbiter_model`, l'extracteur identity utilise `identity_extractor_model`, et le juge mutable utilise le slot de compatibilite `identity_periodic_model`.

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `model` | `text` | non | champ legacy stocke/admin; non consomme par un caller actif |
| `temperature` | `float` | non | champ legacy stocke/admin; non consomme par un caller actif |
| `top_p` | `float` | non | champ legacy stocke/admin; non consomme par un caller actif |
| `timeout_s` | `int` | non | champ legacy stocke/admin; non consomme par un caller actif |

### `identity_extractor_model`

Slot individualise de l'extracteur identity au tour (`extract_identities()`). Il partage le transport OpenRouter de `main_model` (`base_url`, `api_key`, `referer_identity_extractor`, `title_identity_extractor`) mais possede son propre modele, son propre echantillonnage, son budget de sortie et son timeout. La decision humaine du 2026-05-18 conserve `openai/gpt-5.4-mini`.

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `model` | `text` | non | `IDENTITY_EXTRACTOR_MODEL`, defaut `openai/gpt-5.4-mini` |
| `temperature` | `float` | non | `IDENTITY_EXTRACTOR_TEMPERATURE`, defaut `0.0` |
| `top_p` | `float` | non | `IDENTITY_EXTRACTOR_TOP_P`, defaut `1.0` |
| `max_tokens` | `int` | non | `IDENTITY_EXTRACTOR_MAX_TOKENS`, defaut `700` |
| `timeout_s` | `int` | non | `IDENTITY_EXTRACTOR_TIMEOUT_S`, defaut `10` |

### `identity_periodic_model`

Slot de compatibilite conserve sous le nom `identity_periodic_model`, mais depuis le Lot B add-only ontologique il pilote le caller actif `mutable_identity_judge_v2`. Il partage le transport OpenRouter de `main_model` (`base_url`, `api_key`, `referer_identity_periodic`, `title_identity_periodic`) mais possede son propre modele, son budget de sortie et son timeout. La decision humaine du 2026-05-26 passe ce slot runtime a `openai/gpt-5.2` apres smoke strict 3/3; `anthropic/claude-haiku-4.5` est une reference historique fragile, pas le modele runtime actif.

Transition refonte mutable 2026-05-26: le prompt actif expose a l'operateur est `prompts/identity_mutable_judge_v2.txt` via le juge `mutable_identity_judge_v2`. `prompts/identity_mutable_judge.txt` et `prompts/identity_periodic_agent.txt` restent des artefacts legacy/compat pre-Lot-B, pas le prompt runtime actif.

Surface admin operateur: la section doit exposer explicitement le module actif `mutable_identity_judge_v2_add_only`, le caller `mutable_identity_judge`, le contrat `mutable_judge_v2`, le prompt kind `mutable_identity_judge_v2`, le champ de modele effectif `identity_periodic_model.model`, et le structured output `json_schema strict=true` avec `provider.require_parameters=true`. Le nom du slot reste une compatibilite, pas une preuve d'agent periodic actif. Le champ read-only `benchmark_decision` pointe vers la validation GPT-5.2 actuelle; l'ancienne decision Haiku du 2026-05-19 peut rester visible uniquement sous `legacy_benchmark_decision` avec source `legacy_pre_gpt52_cutover`.

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `model` | `text` | non | runtime DB `openai/gpt-5.2`; fallback env `IDENTITY_PERIODIC_MODEL` |
| `temperature` | `float` | non | `IDENTITY_PERIODIC_TEMPERATURE`, defaut `0.0` |
| `top_p` | `float` | non | `IDENTITY_PERIODIC_TOP_P`, defaut `1.0` |
| `max_tokens` | `int` | non | `IDENTITY_PERIODIC_MAX_TOKENS`, defaut `1400` |
| `timeout_s` | `int` | non | `IDENTITY_PERIODIC_TIMEOUT_S`, defaut `10` |

### `memory_arbiter_model`

Slot individualise de l'arbitre memoire. Il partage le transport OpenRouter de `main_model` (`base_url`, `api_key`, `referer_arbiter`, `title_arbiter`) mais possede son propre modele, son propre echantillonnage, son budget de sortie et son timeout.

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `model` | `text` | non | `MEMORY_ARBITER_MODEL`, defaut `mistralai/mistral-small-2603` |
| `temperature` | `float` | non | `MEMORY_ARBITER_TEMPERATURE`, defaut `0.0` |
| `top_p` | `float` | non | `MEMORY_ARBITER_TOP_P`, defaut `1.0` |
| `max_tokens` | `int` | non | `MEMORY_ARBITER_MAX_TOKENS`, defaut `600` |
| `timeout_s` | `int` | non | `MEMORY_ARBITER_TIMEOUT_S`, defaut `10` |

### `summary_model`

Slot individualise du resume conversationnel. Il partage le transport OpenRouter de `main_model` (`base_url`, `api_key`, `referer_resumer`, `title_resumer`) mais possede son propre modele, son propre echantillonnage, son budget de sortie et son timeout. La decision benchmark humaine du 2026-05-18 conserve `openai/gpt-5.4-mini`.

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `model` | `text` | non | `SUMMARY_MODEL`, defaut `openai/gpt-5.4-mini` |
| `temperature` | `float` | non | `SUMMARY_TEMPERATURE`, defaut `0.3` |
| `top_p` | `float` | non | `SUMMARY_TOP_P`, defaut `1.0` |
| `max_tokens` | `int` | non | `SUMMARY_TARGET_TOKENS`, defaut `2000` |
| `timeout_s` | `int` | non | `SUMMARY_TIMEOUT_S`, defaut `90` |

### `web_reformulation_model`

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `model` | `text` | non | `WEB_REFORMULATION_MODEL`, defaut `openai/gpt-5.4-mini` |
| `temperature` | `float` | non | `WEB_REFORMULATION_TEMPERATURE`, defaut `0.2` |
| `max_tokens` | `int` | non | `WEB_REFORMULATION_MAX_TOKENS`, defaut `40` |
| `timeout_s` | `int` | non | `WEB_REFORMULATION_TIMEOUT_S`, defaut `10` |

Convention explicite:

- cette section pilote uniquement la micro-tache `web_search.reformulate()`;
- elle ne modifie ni le modele principal du chat, ni le prompt de reformulation web;
- elle partage le transport OpenRouter de `main_model` (`base_url` et `api_key`);
- les referer/title `web_reformulation` sont portes par `main_model.referer_web_reformulation` et `main_model.title_web_reformulation`, semes depuis `OPENROUTER_REFERER_WEB_REFORMULATION` / `OPENROUTER_TITLE_WEB_REFORMULATION`.

### `stimmung_agent_model`

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `primary_model` | `text` | non | defaut runtime `google/gemini-3.1-flash-lite` |
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
| `primary_model` | `text` | non | defaut runtime `google/gemini-3.1-flash-lite` |
| `fallback_model` | `text` | non | defaut runtime `openai/gpt-5.4-nano` |
| `timeout_s` | `int` | non | defaut runtime `15` |
| `temperature` | `float` | non | defaut runtime `0.0` |
| `top_p` | `float` | non | defaut runtime `1.0` |
| `max_tokens` | `int` | non | defaut runtime `140` |

Convention explicite:

- cette section pilote le `validation_agent` du pipeline hermeneutique;
- `timeout_s` est fixe a `15` secondes par defaut pour eviter les faux timeouts Gemini observes sur le chemin `validation_agent`;
- `max_tokens` reste borne par le contrat de validation serveur, releve a `140` apres relance benchmark du 2026-05-19;
- elle ne donne pas au `validation_agent` un pouvoir de persistence direct sur l'identite.

### `biblio_librarian_agent`

Slot agentique Biblio existant, conserve ici comme section runtime dediee et
comme precedent du mode runtime Agenda.

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `mode` | `text` | non | `BIBLIO_LIBRARIAN_AGENT_MODE` |
| `primary_model` | `text` | non | `BIBLIO_LIBRARIAN_AGENT_MODEL` |
| `fallback_model` | `text` | non | `BIBLIO_LIBRARIAN_AGENT_FALLBACK_MODEL` |
| `timeout_s` | `int` | non | `BIBLIO_LIBRARIAN_AGENT_TIMEOUT_S` |
| `temperature` | `float` | non | `BIBLIO_LIBRARIAN_AGENT_TEMPERATURE` |
| `top_p` | `float` | non | `BIBLIO_LIBRARIAN_AGENT_TOP_P` |
| `max_tokens` | `int` | non | `BIBLIO_LIBRARIAN_AGENT_MAX_TOKENS` |
| `max_tool_calls` | `int` | non | `BIBLIO_LIBRARIAN_AGENT_MAX_TOOL_CALLS` |
| `max_model_calls` | `int` | non | `BIBLIO_LIBRARIAN_AGENT_MAX_MODEL_CALLS` |
| `max_recent_turns` | `int` | non | `BIBLIO_LIBRARIAN_AGENT_MAX_RECENT_TURNS` |
| `reasoning_effort` | `text` | non | `BIBLIO_LIBRARIAN_AGENT_REASONING_EFFORT` |

### `agenda_agent`

Socle runtime de l'agent Agenda V1. Lot 2 livre seulement la configuration et
l'exposition admin redacted; il ne lit pas CalDAV, ne lit pas Nextcloud et ne
lit pas la valeur de l'app-password.

| Champ | Type | Secret | Source actuelle |
| --- | --- | --- | --- |
| `mode` | `text` | non | defaut runtime `off`; modes admis `off`, `shadow`, `candidate`, `active` |
| `caldav_account` | `text` | non | defaut runtime `tof` |
| `caldav_app_password` | `text` | oui | source dediee `FRIDA_AGENDA_CALDAV_TOF_APP_PASSWORD`, non seedee depuis l'environnement dans Lot 2 |

Contraintes:

- `mode=off` est le defaut sur et n'exige aucun secret configure;
- `shadow`, `candidate` et `active` exigent seulement une presence de secret
  redacted pour validation admin, sans decryptage ni lecture de valeur;
- `caldav_account` reste `tof` pour l'Agenda V1;
- le read-model admin expose seulement `is_secret`, `is_set`, `origin` et
  `secret_sources.caldav_app_password`; jamais `value`, `value_encrypted` ou
  app-password.

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
