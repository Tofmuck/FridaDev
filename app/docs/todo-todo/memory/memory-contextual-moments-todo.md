# Memory - memoire de moment contextuel - TODO de cadrage

Statut: brouillon de cadrage actif
Classement: `app/docs/todo-todo/memory/`
Portee: cadrage philosophique et technique d'une couche memoire autonome de `moments contextuels`, distincte des traces, des summaries, de la stimmung et des identities
Etat runtime vise: aucun patch runtime dans ce document
References liees:
- `app/docs/states/architecture/memory-rag-current-pipeline-cartography.md`
- `app/docs/states/specs/memory-rag-summaries-lane-contract.md`
- `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- `app/docs/todo-todo/memory/hermeneutical-add-todo.md`

## 1. Objet

Ce document ouvre un chantier distinct du recall memoire/RAG courant.

Il ne part pas de l'idee suivante:
- ajouter une nouvelle lane de retrieval de plus;
- remplacer l'arbitre memoire actuel;
- remplacer le summary;
- remplacer la stimmung;
- remplacer les identities.

Il part d'une autre hypothese:

- certaines suites de tours finissent par former un `moment signifiant`;
- ce moment n'est ni un simple fait, ni un simple resume narratif, ni une simple tonalite, ni un simple trait identitaire;
- il peut donc meriter un objet memoire propre;
- cet objet doit etre produit de maniere asynchrone, a partir d'un espace de traces chronologique;
- cet objet doit ensuite rester subordonne au systeme memoire souverain de Frida.

## 2. Point de depart dans le code actuel

Le systeme courant dispose deja de plusieurs couches distinctes.

### 2.1 Traces

Les `traces` restent aujourd'hui la matiere premiere principale du recall.

Elles sont:
- stockees comme unites locales de ce qui s'est dit;
- interrogees par le retrieval hybride dense + lexical;
- bornees puis dedupees avant arbitre.

### 2.2 Summaries

Les `summaries` existent comme compression temporelle de sequences de messages.

Leur logique actuelle est:
- dependante d'un seuil de summarization;
- dependante d'une fenetre de messages/tokens;
- ancree par `start_ts` / `end_ts`;
- eventuellement rejointe plus tard a une trace via `summary_id` ou `parent_summary`.

Le summary reste donc une forme de memoire narrative et temporelle.

### 2.3 Stimmung

La `stimmung` actuelle est une lecture processuelle du tour et de la fenetre recente.

Elle sert a:
- qualifier une tonalite dominante;
- decrire une stabilite ou un deplacement tonal;
- alimenter le jugement hermeneutique du tour courant.

Elle ne doit pas etre requalifiee en memoire de moment.

### 2.4 Identities

Les `identities` actuelles stabilisent:
- des traits de soi;
- des traits de Frida;
- des modulations mutables de la relation;
- des distinctions durable / episodic / situation / mixed.

Elles ne doivent pas absorber la memoire de moment, au risque de psychologiser ou d'essentialiser des configurations qui relevent en fait d'un moment dialogue.

## 3. These philosophique retenue

Le summary et la memoire de moment ne doivent pas etre confondus.

La distinction la plus utile est la suivante:

- le `summary` depend d'une fenetre de tokens et produit deja une lecture narrative et interpretative de cette fenetre;
- la `memoire de moment` depend d'une fenetre de signifiance, ancree dans un espace de traces chronologique, et produit une qualification de saillance dialogique.

Formulation courte:

- `summary` = "voici la lecture narrative et interpretative qui se degage d'une fenetre de tokens"
- `memoire de moment` = "voici le type de moment qui a eu lieu dans une fenetre de signifiance"

Point important:

- la fenetre du `summary` et la fenetre du `moment` ne doivent pas etre presumees identiques;
- elles peuvent se chevaucher, mais elles ne se confondent pas par principe;
- le `summary` est regle par une logique de compression narrative;
- le `moment` est regle par une logique de seuil de signifiance.

Consequence directe:

- si la memoire de moment raconte mieux un segment deja resume, elle fait doublon;
- si elle qualifie un evenement hermeneutique ou une saillance dialogique, elle a une place propre.

## 4. Place propre de la memoire de moment

Cette couche doit rester distincte des autres objets memoire.

### 4.1 Ce qu'elle n'est pas

Elle n'est pas:
- un nouveau nom pour `summary`;
- un nouveau nom pour `stimmung`;
- un nouveau nom pour `identity mutable narrative`;
- un nouveau RAG de second rang;
- un graph de faits;
- un moteur souverain qui deciderait seul ce qui doit etre injecte.

### 4.2 Ce qu'elle est

Elle est:
- une memoire de `moment signifiant`;
- derivee asynchronement d'un paquet chronologique de traces;
- classee par type principal de moment;
- coloree par quelques dimensions secondaires;
- presentable ensuite a l'arbitre comme un objet memoire distinct.

### 4.3 Typologie initiale minimale des moments

Types principaux proposes pour un premier lot:
- `ouverture`
- `elucidation`
- `bascule`
- `devoilement`
- `tension`
- `stabilisation`

Dimensions secondaires possibles:
- dominante `hermeneutique`
- dominante `enonciative`
- dominante `tonale`
- dominante `relationnelle`
- `intensite`

Principe de sobriete:
- peu de types principaux;
- quelques dimensions secondaires;
- aucune inflation taxonomique.

## 5. Principe architectural retenu

La bonne forme n'est pas une lane synchrone de plus dans le hot path.

La bonne forme est un module autonome, asynchrone, qui:
- lit les conversations et/ou traces deja persistees;
- maintient un espace de travail chronologique borne;
- laisse operer une decantation de signifiance;
- ne cristallise un objet `moment` qu'au franchissement d'un seuil suffisant;
- persiste ensuite cet objet dans sa propre couche;
- ne revient vers Frida qu'en aval, par integration explicite et future.

Autrement dit:
- il recupere des informations depuis les conversations;
- il n'est pas la conversation;
- il ne remplace aucune couche memoire existante;
- il travaille a part.

## 6. Invariants de non-contradiction avec le code actuel

Pour rester coherent avec l'etat present du depot, les invariants suivants doivent etre fixes des maintenant.

### 6.1 Invariants de frontiere

Le module de memoire de moment ne doit pas:
- modifier la query de retrieval memoire actuelle, qui reste centree sur `user_msg`;
- modifier le retrieval hybride `traces` / lexical / dense existant;
- modifier le contrat actuel des `summaries`;
- modifier la stimmung du tour courant;
- modifier les identities durables ou mutables;
- injecter quoi que ce soit directement dans le prompt principal sans passer par les frontieres memoire normales.

### 6.2 Invariants de stockage

Le module de memoire de moment ne doit pas:
- surcharger la table `summaries`;
- ecrire des pseudo-moments dans `identities`;
- reutiliser `identity_evidence` pour un autre usage;
- transformer `parent_summary` en pseudo-memoire de moment.

Il doit avoir sa propre famille d'objets et, a terme, sa propre persistence.

### 6.3 Invariants de temporalite

La formation d'un moment doit rester:
- ancree dans un espace de traces chronologique;
- bornee par une fenetre temporelle identifiable;
- rattachee a des traces sources explicites;
- impossible a construire par collage arbitraire de morceaux eloignes sans justification.

## 7. Forme cible minimale de l'objet `moment`

Sans figer encore le schema DB final, l'objet logique minimal devrait porter au moins:

- `moment_id`
- `conversation_id`
- `start_ts`
- `end_ts`
- `source_trace_ids`
- `moment_type`
- `dominant_axes`
- `intensity`
- `significance_score`
- `short_label`
- `interpretive_note`
- `decision_source`
- `status`

Contraintes:
- `source_trace_ids` doit toujours rester non vide;
- `start_ts <= end_ts`;
- `moment_type` doit venir d'une taxonomie bornee;
- `interpretive_note` doit rester courte et non narrative;
- `status` doit permettre au minimum `candidate | accepted | rejected | stale`.

## 8. Pipeline technique minimal envisage

### 8.1 Phase A - incubation asynchrone

Un worker ou agent de fond lit:
- les conversations recentes persistees;
- ou un flux de traces deja ecrites;
- ou les deux.

Il constitue des fenetres candidates de traces chronologiquement coherentes.

### 8.2 Phase B - calcul de signifiance

Sur chaque fenetre candidate, il peut combiner:
- heuristiques de recurrence locale;
- stabilite ou inflexion de tonalite;
- marqueurs de bascule enonciative ou hermeneutique;
- densite de references croisantes;
- eventuellement embeddings ou classification LLM/agent.

Principe retenu:
- la memoire de moment n'est pas brute;
- elle est le resultat d'un travail de structuration.

### 8.3 Phase C - cristallisation

Quand la fenetre atteint un seuil suffisant de signifiance:
- un objet `moment` est produit;
- il reste lie a ses traces sources;
- il reste distingue d'un summary;
- il est persiste dans sa couche propre.

### 8.4 Phase D - presentation future a Frida

Dans un lot ulterieur seulement, un `moment` accepte pourrait devenir:
- soit une lane memoire distincte en amont de `memory_retrieved`;
- soit une surface read-only pour l'operateur;
- soit une source auxiliaire presentee au pre-panier.

Ce document ne tranche pas encore cette integration finale.

## 9. Module autonome vise

Le module doit etre pense comme autonome dans `app/memory/`.

Direction de rangement recommandee:

```text
app/memory/moment_memory/
```

avec, a terme, des frontieres explicites du type:
- `collector.py`
- `significance.py`
- `classifier.py`
- `store.py`
- `read_model.py`
- `contracts.py`

Ce decoupage rappelle un principe simple:
- la memoire de moment consomme des informations du systeme;
- elle n'est pas confondue avec le retrieval RAG actuel;
- elle n'est pas confondue avec l'identite;
- elle n'est pas confondue avec la stimmung.

## 10. Place possible d'un agent de fond

Il est legitime d'envisager un agent de fond specialise si, et seulement si, son role reste borne.

Role possible:
- classifier ou qualifier des fenetres de traces candidates;
- proposer un type de moment;
- produire une note interpretative courte;
- attribuer un score de signifiance.

Role interdit:
- decider seul de l'injection finale dans Frida;
- remplacer l'arbitre memoire existant;
- requalifier les identities;
- raconter librement la conversation comme un summary concurrent.

## 11. Ce qu'il ne faut pas faire

Ne pas:
- faire une deuxieme machine narrative concurrente des summaries;
- faire de la memoire de moment une stimmung grossie;
- faire de la memoire de moment une identity deguisee;
- brancher cette couche directement sur le prompt principal avant d'avoir fixe ses invariants;
- casser la lisibilite architecturale actuelle du pipeline memoire.

## 12. Premiere definition of done documentaire

Ce brouillon sera juge suffisamment propre pour ouvrir un lot de conception plus concret si les points suivants sont stabilises:

- la distinction philosophique `summary` / `moment` est tenue;
- la frontiere avec `stimmung` est tenue;
- la frontiere avec `identity` est tenue;
- le caractere asynchrone et autonome du module est explicite;
- la dependence a un espace de traces chronologique est explicite;
- l'absence de contradiction avec le retrieval memoire actuel est explicite.

## 13. Questions encore ouvertes

- quel est le meilleur support de calcul de signifiance: heuristique, embeddings, agent dedie, ou combinaison minimale?
- un `moment` doit-il etre rattache a une seule conversation, ou peut-il plus tard etre promu en objet trans-conversationnel?
- faut-il une lane de recall `moments` distincte, ou une presentation seulement en surface d'arbitrage?
- a partir de quel seuil de rarete accepte-t-on qu'un moment soit digne d'etre persiste?
- comment mesurer qu'un moment apporte plus qu'un summary sans refaire simplement un summary plus elegant?

## 14. Decision provisoire retenue

Decision provisoire de ce brouillon:

- oui a une `memoire de moment contextuel`;
- non comme extension immediate du summary;
- non comme variation de la stimmung;
- non comme surcouche identity;
- oui comme module autonome, asynchrone, produit a partir d'un espace de traces chronologique et d'un seuil de signifiance;
- oui seulement si son objet propre reste la qualification d'un moment signifiant et non la repetition narrative de ce qui est deja raconte ailleurs.
