# Frida V1 - Agentic Observability Contract

Statut: spec source-of-truth livree par Lot 1 docs-only; Lot 2 runtime
`chat_turn_logger` / `log_store` / checklist / read-model livre; correctif
Lot 2.1 writer V1 livre; correctif Lot 2.2 redaction invalid status livre;
Lot 3 Agenda/Biblio no-op observability livre; correctif Lot 3.1 Agenda
fallback status livre; Lot 4 logs runtime content-free livre; Lot 5 decoupe
en 5A/5B/5C avant runtime; Lot 5A admin logs/export Markdown content-free
livre avec correctif Lot 5A.1 value redaction; Lot 5B dashboard statuses
livre avec correctif Lot 5B.1 providers secondaires; Lot 5C reliquats/scans
residuels livre; Lot 6 smokes transverses content-free livre; correctif Lot
6.1 hygiene test dashboard livre; Lot Z preuve/cloture livre sans reset
destructif.
Date: 2026-06-20
Classement: `app/docs/states/specs/`
TODO produit archivee:
`app/docs/todo-done/product/frida-v1-agentic-observability-todo.md`
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
- `app/docs/todo-done/product/frida-v1-agentic-observability-todo.md`;
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
- `app/core/chat_agent_lane_orchestration.py`;
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

### Decisions operateur - logs serveur prives

Decision explicite du 16 juillet 2026:

- FridaDev est actuellement mono-utilisateur et Tof en est l'unique operateur;
- la visibilite du contenu identity/memory deja journalise dans les logs prives
  du serveur OVH est intentionnelle et preservee comme outil d'inspection de la
  construction et de la transformation de l'identite et de la memoire;
- cette exception ne s'applique pas aux JSONL, projections admin, exports,
  telemetrie externe ni retours d'agent, qui restent content-free selon leurs
  contrats;
- elle n'autorise aucun nouveau log, aucune augmentation de contenu, collecte,
  telemetrie, export ou surface produit;
- les secrets restent interdits et les textes d'exceptions brutes restent une
  famille distincte a classifier; cette decision ne les autorise pas
  globalement.

Cette decision requalifie la norme applicable aux seuls logs serveur prives
identity/memory existants. Elle ne modifie pas les contrats des surfaces
techniques partagees ou exportees.

Decision complementaire du 22 juillet 2026, apres inventaire Lot 10F:

- les logs standards Python exclusivement emis vers les sorties serveur
  privees peuvent conserver un texte d'exception existant, famille par
  famille, si aucun chemin de projection n'existe, aucun secret plausible ne
  peut atteindre ce texte et le diagnostic serait degrade par la seule classe;
- le contexte mono-utilisateur et mono-operateur ne vaut jamais autorisation de
  journaliser un token, cookie, mot de passe, cle, DSN complet, header
  d'autorisation ou credential;
- aucun nouveau log de contenu, aucune nouvelle collecte et aucune nouvelle
  surface ne sont autorises par cette decision;
- HTTP, admin, JSONL, exports, telemetrie et retours d'agent restent des
  frontieres content-free. Une redaction locale a ces frontieres ne commande
  pas la suppression d'un diagnostic prive source conforme.

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

## 11. Frontieres content-free et matrice des exceptions

La politique ci-dessous reste transversale aux surfaces partagees: HTTP,
JSONL, projections admin, exports, telemetrie externe et retours d'agent. Les
logs standards Python exclusivement emis vers les sorties serveur privees ne
sont pas une surface partagee par simple usage d'un logger. Ils suivent la
decision bornee et par famille de la section 3. Les writers JSONL/admin restent
distincts de `logging.basicConfig` et ne consomment pas ces sorties standards.

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
brut d'une exception ne doit jamais franchir une surface partagee. Il ne peut
rester dans un log serveur prive que lorsque la matrice ci-dessous classe
explicitement sa famille `PRIVATE_OPERATOR_LOG_ACCEPTED`. Les secrets sont
interdits dans tous les cas.

### Matrice Lot 10F - revalidation du 22 juillet 2026

Le scan a ete reconstruit sur la base
`bdffc8e50125fe6d1a91105f3758dad6346d3c0b`, sans reutiliser le nombre
historique. Apres correction, il compte 132 appels de logger situes dans un
handler et referencant l'exception capturee: 82 rendent encore son texte, 48
n'exposent que sa classe et 2 un identifiant de prompt stable. Aucun appel
`logger.exception`, `exc_info=True`, `traceback`, `format_exc` ou `print_exc`
n'est present dans le code runtime. Les 82 rendus textuels sont reconciles
ci-dessous par fichier et par sink; les branches transport a secret sont
traitees separement meme lorsqu'elles rejoignaient auparavant un de ces sinks.

| famille | fichier/appelant | destination reelle | donnees plausibles dans l'exception | statut | justification |
| --- | --- | --- | --- | --- | --- |
| bootstrap runtime (3) | `app/server.py`, initialisation, bootstrap et backfill settings | log standard serveur prive | classe/reason DB ou crypto, noms de champs techniques | `PRIVATE_OPERATOR_LOG_ACCEPTED` | Aucun writer admin/JSONL ne lit le logger standard; des DSN synthetiques ont confirme que la valeur credential n'est pas rendue par les erreurs psycopg couvertes. |
| init document actif (1) | `app/core/active_conversation_documents.py::init_db` | log standard serveur prive | diagnostic SQL/DB | `PRIVATE_OPERATOR_LOG_ACCEPTED` | Diagnostic de demarrage local, sans projection. |
| lecture/decision documents du tour (3) | `app/core/chat_document_prompt_reads.py`: `_active_documents_for_prompt`, `_workspace_files_for_prompt`; `app/core/chat_service.py`: `_record_active_document_prompt_decisions` | log standard serveur prive; le resultat applicatif ne garde que reason code/classe | diagnostic DB du reader/writer | `PRIVATE_OPERATOR_LOG_ACCEPTED` | Le texte reste au sink prive; les objets `ActiveDocumentsPromptRead` sont bornes. |
| conversations (12) | `conversations_maintenance.py`: `init_catalog_db`, `init_messages_db`, `compute_storage_counts`; `conversations_store.py`: `upsert_conversation_messages`, `conversation_message_row_count`, `load_messages_from_db`, `upsert_conversation_catalog`, `get_conversation_summary`, `list_conversations`, `rename_conversation`, `set_conversation_workspace_folder`, `soft_delete_conversation` | log standard serveur prive | DB, migration legacy, chemin interne ou identifiant | `PRIVATE_OPERATOR_LOG_ACCEPTED` | Les evenements admin voisins utilisent classe/reason; aucune projection du texte standard. |
| dossiers workspace (6) | `workspace_folders_store.py`: `list_workspace_folders`, `get_workspace_folder`, `next_sort_order`, `create_workspace_folder`, `update_workspace_folder`, `soft_delete_workspace_folder` | log standard serveur prive | diagnostic DB/stockage | `PRIVATE_OPERATOR_LOG_ACCEPTED` | Store local uniquement; les services HTTP/Nextcloud projettent type et reason codes. |
| facade et contenu Identity (7) | `identity.py`: `_safe_static_identity_source`, `_get_identities`, `_get_mutable_identity`, `_estimate_tokens`; `static_identity_content.py`: `_read_write_metadata`, `read_static_identity_snapshot`, `write_static_identity_content` | log standard serveur prive | diagnostic fichier, tokenisation ou DB; contenu Identity possible | `PRIVATE_OPERATOR_LOG_ACCEPTED` | Visibilite privee explicitement acceptee; aucun secret ni projection demontre. |
| arbitre hors transport (3) | `arbiter.py`: `_load_prompt`, `filter_traces_with_diagnostics`, `extract_identities` | log standard serveur prive | fichier prompt, position de parsing ou erreur runtime non transport | `PRIVATE_OPERATOR_LOG_ACCEPTED` | Les erreurs `requests` sont interceptees avant ces branches textuelles; le repli deterministe reste inchange. |
| etat hermeneutique (3) | `hermeneutic_node_state.py`: `read_node_state` (2), `write_node_state` | log standard serveur prive | diagnostic DB/etat | `PRIVATE_OPERATOR_LOG_ACCEPTED` | Lecture/ecriture locale sans projection du texte. |
| audit/contexte Memory (5) | `memory_arbiter_audit.py`: `get_hermeneutic_kpis`, `get_arbiter_decisions`, `record_arbiter_decisions`; `memory_context_read.py`: `get_identities`, `get_recent_context_hints` | log standard serveur prive | diagnostic DB et contexte interne | `PRIVATE_OPERATOR_LOG_ACCEPTED` | Les retours structurels restent bornes et les erreurs admin sont projetees separement. |
| dynamique Identity (11) | `memory_identity_dynamics.py`: `_embedding_similarity_safe`, `_embed_identity_conflict_vector` (3), `_has_open_strong_conflict`, `detect_and_record_conflicts`, `_list_recent_evidence`, `_apply_defer_policy_for_content`, `_expire_stale_deferred_global`, `decay_identities`, `reactivate_identities` | log standard serveur prive | diagnostic DB, similarite ou embedding | `PRIVATE_OPERATOR_LOG_ACCEPTED` | Les exceptions transport embedding sont desormais remplacees en amont par une erreur ne contenant que operation et classe source. |
| stores Identity (18) | `memory_identity_mutables.py`: `get_mutable_identity`, `list_mutable_identities`, `get_latest_mutable_identity_audit`, `apply_mutable_identity_subject_updates`, `upsert_mutable_identity`, `clear_mutable_identity`; `memory_identity_read_model.py`: `list_identity_fragments`, `list_identity_evidence`, `list_identity_conflicts`; `memory_identity_staging.py`: `get_identity_staging_state`, `get_latest_identity_staging_state`, `append_identity_staging_pair`, `mark_identity_staging_status`, `clear_identity_staging_buffer`; `memory_identity_write.py`: `set_identity_override`, `relabel_identity`, `record_identity_evidence`, `add_identity` | log standard serveur prive | diagnostic DB et contenu Identity possible | `PRIVATE_OPERATOR_LOG_ACCEPTED` | Logs prives existants necessaires au diagnostic; les read-models admin exposent classe/reason seulement. |
| init Memory (1) | `app/memory/memory_store_infra.py::init_db` | log standard serveur prive | diagnostic SQL/DB | `PRIVATE_OPERATOR_LOG_ACCEPTED` | Initialisation locale sans projection. |
| traces et resumes (7) | `memory_traces_summaries.py`: `_trace_exists_for_message`, `save_new_traces` (2), `save_summary` (2), `update_traces_summary_id`, `get_summary_for_trace` | log standard serveur prive | DB, contenu Memory possible ou erreur embedding deja bornee | `PRIVATE_OPERATOR_LOG_ACCEPTED` | Les resultats de retrieval et evenements JSONL n'exposent que codes/classes; le texte prive reste utile. |
| resume hors transport (2) | `summarizer.py::maybe_summarize`: runtime non transport et persistence DB | log standard serveur prive | parsing/runtime non transport et persistence DB | `PRIVATE_OPERATOR_LOG_ACCEPTED` | La panne DB locale conserve son diagnostic; les `RequestException` ont une branche classe/reason sans texte. |
| transports OpenRouter avec header sensible | `app/memory/summarizer.py::maybe_summarize`, `app/memory/arbiter.py::filter_traces_with_diagnostics`, `extract_identities` | log standard serveur prive | une `InvalidHeader` peut recopier une valeur de header | `SECRET_RISK_REQUIRES_FIX` | Confirme par valeur synthetique puis corrige: les trois branches journalisent operation, reason et classe seulement; les replis restent identiques. |
| transport embedding avec header sensible | `app/memory/memory_store.py::embed` vers les callers Memory/Identity | evenement JSONL classe-only puis logs standards prives aval | une `InvalidHeader` peut recopier le token d'embedding | `SECRET_RISK_REQUIRES_FIX` | Confirme puis corrige au point commun transport: l'erreur propagee ne contient que l'operation et la classe source; aucun caller ne recoit le texte original. |
| validation minimale | `app/minimal_validation.py::_run_check` | stdout texte/JSON et artefact de smoke | tout texte de l'exception du check | `CONTENT_FREE_BOUNDARY_REQUIRED` | Fuite synthetique confirmee puis corrigee au serializer: message public generique, reason code, classe et `raw_error_message_included=false`. |
| admin, JSONL, dashboard et export | `app/admin/admin_actions.py`, `admin_logs.py`, `app/observability/*` | JSONL, HTTP admin, dashboard, export Markdown | panne writer/read-model | `CONTENT_FREE_BOUNDARY_REQUIRED` | 30 branches logger n'exposent que classe/reason; les projections et tests anti-fuite restent la frontiere. |
| chat, Web, juge mutable et notes workspace | `app/core/conversations_*`, `workspace_folder_notes_prompt_lane.py`, `mutable_identity_judge_v2.py`, `web_search.py` | log prive et/ou resultat applicatif borne | panne provider, prompt ou DB | `CONTENT_FREE_BOUNDARY_REQUIRED` | Les 15 autres branches classe-only, dont le log `web_search.search_error` deja conforme via `type(e).__name__`, et les 2 attributs `prompt_id` ne propagent aucun texte arbitraire. |
| HTTP/API et retours d'agents | services admin Identity/Memory/settings, flows Agenda/Biblio, uploads/Whisper/workspace, chat et agents hermeneutiques | HTTP, observabilite ou retour d'agent | exception provider, stockage, DB ou validation | `CONTENT_FREE_BOUNDARY_REQUIRED` | Les sinks utilisent classe, statut, reason code et champs techniques allowlistes; les exceptions Biblio internes sont `repr=False` et projetees par `to_observability()`. |
| reemballage settings/crypto | `runtime_settings_repo.py`, `runtime_settings_write_path.py`, `runtime_secrets.py` | exception interne typee, ensuite log prive ou mapping HTTP classe-only | diagnostic DB/crypto | `NOT_A_LOG_SINK` | `str(exc)` ne sort pas directement; la destination terminale determine la politique. |
| compatibilite de signatures | services admin Identity et helpers embedding `purpose` | comparaison interne seulement | texte de `TypeError` | `NOT_A_LOG_SINK` | Le texte sert a choisir une branche de compatibilite et n'est pas retourne. |
| codes internes stables | extraction documentaire, Stimmung et Validation | warning/reason code applicatif | valeurs fixes de types internes (`prompt_missing`, parsing/validation, OCR) | `CONTENT_FREE_BOUNDARY_REQUIRED` | Ces `str(exc)` ne portent que des codes bornes construits localement; aucune exception arbitraire ne les alimente. |

Aucune famille ne reste `UNKNOWN`. `PRIVATE_OPERATOR_LOG_ACCEPTED` est une
decision explicite de conservation, pas une correction fictive. Les familles
`SECRET_RISK_REQUIRES_FIX` de la matrice ont ete fermees dans ce lot; leur
statut rappelle la classification qui imposait le patch.

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

Lot Z cloture le chantier Observabilite agentique V1 sans executer ce reset:
le GO operateur humain explicite, date et separe etait absent. Le reset reste
donc bloque par `operator_go_required` et doit etre traite comme operation
post-cloture dediee si l'operateur le demande plus tard.

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
- durcissement final Lot 1A/1B du 2026-06-23:
  - `/api/admin/logs` legacy reste disponible pour compatibilite mais ne
    retourne plus les lignes admin brutes; la route lit avec
    `fail_closed=True`, projette via
    `observability.admin_log_projection.project_legacy_admin_log_entries`, et
    expose `logs`, `count`, `redaction` et `payload_projection_schema`;
  - `observability.admin_log_projection` normalise les champs legacy
    `timestamp` / `event` / `level` et replie les autres champs dans un payload
    projete content-free; les cles dangereuses (`message`, `error`, `raw`,
    `payload`, secrets, headers, URL/path, DAV/XML/ETag) sont retirees ou
    redacted;
  - `admin.admin_logs.read_logs(..., fail_closed=True)` remonte
    `RuntimeError('admin_logs_read_failed')` sur panne de lecture apres log
    technique `err_class` content-free;
  - `observability.log_store.read_chat_log_events(..., fail_closed=True)`
    remonte `RuntimeError('chat_log_events_read_failed')` sur panne de lecture
    apres log technique `err_class` content-free;
  - correctif Lot 1B.1: `observability.log_store.read_chat_turn_pipeline(...,
    fail_closed=True)` et
    `observability.log_store.read_full_turn_metrics_snapshot(...,
    fail_closed=True)` remontent respectivement
    `RuntimeError('chat_log_turns_read_failed')` et
    `RuntimeError('chat_log_metrics_read_failed')`; sans `fail_closed=True`, le
    mode degrade historique `source.read_error=true` reste explicite pour les
    callers non-admin;
  - les routes admin logs de lecture principale, metadata, turns, metrics,
    delete scope et export Markdown traduisent les erreurs runtime en HTTP 500
    `ok=false` avec reason code stable, sans `str(exc)`, traceback, chemin,
    payload ou cause brute exposes;
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
- correctif Lot 5B.1: les projections `providers.secondary.<key>.status`
  conservent la taxonomie V1 observee au lieu de reduire tout non-`error` a
  `ok`; la precedence exposee est `error`, `failed`, `refused`,
  `not_configured`, `disabled`, `not_selected`, `not_applicable`, `skipped`,
  `ok`, puis `not_applicable` quand aucun evenement secondaire n'existe;
- `secondary_status_counts` agrege ces statuts reels pour que les no-op/refus
  secondaires restent visibles sans devenir des pannes, et que `failed` ne
  soit pas noye dans `ok`;
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

Decision livree Lot 5C:

- les reliquats `err=%s` corriges sont limites aux familles observabilite V1
  documentees: `observability.log_store`,
  `observability.dashboard_read_model`,
  `observability.dashboard_analytics_storage` et
  `observability.dashboard_materialization_runtime`;
- ces familles journalisent maintenant des pannes actionnables avec
  `reason=...` et `err_class=...`, sans `str(exc)` ni cause brute;
- les niveaux restent inchanges: les pannes store, read-model et storage
  restent `ERROR`, les echecs de materialization/freshness restent `WARNING`;
- le scan `test_observability_residual_redaction_lot5c` verifie l'absence de
  `err=%s`, `str(exc)` et `exc_info` dans `app/observability`, et rejoue des
  sentinelles prompt/message/payload provider/URL/token contre les projections
  admin logs et dashboard ordinaires;
- les projections 5A/5B restent content-free, les flags `raw_*` restent
  qualifies et aucun champ `raw` nu n'est ajoute;
- le content gate conserve son statut d'exception explicite et bornee; il n'est
  pas traite comme une projection ordinaire;
- les occurrences residuelles dans `app/server.py`, `app/admin` et `app/core`
  ne sont pas remplacees mecaniquement par ce lot, car elles couvrent des
  routes ou flux produit/admin plus larges que les projections observabilite V1;
- aucun Lot 6, Lot Z, reset, purge, backfill, migration, scan logs live,
  plateforme, Agenda runtime ou Biblio runtime n'est inclus dans cette
  decision.

Lot 6:

- smokes transverses content-free;
- preuve refus produit sans faux `ERROR`;
- preuve vraie panne fake/local visible;
- scan artefact/docs/diff/logs bornes.

Decision livree Lot 6:

- l'artefact JSONL content-free
  `app/docs/states/baselines/agentic-observability-smokes/frida-v1-agentic-observability-lot6-transverse-smokes-20260621T201840Z.jsonl`
  conserve les cas `LOT6_PREFLIGHT`, `LOT6_NORMAL_TURN_NO_FALSE_ERROR`,
  `LOT6_EXPECTED_REFUSAL_NOT_ERROR`, `LOT6_TRUE_FAILURE_VISIBLE`,
  `LOT6_AGENDA_DISABLED_OR_NOT_CONFIGURED`,
  `LOT6_BIBLIO_DISABLED_OR_NOT_SELECTED`,
  `LOT6_ADMIN_LOGS_PROJECTION_SCAN`, `LOT6_DASHBOARD_PROJECTION_SCAN`,
  `LOT6_ARTIFACT_SCAN`, `LOT6_DOCS_DIFF_SCAN`, `LOT6_LOG_SCAN_BOUNDED` et
  `LOT6_FINAL_VERDICT`;
- les cas comportementaux sont marques `covered_by_tests` quand une preuve live
  impliquerait une mutation artificielle, une panne provoquee ou une
  dependance externe non necessaire;
- les preuves live du Lot 6 sont limitees a la sante app, au scan Docker logs
  borne depuis `2026-06-21T20:18:40Z` et aux scans artefact/docs/diff; aucun
  dump brut n'est affiche, conserve ou committe;
- les projections admin logs/export Markdown et dashboard ordinaires restent
  content-free; le content gate reste l'exception explicite, chargee seulement
  par action volontaire;
- aucun reset, purge, backfill, migration, scan live DB, modification
  plateforme, Lot Z ou reset post-cloture n'est inclus dans cette decision.

Correctif Lot 6.1:

- le test `test_dashboard_static_page_route_returns_skeleton` ferme
  explicitement la reponse Flask `/dashboard` apres lecture du squelette, afin
  d'eviter un `ResourceWarning` sur `dashboard.html` lors des suites avec
  warnings renforces;
- ce correctif est strictement test-only: il ne modifie ni la route produit
  `/dashboard`, ni les projections dashboard, ni les API admin;
- aucun reset, purge, backfill, migration, Lot Z, plateforme ou scan live logs
  large n'est inclus dans cette decision.

Lot Z:

- relire contrat et preuves;
- executer scan logs borne reel;
- cloturer ou documenter les limites;
- evaluer le reset gate sans executer le reset si le GO operateur humain
  explicite/date/separe est absent.

Decision livree Lot Z:

- l'artefact JSONL content-free
  `app/docs/states/baselines/agentic-observability-smokes/frida-v1-agentic-observability-lotz-closure-20260622T081658Z.jsonl`
  conserve les cas `LOTZ_PREFLIGHT`, `LOTZ_REPLAY_PROOFS_LOTS_2_6`,
  `LOTZ_STATUS_TAXONOMY`, `LOTZ_AGENTIC_NOOP_AGENDA_BIBLIO`,
  `LOTZ_ADMIN_LOGS_CONTENT_FREE`, `LOTZ_DASHBOARD_CONTENT_FREE`,
  `LOTZ_TRUE_FAILURE_VISIBLE`, `LOTZ_REFUSAL_NOT_ERROR`,
  `LOTZ_BOUNDED_APP_LOG_SCAN`, `LOTZ_BOUNDED_DOCKER_LOG_SCAN`,
  `LOTZ_ARTIFACT_SCAN`, `LOTZ_DOCS_DIFF_SCAN`, `LOTZ_RESET_GATE` et
  `LOTZ_FINAL_VERDICT`;
- la suite conteneur ciblee rejoue 267 tests et couvre les preuves Lots 2-6:
  taxonomie, logs admin, export Markdown, dashboard, Agenda/Biblio no-op,
  refus produit et vraie panne fake/local;
- le scan Docker logs borne depuis `2026-06-22T08:16:10Z`, tail 5000, couvre
  1 ligne et 74 octets avec `forbidden_match_count=0`;
- le scan applicatif JSONL borne dans le conteneur depuis
  `2026-06-22T08:16:10Z` couvre 15 fichiers candidats, 9084 lignes et
  2941465 octets avec `forbidden_match_count=0`;
- aucun log brut n'est affiche, conserve ou committe; aucun reset, purge,
  backfill, migration, modification plateforme ou modification runtime n'est
  inclus dans Lot Z;
- le reset destructif post-cloture n'est pas execute. Il reste bloque par
  `operator_go_required` jusqu'a un futur GO operateur humain explicite, date,
  separe, avec scope exact, backup et rollback affiches juste avant execution.

### Correctif de vivacite Identity mutable

Le stage de tour existant `mutable_identity_judge` porte la politique Lot 1;
aucun stage autonome d'application n'est ajoute. Sa projection content-free
autorise seulement:

- `failure_class`: `transient`, `deterministic_input`,
  `deterministic_contract` ou `write_recovery`;
- `recovery_action`: `retry_preserve`,
  `terminal_consume_without_write`, `apply_recovery` ou `completed`;
- `processing_state`: `judge_not_called`, `judge_failed`, `write_failed` ou
  `completed`;
- `attempt_current`, `attempt_limit=2`, `window_fingerprint` SHA-256 tronquee a
  12 caracteres, `next_window_progress`, `next_buffer_pairs_count` et
  `writes_previously_applied`;
- les tailles et plafonds content-free deja mesures: nombre de paires,
  caracteres et estimation de tokens.

Ces champs sont allowlistes par la garde d'observabilite, projetes par le
read-model Identity, puis lus tels quels par `/identity` et
`/hermeneutic-admin`. Une absence historique de ces champs reste `unknown`; elle
ne devient ni `ok` ni `completed`. Fenetre, messages, proposition, prompt,
canon, exception brute, URL et secret restent interdits.

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
- distinction recent vs historique par tests/read-models;
- absence de log brut conserve;
- gate reset documente; reset non execute tant que le GO operateur requis est
  absent.

## 16. Interdits permanents

Hors les diagnostics existants explicitement classes
`PRIVATE_OPERATOR_LOG_ACCEPTED` pour les logs serveur prives par les sections 3
et 11, restent interdits sur toute surface technique:

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
