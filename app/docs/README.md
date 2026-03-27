# Docs

Organisation retenue:

- `states/`: etats de reference, baselines, specs et documents de situation
- `todo-done/`: chantiers termines, audits, politiques et validations deja executes
- `todo-todo/`: chantiers ouverts, feuilles de route et briefs d'action

Regle simple:

- ce qui decrit un etat ou une reference stable va dans `states/`
- ce qui documente un travail boucle va dans `todo-done/`
- ce qui pilote un travail a faire va dans `todo-todo/`

Sous-structure cible (Lot 1 rangement):

- `states/specs/`: specs normatives
- `states/baselines/`: baselines et photos techniques datees
- `states/project/`: etats de reference projet (FR/EN)
- `states/policies/`: politiques de retention/gouvernance
- `states/architecture/`, `states/operations/`, `states/legacy/`: reserves pour les lots suivants

- `todo-done/audits/`: audits finalises
- `todo-done/validations/`: rapports de validation
- `todo-done/migrations/`, `todo-done/notes/`: reserves pour les lots suivants

- `todo-todo/memory/`: roadmaps memoire/hermeneutique ouvertes
- `todo-todo/product/`: roadmaps produit/installation ouvertes
- `todo-todo/admin/`, `todo-todo/migration/`: reserves pour les lots suivants

Note:
- les documents canoniques de pilotage (`admin-*`, `fridadev_*`) restent a la racine `app/docs/`
- aucune suppression ni fusion n'est faite dans ce lot
