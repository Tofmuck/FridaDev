# Frida Agenda Agent Lot 0 baseline

Date: 2026-06-08
Statut: baseline Lot 0 validee
Classement: `app/docs/states/baselines/`
TODO actif: `app/docs/todo-todo/product/frida-agenda-agent.md`
Contrat source: `app/docs/states/specs/frida-agenda-agent-contract.md`
Fixtures: `app/docs/states/baselines/agenda-fixtures/`
Scope: docs/fixtures-only, sans patch runtime, sans acces Nextcloud, sans acces
CalDAV reel, sans app-password, sans evenement personnel et sans rebuild.

## Meilleur plan retenu

Le meilleur plan Lot 0 est de preparer des artefacts locaux anonymes plutot
qu'un calendrier de test Nextcloud reel.

Ce choix garde les frontieres claires:

- Frida parle.
- L'agent Agenda travaillera dans un lot futur.
- Le deterministe protegera via outils CalDAV bornes et observabilite
  content-free.
- Lot 0 ne touche pas Nextcloud et ne cree aucun secret.

Un calendrier de test Nextcloud reel appartient a un lot operatoire separe, a
faire seulement si l'operateur le demande explicitement. S'il exige Caddy,
Authelia, Docker, Nextcloud ou app-password, il releve de Sauron.

## Sources relues

- `/opt/platform/fridadev/AGENTS.md`
- `README.md`
- `app/docs/README.md`
- `app/docs/todo-todo/product/frida-agenda-agent.md`
- `app/docs/states/specs/frida-agenda-agent-contract.md`
- `app/docs/states/specs/agentic-response-surface-contract.md`

## Coherence spec / TODO

Constat:

- la spec Agenda porte bien le toggle `agenda_enabled`, separe du mode runtime
  `agenda_agent`;
- la spec reprend le modele agentique: Frida visible, agent Agenda interne,
  deterministe protecteur;
- le contrat de surface agentique exige un message assistant normal, avec
  timestamp, meta content-free, contexte suivant, Memory, resumes et embeddings
  selon les contrats existants;
- la TODO est organisee par familles produit Agenda et par lots runtime futurs;
- les decisions V1 recentes sont coherentes: compte humain `tof` +
  app-password dedie, pas de compte service `frida` pour Agenda V1, memoire
  normale pour les reponses visibles, observabilite content-free;
- la formulation Lot 0 "fixtures CalDAV anonymes ou un calendrier de test" est
  trop ouverte pour ce cran: Lot 0 est maintenant borne aux fixtures locales
  anonymes. Aucun calendrier test Nextcloud reel n'est cree.

Decision Lot 0:

- aucune incoherence bloquante;
- la TODO est precisee pour fermer l'option calendrier reel dans Lot 0;
- la preuve content-free future est precisee dans la spec et dans les fixtures.

## Fixtures anonymes creees

Repertoire:

- `app/docs/states/baselines/agenda-fixtures/`

Fichiers:

- `README.md`: contrat d'usage des fixtures;
- `anonymous-primary-calendar.ics`: calendrier primaire fictif;
- `anonymous-shared-calendar.ics`: calendrier partage fictif, marque comme cas
  de prudence future;
- `anonymous-proof-meta.json`: meta attendue content-free pour les lots runtime
  futurs.

Garanties:

- tous les VEVENT sont synthetiques;
- aucun titre reel;
- aucun lieu reel;
- aucune personne reelle;
- aucun rendez-vous reel;
- aucune description personnelle;
- aucun UID, URL, cookie, token, secret ou app-password reel;
- aucun import Nextcloud ou CalDAV n'a ete fait.

Usage futur autorise:

- parser localement les ICS en test unitaire;
- verifier la resolution de fenetres temporelles;
- verifier les counts et hashes courts;
- verifier que les logs/read-models/JSONL ne contiennent pas les champs humains
  bruts des fixtures.

Usage futur interdit:

- importer ces ICS dans le calendrier personnel;
- les utiliser comme preuve live Nextcloud;
- remplacer les smokes serveur content-free par une preuve fixture-only;
- logguer leurs titres, descriptions ou lieux dans les artefacts runtime.

## Preuve content-free attendue

Pour les lots runtime futurs, une preuve Agenda content-free doit exposer
seulement des signaux techniques et agreges.

Champs autorises:

- `schema_version`;
- `toggle`;
- `mode`;
- `product_method`;
- `tool_names`;
- `status`;
- `reason_code`;
- `calendar_id_short`;
- `family_calendar`;
- `window_start`;
- `window_end`;
- `timezone`;
- `event_count`;
- `candidate_count`;
- `selected_count`;
- `pending_action_id`;
- `confirmation_level`;
- `etag_hash_short`;
- `payload_hash_short`;
- `duration_bucket`;
- `secret_present`;
- `redacted`.

Champs interdits:

- app-password;
- mot de passe principal;
- cookie;
- header Authorization;
- token;
- URL CalDAV complete;
- UID CalDAV brut;
- ETag brut;
- ICS brut;
- titre d'evenement;
- description;
- lieu;
- invite;
- payload modele brut;
- prompt complet;
- dialogue complet;
- evenement personnel brut.

Regle de surface:

- la reponse visible a l'utilisateur peut contenir le contenu Agenda demande,
  puis entrer en memoire comme dialogue normal;
- les preuves techniques, logs, JSONL, dashboard et read-models restent
  content-free;
- les fixtures peuvent contenir du contenu synthetique parce qu'elles sont des
  donnees de test versionnees, mais les artefacts runtime ne doivent pas le
  recopier.

## No-go personnel

Lot 0 confirme:

- aucun acces CalDAV reel;
- aucun acces Nextcloud reel;
- aucun calendrier test Nextcloud cree;
- aucun app-password cree;
- aucun secret lu, affiche ou stocke;
- aucun evenement personnel lu, affiche ou stocke;
- aucun fichier runtime modifie;
- aucun patch Biblio;
- aucun changement Caddy, Authelia, Docker, Nextcloud ou DB;
- aucun rebuild.

## Decision Lot 0

Lot 0 est valide.

Go Lot 1: oui, sous conditions:

- garder `agenda_enabled` off par defaut;
- prouver toggle off = aucun acces Agenda;
- prouver toggle on sans runtime = degradation propre;
- ne faire aucun acces CalDAV dans Lot 1;
- garder les fixtures anonymes comme seuls artefacts Agenda locaux;
- conserver Lot 1+ non coches tant que les preuves runtime correspondantes ne
  sont pas livrees.
