# Frida Mini - exploitation (etat actuel)

## 1) Scope
Frida Mini est une application web locale (Flask + UI statique) executee uniquement via Docker stack.
Objectif: chat local, memoire conversationnelle, admin panel, metriques et outils annexes.

## 2) Architecture active vs legacy
### Architecture active (source unique)
- Repo: `/home/tof/docker-stacks/frida-mini`
- Service runtime: `docker compose` (`frida-mini-docker`)
- Port expose: `8090 -> 8089`
- Donnees persistantes:
  - `state/conv` -> `/app/conv`
  - `state/logs` -> `/app/logs`
  - `state/data` -> `/app/data`

### Legacy (a ne pas utiliser)
- Ancien chemin: `/home/tof/apps/kiki-mini` (inactif)
- Ancien service systemd: `frida-mini.service` (doit rester desactive)

## 3) Fichiers importants
- App: `app/server.py`
- Config env: `app/.env` (non versionne)
- Exemple env: `app/.env.example`
- Compose: `docker-compose.yml`
- Logs admin: `/app/logs/admin.log.jsonl` (host: `state/logs/admin.log.jsonl`)
- Script diagnostic: `scripts/doctor.sh`
- Script migration logs: `scripts/migrate_admin_logs.sh`
- Script migration conversations JSON -> DB: `scripts/migrate_conversations_db.py`

## 4) Demarrage standard
```bash
cd /home/tof/docker-stacks/frida-mini
docker compose up -d --build frida-mini-docker
```

## 5) Verification rapide (runbook)
```bash
cd /home/tof/docker-stacks/frida-mini
make doctor
curl -s http://127.0.0.1:8090/ >/dev/null && echo "web: ok"
make check-conversations-db
```

Checks attendus:
- container `frida-mini-docker` en `running`
- hash `app/config.py` host == hash `/app/config.py` conteneur
- variables critiques presentes dans `app/.env`
- ancien service systemd desactive/inactif

## 6) Admin API security (profil home-lab)
- Historique obsolete depuis le `2026-04-08`:
  - ce document decrit un ancien modele avec allowlist CIDR et header `X-Admin-Token`
  - le runtime courant n'utilise plus de token admin applicatif pour `/api/admin/*`
  - la protection publique attendue repose sur Authelia

## 7) Logs et retention
- Ecriture runtime: `/app/logs/admin.log.jsonl`
- Rotation auto:
  - quotidienne
  - ou depassement de taille (`FRIDA_ADMIN_LOG_MAX_BYTES`)
- Retention fichiers rotates: `FRIDA_ADMIN_LOG_MAX_FILES`
- Migration legacy possible:
```bash
cd /home/tof/docker-stacks/frida-mini
make migrate-admin-logs
```


## 8) Migration conversations JSON -> DB
Le runtime lit prioritairement la DB (`conversations` + `conversation_messages`) et conserve les JSON pour rollback rapide.

Verification de parite (strict):
```bash
cd /home/tof/docker-stacks/frida-mini
make check-conversations-db
```

Migration (idempotente):
```bash
cd /home/tof/docker-stacks/frida-mini
make migrate-conversations-db
```

Les rapports sont ecrits dans `state/data/migrations/`.

## 9) Rollback (safe)
1. Identifier commit stable:
```bash
git log --oneline -n 10
```
2. Revenir sur commit cible:
```bash
git checkout <commit_or_tag>
```
3. Rebuild/restart:
```bash
docker compose up -d --build frida-mini-docker
```
4. Valider:
```bash
make doctor
```

## 10) Recovery secrets
Si suspicion de fuite:
1. Regenerer les secrets externes (OpenRouter, embedding, DB password).
2. Mettre a jour uniquement `app/.env`.
3. Redemarrer:
```bash
docker compose up -d --build frida-mini-docker
```
4. Verifier:
```bash
make doctor
```

## 11) Notes operateur
- Ne pas lancer de service systemd concurrent pour Frida Mini.
- Ne pas ecrire de secrets dans le code Python.
- Toujours valider avec `make doctor` apres changement infra/runtime.
