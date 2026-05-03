# Docs - hub mainteneur

Cette racine reste volontairement minimale: `app/docs/README.md` est la porte d'entree mainteneur pour choisir quoi lire, pas un deuxieme etat projet.

Regle de classement:

- `states/`: references stables, specs, baselines, politiques, operations et etats projet.
- `todo-done/`: preuves de chantiers termines, audits, validations, migrations, refactors et notes archivees.
- `todo-todo/`: chantiers ouverts, organises par domaine.

Ne pas creer d'index concurrent sans besoin fort. Le README racine du repo donne la vue produit/runtime generale; ce fichier oriente dans la documentation structuree.

## Portes d'entree mainteneur

### Current-state

- Audit repo canonique: `todo-done/audits/fridadev_repo_audit.md`
- Audit global date du 2026-05-03: `states/audits/fridadev-global-audit-2026-05-03.md`
- Remediation active de l'audit global: `todo-todo/audits/fridadev-global-audit-remediation-todo.md`
- Cartographie runtime one-glance: `states/architecture/fridadev-current-runtime-pipeline.md`
- Etats projet dates du 2026-04-03: `states/project/Frida-State-french-03-04-26.md` et `states/project/Frida-State-english-03-04-26.md`

### Doctrine active

- Pouvoir de l'arbitre de reponse: `states/specs/response-arbiter-power-contract.md`
- Voix / identite / reprise apres ecart temporel: `states/specs/chat-enunciation-and-gap-contract.md`
- Plan doctrinal identity `static` / `mutable`: `states/policies/identity-new-contract-plan.md`
- Contrat de surface `Memory Admin`: `states/specs/memory-admin-surface-contract.md`
- Protocole streaming public: `states/specs/streaming-protocol.md`

### Archives utiles

- Migration OVH et chemins runtime: `todo-done/migrations/fridadev-to-frida-system-migration-todo.md`
- Cloture operatoire du nouveau contrat identitaire: `todo-done/refactors/identity-new-contract-todo.md`
- Grande roadmap hermeneutique archivee: `todo-done/notes/hermeneutical-add-todo.md`
- Bascule vers un arbitre de reponse LLM dominant: `todo-done/refactors/llm-dominant-response-arbiter-todo.md`
- Fiabilisation archivee du streaming des reponses: `todo-done/product/frida-response-streaming-todo.md`

## Docs a lire d'abord selon le chantier

### Cleanup / refactor repo

Lire d'abord:
- `todo-todo/audits/fridadev-global-audit-remediation-todo.md` pour les corrections actives issues de l'audit global du 2026-05-03.
- `states/audits/fridadev-global-audit-2026-05-03.md` pour la source de verite des findings.
- `todo-done/refactors/fridadev-repo-cleanup-prioritized-todo.md`
- `todo-done/audits/fridadev_repo_audit.md`
- `states/architecture/fridadev-current-runtime-pipeline.md`

But: relire le cleanup priorise livre et les decisions de sortie sans reouvrir une roadmap terminee.

### Runtime courant / chat

Lire d'abord:
- `states/architecture/fridadev-current-runtime-pipeline.md`
- `states/specs/streaming-protocol.md`
- `states/specs/chat-enunciation-and-gap-contract.md`
- `states/specs/response-arbiter-power-contract.md`

Archives utiles:
- `todo-done/product/frida-response-streaming-todo.md`
- `todo-done/notes/chat-enunciation-gap-validation-todo.md`

### Identity / doctrine

Lire d'abord:
- `states/policies/identity-new-contract-plan.md`
- `todo-done/refactors/identity-new-contract-todo.md`

Regle de lecture: garder ces deux references distinctes. Le plan reste doctrinal et actif; l'archive conserve la trace du chantier termine.

Specs liees:
- `states/specs/identity-read-model-contract.md`
- `states/specs/identity-surface-contract.md`
- `states/specs/identity-static-edit-contract.md`
- `states/specs/identity-mutable-edit-contract.md`
- `states/specs/identity-governance-contract.md`

### Memory / hermeneutics

Lire d'abord:
- `todo-todo/memory/hermeneutical-post-stabilization-todo.md`
- `states/architecture/memory-rag-current-pipeline-cartography.md`
- `states/specs/memory-admin-surface-contract.md`
- `states/specs/memory-rag-pre-arbiter-basket-contract.md`
- `states/specs/memory-rag-summaries-lane-contract.md`

Baselines et evaluations:
- `states/baselines/memory-rag-relevance-baseline-2026-04-10.md`
- `states/baselines/memory-rag-6A-evaluation-2026-04-10.md`
- `states/baselines/memory-rag-7B-evaluation-2026-04-10.md`
- `states/baselines/memory-rag-8C-evaluation-2026-04-10.md`
- `states/specs/memory-rag-evaluation-sheet.md`

Archives utiles:
- `todo-done/refactors/memory-rag-relevance-todo.md`
- `todo-done/refactors/hermeneutic-convergence-node-todo.md`
- `todo-done/refactors/hermeneutic-suspension-auto-web-todo.md`
- `todo-done/notes/hermeneutic-dashboard-mode-since-todo.md`

### Install / operations

Lire d'abord:
- `states/operations/frida-installation-operations.md`
- `todo-todo/product/Frida-installation-config.md`
- `todo-done/migrations/fridadev-to-frida-system-migration-todo.md`

Rappel: les secrets, `.env`, DSN complets et tokens runtime ne doivent pas etre affiches dans les docs, commits ou reponses.

### Admin / surfaces

Lire d'abord:
- `states/specs/memory-admin-surface-contract.md`
- `todo-done/refactors/admin-todo.md`
- `todo-done/refactors/log-module-todo.md`
- `todo-done/refactors/log-followups-todo.md`

Surfaces a distinguer:
- `/admin`: runtime settings et configuration operateur
- `/log`: timeline brute, filtres, export et suppressions scopees
- `/memory-admin`: observabilite memoire / RAG
- `/hermeneutic-admin`: detail pipeline hermeneutique et identity
- `/identity`: pilotage canonique des couches identitaires

## Carte des dossiers

- `states/specs/`: specs normatives
- `states/architecture/`: conventions, cartographies et cadrages architecturaux
- `states/audits/`: audits globaux ou transverses dates servant de source de verite
- `states/operations/`: guides operatoires et runbooks
- `states/baselines/`: baselines et photos techniques datees
- `states/project/`: etats projet de reference
- `states/policies/`: politiques et gouvernance
- `states/legacy/`: archives legacy explicites

- `todo-done/audits/`: audits finalises
- `todo-done/validations/`: rapports de validation
- `todo-done/refactors/`: roadmaps de refacto cloturees
- `todo-done/migrations/`: roadmaps de migration archivees
- `todo-done/notes/`: notes de nettoyage et cadrage documentaire
- `todo-done/product/`: roadmaps produit cloturees

- `todo-todo/memory/`: roadmaps memoire/hermeneutique ouvertes
- `todo-todo/product/`: roadmaps produit/installation ouvertes
- `todo-todo/admin/`: roadmaps admin ouvertes
- `todo-todo/audits/`: plans actifs de remediation issus d'audits
- `todo-todo/migration/`: reserve pour futurs chantiers ouverts
- `todo-todo/refactors/`: roadmaps de refactor structurel ouvertes

## Autres references utiles

- Baseline schema de base: `states/baselines/database-schema-baseline.md`
- Decision projet reranker memoire/RAG 2026-04-11: `states/project/memory-rag-reranker-decision-2026-04-11.md`
- Design du candidate generation memoire/RAG: `states/architecture/memory-rag-candidate-generation-design.md`
- Validation de cloture Phase 10E Memory Admin: `todo-done/validations/memory-admin-phase10e-validation-2026-04-12.md`
- Note de travail ouverte externalisation reglee des facultes: `todo-todo/product/fridadev-externalisation-reglee-des-facultes-todo.md`
- Note archivee Whisper V1: `todo-done/notes/integration-whisper-v1-closure.md`
- Roadmap archivee surface `/identity` canonique: `todo-done/refactors/identity-surface-canonical-layout-todo.md`
- Roadmap archivee separation doctrinale `identity` / `prompt`: `todo-done/refactors/identity-vs-prompt-separation-todo.md`
- Trace archivee follow-up audit complet 2026-04-04: `todo-done/audits/fridadev-audit-followup-2026-04-04.md`
- Note archivee lecture web URL explicite / Crawl4AI: `todo-done/notes/web-reading-truth-todo.md`
- Note archivee dialogique / identite: `todo-done/notes/dialogic-identity-closure.md`
- Note archivee token accounting OpenRouter: `todo-done/notes/token-counter-openrouter-todo.md`
- Roadmap ouverte memoire de moment contextuel: `todo-todo/memory/memory-contextual-moments-todo.md`
- Roadmap archivee `conv_store`: `todo-done/refactors/fridadev-conv-store-structural-refactor-todo.md`
- Grounding temporel chat archive: `todo-done/notes/chat-time-grounding-todo.md`

## Notes de maintenance

- La racine `app/docs` ne doit garder que ce `README.md`.
- Les anciennes roadmaps Migration_FridaDev-todo.md et memory-todo.md sont archivees dans `todo-done/migrations/`.
- Les nettoyages faibles valeur patch_done.md et smart-todo.md ont ete supprimes.
- Toute doc qui change un comportement runtime, une attente operateur, une limite ou une regle source-of-truth doit etre mise a jour dans le meme cycle que le patch concerne.
