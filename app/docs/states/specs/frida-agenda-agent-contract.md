# Frida Agenda Agent Contract

Statut: spec vivante docs-only
Date: 2026-06-08
Classement: `app/docs/states/specs/`
TODO produit: `app/docs/todo-todo/product/frida-agenda-agent.md`
Portee: contrat cible du futur agent Agenda Frida, sans patch runtime dans ce
lot.

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

Ce contrat ne code pas l'agent Agenda.

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

Mode runtime agent:

- section cible: `agenda_agent`;
- modes recommandes: `off`, `shadow`, `candidate`, `active`;
- `off`: aucun appel modele agent;
- `shadow`: l'agent peut etre evalue sans influencer la reponse;
- `candidate`: l'agent peut proposer un plan compare au deterministe;
- `active`: l'agent peut piloter une methode produit autorisee, sous
  validation deterministe stricte;
- rollback: repasser a `off` doit restaurer le chat normal sans migration,
  rebuild ni purge DB.

Secrets runtime:

- l'app-password CalDAV dediee Frida Agenda pour le compte `tof` est un secret
  serveur;
- elle ne doit pas apparaitre dans le payload agent, le prompt LLM, la reponse,
  les logs, les JSONL, les docs ou les sorties terminal;
- les read-models admin peuvent exposer seulement des booleens de presence et
  sources redacted.

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

Schema cible minimal:

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
- une mutation sans `confirmation_required=true` est invalide;
- une suppression exige `confirmation_level=reinforced`;
- le calendrier familial exige un risk flag dedie et une confirmation claire
  pour toute mutation;
- les champs de surface restent courts et ne remplacent pas le contenu
  verrouille ni les metas.

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
  courts;
- `calendar_get`: verifier un calendrier cible et ses droits;
- `event_query_range`: requete CalDAV bornee par calendrier et fenetre temps;
- `event_search`: recherche bornee derivee de `event_query_range`;
- `event_get`: relire un evenement cible par URL/UID/ETag deja connus;
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
