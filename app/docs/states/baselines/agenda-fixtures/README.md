# Frida Agenda anonymous fixtures

Date: 2026-06-08
Statut: fixtures Lot 0 anonymes
Classement: `app/docs/states/baselines/agenda-fixtures/`
Baseline: `app/docs/states/baselines/frida-agenda-agent-lot0-baseline-2026-06-08.md`

## Portee

Ces fichiers preparent les lots runtime futurs de l'agent Agenda sans acceder a
Nextcloud ni a CalDAV.

Ils sont entierement fictifs:

- pas de personne reelle;
- pas de lieu reel;
- pas de rendez-vous reel;
- pas de description personnelle;
- pas de secret;
- pas de token;
- pas de cookie;
- pas d'app-password.

## Fichiers

- `anonymous-primary-calendar.ics`: calendrier primaire synthetique.
- `anonymous-shared-calendar.ics`: calendrier partage synthetique, utile pour
  tester les futurs risk flags de prudence.
- `anonymous-proof-meta.json`: meta content-free attendue pour les preuves
  runtime futures.

## Usage autorise

- tests unitaires locaux;
- parsing ICS local;
- verification de fenetres temporelles;
- verification de counts, hashes courts, reason codes et champs redacted;
- verification que les logs/read-models/JSONL ne recopient pas les titres,
  descriptions ou lieux synthetiques.

## Usage interdit

- importer ces fichiers dans Nextcloud;
- les utiliser comme evenement personnel;
- les utiliser comme preuve CalDAV live;
- ajouter un secret ou une URL runtime;
- logguer le contenu humain brut comme preuve technique.

## Regle content-free

Les fixtures contiennent des VEVENT synthetiques pour permettre les tests. Les
artefacts runtime futurs doivent rester content-free: ils peuvent prouver des
counts, ids courts, booleens, hashes courts, fenetres et reason codes, mais pas
les titres, descriptions, lieux ou payload ICS.
