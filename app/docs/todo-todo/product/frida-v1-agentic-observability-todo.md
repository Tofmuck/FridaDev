# Frida V1 - Observabilite globale / logs agentiques - TODO

Statut: TODO actif detaille; Lots 0 et 1 docs-only coches; Lot 2 runtime
borne livre avec correctifs Lot 2.1 / 2.2 writer; Lot 3 Agenda/Biblio
no-op observability livre avec correctif Lot 3.1 Agenda fallback; Lot 4 logs
runtime content-free livre; Lot 5+ ouverts.
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

- [ ] Interdire les nouveaux champs `raw` non qualifies.
- [ ] Projeter ou renommer les compatibilites historiques `raw` exposees aux
  surfaces V1.
- [ ] Stabiliser les schemas JSONL admin content-free.
- [ ] Harmoniser dashboard: historique vs recent, erreurs vraies vs refus.
- [ ] Verifier les exports Markdown/logs admin sans contenu brut.
- [ ] Ajouter scans anti-fuite automatises.

### Lot 6 - Smokes transverses observabilite

- [ ] Produire un artefact JSONL content-free.
- [ ] Prouver un tour normal sans faux `ERROR`.
- [ ] Prouver un refus produit attendu sans faux `ERROR`.
- [ ] Prouver une vraie panne fake/local visible et actionnable.
- [ ] Prouver Agenda/Biblio disabled/not selected/not configured.
- [ ] Scanner artefact, docs, diff staged et logs bornes.

### Lot Z - Cloture Observabilite agentique V1

- [ ] Relire le contrat Lot 1 et les preuves Lots 2-6.
- [ ] Rejouer ou relire les smokes transverses.
- [ ] Executer un scan logs applicatifs borne reel.
- [ ] Verifier qu'aucun log brut, contenu, prompt, payload, token ou secret
  n'est conserve.
- [ ] Verifier que les vraies pannes restent visibles.
- [ ] Executer le reset observabilite post-cloture seulement avec backup,
  inventaire, exclusions produit, preuves content-free, rollback et GO operateur
  humain explicite/date, separe du GO general Lot Z; afficher le scope exact
  avant demande de GO, sinon ne pas executer le reset.
- [ ] Archiver cette TODO seulement si le verdict final est conforme.

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
