# Contrat parametres FridaDev par profil web local

Date: 2026-05-22

Statut: spec Phase 5 du chantier `fridadev-local-web-search-rebuild`.

## Doctrine

Le runtime web FridaDev reste local only:

- SearXNG decouvre les URLs;
- Crawl4AI lit les URLs;
- FridaDev classe, source-first, rerank, ajuste les budgets et observe localement;
- OpenRouter / Exa / Parallel restent hors runtime.

La Phase 5 ne modifie pas SearXNG global. Elle ajoute une politique applicative par profil au-dessus des paniers Phase 4: domaines attendus, domaines secondaires, domaines a declasser, budgets Crawl4AI, cible de latence et signal d'insuffisance de preuve.

## Parametres durs, signaux souples, decisions humaines

Parametres durs deja portes par Phase 4:

- `categories`;
- `engines`;
- `language`;
- `time_range`;
- `safesearch`.

Signaux souples Phase 5:

- `profile_expected_domains`;
- `profile_secondary_domains`;
- `profile_downrank_domains`;
- `profile_situated_secondary_domains`;
- budgets `profile_crawl_top_n_budget` et `profile_crawl_max_chars_budget`;
- `profile_insufficient_evidence` et reason codes.

Decisions humaines integrees:

- documentation officielle: source-first strict quand une autorite est nommee; ouverte assistee si autorite inconnue ou floue;
- administratif francais: sources officielles d'abord, sources syndicales SUD/CGT comme contrepoints situes;
- academique: profil large, sans sous-profils prematurement;
- actualite: Reuters utile mais jamais source unique, sources institutionnelles prioritaires pour actualite institutionnelle;
- latence web manuel normal ciblee autour de 20 a 25 secondes.

## Politiques par profil

| Profil | Mode | Domaines attendus | Secondaires | Declasses | Budget crawl | Latence cible |
| --- | --- | --- | --- | --- | --- | --- |
| `explicit_url` | lecture directe prioritaire | URL utilisateur | fallback search seulement si chemin existant | aucun nouveau declassement | fallback search 2 resultats / 5000 chars | 25s |
| `documentation_officielle` | source-first strict si autorite nommee, ouverte assistee sinon | domaines source-first probables: Adobe, Microsoft Learn, Stripe, OpenRouter, MDN, Docker | docs techniques reconnues | Q&A, GitHub, blogs, tutoriels tiers, dictionnaires/conjugueurs | 3 resultats / 7000 chars | 25s |
| `administratif_francais` | officiel francais d'abord avec contrepoints situes | `service-public.fr`, `ants.gouv.fr`, `legifrance.gouv.fr`, `.gouv.fr`, `education.gouv.fr`, `eduscol.education.fr`, `enseignementsup-recherche.gouv.fr`, `onisep.fr`, `ac-*.fr` | SUD, CGT, Solidaires comme sources situees | dictionnaires/conjugueurs hors demande definitionnelle | 3 resultats / 6500 chars | 25s |
| `academique` | academique large ouvert | arXiv, OpenAIRE, PubMed, HAL, OpenEdition, Cairn, Persee, DOI | Stanford Encyclopedia, JSTOR, universites | dictionnaires, encyclopedies generalistes, blogs, presse generaliste hors appoint | 3 resultats / 8000 chars | 25s |
| `actualite` | fraicheur + institutionnel, jamais source unique | Reuters, domaines institutionnels et UE selon sujet | news bornees | contenus anciens, encyclopedies, dictionnaires | 2 resultats / 4500 chars | 20s |
| `general_divers` | pluraliste sobre | aucun domaine souverain | Wikipedia/Wikidata comme appoint, Mojeek candidat secondaire | aucun ban general | 2 resultats / 5000 chars | 20s |

## Education nationale et syndicats

Pour `administratif_francais`, les sources Education nationale suivantes sont attendues quand le sujet les appelle:

- `education.gouv.fr`;
- `eduscol.education.fr`;
- `enseignementsup-recherche.gouv.fr`;
- `onisep.fr`;
- `ac-*.fr` avec prudence.

SUD, CGT et Solidaires sont visibles comme sources secondaires situees. Elles peuvent aider pour conflit social, conditions de travail, lecture syndicale ou critique institutionnelle. Elles ne sont jamais preuve administrative souveraine et ne doivent pas passer devant les textes officiels quand la question porte sur une regle, une procedure ou un droit positif.

## Preuve insuffisante

La Phase 5 produit un signal, pas une reponse scriptee:

- `profile_insufficient_evidence`;
- `profile_insufficient_evidence_reason_codes`;
- `profile_expected_material_used`;
- `profile_situated_material_used`;
- `profile_source_domain_counts`.

Le signal peut indiquer par exemple:

- aucun materiau injecte;
- source attendue non utilisee;
- source syndicale situee sans source officielle;
- materiau seulement snippet.

Ce signal peut aider le LLM a formuler naturellement une prudence ou une proposition de reformulation. Il ne declenche aucun fallback externe, ne supprime aucune source et ne remplace pas la reponse finale.

## Observabilite

Champs content-free attendus:

- `profile_policy_kind`;
- `profile_policy_mode`;
- `profile_expected_domains`;
- `profile_secondary_domains`;
- `profile_downrank_domains`;
- `profile_situated_secondary_domains`;
- `profile_policy_reason_codes`;
- `profile_crawl_top_n_budget`;
- `profile_crawl_max_chars_budget`;
- `profile_manual_latency_target_s`;
- `profile_source_evidence_policy_kind`;
- `profile_expected_source_present`;
- `profile_expected_material_used`;
- `profile_secondary_source_present`;
- `profile_secondary_material_used`;
- `profile_situated_source_present`;
- `profile_situated_material_used`;
- `profile_downrank_source_present`;
- `profile_downrank_material_used`;
- `profile_insufficient_evidence`;
- `profile_insufficient_evidence_reason_codes`;
- `profile_source_domain_counts`.

Ne jamais logger: prompt brut, contenu crawle complet, secret, token, cookie, HTML brut ou base64.

## Hors scope Phase 5

- pas de modification SearXNG globale;
- pas de `settings.yml`, `remove`, `keep_only`;
- pas de restart SearXNG;
- pas de fallback OpenRouter / Exa / Parallel;
- pas d'auto-web;
- pas de connecteur Adobe ni API Adobe;
- pas de refonte benchmark;
- pas de UI dashboard.
