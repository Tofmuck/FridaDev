# LLM-Dominant Response Arbiter - TODO

Statut: ouvert
Classement: `app/docs/todo-todo/memory/`
Portee: architecture de l'arbitrage de reponse du pipeline hermeneutique
Nature: TODO d'architecture actif, lotable et auditable

## Pourquoi ce document existe

Ce document ouvre un chantier distinct.

Il ne reouvre ni tout le pipeline hermeneutique, ni le chantier identity, ni le memory arbiter.

Il existe parce que l'etat actuel du repo montre une confusion institutionnelle:

- l'amont heuristique prend deja trop de pouvoir sur la posture finale;
- le `validation_agent` recoit un contexte dialogique plus riche, mais trop tard et dans un cadre trop bride;
- des micro-corrections locales ont ameliore certains symptomes sans clarifier proprement qui a le dernier mot.

Le point a trancher ici n'est donc pas "moins d'heuristiques" en general.

Le point a trancher est:

- qui arbitre reellement la reponse;
- a partir de quelle matiere;
- avec quels garde-fous non cassables;
- et avec quel decoupage de chantier pour ne plus corriger a l'aveugle.

## Intention operateur

Le signal operateur "J'en ai marre" doit etre lu ici comme un constat architectural.

Ce signal veut dire:

- trop de corrections locales ont brouille la lisibilite du pouvoir d'arbitrage;
- la chaine de decision n'est plus assez explicite;
- il faut un plan qui requalifie institutionnellement le regime de reponse.

Ce document sert donc de source active pour la bascule suivante:

- depuis un pre-arbitrage mecanique fort avec validation LLM tardive et bridee;
- vers un arbitre LLM dominant, sous garde-fous durs reserves aux cas extremes.

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
Il sert seulement de point de comparaison institutionnel: un LLM y arbitre deja un panier structure plutot que d'arriver en simple correcteur de fin.

## 1. Probleme architectural actuel

### 1.1 Chaine actuelle de pouvoir

Aujourd'hui, la chaine de pouvoir est essentiellement la suivante:

1. `chat_service` construit `recent_window_input`, `user_turn_input` et `user_turn_signals`.
2. `primary_node` produit deja un `primary_verdict` structurant.
3. `build_judgment_posture()` convertit toute ambiguite ou sous-determination active en `clarify`.
4. `build_output_regime()` convertit tout `judgment_posture != answer` en `discursive_regime = meta`.
5. `build_source_conflicts()` peut ajouter une issue `clarify` supplementaire.
6. `validation_agent` relit ensuite le dossier, mais ne renvoie que `confirm|challenge|clarify|suspend`.
7. `_FINAL_POSTURE_BY_PRIMARY_AND_DECISION` mappe cette decision sur la posture primaire deja produite.
8. `chat_prompt_context.build_hermeneutic_judgment_block()` n'injecte ensuite que le verdict valide en bout de chaine.

Autrement dit:

- le primaire ne conseille pas seulement;
- il precontraint deja la parole finale;
- l'aval ne gouverne pas encore souverainement la posture finale.

### 1.2 Pourquoi l'amont contraint trop fort

Dans l'etat courant:

- `user_turn_signals` reste la premiere couche qui localise les problemes;
- `judgment_posture` traite ces signaux comme des conditions quasi-decisionnelles;
- `output_regime` herite mecaniquement de cette posture;
- `source_conflicts` reste oriente vers une issue `clarify`.

Le resultat institutionnel n'est pas seulement "des heuristiques un peu fortes".

Le resultat est:

- des heuristiques qui agissent comme pre-juges;
- une doctrine primaire qui ferme deja le couloir de sortie;
- un arbitre aval qui relit sans disposer d'une pleine souverainete.

### 1.3 Pourquoi le validation_agent n'est pas encore un arbitre souverain

Le `validation_agent` dispose pourtant de deux atouts deja importants:

- son prompt lui dit de lire d'abord `validation_dialogue_context`;
- son integration runtime arrive juste avant la projection du bloc `[JUGEMENT HERMENEUTIQUE]`.

Mais il reste institutionnellement faible pour quatre raisons:

- il n'emet qu'une `validation_decision`, pas un vrai verdict final complet;
- sa decision est remappee par `_FINAL_POSTURE_BY_PRIMARY_AND_DECISION` plutot que de devenir la source directe de la posture finale;
- si le primaire a deja conclu `clarify`, l'aval ne peut pas revenir a `answer`;
- la normalisation actuelle ne corrige que quelques cas et reste explicitement un garde-fou local.

En pratique, cela veut dire:

- le contexte dialogique recent est bien lu;
- mais il n'a pas encore la force institutionnelle suffisante pour casser la mecanique amont quand elle se trompe.

### 1.4 Symptomes produits

Cette architecture produit typiquement:

- surclarification;
- meta prematuree;
- perte du contrat implicite local du tour;
- hesitations bureaucratiques sur des tours quotidiens ou phatiques;
- multiplication de micro-correctifs heuristiques plutot qu'un vrai deplacement du pouvoir.

## 2. Architecture cible

La cible retenue par ce TODO est la suivante:

- un arbitre LLM dominant pour la posture finale de reponse;
- une mecanique amont qui conseille, alerte et structure;
- des garde-fous durs, rares et non cassables, reserves aux cas extremes.

### 2.1 Trois etages de pouvoir cibles

#### A. Garde-fous durs non cassables

Cette couche reste deterministe.

Elle ne doit couvrir que les cas ou l'arbitre ne peut pas legitimement "rompre la mecanique".

Au minimum:

- incompatibilite avec les contraintes systeme/surface deja dures;
- absence de source obligatoire pour une verification externe explicitement requise;
- impossibilite de pretendre avoir lu une page, une source ou un resultat web que le runtime n'a pas effectivement fourni;
- contradiction materielle non resolue entre sources hautes pour un point qui change la reponse;
- payload arbitral invalide ou contexte insuffisant pour arbitrer proprement.

Dans ces cas:

- l'arbitre peut encore choisir entre `clarify` et `suspend` selon le contrat;
- il ne peut pas produire une reponse substantive comme si la contrainte n'existait pas.

#### B. Analyse amont conseillere

Cette couche reste deterministe, mais perd son statut quasi-souverain.

Elle doit produire des artefacts d'aide:

- `user_turn_input`
- `user_turn_signals`
- `epistemic_regime`
- `proof_regime`
- `uncertainty_posture`
- `source_priority`
- `source_conflicts`
- proposition d'`output_regime`

Mais ces artefacts doivent etre lus comme:

- des signaux;
- des hypotheses de cadrage;
- des alertes;
- des recommandations structurees.

Ils ne doivent plus, a eux seuls, fermer le couloir final de reponse hors garde-fous durs.

#### C. Arbitre LLM dominant

L'arbitre final doit:

- recevoir d'abord le contexte dialogique recent;
- recevoir ensuite les artefacts structures amont;
- choisir la posture finale de reponse;
- pouvoir casser une recommandation mecanique quand le contexte local montre qu'elle est fausse;
- rester borne par les garde-fous durs.

## 3. Qui est l'arbitre cible

### Decision actuelle de ce TODO

L'arbitre cible doit etre le `validation_agent` renforce et reinstitue comme arbitre principal de reponse.

### Pourquoi ce choix

Ce choix est le plus propre a ce stade parce que:

- `validation_agent` existe deja;
- il est deja place au bon endroit dans la chaine, juste avant la projection du jugement hermeneutique final;
- son prompt assume deja que `validation_dialogue_context` est la matiere principale de relecture;
- ajouter un autre arbitre LLM ferait proliferer les couches de pouvoir au lieu de les clarifier.

### Ce que cela implique

Le chantier ne doit pas commencer par "ajouter un nouvel agent".

Il doit commencer par:

- requalifier le `validation_agent` comme institution dominante de l'arbitrage de reponse;
- redefinir ce qu'il recoit;
- redefinir ce qu'il a le droit de decider;
- redefinir ce qu'il ne peut pas casser.

Une evolution de nom pourra etre discutee plus tard (`response_arbiter`, alias, wrapper ou renommage).
Mais le premier lot ne doit pas ouvrir un chantier cosmetique de renommage.

## 4. Contexte dialogique que l'arbitre doit recevoir

### 4.1 Matiere principale

La matiere principale de l'arbitre doit etre une fenetre recente de dialogue canonique, centree sur le tour courant.

Contrat cible:

- garder en priorite absolue le tour utilisateur courant;
- garder obligatoirement le dernier message assistant;
- garder les 2 a 4 tours immediatement precedents si disponibles;
- viser une fenetre de 6 a 10 messages maximum, en ordre canonique;
- conserver `role`, `content`, `timestamp` et si utile un label Delta-T derive.

Invariants:

- le tour courant ne doit jamais etre tronque avant les messages plus anciens;
- le dernier message assistant ne doit jamais disparaitre si le tour courant reagit a lui;
- en cas de troncature, il faut perdre d'abord le plus ancien, pas le plus local.

### 4.2 Supports structures secondaires

En secondaire, l'arbitre doit recevoir:

- `user_turn_input`
- `user_turn_signals`
- `epistemic_regime`
- `proof_regime`
- `uncertainty_posture`
- `source_priority`
- `source_conflicts`
- presence/disponibilite de `memory`, `summary`, `identity`, `web`, `time`

Ces elements doivent etre structures, courts et clairement etiquetes comme secondaires.

Etat courant a requalifier:

- l'implementation actuelle compacte deja `validation_dialogue_context` sur une fenetre bornee;
- cette borne existe, mais elle n'a pas encore ete tranchee comme contrat architectural;
- le lot dedie devra fixer la fenetre normative plutot que laisser vivre seulement des constantes techniques.

### 4.3 Supports conditionnels

Ne doivent etre ajoutes que si le cas le justifie:

- extrait de `summary_input` si la fenetre recente ne suffit pas;
- extrait de memoire si le tour demande explicitement une reprise ou depend d'un rappel anterieur;
- contexte web si un fait externe recent ou une verification est en jeu;
- elements identitaires seulement si la coherence relationnelle ou le contenu identitaire pese reelement sur la lecture du tour.

### 4.4 Bruit a eviter

Le futur contrat doit explicitement eviter:

- un dump brut et massif de `canonical_inputs`;
- des justifications freres sans statut clair;
- de la memoire lointaine non impliquee;
- des signaux nombreux mais non hiarchises;
- un contexte recent trop compacte pour garder la contractualite locale du tour.

## 5. Ce que l'arbitre doit pouvoir casser

L'arbitre doit pouvoir casser:

- une recommandation `clarify` issue de `user_turn_signals` quand le contexte recent suffit a desambiguizer;
- une lecture `meta` induite par `output_regime` quand la reponse la plus naturelle doit rester simple;
- une priorite de source simplement indicative quand le dernier echange local est hermeneutiquement plus probant;
- une alerte faible de cadrage quand le contrat local du tour est evident.

Il ne doit pas pouvoir casser:

- les garde-fous durs definis par le lot dedie;
- les contraintes systeme/surface deja non optionnelles;
- l'absence d'une source obligatoire si la reponse pretendrait la posseder;
- la revendication d'une lecture web ou documentaire que le runtime n'a pas effectivement fournie;
- une contradiction materielle non resolue sur un point determinant.

## 6. Contrat de sortie cible

Le contrat actuel `validation_decision` est trop faible pour un arbitre dominant.

Le contrat cible devra au minimum permettre a l'arbitre de produire directement:

- `final_judgment_posture`
- `final_output_regime`
- `pipeline_directives_final`
- `applied_hard_guards`
- `advisory_overrides`

Le detail exact du schema reste a fixer dans le lot de doctrine/contrat.

Mais le principe est deja tranche par ce TODO:

- l'arbitre final ne doit plus etre seulement un validateur de posture primaire;
- il doit produire le verdict final de reponse dans le couloir autorise par les garde-fous durs.

## 7. Cas d'acceptation qui doivent piloter le chantier

Ces cas ne sont pas des exemples decoratifs.
Ils doivent devenir le coeur du corpus de regression du chantier.

### 7.1 Doivent repondre simplement

- `T'as vu l'heure ?`
- `Je me rends compte de ca... t'as vu l'heure ?`
- `Je suis Christophe Muck.`
- question imaginative claire du type: `Imagine que tu es une extraterrestre envoyee sur Terre...`

Attendu:

- pas de surclarification;
- pas de meta prematuree;
- pas de cadrage bureaucratique.

### 7.2 Doivent clarifier

- `Corrige ca`
- `Et ca, t'en penses quoi ?`
- `Quel est le meilleur ?`
- `Tu veux que je m'appuie sur le repo, la memoire ou le web ?`

Attendu:

- clarification breve et pertinente;
- pas de reponse de fond prematuree;
- pas de faux `answer`.

### 7.3 Doivent suspendre

- demande de verification externe actuelle sans source disponible ou sans web admissible;
- contradiction materielle non resolue entre sources fortes sur un point determinant;
- absence de matiere suffisante alors qu'une reponse de fond pretendrait verifier.

Attendu:

- suspension ou limite explicite;
- aucune feinte de savoir;
- aucune pseudo-reponse substantive.

### 7.4 L'arbitre doit casser la mecanique

- cas ou un signal `referent` remonte mais ou le dernier echange local rend le referent evident;
- cas ou l'amont propose `clarify/meta` alors que le contexte recent montre un tour phatique ou quotidien simple;
- cas ou la lecture du tour courant depend plus du dialogue recent immediat que d'une alerte amont generique.

Attendu:

- l'arbitre choisit `answer`;
- la reponse reste simple;
- la mecanique conseille, mais ne dicte pas.

### 7.5 L'arbitre ne doit surtout pas casser la mecanique

- deictique reel sans ancrage local;
- sous-determination de source explicite et materielle;
- verification externe sans base admissible;
- contradiction forte entre sources determinantes.

Attendu:

- maintien de `clarify` ou `suspend`;
- pas de "cassage heroique" du cadre.

## 8. Plan de migration par lots

### Lot 1 - Doctrine et contrat de pouvoir

But:

- fixer noir sur blanc la nouvelle institution du pouvoir;
- distinguer garde-fous durs, analyse conseillere et arbitre dominant;
- definir le contrat de sortie cible de l'arbitre.

Fichiers probables:

- `app/docs/states/specs/`
- `app/docs/todo-todo/memory/llm-dominant-response-arbiter-todo.md`
- `app/docs/README.md`
- `README.md`
- `AGENTS.md`

Risques:

- ecrire une doctrine encore trop vague;
- confondre response arbiter et memory arbiter;
- oublier de dire qui a le dernier mot.

Preuves attendues:

- spec normative courte sur la chaine de pouvoir;
- schema de sortie cible;
- liste explicite des garde-fous durs.

Ne pas toucher dans ce lot:

- code runtime;
- heuristiques;
- prompt principal;
- memory arbiter.

### Lot 2 - Requalification institutionnelle du validation_agent

But:

- faire du `validation_agent` l'arbitre principal de reponse;
- supprimer le statut de simple validateur tardif;
- aligner le wiring sur cette souverainete.

Fichiers probables:

- `app/core/hermeneutic_node/validation/validation_agent.py`
- `app/prompts/validation_agent.txt`
- `app/core/chat_service.py`
- `app/core/chat_prompt_context.py`
- tests `validation_agent` et integration phase 14

Risques:

- garder une souverainete declarative mais pas reelle;
- introduire une double source de verite entre primaire et aval;
- casser le bloc `[JUGEMENT HERMENEUTIQUE]`.

Preuves attendues:

- le verdict final vient bien de l'arbitre;
- le remapping aval ne re-subordonne plus la decision a la posture primaire;
- traces de regression sur `answer / clarify / suspend`.

Ne pas toucher dans ce lot:

- retuning des heuristiques amont;
- memory arbiter;
- read-model/admin hors observabilite minimale.

### Lot 3 - Contexte principal transmis a l'arbitre

But:

- definir et livrer une fenetre de dialogue recent vraiment utile a l'arbitre;
- reduire les cas ou l'arbitre relit un contexte trop pauvre ou trop compacte.

Fichiers probables:

- `app/core/chat_service.py`
- `app/core/chat_prompt_context.py`
- `app/core/hermeneutic_node/inputs/recent_context_input.py` ou equivalent si implique
- `app/prompts/validation_agent.txt`
- tests d'integration et `validation_agent`

Risques:

- injecter trop de bruit;
- perdre le dernier message assistant ou le tour focal;
- faire exploser la taille du prompt.

Preuves attendues:

- contrat clair de fenetre recente;
- tests sur preservation du tour focal et du dernier assistant;
- bornes de troncature explicites.

Ne pas toucher dans ce lot:

- logique de signaux amont;
- policy memory;
- prompt principal de reponse.

### Lot 4 - Redecoupage des heuristiques amont en couche conseillere

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
- laisser croire que "tout devient mou";
- dupliquer des regles deja remontees dans l'arbitre.

Preuves attendues:

- la couche amont produit encore ses alertes;
- mais ces alertes ne ferment plus seules le couloir final;
- les cas quotidiens simples et les deictiques reellement ambigus restent bien separes.

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

- garder trop de "garde-fous" qui sont en realite des heuristiques;
- a l'inverse ouvrir trop largement le couloir arbitral;
- melanger contraintes systeme et preferences hermeneutiques.

Preuves attendues:

- liste borne de garde-fous;
- tests de non-cassage;
- preuve qu'un cas hors garde-fou redevient arbitrable par le LLM.

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
- journaux/observabilite lies a l'arbitre de reponse
- docs de cloture et validations

Risques:

- tests trop synthetiques;
- absence de corpus de tours quotidiens;
- observabilite trop pauvre pour comprendre un override ou un non-override.

Preuves attendues:

- corpus explicite `answer / clarify / suspend`;
- traces de cas ou l'arbitre casse la mecanique;
- traces de cas ou il ne la casse pas;
- journaux disant quels garde-fous ont ete appliques et quelles alertes amont ont ete overrides.

Ne pas toucher dans ce lot:

- memory arbiter hors comparaison documentaire;
- chantiers identity;
- refontes admin larges.

## 9. Frontieres explicites du chantier

Ce TODO ne tranche pas encore:

- le schema exact final `v2` de la sortie arbitrale;
- le nom definitif du module cible;
- la granularite exacte des codes de raison;
- la surface admin eventuelle d'observabilite.

Ce TODO tranche deja:

- le probleme principal est un probleme de pouvoir institutionnel, pas seulement de seuil heuristique;
- la cible est un arbitre LLM dominant sous garde-fous;
- l'arbitre cible est le `validation_agent` reinstitue;
- l'amont doit devenir conseiller;
- les cas d'acceptation doivent piloter le chantier.

## 10. Hors scope

- aucune modification runtime dans ce document;
- aucune requalification effective du `validation_agent` dans ce document;
- aucune retouche heuristique de comportement;
- aucune modification identity;
- aucun chantier memory autre que la comparaison conceptuelle utile;
- aucune refonte admin/read-model dans ce document.
