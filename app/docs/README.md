# Docs

Organisation finale retenue:

- `states/`: references stables (specs, baselines, policies, etats projet) + archive `legacy/`
- `todo-done/`: preuves de chantiers termines (audits, validations, refactors, notes, migrations)
- `todo-todo/`: chantiers ouverts organises par domaine

Regle simple:

- ce qui decrit un etat de reference va dans `states/`
- ce qui prouve un travail boucle va dans `todo-done/`
- ce qui pilote un travail a faire va dans `todo-todo/`

Sous-structure en place:

- `states/specs/`: specs normatives
- `states/baselines/`: baselines et photos techniques datees
- `states/project/`: etats de reference projet (FR/EN)
- `states/policies/`: politiques de retention/gouvernance
- `states/legacy/`: archives legacy explicites (`PROJET.md`, `sanity-frida-mini.md`)
- `states/architecture/`: conventions et cadrage architectural
- `states/operations/`: guides operatoires

- `todo-done/audits/`: audits finalises
- `todo-done/validations/`: rapports de validation
- `todo-done/refactors/`: roadmaps de refacto cloturees
- `todo-done/migrations/`: roadmaps de migration archivees
- `todo-done/notes/`: notes de nettoyage et cadrage documentaire

- `todo-todo/memory/`: roadmaps memoire/hermeneutique ouvertes
- `todo-todo/product/`: roadmaps produit/installation ouvertes
- `todo-todo/admin/`, `todo-todo/migration/`: reserves pour futurs chantiers ouverts

Notes:
- la racine `app/docs` est volontairement minimale et ne garde que ce `README.md`
- roadmap ouverte migration/config: `todo-todo/product/Frida-installation-config.md`
- roadmap ouverte memoire/hermeneutique: `todo-todo/memory/hermeneutical-add-todo.md`
- les anciennes roadmaps `Migration_FridaDev-todo.md` et `memory-todo.md` sont archivees dans `todo-done/migrations/`
- nettoyage faible valeur deja applique: `todo-done/patch_done.md` et `todo-todo/smart-todo.md` supprimes
