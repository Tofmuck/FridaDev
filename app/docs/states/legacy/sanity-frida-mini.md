# Sanity Plan - Frida Mini

Date: 2026-03-22
Scope: correction priorisee en 3 blocs (`securite`, `coherence runtime`, `UX persistance conversations via DB`).

## Contexte
Ce plan part des constats suivants:
- P0: drift critique repo vs conteneur en execution, avec secrets hardcodes dans le conteneur.
- P1: logs admin ecrits hors volume persistant attendu.
- P1: endpoints admin exposes sans authentification.
- P2: persistance conversations mixte (JSON serveur + threads en localStorage), non synchronisee multi-device.
- P3: documentation interne partiellement obsolete.

## Bloc 1 - Securite (priorite immediate)
Objectif: supprimer le risque de fuite/prise de controle le plus critique sans casser le service.

### 1.1 Couper le drift de configuration et sortir tous les secrets du code
- [x] Extraire toutes les valeurs sensibles de `app/config.py` runtime conteneur (API keys, embed token, DSN, endpoints secrets).
- [x] Aligner le conteneur sur la version Git de `app/config.py` (aucun secret en valeur par defaut).
- [x] Mettre toutes les variables sensibles dans `app/.env` (local non versionne) uniquement.
- [x] Verifier que `.gitignore` couvre bien `app/.env`, `*.env`, dumps et backups de secrets.
- [x] Rotation immediate des secrets potentiellement exposes (OpenRouter, embedding, DSN/mot de passe DB).

Acceptance checks:
- `sha256sum app/config.py` (host) == `sha256sum /app/config.py` (conteneur).
- `grep` dans le repo: aucune cle/token/DSN en dur.
- Redemarrage conteneur OK + `/api/chat` fonctionnel.

### 1.2 Ajouter une authentification admin minimale (profil home-lab)
- [x] Ajouter un controle d'acces sur toutes les routes `/api/admin/*`.
- [x] Activer un token statique en header (`X-Admin-Token`) via env `FRIDA_ADMIN_TOKEN`.
- [x] Journaliser les acces refuses (sans loguer les secrets).
- [ ] (Optionnel plus tard) Basculer vers Basic Auth avec hash (`bcrypt`) si besoin.

Routes cibles a proteger:
- `GET /api/admin/logs`
- `POST /api/admin/restart`
- `POST /api/admin/budget/increase`
- `GET/POST /api/admin/hermeneutics/*`

Acceptance checks:
- Sans token (si `FRIDA_ADMIN_TOKEN` defini): `401`.
- Avec token valide: acces normal.
- Aucun endpoint admin accessible anonymement sur le LAN.

### 1.3 Durcir l'exposition reseau (baseline locale)
- [x] Confirmer que les ports sensibles ne sont pas inutilement publies (admin/debug).
- [x] Limiter l'accessibilite admin au LAN interne via allowlist CIDR (`FRIDA_ADMIN_ALLOWED_CIDRS`).
- [x] Verifier l'absence de CORS permissif global sur routes admin.

Acceptance checks:
- Scan local: seuls ports voulus ouverts.
- Test externe/depuis segment non autorise: acces admin bloque.

## Bloc 2 - Coherence Runtime (priorite haute)
Objectif: garantir que ce qui tourne == ce qui est versionne, et que les donnees critiques sont persistantes.

### 2.1 Verrouiller la coherence code/runtime
- [x] Definir une source unique d'execution: stack Docker `docker-stacks/frida-mini`.
- [x] Garder l'ancien service systemd desactive (deja fait).
- [x] Ajouter une verification de drift au demarrage (hash fichier critique logue).
- [x] Ajouter une commande de diagnostic (`make doctor` ou script shell) qui verifie:
  - image active,
  - commit actif,
  - hash config,
  - variables env requises.

Acceptance checks:
- Rapport `doctor` passe au vert.
- Plus aucune ambiguite entre `apps/kiki-mini` et `docker-stacks/frida-mini`.

### 2.2 Corriger la persistence des logs admin
- [x] Changer `admin_logs.py` pour ecrire dans `/app/logs/admin.log.jsonl` (volume monte).
- [x] Migrer/concatener proprement les logs existants de `app/admin/logs/` vers `state/logs/`.
- [x] Supprimer `app/admin/logs/` du runtime applicatif (ou en faire un symlink explicite vers `/app/logs`).
- [x] Ajouter rotation (taille/jour) pour eviter gonflement infini.

Acceptance checks:
- Un seul fichier de logs runtime persistant: `state/logs/admin.log.jsonl`.
- Rebuild conteneur: logs conserves.
- `git status`: plus de `app/admin/logs/` non suivi.

### 2.3 Mettre a jour la doc d'exploitation
- [x] Reviser `app/docs/states/PROJET.md` pour reflecter le vrai contexte actuel (paths, docker, endpoints, auth admin).
- [x] Ajouter un runbook court: demarrage, verification, rollback, recovery secrets.
- [x] Ajouter une section "architecture active" vs "legacy".

Acceptance checks:
- Un nouvel arrivant peut redemarrer le systeme sans ambiguite.
- Plus de references fausses a `/home/tof/apps/kiki-mini` comme source active.

## Bloc 3 - UX Persistance Conversations via DB (priorite fonctionnelle)
Objectif: rendre la liste des conversations coherente et partagee entre devices/profils (sans perte de contenu).

### 3.1 Introduire un vrai catalogue serveur de conversations
- [x] Creer une table DB `conversations` (id, title, created_at, updated_at, message_count, last_message_preview, deleted_at).
- [x] Continuer a stocker les messages (JSON actuel) dans une phase transitoire, mais le "listing" doit venir du serveur.
- [x] Ajouter endpoints:
  - `GET /api/conversations` (liste paginee)
  - `POST /api/conversations` (nouvelle conversation)
  - `PATCH /api/conversations/<id>` (rename)
  - `DELETE /api/conversations/<id>` (soft delete)
  - `GET /api/conversations/<id>/messages` (historique)

Acceptance checks:
- Deux clients differents voient la meme liste et les memes titres.
- Changement de navigateur: la sidebar reste intacte.

### 3.2 Migrer le front de `localStorage` vers API serveur
- [x] Remplacer `kiki.threads` / `kiki.current` comme source de verite par l'API serveur.
- [x] Garder `localStorage` seulement pour preferences UI (temperature, top_p, toggles).
- [x] Implementer synchronisation optimiste + fallback reseau propre.
- [x] Afficher etat offline clair sans ecraser l'etat serveur.

Acceptance checks:
- Sidebar issue du backend uniquement.
- Rename/delete/new thread refletent partout quasi en temps reel.

### 3.3 Finaliser la migration messages vers DB (option recommandee)
- [x] Soit conserver JSON long terme avec index DB metadata, soit migrer messages en table `conversation_messages`.
- [x] Si migration DB:
  - [x] script de migration des JSON existants,
  - [x] checksum / comptage avant-apres,
  - [x] rollback possible.
- [x] Conserver compatibilite API `/api/chat` pendant la transition.

Acceptance checks:
- Zero perte de conversations historiques.
- Perf de listing et chargement stable sous charge normale.

## Ordre d'execution recommande
1. Bloc 1.1 (secrets + drift config) - immediat.
2. Bloc 1.2 (auth admin) - immediat.
3. Bloc 2.2 (logs persistants) - juste apres.
4. Bloc 2.1 + 2.3 (coherence + doc).
5. Bloc 3.1 -> 3.2 -> 3.3 (UX DB progressive).

## Strategie de livraison
- Sprint A (urgence): Bloc 1 complet + 2.2.
- Sprint B (stabilisation): Bloc 2.1 + 2.3.
- Sprint C (UX data): Bloc 3 complet en migration progressive.

## Risques et mitigations
- Risque: coupure service lors rotation secrets.
  - Mitigation: rotation par etapes + test healthcheck apres chaque secret.
- Risque: regression admin suite auth.
  - Mitigation: test automatises routes admin (200/401) + token de secours.
- Risque: perte de conversations pendant migration UX/DB.
  - Mitigation: migration en double ecriture temporaire + scripts de verification + rollback.

## Definition of Done globale
- [ ] Aucun secret hardcode dans code/image.
- [ ] Endpoints admin inaccessibles sans auth.
- [ ] Logs admin centralises et persistants via volume prevu.
- [ ] Runtime docker coherent avec code versionne.
- [x] Liste conversations serveur (multi-device) et UX stable sans dependance `localStorage` pour les threads.
- [ ] Documentation operationnelle alignee sur la realite.
