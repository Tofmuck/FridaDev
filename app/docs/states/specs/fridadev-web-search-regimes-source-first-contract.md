# Contrat regimes de recherche et source-first web local

Date: 2026-05-22

Statut: spec Phase 2/3 du chantier `fridadev-local-web-search-rebuild`.

## Doctrine

Le runtime web FridaDev reste local only:

- SearXNG decouvre les URLs;
- Crawl4AI lit/crawl les URLs;
- la logique FridaDev classe, oriente, rerank et observe localement;
- OpenRouter / Exa / Parallel restent des temoins externes de benchmark, jamais un fallback runtime.

Le profil de recherche ne declenche jamais le web seul. Il s'applique uniquement quand le web est deja demande par le chemin manuel existant.

## Regimes canoniques

| Profil | Intention | Sources probables | Erreurs typiques |
|---|---|---|---|
| `explicit_url` | Lire une URL fournie explicitement. | URL utilisateur, lecture directe Crawl4AI. | Laisser une recherche ouverte masquer l'etat de lecture primaire. |
| `documentation_officielle` | Trouver une documentation, reference API, guide, manuel, support ou help center officiel. | Domaine officiel de l'autorite cible: Adobe, Microsoft Learn, Stripe docs, OpenRouter docs, MDN, Docker docs, etc. | Promouvoir un vendor de fixture juste parce que la requete contient `documentation`, `officiel`, `api` ou `guide`. |
| `administratif_francais` | Trouver une source institutionnelle ou administrative francaise. | `service-public.fr`, `ants.gouv.fr`, `legifrance.gouv.fr`, `.gouv.fr`, `education.gouv.fr`, `eduscol.education.fr`, `enseignementsup-recherche.gouv.fr`, `onisep.fr`, `ac-*.fr` avec prudence. | Conjugueurs, dictionnaires, SEO et forums avant les sources administratives. |
| `academique` | Trouver des sources universitaires ou scientifiques, au sens large. | HAL, arXiv, PubMed, OpenAIRE, OpenEdition, Cairn, Persee, Stanford Encyclopedia, revues et institutions universitaires. | Reduire l'academique a philosophie/Derrida; confondre homonymes et sources conceptuelles. |
| `actualite` | Traiter une demande recente, annoncee, en cours ou datee comme recente. | Sources institutionnelles pour actualite institutionnelle; Reuters accepte comme source internationale fiable mais jamais unique; Bing News reste candidat SearXNG borne futur. | Transformer une source presse ou institution unique en verite suffisante. |
| `general_divers` | Fallback sobre pour les demandes ambigues ou ordinaires. | Panier pluraliste, Wikipedia/dictionnaires comme appoint possible. | Sur-classer une demande ambigue dans un profil d'autorite sans signaux suffisants. |

## Classification deterministe

La classification est locale et sans appel modele.

Ordre de decision:

1. URL explicite -> `explicit_url`.
2. Signaux administratifs francais forts -> `administratif_francais`.
3. Signaux d'actualite/recent -> `actualite`.
4. Signaux de documentation officielle/API/reference/guide/support -> `documentation_officielle`.
5. Signaux academiques larges -> `academique`.
6. Sinon -> `general_divers`.

Les demandes Q&A techniques explicites comme StackOverflow, GitHub issues, AskUbuntu ou SuperUser restent visibles comme appoint potentiel mais ne deviennent pas `documentation_officielle`.

## Source-first

Source-first extrait, quand c'est possible:

- une autorite cible;
- un produit ou objet;
- des domaines probables d'autorite;
- des reason codes content-free.

Exemples normatifs:

| Demande | Autorite | Produit | Domaines probables |
|---|---|---|---|
| documentation officielle Adobe Photoshop | Adobe | Photoshop | `helpx.adobe.com`, `developer.adobe.com`, `adobe.com` |
| documentation officielle Adobe Illustrator | Adobe | Illustrator | `helpx.adobe.com`, `developer.adobe.com`, `adobe.com` |
| documentation officielle Microsoft Graph API | Microsoft | Graph API | `learn.microsoft.com` |
| documentation officielle Stripe Checkout | Stripe | Checkout | `docs.stripe.com` |
| documentation officielle OpenRouter web search | OpenRouter | web search | `openrouter.ai/docs`, `docs.openrouter.ai`, `openrouter.ai` |
| documentation officielle MDN fetch API | MDN / Mozilla | fetch API | `developer.mozilla.org` |
| documentation officielle Docker compose | Docker | Compose | `docs.docker.com` |

La source map est un appoint, pas une verite. Si une autorite inconnue est extraite sans domaine mappe, FridaDev peut utiliser l'autorite pour orienter une requete, mais ne fabrique pas de domaine probable.

Pour les autorites inconnues, l'extraction doit partir du segment cible apres `documentation officielle`, `docs officielles`, `official docs for`, `documentation for`, etc. Les verbes ou formules de demande (`trouve`, `peux-tu`, `cherche`, `find`, `please`) ne doivent jamais devenir autorite. Si aucun segment cible fiable n'existe, source-first reste inactif.

## Anti-overfit

Les termes generiques `documentation`, `officiel`, `api`, `guide`, `support`, `help`, `reference` ne suffisent jamais a promouvoir une source forte.

Promotion forte seulement si:

- l'autorite cible vient de la demande reelle;
- le domaine probable est aligne avec cette autorite;
- le domaine, l'URL ou le titre contient l'autorite ou le produit demande.

Adobe, Microsoft, Stripe, OpenRouter, MDN et Docker sont des cas de garde-fou, pas des normes cachees. Une requete generique `documentation officielle` ou `API documentation` ne doit promouvoir aucun vendor de fixture.

## Observabilite

Les champs observes sont content-free:

- `search_profile`;
- `source_first_policy_kind`;
- `source_first_active`;
- `source_first_authority`;
- `source_first_product`;
- `source_first_probable_domains`;
- `source_first_reason_codes`;

Ne jamais logger: prompt brut, requete utilisateur brute, contenu crawle, HTML, markdown, secret, token, cookie, base64.

## Hors scope Phase 2/3

- pas de changement SearXNG global;
- pas de modification Docker/Caddy/Authelia;
- pas de moteur externe tokenise;
- pas de fallback OpenRouter / Exa / Parallel;
- pas de sous-profils academiques prematurement;
- pas de suppression de sources;
- pas de changement Memory/Identity/Summary/Biblio/RAG/documents actifs.

## Tests de garde-fou

Les tests unitaires doivent couvrir:

- classification URL, docs officielles, administratif francais, academique large, actualite, general ambigu;
- extraction source-first Adobe Photoshop / Illustrator, Microsoft Graph, Stripe Checkout, OpenRouter web search, MDN fetch API, Docker compose;
- extraction d'autorite inconnue dans des formulations naturelles sans promouvoir les mots de commande;
- absence de vendor fixture sur demandes generiques;
- Q&A technique explicite non assimile a documentation officielle;
- reranking source-first comme bonus souple, pas censure.
