# Log Follow-ups TODO (post-MVP)

## Objectif
Traiter les irritants restants de l'UI logs apres cloture du MVP, sans rouvrir le chantier principal archive.

Reference archivee (ne pas rouvrir):
- `app/docs/todo-done/refactors/log-module-todo.md`

## TODO

### Lot 1 - Filtres et suppression UI plus robustes
- [ ] Remplacer le champ libre `conversation` par une liste des conversations presentes dans les logs.
- [ ] Rendre la liste `turn` dependante de la conversation selectionnee.
- [ ] Garder la liste `turn` vide ou desactivee tant qu'aucune conversation n'est selectionnee.
- [ ] Remplacer le champ libre `stage` par une liste deroulante alignee sur les stages reellement supportes par le module logs.
- [ ] Aligner `Supprimer logs conversation` sur la conversation actuellement selectionnee (sans ressaisie manuelle d'id).
- [ ] Aligner `Supprimer logs tour` sur le tour actuellement selectionne (sans ressaisie manuelle d'id).
- [ ] Ajouter un test d'integration frontend qui prouve le flux: selection conversation -> liste tours -> suppression scopee.

### Lot 2 - Export Markdown structure
- [ ] Ajouter un export Markdown structure scope `conversation` (lisible humainement, pas un dump brut).
- [ ] Ajouter un export Markdown structure scope `turn` (lisible humainement, pas un dump brut).
- [ ] Verrouiller le format Markdown minimal (entete de scope, table/sections d'evenements, metadonnees sobres).
- [ ] Clarifier explicitement la granularite `par message`: distincte du tour dans le modele actuel, ou differee hors MVP follow-up.
- [ ] Ajouter un test de preuve sur le format exporte (structure attendue + absence de dump massif).

### Cadrage a clarifier avant implementation
- [ ] Verrouiller la source de donnees pour alimenter les listes `conversation` et `turn` (reutilisation de la lecture paginee existante vs support backend dedie).
- [ ] Verifier l'impact UX si la pagination ne contient pas toutes les conversations/tours disponibles.
- [ ] Verrouiller la strategie pour l'export Markdown (transformation frontend sur reponse existante vs support backend dedie).

## Risques / vigilance
- Ne pas transformer ce follow-up en chantier tentaculaire.
- Eviter toute confusion entre filtre UI et source de verite backend.
- Ne pas reintroduire une suppression fragile basee sur des ids ressaisis a la main.
- Eviter une confusion de granularite entre `tour` et `message` lors de l'export.
- Eviter un export Markdown pseudo-lisible qui redevient un dump de payload.
- Garder le comportement coherent avec le contrat logs (`states/specs/log-module-contract.md`).
