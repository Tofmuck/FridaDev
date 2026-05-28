# Frida Biblio native / Frida Catalogue contract

Statut: spec vivante
Date: 2026-05-28
Classement: `app/docs/states/specs/`
Roadmap active: `app/docs/todo-todo/product/frida-biblio-native-catalogue-todo.md`
Audit Lot 0 Catalogue: `app/docs/states/audits/frida-catalogue-human-metadata-editing-audit-2026-05-28.md`
Specs voisines: `app/docs/states/specs/active-conversation-documents-contract.md`, `app/docs/states/specs/workspace-folders-contract.md`
Portee: contrat produit, frontieres, client futur GET-only, resolver, extraction bornee, lane prompt et observabilite de Biblio native.

## 1. Statut et portee

Biblio native est une capacite documentaire persistante separee. Elle permet a FridaDev de consulter une bibliotheque durable connue de Frida Catalogue / doc-pipeline, puis de resoudre un document et un passage documentaire borne a la demande.

Source nominale:

- API Catalogue / doc-pipeline;
- DB Catalogue geree par la stack Catalogue;
- metadonnees humaines Lot 0 quand elles existent;
- metadonnees d'ingestion comme trace source, jamais comme titre canonique si une correction humaine existe.

Le premier client FridaDev doit etre strictement read-only / GET-only.

Le Lot 1 ne livre aucun code runtime:

- pas de route FridaDev;
- pas de client Catalogue;
- pas de toggle frontend;
- pas de lane prompt effective;
- pas de branchement chat;
- pas de DB;
- pas de modification de `/opt/platform/doc-pipeline`;
- pas de modification de `/opt/platform/doc-library`.

## 2. Vocabulaire stabilise

`library_document`: document persistant d'une bibliotheque native. Terme generique cote FridaDev.

`catalogue_document`: `library_document` dont la source de verite est Frida Catalogue / doc-pipeline. Il possede un identifiant Catalogue, des metadonnees source et, si disponibles, des metadonnees humaines.

`passage documentaire`: extrait borne issu d'un `library_document` ou `catalogue_document`, consulte a la demande pour un tour. Il n'est pas un document actif et ne devient pas automatiquement durable dans FridaDev.

`locator`: repere documentaire demande ou resolu. Exemples: page, chapitre, paragraphe, milestone Stephanus, intervalle `126b -> 126e`, citation structuree ou autre repere supporte par Catalogue.

`resolver documentaire`: service futur FridaDev qui transforme une demande utilisateur en resultat structure:

- document cible;
- locator demande;
- locator resolu;
- statut;
- confiance;
- raisons compactes;
- preuve content-free.

`resolved`: document et locator suffisamment determines pour permettre une extraction bornee sans presenter l'incertitude comme certaine.

`ambiguous`: plusieurs documents, editions, dialogues, locators ou passages restent plausibles. Le modele doit voir l'ambiguite.

`not_found`: aucun document ou locator compatible n'a ete trouve.

`error`: la consultation Catalogue a echoue pour raison technique ou contractuelle.

`confidence`: signal borne, non souverain, qui indique la qualite de resolution. Il peut etre qualitatif ou numerique dans un lot futur, mais ne doit jamais masquer `ambiguous`, `not_found` ou `error`.

`source metadata`: metadonnees d'ingestion ou d'OCR portees par Catalogue: titre auto, nom de fichier source, hash, langue detectee, type source, compteurs, qualite JSON, TOC et champs apparentes.

`human metadata`: metadonnees bibliographiques corrigees humainement par Lot 0 Catalogue: titre canonique, titre original, auteur(s), traducteur(s), editeur scientifique, editeur, collection, annee, langue override, type, notes operateur, statut.

## 3. Frontieres non negociables

Biblio n'est pas `active_document`.

- Un `active_document` est temporaire, conversation-scoped, fourni ou selectionne par l'utilisateur, puis injecte entier ou exclu entier par tour.
- Un `catalogue_document` est durable, hors conversation, consulte ponctuellement.
- Un `passage documentaire` extrait depuis Catalogue ne devient pas automatiquement `active_document`.

Biblio n'est pas workspace.

- Le workspace organise des fichiers persistants a portee de main.
- Biblio designe un fonds/catalogue durable consulte via l'API Catalogue.
- Un `workspace_file` selectionne peut suivre la lane `active_document`; il ne devient pas `catalogue_document`.

Biblio n'est pas Memory/RAG.

- Biblio ne cree pas d'embedding FridaDev par defaut.
- Biblio ne promeut pas les passages dans Memory/RAG.
- Biblio ne remplace pas les traces memoire, les summaries parents ou l'arbitre memoire.

Biblio n'est pas Summary.

- Une consultation Catalogue ne modifie pas le resume de conversation par elle-meme.
- Un passage repris dans une reponse peut ensuite appartenir au dialogue ordinaire, et seulement par ce chemin.

Biblio n'est pas Identity.

- Une consultation d'ouvrage ne cree pas d'enonce identitaire.
- Le juge mutable ne doit pas lire des passages de Biblio comme source identitaire directe.

Biblio n'est pas Web.

- Catalogue est une source locale/persistante deja ingeree.
- Web search decouvre ou lit des sources web; Biblio consulte un fonds Catalogue.

Biblio n'est pas Hermeneutic.

- Hermeneutic juge le tour et la posture.
- Biblio fournit eventuellement un passage documentaire borne dans une lane dediee.

Biblio n'est pas AnythingLLM.

- AnythingLLM n'est pas requis dans le chemin nominal.
- Les precedents OpenWebUI/AnythingLLM peuvent inspirer, mais ne deviennent pas dependance cible.

OCR des documents actifs ne cree pas de Biblio.

- L'OCR ponctuel des `active_document` via Stirling reste conversation-scoped.
- Il ne cree ni `library_document`, ni `catalogue_document`, ni `passage documentaire`.

Un passage extrait ne devient pas automatiquement durable.

- Le passage peut etre utilise dans la reponse du tour.
- Une fois repris dans la reponse, il devient seulement matiere conversationnelle ordinaire.
- Il ne devient pas memoire documentaire durable, document actif, workspace file ou entree Identity.

## 4. Toggle frontend futur

Un lot futur devra ajouter un bouton/toggle Biblio dans le frontend chat, au meme niveau conceptuel que les autres outils explicites.

Invariant `Biblio off`:

- aucune consultation Catalogue;
- aucun appel client Biblio;
- aucune lane `[PASSAGES DE BIBLIOTHEQUE CONSULTES]`;
- aucune tentative de resolver documentaire;
- observabilite `biblio_enabled=false`, `biblio_used=false`.

Invariant `Biblio on`:

- Frida peut consulter Catalogue si la demande appelle une consultation d'ouvrage;
- le toggle autorise seulement une consultation bornee;
- le toggle n'injecte jamais toute la bibliotheque;
- le toggle ne transforme pas Catalogue en contexte permanent;
- l'observabilite indique si Biblio a ete utilisee ou non.

Le toggle n'est pas livre au Lot 1. Il ne doit pas etre confondu avec l'upload de documents actifs, la selection workspace, le web search, Memory/RAG ou un mode OCR.

## 5. Source de verite

La source nominale de Biblio est l'API Catalogue / doc-pipeline.

Priorite metadonnees:

1. `human metadata` validee ou corrigee humainement;
2. `source metadata` d'ingestion Catalogue;
3. `source_filename` seulement comme trace operateur ou fallback affiche, jamais comme titre canonique s'il existe mieux.

Regles:

- le titre canonique humain prime sur le titre auto;
- le titre auto reste utile comme trace d'ingestion;
- `source_filename` ne doit jamais etre presente comme titre bibliographique fiable;
- le statut metadata (`to_review`, `corrected`, `validated`) doit influencer la confiance future;
- FridaDev ne recopie pas Catalogue comme nouvelle source de verite;
- FridaDev ne backfill pas Catalogue;
- AnythingLLM n'est pas requis dans le chemin nominal.

## 6. Contrat client FridaDev futur

Le premier client Catalogue FridaDev doit etre GET-only.

Endpoints autorises au depart:

- `GET /health`;
- `GET /catalog`;
- `GET /doc/{id}`;
- `GET /doc/{id}/metadata`;
- `GET /doc/{id}/locate`;
- `GET /doc/{id}/context`;
- `GET /search`.

Endpoints interdits au client FridaDev initial:

- `DELETE /doc/{id}`;
- `DELETE /doc/{id}/with-files`;
- `PUT /doc/{id}/metadata`;
- `PUT /settings`;
- `POST /settings/reset`;
- `POST /progress/recent/clear`.

Le client futur doit:

- avoir des timeouts explicites;
- gerer Catalogue indisponible sans faire echouer tout le chat si la demande peut etre traitee sans Biblio;
- retourner des erreurs structurees et content-free;
- journaliser seulement endpoint logique, statut, duree, doc id court/hash court, statut de resolution et reason codes;
- ne jamais afficher ni stocker secret, DSN, cookie, texte OCR brut, ouvrage brut, passage complet ou prompt complet dans les logs ordinaires;
- n'ecrire aucune donnee dans Catalogue;
- ne supprimer aucun document;
- ne lancer aucun OCR;
- ne lancer aucun backfill.

## 7. Resolver documentaire

Le resolver futur retourne toujours un statut:

- `resolved`;
- `ambiguous`;
- `not_found`;
- `error`.

Regles:

- ne jamais presenter une resolution incertaine comme certaine;
- toujours distinguer document, corpus, edition, dialogue et locator si les metadonnees l'exigent;
- exposer les raisons d'ambiguite sans texte brut long;
- utiliser `human metadata` comme signal prioritaire quand disponible;
- conserver le `source_filename` comme trace, pas comme preuve bibliographique;
- traiter les milestones Stephanus comme aide, pas comme preuve suffisante.

Cas Platon / Stephanus:

- `126b -> 126e` doit etre un cas de test;
- si le dialogue cible n'est pas determine, le resultat doit etre `ambiguous`;
- si plusieurs occurrences ou editions restent plausibles, le resultat doit etre `ambiguous`;
- si aucun locator compatible n'est trouve, le resultat doit etre `not_found`;
- si Catalogue echoue, le resultat doit etre `error`.

## 8. Extraction bornee

Un passage documentaire extrait doit etre borne.

Champs minimum futurs:

- doc ref;
- doc id court ou hash court;
- titre via `human metadata` si acceptable;
- locator demande;
- locator resolu;
- statut;
- confidence;
- longueur chars;
- hash court du passage;
- reason codes;
- erreurs compactes.

Limites a fixer dans un lot futur:

- limite chars;
- limite tokens;
- comportement si passage trop long;
- politique de citation ou d'affichage utilisateur.

Regles:

- pas de texte brut dans les logs ordinaires;
- pas de contenu d'ouvrage brut dans le dashboard ordinaire;
- pas de stockage comme `active_document`;
- pas de troncature silencieuse sans reason code;
- pas de promesse que tout l'ouvrage a ete lu.

## 9. Lane prompt future

Nom cible:

```text
[PASSAGES DE BIBLIOTHEQUE CONSULTES]
```

La lane doit etre distincte de:

- documents actifs;
- Memory/RAG;
- Summary;
- Identity;
- Web;
- Hermeneutic.

Instruction modele minimale:

```text
Les passages ci-dessous proviennent d'une bibliotheque persistante consultee a la demande.
Ils ne prouvent pas que tout l'ouvrage ou tout le corpus a ete lu.
Respecte le statut de resolution, les limites et les ambiguites.
Ne confonds pas ces passages avec les documents actifs, la memoire, le web, l'identite ou le resume.
```

Si le resolver retourne `ambiguous`, `not_found` ou `error`, la lane doit porter ce statut ou rester absente selon le contrat du lot futur. Le modele ne doit pas recevoir une fiction de resolution.

## 10. Observabilite

Observabilite content-free par defaut:

- `biblio_enabled`;
- `biblio_used`;
- query kind;
- endpoint logique;
- document `resolved` / `ambiguous` / `not_found` / `error`;
- doc id court ou hash court;
- titre human metadata si acceptable, sinon label compact;
- metadata status;
- locator demande;
- locator resolu;
- passage chars;
- passage hash court;
- confidence;
- reason codes;
- erreurs compactes;
- duree appel Catalogue;
- timeout ou retry si applicable.

Ne pas logguer par defaut:

- texte OCR brut;
- passage complet;
- contenu d'ouvrage brut;
- prompt complet;
- secret;
- DSN;
- cookie;
- header d'authentification;
- full document id si un id court suffit;
- source filename si le nom revele une information sensible et qu'un label compact suffit.

Le dashboard ordinaire doit rester content-free. Toute vue future affichant un passage complet devra etre une surface explicite, bornee et documentee separement.

## 11. Tests futurs obligatoires

Lots suivants:

- client GET-only nominal;
- interdiction routes mutatrices;
- `DELETE /doc/{id}` interdit;
- `DELETE /doc/{id}/with-files` interdit;
- `PUT /doc/{id}/metadata` interdit;
- `PUT /settings` interdit;
- `POST /settings/reset` interdit;
- `POST /progress/recent/clear` interdit;
- document trouve;
- document absent;
- document ambigu;
- locator trouve;
- locator absent;
- locator ambigu;
- Stephanus `126b -> 126e`;
- passage trop long;
- lane `[PASSAGES DE BIBLIOTHEQUE CONSULTES]` presente quand Biblio utilisee;
- `Biblio off` empeche toute consultation Catalogue;
- `Biblio on` autorise seulement une consultation bornee;
- anti-contamination `active_document`;
- anti-contamination workspace;
- anti-contamination Memory/RAG;
- anti-contamination Identity;
- anti-contamination Summary;
- anti-contamination Web;
- anti-contamination Hermeneutic;
- absence AnythingLLM dans le chemin nominal;
- observabilite content-free;
- absence de texte brut dans logs ordinaires;
- erreur Catalogue content-free;
- timeout Catalogue content-free.

## 12. Conditions d'ouverture des lots suivants

Lot 2 peut commencer seulement si:

- cette spec reste indexee comme source-of-truth;
- le client cible est confirme GET-only;
- les endpoints mutateurs sont explicitement exclus des tests et du code;
- la frontiere avec `active_document` et workspace est conservee;
- la decision produit accepte que FridaDev consomme Catalogue sans ecrire dans Catalogue.

Tout changement futur qui veut ecrire dans Catalogue, editer les metadonnees depuis FridaDev, supprimer un document, lancer OCR, backfill, indexer ou vectoriser doit ouvrir un nouveau lot explicite avant code.
