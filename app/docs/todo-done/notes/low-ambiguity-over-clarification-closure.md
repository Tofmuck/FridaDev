# Low-Ambiguity Over-Clarification - Closure

Document de cloture du mini-lot A+D livre le 2026-04-19 pour reduire les faux positifs de clarification sur des tours ordinaires peu ambigus, tout en conservant les vrais cas de cadrage.

Mise a jour le 2026-04-19:
- la premiere version de `A` avait surcorrige `referent`;
- le micro-lot de suivi a requalifie cette partie amont sans retoucher `D`.

## Contexte

Diagnostic retenu avant correctif:
- la surclarification venait surtout de l'amont (`user_turn_signals` -> `judgment_posture=clarify`);
- l'aval corrigeait certains cas, mais pas assez pour les interrogations simples.

Symptome cible:
- tours quotidiens et localement evidents, par exemple:
  - `t'as vu l'heure ?`
  - `Je me rends compte de ca... t'as vu l'heure ?`

## Correctif retenu

### A. Amont - faux positifs `referent`

Fichier:
- `app/core/hermeneutic_node/inputs/user_turn_input.py`

Ajustements livres en deux temps:
- premier lot: baisse des faux positifs `referent` sur des tours quotidiens peu ambigus;
- micro-lot de requalification: suppression du cutoff brut par longueur et retrait du critere "dernier message assistant substantiel" comme contexte resolutif general.

Critere retenu apres requalification:
- le contexte recent n'est resolutif que s'il nomme explicitement un artefact ou support concret (`patch`, `diff`, `texte`, `bloc`, `fichier`, etc.), ou s'il partage un vrai recouvrement lexical substantiel avec le tour courant;
- un deictique en amont du tour peut etre desamorce seulement si la clause finale du tour porte a elle seule un ancrage explicite non deictique.

Effet cible:
- eviter qu'un simple `ca` dans une question ordinaire suffise a faire tomber le tour en ambiguite;
- garder les clarifications quand le tour reste deictique sans contexte resolutif reel.

### D. Aval - normalisation anti-surclarification

Fichier:
- `app/core/hermeneutic_node/validation/validation_agent.py`

Ajustement:
- extension de la normalisation low-ambiguity aux gestes `interrogation` (en plus de `exposition`, `positionnement`, `adresse_relationnelle`), avec les memes garde-fous:
  - pas d'ambiguite;
  - pas de sous-determination;
  - aucune famille de signal active;
  - pas de `source_conflicts`;
  - posture primaire `answer`.

Effet cible:
- proteger aussi les questions simples contre des `clarify` bureaucratiques en sortie de validation.

## Surface touchee

Code:
- `app/core/hermeneutic_node/inputs/user_turn_input.py`
- `app/core/hermeneutic_node/validation/validation_agent.py`

Tests:
- `app/tests/unit/core/hermeneutic_node/inputs/test_user_turn_input.py`
- `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py`
- `app/tests/unit/core/hermeneutic_node/runtime/test_primary_node.py`

## Preuves

Preuves unitaires ajoutees/ajustees:
- `user_turn_input`:
  - un message assistant non lie ne suffit plus a desamorcer `referent`;
  - `Corrige ca`, `Je pense a ca depuis hier, tu peux clarifier ?` et `Reprends ce point` restent ambigus;
  - `Je me rends compte de ca... t'as vu l'heure ?` ne force pas `referent`.
- `validation_agent`:
  - une interrogation peu ambigue peut etre renormalisee de `clarify` vers `confirm`;
  - une interrogation avec vrai signal ambigu reste en `clarify`.
- `primary_node`:
  - un tour quotidien peu ambigu reste en posture `answer` et regime `simple`.

## Hors scope assume

Ce mini-lot ne rouvre pas:
- identity;
- memory/gouvernance;
- read-model/admin;
- refonte doctrinale large du prompt.

## Statut documentaire

- note de cloture ajoutee: oui (ce document);
- mise a jour de spec vivante: non.

Raison:
- la doctrine cible ne change pas (meta-clarification seulement quand necessaire);
- le lot ajuste des garde-fous d'implementation pour mieux respecter cette doctrine deja posee, et la mise a jour du 2026-04-19 corrige explicitement une sur-correction amont apparue dans la premiere version.
