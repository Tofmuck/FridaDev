# Frida Agenda Agent - TODO produit

Statut: TODO actif au 2026-06-08
Spec source: `app/docs/states/specs/frida-agenda-agent-contract.md`
Baseline Lot 0: `app/docs/states/baselines/frida-agenda-agent-lot0-baseline-2026-06-08.md`
Fixtures Lot 0: `app/docs/states/baselines/agenda-fixtures/`
Portee: roadmap runtime bornee du futur agent Agenda; Lots 1-7D.1 livrent
toggle no-op, configuration redacted, outils read-only, agent JSON valide sous
garde-fous, branchement applicatif read-only et preuve CalDAV live content-free,
propositions/pending store temporaire, confirmations fake Lot 7A et preuve live
write synthetique bornee Lot 7B, puis verrou calendrier familial Lot 7C avant
mutations utilisateur reelles, et update confirme fake/local avec preservation
de l'ICS source Lot 7D/7D.1 sur VEVENT simple non recurrent. Lot 8A/8B livre
l'observabilite content-free et Lot 8bis ajoute la recherche read-only du
prochain evenement futur correspondant a une requete textuelle. Lot 8bis.1
rend le fallback live Agenda agentique via `surface_error` et transmet
`user_display_name=Tof` au contexte d'enonciation agent. Lot 8bis.2 rend les
surfaces read-only coherentes avec le resultat et affiche les evenements
journee entiere multi-jours comme des plages avec duree. Lot 8ter cartographie
les familles de questions Agenda pour guider les prochains lots sans ouvrir
Lot 9. Les smokes cibles du 2026-06-09 produisent une preuve JSONL
content-free. Le correctif cible du 2026-06-09 cloture les quatre familles
partial revelees par le premier smoke et declare une cloture pragmatique Agenda
V1: utilisable au quotidien, a rouvrir seulement sur bug reel, besoin concret
ou decision explicite de nouvelle capacite.

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
- [x] Lot 5B livre l'acces CalDAV live read-only sous garde-fous.
- [x] Lot 7B prouve une creation live synthetique et son rollback delete sur la
  meme cible synthetique; aucune mutation utilisateur reelle n'est autorisee.

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
- [x] CalDAV fonctionne via l'endpoint DAV serveur, sans exposer de chemin DAV
  brut dans les preuves.
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
- [x] Refuser toute ecriture sans confirmation humaine.
  Preuve livree: Lots 7A/7D, `confirm_*` exige pending action, draft prive,
  confirmation coherente et client write injecte; refus sans pending action ou
  sans draft prive avant toute requete.
- [x] Refuser toute suppression autonome.
  Preuve livree: Lots 7A/7B/7C, suppression impossible hors pending action
  verifiee et confirmation renforcee; rollback live limite a l'evenement
  synthetique cree dans le meme smoke.
- [x] Renforcer la prudence sur le calendrier familial.
  Preuve livree: Lot 7C/7C.1, risk flag `family_calendar` ou
  `calendar_scope_unverified`, confirmation `reinforced`, detection depuis JSON
  agent ou `CalendarSummary` classifie, refus avant write si confirmation
  simple; `family_calendar=False` sans classification connue ne vaut pas preuve
  non familiale.
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
- [x] Ajouter les composants Agenda `app/agenda/` de Lot 4/5A: agent contract,
  methodes produit, client modele injectable, execution read-only, rendu et
  final lock.
  Preuve livree: fichiers separes par responsabilite, aucun fichier
  fourre-tout, pas de `utils.py`.
- [x] Ajouter le pending store temporaire dans `app/agenda/`.
  Preuve livree: Lot 6/6.1, `pending_store.py`, TTL, meta content-free,
  draft prive temporaire, annulation/expiration et refus d'execution avant
  Lot 7.
- [x] Brancher l'Agenda dans `chat_service` a cote de Biblio.
  Preuve livree: toggle absent/off = no-op strict; toggle on = appel runtime
  Agenda borne; Lot 5A ajoute override final seulement quand lecture read-only
  validee produit une reponse.
- [x] Faire passer les reponses finales Agenda par `AssistantResponseOverride`.
  Preuve livree: test serveur fake de message assistant normal avec timestamp,
  meta content-free et sauvegarde conversation/memory path.
- [x] Ne pas brancher l'Agenda dans Memory, summary ou prompt window
  directement.
  Preuve livree: le message assistant normal suffit; aucun canal Memory
  parallele ajoute.
- [x] Definir un final lock Agenda.
  Preuve livree: `agenda_readonly_response`, pas de double reponse, meta et
  observabilite content-free.
- [ ] Definir une lane prompt Agenda seulement pour les cas sans final lock, si
  elle est necessaire.
  Preuve attendue: lane bornee, pas de payload ICS brut, pas de prompt complet
  dans observabilite.
- [x] Ajouter un pending store temporaire pour propositions.
  Preuve livree: Lot 6/6.1, actions create/update/delete temporaires avec TTL,
  pointeur conversation FridaDev content-free et draft structure prive.
- [x] Refuser les confirmations/mutations tant que Lot 7 n'est pas livre.
  Preuve livree: Lot 6, `confirm_*` cible une pending action mais ne fait
  aucune ecriture CalDAV.

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
  la casse; les proprietes ICS techniques usuelles (`RRULE`, `RECURRENCE-ID`,
  `DTSTART`, `LAST-MODIFIED`, etc.) sont aussi interdites; `event_id` refuse
  les formes UID-like `uid:*` et `uid=*`.
- [x] Definir `mutation`.
  Preuve livree: mutation demandee sans confirmation rejetee; suppression
  exige confirmation renforcee; `kind=create|update|delete` incoherent sur une
  methode read-only rejete meme si `requested=false`.
- [x] Definir `answer_mode`, `risk_flags`, `fallback_reason`.
  Preuve livree: champs codes stricts et observations content-free.
- [x] Definir `surface_intro`, `surface_error` et `surface_outro`.
  Preuve livree: champs string, courts, jamais `null`; `surface_error` est
  obligatoire pour les methodes read-only afin qu'une erreur live Agenda reste
  une surface agentique, pas une phrase deterministe locale.
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

- [x] `AG-PROP-01` proposer un evenement a creer.
  Preuve livree: pending action create creee, reponse assistant normale,
  aucune ecriture CalDAV.
- [x] `AG-PROP-02` proposer une modification.
  Preuve livree: cible locale claire requise via `event_get`, pending action
  update creee, aucune ecriture.
- [x] `AG-PROP-03` proposer une suppression.
  Preuve livree: pending action delete creee avec confirmation renforcee,
  suppression explicitement non executee.
- [ ] `AG-PROP-04` proposer un creneau libre.
  Preuve attendue: range borne, calendrier explicite.
- [ ] `AG-PROP-05` proposer un deplacement.
  Preuve attendue: conflit/availability de base et pending action.

### Ecriture confirmee

- [ ] `AG-WRITE-01` creer un evenement apres confirmation.
  Preuve attendue: pending action confirme, CalDAV PUT, relecture content-free.
- [x] `AG-WRITE-02` modifier un evenement apres confirmation.
  Preuve livree: Lot 7D fake/local, pending draft prive confirme, ETag et ICS
  source obligatoires, `PUT` fake, conflit gere content-free, pas de
  reconstruction depuis le dialogue ni de live write utilisateur.
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
- [x] `pending_action_create`.
  Preuve livree: Lot 6, ID local, TTL, hash court, meta content-free.
- [x] `pending_action_get`.
  Preuve livree: Lots 6/7A, `confirm_*` relit une pending action precise et
  execute uniquement si le draft prive et le client write fake sont presents;
  Lot 7D autorise les updates fake/local seulement depuis draft prive, ETag,
  path CalDAV prive et ICS source preservee.
- [x] `pending_action_cancel`.
  Preuve livree: Lot 6, annulation et expiration sans mutation.
- [x] `event_create_confirmed`.
  Preuve livree: Lot 7A non-live fake; Lot 7B live synthetique `PUT 201`,
  evenement relu status-only `GET 200` avec ETag, aucune fuite content-free.
- [x] `event_update_confirmed`.
  Preuve livree: Lot 7D non-live fake/local, update depuis pending draft prive
  + ETag + path CalDAV prive + ICS source, `PUT` fake avec `If-Match`,
  preservation UID/proprietes inconnues/alarmes/participants sur VEVENT simple,
  refus fail-closed des ICS multi-VEVENT, recurrences ou overrides
  `RECURRENCE-ID`, refus des updates no-op, conflit `412` content-free; aucun
  live write utilisateur.
- [x] `event_delete_confirmed`.
  Preuve livree: Lot 7A non-live, CalDAV `DELETE` fake seulement apres
  confirmation renforcee avec ETag obligatoire; Lot 7B rollback live
  synthetique `DELETE 204` uniquement sur la cible creee dans le meme smoke.

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
  ICS/secrets case-insensitive rejetes dans `query`, y compris les proprietes
  ICS techniques usuelles (`RRULE`, `DTSTART`, `LAST-MODIFIED`).
- [x] Durcir la coherence mutations/methodes Lot 4.
  Preuve livree: methode read-only avec `mutation.kind=create` et
  `requested=false` rejetee; propositions et confirmations restent bornees.

### Lot 5 - Lecture read-only active

- [x] Lot 5A: brancher lecture Agenda applicative non-live quand toggle on,
  mode `active`, secret redacted present, plan JSON valide et methode read-only.
  Preuve livree: tests unitaires avec agent fake et client read-only injecte.
- [x] Lot 5A: executer uniquement les outils read-only autorises
  `calendar_list`, `event_query_range`, `event_search` et `event_get`.
  Preuve livree: execution deterministe allowlistee, sans mutation ni pending
  store.
- [x] Lot 5A: rendre la reponse visible comme reponse normale de Frida via
  `AssistantResponseOverride`.
  Preuve livree: test serveur fake avec message assistant, timestamp,
  `message.meta` content-free et chemin Memory eligible.
- [x] Lot 5A: garder les artefacts/meta/observabilite content-free.
  Preuve livree: pas de titre/lieu/description/UID/ETag/URL CalDAV/ICS dans
  l'observabilite testee.
- [x] Lot 5A: ne faire aucun acces CalDAV/Nextcloud live.
  Preuve livree: transports fake/injectes en tests; aucun app-password lu en
  clair.
- [x] Lot 5A.1: refuser toute reponse finale "agenda vide" sans outil read-only
  execute.
  Preuve livree: un plan `read_today` sans `tool_calls` est rejete avant final
  lock; l'execution read-only refuse aussi les plans sans outil.
- [x] Lot 5A.1: ne resoudre le secret CalDAV que pour un plan read-only
  executable.
  Preuve livree: `clarify_agenda_request` valide ne lit pas le secret et
  `secret_access` ne devient vrai que si le secret est effectivement resolu.
- [x] Lot 5A.1: rendre les heures visibles dans la timezone de l'evenement /
  de la lecture.
  Preuve livree: evenement stocke `07:00Z` avec timezone `Europe/Paris` en juin
  affiche `09:00`.
- [x] Lot 5A.2: conserver `TZID` dans le parsing ICS local pour les proprietes
  temporelles necessaires.
  Preuve livree: `DTSTART;TZID=Europe/Paris:20260608T090000` et `DTEND`
  associe sont stockes en UTC interne et rendus `09:00-10:00`, pas
  `11:00-12:00`.
- [x] Lot 5A.2: rendre `VALUE=DATE` comme evenement journee entiere.
  Preuve livree: `DTSTART;VALUE=DATE` / `DTEND;VALUE=DATE` produit un seul
  evenement `all_day` affiche `Toute la journee`, sans heure inventee
  `02:00-02:00`.
- [x] Lot 5A.3: calculer et injecter des fenetres temporelles canoniques
  `today` et `tomorrow` selon `FRIDA_TIMEZONE`.
  Preuve livree: avec `FRIDA_TIMEZONE=Europe/Paris` et
  `now=2026-06-08T10:00:00Z`, `today` vaut
  `2026-06-07T22:00:00Z -> 2026-06-08T22:00:00Z` et `tomorrow`
  `2026-06-08T22:00:00Z -> 2026-06-09T22:00:00Z`.
- [x] Lot 5A.3: refuser `read_today` / `read_tomorrow` si la fenetre du plan
  ne correspond pas a la fenetre canonique disponible.
  Preuve livree: une fenetre UTC brute `00Z -> 00Z` est rejetee en
  `agenda_agent_time_window_mismatch`, sans lecture ni fuite d'observabilite.
- [ ] Lot 5A.3: ajouter `current_week` canonique.
  Hors scope volontaire: a traiter avec le lot semaine/disponibilites, pour ne
  pas ouvrir la politique de debut de semaine dans ce micro-correctif.
- [x] Lot 5B preflight: rendre le schema OpenRouter Agenda compatible avec le
  mode `json_schema.strict` du provider.
  Preuve livree: `params` declare maintenant toutes ses proprietes en
  `required` nullable, le validateur ignore les `null` et le probe provider
  content-free passe de `status_code=400` a `status_code=200`.
- [x] Lot 5B tentative partielle content-free du 2026-06-08.
  Preuve livree:
  `app/docs/states/baselines/agenda-smokes/frida-agenda-lot5b-live-readonly-20260608T162407Z.jsonl`.
  Resultat: runtime redacted OK (`tof`, secret configure, aucune valeur
  exposee), agent JSON valide, CalDAV read-only atteint, mutation=false,
  JSONL content-free. No-go restant: Nextcloud repond `caldav_unauthorized`
  au PROPFIND; le mode a ete remis `off`; Lot 5B n'est pas ferme.
- [x] Lot 5B relance: configuration Sauron redacted du nouvel app-password
  dedie `frida-agenda-agent`.
  Preuve livree: compte `tof`, stockage `db_encrypted`, valeur jamais
  affichee, mode laisse `off` avant smoke, PROPFIND status-only `207`.
- [x] Lot 5B relance: instrumentation JSONL enrichie avant nouvelle preuve.
  Preuve livree: les payloads Lot 5 exposent `read_execution_status`,
  `read_execution_reason_code`, `read_tool_count`, `read_tool_names`,
  `error_class`, acces CalDAV/Nextcloud, final override et meta content-free
  sans valeur brute.
- [x] Lot 5B relance: `search_events` clarifie comme sequence bornee
  `event_query_range` puis `event_search`.
  Preuve livree: tests unitaires du prompt et du plan valide, sans regex
  utilisateur.
- [x] Lot 5B: configuration runtime Sauron redacted, mode `active`, compte
  `tof`, secret CalDAV dedie present sans affichage.
- [x] Lot 5B: preuve live lire aujourd'hui.
  Preuve livree:
  `app/docs/states/baselines/agenda-smokes/frida-agenda-lot5b-live-readonly-20260608T181853Z.jsonl`,
  verdict `met`, `read_execution_status=ok`, `event_query_range`,
  message assistant normal avec meta Agenda content-free.
- [x] Lot 5B: preuve live lire demain.
  Preuve livree: meme artefact, verdict `met`, CalDAV/Nextcloud read-only,
  timestamp et final response override.
- [x] Lot 5B: preuve live recherche evenement.
  Preuve livree: meme artefact, verdict `met`, sequence
  `event_query_range` puis `event_search`, sans contenu Agenda brut.
- [ ] Lot 5B: preuve live details evenement unique si candidat unique existe.
- [x] Lot 5B: preuve live contexte suivant, timestamp, Delta-T et Memory
  eligible.
- [x] Lot 5B: artefact JSONL content-free date, sans contenu Agenda brut.
  Preuve livree: scan sans titre, lieu, description, UID, ETag, raw ICS,
  URL/path CalDAV, Authorization, cookie, token ou app-password; verdict final
  `lot5b_live_readonly_met`; mode final laisse `active`.

### Lot 6 - Propositions et pending store

- [x] Ajouter pending store temporaire avec TTL.
  Preuve livree: `app/agenda/pending_store.py`, TTL 30 minutes par defaut,
  expiration/cancel content-free; Lot 6.1 garde le draft brut dans le store
  prive temporaire et jamais dans `message.meta`.
- [x] Ajouter proposition creation.
  Preuve livree: `propose_create_event` exige un draft structure suffisant,
  cree une pending action, final lock assistant normal, aucune ecriture.
- [x] Ajouter proposition modification.
  Preuve livree: Lots 6.1/6.2/6.3, `propose_update_event` exige une cible
  reellement relue par chemin read-only effectif; un `event_get` seulement
  declare est refuse sans resolution secret/client CalDAV.
- [x] Ajouter proposition suppression.
  Preuve livree: Lots 6.1/6.2/6.3, `propose_delete_event` exige une cible
  reellement relue par chemin read-only effectif; une sequence non executable
  est refusee avant resolution secret/client CalDAV; suppression non executee.
- [x] Rendre les propositions visibles concretes sans fuite meta.
  Preuve livree: Lot 6.1, la reponse Frida explicite quoi/quand/cible; meta,
  observabilite et etat conversationnel restent content-free.
- [x] Proteger le draft Lot 7 futur.
  Preuve livree: Lots 6.1/6.2, brouillon structure prive avec operation,
  calendrier, timezone, creneau, details humains et cible verifiee si besoin;
  Lot 7D peut conserver l'ICS source uniquement dans le draft prive temporaire
  pour patcher un update; JSONL/logs/meta ne contiennent pas titre, lieu,
  description, UID, ETag, path CalDAV ou ICS; les drafts prives tronques,
  expires ou annules sont oublies.
- [x] Prouver aucune ecriture CalDAV dans les propositions.
  Preuve livree: tests fake sans client CalDAV/secret; les propositions ne
  mutent jamais. Les confirmations executees appartiennent au Lot 7A.

### Lot 7 - Confirmations et mutations

- [x] Lot 7A non-live: creation apres confirmation.
  Preuve livree: pending draft prive, `PUT` fake transport, `If-None-Match: *`,
  action neutralisee `executed`, observabilite/meta content-free, aucun write
  live.
- [x] Lot 7B live: creation synthetique apres confirmation.
  Preuve livree: artefact
  `app/docs/states/baselines/agenda-smokes/frida-agenda-lot7b-live-write-20260609T114108Z.jsonl`,
  `PUT 201`, `GET 200`, ETag present, final lock assistant normal, aucun
  evenement personnel touche.
- [x] Lot 7D non-live: modification apres confirmation.
  Preuve livree: pending draft prive avec cible verifiee, ETag obligatoire,
  path CalDAV prive, ICS source disponible, patch preservant UID/proprietes
  inconnues/alarmes/participants sur VEVENT simple, `PUT` fake avec
  `If-Match`, conflit `412` content-free; aucun live write utilisateur.
- [x] Lot 7D.1 non-live: update ICS ambigu et no-op fermes.
  Preuve livree: `change_summary` seul n'est pas un changement executable,
  l'ICS identique est refusee avant `PUT`, et les ICS multi-VEVENT,
  recurrentes ou avec override `RECURRENCE-ID` sont fail-closed avec raison
  content-free tant qu'une selection fiable du composant ICS n'est pas livree.
- [x] Lot 7A non-live: suppression apres confirmation renforcee.
  Preuve livree: pending draft prive avec cible verifiee, `DELETE` fake
  transport, ETag obligatoire, confirmation renforcee obligatoire, aucune
  suppression live.
- [x] Lot 7B live: rollback/suppression de l'evenement synthetique.
  Preuve livree: suppression live bornee a la cible creee dans le meme smoke,
  `DELETE 204`, puis `GET 404`; etat final propre, evenement synthetique
  supprime.
- [x] Protection calendrier familial.
  Preuve livree: Lot 7C/7C.1 fake/local; create/delete sur calendrier familial
  posent `risk_flags=["family_calendar"]`, create/delete sur calendrier non
  classifie posent `risk_flags=["calendar_scope_unverified"]`, exigent
  `confirmation_level=reinforced`, refusent les confirmations simples avant
  `PUT`/`DELETE`, et la surface visible mentionne le calendrier
  partage/familial ou non classifie sans jargon technique.
- [x] Gestion conflit ETag ou equivalent.
  Preuve livree: Lots 7A.1/7D non-live, delete fake `412` et update fake `412`
  refusent proprement sans executer/neutraliser la pending action; aucun
  contenu ICS/source n'entre dans meta ou observabilite.
- [x] Lot 7B live write proof avec evenement synthetique, GO humain explicite,
  rollback/suppression de test documente et artefact content-free.
  Preuve livree: create met, rollback delete met, no-update-live met,
  content-free scan met; aucun titre, lieu, description, UID, ETag, path/URL,
  ICS, Authorization, cookie, token ou app-password dans l'artefact.
- [x] Rollback ou limite de rollback documentee.
  Preuve livree: rollback execute; aucun evenement synthetique laisse en place.

### Lot 8 - Observabilite, dashboard, smokes live anonymises

- [x] Inventaire des metas/observations Agenda existantes.
  Preuve livree: Lot 8A cartographie et projette les schemas
  `frida_agenda_lot5_readonly_v1`, `frida_agenda_lot6_pending_v1`,
  `frida_agenda_lot7a_confirmed_write_v1`,
  `frida_agenda_read_execution_v1`,
  `frida_agenda_proposal_execution_v1` et
  `frida_agenda_write_execution_v1` en read-model content-free.
- [x] Dashboard/read-model sans contenu Agenda brut.
  Preuve livree: route admin `GET /api/admin/agenda/observability`,
  projection runtime des evenements `stage=agenda`; la projection des metas
  conversationnelles existe comme helper teste, non exposee par la route
  runtime Lot 8A. Pending actions exposees uniquement par
  id/hash/statut/expiration/flags, tests anti-fuite sur titre, lieu,
  description, UID, ETag, path CalDAV, raw ICS, Authorization, cookie, token
  et app-password synthetiques.
- [x] JSONL content-free.
  Preuve livree: artefact
  `app/docs/states/baselines/agenda-smokes/frida-agenda-lot8b-live-observability-20260609T142458Z.jsonl`,
  toutes les lignes `content_free=true`, aucune reponse brute, aucun prompt
  brut, seulement statuts, reason codes, counts, hashes et booleens.
- [x] Smokes serveur sans iOS/macOS.
  Preuve livree: Lot 8B lance cote serveur FridaDev via `app.test_client()`:
  runtime redacted active, `read_today`, `read_tomorrow`, `search_events`,
  route admin observability et tour de contexte; aucun client macOS/iOS
  implique. La tentative optionnelle de proposition sans ecriture est
  `partial` et n'est pas utilisee pour fermer le lot.
- [x] Scan secrets/logs.
  Preuve livree: scan Lot 8B de l'artefact JSONL, de la sortie admin
  observability et des logs applicatifs `stage=agenda`; aucun contenu Agenda
  brut, secret, token, cookie, Authorization, UID/ETag brut, path/URL CalDAV ou
  raw ICS detecte dans les preuves conservees.
- [x] Validation conversation reelle anonymisee.
  Preuve livree: vraie conversation Frida Agenda avec toggle on, assistant
  sauvegarde comme message normal, timestamps presents, reprise de contexte et
  Delta-T detectes sans stocker de dialogue brut dans l'artefact.

### Lot 8bis - Recherche prochain evenement correspondant

- [x] Ajouter la methode produit read-only `find_next_matching_event`.
  Preuve livree: l'agent Agenda peut choisir cette methode pour les demandes
  du type `prochain rendez-vous avec X`, sans regex deterministe d'intention.
- [x] Executer la recherche future par fenetres bornees.
  Preuve livree: l'execution part de `now_iso`, applique un horizon par defaut
  de 365 jours maximum, interroge CalDAV par fenetres de 31 jours maximum et
  s'arrete au premier match futur.
- [x] Distinguer `search_events` et `find_next_matching_event`.
  Preuve livree: `search_events` cherche dans une fenetre deja lue; `find_next`
  avance dans le futur par fenetres bornees sans aspirer tout l'agenda.
- [x] Verrouiller la restitution apres erreur live Agenda.
  Preuve livree: si CalDAV/Nextcloud a ete tente et echoue, Frida produit une
  reponse Agenda honnete et verrouillee, sans laisser le LLM libre dire qu'il
  ne peut pas rouvrir l'agenda.
- [x] Ajouter la preuve live content-free Lot 8bis.
  Preuve livree:
  `app/docs/states/baselines/agenda-smokes/frida-agenda-lot8bis-next-matching-live-20260609T152733Z.jsonl`,
  vraie conversation Frida, methode `find_next_matching_event`,
  CalDAV/Nextcloud read-only, final response override, message assistant normal
  timestamped, mutation=false, scan sans contenu Agenda brut.

### Lot 8bis.1 - Fallback live agentique et appel Tof

- [x] Ajouter une surface d'echec agentique `surface_error`.
  Preuve livree: le schema strict exige `surface_error`; les plans read-only
  sans surface d'echec sont rejetes avant acces reseau.
- [x] Supprimer le fallback visible redige par le deterministe.
  Preuve livree: en cas d'erreur apres acces CalDAV/Nextcloud tente, le final
  lock utilise la surface fournie par l'agent Agenda; `response_rendering.py`
  ne porte plus la phrase visible locale.
- [x] Ajouter `user_display_name=Tof` au contexte agent.
  Preuve livree: le payload envoye a l'agent contient `user_display_name`;
  les observations et metas ne stockent que presence/hash/chars, pas le nom en
  clair. Aucun Lot 9 n'est ouvert.

### Lot 8bis.2 - Surface read-only coherente et duree multi-jours

- [x] Ne plus afficher `surface_outro` apres une lecture read-only executee.
  Preuve livree: le final lock read-only assemble `surface_intro` et le contenu
  reel; `surface_outro`, produit avant la lecture, n'est plus affiche apres
  succes, absence de resultat ou erreur live.
- [x] Rendre les evenements all-day multi-jours comme des plages.
  Preuve livree: `DTSTART;VALUE=DATE:20260711` +
  `DTEND;VALUE=DATE:20260718` est restitue comme `du 11 au 17 juillet 2026,
  toute la journee (7 jours)`, en respectant `DTEND` exclusif.
- [x] Preserver le contexte conversationnel utile sans fuite observabilite.
  Preuve livree: la reponse visible contient la plage et la duree; metas et
  observations restent content-free.
- [x] Cartographier les questions possibles a poser a l'Agenda pour reperer
  les prochains trous produit.
  Preuve livree: Lot 8ter docs-only,
  `app/docs/states/audits/frida-agenda-question-cartography-2026-06-09.md`.
  La cartographie separe `Disponible utilisateur` de `Preuve conservee` afin
  de ne plus confondre capacite tentable et preuve formelle. Aucun Lot 9 n'est
  ouvert.

### Lot 8ter - Cartographie des questions Agenda

- [x] Produire une carte produit des questions Agenda vernaculaires.
  Preuve livree:
  `app/docs/states/audits/frida-agenda-question-cartography-2026-06-09.md`.
- [x] Distinguer ce qui marche, ce qui est partiel, ce qui est seulement au
  contrat, ce qui est refuse par design et ce qui manque.
  Preuve livree: table de familles avec disponibilite utilisateur, preuve
  conservee, chemin technique, limite connue et prochain test utile.
- [x] Lister des formulations anonymisees pour les prochains smokes.
  Preuve livree: exemples par famille sans contenu personnel d'agenda, sans
  lecture CalDAV live et sans mutation.
- [x] Ajouter les familles qui ne doivent pas etre vendues implicitement.
  Preuve livree: sous-fenetres vernaculaires, rappels/notifications/alarmes,
  participants/invitations, recurrences/occurrences et perimetre operateur sont
  cartographies avec limites explicites.
- [x] Garder Lot 9 ferme.
  Preuve livree: la cartographie propose des validations futures sans les
  lancer ni les nommer comme Lot 9 actif.

### Smokes cibles de cloture pragmatique V1

- [x] Executer les 4 familles ciblees sans tester toute la cartographie.
  Preuve livree:
  `app/docs/states/baselines/agenda-smokes/frida-agenda-v1-targeted-closure-smokes-20260609T175408Z.jsonl`
  (le premier smoke partial reste conserve sous
  `app/docs/states/baselines/agenda-smokes/frida-agenda-v1-targeted-closure-smokes-20260609T171000Z.jsonl`).
  Les familles testees sont: date explicite, sous-fenetres vernaculaires,
  duree/sejour/reprise multi-tour, aide/perimetre operateur.
- [x] Produire un artefact JSONL content-free et scanner l'absence de fuite.
  Preuve livree: `LOT8CLOSURE5_CONTENT_FREE_SCAN` est `met`, aucun contenu
  Agenda brut n'est stocke dans l'artefact; la seule mutation observee est la
  creation synthetique temporaire de preuve duree, supprimee dans le meme run.
- [x] Declarer la cloture pragmatique Agenda V1.
  Resultat: les 4 familles ciblees sont `met`; Agenda V1 est utilisable au
  quotidien. Ne pas continuer a tester les 25 familles sans bug reel, besoin
  utilisateur concret ou decision explicite de nouvelle capacite.
- [x] Valider la date explicite comme famille convaincante.
  Resultat: `met`. `read_explicit_date` execute CalDAV/Nextcloud read-only et
  verrouille une reponse Frida normale.
- [x] Valider les sous-fenetres vernaculaires.
  Resultat: `met`. `ce matin` et `demain soir` utilisent des fenetres bornees
  de 6h, pas une journee complete.
- [x] Valider duree/sejour/reprise multi-tour.
  Resultat: `met`. Un evenement synthetique multi-jours est cree, lu, repris
  au tour suivant pour la duree, puis supprime dans le meme run.
- [x] Valider l'aide/perimetre operateur.
  Resultat: `met`. Les surfaces dediees expliquent lecture, recherche,
  propositions, confirmations, refus et capacites non livrees sans jargon
  sensible.
- [x] Garder Lot 9 ferme.

Capacites volontairement laissees ouvertes apres cloture pragmatique V1:
disponibilites riches, comparaison de journees/evenements, rappels,
invitations, recurrences produit riches et mutations utilisateur reelles.
  Preuve livree: aucun Lot 9 general n'est coche; les suites restent des
  corrections ciblees ou des decisions produit explicites.

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
