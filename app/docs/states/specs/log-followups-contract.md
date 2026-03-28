# Log Follow-ups Contract (post-MVP)

## Objectif
Verrouiller les decisions de cadrage pour les follow-ups logs, avant implementation.
Ce document complete le contrat MVP (`states/specs/log-module-contract.md`) sans le modifier.

## 1) Source de donnees des selecteurs `conversation` / `turn`
Decision retenue:
- Les selecteurs UI ne doivent pas etre alimentes par la lecture paginee `GET /api/admin/logs/chat`.
- Source canonique: support backend dedie de metadonnees logs:
  - liste des `conversation_id` disponibles;
  - liste des `turn_id` pour une `conversation_id` donnee.

Pourquoi:
- la pagination timeline ne garantit pas une couverture complete;
- un selecteur incomplet cree une UX trompeuse.

Option ecartee:
- reconstruire les selecteurs depuis les items de la page courante.

## 2) Pagination et garanties UX
Decision retenue:
- La pagination actuelle reste reservee a la consultation timeline.
- Les selecteurs doivent afficher une liste complete pour leur scope.
- Si la source complete n'est pas disponible, le selecteur `turn` reste vide/desactive et l'UI doit l'indiquer explicitement.

## 3) Strategie export Markdown
Decision retenue:
- Export Markdown via support backend dedie, pour deux scopes:
  - `conversation`
  - `turn`
- Le frontend ne construit pas l'export depuis les pages deja chargees.

Pourquoi:
- format stable et lisible;
- couverture complete du scope (sans trou de pagination);
- responsabilite claire entre rendu UI et generation export.

Granularite `par message`:
- Non retenue par defaut a ce stade.
- Le follow-up reste borne a `conversation` + `turn` tant qu'un contrat explicite message-level n'existe pas.

## 4) Frontiere observabilite vs lecture metier
Decision retenue:
- Les follow-ups restent dans le perimetre observabilite.
- Pas de reconstruction des logs depuis les tables memoire metier.
- Les exports restent des exports de logs, pas des reconstructions metier.
- Les enrichissements semantiques doivent rester sobres (pas de dump brut prompt/contexte/evidence).

## 5) Ordre conseille de mise en oeuvre
1. Redevabilite `arbiter` cote logs (priorite forte):
   - raisons de rejet exploitables,
   - compte de rejet,
   - synthese motifs,
   - modele et source de decision/fallback.
2. Selecteurs UI `conversation`/`turn` + suppression pilotee par filtres.
3. Export Markdown structure (`conversation`, puis `turn`).
4. Clarifications semantiques restantes:
   - `identities_read`,
   - `embedding`,
   - `identity_write`,
   - `summaries`,
   - `llm_call` stream.

Note:
- La priorite `arbiter` concerne la visibilite logs des decisions deja prises.
- Une eventuelle re-ecriture du prompt arbitre est explicitement hors de ce premier lot.

## 6) Croissance de `app/web/log/log.js`
Decision retenue:
- `log.js` monofichier reste acceptable tant que le lot follow-up UI est borne.
- Si le lot grossit nettement, decoupage impose par responsabilite:
  - API / acces backend
  - etat / filtres UI
  - rendu
  - actions (suppression / export)
- Pas de decoupage premature cosmetique.
