# Contrat d'extraction canonique de la fenetre recente

Date: 2026-03-31
Statut: spec normative active
Scope: extraction canonique de `fenetre_recente` pour le Lot 2, sans implementation runtime

## Purpose

La `fenetre_recente` est le contexte direct retenu pour la lecture hermeneutique du tour.

Elle n'est pas:

- toute la matiere recente disponible;
- une fenetre calculee par budget tokens;
- une qualification semantique de la demande;
- une interpretation hermeneutique deja engagee.

Son role est uniquement de fixer une extraction mecanique, deterministe, testable, au-dessus de la matiere recente brute deja disponible dans le repo.

## Input Relationship

Le repo distingue desormais deux niveaux:

- `recent_context_input`: matiere recente brute exposee au seam du Lot 1;
- `fenetre_recente`: extraction canonique selectionnee a partir de cette matiere pour le Lot 2.

La relation normative est la suivante:

- `recent_context_input` reste la source brute disponible;
- `fenetre_recente` est une selection canonique au-dessus de cette source;
- `fenetre_recente` ne doit pas redefinir ni enrichir semantiquement `recent_context_input`;
- toute qualification ulterieure de la demande reste hors scope de ce contrat.

## Selection Rule

La selection canonique de `fenetre_recente` doit respecter toutes les regles suivantes:

- partir uniquement des messages de `recent_context_input`;
- ne retenir que la matiere situee apres le cutoff du resume actif;
- conserver l'ordre chronologique des messages retenus;
- operer par tours conversationnels, pas par fragments arbitraires;
- ne pratiquer aucune troncature de contenu a l'interieur des messages retenus.

La cible ambitieuse alternative consisterait a exposer toute la matiere post-resume puis a laisser un agent ou noeud decider dynamiquement ou s'arreter.

Ce n'est pas le contrat retenu pour cette premiere version, parce que cette approche serait moins deterministe, moins testable, et moins bornee.

## Depth Rule

La profondeur canonique de la premiere version est fixee a:

- `max_recent_turns = 5`

Cette profondeur se calcule:

- en nombre de tours;
- pas en tokens;
- pas en nombre brut de messages.

La profondeur canonique n'autorise pas la troncature partielle d'un tour retenu.

## Turn Definition

La definition normative d'un tour est:

- un couple `user -> assistant`

Regles associees:

- un tour complet contient un message `user` suivi de la reponse `assistant` correspondante;
- si le dernier tour est incomplet, le dernier message `user` doit etre conserve comme tour en cours;
- aucun message `assistant` ne doit etre rattache retroactivement a un autre tour que celui qui le suit immediatement dans l'ordre chronologique.

## Timestamp Rule

La regle d'horodatage est strictement conservative:

- l'horodatage est conserve par message;
- la `fenetre_recente` ne doit pas inventer un temps synthetique de tour si le repo ne le porte pas deja;
- les timestamps disponibles dans la matiere source doivent etre recopies tels quels dans la structure canonique future.

## Format

Le format canonique attendu pour la future structure `fenetre_recente` doit au minimum permettre:

- un versionnage de schema;
- l'explicitation de `max_recent_turns`;
- une liste ordonnee de tours recents;
- la distinction entre tour complet et tour en cours;
- la conservation des messages sources avec leur `role`, `content`, et `timestamp`.

Forme minimale attendue en esprit:

- `schema_version`
- `max_recent_turns`
- `turns`

Et pour chaque tour:

- `turn_status` (`complete` ou `in_progress`)
- `messages`

Et pour chaque message:

- `role`
- `content`
- `timestamp`

Cette spec fixe l'extraction canonique et la forme attendue, pas encore le module runtime final.

## Repo Grounding

Cette spec est grounded dans l'etat actuel du repo:

- `app/core/hermeneutic_node/inputs/recent_context_input.py` expose deja la matiere recente brute apres cutoff du resume actif;
- `app/core/hermeneutic_node/inputs/summary_input.py` et `app/core/conversations_prompt_window.py` etablissent deja la logique de cutoff du resume actif;
- `app/core/chat_service.py` expose deja `recent_context_input` au seam hermeneutique;
- aucun module runtime ne porte encore `fenetre_recente` comme extraction canonique distincte.

Le contrat formalise donc la prochaine extraction a construire, sans pretendre qu'elle existe deja dans le runtime.

## Non-goals / Out of Scope

Cette spec ne tranche pas:

- la qualification semantique de la demande utilisateur;
- les signaux d'ambiguite ou de sous-determination;
- une profondeur calculee par budget tokens;
- une logique d'arret hermeneutique dynamique;
- la priorisation doctrinale des sources;
- l'implementation runtime de `fenetre_recente`.

## Invariants

Les invariants suivants ne devront pas etre violes:

- `recent_context_input` et `fenetre_recente` doivent rester distincts;
- `fenetre_recente` doit etre calculee en nombre de tours, pas en tokens;
- `fenetre_recente` ne doit pas truncater les messages retenus;
- la selection doit rester post-resume actif;
- l'ordre chronologique des messages doit etre conserve;
- le dernier message `user` incomplet doit etre retenu comme tour en cours;
- l'extraction mecanique ne doit pas etre melangee avec la qualification hermeneutique.
