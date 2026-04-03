# Noeud de convergence hermeneutique - roadmap mere cloturee

## Statut de cloture
Cloture documentaire: 2026-04-03
Statut: archivee dans `app/docs/todo-done/refactors/`

Resultat reel cloture:
- Lot 9 est ferme et la cible runtime retenue est active: `HERMENEUTIC_MODE=enforced_all`
- pipeline observable: `stimmung_agent -> primary_node -> validation_agent -> aval`
- surfaces live: `/log`, `/hermeneutic-admin`, `GET /api/admin/hermeneutics/dashboard`
- marqueurs d'enforcement reel: `memory_mode_apply.source=arbiter_enforced`, `identity_mode_apply.action=persist_enforced`
- observabilite OpenRouter: distinction `estimated_*` / `provider_*`, `HTTP-Referer` et `X-OpenRouter-Title` distincts par composant

Regle de lecture:
- ce document est conserve comme trace de chantier cloture;
- il ne pilote plus un travail actif;
- la reference active memoire/hermeneutique restante est `app/docs/todo-todo/memory/hermeneutical-add-todo.md`.

## Cadrage
Objet historique: piloter la construction du futur noeud de convergence hermeneutique a partir des references:
- `app/docs/states/architecture/hermeneutic_convergence_node.md`
- `app/docs/states/architecture/hermeneutic_convergence_node_matrix.md`

Regle de lecture historique:
- ce document a ete la roadmap mere unique du chantier jusqu'a la cloture du 2026-04-03;
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

- [x] Trancher noir sur blanc que `judgment_posture` est une sortie doctrinale du noeud: posture primaire de parole et de jugement, pas input canonique, pas validation finale, pas simple routing d'action.
- [x] Definir les criteres minimaux pour `answer`.
- [x] Definir les criteres minimaux pour `clarify`.
- [x] Definir les criteres minimaux pour `suspend`, en explicitant que `suspend` = reponse de suspension du jugement et non absence de reponse.
- [x] Definir le lien explicite entre `judgment_posture`, signaux d'ambiguite (Lot 2) et `epistemic_regime` (Lot 4).

Pause normative obligatoire:
- Doc normatif: `hermeneutic-node-judgment-posture-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-judgment-posture-contract.md`
- Module code cible: `core.hermeneutic_node.doctrine.judgment_posture`
- Repertoire code cible: `app/core/hermeneutic_node/doctrine/`
- Fichier Python cible: `judgment_posture.py`
- Raison: la posture de jugement engage la doctrine de sortie et ne doit pas etre codee avant regle explicite.

Sortie attendue du lot: sortie `judgment_posture` explicite et auditable.
Validation minimale: definitions minimales de `answer | clarify | suspend` + articulation explicite Lot 2 / Lot 4, sans confusion entre posture de parole et validation finale.
Dependances: Lots 2 et 4.
Hors scope: UX detaillee des messages de clarification.

## Lot 6 - Hierarchie des sources
Nature du lot: travail de structure + pause normative.

Objectif: rendre explicite quelle source prime selon la demande et le contexte du tour.

Perimetre: memoire, web, identite, resume, contexte recent, temps, stimmung, tour_utilisateur.

- [x] Definir les regles minimales de priorisation entre sources.
- [x] Definir les cas ou certains signaux du `tour_utilisateur` renversent la priorite par defaut.
- [x] Definir le format compact de `source_priority`.
- [x] Definir les cas de cohabitation de sources sans fusion abusive.

Pause normative obligatoire:
- Doc normatif: `hermeneutic-node-source-priority-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-source-priority-contract.md`
- Module code cible: `core.hermeneutic_node.doctrine.source_priority`
- Repertoire code cible: `app/core/hermeneutic_node/doctrine/`
- Fichier Python cible: `source_priority.py`
- Raison: la hierarchie des sources est une regle doctrinale centrale, a trancher avant implementation.

Sortie attendue du lot: hierarchie des sources stable et exploitable, avec ordre par defaut, renversements minimaux et format compact de rangs.
Validation minimale: ordre explicite de rangs avec egalites, statut special de `tour_utilisateur` et `temps`, `identity` maintenu comme famille top-level unique avec regle interne `static > dynamic`, et `web` pose comme faible priorite par defaut mais forte priorite conditionnelle.
Dependances: Lots 4 et 5.
Hors scope: moteur complet de resolution des conflits.

## Lot 7 - Conflits inter-sources
Nature du lot: travail de structure + pause normative.

Objectif: detecter et traiter les conflits explicites entre sources sans les masquer.

Perimetre: detection, explicitation, seuil strict de detection, issue minimale de clarification.

- [x] Definir les types minimaux de conflits inter-sources residuels a couvrir.
- [x] Definir le seuil strict de detection et le format compact de signalement d'un conflit.
- [x] Definir les regles minimales d'issue (`clarify`), en ecartant `prioriser` comme doublon du Lot 6 et `suspend` comme issue normale du conflit residuel.
- [x] Definir le lien entre conflit, `source_priority`, `epistemic_regime` et `judgment_posture`.

Pause normative obligatoire:
- Doc normatif: `hermeneutic-node-source-conflict-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-source-conflict-contract.md`
- Module code cible: `core.hermeneutic_node.doctrine.source_conflicts`
- Repertoire code cible: `app/core/hermeneutic_node/doctrine/`
- Fichier Python cible: `source_conflicts.py`
- Raison: les regles de conflit inter-sources doivent etre explicites et stables avant implementation.

Sortie attendue du lot: mecanisme minimal de conflit inter-sources residuel compatible avec l'auditabilite, sans reouvrir la priorisation normale du Lot 6.
Validation minimale: un conflit residuel detecte produit un signal compact et une issue explicite `clarify`, sans pousser par defaut vers `suspend`.
Dependances: Lot 6.
Hors scope: explication longue source par source dans la reponse finale.

## Lot 8 - Etat persistant + sortie unique du noeud
Nature du lot: travail de structure + pause normative.

Objectif: stabiliser le noeud dans le temps et formaliser la sortie canonique complete.

Perimetre: etat precedent, inertie, `discursive_regime`, `resituation_level`, payload unique.
Etat du lot: ferme (normatif + runtime).

- [x] Definir le schema minimal de persistance de l'etat du noeud par conversation.
- [x] Definir les regles d'inertie (quand conserver ou changer un regime).
- [x] Definir la sortie canonique `discursive_regime`.
- [x] Definir la sortie canonique `resituation_level`.
- [x] Definir la taxonomie canonique de `time_reference_mode` et son articulation avec `discursive_regime` / `resituation_level`.
- [x] Definir le payload unique du noeud (incluant `schema_version`, `epistemic_regime`, `proof_regime`, `uncertainty_posture`, `judgment_posture`, `discursive_regime`, `resituation_level`, `time_reference_mode`, `source_priority`, `source_conflicts`, `pipeline_directives_provisional` et un bloc `audit` minimal).
- [x] Definir le fail-open du noeud primaire (meme forme canonique de payload + fallback explicite) sans effondrement du pipeline.
- [x] Definir les champs minimaux d'auditabilite de ce payload.

Pause normative fermee:
- Doc normatif: `hermeneutic-node-output-regime-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-output-regime-contract.md`
- Module code cible: `core.hermeneutic_node.doctrine.output_regime`
- Repertoire code cible: `app/core/hermeneutic_node/doctrine/`
- Fichier Python cible: `output_regime.py`
- Raison: le sous-bloc doctrinal `output_regime` est maintenant pose pour `discursive_regime`, `resituation_level` et `time_reference_mode`, sans fermer encore la persistance d'etat.

Pause normative fermee:
- Doc normatif: `hermeneutic-node-state-persistence-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-state-persistence-contract.md`
- Module code cible: `core.hermeneutic_node.runtime.node_state`
- Repertoire code cible: `app/core/hermeneutic_node/runtime/`
- Fichier Python cible: `node_state.py`
- Raison: le sous-bloc runtime `node_state` est maintenant pose comme state de pilotage conversation-scoped, distinct du payload complet, des logs et des futurs snapshots d'audit.

Pause normative fermee:
- Doc normatif: `hermeneutic-node-primary-verdict-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-primary-verdict-contract.md`
- Module code cible: `core.hermeneutic_node.runtime.primary_node`
- Repertoire code cible: `app/core/hermeneutic_node/runtime/`
- Fichier Python cible: `primary_node.py`
- Raison: le verdict primaire unique est maintenant pose avec une forme canonique minimale, un fail-open primaire explicite et un bloc d'auditabilite minimal, sans fermer encore la validation finale.

Resultat du lot ferme: `output_regime` doctrinal calcule, `node_state` minimal conversation-scoped, `primary_verdict` canonique unique, fail-open primaire explicite et inertie bornee.
Validation minimale des sous-pas fermes: `output_regime` couvre explicitement `discursive_regime`, `resituation_level` et `time_reference_mode`; `state_persistence` fixe un `node_state` minimal conversation-scoped et des regles d'inertie bornees; `primary_verdict` fixe la forme canonique unique du verdict primaire, le fail-open primaire explicite et un bloc d'auditabilite minimal; l'audit hermeneutique complet par tour et la validation finale restent ouverts.
Dependances: Lots 4 a 7.
Hors scope: branchement aval complet et shadow globale.

## Lot 9 - Validation hermeneutique finale + branchement aval + observabilite + preconditions shadow globale
Nature du lot: travail de structure + pause normative.

Objectif: placer un agent hermeneutique de validation apres le noeud primaire et avant l'aval, puis brancher l'aval uniquement sur la sortie revisee.

Perimetre: validation agent, verdict final valide, branchement aval, integration admin des deux agents LLM hermeneutiques reels du pipeline, surfaces logs/inspection du dispositif final, preconditions de bascule full avec observabilite maintenue, et garde-fou shadow transitoire.
Etat du lot: ferme (runtime + documentation).

- [x] Definir le contrat de revision: entree = verdict primaire + justifications + `validation_dialogue_context` + directives provisoires + entrees canoniques.
- [x] Definir les sorties de revision: `confirm | challenge | clarify | suspend`.
- [x] Definir la table de combinaison normative entre `judgment_posture` primaire et decision de validation.
- [x] Definir le format de sortie finale post-validation, dont `pipeline_directives_final`.
- [x] Definir le contrat de branchement aval sur verdict valide uniquement (pas de consommation directe du verdict primaire, projection aval en prose `[JUGEMENT HERMENEUTIQUE]` derivee de `validated_output`).
- [x] Definir le cadre operationnel du validation agent: budget token, timeout, fail-open, circuit breaker, cout/latence cible.
- [x] Integrer dans l'admin runtime settings les deux agents LLM hermeneutiques reels du pipeline, `stimmung_agent` et `validation_agent`, avec identites explicites, lecture/edition DB et surfaces read-only alignees sur `main_model`, `arbiter_model` et `summary_model`; `primary_node` reste une etape runtime du pipeline et ne devient pas une fausse section "modele".
- [x] Etendre la vue `Logs applicatifs` pour montrer de facon synthetique les grandes etapes du pipeline hermeneutique par tour: activite amont du `stimmung_agent`, verdict/sortie du `primary_node`, entree/sortie du `validation_agent`, statut ok/erreur, sans dump integral des payloads internes.
- [x] Ajouter `Hermeneutic admin`, surface admin HTML distincte de `Logs applicatifs`, detaillee et majoritairement read-only, reprenant `admin.css`, le meme langage visuel que l'admin existante et une logique less is more sobre/compacte; l'acces depuis les autres surfaces admin se fait dans la meme fenetre, l'ouverture depuis la surface principale se fait dans un autre onglet ou une autre fenetre.
- [x] Definir les preconditions concretes d'une bascule full au redemarrage de Frida/du conteneur a partir de cette infrastructure reelle: cible exacte `HERMENEUTIC_MODE=enforced_all`, checklist pre-restart et post-restart immediate, verification via `/log`, `/hermeneutic-admin`, dashboard hermeneutique et `GET /api/admin/logs`, route backend-only `POST /api/admin/restart`, et maintien explicite d'un fonctionnement runtime reel avec observabilite. Doc operations: `app/docs/states/operations/hermeneutic-full-rollout-preconditions.md`.
- [x] Verifier que la shadow globale reste un garde-fou transitoire et hors scope tant que ces preconditions admin/logs/inspection/restart ne sont pas remplies; la cible finale normale du lot reste un runtime full avec observabilite et inspection detaillee, pas un mode `shadow-only`. Doctrine finale absorbee dans `app/docs/states/operations/hermeneutic-full-rollout-preconditions.md`.

Pause normative fermee:
- Doc normatif: `hermeneutic-node-validation-agent-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-validation-agent-contract.md`
- Module code cible: `core.hermeneutic_node.validation.validation_agent`
- Repertoire code cible: `app/core/hermeneutic_node/validation/`
- Fichier Python cible: `validation_agent.py`
- Raison: la revision finale est souveraine sur la validation du verdict, mais le validation agent V1 doit d'abord etre pose comme juge borne, en une passe, relisant `primary_verdict` avec un `validation_dialogue_context` recent elargi comme matiere hermeneutique principale; ce contrat doit preceder le code.

Pause normative fermee:
- Doc normatif: `hermeneutic-node-validated-output-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-validated-output-contract.md`
- Module code cible: `core.hermeneutic_node.validation.validation_agent`
- Repertoire code cible: `app/core/hermeneutic_node/validation/`
- Fichier Python cible: `validation_agent.py`
- Raison: la sortie finale aval-consommable est maintenant posee avec une table de combinaison compacte, un `final_judgment_posture` explicite, et un statut ferme de `pipeline_directives_final`, sans fermer encore le wiring aval ni l'observabilite complete.

Pause normative fermee:
- Doc normatif: `hermeneutic-node-downstream-branching-contract.md`
- Chemin docs: `app/docs/states/specs/hermeneutic-node-downstream-branching-contract.md`
- Zones runtime cibles: `core.chat_service` et `core.chat_prompt_context`
- Fichiers runtime cibles: `app/core/chat_service.py`, `app/core/chat_prompt_context.py`
- Raison: l'aval ne consomme jamais `primary_verdict` brut; il branche sur `validated_output` comme source canonique interne, puis le prompt principal lit une projection aval en prose `[JUGEMENT HERMENEUTIQUE]`, sans dump des artefacts internes.

Sortie attendue du lot: chaine finalisee `stimmung_agent -> primary_node -> validation_agent -> aval` + integration admin des deux agents LLM hermeneutiques reels + vue `Logs applicatifs` synthetique du pipeline + `Hermeneutic admin` detaillee et navigable + bascule full au redemarrage de Frida/du conteneur, avec pipeline actif, base/identities alimentees, effets runtime reels, logs conserves et inspection admin maintenue.
Validation minimale: l'aval branche uniquement sur un jugement valide derive de `validated_output`; le prompt principal lit un bloc prose `[JUGEMENT HERMENEUTIQUE]` resolu, jamais `primary_verdict` brut ni le dossier interne complet.
Dependances: Lots 1, 5 et 8.
Hors scope: lancement operationnel de la shadow globale.
