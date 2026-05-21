# Benchmark recherche web FridaDev

Ce banc compare le pipeline web local FridaDev avec les server tools OpenRouter, sans modifier le runtime `/api/chat`.

Il sert à préparer le chantier produit "Recherche internet" de la roadmap finale. Il ne décide pas encore si FridaDev doit rester local, basculer vers OpenRouter, ou devenir hybride.

## Bras comparés

Par défaut:

- `local`: pipeline FridaDev actuel, c'est-à-dire SearXNG + Crawl4AI + reformulation web existante quand nécessaire;
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

Ces artefacts peuvent rester dans `/tmp`. Ne committe pas de résultats live volumineux ou privés.

## Run live borné

Pour comparer local + Exa + Parallel:

```bash
OPENROUTER_API_KEY=... python3 benchmark/run_benchmark.py \
  --suite web_search \
  --campaign-id 2026-05-21-web-search-comparison \
  --output-dir /tmp/fridadev-web-search-live
```

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

Le bras local peut tout de même utiliser la reformulation web FridaDev selon les settings runtime existants. C'est volontaire: on mesure le pipeline local réel, pas un pipeline réduit artificiellement.

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
- pour le local: `read_state`, `collection_path`, `used_content_kinds`, `injected_chars`, `context_chars`.

Les résultats ne doivent jamais contenir:

- clé OpenRouter;
- header `Authorization`;
- `.env`;
- gros HTML/Markdown complet;
- contenu privé;
- secret ou token.

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

La décision produit reste humaine. Les sorties doivent aider à choisir plus tard entre:

- local seul;
- OpenRouter Exa en fallback;
- OpenRouter Parallel en fallback;
- hybride borné;
- aucun changement.

## Limites connues

- `openrouter:web_search` laisse le modèle décider s'il cherche; le rapport expose donc le nombre réel de requêtes web.
- Exa et Parallel ajoutent un coût serveur en plus des tokens du modèle.
- Le bras local dépend de l'état runtime SearXNG/Crawl4AI et des settings services de l'instance.
- Le benchmark ne teste pas encore `openrouter:web_fetch` par défaut, pour ne pas mélanger recherche et lecture d'URL dans le premier banc.
