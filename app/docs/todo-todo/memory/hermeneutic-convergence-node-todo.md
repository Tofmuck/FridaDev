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

## Lot 2 - Extraction fenetre recente + qualification minimale du tour utilisateur
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
- [x] Definir l'observabilite minimale des objets canoniques / signaux du sous-bloc B des leur exposition au seam.

Pause normative obligatoire:
- Doc normatif a ouvrir: `hermeneutic-node-user-demand-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-user-demand-contract.md`
- Module code cible: `core.hermeneutic_node.inputs.user_turn_input`
- Repertoire code cible: `app/core/hermeneutic_node/inputs/`
- Fichier Python cible: `user_turn_input.py`
- Raison: la qualification du tour utilisateur et les signaux d'ambiguite sont doctrinaux; le contrat doit preceder le code.

Sortie attendue du lot: deux objets distincts et lisibles (`fenetre_recente`, `tour_utilisateur`) + signaux d'ambiguite.
Validation minimale: contrat de sortie qui distingue explicitement extraction mecanique et qualification semantique minimale.
Dependances: Lot 1.
Hors scope: posture de jugement finale et resolution de conflits inter-sources.

## Lot 3 - Signal affectif amont + stimmung stabilisee
Nature du lot: travail de structure + pause normative.

Objectif: cadrer un signal affectif par tour et une `stimmung` stabilisee pour le noeud, sans importer la machine `M6` complete de `Frida_V4`.

Perimetre: `stimmung_agent.py`, `affective_turn_signal`, `stimmung_input.py`, stabilisation minimale, usage par le noeud pour le regime d'enonciation.

Sous-bloc A - Signal affectif par tour:
- [x] Definir le contrat minimal de `affective_turn_signal` produit par `stimmung_agent.py`.
- [x] Definir les grands groupes affectifs utilises dans `FridaDev` (taxonomie large, multi-`tones`, sans micro-taxonomie fine).
- [x] Trancher noir sur blanc: le signal amont est produit par tour, peut contenir plusieurs `tones`, et ne calcule pas a lui seul la `stimmung` stabilisee.

Runtime amont isole deja ferme:
- [x] Creer `stimmung_agent.py` comme agent LLM amont isole.
- [x] Creer le prompt systeme `stimmung_agent.txt`.
- [x] Fermer le modele principal `openai/gpt-5.4-mini` et le fallback `openai/gpt-5.4-nano`.
- [x] Fermer le format JSON strict de `affective_turn_signal`.
- [x] Fermer le calcul contextualise de `affective_turn_signal` sur une fenetre courte issue de `recent_window_input` (`5` tours max), tout en restant centre sur le tour courant.
- [x] Fermer le fail-open compact du stage amont.
- [x] Fermer l'observability amont via `chat_turn_logger`.
- [x] Fermer l'appel amont depuis `chat_service.py`, sans injection au seam hermeneutique.

Sous-bloc B - Stimmung stabilisee pour le noeud:
- [x] Definir le contrat minimal de `stimmung` exposee par `stimmung_input.py`.
- [x] Definir la frontiere stricte entre `affective_turn_signal` brut et `stimmung` stabilisee.
- [x] Definir la mecanique minimale de stabilisation (seuils, `delta`, `hysteresis`, `turns_considered`) au niveau de `stimmung_input.py`.
- [x] Retenir `message.meta.affective_turn_signal` comme source runtime compacte et relisible des signaux recents pour `stimmung_input.py`.
- [x] Definir le branchement minimal de `stimmung_input.py` dans `chat_service.py` avant le seam hermeneutique.
- [x] Rappeler noir sur blanc: le noeud recoit `stimmung` pour le regime d'enonciation, pas la machine `M6` complete.

Sous-bloc C - Fermeture doctrinale:
- [x] Trancher noir sur blanc qu'aucune doctrine dediee d'usage de `stimmung` n'est retenue a ce stade ; son interpretation appartient au noeud comme traitement d'un determinant d'entree parmi d'autres.
- [x] Rappeler noir sur blanc qu'aucune importation brute de la gouvernance `M6` de `Frida_V4` n'est admise.

Socle normatif de reference:
- Doc normatif: `hermeneutic-node-stimmung-input-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-stimmung-input-contract.md`
- Modules code cibles: `core.stimmung_agent` et `core.hermeneutic_node.inputs.stimmung_input`
- Repertoires code cibles: `app/core/` et `app/core/hermeneutic_node/inputs/`
- Fichiers Python cibles: `stimmung_agent.py` et `stimmung_input.py`
- Raison: garder la separation stricte entre signal brut par tour et input stabilise pendant la suite de l'implementation runtime.

Sortie attendue du lot: contrat `affective_turn_signal` + contrat `stimmung` stabilisee + separation stricte `stimmung_agent.py` / `stimmung_input.py`.
Validation minimale: distinction explicite entre signal brut par tour, `stimmung` stabilisee et absence de doctrine dediee supplementaire, sans import complet de `M6`.
Dependances: Lots 1 et 2.
Hors scope: implementation runtime complete de `M6`, gouvernance affective complete, directives finales aval.

## Lot 4 - Arbitrage epistemique
Nature du lot: travail de structure + pause normative.

Objectif: produire un statut epistemique explicite par tour et un regime de preuve associe.

Perimetre: `epistemic_regime`, `proof_regime`, `uncertainty_posture`.

- [x] Definir les classes epistemiques minimales (`certain|probable|incertain|suspendu|contradictoire|a_verifier`).
- [x] Definir les conditions minimales de passage entre classes.
- [x] Definir un `proof_regime` compact coherent avec l'etat epistemique.
- [x] Definir une `uncertainty_posture` explicite et non cosmetique.
- [x] Trancher noir sur blanc que `epistemic_regime`, `proof_regime` et `uncertainty_posture` sont des sorties doctrinales du noeud, pas des inputs canoniques.

Pause normative obligatoire:
- Doc normatif: `hermeneutic-node-epistemic-regime-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-epistemic-regime-contract.md`
- Module code cible: `core.hermeneutic_node.doctrine.epistemic_regime`
- Repertoire code cible: `app/core/hermeneutic_node/doctrine/`
- Fichier Python cible: `epistemic_regime.py`
- Raison: les classes epistemiques et leur regime de preuve sont doctrinaux et doivent etre stabilises avant code.

Sortie attendue du lot: contrat doctrinal d'arbitrage epistemique stable et lisible.
Validation minimale: taxonomie minimale + conditions de passage + `proof_regime` + `uncertainty_posture` ecrits noir sur blanc dans la spec de reference.
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

Perimetre: memoire, web, identite, resume, contexte recent, temps, stimmung, tour_utilisateur.

- [ ] Definir les regles minimales de priorisation entre sources.
- [ ] Definir les cas ou certains signaux du `tour_utilisateur` renversent la priorite par defaut.
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
