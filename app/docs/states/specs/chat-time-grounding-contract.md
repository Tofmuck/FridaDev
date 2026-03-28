# Chat Time Grounding Contract (phase 0)

## Objectif
Fixer un cadrage normatif court pour le grounding temporel du chat, a partir de l'etat reel du repo, avant implementation.

## 1) Constat d'etat reel
Ce qui existe deja dans le code:
- `app/core/chat_prompt_context.py` injecte une brique `[RÉFÉRENCE TEMPORELLE]` avec un `maintenant` explicite et timezone.
- `app/core/chat_service.py` fixe deja un `now` de tour (timestamp canonique de message utilisateur) et le propage a la construction du prompt.
- `app/core/conv_store.py` porte deja des labels relatifs (`delta_t_label`) et des marqueurs de silence (`_silence_label`) injectes dans les messages de prompt.
- `app/prompts/main_hermeneutical.txt` formalise deja l'interpretation du repere temporel, des deltas et des silences.
- resume actif, souvenirs et indices contextuels sont deja situes en partie relativement au temps de tour.
- Contradiction principale actuelle (double source `NOW`):
  - `chat_prompt_context.build_augmented_system()` recalcule un `datetime.now(...)` local pour la prose `[RÉFÉRENCE TEMPORELLE]`;
  - `chat_service.chat_response()` fixe deja `user_timestamp` / `now_iso_value` pour le tour;
  - ce `NOW` n'est pas encore la source unique de verite pour toute la temporalite du tour.

Ce que cela permet deja:
- situer une partie du dialogue dans une temporalite relative lisible;
- maintenir une continuite minimale entre reprises de conversation et contextes memoriels.

Ce que cela ne garantit pas encore:
- un contrat temporel produit unifie et explicite d'un bout a l'autre du pipeline;
- une forme assez contractuelle (pas seulement narrative/prose) pour `NOW` et `DELTA-NOW`;
- la prevention robuste des formulations fautives du modele sur l'acces au temps de reference.

## 2) These normative
Dans FridaDev, le temps n'est pas d'abord une donnee de memoire: c'est une condition de forme du discours.
La memoire conserve des traces horodatees, mais le discours en produit le sens temporel relativement a un `NOW` canonique de tour.
Le `DELTA-NOW` est un operateur de lisibilite du passe pour le present du dialogue, pas un habillage cosmetique.
Si le systeme injecte un `NOW` de tour, le modele ne doit pas pretendre qu'il est prive d'ancrage temporel de reference.

## 3) Invariants produit
- Chaque tour doit avoir un `NOW` canonique, autoritaire, explicite, timezone incluse.
- Les messages injectes dans le prompt doivent rester situables relativement a ce `NOW`.
- Le systeme doit permettre des reponses temporellement situees aux questions du type:
  - "quand est-ce qu'on a parle la derniere fois ?"
  - en forme relative et/ou absolue selon le besoin.
- Le modele ne doit pas declarer qu'il n'a pas acces au temps de reference quand ce temps est fourni.
- Le temps regle aussi la reprise, la re-situation et la continuite du discours.

## 4) Pre-architecture (reservee, non implementee ici)
Distinctions a garder explicites:
- arbitrage memoire: selection/ponderation des traces memorisees;
- arbitrage discursif: forme de reponse et regime d'assertion en contexte;
- orchestration: chaine d'appel qui aligne ces couches.

Decision de pre-structure:
- le temps est le premier determinant du futur regime discursif.
- d'autres determinants pourront converger ensuite (si utile): tonalite contextuelle (`stimmum`), valeur du retrievable, etat du contexte, autres signaux.
- cette convergence future devra produire un regime discursif (formel, epistemique, preuve, reprise/re-situation), sans ouvrir ici une spec supplementaire.

## 5) Frontieres
- Ne pas confondre temps memoire (horodatage de traces) et temps discours (ancrage du sens en tour courant).
- Ne pas reinventer ici l'arbitre memoire.
- Ne pas transformer ce contrat en spec globale de toute la production discursive.
- Rester sur une pre-structure stable, directement exploitable par un chantier produit borne.
