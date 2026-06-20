# Frida V1 - Observabilite globale / logs agentiques - TODO

Statut: TODO actif detaille; Lot 0 audit read-only/docs-only coche; Lot 1+
ouverts.
Roadmap generale: `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`
Audit Lot 0:
`app/docs/states/audits/frida-v1-agentic-observability-lot0-audit-2026-06-20.md`

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

## Decisions ouvertes avant runtime

- Faut-il introduire un statut `refused`, ou encoder les refus produit comme
  `skipped` + reason code?
- Faut-il emettre un evenement Agenda explicite quand le toggle est off, pour
  aligner Agenda sur Biblio?
- Faut-il reclasser `tools_access_denied` / `admin_access_denied` comme
  `WARNING` securite ou `INFO` avec famille `access_denied`?
- Faut-il renommer/projeter le champ JSONL admin `raw` pour eviter toute
  ambiguite content-free?
- Faut-il conserver l'historique `chat_log_events` tel quel ou documenter une
  lecture "historique non requalifie" dans le dashboard?

Ces decisions doivent etre fermees en Lot 1 avant tout patch runtime.

## Regles cibles a stabiliser

Vocabulaire attendu:

- `disabled`: toggle ou feature explicitement off;
- `not_selected`: agent/outillage disponible mais non choisi;
- `not_configured`: prerequis operateur absent;
- `skipped_by_agentic_mode`: skip volontaire du mode agentique;
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

- [ ] Fermer les decisions ouvertes.
- [ ] Definir le vocabulaire status/reason/severity.
- [ ] Definir les familles de logs et leur niveau cible.
- [ ] Definir la politique historique vs fenetre recente.
- [ ] Definir les interdits content-free transversaux.
- [ ] Definir les tests anti-fuite minimaux.
- [ ] Trancher explicitement la correction documentaire Agenda hors runtime:
  soit appliquer un micro-reclassement/archive docs-only Agenda avec mise a
  jour des index, soit documenter pourquoi `frida-agenda-agent.md` reste dans
  `todo-todo` avec statut post-V1 dormant, sans le vendre comme chantier
  runtime actif.
- [ ] Ne modifier aucun runtime dans ce lot si la spec suffit.

### Lot 2 - Harmonisation `chat_turn_logger` / checklist / read-model

- [ ] Corriger les faux `error` pour refus produit attendus.
- [ ] Distinguer `not_applicable`, `disabled`, `not_selected`,
  `not_configured`, `skipped_by_agentic_mode`, `failed` et `error`.
- [ ] Garder les vraies pannes en `ERROR` ou `status=error`.
- [ ] Adapter `turn_observability_checklist` pour ne pas degrader les skips
  normaux.
- [ ] Ajouter tests de classification sur tours chat.
- [ ] Ne pas backfiller l'historique sans decision Lot 1.

### Lot 3 - Agentic Agenda / Biblio observability

- [ ] Aligner Agenda et Biblio sur une grammaire commune.
- [ ] Decider et appliquer l'observation explicite Agenda off si retenue.
- [ ] Distinguer outil non selectionne, agent non configure, mode off, secret
  absent et echec reel.
- [ ] Tester que CalDAV/Catalogue non appeles volontairement ne sont pas des
  erreurs.
- [ ] Ne pas rouvrir Agenda runtime hors observabilite.

### Lot 4 - Durcissement logs runtime content-free

- [ ] Remplacer les logs `err=%s` a risque par `err_class` + reason code quand
  l'information brute peut contenir contenu ou secret.
- [ ] Ne plus logger `conversation_id` client brut invalide.
- [ ] Ne plus logger URL externe brute dans web crawl errors.
- [ ] Conserver les pannes actionnables.
- [ ] Ajouter tests anti-fuite ou probes unitaires ciblés.

### Lot 5 - JSONL admin / dashboard / projections

- [ ] Auditer et corriger le champ ambigu `raw`.
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
- [ ] Archiver cette TODO seulement si le verdict final est conforme.

## Statut Agenda issu du Lot 0

Agenda V1 est cloture pragmatiquement par
`app/docs/states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`.
La TODO `app/docs/todo-todo/product/frida-agenda-agent.md` reste dans
`todo-todo` parce qu'elle conserve une roadmap longue avec dettes post-V1 et
n'a pas ete archivee/reclasse apres la cloture. Ce chantier ne rouvre pas
Agenda runtime.

Correction recommandee: micro-lot docs-only separe pour reclasser ou archiver
la TODO Agenda comme V1 pragmatiquement close / post-V1 dormant, puis mettre a
jour les index qui la decrivent encore comme active.

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
