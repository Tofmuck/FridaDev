# Frida V1 - Final closure TODO

Statut: TODO actif - pilote canonique de cloture finale Frida V1
Date: 2026-06-23
Branche courante: `FridaV1-Continuity-Payload-Audit`
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`
Audit principal: `app/docs/todo-todo/audits/frida-v1-final-global-audit-2026-06-23.md`
Contre-audit: `app/docs/todo-todo/audits/frida-v1-final-global-counter-audit-2026-06-23.md`

Ce fichier est le seul point de pilotage actif pour la cloture finale Frida V1.
Il remplace la TODO squelettique precedente et transforme la comparaison audit /
contre-audit en lots executables. Il ne corrige aucun finding runtime ou produit
par lui-meme.

## 1. Etat global

### Branche et cible Git

- Branche active lue pendant le cadrage: `FridaV1-Continuity-Payload-Audit`.
- Relation observee avec `origin/main`: `origin/main` est ancetre de la branche
  courante, mais `HEAD` n'est pas encore contenu dans `origin/main`.
- Consequence: Frida V1 ne doit pas etre declaree close sur `main` tant que la
  strategie d'integration n'est pas explicite et verifiee.
- Aucun merge vers `main` n'est autorise par cette TODO sans demande ulterieure.

### Statut V1

- Cloture V1 possible: conditionnelle.
- Risque global: moyen tant que les P2 ne sont ni fermes, ni acceptes
  explicitement comme risques residuels.
- Continuity Capsule: livree, bornee, desactivee par defaut; activation
  uniquement apres micro-preuve et GO operateur dedie.
- Agenda: utile et cloture pragmatiquement pour V1, mais statut documentaire
  encore ambigu dans sa TODO active.
- Mail: bonus non bloquant; audit/spec-only possible, runtime a reporter sauf
  GO operateur separe.

### Deja clos pour Frida V1

- Nextcloud folders V1: archive Lot Z `met`.
- Documents ingestion V1: archive Lot Z `met_with_documented_limit`.
- Notes Markdown V1: archive Lot Z `met_with_documented_limit`.
- Exports V1: archive Lot Z `met`.
- Images generees V1: archive Lot Z `met`.
- Observabilite agentique V1: archive Lot Z `met`, reset destructif non execute.
- Continuity Payload V1: archive Lot Z `met`, capsule runtime livree disabled.
- Biblio: chantiers produits V1 clos par archives et artefacts.
- Agenda: cloture pragmatique V1, a traiter comme dormant post-V1 sauf bug reel.

### Bloquants avant cloture propre

- Durcissement ou decision explicite sur `/api/admin/logs` legacy.
- Fail-closed des lectures logs admin si panne de lecture.
- Alignement docs/source-of-truth pour Nextcloud folders, Agenda, Continuity
  audits et pointeurs actifs/archives.
- Matrice finale de cloture et decision branche/main.
- Micro-preuve ou report explicite de la Continuity Capsule.
- Decision Mail: audit/spec-only borne ou report post-V1.

### Reportes post-V1 ou non bloquants

- Mail runtime.
- SMS.
- TTS.
- Agenda Lot 9 / disponibilites riches / invitations / rappels / recurrences
  riches / mutations utilisateur reelles.
- Reset observabilite destructif sans GO operateur humain explicite, date et
  separe.
- Refactors de gros fichiers runtime hors finding cible.
- Nettoyage exhaustif des archives historiques non contradictoires.

## 2. Axes de cloture issus des deux audits

1. Durcissement P2 des logs/admin:
   `/api/admin/logs` legacy et lectures logs fail-closed.
2. Correction P2 docs/source-of-truth:
   Nextcloud folders, Agenda dormant, audits Continuity actifs, pointeurs
   archives et index.
3. Final audit TODO/matrice + strategie branche/main:
   ce fichier, Lot 3 et Lot 4.
4. Micro-preuve d'activation de la Continuity Capsule:
   preuve bornee ou report explicite, jamais activation implicite.
5. Mail:
   audit/spec-only avant V1 ou report post-V1 explicite, pas runtime par defaut.

## 3. Registre des findings

### P2-FINAL-AUDIT-MATRIX-01

- Statut initial: accepted, traite par Lot 0 dans ce fichier.
- Severite: P2.
- Fichiers suspects: `app/docs/todo-todo/product/frida-v1-final-audit-todo.md`.
- Lot cible: Lot 0 puis Lot 3.
- Critere de cloture: TODO finale granulaire presente, puis matrice finale GO /
  PARTIAL / NO-GO executable en Lot 3.
- Preuve minimale: diff docs-only, `git diff --check`, grep du fichier canonique.
- Hors-scope: corriger les autres P2 dans le meme patch.

### P2-ADMIN-LOGS-LEGACY-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: `app/server.py`, `app/admin/admin_logs.py`,
  `app/core/chat_llm_flow.py`.
- Lot cible: Lot 1A.
- Critere de cloture: `/api/admin/logs` legacy est soit depreciee clairement,
  soit projetee/redactee au niveau content-free attendu de
  `/api/admin/logs/chat`.
- Preuve minimale: tests route admin, sentinelles anti-fuite, scan `str(exc)` /
  `error=str(exc)` sur le scope touche.
- Hors-scope: refonte dashboard large, suppression non demandee de l'historique.

### P2-LOG-READ-FAIL-CLOSED-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: `app/observability/log_store.py`, `app/server.py`,
  `app/admin/admin_logs.py`.
- Lot cible: Lot 1B.
- Critere de cloture: une panne de lecture logs ne repond plus `ok: true` avec
  liste vide; elle devient `ok=false` ou statut 5xx avec reason code content-free.
- Preuve minimale: test fake de panne lecture, reponse API fail-closed sans cause
  brute, log technique redige.
- Hors-scope: exposer traceback, chemin, contenu ou exception brute.

### P2-DOCS-SOURCE-OF-TRUTH-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: README, `app/docs/README.md`, roadmap finale, specs V1,
  TODO actives et archives citees par les deux audits.
- Lot cible: Lots 2A, 2B, 2C, 2D.
- Critere de cloture: aucune source active ne contredit l'etat Lot Z des
  chantiers V1; les historiques restent lisibles comme historiques.
- Preuve minimale: grep de pointeurs actifs/archives, diff docs-only, inventaire
  des chemins source-of-truth.
- Hors-scope: reecrire les preuves historiques ou rouvrir les chantiers clos.

### P2-NEXTCLOUD-SPEC-STALE-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`.
- Lot cible: Lot 2A.
- Critere de cloture: les passages qui disent Documents/Notes/Exports/Images
  futurs sont requalifies comme historiques ou alignes sur les specs dediees
  cloturees.
- Preuve minimale: grep `Documents|Notes|Exports|Images|futur|a livrer`, diff
  docs-only, verification des liens vers specs dediees.
- Hors-scope: modifier le contrat runtime de ces chantiers dedies.

### P2-AGENDA-DORMANT-STATUS-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: `app/docs/todo-todo/product/frida-agenda-agent.md`,
  `app/docs/states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`.
- Lot cible: Lot 2B.
- Critere de cloture: Agenda est decrit sans ambiguite comme V1
  pragmatiquement clos et post-V1 dormant; les cases ouvertes sont non
  bloquantes pour Frida 1.0.
- Preuve minimale: diff docs-only, grep `Statut`, grep `Lot 9`, verification
  des pointeurs README/app docs/roadmap.
- Hors-scope: rouvrir Agenda runtime, lire CalDAV, lancer un Lot 9.

### P2-CONTINUITY-AUDITS-ACTIVE-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects:
  `app/docs/todo-todo/audits/frida-v1-continuity-payload-audit-2026-06-22.md`,
  `app/docs/todo-todo/audits/frida-v1-continuity-payload-counter-audit-2026-06-22.md`,
  `app/docs/todo-done/product/frida-v1-continuity-payload-todo.md`.
- Lot cible: Lot 2C.
- Critere de cloture: les audits sources ne peuvent plus etre lus comme
  findings vivants apres Lot Z Continuity.
- Preuve minimale: en-tete superseded ou deplacement conforme a la convention,
  grep des P1/P2/P3 Continuity et pointeur vers l'archive.
- Hors-scope: reecrire les constats historiques ou les artefacts Lot Z.

### P2-BRANCH-INTEGRATION-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: etat Git, roadmap finale, rapport Lot Z final.
- Lot cible: Lot 4.
- Critere de cloture: decision explicite sur integration vers `main` ou
  non-integration temporaire; etat propre, commits pousses, verification apres
  merge si merge demande.
- Preuve minimale: `git status --short --branch`, `git log --oneline`, relation
  avec `origin/main`, hash de decision.
- Hors-scope: effectuer le merge dans cette TODO.

### P2-CAPSULE-ACTIVATION-PROOF-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: `app/core/continuity_capsule.py`,
  `app/core/chat_service.py`, contrat et archive Continuity Payload.
- Lot cible: Lot 5.
- Critere de cloture: soit micro-preuve complete avec texte operateur approuve,
  soit report explicite de l'activation post-V1.
- Preuve minimale: disabled -> enabled normal -> unsafe refused -> final-lock
  bypass -> rollback disabled, sans contenu de capsule brut dans logs/proofs.
- Hors-scope: activation durable sans GO operateur dedie.

### P2-MAIL-RUNTIME-SCOPE-01

- Statut initial: open.
- Severite: P2 si runtime pris avant cloture; bonus sinon.
- Fichiers suspects: `app/docs/todo-todo/product/frida-v1-mail-bonus-todo.md`.
- Lot cible: Lot 6.
- Critere de cloture: decision explicite audit/spec-only ou report post-V1;
  aucun Mail runtime ne bloque Frida 1.0.
- Preuve minimale: TODO/spec Mail mise a jour, invariants no-send/no-secret
  explicites, aucun code runtime modifie.
- Hors-scope: IMAP/SMTP/Nextcloud Mail live, envoi, brouillon runtime, secret.

### P3-ROADMAP-BRANCH-STALE-01

- Statut initial: open, confirme par audits.
- Severite: P3.
- Fichiers suspects: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`.
- Lot cible: Lot 2D.
- Critere de cloture: la branche historique affichee est corrigee ou remplacee
  par une formulation non volatile.
- Preuve minimale: grep `Branche de travail courante`.
- Hors-scope: decision merge/main.

### P3-README-DATE-STALE-01

- Statut initial: open, confirme par audits.
- Severite: P3.
- Fichiers suspects: `README.md`.
- Lot cible: Lot 2D.
- Critere de cloture: l'en-tete d'etat ne contredit plus les livraisons
  documentees jusqu'au 2026-06-23.
- Preuve minimale: grep date README, diff docs-only.
- Hors-scope: reecrire toute la presentation runtime.

### P3-ARCHIVE-CHECKBOXES-01

- Statut initial: open.
- Severite: P3.
- Fichiers suspects: `app/docs/todo-done/product/*`.
- Lot cible: Lot 3 ou Lot 2D selon portee.
- Critere de cloture: les checkboxes ouvertes historiques ne sont plus prises
  pour des TODO actives, par annotation ou matrice finale.
- Preuve minimale: `grep -RIn "\\[ \\]" app/docs/todo-done/product`.
- Hors-scope: cocher artificiellement des limites volontairement documentees.

### P3-CAPSULE-FINAL-LOCK-OBSERVABILITY-01

- Statut initial: open.
- Severite: P3.
- Fichiers suspects: `app/core/continuity_capsule.py`,
  `app/docs/states/specs/frida-v1-continuity-payload-contract.md`.
- Lot cible: Lot 5.
- Critere de cloture: ordre unsafe vs final-lock clarifie; soit statut actuel
  accepte comme non-injection sure, soit refus unsafe rendu observable avant
  bypass si cela ne casse pas le contrat.
- Preuve minimale: test final-lock + unsafe, manifeste content-free.
- Hors-scope: activer la capsule durablement.

### P3-LARGE-FILES-01

- Statut initial: post-V1 sauf si un lot cible touche le fichier.
- Severite: P3.
- Fichiers suspects: `app/server.py`, `app/core/chat_service.py`,
  `app/observability/dashboard_read_model.py`, `app/biblio/librarian_tools.py`.
- Lot cible: aucun lot de correction final par defaut; vigilance sur tous les
  lots runtime.
- Critere de cloture: pas de rallonge opportuniste; si un patch touche un gros
  fichier, verifier la responsabilite et envisager extraction bornee.
- Preuve minimale: `wc -l` cible avant gros patch.
- Hors-scope: refactor structurel opportuniste avant cloture V1.

### Findings supplementaires a garder visibles

- `P3-ARCHIVE-REFERENCES-STALE-01`: references historiques vers anciens chemins
  actifs; Lot 2D si elles troublent la matrice finale.
- `P3-SCOPED-LOG-DELETE-GATE-01`: suppression logs scopee a cadrer comme admin
  courante ou reset partiel; Lot 3 decision, pas reset.
- `P3-STATUS-FLATTENING-01`: certains emitters peuvent aplatir des statuts non
  `error` en `ok`; Lot 7 ou micro-audit cible seulement si zero-erreur exige.
- `P3-BIBLIO-AUDIT-CURRENT-STALE-01`: audit Biblio ancien presente comme courant;
  Lot 2D si la cloture finale parcourt toutes les sources.
- `P3-PROOF-LIVE-COVERAGE-01`: preuves fake/unit ou `covered_by_tests`
  documentees; Lot 3 matrice, sans reexecution live inutile.

## 4. Lots proposes

### Lot 0 - TODO finale et registre de cloture

Type: docs-only.

- [x] Reprendre `app/docs/todo-todo/product/frida-v1-final-audit-todo.md` comme
  fichier canonique de pilotage final.
- [x] Integrer audit principal et contre-audit.
- [x] Creer un registre stable de findings P2/P3.
- [x] Declarer les cinq axes de cloture.
- [x] Definir les lots 1A a Z avec preuves et hors-scope.
- [x] Cocher uniquement le Lot 0.

Preuve minimale:

- `git status --short --branch`
- `git diff --check`
- grep des references final audit/final TODO
- absence pycache/temp
- absence `utils.py` / `helpers.py`

Rebuild: non.
Artefact JSONL: non.

### Lot 1A - Admin logs legacy content-free

Type: runtime cible.

- [ ] Relire `/api/admin/logs`, `/api/admin/logs/chat` et projections associees.
- [ ] Decider: deprecation explicite de legacy ou projection/redaction stricte.
- [ ] Remplacer les sorties `error=str(exc)` du scope touche par reason code /
  `error_class` content-free.
- [ ] Preserver compat UI uniquement si elle reste explicite et testee.
- [ ] Ne pas toucher au dashboard large.

Commandes/preuves minimales:

- grep scope `admin_logs|/api/admin/logs|str(exc)|error=str(exc)`.
- tests unitaires/serveur cibles admin logs.
- scan anti-fuite sur champs `raw`, `payload`, `error`, `message_short`.

Rebuild: oui si runtime deploye.
Artefact JSONL: seulement si le lot produit une preuve content-free utile.

### Lot 1B - Log read fail-closed

Type: runtime cible.

- [ ] Construire un test fake de panne lecture logs chat.
- [ ] Construire un test fake de panne lecture logs legacy si legacy conservee.
- [ ] Faire retourner `ok=false` ou 5xx avec reason code content-free.
- [ ] Verifier que la cause brute n'est jamais exposee.

Commandes/preuves minimales:

- tests serveur cibles.
- grep `return []` et `ok: true` sur lecteurs/routes logs.
- scan anti-fuite sur exception brute.

Rebuild: oui si runtime deploye.
Artefact JSONL: non par defaut.

### Lot 2A - Docs source-of-truth Nextcloud/Folders

Type: docs-only sauf decouverte contraire.

- [ ] Requalifier les formulations stale sur Documents/Notes/Exports/Images.
- [ ] Distinguer socle folders historique des lots dedies clos.
- [ ] Pointer vers les specs dediees cloturees.
- [ ] Ne pas modifier les preuves historiques.

Commandes/preuves minimales:

- `rg -n "Documents|Notes|Exports|Images|futur|a livrer" app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
- `git diff --check`
- grep des liens vers specs dediees.

Rebuild: non.
Artefact JSONL: non.

### Lot 2B - Agenda dormant/actif

Type: docs-only.

- [ ] Trancher le statut de `frida-agenda-agent.md`: post-V1 dormant ou archive.
- [ ] Indiquer que les cases ouvertes sont des reprises post-V1, pas des no-go.
- [ ] Conserver la cloture pragmatique comme source V1.
- [ ] Ne pas lire CalDAV, ne pas relancer de smoke live.

Commandes/preuves minimales:

- grep `Statut|Lot 9|cloture pragmatique|post-V1`.
- `git diff --check`.
- coherence README/app docs/roadmap.

Rebuild: non.
Artefact JSONL: non.

### Lot 2C - Continuity audits / archives

Type: docs-only.

- [ ] Requalifier les deux audits Continuity en sources historiques supersedees
  par l'archive Lot Z, ou les deplacer si la convention repo le permet.
- [ ] Garder les findings historiques intacts.
- [ ] Eviter toute confusion avec des findings Continuity vivants.

Commandes/preuves minimales:

- grep des P1/P2/P3 Continuity dans `todo-todo/audits`.
- grep des pointeurs vers `frida-v1-continuity-payload-todo.md`.
- `git diff --check`.

Rebuild: non.
Artefact JSONL: non.

### Lot 2D - Roadmap / README / index

Type: docs-only.

- [ ] Corriger ou neutraliser la branche historique dans la roadmap finale.
- [ ] Corriger la date stale README si elle reste contradictoire.
- [ ] Ajouter le pointeur vers cette TODO finale si un index actif en manque.
- [ ] Nettoyer uniquement les references stale qui troublent la cloture finale.

Commandes/preuves minimales:

- grep `frida-v1-final.*todo|final-closure|final audit`.
- grep dates/branche.
- `git diff --check`.

Rebuild: non.
Artefact JSONL: non.

### Lot 3 - Final audit matrix

Type: docs-only / preuve-only.

- [ ] Construire une matrice GO / PARTIAL / NO-GO.
- [ ] Lister tous les lots V1 clos et leurs preuves JSONL.
- [ ] Lister les tests minimaux a rejouer et ceux a ne pas rejouer.
- [ ] Distinguer smokes live requis, optionnels, inutiles ou interdits.
- [ ] Marquer reset observabilite: non execute sauf GO operateur separe.
- [ ] Marquer capsule: activee avec preuve ou reportee.
- [ ] Marquer Mail: spec-only ou reporte.
- [ ] Marquer branche/main: decidee.
- [ ] Classer P3: corriges, acceptes ou post-V1.

Commandes/preuves minimales:

- inventaire JSONL baselines V1.
- parse/validation JSONL si utile, sans afficher de contenu sensible.
- `git status --short --branch`.
- `git diff --check`.
- scans content-free bornes.

Rebuild: non.
Artefact JSONL: optionnel, seulement si demande dans le lot.

### Lot 4 - Branche/main gate

Type: Git/process.

- [ ] Verifier branche courante propre.
- [ ] Verifier absence de commits locaux non pousses.
- [ ] Verifier relation avec `origin/main`.
- [ ] Decider: merge vers `main`, PR, ou non-integration temporaire documentee.
- [ ] Si merge demande ulterieurement: verifier apres merge et apres push.

Commandes/preuves minimales:

- `git status --short --branch`
- `git log --oneline -12`
- `git log --oneline --branches --not origin/main`
- `git merge-base --is-ancestor HEAD origin/main`
- `git merge-base --is-ancestor origin/main HEAD`

Rebuild: non sauf merge suivi de changement runtime deploye.
Artefact JSONL: non.

### Lot 5 - Continuity Capsule micro-proof

Type: runtime/preuve ciblee.

- [ ] Obtenir un GO operateur dedie avant toute activation reelle.
- [ ] Resumer le texte operateur exact de facon content-free; ne jamais le
  logger ou committer brut.
- [ ] Sauvegarder la config precedente si un fichier runtime est touche.
- [ ] Prouver l'etat disabled.
- [ ] Prouver enabled normal sur texte approuve ou substitut strictement borne.
- [ ] Prouver unsafe refused.
- [ ] Prouver final-lock bypass.
- [ ] Prouver rollback disabled.
- [ ] Verifier `main_payload_manifest_v1` sans prompt/capsule brut.
- [ ] Decider activation durable ou report post-V1.

Commandes/preuves minimales:

- probe capsule content-free.
- tests capsule/final-lock cibles.
- scan logs/projections/JSONL contre contenu brut.
- `git diff --check`.

Rebuild: oui si changement runtime/config applicative deploye.
Artefact JSONL: oui si micro-preuve realisee, content-free uniquement.

### Lot 6 - Mail audit/spec-only

Type: docs-only par defaut.

- [ ] Relire `frida-v1-mail-bonus-todo.md`.
- [ ] Decider: audit/spec-only avant V1 ou report post-V1 explicite.
- [ ] Si spec-only: definir lecture no-op, brouillons, confirmations humaines,
  secrets redacted, no-send, preuves fakes.
- [ ] Interdire Mail runtime sauf GO operateur separe.

Commandes/preuves minimales:

- grep `mail|IMAP|SMTP|Nextcloud Mail|confirmation`.
- diff docs-only.
- scan secret-like dans docs modifiees.

Rebuild: non.
Artefact JSONL: non.

### Lot 7 - Final closure smoke

Type: preuve-only.

- [ ] Relire les preuves finales V1.
- [ ] Executer seulement les tests/scans bornes choisis par la matrice Lot 3.
- [ ] Produire un artefact JSONL final si demande.
- [ ] Verifier aucune fuite: secret, log brut, prompt brut, payload provider,
  contenu utilisateur brut.
- [ ] Verifier absence pycache/temp et absence `utils.py` / `helpers.py`.

Commandes/preuves minimales:

- `git status --short --branch`
- `git diff --check`
- tests conteneur cibles si requis.
- scans content-free docs/JSONL/log projections.

Rebuild: non sauf si un lot runtime precedent a ete deploye et doit etre smoke.
Artefact JSONL: oui si Lot 7 est le lot de preuve finale.

### Lot Z - Archive finale

Type: docs/preuve.

- [ ] Tous les P2 sont fermes ou acceptes explicitement avec risque residuel.
- [ ] Tous les P3 sont corriges, acceptes ou reportes post-V1.
- [ ] Branche/main est decide.
- [ ] Capsule est activee avec preuve ou reportee.
- [ ] Mail est spec-only ou reporte.
- [ ] Reset observabilite non execute sauf GO operateur separe.
- [ ] Matrice finale GO / PARTIAL / NO-GO produite.
- [ ] Cette TODO est archivee seulement apres decision finale.

Commandes/preuves minimales:

- inventaire des findings.
- inventaire des artefacts.
- grep des TODO actives.
- `git status --short --branch`
- `git diff --check`

Rebuild: non.
Artefact JSONL: selon decision de cloture finale.

## 5. Criteres de non-prolongation

- Pas de nouveau produit V1.
- Pas de nouvelle UI.
- Pas de Mail runtime.
- Pas de refactor opportuniste.
- Pas de reset/purge/backfill.
- Pas de migration DB sauf finding runtime explicite ulterieur.
- Pas de plateforme/Sauron sauf besoin valide et separe.
- Pas de correction massive `err=%s` hors finding borne.
- Pas de provider live sauf lot de preuve explicitement decide.
- Pas d'ecriture Nextcloud hors micro-lot qui l'autorise explicitement.
- Pas d'activation Continuity Capsule sans GO operateur dedie.
- Pas de reouverture Agenda ou Biblio abstraite.

## 6. Format de preuve attendu par lot

Chaque lot doit indiquer dans sa reponse:

- fichiers modifies;
- findings traites;
- findings explicitement non traites;
- commandes executees;
- resultats tests/scans;
- besoin de rebuild: oui/non;
- artefact JSONL: oui/non et chemin si oui;
- scan anti-fuite: oui/non;
- `git status --short --branch`;
- `git diff --check`;
- absence pycache/temp;
- absence `utils.py` / `helpers.py`;
- commit hash;
- push OK.

Pour un lot docs-only, remplacer les tests runtime par:

- inventaire de chemins;
- grep de references;
- coherence des liens;
- `git diff --check`;
- `git status --short --branch`.

Pour un lot runtime, ajouter:

- tests unitaires ou serveur cibles;
- preuve content-free;
- rebuild/restart applicatif si le runtime deploye change;
- verification minimale post-deploiement si applicable.

## 7. No-go avant declaration Frida V1 close

- TODO finale ou matrice finale absente.
- P2 ouvert sans decision explicite.
- Branche/main non decide.
- `/api/admin/logs` legacy non durcie ou non depreciee.
- Lecture logs pouvant masquer une panne en `ok: true`.
- Agenda simultanement actif et dormant dans les sources actives.
- Spec Nextcloud folders contredisant les lots dedies clos.
- Audits Continuity actifs lisibles comme findings vivants.
- Continuity Capsule activee sans micro-preuve et GO operateur dedie.
- Mail runtime lance comme chantier bloquant V1.
- Reset observabilite execute sans GO operateur humain explicite, date et
  separe, avec backup/rollback.
- Secret, log brut, prompt brut, payload provider ou contenu utilisateur brut
  ajoute dans docs, artefacts ou reponses.

## 8. Auto-audit permanent de cette TODO

- Un seul fichier TODO actif pilote la cloture finale: ce fichier.
- Les cinq axes audit/contre-audit sont presents.
- Les findings P2/P3 minimum demandes sont presents.
- Les findings supplementaires du contre-audit restent visibles.
- Aucun lot runtime n'est coche.
- Lot 0 seul est coche par le patch de creation/reprise.
- Aucun reset/purge/backfill/migration n'est demande implicitement.
- L'activation capsule exige un GO operateur dedie.
- Mail runtime est exclu sauf GO ulterieur separe.
- Les docs/index/roadmap ne doivent pas pointer vers un mauvais fichier actif.
- Le contenu reste content-free.
