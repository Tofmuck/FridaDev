# Chat Time Grounding TODO

## Objectif
Ouvrir un premier chantier produit borne pour rendre le grounding temporel du chat plus contractuel, a partir de l'existant reel.

Reference stable:
- `app/docs/states/specs/chat-time-grounding-contract.md`

## TODO

### Lot 1 - Cadrage et preuve de lecture du reel
- [x] Premier livrable concret: unifier la source canonique de `NOW` de tour entre la prose `[RÉFÉRENCE TEMPORELLE]` et le `now` utilise par `delta_t_label`.
- [x] Cartographier les points d'injection temporelle reels (`chat_prompt_context`, `chat_service`, `conv_store`) et confirmer leur role exact.
- [x] Lister les zones ou la temporalite reste surtout narrative/prose et pas encore assez contractuelle.
- [x] Verifier l'alignement des prompts statiques avec le contrat de grounding temporel.

### Lot 2 - Forme canonique de NOW
- [x] Verrouiller la forme canonique de `NOW` de tour (champ attendu, precision, timezone explicite).
- [x] Decider si la forme actuelle est suffisante ou si un format plus contractuel est requis.
- [x] Definir les regles d'affichage absolu vs relatif attendues pour les reponses temporelles.

### Lot 3 - Forme canonique de DELTA-NOW
- [x] Auditer la forme actuelle des labels relatifs (`delta_t_label`) et des marqueurs de silence.
- [x] Verrouiller ce qui doit rester lisible humainement dans les labels relatifs.
- [x] Verrouiller ce qui doit devenir plus stable/contractuel pour eviter les ambiguitees.

### Lot 4 - Implementation comportementale et alignement prompt/runtime
- [x] Implementer l'interdiction des formulations niant l'acces au temps de reference du tour quand `NOW` est fourni.
- [x] Aligner et faire respecter l'usage ancre des regimes de journee (`ce matin`, `cet apres-midi`, `ce soir`, `cette nuit`) entre prompt statique et runtime.
- [x] Aligner et faire respecter l'application de la regle lot 2 pour "quand est-ce qu'on a parle la derniere fois ?" (`relatif` prioritaire, `absolu` court si utile).

### Lot 5 - Preuves automatiques et non-regressions
- [x] Implementer les tests de structure du prompt statique hermeneutique (brique `[RÉFÉRENCE TEMPORELLE]`, `NOW`, `TIMEZONE`, formes Delta-T et silence, garde-fous lot 4).
- [x] Verifier par tests d'assemblage runtime la presence de la brique temporelle, du `NOW` canonique, de `TIMEZONE`, des rappels comportementaux et de l'ordre des briques.
- [x] Ajouter des tests unitaires cibles de non-regression sur `delta_t_label`, `_silence_label` et l'insertion effective des marqueurs via `build_prompt_messages(...)`.

## Risques / vigilance
- Ne pas brouiller memoire et discours temporel.
- Ne pas multiplier trop tot des couches speculatives sans effet concret.
- Ne pas construire une pseudo-architecture grandiose avant de stabiliser les invariants utiles.
- Garder un chantier petit, testable, et reversible.
