# Contrat paniers moteurs SearXNG gouvernes

Date: 2026-05-22

Statut: spec Phase 4 du chantier `fridadev-local-web-search-rebuild`.

## Doctrine

Le runtime web FridaDev reste local only:

- SearXNG decouvre les URLs;
- Crawl4AI lit les URLs;
- FridaDev classe, source-first, rerank et observe localement;
- OpenRouter / Exa / Parallel restent hors runtime.

Cette phase ne modifie pas la configuration globale SearXNG. Les paniers sont applicatifs: FridaDev envoie `categories`, `engines`, `language`, `time_range` et `safesearch` par regime quand le comportement profile est actif. Le bras benchmark `local` garde la baseline historique via les flags `enable_profiled_* = False`; le bras `local_profiled` porte les paniers gouvernes.

## Parametres durs et signaux souples

Parametres durs:

- `engines`;
- `categories`;
- `language`;
- `time_range`;
- `safesearch`.

Signaux souples:

- source-first;
- requetes specialisees bornees;
- reranking explicable;
- downrank dictionnaires/conjugueurs/Q&A hors profil;
- diversite minimale.

Les paniers ne sont pas une censure: ils reduisent le bruit initial sans supprimer le besoin de pluralite, de contestabilite et de lecture humaine des sources.

## Paniers applicatifs retenus

| Regime | Categories | Engines | Langue | Time range | Intention |
| --- | --- | --- | --- | --- | --- |
| `explicit_url` | historique | historique | `fr-FR` | aucun | Ne pas toucher au chemin lecture directe Crawl4AI. |
| `documentation_officielle` | `general,it` | `microsoft learn`, `mdn`, `docker hub`, `bing`, `brave`, `mojeek` | `all` | aucun | Favoriser docs officielles et moteurs techniques sans remplacer source-first. |
| `administratif_francais` | `general` | `bing`, `brave` | `fr-FR` | aucun | Garder `site:` vers sources institutionnelles dans les requetes, avec moteurs generalistes compatibles. |
| `academique` | `general,science` | `arxiv`, `openairepublications`, `pubmed`, `bing`, `brave` | `all` | aucun | Couvrir sciences, medical et web academique large sans sous-profils prematurement. |
| `actualite` | `general,news` | `bing news`, `reuters`, `bing`, `duckduckgo news` | `fr-FR` | `year` | Mixer news et general pour ne pas exclure les sources institutionnelles recentes. |
| `general_divers` | `general` | `bing`, `brave`, `mojeek` | `fr-FR` | aucun | Panier pluraliste sobre, sans hard-request Wikipedia/dictionnaires. |

## Statut Mojeek

Sondage lecture seule effectue sous discipline Sauron via `/config` et `/search` locaux, sans modification plateforme.

Constats:

- `/config` expose `mojeek`, `mojeek images`, `mojeek news`, tous globalement desactives.
- `engines=mojeek` repond sur des sondes bornees.
- `!mjk` repond parfois mais peut retourner `acces refuse`.
- Mojeek est bon comme appoint `general_divers` et candidat secondaire `documentation_officielle`.
- Mojeek n'est pas retenu pour `actualite`: les resultats observes etaient bruites ou hors axe.
- Mojeek n'est pas retenu pour `administratif_francais` ni `academique` en V1 faute de preuve suffisante.

Conclusion: Mojeek est retenu comme moteur secondaire dans les paniers `documentation_officielle` et `general_divers`, mais pas comme moteur souverain.

Artefact local non versionne de sonde: `/tmp/fridadev-mojeek-probe-phase4/mojeek-probe.md`.

## Moteurs evites ou declasses

- Google: acces refuse / 403.
- Google Scholar: acces refuse / unusual traffic.
- Startpage: CAPTCHA.
- DuckDuckGo web: CAPTCHA observe; non retenu comme pilier general.
- Brave News: non retenu tant que le risque 429 reste documente.
- Semantic Scholar: instable / erreur JSON tant que non revalide.
- Qwant News: bruit fort, non retenu en V1.
- Wikipedia / Wikidata / Wiktionary: appoints possibles, mais pas hard-request dans les paniers specialises.
- Q&A techniques: visibles si la recherche les remonte, mais pas autorite documentaire premiere hors demande explicite.

## Observabilite

Les champs content-free attendus:

- `searxng_profile_params_kind`;
- `searxng_profile_params_policy`;
- `searxng_categories`;
- `searxng_engines`;
- `searxng_time_range`;
- `searxng_language`;
- `searxng_safesearch`;
- `searxng_params_reason_codes`;
- `searxng_hard_parameters`;
- `searxng_soft_signal_policy`.

Ne jamais logger: requete brute si le contrat local l'evite, prompt, contenu crawle, secret, token, cookie, HTML ou base64.

## Frontiere plateforme

Non fait en Phase 4 applicative:

- pas de modification `/opt/platform/searxng/settings.yml`;
- pas de `remove` / `keep_only`;
- pas de restart SearXNG;
- pas de modification Docker/Caddy/Authelia;
- pas de moteur externe tokenise;
- pas de fallback OpenRouter / Exa / Parallel.

Toute reconfiguration globale SearXNG reste un lot Sauron separe, avec GO utilisateur explicite, config actuelle, config cible, diff attendu, risques, rollback, backup et fenetre de restart.
