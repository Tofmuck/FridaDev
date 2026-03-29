# Noeud de convergence hermeneutique

Date: 2026-03-29
Statut: cadrage architectural de reference

## 1. Objet

Ce document definit le noeud de convergence hermeneutique cible de `FridaDev`.

Ce noeud est l'instance qui recoit plusieurs determinants heterogenes deja produits par le systeme ou par de futurs modules, puis qui derive un cadre de reponse unique, explicable et testable.

Le noeud ne se confond pas avec :
- la memoire ;
- le pipeline identitaire ;
- le grounding temporel ;
- la recherche web ;
- le prompt final ;
- `M6 Stimmung`.

`M6 Stimmung` est un determinant important du futur noeud, mais il n'est pas le noeud lui-meme.

Le noeud est l'instance de synthese qui arbitre entre :
- memoire ;
- web ;
- identite ;
- temps ;
- resume ;
- contexte recent ;
- `Stimmung` ;
- demande utilisateur.

Sa finalite est de produire, pour chaque tour, un regime de reponse qui dise :
- comment parler ;
- au nom de quelles sources parler ;
- avec quel niveau de certitude parler ;
- avec quel niveau de preuve parler ;
- avec quel degre de reprise ou de re-situation parler.

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

### 3.7 Stimmung / M6

Entrees attendues :
- etat dialogique local ;
- regime derive par M6 ;
- stabilite de regime ;
- preuves typées eventuelles ;
- directives structurelles derivees ;
- etat precedent persistant.

Role :
- fournir un determinant de coherence dialogique ;
- moduler l'acceptabilite des transitions de regime ;
- contribuer au choix du regime discursif et epistemique ;
- ne pas decider seul de la hierarchie de toutes les sources.

### 3.8 Demande utilisateur

Entrees attendues :
- type de demande ;
- formulation explicite ;
- demande de precision, de preuve, de rappel, de speculation ou de clarification ;
- demande d'information instable ou stable ;
- tonalite pragmatique de la demande.

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

## 5. Sorties du noeud

Le noeud doit produire une sortie compacte, structuree, stable et testable.

Cette sortie doit au minimum contenir :
- un `discursive_regime` ;
- un `epistemic_regime` ;
- un `proof_regime` ;
- un `resituation_level` ;
- un `time_reference_mode` ;
- une `source_priority` ou hierarchie effective des sources ;
- un `uncertainty_posture` ;
- des `pipeline_directives` pour les modules aval.

### 5.1 Regime discursif

Le regime discursif dit comment la reponse doit se tenir formellement.

Exemples de dimensions possibles :
- reprise simple ;
- reprise resituee ;
- explicatif prudent ;
- directif justifie ;
- exploratoire ;
- neutre.

Ce regime ne doit pas etre une humeur vague. Il doit etre derive d'un arbitrage entre determinants.

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

### 5.4 Niveau de re-situation

Le noeud doit determiner :
- si la reponse doit reprendre directement ;
- si elle doit rappeler le dernier echange ;
- si elle doit resituer temporellement ou discursivement ;
- si elle doit clarifier un conflit de cadre.

### 5.5 Hierarchie des sources

La sortie doit dire quelle source prime ici, ou quel ordre de lecture doit etre applique :
- web avant memoire ;
- memoire avant resume ;
- resume avant rien du tout ;
- identite pertinente ou hors sujet ;
- contexte recent fort ou faible ;
- M6 contributif mais non souverain.

## 6. Questions que le noeud doit trancher

Le noeud doit etre explicitement charge de trancher les questions suivantes :

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

4. A quel degre faut-il se resituer ?
- pas du tout ;
- legerement ;
- explicitement ;
- fortement.

5. Quel niveau de preuve faut-il mobiliser ?
- minimal ;
- moyen ;
- explicite ;
- obligatoire.

6. Que faire en cas de conflit ?
- suspendre ;
- expliciter le conflit ;
- privilegier une source ;
- demander verification ;
- reduire l'assertivite.

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

En consequence :
- le noeud doit prendre M6 en consideration ;
- mais ne doit jamais se reduire a M6.

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

Mais ces elements restent distribues dans plusieurs couches et non rassembles dans un unique arbitre de convergence.

### 10.3 Ce qui manque

Il manque encore :
- un objet d'entree canonique pour chaque determinant ;
- un nœud unique de synthese ;
- une sortie compacte unique pour le regime de reponse ;
- une hierarchie explicite et centralisee des sources ;
- un arbitrage explicite certain/probable/incertain ;
- un wiring aval piloté par cette sortie.

## 11. Ordre de construction recommande

L'ordre cible n'est pas :
- mesurer d'abord ;
- theoriser ensuite.

L'ordre cible est :

1. Nommer le noeud.
2. Lister ses entrees.
3. Canoniser chaque entree.
4. Definir les sorties minimales.
5. Definir la hierarchie des sources.
6. Brancher le noeud sur les modules aval.
7. Seulement ensuite lancer une vraie shadow globale.

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

V1 recommandee :
- `discursive_regime`
- `epistemic_regime`
- `proof_regime`
- `resituation_level`
- `time_reference_mode`
- `source_priority`
- `pipeline_directives`

### 11.4 Etape 4 - Wiring aval

Les modules aval ne doivent plus deduire chacun leur politique dans leur coin.

Ils doivent consommer les directives du noeud.

### 11.5 Etape 5 - Shadow globale

La shadow globale n'a de sens qu'une fois la structure posee.

Avant cela, toute shadow ne valide qu'un sous-pipeline partiel.

## 12. Taches a faire

Cette section fixe les taches reelles pour converger vers le noeud cible.

### 12.1 Taches documentaires

- decrire explicitement les determinants du noeud dans `FridaDev` ;
- documenter le futur statut de `M6` comme contributeur ;
- formaliser la hierarchie des sources ;
- formaliser le regime epistemique cible ;
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
- introduire un point de sortie unique du regime.

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
- ne pas transformer le noeud en modele tout-puissant opaque ;
- ne pas faire du noeud un simple prompt bavard ;
- ne pas lancer une shadow globale avant que la structure existe reellement.

## 14. Decision de fond retenue

La decision architecturale retenue est la suivante :

- le pipeline actuel de `FridaDev` n'est pas encore le pipeline hermeneutique complet ;
- `M6 Stimmung` n'est pas le noeud de convergence ;
- `M6 Stimmung` est un determinant du futur noeud ;
- le futur noeud devra arbitrer entre temps, memoire, web, identite, resume, contexte et `Stimmung` ;
- tant que ce noeud n'existe pas, toute validation globale du pipeline reste necessairement partielle.
