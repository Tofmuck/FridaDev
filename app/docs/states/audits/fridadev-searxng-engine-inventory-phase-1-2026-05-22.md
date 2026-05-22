# FridaDev SearXNG engine inventory Phase 1 - 2026-05-22

Statut: audit Phase 1 archive, produit par Sauron et versionne par Celebrimbor.

Perimetre: inventaire borne des moteurs SearXNG pertinents pour la reconstruction locale de la recherche web FridaDev. Aucun runtime FridaDev, SearXNG, Crawl4AI, Docker, prompt, benchmark runner, Memory, Identity, Summary, Biblio/RAG ou document actif n'a ete modifie.

## Sources et docs consultees

Documentation SearXNG pertinente:

- documentation principale SearXNG;
- Search API;
- settings `search`, `server`, `engines`;
- `use_default_settings`, `remove`, `keep_only`;
- categories, engines, bangs et activation/desactivation moteur.

Artefacts Sauron lus:

- `/tmp/fridadev-searxng-engine-inventory-phase1-20260522/bang-probes.tsv`;
- `/tmp/fridadev-searxng-engine-inventory-phase1-20260522/engine-only-probes.tsv`;
- `/tmp/fridadev-searxng-engine-inventory-phase1-20260522/engine-probes.tsv`.

Nuance importante: les sondes `engine-probes` peuvent agreger plus large que le moteur seul. Pour decider une activation Phase 4, il faut privilegier les preuves `bang-probes` et `engine-only-probes`.

## Configuration effective observee

- `use_default_settings: true`: heritage SearXNG large, non borne par profils FridaDev.
- Formats exposes: `html`, `json`.
- Langue par defaut: `fr-FR`.
- Safe search: `0`.
- Timeout global observe: `2.5`.
- Limiter actif.
- Valkey actif.
- FridaDev passe en interne, donc sans limitation utilisateur externe SearXNG.

Cette configuration explique une partie du bruit: l'instance herite largement des moteurs et categories SearXNG, tandis que FridaDev doit maintenant devenir source-first et profile au lieu d'accepter un classement generaliste brut.

## Tableau moteur -> statut -> profils -> recommandation

| Moteur | Statut observe | Profils pertinents | Recommandation |
| --- | --- | --- | --- |
| Google | 403 / acces refuse | Aucun en V1 | A eviter comme dependance. Ne pas investir Phase 4 pour le sauver. |
| DuckDuckGo web | CAPTCHA | General/divers si disponible | Ne pas en faire un pilier SearXNG tant que CAPTCHA. Reste utilisable seulement quand il fonctionne. |
| Startpage | CAPTCHA / suspendu | Aucun en V1 | A eviter comme dependance. |
| Brave web | Utile sur certains cas, mais instable / 429 | General, administratif en appoint | Candidat prudent, jamais moteur unique. |
| Bing web | Repond sur certaines sondes et remonte Service Public | Administratif / general en appoint | A etudier prudemment si disponible dans SearXNG, sans API externe. |
| Microsoft Learn | Repond tres bien via bang `!msl` | `documentation_officielle` | Candidat fort Phase 4 pour docs officielles techniques. |
| MDN | Repond bien | `documentation_officielle` web/dev | Candidat fort quand l'autorite cible est Mozilla/Web. |
| Bing News | Repond via bang `!bin`, moteur actuellement desactive | `actualite` | Candidat Phase 4 borne pour actualite; ne pas rendre souverain. |
| Reuters | Repond bien | `actualite` internationale | Source actualite acceptee, fiable, mais jamais source unique. |
| DuckDuckGo News | Repond mais depend de DDG | `actualite` appoint | Appoint possible, pas source principale. |
| Qwant News | Repond avec bruit local/general | `actualite` appoint | Appoint eventuel, a surveiller. |
| Wikinews | Repond mais couverture inegale | `actualite` appoint | Appoint seulement. |
| arXiv | Repond bien | `academique` sciences exactes / informatique / mathematiques | Candidat fort academique sciences. |
| OpenAIRE | Repond | `academique` large | Candidat utile academique, notamment DOI/publications. |
| PubMed | Repond bien | `academique` medical | Candidat fort academique medical. |
| Google Scholar | Acces refuse / unusual traffic | Aucun en V1 | A eviter. |
| Semantic Scholar | Instable / erreur JSON | Academique theorique | Ne pas activer sans nouvelle preuve stable. |
| GitHub / GitHub issues | Repond parfois | Technique appoint | Visible mais declasse hors demande explicite; pas documentation officielle premiere. |
| StackOverflow | Repond via bang desactive | Technique appoint | Visible mais declasse; jamais autorite documentaire premiere. |
| AskUbuntu | Repond | Technique appoint | Visible mais declasse hors demande support explicite. |
| SuperUser | Repond | Technique appoint | Visible mais declasse hors demande support explicite. |
| Docker Hub | Repond | Documentation technique appoint | Utile quand l'autorite cible est Docker/image, pas docs generales. |
| Wikipedia / Wikidata | Variable, parfois vide selon sonde | General/divers, academique appoint | Appoint encyclopedique, pas source finale hors demande encyclopedique. |
| Wiktionary / dictionnaires | Repond pour certains termes | Definitionnel appoint | Appoint seulement, pas autorite finale hors demande definitionnelle. |

## Tableau par profil

| Profil | Panier plausible | A eviter / declasser | Decision |
| --- | --- | --- | --- |
| `documentation_officielle` | Microsoft Learn, MDN, docs officielles source-first par autorite cible, Docker Hub quand cible Docker | Q&A techniques, blogs, tutoriels SEO, dictionnaires | Microsoft Learn valide comme candidat fort. Les docs officielles restent source-first par autorite cible. |
| `administratif_francais` | `service-public.fr`, `ants.gouv.fr`, `legifrance.gouv.fr`, `.gouv.fr`, `education.gouv.fr`, `eduscol.education.fr`, `enseignementsup-recherche.gouv.fr`, `onisep.fr`, `ac-*.fr` avec prudence | Reddit, forums, SEO, conjugueurs, dictionnaires hors definition | Sources institutionnelles francaises validees comme legitimite prioritaire. |
| `academique` | arXiv, OpenAIRE, PubMed, sources universitaires, DOI/publications, encyclopedies academiques selon sujet | Dictionnaires generalistes, Q&A techniques hors demande, Google Scholar refuse, Semantic Scholar instable | Profil academique large valide: philosophie, SHS, droit, sciences exactes, medecine, informatique. Sous-signaux oui, sous-profils prematurement non. |
| `actualite` | Sources institutionnelles quand actualite institutionnelle, Reuters, Bing News comme candidat borne, AFP/vie-publique selon resultats | Un moteur unique, blogs SEO, news bruitées, Reuters seul | Bing News peut etre etudie/active de facon bornee; Reuters accepte mais non unique. |
| `general_divers` | Moteurs generalistes disponibles, Wikipedia/Wikidata en appoint, diversite de domaines | Dictionnaires comme autorite finale, moteurs CAPTCHA/403/429 comme dependance | Rester sobre et pluraliste; ne pas durcir par defaut. |

## Recommandations Phase 4

- Garder le gate utilisateur fort avant toute modification SearXNG.
- Avant patch plateforme, Sauron doit presenter: config actuelle, config cible, diff attendu, risques, rollback et fenetre de restart.
- Auditer `use_default_settings: true` puis proposer eventuellement `remove` / `keep_only` selon la documentation SearXNG.
- Etudier Microsoft Learn comme candidat fort `documentation_officielle`.
- Etudier Bing News comme candidat borne `actualite`, sans en faire un oracle.
- Garder Reuters comme source d'actualite fiable, surtout internationale, mais jamais source unique.
- Ne pas investir sur Google, Google Scholar, Startpage ou DuckDuckGo web tant que les sondes montrent acces refuse ou CAPTCHA.
- Ne pas faire des Q&A techniques des sources officielles par defaut.
- Ne pas globaliser les bans de dictionnaires/encyclopedies: ils restent utiles comme appoint definitionnel ou encyclopedique.

## Decisions utilisateur integrees

Documentation officielle:

- Microsoft Learn est valide comme candidat fort pour `documentation_officielle`.
- Les docs officielles restent source-first par autorite cible.
- Les Q&A techniques ne sont pas autorite documentaire premiere.

Actualite:

- Bing News peut etre etudie ou active comme candidat borne pour `actualite`.
- Reuters est accepte comme source actualite fiable, surtout internationale.
- Reuters ne doit pas devenir source unique.
- Pour actualite institutionnelle, les sources institutionnelles restent prioritaires.

Administratif francais:

- Sources validees: `service-public.fr`, `ants.gouv.fr`, `legifrance.gouv.fr`, domaines `.gouv.fr`, `education.gouv.fr`, `eduscol.education.fr`, `enseignementsup-recherche.gouv.fr`, `onisep.fr`, sites academiques officiels `ac-*.fr` avec prudence.

Academique:

- Profil academique large valide.
- Il inclut philosophie, SHS, droit, sciences exactes, medecine et informatique.
- Sous-signaux oui; sous-profils prematurement non.

Q&A techniques:

- StackOverflow, GitHub issues, AskUbuntu et SuperUser restent visibles mais declasses.
- Ils ne sont pas documentation officielle, sauf demande explicite utilisateur.

Moteurs externes tokenises:

- Non aux moteurs externes tokenises, sauf DuckDuckGo officiel complet.
- Si DuckDuckGo propose une API officielle complete de recherche web/news, elle peut etre etudiee.
- Ne pas accepter de SERP API tierce qui scrape DuckDuckGo en se presentant comme DuckDuckGo.
- Pas de Brave Search API.
- Pas de Google API.
- Pas de Bing API.
- Si DuckDuckGo n'a pas d'API officielle complete, DuckDuckGo reste seulement un moteur SearXNG quand il fonctionne.

## Risques produit et politiques

- Choisir des moteurs produit une realite documentaire; la decision doit rester visible.
- Une source officielle n'est pas une verite absolue; elle est prioritaire quand elle est alignee avec l'autorite demandee.
- Reuters est fiable pour beaucoup d'actualite internationale, mais peut deplacer la perspective vers une presse d'agence anglophone.
- Les sources institutionnelles sont prioritaires en administratif et actualite institutionnelle, mais ne doivent pas effacer les besoins critiques ou academiques.
- Les Q&A techniques sont utiles pour depannage et experience pratique, mais dangereux comme autorite documentaire premiere.
- Les dictionnaires et encyclopedies sont utiles comme appoint; hors demande definitionnelle, ils ne doivent pas dominer.

## Limites de l'audit

- Les sondes capturent l'etat de l'instance au 2026-05-22; CAPTCHA, 403 et 429 peuvent varier.
- `engine-probes` peut agreger plus large que le moteur teste; utiliser `bang-probes` et `engine-only-probes` pour les decisions Phase 4.
- L'inventaire ne modifie pas SearXNG et ne prouve pas une configuration cible.
- Les moteurs externes a API n'ont pas ete testes runtime; la doctrine utilisateur les exclut sauf DuckDuckGo officiel complet.
- La Phase 4 reste necessaire pour proposer une configuration cible, un rollback et une fenetre de restart.
