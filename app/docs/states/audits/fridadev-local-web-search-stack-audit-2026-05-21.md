# FridaDev local web search stack audit - 2026-05-21

Statut: audit docs-only versionne.

Perimetre: comparer la documentation officielle SearXNG/Crawl4AI, la configuration Docker OVH lue en lecture seule, le pipeline FridaDev courant et les resultats du benchmark live local/Exa/Parallel.

Hors scope respecte: aucun changement runtime, prompt, memoire, identity, summary, Docker, SearXNG, Crawl4AI, settings live ou integration OpenRouter.

## Question prealable: existe-t-il un meilleur plan ?

Oui: le meilleur plan n'est pas de patcher directement le runtime local ni de basculer vers OpenRouter, mais de separer quatre couches avant toute implementation:

1. ce que SearXNG et Crawl4AI savent deja faire officiellement;
2. ce que la plateforme OVH expose reellement;
3. ce que FridaDev utilise effectivement;
4. ce que le benchmark live montre comme symptomes.

Ce plan est plus sur parce que les echecs observes ne ressemblent pas a une impossibilite structurelle de la stack locale. Ils ressemblent surtout a une orchestration trop pauvre: requete unique, absence de profil de recherche, absence de reranking, crawl trop tot des premiers resultats et faible usage des filtres Crawl4AI.

## Resume executif

La stack locale est saine sur les URL explicites. Le chemin `explicit_url_direct` lit directement l'URL avec Crawl4AI, renseigne `read_state=page_read` quand la page est lue, applique un budget plus large et evite le bruit SearXNG. Le benchmark live confirme que c'est le meilleur bras local.

La stack locale est fragile sur les recherches ouvertes. FridaDev reformule en une seule requete courte, interroge SearXNG avec seulement `q`, `format=json`, `language=fr-FR`, `safesearch=0`, conserve l'ordre SearXNG, crawle les deux premiers resultats et injecte les cinq premiers resultats sans reranking metier. Les echecs `regulation`, `trace` et `renouveler` viennent directement de ce contrat.

SearXNG n'est pas exploite a son niveau documentaire. L'API supporte `categories`, `engines`, `time_range`, les operateurs de requete, les moteurs actives/desactives et une configuration de poids. La configuration OVH active Wikipedia avec un poids eleve et des moteurs generalistes, mais des moteurs utiles a certains profils sont desactives, notamment news et certaines sources techniques. Cela n'est pas mauvais en soi; c'est simplement trop uniforme pour les profils `actualite`, `technique officielle`, `institutionnel francais` ou `academique`.

Crawl4AI est plus capable que ce que FridaDev consomme. Le endpoint local `/md` expose `fit`, `raw`, `bm25` et `llm`, un parametre `q` et un mode cache. FridaDev utilise correctement `fit` puis `raw` uniquement pour URL explicite, ce qui est une bonne borne. En revanche, FridaDev n'utilise pas le filtrage query-aware BM25 pour les pages issues d'une recherche, et lit le cache en mode frais/ecriture seulement.

Le local peut raisonnablement etre renforce avant tout fallback OpenRouter. Le meilleur ordre est: profil de recherche, multi-requetes specialisees, parametres SearXNG par profil, reranking local avant crawl, crawl query-aware apres reranking, puis politique de confiance/fallback.

OpenRouter Exa/Parallel doit rester un complement borne. Exa est le meilleur bras qualite du benchmark, mais il est plus couteux et injecte beaucoup plus de tokens. Parallel est plus compact, mais plus inegal. Apres renforcement local, leur place naturelle est le fallback explicite ou conditionnel sur faible confiance, pas le remplacement global du pipeline local.

## Etat actuel FridaDev

### Declenchement et auto-web

`app/core/chat_service.py` appelle `_resolve_web_runtime_payload()` avec le flag utilisateur `web_search_on`. Le chantier archive `app/docs/todo-done/refactors/hermeneutic-suspension-auto-web-todo.md` a ferme volontairement l'auto-web lexical:

- `web_search=true` produit un mode manuel;
- `web_search=false` produit `not_requested`;
- les tours ordinaires ne declenchent plus le web automatiquement.

Cette borne doit rester en place. Le present audit ne recommande pas de rouvrir l'auto-web lexical.

### Reformulation web

`app/tools/web_search.py` utilise `reformulate()` avant SearXNG. Le prompt `app/prompts/web_reformulation.txt` demande une requete concise, en francais sauf besoin anglophone, avec l'annee courante pour les sujets recents, et un maximum de huit mots.

Effet observe: la requete devient souvent lexicalement propre mais semantiquement trop pauvre. Dans le benchmark local:

- `régulation IA Europe 2026 changements récents sources` laisse le terme generique `régulation` dominer;
- `trace Derrida sources primaires encyclopédie commentaires académiques` laisse `trace` etre compris comme nom commun ou nom propre;
- `renouveler carte nationale d’identité française procédure officielle source administrative 2026` laisse `renouveler` attirer des conjugueurs.

La reformulation actuelle ne produit ni profil de recherche, ni domaines attendus, ni requetes alternatives, ni signaux de sources officielles.

### Requete SearXNG

`app/tools/web_search.py::search()` appelle SearXNG avec ces seuls parametres:

- `q`;
- `format=json`;
- `language=fr-FR`;
- `safesearch=0`.

Les parametres documentes mais non utilises sont notamment:

- `categories`;
- `engines`;
- `time_range`;
- `pageno`;
- activation/desactivation ponctuelle de moteurs;
- operateurs de requete comme `site:`.

`searxng_results` vaut actuellement `5` cote runtime. `search()` tranche les resultats JSON a cette limite.

### Construction et injection du materiau web

`app/tools/web_search.py::build_context_payload()` suit deux chemins:

- URL explicite: detection par `_extract_explicit_url()`, lecture directe via Crawl4AI, puis recherche fallback seulement si la lecture directe echoue;
- recherche ouverte: reformulation unique, appel SearXNG unique, construction du contexte dans l'ordre SearXNG.

`_build_source_payload()` crawle seulement les resultats `rank <= crawl4ai_top_n`. `crawl4ai_top_n` vaut actuellement `2`. Les resultats crawles sont tronques a `crawl4ai_max_chars=5000`. Les autres resultats injectent seulement titre/snippet/URL.

Il n'y a pas de score local, pas de reranking par domaine, pas de detection de dictionnaire/conjugueur, pas de diversite de domaines, pas de deuxieme passe et pas de politique par categorie.

### Lecture explicite et read_state

Le chantier `app/docs/todo-done/notes/web-reading-truth-todo.md` a stabilise le contrat de lecture:

- URL explicite lue directement avant recherche;
- `read_state` renseigne `page_read`, `page_partially_read`, `page_not_read_crawl_empty`, `page_not_read_error` ou `page_not_read_snippet_fallback`;
- `fit` est tente avant `raw`;
- `raw` est reserve au fallback d'URL explicite, pas aux resultats search-only;
- `crawl4ai_explicit_url_max_chars=25000` donne un budget plus large aux URL explicites.

Ce contrat est coherent avec la documentation Crawl4AI: utiliser un markdown filtre en premier et reserver le brut aux cas ou l'utilisateur a explicitement donne l'URL.

### Observabilite et non-contamination

Le web passe dans le noeud hermeneutique via `app/core/hermeneutic_node/inputs/web_input.py`. Les logs content-free sont produits par:

- `app/observability/hermeneutic_node_logger.py`;
- `app/observability/turn_pipeline_read_model.py`;
- `app/observability/turn_observability_checklist.py`.

Les signaux actuels couvrent notamment le statut, `read_state`, le nombre de resultats, les types de contenu utilises, des hashes de requete et des chemins de collecte. Ils ne couvrent pas encore un futur `search_profile`, les parametres SearXNG reels, les raisons de reranking, les domaines ecartes ou les signaux de confiance.

La non-contamination Memory/Identity/Summary est preservee par le contrat courant: le web est injecte dans le tour, pas transforme en memoire persistante.

## Resultats benchmark et symptomes

Les fichiers live etaient encore presents dans `/tmp/fridadev-web-search-live/`:

- `local.md`;
- `openrouter-exa.md`;
- `openrouter-parallel.md`.

Le benchmark confirme trois regimes.

### Local SearXNG + Crawl4AI

Forces:

- rapide;
- sans cout OpenRouter cote recherche;
- tres bon sur URL explicite;
- observable dans le pipeline FridaDev;
- souverain, lisible et testable localement.

Faiblesses observees:

- bruit lexical sur les recherches ouvertes;
- sources officielles parfois presentes mais trop basses;
- dictionnaires/conjugueurs/Wikipedia generique trop hauts;
- absence de seconde passe quand les premiers resultats sont visiblement mauvais.

Cas live:

- `recent_ai_policy_news`: Wikipedia `Régulation`, Wiktionary, puis Commission europeenne seulement en rang 3; Larousse et Le Robert ensuite.
- `official_openrouter_server_tools`: DataCamp en rang 1, OpenRouter seulement rang 2; pas de restriction domaine officielle.
- `explicit_url_reading_contract`: `page_read`, `explicit_url_direct`, bonne lecture de la page OpenRouter.
- `conceptual_philosophy_search`: Larousse, Trace Colmar, OpenEdition, Wiktionary, Le Robert; un bon domaine academique existe mais les homonymes dominent.
- `french_admin_service_public`: Le Conjugueur, Bescherelle, Service Public rang 3, NouvelObs conjugaison, Larousse conjugaison.

### OpenRouter Exa

Exa donne la meilleure qualite globale du run, avec davantage de sources pertinentes et de meilleurs contenus officiels. Le cout et le volume de tokens sont nettement superieurs au local et a Parallel.

Conclusion: Exa est une bonne soupape haute qualite quand le local ne trouve pas de sources fiables, pas un bon remplacement permanent si l'objectif est souverainete, cout bas et observabilite locale.

### OpenRouter Parallel

Parallel est plus compact et moins cher qu'Exa dans le run. Il est aussi plus inegal:

- bon sur certains cas officiels;
- fragile sur philosophie academique;
- moins strict sur URL explicite quand le bon outil serait une lecture de page plutot qu'une recherche ouverte.

Conclusion: Parallel peut etre un fallback economique ou un comparateur, mais il ne doit pas etre traite comme oracle.

## Bonnes pratiques SearXNG pertinentes

Documentation consultee:

- documentation principale: <https://docs.searxng.org/>;
- Search API: <https://docs.searxng.org/dev/search_api.html>;
- settings: <https://docs.searxng.org/admin/settings/index.html>;
- section `search`: <https://docs.searxng.org/admin/settings/settings.html>;
- engines: <https://docs.searxng.org/admin/settings/settings_engines.html>;
- plugin Hostnames: <https://docs.searxng.org/dev/plugins/hostnames.html>.

Points applicables a FridaDev:

1. L'API `/search` accepte plus que `q`: elle expose `categories`, `engines`, `language`, `pageno`, `time_range`, `safesearch` et `format`.
2. `format=json` doit etre autorise cote settings. La configuration OVH l'autorise deja.
3. `language=fr-FR` est coherent pour l'instance Tof, mais certains profils doivent pouvoir forcer ou ajouter l'anglais, notamment docs techniques et philosophie academique.
4. `time_range` est pertinent pour l'actualite. Ne pas l'utiliser favorise des pages encyclopediques ou intemporelles.
5. Les moteurs ont des `categories`, `disabled`, `timeout`, `weight` et raccourcis. Les poids influencent le classement. Des moteurs peuvent etre inactifs par defaut mais activables selon requete ou config.
6. `use_default_settings` permet de garder les defaults tout en modifiant, conservant ou supprimant des moteurs. Cela rend possible une configuration propre, mais elle doit rester prudente car elle affecte tous les usages de SearXNG.
7. La syntaxe de recherche et les parametres permettent des requetes specialisees, notamment `site:` pour cibler un domaine ou une famille de domaines quand le profil l'exige.
8. Le plugin Hostnames peut prioriser ou retirer des hostnames, mais il s'agit d'un levier global de metasearch. Pour FridaDev, le premier levier devrait etre un reranking applicatif par profil, avant de rendre des bans globaux.

Implication: FridaDev n'utilise aujourd'hui qu'un sous-ensemble minimal de SearXNG. Les echecs du benchmark ne prouvent pas que SearXNG est impropre; ils prouvent que FridaDev lui pose une question trop uniforme et accepte son ordre brut.

## Bonnes pratiques Crawl4AI pertinentes

Documentation consultee:

- documentation principale: <https://docs.crawl4ai.com/>;
- self-hosting / Docker API: <https://docs.crawl4ai.com/core/self-hosting/>;
- markdown generation: <https://docs.crawl4ai.com/core/markdown-generation/>;
- fit markdown et content filters: <https://docs.crawl4ai.com/core/fit-markdown/>;
- cache modes: <https://docs.crawl4ai.com/core/cache-modes/>;
- notes v0.8.0 Docker API / securite: <https://docs.crawl4ai.com/blog/releases/v0.8.0/>.

Points applicables a FridaDev:

1. `DefaultMarkdownGenerator` peut produire un markdown brut et un markdown filtre.
2. `PruningContentFilter` sert a supprimer le bruit par heuristique de pertinence et seuils.
3. `BM25ContentFilter` est fait pour le filtrage query-aware avec `user_query`.
4. `fit_markdown` est le bon contenu a privilegier pour limiter tokens et bruit.
5. Les pages longues risquent de perdre les bons passages si le filtrage ou la troncature intervient avant une selection orientee par la requete.
6. Les cache modes permettent de choisir entre lecture/ecriture cache, bypass et modes partiels. Le cache peut ameliorer latence et fiabilite sur docs stables, mais il peut rendre l'actualite stale s'il est utilise sans profil.
7. La documentation self-hosting decrit un serveur Docker avec des endpoints de crawl, sante, schema et markdown. Le `/md` POST de la plateforme FridaDev est un patch local, pas le endpoint stock tel quel; il reste aligne avec l'usage documentaire attendu: obtenir un markdown borne pour une URL.
8. Les notes v0.8.0 indiquent que les hooks Docker API sont desactives par defaut pour raison de securite. La config OVH garde `CRAWL4AI_HOOKS_ENABLED=false`, ce qui est coherent pour un lecteur web expose au pipeline applicatif.

Configuration Crawl4AI OVH lue en lecture seule:

- image `unclecode/crawl4ai:0.8.0`;
- endpoint local `/md`;
- `f=fit`, `f=raw`, `f=bm25`, `f=llm` exposes par le patch local;
- `q` est disponible pour BM25/LLM;
- `c=1` lit/ecrit le cache, `c=0` force une collecte fraiche en ecrivant ensuite;
- `fit` utilise `PruningContentFilter(min_word_threshold=10, threshold_type="dynamic", threshold=0.45)`;
- `bm25` utilise `BM25ContentFilter(user_query=q, bm25_threshold=1.2)`;
- navigateur headless en `text_mode=true`, timeout page court, workers `1`.

Implication: FridaDev utilise correctement le chemin prudent `fit` puis `raw` pour URL explicite, mais n'utilise pas les capacites BM25/cache deja exposees par le service local.

## Comparaison docs vs implementation actuelle

| Sujet | Docs / capacite | FridaDev actuel | Evaluation |
| --- | --- | --- | --- |
| `format=json` | SearXNG Search API | utilise | correct |
| `language` | SearXNG Search API | force `fr-FR` | correct par defaut, trop rigide pour technique/academique |
| `safesearch` | SearXNG Search API | `0` | acceptable pour recherche generale |
| `categories` | SearXNG Search API | non utilise | manque structurant |
| `engines` | SearXNG Search API | non utilise | manque structurant |
| `time_range` | SearXNG Search API | non utilise | tres penalise l'actualite |
| `site:` / domaines | syntaxe SearXNG | non orchestre | penalise docs officielles et institutionnel |
| poids moteurs | settings engines | config globale seulement | utile mais trop global sans profil |
| Hostnames plugin | priorisation/retrait hostnames | non utilise | possible mais a manier apres reranking applicatif |
| `fit_markdown` | Crawl4AI markdown filtre | utilise | bon choix |
| `raw` | Crawl4AI markdown brut | URL explicite seulement | bonne borne |
| `BM25ContentFilter` | Crawl4AI query-aware | non utilise | manque structurant |
| cache | Crawl4AI cache modes | `c=0` systematique | fiable pour fraicheur, moins bon pour latence/stabilite |
| reranking | a faire applicativement | absent | cause majeure du bruit |
| profils de recherche | a faire applicativement | absent | cause majeure du bruit |

## Explication concrete des echecs locaux

### Actualite IA Europe 2026

Cause dominante: profil `actualite/institutionnel` non exprime.

La requete reformulee met `régulation` en tete et ne force ni `time_range`, ni moteurs news, ni domaines institutionnels europeens. SearXNG renvoie donc des resultats lexicaux et encyclopediques. La configuration OVH a les moteurs news desactives et Wikipedia activee avec poids eleve. Crawl4AI n'est pas la cause premiere: il lit les premiers resultats fournis.

Le correctif local doit combiner:

- requetes specialisees autour de `AI Act`, Commission europeenne et sources UE;
- `time_range` quand l'utilisateur demande recent/2026;
- reranking qui favorise domaines institutionnels et actualite fiable;
- downrank des dictionnaires pour ce profil.

### Derrida / trace

Cause dominante: homonymie non resolue et absence de profil academique/philosophique.

La requete contient `trace`, mais ne force pas assez `Derrida`, `deconstruction`, sources primaires ou domaines academiques. Les resultats `Larousse`, `Wiktionary` et `Trace Colmar` sont plausibles lexicalement mais faux pour l'intention. OpenEdition apparait mais trop bas pour devenir dominant.

Le correctif local doit combiner:

- requetes alternatives en francais et anglais;
- domaines ou moteurs academiques selon disponibilite;
- downrank des dictionnaires et homonymes de marque/lieu pour le profil academique;
- reranking title/snippet qui exige la co-presence `Derrida` + `trace` ou equivalents.

### Renouvellement CNI

Cause dominante: le verbe `renouveler` attire les conjugueurs et le profil institutionnel francais n'est pas impose.

La requete contient pourtant `procédure officielle source administrative`, mais FridaDev ne traduit pas ces indices en domaines cibles (`service-public.fr`, `ants.gouv.fr`, domaines publics). Les conjugueurs gagnent car l'ordre SearXNG brut est injecte sans correction.

Le correctif local doit combiner:

- requete orientee procedure administrative, pas infinitif isole;
- priorisation forte de domaines officiels francais;
- downrank conditionnel des conjugueurs;
- seuil de confiance qui signale si aucun domaine public attendu n'est trouve.

### Docs OpenRouter

Cause dominante: absence de restriction officielle pour un profil technique.

DataCamp devance la documentation officielle. Ce n'est pas catastrophique, car OpenRouter apparait, mais c'est insuffisant pour une question de parametres/couts actuels.

Le correctif local doit combiner:

- profil `technique officielle`;
- `site:openrouter.ai/docs` ou domaines cibles;
- fallback secondaire seulement si la source officielle ne couvre pas la question;
- possibilite de plusieurs requetes courtes au lieu d'une seule requete large.

### URL explicite OpenRouter

Cause dominante: aucune regression observee.

Le chemin local est le bon: detection URL, lecture directe, `read_state=page_read`, pas de recherche ouverte qui parasite. Il faut le conserver tel quel dans le prochain lot.

## Findings

### P1 - La recherche ouverte fait confiance a l'ordre SearXNG brut

Fichiers:

- `app/tools/web_search.py::search()`;
- `app/tools/web_search.py::_build_search_context_material()`;
- `app/tools/web_search.py::_build_source_payload()`.

Constat: FridaDev appelle une seule requete SearXNG avec les parametres minimaux, puis injecte les resultats dans l'ordre recu. Les deux premiers resultats sont crawles avant toute evaluation locale.

Impact: un dictionnaire ou un conjugueur en rang 1-2 devient plus richement injecte qu'une source officielle en rang 3. C'est exactement ce qui se passe pour CNI et IA Europe.

Levier: ajouter un reranking applicatif avant crawl et injection. Le reranking doit utiliser domaine, titre, snippet, profil de recherche, diversite de sources, signaux officiels et downrank conditionnel.

### P1 - La reformulation unique et courte perd l'intention de source

Fichiers:

- `app/prompts/web_reformulation.txt`;
- `app/tools/web_search.py::reformulate()`;
- `app/tools/web_search.py::build_context_payload()`.

Constat: le prompt produit une seule requete de huit mots maximum. Il ne produit ni type de recherche, ni domaines attendus, ni requetes alternatives.

Impact: les termes ambigus (`régulation`, `trace`, `renouveler`) deviennent les pivots de recherche au lieu des signaux de source (`Commission europeenne`, `Derrida`, `service-public`, `ANTS`, `docs officielles`).

Levier: remplacer la reformulation simple par un plan de recherche borne: profil, requete principale, requetes secondaires optionnelles, domaines attendus et exclusions souples. Ce plan peut rester determine et testable.

### P1 - Les profils de recherche ne sont pas representes dans SearXNG

Fichiers/config:

- `app/tools/web_search.py::search()`;
- `/opt/platform/searxng/settings.yml` lu via conteneur.

Constat: SearXNG supporte `categories`, `engines`, `time_range` et operateurs. FridaDev ne les utilise pas. La config OVH est uniforme: moteurs generalistes actifs, Wikipedia activee avec poids eleve, moteurs news desactives, certains moteurs techniques desactives.

Impact: le meme pipeline sert une actualite 2026, une procedure administrative, une question philosophique et une documentation API. Cette uniformite explique les resultats bruites.

Levier: introduire des profils FridaDev, puis mapper chaque profil vers un petit ensemble de parametres/requetes SearXNG. Ne pas commencer par modifier globalement la configuration.

### P2 - Crawl4AI expose BM25 mais FridaDev ne l'utilise pas

Fichiers/config:

- `app/tools/web_search.py::_build_crawl4ai_md_payload()`;
- `app/tools/web_search.py::_crawl_markdown_with_status()`;
- `/opt/platform/crawl4ai/api.py`;
- `/opt/platform/crawl4ai/schemas.py`.

Constat: le endpoint local `/md` accepte `f=bm25` et `q`. FridaDev envoie `f=fit` pour les resultats crawles et ne joint pas de `q`.

Impact: sur les pages longues, le bon passage peut etre elimine ou noye avant injection, surtout si `crawl4ai_max_chars=5000` tronque apres un filtre non oriente par la requete.

Levier: tester `fit` vs `bm25` par profil et type de page. Pour les resultats search-only, `raw` doit rester interdit; BM25 est le bon candidat pour une lecture orientee mais bornee.

### P2 - La politique cache est trop uniforme

Fichiers/config:

- `app/tools/web_search.py::_build_crawl4ai_md_payload()`;
- `/opt/platform/crawl4ai/api.py`;
- documentation Crawl4AI cache modes.

Constat: FridaDev passe `c=0`, que le patch local interprete comme collecte fraiche avec ecriture cache. Cela evite une lecture stale, mais ne profite pas du cache pour docs stables et pages institutionnelles.

Impact: latence et fiabilite restent moins bonnes que possible sur sources stables; a l'inverse, activer le cache partout serait mauvais pour l'actualite.

Levier: politique par profil: frais pour actualite, cache lisible pour docs officielles stables, administration et philosophie, avec signal d'observabilite.

### P2 - Les limites `searxng_results=5` et `crawl4ai_top_n=2` sont bonnes pour le cout, pas pour un ordre non reranke

Fichiers:

- `app/tools/web_search.py::_runtime_collection_settings()`;
- settings runtime lus dans le conteneur FridaDev.

Constat: le budget est sobre. Mais quand les deux premiers resultats sont mauvais, le crawl enrichit le bruit.

Impact: augmenter `crawl4ai_top_n` sans reranking aggraverait parfois le bruit et la latence. Garder `top_n=2` sans reranking laisse les sources officielles trop souvent en snippet seulement.

Levier: reranker avant d'appliquer `crawl4ai_top_n`, puis rendre le nombre de pages crawlees adaptatif par profil et confiance.

### P2 - Les bans globaux seraient dangereux

Fichiers/config:

- `/opt/platform/searxng/settings.yml`;
- documentation SearXNG engines et Hostnames plugin.

Constat: Wikipedia, dictionnaires et conjugueurs sont nuisibles dans les cas benchmarkes, mais ils peuvent etre pertinents pour des questions definitionnelles ou linguistiques.

Impact: desactiver Wikipedia/dictionnaires partout corrigerait les exemples au prix d'une regression produit ailleurs.

Levier: downrank ou exclusion souple par profil dans FridaDev, puis seulement ensuite envisager Hostnames/plugin ou settings SearXNG pour les cas globalement toxiques.

### P3 - Observabilite insuffisante pour diagnostiquer un futur profil

Fichiers:

- `app/observability/hermeneutic_node_logger.py`;
- `app/observability/turn_pipeline_read_model.py`;
- `app/observability/turn_observability_checklist.py`;
- `app/core/hermeneutic_node/inputs/web_input.py`.

Constat: l'observabilite actuelle est bonne pour savoir si le web a ete injecte, quels types de contenu sont utilises et quel `read_state` est present. Elle ne peut pas encore expliquer pourquoi un domaine a ete choisi ou ecarte.

Impact: apres implementation d'un reranker, il faudra logger sans contenu sensible: profil, nombre de requetes, parametres SearXNG, domaines attendus trouves, raisons de downrank/drop et score de confiance.

Levier: ajouter ces champs en meme temps que le lot reranking, sans stocker le texte complet.

### P3 - Le budget URL explicite n'est pas visible dans le runtime canonique web

Fichier:

- `app/core/hermeneutic_node/inputs/web_input.py::_canonical_runtime()`.

Constat: le runtime canonique expose `searxng_results`, `crawl4ai_top_n` et `crawl4ai_max_chars`, mais pas `crawl4ai_explicit_url_max_chars`.

Impact: l'audit du chemin URL explicite est moins lisible, alors que c'est le chemin local le plus solide.

Levier: ajouter le champ dans un futur lot observabilite si cela ne casse pas les snapshots.

## Plan de renforcement local propose

### Lot 0 - Verrouiller l'audit et les fixtures

Objectif: conserver le present audit comme reference de depart et ne pas faire de changement runtime sans tests ciblant les echecs connus.

Preuves futures:

- fixtures de resultats SearXNG bruites pour `regulation`, `trace`, `renouveler`;
- assertions sur les domaines attendus;
- assertions sur non-contamination Memory/Identity/Summary.

### Lot 1 - Introduire un profil de recherche

Ajouter un typage borne du besoin web, sans rouvrir l'auto-web:

- `explicit_url`;
- `actualite`;
- `technique_officielle`;
- `institutionnel_francais`;
- `academique_philosophique`;
- `general`.

Le profil peut etre produit par une petite heuristique ou une reformulation structuree, mais il doit etre observable et testable. Il ne decide pas seul d'activer le web; il ne s'applique que quand l'utilisateur a demande le web.

### Lot 2 - Produire plusieurs requetes specialisees

Remplacer la requete unique par une petite liste bornee selon profil:

- actualite: requete generale + requete institutionnelle + fenetre temporelle;
- technique officielle: `site:` ou domaines officiels en premier;
- institutionnel francais: domaines publics attendus;
- academique/philosophique: requetes francais/anglais et termes savants;
- general: une requete principale seulement sauf faible confiance;
- URL explicite: lecture directe, recherche fallback seulement en cas d'echec.

Le but n'est pas de faire beaucoup de recherches. Le but est de ne plus demander a une seule requete ambigue de tout resoudre.

### Lot 3 - Utiliser les parametres SearXNG par profil

Mapper les profils vers des parametres:

- `time_range` pour actualite quand l'intention le demande;
- `categories` et `engines` quand cela ameliore le profil;
- langue flexible pour technique/academique;
- `site:` pour sources officielles ou institutionnelles;
- pas de ban global par defaut.

La configuration SearXNG globale ne devrait venir qu'apres mesure. Le premier levier doit rester applicatif pour eviter les regressions transverses.

### Lot 4 - Reranker avant de crawler

Ajouter un reranker local entre SearXNG et Crawl4AI:

- bonus domaines officiels attendus;
- bonus co-presence des termes essentiels dans titre/snippet;
- bonus recence pour actualite;
- diversite de domaines;
- malus dictionnaires/conjugueurs quand le profil n'est pas definitionnel ou linguistique;
- malus homonymes evidents;
- seuil de confiance minimal.

Le crawl doit s'appliquer apres ce reranking, pas avant.

### Lot 5 - Lire les pages avec Crawl4AI selon profil

Conserver:

- `fit` par defaut;
- `raw` seulement pour URL explicite quand `fit` est vide;
- pas de `raw` sur search-only.

Tester:

- `bm25` avec `q` pour les pages longues issues de recherche;
- cache lu/ecrit pour docs stables;
- collecte fraiche pour actualite;
- budgets de caracteres par profil.

### Lot 6 - Politique de confiance et fallback OpenRouter

Apres renforcement local, definir une decision explicite:

- local seul si confiance forte;
- proposer fallback si confiance faible;
- Exa pour haute qualite quand sources officielles/locales manquent;
- Parallel pour fallback compact si le besoin est moins critique;
- OpenRouter web_fetch eventuel pour URL explicite seulement si le lecteur local echoue et que l'utilisateur accepte une dependance externe.

## Ce qu'il ne faut pas faire

Ne pas remplacer tout le web local par Exa. Le benchmark montre un gain qualite, mais aussi un cout plus eleve, plus de tokens et moins de souverainete locale.

Ne pas activer OpenRouter automatiquement partout. Cela contredirait la fermeture volontaire de l'auto-web lexical et rendrait le cout moins previsible.

Ne pas corriger seulement le prompt. La reformulation est un facteur, mais SearXNG renverra toujours du bruit si FridaDev n'a ni profil, ni domaine, ni reranking.

Ne pas desactiver Wikipedia, dictionnaires ou conjugueurs globalement. Ils sont toxiques pour certains profils, utiles pour d'autres.

Ne pas autoriser `raw` pour les resultats search-only. Cela augmenterait les tokens et le bruit. La bonne alternative locale est BM25 ou un meilleur reranking avant crawl.

Ne pas creer un RAG web permanent. Le besoin est une lecture web du tour courant, pas une memoire documentaire globale.

Ne pas rouvrir l'auto-web lexical sans decision explicite.

## Place eventuelle d'OpenRouter Exa/Parallel apres renforcement local

Exa:

- meilleur candidat fallback qualite;
- utile quand le local ne trouve pas de source officielle, quand l'actualite est exigeante ou quand plusieurs sources fiables doivent etre recoupees;
- a reserver aux demandes ou la valeur justifie cout et tokens.

Parallel:

- meilleur candidat fallback compact/economique;
- utile pour une seconde opinion rapide;
- moins fiable sur les sujets academiques ou ambigus d'apres le run live.

Local:

- chemin par defaut a conserver;
- excellent pour URL explicite;
- ameliorable sur recherche ouverte avec les lots ci-dessus;
- plus observable et plus controlable.

Decision cible: OpenRouter doit devenir une soupape de confiance, pas une nouvelle base de souverainete.

## Tests et preuves recommandes pour le futur lot d'implementation

Tests unitaires:

- `search()` transmet les parametres SearXNG attendus par profil;
- les requetes multi-pass restent bornees;
- les domaines officiels sont priorises pour institutionnel/technique;
- dictionnaires/conjugueurs sont downrankes seulement hors profil definitionnel;
- `raw` reste interdit pour search-only;
- `bm25` envoie bien `q` quand choisi;
- cache policy differencie actualite et docs stables;
- les logs ne contiennent ni texte crawle complet ni secret.

Tests d'integration:

- fixtures SearXNG reproduisant les mauvais ordres du benchmark;
- verification que Service Public/ANTS passent avant conjugueurs;
- verification que OpenRouter docs passent avant articles tiers pour profil technique;
- verification que Derrida/OpenEdition/SEP-like passent avant homonymes;
- verification que `read_state` d'URL explicite reste inchangé.

Benchmark:

- conserver les trois bras `local`, `openrouter_exa`, `openrouter_parallel`;
- ajouter un bras `local_profiled` pendant la transition;
- comparer domaines attendus, latence, caracteres injectes, cout estime, score de confiance et raisons de fallback;
- ne lancer OpenRouter que pour campagnes explicites.

Observabilite:

- `search_profile`;
- nombre de requetes;
- parametres SearXNG effectifs;
- top domaines avant/apres rerank;
- raisons de downrank/drop;
- choix Crawl4AI `fit`/`bm25`/`raw`;
- cache mode;
- confiance finale;
- fallback propose ou utilise.

## Sources consultees

Docs internes:

- `AGENTS.md`;
- `app/docs/todo-todo/product/fridadev-final-product-roadmap-todo.md`;
- `app/docs/todo-done/notes/web-reading-truth-todo.md`;
- `app/docs/todo-done/refactors/hermeneutic-suspension-auto-web-todo.md`;
- `app/docs/states/audits/fridadev-model-call-catalog-2026-05-17.md`;
- `app/docs/states/architecture/fridadev-current-runtime-pipeline.md`;
- `benchmark/README.md`;
- `benchmark/web-search/README.md`;
- `benchmark/suites/web_search/`.

Code FridaDev:

- `app/tools/web_search.py`;
- `app/prompts/web_reformulation.txt`;
- `app/tools/web_reformulation_settings.py`;
- `app/core/chat_service.py`;
- `app/core/chat_prompt_context.py`;
- `app/core/web_read_state.py`;
- `app/core/hermeneutic_node/inputs/web_input.py`;
- `app/observability/hermeneutic_node_logger.py`;
- `app/observability/turn_pipeline_read_model.py`;
- `app/observability/turn_observability_checklist.py`;
- `app/tests/test_server_chat_web_runtime_contract.py`;
- `app/tests/unit/web_search/`;
- `app/tests/unit/benchmark/test_web_search_benchmark.py`.

Configuration OVH lue en lecture seule:

- `/opt/platform/docker-compose.yml`;
- `/opt/platform/searxng/settings.yml` via conteneur, car lecture hote refusee;
- `/opt/platform/searxng/limiter.toml` via conteneur, avec valeur sensible non affichee;
- `/opt/platform/crawl4ai/config.yml`;
- `/opt/platform/crawl4ai/api.py`;
- `/opt/platform/crawl4ai/server.py`;
- `/opt/platform/crawl4ai/schemas.py`.

Docs officielles externes:

- SearXNG documentation principale: <https://docs.searxng.org/>;
- SearXNG Search API: <https://docs.searxng.org/dev/search_api.html>;
- SearXNG settings: <https://docs.searxng.org/admin/settings/index.html>;
- SearXNG settings `search`/`server`: <https://docs.searxng.org/admin/settings/settings.html>;
- SearXNG engines: <https://docs.searxng.org/admin/settings/settings_engines.html>;
- SearXNG Hostnames plugin: <https://docs.searxng.org/dev/plugins/hostnames.html>;
- Crawl4AI documentation principale: <https://docs.crawl4ai.com/>;
- Crawl4AI self-hosting / Docker API: <https://docs.crawl4ai.com/core/self-hosting/>;
- Crawl4AI markdown generation: <https://docs.crawl4ai.com/core/markdown-generation/>;
- Crawl4AI fit markdown/content filters: <https://docs.crawl4ai.com/core/fit-markdown/>;
- Crawl4AI cache modes: <https://docs.crawl4ai.com/core/cache-modes/>;
- Crawl4AI v0.8.0 notes Docker API / securite: <https://docs.crawl4ai.com/blog/releases/v0.8.0/>;
- OpenRouter web search, pour comparaison seulement: <https://openrouter.ai/docs/guides/features/server-tools/web-search>;
- OpenRouter web fetch, pour comparaison URL explicite seulement: <https://openrouter.ai/docs/guides/features/server-tools/web-fetch>.
