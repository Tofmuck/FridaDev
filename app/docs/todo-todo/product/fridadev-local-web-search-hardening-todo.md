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
- [x] Lot 3 - Requetes specialisees bornees
- [x] Lot 4 - Parametres SearXNG par profil
- [x] Lot 5 - Reranking avant crawl
- [x] Lot 6 - Crawl4AI oriente profil
- [x] Lot 7 - Observabilite + confiance + fallback futur
- [x] Lot 8 - Benchmark final et decision Exa/Parallel

Lecture rapide:

- Lots 0 et 1 sont livres comme socle docs/spec/benchmark.
- Lot 2 est livre comme signal runtime passif: `search_profile` est classe, propage et observe, sans effet sur la recherche.
- Lot 3 est livre: les profils non URL peuvent ajouter 0 a 2 requetes secondaires, avec aggregation bornee et deduplication URL.
- Lot 4 est livre: `local_profiled` applique des parametres SearXNG applicatifs par profil, sans modifier la config globale SearXNG.
- Lot 5 est livre: `local_profiled` rerank les resultats SearXNG de facon souple avant Crawl4AI, sans suppression dure.
- Lot 6 est livre: `local_profiled` applique une politique Crawl4AI profilee, avec `bm25` + `q` borne pour certains profils et repli `fit` si l'extraction est vide ou pauvre.
- Lot 7 est livre: les signaux locaux sont exposes avec une confiance finale visible, non souveraine et non actionnable.
- Lot 8 est livre: le benchmark final local / `local_profiled` / Exa / Parallel est produit et documente dans `app/docs/states/audits/fridadev-web-search-lot8-final-benchmark-2026-05-22.md`.
- Aucun score de confiance actionnable ou fallback OpenRouter runtime n'est livre.

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

Le score de confiance local doit pouvoir dire, en lecture produit:

- `strong`: sources attendues et contenu utile trouves;
- `medium`: sources plausibles mais couverture incomplete;
- `weak`: bruit lexical, domaines attendus absents ou contenu insuffisant;
- `failed`: pas de source exploitable.

Le runtime Lot 7 expose cette lecture sous une echelle operatoire sobre `high` / `medium` / `low` / `unknown`, avec `web_confidence_reason_codes` pour garder le signal contestable.

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

Statut: livre.

Plan de recherche livre:

- requete principale issue de la reformulation existante;
- 0 a 2 requetes secondaires via `app/tools/web_search_query_plan.py`;
- deduplication stricte des requetes;
- aggregation round-robin simple des resultats par requete;
- deduplication des resultats par URL normalisee;
- budget total de resultats borne par `searxng_results`;
- trace content-free du plan dans le payload et les evenements web.

Regles implementees:

- `explicit_url`: aucune requete secondaire; lecture directe prioritaire inchangee.
- `actualite`: variante actualite recente / sources officielles; pour IA Europe, variante `AI Act` ciblee `site:ec.europa.eu`.
- `technique_officielle`: variantes documentation officielle; OpenRouter cible `site:openrouter.ai/docs`.
- `institutionnel_francais`: variantes `service-public.fr`, `ants.gouv.fr`, `legifrance.gouv.fr` ou `gouv.fr` selon le contenu.
- `academique_philosophique`: variantes sources universitaires / OpenEdition / Cairn / Persee / Stanford Encyclopedia.
- `general`: pas de requete secondaire par defaut.

Non-objectifs confirmes:

- pas de categories, engines ou `time_range` SearXNG par profil;
- pas de reranking par score;
- pas de BM25 Crawl4AI;
- pas de fallback OpenRouter runtime;
- pas d'auto-web.

Definition of done Lot 3:

- [x] `build_specialized_queries()` couvre les profils attendus et reste borne a 2 secondaires.
- [x] `explicit_url` ne produit aucune requete secondaire.
- [x] Les resultats multi-requetes sont dedupes par URL normalisee et bornes par `searxng_results`.
- [x] L'observabilite expose `query_count`, `primary_query_sha256_12`, `secondary_query_count`, `secondary_query_sha256_12`, `deduped_result_count` et `query_plan_kind` sans requete brute.
- [x] Le benchmark peut comparer `local` baseline mono-requete et `local_profiled` avec requetes specialisees.

## Lot 4 - Parametres SearXNG par profil

Statut: livre.

Mapper prudemment, cote applicatif seulement:

- `categories`;
- `engines`;
- `time_range`;
- `language`;
- `safesearch`.

Regles implementees:

- `explicit_url`: aucune application de parametres au direct read; fallback search historique si le fallback existant est appele.
- `general`: comportement historique, `language=fr-FR`, `safesearch=0`, pas de categorie/engine/time_range ajoute.
- `actualite`: `categories=general`, `time_range=year`, `language=fr-FR`, `safesearch=0`.
- `technique_officielle`: `categories=general`, `language=all`, `safesearch=0`.
- `institutionnel_francais`: `categories=general`, `language=fr-FR`, `safesearch=0`.
- `academique_philosophique`: `categories=general`, `language=all`, `safesearch=0`.
- `engines` reste vide en V0: la config SearXNG globale locale n'est pas lisible par l'utilisateur applicatif, donc le lot evite de viser des moteurs incertains.

Garde-fous politiques source:

- ces parametres sont marques `soft_broad_hints`, pas comme une police invisible des sources legitimes;
- aucune source, domaine ou moteur unique n'est impose dans ce lot;
- aucune nouvelle contrainte `site:` n'est ajoutee ici, pour eviter un enfermement de domaine;
- la diversite minimale reste preservee par l'aggregation et la deduplication URL du Lot 3; le Lot 5 devra reranker sans censurer;
- la confiance future devra rester visible et explicable, sans pouvoir automatique d'appeler Exa, Parallel ou OpenRouter.

Observabilite content-free livree:

- `searxng_profile_params_kind`;
- `searxng_profile_params_policy`;
- `searxng_categories`;
- `searxng_engines`;
- `searxng_time_range`;
- `searxng_language`;
- `searxng_safesearch`.

Definition of done Lot 4:

- [x] Aucun fichier `/opt/platform/searxng/*` ou Docker n'est modifie.
- [x] `local` benchmark garde la baseline historique mono-requete / params historiques.
- [x] `local_profiled` porte requetes specialisees + params SearXNG par profil.
- [x] URL explicite directe ne lance aucune recherche et n'applique aucun parametre SearXNG.
- [x] Aucun `site:` nouveau n'est introduit dans ce lot; les domaines restent dans les requetes secondaires Lot 3.
- [x] Aucun reranking, BM25 Crawl4AI ou fallback OpenRouter runtime n'est livre.

Regle: ne pas modifier globalement `/opt/platform/searxng/settings.yml` dans ce lot.

## Lot 5 - Reranking avant crawl

Statut: livre.

Ajouter un reranker applicatif avant Crawl4AI:

- module pur `app/tools/web_search_rerank.py`;
- application apres aggregation/deduplication SearXNG multi-requetes et avant construction/crawl des sources;
- active seulement pour `actualite`, `technique_officielle`, `institutionnel_francais` et `academique_philosophique`;
- `explicit_url` et `general` gardent un comportement sans reranking;
- `local` benchmark garde la baseline historique;
- `local_profiled` porte requetes specialisees + params SearXNG + reranking souple.

Regles implementees:

- bonus souple pour domaines officiels ou academiques attendus selon profil;
- bonus souple de co-presence des termes essentiels;
- termes essentiels derives de la demande utilisateur et de la requete reformulee, sans mots-cles de fixtures injectes par profil;
- bonus fort de domaine officiel/academique conditionne par au moins un terme essentiel issu de la demande reelle; sinon le domaine ne recoit qu'un signal contextuel faible;
- pour `technique_officielle`, le bonus fort de documentation officielle depend de l'alignement marque/outil/API demande avec le domaine, le titre ou l'URL; `openrouter.ai` n'est pas une whitelist dominante hors requete OpenRouter;
- les surfaces techniques docs-like restent generiques et prudentes: prefixes `docs.`, `developer.`, `dev.`, `learn.` et chemins comme `/api/`, `/docs`, `/guide`, `/learn`, `/reference`, toujours conditionnes par l'alignement avec la demande;
- bonus souple de fraicheur pour actualite quand des marqueurs recents existent;
- malus souple dictionnaires/conjugueurs hors profil definitionnel;
- malus souple homonymes evidents, notamment `Trace Colmar` sur Derrida/trace;
- diversite simple de domaines pour eviter qu'un seul domaine occupe toute la tete si d'autres domaines plausibles existent;
- aucun resultat n'est supprime par le reranker; le budget reste borne par `searxng_results`;
- les sources hors profil restent presentes quand elles sont dans le budget.

Le crawl ne doit plus enrichir aveuglement les deux premiers resultats SearXNG.

Garde-fous politiques source:

- le reranking reordonne, mais ne censure pas;
- les bonus/malus sont explicites et souples;
- les fixtures de benchmark ne deviennent pas des normes cachees de legitimite;
- aucun domaine, moteur ou type de source unique n'est impose;
- Wikipedia, dictionnaires et conjugueurs ne sont pas bannis globalement;
- la diversite est un garde-fou de pluralite, pas un filtre dur;
- aucun score de confiance actionnable n'est livre dans ce lot;
- Exa, Parallel et OpenRouter restent hors runtime.

Observabilite content-free livree:

- `rerank_applied`;
- `rerank_policy`;
- `rerank_input_count`;
- `rerank_output_count`;
- `rerank_profile`;
- `rerank_top_domains_before`;
- `rerank_top_domains_after`;
- `rerank_reason_counts`;
- `rerank_promoted_count`;
- `rerank_downranked_count`;
- champs source internes `raw_rank`, `reranked_rank`, `rerank_score`, `rerank_bucket`, `rerank_reason_codes`.

Definition of done Lot 5:

- [x] Dictionnaires/conjugueurs downrankes dans `institutionnel_francais` quand Service Public/ANTS sont plausibles.
- [x] Documentation officielle promue dans `technique_officielle`.
- [x] Source UE/officielle promue dans `actualite`.
- [x] Source academique promue dans `academique_philosophique`.
- [x] Diversite minimale de domaines preservee sans imposer un domaine unique.
- [x] Resultats hors profil non supprimes brutalement.
- [x] Tests anti-overfit: CAF/logement, Ukraine/diplomatie et Kant/jugement reflechissant ne sont pas ecrases par les fixtures CNI, AI Act Europe ou Derrida/trace.
- [x] Tests anti-overfit technique: Stripe Checkout et une doc generique alignee battent une documentation OpenRouter officielle mais hors demande.
- [x] Tests docs-like techniques: Microsoft Graph sur `learn.microsoft.com`, React `reference` et Vue `guide` restent promus seulement quand ils sont alignes avec la demande.
- [x] Reason codes observables sans contenu brut.
- [x] URL explicite directe inchangee.
- [x] Benchmark `local` reste baseline; `local_profiled` porte le reranking.
- [x] Aucun BM25, cache policy, OpenRouter, Exa, Parallel, auto-web ou fallback externe runtime.

## Lot 6 - Crawl4AI oriente profil

Statut: livre.

Politique livree:

- `fit` reste le defaut pour `general` et `actualite`;
- `bm25` + `q` est active uniquement sur les resultats search-only des profils `technique_officielle`, `institutionnel_francais` et `academique_philosophique`;
- si `bm25` retourne une extraction vide, en erreur ou trop pauvre, le pipeline se replie vers `fit`;
- `raw` reste reserve au chemin URL explicite direct, uniquement quand `fit` est vide;
- cache `c=1` est utilise pour les extractions BM25 profilees; le chemin historique et l'actualite restent en lecture fraiche/write-through `c=0`;
- budgets de caracteres bornes par profil: actualite 4500, technique 7000, institutionnel 6500, academique 8000, general/explicit fallback 5000 sous le plafond runtime;
- observabilite content-free ajoute `crawl4ai_policy_kinds`, `crawl4ai_filter_counts`, `crawl4ai_cache_modes`, `crawl4ai_fallback_used_count`, hash de query Crawl4AI et resume d'extraction par source.

Regle: toute activation BM25 doit conserver une preuve que les bons passages ne sont pas perdus.

Definition of done Lot 6:

- [x] Politique isolee dans `app/tools/web_search_crawl_policy.py`.
- [x] URL explicite directe conserve `fit` puis `raw` seulement si `fit` est vide.
- [x] Search-only n'utilise jamais `raw`.
- [x] BM25 + `q` est borne aux profils utiles et conserve `fit` comme repli non-censeur.
- [x] Tests de non-perte: si BM25 est pauvre, le passage utile du `fit` est conserve dans le contexte.
- [x] `general` garde un comportement historique sobre.
- [x] Signaux Crawl4AI exposes sans contenu brut, sans prompt brut et sans secret.
- [x] Benchmark `local_profiled` expose les signaux Crawl4AI du Lot 6.
- [x] Aucun score de confiance actionnable, OpenRouter, Exa, Parallel, auto-web, BM25 global ou modification SearXNG/Crawl4AI globale.

## Lot 7 - Observabilite + confiance + fallback futur

Statut: livre.

Signaux exposes:

- `search_profile`;
- nombre de requetes;
- parametres SearXNG effectifs;
- top domaines avant/apres rerank;
- raisons de downrank/drop;
- choix Crawl4AI;
- cache mode;
- fallback BM25 -> `fit`;
- `used_content_kinds`;
- `injected_chars`;
- `context_chars`;
- `read_state`;
- confiance finale via `web_confidence_policy_kind`, `web_confidence_level`, `web_confidence_score`, `web_confidence_reason_codes` et `web_confidence_inputs_summary`;
- fallback OpenRouter futur via `openrouter_fallback_state`, `openrouter_fallback_used` et `openrouter_fallback_reason_codes`.

Regles livrees:

- la confiance est une heuristique d'audit visible, pas une decision;
- elle ne modifie pas l'ordre des sources;
- elle ne supprime aucune source;
- elle ne change pas le contenu injecte;
- `openrouter_fallback_used` reste toujours `false`;
- OpenRouter, Exa et Parallel peuvent etre mentionnes comme fallback futur ou candidat de revue humaine, mais ne sont pas appeles dans le runtime.

Definition of done Lot 7:

- [x] Politique de confiance isolee dans `app/tools/web_search_confidence.py`.
- [x] Signaux ajoutes au payload web runtime et aux evenements `web_search` sans contenu brut.
- [x] Signaux visibles dans les read models / checklist d'observabilite.
- [x] Benchmark local/local_profiled expose la confiance et l'etat de fallback futur.
- [x] Tests: confiance haute sur contenu crawle lu, confiance basse sur no-data/snippets, URL explicite preserve son `read_state`.
- [x] `openrouter_fallback_used` reste faux; aucun appel OpenRouter, Exa ou Parallel n'est ajoute.
- [x] Aucun changement SearXNG, reranking, Crawl4AI policy, auto-web, Memory, Identity, Summary, Biblio/RAG ou Docker.

## Lot 8 - Benchmark final et decision Exa/Parallel

Statut: livre.

Artefacts live a lire:

- `/tmp/fridadev-web-search-lot8-live/local.md`;
- `/tmp/fridadev-web-search-lot8-live/local-profiled.md`;
- `/tmp/fridadev-web-search-lot8-live/openrouter-exa.md`;
- `/tmp/fridadev-web-search-lot8-live/openrouter-parallel.md`.

Bras relances:

- `local`;
- `local_profiled`;
- `openrouter_exa`;
- `openrouter_parallel`.

Decision produite:

- chemin par defaut: local FridaDev;
- URL explicite: local direct prioritaire, sans fallback externe;
- fallback futur recommande: Exa seulement comme soupape explicite et auditable pour certaines recherches ouvertes a enjeu;
- Parallel: option compacte possible, mais trop inegale pour devenir fallback prioritaire;
- aucun fallback OpenRouter runtime active.

Findings a garder pour un chantier ulterieur:

- `local_profiled` regresse fortement sur `recent_ai_policy_news` dans le run Lot 8 alors que le local baseline retrouve des sources UE / AI Act;
- `web_confidence_level=high` reste possible sur un corpus actualite hors sujet, donc la confiance demeure visible et non actionnable;
- le profil academique/philosophique reste fragile pour obtenir une cartographie primaire / encyclopedique / academique.

Definition of done Lot 8:

- [x] Dry-run complet produit.
- [x] Run live borne produit avec les quatre bras.
- [x] Artefacts par bras disponibles dans `/tmp/fridadev-web-search-lot8-live`.
- [x] Grep securite vide apres redaction des apercus d'artefacts.
- [x] Note de decision versionnee: `app/docs/states/audits/fridadev-web-search-lot8-final-benchmark-2026-05-22.md`.
- [x] Aucun fallback OpenRouter/Exa/Parallel runtime active.

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
