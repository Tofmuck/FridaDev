# FridaDev local web search hardening - TODO

Statut: actif.

Classement: `app/docs/todo-todo/product/`.

Reference d'audit: `app/docs/states/audits/fridadev-local-web-search-stack-audit-2026-05-21.md`.

## Intention

Renforcer la recherche web locale FridaDev avant toute integration OpenRouter runtime.

Le chemin par defaut reste SearXNG pour chercher, Crawl4AI pour lire, et FridaDev pour profiler, filtrer, scorer, observer et injecter prudemment.

OpenRouter Exa/Parallel restent des soupapes futures a evaluer apres renforcement local. Ce TODO ne les branche pas dans `/api/chat`.

## Avancement

- [x] Lot 0 - Spec / contrat local web renforce
- [x] Lot 1 - Fixtures et benchmark `local_profiled`
- [x] Lot 2 - Profil de recherche
- [ ] Lot 3 - Requetes specialisees bornees
- [ ] Lot 4 - Parametres SearXNG par profil
- [ ] Lot 5 - Reranking avant crawl
- [ ] Lot 6 - Crawl4AI oriente profil
- [ ] Lot 7 - Observabilite + confiance + fallback futur
- [ ] Lot 8 - Benchmark final et decision Exa/Parallel

Lecture rapide:

- Lots 0 et 1 sont livres comme socle docs/spec/benchmark.
- Lot 2 est livre comme signal runtime passif: `search_profile` est classe, propage et observe, sans effet sur la recherche.
- Lots 3 a 8 restent a implementer.
- Aucun plan multi-requetes, parametre SearXNG par profil, reranking runtime, BM25 runtime ou fallback OpenRouter runtime n'est encore livre.

## Question prealable: existe-t-il un meilleur plan ?

Oui: le meilleur plan est de ne pas commencer par modifier le runtime web. Le bon ordre est de figer le contrat local renforce, d'ajouter les fixtures qui reproduisent les echecs locaux observes, de preparer le benchmark `local_profiled`, puis seulement ensuite d'implementer profil, requetes specialisees, parametres SearXNG, reranking et Crawl4AI query-aware.

Ce plan est meilleur parce que les echecs observes viennent surtout de l'orchestration. Sans fixtures et contrat, une correction runtime pourrait sembler marcher sur un exemple tout en cassant l'URL explicite, la non-contamination ou le cout.

## Invariants produit

- Le web reste manuel: un profil de recherche ne declenche jamais le web seul.
- `explicit_url` reste prioritaire: une URL utilisateur doit etre lue directement avant toute recherche ouverte.
- Le chemin URL explicite conserve `fit` puis `raw` seulement si `fit` est vide.
- `raw` reste interdit sur les resultats search-only.
- Memory, Identity, Summary, Biblio/RAG et documents actifs ne sont pas alimentes par le web de ce chantier.
- Pas de modification globale de SearXNG ou Crawl4AI au depart.
- Pas d'OpenRouter web runtime dans ce chantier sans decision explicite future.
- Pas de reouverture de l'auto-web lexical.
- Pas de ban global de Wikipedia, dictionnaires ou conjugueurs.

## Lot 0 - Spec / contrat local web renforce

Statut: livre dans ce TODO.

### Profils minimaux

Les profils cibles sont:

- `explicit_url`;
- `actualite`;
- `technique_officielle`;
- `institutionnel_francais`;
- `academique_philosophique`;
- `general`.

Regles:

- le profil s'applique seulement si `web_search=true` ou si le chemin web est deja explicitement demande par le runtime courant;
- le profil ne remplace pas `activation_mode`;
- `activation_mode=manual` reste le mode normal du bouton web;
- `activation_mode=auto` reste non actif dans le runtime courant.

### Contrat URL explicite

`explicit_url` garde le contrat archive:

- detecter l'URL dans le message utilisateur;
- tenter Crawl4AI direct avant reformulation/search;
- produire un `read_state`;
- utiliser `crawl4ai_explicit_url_max_chars`;
- tenter `fit`, puis `raw` seulement si `fit` est vide;
- ne pas laisser une recherche fallback masquer l'echec de lecture primaire.

### Contrat recherche ouverte

Pour les profils non URL:

- construire un plan de recherche borne;
- emettre une requete principale;
- ajouter 0 a 2 requetes secondaires si le profil le justifie;
- conserver les domaines attendus et exclusions souples comme signaux, pas comme verites absolues;
- utiliser les parametres SearXNG seulement par profil;
- reranker avant Crawl4AI;
- crawler apres reranking;
- injecter seulement du materiau compatible avec le score/confiance.

### Observabilite attendue

Champs attendus a terme, sans contenu brut:

- `search_profile`;
- nombre de requetes;
- parametres SearXNG effectifs;
- domaines attendus;
- top domaines avant reranking;
- top domaines apres reranking;
- raisons de downrank/drop;
- choix Crawl4AI `fit` / `bm25` / `raw`;
- cache mode;
- confiance finale;
- fallback OpenRouter propose ou utilise.

### Confiance et fallback futur

Le score de confiance local doit pouvoir dire:

- `strong`: sources attendues et contenu utile trouves;
- `medium`: sources plausibles mais couverture incomplete;
- `weak`: bruit lexical, domaines attendus absents ou contenu insuffisant;
- `failed`: pas de source exploitable.

OpenRouter ne doit pas etre appele par ce TODO. Le futur fallback pourra seulement etre etudie si le local profile produit `weak` ou `failed`, et avec une decision produit explicite.

### Definition of done Lot 0

- [x] Profils cibles fixes.
- [x] Web manuel seulement confirme.
- [x] Priorite URL explicite confirmee.
- [x] Non-contamination Memory/Identity/Summary confirmee.
- [x] Observabilite cible listee.
- [x] Critere de confiance/fallback cible liste.

## Lot 1 - Fixtures et benchmark `local_profiled`

Statut: livre en socle de preuve, sans changement runtime.

Objectifs:

- versionner des fixtures reproduisant les mauvais ordres SearXNG du benchmark live;
- ajouter un bras benchmark `local_profiled`;
- faire pointer `local_profiled` temporairement vers le local actuel, avec un statut de stub explicite;
- prouver que le benchmark peut comparer `local`, `local_profiled`, `openrouter_exa` et `openrouter_parallel`.

Livrables:

- `benchmark/suites/web_search/fixtures/local_bad_orders.json`;
- `benchmark.suites.web_search.adapter.load_local_bad_order_fixtures()`;
- bras `local_profiled` dans `benchmark/suites/web_search/campaign.py`;
- dry-run avec artefact `local-profiled.md`;
- tests unitaires benchmark.

Non-objectifs:

- pas de profil runtime reel;
- pas de reranking runtime;
- pas de Crawl4AI BM25 runtime;
- pas d'appel OpenRouter supplementaire hors bras existants.

Definition of done Lot 1:

- [x] Les fixtures couvrent `actualite`, `technique_officielle`, `institutionnel_francais` et `academique_philosophique`.
- [x] `local_profiled` est accepte par `--web-search-arms`.
- [x] Le default benchmark inclut `local_profiled` pour les futures lectures cote a cote.
- [x] Le dry-run n'appelle ni SearXNG, ni Crawl4AI, ni OpenRouter.
- [x] Le rapport systeme isole `local-profiled.md`.

## Lot 2 - Profil de recherche

Statut: livre comme signal runtime passif.

Profil minimal implemente:

- determination deterministe dans `app/tools/web_search_profile.py`;
- profils: `explicit_url`, `actualite`, `technique_officielle`, `institutionnel_francais`, `academique_philosophique`, `general`;
- priorite URL explicite: toute URL explicite classe `explicit_url`;
- pas de declenchement web autonome: la classification ne s'executera que dans le chemin web deja active;
- propagation dans le payload web runtime, `web_input`, logs/evenements content-free, read model d'observabilite et benchmark `local_profiled`;
- fallback `general` en cas d'incertitude.

Non-objectifs confirmes:

- pas de modification des requetes;
- pas de parametres SearXNG par profil;
- pas de changement du nombre de resultats;
- pas de reranking;
- pas de BM25 Crawl4AI;
- pas d'OpenRouter runtime;
- pas de reactivation auto-web.

Definition of done Lot 2:

- [x] Classification unitaire couverte pour URL explicite, actualite, documentation officielle, institutionnel francais, academique/philosophique et fallback general.
- [x] `search_profile` present dans `build_context_payload()` et l'evenement `web_search`.
- [x] `search_profile` present dans le `web_input` canonique transmis au noeud hermeneutique.
- [x] Observabilite content-free enrichie sans contenu brut, prompt ni secret.
- [x] Benchmark `local_profiled` expose le profil runtime quand disponible, tout en restant un stub qualite jusqu'aux lots 3-6.

Risques:

- sur-classer trop vite une requete mixte;
- cacher la vraie ambiguite derriere un profil trop confiant.

## Lot 3 - Requetes specialisees bornees

Statut: a faire.

Construire un plan de recherche:

- requete principale;
- 0 a 2 requetes secondaires;
- domaines attendus;
- exclusions souples;
- langue attendue;
- `time_range` optionnel.

Exemples:

- `actualite`: actualite + source institutionnelle + fraicheur;
- `technique_officielle`: domaine docs officiel en premier;
- `institutionnel_francais`: Service Public / ANTS / domaines publics;
- `academique_philosophique`: termes conceptuels + sources academiques, souvent francais/anglais.

## Lot 4 - Parametres SearXNG par profil

Statut: a faire.

Mapper prudemment:

- `categories`;
- `engines`;
- `time_range`;
- `language`;
- `site:` / domaines;
- limites de resultats.

Regle: ne pas modifier globalement `/opt/platform/searxng/settings.yml` dans ce lot.

## Lot 5 - Reranking avant crawl

Statut: a faire.

Ajouter un reranker applicatif avant Crawl4AI:

- bonus domaines officiels attendus;
- bonus co-presence des termes essentiels;
- bonus fraicheur pour actualite;
- diversite domaines;
- malus dictionnaires/conjugueurs hors profil definitionnel;
- malus homonymes;
- score de confiance.

Le crawl ne doit plus enrichir aveuglement les deux premiers resultats SearXNG.

## Lot 6 - Crawl4AI oriente profil

Statut: a faire.

Tester puis brancher:

- `fit` par defaut;
- `bm25` + `q` pour pages longues issues de recherche;
- `raw` uniquement pour URL explicite si `fit` est vide;
- cache selon profil;
- budgets de caracteres par profil.

Regle: toute activation BM25 doit conserver une preuve que les bons passages ne sont pas perdus.

## Lot 7 - Observabilite + confiance + fallback futur

Statut: a faire.

Ajouter les signaux:

- `search_profile`;
- nombre de requetes;
- parametres SearXNG effectifs;
- top domaines avant/apres rerank;
- raisons de downrank/drop;
- choix Crawl4AI;
- cache mode;
- confiance finale;
- fallback OpenRouter propose ou utilise.

Regle: OpenRouter peut etre mentionne comme fallback futur, pas branche dans le runtime par ce lot.

## Lot 8 - Benchmark final et decision Exa/Parallel

Statut: a faire.

Relancer:

- `local`;
- `local_profiled`;
- `openrouter_exa`;
- `openrouter_parallel`.

Decision attendue:

- local seul;
- local + Exa en fallback;
- local + Parallel en fallback compact;
- autre politique explicite.

## Preuves de ce cycle

Commandes minimales:

```bash
git status --short
git diff --check
git diff --cached --check
test -f app/docs/todo-todo/product/fridadev-local-web-search-hardening-todo.md
grep -RIn "local_profiled\|search_profile\|reranking\|Crawl4AI\|SearXNG\|Exa\|Parallel" app/docs/todo-todo/product/fridadev-local-web-search-hardening-todo.md app/docs/README.md app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md
```

Si benchmark touche:

```bash
python3 -m py_compile benchmark/run_benchmark.py benchmark/suites/web_search/adapter.py benchmark/suites/web_search/campaign.py
python3 benchmark/run_benchmark.py --suite web_search --dry-run --campaign-id dry-run-web-search-hardening --output-dir /tmp/fridadev-web-search-hardening-dry-run
python3 -m unittest app.tests.unit.benchmark.test_web_search_benchmark
git diff --check
git diff --cached --check
```
