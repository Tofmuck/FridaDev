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
- Contradiction principale initiale (desormais resolue dans le code courant):
  - auparavant, `chat_prompt_context.build_augmented_system()` recalculait un `datetime.now(...)` local en concurrence avec le `NOW` de tour de `chat_service`;
  - maintenant, `chat_service.chat_response()` fixe `user_timestamp` / `now_iso_value` et `build_augmented_system(...)` consomme explicitement ce `now_iso`;
  - la source de verite du `NOW` de tour est donc unique a l'echelle du pipeline prompt + labels relatifs.

Ce que cela permet deja:
- situer une partie du dialogue dans une temporalite relative lisible;
- maintenir une continuite minimale entre reprises de conversation et contextes memoriels.

Ce que cela ne garantit pas encore:
- un contrat temporel produit unifie et explicite d'un bout a l'autre du pipeline;
- une forme assez contractuelle (pas seulement narrative/prose) pour `NOW` et `DELTA-NOW`;
- la prevention robuste des formulations fautives du modele sur l'acces au temps de reference.

### Cartographie operationnelle (lot 1)
- `chat_service.chat_response`
  - role: source canonique du `NOW` de tour (`user_timestamp`, propage en `now_iso_value`).
  - forme injectee: timestamp ISO UTC (`YYYY-MM-DDTHH:MM:SSZ`).
  - statut: `canonique`.
- `chat_prompt_context.build_augmented_system`
  - role: exposition du repere temporel global dans le prompt augmente.
  - forme injectee: bloc `[RÉFÉRENCE TEMPORELLE]` avec `NOW: ...`, `TIMEZONE: ...`, puis phrase humaine "Nous sommes le ...".
  - statut: `partiellement contractuel` (socle structurel canonique + prose secondaire).
- `conv_store.build_prompt_messages(..., now=...)` + `conv_store.delta_t_label`
  - role: calcul des labels relatifs par message depuis le `NOW` de tour.
  - forme injectee: prefixes `[à l'instant]`, `[aujourd'hui ...]`, `[hier ...]`, `[il y a ...]`.
  - statut: `derive` (source canonique) + `narratif` (sortie humaine).
- `conv_store._silence_label`
  - role: marquer les ruptures temporelles entre messages consecutifs.
  - forme injectee: `[— silence de X —]`.
  - statut: `derive` + `narratif`.
- `conv_store._get_active_summary` + `_make_summary_message`
  - role: injection du resume actif antérieur.
  - forme injectee: `[Résumé de la période ...]` + contenu resume.
  - statut: `partiellement contractuel` (entete stable, contenu narratif).
- `conv_store._make_memory_context_message`
  - role: contextualiser les souvenirs retenus avec leurs resumes parents.
  - forme injectee: `[Contexte du souvenir — résumé ...]`.
  - statut: `partiellement contractuel`.
- `conv_store._make_memory_message`
  - role: injecter les souvenirs pertinents avec leur position relative au tour.
  - forme injectee: `[Mémoire — souvenirs pertinents]` + lignes prefixees par `delta_t_label`.
  - statut: `partiellement contractuel`.
- `conv_store._make_context_hints_message`
  - role: injecter des indices contextuels recents avec horodatage relatif.
  - forme injectee: `[Indices contextuels recents]` + lignes avec label relatif et `confidence`.
  - statut: `partiellement contractuel`.

### Zones encore trop narratives (lot 1)
- La phrase humaine du bloc `[RÉFÉRENCE TEMPORELLE]` reste en prose naturelle (lisible, mais moins stable qu'un champ strict).
- `delta_t_label` encode des classes temporelles en langue naturelle (`hier`, `aujourd'hui`, `il y a ...`), pas en schema strict.
- Les marqueurs de silence sont narratifs (`silence de ...`) et non normalises en code contractuel.
- Les contenus injectes de resume/souvenirs/indices restent textuels metier (necessaire pour le dialogue, mais non contractuels).

### Alignement des prompts statiques (lot 1)
- `app/prompts/main_hermeneutical.txt`: aligne sur la these "temps du discours" et l'usage de `REFERENCE TEMPORELLE`/Delta-T, mais partiellement en retard sur la forme canonique actuelle (`NOW:` + `TIMEZONE:` non explicites dans ce texte statique).
- `app/prompts/main_hermeneutical.txt`: ne formule pas encore explicitement l'interdit "ne pas pretendre etre prive d'ancrage temporel quand `NOW` est fourni" (point a traiter dans un lot suivant).
- `app/prompts/main_system.txt`: neutre et compatible, sans contradiction directe avec le contrat temporel.

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
