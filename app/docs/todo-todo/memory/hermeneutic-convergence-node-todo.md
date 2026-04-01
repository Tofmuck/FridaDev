# Noeud de convergence hermeneutique - roadmap mere

## Cadrage
Objet: piloter la construction du futur noeud de convergence hermeneutique a partir des references:
- `app/docs/states/architecture/hermeneutic_convergence_node.md`
- `app/docs/states/architecture/hermeneutic_convergence_node_matrix.md`

Regle de lecture:
- ce document est la roadmap mere unique du chantier;
- les docs d'architecture restent la norme, ce TODO est leur plan d'execution;
- les briques existantes continuent a alimenter le LLM principal pendant toute la construction du noeud;
- la convergence vise un dispositif en 2 etages: `noeud primaire -> validation agent`;
- le branchement aval consomme uniquement le verdict valide.

Regle de structuration forte:
- chaque lot est qualifie explicitement: `travail de structure` ou `travail de structure + pause normative`;
- une pause normative est bloquante: pas d'implementation avant contrat ecrit;
- pas de fichier monstre "par commodite" (pas de croissance vers 2000 lignes);
- une responsabilite doctrinale ou fonctionnelle autonome doit converger vers un doc normatif dedie puis un module/fichier dedie, sauf justification explicite;
- centraliser seulement ce qui doit l'etre, eviter les dependances laterales diffuses.

Modele cible de reference (hypothese architecturale actuelle):
- `GPT-5.4` pour l'agent hermeneutique de validation.

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
- Le noeud primaire emet un verdict premier et des directives provisoires.
- Le noeud primaire doit avoir un comportement fail-open explicite et auditable.
- L'agent hermeneutique de validation est juge de revision (`confirm|challenge|clarify|suspend`) et souverain sur la validation finale.
- L'agent de validation n'est pas souverain sur les criteres; les criteres restent fixes par les contrats normatifs.
- La sortie du noeud reste compacte, testable, auditable.
- Le chantier n'avance pas "dans le noir": observabilite minimale incrementale des le Lot 1.

## Structure code cible (documentaire)
- `app/core/hermeneutic_node/inputs/`: contrats d'entree canoniques et traduction runtime.
- `app/core/hermeneutic_node/doctrine/`: modules doctrinaux issus des docs normatifs.
- `app/core/hermeneutic_node/runtime/`: noeud primaire, etat, wiring technique, persistance.
- `app/core/hermeneutic_node/validation/`: agent hermeneutique de validation et sorties de revision.

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
Nature du lot: travail de structure.

Objectif: figer l'insertion du noeud et canoniser les entrees deja presentes sans casser l'injection directe actuelle vers le LLM principal.

Perimetre: insertion pipeline, temps, memoire recuperee, decision d'arbitrage memoire, resume, identite, contexte recent, web, observabilite minimale.

- [x] Figer explicitement le point d'insertion: apres `prepare_memory_context(...)`, avant `build_prompt_messages(...)`.
- [x] Definir l'objet canonique `temps` (NOW/TIMEZONE + derivees utiles).
- [x] Definir l'objet canonique `memoire_retrieved` (traces recuperees, metadonnees utiles).
- [x] Definir l'objet canonique `memory_arbitration` (decisions/statuts) distinct de `memoire_retrieved`.
- [x] Definir les objets canoniques `resume`, `identite`, `contexte_recent`, `web`.
- [x] Definir le contrat "double alimentation" (continue vers LLM principal + entree du noeud).
- [x] Definir une observabilite minimale de lot (presence/qualite des entrees + etape d'insertion), sans attendre le Lot 9.

Sortie attendue du lot: contrat d'entrees canoniques + point d'insertion officiel + socle d'observabilite minimale.
Validation minimale: schema d'entrees versionne et mappe 1:1 au pipeline reel, avec distinction explicite `memoire_retrieved` vs `memory_arbitration`.
Dependances: docs d'architecture noeud + matrice.
Hors scope: arbitrage global inter-sources et branchement aval complet.

## Lot 2 - Extraction fenetre recente + qualification minimale de la demande
Nature du lot: travail de structure + pause normative.

Objectif: isoler la matiere diffuse du tour en cours en separant clairement extraction mecanique et qualification semantique minimale.

Perimetre: `fenetre_recente`, `tour_utilisateur`, signaux d'ambiguite/sous-determination.

Sous-bloc A - Extraction simple:
- [x] Definir l'extraction canonique de `fenetre_recente` (selection, profondeur, horodatage, format).
- [x] Definir l'objet de sortie `fenetre_recente` exploitable sans interpretation metier forte.
- [x] Definir l'observabilite minimale de `fenetre_recente` au seam (presence/qualite minimale).

Sous-bloc B - Qualification semantique minimale:
- [x] Definir l'objet canonique `tour_utilisateur` (geste dialogique dominant, puis qualificateurs secondaires comme besoin de preuve et portee temporelle).
- [x] Definir les signaux minimaux d'ambiguite/sous-determination.
- [x] Definir la frontiere explicite entre qualification minimale et interpretation metier avancee.
- [ ] Definir l'observabilite minimale des objets canoniques / signaux du sous-bloc B des leur exposition au seam.

Pause normative obligatoire:
- Doc normatif a ouvrir: `hermeneutic-node-user-demand-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-user-demand-contract.md`
- Module code cible: `core.hermeneutic_node.inputs.user_turn`
- Repertoire code cible: `app/core/hermeneutic_node/inputs/`
- Fichier Python cible: `user_turn.py`
- Raison: la qualification du tour utilisateur et les signaux d'ambiguite sont doctrinaux; le contrat doit preceder le code.

Sortie attendue du lot: deux objets distincts et lisibles (`fenetre_recente`, `tour_utilisateur`) + signaux d'ambiguite.
Validation minimale: contrat de sortie qui distingue explicitement extraction mecanique et qualification semantique minimale.
Dependances: Lot 1.
Hors scope: posture de jugement finale et resolution de conflits inter-sources.

## Lot 3 - Integration de Stimmung / M6 comme determinant
Nature du lot: travail de structure + pause normative.

Objectif: integrer M6 comme determinant structurel du noeud sans double souverainete de directives.

Perimetre: interface `stimmung`, compatibilite FridaDev, articulation des directives.

- [ ] Definir l'interface canonique d'entree `stimmung` pour le noeud.
- [ ] Definir les champs minimaux utiles (etat, stabilite, regime derive, signaux de preuve).
- [ ] Distinguer explicitement les 2 artefacts `stimmung`: contrat d'entree (`inputs`) vs gouvernance doctrinale (`doctrine`).
- [ ] Trancher noir sur blanc: M6 fournit des signaux/determinants d'entree, pas la sortie finale aval.
- [ ] Trancher noir sur blanc: le noeud emet des `pipeline_directives_provisional`, la validation emet `pipeline_directives_final`.
- [ ] Definir la compatibilite minimale avec l'existant `FridaDev` sans import brutal de `Frida_V4`.

Pause normative obligatoire:
- Doc normatif a ouvrir: `hermeneutic-node-stimmung-input-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-stimmung-input-contract.md`
- Module code cible: `core.hermeneutic_node.inputs.stimmung`
- Repertoire code cible: `app/core/hermeneutic_node/inputs/`
- Fichier Python cible: `stimmung.py`
- Raison: fixer le contrat d'entree `stimmung` avant la gouvernance doctrinale.

Pause normative obligatoire:
- Doc normatif a ouvrir: `hermeneutic-node-stimmung-governance-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-stimmung-governance-contract.md`
- Module code cible: `core.hermeneutic_node.doctrine.stimmung_governance`
- Repertoire code cible: `app/core/hermeneutic_node/doctrine/`
- Fichier Python cible: `stimmung_governance.py`
- Raison: fixer une gouvernance unique `M6 -> noeud -> directives aval` avant implementation pour eviter les souverainetes concurrentes.

Sortie attendue du lot: contrat `stimmung` + gouvernance explicite `M6 -> noeud -> directives aval`.
Validation minimale: distinction explicite entre contrat d'entree `stimmung` et gouvernance doctrinale, avec regle anti-double-pilotage testable.
Dependances: Lots 1 et 2.
Hors scope: implementation runtime complete de M6.

## Lot 4 - Arbitrage epistemique
Nature du lot: travail de structure + pause normative.

Objectif: produire un statut epistemique explicite par tour et un regime de preuve associe.

Perimetre: `epistemic_regime`, `proof_regime`, `uncertainty_posture`.

- [ ] Definir les classes epistemiques minimales (`certain|probable|incertain|suspendu|contradictoire|a_verifier`).
- [ ] Definir les conditions minimales de passage entre classes.
- [ ] Definir un `proof_regime` compact coherent avec l'etat epistemique.
- [ ] Definir une `uncertainty_posture` explicite et non cosmetique.

Pause normative obligatoire:
- Doc normatif a ouvrir: `hermeneutic-node-epistemic-regime-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-epistemic-regime-contract.md`
- Module code cible: `core.hermeneutic_node.doctrine.epistemic_regime`
- Repertoire code cible: `app/core/hermeneutic_node/doctrine/`
- Fichier Python cible: `epistemic_regime.py`
- Raison: les classes epistemiques et leur regime de preuve sont doctrinaux et doivent etre stabilises avant code.

Sortie attendue du lot: composant d'arbitrage epistemique stable et lisible.
Validation minimale: table de decision compacte qui produit toujours une classe epistemique + un regime de preuve.
Dependances: Lots 1 a 3.
Hors scope: formulation finale de la reponse utilisateur.

## Lot 5 - Posture de jugement
Nature du lot: travail de structure + pause normative.

Objectif: operationaliser la sortie `answer | clarify | suspend` avec les signaux du Lot 2 et l'etat du Lot 4.

Perimetre: `judgment_posture`, criteres de decision, effets minimaux.

- [ ] Definir les criteres minimaux pour `answer`.
- [ ] Definir les criteres minimaux pour `clarify`.
- [ ] Definir les criteres minimaux pour `suspend`.
- [ ] Definir le lien explicite entre `judgment_posture`, signaux d'ambiguite (Lot 2) et `epistemic_regime` (Lot 4).

Pause normative obligatoire:
- Doc normatif a ouvrir: `hermeneutic-node-judgment-posture-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-judgment-posture-contract.md`
- Module code cible: `core.hermeneutic_node.doctrine.judgment_posture`
- Repertoire code cible: `app/core/hermeneutic_node/doctrine/`
- Fichier Python cible: `judgment_posture.py`
- Raison: la posture de jugement engage la doctrine de sortie et ne doit pas etre codee avant regle explicite.

Sortie attendue du lot: sortie `judgment_posture` explicite et auditable.
Validation minimale: regles de decision qui couvrent les 3 postures sans zone implicite.
Dependances: Lots 2 et 4.
Hors scope: UX detaillee des messages de clarification.

## Lot 6 - Hierarchie des sources
Nature du lot: travail de structure + pause normative.

Objectif: rendre explicite quelle source prime selon la demande et le contexte du tour.

Perimetre: memoire, web, identite, resume, contexte recent, temps, stimmung, demande utilisateur.

- [ ] Definir les regles minimales de priorisation entre sources.
- [ ] Definir les cas ou la demande utilisateur renverse la priorite par defaut.
- [ ] Definir le format compact de `source_priority`.
- [ ] Definir les cas de cohabitation de sources sans fusion abusive.

Pause normative obligatoire:
- Doc normatif a ouvrir: `hermeneutic-node-source-priority-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-source-priority-contract.md`
- Module code cible: `core.hermeneutic_node.doctrine.source_priority`
- Repertoire code cible: `app/core/hermeneutic_node/doctrine/`
- Fichier Python cible: `source_priority.py`
- Raison: la hierarchie des sources est une regle doctrinale centrale, a trancher avant implementation.

Sortie attendue du lot: hierarchie des sources stable et exploitable.
Validation minimale: chaque tour produit un ordre explicite de sources ou une regle explicite d'egalite.
Dependances: Lots 4 et 5.
Hors scope: moteur complet de resolution des conflits.

## Lot 7 - Conflits inter-sources
Nature du lot: travail de structure + pause normative.

Objectif: detecter et traiter les conflits explicites entre sources sans les masquer.

Perimetre: detection, explicitation, issue minimale de conflit.

- [ ] Definir les types minimaux de conflits inter-sources a couvrir.
- [ ] Definir le format compact de signalement d'un conflit.
- [ ] Definir les regles minimales d'issue (`prioriser | clarify | suspend`).
- [ ] Definir le lien entre conflit, `epistemic_regime` et `judgment_posture`.

Pause normative obligatoire:
- Doc normatif a ouvrir: `hermeneutic-node-source-conflict-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-source-conflict-contract.md`
- Module code cible: `core.hermeneutic_node.doctrine.source_conflicts`
- Repertoire code cible: `app/core/hermeneutic_node/doctrine/`
- Fichier Python cible: `source_conflicts.py`
- Raison: les regles de conflit inter-sources doivent etre explicites et stables avant implementation.

Sortie attendue du lot: mecanisme minimal de conflit inter-sources compatible avec l'auditabilite.
Validation minimale: un conflit detecte declenche obligatoirement une issue explicite et tracable.
Dependances: Lot 6.
Hors scope: explication longue source par source dans la reponse finale.

## Lot 8 - Etat persistant + sortie unique du noeud
Nature du lot: travail de structure + pause normative.

Objectif: stabiliser le noeud dans le temps et formaliser la sortie canonique complete.

Perimetre: etat precedent, inertie, `discursive_regime`, `resituation_level`, payload unique.

- [ ] Definir le schema minimal de persistance de l'etat du noeud par conversation.
- [ ] Definir les regles d'inertie (quand conserver ou changer un regime).
- [ ] Definir la sortie canonique `discursive_regime`.
- [ ] Definir la sortie canonique `resituation_level`.
- [ ] Definir la taxonomie canonique de `time_reference_mode` et son articulation avec `discursive_regime` / `resituation_level`.
- [ ] Definir le payload unique du noeud (incluant `epistemic_regime`, `proof_regime`, `judgment_posture`, `source_priority`, `time_reference_mode`, `pipeline_directives_provisional`).
- [ ] Definir le fail-open du noeud primaire (fallback minimal + auditabilite) sans effondrement du pipeline.
- [ ] Definir les champs minimaux d'auditabilite de ce payload.

Pause normative obligatoire:
- Doc normatif a ouvrir: `hermeneutic-node-output-regime-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-output-regime-contract.md`
- Module code cible: `core.hermeneutic_node.doctrine.output_regime`
- Repertoire code cible: `app/core/hermeneutic_node/doctrine/`
- Fichier Python cible: `output_regime.py`
- Raison: `discursive_regime` et `resituation_level` exigent une doctrine de sortie stable avant implementation.

Pause normative obligatoire:
- Doc normatif a ouvrir: `hermeneutic-node-state-persistence-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-state-persistence-contract.md`
- Module code cible: `core.hermeneutic_node.runtime.node_state`
- Repertoire code cible: `app/core/hermeneutic_node/runtime/`
- Fichier Python candidat: `node_state.py` (a confirmer)
- Raison: la persistance d'etat du noeud doit etre fixee contractuellement avant choix technique final.

Sortie attendue du lot: snapshot persistant + payload unique complet, compact et versionne.
Validation minimale: le payload de sortie couvre explicitement `discursive_regime`, `resituation_level` et `time_reference_mode`, avec fail-open primaire defini.
Dependances: Lots 4 a 7.
Hors scope: branchement aval complet et shadow globale.

## Lot 9 - Validation hermeneutique finale + branchement aval + observabilite + preconditions shadow globale
Nature du lot: travail de structure + pause normative.

Objectif: placer un agent hermeneutique de validation apres le noeud primaire et avant l'aval, puis brancher l'aval uniquement sur la sortie revisee.

Perimetre: validation agent, verdict final valide, branchement aval, observabilite du dispositif final, preconditions shadow.

- [ ] Definir le contrat de revision: entree = verdict primaire + justifications + directives provisoires + entrees canoniques.
- [ ] Definir les sorties de revision: `confirm | challenge | clarify | suspend`.
- [ ] Definir la table de combinaison normative entre `judgment_posture` primaire et decision de validation.
- [ ] Definir le format de sortie finale post-validation, dont `pipeline_directives_final`.
- [ ] Definir le contrat de branchement aval sur verdict valide uniquement (pas de consommation directe du verdict primaire).
- [ ] Definir le cadre operationnel du validation agent: budget token, timeout, fail-open, circuit breaker, cout/latence cible.
- [ ] Definir les signaux d'observabilite du dispositif final (noeud primaire + validation), sans inflation de logs.
- [ ] Definir les KPI minimaux de stabilite pour ce branchement.
- [ ] Definir les preconditions strictes d'une future shadow globale.
- [ ] Verifier que la shadow globale reste hors scope tant que ces preconditions ne sont pas remplies.

Pause normative obligatoire:
- Doc normatif a ouvrir: `hermeneutic-node-validation-agent-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-validation-agent-contract.md`
- Module code cible: `core.hermeneutic_node.validation.validation_agent`
- Repertoire code cible: `app/core/hermeneutic_node/validation/`
- Fichier Python cible: `validation_agent.py`
- Raison: la revision finale est souveraine sur la validation du verdict, la table de combinaison normative et le cadre operationnel; ce contrat doit preceder le code.

Sortie attendue du lot: chaine finalisee `noeud primaire -> validation agent -> aval` + observabilite complete + check-list pre-shadow.
Validation minimale: l'aval consomme explicitement une sortie revisee (`confirm|challenge|clarify|suspend`) et des `pipeline_directives_final`, jamais un verdict primaire brut.
Dependances: Lots 1, 5 et 8.
Hors scope: lancement operationnel de la shadow globale.
