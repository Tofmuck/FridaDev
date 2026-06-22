# Frida V1 - Observabilite globale / logs agentiques - TODO archivee

Statut: chantier Frida V1 cloture et archive en Lot Z le 2026-06-22.
Lots 0 et 1 docs-only livres; Lot 2 runtime borne livre avec correctifs
Lot 2.1 / 2.2 writer; Lot 3 Agenda/Biblio no-op observability livre avec
correctifs Lot 3.1 / 3.2; Lot 4 logs runtime content-free livre avec correctif
Lot 4.1; Lot 5A admin logs/export Markdown content-free livre avec correctif
Lot 5A.1 value redaction; Lot 5B dashboard statuses livre avec correctif
Lot 5B.1 providers secondaires; Lot 5C reliquats/scans residuels livre; Lot 6
smokes transverses content-free livre; correctif Lot 6.1 hygiene test
dashboard livre; Lot Z preuve/cloture livre. Reset observabilite destructif
non execute: il reste une operation post-cloture separee, bloquee par
`operator_go_required`.
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`
Audit Lot 0:
`app/docs/states/audits/frida-v1-agentic-observability-lot0-audit-2026-06-20.md`
Contrat source:
`app/docs/states/specs/frida-v1-agentic-observability-contract.md`

## Objectif produit

Rendre l'observabilite Frida 1.0 lisible en mode agentique sans exposer de
contenu brut et sans transformer des comportements attendus en erreurs.

Une vraie panne doit rester visible. Un log `ERROR` ou `WARNING` doit etre:

- coherent avec le code et le mode actif;
- content-free;
- actionnable;
- classe par famille;
- distinct d'un refus produit attendu, d'un skip/no-op normal ou d'une
  dependance volontairement non appelee.

## Sources de verite

- Roadmap finale Frida 1.0:
  `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`
- Audit Lot 0:
  `app/docs/states/audits/frida-v1-agentic-observability-lot0-audit-2026-06-20.md`
- Contrat source Lot 1:
  `app/docs/states/specs/frida-v1-agentic-observability-contract.md`
- Surface agentique:
  `app/docs/states/specs/agentic-response-surface-contract.md`
- Agenda V1:
  `app/docs/states/specs/frida-agenda-agent-contract.md`
  et
  `app/docs/states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`
- Biblio:
  `app/docs/states/specs/frida-biblio-librarian-agent-contract.md`
- Observabilite existante:
  `app/observability/`
- Logs de tour:
  `observability.chat_log_events`
- JSONL applicatifs:
  `/app/logs/*.jsonl` dans le conteneur runtime.

## Hors-scope V1 de ce chantier

- Refonte complete du dashboard.
- Nouveau systeme de logs plateforme.
- Mutation Docker/Caddy/Authelia/secrets.
- Masquage de vraies pannes.
- Backfill historique sans decision explicite.
- Reouverture runtime Agenda.
- Exposition de contenu utilisateur, prompts, payloads provider, DAV/XML,
  ETag, data URL, base64, cookies, tokens ou secrets.

## Decisions fermees par le Lot 1

- `refused` est un statut V1 explicite pour les refus produit attendus.
- Agenda off doit etre observe explicitement en content-free, sans appel CalDAV,
  secret, OpenRouter ou outil Agenda.
- `tools_access_denied` / `admin_access_denied` restent des `WARNING` securite
  avec famille `access_denied_security`.
- Le champ non qualifie `raw` est interdit dans les nouveaux JSONL et doit etre
  projete/renomme pour les surfaces V1.
- L'historique `chat_log_events` reste non requalifie; le dashboard doit
  distinguer historique et fenetre recente.
- Le reset observabilite post-cloture est decide normativement, mais interdit
  avant Lot Z ou lot dedie explicite.

## Regles cibles a stabiliser

Vocabulaire attendu:

- `ok`: operation observee et conforme;
- `skipped`: operation ignoree proprement quand aucun statut plus precis ne
  s'applique;
- `disabled`: toggle ou feature explicitement off;
- `not_selected`: agent/outillage disponible mais non choisi;
- `not_configured`: prerequis operateur absent;
- `not_applicable`: branche hors sujet;
- `refused`: entree utilisateur ou etat produit refuse proprement;
- `failed`: tentative effectuee et echec degrade/recoverable;
- `error`: panne runtime ou contrat casse.

Severite attendue:

- `DEBUG`: bruit developpement non necessaire en production;
- `INFO`: etapes attendues, skips normaux, refus produit traites;
- `WARNING`: degradation secondaire, tentative suspecte, compensation non
  critique ou signal securite choisi;
- `ERROR`: panne runtime, echec principal, corruption, rollback critique ou
  divergence non masquee.

## Lots

### Lot 0 - Audit logs complet read-only/docs-only

- [x] Relire docs sources, roadmap, Agenda, README et hub docs.
- [x] Scanner `docker logs platform-fridadev` borne et date sans conserver de
  log brut.
- [x] Inventorier `/app/logs/*.jsonl` sans recopier de lignes brutes.
- [x] Interroger `observability.chat_log_events` en compteurs content-free.
- [x] Scanner les preuves JSONL recentes utiles.
- [x] Inventorier `logger.*`, `logging.*`, `app.logger.*`, `print`,
  `traceback`, `exc_info`, reason codes et events observability.
- [x] Classifier les familles de logs.
- [x] Identifier les cas agentiques ambigus.
- [x] Clarifier le statut Agenda sans rouvrir Agenda runtime.
- [x] Produire l'audit Lot 0:
  `app/docs/states/audits/frida-v1-agentic-observability-lot0-audit-2026-06-20.md`.
- [x] Ne conserver aucun fichier temporaire ni log brut.

### Lot 1 - Contrat source-of-truth observabilite agentique

- [x] Fermer les decisions du Lot 0.
- [x] Definir le vocabulaire status/reason/severity.
- [x] Definir les familles de logs et leur niveau cible.
- [x] Definir la politique historique vs fenetre recente.
- [x] Definir les interdits content-free transversaux.
- [x] Definir les tests anti-fuite minimaux.
- [x] Trancher la correction documentaire Agenda hors runtime: maintien
  temporaire en `todo-todo`, mais libelle post-V1 dormant dans les index, sans
  le vendre comme chantier runtime actif.
- [x] Specifier le reset observabilite post-cloture avec backup, inventaire,
  exclusions produit, preuves content-free et rollback.
- [x] Ne modifier aucun runtime dans ce lot.
- [x] Produire le contrat source:
  `app/docs/states/specs/frida-v1-agentic-observability-contract.md`.

### Lot 2 - Harmonisation `chat_turn_logger` / checklist / read-model

- [x] Corriger les faux `error` pour refus produit attendus.
- [x] Distinguer `not_applicable`, `disabled`, `not_selected`,
  `not_configured`, `refused`, `failed` et `error`.
- [x] Garder les vraies pannes en `ERROR` ou `status=error`.
- [x] Etendre/projeter `chat_log_events.status` vers la taxonomie V1 sans
  backfill implicite.
- [x] Adapter `turn_observability_checklist` pour ne pas degrader les skips
  normaux.
- [x] Ajouter tests de classification sur tours chat.
- [x] Ne pas backfiller l'historique; tout backfill reste interdit hors lot
  destructif explicite.
- [x] Correctif Lot 2.1: marquer les nouveaux evenements
  `chat_turn_logger` en `agentic_v1`, y compris `ok/skipped/error`.
- [x] Correctif Lot 2.1: empecher un statut writer invalide de devenir `ok`;
  l'evenement devient `error` content-free avec reason
  `agentic_status_invalid`.
- [x] Correctif Lot 2.2: empecher tout `error_code` ou payload caller
  d'ecraser le payload minimal redacted de la branche writer invalid status.

### Lot 3 - Agentic Agenda / Biblio observability

- [x] Aligner Agenda et Biblio sur une grammaire commune.
- [x] Appliquer l'observation explicite Agenda off prevue par le contrat.
- [x] Distinguer outil non selectionne, agent non configure, mode off, secret
  absent et echec reel.
- [x] Tester que CalDAV/Catalogue non appeles volontairement ne sont pas des
  erreurs.
- [x] Ne pas rouvrir Agenda runtime hors observabilite.

Notes Lot 3:

- Agenda absent/off emet un evenement `agenda` `status=disabled`,
  `reason_code=agenda_toggle_off`, `status_schema_version=agentic_v1`, sans
  appel Agenda runtime, CalDAV, secret, LLM Agenda ou mutation.
- Biblio off emet `status=disabled`; Biblio on sans signal bibliographique
  emet `status=not_selected`, sans appel Catalogue.
- Les pannes Agenda/Biblio fake/local restent `error` ou `failed` et ne sont
  pas degradees en no-op.
- Correctif Lot 3.1: les resultats Agenda `status=fallback` ne sont plus
  projetes en `ok`: secret/modele/provider absent deviennent
  `not_configured`, mode unsupported devient `not_applicable`, erreur provider
  devient `error`, et les rejets validation/plan deviennent `failed`.

### Lot 4 - Durcissement logs runtime content-free

- [x] Inventorier les logs runtime a risque avant patch.
- [x] Remplacer les logs `err=%s` Lot 4 confirmes par `err_class` + reason code:
  `crawl_error`, `reformulate_error`, `chat_turn_log_emit_failed`,
  `chat_log_event_insert_failed`.
- [x] Ne plus logger `conversation_id` client brut invalide; exposer seulement
  presence, longueur et hash court.
- [x] Ne plus logger URL externe brute dans web crawl errors; exposer seulement
  scheme, hash court host, presence query/fragment et longueur.
- [x] Conserver les pannes actionnables aux niveaux `WARNING` / `ERROR`.
- [x] Ajouter tests anti-fuite ou probes unitaires ciblés.

Notes Lot 4:

- Les vraies pannes restent visibles: `crawl_error` et
  `chat_turn_log_emit_failed` restent `WARNING`, `chat_log_event_insert_failed`
  reste `ERROR`.
- Les autres `err=%s` releves dans les stores DB, dashboard, exports markdown
  ou flux larges restent hors Lot 4 quand leur correction demanderait une
  refonte/projection plus large; ils sont a traiter par Lot 5/6 ou par lots
  dedies sans masquer de panne reelle.
- Aucun reset, purge, backfill, migration ou scan logs live n'a ete execute
  dans ce lot.

### Lot 5 - JSONL admin / dashboard / projections

Le Lot 5 complet n'est pas ouvert en bloc. Il est decoupe en sous-lots
deterministes pour eviter un patch transversal melant admin logs, export
Markdown, dashboard, schemas JSONL et logs store/dashboard.

Ordre cible:

- [x] Lot 5A avant 5B/5C, sauf meilleur plan explicitement justifie avant patch.
- [x] Lot 5B apres 5A, sauf finding bloquant propre au dashboard.
- [x] Lot 5C apres 5A/5B, sauf micro-correctif content-free strictement borne.

#### Lot 5A - Admin logs et export Markdown content-free

Objectif:

- [x] Rendre les surfaces admin logs et export Markdown conformes V1
  content-free sans casser inutilement la compat UI existante.

Surfaces visees:

- [x] `/api/admin/logs/chat`.
- [x] `/api/admin/logs/chat/metadata`.
- [x] `/api/admin/logs/chat/turns`.
- [x] `/api/admin/logs/chat/metrics` si des payloads historiques y sont
  exposes.
- [x] `/api/admin/logs/chat/export.md`.
- [x] `observability.log_store.read_chat_log_events`.
- [x] `observability.log_markdown_export`.

Critere de fin:

- [x] Les payloads historiques exposes par les surfaces admin sont projetes ou
  allowlistes.
- [x] Aucun prompt, message utilisateur, payload provider, DAV/XML, ETag brut,
  secret, token, cookie, header sensible ou contenu brut n'est expose.
- [x] Aucun champ `raw` non qualifie n'est introduit.
- [x] Toute compat UI conservee est documentee avec indicateurs explicites,
  par exemple `raw_event_payloads_included=false`,
  `raw_content_included=false`, `raw_prompt_included=false`,
  `raw_provider_payload_included=false` et
  `raw_webdav_payload_included=false`.
- [x] L'export Markdown indique qu'il est resume/content-free et ne reproduit
  aucun payload brut.

Hors scope:

- [x] Ne pas modifier la logique dashboard hors dependance stricte de
  projection admin logs.
- [x] Ne pas modifier Agenda, Biblio, Documents, Notes, Exports ou Images.
- [x] Ne pas reset, purger, backfiller ou migrer.

Tests/proofs attendus:

- [x] Tests sentinelles anti-fuite sur `/api/admin/logs/chat`.
- [x] Tests sentinelles anti-fuite sur `/api/admin/logs/chat/export.md`.
- [x] Test de compat UI si le champ `payload` reste present mais projete.
- [x] Scan de diff prouvant l'absence de nouveau champ `raw` non qualifie.

Notes Lot 5A:

- La projection dediee `observability.admin_log_projection` expose une surface
  admin V1 content-free en gardant `payload` comme compat UI projetee.
- Correctif Lot 5A.1: les valeurs sous cles allowlistees sont redacted si
  elles ressemblent a une URL, un path/target, un token/Bearer, un header, un
  credential, un payload DAV/XML ou un email; `model` conserve seulement le
  format content-free explicitement valide, par exemple `openai/gpt-5.4-mini`.
- `/api/admin/logs/chat` force `payload_projection=admin` et reprojette
  defensivement la reponse avant JSON.
- `log_markdown_export` utilise la meme projection et declare dans l'export
  Markdown `content_free=true` et les flags raw qualifies a `false`.
- Les read-models `/api/admin/logs/chat/turns` et
  `/api/admin/logs/chat/metrics` restent compacts/content-free; les calculs
  internes peuvent lire le payload DB mais ne l'exposent pas.
- Aucun dashboard `/api/admin/dashboard/*`, reset, purge, backfill, migration,
  Agenda, Biblio, Documents, Notes, Exports ou Images n'a ete modifie.

#### Lot 5B - Dashboard historique/recent et statuts agentiques

Objectif:

- [x] Harmoniser les surfaces dashboard avec la taxonomie V1 sans masquer les
  vraies pannes et sans compter les no-op/refus normaux comme erreurs.

Surfaces visees:

- [x] `/api/admin/dashboard/*`.
- [x] `observability.dashboard_read_model`.
- [x] `observability.dashboard_analytics_projection`.
- [x] `observability.dashboard_materialization_runtime`.
- [x] `observability.dashboard_content_gate` uniquement comme exception
  explicite, bornee, auditee et documentee.

Critere de fin:

- [x] Les evenements legacy et `agentic_v1` sont distinguables dans les vues
  recentes/historiques.
- [x] `disabled`, `not_selected`, `not_configured`, `not_applicable` et
  `refused` ne sont pas comptes comme vraies pannes.
- [x] `failed` et `error` restent visibles, actionnables et non noyes dans
  `ok`.
- [x] Le dashboard recent est coherent avec la taxonomie Lots 2/3 et ne
  deforme pas les no-op agentiques.
- [x] Le content gate reste l'exception explicite d'acces contenu, separee des
  projections content-free ordinaires.

Hors scope:

- [x] Ne pas refondre tout le dashboard.
- [x] Ne pas elargir `dashboard_read_model` sans separation claire de
  responsabilite si le patch devient trop large.
- [x] Ne pas lire ni scanner les logs live.
- [x] Ne pas reset, purger, backfiller ou migrer.

Tests/proofs attendus:

- [x] Tests dashboard avec melange d'evenements legacy et `agentic_v1`.
- [x] Tests prouvant que les no-op/refus normaux ne deviennent pas erreurs.
- [x] Tests prouvant qu'une vraie panne fake/local reste visible.
- [x] Tests content-free sur les projections dashboard hors content gate
  explicite.

Notes Lot 5B:

- Les faits dashboard portent des compteurs `status_schema` content-free via
  les JSON existants, sans migration DB, purge, reset, backfill ni scan live.
- Les agregats `errors` distinguent `error_count`, `failed_count`,
  `attempt_failure_count`, `problem_count` et
  `non_problem_status_count`; les no-op/refus restent visibles mais ne
  fournissent plus la raison de degradation du module `errors`.
- Les vues overview, conversations, turns et inspection exposent la
  distinction legacy vs `agentic_v1` quand les faits materialises la portent.
- Correctif Lot 5B.1: `providers.secondary.<key>.status` conserve maintenant
  la taxonomie V1 observee avec precedence `error`, `failed`, `refused`,
  `not_configured`, `disabled`, `not_selected`, `not_applicable`, `skipped`,
  `ok`; les providers secondaires absents restent `not_applicable` et
  `secondary_status_counts` reflete les statuts reels.
- Le content gate reste separe: `/api/admin/dashboard/turns/<turn_id>/content`
  charge eventuellement du contenu seulement apres action explicite et audit;
  les projections dashboard ordinaires gardent `raw_content_included=false`.
- Aucun dashboard large, frontend, Agenda runtime, Biblio runtime, Lot 5C,
  Lot 6 ou Lot Z n'a ete modifie.

#### Lot 5C - Reliquats logs runtime/store/dashboard et scans schemas

Objectif:

- [x] Traiter les reliquats transverses non couverts par 5A/5B sans
  remplacement mecanique aveugle et sans masquer de panne reelle.

Surfaces visees:

- [x] `err=%s` restants dans stores, dashboard et read-models.
- [x] Logs DB/store/dashboard qui peuvent etre convertis surement vers
  `reason` + `err_class`.
- [x] Schemas de sortie JSONL/admin/dashboard content-free transverses.
- [x] Scans anti-fuite automatises reutilisables pour Lot 6/Z.

Critere de fin:

- [x] Chaque correction de log garde le niveau adapte: les vraies pannes
  restent `WARNING` ou `ERROR`.
- [x] Les chemins corriges n'exposent pas `str(exc)`, cause brute, prompt,
  contenu, payload provider, DAV/XML, ETag, token ou secret.
- [x] Les scans echouent sur champ `raw` non qualifie ou payload brut dans une
  projection V1.
- [x] Les schemas/projections content-free sont coherents avec 5A/5B.

Hors scope:

- [x] Pas de remplacement global automatique de `err=%s`.
- [x] Pas de reset, purge, backfill ou migration destructive.
- [x] Pas de changement plateforme, Caddy, Authelia, secrets ou DB Nextcloud.

Tests/proofs attendus:

- [x] Tests unitaires ou scans cibles pour chaque famille corrigee.
- [x] Scans schemas/projections sans raw non qualifie.
- [x] Preuve que les vraies pannes fake/local restent visibles.
- [x] Preuve que les artefacts produits restent reutilisables pour Lot 6/Z.

Notes Lot 5C:

- Les reliquats `err=%s` corriges sont bornes a `app/observability`:
  `log_store`, `dashboard_read_model`, `dashboard_analytics_storage` et
  `dashboard_materialization_runtime` loggent maintenant `reason=...` +
  `err_class=...` sans `str(exc)`.
- Les niveaux `ERROR` et `WARNING` sont conserves: une vraie panne store,
  read-model ou materialization reste actionnable.
- Le scan unitaire
  `app.tests.unit.logs.test_observability_residual_redaction_lot5c` verifie
  l'absence de `err=%s`, `str(exc)` et `exc_info` dans `app/observability`,
  ainsi que la redaction des sentinelles payload/prompt/message/provider/URL/
  token dans les projections admin et dashboard ordinaires.
- Les occurrences `err=%s`/`str(exc)` encore presentes dans `app/server.py`,
  `app/admin` ou `app/core` ne sont pas remplacees mecaniquement par ce lot:
  elles relevent de surfaces produit/admin plus larges ou de traitements
  applicatifs hors projections observabilite V1 et devront etre rouvertes par
  finding borne si necessaire.
- Aucun content gate, reset, purge, backfill, migration, scan logs live,
  plateforme, Agenda runtime, Biblio runtime, Lot 6 ou Lot Z n'a ete modifie.

### Lot 6 - Smokes transverses observabilite

- [x] Produire un artefact JSONL content-free.
- [x] Prouver un tour normal sans faux `ERROR`.
- [x] Prouver un refus produit attendu sans faux `ERROR`.
- [x] Prouver une vraie panne fake/local visible et actionnable.
- [x] Prouver Agenda/Biblio disabled/not selected/not configured.
- [x] Scanner artefact, docs, diff staged et logs bornes.

Notes Lot 6:

- Artefact de preuve:
  `app/docs/states/baselines/agentic-observability-smokes/frida-v1-agentic-observability-lot6-transverse-smokes-20260621T201840Z.jsonl`.
- Les cas live restent bornes a la sante app, au scan Docker logs depuis
  `2026-06-21T20:18:40Z` et aux scans d'artefact/docs/diff. Aucun log brut
  n'est affiche, conserve ou committe.
- Les cas comportementaux sont honnetement marques `covered_by_tests` quand
  une observation live exigerait une mutation artificielle ou une panne
  provoquee: tour normal, refus/no-op attendus, vraie panne fake/local,
  Agenda disabled/not_configured et Biblio disabled/not_selected.
- Les suites conteneur rejouent les preuves Lot 5A/5B/5C: projections admin
  logs/export Markdown, dashboard ordinaire, content gate comme exception
  explicite et redaction residuelle `err_class`.
- Aucun reset, purge, backfill, migration, scan live DB, plateforme, Caddy,
  Authelia, secret, Agenda runtime produit, Biblio runtime produit, Lot Z ou
  reset post-cloture n'a ete execute.

Notes Lot 6.1:

- Hygiene test-only: `test_dashboard_static_page_route_returns_skeleton` ferme
  explicitement la reponse Flask `/dashboard` apres lecture du squelette.
- Preuve ciblee:
  `PYTHONWARNINGS=error::ResourceWarning ... test_dashboard_static_page_route_returns_skeleton`
  ne laisse plus remonter de `ResourceWarning` sur `dashboard.html`.
- Aucun comportement produit `/dashboard`, observabilite runtime, reset, purge,
  backfill, migration, Lot Z ou plateforme n'est modifie.

### Lot Z - Cloture Observabilite agentique V1

- [x] Relire le contrat Lot 1 et les preuves Lots 2-6.
- [x] Rejouer ou relire les smokes transverses.
- [x] Executer un scan logs applicatifs borne reel.
- [x] Verifier qu'aucun log brut, contenu, prompt, payload, token ou secret
  n'est conserve dans les preuves Lot Z.
- [x] Verifier que les vraies pannes restent visibles.
- [x] Evaluer le gate reset: GO operateur humain explicite/date absent, donc
  reset non execute et bloque par `operator_go_required`.
- [x] Archiver cette TODO avec verdict final conforme.

Notes Lot Z:

- Artefact de cloture:
  `app/docs/states/baselines/agentic-observability-smokes/frida-v1-agentic-observability-lotz-closure-20260622T081658Z.jsonl`.
- Les preuves Lot Z rejouent la suite conteneur ciblee, 267 tests OK, couvrant
  taxonomie V1, logs admin, export Markdown, dashboard, Agenda/Biblio no-op,
  refus produit et vraie panne fake/local.
- Scan Docker logs borne depuis `2026-06-22T08:16:10Z`, tail 5000:
  1 ligne, 74 octets, `forbidden_match_count=0`.
- Scan applicatif JSONL borne dans le conteneur depuis `2026-06-22T08:16:10Z`:
  15 fichiers candidats, 9084 lignes, 2941465 octets,
  `forbidden_match_count=0`.
- Aucun log brut n'a ete affiche, committe ou conserve dans le depot. Le dump
  temporaire Docker sous `/tmp` a ete supprime avant livraison.
- Le reset observabilite destructif n'a pas ete execute. Il exige un futur GO
  operateur humain explicite, date et separe, avec scope exact, backup et
  rollback affiches juste avant execution.

## Statut Agenda issu du Lot 0

Agenda V1 est cloture pragmatiquement par
`app/docs/states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`.
La TODO `app/docs/todo-todo/product/frida-agenda-agent.md` reste dans
`todo-todo` parce qu'elle conserve une roadmap longue avec dettes post-V1 et
n'a pas ete archivee/reclasse apres la cloture. Ce chantier ne rouvre pas
Agenda runtime.

Decision Lot 1: `frida-agenda-agent.md` reste temporairement dans `todo-todo`,
mais les index doivent le presenter comme post-V1 dormant / a rouvrir seulement
sur bug reel, besoin concret ou decision explicite. Un micro-lot docs-only
separe pourra ensuite l'archiver ou le deplacer, sans bloquer l'observabilite
runtime.

## Preuves attendues

- Inventaire code/logs content-free.
- Tests de classification et anti-fuite.
- Smokes representatifs.
- Scans logs bornes sans raw logs.
- Documentation des limites et de l'historique.

## Interdits permanents

- Log brut conserve ou committe.
- Prompt brut.
- Message utilisateur brut.
- Contenu document, note, export, image ou agenda.
- Payload provider ou WebDAV.
- URL DAV, XML, ETag brut.
- Data URL, base64, bytes.
- Token, cookie, app-password, Authorization, secret.
- Faux passage d'une panne reelle en succes silencieux.
