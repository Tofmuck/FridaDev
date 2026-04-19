# Noeud de convergence hermeneutique

Date: 2026-03-29
Statut: cadrage architectural de reference

## 1. Objet

Ce document definit le dispositif de convergence hermeneutique cible de `FridaDev`.

Le dispositif cible est constitue de deux etages:
- un noeud primaire de convergence;
- un agent hermeneutique de validation (juge de revision), place apres le noeud primaire et avant le branchement aval.

Le noeud primaire recoit plusieurs determinants heterogenes deja produits par le systeme ou par de futurs modules, puis derive un premier cadre de reponse explicable et testable.
L'agent de validation relit ce premier verdict, puis decide sa validation finale.

Le noeud ne se confond pas avec :
- la memoire ;
- le pipeline identitaire ;
- le grounding temporel ;
- la recherche web ;
- le prompt final ;
- `M6 Stimmung`.

`M6 Stimmung` est un determinant important du futur noeud, mais il n'est pas le noeud lui-meme.

Le noeud primaire est l'instance de synthese qui arbitre entre :
- memoire ;
- web ;
- identite ;
- temps ;
- resume ;
- contexte recent ;
- `Stimmung` ;
- `tour_utilisateur`.

Sa finalite est de produire, pour chaque tour, un verdict premier qui dise :
- comment parler ;
- au nom de quelles sources parler ;
- avec quel niveau de certitude parler ;
- avec quel niveau de preuve parler ;
- s'il faut repondre, demander une precision, ou suspendre le jugement ;
- avec quel degre de reprise ou de re-situation parler.

L'agent hermeneutique de validation revise ensuite ce verdict premier avec quatre sorties possibles:
- `confirm`
- `challenge`
- `clarify`
- `suspend`

Modele cible de reference pour cet agent de validation: `GPT-5.4`.

## 2. Pourquoi ce noeud est necessaire

Le pipeline actuel de `FridaDev` assemble deja plusieurs briques serieuses :
- system prompt ;
- prompt hermeneutique ;
- `NOW` canonique ;
- identites statiques et dynamiques ;
- resume actif ;
- indices contextuels ;
- memoire RAG ;
- arbitrage memoire ;
- recherche web optionnelle ;
- journaux et observabilite.

Mais ces briques, a elles seules, ne suffisent pas encore a produire un arbitre de reponse complet.

Aujourd'hui, le systeme sait deja :
- recuperer ;
- filtrer ;
- injecter ;
- resumer ;
- journaliser ;
- faire survivre certains etats.

En revanche, il ne dispose pas encore d'une instance superieure qui tranche explicitement :
- quelle source prime ici ;
- si l'on doit parler de maniere prudente, assertive, exploratoire ou justificative ;
- si l'on doit repondre comme a une reprise conversationnelle, une verification factuelle, une demande de preuve, une hypothese ou une objection ;
- comment arbitrer entre memoire conversationnelle, source web, identite stable, contexte recent, resume actif et etat dialogique.

Sans ce noeud, le pipeline reste un assemblage de sous-pipelines hermeneutiques partiels.

## 3. Entrees du noeud

Le noeud cible doit recevoir des entrees deja structurees. Il ne doit pas recevoir un melange informe de prose brute.

### 3.1 Temps

Entrees attendues :
- `NOW` canonique du tour ;
- `TIMEZONE` canonique ;
- `delta_class` et `delta_human` pour les tours et souvenirs ;
- `silence_class` et `silence_human` pour les interruptions ;
- informations utiles de recence et de distance temporelle.

Role :
- situer le present du tour ;
- convertir les traces horodatees en rapports au present ;
- aider a choisir le niveau de reprise et de re-situation ;
- interdire les improvisations temporelles sans ancrage.

### 3.2 Memoire

Entrees attendues :
- traces recuperees ;
- scores de pertinence ;
- decisions d'arbitrage memoire ;
- informations de redondance ou de gain contextuel ;
- eventuels resumés parents des traces.

Role :
- fournir des rappels potentiellement utiles ;
- fournir des souvenirs explicables ;
- permettre un arbitrage entre souvenir utile et bruit memoriel.

### 3.3 Identite

Entrees attendues :
- identite statique du modele ;
- identite statique de l'utilisateur ;
- identites dynamiques acceptees ;
- eventuels indices identitaires contextuels ou episodiques s'ils sont exposes ;
- etat de confiance, recurrence, stabilite et statut.

Role :
- stabiliser certaines constantes de relation ;
- fournir des contraintes de lecture sur l'utilisateur et le modele ;
- ne jamais se substituer seule a la demande du tour.

### 3.4 Resume

Entrees attendues :
- presence ou absence d'un resume actif ;
- portee temporelle du resume ;
- relation du resume avec les tours recents.

Role :
- compresser l'historique lointain ;
- fournir un plan de continuite lorsque le dialogue depasse la fenetre recente ;
- ne jamais etre traite comme une autorite plus forte que l'ensemble des autres sources.

### 3.5 Contexte recent

Entrees attendues :
- indices contextuels recents ;
- evenementialite locale du tour ou des derniers tours ;
- contraintes de situation, fatigue, urgence, etc., lorsqu'elles sont structurees.

Role :
- fournir une faible memoire de situation ;
- influer sur la reprise et la prudence ;
- ne pas polluer l'identite durable.

### 3.6 Web

Entrees attendues :
- presence ou absence de recherche web sur le tour ;
- nature de la demande ;
- resultat de reformulation ;
- nombre de resultats ;
- fraicheur ;
- autorite relative des sources ;
- conflit eventuel avec memoire, identite ou resume.

Role :
- fournir des faits externes frais ou verifiables ;
- corriger ou suspendre des souvenirs si ceux-ci portent sur des contenus temporellement instables ;
- imposer un regime de preuve plus exigeant sur certaines questions.

### 3.7 Stimmung

Entrees attendues :
- un input canonique `stimmung` stabilise calcule par `app/core/hermeneutic_node/inputs/stimmung_input.py` ;
- une `dominant_tone` ;
- des `active_tones` ;
- une `stability` ;
- un `shift_state` ;
- un `turns_considered`.

Role :
- fournir un determinant affectif structure et stabilise ;
- moduler l'acceptabilite de certaines transitions de regime ;
- contribuer au regime d'enonciation ;
- etre calcule en amont a partir de `affective_turn_signal` produits par `app/core/stimmung_agent.py`, sans exposer ces signaux bruts comme entree canonique directe du noeud ;
- ne pas importer la machine `M6` complete ;
- ne pas decider seul de la hierarchie de toutes les sources ni des directives finales.

### 3.8 Tour utilisateur

Entrees attendues :
- `geste_dialogique_dominant` ;
- `regime_probatoire` ;
- `qualification_temporelle`.

Raffinements ulterieurs possibles, hors contrat minimal courant :
- formulation explicite du tour ;
- marqueurs de precision, de rappel, de speculation ou de clarification ;
- rapport du tour a une information stable ou instable ;
- signaux d'ambiguite / sous-determination.

Role :
- orienter la fonction de reponse ;
- indiquer la forme la plus utile de restitution ;
- servir de cle de lecture pour la priorisation des sources.

## 4. Ce que le noeud ne doit pas recevoir

Pour rester lisible et auditable, le noeud ne doit pas recevoir :
- le texte final deja redige ;
- des scenes finales aval ;
- des modules deja recomposes de maniere irreversible ;
- le contenu brut integral de tous les documents lointains ;
- des sorties maquillées qui empechent de retrouver la source premiere.

Le noeud doit recevoir des determinants structures, pas des resultats deja cuits.

## 5. Sorties du dispositif

Le dispositif produit deux niveaux de sortie:
- une sortie primaire (noeud primaire);
- une sortie finale revisee (agent de validation), seule consommable par l'aval.

### 5.0 Sortie primaire du noeud

La sortie primaire du noeud doit rester compacte, structuree, stable et testable.

Le noyau doctrinal de cette sortie primaire doit au minimum contenir:
- un `discursive_regime` ;
- un `epistemic_regime` ;
- un `proof_regime` ;
- un `judgment_posture` ;
- un `resituation_level` ;
- un `time_reference_mode` ;
- une `source_priority` ou hierarchie effective des sources ;
- un `source_conflicts` compact ;
- un `uncertainty_posture` ;
- des `pipeline_directives_provisional`.

### 5.1 Regime discursif

Le regime discursif dit quelle forme discursive substantive prend la sortie primaire.

Il doit rester distinct :
- de `judgment_posture`, qui garde seul `answer|clarify|suspend` ;
- de `resituation_level`, qui dit combien la sortie recontextualise.

Taxonomie minimale cible :
- `meta` ;
- `simple` ;
- `cadre` ;
- `comparatif` ;
- `continuite`.

`meta` ne vaut ni `clarify` ni `suspend`.
Il indique seulement qu'aucun regime discursif substantif n'est retenu en propre dans cette premiere version.

### 5.2 Regime epistemique

Le regime epistemique dit sur quel type de validite la reponse peut s'appuyer.

Exemples de statuts :
- certain ;
- probable ;
- incertain ;
- suspendu ;
- contradictoire ;
- a verifier.

Le regime epistemique doit empecher qu'une memoire locale, une source web recente et une hypothese soient traitees comme des evidences du meme rang.

### 5.3 Regime de preuve

Le regime de preuve dit si la reponse peut se contenter :
- d'un rappel contextualise ;
- d'un absolu factuel ;
- d'une indication prudente ;
- d'une explicitation de source ;
- d'une suspension avec demande de verification.

### 5.4 Posture de jugement / epoke

Le noeud doit rendre explicite la posture de jugement adoptee sur le tour.

La cible minimale retenue est :
- `answer`
- `clarify`
- `suspend`

Sens :
- `answer` : le cadre est assez stable pour produire une reponse substantive ;
- `clarify` : la demande est sous-determinee, trop floue, ou demande une precision avant de conclure ;
- `suspend` : l'assise epistemique ou probatoire reste insuffisante, bloquee, ou non assez solide pour trancher proprement.

Effets attendus :
- `clarify` doit permettre des formes du type `Peux-tu preciser ?`
- `suspend` doit permettre des formes du type `Je ne sais pas`, `Je ne peux pas trancher proprement`, ou une suspension equivalente.

Un conflit inter-source residuel clarifiable n'appelle pas, a lui seul, `suspend`.
Il doit normalement nourrir une parole de clarification explicite.

Cette posture n'est pas un simple style de sortie.
Elle est la forme operationnelle de la suspension du jugement dans le pipeline.

### 5.5 Niveau de re-situation

Le noeud doit determiner combien la sortie doit recontextualiser.

Taxonomie minimale cible :
- `none` ;
- `light` ;
- `explicit` ;
- `strong`.

Cet axe reste orthogonal au regime discursif :
- `discursive_regime` dit sous quelle forme substantive la sortie se tient ;
- `resituation_level` dit combien elle rappelle ou recontextualise.

### 5.6 Hierarchie des sources

La sortie doit dire quelle source prime ici, ou quel ordre de lecture doit etre applique, selon une hierarchie doctrinale explicite :
- `tour_utilisateur` puis `temps` comme couches de cadrage et de validite ;
- `memoire`, `contexte_recent` et `identity` comme premier rang de contenu par defaut ;
- `resume` comme support de continuite ;
- `web` comme priorite faible par defaut mais forte sur les contenus instables, dates ou explicitement verifiables ;
- `M6` contributif pour l'enonciation, non souverain.

### 5.7 Validation finale du verdict primaire

L'agent hermeneutique de validation recoit:
- un `validation_dialogue_context` recent elargi;
- les entrees canoniques;
- le verdict primaire du noeud;
- les justifications et directives provisoires.

Ce contexte dialogique recent elargi n'est pas un simple complement.
Il constitue la matiere hermeneutique principale de la relecture.

Il agit comme juge de revision et produit directement un verdict arbitral final:
- `final_judgment_posture` ;
- `final_output_regime` ;
- `arbiter_reason`.

Une trace `validation_decision` peut subsister pour compatibilite et observabilite,
mais elle n'est plus la source souveraine du couloir final.

Le contrat du validation agent doit donc porter prioritairement:
- le verdict final consomme par l'aval ;
- les directives finales derivees de ce verdict ;
- la visibilite du suivi vs override des recommandations amont.

Il est souverain sur la validation finale du verdict.
Il n'est pas souverain sur les criteres: les criteres restent fixes dans les contrats normatifs.

Le contrat doit aussi fixer le cadre operationnel minimal de la validation:
- budget token;
- timeout;
- fail-open;
- circuit breaker;
- cout/latence operationnels acceptables.

L'aval consomme uniquement une sortie validee par cet agent.
Cette sortie reste canonique en interne, mais le prompt principal doit la lire via une projection aval en prose, et non comme un JSON brut.
Le bloc cible retenu pour cette projection est `[JUGEMENT HERMENEUTIQUE]`.

### 5.8 Fail-open du noeud primaire

Le noeud primaire doit aussi avoir un comportement fail-open explicite:
- en cas d'echec primaire, le pipeline ne doit pas s'effondrer;
- un fallback minimal audit-able doit etre produit;
- ce fallback reste soumis a la validation avant consommation aval.

## 6. Questions que le dispositif doit trancher

Le dispositif (noeud primaire + validation) doit etre explicitement charge de trancher les questions suivantes:

1. De quel type de reponse s'agit-il ?
- reprise conversationnelle ;
- rappel ;
- demande factuelle ;
- demande de preuve ;
- hypothese ;
- objection ;
- clarification.

2. Quelle source prime ?
- source web ;
- memoire conversationnelle ;
- identite stable ;
- contexte recent ;
- resume actif ;
- combinaison de plusieurs sources.

3. Comment parler ?
- avec prudence ;
- avec exigence de justification ;
- avec reprise simple ;
- avec reprise resituee ;
- avec suspension ou verification.

4. Faut-il repondre, demander une precision, ou suspendre le jugement ?
- `answer`
- `clarify`
- `suspend`

5. A quel degre faut-il se resituer ?
- pas du tout ;
- legerement ;
- explicitement ;
- fortement.

6. Quel niveau de preuve faut-il mobiliser ?
- minimal ;
- moyen ;
- explicite ;
- obligatoire.

7. Que faire en cas de conflit ?
- expliciter le conflit ;
- demander une clarification explicite ;
- reduire l'assertivite.

8. Le verdict primaire est-il valide en revision ?
- `confirm`
- `challenge`
- `clarify`
- `suspend`

## 7. Hierarchie des sources

Cette section fixe la logique cible d'arbitrage inter-sources.

### 7.1 Temps

Le temps ne prime pas comme contenu, mais comme condition de forme du discours.

Il regle :
- la recence ;
- la reprise ;
- le mode relatif/absolu ;
- la legitimite des formulations de journee ;
- la distinction entre information stable et instable.

### 7.2 Web

Le web doit primer lorsque la question porte sur des contenus instables ou datés :
- actualite ;
- prix ;
- disponibilites ;
- informations susceptibles d'avoir change.

Le web ne doit pas automatiquement ecraser la memoire lorsque la question porte sur une histoire conversationnelle ou une preference stable.

### 7.3 Memoire

La memoire doit primer lorsqu'il s'agit :
- de reprise conversationnelle ;
- de rappel d'un contenu deja echange ;
- d'un souvenir utile pour comprendre la demande actuelle ;
- d'une coherence longitudinale du dialogue.

Mais elle doit etre abaissee lorsque :
- la trace est ancienne et faible ;
- elle contredit une source externe plus autorisee sur un contenu instable ;
- elle n'apporte pas de gain contextuel reel.

### 7.4 Identite

L'identite doit agir comme contrainte de relation et d'interpretation, pas comme preuve sur le monde.

Elle peut primer sur la forme de reponse, par exemple :
- niveau de structure attendu ;
- preferences de style conversationnel ;
- constances stables de l'utilisateur.

Elle ne doit pas primer sur :
- les faits externes ;
- les informations temporellement instables ;
- les conflits de sources verifiables.

### 7.5 Resume

Le resume actif est une compression utile, pas une source souveraine.

Il peut primer sur l'oubli brut, mais il ne doit pas primer sur :
- les tours recents explicites ;
- une trace memoire plus precise ;
- une source externe verifiable sur un fait instable.

### 7.6 Contexte recent

Le contexte recent a une autorite faible mais immediatement utile.

Il peut influer sur :
- la prudence ;
- la reprise ;
- la lecture d'une demande ;
- le degre d'insistance.

Il ne doit pas durcir seul un regime de preuve.

### 7.7 Stimmung / M6

M6 joue comme determinant de coherence et de transition.

Il peut influer fortement sur :
- le regime discursif ;
- la stabilite des transitions ;
- le cout d'un changement de posture.

Mais il ne doit pas devenir l'autorite epistemique ultime. Il ne remplace ni le web, ni la memoire, ni le temps.

## 8. Regimes cibles produits par le noeud

Le noeud doit produire au moins trois familles de regimes.

### 8.1 Regime discursif

Il dit comment tenir formellement la reponse :
- direct ;
- neutre ;
- explicatif ;
- prudent ;
- resitue ;
- exploratoire ;
- justifie.

### 8.2 Regime epistemique

Il dit au nom de quel type de certitude la reponse parle :
- certain ;
- probable ;
- plausible ;
- incertain ;
- suspendu ;
- contradictoire.

### 8.3 Regime de preuve

Il dit combien de preuve doit etre explicitee :
- simple rappel suffisant ;
- source implicite suffisante ;
- source explicite utile ;
- justification obligatoire ;
- impossibilite de conclure proprement.

### 8.4 Posture de jugement

Le noeud doit aussi produire une posture de jugement explicite :
- repondre ;
- demander une precision ;
- suspendre.

La suspension du jugement n'est pas un echec du systeme.
Elle est une sortie legitime lorsque le cadre ne permet pas une conclusion propre.

## 9. Place de M6

M6 doit etre traite comme un module contributeur du noeud, pas comme le noeud lui-meme.

M6 apporte :
- un etat dialogique ;
- une inertie ;
- des transitions de regime ;
- un indicateur de stabilite ;
- des directives structurelles.

M6 n'apporte pas, a lui seul :
- la hierarchie generale des sources ;
- le choix entre memoire et web ;
- la lecture complete de la demande ;
- l'arbitrage global entre resume, contexte, identite et temps.

En consequence:
- le noeud primaire doit prendre M6 en consideration;
- l'agent de validation peut challenger un verdict primaire qui surexpose M6;
- M6 ne doit jamais devenir un souverain concurrent de la validation finale.

## 10. Place des briques deja existantes dans FridaDev

### 10.1 Ce qui existe deja

`FridaDev` dispose deja de briques solides :
- `NOW` canonique et cadre temporel du tour ;
- labels relatifs et marqueurs de silence ;
- resume actif ;
- indices contextuels recents ;
- retrieval memoire ;
- arbitrage memoire ;
- extraction identitaire ;
- politiques `accept/defer/reject` ;
- recherche web optionnelle ;
- prompt hermeneutique explicite ;
- observabilite fine.

### 10.2 Ce qui existe partiellement

Existe de maniere partielle :
- discipline temporelle du discours ;
- discipline de preuve sur certaines briques ;
- hierarchie locale implicite entre certaines sources ;
- contraintes hermeneutiques du prompt.

Le Lot 8 les a maintenant rassembles dans un noeud primaire compact, mais la validation finale et le wiring aval restent ouverts.

### 10.3 Ce qui manque

Il manque encore :
- un objet d'entree canonique pour chaque determinant ;
- un arbitrage explicite certain/probable/incertain ;
- un agent hermeneutique de validation place avant l'aval ;
- un wiring aval pilote par une sortie revisee.

## 11. Ordre de construction recommande

L'ordre cible n'est pas :
- mesurer d'abord ;
- theoriser ensuite.

L'ordre cible est:

1. Nommer le noeud.
2. Lister ses entrees.
3. Canoniser chaque entree.
4. Definir les sorties minimales.
5. Definir l'agent de validation de revision.
6. Definir la hierarchie des sources.
7. Brancher l'aval sur la sortie validee.
8. Seulement ensuite lancer une vraie shadow globale.

### 11.1 Etape 1 - Cartographie canonique des determinants

Pour chaque determinant :
- source ;
- format ;
- stabilite ;
- niveau d'autorite ;
- mode de lecture.

### 11.2 Etape 2 - Contrat d'entree

Chaque determinant doit avoir :
- un format stable ;
- une semantique stable ;
- une frontiere claire.

### 11.3 Etape 3 - Sortie minimale du noeud

V1 recommandee (noyau doctrinal) :
- `discursive_regime`
- `epistemic_regime`
- `proof_regime`
- `judgment_posture`
- `resituation_level`
- `time_reference_mode`
- `source_priority`
- `source_conflicts`
- `uncertainty_posture`
- `pipeline_directives_provisional`

### 11.4 Etape 4 - Validation avant aval

Le verdict primaire ne doit pas etre consomme directement par l'aval.

L'agent hermeneutique de validation revise ce verdict, puis produit une sortie validee minimale:
- `final_judgment_posture`
- `final_output_regime`
- `pipeline_directives_final`
- `arbiter_reason`

Un champ `validation_decision` peut etre conserve comme trace legacy,
mais il est derive du verdict final et n'est plus la source normative du branchement aval.

Modele cible de reference pour cette etape: `GPT-5.4`.

Cette etape inclut aussi le cadre operationnel de validation:
- budget token;
- timeout;
- fail-open;
- circuit breaker.

### 11.5 Etape 5 - Wiring aval

Les modules aval ne doivent plus deduire chacun leur politique dans leur coin.
Ils doivent brancher sur la sortie validee, et non `primary_verdict` brut.
Pour le prompt principal, cette sortie doit etre projetee en un bloc prose dedie `[JUGEMENT HERMENEUTIQUE]`, derive de `validated_output`, avec `final_judgment_posture`, `final_output_regime` et `pipeline_directives_final` deja resolus comme surface normative compacte.

### 11.6 Etape 6 - Shadow globale

La shadow globale n'a de sens qu'une fois la structure posee.

Avant cela, toute shadow ne valide qu'un sous-pipeline partiel.

## 12. Taches a faire

Cette section fixe les taches reelles pour converger vers le noeud cible.

### 12.1 Taches documentaires

- decrire explicitement les determinants du noeud dans `FridaDev` ;
- documenter le futur statut de `M6` comme contributeur ;
- formaliser la hierarchie des sources ;
- formaliser le regime epistemique cible ;
- formaliser la suspension du jugement comme sortie legitime du noeud ;
- formaliser la sortie minimale du noeud.

### 12.2 Taches de structuration

- extraire ou canoniser un format d'entree pour chaque source ;
- rendre comparable l'autorite relative des sources ;
- rendre visible les conflits de sources ;
- rendre explicites les cas de suspension.

### 12.3 Taches de refacto

- reduire les deductions implicites eparses ;
- eviter que chaque module aval rederive sa propre politique ;
- isoler les briques qui devront devenir entrees du noeud.

### 12.4 Taches de wiring

- faire consommer au retrieval / arbitrage / generation des directives communes ;
- brancher M6 comme determinant et non comme souverain ;
- introduire un verdict primaire explicite du noeud ;
- definir le fail-open du noeud primaire ;
- introduire l'agent hermeneutique de validation avant l'aval ;
- brancher la posture `answer | clarify | suspend` sur la sortie validee ;
- introduire un point de sortie unique revise.

### 12.5 Taches de preuve

- tests de structure du noeud ;
- tests d'arbitrage inter-sources ;
- tests de conflits de sources ;
- tests de regimes epistemiques ;
- shadow globale seulement apres existence du noeud.

## 13. Frontieres

Pour rester propre, ce chantier doit respecter les frontieres suivantes :

- ne pas confondre memoire et noeud ;
- ne pas confondre grounding temporel et noeud ;
- ne pas confondre M6 et noeud ;
- ne pas confondre criteres doctrinaux et pouvoir de revision de l'agent de validation ;
- ne pas transformer le noeud en modele tout-puissant opaque ;
- ne pas transformer l'agent de validation en auto-legislateur des criteres ;
- ne pas faire du noeud un simple prompt bavard ;
- ne pas lancer une shadow globale avant que la structure existe reellement.

## 14. Decision de fond retenue

La decision architecturale retenue est la suivante:

- le pipeline actuel de `FridaDev` n'est pas encore le pipeline hermeneutique complet ;
- `M6 Stimmung` n'est pas le noeud de convergence ;
- `M6 Stimmung` est un determinant du noeud primaire ;
- le noeud primaire arbitre entre temps, memoire, web, identite, resume, contexte et `Stimmung` ;
- le verdict primaire devra etre revise par un agent hermeneutique de validation, modele cible `GPT-5.4` ;
- cet agent sera souverain sur la validation finale (`confirm|challenge|clarify|suspend`) mais non souverain sur les criteres ;
- l'aval consommera uniquement la sortie validee ;
- tant que la validation hermeneutique et le wiring aval ne sont pas livres, toute validation globale du pipeline reste necessairement partielle.

## 15. Structure code cible (documentaire)

Structure cible de lisibilite (sans creation dans cette tranche):

- `app/core/hermeneutic_node/inputs/`
  - contrats d'entree canoniques et traduction runtime.
- `app/core/hermeneutic_node/doctrine/`
  - modules doctrinaux issus des specs normatives.
- `app/core/hermeneutic_node/runtime/`
  - noeud primaire, etat persistant, wiring technique.
- `app/core/hermeneutic_node/validation/`
  - agent hermeneutique de validation et sorties de revision.
