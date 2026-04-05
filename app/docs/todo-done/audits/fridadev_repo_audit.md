# FridaDev Repo Audit

Date de reference: 2026-04-03

## 1. Resume executif
- [Constate] `FridaDev` n'est plus dans une simple phase de preparation hermeneutique: le runtime local verifie tourne en `HERMENEUTIC_MODE=enforced_all`, avec `/log`, `/hermeneutic-admin` et `GET /api/admin/hermeneutics/dashboard` actifs.
- [Constate] L'architecture applicative est plus lisible qu'au precedent audit: `app/core/` distingue desormais orchestration chat, session, memoire/arbitrage, contexte prompt et flux LLM; le pipeline hermeneutique complet est branche dans `app/core/chat_service.py`.
- [Constate] L'observabilite a nettement progresse: distinction `estimated_*` / `provider_*`, logs des stages `stimmung_agent`, `hermeneutic_node_insertion`, `primary_node`, `validation_agent`, dashboard hermeneutique et surface HTML dediee.
- [Constate] Les principaux points de couplage restants sont maintenant `app/minimal_validation.py` (1211 lignes), `app/server.py` (1094), `app/admin/runtime_settings.py` (1066), `app/web/admin.js` (1367) et `app/web/log/log.js` (564).
- [Infere] La dette principale n'est plus l'absence du Lot 9 en runtime, mais le poids residuel de quelques facades/orchestrateurs transverses et le cout de regression des changements cross-layer.
- [Recommande] Garder le Lot 9 ferme et concentrer les prochaines tranches sur le desepaississement progressif des surfaces HTTP/runtime/frontend encore lourdes, sans rouvrir la doctrine deja closee.

## 2. Sources et perimetre
- [Constate] Sources primaires utilisees pour cet audit:
  - code du repo
  - documentation de reference existante
  - runtime local sur `http://127.0.0.1:8093`
  - `docker compose ps`
- [Constate] Sources secondaires utilisees:
  - tests existants
  - grep de references croisees
- [Constate] Aucune source web externe n'a ete utilisee.
- [Constate] Les documents `todo-todo/` et `todo-done/` n'ont ete utilises comme sources de verite que pour la classification documentaire et l'etat de cloture des chantiers; le diagnostic de fond repose sur code + runtime.

## 3. Cartographie actuelle du repo
- [Constate] Racine:
  - `docker-compose.yml`, `stack.sh`, `README.md`, `AGENTS.md`
  - `app/` concentre l'application, les tests et la documentation structuree
- [Constate] Backend Python:
  - entree HTTP unique: `app/server.py`
  - couche applicative et flux: `app/core/`
  - memoire/identite: `app/memory/`, `app/identity/`
  - admin/runtime settings/hermeneutique: `app/admin/`
  - observabilite: `app/observability/`
  - validation smoke: `app/minimal_validation.py`
- [Constate] Frontend statique:
  - chat: `app/web/index.html`, `app/web/app.js`
  - admin settings: `app/web/admin.html`, `app/web/admin.js`, `app/web/admin_section_*.js`
  - logs: `app/web/log.html`, `app/web/log/log.js`
  - hermeneutic admin: `app/web/hermeneutic-admin.html`, `app/web/hermeneutic-admin.js`
- [Constate] Tests:
  - `60` fichiers `test_*.py` sous `app/tests/`
  - couverture explicite pour runtime settings, logs, OpenRouter provider metadata, pipeline hermeneutique, surfaces frontend admin/logs/hermeneutic-admin
- [Constate] Documentation:
  - `app/docs/states/`: references stables
  - `app/docs/todo-todo/`: chantiers actifs
  - `app/docs/todo-done/`: traces archivees et audits

## 4. Runtime et surfaces verifies au 2026-04-03
- [Constate] `docker compose ps` montre un conteneur `FridaDev` sain, expose en `0.0.0.0:8093->8089`.
- [Constate] `GET /api/admin/hermeneutics/dashboard` retourne:
  - `mode=enforced_all`
  - `alerts=[]`
  - `parse_error_rate=0.0`
  - `fallback_rate=0.0`
- [Constate] `curl -I http://127.0.0.1:8093/log` retourne `200 OK`.
- [Constate] `curl -I http://127.0.0.1:8093/hermeneutic-admin` retourne `200 OK`.
- [Constate] `GET /api/admin/settings/main-model` expose des champs distincts `referer_*` et `title_*` pour:
  - `llm`
  - `arbiter`
  - `identity_extractor`
  - `resumer`
  - `stimmung_agent`
  - `validation_agent`
- [Constate] `core.llm_client.or_headers(...)` confirme des `HTTP-Referer` et `X-OpenRouter-Title` distincts par composant, en coherence avec les settings runtime.
- [Infere] Le dernier restart live a bien bascule le runtime sur des identites OpenRouter distinctes par composant, et pas seulement sur une configuration documentaire.

## 5. Architecture reelle actuelle
### 5.1 HTTP et orchestration
- [Constate] `app/server.py` reste l'entree Flask unique et contient:
  - garde admin `before_request`
  - routes chat publiques
  - routes admin settings
  - routes logs applicatifs
  - routes admin hermeneutiques
  - surface restart backend-only
  - routes statiques `/`, `/admin`, `/log`, `/hermeneutic-admin`
- [Constate] Le garde admin est runtime-dependent:
  - token via `FRIDA_ADMIN_TOKEN`
  - restriction LAN/CIDR via `FRIDA_ADMIN_LAN_ONLY` et `FRIDA_ADMIN_ALLOWED_CIDRS`

### 5.2 Flux chat et pipeline hermeneutique
- [Constate] `app/core/chat_service.py` orchestre desormais:
  - resolution de session
  - grounding temporel
  - preparation memoire
  - `stimmung_agent`
  - `primary_node`
  - `validation_agent`
  - injection du bloc `[JUGEMENT HERMENEUTIQUE]`
  - appel du LLM principal
- [Constate] `app/core/chat_memory_flow.py` porte la logique de mode:
  - `off`
  - `shadow`
  - `enforced_identities`
  - `enforced_all`
- [Constate] `memory_mode_apply` et `identity_mode_apply` rendent explicites les effets reels du mode runtime, y compris:
  - `source=arbiter_enforced`
  - `action=persist_enforced`
- [Constate] `app/core/chat_prompt_context.py` projette `validated_output` en prose compacte `[JUGEMENT HERMENEUTIQUE]` avant l'appel final au modele principal.

### 5.3 Observabilite et surfaces operateur
- [Constate] `app/observability/hermeneutic_node_logger.py` emet des payloads compacts pour `hermeneutic_node_insertion`, `primary_node` et `validation_agent`, sans dump des payloads internes interdits.
- [Constate] `app/server.py`, `app/core/chat_llm_flow.py` et `app/core/llm_client.py` separent les estimations locales (`estimated_*`) et les metadonnees provider post-call (`provider_*`).
- [Constate] La surface `/log` reste l'observabilite transversale compacte du pipeline par tour.
- [Constate] La surface `/hermeneutic-admin` fournit une lecture plus detaillee du dispositif hermeneutique sans devenir une seconde stack UI parallele.

### 5.4 Prompts et posture de reponse
- [Constate] `app/prompts/main_system.txt` recadre explicitement Frida comme "interlocuteur de travail et de reflexion".
- [Constate] `app/prompts/main_hermeneutical.txt` fixe la hierarchie des briques runtime et donne au bloc `[JUGEMENT HERMENEUTIQUE]` une priorite explicite en aval.
- [Infere] Le repo ne decrit plus seulement une ambition hermeneutique; il opere deja une lecture aval guidee par un verdict valide.

## 6. Findings clos depuis l'audit precedent
- [Constate] Le constat precedent sur `FRIDA_WEB_HOST` est stale:
  - `app/server.py` lance maintenant `app.run(host=config.WEB_HOST, port=config.WEB_PORT)`
  - `config.py` porte explicitement le contrat host/port runtime
- [Constate] Le constat precedent sur un payload chat `history` frontend/backend divergent est stale:
  - aucune occurrence active de `history` n'est observee dans `app/web/app.js` ou `app/server.py`
- [Constate] Le constat precedent sur `app/core/conv_store.py` comme monolithe critique principal est stale:
  - le fichier fait maintenant `591` lignes et n'est plus le principal foyer de dette du repo
- [Constate] Le constat precedent sur un `.gitignore` excluant `app/docs/states/*` n'est plus confirme dans l'etat actuel du repo.
- [Infere] Le fichier d'audit canonique avait besoin d'une mise a jour de fond, pas d'une simple actualisation de date.

## 7. Dette structurelle restante
- [Constate] `app/server.py` reste un point de couplage important entre HTTP, securite admin, logs, restart, settings admin et hermeneutique.
- [Constate] `app/admin/runtime_settings.py` reste une facade lourde malgre la presence de sous-modules `spec`, `repo`, `validation` et `secrets`.
- [Constate] `app/minimal_validation.py` reste volumineux mais doit demeurer la couche smoke globale selon la politique du repo.
- [Constate] `app/web/admin.js` demeure dense meme apres le split par sections; la surface admin garde un cout de changement notable.
- [Constate] `app/web/log/log.js` reste un module concentre pour une surface pourtant critique d'observabilite.
- [Constate] `app/memory/memory_store.py` reste relativement dense et melange persistence, evidence identitaire, audit arbitre et KPIs hermeneutiques.
- [Infere] Les prochains gains de lisibilite viendront davantage du desepaississement de facades que d'une reouverture doctrinale du pipeline hermeneutique.

## 8. Points de vigilance
- [Constate] La posture de securite admin reste dependante du runtime; elle n'est pas auto-durcie par une politique unique compilee.
- [Constate] Le repo repose encore sur un point d'entree Flask unique, ce qui augmente le risque de regression des changements transverses.
- [Constate] La documentation d'entree doit rester synchronisee avec le runtime reel; a defaut, le risque principal est documentaire plus que fonctionnel.
- [Infere] Un faux refacto consistant a deplacer du code sans reduire la concentration de responsabilites serait maintenant plus nuisible qu'utile.

## 9. Ordre de suite recommande
1. [Recommande] Desepaissir `app/server.py` par sous-surfaces de routes, sans changer les contrats HTTP.
2. [Recommande] Continuer a reduire la facade `app/admin/runtime_settings.py`, en laissant les sous-modules garder la responsabilite metier reelle.
3. [Recommande] Poursuivre le split frontend admin/logs la ou il diminue vraiment la densite locale (`admin.js`, `log.js`), sans recruter une nouvelle complexite cosmétique.
4. [Recommande] Garder les etats projet dates, l'audit canonique et le `README.md` comme surfaces vivantes alignees au runtime reel.
5. [Recommande] Laisser le Lot 9 archive; porter les suites sur `app/docs/todo-todo/memory/hermeneutical-add-todo.md` et `app/docs/todo-todo/product/Frida-installation-config.md`.

## 10. References associees
- etats projet courants:
  - `app/docs/states/project/Frida-State-french-03-04-26.md`
  - `app/docs/states/project/Frida-State-english-03-04-26.md`
- etats projet precedents:
  - `app/docs/states/project/Frida-State-french-28-03-26.md`
  - `app/docs/states/project/Frida-State-english-28-03-26.md`
- operations:
  - `app/docs/states/operations/hermeneutic-full-rollout-preconditions.md`
  - `app/docs/states/operations/frida-installation-operations.md`
- archive de cloture Lot 9:
  - `app/docs/todo-done/refactors/hermeneutic-convergence-node-todo.md`
