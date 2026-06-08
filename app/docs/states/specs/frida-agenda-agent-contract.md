# Frida Agenda Agent Contract

Statut: spec vivante
Date: 2026-06-08
Classement: `app/docs/states/specs/`
TODO produit: `app/docs/todo-todo/product/frida-agenda-agent.md`
Portee: contrat cible du futur agent Agenda Frida. Lots 1-3.2 livrent seulement
toggle no-op, configuration redacted et outils read-only non branches, sans
agent Agenda reel ni acces CalDAV live.

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

Ce contrat ne code pas l'agent Agenda reel.

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
- CalDAV fonctionne cote serveur via `/remote.php/dav/`;
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
  complete RFC 5545, pas de `VTIMEZONE`/`TZID` avance, pas de validation live
  Nextcloud/macOS tant qu'un probe content-free separe n'est pas autorise.

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
  UID, ETag, ICS brut, Authorization, cookie, token ou app-password;
- une mutation sans `confirmation_required=true` est invalide;
- une suppression exige `confirmation_level=reinforced`;
- le calendrier familial exige un risk flag dedie et une confirmation claire
  pour toute mutation;
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
- cree une action pending avec expiration;
- la reponse visible doit expliciter ce qui serait cree, modifie ou supprime;
- la meta durable reste content-free autant que possible.

Mutation:

- impossible sans confirmation humaine explicite;
- la confirmation doit viser une proposition precise;
- la confirmation doit etre recue dans un tour ulterieur ou dans une UI dediee;
- creation et modification exigent confirmation simple;
- suppression exige confirmation renforcee;
- calendrier familial exige prudence renforcee et confirmation claire.

## 11. Etat temporaire de proposition

Le stockage cible des propositions ne doit pas etre un dump permanent de
calendrier.

Modele recommande:

- table ou store futur `agenda_pending_actions`;
- TTL court obligatoire;
- contenu minimal necessaire a l'execution: operation, calendrier cible,
  champs normalises du brouillon, identifiants CalDAV cibles, ETag si utile,
  create/update/delete, risques, create_ts, expires_ts;
- suppression du pending apres confirmation, annulation ou expiration;
- `message.meta` ne porte qu'un pointeur content-free:
  `pending_action_id`, operation, calendar id court, confirmation level,
  risk flags, hash court, expiration;
- les details humains restent dans la reponse visible et, si necessaire, dans
  le pending store temporaire, pas dans les logs/dashboard/JSONL.

Si aucun store temporaire n'est livre dans un premier lot runtime, les mutations
doivent rester NO-GO. Relire uniquement le dialogue pour reconstruire une
mutation est trop fragile.

## 12. Restitution visible et contexte suivant

La reponse Agenda visible suit le contrat agentic response surface:

1. `surface_intro` si non vide;
2. reponse naturelle Frida;
3. limites utiles;
4. question de clarification ou demande de confirmation si necessaire;
5. `surface_outro` si non vide.

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
  `surface_intro` et `surface_outro`;
- `surface_intro` et `surface_outro` doivent etre des strings courts, jamais
  `null`;
- les outils inconnus, hors methode produit, mutatifs ou avec params interdits
  sont refuses avant tout reseau;
- les mutations demandees exigent confirmation humaine et les suppressions
  exigent confirmation renforcee;
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

NO-GO mutation tant que:

- le secret runtime dedie n'est pas configure;
- le pending store n'existe pas;
- la confirmation humaine n'est pas testee;
- les logs content-free ne sont pas prouves;
- le calendrier familial n'est pas protege par une confirmation claire.
