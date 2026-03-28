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

### Lot 3 - Clarification semantique des evenements
- [ ] Prioriser l'amelioration `arbiter` cote logs (redevabilite des decisions) avant tout chantier de re-ecriture du prompt arbitre.
- [ ] Clarifier que le probleme principal `arbiter` est la visibilite logs des decisions deja prises (et non une re-ecriture immediate de la logique arbitre).
- [ ] Enrichir `arbiter` pour exposer `rejected_candidates`, une synthese exploitable des motifs de rejet, `model` arbitre, et `decision_source`/fallback.
- [ ] Clarifier `identities_read` en separant explicitement les natures de lecture: identite fixe/statique, identite durable memoire, identite fluctuante context hints/evidence.
- [ ] Expliciter que le stage `identities_read` actuel melange plusieurs lectures de nature differente et n'est pas assez parlant sans taxonomie.
- [ ] Choisir un contrat lisible pour `identities_read`: `source_kind` explicite ou stages distincts, sans dump massif.
- [ ] Clarifier `embedding` avec une taxonomie de finalite/source stable (`query`, `trace_user`, `trace_assistant`, `summary`, autres cas futurs) et une finalite fonctionnelle lisible.
- [ ] Verrouiller que les embeddings de resumes sont identifiables explicitement dans les logs.
- [ ] Clarifier `identity_write` quand `status=skipped` (notamment mode shadow) pour eviter une lecture ambigue.
- [ ] Clarifier la visibilite `identity_write` par cote (`frida` / `user`) et traiter le cas ou un seul cote apparait alors qu'une vision humaine attendrait plus de contexte.
- [ ] Clarifier la frontiere `identity_write`: preview/evidence en mode shadow vs vraie ecriture durable en memoire identitaire.
- [ ] Clarifier `summaries`: distinguer explicitement "resume actif injecte au prompt" vs "resume genere dans ce tour".
- [ ] Clarifier `llm_call` en mode stream pour exposer une metrique finale exploitable (sans dump de reponse).
- [ ] Ajouter des tests de preuve cibles pour ces clarifications semantiques (contrat lisible + sobriete preservee).

### Cadrage a clarifier avant implementation
- [ ] Verrouiller la source de donnees pour alimenter les listes `conversation` et `turn` (reutilisation de la lecture paginee existante vs support backend dedie).
- [ ] Verifier l'impact UX si la pagination ne contient pas toutes les conversations/tours disponibles.
- [ ] Verrouiller la strategie pour l'export Markdown (transformation frontend sur reponse existante vs support backend dedie).
- [ ] Verrouiller la frontiere "observabilite vs lecture metier" pour ces clarifications, afin d'eviter un glissement vers des payloads explicatifs trop lourds.

## Risques / vigilance
- Ne pas transformer ce follow-up en chantier tentaculaire.
- Eviter toute confusion entre filtre UI et source de verite backend.
- Ne pas reintroduire une suppression fragile basee sur des ids ressaisis a la main.
- Eviter une confusion de granularite entre `tour` et `message` lors de l'export.
- Eviter un export Markdown pseudo-lisible qui redevient un dump de payload.
- Eviter de melanger identite statique, identite durable et hints fluctuants dans un seul signal illisible.
- Eviter un `embedding` trop pauvre (incomprehensible) ou trop riche (quasi dump brut).
- Eviter des clarifications `arbiter`/`identity_write` qui cassent la sobriete du contrat logs.
- Eviter de confondre "mieux exposer les decisions d'arbitre" avec "re-ecrire tout de suite le prompt arbitre".
- Garder le comportement coherent avec le contrat logs (`states/specs/log-module-contract.md`).
