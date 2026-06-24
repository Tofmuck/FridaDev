# Frida V1 - Mega audit code + stack TODO

Statut: TODO actif.
Date d'ouverture: 2026-06-24.
Branche de travail: `FridaV1-Mega-Audit-Code-Stack`.
Audit source: `app/docs/todo-todo/audits/frida-v1-mega-audit-code-stack-2026-06-24.md`.
Contre-audit source: `app/docs/todo-todo/audits/frida-v1-mega-audit-code-stack-counter-audit-2026-06-24.md`.

## Etat global

- Objectif: nettoyer et durcir methodiquement FridaDev + stack OVH apres
  integration Frida V1 sur `main`.
- Mode: double discipline Sauron/Celebrimbor.
- Runtime modifie par Lot 0: non.
- Plateforme modifiee par Lot 0: non.
- Secrets/logs bruts affiches par Lot 0: non.
- P0 connu: aucun.
- P1 ouvert restant: backups/dumps/artefacts sensibles plateforme hors
  `.env.bak-*`.
- Lot 0.1: consolidation contre-audit executee; audit principal reconnu
  partiellement trop Sauron-heavy, findings Celebrimbor concrets integres.

## Lot 0.1 - Consolidation contre-audit Sauron/Celebrimbor

- [x] Comparer audit principal et contre-audit.
- [x] Declarer l'audit principal partiellement trop Sauron-heavy.
- [x] Valider/invalider/dedupliquer/requalifier chaque finding du contre-audit.
- [x] Integrer les findings Celebrimbor manquants dans le registre canonique.
- [x] Ne cocher aucun lot de correction runtime ou plateforme.

### Resolution Lot 0.1

- Validés: Adminer lateral, Cockpit reachability a revalider, healthchecks,
  hardening conteneur FridaDev, mounts Nextcloud RW, gouvernance permissions,
  AGENTS admin token stale, prompts admin DOM, erreurs LLM/admin 400,
  dashboard legacy raw, identity hash policy, Notes UI gap, frontend empty on
  error, chat orchestration gravity, final-lock conflict test, Biblio comments,
  log frontend denylist, filenames doctrine.
- Doublons/fusionnes: docker socket surface; server boundary gravity;
  large-files amplified.
- Invalides/stale: bypass public Authelia, bypass lateral `/api/admin/*`,
  ports publics hors Caddy, JSONL invalides, secrets repo committes non
  confirmes. Agenda dormant wording reste P3 faible / `needs_targeted_validation`.

## Lot 1A - Investigation permissions `.env`

Statut: investigation Sauron docs-only executee le 2026-06-24.
Finding cible: `P1-SAU-ENV-PERMISSIONS-01`.
Correction appliquee: non.
P1 ferme: non.

- [x] Inventorier les metadonnees `.env` et backups sans lire les valeurs.
- [x] Identifier les consommateurs reels de `/opt/platform/.env`.
- [x] Tester `docker compose config --quiet` avec et sans sudo, sans afficher
  de valeurs.
- [x] Classer les variables par noms seulement.
- [x] Valider/invalider les hypotheses H1-H5.
- [x] Comparer les options de correction A-E sans les appliquer.

### Resultat Lot 1A

- Permissions observees: `/opt/platform/.env` et les backups `.env.bak-*`
  sont en `0644 root:root`; `/opt` et `/opt/platform` sont traversables en
  `0755`; `/opt/platform/secrets` est en `0700 root:root`.
- Consommateurs confirmes: Docker Compose global par auto-chargement du
  `.env` projet et interpolation de variables, `doc-pipeline` via `../.env`,
  et `/opt/platform/frida-m4-rag/smoke.sh` via reference directe.
- Consommateurs non confirmes: `/opt/platform/scripts/*` ne contient pas de
  reference directe a `/opt/platform/.env` dans ce lot.
- Compat sans sudo: `docker compose config --quiet` echoue deja pour la stack
  globale sur un autre fichier env root-only, et pour `doc-pipeline` sur un
  fichier sous `secrets`; le `0644` du `.env` racine n'est donc pas suffisant
  pour operer ces grandes stacks sans sudo.
- Compat probablement impactee par `0600 root:root`: le smoke `frida-m4-rag`
  lance comme `tof` perdrait sa lecture directe du `.env` racine; les Compose
  globaux/doc-pipeline sans sudo echoueraient aussi plus tot, mais ils ne sont
  deja pas operationnels sans sudo.
- Variables par noms seulement: 41 noms observes; 5 classifies
  probablement secrets; 36 classifies config/hostname/tuning; 0 incertain.
- Hypotheses: H1 validee probable; H2 invalidee pour les grandes stacks mais
  partiellement vraie pour `frida-m4-rag/smoke.sh`; H3 validee; H4 validee; H5
  validee.

### Options Lot 1A

- Option A: `0600 root:root` pour actif et backups; meilleure securite locale,
  compat operateur via sudo, effet de bord probable sur `frida-m4-rag/smoke.sh`
  sans sudo; rollback `0644` borne si necessaire.
- Option B: `0640 root:tof` ou ACL dediee `tof`; compromis operateur, expose
  encore au compte `tof`, moins large que world-readable; test avec Compose et
  smoke; rollback par retrait ACL/groupe.
- Option C: split config non sensible + secrets verrouilles; meilleur modele a
  terme, plus de migration et risque de drift; tests Compose exhaustifs.
- Option D: sortir les variables M4/doc-pipeline vers secrets/env dedies;
  reduit pression sur `.env` racine, mais demande migration par stack.
- Option E: garder `0644` comme exception documentee; non recommande sauf
  preuve forte qu'un consommateur non-root legitime ne peut pas etre adapte.

Recommandation Lot 1A: appliquer ensuite un Lot 1B correctif borne, avec
backup metadata prealable, cible initiale Option B pour preserver le smoke
operateur `tof`, puis durcissement progressif vers Option C/D si la separation
des variables est validee. Ne pas fermer `P1-SAU-ENV-PERMISSIONS-01` avant la
preuve apres correction.

## Lot 1A.1 - Investigation impact Frida V4/M4

Statut: investigation Sauron docs-only executee le 2026-06-24.
Finding cible: `P1-SAU-ENV-PERMISSIONS-01`.
Correction appliquee: non.
P1 ferme: non.

- [x] Relire compose et smoke Frida V4/M4.
- [x] Lister les variables `FRIDA_M4_*` par noms seulement, token redacted.
- [x] Tester `docker compose config --quiet` M4 avec et sans sudo.
- [x] Verifier health/smoke M4 sans afficher de token.
- [x] Comparer les options A/B/B2/C/D pour l'impact Frida V4.

### Resultat Lot 1A.1

- Dependence a `/opt/platform/.env`: partielle, mais reelle.
- `.env` racine: porte `FRIDA_M4_CADDY_HOSTS` et
  `FRIDA_M4_API_TOKEN` redacted; il ne porte pas les model IDs M4 dans l'etat
  observe.
- `/opt/platform/frida-m4-rag/.env`: porte `FRIDA_M4_STACK_NAME`,
  `FRIDA_M4_DEVICE`, `FRIDA_M4_EMBEDDING_MODEL_ID=BAAI/bge-m3` et
  `FRIDA_M4_RERANK_MODEL_ID=BAAI/bge-reranker-v2-m3`.
- Compose M4: `docker compose config --quiet` reussit avec et sans sudo depuis
  `/opt/platform/frida-m4-rag`; il s'appuie sur le `.env` local et/ou les
  defaults du compose pour les model IDs, pas sur le `.env` racine.
- Caddy/global: `/opt/platform/docker-compose.yml` et `Caddyfile` utilisent le
  host public et le token M4 depuis le `.env` racine pour la surface publique.
- Smoke M4: `smoke.sh` lit explicitement `/opt/platform/.env` si
  `FRIDA_M4_API_TOKEN` n'est pas deja fourni dans l'environnement. Avec le mode
  courant, le smoke operateur `tof` passe: embedding health, embedding request,
  rerank health et rerank request OK, sortie courte sans token.
- Health local: pas de port host `127.0.0.1:18100` disponible; les healthchecks
  intra-conteneur sont healthy avec `BAAI/bge-m3`, dimension 1024,
  `BAAI/bge-reranker-v2-m3`, max length 512.

### Effets de bord Frida V4

- Option A `0600 root:root`: ne casse probablement pas les conteneurs M4 deja
  lances ni `docker compose config` M4 sous `tof`, mais casse le smoke M4 lance
  par `tof` si le token n'est pas fourni autrement; la surface Caddy globale
  reste operable via sudo.
- Option B `0640 root:tof`: preserve le smoke M4 et retire la lecture par tout
  autre utilisateur local; compat operateur la plus simple pour le prochain
  correctif borne.
- Option B2 ACL `u:tof:r`: meme preservation que B sans changer le groupe,
  mais ajoute une dependance ACL a documenter et rollbacker.
- Option C dupliquer/sortir les variables M4 necessaires dans
  `/opt/platform/frida-m4-rag/.env`: permet ensuite `0600 root:root` sur le
  `.env` racine sans casser le smoke, mais duplique un token si fait sans
  design de secrets dedie.
- Option D adapter `smoke.sh` pour exiger token/env explicite ou sudo: modele
  le plus strict, mais moins ergonomique et necessite un runbook operateur.

Recommandation Lot 1A.1: pour Lot 1B, preferer Option B immediate
`0640 root:tof` sur `/opt/platform/.env` et ses backups, avec backup metadata,
`docker compose config --quiet` global/doc-pipeline/M4, smoke M4, health
FridaDev/Caddy, puis planifier C/D si l'objectif devient suppression de toute
lecture racine par `tof`. Ne pas appliquer Option A sans adapter le smoke ou
fournir explicitement `FRIDA_M4_API_TOKEN`.

## Lot 1B - Correctif permissions `.env` root

Statut: execute le 2026-06-24.
Decision operateur: GO `0640 root:tof`.
Finding cible: `P1-SAU-ENV-PERMISSIONS-01`.
Runtime redemarre: non.
Plateforme modifiee: oui, permissions/ownership uniquement sur
`/opt/platform/.env` et `/opt/platform/.env.bak-*`.
Artefact metadata: `/opt/platform/_codex_reports/frida-v1-mega-audit-lot1b-env-permissions-metadata-20260624T161205Z.txt`.

- [x] Capturer les metadonnees avant correction sans lire de valeurs.
- [x] Creer l'artefact metadata content-free, sans hash de contenu.
- [x] Appliquer `root:tof` et `0640` a `/opt/platform/.env`.
- [x] Appliquer `root:tof` et `0640` aux backups `/opt/platform/.env.bak-*`.
- [x] Prouver que `tof` lit encore et que `nobody` ne lit plus.
- [x] Valider Compose global/doc-pipeline via sudo, M4 avec et sans sudo,
  FridaDev app/db sans sudo.
- [x] Valider smoke Frida V4/M4 sans fuite de token.
- [x] Valider sante FridaDev/Caddy sans rebuild/restart.

### Resultat Lot 1B

- Avant: actif et 3 backups `.env.bak-*` en `0644 root:root`.
- Apres: actif et 3 backups `.env.bak-*` en `0640 root:tof`.
- Lecture attendue: `tof` lit encore; `nobody` ne lit plus.
- Compose: global sudo OK, doc-pipeline sudo OK, M4 utilisateur OK, M4 sudo
  OK, FridaDev app OK, FridaDev DB OK.
- Smoke M4: OK; 9 lignes, 337 octets, aucun marqueur token/secret/cookie dans
  la sortie capturee.
- Sante FridaDev/Caddy: conteneurs FridaDev healthy; `/admin` repond `302`
  vers Authelia via Caddy.
- Secrets/logs bruts affiches: non.
- `P1-SAU-ENV-PERMISSIONS-01`: clos par Lot 1B.

## Lot 1C - Investigation backups/dumps/reports sensibles

Statut: investigation Sauron metadata-only executee le 2026-06-24.
Finding cible: `P1-SAU-SENSITIVE-BACKUPS-PERMS-01`.
Correction appliquee: non.
P1 ferme: non.

- [x] Inventorier par metadonnees les backups, dumps, archives, rapports,
  copies `.env`, cles et bases locales sous `/opt/platform`.
- [x] Ne lire aucun contenu de secret, dump, backup, log, base ou archive.
- [x] Ne calculer aucun hash de contenu sensible.
- [x] Tester la lisibilite `tof` / `nobody` par `test -r`, sans afficher de
  contenu.
- [x] Reperer les consommateurs probables uniquement via scripts/configs non
  sensibles et metadonnees Docker.
- [x] Classer les familles selon le risque et proposer un lot correctif sans
  l'appliquer.

### Resultat Lot 1C

- Methodologie: `find -xdev` metadata-only, `stat`, tests `test -r` sous
  `tof` et `nobody`, inventaire Docker des mounts et grep borne sur scripts,
  configs et docs versionnes; aucun contenu backup/dump/log/secret lu.
- Deja traite par Lot 1B: `/opt/platform/.env` et les 3 backups
  `/opt/platform/.env.bak-*` sont en `0640 root:tof`, lisibles par `tof`, non
  lisibles par `nobody`.
- `active_sensitive_backup`: 25 fichiers, environ 551 MB; 5 world-readable,
  6 group-readable, 14 dans des racines montees par conteneur. Exemples a
  traiter avec prudence: backups SQLite historiques sous
  `/opt/platform/data/n8n`, base active legacy sous
  `/opt/platform/data/n8n/.n8n`, base locale Stirling sous
  `/opt/platform/data/stirling/configs`.
- `restorable_db_dump`: 22 fichiers, environ 314 MB; 16 world-readable, 16
  group-readable, 9 dans des racines montees. Familles a risque: dumps
  doc-pipeline, Nextcloud, n8n, crawl4ai, imports FridaDev DB et backups SQL
  Stirling. Les imports FridaDev DB observes sont deja stricts mais restent
  montes dans la sous-stack DB.
- `codex_report_sensitive_metadata`: 7 fichiers, environ 95 MB; 6
  world-readable. Les dumps DB de lots Frida V1 dans
  `/opt/platform/_codex_reports` sont host-only et doivent etre durcis ou
  reclasses; le dump Notes deja en `0600` est conforme.
- `historical_archive_sensitive`: 10 fichiers, environ 737 MB; 8
  world-readable. Familles observees: archives Nextcloud upgrade, Authelia,
  crawl4ai, Homepage et autres bundles de sauvegarde sous `_codex_backups` ou
  `/opt/platform/backups`.
- `secret_key_material`: 5 fichiers; 3 world-readable. Les cles privees
  observees sont strictes; les cles publiques peuvent etre acceptables mais
  doivent etre documentees; une cle JWT Stirling sous backup/config est un
  candidat de correction ciblee.
- `probably_safe_metadata_only`: 43 entrees, majoritairement sources ou assets
  Nextcloud matches par nom/extension; aucun correctif a lancer depuis ce
  finding sans validation plus fine.
- `needs_targeted_validation`: 16 entrees, incluant des repertoires `0755`
  sous `/opt/platform/backups`, `_codex_backups`, `_codex_reports`, Stirling,
  doc-pipeline et FridaDev state. Les droits des repertoires pilotent la
  decouvrabilite et doivent etre traites avec les fichiers, pas separement.
- `needs_operator_decision`: retention, purge/deplacement eventuel, mode cible
  `0600 root:root` vs `0640 root:tof` pour artefacts host-only, exceptions
  cles publiques et fenetre de validation service pour donnees actives.
- Consommateurs probables: les fichiers sous `/opt/platform/data/*` peuvent
  etre actifs via mounts conteneurs; les familles `_codex_reports`,
  `_codex_backups` et `/opt/platform/backups` sont majoritairement host-only et
  liees a des preuves, migrations ou sauvegardes operateur.
- Impact `0600 root:root`: adapte aux artefacts host-only sans consommateur
  non-root, mais risque de casser des fichiers actifs service-owned sous
  `/opt/platform/data/*` si applique en masse.
- Impact `0640 root:tof`: bon compromis pour artefacts host-only que
  l'operateur doit inspecter/restaurer, mais insuffisant pour fichiers de
  service qui doivent rester lisibles par leur UID conteneur.
- Impact ACL: utile pour garder owner/service et donner lecture operateur
  ciblee, mais ajoute une dependance a documenter et rollbacker.
- Purge/deplacement: a reserver a une decision de retention; ne pas faire
  pendant un lot permission-only.
- Recommendation Lot 1C: scinder le correctif. Lot 2A pour host-only
  `_codex_reports`, `_codex_backups` et `/opt/platform/backups` avec modes
  stricts et preuve sans contenu. Lot 2B pour donnees actives montees sous
  `/opt/platform/data/*`, avec validation par service avant tout chmod.
  `P1-SAU-SENSITIVE-BACKUPS-PERMS-01` reste ouvert jusqu'aux corrections.

## Registre findings

### P1-SAU-ENV-PERMISSIONS-01

- Statut initial: open.
- Statut courant: closed by Lot 1B.
- Severite: P1.
- Fichiers/zones suspects: `/opt/platform/.env`.
- Lot cible: Lot 1.
- Investigation Lot 1A: valide; cause probable umask/copie `022`, besoins
  non-root limites surtout a `frida-m4-rag/smoke.sh`; correction non appliquee.
- Investigation Lot 1A.1: Frida V4/M4 depend partiellement du `.env` racine
  pour host/token public et smoke operateur; Compose M4 depend surtout du
  `.env` local; correction non appliquee.
- Correction Lot 1B: actif et backups `.env.bak-*` passes de `0644 root:root`
  a `0640 root:tof`; `nobody` refuse; Compose/smoke/health OK.
- Critere de cloture: permissions resserrees ou exception documentee,
  verification Compose/health sans secret affiche.
- Preuve minimale: `stat` content-free avant/apres, `docker compose config
  --quiet`, health Caddy/FridaDev.
- Hors-scope: rotation secret, changement contenu `.env`, restart large.

### P1-SAU-SENSITIVE-BACKUPS-PERMS-01

- Statut initial: open.
- Statut courant: open; investigation Lot 1C completee, correction non
  appliquee.
- Severite: P1.
- Fichiers/zones suspects: `/opt/platform/backups`,
  `/opt/platform/_codex_backups`, `/opt/platform/_codex_reports`,
  `/opt/platform/data/*`, dumps DB, archives, keys.
- Lot cible: Lot 2.
- Investigation Lot 1C: valide. Le risque est confirme sur des dumps DB,
  archives historiques, rapports Codex et quelques fichiers actifs ou
  service-owned; les familles `.env` racine sont exclues car closes par Lot 1B.
- Classification Lot 1C: `closed_by_lot_1b_already`,
  `active_sensitive_backup`, `restorable_db_dump`,
  `codex_report_sensitive_metadata`, `historical_archive_sensitive`,
  `secret_key_material`, `probably_safe_metadata_only`,
  `needs_targeted_validation`, `needs_operator_decision`.
- Plan propose: Lot 2A host-only backups/reports/dumps; Lot 2B donnees actives
  montees et fichiers service-owned; aucune purge sans decision retention.
- Critere de cloture: matrice retention/permissions et absence de secret/dump
  world-readable non justifie.
- Preuve minimale: inventaire metadata content-free, pas de contenu ouvert.
- Hors-scope: purge destructive sans GO operateur.

### P2-SAU-LOG-SECRETLIKE-01

- Statut initial: open.
- Severite: P2.
- Zones suspectes: logs recents Authelia/Caddy.
- Lot cible: Lot 2.
- Critere de cloture: faux positif documente ou redaction/log-level corrige.
- Preuve minimale: scan borne sans lignes brutes, counts avant/apres.
- Hors-scope: purge logs globale.

### P2-SAU-DOCKER-SOCKET-SURFACE-01

- Statut initial: open.
- Severite: P2.
- Zones suspectes: `platform-docker-socket-proxy`, `platform_proxy_net`,
  compose global, service status avec socket direct selon contre-audit.
- Alias/fusion: confirme et amplifie par `P2-SAU-DOCKER-SOCKET-SURFACE-01`
  contre-audit.
- Lot cible: Lot 3.
- Critere de cloture: matrice consumers/endpoints/reseaux.
- Preuve minimale: `docker inspect` content-free, compose metadata,
  eventuellement test consumer.
- Hors-scope: couper socket proxy sans connaitre dependances.

### P2-SAU-ADMINER-LATERAL-01

- Statut initial: open.
- Severite: P2.
- Zones suspectes: `platform-frida-adminer`, `platform_platform_net`,
  `fridadev-db.frida-system.fr`.
- Lot cible: Lot 3.
- Critere de cloture: Adminer non joignable lateralement depuis le grand reseau
  Docker, ou exception documentee avec justification.
- Preuve minimale: test lateral content-free depuis un conteneur pair, headers
  publics Authelia sans cookie, `docker inspect` reseaux.
- Hors-scope: suppression Adminer ou changement DB sans GO operateur.

### P2-SAU-COCKPIT-DOCKER-REACHABILITY-01

- Statut initial: needs_targeted_validation.
- Severite: P2.
- Zones suspectes: Cockpit host port, UFW, ranges Docker.
- Lot cible: Lot 3.
- Critere de cloture: confirmer ou invalider la reachability Cockpit depuis
  conteneurs; restreindre ou documenter si confirme.
- Preuve minimale: test reseau borne sans credentials, inventaire UFW
  content-free, aucune auth Cockpit tentee.
- Hors-scope: modification firewall sans plan Sauron.

### P2-SAU-HEALTHCHECKS-ABSENT-01

- Statut initial: open.
- Severite: P2.
- Zones suspectes: Caddy, Nextcloud, Nextcloud DB/Redis/Cron, n8n, SearxNG,
  Adminer, doc-pipeline, socket proxy.
- Lot cible: Lot 3.
- Critere de cloture: healthcheck ajoute ou absence justifiee service par
  service.
- Preuve minimale: `docker inspect` health status, compose metadata, tests
  service bornes.
- Hors-scope: restart large ou healthcheck qui mute les donnees.

### P2-SAU-FRIDADEV-CONTAINER-HARDENING-01

- Statut initial: open.
- Severite: P2.
- Zones suspectes: `platform-fridadev`.
- Lot cible: Lot 3.
- Critere de cloture: decision explicite sur user non-root,
  `no-new-privileges`, rootfs read-only et mounts RW necessaires.
- Preuve minimale: `docker inspect` content-free, rebuild app seulement dans
  un lot runtime autorise, tests admin/chat cibles.
- Hors-scope: changement conteneur sans rollback et health checks.

### P2-SAU-NEXTCLOUD-DATA-RW-MOUNTS-01

- Statut initial: open.
- Severite: P2.
- Zones suspectes: `doc-pipeline`, `doc-pipeline-api`, mounts data Nextcloud.
- Lot cible: Lot 3.
- Critere de cloture: montages RW confirmes necessaires ou reduits/RO.
- Preuve minimale: `docker inspect` mounts content-free, test fonctionnel
  doc-pipeline si modification autorisee.
- Hors-scope: lecture contenu Nextcloud ou modification fichiers utilisateur.

### P2-SAU-COMPOSE-PERMISSIONS-01

- Statut initial: open.
- Severite: P2.
- Zones suspectes: compose FridaDev group-writable.
- Lot cible: Lot 2 ou 3.
- Critere de cloture: modes/ownership explicites et verifies.
- Preuve minimale: `stat`, `docker compose config --quiet`.
- Hors-scope: changement runtime.

### P2-SAU-PERMISSIONS-GOVERNANCE-01

- Statut initial: open.
- Severite: P2.
- Zones suspectes: `/opt/platform/backups`, `_codex_backups`,
  `_codex_reports`, logs et dumps runtime.
- Lot cible: Lot 2.
- Critere de cloture: politique de retention, modes cibles et exceptions
  documentees; P1 backups traite sans purge opportuniste.
- Preuve minimale: inventaire metadata content-free, aucune valeur lue.
- Hors-scope: suppression/chmod recursive non bornee.

### P2-SAU-AGENTS-ADMIN-TOKEN-STALE-01

- Statut initial: open.
- Severite: P2.
- Zones suspectes: `/opt/platform/AGENTS.md` vs
  `/opt/platform/fridadev/AGENTS.md`.
- Lot cible: Lot 8.
- Critere de cloture: instructions Sauron alignees avec contrat OVH courant:
  Authelia + proxy `Remote-User`/loopback, pas de token humain.
- Preuve minimale: diff docs-only, grep `FRIDA_ADMIN_TOKEN` contextualise.
- Hors-scope: changer runtime ou `.env`.

### P2-CEL-ADMIN-COMPAT-KNOBS-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: tests admin mentionnant `FRIDA_ADMIN_TOKEN` /
  `FRIDA_ADMIN_LAN_ONLY`, `app/server.py`.
- Lot cible: Lot 5.
- Critere de cloture: tests admin alignes sur loopback/proxy `Remote-User`,
  knobs obsoletes marques compat si conserves.
- Preuve minimale: tests admin conteneur, refus lateral direct.
- Hors-scope: reintroduire token humain.

### P2-CEL-ADMIN-PROMPTS-DOM-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: `app/admin/runtime_settings_api_view.py`,
  `app/web/admin_section_main_model.js`, `app/web/admin_ui_common.js`,
  `app/web/admin.html`, tests admin.
- Lot cible: Lot 5 ou 6.
- Critere de cloture: decision explicite: exception operateur assumee avec
  content gate, ou remplacement par metadonnees/statuts sans prompt brut DOM.
- Preuve minimale: test admin DOM/JSON avec sentinelle prompt brut; scan
  content-free.
- Hors-scope: modifier prompts.

### P2-CEL-LLM-ERROR-RAW-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: `app/core/chat_llm_flow.py`, `app/admin/admin_logs.py`.
- Lot cible: Lot 6.
- Critere de cloture: erreurs LLM exposees via `error_code`/`error_class` et
  message utilisateur stable, sans `str(exc)` brut.
- Preuve minimale: tests sentinelles URL/token/path/provider error, logs
  content-free.
- Hors-scope: changer provider/model.

### P2-CEL-DASHBOARD-WEB-LEGACY-RAW-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: `app/observability/turn_pipeline_read_model.py`,
  dashboard read-model.
- Lot cible: Lot 6.
- Critere de cloture: legacy web facts projetes sans URL brute ni hash stable
  sensible non justifie.
- Preuve minimale: event historique sentinelle, dashboard JSON content-free.
- Hors-scope: purge historique.

### P2-CEL-IDENTITY-HASH-POLICY-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: `app/observability/identity_observability.py`,
  projection pipeline identity.
- Lot cible: Lot 6 ou 8.
- Critere de cloture: doctrine explicite sur hashes courts identity:
  suppression, HMAC/salt, ou exception justifiee.
- Preuve minimale: spec/docs + tests projection.
- Hors-scope: modifier contenu identity.

### P2-CEL-NOTES-UI-GAP-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: routes Notes folder-scoped, panels frontend workspace.
- Lot cible: Lot 5.
- Critere de cloture: decision produit UI Notes minimale ou statut
  API-only/post-V1 explicite.
- Preuve minimale: audit frontend/route, test UI si implementation future.
- Hors-scope: rouvrir backend Notes sans besoin.

### P2-CEL-FRONTEND-EMPTY-ON-ERROR-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: `app/web/chat_threads_sidebar.js`, panels
  Documents/Exports/Images.
- Lot cible: Lot 5 ou 7.
- Critere de cloture: erreurs API panels visibles comme erreur, pas comme
  liste vide.
- Preuve minimale: tests 500/payload invalide par panel.
- Hors-scope: redesign UI large.

### P2-CEL-EXCEPTION-RAW-SURFACE-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: `app/server.py`, `app/tools/web_search.py`,
  `app/core/*`, `app/memory/*`, `app/observability/*`, `app/biblio/*`.
- Lot cible: Lot 6.
- Critere de cloture: surfaces qualifiees; corrections bornees uniquement.
- Preuve minimale: tests content-free/fail-closed par surface.
- Hors-scope: remplacement massif aveugle de `str(exc)`.

### P2-CEL-ADMIN-400-RAW-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: `app/server.py` routes admin logs/dashboard/export.
- Lot cible: Lot 6.
- Critere de cloture: `ValueError`/400 admin renvoie reason code stable sans
  echo de valeur invalide.
- Preuve minimale: tests sentinelles URL/token/path dans query params.
- Hors-scope: refactor routes admin.

### P2-CEL-DOCS-ACTIVE-AUDITS-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: audits superseded dans `app/docs/todo-todo/audits`.
- Lot cible: Lot 8.
- Critere de cloture: aucun audit superseded ambigu comme travail actif.
- Preuve minimale: grep references, liens mis a jour.
- Hors-scope: reecrire constats historiques.

### P2-CEL-SERVER-ROUTE-GRAVITY-01

- Statut initial: open.
- Severite: P2.
- Fichier suspect: `app/server.py`.
- Alias/fusion: `P2-CEL-SERVER-BOUNDARY-GRAVITY-01`.
- Lot cible: Lot 9.
- Critere de cloture: plan de split par responsabilite et golden tests routes.
- Preuve minimale: snapshot routes, tests routes/admin/workspace/chat.
- Hors-scope: refactor sans tests.

### P2-CEL-CHAT-ORCHESTRATION-GRAVITY-01

- Statut initial: open.
- Severite: P2.
- Fichier suspect: `app/core/chat_service.py`.
- Lot cible: Lot 9.
- Critere de cloture: golden tests d'ordre lanes/final-lock/capsule avant
  extraction de l'orchestration.
- Preuve minimale: tests fake couvrant conflits lanes et bypass final-lock.
- Hors-scope: refactor chat sans preuve d'ordre comportemental.

### P2-CEL-REQUESTS-TIMEOUT-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: clients HTTP detectes par scan heuristique.
- Lot cible: Lot 4.
- Critere de cloture: timeouts/fallbacks verifies ou ajoutes.
- Preuve minimale: tests timeout/fallback.
- Hors-scope: provider live non demande.

### P3-CEL-LARGE-FILES-01

- Statut initial: open.
- Severite: P3.
- Alias/fusion: `P3-CEL-LARGE-FILES-AMPLIFIED-01`.
- Lot cible: Lot 9.
- Critere de cloture: lots de refactor cibles, pas cosmetiques.
- Preuve minimale: lignes avant/apres, tests inchanges.

### P3-CEL-TEST-PROOF-MAPPING-01

- Statut initial: open.
- Severite: P3.
- Lot cible: Lot 7.
- Critere de cloture: matrice tests/proofs par domaine.
- Preuve minimale: classification live/fake/mock/covered_by_tests.

### P3-CEL-SECRET-LIKE-FIXTURES-01

- Statut initial: open.
- Severite: P3.
- Lot cible: Lot 7.
- Critere de cloture: allowlist fixtures ou remplacement par sentinelles
  clairement synthetiques.
- Preuve minimale: scan anti-fuite avec forbidden count stable.

### P3-CEL-OPEN-CHECKBOXES-ARCHIVES-01

- Statut initial: open.
- Severite: P3.
- Lot cible: Lot 8.
- Critere de cloture: conventions archives vs actifs clarifiees.
- Preuve minimale: scan checkboxes et index docs.

### P3-CEL-FINAL-LOCK-CONFLICT-TEST-01

- Statut initial: open.
- Severite: P3.
- Fichiers suspects: `app/core/chat_service.py`.
- Lot cible: Lot 7.
- Critere de cloture: test integration fake si Agenda et Biblio final locks
  apparaissent simultanement.
- Preuve minimale: test ordre de priorite ou decision explicite impossible.

### P3-CEL-BIBLIO-COMMENTS-STALE-01

- Statut initial: open.
- Severite: P3.
- Fichiers suspects: `app/config.py`, `app/biblio/librarian_agent_runtime.py`.
- Lot cible: Lot 8.
- Critere de cloture: commentaires/config alignes sur agent-first sans
  requalifier Biblio V1.
- Preuve minimale: diff docs/commentaires, tests non requis si commentaires.

### P3-CEL-AGENDA-DORMANT-WORDING-01

- Statut initial: needs_targeted_validation.
- Severite: P3.
- Fichier suspect: `app/docs/todo-todo/product/frida-agenda-agent.md`.
- Lot cible: Lot 8.
- Critere de cloture: confirmer qu'aucune phrase ne rouvre Agenda runtime, ou
  micro-correction docs-only.
- Preuve minimale: grep statut dormant/post-V1.

### P3-CEL-LOG-FRONTEND-DENYLIST-01

- Statut initial: open.
- Severite: P3.
- Fichier suspect: `app/web/log/log.js`.
- Lot cible: Lot 5 ou 7.
- Critere de cloture: UI `/log` utilise allowlist explicite ou test sentinelle
  champ inconnu.
- Preuve minimale: test frontend/log render.

### P3-CEL-FILENAMES-CONTENT-FREE-DECISION-01

- Statut initial: open.
- Severite: P3.
- Zones suspectes: dashboard/read-model documents.
- Lot cible: Lot 8.
- Critere de cloture: doctrine explicite sur filenames comme metadonnees
  produit visibles ou content-free limitees.
- Preuve minimale: spec/docs et test projection si changement runtime.

## Lots proposes

### Lot 0 - Baseline audit et registre

- [x] Creer l'audit baseline content-free.
- [x] Creer la TODO de remediation.
- [x] Classer P0/P1/P2/P3/POST-V1/INVALID.
- [x] Ne modifier ni runtime ni plateforme.

### Lot 1 - Securite plateforme P1 immediate

- [x] Traiter `P1-SAU-ENV-PERMISSIONS-01`.
- [x] Verifier ownership/mode `.env` et compat Compose.
- [x] Ne pas lire ni afficher les valeurs.
- [x] Produire preuve health apres correction si correction autorisee.

### Lot 2 - Secrets/env/logs/permissions

- [ ] Lot 2A: corriger les artefacts host-only `_codex_reports`,
  `_codex_backups` et `/opt/platform/backups` valides par Lot 1C, sans lire
  leur contenu.
- [ ] Lot 2B: corriger ou documenter les fichiers actifs/service-owned sous
  `/opt/platform/data/*` apres validation par service.
- [ ] Traiter backups/dumps/keys world-readable.
- [ ] Qualifier logs Authelia/Caddy secret-like.
- [ ] Traiter compose group-writable si confirme.
- [ ] Traiter la gouvernance permissions/retention au-dela des deux P1.
- [ ] Definir retention et mode cible.

### Lot 3 - Docker/Caddy/Authelia/reseaux

- [ ] Auditer socket proxy et consumers.
- [ ] Auditer Adminer lateral sur le grand reseau Docker.
- [ ] Valider/invalider Cockpit joignable depuis les ranges Docker.
- [ ] Qualifier healthchecks absents sur services critiques.
- [ ] Qualifier hardening conteneur `platform-fridadev`.
- [ ] Qualifier mounts RW Nextcloud du doc-pipeline.
- [ ] Auditer reseaux et frontieres public/interne.
- [ ] Verifier hostnames Caddy/Authelia sans exposer secrets.
- [ ] Valider pas de service public hors Caddy.

### Lot 4 - Code runtime P1/P2

- [ ] Qualifier appels HTTP et timeouts.
- [ ] Qualifier `requests.*` par client: timeout, fallback, retry.
- [ ] Chercher vrais dead paths ou NotImplemented runtime.
- [ ] Ne corriger que findings valides et bornes.

### Lot 5 - Admin/security/app routes

- [ ] Aligner tests admin sur contrat proxy/loopback.
- [ ] Verifier routes admin registerees par modules.
- [ ] Verifier admin HTML/public host vs API guard.
- [ ] Decider prompts complets dans DOM admin: exception operateur ou content gate.
- [ ] Traiter Notes UI gap: UI minimale ou API-only/post-V1 explicite.
- [ ] Traiter panels frontend qui rendent les erreurs comme listes vides.
- [ ] Traiter `/log` UI denylist si Lot 7 confirme le besoin.
- [ ] Garder Authelia comme frontiere publique.

### Lot 6 - Observabilite/logs applicatifs

- [ ] Qualifier `str(exc)`, raw, payload, traceback, print.
- [ ] Traiter erreurs LLM brutes.
- [ ] Traiter erreurs 400 admin brutes.
- [ ] Traiter dashboard web legacy URL/hash raw.
- [ ] Trancher doctrine hashes courts identity.
- [ ] Corriger seulement surfaces qui exposent ou masquent une panne.
- [ ] Conserver diagnostics content-free.

### Lot 7 - Tests/smokes/artefacts

- [ ] Construire matrice live/fake/mock/covered_by_tests.
- [ ] Ajouter test conflit final-lock Agenda/Biblio si confirme necessaire.
- [ ] Ajouter tests panels frontend erreur vs vide.
- [ ] Ajouter test `/log` champ inconnu si denylist conservee.
- [ ] Verifier JSONL et anti-fuite.
- [ ] Gerer fixtures secret-like par allowlist ou sentinelles.

### Lot 8 - Docs/source-of-truth

- [ ] Reclasser audits superseded encore en `todo-todo/audits`.
- [ ] Clarifier checkboxes historiques.
- [ ] Corriger `/opt/platform/AGENTS.md` admin token stale, sans runtime.
- [ ] Clarifier wording Agenda dormant si encore ambigu.
- [ ] Clarifier commentaires Biblio stale.
- [ ] Trancher doctrine filenames content-free/metadonnees produit.
- [ ] Mettre a jour index si chemins bougent.

### Lot 9 - Refactors cibles

- [ ] Prioriser `server.py` et gros modules.
- [ ] Prioriser `chat_service.py` orchestration seulement apres golden tests.
- [ ] Ecrire golden tests avant extraction.
- [ ] Refuser refactor cosmetique sans reduction de risque.

### Lot Z - Cloture mega-audit

- [ ] Tous P1/P2 fermes, invalides ou acceptes explicitement.
- [ ] P3 classes ou planifies post-audit.
- [ ] Artefact final content-free.
- [ ] TODO archivee dans `todo-done/audits`.

## Non-prolongation

- Pas de Mail runtime.
- Pas de reactivation Agenda.
- Pas de changement Capsule sauf P0/P1 explicite et GO operateur.
- Pas de reset/purge/backfill/migration.
- Pas de refactor opportuniste.
- Pas de modification plateforme hors lot Sauron explicitement autorise.

## Format de preuve attendu

- Toujours content-free.
- Chemins/metadonnees OK; contenu secret/log brut interdit.
- Logs: source, fenetre, line count, byte count, categories, forbidden count.
- Permissions: chemin, mode, owner numerique, taille, statut.
- Tests: commande, resultat, raison si non lance.
- Runtime: rebuild uniquement si code/config runtime change.
