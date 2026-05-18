# Chat Time Grounding Contract (phase 0)

## Objectif
Fixer un cadrage normatif court pour le grounding temporel du chat, a partir de l'etat reel du repo, avant implementation.

## 1) Constat d'etat reel
Ce qui existe deja dans le code:
- `app/core/chat_prompt_context.py` injecte une brique `[RÉFÉRENCE TEMPORELLE]` avec un `maintenant` explicite et timezone.
- `app/core/chat_service.py` fixe deja un `now` de tour (timestamp canonique de message utilisateur) et le propage a la construction du prompt.
- `app/core/conv_store.py` porte deja des labels Delta-T (`delta_t_label`) et des marqueurs de silence (`_silence_label`) injectes dans les messages de prompt.
- `app/prompts/main_hermeneutical.txt` formalise deja l'interpretation du repere temporel, des deltas et des silences.
- resume actif, contextes de souvenirs parents, souvenirs et indices contextuels sont situes sur la temporalite locale Frida quand une date est visible.
- Contradiction principale initiale (desormais resolue dans le code courant):
  - auparavant, `chat_prompt_context.build_augmented_system()` recalculait un `datetime.now(...)` local en concurrence avec le `NOW` de tour de `chat_service`;
  - maintenant, `chat_service.chat_response()` fixe `user_timestamp` / `now_iso_value` et `build_augmented_system(...)` consomme explicitement ce `now_iso`;
  - la source de verite du `NOW` de tour est donc unique a l'echelle du pipeline prompt + labels relatifs.

Ce que cela permet deja:
- situer une partie du dialogue avec une ancre locale absolue et une temporalite relative lisible;
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
  - forme injectee: prefixes `[lundi 18 mai 2026 à 19h27 Europe/Paris — aujourd'hui]`, `[dimanche 17 mai 2026 à 19h27 Europe/Paris — hier]`, `[vendredi 15 mai 2026 à 19h27 Europe/Paris — il y a 3 jours]`.
  - statut: `derive` (source canonique) + `ancre absolue locale visible` + `relatif narratif`.
- `conv_store._silence_label`
  - role: marquer les ruptures temporelles entre messages consecutifs.
  - forme injectee: `[— silence de X —]`.
  - statut: `derive` + `narratif`.
- `conv_store._get_active_summary` + `_make_summary_message`
  - role: injection du resume actif antérieur.
  - forme injectee: `[Résumé de la période ...]` + contenu resume, ou `[Résumé]` quand aucun bornage temporel n'est disponible; les dates de periode sont derivees en date locale `FRIDA_TIMEZONE`.
  - statut: `partiellement contractuel` (entete stable en date locale, contenu narratif).
- `conv_store._make_memory_context_message`
  - role: contextualiser les souvenirs retenus avec leurs resumes parents.
  - forme injectee: `[Contexte du souvenir S1 — résumé ...]` quand un repere parent est utile, sinon `[Contexte du souvenir — résumé ...]`; les dates de periode sont derivees en date locale `FRIDA_TIMEZONE`.
  - statut: `partiellement contractuel` (entete stable en date locale).
- `conv_store._make_memory_message`
  - role: injecter les souvenirs pertinents avec leur position relative au tour.
  - forme injectee: `[Mémoire — souvenirs pertinents]` + lignes prefixees par `delta_t_label`, avec `[contexte S1]` si la trace est liee au resume parent de meme repere.
  - statut: `partiellement contractuel`.
- `conv_store._make_context_hints_message`
  - role: injecter des indices contextuels recents avec horodatage relatif.
  - forme injectee: `[Indices contextuels recents]` + lignes avec label relatif et `confidence`.
  - statut: `partiellement contractuel`.
- `web_search.reformulate` + blocs `[RECHERCHE WEB]`
  - role: reformuler la requete web et injecter le contexte web dans le prompt principal.
  - forme injectee: `Nous sommes le lundi 18 mai 2026 Europe/Paris.` dans le prompt de reformulation web, puis `[RECHERCHE WEB — lundi 18 mai 2026 Europe/Paris]` dans les blocs web.
  - statut: `derive du NOW de tour` + `date locale Frida visible` + `timezone visible`.

### Zones encore trop narratives (lot 1)
- La phrase humaine du bloc `[RÉFÉRENCE TEMPORELLE]` reste en prose naturelle (lisible, mais moins stable qu'un champ strict).
- `delta_t_label` encode une ancre absolue locale visible (`jour date heure timezone`) et un relatif humain (`hier`, `aujourd'hui`, `il y a ...`). La classe stable reste interne au payload de calcul.
- Les marqueurs de silence sont narratifs (`silence de ...`) et non normalises en code contractuel.
- Les contenus injectes de resume/souvenirs/indices restent textuels metier (necessaire pour le dialogue, mais non contractuels).

### Alignement des prompts statiques (lot 1)
- `app/prompts/main_hermeneutical.txt`: aligne sur la these "temps du discours", l'usage de `[RÉFÉRENCE TEMPORELLE]`, les lignes `NOW:` / `TIMEZONE:` et les labels Delta-T absolus + relatifs.
- `app/prompts/main_hermeneutical.txt`: formule explicitement l'interdit de pretendre etre prive d'ancrage temporel quand `NOW` est fourni.
- `app/prompts/main_system.txt`: neutre et compatible, sans contradiction directe avec le contrat temporel.

## 2) These normative
Dans FridaDev, le temps n'est pas d'abord une donnee de memoire: c'est une condition de forme du discours.
La memoire conserve des traces horodatees, mais le discours en produit le sens temporel relativement a un `NOW` canonique de tour.
Le `DELTA-NOW` est un operateur de lisibilite du passe pour le present du dialogue, pas un habillage cosmetique.
Si le systeme injecte un `NOW` de tour, le modele ne doit pas pretendre qu'il est prive d'ancrage temporel de reference.

## 3) Invariants produit
- Chaque tour doit avoir un `NOW` canonique, autoritaire, explicite, timezone incluse.
- Les messages injectes dans le prompt doivent rester situables relativement a ce `NOW`.
- Les labels Delta-T visibles sur les messages doivent aussi porter la date locale absolue, l'heure locale et la timezone afin d'eviter toute reconstruction fragile du jour a partir d'une heure correcte.
- Les dates visibles des resumes actifs, des contextes de souvenirs parents et du dialogue envoye au resumeur doivent etre calculees en date locale `FRIDA_TIMEZONE`, jamais par troncature brute d'un timestamp UTC.
- Les dates visibles par la lane web, reformulation comprise, doivent etre calculees depuis le `NOW` de tour en date locale `FRIDA_TIMEZONE`, jamais depuis une date humaine UTC hote.
- Les modeles secondaires qui influencent l'interpretation finale ne doivent pas reconstruire `hier` / `aujourd'hui` depuis des timestamps UTC bruts:
  - le validation agent recoit une `temporal_reference` prioritaire et des `temporal_label` locaux dans son contexte principal;
  - l'arbitre memoire recoit le `NOW` local du tour, des labels locaux pour le recent context et les candidats, et ne doit pas inferer le jour local depuis l'UTC brut;
  - identity extractor et identity periodic ne raisonnent pas temporellement: ils rejettent les claims relatifs faibles (`hier`, `aujourd'hui`, `depuis hier`, `en ce moment`) au lieu de les consolider en identite durable;
  - stimmung ignore volontairement timestamps, delais, gaps et claims relatifs; ce caller ne produit qu'un signal affectif centre sur le tour courant.
- Le systeme doit permettre des reponses temporellement situees aux questions du type:
  - "quand est-ce qu'on a parle la derniere fois ?"
  - en forme relative et/ou absolue selon le besoin.
- Le modele ne doit pas declarer qu'il n'a pas acces au temps de reference quand ce temps est fourni.
- Le temps regle aussi la reprise, la re-situation et la continuite du discours.

## 3 bis) Regles d'affichage des reponses temporelles (absolu vs relatif)
Regle generale:
- par defaut, privilegier la forme la plus utile a la question posee;
- la forme relative sert la reprise conversationnelle;
- la forme absolue sert la precision factuelle;
- combiner les deux seulement si cela augmente la clarte utile.

Cas cibles et forme attendue:
- question de reprise (`quand est-ce qu'on a parle la derniere fois ?`): `relatif + absolu court`.
  - exemple: `vendredi en fin de journee, vers 17h05`.
- question de precision explicite (`a quelle heure exactement ?`): `absolu` en premier, `relatif` optionnel.
  - exemple: `vendredi 27 mars 2026 a 17h05`.
- question floue (`ca fait combien de temps ?`): `relatif` en premier, `absolu` optionnel si utile.
  - exemple: `il y a environ une heure`.
- reprise ordinaire d'echange recent: `relatif` seul par defaut.
  - exemple: `vendredi en fin de journee`.

Regles de sobriete:
- ne pas afficher l'absolu complet systematiquement par lourdeur;
- ne pas rester en relatif seul quand la precision explicite est demandee;
- ne pas forcer une granularite excessive (secondes/offset) sans besoin explicite.

Lien avec les lots suivants:
- lot 3 stabilise la forme contractuelle de `DELTA-NOW`;
- lot 4 interdit les formulations temporelles improvisees sans ancrage.

## 3 ter) Contrat DELTA-NOW et marqueurs de silence (lot 3)
Audit bref de l'existant (`app/core/conv_store.py`):
- `delta_t_label` rend aujourd'hui une ancre absolue locale suivie d'un relatif:
  - `jour D mois YYYY à HhMM TIMEZONE — à l'instant`
  - `jour D mois YYYY à HhMM TIMEZONE — il y a X minute(s)`
  - `jour D mois YYYY à HhMM TIMEZONE — aujourd'hui`
  - `jour D mois YYYY à HhMM TIMEZONE — hier`
  - `jour D mois YYYY à HhMM TIMEZONE — il y a X jour(s)`
  - `jour D mois YYYY à HhMM TIMEZONE — il y a X semaine(s)`
  - `jour D mois YYYY à HhMM TIMEZONE — il y a X mois`
  - `jour D mois YYYY à HhMM TIMEZONE — il y a X an(s)`
- `_silence_label` rend aujourd'hui:
  - `[— silence de quelques secondes —]`
  - `[— silence de X minute(s) —]`
  - `[— silence de X heure(s) —]`
  - `[— silence d'un jour —]`
  - `[— silence de X jours —]`
  - `[— silence de X semaine(s) —]`
  - `[— silence de X mois —]`

Decision normative:
- `DELTA-NOW` reste lisible humainement dans le prompt.
- `DELTA-NOW` doit aussi porter une ancre locale absolue visible pour chaque message pertinent.
- `DELTA-NOW` doit porter une categorie stable testable (contrat), distincte du wording humain.
- Le contrat cible est donc a deux niveaux:
  - `delta_class` (stable): `just_now`, `minutes`, `same_day`, `yesterday`, `days`, `weeks`, `months`, `years`
  - `delta_label` (visible): rendu `date locale absolue + heure locale + timezone — relatif lisible`
- Seuils contractuels attendus (coherents avec l'existant):
  - `instant`: < 60 s
  - `minutes`: [60 s, 3600 s[
  - `today_clock`: meme date locale que `NOW` et >= 3600 s
  - `yesterday_clock`: date locale = veille de `NOW`
  - `days`: < 7 jours (hors today/yesterday)
  - `weeks`: < 30 jours
  - `months`: < 365 jours
  - `years`: >= 365 jours

Contrat des silences:
- Les marqueurs de silence ne restent pas purement narratifs.
- Ils suivent la meme logique a deux niveaux:
  - `silence_class` (stable): `silence_seconds`, `silence_minutes`, `silence_hours`, `silence_day`, `silence_days`, `silence_weeks`, `silence_months`
  - `silence_human` (lisible): forme `[— silence de ... —]`
- La classe stable sert de base de test/non-regression; le rendu humain conserve la lisibilite conversationnelle.

Frontiere lot 3 vs lot 4:
- lot 3 stabilise la categorisation contractuelle des deltas et silences;
- lot 4 definira les comportements de reponse interdits/attendus du modele;
- lot 3 ne redefinit pas ces comportements.

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
