# Frida V1 - Audit final global - 2026-06-23

Statut: audit source historique. Superseded par l'archive finale Lot Z:
`app/docs/todo-done/product/frida-v1-final-audit-todo.md`. Les findings
ci-dessous documentent l'etat observe avant les Lots 0-Z et ne constituent plus
un registre actif sauf reouverture explicite.

## Verdict court

- Cloture V1 possible : conditionnelle.
- Continuity Capsule : activer apres micro-preuve, pas maintenant en aveugle.
- Agenda : V1 clos pragmatiquement, TODO encore dormante en `todo-todo`.
- Mail bonus : prendre seulement audit/spec Mail, reporter le runtime post-V1.
- Risque global : moyen.

Le depot est coherent dans ses grands contrats V1 recents: dossiers Nextcloud,
Documents, Notes, Exports, Images generees, Observabilite agentique et
Continuity Payload ont des specs source-of-truth, archives de livraison et
artefacts content-free retrouvables. Les blocages avant cloture finale ne sont
pas des chantiers produit manquants massifs; ce sont surtout des gates
d'integration, de statut documentaire et de preuves finales.

No-go principal: ne pas declarer Frida V1 close tant que le contre-audit
independant n'a pas ete compare, que les P2 ci-dessous n'ont pas ete acceptes
ou corriges, et que la cible Git de cloture a ete clarifiee.

## Carte globale des chantiers

| Chantier | TODO | Spec source-of-truth | Dernier statut connu | Preuve principale | Risque restant |
| --- | --- | --- | --- | --- | --- |
| Nextcloud folders | archivee `todo-done/product/frida-v1-nextcloud-folders-todo.md` | `states/specs/frida-v1-nextcloud-folders-contract.md` | Lot Z `met`, 2026-06-17 | JSONL Lot Z dossiers, sous-dossiers standards et reconciliation | P3: contrat ancien tres long; ne pas rouvrir pour fichiers, mail ou Agenda |
| Documents ingestion | archivee `todo-done/product/frida-v1-documents-ingestion-todo.md` | `states/specs/frida-v1-documents-ingestion-contract.md` | Lot Z `met_with_documented_limit`, 2026-06-18 | JSONL Lot Z Documents | P3: refus live dossier non `linked` non applicable, couvert par tests; checkbox historique ouverte peut troubler |
| Notes Markdown | archivee `todo-done/product/frida-v1-folder-markdown-notes-todo.md` | `states/specs/frida-v1-folder-markdown-notes-contract.md` | Lot Z `met_with_documented_limit`, 2026-06-18 | JSONL Lot Z Notes | P3: conflit ETag live non prouve, couvert par fake/unit et documente |
| Exports | archivee `todo-done/product/frida-v1-exports-todo.md` | `states/specs/frida-v1-exports-contract.md` | Lot Z `met`, 2026-06-19 | JSONL Lot Z Exports | P3: reuse `.docx`/`.pdf` comme source texte reste post-V1 |
| Images generees | archivee `todo-done/product/frida-v1-generated-images-todo.md` | `states/specs/frida-v1-generated-images-contract.md` | Lot Z `met`, 2026-06-20 | JSONL Lot Z Images | P3: live observe PNG seulement; JPEG/WebP par tests/fakes |
| Observabilite agentique | archivee `todo-done/product/frida-v1-agentic-observability-todo.md` | `states/specs/frida-v1-agentic-observability-contract.md` | Lot Z `met`, 2026-06-22 | JSONL Lot Z Observabilite, tests conteneur, scans bornes | P2: residus `str(exc)`/`err=%s` hors observabilite V1 a cadrer avant cloture globale |
| Continuity Payload | archivee `todo-done/product/frida-v1-continuity-payload-todo.md` | `states/specs/frida-v1-continuity-payload-contract.md` | Lot Z `met`, 2026-06-23 | JSONL Lot Z Continuity, tests capsule/manifeste/garde | P2: activation operateur exige micro-preuve; role provider `system` reste non souverain contractuellement, pas mecaniquement |
| Agenda | TODO active/dormante `todo-todo/product/frida-agenda-agent.md` | `states/specs/frida-agenda-agent-contract.md` | cloture pragmatique V1, 2026-06-09 | audit cloture pragmatique et smokes cibles | P3: statut documentaire ambigu; TODO reste en `todo-todo` pour dettes post-V1 |
| Biblio | archives BIB et agent bibliothecaire | `states/specs/frida-biblio-native-catalogue-contract.md`, `states/specs/frida-biblio-librarian-agent-contract.md` | BIB-01 a BIB-33 fermes live; agent-first borne documente | artefacts Biblio JSONL et archive Last Chance | P3: modules gros, dependance OpenRouter/JSON, navigation canonique post-V1 |
| Mail bonus | TODO active bonus `todo-todo/product/frida-v1-mail-bonus-todo.md` | aucune spec dediee encore | bonus non bloquant | TODO courte Mail | P2 si runtime pris maintenant; spec/audit seulement raisonnable |
| Audit final general | archive `todo-done/product/frida-v1-final-audit-todo.md` | le present audit, superseded par Lot Z | clos Lot Z | artefact final audit Lot Z | integration `main` reste hors archive, sous GO separe |

Chantiers post-V1 ou bonus: Mail runtime, SMS, TTS, reset observabilite,
disponibilites Agenda riches, mutations Agenda utilisateur reelles, lookup
Exports par titre, reuse `.docx`/`.pdf` comme source, raffinement capsule,
nettoyage des gros modules Biblio/observabilite.

Chantiers ambigus ou mal ranges: Agenda est volontairement dormant dans
`todo-todo`; quelques archives conservent des cases ouvertes historiques; des
references anciennes pointent encore vers
`todo-todo/product/frida-v1-agentic-observability-todo.md`.

## Findings

### P1

Aucun P1 produit/runtime confirme dans l'etat lu. P1 process avant cloture:
le present audit doit etre compare au contre-audit independant et la decision
de cloture doit etre prise apres resolution explicite des P2.

### P2

- P2-GIT-01 - La branche courante `FridaV1-Continuity-Payload-Audit` contient
  des commits Continuity non presents dans `origin/main` au moment de l'audit.
  Si la cloture V1 cible `main`, il faut merger/pousser la cible finale avant
  de dire que V1 est close sur la branche de reference.
- P2-CAPSULE-01 - La Continuity Capsule est livree et desactivee, mais son
  activation reelle ne doit pas etre faite sans micro-preuve operateur:
  statut runtime, texte exact approuve, scan content-free du manifeste, rollback
  prouve et verification qu'aucun final lock n'est perturbe.
- P2-LOGS-01 - Les Lots Observabilite ont volontairement laisse des
  occurrences `err=%s`, `str(exc)` et retours JSON `error=str(exc)` hors
  `app/observability`, notamment dans `app/server.py`, `app/core` et
  `app/admin`. Ce n'est pas un regressif Observabilite V1, mais c'est un risque
  final global si une exception transporte un chemin, une URL, un contenu ou un
  detail sensible.
- P2-MAIL-01 - Prendre Mail runtime avant le 3 juillet exigerait protocoles,
  secrets, confirmations humaines, smokes et surfaces UI. Le scope actuel ne
  suffit pas pour un runtime bonus prudent.

### P3

- P3-DOC-01 - Des references stale vers
  `todo-todo/product/frida-v1-agentic-observability-todo.md` restent dans des
  docs historiques ou archives.
- P3-DOC-02 - Plusieurs TODO archivees conservent des checkboxes ouvertes
  historiques. La plupart sont marquees obsolete/sans objet; Documents conserve
  une ligne non `linked` ouverte mais supersedee par Lot Z
  `met_with_documented_limit`.
- P3-AGENDA-01 - Agenda est utile et pragmatiquement clos, mais son fichier
  reste formellement `Statut: TODO actif`. Les index le qualifient dormant;
  un micro-lot docs-only pourrait le renommer/deplacer sans rouvrir runtime.
- P3-SIZE-01 - Plusieurs fichiers runtime depassent largement la zone
  500-600 lignes: `app/server.py`, `app/core/chat_service.py`,
  `app/observability/dashboard_read_model.py`, `app/biblio/librarian_tools.py`
  et plusieurs modules Biblio/observabilite. Ne pas empiler de nouvelles
  capacites sans separation par responsabilite.
- P3-PROOF-01 - Certaines preuves sont `covered_by_tests` ou fake/unit plutot
  que live: Documents non `linked`, Notes conflit ETag, Images JPEG/WebP.
  Elles sont documentees et non bloquantes, mais doivent rester visibles.

## Continuity Capsule - analyse d'activation

La Continuity Capsule n'est plus seulement un prealable documentaire: c'est une
surface runtime utilisable, livree par `app/core/continuity_capsule.py` et
branchee tardivement dans `app/core/chat_service.py`, apres les lanes tardives
et apres le choix d'un final response lock Agenda/Biblio.

Elle n'est pas activee par defaut. Le probe runtime content-free du conteneur a
confirme: `enabled=false`, `status=disabled`,
`reason_code=continuity_capsule_disabled`, `content_chars=0`,
`max_chars=900`, `injected_count=0`.

Activation possible sans migration DB:

- config module: `CONTINUITY_CAPSULE_ENABLED`,
  `CONTINUITY_CAPSULE_TEXT`, `CONTINUITY_CAPSULE_VERSION`,
  `CONTINUITY_CAPSULE_MAX_CHARS`;
- fallback env: `FRIDA_CONTINUITY_CAPSULE_ENABLED`,
  `FRIDA_CONTINUITY_CAPSULE_TEXT`, `FRIDA_CONTINUITY_CAPSULE_VERSION`,
  `FRIDA_CONTINUITY_CAPSULE_MAX_CHARS`;
- rollback instantane: repasser enabled a false ou retirer le texte; aucune
  migration, purge, backfill ou DB n'est requise.

Ce qu'il faut ecrire dedans: une surface courte de conduite, non factuelle et
contestable. Exemples de categories autorisees: posture dialogique, densite
d'explication, proactivite bornee, prudence en refus/incertitude, rituels
content-free/audit/no-go, reprise apres interruption. Ne pas y mettre de fait
utilisateur, secret, URL, chemin, token, contenu documentaire, note, passage
Biblio, payload provider, instruction cachee souveraine ou doctrine identitaire.

Contenus refuses avant provider: texte absent, texte trop long, URL ou `www.`,
credential/token-like avec `=` ou `:`, bearer/authorization/cookie, data
URL/base64 evident, XML/DAV/CALDAV/WebDAV, chemin prive/absolu, bloc de cle
privee, structure multiligne suspecte. Le refus expose seulement
`continuity_capsule_unsafe_content` ou un reason code borne.

Observabilite: la capsule apparait dans `main_payload_manifest_v1` et dans
`lane_statuses.continuity_capsule` avec presence, enabled, version, status,
reason code, tailles, compteurs et flags raw/fingerprint a false. Le contenu de
capsule et son hash stable ne sont pas exposes.

Non-souverainete: elle est contractuelle et testee, mais pas mecanique. Le
message injecte utilise le role provider `system`, donc un modele peut le
ponderer fortement. Les garde-fous reels sont: disabled par defaut, texte
court, clause de priorite interne, final lock bypass, aucun write identity /
memory / summary, role logique distinct `continuity_capsule`, manifeste
content-free, garde writer-side et rollback.

Preuves existantes:

- tests runtime capsule: disabled, valide, missing, too large, unsafe, final
  lock bypass, config sans DB;
- tests manifeste/projection/garde writer-side;
- test chat_service avec capsule activee sans fuite;
- artefact Lot Z Continuity: 14 lignes content-free.

Preuves manquantes avant activation operateur:

- texte exact de capsule approuve par l'operateur, relu comme non factuel et
  non secret;
- micro-probe runtime avec enabled true sur texte court approuve, sans appel
  provider live si le probe peut rester fake/local;
- verification `main_payload_manifest_v1` post-activation: statut `ok`,
  `injected_count=1`, flags raw/fingerprint false;
- verification rollback: repasser disabled et obtenir zero injection;
- verification final lock: Agenda/Biblio bypass garde zero injection.

Recommandation: ACTIVER APRES MICRO-PREUVE.

Ne pas activer maintenant, non parce que le code serait immature, mais parce
que l'activation est une decision de produit et de texte. La capsule est assez
safeguardee pour une activation bornee apres preuve; elle n'est pas assez
neutre pour etre activee sans texte approuve ni rollback observe.

## Agenda - état réel et reste à faire

Agenda V1 est clos pragmatiquement par
`states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`. La TODO
`todo-todo/product/frida-agenda-agent.md` reste presente comme roadmap dormante
post-V1, avec dettes et familles non promises.

Agenda fonctionnel utile:

- lire aujourd'hui, demain, date explicite et sous-fenetres simples;
- chercher dans une fenetre lue;
- trouver le prochain evenement correspondant a un terme;
- rendre evenements journee entiere et multi-jours;
- proposer creation/modification/deplacement/suppression sans action autonome;
- confirmation humaine fake/local et creation synthetique live rollbackee;
- observabilite content-free et garde calendrier familial fail-closed.

Agenda V1 clos pragmatiquement:

- cloture volontairement non exhaustive;
- pas de test des 25 familles sans bug reel ou besoin concret;
- Lot 9 garde ferme;
- reouverture seulement par micro-lot cible.

Agenda post-V1:

- disponibilites riches;
- comparaisons;
- rappels/alarmes;
- participants/invitations;
- recurrences riches;
- mutations utilisateur reelles;
- pending store robuste apres restart;
- selection vernaculaire avancee de calendrier.

Ambiguite documentaire: le fichier porte encore `Statut: TODO actif`, alors que
les index principaux le qualifient dormant. Pour dire "Agenda fini" au sens
V1, il manque surtout une decision documentaire: soit conserver explicitement
le fichier en dormant post-V1, soit l'archiver/renommer via micro-lot docs-only.
Un probe runtime de statut live `agenda_agent` peut etre utile, mais il ne doit
pas rouvrir CalDAV ni exposer d'evenement.

Risques si laisse dormant: confusion operateur, faux sentiment de chantier
actif, tentation de rouvrir un Lot 9 abstrait. Risque runtime faible si les
garde-fous actuels restent inchanges.

Lots minimaux restants:

1. Micro-lot docs-only de statut Agenda: renommer "TODO actif" en
   "post-V1 dormant" ou archiver avec references.
2. Optionnel: probe runtime content-free de configuration Agenda, sans lecture
   evenement.
3. Aucun lot produit Agenda avant bug reel ou demande concrete.

## Mail bonus - état réel et recommandation

La TODO Mail existe:
`app/docs/todo-todo/product/frida-v1-mail-bonus-todo.md`. Elle est courte,
marquee bonus non bloquant et sans spec source-of-truth dediee.

Ce n'est pas bloquant pour V1. Scope minimal realiste avant le 3 juillet:
audit/spec Mail seulement, pas runtime. Un runtime Mail demanderait au minimum:

- choix protocole Nextcloud Mail / IMAP / SMTP / API controlee;
- modele de secrets et redaction;
- lecture no-op puis fake;
- aucun envoi sans confirmation humaine explicite;
- brouillons separes de l'envoi;
- observabilite content-free;
- tests d'absence de secret/log brut;
- frontiere avec dossiers Frida si rattachement est pris.

Invariants:

- aucun envoi autonome;
- aucune preuve avec corps de mail brut;
- pas de secret, token, app-password, header, IMAP/SMTP URL ou payload brut
  dans logs/docs/JSONL;
- confirmation humaine juste avant envoi;
- brouillon et envoi distingues;
- Mail ne bloque pas Frida 1.0.

Recommandation: PRENDRE SEULEMENT AUDIT/SPEC MAIL.

Reporter le runtime post-V1 sauf si les P2 final-audit sont fermes tres tot et
que l'operateur accepte explicitement un bonus borne sans obligation de le
livrer pour la cloture.

## Observabilité / logs / reset

Observabilite agentique V1 est close avec verdict `met`. Le reset destructif
n'a pas ete execute et reste bloque par `operator_go_required`. Ce point est
coherent entre AGENTS, README, app/docs/README, roadmap finale, TODO archivee
et contrat.

Content-free:

- artefact Lot Z Observabilite existe;
- artefact Lot 6 transverse existe;
- projections admin logs/export Markdown et dashboard sont documentees;
- content gate reste exception explicite;
- reset exige GO operateur humain date, scope exact, backup et rollback.

Risques classes:

- P2: occurrences `err=%s`, `str(exc)`, `error=str(exc)` hors
  `app/observability` restent a re-auditer avant cloture globale. Elles ont ete
  explicitement hors scope Lot 5C, donc ce n'est pas un finding stale.
- P3: `message_short=str(exc)` passe par `chat_turn_logger.emit_error`, qui
  stocke une projection content-free selon les tests, mais chaque chemin direct
  de retour JSON doit etre distingue.
- P3: les tokens/hashes courts qualifies restent nombreux mais contractes; ne
  pas ajouter de hash stable generique sur texte sensible.

## Docs / TODO / specs / archives

Coherences confirmees:

- README, AGENTS, app/docs/README et roadmap finale pointent vers les archives
  Continuity et Observabilite recentes;
- les specs V1 principales sont en `states/specs`;
- les archives produit recentes sont en `todo-done/product`;
- les artefacts Lot Z critiques sont en `states/baselines`;
- Mail est bonus non bloquant;
- SMS/TTS sont reportes.

Incoherences ou dettes:

- `frida-v1-generated-images-todo.md` garde un "Prochain pas" vers l'ancienne
  TODO Observabilite sous `todo-todo`.
- Les audits Lot 0 historiques Nextcloud/Observabilite referencent aussi
  l'ancien chemin `todo-todo/product/frida-v1-agentic-observability-todo.md`.
  Ces audits sont historiques, mais le chemin est maintenant archive.
- Plusieurs archives anciennes gardent des `[ ]`; certaines docs expliquent que
  ces cases sont historiques. La cloture finale gagnerait a ne pas les compter
  comme TODO vivants.
- La roadmap finale indique encore "Branche de travail courante:
  `FridaV1-Nextcloud-Folders`", alors que l'audit se fait sur
  `FridaV1-Continuity-Payload-Audit`. C'est mineur mais a nettoyer avant
  l'etat de cloture final.

Findings anciens non fantomes:

- Le finding arbiter provenance modele est explicitement stale/corrige dans
  AGENTS et ne doit pas etre rouvert sans regression.
- P3 offline payload export Continuity est ferme pour ce chantier par
  remplacement avec `main_payload_manifest_v1`, mais le script offline reste
  post-V1 possible.

## Tests / preuves / artefacts

Artefacts critiques verifies comme presents:

- Continuity Lot Z: 14 lignes.
- Observabilite Lot Z: 14 lignes.
- Images Lot Z: 18 lignes.
- Exports Lot Z: 23 lignes.
- Documents Lot Z: 14 lignes.
- Notes Lot Z: 16 lignes.
- Nextcloud folders Lot Z: 9 lignes pour l'artefact verifie.
- Agenda cloture ciblee: 16 lignes.

Scan content-free borne sur les familles JSONL critiques: aucun fichier
signale par les patterns de fuite cherches (`raw_*:true`, Authorization-like,
token-like, data URL/base64).

Preuves fortes:

- Nextcloud folders, Exports, Images PNG, Observabilite, Continuity ont des
  preuves live/smoke et scans Lot Z.
- Agenda a des smokes cibles utiles et une cloture pragmatique assumee.
- Biblio BIB-01 a BIB-33 est ferme live par artefacts content-free.

Preuves fragiles mais documentees:

- Documents non `linked`: covered_by_tests, pas live naturel.
- Notes conflit ETag: fake/unit, pas live concurrent propre.
- Images JPEG/WebP: tests/fakes, live observe PNG.
- Observabilite "tour normal/refus/vraie panne" parfois covered_by_tests quand
  le live exigerait mutation ou panne provoquee.

## Risques de régression

- Continuity Capsule et final locks Agenda/Biblio: le code bypass la capsule
  quand un final response lock existe. Le risque restant est une modification
  future de priorite ou d'injection tardive sans mise a jour du manifeste.
- Memory/Identity/Summary: la capsule n'ecrit pas dans ces sous-systemes et le
  manifeste distingue les roles. Le risque restant est doctrinal si un futur
  texte de capsule contient des faits identitaires.
- Writer guard: tres stricte et default-deny; risque de faux refus
  d'observabilite legitime si un nouveau schema n'est pas ajoute proprement.
  Risque inverse plus faible mais possible si des retours JSON directs
  contournent `chat_turn_logger`.
- Admin/UI: les grands read-models et `server.py` restent gros; un correctif
  final transversal peut casser une route admin si fait sans tests cibles.
- Docs: des archives ont bouge mais quelques references historiques restent
  stale.
- Branches: la branche courante contient les commits Continuity recents non
  presents dans `origin/main`; toute cloture sur `main` doit integrer ce travail.
- Architecture: aucun `utils.py` ou `helpers.py` trouve; pycache/pyc absents.
  En revanche plusieurs fichiers runtime depassent la zone de vigilance.

## Plan recommandé jusqu’au 3 juillet

- Jours 1-2, 2026-06-24 au 2026-06-25: comparer ce rapport au contre-audit,
  trancher P1/P2, decider la cible Git de cloture, corriger uniquement les P2
  acceptes comme bloquants.
- Jours 3-5, 2026-06-26 au 2026-06-28: micro-lot docs Agenda si retenu,
  micro-lot redaction/erreurs si P2-LOGS-01 confirme, micro-preuve Continuity
  Capsule si activation souhaitee.
- Jours 6-8, 2026-06-29 au 2026-07-01: audit/spec Mail seulement si les P2 sont
  sous controle; sinon reporter Mail. Rejouer smokes strictement necessaires,
  sans reset et sans provider live inutile.
- Buffer, 2026-07-02 au 2026-07-03: Lot final de decision, index de cloture,
  statut Git cible, verification content-free, decision reset observee mais non
  executee sans GO explicite.

La roadmap interne cite une cible de cloture au 2026-07-02; la demande courante
vise le 2026-07-03. Garder le 2026-07-03 comme buffer humain/contre-audit.

## No-go avant clôture

- Declarer V1 close sans comparaison au contre-audit.
- Declarer V1 close sur `main` si les commits de la branche courante ne sont
  pas integres a la cible.
- Activer la Continuity Capsule sans texte approuve, micro-preuve
  content-free et rollback verifie.
- Executer le reset observabilite sans GO operateur humain explicite, date,
  separe, avec backup/rollback.
- Prendre Mail runtime comme bloquant Frida 1.0.
- Laisser un retour JSON direct `str(exc)` sur une surface sensible sans
  decision de risque.
- Rouvrir Agenda ou Biblio abstraitement hors bug reel ou besoin concret.
- Faire une migration DB, purge, backfill, provider live, Nextcloud write ou
  modification plateforme dans le lot de cloture finale sans scope dedie.

## Annexes content-free

### Commandes exécutées

- `git status --short --branch`
- `git branch --show-current`
- `git log --oneline -12`
- `git diff --check`
- `git fetch origin main`
- `git pull --ff-only origin main`
- lectures `sed`/`grep` de `AGENTS.md`, `README.md`, `app/docs/README.md`,
  roadmap finale, specs, TODO, audits et archives pertinentes.
- scans obligatoires `grep` Continuity, Observabilite, Agenda, Mail, references
  stale, checkboxes ouvertes, signaux `err=%s`/`str(exc)`/`raw_`/hash.
- `find app/docs -maxdepth 4 -type f | sort | grep -E ...`
- `find app -path "*__pycache__*" -o -name "*.pyc"`
- `find app -type f \( -name "utils.py" -o -name "helpers.py" \)`
- probe runtime content-free de `resolve_continuity_capsule()`.
- `docker ps --filter name=platform-fridadev ...`
- inventaires d'artefacts JSONL Lot Z par existence et lignes.
- scan content-free des JSONL critiques par liste de fichiers seulement.

### Fichiers relus

- `AGENTS.md`
- `README.md`
- `app/docs/README.md`
- `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`
- `app/docs/todo-done/product/frida-v1-continuity-payload-todo.md`
- `app/docs/states/specs/frida-v1-continuity-payload-contract.md`
- `app/docs/todo-done/product/frida-v1-agentic-observability-todo.md`
- `app/docs/states/specs/frida-v1-agentic-observability-contract.md`
- `app/docs/todo-done/product/frida-v1-generated-images-todo.md`
- `app/docs/states/specs/frida-v1-generated-images-contract.md`
- `app/docs/todo-done/product/frida-v1-exports-todo.md`
- `app/docs/states/specs/frida-v1-exports-contract.md`
- `app/docs/todo-done/product/frida-v1-nextcloud-folders-todo.md`
- `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
- `app/docs/todo-done/product/frida-v1-documents-ingestion-todo.md`
- `app/docs/states/specs/frida-v1-documents-ingestion-contract.md`
- `app/docs/todo-done/product/frida-v1-folder-markdown-notes-todo.md`
- `app/docs/states/specs/frida-v1-folder-markdown-notes-contract.md`
- `app/docs/todo-todo/product/frida-agenda-agent.md`
- `app/docs/states/specs/frida-agenda-agent-contract.md`
- `app/docs/states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`
- `app/docs/states/audits/frida-agenda-question-cartography-2026-06-09.md`
- `app/docs/todo-todo/product/frida-v1-mail-bonus-todo.md`
- `app/docs/todo-done/product/frida-v1-final-audit-todo.md`
- docs Biblio natives, agent, archives Last Chance et audit architecture.
- code: `app/core/continuity_capsule.py`, `app/core/chat_service.py`,
  `app/observability/main_payload_manifest.py`,
  `app/observability/main_payload_manifest_lanes.py`, `app/server.py`.

### Artefacts cités

- `app/docs/states/baselines/continuity-payload-smokes/frida-v1-continuity-payload-lotz-closure-20260623T100649Z.jsonl`
- `app/docs/states/baselines/agentic-observability-smokes/frida-v1-agentic-observability-lotz-closure-20260622T081658Z.jsonl`
- `app/docs/states/baselines/generated-images-smokes/frida-v1-generated-images-lotz-closure-20260620T130636Z.jsonl`
- `app/docs/states/baselines/exports-smokes/frida-v1-exports-lotz-closure-20260619T150617Z.jsonl`
- `app/docs/states/baselines/documents-smokes/frida-v1-documents-lotz-closure-20260618T073325Z.jsonl`
- `app/docs/states/baselines/notes-smokes/frida-v1-notes-lotz-closure-20260618T134905Z.jsonl`
- `app/docs/states/baselines/nextcloud-folder-smokes/frida-v1-nextcloud-folders-lotz-live-closure-20260617T104124Z.jsonl`
- `app/docs/states/baselines/nextcloud-folder-smokes/frida-v1-nextcloud-folders-lotz-live-closure-20260617T104258Z.jsonl`
- `app/docs/states/baselines/agenda-smokes/frida-agenda-v1-targeted-closure-smokes-20260609T175408Z.jsonl`
- Biblio JSONL sous `app/docs/states/baselines/biblio-smokes/`.

## Auto-audit

- Audit content-free: oui.
- Secret affiche: non.
- Log brut affiche/conserve: non.
- Prompt brut ou payload provider: non.
- Contenu utilisateur brut: non.
- Runtime modifie: non.
- Reset/purge/backfill/migration: non.
- Activation Continuity Capsule: non.
- TODO/spec/roadmap hors audit modifiee: non.
- Pycache/temp crees: non.
- `utils.py` / `helpers.py` crees: non.
