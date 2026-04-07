# Hermeneutic Suspension / Auto-Web TODO

Statut: ouvert
Classement: `app/docs/todo-todo/memory/`
Origine: diagnostic code+traces revalide le `2026-04-06`

## Etat courant

- Runtime actuel: web manuel uniquement.
- `web_search=true` declenche le web avec `activation_mode = manual`.
- `web_search=false` laisse le web en `activation_mode = not_requested`.
- Les demandes `source`, `lien`, `reference`, `verification pure`, les confirmations conversationnelles, et les cas conceptuels nettoyes n'activent pas le web pre-node.
- `activation_mode = manual|auto|not_requested` reste le contrat canonique du `web_input`, mais `auto` n'est pas active dans le runtime actuel.
- Le vrai rattrapage anti-suspension `no-web -> web` n'est pas implemente.
- Pas de bug runtime immediat retenu a ce stade.

## Ce qui est ferme

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
- [x] Le statut reel est documente honnetement dans les docs vivantes:
  - runtime actuel sans auto-web actif
  - `activation_mode = auto` reserve a un futur design eventuel

## Ce qui reste vraiment

- [ ] Decider plus tard s'il faut vraiment concevoir un rattrapage anti-suspension `no-web -> web`.
- [ ] Si oui, ouvrir un lot de design dedie avant tout nouveau patch runtime.
- [ ] Sinon, archiver ce TODO comme clos dans un pas separe.

## Hors scope actuel

- pas de patch runtime maintenant
- pas de web auto pre-node
- pas d'heuristique lexicale ou semantique de recherche web
- pas de modification de `judgment_posture.py`
- pas de modification du `validation_agent`

## Prochain geste recommande

- Rien cote runtime pour l'instant.
- On peut rester comme ca tant qu'aucun lot dedie de rattrapage anti-suspension n'est explicitement ouvert.
- Si le besoin revient, il faudra d'abord trancher le design aval proprement.
- Si le besoin ne revient pas, le prochain geste propre sera un archivage documentaire de ce TODO.
