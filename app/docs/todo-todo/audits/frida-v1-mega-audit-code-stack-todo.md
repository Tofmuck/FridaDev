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
- P1 plateforme local restant: backups/dumps/artefacts sensibles hors
  `.env.bak-*`, statut `risk_accepted_temporarily` par decision operateur.
- Lot 0.1: consolidation contre-audit executee; audit principal reconnu
  partiellement trop Sauron-heavy, findings Celebrimbor concrets integres.
- Doctrine Sauron courante: serveur solo derriere Caddy/Authelia; chercher
  d'abord les gros rouge public et les risques realistes, ne pas transformer le
  mega-audit en micro-hardening local infini a rendement decroissant.
- Lot 4A: audit/triage runtime P1/P2 execute; granularite Lot 4 jugee
  insuffisante pour patch runtime direct, mais suffisante pour isoler des lots
  corrigibles.
- Lot 4B: web/search fail-open cible corrige; panne SearXNG distinguee de
  `no_data` dans le payload/runtime event content-free.
- Lot 4D: audit fail-open runtime execute; correction bornee appliquee sur
  discovery web OpenRouter, autres candidats classes sans refactor large.
- Lot 4D.2: memory/identity/summary input fail-open valide puis corrige;
  les pannes de lecture atteignent les inputs primaires comme `error`.
- Post Lot 4D.2: les echecs larges observes hors correction ciblee sont
  traces comme findings ouverts, sans correction runtime ni reouverture 4D.2.
- Lot 5A: audit/triage admin/security/app routes execute docs-only; aucun
  patch runtime, corrections eventuelles decoupees en sous-lots 5B/5C/5D ou
  reportees Lot 6/7/9 selon surface.

## Doctrine securite plateforme avant audit code

Decision operateur du 2026-06-25: pour ce serveur solo, la cible realiste
principale est le bot opportuniste ou la faille publique d'un service expose.
La priorite Sauron avant de passer au code est donc:

1. absence de gros rouge public;
2. absence de service critique expose sans garde;
3. absence de bypass evident Authelia/Caddy/admin/DB/socket Docker;
4. etat des mises a jour serveur, services et images;
5. seulement ensuite, audit code applicatif, dette, structure et tests.

Consequence: les micro-durcissements locaux deja investigues restent visibles
dans le registre, mais ils ne bloquent pas le passage a Celebrimbor s'ils sont
`risk_accepted_temporarily`, `hygiene_deferred` ou optionnels et qu'aucun P0/P1
public ou update securite critique n'est detecte par les checkpoints Lot 3/3B.
Toute correction plateforme reelle reste un lot separe avec GO operateur,
backup/rollback et health checks.

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
  confirmes. Le wording Agenda est requalifie: runtime Agenda implemente,
  chantier/TODO large Agenda post-V1 dormant.

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

## Lot 1D - Investigation consommateurs backups/dumps/reports sensibles

Statut: investigation Sauron metadata/config-only executee le 2026-06-24.
Finding cible: `P1-SAU-SENSITIVE-BACKUPS-PERMS-01`.
Correction appliquee: non.
P1 ferme: non.

- [x] Cartographier les consommateurs Docker/Compose des familles sensibles.
- [x] Chercher les references statiques dans scripts, docs, runbooks et
  configs non sensibles, sans grepper les backups/dumps eux-memes.
- [x] Verifier crons/systemd par noms/compteurs, sans recopier de commande
  sensible.
- [x] Distinguer `confirmed_no_static_consumer`, `probable_operator_only`,
  `unknown_consumer`, `active_service_owned_do_not_touch` et
  `closed_by_lot_1b`.
- [x] Produire une table de decision sans appliquer de correction.

### Resultat Lot 1D

Question pre-action: existe-t-il un meilleur plan ? Non. Le plan le plus sur
est une cartographie metadata/config-only des consommateurs connus/probables,
avant tout chmod sur des artefacts dont le consommateur n'est pas certain.

- Docker mounts inspectes: aucune racine `_codex_reports`, `_codex_backups` ou
  `/opt/platform/backups` n'apparait comme mount actif des conteneurs courants.
- Racines actives montees confirmees: `/opt/platform/data/n8n`,
  `/opt/platform/data/stirling/configs`, `/opt/platform/data/nextcloud`,
  `/opt/platform/data/nextcloud-db`, `/opt/platform/doc-pipeline/data`,
  `/opt/platform/fridadev-db/imports`.
- References statiques: 300 fichiers non sensibles scannes; 45 contiennent des
  references de famille backup/restore/dump/archive. Les references sont
  principalement docs, runbooks, specs et TODO; aucun script de consommation
  automatique host-only n'a ete confirme pour `_codex_reports`,
  `_codex_backups` ou `/opt/platform/backups`.
- Cron/systemd: aucun cron ou timer applicatif custom consommateur de ces
  artefacts n'a ete confirme; seul un timer systeme `dpkg-db-backup` est
  observe et hors scope Frida/plateforme applicative.
- Crontab utilisateur: commande `crontab` absente dans l'environnement; root
  crontab via `sudo -n` n'a pas revele de consommateur backup applicatif dans
  les compteurs content-free.
- Historique shell: non utilise, risque de secret.

### Table decisionnelle Lot 1D

| path_or_family | classification | current_permissions_summary | docker_mount_consumer | compose_consumer | script_consumer | cron_systemd_consumer | docs_runbook_consumer | operator_only_likely | confidence | touch_decision | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/opt/platform/.env` et `.env.bak-*` | `closed_by_lot_1b` | `0640 root:tof`, world off | non | oui, deja traite | smoke M4 deja traite | non | oui | oui | `100_static_config` | `closed_by_lot_1b` | Finding `.env` clos; ne pas retraiter ici. |
| `/opt/platform/_codex_reports` | `confirmed_no_static_consumer` + `probable_operator_only` | 7 fichiers, environ 95 MB, 6 world-readable | non | non | non confirme | non confirme | oui, preuves/docs V1 | oui | high | `candidate_0640_root_tof_after_go` | Host-only; correction possible apres GO et scan avant/apres. |
| `/opt/platform/_codex_backups` | `probable_operator_only` | 11 fichiers sensibles matches, environ 915 MB, 10 world-readable | non | non | non confirme | non confirme | oui, runbooks/docs migration | oui | high | `candidate_0640_root_tof_after_go` | Backups/restauration host-only; conserver retention avant chmod. |
| `/opt/platform/backups` | `probable_operator_only` | 5 fichiers matches, environ 129 MB, 4 world-readable | non | non | non confirme | non confirme | oui, docs migration/archives | oui | high | `candidate_0640_root_tof_after_go` | Pas de consommateur runtime confirme; durcir apres GO. |
| `/opt/platform/fridadev-db/imports` | `active_service_owned_do_not_touch` | 2 dumps, deja `0600 tof:tof` | `platform-fridadev-postgres` -> `/imports` ro | oui, sous-stack DB | non | non | oui, migration | non | `100_static_config` | `do_not_touch_active_service` | Racine montee par Postgres; deja stricte. |
| `/opt/platform/fridadev-db/backups` | `confirmed_no_static_consumer` | 2 fichiers observes, deja `0600 tof:tof` | non | non | non confirme | non confirme | oui, migration | oui | medium | `candidate_0600_root_root_after_go` | Host-only et deja non world-readable; ownership a trancher separement. |
| `/opt/platform/fridadev-app/state-backup-*` | `confirmed_no_static_consumer` | archive observee `0600 tof:tof` | non | non | non confirme | non confirme | oui, migration | oui | medium | `candidate_0600_root_root_after_go` | Host-only; pas prioritaire car deja stricte. |
| `/opt/platform/data/n8n` | `active_service_owned_do_not_touch` | 8 fichiers sensibles matches, 3 world-readable | `platform-n8n` -> `/home/node/.n8n` rw | oui | non confirme | non confirme | historique/audit | non | `100_static_config` | `do_not_touch_active_service` | Donnees actives n8n; correction seulement avec validation service. |
| `/opt/platform/data/stirling/configs` | `active_service_owned_do_not_touch` | 8 fichiers matches, 8 world-readable | `platform-stirling-pdf` -> `/configs` rw | oui | non confirme | non confirme | non central | non | `100_static_config` | `do_not_touch_active_service` | Config active Stirling; cle JWT backup a valider dans lot dedie. |
| `/opt/platform/data/nextcloud*` | `active_service_owned_do_not_touch` | nombreux matches par noms/source, majoritairement service-owned | Nextcloud/DB/Cron mounts rw | oui | non confirme | non confirme | runbooks upgrade | non | `100_static_config` | `do_not_touch_active_service` | Donnees/source service actifs; ne pas corriger via P1 host-only. |
| `/opt/platform/doc-pipeline/data` | `active_service_owned_do_not_touch` | contenu partiellement non lisible, service DB monte | `platform-doc-pipeline-db` -> postgres data rw | oui | non confirme | non confirme | docs pipeline | non | high | `do_not_touch_active_service` | Racine service active; permission denied confirme prudence. |
| `/opt/platform/doc-library/index.html.backup` | `confirmed_no_static_consumer` | fichier HTML backup `0644 root:root` | `platform-doc-library` monte le dossier parent ro | compose parent oui | non | non | non confirme | uncertain | medium | `needs_targeted_validation` | Backup probablement non sensible mais dans dossier servi en lecture; ne pas classer P1 sans validation. |
| `/opt/platform/fridadev/app/admin/sql/runtime_settings_v1.sql` | `probably_safe_metadata_only` | fichier SQL repo, `0664 tof:tof` | non | non | non | non | source repo | non | high | `needs_targeted_validation` | Fichier source applicatif, pas dump runtime; hors correction Sauron immediate. |

### Synthese decisionnelle Lot 1D

- Nombre de lignes table: 13.
- `candidate_0640_root_tof_after_go`: 3 familles host-only prioritaires.
- `candidate_0600_root_root_after_go`: 2 familles host-only deja strictes
  mais ownership a trancher.
- `do_not_touch_unknown_consumer`: 0 famille majeure; les inconnues sont
  classees `needs_targeted_validation`.
- `do_not_touch_active_service`: 5 familles/racines montees.
- `needs_targeted_validation`: 2 lignes explicites.
- `closed_by_lot_1b`: 1 ligne.

Conclusion Lot 1D: ce qui est connu a 100% est la non-consommation Docker des
racines host-only `_codex_reports`, `_codex_backups` et `/opt/platform/backups`
dans les mounts courants, et la consommation active des racines sous
`/opt/platform/data/*`/`fridadev-db/imports`. Ce qui ne peut pas etre garanti
est l'absence de scripts humains externes, d'historique shell ou de runbooks
hors scan. Consequence operateur: ne corriger que les candidats host-only apres
GO explicite; ne pas toucher aux racines actives ou inconnues.

## Lot 1E - Decision operateur backups/dumps/reports sensibles

Statut: decision Sauron docs-only documentee le 2026-06-24.
Finding cible: `P1-SAU-SENSITIVE-BACKUPS-PERMS-01`.
Decision operateur: `NO-GO` correction permissions pour l'instant.
Correction appliquee: non.
P1 ferme comme corrige: non.
Statut retenu: `risk_accepted_temporarily`.

- [x] Documenter que Lot 1C/1D ont etabli les preuves statiques et metadata.
- [x] Documenter que les familles host-only ne sont pas montees par Docker
  courant et n'ont pas de consommateur statique confirme dans le scope scanne.
- [x] Documenter que l'absence absolue de consommateur hors repo/hors scan ne
  peut pas etre garantie.
- [x] Interdire chmod/chown/setfacl/purge/deplacement sans nouveau GO
  operateur explicite.
- [x] Garder `P1-SAU-SENSITIVE-BACKUPS-PERMS-01` visible et non ferme comme
  corrige.

### Decision Lot 1E

- Lots 1C/1D etablissent que `_codex_reports`, `_codex_backups` et
  `/opt/platform/backups` ne sont pas montes par Docker courant.
- Aucun consommateur statique n'a ete confirme dans Compose, scripts, cron,
  systemd, docs et runbooks scannes.
- L'absence absolue d'un consommateur hors repo, hors scan, usage humain non
  versionne ou historique shell ne peut pas etre garantie.
- Decision operateur: ne pas appliquer de `chmod`, `chown`, `setfacl`,
  purge ou deplacement pour l'instant.
- Ne pas lancer de correction host-only tant qu'il n'y a pas soit un
  consommateur confirme a 100%, soit un GO operateur explicite acceptant le
  risque de casser un usage externe non versionne.
- `P1-SAU-SENSITIVE-BACKUPS-PERMS-01` reste visible en
  `risk_accepted_temporarily`: risque reconnu, non corrige, non actionne.
- Prochain comportement: passer au finding suivant; ne pas relancer Lot 2A
  correctif sans nouvelle decision operateur explicite.

## Lot 2C - Investigation logs Authelia/Caddy secret-like

Statut: investigation Sauron count-only executee le 2026-06-24.
Finding cible: `P2-SAU-LOG-SECRETLIKE-01`.
Correction appliquee: non.
P2 ferme: non.

- [x] Detecter les conteneurs Caddy/Authelia.
- [x] Scanner `docker logs --since 24h --tail 5000` sans afficher de ligne
  brute.
- [x] Compter les familles `Authorization`, `Bearer`, `Basic`, cookies,
  token, secret, OAuth, JWT-like, DSN et URL avec query longue.
- [x] Inspecter les logs persistants par metadonnees seulement.
- [x] Inspecter les configs Caddy/Authelia par compteurs de mots-cles
  seulement, sans afficher de secret.
- [x] Documenter la classification sans corriger log-level/config.

### Resultat Lot 2C

Question pre-action: existe-t-il un meilleur plan ? Non. Le plan le plus sur
est le scan borne count-only des logs Docker et de la configuration de logging,
sans afficher de lignes ni modifier la plateforme.

- Conteneurs scannes: `platform-authelia`, `platform-caddy`.
- Fenetre: `since=24h`, `tail=5000`.
- Log drivers Docker: `json-file`, `max-size=10m`, `max-file=3` pour les deux
  conteneurs.
- Fichiers logs persistants detectes par metadonnees: pas de fichier log Caddy
  dedie sous `/opt/platform/caddy`; `/opt/platform/authelia/notification.txt`
  existe mais est vide; plusieurs logs d'autres services sont detectes sous des
  chemins `logs`, non scannes en contenu dans ce lot.
- Configs relues count-only: `/opt/platform/caddy/Caddyfile`,
  `/opt/platform/authelia/configuration.yml` via `sudo -n` et
  `/opt/platform/docker-compose.yml`; aucune ligne brute ni valeur affichee.

### Comptes Lot 2C

| surface | lines | bytes | confirmed_secret_value | credential_header_name_only | cookie_header_name_only | oauth_flow_metadata | false_positive_word_secret | needs_targeted_validation | conclusion |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `platform-caddy` | 287 | 88428 | 0 | 3 | 0 | 0 | 0 | 0 | Faux positif probable: noms de header `Authorization` sans valeur detectee. |
| `platform-authelia` | 2108 | 781859 | 6 JWT-like matches sur 3 lignes, plus URLs completes avec query | 0 | 0 | 4 | 2 | 1 | Partiel/confirme: pas de cookie/token/header classique, mais valeurs JWT-like et URLs avec query complete detectees. |

Details Authelia count-only:

- `url_query_match_count=2124`, `url_query_line_count=2091`.
- Principaux noms de query observes, sans valeurs: `rd`, `rm`, `p`, `v`,
  `rsd`, `rest_route`, `panel`.
- `sensitive_query_value_line_count=0` pour les familles `code`, `state`,
  `access_token`, `refresh_token`, `id_token`, `client_secret`, `token`.
- `jwt_like_match_count=6`, `jwt_like_line_count=3`; format de log Authelia
  non JSON dans cette fenetre, donc champ source non resolu sans extrait
  redige.
- `secret_word_count=2`, `secret_param_value_count=0`: classifie
  `false_positive_word_secret` dans ce lot.

Conclusion Lot 2C:

- `platform-caddy`: finding invalide pour cette fenetre; seulement des noms de
  header, aucune valeur credential detectee.
- `platform-authelia`: finding partiellement confirme. Les logs semblent
  contenir des URLs completes avec query `rd/rm` et quelques valeurs
  JWT-like; aucun cookie, `Authorization`, `Bearer`, `Basic`, DSN ou token
  parametre classique n'est detecte.
- Decision: ne pas fermer `P2-SAU-LOG-SECRETLIKE-01`; ouvrir un prochain lot
  de validation/correction Authelia pour comprendre la source des JWT-like et
  decider d'une redaction/log-level sans purger les logs.

## Lot 2D - Validation Authelia log secret-like

Statut: validation Sauron count-only/redacted-only executee le 2026-06-25.
Finding cible: `P2-SAU-LOG-SECRETLIKE-01`.
Correction appliquee: non.
Plateforme modifiee: non.
P2 ferme: non.
Classification: `partially_confirmed_non_sensitive`.

- [x] Identifier le format log Authelia sans afficher de ligne brute.
- [x] Requalifier les URLs avec query par noms de cles et dimensions, sans
  valeur.
- [x] Requalifier les matches JWT-like par dimensions et structure, sans
  afficher les chaines.
- [x] Lire la config logging Authelia/Compose sans afficher de secret.
- [x] Produire une decision avant toute correction.

### Resultat Lot 2D

Question pre-action: existe-t-il un meilleur plan ? Non. Le plan le plus sur
est une validation Authelia count-only/redacted-only, puis une decision
documentaire avant toute correction de configuration.

- Fenetre: `docker logs --since 24h --tail 5000 platform-authelia`.
- Format logs Authelia: texte/logfmt, non JSON dans la fenetre scannee.
- Champs logfmt detectes par nom seulement: `time`, `level`, `msg`, `method`,
  `path`, `remote_ip`, `rd`, `rm`, puis quelques cles fonctionnelles.
- Niveaux observes: majoritairement `info`, quelques `error`, un `warning`.
- Config logging Authelia: bloc `log` present, `level=info`, pas de format
  explicite detecte; Docker log driver `json-file` avec rotation `10m/3`.
- Source probable: flux access/redirect Authelia, avec champs fonctionnels
  `rd` et `rm`; marqueurs authentication/notification/session minoritaires.

### Validation URLs Lot 2D

- URLs avec query detectees: `2015` matches sur `1977` lignes.
- Cles de query top-level, sans valeurs: `rd`, `rm`, `p`, `v`, `rsd`,
  `rest_route`, `panel`, `t`.
- `rd`: `1977` valeurs URL-like; longueur min/max `28/140`; `38` valeurs
  contiennent une query imbriquee.
- Cles imbriquees dans `rd`, sans valeurs: `p`, `v`, `rsd`, `rest_route`,
  `panel`, `t`.
- Cles sensibles absentes dans top-level et imbrique: `code`, `state`,
  `access_token`, `refresh_token`, `id_token`, `client_secret`, `token`.
- Classification URLs: query fonctionnelle/potentiellement privacy-sensitive,
  mais aucune valeur credential/OAuth exploitable observee dans la fenetre.

### Validation JWT-like Lot 2D

- Matches JWT-like: `6` matches sur `3` lignes.
- Dimensions: longueur totale `33`, segments `(10, 10, 11)` pour les 6
  matches.
- Premier segment: base64url-decodable pour les 6, mais `0` objet JSON de
  header JWT; aucune cle de header JWT detectee.
- Contexte count-only: les 3 lignes contiennent aussi URL/query `rd`/`rm`.
- Classification JWT-like: faux positif structurel probable dans valeurs
  URL/redirect; pas un JWT valide selon la structure minimale observee.

Conclusion Lot 2D:

- Authelia ne montre pas de cookie, header credential, DSN, token classique,
  code/state OAuth ou JWT valide dans la fenetre scannee.
- Le signal secret-like Lot 2C est requalifie: JWT-like faux positif probable;
  URLs de redirection completes journalisees comme metadonnees fonctionnelles.
- Correction immediate non necessaire pour fuite de secret exploitable.
- Risque residuel: si une URL future contient une query sensible dans la cible
  `rd`, Authelia pourrait la journaliser. Cela releve d'une decision de
  politique logging/privacy, pas d'un secret confirme dans ce lot.
- Prochain comportement: ne pas modifier Authelia sans GO operateur; ouvrir un
  lot policy/redaction seulement si l'operateur decide que toute URL de
  redirection complete doit etre masquee.

## Lot 2F - Investigation permissions Compose/YAML

Statut: investigation Sauron metadata-only executee le 2026-06-25.
Finding cible: `P2-SAU-COMPOSE-PERMISSIONS-01`.
Correction appliquee: non.
Plateforme modifiee: non.
P2 ferme: non.
Classification: `partially_confirmed`.

- [x] Inventorier les fichiers Compose/YAML par metadonnees uniquement.
- [x] Classer les fichiers Compose actifs, historiques/quasi-actifs et YAML
  non Compose.
- [x] Valider `docker compose config --quiet` sur les stacks prioritaires sans
  afficher de configuration.
- [x] Chercher les scripts/docs qui referencent ou modifient les Compose sans
  afficher de secret.
- [x] Produire une decision avant tout chmod/chown.

### Resultat Lot 2F

Question pre-action: existe-t-il un meilleur plan ? Non. Le plan le plus sur
est une investigation metadata-only des Compose/YAML, en reservant Lot 2E pour
l'option Authelia deja ouverte et en utilisant Lot 2F pour eviter l'ambiguite,
puis une mise a jour docs-only sans chmod ni correction plateforme.

- Inventaire YAML/Compose borne hors `data`, `backups`, `_codex_backups`,
  `secrets`, `node_modules` et `models`: `19` fichiers.
- Fichiers world-writable detectes: `0`.
- Fichiers group-writable detectes: `3`.
- Compose actifs prioritaires valides par `docker compose config --quiet`:
  global, FridaDev app, FridaDev DB, Frida M4/RAG et doc-pipeline: OK.
- Repos Git detectes: seul `/opt/platform/fridadev` est un repo Git dans la
  profondeur scannee; les sous-stacks `/opt/platform/fridadev-app`,
  `/opt/platform/fridadev-db`, `/opt/platform/frida-m4-rag` et
  `/opt/platform/doc-pipeline` sont des stacks runtime host-side hors Git.
- Groupes concernes: `tof` et `debian`; aucun membre additionnel liste par
  `getent group`, mais les comptes `tof` et `debian` ont aussi acces Docker.

### Table decisionnelle Lot 2F

| Path/famille | Classification | Permissions | Validation | Decision |
| --- | --- | --- | --- | --- |
| `/opt/platform/fridadev-app/docker-compose.yml` | `confirmed_group_writable_runtime_compose` | `0664 tof:tof` | Compose app OK | `candidate_0644_after_go` |
| `/opt/platform/fridadev/docker-compose.yml` | `historical_or_quasi_active_compose` | `0664 tof:tof` | Compose repo KO: env local absent; `stack.sh` le reference | `candidate_0644_after_go` |
| `/opt/platform/homepage/kubernetes.yaml` | `yaml_not_runtime_compose` | `0664 debian:debian` | Non teste comme Compose | `candidate_0644_after_go` |
| Compose global/doc-pipeline/FridaDev DB/M4 | `confirmed_safe_readonly_compose` | `0644` ou `0640`, non group-writable | Compose OK | `no_change_needed` |
| Authelia/SearxNG YAML sensibles | `confirmed_safe_readonly_compose` / config sensible | `0600` ou `0640 root:root` | Metadata seulement | `no_change_needed` |
| Homepage YAML non group-writable | `yaml_not_runtime_compose` | `0644`, non group-writable | Metadata seulement | `no_change_needed` |

### Decision Lot 2F

- Finding confirme partiellement: le risque initial existe bien pour un Compose
  runtime actif (`fridadev-app`) et pour un Compose repo/quasi-actif
  (`fridadev`), mais pas pour les autres Compose prioritaires.
- Aucun fichier Compose/YAML scanne n'est world-writable.
- Aucun script modificateur `chmod/chown compose` n'a ete detecte dans les
  chemins scannes; `stack.sh` reference seulement le Compose repo local.
- Correction recommandee, sans application dans ce lot: passer les fichiers
  group-writable candidats en `0644` apres GO operateur, avec `stat` avant/apres
  et `docker compose config --quiet` pour `fridadev-app`; ne pas corriger
  `fridadev` sans decider s'il reste un compose local supporte ou historique.
- Correction non urgente: le groupe `tof` semble mono-utilisateur, donc le
  risque principal est le durcissement d'hygiene et la reduction du drift, pas
  une exposition world-write immediate.

## Lot 2G - Recadrage securite plateforme realiste avant audit code

Statut: recadrage Sauron docs-only execute le 2026-06-25.
Decision operateur: ne pas poursuivre les micro-durcissements locaux a
rendement decroissant avant d'avoir verifie les gros rouge publics et les
mises a jour critiques.
Correction appliquee: non.
Plateforme modifiee: non.

- [x] Inscrire la doctrine serveur solo derriere Caddy/Authelia.
- [x] Reclasser les micro-hardening locaux Lot 2 comme acceptes
  temporairement, differes ou optionnels.
- [x] Redefinir Lot 3 comme checkpoint securite plateforme realiste avant audit
  code.
- [x] Ajouter Lot 3B inventaire mises a jour serveur/services/images.
- [x] Ne fermer aucun finding comme corrige par ce recadrage.

### Decision Lot 2G

- `P1-SAU-SENSITIVE-BACKUPS-PERMS-01`: conserver
  `risk_accepted_temporarily`; ne pas relancer de correctif permissions sans
  nouveau GO operateur explicite.
- `P2-SAU-LOG-SECRETLIKE-01`: Caddy reste faux positif probable; Authelia est
  requalifie `partially_confirmed_non_sensitive`; Lot 2E policy URLs de
  redirection reste optionnel et non bloquant.
- `P2-SAU-COMPOSE-PERMISSIONS-01`: reclasser en `hygiene_deferred`; correction
  possible apres GO, mais non bloquante pour un serveur solo sauf nouveau gros
  rouge public.
- Lot 2 devient un gel/registre des micro-hardening locaux: garder les risques
  visibles, mais ne pas les traiter comme no-go avant l'audit code si Lot 3 et
  Lot 3B ne trouvent pas de P0/P1 public ou update critique.
- Transition: si Lot 3/3B ne remonte pas de gros rouge public, de bypass
  evident ou d'update securite critique urgente, la partie securite plateforme
  est suffisante pour serveur solo et le mega-audit passe au code applicatif.

## Lot 3 - Checkpoint securite plateforme realiste avant audit code

Statut: audit Sauron metadata/headers-only execute le 2026-06-25.
Correction appliquee: non.
Plateforme modifiee: non.
Runtime modifie: non.
Classification globale: aucun P0/P1 public confirme; securite plateforme
suffisante pour serveur solo sous reserve du Lot 3B updates.

- [x] Inventorier ports publics et services exposes sans afficher secrets.
- [x] Verifier Caddy/Authelia comme frontiere publique des services sensibles.
- [x] Verifier absence de service critique expose sans garde.
- [x] Verifier absence de bypass evident Authelia/Caddy/admin/DB depuis
  Internet.
- [x] Verifier admin Frida, Adminer et DB: pas d'exposition publique directe
  hors garde attendue.
- [x] Verifier Docker socket/proxy a haut niveau: pas d'exposition publique ni
  consommateur evident hors besoin documente.
- [x] Verifier Cockpit a haut niveau: pas de surface publique directe
  inattendue; route Caddy a valider separement si besoin.
- [x] Verifier frontieres Docker raisonnables a haut niveau; ne pas lancer de
  micro-hardening reseau si aucun gros rouge public.
- [x] Verifier health generale des services critiques sans restart/rebuild.
- [x] Si aucun P0/P1 public n'apparait, considerer la securite plateforme
  suffisante pour serveur solo et passer au Lot 3B updates.

### Resultat Lot 3

Question pre-action: existe-t-il un meilleur plan ? Non. Le plan le plus sur
est le checkpoint read-only des surfaces publiques et des gros rouges, puis une
mise a jour docs-only avant Lot 3B.

- Ports host: UFW actif, default deny incoming. Regles publiques attendues:
  `80/tcp`, `443/tcp` et `22/tcp`. `9090/tcp` est autorise seulement depuis
  des plages Docker/Caddy documentees; pas d'ouverture Internet directe
  observee. `5355/tcp+udp` ecoute via `systemd-resolve`, mais aucune regle UFW
  publique explicite n'a ete observee.
- Ports Docker publies: seul `platform-caddy` publie `80/tcp` et `443/tcp`
  vers le host. Aucun port Docker public pour FridaDev, Adminer, Postgres,
  Authelia ou docker-socket-proxy.
- Hostnames testes par HEAD public, cookies redacted: `fridadev.frida-system.fr`
  `/admin` -> redirect protege; `fridadev-db.frida-system.fr` -> redirect
  protege; `home.frida-system.fr`, `cloud.frida-system.fr` et
  `cloud.137-74-204-229.sslip.io` -> redirect protege; racines
  `frida-system.fr` et `www.frida-system.fr` -> redirect simple attendu.
- Caddy/Authelia: Caddy reste la frontiere publique principale. Les surfaces
  sensibles testees repondent par redirection/challenge attendu, sans 200
  public direct observe dans ce lot.
- Admin Frida: pas de port Docker publie; surface publique `/admin` redirige
  vers la garde Caddy/Authelia.
- Adminer: pas de port Docker publie; hostname DB public redirige vers la
  garde Caddy/Authelia. Le risque lateral Docker reste un P2 interne separe.
- DB FridaDev: Postgres expose seulement un port conteneur interne sur le
  reseau DB; aucun port host publie observe.
- Docker socket/proxy: `platform-docker-socket-proxy` n'a aucun port publie et
  reste sur `platform_proxy_net` dans l'etat inspecte; pas d'exposition
  publique observee.
- Cockpit: service host actif sur `*:9090`, UFW limite l'ingress a des plages
  Docker/Caddy. Caddy contient une route `{$COCKPIT_HOST}` vers
  `https://172.20.0.1:9090`. Aucun bypass public direct n'est confirme, mais
  le couple hostname Caddy/Cockpit reste `needs_targeted_validation` si
  l'operateur veut prouver la garde de cette surface.
- Docker/reseaux: Caddy est sur les reseaux platform/crawl/M4; Authelia sur
  auth/platform; Adminer sur platform + db; Postgres FridaDev sur db; socket
  proxy sur proxy. Aucun maillage public critique inattendu n'a ete confirme.
- Health: aucun conteneur `unhealthy`, `restarting` ou `exited` observe via
  `docker ps -a`. Plusieurs services restent `Up` sans healthcheck explicite;
  `P2-SAU-HEALTHCHECKS-ABSENT-01` reste donc visible comme hygiene/service
  observability, pas comme rouge public.

### Decision Lot 3

- P0 public: aucun confirme.
- P1 public: aucun confirme.
- P2 internes/hygiene maintenus: Cockpit/Caddy `needs_targeted_validation`,
  Adminer lateral, docker socket proxy governance, healthchecks absents,
  Compose/YAML hygiene, backups sensibles `risk_accepted_temporarily`,
  `5355` host listener derriere UFW default deny.
- Lot 3 suffisant pour serveur solo: oui, sous reserve du Lot 3B inventaire
  mises a jour serveur/services/images.
- Prochain lot recommande: Lot 3B updates inventory, audit-only, aucune update
  sans lot dedie backup/rollback/health.

## Lot 3B - Inventaire mises a jour serveur/services/images

Statut: audit Sauron inventory-only execute le 2026-06-25.
Updates appliquees: non.
Pulls Docker effectues: non.
Plateforme modifiee: non.
Runtime modifie: non.
Classification globale: aucune update securite critique urgente confirmee;
passage a l'audit code autorise.

- [x] Inventorier OS / paquets systeme sans appliquer de mise a jour.
- [x] Inventorier Docker / Docker Compose.
- [x] Inventorier images Docker des services, sans `pull`.
- [x] Inventorier Caddy.
- [x] Inventorier Authelia.
- [x] Inventorier Nextcloud.
- [x] Inventorier Postgres/Redis.
- [x] Inventorier n8n.
- [x] Inventorier SearxNG.
- [x] Inventorier Adminer.
- [x] Inventorier FridaDev app/db.
- [x] Inventorier autres services exposes ou critiques.
- [x] Classer chaque element: `update_critique_securite`,
  `update_recommandee`, `update_postposable`, `no_action`,
  `needs_operator_decision`, `needs_targeted_validation`,
  `unknown_no_network_check`.
- [x] Si update critique securite urgente: ouvrir un lot separe avec
  backup/rollback/health; sinon passer a l'audit code.

### Resultat Lot 3B

Question pre-action: existe-t-il un meilleur plan ? Non. Le plan le plus sur
est un inventaire read-only sans `apt update`, sans pull registry et sans
restart, puis une decision documentaire sur le blocage ou non de l'audit code.

- OS/host: Debian GNU/Linux 13 `trixie`; kernel courant
  `6.12.90+deb13.1-amd64`.
- Updates systeme: `apt list --upgradable` ne remonte aucun paquet dans le
  cache courant. `apt-check` update-notifier absent sur cet hote Debian.
- Reboot: `/var/run/reboot-required` present; paquet indique:
  `linux-image-6.12.94+deb13-amd64`. Un reboot planifie est recommande pour
  activer le kernel installe plus recent, mais ce n'est pas une update a
  appliquer dans Lot 3B.
- Docker: Docker `26.1.5+dfsg1`; Docker Compose `2.26.1-4`; daemon sur Debian
  13 avec kernel courant `6.12.90+deb13.1-amd64`.
- Conteneurs/images: 30 conteneurs actifs, 27 images actives uniques,
  860 lignes d'images locales dont 820 dangling rows. Les dangling images sont
  un sujet hygiene/retention postposable; aucune purge dans ce lot.
- Caddy: image `caddy:2.11.3`, binaire `2.11.3`, no action immediate observee.
- Authelia: image `authelia/authelia:4.39.19`, binaire `4.39.19`, conteneur
  healthy, no action immediate observee.
- Nextcloud: image `nextcloud:33-apache`; `occ status` read-only:
  `version=33.0.5`, maintenance off, `needsDbUpgrade=false`, no action
  immediate observee.
- FridaDev: image locale `platform-fridadev-app:local`, creee le 2026-06-24;
  conteneur healthy; Python runtime `3.11.15`; HEAD repo
  `f53bae668fbbad146c2a07ecf2cd072ac9696bdb`.
- FridaDev DB: `pgvector/pgvector:pg17`, PostgreSQL `17.9`, healthy.
- Doc-pipeline DB: `postgres:16-alpine`, PostgreSQL `16.12`, healthy.
- Nextcloud DB: `mariadb:11`, MariaDB `11.8.6`.
- Redis/Valkey: `redis:7-alpine` -> Redis `7.4.7`; `valkey:8-alpine` ->
  Valkey `8.1.6`.
- n8n: image `n8nio/n8n`, runtime version `2.9.4`; floating image tag, donc
  freshness registry non prouvee sans pull.
- SearxNG: image `ghcr.io/searxng/searxng:2026.3.3-b5c1c2804`; version runtime
  non recuperee par commande simple dans ce lot, mais tag date explicite.
- Adminer: image `adminer:latest`, PHP runtime `8.4.19`; version applicative
  precise non prouvee sans inspection plus ciblee/pull.
- Autres services critiques/exposes: `homepage:v1.13.1`, `crawl4ai:0.8.5`,
  `text-embeddings-inference:cpu-latest`, `stirling-pdf`, `trilium:latest`,
  `docker-socket-proxy`, images locales M4/doc-pipeline/whisper. Pas de signal
  local d'urgence securite; freshness registry non prouvee pour les tags
  flottants ou images locales.

### Classification Lot 3B

- `update_critique_securite`: aucun element confirme.
- `update_recommandee`: reboot planifie pour activer le kernel installe
  `6.12.94+deb13-amd64`; a faire dans un lot operateur separe avec fenetre,
  health pre/post et rollback operatoire si necessaire.
- `update_postposable`: hygiene des images Docker dangling; revue des tags
  flottants `latest`/sans tag; eventuel refresh images apres backup/rollback.
- `no_action`: Caddy, Authelia, Nextcloud status, FridaDev app/db,
  Postgres/Redis/MariaDB/Valkey selon les signaux locaux disponibles.
- `needs_operator_decision`: calendrier reboot kernel; politique de tags
  flottants vs pinning; eventuel nettoyage images dangling.
- `needs_targeted_validation`: version applicative Adminer precise; version
  runtime SearxNG; services `trilium`, `stirling-pdf`, `anythingllm`,
  `text-embeddings-inference` et images locales sans registry freshness.
- `unknown_no_network_check`: toutes les images avec tag flottant ou sans pull
  registry (`adminer:latest`, `n8nio/n8n`, `tecnativa/docker-socket-proxy`,
  `stirlingtools/stirling-pdf`, `zadam/trilium:latest`,
  `ghcr.io/huggingface/text-embeddings-inference:cpu-latest`, images locales
  FridaDev/M4/doc-pipeline/whisper, `nginx` sans tag explicite).

### Decision Lot 3B

- Update critique securite urgente: non confirmee.
- Blocage avant audit code: non.
- Prochain lot recommande: passer a l'audit code Celebrimbor. Programmer plus
  tard un lot Sauron separe pour reboot kernel et, si l'operateur le souhaite,
  un inventaire/pinning des images flottantes avec registry check, pull controle,
  backup/rollback et health.

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
- Statut courant: `risk_accepted_temporarily` par decision operateur Lot 1E;
  risque reconnu, correction permissions `NO-GO` pour l'instant, P1 non ferme
  comme corrige.
- Severite: P1.
- Fichiers/zones suspects: `/opt/platform/backups`,
  `/opt/platform/_codex_backups`, `/opt/platform/_codex_reports`,
  `/opt/platform/data/*`, dumps DB, archives, keys.
- Lot cible: Lot 2.
- Investigation Lot 1C: valide. Le risque est confirme sur des dumps DB,
  archives historiques, rapports Codex et quelques fichiers actifs ou
  service-owned; les familles `.env` racine sont exclues car closes par Lot 1B.
- Investigation Lot 1D: consommateurs cartographies. Les familles host-only
  `_codex_reports`, `_codex_backups` et `/opt/platform/backups` n'ont pas de
  consommateur Docker/cron/systemd/script confirme et deviennent candidates a
  durcissement apres GO; les racines montees restent `do_not_touch_active_service`.
- Decision Lot 1E: `NO-GO` correction permissions pour l'instant car
  l'absence absolue d'un consommateur hors repo/hors scan ne peut pas etre
  garantie. Ne pas relancer de correction host-only sans nouveau GO operateur
  explicite.
- Recadrage Lot 2G: risque local reconnu mais accepte temporairement pour un
  serveur solo; ne bloque pas le passage a l'audit code sauf nouveau signal de
  fuite publique, backup expose, ou GO operateur de correction.
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
- Statut courant: `invalid_as_secret_exposure_by_lot_2D`. Caddy est un faux
  positif probable; Authelia ne montre pas de secret exploitable dans la
  fenetre scannee. Les URLs de redirection completes restent une option de
  politique privacy, pas un finding P2 secret confirme.
- Severite: P2.
- Zones suspectes: logs recents Authelia/Caddy.
- Lot cible: Lot 2.
- Investigation Lot 2C: `platform-caddy` ne montre que 3 noms de header
  `Authorization` sans valeur sur 24h/287 lignes; `platform-authelia` montre
  2108 lignes / 781859 bytes, 2124 URLs avec query, 6 matches JWT-like sur 3
  lignes, 0 cookie/token/header credential classique.
- Validation Lot 2D: format texte/logfmt, `level=info`, flux access/redirect.
  Les JWT-like sont de longueur 33 avec segments `(10,10,11)` et `0` header
  JWT JSON; requalifies faux positifs probables. Les URLs `rd/rm` ne contiennent
  pas de cles sensibles observees (`code/state/token/...` absents), mais sont
  des URLs de redirection completes.
- Prochain lot: uniquement sur GO operateur si la politique decide de masquer
  les URLs de redirection completes; pas de purge/reload/correction implicite.
- Recadrage Lot 2G: Lot 2E reste optionnel; ce finding ne bloque pas le
  passage a l'audit code tant qu'aucune valeur exploitable ou fuite publique
  n'est confirmee.
- Critere de cloture: faux positif documente ou redaction/log-level corrige.
- Preuve minimale: scan borne sans lignes brutes, counts avant/apres.
- Hors-scope: purge logs globale.

### P2-SAU-DOCKER-SOCKET-SURFACE-01

- Statut initial: open.
- Statut courant: `accepted_explicitly_by_operator_decision_2026_06_25`;
  aucune exposition publique confirmee par Lot 3, limite interne conservee et
  reouvrable sur nouveau consommateur, nouvelle exposition ou decision Sauron.
- Severite: P2.
- Zones suspectes: `platform-docker-socket-proxy`, `platform_proxy_net`,
  compose global, service status avec socket direct selon contre-audit.
- Alias/fusion: confirme et amplifie par `P2-SAU-DOCKER-SOCKET-SURFACE-01`
  contre-audit.
- Lot cible: Lot 3.
- Checkpoint Lot 3: aucun port publie; conteneur observe sur
  `platform_proxy_net`; pas de surface publique directe observee.
- Critere de cloture: matrice consumers/endpoints/reseaux.
- Preuve minimale: `docker inspect` content-free, compose metadata,
  eventuellement test consumer.
- Hors-scope: couper socket proxy sans connaitre dependances.

### P2-SAU-ADMINER-LATERAL-01

- Statut initial: open.
- Statut courant: `accepted_explicitly_by_operator_decision_2026_06_25`;
  aucune exposition publique confirmee par Lot 3, risque lateral interne
  conserve comme limite du serveur solo.
- Severite: P2.
- Zones suspectes: `platform-frida-adminer`, `platform_platform_net`,
  `fridadev-db.frida-system.fr`.
- Lot cible: Lot 3.
- Checkpoint Lot 3: aucun port host/Docker publie pour Adminer; hostname public
  DB redirige vers la garde Caddy/Authelia; risque lateral interne non ferme.
- Critere de cloture: Adminer non joignable lateralement depuis le grand reseau
  Docker, ou exception documentee avec justification.
- Preuve minimale: test lateral content-free depuis un conteneur pair, headers
  publics Authelia sans cookie, `docker inspect` reseaux.
- Hors-scope: suppression Adminer ou changement DB sans GO operateur.

### P2-SAU-COCKPIT-DOCKER-REACHABILITY-01

- Statut initial: needs_targeted_validation.
- Statut courant: `accepted_explicitly_by_operator_decision_2026_06_25`;
  aucune exposition Internet directe confirmee par Lot 3; la validation ciblee
  Caddy/Cockpit reste un declencheur de reouverture, pas un P2 bloquant.
- Severite: P2.
- Zones suspectes: Cockpit host port, UFW, ranges Docker.
- Lot cible: Lot 3.
- Checkpoint Lot 3: Cockpit actif sur `*:9090`; UFW autorise `9090/tcp`
  seulement depuis des plages Docker/Caddy; Caddy contient
  `{$COCKPIT_HOST}` -> `https://172.20.0.1:9090`; aucun login ni contenu
  Cockpit teste.
- Critere de cloture: confirmer ou invalider la reachability Cockpit depuis
  conteneurs; restreindre ou documenter si confirme.
- Preuve minimale: test reseau borne sans credentials, inventaire UFW
  content-free, aucune auth Cockpit tentee.
- Hors-scope: modification firewall sans plan Sauron.

### P2-SAU-HEALTHCHECKS-ABSENT-01

- Statut initial: open.
- Statut courant: `accepted_explicitly_by_operator_decision_2026_06_25` comme
  limite d'hygiene/observabilite service; aucun conteneur unhealthy ou en
  restart observe par Lot 3.
- Severite: P2.
- Zones suspectes: Caddy, Nextcloud, Nextcloud DB/Redis/Cron, n8n, SearxNG,
  Adminer, doc-pipeline, socket proxy.
- Lot cible: Lot 3.
- Checkpoint Lot 3: aucun conteneur `unhealthy`, `restarting` ou `exited`;
  plusieurs services critiques restent sans healthcheck explicite.
- Critere de cloture: healthcheck ajoute ou absence justifiee service par
  service.
- Preuve minimale: `docker inspect` health status, compose metadata, tests
  service bornes.
- Hors-scope: restart large ou healthcheck qui mute les donnees.

### P2-SAU-FRIDADEV-CONTAINER-HARDENING-01

- Statut initial: open.
- Statut courant: `accepted_explicitly_by_operator_decision_2026_06_25` comme
  limite de hardening interne du serveur solo; tout changement user/rootfs/
  privileges exige un lot Sauron distinct avec rollback.
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
- Statut courant: `accepted_explicitly_by_operator_decision_2026_06_25` comme
  limite interne des services actifs; aucune reduction de mount sans lot
  Sauron et preuve fonctionnelle doc-pipeline.
- Severite: P2.
- Zones suspectes: `doc-pipeline`, `doc-pipeline-api`, mounts data Nextcloud.
- Lot cible: Lot 3.
- Critere de cloture: montages RW confirmes necessaires ou reduits/RO.
- Preuve minimale: `docker inspect` mounts content-free, test fonctionnel
  doc-pipeline si modification autorisee.
- Hors-scope: lecture contenu Nextcloud ou modification fichiers utilisateur.

### P2-SAU-COMPOSE-PERMISSIONS-01

- Statut initial: open.
- Statut courant: `accepted_explicitly_by_operator_decision_2026_06_25`;
  risque partiellement confirme par Lot 2F et classe `hygiene_deferred` par
  Lot 2G, sans correction implicite.
- Severite: P2.
- Zones suspectes: Compose FridaDev group-writable.
- Lot cible: Lot 2 ou 3.
- Investigation Lot 2F: `19` YAML/Compose inventories hors zones exclues,
  `0` world-writable, `3` group-writable. Compose runtime actif confirme:
  `/opt/platform/fridadev-app/docker-compose.yml` en `0664 tof:tof`, compose
  config OK. Compose repo/quasi-actif:
  `/opt/platform/fridadev/docker-compose.yml` en `0664 tof:tof`, reference par
  `stack.sh`, mais `docker compose config --quiet` echoue dans l'etat observe
  sur env local absent. YAML non Compose group-writable:
  `/opt/platform/homepage/kubernetes.yaml` en `0664 debian:debian`.
- Correction proposee: `candidate_0644_after_go` pour les fichiers
  group-writable confirmes, avec validation compose ciblee; ne pas appliquer
  sans GO operateur.
- Recadrage Lot 2G: hygiene locale differable pour serveur solo; ne pas
  corriger maintenant sauf si Lot 3 montre un gros rouge public ou si
  l'operateur donne un GO dedie.
- Critere de cloture: modes/ownership explicites et verifies.
- Preuve minimale: `stat`, `docker compose config --quiet`.
- Hors-scope: changement runtime.

### P2-SAU-PERMISSIONS-GOVERNANCE-01

- Statut initial: open.
- Statut courant: `accepted_explicitly_by_operator_decision_2026_06_25` comme
  dette locale de gouvernance/retention; le risque P1 backup correspondant
  reste accepte temporairement et toute mutation exige un GO Sauron distinct.
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
- Statut courant: closed_by_lot_8_docs_source_of_truth.
- Severite: P2.
- Zones suspectes: `/opt/platform/AGENTS.md` vs
  `/opt/platform/fridadev/AGENTS.md`.
- Lot cible: Lot 8.
- Correctif Lot 8: `/opt/platform/AGENTS.md` aligne la doctrine Sauron sur
  Authelia/Caddy comme frontiere publique, `/api/admin/*` accepte uniquement
  proxy de confiance avec `Remote-User` ou loopback conteneur, et
  `FRIDA_ADMIN_TOKEN`/knobs legacy ne sont plus presentes comme garde humaine
  ni knobs operateur actifs. Modification faite hors depot FridaDev.
- Critere de cloture: instructions Sauron alignees avec contrat OVH courant:
  Authelia + proxy `Remote-User`/loopback, pas de token humain.
- Preuve minimale: diff docs-only, grep `FRIDA_ADMIN_TOKEN` contextualise.
- Hors-scope: changer runtime ou `.env`.

### P2-CEL-ADMIN-COMPAT-KNOBS-01

- Statut initial: open.
- Statut courant: closed_by_lot_5D_admin_guard_contract.
- Severite: P2.
- Fichiers suspects: tests admin mentionnant `FRIDA_ADMIN_TOKEN` /
  `FRIDA_ADMIN_LAN_ONLY`, `app/server.py`.
- Lot cible: Lot 5.
- Audit Lot 5A: `app/server.py` garde `/api/admin/*` via loopback conteneur ou
  proxy de confiance Caddy/Authelia avec identite `Remote-User`; le code source
  du guard ne rebranche pas `FRIDA_ADMIN_TOKEN`, `FRIDA_ADMIN_LAN_ONLY`,
  `FRIDA_ADMIN_ALLOWED_CIDRS` ni `X-Admin-Token`.
- Preuve Lot 5A: introspection Flask conteneur: 122 routes, toutes les routes
  admin API observees sont sous `/api/admin/*`; `/api/tools/image-generation`
  est une surface outil sensible guardee separement par `_GUARDED_TOOLS_PATHS`.
- Reste ouvert: quelques suites de tests/config mentionnent encore les knobs
  obsoletes comme fixtures/compat; besoin d'un sous-lot de nettoyage tests/docs
  pour eviter toute ambiguite future, sans reintroduire de token humain.
- Correctif Lot 5D: `.env.example` ne presente plus `FRIDA_ADMIN_TOKEN`,
  `FRIDA_ADMIN_LAN_ONLY` ni `FRIDA_ADMIN_ALLOWED_CIDRS` comme variables
  configurables. `config.py` conserve seulement les constantes legacy
  non env-backed pour compat tests/imports. Les tests prouvent le contrat OVH:
  loopback accepte, proxy de confiance + `Remote-User` accepte, appel direct
  non-proxy refuse, appel lateral avec `Remote-User` forge refuse, et
  `X-Admin-Token`/`FRIDA_ADMIN_TOKEN` seul ne donne aucun acces humain.
- Critere de cloture: tests admin alignes sur loopback/proxy `Remote-User`,
  knobs obsoletes marques compat si conserves.
- Preuve minimale: tests admin conteneur, refus lateral direct.
- Hors-scope: reintroduire token humain.

### P2-CEL-ADMIN-PROMPTS-DOM-01

- Statut initial: open.
- Statut courant: closed_by_lot_5B_1_content_gate.
- Severite: P2.
- Fichiers suspects: `app/admin/runtime_settings_api_view.py`,
  `app/web/admin_section_main_model.js`, `app/web/admin_ui_common.js`,
  `app/web/admin.html`, tests admin.
- Lot cible: Lot 5 ou 6.
- Audit Lot 5A: valide. `runtime_settings_api_view.py` expose des prompts
  complets dans `readonly_info.*.system_prompt.value` et champs equivalents;
  `admin_section_main_model.js` et `admin_ui_common.js` les rendent dans des
  blocs readonly/textarea cote admin.
- Decision Lot 5B.1: option content gate. Le JSON/DOM admin initial expose
  seulement des metadonnees content-free (`present`, `char_count`,
  `line_count`, `path`, `loader`, `reason_code`, endpoint gate) et ne contient
  plus les prompts complets.
- Critere de cloture: endpoint de lecture brute separe en `POST` avec
  acquittement explicite `content_gate_acknowledged`; sans acquittement, refus
  `admin_prompt_content_gate_ack_required`; aucune republication brute dans
  `readonly_info` standard.
- Preuve minimale: tests admin DOM/JSON, content gate explicite, scan
  content-free.
- Hors-scope: modifier prompts.

### P2-CEL-LLM-ERROR-RAW-01

- Statut courant: closed_by_lot_6B.
- Severite: P2.
- Fichiers suspects: `app/core/chat_llm_flow.py`, `app/admin/admin_logs.py`.
- Lot cible: Lot 6B.
- Preuve Lot 6A: le scan cible confirme encore des surfaces LLM avec
  `str(exc)` ou equivalent dans les reponses/logs applicatifs, notamment autour
  du flow LLM et du proxy LLM serveur.
- Correction Lot 6B: `chat_llm_flow.py` et les relais LLM de `server.py`
  exposent des erreurs LLM via `error_code`, `reason_code`, `error_class` et
  messages visibles stables; les exceptions provider/secret/finalize ne sont
  plus recopiees en clair dans la reponse, les events `llm_*` ni le
  `message_short` du turn logger.
- Preuve Lot 6B: tests sentinelles avec URL/query, header auth synthetique,
  path synthetique et payload provider sentinelle; la sentinelle ne sort
  ni dans la reponse ni dans les events cibles.
- Critere de cloture: erreurs LLM exposees via `error_code`/`error_class` et
  message utilisateur stable, sans `str(exc)` brut.
- Preuve minimale: tests sentinelles URL/token/path/provider error, logs
  content-free.
- Hors-scope: changer provider/model.

### P2-CEL-DASHBOARD-WEB-LEGACY-RAW-01

- Statut courant: closed_by_lot_6D.
- Severite: P2.
- Fichiers suspects: `app/observability/turn_pipeline_read_model.py`,
  dashboard read-model.
- Lot cible: Lot 6D.
- Preuve Lot 6A: les motifs `raw`, `url`, `hash` restent melanges entre champs
  defensifs, schema guard et projections dashboard; aucune correction mecanique
  n'est sure sans fixture historique sentinelle.
- Preuve Lot 6D: `_web_summary()` projetait encore `url`,
  `query_sha256_12`, `crawl4ai_query_sha256_12` et
  `crawl_query_sha256_12` dans le fact dashboard Web. Le correctif garde
  uniquement presence, longueurs, compteurs et statuts content-free; le test
  sentinelle dashboard prouve qu'une URL/query/hash synthetiques sensibles ne
  ressortent pas dans le fact.
- Critere de cloture: legacy web facts projetes sans URL brute ni hash stable
  sensible non justifie.
- Preuve minimale: event historique sentinelle, dashboard JSON content-free.
- Hors-scope: purge historique.

### P2-CEL-IDENTITY-HASH-POLICY-01

- Statut courant: closed_by_lot_6E_1.
- Severite: P2.
- Fichiers suspects: `app/observability/identity_observability.py`,
  projection pipeline identity.
- Lot cible: Lot 6E.
- Preuve Lot 6A: policy gap confirme sur les hashes courts identity; aucun
  patch runtime avant doctrine explicite sur suppression, HMAC/salt ou
  exception justifiee.
- Decision Lot 6E: doctrine tranchee. Les surfaces observabilite/admin identity
  ne doivent plus exposer de hash court stable derive de texte identity,
  mutable, proposition ou reason/update_reason. Les diagnostics retenus sont
  presence, longueurs, compteurs, statuts/reason codes et IDs opaques non
  derives du texte.
- Correction Lot 6E: suppression des hashes courts identity dans le writer
  `identity_prompt_injection`, la projection dashboard identity, les outcomes
  mutable identity, les projections admin identity legacy et les annotations
  textuelles libres du juge mutable. Les colonnes SQL historiques
  `old_sha256_12` / `new_sha256_12` restent conservees pour compatibilite,
  mais les nouveaux audits ecrivent `NULL` et les read-models ne les exposent
  plus.
- Correctif Lot 6E.1: cloture prematuree corrigee. La route active
  `/api/admin/hermeneutics/identity-candidates` ne projette plus
  `content_sha256_12`, `content_norm_sha256_12`, `reason_sha256_12` ni
  `override_note_sha256_12`; le libelle `observability_contract` identity ne
  promet plus de hashes; les specs actives identity/dashboard/read-model sont
  alignees sur presence, longueurs, compteurs, statuts, reason codes, IDs
  opaques et timestamps.
- Critere de cloture: doctrine explicite sur hashes courts identity:
  suppression, HMAC/salt, ou exception justifiee.
- Preuve minimale: spec/docs + tests projection.
- Preuve Lot 6E/6E.1: tests sentinelles guard/dashboard/admin/read-model prouvent que
  les anciens champs `identity_block_sha256_12`, `update_reason_sha256_12`,
  `old_sha256_12`, `new_sha256_12`, `proposition_sha256_12` et les hashes de
  contenu/reason legacy identity ne ressortent plus dans les surfaces traitees.
- Hors-scope: modifier contenu identity.

### P2-CEL-NOTES-UI-GAP-01

- Statut initial: open.
- Statut courant: closed_by_lot_5B_2_3_backend_notes_mode_folder_lookup_guard.
- Severite: P2.
- Fichiers suspects: routes Notes folder-scoped, panels frontend workspace.
- Lot cible: Lot 5.
- Audit Lot 5A: valide. Les routes Notes folder-scoped existent
  (`/api/workspace-folders/<folder_id>/notes`, lookup, get, append, prepare,
  create) et le prompt/context Notes est cable cote runtime, mais aucune UI
  Notes dediee n'a ete trouvee dans `app/web`.
- Decision Lot 5B.2: Notes n'est plus API-only. Un mode Notes minimal est
  visible dans le composer, au meme rang conceptuel que les modes Biblio/Agenda,
  avec panneau de notes par repertoire courant.
- Correctif Lot 5B.2.1: valide et corrige un effet de bord P2: le frontend
  envoyait `workspace_notes_mode=true`, mais le backend ne consommait que
  `workspace_note_id` / `workspace_note_ids`. Le bouton Notes seul pouvait donc
  etre un no-op backend sans note selectionnee.
- Correctif Lot 5B.2.2: valide et corrige deux effets de bord: le mode Notes
  actif sans note court-circuitait la validation du dossier courant; le contrat
  prompt disait simultanement que des notes etaient selectionnees et qu'aucune
  note n'etait selectionnee.
- Correctif Lot 5B.2.3: valide et corrige l'effet de bord restant: un
  `workspace_folder_id` syntaxiquement valide mais introuvable ou supprime
  pouvait encore produire une lane Notes sans selection parlant du dossier
  courant. Le dossier est maintenant lu via `_get_folder(..., include_deleted=True)`
  avant toute lane `workspace_notes_mode_active_without_selection`.
- Critere de cloture: UI minimale livree sur routes Notes existantes: liste des
  notes du repertoire, creation d'une note vide titree, preparation/selection
  d'une note comme contexte `workspace_note_id`, erreur de liste rendue comme
  erreur visible au lieu d'une liste vide, et consommation backend reelle de
  `workspace_notes_mode=true` meme sans note selectionnee, avec garde
  d'existence/suppression du dossier courant et contrat prompt non contradictoire.
- Preuve minimale: tests module frontend Notes, tests panneau Notes,
  lane backend Notes, contrats backend Notes existants.
- Hors-scope: rouvrir backend Notes sans besoin.

### P2-CEL-FRONTEND-EMPTY-ON-ERROR-01

- Statut initial: open.
- Statut courant: closed_by_lot_5C_1_frontend_documents_error_states.
- Severite: P2.
- Fichiers suspects: `app/web/chat_threads_sidebar.js`, panels
  Documents/Exports/Images.
- Lot cible: Lot 5 ou 7.
- Audit Lot 5A: valide partiellement. Plusieurs chemins frontend affichent deja
  un statut d'erreur, mais des fetch/listes workspace peuvent encore convertir
  une erreur amont en tableau vide ou etat visuel vide; sans tests par panel, on
  ne peut pas declarer que chaque erreur API est distinguee d'une vraie liste
  vide.
- Decision Lot 5C: tests/micro-corrections par panel, sans attendre une matrice
  smoke frontend globale.
- Correctif Lot 5C: valide et corrige Exports/Images hors Notes. Exports et
  Images conservent maintenant un `status=error` content-free dans
  l'etat central quand le fetch echoue, quand `ok=false`, quand HTTP est non-2xx
  ou quand le payload liste est inattendu; les panels rendent alors une erreur
  visible au lieu de `Aucun export` / `Aucune image`. Le vide normal `ok` + liste
  vide reste affiche comme etat vide normal. Notes reste non regresse par ses
  tests Lot 5B.
- Correctif Lot 5C.1: valide et corrige le reste Documents/Fichiers. Le
  chargement `/files` conserve maintenant un statut `error` content-free
  distinct de la liste vide pour fetch/HTTP/`ok=false`/payload inattendu, et le
  panneau rend `Chargement des fichiers impossible` au lieu de `Aucun fichier`.
  Le vide normal et les controles fichier existants restent couverts par tests.
- Critere de cloture: erreurs API panels visibles comme erreur, pas comme
  liste vide.
- Preuve minimale: tests 500/payload invalide par panel.
- Hors-scope: redesign UI large.

### P2-CEL-EXCEPTION-RAW-SURFACE-01

- Statut courant: closed_by_lot_6J_internal_logs_requalified.
- Severite: P2.
- Fichiers suspects: `app/server.py`, `app/tools/web_search.py`,
  `app/core/*`, `app/memory/*`, `app/observability/*`, `app/biblio/*`.
- Lot cible: Lots 6B/6C/6D/6E, Lot 6I pour les surfaces exposees
  confirmees, puis Lot 6J pour les logs runtime `err=%s` restants.
- Preuve Lot 6A: le scan `str(exc)` / `repr(exc)` / `exc_info` / `traceback` /
  `print(` trouve plusieurs familles independantes; elles ne doivent pas etre
  remplacees globalement sans validation surface par surface.
- Preuve Lot 6I: les surfaces restantes confirmees ont ete corrigees sans
  remplacement global: `/api/chat` catch-all, Web Search `message_short`,
  reponses settings/admin validation, `read_errors` Memory Admin, logs admin
  conversations/restart et reponses governance identity.
- Limite Lot 6I.1: la cloture globale etait trop large. Les logs runtime
  `logger.*("... err=%s", exc)` restent a qualifier par famille avant cloture
  complete, notamment `app/server.py`, `app/memory/memory_traces_summaries.py`,
  `app/core/conversations_store.py`, `app/memory/arbiter.py` et autres familles
  runtime detectees par scan.
- Preuve Lot 6J: scan borne `err=%s` / `str(exc)` / `repr(exc)` /
  `exc_info=True` / `traceback` sur `app/server.py`, `app/admin`, `app/core`,
  `app/memory`, `app/observability`, `app/tools`, `app/agenda`, `app/biblio`
  et `app/identity`: 106 hits qualifies. Aucun hit restant n'est une reponse
  HTTP utilisateur/admin, un payload observabilite, une projection dashboard ou
  un export lisible avec exception brute confirme. Les logs restants sont
  requalifies comme `safe_internal_log` / `content_free_already` /
  `test_only` / `out_of_scope_post_v1` selon famille.
- Critere de cloture: surfaces qualifiees; corrections bornees uniquement.
- Preuve minimale: tests content-free/fail-closed par surface.
- Hors-scope: remplacement massif aveugle de `str(exc)`.

### P2-CEL-OBSERVABILITY-PAYLOAD-REJECTED-STREAM-01

- Statut courant: closed_by_lot_6J_stream_payload_schema.
- Severite: P2.
- Classe: `P2_observability_guard_rejection`.
- Surfaces suspectes: suites stream LLM, `chat_turn_log_payload_rejected`,
  writer-side observability guard et projection finale de stream.
- Lot cible: Lot 6J si le rejet writer-side est confirme et corrigeable avant
  smokes; Lot 7 si le sujet releve de matrice/smoke/projection finale.
- Preuve Lot 6I.1: les warnings `chat_turn_log_payload_rejected` vus dans les
  suites stream LLM ne doivent plus rester une note volante ni etre caches par
  la cloture partielle de `P2-CEL-EXCEPTION-RAW-SURFACE-01`.
- Preuve Lot 6J: reproduction conteneur valide les rejets stream sur
  `llm_call` / `persist_response`. Cause isolee: `stream_chunks`,
  `stream_terminal` et le champ libre `reason` de `persist_response`. Correctif:
  schema writer-side accepte uniquement les champs stream compacts content-free,
  et `persist_response` projette `reason_code` au lieu de `reason`.
  Probe Lot 6J: `stream_rejection_count=0`; les rejets `chat_response`
  non-stream restants sont requalifies en finding dedie Lot 6J.1.
- Critere de cloture: reproduire le payload stream exact sans contenu brut,
  classer `test_stale` / `projection_drift` / `guard_rejection`, puis corriger
  uniquement la surface confirmee.
- Hors-scope Lot 6I.1: aucun patch runtime.

### P2-CEL-OBSERVABILITY-PAYLOAD-REJECTED-CHAT-RESPONSE-01

- Statut courant: closed_by_lot_6J_1_chat_response_refusal_payload.
- Severite: P2.
- Classe: `P2_observability_guard_rejection`.
- Surface: `chat_turn_logger.emit_refusal()` appele par `/api/chat` pour les
  refus produit non-stream 4xx.
- Preuve Lot 6J.1: probe direct de la garde avec
  `reason_short: "chat status 400"` -> `accepted=False`,
  `issue_classes=['unsafe_string_value']`. Le payload etait remplace par
  `observability_payload_rejected`, ce qui masquait le diagnostic compact
  `chat_response`.
- Correctif Lot 6J.1: `emit_refusal()` ne stocke plus le texte court libre; il
  conserve `reason_code`, `reason_short_chars` et
  `reason_short_included=False`.
- Critere de cloture: plus de `chat_turn_log_payload_rejected stage=chat_response`
  dans les tests cibles; aucun message utilisateur, payload brut ni exception
  brute ajoute.
- Hors-scope: Lot 7 `/log` denylist, Lot 9 refactors.

### P2-CEL-ADMIN-400-RAW-01

- Statut courant: closed_by_lot_6C.
- Severite: P2.
- Fichiers suspects: `app/server.py` routes admin logs/dashboard/export.
- Lot cible: Lot 6C.
- Preuve Lot 6A: les routes admin 400/404 exposent encore des erreurs issues de
  `ValueError` / `LookupError` sous forme textuelle; le correctif doit rester
  borne aux reason codes stables et aux tests sentinelles.
- Preuve Lot 6C: `app/server.py` ne renvoie plus `str(exc)` sur les 400/404
  admin logs/dashboard/export/content; les tests sentinelles conteneur valident
  l'absence d'URL/query, path prive synthetique, token-like synthetique et
  payload raw synthetique dans les reponses.
- Critere de cloture: `ValueError`/400 admin renvoie reason code stable sans
  echo de valeur invalide.
- Preuve minimale: tests sentinelles URL/token/path dans query params.
- Hors-scope: refactor routes admin.

### P2-CEL-DOCS-ACTIVE-AUDITS-01

- Statut initial: open.
- Statut courant: closed_by_lot_8_audit_index.
- Severite: P2.
- Fichiers suspects: audits superseded dans `app/docs/todo-todo/audits`.
- Lot cible: Lot 8.
- Correctif Lot 8: `app/docs/todo-todo/audits/README.md` classe explicitement
  les audits superseded conserves provisoirement et renvoie la source active a
  la TODO canonique. Aucun fichier n'a ete deplace afin de ne pas casser les
  liens avant l'archive Lot Z.
- Critere de cloture: aucun audit superseded ambigu comme travail actif.
- Preuve minimale: grep references, liens mis a jour.
- Hors-scope: reecrire constats historiques.

### P2-CEL-SERVER-ROUTE-GRAVITY-01

- Statut courant: `closed_by_lot_9A_and_lot_9Z`.
- Severite: P2.
- Fichier suspect: `app/server.py`.
- Alias/fusion: `P2-CEL-SERVER-BOUNDARY-GRAVITY-01`.
- Lot cible: Lot 9.
- Decision Lot 4E: aucun P1/P2 comportemental immediat confirme par la seule
  taille du fichier; la gravite reste structurelle et doit passer par golden
  tests routes/admin/workspace/chat avant extraction.
- Critere de cloture: plan de split par responsabilite et golden tests routes.
- Preuve minimale: snapshot routes, tests routes/admin/workspace/chat.
- Hors-scope: refactor sans tests.

### P2-CEL-CHAT-ORCHESTRATION-GRAVITY-01

- Statut courant: `closed_by_lot_9B_and_lot_9Z`.
- Severite: P2.
- Fichier suspect: `app/core/chat_service.py`.
- Lot cible: Lot 9.
- Decision Lot 4E: aucun P1/P2 comportemental immediat confirme apres Lots
  4B/4D/4D.2/4D.3/4D.3.1; l'orchestration reste lourde et fragile, mais ne
  doit pas etre extraite sans golden tests d'ordre des lanes/final-lock/capsule.
- Critere de cloture: golden tests d'ordre lanes/final-lock/capsule avant
  extraction de l'orchestration.
- Preuve minimale: tests fake couvrant conflits lanes et bypass final-lock.
- Hors-scope: refactor chat sans preuve d'ordre comportemental.

### P2-CEL-REQUESTS-TIMEOUT-01

- Statut courant: `invalid_as_global_finding_by_lot_4A`; aucun appel HTTP
  externe evident sans timeout dans le perimetre audite, et les fail-open
  ciblables isoles ensuite sont fermes par Lots 4B et 4D.
- Severite: P2.
- Fichiers suspects: clients HTTP detectes par scan heuristique.
- Lot cible: Lot 4A/4B.
- Resultat Lot 4A: aucun appel HTTP externe evident sans timeout dans le
  perimetre scanne; les timeouts sont explicites sur OpenRouter principal,
  agents secondaires, SearXNG, Crawl4AI, OCR/Stirling, image generation,
  Catalogue/Biblio, CalDAV et clients Nextcloud/WebDAV.
- Reste ouvert: verifier les fallbacks qui transforment une panne amont en
  resultat vide, en particulier web/search.
- Critere de cloture: timeouts/fallbacks verifies par client, avec decision
  explicite pour les fail-open intentionnels.
- Preuve minimale: tests timeout/fallback par client corrige ou accepte.
- Hors-scope: provider live non demande.

### P2-CEL-WEB-SEARCH-FAIL-OPEN-01

- Statut courant: closed_by_lot_4B.
- Severite: P2.
- Classe: `P2_error_handling`.
- Fichiers suspects: `app/tools/web_search.py`,
  `app/tests/unit/web_search/test_web_search_phase4.py`,
  `app/tests/unit/logs/test_chat_turn_logger_web_search.py`,
  `app/tests/test_server_chat_web_runtime_contract.py`.
- Constat: `search()` intercepte une panne SearXNG et retourne `[]` avec un
  warning content-free; en aval, `build_context()` / payloads peuvent donc
  ressembler a un vrai `no_data` au lieu d'une panne de lecture recherche.
- Preuve Lot 4A: `app/tools/web_search.py` utilise `timeout=10` mais retourne
  `[]` sur exception; les tests couvrent le no-data manuel et l'event error
  general, pas encore une panne SearXNG reelle propagee comme `status=error`
  jusqu'au payload runtime.
- Resultat Lot 4B: finding valide puis corrige. Le contrat legacy `search()`
  conserve une liste pour compatibilite, mais le chemin runtime utilise un
  outcome interne content-free; une panne locale SearXNG sans resultat devient
  `status=error`, `reason_code=web_search_upstream_error`, `error_class`
  qualifie, tandis qu'un vrai zero resultat reste `status=skipped`,
  `reason_code=no_data`.
- Preuve Lot 4B: tests fake `requests.get` pour exception SearXNG et reponse
  vide; verification du payload consomme par le chat, de l'event
  `web_search`, du logger `error`, du timeout `10`, et de l'absence de query /
  URL / exception brute dans les projections content-free.
- Impact: confiance produit excessive dans une reponse sans contexte web alors
  que la recherche a pu echouer.
- Lot cible: Lot 4B.
- Critere de cloture: distinguer panne SearXNG amont et absence reelle de
  resultats via status/reason code stable content-free, sans requete brute ni
  URL brute.
- Preuve minimale: couvert par test fake `requests.get` qui leve, verification
  `status=error` ou `partial` stable dans `build_context_payload`/chat web, et
  absence de query brute dans logs/projections.
- Hors-scope: provider live, refonte web_search globale, correction logs
  content-free hors Lot 6.

### P2-CEL-WEB-DISCOVERY-FAIL-OPEN-01

- Statut courant: closed_by_lot_4D.
- Severite: P2.
- Classe: `P2_error_as_empty`.
- Fichiers touches: `app/tools/web_search.py`,
  `app/tests/unit/web_search/test_web_search_discovery.py`.
- Constat valide Lot 4D: apres Lot 4B, la recherche locale SearXNG distingue
  panne et zero resultat, mais le provider de discovery `openrouter_exa`
  pouvait encore retourner `results=[]` avec
  `web_discovery_external_error_kind` et finir dans le payload comme
  `status=skipped`, `reason_code=no_data`.
- Impact: une panne OpenRouter/config/tool discovery pouvait etre lue comme
  absence reelle de sources web, alors que le provider amont avait echoue.
- Correction Lot 4D: si le plan contient
  `openrouter_exa_discovery_failed` et `web_discovery_external_error_kind`, le
  payload/runtime event sort maintenant en `status=error`,
  `reason_code=web_discovery_upstream_error`, `error_class`
  `WebDiscoveryUpstreamError`; le cas valide sans citation reste
  `status=skipped`, `reason_code=no_data`.
- Preuve Lot 4D: test fake OpenRouter config error vs reponse valide sans
  citation, sans provider live ni query/URL brute.
- Lot cible: Lot 4D.
- Hors-scope: changement provider OpenRouter, fallback externe automatique,
  correction logs raw Lot 6.

### P2-CEL-MEMORY-INPUT-FAIL-OPEN-01

- Statut courant: closed_by_lot_4D_2.
- Severite: P2.
- Classe: `P2_error_as_empty`.
- Fichiers touches: `app/core/chat_turn_runtime_inputs.py`,
  `app/core/hermeneutic_node/inputs/identity_input.py`,
  `app/core/hermeneutic_node/inputs/summary_input.py`,
  `app/tests/unit/core/test_chat_turn_runtime_inputs.py`.
- Constat valide Lot 4D.2: `resolve_summary_input()` transformait une
  exception de lecture summary en `status=missing`, et
  `resolve_identity_input()` transformait une exception identity en payload
  `v2` vide sans `status` ni `reason_code`. La retrieval memoire dense et
  arbitration etaient deja correctes via `memory_retrieved.status=error` et
  `reason_code=retrieve_error`.
- Impact: le primary node / validation agent pouvait lire une panne summary ou
  identity comme absence normale de donnees, tout en perdant le signal
  content-free de panne dans les canonical inputs.
- Correction Lot 4D.2: les builders canoniques portent maintenant un statut
  content-free; absence normale reste `missing`, donnees presentes deviennent
  `available`, et panne de lecture devient `status=error` avec
  `reason_code=summary_read_error` ou `identity_read_error`, `error_code`
  `upstream_error`, `error_class` qualifie.
- Preuve Lot 4D.2: tests fakes summary/identity read error, absence normale,
  contenu present, absence de fuite brute, et canonical inputs transmis au
  hermeneutic node.
- Lot cible: Lot 4D.2.
- Hors-scope: changement doctrinal du primary node, refactor memory/identity,
  logs raw Lot 6.

### P2-CEL-AGENDA-CLIENT-UNAVAILABLE-AMBIGUITY-01

- Statut courant: closed_by_lot_4D_3.
- Severite finale: P2.
- Classe: `P2_error_as_empty`.
- Fichiers touches: `app/agenda/chat_runtime.py`,
  `app/agenda/read_execution.py`, `app/agenda/proposal_execution.py`,
  `app/observability/observability_payload_guard_schema.py`,
  `app/tests/unit/agenda/test_chat_runtime.py`.
- Requalification Lot 4D.3: Agenda n'est pas dormant au sens runtime. Le
  runtime Agenda est implemente, branche dans `chat_service`, activable par
  toggle utilisateur et section runtime `agenda_agent`; le chantier/TODO large
  Agenda reste seul post-V1 dormant.
- Constat valide Lot 4D.3: `_resolve_read_client()` attrapait une exception de
  lecture secret/config et retournait `(None, False)`. Un plan read sortait
  ensuite `status=skipped`, `reason_code=agenda_readonly_client_unavailable`;
  le chemin proposal delegue a `_resolve_read_client()` pouvait de meme perdre
  le signal de panne.
- Impact: une panne runtime actuelle de resolution client Agenda pouvait etre
  lue comme absence volontaire de client ou indisponibilite normale, alors que
  le mode actif et le secret configure impliquent une vraie erreur operatoire.
- Correction Lot 4D.3: la resolution client porte maintenant un etat
  content-free. Client absent volontaire / secret vide reste
  `agenda_readonly_client_unavailable`; secret non configure reste
  `agenda_agent_secret_not_configured`; exception secret/config devient
  `status=error` avec `agenda_readonly_client_resolution_error` sur read, et
  `agenda_pending_read_client_resolution_error` sur proposal.
- Preuve Lot 4D.3: tests fake/local secret reader qui leve, secret vide,
  client absent normal, read plan et proposal plan, sans secret, URL CalDAV ni
  exception brute dans payload.
- Lot cible: Lot 4D.3.
- Hors-scope: pas de CalDAV live, pas de provider live, pas de nouvelles
  capacites Agenda, pas de modification DB.

### P2-CEL-AGENDA-PAYLOAD-GUARD-REJECTS-REAL-ERROR-01

- Statut courant: closed_by_lot_4D_3_1.
- Severite finale: P2.
- Classe: `P2_observability_guard_rejection`.
- Fichiers touches: `app/observability/observability_payload_guard_schema.py`,
  `app/tests/unit/agenda/test_chat_runtime.py`,
  `app/tests/unit/logs/test_observability_payload_guard.py`.
- Constat valide Lot 4D.3.1: les payloads reels produits par
  `run_agenda_chat_turn()` apres Lot 4D.3 portaient bien
  `read_execution_status=error` ou `pending_execution_status=error`, mais la
  garde writer-side les rejetait encore avec `observability_payload_rejected`.
- Correction Lot 4D.3.1: allowlist schema-first et bornee des champs Agenda
  content-free reels (`agent.validation.plan`, hashes/listes, timestamps,
  `read_execution`, `pending_execution`, `pending_state`, `redacted`), sans
  suffixes generiques ni acceptation URL/DAV/ICS/secret/payload provider.
- Preuve Lot 4D.3.1: probe sur payloads reels read/proposal acceptes par
  `guard_payload(...)`, test de faux payload dangereux toujours refuse.
- Lot cible: Lot 4D.3.1.

### P2-CEL-AGENDA-READMODEL-CHILD-ERROR-MASKED-01

- Statut courant: closed_by_lot_4D_3_1.
- Severite finale: P2.
- Classe: `P2_observability_projection_masking`.
- Fichier touche: `app/agenda/observability_read_model.py`.
- Constat valide Lot 4D.3.1: la projection admin lisait d'abord
  `payload.status` / `payload.reason_code`, donc un payload
  `status=active_ready` avec `read_execution_status=error` ou
  `pending_execution_status=error` pouvait etre projete comme
  `active_ready/agenda_agent_active_validated`.
- Correction Lot 4D.3.1: la projection admin prefere maintenant les statuts
  enfants `error` / `failed` read, pending ou write avec leurs reason codes,
  tout en preservant l'ordre existant pour les cas normaux.
- Preuve Lot 4D.3.1: tests read-model et probe sur payloads reels read/proposal
  projetes en `error` avec le reason code enfant attendu.
- Lot cible: Lot 4D.3.1.

### P2-CEL-MUTABLE-IDENTITY-STAGING-TEST-FAILURES-01

- Statut courant: closed_by_lot_6F.
- Severite: P2.
- Classe: `P2_test_contract_or_runtime_validation`.
- Suite concernee: `tests.unit.memory.test_identity_periodic_agent_phase1`.
- Constat observe apres Lot 4D.2: des cas mutable identity staging attendus
  `ok` sortent `skipped` ou `refused`; `invalid_verdict` peut etre remplace
  par `observability_payload_rejected`, et un cas laisse un buffer non nettoye.
- Preuve Lot 6A: la suite cible relancee en conteneur reproduisait encore ces
  ecarts.
- Preuve Lot 6F: les ecarts ont ete classes. Cause confirmee: garde
  observabilite trop stricte sur payload compact legitime, plus fixtures de
  succes stale vis-a-vis du contrat ontologique v2. `buffer_cleanup_bug` et
  `runtime_identity_bug` sont invalides pour ce lot.
- Lot cible: Lot 6F.
- Critere de cloture: suite cible verte; reason codes utiles conserves;
  `observability_payload_rejected` ne masque plus le cas mutable identity
  legitime; cleanup buffer conforme sur retry reussi; aucun contenu identity
  brut ajoute.
- Hors-scope Lot 4D.2: ne pas requalifier le correctif memory input cible.

### P2-CEL-ARBITER-PAYLOAD-GUARD-REJECTION-01

- Statut courant: closed_by_lot_6F_1.
- Severite: P2.
- Classe: `P2_observability_guard_rejection`.
- Suite concernee: `tests.unit.logs.test_chat_turn_logger_phase2`.
- Constat observe apres Lot 6F: les events `stage=arbiter` etaient remplaces
  par `observability_payload_rejected`; les tests perdaient le payload compact
  et echouaient sur `raw_candidates`.
- Preuve Lot 6F.1: la reproduction conteneur confirmait deux erreurs avec
  `chat_turn_log_payload_rejected stage=arbiter`; le probe de garde isolait
  uniquement `rejected_candidates` et `fallback_decisions` comme compteurs
  non allowlistes.
- Correction Lot 6F.1: ajouter ces deux compteurs au schema writer-side et
  verrouiller par tests que `raw_candidates` reste un entier, que
  `rejection_reason_code_counts` reste une map de compteurs et que contenu
  candidat, prompt, URL et payload provider bruts restent refuses.
- Lot cible: Lot 6F.1.
- Critere de cloture: suite arbiter verte; payload arbiter compact legitime
  accepte; payload dangereux refuse; mutable identity Lot 6F non regresse.
- Hors-scope: ne traite pas `P2-CEL-STIMMUNG-PROMPT-GUARD-REJECTION-01`,
  `P2-CEL-COMPACT-OBSERVABILITY-MESSAGES-COUNT-01`, Lot 7 ni Lot 9.

### P2-CEL-COMPACT-OBSERVABILITY-MESSAGES-COUNT-01

- Statut courant: closed_by_lot_6H_test_stale.
- Severite: P2.
- Classe: `P2_observability_contract_drift`.
- Suite concernee: `tests.test_server_chat_compact_observability_contract`.
- Constat observe apres Lot 4D.2: `messages_count` attendu `1`, obtenu `2`
  dans le contrat compact observability.
- Preuve Lot 6A: la suite cible relancee en conteneur reproduit encore
  l'ecart; le meme run observe aussi un statut summary attendu `missing` devenu
  `error`, probablement lie aux corrections fail-open memoire recentes.
- Preuve Lot 6H: la suite cible ne reproduit plus le drift summary; le statut
  `summary.status=missing` reste attendu pour l'absence normale de summary.
  Le seul echec restant etait `prompt_prepared.messages_count`: le probe
  content-free montre que `messages_count=2` correspond exactement aux deux
  messages transmis au payload LLM par `_LLMChatLogProxy.build_payload()`.
- Decision Lot 6H: test stale uniquement; `messages_count=2` est l'etat produit
  attendu pour ce scenario, pas un bug runtime ni une fuite de contenu.
- Lot cible: Lot 6H si la correction concerne le schema/projection
  observabilite compacte; Lot 7 si la revalidation conclut a un drift de
  matrice/smoke plutot qu'a un bug runtime.
- Critere de cloture: prouver si `2` est l'etat produit attendu ou une
  regression; ajuster le test ou le payload sans exposer message/prompt brut.
- Hors-scope Lot 4D.2: ne touche pas au statut summary/identity corrige.

### P2-CEL-STIMMUNG-PROMPT-GUARD-REJECTION-01

- Statut courant: closed_by_lot_6G.
- Severite: P2.
- Classe: `P2_observability_guard_rejection`.
- Suite concernee: `tests.unit.logs.test_chat_turn_logger_hermeneutic_observability`.
- Constat observe apres Lot 4D.2: l'event `stimmung_prompt_prepared` attendu
  `ok` sort `refused` avec `observability_payload_rejected`.
- Preuve Lot 6A: la suite cible relancee en conteneur reproduit encore le rejet
  de garde sur le code courant.
- Preuve Lot 6G: la reproduction cible relancee en conteneur sortait
  `refused/observability_payload_rejected`; le probe sur le payload genere par
  `build_stimmung_prompt_prepared_payload()` isolait `stimmung_status`,
  `recent_has_in_progress_turn` et `recent_max_turns` comme cles compactes
  content-free non allowlistees.
- Correction Lot 6G: autoriser uniquement ces trois cles dans le schema
  writer-side et ajouter des sentinelles prouvant que prompt brut, message
  brut, payload provider brut et URL brute restent refuses.
- Lot cible: Lot 6G, garde observabilite / schema payload.
- Critere de cloture: reproduire en fake local, identifier la cle ou classe de
  payload rejetee sans prompt brut, puis corriger schema ou test selon contrat.
- Hors-scope Lot 4D.2: pas de correction logs/raw ni de changement Stimmung.

### P3-CEL-LARGE-FILES-01

- Statut courant: `superseded_by_complexity_hotspots_then_closed_by_lot_9Z`.
- Severite: P3.
- Alias/fusion: `P3-CEL-LARGE-FILES-AMPLIFIED-01`; la seconde passe le
  supersede par `P3-CEL-COMPLEXITY-HOTSPOTS-01`.
- Lot cible: Lot 9.
- Decision Lot 4E: dette structurelle confirmee; pas de correction runtime
  immediate, pas de split cosmetique, golden tests requis avant extraction.
- Resolution Lot 10G: matrice courante module/fonction/appelants/tests vers
  9A-9H, sans `UNKNOWN`; chaque hotspot a une destination principale, un gate
  golden et une condition de reduction de responsabilite. La dette reste dans
  l'unique roadmap Lot 9; le finding de seconde passe est absorbe, pas simule
  comme refactor execute.
- Critere de sortie future: lots de refactor cibles, pas cosmetiques, apres
  Lot 9.0.
- Preuve minimale: lignes avant/apres, tests inchanges.

### P3-CEL-TEST-PROOF-MAPPING-01

- Statut courant: closed_by_lot_7_smoke_matrix.
- Severite: P3.
- Lot cible: Lot 7.
- Preuve Lot 7: matrice finale `met` / `covered_by_tests` /
  `accepted_with_documented_limit` / `post_v1` ajoutee dans la TODO et artefact
  JSONL content-free cree sous
  `app/docs/states/baselines/mega-audit-smokes/`.
- Critere de cloture: matrice tests/proofs par domaine.
- Preuve minimale: classification live/fake/mock/covered_by_tests.

### P3-CEL-SECRET-LIKE-FIXTURES-01

- Statut courant: accepted_with_documented_limit_by_lot_7.
- Severite: P3.
- Lot cible: Lot 7.
- Decision Lot 7: les fixtures de tests conservees sont des sentinelles
  synthetiques explicites; aucune valeur sensible runtime ni payload externe
  brut n'est ajoute par le lot. La chasse exhaustive des libelles historiques reste
  post-audit si l'operateur veut une hygienisation cosmetique.
- Critere de cloture: allowlist fixtures ou remplacement par sentinelles
  clairement synthetiques.
- Preuve minimale: scan anti-fuite avec forbidden count stable.

### P3-CEL-OPEN-CHECKBOXES-ARCHIVES-01

- Statut initial: open.
- Statut courant: closed_by_lot_8_audit_index.
- Severite: P3.
- Lot cible: Lot 8.
- Correctif Lot 8: `app/docs/todo-todo/audits/README.md` distingue la TODO
  canonique active, les pieces source/contre-audit du mega-audit courant et les
  audits superseded conserves provisoirement. Les checkboxes d'une piece
  historique ne sont plus executables sans renvoi explicite par la TODO
  canonique.
- Critere de cloture: conventions archives vs actifs clarifiees.
- Preuve minimale: scan checkboxes et index docs.

### P3-CEL-FINAL-LOCK-CONFLICT-TEST-01

- Statut courant: `closed_by_lot_9B_golden_matrix`.
- Severite: P3.
- Fichiers suspects: `app/core/chat_service.py`.
- Lot cible: Lot 7.
- Decision Lot 7: aucun conflit Agenda/Biblio final-lock nouveau n'est confirme
  par les smokes contractuels disponibles; le vrai verrouillage d'ordre
  orchestration releve des golden tests Lot 9 avant refactor.
- Critere de cloture: test integration fake si Agenda et Biblio final locks
  apparaissent simultanement.
- Preuve minimale: test ordre de priorite ou decision explicite impossible.

### P3-CEL-BIBLIO-COMMENTS-STALE-01

- Statut initial: open.
- Statut courant: closed_by_lot_8_docs_doctrine.
- Severite: P3.
- Fichiers suspects: `app/config.py`, `app/biblio/librarian_agent_runtime.py`.
- Lot cible: Lot 8.
- Validation Lot 8: grep des fichiers suspects sans commentaire runtime stale
  confirme; l'ambiguite restante etait dans les index/docs actifs. `AGENTS.md`
  et `app/docs/README.md` ne vendent plus l'agent bibliothecaire comme un futur
  abstrait et rappellent la doctrine: deterministe = murs/garde-fous,
  bibliothecaire LLM = travail de bibliotheque, references "18" = cas produit
  historiques/regression, pas promesse de 18 outils a rouvrir.
- Critere de cloture: commentaires/config alignes sur agent-first sans
  requalifier Biblio V1.
- Preuve minimale: diff docs/commentaires, tests non requis si commentaires.

### P3-CEL-AGENDA-DORMANT-WORDING-01

- Statut courant: closed_by_lot_4D_3.
- Severite: P3.
- Fichiers touches: `app/docs/todo-todo/product/frida-agenda-agent.md`,
  `AGENTS.md`, `README.md`, `app/docs/README.md`,
  `app/docs/states/specs/frida-agenda-agent-contract.md`.
- Lot cible: Lot 4D.3.
- Resolution: les docs actives distinguent maintenant le runtime Agenda V1
  implemente/cable/activable et la roadmap/TODO large Agenda post-V1
  dormante.
- Preuve minimale: grep statut dormant/post-V1 qualifie, aucun `futur agent
  Agenda` ni `futur bouton` actif.

### P3-CEL-LOG-FRONTEND-DENYLIST-01

- Statut initial: open.
- Statut courant: closed_by_lot_7_log_payload_allowlist.
- Severite: P3.
- Fichier suspect: `app/web/log/log.js`.
- Lot cible: Lot 5 ou 7.
- Audit Lot 5A: valide. La UI `/log` utilise des listes de cles/labels bloques
  (`BLOCKED_PAYLOAD_KEYS`, `BLOCKED_METRIC_LABELS`) et non une allowlist stricte
  par shape d'evenement. Aucune fuite n'est confirmee par Lot 5A, mais le modele
  denylist doit etre prouve par test sentinelle ou remplace plus tard.
- Correction Lot 7: le rendu payload `/log` utilise maintenant une allowlist
  frontend explicite de cles/suffixes content-free, tout en gardant le backend
  `payload_projection='admin'` et la projection `admin_log_event_projection_v1`.
  Un test browser sentinelle prouve qu'un champ inconnu et des champs
  `prompt`/`content` synthetiques ne sont pas rendus.
- Critere de cloture: UI `/log` utilise allowlist explicite ou test sentinelle
  champ inconnu.
- Preuve minimale: test frontend/log render.

### P2-CEL-LOG-SAFECODE-TOKENLIKE-01

- Statut courant: closed_by_lot_7_1_tokenlike_safe_code_redaction.
- Severite: P2.
- Classe: `P2_defense_in_depth_log_projection`.
- Surfaces: garde writer-side observabilite, projection admin des logs,
  rendu frontend `/log`.
- Constat Lot 7.1: aucune fuite reelle observee, mais une valeur token-like
  evidente sous une cle normalement safe-code (`reason_code` / `error_code`)
  passait la garde, la projection admin et le rendu `/log`.
- Correction Lot 7.1: detection prudente des prefixes token-like evidents
  `sk-*`, `sk-or-*`, `sk-live-*` avec queue longue; garde writer-side refuse,
  projection admin redacted et `/log` redacted en defense secondaire.
- Critere de cloture: reason codes normaux (`skipped`, `provider_timeout`,
  `llm_call_ok`) restent acceptes/rendus; valeur token-like synthetique refusee
  ou redacted aux trois frontieres; aucun contenu brut ajoute.

### P2-CEL-LOG-SAFECODE-TOKENLIKE-VARIANTS-01

- Statut courant: closed_by_lot_7_2_tokenlike_safe_code_variants.
- Severite: P2.
- Classe: `P2_defense_in_depth_log_projection`.
- Surfaces: garde writer-side observabilite, projection admin des logs,
  rendu frontend `/log`.
- Constat Lot 7.2: audit contradictoire valide que Lot 7.1 couvrait les
  variantes `sk-*` avec tirets, mais pas les variantes token-like evidentes
  avec underscore ou prefixes provider synthetiques (`sk_live*`, `sk_or*`,
  `ghp_*`, `hf_*`, `xoxb-*`) sous champs safe-code.
- Correction Lot 7.2: detection bornee et prudente de ces prefixes; pas de
  blocage generique des underscores ni des reason codes normaux.
- Critere de cloture: toutes les variantes synthetiques listees sont
  refusees/redacted; `skipped`, `provider_timeout`, `llm_call_ok` et
  `openai/gpt-5.4-mini` restent acceptes/rendus.

### P3-CEL-FILENAMES-CONTENT-FREE-DECISION-01

- Statut initial: open.
- Statut courant: closed_by_lot_8_docs_doctrine.
- Severite: P3.
- Zones suspectes: dashboard/read-model documents.
- Lot cible: Lot 8.
- Decision Lot 8: les filenames sont des metadonnees produit visibles quand le
  fichier/artefact est l'objet consulte ou admin-projete explicitement. Les logs,
  JSONL, smokes, payloads d'observabilite et dashboards content-free ne doivent
  pas stocker ni projeter de filenames bruts par defaut; utiliser presence,
  compteurs, statuts, reason codes, tailles, extensions ou chemins redacted.
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

### Lot 2 - Gel micro-hardening local secrets/env/logs/permissions

Intention: cloturer la phase de micro-investigation locale sans masquer les
findings. Pour un serveur solo derriere Caddy/Authelia, ces points ne bloquent
plus le passage a l'audit code tant qu'ils restent locaux, acceptes/differes ou
optionnels, et qu'aucun gros rouge public n'apparait en Lot 3/3B.

- [ ] Lot 2A: bloque par decision Lot 1E `NO-GO`; statut
  `risk_accepted_temporarily`; ne pas corriger les
  artefacts host-only `_codex_reports`, `_codex_backups` et
  `/opt/platform/backups` sans nouveau GO operateur explicite.
- [ ] Lot 2B: corriger ou documenter les fichiers actifs/service-owned sous
  `/opt/platform/data/*` seulement si un service ou un gros rouge public le
  justifie.
- [x] Lot 2C: investiguer logs Authelia/Caddy secret-like sans afficher de
  lignes brutes.
- [x] Lot 2D: valider Authelia secret-like en count-only/redacted-only; aucune
  correction immediate sans GO operateur.
- [ ] Lot 2E: optionnel, definir une politique de masquage des URLs de
  redirection completes Authelia si l'operateur le demande.
- [x] Lot 2F: investiguer permissions Compose/YAML group-writable sans
  correction plateforme.
- [x] Lot 2G: recadrer la securite plateforme realiste avant audit code.
- [ ] Postposer backups/dumps/keys host-only: aucune correction sans nouveau
  GO operateur explicite.
- [ ] Postposer Compose/YAML group-writable: `hygiene_deferred`, correction
  seulement sur GO dedie.
- [ ] Garder la gouvernance permissions/retention visible mais non bloquante
  avant Lot 3/3B.

### Lot 3 - Checkpoint securite plateforme realiste avant audit code

- [x] Inventorier ports publics et services exposes sans afficher secrets.
- [x] Verifier Caddy/Authelia comme frontiere publique des services sensibles.
- [x] Verifier absence de service critique expose sans garde.
- [x] Verifier absence de bypass evident Authelia/Caddy/admin/DB depuis
  Internet.
- [x] Verifier admin Frida, Adminer et DB: pas d'exposition publique directe
  hors garde attendue.
- [x] Verifier Docker socket/proxy a haut niveau: pas d'exposition publique ni
  consommateur evident hors besoin documente.
- [x] Verifier Cockpit a haut niveau: pas de surface publique directe
  inattendue; route Caddy/Cockpit reste a validation ciblee si souhaite.
- [x] Verifier frontieres Docker raisonnables a haut niveau; ne pas lancer de
  micro-hardening reseau si aucun gros rouge public.
- [x] Verifier health generale des services critiques sans restart/rebuild.
- [x] Si aucun P0/P1 public n'apparait, considerer la securite plateforme
  suffisante pour serveur solo et passer a l'audit code.

### Lot 3B - Inventaire mises a jour serveur/services/images

Alias lisible: inventaire des mises à jour serveur, services et images.

Statut cible: audit/inventaire only, aucune update dans ce lot.

- [x] Inventorier OS / paquets systeme sans appliquer de mise a jour.
- [x] Inventorier Docker / Docker Compose.
- [x] Inventorier images Docker des services, sans `pull`.
- [x] Inventorier Caddy.
- [x] Inventorier Authelia.
- [x] Inventorier Nextcloud.
- [x] Inventorier Postgres/Redis.
- [x] Inventorier n8n.
- [x] Inventorier SearxNG.
- [x] Inventorier Adminer.
- [x] Inventorier FridaDev app/db.
- [x] Inventorier autres services exposes ou critiques.
- [x] Classer chaque element: `update_critique_securite`,
  `update_recommandee`, `update_postposable`, `no_action`,
  `needs_operator_decision`, `needs_targeted_validation`,
  `unknown_no_network_check`.
- [x] Si update critique securite urgente: ouvrir un lot separe avec
  backup/rollback/health; sinon passer a l'audit code.

### Lot 4 - Code runtime P1/P2

Granularite decision Lot 4A: le lot parent est trop large pour patch runtime
direct. Il sert de cadre; les corrections doivent passer par sous-lots bornes.

#### Lot 4A - Audit/triage runtime P1/P2

- [x] Qualifier appels HTTP et timeouts sans provider live.
- [x] Qualifier `requests.*` / `urlopen` par client: timeout, fallback, retry.
- [x] Chercher vrais dead paths ou NotImplemented runtime.
- [x] Separer runtime code, admin/security routes et observabilite/logs.
- [x] Proposer sous-lots corrigibles sans modifier Python/JS.

Resultat Lot 4A:

- P1 runtime: aucun confirme.
- Timeouts: presents sur les clients externes scannes; `rg` sur
  `requests.*`, `urlopen`, `timeout=` et settings runtime n'a pas trouve de
  client evident sans timeout dans le perimetre prioritaire.
- Retries: rares ou absents; a ne pas corriger globalement sans besoin produit.
  Les agents secondaires utilisent plutot fallback primaire/fallback_model ou
  fail-open documente.
- Dead paths: scan `NotImplemented|NotImplementedError|TODO|FIXME` sans hit
  runtime dans le perimetre prioritaire.
- P2 runtime retenu par Lot 4A: `P2-CEL-WEB-SEARCH-FAIL-OPEN-01`,
  corrige ensuite par Lot 4B.
- P2/P3 hors Lot 4: erreurs LLM/admin raw, dashboard/log raw, admin DOM,
  panels frontend vides et routes admin restent Lots 5/6/7.
- Gros fichiers/orchestration: risques confirmes mais non patchables en Lot 4;
  conserver Lot 9 avec golden tests avant extraction.

#### Lot 4B - HTTP clients/timeouts/fail-open cibles

- [x] Traiter `P2-CEL-WEB-SEARCH-FAIL-OPEN-01`.
- [x] Ajouter test panne SearXNG reelle simulee jusqu'au payload chat web.
- [x] Garder content-free: pas de query brute, URL brute, prompt brut ou
  payload provider.
- [x] Revalider que les autres clients HTTP restent timeout-explicites.

Resultat Lot 4B:

- `app/tools/web_search.py` conserve `timeout=10` sur SearXNG.
- Panne SearXNG simulee: `status=error`,
  `reason_code=web_search_upstream_error`, `error_class` qualifie,
  `web_status_error` cote evidence.
- Vrai zero resultat simule: `status=skipped`, `reason_code=no_data`.
- Tests conteneur passes:
  `tests.unit.web_search.test_web_search_phase4`,
  `tests.unit.logs.test_chat_turn_logger_web_search`,
  `tests.unit.chat.test_chat_llm_flow`.
- Runtime/UI/server large non modifies.

#### Lot 4C - Dead paths / NotImplemented runtime confirmes

- [x] Garder dormant tant qu'aucun hit runtime n'est confirme.
- [x] N'ouvrir que sur preuve `NotImplemented`/path mort produit reel.

Resultat Lot 4C:

- Statut: `skipped_no_runtime_hit_confirmed`.
- Lot 4A n'a confirme aucun `NotImplemented`, `NotImplementedError`,
  `TODO`, `FIXME`, `pass` ou chemin dormant runtime prioritaire necessitant un
  patch immediat.
- Agenda n'est pas un dormant runtime: le runtime Agenda est
  implemente/cable/activable; l'ambiguite documentaire et le fail-open client
  ont ete traites en Lots 4D.3 et 4D.3.1.
- Aucun patch runtime Lot 4C. Les vrais sujets restants de cette sequence sont
  Lot 4E, puis Lots 5/6/7/9 selon leurs scopes propres.

#### Lot 4D - Error handling runtime qui masque une panne

- [x] Auditer uniquement les fallbacks qui changent le sens produit d'une panne
  en succes vide.
- [x] Corriger le fail-open borne `P2-CEL-WEB-DISCOVERY-FAIL-OPEN-01`.
- [x] Ne pas absorber les sujets Lot 6 `str(exc)` / raw logs.
- [x] Lot 4D.2: valider/corriger `P2-CEL-MEMORY-INPUT-FAIL-OPEN-01`.
- [x] Lot 4D.3: valider/corriger Agenda runtime client unavailable et wording
  dormant.
- [x] Lot 4D.3.1: corriger les effets de bord observabilite Agenda
  guard/read-model.

Resultat Lot 4D:

- Corrige: discovery web `openrouter_exa` upstream error ne sort plus comme
  `no_data`; reason code stable `web_discovery_upstream_error`.
- Preserve: reponse OpenRouter valide sans citation reste `skipped/no_data`.
- Invalides/deja distingues: Biblio/Catalogue utilise
  `catalogue_unavailable`; Agenda read/write utilise reason codes client/tool;
  Notes/Documents/Exports/Images utilisent `lookup_failed`, status 503 ou
  state failed sur les lectures locales/Nextcloud bornees; primary node
  fail-open porte `fail_open=True` et reason/error class content-free.
- Non absorbe: admin/security routes Lot 5 et `str(exc)` / logs raw Lot 6.

Resultat Lot 4D.2:

- Corrige: panne de lecture summary -> `status=error`,
  `reason_code=summary_read_error`, pas `missing`.
- Corrige: panne de lecture identity -> `status=error`,
  `reason_code=identity_read_error`, pas payload vide silencieux.
- Preserve: absence normale summary/identity -> `missing`; contenu present ->
  `available`.
- Deja correct: retrieval memoire dense/arbitration -> `retrieve_error` sur
  panne amont.
- Non absorbe: doctrine primary node, refactor memory/identity, Lot 6 logs raw.
- Echecs larges observes hors scope et traces separement:
  `P2-CEL-MUTABLE-IDENTITY-STAGING-TEST-FAILURES-01`,
  `P2-CEL-COMPACT-OBSERVABILITY-MESSAGES-COUNT-01`,
  `P2-CEL-STIMMUNG-PROMPT-GUARD-REJECTION-01`.

Resultat Lot 4D.3:

- Requalifie: Agenda runtime n'est pas dormant; seul le chantier/TODO large
  Agenda reste post-V1 dormant.
- Corrige: exception lecture secret/config read client ->
  `status=error`, `reason_code=agenda_readonly_client_resolution_error`, pas
  `skipped/client_unavailable`.
- Corrige: exception resolution read client sur proposal ->
  `status=error`, `reason_code=agenda_pending_read_client_resolution_error`.
- Preserve: toggle off -> `disabled/agenda_toggle_off`; secret non configure
  -> `fallback/agenda_agent_secret_not_configured`; secret vide ou client
  volontairement absent -> `agenda_readonly_client_unavailable`.
- Non absorbe: capacites Agenda riches, CalDAV live smoke, provider live,
  mutations utilisateur reelles et Lot 6 observabilite generale.

Resultat Lot 4D.3.1:

- Corrige: les payloads reels Agenda read/proposal avec erreur de resolution
  client sont acceptes par la garde writer-side tout en restant content-free.
- Corrige: la projection admin Agenda ne masque plus un statut enfant
  `error` / `failed` derriere `active_ready`.
- Preserve: faux payload dangereux avec URL, DAV path, ICS, secret/token,
  payload provider ou texte brut reste refuse.
- Non absorbe: CalDAV live smoke, provider live, migration DB, chantier Agenda
  riche et Lot 6 observabilite generale.

#### Lot 4E - Decision gros fichiers/orchestration sans refactor massif

- [x] Revalider que `server.py`, `chat_service.py`, `web_search.py` et les gros
  modules Biblio/observabilite restent Lot 9, sauf P1/P2 comportemental borne.

Resultat Lot 4E:

- Statut: `completed_docs_only_no_immediate_runtime_p1_p2`.
- Decision: pas de P1/P2 comportemental nouveau confirme par l'audit des gros
  fichiers/orchestrations; aucun refactor opportuniste. Les dettes
  structurelles restent visibles et partent en Lot 9 sous golden tests.
- Fichiers a ne pas toucher avant tests d'or: `app/server.py`,
  `app/core/chat_service.py`, `app/tools/web_search.py`,
  `app/observability/observability_payload_guard_schema.py`,
  `app/observability/turn_pipeline_read_model.py`, les runtimes Agenda/Biblio
  et les projections observabilite larges.

| Surface | Taille approx. | Responsabilite principale | Risque comportemental immediat | Dette structurelle | Decision |
| --- | ---: | --- | --- | --- | --- |
| `app/server.py` | 1849 lignes | Routes HTTP, bootstrap runtime, garde admin, endpoints admin/workspace/chat | Aucun P1/P2 immediat confirme par Lot 4E; sujets raw/admin restent Lots 5/6 | Oui, route gravity | Reporter Lot 9 avec golden tests routes/admin/workspace/chat |
| `app/core/chat_service.py` | 1255 lignes | Orchestration tour chat, lanes, final locks, capsule, primary node | P2 cibles deja traites par Lots 4D.2/4D.3; aucun nouveau patch borne | Oui, orchestration gravity | Reporter Lot 9 avec golden tests ordre lanes/final-lock/capsule |
| `app/tools/web_search.py` | 2655 lignes | Recherche web, SearXNG, Crawl4AI, discovery, evidence, projections web | P2 fail-open SearXNG/discovery traites par Lots 4B/4D; legacy `build_context()` garde contrat tuple mais emet `status=error` | Oui, module multi-responsabilite | Reporter Lot 9 seulement apres tests SearXNG error/no_data, explicit URL, discovery et content-free logs |
| `app/observability/observability_payload_guard_schema.py` | 740 lignes | Schema central default-deny des payloads observabilite | Pas de P1/P2 immediat; bugs de schema precis restent Lot 6 | Oui, schema central en croissance | Garder central maintenant; split eventuel Lot 9 apres tests garde dangereux/accepte |
| `app/observability/turn_pipeline_read_model.py` | 1393 lignes | Projection cockpit content-free des turns | Pas de P1/P2 immediat par taille; drifts `messages_count`/Stimmung restent Lot 6/7 | Oui, read-model dense | Reporter extraction apres golden tests projections compactes |
| Runtimes Agenda/Biblio | 500-1200+ lignes par module cle | Agents bornes, final locks, outils GET/CalDAV, projections | Agenda fail-open/observabilite traite en 4D.3/4D.3.1; Biblio pas de nouveau P2 Lot 4E | Oui, domaines riches | Pas de refactor avant tests d'or par domaine |

Decisions Lot 4E:

- Valides/reportes: `P2-CEL-SERVER-ROUTE-GRAVITY-01`,
  `P2-CEL-CHAT-ORCHESTRATION-GRAVITY-01` et
  `P3-CEL-LARGE-FILES-01` restent actifs mais cibles Lot 9.
- Invalides comme P1/P2 immediat: la taille seule de `server.py`,
  `chat_service.py`, `web_search.py` ou du schema observabilite ne justifie pas
  de patch runtime sans bug borne.
- Lot 5 reste dedie admin/security/app routes.
- Lot 6 reste dedie observabilite/logs applicatifs, dont les findings
  `P2-CEL-MUTABLE-IDENTITY-STAGING-TEST-FAILURES-01`,
  `P2-CEL-STIMMUNG-PROMPT-GUARD-REJECTION-01` et les surfaces raw/400.
- Lot 7 reste dedie tests/smokes/artefacts et matrice proof mapping.
- Lot 9 doit commencer par une matrice de golden tests avant tout split:
  routes HTTP, chat flow lanes, web/search error-vs-no-data, Agenda/Biblio
  final locks, guard schema accept/refuse et read-model projections.

### Lot 5 - Admin/security/app routes

- [x] Lot 5A: audit/triage admin/security/app routes docs-only.
- [x] Lot 5B.1: prompts admin complets proteges par content gate explicite.
- [x] Lot 5B.2: mode Notes minimal livre dans l'UI chat.
- [x] Lot 5B.2.1: mode Notes consomme cote backend sans note selectionnee.
- [x] Lot 5B.2.2: mode Notes sans dossier courant bloque sans lane mensongere.
- [x] Lot 5B.2.3: mode Notes valide le dossier reel avant lane sans selection.
- [x] Lot 5D: aligner compat knobs/tests admin sur contrat proxy/loopback.
- [x] Verifier routes admin registerees par modules: couvert par Lot 5A.
- [x] Verifier admin HTML/public host vs API guard: couvert par Lots 3/5A/5D.
- [x] Decider prompts complets dans DOM admin: content gate explicite livre.
- [x] Traiter Notes UI gap: UI minimale livree, plus API-only.
- [x] Lot 5C: traiter panels frontend qui rendaient les erreurs comme listes
  vides.
- [x] Lot 5C.1: traiter Documents/Fichiers erreur API visible.
- [x] Deleguer `/log` UI denylist au Lot 7: vrai test/smoke conserve ouvert
  en Lot 7.
- [x] Garder Authelia comme frontiere publique: invariant verifie par Lot 3/5A/5D.

#### Lot 5A - Audit/triage admin/security/app routes

Statut: execute docs-only le 2026-06-25.
Runtime modifie: non.
Plateforme modifiee: non.
Correction appliquee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le Lot 5 parent est
trop large pour patch runtime direct; le meilleur plan est un triage docs-only,
puis des sous-lots de correction bornes.

- [x] Inventorier les routes Flask depuis le conteneur runtime sans secret.
- [x] Verifier le contrat `/api/admin/*`: loopback conteneur ou proxy de
  confiance Caddy/Authelia avec `Remote-User`.
- [x] Distinguer pages HTML admin publiques et API admin applicatives.
- [x] Valider/requalifier les prompts complets dans DOM admin.
- [x] Valider/requalifier le gap UI Notes.
- [x] Valider/requalifier les panels frontend qui peuvent rendre erreur comme
  liste vide.
- [x] Valider/requalifier la UI `/log` denylist.
- [x] Ne pas absorber Lot 6/7/9.

Resultat Lot 5A:

- Routes Flask: `122` routes inventoriees via conteneur. Les routes API admin
  observees sont sous `/api/admin/*`: logs/chat logs, dashboard, biblio
  observability, agenda observability, memory dashboard, restart, settings,
  identity et hermeneutics.
- Guard applicatif: `before_request` protege `/api/admin/*` avec loopback local
  ou proxy de confiance + `Remote-User`; aucun retour au token humain comme
  garde d'acces active.
- Surface outil sensible hors `/api/admin/*`: `/api/tools/image-generation` est
  guardee separement par `_GUARDED_TOOLS_PATHS`; a garder dans les tests routes.
- Pages HTML admin: `/admin`, `/log`, `/dashboard`, `/hermeneutic-admin`,
  `/identity`, `/memory-admin` sont des routes HTML statiques cote app. Leur
  frontiere publique releve de Caddy/Authelia, pas du guard `/api/admin/*`.
- Verification publique bornee: `HEAD https://fridadev.frida-system.fr/admin`
  et `/api/admin/logs` repondent `302` vers Authelia via Caddy; cookies non
  recopies.
- `P2-CEL-ADMIN-COMPAT-KNOBS-01`: pas de bypass runtime confirme, mais les
  fixtures/tests mentionnant encore les knobs obsoletes doivent etre nettoyes ou
  marques compat dans un sous-lot.
- `P2-CEL-ADMIN-PROMPTS-DOM-01`: valide; prompts complets presents dans admin
  JSON/DOM readonly. Decision operateur requise avant correction.
- `P2-CEL-NOTES-UI-GAP-01`: valide; backend/runtime Notes existe, UI dediee
  absente. Decision produit requise.
- `P2-CEL-FRONTEND-EMPTY-ON-ERROR-01`: valide; corrige en Lot 5C pour les
  surfaces ciblees Exports/Images, Notes non regresse.
- `P3-CEL-LOG-FRONTEND-DENYLIST-01`: valide comme dette de preuve; a traiter en
  Lot 7 sauf decision d'allowlist UI dediee.

Decoupage apres Lot 5A:

- Lot 5B: decision/correction admin prompts DOM et statut Notes UI
  API-only/UI minimale/post-audit.
- Lot 5C: tests et micro-corrections frontend erreur-vs-vide par panel, sans
  redesign UI; execute le 2026-06-25.
- Lot 5D: nettoyage tests/docs admin compat knobs et preuve route guard
  loopback/proxy/lateral direct.
- Lot 7: test `/log` champ inconnu si denylist conservee; matrice frontend
  smoke globale sans compenser les panels Exports/Images deja corriges en Lot 5C.
- Lot 6: surfaces raw/`str(exc)`, 400 admin, logs/payloads et prompt/raw
  observability; non absorbe par Lot 5A.

#### Lot 5B - Admin prompts content gate et mode Notes minimal

Statut: execute le 2026-06-25.
Runtime modifie: oui, borne a l'API admin settings et a l'UI chat Notes.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le plan le plus sur
etait de traiter les deux decisions operateur comme deux micro-surfaces bornees:
content gate explicite pour les prompts admin, puis mode Notes minimal branche
sur les routes Notes existantes, sans absorber les panels erreur-vs-vide ni les
lots logs/tests/refactor.

- [x] Valider `P2-CEL-ADMIN-PROMPTS-DOM-01`.
- [x] Lot 5B.1: retirer les prompts complets du JSON/DOM admin initial.
- [x] Lot 5B.1: exposer seulement les metadonnees content-free des prompts.
- [x] Lot 5B.1: ajouter une lecture brute separee par `POST` avec
  acquittement explicite `content_gate_acknowledged`.
- [x] Valider `P2-CEL-NOTES-UI-GAP-01`.
- [x] Lot 5B.2: ajouter un mode Notes visible dans le composer chat.
- [x] Lot 5B.2: afficher les notes du repertoire courant via les routes
  folder-scoped existantes.
- [x] Lot 5B.2: permettre creation minimale, preparation et selection de note
  comme contexte `workspace_note_id`.
- [x] Lot 5B.2: rendre une erreur de liste Notes comme erreur visible, pas
  comme liste vide.
- [x] Lot 5B.2.1: corriger `workspace_notes_mode=true` ignore cote backend
  quand aucune note n'est selectionnee.
- [x] Lot 5B.2.2: corriger le court-circuit du dossier courant et le texte de
  contrat contradictoire en mode Notes sans note selectionnee.
- [x] Lot 5B.2.3: corriger le cas `workspace_folder_id` syntaxiquement valide
  mais dossier introuvable ou supprime avant lane Notes sans selection.
- [x] Ne pas traiter `P2-CEL-FRONTEND-EMPTY-ON-ERROR-01` hors surface Notes.
- [x] Ne pas traiter `P2-CEL-ADMIN-COMPAT-KNOBS-01`.
- [x] Ne pas traiter `P3-CEL-LOG-FRONTEND-DENYLIST-01`.

Resultat Lot 5B:

- Admin prompts: `readonly_info` standard ne contient plus les prompts bruts;
  il expose `present`, `char_count`, `line_count`, `path`, `loader`,
  `reason_code`, `raw_content_included=false` et l'endpoint de content gate.
  La lecture brute reste possible uniquement par action admin explicite separee
  avec acquittement; sans acquittement, l'API retourne
  `admin_prompt_content_gate_ack_required`.
- Notes UI: un bouton/mode Notes est disponible dans le composer; le panneau du
  repertoire courant liste les notes, permet une creation titree minimale, une
  preparation et une selection contextuelle. Le payload chat ne transporte que
  le mode et l'identifiant de note selectionne, sans contenu Markdown brut.
- Notes backend: `workspace_notes_mode=true` sans `workspace_note_id` injecte
  maintenant un contrat Notes minimal content-free dans le prompt/runtime:
  mode Notes actif, aucune note existante lue/injectee, accompagnement possible
  de creation/preparation/selection/reprise/structuration de note. Aucun corps
  Markdown n'est lu automatiquement.
- Notes backend Lot 5B.2.2: sans `workspace_folder_id`, le mode Notes actif ne
  pretend plus disposer d'un dossier courant; il retourne une erreur
  content-free `folder_note_folder_not_linked` et n'injecte aucun contrat de
  dossier courant. Le texte de contrat distingue le cas mode actif sans
  selection du cas notes selectionnees/injectees.
- Notes backend Lot 5B.2.3: avec un `workspace_folder_id` syntaxiquement valide,
  le dossier est verifie via `_get_folder(..., include_deleted=True)` avant toute
  lane Notes sans selection. Un dossier introuvable retourne
  `folder_note_folder_not_linked`; un dossier supprime retourne
  `workspace_folder_deleted`; dans les deux cas, aucune lane ne pretend disposer
  du dossier courant et aucun Markdown de note n'est lu.
- Frontend Notes: l'erreur API de liste Notes est projetee comme erreur visible
  avec `reason_code` content-free; elle n'est pas convertie en "Aucune note".

Limites conservees:

- `P2-CEL-FRONTEND-EMPTY-ON-ERROR-01` est clos par Lot 5C + Lot 5C.1:
  Exports/Images corriges en Lot 5C, Documents/Fichiers corriges en Lot 5C.1,
  Notes couvert par Lot 5B.
- `P2-CEL-ADMIN-COMPAT-KNOBS-01` est clos par Lot 5D: compat legacy bornee,
  exemple env nettoye, preuve guard admin ajoutee.
- `P3-CEL-LOG-FRONTEND-DENYLIST-01` reste cible Lot 7.
- Lot 6/7/9 restent non coches.

#### Lot 5C - Frontend panels erreur API visible

Statut: execute le 2026-06-25.
Runtime modifie: oui, borne au frontend chat.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le finding etait
suffisamment borne: Exports/Images avaient le meme fail-open que Notes avant
Lot 5B, et la correction minimale etait d'ajouter un statut de chargement
content-free puis de le rendre dans chaque panel.

- [x] Valider `P2-CEL-FRONTEND-EMPTY-ON-ERROR-01`.
- [x] Corriger Exports: erreur fetch/HTTP/`ok=false`/payload inattendu rendue
  comme `Chargement des exports impossible`, pas `Aucun export`.
- [x] Corriger Images: erreur fetch/HTTP/`ok=false`/payload inattendu rendue
  comme `Chargement des images impossible`, pas `Aucune image`.
- [x] Conserver le vide normal Exports/Images quand l'API repond `ok` avec une
  vraie liste vide.
- [x] Revalider Notes: erreur Notes reste visible comme erreur, non regresse.
- [x] Ne pas absorber Lot 5D/6/7/9.

Resultat Lot 5C:

- `chat_threads_sidebar.js` conserve maintenant des maps de statut separees
  pour Exports et Images, sur le modele Notes: `ok`, `not_applicable`, `error`
  et `reason_code` content-free.
- Les panels Exports/Images consultent ce statut avant de rendre l'etat vide.
- Les payloads inattendus ne sont plus normalises silencieusement en listes
  vides: ils deviennent `folder_export_lookup_failed` ou
  `folder_generated_image_lookup_failed`.
- Les tests Node prouvent: vide normal Exports/Images, erreur Exports/Images,
  non-regression Notes, absence de payload brut/detail technique dans le DOM test.

#### Lot 5C.1 - Documents/Fichiers erreur API visible

Statut: execute le 2026-06-25.
Runtime modifie: oui, borne au frontend chat.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le retour Lot 5C avait
ferme trop largement le finding: Exports/Images etaient corriges, Notes etait
non regresse, mais Documents/Fichiers gardait encore un `catch -> []`.

- [x] Valider le reste `P2-CEL-FRONTEND-EMPTY-ON-ERROR-01` sur Documents/Fichiers.
- [x] Corriger `/files`: erreur fetch/HTTP/`ok=false`/payload inattendu rendue
  comme `Chargement des fichiers impossible`, pas `Aucun fichier`.
- [x] Conserver le vrai vide normal Documents/Fichiers quand l'API repond `ok`
  avec une vraie liste vide.
- [x] Conserver les actions fichier existantes quand la liste est OK:
  selection, suppression, OCR/edition selon metadata.
- [x] Revalider Exports/Images/Notes.
- [x] Ne pas absorber Lot 5D/6/7/9.

Resultat Lot 5C.1:

- `chat_threads_sidebar.js` conserve maintenant une map de statut separee pour
  Documents/Fichiers, sur le modele Notes/Exports/Images: `ok`, `error` et
  `reason_code` content-free.
- `chat_workspace_folders_sidebar.js` consulte ce statut avant de rendre
  `Aucun fichier`.
- Un payload `/files` inattendu devient `workspace_files_lookup_failed` au lieu
  d'une liste vide silencieuse.
- Les tests Node prouvent: HTTP 500/`ok=false`, payload inattendu, vide normal,
  rendu erreur visible, actions fichier visibles en cas liste OK, et
  non-regression Exports/Images/Notes.

#### Lot 5D - Admin compat knobs et preuve guard admin OVH

Statut: execute le 2026-06-25.
Runtime modifie: non.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le guard runtime etait
deja aligne; le meilleur plan etait de renforcer la preuve comportementale,
nettoyer l'exemple d'environnement qui presentait encore les anciens knobs comme
configurables, et documenter le statut compat legacy.

- [x] Valider `P2-CEL-ADMIN-COMPAT-KNOBS-01`.
- [x] Confirmer que `server.py` ne rebranche pas `FRIDA_ADMIN_TOKEN`,
  `FRIDA_ADMIN_LAN_ONLY`, `FRIDA_ADMIN_ALLOWED_CIDRS` ni `X-Admin-Token` dans
  le guard `/api/admin/*`.
- [x] Confirmer que `config.py` conserve seulement des constantes compat
  obsoletes non env-backed.
- [x] Nettoyer `.env.example`: ne plus presenter les anciens knobs comme des
  variables operateur actives.
- [x] Ajouter une preuve test: loopback local accepte.
- [x] Ajouter une preuve test: proxy de confiance + `Remote-User` accepte.
- [x] Ajouter une preuve test: acces direct non-proxy refuse.
- [x] Ajouter une preuve test: lateral direct avec `Remote-User` forge refuse.
- [x] Ajouter une preuve test: `X-Admin-Token`/`FRIDA_ADMIN_TOKEN` seul ne
  suffit pas.
- [x] Ne pas absorber Lot 6/7/9.

Resultat Lot 5D:

- Contrat OVH maintenu: `/api/admin/*` accepte seulement loopback conteneur ou
  proxy Caddy/Authelia de confiance avec identite `Remote-User`.
- Les appels directs depuis une adresse non-loopback/non-proxy restent refuses,
  meme si un header `Remote-User` est forge.
- Le token admin legacy n'est pas un garde humain: meme si la constante compat
  est modifiee dans un test, `X-Admin-Token` seul ne donne pas acces.
- Les anciens noms restent visibles uniquement comme compat obsoletes dans
  `config.py` et dans quelques tests historiques qui snapshotent ces constantes;
  ils ne sont pas env-backed et ne sont plus proposes dans `.env.example`.

#### Lot 5 parent checklist validation docs-only

Statut: execute le 2026-06-25.
Runtime modifie: non.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le Lot 5 parent
contenait encore des cases ouvertes qui etaient soit deja prouvees par les
sous-lots, soit a deleguer explicitement a Lot 7.

Validation case par case:

| Case parent | Statut | Preuve | Decision |
|---|---|---|---|
| Verifier routes admin registerees par modules | `stale_already_covered` | Lot 5A: inventaire Flask `122` routes, routes API admin observees sous `/api/admin/*`, surface outil sensible separee `/api/tools/image-generation`. | Case cochee comme couverte par Lot 5A. |
| Verifier admin HTML/public host vs API guard | `stale_already_covered` | Lot 3: Caddy/Authelia frontiere publique; Lot 5A: distinction pages HTML statiques vs API admin; Lot 5D: preuve guard `/api/admin/*`. | Case cochee comme couverte par Lots 3/5A/5D. |
| Traiter `/log` UI denylist si Lot 7 confirme le besoin | `move_or_delegate_to_later_lot` | Lot 5A qualifie `P3-CEL-LOG-FRONTEND-DENYLIST-01` comme dette de preuve; Lot 7 contient deja le test `/log` champ inconnu. | Case non cochee, reformulee comme delegation explicite Lot 7. |
| Garder Authelia comme frontiere publique | `stale_already_covered` | Lot 3 verifie Caddy/Authelia comme frontiere publique; Lot 5A verifie les HEAD publics rediriges vers Authelia; Lot 5D maintient le guard proxy `Remote-User`/loopback. | Case cochee comme invariant deja verifie. |

Decision:

- Lot 5 parent n'a plus de tache ouverte propre a Lot 5 hors delegation Lot 7.
- Lot 7 reste non coche et conserve `/log` UI denylist comme preuve/smoke futur.
- Lot 6/9 restent non absorbes.

### Lot 6 - Observabilite/logs applicatifs

- [x] Lot 6A: audit/triage observabilite/logs applicatifs, docs-only.
- [x] Qualifier `str(exc)`, raw, payload, traceback, print.
- [x] Lot 6B: traiter erreurs LLM brutes.
- [x] Lot 6C: traiter erreurs 400/404 admin brutes sur logs/dashboard/export.
- [x] Lot 6D: traiter dashboard web legacy URL/hash raw.
- [x] Lot 6E: trancher doctrine hashes courts identity.
- [x] Lot 6E.1: corriger hashes identity restants dans `identity-candidates`,
  libelle runtime et specs actives.
- [x] Lot 6E.2: aligner versions de projection identity apres retrait des
  hashes courts.
- [x] Corriger seulement surfaces qui exposent ou masquent une panne.
- [x] Conserver diagnostics content-free.
- [x] Lot 6F: traiter `P2-CEL-MUTABLE-IDENTITY-STAGING-TEST-FAILURES-01`
  apres separation garde observabilite / contrat stale / runtime identity.
- [x] Lot 6F.1: traiter le rejet de garde du payload arbiter compact
  content-free.
- [x] Lot 6G: traiter `P2-CEL-STIMMUNG-PROMPT-GUARD-REJECTION-01`.
- [x] Lot 6H: requalifier `P2-CEL-COMPACT-OBSERVABILITY-MESSAGES-COUNT-01`
  comme test stale et aligner le contrat compact.
- [x] Lot 6I: requalifier/corriger les surfaces exposees confirmees restantes
  de `P2-CEL-EXCEPTION-RAW-SURFACE-01`.
- [x] Lot 6J: requalifier les logs runtime `err=%s` par famille avant cloture
  complete de `P2-CEL-EXCEPTION-RAW-SURFACE-01`.
- [x] Lot 6J: valider et corriger
  `P2-CEL-OBSERVABILITY-PAYLOAD-REJECTED-STREAM-01`
  (`chat_turn_log_payload_rejected` stream LLM).
- [x] Lot 6J.1: valider et corriger
  `P2-CEL-OBSERVABILITY-PAYLOAD-REJECTED-CHAT-RESPONSE-01`
  (`chat_turn_log_payload_rejected` chat_response non-stream).

#### Lot 6A - Audit/triage observabilite/logs applicatifs

Statut: execute le 2026-06-25.
Runtime modifie: non.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non pour un correctif
runtime immediat: Lot 6 est trop large et contient plusieurs P2 independants.
Le meilleur plan sur est un triage docs-only, puis des sous-lots bornes.

Inventaire Lot 6A:

- Scan cible `str(exc)` / `repr(exc)` / `exc_info` / `traceback` / `print(`:
  plusieurs familles independantes existent encore dans `server.py`,
  `chat_llm_flow.py`, services admin, outils web, memoire et tests. Le scan
  invalide un remplacement global aveugle.
- Scan cible `raw` / `payload` / `url` / `hash` / `prompt`: beaucoup de
  mentions sont des champs de schema, flags defensifs ou tests. Les surfaces
  dashboard legacy et hashes identity restent a valider par fixture dediee.
- Tests cibles relances en conteneur:
  `tests.unit.memory.test_identity_periodic_agent_phase1`,
  `tests.test_server_chat_compact_observability_contract`,
  `tests.unit.logs.test_chat_turn_logger_hermeneutic_observability`.
  Resultat: echec reproduit, sans patch runtime dans ce lot.

Table de decision Lot 6A:

| Finding | Statut Lot 6A | Decision |
|---|---|---|
| `P2-CEL-LLM-ERROR-RAW-01` | `validated` | Lot 6B: remplacer les surfaces LLM brutes par `error_class` / `error_code` / message stable content-free. |
| `P2-CEL-EXCEPTION-RAW-SURFACE-01` | `validated_broad` | Ne pas corriger globalement; traiter par sous-surface seulement. |
| `P2-CEL-ADMIN-400-RAW-01` | `validated` | Lot 6C: admin 400/404 reason codes stables, tests sentinelles. |
| `P2-CEL-DASHBOARD-WEB-LEGACY-RAW-01` | `needs_targeted_validation` | Lot 6D: fixture historique dashboard, URL/hash content-free. |
| `P2-CEL-IDENTITY-HASH-POLICY-01` | `validated_policy_gap` | Lot 6E: doctrine et tests sur hashes courts identity avant patch runtime. |
| `P2-CEL-MUTABLE-IDENTITY-STAGING-TEST-FAILURES-01` | `validated_needs_surface_split` | Lot 6F: isoler garde observabilite vs contrat stale vs bug identity/memory. |
| `P2-CEL-STIMMUNG-PROMPT-GUARD-REJECTION-01` | `validated` | Lot 6G: reproduire payload local, corriger schema/test sans prompt brut. |
| `P2-CEL-COMPACT-OBSERVABILITY-MESSAGES-COUNT-01` | `validated_needs_contract_decision` | Lot 6H ou Lot 7 selon cause: projection/schema compacte ou drift de matrice. |

Decoupage recommande:

- Lot 6B - LLM errors content-free: `chat_llm_flow.py` et proxy LLM serveur,
  tests provider-error sentinelles, aucun payload provider brut.
- Lot 6C - Admin 400/404 raw: routes admin logs/dashboard/export/content,
  reason codes stables, pas d'echo de valeur invalide.
- Lot 6D - Dashboard web legacy raw URL/hash: fixture historique sentinelle,
  projection dashboard content-free.
- Lot 6E - Doctrine hashes identity: trancher `sha256_12` sur contenu
  identity/update_reason, puis patcher seulement si la doctrine l'exige.
- Lot 6F - Mutable identity staging failures: fake minimal pour separer rejet
  guard, contrat stale et bug cleanup buffer.
- Lot 6G - Stimmung prompt guard rejection: garde/schema payload pour
  `stimmung_prompt_prepared`, sans prompt brut.
- Lot 6H - Compact observability drift: `messages_count` et statut summary;
  deleguer au Lot 7 si c'est une rebaseline smoke/matrice, pas un bug schema.

Decision:

- Lot 6 parent reste ouvert: seul le triage Lot 6A est clos.
- Aucun runtime n'est corrige dans Lot 6A.
- Lot 7 `/log` denylist et Lot 9 refactors restent hors scope.

#### Lot 6B - Erreurs LLM content-free

Statut: execute le 2026-06-25.
Runtime modifie: oui, borne aux erreurs LLM.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le finding etait
borne a la frontiere LLM: reponses visibles `/api/chat`, events `llm_*` et
`message_short` turn logger.

- [x] Valider `P2-CEL-LLM-ERROR-RAW-01`.
- [x] Remplacer les reponses visibles `Connexion au LLM: <exception>` /
  `Erreur: <exception>` / erreur secret brute par des messages stables.
- [x] Conserver diagnostics content-free: `error_code`, `reason_code`,
  `error_class`.
- [x] Supprimer l'exception brute des events `llm_error`, `llm_stream_error`,
  `llm_stream_finalize_error` et du `message_short` turn logger LLM.
- [x] Ajouter tests sentinelles URL/query, header auth synthetique, path synthetique
  et payload provider sentinelle.
- [x] Ne pas traiter Lot 6C/6D/6E/6F/6G/6H, Lot 7 ni Lot 9.

Resultat Lot 6B:

- `P2-CEL-LLM-ERROR-RAW-01` est clos.
- Les erreurs provider/LLM restent diagnostiquables sans contenu brut:
  `llm_upstream_error`, `llm_secret_resolution_error`,
  `llm_internal_error`, `llm_stream_finalize_error`.
- Les `str(exc)` restants dans `server.py` correspondent aux surfaces hors
  scope deja deleguees, notamment Lot 6C admin 400/404 et Lot 6 global par
  sous-surface.

#### Lot 6C - Admin 400/404 raw

Statut: execute le 2026-06-25.
Runtime modifie: oui, borne aux reponses admin logs/dashboard/export.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le finding etait
borne aux routes admin `server.py` qui transformaient `ValueError` /
`LookupError` en `error: str(exc)` sur 400/404.

- [x] Valider `P2-CEL-ADMIN-400-RAW-01`.
- [x] Remplacer les 400 admin brutes des surfaces chat logs metadata/turns/
  metrics/delete/export par `admin_bad_request` + reason code stable.
- [x] Remplacer les 400/404 dashboard brutes par `admin_bad_request` /
  `admin_not_found` + reason code stable.
- [x] Ajouter tests sentinelles avec URL/query, path prive synthetique,
  token-like synthetique et payload raw synthetique.
- [x] Conserver les statuts HTTP existants 400/404.
- [x] Ne pas traiter Lot 6D/6E/6F/6G/6H, Lot 7 ni Lot 9.

Resultat Lot 6C:

- `P2-CEL-ADMIN-400-RAW-01` est clos pour les routes admin logs/dashboard/
  export/content de `server.py`.
- Les reponses admin 400/404 restent diagnostiquables via `error_code` et
  `reason_code`, sans echo de valeur invalide ni exception brute.
- Les `str(exc)` restants dans `app/admin/*` ne sont pas corriges par ce lot:
  ils relevent des contrats settings/services ou du finding large
  `P2-CEL-EXCEPTION-RAW-SURFACE-01`, a traiter seulement par sous-surface
  dediee.

#### Lot 6D - Dashboard web legacy raw URL/hash

Statut: execute le 2026-06-25.
Runtime modifie: oui, borne a la projection dashboard Web.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le finding etait
assez borne apres Lot 6A: il fallait valider les projections dashboard Web
plutot que remplacer globalement les champs `url`, `hash`, `raw` ou `payload`.

- [x] Valider `P2-CEL-DASHBOARD-WEB-LEGACY-RAW-01`.
- [x] Supprimer du fact dashboard Web les URL brutes et hashes courts
  historiques de requete/crawl.
- [x] Conserver des diagnostics content-free: presence URL, longueurs,
  compteurs, statuts crawl/cache/policy.
- [x] Ajouter une fixture sentinelle dashboard avec URL/query/hash
  synthetiques dangereux.
- [x] Ne pas traiter Lot 6E/6F/6G/6H, Lot 7 ni Lot 9.

Resultat Lot 6D:

- `app/observability/turn_pipeline_read_model.py::_web_summary()` ne projette
  plus `url`, `query_sha256_12`, `crawl4ai_query_sha256_12` ni
  `crawl_query_sha256_12` dans le fact dashboard Web.
- Les diagnostics utiles restent disponibles via `url_present`, `url_chars`,
  `query_present`, `query_chars`, `crawl_query_chars` et
  `crawl4ai_query_count`.
- Le test `test_dashboard_web_projection_drops_legacy_url_query_and_hash_values`
  couvre le cas historique avec sentinelles synthetiques et verifie l'absence
  de fuite dans le JSON dashboard projete.

#### Lot 6E - Doctrine hashes courts identity

Statut: execute le 2026-06-25.
Runtime modifie: oui, borne aux surfaces identity observabilite/admin/read-model.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le finding etait
valide et les surfaces confirmees relevaient toutes de la meme doctrine:
hashes courts stables sur texte identity/mutable/update_reason. Le patch le
plus sur etait de supprimer ces empreintes dans les projections traitees et de
conserver les diagnostics par presence/longueurs/compteurs/statuts.

- [x] Valider `P2-CEL-IDENTITY-HASH-POLICY-01`.
- [x] Supprimer `identity_block_sha256_12`, les `sha256_12` de couches
  static/mutable et `update_reason_sha256_12` du payload
  `identity_prompt_injection`.
- [x] Supprimer `sha256_12` de la projection dashboard identity.
- [x] Supprimer `old_sha256_12`, `new_sha256_12` et
  `proposition_sha256_12` des outcomes/audits/projections mutable identity.
- [x] Supprimer les hashes courts des fragments/evidence/conflicts identity
  legacy dans le read-model admin.
- [x] Remplacer les annotations textuelles libres du juge mutable par
  `present` + `chars`.
- [x] Garder les diagnostics content-free: presence, longueurs, compteurs,
  statuts/reason codes, IDs opaques.
- [x] Ne pas purger ni migrer l'historique: colonnes SQL historiques conservees
  pour compatibilite, nouveaux writes a `NULL`, read-models sans exposition.
- [x] Ne pas traiter Lot 6F/6G/6H, Lot 7 ni Lot 9.

Resultat Lot 6E:

- `P2-CEL-IDENTITY-HASH-POLICY-01` etait clos trop tot: un contre-audit a
  confirme des restes dans `identity-candidates`, un libelle runtime et trois
  specs actives. Ces restes sont traites en Lot 6E.1 ci-dessous.
- La garde observabilite refuse explicitement les anciens champs
  `identity_block_sha256_12` et `update_reason_sha256_12`.
- Les tests cibles prouvent que les payloads identity reels restent acceptes
  sans hash court stable et que les anciennes valeurs/hash sentinelles ne
  ressortent pas dans les projections admin/dashboard concernees.
- Les surfaces de hash hors identity, par exemple documents actifs,
  hermeneutique ou memoire durable, restent hors scope de ce lot.

#### Lot 6E.1 - Correctif hashes identity restants

Statut: execute le 2026-06-25.
Runtime modifie: oui, borne a `/api/admin/hermeneutics/identity-candidates`
et au libelle du read-model identity.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Les trois findings
etaient confirmes dans l'etat courant et relevaient du meme correctif de
cloture Lot 6E sans migration ni refactor.

- [x] Valider et corriger la route active
  `/api/admin/hermeneutics/identity-candidates`: retrait de
  `content_sha256_12`, `content_norm_sha256_12`, `reason_sha256_12` et
  `override_note_sha256_12`.
- [x] Conserver les diagnostics content-free sur cette route:
  `content_present`, `content_chars`, `content_norm_present`,
  `content_norm_chars`, `reason_code`, `reason_present`, `reason_chars`,
  `override_note_code`, `override_note_present`, `override_note_chars`,
  statuts, subject, IDs opaques, timestamps et metadonnees.
- [x] Aligner le libelle runtime `observability_contract` sur
  `content_free_counts_status_reasons_lengths_timestamps`.
- [x] Aligner les specs actives `identity-surface-contract.md`,
  `dashboard-long-term-observability-contract.md` et
  `identity-read-model-contract.md`.
- [x] Ne pas purger ni migrer l'historique; ne pas modifier le contrat
  d'edition canonique static/mutable.
- [x] Ne pas traiter Lot 6F/6G/6H, Lot 7 ni Lot 9.

Resultat Lot 6E.1:

- `P2-CEL-IDENTITY-HASH-POLICY-01` est clos apres correction des restes.
- Les tests sentinelles calculent les anciens hashes courts synthetiques et
  verifient qu'ils ne ressortent pas dans la reponse `identity-candidates`.
- Les specs vivantes disent desormais que les surfaces identity diagnostiques
  gardent presence, longueurs, compteurs, statuts, reason codes, IDs opaques et
  timestamps, sans hash court stable sur texte identity/reason libre.

#### Lot 6E.2 - Versions de projection identity

Statut: execute le 2026-06-25.
Runtime modifie: oui, borne aux constantes `projection_version` identity.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le fond Lot 6E/6E.1
etait correct, mais les noms de projection `v1` restaient stale apres retrait
des champs `*_sha256_12`.

- [x] Valider `P3-IDENTITY-CANDIDATES-PROJECTION-VERSION-STALE`.
- [x] Bumper la projection candidates vers
  `identity_candidates_content_minimized_v2`.
- [x] Valider `P3-IDENTITY-LEGACY-PROJECTION-VERSION-STALE`.
- [x] Bumper la projection legacy vers
  `identity_legacy_content_minimized_v2`.
- [x] Adapter les tests de contrat route/read-model.
- [x] Ne pas reintroduire de hash, ne pas modifier les contenus identity, ne pas
  traiter Lot 6F/6G/6H, Lot 7 ni Lot 9.

Resultat Lot 6E.2:

- Les versions de projection correspondent maintenant au schema sans hash court
  stable sur texte identity/reason.
- Les specs actives ne mentionnaient pas ces identifiants de version; aucune
  modification supplementaire de spec n'etait necessaire.

#### Lot 6F - Mutable identity staging failures

Statut: execute le 2026-06-25.
Runtime modifie: oui, borne a la garde observabilite writer-side mutable
identity. Tests fixtures alignes, sans changement de contenu identity canonique.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le bon plan etait de
reproduire la suite cible, classifier chaque ecart, puis corriger uniquement la
garde content-free confirmee et les fixtures stale.

- [x] Reproduire `tests.unit.memory.test_identity_periodic_agent_phase1` en
  conteneur avant patch: 8 echecs confirmes.
- [x] Classer `guard_rejection`: payloads `mutable_identity_judge`
  content-free legitimes refuses par la garde, avec
  `observability_payload_rejected`.
- [x] Classer `test_contract_stale`: plusieurs fixtures de succes utilisaient
  encore des propositions non conformes au contrat ontologique v2.
- [x] Invalider `buffer_cleanup_bug`: le buffer retry restait plein parce que
  la seconde tentative utilisait une fixture stale devenue
  `non_ontological_proposition`; le cleanup runtime est conforme avec une
  proposition v2 valide.
- [x] Invalider `runtime_identity_bug` pour ce lot: le runtime conserve les
  reason codes utiles (`invalid_verdict`, `non_ontological_proposition`) et
  preserve le buffer sur invalidation reelle.
- [x] Autoriser dans la garde seulement les champs compacts deja attendus pour
  `mutable_identity_judge`: pipeline, statuts/reason codes, flags buffer/write,
  compteurs, listes de codes/sujets et outcomes reduits aux metadonnees.
- [x] Ne pas accepter contenu identity brut, proposition, prompt, payload
  provider, token/cookie/DSN/secret.
- [x] Ne pas traiter Lot 6G/6H, Lot 7 ni Lot 9.

Resultat Lot 6F:

- `P2-CEL-MUTABLE-IDENTITY-STAGING-TEST-FAILURES-01` est clos.
- La garde writer-side ne remplace plus un event mutable identity legitime par
  `observability_payload_rejected`; le reason code utile reste visible.
- Les tests stale sont alignes sur le contrat v2 sans relacher la validation
  ontologique runtime.
- Les buffers restent preserves sur erreur reelle et sont bien nettoyes apres
  retry reussi.

#### Lot 6F.1 - Correction ciblee du rejet de garde arbiter

Statut: execute le 2026-06-25.
Runtime modifie: oui, borne au schema writer-side observabilite.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le rejet etait
reproduit et le probe de garde isolait deux compteurs manquants; un patch
schema/tests cible etait plus sur qu'un relachement global de la garde.

- [x] Reproduire `tests.unit.logs.test_chat_turn_logger_phase2` en conteneur:
  deux erreurs avec `chat_turn_log_payload_rejected stage=arbiter`.
- [x] Valider `P2-CEL-ARBITER-PAYLOAD-GUARD-REJECTION-01`.
- [x] Autoriser uniquement les compteurs arbiter compacts manquants:
  `rejected_candidates` et `fallback_decisions`.
- [x] Conserver `raw_candidates` comme compteur entier, sans permettre liste
  ou string de contenu candidat.
- [x] Conserver `rejection_reason_code_counts` comme map de compteurs
  content-free.
- [x] Ajouter sentinelles refusant `candidate_content`, `candidates`,
  `prompt`, URL brute et payload provider brut.
- [x] Ne pas traiter Lot 6G/6H, Lot 7 ni Lot 9.

Resultat Lot 6F.1:

- Le payload compact `stage=arbiter` est accepte par la garde writer-side.
- Les compteurs et reason codes arbiter utiles restent disponibles.
- Les payloads dangereux restent refuses et redacted.
- `P2-CEL-ARBITER-PAYLOAD-GUARD-REJECTION-01` est clos.

#### Lot 6G - Correction du rejet de garde stimmung_prompt_prepared

Statut: execute le 2026-06-25.
Runtime modifie: oui, borne au schema writer-side observabilite.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le rejet etait
reproduit et le probe de garde sur le payload genere isolait trois cles
content-free manquantes; un patch schema/tests cible etait plus sur qu'un
relachement global de la garde.

- [x] Reproduire
  `test_stimmung_prompt_prepared_emits_provider_secondary_fingerprint_without_raw_payload`
  en conteneur: event `stimmung_prompt_prepared` en `refused` avec
  `observability_payload_rejected`.
- [x] Valider `P2-CEL-STIMMUNG-PROMPT-GUARD-REJECTION-01`.
- [x] Autoriser uniquement `stimmung_status`,
  `recent_has_in_progress_turn` et `recent_max_turns`.
- [x] Conserver les diagnostics content-free: compteurs messages/roles,
  presence et tailles prompt/user, stats recent window, sampling.
- [x] Ajouter sentinelles refusant prompt brut, message brut, payload provider
  brut et URL brute.
- [x] Ne pas traiter Lot 6H, Lot 7 ni Lot 9.

Resultat Lot 6G:

- Le payload compact `stage=stimmung_prompt_prepared` est accepte par la garde
  writer-side.
- Les diagnostics provider secondary restent disponibles sans prompt/message
  brut.
- Les payloads dangereux restent refuses et redacted.
- `P2-CEL-STIMMUNG-PROMPT-GUARD-REJECTION-01` est clos.

#### Lot 6H - Compact observability drift messages_count / summary status

Statut: execute le 2026-06-25.
Runtime modifie: non.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le bon plan etait de
reproduire la suite cible, isoler l'event compact, puis corriger seulement le
contrat de test si le runtime etait coherent.

- [x] Reproduire `tests.test_server_chat_compact_observability_contract` en
  conteneur: un seul echec restant sur `prompt_prepared.messages_count`.
- [x] Requalifier le volet summary: `summary.status=missing` passe deja dans
  la suite cible et reste le contrat attendu pour absence normale de summary.
- [x] Isoler `prompt_prepared.messages_count`: le payload compact expose
  `len(messages)` recu par `_LLMChatLogProxy.build_payload()`.
- [x] Prouver content-free que le payload LLM du scenario contient deux
  messages (`user`, `system`) et que `messages_count=2` est donc l'etat produit
  attendu.
- [x] Aligner le test sur le contrat reel sans modifier le runtime.
- [x] Ne pas traiter Lot 7 ni Lot 9.

Resultat Lot 6H:

- `P2-CEL-COMPACT-OBSERVABILITY-MESSAGES-COUNT-01` est clos comme
  `test_stale`.
- `messages_count` reste le nombre de messages remis au provider LLM, pas le
  nombre initial de messages retourne par la fixture `build_prompt_messages`.
- `summary.status=missing` est confirme comme comportement attendu en absence
  normale de summary.

#### Lot 6I - Exception raw surfaces restantes

Statut: execute le 2026-06-25.
Runtime modifie: oui, borne aux surfaces exception raw restantes.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le meilleur plan etait
de rescanner les hits `str(exc)` / `repr(exc)` / `message_short`, corriger
uniquement les sorties confirmees, et requalifier explicitement les usages
internes sans remplacement global.

- [x] Valider les surfaces confirmees restantes:
  `/api/chat` catch-all, Web Search `message_short`, settings admin,
  Memory Admin `read_errors`, admin logs conversations/restart et governance
  identity.
- [x] Remplacer les textes d'exception bruts par `error_code`, `reason_code`,
  `error_class`, messages stables et flags `raw_error_message_included=false`.
- [x] Durcir les details de validation runtime secrets: les checks admin
  exposent le champ et la classe d'erreur, pas le texte brut.
- [x] Ajouter tests sentinelles URL/token synthetiques pour settings,
  governance, conversations, Memory Admin et Web Search.
- [x] Requalifier les hits restants du scan sans patch:
  `runtime_settings_repo.py` / `runtime_settings_write_path.py` /
  `runtime_secrets.py` sont des propagations internes maintenant sanitisees
  par les responses settings et les checks de validation; les probes
  `purpose not in str(exc)` et `unexpected keyword` sont des compatibilites
  test-double; `validation_agent.py` / `stimmung_agent.py` bornent les
  exceptions JSON/payload en reason codes internes; `active_document_text_extraction.py`
  n'utilise que des exceptions internes avec warnings stables
  (`pdf_page_without_text`, `pypdf_unavailable`) ou la classe d'erreur.
- [x] Ne pas traiter Lot 7 `/log` denylist ni Lot 9 refactors.

Resultat Lot 6I:

| Surface | Decision |
|---|---|
| `app/server.py:823` | Corrige: `emit_error()` recoit un message stable, plus `str(exc)`. |
| `app/tools/web_search.py:2452,2641` | Corrige: les erreurs Web utilisent le reason code stable; fallback `emit_error()` ne derive plus de la query. |
| `app/admin/admin_settings_service.py` | Corrige: 400/503 settings exposent `runtime_settings_validation_error` / `runtime_settings_unavailable`, pas `str(exc)`. |
| `app/admin/runtime_settings_validation.py` | Corrige: details de secret runtime content-free par champ + classe. |
| `app/admin/admin_memory_service.py` | Corrige: `read_errors` garde section, codes et classe, sans message brut. |
| `app/core/conversations_store.py` / `app/core/conversations_maintenance.py` / `app/admin/admin_actions.py` | Corrige: logs admin et logs applicatifs remplacent l'erreur brute par codes + classe. |
| `app/admin/admin_identity_governance_service.py` | Corrige: reponses governance identity stables sans exception brute. |
| Hits internes restants hors logs runtime `err=%s` | Invalides pour Lot 6I: propagation interne, compat, ou reason codes/warnings bornes sans surface brute confirmee. |
| Logs runtime `err=%s` restants | Non clos par Lot 6I: a qualifier par famille en Lot 6J avant cloture complete du P2 large. |

Decision:

- `P2-CEL-EXCEPTION-RAW-SURFACE-01` est partiellement clos apres Lot 6I:
  `partially_closed_by_lot_6I_needs_log_surface_requalification`.
- Lot 6B a traite LLM; Lot 6C admin 400/404; Lot 6D dashboard Web; Lot 6E
  hashes identity; Lot 6F/6F.1/6G/6H observabilite compacte/garde. Lot 6I
  ferme le reliquat expose `str(exc)` / `message_short` sans absorber Lot 7 ni
  Lot 9.
- Restent ouverts pour Lot 6J: logs runtime `logger.*("... err=%s", exc)` par
  famille (`app/server.py`, `app/memory/memory_traces_summaries.py`,
  `app/core/conversations_store.py`, `app/memory/arbiter.py`, autres hits de
  scan) afin de distinguer logs internes acceptables et surfaces durables a
  durcir.
- Les warnings observabilite `chat_turn_log_payload_rejected` vus dans les
  suites stream LLM deviennent le finding dedie
  `P2-CEL-OBSERVABILITY-PAYLOAD-REJECTED-STREAM-01`: Lot 6J si rejet
  writer-side confirme, Lot 7 si matrice/smoke/projection finale.

#### Lot 6J - Requalification logs runtime err=%s et rejets stream

Statut: execute le 2026-06-26.
Runtime modifie: oui, borne a la garde observabilite stream et au payload
`persist_response`.
Plateforme modifiee: non.

- [x] Requalifier par famille les logs runtime `logger.*("... err=%s", exc)`
  encore presents apres Lot 6I.
- [x] Distinguer logs internes defensifs acceptables, logs durables lisibles,
  projections admin/dashboard et reponses HTTP.
- [x] Corriger uniquement les familles confirmees comme surface brute durable ou
  visible; conserver `error_class`, `reason_code` et diagnostics content-free.
- [x] Valider `P2-CEL-OBSERVABILITY-PAYLOAD-REJECTED-STREAM-01`.
- [x] Ne pas traiter Lot 7 `/log` denylist ni Lot 9 refactors dans ce lot.

Question pre-action: existe-t-il un meilleur plan ? Non. Le bon plan etait de
reproduire les rejets stream, isoler les cles refusees par la garde, puis
qualifier les logs `err=%s` par famille sans remplacement global.

Inventaire Lot 6J:

| Famille | Classification | Decision |
|---|---|---|
| `/api/chat` stream `llm_call` | `needs_redaction` confirme | Corrige: `stream_chunks` compteur et `stream_terminal` code compact acceptes par la garde; valeurs dangereuses restent refusees. |
| `/api/chat` stream `persist_response` | `needs_redaction` confirme | Corrige: `reason` libre remplace par `reason_code` stable dans le payload primaire. |
| Logs bootstrap/runtime settings `app/server.py` | `safe_internal_log` | Logs operateur internes uniquement; pas de reponse HTTP/admin ni payload observabilite. Pas de patch Lot 6J. |
| Logs DB/stores conversations/memoire/identity | `safe_internal_log` | Logs applicatifs internes avec identifiants techniques et exceptions; pas de surface publique/projection/export confirmee. Pas de patch global. |
| Branches deja en `err_class` / reason codes | `content_free_already` | Aucun patch: diagnostics deja bornes, notamment plusieurs chemins LLM, conversations maintenance, prompt lanes et services recents. |
| Compat tests `purpose not in str(exc)` / `unexpected keyword` | `test_only` | Aucun patch runtime: compatibilites de doubles de tests deja requalifiees par Lot 6I. |
| Warnings actifs post-V1 hors surfaces exposees | `out_of_scope_post_v1` | Hygiene future possible si l'operateur veut redacter aussi les logs internes conteneur, mais pas bloquant pour le P2 public/admin. |

Resultat Lot 6J:

- `P2-CEL-EXCEPTION-RAW-SURFACE-01` est clos comme
  `closed_by_lot_6J_internal_logs_requalified`: les surfaces exposees ont ete
  corrigees en Lots 6B-6I, et les logs `err=%s` restants sont qualifies comme
  internes/non publics ou hors scope post-V1.
- `P2-CEL-OBSERVABILITY-PAYLOAD-REJECTED-STREAM-01` est clos: les rejets
  `llm_call` / `persist_response` stream ne se reproduisent plus apres patch.
- Probe Lot 6J avant Lot 6J.1: `stream_rejection_count=0`; les deux rejets
  restants `chat_response` observes dans la suite route sont non-stream et
  deviennent le finding dedie Lot 6J.1.
- Lot 7 `/log` denylist et Lot 9 refactors restent non absorbes.

#### Lot 6J.1 - Micro-correctif chat_response payload rejected non-stream

Statut: execute le 2026-06-26.
Runtime modifie: oui, borne a `chat_turn_logger.emit_refusal()`.
Plateforme modifiee: non.

- [x] Valider
  `P2-CEL-OBSERVABILITY-PAYLOAD-REJECTED-CHAT-RESPONSE-01`.
- [x] Supprimer le texte libre `reason_short` du payload primaire
  `chat_response`.
- [x] Conserver les diagnostics content-free: `reason_code`,
  `reason_short_chars`, `reason_short_included=False`.
- [x] Ne pas relacher la garde writer-side et ne pas traiter Lot 7 ou Lot 9.

Question pre-action: existe-t-il un meilleur plan ? Non. Le rejet est local:
`emit_refusal()` emettait un texte court libre (`chat status 400`) sous une cle
que la garde traite comme code safe-only. Le correctif le plus borne est donc
d'aligner `emit_refusal()` sur la logique `emit_error()` sans allowlist de texte
libre.

Resultat Lot 6J.1:

- Finding valide: probe pre-patch `accepted=False`,
  `issue_classes=['unsafe_string_value']` pour le payload
  `reason_short="chat status 400"`.
- Correctif: `chat_response` conserve son `status` (`refused` /
  `not_applicable`) et son `reason_code`, mais ne stocke plus la phrase courte.
- Preuve apres patch: payload content-free `reason_short_chars` /
  `reason_short_included=False` accepte par la garde, `has_reason_short=False`,
  `chat_response_rejection_count=0` sur les tests cibles; le texte
  `chat status 400` n'est plus present dans les payloads.
- Limite: Lot 7 `/log` denylist et Lot 9 refactors restent ouverts et non
  absorbes.

### Lot 7 - Tests/smokes/artefacts

- [x] Construire matrice live/fake/mock/covered_by_tests.
- [x] Requalifier le test conflit final-lock Agenda/Biblio: pas de nouveau
  conflit confirme en Lot 7; golden tests d'ordre a garder en Lot 9 avant
  refactor orchestration.
- [x] Revalider tests panels frontend erreur vs vide.
- [x] Remplacer la denylist payload `/log` par allowlist content-free et ajouter
  test sentinelle champ inconnu.
- [x] Verifier JSONL et anti-fuite.
- [x] Gerer fixtures secret-like par sentinelles synthetiques documentees.

Note Lot 6H: `P2-CEL-COMPACT-OBSERVABILITY-MESSAGES-COUNT-01` est revalide
et clos en Lot 6H; il n'est plus une tache Lot 7 et ne requiert pas de
smoke/matrice globale.

Statut Lot 7: execute le 2026-06-26.
Runtime modifie: oui, borne a `app/web/log/log.js`.
Plateforme modifiee: non.

Question pre-action: existe-t-il un meilleur plan ? Non. Le bon plan etait de
valider d'abord `/log`: la route admin projette deja les payloads en
content-free, mais la UI restait en denylist locale. Le correctif minimal est
donc une allowlist frontend explicite plus une sentinelle browser, sans refactor
admin logs ni Lot 9.

Inventaire Lot 7:

| Surface | Decision | Preuve |
|---|---|---|
| `/log` UI active | `met` | Route `/log` active; endpoints `/api/admin/logs/chat*`; projection backend `admin_log_event_projection_v1`. |
| `/log` payload entries | `met` | Allowlist frontend content-free; sentinelle browser champ inconnu / `prompt` / `content` non rendue. |
| Admin logs read/projection | `covered_by_tests` | `tests.test_server_admin_chat_logs_contract`, `tests.integration.frontend_admin.test_frontend_logs_phase5`. |
| Chat non-stream/stream | `covered_by_tests` | `tests.test_server_chat_agentic_observability_contract`, `tests.test_server_chat_route_transport_contract`, `tests.unit.chat.test_chat_llm_flow`. |
| Manifest / Continuity Capsule | `covered_by_tests` | `tests.unit.logs.test_main_payload_manifest`. |
| Panels Notes/Documents/Exports/Images | `covered_by_tests` | `node --test app/tests/unit/frontend_chat/*.js` (118 tests). |
| Agenda / Biblio | `covered_by_tests` | Suites Agenda/Biblio contractuelles fake/local. |
| Rejets observabilite inattendus | `met` | `payload_rejected_unexpected_count=0`, `chat_response_rejection_count=0`, `stream_rejection_count=0` sur les suites cibles. |
| Browser full smoke global | `accepted_with_documented_limit` | Suite globale browser hote bloquee avant `/log` sur timeouts image-generation hors scope; scenario `/log` cible passe. |

Matrice finale Lot 7:

| Domaine | Classification | Decision |
|---|---|---|
| Securite plateforme serveur solo | `met` | Lot 3: aucun P0/P1 public; frontiere Caddy/Authelia verifiee. |
| Updates serveur/services/images | `accepted_with_documented_limit` | Lot 3B: pas d'update securite critique bloquante; updates reelles restent lots separes. |
| Code runtime P1/P2 | `met` | Lots 4A-4E: P2 bornes corriges/requalifies; dette structurelle reportee Lot 9. |
| Admin/security/app routes | `met` | Lots 5A-5D: guard admin, prompts, Notes, panels, compat knobs traites. |
| Observabilite/logs applicatifs | `met` | Lots 6A-6J.1: P2 raw/garde/projection corriges ou requalifies. |
| `/log` denylist | `met` | Lot 7: allowlist payload frontend + projection backend + sentinelle browser. |
| Lot 9 refactors | `post_v1` | Refactors structurels ouverts; golden tests requis avant extraction. |
| Backups stack Sauron | `accepted_with_documented_limit` | Scope Sauron separe; aucun chmod/purge sans nouveau GO operateur. |

Artefact Lot 7:

- `app/docs/states/baselines/mega-audit-smokes/frida-v1-mega-audit-lot7-smoke-20260626T080759Z.jsonl`
- Format: JSONL content-free, statuts/reason codes/compteurs/commandes, aucun
  log brut, prompt, payload externe ni valeur sensible runtime.

Resultat Lot 7:

- `P3-CEL-LOG-FRONTEND-DENYLIST-01` est clos par allowlist UI + test sentinelle.
- `P3-CEL-TEST-PROOF-MAPPING-01` est clos par matrice Lot 7 + artefact JSONL.
- `P3-CEL-SECRET-LIKE-FIXTURES-01` est accepte avec limite documentee:
  sentinelles synthetiques explicites, pas de secret runtime ajoute.
- `P3-CEL-FINAL-LOCK-CONFLICT-TEST-01` est requalifie vers Lot 9 golden tests
  si refactor orchestration; aucun conflit runtime nouveau confirme par Lot 7.
- Lot 9 et Lot Z restent non coches.

#### Lot 7.1 - Micro-correctif `/log` token-like safe-code

Statut: execute le 2026-06-26.
Runtime modifie: oui, borne a la garde observabilite, projection admin logs et
defense frontend `/log`.
Plateforme modifiee: non.

- [x] Valider `P2-CEL-LOG-SAFECODE-TOKENLIKE-01`: une valeur token-like
  synthetique sous `reason_code` passait la garde writer-side, la projection
  admin et le rendu `/log`.
- [x] Refuser les safe-codes token-like evidents dans la garde writer-side sans
  bloquer `skipped`, `provider_timeout` ni les reason codes snake_case normaux.
- [x] Redacter les valeurs token-like dans la projection admin et dans `/log`
  comme defense secondaire.
- [x] Ajouter sentinelles garde/projection/browser prouvant que les champs
  `prompt`, `content`, URL/query et valeurs token-like synthetiques ne sont pas
  rendus.
- [x] Ne pas cocher Lot 9 ni Lot Z.

Resultat Lot 7.1:

- `P2-CEL-LOG-SAFECODE-TOKENLIKE-01` est clos par defense en profondeur sur les
  safe-codes token-like evidents.
- Le contrat `/log` reste content-free: valeurs normales affichees, valeurs
  token-like synthetiques redacted, aucun secret runtime ni prompt brut ajoute.

#### Lot 7.2 - Correction token-like safe-code variants

Statut: execute le 2026-06-26.
Runtime modifie: oui, borne a la garde observabilite, projection admin logs et
defense frontend `/log`.
Plateforme modifiee: non.

- [x] Valider `P2-CEL-LOG-SAFECODE-TOKENLIKE-VARIANTS-01`: les variantes
  token-like synthetiques avec underscore ou prefixes provider passaient encore
  sous `reason_code`.
- [x] Etendre la detection aux variantes `sk_live*`, `sk_or*`, `ghp_*`, `hf_*`
  et `xoxb-*`, sans bloquer les underscores ordinaires.
- [x] Prouver que `skipped`, `provider_timeout`, `llm_call_ok` et
  `openai/gpt-5.4-mini` restent acceptes/rendus.
- [x] Conserver Lot 9 et Lot Z non coches.

Resultat Lot 7.2:

- `P2-CEL-LOG-SAFECODE-TOKENLIKE-VARIANTS-01` est clos.
- Garde writer-side, projection admin et `/log` appliquent la meme defense
  token-like sur les variantes synthetiques confirmees.


#### Lot 7.3 - Incident frontend chat / bindings globaux Notes

Statut: hotfix execute le 2026-06-26.
Runtime modifie: oui, borne au frontend chat.
Plateforme modifiee: non.

- [x] Reproduire la casse navigateur: plus de sidebar/dossiers/boutons agentiques
  ni initialisation chat apres erreur JS.
- [x] Identifier la cause exacte: declaration top-level dupliquee
  `WorkspaceFolderNotesPanel` dans deux scripts navigateur non-module.
- [x] Corriger le script inutilement redeclarant le binding global, sans refactor
  Notes ni changement backend.
- [x] Ajouter une regression test empechant une double declaration du binding
  Notes panel.
- [x] Rejouer le smoke navigateur chat nominal/error/conversations qui avait
  echoue avant patch.

Resultat Lot 7.3:

- L'initialisation frontend chat est restauree: `chat_threads_sidebar.js` peut
  de nouveau exposer `window.FridaChatThreadsSidebar`, puis `app.js` charge les
  dossiers, conversations, modes agentiques et le chat.
- Tests obligatoires a conserver pour tout futur patch frontend chat/Notes:
  `node --test app/tests/unit/frontend_chat/*.js` et smoke browser cible
  `chat stream nominal|chat stream error|conversation`.
- Aucun service plateforme, DB, Caddy ou Authelia n'est modifie.

### Lot 8 - Docs/source-of-truth

- [x] Reclasser audits superseded encore en `todo-todo/audits`.
- [x] Clarifier checkboxes historiques.
- [x] Corriger `/opt/platform/AGENTS.md` admin token stale, sans runtime.
- [x] Maintenir la distinction runtime Agenda implemente / roadmap Agenda
  post-V1 dormante dans les futurs index docs.
- [x] Clarifier commentaires Biblio stale.
- [x] Trancher doctrine filenames content-free/metadonnees produit.
- [x] Mettre a jour index si chemins bougent.

Resultat Lot 8:

- Audit index ajoute: `app/docs/todo-todo/audits/README.md` classe la TODO
  canonique active, les pieces source/counter du mega-audit courant et les
  audits superseded conserves provisoirement jusqu'a Lot Z.
- Aucun deplacement de fichier: les pointeurs ne changent pas; `app/docs/README.md`
  reference l'index d'audits pour eviter les fausses taches actives.
- `/opt/platform/AGENTS.md` corrige hors depot FridaDev: plus de ligne
  presentant un token admin comme requis ni "Authelia + token" comme doctrine
  admin OVH.
- Agenda: les index actifs conservent la distinction runtime V1
  implemente/cable/activable vs roadmap large post-V1 dormante.
- Biblio: docs/index alignes sur agent bibliothecaire borne et doctrine
  deterministe-murs / LLM-bibliothecaire, sans reouvrir Biblio ni Lot 9.
- Filenames: doctrine explicite ajoutee dans `app/docs/README.md`.
- Lot 9 et Lot Z restent ouverts.

### Lot 9 - Refactors cibles

Statut: ferme le 19 aout 2026; roadmap dediee archivee apres 9Z.

- [x] Executer readiness audit docs-only Lot 9.
- [x] Creer TODO canonique dediee:
  `app/docs/todo-done/refactors/frida-v1-mega-audit-lot9-refactors-todo.md`.
- [x] Definir `Lot 9.0 - golden test harness / preuve avant refactor`.
- [x] Decouper les refactors par responsabilite reelle: server routes,
  chat orchestration, web search, observabilite, frontend, Agenda, Biblio,
  Memory/Admin.
- [x] Executer Lot 9.0 avant toute extraction runtime.
- [x] Executer les sous-lots 9A-9H uniquement apres golden tests prealables.
- [x] Refuser refactor cosmetique sans reduction de risque.

Resultat readiness historique Lot 9:

- Audit cree:
  `app/docs/states/audits/frida-v1-mega-audit-lot9-refactor-readiness-2026-06-26.md`.
- TODO canonique creee:
  `app/docs/todo-done/refactors/frida-v1-mega-audit-lot9-refactors-todo.md`.
- A cette etape historique, aucun runtime n'etait modifie et seuls l'audit
  preparatoire et la planification granulaire etaient termines.
- Le Lot 10G ajoute au meme backlog la baseline statique courante et la matrice
  exhaustive des hotspots de la seconde passe. Il ne lance aucun sous-lot et
  confirmait alors 9.0 comme seul prochain lot executable.

Resultat final Lot 9:

- 9.0 et toutes les familles 9A a 9H sont fermees par des goldens prealables,
  des micro-lots bornes, des commits distincts pousses et une baseline finale
  hermetique de `2665 tests`, sans echec ni erreur;
- aucun P1/P2 comportemental attribuable aux refactors ne reste ouvert et
  aucune capacite produit n'a ete ajoutee;
- les coordinateurs encore coherents sont classes `accepted_limit`; la
  campagne benchmark Identity legacy et les travaux Agenda/Catalogue live sont
  `post_v1`; la validation qualitative dialogique et ce registre `Lot Z`
  restent `needs_operator_decision` hors de la roadmap structurelle;
- la decision d'arret 9Z et les preuves detaillees sont archivees dans
  `app/docs/todo-done/refactors/frida-v1-mega-audit-lot9-refactors-todo.md`;
- aucun merge, rebuild, restart ou deploiement n'est execute par 9Z. Le
  `Lot Z - Cloture mega-audit` ci-dessous reste integralement ouvert et
  distinct.

### Lot 10 - Remediation de la seconde passe code-only

Statut: ferme le 2026-07-22; TODO dediee archivee apres Lot 10G.
Agent: Celebrimbor uniquement.
Audit source:
`app/docs/states/audits/frida-v1-mega-audit-code-only-2026-07-15.md`.
Archive dediee:
`app/docs/todo-done/audits/frida-v1-mega-audit-code-only-remediation-2026-07-15-todo.md`.

La seconde passe historique a initialement rapporte cinq P2 et trois P3 dans le
code applicatif au HEAD `afdf19fa54c6a1602232e54e40bb23a6ba33787d`. La
decision produit explicite du 2026-07-16 requalifie ensuite le signal sur les
logs serveur prives identity/memory en non-finding dans le contexte courant:
leur visibilite existante est intentionnelle pour l'unique
utilisateur-operateur. Cette decision n'est pas un lot, n'autorise aucun nouveau
log, contenu, export, collecte ou surface, ne couvre aucun secret et ne
requalifie pas les exceptions brutes. La remediation active contient donc
quatre P2 et trois P3, ordonnes en Lots 10A a 10G. Elle ne modifie ni runtime ni
plateforme et ne rouvre pas Sauron.

- [x] Transferer l'audit source dans `states/audits/`.
- [x] Creer la TODO granulaire de remediation Celebrimbor.
- [x] Lot 10A: garde SSRF URL HTML/Crawl4AI partagee avec la politique PDF.
  Cloture complete au 2026-07-16: garde URL/DNS amont FridaDev avant `/md` et
  barriere aval Crawl4AI sur la navigation Chromium effective, y compris
  redirections et resolution a la connexion, verifiees independamment par
  Sauron. `P2-CEL-WEB-HTML-SSRF-GUARD-01` est ferme. P3 distinct
  `P3-SAU-CRAWL4AI-CHROMIUM-FAKE-PROXY-SOCKET-01`: `ConnectionResetError`
  historique non reproduit dans 13 executions isolees, sorties 0 et `stderr`
  vide, sans patch; non bloquant, non confirme, ni `stale`, corrige ni clos.
  Reouvrir seulement sur traceback, exception asynchrone ou `stderr` anormal
  reproduit par ce test; ni Lot 10A ni correction speculative.
- [x] Lot 10B: plafonds uploads/documents/transcription sur taille reelle.
  - [x] Tranche transcription Whisper fermee le 2026-07-16: frontend `300 s`,
    un blob/upload/transcription, fichier reel FridaDev `16 Mio`, corps declare
    FridaDev/Caddy `17 Mio`, tolerance Whisper `305 s`, rejets 413/422
    allowlistes et content-free; preuves plateforme Sauron et suites
    applicatives sans reseau vertes. La fermeture plateforme inclut la
    regression du WebM navigateur sans duree de conteneur: seule une
    normalisation bornee a `306 s` est permise, la duree WAV connue et
    `<= 305 s` reste obligatoire avant `whisper-cli`, sans fallback brut en cas
    d'echec; le vrai WebM auparavant refuse a ensuite ete transcrit avec HTTP
    200.
  - [x] Reliquat Lot 10B ferme le 2026-07-22: Flask
    `MAX_CONTENT_LENGTH=40 MiB` borne les corps avant materialisation, y compris
    sans longueur fiable a la frontiere WSGI; documents actifs et workspace
    lisent par blocs jusqu'a `40 MiB + 1 octet`. Ce plafond lecteur defensif
    accepte sa limite exacte lorsqu'il est teste seul; de bout en bout,
    l'enveloppe multipart compte dans le plafond du corps et rend un fichier de
    `40 MiB` non uploadable. La preuve composee verrouille cette distinction
    sans nouveau plafond produit. Les payloads fake prouvent document entier
    ou absent, tour maintenu et reponse honnete de Frida.
    `P2-CEL-UPLOAD-LIMITS-01` reste ferme;
    `P3-CEL-DOCUMENT-MULTIPART-EXACT-LIMIT-CONTRACT-01` est ferme par la
    correction docs/tests du 2026-07-22.
- [x] Lot 10C ferme le 2026-07-22: la persistence assistant canonique reste
  fail-closed sur les quatre surfaces normal/override et JSON/stream. Apres sa
  preuve positive, `AssistantText`, traces, ecritures et reactivations Identity
  sont tentees independamment et fail-open; leur observation content-free est
  elle-meme `never raises`. Les pannes injectees conservent HTTP 200 ou le
  terminal `done`, un unique message durable et aucun second save.
  `P2-CEL-CHAT-POST-PERSIST-AUX-01` est ferme.
- [x] Lot 10D ferme le 2026-07-22: `chat_llm_flow` consomme directement l'URL
  finale de `llm_client.or_chat_completions_url()` pour les appels principaux
  stream et non-stream. Les preuves a transports fakes opposent une base
  runtime synthetique a `config_module.OR_BASE`, imposent un unique appel du
  resolver par appel provider et aucun appel pour les overrides. La
  normalisation et le fallback historique restent centralises dans
  `llm_client`; aucun provider, reglage ni fallback produit n'a ete ajoute.
  `P2-CEL-MAIN-LLM-BASE-URL-01` est ferme.
- [x] Lot 10E ferme le 2026-07-22: les prompts constitutifs `main_system` et
  `main_hermeneutical` sont verifies a l'entree du chat avant toute resolution
  ou mutation de conversation; leur indisponibilite produit le refus borne
  `503 critical_prompt_unavailable`. La creation de conversation exige
  seulement `main_system`. Les prompts de resume, reformulation Web et juge
  Identity mutable bornent leur propre fonction sans appel provider, tandis
  que Stimmung, Validation, arbitre et extracteur conservent leurs replis
  locaux. Les prompts legacy ne bloquent ni le runtime ni la validation
  offline. `P3-CEL-PROMPT-FAIL-OPEN-01` est ferme sans modifier un texte de
  prompt, un modele ou une politique produit.
- [x] Lot 10F ferme le 2026-07-22: l'inventaire courant reconcilie chaque
  famille par destination sans `UNKNOWN`. Les diagnostics existants
  exclusivement emis dans les logs standards prives restent lisibles quand
  aucun secret plausible n'est en jeu; HTTP, admin, JSONL, exports, telemetrie
  et retours d'agent restent content-free. Les exceptions de transport
  OpenRouter et embedding capables de recopier un header synthetique sont
  desormais bornees avant tout sink textuel, et la validation minimale ne
  serialise plus sa cause brute. Aucun remplacement global ni nouveau log n'a
  ete introduit. `P3-CEL-RAW-EXCEPTION-LOGS-01` est ferme.
- [x] Lot 10G ferme le 2026-07-22: le scan statique courant recalcule lignes
  utiles, spans/noeuds AST, appelants, responsabilites et tests de chaque
  hotspot. La TODO Lot 9 porte la matrice complete vers une destination
  principale unique 9A-9H, avec golden prerequisite et condition de reduction
  de responsabilite. Les absences chat LLM/stream, validation hermeneutique,
  validateur UI, dashboard read-models et emission Web sont absorbees dans les
  familles existantes, sans `UNKNOWN`, nouveau backlog ou refactor anticipe.
  `P3-CEL-COMPLEXITY-HOTSPOTS-01` est absorbe dans le Lot 9; le Lot 10 est
  ferme et sa TODO archivee. A cette date, Lot 9 restait ouvert et 9.0 etait le
  seul prochain lot executable; sa fermeture ulterieure est documentee dans la
  section Lot 9 ci-dessus.

Regle Lot 10:

- revalider chaque finding dans le HEAD courant avant patch;
- un lot ne vaut pas GO pour le suivant;
- respecter la doctrine de consolidation sans extension fonctionnelle;
- traiter les P3 logs et complexite comme des revalidations bornees, pas comme
  des remplacements globaux ou un refactor massif;
- le constat historique Lot 7 `Code runtime P1/P2 = met` vaut pour son etat de
  2026-06-26 et est desormais complete par les P2 actifs du Lot 10; il ne
  constitue pas une cloture actuelle des P2 code.

### Lot Z - Cloture mega-audit

#### Passe Z.1 - Registre final P1/P2

Date de revalidation: 2026-08-19.

Perimetre inventorie: TODO canonique, audit source, contre-audit, seconde passe
code-only et son archive de remediation, archive Lot 9. L'union contient
exactement `47` identifiants: `2 P1` et `45 P2`. La classification finale est
exhaustive: `32 fermes`, `6 invalides comme P1/P2` et `9 acceptes
explicitement`; aucun identifiant ne reste `open`, `unknown` ou seulement
`needs_targeted_validation` dans le registre P1/P2.

| Finding | Issue finale P1/P2 | Autorite de cloture ou d'acceptation |
| --- | --- | --- |
| `P1-SAU-ENV-PERMISSIONS-01` | `ferme` | Lot 1B; `.env` et backups cibles resserres, compatibilite et health verifies. |
| `P1-SAU-SENSITIVE-BACKUPS-PERMS-01` | `accepte_explicitement` | Decisions operateur Lots 1E/2G: risque local reconnu et accepte temporairement; nouveau GO Sauron requis pour agir. |
| `P2-CEL-ADMIN-400-RAW-01` | `ferme` | Lot 6C; erreurs admin publiques bornees par codes stables et sentinelles. |
| `P2-CEL-ADMIN-COMPAT-KNOBS-01` | `ferme` | Lot 5D; contrat loopback/proxy `Remote-User`, knobs legacy non operateurs. |
| `P2-CEL-ADMIN-PROMPTS-DOM-01` | `ferme` | Lot 5B.1; JSON/DOM standard content-free et lecture brute sous acquittement explicite. |
| `P2-CEL-AGENDA-CLIENT-UNAVAILABLE-AMBIGUITY-01` | `ferme` | Lot 4D.3; absence normale et panne de resolution client sont distinguees. |
| `P2-CEL-AGENDA-PAYLOAD-GUARD-REJECTS-REAL-ERROR-01` | `ferme` | Lot 4D.3.1; payloads Agenda compacts acceptes, charges dangereuses refusees. |
| `P2-CEL-AGENDA-READMODEL-CHILD-ERROR-MASKED-01` | `ferme` | Lot 4D.3.1; erreurs enfants prioritaires dans le read-model. |
| `P2-CEL-ARBITER-PAYLOAD-GUARD-REJECTION-01` | `ferme` | Lot 6F.1; compteurs compacts allowlistes sans contenu candidat. |
| `P2-CEL-CHAT-ORCHESTRATION-GRAVITY-01` | `ferme` | Lots 9B/9Z; orchestration extraite sous goldens, limite residuelle classee sans P1/P2 comportemental. |
| `P2-CEL-CHAT-POST-PERSIST-AUX-01` | `ferme` | Lot 10C; succes canonique preserve malgre panne auxiliaire, sans double save. |
| `P2-CEL-COMPACT-OBSERVABILITY-MESSAGES-COUNT-01` | `invalide` | Lot 6H; attente de test stale, compteur `2` conforme au payload reel. |
| `P2-CEL-DASHBOARD-WEB-LEGACY-RAW-01` | `ferme` | Lot 6D; projection Web legacy sans URL/query/hash stable. |
| `P2-CEL-DOC-CLOSURE-DRIFT-SERVER-01` | `invalide` | Seconde passe: partie code requalifiee P3 architectural, jamais confirmee comme P2 runtime. |
| `P2-CEL-DOCS-ACTIVE-AUDITS-01` | `ferme` | Lot 8; index actif distingue sources historiques et TODO canonique. |
| `P2-CEL-EXCEPTION-RAW-SURFACE-01` | `ferme` | Lots 6B/6C/6I/6J; surfaces exposees bornees, logs prives restants qualifies famille par famille. |
| `P2-CEL-FRONTEND-EMPTY-ON-ERROR-01` | `ferme` | Lots 5C/5C.1; erreurs Notes/Documents/Exports/Images distinctes du vide normal. |
| `P2-CEL-IDENTITY-HASH-POLICY-01` | `ferme` | Lots 6E/6E.1; hashes courts de contenu retires des surfaces actives. |
| `P2-CEL-IDENTITY-RAW-LOG-01` | `invalide` | Decision produit explicite du 2026-07-16: non-finding pour les logs prives identity/memory existants, sans nouveau log ni secret. |
| `P2-CEL-LLM-ERROR-RAW-01` | `ferme` | Lot 6B; erreurs provider exposees par codes/classes stables. |
| `P2-CEL-LOG-SAFECODE-TOKENLIKE-01` | `ferme` | Lot 7.1; valeurs token-like refusees/redacted aux trois frontieres. |
| `P2-CEL-LOG-SAFECODE-TOKENLIKE-VARIANTS-01` | `ferme` | Lot 7.2; variantes provider synthetiques bornees sans bloquer les codes normaux. |
| `P2-CEL-MAIN-LLM-BASE-URL-01` | `ferme` | Lot 10D; resolver runtime unique pour stream/non-stream, absent sous override. |
| `P2-CEL-MEMORY-INPUT-FAIL-OPEN-01` | `ferme` | Lot 4D.2; pannes summary/identity propagees comme erreurs content-free. |
| `P2-CEL-MUTABLE-IDENTITY-STAGING-TEST-FAILURES-01` | `ferme` | Lot 6F; garde legitime corrigee, fixtures stale alignees, faux bugs invalides. |
| `P2-CEL-NOTES-UI-GAP-01` | `ferme` | Lots 5B.2 a 5B.2.3; mode Notes minimal et garde dossier effectifs. |
| `P2-CEL-OBSERVABILITY-PAYLOAD-REJECTED-CHAT-RESPONSE-01` | `ferme` | Lot 6J.1; refus non-stream compact conserve par la garde. |
| `P2-CEL-OBSERVABILITY-PAYLOAD-REJECTED-STREAM-01` | `ferme` | Lot 6J; metadonnees stream compactes acceptees sans texte brut. |
| `P2-CEL-REQUESTS-TIMEOUT-01` | `invalide` | Lot 4A; aucun appel externe evident sans timeout, sous-findings fail-open fermes en 4B/4D. |
| `P2-CEL-SERVER-BOUNDARY-GRAVITY-01` | `invalide` | Alias fusionne dans `P2-CEL-SERVER-ROUTE-GRAVITY-01`, sans finding distinct. |
| `P2-CEL-SERVER-ROUTE-GRAVITY-01` | `ferme` | Lots 9A/9Z; routes extraites sous route-map/goldens, sans P1/P2 comportemental residuel. |
| `P2-CEL-STIMMUNG-PROMPT-GUARD-REJECTION-01` | `ferme` | Lot 6G; cles compactes allowlistees, prompt/payload brut toujours refuses. |
| `P2-CEL-UPLOAD-LIMITS-01` | `ferme` | Lot 10B; corps et flux effectifs bornes, distinction multipart verrouillee. |
| `P2-CEL-WEB-DISCOVERY-FAIL-OPEN-01` | `ferme` | Lot 4D; panne discovery distincte du vrai `no_data`. |
| `P2-CEL-WEB-HTML-SSRF-GUARD-01` | `ferme` | Lot 10A; garde amont FridaDev et barriere aval Crawl4AI validees. |
| `P2-CEL-WEB-SEARCH-FAIL-OPEN-01` | `ferme` | Lot 4B; panne SearXNG distincte du zero resultat. |
| `P2-CEL-WEB-TURN-PROVENANCE-CONTINUITY-01` | `ferme` | Correctif audite le 2026-07-25 et validation dialogique live utilisateur du 2026-08-14. |
| `P2-SAU-ADMINER-LATERAL-01` | `accepte_explicitement` | Decisions operateur Lots 2G/3: limite interne du serveur solo, sans exposition publique directe. |
| `P2-SAU-AGENTS-ADMIN-TOKEN-STALE-01` | `ferme` | Lot 8; instructions Sauron alignees sur Caddy/Authelia et `Remote-User`. |
| `P2-SAU-COCKPIT-DOCKER-REACHABILITY-01` | `accepte_explicitement` | Decisions operateur Lots 2G/3: pas d'exposition Internet directe confirmee, validation ciblee reouvrable. |
| `P2-SAU-COMPOSE-PERMISSIONS-01` | `accepte_explicitement` | Decision operateur Lot 2G: `hygiene_deferred` pour serveur solo, correction seulement apres GO. |
| `P2-SAU-DOCKER-SOCKET-SURFACE-01` | `accepte_explicitement` | Decisions operateur Lots 2G/3: pas de port public, gouvernance interne conservee comme limite. |
| `P2-SAU-FRIDADEV-CONTAINER-HARDENING-01` | `accepte_explicitement` | Decisions operateur Lots 2G/3: hardening interne differe; changement uniquement par lot Sauron. |
| `P2-SAU-HEALTHCHECKS-ABSENT-01` | `accepte_explicitement` | Decisions operateur Lots 2G/3: dette d'observabilite service non bloquante sur serveur solo. |
| `P2-SAU-LOG-SECRETLIKE-01` | `invalide` | Lot 2D: aucun secret exploitable confirme; faux positifs et option privacy separes. |
| `P2-SAU-NEXTCLOUD-DATA-RW-MOUNTS-01` | `accepte_explicitement` | Decisions operateur Lots 2G/3: mounts actifs conserves; reduction exige lot Sauron et preuve fonctionnelle. |
| `P2-SAU-PERMISSIONS-GOVERNANCE-01` | `accepte_explicitement` | Decisions operateur Lots 1E/2G: dette locale reconnue, pas de mutation sans GO Sauron. |

Revalidation courante content-free:

- Git initial: branche `FridaV1-Lot9A-Route-Refactors`, HEAD/upstream/distant
  `1ca33a11b8657cc93ec6c9dbeaa59f31468ddb8f`, divergence `0/0`, worktree
  propre;
- plateforme: `.env` en `0640 root:tof`; permissions sensibles residuelles et
  Compose `0664` confirment que les risques acceptes ne sont pas declares
  corriges; FridaDev reste root/rootfs writable sans options de hardening;
  Adminer et socket proxy n'ont aucun port host; les mounts doc-pipeline
  concernes restent RW; `18` conteneurs actifs sans healthcheck explicite,
  `0` unhealthy/restarting/exited;
- applicatif hermetique: decouverte complete `2665 tests`, `0` echec,
  `0` erreur; bundle P1/P2 cible `269/269`; frontend workspace
  `135/135`, tous sans reseau ni secret/provider reel;
- runtime FridaDev avant documentation: conteneur
  `3135a0c35d266766a3d35c5d68207cbeeca2f75268d6e07de0419a521cec8191`,
  image `sha256:dec8afcf1ce9f21f05fe01dc6588425a0715ad3a8f979ef6f84f8da805bf9ba5`,
  healthy, restart `0`, OOM false.

Limites: les neuf acceptations explicites ne sont pas des corrections ni une
affirmation d'absence de risque. Elles restent reouvrables sur exposition
publique, secret confirme, panne, nouveau consommateur, changement de menace ou
nouvelle decision operateur. Cette passe ne classe aucun P3, ne produit pas
l'artefact final et n'archive pas la TODO.

- [x] Tous P1/P2 fermes, invalides ou acceptes explicitement.

#### Passe Z.2 - Registre final P3

Date de revalidation: 2026-08-19.

Perimetre inventorie: les memes sources versionnees que Z.1, completees par
les audits d'execution et le journal d'ingenierie des Lots dialogique, 10F et
9A. Ces traces ajoutent quatre findings confirmes puis fermes qui n'avaient pas
ete recopies dans le registre versionne. L'univers final contient donc
exactement `23` identifiants P3: `18 fermes`, `3 supersedes`, `1 accepted_limit`
et `1 post_audit_trigger_only`. Aucun P3 ne reste sans classe ni destination.

| Finding | Classe finale | Autorite ou destination post-audit |
| --- | --- | --- |
| `P3-CEL-AGENDA-DORMANT-WORDING-01` | `ferme` | Lot 4D.3; docs actives alignees sur runtime Agenda V1 et roadmap post-V1. |
| `P3-CEL-BIBLIO-COMMENTS-STALE-01` | `ferme` | Lot 8; doctrine Biblio agent-first et references aux cas produit clarifiees. |
| `P3-CEL-COMPLEXITY-HOTSPOTS-01` | `ferme` | Lot 10G puis Lots 9A-9Z; hotspots traites par micro-lots, limites residuelles classees `accepted_limit` ou `post_v1`. |
| `P3-CEL-DIALOGIC-ACTIVE-OVERVIEW-STALE-01` | `ferme` | Correctif `df8d9ebc`; la reference active distingue le modele principal et l'override local `presence`. |
| `P3-CEL-DOCUMENT-MULTIPART-EXACT-LIMIT-CONTRACT-01` | `ferme` | Lot 10B; distinction plafond fichier/lecteur et enveloppe multipart documentee et testee. |
| `P3-CEL-FILENAMES-CONTENT-FREE-DECISION-01` | `ferme` | Lot 8; doctrine filenames visibles produit vs observabilite content-free. |
| `P3-CEL-FINAL-LOCK-CONFLICT-TEST-01` | `ferme` | Lot 9B; matrice Agenda/Biblio, priorite, candidats ecartes et bypass provider verrouilles. |
| `P3-CEL-LARGE-FILES-01` | `supersede` | Supersede par `P3-CEL-COMPLEXITY-HOTSPOTS-01`, puis absorbe par le Lot 9 ferme. |
| `P3-CEL-LARGE-FILES-AMPLIFIED-01` | `supersede` | Alias du finding large-files, sans dette distincte. |
| `P3-CEL-LARGE-FILES-HOTSPOTS-01` | `supersede` | Seconde passe remplacee par la matrice fonctionnelle `P3-CEL-COMPLEXITY-HOTSPOTS-01`. |
| `P3-CEL-LOG-FRONTEND-DENYLIST-01` | `ferme` | Lot 7; allowlist frontend et test sentinelle champ inconnu. |
| `P3-CEL-LOT10F-INVENTORY-COUNT-01` | `ferme` | Micro-lot docs-only Lot 10F; inventaire corrige `132 = 82 + 48 + 2`. |
| `P3-CEL-LOT9A1-DASHBOARD-ROUTE-OWNER-DOC-01` | `ferme` | Commit `5a244fd1`; contrat dashboard attribue les routes au module extrait. |
| `P3-CEL-LOT9A3-CHAT-ROUTE-OWNER-DOC-01` | `ferme` | Commit `27d66d8b`; architecture active attribue `/api/chat` a `chat_transport_routes.py`, wiring dans `server.py`. |
| `P3-CEL-LOT9A3-SOURCE-OWNER-TEST-01` | `ferme` | Commit `efa004a0`; preuve AST accepte les deux proprietaires autorises et refuse zero/duplication. |
| `P3-CEL-OPEN-CHECKBOXES-ARCHIVES-01` | `ferme` | Lot 8; index distingue TODO canonique et pieces historiques non executables. |
| `P3-CEL-PROMPT-FAIL-OPEN-01` | `ferme` | Lot 10E; prompts critiques fail-closed et fallbacks locaux bornes. |
| `P3-CEL-RAW-EXCEPTION-LOGS-01` | `ferme` | Lot 10F; inventaire par destination, transports sensibles bornes, logs prives qualifies famille par famille. |
| `P3-CEL-SECRET-LIKE-FIXTURES-01` | `accepted_limit` | Lot 7; sentinelles synthetiques explicites, aucune valeur runtime; hygienisation cosmetique non requise. |
| `P3-CEL-TEST-PROOF-MAPPING-01` | `ferme` | Lot 7; matrice tests/preuves et baseline JSONL content-free. |
| `P3-IDENTITY-CANDIDATES-PROJECTION-VERSION-STALE` | `ferme` | Lot 6E.2; projection candidates active en `identity_candidates_content_minimized_v2`. |
| `P3-IDENTITY-LEGACY-PROJECTION-VERSION-STALE` | `ferme` | Lot 6E.2; projection legacy active en `identity_legacy_content_minimized_v2`. |
| `P3-SAU-CRAWL4AI-CHROMIUM-FAKE-PROXY-SOCKET-01` | `post_audit_trigger_only` | Non confirme apres 13 executions isolees; ne rouvrir que sur traceback, exception asynchrone ou `stderr` anormal reproduit par ce test. |

Revalidation courante content-free:

- univers versionne `19` + quatre findings d'execution fermes = `23`; chaque
  identifiant apparait exactement une fois dans ce registre;
- preuves ciblees hermetiques `92/92`: prompts requis, multipart, projections
  Identity V2, source owner AST, allowlist logs et golden final-lock;
- la reference dialogique active documente l'override `presence`; le contrat
  dashboard pointe vers `admin_logs_dashboard_routes.py`; l'architecture chat
  pointe vers `chat_transport_routes.py`; le contrat observabilite porte les
  compteurs Lot 10F corriges;
- baseline complete avant documentation: `2665 tests`, `0` echec, `0` erreur;
  runtime FridaDev inchange, healthy, restart `0`, OOM false.

Limites: `accepted_limit` n'est pas une correction; le suivi Crawl4AI n'est pas
un finding confirme ni un lot actif et interdit un patch speculatif. Les sujets
`post_v1` deja classes par le Lot 9 ne sont pas rouverts. Cette passe ne produit
pas l'artefact final et n'archive pas la TODO.

- [x] P3 classes ou planifies post-audit.
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
