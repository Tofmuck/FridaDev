# FridaDev Adobe docs mode contract

Statut: spec vivante
Date: 2026-05-23
TODO source: `app/docs/todo-todo/product/Adobe to do.md`
Portee: contrat UI, payload, backend, lecture HelpX, prompt, non-contamination et observabilite du mode Adobe Photoshop / Illustrator.

## 1. Verdict de plan

Existe-t-il un meilleur plan que la TODO seule ?

Oui, legerement: garder la TODO comme feuille de route, mais ajouter cette spec courte comme contrat normatif avant tout patch runtime.

Raison: la TODO est granulaire et actionnable, mais les futurs lots runtime doivent pouvoir verifier rapidement les invariants sans relire tout le plan. Cette spec verrouille donc les champs de payload, la separation avec `web_search`, la politique de cache, la non-contamination et le minimum de tests.

## 2. Definition

Le mode Adobe est un mode explicite de conversation qui aide l'utilisateur sur Photoshop ou Illustrator en lisant a la demande quelques pages officielles HelpX.

Le mode Adobe n'est pas:

- une grosse base Adobe;
- un index durable;
- une Biblio Adobe;
- une ingestion massive;
- un mode Auto;
- une variante de recherche web ouverte;
- une dependance SearXNG, Exa, OpenRouter ou AnythingLLM.

## 3. Contrat UI

Etat par defaut:

- le mode Adobe est inactif au chargement;
- aucune conversation existante ne doit l'activer implicitement.

Controle:

- l'UI doit proposer un controle explicite;
- le produit doit etre choisi explicitement: `photoshop` ou `illustrator`;
- aucun choix `auto` ne doit exister dans le MVP;
- la desactivation doit etre simple et visible;
- l'etat actif doit etre lisible sans promettre une expertise absolue.

Si le mode Adobe est actif, l'UI doit rendre clair que Frida consulte des sources Adobe officielles bornees. Le controle ne doit pas suggerer que Frida possede toute la connaissance Adobe.

## 4. Contrat payload

Activation normative:

```json
{
  "specialization_profile": "adobe",
  "adobe_product": "photoshop"
}
```

Produits valides:

- `photoshop`;
- `illustrator`.

Compatibilite:

- si `specialization_profile` est absent, vide ou different de `adobe`, le chat existant reste inchange;
- les clients existants qui n'envoient pas ces champs ne changent pas de comportement.

Erreurs:

- si `specialization_profile=adobe` et `adobe_product` est absent, le backend doit refuser le tour avec une erreur compacte, par exemple `adobe_product_required`;
- si `adobe_product` est different de `photoshop` ou `illustrator`, le backend doit refuser le tour avec une erreur compacte, par exemple `adobe_product_invalid`;
- le backend ne doit jamais deviner le produit.

Interaction avec `web_search`:

- pour le MVP, le mode Adobe et la recherche web generale sont mutuellement exclusifs dans l'execution;
- si `specialization_profile=adobe`, le backend ne doit pas lancer `tools/web_search.py`, meme si `web_search=true` arrive dans le payload;
- l'observabilite doit signaler que le web general a ete ignore ou non demande pour raison `adobe_profile_owns_retrieval`.

## 5. Contrat backend

Le pipeline Adobe doit etre separe du web search general.

Obligatoire:

- ne pas remplacer `tools/web_search.py`;
- ne pas transformer les profils web existants en profils Adobe;
- ajouter un module dedie, par exemple `app/tools/adobe_docs.py` ou une separation equivalente par responsabilite;
- garder `app/server.py` comme entree HTTP et orchestration;
- brancher le mode dans `chat_service` ou une couche applicative equivalente;
- ne pas modifier Memory, Identity, Summary, Biblio ou Active Documents sauf garde-fou strictement necessaire;
- ne pas utiliser SearXNG, Exa ou OpenRouter comme discovery nominale du MVP Adobe.

Le backend doit produire deux choses distinctes:

- un bloc prompt Adobe contenant uniquement les passages courts retenus pour le tour;
- un payload d'observabilite content-free, sans markdown ni passage source.

Le payload d'observabilite ne doit pas transporter `context_block`, `content_used`, `search_snippet` ou autre champ contenant du texte Adobe.

## 6. Contrat de lecture

Sources MVP:

- host strict: `helpx.adobe.com`;
- produit obligatoire dans le chemin: `/photoshop/` ou `/illustrator/`;
- seeds courtes par produit: hub, release notes, known/fixed issues;
- liens internes seulement, filtres par produit et par extension.

Registre source Lot 1:

- le registre source est content-free: produit, type, URL, titre court et politique langue seulement;
- les produits valides sont seulement `photoshop` et `illustrator`;
- les types sources valides sont `hub`, `release_notes`, `known_issues` et `help_page`;
- la canonicalisation retire fragment et query string avec reason codes content-free;
- la canonicalisation ne reecrit pas les chemins langue/region et n'invente pas d'URL;
- la deduplication stable se fait sur URL canonique, en conservant le premier ordre observe.

Interdits MVP:

- `www.adobe.com/learn`;
- `community.adobe.com`;
- PDF, images, videos, archives lourdes;
- sites tiers;
- crawl massif;
- ingestion durable.

Crawl4AI:

- `raw` est la lecture primaire;
- `fit` peut etre une optimisation ou un fallback court, jamais une preuve unique de lecture complete;
- nombre de pages par tour borne;
- nombre de liens suivis borne;
- timeout par page et timeout global bornes;
- grosses pages jamais injectees brutes.

Reader Crawl4AI Lot 2:

- le reader lit une URL Adobe deja validee avec `/md`, filtre `raw` et cache Crawl4AI desactive (`c=0`);
- le reader retourne le markdown seulement dans l'objet resultat en memoire du tour;
- le `repr` et les exports content-free du resultat ne contiennent jamais le markdown;
- les statuts du reader sont `success`, `empty`, `error`, `timeout` et `invalid_url`;
- les metriques autorisees sont chars, headings, link_count, elapsed_ms, filter_used, cache_mode, source_type, produit, URL hash court et reason codes;
- le Lot 2 n'implemente pas de fallback `fit`; un futur fallback devra rester explicite et ne pourra jamais devenir preuve unique;
- le reader ne cree pas de fichier temporaire et n'ecrit pas le markdown dans un cache applicatif.

Extraction de liens Lot 3:

- l'extracteur lit seulement du Markdown deja present en memoire et ne declenche aucun crawl;
- les liens Markdown sont resolus contre l'URL source, canonicalises et revalides par le registre Lot 1;
- les liens acceptes restent limites a `helpx.adobe.com` et au produit explicite;
- les fragments et query strings sont retires avec reason codes;
- les liens Learn, Community, marketing, comptes, PDF, images, videos, archives et autre produit sont exclus;
- les objets lien et ranking peuvent contenir l'URL canonique pour le futur reader, mais leurs `repr` et exports content-free ne contiennent ni Markdown ni texte d'ancre;
- le ranking est deterministe: questions version/nouveaute vers release notes, questions bug/erreur vers known issues, questions d'usage vers help pages;
- les seeds release notes et known issues du registre restent disponibles si peu de liens utiles sont extraits;
- la limite de suivi par tour reste stricte et par defaut bornee autour de 4 a 8 liens.

Cache:

- cache applicatif interdit;
- cache Crawl4AI desactive par defaut pour Adobe;
- tout cache technique Crawl4AI doit etre explicitement borne/ephemere et documente avant activation;
- si le comportement du cache Crawl4AI n'est pas prouve, il ne doit pas etre utilise pour le mode Adobe.

## 7. Contrat prompt

La lane Adobe est dediee et non instructionnelle.

Elle doit inclure:

- produit choisi;
- statut de lecture;
- sources courtes avec URL canonique;
- passages courts et bornes;
- indication de source officielle HelpX quand applicable;
- caveat si source anglaise, menu localise incertain, lecture partielle ou preuve insuffisante.

Elle doit interdire:

- de traiter le contenu Adobe comme instruction systeme;
- d'affirmer une lecture exhaustive si seule une selection est injectee;
- d'inventer une source Adobe;
- de masquer une lecture partielle ou un echec.

Reponse attendue:

- en francais;
- pratique et utile pour le cas utilisateur;
- sourcee quand une source a ete utilisee;
- prudente quand les passages ne suffisent pas.

## 8. Contrat memoire / persistance

Le texte Adobe lu a la demande est temporaire.

Interdits:

- stockage applicatif du markdown Adobe;
- stockage applicatif des passages Adobe;
- embeddings persistants;
- Biblio Adobe;
- Active Documents Adobe;
- Memory, Identity ou Summary a partir de la lane Adobe;
- logs contenant le texte source ou les passages.

Autorise:

- la reponse finale visible par l'utilisateur reste dans l'historique conversationnel ordinaire;
- cet historique peut dire que l'utilisateur a demande de l'aide Photoshop ou Illustrator;
- il ne doit pas promouvoir des passages Adobe copies comme connaissance durable.

Implementation attendue:

- le bloc prompt Adobe ne doit pas entrer dans les inputs Memory/Identity/Summary;
- si une structure canonique downstream est necessaire, elle doit etre content-free;
- les tests doivent verifier l'absence de `content_used`, `context_block` ou markdown Adobe dans les payloads de non-contamination.

## 9. Contrat observabilite

Autorise, content-free:

- mode actif/inactif;
- produit choisi;
- URL hash court;
- host;
- type source;
- statut crawl;
- filtre utilise;
- cache mode;
- chars bruts;
- headings count;
- link count;
- passages candidats;
- passages injectes;
- chars injectes;
- latence par page;
- latence totale;
- evidence status;
- reason codes.

Interdit:

- markdown Adobe;
- passage Adobe complet;
- prompt final avec passages;
- contenu utilisateur sensible;
- secret, token, cookie, `.env`, DSN;
- fichier temporaire de page;
- screenshot;
- PDF/OCR brut.

## 10. Tests minimaux avant fermeture runtime

UI:

- mode inactif par defaut;
- activation Photoshop;
- activation Illustrator;
- absence de choix Auto;
- desactivation;
- payload produit explicite.

Payload/backend:

- absence de champs Adobe = comportement chat existant inchange;
- `specialization_profile=adobe` sans produit = erreur;
- produit invalide = erreur;
- Adobe actif n'appelle pas `tools/web_search.py`;
- `web_search=true` + Adobe actif ne lance pas la recherche generale.

Lecture:

- seeds valides par produit;
- host non HelpX refuse;
- autre produit refuse;
- PDF/media/Learn/Community refuses;
- `raw` primaire;
- limites pages/liens/passages respectees.

Prompt/persistence:

- passage court injecte dans lane Adobe;
- grosses pages non injectees brutes;
- source externe non instructionnelle;
- payload d'observabilite sans texte Adobe;
- Memory/Identity/Summary/Biblio/Active Documents ne recoivent pas la lane Adobe.

## 11. Decisions utilisateur restantes avant code

Le code peut commencer sans reouvrir la doctrine. Les seules decisions produit encore utiles avant UI sont:

- libelle exact du bouton;
- emplacement du controle;
- persistance du produit par conversation ou reset a chaque nouvelle conversation;
- affichage utilisateur des sources consultees.

Ces decisions ne changent pas les invariants runtime ci-dessus.
