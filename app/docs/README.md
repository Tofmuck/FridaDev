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
- Catalogue des appels modeles et services d'inference 2026-05-17: `states/audits/fridadev-model-call-catalog-2026-05-17.md`
- Audit stack locale SearXNG/Crawl4AI vs benchmark web 2026-05-21: `states/audits/fridadev-local-web-search-stack-audit-2026-05-21.md`
- Benchmark final Lot 8 web local vs OpenRouter Exa/Parallel 2026-05-22: `states/audits/fridadev-web-search-lot8-final-benchmark-2026-05-22.md`
- Baseline consolidee Phase 0 recherche web locale 2026-05-22: `states/audits/fridadev-local-web-search-phase-0-baseline-2026-05-22.md`
- TODO actif de renforcement web local SearXNG/Crawl4AI: `todo-todo/product/fridadev-local-web-search-hardening-todo.md`
- TODO actif A-Z de reconstruction locale de la recherche web: `todo-todo/product/fridadev-local-web-search-rebuild-todo.md`
- Archive du benchmark / organisation progressive des callers modeles: `todo-done/refactors/fridadev-model-caller-benchmark-todo.md`
- Archive produit generation d'images OpenRouter V0: `todo-done/product/fridadev-image-generation-openrouter-todo.md`
- Archive lecture d'images comme documents actifs: `todo-done/product/fridadev-active-image-documents-todo.md`
- Boussole produit finale des cinq derniers gros chantiers FridaDev: `todo-todo/product/fridadev-final-product-roadmap-todo.md`
- Archive atelier documentaire / répertoires de travail: `todo-done/product/fridadev-workspace-folders-todo.md`
- Contrat source-of-truth atelier documentaire / répertoires de travail: `states/specs/workspace-folders-contract.md`
- Audit court du contrat courant `identity_periodic_agent` 2026-05-19: `states/audits/identity-periodic-current-contract-audit-2026-05-19.md`
- Audit global de verite temporelle 2026-05-18: `states/audits/fridadev-temporal-system-audit-2026-05-18.md`
- Remediation archivee de comprehension temporelle modele: `todo-done/audits/fridadev-temporal-truth-remediation-todo.md`
- Archive de cloture de la remediation de l'audit global: `todo-done/audits/fridadev-global-audit-remediation-todo.md`
- Synthese francaise du pipeline complet FridaDev 2026-05-19: `states/architecture/fridadev-full-pipeline-overview-2026-05-19.md`
- Archive de bascule du modele principal vers GPT-5.1: `todo-done/refactors/fridadev-main-model-gpt51-switch-todo.md`
- Plan archive de bascule du modele principal vers GPT-5.1: `todo-done/refactors/fridadev-main-model-gpt51-switch-plan.md`
- Cartographie runtime one-glance: `states/architecture/fridadev-current-runtime-pipeline.md`
- Etats projet dates du 2026-04-03: `states/project/Frida-State-french-03-04-26.md` et `states/project/Frida-State-english-03-04-26.md`

### Doctrine active

- Pouvoir de l'arbitre de reponse: `states/specs/response-arbiter-power-contract.md`
- Voix / identite / reprise apres ecart temporel: `states/specs/chat-enunciation-and-gap-contract.md`
- Plan doctrinal identity `static` / `mutable`: `states/policies/identity-new-contract-plan.md`
- Contrat de surface `Memory Admin`: `states/specs/memory-admin-surface-contract.md`
- Protocole streaming public: `states/specs/streaming-protocol.md`
- Contrat des documents actifs de conversation: `states/specs/active-conversation-documents-contract.md`
- Contrat atelier documentaire / répertoires de travail: `states/specs/workspace-folders-contract.md`
- Extension OCR archivee des documents actifs de conversation: `todo-done/product/active-conversation-documents-ocr-todo.md`
- Copie de bulle et export Markdown du chat: `states/specs/chat-copy-export-contract.md`
- Contrat du dashboard long terme: `states/specs/dashboard-long-term-observability-contract.md`
- Discipline triadique `Warum / Wofür / Wozu` du `validation_agent`: `states/specs/hermeneutic-warum-wofuer-wozu-triad-contract.md`

### Archives utiles

- Migration OVH et chemins runtime: `todo-done/migrations/fridadev-to-frida-system-migration-todo.md`
- Cloture operatoire du nouveau contrat identitaire: `todo-done/refactors/identity-new-contract-todo.md`
- Grande roadmap hermeneutique archivee: `todo-done/notes/hermeneutical-add-todo.md`
- Bascule vers un arbitre de reponse LLM dominant: `todo-done/refactors/llm-dominant-response-arbiter-todo.md`
- Fiabilisation archivee du streaming des reponses: `todo-done/product/frida-response-streaming-todo.md`
- Roadmap archivee des documents actifs de conversation: `todo-done/product/active-conversation-documents-todo.md`
- Audit-plan archive des documents actifs de conversation: `todo-done/product/active-conversation-documents-audit-plan.md`
- Extension OCR archivee des documents actifs de conversation: `todo-done/product/active-conversation-documents-ocr-todo.md`
- Roadmap archivee du dashboard long terme: `todo-done/admin/dashboard-long-term-observability-todo.md`

## Docs a lire d'abord selon le chantier

### Cleanup / refactor repo

Lire d'abord:
- `todo-done/audits/fridadev-global-audit-remediation-todo.md` pour l'archive de remediation cloturee issue de l'audit global du 2026-05-03.
- `states/audits/fridadev-global-audit-2026-05-03.md` pour la source de verite des findings.
- `todo-done/refactors/fridadev-repo-cleanup-prioritized-todo.md`
- `todo-done/audits/fridadev_repo_audit.md`
- `states/architecture/fridadev-current-runtime-pipeline.md`

But: relire le cleanup priorise livre et les decisions de sortie sans reouvrir une roadmap terminee.

### Runtime courant / chat

Lire d'abord:
- `todo-done/refactors/fridadev-main-model-gpt51-switch-todo.md` pour l'archive de bascule runtime vers `openai/gpt-5.1`.
- `todo-done/refactors/fridadev-main-model-gpt51-switch-plan.md` pour relire le plan de bascule du modele principal vers `openai/gpt-5.1`, cout, compatibilite images actives, smoke live et rollback.
- `states/architecture/fridadev-full-pipeline-overview-2026-05-19.md` pour une synthese francaise lisible du pipeline complet, du navigateur aux derives apres reponse.
- `states/operations/main-prompt-payload-audit.md` pour cartographier le prompt effectif du modele principal et exporter un payload synthetique expurge.
- `states/architecture/fridadev-current-runtime-pipeline.md`
- `states/audits/fridadev-model-call-catalog-2026-05-17.md` pour cartographier les modeles OpenRouter, embeddings, Whisper, OCR, tokens et contrats de sortie avant tout raffinage provider.
- `todo-done/refactors/fridadev-model-caller-benchmark-todo.md` pour relire le chantier clos de benchmark, decision et decouplage caller par caller.
- `../../benchmark/README.md` pour relancer l'atelier durable de benchmark des callers modeles.
- `states/audits/fridadev-temporal-system-audit-2026-05-18.md` avant tout changement touchant `NOW`, `hier/aujourd'hui`, les timestamps, les resumes, la memoire, le web, le dashboard ou les exports.
- `states/specs/streaming-protocol.md`
- `states/specs/chat-copy-export-contract.md`
- `states/specs/chat-enunciation-and-gap-contract.md`
- `states/specs/response-arbiter-power-contract.md`
- `todo-done/audits/model-prompt-payload-interpretation-audit-2026-05-16.md` pour l'audit archive du contrat semantique prompt/payload et les limites volontaires conservees.

Archives utiles:
- `todo-done/product/frida-response-streaming-todo.md`
- `todo-done/notes/chat-enunciation-gap-validation-todo.md`

### Recherche internet

Lire d'abord:
- `todo-todo/product/fridadev-local-web-search-rebuild-todo.md` pour piloter la reconstruction A-Z locale, source-first, gouvernee et sans hybride runtime.
- `todo-todo/product/fridadev-local-web-search-hardening-todo.md` pour le contrat V0, les lots d'implementation et le bras benchmark `local_profiled`.
- `states/audits/fridadev-local-web-search-phase-0-baseline-2026-05-22.md` pour la consolidation Phase 0: cas deja couverts, complement local-only borne et passage vers l'inventaire moteur SearXNG.
- `states/specs/fridadev-web-search-regimes-source-first-contract.md` pour le contrat Phase 2/3: regimes canoniques, source-first, anti-overfit et observabilite content-free.
- `states/audits/fridadev-local-web-search-stack-audit-2026-05-21.md` pour comparer SearXNG, Crawl4AI, configuration OVH, pipeline FridaDev et benchmark local/Exa/Parallel avant tout lot runtime.
- `states/audits/fridadev-web-search-lot8-final-benchmark-2026-05-22.md` pour la decision Lot 8 recadree: runtime web `local only`, Exa/Parallel uniquement comme benchmarks externes, aucune activation runtime OpenRouter.
- `todo-done/notes/web-reading-truth-todo.md` pour le contrat archive de lecture URL explicite, `read_state`, `fit` puis `raw` et observabilite content-free.
- `todo-done/refactors/hermeneutic-suspension-auto-web-todo.md` pour la decision archivee de suspension de l'auto-web lexical.
- `benchmark/web-search/README.md` pour relancer le benchmark comparatif local / OpenRouter Exa / OpenRouter Parallel.

But: renforcer la recherche locale sans rouvrir l'auto-web, sans remplacer la stack par OpenRouter par defaut, et sans contaminer Memory/Identity/Summary.

### Documents actifs de conversation

Lire d'abord:
- `states/specs/workspace-folders-contract.md` pour le contrat source-of-truth de l'atelier documentaire / répertoires de travail, fichiers persistants, sélection conversation-scoped et non-contamination.
- `todo-done/product/fridadev-workspace-folders-todo.md` pour l'archive du chantier atelier documentaire / répertoires de travail, qui organise fichiers persistants et conversations sans les injecter automatiquement.
- `states/specs/active-conversation-documents-contract.md`
- `todo-done/product/fridadev-active-image-documents-todo.md` pour l'archive de lecture d'images comme pieces actives de conversation.
- `todo-done/product/active-conversation-documents-audit-plan.md`
- `todo-done/product/active-conversation-documents-todo.md`
- `todo-done/product/active-conversation-documents-ocr-todo.md` pour l'archive de l'extension OCR bornee des PDF scannes.

But: relire le chantier livre permettant a l'utilisateur de fournir des documents textuels, ou certains PDF scannes apres OCR V1 bornee, a une conversation active, sans RAG documentaire, sans contamination Memory/RAG/Identity/Summary, et sans promesse d'ouverture du texte complet du document dans le dashboard.

Frontiere importante: ce chantier concerne les `active_document` temporaires, pas la future Biblio persistante.

Extension livree: l'OCR bornee des PDF scannes est archivee dans `todo-done/product/active-conversation-documents-ocr-todo.md`; elle prolonge `active_document` via Stirling seulement apres `document_ocr_required`, avec limites `25 pages`, `25 Mo`, `180` secondes, `fra+eng+deu`, sans ouvrir Biblio, n8n ni doc-pipeline nominal.

### Biblio native / Frida Catalogue

Lire d'abord:
- `todo-todo/product/frida-biblio-native-catalogue-audit-plan.md`
- `todo-todo/product/frida-biblio-native-catalogue-todo.md`

But: cadrer le chantier separe permettant a Frida de consulter une bibliotheque persistante native, identifier un `library_document` / `catalogue_document`, resoudre un locator et extraire un `passage documentaire` sans confondre cette capacite avec les documents actifs de conversation.

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
- `states/architecture/memory-rag-current-pipeline-cartography.md`
- `states/specs/memory-admin-surface-contract.md`
- `states/specs/memory-rag-pre-arbiter-basket-contract.md`
- `states/specs/memory-rag-summaries-lane-contract.md`

Noeud hermeneutique runtime:
- `states/specs/log-module-contract.md`
- `states/specs/response-arbiter-power-contract.md`
- `states/specs/hermeneutic-node-validation-agent-contract.md`
- `states/specs/hermeneutic-node-stimmung-input-contract.md`
- `states/specs/hermeneutic-node-primary-verdict-contract.md`
- `states/specs/hermeneutic-node-state-persistence-contract.md`

Baselines et evaluations:
- `states/baselines/memory-rag-relevance-baseline-2026-04-10.md`
- `states/baselines/memory-rag-6A-evaluation-2026-04-10.md`
- `states/baselines/memory-rag-7B-evaluation-2026-04-10.md`
- `states/baselines/memory-rag-8C-evaluation-2026-04-10.md`
- `states/specs/memory-rag-evaluation-sheet.md`

Archives utiles:
- `todo-done/validations/hermeneutical-post-stabilization-todo.md`
- `todo-done/validations/hermeneutical-post-stabilization-validation-2026-05-04.md`
- `todo-done/refactors/memory-rag-relevance-todo.md`
- `todo-done/refactors/hermeneutic-convergence-node-todo.md`
- `todo-done/refactors/hermeneutic-suspension-auto-web-todo.md`
- `todo-done/notes/hermeneutic-dashboard-mode-since-todo.md`
- `todo-done/memory/hermeneutic-warum-wofuer-wozu-prompt-first-todo.md`

Doctrine livree:
- `states/specs/hermeneutic-warum-wofuer-wozu-triad-contract.md`: discipline de lecture hermeneutique par la triade `Warum / Wofür / Wozu`, livree en V1 dans le `validation_agent` sans nouvel agent, nouveau JSON ni projection directe vers `[JUGEMENT HERMENEUTIQUE]`.

### Install / operations

Lire d'abord:
- `states/operations/frida-installation-operations.md`
- `todo-todo/product/Frida-installation-config.md`
- `todo-done/migrations/fridadev-to-frida-system-migration-todo.md`

Rappel: les secrets, `.env`, DSN complets et tokens runtime ne doivent pas etre affiches dans les docs, commits ou reponses.

### Admin / surfaces

Lire d'abord:
- `states/specs/dashboard-long-term-observability-contract.md`
- `states/specs/memory-admin-surface-contract.md`
- `todo-done/refactors/admin-todo.md`
- `todo-done/refactors/log-module-todo.md`
- `todo-done/refactors/log-followups-todo.md`

Surfaces a distinguer:
- `/admin`: runtime settings et configuration operateur
- `/dashboard`: pouls global, courbes longue periode, conversations et inspection traduite
- `/log`: timeline brute, filtres, export et suppressions scopees pour debug technique
- `/memory-admin`: observabilite domaine memoire / RAG
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
- Diagnostic archive `transcription indisponible` / Whisper API: `todo-done/notes/whisper-transcription-indisponible-diagnostic-2026-05-05.md`
- Roadmap ouverte memoire de moment contextuel: `todo-todo/memory/memory-contextual-moments-todo.md`
- Roadmap archivee `conv_store`: `todo-done/refactors/fridadev-conv-store-structural-refactor-todo.md`
- Grounding temporel chat archive: `todo-done/notes/chat-time-grounding-todo.md`

## Notes de maintenance

- La racine `app/docs` ne doit garder que ce `README.md`.
- Les anciennes roadmaps Migration_FridaDev-todo.md et memory-todo.md sont archivees dans `todo-done/migrations/`.
- Les nettoyages faibles valeur patch_done.md et smart-todo.md ont ete supprimes.
- Toute doc qui change un comportement runtime, une attente operateur, une limite ou une regle source-of-truth doit etre mise a jour dans le meme cycle que le patch concerne.
