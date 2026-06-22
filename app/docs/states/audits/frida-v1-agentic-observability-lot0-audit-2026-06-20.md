# Frida V1 - Agentic Observability Lot 0 audit

Date: 2026-06-20
Classement: `app/docs/states/audits/`
Portee: audit read-only/docs-only des logs, read-models et preuves
observabilite FridaDev en mode agentique.

## Verdict de plan

Existe-t-il un meilleur plan ?

Non. Le bon premier pas est un audit content-free et sans patch runtime. Le
chantier doit d'abord separer les vraies pannes des refus produit et des skips
agentiques attendus, puis seulement ensuite corriger les statuts, niveaux et
surfaces dashboard.

Lot 0 ne modifie aucun code, aucune route, aucune configuration Docker, aucun
secret et aucun runtime.

## Sources relues

Docs de cadrage:

- `AGENTS.md`;
- `app/docs/todo-todo/product/frida-v1-agentic-observability-todo.md`;
- `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`;
- `app/docs/states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`;
- `app/docs/todo-todo/product/frida-agenda-agent.md`;
- `app/docs/states/specs/frida-agenda-agent-contract.md`;
- `README.md`;
- `app/docs/README.md`.

Surfaces code relues ou inventoriees:

- `app/server.py`;
- `app/core/chat_service.py`;
- `app/core/chat_llm_flow.py`;
- `app/core/chat_session_flow.py`;
- `app/core/conversations_store.py`;
- `app/core/conversations_maintenance.py`;
- `app/core/workspace_folders_store.py`;
- `app/core/workspace_folder_nextcloud_runtime.py`;
- `app/core/workspace_folder_nextcloud_reconcile.py`;
- `app/tools/web_search.py`;
- `app/agenda/chat_runtime.py`;
- `app/agenda/observability.py`;
- `app/agenda/observability_read_model.py`;
- `app/biblio/chat_runtime.py`;
- `app/biblio/observability.py`;
- `app/observability/chat_turn_logger.py`;
- `app/observability/log_store.py`;
- `app/observability/turn_pipeline_read_model.py`;
- `app/observability/turn_observability_checklist.py`;
- modules Documents, Notes, Exports, Generated Images et tests via inventaire
  `logger.*`, `reason_code` et `observability`.

## Scans executes

Les scans n'ont conserve ni recopie aucune ligne de log brute.

### Docker logs bornes

Commande source:

```text
docker logs platform-fridadev --since 24h --tail 20000
```

Resultat content-free:

- lignes scannees: 187;
- octets scannes: 13 849;
- niveaux detectes: `INFO=181`;
- `ERROR=0`, `WARNING=0` dans la fenetre Docker bornee;
- categories interdites detectees: 0.

Les logs Docker etaient majoritairement sur stderr Docker, ce qui est normal
pour le flux logging de l'application et ne signifie pas en soi un niveau
`ERROR`.

### Fichiers JSONL applicatifs disponibles

Inventaire conteneur:

- dossier: `/app/logs`;
- fichiers JSONL: 15;
- lignes JSONL scannees: 9 009;
- lignes JSON invalides: 0;
- octets scannes: 2 916 030;
- niveaux: `INFO=9002`, `WARN=7`, `ERROR=0`;
- evenements `WARN`: `tools_access_denied=4`, `admin_access_denied=3`;
- categories interdites detectees: 0.

Observation: ces `WARN` sont des refus d'acces securite/admin/outils. Ils
peuvent rester visibles comme signaux de securite, mais le Lot 1 doit definir
s'ils relevent d'un niveau `WARNING`, d'un niveau `INFO/security`, ou d'une
famille dediee `access_denied`.

### Read-model `observability.chat_log_events`

Synthese DB applicative, sans payload brut:

- evenements totaux: 171 617;
- `ok=118641`;
- `skipped=41928`;
- `error=11048`.

Top familles historiques `error`:

- `validation_agent`: 2 482;
- `memory_retrieve`: 2 217;
- `embedding`: 2 217;
- stage generique `error`: 1 991;
- `turn_end`: 1 049;
- `llm_call`: 867;
- `stimmung_agent`: 118;
- `adobe_docs`: 42;
- `persist_response`: 36;
- `adobe_prompt_lane`: 14;
- `memory_chain_snapshot`: 12;
- `identity_periodic_agent`: 3.

Sur les 500 evenements recents lus via le read-model:

- `ok=460`;
- `skipped=40`;
- `error=0`.

Interpretation: la sante runtime recente ne montre pas d'erreur dans
l'echantillon, mais l'historique contient beaucoup de statuts `error`. Lot 1
doit distinguer historique, vraie panne et faux signal avant toute correction
ou backfill.

### Preuves JSONL recentes utiles

Fichiers scannes:

- Agenda observabilite Lot 8B;
- Agenda cloture ciblee;
- Documents Lot Z;
- Exports Lot Z;
- Generated Images Lot Z;
- Nextcloud folders Lot Z;
- Notes Lot Z.

Resultat:

- fichiers presents: 7/7;
- JSON invalide: 0;
- categories interdites detectees: 0.

## Inventaire code logging

Commande source:

```text
grep -RIn "logger\\.\\|logging\\.\\|app.logger\\|print(\\|traceback\\|exc_info\\|reason_code\\|observability" app/core app/server.py app/observability app/tools app/web app/tests
```

Resultat:

- lignes inventoriees: 5 518;
- repartition: `tests=3033`, `core=1573`, `observability=380`,
  `tools=325`, `web=131`, `server.py=76`;
- appels logging explicites inventoriees separement: 134;
- appels explicites: `logger.warning=49`, `logger.info=23`,
  `logger.error=16`, `print=10`, `traceback=4`.

Top fichiers d'appels logging explicites:

- `app/core/conversations_store.py`: 20;
- `app/server.py`: 12;
- `app/core/chat_llm_flow.py`: 10;
- `app/core/workspace_folders_store.py`: 9;
- `app/core/conversations_maintenance.py`: 9;
- `app/observability/identity_observability.py`: 5;
- `app/tools/web_search.py`: 5.

## Familles de logs et classification

### Vrais defauts runtime

Ces familles doivent rester visibles, souvent `ERROR` ou `WARNING` selon
impact, avec cause redacted et action operateur claire:

- init runtime settings ou bootstrap DB echoue;
- persistence conversation/catalog/messages echoue;
- stream LLM sans terminal, terminal multiple ou erreur upstream;
- ecriture traces/memory/identity apres reponse echoue;
- `memory_retrieve`, `embedding`, `validation_agent`, `stimmung_agent` en erreur
  quand le service etait attendu;
- rollback/compensation Nextcloud echoue;
- store local indisponible pendant create/list/lookup/read;
- provider externe appele puis KO.

Regle cible: niveau `ERROR` si l'operation principale utilisateur ou une
compensation critique echoue; niveau `WARNING` si une capacite secondaire
echoue mais le tour utilisateur reste coherent; toujours reason code
content-free.

### Refus produit attendus

Ces cas ne doivent pas se presenter comme panne runtime:

- dossier non `linked`;
- ressource absente/deleted/cross-folder;
- payload client invalide ou champ interdit;
- source/format/taille non supporte;
- outil admin ou tools refuse par controle d'acces;
- produit Adobe absent/invalide;
- prompt ou options Generated Images invalides;
- source publique non preparee dans Exports.

Regle cible: `status=skipped`, `status=refused` si un vocabulaire futur
l'introduit, ou reponse HTTP 4xx avec reason code; eviter `stage status=error`
sauf si la route/transport a réellement casse.

### Skips/no-op attendus en mode agentique

Ces cas sont des non-actions normales et doivent etre distingués:

- `web_search` non demande;
- `summaries` sans resume actif;
- Biblio toggle off;
- Biblio toggle on mais aucun signal bibliographique;
- Agenda toggle off;
- Agenda mode off;
- Agenda secret non configure;
- Agenda plan non executable ou non selectionne;
- secondary providers non appeles car non attendus;
- Identity write sans changement;
- branche hermeneutique non applicable selon mode.

Regle cible: `skipped_by_agentic_mode`, `not_selected`, `disabled`,
`not_configured`, `not_applicable` ou `no_data`; pas de `error`, pas de
`failed`.

### Dependances volontairement non appelees

Ce sont des preuves de garde-fou, pas des lacunes:

- pas de CalDAV si Agenda off, mode off, secret absent ou plan non executable;
- pas d'OpenRouter Agenda si mode off ou secret absent;
- pas de Nextcloud/WebDAV pour list/lookup metadata-only;
- pas de provider image si le dossier est refuse avant generation;
- pas de Biblio Catalogue si toggle off ou signal absent.

Regle cible: champ booleen explicite `*_access=false`,
`dependency_called=false`, reason code stable.

### Signal utile mais mauvais niveau potentiel

Familles a revoir en Lot 1/2:

- les refus 4xx emis comme `chat_turn_logger.emit_error(...)` avec
  `error_code=not_applicable` dans `server.py`;
- `adobe_docs` historiquement en `error` pour `adobe_product_required` ou
  `adobe_product_invalid`, qui sont des refus produit;
- `tools_access_denied` et `admin_access_denied` en `WARN`: utile securite,
  mais doit etre explicitement classe `access_denied`, pas melange avec panne
  runtime;
- `turn_observability_checklist._stage_health_item()` degrade toute presence de
  `status=error`, ce qui est juste pour les vraies pannes mais amplifie les
  refus produit mal classes.

### Bruit/stale historique

L'historique DB porte des erreurs anciennes (`upstream_error`, `invalid_json`,
`timeout`, `stream_finalize_error`, etc.). Elles ne doivent pas etre effacees
sans decision explicite, mais les dashboards Lot 1 doivent afficher:

- fenetre recente;
- total historique;
- statut de cloture ou d'anciennete;
- distinction `historical_error` vs `current_error`.

### Risques content-free

Surfaces a durcir:

- `chat_session_flow`: log `conv_id_invalid raw=%s` peut recopier un id client
  brut;
- `tools/web_search.py`: `crawl_error url=%s` peut recopier une URL externe
  brute;
- plusieurs logs `err=%s` peuvent contenir une cause brute; preferer
  `err_class`, reason code et hash court si necessaire;
- les JSONL admin contiennent une cle nommee `raw` dans certains evenements
  techniques. Le scan n'a pas montre de fuite, mais le nom est ambigu pour un
  contrat content-free et doit etre renomme ou projete.

## Coherence agentique

Constats:

- Biblio emet un evenement stage `biblio` meme quand le toggle est off, avec
  `status=skipped` et reason `biblio_toggle_disabled`.
- Agenda n'emet un evenement stage `agenda` que si `agenda_enabled` est vrai.
  L'absence d'evenement Agenda signifie donc souvent "toggle off", mais peut
  aussi ressembler a "non observe" pour un dashboard.
- Les secondary providers ont deja une notion `not_called` dans la checklist
  quand ils ne sont pas attendus.
- Les erreurs historiques sont visibles dans `chat_log_events`, mais
  l'echantillon recent ne montre pas d'erreur.

Regle cible de vocabulaire:

- `disabled`: feature/toggle explicitement off;
- `not_selected`: agent ou outil disponible mais non choisi pour ce tour;
- `not_configured`: prerequis operateur absent;
- `skipped_by_agentic_mode`: skip volontaire du mode agentique;
- `not_applicable`: branche hors sujet pour le tour;
- `refused`: entree utilisateur ou etat produit refuse proprement;
- `failed`: tentative effectuee et echec recoverable/degrade;
- `error`: panne runtime ou contrat casse.

Regle cible de severite:

- `DEBUG`: details de developpement non necessaires en prod;
- `INFO`: etapes attendues, skips normaux, refus produit traites;
- `WARNING`: degradation secondaire, tentative suspecte, compensation non
  critique, access denied si choisi comme signal securite;
- `ERROR`: panne runtime, echec principal, corruption, rollback critique,
  divergence non masquee.

## Agenda

Statut determine:

- Agenda V1 est cloture pragmatiquement par
  `app/docs/states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`.
- Le runtime Agenda ne doit pas etre rouvert par ce chantier.
- `app/docs/todo-todo/product/frida-agenda-agent.md` reste dans `todo-todo`
  parce que la roadmap longue conserve des cases post-V1 ouvertes et n'a pas
  ete archivee/reclasse apres la cloture pragmatique.
- Les index (`AGENTS.md`, `README.md`, `app/docs/README.md`) continuent donc de
  parler d'une TODO Agenda active, ce qui est ambigu.

Correction documentaire recommandee, hors Lot 0:

- ouvrir un micro-lot docs-only Agenda;
- soit archiver la TODO Agenda comme V1 pragmatiquement close avec dettes
  post-V1 explicites;
- soit la reclasser comme "post-V1 dormant / a rouvrir seulement sur bug ou
  besoin concret";
- mettre a jour `AGENTS.md`, `README.md`, `app/docs/README.md` et la roadmap
  pour ne pas vendre Agenda comme chantier runtime actif.

## No-go avant Lot 1

- Ne pas patcher les logs un par un sans taxonomie.
- Ne pas transformer des vraies pannes en `INFO`.
- Ne pas effacer ou backfiller l'historique DB sans decision explicite.
- Ne pas recopier de logs bruts dans les docs.
- Ne pas rouvrir Agenda runtime.
- Ne pas corriger Caddy/Docker/Authelia dans ce chantier applicatif.

## Inputs pour Lot 1

Lot 1 doit produire un contrat source-of-truth d'observabilite agentique:

- vocabulaire status/reason code/severity;
- mapping `DEBUG/INFO/WARNING/ERROR`;
- distinction refus produit vs panne runtime;
- regles `disabled`, `not_selected`, `not_configured`,
  `skipped_by_agentic_mode`, `not_applicable`, `refused`, `failed`, `error`;
- politique de fenetre recente vs historique;
- regles content-free pour exception, URL, ids, payloads, ETag, DAV/XML,
  prompt, contenu et secrets;
- decision sur le champ `raw` des JSONL admin;
- decision sur l'observation explicite Agenda off;
- test anti-fuite transversal minimal.

## Conclusion

Le runtime recent n'affiche pas d'erreur Docker ou `chat_log_events` recente
dans les echantillons bornes, mais l'historique et le code montrent une dette
de vocabulaire: certains refus produit et skips agentiques peuvent etre lus
comme des erreurs, tandis que certaines vraies pannes doivent rester fortes.

Lot 0 est termine si cette audit est conserve, la TODO Observabilite est
detaillee, et aucun log brut/temporaire n'est conserve.
