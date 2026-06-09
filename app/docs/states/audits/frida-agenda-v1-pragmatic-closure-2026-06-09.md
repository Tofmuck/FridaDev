# Frida Agenda V1 - Cloture pragmatique

Date: 2026-06-09
Classement: `app/docs/states/audits/`
Branche: `FridaAgenda`
Commit de base: `7fa2622 fix: enforce Agenda calendar scope consistency`
Etat: Agenda V1 cloture pragmatiquement.

## 1. Decision

Agenda V1 est considere utilisable en pratique pour les usages prouves et les
garde-fous livres. Cette cloture ne signifie pas que toutes les familles de
questions Agenda sont couvertes, ni que les mutations utilisateur reelles sont
ouvertes.

La regle de suite est volontairement simple:

- ne pas relancer des lots Agenda abstraits apres cette cloture;
- ne pas tester les 25 familles de la cartographie sans raison concrete;
- rouvrir uniquement sur bug utilisateur reel, besoin produit explicite ou
  decision operateur;
- si un sujet revient, ouvrir un micro-lot cible, avec preuve bornee.

Lot 9 reste ferme.

## 2. Etat runtime

Cette note est docs-only: aucun probe runtime, CalDAV, Nextcloud ou valeur
sensible n'a ete effectue.

Mode attendu en exploitation: `agenda_agent.mode=active` si l'etat operateur
courant le confirme. Cette note ne le verifie pas; a verifier cote runtime si
un operateur veut auditer l'etat live.

## 3. Preuves conservees

Artefacts et sources principaux:

- `app/docs/states/baselines/agenda-smokes/frida-agenda-lot5b-live-readonly-20260608T181853Z.jsonl`;
- `app/docs/states/baselines/agenda-smokes/frida-agenda-lot7b-live-write-20260609T114108Z.jsonl`;
- `app/docs/states/baselines/agenda-smokes/frida-agenda-lot8b-live-observability-20260609T142458Z.jsonl`;
- `app/docs/states/baselines/agenda-smokes/frida-agenda-lot8bis-next-matching-live-20260609T152733Z.jsonl`;
- `app/docs/states/baselines/agenda-smokes/frida-agenda-v1-targeted-closure-smokes-20260609T175408Z.jsonl`;
- `app/docs/states/audits/frida-agenda-question-cartography-2026-06-09.md`;
- `app/docs/states/specs/frida-agenda-agent-contract.md`;
- `app/docs/todo-todo/product/frida-agenda-agent.md`.

Le premier smoke cible partial reste conserve comme trace de decouverte:

- `app/docs/states/baselines/agenda-smokes/frida-agenda-v1-targeted-closure-smokes-20260609T171000Z.jsonl`.

## 4. Capacites V1 prouves

Lecture et recherche:

- lecture aujourd'hui et demain en fenetre locale canonique;
- lecture d'une date explicite;
- sous-fenetres vernaculaires simples: matin, apres-midi, soir;
- recherche dans une fenetre lue;
- recherche du prochain evenement futur correspondant a une requete textuelle;
- rendu des evenements journee entiere;
- rendu des evenements journee entiere multi-jours comme plage avec duree;
- reprise contextuelle simple depuis une reponse visible deja rendue.

Dialogue et produit:

- reponse assistant Frida normale, sans canal parallele visible;
- fallback live Agenda agentique via surface fournie par l'agent;
- aide et perimetre operateur bornes;
- distinction claire entre lecture, proposition, confirmation et action
  executee;
- propositions de creation, modification, deplacement et suppression avec
  pending action temporaire;
- confirmations bornees en fake/local;
- creation synthetique live bornee puis rollback de la meme cible synthetique.

Observabilite et garde-fous:

- observabilite Agenda content-free;
- read-model admin content-free;
- artefacts JSONL content-free;
- absence de contenu personnel Agenda brut dans les preuves conservees;
- calendrier familial ou partage fail-closed pour create/delete;
- statut familial inconnu traite avec prudence renforcee;
- scope calendrier explicite fail-closed si l'id local est absent, non resolu
  ou hors scope;
- meme garde-fou pour `event_query_range` et `find_next_matching_event`;
- update confirme fake/local preserve la source calendrier sur cas simple et
  refuse les composants recurrents ou ambigus.

## 5. Limites volontaires post-V1

Ces sujets restent ouverts volontairement apres V1:

- disponibilites riches et recherche de creneaux libres;
- comparaison de journees ou d'evenements;
- rappels, notifications et alarmes;
- participants, invitations et reponses a invitation;
- recurrences produit riches, repetition, occurrence unique;
- mutations utilisateur reelles;
- selection vernaculaire avancee d'un calendrier precis;
- persistance robuste des pending actions apres restart;
- update live utilisateur sur evenements personnels;
- surfaces de clarification plus fines par famille.

Ces limites ne bloquent pas l'usage quotidien V1 tant qu'elles sont traitees
comme non promises.

## 6. Ce que V1 ne promet pas

Agenda V1 ne promet pas:

- un assistant de disponibilites complet;
- une gestion d'invitations;
- des rappels ou alarmes;
- des mutations utilisateur reelles par defaut;
- une edition live d'evenements personnels;
- une comprehension parfaite de tous les libelles de calendriers;
- une couverture exhaustive de toutes les questions de la cartographie.

## 7. Regle de reouverture

Apres cette cloture, la bonne forme de travail est:

1. constater un bug reel ou un besoin concret;
2. nommer une seule famille ou un seul garde-fou;
3. ouvrir un micro-lot cible;
4. ajouter une preuve content-free;
5. documenter le resultat sans transformer le sujet en grande roadmap.

Ne pas ouvrir Lot 9 sans decision explicite.

## 8. Risques assumes

- Certaines questions utilisateur sont tentables par l'agent mais non fermees
  par smoke dedie.
- La selection vernaculaire d'un calendrier precis reste partielle; le runtime
  refuse desormais les incoherences de scope au lieu d'elargir la lecture.
- La reprise multi-tour repose encore souvent sur le contexte visible, pas sur
  un graphe d'ancres Agenda robuste.
- Le pending store reste temporaire et memoire; une persistance robuste serait
  un chantier separe.
- Les mutations utilisateur reelles restent un choix produit futur, pas un
  acquis V1.
