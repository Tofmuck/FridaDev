# Memory RAG - decision reranker - 2026-04-11

Statut: decision active
Classement: `app/docs/states/project/`
Date: `2026-04-11`
Roadmap liee: `app/docs/todo-done/refactors/memory-rag-relevance-todo.md`
References liees:
- `app/docs/states/baselines/memory-rag-6A-evaluation-2026-04-10.md`
- `app/docs/states/baselines/memory-rag-7B-evaluation-2026-04-10.md`
- `app/docs/states/baselines/memory-rag-8C-evaluation-2026-04-10.md`
- `app/docs/states/specs/memory-rag-evaluation-sheet.md`
- `app/docs/states/specs/memory-rag-pre-arbiter-basket-contract.md`
- `app/docs/states/architecture/memory-rag-current-pipeline-cartography.md`

## 1. Objet

Fermer proprement la Phase `9D` du chantier `memory-rag-relevance` par une decision explicite `go / no-go` sur un reranker, sans ouvrir d'implementation runtime supplementaire.

Cette note est volontairement doc-only:
- aucun reranker n'a ete implemente;
- aucun modele n'a ete selectionne;
- aucun provider ou service externe n'a ete integre;
- aucun benchmark artificiel n'a ete lance pour forcer un `go`.

## 2. Decision

Decision retenue au `2026-04-11`:

`reranker = no-go for now`

Lecture retenue:
- le reranker reste une option tardive et strictement optionnelle;
- il n'est pas necessaire a ce stade;
- son introduction ne serait pas proportionnee au dossier de preuve actuel;
- ce `no-go` est une decision de pilotage a date, pas une condamnation metaphysique du reranker.

## 3. Pourquoi la Phase 9D est fermable maintenant

Les prerequis amont de la question reranker sont juges suffisamment fermes:

- `6A` a deja apporte un recall hybride defendable, avec un vrai gain surtout lexical / exact-term / nom propre / URL, sans ouvrir de reranker.
- `7B` a deja apporte un panier pre-arbitre borne, plus lisible, moins redondant et relie par IDs stables jusqu'a l'injection.
- `8C` a deja apporte une voie `summaries` propre sur fixtures/replay, sans double injection, tout en restant explicitement neutre en live tant que `summaries=0`.

Autrement dit:
- le systeme n'est plus dans un etat ou le reranker servirait a compenser un rappel brut ou un panier encore mal pose;
- la question `go / no-go` peut donc etre tranchee honnetement a partir du dossier deja accumule.

## 4. Limites reelles qui restent ouvertes

Les limites restantes sont reelles et doivent rester dites comme telles:

- le live OVH reste sans `summaries`, donc la nouvelle lane `summaries` est encore neutre en production;
- plusieurs probes restent faibles ou neutres, notamment sur preferences durables, identite durable et certains cas d'assistant generique;
- un bruit assistant residuel existe encore sur certains cas;
- le corpus live reste petit et ne prouve pas encore une couverture forte des preferences durables;
- certains verdicts aval arbitre restent variables ou peu demonstratifs selon les probes.

Mais ces limites ne suffisent pas, a date, a demontrer que le prochain goulet serait le ranking final d'un panier deja assaini et borne a `8` candidats max.

Le dossier actuel dit plutot:
- certaines limites restent en amont ou dans la richesse du corpus live;
- aucune preuve forte ne montre encore qu'un reranker serait la reponse proportionnee suivante.

## 5. Pourquoi le reranker reste non retenu a ce stade

Introduire un reranker maintenant ajouterait surtout:

- une integration supplementaire dans la stack applicative;
- un choix de modele et/ou de provider qui n'est pas encore justifie;
- un cout de latence additionnel sur un pipeline ou l'arbitre porte deja l'essentiel du budget;
- un cout d'exploitation et de maintenance de plus;
- une complexite de rollback, d'observabilite et de debugging supplementaire;
- un risque de masquer un probleme amont encore mal cadre.

Le `no-go` retenu est donc fonde sur une disproportion actuelle entre:
- le cout / la latence / la complexite a ajouter;
- et le niveau de preuve disponible sur la necessite reelle du reranking.

La bonne lecture n'est pas:
- "un reranker ne servira jamais".

La bonne lecture est:
- "le reranker reste tardif, optionnel et non necessaire a ce stade; le dossier actuel ne justifie pas d'engager ce cout maintenant".

## 6. Quand reouvrir honnetement la question

La question reranker pourra etre rouverte plus tard seulement si plusieurs signaux convergent, par exemple:

- le panier pre-arbitre reste propre et borne, mais son ordre final demeure systematiquement mediocre sur le meme corpus de probes;
- le corpus live devient plus riche, notamment avec des `summaries` non vides et une lane `summaries` qui compte reellement en production;
- l'arbitre echoue de facon repetee a exploiter un panier pourtant propre;
- une comparaison avant/apres sur panier deja assaini montre qu'un reranker aurait une chance realiste d'etre proportionne;
- un budget de latence, un plan de rollback et une forme d'exploitation restent defendables apres cette preuve.

Tant que ces signaux ne sont pas reunis, il ne faut ni choisir un modele, ni choisir un provider, ni ouvrir un prototype "vite fait" pour forcer un `go`.

## 7. Consequence pour la suite du chantier

La consequence de cette decision est simple:

- la Phase `9D` est fermee proprement par un `no-go` documente;
- la question `go / no-go` etant maintenant tranchee, la Phase `10E` peut etre ouverte plus tard sans reranker retenu;
- ce patch n'ouvre cependant aucune implementation `10E`, aucune UI, aucun endpoint et aucun lot runtime supplementaire.

La decision utile ici est donc bien:

`reranker = no-go for now`
