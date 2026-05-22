# FridaDev web search - decision OpenRouter/Exa discovery - 2026-05-22

Statut: decision produit active.

## Decision

FridaDev devient **local-first + OpenRouter/Exa pour la decouverte web ouverte**.

Le diagnostic Phase 8 est acte:

- Crawl4AI lit correctement quand l'URL est bonne;
- les contrats de preuve, confiance, source-first, reranking et observabilite restent utiles;
- le probleme central est la decouverte et le ranking des URLs;
- SearXNG local reste trop fragile pour porter seul la recherche ouverte dans son etat courant;
- FridaDev ne doit plus compenser un mauvais panier de decouverte par de la couture heuristique cas par cas.

## Doctrine runtime

- `explicit_url`: reste local direct, prioritaire et inchangé.
- Documents fournis, workspace et OCR: inchanges.
- Recherche ouverte: OpenRouter `openrouter:web_search` avec `engine=exa` devient provider prioritaire quand `WEB_SEARCH_DISCOVERY_PROVIDER=openrouter_exa`.
- Lecture/crawl: Crawl4AI reste la couche locale de lecture.
- Qualification: FridaDev garde source-first, reranking, evidence, confiance visible et observabilite content-free.
- SearXNG: reste disponible via `WEB_SEARCH_DISCOVERY_PROVIDER=local`, comme baseline historique, fallback operateur explicite et objet d'audit plateforme.
- Parallel: reste temoin benchmark externe, pas provider runtime.

Exa cherche des URLs. FridaDev lit, contextualise, qualifie, signale l'incertitude et reste responsable de ce qui est injecte au modele.

## Configuration

Variables ajoutees:

- `WEB_SEARCH_DISCOVERY_PROVIDER=local|openrouter_exa`
- `WEB_SEARCH_DISCOVERY_MODEL`
- `WEB_SEARCH_DISCOVERY_TIMEOUT_S`
- `WEB_SEARCH_DISCOVERY_SEARCH_CONTEXT_SIZE`
- `WEB_SEARCH_DISCOVERY_MAX_RESULTS`
- `WEB_SEARCH_DISCOVERY_MAX_TOTAL_RESULTS`
- `OPENROUTER_REFERER_WEB_DISCOVERY`
- `OPENROUTER_TITLE_WEB_DISCOVERY`

Le defaut applicatif est `openrouter_exa`, conformement a la decision produit. Le bras benchmark `local` force explicitement `local` pour conserver la baseline SearXNG historique.

Le secret OpenRouter n'est pas duplique: le provider de decouverte utilise le transport partage `main_model.api_key` via les helpers OpenRouter existants. Si `openrouter_exa` est choisi sans configuration OpenRouter valide, le systeme doit echouer proprement avec un signal observable, sans fuite de secret.

Point cout/latence: le plan de recherche borne reste applique avant la decouverte. En mode `openrouter_exa`, chaque requete du plan peut produire un appel OpenRouter distinct. Le comportement courant est donc borne par le contrat existant: requete principale + 0 a 2 requetes secondaires, soit au plus 3 appels de decouverte externe par tour web manuel. `query_count`, `secondary_query_count` et les metriques `provider_caller=web_discovery` doivent rendre ce cout visible avant tout test live.

## Observabilite

Champs content-free attendus:

- `web_discovery_provider`
- `web_discovery_provider_requested`
- `web_discovery_provider_effective`
- `web_discovery_external_used`
- `web_discovery_external_provider`
- `web_discovery_external_error_kind`
- `web_discovery_reason_codes`

Ces champs doivent rester distincts de `openrouter_fallback_*`: Exa n'est pas un fallback automatique, c'est un provider de decouverte configure.

## Sources officielles consultees

- OpenRouter, server tools web search: `https://openrouter.ai/docs/guides/features/server-tools/web-search`

La documentation officielle decrit le server tool `openrouter:web_search`, les moteurs supportes dont Exa, et les parametres `max_results`, `max_total_results` et `search_context_size`.

## Limites

- La parite de requete exacte avec OpenRouter reste limitee: l'appel passe par un modele et un server tool, pas par une API Exa directe.
- La confiance web reste non souveraine et ne declenche aucun fallback.
- Les resultats Exa doivent encore etre lus par Crawl4AI: une URL pertinente ne garantit pas que le passage utile soit extrait.
- Une validation live bornee reste necessaire avant de traiter Phase 9 comme cloturee.
