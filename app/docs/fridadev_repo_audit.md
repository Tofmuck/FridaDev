# FridaDev Repo Audit

## 1. Résumé exécutif
- [Constaté] Le repo est fonctionnel mais présente plusieurs modules monolithiques critiques (`app/server.py`, `app/memory/memory_store.py`, `app/admin/runtime_settings.py`, `app/web/admin.js`) avec un couplage transversal élevé.
- [Constaté] Des contradictions de contrat existent entre couches (frontend/backend, démarrage runtime, source de modèle arbitre), et des reliquats de migration DB-only restent présents dans le code.
- [Inféré] L’architecture actuelle reflète des strates successives (phases) bien intégrées fonctionnellement, mais la dette de structure commence à freiner la lisibilité, la testabilité et la vitesse de changement.
- [Recommandé] Prioriser un découpage modulaire progressif: extraction de services applicatifs depuis `server.py`, séparation des responsabilités de `runtime_settings`, réduction de la duplication frontend admin, puis purge contrôlée des reliquats legacy.

## 2. Exclusions
- [Constaté] Les contenus suivants sont exclus de l’analyse de fond (non utilisés comme source de vérité):
  - `app/docs/admin-todo.md`
  - `app/docs/todo-done/**`
  - `app/docs/todo-todo/**`
  - plus généralement: tout artefact `todo`, `TODO`, `to-do`, checklist, note d’avancement équivalente.
- [Constaté] Ces éléments ont été traités uniquement comme catégories/chemins exclus, sans commentaire de contenu.
- [Inféré] Une partie des décisions de chantier historique existe dans ces zones, mais elles ne fondent pas le diagnostic ci-dessous.
- [Recommandé] Maintenir cette exclusion pour toute phase d’audit structurel future, et ne réintroduire ces sources qu’en phase de pilotage produit explicitement dédiée.

## 3. Cartographie actuelle du repo
- [Constaté] Racine:
  - `docker-compose.yml`, `stack.sh`, `README.md`, `AGENTS.md`
  - `app/` concentre l’essentiel du code et de la documentation.
- [Constaté] Backend Python:
  - Entrées: `app/server.py` (1201 lignes), `app/minimal_validation.py` (803 lignes)
  - Modules principaux: `app/core/`, `app/memory/`, `app/identity/`, `app/admin/`, `app/tools/`
  - Config: `app/config.py`, `app/config.example.py`, `app/.env.example`
- [Constaté] Frontend statique:
  - `app/web/index.html`, `app/web/app.js` (768 lignes), `app/web/admin.html`, `app/web/admin.js` (3654 lignes), `app/web/styles.css`, `app/web/admin.css`
- [Constaté] Tests:
  - `app/tests/` avec 26 fichiers, majoritairement nommés par phase (`phase4`, `phase8`, `phase13`, etc.).
- [Constaté] Documentation suivie:
  - `app/docs/` avec docs admin et 2 états versionnés dans `app/docs/states/`.
- [Inféré] Le repo est organisé par surfaces techniques (backend/web/tests/docs), mais sans séparation nette domain/application/infrastructure/interfaces.
- [Recommandé] Cibler une cartographie modulaire explicite (cf. section 9) pour réduire le couplage latéral.

## 4. Incohérences structurelles
- [Constaté] Modules critiques très volumineux:
  - `app/server.py`, `app/memory/memory_store.py`, `app/admin/runtime_settings.py`, `app/web/admin.js`.
- [Constaté] Le “core” n’est pas indépendant: `app/core/conv_store.py` et `app/core/llm_client.py` dépendent de `app/admin/runtime_settings.py` et `app/admin/admin_logs.py`.
- [Constaté] `app/admin/runtime_settings.py` mélange schema, seed, accès DB, cryptographie, validation runtime, métadonnées UI readonly.
- [Constaté] `app/.gitignore` ignore `app/docs/states/*` sauf deux fichiers whitelists, alors que `app/docs/README.md` présente `states/` comme zone de référence pérenne.
- [Inféré] Le découpage actuel a privilégié l’intégration rapide des phases plutôt qu’une frontière modulaire stable.
- [Recommandé] Réduire les modules “god objects” et aligner conventions docs/versioning avec l’intention documentaire déclarée.

## 5. Contradictions dans le code
- [Constaté] Contrat de démarrage incohérent:
  - `app/Dockerfile` lance `python server.py` directement.
  - `app/run.sh` charge `.env`, lit `FRIDA_WEB_HOST`/`FRIDA_WEB_PORT`, mais n’est pas utilisé par Docker.
  - `app/server.py` force `host="0.0.0.0"` et ignore `FRIDA_WEB_HOST`.
  - `docker-compose.yml` injecte pourtant `FRIDA_WEB_HOST`.
- [Constaté] Contrat frontend/backend divergent sur le chat:
  - `app/web/app.js` envoie `history` dans `POST /api/chat`.
  - `app/server.py` ne lit jamais `history`.
- [Constaté] Modèle arbitre potentiellement incohérent en persistance:
  - décision calculée via runtime DB (`app/memory/arbiter.py`),
  - mais `record_arbiter_decisions` stocke `model=config.ARBITER_MODEL` (`app/memory/memory_store.py`).
- [Constaté] Migration DB-only partiellement nettoyée:
  - `app/server.py` loggue `conv_json_bootstrap disabled for db_only_migration`,
  - tout en gardant `conv_store.ensure_conv_dir()` et des reliquats JSON dans `app/core/conv_store.py`.
- [Inféré] Ces contradictions viennent de transitions incomplètement consolidées entre anciennes et nouvelles strates.
- [Recommandé] Fermer explicitement chaque contrat inter-couche (runtime start, payload API, provenance des settings) avant toute refacto large.

## 6. Code mort / déchets / reliquats

| Chemin | Problème | Niveau de confiance | Justification courte |
| --- | --- | --- | --- |
| `app/memory/summarizer.py` | `needs_summarization()` non appelée | `certain` | Recherche globale: aucune référence hors définition |
| `app/web/app.js` | `const panel = $("#panel")` non utilisé | `certain` | Variable déclarée sans usage |
| `app/web/app.js` | `MAX_CONTEXT_MESSAGES` non utilisé | `certain` | Constante déclarée sans usage |
| `app/web/app.js` + `app/server.py` | Payload `history` envoyé mais ignoré | `certain` | Référence frontend présente, backend sans lecture |
| `app/tools/web_search.py` | `build_context(...)-> (..., False)` flag final figé | `certain` | 4e valeur toujours `False`, aucun chemin `True` |
| `app/core/conv_store.py` | Fonctions de sync JSON (`sync_catalog_from_json_files`, `sync_messages_from_json_files`, `get_storage_counts`) hors runtime principal | `probable` | Non appelées dans le code applicatif hors module/tests/docs |
| `app/core/conv_store.py` | `_load_json_conversation_file` reliquat de la strate JSON | `probable` | Utilisée uniquement par le sous-ensemble de sync JSON |
| `app/core/conv_store.py` | `delete_conversation` (purge forte) non branchée API (`soft_delete` utilisé) | `à vérifier` | Peut être prévue pour usage opératoire futur |
| `app/run.sh` | Script de lancement potentiellement non utilisé en exécution container | `à vérifier` | Docker démarre via `CMD ["python", "server.py"]` |

## 7. Problèmes de syntaxe / style / conventions
- [Constaté] Convention de nommage de logs incohérente: mix `frida.*` et `kiki.*` (ex: `app/server.py`, `app/core/conv_store.py`, `app/admin/admin_logs.py`).
- [Constaté] Convention de nommage tests orientée historique de phase (`test_*_phase4.py`, `phase8`, `phase13`) plutôt que domaine fonctionnel.
- [Constaté] Codebase mixte FR/EN dans messages, labels, variables et contenus prompts.
- [Constaté] Styles de typage hétérogènes (`List[Dict[str, Any]]` vs `list[dict]`) et organisation procédurale répétitive côté UI admin.
- [Inféré] Ces divergences nuisent à la lecture transversale plus qu’à l’exécution.
- [Recommandé] Uniformiser conventions minimales (logging namespace, nomenclature tests, style de typage) comme prérequis léger avant gros refacto.

## 8. Problèmes de responsabilité modulaire
- [Constaté] `app/server.py` cumule: routing HTTP, sécurité admin, orchestration métier chat, arbitrage mémoire, identité, métriques et endpoints admin spécialisés.
- [Constaté] `app/admin/runtime_settings.py` cumule: modèle de données, migration/seed, accès DB, secret management, validation runtime, données readonly UI.
- [Constaté] `app/web/admin.js` cumule: rendering, validation locale, mapping d’erreurs backend, orchestration API, état global multi-sections.
- [Constaté] Duplication de logique runtime DB bootstrap dans plusieurs modules (`app/core/conv_store.py`, `app/memory/memory_store.py`, `app/minimal_validation.py`).
- [Inféré] Le système fonctionne mais repose sur des dépendances latérales qui rendent les changements locaux risqués.
- [Recommandé] Introduire des frontières explicites: use-cases applicatifs, adaptateurs infra, routes HTTP minces, UI admin découpée en modules partagés.

## 9. Architecture cible recommandée
- [Recommandé] Structure cible pragmatique pour FridaDev:

```text
app/
  domain/
    conversation/
    memory/
    identity/
    runtime_settings/
  application/
    chat_service.py
    conversation_service.py
    admin_settings_service.py
    hermeneutics_service.py
  infrastructure/
    db/
      conversation_repo.py
      memory_repo.py
      runtime_settings_repo.py
    llm/
      openrouter_client.py
    services/
      web_search_client.py
      embed_client.py
    secrets/
      runtime_secrets_adapter.py
  interfaces/
    http/
      app_factory.py
      routes_chat.py
      routes_conversations.py
      routes_admin_settings.py
      routes_admin_hermeneutics.py
    web/
      admin/
        state.js
        api.js
        forms.js
        readonly.js
      chat/
        app.js
  shared/
    config.py
    logging.py
    token_counter.py
  tests/
    unit/
    integration/
    smoke/
  docs/
```

- [Inféré] Cette cible conserve la logique actuelle mais rend les dépendances directionnelles explicites.
- [Constaté] Les modules actuels peuvent être mappés incrémentalement vers cette cible sans big-bang.

## 10. Ordre de refacto recommandé
1. [Recommandé] Extraire un service applicatif `chat_service` depuis `app/server.py` sans changer les routes externes.
2. [Recommandé] Isoler une bibliothèque partagée de bootstrap runtime DB/section lookup pour supprimer la duplication (`conv_store`, `memory_store`, `minimal_validation`).
3. [Recommandé] Scinder `app/admin/runtime_settings.py` en 3 blocs: `spec/schema`, `repository`, `runtime_validation+api_view`.
4. [Recommandé] Corriger les contrats contradictoires à faible risque: `history` chat, `FRIDA_WEB_HOST`, modèle arbitre persisté.
5. [Recommandé] Isoler les endpoints admin herméneutiques dans un module route dédié, séparé des settings admin.
6. [Recommandé] Découper `app/web/admin.js` en modules communs + modules de section (sans changer l’UI).
7. [Recommandé] Purger/feature-flagger les reliquats JSON de `conv_store` après couverture de tests dédiée.
8. [Recommandé] Reclasser progressivement les tests par domaine (`admin_settings`, `chat`, `memory`, `runtime`) en gardant des wrappers phase transitoires.

## 11. Risques
- [Constaté] Risque de régression fonctionnelle élevé si refacto monolithique direct sur `server.py` ou `runtime_settings.py`.
- [Constaté] Risque de casser des scripts opératoires implicites si les reliquats “legacy” sont supprimés sans inventaire d’usage réel.
- [Inféré] Risque de divergence frontend/backend persistant si les contrats payload/settings ne sont pas traités en priorité.
- [Recommandé] Imposer des tranches courtes, chacune avec tests ciblés + smoke `app/minimal_validation.py`.

## 12. Questions ouvertes / points incertains
- [À clarifier] `app/run.sh` est-il encore utilisé en dehors du flux Docker actuel ?
- [À clarifier] Les fonctions de sync JSON dans `app/core/conv_store.py` doivent-elles rester comme outils opératoires officiels ?
- [À clarifier] Le namespace logger `kiki.*` est-il un héritage à conserver (compat logs) ou une dette de renommage ?
- [À clarifier] Le champ `history` envoyé par `app/web/app.js` est-il conservé pour rétrocompatibilité d’anciens backends ?
- [À clarifier] L’exclusion quasi totale de `app/docs/states/*` par `.gitignore` est-elle intentionnelle à long terme ?

