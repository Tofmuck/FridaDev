# FridaDev web search Phase 9 final validation - 2026-05-22

Statut: validation finale Phase 9 livree apres calibration confiance/evidence, rebuild applicatif et smoke live borne.

Doctrine validee: web manuel seulement; `explicit_url` reste local direct; la recherche ouverte utilise OpenRouter/Exa discovery quand configure; Crawl4AI lit les URLs; FridaDev conserve source-first, reranking, evidence, confiance et observabilite; SearXNG reste provider `local` / baseline / rollback operateur explicite; Parallel reste benchmark externe.

Artefacts temporaires a lire:

- `/tmp/fridadev-web-search-phase9-final-validation/phase9-final.json`
- `/tmp/fridadev-web-search-phase9-final-validation/phase9-final.md`

## Methode

Le smoke a ete lance dans le conteneur applicatif `platform-fridadev`, avec le provider runtime configure en `openrouter_exa`.

Les cas web manuel ont appele la brique runtime `tools.web_search.build_context_payload()` avec le transport OpenRouter applicatif. Le controle web desactive a appele `resolve_web_runtime_payload(web_search_on=False)`.

Le proxy de mesure n'a conserve que des signaux content-free ou des metadonnees de source:

- `web_discovery_provider_effective`;
- `web_discovery_external_used`;
- `query_count`;
- `secondary_query_count`;
- nombre d'appels `provider_caller=web_discovery`;
- evidence / confidence;
- domaines et URLs top;
- latence approximative;
- cout OpenRouter observe quand le provider le renvoie.

Aucune cle, header sensible, cookie, fichier environnement, DSN, data URL, base64 ou contenu crawle complet n'a ete ecrit.

## Patch confiance/evidence

Finding valide: avant correction, `web_confidence_level=high` pouvait survivre quand une source tentee par Crawl4AI echouait mais etait tout de meme injectee sous forme de snippet. Cela creait une fausse solidite documentaire pour les pages ou PDF importants non lus.

Correction livree:

- ajout de `crawl_failed_used_source_count` dans les resumes confiance/evidence;
- ajout des reason codes `crawl_failed_prompt_material_used` et `crawl_partial_failure_limits_confidence`;
- plafonnement a `medium` quand un echec Crawl4AI fournit quand meme du materiau de prompt;
- evidence `partial` + caveat dans ce cas;
- aucun changement de fallback externe, aucun declenchement OpenRouter/Exa/Parallel par la confiance.

Le contre-cas reste autorise: une erreur Crawl4AI non utilisee dans le prompt reste observable via `crawl_empty_or_error_present`, mais ne baisse pas automatiquement une confiance haute si d'autres sources fortes sont effectivement lues.

## Resultats synthetiques

| Cas | Provider effectif | Appels `web_discovery` | Evidence | Caveat | Confiance | Latence | Cout observe | Domaines principaux |
| --- | --- | ---: | --- | ---: | --- | ---: | ---: | --- |
| web off | n/a | 0 | n/a | false | n/a | 0 ms | n/a | n/a |
| URL explicite OpenRouter docs | `local` | 0 | `sufficient` | false | `high` | 1704 ms | n/a | `openrouter.ai` |
| Adobe Photoshop docs | `openrouter_exa` | 3 | `partial` | true | `medium` | 19806 ms | 0.029748 USD | `developer.adobe.com`, `helpx.adobe.com`, `adobe.com` |
| Adobe Illustrator docs | `openrouter_exa` | 3 | `partial` | true | `medium` | 19093 ms | 0.031741 USD | `developer.adobe.com`, `adobe.com`, `helpx.adobe.com` |
| Renouvellement CNI | `openrouter_exa` | 3 | `partial` | true | `medium` | 20902 ms | 0.036457 USD | `service-public.fr`, `service-public.gouv.fr`, `ants.gouv.fr` |
| Actualite institutionnelle IA Europe | `openrouter_exa` | 3 | `sufficient` | false | `high` | 20726 ms | 0.041869 USD | `ec.europa.eu`, `digital-strategy.ec.europa.eu`, `data.consilium.europa.eu`, `europarl.europa.eu` |
| OpenRouter docs | `openrouter_exa` | 3 | `partial` | true | `medium` | 20761 ms | 0.035416 USD | `openrouter.ai` |
| Bourdieu / sociologie | `openrouter_exa` | 3 | `partial` | true | `medium` | 23595 ms | 0.042905 USD | `persee.fr`, `openedition.org`, `stanford.edu` |
| CRISPR / PubMed | `openrouter_exa` | 3 | `partial` | true | `medium` | 32189 ms | 0.046710 USD | `medecinesciences.org`, `hal.umontpellier.fr`, `ncbi.nlm.nih.gov` |

Total observe sur les couts OpenRouter retournes par le provider: environ `0.264846` USD pour 21 appels `web_discovery`.

Note: les recherches ouvertes ont aussi observe un appel `web_reformulation` par cas. Ce cout est distinct du compteur `provider_caller=web_discovery` et doit rester visible dans les logs provider.

## Lecture par cas

### Web desactive

- `status=skipped`;
- `reason_code=not_applicable`;
- aucun appel provider.

Conclusion: le bouton web reste le declencheur. La decision Exa ne reactive pas l'auto-web.

### URL explicite OpenRouter docs

- `collection_path=explicit_url_direct`;
- `search_profile=explicit_url`;
- `read_state=page_read`;
- provider effectif `local`;
- aucun appel `web_discovery`.

Conclusion: une URL explicite force toujours la lecture locale directe. Exa n'est pas appele.

### Adobe Photoshop / Illustrator

Exa trouve les domaines attendus Adobe: `developer.adobe.com`, `helpx.adobe.com`, `adobe.com`.

Les cas sont `partial` / `medium` car au moins une source tentee par Crawl4AI est vide et son snippet reste injecte. Ce n'est pas un echec produit: Frida peut repondre, mais doit signaler la lecture partielle.

### Renouvellement CNI

Exa trouve `service-public.fr`, `service-public.gouv.fr` et `passeport.ants.gouv.fr`.

Le statut est `partial` / `medium` parce que la page principale Service Public renvoie un crawl vide dans ce run, puis une autre source Service Public est lue. Frida peut repondre avec prudence, sans pretendre que toutes les pages officielles ont ete lues.

### Actualite institutionnelle IA Europe

Exa trouve deux sources europeennes lues avec succes et des sources supplementaires institutionnelles non crawlees car hors budget. Dans ce run, aucune erreur Crawl4AI n'est presente sur les sources tentees; la confiance `high` est donc acceptable.

### OpenRouter docs

Exa trouve `openrouter.ai`, avec une source lue et plusieurs sources snippet. Le statut `partial` / `medium` est volontaire: le systeme ne doit pas traiter une documentation partiellement lue comme preuve exhaustive.

### Bourdieu / sociologie

Exa trouve des sources SHS pertinentes: `persee.fr`, `openedition.org`, PDF Stanford. Le statut `partial` / `medium` vient d'un PDF ou d'une source non lue injectee sous forme de snippet.

### CRISPR / PubMed

Exa trouve des sources scientifiques, dont `medecinesciences.org`, HAL et PMC. La latence observee depasse la cible normale de 20 a 25 secondes, et le statut reste `partial` / `medium`.

## Rollback operateur

Rollback applicatif de decouverte ouverte:

1. revenir a `WEB_SEARCH_DISCOVERY_PROVIDER=local` dans l'environnement applicatif;
2. redeployer uniquement l'app FridaDev si la variable runtime est modifiee;
3. verifier que `explicit_url` reste inchange: lecture locale directe;
4. verifier qu'une recherche ouverte utilise de nouveau SearXNG comme provider local;
5. garder en tete les limites connues de SearXNG documentees par les Phases 0 a 8.

Ce rollback ne demande pas de modification SearXNG globale, Caddy, Authelia, DB ou Crawl4AI. Ne jamais afficher de fichier environnement ni secret pendant l'operation.

## Decision Phase 9

Phase 9 est cloturable.

Raisons:

- le provider effectif est lisible;
- web desactive, URL explicite et recherche ouverte sont valides;
- le corpus final borne est passe;
- les couts, latences, query counts et appels `provider_caller=web_discovery` sont mesures;
- le finding confiance est corrige;
- le rollback operateur est documente.

Limites connues non bloquantes:

- Crawl4AI reste fragile sur certaines pages institutionnelles/PDF;
- plusieurs cas doivent etre repondus avec caveat, ce qui est conforme au contrat Phase 7;
- la latence CRISPR/PubMed depasse la cible normale et appelle un futur reglage de budget/crawl si ce cas devient frequent;
- Exa reste un provider externe de decouverte et doit rester observable, pas naturalise comme verite.

## Securite

Grep securite effectue sur `/tmp/fridadev-web-search-phase9-final-validation` et les notes Phase 9:

- aucune cle OpenRouter;
- aucun prefixe de cle;
- aucun token porteur;
- aucun parametre de cle;
- aucun header d'autorisation;
- aucun cookie;
- aucune data URL ou base64.
