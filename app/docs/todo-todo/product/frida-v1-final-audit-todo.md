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
- Etat Lot 4 apres `git fetch origin main` le 2026-06-23:
  `HEAD=f7beb6df35b406ec8c1ce6ca706bd497fd27208a`,
  `origin/main=966adabea40da0513d789383c75531dac3a0b45f`,
  `origin_main_ancestor_of_HEAD=0`, `HEAD_ancestor_of_origin_main=1`.
- Aucun commit local non pousse n'est observe entre `HEAD` et
  `origin/FridaV1-Continuity-Payload-Audit`.
- Decision Lot 4: non-integration temporaire. La cloture finale continue sur
  `FridaV1-Continuity-Payload-Audit` jusqu'a la fin des gates 5/6/7/Z; merge,
  PR, push vers `main` ou declaration close sur `main` exigent un GO operateur
  separe.
- Aucun merge vers `main` n'est autorise par cette TODO sans demande ulterieure.

### Statut V1

- Cloture V1 possible: conditionnelle.
- Risque global: moyen tant que les P2 ne sont ni fermes, ni acceptes
  explicitement comme risques residuels.
- Continuity Capsule: livree, bornee, desactivee par defaut; activation
  uniquement apres micro-preuve et GO operateur dedie.
- Agenda: utile et pragmatiquement clos pour V1; TODO maintenue en statut
  post-V1 dormant, non bloquante pour Frida 1.0 sauf bug reel, besoin concret
  ou decision explicite.
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
- Admin logs Lot 1A/1B: `/api/admin/logs` legacy projete content-free et
  lectures admin logs fail-closed, sans cause brute exposee.
- Biblio: chantiers produits V1 clos par archives et artefacts.
- Agenda: cloture pragmatique V1, a traiter comme dormant post-V1 sauf bug reel.

### Bloquants avant cloture propre

- Micro-preuve ou report explicite de la Continuity Capsule.
- Decision Mail: audit/spec-only borne ou report post-V1.
- Smoke final Lot 7 selon matrice Lot 3.
- Archive finale Lot Z.

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
   Nextcloud folders, Agenda dormant, audits Continuity historiques, pointeurs
   archives et index.
3. Final audit TODO/matrice + strategie branche/main:
   ce fichier, Lot 3 et Lot 4.
4. Micro-preuve d'activation de la Continuity Capsule:
   preuve bornee ou report explicite, jamais activation implicite.
5. Mail:
   audit/spec-only avant V1 ou report post-V1 explicite, pas runtime par defaut.

## Matrice finale Lot 3 - GO / PARTIAL / NO-GO

### Legende

- `GO`: clos/prove dans son perimetre V1; ne bloque pas la cloture.
- `PARTIAL`: livrable avec limite documentee; ne bloque pas si la limite reste
  acceptee explicitement.
- `NO-GO`: bloque la declaration finale tant que le lot/decision n'est pas
  traite.
- `POST-V1`: hors cloture Frida 1.0.
- `GATED`: possible seulement apres lot dedie ou GO operateur explicite.

### Matrice des chantiers et gates

| Domaine | Statut | Preuve source | Limite acceptee | Decision restante | Lot |
| --- | --- | --- | --- | --- | --- |
| Nextcloud folders | GO | `todo-done/product/frida-v1-nextcloud-folders-todo.md`, JSONL `nextcloud-folder-smokes/` Lot Z | Socle dossiers seulement; frontiere Sauron/Nextcloud conservee | Aucune pour V1 | Clos |
| Documents ingestion | PARTIAL | `todo-done/product/frida-v1-documents-ingestion-todo.md`, JSONL `documents-smokes/` Lot Z | Refus live dossier non `linked` non applicable, couvert par tests unitaires/serveur | Aucune si limite acceptee | Clos |
| Notes Markdown | PARTIAL | `todo-done/product/frida-v1-folder-markdown-notes-todo.md`, JSONL `notes-smokes/` Lot Z | Conflit ETag/version live `not_applicable` / `covered_by_unit_tests` | Aucune si limite acceptee | Clos |
| Exports | GO | `todo-done/product/frida-v1-exports-todo.md`, JSONL `exports-smokes/` Lot Z | Reuse `.docx`/`.pdf` comme source texte reste post-V1 | Aucune pour V1 | Clos |
| Generated Images | PARTIAL | `todo-done/product/frida-v1-generated-images-todo.md`, JSONL `generated-images-smokes/` Lot Z | Live provider observe PNG; JPEG/WebP couverts par tests/fakes | Aucune si limite acceptee | Clos |
| Agentic Observability | GO | `todo-done/product/frida-v1-agentic-observability-todo.md`, JSONL `agentic-observability-smokes/` Lot Z | Reset destructif non execute; operation separee sous GO operateur | Reset reste `GATED` post-cloture | Clos / GATED reset |
| Continuity Payload | GO | `todo-done/product/frida-v1-continuity-payload-todo.md`, JSONL `continuity-payload-smokes/` Lot Z | Capsule runtime livree disabled; activation texte non prouvee | Activation ou report par Lot 5 | Clos / GATED capsule |
| Biblio | GO | `todo-done/product/frida-biblio-last-chance-archive-2026-06-06.md`, JSONL `biblio-smokes/` BIB-01 -> BIB-33 | Agent/refactors/ergonomie avancee restent post-V1 | Aucune pour V1 | Clos |
| Agenda pragmatique | PARTIAL | `states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`, JSONL `agenda-smokes/` | Agenda utile mais non exhaustif; Lot 9 et capacites riches post-V1 | Aucune sauf bug reel/besoin concret | Clos pragmatique |
| Admin logs Lot 1A/1B/1B.1 | GO | Tests admin/logs et TODO finale Lots 1A/1B | Pas de refonte dashboard large | Aucune pour V1 | Clos |
| Branche/main | GATED | Etat Git Lot 4: `origin_main_ancestor_of_HEAD=0`, `HEAD_ancestor_of_origin_main=1` | `HEAD` n'est pas contenu dans `origin/main`; Frida V1 n'est pas declaree close sur `main` | Non-integration temporaire; merge/PR/main seulement sur GO separe | Lot 4 clos / main gate |
| Continuity Capsule activation | GATED | Contrat/archives Continuity et tests existants | Substitut borne ne prouve que la mecanique runtime | Micro-preuve texte operateur ou report | Lot 5 |
| Mail bonus | GATED | Roadmap finale et TODO Mail bonus | Runtime Mail exclu de V1 par defaut | Audit/spec-only ou report explicite | Lot 6 |
| Final closure smoke | NO-GO | Cette matrice et inventaire JSONL Lot 3 | Pas de smoke live non necessaire en Lot 3 | Scans/tests bornes choisis | Lot 7 |
| Archive finale | NO-GO | TODO finale active | Tous P2/P3 doivent etre fermes, acceptes ou reportes | Archivage apres decisions | Lot Z |
| SMS | POST-V1 | Roadmap finale | Hors cloture Frida 1.0 | Aucune | Post-V1 |
| TTS | POST-V1 | Roadmap finale | Hors cloture Frida 1.0 | Aucune | Post-V1 |
| Mail runtime | POST-V1 | Roadmap finale et finding `P2-MAIL-RUNTIME-SCOPE-01` | Aucun IMAP/SMTP/Nextcloud Mail live sans GO separe | Report ou chantier futur | Post-V1 |
| Reset observabilite destructif | GATED | Contrat Observabilite agentique | Backup/rollback/GO operateur requis | Lot separe si demande | Post-cloture |
| Gros refactors runtime | POST-V1 | `wc -l` Lot 3 sur fichiers cibles | Vigilance seulement; pas de refactor opportuniste | Aucun avant finding cible | Post-V1 |

### Preuves et smokes apres Lot 3

- JSONL inventories par chemins: 118 fichiers candidats sous
  `app/docs/states/baselines`, 671 enregistrements parses, 0 erreur JSON.
- Les preuves live conservees restent suffisantes pour les chantiers `GO` et
  `PARTIAL`; les limites `covered_by_tests`, `covered_by_unit_tests` ou
  `not_applicable` sont visibles et non converties en faux `GO`.
- Aucun provider live, Nextcloud live, CalDAV live, Mail runtime, reset, purge,
  backfill ou migration n'est requis par Lot 3.
- Lot 7 devra rejouer seulement les scans bornes choisis par cette matrice:
  `git status`, `git diff --check`, inventaire JSONL, scan anti-fuite docs/proofs,
  absence pycache/temp, absence `utils.py` / `helpers.py`, et tests cibles
  uniquement si un lot runtime precedent le justifie.
- Smokes live interdits ou inutiles avant decision dediee: Capsule activee,
  Mail runtime, reset observabilite, Agenda/CalDAV, provider images, ecriture
  Nextcloud.

### Classification P3 Lot 3

- `P3-ARCHIVE-CHECKBOXES-01`: accepte comme historique/post-V1, avec une seule
  case ouverte V1 directe dans Documents (`non linked`) deja couverte par le
  verdict `met_with_documented_limit`; les autres cases relevent d'archives
  non V1 finales ou de roadmaps Biblio/Web/Adobe obsoletes.
- `P3-ARCHIVE-REFERENCES-STALE-01`: accepte comme historique; les anciens
  pointeurs trouves dans archives Documents/Exports/Images sont des chaines de
  handoff entre lots archives, pas des pointeurs actifs.
- `P3-CAPSULE-FINAL-LOCK-OBSERVABILITY-01`: classe `GATED` Lot 5; le statut
  actuel est non-injection sure sous final lock, mais l'ordre unsafe/final-lock
  reste a clarifier si l'objectif devient activation reelle.
- `P3-SCOPED-LOG-DELETE-GATE-01`: suppression scopee classee action admin
  bornee (`conversation_id` requis, `turn_id` optionnel), distincte du reset
  destructif global; tout reset large reste `GATED`.
- `P3-STATUS-FLATTENING-01`: classe P3 de vigilance; non bloquant pour V1 tant
  qu'aucune preuve ne montre un `failed/refused/not_configured/skipped` masque;
  Lot 7 peut ouvrir un micro-audit cible si la cloture zero-erreur l'exige.
- `P3-BIBLIO-AUDIT-CURRENT-STALE-01`: accepte comme historique/source
  d'architecture; l'archive Last Chance BIB-01 -> BIB-33 reste la preuve de
  cloture V1.
- `P3-PROOF-LIVE-COVERAGE-01`: ferme par cette matrice; les preuves live,
  fake/unit, `covered_by_tests`, `covered_by_unit_tests` et `not_applicable`
  sont distinguees explicitement.
- `P3-LARGE-FILES-01`: confirme post-V1; les gros fichiers mesures au Lot 3
  restent sous vigilance sans refactor opportuniste.

## Decisions de cloture restantes apres Lot 4

- Lot 4: decision branche/main prise; `P2-BRANCH-INTEGRATION-01` est clos par
  non-integration temporaire, sans merge ni push vers `main`.
- Lot 5: micro-preuve Capsule avec texte operateur approuve ou report post-V1;
  `P2-CAPSULE-ACTIVATION-PROOF-01` reste ouvert.
- Lot 6: Mail audit/spec-only ou report post-V1; `P2-MAIL-RUNTIME-SCOPE-01`
  reste ouvert tant que la decision n'est pas documentee.
- Lot 7: smoke final borne selon cette matrice, sans nouveaux smokes live
  inutiles.
- Lot Z: archivage final seulement apres P2 fermes/acceptes et P3
  corriges/acceptes/reportes.

## 3. Registre des findings

### P2-FINAL-AUDIT-MATRIX-01

- Statut initial: accepted; support de pilotage clos par Lot 0, matrice finale
  livree par Lot 3 le 2026-06-23.
- Severite: P2.
- Fichiers suspects: `app/docs/todo-todo/product/frida-v1-final-audit-todo.md`.
- Lot cible: Lot 0 pour fermer la dette "TODO squelettique", puis Lot 3 pour
  livrer la matrice finale executable.
- Critere de cloture: le support de pilotage est present depuis Lot 0; la
  composante "matrice finale GO / PARTIAL / NO-GO executable" couvre desormais
  les chantiers V1 clos, les limites `PARTIAL`, les gates `NO-GO/GATED`, les
  decisions `POST-V1` et les lots restants.
- Preuve minimale: matrice Lot 3, inventaire JSONL content-free, `git diff
  --check`, grep `GO|PARTIAL|NO-GO|POST-V1|GATED`.
- Hors-scope: corriger les autres P2 dans le meme patch.

### P2-ADMIN-LOGS-LEGACY-01

- Statut initial: accepted; clos par Lot 1A le 2026-06-23.
- Severite: P2.
- Fichiers suspects: `app/server.py`, `app/admin/admin_logs.py`,
  `app/observability/admin_log_projection.py`.
- Lot cible: Lot 1A.
- Critere de cloture: `/api/admin/logs` legacy reste disponible mais retourne
  les entrees sous projection content-free, avec `payload_projection_schema`,
  `redaction` agregee et champs dangereux retires/redacted.
- Preuve minimale: tests route admin avec sentinelles anti-fuite, compat `logs`,
  et projection `observability.admin_log_projection`.
- Hors-scope: refonte dashboard large, suppression non demandee de l'historique.

### P2-LOG-READ-FAIL-CLOSED-01

- Statut initial: accepted; clos par Lot 1B le 2026-06-23.
- Severite: P2.
- Fichiers suspects: `app/observability/log_store.py`, `app/server.py`,
  `app/admin/admin_logs.py`.
- Lot cible: Lot 1B.
- Critere de cloture: les routes admin `/api/admin/logs` et
  `/api/admin/logs/chat` optent pour `fail_closed=True`; une panne de lecture
  devient `ok=false`, HTTP 500 et reason code content-free au lieu d'un succes
  vide. Correctif Lot 1B.1: les read-models derives `turns` et `metrics`
  optent aussi pour un fail-closed reel cote helper quand la route admin le
  demande.
- Preuve minimale: tests fake de panne lecture legacy/chat, tests bas niveau
  `read_chat_log_events(fail_closed=True)`,
  `read_chat_turn_pipeline(fail_closed=True)` et
  `read_full_turn_metrics_snapshot(fail_closed=True)`, preuve route avec
  `conn_factory` cassee, absence de cause brute exposee.
- Hors-scope: exposer traceback, chemin, contenu ou exception brute.

### P2-DOCS-SOURCE-OF-TRUTH-01

- Statut initial: accepted; clos par Lots 2A, 2B, 2C et 2D le 2026-06-23.
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

- Statut initial: accepted; clos par Lot 2A le 2026-06-23.
- Severite: P2.
- Fichiers suspects: `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`.
- Lot cible: Lot 2A.
- Critere de cloture: les passages qui disaient Documents/Notes/Exports/Images
  futurs ont ete requalifies comme historiques ou alignes sur les specs dediees
  cloturees.
- Preuve minimale: grep `Documents|Notes|Exports|Images|futur|a livrer`, diff
  docs-only, verification des liens vers specs dediees dans la spec Folders.
- Hors-scope: modifier le contrat runtime de ces chantiers dedies.

### P2-AGENDA-DORMANT-STATUS-01

- Statut initial: accepted; clos par Lot 2B le 2026-06-23.
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

- Statut initial: accepted; clos par Lot 2C le 2026-06-23.
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

- Statut initial: accepted; clos par decision Lot 4 le 2026-06-23.
- Severite: P2.
- Fichiers suspects: etat Git, roadmap finale, rapport Lot Z final.
- Lot cible: Lot 4.
- Critere de cloture: decision explicite sur integration vers `main` ou
  non-integration temporaire; etat propre, commits pousses sur la branche de
  travail, relation avec `origin/main` documentee.
- Decision Lot 4: non-integration temporaire. Poursuite sur
  `FridaV1-Continuity-Payload-Audit` jusqu'a la fin des gates 5/6/7/Z; merge,
  PR, push vers `main` ou declaration close sur `main` reportes a un GO
  operateur separe.
- Etat Git Lot 4: branche courante `FridaV1-Continuity-Payload-Audit`;
  `HEAD=f7beb6df35b406ec8c1ce6ca706bd497fd27208a`;
  `origin/main=966adabea40da0513d789383c75531dac3a0b45f`;
  `origin_main_ancestor_of_HEAD=0`; `HEAD_ancestor_of_origin_main=1`;
  `origin/FridaV1-Continuity-Payload-Audit..HEAD` vide;
  `HEAD..origin/FridaV1-Continuity-Payload-Audit` vide.
- Preuve minimale: `git status --short --branch`, `git fetch origin main`,
  `git log --oneline -12`, `git log --oneline --branches --not origin/main`,
  `git merge-base --is-ancestor origin/main HEAD`, `git merge-base
  --is-ancestor HEAD origin/main`, `git branch --show-current`,
  `git rev-parse HEAD`, `git rev-parse origin/main`.
- Hors-scope: effectuer le merge dans cette TODO.

### P2-CAPSULE-ACTIVATION-PROOF-01

- Statut initial: open.
- Severite: P2.
- Fichiers suspects: `app/core/continuity_capsule.py`,
  `app/core/chat_service.py`, contrat et archive Continuity Payload.
- Lot cible: Lot 5.
- Critere de cloture: soit micro-preuve complete avec texte operateur approuve,
  soit report explicite de l'activation post-V1.
- Preuve minimale: disabled -> enabled normal avec texte operateur approuve si
  l'objectif est l'activation reelle -> unsafe refused -> final-lock bypass ->
  rollback disabled, sans contenu de capsule brut dans logs/proofs. Un substitut
  strictement borne peut prouver la mecanique runtime, mais ne ferme pas ce P2
  comme preuve d'activation reelle.
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

- Statut initial: accepted; clos par Lot 2D le 2026-06-23.
- Severite: P3.
- Fichiers suspects: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`.
- Lot cible: Lot 2D.
- Critere de cloture: la branche historique affichee a ete remplacee
  par une formulation non volatile.
- Preuve minimale: grep `Branche de cloture courante` et absence de l'ancienne
  branche Nextcloud/Folders dans les surfaces actives.
- Hors-scope: decision merge/main.

### P3-README-DATE-STALE-01

- Statut initial: accepted; clos par Lot 2D le 2026-06-23.
- Severite: P3.
- Fichiers suspects: `README.md`.
- Lot cible: Lot 2D.
- Critere de cloture: l'en-tete d'etat ne contredit plus les livraisons
  documentees jusqu'au 2026-06-23.
- Preuve minimale: grep date README, diff docs-only.
- Hors-scope: reecrire toute la presentation runtime.

### P3-FINAL-AUDIT-POINTERS-01

- Statut initial: accepted; clos par Lot 2D le 2026-06-23.
- Severite: P3.
- Fichiers suspects: `README.md`, `app/docs/README.md`, `AGENTS.md`.
- Lot cible: Lot 2D.
- Critere de cloture: les surfaces actives utiles pointent vers
  `app/docs/todo-todo/product/frida-v1-final-audit-todo.md` comme pilote actif
  de cloture finale, sans doublonner l'historique.
- Preuve minimale: grep `frida-v1-final-audit-todo.md` dans README, hub docs,
  roadmap et AGENTS.
- Hors-scope: transformer les index en journal de bord ou clore la matrice.

### P3-ARCHIVE-CHECKBOXES-01

- Statut initial: accepted; caracterise par Lot 3 le 2026-06-23.
- Severite: P3.
- Fichiers suspects: `app/docs/todo-done/product/*`.
- Lot cible: Lot 3.
- Critere de cloture: les checkboxes ouvertes historiques sont classees comme
  archives/post-V1/non pertinentes pour V1, sauf preuve contraire; la seule
  case ouverte V1 directe Documents `non linked` reste couverte par
  `met_with_documented_limit`.
- Preuve minimale: `grep -RIn "\\[ \\]" app/docs/todo-done/product`, comptage
  par fichier et matrice Lot 3.
- Hors-scope: cocher artificiellement des limites volontairement documentees.

### P3-CAPSULE-FINAL-LOCK-OBSERVABILITY-01

- Statut initial: accepted; classe GATED Lot 5 par Lot 3 le 2026-06-23.
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

- Statut initial: post-V1 confirme par Lot 3 le 2026-06-23 sauf si un lot cible
  touche le fichier.
- Severite: P3.
- Fichiers suspects: `app/server.py`, `app/core/chat_service.py`,
  `app/observability/dashboard_read_model.py`, `app/biblio/librarian_tools.py`.
- Lot cible: aucun lot de correction final par defaut; vigilance sur tous les
  lots runtime.
- Critere de cloture: pas de rallonge opportuniste; si un patch touche un gros
  fichier, verifier la responsabilite et envisager extraction bornee.
- Preuve minimale: `wc -l` cible avant gros patch.
- Hors-scope: refactor structurel opportuniste avant cloture V1.

### Findings supplementaires du contre-audit

#### P3-ARCHIVE-REFERENCES-STALE-01

- Statut initial: accepted; classe historique par Lot 3 le 2026-06-23.
- Severite: P3.
- Fichiers suspects:
  `app/docs/todo-done/product/frida-v1-documents-ingestion-todo.md`,
  `app/docs/todo-done/product/frida-v1-exports-todo.md`,
  `app/docs/todo-done/product/frida-v1-generated-images-todo.md`.
- Lot cible: Lot 3.
- Critere de cloture: les references vers anciens chemins actifs sont declarees
  non bloquantes dans la matrice car elles apparaissent dans des archives comme
  handoffs historiques, pas dans des pointeurs actifs de pilotage.
- Preuve minimale: grep des anciens chemins `todo-todo` dans les archives V1 et
  matrice Lot 3.
- Hors-scope: reecrire les preuves historiques ou deplacer des archives sans
  convention explicite.

#### P3-SCOPED-LOG-DELETE-GATE-01

- Statut initial: accepted; cadre par Lot 3 le 2026-06-23.
- Severite: P3.
- Fichiers suspects: `app/server.py`, `app/observability/log_store.py`,
  `app/docs/states/specs/frida-v1-agentic-observability-contract.md`.
- Lot cible: Lot 3 pour decision de cadrage.
- Critere de cloture: la suppression logs scopee est classee action admin
  bornee distincte du reset global, car elle refuse la suppression tous logs et
  exige `conversation_id`; tout reset large reste `GATED`.
- Preuve minimale: lecture des routes/scope delete, grep `reset` / `delete` /
  `operator_go`, decision inscrite dans la matrice finale.
- Hors-scope: executer reset, purge, backfill, suppression logs ou migration.

#### P3-STATUS-FLATTENING-01

- Statut initial: post-V1 / vigilance; classe par Lot 3 le 2026-06-23.
- Severite: P3.
- Fichiers suspects: `app/core/chat_service.py`.
- Lot cible: Lot 7 ou micro-audit cible si la cloture zero-erreur l'exige.
- Critere de cloture: les emitters concernes sont confirmes comme ne masquant
  pas `failed`, `refused`, `not_configured` ou `skipped`, ou un finding runtime
  borne est ouvert.
- Preuve minimale: grep des emitters Adobe/Notes, tests ou lecture ciblee des
  payloads possibles, sans provider live inutile.
- Hors-scope: refactor global de `chat_service.py` ou remplacement mecanique de
  tous les statuts.

#### P3-BIBLIO-AUDIT-CURRENT-STALE-01

- Statut initial: accepted; classe historique par Lot 3 le 2026-06-23.
- Severite: P3.
- Fichiers suspects:
  `app/docs/states/audits/frida-biblio-librarian-agent-architecture-audit-2026-05-31.md`,
  archives Biblio Lot 33/33 sous `app/docs/todo-done/product/`.
- Lot cible: Lot 3.
- Critere de cloture: l'audit Biblio ancien est classe comme source
  d'architecture/historique non bloquante; l'archive Last Chance BIB-01 ->
  BIB-33 reste la preuve de cloture V1.
- Preuve minimale: grep des pointeurs Biblio dans README/app docs/roadmap et
  verification du lien vers l'archive de cloture Biblio.
- Hors-scope: rouvrir Biblio runtime ou reecrire l'audit historique.

#### P3-PROOF-LIVE-COVERAGE-01

- Statut initial: accepted; clos par matrice Lot 3 le 2026-06-23.
- Severite: P3.
- Fichiers suspects: artefacts sous `app/docs/states/baselines/`, archives V1
  Documents/Notes/Images/Observabilite, audits final et contre-audit.
- Lot cible: Lot 3.
- Critere de cloture: la matrice finale distingue preuves live, fakes/unitaires,
  `covered_by_tests`, `not_applicable` et reports volontaires sans demander de
  reexecution live inutile.
- Preuve minimale: inventaire JSONL content-free, lecture des statuts de preuve
  et annotation dans la matrice GO / PARTIAL / NO-GO.
- Hors-scope: forcer des smokes live non necessaires, provider live, ecriture
  Nextcloud ou mutation DB pour combler une limite deja documentee.

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

- [x] Relire `/api/admin/logs`, `/api/admin/logs/chat` et projections associees.
- [x] Decider: deprecation explicite de legacy ou projection/redaction stricte.
- [x] Remplacer les sorties `error=str(exc)` du scope touche par reason code /
  `error_class` content-free.
- [x] Preserver compat UI uniquement si elle reste explicite et testee.
- [x] Ne pas toucher au dashboard large.

Resultat Lot 1A:

- `/api/admin/logs` conserve la cle `logs`, mais les items legacy passent par
  `observability.admin_log_projection.project_legacy_admin_log_entries`.
- Les champs historiques dangereux (`message`, `error`, `raw`, `payload`,
  provider/DAV/token/path-like) sont retires ou redacted; seuls des codes et
  compteurs content-free peuvent rester.
- La route retourne `count`, `redaction` et `payload_projection_schema` pour
  rendre la projection observable.
- Le dashboard large n'a pas ete modifie.

Commandes/preuves minimales:

- grep scope `admin_logs|/api/admin/logs|str(exc)|error=str(exc)`.
- tests unitaires/serveur cibles admin logs.
- scan anti-fuite sur champs `raw`, `payload`, `error`, `message_short`.

Rebuild: oui si runtime deploye.
Artefact JSONL: seulement si le lot produit une preuve content-free utile.

### Lot 1B - Log read fail-closed

Type: runtime cible.

- [x] Construire un test fake de panne lecture logs chat.
- [x] Construire un test fake de panne lecture logs legacy si legacy conservee.
- [x] Faire retourner `ok=false` ou 5xx avec reason code content-free.
- [x] Verifier que la cause brute n'est jamais exposee.

Resultat Lot 1B:

- `admin_logs.read_logs(..., fail_closed=True)` remonte
  `RuntimeError('admin_logs_read_failed')` apres log technique `err_class`
  content-free.
- `log_store.read_chat_log_events(..., fail_closed=True)` remonte
  `RuntimeError('chat_log_events_read_failed')` apres log technique `err_class`
  content-free.
- Correctif Lot 1B.1: `log_store.read_chat_turn_pipeline(...,
  fail_closed=True)` et `log_store.read_full_turn_metrics_snapshot(...,
  fail_closed=True)` remontent respectivement
  `RuntimeError('chat_log_turns_read_failed')` et
  `RuntimeError('chat_log_metrics_read_failed')`; sans `fail_closed=True`, le
  mode degrade historique `source.read_error=true` reste explicite pour les
  callers non-admin.
- Les routes admin logs de lecture principale, metadata, turns, metrics, delete
  scope et export Markdown traduisent les erreurs runtime en HTTP 500
  `ok=false` avec reason code stable, sans traceback ni message d'exception
  brut.

Commandes/preuves minimales:

- tests serveur cibles.
- grep `return []` et `ok: true` sur lecteurs/routes logs.
- scan anti-fuite sur exception brute.

Rebuild: oui si runtime deploye.
Artefact JSONL: non par defaut.

### Lot 2A - Docs source-of-truth Nextcloud/Folders

Type: docs-only sauf decouverte contraire.

- [x] Requalifier les formulations stale sur Documents/Notes/Exports/Images.
- [x] Distinguer socle folders historique des lots dedies clos.
- [x] Pointer vers les specs dediees cloturees.
- [x] Ne pas modifier les preuves historiques.

Resultat Lot 2A:

- `frida-v1-nextcloud-folders-contract.md` reste source-of-truth du socle
  `workspace_folders`, du mapping `/Frida/<dossier>` et des sous-dossiers
  standards.
- Documents, Notes, Exports et Images sont renvoyes vers leurs contrats dedies
  clotures.
- Les formulations "futur" restantes dans la spec Folders sont historiques,
  generiques ou post-V1 bornees; elles ne rouvrent pas ces chantiers V1.
- Aucune archive historique, preuve JSONL ou surface runtime n'a ete modifiee.

Commandes/preuves minimales:

- `rg -n "Documents|Notes|Exports|Images|futur|a livrer" app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
- `git diff --check`
- grep des liens vers specs dediees.

Rebuild: non.
Artefact JSONL: non.

### Lot 2B - Agenda dormant/actif

Type: docs-only.

- [x] Trancher le statut de `frida-agenda-agent.md`: post-V1 dormant ou archive.
- [x] Indiquer que les cases ouvertes sont des reprises post-V1, pas des no-go.
- [x] Conserver la cloture pragmatique comme source V1.
- [x] Ne pas lire CalDAV, ne pas relancer de smoke live.

Resultat Lot 2B:

- `frida-agenda-agent.md` declare Agenda V1 pragmatiquement clos et maintient la
  TODO en `todo-todo` comme post-V1 dormant.
- Les lots ouverts Agenda, Lot 9, disponibilites riches, invitations, rappels,
  recurrences riches et mutations utilisateur reelles sont hors cloture Frida
  1.0.
- La reouverture exige bug reel, besoin utilisateur concret ou GO operateur /
  decision produit dediee.
- Les pointeurs actifs `AGENTS.md`, `README.md`, `app/docs/README.md` et roadmap
  finale etaient deja coherents avec ce statut; aucune modification requise.
- Aucun runtime Agenda, CalDAV, smoke live, secret ou pending store n'a ete
  touche.

Commandes/preuves minimales:

- grep `Statut|Lot 9|cloture pragmatique|post-V1`.
- `git diff --check`.
- coherence README/app docs/roadmap.

Rebuild: non.
Artefact JSONL: non.

### Lot 2C - Continuity audits / archives

Type: docs-only.

- [x] Requalifier les deux audits Continuity en sources historiques supersedees
  par l'archive Lot Z, ou les deplacer si la convention repo le permet.
- [x] Garder les findings historiques intacts.
- [x] Eviter toute confusion avec des findings Continuity vivants.

Resultat Lot 2C:

- Les deux audits Continuity gardent leur emplacement historique dans
  `todo-todo/audits`, mais leur en-tete indique qu'ils sont superseded par la
  cloture Lot Z Continuity Payload.
- Les en-tetes pointent vers l'archive
  `app/docs/todo-done/product/frida-v1-continuity-payload-todo.md`, l'artefact
  Lot Z et le contrat courant.
- Les findings P1/P2/P3 historiques n'ont pas ete reecrits ou supprimes.
- Ces audits ne constituent plus un registre actif sauf reouverture explicite
  par une TODO active.
- Aucun runtime, provider, DB, reset, purge ou backfill n'a ete touche.

Commandes/preuves minimales:

- grep des P1/P2/P3 Continuity dans `todo-todo/audits`.
- grep des pointeurs vers `frida-v1-continuity-payload-todo.md`.
- `git diff --check`.

Rebuild: non.
Artefact JSONL: non.

### Lot 2D - Roadmap / README / index

Type: docs-only.

- [x] Corriger ou neutraliser la branche historique dans la roadmap finale.
- [x] Corriger la date stale README si elle reste contradictoire.
- [x] Ajouter le pointeur vers cette TODO finale si un index actif en manque.
- [x] Nettoyer uniquement les references stale qui troublent la cloture finale.

Resultat Lot 2D:

- La roadmap finale ne porte plus la branche historique Nextcloud/Folders; elle
  renvoie a la TODO finale active et a l'etat Git courant, sans trancher le gate
  `main`.
- Le README racine annonce maintenant l'etat courant au 2026-06-23; les dates
  historiques legitimes restent intactes.
- `README.md`, `app/docs/README.md` et `AGENTS.md` pointent vers
  `app/docs/todo-todo/product/frida-v1-final-audit-todo.md` comme pilote actif
  de cloture finale.
- `P2-BRANCH-INTEGRATION-01` etait laisse au Lot 4; il est maintenant clos par
  decision de non-integration temporaire. Aucun merge, changement de branche ou
  push vers `main` n'a ete effectue.
- Aucun runtime, DB, reset, provider, Docker ou artefact historique n'a ete
  modifie.

Commandes/preuves minimales:

- grep `frida-v1-final.*todo|final-closure|final audit`.
- grep dates/branche.
- `git diff --check`.

Rebuild: non.
Artefact JSONL: non.

### Lot 3 - Final audit matrix

Type: docs-only / preuve-only.

- [x] Construire une matrice GO / PARTIAL / NO-GO.
- [x] Lister tous les lots V1 clos et leurs preuves JSONL.
- [x] Lister les tests minimaux a rejouer et ceux a ne pas rejouer.
- [x] Distinguer smokes live requis, optionnels, inutiles ou interdits.
- [x] Marquer reset observabilite: non execute sauf GO operateur separe.
- [x] Marquer capsule: gate Lot 5 activation/report, non activee par Lot 3.
- [x] Marquer Mail: gate Lot 6 audit/spec-only ou report, runtime post-V1.
- [x] Marquer branche/main: gate Lot 4, decision prise ensuite par Lot 4.
- [x] Classer P3: corriges, acceptes ou post-V1.

Resultat Lot 3:

- Matrice GO / PARTIAL / NO-GO / POST-V1 / GATED ajoutee dans cette TODO.
- Les chantiers V1 clos sont classes sans faux GO: Documents, Notes, Generated
  Images et Agenda pragmatique restent visibles comme `PARTIAL` a limite
  acceptee; Observabilite et Continuity ont leurs gates reset/capsule separes.
- Au Lot 3, les gates branche/main, Capsule, Mail, smoke final et archive
  finale restaient `NO-GO` ou `GATED`; depuis Lot 4, branche/main est decidee
  en non-integration temporaire, et les gates Capsule, Mail, smoke final et
  archive finale restent ouverts tant que les Lots 5/6/7/Z ne sont pas traites.
- Les preuves JSONL ont ete inventoriees et parsees content-free: 118 fichiers,
  671 enregistrements, 0 erreur.
- Les checkboxes ouvertes historiques ont ete caracterisees sans correction
  artificielle: 7 fichiers `todo-done/product`, 149 cases ouvertes, dont une
  seule V1 finale directe deja couverte par `met_with_documented_limit`.
- Aucun runtime, provider, DB, reset, purge, migration, Docker, Mail runtime,
  activation Capsule, CalDAV ou ecriture Nextcloud n'a ete touche.

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

- [x] Verifier branche courante propre.
- [x] Verifier absence de commits locaux non pousses.
- [x] Verifier relation avec `origin/main`.
- [x] Decider: merge vers `main`, PR, ou non-integration temporaire documentee.
- [x] Constater qu'aucun merge n'est demande dans ce lot; verification apres
  merge/push reportee a un GO operateur separe si merge futur.

Resultat Lot 4:

- Branche courante: `FridaV1-Continuity-Payload-Audit`.
- `HEAD=f7beb6df35b406ec8c1ce6ca706bd497fd27208a`.
- `origin/main=966adabea40da0513d789383c75531dac3a0b45f`.
- `origin/main` est ancetre de `HEAD`: code `0`.
- `HEAD` est ancetre de `origin/main`: code `1`.
- Aucun commit local non pousse n'est observe face a
  `origin/FridaV1-Continuity-Payload-Audit`.
- Decision: non-integration temporaire; continuer sur la branche courante
  jusqu'a la fin des gates 5/6/7/Z. Aucun merge, PR, rebase, push vers `main`
  ou tag release n'a ete effectue.

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
- [ ] Prouver enabled normal sur texte operateur approuve si l'objectif est une
  activation reelle.
- [ ] Si un substitut strictement borne est utilise, le classer seulement comme
  preuve de mecanique runtime; il ne ferme pas
  `P2-CAPSULE-ACTIVATION-PROOF-01` comme preuve d'activation reelle.
- [ ] Fermer `P2-CAPSULE-ACTIVATION-PROOF-01` uniquement par vraie micro-preuve
  avec texte operateur approuve, ou par report post-V1 explicite.
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
- Declaration de Frida V1 close sur `main` alors que `HEAD` n'est pas contenu
  dans `origin/main`, sauf GO operateur separe de merge/PR/main et verification
  post-integration.
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
- Les findings supplementaires du contre-audit sont documentes au format
  registre.
- Seuls les lots effectivement livres sont coches: Lot 0, Lot 1A, Lot 1B,
  Lot 2A, Lot 2B, Lot 2C, Lot 2D, Lot 3 et Lot 4.
- Les lots 5, 6, 7 et Z restent non coches tant que leurs gates ne sont pas
  traites.
- Aucun lot futur ou gate final n'est coche prematurement.
- Les correctifs runtime deja livres en Lots 1A/1B ne sont pas nies par cette
  section; aucun nouveau runtime n'est implique par l'auto-audit.
- Aucun reset/purge/backfill/migration n'est demande implicitement.
- L'activation capsule exige un GO operateur dedie.
- Mail runtime est exclu sauf GO ulterieur separe.
- Les docs/index/roadmap ne doivent pas pointer vers un mauvais fichier actif.
- Le contenu reste content-free.
