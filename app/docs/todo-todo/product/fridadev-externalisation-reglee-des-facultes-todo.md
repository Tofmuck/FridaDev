# FridaDev - Externalisation reglee des facultes - TODO

Statut: actif
Classement: `app/docs/todo-todo/product/`
Nature: note de travail + roadmap de clarification architecturale
Portee: FridaDev comme noyau orchestrateur et externalisation progressive de certaines capacites

## Intention

Cette note formalise une orientation d'architecture pour FridaDev.

La question n'est pas d'abord:
- faut-il tout dockeriser ?
- faut-il tout transformer en microservices ?

La bonne question est:
- quelles fonctions doivent rester au centre ?
- quelles fonctions peuvent devenir des capacites externes sans disperser l'unite du systeme ?

La these de travail est la suivante:

```text
FridaDev doit rester une intelligence organisatrice centrale,
et externaliser progressivement certaines facultes specialisees
sous contrat stable.
```

## Partie 1 - Formulation philosophique

FridaDev ne doit pas devenir une federation de petits esprits souverains.

Il doit rester:
- le lieu de l'unite du jugement,
- le lieu de la continuite de la memoire,
- le lieu de la coherence de l'identite,
- le lieu de l'orchestration de l'action.

Autour de ce centre peuvent exister des puissances plus specialisees:
- documentation,
- transcription,
- synthese,
- arbitrage,
- validation,
- autres capacites futures.

Mais ces puissances doivent rester:
- des organes,
- non des sujets autonomes,
- des facultes deleguees,
- non des centres rivaux de coherence.

La formule directrice est donc:

```text
externaliser les fonctions,
conserver au centre l'unite du sens
```

Ou encore:

```text
deleguer les facultes,
ne pas disperser le sujet
```

## Partie 2 - Reformulation technique

### Principe architectural central

FridaDev reste le noyau.

Le noyau doit garder:
- la conversation,
- l'orchestration des tours,
- la memoire,
- l'identite canonique,
- la gouvernance runtime,
- l'administration applicative.

Les capacites externes doivent rester:
- remplacables,
- contractuelles,
- bornees,
- observables,
- subordonnees au noyau orchestrateur.

### Distinction structurante

#### 1. Le centre

Le centre est ce qui porte:
- la continuite dialogique,
- la memoire vive et durable,
- l'identite canonique,
- la responsabilite du dernier arbitrage,
- la coherence de l'ensemble.

Dans l'etat actuel, ce centre est FridaDev lui-meme.

#### 2. Les facultes deleguees

Une faculte delegatee est une capacite specialisee qui:
- prend une entree structuree,
- applique une operation determinee,
- retourne une sortie structuree,
- ne decide pas du sens global du systeme.

Une faculte delegatee ne doit pas:
- devenir source de verite canonique a la place du noyau,
- ecrire seule dans la memoire sans contrat explicite,
- redefinir la doctrine du systeme,
- imposer sa propre orchestration generale.

### Regle d'externalisation

Une capacite ne doit sortir du noyau que si sa frontiere est deja claire.

Conditions d'externalisation:
- sa fonction est bien delimitee;
- son contrat d'entree/sortie est stable;
- elle peut etre evaluee independamment;
- elle n'endommage pas l'unite du jugement central;
- sa sortie peut etre refusee, corrigee ou ignoree par le noyau;
- son extraction simplifie vraiment la lisibilite du systeme.

Si ces conditions ne sont pas remplies, la capacite doit rester interne.

### Contrat type d'une capacite externe

Toute capacite externe devrait tendre vers le meme contrat minimal:
- entree JSON explicite,
- sortie JSON versionnee,
- modele effectivement utilise,
- timeout explicite,
- trace_id / conversation_id,
- reason codes stables,
- mode local ou HTTP interchangeable,
- observabilite simple,
- possibilite de fallback.

Formule cible:

```text
meme interface logique,
deux modes possibles:
- local
- HTTP
```

### Cartographie provisoire

#### A. Ce qui doit rester au centre pour l'instant

A garder dans FridaDev:
- orchestration du chat,
- memoire et persistence,
- write-paths memoire,
- identite canonique,
- extraction identitaire,
- mutable rewriter,
- arbitrage d'ecriture,
- gouvernance runtime,
- administration applicative.

Raison:
ces elements touchent encore trop directement a l'unite hermeneutique du systeme.

#### B. Ce qui est candidat a une externalisation progressive

Bons candidats:
- module documentaire,
- STT,
- TTS,
- summarizer,
- validation agent,
- stimmung agent,
- eventuellement arbiter, plus tard.

Raison:
ces modules ressemblent davantage a des facultes specialisees:
- input structure,
- traitement borne,
- output structure.

#### C. Cas special de l'arbiter

L'arbiter est un bon candidat futur, mais pas immediat.

Pourquoi:
- il a deja une frontiere relativement claire;
- mais il reste encore lie a la qualite du retrieval et au panier de candidats;
- l'extraire trop tot risquerait de figer une frontiere encore immature.

Conclusion provisoire:
- preparer un futur `arbiter-service`;
- mais ne l'extraire qu'apres clarification du pipeline memoire/RAG.

## Anti-pattern a eviter

Ne pas viser:
- une micro-fragmentation prematuree,
- une multiplication de services mal definis,
- des modules externes qui reconstituent chacun leur propre logique globale,
- une architecture ou la responsabilite devient illisible,
- une balkanisation fonctionnelle.

Symptomes de mauvais decoupage:
- doublons de verite,
- logique distribuee sans centre clair,
- contrats implicites,
- dependances circulaires,
- debuggage impossible sans replay systemique complet.

## Trajectoire recommandee

### Phase 1 - Cartographier les ports internes

Identifier les vraies frontieres logiques:
- qui appelle quoi,
- avec quelle entree,
- pour quelle sortie,
- avec quelle responsabilite.

### Phase 2 - Stabiliser des interfaces internes

Definir pour chaque capacite candidate:
- schema d'entree,
- schema de sortie,
- erreurs,
- timeouts,
- fallback,
- observabilite.

### Phase 3 - Introduire un adapter local|http

Objectif:
- garder exactement la meme logique metier,
- mais permettre une execution soit locale, soit distante,
- sans changer l'orchestration centrale.

### Phase 4 - Extraire un premier candidat borne

Ordre plausible:
1. module documentaire
2. STT/TTS si deja API
3. puis, eventuellement, arbiter
4. autres facultes ensuite

### Phase 5 - Convergence contractuelle

Faire converger les capacites externes vers une meme discipline:
- contrats homogenes,
- traces homogenes,
- timeouts homogenes,
- supervision lisible.

## Regle de souverainete du noyau

Le noyau FridaDev doit toujours garder:
- la decision d'utiliser ou non une capacite,
- la decision d'accepter ou non son resultat,
- la synthese finale,
- la responsabilite du sens,
- la coherence de la memoire et de l'identite.

Autrement dit:
une capacite externe produit un resultat,
mais FridaDev garde le jugement de dernier ressort.

## Decision de travail retenue

Orientation retenue:

```text
FridaDev = orchestrateur + memoire + identite + admin
Capacites externes = services specialises a contrat stable
```

Donc:
- oui a une modularisation progressive,
- oui a des services externes bien bornes,
- non a l'eclatement premature du coeur du systeme.

## Question directrice pour chaque extraction future

Avant d'extraire un module, poser toujours cette question:

```text
est-ce que cette extraction clarifie une faculte,
ou est-ce qu'elle disperse le sujet ?
```

Si elle clarifie une faculte:
- extraire est legitime.

Si elle disperse le sujet:
- il faut garder la fonction au centre.

## TODO actif

- [ ] Cartographier les frontieres internes actuelles de FridaDev par capacite.
- [ ] Identifier les ports internes qui pourraient avoir un adapter `local|http` sans changer la logique metier.
- [ ] Distinguer explicitement ce qui doit rester dans le noyau et ce qui peut devenir service externe.
- [ ] Produire un premier schema cible `noyau + capacites externes` pour le module documentaire, STT/TTS et un futur arbiter-service.
- [ ] Definir un contrat minimal commun pour toute capacite externalisee.
- [ ] Verifier que cette trajectoire reste compatible avec le chantier memoire/RAG en cours.

## Note finale

L'objectif n'est pas la modernite formelle de l'architecture.

L'objectif est:
- la lisibilite,
- la stabilite,
- la responsabilite,
- l'evolutivite,
- et la conservation de l'unite hermeneutique de FridaDev.
