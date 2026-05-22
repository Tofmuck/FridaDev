# Contrat reranking web local explicable par profil

Date: 2026-05-22

Statut: spec Phase 6 du chantier `fridadev-local-web-search-rebuild`.

## Doctrine

Le reranking FridaDev reste un reordonnancement souple:

- il reordonne un panier deja decouvert par SearXNG;
- il explique les mouvements par reason codes content-free;
- il ne supprime pas les resultats;
- il ne bannit pas de source;
- il ne declenche aucun fallback OpenRouter / Exa / Parallel;
- il ne transforme pas une source officielle en verite absolue;
- il ne transforme pas une source situee en source illegitime.

Le reranking ne doit pas pretendre sauver une recherche SearXNG fondamentalement mauvaise. Si le panier initial est pauvre, les phases suivantes doivent rendre cet etat dicible plutot que le masquer.

## Signaux utilises

Le reranker utilise des signaux locaux:

- profil de recherche;
- termes essentiels derives de la demande et de la requete reformulee;
- source-first quand une autorite documentaire est nommee;
- politique Phase 5: domaines attendus, secondaires, situes et declasses;
- indices de fraicheur;
- diversite de domaines.

Ces signaux restent souples. Les resultats declasses restent inspectables dans les sources.

## Regles par profil

### `documentation_officielle`

Promotions souples:

- domaine attendu source-first aligne avec l'autorite nommee;
- documentation officielle alignee avec l'outil, produit, API ou librairie demandes;
- surfaces docs-like quand elles sont alignees avec les termes non generiques de la demande.

Declassements souples:

- Q&A, forums, GitHub issues, blogs, tutoriels tiers et SEO;
- dictionnaires/conjugueurs hors demande definitionnelle.

Garde-fou: OpenRouter, Adobe, Microsoft, Stripe, MDN ou Docker ne doivent pas etre promus parce qu'ils sont connus; la promotion forte depend de l'autorite extraite depuis la demande.

### `administratif_francais`

Promotions souples:

- `service-public.fr`, `ants.gouv.fr`, `legifrance.gouv.fr`, `.gouv.fr`;
- sources Education nationale quand le sujet s'y rapporte;
- autres sources administratives alignees avec les termes essentiels.

Sources situees:

- SUD, CGT et Solidaires restent visibles comme contrepoints situes;
- elles ne passent pas devant une source officielle sur une question de regle, procedure ou droit positif.

Declassements souples:

- dictionnaires, conjugueurs, SEO hors sujet;
- sources non administratives quand une source officielle pertinente existe.

### `academique`

Promotions souples:

- arXiv, OpenAIRE, PubMed, HAL, OpenEdition, Cairn, Persee, DOI, revues et universites;
- source academique alignee avec le sujet reel, pas seulement philosophie.

Declassements souples:

- dictionnaires, encyclopedies generalistes, blogs et presse generaliste hors appoint.

Garde-fou: Stanford Encyclopedia peut etre utile en philosophie, mais ne devient pas un raccourci souverain pour sciences exactes, droit, medical, sociologie ou informatique.

### `actualite`

Promotions souples:

- fraicheur;
- source institutionnelle alignee quand l'actualite est institutionnelle;
- Reuters comme source internationale utile.

Declassements souples:

- vieux contenus;
- encyclopedies, dictionnaires, pages generiques hors actualite.

Garde-fou: Reuters ne devient jamais source unique souveraine; une source institutionnelle alignee peut passer devant une news generique.

### `general_divers`

Comportement sobre:

- diversite de domaines;
- downrank leger des dictionnaires/conjugueurs accidentels;
- aucune source officielle ou academique imposee par defaut;
- Mojeek reste candidat secondaire, pas souverain.

## Reason codes stables

Reason codes Phase 6:

- `profile_expected_domain_soft_bonus`;
- `profile_secondary_domain_soft_bonus`;
- `profile_situated_secondary_visible_not_authority`;
- `profile_downrank_domain_soft_penalty`;
- `source_first_expected_domain_soft_bonus`;
- `official_source_soft_bonus`;
- `academic_source_soft_bonus`;
- `freshness_soft_bonus`;
- `dictionary_soft_downrank`;
- `conjugator_soft_downrank`;
- `qa_soft_downrank`;
- `domain_diversity_soft_adjustment`;
- `promoted`;
- `downranked`.

Les anciens reason codes restent conserves quand ils existaient deja afin de ne pas casser les lectures historiques.

## Diversite et non-censure

La diversite de domaines est un ajustement souple. Elle evite qu'une tete de resultats soit entierement concentree sur un seul domaine quand d'autres domaines plausibles existent, sans effacer les resultats dominants.

Aucune source n'est supprimee par Phase 6. Les dictionnaires, Q&A, forums, syndicats, encyclopedies ou blogs peuvent rester visibles comme appoints ou contrepoints, mais leur statut est explicite.

## Hors scope Phase 6

- pas de suppression dure;
- pas de fallback OpenRouter / Exa / Parallel;
- pas d'auto-web;
- pas de changement SearXNG global;
- pas de changement Crawl4AI;
- pas de score de confiance actionnable;
- pas de UI dashboard;
- pas de changement Memory / Identity / Summary / Biblio / RAG.
