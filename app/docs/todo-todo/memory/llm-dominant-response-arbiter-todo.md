# LLM-Dominant Response Arbiter - TODO

Statut: ouvert
Classement: `app/docs/todo-todo/memory/`
Portee: architecture de l'arbitrage de reponse du pipeline hermeneutique
Nature: TODO d'architecture actif, lotable, auditable et anti-confusion

Source normative du lot 1:

- `app/docs/states/specs/response-arbiter-power-contract.md`

## Pourquoi ce document existe

Ce document reste le TODO actif unique pour la bascule vers un arbitre de reponse LLM dominant sous garde-fous.

Il n'ouvre pas un chantier parallele.
Il n'ouvre pas non plus un patch runtime cache.

Il existe parce que le probleme principal n'est plus un simple probleme de seuil heuristique.
Le probleme principal est un probleme de pouvoir institutionnel dans la chaine de reponse:

- l'amont heuristique a pris trop de pouvoir souverain;
- le `validation_agent` lit deja une matiere dialogique plus riche, mais trop tard et avec un droit de decision trop faible;
- des micro-corrections locales ont deplace certains symptomes sans clarifier noir sur blanc qui tranche vraiment.

Ce document sert donc de source de verite active pour:

- expliciter les decisions deja tranchees;
- decrire l'architecture cible;
- borner ce qui reste non cassable;
- decouper l'implementation en lots a cases a cocher.

La doctrine normative du lot 1 ne vit plus seulement ici.
Elle est maintenant fixee dans `app/docs/states/specs/response-arbiter-power-contract.md`.
Ce TODO reste la roadmap active du chantier.

## Intention operateur

Le signal operateur "J'en ai marre" doit etre lu ici comme un constat operatoire fort:

- trop de temps a ete perdu en TODO flous ou insuffisamment tranches;
- trop de corrections locales ont degrade la lisibilite du pouvoir d'arbitrage;
- il faut maintenant un document qui n'oublie rien de ce qui est deja decide;
- l'implementation future doit etre pilotable sans dependre de la memoire de la conversation.

## Source grounding

Ancrages code/doc/tests ayant motive ce TODO:

- `app/core/chat_service.py`
- `app/core/chat_prompt_context.py`
- `app/prompts/main_hermeneutical.txt`
- `app/prompts/validation_agent.txt`
- `app/core/hermeneutic_node/inputs/user_turn_input.py`
- `app/core/hermeneutic_node/doctrine/judgment_posture.py`
- `app/core/hermeneutic_node/doctrine/output_regime.py`
- `app/core/hermeneutic_node/doctrine/source_conflicts.py`
- `app/core/hermeneutic_node/doctrine/source_priority.py`
- `app/core/hermeneutic_node/runtime/primary_node.py`
- `app/core/hermeneutic_node/validation/validation_agent.py`
- `app/observability/chat_turn_logger.py`
- `app/observability/hermeneutic_node_logger.py`
- `app/tests/unit/core/hermeneutic_node/inputs/test_user_turn_input.py`
- `app/tests/unit/core/hermeneutic_node/runtime/test_primary_node.py`
- `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py`
- `app/tests/unit/logs/test_chat_turn_logger_phase2.py`
- `app/tests/test_server_phase14.py`
- `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- `app/docs/states/specs/hermeneutic-node-output-regime-contract.md`
- `app/docs/states/specs/hermeneutic-node-user-demand-contract.md`
- `app/docs/states/specs/response-arbiter-power-contract.md`
- `app/docs/todo-done/notes/low-ambiguity-over-clarification-closure.md`
- `app/docs/todo-done/notes/web-reading-truth-todo.md`

Comparaison conceptuelle utile seulement:

- `app/memory/arbiter.py`

Le memory arbiter reste hors scope de ce chantier.
Il sert seulement de point de comparaison institutionnel: un LLM y arbitre deja un panier structure plutot que d'arriver comme simple correcteur tardif.

## 1. Probleme architectural actuel

### 1.1 Chaine initiale de pouvoir avant lot 2

Avant le lot 2 runtime, la chaine de pouvoir etait essentiellement la suivante:

1. `chat_service` construisait `recent_window_input`, `user_turn_input` et `user_turn_signals`.
2. `primary_node` produisait deja un `primary_verdict` structurant.
3. `build_judgment_posture()` convertissait toute ambiguite ou sous-determination active en `clarify`.
4. `build_output_regime()` convertissait trop facilement `judgment_posture != answer` en `discursive_regime = meta`.
5. `build_source_conflicts()` pouvait encore pousser une issue `clarify`.
6. `validation_agent` relisait ensuite le dossier, mais ne renvoyait encore qu'une `validation_decision`.
7. `_FINAL_POSTURE_BY_PRIMARY_AND_DECISION` remappait cette decision sur une posture deja preconstruite par le primaire.
8. `chat_prompt_context.build_hermeneutic_judgment_block()` projetait ensuite ce verdict deja remappe dans `[JUGEMENT HERMENEUTIQUE]`.

Depuis le lot 2:

- l'aval est effectivement souverain sur le verdict final;
- le bloc projete suit bien ce verdict final arbitral;
- la pression residuelle vient surtout de l'amont encore trop structurant, qui reste a requalifier dans les lots 3 et 4.

### 1.2 Pourquoi cela produisait de la surclarification et de la meta prematuree

Avant le lot 2:

- les signaux amont avaient une force quasi-decisionnelle;
- `judgment_posture` et `source_conflicts` pouvaient pousser trop vite vers `clarify`;
- `output_regime` restait trop couple a cette logique;
- le `validation_agent` n'avait pas encore un vrai contrat de verdict final.

Apres le lot 2, le point institutionnel central est traite.
Le probleme restant pour la suite du chantier est de requalifier l'amont comme couche conseillere sans rouvrir une souverainete mecanique masquee.

Le resultat institutionnel est:

- de la surclarification;
- de la meta prematuree;
- une perte de contractualite dialogique locale;
- une inflation de micro-correctifs heuristiques au lieu d'un vrai deplacement du pouvoir.

## 2. Decisions deja tranchees

Les points ci-dessous sont deja decides.
Ils ne sont pas ouverts a rediscussion dans ce TODO.

### 2.1 Souverainete de l'arbitre

Le `validation_agent` doit avoir le dernier mot sur la posture finale de reponse.

Son nom actuel pourra etre requalifie plus tard si besoin.
Mais l'institution cible est deja tranchee: c'est bien lui, renforce, qui doit devenir l'arbitre principal.

### 2.2 Statut de l'amont

L'amont garde une autorite reelle, mais non souveraine.

Il reste:

- conseiller;
- ponderant;
- indicatif;
- producteur d'alertes et de recommandations structurees.

Il informe le jugement final.
Il pese.
Mais il ne tranche plus a la place de l'arbitre.

### 2.3 Garde-fous durs

Seuls des garde-fous durs, rares et non cassables doivent pouvoir interdire `answer`.

Les heuristiques ordinaires n'en font pas partie.

Sous garde-fou dur:

- l'arbitre ne peut pas ignorer la contrainte;
- mais il garde la main pour choisir entre `clarify` et `suspend`.

### 2.4 Expression vernaculaire des limites

Quand un garde-fou dur s'active, la sortie ne doit pas forcer un discours meta-systemique.

La limite doit pouvoir etre exprimee de facon:

- vernaculaire;
- dialogique;
- locale;
- non metamodelisee.

La contrainte borne la reponse.
Elle n'impose pas a elle seule une sortie bureaucratique ni un discours meta.

### 2.5 Statut du regime `meta`

Le regime `meta` devient exceptionnel.

Il ne doit plus:

- etre une consequence mecanique de `clarify`;
- servir de regime pratique ordinaire de gestion des difficultes locales;
- s'activer par reflexe sur les difficultees dialogiques courantes.

### 2.6 Matiere principale de l'arbitre

L'arbitre doit etre pense comme un juge.

Sa matiere principale est une fenetre dialogique locale reelle.
L'hypothese de travail retenue pour le chantier est:

- 5 tours canonises;
- priorite absolue au tour utilisateur courant;
- priorite absolue au dernier message assistant;
- priorite forte aux tours immediatement precedents;
- le reste est secondaire et indiciaire.

### 2.7 Statut du reste du contexte

Les elements suivants restent secondaires:

- `user_turn_signals`
- posture proposee
- `output_regime` propose
- `source_conflicts`
- `identity`
- `memory`
- `summary`
- `web`
- `time`

Ils donnent des indices.
Ils peuvent peser.
Mais in fine, c'est le bon sens dialogique local qui tranche.

### 2.8 Priorite de lecture

Par defaut, l'arbitre doit privilegier:

- la lecture la plus naturelle du tour;
- la continuite dialogique locale;
- la reponse simple.

Il ne doit monter vers:

- `clarify`
- `suspend`
- `meta`

que si cette lecture naturelle echoue reellement.

### 2.9 Override observable

L'arbitre doit pouvoir casser explicitement une recommandation amont.

Cet override doit etre observable:

- en logs;
- avec une raison lisible;
- avec trace de ce qui a ete suivi ou casse.

Cette observabilite est indispensable pour que l'architecture reste auditable.

### 2.10 Verdict projete

Si l'arbitre tranche contre l'amont, c'est toujours le verdict final de l'arbitre qui doit etre projete dans `[JUGEMENT HERMENEUTIQUE]`.

Le bloc projete ne doit plus re-subordonner la sortie a une recommendation amont souveraine.

### 2.11 Sortie minimale cible

Le futur arbitre final doit produire directement au minimum:

- `final_judgment_posture`
- `final_output_regime`
- la trace des garde-fous appliques
- la trace des recommandations amont suivies ou cassees

La forme technique exacte du schema reste a fixer dans le lot de contrat.
Mais cette matiere minimale est deja tranchee.

### 2.12 Priorite du premier vrai lot

Le premier vrai lot d'implementation ne doit pas commencer par retuner les heuristiques.

Il doit d'abord:

- fixer le contrat normatif;
- renforcer institutionnellement le `validation_agent`;
- et seulement ensuite requalifier l'amont.

### 2.13 Regle de completude

Tout ce qui a ete tranche doit apparaitre explicitement dans ce TODO.

Rien de decisif ne doit etre:

- laisse a la memoire de la conversation;
- disperse entre plusieurs notes;
- sous-entendu par une prose trop implicite.

## 3. Architecture cible

La cible retenue par ce TODO est la suivante:

- un arbitre LLM dominant pour la posture finale de reponse;
- une mecanique amont qui conseille, alerte et structure;
- des garde-fous durs, rares et non cassables, reserves aux cas extremes.

### 3.1 Trois etages de pouvoir cibles

#### A. Garde-fous durs non cassables

Cette couche reste deterministe.
Elle ne couvre que des cas extremes et clairement delimites.

Elle peut interdire `answer`.
Elle ne doit pas dicter a elle seule une sortie `meta`.

Sous garde-fou dur:

- l'arbitre ne peut pas produire une reponse substantive comme si la contrainte n'existait pas;
- l'arbitre garde la main pour choisir entre `clarify` et `suspend`;
- la formulation finale peut rester vernaculaire et dialogique.

Exemples de familles plausibles a borner dans le lot dedie:

- incompatibilite avec une contrainte systeme ou surface deja dure;
- absence de source obligatoire pour une verification externe explicitement requise;
- impossibilite de pretendre avoir lu une source ou un resultat web non effectivement fourni;
- contradiction materielle non resolue entre sources hautes sur un point determinant;
- payload arbitral invalide ou contexte insuffisant pour arbitrer proprement.

#### B. Analyse amont conseillere

Cette couche reste deterministe, mais perd son statut quasi-souverain.

Elle produit des artefacts d'aide:

- `user_turn_input`
- `user_turn_signals`
- `epistemic_regime`
- `proof_regime`
- `uncertainty_posture`
- `source_priority`
- `source_conflicts`
- proposition de `judgment_posture`
- proposition d'`output_regime`

Ces artefacts doivent etre lus comme:

- des alertes;
- des hypotheses de cadrage;
- des recommandations structurees;
- des ponderations.

Ils ne doivent plus, a eux seuls, fermer le couloir final de reponse hors garde-fous durs.

#### C. Arbitre LLM dominant

L'arbitre final doit:

- recevoir d'abord la matiere dialogique locale;
- recevoir ensuite les artefacts structures amont;
- lire ces artefacts comme des indices secondaires;
- choisir la posture finale de reponse;
- choisir le regime final de sortie;
- pouvoir casser une recommendation mecanique quand le contexte local montre qu'elle est fausse;
- rester borne par les garde-fous durs.

## 4. Institution cible: `validation_agent` renforce

### 4.1 Decision

L'arbitre cible doit etre le `validation_agent` renforce et reinstitue comme arbitre principal de reponse.

### 4.2 Pourquoi ce choix

Ce choix est deja le plus propre a ce stade parce que:

- `validation_agent` existe deja;
- il est deja place juste avant la projection du jugement final;
- son prompt lit deja `validation_dialogue_context` comme matiere principale;
- ajouter un autre arbitre LLM ferait proliferer les couches de pouvoir au lieu de les clarifier.

### 4.3 Ce que cela implique

Le chantier ne doit pas commencer par ajouter un nouvel agent.

Il doit commencer par:

- requalifier le `validation_agent` comme institution dominante de l'arbitrage de reponse;
- redefinir ce qu'il recoit;
- redefinir ce qu'il produit;
- redefinir ce qu'il peut casser;
- redefinir ce qu'il ne peut pas casser.

Une evolution de nom pourra etre discutee plus tard.
Mais aucun premier lot ne doit rouvrir un chantier cosmetique de renommage.

## 5. Contrat de contexte de l'arbitre

### 5.1 Matiere principale

La matiere principale de l'arbitre doit etre une fenetre dialogique locale reelle, canonisee et centree sur le tour courant.

Hypothese de travail retenue:

- 5 tours canonises;
- priorite absolue au tour utilisateur courant;
- priorite absolue au dernier message assistant;
- priorite forte aux tours immediatement precedents;
- le plus ancien est perdu avant le plus local en cas de troncature.

Le contrat cible devra preserver au minimum:

- `role`
- `content`
- `timestamp` si disponible
- et un marqueur temporel derive seulement si cela aide reellement la lecture locale.

### 5.2 Matieres secondaires

En secondaire seulement, l'arbitre doit pouvoir recevoir:

- `user_turn_input`
- `user_turn_signals`
- posture proposee par l'amont
- `output_regime` propose
- `source_priority`
- `source_conflicts`
- presence ou indisponibilite de `memory`
- presence ou indisponibilite de `summary`
- presence ou indisponibilite de `identity`
- presence ou indisponibilite de `web`
- presence ou indisponibilite de `time`

Ces elements doivent etre:

- structures;
- courts;
- etiquetes comme secondaires;
- explicitement subordonnes a la lecture dialogique locale.

### 5.3 Bruit a eviter

Le futur contrat doit explicitement eviter:

- un dump brut de `canonical_inputs`;
- une accumulation de justifications non hierarchisees;
- de la memoire lointaine non impliquee;
- des signaux nombreux sans statut clair;
- une compression trop forte du recent qui ferait perdre le contrat implicite local du tour.

## 6. Garde-fous et expression vernaculaire

Le futur contrat doit distinguer proprement deux choses:

- la contrainte non cassable;
- la forme discursive de son expression.

Ce qui est tranche:

- un garde-fou dur peut interdire `answer`;
- il ne force pas a lui seul un `meta` bureaucratique;
- il ne retire pas a l'arbitre le choix entre `clarify` et `suspend`;
- il n'interdit pas une expression sobre, dialogique et vernaculaire de la limite.

Cette distinction doit rester visible dans le contrat, les prompts futurs, le wiring et les tests.

## 7. Contrat de sortie cible

Le contrat actuel `validation_decision` est trop faible pour un arbitre dominant.

Le contrat cible devra permettre a l'arbitre de produire directement au minimum:

- `final_judgment_posture`
- `final_output_regime`
- `applied_hard_guards`
- `advisory_recommendations_followed`
- `advisory_recommendations_overridden`
- `arbiter_reason`

Le detail exact du schema reste a fixer dans le lot de doctrine.
Mais le principe est deja tranche:

- l'arbitre ne doit plus etre seulement un validateur de posture primaire;
- il doit produire le verdict final de reponse dans le couloir autorise par les garde-fous durs;
- si l'arbitre casse l'amont, c'est son verdict final qui doit etre projete dans `[JUGEMENT HERMENEUTIQUE]`.

## 8. Priorite de lecture et statut de `meta`

Le contrat cible doit expliciter noir sur blanc que, par defaut, l'arbitre privilegie:

- la lecture la plus naturelle du tour;
- la continuite dialogique locale;
- la reponse simple.

Il ne monte vers `clarify`, `suspend` ou `meta` que si cette lecture echoue reellement.

Le statut vise pour `meta` est deja tranche:

- `meta` doit devenir exceptionnel;
- `meta` ne doit plus etre une consequence mecanique de `clarify`;
- `meta` ne doit plus etre un regime ordinaire de gestion des difficultes locales.

## 9. Cas d'acceptation qui doivent piloter le chantier

Ces cas ne sont pas decoratifs.
Ils doivent rester le coeur du corpus de regression du chantier.

### 9.1 Doivent repondre simplement

- `T'as vu l'heure ?`
- `Je me rends compte de ca... t'as vu l'heure ?`
- `Je suis Christophe Muck.`
- question imaginative claire du type `Imagine que tu es une extraterrestre envoyee sur Terre...`

Attendu:

- pas de surclarification;
- pas de meta prematuree;
- pas de cadrage bureaucratique;
- priorite a la reponse simple.

### 9.2 Doivent clarifier

- `Corrige ca`
- `Et ca, t'en penses quoi ?`
- `Quel est le meilleur ?`
- `Tu veux que je m'appuie sur le repo, la memoire ou le web ?`

Attendu:

- clarification breve et pertinente;
- pas de reponse de fond prematuree;
- pas de faux `answer`.

### 9.3 Doivent suspendre

- demande de verification externe actuelle sans source disponible ou sans web admissible;
- contradiction materielle non resolue entre sources fortes sur un point determinant;
- absence de matiere suffisante alors qu'une reponse de fond pretendrait verifier.

Attendu:

- suspension ou limite explicite;
- aucune feinte de savoir;
- aucune pseudo-reponse substantive.

### 9.4 L'arbitre doit casser la mecanique

- cas ou un signal `referent` remonte mais ou le dernier echange local rend le referent evident;
- cas ou l'amont propose `clarify` ou `meta` alors que le contexte recent montre un tour phatique ou quotidien simple;
- cas ou la lecture du tour courant depend plus du dialogue recent immediat que d'une alerte amont generique.

Attendu:

- l'arbitre choisit `answer`;
- la reponse reste simple;
- la mecanique conseille, mais ne dicte pas.

### 9.5 L'arbitre ne doit surtout pas casser la mecanique

- deictique reel sans ancrage local;
- sous-determination de source explicite et materielle;
- verification externe sans base admissible;
- contradiction forte entre sources determinantes.

Attendu:

- maintien de `clarify` ou `suspend`;
- pas de cassage heroique du cadre.

## 10. Observabilite cible

L'observabilite de ce chantier ne doit pas repartir de zero.

Elle doit rester:

- petite;
- structurelle;
- reutilisable;
- suffisante pour coder sans aveuglement;
- integree lot par lot plutot que repoussee a la fin.

### 10.1 Inventaire minimal de l'existant

L'existant utile au chantier est deja reel et reutilisable:

- `chat_turn_logger` fournit deja un seam canonique par `stage`, `status`, `payload_json`, `model`, `reason_code` et persiste ces evenements dans `observability.chat_log_events`;
- `hermeneutic_node_logger` expose deja des evenements compacts pour `hermeneutic_node_insertion`, `primary_node` et `validation_agent`;
- le payload `validation_agent` expose deja la base utile du lot 2, puis du lot 4: `dialogue_messages_count`, `upstream_recommendation_posture`, `upstream_output_regime_proposed`, `upstream_active_signal_families`, `upstream_constraint_present`, `validation_decision`, `final_judgment_posture`, `final_output_regime`, `arbiter_followed_upstream`, `advisory_recommendations_followed`, `advisory_recommendations_overridden`, `applied_hard_guards`, `arbiter_reason`, `projected_judgment_posture`, `pipeline_directives_final`, `decision_source`, `reason_code`;
- `test_chat_turn_logger_phase2.py` verrouille deja la discipline de logs compacts par stage;
- `test_server_phase14.py` intercepte deja `insert_chat_log_event` sur des seams d'integration, donc le chantier possede deja une couture de preuve live sans surface admin dediee;
- les notes archivees recentes, notamment sur le web, montrent deja la doctrine utile: observabilite suffisante, compacte, sans dump brut ni replay code obligatoire.

Ce qui manque specifiquement pour le nouveau regime d'arbitrage n'est donc pas une nouvelle pile d'observabilite.
Ce qui manque est:

- un contrat minimal de champs specifiques a l'arbitre dominant;
- une visibilite explicite du suivi vs override de l'amont;
- une visibilite explicite des garde-fous durs appliques;
- une visibilite explicite du verdict final effectivement projete;
- des preuves de lot qui verifient ces traces au fur et a mesure.

### 10.2 Ce qu'on garde, ce qu'on adapte, ce qu'on ne refait pas

Ce chantier garde:

- `chat_turn_logger` comme socle canonique des logs de tour;
- `hermeneutic_node_logger` comme couture compacte du pipeline hermeneutique;
- les tests de logs et d'integration existants comme points d'appui de preuve;
- le principe "observabilite compacte, sans dump de matiere brute" deja valide sur d'autres mini-chantiers.

Ce chantier adapte:

- le contenu des payloads lies au `primary_node`, au `validation_agent` reinstitue et a la projection finale;
- la lisibilite des raisons, overrides et garde-fous;
- les tests pour faire du verdict arbitral final une preuve observable, pas seulement une consequence implicite.

Ce chantier ne refait pas:

- une nouvelle infrastructure de logs;
- une nouvelle surface admin dediee des le lot 1 ou le lot 2;
- une refonte globale de l'observabilite produit;
- un chantier separe et massif d'analytics.

### 10.3 Niveaux d'observabilite cibles

#### A. Observabilite minimale indispensable

Cette observabilite est obligatoire pour ouvrir les lots de code sans aveuglement.

Elle doit rendre visible:

- la recommendation amont principale pertinente;
- le verdict final arbitral;
- le fait que l'arbitre suive ou casse l'amont;
- le ou les garde-fous durs appliques;
- la raison lisible de la decision;
- le verdict final effectivement projete dans `[JUGEMENT HERMENEUTIQUE]`.

Surfaces retenues par defaut:

- logs applicatifs compacts d'abord;
- tests ensuite;
- aucun besoin de surface admin dediee pour tenir ce minimum.

#### B. Observabilite souhaitable mais non bloquante

Peut venir dans le chantier sans bloquer les premiers lots:

- taxonomie plus fine de `reason_code` et `arbiter_reason`;
- exports/debug compacts reutilisant la filiere `chat_log_events`;
- vues regroupees simples si elles reutilisent l'existant sans ouvrir une roadmap admin autonome.

#### C. Ce qui peut attendre

Peut etre remis a plus tard:

- surface admin dediee pour lire les arbitrages;
- agregats metriques ou dashboards produits;
- outillage d'analyse historique large echelle.

### 10.4 Contrat minimal d'observabilite du chantier

Le contrat minimal doit etre concret et testable.

Par defaut, il doit vivre d'abord dans les logs applicatifs compacts du seam arbitral et dans les tests qui les relisent.

Le contrat normatif du lot 1 est maintenant fixe dans:

- `app/docs/states/specs/response-arbiter-power-contract.md`

Champs minimaux cibles a rendre visibles, en reutilisant l'existant autant que possible:

- `upstream_recommendation_posture`
- `upstream_output_regime_proposed`
- `upstream_active_signal_families`
- `upstream_constraint_present`
- `final_judgment_posture`
- `final_output_regime`
- `arbiter_followed_upstream`
- `advisory_recommendations_followed`
- `advisory_recommendations_overridden`
- `applied_hard_guards`
- `arbiter_reason`
- `projected_judgment_posture`

Lecture attendue de ce contrat:

- si l'arbitre suit l'amont, cela doit etre visible sans diff implicite a reconstituer;
- si l'arbitre casse l'amont, l'override doit etre lisible comme tel;
- si un garde-fou dur borne la decision, il doit etre nomme;
- si la projection finale diverge de ce qui etait propose en amont, cette divergence doit etre observable;
- la raison doit rester courte, lisible et non bureaucratique.

### 10.5 Exigence minimale des lots 1 et 2

Des le lot 1, obligatoire:

- fixer noir sur blanc les champs minimaux du contrat d'observabilite;
- fixer quels stages existants sont reutilises plutot qu'inventer une nouvelle arborescence de logs;
- fixer que les preuves de lot passent d'abord par logs compacts + tests.

Des le lot 2, obligatoire:

- rendre observable noir sur blanc si l'arbitre suit ou override l'amont;
- rendre observable le verdict final produit et le verdict final projete;
- rendre observable le garde-fou dur applique si present;
- rendre observable une raison lisible de decision;
- ajouter des tests qui relisent explicitement ces champs sur le seam de logs existant.

L'observabilite ne doit pas etre une annexe optionnelle.
Elle fait partie du contrat institutionnel du chantier.

## 11. Checklist d'implementation

Tout ce qui suit releve de l'implementation future et doit etre lu comme un plan a cocher.

### Lot 1 - Doctrine et contrat de pouvoir

But:

- fixer noir sur blanc la nouvelle institution du pouvoir;
- distinguer garde-fous durs, analyse conseillere et arbitre dominant;
- definir le contrat normatif minimal de sortie.

Fichiers probables:

- `app/docs/states/specs/`
- `app/docs/todo-todo/memory/llm-dominant-response-arbiter-todo.md`
- `app/docs/README.md`
- `README.md`
- `AGENTS.md`

Risques:

- doctrine encore trop vague;
- confusion entre response arbiter et memory arbiter;
- oubli de la distinction entre autorite non souveraine et souverainete.

- [x] Ecrire la spec normative de la chaine de pouvoir cible.
- [x] Ecrire noir sur blanc que `validation_agent` a le dernier mot sur `final_judgment_posture`.
- [x] Ecrire noir sur blanc que l'amont garde une autorite non souveraine.
- [x] Ecrire noir sur blanc que `meta` devient un regime exceptionnel.
- [x] Fixer la liste doctrinale initiale des garde-fous durs plausibles.
- [x] Fixer le contrat minimal de sortie cible de l'arbitre.
- [x] Fixer le contrat minimal d'observabilite du chantier en reutilisant les seams de logs existants.
- [x] Fixer noir sur blanc que logs compacts + tests constituent la preuve minimale obligatoire.
- [x] Fixer noir sur blanc que le premier lot de code ne commence pas par retuner les heuristiques.
- [x] Verifier que les docs index renvoient vers la bonne source de verite.

Critere de completion:

- [x] Une spec courte et normative existe.
- [x] Le dernier mot de l'arbitre n'est plus implicite.
- [x] La frontiere garde-fou / conseil / souverainete est lisible sans relire la conversation.
- [x] Le minimum d'observabilite requis pour les lots 1 et 2 est nomme noir sur blanc.

Ne pas toucher dans ce lot:

- code runtime;
- heuristiques;
- prompt principal;
- memory arbiter.

### Lot 2 - Requalification institutionnelle du `validation_agent`

But:

- faire du `validation_agent` l'arbitre principal de reponse;
- supprimer son statut de simple validateur tardif;
- aligner le wiring sur cette souverainete.

Fichiers probables:

- `app/core/hermeneutic_node/validation/validation_agent.py`
- `app/prompts/validation_agent.txt`
- `app/core/chat_service.py`
- `app/core/chat_prompt_context.py`
- tests `validation_agent` et integration phase 14

Risques:

- souverainete declarative mais non reelle;
- double source de verite entre primaire et aval;
- projection finale encore re-subordonnee au primaire.

- [x] Remplacer le contrat `validation_decision` par un vrai verdict arbitral final.
- [x] Supprimer le remapping qui re-subordonne la posture finale a une posture primaire deja figee.
- [x] Faire produire directement `final_judgment_posture` par l'arbitre.
- [x] Faire produire directement `final_output_regime` par l'arbitre.
- [x] Conserver le `validation_agent` comme institution cible sans ouvrir un chantier de renommage.
- [x] Verifier que `[JUGEMENT HERMENEUTIQUE]` projette le verdict final de l'arbitre.
- [x] Etendre le payload du seam arbitral existant plutot que creer une nouvelle filiere de logs.
- [x] Rendre visible si l'arbitre suit ou override l'amont.
- [x] Rendre visible le verdict final effectivement projete.
- [x] Rendre visible une raison lisible de decision et les garde-fous appliques si presents.
- [x] Ajouter des tests qui relisent explicitement ces champs sur le seam de logs existant.

Critere de completion:

- [x] Le verdict final vient bien de l'arbitre.
- [x] Un override de l'amont est techniquement possible et tracable.
- [x] La sortie finale n'est plus un simple remap d'une posture primaire.
- [x] Les logs permettent de voir sans replay code si l'arbitre a suivi ou casse l'amont.
- [x] Les tests couvrent le seam de projection finale observable.

Ne pas toucher dans ce lot:

- retuning des heuristiques amont;
- memory arbiter;
- admin/read-model hors observabilite minimale.

### Lot 3 - Contrat de contexte principal transmis a l'arbitre

But:

- definir et livrer une fenetre de dialogue recent vraiment utile a l'arbitre;
- ancrer noir sur blanc la priorite locale des 5 messages dialogiques canonises.

Fichiers probables:

- `app/core/chat_service.py`
- `app/core/chat_prompt_context.py`
- `app/prompts/validation_agent.txt`
- tests d'integration et `validation_agent`

Risques:

- trop de bruit;
- perte du dernier message assistant ou du tour focal;
- troncature qui preserve le lointain au detriment du local.

- [x] Fixer la fenetre normative de 5 messages dialogiques canonises.
- [x] Garantir la priorite absolue du tour utilisateur courant.
- [x] Garantir la priorite absolue du dernier message assistant.
- [x] Garantir que les tours immediatement precedents priment sur les indices lointains.
- [x] Encadrer la troncature pour perdre d'abord le plus ancien.
- [x] Etiqueter explicitement les matieres secondaires comme secondaires.
- [x] Rendre visible dans les logs compacts le nombre de messages retenus et le fait qu'une troncature a eu lieu.
- [x] Rendre visible si le tour utilisateur courant et le dernier assistant ont bien ete retenus.
- [x] Ajouter des tests sur cette observabilite compacte de contexte, sans journaliser la matiere brute complete.

Critere de completion:

- [x] Le contrat de contexte recent est specifiable et testable.
- [x] Les cas de dialogue local simple restent lisibles pour l'arbitre.
- [x] Les supports secondaires n'ecrasent pas la matiere principale.
- [x] La retention/troncature du contexte recent est observable sans dump massif.

Ne pas toucher dans ce lot:

- logique des signaux amont;
- policy memory;
- prompt principal de reponse.

### Lot 4 - Redecoupage de l'amont en couche conseillere

But:

- convertir `user_turn_signals`, `judgment_posture`, `source_conflicts` et `output_regime` en artefacts conseillers plutot qu'en verrous quasi-definitifs.

Fichiers probables:

- `app/core/hermeneutic_node/inputs/user_turn_input.py`
- `app/core/hermeneutic_node/doctrine/judgment_posture.py`
- `app/core/hermeneutic_node/doctrine/source_conflicts.py`
- `app/core/hermeneutic_node/doctrine/output_regime.py`
- `app/core/hermeneutic_node/runtime/primary_node.py`
- tests `user_turn_input` et `primary_node`

Risques:

- perdre des clarifications legitimes;
- laisser croire que tout devient mou;
- dupliquer des regles qui devraient vivre dans l'arbitre.

- [x] Requalifier l'amont comme autorite non souveraine dans le code et les tests.
- [x] Faire de `judgment_posture` une recommendation explicite plutot qu'une fermeture de couloir.
- [x] Faire de `output_regime` propose un indicateur conseiller plutot qu'un verdict quasi-final.
- [x] Rendre visible quelles recommendations sont proposees a l'arbitre.
- [x] Preserver les vrais cas ambigus sans redonner a l'amont un pouvoir souverain.
- [x] Rendre visible en logs compacts la recommendation amont principale et les familles de signaux actives pertinentes.
- [x] Ajouter des tests qui permettent de comparer recommendation amont et verdict final sans reconstituer toute la pile.

Critere de completion:

- [x] La couche amont produit encore ses alertes.
- [x] Les alertes ne ferment plus seules le couloir final.
- [x] Les cas quotidiens simples et les deictiques reellement ambigus restent bien separes.
- [x] Le statut non souverain de l'amont est devenu observable, pas seulement doctrinal.

Ne pas toucher dans ce lot:

- garde-fous durs;
- memory arbiter;
- admin/read-model.

### Lot 5 - Extraction des garde-fous durs

But:

- lister puis coder les conditions vraiment non cassables;
- retirer des heuristiques amont tout ce qui n'est pas un vrai garde-fou extreme.

Fichiers probables:

- specs hermeneutiques voisines
- `validation_agent.py` ou futur wrapper arbitral
- `chat_prompt_context.py`
- `chat_service.py`
- tests de suspension et de verification

Risques:

- garder trop de faux garde-fous;
- ouvrir trop largement le couloir arbitral;
- melanger contraintes systeme et preferences hermeneutiques.

- [ ] Fixer la liste borne des garde-fous durs retenus.
- [ ] Distinguer explicitement ce qui interdit `answer` de ce qui recommande seulement `clarify`.
- [ ] Preserver le choix arbitral entre `clarify` et `suspend` sous garde-fou dur.
- [ ] Verifier que le garde-fou ne force pas une sortie `meta` bureaucratique.
- [ ] Tester qu'un cas hors garde-fou redevient arbitrable par le LLM.
- [ ] Rendre visible quel garde-fou a borne la decision, sans journaliser de dump contextuel brut.
- [ ] Rendre visible si le garde-fou a interdit `answer` mais laisse l'arbitre choisir `clarify` ou `suspend`.
- [ ] Ajouter des tests qui prouvent qu'un garde-fou ne force pas a lui seul un regime `meta`.

Critere de completion:

- [ ] La liste des garde-fous est courte, rare et lisible.
- [ ] Les cas limites restent vernaculaires.
- [ ] Les heuristiques ordinaires ne se cachent plus derriere le label garde-fou.
- [ ] Les garde-fous appliques sont observables par nom et par effet.

Ne pas toucher dans ce lot:

- contenu identity;
- memory arbiter;
- prompts non lies a l'arbitre.

### Lot 6 - Regression, acceptance et observabilite

But:

- piloter le chantier par un corpus d'acceptation stable;
- rendre les arbitrages lisibles en logs;
- eviter le retour aux micro-corrections opaques.

Fichiers probables:

- `app/tests/unit/core/hermeneutic_node/`
- `app/tests/test_server_phase14.py`
- journaux et observabilite lies a l'arbitre de reponse
- docs de cloture et validations

Risques:

- tests trop synthetiques;
- absence de corpus de tours quotidiens;
- observabilite trop pauvre pour comprendre un override ou un non-override.

- [ ] Fixer un corpus stable `answer / clarify / suspend`.
- [ ] Ajouter des cas ou l'arbitre casse la mecanique.
- [ ] Ajouter des cas ou l'arbitre ne doit surtout pas la casser.
- [ ] Journaliser les garde-fous appliques.
- [ ] Journaliser les recommendations amont suivies.
- [ ] Journaliser les recommendations amont cassees.
- [ ] Journaliser une raison lisible pour chaque override significatif.
- [ ] Verifier que le verdict projete dans `[JUGEMENT HERMENEUTIQUE]` correspond bien au verdict final de l'arbitre.
- [ ] Reutiliser `chat_turn_logger` et `hermeneutic_node_logger` plutot qu'ouvrir une nouvelle filiere d'observabilite.
- [ ] Verifier que les preuves de logs restent compactes et sans dump brut de contexte.

Critere de completion:

- [ ] Le chantier est pilote par des cas d'acceptation explicites.
- [ ] Un override est comprehensible sans reconstituer la pile entiere.
- [ ] Les regressions de surclarification et de meta prematuree deviennent visibles.
- [ ] L'observabilite minimale du chantier est tenue sans surface admin dediee.

Ne pas toucher dans ce lot:

- memory arbiter hors comparaison documentaire;
- chantiers identity;
- refontes admin larges.

## 12. Frontieres explicites du chantier

Ce TODO ne tranche pas encore:

- le schema exact final `v2` de la sortie arbitrale;
- le nom definitif du module cible;
- la granularite exacte des codes de raison;
- la surface admin eventuelle d'observabilite.

Ce TODO tranche deja:

- le probleme principal est un probleme de pouvoir institutionnel, pas seulement de seuil heuristique;
- la cible est un arbitre LLM dominant sous garde-fous;
- l'arbitre cible est le `validation_agent` reinstitue;
- l'amont garde une autorite non souveraine;
- `meta` devient un regime exceptionnel;
- la matiere principale de l'arbitre est une fenetre dialogique locale de 5 tours canonises;
- le verdict projete dans `[JUGEMENT HERMENEUTIQUE]` doit etre le verdict final de l'arbitre.

## 13. Hors scope

- aucune modification runtime dans ce document;
- aucune requalification effective du `validation_agent` dans ce document;
- aucune retouche heuristique de comportement;
- aucune modification identity;
- aucun chantier memory autre que la comparaison conceptuelle utile;
- aucune refonte admin/read-model dans ce document.
