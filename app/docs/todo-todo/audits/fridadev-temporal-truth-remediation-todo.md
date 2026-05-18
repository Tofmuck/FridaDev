# FridaDev - remediation de verite temporelle - TODO

Source: `app/docs/states/audits/fridadev-temporal-system-audit-2026-05-18.md`

## Objectif

Fermer les findings actifs de l'audit temporel du 2026-05-18 sans refonte opportuniste. La cible est simple: toute temporalite visible par un modele ou par l'utilisateur doit etre derivee de la meme verite locale Frida, sauf surfaces operateur explicitement UTC.

## Non-objectifs

- Pas de changement provider/modele.
- Pas de refonte memoire.
- Pas de refonte dashboard large.
- Pas de chantier Biblio.
- Pas de normalisation generale des logs hors clarification UTC necessaire.
- Pas de requalification de la doctrine conversationnelle au-dela du temps.

## Lot 1 - Web local time

Finding cible: `TEMP-20260518-P1-001`.

Actions:

- remplacer les dates `datetime.now(timezone.utc).strftime("%d %B %Y")` de `app/tools/web_search.py` par une date locale Frida construite via le coeur temporel;
- inclure la timezone ou une mention explicite Europe/Paris dans le contexte web et le prompt de reformulation;
- ne pas dependre de la locale systeme pour les mois/jours francais;
- tester `2026-05-17T22:05:00Z -> 18 mai 2026 Europe/Paris`.

Condition de sortie:

- aucun contexte web ne peut contredire `[RÉFÉRENCE TEMPORELLE]` autour de minuit local.

## Lot 2 - Modeles secondaires temporellement ancres

Findings cibles: `TEMP-20260518-P2-001`, `TEMP-20260518-P2-002`, `TEMP-20260518-P2-003`, `TEMP-20260518-P3-001`, `TEMP-20260518-P3-002`.

Actions:

- validation agent: exposer les timestamps du `validation_dialogue_context` sous forme locale robuste, ou remonter `NOW/TIMEZONE` au meme niveau de priorite que le contexte;
- arbitre memoire: fournir recent context et candidats avec labels locaux sobres, en conservant l'UTC technique si utile;
- identity extractor: ajouter un ancrage temporel ou une regle de rejet explicite des claims temporels relatifs non durables;
- identity periodic: statuer sur le besoin d'ancre locale pour les `buffer_pairs`;
- stimmung: choisir explicitement entre "ignore les gaps" documente/teste ou "recoit les gaps locaux".

Condition de sortie:

- aucun modele secondaire influencant la reponse finale ne recoit un `hier/aujourd'hui` sans ancre locale ou politique d'ignorance explicite.

## Lot 3 - UI, exports et dashboard

Findings cibles: `TEMP-20260518-P2-004`, `TEMP-20260518-P2-005`.

Actions:

- dashboard `today/yesterday`: passer en jour local Frida ou renommer/labeliser explicitement UTC;
- chat bylines: choisir Europe/Paris explicite ou locale navigateur explicite;
- export Markdown: meme decision que byline, avec timezone visible;
- tests frontend/dashboard autour de `2026-05-17T22:05:00Z`.

Condition de sortie:

- une heure correcte ne peut plus etre associee silencieusement au mauvais jour dans une surface utilisateur.

## Lot 4 - Classifieur et fallbacks

Findings cibles: `TEMP-20260518-P2-006`, `TEMP-20260518-P3-003`, `TEMP-20260518-P3-004`.

Actions:

- reconnaitre `hier` / `depuis hier` dans la qualification temporelle du tour;
- rendre le fallback timestamp invalide observable et non inventif pour le dialogue;
- rendre le fallback timezone invalide observable, avec test;
- ajouter tests DST Europe/Paris si le lot touche le coeur temporel.

Condition de sortie:

- un signal temporel relatif explicite n'est plus classe atemporel;
- une donnee temporelle invalide n'est plus transformee silencieusement en present dialogique.

## Condition de non-prolongation

Ce TODO est clos quand les findings listes sont resolus ou explicitement requalifies stale avec tests/preuves. Toute nouvelle demande de refonte memoire, provider, dashboard ou Biblio doit ouvrir un autre chantier.
