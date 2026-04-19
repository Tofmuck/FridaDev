# LLM-Dominant Response Arbiter - TODO

Statut: ouvert
Classement: `app/docs/todo-todo/memory/`
Portee: architecture de l'arbitrage de reponse du pipeline hermeneutique
Nature: TODO d'architecture actif, lotable, auditable et anti-confusion

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
- `app/tests/unit/core/hermeneutic_node/inputs/test_user_turn_input.py`
- `app/tests/unit/core/hermeneutic_node/runtime/test_primary_node.py`
- `app/tests/unit/core/hermeneutic_node/validation/test_validation_agent.py`
- `app/docs/states/specs/chat-enunciation-and-gap-contract.md`
- `app/docs/states/specs/hermeneutic-node-output-regime-contract.md`
- `app/docs/states/specs/hermeneutic-node-user-demand-contract.md`
- `app/docs/todo-done/notes/low-ambiguity-over-clarification-closure.md`

Comparaison conceptuelle utile seulement:

- `app/memory/arbiter.py`

Le memory arbiter reste hors scope de ce chantier.
Il sert seulement de point de comparaison institutionnel: un LLM y arbitre deja un panier structure plutot que d'arriver comme simple correcteur tardif.

## 1. Probleme architectural actuel

### 1.1 Chaine actuelle de pouvoir

Aujourd'hui, la chaine de pouvoir est essentiellement la suivante:

1. `chat_service` construit `recent_window_input`, `user_turn_input` et `user_turn_signals`.
2. `primary_node` produit deja un `primary_verdict` structurant.
3. `build_judgment_posture()` convertit toute ambiguite ou sous-determination active en `clarify`.
4. `build_output_regime()` convertit aujourd'hui trop facilement `judgment_posture != answer` en `discursive_regime = meta`.
5. `build_source_conflicts()` peut encore pousser une issue `clarify`.
6. `validation_agent` relit ensuite le dossier, mais ne renvoie encore qu'une `validation_decision`.
7. `_FINAL_POSTURE_BY_PRIMARY_AND_DECISION` remappe cette decision sur une posture deja preconstruite par le primaire.
8. `chat_prompt_context.build_hermeneutic_judgment_block()` projette ensuite le verdict final injecte dans `[JUGEMENT HERMENEUTIQUE]`.

Autrement dit:

- l'amont ne conseille pas seulement;
- il precontraint deja fortement le couloir de sortie;
- l'aval n'a pas encore de pleine souverainete sur la posture finale.

### 1.2 Pourquoi cela produit de la surclarification et de la meta prematuree

Dans l'etat courant:

- les signaux amont ont encore une force quasi-decisionnelle;
- `judgment_posture` et `source_conflicts` peuvent pousser trop vite vers `clarify`;
- `output_regime` reste encore trop couple a cette logique;
- le `validation_agent` n'a pas encore un vrai contrat de verdict final.

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

L'architecture cible doit etre observable noir sur blanc.

Elle doit permettre de comprendre:

- quelle recommendation amont a ete suivie;
- quelle recommendation amont a ete cassee;
- quel garde-fou dur a borne la decision;
- quelle raison lisible a motive l'override ou le non-override;
- quel verdict final a ete projete dans `[JUGEMENT HERMENEUTIQUE]`.

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

- [ ] Ecrire la spec normative de la chaine de pouvoir cible.
- [ ] Ecrire noir sur blanc que `validation_agent` a le dernier mot sur `final_judgment_posture`.
- [ ] Ecrire noir sur blanc que l'amont garde une autorite non souveraine.
- [ ] Ecrire noir sur blanc que `meta` devient un regime exceptionnel.
- [ ] Fixer la liste doctrinale initiale des garde-fous durs plausibles.
- [ ] Fixer le contrat minimal de sortie cible de l'arbitre.
- [ ] Fixer noir sur blanc que le premier lot de code ne commence pas par retuner les heuristiques.
- [ ] Verifier que les docs index renvoient vers la bonne source de verite.

Critere de completion:

- [ ] Une spec courte et normative existe.
- [ ] Le dernier mot de l'arbitre n'est plus implicite.
- [ ] La frontiere garde-fou / conseil / souverainete est lisible sans relire la conversation.

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

- [ ] Remplacer le contrat `validation_decision` par un vrai verdict arbitral final.
- [ ] Supprimer le remapping qui re-subordonne la posture finale a une posture primaire deja figee.
- [ ] Faire produire directement `final_judgment_posture` par l'arbitre.
- [ ] Faire produire directement `final_output_regime` par l'arbitre.
- [ ] Conserver le `validation_agent` comme institution cible sans ouvrir un chantier de renommage.
- [ ] Verifier que `[JUGEMENT HERMENEUTIQUE]` projette le verdict final de l'arbitre.

Critere de completion:

- [ ] Le verdict final vient bien de l'arbitre.
- [ ] Un override de l'amont est techniquement possible et tracable.
- [ ] La sortie finale n'est plus un simple remap d'une posture primaire.

Ne pas toucher dans ce lot:

- retuning des heuristiques amont;
- memory arbiter;
- admin/read-model hors observabilite minimale.

### Lot 3 - Contrat de contexte principal transmis a l'arbitre

But:

- definir et livrer une fenetre de dialogue recent vraiment utile a l'arbitre;
- ancrer noir sur blanc la priorite locale des 5 tours canonises.

Fichiers probables:

- `app/core/chat_service.py`
- `app/core/chat_prompt_context.py`
- `app/prompts/validation_agent.txt`
- tests d'integration et `validation_agent`

Risques:

- trop de bruit;
- perte du dernier message assistant ou du tour focal;
- troncature qui preserve le lointain au detriment du local.

- [ ] Fixer la fenetre normative de 5 tours canonises.
- [ ] Garantir la priorite absolue du tour utilisateur courant.
- [ ] Garantir la priorite absolue du dernier message assistant.
- [ ] Garantir que les tours immediatement precedents priment sur les indices lointains.
- [ ] Encadrer la troncature pour perdre d'abord le plus ancien.
- [ ] Etiqueter explicitement les matieres secondaires comme secondaires.

Critere de completion:

- [ ] Le contrat de contexte recent est specifiable et testable.
- [ ] Les cas de dialogue local simple restent lisibles pour l'arbitre.
- [ ] Les supports secondaires n'ecrasent pas la matiere principale.

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

- [ ] Requalifier l'amont comme autorite non souveraine dans le code et les tests.
- [ ] Faire de `judgment_posture` une recommendation explicite plutot qu'une fermeture de couloir.
- [ ] Faire de `output_regime` propose un indicateur conseiller plutot qu'un verdict quasi-final.
- [ ] Rendre visible quelles recommendations sont proposees a l'arbitre.
- [ ] Preserver les vrais cas ambigus sans redonner a l'amont un pouvoir souverain.

Critere de completion:

- [ ] La couche amont produit encore ses alertes.
- [ ] Les alertes ne ferment plus seules le couloir final.
- [ ] Les cas quotidiens simples et les deictiques reellement ambigus restent bien separes.

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

Critere de completion:

- [ ] La liste des garde-fous est courte, rare et lisible.
- [ ] Les cas limites restent vernaculaires.
- [ ] Les heuristiques ordinaires ne se cachent plus derriere le label garde-fou.

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

Critere de completion:

- [ ] Le chantier est pilote par des cas d'acceptation explicites.
- [ ] Un override est comprehensible sans reconstituer la pile entiere.
- [ ] Les regressions de surclarification et de meta prematuree deviennent visibles.

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
