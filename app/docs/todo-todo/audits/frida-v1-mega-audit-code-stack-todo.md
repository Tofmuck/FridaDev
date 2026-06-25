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
- Statut courant: requalified_by Lot 2D;
  `partially_confirmed_non_sensitive`. Caddy faux positif probable; Authelia ne
  montre pas de secret exploitable dans la fenetre scannee, mais logge des URLs
  de redirection completes.
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
- Statut courant: no public exposure confirmed by Lot 3; governance/consumer
  matrix still open as P2.
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
- Statut courant: no public exposure confirmed by Lot 3; lateral Docker risk
  remains open as P2.
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
- Statut courant: needs_targeted_validation after Lot 3; no direct Internet
  exposure confirmed, Caddy/Cockpit route still worth targeted validation.
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
- Statut courant: hygiene/service observability remains open; no unhealthy or
  restarting container observed by Lot 3.
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
- Statut courant: partially_confirmed_by Lot 2F; correction candidate
  documentee mais non appliquee; `hygiene_deferred` par recadrage Lot 2G.
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

- [ ] Inventorier OS / paquets systeme sans appliquer de mise a jour.
- [ ] Inventorier Docker / Docker Compose.
- [ ] Inventorier images Docker des services, sans `pull`.
- [ ] Inventorier Caddy.
- [ ] Inventorier Authelia.
- [ ] Inventorier Nextcloud.
- [ ] Inventorier Postgres/Redis.
- [ ] Inventorier n8n.
- [ ] Inventorier SearxNG.
- [ ] Inventorier Adminer.
- [ ] Inventorier FridaDev app/db.
- [ ] Inventorier autres services exposes ou critiques.
- [ ] Classer chaque element: `update_critique_securite`,
  `update_recommandee`, `update_postposable`, `no_action`,
  `needs_operator_decision`.
- [ ] Si update critique securite urgente: ouvrir un lot separe avec
  backup/rollback/health; sinon passer a l'audit code.

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
