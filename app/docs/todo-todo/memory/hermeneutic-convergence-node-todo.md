# Noeud de convergence hermeneutique - roadmap mere

## Cadrage
Objet: piloter la construction du futur noeud de convergence hermeneutique a partir des references:
- `app/docs/states/architecture/hermeneutic_convergence_node.md`
- `app/docs/states/architecture/hermeneutic_convergence_node_matrix.md`

Regle de lecture:
- ce document est la roadmap mere unique du chantier;
- il ne remplace pas les documents d'architecture, il les convertit en plan d'execution;
- pendant toute la construction du noeud, les briques existantes continuent a alimenter directement le LLM principal;
- en parallele, ces briques deviennent des entrees canoniques du noeud.

## Invariants
- [ ] M6 / Stimmung est un determinant du noeud, pas le noeud lui-meme.
- [ ] Tant que le noeud n'existe pas, la shadow globale du pipeline complet reste hors de portee.
- [ ] La posture de jugement explicite doit exister: `answer | clarify | suspend`.
- [ ] Le noeud ne doit pas devenir un modele souverain opaque.
- [ ] La sortie du noeud doit rester compacte, testable et auditable.

## Vue d'ensemble
Deja disponible:
- briques temps, memoire, resume, identite, contexte, web et arbitrage memoire actives dans le pipeline actuel;
- bonne observabilite locale de sous-pipelines;
- matrice de cadrage qui distingue clairement ce qui est deja la, a canoniser, a extraire, a integrer, a creer.

Manques majeurs:
- qualification canonique de la demande utilisateur et fenetre recente exploitable par le noeud;
- arbitrage epistemique explicite et posture de jugement;
- hierarchie stable des sources et gestion des conflits inter-sources;
- etat persistant + payload unique du noeud + directives aval unifiees.

Pourquoi une seule roadmap:
- garder un ordre de construction unique;
- eviter 9 TODOs concurrents qui fragmentent le pilotage;
- conserver une lecture simple des dependances entre lots.

Nature du travail cible:
- a canoniser depuis l'existant: Lot 1;
- a extraire depuis l'existant: Lot 2;
- a integrer depuis l'autre systeme: Lot 3 (M6/Stimmung);
- a creer from scratch: Lots 4 a 9.

## Lot 1 - Canonisation des entrees existantes
Objectif: transformer les briques deja presentes en entrees canoniques du noeud sans casser l'injection directe actuelle vers le LLM principal.

Perimetre: temps, memoire RAG, arbitrage memoire, resume actif, identite, contexte recent, web.

- [ ] Definir un contrat d'entree canonique `temps` (NOW/TIMEZONE + derivees temporelles utiles).
- [ ] Definir un contrat d'entree canonique `memoire` (traces + statut d'arbitrage).
- [ ] Definir un contrat d'entree canonique `resume`.
- [ ] Definir un contrat d'entree canonique `identite`.
- [ ] Definir un contrat d'entree canonique `contexte_recent`.
- [ ] Definir un contrat d'entree canonique `web` (fraicheur, autorite relative, conflit potentiel).

Sortie attendue du lot: schema minimal des entrees canoniques deja existantes et branchables dans le noeud.
Dependances: docs d'architecture noeud + matrice.
Hors scope: modification du prompt final et arbitrage global inter-sources.

## Lot 2 - Extraction fenetre recente + demande utilisateur
Objectif: extraire ce qui est encore diffus pour fournir au noeud une lecture immediate du tour en cours.

Perimetre: fenetre conversationnelle recente, qualification de la demande, signaux d'ambiguite/sous-determination.

- [ ] Definir l'objet canonique `fenetre_recente` (selection, profondeur, role dans le noeud).
- [ ] Definir l'objet canonique `demande_utilisateur` (type, intention, exigences de preuve).
- [ ] Definir les signaux minimaux d'ambiguite et de sous-determination.
- [ ] Poser la frontiere entre extraction structuree et interpretation metier.

Sortie attendue du lot: contrat d'entree exploitable pour `fenetre_recente` et `demande_utilisateur`.
Dependances: Lot 1.
Hors scope: posture de jugement finale et resolution de conflits inter-sources.

## Lot 3 - Integration de Stimmung / M6 comme determinant
Objectif: integrer M6 comme determinant structurel sans confondre M6 avec le noeud de convergence.

Perimetre: interface d'entree `Stimmung`, stabilite de regime, directives structurantes minimales.

- [ ] Definir l'interface canonique d'entree `stimmung` pour le noeud.
- [ ] Poser les champs minimaux utiles au noeud (etat, stabilite, regime derive).
- [ ] Definir la compatibilite minimale avec l'existant `FridaDev` sans copier `Frida_V4` en bloc.
- [ ] Verifier que `stimmung` reste un determinant parmi d'autres.

Sortie attendue du lot: contrat d'entree `stimmung` explicite, borné et non souverain.
Dependances: Lots 1 et 2.
Hors scope: implementation complete de M6 dans le runtime.

## Lot 4 - Arbitrage epistemique
Objectif: produire un statut epistemique explicite par tour pour eviter les certitudes implicites.

Perimetre: classes `certain | probable | incertain | suspendu | contradictoire | a_verifier`.

- [ ] Definir les classes epistemiques minimales du noeud.
- [ ] Definir les conditions minimales de passage d'une classe a l'autre.
- [ ] Definir la forme de sortie compacte du regime epistemique.
- [ ] Definir les limites de confiance et les cas de suspension legitime.

Sortie attendue du lot: composant d'arbitrage epistemique contractuel et testable.
Dependances: Lots 1 a 3.
Hors scope: redaction finale de la reponse utilisateur.

## Lot 5 - Posture de jugement
Objectif: rendre explicite la decision de sortie du noeud: repondre, demander clarification, ou suspendre.

Perimetre: `answer | clarify | suspend`.

- [ ] Definir les criteres minimaux pour `answer`.
- [ ] Definir les criteres minimaux pour `clarify`.
- [ ] Definir les criteres minimaux pour `suspend`.
- [ ] Definir le lien explicite entre posture de jugement et regime epistemique.

Sortie attendue du lot: sortie `judgment_posture` explicite, auditable et exploitable en aval.
Dependances: Lot 4.
Hors scope: strategie UX detaillee des messages de clarification.

## Lot 6 - Hierarchie des sources
Objectif: rendre explicite quelle source prime selon la demande et le contexte du tour.

Perimetre: memoire, web, identite, resume, contexte recent, temps, stimmung, demande utilisateur.

- [ ] Definir les regles minimales de priorisation entre sources.
- [ ] Definir les cas ou la demande utilisateur renverse la priorite par defaut.
- [ ] Definir le format compact de `source_priority`.
- [ ] Definir les cas de cohabitation de sources sans fusion abusive.

Sortie attendue du lot: hierarchie des sources stable et lisible pour le noeud.
Dependances: Lots 1 a 5.
Hors scope: moteur complet de resolution de conflits.

## Lot 7 - Conflits inter-sources
Objectif: detecter et traiter les conflits explicites entre sources sans les masquer.

Perimetre: detection, explicitation, issue minimale.

- [ ] Definir les types minimaux de conflits inter-sources a couvrir.
- [ ] Definir le format de signalement compact d'un conflit.
- [ ] Definir les regles minimales d'issue (prioriser, suspendre, demander precision).
- [ ] Definir le lien entre conflit, regime epistemique et posture de jugement.

Sortie attendue du lot: mecanisme minimal de conflit inter-sources compatible avec l'auditabilite du noeud.
Dependances: Lots 4 a 6.
Hors scope: explication longue source par source dans la reponse finale.

## Lot 8 - Etat persistant + sortie unique du noeud
Objectif: stabiliser le noeud dans le temps et produire un payload unique de sortie.

Perimetre: etat precedent, inertie/stabilite, payload canonique du noeud.

- [ ] Definir le schema minimal de persistance de l'etat du noeud par conversation.
- [ ] Definir les regles d'inertie (quand conserver ou changer un regime).
- [ ] Definir le payload unique du noeud (regimes, posture, priorites, directives).
- [ ] Definir les champs minimaux d'auditabilite de ce payload.

Sortie attendue du lot: snapshot persistant + sortie unique et versionnee du noeud.
Dependances: Lots 1 a 7.
Hors scope: observabilite globale complete et shadow globale.

## Lot 9 - Branchement aval + observabilite + preconditions shadow globale
Objectif: brancher les directives du noeud vers l'aval et preparer une shadow globale future sans la lancer.

Perimetre: directives aval, traces du noeud, criteres d'entree en shadow globale.

- [ ] Definir le contrat de branchement des directives du noeud vers les modules aval.
- [ ] Definir les signaux d'observabilite minimaux du noeud (sans inflation de logs).
- [ ] Definir les preconditions strictes d'une future shadow globale.
- [ ] Verifier que la shadow globale reste explicitement hors scope tant que ces preconditions ne sont pas remplies.

Sortie attendue du lot: integration aval preparatoire + check-list de preconditions shadow globale.
Dependances: Lot 8.
Hors scope: lancement operationnel de la shadow globale.
