# Frida V1 - Mega audit code + stack OVH - 2026-06-24

Statut: audit baseline Lot 0, read-only/docs-only.
Branche: `FridaV1-Mega-Audit-Code-Stack`.
Base: `main` a `bc8aee23499cd58fcd29abfb7314a9a2a688e3d6`.
Roles: Sauron pour `/opt/platform`, Celebrimbor pour `/opt/platform/fridadev`.
Contre-audit source: `app/docs/todo-todo/audits/frida-v1-mega-audit-code-stack-counter-audit-2026-06-24.md`.

## Verdict court

- P0: aucun danger immediat prouve dans ce lot.
- P1: 2 risques plateforme locaux a traiter avant tout nettoyage large.
- P2: plusieurs dettes serieuses a cadrer par lots bornes.
- P3: dette de lisibilite et de hygiene importante, surtout gros fichiers/docs.
- Runtime modifie: non.
- Plateforme modifiee: non.
- Secrets/logs bruts/payloads affiches: non.

## Scope couvert

### Sauron

- Arborescence `/opt/platform` par inventaire de fichiers et metadonnees.
- Compose/Caddy/env par chemins, tailles, modes et compteurs, sans valeurs.
- Docker containers, networks, volumes, ports publies, health/restart policy.
- Logs Docker recents bornes `since=30m tail=200`, sans lignes brutes.
- Fichiers sensibles par noms/extensions: `.env`, dumps, DB, archives, keys.
- Exposition publique FridaDev/Adminer par headers HTTP sans cookies.

### Celebrimbor

- Repo Git, branche, diff, JSONL baselines, TODO/docs actives et archives.
- `app/server.py`, `app/core`, `app/admin`, `app/observability`, `app/memory`,
  `app/agenda`, `app/biblio`, `app/tools`, `app/web`, `app/tests`.
- Routes HTTP, garde admin globale, Continuity Capsule, Mail spec-only,
  Agenda dormant, docs final V1, artefacts JSONL.
- Scans de taille, patterns de logs/erreurs, tests fake/live, secret-like
  literals en fixtures.

## Scope non couvert

- Pas de lecture de contenus secrets `.env`, token, DSN, cookie ou cle privee.
- Pas de lecture brute de logs.
- Pas de scan exhaustif de contenu utilisateur, documents Nextcloud ou DB.
- Pas de tests runtime complets, provider live, Nextcloud live ou Mail live.
- Pas de correction code, plateforme, config, Caddy, Authelia, DB ou Docker.

## Lot 0.1 - Consolidation contre-audit Sauron/Celebrimbor

Le contre-audit confirme que le Lot 0 principal etait partiellement trop
Sauron-heavy: il a bien ouvert les risques plateforme, mais il a trop agrege
les risques Celebrimbor sous des familles larges comme exception/raw,
`server.py` et gros fichiers. Le registre canonique doit donc conserver les
findings applicatifs concrets suivants sans les masquer.

### Resolution finding par finding

| ID contre-audit | Decision Lot 0.1 | Integration canonique |
| --- | --- | --- |
| `P1-SAU-ENV-PERMISSIONS-01` | Valide deja couvert | Conserve tel quel Lot 1 |
| `P1-SAU-SENSITIVE-BACKUPS-PERMS-01` | Valide deja couvert | Conserve tel quel Lot 2 |
| `P2-SAU-ADMINER-LATERAL-01` | Valide | Ajoute Lot 3 |
| `P2-SAU-COCKPIT-DOCKER-REACHABILITY-01` | Valide, `needs_targeted_validation` pour la regle UFW exacte | Ajoute Lot 3 |
| `P2-SAU-DOCKER-SOCKET-SURFACE-01` | Valide deja couvert, amplifie par socket direct status | Fusion/alias dans Lot 3 |
| `P2-SAU-HEALTHCHECKS-ABSENT-01` | Valide | Ajoute Lot 3 |
| `P2-SAU-FRIDADEV-CONTAINER-HARDENING-01` | Valide | Ajoute Lot 3 |
| `P2-SAU-NEXTCLOUD-DATA-RW-MOUNTS-01` | Valide | Ajoute Lot 3 |
| `P2-SAU-PERMISSIONS-GOVERNANCE-01` | Valide comme gouvernance large, distinct du P1 backup | Ajoute Lot 2 |
| `P2-SAU-AGENTS-ADMIN-TOKEN-STALE-01` | Valide | Ajoute Lot 8 docs |
| `P2-CEL-ADMIN-PROMPTS-DOM-01` | Valide | Ajoute Lot 5/6 decision content gate |
| `P2-CEL-LLM-ERROR-RAW-01` | Valide | Ajoute Lot 6 |
| `P2-CEL-DASHBOARD-WEB-LEGACY-RAW-01` | Valide | Ajoute Lot 6 |
| `P2-CEL-IDENTITY-HASH-POLICY-01` | Valide comme decision P2 | Ajoute Lot 6/8 |
| `P2-CEL-NOTES-UI-GAP-01` | Valide produit/UX, non runtime bug | Ajoute Lot 5 |
| `P2-CEL-FRONTEND-EMPTY-ON-ERROR-01` | Valide | Ajoute Lot 5/7 |
| `P2-CEL-CHAT-ORCHESTRATION-GRAVITY-01` | Valide | Ajoute Lot 9 avec golden tests |
| `P2-CEL-SERVER-BOUNDARY-GRAVITY-01` | Doublon precis de `P2-CEL-SERVER-ROUTE-GRAVITY-01` | Fusionne comme alias Lot 9 |
| `P2-CEL-ADMIN-400-RAW-01` | Valide | Ajoute Lot 6 |
| `P3-CEL-FINAL-LOCK-CONFLICT-TEST-01` | Valide P3 | Ajoute Lot 7 |
| `P3-CEL-BIBLIO-COMMENTS-STALE-01` | Valide P3 | Ajoute Lot 8 |
| `P3-CEL-AGENDA-DORMANT-WORDING-01` | Requalifie P3 faible / stale partiel | Ajoute `needs_targeted_validation` Lot 8 |
| `P3-CEL-LOG-FRONTEND-DENYLIST-01` | Valide P3 | Ajoute Lot 5/7 |
| `P3-CEL-FILENAMES-CONTENT-FREE-DECISION-01` | Valide decision P3 | Ajoute Lot 8 |
| `P3-CEL-LARGE-FILES-AMPLIFIED-01` | Doublon amplifie de `P3-CEL-LARGE-FILES-01` | Fusionne comme alias Lot 9 |

### Synthese Lot 0.1

- Validés et ajoutes: Sauron lateralite/Adminer/Cockpit/healthchecks/hardening/mounts,
  Celebrimbor prompts DOM, erreurs LLM/admin 400, dashboard legacy raw, hashes
  identity, Notes UI, erreurs frontend vides, orchestration chat, final-lock
  conflict, Biblio comments, frontend denylist et filenames.
- Fusionnes: Docker socket avec surface socket existante; server boundary avec
  server route gravity; large files amplified avec large files.
- Requalifies: Agenda dormant wording en P3 faible/stale partiel.
- Invalides deja conserves: pas de bypass public Authelia, pas de bypass
  lateral `/api/admin/*`, ports publics hors Caddy non confirmes.

## Findings

### P0

Aucun P0 prouve.

### P1

#### P1-SAU-ENV-PERMISSIONS-01 - `/opt/platform/.env` world-readable

- Severite: P1.
- Zone: Sauron, secrets plateforme.
- Constat: `/opt/platform/.env` existe avec mode `0644`, uid/gid `0/0`, taille
  2241 octets, donc lisible par tout utilisateur local.
- Preuve: inventaire `stat` content-free des fichiers sensibles.
- Impact: exposition locale possible de secrets plateforme si un compte local
  non privilegie existe ou si un processus compromis peut lire ce fichier.
- Recommandation: lot Sauron dedie, backup metadata, `chmod 600`, verification
  ownership, controle que Compose/Caddy continuent a lire le fichier.
- Lot propose: Lot 1 - securite plateforme P1.
- Risque d'effet de bord: permissions trop strictes si un service lit le
  fichier directement hors root; a verifier avant chmod.
- Preuve de fermeture attendue: `stat` content-free, `docker compose config
  --quiet`, health Caddy/FridaDev, aucun secret affiche.

#### P1-SAU-SENSITIVE-BACKUPS-PERMS-01 - backups/dumps/keys lisibles localement

- Severite: P1.
- Zone: Sauron, backups et artefacts runtime hors repo.
- Constat: scan nom/metadata trouve 62 fichiers sensibles nommes; 39 sont
  world-readable et 5 group-writable. Exemples de categories: SQLite n8n,
  dumps DB, archives `.tgz`, backup Authelia, DB Stirling, key backup,
  `_codex_reports` DB dumps.
- Preuve: scan metadata content-free; aucune valeur ni contenu ouvert.
- Impact: fuite locale possible de donnees, secrets, historique n8n ou dumps si
  permissions/retention restent larges.
- Recommandation: lot Sauron separe: classifier backup actif vs obsolete,
  restreindre modes, deplacer/archiver proprement, definir retention.
- Lot propose: Lot 2 - secrets/env/logs/permissions.
- Risque d'effet de bord: suppression ou chmod large peut casser restauration
  ou audit; commencer par inventaire et backup de metadata.
- Preuve de fermeture attendue: matrice de retention, modes `0600/0640`
  justifies, aucun dump world-readable non justifie.

### P2

#### P2-SAU-LOG-SECRETLIKE-01 - logs Authelia/Caddy avec marqueurs secret-like

- Severite: P2.
- Zone: Sauron, logs plateforme.
- Constat: scan Docker logs borne `since=30m tail=200` sans affichage brut:
  Authelia `200` lignes / 76675 octets / `secret_count=12`; Caddy `35` lignes /
  8641 octets / `authorization_count=1`.
- Preuve: compteur par categorie, lignes brutes non imprimees.
- Impact: peut etre faux positif lexical, mais peut aussi signaler presence de
  termes ou headers sensibles dans logs.
- Recommandation: lot Sauron avec lecture locale bornee et redaction immediate,
  puis regle de logging/headers si confirme.
- Lot propose: Lot 2 - secrets/env/logs/permissions.
- Risque d'effet de bord: ne pas purger logs sans politique de retention.
- Preuve de fermeture attendue: qualification faux positif ou correction
  log-level/redaction, rapport content-free seulement.

#### P2-SAU-DOCKER-SOCKET-SURFACE-01 - surface docker socket proxy a revalider

- Severite: P2.
- Zone: Sauron, Docker/socket proxy.
- Constat: compose global contient des mentions `docker.sock`/socket proxy; un
  container `platform-docker-socket-proxy` est actif sur `platform_proxy_net`.
- Preuve: inventaire compose et `docker inspect` content-free.
- Impact: si API Docker exposee trop largement a un service web, une compromission
  applicative peut devenir compromise host.
- Recommandation: verifier ACL du socket proxy, reseaux attaches, methodes
  autorisees, consommateurs reels.
- Lot propose: Lot 3 - Docker/Caddy/Authelia/reseaux.
- Risque d'effet de bord: durcir sans connaitre les consommateurs peut casser
  Homepage/monitoring.
- Preuve de fermeture attendue: matrice consumers -> endpoints Docker autorises,
  scan reseaux, test services consommateurs.

#### P2-SAU-COMPOSE-PERMISSIONS-01 - compose FridaDev group-writable

- Severite: P2.
- Zone: Sauron/Celebrimbor boundary.
- Constat: `/opt/platform/fridadev-app/docker-compose.yml` et
  `/opt/platform/fridadev/docker-compose.yml` sont en `0664`, donc
  group-writable.
- Preuve: scan `stat` content-free.
- Impact: modification runtime possible par tout membre du groupe proprietaire;
  risque de drift plateforme/app.
- Recommandation: verifier ownership attendu puis passer en mode non
  group-writable si compatible.
- Lot propose: Lot 2 ou Lot 3.
- Risque d'effet de bord: workflow operateur local peut dependre du groupe.
- Preuve de fermeture attendue: mode cible documente, `docker compose config
  --quiet`, aucun service modifie.

#### P2-CEL-ADMIN-COMPAT-KNOBS-01 - tests admin encore centres sur knobs obsoletes

- Severite: P2.
- Zone: Celebrimbor, admin/security/tests.
- Constat: 13 fichiers tests mentionnent `FRIDA_ADMIN_TOKEN` ou
  `FRIDA_ADMIN_LAN_ONLY`, alors que le contrat actif OVH dit que ces knobs sont
  obsoletes/non operateur. Le garde actuel est bien global via
  `@app.before_request` + loopback/`Remote-User`, donc le risque n'est pas un
  bypass prouve mais une preuve de test confuse.
- Preuve: scan tests admin; `app/server.py` lignes garde admin lues.
- Impact: futures corrections peuvent etre validees par des tests qui manipulent
  des knobs qui ne doivent plus representer le contrat humain.
- Recommandation: lot applicatif cible pour requalifier ces tests en
  compatibilite obsolete, renforcer tests `Remote-User`/proxy/loopback, et
  documenter les exceptions.
- Lot propose: Lot 5 - admin/security/app routes.
- Risque d'effet de bord: casser des tests historiques sans verifier les routes
  admin registerees hors `server.py`.
- Preuve de fermeture attendue: suite admin contract en conteneur, tests
  refus lateral direct et accept proxy/loopback.

#### P2-CEL-EXCEPTION-RAW-SURFACE-01 - surface globale `str(exc)`/raw/payload a borner

- Severite: P2.
- Zone: Celebrimbor, logs/observabilite.
- Constat: scan Python trouve 64 occurrences `str(exc)`/`str(e)`, 478 matches
  de cles payload/raw sensibles au sens large, 12 `print(` et 2 mentions
  traceback/format. Les lots V1 ont durci les surfaces critiques, mais le repo
  complet reste a qualifier.
- Preuve: scan par fichier, sans lignes de contenu.
- Impact: risque de cause brute exposee, fail-open, ou logs trop bavards dans
  chemins hors V1 final audit.
- Recommandation: lot par surfaces, pas nettoyage massif: admin routes, tools,
  memory/model calls, web search, biblio/agenda.
- Lot propose: Lot 6 - observabilite/logs.
- Risque d'effet de bord: remplacer tous les `str(exc)` aveuglement peut masquer
  diagnostics utiles.
- Preuve de fermeture attendue: tests content-free et fail-closed par surface.

#### P2-CEL-DOCS-ACTIVE-AUDITS-01 - audits superseded encore dans `todo-todo/audits`

- Severite: P2.
- Zone: docs/TODO/source-of-truth.
- Constat: 4 audits V1 final/Continuity restent sous `todo-todo/audits`; ils
  sont marques historiques/superseded, mais la convention de chemin continue a
  les rendre actifs. Un audit final global conserve aussi une checkbox ouverte.
- Preuve: inventaire `find app/docs/todo-todo`; scan headers `superseded`;
  scan checkboxes.
- Impact: un agent suivant peut rouvrir des P1/P2 historiques ou compter une
  archive comme dette active.
- Recommandation: lot docs: deplacer vers `todo-done/audits` si convention OK,
  ou ajouter index `historical/superseded` explicite et fermer checkbox
  documentaire sans toucher aux constats historiques.
- Lot propose: Lot 8 - docs/source-of-truth.
- Risque d'effet de bord: casser pointeurs historiques.
- Preuve de fermeture attendue: zero audit superseded ambigu dans `todo-todo`.

#### P2-CEL-SERVER-ROUTE-GRAVITY-01 - `server.py` reste point de concentration

- Severite: P2.
- Zone: architecture applicative.
- Constat: `app/server.py` contient 1850 lignes et 64 routes; 17 routes admin
  reposent sur garde global. La discipline AGENTS recommande de ne pas
  allonger au-dela de 500-600 lignes hors necessite vitale.
- Preuve: comptage lignes/routes.
- Impact: risque de regression transversale, oubli de garde, couplage routes
  produit/admin, difficulte de revue.
- Recommandation: lot de refactor cible par responsabilite, apres P1/P2
  securite; extraire blueprints/routes sans changer comportement.
- Lot propose: Lot 9 - refactors cibles.
- Risque d'effet de bord: fort si refactor trop large; necessite golden tests
  routes avant mouvement.
- Preuve de fermeture attendue: snapshot routes, tests admin/workspace/chat,
  diff comportement nul.

#### P2-CEL-REQUESTS-TIMEOUT-01 - appels HTTP directs a qualifier

- Severite: P2.
- Zone: tools/model calls/connecteurs.
- Constat: scan heuristique trouve des appels `requests.*` dans `web_search`,
  `arbiter`, `catalogue_client`, `summarizer`, `mutable_identity_judge_v2`.
  Le scan ne prouve pas l'absence de timeout pour chaque appel.
- Preuve: scan regex content-free.
- Impact: risque de blocage runtime si certains appels externes n'ont pas de
  timeout ou de fallback.
- Recommandation: micro-audit appels HTTP, lister timeout/retry/fallback,
  corriger seulement les vrais absents.
- Lot propose: Lot 4 - code runtime P1/P2.
- Risque d'effet de bord: timeouts trop courts peuvent degrader UX.
- Preuve de fermeture attendue: tests timeout/fallback par client.

#### P2 supplementaires valides par Lot 0.1

- `P2-SAU-ADMINER-LATERAL-01`: Adminer protege publiquement par Authelia mais
  a isoler/revalider en lateralite Docker.
- `P2-SAU-COCKPIT-DOCKER-REACHABILITY-01`: reachability Cockpit depuis ranges
  Docker a valider en lot Sauron cible.
- `P2-SAU-HEALTHCHECKS-ABSENT-01`: healthchecks absents sur plusieurs services
  critiques, a traiter service par service.
- `P2-SAU-FRIDADEV-CONTAINER-HARDENING-01`: conteneur app a durcir
  progressivement, sans rebuild implicite.
- `P2-SAU-NEXTCLOUD-DATA-RW-MOUNTS-01`: mounts Nextcloud RW du doc-pipeline a
  justifier ou reduire.
- `P2-SAU-PERMISSIONS-GOVERNANCE-01`: gouvernance permissions/retention plus
  large que les deux P1.
- `P2-SAU-AGENTS-ADMIN-TOKEN-STALE-01`: `/opt/platform/AGENTS.md` doit etre
  aligne avec le contrat admin OVH courant.
- `P2-CEL-ADMIN-PROMPTS-DOM-01`: prompts complets dans DOM admin a assumer
  comme exception operateur ou a remplacer par metadonnees/content gate.
- `P2-CEL-LLM-ERROR-RAW-01`: erreurs LLM brutes a remplacer par codes stables.
- `P2-CEL-DASHBOARD-WEB-LEGACY-RAW-01`: URL/hash web legacy a projeter
  content-free.
- `P2-CEL-IDENTITY-HASH-POLICY-01`: doctrine hashes courts identity a trancher.
- `P2-CEL-NOTES-UI-GAP-01`: Notes V1 a clarifier UI minimale ou API-only.
- `P2-CEL-FRONTEND-EMPTY-ON-ERROR-01`: panels frontend ne doivent pas rendre
  une panne comme liste vide.
- `P2-CEL-CHAT-ORCHESTRATION-GRAVITY-01`: orchestration chat a couvrir par
  golden tests avant extraction.
- `P2-CEL-ADMIN-400-RAW-01`: erreurs admin 400 ne doivent pas echo de valeurs
  invalides.

#### Doublons P2 fusionnes par Lot 0.1

- `P2-SAU-DOCKER-SOCKET-SURFACE-01`: confirme/amplifie, conserve sous l'ID
  existant avec mention socket direct.
- `P2-CEL-SERVER-BOUNDARY-GRAVITY-01`: fusionne dans
  `P2-CEL-SERVER-ROUTE-GRAVITY-01`.

### P3

#### P3-CEL-LARGE-FILES-01 - beaucoup de gros modules et tests

- Severite: P3.
- Zone: architecture/lisibilite.
- Constat: 653 fichiers code/tests/web scans; 166 fichiers >=500 lignes et
  114 >=600. Exemples: `app/tools/web_search.py` 2494,
  `app/web/styles.css` 2002, `app/server.py` 1850,
  `app/observability/dashboard_read_model.py` 1689,
  `app/core/chat_service.py` 1256.
- Preuve: comptage lignes.
- Impact: cout de revue et risque de regression.
- Recommandation: ne pas refactorer maintenant; traiter seulement apres gates
  P1/P2, par extraction testee.
- Lot propose: Lot 9.
- Preuve de fermeture attendue: plans de split par responsabilite, pas de
  refactor cosmetique.

#### P3-CEL-TEST-PROOF-MAPPING-01 - tests fake/live a cartographier

- Severite: P3.
- Zone: tests/preuves.
- Constat: 261 fichiers tests; marqueurs `fake=2663`, `mock=212`, `live=82`,
  `skip=0`, `xfail=0`. Ce n'est pas un bug, mais le mega-audit doit distinguer
  preuve runtime, fake, covered_by_tests et live.
- Preuve: scan tests.
- Impact: faux sentiment de couverture si les tests fake sont lus comme preuve
  live.
- Recommandation: matrice tests/proofs par domaine.
- Lot propose: Lot 7 - tests/smokes/artefacts.
- Preuve de fermeture attendue: tableau domaine -> test -> type de preuve.

#### P3-CEL-SECRET-LIKE-FIXTURES-01 - faux positifs secrets en fixtures/tests

- Severite: P3.
- Zone: tests/content-free.
- Constat: scan tracked files trouve 23 fichiers avec secret-like literals,
  majoritairement tests de redaction/fixtures; un marqueur private-key est dans
  un test Continuity.
- Preuve: scan counts, pas de valeurs affichees.
- Impact: bruit dans scans anti-fuite et risque de fixture trop realiste.
- Recommandation: allowlist explicite ou fixtures synthetiques nommees.
- Lot propose: Lot 7.
- Preuve de fermeture attendue: scan anti-fuite avec allowlist documentee.

#### P3-CEL-OPEN-CHECKBOXES-ARCHIVES-01 - checkboxes historiques persistantes

- Severite: P3.
- Zone: docs/archives.
- Constat: plusieurs `todo-done` gardent des checkboxes ouvertes historiques,
  dont Biblio/Web/Adobe/migrations; Agenda actif garde 64 cases post-V1.
- Preuve: scan checkboxes par fichier.
- Impact: bruit pour agents suivants.
- Recommandation: ne pas cocher artificiellement; ajouter conventions de
  lecture historique ou deplacer les vrais plans ouverts.
- Lot propose: Lot 8.
- Preuve de fermeture attendue: index docs distinguant ouvert actif vs archive
  historique.

#### P3 supplementaires valides ou requalifies par Lot 0.1

- `P3-CEL-FINAL-LOCK-CONFLICT-TEST-01`: test fake a ajouter si Agenda/Biblio
  final locks peuvent coexister.
- `P3-CEL-BIBLIO-COMMENTS-STALE-01`: commentaires Biblio a aligner avec
  agent-first.
- `P3-CEL-AGENDA-DORMANT-WORDING-01`: requalifie P3 faible/stale partiel,
  `needs_targeted_validation`.
- `P3-CEL-LOG-FRONTEND-DENYLIST-01`: `/log` UI a passer en allowlist ou test
  sentinelle champ inconnu.
- `P3-CEL-FILENAMES-CONTENT-FREE-DECISION-01`: doctrine filenames a trancher.
- `P3-CEL-LARGE-FILES-AMPLIFIED-01`: fusionne dans `P3-CEL-LARGE-FILES-01`.

### POST-V1

- Mail runtime: explicitement `spec_only` pour Frida 1.0, `send_allowed=false`.
- Agenda Lot 9/capacites riches: dormant post-V1.
- Reset observabilite destructif: gated post-cloture avec GO operateur.
- Refactors massifs: post-P1/P2 uniquement.

### INVALID/STALE

- `admin_routes_without_local_guard`: invalide comme P1; garde global
  `before_request` existe pour `/api/admin/*`.
- `pycache/pyc`: absent apres scan.
- `utils.py/helpers.py`: absent.
- JSONL baselines: 123 fichiers, 709 records, 0 erreur JSON.
- Ancienne reference active vers `todo-todo/product/frida-v1-final-audit-todo.md`:
  absente.

## Synthese plateforme

- Containers actifs: 30.
- Ports publies host: Caddy seul publie `80/443`; les autres ports observes
  sont internes Docker.
- FridaDev public `/admin`, `/api/admin/logs` et `fridadev-db` repondent par
  `HTTP 302` vers Authelia sans cookie affiche.
- Reseaux Docker: 9 reseaux locaux observes, dont `platform_platform_net`,
  `platform_auth_net`, `platform_fridadev_db_net`, `platform_proxy_net`.
- Volumes Docker nommes: 3.
- Logs bornes: 30 containers, `since=30m tail=200`, aucune ligne brute
  imprimee.
- Backups/zones: `/opt/platform/backups` environ 125M,
  `_codex_backups` environ 1.6G, `_codex_reports` environ 92M.

## Synthese applicative

- Branche audit creee depuis `main` propre.
- `app/server.py`: 1850 lignes, 64 routes.
- Fichiers code/tests/web analyses: 653.
- Fichiers >=500 lignes: 166; >=600 lignes: 114.
- Routes admin: garde global observe; tests admin historiques encore axes sur
  knobs obsoletes.
- Continuity Capsule: active durablement selon docs/specs; scan ciblage sans
  affichage du texte brut.
- Mail: spec-only V1, runtime post-V1.
- Agenda: dormant post-V1.
- Artefacts JSONL: valides syntaxiquement.

## Commandes executees

- `git fetch origin main`
- `git switch main`
- `git pull --ff-only origin main`
- `git switch -c FridaV1-Mega-Audit-Code-Stack`
- `git status --short --branch`
- `git log -8 --oneline`
- `git diff --check`
- `git diff --cached --check`
- `find app -path "*__pycache__*" -o -name "*.pyc"`
- `find app -type f ( -name utils.py -o -name helpers.py )`
- `find /opt/platform ... docker-compose/Caddyfile/env` metadata only
- `docker ps`, `docker network ls`, `docker volume ls`
- `docker inspect` summarized fields only
- `docker logs --since 30m --tail 200` summarized counts only
- `curl -sSI` public endpoints with cookies filtered
- Python scans content-free for permissions, JSONL, routes, sizes, docs,
  secret-like fixtures and patterns.

## No-go de correction dans ce lot

- Ne pas chmod, supprimer, deplacer ou purger avant lot Sauron dedie.
- Ne pas modifier Caddy/Authelia/Docker/DB/Nextcloud.
- Ne pas corriger code runtime dans le lot baseline.
- Ne pas lire ni afficher les lignes Authelia/Caddy marquees secret-like sans
  protocole Sauron dedie.
- Ne pas refactorer `server.py` ou les gros modules avant golden tests.
