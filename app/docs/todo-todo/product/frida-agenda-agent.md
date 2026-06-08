# Frida Agenda Agent - TODO produit

Statut: TODO actif au 2026-06-08
Spec source: `app/docs/states/specs/frida-agenda-agent-contract.md`
Baseline Lot 0: `app/docs/states/baselines/frida-agenda-agent-lot0-baseline-2026-06-08.md`
Fixtures Lot 0: `app/docs/states/baselines/agenda-fixtures/`
Portee: roadmap runtime bornee du futur agent Agenda; Lots 1-4 livrent
toggle no-op, configuration redacted, outils read-only non branches et agent
JSON valide sous garde-fous, sans lecture CalDAV live ni mutation.

Question prealable: existe-t-il un meilleur plan ?

Oui: le meilleur plan pour ce cran est docs-only. Il faut d'abord cartographier
FridaDev et Nextcloud, figer le contrat, puis lister les lots runtime futurs.
Coder l'agent Agenda maintenant serait premature: le risque serait de reproduire
une couche de regex locales au lieu d'une capacite agentique bornee.

## Decision produit inscrite

- [x] Frida parle.
- [x] L'agent Agenda travaille.
- [x] Le deterministe protege.
- [x] Toggle Agenda obligatoire.
- [x] Toggle Agenda off: Frida repond normalement, sans acces agenda.
- [x] Toggle Agenda on: Frida peut deleguer a l'agent Agenda.
- [x] Lecture et proposition sont autorisees avec le toggle Agenda.
- [x] Creation/modification seulement apres confirmation explicite.
- [x] Suppression jamais autonome, confirmation renforcee obligatoire.
- [x] Calendrier familial: prudence renforcee.
- [x] Aucun agent Agenda reel ni acces CalDAV n'est livre par ce document.

## Audit existant FridaDev

- [x] Toggle Biblio identifie: `app/web/chat_biblio_mode.js` porte
  `biblio_enabled` cote payload chat et persistance navigateur locale.
- [x] Surface UI cible identifiee: `app/web/index.html` et `app/web/app.js`
  injectent les payloads de toggles dans `POST /api/chat`.
- [x] Agent Biblio identifie: `app/biblio/librarian_agent_contract.py` porte
  schema JSON, validation locale, modes et budgets.
- [x] Methodes produit Biblio identifiees:
  `app/biblio/librarian_product_methods.py` separe methodes produit et outils.
- [x] Tools Biblio identifies: `app/biblio/librarian_tools.py` expose un
  registre GET-only allowliste avec observabilite content-free.
- [x] Runtime Biblio identifie: `app/biblio/chat_runtime.py` gere decision,
  etat conversationnel, execution et final lock.
- [x] Branchement chat identifie: `app/core/chat_service.py` appelle Biblio
  avant la preparation finale du prompt et avant `run_llm_exchange()`.
- [x] Surface agentique identifiee:
  `app/docs/states/specs/agentic-response-surface-contract.md`.
- [x] Override final identifie: `app/core/chat_llm_flow.py` persiste un
  `AssistantResponseOverride` comme message assistant normal.
- [x] Stockage messages identifie: `conversation_messages` porte
  `timestamp TIMESTAMPTZ NOT NULL` et `meta JSONB`.
- [x] Contexte suivant identifie: `conversations_prompt_window` reprend les
  messages user/assistant avec labels Delta-T.
- [x] Memory identifiee: `memory_traces_summaries.save_new_traces()` rend les
  messages assistant normaux eligibles aux traces et embeddings.
- [x] Resume identifie: `summarizer._raw_dialogue()` inclut les messages
  assistant normaux non encore resumes.
- [x] Observabilite identifiee: les logs/dashboard/JSONL doivent rester
  content-free et ne pas exposer les contenus Agenda bruts.

## Audit existant Nextcloud / Agenda

- [x] Rapport source lu:
  `/opt/platform/_codex_reports/nextcloud-frida-agenda-mail-roadmap-20260607T103442Z.md`.
- [x] Nextcloud est le socle prioritaire pour Agenda/Mail/Files.
- [x] Calendar est installe et active.
- [x] CalDAV fonctionne via `/remote.php/dav/`.
- [x] Le bypass DAV est borne aux routes DAV necessaires; l'interface web reste
  derriere Authelia.
- [x] Les clients natifs doivent utiliser des app-passwords nommes, dedies et
  revocables.
- [x] Aucun mot de passe principal humain ne doit entrer dans Frida.
- [x] Aucun acces DB direct Nextcloud n'est autorise.
- [x] Le calendrier familial est un objet humain partage, pas une ressource
  cachee appartenant a Frida.
- [x] Contexte utilisateur courant note: calendrier visible sur macOS et iPhone,
  evenements synchronises, calendrier familial existant.
- [x] Les frottements Apple/Amandine restants sont classes clients/config, pas
  blocage d'architecture serveur.
- [x] Les preuves serveur futures ne doivent pas dependre d'iOS ou macOS.

## Decisions V1 tranchees

- [x] Identite CalDAV V1: compte humain `tof` + app-password dedie Frida
  Agenda.
- [x] Pas de compte service Nextcloud `frida` pour l'Agenda V1.
- [x] Un utilisateur `frida` pourra etre envisage plus tard pour Files /
  repertoire Frida, mais ce n'est pas le sujet Agenda actuel.
- [x] Ne pas creer l'app-password dans ce lot.
- [x] Ne jamais afficher ni stocker la valeur de l'app-password dans docs,
  logs, JSONL, prompt LLM, sortie terminal ou reponse.
- [x] Privacy V1: instance personnelle locale/OVH privee; les reponses Agenda
  visibles suivent le contrat memoire normal de Frida.
- [x] Pas de redaction speciale memoire pour l'Agenda V1, hors secrets et
  observabilite content-free.
- [x] Le contenu visible que l'utilisateur demande a Frida peut etre memorise
  comme dialogue normal.
- [x] Les frottements Amandine/macOS/iOS restent de l'administration client.
- [x] Amandine/Apple ne bloque pas le chantier code Agenda.
- [x] Les preuves serveur futures ne dependent toujours pas d'iOS/macOS.

## Verrou architecture applicative Agenda

- [x] Tous les nouveaux fichiers applicatifs Agenda doivent etre ranges dans un
  module dedie au meme niveau que `app/biblio/`.
  Nom cible actuel: `app/agenda/`.
- [x] `app/agenda/` est le repertoire calendrier/agenda. La logique Agenda ne
  doit pas etre dispersee dans `app/core/`, `app/web/`, `app/admin/` ou ailleurs,
  sauf pour les points de branchement strictement necessaires.
- [x] Pour les nouveaux fichiers Agenda, aucun fichier ne doit devenir un gros
  fichier fourre-tout.
- [x] Regle pratique: si un nouveau fichier Agenda approche ou depasse 600
  lignes, le decouper par responsabilite avant commit.
- [x] Interdits: `utils.py`, `helpers.py` generique, ou module qui melange agent
  contract, CalDAV, runtime chat, pending store, observabilite et rendu.

## Invariants securite

- [ ] Ne jamais utiliser la DB Nextcloud depuis Frida.
  Preuve attendue: tests interdisant tout client DB Nextcloud et docs de
  configuration sans DSN Nextcloud.
- [ ] Ne jamais utiliser de mot de passe principal.
  Preuve attendue: runtime settings/secrets n'acceptent qu'un secret dedie et
  redacted.
- [ ] Utiliser le compte humain `tof` avec un app-password dedie Frida Agenda,
  nomme et revocable.
  Preuve attendue: presence booleenne redacted, aucune valeur en logs/docs, pas
  de compte service `frida` pour Agenda V1.
- [ ] Garder les secrets uniquement cote runtime/config serveur.
  Preuve attendue: payload agent et observabilite sans secret.
- [ ] Utiliser CalDAV comme frontiere d'acces.
  Preuve attendue: tools bornes `calendar_list`, `event_query_range`,
  `event_get`, puis mutations confirmees.
- [ ] Refuser toute ecriture sans confirmation humaine.
  Preuve attendue: smoke de refus mutation sans pending action confirme.
- [ ] Refuser toute suppression autonome.
  Preuve attendue: suppression impossible hors confirmation renforcee.
- [ ] Renforcer la prudence sur le calendrier familial.
  Preuve attendue: risk flag `family_calendar` et confirmation claire exigee.
- [ ] Refuser toute creation d'evenement invisible ou ambigu.
  Preuve attendue: clarification si calendrier, date, fuseau ou titre cible est
  ambigu.
- [ ] Ne jamais scraper l'UI Nextcloud pour agir.
  Preuve attendue: aucune dependance navigateur Nextcloud dans le runtime.
- [ ] Ne jamais faire dependre la preuve serveur d'iOS/macOS.
  Preuve attendue: smokes CalDAV serveur content-free.
- [ ] Garder tout live proof content-free ou anonymise.
  Preuve attendue: artefacts sans titre, description, invite, lieu ou ICS brut.
- [ ] Ne jamais mettre secret, token, app-password, cookie ou evenement personnel
  brut dans JSONL/docs.
  Preuve attendue: scan anti-fuite et revue manuelle.

## Architecture cible

- [x] Ajouter un toggle frontend `agenda_enabled`, off par defaut, voisin de
  Biblio.
  Preuve livree: Lot 1, payload `agenda_enabled`, off no-op et on degradant
  proprement sans runtime agent.
- [x] Ajouter une section runtime `agenda_agent`.
  Preuve livree: Lot 2, schema runtime settings, seed, API admin dediee et
  read-model redacted.
- [x] Ajouter une source de secret CalDAV dediee au compte `tof`, jamais
  exposee au LLM.
  Preuve livree: source dediee redacted/source-only, aucun app-password cree
  par le code.
- [x] Ajouter le module applicatif `app/agenda/` avec responsabilites livrees
  separees: runtime chat no-op, runtime config, modeles CalDAV, client read-only,
  parser ICS, tools read-only et observability.
  Preuve livree: fichiers separes par responsabilite, pas de `utils.py`.
- [ ] Ajouter les composants Agenda futurs non livres dans `app/agenda/`:
  agent contract, methodes produit, pending store, rendu/final lock.
  Preuve attendue: aucun fichier fourre-tout et branchements minimaux.
- [x] Brancher l'Agenda dans `chat_service` a cote de Biblio.
  Preuve livree: toggle absent/off = no-op strict; toggle on = appel runtime
  Agenda borne, sans prompt lane ni final response override.
- [ ] Faire passer les reponses finales Agenda par `AssistantResponseOverride`.
  Preuve attendue: message assistant DB, timestamp, meta, Memory et contexte
  suivant prouves.
- [ ] Ne pas brancher l'Agenda dans Memory, summary ou prompt window directement.
  Preuve attendue: aucun canal parallele; message assistant normal suffit.
- [ ] Definir un final lock Agenda.
  Preuve attendue: pas de double reponse, pas de contenu technique visible.
- [ ] Definir une lane prompt Agenda seulement pour les cas sans final lock, si
  elle est necessaire.
  Preuve attendue: lane bornee, pas de payload ICS brut, pas de prompt complet
  dans observabilite.
- [ ] Ajouter un pending store temporaire pour propositions.
  Preuve attendue: TTL, suppression apres confirm/cancel/expire, meta
  content-free.
- [ ] Refuser les mutations tant que le pending store n'existe pas.
  Preuve attendue: tests de no-go mutation.

## Contrat JSON agent

- [x] Definir `schema_version=frida_agenda_agent_v1`.
  Preuve livree: validation accepte version exacte et refuse autre version.
- [x] Definir `product_method` obligatoire.
  Preuve livree: sortie sans methode connue rejetee.
- [x] Definir `calendar_scope` structurel.
  Preuve livree: champs stricts `calendar_ids`, `family_calendar`,
  `ambiguity`; les clarifications produit restent Lot 5+.
- [x] Definir `time_scope` structurel.
  Preuve livree: champs stricts `kind`, `start`, `end`, `timezone`,
  `ambiguity`; la resolution produit de `today/tomorrow` reste Lot 5.
- [x] Definir `tool_calls` comme sous-plan technique allowliste.
  Preuve livree: outil inconnu, outil hors methode, methode non-GET et params
  interdits refuses avant reseau; URLs/paths CalDAV bruts, UID/e-mail brut et
  marqueurs secret/ICS rejetes dans les valeurs techniques, sans dependance a
  la casse; `event_id` refuse aussi les formes UID-like `uid:*` et `uid=*`.
- [x] Definir `mutation`.
  Preuve livree: mutation demandee sans confirmation rejetee; suppression
  exige confirmation renforcee; `kind=create|update|delete` incoherent sur une
  methode read-only rejete meme si `requested=false`.
- [x] Definir `answer_mode`, `risk_flags`, `fallback_reason`.
  Preuve livree: champs codes stricts et observations content-free.
- [x] Definir `surface_intro` et `surface_outro`.
  Preuve livree: champs string, courts, jamais `null`.
- [x] Interdire le raw JSON modele en logs.
  Preuve livree: observabilite compacte avec hashes, counts et flags.

## Methodes produit Agenda

### Lecture read-only

- [ ] `AG-READ-01` lire aujourd'hui.
  Preuve attendue: fenetre locale du jour, counts content-free, reponse
  naturelle sans dump ICS.
- [ ] `AG-READ-02` lire demain.
  Preuve attendue: resolution `demain` via `FRIDA_TIMEZONE`, pas UTC brut.
- [ ] `AG-READ-03` lire une date explicite.
  Preuve attendue: date explicite, clarification si fuseau ou calendrier
  ambigu.
- [ ] `AG-READ-04` lire une semaine.
  Preuve attendue: range borne, limite de resultats, synthese naturelle.
- [ ] `AG-READ-05` chercher un rendez-vous.
  Preuve attendue: recherche bornee, not_found propre si rien.
- [ ] `AG-READ-06` chercher par personne, lieu ou mot-cle.
  Preuve attendue: pas de recherche globale non bornee, pas de contenu en logs.
- [ ] `AG-READ-07` retrouver les details pratiques d'un evenement.
  Preuve attendue: evenement unique relu; ambiguite si plusieurs candidats.
- [ ] `AG-READ-08` resumer la journee.
  Preuve attendue: resume utile, pas de liste brute non demandee.
- [ ] `AG-READ-09` reperer les trous/disponibilites.
  Preuve attendue: disponibilites derivees d'une fenetre bornee.

### Clarification

- [ ] `AG-CLAR-01` date ambigue.
  Preuve attendue: question de clarification, aucune requete large.
- [ ] `AG-CLAR-02` calendrier ambigu.
  Preuve attendue: choix demande entre calendriers accessibles.
- [ ] `AG-CLAR-03` evenement introuvable.
  Preuve attendue: not_found propre et proposition de precision.
- [ ] `AG-CLAR-04` plusieurs evenements possibles.
  Preuve attendue: choix humain avant details ou mutation.
- [ ] `AG-CLAR-05` demande trop vague.
  Preuve attendue: clarification sans ecriture.
- [ ] `AG-CLAR-06` demande dangereuse ou hors perimetre.
  Preuve attendue: refus ou clarification, reason code content-free.

### Proposition sans ecriture

- [ ] `AG-PROP-01` proposer un evenement a creer.
  Preuve attendue: pending action creee, aucune ecriture CalDAV.
- [ ] `AG-PROP-02` proposer une modification.
  Preuve attendue: cible relue, proposition affichee, aucune ecriture.
- [ ] `AG-PROP-03` proposer une suppression.
  Preuve attendue: suppression indiquee comme non executee, confirmation
  renforcee demandee.
- [ ] `AG-PROP-04` proposer un creneau libre.
  Preuve attendue: range borne, calendrier explicite.
- [ ] `AG-PROP-05` proposer un deplacement.
  Preuve attendue: conflit/availability de base et pending action.

### Ecriture confirmee

- [ ] `AG-WRITE-01` creer un evenement apres confirmation.
  Preuve attendue: pending action confirme, CalDAV PUT, relecture content-free.
- [ ] `AG-WRITE-02` modifier un evenement apres confirmation.
  Preuve attendue: ETag ou equivalent relu, CalDAV update, conflit gere.
- [ ] `AG-WRITE-03` supprimer un evenement apres confirmation renforcee.
  Preuve attendue: cible relue juste avant, confirmation renforcee, delete
  borne.
- [ ] `AG-WRITE-04` rollback/annulation si techniquement possible.
  Preuve attendue: rollback documente; si impossible, limite explicite et
  action corrective manuelle documentee.

### Contexte et memoire

- [ ] `AG-CTX-01` les reponses Agenda entrent comme reponses normales de Frida.
  Preuve attendue: message assistant DB avec timestamp.
- [ ] `AG-CTX-02` timestamps obligatoires.
  Preuve attendue: `conversation_messages.timestamp` non nul.
- [ ] `AG-CTX-03` le contexte LLM suivant voit les reponses Agenda comme
  dialogue.
  Preuve attendue: payload de reprise avec Delta-T, content-free si exporte.
- [ ] `AG-CTX-04` Memory/resume/embeddings suivent les contrats Frida.
  Preuve attendue: trace eligible ou echec embedding non bloquant.
- [ ] `AG-CTX-04bis` Privacy V1: pas de redaction speciale memoire pour les
  reponses Agenda visibles.
  Preuve attendue: reponse visible traitee comme dialogue normal, secrets
  exclus, observabilite content-free.
- [ ] `AG-CTX-05` pas de dump brut permanent de calendrier.
  Preuve attendue: pas d'ICS, pas de liste brute non demandee, pas de payload
  CalDAV dans meta/logs.
- [ ] `AG-CTX-06` meta content-free pour preuves.
  Preuve attendue: ids courts, counts, hashes, reason codes seulement.

## Tools CalDAV cibles

- [x] `calendar_list`.
  Preuve attendue: calendriers accessibles, ids courts, permissions.
- [ ] `calendar_get`.
  Preuve attendue: verification calendrier cible et droits.
- [x] `event_query_range`.
  Preuve attendue: requete bornee par calendrier et fenetre.
- [x] `event_search`.
  Preuve attendue: recherche bornee, limite de resultats.
- [x] `event_get`.
  Preuve attendue: evenement cible relu avec ETag ou equivalent.
- [ ] `availability_query`.
  Preuve attendue: disponibilites derivees sans route non prouvee.
- [ ] `event_draft_validate`.
  Preuve attendue: normalisation sans ecriture.
- [ ] `pending_action_create`.
  Preuve attendue: TTL et meta content-free.
- [ ] `pending_action_get`.
  Preuve attendue: confirmation cible une proposition precise.
- [ ] `pending_action_cancel`.
  Preuve attendue: annulation/expiration sans mutation.
- [ ] `event_create_confirmed`.
  Preuve attendue: CalDAV PUT apres confirmation.
- [ ] `event_update_confirmed`.
  Preuve attendue: update avec protection concurrence.
- [ ] `event_delete_confirmed`.
  Preuve attendue: suppression seulement confirmation renforcee.

## Lots runtime futurs

### Lot 0 - Baseline docs et fixtures anonymes

- [x] Relire spec Agenda et TODO.
- [x] Creer des fixtures CalDAV anonymes cote repo, sans calendrier test
  Nextcloud reel.
- [x] Definir la preuve content-free attendue.
- [x] Confirmer le no-go sur evenements personnels.

### Lot 1 - Toggle UI et no-op backend

- [x] Ajouter le bouton Agenda off par defaut.
- [x] Envoyer `agenda_enabled`.
- [x] Backend toggle off = no-op prouve.
- [x] Backend toggle on sans runtime agent = degradation propre.
- [x] Aucun acces CalDAV dans ce lot.

### Lot 2 - Runtime settings et secrets redacted

- [x] Ajouter section `agenda_agent`.
- [x] Ajouter source secret CalDAV dediee au compte `tof`, redacted.
- [x] Ajouter validations admin.
- [x] Ajouter routes admin dediees `GET/PATCH/POST validate` pour
  `agenda-agent`.
- [x] Borner les modes Agenda V1 a `off` et `active` seulement.
- [x] Ajouter tests anti-fuite.
- [x] Ne pas creer d'app-password dans le code.

### Lot 3 - Outils CalDAV read-only

- [x] Implementer `calendar_list`.
- [x] Implementer `event_query_range`.
- [x] Implementer `event_get`.
- [x] Implementer `event_search`.
- [x] Implementer observations content-free.
- [x] Prouver aucun payload ICS dans logs, metas ou read-models de test.

### Lot 3.1 - Correctifs outils read-only avant agent

- [x] Ajouter un support borne des occurrences ICS recurrentes dans la fenetre
  demandee.
  Preuve livree: tests RRULE `DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`, `COUNT`,
  `INTERVAL`, `EXDATE` et `RECURRENCE-ID` sur fixtures synthetiques.
- [x] Refuser proprement les regles recurrentes non supportees.
  Preuve livree: test d'erreur `IcsRecurrenceUnsupportedError` sans payload ICS
  brut ni UID dans l'erreur.
- [x] Brancher `event_get` sur le client read-only quand l'evenement connu porte
  un `caldav_path` exploitable.
  Preuve livree: test `event_get` avec transport fake `GET`, sans accepter UID
  ou URL arbitraire.
- [x] Refuser un `event_get` CalDAV sans `caldav_path` connu.
  Preuve livree: test d'erreur propre depuis un evenement deja en state mais
  sans chemin CalDAV.
- [x] Valider les statuts HTTP CalDAV attendus.
  Preuve livree: tests 401/403/404/500 et GET 404 avec erreur structuree
  content-free, sans body brut.
- [x] Corriger les cases TODO hautes deja livrees par Lots 1-3.
  Preuve livree: toggle, runtime settings, source redacted et module
  `app/agenda/` coches sans anticiper les lectures live Lot 5+.

### Lot 3.2 - RRULE realistes avant agent

- [x] Auditer les bibliotheques RRULE disponibles sans installer de dependance
  lourde.
  Preuve livree: `dateutil.rrule` absent cote hote et conteneur
  `platform-fridadev`.
- [x] Ne pas faire de probe live CalDAV.
  Preuve livree: aucune configuration secret/app-password lue, aucun acces
  Nextcloud/CalDAV live, tests synthetiques uniquement.
- [x] Decouper l'expansion RRULE dans un fichier Agenda dedie.
  Preuve livree: `app/agenda/rrule_expander.py`, pas de `utils.py` ni
  `helpers.py`, fichiers applicatifs Agenda sous 600 lignes.
- [x] Supporter les formes hebdomadaires realistes `BYDAY`.
  Preuve livree: tests `FREQ=WEEKLY;BYDAY=MO` et `BYDAY=MO,WE`.
- [x] Supporter les formes mensuelles realistes `BYMONTHDAY`, `BYDAY` et
  `BYSETPOS`.
  Preuve livree: tests `FREQ=MONTHLY;BYMONTHDAY=...`,
  `FREQ=MONTHLY;BYDAY=...` et `FREQ=MONTHLY;BYDAY=...;BYSETPOS=...`.
- [x] Supporter la forme annuelle `BYMONTH` + `BYMONTHDAY`.
  Preuve livree: test `FREQ=YEARLY;BYMONTH=...;BYMONTHDAY=...`.
- [x] Garder `COUNT`, `UNTIL`, `INTERVAL`, `EXDATE` et `RECURRENCE-ID` bornes.
  Preuve livree: tests de fenetre bornee, intervalle, until, exclusion et
  override recurrent.
- [x] Garder les erreurs RRULE non supportees content-free.
  Preuve livree: test d'erreur sur partie non supportee sans payload ICS, UID,
  titre, lieu ou description.

### Lot 4 - Agent JSON active sous garde-fous

- [x] Definir schema `frida_agenda_agent_v1`.
- [x] Ajouter validation stricte.
- [x] Consommer les modes runtime Lot 2 `off/active` sans reintroduire
  `shadow` ou `candidate`.
- [x] Ajouter fallback deterministe propre.
- [x] Prouver JSON absent/invalide/hors schema.
- [x] Prouver que Lot 4 ne fait aucun acces CalDAV/Nextcloud live, ne lit aucun
  secret et ne tente aucune mutation.
- [x] Durcir la validation des params Lot 4.
  Preuve livree: `calendar_id` URL/path CalDAV brut rejete, `event_id`
  UID/e-mail brut ou UID-like rejete, `event_id` local court accepte, marqueurs
  ICS/secrets case-insensitive rejetes dans `query`.
- [x] Durcir la coherence mutations/methodes Lot 4.
  Preuve livree: methode read-only avec `mutation.kind=create` et
  `requested=false` rejetee; propositions et confirmations restent bornees.

### Lot 5 - Lecture read-only active

- [ ] Brancher lecture Agenda quand toggle on et mode autorise.
- [ ] Prouver lire aujourd'hui.
- [ ] Prouver lire demain.
- [ ] Prouver recherche evenement.
- [ ] Prouver details evenement unique.
- [ ] Prouver contexte suivant, timestamp, Memory eligible.

### Lot 6 - Propositions et pending store

- [ ] Ajouter pending store temporaire avec TTL.
- [ ] Ajouter proposition creation.
- [ ] Ajouter proposition modification.
- [ ] Ajouter proposition suppression.
- [ ] Prouver aucune ecriture CalDAV dans les propositions.

### Lot 7 - Confirmations et mutations

- [ ] Creation apres confirmation.
- [ ] Modification apres confirmation.
- [ ] Suppression apres confirmation renforcee.
- [ ] Protection calendrier familial.
- [ ] Gestion conflit ETag ou equivalent.
- [ ] Rollback ou limite de rollback documentee.

### Lot 8 - Observabilite, dashboard, smokes live anonymises

- [ ] JSONL content-free.
- [ ] Dashboard/read-model sans contenu Agenda brut.
- [ ] Smokes serveur sans iOS/macOS.
- [ ] Scan secrets/logs.
- [ ] Validation conversation reelle anonymisee.

## Auto-audit permanent

- [ ] Pas de derive vers script/regex au lieu d'agent Agenda.
- [ ] Toggle Agenda present.
- [ ] Confirmations humaines presentes.
- [ ] Lecture, proposition et ecriture separees.
- [ ] Calendrier familial traite comme risque renforce.
- [ ] Aucun secret dans prompt LLM.
- [ ] Aucune DB directe Nextcloud.
- [ ] Coherence avec Biblio et la surface agentique.
- [ ] Coherence avec `AGENTS.md`.
- [ ] TODO cochable et non vague.
- [ ] Cases ouvertes/fermees coherentes.

## Hors-scope

- [ ] Ne pas coder l'agent Agenda dans le lot de cadrage.
- [ ] Ne pas creer d'app-password.
- [ ] Ne pas lire ou afficher des evenements reels en clair.
- [ ] Ne pas modifier Nextcloud.
- [ ] Ne pas modifier Caddy/Authelia.
- [ ] Ne pas modifier Calendar/Mail/Contacts.
- [ ] Ne pas faire de test live avec de vrais evenements personnels.
- [ ] Ne pas creer, modifier ou supprimer un evenement.
- [ ] Ne pas toucher a Biblio.
- [ ] Ne pas creer un agent Mail.
