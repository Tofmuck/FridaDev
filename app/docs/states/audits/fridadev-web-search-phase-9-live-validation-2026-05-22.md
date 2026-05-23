# FridaDev web search Phase 9 live validation - 2026-05-22

Statut: validation live bornee, sans changement code, settings, SearXNG, Crawl4AI, Docker ni rebuild.

Doctrine validee: web manuel seulement, `explicit_url` local direct, recherche ouverte via OpenRouter/Exa discovery quand configure, lecture Crawl4AI locale, evidence/confiance/reranking/observabilite FridaDev, aucun fallback automatique.

Artefacts temporaires a lire:

- `/tmp/fridadev-web-search-phase9-live-validation/phase9-live.json`
- `/tmp/fridadev-web-search-phase9-live-validation/phase9-live.md`

## Methode

Le smoke a ete lance dans le conteneur applicatif `platform-fridadev`, avec le runtime courant et `WEB_SEARCH_DISCOVERY_PROVIDER=openrouter_exa`.

Les cas web manuel ont appele la brique runtime `tools.web_search.build_context_payload()` avec le transport OpenRouter applicatif. Le controle web desactive a appele `resolve_web_runtime_payload(web_search_on=False)`.

Le proxy de mesure n'a conserve que des signaux content-free:

- `web_discovery_provider_effective`;
- `web_discovery_external_used`;
- `query_count`;
- `secondary_query_count`;
- nombre d'appels `provider_caller=web_discovery`;
- evidence / confidence;
- domaines et URLs top;
- latence approximative;
- cout OpenRouter observe quand le provider le renvoie.

Aucune cle, header sensible, temoin de session, fichier environnement, DSN ou contenu crawle complet n'a ete ecrit.

## Resultats synthetiques

| Cas | Provider effectif | Externe | Query count | Appels `web_discovery` | Evidence | Confiance | Latence | Domaines principaux |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: | --- |
| web off | n/a | false | 0 | 0 | n/a | n/a | 0 ms | n/a |
| URL explicite OpenRouter docs | `local` | false | 0 | 0 | `sufficient` | `high` | 1555 ms | `openrouter.ai` |
| Adobe Photoshop docs | `openrouter_exa` | true | 3 | 3 | `sufficient` | `high` | 18067 ms | `developer.adobe.com`, `helpx.adobe.com`, `adobe.com` |
| Renouvellement CNI | `openrouter_exa` | true | 3 | 3 | `sufficient` | `high` | 16392 ms | `service-public.fr`, `ants.gouv.fr`, `service-public.gouv.fr` |
| Actualite institutionnelle IA Europe | `openrouter_exa` | true | 3 | 3 | `sufficient` | `high` | 21838 ms | `europarl.europa.eu`, `ai-act-service-desk.ec.europa.eu`, `data.consilium.europa.eu` |

## Lecture par cas

### Web desactive

- `status=skipped`;
- `reason_code=not_applicable`;
- `query_count=0`;
- `provider_call_counts={}`;
- aucun appel `web_discovery`.

Conclusion: le bouton web reste le declencheur. La decision Exa ne reactive pas l'auto-web.

### URL explicite OpenRouter docs

- `collection_path=explicit_url_direct`;
- `search_profile=explicit_url`;
- `read_state=page_read`;
- `primary_read_status=success`;
- `web_discovery_provider_requested=openrouter_exa`;
- `web_discovery_provider_effective=local`;
- `web_discovery_external_used=false`;
- `provider_caller_web_discovery_calls=0`.

Conclusion: une URL explicite force toujours le chemin local direct. Exa n'est pas appele.

### Adobe Photoshop docs

Top URLs observees:

- `https://developer.adobe.com/photoshop/`;
- `https://helpx.adobe.com/photoshop/desktop/get-started/learn-the-basics/adobe-photoshop-on-desktop-faq.html`;
- `https://helpx.adobe.com/ca_fr/photoshop/desktop.html`;
- `https://www.adobe.com/products/photoshop/how-to-use.html`;
- `https://helpx.adobe.com/photoshop/desktop.html`.

Signaux:

- `web_discovery_provider_effective=openrouter_exa`;
- `web_discovery_external_used=true`;
- `query_count=3`;
- `secondary_query_count=2`;
- `provider_caller_web_discovery_calls=3`;
- cout observe sur les appels discovery: `0.0323275` USD;
- `crawl4ai_policy_kinds=['profile_query_aware_bm25_with_fit_fallback']`;
- evidence `sufficient`, confiance `high`.

Conclusion: Exa trouve un panier Adobe beaucoup plus conforme que les echecs SearXNG Phase 8.

### Renouvellement CNI

Top URLs observees:

- `https://www.service-public.fr/particuliers/vosdroits/F21089`;
- `https://passeport.ants.gouv.fr/toute-l-actualite/renouvellement-de-vos-titres-d-identite-pensez-a-anticiper`;
- `https://www.service-public.gouv.fr/particuliers/vosdroits/F21089`;
- `https://www.service-public.fr/particuliers/vosdroits/R62483`;
- `https://sites.service-information-publique.fr/vias/guide-particuliers/F21089.html`.

Signaux:

- `web_discovery_provider_effective=openrouter_exa`;
- `query_count=3`;
- `provider_caller_web_discovery_calls=3`;
- cout observe sur les appels discovery: `0.030591` USD;
- evidence `sufficient`, confiance `high`.

Conclusion: Exa discovery retrouve les sources administratives attendues, puis FridaDev garde la lecture/reranking/evidence locale.

### Actualite institutionnelle IA Europe

Top URLs observees:

- `https://www.europarl.europa.eu/news/fr/press-room/20260427IPR42011/ia-mesures-de-simplification-et-interdiction-des-applications-de-deshabillage`;
- `https://ai-act-service-desk.ec.europa.eu/fr/faq`;
- `https://data.consilium.europa.eu/doc/document/ST-9247-2026-INIT/en/pdf`;
- `https://www.europarl.europa.eu/news/en/press-room/20260427IPR42011/ai-act-deal-on-simplification-measures-ban-on-nudifier-apps`;
- `https://ai-act-service-desk.ec.europa.eu/en/ai-act/timeline/timeline-implementation-eu-ai-act`.

Signaux:

- `web_discovery_provider_effective=openrouter_exa`;
- `query_count=3`;
- `provider_caller_web_discovery_calls=3`;
- cout observe sur les appels discovery: `0.04451625` USD;
- `crawl4ai_policy_kinds=['profile_fit_fresh']`;
- une erreur Crawl4AI 500 est apparue sur une page Parlement europeen pendant le run;
- reason code present: `crawl_empty_or_error_present`;
- evidence `sufficient`, confiance `high` dans ce run.

Conclusion: Exa trouve des URLs institutionnelles nettement meilleures que SearXNG Phase 8. La limite Crawl4AI demeure: certaines pages/PDF institutionnelles restent fragiles. Dans ce run, la confiance n'a pas baisse malgre le signal `crawl_empty_or_error_present`; la calibration confiance/Crawl4AI reste donc a surveiller et ne doit pas etre traitee comme cloturee par cette validation.

## Cases Phase 9 validees

- [x] Web desactive = aucun appel web.
- [x] URL explicite = lecture locale directe, Exa non appele.
- [x] Recherche ouverte = Exa discovery puis Crawl4AI local.
- [x] `query_count`, `secondary_query_count` et `provider_caller=web_discovery` observes.
- [x] Cout et latence observes sur corpus borne.
- [x] Adobe Photoshop, CNI, actualite institutionnelle Europe et URL explicite OpenRouter docs verifies.

## Cases Phase 9 encore ouvertes

- [ ] Verification complete du corpus Phase 9: Adobe Illustrator et cas academique non relances dans ce micro-smoke.
- [ ] Decision operateur sur variable runtime OVH si le defaut doit etre force cote plateforme.
- [ ] Limites Crawl4AI PDF/pages institutionnelles a documenter plus finement.
- [ ] Calibration confiance quand `crawl_empty_or_error_present` coexiste avec des sources institutionnelles pertinentes.
- [ ] Rapport final de cloture Phase 9 et archivage du TODO actif.

## Securite

Grep securite sur `/tmp/fridadev-web-search-phase9-live-validation`:

- aucune cle OpenRouter;
- aucun prefixe de cle;
- aucun jeton porteur;
- aucun parametre de cle;
- aucun header sensible;
- aucune data URL ou base64.
