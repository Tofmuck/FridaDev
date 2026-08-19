# Frida V1 - Mega audit code + stack - contre-audit multi-agent - 2026-06-24

Statut: contre-audit historique archive apres cloture du mega-audit au Lot Z le 2026-08-19; preuve read-only parallele au mega-audit principal.
Archive: `app/docs/todo-done/audits/frida-v1-mega-audit-code-stack-counter-audit-2026-06-24.md`.
Branche: `FridaV1-Mega-Audit-Code-Stack`.
Base verifiee: `bc8aee23499cd58fcd29abfb7314a9a2a688e3d6`, puis support Lot 0 principal `d43248e4` observe.
Runtime modifie: non.
Plateforme modifiee: non.
Secrets/logs bruts/contenu utilisateur affiches: non.

## Methode

Ce contre-audit a utilise six agents read-only en parallele, puis une relecture
locale de consolidation par Codex. Les agents ont couvert des domaines
independants:

- plateforme Docker, services, ports, health, reseaux;
- Caddy, Authelia, Adminer, surface admin et lateralite Docker;
- secrets, `.env`, backups, permissions, logs bornes;
- architecture backend et frontieres modules;
- observabilite, dashboard, content-free et logs;
- frontend, admin UI, panels workspace et DOM.

Les agents n'ont pas patche, n'ont pas redemarre de service et n'ont pas
conserve de fichiers temporaires. Les scans logs sont restes bornes et
content-free.

## Verdict court

- P0: aucun P0 confirme.
- P1: risques locaux de permissions secrets/backups confirmes cote plateforme.
- P2: plusieurs dettes serieuses confirment que le mega-audit doit traiter
  d'abord la surface operateur/infra, puis les surfaces content-free et
  architecture.
- P3: dette de documentation, tests, UI et lisibilite importante.
- Invalides importants: pas de bypass public Authelia observe; `/api/admin/*`
  resiste aux appels lateraux directs avec `Remote-User` forge.

## Findings consolides

### P1

#### P1-SAU-ENV-PERMISSIONS-01 - `.env` plateforme lisible localement

- Statut: confirme par deux agents.
- Zone: `/opt/platform/.env` et backups racine `.env.bak-*`.
- Constat: le fichier actif et des backups racine sont lisibles par `other`.
- Preuve content-free: metadata `stat`, noms de cles sensibles comptes sans
  valeurs; aucune valeur affichee.
- Impact: exposition locale possible si un compte/processus non privilegie est
  compromis.
- Remediation attendue: lot Sauron dedie, `chmod 600` ou exception explicite,
  verification `docker compose config --quiet` et health checks.
- Risque: ne pas changer de contenu ni rotation sans decision separee.

#### P1-SAU-SENSITIVE-BACKUPS-PERMS-01 - backups/dumps/keys sensibles trop lisibles

- Statut: confirme par deux agents.
- Zone: `/opt/platform/backups`, `/opt/platform/_codex_backups`,
  `/opt/platform/_codex_reports`, backups n8n, Authelia, Nextcloud,
  Doc-pipeline, key backup Stirling.
- Constat: plusieurs dumps, sqlite, archives et une cle backup sont lisibles
  localement par d'autres comptes ou traversables via dossiers trop ouverts.
- Preuve content-free: chemins, modes, tailles, categories seulement.
- Impact: fuite locale de donnees operationnelles ou secrets historiques.
- Remediation attendue: fermer permissions, matrice retention, politique de
  conservation, decision explicite avant suppression.
- Risque: purge destructive interdite sans GO operateur.

### P2 plateforme / Sauron

#### P2-SAU-ADMINER-LATERAL-01 - Adminer joignable depuis le grand reseau Docker

- Statut: confirme.
- Zone: `/opt/platform/fridadev-db/docker-compose.yml`, `platform_platform_net`.
- Constat: `fridadev-db.frida-system.fr` public est protege par Authelia, mais
  un conteneur pair du grand reseau peut joindre directement Adminer par nom
  Docker.
- Preuve: test lateral depuis `platform-homepage` vers
  `http://platform-frida-adminer:8080/` retourne `200`.
- Impact: surface admin DB plus large que necessaire en cas de compromission
  d'un conteneur pair; pas un bypass DB sans credentials.
- Remediation attendue: isoler Adminer sur reseau proxy dedie Caddy/Adminer +
  reseau DB, retirer du grand `platform_platform_net` si compatible.

#### P2-SAU-COCKPIT-DOCKER-REACHABILITY-01 - Cockpit joignable depuis reseaux Docker

- Statut: confirme a revalider en lot Sauron.
- Zone: Cockpit `*:9090`, UFW, reseaux Docker `172.20.0.0/16` et
  `172.23.0.0/16`.
- Constat: Internet direct est bloque par UFW, mais les ranges Docker sont
  autorises et peuvent joindre Cockpit hors Authelia.
- Impact: surface host sensible accessible depuis conteneurs si un conteneur est
  compromis.
- Remediation attendue: auditer besoin reel Cockpit depuis Docker; restreindre
  UFW si non necessaire.

#### P2-SAU-DOCKER-SOCKET-SURFACE-01 - Docker socket direct/proxy a justifier

- Statut: confirme.
- Zone: `platform-docker-socket-proxy`, `platform-frida-v4-status`.
- Constat: le proxy est attendu, mais un service status a aussi un montage
  direct du socket Docker.
- Impact: risque host si service consommateur est compromis.
- Remediation attendue: matrice consommateurs/endpoints; retirer direct socket
  si le proxy suffit.

#### P2-SAU-HEALTHCHECKS-ABSENT-01 - healthchecks absents sur services critiques

- Statut: confirme.
- Zone: Caddy, Nextcloud, Nextcloud DB/Redis/Cron, n8n, SearxNG, Adminer,
  doc-pipeline, socket proxy.
- Constat: pas de conteneur unhealthy observe, mais plusieurs services n'ont pas
  de healthcheck Docker.
- Impact: monitoring moins discriminant; pannes silencieuses possibles.
- Remediation attendue: ajouter healthchecks bornes service par service, sans
  redemarrage large non controle.

#### P2-SAU-FRIDADEV-CONTAINER-HARDENING-01 - container app root et peu durci

- Statut: confirme.
- Zone: `platform-fridadev`.
- Constat: process root, `no-new-privileges=false`, rootfs non read-only,
  mounts RW.
- Impact: blast radius plus large en cas de compromission app.
- Remediation attendue: lot hardening progressif avec tests rebuild, user non
  root si compatible, `no-new-privileges`, evaluation read-only rootfs.

#### P2-SAU-NEXTCLOUD-DATA-RW-MOUNTS-01 - doc-pipeline monte fichiers Nextcloud en RW

- Statut: confirme.
- Zone: `doc-pipeline`, `doc-pipeline-api`, data Nextcloud utilisateur.
- Constat: montage large `/opt/platform/data/nextcloud/data/tof/files` en RW.
- Impact: compromission doc-pipeline peut modifier/supprimer fichiers.
- Remediation attendue: verifier besoin RW; passer RO ou limiter chemin si
  possible.

#### P2-SAU-PERMISSIONS-GOVERNANCE-01 - backups/reports/logs traversables

- Statut: confirme.
- Zone: `/opt/platform/backups`, `_codex_backups`, `_codex_reports`, logs n8n,
  logs Stirling.
- Constat: nombreuses preuves/backups/logs lisibles ou traversables largement.
- Impact: dette de gouvernance, retention et cloisonnement.
- Remediation attendue: politique de retention + modes cibles + inventaire
  content-free.

#### P2-SAU-AGENTS-ADMIN-TOKEN-STALE-01 - contradiction `/opt/platform/AGENTS.md`

- Statut: confirme.
- Zone: `/opt/platform/AGENTS.md` vs `/opt/platform/fridadev/AGENTS.md`.
- Constat: AGENTS plateforme parle encore d'Authelia + `FRIDA_ADMIN_TOKEN` sur
  APIs admin, alors que le contrat courant est proxy `Remote-User` ou loopback,
  sans token humain.
- Impact: risque de reintroduire un ancien garde par confusion documentaire.
- Remediation attendue: patch docs Sauron, sans toucher runtime.

### P2 applicatif / Celebrimbor

#### P2-CEL-ADMIN-PROMPTS-DOM-01 - prompts complets rendus dans l'admin UI

- Statut: confirme, severite requalifiee P2 plutot que P1 car surface admin
  protegee et serveur solo, mais incoherence forte avec l'ambition content-free.
- Zone: `app/admin/runtime_settings_api_view.py`, `app/web/admin_section_main_model.js`,
  `app/web/admin_ui_common.js`, `app/web/admin.html`, tests admin.
- Constat: l'admin settings expose `system_prompt` et `hermeneutical_prompt`
  complets en champs readonly; les tests valident cette exposition.
- Impact: contenu prompt brut dans DOM admin, screenshot/export/browser cache
  possible; contradiction avec la discipline d'observabilite content-free si on
  considere l'admin comme surface ordinaire.
- Decision necessaire: garder comme exception operateur explicite ou remplacer
  par metadonnees/statuts + content gate dedie.

#### P2-CEL-LLM-ERROR-RAW-01 - erreurs LLM renvoient/loggent `str(exc)`

- Statut: confirme.
- Zone: `app/core/chat_llm_flow.py:583-594`, `669-683`, `773-794`,
  `app/admin/admin_logs.py` writer brut.
- Constat: certaines branches stockent `error=str(exc)` et les branches
  non-stream retournent `Connexion au LLM: {exc}` ou `Erreur: {exc}`.
- Impact: risque de cause brute/provider URL/token-like renvoyee a l'utilisateur
  ou stockee avant projection admin.
- Remediation attendue: `error_code`/`error_class`, message utilisateur stable,
  test sentinelle URL/token/path.

#### P2-CEL-DASHBOARD-WEB-LEGACY-RAW-01 - read-model dashboard rematerialise URL/hash web legacy

- Statut: confirme.
- Zone: `app/observability/turn_pipeline_read_model.py:836-907`.
- Constat: champs legacy `url`, `crawl_query_sha256_12`, `query_sha256_12`
  peuvent ressortir dans facts/dashboard.
- Impact: tension avec contrats Observabilite/Continuity, surtout hash stable de
  requete et URL brute.
- Remediation attendue: projection legacy content-free, tests avec event
  historique sentinelle.

#### P2-CEL-IDENTITY-HASH-POLICY-01 - hashes courts d'identite a trancher

- Statut: confirme comme decision P2/P3; classer P2 si identite est contenu
  sensible.
- Zone: `app/observability/identity_observability.py` et projection pipeline.
- Constat: `sha256_12` qualifie sur blocs identity/static/mutable/reason.
- Impact: correlation/dictionnaire possible pour textes courts.
- Remediation attendue: documenter exception HMAC/salt ou supprimer les hashes
  stables au profit presence/longueur/counts.

#### P2-CEL-NOTES-UI-GAP-01 - Notes V1 API sans surface browser equivalente

- Statut: confirme fonctionnellement comme gap UX/P2 produit, non bug runtime.
- Zone: routes Notes folder-scoped et frontend workspace folder panels.
- Constat: UI couvre Documents/Exports/Images mais pas Notes; pas de panel Notes
  ni payload chat `workspace_note_id(s)` visible.
- Impact: capacite V1 livree backend mais difficilement utilisable depuis la UI.
- Remediation attendue: decision produit: livrer UI Notes minimale ou documenter
  explicitement comme API-only/post-V1.

#### P2-CEL-FRONTEND-EMPTY-ON-ERROR-01 - erreurs panels rendues comme listes vides

- Statut: confirme.
- Zone: `app/web/chat_threads_sidebar.js`, panels Documents/Exports/Images.
- Constat: erreurs de chargement absorbees en `[]`, puis UI affiche `Aucun...`.
- Impact: panne API vendue comme absence de donnees.
- Remediation attendue: etats erreur par panel + tests 500/payload invalide.

#### P2-CEL-CHAT-ORCHESTRATION-GRAVITY-01 - orchestration chat concentree

- Statut: confirme.
- Zone: `app/core/chat_service.py`, `chat_response()`.
- Constat: flow de plus de 500 lignes sequence toutes les lanes et final locks.
- Impact: interactions entre lanes, bypass capsule et final locks difficiles a
  prouver par tests feature isoles.
- Remediation attendue: golden tests d'ordre/payload avant refactor; extractions
  par responsabilite seulement.

#### P2-CEL-SERVER-BOUNDARY-GRAVITY-01 - `server.py` reste orchestration large

- Statut: confirme.
- Zone: `app/server.py`.
- Constat: routes HTTP, bootstrap DB/settings, garde admin, proxies logs,
  streaming finalization dans un seul fichier de 1849 lignes.
- Impact: frontiere transport/service brouillee, risque de regression et de
  garde oubliee.
- Remediation attendue: snapshot routes + extraction blueprints/services par
  lots, pas refactor cosmetique.

#### P2-CEL-ADMIN-400-RAW-01 - erreurs 400 admin renvoient `str(exc)`

- Statut: confirme.
- Zone: routes admin logs/dashboard/export dans `app/server.py`.
- Constat: plusieurs `except ValueError as exc: error=str(exc)`; les parseurs
  peuvent inclure valeur invalide.
- Impact: reflet possible d'un parametre admin contenant URL/token/path.
- Remediation attendue: reason codes stables, tests sentinelles.

### P3

#### P3-CEL-FINAL-LOCK-CONFLICT-TEST-01 - conflit Agenda/Biblio implicite a tester

- Statut: confirme P3, non P2 car Agenda dormant/off par defaut.
- Zone: `app/core/chat_service.py:1146-1168`.
- Constat: `agenda_final_response_override or biblio_final_response_override`.
- Impact: politique `agenda_over_biblio` existe ailleurs mais ce chemin merite
  un test d'integration fake si les deux locks apparaissent.

#### P3-CEL-BIBLIO-COMMENTS-STALE-01 - commentaires Biblio parlent encore de deterministe

- Statut: confirme.
- Zone: `app/config.py`, `app/biblio/librarian_agent_runtime.py`.
- Constat: commentaires/config historiques disent que le deterministe controle
  encore la reponse, alors que l'agent-first peut produire la reponse.
- Impact: risque de recoder des regex au lieu de respecter le bibliothecaire
  agentique.

#### P3-CEL-AGENDA-DORMANT-WORDING-01 - wording Agenda encore bruyant mais pas bloquant

- Statut: requalifie P3 faible/stale partiel.
- Zone: `app/docs/todo-todo/product/frida-agenda-agent.md`.
- Constat: le statut dormant post-V1 est globalement clair; l'expression
  `n'ouvre aucun runtime Agenda` peut etre mal lue mais ne contredit pas la
  cloture pragmatique.

#### P3-CEL-LOG-FRONTEND-DENYLIST-01 - `/log` UI filtre par denylist

- Statut: confirme.
- Zone: `app/web/log/log.js`.
- Constat: backend projette deja, mais frontend affiche les cles restantes apres
  denylist.
- Impact: futur champ safe-looking pourrait etre rendu.
- Remediation attendue: allowlist UI explicite ou test sentinelle champ inconnu.

#### P3-CEL-FILENAMES-CONTENT-FREE-DECISION-01 - statut des filenames a trancher

- Statut: decision P3.
- Zone: dashboard/read-model documents.
- Constat: filenames sont exposes comme metadonnees produit. Cela peut etre OK,
  mais doit etre doctrinalement explicite.

#### P3-CEL-LARGE-FILES-AMPLIFIED-01 - dette gros fichiers confirmee

- Statut: confirme.
- Zone: repo complet.
- Constat: scan Codex a releve 114 fichiers >=600 lignes; certains sont docs ou
  tests, mais plusieurs modules runtime depassent largement la limite AGENTS.
- Remediation attendue: lot refactor seulement apres P1/P2, avec golden tests.

## Invalides ou requalifies

- Public bypass FridaDev/Adminer: invalide; endpoints publics testes redirigent
  vers Authelia ou Nextcloud DAV retourne `401` attendu.
- `/api/admin/*` lateral bypass: invalide; appels lateraux directs et headers
  `Remote-User` forges refusent, Caddy trusted et loopback fonctionnent.
- Ports Docker publics hors Caddy: invalide; Docker publie seulement `80/443`.
- Secrets committes dans repo FridaDev: non confirme; hits observes surtout
  exemples/tests/fixtures attendus.
- JSONL baselines invalides: invalide; 123 fichiers, 709 records, 0 erreur.
- Agenda V1 incoherent: requalifie P3 faible; le dormant post-V1 est documente.

## Lots conseilles cote contre-audit

Ordre recommande, a fusionner avec la TODO principale du mega-audit:

1. Sauron P1: permissions `/opt/platform/.env` et backups racine.
2. Sauron P1/P2: backups/dumps/key/log permissions + retention.
3. Sauron P2: Adminer lateral, Cockpit Docker reachability, socket Docker,
   mounts RW larges, healthchecks.
4. Sauron docs: corriger `/opt/platform/AGENTS.md` sur `FRIDA_ADMIN_TOKEN`.
5. Celebrimbor P2 content-free: LLM errors, admin 400, dashboard web legacy,
   identity hashes decision.
6. Celebrimbor P2 UI/admin: prompts admin DOM, errors-as-empty, Notes UI gap.
7. Celebrimbor P2 architecture: golden tests puis extraction `server.py` /
   `chat_service.py` seulement par responsabilite.
8. P3 docs/tests: Biblio comments, final-lock conflict test, `/log` allowlist,
   filename doctrine, gros fichiers.

## Checks executes par le contre-audit

- Lecture `/Users/tof/Dev/AGENTS.md`, `/Users/tof/Dev/memory.md`.
- Lecture skill `dispatching-parallel-agents`.
- Lecture skill `deep-security-scan` comme cadrage de securite approfondie.
- Verification branche serveur: `FridaV1-Mega-Audit-Code-Stack`.
- Verification base: HEAD branche creee depuis `main`, puis commit Lot 0
  principal `d43248e4` observe.
- Scans read-only lignes/fichiers/patterns dans `/opt/platform/fridadev`.
- JSONL parse: 123 fichiers, 709 records, 0 erreur.
- Relecture ciblee lignes critiques signalees par agents.

## Hygiene

- Aucun patch runtime.
- Aucun patch plateforme.
- Aucun service redemarre.
- Aucun secret/log brut/contenu utilisateur affiche.
- Agents fermes apres collecte.
- Pas de fichier temporaire distant cree par les agents; le seul fichier cree
  par Codex est ce document de contre-audit.
