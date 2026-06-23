# Frida V1 - Final Global Counter-Audit - 2026-06-23

## Statut

Contre-audit read-only produit depuis la session lead, en parallele de l'audit
principal demande a Celebrimbor.

Ce document ne corrige rien. Il consolide une relecture SSH-based sur OVH et
cinq sous-audits independants:

- Hume: coherence docs, roadmap, TODO et specs.
- Ampere: Continuity Capsule, runtime, manifeste payload.
- Boyle: observabilite, logs, content-free et reset.
- Kepler: tests, smokes, artefacts JSONL et preuves.
- Hypatie: Agenda, Mail bonus et calendrier jusqu'au 3 juillet.

Aucun secret, log brut, prompt brut, contenu utilisateur brut, payload provider
ou contenu documentaire n'est conserve dans ce fichier.

## Verdict court

- Cloture V1 possible: conditionnelle.
- Risque global: moyen tant que les P2 ci-dessous ne sont pas traites ou
  explicitement acceptes.
- Continuity Capsule: activer apres micro-preuve, pas immediatement.
- Agenda: pragmatiquement fini pour V1, mais encore ambigu dans sa TODO active.
- Mail bonus: non bloquant; recommandation spec/audit-only si on le prend avant
  le 3 juillet.
- Audit final general: pas encore executable comme cloture complete; la TODO est
  trop squelettique.

## Findings

### P1

Aucun P1 confirme dans ce contre-audit.

### P2

#### P2-FINAL-AUDIT-01 - La TODO d'audit final reste trop squelettique

- Fichier: `app/docs/todo-todo/product/frida-v1-final-audit-todo.md`
- Lignes observees: `1-36`

La roadmap finale fait de l'audit final general un point obligatoire avant
cloture Frida 1.0, mais la TODO dediee dit encore `Statut: TODO a detailler` et
renvoie a une matrice, des commandes, des smokes et un format de rapport a
definir dans un lot separe.

Impact: les preuves des chantiers V1 sont largement presentes, mais la cloture
finale globale n'a pas encore de protocole executable source-of-truth.

Correction recommandee: transformer cette TODO en plan d'audit final lotable,
avec matrice GO / PARTIAL / NO-GO, commandes, smokes minimaux, criteres de
cloture et format d'artefact.

#### P2-LEGACY-ADMIN-LOGS-01 - `/api/admin/logs` legacy contourne la projection admin logs chat

- Fichiers:
  - `app/server.py:969-976`
  - `app/admin/admin_logs.py:74-88`, `91-106`, `292-301`
  - `app/core/chat_llm_flow.py:583-594`, `669-683`, `773-794`

`/api/admin/logs/chat` passe par la projection admin content-free recente.
En revanche `/api/admin/logs` renvoie directement `admin_logs.read_logs()`. Le
writer legacy `admin_logs.log_event()` ne retire que quelques cles exactes, et
plusieurs branches LLM ecrivent encore `error=str(exc)`.

Impact: aucune fuite brute n'a ete constatee dans les scans bornes, mais la
surface legacy peut encore exposer une chaine d'exception si un provider, une
lib ou un chemin d'erreur y met du contexte sensible. C'est incoherent avec le
niveau d'exigence Observabilite V1.

Correction recommandee: soit deprecier explicitement `/api/admin/logs`, soit
lui appliquer une projection/redaction stricte comparable a `/api/admin/logs/chat`,
et remplacer les `error=str(exc)` legacy par `error_class` / `error_code` /
reason code content-free.

#### P2-LOG-READ-FAIL-CLOSED-01 - Des pannes de lecture logs peuvent devenir `ok` avec liste vide

- Fichiers:
  - `app/observability/log_store.py:449-465`
  - `app/server.py:1008-1019`
  - `app/admin/admin_logs.py:91-106`
  - `app/server.py:969-976`

`read_chat_log_events()` capture une exception large, logge une erreur
content-free, puis retourne un resultat vide. La route admin repond ensuite
`ok: true`. Meme logique legacy: `admin_logs.read_logs()` retourne `[]` en cas
d'erreur lecture puis la route repond `ok: true`.

Impact: un dashboard/logs peut paraitre propre alors que la lecture est cassee.
Cela contredit l'objectif de ne pas masquer les vraies pannes.

Correction recommandee: fail-closed cote API admin (`ok=false`, statut 5xx ou
reason code dedie) en gardant la cause brute masquee.

#### P2-NEXTCLOUD-SPEC-STALE-01 - La spec Nextcloud folders contredit les lots Documents/Notes/Exports/Images clos

- Fichier: `app/docs/states/specs/frida-v1-nextcloud-folders-contract.md`
- Lignes observees: `1187-1206`, `1282-1336`

La spec est marquee cloturee Lot Z en tete, mais certains blocs disent encore
que le runtime fichiers reste a livrer, que Notes/Exports/Images sont des lots
futurs, et que Documents/Notes/Exports/Images doivent etre cadres plus tard.
La roadmap finale et les specs dediees disent pourtant que Documents, Notes,
Exports et Images V1 sont maintenant clotures en Lot Z.

Impact: contradiction documentaire source-of-truth. Pour un operateur qui relit
la spec Nextcloud folders seule, l'etat des artefacts V1 est faux.

Correction recommandee: micro-correctif docs-only pour requalifier ces sections
comme historique pre-lots dedies, ou les aligner sur les contrats dedies clos.

#### P2-AGENDA-DORMANT-STATUS-01 - Agenda est dormant post-V1 mais sa TODO se dit encore active

- Fichiers:
  - `app/docs/todo-todo/product/frida-agenda-agent.md:1-39`
  - `app/docs/states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md:11-24`, `91-129`

Agenda V1 est documente comme cloture pragmatiquement et a rouvrir seulement
sur bug reel, besoin concret ou decision explicite. Pourtant la TODO dit encore
`Statut: TODO actif` et conserve de nombreuses cases ouvertes.

Impact: ambiguite de pilotage. On peut croire qu'Agenda bloque encore Frida 1.0,
alors que les docs de cloture le classent comme post-V1 dormant.

Correction recommandee: docs-only. Renommer le statut en `post-V1 dormant`,
expliciter que les cases ouvertes sont non bloquantes pour V1, et garder la
TODO comme carte de reprise, pas chantier actif.

#### P2-CONTINUITY-AUDITS-ACTIVE-01 - Les audits Continuity sources restent dans `todo-todo/audits` avec findings vivants

- Fichiers:
  - `app/docs/todo-todo/audits/frida-v1-continuity-payload-audit-2026-06-22.md:468-554`
  - `app/docs/todo-todo/audits/frida-v1-continuity-payload-counter-audit-2026-06-22.md:24-80`
  - `app/docs/todo-done/product/frida-v1-continuity-payload-todo.md`

La TODO Continuity Payload est archivee et tous les findings y sont clos ou
traites pour ce chantier. Mais les deux audits sources restent dans `todo-todo`
et parlent encore de P1/P2/P3 comme findings vivants.

Impact: finding fantome documentaire. Un audit global peut relire ces sources
et croire que Continuity est encore ouverte, malgre Lot Z et Z.1.

Correction recommandee: soit deplacer ces audits sous `todo-done/audits`, soit
ajouter un en-tete clair `supersede par frida-v1-continuity-payload-todo.md`,
sans reecrire l'historique des constats.

#### P2-CAPSULE-ACTIVATION-PROOF-01 - La Continuity Capsule est livree mais pas prouvee avec son texte exact de production

- Fichiers:
  - `app/core/continuity_capsule.py:186-269`
  - `app/core/chat_service.py:1167-1223`
  - `app/docs/todo-done/product/frida-v1-continuity-payload-todo.md`

La capsule est utilisable runtime, desactivee par defaut, configurable sans DB
ni migration, et observable content-free. Mais aucun texte exact d'activation
operateur n'a encore ete valide ni prouve en live/staging avec manifeste.

Impact: la capsule ne doit pas etre activee directement en production sans
micro-preuve. Le risque n'est pas une faille technique evidente, mais une derive
produit: texte trop large, trop souverain, trop factuel, ou non conforme a la
presence souhaitee.

Correction recommandee: micro-lot d'activation: rediger un texte court de
capsule, le valider par la policy unsafe, l'activer temporairement dans un
contexte controle, verifier `main_payload_manifest_v1` content-free
(`status=ok`, `injected_count=1`, role provider `system`, role logique
`continuity_capsule`), puis decider GO/NO-GO operateur.

### P3

#### P3-ROADMAP-BRANCH-STALE-01 - La roadmap indique une ancienne branche de travail

- Fichier: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md:6`

La branche affichee est encore `FridaV1-Nextcloud-Folders`, alors que l'etat OVH
lu pendant ce contre-audit est `FridaV1-Continuity-Payload-Audit` au commit
`26667a0b`.

#### P3-README-DATE-STALE-01 - Le README annonce un etat courant du 2026-05-29

- Fichier: `README.md:3-4`

Le README reference des livraisons jusqu'au 2026-06-23, mais son en-tete dit
encore `Current repository state as of Friday, May 29, 2026`.

#### P3-ARCHIVE-REFERENCES-STALE-01 - Des archives V1 pointent encore vers anciens chemins actifs

- Fichiers observes:
  - `app/docs/todo-done/product/frida-v1-documents-ingestion-todo.md`
  - `app/docs/todo-done/product/frida-v1-exports-todo.md`
  - `app/docs/todo-done/product/frida-v1-generated-images-todo.md`

Certaines references internes historiques pointent encore vers des chemins
`todo-todo` pour des chantiers maintenant archives. Ce n'est pas bloquant si le
contexte historique est clair, mais cela pollue la relecture finale.

#### P3-DOCUMENTS-ARCHIVE-CHECKBOX-01 - Une case ouverte reste dans l'archive Documents V1

- Fichier: `app/docs/todo-done/product/frida-v1-documents-ingestion-todo.md:651`

Le statut de tete et Lot Z expliquent `met_with_documented_limit`; la case
ouverte n'est donc pas un no-go produit. Mais un scan litteral des archives la
remonte, ce qui fragilise l'audit final automatise.

#### P3-CAPSULE-FINAL-LOCK-ORDER-01 - Sous final-lock, une capsule unsafe est observee `not_selected` avant `refused`

- Fichier: `app/core/continuity_capsule.py:229-249`

L'ordre actuel evalue la taille, puis le final-lock bypass, puis le contenu
unsafe. Donc si un final lock est present, une capsule unsafe ne fuit pas et
n'est pas injectee, mais elle sera observee comme `not_selected` plutot que
`refused`.

Ce n'est pas bloquant, mais c'est moins explicite pour un audit de safety.

#### P3-SCOPED-LOG-DELETE-GATE-01 - Suppression logs scoped hors gate reset explicite

- Fichiers:
  - `app/server.py:1216-1235`
  - `app/observability/log_store.py:1009-1062`
  - `app/docs/states/specs/frida-v1-agentic-observability-contract.md:352-390`

Le reset global est correctement bloque sans GO operateur. En revanche la route
de suppression par conversation/turn existe sans backup ni GO reset. Si elle est
consideree comme gestion admin courante, elle est acceptable; si elle tombe dans
la doctrine reset post-cloture, il faut la cadrer.

#### P3-STATUS-FLATTENING-01 - Certains emitters aplatisent tout non-error en `ok`

- Fichier: `app/core/chat_service.py:403-486`

Les emitters Adobe et Notes convertissent certains statuts non `error` en `ok`.
Selon les payloads reels, cela peut etre correct ou peut masquer `failed`,
`refused`, `not_configured`, `skipped`. A verifier par micro-audit cible avant
cloture zero-erreur.

#### P3-BIBLIO-AUDIT-CURRENT-STALE-01 - Un audit Biblio ancien reste presente comme courant

- Fichier: `app/docs/states/audits/frida-biblio-librarian-agent-architecture-audit-2026-05-31.md`

Biblio est cloture par archive dediee 33/33, mais cet audit ancien conserve des
findings P1/P2/P3 et un vocabulaire d'audit courant. Non bloquant, mais a
requalifier si l'audit final global parcourt toutes les sources.

## Continuity Capsule - Analyse d'activation

Verdict: `ACTIVER APRES MICRO-PREUVE`.

Ce qui est acquis:

- desactivee par defaut;
- activable par `CONTINUITY_CAPSULE_*` dans le module config, avec fallback env
  `FRIDA_CONTINUITY_CAPSULE_*`;
- max par defaut 900 caracteres;
- refuse absence, taille excessive, marqueurs unsafe, credentials, URL-like,
  chemins prives, XML/DAV/WebDAV/CALDAV, base64 evident, cles privees;
- pas d'injection si Agenda/Biblio produit un final lock;
- injection provider role `system`, mais role logique `continuity_capsule`;
- pas d'ecriture identity, memory ou summary;
- observee par `main_payload_manifest_v1` sans contenu brut ni fingerprint.

Ce qui manque avant activation:

- texte exact de capsule decide par operateur;
- preuve avec ce texte exact ou un substitut synthetique strictement equivalent;
- verif que le manifeste live expose `status=ok`, `injected_count=1`,
  `provider_role=system`, `logical_roles=["continuity_capsule"]`;
- confirmation que la capsule n'est pas traitee comme identite canonique;
- mini-runbook de rollback: remettre `CONTINUITY_CAPSULE_ENABLED=false` ou
  supprimer le texte runtime.

Recommandation: ne pas l'activer dans le meme geste que l'audit final. Faire un
micro-lot d'activation borne, puis GO operateur.

## Agenda - Etat reel

Verdict: Agenda est `post-V1 dormant / pragmatiquement fini`, pas un blocage
Frida 1.0.

Preuves et statut:

- audit de cloture pragmatique: `app/docs/states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`;
- utilisable pour les usages prouves;
- limites post-V1 explicites: disponibilites riches, invitations, rappels,
  recurrences riches, mutations utilisateur reelles, persistance robuste de
  pending actions apres restart;
- reouverture seulement sur bug reel, besoin concret ou decision operateur.

Travail minimal restant:

1. docs-only: aligner le statut de `frida-agenda-agent.md` sur `post-V1 dormant`;
2. distinguer cases ouvertes non bloquantes vs no-go;
3. optionnel: probe runtime content-free du mode Agenda courant, sans lire
   evenements ni secrets.

## Mail bonus - Etat reel

Verdict: `PRENDRE SEULEMENT AUDIT/SPEC MAIL` si on veut utiliser la marge; sinon
report post-V1.

Constats:

- `frida-v1-mail-bonus-todo.md` est volontairement court;
- Mail est non bloquant Frida 1.0;
- aucune surface applicative Mail V1 complete n'a ete trouvee;
- invariants deja clairs: pas d'envoi sans confirmation humaine, pas de secrets
  en logs, fakes avant live, audit no-op d'abord.

Recommandation calendrier: ne pas construire un agent Mail complet avant le 3
juillet. Si marge: Lot 0 audit no-op + Lot 1 spec, puis stop sauf GO explicite.

## Observabilite / logs / reset

- Reset global observabilite: non execute, gate operateur respecte.
- Logs Docker/applicatifs recents: scans content-free annonces propres dans les
  artefacts Observabilite et confirmes par sous-audit sans lignes brutes.
- Admin logs chat/dashboard/export Markdown: globalement durcis.
- Surface legacy `/api/admin/logs`: P2 a traiter avant cloture zero-surprise.
- Content gate dashboard: exception separee et documentee.

## Tests / preuves / artefacts

Resultats du contre-audit Kepler:

- references JSONL trouvees: 186;
- references manquantes: 0;
- fichiers JSONL verifies: 118;
- JSONL invalides ou vides: 0;
- les statuts `met`, `not_applicable`, `covered_by_tests` sont globalement
  coherents avec les docs;
- les artefacts intermediaires `partial` ou `failed` ont des artefacts Lot Z ou
  correctifs ulterieurs, sauf quand documentes comme limites volontaires.

Fragilites:

- certains artefacts historiques utilisent encore vocabulaire comme
  `secret_available=true`, sans valeur secrete exposee; acceptable mais moins
  propre que `secret_configured_status=redacted`;
- preuves finales parfois `covered_by_tests` plutot que live, mais les limites
  sont generalement documentees.

## Plan recommande jusqu'au 3 juillet

### 23-24 juin

- Recevoir et comparer l'audit Celebrimbor et ce contre-audit.
- Corriger P2 docs/logs les plus nets: final audit TODO, Agenda dormant,
  Nextcloud spec stale, legacy admin logs.

### 25 juin

- Finaliser la matrice d'audit final general.
- Decider micro-lot Continuity Capsule activation ou report.

### 26-27 juin

- Executer smokes strictement necessaires, pas de nouveau chantier produit.
- Si capsule: micro-preuve + runbook rollback + GO operateur.

### 28-30 juin

- Nettoyage documentation/index/archives.
- Option Mail: audit/spec only, pas agent complet.

### 1er juillet

- Correctifs P1/P2 seulement.
- Freeze fonctionnel.

### 2 juillet

- Lot Z audit final general, decision GO/PARTIAL/NO-GO.

### 3 juillet

- Buffer. Aucun nouveau produit.

## No-go avant cloture

- Laisser `/api/admin/logs` legacy comme surface brute non projetee.
- Laisser la TODO d'audit final squelettique.
- Declarer Agenda actif et dormant simultanement.
- Activer la Continuity Capsule sans micro-preuve du texte exact.
- Lancer Mail comme chantier runtime complet avant de clore V1.
- Executer un reset observabilite sans GO operateur humain explicite, date,
  separe, backup et rollback.

## Annexes content-free

Commandes et lectures principales:

- `git status --short --branch`
- `git log --oneline -12`
- lecture `AGENTS.md`, `README.md`, `app/docs/README.md`, roadmap finale;
- lecture TODO/specs Continuity, Observabilite, Nextcloud folders, Agenda, Mail;
- scans grep content-free sur logs/observabilite/capsule;
- parse JSONL des artefacts sous `app/docs/states/baselines`;
- sous-audits read-only Hume, Ampere, Boyle, Kepler, Hypatie.

Aucune ligne de log brute, aucun secret, aucun prompt brut, aucun contenu
utilisateur brut, aucune valeur de capsule reelle et aucun payload provider ne
sont inclus dans ce rapport.
