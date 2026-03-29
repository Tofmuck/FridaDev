# Noeud de convergence hermeneutique - roadmap mere

## Cadrage
Objet: piloter la construction du futur noeud de convergence hermeneutique a partir des references:
- `app/docs/states/architecture/hermeneutic_convergence_node.md`
- `app/docs/states/architecture/hermeneutic_convergence_node_matrix.md`

Regle de lecture:
- ce document est la roadmap mere unique du chantier;
- les docs d'architecture restent la norme, ce TODO est leur plan d'execution;
- les briques existantes continuent a alimenter le LLM principal pendant toute la construction du noeud;
- la convergence vise un noeud central place clairement dans le pipeline, sans dependances laterales permanentes.

## Point d'insertion du noeud dans le pipeline reel
Contrainte structurante du chantier:
- dans `chat_service.chat_response(...)`, le noeud est place **apres** `prepare_memory_context(...)`;
- et **avant** `build_prompt_messages(...)`;
- ce point d'insertion est fixe des le Lot 1.

## Invariants
- M6 / Stimmung est un determinant du noeud, pas le noeud lui-meme.
- Tant que le noeud n'existe pas, la shadow globale du pipeline complet est hors de portee.
- La posture de jugement explicite doit exister: `answer | clarify | suspend`.
- Le noeud ne doit pas devenir un modele souverain opaque.
- Le noeud arbitre et emet la sortie finale aval; les determinants n'emettent pas des directives aval concurrentes.
- La sortie du noeud reste compacte, testable, auditable.
- Le chantier n'avance pas "dans le noir": observabilite minimale incrementale des le Lot 1.

## Vue d'ensemble en un coup d'oeil
Ce qui est deja la:
- temps, memoire, arbitrage memoire, resume, identite, contexte, web alimentent deja le pipeline.

Ce qui manque:
- qualification canonique de la demande;
- arbitrage epistemique explicite;
- posture de jugement explicite;
- hierarchie des sources + conflits inter-sources;
- etat persistant + sortie unique du noeud.

Natures de travail:
- canoniser depuis l'existant: Lot 1;
- extraire depuis l'existant: Lot 2;
- integrer depuis l'autre systeme: Lot 3;
- creer from scratch: Lots 4 a 9.

## Lot 1 - Canonisation des entrees existantes + insertion pipeline
Objectif: figer l'insertion du noeud et canoniser les entrees deja presentes sans casser l'injection directe actuelle vers le LLM principal.

Perimetre: insertion pipeline, temps, memoire recuperee, decision d'arbitrage memoire, resume, identite, contexte recent, web, observabilite minimale.

- [ ] Figer explicitement le point d'insertion: apres `prepare_memory_context(...)`, avant `build_prompt_messages(...)`.
- [ ] Definir l'objet canonique `temps` (NOW/TIMEZONE + derivees utiles).
- [ ] Definir l'objet canonique `memoire_retrieved` (traces recuperees, metadonnees utiles).
- [ ] Definir l'objet canonique `memory_arbitration` (decisions/statuts) distinct de `memoire_retrieved`.
- [ ] Definir les objets canoniques `resume`, `identite`, `contexte_recent`, `web`.
- [ ] Definir le contrat "double alimentation" (continue vers LLM principal + entree du noeud).
- [ ] Definir une observabilite minimale de lot (presence/qualite des entrees + etape d'insertion), sans attendre le Lot 9.

Sortie attendue du lot: contrat d'entrees canoniques + point d'insertion officiel + socle d'observabilite minimale.
Validation minimale: schema d'entrees versionne et mappe 1:1 au pipeline reel, avec distinction explicite `memoire_retrieved` vs `memory_arbitration`.
Dependances: docs d'architecture noeud + matrice.
Hors scope: arbitrage global inter-sources et branchement aval complet.

## Lot 2 - Extraction fenetre recente + qualification minimale de la demande
Objectif: isoler la matiere diffuse du tour en cours en separant clairement extraction mecanique et qualification semantique minimale.

Perimetre: `fenetre_recente`, `demande_utilisateur`, signaux d'ambiguite/sous-determination.

Sous-bloc A - Extraction simple:
- [ ] Definir l'extraction canonique de `fenetre_recente` (selection, profondeur, horodatage, format).
- [ ] Definir l'objet de sortie `fenetre_recente` exploitable sans interpretation metier forte.

Sous-bloc B - Qualification semantique minimale:
- [ ] Definir l'objet canonique `demande_utilisateur` (type de demande, besoin de preuve, portee temporelle).
- [ ] Definir les signaux minimaux d'ambiguite/sous-determination.
- [ ] Definir la frontiere explicite entre qualification minimale et interpretation metier avancee.

Sortie attendue du lot: deux objets distincts et lisibles (`fenetre_recente`, `demande_utilisateur`) + signaux d'ambiguite.
Validation minimale: contrat de sortie qui distingue explicitement extraction mecanique et qualification semantique minimale.
Dependances: Lot 1.
Hors scope: posture de jugement finale et resolution de conflits inter-sources.

## Lot 3 - Integration de Stimmung / M6 comme determinant
Objectif: integrer M6 comme determinant structurel du noeud sans double souverainete de directives.

Perimetre: interface `stimmung`, compatibilite FridaDev, articulation des directives.

- [ ] Definir l'interface canonique d'entree `stimmung` pour le noeud.
- [ ] Definir les champs minimaux utiles (etat, stabilite, regime derive, signaux de preuve).
- [ ] Trancher noir sur blanc: M6 fournit des signaux/determinants d'entree, pas la sortie finale aval.
- [ ] Trancher noir sur blanc: les `pipeline_directives` finales sont emises par le noeud de convergence.
- [ ] Definir la compatibilite minimale avec l'existant `FridaDev` sans import brutal de `Frida_V4`.

Sortie attendue du lot: contrat `stimmung` + gouvernance explicite `M6 -> noeud -> directives aval`.
Validation minimale: schema d'entree `stimmung` et regle anti-double-pilotage formalisee et testable.
Dependances: Lots 1 et 2.
Hors scope: implementation runtime complete de M6.

## Lot 4 - Arbitrage epistemique
Objectif: produire un statut epistemique explicite par tour et un regime de preuve associe.

Perimetre: `epistemic_regime`, `proof_regime`, `uncertainty_posture`.

- [ ] Definir les classes epistemiques minimales (`certain|probable|incertain|suspendu|contradictoire|a_verifier`).
- [ ] Definir les conditions minimales de passage entre classes.
- [ ] Definir un `proof_regime` compact coherent avec l'etat epistemique.
- [ ] Definir une `uncertainty_posture` explicite et non cosmetique.

Sortie attendue du lot: composant d'arbitrage epistemique stable et lisible.
Validation minimale: table de decision compacte qui produit toujours une classe epistemique + un regime de preuve.
Dependances: Lots 1 a 3.
Hors scope: formulation finale de la reponse utilisateur.

## Lot 5 - Posture de jugement
Objectif: operationaliser la sortie `answer | clarify | suspend` avec les signaux du Lot 2 et l'etat du Lot 4.

Perimetre: `judgment_posture`, criteres de decision, effets minimaux.

- [ ] Definir les criteres minimaux pour `answer`.
- [ ] Definir les criteres minimaux pour `clarify`.
- [ ] Definir les criteres minimaux pour `suspend`.
- [ ] Definir le lien explicite entre `judgment_posture`, signaux d'ambiguite (Lot 2) et `epistemic_regime` (Lot 4).

Sortie attendue du lot: sortie `judgment_posture` explicite et auditable.
Validation minimale: regles de decision qui couvrent les 3 postures sans zone implicite.
Dependances: Lots 2 et 4.
Hors scope: UX detaillee des messages de clarification.

## Lot 6 - Hierarchie des sources
Objectif: rendre explicite quelle source prime selon la demande et le contexte du tour.

Perimetre: memoire, web, identite, resume, contexte recent, temps, stimmung, demande utilisateur.

- [ ] Definir les regles minimales de priorisation entre sources.
- [ ] Definir les cas ou la demande utilisateur renverse la priorite par defaut.
- [ ] Definir le format compact de `source_priority`.
- [ ] Definir les cas de cohabitation de sources sans fusion abusive.

Sortie attendue du lot: hierarchie des sources stable et exploitable.
Validation minimale: chaque tour produit un ordre explicite de sources ou une regle explicite d'egalite.
Dependances: Lots 4 et 5.
Hors scope: moteur complet de resolution des conflits.

## Lot 7 - Conflits inter-sources
Objectif: detecter et traiter les conflits explicites entre sources sans les masquer.

Perimetre: detection, explicitation, issue minimale de conflit.

- [ ] Definir les types minimaux de conflits inter-sources a couvrir.
- [ ] Definir le format compact de signalement d'un conflit.
- [ ] Definir les regles minimales d'issue (`prioriser | clarify | suspend`).
- [ ] Definir le lien entre conflit, `epistemic_regime` et `judgment_posture`.

Sortie attendue du lot: mecanisme minimal de conflit inter-sources compatible avec l'auditabilite.
Validation minimale: un conflit detecte declenche obligatoirement une issue explicite et tracable.
Dependances: Lot 6.
Hors scope: explication longue source par source dans la reponse finale.

## Lot 8 - Etat persistant + sortie unique du noeud
Objectif: stabiliser le noeud dans le temps et formaliser la sortie canonique complete.

Perimetre: etat precedent, inertie, `discursive_regime`, `resituation_level`, payload unique.

- [ ] Definir le schema minimal de persistance de l'etat du noeud par conversation.
- [ ] Definir les regles d'inertie (quand conserver ou changer un regime).
- [ ] Definir la sortie canonique `discursive_regime`.
- [ ] Definir la sortie canonique `resituation_level`.
- [ ] Definir le payload unique du noeud (incluant `epistemic_regime`, `proof_regime`, `judgment_posture`, `source_priority`, `time_reference_mode`, `pipeline_directives`).
- [ ] Definir les champs minimaux d'auditabilite de ce payload.

Sortie attendue du lot: snapshot persistant + payload unique complet, compact et versionne.
Validation minimale: le payload de sortie couvre explicitement `discursive_regime` et `resituation_level` sans champ implicite critique.
Dependances: Lots 4 a 7.
Hors scope: branchement aval complet et shadow globale.

## Lot 9 - Branchement aval + observabilite du noeud + preconditions shadow globale
Objectif: brancher les directives du noeud vers l'aval, finaliser son observabilite, et fixer les preconditions d'une future shadow globale.

Perimetre: branchement des directives, observabilite du noeud, preconditions shadow.

- [ ] Definir le contrat de branchement des `pipeline_directives` vers les modules aval.
- [ ] Definir les signaux d'observabilite du noeud (decisions, transitions, conflits, charge), sans inflation de logs.
- [ ] Definir les KPI minimaux de stabilite pour ce branchement.
- [ ] Definir les preconditions strictes d'une future shadow globale.
- [ ] Verifier que la shadow globale reste hors scope tant que ces preconditions ne sont pas remplies.

Sortie attendue du lot: integration aval preparee + observabilite du noeud complete + check-list pre-shadow.
Validation minimale: checklist de preconditions shadow fermee et explicitement dependante de la stabilite du noeud branche.
Dependances: Lots 1 et 8.
Hors scope: lancement operationnel de la shadow globale.
