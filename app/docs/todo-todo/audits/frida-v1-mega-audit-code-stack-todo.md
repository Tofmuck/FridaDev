# Frida V1 - Mega audit code + stack TODO

Statut: TODO actif.
Date d'ouverture: 2026-06-24.
Branche de travail: `FridaV1-Mega-Audit-Code-Stack`.
Audit source: `app/docs/todo-todo/audits/frida-v1-mega-audit-code-stack-2026-06-24.md`.

## Etat global

- Objectif: nettoyer et durcir methodiquement FridaDev + stack OVH apres
  integration Frida V1 sur `main`.
- Mode: double discipline Sauron/Celebrimbor.
- Runtime modifie par Lot 0: non.
- Plateforme modifiee par Lot 0: non.
- Secrets/logs bruts affiches par Lot 0: non.
- P0 connu: aucun.
- P1 connus: permissions secrets/backups plateforme.

## Registre findings

### P1-SAU-ENV-PERMISSIONS-01

- Statut initial: open.
- Severite: P1.
- Fichiers/zones suspects: `/opt/platform/.env`.
- Lot cible: Lot 1.
- Critere de cloture: permissions resserrees ou exception documentee,
  verification Compose/health sans secret affiche.
- Preuve minimale: `stat` content-free avant/apres, `docker compose config
  --quiet`, health Caddy/FridaDev.
- Hors-scope: rotation secret, changement contenu `.env`, restart large.

### P1-SAU-SENSITIVE-BACKUPS-PERMS-01

- Statut initial: open.
- Severite: P1.
- Fichiers/zones suspects: `/opt/platform/backups`,
  `/opt/platform/_codex_backups`, `/opt/platform/_codex_reports`,
  `/opt/platform/data/*`, dumps DB, archives, keys.
- Lot cible: Lot 2.
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
  compose global.
- Lot cible: Lot 3.
- Critere de cloture: matrice consumers/endpoints/reseaux.
- Preuve minimale: `docker inspect` content-free, compose metadata,
  eventuellement test consumer.
- Hors-scope: couper socket proxy sans connaitre dependances.

### P2-SAU-COMPOSE-PERMISSIONS-01

- Statut initial: open.
- Severite: P2.
- Zones suspectes: compose FridaDev group-writable.
- Lot cible: Lot 2 ou 3.
- Critere de cloture: modes/ownership explicites et verifies.
- Preuve minimale: `stat`, `docker compose config --quiet`.
- Hors-scope: changement runtime.

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

### P2-CEL-EXCEPTION-RAW-SURFACE-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: `app/server.py`, `app/tools/web_search.py`,
  `app/core/*`, `app/memory/*`, `app/observability/*`, `app/biblio/*`.
- Lot cible: Lot 6.
- Critere de cloture: surfaces qualifiees; corrections bornees uniquement.
- Preuve minimale: tests content-free/fail-closed par surface.
- Hors-scope: remplacement massif aveugle de `str(exc)`.

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
- Lot cible: Lot 9.
- Critere de cloture: plan de split par responsabilite et golden tests routes.
- Preuve minimale: snapshot routes, tests routes/admin/workspace/chat.
- Hors-scope: refactor sans tests.

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

## Lots proposes

### Lot 0 - Baseline audit et registre

- [x] Creer l'audit baseline content-free.
- [x] Creer la TODO de remediation.
- [x] Classer P0/P1/P2/P3/POST-V1/INVALID.
- [x] Ne modifier ni runtime ni plateforme.

### Lot 1 - Securite plateforme P1 immediate

- [ ] Traiter `P1-SAU-ENV-PERMISSIONS-01`.
- [ ] Verifier ownership/mode `.env` et compat Compose.
- [ ] Ne pas lire ni afficher les valeurs.
- [ ] Produire preuve health apres correction si correction autorisee.

### Lot 2 - Secrets/env/logs/permissions

- [ ] Traiter backups/dumps/keys world-readable.
- [ ] Qualifier logs Authelia/Caddy secret-like.
- [ ] Traiter compose group-writable si confirme.
- [ ] Definir retention et mode cible.

### Lot 3 - Docker/Caddy/Authelia/reseaux

- [ ] Auditer socket proxy et consumers.
- [ ] Auditer reseaux et frontieres public/interne.
- [ ] Verifier hostnames Caddy/Authelia sans exposer secrets.
- [ ] Valider pas de service public hors Caddy.

### Lot 4 - Code runtime P1/P2

- [ ] Qualifier appels HTTP et timeouts.
- [ ] Chercher vrais dead paths ou NotImplemented runtime.
- [ ] Ne corriger que findings valides et bornes.

### Lot 5 - Admin/security/app routes

- [ ] Aligner tests admin sur contrat proxy/loopback.
- [ ] Verifier routes admin registerees par modules.
- [ ] Verifier admin HTML/public host vs API guard.
- [ ] Garder Authelia comme frontiere publique.

### Lot 6 - Observabilite/logs applicatifs

- [ ] Qualifier `str(exc)`, raw, payload, traceback, print.
- [ ] Corriger seulement surfaces qui exposent ou masquent une panne.
- [ ] Conserver diagnostics content-free.

### Lot 7 - Tests/smokes/artefacts

- [ ] Construire matrice live/fake/mock/covered_by_tests.
- [ ] Verifier JSONL et anti-fuite.
- [ ] Gerer fixtures secret-like par allowlist ou sentinelles.

### Lot 8 - Docs/source-of-truth

- [ ] Reclasser audits superseded encore en `todo-todo/audits`.
- [ ] Clarifier checkboxes historiques.
- [ ] Mettre a jour index si chemins bougent.

### Lot 9 - Refactors cibles

- [ ] Prioriser `server.py` et gros modules.
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
