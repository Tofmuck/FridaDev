# FridaDev local web search Phase 0 baseline - 2026-05-22

Statut: consolidation Phase 0, docs + benchmark-only.

Perimetre: consolider l'etat des lieux reel de la recherche web locale FridaDev sans repartir de zero. Aucun runtime FridaDev, SearXNG, Crawl4AI, Docker, prompt, Memory, Identity, Summary, Biblio/RAG ou document actif n'a ete modifie.

## Resume executif

La Phase 0 ne doit pas etre relancee comme un audit illimite. Les preuves existantes couvrent deja le coeur du diagnostic:

- audit stack locale SearXNG/Crawl4AI;
- benchmark Lot 8 local / local_profiled / Exa / Parallel;
- diagnostic same-query SearXNG vs OpenRouter;
- complement local-only borne sur les cas manquants.

Hypothese utilisateur confirmee avec precision: actualite IA Europe, OpenRouter docs, Derrida / trace, renouvellement CNI, URL explicite, local vs local_profiled, diagnostic SearXNG vs reformulation et audit stack sont deja largement couverts. Les cas Adobe Photoshop, Adobe Illustrator, Bourdieu / sociologie, sciences exactes, documentation technique autre qu'OpenRouter et divers ambigu etaient manquants; ils ont ete completes par un run local-only borne.

Conclusion: la Phase 0 est consolidee pour passer au travail Sauron de Phase 1 sur l'inventaire moteur SearXNG. Elle ne justifie pas de relancer Exa/Parallel ni d'elargir indefiniment le corpus.

## Sources relues

- `app/docs/todo-todo/product/fridadev-local-web-search-rebuild-todo.md`
- `app/docs/states/audits/fridadev-local-web-search-stack-audit-2026-05-21.md`
- `app/docs/states/audits/fridadev-web-search-lot8-final-benchmark-2026-05-22.md`
- `benchmark/web-search/README.md`
- `/tmp/fridadev-web-search-lot8-live/local.md`
- `/tmp/fridadev-web-search-lot8-live/local-profiled.md`
- `/tmp/fridadev-web-search-same-query-diagnostic/comparison.md`
- `/tmp/fridadev-web-search-same-query-diagnostic/searxng.md`

## Artefacts reutilises

- `/tmp/fridadev-web-search-lot8-live/local.md`
- `/tmp/fridadev-web-search-lot8-live/local-profiled.md`
- `/tmp/fridadev-web-search-lot8-live/openrouter-exa.md`
- `/tmp/fridadev-web-search-lot8-live/openrouter-parallel.md`
- `/tmp/fridadev-web-search-same-query-diagnostic/comparison.md`
- `/tmp/fridadev-web-search-same-query-diagnostic/searxng.md`

## Complement minimal lance

Artefact:

- `/tmp/fridadev-web-search-phase0-missing-local/phase0-missing-local.md`

Scope du complement:

- bras `local` et `local_profiled` uniquement;
- 6 cas manquants;
- aucun appel OpenRouter / Exa / Parallel;
- aucun changement runtime;
- aucun patch SearXNG ou Crawl4AI;
- rapport Markdown borne, sans secret.

Limite de lecture: l'artefact complementaire est suffisant pour les domaines, titres, profils, signaux locaux et erreurs de ranking; plusieurs extraits bornes y sont vides, donc il ne doit pas servir de preuve fine du contenu textuel lu.

## Tableau des cas Phase 0

| Cas | Statut | Preuves | Diagnostic synthetique | A mesurer encore |
| --- | --- | --- | --- | --- |
| Actualite IA Europe | Deja couvert | Lot 8 + same-query | Local historique trouve des sources UE mais reste bruite; local_profiled regresse fortement; same-query montre que SearXNG peut tomber sur dictionnaires/Wikipedia avec la requete exacte. | Inventaire moteurs/news SearXNG en Phase 1; ne pas relancer Exa/Parallel. |
| OpenRouter docs | Deja couvert | Lot 8 + same-query | SearXNG trouve `openrouter.ai`, mais la page cible et les extraits restent imparfaits; cas utile pour source-first documentation officielle. | Tester apres Phase 3/5, pas maintenant. |
| URL explicite / lecture directe | Deja couvert | Lot 8 local + local_profiled | Chemin local excellent: `explicit_url_direct`, `page_read`, Crawl4AI fit, pas de rerank ni recherche ouverte. | Rien en Phase 0. |
| Derrida / trace | Deja couvert | Lot 8 + same-query | SearXNG reste fragile face aux homonymes et dictionnaires; local_profiled ameliore un peu mais ne construit pas encore un vrai panier academique. | Panier moteurs academiques en Phase 1; regime `academique` en Phase 2. |
| Renouvellement CNI | Deja couvert | Lot 8 + same-query | Local historique echoue sur conjugueurs; local_profiled corrige nettement avec ANTS / Service Public; same-query montre que SearXNG strict peut encore manquer les domaines attendus. | Panier institutionnel francais en Phase 1. |
| Adobe Photoshop | Complete local-only | Complement Phase 0 | Local trouve `helpx.adobe.com` et `adobe.com`, mais derriere `herothemes.com` et Wikipedia; local_profiled classe `general` et perd les domaines Adobe. | Phase 2/3: classification `documentation_officielle` et source-first autorite Adobe. |
| Adobe Illustrator | Complete local-only | Complement Phase 0 | Local et local_profiled classent `general`; aucun domaine Adobe dans le top 5; bruit `documentation` dominant. | Phase 2/3: ne pas laisser le terme generique `documentation` gouverner la recherche. |
| Bourdieu / sociologie | Complete local-only | Complement Phase 0 | Local et local_profiled classent `general`; SearXNG part sur `Pierre` comme prenom/nom commun et remonte des pierres/mineraux. | Phase 2: `academique` large; Phase 1: moteurs SHS; Phase 6: homonymie. |
| Sciences exactes | Complete local-only | Complement Phase 0 | Local et local_profiled classent `general`; resultats generiques sur `theoreme` et dictionnaires au lieu de Noether/symetries. | Phase 2: academique sciences exactes sans sous-decoupage premature; Phase 1: moteurs pertinents. |
| Documentation technique autre qu'OpenRouter | Complete local-only | Complement Phase 0 | Microsoft Graph est classe `technique_officielle`, mais local manque `learn.microsoft.com`; local_profiled retombe sur bruit `documentation` / dictionnaires. | Phase 3 source-first autorite Microsoft; Phase 5 parametres docs officielles. |
| Divers volontairement ambigu | Complete local-only | Complement Phase 0 | Jaguar remonte surtout marque automobile et pages auto; l'ambiguite animal/marque n'est pas equilibree. | Phase 7 comportement d'echec/elargissement; Phase 6 diversite si besoin. |

## Diagnostic consolide

1. Le chemin URL explicite est sain et ne doit pas etre reouvert en Phase 0.
2. Les echecs ouverts ne viennent pas d'une seule cause: il y a a la fois classification trop generale, ranking/index SearXNG fragile et absence de source-first robuste.
3. Le profil `local_profiled` V0 n'est pas suffisant: il peut corriger CNI mais regresser actualite et documentation officielle hors OpenRouter.
4. La confiance locale reste trop optimiste sur plusieurs cas: actualite IA, Adobe, Bourdieu, sciences exactes et Microsoft Graph montrent du materiau injecte mais mal aligne.
5. Le terme generique `documentation` est dangereux: il peut dominer la requete au lieu de l'autorite cible.
6. L'academique doit rester large: philosophie, SHS, sciences exactes et informatique documentaire ont des erreurs differentes, mais il serait premature de creer trop de sous-profils avant Phase 1.
7. SearXNG doit etre audite comme index/ranking local, pas compense par OpenRouter runtime.

## Ce qu'il faut encore mesurer

- Phase 1 Sauron: moteurs SearXNG reellement utilisables par profil cible.
- Categories SearXNG disponibles et utiles depuis l'instance OVH.
- Moteurs qui CAPTCHA, 429, repondent avec bruit ou sont trop lents.
- Panier moteur plausible ou manque explicite pour `documentation_officielle`, `administratif_francais`, `academique`, `actualite` et `general_divers`.

## Ce qu'il ne faut pas relancer inutilement

- Pas de nouveau benchmark complet local / Exa / Parallel pour Phase 0.
- Pas de nouveau same-query OpenRouter sans question nouvelle.
- Pas de nouvel elargissement du corpus au-dela des 11 cas consolides sans decision explicite.
- Pas de correction runtime pendant la consolidation.
- Pas de fallback OpenRouter / Exa / Parallel, meme comme "soupape" experimentale.

## Passage vers Phase 1

La consolidation Celebrimbor est suffisante pour ouvrir Phase 1 cote Sauron: inventaire borne des moteurs SearXNG pertinents par profil.

Phase 0 n'est pas cochee globalement dans la TODO A-Z, car la part plateforme `moteurs actifs / reellement utilisables / categories disponibles` doit maintenant etre qualifiee proprement par Sauron en Phase 1 plutot que gonflee dans une Phase 0 interminable.

Critere de passage propose:

- l'utilisateur accepte le corpus baseline borne;
- aucun cas supplementaire n'est ajoute sans decision explicite;
- Sauron lance l'inventaire moteur profile, sans auditer les 200+ moteurs un par un.
