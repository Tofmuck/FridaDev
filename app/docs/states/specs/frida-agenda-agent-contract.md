# Frida Agenda Agent Contract

Statut: spec vivante
Date: 2026-06-08
Classement: `app/docs/states/specs/`
TODO produit: `app/docs/todo-todo/product/frida-agenda-agent.md`
Cloture V1: `app/docs/states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`
Portee: contrat cible du futur agent Agenda Frida. Lots 1-7D.1 livrent toggle
no-op, configuration redacted, outils read-only, agent JSON valide,
branchement applicatif read-only et preuve CalDAV live content-free. Les
propositions Agenda creent des pending actions temporaires; Lot 7A livre les
mutations confirmees uniquement avec fake transport; Lot 7B prouve uniquement
une creation live synthetique et son rollback delete sur la meme cible
synthetique avec GO humain explicite. Lot 7C/7C.1 verrouille les calendriers
familiaux ou non classifies; Lot 7D livre l'update confirme fake/local avec
preservation de l'ICS source sur VEVENT simple non recurrent; Lot 7D.1 ferme
les updates no-op et les ICS multi-VEVENT/recurrentes/overrides en fail-closed.
Lot 8A/8B livre l'observabilite content-free; Lot 8bis ajoute la recherche
read-only `find_next_matching_event` pour le prochain evenement futur
correspondant a une requete textuelle. Lot 8bis.1 rend le fallback live Agenda
agentique via `surface_error` et transmet `user_display_name=Tof` au contexte
d'enonciation agent. Lot 8bis.2 rend les surfaces read-only coherentes avec le
resultat et affiche les all-day multi-jours comme des plages avec duree.
Lot 8ter ajoute une cartographie docs-only des familles de questions Agenda
pour guider les validations futures sans ouvrir Lot 9. Le correctif cible du
2026-06-09 ferme les quatre familles partial des smokes de cloture et declare
une cloture pragmatique Agenda V1: utilisable au quotidien, a rouvrir seulement
sur bug reel, besoin concret ou decision explicite de nouvelle capacite. Les
updates live et mutations utilisateur reelles restent hors scope. Le
micro-correctif de cloture V1 ajoute deux garde-fous normatifs: les lectures
calendrier explicitement scopees refusent un `calendar_id` non resolu au lieu
d'elargir a tous les calendriers; un `calendar_id` resolu mais hors du scope
declare est refuse aussi. Les fenetres `soir` sont des intervalles demi-ouverts
18:00 -> 00:00 locale. Le garde-fou de scope calendrier couvre aussi la
recherche future `find_next_matching_event`.

Note normative de cloture: la note
`app/docs/states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`
declare Agenda V1 cloture pragmatiquement pour les usages prouves, garde Lot 9
ferme et limite toute suite a un micro-lot motive par bug reel, besoin concret
ou decision explicite.

Sources:

- `/opt/platform/fridadev/AGENTS.md`
- `/opt/platform/AGENTS.md`
- `/opt/platform/_codex_reports/nextcloud-frida-agenda-mail-roadmap-20260607T103442Z.md`
- `app/docs/states/specs/agentic-response-surface-contract.md`
- `app/docs/states/specs/frida-biblio-librarian-agent-contract.md`
- `app/docs/states/specs/frida-biblio-native-catalogue-contract.md`
- `app/docs/states/audits/frida-agentic-response-surface-lot0-audit-2026-06-06.md`
- `app/docs/states/audits/fridadev-temporal-system-audit-2026-05-18.md`
- `app/docs/states/policies/Frida-conversations-retention-policy.md`

## 1. Decision

Frida Agenda est une capacite agentique bornee, pas une collection de regex
locales qui devinent `demain`, `rendez-vous` ou `Famille`.

Formule produit:

- Frida parle.
- L'agent Agenda travaille.
- Le deterministe protege.

Modele cible:

- toggle Agenda off: Frida repond normalement, sans acces agenda;
- toggle Agenda on: Frida peut deleguer a l'agent Agenda;
- l'agent Agenda recoit la demande utilisateur, le dialogue recent borne, la
  date/heure courante, les calendriers disponibles et l'etat agenda utile;
- l'agent choisit une methode produit Agenda;
- le deterministe execute des outils CalDAV bornes;
- Frida restitue en langage naturel dans la voix normale du chat.

L'Agenda doit reutiliser le contrat de surface agentique: une reponse Agenda
integree est un message assistant Frida normal, pas un canal visible parallele.

## 2. Hors-scope du lot courant

Lot 5A branche l'execution applicative read-only avec transports injectables,
mais ne ferme pas la preuve live CalDAV.

Interdits pour le lot de cadrage:

- pas de creation d'app-password;
- pas de lecture ou affichage d'evenements reels en clair;
- pas de modification Nextcloud;
- pas de modification Caddy, Authelia, Calendar, Mail ou Contacts;
- pas de test live sur des evenements personnels;
- pas de creation, modification ou suppression d'evenement;
- pas de patch Biblio;
- pas d'agent Mail.

## 3. Cartographie FridaDev utile

Surfaces existantes a respecter:

- `app/web/chat_biblio_mode.js`: toggle conversationnel frontend
  `biblio_enabled`, persiste localement cote navigateur;
- `app/web/index.html` et `app/web/app.js`: zone naturelle pour un futur bouton
  Agenda dans les controles du composer, avec payload ajoute a `/api/chat`;
- `app/admin/runtime_settings_spec.py`: section `biblio_librarian_agent` comme
  modele d'une configuration runtime agent separee du toggle utilisateur;
- `app/core/chat_service.py`: orchestration du tour, lecture du toggle Biblio,
  appel Biblio avant l'appel LLM principal, puis construction du prompt;
- `app/biblio/chat_runtime.py`: decision d'activation, etat conversationnel,
  execution bornee, final lock et metas content-free;
- `app/biblio/librarian_agent_contract.py`: schema JSON, modes
  `off/shadow/candidate/active`, validation locale et budgets;
- `app/biblio/librarian_product_methods.py`: couche de methodes produit au-dessus
  des outils techniques;
- `app/biblio/librarian_tools.py`: registre d'outils allowlistes et
  observabilite content-free;
- `app/core/chat_llm_flow.py`: `AssistantResponseOverride`, persistance du
  message assistant final, timestamp, `message.meta`, Memory et identite;
- `app/core/conversations_maintenance.py`: table `conversation_messages` avec
  `timestamp TIMESTAMPTZ NOT NULL` et `meta JSONB`;
- `app/core/conversations_prompt_window.py`: reprise du dialogue avec labels
  Delta-T a partir des timestamps;
- `app/memory/memory_traces_summaries.py`: les messages `user` et `assistant`
  non vides deviennent eligibles aux traces, embeddings et resumes;
- `app/memory/summarizer.py`: les messages assistant normaux sont resumes quand
  le seuil de dialogue est atteint;
- `app/observability/chat_turn_logger.py`, dashboards et JSONL: lieux de preuve
  content-free, jamais de payload agenda brut.

Insertion cible:

- frontend: un toggle `agenda_enabled` dans les controles du composer, voisin du
  toggle Biblio;
- backend: un module futur `app/agenda/` avec agent, methodes produit, outils,
  et runtime chat, appele depuis `chat_service` a cote de Biblio;
- runtime settings: une section future `agenda_agent` pour le mode, le modele,
  les budgets, timeouts et limites;
- identite CalDAV V1: compte humain `tof` + app-password dedie Frida Agenda;
- secrets: une section ou source runtime dediee pour l'app-password, jamais
  exposee au LLM ni aux logs;
- surface finale: `AssistantResponseOverride` quand le resultat Agenda produit
  une reponse finale verrouillee; sinon lane prompt bornee ou clarification
  normale selon le cas.

Frontieres module Agenda:

- tous les nouveaux fichiers applicatifs Agenda vivent dans `app/agenda/`, au
  meme niveau que `app/biblio/`;
- `app/agenda/` est le repertoire calendrier/agenda: la logique Agenda ne doit
  pas etre dispersee dans `app/core/`, `app/web/`, `app/admin/` ou ailleurs,
  sauf pour les points de branchement strictement necessaires;
- les fichiers de `app/agenda/` restent separes par responsabilite;
- si un nouveau fichier Agenda approche ou depasse 600 lignes, il doit etre
  decoupe avant commit;
- ne pas creer de `utils.py`, de `helpers.py` generique, ni de fichier melant
  agent contract, CalDAV, runtime chat, pending store, observabilite et rendu.

## 4. Cartographie Nextcloud / Agenda

Etat issu du rapport plateforme du 2026-06-07 et du contexte produit courant:

- Nextcloud est le socle prioritaire;
- Calendar est installe et active;
- CalDAV fonctionne cote serveur via l'endpoint DAV Nextcloud, sans exposer de
  chemin DAV brut dans les preuves;
- le bypass DAV est borne aux routes DAV necessaires et l'interface web reste
  derriere Authelia;
- les clients doivent utiliser des app-passwords Nextcloud nommes, dedies et
  revocables;
- aucun mot de passe principal humain ne doit entrer dans Frida;
- le calendrier familial est un objet humain partage, pas une ressource cachee
  appartenant a Frida;
- le contexte utilisateur du 2026-06-08 indique que Calendar est visible sur
  macOS et iPhone, que les evenements se synchronisent et que le calendrier
  familial existe;
- les frottements Apple/Amandine restants sont classes clients/configuration,
  pas blocage d'architecture serveur.

Consequences pour FridaDev:

- la preuve serveur future ne doit pas dependre de macOS ou iOS;
- les frottements Amandine / Apple restent de l'administration client et ne
  bloquent pas le chantier code Agenda;
- CalDAV est la frontiere d'acces;
- aucune lecture DB Nextcloud n'est autorisee;
- aucune action par scraping de l'UI Nextcloud n'est autorisee.

## 4 bis. Decisions V1 tranchees

Identite CalDAV V1:

- Frida Agenda utilise le compte Nextcloud humain `tof` pour le premier
  chantier Agenda;
- elle utilisera un app-password dedie, nomme et revocable;
- pas de compte service Nextcloud `frida` pour l'Agenda V1;
- un utilisateur `frida` pourra etre envisage plus tard pour Files /
  repertoire Frida, mais ce n'est pas le sujet Agenda actuel;
- ce lot ne cree pas l'app-password;
- la valeur de l'app-password ne doit jamais etre affichee ni stockee dans les
  docs, logs, JSONL, prompts LLM, sorties terminal ou reponses.

Privacy V1:

- l'instance est une instance personnelle locale/OVH privee;
- les reponses Agenda visibles sont des reponses normales de Frida;
- elles entrent normalement dans le contexte, les resumes, embeddings et la
  memoire longue selon les contrats Frida existants;
- pas de politique speciale de redaction memoire pour l'Agenda V1;
- le contenu visible que l'utilisateur demande a Frida peut etre memorise comme
  dialogue normal;
- les secrets restent exclus partout;
- les logs, JSONL, read-models et observabilite restent content-free.

Amandine / Apple:

- les frottements Amandine, macOS et iOS restent de l'administration client;
- ils ne bloquent pas le chantier code Agenda;
- les preuves serveur futures ne dependent toujours pas d'iOS ou macOS;
- ce point ne doit pas etre traite dans un lot applicatif Agenda sans demande
  explicite.

## 5. Toggle et modes

Deux niveaux doivent rester distincts.

Toggle conversationnel:

- champ cible: `agenda_enabled`;
- portee: consentement explicite par conversation/tour depuis l'UI chat;
- off par defaut;
- si off, aucun appel CalDAV, aucun appel agent Agenda, aucune lecture d'etat
  Agenda;
- si on, Frida peut appeler l'agent Agenda, sans garantir une mutation.

Etat livre Lot 1:

- `agenda_enabled` est accepte dans le payload `/api/chat`;
- le frontend expose un toggle Agenda off par defaut avec persistance navigateur
  locale, voisin du toggle Biblio;
- `agenda_enabled` absent ou false reste un no-op strict cote backend;
- `agenda_enabled=true` appelle seulement un runtime no-op local
  `app/agenda/chat_runtime.py`;
- ce runtime no-op produit une observabilite content-free
  `frida_agenda_lot1_noop_v1` avec `caldav_access=false`,
  `nextcloud_access=false`, `secret_access=false` et
  `mutation_attempted=false`;
- aucun prompt lane, final lock, outil CalDAV, secret ou acces Nextcloud n'est
  cree dans Lot 1.

Etat livre Lot 2:

- `agenda_agent` existe comme section runtime settings;
- le mode par defaut est `off`;
- les modes admis sont seulement `off` et `active`;
- `shadow` et `candidate` sont retires de l'Agenda V1 et doivent etre rejetes;
- `caldav_account` est borne a l'identite V1 `tof`;
- `caldav_app_password` est un champ secret dedie, associe a la source
  operateur `FRIDA_AGENDA_CALDAV_TOF_APP_PASSWORD`, non seede depuis
  l'environnement dans Lot 2;
- les routes admin dediees `GET /api/admin/settings/agenda-agent`,
  `PATCH /api/admin/settings/agenda-agent` et
  `POST /api/admin/settings/agenda-agent/validate` sont exposees;
- le read-model admin expose seulement les booleens/presence et sources
  redacted: `is_secret`, `is_set`, `origin` et `secret_sources`;
- la validation admin de `active` exige une presence de secret, mais ne decrypt
  pas et ne lit jamais la valeur de l'app-password;
- aucun acces CalDAV, Nextcloud, app-password en clair, prompt agent ou outil
  Agenda n'est cree dans Lot 2.

Mode runtime agent:

- section cible: `agenda_agent`;
- modes autorises: `off`, `active`;
- `off`: aucun appel modele agent;
- `shadow`: mode non retenu pour l'Agenda V1, invalide;
- `candidate`: mode non retenu pour l'Agenda V1, invalide;
- `active`: l'agent peut piloter une methode produit autorisee, sous
  validation deterministe stricte;
- rollback: repasser a `off` doit restaurer le chat normal sans migration,
  rebuild ni purge DB.

Secrets runtime:

- l'app-password CalDAV dediee Frida Agenda pour le compte `tof` est un secret
  serveur;
- la source dediee V1 est `FRIDA_AGENDA_CALDAV_TOF_APP_PASSWORD`, conservee
  comme metadonnee operateur et non lue par Lot 2;
- elle ne doit pas apparaitre dans le payload agent, le prompt LLM, la reponse,
  les logs, les JSONL, les docs ou les sorties terminal;
- les read-models admin peuvent exposer seulement des booleens de presence et
  sources redacted.

Etat livre Lot 3:

- les briques techniques read-only vivent sous `app/agenda/`;
- `app/agenda/caldav_models.py` porte les modeles structures internes;
- `app/agenda/caldav_read_client.py` construit les requetes CalDAV read-only
  `PROPFIND`, `REPORT` et `GET` avec transport injectable;
- `app/agenda/ics_reader.py` parse les fixtures ICS anonymes vers evenements
  normalises;
- `app/agenda/read_tools.py` expose `calendar_list`, `event_query_range`,
  `event_get` et `event_search`;
- `app/agenda/observability.py` produit des observations content-free avec
  counts, fenetres et hashes courts;
- les tests Lot 3 utilisent seulement des fixtures anonymes et un transport
  fake;
- aucun branchement `/api/chat`, agent JSON, secret, CalDAV live, Nextcloud live
  ou mutation calendrier n'est cree dans Lot 3;
- le toggle conversationnel Agenda reste le no-op livre au Lot 1.

Etat livre Lot 3.1:

- le parseur ICS developpe les occurrences recurrentes dans la fenetre demandee,
  sans scan infini;
- le support borne couvre `RRULE` avec `FREQ=DAILY|WEEKLY|MONTHLY|YEARLY`,
  `COUNT`, `UNTIL`, `INTERVAL`, `EXDATE` et `RECURRENCE-ID`;
- les identifiants internes d'occurrences sont stables et distincts, derives
  sans exposer l'UID brut dans l'observabilite;
- les parties `RRULE` non supportees, par exemple les familles `BY*`, doivent
  lever une erreur locale content-free au lieu de produire une lecture fausse;
- `event_get` refuse tout UID ou URL arbitraire utilisateur: la cible doit deja
  exister dans `AgendaReadState`;
- si la cible connue porte un `caldav_path` exploitable et qu'un client
  read-only est fourni, `event_get` relit l'evenement par `GET` via transport
  injectable;
- si un client read-only est fourni mais que la cible connue n'a pas de
  `caldav_path`, `event_get` echoue proprement au lieu de pretendre avoir fait
  un `GET`;
- les statuts HTTP CalDAV sont valides: `PROPFIND` et `REPORT` attendent 207,
  `GET` attend 200, et 401/403/404/5xx produisent une erreur structuree sans
  body brut;
- aucun branchement chat, agent JSON, secret, CalDAV live, Nextcloud live ou
  mutation calendrier n'est ajoute par Lot 3.1.

Etat livre Lot 3.2:

- `dateutil.rrule` n'est pas disponible cote hote ni dans le conteneur
  `platform-fridadev`; aucune dependance nouvelle n'est ajoutee dans ce lot;
- aucun probe CalDAV live n'est fait: les preuves restent synthetiques,
  anonymes et sans secret;
- l'expansion recurrente vit dans `app/agenda/rrule_expander.py`, appelee par
  `app/agenda/ics_reader.py`, pour garder les responsabilites separees;
- le support borne couvre les formes iCalendar realistes suivantes:
  `FREQ=WEEKLY;BYDAY=MO`, `FREQ=WEEKLY;BYDAY=MO,WE`,
  `FREQ=MONTHLY;BYMONTHDAY=...`, `FREQ=MONTHLY;BYDAY=...`,
  `FREQ=MONTHLY;BYDAY=...;BYSETPOS=...` et
  `FREQ=YEARLY;BYMONTH=...;BYMONTHDAY=...`;
- `COUNT`, `UNTIL`, `INTERVAL`, `EXDATE` et `RECURRENCE-ID` restent appliques
  dans une fenetre bornee;
- aucune occurrence hors fenetre ne doit etre retournee par le read path;
- les identifiants d'occurrences restent stables et distincts, sans exposition
  de l'UID brut en observabilite;
- les parties RRULE non supportees continuent de produire une erreur locale
  content-free au lieu d'une lecture silencieusement fausse;
- les limites restantes avant live sont documentees: pas de prise en charge
  complete RFC 5545, pas de `VTIMEZONE` avance, support `TZID` simple complete
  en Lot 5A.2, pas de validation live Nextcloud/macOS tant qu'un probe
  content-free separe n'est pas autorise.

## 6. Entrees agent cible

L'agent Agenda recoit des entrees structurees et bornees:

- `schema_version`;
- `conversation_id_present`;
- `turn_id` technique content-free si disponible;
- message utilisateur courant pour interpretation interne;
- dialogue recent borne, avec timestamps;
- `now_utc_iso`, timezone Frida, date locale et heure locale;
- toggle Agenda effectif;
- mode agent effectif;
- calendriers disponibles: ids courts, display names si necessaires a la
  decision produit visible, permissions, flags `family_calendar` / `shared`;
- etat agenda utile content-free: fenetre lue, pending action id, dernier
  statut, ambiguite active;
- registre d'outils CalDAV autorises;
- budgets effectifs;
- contraintes de confirmation et de sortie;
- configuration modele effective expurgee.

Les entrees d'observabilite ne contiennent jamais:

- app-password;
- mot de passe principal;
- cookie;
- header Authorization;
- payload ICS brut;
- evenement brut;
- dialogue complet;
- prompt complet.

## 7. Sortie agent JSON cible

Schema livre en Lot 4:

```json
{
  "schema_version": "frida_agenda_agent_v1",
  "product_method": "read_today",
  "intent": "string",
  "calendar_scope": {
    "calendar_ids": ["short_id"],
    "family_calendar": false,
    "ambiguity": "none"
  },
  "time_scope": {
    "kind": "day",
    "start": "YYYY-MM-DDTHH:MM:SSZ",
    "end": "YYYY-MM-DDTHH:MM:SSZ",
    "timezone": "Europe/Paris",
    "ambiguity": "none"
  },
  "tool_calls": [],
  "draft": {
    "title": null,
    "location": null,
    "description": null,
    "calendar_id": null,
    "start": null,
    "end": null,
    "timezone": null,
    "all_day": null,
    "target_event_id": null,
    "change_summary": null
  },
  "mutation": {
    "requested": false,
    "kind": "none",
    "confirmation_required": false,
    "confirmation_level": "none",
    "pending_action_id": ""
  },
  "answer_mode": "agenda_summary",
  "risk_flags": [],
  "fallback_reason": "",
  "surface_intro": "",
  "surface_error": "",
  "surface_outro": ""
}
```

Regles:

- `product_method` est le niveau produit; les `tool_calls` sont seulement le
  sous-plan technique;
- la validation locale refuse toute methode inconnue;
- la validation locale refuse tout outil non allowliste;
- la validation locale refuse toute methode HTTP autre que `GET` dans
  `tool_calls`;
- la validation locale refuse les params techniques qui portent URL CalDAV,
  UID, ETag, ICS brut, Authorization, cookie, token ou app-password, quelle que
  soit la casse des marqueurs techniques; les proprietes ICS techniques
  usuelles (`RRULE`, `RECURRENCE-ID`, `RDATE`, `EXDATE`, `DTSTART`, `DTEND`,
  `DTSTAMP`, `CREATED`, `LAST-MODIFIED`, `SEQUENCE`, `STATUS`, `TRANSP`,
  `CATEGORIES`, `CLASS`, `PRIORITY`) sont interdites dans les params agent;
- `calendar_id` et `event_id` sont des identifiants locaux courts, jamais une
  URL complete, un chemin DAV brut, un UID/e-mail brut, un ETag ou une valeur
  contenant un secret; `event_id` refuse aussi les formes UID-like
  `uid:*`, `UID:*` et `uid=*`;
- `query`, `start`, `end` et `timezone` restent bornes par type et forme:
  aucun payload ICS, URL/path CalDAV, Authorization, cookie, token,
  app-password, UID/e-mail ou marqueur `SUMMARY`/`LOCATION`/`DESCRIPTION`;
- une mutation sans `confirmation_required=true` est invalide;
- une methode read-only, clarification ou contexte doit porter
  `mutation.kind=none` quand aucune mutation n'est demandee;
- les methodes `propose_*` peuvent porter l'intention de mutation associee a la
  methode produit, mais ne doivent pas devenir des mutations executees;
- les methodes `propose_*` portent un `draft` structure borne; pour une creation
  il doit contenir au minimum titre, calendrier cible, debut, fin et timezone;
- pour modification, deplacement ou suppression, un `event_get` declare par
  l'agent ne suffit pas: la cible doit etre reellement relue par un chemin
  read-only effectif, injecte/fake en test ou CalDAV read-only en runtime,
  avant pending action;
- les methodes `confirm_*` exigent `requested=true`, confirmation humaine,
  `pending_action_id` non vide et kind coherent;
- une suppression exige `confirmation_level=reinforced`;
- le calendrier familial exige un risk flag dedie; `create` et `delete` sur
  calendrier familial exigent `confirmation_level=reinforced`;
- un calendrier dont la classification familial/partage est inconnue ou absente
  est fail-closed pour `create`/`delete`: pas de confirmation simple, risk flag
  content-free `calendar_scope_unverified`;
- les champs de surface restent courts et ne remplacent pas le contenu
  verrouille ni les metas.

Implementation Lot 4:

- `app/agenda/product_methods.py` porte le registre des methodes produit et
  outils Agenda read-only autorises;
- `app/agenda/agent_contract.py` porte `frida_agenda_agent_v1`, la validation
  publique et les observations content-free;
- `app/agenda/agent_validation.py` porte les regles strictes de schema,
  methodes, outils, params et mutations;
- `app/agenda/agent_runtime.py` porte le runtime agent injectable/fakeable;
- `app/agenda/chat_runtime.py` consomme le toggle conversationnel et le mode
  runtime `agenda_agent` comme deux garde-fous separes.

Comportement Lot 4:

- `agenda_enabled` absent ou false: no-op strict, le runtime Agenda n'est pas
  appele;
- `agenda_enabled=true` et `agenda_agent.mode=off`: no-op propre et
  content-free;
- `agenda_enabled=true` et `agenda_agent.mode=active`: le runtime peut appeler
  un client modele injecte et valider un JSON agent, sans executer les outils
  CalDAV;
- `shadow` et `candidate` restent invalides pour Agenda V1 et produisent un
  fallback propre s'ils apparaissent par injection ou config corrompue;
- JSON absent, invalide, tronque ou hors schema: fallback propre, aucune
  exception utilisateur brute, aucun raw JSON modele en observabilite;
- Lot 4 ne lit aucun secret, ne contacte ni CalDAV ni Nextcloud, ne cree pas de
  pending action, ne fait aucune mutation et n'installe aucun final lock.

Etat livre Lot 5A:

- `app/agenda/agent_openrouter.py` ajoute un client modele Agenda injectable
  reutilisant le transport OpenRouter existant de FridaDev, sans nouveau secret
  provider;
- `app/agenda/read_execution.py` execute les plans read-only valides via
  `calendar_list`, `event_query_range`, `event_search` et `event_get`;
- `app/agenda/response_rendering.py` produit un `AgendaFinalResponseLock`
  content-free en meta/observabilite et visible en langage naturel;
- `app/agenda/caldav_transport.py` prepare le transport CalDAV read-only
  `PROPFIND`, `REPORT` et `GET`, mais les tests Lot 5A utilisent seulement un
  client injecte/fake;
- `app/core/chat_service.py` convertit un final lock Agenda valide en
  `AssistantResponseOverride`, donc la reponse Agenda est persistee comme
  message assistant Frida normal avec timestamp;
- le toggle conversationnel, le mode runtime `active` et la presence redacted
  du secret restent trois garde-fous separes;
- `agenda_agent.mode=off` reste un no-op, meme si le toggle est actif;
- `agenda_enabled=false` ou absent reste un no-op, meme si le mode runtime est
  actif;
- Lot 5A ne fait aucun acces CalDAV/Nextcloud live, ne lit aucun evenement
  personnel, ne cree pas d'app-password, ne fait aucune mutation et ne cree pas
  de pending store;
- Lot 5A.1 interdit toute reponse finale indiquant un agenda vide si aucun
  outil read-only n'a ete execute;
- une methode read-only executable doit porter au moins un `tool_call`
  allowliste; la validation et l'execution refusent toutes deux les plans
  read-only sans outil;
- le secret CalDAV et le client CalDAV ne sont resolus que pour un plan
  read-only valide et executable, ou pour la verification read-only d'une
  cible de proposition update/delete/reschedule lorsque le plan de
  verification est lui-meme executable;
- les methodes `clarify_*`, `confirm_*`, contexte et les propositions sans
  sequence de verification cible executable ne doivent jamais provoquer de
  lecture de secret ni construction de client CalDAV;
- `secret_access` en observabilite vaut vrai seulement si le secret runtime a
  ete effectivement resolu;
- les heures visibles sont rendues dans la timezone portee par l'evenement ou
  la lecture, avec fallback UTC si la timezone est invalide;
- Lot 5A.2 conserve les parametres ICS utiles et supporte `TZID` pour
  `DTSTART`, `DTEND`, `RECURRENCE-ID` et `EXDATE` dans le chemin read-only
  local;
- Lot 5A.2 marque `VALUE=DATE` comme evenement journee entiere et interdit au
  rendu d'inventer une heure visible pour ces evenements;
- Lot 5A.3 calcule des fenetres canoniques `today` et `tomorrow` depuis
  `now_iso` et `FRIDA_TIMEZONE`, puis les injecte dans le payload agent sous
  `canonical_time_windows`;
- Lot 5A.3 impose que `read_today` et `read_tomorrow` utilisent exactement la
  fenetre canonique disponible, cote `time_scope` et `event_query_range`; une
  fenetre UTC brute incompatible est rejetee avant lecture;
- `current_week` canonique reste hors scope du micro-correctif 5A.3 et devra
  etre tranche avec la politique de lecture semaine/disponibilites;
- Lot 5 complet reste ouvert jusqu'a une configuration Sauron redacted et une
  preuve live JSONL content-free.

## 8. Methodes produit Agenda

Familles minimales:

- lecture read-only;
- clarification;
- proposition sans ecriture;
- ecriture confirmee;
- contexte et memoire.

Methodes produit cibles:

| Methode | Famille | Mutation | Notes |
| --- | --- | --- | --- |
| `read_today` | lecture | non | lire la journee locale courante. |
| `read_tomorrow` | lecture | non | lire demain selon `FRIDA_TIMEZONE`, pas UTC brut. |
| `read_explicit_date` | lecture | non | date explicite resolue ou clarification. |
| `read_week` | lecture | non | fenetre bornee, synthese naturelle. |
| `search_events` | lecture | non | personne, lieu, mot-cle, date ou combinaison. |
| `find_next_matching_event` | lecture | non | prochain evenement futur correspondant a une requete textuelle. |
| `event_details` | lecture | non | details pratiques d'un evenement unique. |
| `summarize_day` | lecture | non | resume utile, pas dump ICS. |
| `find_availability` | lecture | non | trous/disponibilites derives d'une fenetre bornee. |
| `clarify_agenda_request` | clarification | non | date, calendrier, evenement ou intention ambigue. |
| `propose_create_event` | proposition | non | produit une proposition et un pending action. |
| `propose_update_event` | proposition | non | identifie la cible et propose le changement. |
| `propose_delete_event` | proposition | non | suppression jamais autonome. |
| `propose_free_slot` | proposition | non | propose un creneau libre. |
| `propose_reschedule` | proposition | non | propose un deplacement. |
| `confirm_create_event` | ecriture | oui | exige pending action + confirmation utilisateur. |
| `confirm_update_event` | ecriture | oui | exige pending action + confirmation utilisateur. |
| `confirm_delete_event` | ecriture | oui | exige confirmation renforcee. |
| `cancel_pending_agenda_action` | contexte | non | annule une proposition en attente cote FridaDev. |

## 9. Outils CalDAV minimaux

Outils read-only:

- `calendar_list`: lister les calendriers accessibles, permissions et ids
  courts; livre en Lot 3 avec reponse CalDAV synthetique et transport fake;
- `calendar_get`: verifier un calendrier cible et ses droits;
- `event_query_range`: requete CalDAV bornee par calendrier et fenetre temps;
- `event_search`: recherche bornee derivee de `event_query_range`, sans scan
  global ni nouvel acces large;
- `find_next_matching_event`: execution produit read-only qui part de `now_iso`,
  parcourt le futur par fenetres CalDAV de 31 jours maximum, applique un
  horizon par defaut de 365 jours maximum, s'arrete au premier match futur et
  retourne le plus proche; ce n'est pas une regex d'intention utilisateur;
- `event_get`: relire un evenement cible deja connu dans l'etat interne; si un
  `caldav_path` connu existe et qu'un client read-only est fourni, faire un
  `GET` borne via transport injectable; ne jamais exposer UID, ETag, URL brute
  ou ICS dans l'observation;
- `availability_query`: derivation bornee de disponibilites depuis les
  evenements lus, sans promettre une route free-busy tant qu'elle n'est pas
  prouvee.

Outils de proposition:

- `event_draft_validate`: normaliser et valider un brouillon sans ecriture;
- `pending_action_create`: stocker temporairement une proposition;
- `pending_action_get`: relire une proposition en attente;
- `pending_action_cancel`: annuler/expirer une proposition.

Outils de mutation confirmee:

- `event_create_confirmed`: creer via CalDAV seulement apres confirmation;
- `event_update_confirmed`: modifier via CalDAV seulement apres confirmation,
  avec ETag ou equivalent de concurrence;
- `event_delete_confirmed`: supprimer via CalDAV seulement apres confirmation
  renforcee, avec ETag ou equivalent de concurrence.

Interdits:

- lecture DB Nextcloud;
- route Nextcloud non-DAV pour agir sur le calendrier sans contrat separe;
- scraping UI Nextcloud;
- mutation sans pending action;
- suppression autonome;
- creation d'evenement invisible, calendrier ambigu ou horaire ambigu;
- dump ICS dans logs, docs, JSONL ou prompt agent.

## 10. Read-only, proposition, mutation

Lecture:

- autorisee avec toggle Agenda on;
- doit rester bornee par calendrier, fenetre et limite de resultats;
- peut mentionner dans la reponse visible les elements necessaires a la demande;
- ne doit pas persister de payload ICS brut ni de liste complete non demandee.

Proposition:

- autorisee avec toggle Agenda on;
- ne modifie pas Nextcloud;
- cree une action pending avec expiration TTL cote FridaDev;
- utilise un draft structure prive pour eviter de reconstruire la mutation
  depuis le dialogue au Lot 7;
- exige une cible reellement verifiee pour update/delete/reschedule;
- la reponse visible doit expliciter ce qui serait cree, modifie ou supprime;
- la meta durable reste content-free autant que possible.

Mutation:

- impossible sans confirmation humaine explicite;
- la confirmation doit viser une proposition precise;
- la confirmation doit etre recue dans un tour ulterieur ou dans une UI dediee;
- creation exige confirmation simple seulement si le calendrier est explicitement
  classifie non familial; calendrier familial/partage ou classification inconnue
  exige confirmation renforcee;
- modification est livree en fake/local seulement si le draft prive, la cible
  verifiee, l'ETag, le path CalDAV prive et l'ICS source sont presents; le
  patch preserve un VEVENT source simple non recurrent et ne reconstruit pas
  depuis le dialogue;
- suppression exige confirmation renforcee;
- calendrier familial exige prudence renforcee, risk flag `family_calendar`,
  detection depuis JSON agent ou calendrier lu quand disponible, et confirmation
  renforcee pour create/delete;
- `family_calendar=False` seul ne prouve pas un calendrier non familial: seule
  une classification explicite non familiale autorise une confirmation simple.

## 11. Etat temporaire de proposition

Le stockage cible des propositions ne doit pas etre un dump permanent de
calendrier.

Modele livre Lot 6:

- store temporaire attache a l'etat de conversation FridaDev
  (`agenda_pending_state`);
- TTL court obligatoire, 30 minutes par defaut;
- contenu durable content-free: operation, hashes courts, risques, create_ts,
  expires_ts, pointeur de draft prive et hash court;
- annulation et expiration sans mutation;
- une confirmation Lot 6 relisait la pending action mais refusait toute
  execution; Lot 7A execute maintenant seulement via fake transport injecte;
- `message.meta` ne porte qu'un pointeur content-free:
  `pending_action_id`, operation, confirmation level, risk flags, hash court,
  expiration et booleen `draft_private`;
- le draft structure prive temporaire peut contenir les details necessaires a
  une future execution Lot 7: operation, calendrier cible, timezone, start/end,
  all_day, titre, lieu, description, changement propose et cible verifiee;
- si disponible, une reference technique interne de cible peut rester dans le
  store prive temporaire, mais jamais dans `message.meta`, observabilite,
  dashboard, logs ou JSONL;
- Lot 7D peut ajouter l'ICS source a cette reference technique interne pour
  patcher un update confirme; cette ICS source reste strictement privee,
  temporaire et interdite dans `message.meta`, observabilite, dashboard, logs
  ou JSONL;
- les details humains restent dans la reponse visible et dans le pending store
  temporaire prive, pas dans les logs/dashboard/JSONL.

Lot 7A execute une confirmation uniquement depuis le pending draft prive et
avec client CalDAV write injecte/fake. Lot 7A.1 durcit le preflight avant tout
live write: update/delete exigent une cible technique avec ETag verifie. Lot 7D
ouvre `confirm_update_event` en fake/local seulement quand l'ICS source est
disponible et preservable. Lot 7D.1 precise que `change_summary` seul n'est pas
un changement executable, qu'un patch ICS identique a la source est refuse avant
`PUT`, et que les ICS multi-VEVENT, recurrentes ou avec override
`RECURRENCE-ID` restent fail-closed tant qu'une selection fiable du composant
ICS n'est pas livree. Relire uniquement le dialogue pour reconstruire une
mutation reste interdit.

Preuve Lot 6:

- `propose_create_event` cree une pending action create sans ecriture CalDAV;
- Lot 6.1: `propose_create_event` exige un draft structure suffisant avant de
  creer une pending action;
- Lot 6.2: `propose_update_event`, `propose_reschedule` et
  `propose_delete_event` ne reposent plus sur un resolver fake-only:
  le runtime peut executer les tool calls read-only bornes nécessaires
  (`event_query_range`, `event_search`, `event_get`) pour verifier la cible;
- Lot 6.3: la resolution du secret/client CalDAV pour verifier une cible
  update/delete/reschedule est interdite tant que le plan ne porte pas une
  sequence read-only executable, au minimum `event_query_range` puis
  `event_get`, avec `event_search` optionnel entre les deux; un `event_get`
  seul est refuse avec `agenda_pending_target_not_verified`,
  `secret_access=false` et `caldav_access=false`;
- Lot 6.2: `propose_delete_event` cree une pending action delete avec
  confirmation renforcee seulement apres cible relue, sans suppression;
- Lot 6.1: le rendu visible est concret, mais meta/observabilite restent
  content-free et ne contiennent pas titre, lieu, description, UID, ETag, path
  CalDAV ou ICS;
- Lot 6.2: les drafts prives sortis de l'etat par tronquage `MAX_ACTIONS`,
  expiration ou annulation sont oublies.
- Lot 7A/7D: `confirm_create_event`, `confirm_update_event` et
  `confirm_delete_event` executent uniquement en fake transport injecte pour les
  preuves locales; aucun write live utilisateur n'est autorise par Lot 7D;
- Lot 7A: `confirm_create_event` utilise un draft prive structure, genere un
  ICS minimal, fait un `PUT` avec `If-None-Match: *`, puis neutralise la
  pending action en `executed`;
- Lot 7D: `confirm_update_event` utilise la cible verifiee du draft prive,
  exige ETag, path CalDAV prive et ICS source, puis applique un patch cible sur
  le VEVENT source simple; UID, proprietes inconnues, alarmes, participants et
  metadonnees non touchees doivent etre preserves autant que possible;
- Lot 7D.1: les ICS multi-VEVENT, les evenements recurrents (`RRULE`, `RDATE`,
  `EXDATE`) et les overrides `RECURRENCE-ID` sont refuses avant `PUT` avec une
  raison content-free; aucun patch silencieux du premier VEVENT n'est autorise;
- Lot 7D.1: `change_summary` seul ne permet pas de creer une pending action
  update executable; les drafts legacy sans champ patchable concret et les
  patchs identiques a l'ICS source sont refuses avant `PUT`;
- Lot 7D: si l'ICS source manque ou ne peut pas etre preservee, l'update est
  refuse avant `PUT` avec une raison content-free; aucun update n'est reconstruit
  depuis le dialogue ou depuis un VEVENT minimal;
- Lot 7A: `confirm_delete_event` exige une confirmation renforcee et fait un
  `DELETE` sur la cible technique interne avec ETag obligatoire; aucune
  suppression n'est possible sans pending action valide, draft prive et ETag
  verifie;
- Lot 7A: si le draft prive a disparu, si l'action est expiree/annulee, si le
  client write est absent ou si la cible technique est absente, la confirmation
  est refusee avant toute requete write;
- Lot 7A.1: `agenda_write_etag_missing` refuse update/delete avant tout
  `PUT`/`DELETE`; `CalDavWriteClient` applique aussi cette defense en profondeur;
- Lot 7C: create/delete sur calendrier familial ou partage exigent
  `risk_flags=["family_calendar"]` et `confirmation_level=reinforced`; la
  detection combine `calendar_scope.family_calendar` du JSON agent et
  `CalendarSummary.family_calendar` quand le calendrier est connu ou la cible a
  ete relue; toute pending action familiale avec confirmation simple est refusee
  avant `PUT`/`DELETE`;
- Lot 7C.1: la protection est fail-closed; un `CalendarSummary` sans
  classification explicite reste `unknown`, `parse_calendar_propfind()` ne
  traite plus l'absence de prop custom comme non familial prouve, et create/delete
  sur scope inconnu portent `calendar_scope_unverified` avec confirmation
  renforcee obligatoire;
- Lot 7C.1: le runtime ne resout pas le secret CalDAV uniquement pour classifier
  une creation; sans etat calendrier connu, la proposition reste possible mais
  seulement en confirmation renforcee;
- Lot 7C: la surface visible mentionne en langage naturel que le calendrier est
  partage ou familial, sans exposer UID, ETag, path CalDAV, ICS ni jargon
  technique;
- `cancel_pending_agenda_action` annule une pending action sans mutation;
- expiration/cancel empechent toute execution;
- observabilite et meta restent content-free: id, operation, expiration,
  confirmation level, risk flags, hash court, method names, status codes,
  booleens; elles ne contiennent jamais titre, lieu, description, UID, ETag,
  path/URL CalDAV, ICS, Authorization, cookie, token ou app-password.

Lot 7B livre:

- preuve live write separee, avec evenement synthetique, GO humain explicite,
  rollback/suppression de test documente;
- artefact content-free:
  `app/docs/states/baselines/agenda-smokes/frida-agenda-lot7b-live-write-20260609T114108Z.jsonl`;
- `LOT7B_CREATE_SYNTHETIC_EVENT`: pending create confirme, `PUT 201`,
  final lock assistant normal, ETag present, aucun evenement personnel touche;
- `LOT7B_CREATED_EVENT_STATUS_ONLY`: relance status-only `GET 200`, ETag
  present, sans sauvegarder ICS ni titre/lieu/description;
- `LOT7B_ROLLBACK_SYNTHETIC_EVENT`: rollback delete renforce sur la cible issue
  du meme smoke, `DELETE 204`;
- `LOT7B_FINAL_SYNTHETIC_STATE`: `GET 404`, evenement synthetique supprime;
- `LOT7B_NO_UPDATE_LIVE`: au moment du smoke Lot 7B,
  `confirm_update_event` restait refuse avec
  `agenda_write_update_preservation_required`, zero requete `PUT`; Lot 7D
  supersede ce blocage en fake/local seulement, sans preuve d'update live;
- `LOT7B_CONTENT_FREE_SCAN`: aucun titre, lieu, description, UID, ETag, path
  CalDAV, ICS, Authorization, cookie, token ou app-password dans l'artefact;
- aucun Lot 8 n'est ferme par Lot 7B.

## 12. Restitution visible et contexte suivant

La reponse Agenda visible suit le contrat agentic response surface:

1. `surface_intro` si non vide;
2. reponse naturelle Frida;
3. limites utiles;
4. question de clarification ou demande de confirmation si necessaire;
5. `surface_outro` si non vide.

En cas d'echec apres tentative live Agenda (`caldav_access=true` ou
`nextcloud_access=true`), la surface visible verrouillee utilise `surface_error`
fournie par l'agent Agenda. Le deterministe peut selectionner et assembler cette
surface, mais il ne redige pas la phrase d'echec visible. Pour les methodes
read-only, `surface_error` est obligatoire et doit rester simple, honnete et
vernaculaire: pas de jargon CalDAV, pas d'invention de resultat, pas de
mensonge du type `je ne peux pas rouvrir ton agenda` quand une tentative live a
eu lieu.

Pour les methodes read-only, `surface_outro` reste un champ contractuel mais
n'est plus affiche apres execution. Cette surface est produite avant la lecture
effective et ne doit donc pas servir de conclusion dependante du resultat
(`si rien ne remonte`, relance de recreation, etc.). La restitution read-only
utilise `surface_intro` puis le contenu reel, ou `surface_error` en cas d'echec
live.

Regles:

- Frida reste la seule voix visible;
- pas de wrapper technique `[AGENDA RESULT]`;
- pas de noms d'outils, ETag, UID, ICS, URL CalDAV ou reason codes dans la
  phrase normale;
- les metas prouvent en `message.meta`, observabilite et JSONL content-free;
- le message assistant Agenda est persiste normalement avec timestamp;
- le tour suivant doit voir cette reponse comme dialogue normal;
- Memory, resumes et embeddings suivent les contrats existants pour les
  messages assistant normaux.

## 13. Timestamps et verite temporelle

L'agent Agenda est temporellement sensible.

Contraintes:

- `now_utc_iso` vient de l'horloge de tour Frida;
- `FRIDA_TIMEZONE` est la source du jour local;
- `aujourd'hui`, `demain`, `semaine prochaine` et les gaps de dialogue se
  resolvent depuis le payload temps canonique, pas depuis l'UTC brut;
- les fenetres CalDAV sont stockees/executees en instants explicites;
- la reponse visible doit etre claire sur le jour local si l'ambiguite est
  possible;
- toute preuve live doit noter le timestamp technique sans contenu personnel.

## 14. Observabilite content-free

Events conceptuels futurs:

- `agenda_start`;
- `agenda_model_call`;
- `agenda_json_validated`;
- `agenda_tool_plan`;
- `agenda_tool_call`;
- `agenda_pending_action`;
- `agenda_confirmation`;
- `agenda_mutation`;
- `agenda_fallback`;
- `agenda_final`.

Champs autorises:

- schema version;
- toggle;
- mode agent;
- modele effectif expurge;
- status;
- reason code;
- methode produit;
- tool names;
- endpoint kind;
- calendar ids courts;
- family calendar boolean;
- window start/end;
- counts;
- duration buckets;
- retry count;
- ETag hash court;
- pending action id;
- confirmation level;
- booleens de presence;
- hashes courts.

Champs interdits:

- app-password;
- mot de passe principal;
- cookie;
- header;
- URL CalDAV complete si elle contient des ids sensibles;
- ICS brut;
- titre, description, lieu ou invite brut dans logs/read-models;
- evenement brut;
- prompt complet;
- dialogue complet;
- raw JSON modele;
- `.env`;
- DSN;
- token.

### 14.1 Read-model admin Agenda Lot 8A

Lot 8A livre une premiere surface admin content-free:

- route: `GET /api/admin/agenda/observability`;
- source runtime: evenements `observability.chat_log_events` filtres
  `stage=agenda`, sans lecture Nextcloud ni DB Nextcloud;
- source testable hors route: metas conversationnelles Agenda deja persistees
  comme messages assistant normaux;
- schemas projetes: read-only, propositions/pending, confirmations/write fake
  ou synthetiques, et erreurs content-free;
- pending actions exposees seulement par id, hash, operation, statut,
  expiration, niveau de confirmation et flags de risque;
- drafts prives, contenu humain d'evenement, references techniques CalDAV et
  payloads bruts restent exclus du read-model;
- la route peut compter, hasher ou bucketiser, mais ne doit jamais recopier
  titre, lieu, description, invite, UID brut, ETag brut, path/URL CalDAV brut,
  ICS brut, Authorization, cookie, token, app-password, prompt brut ou dialogue
  brut.

La route runtime Lot 8A ne projette pas une conversation courante: elle expose
uniquement les evenements `stage=agenda`. La projection conversationnelle reste
un helper teste pour prouver que les metas Agenda peuvent etre reduites sans
contenu brut, pas une vue admin conversationnelle.

### 14.2 Smokes live anonymises Lot 8B

Preuve conservee:

- artefact:
  `app/docs/states/baselines/agenda-smokes/frida-agenda-lot8b-live-observability-20260609T142458Z.jsonl`;
- smokes serveur realises via FridaDev, sans iOS/macOS:
  `read_today`, `read_tomorrow`, `search_events`, route admin observability et
  tour de contexte suivant;
- runtime redacted: mode `active`, compte `tof` prouve par hash, secret
  configure uniquement comme booleen;
- conversation reelle anonymisee: assistant sauvegarde comme message normal,
  timestamp present, contexte precedent repris, Delta-T detecte;
- tentative optionnelle de proposition sans ecriture: `partial`, non utilisee
  pour fermer le Lot 8B;
- aucun live write, aucune mutation utilisateur, aucune DB Nextcloud;
- artefact, sortie admin observability et logs applicatifs `stage=agenda`
  scannes contre les familles interdites; preuves conservees sans titre, lieu,
  description, invite, UID brut, ETag brut, path/URL CalDAV brut, ICS brut,
  Authorization, cookie, token, app-password, prompt brut ou dialogue brut.

Lot 8B ferme les smokes live anonymises et le scan content-free du read-model
Agenda. Il ne ferme pas Lot 9 et n'autorise pas de mutation utilisateur reelle.

### 14.3 Recherche prochain evenement correspondant Lot 8bis

Lot 8bis ajoute le cas produit read-only `find_next_matching_event`:

- l'agent Agenda choisit cette methode pour les demandes du type prochain
  rendez-vous avec une personne, un lieu ou un terme textuel;
- le deterministe ne reconnait pas l'intention par regex utilisateur: il execute
  seulement le plan JSON valide de l'agent;
- l'execution part de `now_iso`, interroge les calendriers accessibles par
  fenetres CalDAV de 31 jours maximum, applique un horizon par defaut de 365
  jours maximum et s'arrete des qu'un match futur est trouve;
- si `calendar_scope.calendar_ids` porte une cible explicite,
  `find_next_matching_event` exige un `calendar_id` resolu dans les calendriers
  accessibles et inclus dans ce scope avant toute lecture de fenetre; sinon il
  refuse content-free au lieu d'elargir a tous les calendriers;
- `search_events` reste une recherche dans une fenetre deja lue; `find_next`
  est une recherche future progressive et bornee;
- si aucun match n'est trouve dans l'horizon, Frida repond que rien n'a ete
  trouve dans cet horizon, sans pretendre avoir scanne l'infini;
- si CalDAV/Nextcloud a ete tente mais echoue, Frida produit une reponse Agenda
  verrouillee via `surface_error` fournie par l'agent; le LLM principal ne doit
  pas inventer une explication du type `je ne peux pas rouvrir ton agenda`;
- les logs, metas, read-models et JSONL restent content-free: pas de titre,
  lieu, description, UID, ETag, path/URL CalDAV, ICS brut ou secret.

Lot 8bis.1 ajoute aussi `user_display_name=Tof` dans le payload agent comme
contexte d'enonciation. Ce nom n'est pas un secret et peut apparaitre dans le
message assistant visible, mais l'observabilite, les metas et les JSONL ne
stockent que presence/hash/chars.

Preuve conservee:

- artefact:
  `app/docs/states/baselines/agenda-smokes/frida-agenda-lot8bis-next-matching-live-20260609T152733Z.jsonl`;
- vraie conversation Frida avec toggle Agenda actif et runtime `active`;
- methode produit validee: `find_next_matching_event`;
- CalDAV/Nextcloud touches uniquement en read-only;
- `final_response_override=true`, message assistant normal timestamped,
  `mutation_attempted=false`;
- scan content-free `met`, sans contenu Agenda brut ni secret.

### 14.4 Surface read-only et all-day multi-jours Lot 8bis.2

Lot 8bis.2 corrige deux invariants de restitution:

- une lecture read-only executee n'affiche plus `surface_outro`, que le resultat
  soit trouve ou vide; cela evite les conclusions contradictoires generees avant
  la lecture effective;
- `surface_error` reste la seule surface d'echec live agentique;
- les evenements `VALUE=DATE` multi-jours respectent `DTEND` exclusif et sont
  rendus comme des plages avec duree, par exemple `du 11 au 17 juillet 2026,
  toute la journee (7 jours)` pour `DTSTART=20260711` et `DTEND=20260718`;
- la surface visible porte assez de contexte pour qu'un tour suivant puisse
  raisonner sur la duree du sejour depuis le dialogue normal;
- l'observabilite reste content-free: pas de titre, lieu, description, UID,
  ETag, path/URL CalDAV, ICS brut ou secret.

### 14.5 Cartographie des questions Agenda Lot 8ter

Lot 8ter livre uniquement une cartographie documentaire:

- audit source:
  `app/docs/states/audits/frida-agenda-question-cartography-2026-06-09.md`;
- familles classees avec exemples vernaculaires anonymises, disponibilite
  utilisateur, preuve conservee, chemin technique, limite connue et prochain
  test utile;
- `Disponible utilisateur` et `Preuve conservee` sont deux axes separes:
  une question peut etre tentable par l'utilisateur sans avoir encore un smoke
  dedie, et une absence de preuve conservee ne signifie pas absence de capacite;
- familles explicites ajoutees pour eviter les promesses implicites:
  sous-fenetres vernaculaires, rappels/notifications/alarmes,
  participants/invitations, recurrences/occurrences et perimetre operateur;
- la cartographie ne cree aucune capacite runtime, ne lance aucun smoke live, ne
  lit aucun calendrier et ne modifie pas le perimetre CalDAV;
- Lot 9 reste ferme: les validations futures proposees sont des pistes de
  decision, pas des cases cochees.

### 14.6 Smokes cibles de cloture pragmatique

Les smokes cibles du 2026-06-09 ne testent pas toute la cartographie. Ils
verifient seulement quatre familles jugees proches de l'usage quotidien:

- lire une date explicite;
- lire des sous-fenetres vernaculaires matin/apres-midi/soir;
- reprendre une duree ou un sejour en multi-tour;
- demander l'aide ou le perimetre operateur de l'Agenda.

Artefact conserve:

- `app/docs/states/baselines/agenda-smokes/frida-agenda-v1-targeted-closure-smokes-20260609T175408Z.jsonl`.
- Le premier smoke partial reste conserve sous
  `app/docs/states/baselines/agenda-smokes/frida-agenda-v1-targeted-closure-smokes-20260609T171000Z.jsonl`.

Verdict normatif:

- l'artefact final est content-free;
- les quatre familles ciblees sont `met`;
- la seule mutation observee est une creation synthetique temporaire pour
  prouver duree/sejour/reprise, supprimee par rollback dans le meme run;
- une cloture pragmatique globale Agenda V1 est declaree;
- la note de cloture normative est conservee sous
  `app/docs/states/audits/frida-agenda-v1-pragmatic-closure-2026-06-09.md`;
- Lot 9 reste ferme.

Resultats prouves:

- `read_explicit_date` execute CalDAV/Nextcloud read-only et produit un final
  lock Frida normal;
- les sous-fenetres vernaculaires simples prouvent des fenetres horaires bornees
  de 6h pour `ce matin` et `demain soir`; les fenetres `soir` finissent a
  minuit local en borne exclusive;
- la reprise duree/sejour est prouvee avec un evenement synthetique multi-jours
  cree, lu, repris au tour suivant, puis supprime dans le meme run. Le tour de
  reprise repond depuis le contexte visible deja rendu et ne constitue pas une
  nouvelle lecture Agenda;
- l'aide/perimetre operateur dispose d'une surface dediee sans jargon sensible.

Garde-fou de scope calendrier V1:

- si `calendar_scope.calendar_ids` est vide, un `calendar_id` invente par le
  modele dans un outil de lecture peut etre ignore et la lecture generale peut
  interroger les calendriers accessibles;
- si `calendar_scope.calendar_ids` est non vide, le plan est explicitement
  scope: un `calendar_id` absent, non resolu ou hors scope doit produire un
  refus content-free avant toute lecture elargie tous calendriers, y compris
  pour `find_next_matching_event`;
- l'id brut non resolu ne doit pas apparaitre dans l'observabilite.

Capacites volontairement laissees ouvertes apres V1: disponibilites riches,
comparaison de journees/evenements, rappels, invitations, recurrences produit
riches et mutations utilisateur reelles.

## 15. Invariants securite

Invariants durs:

- pas de DB directe Nextcloud;
- pas de mot de passe principal;
- identite CalDAV V1 = compte humain `tof` + app-password dedie Frida Agenda;
- pas de compte service Nextcloud `frida` pour l'Agenda V1;
- app-password dedie Frida Agenda, jamais expose au LLM;
- secrets uniquement cote runtime/config serveur;
- CalDAV comme frontiere d'acces;
- pas d'ecriture sans confirmation humaine;
- pas de suppression autonome;
- pas de modification du calendrier familial sans confirmation claire;
- pas de creation d'evenement invisible ou ambigu;
- pas de scraping UI Nextcloud pour agir;
- pas de dependance a iOS/macOS pour la preuve serveur;
- tout live proof doit etre content-free ou anonymise;
- aucun secret, token, app-password, cookie ou evenement personnel brut dans
  JSONL/docs;
- pas de redaction speciale memoire pour les reponses Agenda visibles en V1,
  hors secrets et observabilite content-free;
- aucune mutation si le calendrier cible ou le fuseau horaire sont ambigus;
- aucune suppression si l'evenement cible n'est pas relu juste avant execution.

## 16. Preuves live futures

Les preuves futures doivent rester content-free.

Baseline et fixtures Lot 0:

- baseline source:
  `app/docs/states/baselines/frida-agenda-agent-lot0-baseline-2026-06-08.md`;
- fixtures anonymes:
  `app/docs/states/baselines/agenda-fixtures/`;
- les fixtures sont synthetiques, versionnees, non personnelles et locales au
  repo;
- elles peuvent servir aux tests unitaires locaux de parsing, fenetres, counts,
  hashes courts et redaction;
- elles ne sont pas une preuve live CalDAV et ne doivent pas etre importees dans
  Nextcloud;
- aucun lot runtime ne doit recopier les titres, descriptions, lieux, UID,
  ETag, URL CalDAV ou payload ICS dans les logs, JSONL, read-models ou docs de
  preuve.

Preuve Lot 3 locale:

- `calendar_list` est prouve avec une reponse PROPFIND synthetique;
- `event_query_range` est prouve avec fixtures ICS anonymes et fenetres ISO
  explicites;
- `event_get` est prouve depuis un identifiant deja present dans l'etat interne
  de test, puis par `GET` fake quand un `caldav_path` connu existe;
- `event_search` est prouve comme recherche locale bornee sur evenements deja
  lus;
- le client read-only construit `PROPFIND`, `REPORT` et `GET` mais les tests
  n'utilisent qu'un transport fake;
- les observations de test ne contiennent pas ICS brut, UID brut, ETag brut,
  URL CalDAV brute, header Authorization, cookie, app-password, titre, lieu ou
  description.

Preuve Lot 3.1 locale:

- les recurrences ICS sont testees avec fenetre bornee, `RRULE`, `EXDATE` et
  `RECURRENCE-ID`;
- les erreurs de recurrence non supportee ne contiennent pas de payload ICS,
  UID, titre, lieu ou description;
- 401/403/404/500 sont testes avec un transport fake et produisent une erreur
  CalDAV read-only structuree, redacted et content-free;
- aucune preuve Lot 3.1 ne depend de Nextcloud live, CalDAV live, secret,
  app-password ou evenement personnel.

Preuve Lot 3.2 locale:

- les bibliotheques de recurrence sont probees sans installer de dependance:
  `dateutil.rrule` est absent cote hote et conteneur;
- les tests synthetiques couvrent les familles `BYDAY`, `BYMONTHDAY`,
  `BYSETPOS`, `BYMONTH`, `COUNT`, `UNTIL`, `INTERVAL`, `EXDATE` et
  `RECURRENCE-ID`;
- les tests verifient des fenetres explicites, l'absence d'occurrence hors
  fenetre et des ids d'occurrence distincts;
- aucune preuve Lot 3.2 ne lit Nextcloud live, CalDAV live, secret,
  app-password, UID brut, titre, lieu, description ou payload ICS personnel.

Preuve Lot 4 locale:

- `frida_agenda_agent_v1` est valide strictement: version exacte, root keys
  strictes, `product_method`, `calendar_scope`, `time_scope`, `tool_calls`,
  `mutation`, `answer_mode`, `risk_flags`, `fallback_reason`,
  `surface_intro`, `surface_error` et `surface_outro`;
- `surface_intro`, `surface_error` et `surface_outro` doivent etre des strings
  courts, jamais `null`; `surface_error` est obligatoire pour les methodes
  read-only;
- les outils inconnus, hors methode produit, mutatifs ou avec params interdits
  sont refuses avant tout reseau;
- les valeurs dangereuses dans des params autorises sont refusees: URL/path
  CalDAV brut dans `calendar_id`, UID/e-mail brut dans `event_id`, marqueurs
  secret/ICS case-insensitive dans `query`, `start`, `end` ou `timezone`, et
  proprietes ICS techniques usuelles case-insensitive (`RRULE`,
  `RECURRENCE-ID`, `DTSTART`, `LAST-MODIFIED`, etc.), et formes UID-like dans
  `event_id`;
- les mutations demandees exigent confirmation humaine et les suppressions
  exigent confirmation renforcee;
- les mutations incoherentes sont refusees: une methode read-only ne peut pas
  porter `kind=create|update|delete`, meme avec `requested=false`;
- les confirmations exigent un pending action id non vide;
- le runtime agent est fakeable/injectable en test et le client par defaut ne
  contacte aucun provider;
- le toggle conversationnel et le mode runtime restent deux conditions
  separees: toggle off = no-op, mode off = no-op, mode actif seul ne suffit pas
  si le toggle est off;
- `shadow` et `candidate` restent rejetes comme modes Agenda V1;
- JSON absent, invalide, tronque ou hors schema produit un fallback propre;
- aucune preuve Lot 4 ne lit Nextcloud live, CalDAV live, secret, app-password,
  UID brut, titre, lieu, description, URL CalDAV brute ou payload ICS personnel;
- Lot 4 ne branche pas encore de lecture active, pending store, mutation,
  final lock Agenda ou reponse visible Agenda.

Preuve Lot 5A locale:

- l'agent JSON reste fakeable/injectable en test et le provider live n'est pas
  requis pour fermer Lot 5A;
- le client read-only reste injectable en test; aucun transport CalDAV live
  n'est utilise dans les preuves Lot 5A;
- un plan `read_today` valide execute `event_query_range` avec client fake et
  produit un `AgendaFinalResponseLock`;
- le chemin serveur fake prouve que le final lock devient un
  `AssistantResponseOverride`, puis un message assistant normal avec timestamp,
  `message.meta` content-free et sauvegarde de conversation;
- les observations Lot 5A ne contiennent pas titre, lieu, description, UID,
  ETag, URL/path CalDAV, payload ICS, Authorization, cookie, token ou
  app-password;
- Lot 5A ne prouve pas encore `today`, `tomorrow`, `search`, `details`,
  Delta-T et Memory eligible en live CalDAV: ces preuves restent Lot 5B.

Preuve Lot 5A.1 locale:

- un payload read-only sans `tool_calls` est rejete avec
  `agenda_agent_tool_not_executable`;
- `read_execution` retourne `agenda_readonly_no_tool_calls` si un plan
  read-only sans outil atteint l'execution par defense en profondeur;
- un plan `clarify_agenda_request` valide n'appelle pas
  `get_runtime_secret_value()`;
- l'observabilite `secret_access` reste fausse sans secret resolu et devient
  vraie seulement quand un secret fake de test est resolu via runtime settings;
- un evenement `07:00Z` en timezone `Europe/Paris` pendant juin est rendu
  `09:00`, pas `07:00`;
- aucune preuve Lot 5A.1 ne lit Nextcloud live, CalDAV live ou secret reel.

Preuve Lot 5A.2 locale:

- un evenement `DTSTART;TZID=Europe/Paris:20260608T090000` /
  `DTEND;TZID=Europe/Paris:20260608T100000` est stocke en UTC interne
  `07:00Z-08:00Z` et rendu `09:00-10:00`, pas `11:00-12:00`;
- un evenement `DTSTART;VALUE=DATE:20260608` /
  `DTEND;VALUE=DATE:20260609` produit un seul `CalendarEvent.all_day` et le
  rendu affiche `Toute la journee`, sans `02:00-02:00`;
- un evenement UTC `07:00Z` continue de se rendre `09:00` en timezone
  `Europe/Paris`;
- aucune preuve Lot 5A.2 ne lit Nextcloud live, CalDAV live ou secret reel.

Preuve Lot 5A.3 locale:

- avec `FRIDA_TIMEZONE=Europe/Paris` et `now=2026-06-08T10:00:00Z`,
  `today` est `2026-06-07T22:00:00Z -> 2026-06-08T22:00:00Z` et `tomorrow`
  est `2026-06-08T22:00:00Z -> 2026-06-09T22:00:00Z`;
- `canonical_time_windows` est transmis a l'agent Agenda dans le payload modele;
- un plan `read_today` / `read_tomorrow` utilisant la fenetre canonique est
  accepte, tandis qu'une fenetre UTC brute `00Z -> 00Z` est rejetee avec
  `agenda_agent_time_window_mismatch`;
- le rejet precede toute lecture CalDAV/client read-only et son observabilite
  ne contient pas la fenetre brute rejetee;
- un evenement journee entiere de test n'est lu/rendu que via la fenetre locale
  canonique;
- aucune preuve Lot 5A.3 ne lit Nextcloud live, CalDAV live ou secret reel.

Preuve Lot 5B partielle:

- artefact:
  `app/docs/states/baselines/agenda-smokes/frida-agenda-lot5b-live-readonly-20260608T162407Z.jsonl`;
- le schema OpenRouter Agenda est rendu compatible avec
  `response_format.type=json_schema` et `strict=true`: les params d'outils
  declarent toutes leurs proprietes comme `required` nullable, et le
  validateur ignore les `null` avant execution;
- le probe provider content-free observe `status_code=200` apres correction,
  sans prompt brut ni payload modele brut dans l'artefact;
- runtime settings redacted OK: `agenda_agent.mode` peut passer
  temporairement a `active`, `caldav_account=tof`, secret CalDAV dedie
  configure via source `db_encrypted`, aucune valeur ni `value_encrypted`
  exposee;
- les cas `read_today` et `read_tomorrow` produisent un JSON agent valide et
  declenchent un acces CalDAV/Nextcloud read-only, sans mutation;
- le transport CalDAV echoue ensuite en `caldav_unauthorized` sur le PROPFIND:
  aucun final lock Agenda n'est autorise, aucun message assistant Agenda avec
  meta Agenda n'est persiste pour ces lectures, et les cases Lot 5B restent
  ouvertes;
- le smoke de reprise contexte prouve un tour suivant avec timestamp et
  Delta-T, mais cette preuve seule ne ferme pas Lot 5B sans lecture CalDAV
  reussie;
- politique appliquee: comme le verdict global est `partial`, le mode runtime
  est remis `off`;
- aucun titre, lieu, description, UID, ETag, URL/path CalDAV, ICS, prompt brut,
  dialogue brut, cookie, Authorization, token ou app-password n'est stocke dans
  l'artefact.

Preuve Lot 5B relance:

- Sauron a cree un nouvel app-password Nextcloud dedie `frida-agenda-agent`
  pour le compte humain `tof` et l'a depose dans `agenda_agent` en
  `db_encrypted`, sans afficher la valeur;
- `agenda_agent.mode` reste `off` apres depot jusqu'au smoke live;
- un PROPFIND status-only sur CalDAV repond `207`, sans header, body, URL/path
  CalDAV complet, token, cookie ou app-password dans la sortie;
- les payloads Lot 5 exposent maintenant les champs content-free attendus pour
  la preuve: `read_execution_status`, `read_execution_reason_code`,
  `read_tool_count`, `read_tool_names`, `error_class`, `caldav_access`,
  `nextcloud_access`, `final_response_override`, presence meta Agenda et
  verdict `meta_content_free`;
- `search_events` est verrouille comme lecture bornee: l'agent doit produire
  `event_query_range` pour constituer le pool de recherche puis `event_search`
  avec `query`, `limit` et optionnellement `calendar_id`, sans `start`, `end`
  ni `timezone` dans les params `event_search`.
- artefact live final:
  `app/docs/states/baselines/agenda-smokes/frida-agenda-lot5b-live-readonly-20260608T181853Z.jsonl`;
- verdict final `met`: `read_today`, `read_tomorrow`, `search_events`,
  contexte suivant / Delta-T, timestamp, message assistant normal,
  `AssistantResponseOverride`, meta Agenda content-free et Memory eligible par
  contrat sont prouves;
- `read_today` et `read_tomorrow` executent `event_query_range` en CalDAV
  read-only; `search_events` execute `event_query_range` puis `event_search`;
- les records live portent `read_execution_status`,
  `read_execution_reason_code`, `read_tool_count`, `read_tool_names`,
  `error_class`, `caldav_access`, `nextcloud_access`,
  `final_response_override`, `agenda_meta_present` et `meta_content_free`;
- `mutation_attempted=false` partout et le mode final reste `active` car le
  verdict global est `met`;
- aucun titre, lieu, description, invite, UID, ETag, raw ICS, URL/path CalDAV,
  Authorization, cookie, token, app-password, prompt brut ou dialogue brut
  n'est stocke dans l'artefact.

Preuve content-free minimale:

- autorise: schema version, toggle, mode, methode produit, noms d'outils,
  statut, reason code, calendar id court, flag calendrier familial, fenetre
  start/end, timezone, counts, hashes courts, pending action id, niveau de
  confirmation, booleens de presence et valeurs redacted;
- interdit: app-password, mot de passe principal, cookie, header Authorization,
  token, URL CalDAV complete, UID brut, ETag brut, ICS brut, titre,
  description, lieu, invite, payload modele brut, prompt complet, dialogue
  complet et evenement personnel brut.

Read-only:

- lister les calendriers sous forme ids courts et counts;
- lire une fenetre de test anonymisee;
- prouver `today/tomorrow` avec `FRIDA_TIMEZONE`;
- prouver que les reponses Agenda entrent dans le dialogue suivant;
- prouver timestamp, meta content-free, trace Memory eligible et absence de
  payload ICS en logs.

Mutation:

- utiliser uniquement un calendrier de test ou evenement de test anonymise;
- prouver pending action;
- prouver refus sans confirmation;
- prouver creation/modification apres confirmation;
- prouver suppression seulement avec confirmation renforcee;
- prouver rollback quand possible, ou documenter la limite quand CalDAV ne le
  permet pas automatiquement.

NO-GO mutations utilisateur reelles tant que:

- le secret runtime dedie n'est pas configure en redacted;
- la confirmation humaine n'est pas testee sur le type de mutation utilisateur
  reel vise;
- les logs/content-free ne sont pas prouves pour le lot live vise;
- le calendrier familial ou non classifie n'a pas de confirmation claire et
  renforcee quand la politique l'exige;
- l'update live reste non autorise tant qu'une preuve live separee ne valide pas
  la preservation ICS source sans toucher d'evenement personnel.
