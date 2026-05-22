# Benchmark recherche web FridaDev

Ce banc compare le pipeline web FridaDev et les server tools OpenRouter. Il sert aussi a verifier la bascule produit: FridaDev reste local-first pour lire/qualifier/auditer, mais la recherche ouverte peut utiliser OpenRouter/Exa comme provider de decouverte URL.

Doctrine produit actuelle: `explicit_url` reste local direct, Crawl4AI lit les URLs, OpenRouter/Exa decouvre les URLs en recherche ouverte par defaut applicatif (`WEB_SEARCH_DISCOVERY_PROVIDER=openrouter_exa`), et Parallel reste benchmark externe. Exa n'est pas un fallback automatique declenche par la confiance.

## Bras comparés

Par défaut:

- `local`: baseline locale à requête unique, c'est-à-dire SearXNG + Crawl4AI + reformulation web existante sans requêtes spécialisées;
- `local_profiled`: bras profilé qui utilise le profil runtime, les requêtes spécialisées bornées, le provider de decouverte configure, le reranking local souple avant crawl, la politique Crawl4AI profilée et les signaux de confiance avec fallback externe désactivé;
- `openrouter_exa`: `openrouter:web_search` avec `engine=exa`;
- `openrouter_parallel`: `openrouter:web_search` avec `engine=parallel`.

Le mode `openrouter_native` existe comme option opérateur, mais il n'est pas lancé par défaut pour garder le premier benchmark lisible et économique.

Les anciens chemins OpenRouter `plugins: [{ id: "web" }]` et les modèles `:online` sont explicitement hors benchmark: la documentation OpenRouter les marque comme dépréciés au profit des server tools.

## Cas de test

La matrice versionnée vit dans:

```bash
benchmark/suites/web_search/fixtures/cases.json
```

Elle couvre cinq familles:

- actualité récente;
- documentation technique officielle;
- URL explicite à lire;
- recherche philosophique / académique / conceptuelle;
- recherche institutionnelle française.

Chaque cas contient `id`, `title`, `user_query`, `category`, `expected_source_kinds`, domaines attendus éventuels et notes de lecture humaine.

## Dry-run

Le dry-run valide la configuration, les artefacts et la forme des résultats sans appeler OpenRouter, SearXNG ni Crawl4AI:

```bash
python3 benchmark/run_benchmark.py \
  --suite web_search \
  --dry-run \
  --campaign-id dry-run-web-search \
  --output-dir /tmp/fridadev-web-search-dry-run
```

Artefacts produits:

- `dry-run-web-search.json`;
- `dry-run-web-search.jsonl`;
- `dry-run-web-search.md`.
- `local.md`;
- `local-profiled.md`;
- `openrouter-exa.md`;
- `openrouter-parallel.md`.

Ces artefacts peuvent rester dans `/tmp`. Ne committe pas de résultats live volumineux ou privés.

## Run live borné

Pour comparer local + Exa + Parallel:

```bash
OPENROUTER_API_KEY=... python3 benchmark/run_benchmark.py \
  --suite web_search \
  --campaign-id 2026-05-21-web-search-comparison \
  --output-dir /tmp/fridadev-web-search-live
```

Le dossier live contient aussi un Markdown par système. Ce sont les fichiers à
ouvrir côte à côte pour la lecture humaine:

- `local.md`;
- `local-profiled.md`;
- `openrouter-exa.md`;
- `openrouter-parallel.md`.

Paramètres OpenRouter par défaut:

```json
{
  "type": "openrouter:web_search",
  "parameters": {
    "engine": "exa",
    "max_results": 5,
    "max_total_results": 5,
    "search_context_size": "low"
  }
}
```

Le même profil est utilisé pour `engine=parallel`.

Pour augmenter plus tard le contexte sans changer le code:

```bash
OPENROUTER_API_KEY=... python3 benchmark/run_benchmark.py \
  --suite web_search \
  --campaign-id web-search-medium \
  --web-search-context-size medium \
  --output-dir /tmp/fridadev-web-search-medium
```

Pour tester seulement le pipeline local, sans clé benchmark OpenRouter:

```bash
python3 benchmark/run_benchmark.py \
  --suite web_search \
  --web-search-arms local \
  --campaign-id web-search-local-only \
  --output-dir /tmp/fridadev-web-search-local
```

Le bras local peut tout de même utiliser la reformulation web FridaDev selon les settings runtime existants. Depuis les lots de durcissement local, il désactive les requêtes spécialisées, les paniers moteurs SearXNG gouvernés, le reranking et la politique Crawl4AI profilée pour conserver une baseline historique face à `local_profiled`, mais expose aussi les signaux de confiance observatoires du runtime.

Pour préparer la comparaison du futur pipeline profilé sans appeler OpenRouter:

```bash
python3 benchmark/run_benchmark.py \
  --suite web_search \
  --dry-run \
  --web-search-arms local local_profiled \
  --campaign-id web-search-local-profiled-dry-run \
  --output-dir /tmp/fridadev-web-search-local-profiled-dry-run
```

Depuis la Phase 4 du rebuild local, `local_profiled` n'est plus un simple stub qualité: il active le plan de requêtes spécialisées bornées, les paniers moteurs SearXNG gouvernés par régime, le reranking local souple, la politique Crawl4AI profilée et l'observabilité de confiance dans les runs live locaux. En dry-run, il ne lance toujours aucun appel SearXNG/Crawl4AI et expose seulement la forme du bras.

## Sorties et métriques

Pour chaque cas et chaque bras, le JSON/Markdown garde:

- mode / engine;
- succès ou échec;
- latence;
- coût estimé si disponible;
- `usage.server_tool_use.web_search_requests` quand OpenRouter le renvoie;
- tokens d'entrée/sortie quand disponibles;
- URLs et domaines cités;
- aperçu borné des extraits, jamais le dump complet;
- pour le local: `read_state`, `collection_path`, `search_profile`, `query_plan_kind`, `query_count`, `secondary_query_count`, `deduped_result_count`, `searxng_profile_params_kind`, `searxng_profile_params_policy`, `searxng_categories`, `searxng_engines`, `searxng_time_range`, `searxng_language`, `searxng_safesearch`, `web_discovery_provider`, `web_discovery_provider_requested`, `web_discovery_provider_effective`, `web_discovery_external_used`, `web_discovery_external_provider`, `web_discovery_external_error_kind`, `web_discovery_reason_codes`, `rerank_applied`, `rerank_policy`, `rerank_top_domains_before`, `rerank_top_domains_after`, `rerank_reason_counts`, `crawl4ai_policy_kinds`, `crawl4ai_filter_counts`, `crawl4ai_cache_modes`, `crawl4ai_fallback_used_count`, `web_confidence_policy_kind`, `web_confidence_level`, `web_confidence_score`, `web_confidence_reason_codes`, `openrouter_fallback_state`, `openrouter_fallback_used`, `openrouter_fallback_reason_codes`, `used_content_kinds`, `injected_chars`, `context_chars`.

`web_confidence_*` est un signal heuristique visible pour audit humain. Il ne modifie pas l'ordre des sources, ne supprime rien et ne déclenche jamais OpenRouter/Exa/Parallel. Si Exa est utilise, il doit apparaitre via `web_discovery_*`, pas via `openrouter_fallback_*`. `openrouter_fallback_used` doit rester `False`.

Les résultats ne doivent jamais contenir:

- clé OpenRouter;
- header `Authorization`;
- `.env`;
- gros HTML/Markdown complet;
- contenu privé;
- secret ou token.

Les aperçus bornés des sources et réponses sont expurges avant écriture des artefacts pour éviter qu'une documentation publique contenant un exemple de header ou de clé fictive déclenche les greps sécurité du banc.

## Lecture humaine

Le rapport Markdown contient une grille simple:

- pertinence des sources;
- fraîcheur;
- autorité / source officielle;
- qualité des extraits;
- capacité à traiter une URL explicite;
- coût;
- latence;
- intégrabilité dans FridaDev;
- observabilité et vérité de lecture.

La decision produit post Phase 8 est fixee: local-first + OpenRouter/Exa comme provider de decouverte URL configure pour la recherche ouverte.

- SearXNG reste le provider `local`, baseline historique et fallback operateur explicite;
- Crawl4AI reste le point de lecture/crawl local;
- Exa peut devenir la decouverte prioritaire quand configure;
- Parallel reste comparateur externe;
- le chantier critique SearXNG reste utile, mais ne bloque plus la bascule de decouverte ouverte.

## Lecture Lot 8 du 2026-05-22

Note persistante: `app/docs/states/audits/fridadev-web-search-lot8-final-benchmark-2026-05-22.md`.

Artefacts live:

- `/tmp/fridadev-web-search-lot8-live/local.md`;
- `/tmp/fridadev-web-search-lot8-live/local-profiled.md`;
- `/tmp/fridadev-web-search-lot8-live/openrouter-exa.md`;
- `/tmp/fridadev-web-search-lot8-live/openrouter-parallel.md`.

Decision Lot 8 supersedee le 2026-05-22: le benchmark Phase 8 a montre que SearXNG ne suffit pas pour la decouverte ouverte. La decision active est documentee dans `app/docs/states/policies/fridadev-web-search-openrouter-exa-decision-2026-05-22.md`.

## Diagnostic same-query

Pour isoler l'effet requete/index/ranking, le diagnostic same-query envoie une requete fixe aux trois systemes de recherche:

- SearXNG local, avec la chaine dans le parametre strict `q`;
- OpenRouter Exa, via une consigne demandant d'utiliser exactement cette chaine;
- OpenRouter Parallel, avec la meme consigne.

Limite importante: OpenRouter ne renvoie pas la requete effectivement deleguee a Exa/Parallel. La parite est donc stricte pour SearXNG, mais seulement contrainte par prompt pour OpenRouter.

Commande type dans l'environnement applicatif:

```bash
python3 -m benchmark.suites.web_search.same_query_diagnostic \
  --output-dir /tmp/fridadev-web-search-same-query-diagnostic \
  --searxng-url "$SEARXNG_URL"
```

Artefacts:

- `/tmp/fridadev-web-search-same-query-diagnostic/searxng.md`;
- `/tmp/fridadev-web-search-same-query-diagnostic/openrouter-exa.md`;
- `/tmp/fridadev-web-search-same-query-diagnostic/openrouter-parallel.md`;
- `/tmp/fridadev-web-search-same-query-diagnostic/comparison.md`.

## Limites connues

- `openrouter:web_search` laisse le modèle décider s'il cherche; le rapport expose donc le nombre réel de requêtes web.
- Exa et Parallel ajoutent un coût serveur en plus des tokens du modèle.
- Le bras local dépend de l'état runtime SearXNG/Crawl4AI et des settings services de l'instance.
- Le benchmark ne teste pas encore `openrouter:web_fetch` par défaut, pour ne pas mélanger recherche et lecture d'URL dans le premier banc.
- `local_profiled` porte les requêtes spécialisées bornées, les paniers moteurs SearXNG gouvernés par régime, le reranking local souple, la politique BM25 Crawl4AI bornée et une confiance finale observatoire; aucun fallback externe n'est appelé par le benchmark local.
