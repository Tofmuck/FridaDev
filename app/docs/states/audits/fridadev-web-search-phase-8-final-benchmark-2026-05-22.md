# FridaDev web search Phase 8 final benchmark - 2026-05-22

Statut: Phase 8 livree comme preuve benchmark locale, sans modification runtime ni plateforme.

Perimetre: comparaison finale entre l'ancien local historique et le nouveau local profile reconstruit par les Phases 2 a 7. OpenRouter, Exa et Parallel n'ont pas ete relances dans cette Phase 8; ils restent des temoins externes des benchmarks precedents, jamais une strategie runtime.

## Artefacts

Artefacts live locaux:

- `/tmp/fridadev-web-search-phase8-final/local.md`
- `/tmp/fridadev-web-search-phase8-final/local-profiled.md`
- `/tmp/fridadev-web-search-phase8-final/comparison.md`
- `/tmp/fridadev-web-search-phase8-final/phase8-final.json`
- `/tmp/fridadev-web-search-phase8-final/phase8-final.md`
- `/tmp/fridadev-web-search-phase8-final/phase8-final.jsonl`

Dry-run runner historique:

- `/tmp/fridadev-web-search-phase8-final-dry-run/dry-run-web-search-phase8-final.json`
- `/tmp/fridadev-web-search-phase8-final-dry-run/dry-run-web-search-phase8-final.md`

Limite methodologique: le runner versionne standard garde volontairement les 5 cas historiques. Le corpus Phase 8 borne a donc ete execute par un mini-run benchmark-only dans le conteneur applicatif, en appelant directement `tools.web_search.build_context_payload` avec les memes flags que les bras `local` et `local_profiled`. Aucun fichier runtime, SearXNG, Crawl4AI ou Docker n'a ete modifie.

## Corpus

Le corpus Phase 8 contient 12 cas, dans la limite du corpus borne valide:

- documentation officielle Adobe Photoshop;
- documentation officielle Adobe Illustrator;
- renouvellement CNI;
- Education nationale / obligation administrative;
- actualite IA Europe recente;
- Bourdieu / sociologie;
- CRISPR / PubMed;
- documentation officielle Microsoft Graph API;
- documentation officielle OpenRouter web search;
- Derrida / trace;
- Jaguar ambigu;
- URL explicite / lecture directe.

## Resume executif

`local_profiled` n'est pas pret a etre traite comme victoire globale.

Gains nets:

- le chemin URL explicite reste stable et sain: `read_state=page_read`;
- CNI est mieux ordonne: ANTS puis Service Public passent devant les dictionnaires;
- Microsoft Graph atteint `learn.microsoft.com`, alors que le local historique ne produit pas de donnees;
- OpenRouter docs reste stable avec `openrouter.ai` en tete;
- Jaguar ambigu est legerement mieux equilibre, avec Wikipedia avant les domaines automobile.

Pertes ou echecs restants:

- Adobe Illustrator echoue fortement: MDN Flash, Docker Hub et SuperUser remplacent les domaines Adobe attendus;
- actualite IA Europe est hors sujet dans les deux bras, et `local_profiled` produit du bruit Google Help / OBS / Zhihu / Baidu avec confiance haute;
- Bourdieu / sociologie reste casse par homonymie `Pierre` / mineraux;
- CRISPR / PubMed ne trouve pas PubMed et garde une confiance haute sur un panier faible;
- Derrida / trace reste hors sujet;
- Education nationale passe d'un contresens finance en local a `no_results` en profile, ce qui est plus honnete mais pas suffisant.

## Resultats par cas

| Cas | Local historique | Local profile | Lecture |
| --- | --- | --- | --- |
| Adobe Photoshop | Trouve `helpx.adobe.com`, mais derriere Wikipedia, SEO et dictionnaires. | Remonte `adobe.com`, mais page Adobe generique et bruit Docker Hub. | Leger mieux domaine, insuffisant. |
| Adobe Illustrator | Wikipedia / SEO / dictionnaires / Google Docs. | MDN Flash, Docker Hub, SuperUser; Adobe absent. | Regression. |
| CNI | Service Public et ANTS presents, mais Larousse premier. | ANTS puis Service Public premiers; evidence partielle par snippets/crawl pauvre. | Gain net, crawl a ameliorer. |
| Education nationale | Contresens sur obligation financiere. | `no_results`, evidence insuffisante. | Echec, mais plus honnete. |
| Actualite IA Europe | BILD domine. | Google Help / OBS / Zhihu / Baidu dominent; confiance haute. | Regression et probleme de confiance. |
| Bourdieu / sociologie | Pierres/mineraux et Pierre apotre. | Pierres/mineraux encore en tete; confiance haute. | Echec academique SHS. |
| CRISPR / PubMed | Wikipedia, SEO/science vulgarisee, un domaine NIH. | Similaire, sans PubMed, confiance haute. | Echec academique sciences/medical. |
| Microsoft Graph | `no_data`. | `learn.microsoft.com` premier. | Gain fort source-first. |
| OpenRouter docs | `openrouter.ai` premier puis GitHub/tutoriels. | `openrouter.ai` premier, mais bruit docs secondaires. | Stable / petit gain. |
| Derrida / trace | BalkanDownload. | ESL, forums seniors, Zhihu/Baidu. | Echec academique. |
| Jaguar ambigu | Jaguar automobile + Wikipedia. | Wikipedia puis Jaguar automobile. | Leger gain pluraliste. |
| URL explicite | Lecture directe OpenRouter, `page_read`. | Identique. | Stable, a ne pas rouvrir. |

## Latence

La latence reste compatible avec la cible web manuel 20-25 secondes. Le cas le plus lent observe est Bourdieu `local_profiled` a environ 16,5 secondes. Le chemin URL explicite reste sous 2 secondes.

La qualite documentaire, pas la latence, bloque la cloture.

## Diagnostic

La reconstruction locale a apporte des briques utiles: profil, source-first, paniers applicatifs, reranking, politique crawl, evidence et confiance observables. Mais le run final montre que ces briques ne suffisent pas quand le panier SearXNG ou les requetes specialisees partent dans un mauvais espace documentaire.

Causes probables:

- certains paniers moteurs profilés introduisent du bruit inattendu, notamment documentation officielle et actualite;
- la generation de requetes specialisees ne resout pas encore les homonymies fortes;
- le source-first Adobe reste trop faible pour imposer `helpx.adobe.com` / `developer.adobe.com` quand SearXNG ramene Docker/MDN;
- la confiance locale valorise encore trop le volume de materiau lu au lieu de l'alignement avec les domaines attendus et les termes essentiels;
- l'evidence Phase 7 sait parfois dire `insufficient`, mais pas encore assez souvent quand les domaines visibles sont manifestement hors sujet.

## Decision recommandee

Ne pas clore Phase 9 comme deploiement final sans correctif.

Garder la doctrine runtime:

- FridaDev web runtime = local only;
- aucun fallback OpenRouter / Exa / Parallel;
- aucun hybride runtime;
- Exa/Parallel restent des temoins externes de benchmark seulement.

Avant cloture Phase 9, ouvrir un correctif borne:

1. recalibrer la confiance pour qu'un panier hors domaines attendus ne puisse pas rester `high`;
2. corriger le panier/requetes `actualite`;
3. corriger le profil academique SHS/sciences face aux homonymies;
4. renforcer source-first Adobe sans creer de whitelist souveraine;
5. relancer un sous-benchmark Phase 8 reduit: Adobe Illustrator, actualite IA Europe, Bourdieu, CRISPR/PubMed, Derrida/trace, URL explicite controle.

## Ce qui n'a pas ete active

- pas de fallback OpenRouter;
- pas d'appel Exa / Parallel dans le runtime;
- pas d'auto-web;
- pas de modification SearXNG globale;
- pas de modification Crawl4AI globale;
- pas de rebuild applicatif;
- pas de changement Memory / Identity / Summary / Biblio / RAG.

## Conclusion Phase 8

Phase 8 est livree comme benchmark et diagnostic. Elle ne valide pas encore la cloture produit de la reconstruction locale.

Le nouveau local est meilleur sur certains cas d'autorite explicite et sur l'observabilite, mais il reste trop fragile sur actualite, academique et Adobe. Le prochain geste doit etre un correctif local de qualite et de confiance, pas une hybridation externe.
