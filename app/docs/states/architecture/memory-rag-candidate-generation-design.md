# Memory RAG - design du candidate generation - 2026-04-10

Statut: reference active
Classement: `app/docs/states/architecture/`
Portee: design du candidate generation memoire/RAG avant tout lot d'implementation V2
Roadmap liee: `app/docs/todo-todo/memory/memory-rag-relevance-todo.md`
Baseline liee: `app/docs/states/baselines/memory-rag-relevance-baseline-2026-04-10.md`
Cartographie liee: `app/docs/states/architecture/memory-rag-current-pipeline-cartography.md`

## 1. Objet

Cette note ferme la Phase 2 du chantier `memory-rag-relevance`.

Elle tranche, sans patch runtime:
- les lanes de candidate generation qui meritent d'etre etudiees;
- la strategie recommandee pour le premier lot d'implementation;
- les alternatives rejetees;
- la place de la recence, de la lane `assistant`, de la lane `summaries` et de la reformulation de query;
- les dependances minimales pour tester un recall plus large sans toucher au reranker.

Elle ne fait pas:
- le design du panier pre-arbitre cible;
- le design complet de la deduplication;
- l'ouverture de la voie `summaries` live;
- la decision reranker;
- un prototype de V2.

## 2. Methode et preuves relues

Sources retenues:
- code du depot;
- baseline Phase 0;
- cartographie Phase 1;
- tests existants sur le retrieval et les contrats canoniques;
- runtime OVH en lecture seule.

Comparaisons runtime relues pour cette phase:
- `global_top10`: top vectoriel global sur `traces`;
- `user_top5`: top vectoriel borne a `role='user'`;
- `assistant_top5`: top vectoriel borne a `role='assistant'`;
- `best_per_conv_top5`: meilleur item par conversation, trie ensuite par score;
- `recent_72h_top5`: top vectoriel borne aux `72` dernieres heures.

Probes relus:
- `architecture modules externes arbiter STT TTS`
- `qui suis-je pour toi maintenant identite durable`
- `preferences utilisateur durables style reponse`
- `OVH migration Authelia Caddy Docker`
- `contexte circonstanciel recent ce soir fatigue`

Contraintes factuelles toujours actives:
- le retrieval live interroge `traces` seulement;
- `MEMORY_TOP_K=5` aujourd'hui;
- `summaries=0` en live;
- la baseline Phase 0 montre un probleme de composition avant un probleme de profondeur;
- la cartographie Phase 1 montre que l'arbitre voit encore un payload plat et ne doit pas etre retouche dans le lot suivant.

## 3. Contraintes de design pour la Phase 2

- Le premier lot d'implementation doit rester borne au candidate generation.
- Il ne doit pas changer le schema du panier arbitre, les seuils arbitre ni le prompt final.
- Il doit pouvoir etre evalue via le corpus de probes Phase 0, sans reranker.
- Il doit traiter le biais de composition observe en Phase 0 sans pretendre regler deja toute la dedup Phase 3.
- Il ne doit pas faire semblant que la voie `summaries` est exploitable alors qu'elle est vide en live.

## 4. Lanes candidates etudiees

### 4.1 Lane `traces` globale actuelle

Objectif:
- conserver un filet de rappel semantique general qui ne depend pas d'une hypothese trop forte sur le role ou le type de souvenir.

Souvenirs vises:
- tout souvenir semantiquement proche, quel que soit son role.

Risque principal:
- saturation par des reponses `assistant` generiques, procedurales ou auto-referentielles;
- absence de garde-fou de composition;
- collisions nombreuses entre items quasi redondants.

Signal attendu pour dire qu'elle aide:
- des candidats utiles qui ne seraient recuperes par aucune lane specialisee;
- une meilleure couverture brute quand le top global actuel coupe trop vite.

Preuves relues:
- probe `architecture...`: `global_top10` = `10 assistant / 0 user`;
- probe `OVH migration...`: `global_top10` = `7 assistant / 3 user`, avec bruit parasite de validation et d'identifiant technique;
- probe `contexte...`: `global_top10` = `9 assistant / 1 user`.

Verdict:
- lane necessaire comme filet de securite;
- insuffisante seule pour le premier lot.

### 4.2 Lane `user` dediee

Objectif:
- remonter explicitement les traces utilisateur qui ont le plus de chance de porter des preferences durables, des faits identitaires ou des indications operatoires posees par l'utilisateur.

Souvenirs vises:
- identite;
- preferences de style;
- faits utilisateur durables;
- contraintes exprimees par l'utilisateur.

Risque principal:
- duplication exacte de questions utilisateur;
- questions de travail ponctuelles confondues avec de la memoire durable;
- traces lexicalement proches mais pauvres semantiquement.

Signal attendu pour dire qu'elle aide:
- une meilleure presence de faits utilisateur dans le pool brut sans attendre la Phase 3;
- moins de dependance au hasard d'un top global assistant-heavy.

Preuves relues:
- probe `qui suis-je...`: la lane `user` remonte bien le versant identitaire, mais sature en doublons exacts `Qui suis-je pour toi maintenant ?`;
- probe `preferences...`: le global actuel est deja majoritairement `user` (`8/10`), ce qui confirme qu'une lane `user` peut porter des souvenirs pertinents, mais aussi des requetes generiques et repetitives.

Verdict:
- lane utile et vraisemblablement necessaire dans le premier lot;
- lane non suffisante seule a cause des doublons et du bruit utilisateur.

### 4.3 Lane `assistant` dediee

Objectif:
- ne pas perdre les rares traces `assistant` qui portent une explication systeme, un cadrage architectural ou un rappel utile qui n'existe pas cote `user`.

Souvenirs vises:
- explications systeme;
- reponses architecturales deja formulees;
- rappels operationnels derives par l'assistant.

Risque principal:
- reponses verboses, procedurales ou generiques;
- saturation par du texte `assistant` presentable mais peu utile;
- effet de masque sur les faits utilisateur.

Signal attendu pour dire qu'elle aide:
- recuperer un petit nombre d'items `assistant` clairement sur l'axe, absents du top `user`.

Preuves relues:
- probe `architecture...`: la dominance `assistant` ne prouve pas l'utilite; elle montre surtout que le global actuel laisse les traces `assistant` occuper tout l'espace;
- probe `contexte...`: meme quand un sujet parait recent, la lane `assistant` remonte surtout des reponses circonstancielles et de presse;
- probe `OVH migration...`: la lane `assistant` remonte surtout du texte de validation et de reformulation.

Verdict:
- lane a garder comme backfill borne;
- a plafonner par defaut;
- pas de parite `assistant=user` dans le premier lot.

### 4.4 Lane recence / diversite conversationnelle

Objectif:
- reduire l'effet d'inondation par une meme conversation;
- recuperer au besoin un peu de contexte recent sans ecraser la memoire durable.

Souvenirs vises:
- contexte tres recent;
- couverture de conversations plus diverse;
- limitation des floods venant d'un meme echange.

Risque principal:
- la recence pure remonte du bruit local plutot qu'un souvenir utile;
- la diversite par conversation ne traite pas les doublons exacts presents dans plusieurs conversations.

Signal attendu pour dire qu'elle aide:
- moins de saturation par une seule conversation dans le pool brut;
- un appoint recent utile sur les probes circonstanciels.

Preuves relues:
- probe `qui suis-je...`: `recent_72h_top5` perd le coeur des souvenirs identitaires et remonte surtout des traces recentes non decisives;
- probe `architecture...`: `best_per_conv_top5` reste entierement `assistant` et ne regle donc pas le biais principal;
- probe `qui suis-je...`: `best_per_conv_top5` conserve encore quatre fois le meme enonce utilisateur exact, ce qui montre que la diversite conversationnelle seule ne remplace pas la future dedup Phase 3.

Verdict:
- utile seulement comme heuristique secondaire de merge;
- non recommandee comme lane principale autonome du premier lot.

### 4.5 Lane `summaries` future

Objectif:
- offrir plus tard une voie de souvenirs plus condenses et plus durables.

Souvenirs vises:
- resumes parentaux;
- memoire de plus long terme.

Risque principal:
- voie fictive en live tant que `summaries=0`;
- impossibilite d'evaluer correctement son apport sur OVH aujourd'hui.

Signal attendu pour dire qu'elle aide:
- gain de couverture utile sur probes deja difficiles, sans injection double.

Preuves relues:
- `summaries=0`;
- `summary_id` absent dans les probes live;
- `parent_summary` nul en pratique sur le runtime observe.

Verdict:
- lane explicitement future;
- bloquee live pour le premier lot.

## 5. Comparaison des options plausibles

### Option A - augmenter seulement le `top_k` global

Interet:
- changement simple a implementer et a tester.

Limite majeure:
- ne corrige pas la composition du recall;
- ne reserve aucun espace aux faits `user`;
- laisse le global assistant-heavy dominer sur `architecture`, `OVH` et `contexte`.

Verdict:
- rejetee comme strategie suffisante pour le lot A.

### Option B - union multi-lanes bornee avec caps par role

Interet:
- garde un filet global;
- reserve de la place a la lane `user`;
- permet de garder un petit filet `assistant` sans lui donner la parite;
- peut etre evaluee avant tout redesign du panier arbitre.

Limite:
- ne traite pas encore toute la dedup;
- demande une discipline claire de merge et de mesure.

Verdict:
- option recommandee.

### Option C - parite stricte `user` / `assistant`

Interet:
- symetrie simple a expliquer.

Limite majeure:
- les probes relus ne justifient pas de reserver autant de place a `assistant` qu'a `user`;
- forte probabilite de bruit `assistant` generique.

Verdict:
- rejetee pour le premier lot.

### Option D - lane de recence autonome des le premier lot

Interet:
- peut aider sur les souvenirs tres locaux et circonstanciels.

Limite majeure:
- les preuves relues montrent qu'une recence borne seule degrade les cas d'identite durable et ne resout pas le bruit `assistant`.

Verdict:
- rejetee comme lane principale du premier lot;
- conservee seulement comme heuristique secondaire possible.

### Option E - reformulation de query des le premier lot

Interet:
- pourrait, en theorie, mieux aligner certaines requetes floues.

Limite majeure:
- ajoute une nouvelle source de variabilite et potentiellement un nouvel appel modele;
- risque de masquer un probleme d'equilibrage de lanes encore non traite;
- non necessaire pour tester un recall plus large a ce stade.

Verdict:
- hors scope du premier lot.

## 6. Strategie recommandee pour le futur lot A

Strategie retenue:
- une union multi-lanes bornee composee de:
  - une lane globale un peu plus large que le `top_k=5` actuel, utilisee comme filet de rappel;
  - une lane `user` dediee avec une reservation explicite;
  - une lane `assistant` de backfill avec cap strict inferieur a la lane `user`;
  - une heuristique legere de diversite conversationnelle au moment du merge, sans pretendre encore faire la dedup Phase 3.

Ce que cette strategie cherche a corriger tout de suite:
- l'absence de reservation explicite pour les souvenirs cote `user`;
- la saturation `assistant` observee sur plusieurs probes;
- la coupure trop precoce du recall global quand le top `5` porte deja du bruit.

Ce qu'elle ne pretend pas regler dans le lot A:
- la dedup exacte et quasi-doublon complete;
- le schema cible du panier arbitre;
- le traitement complet des collisions trace/summary;
- la qualite d'un reranker.

## 7. Regles de decision explicites pour les questions difficiles

### 7.1 Traces `assistant`: cap, penalite, parite

Decision Phase 2:
- dans le premier lot, les traces `assistant` doivent etre gardees avec cap strict;
- elles peuvent etre penalisees au moment du merge si la lane globale est deja majoritairement `assistant`;
- elles ne doivent pas etre a parite avec `user` par defaut.

Raison:
- les probes `architecture`, `OVH` et `contexte` montrent deja que le recall actuel sur-selectionne `assistant`;
- rien, dans les preuves relues, ne justifie de lui reserver la moitie du pool brut.

Exception eventuelle plus tard:
- une parite ou un relachement du cap ne devrait etre reconsidere qu'apres mesures post-lot A sur probes systeme, pas avant.

### 7.2 Recence sans ecraser la memoire durable

Decision Phase 2:
- ne pas ouvrir une vraie lane de recence autonome dans le premier lot;
- au mieux, utiliser la recence comme appoint secondaire ou critere de tie-break dans un pool deja semantiquement borne.

Raison:
- `recent_72h_top5` sur `qui suis-je...` degrade le rappel identitaire;
- la recence aide a retrouver du contexte local, mais pas a elle seule un souvenir durable.

### 7.3 Reformulation de query

Decision Phase 2:
- la reformulation de query reste hors scope du premier lot.

Raison:
- le probleme dominant relu en Phase 0 et confirme ici est la composition des candidats;
- introduire une reformulation maintenant compliquerait la lecture des gains et des regressions.

## 8. Dependances minimales pour tester un recall plus large sans reranker

Le futur lot A peut rester borne au candidate generation si:
- il garde l'arbitre, ses seuils et son interface d'entree inchanges;
- il compare le corpus canonique Phase 0 avant/apres sur le pool brut pre-arbitre;
- il archive au minimum, pour chaque probe:
  - composition par role;
  - composition par conversation;
  - apercu des duplications les plus visibles;
  - provenance de lane dans les artefacts de comparaison, sans encore figer le schema Phase 3;
- il ne depend ni d'une lane `summaries` live ni d'un reranker.

Ce qui n'est pas requis pour ouvrir le lot A:
- un redesign complet du panier arbitre;
- une nouvelle politique de seuils;
- une reformulation de query;
- un reranker.

## 9. Pourquoi le lot suivant peut rester borne au candidate generation

La recommendation ci-dessus reste bien un sujet Phase 2 parce qu'elle modifie seulement:
- quelles lanes de retrieval sont sollicitees;
- comment leurs sorties brutes sont mergees;
- comment on borne mieux le pool avant l'arbitre.

Elle ne tranche pas encore:
- le schema canonique cible du panier pre-arbitre;
- la cle stable de dedup;
- la place exacte de `parent_summary` dans un futur panier enrichi;
- les regles de fusion `traces + summaries`.

Ces sujets restent explicitement reserves a la Phase 3 puis a la Phase 4.

## 10. Decision de cloture Phase 2

Decision retenue:
- fermer la Phase 2 avec une strategie recommandee claire:
  - `global` plus large comme filet;
  - lane `user` reservee;
  - lane `assistant` capee;
  - diversite conversationnelle legere comme heuristique secondaire;
  - pas de lane `summaries` live;
  - pas de reformulation de query;
  - pas de reranker.

Alternative explicitement rejetee:
- augmenter seulement le `top_k` global.

Alternatives aussi rejetees a ce stade:
- parite stricte `user` / `assistant`;
- lane de recence autonome des le lot A;
- reformulation de query des le lot A.

Ce que cette phase debloque:
- un futur lot A d'implementation borne au candidate generation.

Ce qu'elle ne debloque pas encore:
- la Phase 3 de schema panier et dedup;
- la Phase 4 `summaries`;
- la Phase 9 reranker.
