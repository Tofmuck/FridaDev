# Frida State — 28/03/2026

## Objet du document
Ce document fixe un etat lisible du repository `FridaDev` au **28 mars 2026**.
Il sert de reference de comparaison pour les audits suivants.

Methode:
- constats tires du code et de la structure reelle du repo;
- inférences signalees explicitement;
- recommandations operationnelles courtes et priorisees.

## 1. Resume executif
Au 28/03/2026, `FridaDev` est une base applicative exploitable avec:
- stack Docker locale stable (`docker-compose.yml` + `stack.sh`);
- backend Flask unique (`app/server.py`) qui orchestre chat, admin settings, hermeneutique et observabilite;
- persistance conversationnelle et memoire en PostgreSQL (DB-first en flux nominal);
- prompts backend centralises et separes (`main_system.txt` / `main_hermeneutical.txt`);
- observabilite de tour chat dediee (package `app/observability/`, routes logs metadata/delete/export Markdown, UI `/log`).

Changements structurels marquants depuis le state du 23/03/2026:
- decomposition du flux chat en modules `core/chat_session_flow.py`, `core/chat_memory_flow.py`, `core/chat_llm_flow.py`, orchestration dans `core/chat_service.py`;
- decomposition partielle runtime settings (`runtime_settings_spec.py`, `runtime_settings_repo.py`, `runtime_settings_validation.py`, `runtime_secrets.py`) avec facade stable `runtime_settings.py`;
- split frontend admin en modules (`admin_api.js`, `admin_state.js`, `admin_section_*.js`, `admin_ui_common.js`) meme si `admin.js` reste volumineux;
- stabilisation des follow-ups logs (metadata selectors, suppression scopee, export Markdown, tests associes);
- grounding temporel chat aligne prompt/runtime (`NOW`, `TIMEZONE`, labels relatifs/silence et garde-fous temporels).

Points critiques encore ouverts:
- monolithes residuels (`server.py`, `conv_store.py`, `runtime_settings.py`, `admin.js`, `log.js`);
- politique de suppression conversationnelle encore plus destructive en code que la cible documentaire long terme;
- securite admin toujours conditionnee au runtime (`FRIDA_ADMIN_TOKEN` / `FRIDA_ADMIN_LAN_ONLY`) et non enforcee par defaut strict.

## 2. Perimetre reel du depot
### 2.1 Ce que le depot versionne
- code applicatif backend/frontend (`app/`);
- prompts statiques (`app/prompts/`);
- scripts d'exploitation (`stack.sh`, `docker-compose.yml`, `app/run.sh`);
- tests (`app/tests/`);
- documentation structuree (`app/docs/`).

### 2.2 Ce que le depot ne versionne pas
(d'apres `.gitignore`)
- `app/.env` et variantes locales;
- runtime state local `state/`;
- artefacts runtime `app/conv/`, `app/data/`, logs runtime fichier;
- environnements/caches Python et artefacts systeme.

### 2.3 Consequence pratique sur clone neuf
Un clone neuf ne suffit pas seul pour executer la stack:
- il faut fournir un `.env` valide;
- il faut un backend PostgreSQL accessible selon la config runtime;
- il faut initialiser le state local monte par Docker (`state/`), notamment pour les identites fichiers runtime.

## 3. Stack et execution
### 3.1 Orchestration Docker
`docker-compose.yml` decrit:
- projet `fridadev`;
- service `fridadev`, conteneur `FridaDev`;
- image `fridadev-app:local` build depuis `app/Dockerfile`;
- port `8093 -> 8089`;
- volumes `./state/conv:/app/conv`, `./state/logs:/app/logs`, `./state/data:/app/data`;
- healthcheck HTTP local sur `/`.

### 3.2 Script operateur
`stack.sh` fournit `up`, `down`, `restart`, `logs`, `ps`, `config`, `health`.
`restart` reconstruit l'image et relance le service (`docker compose up -d --build`).

### 3.3 Entree runtime
- entree container canonique: `python server.py` (`app/Dockerfile`);
- `app/run.sh` reste un wrapper local (chargement `.env` + venv), non entree Docker officielle.

## 4. Architecture reelle actuelle
### 4.1 Backend HTTP
`app/server.py` (1009 lignes) reste l'entree unique.
Il contient:
- garde admin (`before_request`) base sur token et CIDR;
- routes chat publiques (`/api/chat`, `/api/conversations*`);
- routes admin settings (`/api/admin/settings*`);
- routes admin hermeneutiques (`/api/admin/hermeneutics/*`);
- routes observabilite logs (`/api/admin/logs/chat*`, metadata, delete scope, export Markdown);
- routes statiques (`/`, `/admin`, `/log`).

### 4.2 Core applicatif
`app/core/` distingue maintenant:
- orchestration chat: `chat_service.py`;
- session/conversation chat: `chat_session_flow.py`;
- pipeline memoire/arbitrage/identite: `chat_memory_flow.py`;
- appel LLM et stream: `chat_llm_flow.py`;
- construction prompt conversationnel + labels temporels: `conv_store.py`;
- brique prompt augmente et reference temporelle: `chat_prompt_context.py`.

### 4.3 Memoire / identite / admin
- `app/memory/`: retrieval, resumes, arbitrage, ecriture identitaire, audit arbitre, persistence SQL;
- `app/identity/identity.py`: bloc identitaire hybride (statique + dynamique);
- `app/admin/`: settings runtime, services admin, logs admin, actions runtime.

### 4.4 Observabilite applicative
- package dedie `app/observability/` (extrait du namespace conflictuel historique `app/logs/`);
- stockage SQL des evenements de tour (`log_store.py`);
- emission d'evenements de pipeline (`chat_turn_logger.py`);
- export Markdown scope conversation/tour (`log_markdown_export.py`).

### 4.5 Prompts
Prompts statiques centralises:
- `main_system.txt`
- `main_hermeneutical.txt`
- `summary_system.txt`
- `arbiter.txt`
- `identity_extractor.txt`
- `web_reformulation.txt`

### 4.6 Web
- chat: `web/index.html` + `web/app.js`;
- admin settings: `web/admin.html` + `admin.js` et modules `admin_section_*.js`;
- logs: `web/log.html` + `web/log/log.js`;
- style principal admin partage via `web/admin.css`.

### 4.7 Tests
- 46 fichiers `test_*.py` sous `app/tests/`;
- structuration hybride legacy `phase*` + migration progressive vers `tests/unit/*` et `tests/integration/*`;
- couverture explicite des lots logs/time-grounding (server, prompt loader, chat prompt context, frontend logs).

### 4.8 Documentation
- `app/docs/states/`: references normatives/projet;
- `app/docs/todo-todo/`: chantiers actifs;
- `app/docs/todo-done/`: traces de chantiers clos.

## 5. Etat des grands chantiers integres (verifies dans le code)
- DB-first conversation state confirme en flux normal (`conversations`, `conversation_messages`, summaries/traces SQL);
- prompts backend centralises et separes (`prompt_loader`, paths config dedies);
- observabilite logs stabilisee:
  - lecture paginee,
  - metadata selectors conversation/tour,
  - suppression scopee conversation/tour,
  - export Markdown backend dedie,
  - UI logs dediee;
- chat-time-grounding stabilise sur le perimetre implemente:
  - source unique du NOW de tour,
  - brique `[RÉFÉRENCE TEMPORELLE]` avec `NOW` et `TIMEZONE`,
  - labels relatifs et marqueurs de silence injectes,
  - garde-fous temporels explicites dans le prompt hermeneutique;
- runtime settings deja desacouples partiellement en sous-modules dedies, avec facade retro-compatible.

## 6. Dette structurelle restante
Constats:
- `app/core/conv_store.py` (1312 lignes) concentre encore persistence conversation, fenetre tokens, labels temporels, resumes, memories, suppression forte;
- `app/server.py` (1009 lignes) reste un point de couplage transversal important;
- `app/admin/runtime_settings.py` (939 lignes) reste une facade lourde malgre le split interne;
- frontend encore dense: `app/web/admin.js` (1073 lignes), `app/web/log/log.js` (564 lignes).

Effets de bord possibles:
- augmentation du cout de regression pour les changements transverses;
- risque de faux refacto (deplacement de complexite sans reduction reelle) si les prochains lots ne restent pas strictement orientes responsabilites.

## 7. Contradictions et points de vigilance verifies
- securite admin:
  - le garde existe mais depend du runtime (`FRIDA_ADMIN_TOKEN`, `FRIDA_ADMIN_LAN_ONLY`),
  - en configuration permissive, la surface admin reste accessible localement/LAN;
- retention/suppression:
  - la suppression API conversation est logique (soft delete),
  - une suppression forte reste presente et destructive dans `conv_store.delete_conversation`;
- transition DB-only:
  - la logique active est DB-first,
  - des traces/compatibilites filesystem restent presentes (`ensure_conv_dir`, volumes `state/conv`).

## 8. Priorites recommandees (ordre de suite)
1. Reduire le couplage `server.py` en externalisant progressivement les sous-surfaces routes (sans rupture de contrat HTTP).
2. Desepaissir `conv_store.py` par responsabilite (time labels, assembly prompt, persistence conversations, retention) avec tests de non-regression cibles.
3. Durcir la posture de securite admin par defaut (token obligatoire en contexte partage, guardrail explicite de demarrage).
4. Finaliser la migration nomenclature tests (domaines cibles) sans casser les patterns legacy encore appeles.
5. Rapprocher politique documentaire retention/suppression et implementation effective de purge forte.

## 9. Documents de reference associes
- state precedent: `app/docs/states/project/Frida-State-french-23-03-26.md`
- equivalent EN (meme date): `app/docs/states/project/Frida-State-english-28-03-26.md`
- contrat grounding temporel: `app/docs/states/specs/chat-time-grounding-contract.md`
- contrat logs: `app/docs/states/specs/log-module-contract.md`
