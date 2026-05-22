# FridaDev web search Lot 8 final benchmark - 2026-05-22

Statut: benchmark final Lot 8 produit.

Chantier source: `app/docs/todo-todo/product/fridadev-local-web-search-hardening-todo.md`.

Audit source: `app/docs/states/audits/fridadev-local-web-search-stack-audit-2026-05-21.md`.

Artefacts live a conserver dans `/tmp`:

- `/tmp/fridadev-web-search-lot8-live/local.md`
- `/tmp/fridadev-web-search-lot8-live/local-profiled.md`
- `/tmp/fridadev-web-search-lot8-live/openrouter-exa.md`
- `/tmp/fridadev-web-search-lot8-live/openrouter-parallel.md`

## Resume executif

Le benchmark final compare les quatre bras prevus:

- `local`: baseline historique SearXNG + Crawl4AI;
- `local_profiled`: Lots 2 a 7, avec profil, requetes specialisees, parametres SearXNG, reranking, politique Crawl4AI et confiance visible;
- `openrouter_exa`: OpenRouter `openrouter:web_search` avec `engine=exa`;
- `openrouter_parallel`: OpenRouter `openrouter:web_search` avec `engine=parallel`.

Decision produit actee apres lecture du benchmark: FridaDev web runtime reste local only. SearXNG reste le point de recherche local, Crawl4AI le point de lecture/crawl local, et Exa/Parallel/OpenRouter restent des outils de benchmark externe, jamais une voie produit automatique ou semi-automatique.

La conclusion importante n'est pas que le local profile est termine: il progresse nettement sur l'institutionnel francais et conserve le tres bon chemin URL explicite, mais il regresse fortement sur le cas actualite IA 2026 et la confiance locale y reste trop optimiste. Le signal de confiance doit donc rester visible, contestable et non actionnable.

## Protocole

Dry-run:

```bash
python3 benchmark/run_benchmark.py \
  --suite web_search \
  --dry-run \
  --campaign-id dry-run-web-search-lot8 \
  --output-dir /tmp/fridadev-web-search-lot8-dry-run
```

Run live OpenRouter borne:

```bash
python3 benchmark/run_benchmark.py \
  --suite web_search \
  --campaign-id 2026-05-22-web-search-lot8-final \
  --output-dir /tmp/fridadev-web-search-lot8-live
```

Parametres OpenRouter effectifs:

- `max_results=5`;
- `max_total_results=5`;
- `search_context_size=low`;
- engines: `exa` et `parallel`.

Note d'execution: l'hote OVH n'a pas les dependances Python runtime locales (`psycopg`). Les bras `local` et `local_profiled` ont donc ete rejoues dans le conteneur applicatif `platform-fridadev`, puis fusionnes dans les artefacts `/tmp/fridadev-web-search-lot8-live`. Les bras OpenRouter ont ete produits par le run live hote. Aucun secret n'a ete affiche ni versionne.

## Resultats synthetiques

| Cas | Local | Local profiled | Exa | Parallel |
| --- | --- | --- | --- | --- |
| Actualite IA Europe 2026 | Bonnes sources UE / AI Act mais bruit | Regression forte: forum, Zhihu, Outlook | Meilleur bloc officiel UE / Parlement / Conseil | Bon mais plus melange cabinets / blogs |
| Documentation OpenRouter | OpenRouter en tete, sources mixtes | OpenRouter reste present mais extrait pauvre, confiance basse | Meilleur: docs OpenRouter ciblees | Tres bon sur docs OpenRouter, compact |
| URL explicite OpenRouter web fetch | Excellent: `page_read`, direct URL | Excellent: identique au local | Bon via sources OpenRouter | Moins bon: indique ne pas obtenir directement la page cible |
| Derrida / trace | Bruite: Larousse, homonymes, Trace Colmar | Ameliore mais reste faible academiquement | Correct mais sources inegales | Incomplet, inclut Reddit / Medium |
| CNI francaise | Echec historique: conjugueurs | Correction nette: ANTS + Service Public en tete | Meilleur institutionnel, Service Public dominant | Bon mais melange officiel et SEO |

## Cout et latence

| Bras | Latence moyenne | Cout total estime 5 cas | Tokens totaux |
| --- | ---: | ---: | ---: |
| `local` | 4.7 s | 0 USD cote OpenRouter | n/a |
| `local_profiled` | 4.1 s | 0 USD cote OpenRouter | n/a |
| `openrouter_exa` | 9.7 s | 0.101670 USD | 28 408 |
| `openrouter_parallel` | 10.1 s | 0.084009 USD | 15 427 |

Lecture: Exa offre souvent la meilleure qualite de sources sur actualite et institutionnel, mais avec plus de tokens et un cout plus eleve. Parallel est moins cher et plus compact, mais son classement est plus inegal.

## Observabilite locale

Points positifs:

- `explicit_url` conserve `read_state=page_read`, `collection_path=explicit_url_direct`, `query_count=0` et `rerank_applied=false`;
- `local_profiled` expose `search_profile`, `query_count`, parametres SearXNG, top domaines avant/apres rerank, choix Crawl4AI, `used_content_kinds`, `injected_chars`, `context_chars` et confiance;
- `openrouter_fallback_used=false` partout.

Point critique:

- sur `recent_ai_policy_news`, `local_profiled` donne `web_confidence_level=high` malgre des sources manifestement hors sujet. La confiance reste donc utile comme signal d'audit, mais pas comme mecanisme de decision automatique.

## Decision recommandee

Politique recommandee: local only. Pas d'hybride web search.

Concretement:

- garder le local par defaut;
- garder l'URL explicite en local direct, qui est le meilleur chemin du benchmark;
- ne jamais appeler Exa/Parallel/OpenRouter depuis le runtime web FridaDev;
- utiliser Exa/Parallel seulement comme outils de benchmark externe pour comprendre les faiblesses locales;
- ouvrir ensuite un audit critique de SearXNG lui-meme, cote plateforme et documentation officielle;
- corriger la calibration `actualite` / confiance locale sans creer de passerelle externe.

## Ce qui n'a pas ete active

- Aucune passerelle OpenRouter runtime;
- aucun appel Exa/Parallel depuis `/api/chat`;
- aucun auto-web;
- aucune modification SearXNG ou Crawl4AI globale;
- aucun changement Memory, Identity, Summary, Biblio/RAG ou documents actifs;
- aucune decision automatique basee sur `web_confidence_*`.

## Findings restants

### P1 - `local_profiled` actualite peut regresser face au local baseline

Sur le cas IA Europe 2026, le local baseline remonte `artificialintelligenceact.eu` et `digital-strategy.ec.europa.eu`, tandis que `local_profiled` remonte forum, Zhihu et Outlook. C'est un signal fort que les requetes specialisees ou parametres `actualite` peuvent produire un mauvais axe SearXNG.

Action future: ajouter une regression fixture dediee et revoir Lot 3/Lot 4 pour `actualite` sans durcir en monopole de domaines.

### P1 - La confiance locale surestime un corpus hors sujet

Sur le meme cas, `web_confidence_level=high` alors que les sources injectees ne repondent pas. Le score detecte du materiau multi-domaines et du crawl, mais pas assez la pertinence semantique ou l'absence de domaines d'autorite attendus.

Action future: Lot post-7 de calibration confiance, toujours non actionnable.

### P2 - Philosophie / academique reste fragile

`local_profiled` ameliore le bruit homonyme, mais ne produit pas encore une vraie cartographie primaire / encyclopedique / academique. Exa et Parallel ne resolvent pas completement ce cas non plus.

Action future: renforcer les signaux academiques sans transformer OpenEdition/Cairn/SEP en police invisible.

## Complement same-query du 2026-05-22

Un diagnostic benchmark-only a ete ajoute apres le Lot 8 pour isoler la cause entre requete FridaDev, parametres locaux et index/ranking.

Artefacts:

- `/tmp/fridadev-web-search-same-query-diagnostic/searxng.md`;
- `/tmp/fridadev-web-search-same-query-diagnostic/openrouter-exa.md`;
- `/tmp/fridadev-web-search-same-query-diagnostic/openrouter-parallel.md`;
- `/tmp/fridadev-web-search-same-query-diagnostic/comparison.md`.

Lecture:

- SearXNG recoit exactement la chaine diagnostique via le parametre `q`;
- OpenRouter Exa/Parallel recoivent une consigne verrouillee, mais l'API n'expose pas la requete effectivement deleguee au moteur;
- sur `actualite IA`, `Derrida/trace` et `CNI`, SearXNG manque les domaines attendus ou remonte le bruit lexical avec la meme requete;
- sur ces memes cas, au moins un moteur OpenRouter retrouve des domaines attendus que SearXNG ne remonte pas dans le top 5;
- sur `OpenRouter web_search`, SearXNG trouve le domaine officiel, mais Exa/Parallel trouvent mieux les pages de documentation.

Conclusion diagnostique: le probleme n'est pas seulement la reformulation FridaDev ni le reranking `local_profiled`. Une part importante vient du ranking/index SearXNG sur ces requetes ouvertes, avec un residu local specifique sur la strategie `actualite` et la calibration de confiance. Cela oriente le prochain chantier vers un audit critique SearXNG, pas vers une passerelle runtime.

## Preuves

Commandes de verification executees pendant le lot:

```bash
find /tmp/fridadev-web-search-lot8-live -maxdepth 1 -type f | sort
test -f /tmp/fridadev-web-search-lot8-live/local.md
test -f /tmp/fridadev-web-search-lot8-live/local-profiled.md
test -f /tmp/fridadev-web-search-lot8-live/openrouter-exa.md
test -f /tmp/fridadev-web-search-lot8-live/openrouter-parallel.md
python3 -m py_compile benchmark/run_benchmark.py benchmark/suites/web_search/adapter.py benchmark/suites/web_search/campaign.py
python3 -m unittest app.tests.unit.benchmark.test_web_search_benchmark
```

Le grep securite demande dans la mission est vide apres redaction des apercus d'artefacts. Les rapports restent content-free au sens operateur: ils exposent URLs, domaines, compteurs, hash et apercus bornes, sans secret, header d'authentification ou dump de contenu.
