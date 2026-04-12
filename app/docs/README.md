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
- `todo-todo/admin/`: roadmaps admin ouvertes
- `todo-todo/migration/`: reserve pour futurs chantiers ouverts
- `todo-todo/refactors/`: roadmaps de refactor structurel ouvertes (cas ponctuels)

Notes:
- la racine `app/docs` est volontairement minimale et ne garde que ce `README.md`
- audit general canonique: `todo-done/audits/fridadev_repo_audit.md`
- etat projet FR 03/04/2026: `states/project/Frida-State-french-03-04-26.md`
- etat projet EN 03/04/2026: `states/project/Frida-State-english-03-04-26.md`
- decision projet reranker memoire/RAG 2026-04-11: `states/project/memory-rag-reranker-decision-2026-04-11.md`
- contrat de surface `Memory Admin`: `states/specs/memory-admin-surface-contract.md`
- doctrine produit voix / identite / gap du chat: `states/specs/chat-enunciation-and-gap-contract.md`
- baseline schema de base: `states/baselines/database-schema-baseline.md`
- baseline Phase 0 pertinence memoire/RAG 2026-04-10: `states/baselines/memory-rag-relevance-baseline-2026-04-10.md`
- baseline d'evaluation Lot 6A memoire/RAG 2026-04-10: `states/baselines/memory-rag-6A-evaluation-2026-04-10.md`
- baseline d'evaluation Lot 7B memoire/RAG 2026-04-10: `states/baselines/memory-rag-7B-evaluation-2026-04-10.md`
- baseline d'evaluation Lot 8C memoire/RAG 2026-04-10: `states/baselines/memory-rag-8C-evaluation-2026-04-10.md`
- cartographie courante du pipeline memoire/RAG: `states/architecture/memory-rag-current-pipeline-cartography.md`
- design du candidate generation memoire/RAG: `states/architecture/memory-rag-candidate-generation-design.md`
- contrat cible du panier pre-arbitre memoire/RAG: `states/specs/memory-rag-pre-arbiter-basket-contract.md`
- contrat minimal de la voie `summaries` memoire/RAG: `states/specs/memory-rag-summaries-lane-contract.md`
- feuille d'evaluation normative memoire/RAG: `states/specs/memory-rag-evaluation-sheet.md`
- validation de cloture Phase 10E Memory Admin: `todo-done/validations/memory-admin-phase10e-validation-2026-04-12.md`
- guide operatoire installation/exploitation initiale: `states/operations/frida-installation-operations.md`
- roadmap ouverte migration/config: `todo-todo/product/Frida-installation-config.md`
- note archivee de cloture prompt-first voix / identite / gap du chat: `todo-done/notes/chat-enunciation-gap-validation-todo.md`
- note de travail ouverte externalisation reglee des facultes: `todo-todo/product/fridadev-externalisation-reglee-des-facultes-todo.md`
- trace archivee migration `tofnas` -> `frida-system.fr`: `todo-done/migrations/fridadev-to-frida-system-migration-todo.md`
- roadmap archivee surface de controle / gouvernance identity: `todo-done/refactors/identity-control-surface-todo.md`
- mini-lot admin archive `mode depuis / observation du mode`: `todo-done/notes/hermeneutic-dashboard-mode-since-todo.md`
- roadmap archivee surface `/identity` canonique: `todo-done/refactors/identity-surface-canonical-layout-todo.md`
- roadmap archivee separation doctrinale `identity` / `prompt`: `todo-done/refactors/identity-vs-prompt-separation-todo.md`
- trace archivee follow-up audit complet 2026-04-04: `todo-done/audits/fridadev-audit-followup-2026-04-04.md`
- note archivee de cloture lecture web URL explicite / Crawl4AI: `todo-done/notes/web-reading-truth-todo.md`
- note archivee de cloture mini-lot dialogique / identite: `todo-done/notes/dialogic-identity-closure.md`
- note archivee token accounting OpenRouter: `todo-done/notes/token-counter-openrouter-todo.md`
- roadmap ouverte memoire/hermeneutique: `todo-todo/memory/hermeneutical-add-todo.md`
- roadmap archivee pertinence memoire/RAG: `todo-done/refactors/memory-rag-relevance-todo.md`
- trace archivee suspension excessive / auto-web backend: `todo-done/refactors/hermeneutic-suspension-auto-web-todo.md`
- roadmap Lot 9 archivee noeud de convergence hermeneutique: `todo-done/refactors/hermeneutic-convergence-node-todo.md`
- roadmap archivee refactor structurel `conv_store`: `todo-done/refactors/fridadev-conv-store-structural-refactor-todo.md`
- TODO produit grounding temporel chat archive: `todo-done/notes/chat-time-grounding-todo.md`
- TODO principal logs applicatifs archive: `todo-done/refactors/log-module-todo.md`
- TODO follow-up logs archive: `todo-done/refactors/log-followups-todo.md`
- serie historique des etats projet precedents: `states/project/Frida-State-*-23-03-26.md` et `states/project/Frida-State-*-28-03-26.md`
- les anciennes roadmaps `Migration_FridaDev-todo.md` et `memory-todo.md` sont archivees dans `todo-done/migrations/`
- nettoyage faible valeur deja applique: `todo-done/patch_done.md` et `todo-todo/smart-todo.md` supprimes
