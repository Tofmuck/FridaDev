# Hermeneutic Suspension / Auto-Web TODO

Statut: ferme
Classement: `app/docs/todo-done/refactors/`
Origine: diagnostic code+traces revalide le `2026-04-06`

## Decision de cloture

- Le runtime actuel est accepte tel quel.
- Ce TODO ne porte plus d'action runtime immediate.
- Le rattrapage anti-suspension `no-web -> web` n'est pas decide maintenant.
- Si ce sujet revient plus tard, il devra etre rouvert dans un nouveau TODO separe.

## Etat runtime retenu

- Runtime actuel: web manuel uniquement.
- `web_search=true` declenche le web avec `activation_mode = manual`.
- `web_search=false` laisse le web en `activation_mode = not_requested`.
- Les demandes `source`, `lien`, `reference`, `verification pure`, les confirmations conversationnelles, et les cas conceptuels nettoyes n'activent pas le web pre-node.
- `activation_mode = manual|auto|not_requested` reste le contrat canonique du `web_input`, mais `auto` n'est pas active dans le runtime actuel.

## Points fermes et traces gardees

- [x] Le tour suspendu de reference a ete diagnostique proprement:
  - `conversation_id = a2bebfd3-96d3-4088-b622-6495461f534a`
  - `turn_id = turn-6a02836c-b2e8-4813-88ce-05915d590a59`
  - `decision_source = primary`
  - trajectoire observee: `verification_externe_requise` puis `suspend`
- [x] Le faux positif amont a ete corrige:
  - `preuve` dans `faire preuve de ...`
  - `lien` dans `lien a l'autre`
- [x] Les demandes explicites de verification, de source, de reference et de lien restent classables comme `factuelle` et/ou `web` pour le noeud et l'observabilite.
- [x] L'observabilite compacte expose maintenant `provenances` dans `user_turn.regime_probatoire`.
- [x] La branche trop large `factuelle + atemporale + sans provenance => web` a ete retiree.
- [x] L'auto-web pre-node lexicalise a ete retire:
  - `web_search=false` laisse maintenant le web en `not_requested`
  - `source/lien/reference/verification` ne suffisent plus a lancer le web avant le noeud
- [x] Le bouton manuel `web_search=true` reste intact.
- [x] Le statut reel est documente honnetement dans les docs vivantes.

## Prochaine reouverture eventuelle

- Aucun travail runtime n'est demande maintenant.
- Si un vrai rattrapage anti-suspension `no-web -> web` redevient souhaitable, il devra faire l'objet d'un nouveau TODO distinct.
