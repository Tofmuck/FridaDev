# Chat Time Grounding TODO

## Objectif
Ouvrir un premier chantier produit borne pour rendre le grounding temporel du chat plus contractuel, a partir de l'existant reel.

Reference stable:
- `app/docs/states/specs/chat-time-grounding-contract.md`

## TODO

### Lot 1 - Cadrage et preuve de lecture du reel
- [ ] Cartographier les points d'injection temporelle reels (`chat_prompt_context`, `chat_service`, `conv_store`) et confirmer leur role exact.
- [ ] Lister les zones ou la temporalite reste surtout narrative/prose et pas encore assez contractuelle.
- [ ] Verifier l'alignement des prompts statiques avec le contrat de grounding temporel.

### Lot 2 - Forme canonique de NOW
- [ ] Verrouiller la forme canonique de `NOW` de tour (champ attendu, precision, timezone explicite).
- [ ] Decider si la forme actuelle est suffisante ou si un format plus contractuel est requis.
- [ ] Definir les regles d'affichage absolu vs relatif attendues pour les reponses temporelles.

### Lot 3 - Forme canonique de DELTA-NOW
- [ ] Auditer la forme actuelle des labels relatifs (`delta_t_label`) et des marqueurs de silence.
- [ ] Verrouiller ce qui doit rester lisible humainement dans les labels relatifs.
- [ ] Verrouiller ce qui doit devenir plus stable/contractuel pour eviter les ambiguitees.

### Lot 4 - Comportements attendus et interdits
- [ ] Interdire explicitement les formulations du type "je n'ai pas acces a l'heure reelle" lorsque `NOW` est fourni.
- [ ] Interdire les regimes temporels improvises ("ce matin", "ce soir", etc.) sans ancrage robuste.
- [ ] Definir le comportement attendu pour "derniere fois qu'on a parle" (restitution temporellement situee).

### Lot 5 - Plan de tests a implementer ensuite
- [ ] Lister les tests produit/comportement a ajouter pour valider le grounding temporel.
- [ ] Lister les tests de structure prompt a ajouter pour verifier la presence/forme des briques temporelles.
- [ ] Lister les tests de non-regression sur les cas temporels evidents (reprise, silence, delta relatif).

## Risques / vigilance
- Ne pas brouiller memoire et discours temporel.
- Ne pas multiplier trop tot des couches speculatives sans effet concret.
- Ne pas construire une pseudo-architecture grandiose avant de stabiliser les invariants utiles.
- Garder un chantier petit, testable, et reversible.
