# Frida V1 - Agentic Observability Contract

Statut: spec source-of-truth livree par Lot 1 docs-only; Lot 2 runtime
`chat_turn_logger` / `log_store` / checklist / read-model livre; correctif
Lot 2.1 writer V1 livre; correctif Lot 2.2 redaction invalid status livre;
Lot 3 Agenda/Biblio no-op observability livre; correctif Lot 3.1 Agenda
fallback status livre; Lot 4 logs runtime content-free livre; Lot 5 decoupe
en 5A/5B/5C avant runtime; Lot 5A admin logs/export Markdown content-free
livre avec correctif Lot 5A.1 value redaction; Lot 5B dashboard statuses
livre.
Date: 2026-06-20
Classement: `app/docs/states/specs/`
TODO produit: `app/docs/todo-todo/product/frida-v1-agentic-observability-todo.md`
Audit source:
`app/docs/states/audits/frida-v1-agentic-observability-lot0-audit-2026-06-20.md`

## 1. Decision

Cette spec ferme les decisions du Lot 0 pour l'observabilite agentique Frida
V1. Elle definit la taxonomie cible, la severite des logs, les no-op
agentiques, la politique historique/recent, la politique `raw` JSONL, le statut
documentaire Agenda et le reset d'observabilite post-cloture.

Lot 1 est docs-only:

- aucun patch Python ou JavaScript;
- aucune migration DB;
- aucun reset;
- aucun backfill;
- aucune suppression de logs;
- aucune modification Docker, Caddy, Authelia ou secret;
- aucune reouverture runtime Agenda.

Le runtime Lot 2 accepte la taxonomie V1 dans
`observability.chat_log_events.status`. L'historique ancien n'est ni backfille,
ni purgé, ni requalifie destructivement; les read-models exposent une projection
content-free permettant de distinguer evenements `agentic_v1` et evenements
legacy.

## 2. Sources

- `AGENTS.md`;
- `app/docs/todo-todo/product/frida-v1-agentic-observability-todo.md`;
- `app/docs/states/audits/frida-v1-agentic-observability-lot0-audit-2026-06-20.md`;
- `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`;
- `app/docs/states/specs/agentic-response-surface-contract.md`;
- `app/docs/states/specs/frida-agenda-agent-contract.md`;
- `app/docs/states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`;
- `app/docs/todo-todo/product/frida-agenda-agent.md`;
- `app/docs/states/specs/frida-biblio-librarian-agent-contract.md`;
- `app/observability/chat_turn_logger.py`;
- `app/observability/turn_observability_checklist.py`;
- `app/observability/log_store.py`;
- `app/observability/dashboard_read_model.py`;
- `app/server.py`;
- `app/core/chat_service.py`;
- `app/agenda/chat_runtime.py`;
- `app/biblio/chat_runtime.py`.

## 3. Portee produit

L'observabilite agentique doit rendre lisible un tour Frida V1 sans recopier de
contenu brut et sans transformer des comportements attendus en erreurs.

Objectif:

- les vraies pannes restent visibles;
- les refus produit attendus deviennent des refus, pas des erreurs;
- les skips/no-op agentiques deviennent explicites;
- les dependances non appelees volontairement sont prouvees comme garde-fous;
- le dashboard distingue dette historique et etat recent;
- les preuves restent content-free.

Hors scope:

- nouveau systeme de logs plateforme;
- refonte complete dashboard;
- reset plateforme;
- reouverture Agenda runtime;
- purge ou backfill historique en Lot 1;
- exposition de contenu utilisateur.

## 4. Taxonomie `status`

Les statuts V1 autorises sont:

- `ok`: operation observee et conforme;
- `skipped`: operation generique ignoree proprement; a utiliser quand aucun
  statut plus precis ci-dessous ne s'applique;
- `disabled`: feature, toggle ou mode explicitement off;
- `not_selected`: agent, outil ou branche disponible mais non choisi pour ce
  tour;
- `not_configured`: prerequis operateur absent ou incomplet;
- `not_applicable`: branche hors sujet pour ce tour;
- `refused`: entree utilisateur, etat produit ou demande refusee proprement;
- `failed`: tentative effectuee et echec recoverable ou degrade, sans
  corruption connue;
- `error`: panne runtime, contrat casse, corruption, divergence ou echec
  principal.

Decision ferme: `refused` est un statut V1 explicite. Un refus produit attendu
ne doit pas etre encode comme faux `error`.

Regles:

- `error` implique une tentative ou une invariance runtime cassee;
- `failed` implique une tentative reelle, mais la panne est bornee ou
  recoverable;
- `refused` implique que le systeme a applique un garde-fou produit;
- `disabled`, `not_selected`, `not_configured` et `not_applicable` ne sont
  jamais des pannes par eux-memes;
- `skipped_by_agentic_mode` est un reason code ou une famille de reason code,
  pas un statut additionnel.

Compatibilite runtime:

- Lot 2 etend `chat_log_events.status` via une contrainte SQL V1 acceptant les
  neuf statuts cibles;
- les lectures exposent `status_v1`, `status_schema_version` et
  `legacy_status` sans backfill historique;
- les nouveaux evenements emis par `chat_turn_logger` portent explicitement
  `status_schema_version=agentic_v1`, y compris quand leur statut stocke reste
  `ok`, `skipped` ou `error`;
- les statuts non-legacy (`disabled`, `not_selected`, `not_configured`,
  `not_applicable`, `refused`, `failed`) sont projetes `agentic_v1`; les
  anciens `ok/error/skipped` sans marqueur explicite restent projetes legacy;
- les evenements historiques `ok/error/skipped` restent lisibles comme legacy,
  sans etre vendus comme requalifies.

Regle writer Lot 2.1:

- un statut invalide fourni au writer d'observabilite ne doit jamais etre
  transforme en `ok`;
- le writer emet `status=error` avec reason/error code
  `agentic_status_invalid` et marqueur content-free `invalid_status_redacted`;
- dans cette branche invalide, aucun `reason_code`, `error_code`, `model`,
  `prompt_kind` ou payload fourni par l'appelant ne peut remplacer ou enrichir
  le payload minimal redacted;
- un vrai `status=error` valide conserve son `error_code` stable normal;
- la valeur brute du statut invalide ne doit pas etre loggee, stockee dans le
  payload ou exposee dans les projections;
- cette regle ne backfille pas l'historique et ne modifie pas la projection
  legacy des anciens evenements non marques.

## 5. Reason codes et familles

Un reason code V1:

- est un token stable ASCII lowercase, par exemple
  `agenda_toggle_disabled`;
- ne contient jamais de contenu utilisateur, prompt, URL brute, chemin, DAV,
  XML, ETag, secret, token, cookie, payload provider ou payload WebDAV;
- doit etre assez specifique pour guider une action ou une interpretation;
- peut etre compte, agrege et expose dans les projections techniques.

Familles minimales:

- `runtime_failure`;
- `product_refusal`;
- `agentic_skip`;
- `dependency_not_called`;
- `access_denied_security`;
- `configuration_absent`;
- `content_free_redaction`;
- `historical_legacy`;
- `reset_cutover`.

## 6. Severite des logs

Mapping cible:

- `DEBUG`: details de developpement non necessaires en production;
- `INFO`: etapes attendues, skips normaux, refus produit traites, no-op
  agentiques, projections content-free;
- `WARNING`: signal securite, degradation secondaire, tentative suspecte,
  compensation non critique, divergence bornee mais visible;
- `ERROR`: panne runtime, corruption, rollback critique, divergence non masquee
  ou echec principal utilisateur.

Decision fermee pour `tools_access_denied` et `admin_access_denied`:

- ils restent des `WARNING` de securite assumee;
- leur famille cible est `access_denied_security`;
- ils ne doivent pas etre melanges aux pannes applicatives runtime;
- ils doivent rester content-free et ne jamais exposer token, cookie, valeur de
  header sensible ou secret.

Un refus 4xx produit normal peut etre `INFO` + `status=refused`. Un refus
securite peut etre `WARNING` + `status=refused` + famille
`access_denied_security`.

## 7. Vraie panne vs refus vs skip agentique

Vraie panne:

- appel attendu effectue puis echec;
- store ou DB applicative indisponible;
- LLM principal echoue alors qu'il est requis;
- rollback critique echoue;
- corruption, incoherence ou divergence non masquee;
- schema de sortie requis casse.

Refus produit:

- payload invalide;
- champ client interdit;
- dossier non `linked`;
- source ou format non supporte;
- ressource absente, deleted ou cross-scope;
- prompt/options invalides;
- source publique non preparee;
- acces admin/tool refuse.

Skip/no-op agentique:

- toggle off;
- mode off;
- branche hors sujet;
- agent non selectionne;
- prerequis absent;
- aucun signal produit pertinent;
- dependance volontairement non appelee.

Un skip/no-op agentique ne doit pas degrader le tour en erreur. Il peut etre
observe en `INFO` avec `dependency_called=false` et reason code stable.

## 8. Agentic no-op et dependances non appelees

Les services non appeles parce que le mode agentique ne les selectionne pas ne
sont jamais des erreurs.

Cas normatifs:

- Agenda off: `status=disabled`, reason `agenda_toggle_off`, aucun CalDAV,
  aucun secret, aucun agent Agenda;
- Biblio off: `status=disabled`, reason `biblio_toggle_disabled`, aucun
  Catalogue;
- Biblio on sans signal bibliographique: `status=not_selected` ou
  `not_applicable`, reason `biblio_no_bibliographic_signal`;
- Web search non demande: `status=not_selected`, reason `web_search_not_requested`;
- Notes/Documents/Exports/Images non selectionnes dans un tour: `status=not_selected`
  ou absence justifiee par un signal de non-selection, jamais `error`;
- provider secondaire non appele: `status=not_selected`,
  `dependency_called=false`;
- CalDAV/Catalogue/WebDAV non appele volontairement: observation content-free
  avec `dependency_called=false` et reason code stable.

Decision fermee Agenda-off: Lot 3 doit aligner Agenda sur Biblio en emettant
une observation content-free quand Agenda est off, sans appeler CalDAV,
OpenRouter, secret ou outil Agenda.

## 9. Historique vs recent

Politique fermee:

- l'historique `observability.chat_log_events` peut contenir des erreurs
  anciennes non requalifiees;
- ces erreurs historiques ne doivent pas etre effacees, purges, requalifiees ou
  backfillees sans lot destructif explicite;
- le dashboard doit distinguer au minimum:
  - fenetre recente;
  - total historique;
  - statut historique non requalifie;
  - cutover observabilite V1;
  - erreurs courantes vs `historical_legacy`;
- les preuves de cloture doivent partir d'une fenetre recente ou d'un
  `cutover_utc` propre;
- toute lecture historique doit porter une limite explicite et un label
  content-free.

Le reset post-cloture defini plus bas n'est pas un backfill: c'est une
operation destructrice controlee a executer uniquement apres validation finale.

## 10. JSONL `raw` et projections techniques

Decision fermee:

- le champ non qualifie `raw` est interdit dans les nouveaux JSONL applicatifs
  et dans les nouvelles projections techniques;
- les evenements historiques ou compatibilites existantes qui portent un champ
  `raw` doivent etre projetes ou renommes par surface avant d'etre presentes
  comme conformes V1: Lot 5A pour admin logs/export Markdown, Lot 5B pour
  dashboard, Lot 5C pour reliquats transverses et scans schemas;
- les nouvelles preuves doivent utiliser des indicateurs explicites:
  - `raw_event_payloads_included=false`;
  - `raw_log_included=false`;
  - `raw_content_included=false`;
  - `raw_prompt_included=false`;
  - `raw_provider_payload_included=false`;
  - `raw_webdav_payload_included=false`;
- un payload technique detaille peut exister seulement sous un nom qualifie,
  avec schema content-free et test anti-fuite.

Interdits dans JSONL/projections techniques:

- log brut;
- message utilisateur brut;
- prompt brut;
- contenu document/note/export/image/agenda;
- bytes, base64, data URL;
- payload provider;
- payload WebDAV;
- chemin DAV, URL DAV, XML, ETag brut;
- token, cookie, app-password, Authorization, secret;
- URL externe brute quand elle peut porter du contenu sensible;
- identifiant client invalide brut.

## 11. Politique content-free transversale

Les surfaces techniques autorisees exposent uniquement:

- booleens;
- compteurs;
- tailles agregees;
- durees;
- statuts;
- reason codes;
- classes d'erreur redacted;
- hashes courts non reversibles;
- UUID deja surface API quand le produit le permet;
- noms de modules/stages allowlistes;
- presence/absence de secret sous forme booleenne redacted.

Les exceptions doivent etre observees par `err_class`, reason code, et hash
court d'une cause redacted quand un diagnostic stable est necessaire. Le texte
brut d'une exception ne doit pas etre logge quand il peut contenir contenu,
prompt, URL, chemin, payload ou secret.

## 12. Statut documentaire Agenda

Decision fermee:

- Agenda V1 est cloture pragmatiquement par
  `app/docs/states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`;
- ce chantier Observabilite ne rouvre pas Agenda runtime;
- `app/docs/todo-todo/product/frida-agenda-agent.md` peut rester
  temporairement dans `todo-todo`, mais il doit etre presente par les index
  comme post-V1 dormant / a rouvrir seulement sur bug reel, besoin concret ou
  decision explicite;
- il ne doit plus etre vendu comme chantier runtime actif;
- avant le Lot 3 Observabilite, les index principaux doivent porter ce libelle
  non ambigu.

Lot 1 applique ce cadrage dans les index. Un micro-lot docs-only separe pourra
ensuite archiver ou deplacer la TODO Agenda, mais ce deplacement n'est pas une
condition pour ouvrir les lots Observabilite runtime.

## 13. Reset observabilite post-cloture

Decision normative:

Apres la cloture du chantier Observabilite agentique V1, l'observabilite
applicative doit repartir d'un etat propre pour Frida 1.0. Ce reset est une
operation destructive controlee. Il est interdit avant validation Lot Z ou lot
dedie explicite.

Lot 1 specifie le reset, mais ne l'execute pas.

La validation de cette spec, le GO general d'un Lot Z ou la cloture du chantier
Observabilite ne valent jamais GO implicite pour le reset destructif. Le reset
exige un GO operateur humain explicite, date, donne juste avant execution et
separe de tout autre GO.

Preconditions obligatoires:

- audit final conforme;
- preuves conservees dans `app/docs/states/`;
- backup DB applicative avant toute suppression, troncature ou reset;
- inventaire exact des tables, read-models, snapshots et fichiers applicatifs
  concernes;
- plan de rollback documente par restauration du backup applicatif;
- affichage prealable du scope exact avant demande de GO operateur:
  - tables applicatives concernees;
  - fichiers applicatifs concernes;
  - comptes avant reset;
  - exclusions produit;
  - chemin du backup;
  - rollback prevu;
  - `cutover_utc` prevu ou calcule;
- GO operateur humain explicite et date, separe du GO general du Lot Z;
- interdiction d'executer le reset si ce GO operateur explicite est absent;
- Celebrimbor peut proposer et executer seulement le scope applicatif valide
  par l'operateur humain;
- aucun reset plateforme n'est autorise.

Donnees produit strictement exclues:

- conversations;
- messages;
- memoire;
- identite;
- workspace folders;
- documents;
- notes;
- exports;
- images;
- agenda runtime settings;
- runtime settings generaux;
- secrets;
- configuration Docker/Caddy/Authelia;
- DB Nextcloud.

Elements a conserver:

- audits;
- specs;
- TODO archivees;
- artefacts JSONL de preuve dans `app/docs/states/`;
- roadmap et index documentaires.

Preuve content-free obligatoire du reset:

- `cutover_utc`;
- compte avant par table/fichier applicatif concerne;
- compte apres;
- hash court du backup DB applicative;
- sante app apres reset;
- scan logs applicatifs borne depuis `cutover_utc`;
- `raw_logs_committed=false`;
- `raw_log_lines_in_artifact=false`;
- `product_data_touched=false`;
- `platform_reset_performed=false`.

Logs plateforme:

- Docker, Caddy, Authelia et system logs sont hors scope Celebrimbor;
- pour ces journaux, la preuve utilise `since_utc` de cutover au lieu d'une
  suppression plateforme;
- aucun fichier de log brut plateforme ne doit etre committe ou recopie.

Validation finale attendue:

- dashboard recent et scans recents refletent un etat Frida 1.0 propre;
- la dette historique pre-refonte ne reapparait pas dans la fenetre post-cutover;
- les vraies pannes restent visibles;
- rollback par restauration backup applicative est documente et testable.

## 14. Lots runtime derives

Lot 2:

- `chat_turn_logger` normalise les statuts V1 et sait emettre un refus produit
  sans `emit_error`;
- `log_store` accepte les neuf statuts V1 en DB applicative et projette
  `status_v1` / `status_schema_version` / `legacy_status`;
- la route chat non-stream classe les 4xx produit en `refused` ou
  `not_applicable`, tandis que 5xx et exceptions restent `error`;
- la checklist ne degrade plus les statuts non-problemes
  `disabled/not_selected/not_configured/not_applicable/refused`;
- les read-models compacts distinguent recent V1, historique legacy et
  statuts non-erreur, sans backfill.

Lot 3:

- Agenda absent/off emet `status=disabled`,
  `reason_code=agenda_toggle_off`, `status_schema_version=agentic_v1`, sans
  executer le runtime Agenda produit, sans CalDAV, secret, LLM Agenda ou
  mutation;
- Biblio off emet `status=disabled`; Biblio on sans signal bibliographique
  emet `status=not_selected`, avec `client.event_count=0` et sans appel
  Catalogue;
- les pannes Agenda/Biblio fake/local restent `error` ou `failed`;
- la checklist/read-model conservent ces no-op comme non-erreurs content-free.

Correctif Lot 3.1:

- Agenda `status=fallback` n'est jamais projete `ok`;
- `agenda_agent_secret_not_configured`, `agenda_agent_model_not_configured` et
  `agenda_agent_provider_not_configured` se projettent `not_configured`;
- `agenda_agent_mode_unsupported` se projette `not_applicable`;
- `agenda_agent_provider_error` se projette `error`;
- les autres fallback de validation JSON, time window, draft ou plan invalide
  se projettent `failed`;
- cette classification reste content-free et ne lit ni secret, ni CalDAV, ni
  OpenRouter en plus des branches deja executees par le runtime.

Lot 4:

- familles durcies:
  - `tools.web_search` `crawl_error`: plus d'URL brute ni `str(exc)`;
    conserver `reason=crawl_exception`, filtre, scheme, hash court host,
    presence query/fragment, longueur et `err_class`;
  - `tools.web_search` `reformulate_error`: plus de `str(exc)`, conserver
    `reason=web_reformulation_exception` et `err_class`;
  - `core.chat_session_flow` `conv_id_invalid`: plus de
    `conversation_id` client brut invalide, conserver presence, longueur et
    hash court;
  - `observability.chat_turn_logger` `chat_turn_log_emit_failed`: plus de
    `str(exc)`, conserver `reason=chat_log_event_insert_exception` et
    `err_class`;
  - `observability.log_store` `chat_log_event_insert_failed`: plus de
    `str(exc)`, conserver `reason=chat_log_event_insert_failed` et
    `err_class`;
- ces logs gardent leur niveau `WARNING` ou `ERROR`: une vraie panne reste
  visible et actionnable;
- les autres `err=%s` des stores DB, dashboard/read-models ou surfaces
  d'export restent hors Lot 4 si leur correction demande une projection plus
  large; Lot 5/6 devront les traiter sans survendre la portee Lot 4;
- aucun reset, purge, backfill, migration ni suppression de logs n'est execute
  en Lot 4.

Lot 5:

- le Lot 5 complet n'est pas ouvert en bloc;
- l'ordre cible est Lot 5A puis Lot 5B puis Lot 5C, sauf meilleur plan
  explicitement justifie avant patch;
- aucun sous-lot Lot 5 ne doit reset, purger, backfiller, migrer ou masquer une
  vraie panne.

Lot 5A - Admin logs et export Markdown content-free:

- objectif: rendre les surfaces admin logs et export Markdown conformes V1
  content-free tout en conservant une compat UI seulement si elle est explicite
  et projetee;
- surfaces visees:
  - `/api/admin/logs/chat`;
  - `/api/admin/logs/chat/metadata`;
  - `/api/admin/logs/chat/turns`;
  - `/api/admin/logs/chat/metrics` si des payloads historiques y sont exposes;
  - `/api/admin/logs/chat/export.md`;
  - `observability.log_store.read_chat_log_events`;
  - `observability.log_markdown_export`;
- criteres de fin:
  - payloads historiques projetes ou allowlistes;
  - aucun prompt, message utilisateur, payload provider, DAV/XML, ETag brut,
    secret, token, cookie, header sensible ou contenu brut;
  - aucun champ `raw` non qualifie;
  - compat UI documentee si un champ historique comme `payload` reste present;
  - indicateurs explicites tels que `raw_event_payloads_included=false`,
    `raw_content_included=false`, `raw_prompt_included=false`,
    `raw_provider_payload_included=false` et
    `raw_webdav_payload_included=false`;
  - export Markdown resume/content-free, sans payload brut;
- hors scope: dashboard large, Agenda, Biblio, Documents, Notes, Exports,
  Images, reset, purge, backfill et migration;
- tests/preuves attendus: sentinelles anti-fuite sur admin logs et export
  Markdown, compat UI si conservee, scan de diff contre `raw` non qualifie.

Decision livree Lot 5A:

- la projection admin logs V1 est portee par
  `observability.admin_log_projection`, module dedie de projection content-free;
- `/api/admin/logs/chat` demande `payload_projection=admin` a
  `observability.log_store.read_chat_log_events` et applique une projection
  defensive avant JSON;
- le champ historique `payload` reste present pour compat UI, mais il ne
  contient plus le payload DB brut sur la route admin: seules les valeurs
  allowlistees et redacted sont exposees;
- correctif Lot 5A.1: l'allowlist admin valide aussi les valeurs; une valeur
  URL-like, path/target-like, token/Bearer-like, header-like, credential-like,
  DAV/XML-like ou email-like est redacted meme sous une cle allowlistee; le
  champ `model` garde une validation dediee pour les identifiants
  content-free de type `provider/model`;
- les items et listings portent des indicateurs explicites:
  `raw_event_payloads_included=false`, `raw_content_included=false`,
  `raw_prompt_included=false`, `raw_provider_payload_included=false`,
  `raw_webdav_payload_included=false` et
  `raw_error_message_included=false`;
- `log_markdown_export` utilise la meme projection et ajoute des metadonnees
  Markdown `content_free=true`, `payload_projection_schema` et flags raw
  qualifies a `false`;
- `/api/admin/logs/chat/metadata`, `/api/admin/logs/chat/turns` et
  `/api/admin/logs/chat/metrics` restent content-free par construction:
  metadonnees, pipeline compact et snapshot agrege; les lectures internes qui
  calculent ces read-models ne valent pas exposition admin de payload brut;
- aucune requalification, purge, migration, suppression ou backfill historique
  n'est effectue: les evenements legacy restent legacy et les evenements
  `agentic_v1` restent lisibles;
- les tests sentinelles Lot 5A prouvent l'absence de prompt, message,
  contenu, payload provider, Authorization/Bearer/token, DAV/XML/ETag,
  exception brute et champ `raw` non qualifie dans les surfaces livrees;
- le dashboard reste hors scope Lot 5A et doit etre traite par Lot 5B.

Lot 5B - Dashboard historique/recent et statuts agentiques:

- objectif: harmoniser le dashboard avec la taxonomie V1 sans compter
  no-op/refus normaux comme vraies pannes et sans masquer `failed`/`error`;
- surfaces visees:
  - `/api/admin/dashboard/*`;
  - `observability.dashboard_read_model`;
  - `observability.dashboard_analytics_projection`;
  - `observability.dashboard_materialization_runtime`;
  - `observability.dashboard_content_gate` uniquement comme exception explicite,
    bornee, auditee et documentee;
- criteres de fin:
  - legacy et `agentic_v1` distinguables dans les vues recentes/historiques;
  - `disabled`, `not_selected`, `not_configured`, `not_applicable` et
    `refused` non comptes comme vraies pannes;
  - `failed` et `error` visibles, actionnables et non noyes dans `ok`;
  - dashboard recent coherent avec les Lots 2/3;
  - content gate separe des projections content-free ordinaires;
- hors scope: refonte complete dashboard, scan logs live, reset, purge,
  backfill et migration;
- tests/preuves attendus: dashboard avec evenements legacy + `agentic_v1`,
  no-op/refus non-erreur, vraie panne fake/local visible, projections
  content-free hors content gate explicite.

Decision livree Lot 5B:

- les faits dashboard conservent la distinction legacy vs `agentic_v1` dans
  des compteurs `status_schema` content-free portes par les JSON existants,
  sans migration DB, backfill, purge, reset ni scan logs live;
- les agregats `errors` distinguent les vraies pannes
  `error_count`/`failed_count` via `attempt_failure_count` et `problem_count`,
  tout en exposant les no-op/refus normaux via `non_problem_status_count` et
  les compteurs par statut;
- `disabled`, `not_selected`, `not_configured`, `not_applicable`, `refused`
  et `skipped` restent visibles dans les compteurs dashboard, mais ne
  fournissent pas la raison de degradation du module `errors`;
- `failed` et `error` restent visibles dans les facts, buckets, overview,
  conversations et inspection traduite, avec reason codes compacts separes
  dans `problem_reason_code_counts`;
- Agenda off et Biblio non selectionnee restent des no-op non-erreur dans les
  vues dashboard; une panne fake/local `failed` ou `error` reste actionnable;
- le content gate reste une exception explicite et bornee:
  `/api/admin/dashboard/turns/<turn_id>/content` peut charger du contenu apres
  action volontaire et audit, tandis que les projections ordinaires restent
  `raw_content_included=false`;
- aucun frontend dashboard large, Lot 5C, Lot 6, Lot Z, reset, purge,
  backfill, migration, scan live, Agenda runtime ou Biblio runtime n'est inclus
  dans cette decision.

Lot 5C - Reliquats logs runtime/store/dashboard et scans schemas:

- objectif: traiter les reliquats non couverts par 5A/5B, notamment les logs
  store/dashboard et scans transverses, sans remplacement mecanique aveugle;
- surfaces visees:
  - `err=%s` restants dans stores, dashboard et read-models;
  - logs DB/store/dashboard convertibles surement vers `reason` + `err_class`;
  - schemas de sortie JSONL/admin/dashboard content-free transverses;
  - scans anti-fuite automatises reutilisables pour Lot 6/Z;
- criteres de fin:
  - vraies pannes gardees en `WARNING` ou `ERROR`;
  - pas de `str(exc)`, cause brute, prompt, contenu, payload provider,
    DAV/XML, ETag, token ou secret sur les chemins corriges;
  - scans echouant sur champ `raw` non qualifie ou payload brut dans une
    projection V1;
  - schemas/projections coherents avec 5A/5B;
- hors scope: remplacement global automatique de `err=%s`, reset, purge,
  backfill, migration destructive, plateforme, Caddy, Authelia, secrets et DB
  Nextcloud;
- tests/preuves attendus: tests ou scans cibles par famille corrigee, scans
  schemas/projections, preuve vraie panne fake/local visible, artefacts
  reutilisables pour Lot 6/Z.

Lot 6:

- smokes transverses content-free;
- preuve refus produit sans faux `ERROR`;
- preuve vraie panne fake/local visible;
- scan artefact/docs/diff/logs bornes.

Lot Z:

- relire contrat et preuves;
- executer scan logs borne reel;
- cloturer ou documenter les limites;
- executer le reset seulement dans le cadre valide par cette spec, ou ouvrir un
  lot reset dedie explicite si Lot Z reste proof-only.

## 15. Tests et preuves attendus

Tests minimaux futurs:

- `refused` accepte ou projete sans devenir `error`;
- `disabled`, `not_selected`, `not_configured`, `not_applicable` ne degradent
  pas le tour;
- vraie panne fake/local reste `error`;
- `tools_access_denied` / `admin_access_denied` restent `WARNING` securite;
- Agenda off emet une observation content-free et n'appelle aucune dependance;
- Biblio off / no signal n'appelle pas Catalogue;
- secondary provider not selected ne devient pas missing;
- JSONL nouveaux sans champ `raw` non qualifie;
- scans anti-fuite sur prompt, contenu, payload, DAV/XML, ETag et secret;
- dashboard recent distingue historique non requalifie.

Preuves Lot Z:

- artefact JSONL content-free;
- scan logs applicatifs borne reel;
- compte recent vs historique;
- absence de log brut conserve;
- cutover/reset selon section 13 quand execute.

## 16. Interdits permanents

- Masquer une vraie panne en succes;
- transformer un refus produit en `error`;
- traiter un no-op agentique comme panne;
- backfill historique implicite;
- reset destructif sans backup;
- reset plateforme depuis ce chantier;
- log brut committe;
- prompt brut;
- contenu utilisateur;
- payload provider ou WebDAV;
- URL DAV, chemin DAV, XML, ETag brut;
- data URL, base64, bytes;
- token, cookie, app-password, Authorization ou secret.
